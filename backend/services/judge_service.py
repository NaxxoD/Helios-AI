"""
judge_service — Couche 2 de la grille de qualité (docs/recherche/grille-qualite-helios.md).

Juge sémantique ANCRÉ pour l'évaluation offline de non-dégradation :
  - Profil A : non-régression vs réponse baseline (palier / compression).
  - Profil B : conformité à un barème de tâche (restructuration / swap de modèle).
  - generate_bareme() : barème construit BLIND (à partir du prompt seul, jamais des
    réponses) → ne peut pas être biaisé vers une réponse. Distingue essentiel/bonus
    pour éviter le biais inverse (sur-créditer la verbosité).
  - cohen_kappa() : accord inter-juges = fiabilité des labels (§7). C'est le verrou
    du projet : labels bruités = plafond 0.59. À mesurer AVANT d'entraîner dessus.

Découplé de chat_service (pas de palier, pas de FastAPI) : juge déterministe,
sortie JSON stricte. httpx synchrone (comme qm_evaluate) → utilisable en script
offline. Backend juge : "anthropic" (premium, Opus) ou "ollama" (2e juge cheap κ).

Les fonctions PURES (cohen_kappa, remap_profil_a, score_bareme, verdict_profil_b,
compare_profil_b) n'appellent aucun LLM → testées unitairement sans réseau.
"""
from __future__ import annotations
import json, random, re, time
from typing import Optional
import httpx

# Miroir local de chat_service._ANTHROPIC_IDS (gardé ici pour le découplage)
_ANTHROPIC_IDS = {
    "claude-opus-4-8":   "claude-opus-4-8",
    "claude-opus-4-7":   "claude-opus-4-7",
    "claude-sonnet-4-6": "claude-sonnet-4-6",
    "claude-haiku-4-5":  "claude-haiku-4-5-20251001",
}

_STATUT_POIDS = {"couvert": 1.0, "partiel": 0.5, "absent": 0.0}

# ===========================================================================
# Fonctions PURES (testables sans réseau)
# ===========================================================================

def cohen_kappa(labels_a: list, labels_b: list) -> float:
    """Kappa de Cohen entre deux séries d'étiquettes catégorielles appariées.

    Mesure l'accord AU-DELÀ du hasard : 1 = accord parfait, 0 = niveau du hasard,
    < 0 = pire que le hasard. C'est le thermomètre de fiabilité de la grille (§7).
    """
    if len(labels_a) != len(labels_b):
        raise ValueError("séries de longueurs différentes")
    n = len(labels_a)
    if n == 0:
        raise ValueError("séries vides")
    p_o = sum(1 for a, b in zip(labels_a, labels_b) if a == b) / n
    # accord attendu par hasard, depuis les marginales de chaque juge
    cats = set(labels_a) | set(labels_b)
    p_e = sum((labels_a.count(c) / n) * (labels_b.count(c) / n) for c in cats)
    if p_e >= 1.0:          # une seule catégorie des deux côtés → accord trivial
        return 1.0
    return (p_o - p_e) / (1.0 - p_e)


def remap_profil_a(raw: dict, swap: bool) -> dict:
    """Traduit la sortie symétrique du juge ({meilleure: 1|2|egal, ...}) en un
    verdict orienté CANDIDATE vs RÉFÉRENCE, puis applique l'arbre §5.

    swap=True  → la candidate était affichée en "Réponse 1".
    swap=False → la candidate était affichée en "Réponse 2".
    """
    cand = "1" if swap else "2"
    meilleure = str(raw.get("meilleure", "?"))
    if meilleure == cand:
        cvr = "meilleure"
    elif meilleure == "egal":
        cvr = "egal"
    else:
        cvr = "moins_bonne"

    exa_ko = str(raw.get("exactitude_ko", "aucune"))
    candidate_exa_ko = (exa_ko == cand)
    ecart = str(raw.get("ecart", "aucun"))

    # Arbre de décision §5 (veto exactitude, sinon sévérité de l'écart)
    if candidate_exa_ko:
        verdict = "inacceptable"
    elif cvr in ("meilleure", "egal"):
        verdict = "equivalent"
    elif ecart == "majeur":
        verdict = "inacceptable"
    else:                                   # moins_bonne + écart mineur
        verdict = "tolerable"

    return {
        "candidate_vs_ref": cvr,
        "exactitude_candidate_ko": candidate_exa_ko,
        "ecart": ecart,
        "verdict": verdict,
        "justification": raw.get("justification", ""),
        "_swap": swap,
    }


