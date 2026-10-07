"""Feature Extractor : prompt -> vecteur numpy de longueur fixe.
Seul module qui parle à nomic-embed (Ollama). Réutilise la logique palier du backend.
"""
import re
import numpy as np
import httpx
from utils.optimiseur import detect_palier, _CONSTRAINT_MARKERS  # logique existante

OLLAMA_EMBED = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"
EMBED_DIM = 768

# ordre STABLE des paliers -> index numérique (feature)
_PALIER_ORDER = ['★', '0', '1', '2', '3', '4', '5', 'C', '6']

STRUCTURAL_NAMES = [
    "word_count", "char_count", "question_marks",
    "has_constraint", "is_code", "is_doc", "is_complex", "palier_idx",
]
N_STRUCTURAL = len(STRUCTURAL_NAMES)

_CODE_RE = re.compile(r"\b(fonction|function|code|python|sql|bug|script|classe)\b", re.I)
_DOC_RE = re.compile(r"\b(documentation|rédige|article|rapport|tutoriel)\b", re.I)
_COMPLEX_RE = re.compile(r"\b(compare|analyse|avantages|inconvénients|pourquoi|explique)\b", re.I)

# Contrainte de longueur numérique explicite (« 50 mots », « 3 lignes », « 100 caractères »…).
# Complète `_CONSTRAINT_MARKERS` du backend (qui ne couvre que « mots max », pas les limites chiffrées).
_NUM_CONSTRAINT_RE = re.compile(
    r"\b\d+\s*(mots?|words?|caractères?|characters?|lignes?|lines?|"
    r"phrases?|sentences?|bullets?|points?|paragraphes?|paragraphs?)\b",
    re.I,
)


class EmbeddingUnavailable(RuntimeError):
    pass


def _has_constraint(prompt: str) -> bool:
    low = prompt.lower()
    if any(m in low for m in _CONSTRAINT_MARKERS):
        return True
    return _NUM_CONSTRAINT_RE.search(prompt) is not None


def structural_features(prompt: str) -> np.ndarray:
    words = prompt.split()
    pk = detect_palier(prompt)
    vec = [
        float(len(words)),
        float(len(prompt)),
        float(prompt.count("?")),
        1.0 if _has_constraint(prompt) else 0.0,
        1.0 if _CODE_RE.search(prompt) else 0.0,
        1.0 if _DOC_RE.search(prompt) else 0.0,
        1.0 if _COMPLEX_RE.search(prompt) else 0.0,
        float(_PALIER_ORDER.index(pk) if pk in _PALIER_ORDER else -1),
    ]
    return np.array(vec, dtype=np.float32)


def embed(prompt: str, timeout: float = 15.0) -> np.ndarray:
    try:
        r = httpx.post(OLLAMA_EMBED, json={"model": EMBED_MODEL, "prompt": prompt}, timeout=timeout)
        r.raise_for_status()
        emb = r.json().get("embedding")
        if not emb or len(emb) != EMBED_DIM:
            raise EmbeddingUnavailable(f"embedding invalide (len={len(emb) if emb else 0})")
        return np.array(emb, dtype=np.float32)
    except EmbeddingUnavailable:
        raise
    except Exception as e:
        raise EmbeddingUnavailable(str(e))


def extract_features(prompt: str) -> np.ndarray:
    """vecteur complet [embedding(768) | structurels(8)] -> shape (776,)"""
    return np.concatenate([embed(prompt), structural_features(prompt)])


FEATURE_DIM = EMBED_DIM + N_STRUCTURAL
