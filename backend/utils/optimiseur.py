"""
Optimiseur de prompts -- heuristiques locales, zero appel API.

Chaque regle est (pattern_regex, remplacement, label).
L'application est sequentielle : chaque regle recoit la sortie de la precedente.
"""

import re
from utils.calculator import estimate_tokens_from_text

# Policy Engine ML (gating de compression) — import tolérant : le backend tourne
# normalement même si le package ML n'est pas prêt / l'artifact est absent.
try:
    from ml.policy import decide_policy
except Exception:
    decide_policy = None

# ---------------------------------------------------------------------------
# Paliers — définitions et contraintes output
# ---------------------------------------------------------------------------

PALIERS = {
    '★': {'label': 'Signal pur',               'emoji': '⚡', 'constraint': 'Réponds en 50 mots maximum.'},
    '0': {'label': 'Réduction stratégique',    'emoji': '🗒️', 'constraint': 'Réponds en 60 mots maximum.'},
    '1': {'label': 'Compression fluide',       'emoji': '📱', 'constraint': 'Réponds en 85 mots maximum.'},
    '2': {'label': 'Contrôle adaptatif',       'emoji': '🎯', 'constraint': 'Réponds en 115 mots maximum.'},
    '3': {'label': 'Profondeur équilibrée',    'emoji': '🧠', 'constraint': 'Réponds en 140 mots maximum.'},
    '4': {'label': 'Élaboration multi-niveaux','emoji': '🌐', 'constraint': 'Réponds en 165 mots maximum.'},
    '5': {'label': 'Surcharge / Dilatation',   'emoji': '🌀', 'constraint': None},
    'C': {'label': 'Code pur',                 'emoji': '⚙️', 'constraint': 'Code uniquement. Commentaires minimalistes.'},
    '6': {'label': 'Documentation',            'emoji': '📚', 'constraint': None},
}

# Réponse naturelle estimée SANS contrainte (baseline "no-limit"), par type de question
PALIER_BASELINE_TOKENS = {
    '★': 200,
    '0': 250,
    '1': 320,
    '2': 400,
    '3': 500,
    '4': 650,
    '5': None,
    'C': None,
    '6': None,
}

# Plafond tokens sortie par PALIER (mots max × 1.4)
PALIER_OUTPUT_CEILING = {
    '★': 70,
    '0': 85,
    '1': 120,
    '2': 160,
    '3': 195,
    '4': 230,
    '5': None,
    'C': None,
    '6': None,
}

_LIST_RE    = re.compile(r'\b(liste[zr]?|énumère[zr]?|exemples?|bullet|points?)\b', re.IGNORECASE)
_COMPARE_RE = re.compile(
    r'\b(compare[zr]?|comparaison|vs\.?|versus|diff[eé]rences?\s+entre'
    r'|avantages?\s+et\s+inconv[eé]nients?)\b', re.IGNORECASE
)


def _estimate_output_tokens(text: str, palier_key: str) -> tuple[int | None, int | None]:
    """Estimation réaliste des tokens sortie. Retourne (estimated, ceiling).
    Pour les paliers sans plafond fixe (C, 6, 5), utilise une heuristique basée sur l'input.
    """
    ceiling = PALIER_OUTPUT_CEILING.get(palier_key)
    input_tokens = estimate_tokens_from_text(text) if text else 0

    if ceiling is None:
        if palier_key == 'C':
            # Code : sortie ≈ 1× à 3× l'input selon complexité
            factor = 1.8 if input_tokens > 40 else 1.2
            estimated = round(input_tokens * factor)
            max_out   = round(input_tokens * 3.5)
            return estimated, max_out
        if palier_key == '6':
            # Documentation : sortie ≈ 2× à 5× l'input
            estimated = round(input_tokens * 2.5)
            max_out   = round(input_tokens * 5)
            return estimated, max_out
        if palier_key == '5':
            # Dilatation sans contrainte : estimation prudente
            estimated = round(input_tokens * 1.5)
            max_out   = round(input_tokens * 4)
            return estimated, max_out
        return None, None

    words  = text.split()
    factor = 0.50
    factor += text.count('?') * 0.08
    if _LIST_RE.search(text):
        factor *= 1.25
    if _COMPARE_RE.search(text):
        factor *= 1.15
    if len(words) < 8:
        factor *= 0.65

    factor    = max(0.35, min(0.95, factor))
    estimated = round(ceiling * factor)
    return estimated, ceiling


_CODE_MARKERS = {
    'python', 'javascript', 'typescript', 'react', 'vue', 'angular', 'sql', 'bash',
    'html', 'css', 'json', 'api', 'endpoint', 'composant', 'component', 'script',
    'debug', 'algorithme', 'algorithm', 'fonction', 'function', 'class', 'interface',
    'fastapi', 'django', 'flask', 'node', 'express', 'rust', 'golang', 'java', 'swift',
    'kotlin', 'regex', 'query', 'database', 'endpoint', 'microservice',
}
_CODE_VERBS = {
    'écris', 'ecris', 'génère', 'genere', 'crée', 'cree',
    'développe', 'developpe', 'implémente', 'implemente',
    'construis', 'programme', 'code',
    # EN
    'write', 'generate', 'create', 'build', 'implement', 'develop', 'make',
}
_DOC_MARKERS = {
    'documentation', 'readme', 'guide complet', 'cours complet', 'tutoriel complet', 'tout sur',
    # EN
    'complete guide', 'full guide', 'tutorial', 'full tutorial',
}
_COMPLEX_MARKERS = {
    'compare', 'analyse', 'évalue', 'evalue', 'pros et cons', 'pros and cons',
    'avantages et inconvénients', 'avantages et inconvenients',
    'différences entre', 'differences entre', 'differences between',
    'architecture', 'stratégie', 'strategie',
    # EN
    'compare', 'analyze', 'evaluate', 'trade-offs', 'tradeoffs',
    'advantages and disadvantages', 'when to use', 'vs',
}
_CONSTRAINT_MARKERS = {
    'mots maximum', 'mots max', 'lignes maximum', 'sois bref',
    'brièvement', 'concisément', 'en détail', 'exhaustif',
    # Contraintes de format de sortie
    'en json', 'format json', 'en yaml', 'en xml', 'en csv',
    'en markdown', 'format markdown', 'réponds en', 'reponds en',
    'retourne un', 'retourne une', 'output json', 'output in json',
}


def detect_complexity(text: str) -> str:
    """Détecte la complexité de la TÂCHE, indépendamment de la longueur d'output attendue.
    Retourne : 'simple' | 'technique' | 'analytique' | 'documentaire'
    """
    t = text.lower()

    # Documentaire — génération de contenu long et structuré
    if any(m in t for m in _DOC_MARKERS):
        return 'documentaire'

    # Technique — création ou manipulation de code
    if any(m in t for m in _CODE_MARKERS) and any(v in t for v in _CODE_VERBS):
        return 'technique'

    # Analytique — comparaison, évaluation, raisonnement
    if any(m in t for m in _COMPLEX_MARKERS):
        return 'analytique'

    return 'simple'


def detect_palier(text: str) -> str:
    """Détection déterministe du palier optimal selon le contenu du prompt."""
    t = text.lower()
    words = text.split()

    # Contrainte déjà présente → ne pas écraser
    if any(m in t for m in _CONSTRAINT_MARKERS):
        return '5'

    # Code — marqueur technique + verbe de création
    if any(m in t for m in _CODE_MARKERS) and any(v in t for v in _CODE_VERBS):
        return 'C'

    # Documentation
    if any(m in t for m in _DOC_MARKERS):
        return '6'

    # Demande analytique complexe (avant le word count — une question courte peut être complexe)
    if any(m in t for m in _COMPLEX_MARKERS):
        return '3'

    # Question factuelle courte
    if len(words) <= 15 and '?' in text:
        return '★'

    # Question courte sans contexte
    if len(words) <= 25:
        return '0'

    return '2'


# ---------------------------------------------------------------------------
# E3 — Chips de complétion guidée
# ---------------------------------------------------------------------------

E3_CHIPS = {
    'technique': [
        {'slot': 'langage',        'label': 'Langage ?',          'options': ['Python', 'JavaScript', 'TypeScript', 'Sans préférence']},
        {'slot': 'format_sortie',  'label': 'Format de sortie ?', 'options': ['Code seul', 'Code + explications', 'Pseudo-code']},
        {'slot': 'objectif',       'label': 'Objectif ?',         'options': ['Créer', 'Débugger', 'Optimiser', 'Expliquer']},
        {'slot': 'gestion_erreurs','label': 'Gestion erreurs ?',  'options': ['Inclure', 'Pas nécessaire']},
    ],
    'analytique': [
        {'slot': 'criteres', 'label': 'Critères ?',         'options': ['Performance', 'Coût', 'Facilité', 'Tous']},
        {'slot': 'format',   'label': 'Format de sortie ?', 'options': ['Tableau', 'Liste', 'Pros/Cons', 'Prose']},
        {'slot': 'verdict',  'label': 'Verdict attendu ?',  'options': ['Oui, recommandez', 'Analyse seule']},
    ],
    'documentaire': [
        {'slot': 'audience',  'label': 'Audience ?',         'options': ['Débutant', 'Intermédiaire', 'Expert']},
        {'slot': 'niveau',    'label': 'Niveau de détail ?', 'options': ["Vue d'ensemble", 'Détaillé', 'Exhaustif']},
        {'slot': 'structure', 'label': 'Structure ?',        'options': ['Sections titrées', 'Tutoriel étapes', 'Libre']},
    ],
    'simple': [],
}

