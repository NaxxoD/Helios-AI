"""
Palier A — gain réel de l'heuristique sur la Couche A (le prompt user), corpus comparia.

On sépare DEUX transformations qui bougent les tokens en sens opposé :
  • NETTOYAGE   (optimise(), pur Python)  → RÉDUIT l'input (le vrai levier). Phase 1a, GRATUIT, large.
  • RESTRUCTURATION (Qwen local, template) → AJOUTE du scaffolding. Phase 1b, échantillon, via Ollama.

Phase 1a — exhaustive/gratuite (analogue Palier 1) :
  - distribution du gain nettoyage par message user (médiane / moyenne / pondéré-tokens)
  - décomposition pyramide (bruit / contexte / intention) sur prompts réels
  - effet cumulatif sur la Couche B : on ne nettoie QUE les tours user (l'assistant = substance).
    → quelle part de B est réductible, et gain B réel qui en découle.

Phase 1b — restructuration (analogue idée AD : décomposer le "+7%") :
  pour un échantillon, nettoyage → call_qwen → on mesure le delta tokens RÉEL et on le
  ventile via l'audit : composantes `inferred` = CONTEXTE IMPLICITE explicité (valeur),
  `present` = SIGNAL TECHNIQUE repackagé. On compare le delta des prompts SANS inferred
  (≈ surcoût template pur) vs AVEC inferred (≈ contexte implicite matérialisé).

Lancer : python analysis/qm/palierA_heuristique_corpus.py
"""
import sys, os, json, re, statistics as st

try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

# backend importable (optimise/calculator/config vivent sous backend/)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))

import pyarrow.parquet as pq
from utils.optimiseur import optimise
from utils.calculator import estimate_tokens_from_text

PARQUET = os.path.join(ROOT, "docs", "conversations.parquet")
OUT = os.path.join(ROOT, "analysis", "qm", "palierA_results.json")

N_CONV   = 4000     # conversations FR multi-tours scannées (Phase 1a)
N_RESTR  = 30       # messages user échantillonnés pour la restructuration (Phase 1b)
MIN_CHARS = 12      # ignore les messages quasi-vides
USER_ROLES = {"user", "human"}


def _is_user(turn):
    return (turn.get("role") or "").lower() in USER_ROLES


# ──────────────────────────────────────────────────────────────────────────
# Phase 1a — nettoyage (gratuit)
# ──────────────────────────────────────────────────────────────────────────
def phase_1a():
    pf = pq.ParquetFile(PARQUET)
    msg_before, msg_after = [], []        # tokens par message user
    pyr = {"intention": 0, "contrainte": 0, "contexte": 0, "bruit": 0, "meta": 0}
    # accumulateurs session (effet cumulatif sur B)
    b_user_before = b_user_after = b_assist = 0
    n_conv = n_msg = 0
    restr_pool = []                        # candidats pour Phase 1b

    for batch in pf.iter_batches(batch_size=8000,
                                 columns=["conv_turns", "languages", "conversation_a"]):
        d = batch.to_pydict()
        for i in range(len(d["conv_turns"])):
            ct = d["conv_turns"][i]
            if not ct or ct < 2:                       continue
            if "fr" not in (d["languages"][i] or []):  continue
            conv = d["conversation_a"][i]
            if not conv:                                continue
            n_conv += 1
            # Couche B au dernier tour = tous les tours SAUF le dernier
            for t in conv[:-1]:
                content = t.get("content") or ""
                tb = estimate_tokens_from_text(content) if content else 0
                if _is_user(t):
                    b_user_before += tb
                    if content.strip():
                        r = optimise(content)
                        b_user_after += r["tokens_after"]
                    else:
                        b_user_after += tb
                else:
                    b_assist += tb
            # gain par message user (sur TOUS les tours, pour la distribution)
            for t in conv:
                if not _is_user(t):                     continue
                content = (t.get("content") or "").strip()
                if len(content) < MIN_CHARS:            continue
                r = optimise(content)
                msg_before.append(r["tokens_before"])
                msg_after.append(r["tokens_after"])
                for k in pyr:
                    pyr[k] += len(r["pyramid"].get(k, []))
                n_msg += 1
                if len(restr_pool) < N_RESTR * 6 and r["tokens_before"] >= 25:
                    restr_pool.append({"clean": r["optimised"], "raw": content,
                                       "tok_clean": estimate_tokens_from_text(r["optimised"])})
            if n_conv >= N_CONV:
                break
        if n_conv >= N_CONV:
            break

    saved = [b - a for b, a in zip(msg_before, msg_after)]
    pct = [(b - a) / b for b, a in zip(msg_before, msg_after) if b > 0]
    tot_b, tot_a = sum(msg_before), sum(msg_after)

    res = {
        "n_conv": n_conv, "n_msg_user": n_msg,
        "gain_pondere_tokens": (tot_b - tot_a) / tot_b if tot_b else 0,   # la "facture" Couche A
        "gain_moyen_msg": st.mean(pct) if pct else 0,
        "gain_median_msg": st.median(pct) if pct else 0,
        "msg_avec_gain_pct": sum(1 for s in saved if s > 0) / len(saved) if saved else 0,
        "pyramide_segments": pyr,
        # effet cumulatif sur la Couche B
        "B_user_tokens": b_user_before,
        "B_assist_tokens": b_assist,
        "B_part_user": b_user_before / (b_user_before + b_assist) if (b_user_before + b_assist) else 0,
        "B_gain_si_nettoie_user": (b_user_before - b_user_after) / (b_user_before + b_assist)
                                  if (b_user_before + b_assist) else 0,
    }
    return res, restr_pool


