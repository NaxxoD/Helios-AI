from sqlalchemy.orm import Session
from models.noise_candidate import NoiseCandidate


def upsert(db: Session, text: str, score: float) -> None:
    """Insère le candidat ou incrémente sa fréquence s'il existe déjà."""
    existing = db.query(NoiseCandidate).filter_by(text=text).first()
    if existing:
        existing.frequency   += 1
        existing.noise_score  = round((existing.noise_score + score) / 2, 3)
    else:
        db.add(NoiseCandidate(text=text, noise_score=round(score, 3)))
    db.commit()


def list_unvalidated(db: Session, min_frequency: int = 1) -> list[NoiseCandidate]:
    return (
        db.query(NoiseCandidate)
        .filter_by(validated=False)
        .filter(NoiseCandidate.frequency >= min_frequency)
        .order_by(NoiseCandidate.frequency.desc(), NoiseCandidate.noise_score.desc())
        .all()
    )


def validate(db: Session, candidate_id: int, label: int) -> bool:
    c = db.query(NoiseCandidate).filter_by(id=candidate_id).first()
    if not c:
        return False
    c.validated = True
    c.label     = label
    db.commit()
    return True
