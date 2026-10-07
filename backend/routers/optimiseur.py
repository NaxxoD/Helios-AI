import asyncio

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from database import get_db
from dependencies import get_optional_user
from models import ConversionFactor, User
from utils.optimiseur import optimise
from utils.cost_calculator import PRICING
from utils.routing import suggest_routing
from utils.qwen_optimizer import call_qwen
from repositories import noise_candidate_repo

router = APIRouter(prefix="/optimise", tags=["optimiseur"])
limiter = Limiter(key_func=get_remote_address)


class OptimiseRequest(BaseModel):
    prompt: str
    provider: Optional[str] = None
    model: Optional[str] = None
    palier: Optional[str] = None
    save_candidates: bool = False  # True uniquement depuis le bouton Aperçu
    semantic: bool = False          # True depuis Aperçu/OptimiseurView — active la couche Qwen


@router.post("/")
@limiter.limit("60/minute")
@limiter.limit("10/10seconds")
async def optimise_prompt(request: Request, body: OptimiseRequest,
                          db: Session = Depends(get_db),
                          user: User | None = Depends(get_optional_user)):
    kwh_per_token = None
    if body.provider and body.model:
        factor = await asyncio.to_thread(
            lambda: db.query(ConversionFactor).filter_by(provider=body.provider, model=body.model).first()
        )
        if factor:
            kwh_per_token = factor.kwh_per_token

    result = await asyncio.to_thread(
        lambda: optimise(body.prompt, kwh_per_token=kwh_per_token, palier=body.palier)
    )

    savings_input_usd     = None
    exchange_cost_usd     = None
    exchange_cost_max_usd = None
    savings_output_usd    = None

    if body.provider and body.model:
        rates = PRICING.get(body.provider, {}).get(body.model)
        if rates:
            tokens_saved     = result.get('tokens_saved', 0)
            tokens_after     = result.get('tokens_after', 0)
            est_output       = result.get('estimated_output_tokens')
            max_output       = result.get('output_tokens_max')
            savings_out_tok  = result.get('savings_output_tokens')

            if tokens_saved > 0:
                savings_input_usd = round(tokens_saved / 1_000_000 * rates['input'], 8)

            if est_output is not None:
                exchange_cost_usd = round(
                    (tokens_after / 1_000_000 * rates['input']) +
                    (est_output   / 1_000_000 * rates['output']),
                    8
                )

            if max_output is not None:
                exchange_cost_max_usd = round(
                    (tokens_after / 1_000_000 * rates['input']) +
                    (max_output   / 1_000_000 * rates['output']),
                    8
                )

            if savings_out_tok:
                savings_output_usd = round(savings_out_tok / 1_000_000 * rates['output'], 8)

    result['savings_input_usd']     = savings_input_usd
    result['exchange_cost_usd']     = exchange_cost_usd
    result['exchange_cost_max_usd'] = exchange_cost_max_usd
    result['savings_output_usd']    = savings_output_usd

    # Qwen — enrichissement sémantique (opt-in depuis Aperçu/OptimiseurView uniquement)
    # Paliers production (5, C, 6) : tâches longues/code/doc → bypass Qwen, regex seule suffit
    _PRODUCTION_PALIERS = {'5', 'C', '6'}
    _skip_qwen = result.get('palier') in _PRODUCTION_PALIERS
    qwen = await call_qwen(result.get("optimised_flat", "")) if body.semantic and not _skip_qwen else None
    if qwen:
        result["qwen_restructure"]            = qwen.get("prompt_restructure")
        result["qwen_audit"]                  = qwen.get("audit")
        result["qwen_template_type"]          = qwen.get("template_type")
        result["qwen_ambiguites"]             = qwen.get("ambiguites", [])
        result["qwen_composantes_manquantes"] = qwen.get("composantes_manquantes", [])
        result["gain_estime"]                 = qwen.get("gain_estime")
        result["qwen_available"]              = True
    else:
        result["qwen_available"] = False

    try:
        routing = suggest_routing(body.prompt)
        result['suggested_effort']     = routing['effort']
        result['suggested_model_tier'] = routing['model_tier']
        result['suggested_task']       = routing['task']
        result['routing_confidence']   = routing['confidence']
    except Exception as e:
        import logging
        logging.error("[routing] suggest_routing failed: %s", e, exc_info=True)
        result['suggested_effort']     = None
        result['suggested_model_tier'] = None
        result['suggested_task']       = None
        result['routing_confidence']   = 0

    # Alimentation du dataset — Aperçu (save_candidates=True) ET utilisateur authentifié
    # uniquement (anti-pollution anonyme du dataset, cf. faille #11).
    if body.save_candidates and user is not None:
        for candidate in result.get('noise_candidates', []):
            try:
                noise_candidate_repo.upsert(db, candidate['text'], candidate['score'])
            except Exception:
                pass

    return result
