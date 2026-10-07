"""Couche ML Helios : Policy Engine (gating de compression).

API publique : decide_policy(prompt) -> PolicyDecision

L'import est tolérant : pendant le build incrémental, `policy` peut ne pas
encore exister. On n'empêche pas l'import du package (ni de ses sous-modules
comme `ml.features`) tant que la pièce manque.
"""
try:  # pragma: no cover - dépend de l'avancement du build
    from .policy import decide_policy, PolicyDecision  # noqa: F401
except Exception:  # policy.py pas encore présent (T5)
    decide_policy = None
    PolicyDecision = None
