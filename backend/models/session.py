from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


def _now():
    return datetime.now(timezone.utc)


class SimulationSession(Base):
    __tablename__ = "simulation_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), default="Session sans titre")
    provider = Column(String(50))
    model = Column(String(100))
    nb_turns = Column(Integer, default=0)
    tokens_estimated = Column(Integer, default=0)
    tokens_saved = Column(Integer, default=0)
    total_kwh = Column(Float, default=0.0)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    user = relationship("User", back_populates="sessions")
    metrics = relationship(
        "ImpactMetric", back_populates="session",
        uselist=False, cascade="all, delete-orphan"
    )
