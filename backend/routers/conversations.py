from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from models import User
from repositories import conversation_repo
from utils import minio_client

router = APIRouter(tags=["conversations"])


class ConvSaveRequest(BaseModel):
    id: str | None = None
    title: str
    provider: str
    model: str
    nb_turns: int
    tokens_total: int
    co2_g: float
    cost_usd: float
    impact_level: str
    messages: list[dict]


class ConvDeleteRequest(BaseModel):
    pass


def _impact_level(tokens: int) -> str:
    if tokens < 5_000:
        return "low"
    if tokens < 20_000:
        return "medium"
    return "high"


@router.get("")
def list_conversations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    convs = conversation_repo.list_for_user(db, user.id)
    return [
        {
            "id":           c.id,
            "title":        c.title,
            "provider":     c.provider,
            "model":        c.model,
            "nb_turns":     c.nb_turns,
            "tokens_total": c.tokens_total,
            "co2_g":        c.co2_g,
            "cost_usd":     c.cost_usd,
            "impact_level": c.impact_level,
            "created_at":   c.created_at.isoformat(),
            "updated_at":   c.updated_at.isoformat(),
        }
        for c in convs
    ]


@router.post("/save")
def save_conversation(
    body: ConvSaveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    impact = _impact_level(body.tokens_total)

    if body.id:
        conv = conversation_repo.update_metrics(
            db, body.id, user.id,
            nb_turns=body.nb_turns,
            tokens_total=body.tokens_total,
            co2_g=body.co2_g,
            cost_usd=body.cost_usd,
            impact_level=impact,
            title=body.title,
        )
        if not conv:
            raise HTTPException(404, "Conversation introuvable")
    else:
        conv = conversation_repo.create(
            db, user_id=user.id,
            title=body.title,
            provider=body.provider,
            model=body.model,
        )
        conversation_repo.update_metrics(
            db, conv.id, user.id,
            nb_turns=body.nb_turns,
            tokens_total=body.tokens_total,
            co2_g=body.co2_g,
            cost_usd=body.cost_usd,
            impact_level=impact,
        )

    try:
        minio_client.save_messages(user.id, conv.id, body.messages)
    except Exception:
        pass  # MinIO down ne bloque pas la sauvegarde métadonnées

    return {"id": conv.id}


@router.get("/{conv_id}/messages")
def get_messages(
    conv_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = conversation_repo.get(db, conv_id, user.id)
    if not conv:
        raise HTTPException(404, "Conversation introuvable")
    messages = minio_client.load_messages(user.id, conv_id)
    return {
        "id":       conv.id,
        "title":    conv.title,
        "provider": conv.provider,
        "model":    conv.model,
        "messages": messages,
    }


@router.delete("/{conv_id}")
def delete_conversation(
    conv_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    minio_client.delete_messages(user.id, conv_id)
    ok = conversation_repo.delete(db, conv_id, user.id)
    if not ok:
        raise HTTPException(404, "Conversation introuvable")
    return {"ok": True}