def score_bareme(bareme: list, couverture: list) -> dict:
    """Agrège la couverture d'une réponse contre un barème.

    bareme     : [{id, element, essentiel}]
    couverture : [{id, statut: "couvert"|"partiel"|"absent"}]
    couvert=1.0, partiel=0.5, absent=0.0.
    """
    statut = {c.get("id"): c.get("statut", "absent") for c in couverture}
    ess_ids = [e.get("id") for e in bareme if e.get("essentiel")]
    all_ids = [e.get("id") for e in bareme]

    def moy(ids):
        if not ids:
            return 1.0
        return sum(_STATUT_POIDS.get(statut.get(i, "absent"), 0.0) for i in ids) / len(ids)

    ess_absents = sum(1 for i in ess_ids if statut.get(i, "absent") == "absent")
    return {
        "score_essentiel": round(moy(ess_ids), 3),
        "score_global": round(moy(all_ids), 3),
        "essentiel_absents": ess_absents,
        "n_essentiel": len(ess_ids),
    }


def verdict_profil_b(score: dict, exactitude_ok: bool) -> str:
    """Verdict ternaire de conformité d'UNE réponse à son barème (§5 adapté)."""
    if not exactitude_ok:
        return "inacceptable"
    if score.get("essentiel_absents", 0) > 0:      # un élément requis manque
        return "inacceptable"
    if score.get("score_essentiel", 0.0) >= 0.999:  # tout l'essentiel couvert
        return "equivalent"
    return "tolerable"                              # essentiel partiellement couvert


def compare_profil_b(score_ref: dict, score_cand: dict, seuil: float = 0.1) -> str:
    """Compare deux réponses en Profil B (la question 'densité' : qui couvre mieux
    l'essentiel ?). Renvoie le verdict orienté candidate."""
    delta = score_cand.get("score_essentiel", 0.0) - score_ref.get("score_essentiel", 0.0)
    if delta > seuil:
        return "candidate_meilleure"
    if delta < -seuil:
        return "candidate_moins_bonne"
    return "equivalent"


# ===========================================================================
# Appels LLM (IO — non testés unitairement)
# ===========================================================================

def _extract_json(raw: str) -> dict:
    """Extrait le 1er objet JSON d'une sortie LLM (tolère texte autour + <think>)."""
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        raise ValueError(f"pas de JSON dans la réponse juge : {raw[:200]}")
    return json.loads(m.group(0))


def _post_with_retry(url: str, headers: dict, json_body: dict,
                     timeout: float = 180.0, retries: int = 3):
    """POST httpx avec retry sur timeout / erreur transport / 429 / 5xx (backoff
    linéaire). retour du co-auteur : 1 timeout sur ~100 appels tuait tout le run."""
    for attempt in range(retries):
        try:
            r = httpx.post(url, headers=headers, json=json_body, timeout=timeout)
            if r.status_code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            return r
        except (httpx.TimeoutException, httpx.TransportError):
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise   # dernier essai : on relève l'exception courante


def _call_anthropic(system: str, user: str, model: str, api_key: str,
                    max_tokens: int, temperature: Optional[float]) -> str:
    body: dict = {
        "model": _ANTHROPIC_IDS.get(model, model),
        "max_tokens": max_tokens,
        "system": [{"type": "text", "text": system}],
        "messages": [{"role": "user", "content": user}],
    }
    if temperature is not None:
        body["temperature"] = temperature
    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01",
               "content-type": "application/json"}
    url = "https://api.anthropic.com/v1/messages"
    r = _post_with_retry(url, headers, body)
    # Certains modèles récents (Opus adaptatif) refusent 'temperature' → retry sans
    if r.status_code == 400 and "temperature" in r.text.lower():
        body.pop("temperature", None)
        r = _post_with_retry(url, headers, body)
    r.raise_for_status()
    data = r.json()
    return next((b["text"] for b in data["content"] if b["type"] == "text"), "")


def _call_ollama(system: str, user: str, model: str,
                 base: str = "http://localhost:11434") -> str:
    r = _post_with_retry(f"{base}/api/chat", {}, {
        "model": model, "stream": False, "options": {"temperature": 0},
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
    })
    r.raise_for_status()
    return r.json().get("message", {}).get("content", "")


def _judge_call(system: str, user: str, *, model: str, api_key: Optional[str],
                backend: str, max_tokens: int = 1500,
                temperature: Optional[float] = 0.0) -> str:
    if backend == "anthropic":
        if not api_key:
            raise ValueError("api_key requis pour le backend anthropic")
        return _call_anthropic(system, user, model, api_key, max_tokens, temperature)
    if backend == "ollama":
        return _call_ollama(system, user, model)
    raise ValueError(f"backend juge inconnu : {backend}")


# ---------------------------------------------------------------------------
# Barème (Profil B) — généré BLIND, à partir du prompt seul
# ---------------------------------------------------------------------------

_BAREME_SYS = (
    "Tu construis un BARÈME d'évaluation à partir d'une DEMANDE utilisateur, SANS "
    "voir aucune réponse. Liste ce qu'une bonne réponse DOIT contenir pour "
    "satisfaire la demande.\n"
    "Règles STRICTES :\n"
    "- Uniquement des éléments VÉRIFIABLES (présent / absent), pas de jugement vague.\n"
    "- Distingue 'essentiel' (true : la réponse échoue sans) de 'bonus' (false : "
    "apprécié mais non requis).\n"
    "- Maximum 6 éléments, PRIVILÉGIE l'essentiel. N'invente PAS d'exigences que la "
    "demande ne réclame pas — sinon tu favorises artificiellement les réponses "
    "longues.\n"
    'Réponds UNIQUEMENT en JSON : '
    '{"elements": [{"id": 1, "element": "...", "essentiel": true}]}'
)