_SLOT_DETECTORS = {
    'langage':         re.compile(r'\b(python|javascript|typescript|java|rust|golang|swift|kotlin|ruby|php|bash|c\+\+)\b', re.IGNORECASE),
    'format_sortie':   re.compile(r'\b(en json|format json|retourne[szr]? (du )?json|output json|en markdown|en csv|en yaml|en xml|code seul|avec explications?)\b', re.IGNORECASE),
    'objectif':        re.compile(r'\b(crée[zr]?|débugge[zr]?|optimise[zr]?|explique[zr]?|écris?|génère[zr]?)\b', re.IGNORECASE),
    'gestion_erreurs': re.compile(r'\b(erreurs?|exceptions?|gestion|try|catch|fallback)\b', re.IGNORECASE),
    'criteres':        re.compile(r'\b(critères?|selon|en fonction de|performance|coût|facilité)\b', re.IGNORECASE),
    'format':          re.compile(r'\b(tableau|liste|bullet|pros.cons|format|prose)\b', re.IGNORECASE),
    'verdict':         re.compile(r'\b(recommande[zr]?|conseille[zr]?|conclusion|verdict|décision)\b', re.IGNORECASE),
    'audience':        re.compile(r'\b(débutant|expert|intermédiaire|audience|niveau)\b', re.IGNORECASE),
    'niveau':          re.compile(r'\b(détaillé|exhaustif|vue.ensemble|aperçu)\b', re.IGNORECASE),
    'structure':       re.compile(r'\b(sections?|titres?|étapes?|plan|structure)\b', re.IGNORECASE),
}


def detect_chips(prompt: str, task_type: str) -> list[dict]:
    """Retourne les chips pour les slots non encore spécifiés dans le prompt."""
    chips = E3_CHIPS.get(task_type, [])
    result = []
    for chip in chips:
        detector = _SLOT_DETECTORS.get(chip['slot'])
        if detector is None or not detector.search(prompt):
            result.append(chip)
    return result


# ---------------------------------------------------------------------------
# Regles
# ---------------------------------------------------------------------------

# Patterns CONTRAINTE — segments portant une règle à respecter (à protéger)
_CONTRAINTE_RE = [re.compile(p, re.IGNORECASE) for p in [
    r"n['’]oublie pas de\b",
    r"\bassure-toi de\b",
    r"\butilise\b.{0,40}\b(format|style|langue|json|markdown|liste|python|javascript|typescript)\b",
    r"\blimite[zr]?\b.{0,20}\b(mots?|caract[eè]res?|lignes?|tokens?)\b",
    r"\bobligatoirement\b",
    r"\btoujours\b.{0,30}\b(retourne[sz]?|formate[sz]?|utilise[sz]?|inclus)\b",
    r"\bne (pas|jamais)\b.{0,20}\b(utiliser|inclure|mentionner|ajouter)\b",
]]

# Patterns CONTEXTE — segments expliquant la situation ou le besoin
_CONTEXTE_RE = [re.compile(p, re.IGNORECASE) for p in [
    r"\bparce que\b", r"\bcar\b", r"\bpuisque\b",
    r"\bdepuis que\b", r"\bvu que\b",
    r"\ble contexte\b", r"\bje travaille sur\b",
    r"\bdans le cadre de\b",
]]

# Patterns FORMAT \u2014 modificateurs de SORTIE (longueur, ton, format, nombre).
# Servent UNIQUEMENT \u00e0 la classification du scaffold (pas \u00e0 _protect_constraints,
# pour ne pas r\u00e9duire le nettoyage E1). On ne cible PAS les noms de livrables
# (\u00ab liste \u00bb, \u00ab roadmap \u00bb, \u00ab plan \u00bb) qui sont souvent la t\u00e2che elle-m\u00eame.
_FORMAT_RE = [re.compile(p, re.IGNORECASE) for p in [
    r"\ben\s+(\d+|deux|trois|quatre|cinq|six)\s+(points?|[e\u00e9]tapes?|parties?|phrases?|lignes?|mots?|axes?)\b",
    r"\b(\d+|deux|trois|quatre|cinq|six)\s+(points?|[e\u00e9]tapes?|axes?)\b",
    r"\b(maximum|max\.?|au maximum|au plus|pas plus de)\s+\d+\b",
    r"\b\d+\s+(mots?|caract[e\u00e8]res?|lignes?|tokens?)\s+(max|maximum)\b",
    r"\b(sois|reste[zr]?)\s+(bref|concis|synth[e\u00e9]tique)\b",
    r"\b(pas trop long|court mais|bien structur[e\u00e9]e?|point par point|de mani[e\u00e8]re concise)\b",
    r"\bsous forme d['e]\s*(liste|tableau|bullets?|sch[e\u00e9]ma|plan)\b",
    r"\b(en|au format)\s+(json|markdown|csv|yaml|xml|tableau|bullets?)\b",
    r"\bton\s+(professionnel|formel|informel|amical|s[e\u00e9]rieux|p[e\u00e9]dagogique|neutre)\b",
]]

# Apostrophe : accepte ASCII ' (U+0027) et typographique ' (U+2019)
_AO = "['\u2019]"

# ---------------------------------------------------------------------------
# Phrases enti\u00e8res de politesse \u00e0 supprimer (niveau phrase)
# ---------------------------------------------------------------------------

_PHRASES_BRUIT_RE = [re.compile(p, re.IGNORECASE) for p in [
    # Salutations
    r"^(bonjour|bonsoir|salut|coucou|hello|hi|hey)\b",
    r"^j" + _AO + r"esp[e\u00e8]re que (vous allez|tu vas|tout va|[c\u00e7]a va)\b",
    # Formules de contact / permission
    r"^je me permets (de|d" + _AO + r")",
    r"^je prends la libert",
    r"^je (vous|te|t" + _AO + r") (contacte|[e\u00e9]cris|sollicite)\b",
    # Formules de besoin d'aide
    r"^j" + _AO + r"aurais (besoin de (votre|ton|ta) aide|besoin que)\b",
    r"^si cela ne (vous|te) d[e\u00e9]range pas\b",
    r"^si (vous avez|tu as) (le temps|un moment|la gentillesse)\b",
    # Pr\u00e9ambules de difficult\u00e9
    r"^j" + _AO + r"ai (quelques |des |un peu de )?(difficult[e\u00e9]|mal|du mal|probl[e\u00e8]me)\b",
    r"^je rencontre (quelques|des|un) (difficult[e\u00e9]|probl[e\u00e8]me|souci)\b",
    r"^malgr[e\u00e9] mes (recherches|efforts|tentatives)\b",
    # Remerciements
    r"^(je (vous|te) remercie|merci (beaucoup|infiniment|d" + _AO + r"avance|pour votre))\b",
    r"^en (vous|te) remerciant\b",
    r"^avec mes (sinc[e\u00e8]res?|chaleureux) remerciements\b",
    r"^dans l" + _AO + r"espoir (d" + _AO + r"une r[e\u00e9]ponse|de vous|de te)\b",
    r"^en esp[e\u00e9]rant (une|votre|ta|une r[e\u00e9]ponse)\b",
    r"^votre aide (sera|est) (tr[e\u00e8]s )?(pr[e\u00e9]cieuse|appr[e\u00e9]ci[e\u00e9]e)\b",
    # Cl\u00f4tures
    r"^n" + _AO + r"h[e\u00e9]sitez? pas [a\u00e0] (me|nous|le|la)\b",
    r"^(cordialement|bien [a\u00e0] (vous|toi)|avec mes salutations)\b",
    # M\u00e9t\u00e9o, ambiance, humeur \u2014 hors sujet business
    r"^en plus (il fait|c" + _AO + r"est)\b.{0,80}\b(beau|chaud|froid|soleil|nuageux|pluvieux)\b",
    r"^il fait\b.{0,60}\b(beau|chaud|froid|soleil|nuageux|pluvieux)\b",
    r"\b[c\u00e7]a (me |nous |te )?donne (de l" + _AO + r")?(\u00e9nergie|energie|envie|courage|la p[e\u00ea]che)\b",
    r"^je suis (tr[e\u00e8]s |bien |super )?(motiv[e\u00e9]e?|en forme|de bonne humeur|content|ravi)\b",
    r"^(quelle|c" + _AO + r"est une?) (belle|bonne|super|magnifique) (journ[e\u00e9]e|matin[e\u00e9]e|semaine)\b",
]]

