# Helios — Gating de compression (Plan 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire une Policy Engine ML qui décide *si on applique la contrainte de longueur (palier)* à un prompt — pour ne garder le gain coût (−32%) que sur le sous-ensemble où ça ne dégrade pas la réponse.

**Architecture:** Une couche ML branchée **après** l'optimiseur existant. Un Feature Extractor (embedding nomic-embed + features structurels) alimente un classifieur de gating ; un Combiner applique la décision avec **fallback heuristique** (le système marche même sans modèle). Décision intégrée dans `optimise()` : si gating = "non sûr", le palier est rabaissé vers un palier **sans contrainte** (réponse libre), sinon le palier heuristique est conservé. Frontend inchangé.

**Tech Stack:** Python 3 (venv Windows `backend/.venv/Scripts/python.exe`), FastAPI, scikit-learn + joblib (à installer), numpy/pandas (présents), httpx, Ollama (`nomic-embed-text`), unittest.

---

## File Structure

**Nouveau package `backend/ml/`** (couche ML isolée, un fichier = un rôle) :
- `backend/ml/__init__.py` — exporte l'API publique (`decide_policy`).
- `backend/ml/features.py` — Feature Extractor : prompt → vecteur numpy. Seul fichier qui parle à nomic-embed.
- `backend/ml/gating.py` — chargement du modèle `.joblib` + `predict_safe(vec) -> float`.
- `backend/ml/policy.py` — Combiner : `decide_policy(prompt) -> PolicyDecision` + fallback.
- `backend/ml/artifacts/` — modèles sérialisés (produits hors-ligne).

**Scripts hors-ligne (labeling + entraînement)** sous `analysis/ml/` :
- `analysis/ml/build_gating_dataset.py` — sorties QM → dataset labellisé (features + label sûr/non-sûr).
- `analysis/ml/train_gating.py` — entraîne, valide, sérialise vers `backend/ml/artifacts/gating_model.joblib`.

**Modifié :**
- `backend/requirements.txt` — ajout `scikit-learn`, `joblib`.
- `backend/utils/optimiseur.py` — `optimise()` consulte `decide_policy` et override le palier si non-sûr.

**Tests :** `backend/tests/test_ml_features.py`, `test_ml_gating.py`, `test_ml_policy.py`, et extension de `test_optimiseur.py`.

---

## Conventions

- **Toujours** lancer le python Windows : `./.venv/Scripts/python.exe` depuis `backend/` (atteint Ollama, a les deps).
- Tests : `cd backend && ./.venv/Scripts/python.exe -m unittest tests.test_ml_features -v`
- Palier "sans contrainte" cible quand gating=non-sûr : `'5'` (Dilatation, `PALIERS['5']['constraint'] is None` — vérifié `optimiseur.py`).

---

### Task 0: Dépendances + squelette du package ML

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/ml/__init__.py`, `backend/ml/artifacts/.gitkeep`

- [ ] **Step 1: Ajouter les deps**

Ajouter à la fin de `backend/requirements.txt` :

```
scikit-learn
joblib
```

- [ ] **Step 2: Installer**

Run: `cd backend && ./.venv/Scripts/python.exe -m pip install scikit-learn joblib`
Expected: `Successfully installed joblib-... scikit-learn-... scipy-...`

- [ ] **Step 3: Créer le package**

`backend/ml/__init__.py` :

```python
"""Couche ML Helios : Policy Engine (gating de compression).

API publique : decide_policy(prompt) -> PolicyDecision
"""
from .policy import decide_policy, PolicyDecision  # noqa: F401
```

Créer le dossier artifacts avec `backend/ml/artifacts/.gitkeep` (fichier vide).

- [ ] **Step 4: Vérifier l'install**

Run: `cd backend && ./.venv/Scripts/python.exe -c "import sklearn, joblib; print(sklearn.__version__, joblib.__version__)"`
Expected: deux numéros de version, pas d'ImportError.

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/ml/__init__.py backend/ml/artifacts/.gitkeep
git commit -m "chore(ml): scaffold backend/ml package + scikit-learn/joblib deps"
```

---

### Task 1: Feature Extractor

**Files:**
- Create: `backend/ml/features.py`
- Test: `backend/tests/test_ml_features.py`

