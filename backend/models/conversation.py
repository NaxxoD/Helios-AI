import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


def _now():
    return datetime.now(timezone.utc)


class Conversation(Base):
    __tablename__ = "conversations"

    id       = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id  = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title    = Column(String(200), default="Nouvelle conversation")
    provider = Column(String(50))
    model    = Column(String(100))
    nb_turns       = Column(Integer, default=0)
    tokens_total   = Column(Integer, default=0)
    co2_g          = Column(Float, default=0.0)
    cost_usd       = Column(Float, default=0.0)
    impact_level   = Column(String(10), default="low")  # low / medium / high
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    user = relationship("User", back_populates="conversations")
