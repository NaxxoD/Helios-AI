from sqlalchemy import text
from sqlalchemy.orm import Session

from models import ConversionFactor


def run_migrations(engine) -> None:
    with engine.connect() as conn:
        # Contrainte unique en premier — nécessaire pour que ON CONFLICT fonctionne
        for sql in [
            "CREATE UNIQUE INDEX IF NOT EXISTS uix_factor_provider_model ON conversion_factors(provider, model)",
            """CREATE TABLE IF NOT EXISTS conversations (
                id VARCHAR(36) PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(200) DEFAULT 'Nouvelle conversation',
                provider VARCHAR(50),
                model VARCHAR(100),
                nb_turns INTEGER DEFAULT 0,
                tokens_total INTEGER DEFAULT 0,
                co2_g FLOAT DEFAULT 0.0,
                cost_usd FLOAT DEFAULT 0.0,
                impact_level VARCHAR(10) DEFAULT 'low',
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )""",
            "CREATE INDEX IF NOT EXISTS ix_conversations_user_id ON conversations(user_id)",
            """CREATE TABLE IF NOT EXISTS noise_candidates (
                id SERIAL PRIMARY KEY,
                text VARCHAR(500) NOT NULL,
                noise_score FLOAT DEFAULT 0.0,
                frequency INTEGER DEFAULT 1,
                validated BOOLEAN DEFAULT FALSE,
                label INTEGER,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )""",
            "CREATE UNIQUE INDEX IF NOT EXISTS uix_noise_candidates_text ON noise_candidates(text)",
        ]:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass

        # En mode dev (sans SMTP), tous les comptes existants sont vérifiés automatiquement
        try:
            from config import settings
            if not settings.MAIL_USERNAME:
                conn.execute(text("UPDATE users SET is_verified = TRUE WHERE is_verified = FALSE"))
                conn.commit()
        except Exception:
            pass

        # Nettoyage des doublons existants (garde le MIN(id) par paire provider+model)
        try:
            conn.execute(text("""
                DELETE FROM conversion_factors
                WHERE id NOT IN (
                    SELECT MIN(id) FROM conversion_factors GROUP BY provider, model
                )
            """))
            conn.commit()
        except Exception:
            pass

        # Nettoyage modèles obsolètes
        obsolete = [
            ("OpenAI",    "gpt-4"),
            ("OpenAI",    "gpt-3.5-turbo"),
            ("Anthropic", "claude-3-opus"),
            ("Anthropic", "claude-3-sonnet"),
            ("Anthropic", "claude-3-haiku"),
            ("Anthropic", "claude-3-5-sonnet"),
            ("Anthropic", "claude-3-5-haiku"),
            ("Google",    "gemini-pro"),
            ("Google",    "gemini-ultra"),
            ("Mistral",   "mistral-7b"),
        ]
        for provider, model in obsolete:
            try:
                conn.execute(text(
                    "DELETE FROM conversion_factors WHERE provider = :p AND model = :m"
                ), {"p": provider, "m": model})
                conn.commit()
            except Exception:
                pass

        # Ajout / mise à jour modèles (ON CONFLICT DO NOTHING — idempotent)
        new_factors = [
            # OpenAI — actifs
            ("OpenAI", "gpt-4o",        0.0000009, 0.4, 0.015),
            ("OpenAI", "gpt-4o-mini",   0.0000002, 0.4, 0.015),
            ("OpenAI", "gpt-4-1",       0.0000014, 0.4, 0.015),
            ("OpenAI", "gpt-4.1",       0.0000015, 0.4, 0.015),
            ("OpenAI", "gpt-4.1-nano",  0.0000001, 0.4, 0.015),
            ("OpenAI", "o1",            0.0000020, 0.4, 0.015),
            ("OpenAI", "o1-mini",       0.0000008, 0.4, 0.015),
            ("OpenAI", "o3",            0.0000030, 0.4, 0.015),
            ("OpenAI", "o3-mini",       0.0000010, 0.4, 0.015),
            # OpenAI GPT-5.x (IDs non confirmés — en attente doc officielle)
            ("OpenAI", "gpt-5",         0.0000035, 0.4, 0.015),
            ("OpenAI", "gpt-5-mini",    0.0000005, 0.4, 0.015),
            ("OpenAI", "gpt-5-nano",    0.0000002, 0.4, 0.015),
            ("OpenAI", "gpt-5.4",       0.0000030, 0.4, 0.015),
            ("OpenAI", "gpt-5.4-mini",  0.0000008, 0.4, 0.015),
            ("OpenAI", "gpt-5.4-nano",  0.0000003, 0.4, 0.015),
            ("OpenAI", "gpt-5.5",       0.0000050, 0.4, 0.015),
            # Anthropic (tarifs vérifiés — docs.anthropic.com mai 2026)
            ("Anthropic", "claude-opus-4-8",   0.0000022, 0.4, 0.015),
            ("Anthropic", "claude-opus-4-7",   0.0000022, 0.4, 0.015),
            ("Anthropic", "claude-sonnet-4-6", 0.0000009, 0.4, 0.015),
            ("Anthropic", "claude-haiku-4-5",  0.0000002, 0.4, 0.015),
            # Google Gemini 2.x — stable
            ("Google", "gemini-2-5-pro",        0.0000012, 0.4, 0.015),
            ("Google", "gemini-2-5-flash",       0.0000003, 0.4, 0.015),
            ("Google", "gemini-2-5-flash-lite",  0.0000002, 0.4, 0.015),
            ("Google", "gemini-2-0-flash",       0.0000002, 0.4, 0.015),
            # Google Gemini 3.x (IDs vérifiés — ai.google.dev mai 2026)
            ("Google", "gemini-3-5-flash",       0.0000003, 0.4, 0.015),
            ("Google", "gemini-3-1-flash-lite",  0.0000003, 0.4, 0.015),
            ("Google", "gemini-3-1-pro",         0.0000018, 0.4, 0.015),
            ("Google", "gemini-3-flash",         0.0000006, 0.4, 0.015),
        ]
        # Remplace claude-opus-4 par claude-opus-4-8
        try:
            conn.execute(text(
                "DELETE FROM conversion_factors WHERE provider = 'Anthropic' AND model = 'claude-opus-4'"
            ))
            conn.commit()
        except Exception:
            pass
        for provider, model, kwh, co2_std, co2_eth in new_factors:
            try:
                conn.execute(text("""
                    INSERT INTO conversion_factors (provider, model, kwh_per_token, co2_per_kwh_standard, co2_per_kwh_ethical)
                    VALUES (:provider, :model, :kwh, :co2_std, :co2_eth)
                    ON CONFLICT DO NOTHING
                """), {"provider": provider, "model": model, "kwh": kwh, "co2_std": co2_std, "co2_eth": co2_eth})
                conn.commit()
            except Exception:
                pass

        # Corriger les valeurs CO2 stockées en grammes → kg (migration one-shot)
        # La condition > 1 détecte les anciennes valeurs en grammes (une session > 1 g CO2 = > 2.5 Wh, plausible)
        try:
            conn.execute(text("""
                UPDATE impact_metrics
                SET co2_standard = co2_standard / 1000,
                    co2_ethical  = co2_ethical  / 1000,
                    co2_saved    = co2_saved    / 1000
                WHERE co2_standard > 1
            """))
            conn.commit()
        except Exception:
            pass

        # Recréer la FK session_id avec ON DELETE CASCADE
        for sql in [
            "ALTER TABLE impact_metrics DROP CONSTRAINT IF EXISTS impact_metrics_session_id_fkey",
            "ALTER TABLE impact_metrics ADD CONSTRAINT impact_metrics_session_id_fkey FOREIGN KEY (session_id) REFERENCES simulation_sessions(id) ON DELETE CASCADE",
        ]:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass

        # Recréer la FK user_id avec ON DELETE CASCADE
        for sql in [
            "ALTER TABLE simulation_sessions DROP CONSTRAINT IF EXISTS simulation_sessions_user_id_fkey",
            "ALTER TABLE simulation_sessions ADD CONSTRAINT simulation_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE",
        ]:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass

        for sql in [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS co2_weekly_threshold FLOAT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_threshold_alert_at TIMESTAMP",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_token VARCHAR(256)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token VARCHAR(256)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expires TIMESTAMP",
            "ALTER TABLE simulation_sessions DROP COLUMN IF EXISTS file_key",
            "ALTER TABLE simulation_sessions ADD COLUMN IF NOT EXISTS tokens_saved INTEGER DEFAULT 0",
"CREATE UNIQUE INDEX IF NOT EXISTS uix_impact_session ON impact_metrics(session_id)",
        ]:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass


