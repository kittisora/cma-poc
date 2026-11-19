"""Run Alembic migrations programmatically (used by the refresh job, the API on
startup and the test suite). Equivalent to `alembic upgrade head`."""

from __future__ import annotations

from alembic import command
from alembic.config import Config

from .config import BACKEND_DIR, get_settings


def alembic_config(url: str | None = None) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url or get_settings().database_url)
    return cfg


def upgrade_db(url: str | None = None) -> None:
    command.upgrade(alembic_config(url), "head")
