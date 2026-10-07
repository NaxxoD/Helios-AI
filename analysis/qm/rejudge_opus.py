"""
Re-jugement A_vs_B des paires ABC avec un juge PREMIUM (Opus 4.8 via API Anthropic),
pour remplacer les labels du juge local qwen2.5:7b (bruite, 1/3 desaccord).

Reutilise le prompt-juge + l'anti-biais de position de qm_evaluate_abc.py, mais :
  - backend = API Anthropic (credits) au lieu d'Ollama local
  - PARALLELE (ThreadPoolExecutor) -> minutes au lieu d'heures
  - checkpoint atomique + reprise (tmp + rename)
  - mesure le COUT REEL (usage tokens) et l'affiche a la fin
  - A_vs_B uniquement (ce dont le gate a besoin) -> ~moitie du cout

Lancer :
  python analysis/qm/rejudge_opus.py --limit 5     # smoke-test
  python analysis/qm/rejudge_opus.py               # run complet (349+ paires)
"""
import argparse, json, os, random, re, sys, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ABC_PATH = os.path.join(ROOT, "analysis", "qm", "qwen_458_abc.json")
OUT_PATH = os.path.join(ROOT, "analysis", "qm", "qwen_458_verdicts_opus48.json")

MODEL = "claude-opus-4-8"
PRICE_IN, PRICE_OUT = 5.0, 25.0  # $/1M tokens (Opus 4.8)

JUDGE_SYS = (
    "Tu es un evaluateur rigoureux et impartial. On te donne la DEMANDE d'un "
    "utilisateur et DEUX reponses (A et B). Decide si la reponse B satisfait le "
    "besoin AU MOINS aussi bien que la reponse A. IGNORE la longueur et la "
    "verbosite : une reponse plus courte qui repond correctement est aussi bonne, "
    "voire meilleure. Juge pertinence, exactitude, completude vs la demande. "
    "Reponds UNIQUEMENT en JSON : {\"meilleure\": \"A\"|\"B\"|\"egal\", \"raison\": \"...\"}"
)


def _post_with_retry(url, headers, body, timeout=180.0, retries=4):
    """retry sur timeout / transport / 429 / 5xx, backoff lineaire (patch msg13)."""
    last = None
    for attempt in range(retries):
        try:
            r = httpx.post(url, headers=headers, json=body, timeout=timeout)
            if r.status_code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(3 * (attempt + 1))
                continue
            return r
        except (httpx.TimeoutException, httpx.TransportError) as e:
            last = e
            if attempt < retries - 1:
                time.sleep(3 * (attempt + 1))
                continue
            raise
    raise last


def call_opus(system, user, api_key, max_tokens=1000):
    """retourne (texte, in_tokens, out_tokens). Pas de temperature (Opus 4.8 la refuse),
    pas de thinking (inutile pour un juge -> plus rapide/moins cher)."""
    body = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": [{"type": "text", "text": system}],
        "messages": [{"role": "user", "content": user}],
    }
    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01",
               "content-type": "application/json"}
    r = _post_with_retry("https://api.anthropic.com/v1/messages", headers, body)
    r.raise_for_status()
    data = r.json()
    txt = next((b["text"] for b in data["content"] if b["type"] == "text"), "")
    u = data.get("usage", {})
    return txt, u.get("input_tokens", 0), u.get("output_tokens", 0)


def parse_verdict(raw):
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return {"meilleure": "?", "raison": raw[:120]}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {"meilleure": "?", "raison": raw[:120]}


