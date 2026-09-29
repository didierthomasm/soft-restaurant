import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pymssql
import pytest

from tabernas.domain.periods import RangeError
from tabernas.sr import pymssql_source
from tabernas.sr.pymssql_source import ALL_SQL, CHECKINS_SQL, EMPLOYEES_SQL, PymssqlSource
from tabernas.sr.source import SrEmployee, SrUnavailableError


class FakeCursor:
    def __init__(self, rows: list[dict[str, Any]], executed: list[tuple[str, Any]]) -> None:
        self._rows = rows
        self._executed = executed

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def execute(self, sql: str, params: Any = None) -> None:
        self._executed.append((sql, params))

    def fetchall(self) -> list[dict[str, Any]]:
        return self._rows


class FakeConnection:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.executed: list[tuple[str, Any]] = []
        self.closed = False

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, *exc: object) -> None:
        self.closed = True

    def cursor(self, as_dict: bool = False) -> FakeCursor:
        assert as_dict, "rows must come back as dicts"
        return FakeCursor(self.rows, self.executed)


def source_with(rows: list[dict[str, Any]]) -> tuple[PymssqlSource, FakeConnection]:
    conn = FakeConnection(rows)
    return PymssqlSource(lambda: conn), conn


def test_fetch_checkins_sends_bounded_query_and_normalizes_ids() -> None:
    rows = [
        {"idempleado": "06", "entrada": datetime(2026, 8, 1, 16, 41, 31)},
        {"idempleado": " 011 ", "entrada": datetime(2026, 8, 2, 16, 30, 2)},
    ]
    source, conn = source_with(rows)
    result = source.fetch_checkins(date(2026, 8, 1), date(2026, 8, 31))
    assert conn.executed == [(CHECKINS_SQL, (datetime(2026, 8, 1), datetime(2026, 9, 1)))]
    assert [(c.sr_id, c.at) for c in result] == [
        (6, datetime(2026, 8, 1, 16, 41, 31)),
        (11, datetime(2026, 8, 2, 16, 30, 2)),
    ]
    assert conn.closed


def test_non_numeric_ids_are_dropped_and_logged(caplog: pytest.LogCaptureFixture) -> None:
    rows = [
        {"idempleado": "XX", "entrada": datetime(2026, 8, 1, 16, 41)},
        {"idempleado": "06", "entrada": datetime(2026, 8, 1, 16, 42)},
    ]
    source, _ = source_with(rows)
    with caplog.at_level(logging.WARNING):
        result = source.fetch_checkins(date(2026, 8, 1), date(2026, 8, 1))
    assert [c.sr_id for c in result] == [6]
    assert "non-numeric" in caplog.text


def test_range_is_validated_before_connecting() -> None:
    def must_not_connect() -> Any:
        pytest.fail("should not connect")

    with pytest.raises(RangeError):
        PymssqlSource(must_not_connect).fetch_checkins(date(2026, 1, 1), date(2026, 6, 1))


def test_sql_is_read_only_and_never_touches_sensitive_columns() -> None:
    module_text = Path(pymssql_source.__file__).read_text(encoding="utf-8").lower()
    assert "contrase" not in module_text
    assert "fotografia" not in module_text
    for sql in ALL_SQL:
        words = sql.upper().split()
        assert words[0] == "SELECT"
        assert not {"INSERT", "UPDATE", "DELETE", "EXEC", "DROP", "ALTER", "MERGE"} & set(words)


def test_table_queries_use_nolock() -> None:
    for sql in (CHECKINS_SQL, EMPLOYEES_SQL):
        assert "WITH (NOLOCK)" in sql


def test_fetch_employees_maps_rows() -> None:
    rows = [{"idmesero": "06", "nombre": " EMPLEADO A ", "tipo": 1, "visible": 1}]
    source, conn = source_with(rows)
    assert source.fetch_employees() == [
        SrEmployee(sr_id=6, name="EMPLEADO A", kind=1, visible=True)
    ]
    assert conn.executed == [(EMPLOYEES_SQL, None)]


def _info_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "server": "SRV",
        "instance": "INST",
        "version": "12.0.4100.1",
        "edition": "Express Edition",
        "database_name": "softrestaurant11",
        "login": "reportes_ro",
        "is_datareader": 1,
        "is_denywriter": 1,
        "is_sysadmin": 0,
    }
    return {**row, **overrides}


def test_server_info_read_only_flags() -> None:
    source, _ = source_with([_info_row()])
    assert source.server_info().read_only
    writer, _ = source_with([_info_row(is_denywriter=None)])
    assert not writer.server_info().read_only
    admin, _ = source_with([_info_row(is_sysadmin=1)])
    assert not admin.server_info().read_only


def test_driver_errors_become_sr_unavailable_without_secrets() -> None:
    def broken() -> Any:
        raise pymssql.OperationalError("login failed, password hunter2")

    with pytest.raises(SrUnavailableError) as info:
        PymssqlSource(broken).fetch_employees()
    assert "hunter2" not in str(info.value)
