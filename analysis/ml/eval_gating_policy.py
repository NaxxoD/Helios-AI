"""Évalue la policy de gating vs compression aveugle, sur les sorties QM déjà jugées.
Pour chaque prompt jugé : la policy (modèle) aurait-elle comprimé ? Si oui, on compte
la non-dégradation réelle (verdict A_vs_B). On compare au régime 'toujours comprimer'.
Lancer : cd backend && ./.venv/Scripts/python.exe ../analysis/ml/eval_gating_policy.py
"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
from ml.features import structural_features
from ml.gating import get_model

QM = os.path.join(os.path.dirname(__file__), "..", "qm")
ABC = json.load(open(os.path.join(QM, "qwen_458_abc.json"), encoding="utf-8"))
V14 = {v["id"]: v for v in json.load(open(os.path.join(QM, "qwen_458_verdicts_qwen25_7b.json"), encoding="utf-8"))["verdicts"]}

g = get_model()
if not g.available:
    print("artifact absent — lancer train_gating.py"); sys.exit(1)

THRESHOLD = 0.5
blind_nondeg = blind_n = 0
gate_nondeg = gate_n = 0
for r in ABC:
    v = V14.get(r["id"], {}).get("A_vs_B")
    if v is None:
        continue
    nondeg = (v != "helios_moins_bonne")
    # régime aveugle : on comprime toujours
    blind_n += 1; blind_nondeg += nondeg
    # régime gating : on comprime seulement si le modèle dit sûr
    p = g.predict_safe(structural_features(r["demande"]))
    if p is not None and p >= THRESHOLD:
        gate_n += 1; gate_nondeg += nondeg

print(f"AVEUGLE  : non-dégradation {blind_nondeg}/{blind_n} = {100*blind_nondeg/max(1,blind_n):.0f}% (comprime {blind_n})")
print(f"GATING   : non-dégradation {gate_nondeg}/{gate_n} = {100*gate_nondeg/max(1,gate_n):.0f}% (comprime {gate_n})")
print("-> objectif spec : gating > 90% de non-degradation sur ce qu'il comprime")
