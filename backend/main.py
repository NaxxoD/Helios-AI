import re
import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import settings
from database import Base, engine, SessionLocal
from utils.seed import run_migrations, seed_conversion_factors

from routers import auth, sessions, stats, settings as settings_router, export, admin, accueil, optimiseur, chat, conversations

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_WEAK_SECRETS = {
    "helios-dev-secret-change-in-production",
    "changeme", "secret", "your-secret-key", "dev", "development",
    "your_secret_key", "change_me", "placeholder",
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    sk = settings.SECRET_KEY
    if sk in _WEAK_SECRETS or len(sk) < 32:
        raise RuntimeError(
            f"SECRET_KEY invalide (longueur={len(sk)}). "
            "Définissez une clé forte d'au moins 32 caractères avant de démarrer."
        )
    Base.metadata.create_all(bind=engine)
    run_migrations(engine)
    with SessionLocal() as db:
        seed_conversion_factors(db)
    yield


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Helios API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        is_docs = request.url.path in ("/docs", "/redoc", "/openapi.json")
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://fastapi.tiangolo.com; "
            "connect-src 'self' https://api.openai.com https://api.anthropic.com https://generativelanguage.googleapis.com"
        ) if is_docs else (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self' https://api.openai.com https://api.anthropic.com https://generativelanguage.googleapis.com"
        )
        response.headers["Content-Security-Policy"] = csp
        return response

app.add_middleware(SecurityHeadersMiddleware)

# CORS — frontend + Chrome extension (ID configuré via CHROME_EXTENSION_ID)
_ext_regex = (
    rf"^chrome-extension://{re.escape(settings.CHROME_EXTENSION_ID)}$"
    if settings.CHROME_EXTENSION_ID
    else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_origin_regex=_ext_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,             prefix="/api/auth")
app.include_router(sessions.router,         prefix="/api/sessions", tags=["sessions"])
app.include_router(stats.router,            prefix="/api")
app.include_router(settings_router.router,  prefix="/api")
app.include_router(export.router,           prefix="/api/export")
app.include_router(admin.router,            prefix="/api/admin")
app.include_router(accueil.router,          prefix="/api")
app.include_router(optimiseur.router,       prefix="/api")
app.include_router(chat.router,             prefix="/api/chat")
app.include_router(conversations.router,    prefix="/api/conversations")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