def judge_AB(api_key, demande, base, helios, rid):
    """anti-biais position (swap deterministe par id), comme qm_evaluate_abc.
    retourne (verdict, raison, in_tok, out_tok)."""
    rng = random.Random(str(rid))
    swap = rng.random() < 0.5
    A, B = (helios, base) if swap else (base, helios)
    user = (f"DEMANDE :\n{demande}\n\n--- Reponse A ---\n{A['content']}\n\n"
            f"--- Reponse B ---\n{B['content']}\n\nEvalue.")
    txt, ti, to = call_opus(JUDGE_SYS, user, api_key)
    v = parse_verdict(txt)
    best = v.get("meilleure", "?")
    if best == "egal":
        return "equivalent", v.get("raison", ""), ti, to
    helios_won = (best == "B" and not swap) or (best == "A" and swap)
    return ("helios_meilleure" if helios_won else "helios_moins_bonne"), v.get("raison", ""), ti, to


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="0 = tout ; sinon smoke-test")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default=OUT_PATH)
    a = ap.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY absente de os.environ")

    rows = json.load(open(ABC_PATH, encoding="utf-8"))
    # paires exploitables : A et B ont du contenu, pas d'erreur
    pairs = [r for r in rows
             if isinstance(r.get("A_baseline"), dict) and "content" in r["A_baseline"]
             and isinstance(r.get("B_palier"), dict) and "content" in r["B_palier"]]

    # reprise
    done = {}
    if os.path.exists(a.out):
        try:
            for v in json.load(open(a.out, encoding="utf-8")).get("verdicts", []):
                done[v["id"]] = v
        except Exception:
            done = {}
    todo = [r for r in pairs if r["id"] not in done]
    if a.limit:
        todo = todo[:a.limit]

    verdicts = list(done.values())
    lock = threading.Lock()
    stats = {"in": 0, "out": 0, "ok": 0, "err": 0}
    t0 = time.time()

    def save():
        tmp = a.out + ".tmp"
        json.dump({"verdicts": verdicts}, open(tmp, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        os.replace(tmp, a.out)

    print(f"juge={MODEL} | a faire={len(todo)} | deja faits={len(done)} | workers={a.workers}", flush=True)

    def work(row):
        rec = {"id": row["id"], "gain_estime": row.get("gain_estime"), "palier": row.get("palier")}
        try:
            v, why, ti, to = judge_AB(api_key, row.get("demande", ""),
                                      row["A_baseline"], row["B_palier"], str(row["id"]) + "AB")
            rec["A_vs_B"] = v
            rec["A_vs_B_raison"] = why
            rec["_usage"] = {"in": ti, "out": to}
        except Exception as e:
            rec["error"] = str(e)
        return rec

    n = 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(work, r): r for r in todo}
        for fut in as_completed(futs):
            rec = fut.result()
            n += 1
            with lock:
                verdicts.append(rec)
                if "error" in rec:
                    stats["err"] += 1
                else:
                    stats["ok"] += 1
                    stats["in"] += rec.get("_usage", {}).get("in", 0)
                    stats["out"] += rec.get("_usage", {}).get("out", 0)
                if n % 5 == 0 or n == len(todo):
                    save()
            el = time.time() - t0
            rate = el / n
            eta = rate * (len(todo) - n)
            cost = stats["in"] * PRICE_IN / 1e6 + stats["out"] * PRICE_OUT / 1e6
            print(f"  {n}/{len(todo)}  {rate:.1f}s/juge  ETA {int(eta)}s  "
                  f"ok={stats['ok']} err={stats['err']}  cout=${cost:.3f}  "
                  f"[{rec['id']}: {rec.get('A_vs_B', rec.get('error', '?'))[:20]}]", flush=True)

    save()
    cost = stats["in"] * PRICE_IN / 1e6 + stats["out"] * PRICE_OUT / 1e6
    # bilan verdicts (sur tout le fichier, reprise-safe)
    from collections import Counter
    c = Counter(v.get("A_vs_B") for v in verdicts if "A_vs_B" in v)
    nd = c.get("helios_meilleure", 0) + c.get("equivalent", 0)
    tot = sum(c.values())
    print(f"\n=== BILAN {MODEL} ===")
    print(f"  juges A_vs_B : {tot}  |  non-degrade (safe) : {nd}/{tot} = {100*nd/tot:.0f}%" if tot else "  aucun verdict")
    print(f"  detail : {dict(c)}")
    print(f"  tokens : in={stats['in']} out={stats['out']}  |  COUT REEL = ${cost:.3f}")
    print(f"  duree : {int(time.time()-t0)}s  |  out -> {a.out}")


if __name__ == "__main__":
    main()
