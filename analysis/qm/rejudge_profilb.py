"""
rejudge_profilb — re-juge des paires raw/qwen avec la grille (docs/recherche/grille-qualite-helios.md).

But : trancher la question DENSITÉ proprement. Le verdict initial "raw > qwen"
venait d'un juge holistique en Profil A (non-régression vs réponse baseline), qui
sous-note structurellement la restructuration. On veut isoler l'effet du PROFIL.

CONTRÔLE anti-confusion (le point clé) : on fait tourner LE MÊME juge (Opus) dans
les DEUX profils sur les MÊMES paires :
  - Profil A : qwen dégrade-t-il vs la réponse baseline ?
  - Profil B : qwen couvre-t-il mieux le BARÈME de la tâche ?
Le delta A→B, à juge constant, = l'effet PUR du profil (pas l'effet "meilleur juge").

FIABILITÉ (§7) — matrice 3 runs (retour du co-auteur) :
  run 1 = Opus      / Profil A → effet profil (vs run 2)
  run 2 = Opus      / Profil B → effet profil + densité
  run 3 = 2e juge   / Profil B → κ vs run 2  (κ exige un juge DIFFÉRENT : 2 passes
                                              Opus seraient un κ≈1 trivial et trompeur)
Le delta 1→2 = effet profil pur ; l'accord 2↔3 = κ des labels Profil B. κ bas →
labels bruités → gating condamné quoi qu'il arrive (su AVANT un gros run).

Barèmes : --baremes baremes.json (hand-reviewés, recommandé à N=20) sinon générés
BLIND (à partir du prompt seul). --gen-baremes pour générer puis hand-reviewer.

Lancer (depuis backend/, venv) :
  export ANTHROPIC_API_KEY=...   # (ou .env)
  ./.venv/Scripts/python.exe ../analysis/qm/rejudge_profilb.py \
      --in ../analysis/qm/pairs_sonnet.json \
      --baremes ../analysis/qm/baremes_exemples.json \
      --judge-model claude-opus-4-8 --judge2-model claude-sonnet-4-6
"""
import argparse, json, os, sys

_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "backend")
sys.path.insert(0, _BACKEND)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from services.judge_service import (
    generate_bareme, judge_profil_a, judge_profil_b, compare_profil_b, cohen_kappa,
)
from utils.quality_gates import is_unjudgeable, text_of as _content


