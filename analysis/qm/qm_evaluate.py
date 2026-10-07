"""
QM — évaluation : à partir de output_delta_mistral.json, calcule
  (1) le delta tokens OUTPUT (et input) raw vs qwen,
  (2) l'économie de coût (tarif Haiku),
  (3) la NON-DÉGRADATION via un juge local fort (qwen2.5:14b), autre famille
      que la cible → pas d'auto-évaluation. C'est le chiffre #2 manquant.

Le juge ignore la longueur : une réponse plus courte qui satisfait le besoin
est jugée équivalente. Ordre A/B randomisé (seed déterministe) → pas de biais
de position.

Lancer (python Windows du venv) :
  ./.venv/Scripts/python.exe ../analysis/qm/qm_evaluate.py \
      --in ../analysis/qm/output_delta_mistral.json
"""
import argparse, json, random, re, sys
import httpx
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

OLLAMA = "http://localhost:11434/api/chat"
PRICE_IN, PRICE_OUT = 0.80, 4.00   # $/M tokens (Haiku) — à labelliser

JUDGE_SYS = (
    "Tu es un évaluateur rigoureux et impartial. On te donne la DEMANDE d'un "
    "utilisateur et DEUX réponses (A et B) produites par des assistants. "
    "Décide si la réponse B satisfait le besoin de l'utilisateur AU MOINS aussi "
    "bien que la réponse A. IGNORE la longueur et la verbosité : une réponse plus "
    "courte qui répond correctement est aussi bonne, voire meilleure. Juge la "
    "pertinence, l'exactitude et la complétude par rapport à la demande. "
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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="output_delta_mistral.json")
    ap.add_argument("--out", dest="out", default="qm_verdicts.json")
    ap.add_argument("--judge-model", default="qwen2.5:14b")
    ap.add_argument("--no-judge", action="store_true", help="tokens/coût seulement")
    a = ap.parse_args()

    rows = json.load(open(a.inp, encoding="utf-8"))
    d_out, d_in = [], []
    cost_raw_tot = cost_qwen_tot = 0.0
    verdicts, n_judge_ok, n_nondeg, trunc = [], 0, 0, 0

    for row in rows:
        raw, qw = row.get("prompt_raw"), row.get("prompt_qwen")
        if not raw or not qw or "error" in raw or "error" in qw:
            continue
        if raw.get("truncated") or qw.get("truncated"):
            trunc += 1
        # tokens
        if raw["output_tokens"]:
            d_out.append((raw["output_tokens"] - qw["output_tokens"]) / raw["output_tokens"])
        if raw["input_tokens"]:
            d_in.append((raw["input_tokens"] - qw["input_tokens"]) / raw["input_tokens"])
        # coût
        cost_raw_tot  += raw["input_tokens"]*PRICE_IN/1e6 + raw["output_tokens"]*PRICE_OUT/1e6
        cost_qwen_tot += qw["input_tokens"]*PRICE_IN/1e6 + qw["output_tokens"]*PRICE_OUT/1e6
        # juge
        if not a.no_judge:
            rng = random.Random(str(row["id"]))
            swap = rng.random() < 0.5            # qwen montré en A ou B (anti-biais)
            A, B = (qw, raw) if swap else (raw, qw)
            try:
                v = judge(a.judge_model, row.get("demande", ""), A["content"], B["content"])
            except Exception as e:
                verdicts.append({"id": row["id"], "error": str(e)}); continue
            best = v.get("meilleure", "?")
            # remap vers qwen vs raw
            if best == "egal": qwen_verdict = "equivalent"
            elif (best == "A" and swap) or (best == "B" and not swap): qwen_verdict = "qwen_meilleure"
            elif best in ("A", "B"): qwen_verdict = "qwen_moins_bonne"
            else: qwen_verdict = "?"
            n_judge_ok += 1
            if qwen_verdict in ("equivalent", "qwen_meilleure"): n_nondeg += 1
            verdicts.append({"id": row["id"], "verdict": qwen_verdict, "raison": v.get("raison","")})

    n = len(d_out)
    def pct(lst): return 100*sum(lst)/len(lst) if lst else 0
    print(f"\n=== QM — {n} prompts exploitables (tronqués: {trunc}) ===")
    print(f"Réduction tokens OUTPUT (raw→qwen) : {pct(d_out):+.1f}%")
    print(f"Réduction tokens INPUT             : {pct(d_in):+.1f}%")
    sav = 100*(cost_raw_tot-cost_qwen_tot)/cost_raw_tot if cost_raw_tot else 0
    print(f"Coût (Haiku $0.80/$4.00) : ${cost_raw_tot:.5f} → ${cost_qwen_tot:.5f}  (économie {sav:+.1f}%, pondérée tokens)")
    print(f"  → projection /1M prompts : ${cost_raw_tot/max(1,n)*1e6:.0f} → ${cost_qwen_tot/max(1,n)*1e6:.0f}")
    if not a.no_judge and n_judge_ok:
        print(f"\n#2 NON-DÉGRADATION (juge {a.judge_model}, anti-biais) :")
        print(f"  réponses qwen ≥ équivalentes : {n_nondeg}/{n_judge_ok}  ({100*n_nondeg/n_judge_ok:.0f}%)")
        worse = [v for v in verdicts if v.get("verdict") == "qwen_moins_bonne"]
        print(f"  ⚠ dégradations à inspecter : {len(worse)}")
    json.dump({"verdicts": verdicts}, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n✓ verdicts → {a.out}")

if __name__ == "__main__":
    main()
