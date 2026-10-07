import logging

import httpx
from fastapi import HTTPException
from typing import Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Calibration par palier (basée sur Pyramide_Pertinence_Détail_v2.md)
# ---------------------------------------------------------------------------

_PALIER_MAX_TOKENS = {
    '★': 90,  '0': 120, '1': 160, '2': 200,
    '3': 240, '4': 290, '5': 8192, 'C': 4096, '6': 8192,
}

_PALIER_SYSTEM = {
    '★': 'Réponds en 50 mots maximum.',
    '0': 'Réponds en 60 mots maximum.',
    '1': 'Réponds en 85 mots maximum.',
    '2': 'Réponds en 115 mots maximum.',
    '3': 'Réponds en 140 mots maximum.',
    '4': 'Réponds en 165 mots maximum.',
    '5': None,
    'C': 'Code uniquement. Commentaires minimalistes.',
    '6': None,
}

_PALIER_TEMPERATURE = {
    '★': 0.2, '0': 0.3, '1': 0.4, '2': 0.5,
    '3': 0.6, '4': 0.7, '5': 0.8, 'C': 0.1, '6': 0.65,
}


def _system_from_palier(palier: str | None) -> str | None:
    if not palier:
        return None
    return _PALIER_SYSTEM.get(palier)


def _max_tokens_from_palier(palier: str | None, thinking_budget: int = 0) -> int:
    ceiling = _PALIER_MAX_TOKENS.get(palier, 8192) if palier else 8192
    return ceiling + thinking_budget if thinking_budget > 0 else ceiling


def _temperature_from_palier(palier: str | None, thinking_budget: int = 0) -> float:
    if thinking_budget > 0:
        return 1.0  # Anthropic exige temperature=1 quand thinking activé
    return _PALIER_TEMPERATURE.get(palier, 0.7) if palier else 0.7


def _assemble_system(role: str | None, context: str | None,
                     palier: str | None) -> str | None:
    """Assemble le system prompt depuis les champs Helios first-class.
    Ordre : role (persona) → context (situation / mémoire de session) → contrainte de palier.
    Renvoie None si aucun n'est fourni (comportement identique à _system_from_palier seul)."""
    parts = []
    if role and role.strip():
        parts.append(role.strip())
    if context and context.strip():
        parts.append(context.strip())
    palier_sys = _system_from_palier(palier)
    if palier_sys:
        parts.append(palier_sys)
    return "\n\n".join(parts) if parts else None


# Effort → paramètres API réels par provider
# Anthropic : budget_tokens (0 = thinking désactivé)
# OpenAI    : reasoning_effort "low"|"medium"|"high" (o-series uniquement)
# Google    : thinkingBudget (0 = pas de thinkingConfig)
_EFFORT_MAP = {
    "off":      {"anthropic": 0,     "openai": None,     "google": 0},
    "on":       {"anthropic": 5000,  "openai": "medium", "google": 5000},  # alias générique « activé »
    "low":      {"anthropic": 1024,  "openai": "low",    "google": 1024},
    "standard": {"anthropic": 5000,  "openai": "medium", "google": 5000},
    "medium":   {"anthropic": 5000,  "openai": "medium", "google": 5000},
    "high":     {"anthropic": 16000, "openai": "high",   "google": 16000},
    "xhigh":    {"anthropic": 32000, "openai": "high",   "google": 32000},
    "max":      {"anthropic": 64000, "openai": "high",   "google": 32000},
}

# Modèles OpenAI qui supportent reasoning_effort
_OPENAI_REASONING_MODELS = {"o1", "o1-mini", "o3", "o3-mini", "o4-mini"}

# Mapping noms internes → IDs API réels
_ANTHROPIC_IDS = {
    "claude-opus-4-8":   "claude-opus-4-8",
    "claude-opus-4-7":   "claude-opus-4-7",
    "claude-sonnet-4-6": "claude-sonnet-4-6",
    "claude-haiku-4-5":  "claude-haiku-4-5-20251001",
}
_GOOGLE_IDS = {
    # Gemini 2.x — stable (source : ai.google.dev/gemini-api/docs/models)
    "gemini-2-5-pro":        "gemini-2.5-pro",
    "gemini-2-5-flash":      "gemini-2.5-flash",
    "gemini-2-5-flash-lite": "gemini-2.5-flash-lite",
    "gemini-2-0-flash":      "gemini-2.0-flash",
    # Gemini 3.x — IDs API vérifiés
    "gemini-3-5-flash":      "gemini-3.5-flash",           # stable
    "gemini-3-1-flash-lite": "gemini-3.1-flash-lite",      # stable
    "gemini-3-1-pro":        "gemini-3.1-pro-preview",     # preview
    "gemini-3-flash":        "gemini-3-flash-preview",     # preview
}


async def call_llm(provider: str, model: str, api_key: str, messages: list,
                   effort: Optional[str] = None,
                   palier: Optional[str] = None,
                   role: Optional[str] = None,
                   context: Optional[str] = None) -> dict:
    if effort and effort not in _EFFORT_MAP:
        log.warning("[chat] effort inconnu '%s' — réflexion désactivée (valides : %s)",
                    effort, sorted(_EFFORT_MAP))
    params = _EFFORT_MAP.get(effort, {}) if effort else {}
    try:
        if provider == "OpenAI":
            return await _openai(model, api_key, messages, params, palier, role, context)
        elif provider == "Anthropic":
            return await _anthropic(model, api_key, messages, params, palier, role, context)
        elif provider == "Google":
            return await _google(model, api_key, messages, params, palier, role, context)
        else:
            raise HTTPException(400, f"Provider non supporté : {provider}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Erreur API {provider} : {e}")