# Transformations des tournures interrogatives polies \u2192 imp\u00e9ratives directes
_INTERROGATIF = [
    # "Pourriez-vous [svp] m'expliquer X" \u2192 "Expliquez-moi X"
    (r"pourr?iez-vous(?:\s+s" + _AO + r"il vous pla[i\u00ee]t)?\s+m" + _AO + r"expliquer\s+",
     "Expliquez-moi ", "tournure interrogative \u2192 imperative"),
    (r"pourr?ais-tu(?:\s+s" + _AO + r"il te pla[i\u00ee]t)?\s+m" + _AO + r"expliquer\s+",
     "Explique-moi ", "tournure interrogative \u2192 imperative"),
    (r"pourr?iez-vous(?:\s+s" + _AO + r"il vous pla[i\u00ee]t)?\s+me?\s+d[e\u00e9]crire\s+",
     "D\u00e9crivez ", "tournure interrogative \u2192 imperative"),
    (r"pourr?iez-vous(?:\s+s" + _AO + r"il vous pla[i\u00ee]t)?\s+me?\s+montrer\s+",
     "Montrez-moi ", "tournure interrogative \u2192 imperative"),
    (r"pourr?iez-vous(?:\s+s" + _AO + r"il vous pla[i\u00ee]t)?\s+me?\s+dire\s+",
     "Dites-moi ", "tournure interrogative \u2192 imperative"),
    (r"pourr?iez-vous(?:\s+s" + _AO + r"il vous pla[i\u00ee]t)?\s+",
     "", "tournure interrogative condensee"),
    (r"pourr?ais-tu(?:\s+s" + _AO + r"il te pla[i\u00ee]t)?\s+",
     "", "tournure interrogative condensee"),
    (r"est-ce que vous pouvez\s+",   "", "tournure interrogative condensee"),
    (r"est-ce que tu peux\s+",       "", "tournure interrogative condensee"),
]

_POLITESSE = [
    (r'\bpourr?ais-tu s' + _AO + r'il te pla[i\xee]t\b', '', 'formule de politesse'),
    (r'\bpourr?ais-tu\b',                                  '', 'formule de politesse'),
    (r'\bpourr?iez-vous s' + _AO + r'il vous pla[i\xee]t\b', '', 'formule de politesse'),
    (r'\bpourr?iez-vous\b',                                '', 'formule de politesse'),
    (r's' + _AO + r'il te pla[i\xee]t\b',                 '', 'formule de politesse'),
    (r's' + _AO + r'il vous pla[i\xee]t\b',               '', 'formule de politesse'),
    (r'\bje t' + _AO + r'en (supplie|prie)\b',             '', 'formule de politesse'),
    (r'\bmerci d' + _AO + r'avance\b',                     '', 'formule de politesse'),
    (r'\bmerci beaucoup\b',                                '', 'formule de politesse'),
    (r'\bje te remercie\b',                                '', 'formule de politesse'),
    (r'\bje vous remercie\b',                              '', 'formule de politesse'),
]

_VERBEUX = [
    (r'\bje voudrais que tu (?:me )?(fasses?|[e\xe9]crives?|expliques?|'
     r'g[e\xe9]n[e\xe8]res?|cr[e\xe9]es?|listes?|donnes?|proposes?)\b',
     r'\1', 'tournure verbale condensee'),
    (r'\best-ce que tu peux\b',                            '', 'tournure verbale condensee'),
    (r'\bpeux-tu\b',                                       '', 'tournure verbale condensee'),
    (r'\bj' + _AO + r'aimerais que tu\b',                  '', 'tournure verbale condensee'),
    (r'\bj' + _AO + r'aurais besoin que tu\b',             '', 'tournure verbale condensee'),
    (r'\bje souhaiterais que tu\b',                        '', 'tournure verbale condensee'),
    (r'\bje voulais te demander\b',                        '', 'tournure verbale condensee'),
    (r'\bn' + _AO + r'oublie pas de\b',                    '', 'tournure verbale condensee'),
    (r'\bje voudrais\b',                                   '', 'tournure verbale condensee'),
    (r'\bj' + _AO + r'aimerais\b',                         '', 'tournure verbale condensee'),
]

_REDONDANCES = [
    (r'comme je (te|vous) l' + _AO + r'ai dit (plus t[o\xf4]t|avant|'
     r'pr[e\xe9]c[e\xe9]demment|d[e\xe9]j[a\xe0])[,.]?\s*', '', 'contexte redondant'),
    (r'comme (mentionn[e\xe9]|dit|expliqu[e\xe9]|indiqu[e\xe9]) '
     r'(plus t[o\xf4]t|avant|pr[e\xe9]c[e\xe9]demment|d[e\xe9]j[a\xe0])[,.]?\s*',
     '', 'contexte redondant'),
    (r'comme tu (le )?(sais|vois|peux le constater)[,.]?\s*', '', 'contexte redondant'),
    (r'\ben (d' + _AO + r'autres termes|d' + _AO + r'autres mots|r[e\xe9]sum[e\xe9])[,.]?\s*',
     '', 'reformulation redondante'),
    (r'\b(bien ([s\xf9]r|entendu)|[e\xe9]videmment|naturellement|clairement|franchement)[,.]?\s*',
     '', 'adverbe de remplissage'),
    (r'\b(en fait|en r[e\xe9]alit[e\xe9]|au fond)[,.]?\s*', '', 'adverbe de remplissage'),
    (r'\bje pense que\b',                                  '', 'hedge inutile'),
    (r'\b[a\xe0] mon avis[,.]?\s*',                        '', 'hedge inutile'),
    (r'\bselon moi[,.]?\s*',                               '', 'hedge inutile'),
    # Openers mid-texte (pas en ^ absolu)
    (r'\balors\s+voil[a\xe0][,.]?\s*',                     '', 'intro conversationnelle'),
    (r'\bdu coup[,.]?\s+(?=est-ce que|est-ce qu|tu pourrais|vous pourriez)', '', 'transition orale'),
    (r',?\s*tu vois le genre\s*\??[,.]?\s*',               '. ', 'fin de phrase vide'),
]

# ── Bruit social / contextuel — patterns hors-sujet non techniques ────────────

_SOCIAL_FILLER = [
    # Salutations d'entrée
    (r'^[Ss]alut\s*[!,.]?\s+',                                                    '', 'salutation'),
    (r'^[Bb]onjour\s*[!,.]?\s+',                                                  '', 'salutation'),
    (r'^[Cc]oucou\s*[!,.]?\s+',                                                   '', 'salutation'),
    (r'^[Hh]e(?:y|llo)\s*[!,.]?\s+',                                              '', 'salutation'),
    # J'espère que + état social
    (r"[Jj]" + _AO + r"esp[eè]re que tu (?:as pass[eé]|passes?) (?:un bon|une bonne|de bonnes?)[^.!?]{2,40}[.!?]?\s*",
                                                                                   '', 'contextuel social'),
    (r"[Jj]" + _AO + r"esp[eè]re que tu vas bien[.!,]?\s*",                      '', 'contextuel social'),
    (r"[Jj]" + _AO + r"esp[eè]re que tu as (?:bien dormi|pass[eé] une bonne nuit|pass[eé] de bonnes vacances)[.!,]?\s*",
                                                                                   '', 'contextuel social'),
    (r"[Jj]" + _AO + r"esp[eè]re que tu as (?:la p[eê]che|la forme|la frite|la patate|la banane)(?:\s+aujourd" + _AO + r"hui)?[.!,]?\s*",
                                                                                   '', 'contextuel social'),
    # Intro "j'ai une question"
    (r"[Jj]" + _AO + r"ai une (?:petite |toute petite )?question (?:un peu |assez )?(?:technique|simple|rapide|basique|b[eê]te|pratique)?(?:\s+pour (?:toi|vous))?(?:\s+aujourd" + _AO + r"hui)?(?:\s+(?:parce que|car|puisque)[^.!?]{0,80})?\s*[.!,]?\s*",
                                                                                   '', 'intro question'),
    # Écoute / alors écoute en ouverture
    (r"(?:^|(?<=[!?]\s)|(?<=\.\s))[EeÉé]coute[,.]?\s+",                          '', 'transition orale'),
    (r"[Aa]lors\s+[eé]coute[,.]?\s+",                                             '', 'transition orale'),
    # "je me demandais" comme intro
    (r"(?:^|,\s*)je me demandais[,.]?\s+",                                        ' ', 'transition orale'),
    # "Genre," en début de phrase ou après ponctuation
    (r"(?:^|(?<=[!?.]\s))[Gg]enre[,.]?\s+",                                      '', 'transition orale'),
    # Conclusions vides
    (r"[Vv]oil[aà][,.]?\s+c" + _AO + r"est tout pour (?:le moment|l" + _AO + r"instant|maintenant)[.!]?\s*",
                                                                                   '', 'conclusion vide'),
    (r"[Vv]oil[aà][,.]?\s+c" + _AO + r"est tout[.!]?\s*",                        '', 'conclusion vide'),
    (r"[Cc]" + _AO + r"est tout pour (?:le moment|l" + _AO + r"instant|maintenant)[.!]?\s*",
                                                                                   '', 'conclusion vide'),
    (r"[Cc]" + _AO + r"est (?:[aà] peu pr[eè]s|grosso modo) tout[.!]?\s*",       '', 'conclusion vide'),
    (r"[Vv]oil[aà] (?:ma question|mon probl[eè]me|ma demande|ce que je voulais demander)[.!]?\s*",
                                                                                   '', 'conclusion vide'),
    (r"[Cc]" + _AO + r"est (?:ma question|ma demande)[.!]?\s*",                  '', 'conclusion vide'),
    (r"[Jj]" + _AO + r"esp[eè]re (?:que c" + _AO + r"est clair|avoir [eé]t[eé] clair)[.!]?\s*",
                                                                                   '', 'conclusion vide'),
]

