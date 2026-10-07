from sqlalchemy.orm import Session
from models import User


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter_by(email=email).first()


def create(db: Session, email: str, password: str) -> User:
    user = User(email=email)
    user.set_password(password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()


def list_all(db: Session) -> list[User]:
    return db.query(User).order_by(User.created_at.desc()).all()


def set_role(db: Session, user: User, role: str) -> User:
    user.role = role
    db.commit()
    return user
