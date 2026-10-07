"""
Email utility — wraps fastapi-mail.
All functions are no-ops when MAIL_USERNAME is not configured.
"""
import logging
from config import settings

logger = logging.getLogger(__name__)

_fm = None


def _get_mailer():
    global _fm
    if _fm is not None:
        return _fm
    if not settings.MAIL_USERNAME:
        return None
    try:
        from fastapi_mail import FastMail, ConnectionConfig
        conf = ConnectionConfig(
            MAIL_USERNAME=settings.MAIL_USERNAME,
            MAIL_PASSWORD=settings.MAIL_PASSWORD,
            MAIL_FROM=settings.MAIL_FROM or settings.MAIL_USERNAME,
            MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
            MAIL_SERVER=settings.MAIL_SERVER,
            MAIL_PORT=settings.MAIL_PORT,
            MAIL_STARTTLS=settings.MAIL_STARTTLS,
            MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True,
        )
        _fm = FastMail(conf)
    except Exception as e:
        logger.warning("Mailer init failed: %s", e)
    return _fm


async def send_verification_email(to: str, verify_url: str) -> None:
    fm = _get_mailer()
    if not fm:
        logger.warning("[mailer] verification email suppressed (no MAIL_USERNAME). URL: %s", verify_url)
        return
    from fastapi_mail import MessageSchema, MessageType
    msg = MessageSchema(
        subject="Confirmez votre adresse email — Helios AI",
        recipients=[to],
        body=f"""
<html><body style="font-family:sans-serif;background:#0b1410;color:#e8f0eb;padding:32px">
  <div style="max-width:480px;margin:0 auto;background:#111d17;border-radius:16px;border:1px solid #1f3028;padding:32px">
    <h2 style="color:#4ade80;margin-bottom:8px">Bienvenue sur Helios AI</h2>
    <p style="color:#6b8f79;margin-bottom:24px">Cliquez sur le bouton ci-dessous pour confirmer votre adresse email et activer votre compte.</p>
    <a href="{verify_url}"
       style="display:inline-block;background:linear-gradient(135deg,#16a34a,#22c55e);color:#fff;
              font-weight:700;padding:12px 28px;border-radius:12px;text-decoration:none;font-size:14px">
      Confirmer mon adresse email
    </a>
    <p style="color:#4b6b56;font-size:12px;margin-top:24px">Si vous n'avez pas créé de compte, ignorez cet email.</p>
  </div>
</body></html>
""",
        subtype=MessageType.html,
    )
    try:
        await fm.send_message(msg)
    except Exception as e:
        logger.error("Failed to send verification email to %s: %s — fallback URL: %s", to, e, verify_url)


async def send_reset_email(to: str, reset_url: str) -> None:
    fm = _get_mailer()
    if not fm:
        logger.info("[mailer] reset email suppressed (no MAIL_USERNAME). URL: %s", reset_url)
        return
    from fastapi_mail import MessageSchema, MessageType
    msg = MessageSchema(
        subject="Réinitialisation de votre mot de passe — Helios AI",
        recipients=[to],
        body=f"""
<html><body style="font-family:sans-serif;background:#0b1410;color:#e8f0eb;padding:32px">
  <div style="max-width:480px;margin:0 auto;background:#111d17;border-radius:16px;border:1px solid #1f3028;padding:32px">
    <h2 style="color:#4ade80;margin-bottom:8px">Réinitialisation du mot de passe</h2>
    <p style="color:#6b8f79;margin-bottom:24px">Cliquez sur le bouton ci-dessous pour définir un nouveau mot de passe. Le lien expire dans <strong style="color:#e8f0eb">1 heure</strong>.</p>
    <a href="{reset_url}"
       style="display:inline-block;background:linear-gradient(135deg,#16a34a,#22c55e);color:#fff;
              font-weight:700;padding:12px 28px;border-radius:12px;text-decoration:none;font-size:14px">
      Réinitialiser le mot de passe
    </a>
    <p style="color:#4b6b56;font-size:12px;margin-top:24px">Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.</p>
  </div>
</body></html>
""",
        subtype=MessageType.html,
    )
    try:
        await fm.send_message(msg)
    except Exception as e:
        logger.error("Failed to send reset email to %s: %s", to, e)


async def send_threshold_alert(to: str, weekly_co2: float, threshold: float) -> None:
    fm = _get_mailer()
    if not fm:
        logger.info("[mailer] threshold alert suppressed (no MAIL_USERNAME).")
        return
    from fastapi_mail import MessageSchema, MessageType

    def fmt_co2(g: float) -> str:
        if g < 0.001:
            return f"{g * 1000:.2f} µg"
        if g < 1:
            return f"{g * 1000:.1f} mg"
        return f"{g:.3f} g"

    msg = MessageSchema(
        subject="⚠️ Seuil CO₂ dépassé cette semaine — Helios AI",
        recipients=[to],
        body=f"""
<html><body style="font-family:sans-serif;background:#0b1410;color:#e8f0eb;padding:32px">
  <div style="max-width:480px;margin:0 auto;background:#111d17;border-radius:16px;border:1px solid #1f3028;padding:32px">
    <h2 style="color:#ff8533;margin-bottom:8px">Seuil CO₂ hebdomadaire dépassé</h2>
    <p style="color:#6b8f79;margin-bottom:16px">
      Votre consommation IA de cette semaine est de
      <strong style="color:#ef4444">{fmt_co2(weekly_co2)}</strong>,
      au-dessus de votre seuil fixé à <strong style="color:#e8f0eb">{fmt_co2(threshold)}</strong>.
    </p>
    <p style="color:#6b8f79;margin-bottom:24px">
      Pensez à utiliser des modèles plus sobres (GPT-4o mini, Claude Haiku, Gemini Flash) ou à optimiser vos prompts.
    </p>
    <a href="{settings.FRONTEND_URL}/optimiser"
       style="display:inline-block;background:linear-gradient(135deg,#16a34a,#22c55e);color:#fff;
              font-weight:700;padding:12px 28px;border-radius:12px;text-decoration:none;font-size:14px">
      Optimiser mes prompts
    </a>
    <p style="color:#4b6b56;font-size:12px;margin-top:24px">
      Modifier votre seuil dans <a href="{settings.FRONTEND_URL}/parametres" style="color:#4ade80">Paramètres</a>.
    </p>
  </div>
</body></html>
""",
        subtype=MessageType.html,
    )
    try:
        await fm.send_message(msg)
    except Exception as e:
        logger.error("Failed to send threshold alert to %s: %s", to, e)
