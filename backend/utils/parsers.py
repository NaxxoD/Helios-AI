import json
import re as _re

from utils.calculator import estimate_tokens_from_text as _estimate_tokens

# ── Détection de modèle (conservative — signaux forts uniquement) ──

_PROVIDER_PATTERNS = [
    (_re.compile(r'\b(chatgpt|gpt[-\s]?\d|openai)\b', _re.I), 'chatgpt'),
    (_re.compile(r'\bclaude\b',                         _re.I), 'claude'),
    (_re.compile(r'\bgemini\b',                         _re.I), 'gemini'),
    (_re.compile(r'\bmistral\b',                        _re.I), 'mistral'),
    (_re.compile(r'\bgrok\b',                           _re.I), 'grok'),
]

_MODEL_PATTERNS = [
    (_re.compile(r'gpt-4o-mini',              _re.I), 'chatgpt',   'gpt-4o-mini'),
    (_re.compile(r'gpt-4o\b',                 _re.I), 'chatgpt',   'gpt-4o'),
    (_re.compile(r'gpt-4-1\b',                _re.I), 'chatgpt',   'gpt-4-1'),
    (_re.compile(r'gpt-4\b',                  _re.I), 'chatgpt',   'gpt-4'),
    (_re.compile(r'gpt-3\.5-turbo',           _re.I), 'chatgpt',   'gpt-3.5-turbo'),
    (_re.compile(r'claude-opus-4',            _re.I), 'claude',    'claude-opus-4'),
    (_re.compile(r'claude-sonnet-4',          _re.I), 'claude',    'claude-sonnet-4-6'),
    (_re.compile(r'claude-haiku-4',           _re.I), 'claude',    'claude-haiku-4-5-20251001'),
    (_re.compile(r'claude-3-5-sonnet',        _re.I), 'claude',    'claude-3-5-sonnet'),
    (_re.compile(r'claude-3-opus',            _re.I), 'claude',    'claude-3-opus'),
    (_re.compile(r'gemini-2\.5-flash',        _re.I), 'gemini',    'gemini-2.5-flash'),
    (_re.compile(r'gemini-2\.5-pro',          _re.I), 'gemini',    'gemini-2.5-pro'),
    (_re.compile(r'gemini-1\.5-pro',          _re.I), 'gemini',    'gemini-1.5-pro'),
    (_re.compile(r'mistral-large',            _re.I), 'mistral',   'mistral-large'),
    (_re.compile(r'mistral-small',            _re.I), 'mistral',   'mistral-small'),
    (_re.compile(r'grok-3-mini',              _re.I), 'grok',      'grok-3-mini'),
    (_re.compile(r'grok-3\b',                 _re.I), 'grok',      'grok-3'),
]


def detect_model_from_content(text: str) -> dict:
    """Détection conservative : JSON structure + 3 premières lignes uniquement."""
    try:
        data = json.loads(text.strip())
        model_str = ''
        if isinstance(data, dict):
            model_str = str(data.get('model', '') or data.get('model_slug', ''))
        elif isinstance(data, list) and data and isinstance(data[0], dict):
            model_str = str(data[0].get('model', ''))
        if model_str:
            for pattern, provider, model in _MODEL_PATTERNS:
                if pattern.search(model_str):
                    return {"provider": provider, "model": model, "confidence": "full"}
            for pattern, provider in _PROVIDER_PATTERNS:
                if pattern.search(model_str):
                    return {"provider": provider, "model": None, "confidence": "provider_only"}
    except Exception:
        pass

    header = '\n'.join(text.splitlines()[:3])
    for pattern, provider, model in _MODEL_PATTERNS:
        if pattern.search(header):
            return {"provider": provider, "model": model, "confidence": "full"}
    for pattern, provider in _PROVIDER_PATTERNS:
        if pattern.search(header):
            return {"provider": provider, "model": None, "confidence": "provider_only"}

    return {"provider": None, "model": None, "confidence": "none"}


# ── Calcul d'impact ──

CHAR_PER_TOKEN = {'fr': 3.5, 'en': 4.0}
_MINUTES_PER_KWH = 60 / (1700 / 6000)  # Infomaniak D4 : 1,7 MW → 6 000 logements BBC

# Un token de sortie nécessite un forward pass complet (autoregressif)
# vs tokens d'entrée traités en parallèle — ratio standard de la littérature
OUTPUT_TOKEN_WEIGHT = 5

CO2_RESEAU_CHALEUR_KG_KWH  = 0.113
KWH_LOGEMENT_BBC_PAR_HEURE = 0.400
KWH_APPART_MOYEN_PAR_HEURE = 1.940


def count_tokens_from_text(text: str, langue: str = 'fr') -> int:
    cleaned = ' '.join(text.split())
    ratio = CHAR_PER_TOKEN.get(langue, 4.0)
    return int(len(cleaned) / ratio)