async def call_helios(call, api_key: str) -> dict:
    """Exécute un HeliosCall (format pivot {message, effort, role, context}) en le mappant
    vers le provider cible. api_key passée à part (secret, hors de l'objet)."""
    return await call_llm(
        call.provider, call.model, api_key,
        [{"role": m.role, "content": m.content} for m in call.messages],
        effort=call.effort, palier=call.palier, role=call.role, context=call.context,
    )


async def _openai(model: str, api_key: str, messages: list, params: dict,
                  palier: Optional[str] = None,
                  role: Optional[str] = None, context: Optional[str] = None) -> dict:
    system_text = _assemble_system(role, context, palier)
    temperature = _temperature_from_palier(palier)
    max_tokens  = _max_tokens_from_palier(palier)

    body_messages = messages
    if system_text:
        body_messages = [{"role": "system", "content": system_text}] + messages

    body: dict = {"model": model, "messages": body_messages}
    if model in _OPENAI_REASONING_MODELS:
        # o-series : exige max_completion_tokens (pas max_tokens) et n'accepte que
        # temperature=1 (défaut) → on l'omet. Envoyer max_tokens/temperature≠1 = 400.
        body["max_completion_tokens"] = max_tokens
        reasoning_effort = params.get("openai")
        if reasoning_effort:
            body["reasoning_effort"] = reasoning_effort
    else:
        body["max_tokens"]  = max_tokens
        body["temperature"] = temperature

    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=body,
        )
    if r.status_code != 200:
        msg = r.json().get("error", {}).get("message", r.text) if r.content else r.text
        raise HTTPException(r.status_code, f"OpenAI : {msg}")
    data = r.json()
    choices = data.get("choices") or []
    if not choices:
        raise HTTPException(502, "OpenAI : réponse vide (aucun choix retourné)")
    usage = data.get("usage", {})
    return {
        "content":       (choices[0].get("message") or {}).get("content") or "",
        "input_tokens":  usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
    }


async def _anthropic(model: str, api_key: str, messages: list, params: dict,
                     palier: Optional[str] = None,
                     role: Optional[str] = None, context: Optional[str] = None) -> dict:
    api_model   = _ANTHROPIC_IDS.get(model, model)
    budget      = params.get("anthropic", 0)
    max_tokens  = _max_tokens_from_palier(palier, budget)
    temperature = _temperature_from_palier(palier, budget)
    system_text = _assemble_system(role, context, palier)

    body: dict = {"model": api_model, "max_tokens": max_tokens,
                  "messages": messages, "temperature": temperature}
    if system_text:
        body["system"] = [{"type": "text", "text": system_text}]
    if budget > 0:
        body["thinking"] = {"type": "enabled", "budget_tokens": budget}

    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=body,
        )
    if r.status_code != 200:
        msg = r.json().get("error", {}).get("message", r.text) if r.content else r.text
        raise HTTPException(r.status_code, f"Anthropic : {msg}")
    data = r.json()
    text_block = next((b.get("text", "") for b in data.get("content", [])
                       if b.get("type") == "text"), "")
    usage = data.get("usage", {})
    return {
        "content":         text_block,
        "input_tokens":    usage.get("input_tokens", 0),
        "output_tokens":   usage.get("output_tokens", 0),
        # Anthropic n'expose pas de compteur de raisonnement séparé (déjà inclus dans output_tokens).
        "thinking_tokens": 0,
    }


async def _google(model: str, api_key: str, messages: list, params: dict,
                  palier: Optional[str] = None,
                  role: Optional[str] = None, context: Optional[str] = None) -> dict:
    api_model       = _GOOGLE_IDS.get(model, model)
    system_text     = _assemble_system(role, context, palier)
    temperature     = _temperature_from_palier(palier)
    thinking_budget = params.get("google", 0)
    # maxOutputTokens est le plafond TOTAL (réflexion incluse) chez Gemini : il DOIT
    # couvrir le thinking_budget, sinon la réflexion épuise la sortie → réponse vide.
    max_out_tokens  = _max_tokens_from_palier(palier, thinking_budget)

    contents = [
        {"role": "user" if m["role"] == "user" else "model",
         "parts": [{"text": m["content"]}]}
        for m in messages
    ]
    body: dict = {"contents": contents}

    gen_config: dict = {"maxOutputTokens": max_out_tokens, "temperature": temperature}
    if thinking_budget > 0:
        gen_config["thinkingConfig"] = {"thinkingBudget": thinking_budget}
    body["generationConfig"] = gen_config

    if system_text:
        body["systemInstruction"] = {"parts": [{"text": system_text}]}

    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{api_model}:generateContent",
            params={"key": api_key},
            json=body,
        )
    if r.status_code != 200:
        msg = r.json().get("error", {}).get("message", r.text) if r.content else r.text
        raise HTTPException(r.status_code, f"Google : {msg}")
    data = r.json()
    candidates = data.get("candidates") or []
    if not candidates:
        reason = (data.get("promptFeedback") or {}).get("blockReason", "aucun candidat")
        raise HTTPException(502, f"Google : réponse vide ({reason})")
    parts = ((candidates[0].get("content") or {}).get("parts")) or []
    content = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
    meta = data.get("usageMetadata", {})
    return {
        "content":         content,
        "input_tokens":    meta.get("promptTokenCount", 0),
        "output_tokens":   meta.get("candidatesTokenCount", 0),
        "thinking_tokens": meta.get("thoughtsTokenCount", 0),
    }
