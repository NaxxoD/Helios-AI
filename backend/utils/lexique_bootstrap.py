"""
Bootstrap du glossaire de bruit depuis Lexique3 (lexique.org).

Lexique3 est un lexique français libre de 140 000 entrées avec :
- cgram   : catégorie grammaticale (ONO, ADV, VER, NOM, ADJ...)
- freqlemfilm2 : fréquence dans les sous-titres de films (proxy oral/conversationnel)
- freqlemlivres: fréquence dans les livres (proxy écrit)

On en déduit un score de bruit 0.0→1.0 par mot selon sa catégorie et son contexte.

Usage : python -m utils.lexique_bootstrap
        → génère backend/data/lexique_noise.json
"""

import csv
import io
import json
import os

import httpx

LEXIQUE_URL  = "http://www.lexique.org/databases/Lexique383/Lexique383.tsv"
CACHE_PATH   = os.path.join(os.path.dirname(__file__), "..", "data", "lexique_noise.json")

# Score de bruit de base par catégorie grammaticale
_CGRAM_BASE = {
    "ONO": 0.88,   # Onomatopées / interjections : "coucou", "bref", "hein"
    "ADV": 0.55,   # Adverbes — souvent remplissage, affinés par fréquence orale
    "ADJ": 0.22,   # Adjectifs — signal en général
    "NOM": 0.12,   # Noms — signal fort
    "VER": 0.18,   # Verbes — signal fort (sauf émotionnels)
    "PRO": 0.20,   # Pronoms
    "PRE": 0.28,   # Prépositions
    "CON": 0.32,   # Conjonctions
    "ART": 0.08,   # Articles
}

# Adverbes à score élevé malgré la catégorie : intensificateurs vides en oral
_HIGH_NOISE_ADV = frozenset({
    "vraiment", "franchement", "sincèrement", "honnêtement",
    "clairement", "évidemment", "naturellement", "forcément",
    "carrément", "vachement", "trop", "super", "hyper",
    "genre", "bref", "quand même", "enfin", "bref",
})

# Verbes à score élevé : émotions sans apport informatif
_EMOTIONAL_VERBS = frozenset({
    "stresser", "angoisser", "flipper", "paniquer", "craindre",
    "redouter", "appréhender", "douter", "hésiter",
    "espérer", "souhaiter", "rêver", "imaginer",
})


def _compute_score(word: str, cgram: str, freq_film: float, freq_livres: float) -> float:
    base = _CGRAM_BASE.get(cgram[:3], 0.35)

    # Adverbes oraux très fréquents → score plus élevé
    if cgram.startswith("ADV"):
        if word in _HIGH_NOISE_ADV:
            base = 0.80
        elif freq_film > 50:   # très fréquent à l'oral → probablement remplissage
            base = min(0.70, base + 0.15)

    # Verbes émotionnels → score plus élevé
    if cgram.startswith("VER") and word in _EMOTIONAL_VERBS:
        base = 0.72

    # Interjections rares → pas forcément du bruit (terme technique)
    if cgram == "ONO" and freq_film < 2:
        base = 0.50

    return round(base, 2)


def build(force: bool = False) -> dict[str, float]:
    """Télécharge Lexique3 et retourne {mot: score_bruit}.
    Utilise le cache JSON si disponible.
    """
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)

    if not force and os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)

    print("Téléchargement de Lexique3 (~30 Mo)...")
    resp = httpx.get(LEXIQUE_URL, timeout=60, follow_redirects=True)
    resp.raise_for_status()

    scores: dict[str, float] = {}
    reader = csv.DictReader(io.StringIO(resp.text), delimiter="\t")

    for row in reader:
        word  = row.get("ortho", "").strip().lower()
        cgram = row.get("cgram", "").strip()
        if not word or not cgram:
            continue
        try:
            freq_film   = float(row.get("freqlemfilm2",  "0") or "0")
            freq_livres = float(row.get("freqlemlivres", "0") or "0")
        except ValueError:
            continue

        score = _compute_score(word, cgram, freq_film, freq_livres)
        # Ne stocker que les entrées à score significatif (≥ 0.55)
        # pour garder le fichier léger
        if score >= 0.55:
            scores[word] = score

    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=None)

    print("Lexique3 traite : " + str(len(scores)) + " entrees avec score >= 0.55")
    return scores


def load() -> dict[str, float]:
    """Charge le cache. Retourne {} si le bootstrap n'a pas encore été fait."""
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


if __name__ == "__main__":
    scores = build(force=True)
    print("Exemples : " + str({k: v for k, v in list(scores.items())[:10]}))
