import uuid
from sqlalchemy.orm import Session
from models.conversation import Conversation


def create(db: Session, user_id: int, title: str, provider: str, model: str) -> Conversation:
    conv = Conversation(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title=title,
        provider=provider,
        model=model,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def update_metrics(
    db: Session, conv_id: str, user_id: int,
    nb_turns: int, tokens_total: int, co2_g: float,
    cost_usd: float, impact_level: str, title: str | None = None,
) -> Conversation | None:
    conv = db.query(Conversation).filter_by(id=conv_id, user_id=user_id).first()
    if not conv:
        return None
    conv.nb_turns     = nb_turns
    conv.tokens_total = tokens_total
    conv.co2_g        = co2_g
    conv.cost_usd     = cost_usd
    conv.impact_level = impact_level
    if title:
        conv.title = title
    db.commit()
    db.refresh(conv)
    return conv


def list_for_user(db: Session, user_id: int) -> list[Conversation]:
    return (
        db.query(Conversation)
        .filter_by(user_id=user_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )


def get(db: Session, conv_id: str, user_id: int) -> Conversation | None:
    return db.query(Conversation).filter_by(id=conv_id, user_id=user_id).first()


def delete(db: Session, conv_id: str, user_id: int) -> bool:
    conv = db.query(Conversation).filter_by(id=conv_id, user_id=user_id).first()
    if not conv:
        return False
    db.delete(conv)
    db.commit()
    return True
