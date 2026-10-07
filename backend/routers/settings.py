from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from schemas.settings import SettingsOut, SettingsPatch
from models import User

router = APIRouter()


@router.get("/settings", response_model=SettingsOut)
def get_settings(user: User = Depends(get_current_user)):
    return SettingsOut(email=user.email, co2_weekly_threshold=user.co2_weekly_threshold)


@router.patch("/settings")
def patch_settings(
    data: SettingsPatch,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if "co2_weekly_threshold" in data.model_fields_set:
        val = data.co2_weekly_threshold
        user.co2_weekly_threshold = max(0.0, float(val)) if val is not None else None
        db.commit()
    return {"ok": True}


@router.get("/factors")
def factors(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from repositories import factor_repo
    all_factors = factor_repo.list_all(db)
    providers: dict = {}
    for f in all_factors:
        providers.setdefault(f.provider, []).append(f.model)
    return {"providers": providers}


@router.post("/optimise")
def optimise(
    data: dict,
    user: User = Depends(get_current_user),
):
    from fastapi import HTTPException
    from utils.optimiseur import optimise as _optimise
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(400, "Prompt vide")
    if len(prompt) > 8000:
        raise HTTPException(400, "Prompt trop long (max 8000 caractères)")
    return _optimise(prompt)
