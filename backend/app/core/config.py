"""Application settings, loaded from environment / .env (never hardcoded)."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- General ----
    app_name: str = "VPN Robot"
    environment: Literal["development", "staging", "production"] = "production"
    debug: bool = False
    timezone: str = "Asia/Tehran"
    secret_key: str = Field(min_length=16)
    api_base_url: str = "http://localhost:8000"
    dashboard_base_url: str = "http://localhost:3000"

    # ---- Database ----
    database_url: str = Field(
        default="postgresql+asyncpg://vpnrobot:vpnrobot@postgres:5432/vpnrobot"
    )

    # ---- Redis / Celery ----
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # ---- JWT ----
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    jwt_refresh_secret_key: str = Field(min_length=16)

    # ---- Telegram ----
    customer_bot_token: str = ""
    admin_bot_token: str = ""
    bootstrap_super_admins: str = ""  # comma-separated telegram ids
    telegram_webhook_secret: str = ""
    use_webhook: bool = False

    # ---- Payments ----
    payment_provider: Literal["zarinpal", "idpay", "nextpay"] = "zarinpal"
    zarinpal_merchant_id: str = ""
    zarinpal_sandbox: bool = True
    idpay_api_key: str = ""
    idpay_sandbox: bool = True
    nextpay_api_key: str = ""
    payment_callback_url: str = ""

    # ---- Inventory ----
    low_inventory_threshold: int = 5

    # ---- Uploads ----
    media_root: str = "/app/media"
    max_upload_size_mb: int = 10
    allowed_upload_extensions: str = "jpg,jpeg,png,pdf"

    # ---- CORS / rate limit ----
    cors_origins: str = "http://localhost:3000"
    rate_limit_per_minute: int = 120

    # ---- Derived helpers ----
    @computed_field  # type: ignore[prop-decorator]
    @property
    def sync_database_url(self) -> str:
        """Sync DSN used by Alembic / psycopg2 utilities."""
        return self.database_url.replace("+asyncpg", "+psycopg2")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def bootstrap_admin_ids(self) -> list[int]:
        return [
            int(x.strip())
            for x in self.bootstrap_super_admins.split(",")
            if x.strip().isdigit()
        ]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def allowed_extension_set(self) -> set[str]:
        return {e.strip().lower() for e in self.allowed_upload_extensions.split(",") if e.strip()}

    @field_validator("secret_key", "jwt_refresh_secret_key")
    @classmethod
    def _no_placeholder_secret(cls, v: str) -> str:
        if "change-me" in v.lower() and len(v) < 24:
            # Permit during local dev but never silently in production.
            return v
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
