"""One-off: create the read-only login `reportes_ro` using the sa credentials in .env.

Usage: uv run scripts/create_readonly_user.py
- Generates a strong password, runs sql/create_readonly_user.sql with it,
  then rewrites .env to use reportes_ro (removing the sa password from disk).
- Aborts if the login already exists.
"""
import os
import re
import secrets
import string
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("FREETDSCONF", str(ROOT / "freetds.conf"))

import pymssql  # noqa: E402
from dotenv import dotenv_values  # noqa: E402

ENV_PATH = ROOT / ".env"
SQL_PATH = ROOT / "sql" / "create_readonly_user.sql"
LOGIN = "reportes_ro"
PLACEHOLDER = "<CONTRASENA_FUERTE>"
PASSWORD_CLASSES = (string.ascii_uppercase, string.ascii_lowercase, string.digits, "-_.")


def generate_password(length: int = 24) -> str:
    alphabet = "".join(PASSWORD_CLASSES)
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if all(any(c in cls for c in pwd) for cls in PASSWORD_CLASSES):
            return pwd


def split_batches(sql: str) -> list[str]:
    batches = re.split(r"^\s*GO\s*$", sql, flags=re.MULTILINE | re.IGNORECASE)
    return [b.strip() for b in batches if b.strip()]


def with_readonly_credentials(env_text: str, password: str) -> str:
    replacements = {"SR_DB_USER": LOGIN, "SR_DB_PASSWORD": password}
    lines = [
        f"{key}={replacements[key]}" if (key := line.split("=", 1)[0].strip()) in replacements else line
        for line in env_text.splitlines()
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    cfg = dotenv_values(ENV_PATH)
    if cfg.get("SR_DB_USER", "").lower() != "sa":
        sys.exit("El .env debe tener SR_DB_USER=sa para crear el login.")

    password = generate_password()
    batches = split_batches(SQL_PATH.read_text(encoding="utf-8").replace(PLACEHOLDER, password))

    try:
        conn = pymssql.connect(
            server=cfg["SR_DB_HOST"], port=cfg["SR_DB_PORT"], database="master",
            user=cfg["SR_DB_USER"], password=cfg["SR_DB_PASSWORD"],
            login_timeout=15, autocommit=True,
        )
    except pymssql.OperationalError as exc:
        sys.exit(f"No se pudo conectar como sa: {exc}")

    with conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM sys.server_principals WHERE name = %s", (LOGIN,))
        if cur.fetchone():
            sys.exit(f"El login {LOGIN} ya existe; no se hizo ningún cambio.")
        for batch in batches:
            cur.execute(batch)
        roles = [row[0] for row in cur.fetchall()]

    print(f"Login {LOGIN} creado. Roles: {', '.join(roles)}")
    try:
        ENV_PATH.write_text(with_readonly_credentials(ENV_PATH.read_text(), password))
    except OSError as exc:
        print(f"No pude actualizar .env ({exc}). Contraseña de {LOGIN}: {password}")
        sys.exit(1)
    print(".env actualizado a reportes_ro (la contraseña de sa ya no está en disco).")


if __name__ == "__main__":
    main()
