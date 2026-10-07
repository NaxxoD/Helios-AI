import logging

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import get_db
from models import User

log = logging.getLogger(__name__)


def _extract_token(request: Request) -> str | None:
    """Accepte Authorization: Bearer <token> (frontend Vue) ou cookie access_token (extension Chrome)."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get("access_token")


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    from services.auth_service import decode_token
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Non authentifié")
    try:
        user_id = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Token invalide")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    return user


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    from services.auth_service import decode_token
    token = _extract_token(request)
    if not token:
        return None
    try:
        user_id = decode_token(token)
        return db.get(User, user_id)
    except ValueError:
        return None  # token invalide/expiré — cas attendu
    except Exception:
        # erreur inattendue (DB, etc.) : ne pas crasher un endpoint optionnel,
        # mais tracer pour ne pas masquer un incident.
        log.warning("[auth] get_optional_user : erreur inattendue de résolution du token",
                    exc_info=True)
        return None


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin():
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    return user
