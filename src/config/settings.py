"""Global application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class Settings(BaseModel):
    """Application-level settings (not tenant-specific)."""

    anthropic_api_key: str = Field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", "")
    )
    langchain_api_key: str = Field(
        default_factory=lambda: os.getenv("LANGCHAIN_API_KEY", "")
    )
    tenants_dir: str = Field(
        default_factory=lambda: os.getenv("TENANTS_DIR", "./tenants")
    )
    database_path: str = Field(
        default_factory=lambda: os.getenv("DATABASE_PATH", "./data/sales_agent.db")
    )
    telegram_bot_token: str = Field(
        default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", "")
    )
    telegram_driver_bot_token: str = Field(
        default_factory=lambda: os.getenv("TELEGRAM_DRIVER_BOT_TOKEN", "")
    )
    default_city: str = Field(
        default_factory=lambda: os.getenv("DEFAULT_CITY", "Mazatlán, Sinaloa, México")
    )
    maps_api_key: str = Field(
        default_factory=lambda: os.getenv("MAPS_API_KEY", "")
    )
    whatsapp_token: str = Field(
        default_factory=lambda: os.getenv("WHATSAPP_TOKEN", os.getenv("WHATSAPP_ACCESS_TOKEN", ""))
    )
    whatsapp_phone_number_id: str = Field(
        default_factory=lambda: os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    )
    whatsapp_verify_token: str = Field(
        default_factory=lambda: os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    )
    whatsapp_business_account_id: str = Field(
        default_factory=lambda: os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", os.getenv("WHATSAPP_WABA_ID", ""))
    )
    whatsapp_api_version: str = Field(
        default_factory=lambda: os.getenv("WHATSAPP_API_VERSION", "v21.0")
    )
    whatsapp_app_secret: str = Field(
        default_factory=lambda: os.getenv("WHATSAPP_APP_SECRET", "")
    )
    cors_origins: str = Field(
        default_factory=lambda: os.getenv("CORS_ORIGINS", "*")
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
