"""Orchestrateur Helios (Jalon 2.3) — flux backend OPTIONNEL : optimise → route → adapt.

Activé via /chat/send `orchestrate=true` (off par défaut : sinon c'est le front qui
orchestre, en appelant /api/optimise puis /chat/send séparément). Câble le flux
gauche→droite du schéma cible côté serveur, sans changer le comportement existant.
"""
import asyncio
from typing import Callable, Optional

from utils.optimiseur import optimise
from utils.routing import suggest_routing
from services import chat_service, memory_service
from schemas.helios import HeliosCall, HeliosMessage


async def apply_memory(messages: list, api_key: str, *,
                       keep: int = memory_service.KEEP_DEFAULT,
                       seuil: int = memory_service.SEUIL_DEFAULT,
                       summarizer_model: str = "claude-haiku-4-5",
                       summarize: Optional[Callable] = None,
                       state_judge: Optional[Callable] = None) -> dict:
    """Sous-agent mémoire (Jalon 3) : si le vieil historique dépasse le seuil, le résume
    (modèle léger, SA propre fenêtre) et le fait valider par les gates (fidélité + cohérence
    d'état). Renvoie {compacted, context, messages, reason}. Sur rollback ou seuil non
    atteint : compacted=False et messages inchangés (aucune perte).

    `summarize(fold_render)->str` et `state_judge(sys,user)->dict` injectables (tests)."""
    plan = memory_service.plan_compaction(messages, keep, seuil)
    if not plan["should_compact"]:
        return {"compacted": False, "context": None, "messages": messages,
                "reason": "seuil non atteint"}
    fold = plan["fold"]

    async def _default_summarize(fold_render: str) -> str:
        res = await chat_service.call_llm(
            "Anthropic", summarizer_model, api_key,
            [{"role": "user", "content": memory_service.summarizer_input(fold_render)}],
            role=memory_service.MEMORY_SYS)
        return res["content"]

    summarize = summarize or _default_summarize
    summary = await summarize(memory_service.render_history(fold))

    ok, reason = memory_service.evaluate_summary(summary, fold, state_judge)
    if not ok:
        # rollback : on NE compacte pas ce tour (garde le brut) — qualité shippée préservée.
        return {"compacted": False, "context": None, "messages": messages,
                "reason": f"rollback ({reason})"}

    # P1/Pn : le résumé devient le `context` (invariable réinjecté), on ne garde que les
    # KEEP derniers tours verbatim (la variable).
    return {"compacted": True, "context": summary, "messages": plan["recent"],
            "reason": "ok", "fold_tokens": plan["fold_tokens"]}


async def orchestrate(provider: str, model: str, api_key: str, messages: list, *,
                      effort: Optional[str] = None, palier: Optional[str] = None,
                      role: Optional[str] = None, context: Optional[str] = None) -> dict:
    """Nettoie le dernier message user (heuristique locale), complète effort/palier via
    le routing si absents, construit un HeliosCall, puis appelle le LLM. Retourne le
    résultat LLM enrichi d'un bloc `orchestration` (traçabilité de ce qui a été fait)."""
    msgs = [dict(m) for m in messages]
    meta = {"optimised": False, "tokens_saved": 0,
            "suggested_effort": None, "suggested_model_tier": None}

    last_user = next((m for m in reversed(msgs) if m.get("role") == "user"), None)
    if last_user and last_user.get("content"):
        routing = suggest_routing(last_user["content"])
        meta["suggested_effort"] = routing.get("effort")
        meta["suggested_model_tier"] = routing.get("model_tier")
        if effort is None:
            effort = routing.get("effort")

        opt = await asyncio.to_thread(lambda: optimise(last_user["content"], palier=palier))
        last_user["content"] = opt.get("optimised") or last_user["content"]
        meta["optimised"] = bool(opt.get("tokens_saved"))
        meta["tokens_saved"] = opt.get("tokens_saved", 0)
        if palier is None:
            palier = opt.get("palier")

    call = HeliosCall(provider=provider, model=model,
                      messages=[HeliosMessage(**m) for m in msgs],
                      effort=effort, palier=palier, role=role, context=context)
    result = await chat_service.call_helios(call, api_key)
    result["orchestration"] = meta
    return result
