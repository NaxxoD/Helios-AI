from sqlalchemy.orm import Session
from models import ConversionFactor


def get_by_provider_model(db: Session, provider: str, model: str) -> ConversionFactor | None:
    return db.query(ConversionFactor).filter_by(provider=provider, model=model).first()


def list_all(db: Session) -> list[ConversionFactor]:
    return db.query(ConversionFactor).order_by(ConversionFactor.provider, ConversionFactor.model).all()


def create(db: Session, data: dict, updated_by: int) -> ConversionFactor:
    f = ConversionFactor(**data, updated_by=updated_by)
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


def update(db: Session, f: ConversionFactor, data: dict, updated_by: int) -> ConversionFactor:
    for key, val in data.items():
        if val is not None:
            setattr(f, key, val)
    f.updated_by = updated_by
    db.commit()
    return f


def delete(db: Session, f: ConversionFactor) -> None:
    db.delete(f)
    db.commit()


def count(db: Session) -> int:
    return db.query(ConversionFactor).count()
