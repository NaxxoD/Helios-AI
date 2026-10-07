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
