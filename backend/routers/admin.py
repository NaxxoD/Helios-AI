import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from dependencies import require_admin
from services import admin_service
from schemas.admin import FactorOut, FactorCreate, FactorUpdate, AdminUserOut, RolePatch
from models import User, SimulationSession, ImpactMetric, ConversionFactor

router = APIRouter()

_NAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._\- ]{0,98}[A-Za-z0-9]$|^[A-Za-z0-9]$')

def _validate_path_name(value: str, field: str) -> str:
    if not _NAME_RE.match(value):
        raise HTTPException(400, f"{field} invalide")
    return value


@router.get("/dashboard")
def admin_dashboard(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    sessions = db.query(SimulationSession).all()
    users    = db.query(User).all()

    total_kwh = sum(s.total_kwh or 0 for s in sessions)
    total_co2 = sum(s.metrics.co2_standard for s in sessions if s.metrics)

    # Top users par kWh
    user_kwh: dict = {}
    user_sess: dict = {}
    user_email: dict = {}
    for s in sessions:
        uid = s.user_id
        user_kwh[uid]  = user_kwh.get(uid, 0) + (s.total_kwh or 0)
        user_sess[uid] = user_sess.get(uid, 0) + 1
    for u in users:
        user_email[u.id] = u.email
    top_users = sorted(user_kwh.items(), key=lambda x: x[1], reverse=True)[:5]

    # Chart global cumulé par jour
    from collections import defaultdict
    from datetime import timedelta
    daily: dict = defaultdict(float)
    for s in sessions:
        if s.created_at:
            daily[s.created_at.date().isoformat()] += s.total_kwh or 0
    sorted_days = sorted(daily.keys())
    cumul, running = [], 0.0
    for d in sorted_days:
        running += daily[d]
        cumul.append({"date": d[-5:], "kwh": round(running, 7)})

    # Par provider
    by_prov: dict = defaultdict(float)
    for s in sessions:
        if s.metrics:
            by_prov[s.provider] += s.metrics.co2_standard
    by_provider_sorted = sorted(by_prov.items(), key=lambda x: x[1], reverse=True)

    # Top user email
    top_user_email = user_email.get(top_users[0][0], "—") if top_users else "—"

    return {
        "kpi": {
            "kwh":      round(total_kwh * 1000, 4),
            "co2":      round(total_co2 * 1000, 4),
            "sessions": len(sessions),
            "users":    len(users),
            "top_user": top_user_email,
        },
        "chart": {
            "labels": [c["date"] for c in cumul],
            "kwh":    [c["kwh"] for c in cumul],
            "co2":    [round(c["kwh"] * (total_co2 / total_kwh if total_kwh else 0), 6) for c in cumul],
        },
        "by_provider": {
            "labels": [p for p, _ in by_provider_sorted],
            "co2":    [round(v * 1000, 4) for _, v in by_provider_sorted],
        },
        "top_users": [
            {"email": user_email.get(uid, "?"), "kwh": round(kwh * 1000, 4), "sessions": user_sess.get(uid, 0)}
            for uid, kwh in top_users
        ],
        "sessions": [
            {
                "id":           s.id,
                "email":        user_email.get(s.user_id, "?"),
                "provider":     s.provider,
                "model":        s.model,
                "tokens":       s.tokens_estimated,
                "kwh":          round((s.total_kwh or 0) * 1000, 4),
                "co2":          round((s.metrics.co2_standard if s.metrics else 0) * 1000, 4),
                "energy_status": (
                    "low" if (s.metrics and s.metrics.co2_standard < 0.001)
                    else "medium" if (s.metrics and s.metrics.co2_standard < 0.01)
                    else "high" if s.metrics else None
                ),
                "date": s.created_at.isoformat() if s.created_at else None,
            }
            for s in sorted(sessions, key=lambda x: x.created_at or x.id, reverse=True)
        ],
        "users": [
            {
                "id": u.id, "email": u.email, "role": u.role,
                "sessions": len(u.sessions),
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "factors": [
            {
                "id": f.id, "provider": f.provider, "model": f.model,
                "kwh_per_token": f.kwh_per_token,
                "co2_per_kwh_standard": f.co2_per_kwh_standard,
                "co2_per_kwh": f.co2_per_kwh_standard,
                "co2_per_kwh_ethical": f.co2_per_kwh_ethical,
            }
            for f in db.query(ConversionFactor).order_by(ConversionFactor.provider, ConversionFactor.model).all()
        ],
    }


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    s = db.get(SimulationSession, session_id)
    if not s:
        raise HTTPException(404, "Session introuvable")
    db.delete(s)
    db.commit()
    return {"ok": True}


@router.get("/factors", response_model=list[FactorOut])
def list_factors(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return admin_service.list_factors(db)


@router.post("/factors", status_code=201)
def add_factor(
    data: FactorCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    f = admin_service.add_factor(db, data, admin.id)
    return {"ok": True, "id": f.id}


@router.patch("/factors/{factor_id}")
def update_factor(
    factor_id: int,
    data: FactorUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    admin_service.update_factor(db, factor_id, data, admin.id)
    return {"ok": True}


@router.delete("/factors/{factor_id}")
def delete_factor(
    factor_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    admin_service.delete_factor(db, factor_id)
    return {"ok": True}


@router.get("/users", response_model=list[AdminUserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    users = admin_service.list_users(db)
    return [
        AdminUserOut(
            id=u.id, email=u.email, role=u.role,
            sessions=len(u.sessions), created_at=u.created_at,
        )
        for u in users
    ]


@router.put("/factors/{provider}/{model}")
def update_factor_by_name(
    provider: str,
    model: str,
    data: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    _validate_path_name(provider, "provider")
    _validate_path_name(model, "model")
    f = db.query(ConversionFactor).filter_by(provider=provider, model=model).first()
    if not f:
        raise HTTPException(404, "Facteur introuvable")
    if "kwh_per_token" in data:
        f.kwh_per_token = float(data["kwh_per_token"])
    if "co2_per_kwh" in data:
        f.co2_per_kwh_standard = float(data["co2_per_kwh"])
    if "co2_per_kwh_ethical" in data:
        f.co2_per_kwh_ethical = float(data["co2_per_kwh_ethical"])
    f.updated_by = admin.id
    db.commit()
    return {"ok": True}


@router.patch("/users/{user_id}/role")
def set_role(
    user_id: int,
    data: RolePatch,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    admin_service.set_user_role(db, user_id, data.role, admin.id)
    return {"ok": True}