# ── co-auteur — bruit conversationnel oral ────────────────────────────────────────

# Catégorie 1 — Openers conversationnels
_INTRO_CONVOS = [
    (r'^[Aa]lors\s+voil[a\xe0][,.]?\s*',                                    '', 'intro conversationnelle'),
    (r'\bje t' + _AO + r'explique\s+(mon\s+)?(probl[e\xe8]me|situation|cas)[,.]?\s*',
                                                                             '', 'intro conversationnelle'),
    (r'\bdu coup[,\s]+je me disais[,]?\s+',                                  '', 'transition orale'),
    (r'^[Bb]ref[,.]?\s+',                                                    '', 'transition orale'),
    (r'\bouais[,.]?\s+(?=c' + _AO + r'[e\xe9]tait|c' + _AO + r'est\s+en\s+\d{4})',
                                                                             '', 'interjection orale'),
]

# Catégorie 2 — Redondances synonymiques orales
_REDONDANCES_ORALES = [
    (r'\bou une sorte de\b',                                                 '', 'redondance synonymique'),
    (r',?\s+genre\s+(?=une?|des|le|la|ce|qu)',                               ' ', 'redondance synonymique'),
    (r'\bou des trucs (?:[a\xe0] faire|comme [c\xe7]a)\b',                   '', 'redondance orale'),
    (r'\bou quelque chose comme [c\xe7]a\b',                                 '', 'redondance orale'),
    (r'\bdes trucs [a\xe0] faire\b',                                         '', 'redondance orale'),
]

# Catégorie 3 — Hedges et approximations parenthétiques
_HEDGES = [
    # "(le SEO je crois qu'on dit comme ça ?)" — parenthétique de doute
    (r'\([^)]{0,80}je crois qu' + _AO + r'on dit comme [c\xe7]a\s*\??\s*\)', '', 'hedge parenthetique'),
    (r'\([^)]{0,80}(?:non|enfin)?\s*je crois\s*\??\s*\)',                    '', 'hedge parenthetique'),
    # "je crois" en fin de proposition
    (r',?\s+je crois\s*(?=[,.\?!]|$)',                                       '', 'hedge de confirmation'),
    (r',?\s+enfin je crois\b',                                               '', 'hedge'),
]

# Catégorie 4 — Intensificateurs vides (hors "franchement" déjà dans _REDONDANCES)
_INTENSIFIERS = [
    (r'\bde fou\b',                                                          '', 'intensifieur creux'),
    (r'\bvachement\b',                                                       '', 'intensifieur creux'),
    (r'\bsuper\s+bon\b',                                                     '', 'intensifieur creux'),
    (r'\btrop\s+(?:bien|cool|sympa|super|top)\b',                            '', 'intensifieur creux'),
]


# ── Glossaire de bruit — score 0.0 (signal pur) → 1.0 (bruit pur) ────────────
# Format : (phrase, score, label)
# Seules les entrées avec score ≥ NOISE_THRESHOLD sont supprimées.
# Les phrases longues sont appliquées en premier pour éviter les correspondances partielles.

NOISE_THRESHOLD = 0.70

NOISE_GLOSSARY = [
    # Méta-commentaire — l'utilisateur commente son propre prompt
    ("je sais pas trop par où prendre le problème",   0.95, "méta-commentaire"),
    ("je sais pas trop par où commencer",             0.95, "méta-commentaire"),
    ("je ne sais pas trop par où",                    0.90, "méta-commentaire"),
    ("je sais pas trop comment aborder",              0.90, "méta-commentaire"),
    ("je sais pas trop",                              0.85, "méta-commentaire"),
    ("je ne sais pas trop",                           0.85, "méta-commentaire"),
    ("je sais vraiment pas",                          0.85, "méta-commentaire"),
    ("je comprends pas trop",                         0.85, "méta-commentaire"),
    ("je comprends vraiment pas",                     0.85, "méta-commentaire"),
    ("j'ai du mal à cerner le problème",              0.88, "méta-commentaire"),
    ("donc donne-moi des idées assez globales",       0.90, "méta-commentaire"),
    ("donne-moi des idées assez globales",            0.88, "méta-commentaire"),

    # Qualificateurs flous — rendent la demande moins précise
    ("des idées assez globales",                      0.82, "qualificateur flou"),
    ("des trucs généraux à proposer",                 0.78, "qualificateur flou"),
    ("des pistes générales",                          0.72, "qualificateur flou"),
    ("assez globales",                                0.78, "qualificateur flou"),
    ("assez global",                                  0.78, "qualificateur flou"),
    ("d'une façon générale",                          0.72, "qualificateur flou"),
    ("de façon générale",                             0.72, "qualificateur flou"),
    ("en gros",                                       0.74, "qualificateur flou"),
    ("de manière générale",                           0.70, "qualificateur flou"),

    # Introductions orales multi-mots (phrases longues d'abord)
    ("bon, je t'explique",                            0.92, "intro conversationnelle"),
    ("bon, je vous explique",                         0.92, "intro conversationnelle"),
    ("bon, voilà",                                    0.88, "intro conversationnelle"),
    ("bon, alors",                                    0.85, "intro conversationnelle"),

    # État émotionnel sans apport pour le LLM
    ("je t'avoue que je dors super mal en ce moment", 0.95, "état émotionnel"),
    ("je t'avoue que je dors mal",                    0.92, "état émotionnel"),
    ("j'ose enfin me lancer mais j'ai trop peur de rater", 0.88, "état émotionnel"),
    ("j'ai trop peur de rater",                       0.82, "état émotionnel"),
    ("j'ai peur de rater",                            0.78, "état émotionnel"),
    ("j'ai peur de me tromper",                       0.78, "état émotionnel"),
    ("je t'avoue que",                                0.75, "aveu conversationnel"),
    ("je dois t'avouer que",                          0.75, "aveu conversationnel"),
    ("et je stresse un peu",                          0.72, "état émotionnel"),
    ("et je stresse vraiment",                        0.72, "état émotionnel"),
    ("je stresse un peu",                             0.68, "état émotionnel"),
    ("ça m'angoisse un peu",                          0.68, "état émotionnel"),

    # Salutations exactes
    ("salut !",                                       0.95, "salutation"),
    ("bonjour !",                                     0.92, "salutation"),
    ("coucou !",                                      0.95, "salutation"),
    ("hey !",                                         0.92, "salutation"),

    # Contextuel social — météo, humeur, vie perso
    ("j'espère que tu as passé un bon week-end",      0.95, "contextuel social"),
    ("j'espère que tu as passé une bonne semaine",    0.95, "contextuel social"),
    ("j'espère que tu vas bien",                      0.95, "contextuel social"),
    ("j'espère que tu as passé une bonne journée",    0.95, "contextuel social"),
    ("il fait super beau aujourd'hui",                0.95, "contextuel social"),
    ("il fait beau aujourd'hui",                      0.92, "contextuel social"),
    ("ça donne de l'énergie",                         0.88, "contextuel social"),
    ("ça donne la motivation",                        0.88, "contextuel social"),
    ("je suis à fond sur un nouveau projet",          0.82, "contextuel social"),
    ("je suis à fond sur ce projet",                  0.82, "contextuel social"),

    # Transitions orales
    ("écoute,",                                       0.78, "transition orale"),
    ("écoute.",                                       0.75, "transition orale"),
    ("je me demandais,",                              0.78, "transition orale"),
    ("donc voilà,",                                   0.80, "transition orale"),
    ("bah voilà,",                                    0.82, "transition orale"),
    ("bon voilà,",                                    0.80, "transition orale"),

    # Conclusions / fermetures vides
    ("voilà, c'est tout pour le moment",              0.92, "conclusion vide"),
    ("voilà, c'est tout",                             0.88, "conclusion vide"),
    ("c'est tout pour le moment",                     0.88, "conclusion vide"),
    ("c'est tout pour l'instant",                     0.88, "conclusion vide"),
    ("c'est à peu près tout",                         0.85, "conclusion vide"),
    ("je pense que c'est à peu près tout",            0.88, "conclusion vide"),
    ("voilà ma question",                             0.85, "conclusion vide"),
    ("voilà mon problème",                            0.82, "conclusion vide"),
    ("voilà ma demande",                              0.82, "conclusion vide"),
    ("c'est ma question",                             0.82, "conclusion vide"),
    ("j'espère que c'est clair",                      0.85, "conclusion vide"),
    ("j'espère avoir été clair",                      0.82, "conclusion vide"),
    ("bonne continuation",                            0.90, "conclusion vide"),
    ("bonne journée",                                 0.88, "conclusion vide"),

    # Fins de phrase orales vides
    ("tu vois ?",                                     0.82, "fin de phrase vide"),
    ("tu vois.",                                      0.82, "fin de phrase vide"),
    ("tu vois,",                                      0.80, "fin de phrase vide"),
    ("tu sais.",                                      0.78, "fin de phrase vide"),
    ("tu sais,",                                      0.78, "fin de phrase vide"),
    ("hein ?",                                        0.88, "fin de phrase vide"),
    ("hein.",                                         0.85, "fin de phrase vide"),
    ("enfin voilà.",                                  0.82, "fin de phrase vide"),
    ("enfin voilà,",                                  0.82, "fin de phrase vide"),
    ("c'est tout.",                                   0.72, "fin de phrase vide"),
    ("voilà quoi.",                                   0.85, "fin de phrase vide"),
    ("voilà quoi,",                                   0.85, "fin de phrase vide"),
]


