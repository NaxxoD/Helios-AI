import os
from pydantic_settings import BaseSettings, SettingsConfigDict

_HERE = os.path.dirname(os.path.abspath(__file__))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=os.path.join(_HERE, ".env"), extra="ignore")

    SECRET_KEY: str = "helios-dev-secret-change-in-production"
    DATABASE_URL: str = "postgresql+psycopg://helios:helios@localhost:5433/helios"
    FRONTEND_URL: str = "http://localhost:5173"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 30

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_USER: str = "helios"
    MINIO_PASSWORD: str = "helios123"
    MINIO_BUCKET: str = "conversations"
    MINIO_SECURE: bool = False

    # Chrome extension (laisser vide jusqu'à la publication de l'extension)
    CHROME_EXTENSION_ID: str = ""

    # Logging
    LOG_LEVEL: str = "INFO"

    # Qwen / Ollama (optimiseur sémantique local)
    OLLAMA_URL: str = "http://localhost:11434"
    QWEN_MODEL: str = "qwen3:8b"
    QWEN_ENABLED: bool = False

    # Email (facultatif — laisser vide pour désactiver les envois)
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""
    MAIL_FROM_NAME: str = "Helios AI"
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_PORT: int = 587
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False


settings = Settings()