def estimate_turns(total_tokens: int) -> int:
    return max(1, total_tokens // 500)


# NB : le calcul d'impact (calculate_impact) vit dans utils/calculator.py — source unique.
# L'ancienne copie ici (schéma de clés incompatible avec session_repo) a été retirée.


def calculate_helios_equivalences(kwh: float) -> dict:
    return {
        'co2_evite':           round(kwh * CO2_RESEAU_CHALEUR_KG_KWH, 6),
        'heures_logement_bbc': round(kwh / KWH_LOGEMENT_BBC_PAR_HEURE, 4),
        'heures_appart_moyen': round(kwh / KWH_APPART_MOYEN_PAR_HEURE, 4),
        'mwh':                 round(kwh / 1000, 8),
    }


def format_energie(kwh: float) -> str:
    if kwh < 0.001:
        return f"{round(kwh * 1_000_000, 2)} mWh"
    elif kwh < 1:
        return f"{round(kwh * 1000, 1)} Wh"
    return f"{round(kwh, 2)} kWh"


def format_co2(kg: float) -> str:
    if kg < 1:
        return f"{round(kg * 1000, 1)} g CO₂"
    return f"{round(kg, 2)} kg CO₂"


def format_duree(heures: float) -> str:
    secondes = heures * 3600
    minutes  = heures * 60
    if secondes < 60:
        return f"{round(secondes, 1)} sec"
    elif minutes < 60:
        return f"{round(minutes, 1)} min"
    elif heures < 24:
        h = int(heures)
        m = int((heures - h) * 60)
        return f"{h}h {m}min" if m > 0 else f"{h}h"
    return f"{round(heures / 24, 1)} jours"


def parse_conversation(content, provider, is_file=False):
    """
    Parse une conversation depuis du texte ou un fichier JSON exporté.
    Retourne : {name, provider, nb_turns, tokens_estimated}
    """
    if is_file:
        try:
            data = json.loads(content)
            if provider == 'OpenAI':
                return _parse_chatgpt_json(data)
            elif provider == 'Anthropic':
                return _parse_claude_json(data)
        except (json.JSONDecodeError, KeyError, TypeError):
            pass  # Fallback vers le parsing texte

    return _parse_plain_text(content, provider)


def _parse_chatgpt_json(data):
    """Parse le format d'export JSON de ChatGPT (conversations.json)."""
    conv = data[0] if isinstance(data, list) and data else (data if isinstance(data, dict) else {})
    name = conv.get('title', 'Conversation ChatGPT')

    nb_turns = 0
    user_text = []
    assistant_text = []
    for node in conv.get('mapping', {}).values():
        msg = node.get('message')
        if not msg:
            continue
        role = msg.get('author', {}).get('role', '')
        parts = msg.get('content', {}).get('parts', [])
        text = ' '.join(str(p) for p in parts if isinstance(p, str))
        if not text.strip():
            continue
        if role == 'user':
            nb_turns += 1
            user_text.append(text)
        elif role == 'assistant':
            assistant_text.append(text)

    tokens_input  = _estimate_tokens(' '.join(user_text))
    tokens_output = _estimate_tokens(' '.join(assistant_text))
    return {
        'name': name,
        'provider': 'OpenAI',
        'nb_turns': max(nb_turns, 1),
        'tokens_estimated': tokens_input + tokens_output * OUTPUT_TOKEN_WEIGHT,
    }


def _parse_claude_json(data):
    """Parse le format d'export JSON de Claude (claude.ai)."""
    conv = data[0] if isinstance(data, list) and data else (data if isinstance(data, dict) else {})
    name = conv.get('name', 'Conversation Claude')

    nb_turns = 0
    user_text = []
    assistant_text = []
    for msg in conv.get('messages', []):
        text = msg.get('text') or ''
        if not text.strip():
            continue
        if msg.get('sender') == 'human':
            nb_turns += 1
            user_text.append(text)
        else:
            assistant_text.append(text)

    tokens_input  = _estimate_tokens(' '.join(user_text))
    tokens_output = _estimate_tokens(' '.join(assistant_text))
    return {
        'name': name,
        'provider': 'Anthropic',
        'nb_turns': max(nb_turns, 1),
        'tokens_estimated': tokens_input + tokens_output * OUTPUT_TOKEN_WEIGHT,
    }


def _parse_plain_text(text, provider):
    """Fallback : estimation depuis un texte brut collé."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # Détection des marqueurs de locuteur
    user_markers = ('vous:', 'user:', 'human:', 'toi:', 'moi:', 'you:')
    nb_turns = sum(
        1 for line in lines
        if any(line.lower().startswith(m) for m in user_markers)
    )

    if nb_turns == 0:
        # Estimation : paragraphes alternés, moitié = tours utilisateur
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        nb_turns = max(1, len(paragraphs) // 2)
        # Sans séparation rôles détectable : hypothèse 50/50 input/output
        total = _estimate_tokens(text)
        half  = total // 2
        tokens_weighted = half + half * OUTPUT_TOKEN_WEIGHT
    else:
        # Marqueurs détectés : on sépare user / assistant ligne par ligne
        user_lines      = [l for l in lines if any(l.lower().startswith(m) for m in user_markers)]
        assistant_lines = [l for l in lines if not any(l.lower().startswith(m) for m in user_markers)]
        tokens_input    = _estimate_tokens(' '.join(user_lines))
        tokens_output   = _estimate_tokens(' '.join(assistant_lines))
        tokens_weighted = tokens_input + tokens_output * OUTPUT_TOKEN_WEIGHT

    return {
        'name': 'Session importée',
        'provider': provider,
        'nb_turns': nb_turns,
        'tokens_estimated': tokens_weighted,
    }
