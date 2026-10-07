"""Palier Grille — fiabilité de la GRILLE DE COUVERTURE (J4.1c).

Question : quand un résumé PERD une info importante, le gate l'attrape-t-il (rappel),
sans sur-flagger les résumés fidèles (faux positifs) ?

Labels contrôlés, sur N vraies convs comparia (fold > seuil) :
  - résumé FIDÈLE (Haiku)                         → label attendu : passe (fidèle)
  - résumé AMPUTÉ d'un élément essentiel (Sonnet) → label attendu : rejeté (perte)
Testés par les DEUX couches du gate :
  - Couche 1 (déterministe, gratuite) : memory_service.coverage_gate
  - Couche 2 (juge fidélité Haiku, abordable) : perte_grave → rejet
On filtre les CONTINUATIONS (résumé qui n'en est pas un — déjà mesuré en 4.1b) pour
isoler la couverture. Mesure rappel + faux positifs, par couche et combiné.

Lancer : python analysis/qm/palier_grille_couverture.py [N]   (défaut 40 ; smoke 4)
"""
import sys, os, json, re, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from services.memory_service import (MEMORY_SYS, summarizer_input, render_history,
                                      coverage_gate, KEEP_DEFAULT, SEUIL_DEFAULT, plan_compaction)
import pyarrow.parquet as pq

N = int(sys.argv[1]) if len(sys.argv) > 1 else 40
KEEP = KEEP_DEFAULT
TMIN, TMAX = 10, 20
STRIDE = 7
PARQUET = os.path.join(ROOT, "docs", "conversations.parquet")
OUT = os.path.join(ROOT, "analysis", "qm", "palier_grille_verdicts.json")

SUMM_MODEL = "claude-haiku-4-5"
LOSSY_MODEL = "claude-sonnet-4-6"     # ampute un élément essentiel (label positif contrôlé)
JUDGE_MODEL = "claude-haiku-4-5"      # Couche 2 = juge fidélité abordable (le gate sous test)
PIN, POUT = 1.0, 5.0

LOSSY_SYS = (
    "On te donne un RÉSUMÉ fidèle. Retire-en UN seul élément essentiel — soit une décision, "
    "soit un chiffre, soit une entité/nom, soit une question ouverte — et garde TOUT le reste "
    "mot pour mot. Ne signale pas ce que tu as retiré. Renvoie UNIQUEMENT le résumé amputé."
)
JUDGE_SYS = (
    "Évaluateur STRICT de fidélité. On te donne un HISTORIQUE BRUT puis un RÉSUMÉ censé le "
    "remplacer. Le résumé PERD-il une info IMPORTANTE du brut (décision, fait, entité, chiffre, "
    "question ouverte) qui empêcherait de continuer ? Ignore style et longueur. "
    'JSON SEUL : {"verdict":"fidele"|"perte_mineure"|"perte_grave"}'
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


def call(system, user, model, key, max_tokens=1500):
    h = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    r = _post("https://api.anthropic.com/v1/messages", h,
              {"model": model, "max_tokens": max_tokens, "system": [{"type": "text", "text": system}],
               "messages": [{"role": "user", "content": user}]})
    r.raise_for_status(); d = r.json()
    txt = next((b["text"] for b in d["content"] if b["type"] == "text"), "")
    u = d.get("usage", {})
    return txt, (u.get("input_tokens", 0) * PIN + u.get("output_tokens", 0) * POUT) / 1e6


def verdict(t):
    m = re.search(r'"verdict"\s*:\s*"(fidele|perte_mineure|perte_grave)"', t or "")
    return m.group(1) if m else None


def judge_grave(summary, fold_render, key):
    """Couche 2 : True si le gate REJETTE (perte_grave)."""
    t, c = call(JUDGE_SYS, f"=== BRUT ===\n{fold_render}\n\n=== RÉSUMÉ ===\n{summary}\n\nÉvalue.",
                JUDGE_MODEL, key, 120)
    return verdict(t) == "perte_grave", c


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
            sample.append({"id": int(d["id"][i]), "fold": render_history(msgs[:len(msgs) - KEEP])})
            if len(sample) >= N: break
        if len(sample) >= N: break
    print(f"Échantillon : {len(sample)} convs (fold > seuil) sur {matched} candidates\n", flush=True)

    cost = {"v": 0.0}; lock = threading.Lock(); rows = []

    def work(s):
        fold = s["fold"]
        faithful, c1 = call(MEMORY_SYS, summarizer_input(fold), SUMM_MODEL, key)
        # filtre continuation : si la Couche 1 rejette le FIDÈLE comme dégénéré, c'est une
        # continuation (déjà mesuré en 4.1b) → hors périmètre couverture.
        ok_faithful, reason_f = coverage_gate(faithful, [{"role": "x", "content": fold}])
        is_continuation = (not ok_faithful) and "dégénéré" in reason_f
        if is_continuation:
            return {"id": s["id"], "continuation": True, "cost": c1}
        lossy, c2 = call(LOSSY_SYS, faithful, LOSSY_MODEL, key)
        # Couche 1 sur fidèle et amputé
        c1_flag_faithful = not ok_faithful
        c1_flag_lossy = not coverage_gate(lossy, [{"role": "x", "content": fold}])[0]
        # Couche 2 (juge) sur fidèle et amputé
        c2_flag_faithful, c3 = judge_grave(faithful, fold, key)
        c2_flag_lossy, c4 = judge_grave(lossy, fold, key)
        return {"id": s["id"], "continuation": False,
                "c1_faithful": c1_flag_faithful, "c1_lossy": c1_flag_lossy,
                "c2_faithful": c2_flag_faithful, "c2_lossy": c2_flag_lossy,
                "cost": c1 + c2 + c3 + c4}

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
            tag = "CONT" if rec.get("continuation") else (
                f"c1L={rec.get('c1_lossy')} c2L={rec.get('c2_lossy')} c2F={rec.get('c2_faithful')}")
            print(f"  {done}/{len(sample)} {tag} ${cost['v']:.3f}", flush=True)

    valid = [r for r in rows if r.get("continuation") is False]
    cont = [r for r in rows if r.get("continuation") is True]
    n = len(valid)
    def pct(rs, k): return 100 * sum(1 for r in rs if r.get(k)) / len(rs) if rs else 0
    def pct_or(rs, a, b): return 100 * sum(1 for r in rs if r.get(a) or r.get(b)) / len(rs) if rs else 0
    print(f"\n=== PALIER GRILLE COUVERTURE — sur {n} résumés (vrais résumés ; {len(cont)} continuations exclues) ===")
    print(f"  RAPPEL (amputé attrapé)   Couche1={pct(valid,'c1_lossy'):.0f}%  Couche2={pct(valid,'c2_lossy'):.0f}%  combiné={pct_or(valid,'c1_lossy','c2_lossy'):.0f}%")
    print(f"  FAUX POSITIFS (fidèle flag) Couche1={pct(valid,'c1_faithful'):.0f}%  Couche2={pct(valid,'c2_faithful'):.0f}%  combiné={pct_or(valid,'c1_faithful','c2_faithful'):.0f}%")
    print(f"  COÛT TOTAL : ${cost['v']:.3f}  | verdicts → {OUT}")
    print("  ⚠️ amputation synthétique (proxy) ; n petit → IC large.")


if __name__ == "__main__":
    main()
