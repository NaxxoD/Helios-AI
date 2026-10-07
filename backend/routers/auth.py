import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, Request

logger = logging.getLogger(__name__)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from config import settings
from database import get_db
from dependencies import get_current_user, get_optional_user
from repositories import user_repo
from services.auth_service import create_token
from schemas.auth import LoginIn, RegisterIn, PasswordChangeIn, UserOut, ForgotPasswordIn, ResetPasswordIn
from models import User, PasswordResetToken
from utils.mailer import send_reset_email, send_verification_email

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,  # 30 jours
    )


@router.get("/me")
def me(user: User | None = Depends(get_optional_user)):
    if not user:
        return {"user": None}
    return {"user": UserOut(
        id=user.id, email=user.email,
        is_admin=user.is_admin(),
        co2_weekly_threshold=user.co2_weekly_threshold,
    )}


@router.post("/login")
@limiter.limit("20/minute")
@limiter.limit("5/10seconds")
def login(request: Request, data: LoginIn, db: Session = Depends(get_db)):
    user = user_repo.get_by_email(db, data.email.strip().lower())
    if not user or not user.check_password(data.password):
        raise HTTPException(401, "Email ou mot de passe incorrect")
    if not user.is_verified:
        raise HTTPException(403, "Compte non vérifié — consultez votre boîte mail")
    token = create_token(user.id)
    response = JSONResponse({
        "id": user.id, "email": user.email, "is_admin": user.is_admin(),
        "access_token": token,
    })
    _set_auth_cookie(response, token)
    return response


@router.post("/connexion")
@limiter.limit("20/minute")
@limiter.limit("5/10seconds")
def connexion(request: Request, data: LoginIn, db: Session = Depends(get_db)):
    return login(request, data, db)


@router.post("/register", status_code=201)
@limiter.limit("5/hour")
async def register(request: Request, data: RegisterIn, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    if not email or not data.password:
        raise HTTPException(400, "Email et mot de passe requis")
    if len(data.password) < 8:
        raise HTTPException(400, "Mot de passe trop court (8 caractères min)")
    if user_repo.get_by_email(db, email):
        raise HTTPException(409, "Cet email est déjà utilisé")
    user = user_repo.create(db, email, data.password)
    if not settings.MAIL_USERNAME:
        # Mode dev sans SMTP — compte activé directement
        user.is_verified = True
        db.commit()
        token = create_token(user.id)
        response = JSONResponse({"id": user.id, "email": user.email, "is_admin": user.is_admin(), "access_token": token}, status_code=201)
        _set_auth_cookie(response, token)
        return response
    verification_token = secrets.token_urlsafe(32)
    user.verification_token = verification_token
    db.commit()
    verify_url = f"{settings.FRONTEND_URL}/auth/verify/{verification_token}"
    # Ne JAMAIS logger verify_url : il contient le token d'activation (secret d'auth).
    logger.info("[auth] Email de vérification envoyé à %s", user.email)
    await send_verification_email(user.email, verify_url)
    return JSONResponse({"detail": "Email de confirmation envoyé. Vérifiez votre boîte mail."}, status_code=201)


@router.post("/inscription", status_code=201)
@limiter.limit("5/hour")
async def inscription(request: Request, data: RegisterIn, db: Session = Depends(get_db)):
    return await register(request, data, db)


@router.get("/verify/{token}")
def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(verification_token=token).first()
    if not user:
        raise HTTPException(400, "Lien invalide ou déjà utilisé")
    user.is_verified = True
    user.verification_token = None
    db.commit()
    jwt = create_token(user.id)
    response = JSONResponse({"id": user.id, "email": user.email, "is_admin": user.is_admin(), "access_token": jwt})
    _set_auth_cookie(response, jwt)
    return response


@router.post("/resend-verification")
@limiter.limit("3/hour")
async def resend_verification(request: Request, data: ForgotPasswordIn, db: Session = Depends(get_db)):
    user = user_repo.get_by_email(db, data.email.strip().lower())
    if user and not user.is_verified:
        token = user.verification_token or secrets.token_urlsafe(32)
        user.verification_token = token
        db.commit()
        verify_url = f"{settings.FRONTEND_URL}/auth/verify/{token}"
        # Ne JAMAIS logger verify_url : il contient le token d'activation (secret d'auth).
        logger.info("[auth] Email de vérification renvoyé à %s", user.email)
        await send_verification_email(user.email, verify_url)
    return {"detail": "Si ce compte existe et n'est pas vérifié, un email a été renvoyé."}


@router.post("/logout")
def logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie("access_token")
    return response


@router.patch("/password")
def change_password(
    data: PasswordChangeIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.check_password(data.current_password):
        raise HTTPException(400, "Mot de passe actuel incorrect")
    if len(data.new_password) < 8:
        raise HTTPException(400, "Nouveau mot de passe trop court (8 caractères min)")
    user.set_password(data.new_password)
    db.commit()
    return {"ok": True}


@router.post("/forgot-password")
@limiter.limit("5/hour")
async def forgot_password(request: Request, data: ForgotPasswordIn, db: Session = Depends(get_db)):
    user = user_repo.get_by_email(db, data.email.strip().lower())
    if user:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        db.add(PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
        db.commit()
        reset_url = f"{settings.FRONTEND_URL}/auth/reset-password/{raw_token}"
        await send_reset_email(user.email, reset_url)
    return {"ok": True}


@router.post("/reset-password")
@limiter.limit("10/hour")
def reset_password(request: Request, data: ResetPasswordIn, db: Session = Depends(get_db)):
    if len(data.new_password) < 8:
        raise HTTPException(400, "Mot de passe trop court (8 caractères min)")
    token_hash = hashlib.sha256(data.token.encode()).hexdigest()
    record = db.query(PasswordResetToken).filter_by(token_hash=token_hash, used=False).first()
    if not record:
        raise HTTPException(400, "Lien invalide ou déjà utilisé")
    if datetime.now(timezone.utc) > record.expires_at.replace(tzinfo=timezone.utc):
        raise HTTPException(400, "Lien expiré — demandez un nouveau lien")
    user = db.get(User, record.user_id)
    if not user:
        raise HTTPException(400, "Utilisateur introuvable")
    user.set_password(data.new_password)
    record.used = True
    db.commit()
    return {"ok": True}


@router.delete("/account")
def delete_account(
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    user_repo.delete(db, user)
    response.delete_cookie("access_token")
    return {"ok": True}
