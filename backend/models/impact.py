from sqlalchemy import Column, Integer, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base


class ImpactMetric(Base):
    __tablename__ = "impact_metrics"
    __table_args__ = (UniqueConstraint("session_id", name="uix_impact_session"),)

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("simulation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    co2_standard = Column(Float, default=0.0)
    co2_ethical = Column(Float, default=0.0)
    co2_saved = Column(Float, default=0.0)
    homes_heated_min = Column(Float, default=0.0)
    showers_equiv = Column(Float, default=0.0)

    session = relationship("SimulationSession", back_populates="metrics")
