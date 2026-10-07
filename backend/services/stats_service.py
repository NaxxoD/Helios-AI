from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from repositories import session_repo
from models import SimulationSession
from schemas.stats import StatsOut, Totals, Charts


def compute(db: Session, user_id: int) -> StatsOut:
    sessions = session_repo.list_by_user(db, user_id)

    total_kwh = sum(s.total_kwh or 0 for s in sessions)
    total_co2_std = sum(s.metrics.co2_standard for s in sessions if s.metrics)
    total_co2_eth = sum(s.metrics.co2_ethical for s in sessions if s.metrics)

    # --- Courbe cumulée par jour ---
    daily_rows = (
        db.query(
            func.date(SimulationSession.created_at).label("day"),
            func.sum(SimulationSession.total_kwh).label("kwh_sum"),
        )
        .filter_by(user_id=user_id)
        .group_by(func.date(SimulationSession.created_at))
        .order_by(func.date(SimulationSession.created_at))
        .all()
    )
    kwh_by_day = {
        (r.day if isinstance(r.day, str) else r.day.isoformat()): (r.kwh_sum or 0)
        for r in daily_rows
    }
    cumulative: list[dict] = []
    if kwh_by_day:
        cursor = datetime.fromisoformat(min(kwh_by_day))
        end = datetime.fromisoformat(max(kwh_by_day))
        running = 0.0
        while cursor <= end:
            day_str = cursor.date().isoformat()
            running += kwh_by_day.get(day_str, 0)
            cumulative.append({"date": cursor.strftime("%d/%m"), "kwh": round(running, 7)})
            cursor += timedelta(days=1)

    # --- CO₂ par provider ---
    by_provider: dict[str, float] = {}
    for s in sessions:
        if s.metrics:
            by_provider[s.provider] = by_provider.get(s.provider, 0) + s.metrics.co2_standard
    provider_chart = [
        {"provider": p, "co2": round(v, 4)}
        for p, v in sorted(by_provider.items(), key=lambda x: x[1], reverse=True)
    ]

    # --- Sessions par semaine (8 dernières) ---
    weekly: dict[str, int] = {}
    for s in sessions:
        week = s.created_at.strftime("%Y-W%W")
        weekly[week] = weekly.get(week, 0) + 1
    weekly_chart = [{"week": w, "count": c} for w, c in sorted(weekly.items())[-8:]]

    # --- Répartition par modèle ---
    by_model: dict[str, float] = {}
    for s in sessions:
        key = s.provider + " " + s.model
        by_model[key] = by_model.get(key, 0) + (s.total_kwh or 0)
    model_chart = [
        {"model": m, "kwh": round(v, 7)}
        for m, v in sorted(by_model.items(), key=lambda x: x[1], reverse=True)
    ]

    # --- Comparaison mensuelle std vs eth (6 derniers mois) ---
    monthly_std: dict[str, float] = {}
    monthly_eth: dict[str, float] = {}
    for s in sessions:
        month = s.created_at.strftime("%b %Y")
        if s.metrics:
            monthly_std[month] = monthly_std.get(month, 0) + s.metrics.co2_standard
            monthly_eth[month] = monthly_eth.get(month, 0) + s.metrics.co2_ethical
    all_months = sorted(set(list(monthly_std) + list(monthly_eth)))[-6:]
    monthly_chart = [
        {"month": m, "standard": round(monthly_std.get(m, 0), 4), "ethical": round(monthly_eth.get(m, 0), 4)}
        for m in all_months
    ]

    # --- CO₂ hebdo vs seuil ---
    week_start = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    weekly_co2 = sum(
        s.metrics.co2_standard for s in sessions
        if s.metrics and s.created_at >= week_start
    )

    return StatsOut(
        totals=Totals(
            kwh=round(total_kwh, 5),
            co2_standard=round(total_co2_std, 3),
            co2_ethical=round(total_co2_eth, 3),
            co2_saved=round(total_co2_std - total_co2_eth, 3),
            sessions=len(sessions),
        ),
        weekly_co2=round(weekly_co2, 3),
        threshold=None,  # injecté par le router depuis user.co2_weekly_threshold
        charts=Charts(
            cumulative=cumulative,
            by_provider=provider_chart,
            by_week=weekly_chart,
            by_model=model_chart,
            monthly_comparison=monthly_chart,
        ),
    )
