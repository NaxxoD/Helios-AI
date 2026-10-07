from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from repositories import session_repo, factor_repo
from utils.calculator import estimate_tokens_from_turns, calculate_impact
from utils.parsers import parse_conversation, OUTPUT_TOKEN_WEIGHT
from schemas.session import SessionCreate, SessionFromExtension, SessionOut


def _to_out(sess) -> SessionOut:
    m = sess.metrics
    return SessionOut(
        id=sess.id, name=sess.name, provider=sess.provider,
        model=sess.model, nb_turns=sess.nb_turns,
        tokens_estimated=sess.tokens_estimated, total_kwh=sess.total_kwh,
        co2_standard=m.co2_standard if m else None,
        co2_ethical=m.co2_ethical if m else None,
        co2_saved=m.co2_saved if m else None,
        homes_heated_min=m.homes_heated_min if m else None,
        showers_equiv=m.showers_equiv if m else None,
        created_at=sess.created_at,
    )


def create_manual(db: Session, user_id: int, data: SessionCreate) -> SessionOut:
    tokens = estimate_tokens_from_turns(data.nb_turns)
    factor = factor_repo.get_by_provider_model(db, data.provider, data.model)
    impact = calculate_impact(tokens, factor)
    sess = session_repo.create_with_metrics(
        db, user_id=user_id, name=data.name, provider=data.provider,
        model=data.model, nb_turns=data.nb_turns, tokens=tokens, impact=impact,
    )
    return _to_out(sess)


def create_from_extension(db: Session, user_id: int, data: SessionFromExtension) -> SessionOut:
    if not data.provider:
        raise HTTPException(400, "Provider requis")
    input_tokens  = data.exact_input_tokens  or 0
    output_tokens = data.exact_output_tokens or 0
    if input_tokens == 0 and output_tokens == 0:
        raise HTTPException(400, "Aucun token enregistré")
    tokens = input_tokens + output_tokens * OUTPUT_TOKEN_WEIGHT
    factor = factor_repo.get_by_provider_model(db, data.provider, data.model)
    impact = calculate_impact(tokens, factor)
    sess = session_repo.create_with_metrics(
        db, user_id=user_id, name=data.name, provider=data.provider,
        model=data.model, nb_turns=data.nb_turns, tokens=tokens, impact=impact,
    )
    return _to_out(sess)


def import_from_text(
    db: Session, user_id: int,
    provider: str, model: str,
    content: str, is_file: bool,
) -> SessionOut:
    parsed = parse_conversation(content, provider, is_file=is_file)
    tokens = parsed["tokens_estimated"]
    if not model:
        factor = factor_repo.get_by_provider_model(db, parsed["provider"], "default")
        model = factor.model if factor else "default"
    factor = factor_repo.get_by_provider_model(db, parsed["provider"], model)
    impact = calculate_impact(tokens, factor)
    sess = session_repo.create_with_metrics(
        db, user_id=user_id, name=parsed["name"], provider=parsed["provider"],
        model=model, nb_turns=parsed["nb_turns"], tokens=tokens, impact=impact,
    )
    return _to_out(sess)


def get_detail(db: Session, session_id: int, user_id: int, is_admin: bool) -> dict:
    sess = session_repo.get_by_id(db, session_id)
    if not sess:
        raise HTTPException(404, "Session introuvable")
    if sess.user_id != user_id and not is_admin:
        raise HTTPException(403, "Accès refusé")
    m = sess.metrics
    co2_std = m.co2_standard if m else None
    energy_status = None
    if co2_std is not None:
        energy_status = "low" if co2_std < 0.001 else "medium" if co2_std < 0.01 else "high"
    session_out = {
        "id":               sess.id,
        "date":             sess.created_at.isoformat() if sess.created_at else None,
        "provider":         sess.provider,
        "model":            sess.model,
        "tokens_estimated": sess.tokens_estimated,
        "kwh_estimated":    sess.total_kwh,
        "co2_standard":     co2_std,
        "co2_equiv":        co2_std,
        "co2_ethical":      m.co2_ethical if m else None,
        "co2_saved":        m.co2_saved if m else None,
        "homes_heated_min": m.homes_heated_min if m else None,
        "energy_status":    energy_status,
    }
    factor = factor_repo.get_by_provider_model(db, sess.provider, sess.model)
    factors_out = None
    if factor:
        factors_out = {
            "kwh_per_token":       factor.kwh_per_token,
            "co2_per_kwh":         factor.co2_per_kwh_standard,
            "co2_per_kwh_ethical": factor.co2_per_kwh_ethical,
        }
    return {"session": session_out, "content": None, "factors": factors_out}


def update_model(db: Session, session_id: int, user_id: int, is_admin: bool, provider: str, model: str) -> dict:
    sess = session_repo.get_by_id(db, session_id)
    if not sess:
        raise HTTPException(404, "Session introuvable")
    if sess.user_id != user_id and not is_admin:
        raise HTTPException(403, "Accès refusé")
    factor = factor_repo.get_by_provider_model(db, provider, model)
    if not factor:
        raise HTTPException(400, f"Coefficients introuvables pour {provider} / {model}")
    impact = calculate_impact(sess.tokens_estimated or 1, factor)
    sess.provider   = provider
    sess.model      = model
    sess.total_kwh  = impact["total_kwh"]
    if sess.metrics:
        sess.metrics.co2_standard    = impact["co2_standard"]
        sess.metrics.co2_ethical     = impact["co2_ethical"]
        sess.metrics.co2_saved       = impact["co2_saved"]
        sess.metrics.homes_heated_min = impact["homes_heated_min"]
        sess.metrics.showers_equiv   = impact["showers_equiv"]
    db.commit()
    db.refresh(sess)
    return get_detail(db, session_id, user_id, is_admin)


def delete(db: Session, session_id: int, user_id: int, is_admin: bool) -> None:
    sess = session_repo.get_by_id(db, session_id)
    if not sess:
        raise HTTPException(404, "Session introuvable")
    if sess.user_id != user_id and not is_admin:
        raise HTTPException(403, "Accès refusé")
    session_repo.delete(db, sess)
