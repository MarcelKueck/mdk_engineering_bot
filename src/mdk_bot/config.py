"""Application configuration loaded from environment variables.

All settings live in :class:`Settings` and are exposed as a process-wide
singleton via :func:`get_settings`. Anything that smells like a secret
gets scrubbed from log output (see :func:`Settings.safe_dump`).
"""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from typing import Literal
from uuid import UUID

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Process configuration sourced from ``.env`` / environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    ENVIRONMENT: Literal["development", "production", "test"] = "development"
    LOG_LEVEL: str = "INFO"
    TIMEZONE: str = "Europe/Berlin"

    DATABASE_URL: str = "postgresql+asyncpg://mdk:mdk@localhost:5432/mdk"
    DATABASE_URL_SYNC: str = "postgresql+psycopg://mdk:mdk@localhost:5432/mdk"
    REDIS_URL: str = "redis://localhost:6379/0"

    SECRET_KEY: str = "dev-secret-key-change-me"
    WEB_SESSION_TOKEN: str = "dev-web-token"
    INTERNAL_API_TOKEN: str = "dev-internal-token"
    MASTER_ENCRYPTION_KEY: str = ""

    TELEGRAM_BOT_TOKEN: str = ""
    AUTHORIZED_TELEGRAM_USER_ID: int = 0

    BOT_DOMAIN: str = "localhost"

    OBLIGATIONS_FILE: str = "./obligations.json"
    DAILY_CHECK_HOUR: int = 8
    DEFAULT_TENANT_ID: UUID = UUID("00000000-0000-0000-0000-000000000001")

    INTERNAL_API_URL: str = "http://api:8000/api/v1"

    # -- Phase 2: feature flags --------------------------------------------
    # When a flag is off OR its required credential is missing, the related
    # module no-ops cleanly (logs once at module init and exits).
    FEATURE_LEXWARE_SYNC: bool = False
    FEATURE_USTVA: bool = False
    FEATURE_LIQUIDITY: bool = False
    FEATURE_DUNNING: bool = False
    FEATURE_VIES: bool = False
    FEATURE_DATEV: bool = False

    # -- Phase 2: Lexware Office (lexoffice) -------------------------------
    LEXWARE_API_KEY: str = ""
    LEXWARE_API_BASE_URL: str = "https://api.lexoffice.io/v1"
    LEXWARE_SYNC_HOUR: int = 7

    # -- Phase 2: Liquidity ------------------------------------------------
    # Manual opening balance — single source of truth until a bank API lands.
    LIQUIDITY_OPENING_BALANCE: Decimal = Decimal("0")
    LIQUIDITY_RUNWAY_WARNING_DAYS: int = 45
    # Rate (0..1) applied to received revenue to compute Steuerrücklage.
    STEUERRUECKLAGE_RATE: Decimal = Decimal("0.30")

    # -- Phase 2: Mahnwesen (dunning) --------------------------------------
    # German B2B Verzugszinsen = Bundesbank Basiszinssatz + 9 percentage points
    # (§ 288 Abs. 2 BGB). The Basiszinssatz changes every January and July;
    # the value below is the rate effective 2025-01-01 (3.27 %). REVIEW THIS
    # FIELD EVERY JAN/JUL — the Bundesbank publishes the new value at
    # https://www.bundesbank.de/...basiszinssatz before each half-year.
    BASISZINSSATZ: Decimal = Decimal("3.27")
    DUNNING_B2B_MARGIN: Decimal = Decimal("9.00")
    DUNNING_FEE_AMOUNT: Decimal = Decimal("40.00")

    # -- Phase 2: VIES VAT validation --------------------------------------
    # The operator's own VAT ID — sent as the requester for a qualified query.
    VIES_REQUESTER_VAT_ID: str = ""
    VIES_API_URL: str = "https://ec.europa.eu/taxation_customs/vies/services/checkVatService"

    # -- Phase 2: DATEV year-end export ------------------------------------
    DATEV_EXPORT_DIR: str = "./data/datev"

    @field_validator("DAILY_CHECK_HOUR", "LEXWARE_SYNC_HOUR")
    @classmethod
    def _hour_in_range(cls, v: int) -> int:
        if not 0 <= v <= 23:
            raise ValueError("hour must be 0..23")
        return v

    def safe_dump(self) -> dict[str, object]:
        """Return a dict suitable for logging — secrets are masked."""
        secret_keys = {
            "SECRET_KEY",
            "WEB_SESSION_TOKEN",
            "INTERNAL_API_TOKEN",
            "MASTER_ENCRYPTION_KEY",
            "TELEGRAM_BOT_TOKEN",
            "DATABASE_URL",
            "DATABASE_URL_SYNC",
            "LEXWARE_API_KEY",
        }
        out: dict[str, object] = {}
        for k, v in self.model_dump().items():
            if k in secret_keys and v:
                out[k] = "***"
            else:
                out[k] = v
        return out


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings singleton."""
    return Settings()
