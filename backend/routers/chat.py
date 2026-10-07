from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from database import get_db
from dependencies import get_current_user, get_optional_user
from models import User
from repositories import session_repo, factor_repo
from services import chat_service, orchestrator_service
from utils.calculator import calculate_impact
from utils.cost_calculator import calculate_cost
from utils.parsers import OUTPUT_TOKEN_WEIGHT

router = APIRouter(tags=["chat"])
limiter = Limiter(key_func=get_remote_address)


class MessageIn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    provider: str
    model: str
    api_key: str
    messages: list[MessageIn]
    tokens_saved: int = 0
    effort: Optional[str] = None   # off|on|low|standard|medium|high|xhigh|max
    palier: Optional[str] = None   # ★|0|1|2|3|4|5|C|6
    role: Optional[str] = None     # persona/système (objet Helios)
    context: Optional[str] = None  # contexte additionnel (objet Helios)
    orchestrate: bool = False      # true → flux backend optimise→route→adapt (Jalon 2.3)
    memory: bool = False           # true → sous-agent mémoire : compacte la Couche B (Jalon 3)


class CompactRequest(BaseModel):
    provider: str
    model: str
    api_key: str
    messages: list[MessageIn]


@router.post("/send")
@limiter.limit("30/minute")
@limiter.limit("5/10seconds")
async def send_chat(
    request: Request,
    body: ChatRequest,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    msgs = [{"role": m.role, "content": m.content} for m in body.messages]
    ctx = body.context
    mem_block = None
    if body.memory:
        mem = await orchestrator_service.apply_memory(msgs, body.api_key)
        mem_block = {"compacted": mem["compacted"], "reason": mem["reason"]}
        if mem["compacted"]:
            msgs = mem["messages"]
            ctx = "\n\n".join(p for p in (ctx, mem["context"]) if p) or None

    if body.orchestrate:
        result = await orchestrator_service.orchestrate(
            body.provider, body.model, body.api_key, msgs,
            effort=body.effort, palier=body.palier, role=body.role, context=ctx)
    else:
        result = await chat_service.call_llm(
            body.provider, body.model, body.api_key, msgs,
            effort=body.effort, palier=body.palier, role=body.role, context=ctx)

    if mem_block is not None:
        result["orchestration"] = {**result.get("orchestration", {}), "memory": mem_block}

    tokens = result["input_tokens"] + result["output_tokens"] * OUTPUT_TOKEN_WEIGHT
    factor = factor_repo.get_by_provider_model(db, body.provider, body.model)
    impact = calculate_impact(int(tokens), factor)

    # Sauvegarde session uniquement pour les utilisateurs connectés
    if user is not None:
        last_msg = body.messages[-1].content
        name = f"Chat {body.provider} — {last_msg[:50]}{'…' if len(last_msg) > 50 else ''}"
        session_repo.create_with_metrics(
            db, user_id=user.id, name=name,
            provider=body.provider, model=body.model,
            nb_turns=1, tokens=int(tokens), impact=impact,
            tokens_saved=body.tokens_saved,
        )

    cost = calculate_cost(body.provider, body.model, result["input_tokens"], result["output_tokens"])

    return {
        "content":        result["content"],
        "input_tokens":   result["input_tokens"],
        "output_tokens":  result["output_tokens"],
        "thinking_tokens": result.get("thinking_tokens", 0),
        "effort":         body.effort,
        "impact":         impact,
        "guest":          user is None,
        **({"orchestration": result["orchestration"]} if "orchestration" in result else {}),
        **cost,
    }


@router.post("/compact")
async def compact_chat(
    body: CompactRequest,
    user: User = Depends(get_current_user),
):
    if not body.messages:
        raise HTTPException(status_code=422, detail="messages ne peut pas être vide")

    conversation = "\n".join(
        f"[{'Utilisateur' if m.role == 'user' else 'Assistant'}] {m.content}"
        for m in body.messages
    )
    prompt = (
        "Résume cette conversation en 5 phrases factuelles maximum. "
        "Conserve : les décisions prises, le contexte technique, "
        "les contraintes mentionnées, les fichiers ou données évoqués. "
        "Commence par 'Contexte :'\n\n" + conversation
    )
    try:
        result = await chat_service.call_llm(
            body.provider, body.model, body.api_key,
            [{"role": "user", "content": prompt}],
        )
        return {"summary": result["content"]}
    except HTTPException:
        raise  # préserve le vrai statut (401 clé invalide, 429 quota, …)
    except Exception:
        raise HTTPException(status_code=502, detail="Erreur LLM lors de la compaction.")
