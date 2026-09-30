from pathlib import Path

from tests.support import DEFAULT_TEST_DATABASE_URL, resolve_test_database_url

FROM_ENV = "postgresql+psycopg://u:p@localhost:5432/from_env_test"
FROM_FILE = "postgresql+psycopg://u:p@localhost:5432/from_file_test"


def _env_file(tmp_path: Path, content: str) -> Path:
    path = tmp_path / ".env"
    path.write_text(content, encoding="utf-8")
    return path


def test_environment_variable_wins(tmp_path: Path) -> None:
    env_file = _env_file(tmp_path, f"TEST_DATABASE_URL={FROM_FILE}\n")
    assert resolve_test_database_url({"TEST_DATABASE_URL": FROM_ENV}, env_file) == FROM_ENV


def test_falls_back_to_the_env_file(tmp_path: Path) -> None:
    env_file = _env_file(tmp_path, f"OTHER=1\nTEST_DATABASE_URL={FROM_FILE}\n")
    assert resolve_test_database_url({}, env_file) == FROM_FILE


def test_defaults_when_neither_is_set(tmp_path: Path) -> None:
    assert resolve_test_database_url({}, tmp_path / "missing.env") == DEFAULT_TEST_DATABASE_URL
    env_file = _env_file(tmp_path, "OTHER=1\n")
    assert resolve_test_database_url({}, env_file) == DEFAULT_TEST_DATABASE_URL
