"""Construit le dataset de gating : prompt -> (features structurels, label safe).
safe=1 : appliquer le palier ne dégrade pas (juges d'accord) ; safe=0 : dégrade (juges d'accord).
Les désaccords inter-juges sont écartés (label bruité).
Lancer depuis backend/ pour l'import des features :
  cd backend && ./.venv/Scripts/python.exe ../analysis/ml/build_gating_dataset.py
"""
import json, os, sys, csv
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
from ml.features import structural_features, STRUCTURAL_NAMES

QM = os.path.join(os.path.dirname(__file__), "..", "qm")
ABC = json.load(open(os.path.join(QM, "qwen_458_abc.json"), encoding="utf-8"))
V1 = {v["id"]: v for v in json.load(open(os.path.join(QM, "qwen_458_verdicts_qwen25_7b.json"), encoding="utf-8"))["verdicts"]}

rows, kept, dropped = [], 0, 0
for r in ABC:
    rid = r["id"]
    j1 = V1.get(rid, {}).get("A_vs_B")
    if j1 is None:
        dropped += 1; continue
    safe = 0 if j1 == "helios_moins_bonne" else 1
    feats = structural_features(r["demande"])
    rows.append(list(feats) + [safe, rid])
    kept += 1

out = os.path.join(os.path.dirname(__file__), "gating_dataset.csv")
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(STRUCTURAL_NAMES + ["safe", "id"])
    w.writerows(rows)
print(f"gardés={kept}  écartés(désaccord/no-juge)={dropped}  -> {out}")
print(f"répartition safe : {sum(1 for r in rows if r[-2]==1)} sûrs / {kept}")
