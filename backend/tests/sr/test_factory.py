from tabernas.config import Settings
from tabernas.sr import build_sr_source
from tabernas.sr.fake_source import FakeSource
from tabernas.sr.pymssql_source import PymssqlSource


def test_fake_mode_builds_fake_source() -> None:
    settings = Settings(_env_file=None, sr_mode="fake")  # type: ignore[call-arg]
    assert isinstance(build_sr_source(settings), FakeSource)


def test_live_mode_builds_pymssql_source_without_connecting() -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        sr_mode="live",
        sr_db_host="192.0.2.1",  # TEST-NET, never contacted here
        sr_db_password="x",  # type: ignore[arg-type]
    )
    assert isinstance(build_sr_source(settings), PymssqlSource)
