from pydantic import BaseModel


class Totals(BaseModel):
    kwh: float
    co2_standard: float
    co2_ethical: float
    co2_saved: float
    sessions: int


class Charts(BaseModel):
    cumulative: list[dict]
    by_provider: list[dict]
    by_week: list[dict]
    by_model: list[dict]
    monthly_comparison: list[dict]


class StatsOut(BaseModel):
    totals: Totals
    weekly_co2: float
    threshold: float | None
    charts: Charts
