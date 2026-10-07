"""Entraîne le classifieur de gating (régression logistique) sur gating_dataset.csv,
évalue en cross-val (petit dataset), sérialise vers backend/ml/artifacts/gating_model.joblib.
Lancer : cd backend && ./.venv/Scripts/python.exe ../analysis/ml/train_gating.py
"""
import os, sys, json, argparse
import numpy as np, pandas as pd, joblib
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score, StratifiedKFold

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
from ml.features import STRUCTURAL_NAMES

HERE = os.path.dirname(__file__)
ap = argparse.ArgumentParser()
ap.add_argument("--csv", default=os.path.join(HERE, "gating_dataset.csv"))
ap.add_argument("--out", default=None, help="chemin du .joblib (défaut: backend/ml/artifacts/gating_model.joblib)")
args = ap.parse_args()

df = pd.read_csv(args.csv)
X = df[STRUCTURAL_NAMES].values.astype("float32")
y = df["safe"].values.astype(int)

clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced"))

# cross-val seulement si chaque classe a >= n_splits exemples
n_splits = min(5, int(np.bincount(y).min()))
if n_splits >= 2:
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=0)
    scores = cross_val_score(clf, X, y, cv=cv, scoring="roc_auc")
    print(f"ROC-AUC cross-val ({n_splits} folds) : {scores.mean():.3f} ± {scores.std():.3f}")
else:
    print("dataset trop petit pour cross-val — entraînement direct (indicatif)")

clf.fit(X, y)
art_dir = os.path.join(HERE, "..", "..", "backend", "ml", "artifacts")
os.makedirs(art_dir, exist_ok=True)
path = args.out or os.path.join(art_dir, "gating_model.joblib")
joblib.dump({"model": clf, "features": STRUCTURAL_NAMES, "kind": "structural"}, path)
print(f"modèle sérialisé -> {path}")
