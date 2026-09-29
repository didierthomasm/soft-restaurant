import pytest
from pydantic import ValidationError

from tabernas.config import Settings


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("SR_MODE", "SR_DB_HOST", "SR_DB_PASSWORD", "DATABASE_URL", "APP_TIMEZONE"):
        monkeypatch.delenv(name, raising=False)


def test_defaults_to_fake_mode_without_sr_credentials() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.sr_mode == "fake"
    assert settings.app_timezone == "America/Mexico_City"


def test_live_mode_requires_host_and_password() -> None:
    with pytest.raises(ValidationError, match="SR_DB_HOST, SR_DB_PASSWORD"):
        Settings(_env_file=None, sr_mode="live")  # type: ignore[call-arg]


def test_live_mode_refuses_sa_login() -> None:
    with pytest.raises(ValidationError, match="sa"):
        Settings(
            _env_file=None,  # type: ignore[call-arg]
            sr_mode="live",
            sr_db_host="10.0.0.1",
            sr_db_password="secret",  # type: ignore[arg-type]
            sr_db_user="sa",
        )


def test_live_mode_refuses_sa_login_case_insensitive_with_whitespace() -> None:
    with pytest.raises(ValidationError, match="sa"):
        Settings(
            _env_file=None,  # type: ignore[call-arg]
            sr_mode="live",
            sr_db_host="10.0.0.1",
            sr_db_password="secret",  # type: ignore[arg-type]
            sr_db_user=" SA ",
        )


def test_live_mode_accepts_complete_config() -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        sr_mode="live",
        sr_db_host="10.0.0.1",
        sr_db_password="secret",  # type: ignore[arg-type]
    )
    assert settings.sr_db_password.get_secret_value() == "secret"
    assert "secret" not in repr(settings)
