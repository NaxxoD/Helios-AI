"""Sous-agent mémoire (Jalon 3) — compaction de la Couche B.

Spec : docs/produit/sous-agent-memoire-helios.md. Worker CONTRAINT (pas un agent autonome) :
il résume le vieil historique, garde KEEP tours verbatim, et son résumé passe par un
gate de fidélité (Couche 1 déterministe) + un gate de COHÉRENCE D'ÉTAT (retour retour du co-auteur).

Ce module est volontairement SYNCHRONE et sans I/O réseau : il fournit les briques
déterministes (plan de compaction, gates, prompts). L'appel au modèle résumeur (async)
est branché par l'orchestrateur, qui injecte le résultat dans HeliosCall.context.
"""
from typing import Callable, Optional

from utils.calculator import estimate_tokens_from_text
from utils import quality_gates

KEEP_DEFAULT = 4        # derniers tours gardés VERBATIM (fidélité d'état)
SEUIL_DEFAULT = 8000    # seuil de tokens du vieil historique qui déclenche la compaction

# System prompt du sous-agent (spec §3) — passé comme `role` à call_llm (→ system).
MEMORY_SYS = (
    "# SOUS-AGENT MÉMOIRE — Helios\n\n"
    "## Tâche\nTu es le sous-agent MÉMOIRE. On te fournit le DÉBUT d'une conversation "
    "(tours anciens). Produis un RÉSUMÉ STRUCTURÉ qui REMPLACERA ce passé brut dans le "
    "contexte de l'agent principal — un LLM qui n'a JAMAIS vu le brut. But : qu'il continue "
    "sans rien perdre.\n\n"
    "## Format (sections ; omets les vides ; puces courtes, un fait par ligne)\n"
    "- Objectif / fil courant\n- Parcours / chronologie (séquence + blocages RÉSOLUS)\n"
    "- Décisions & faits actés\n- Entités / chiffres / fichiers\n- Questions ouvertes\n\n"
    "## Scope (compresser SANS perte — la fidélité prime sur le taux)\n"
    "Jette : politesses, ré-explications, tangentes mortes, verbosité, style.\n"
    "Ne jette JAMAIS : une décision, un chiffre, une entité, une question ouverte, un "
    "blocage et sa résolution, l'ordre des événements. Doute → GARDE.\n"
    "Plafond ~85% de réduction : n'aspire PAS à compresser plus ; sur un historique dense, "
    "comprime MOINS.\n\n"
    "## Fidélité\nChaque élément doit être présent dans le brut. N'invente rien, ne déduis "
    "rien qui n'y est pas.\n\n"
    "## Sortie\nUNIQUEMENT le résumé structuré. Pas de préambule. Auto-suffisant."
)

# Gate de cohérence d'état (retour du co-auteur) — juge dédié, focalisé sur la contradiction d'état.
STATE_GATE_SYS = (
    "Tu vérifies la COHÉRENCE D'ÉTAT d'un résumé. On te donne l'HISTORIQUE BRUT (vérité) "
    "et un RÉSUMÉ censé le remplacer. Question UNIQUE : une affirmation du résumé "
    "CONTREDIT-elle l'état FINAL du brut ? (ex : le résumé dit « bloqué » alors que le brut "
    "finit sur « résolu »). Ignore le style, la couverture, la longueur — seulement les "
    'contradictions d\'état. JSON SEUL : {"contradiction": true|false, "detail": "..."}'
)

def render_history(messages: list) -> str:
    """Rend une liste de tours en texte brut étiqueté par rôle."""
    return "\n\n".join(f"[{m.get('role', '?')}] {m.get('content', '')}" for m in messages)


