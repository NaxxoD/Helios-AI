from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from database import Base


def _now():
    return datetime.now(timezone.utc)


class NoiseCandidate(Base):
    __tablename__ = "noise_candidates"

    id          = Column(Integer, primary_key=True)
    text        = Column(String(500), unique=True, nullable=False, index=True)
    noise_score = Column(Float, default=0.0)
    frequency   = Column(Integer, default=1)
    validated   = Column(Boolean, default=False)
    label       = Column(Integer, nullable=True)  # 0=signal, 1=bruit (post-validation)
    created_at  = Column(DateTime, default=_now)
    updated_at  = Column(DateTime, default=_now, onupdate=_now)
