"""
QM A/B/C — évaluation. À partir de smoke45_abc.json (3 conditions par prompt) :

  (1) Décomposition tokens/coût :
        A→B  = valeur du PALIER seul (consigne longueur + cap)
        B→C  = apport marginal de QWEN (par-dessus le palier)
        A→C  = Helios COMPLET vs sans Helios
  (2) Formule du prof (1 − Y/X) pondérée tokens, pour A→C.
  (3) Non-dégradation par juge LLM neutre, sur les réponses RÉELLEMENT cappées :
        - A vs B : le cap palier dégrade-t-il vs la réponse libre ?
        - A vs C : Helios complet dégrade-t-il vs sans Helios ?
      Le juge ignore la longueur (consigne explicite), ordre randomisé (anti-biais).

Lancer (python Windows du venv) :
  ./.venv/Scripts/python.exe ../analysis/qm/qm_evaluate_abc.py \
      --in ../analysis/qm/smoke45_abc.json
"""
import argparse, json, os, random, re, sys, time
import httpx
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def _fmt_dur(s):
    s = int(s); h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    return f"{h}h{m:02d}m" if h else f"{m}m{sec:02d}s"

OLLAMA = "http://localhost:11434/api/chat"
PRICE_IN, PRICE_OUT = 0.80, 4.00   # $/M tokens (Haiku) — à labelliser

JUDGE_SYS = (
    "Tu es un évaluateur rigoureux et impartial. On te donne la DEMANDE d'un "
    "utilisateur et DEUX réponses (A et B). Décide si la réponse B satisfait le "
    "besoin AU MOINS aussi bien que la réponse A. IGNORE la longueur et la "
    "verbosité : une réponse plus courte qui répond correctement est aussi bonne, "
    "voire meilleure. Juge pertinence, exactitude, complétude vs la demande. "
    "Réponds UNIQUEMENT en JSON : {\"meilleure\": \"A\"|\"B\"|\"egal\", \"raison\": \"...\"}"
)

def judge(model, demande, ans_A, ans_B):
    user = (f"DEMANDE :\n{demande}\n\n--- Réponse A ---\n{ans_A}\n\n"
            f"--- Réponse B ---\n{ans_B}\n\nÉvalue.")
    r = httpx.post(OLLAMA, json={
        "model": model,
        "messages": [{"role": "system", "content": JUDGE_SYS},
                     {"role": "user", "content": user}],
        "stream": False, "options": {"temperature": 0},
    }, timeout=180.0)
    r.raise_for_status()
    raw = r.json().get("message", {}).get("content", "")
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    return json.loads(m.group(0)) if m else {"meilleure": "?", "raison": raw[:120]}

def ok(cond):
    """une condition est exploitable pour les tokens si compteurs fiables + non tronquée"""
    return (isinstance(cond, dict) and "error" not in cond
            and cond.get("counts_ok") and not cond.get("truncated"))

def cost(cond):
    return cond["input_tokens"]*PRICE_IN/1e6 + cond["output_tokens"]*PRICE_OUT/1e6

