from pydantic import BaseModel


class SettingsOut(BaseModel):
    email: str
    co2_weekly_threshold: float | None = None


class SettingsPatch(BaseModel):
    co2_weekly_threshold: float | None = None
