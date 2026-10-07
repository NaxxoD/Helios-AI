"""Objet Helios — format pivot générique d'un appel LLM, indépendant du provider.

Mappé vers chaque API (OpenAI / Anthropic / Google) par services/chat_service.py
(_assemble_system + _EFFORT_MAP + _ANTHROPIC_IDS/_GOOGLE_IDS). C'est la matérialisation
du « {message, effort, role, context} » du schéma d'architecture cible.
"""
from typing import Optional

from pydantic import BaseModel


class HeliosMessage(BaseModel):
    role: str        # "user" | "assistant" | "system"
    content: str


class HeliosCall(BaseModel):
    """Représentation générique d'un échange, avant mapping provider.

    - role    : persona / système, first-class (ex. « Tu es un expert Python. »)
    - context : contexte additionnel injecté, first-class (ex. résumé mémoire — Jalon 3)
    - effort  : off|on|low|standard|medium|high|xhigh|max → budget de raisonnement
    - palier  : contrainte de longueur de sortie (★..6)

    L'api_key n'est volontairement PAS dans l'objet (secret transporté séparément).
    """
    provider: str
    model: str
    messages: list[HeliosMessage]
    effort: Optional[str] = None
    palier: Optional[str] = None
    role: Optional[str] = None
    context: Optional[str] = None
