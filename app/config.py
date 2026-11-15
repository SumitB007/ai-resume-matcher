"""Application configuration via Pydantic Settings.

Reads from environment variables / .env file. All config is centralized here.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ──
    app_name: str = "AI Resume & Job Matcher"
    debug: bool = False

    # ── Database ──
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ats_matcher"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/ats_matcher"

    # ── Redis ──
    redis_url: str = "redis://localhost:6379/0"

    # ── JWT Authentication ──
    secret_key: str = "change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # ── OpenRouter (LLM) ──
    openrouter_api_key: str = ""
    openrouter_default_model: str = "openai/gpt-4o-mini"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # ── Celery ──
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── Rate Limiting ──
    rate_limit_per_minute: int = 10

    # ── Phase 8 hardening ──
    # Comma-separated list of allowed browser origins for CORS. "*" is no
    # longer the default: a credentialed API must name its frontends.
    cors_origins: str = "http://localhost:3000,http://localhost:3100"
    # Auth endpoints: attempts per minute per IP (login/register abuse).
    auth_rate_limit_per_minute: int = 10
    # Anonymous ATS checker: per IP, per minute + per day (it does real
    # parsing work for unauthenticated strangers — the Phase 2 known gap).
    anon_check_rate_limit_per_minute: int = 5
    anon_check_daily_cap: int = 100
    # Per-user daily cap across all AI generation endpoints. LLM spend is
    # the product's variable cost; the cap is generous for real use and
    # useless for scripted abuse. 0 disables.
    ai_daily_cap: int = 100


settings = Settings()
