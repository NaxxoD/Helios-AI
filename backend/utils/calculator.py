# Référence Infomaniak D4 : 1,7 MW de chaleur fatale → 6 000 logements BBC
# Puissance par logement = 1700 / 6000 = 0,2833 kW
# 1 kWh chauffe 1 logement pendant : 1 / 0,2833 h = 3,53 h = 212 minutes
_POWER_PER_HOME_KW = 1700 / 6000
MINUTES_PER_KWH = 60 / _POWER_PER_HOME_KW  # ≈ 212 min/kWh

# Douche moyenne : 8 min, 40 L, ΔT = 25°C → Q = 40 * 4186 * 25 / 3_600_000 ≈ 1,16 kWh
KWH_PER_SHOWER = 1.16

# Facteurs par défaut si le modèle n'est pas en base
DEFAULT_KWH_PER_TOKEN = 0.000001     # 1 µWh/token
DEFAULT_CO2_STANDARD = 0.4           # kg CO2/kWh (mix mondial moyen)
DEFAULT_CO2_ETHICAL = 0.015          # kg CO2/kWh (Infomaniak renouvelable)

# Tokens moyens estimés par tour (question + réponse)
AVG_TOKENS_PER_TURN = 500


def calculate_impact(tokens: int, factor=None) -> dict:
    """
    Calcule l'impact environnemental d'une session.

    `factor` peut être un objet ORM ConversionFactor ou None.
    Si None, on utilise les valeurs par défaut (framework-agnostic).
    """
    kwh_per_token = factor.kwh_per_token if factor else DEFAULT_KWH_PER_TOKEN
    co2_std_rate = factor.co2_per_kwh_standard if factor else DEFAULT_CO2_STANDARD
    co2_eth_rate = factor.co2_per_kwh_ethical if factor else DEFAULT_CO2_ETHICAL

    total_kwh = tokens * kwh_per_token
    co2_standard_kg = total_kwh * co2_std_rate
    co2_ethical_kg = total_kwh * co2_eth_rate

    return {
        "total_kwh":      round(total_kwh, 7),
        "co2_standard":   round(co2_standard_kg, 6),
        "co2_ethical":    round(co2_ethical_kg, 6),
        "co2_saved":      round(co2_standard_kg - co2_ethical_kg, 6),
        "homes_heated_min": round(total_kwh * MINUTES_PER_KWH, 3),
        "showers_equiv":  round(total_kwh / KWH_PER_SHOWER, 4),
    }


def estimate_tokens_from_turns(nb_turns: int) -> int:
    return max(1, nb_turns * AVG_TOKENS_PER_TURN)


_ACCENTED = frozenset("éàùçèêîïôûüœæÉÀÙÇÈÊÎÏÔÛÜŒÆ")


def estimate_tokens_from_text(text: str) -> int:
    """1 token ≈ 4 chars EN / ≈ 3.5 chars pour le français technique."""
    if len(text) < 10:
        return max(1, len(text) // 4)
    accented = sum(1 for c in text if c in _ACCENTED)
    chars_per_token = 3.5 if accented / len(text) > 0.02 else 4.0
    return max(1, int(len(text) / chars_per_token))
