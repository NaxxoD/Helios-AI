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
        # classe 1 == "safe" ; si absente du modèle (artifact incompatible),
        # on renvoie None pour forcer le fallback du Combiner plutôt qu'un index aveugle.
        classes = list(self.model.classes_)
        if 1 not in classes:
            return None
        return float(proba[classes.index(1)])


# singleton chargé une fois au démarrage
_INSTANCE = None

def get_model() -> "GatingModel":
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = GatingModel()
    return _INSTANCE
