from datetime import datetime
from pydantic import BaseModel


class FactorOut(BaseModel):
    id: int
    provider: str
    model: str
    kwh_per_token: float
    co2_per_kwh_standard: float
    co2_per_kwh_ethical: float
    updated_at: datetime | None = None


class FactorCreate(BaseModel):
    provider: str
    model: str
    kwh_per_token: float
    co2_per_kwh_standard: float = 0.4
    co2_per_kwh_ethical: float = 0.015


class FactorUpdate(BaseModel):
    kwh_per_token: float | None = None
    co2_per_kwh_standard: float | None = None
    co2_per_kwh_ethical: float | None = None


class AdminUserOut(BaseModel):
    id: int
    email: str
    role: str
    sessions: int
    created_at: datetime | None = None


class RolePatch(BaseModel):
    role: str
