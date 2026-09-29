"""SoftRestaurant reader over pymssql. The ONLY module that sends SQL to SR.

Rules: SELECT only, WITH (NOLOCK) on every table, always date-bounded, never the
password or photo columns of `meseros`.
"""

import logging
import os
from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from typing import Any

import pymssql

from tabernas.config import REPO_ROOT, Settings
from tabernas.domain.periods import validate_range
from tabernas.sr.source import (
    SrCheckin,
    SrEmployee,
    SrServerInfo,
    SrUnavailableError,
    parse_sr_id,
)

logger = logging.getLogger(__name__)

CHECKINS_SQL = (
    "SELECT idempleado, entrada FROM registroasistencias WITH (NOLOCK) "
    "WHERE entrada >= %s AND entrada < %s ORDER BY entrada"
)
EMPLOYEES_SQL = "SELECT idmesero, nombre, tipo, visible FROM meseros WITH (NOLOCK)"
SERVER_INFO_SQL = """
SELECT
    CAST(@@SERVERNAME AS NVARCHAR(128))                     AS [server],
    CAST(SERVERPROPERTY('InstanceName') AS NVARCHAR(128))   AS [instance],
    CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(128)) AS [version],
    CAST(SERVERPROPERTY('Edition') AS NVARCHAR(128))        AS [edition],
    DB_NAME()                                               AS [database_name],
    SUSER_SNAME()                                           AS [login],
    IS_ROLEMEMBER('db_datareader')                          AS [is_datareader],
    IS_ROLEMEMBER('db_denydatawriter')                      AS [is_denywriter],
    IS_SRVROLEMEMBER('sysadmin')                            AS [is_sysadmin]
""".strip()
ALL_SQL = (CHECKINS_SQL, EMPLOYEES_SQL, SERVER_INFO_SQL)

LOGIN_TIMEOUT_S = 10
QUERY_TIMEOUT_S = 20

Row = dict[str, Any]


class PymssqlSource:
    def __init__(self, connect: Callable[[], Any]) -> None:
        self._connect = connect

    @classmethod
    def from_settings(cls, settings: Settings) -> "PymssqlSource":
        # FreeTDS must read freetds.conf (TLS 1.0 for SQL Server 2014) before connecting.
        os.environ.setdefault("FREETDSCONF", str(REPO_ROOT / "freetds.conf"))

        def connect() -> Any:
            return pymssql.connect(
                server=settings.sr_db_host,
                port=str(settings.sr_db_port),
                database=settings.sr_db_name,
                user=settings.sr_db_user,
                password=settings.sr_db_password.get_secret_value(),
                login_timeout=LOGIN_TIMEOUT_S,
                timeout=QUERY_TIMEOUT_S,
            )

        return cls(connect)

    def fetch_checkins(self, start: date, end: date) -> list[SrCheckin]:
        validate_range(start, end)
        params = (
            datetime.combine(start, time.min),
            datetime.combine(end + timedelta(days=1), time.min),
        )
        return [
            SrCheckin(sr_id=sr_id, at=row["entrada"])
            for row in self._query(CHECKINS_SQL, params)
            if (sr_id := parse_sr_id(row["idempleado"])) is not None
        ]

    def fetch_employees(self) -> list[SrEmployee]:
        return [
            SrEmployee(
                sr_id=sr_id,
                name=str(row["nombre"] or "").strip(),
                kind=row["tipo"],
                visible=bool(row["visible"]),
            )
            for row in self._query(EMPLOYEES_SQL)
            if (sr_id := parse_sr_id(row["idmesero"])) is not None
        ]

    def server_info(self) -> SrServerInfo:
        row = self._query(SERVER_INFO_SQL)[0]
        return SrServerInfo(
            server=str(row["server"]),
            instance=str(row["instance"] or ""),
            version=str(row["version"]),
            edition=str(row["edition"]),
            database=str(row["database_name"]),
            login=str(row["login"]),
            is_datareader=bool(row["is_datareader"]),
            is_denywriter=bool(row["is_denywriter"]),
            is_sysadmin=bool(row["is_sysadmin"]),
        )

    def _query(self, sql: str, params: tuple[Any, ...] | None = None) -> list[Row]:
        try:
            conn = self._connect()
            with conn, conn.cursor(as_dict=True) as cursor:
                cursor.execute(sql, params)
                return list(cursor.fetchall())
        except pymssql.Error as exc:
            # Never log the exception text: driver messages can echo connection details.
            logger.warning("SoftRestaurant query failed: %s", type(exc).__name__)
            raise SrUnavailableError("No se pudo leer SoftRestaurant") from exc