def judge_pair(model, demande, base, helios, rid):
    """retourne 'nondeg' (helios >= base), 'degrade', ou None ; anti-biais position"""
    rng = random.Random(str(rid))
    swap = rng.random() < 0.5
    A, B = (helios, base) if swap else (base, helios)
    v = judge(model, demande, A["content"], B["content"])
    best = v.get("meilleure", "?")
    if best == "egal":
        return "equivalent", v.get("raison", "")
    # helios est en B si not swap, en A si swap
    helios_won = (best == "B" and not swap) or (best == "A" and swap)
    return ("helios_meilleure" if helios_won else "helios_moins_bonne"), v.get("raison", "")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="smoke45_abc.json")
    ap.add_argument("--out", dest="out", default="qm_abc_verdicts.json")
    ap.add_argument("--judge-model", default="llama3.1:8b")
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--no-ac", action="store_true",
                    help="ne juge que A_vs_B (lean gating) — saute A_vs_C")
    a = ap.parse_args()

    rows = json.load(open(a.inp, encoding="utf-8"))
    # agrégats coût (échange complet = input + output) sur lignes où A,B,C exploitables
    cA = cB = cC = 0.0
    tokA = tokB = tokC = 0
    n_tok = 0
    for row in rows:
        A, B, C = row.get("A_baseline"), row.get("B_palier"), row.get("C_helios")
        if ok(A) and ok(B) and ok(C):
            n_tok += 1
            cA += cost(A); cB += cost(B); cC += cost(C)
            tokA += A["input_tokens"]+A["output_tokens"]
            tokB += B["input_tokens"]+B["output_tokens"]
            tokC += C["input_tokens"]+C["output_tokens"]

    # --- jugement : reprise + sauvegarde incrémentale ---
    verdicts = []
    if not a.no_judge:
        done = {}
        if os.path.exists(a.out):
            try:
                for v in json.load(open(a.out, encoding="utf-8")).get("verdicts", []):
                    done[v["id"]] = v
            except Exception:
                done = {}
        verdicts = list(done.values())

        def save():
            tmp = a.out + ".tmp"
            json.dump({"verdicts": verdicts}, open(tmp, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
            os.replace(tmp, a.out)

        todo = [r for r in rows
                if isinstance(r.get("A_baseline"), dict) and "error" not in r["A_baseline"]
                and r["id"] not in done]
        total = len(todo)
        print(f"reprise juge ({a.judge_model}) : {len(done)} déjà jugés, {total} à faire", flush=True)
        t0 = time.time()
        for k, row in enumerate(todo, 1):
            A, B, C = row.get("A_baseline"), row.get("B_palier"), row.get("C_helios")
            demande = row.get("demande", "")
            rec = {"id": row["id"], "gain_estime": row.get("gain_estime"), "palier": row.get("palier")}
            try:
                if isinstance(B, dict) and "error" not in B and A.get("content") and B.get("content"):
                    v, why = judge_pair(a.judge_model, demande, A, B, str(row["id"])+"AB")
                    rec["A_vs_B"] = v; rec["A_vs_B_raison"] = why
                if not a.no_ac and isinstance(C, dict) and "error" not in C and A.get("content") and C.get("content"):
                    v, why = judge_pair(a.judge_model, demande, A, C, str(row["id"])+"AC")
                    rec["A_vs_C"] = v; rec["A_vs_C_raison"] = why
            except Exception as e:
                rec["error"] = str(e)
            verdicts.append(rec)
            save()   # checkpoint après chaque prompt jugé
            elapsed = time.time() - t0
            rate = elapsed / k
            eta = rate * (total - k)
            pct = 100 * k / total if total else 100
            filled = int(pct // 5)
            bar = "#" * filled + "-" * (20 - filled)
            print(f"[{bar}] {pct:5.1f}%  {k}/{total}  {rate:.0f}s/juge  "
                  f"écoulé {_fmt_dur(elapsed)}  ETA {_fmt_dur(eta)}", flush=True)

    # comptages recomputés depuis les verdicts -> resume-safe
    j_AB = sum(1 for v in verdicts if "A_vs_B" in v)
    nd_AB = sum(1 for v in verdicts if v.get("A_vs_B") in ("equivalent", "helios_meilleure"))
    j_AC = sum(1 for v in verdicts if "A_vs_C" in v)
    nd_AC = sum(1 for v in verdicts if v.get("A_vs_C") in ("equivalent", "helios_meilleure"))

    print(f"\n=== QM A/B/C — {len(rows)} prompts ({n_tok} exploitables tokens) ===")
    if n_tok:
        def sav(a_, b_): return 100*(a_-b_)/a_ if a_ else 0
        print("\n— DÉCOMPOSITION COÛT (échange complet, Haiku $0.80/$4.00) —")
        print(f"  A sans Helios : ${cA:.5f}   ({tokA} tokens)")
        print(f"  B palier seul : ${cB:.5f}   ({tokB} tokens)   → vs A : {sav(cA,cB):+.1f}% coût")
        print(f"  C Helios full : ${cC:.5f}   ({tokC} tokens)   → vs A : {sav(cA,cC):+.1f}% coût")
        print(f"  apport Qwen (B→C) : {sav(cB,cC):+.1f}% coût")
        gain_prof = 100*(1 - tokC/tokA) if tokA else 0
        print(f"  Gain ÉCHANGE COMPLET (prof, 1−Y/X, A→C) : {gain_prof:+.1f}%  (X={tokA} → Y={tokC})")
        print(f"  → projection /1M prompts : A ${cA/n_tok*1e6:.0f}  B ${cB/n_tok*1e6:.0f}  C ${cC/n_tok*1e6:.0f}")
    if not a.no_judge:
        print("\n— NON-DÉGRADATION (juge {}, anti-biais, sur réponses cappées) —".format(a.judge_model))
        if j_AB: print(f"  A vs B (palier cappé ≥ baseline libre) : {nd_AB}/{j_AB}  ({100*nd_AB/j_AB:.0f}%)")
        if j_AC: print(f"  A vs C (Helios complet ≥ sans Helios)  : {nd_AC}/{j_AC}  ({100*nd_AC/j_AC:.0f}%)")
        worse_AC = [v for v in verdicts if v.get("A_vs_C") == "helios_moins_bonne"]
        print(f"  ⚠ Helios dégrade (A vs C) : {len(worse_AC)} cas")
    json.dump({"verdicts": verdicts}, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n✓ verdicts → {a.out}")

if __name__ == "__main__":
    main()
