"""
quality_gates — Couche 1 de la grille de qualité (docs/recherche/grille-qualite-helios.md §3).

Gates MÉCANIQUES déterministes : pass/fail calculé sans LLM (κ=1, zéro coût,
zéro bruit). Un seul gate "dur" qui saute = réponse mauvaise.

Une SEULE source de vérité, deux agrégations selon le contexte :
  - LIVE (router cheap-first)  : needs_escalation(réponse) → escalade premium
    si N'IMPORTE quel gate dur saute (le seul contrôle qualité en prod, sans juge).
  - OFFLINE (éval Couche 2)    : on n'exclut QUE l'INJUGEABLE (troncature/vide/
    erreur) — un refus ou une boucle de la candidate est une vraie dégradation
    qu'on VEUT laisser le juge mesurer, pas exclure (cf. is_unjudgeable()).

Tout est pur et déterministe → testable sans réseau. La détection de langue est
INJECTABLE (detect_lang) pour ne pas imposer de dépendance dure.
"""
from __future__ import annotations
import json, re
from typing import Callable, Optional

# Patterns de refus FR + EN, volontairement restrictifs. Le lookahead négatif
# évite les faux positifs courants ("je ne peux pas GARANTIR" n'est pas un refus).
_REFUS = re.compile(
    r"(je ne peux pas(?!\s+(?:garantir|assurer|certifier|promettre|exclure))"
    r"|je ne suis pas en mesure|je n'?ai pas accès"
    r"|en tant qu'?(?:ia|intelligence artificielle)"
    r"|i can'?t help|i cannot help|i'?m unable to|i am unable to|as an ai)",
    re.IGNORECASE,
)


def text_of(resp) -> str:
    """Texte d'une réponse, tolérant aux formats (content / text / str brut)."""
    if isinstance(resp, dict):
        return resp.get("content") or resp.get("text") or ""
    return resp or ""


# --------------------------------------------------------------------------
# Gates individuels (purs)
# --------------------------------------------------------------------------

def is_empty(text: str, min_chars: int = 10) -> bool:
    return len(text.strip()) < min_chars


def is_refusal(text: str, head_chars: int = 120, max_total: int = 250) -> bool:
    """Refus RÉEL et court en tête. Une longue réponse utile contenant 'je ne peux
    pas X' enfoui n'est PAS un refus → garde-fous longueur + position."""
    t = text.strip()
    if len(t) > max_total:
        return False
    return bool(_REFUS.search(t[:head_chars]))


def is_truncated(meta, ratio: float = 0.95) -> bool:
    """finish_reason == 'length', flag explicite (truncated/trunc), ou
    output >= 95% du plafond (max_tokens/num_predict)."""
    if not isinstance(meta, dict):
        return False
    if meta.get("truncated") or meta.get("trunc"):
        return True
    if meta.get("finish_reason") == "length":
        return True
    out = meta.get("output_tokens") or meta.get("out")
    mx = meta.get("max_tokens") or meta.get("num_predict")
    if out and mx:
        try:
            return float(out) >= ratio * float(mx)
        except (TypeError, ValueError):
            return False
    return False


def repetition_ratio(text: str) -> float:
    """Mots uniques / total (1.0 = aucun doublon, bas = radotage)."""
    words = re.findall(r"\w+", text.lower())
    return len(set(words)) / len(words) if words else 1.0


def is_degenerate_repetition(text: str, min_words: int = 40, seuil: float = 0.55) -> bool:
    """Boucle dégénérée. Ignoré sous min_words (ratio instable sur le court)."""
    words = re.findall(r"\w+", text.lower())
    if len(words) < min_words:
        return False
    return (len(set(words)) / len(words)) < seuil


def bad_format(text: str, expected: Optional[str]) -> bool:
    """Format structuré demandé mais cassé (JSON invalide)."""
    if expected != "json":
        return False
    m = re.search(r"[\{\[].*[\}\]]", text, re.DOTALL)
    if not m:
        return True
    try:
        json.loads(m.group(0))
        return False
    except Exception:
        return True


def wrong_language(text: str, expected: Optional[str],
                   detect_lang: Optional[Callable[[str], str]] = None,
                   min_chars: int = 40) -> bool:
    """Mauvaise langue. DÉSACTIVÉ sans détecteur injecté ou texte trop court."""
    if not expected or detect_lang is None or len(text.strip()) < min_chars:
        return False
    try:
        return detect_lang(text) != expected
    except Exception:
        return False


def word_count(text: str) -> int:
    return len(re.findall(r"\w+", text))


def over_length(text: str, max_words: Optional[int], tol: float = 1.3) -> bool:
    """Dépasse la cible de mots du palier (DRAPEAU, pas un échec dur)."""
    if not max_words:
        return False
    return word_count(text) > tol * max_words


# --------------------------------------------------------------------------
# Agrégations
# --------------------------------------------------------------------------

def needs_escalation(resp, *, expected_lang: Optional[str] = None,
                     expected_format: Optional[str] = None,
                     max_words: Optional[int] = None,
                     detect_lang: Optional[Callable[[str], str]] = None) -> tuple[bool, str]:
    """LIVE cheap-first : (escalade?, motif). Tout gate dur déclenche l'escalade ;
    la longueur n'est qu'un drapeau (n'escalade pas seule)."""
    text = text_of(resp)
    meta = resp if isinstance(resp, dict) else {}

    if meta.get("error"):
        return True, "erreur"
    if is_empty(text):
        return True, "vide"
    if is_truncated(meta):
        return True, "troncature"
    if is_refusal(text):
        return True, "refus"
    if is_degenerate_repetition(text):
        return True, "repetition"
    if wrong_language(text, expected_lang, detect_lang):
        return True, "langue"
    if bad_format(text, expected_format):
        return True, "format"
    if over_length(text, max_words):
        return False, "flag:longueur"
    return False, "ok"


def is_unjudgeable(resp) -> bool:
    """OFFLINE : la réponse est-elle INJUGEABLE (à exclure de l'éval) ? On exclut
    seulement vide / erreur / troncature — PAS les refus/boucles, qui sont de
    vraies dégradations à laisser mesurer par le juge Couche 2."""
    text = text_of(resp)
    meta = resp if isinstance(resp, dict) else {}
    return bool(meta.get("error")) or is_empty(text) or is_truncated(meta)
