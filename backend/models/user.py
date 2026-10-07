from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from database import Base


def _now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(20), default="user")
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(256), nullable=True)
    reset_token = Column(String(256), nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    co2_weekly_threshold = Column(Float, nullable=True, default=None)
    last_threshold_alert_at = Column(DateTime, nullable=True, default=None)
    created_at = Column(DateTime, default=_now)

    sessions = relationship(
        "SimulationSession", back_populates="user", cascade="all, delete-orphan"
    )
    conversations = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def is_admin(self) -> bool:
        return self.role == "admin"