def _couche1_ok(ref, cand):
    """Couche 1 (offline) : ne garder que les paires JUGEABLES. Exclut vide /
    erreur / troncature via quality_gates — MÊME source de vérité que l'escalade
    live. On n'exclut PAS les refus/boucles (vraies dégradations à laisser au juge)."""
    return not (is_unjudgeable(ref) or is_unjudgeable(cand))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="fichier de paires JSON")
    ap.add_argument("--out", dest="out", default="rejudge_profilb_verdicts.json")
    ap.add_argument("--ref-key", default="prompt_raw", help="clé de la réponse baseline")
    ap.add_argument("--cand-key", default="prompt_qwen", help="clé de la réponse candidate")
    ap.add_argument("--judge-model", default="claude-opus-4-8")
    ap.add_argument("--judge2-model", default=None, help="2e juge DISTINCT, Profil B, pour le kappa (optionnel)")
    ap.add_argument("--baremes", default=None, help="barèmes hand-reviewés {id: {elements}}")
    ap.add_argument("--gen-baremes", default=None, help="génère les barèmes BLIND → ce fichier puis stop")
    ap.add_argument("--limit", type=int, default=0, help="ne traiter que les N premières paires (smoke test)")
    a = ap.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY absente de l'environnement.")

    data = json.load(open(a.inp, encoding="utf-8"))
    rows = data["records"] if isinstance(data, dict) and "records" in data else data
    if a.limit:
        rows = rows[:a.limit]

    # Mode génération de barèmes (à hand-reviewer avant le run réel)
    if a.gen_baremes:
        out = {}
        for row in rows:
            rid = str(row["id"])
            out[rid] = {"demande": row.get("demande", ""),
                        "elements": generate_bareme(row.get("demande", ""),
                                                    model=a.judge_model, api_key=api_key)}
            print(f"barème {rid} : {len(out[rid]['elements'])} éléments")
        json.dump(out, open(a.gen_baremes, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print(f"\n✓ barèmes → {a.gen_baremes}  (HAND-REVIEW avant de relancer avec --baremes)")
        return

    baremes = json.load(open(a.baremes, encoding="utf-8")) if a.baremes else None

    verdicts = []
    # labels pour le kappa : Profil B (les labels qui nourriront le gating pour la
    # restructuration), entre le juge principal et un 2e juge DISTINCT.
    kappa_b_j1, kappa_b_j2 = [], []

    for row in rows:
        rid = str(row["id"])
        demande = row.get("demande", "")
        ref, cand = row.get(a.ref_key), row.get(a.cand_key)
        if not _couche1_ok(ref, cand):
            verdicts.append({"id": rid, "skip": "couche1"})
            continue
        ref_txt, cand_txt = _content(ref), _content(cand)

        # Barème : hand-reviewé sinon généré blind
        if baremes and rid in baremes:
            bareme = baremes[rid]["elements"]
        else:
            bareme = generate_bareme(demande, model=a.judge_model, api_key=api_key)

        # --- Profil A + Profil B (juge principal), résilient par paire ---
        try:
            a1 = judge_profil_a(demande, ref_txt, cand_txt, model=a.judge_model,
                                api_key=api_key, seed=rid)
            b_ref = judge_profil_b(demande, bareme, ref_txt, model=a.judge_model, api_key=api_key)
            b_cand = judge_profil_b(demande, bareme, cand_txt, model=a.judge_model, api_key=api_key)
        except Exception as e:
            verdicts.append({"id": rid, "error": str(e)[:200]})
            print(f"{rid}: ERREUR {str(e)[:80]}")
            continue
        b_cmp = compare_profil_b(b_ref, b_cand)

        rec = {"id": rid,
               "profil_a": {"candidate_vs_ref": a1["candidate_vs_ref"], "verdict": a1["verdict"]},
               "profil_b": {"score_ref": b_ref["score_essentiel"],
                            "score_cand": b_cand["score_essentiel"], "compare": b_cmp}}

        # --- Run 3 : 2e juge DISTINCT en Profil B → κ vs run 2 (retour du co-auteur :
        #     κ exige deux juges différents ; 2 passes Opus = κ trivial) ---
        if a.judge2_model:
            try:
                b2_ref = judge_profil_b(demande, bareme, ref_txt, model=a.judge2_model, api_key=api_key)
                b2_cand = judge_profil_b(demande, bareme, cand_txt, model=a.judge2_model, api_key=api_key)
                b2_cmp = compare_profil_b(b2_ref, b2_cand)
                rec["profil_b_judge2"] = b2_cmp
                kappa_b_j1.append(b_cmp)
                kappa_b_j2.append(b2_cmp)
            except Exception as e:
                rec["judge2_error"] = str(e)[:200]

        verdicts.append(rec)
        print(f"{rid}: A={a1['candidate_vs_ref']:<12} B={b_cmp:<20} "
              f"(ref {b_ref['score_essentiel']:.2f} / cand {b_cand['score_essentiel']:.2f})")

    # ---------------- Agrégation ----------------
    judged = [v for v in verdicts if "skip" not in v]
    n = len(judged)
    def rate(seq, hits):
        return f"{sum(1 for x in seq if x in hits)}/{len(seq)} ({100*sum(1 for x in seq if x in hits)/max(1,len(seq)):.0f}%)"

    a_vals = [v["profil_a"]["candidate_vs_ref"] for v in judged]
    b_vals = [v["profil_b"]["compare"] for v in judged]
    print(f"\n=== {n} paires jugées (juge {a.judge_model}) ===")
    print("PROFIL A (non-régression vs baseline) — qwen ≥ baseline :",
          rate(a_vals, {"meilleure", "egal"}))
    print("PROFIL B (conformité barème)         — qwen ≥ baseline :",
          rate(b_vals, {"candidate_meilleure", "equivalent"}))
    print("  → si B > A : la densité de qwen était masquée par le Profil A (thèse validée)")

    summary = {"n": n, "judge": a.judge_model,
               "profil_a_qwen_non_degrade": rate(a_vals, {"meilleure", "egal"}),
               "profil_b_qwen_non_degrade": rate(b_vals, {"candidate_meilleure", "equivalent"})}

    if a.judge2_model and len(kappa_b_j1) > 1:
        k = cohen_kappa(kappa_b_j1, kappa_b_j2)
        summary["kappa_profil_b"] = round(k, 3)
        verdict_k = ("substantiel ✓" if k >= 0.6 else "modéré" if k >= 0.4 else "FAIBLE — labels bruités")
        print(f"\nFIABILITÉ — κ Profil B ({a.judge_model} vs {a.judge2_model}) : {k:.3f}  → {verdict_k}")
        print("  κ < 0.4 → aucun labeling ne sauvera le gating ; pivot mécanique/comportemental.")

    json.dump({"summary": summary, "verdicts": verdicts},
              open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n✓ verdicts → {a.out}")


if __name__ == "__main__":
    main()
