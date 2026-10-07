from math import ceil
from sqlalchemy.orm import Session
from models import SimulationSession, ImpactMetric


def get_by_id(db: Session, session_id: int) -> SimulationSession | None:
    return db.get(SimulationSession, session_id)


def list_by_user(db: Session, user_id: int) -> list[SimulationSession]:
    return (
        db.query(SimulationSession)
        .filter_by(user_id=user_id)
        .order_by(SimulationSession.created_at.asc())
        .all()
    )


def paginate(
    db: Session, user_id: int, page: int = 1, per_page: int = 15
) -> dict:
    total = db.query(SimulationSession).filter_by(user_id=user_id).count()
    items = (
        db.query(SimulationSession)
        .filter_by(user_id=user_id)
        .order_by(SimulationSession.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    pages = ceil(total / per_page) if total else 1
    return {
        "items": items,
        "total": total,
        "pages": pages,
        "page": page,
        "has_next": page < pages,
        "has_prev": page > 1,
    }


def create_with_metrics(
    db: Session,
    user_id: int,
    name: str,
    provider: str,
    model: str,
    nb_turns: int,
    tokens: int,
    impact: dict,
    tokens_saved: int = 0,
) -> SimulationSession:
    sess = SimulationSession(
        user_id=user_id, name=name, provider=provider, model=model,
        nb_turns=nb_turns, tokens_estimated=tokens, tokens_saved=tokens_saved,
        total_kwh=impact["total_kwh"],
    )
    db.add(sess)
    db.flush()
    db.add(ImpactMetric(
        session_id=sess.id,
        co2_standard=impact["co2_standard"],
        co2_ethical=impact["co2_ethical"],
        co2_saved=impact["co2_saved"],
        homes_heated_min=impact["homes_heated_min"],
        showers_equiv=impact["showers_equiv"],
    ))
    db.commit()
    db.refresh(sess)
    return sess


def delete(db: Session, sess: SimulationSession) -> None:
    db.delete(sess)
    db.commit()
