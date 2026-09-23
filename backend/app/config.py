import os
import json
from typing import Any
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "LM-Screen"
    ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "lm-screen-super-secret-key-change-in-production-2026"
    BACKEND_HOST: str = "0.0.0.0"
    # Render injects PORT as an env var; default to 8000 for local dev
    BACKEND_PORT: int = int(os.environ.get("PORT", 8000))
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./lm_screen.db"

    # CORS — accepts a comma-separated string (e.g. from Render env dashboard)
    # OR a JSON array string OR already a list.
    CORS_ORIGINS: Any = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]

    # Uploads directory — portable, never hardcodes Windows paths
    UPLOAD_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "uploads"
    )

    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list:
        """Accept a comma-separated string, JSON array string, or a list."""
        if isinstance(v, list):
            return [o.strip() for o in v if o.strip()]
        if isinstance(v, str):
            v = v.strip()
            # Try JSON array first
            if v.startswith("["):
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [o.strip() for o in parsed if o.strip()]
                except json.JSONDecodeError:
                    pass
            # Comma-separated fallback
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_db_url(cls, v: str) -> str:
        """
        SQLAlchemy 2.x requires 'postgresql://' not 'postgres://'.
        Render provides DATABASE_URL starting with 'postgres://'.
        """
        if isinstance(v, str) and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v


settings = Settings()
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
