# Prix en $ par million de tokens (source : pages de tarification officielles — mai 2026)
PRICING = {
    "OpenAI": {
        # ── Modèles actuels (workflows, n8n, intégrations existantes) ──
        "gpt-4o":        {"input": 2.50,  "output": 10.00},
        "gpt-4o-mini":   {"input": 0.15,  "output": 0.60},
        "gpt-4-1":       {"input": 2.00,  "output": 8.00},
        "gpt-4.1":       {"input": 2.00,  "output": 8.00},
        "gpt-4.1-nano":  {"input": 0.10,  "output": 0.40},
        "o1":            {"input": 15.00, "output": 60.00},
        "o1-mini":       {"input": 3.00,  "output": 12.00},
        "o3":            {"input": 10.00, "output": 40.00},
        "o3-mini":       {"input": 1.10,  "output": 4.40},
        # ── GPT-5.x — nouveaux modèles (IDs à vérifier avec doc OpenAI) ──
        "gpt-5":         {"input": 1.25,  "output": 10.00},
        "gpt-5-mini":    {"input": 0.25,  "output":  2.00},
        "gpt-5-nano":    {"input": 0.05,  "output":  0.40},
        "gpt-5.4":       {"input": 2.50,  "output": 15.00},
        "gpt-5.4-mini":  {"input": 0.75,  "output":  4.50},
        "gpt-5.4-nano":  {"input": 0.20,  "output":  1.25},
        "gpt-5.4-pro":   {"input": 30.00, "output": 180.00},
        "gpt-5.5":       {"input": 5.00,  "output": 30.00},
        "gpt-5.5-pro":   {"input": 30.00, "output": 180.00},
    },
    "Anthropic": {
        # Source : docs.anthropic.com/en/docs/about-claude/models — juin 2026
        "claude-opus-4-8":   {"input": 15.00, "output": 75.00},
        "claude-opus-4-7":   {"input":  5.00, "output": 25.00},
        "claude-sonnet-4-6": {"input":  3.00, "output": 15.00},
        "claude-haiku-4-5":  {"input":  1.00, "output":  5.00},
    },
    "Meta": {
        # Source : docs.together.ai / Groq — juin 2026
        "llama-3-3-70b":     {"input":  0.59, "output":  0.79},
        "llama-3-1-8b":      {"input":  0.10, "output":  0.10},
        "llama-3-1-70b":     {"input":  0.59, "output":  0.79},
        "llama-3-1-405b":    {"input":  3.50, "output":  3.50},
    },
    "Mistral": {
        # Source : mistral.ai/technology/#pricing — juin 2026
        "mistral-large":     {"input":  2.00, "output":  6.00},
        "mistral-small":     {"input":  0.10, "output":  0.30},
        "mistral-nemo":      {"input":  0.15, "output":  0.15},
        "codestral":         {"input":  0.20, "output":  0.60},
    },
    "Google": {
        # ── Gemini 2.x — modèles actuels ──
        "gemini-2-5-pro":        {"input": 1.25, "output": 10.00},
        "gemini-2-5-flash":      {"input": 0.30, "output":  2.50},
        "gemini-2-5-flash-lite": {"input": 0.10, "output":  0.40},
        "gemini-2-0-flash":      {"input": 0.10, "output":  0.40},
        # ── Gemini 3.x — source : ai.google.dev/gemini-api/docs/models ──
        "gemini-3-5-flash":      {"input": 0.15, "output":  0.60},  # stable
        "gemini-3-1-flash-lite": {"input": 0.10, "output":  0.40},  # stable
        "gemini-3-1-pro":        {"input": 2.00, "output": 12.00},  # preview
        "gemini-3-flash":        {"input": 0.50, "output":  3.00},  # preview
    },
}


def calculate_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> dict:
    """Retourne le coût en $ de l'échange. Renvoie None si le modèle est inconnu."""
    import logging
    rates = PRICING.get(provider, {}).get(model)
    if not rates:
        logging.warning("cost_calculator: pricing manquant pour %s / %s", provider, model)
        return {"cost_usd": None, "input_cost_usd": None, "output_cost_usd": None}

    input_cost  = (input_tokens  / 1_000_000) * rates["input"]
    output_cost = (output_tokens / 1_000_000) * rates["output"]
    return {
        "cost_usd":        round(input_cost + output_cost, 6),
        "input_cost_usd":  round(input_cost, 6),
        "output_cost_usd": round(output_cost, 6),
    }


def calculate_savings(provider: str, model: str, tokens_saved: int) -> float | None:
    """Coût évité grâce à l'optimisation du prompt (tokens input économisés)."""
    rates = PRICING.get(provider, {}).get(model)
    if not rates or tokens_saved <= 0:
        return None
    return round((tokens_saved / 1_000_000) * rates["input"], 6)