def seed_conversion_factors(db: Session) -> None:
    if db.query(ConversionFactor).count() > 0:
        return
    defaults = [
        # OpenAI — actifs
        ("OpenAI", "gpt-4o",            0.0000009),
        ("OpenAI", "gpt-4o-mini",       0.0000002),
        ("OpenAI", "gpt-4-1",           0.0000014),
        ("OpenAI", "gpt-4.1",           0.0000015),
        ("OpenAI", "gpt-4.1-nano",      0.0000001),
        ("OpenAI", "o1",                0.0000020),
        ("OpenAI", "o1-mini",           0.0000008),
        ("OpenAI", "o3",                0.0000030),
        ("OpenAI", "o3-mini",           0.0000010),
        # OpenAI GPT-5.x (IDs non confirmés)
        ("OpenAI", "gpt-5",             0.0000035),
        ("OpenAI", "gpt-5-mini",        0.0000005),
        ("OpenAI", "gpt-5-nano",        0.0000002),
        ("OpenAI", "gpt-5.4",           0.0000030),
        ("OpenAI", "gpt-5.4-mini",      0.0000008),
        ("OpenAI", "gpt-5.4-nano",      0.0000003),
        ("OpenAI", "gpt-5.5",           0.0000050),
        # Anthropic (vérifiés docs.anthropic.com mai 2026)
        ("Anthropic", "claude-opus-4-8",   0.0000022),
        ("Anthropic", "claude-opus-4-7",   0.0000022),
        ("Anthropic", "claude-sonnet-4-6", 0.0000009),
        ("Anthropic", "claude-haiku-4-5",  0.0000002),
        # Google Gemini 2.x — stable
        ("Google", "gemini-2-5-pro",         0.0000012),
        ("Google", "gemini-2-5-flash",        0.0000003),
        ("Google", "gemini-2-5-flash-lite",   0.0000002),
        ("Google", "gemini-2-0-flash",        0.0000002),
        # Google Gemini 3.x (vérifiés ai.google.dev mai 2026)
        ("Google", "gemini-3-5-flash",        0.0000003),
        ("Google", "gemini-3-1-flash-lite",   0.0000003),
        ("Google", "gemini-3-1-pro",          0.0000018),
        ("Google", "gemini-3-flash",          0.0000006),
        # Meta & Mistral — workflows legacy
        ("Meta",    "llama-3-8b",         0.0000003),
        ("Meta",    "llama-3-70b",        0.0000012),
        ("Mistral", "mistral-large",      0.0000012),
        ("Mistral", "mistral-small",      0.0000004),
    ]
    for provider, model, kwh in defaults:
        db.add(ConversionFactor(
            provider=provider,
            model=model,
            kwh_per_token=kwh,
            co2_per_kwh_standard=0.4,
            co2_per_kwh_ethical=0.015,
        ))
    db.commit()