def generate_bareme(prompt: str, *, model: str = "claude-opus-4-8",
                    api_key: Optional[str] = None,
                    backend: str = "anthropic") -> list[dict]:
    """Génère le barème d'une demande, à l'aveugle des réponses. À hand-reviewer
    pour N petit (le doc §4.0 le recommande sur les 20 paires)."""
    raw = _judge_call(_BAREME_SYS, f"DEMANDE :\n{prompt}\n\nConstruis le barème.",
                      model=model, api_key=api_key, backend=backend)
    elements = _extract_json(raw).get("elements", [])
    return [{"id": e.get("id", i), "element": str(e.get("element", "")).strip(),
             "essentiel": bool(e.get("essentiel", True))}
            for i, e in enumerate(elements, 1)]


# ---------------------------------------------------------------------------
# Profil A — non-régression vs réponse baseline (comparatif, anti-biais)
# ---------------------------------------------------------------------------

_PROFIL_A_SYS = (
    "Tu es un évaluateur STRICT et impartial. On te donne une DEMANDE et DEUX "
    "réponses (1 et 2). Dis laquelle satisfait le mieux le besoin.\n"
    "- IGNORE le style et la longueur : une réponse plus courte qui garde "
    "l'information n'est PAS moins bonne.\n"
    "- Juge pertinence, exactitude, complétude par rapport à la demande.\n"
    "- Signale si une réponse contient une erreur factuelle ou un contresens "
    "(absent de l'autre).\n"
    'Réponds UNIQUEMENT en JSON : {"meilleure": "1"|"2"|"egal", '
    '"ecart": "aucun"|"mineur"|"majeur", '
    '"exactitude_ko": "aucune"|"1"|"2", "justification": "..."}'
)


def judge_profil_a(prompt: str, reference: str, candidate: str, *,
                   model: str = "claude-opus-4-8", api_key: Optional[str] = None,
                   backend: str = "anthropic", seed: Optional[str] = None) -> dict:
    """Profil A : la candidate dégrade-t-elle vs la réponse baseline ?
    Ordre 1/2 randomisé (seed déterministe) → pas de biais de position."""
    rng = random.Random(seed if seed is not None else prompt)
    swap = rng.random() < 0.5
    r1, r2 = (candidate, reference) if swap else (reference, candidate)
    user = (f"DEMANDE :\n{prompt}\n\n--- Réponse 1 ---\n{r1}\n\n"
            f"--- Réponse 2 ---\n{r2}\n\nÉvalue.")
    raw = _extract_json(_judge_call(_PROFIL_A_SYS, user, model=model,
                                    api_key=api_key, backend=backend))
    return remap_profil_a(raw, swap)


# ---------------------------------------------------------------------------
# Profil B — conformité d'UNE réponse à son barème (absolu, pas de comparaison)
# ---------------------------------------------------------------------------

_PROFIL_B_SYS = (
    "Tu évalues une RÉPONSE contre un BARÈME (liste d'éléments attendus). Pour "
    "CHAQUE élément du barème, dis s'il est 'couvert', 'partiel' ou 'absent' dans "
    "la réponse. Signale aussi toute erreur factuelle dans la réponse.\n"
    "Ne juge QUE la présence des éléments du barème, pas le style.\n"
    'Réponds UNIQUEMENT en JSON : {"couverture": [{"id": 1, "statut": '
    '"couvert"|"partiel"|"absent"}], "exactitude_ok": true, "justification": "..."}'
)


def judge_profil_b(prompt: str, bareme: list, response: str, *,
                   model: str = "claude-opus-4-8", api_key: Optional[str] = None,
                   backend: str = "anthropic") -> dict:
    """Profil B : couverture du barème par une réponse. Renvoie scores + verdict.
    Pour la 'densité', appeler sur ref ET candidate puis compare_profil_b()."""
    bareme_txt = "\n".join(
        f"{e.get('id', i)}. [{'essentiel' if e.get('essentiel') else 'bonus'}] {e.get('element', '')}"
        for i, e in enumerate(bareme))
    user = (f"DEMANDE :\n{prompt}\n\nBARÈME :\n{bareme_txt}\n\n"
            f"--- RÉPONSE ---\n{response}\n\nÉvalue la couverture.")
    raw = _extract_json(_judge_call(_PROFIL_B_SYS, user, model=model,
                                    api_key=api_key, backend=backend))
    couverture = raw.get("couverture", [])
    exactitude_ok = bool(raw.get("exactitude_ok", True))
    score = score_bareme(bareme, couverture)
    return {
        **score,
        "exactitude_ok": exactitude_ok,
        "verdict": verdict_profil_b(score, exactitude_ok),
        "couverture": couverture,
        "justification": raw.get("justification", ""),
    }
