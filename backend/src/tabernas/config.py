"""Application settings, read from environment variables and the repo's .env file."""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/src/tabernas/config.py -> repo root. Inside Docker this resolves to "/",
# where no .env exists; compose injects the variables instead.
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    sr_mode: Literal["live", "fake"] = "fake"
    sr_db_host: str = ""
    sr_db_port: int = 1433
    sr_db_name: str = "softrestaurant11"
    sr_db_user: str = "reportes_ro"
    sr_db_password: SecretStr = SecretStr("")
    database_url: str = "postgresql+psycopg://tabernas:tabernas@localhost:5432/tabernas"
    app_timezone: str = "America/Mexico_City"

    @model_validator(mode="after")
    def _require_live_credentials(self) -> Self:
        if self.sr_mode != "live":
            return self
        required = {
            "SR_DB_HOST": self.sr_db_host,
            "SR_DB_PASSWORD": self.sr_db_password.get_secret_value(),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"Faltan variables para SR_MODE=live: {', '.join(missing)}")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