def summarizer_input(fold_render: str) -> str:
    """Enveloppe l'historique pour le résumeur. Consigne explicite « résume, ne continue pas ».

    ⚠️ NÉCESSAIRE MAIS INSUFFISANTE (mesuré, Palier Continuation n=40, analysis/qm/
    palier_continuation.py) : même avec, le résumeur CONTINUE la conversation ~18% du temps
    (67% quand le fold finit sur un tour user ; 14% sur assistant) au lieu de résumer. Le gate
    (Couche 1) reste le FAIL-SAFE : une continuation est rejetée → rollback → historique intact
    (qualité préservée, hit-rate compaction ~82%). Durcir le résumeur = travail restant."""
    return ("HISTORIQUE BRUT À RÉSUMER — ne le CONTINUE PAS, ne réponds PAS à l'utilisateur ; "
            "produis UNIQUEMENT le résumé structuré demandé dans tes instructions :\n\n" + fold_render)


def plan_compaction(messages: list, keep: int = KEEP_DEFAULT,
                    seuil: int = SEUIL_DEFAULT) -> dict:
    """Décide quoi plier. Pur/déterministe. `messages` = historique complet (message
    courant inclus, en dernier). Garde les KEEP derniers tours verbatim ; le reste = à plier.
    Compacte seulement si le vieux dépasse `seuil` ET qu'il reste des tours à plier."""
    if len(messages) <= keep:
        return {"should_compact": False, "fold": [], "recent": list(messages), "fold_tokens": 0}
    fold = messages[:-keep]
    recent = messages[-keep:]
    fold_tokens = sum(estimate_tokens_from_text(m.get("content") or "") for m in fold)
    return {"should_compact": fold_tokens > seuil, "fold": fold,
            "recent": recent, "fold_tokens": fold_tokens}


def coverage_gate(summary: str, fold: list) -> tuple[bool, str]:
    """Couche 1 (gratuit, déterministe) : pré-filtre cheap — le résumé n'est ni vide ni
    dégénéré (boucle / continuation répétitive).

    La couverture SÉMANTIQUE (perte de décision / entité / chiffre) est le job de la Couche 2
    (juge), PAS d'un comptage de nombres : MESURÉ (Palier Grille, 4.1c) qu'une règle « >50% des
    nombres du brut manquent → rejet » écarte ~100% des résumés FIDÈLES (un résumé abandonne par
    nature les nombres incidents d'un échange de 10-20 tours). Règle retirée. `fold` conservé
    pour l'interface (la Couche 2 l'utilise)."""
    if quality_gates.is_empty(summary):
        return False, "résumé vide"
    if quality_gates.is_degenerate_repetition(summary):
        return False, "résumé dégénéré (répétition)"
    return True, "ok"


def state_consistency_ok(summary: str, fold: list,
                         state_judge: Callable[[str, str], dict]) -> tuple[bool, str]:
    """Gate de cohérence d'état : le résumé contredit-il l'état FINAL du brut ?
    `state_judge(system, user) -> dict` (JSON déjà parsé). Injecté → testable sans réseau.

    ⚠️ MESURÉ FAIBLE (Palier État, n=120, analysis/qm/palierE_state_gate.py) : un juge LLM
    réalise mal ce gate — rappel Haiku 0% / Sonnet 25% sur des contradictions injectées (FP 4%).
    Conséquence : gate gardé DISPONIBLE mais NON câblé en live (state_judge=None par défaut) ;
    la fenêtre verbatim (KEEP derniers tours bruts) reste la protection PRIMAIRE de l'état."""
    user = f"=== BRUT ===\n{render_history(fold)}\n\n=== RÉSUMÉ ===\n{summary}\n\nVérifie."
    verdict = state_judge(STATE_GATE_SYS, user) or {}
    return (not bool(verdict.get("contradiction"))), str(verdict.get("detail", ""))


def evaluate_summary(summary: str, fold: list,
                     state_judge: Optional[Callable[[str, str], dict]] = None) -> tuple[bool, str]:
    """Combine les gates : Couche 1 (couverture) puis, si fournie, cohérence d'état.
    Renvoie (accepté, raison). `perte_grave`/contradiction → rollback côté orchestrateur."""
    ok, reason = coverage_gate(summary, fold)
    if not ok:
        return False, reason
    if state_judge is not None:
        ok_state, detail = state_consistency_ok(summary, fold, state_judge)
        if not ok_state:
            return False, f"contradiction d'état ({detail})"
    return True, "ok"
