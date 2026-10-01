from pathlib import Path

from alembic.config import Config
from sqlalchemy import Engine, text

from alembic import command
from tabernas.db.models import Base
from tests.support import TEST_DATABASE_URL, reset_schema

BACKEND_DIR = Path(__file__).resolve().parents[2]


def alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    return cfg


def test_migrations_match_models_and_seed_settings(engine: Engine) -> None:
    reset_schema(engine)
    try:
        cfg = alembic_config()
        command.upgrade(cfg, "head")
        command.check(cfg)  # raises if the models and the migrated schema differ
        with engine.connect() as conn:
            stored = dict(conn.execute(text("SELECT key, value FROM setting")).all())
        assert stored == {
            "entry_time_kitchen": "16:30",
            "entry_time_other": "16:40",
            "tolerance_minutes": "10",
            "review_streak_days": "2",
            "review_late_week": "2",
            "review_late_weeks": "3",
        }
    finally:
        reset_schema(engine)
        Base.metadata.create_all(engine)
