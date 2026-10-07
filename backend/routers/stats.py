from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user, get_optional_user
from services import stats_service
from models import User, ConversionFactor
from repositories import session_repo
from utils.cost_calculator import calculate_cost

router = APIRouter()


@router.get("/stats")
def stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    result = stats_service.compute(db, user.id)
    result.threshold = user.co2_weekly_threshold
    return result


@router.get("/user/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Alias format AD — compatible avec le frontend Vue."""
    result = stats_service.compute(db, user.id)
    sessions = session_repo.list_by_user(db, user.id)

    weekly_co2 = round(result.weekly_co2, 6)
    total_kwh  = result.totals.kwh

    # Calcul financier à la volée
    total_tokens   = sum(s.tokens_estimated or 0 for s in sessions)
    total_saved    = sum(s.tokens_saved or 0 for s in sessions)
    total_cost_usd = 0.0
    total_savings_usd = 0.0
    for s in sessions:
        if s.provider and s.model and s.tokens_estimated:
            # tokens_estimated = input + output * OUTPUT_WEIGHT(5). Hypothèse 60/40 :
            # tokens_estimated = 0.6T + 0.4T*5 = 2.6T → T_réel = tokens_estimated / 2.6
            actual = s.tokens_estimated / 2.6
            inp = int(actual * 0.6)
            out = int(actual * 0.4)
            cost = calculate_cost(s.provider, s.model, inp, out)
            if cost["cost_usd"] is not None:
                total_cost_usd += cost["cost_usd"]
            if s.tokens_saved:
                savings = calculate_cost(s.provider, s.model, s.tokens_saved, 0)
                if savings["cost_usd"] is not None:
                    total_savings_usd += savings["cost_usd"]

    return {
        "kpi": {
            "kwh":      round(total_kwh * 1000, 4),
            "co2":      round(result.totals.co2_standard, 6),
            "sessions": result.totals.sessions,
            "avg_kwh":  round((total_kwh / result.totals.sessions * 1000) if result.totals.sessions else 0, 4),
            "tokens":   total_tokens,
        },
        "financial": {
            "cost_usd":       round(total_cost_usd, 4),
            "savings_usd":    round(total_savings_usd, 4),
            "tokens_saved":   total_saved,
            "avg_cost_usd":   round(total_cost_usd / result.totals.sessions, 6) if result.totals.sessions else 0,
        },
        "chart": {
            "labels": [c["date"] for c in result.charts.cumulative],
            "kwh":    [c["kwh"] for c in result.charts.cumulative],
            "co2":    [round(c["kwh"] * (result.totals.co2_standard / result.totals.kwh if result.totals.kwh else 0), 6) for c in result.charts.cumulative],
        },
        "donut": {
            "labels": [p["provider"] for p in result.charts.by_provider],
            "values": [p["co2"] for p in result.charts.by_provider],
        },
        "sessions": [
            {
                "id":               s.id,
                "name":             s.name,
                "session_type":     (
                    "chat"       if (s.name or "").startswith("Chat ")        else
                    "import"     if (s.name or "").startswith("Conversation ") else
                    "estimation"
                ),
                "date":             s.created_at.isoformat() if s.created_at else None,
                "provider":         s.provider,
                "model":            s.model,
                "db_turns":         s.nb_turns,
                "tokens_estimated": s.tokens_estimated,
                "tokens_saved":     s.tokens_saved or 0,
                "kwh_estimated":    s.total_kwh if s.total_kwh else None,
                "co2_equiv":        s.metrics.co2_standard if s.metrics else None,
                "energy_status":    s.metrics.co2_standard and ("low" if s.metrics.co2_standard < 0.001 else "medium" if s.metrics.co2_standard < 0.01 else "high") or None,
                "cost_usd":         calculate_cost(s.provider, s.model, int((s.tokens_estimated or 0) / 2.6 * 0.6), int((s.tokens_estimated or 0) / 2.6 * 0.4))["cost_usd"] if s.provider and s.model else None,
            }
            for s in reversed(sessions)
        ],
        "user": {
            "email":     user.email,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "is_admin":  user.is_admin(),
            "threshold": user.co2_weekly_threshold,
        },
        "weekly_co2": weekly_co2,
    }


@router.get("/upload/providers")
def list_providers(db: Session = Depends(get_db)):
    from sqlalchemy import distinct
    rows = db.query(ConversionFactor).order_by(ConversionFactor.provider, ConversionFactor.model).all()
    groups: dict = {}
    for r in rows:
        groups.setdefault(r.provider, []).append(r.model)
    return [{"provider": p, "models": m} for p, m in groups.items()]


@router.post("/upload/detect")
async def detect_model(conversation: UploadFile = File(...)):
    from utils.parsers import detect_model_from_content
    raw  = await conversation.read()
    text = raw.decode("utf-8", errors="ignore")
    return detect_model_from_content(text)


class ManualCalcInput(BaseModel):
    provider: str
    model: str
    tokens: int
    langue: str = "fr"


@router.post("/upload/manuel")
def manual_calculate(
    body: ManualCalcInput,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    from utils.calculator import calculate_impact
    from utils.parsers import calculate_helios_equivalences, estimate_turns, format_energie, format_co2, format_duree

    factor = db.query(ConversionFactor).filter_by(
        provider=body.provider, model=body.model
    ).first()
    if factor is None:
        raise HTTPException(404, f"Coefficients introuvables pour {body.provider} / {body.model}.")

    tokens = max(1, body.tokens)
    turns  = estimate_turns(tokens)
    impact = calculate_impact(tokens, factor)
    helios = calculate_helios_equivalences(impact["total_kwh"])

    saved = False
    if user:
        session_repo.create_with_metrics(
            db, user_id=user.id,
            name=f"Estimation {body.provider}",
            provider=body.provider, model=body.model,
            nb_turns=turns, tokens=tokens, impact=impact,
        )
        saved = True

    return {
        "provider":     body.provider,
        "total_tokens": tokens,
        "turns":        turns,
        "saved":        saved,
        "fmt": {
            "energie":      format_energie(impact["total_kwh"]),
            "co2":          format_co2(impact["co2_standard"]),
            "co2_evite":    format_co2(helios["co2_evite"]),
            "logement_bbc": format_duree(helios["heures_logement_bbc"]),
        },
    }


@router.post("/upload/file")
async def upload_conversation(
    conversation: UploadFile = File(...),
    provider: str = Form(...),
    model: str = Form(...),
    langue: str = Form("fr"),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    from utils.calculator import calculate_impact
    from utils.parsers import (
        count_tokens_from_text, estimate_turns,
        calculate_helios_equivalences, format_energie, format_co2, format_duree,
    )

    content = (await conversation.read()).decode("utf-8", errors="replace")
    char_count = len(content)

    factor = db.query(ConversionFactor).filter_by(provider=provider, model=model).first()
    if factor is None:
        raise HTTPException(404, f"Coefficients introuvables pour {provider} / {model}.")

    tokens = count_tokens_from_text(content, langue)
    turns  = estimate_turns(tokens)
    impact = calculate_impact(tokens, factor)
    helios = calculate_helios_equivalences(impact["total_kwh"])

    saved = False
    if user:
        session_repo.create_with_metrics(
            db, user_id=user.id,
            name=conversation.filename or f"Upload {provider}",
            provider=provider, model=model,
            nb_turns=turns, tokens=tokens, impact=impact,
        )
        saved = True

    return {
        "provider":     provider,
        "model":        model,
        "char_count":   char_count,
        "total_tokens": tokens,
        "turns":        turns,
        "saved":        saved,
        "fmt": {
            "energie":      format_energie(impact["total_kwh"]),
            "co2":          format_co2(impact["co2_standard"]),
            "co2_evite":    format_co2(helios["co2_evite"]),
            "logement_bbc": format_duree(helios["heures_logement_bbc"]),
            "appart_moyen": format_duree(helios["heures_appart_moyen"]),
        },
    }
