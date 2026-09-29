"""Connection smoke test for the SoftRestaurant DB (read-only).

Usage (from the repo root): uv run --project backend scripts/check_connection.py
Reads credentials from .env. Runs only SELECTs on server metadata.
"""
import os
import sys
from pathlib import Path

# Must be set before pymssql opens a connection; see freetds.conf for why.
os.environ.setdefault("FREETDSCONF", str(Path(__file__).resolve().parent.parent / "freetds.conf"))

import pymssql  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

REQUIRED_VARS = ("SR_DB_HOST", "SR_DB_PORT", "SR_DB_NAME", "SR_DB_USER", "SR_DB_PASSWORD")

CHECK_SQL = """
SELECT
    @@SERVERNAME                                   AS servidor,
    CAST(SERVERPROPERTY('InstanceName') AS NVARCHAR(128)) AS instancia,
    CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(128)) AS version,
    CAST(SERVERPROPERTY('Edition') AS NVARCHAR(128))        AS edicion,
    DB_NAME()                                      AS base,
    SUSER_SNAME()                                  AS login,
    IS_ROLEMEMBER('db_datareader')                 AS es_datareader,
    IS_ROLEMEMBER('db_denydatawriter')             AS es_denywriter,
    IS_SRVROLEMEMBER('sysadmin')                   AS es_sysadmin
"""


def load_config() -> dict:
    load_dotenv()
    missing = [v for v in REQUIRED_VARS if not os.getenv(v)]
    if missing:
        sys.exit(f"Faltan variables en .env: {', '.join(missing)}")
    return {v: os.environ[v] for v in REQUIRED_VARS}


def main() -> None:
    cfg = load_config()
    try:
        conn = pymssql.connect(
            server=cfg["SR_DB_HOST"],
            port=cfg["SR_DB_PORT"],
            database=cfg["SR_DB_NAME"],
            user=cfg["SR_DB_USER"],
            password=cfg["SR_DB_PASSWORD"],
            login_timeout=15,
            timeout=30,
        )
    except pymssql.OperationalError as exc:
        sys.exit(f"No se pudo conectar: {exc}")

    with conn, conn.cursor(as_dict=True) as cur:
        cur.execute(CHECK_SQL)
        row = cur.fetchone()

    for key, value in row.items():
        print(f"{key:>14}: {value}")
    if row["es_sysadmin"] or not row["es_denywriter"]:
        print("\nAVISO: este login NO es de solo lectura. Usa reportes_ro.")


if __name__ == "__main__":
    main()
