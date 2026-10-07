"""Palier Continuation (J4.1b suite) — mesure HORS-LIGNE : le résumeur RÉSUME-t-il, ou
CONTINUE-t-il la conversation ? (mode d'échec révélé par le smoke live).

Pour N vraies convs comparia dont le fold dépasse le seuil :
  - résumé sur le fold PAR DÉFAUT (msgs[:-KEEP])
  - résumé sur le fold AVEC FIX DE BORD (on retire les tours user pendants en fin de fold)
puis un classifieur (Haiku) étiquette chaque sortie : 'resume' vs 'continuation'.

Rapporte : taux de continuation par défaut, ventilé par fin de fold (user vs assistant),
et taux avec le fix de bord → dit si le fix vaut le coup AVANT de toucher le code.

Lancer : python analysis/qm/palier_continuation.py [N]   (défaut 40 ; ~$1)
"""
import sys, os, json, re, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from services.memory_service import MEMORY_SYS, summarizer_input, render_history, KEEP_DEFAULT, SEUIL_DEFAULT, plan_compaction
import pyarrow.parquet as pq

N = int(sys.argv[1]) if len(sys.argv) > 1 else 40
KEEP = KEEP_DEFAULT
TMIN, TMAX = 10, 20
STRIDE = 7
MODEL = "claude-haiku-4-5"
PIN, POUT = 1.0, 5.0
PARQUET = os.path.join(ROOT, "docs", "conversations.parquet")
OUT = os.path.join(ROOT, "analysis", "qm", "palier_continuation_verdicts.json")

CLASSIFY_SYS = (
    "On te donne la SORTIE d'un sous-agent censé RÉSUMER un historique de conversation. "
    "Classe-la : 'resume' = c'est un RÉSUMÉ/synthèse (sections, faits, décisions, entités) ; "
    "'continuation' = c'est une RÉPONSE qui CONTINUE la conversation (s'adresse à l'utilisateur, "
    "répond à une question, commence par « Oui / Voici / Vous avez raison / Bien sûr »…). "
    'JSON SEUL : {"type":"resume"|"continuation"}'
)


def _post(url, h, b, retries=4, timeout=180.0):
    last = None
    for a in range(retries):
        try:
            r = httpx.post(url, headers=h, json=b, timeout=timeout)
            if r.status_code in (429, 500, 502, 503, 504) and a < retries - 1:
                time.sleep(3 * (a + 1)); continue
            return r
        except (httpx.TimeoutException, httpx.TransportError) as e:
            last = e
            if a < retries - 1: time.sleep(3 * (a + 1)); continue
            raise
    raise last


def call(system, user, key, max_tokens=1500):
    h = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    r = _post("https://api.anthropic.com/v1/messages", h,
              {"model": MODEL, "max_tokens": max_tokens, "system": [{"type": "text", "text": system}],
               "messages": [{"role": "user", "content": user}]})
    r.raise_for_status(); d = r.json()
    txt = next((b["text"] for b in d["content"] if b["type"] == "text"), "")
    u = d.get("usage", {})
    return txt, (u.get("input_tokens", 0) * PIN + u.get("output_tokens", 0) * POUT) / 1e6


def classify(summary, key):
    t, c = call(CLASSIFY_SYS, summary, key, max_tokens=30)
    m = re.search(r'"type"\s*:\s*"(resume|continuation)"', t)
    return (m.group(1) if m else "?"), c


def split_no_trailing_user(msgs, keep):
    split = len(msgs) - keep
    while split > 0 and (msgs[split - 1].get("role") == "user"):
        split -= 1
    return split


def main():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key: sys.exit("ANTHROPIC_API_KEY absente")

    pf = pq.ParquetFile(PARQUET)
    sample = []; matched = 0
    for batch in pf.iter_batches(batch_size=4000, columns=["id", "conv_turns", "languages", "conversation_a"]):
        d = batch.to_pydict()
        for i in range(len(d["conv_turns"])):
            ct = d["conv_turns"][i]
            if not ct or not (TMIN <= ct <= TMAX): continue
            if "fr" not in (d["languages"][i] or []): continue
            conv = d["conversation_a"][i]
            if not conv: continue
            msgs = [{"role": t.get("role") or "user", "content": t.get("content") or ""} for t in conv]
            if not plan_compaction(msgs, KEEP, SEUIL_DEFAULT)["should_compact"]: continue
            matched += 1
            if matched % STRIDE != 1: continue
            sample.append({"id": int(d["id"][i]), "msgs": msgs})
            if len(sample) >= N: break
        if len(sample) >= N: break
    print(f"Échantillon : {len(sample)} convs FR {TMIN}-{TMAX}t (fold > seuil) sur {matched} candidates\n", flush=True)

    cost = {"v": 0.0}; lock = threading.Lock(); rows = []

    def work(s):
        msgs = s["msgs"]
        fold_def = msgs[:len(msgs) - KEEP]
        ends_user = fold_def[-1].get("role") == "user" if fold_def else False
        sd, c1 = call(MEMORY_SYS, summarizer_input(render_history(fold_def)), key)
        cls_d, c2 = classify(sd, key)
        # fold avec fix de bord
        split_fx = split_no_trailing_user(msgs, KEEP)
        if split_fx == len(msgs) - KEEP or split_fx == 0:
            cls_fx, c3, c4 = cls_d, 0.0, 0.0   # pas de changement de bord → même sortie
        else:
            sf, c3 = call(MEMORY_SYS, summarizer_input(render_history(msgs[:split_fx])), key)
            cls_fx, c4 = classify(sf, key)
        return {"id": s["id"], "ends_user": ends_user, "cls_default": cls_d,
                "cls_fixed": cls_fx, "cost": c1 + c2 + c3 + c4}

    done = 0
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(work, s): s for s in sample}
        for f in as_completed(futs):
            try: rec = f.result()
            except Exception as e: rec = {"id": futs[f]["id"], "error": str(e)}
            done += 1
            with lock:
                rows.append(rec); cost["v"] += rec.get("cost", 0)
                json.dump({"verdicts": rows}, open(OUT + ".tmp", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
                os.replace(OUT + ".tmp", OUT)
            print(f"  {done}/{len(sample)} fin_fold={'user' if rec.get('ends_user') else 'assist'} "
                  f"défaut={rec.get('cls_default')} fix={rec.get('cls_fixed')} ${cost['v']:.3f}", flush=True)

    ok = [r for r in rows if "cls_default" in r]
    n = len(ok)
    def rate(rs, k): return sum(1 for r in rs if r[k] == "continuation") / len(rs) if rs else 0
    eu = [r for r in ok if r["ends_user"]]; ea = [r for r in ok if not r["ends_user"]]
    print(f"\n=== PALIER CONTINUATION — résumeur {MODEL} sur {n} convs ===")
    print(f"  CONTINUATION (défaut)            : {100*rate(ok,'cls_default'):.0f}%  ({sum(1 for r in ok if r['cls_default']=='continuation')}/{n})")
    print(f"   ├─ quand fold finit sur USER     : {100*rate(eu,'cls_default'):.0f}%  (n={len(eu)})")
    print(f"   └─ quand fold finit sur ASSIST   : {100*rate(ea,'cls_default'):.0f}%  (n={len(ea)})")
    print(f"  CONTINUATION (fix bord de fold)  : {100*rate(ok,'cls_fixed'):.0f}%  → effet du fix")
    print(f"  COÛT TOTAL : ${cost['v']:.3f}  | verdicts → {OUT}")


if __name__ == "__main__":
    main()
