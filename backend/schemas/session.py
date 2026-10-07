from datetime import datetime
from pydantic import BaseModel, field_validator


class SessionCreate(BaseModel):
    name: str = "Session sans titre"
    provider: str
    model: str
    nb_turns: int = 1

    @field_validator("nb_turns")
    @classmethod
    def nb_turns_positive(cls, v: int) -> int:
        return max(1, v)


class SessionFromExtension(BaseModel):
    name: str = "Session extension"
    provider: str
    model: str = ""
    exact_input_tokens: int = 0
    exact_output_tokens: int = 0
    exact_total_tokens: int = 0
    nb_turns: int = 1


class SessionOut(BaseModel):
    id: int
    name: str
    provider: str
    model: str
    nb_turns: int
    tokens_estimated: int
    total_kwh: float
    co2_standard: float | None = None
    co2_ethical: float | None = None
    co2_saved: float | None = None
    homes_heated_min: float | None = None
    showers_equiv: float | None = None
    created_at: datetime


class SessionsPage(BaseModel):
    items: list[SessionOut]
    total: int
    pages: int
    page: int
    has_next: bool
    has_prev: bool


class SessionDetailOut(SessionOut):
    factor: dict | None = None