def _apply_noise_glossary(text: str, threshold: float = NOISE_THRESHOLD) -> tuple[str, dict]:
    """Supprime les phrases dont le score de bruit dépasse le seuil.
    Applique les entrées les plus longues en premier pour éviter les faux positifs.
    """
    entries = sorted(
        [(ph, sc, lb) for ph, sc, lb in NOISE_GLOSSARY if sc >= threshold],
        key=lambda x: len(x[0]),
        reverse=True,
    )
    labels_used = {}
    for phrase, _score, label in entries:
        # Gère apostrophe droite ET courbe (U+2019) dans les phrases du glossaire
        escaped = re.escape(phrase).replace(r"\'", r"['']")
        pattern = r'(?i)\s*' + escaped + r'\s*'
        new_text, n = re.subn(pattern, ' ', text)
        if n > 0:
            text = new_text
            labels_used[label] = labels_used.get(label, 0) + n
    return text, labels_used


# Meta-prompt patterns — role assignment, behavioral meta-instructions, empty qualifiers
# [^.!?]* au lieu de [^.]* pour ne pas traverser les fins de phrases (?, !)
_S = r"[^.!?]*"   # segment sans fin de phrase

_ROLE_ASSIGN_RULES = [
    # IA explicite
    (r"tu es (une?\s+)?(intelligence artificielle|IA|assistant)\b" + _S + r"\b(avanc[eé]|dot[eé]e?|disposant|sp[eé]cialis[eé])\b" + _S + r"\.", "", "role IA supprime"),
    # Tu es un expert/spécialiste/ingénieur/développeur [domaine]
    (r"tu es une?\s+(?:expert|sp[eé]cialiste|professionnel|ing[eé]nieur|d[eé]veloppeur|consultant|chercheur|analyste)\w*" + _S + r"\.", "", "role expert supprime"),
    # Tu es doté(e) / équipé(e) de
    (r"tu es dot[eé]e?\s+d(?:e|'une?)\s+" + _S + r"\.", "", "role assignation supprime"),
    # Tu disposes de/d'une [X] (élargi — plus besoin de mot-clé spécifique)
    (r"tu disposes?\s+d(?:e|'une?)\s+" + _S + r"\.", "", "role capacite supprime"),
    # Tu as une vision/connaissance/maîtrise/compréhension
    (r"tu as une\s+(?:vision|connaissance|ma[îi]trise|compr[eé]hension|expertise)\s+" + _S + r"\.", "", "role capacite supprime"),
    # Ta mission consiste/est à [verbe comportemental] — pas les vraies requêtes (expliquer, créer…)
    (r"ta mission (?:consiste|est)\s+[\xe0a]\s+(?:fournir|assurer|garantir|maintenir|analyser|traiter|r[eé]pondre|adopter|soutenir|aider [^\xe0])" + _S + r"\.", "", "mission supprimee"),
    # Tu as pour mission de [verbe comportemental]
    (r"tu as pour mission\s+de\s+(?:fournir|assurer|garantir|maintenir|analyser|traiter|r[eé]pondre|adopter|soutenir)" + _S + r"\.", "", "mission supprimee"),
]

_META_INSTR_RULES = [
    (r"veille[sz]? [\xe0a] (maintenir|respecter|garantir)" + _S + r"\.", "", "instruction meta supprimee"),
    (r"assure[sz]?-toi (que|de) \w" + _S + r"\.", "", "instruction meta supprimee"),
    (r"dans un souci [^\n]{5,80}[.,]?", "", "instruction meta supprimee"),
    (r"ta r[eé]ponse devr(a|ait) id[eé]alement inclure" + _S + r"[.]?", "", "instruction meta supprimee"),
    (r"(?m)^(?:enfin|par ailleurs|ainsi|de m[eê]me|en outre|n[eé]anmoins)[,\s]*$", "", "connecteur vide"),
]

_PLACEHOLDER_RULES = [
    (r"\[(?:INS[EÉ]RER|INSERT|YOUR|VOTRE|ENTER|AJOUTER|REMPLACER|FILL|METTRE)[^\]\n]{0,80}\]?", "", "placeholder non rempli"),
    (r"<(?:INS[EÉ]RER|INSERT|YOUR|VOTRE|ENTER|AJOUTER|REMPLACER|FILL)[^>\n]{0,80}>?", "", "placeholder non rempli"),
]

_EMPTY_QUAL_RULES = [
    (r'\bholistique\b',                       '', 'qualificateur creux'),
    (r'\bmultidimensionnel(?:le)?\b',         '', 'qualificateur creux'),
    (r'\btransversal(?:e)?\b',                '', 'qualificateur creux'),
    (r'\ben constantes? [eé]volution\b',      '', 'qualificateur creux'),
    (r'\bvaleur ajout[eé]e strat[eé]gique\b', '', 'qualificateur creux'),
    (r'\bcontexte globalis[eé]\b',            '', 'qualificateur creux'),
    (r'\bactionnable[s]?\b',                  '', 'qualificateur creux'),
    (r'\bholistic(?:ally)?\b',                '', 'qualificateur creux'),
    (r'\bmulti-?dimensional(?:ly)?\b',        '', 'qualificateur creux'),
    (r'\bactionable\b',                       '', 'qualificateur creux'),
]

_HORS_SUJET_RULES = [
    # Météo — totalement hors sujet dans un prompt LLM
    (r"[eé]n plus[,]?\s+il fait\s+" + _S + r"[.!]", "", "contexte hors sujet supprime"),
    (r"il fait\s+(?:super\s+|vraiment\s+|tellement\s+)?(?:beau|chaud|froid|soleil|gris|moche)\s*" + _S + r"[.!,]", "", "contexte hors sujet supprime"),
    (r"il y a\s+(?:du soleil|un soleil|de la pluie|du vent|du brouillard)\s*" + _S + r"[.!,]", "", "contexte hors sujet supprime"),
    (r"(?:le soleil|la pluie|le beau temps|la chaleur)\s+" + _S + r"(?:donne|inspire|motive|aide|pousse)\s+" + _S + r"[.!]", "", "contexte hors sujet supprime"),
    (r"ça donne\s+(?:de l[' ]|une\s+)?[eé]nergie\s+" + _S + r"[.!]", "", "contexte hors sujet supprime"),
    # Heure / moment de la journée sans rapport
    (r"ce matin[,]?\s+" + _S + r"(?:en buvant|pendant|avant|après)\s+" + _S + r"[.!]", "", "contexte hors sujet supprime"),
]

# _ROLE_ASSIGN_RULES exclus du pipeline : les assignations de rôle sont des instructions légitimes
_META_PROMPT_RULES = _META_INSTR_RULES + _PLACEHOLDER_RULES + _EMPTY_QUAL_RULES + _HORS_SUJET_RULES
_META_RE = [re.compile(p, re.IGNORECASE | re.DOTALL) for p, _, _ in _META_INSTR_RULES + _HORS_SUJET_RULES]


