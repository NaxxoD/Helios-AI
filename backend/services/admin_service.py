from fastapi import HTTPException
from sqlalchemy.orm import Session
from repositories import factor_repo, user_repo
from models import ConversionFactor, User
from schemas.admin import FactorCreate, FactorUpdate


def list_factors(db: Session) -> list[ConversionFactor]:
    return factor_repo.list_all(db)


def add_factor(db: Session, data: FactorCreate, updated_by: int) -> ConversionFactor:
    return factor_repo.create(db, data.model_dump(), updated_by)


def update_factor(db: Session, factor_id: int, data: FactorUpdate, updated_by: int) -> ConversionFactor:
    f = db.get(ConversionFactor, factor_id)
    if not f:
        raise HTTPException(404, "Facteur introuvable")
    return factor_repo.update(db, f, data.model_dump(exclude_none=True), updated_by)


def delete_factor(db: Session, factor_id: int) -> None:
    f = db.get(ConversionFactor, factor_id)
    if not f:
        raise HTTPException(404, "Facteur introuvable")
    factor_repo.delete(db, f)


def list_users(db: Session) -> list[User]:
    return user_repo.list_all(db)


def set_user_role(db: Session, user_id: int, role: str, current_user_id: int) -> User:
    if role not in ("user", "admin"):
        raise HTTPException(400, "Rôle invalide")
    if user_id == current_user_id:
        raise HTTPException(400, "Impossible de modifier son propre rôle")
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "Utilisateur introuvable")
    return user_repo.set_role(db, u, role)