# ──────────────────────────────────────────────────────────────────────────
# Phase 1b — restructuration (Ollama local) — skip propre si down
# ──────────────────────────────────────────────────────────────────────────
def phase_1b(pool):
    import httpx
    from config import settings
    from utils.qwen_optimizer import _SYSTEM, _escape_ctrl_in_strings, _fix_audit_coherence

    url = settings.OLLAMA_URL.rstrip("/")
    # ping
    try:
        httpx.get(f"{url}/api/tags", timeout=4.0)
    except Exception as e:
        return {"skipped": True, "reason": f"Ollama injoignable ({type(e).__name__})", "url": url}

    def restruct(clean):
        r = httpx.post(f"{url}/api/chat",
            json={"model": settings.QWEN_MODEL,
                  "messages": [{"role": "system", "content": _SYSTEM},
                               {"role": "user", "content": clean}],
                  "stream": False, "think": False},
            timeout=httpx.Timeout(connect=5.0, read=180.0, write=10.0, pool=5.0))
        raw = r.json()["message"]["content"]
        clean_txt = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        if clean_txt.startswith("```"):
            parts = clean_txt.split("```"); clean_txt = parts[1]
            if clean_txt.startswith("json"): clean_txt = clean_txt[4:]
        obj = json.loads(_escape_ctrl_in_strings(clean_txt.strip()))
        return _fix_audit_coherence(obj)

    rows = []
    for item in pool[:N_RESTR]:
        try:
            obj = restruct(item["clean"])
        except Exception as e:
            rows.append({"error": f"{type(e).__name__}: {e}"}); continue
        restr = obj.get("prompt_restructure", "")
        audit = obj.get("audit", {})
        tok_r = estimate_tokens_from_text(restr)
        n_inf = sum(1 for v in audit.values() if v == "inferred")
        n_pre = sum(1 for v in audit.values() if v == "present")
        n_abs = sum(1 for v in audit.values() if v == "absent")
        rows.append({"tok_clean": item["tok_clean"], "tok_restruct": tok_r,
                     "delta_pct": (tok_r - item["tok_clean"]) / max(1, item["tok_clean"]),
                     "n_inferred": n_inf, "n_present": n_pre, "n_absent": n_abs})
        print(f"  restruct {len(rows)}/{N_RESTR}: {item['tok_clean']}→{tok_r} tk "
              f"({100*(tok_r-item['tok_clean'])/max(1,item['tok_clean']):+.0f}%) "
              f"present={n_pre} inferred={n_inf}", flush=True)

    ok = [r for r in rows if "delta_pct" in r]
    if not ok:
        return {"skipped": False, "n_ok": 0, "rows": rows}
    avec_inf = [r["delta_pct"] for r in ok if r["n_inferred"] > 0]
    sans_inf = [r["delta_pct"] for r in ok if r["n_inferred"] == 0]
    return {
        "skipped": False, "n_ok": len(ok),
        "delta_moyen": st.mean(r["delta_pct"] for r in ok),
        "delta_median": st.median(r["delta_pct"] for r in ok),
        # la décomposition AD : surcoût template pur vs contexte implicite explicité
        "delta_sans_inferred": st.mean(sans_inf) if sans_inf else None,   # ≈ surcoût template
        "delta_avec_inferred": st.mean(avec_inf) if avec_inf else None,   # ≈ + contexte implicite
        "n_sans_inferred": len(sans_inf), "n_avec_inferred": len(avec_inf),
        "rows": rows,
    }


def main():
    print("PALIER A — heuristique sur la Couche A (corpus comparia)\n", flush=True)
    print("→ Phase 1a (nettoyage, gratuit)…", flush=True)
    a, pool = phase_1a()
    print(f"\n=== PHASE 1a — NETTOYAGE ({a['n_conv']} convs FR, {a['n_msg_user']} msg user) ===")
    print(f"  gain pondéré-tokens (la facture Couche A) : {100*a['gain_pondere_tokens']:.1f}%")
    print(f"  gain moyen / message  : {100*a['gain_moyen_msg']:.1f}%")
    print(f"  gain médian / message : {100*a['gain_median_msg']:.1f}%")
    print(f"  messages avec un gain : {100*a['msg_avec_gain_pct']:.0f}%")
    print(f"  pyramide segments     : {a['pyramide_segments']}")
    print(f"  Couche B — part user  : {100*a['B_part_user']:.0f}%  (reste = sorties assistant, intouchables)")
    print(f"  Couche B — gain si on nettoie les tours user : {100*a['B_gain_si_nettoie_user']:.1f}%")

    print("\n→ Phase 1b (restructuration, Ollama)…", flush=True)
    b = phase_1b(pool)
    if b.get("skipped"):
        print(f"  SKIP — {b['reason']} ({b.get('url')}). Lance Ollama puis relance le script.")
    elif b.get("n_ok", 0) == 0:
        print(f"  Aucune restructuration valide (erreurs). rows={b.get('rows')[:3]}")
    else:
        print(f"\n=== PHASE 1b — RESTRUCTURATION (n={b['n_ok']}) ===")
        print(f"  delta tokens moyen  : {100*b['delta_moyen']:+.1f}%   (médian {100*b['delta_median']:+.1f}%)")
        if b['delta_sans_inferred'] is not None:
            print(f"  delta SANS inferred : {100*b['delta_sans_inferred']:+.1f}%  (n={b['n_sans_inferred']}) ≈ surcoût template pur")
        if b['delta_avec_inferred'] is not None:
            print(f"  delta AVEC inferred : {100*b['delta_avec_inferred']:+.1f}%  (n={b['n_avec_inferred']}) ≈ + contexte implicite explicité")

    json.dump({"phase_1a": a, "phase_1b": b}, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"\n→ résultats : {OUT}")


if __name__ == "__main__":
    main()