def _remove_bruit_sentences(text: str) -> tuple[str, int]:
    """Supprime les phrases entières identifiées comme du bruit de politesse.
    Si le pattern ne couvre qu'un préfixe court de la phrase (salut + vrai contenu),
    on strip uniquement la partie matchée pour ne pas effacer le contenu.
    Retourne (texte_nettoyé, nombre_de_phrases_supprimées).
    """
    # Découpe en phrases en conservant la ponctuation
    chunks = re.split(r'([.!?]+\s*)', text)
    # Regroupe "phrase" + "ponctuation"
    sentences = []
    i = 0
    while i < len(chunks):
        if i + 1 < len(chunks) and re.fullmatch(r'[.!?]+\s*', chunks[i + 1]):
            sentences.append(chunks[i] + chunks[i + 1])
            i += 2
        else:
            if chunks[i].strip():
                sentences.append(chunks[i])
            i += 1

    kept, removed = [], 0
    for s in sentences:
        stripped = s.strip()
        matched_p = next((p for p in _PHRASES_BRUIT_RE if p.search(stripped)), None)
        if stripped and matched_p:
            m = matched_p.search(stripped)
            match_words = len(m.group().split())
            match_ratio  = len(m.group()) / max(1, len(stripped))

            if match_words >= 3 or match_ratio > 0.60:
                # Formule longue (≥ 3 mots matchés) ou phrase quasi-entière → supprimer tout
                removed += 1
            else:
                # Salutation courte (1-2 mots) — garder le reste seulement si c'est
                # du contenu réel : ≥ 20 mots OU ≥ 10 mots avec un verbe de tâche
                trimmed = matched_p.sub('', s).strip(' ,;')
                n_words  = len(trimmed.split()) if trimmed else 0
                has_task = bool(_TASK_VERBS_RE.search(trimmed)) if trimmed else False
                if trimmed and (n_words >= 20 or (n_words >= 10 and has_task)):
                    kept.append(trimmed)
                removed += 1
        else:
            kept.append(s)
    return ''.join(kept).strip(), removed


def _classify_segments(text) -> dict:
    """Classifie chaque segment du prompt dans une couche de la pyramide."""
    raw = [s.strip() for s in re.split(r'[.!?;]+\s*|\n+', text) if s.strip()]
    pyramid = {'intention': [], 'contrainte': [], 'contexte': [], 'bruit': [], 'meta': []}
    for seg in raw:
        if any(p.search(seg) for p in _META_RE):
            pyramid['meta'].append(seg)
        elif any(p.search(seg) for p in _CONTRAINTE_RE) or any(p.search(seg) for p in _FORMAT_RE):
            pyramid['contrainte'].append(seg)
        elif any(p.search(seg) for p in _CONTEXTE_RE):
            pyramid['contexte'].append(seg)
        else:
            # Bruit = après nettoyage des règles, il reste < 3 mots
            cleaned = seg
            for p, repl, _ in _POLITESSE + _VERBEUX + _REDONDANCES:
                cleaned = re.sub(p, repl, cleaned, flags=re.IGNORECASE)
            cleaned = cleaned.strip(' ,;.')
            if len(cleaned.split()) < 3:
                pyramid['bruit'].append(seg)
            else:
                pyramid['intention'].append(seg)
    return pyramid


# Coréférence en tête de segment — déplacer une phrase qui commence par un
# pronom anaphorique casserait son référent. On skip dans ce cas.
_ANAPHORA_RE = re.compile(
    r"^\s*(ce|cette|cet|cela|[çc]a|il|elle|ils|elles|le|la|les|lui|leur|y|en)\b",
    re.IGNORECASE)


def _restructure_scaffold(text: str) -> tuple[str, bool]:
    """Socle déterministe « lead with the ask » : remonte la phrase de demande
    (verbe de tâche ou '?') en tête, garde le reste dans l'ordre.
    Sûr par construction : un seul segment déplacé, ordre du contexte préservé,
    garde anti-coréférence. Retourne (texte, restructured)."""
    segs = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s.strip()]
    if len(segs) < 2:
        return text, False
    # Dernière phrase portant la demande (les prompts bavards énoncent l'ask en fin)
    idx = next((i for i in range(len(segs) - 1, -1, -1)
                if _TASK_VERBS_RE.search(segs[i]) or '?' in segs[i]), None)
    if idx is None or idx == 0:
        return text, False
    if _ANAPHORA_RE.search(segs[idx]):
        return text, False  # déplacer casserait le référent
    lead = segs[idx]
    rest = segs[:idx] + segs[idx + 1:]
    return lead + ' ' + ' '.join(rest), True


def _capitalize_sentences(text: str) -> str:
    """Majuscule en tête de texte et après chaque ponctuation forte."""
    text = re.sub(r'^\s*[a-zà-ÿ]', lambda m: m.group(0).upper(), text)
    text = re.sub(r'([.!?]\s+)([a-zà-ÿ])',
                  lambda m: m.group(1) + m.group(2).upper(), text)
    return text


def _compute_quality_note(final, tokens_before, tokens_after, junk_density,
                          restructured, is_underspecified, is_generic):
    """Note qualité 4 axes (v0, déterministe, additive — ne remplace pas pertinence_score).
    Spécificité est heuristique pour l'instant (sera affinée par missing_components/E3)."""
    words = final.split()
    n = max(1, len(words))
    filler = sum(1 for w in words if w.lower().strip(",.!?;:") in _FILLER_WORDS)
    hedge = len(_RESIDUAL_HEDGE_RE.findall(final))
    # Clarté = inverse de la densité de remplisseurs/hedges RÉSIDUELS du texte final
    clarte = max(0, min(100, round(100 - (filler + hedge) / n * 180)))
    reduc = (tokens_before - tokens_after) / tokens_before if tokens_before else 0
    concision = max(0, min(100, round(50 + reduc * 100)))
    has_constraint = (any(p.search(final) for p in _CONTRAINTE_RE)
                      or any(p.search(final) for p in _FORMAT_RE))
    structure = max(0, min(100, 50 + (30 if restructured else 0) + (20 if has_constraint else 0)))
    spec = 70
    if is_underspecified:
        spec -= 40
    if is_generic:
        spec -= 20
    if re.search(r'\d', final):
        spec += 10
    if any(p.search(final) for p in _FORMAT_RE):
        spec += 10
    specificite = max(0, min(100, spec))
    glob = round(clarte * 0.25 + specificite * 0.30 + structure * 0.25 + concision * 0.20)
    return {'clarte': clarte, 'specificite': specificite,
            'structure': structure, 'concision': concision, 'global': glob}


def _protect_constraints(text):
    """Remplace les segments contrainte par des marqueurs pour les protéger des règles."""
    parts = re.split(r'(\s*[.!?;]\s+|\n+)', text)
    protected = {}
    result = []
    current = ''
    for part in parts:
        if re.fullmatch(r'\s*[.!?;]\s+|\n+', part):
            seg = current.strip()
            if seg and any(p.search(seg) for p in _CONTRAINTE_RE):
                key = f'__HC{len(protected)}__'
                protected[key] = current
                result.append(key + part)
            else:
                result.append(current + part)
            current = ''
        else:
            current = part
    if current.strip():
        if any(p.search(current.strip()) for p in _CONTRAINTE_RE):
            key = f'__HC{len(protected)}__'
            protected[key] = current
            result.append(key)
        else:
            result.append(current)
    return ''.join(result), protected


def _restore_constraints(text, protected):
    for key, val in protected.items():
        text = text.replace(key, val)
    return text


def _apply_rules(text, rules):
    used = []
    for pattern, repl, label in rules:
        new_text, n = re.subn(pattern, repl, text, flags=re.IGNORECASE)
        if n > 0:
            text = new_text
            used.append((label, n))
    return text, used


# ── Phase 1 — Analyse silencieuse des segments ────────────────────────────────

# Lexique3 — chargé au démarrage, vide si bootstrap pas encore fait
from utils.lexique_bootstrap import load as _load_lexique
_LEXIQUE_SCORES: dict[str, float] = _load_lexique()

_FILLER_WORDS = frozenset({
    'trop', 'vraiment', 'juste', 'genre', 'quoi', 'hein', 'bref',
    'super', 'vachement', 'carrément', 'franchement', 'sincèrement',
    'clairement', 'évidemment', 'naturellement', 'forcément',
})

# Hedges/remplisseurs résiduels — sert à mesurer la clarté du texte FINAL
_RESIDUAL_HEDGE_RE = re.compile(
    r"\b(un peu|en gros|genre|du coup|en fait|vraiment|trop|super|en vrai|"
    r"quoi|bref|peut-être|une sorte de|des trucs?)\b", re.IGNORECASE)

_SOCIAL_STARTERS = re.compile(
    r"^(j['’]esp[eè]re|dis[,\s]|coucou|je me demandais|je voulais te demander"
    r"|bon[,\s]|allez[,\s]|alors[,\s]+voil[aà]|salut[,\s!])",
    re.IGNORECASE,
)


def _score_segment_noise(sentence: str) -> float:
    """Score de bruit 0.0 (signal pur) → 1.0 (bruit pur) pour un segment."""
    t = sentence.lower().strip()
    words = t.split()
    n = len(words)
    if n == 0:
        return 1.0

    score = 0.5

    # ── Signaux → baisse le score (c'est du contenu) ──
    if _TASK_VERBS_RE.search(t):                    score -= 0.35
    if '?' in sentence:                             score -= 0.25
    if re.search(r'\b(comment|pourquoi|quand|où|quel|quelle)\b', t): score -= 0.15
    if n > 12:                                      score -= 0.10

    # ── Bruit → monte le score ──
    if any(p.search(sentence) for p in _PHRASES_BRUIT_RE): score += 0.45
    if _SOCIAL_STARTERS.search(sentence):           score += 0.40
    glossary_hits = sum(
        1 for ph, sc, _ in NOISE_GLOSSARY if sc >= NOISE_THRESHOLD and ph.lower() in t
    )
    score += glossary_hits * 0.20
    # Signal Lexique3 : score moyen des mots connus à bruit élevé
    if _LEXIQUE_SCORES:
        lex_hits = [_LEXIQUE_SCORES[w] for w in words if w in _LEXIQUE_SCORES]
        if lex_hits:
            score += (sum(lex_hits) / len(lex_hits) - 0.55) * 0.40
    filler_ratio = sum(1 for w in words if w in _FILLER_WORDS) / n
    score += filler_ratio * 0.30
    if n <= 5 and not _TASK_VERBS_RE.search(t):    score += 0.20

    return max(0.0, min(1.0, score))