Le Feature Extractor renvoie un vecteur de longueur fixe = `[embedding nomic-embed (768) ] + [features structurels (8)]`. Si l'embedding échoue (Ollama down), il lève `EmbeddingUnavailable` (le Combiner le rattrapera en fallback).

- [ ] **Step 1: Écrire le test qui échoue**

`backend/tests/test_ml_features.py` :

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unittest
from ml import features


class TestStructuralFeatures(unittest.TestCase):
    def test_structural_vector_length_and_values(self):
        # n'appelle PAS Ollama : teste seulement la partie structurelle
        feats = features.structural_features("Explique-moi la récursivité en 50 mots ?")
        # 8 features structurels attendus, ordre stable
        self.assertEqual(len(feats), features.N_STRUCTURAL)
        self.assertEqual(features.N_STRUCTURAL, 8)
        # word_count > 0, question_marks == 1, has_constraint == 1 ("50 mots")
        names = features.STRUCTURAL_NAMES
        d = dict(zip(names, feats))
        self.assertGreater(d["word_count"], 0)
        self.assertEqual(d["question_marks"], 1.0)
        self.assertEqual(d["has_constraint"], 1.0)

    def test_palier_feature_uses_backend_logic(self):
        feats = dict(zip(features.STRUCTURAL_NAMES,
                         features.structural_features("Écris une fonction Python qui trie une liste")))
        # detect_palier renvoie 'C' (code) -> encodé en index numérique stable
        self.assertGreaterEqual(feats["palier_idx"], 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Lancer le test (échec attendu)**

Run: `cd backend && ./.venv/Scripts/python.exe -m unittest tests.test_ml_features -v`
Expected: FAIL `ModuleNotFoundError: No module named 'ml.features'`

- [ ] **Step 3: Implémenter**

`backend/ml/features.py` :

```python
"""Feature Extractor : prompt -> vecteur numpy de longueur fixe.
Seul module qui parle à nomic-embed (Ollama). Réutilise la logique palier du backend.
"""
import re
import numpy as np
import httpx
from utils.optimiseur import detect_palier, PALIERS, _CONSTRAINT_MARKERS  # logique existante

OLLAMA_EMBED = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"
EMBED_DIM = 768

# ordre STABLE des paliers -> index numérique (feature)
_PALIER_ORDER = ['★', '0', '1', '2', '3', '4', '5', 'C', '6']

STRUCTURAL_NAMES = [
    "word_count", "char_count", "question_marks",
    "has_constraint", "is_code", "is_doc", "is_complex", "palier_idx",
]
N_STRUCTURAL = len(STRUCTURAL_NAMES)

_CODE_RE = re.compile(r"\b(fonction|function|code|python|sql|bug|script|classe)\b", re.I)
_DOC_RE = re.compile(r"\b(documentation|rédige|article|rapport|tutoriel)\b", re.I)
_COMPLEX_RE = re.compile(r"\b(compare|analyse|avantages|inconvénients|pourquoi|explique)\b", re.I)


class EmbeddingUnavailable(RuntimeError):
    pass


def structural_features(prompt: str) -> np.ndarray:
    words = prompt.split()
    pk = detect_palier(prompt)
    has_constraint = any(m in prompt.lower() for m in _CONSTRAINT_MARKERS)
    vec = [
        float(len(words)),
        float(len(prompt)),
        float(prompt.count("?")),
        1.0 if has_constraint else 0.0,
        1.0 if _CODE_RE.search(prompt) else 0.0,
        1.0 if _DOC_RE.search(prompt) else 0.0,
        1.0 if _COMPLEX_RE.search(prompt) else 0.0,
        float(_PALIER_ORDER.index(pk) if pk in _PALIER_ORDER else -1),
    ]
    return np.array(vec, dtype=np.float32)


def embed(prompt: str, timeout: float = 15.0) -> np.ndarray:
    try:
        r = httpx.post(OLLAMA_EMBED, json={"model": EMBED_MODEL, "prompt": prompt}, timeout=timeout)
        r.raise_for_status()
        emb = r.json().get("embedding")
        if not emb or len(emb) != EMBED_DIM:
            raise EmbeddingUnavailable(f"embedding invalide (len={len(emb) if emb else 0})")
        return np.array(emb, dtype=np.float32)
    except EmbeddingUnavailable:
        raise
    except Exception as e:
        raise EmbeddingUnavailable(str(e))


def extract_features(prompt: str) -> np.ndarray:
    """vecteur complet [embedding(768) | structurels(8)] -> shape (776,)"""
    return np.concatenate([embed(prompt), structural_features(prompt)])


FEATURE_DIM = EMBED_DIM + N_STRUCTURAL
```

> Note : si `_CONSTRAINT_MARKERS` n'est pas importable depuis optimiseur, le remplacer par une liste locale des marqueurs (`["mots max", "en mots", "caractères", "bullet"]`) — vérifier le nom exact à l'import (`grep CONSTRAINT_MARKERS backend/utils/optimiseur.py`).

- [ ] **Step 4: Lancer le test (succès attendu)**

Run: `cd backend && ./.venv/Scripts/python.exe -m unittest tests.test_ml_features -v`
Expected: PASS (2 tests). Le test n'appelle que `structural_features`, donc pas besoin d'Ollama.

- [ ] **Step 5: Smoke embedding (manuel, Ollama requis)**

Run: `cd backend && ./.venv/Scripts/python.exe -c "from ml.features import extract_features; print(extract_features('Explique la récursivité').shape)"`
Expected: `(776,)`

- [ ] **Step 6: Commit**

```bash
git add backend/ml/features.py backend/tests/test_ml_features.py
git commit -m "feat(ml): feature extractor (nomic-embed + structurels)"
```

---

### Task 2: Construire le dataset de gating depuis les sorties QM

**Files:**
- Create: `analysis/ml/build_gating_dataset.py`
- Inputs (existants) : `analysis/qm/smoke45_abc.json`, `analysis/qm/qm_abc_verdicts.json`, `analysis/qm/qm_abc_verdicts_qwen14b.json`
- Output: `analysis/ml/gating_dataset.csv`

Label = **compression sûre** : le palier (condition B) ne dégrade PAS vs baseline (A). On prend le **label haute-confiance** : les deux juges d'accord. `safe = 1` si aucun juge ne dit "helios_moins_bonne" sur A_vs_B ; `safe = 0` si les deux disent dégradé ; on **écarte** les désaccords (label bruité).

- [ ] **Step 1: Écrire le script**

`analysis/ml/build_gating_dataset.py` :

```python
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
ABC = json.load(open(os.path.join(QM, "smoke45_abc.json"), encoding="utf-8"))
V8 = {v["id"]: v for v in json.load(open(os.path.join(QM, "qm_abc_verdicts.json"), encoding="utf-8"))["verdicts"]}
V14 = {v["id"]: v for v in json.load(open(os.path.join(QM, "qm_abc_verdicts_qwen14b.json"), encoding="utf-8"))["verdicts"]}

rows, kept, dropped = [], 0, 0
for r in ABC:
    rid = r["id"]
    j8 = V8.get(rid, {}).get("A_vs_B")
    j14 = V14.get(rid, {}).get("A_vs_B")
    if j8 is None or j14 is None:
        dropped += 1; continue
    deg8 = (j8 == "helios_moins_bonne")
    deg14 = (j14 == "helios_moins_bonne")
    if deg8 != deg14:        # désaccord -> label bruité, on écarte
        dropped += 1; continue
    safe = 0 if deg8 else 1   # les deux d'accord
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
```

> Note : ce dataset utilise les **features structurels seuls** (rapide, pas d'appel Ollama pour la version initiale). Task 3 ajoute l'embedding au train si on veut ; on commence structurels pour valider la chaîne.

- [ ] **Step 2: Lancer**

Run: `cd backend && ./.venv/Scripts/python.exe ../analysis/ml/build_gating_dataset.py`
Expected: ligne `gardés=N écartés=M -> .../gating_dataset.csv` avec N ≈ 17–30 (smoke). Fichier CSV créé.

- [ ] **Step 3: Vérifier le CSV**

Run: `cd backend && ./.venv/Scripts/python.exe -c "import pandas as pd; d=pd.read_csv('../analysis/ml/gating_dataset.csv'); print(d.shape); print(d['safe'].value_counts())"`
Expected: un DataFrame avec colonnes structurelles + `safe` + `id`, et les deux classes présentes.

- [ ] **Step 4: Commit**

```bash
git add analysis/ml/build_gating_dataset.py analysis/ml/gating_dataset.csv
git commit -m "feat(ml): build gating dataset from QM dual-judge labels"
```

> ⚠️ **Limite assumée (à logger)** : le smoke (45 prompts) donne très peu d'exemples après filtrage haute-confiance. Le modèle sera indicatif. Le run complet (labeling sur les 458 prompts QM) est un pré-requis pour des chiffres défendables — c'est un incrément de données, pas de code (relancer `qm_run_abc.py`/`qm_evaluate_abc.py` sur `input_delta_QM.json`).

---

### Task 3: Entraîner et sérialiser le modèle de gating

**Files:**
- Create: `analysis/ml/train_gating.py`
- Output: `backend/ml/artifacts/gating_model.joblib`

- [ ] **Step 1: Écrire le script d'entraînement**

`analysis/ml/train_gating.py` :

```python
"""Entraîne le classifieur de gating (régression logistique) sur gating_dataset.csv,
évalue en cross-val (petit dataset), sérialise vers backend/ml/artifacts/gating_model.joblib.
Lancer : cd backend && ./.venv/Scripts/python.exe ../analysis/ml/train_gating.py
"""
import os, sys, json
import numpy as np, pandas as pd, joblib
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score, StratifiedKFold

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
from ml.features import STRUCTURAL_NAMES

HERE = os.path.dirname(__file__)
df = pd.read_csv(os.path.join(HERE, "gating_dataset.csv"))
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
path = os.path.join(art_dir, "gating_model.joblib")
joblib.dump({"model": clf, "features": STRUCTURAL_NAMES, "kind": "structural"}, path)
print(f"modèle sérialisé -> {path}")
```

- [ ] **Step 2: Lancer l'entraînement**

Run: `cd backend && ./.venv/Scripts/python.exe ../analysis/ml/train_gating.py`
Expected: une ligne ROC-AUC (ou message "trop petit") + `modèle sérialisé -> .../gating_model.joblib`. Fichier joblib créé.

- [ ] **Step 3: Commit**

```bash
git add analysis/ml/train_gating.py backend/ml/artifacts/gating_model.joblib
git commit -m "feat(ml): train + serialize gating classifier"
```

---

### Task 4: Loader + prédiction du modèle de gating

**Files:**
- Create: `backend/ml/gating.py`
- Test: `backend/tests/test_ml_gating.py`

- [ ] **Step 1: Écrire le test qui échoue**

`backend/tests/test_ml_gating.py` :

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unittest
import numpy as np
from ml import gating


class TestGatingLoader(unittest.TestCase):
    def test_missing_artifact_returns_none(self):
        g = gating.GatingModel(path="/chemin/inexistant.joblib")
        self.assertFalse(g.available)
        self.assertIsNone(g.predict_safe(np.zeros(8, dtype="float32")))

    def test_loaded_model_predicts_probability(self):
        g = gating.GatingModel()  # charge l'artifact par défaut
        if not g.available:
            self.skipTest("artifact absent — lancer train_gating.py d'abord")
        # vecteur structurel de bonne taille
        from ml.features import structural_features
        p = g.predict_safe(structural_features("Explique la récursivité en 50 mots"))
        self.assertIsInstance(p, float)
        self.assertGreaterEqual(p, 0.0)
        self.assertLessEqual(p, 1.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Lancer le test (échec attendu)**

Run: `cd backend && ./.venv/Scripts/python.exe -m unittest tests.test_ml_gating -v`
Expected: FAIL `ModuleNotFoundError: No module named 'ml.gating'`

- [ ] **Step 3: Implémenter**

`backend/ml/gating.py` :

```python
"""Chargement du modèle de gating sérialisé + prédiction P(compression sûre).
Robuste à l'absence d'artifact (available=False -> le Combiner fera le fallback).
"""
import os
import numpy as np

try:
    import joblib
except Exception:
    joblib = None

_DEFAULT = os.path.join(os.path.dirname(__file__), "artifacts", "gating_model.joblib")


class GatingModel:
    def __init__(self, path: str = _DEFAULT):
        self.path = path
        self.model = None
        self.features = None
        if joblib is not None and os.path.exists(path):
            try:
                bundle = joblib.load(path)
                self.model = bundle["model"]
                self.features = bundle["features"]
            except Exception:
                self.model = None

    @property
    def available(self) -> bool:
        return self.model is not None

    def predict_safe(self, struct_vec: np.ndarray):
        """P(safe) in [0,1], ou None si modèle indisponible."""
        if not self.available:
            return None
        x = np.asarray(struct_vec, dtype="float32").reshape(1, -1)
        proba = self.model.predict_proba(x)[0]
        # classe 1 == "safe"
        idx = list(self.model.classes_).index(1) if 1 in self.model.classes_ else 1
        return float(proba[idx])


# singleton chargé une fois au démarrage
_INSTANCE = None

def get_model() -> "GatingModel":
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = GatingModel()
    return _INSTANCE
```

- [ ] **Step 4: Lancer le test (succès attendu)**

Run: `cd backend && ./.venv/Scripts/python.exe -m unittest tests.test_ml_gating -v`
Expected: PASS (le 2e test se skip si l'artifact n'existe pas, sinon vérifie la proba).

- [ ] **Step 5: Commit**

```bash
git add backend/ml/gating.py backend/tests/test_ml_gating.py
git commit -m "feat(ml): gating model loader + predict_safe with graceful absence"
```

---

### Task 5: Policy Combiner (décision + fallback)

**Files:**
- Create: `backend/ml/policy.py`
- Test: `backend/tests/test_ml_policy.py`

`decide_policy(prompt)` renvoie un `PolicyDecision(compress: bool, confidence: float, source: str)`.
Règle : extraire features → `predict_safe`. Si `p >= THRESHOLD` → `compress=True`. Si modèle absent **ou** embedding/features en échec → `compress=True, source="fallback_heuristique"` (comportement actuel : on applique le palier comme aujourd'hui). Seuil **conservateur** configurable.

- [ ] **Step 1: Écrire le test qui échoue**

`backend/tests/test_ml_policy.py` :

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unittest
from ml import policy


class TestPolicy(unittest.TestCase):
    def test_fallback_when_model_unavailable(self):
        # force un modèle indisponible
        d = policy.decide_policy("Explique la récursivité", model=policy._UnavailableModel())
        self.assertTrue(d.compress)               # fallback = comportement actuel (on comprime)
        self.assertEqual(d.source, "fallback")

    def test_compress_decision_respects_threshold(self):
        class FakeModel:
            available = True
            def predict_safe(self, vec):
                return 0.9
        d = policy.decide_policy("Explique", model=FakeModel(),
                                 struct_only=True, threshold=0.5)
        self.assertTrue(d.compress)
        self.assertEqual(d.source, "model")

        class FakeLow(FakeModel):
            def predict_safe(self, vec):
                return 0.2
        d2 = policy.decide_policy("Explique", model=FakeLow(),
                                  struct_only=True, threshold=0.5)
        self.assertFalse(d2.compress)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Lancer le test (échec attendu)**

Run: `cd backend && ./.venv/Scripts/python.exe -m unittest tests.test_ml_policy -v`
Expected: FAIL `ModuleNotFoundError: No module named 'ml.policy'`

- [ ] **Step 3: Implémenter**

`backend/ml/policy.py` :

```python
"""Policy Combiner : decide_policy(prompt) -> PolicyDecision.
Décide si on applique la contrainte de longueur (palier). Fallback heuristique
robuste : si modèle absent ou features indisponibles, on garde le comportement
actuel (compress=True), donc jamais de régression.
"""
from dataclasses import dataclass
from .gating import get_model
from . import features as F

THRESHOLD = 0.5   # conservateur : >=0.5 -> compresser


@dataclass
class PolicyDecision:
    compress: bool
    confidence: float
    source: str   # "model" | "fallback"


class _UnavailableModel:
    available = False
    def predict_safe(self, vec):
        return None


def decide_policy(prompt: str, model=None, threshold: float = THRESHOLD,
                  struct_only: bool = True) -> PolicyDecision:
    model = model if model is not None else get_model()
    if not getattr(model, "available", False):
        return PolicyDecision(compress=True, confidence=0.0, source="fallback")
    try:
        vec = F.structural_features(prompt) if struct_only else F.extract_features(prompt)
        p = model.predict_safe(vec)
    except F.EmbeddingUnavailable:
        return PolicyDecision(compress=True, confidence=0.0, source="fallback")
    if p is None:
        return PolicyDecision(compress=True, confidence=0.0, source="fallback")
    return PolicyDecision(compress=(p >= threshold), confidence=p, source="model")
```

> Note : `struct_only=True` par défaut car le modèle de Task 3 est entraîné sur les features structurels. Quand l'embedding sera intégré au train, passer à `struct_only=False`.

- [ ] **Step 4: Lancer le test (succès attendu)**

Run: `cd backend && ./.venv/Scripts/python.exe -m unittest tests.test_ml_policy -v`
Expected: PASS (3 assertions).

- [ ] **Step 5: Commit**

```bash
git add backend/ml/policy.py backend/tests/test_ml_policy.py
git commit -m "feat(ml): policy combiner with conservative threshold + heuristic fallback"
```

---

### Task 6: Intégrer la Policy dans `optimise()`

**Files:**
- Modify: `backend/utils/optimiseur.py` (fonction `optimise`, après `detect_palier`)
- Test: `backend/tests/test_optimiseur.py` (ajout)

Quand gating = non-sûr, on **rabaisse le palier vers `'5'`** (sans contrainte → réponse libre). Le reste du pipeline (estimation tokens, retour API) suit le palier overridé. Frontend inchangé (il applique la contrainte du palier renvoyé ; `'5'` n'a pas de contrainte).

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter à `backend/tests/test_optimiseur.py` :

```python
from unittest import mock

class TestPolicyIntegration(unittest.TestCase):
    def test_unsafe_gating_overrides_palier_to_free(self):
        from ml.policy import PolicyDecision
        with mock.patch("utils.optimiseur.decide_policy",
                        return_value=PolicyDecision(False, 0.1, "model")):
            r = _optimise("Compare en profondeur les avantages et inconvénients du nucléaire")
            self.assertEqual(r["palier"], "5")          # rabaissé
            self.assertEqual(r["gating_source"], "model")
            self.assertFalse(r["gating_compress"])

    def test_safe_gating_keeps_heuristic_palier(self):
        from ml.policy import PolicyDecision
        with mock.patch("utils.optimiseur.decide_policy",
                        return_value=PolicyDecision(True, 0.9, "model")):
            r = _optimise("Explique-moi la récursivité ?")
            self.assertNotEqual(r["palier"], "5")
            self.assertTrue(r["gating_compress"])

    def test_fallback_preserves_current_behavior(self):
        from ml.policy import PolicyDecision
        with mock.patch("utils.optimiseur.decide_policy",
                        return_value=PolicyDecision(True, 0.0, "fallback")):
            r = _optimise("Explique-moi la récursivité ?")
            self.assertEqual(r["gating_source"], "fallback")
```

- [ ] **Step 2: Lancer le test (échec attendu)**

Run: `cd backend && ./.venv/Scripts/python.exe -m unittest tests.test_optimiseur.TestPolicyIntegration -v`
Expected: FAIL (`KeyError: 'gating_source'` ou import error sur `decide_policy`).

- [ ] **Step 3: Implémenter l'intégration**

Dans `backend/utils/optimiseur.py` :

1. En haut du fichier, ajouter l'import (tolérant si le package ML n'est pas prêt) :

```python
try:
    from ml.policy import decide_policy
except Exception:
    decide_policy = None
```

2. Dans `optimise()`, **juste après** la ligne qui calcule `palier = detect_palier(...)` (≈ `optimiseur.py:1171`), insérer :

```python
    # Policy Engine : décider si on garde la contrainte de longueur
    gating_compress, gating_source, gating_conf = True, "disabled", 0.0
    if decide_policy is not None:
        try:
            decision = decide_policy(prompt)
            gating_compress = decision.compress
            gating_source = decision.source
            gating_conf = decision.confidence
            if not gating_compress:
                palier = "5"   # sans contrainte -> réponse libre
        except Exception:
            gating_compress, gating_source = True, "fallback"
```

3. Dans le dict de retour de `optimise()`, ajouter les trois clés :

```python
        "gating_compress": gating_compress,
        "gating_source": gating_source,
        "gating_confidence": gating_conf,
```

> Vérifier le nom exact de la variable palier et la structure du `return` avant d'éditer (`grep -n "detect_palier\|return {" backend/utils/optimiseur.py`).

- [ ] **Step 4: Lancer le test (succès attendu)**

Run: `cd backend && ./.venv/Scripts/python.exe -m unittest tests.test_optimiseur.TestPolicyIntegration -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Non-régression complète**

Run: `cd backend && ./.venv/Scripts/python.exe -m unittest discover tests -v`
Expected: tous les tests existants + nouveaux PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/utils/optimiseur.py backend/tests/test_optimiseur.py
git commit -m "feat(ml): integrate gating into optimise() with palier override + fallback"
```

---

### Task 7: Vérification bout-en-bout (frontière coût/qualité)

**Files:**
- Create: `analysis/ml/eval_gating_policy.py`
- Output: rapport console (before/after)

Mesure : sur les prompts du dataset, comparer **compression aveugle** (palier toujours appliqué) vs **gating** (palier seulement si modèle dit sûr). Critères de succès (spec §7) : sur le sous-ensemble "compresser", non-dégradation > 90% (vs ~55% aveugle), gain coût ≈ préservé.

- [ ] **Step 1: Écrire le script d'évaluation**

`analysis/ml/eval_gating_policy.py` :

```python
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
ABC = json.load(open(os.path.join(QM, "smoke45_abc.json"), encoding="utf-8"))
V14 = {v["id"]: v for v in json.load(open(os.path.join(QM, "qm_abc_verdicts_qwen14b.json"), encoding="utf-8"))["verdicts"]}

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
print("→ objectif spec : gating > 90% de non-dégradation sur ce qu'il comprime")
```

> ⚠️ Sur le **smoke (45)**, ces chiffres sont indicatifs et le modèle est entraîné/évalué sur des données qui se recouvrent — c'est une **vérification de chaîne**, pas une preuve. La preuve défendable exige : (1) run QM complet sur 458, (2) split train/test propre. À logger explicitement dans le rapport de démo.

- [ ] **Step 2: Lancer l'évaluation**

Run: `cd backend && ./.venv/Scripts/python.exe ../analysis/ml/eval_gating_policy.py`
Expected: deux lignes AVEUGLE / GATING avec un % de non-dégradation plus haut pour GATING.

- [ ] **Step 3: Commit**

```bash
git add analysis/ml/eval_gating_policy.py
git commit -m "feat(ml): end-to-end gating vs blind-compression evaluation"
```

---

## Notes de séquencement (incréments suivants, hors ce plan)

- **Données défendables** : relancer `qm_run_abc.py` + `qm_evaluate_abc.py` sur les 458 prompts (`input_delta_QM.json`) puis re-`build_gating_dataset` + `train_gating` → vrais chiffres train/test.
- **Embedding au train** : passer `struct_only=False` une fois le dataset reconstruit avec `extract_features` (768+8).
- **Plan 2** : Output regressor (label `eval_count`). **Plan 3** : Routing appris. **Plan 4** : Dashboard frontière coût/qualité.

## Self-review (effectué)
- Couverture spec : Feature Extractor (T1), Gating model (T3/T4), Combiner+fallback (T5), intégration pipeline (T6), labeling (T2), vérif coût/qualité (T7). Output regressor & routing = plans séparés (décomposition annoncée). ✔
- Pas de placeholder : code complet à chaque step. ✔
- Cohérence types : `PolicyDecision(compress, confidence, source)`, `structural_features`/`STRUCTURAL_NAMES`/`N_STRUCTURAL`, `GatingModel.available`/`predict_safe`, `decide_policy` — noms constants à travers les tâches. ✔
- Risque assumé loggé : taille smoke, recouvrement train/éval, fallback partout. ✔
