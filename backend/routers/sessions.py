import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from database import get_db, SessionLocal
from dependencies import get_current_user
from repositories import session_repo
from services import session_service
from schemas.session import SessionCreate, SessionFromExtension, SessionOut, SessionsPage, SessionDetailOut
from models import User, SimulationSession
from utils.mailer import send_threshold_alert

router = APIRouter()


async def _maybe_alert_threshold(user_id: int) -> None:
    with SessionLocal() as db:
        from sqlalchemy import func
        user = db.get(User, user_id)
        if not user or not user.co2_weekly_threshold:
            return
        now = datetime.now(timezone.utc)
        if user.last_threshold_alert_at:
            last = user.last_threshold_alert_at
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if (now - last) < timedelta(hours=24):
                return
        week_start = now.replace(tzinfo=None) - timedelta(days=7)
        weekly_co2 = db.query(func.sum(SimulationSession.total_kwh)).filter(
            SimulationSession.user_id == user_id,
            SimulationSession.created_at >= week_start,
        ).scalar() or 0.0
        # Convert kWh to g CO₂ using standard factor ~400 g/kWh
        weekly_co2_g = weekly_co2 * 400
        if weekly_co2_g <= user.co2_weekly_threshold:
            return
        user.last_threshold_alert_at = now.replace(tzinfo=None)
        db.commit()
        await send_threshold_alert(user.email, weekly_co2_g, user.co2_weekly_threshold)


def _run_alert(user_id: int) -> None:
    asyncio.run(_maybe_alert_threshold(user_id))


@router.get("", response_model=SessionsPage)
def list_sessions(
    page: int = 1,
    per_page: int = 15,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = session_repo.paginate(db, user.id, page, per_page)
    result["items"] = [session_service._to_out(s) for s in result["items"]]
    return SessionsPage(**result)


@router.post("", response_model=SessionOut, status_code=201)
def create_session(
    data: SessionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = session_service.create_manual(db, user.id, data)
    background_tasks.add_task(_run_alert, user.id)
    return result


@router.post("/from-extension", response_model=SessionOut, status_code=201)
def create_from_extension(
    data: SessionFromExtension,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = session_service.create_from_extension(db, user.id, data)
    background_tasks.add_task(_run_alert, user.id)
    return result


@router.post("/import", response_model=SessionOut, status_code=201)
async def import_session(
    provider: str = Form("OpenAI"),
    model: str = Form(""),
    conversation_text: str = Form(""),
    conversation_file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from fastapi import HTTPException
    content, is_file = None, False
    if conversation_file and conversation_file.filename:
        content = (await conversation_file.read()).decode("utf-8", errors="replace")
        is_file = True
    elif conversation_text.strip():
        content = conversation_text.strip()
    else:
        raise HTTPException(400, "Collez une conversation ou uploadez un fichier")
    return session_service.import_from_text(db, user.id, provider, model, content, is_file)


@router.get("/{session_id}")
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return session_service.get_detail(db, session_id, user.id, user.is_admin())


@router.patch("/{session_id}")
def update_session_model(
    session_id: int,
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from fastapi import HTTPException
    provider = body.get("provider", "").strip()
    model    = body.get("model", "").strip()
    if not provider or not model:
        raise HTTPException(400, "provider et model requis")
    return session_service.update_model(db, session_id, user.id, user.is_admin(), provider, model)


@router.delete("/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session_service.delete(db, session_id, user.id, user.is_admin())
    return {"ok": True}