def detect_noise_candidates(text: str) -> list[dict]:
    """Phase 1 : détecte les segments bruités non couverts par les règles existantes.
    Retourne une liste de candidats à stocker dans le dataset.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    candidates = []
    all_rules = (
        _SOCIAL_FILLER + _POLITESSE + _VERBEUX + _REDONDANCES +
        _INTRO_CONVOS + _REDONDANCES_ORALES + _HEDGES + _INTENSIFIERS
    )

    for sent in sentences:
        sent = sent.strip()
        if not sent or len(sent.split()) < 3:
            continue

        score = _score_segment_noise(sent)
        if score < 0.65:
            continue

        already_covered = (
            any(p.search(sent) for p in _PHRASES_BRUIT_RE) or
            any(re.search(p, sent, re.IGNORECASE) for p, _, _ in all_rules) or
            any(ph.lower() in sent.lower() for ph, sc, _ in NOISE_GLOSSARY if sc >= NOISE_THRESHOLD)
        )
        if not already_covered:
            candidates.append({'text': sent, 'score': round(score, 3)})

    return candidates


_CONNECTORS = re.compile(
    r'^(bon alors?|alors|bref|du coup|en gros|mais|donc|or|cependant|néanmoins)[,\s]+',
    re.IGNORECASE,
)


_PREP_RE = re.compile(
    r'^(à|de|du|des|en|sur|sous|avec|par|pour|sans|dans|vers|chez)\b',
    re.IGNORECASE,
)


def _remove_short_fragments(text: str) -> str:
    """Supprime les fragments orphelins générés par le pipeline.
    - Clause prépositionnelle courte après connecteur : 'bon alors, à cause du stress.'
    - Fragment < 3 mots significatifs sans verbe de tâche.
    Ne touche pas aux phrases complètes même courtes ('Explique-moi X.')."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    kept = []
    for s in sentences:
        stripped = s.strip()
        content = _CONNECTORS.sub('', stripped).strip(' ,;')
        words = content.split()
        # Clause prépositionnelle sans verbe principal (ex: "à cause du stress")
        orphan_prep = _PREP_RE.match(content) and len(words) < 7 and not _TASK_VERBS_RE.search(content)
        # Fragment trop court — mais pas si c'est une phrase complète (majuscule + ponctuation)
        is_complete = bool(stripped) and stripped[0].isupper() and stripped[-1] in '.!?'
        orphan_short = len(words) < 3 and len(stripped.split()) < 5 and not is_complete
        if orphan_prep or orphan_short:
            continue
        kept.append(s)
    return ' '.join(kept).strip() if kept else text


def _clean_whitespace(text):
    # Guillemets/apostrophes typographiques en début de texte (bloquent les patterns ^)
    text = re.sub(r'^[“”‘’«»"\']+\s*', '', text)
    # Espaces multiples
    text = re.sub(r'[ \t]+', ' ', text)
    # Ponctuation orpheline en début de phrase/texte (ex: ", j'ai", ". on doit")
    text = re.sub(r'^[ ,;.]+\s*', '', text, flags=re.MULTILINE)
    # Virgule orpheline après ponctuation de fin (ex: ". , j'ai" → ". j'ai")
    text = re.sub(r'([.!?])\s+,\s*', r'\1 ', text)
    # Connecteurs orphelins avant ponctuation (ex: "pistes ou ?", "et .", "ou ,")
    text = re.sub(r'\b(ou|et|mais|donc|car|ni)\s*([,.\?!])', r'\2', text, flags=re.IGNORECASE)
    # Double ponctuation (ex: ", .", "? .", ", ,")
    text = re.sub(r'([,;])\s*([,;.])', r'\2', text)
    text = re.sub(r'\.\s*\.', '.', text)
    # Ponctuation forte suivie d'un point (ex: "quotidien?." -> "quotidien?")
    text = re.sub(r'([?!])\s*\.', r'\1', text)
    # Espace avant ponctuation
    text = re.sub(r' ([,;.?!])', r'\1', text)
    # Virgule en fin de phrase avant majuscule ou fin de texte
    text = re.sub(r',\s*([A-ZÀ-Ü])', r'. \1', text)
    return text.strip()


def _compute_junk_density(text: str) -> float:
    """Ratio 0.0–1.0 de chars méta détectés (rôle IA + instructions comportementales + qualificateurs vides) vs longueur totale."""
    junk_chars = sum(
        len(m.group())
        for p, _, _ in _ROLE_ASSIGN_RULES + _META_INSTR_RULES
        for m in re.finditer(p, text, re.IGNORECASE | re.DOTALL)
    )
    qual_chars = sum(
        len(m.group())
        for p, _, _ in _EMPTY_QUAL_RULES
        for m in re.finditer(p, text, re.IGNORECASE)
    )
    return min(1.0, (junk_chars + qual_chars) / max(1, len(text)))


_TASK_VERBS_RE = re.compile(
    r'\b(explique[szr]?|expliquer|décris?|décrire|génère[szr]?|générer'
    r'|crée[szr]?|créer|donne[szr]?|donner|liste[szr]?|lister'
    r'|analyse[szr]?|analyser|compare[szr]?|comparer|montre[szr]?|montrer'
    r'|écris?|écrire|résume[szr]?|résumer|définis?|définir'
    r'|comment|pourquoi|quand|help|show|list|explain|give|write|create|generate)\b',
    re.IGNORECASE,
)

_ARTICLES_RE = re.compile(
    r'\b(le|la|les|un|une|des|du|au|aux|the|a|an)\b', re.IGNORECASE
)

_INCOMPLETE_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"comment\s+(?:faire|on\s+fait|ça\s+marche|fonctionne|utiliser|je)\s*$",
        r"(?:est-ce\s+que|est-ce\s+qu)\s*$",
        r"(?:j[’']aurais?|j[’']aimerais?|je\s+voudrais?)\s+(?:savoir|comprendre|que\s+tu)\s*$",
        r"(?:peux?-tu|pourr?ais?-tu|pourr?iez?-vous)\s+(?:m[’'e]|me|nous)?\s*$",
        r"\bque?\s+(?:tu|vous)\s+(?:me|nous)?\s*$",
        r"\bcomment\s+[a-zà-ÿ]+\s*$",
    ]
]


def _detect_underspecified(text: str) -> dict:
    """Détecte les prompts trop vagues, télégraphiques ou incomplets."""
    words = text.split()
    n = len(words)
    stripped = text.strip()

    # Langage télégraphique : très court + pas d'articles + longueur moyenne mot < 5
    avg_len = sum(len(w.strip('.,!?')) for w in words) / max(1, n)
    article_count = len(_ARTICLES_RE.findall(text))
    has_task_verb = bool(_TASK_VERBS_RE.search(text))
    is_telegraphic = n <= 7 and article_count == 0 and avg_len < 6 and has_task_verb

    # Cave-man : très court SANS verbe de tâche non plus → vraiment brut
    is_caveman = n <= 5 and not has_task_verb and n > 0

    # Phrase incomplète : finit sur un mot grammatical déclencheur sans complément
    ends_without_punct = not re.search(r'[.!?]$', stripped)
    is_incomplete = any(p.search(stripped) for p in _INCOMPLETE_PATTERNS) and ends_without_punct

    return {
        'is_underspecified': is_telegraphic or is_caveman,
        'is_incomplete':     is_incomplete,
        'underspec_type':    'caveman' if is_caveman else ('telegraphic' if is_telegraphic else None),
    }


def _detect_list_in_prose(text):
    sentences = [s.strip() for s in re.split(r'[.!?]', text) if len(s.strip()) > 50]
    for sentence in sentences:
        parts = re.split(r'\b(et|puis|ensuite|,)\b', sentence)
        items = [p.strip() for p in parts
                 if p.strip() and p.strip() not in ('et', 'puis', 'ensuite', ',')]
        if len(items) >= 3:
            return True, items
    return False, None


def _detect_repeated_words(text):
    words = re.findall(r'\b[a-zA-Z\xc0-\xff]{5,}\b', text.lower())
    stopwords = {
        'comme', 'aussi', 'alors', 'apres', 'avant', 'votre', 'notre', 'leurs',
        'dans', 'avec', 'pour', 'cette', 'entre', 'jusqu', 'depuis', 'encore',
        'plusieurs', 'certains', 'chaque', 'quand', 'comment', 'toutes', 'toujours',
    }
    counts = {}
    for w in words:
        if w not in stopwords:
            counts[w] = counts.get(w, 0) + 1
    return {w: c for w, c in counts.items() if c > 2}


