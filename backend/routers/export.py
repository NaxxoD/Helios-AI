import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from repositories import session_repo
from models import User

router = APIRouter()


@router.get("/csv")
def export_csv(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from models import SimulationSession
    sessions = (
        db.query(SimulationSession)
        .filter_by(user_id=user.id)
        .order_by(SimulationSession.created_at.desc())
        .all()
    )
    output = io.StringIO()
    output.write("﻿")  # BOM UTF-8 pour Excel
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "ID", "Nom", "Provider", "Modèle", "Tours",
        "Tokens estimés", "kWh total",
        "CO₂ standard (kg)", "CO₂ éthique (kg)", "CO₂ économisé (kg)",
        "Chauffage BBC (min)", "Équiv. douches", "Date",
    ])
    for s in sessions:
        m = s.metrics
        writer.writerow([
            s.id, s.name, s.provider, s.model, s.nb_turns,
            s.tokens_estimated, s.total_kwh,
            m.co2_standard if m else "", m.co2_ethical if m else "",
            m.co2_saved if m else "", m.homes_heated_min if m else "",
            m.showers_equiv if m else "",
            s.created_at.strftime("%Y-%m-%d %H:%M"),
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=helios_sessions.csv"},
    )
