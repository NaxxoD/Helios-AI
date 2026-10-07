from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from database import Base


def _now():
    return datetime.now(timezone.utc)


class ConversionFactor(Base):
    __tablename__ = "conversion_factors"

    id = Column(Integer, primary_key=True)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    kwh_per_token = Column(Float, nullable=False)
    co2_per_kwh_standard = Column(Float, nullable=False, default=0.4)
    co2_per_kwh_ethical = Column(Float, nullable=False, default=0.015)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, default=_now, onupdate=_now)