# ---------------------------------------------------------------------------
# Entree publique
# ---------------------------------------------------------------------------

def optimise(prompt: str, kwh_per_token: float | None = None, palier: str | None = None) -> dict:
    """
    Analyse et optimise un prompt.
    Retourne un dict avec :
      original, optimised, rules_applied, suggestions,
      tokens_before, tokens_after, tokens_saved, kwh_saved.
    """
    text = prompt.strip()
    tokens_before = estimate_tokens_from_text(text) if text else 0

    # Classification pyramide sur le texte original
    pyramid = _classify_segments(text) if text else {'intention': [], 'contrainte': [], 'contexte': [], 'bruit': [], 'meta': []}

    # Densité méta calculée sur le texte original
    junk_density = _compute_junk_density(text) if text else 0.0

    # Qualité du prompt original (avant nettoyage) — pour comparaison avant/après
    quality_note_original = _compute_quality_note(
        text, tokens_before, tokens_before, junk_density,
        False, False, junk_density > 0.35)

    # Étape 0 — suppression des phrases entières de politesse
    text, n_phrases = _remove_bruit_sentences(text)
    applied_labels = {}
    if n_phrases:
        applied_labels['phrases de politesse supprimées'] = n_phrases

    def _record(used):
        for label, n in used:
            applied_labels[label] = applied_labels.get(label, 0) + n

    # Étape 1 — transformations interrogatives → impératives
    text, used = _apply_rules(text, _INTERROGATIF)
    _record(used)

    # Protection des segments contrainte avant application des règles
    text, protected = _protect_constraints(text)

    # Étape 1b — bruit social / contextuel (salutations, météo, conclusions vides)
    text, used = _apply_rules(text, _SOCIAL_FILLER)
    _record(used)

    # Étapes 2-4 — règles mot/expression
    text, used = _apply_rules(text, _POLITESSE)
    _record(used)
    text, used = _apply_rules(text, _VERBEUX)
    _record(used)
    text, used = _apply_rules(text, _REDONDANCES)
    _record(used)

    # Étape 4b — bruit conversationnel oral (co-auteur)
    text, used = _apply_rules(text, _INTRO_CONVOS)
    _record(used)
    text, used = _apply_rules(text, _REDONDANCES_ORALES)
    _record(used)
    text, used = _apply_rules(text, _HEDGES)
    _record(used)
    text, used = _apply_rules(text, _INTENSIFIERS)
    _record(used)

    # Étape 4c — glossaire de bruit (score ≥ NOISE_THRESHOLD)
    text, glossary_labels = _apply_noise_glossary(text)
    for label, n in glossary_labels.items():
        applied_labels[label] = applied_labels.get(label, 0) + n

    # Étape 5 — règles méta-prompt (intérieur de la zone protégée)
    tokens_before_meta = estimate_tokens_from_text(text)
    text, used = _apply_rules(text, _META_PROMPT_RULES)
    _record(used)
    meta_tokens_removed = tokens_before_meta - estimate_tokens_from_text(text)

    text = _restore_constraints(text, protected)
    text = _clean_whitespace(text)
    text = _remove_short_fragments(text)

    # Socle déterministe E2 — « lead with the ask » (réordonnancement sûr)
    optimised_flat = text
    text, restructured = _restructure_scaffold(text)
    if restructured:
        text = _clean_whitespace(text)
        text = _capitalize_sentences(text)

    tokens_after = estimate_tokens_from_text(text) if text else 0
    # Supprimer du contenu ne peut pas augmenter les tokens — le tokenizer heuristique
    # peut fluctuer près du seuil d'accentuation si on retire des mots ASCII purs.
    tokens_after = min(tokens_after, tokens_before)
    tokens_saved = tokens_before - tokens_after

    rules_applied = [{'label': label, 'count': count}
                     for label, count in applied_labels.items()]

    suggestions = []

    is_list, items = _detect_list_in_prose(prompt)
    if is_list:
        suggestions.append({
            'type': 'format_liste',
            'message': ('Ce prompt contient une liste en prose -- reformuler en bullet points '
                        'reduit les tokens et ameliore la precision du modele.'),
            'example': '\n'.join('- ' + item for item in items[:5]),
        })

    repeated = _detect_repeated_words(prompt)
    if repeated:
        mots = ', '.join('"' + w + '" (' + str(c) + 'x)' for w, c in list(repeated.items())[:4])
        suggestions.append({
            'type': 'repetition',
            'message': 'Mots repetes detectes : ' + mots + '. Remplacez par un pronom ou restructurez.',
            'example': None,
        })

    if len(prompt) > 800:
        suggestions.append({
            'type': 'longueur',
            'message': ('Prompt long (>800 chars). Verifiez si tout le contexte est necessaire -- '
                        'supprimer les exemples evidents reduit fortement les tokens.'),
            'example': None,
        })

    underspec = _detect_underspecified(prompt.strip())
    if underspec['is_underspecified']:
        msg = (
            'Prompt trop telegraphique -- le modele manque de contexte. '
            'Ajoutez : la tache precise, le format attendu, le niveau de detail.'
            if underspec['underspec_type'] == 'telegraphic'
            else 'Prompt tres court -- precisez ce que vous attendez exactement.'
        )
        suggestions.append({'type': 'underspecified', 'message': msg, 'example': None})
    if underspec['is_incomplete']:
        suggestions.append({
            'type': 'incomplete',
            'message': 'Phrase incomplete -- votre requete semble s\'arreter avant la fin. Reformulez en phrase complete.',
            'example': None,
        })

    # Palier — détection auto ou sélection utilisateur
    user_chose_palier = palier in PALIERS
    palier_key = palier if user_chose_palier else detect_palier(prompt.strip())

    # Policy Engine : décider si on garde la contrainte de longueur (palier).
    # On ne sur-écrit JAMAIS un palier choisi explicitement par l'utilisateur.
    # Fallback robuste partout -> jamais de régression vs comportement actuel.
    gating_compress, gating_source, gating_conf = True, "disabled", 0.0
    if decide_policy is not None and not user_chose_palier:
        try:
            decision = decide_policy(prompt)
            gating_compress = decision.compress
            gating_source = decision.source
            gating_conf = decision.confidence
            if not gating_compress:
                palier_key = "5"   # sans contrainte -> réponse libre
        except Exception:
            gating_compress, gating_source = True, "fallback"

    palier_info = PALIERS[palier_key]
    est_output, max_output = _estimate_output_tokens(text, palier_key)
    baseline_output = PALIER_BASELINE_TOKENS.get(palier_key)
    savings_output_tokens = max(0, baseline_output - est_output) if (baseline_output and est_output) else None
    # La contrainte est retournée séparément — non incluse dans 'optimised'
    # Le frontend l'affiche comme chip verrouillé et la réappend à l'envoi
    palier_constraint = palier_info['constraint'] or None

    from utils.calculator import DEFAULT_KWH_PER_TOKEN
    rate = kwh_per_token if kwh_per_token is not None else DEFAULT_KWH_PER_TOKEN
    kwh_saved = round(tokens_saved * rate, 9)

    base_score = max(0, min(100, round((1 - tokens_saved / tokens_before) * 100))) if tokens_before > 0 else 100
    pertinence_score = max(0, min(100, base_score - round(junk_density * 60)))

    quality_note = _compute_quality_note(
        text, tokens_before, tokens_after, junk_density,
        restructured, underspec['is_underspecified'], junk_density > 0.35)

    return {
        'original':                prompt.strip(),
        'optimised':               text,
        'optimised_flat':          optimised_flat,
        'restructured':            restructured,
        'rules_applied':           rules_applied,
        'suggestions':             suggestions,
        'tokens_before':           tokens_before,
        'tokens_after':            tokens_after,
        'tokens_saved':            tokens_saved,
        'kwh_saved':               kwh_saved,
        'pertinence_score':        pertinence_score,
        'quality_note':            quality_note,
        'quality_note_original':   quality_note_original,
        'pyramid':                 pyramid,
        'palier':                  palier_key,
        'palier_label':            palier_info['label'],
        'palier_emoji':            palier_info['emoji'],
        'complexity':              detect_complexity(prompt.strip()),
        'chips':                   detect_chips(prompt.strip(), detect_complexity(prompt.strip())),
        'estimated_output_tokens': est_output,
        'output_tokens_max':       max_output,
        'baseline_output_tokens':  baseline_output,
        'savings_output_tokens':   savings_output_tokens,
        'is_underspecified':        underspec['is_underspecified'],
        'is_incomplete':           underspec['is_incomplete'],
        'underspec_type':          underspec['underspec_type'],
        'junk_density':            round(junk_density, 3),
        'is_generic_prompt':       junk_density > 0.35,
        'meta_tokens_removed':     meta_tokens_removed,
        'palier_constraint':       palier_constraint,
        'gating_compress':         gating_compress,
        'gating_source':           gating_source,
        'gating_confidence':       gating_conf,
        'noise_candidates':        detect_noise_candidates(prompt.strip()),
    }
