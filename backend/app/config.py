"""Application settings, loaded from environment variables or a .env file.

Provider credentials (OPENAI_API_KEY, ANTHROPIC_API_KEY, future MLS keys) are
read here on the server only. They are never sent to the browser.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # SQLite works out of the box; set a postgresql+psycopg:// URL for PostgreSQL/PostGIS.
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'cma.db').as_posix()}"

    # Market served by the refresh job. Comma-separated in the environment.
    target_zips: str = "22308,22309"

    # Data provider used by the refresh job (see app/sources/registry.py).
    data_provider: str = "fairfax_arcgis"
    arcgis_base_url: str = (
        "https://services1.arcgis.com/ioennV6PpG5Xodq0/ArcGIS/rest/services"
    )
    # Optional ArcGIS token. The county layers are public, so this is normally blank.
    arcgis_token: str = ""
    http_timeout_seconds: float = 120.0
    refresh_concurrency: int = 4

    # AI agent (optional). Search, ranking, pricing and reports work without it.
    # AI_PROVIDER: "auto" (OpenAI when OPENAI_API_KEY is set, otherwise Anthropic), "openai",
    # "anthropic" or "none".
    ai_provider: str = "auto"
    openai_api_key: str = ""
    openai_model: str = "gpt-6.2-sol"
    # Blank uses the model's default reasoning effort.
    openai_reasoning_effort: str = ""
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5-5"
    anthropic_effort: str = "medium"
    agent_max_turns: int = 8

    # Default report branding (editable in the app; saved values override these).
    brand_company: str = "Your Brokerage"
    brand_agent_name: str = ""
    brand_phone: str = ""
    brand_email: str = ""
    brand_color: str = "#1F4E79"

    # Serve the exported Next.js app (`npm run build` -> frontend/out) from this directory when it exists.
    frontend_dist: str = str(REPO_DIR / "frontend" / "out")

    cors_origins: str = Field(default="http://localhost:3000,http://127.0.0.1:3000")

    # Optional shared login (HTTP Basic). Set APP_PASSWORD on any server reachable by others.
    app_username: str = "team"
    app_password: str = ""

    @property
    def zips(self) -> list[str]:
        return [z.strip() for z in self.target_zips.split(",") if z.strip()]

    @property
    def active_ai_provider(self) -> str | None:
        """The AI provider in use, or None when no key is configured for the chosen provider."""
        choice = self.ai_provider.strip().lower() or "auto"
        has = {"openai": bool(self.openai_api_key.strip()), "anthropic": bool(self.anthropic_api_key.strip())}
        if choice == "auto":
            return "openai" if has["openai"] else "anthropic" if has["anthropic"] else None
        return choice if has.get(choice) else None

    @property
    def ai_enabled(self) -> bool:
        return self.active_ai_provider is not None

    @property
    def ai_model(self) -> str:
        return self.anthropic_model if self.active_ai_provider == "anthropic" else self.openai_model


@lru_cache
def get_settings() -> Settings:
    return Settings()
