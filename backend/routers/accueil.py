from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import ConversionFactor, SimulationSession, ImpactMetric
from utils.calculator import calculate_impact
from utils.parsers import (
    count_tokens_from_text, estimate_turns,
    calculate_helios_equivalences,
    format_energie, format_co2, format_duree,
)

CHAR_LIMIT = 3000

router = APIRouter(tags=["accueil"])


class QuickCalcInput(BaseModel):
    text: str
    provider: str
    model: str
    langue: str = "fr"


@router.post("/accueil/calculate")
def quick_calculate(body: QuickCalcInput, db: Session = Depends(get_db)):
    if len(body.text) > CHAR_LIMIT:
        raise HTTPException(
            status_code=400,
            detail=f"Texte limité à {CHAR_LIMIT} caractères sans compte. Créez un compte pour analyser des conversations plus longues.",
        )
    factor = db.query(ConversionFactor).filter_by(
        provider=body.provider, model=body.model
    ).first()
    if factor is None:
        raise HTTPException(status_code=400, detail=f"Coefficients introuvables pour {body.provider} / {body.model}.")

    total_tokens = count_tokens_from_text(body.text, body.langue)
    turns        = estimate_turns(total_tokens)
    impact       = calculate_impact(total_tokens, factor)
    helios       = calculate_helios_equivalences(impact["total_kwh"])

    return {
        "total_tokens": total_tokens,
        "turns":        turns,
        "impact":       impact,
        "fmt": {
            "energie":      format_energie(impact["total_kwh"]),
            "co2":          format_co2(impact["co2_standard"]),
            "co2_evite":    format_co2(helios["co2_evite"]),
            "logement_bbc": format_duree(helios["heures_logement_bbc"]),
        },
    }


@router.get("/accueil/stats")
def accueil_stats(db: Session = Depends(get_db)):
    from sqlalchemy import func
    row = db.query(
        func.coalesce(func.sum(ImpactMetric.co2_standard), 0).label("total_co2"),
        func.count(SimulationSession.id).label("total_sessions"),
    ).outerjoin(SimulationSession, ImpactMetric.session_id == SimulationSession.id).first()

    total_co2      = float(row.total_co2 or 0)
    total_sessions = int(row.total_sessions or 0)
    total_kwh      = total_co2 / 0.4 if total_co2 > 0 else 0

    return {
        "total_sessions": total_sessions,
        "total_co2":      format_co2(total_co2),
        "total_kwh":      format_energie(total_kwh),
    }
