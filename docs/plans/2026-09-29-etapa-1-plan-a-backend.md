# Etapa 1 · Plan A — Infraestructura + Backend de asistencia

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Backend FastAPI + Postgres en Docker que lee checadas de SR en vivo, calcula
lo planeado vs lo real (retardos, faltas, cambios sin registrar), permite justificar y
exporta la lista para RH y un Excel.

**Architecture:** `domain/` son funciones puras que reciben empleados, reglas,
excepciones, justificaciones, settings y checadas, y devuelven resultados por
empleado-día. `repos/` persiste la configuración en Postgres y devuelve dataclasses
inmutables del dominio. `sr/` lee SR (real o sintético) detrás del protocolo
`SrSource`. `services/attendance.py` es el único lugar que junta DB + SR + dominio; los
routers de `api/` solo traducen HTTP ↔ servicio. Nada derivado se persiste.

**Tech Stack:** Python 3.12, uv 0.10, FastAPI 0.141, Pydantic 2.13 + pydantic-settings,
SQLAlchemy 2.1, Alembic 1.20, psycopg 3.3, pymssql 2.4 (FreeTDS), openpyxl 3.1,
pytest 9 + pytest-cov, ruff, pyright, Postgres 16, Docker Compose.

**Spec:** [`docs/specs/2026-09-29-etapa-1-asistencia-design.md`](../specs/2026-09-29-etapa-1-asistencia-design.md)
(leerlo completo antes de empezar; este plan argumenta desde él). Reglas de negocio de
fondo en `docs/plan.md` §4 y §6; esquema de SR en `docs/db-map.md`.

## Global Constraints

- **SR es producción, solo lectura:** login `reportes_ro`; solo las consultas de
  `sr/pymssql_source.py`; siempre `WITH (NOLOCK)`; siempre acotadas por fecha; nunca
  DDL/DML; nunca `sa`.
- Nunca seleccionar ni mencionar en SQL `meseros.contraseña` ni `meseros.fotografia`.
- **Repo público:** nada de nombres reales de empleados, IPs, hostnames ni cifras de
  venta en archivos versionados. Tests y demo usan datos sintéticos (`EMPLEADO A`…).
  Nunca versionar `db_examples/`, `docs/private/`, `.env`.
- Código, identificadores y commits en inglés; textos para el usuario (mensajes de
  error de la API, etiquetas del Excel) en español.
- Rango máximo de fechas en cualquier consulta: **93 días inclusivos**.
- Retardo ⇔ `HH:MM` de la checada > hora de entrada del área + tolerancia (se ignoran
  segundos). Defaults: cocina `16:30`, resto `16:40`, tolerancia `10`.
- Semanas ISO lunes–domingo. Zona horaria de negocio `America/Mexico_City`; SR guarda
  datetimes *naive* en hora local.
- Todos los puertos de Docker se publican en `127.0.0.1`.
- Dataclasses del dominio `frozen=True`; los repos nunca devuelven objetos ORM.
- Funciones < 50 líneas, archivos < 400 líneas.
- Todos los comandos de backend se corren **desde `backend/`** salvo que se indique.
- Commits con formato `<type>: <description>` (feat, fix, refactor, docs, test, chore,
  ci) y cerrando con la línea `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Rango que cruza "hoy":** pedir la semana en curso debe consultar SR solo hasta hoy
   y marcar `FUTURE` el resto, sin error. → test en Task 15.
2. **Checadas de un empleado desactivado:** no se pierden en silencio; salen como aviso
   `UNMAPPED_CHECKIN`. → test en Task 5.
3. **Zona horaria de "hoy":** a las 23:30 de Monterrey (05:30 UTC del día siguiente),
   "hoy" sigue siendo el día local. → test en Task 13.
4. **Ids de SR con espacios o ceros** (`' 06 '`, `'006'`) se normalizan a `6`; un id no
   numérico se descarta con log sin tumbar la consulta. → tests en Task 8.
5. **Tabla `setting` vacía** (base creada sin la semilla): la API usa los defaults en
   lugar de fallar. → test en Task 11.

---

## Estructura de archivos

```
backend/
  pyproject.toml, uv.lock, Dockerfile, alembic.ini
  alembic/env.py, alembic/script.py.mako, alembic/versions/0001_initial_schema.py
  src/tabernas/
    __init__.py
    config.py                  Settings (pydantic-settings)
    main.py                    create_app(), local_clock()
    demo.py                    seed_demo_data() para SR_MODE=fake
    domain/
      __init__.py
      types.py                 enums + dataclasses del dominio
      validation.py            DomainValidationError + validadores
      periods.py               rangos, semanas ISO, meses, semana doble
      planning.py              planned_calendar()
      compare.py               compare()
      justify.py               apply_justifications(), default_rh_type()
      rh.py                    rh_type_for(), to_rh_rows()
      summary.py               summarize()
    sr/
      __init__.py              build_sr_source()
      source.py                SrSource, SrEmployee, SrCheckin, SrServerInfo, errores
      pymssql_source.py        PymssqlSource
      fake_source.py           FakeSource, FAKE_EMPLOYEES
      export_reader.py         read_attendance_export() (conciliación)
    db/
      __init__.py
      models.py                Base + filas ORM
      session.py               make_engine(), make_session_factory()
    repos/
      __init__.py
      errors.py                NotFoundError, ConflictError
      common.py                require_employee(), ranges_overlap()
      employees.py             EmployeeRepo
      settings.py              SettingsRepo
      rest_rules.py            RestRuleRepo
      exceptions.py            ExceptionRepo
      justifications.py        JustificationRepo
    services/
      __init__.py
      attendance.py            AttendanceService, AttendanceReport
    export/
      __init__.py
      labels.py                etiquetas en español y colores
      xlsx.py                  build_workbook()
    api/
      __init__.py
      envelope.py              Envelope, ErrorBody, ok()
      errors.py                register_error_handlers()
      deps.py                  SessionDep, SrSourceDep, ClockDep, AppSettingsDep
      routes/__init__.py       ROUTERS
      routes/health.py, employees.py, settings.py, rest_rules.py,
      routes/exceptions.py, justifications.py, attendance.py
  tests/
    __init__.py, conftest.py, support.py
    test_config.py, test_main.py
    domain/  sr/  db/  repos/  api/  export/   (cada uno con __init__.py)
docker/db/init-test-db.sql
docker-compose.yml, .dockerignore, .env.example
scripts/check_connection.py (modificado), seed_demo.py, reconcile_attendance.py
.github/workflows/ci.yml
```

---

### Task 1: Bootstrap del repo y del proyecto backend

**Files:**
- Create: `backend/pyproject.toml`, `backend/src/tabernas/__init__.py`,
  `backend/src/tabernas/config.py`, `backend/tests/__init__.py`,
  `backend/tests/test_config.py`
- Modify: `scripts/check_connection.py:1-5` (docstring de uso), `.gitignore`
- Delete: `main.py`, `pyproject.toml`, `uv.lock`, `.venv/` (raíz)

**Interfaces:**
- Produces: `tabernas.config.Settings` (campos `sr_mode: Literal["live","fake"]`,
  `sr_db_host`, `sr_db_port: int`, `sr_db_name`, `sr_db_user`,
  `sr_db_password: SecretStr`, `database_url: str`, `app_timezone: str`),
  `tabernas.config.get_settings() -> Settings`, `tabernas.config.REPO_ROOT: Path`.

- [ ] **Step 1: Inicializar git y verificar que no se cuelan datos privados**

```bash
cd /Users/didiertm/Documents/Projects/TabernasCerveceras
git init -b main
git status --short --ignored
```
Expected: `.env`, `db_examples/`, `docs/private/`, `.idea/`, `.venv/` aparecen como
ignorados (`!!`), nunca como `??`. Si alguno aparece como `??`, detente y corrige
`.gitignore` antes de seguir.

Agrega al final de `.gitignore`:
```gitignore

# Node / frontend (Plan B)
node_modules/
.next/
```

- [ ] **Step 2: Mover el proyecto Python a `backend/`**

```bash
rm -f main.py pyproject.toml uv.lock
rm -rf .venv
mkdir -p backend/src/tabernas backend/tests
touch backend/src/tabernas/__init__.py backend/tests/__init__.py
```

Crea `backend/pyproject.toml`:
```toml
[project]
name = "tabernas"
version = "0.1.0"
description = "Attendance and sales reports on top of a SoftRestaurant POS database"
requires-python = ">=3.12"
dependencies = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/tabernas"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = "-m 'not sr' --strict-markers"
markers = ["sr: needs the live SoftRestaurant server (local only, never in CI)"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM"]

[tool.pyright]
include = ["src", "tests"]
pythonVersion = "3.12"
typeCheckingMode = "standard"

[tool.coverage.run]
source = ["tabernas"]
branch = true

[tool.coverage.report]
fail_under = 80
show_missing = true
```

Instala dependencias:
```bash
cd backend
uv python pin 3.12
uv add fastapi "uvicorn[standard]" pydantic-settings "sqlalchemy>=2.1" alembic "psycopg[binary]" pymssql openpyxl python-dotenv
uv add --dev pytest pytest-cov httpx ruff pyright
```
Expected: `backend/uv.lock` creado, sin errores.

- [ ] **Step 3: Escribir el test de configuración (falla)**

`backend/tests/test_config.py`:
```python
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


def test_live_mode_accepts_complete_config() -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        sr_mode="live",
        sr_db_host="10.0.0.1",
        sr_db_password="secret",  # type: ignore[arg-type]
    )
    assert settings.sr_db_password.get_secret_value() == "secret"
    assert "secret" not in repr(settings)
```

- [ ] **Step 4: Correr el test y verificar que falla**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'tabernas.config'`

- [ ] **Step 5: Implementar `config.py`**

`backend/src/tabernas/config.py`:
```python
"""Application settings, read from environment variables and the repo's .env file."""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/src/tabernas/config.py -> repo root. Inside Docker this resolves to "/",
# where no .env exists; compose injects the variables instead.
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    sr_mode: Literal["live", "fake"] = "fake"
    sr_db_host: str = ""
    sr_db_port: int = 1433
    sr_db_name: str = "softrestaurant11"
    sr_db_user: str = "reportes_ro"
    sr_db_password: SecretStr = SecretStr("")
    database_url: str = "postgresql+psycopg://tabernas:tabernas@localhost:5432/tabernas"
    app_timezone: str = "America/Mexico_City"

    @model_validator(mode="after")
    def _require_live_credentials(self) -> Self:
        if self.sr_mode != "live":
            return self
        required = {
            "SR_DB_HOST": self.sr_db_host,
            "SR_DB_PASSWORD": self.sr_db_password.get_secret_value(),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"Faltan variables para SR_MODE=live: {', '.join(missing)}")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 6: Correr tests, lint y tipos**

Run: `uv run pytest tests/test_config.py -v && uv run ruff check . && uv run ruff format --check . && uv run pyright`
Expected: 3 passed; ruff sin errores; pyright `0 errors`.

- [ ] **Step 7: Ajustar el script de conexión existente**

En `scripts/check_connection.py`, cambia la línea de uso del docstring:
```python
Usage (from the repo root): uv run --project backend scripts/check_connection.py
```
Run (desde la raíz): `uv run --project backend scripts/check_connection.py`
Expected: imprime `version: 12.0.4100.1`, `es_sysadmin: 0` y ningún `AVISO`.
(Requiere Tailscale activo; si no está, anota que se verificará en Task 2.)

- [ ] **Step 8: Commit**

```bash
cd /Users/didiertm/Documents/Projects/TabernasCerveceras
git add .gitignore CLAUDE.md docs/plan.md docs/db-map.md docs/specs docs/plans \
  freetds.conf .env.example sql scripts backend
git status --short   # confirma: nada de .env, db_examples/, docs/private/
git commit -m "chore: bootstrap backend project with settings

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Docker Compose y spike de conectividad a SR desde el contenedor

Primer riesgo del spec (§4): que el contenedor alcance SR por el Tailscale del host.

**Files:**
- Create: `backend/Dockerfile`, `.dockerignore`, `docker-compose.yml`,
  `docker/db/init-test-db.sql`
- Modify: `.env.example`, `docs/db-map.md` (sección "Acceso desde Docker")

**Interfaces:**
- Produces: servicios compose `db` (Postgres en `127.0.0.1:5432`, usuario/contraseña
  `tabernas`, bases `tabernas` y `tabernas_test`) y `backend` (`127.0.0.1:8000`,
  imagen con `/scripts` y `FREETDSCONF=/etc/freetds/freetds.conf`). El comando del
  backend (`alembic` + `uvicorn --factory tabernas.main:create_app`) solo funcionará
  desde Task 13; en esta tarea el contenedor se usa con `docker compose run`.

- [ ] **Step 1: Escribir los archivos de infraestructura**

`backend/Dockerfile`:
```dockerfile
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.10 /uv /usr/local/bin/uv

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ ./
RUN uv sync --frozen --no-dev
COPY scripts/ /scripts/

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn --factory tabernas.main:create_app --host 0.0.0.0 --port 8000"]
```

`.dockerignore`:
```
**/.venv
**/__pycache__
**/.pytest_cache
**/node_modules
**/.next
.env
.env.*
db_examples
docs/private
.git
.idea
```

`docker/db/init-test-db.sql`:
```sql
-- Runs once, when the db volume is first created. Test suite database.
CREATE DATABASE tabernas_test;
```

`docker-compose.yml`:
```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: tabernas
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-tabernas}
      POSTGRES_DB: tabernas
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./docker/db/init-test-db.sql:/docker-entrypoint-initdb.d/10-test-db.sql:ro
    ports:
      - "127.0.0.1:5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U tabernas -d tabernas"]
      interval: 5s
      timeout: 3s
      retries: 10

  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    env_file:
      - path: .env
        required: false  # CI and the public demo run without a .env
    environment:
      SR_MODE: ${SR_MODE:-live}
      DATABASE_URL: postgresql+psycopg://tabernas:${POSTGRES_PASSWORD:-tabernas}@db:5432/tabernas
      FREETDSCONF: /etc/freetds/freetds.conf
    volumes:
      - ./freetds.conf:/etc/freetds/freetds.conf:ro
    ports:
      - "127.0.0.1:8000:8000"
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"]
      interval: 10s
      timeout: 5s
      retries: 12

volumes:
  pgdata:
```

`.env.example` (reemplaza el contenido completo):
```bash
# live = read the real SoftRestaurant server; fake = synthetic demo data (no SR needed)
SR_MODE=live
# SoftRestaurant SQL Server (via Tailscale). Read-only login only.
SR_DB_HOST=100.x.y.z
SR_DB_PORT=1433
SR_DB_NAME=softrestaurant11
SR_DB_USER=reportes_ro
SR_DB_PASSWORD=
# Local Postgres (docker compose). Only reachable from 127.0.0.1.
POSTGRES_PASSWORD=tabernas
DATABASE_URL=postgresql+psycopg://tabernas:tabernas@localhost:5432/tabernas
APP_TIMEZONE=America/Mexico_City
# Fake login for the frontend (Plan B). NOT security: placeholder until real auth.
FAKE_AUTH_USER=demo
FAKE_AUTH_PASSWORD=demo
BACKEND_URL=http://localhost:8000
```
Agrega a tu `.env` local `SR_MODE=live` (y las demás variables nuevas) sin tocar las
credenciales existentes. Compose usa el `.env` de la raíz tanto para `env_file` como para
interpolar `${SR_MODE}`; en CI/demo basta con exportar `SR_MODE=fake`.

- [ ] **Step 2: Levantar Postgres y verificar las dos bases**

```bash
docker compose up -d db
docker compose exec db psql -U tabernas -d tabernas -c "\l" | grep tabernas
```
Expected: aparecen `tabernas` y `tabernas_test`.

- [ ] **Step 3: Spike — alcanzar SR desde el contenedor**

```bash
docker compose build backend
docker compose run --rm --no-deps backend python /scripts/check_connection.py
```
Expected: igual que en local: `version: 12.0.4100.1`, `login: reportes_ro`,
`es_sysadmin: 0`, sin `AVISO`.

Si falla, diagnostica en este orden y **no sigas con Task 3 sin resolverlo o sin
acordar con el usuario**:
1. TCP: `docker compose run --rm --no-deps backend python -c "import os,socket; socket.create_connection((os.environ['SR_DB_HOST'], int(os.environ['SR_DB_PORT'])), 5); print('tcp ok')"`
   - Falla TCP → Docker no enruta al Tailscale del host. Plan B del spec: sidecar
     `tailscale/tailscale` con `network_mode: service:tailscale` para `backend` (requiere
     un auth key de Tailscale: pedirlo al usuario; nunca versionarlo).
2. TCP ok pero error 20002 → TLS 1.0 rechazado por el OpenSSL de la imagen. Verifica
   que `FREETDSCONF` apunte al archivo montado (`docker compose run --rm --no-deps backend cat /etc/freetds/freetds.conf`);
   si el archivo está y sigue fallando, prueba agregar al servicio
   `OPENSSL_CONF: /etc/ssl/openssl-legacy.cnf` con un archivo que fije
   `MinProtocol = TLSv1` y `CipherString = DEFAULT@SECLEVEL=0`, montado igual que
   `freetds.conf`.

- [ ] **Step 4: Documentar el resultado**

En `docs/db-map.md`, bajo "## Servidor", agrega (con el resultado real, sin IPs):
```markdown
**Acceso desde Docker:** el contenedor `backend` alcanza SR a través del Tailscale del
host (Docker Desktop enruta por la red de macOS); `freetds.conf` se monta en
`/etc/freetds/freetds.conf`. Verificado el 2026-MM-DD con `scripts/check_connection.py`.
```
(Si se usó el sidecar u `OPENSSL_CONF`, describe eso en su lugar.)

- [ ] **Step 5: Commit**

```bash
git add backend/Dockerfile .dockerignore docker-compose.yml docker/ .env.example docs/db-map.md
git commit -m "chore: add docker compose with postgres and SR connectivity check

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Tipos del dominio, periodos y validación

**Files:**
- Create: `backend/src/tabernas/domain/__init__.py` (vacío),
  `backend/src/tabernas/domain/types.py`, `backend/src/tabernas/domain/validation.py`,
  `backend/src/tabernas/domain/periods.py`, `backend/tests/domain/__init__.py` (vacío),
  `backend/tests/domain/test_periods.py`, `backend/tests/domain/test_validation.py`

**Interfaces:**
- Produces (`tabernas.domain.types`): enums `Area {KITCHEN, OTHER}`,
  `RhType {RETARDO, FALTA_INJUSTIFICADA, FALTA_JUSTIFICADA, VACACIONES, INCAPACIDAD, PERMISO, DESCANSO, NO_CAPTURAR}`,
  `ExceptionKind {STORE_CLOSED, PRESENT_NO_CHECKIN, REST_TO_WORK, WORK_TO_ABSENCE, MANUAL_ABSENCE}`,
  `Incident {LATE, ABSENT}`, `Planned {WORK, REST, CLOSED, ABSENCE}`,
  `Outcome {OK, LATE, ABSENT, UNREGISTERED_CHANGE, REST, CLOSED, JUSTIFIED, PENDING, FUTURE}`,
  `WarningCode {NO_REST_RULE, UNMAPPED_CHECKIN, ORPHAN_JUSTIFICATION, MISSING_RH_NAME}`;
  dataclasses frozen `Employee`, `RestRule`, `ScheduleException`, `Justification`,
  `Checkin`, `AttendanceSettings` (+ `.entry_time(area) -> time`), `PlannedDay`,
  `DayResult`, `AttendanceWarning`, `RhRow`; constante `DEFAULT_SETTINGS`.
- Produces (`tabernas.domain.validation`): `DomainValidationError(ValueError)`,
  `ABSENCE_RH_TYPES`, `validate_rest_rule(**)`, `validate_exception(**)`,
  `validate_justification(*, incident, rh_type)`, `parse_hhmm(str) -> time`,
  `format_hhmm(time) -> str`, `validate_tolerance(int)`.
- Produces (`tabernas.domain.periods`): `MAX_RANGE_DAYS = 93`,
  `RangeError(DomainValidationError)`, `validate_range(start, end)`,
  `days(start, end) -> list[date]` (vacía si `end < start`), `week_monday(d)`,
  `iso_week_range(year, week)`, `month_range(year, month)`, `iso_week_key(d) -> "2026-W39"`,
  `month_key(d) -> "2026-09"`, `is_double_rest_week(anchor, day) -> bool`.

- [ ] **Step 1: Escribir `types.py`** (solo datos; se prueba a través de las demás tareas)

`backend/src/tabernas/domain/types.py`:
```python
"""Attendance domain types. Pure data: no database, no HTTP."""

from dataclasses import dataclass
from datetime import date, datetime, time
from enum import StrEnum


class Area(StrEnum):
    KITCHEN = "KITCHEN"
    OTHER = "OTHER"


class RhType(StrEnum):
    """Incident types of the HR tool, plus NO_CAPTURAR (justified, not reported)."""

    RETARDO = "RETARDO"
    FALTA_INJUSTIFICADA = "FALTA_INJUSTIFICADA"
    FALTA_JUSTIFICADA = "FALTA_JUSTIFICADA"
    VACACIONES = "VACACIONES"
    INCAPACIDAD = "INCAPACIDAD"
    PERMISO = "PERMISO"
    DESCANSO = "DESCANSO"
    NO_CAPTURAR = "NO_CAPTURAR"


class ExceptionKind(StrEnum):
    STORE_CLOSED = "STORE_CLOSED"
    PRESENT_NO_CHECKIN = "PRESENT_NO_CHECKIN"
    REST_TO_WORK = "REST_TO_WORK"
    WORK_TO_ABSENCE = "WORK_TO_ABSENCE"
    MANUAL_ABSENCE = "MANUAL_ABSENCE"


class Incident(StrEnum):
    LATE = "LATE"
    ABSENT = "ABSENT"


class Planned(StrEnum):
    WORK = "WORK"
    REST = "REST"
    CLOSED = "CLOSED"
    ABSENCE = "ABSENCE"


class Outcome(StrEnum):
    OK = "OK"
    LATE = "LATE"
    ABSENT = "ABSENT"
    UNREGISTERED_CHANGE = "UNREGISTERED_CHANGE"
    REST = "REST"
    CLOSED = "CLOSED"
    JUSTIFIED = "JUSTIFIED"
    PENDING = "PENDING"
    FUTURE = "FUTURE"


class WarningCode(StrEnum):
    NO_REST_RULE = "NO_REST_RULE"
    UNMAPPED_CHECKIN = "UNMAPPED_CHECKIN"
    ORPHAN_JUSTIFICATION = "ORPHAN_JUSTIFICATION"
    MISSING_RH_NAME = "MISSING_RH_NAME"


@dataclass(frozen=True)
class Employee:
    id: int
    sr_id: int | None
    short_name: str
    rh_name: str | None
    area: Area
    applies_lateness: bool
    tracks_attendance: bool
    active: bool


@dataclass(frozen=True)
class RestRule:
    id: int
    employee_id: int
    fixed_weekday: int  # date.weekday(): 0 = Monday ... 6 = Sunday
    extra_weekday: int
    double_rest_anchor: date  # Monday of a week with double rest
    valid_from: date
    valid_to: date | None


@dataclass(frozen=True)
class ScheduleException:
    id: int
    kind: ExceptionKind
    employee_id: int | None  # None only for STORE_CLOSED
    date_from: date
    date_to: date
    rh_type: RhType | None  # set only for WORK_TO_ABSENCE
    comment: str


@dataclass(frozen=True)
class Justification:
    id: int
    employee_id: int
    day: date
    incident: Incident
    reason: str
    rh_type: RhType


@dataclass(frozen=True)
class Checkin:
    sr_id: int
    at: datetime  # naive, SR local time


@dataclass(frozen=True)
class AttendanceSettings:
    entry_time_kitchen: time
    entry_time_other: time
    tolerance_minutes: int

    def entry_time(self, area: Area) -> time:
        return self.entry_time_kitchen if area == Area.KITCHEN else self.entry_time_other


DEFAULT_SETTINGS = AttendanceSettings(
    entry_time_kitchen=time(16, 30), entry_time_other=time(16, 40), tolerance_minutes=10
)


@dataclass(frozen=True)
class PlannedDay:
    employee_id: int
    day: date
    planned: Planned
    rh_type: RhType | None = None
    present_no_checkin: bool = False
    manual_absence: bool = False
    comment: str = ""


@dataclass(frozen=True)
class DayResult:
    employee_id: int
    day: date
    planned: Planned
    outcome: Outcome
    checkin: datetime | None = None
    minutes_late: int | None = None
    rh_type: RhType | None = None
    justification_id: int | None = None
    comment: str = ""


@dataclass(frozen=True)
class AttendanceWarning:
    code: WarningCode
    employee_id: int | None
    day: date | None
    detail: str


@dataclass(frozen=True)
class RhRow:
    employee_id: int
    name: str
    day: date
    rh_type: RhType
    comment: str
```

- [ ] **Step 2: Escribir los tests de periodos y validación (fallan)**

`backend/tests/domain/test_periods.py`:
```python
from datetime import date

import pytest

from tabernas.domain.periods import (
    MAX_RANGE_DAYS,
    RangeError,
    days,
    is_double_rest_week,
    iso_week_key,
    iso_week_range,
    month_key,
    month_range,
    validate_range,
    week_monday,
)


def test_iso_week_39_of_2026_is_21_to_27_september() -> None:
    assert iso_week_range(2026, 39) == (date(2026, 9, 21), date(2026, 9, 27))


def test_month_range_handles_february() -> None:
    assert month_range(2026, 2) == (date(2026, 2, 1), date(2026, 2, 28))


def test_days_is_inclusive_and_empty_when_reversed() -> None:
    assert days(date(2026, 9, 21), date(2026, 9, 23)) == [
        date(2026, 9, 21),
        date(2026, 9, 22),
        date(2026, 9, 23),
    ]
    assert days(date(2026, 9, 23), date(2026, 9, 21)) == []


def test_week_monday() -> None:
    assert week_monday(date(2026, 9, 27)) == date(2026, 9, 21)
    assert week_monday(date(2026, 9, 21)) == date(2026, 9, 21)


def test_keys_use_iso_year_at_year_boundary() -> None:
    assert iso_week_key(date(2026, 9, 23)) == "2026-W39"
    assert iso_week_key(date(2027, 1, 1)) == "2026-W53"
    assert month_key(date(2027, 1, 1)) == "2027-01"


def test_validate_range_accepts_93_days() -> None:
    validate_range(date(2026, 7, 1), date(2026, 10, 1))  # 93 days inclusive


def test_validate_range_rejects_94_days_and_reversed() -> None:
    assert MAX_RANGE_DAYS == 93
    with pytest.raises(RangeError, match="93"):
        validate_range(date(2026, 7, 1), date(2026, 10, 2))
    with pytest.raises(RangeError, match="anterior"):
        validate_range(date(2026, 9, 2), date(2026, 9, 1))


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2026, 9, 28), True),  # anchor week
        (date(2026, 10, 4), True),  # same week, Sunday
        (date(2026, 10, 5), False),  # next week
        (date(2026, 10, 12), True),  # two weeks later
        (date(2026, 9, 21), False),  # week before the anchor
        (date(2026, 9, 14), True),  # two weeks before the anchor
    ],
)
def test_double_rest_week_alternates_from_anchor(day: date, expected: bool) -> None:
    assert is_double_rest_week(date(2026, 9, 28), day) is expected
```

`backend/tests/domain/test_validation.py`:
```python
from datetime import date, time

import pytest

from tabernas.domain.types import ExceptionKind, Incident, RhType
from tabernas.domain.validation import (
    DomainValidationError,
    format_hhmm,
    parse_hhmm,
    validate_exception,
    validate_justification,
    validate_rest_rule,
    validate_tolerance,
)

MONDAY = date(2026, 9, 28)


def _rule(**overrides: object) -> None:
    fields: dict[str, object] = {
        "fixed_weekday": 1,
        "extra_weekday": 0,
        "double_rest_anchor": MONDAY,
        "valid_from": date(2026, 1, 1),
        "valid_to": None,
    }
    validate_rest_rule(**{**fields, **overrides})  # type: ignore[arg-type]


def test_valid_rest_rule_passes() -> None:
    _rule()


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"fixed_weekday": 7}, "entre 0"),
        ({"extra_weekday": -1}, "entre 0"),
        ({"extra_weekday": 1}, "distintos"),
        ({"double_rest_anchor": date(2026, 9, 29)}, "lunes"),
        ({"valid_to": date(2025, 12, 31)}, "vigencia"),
    ],
)
def test_invalid_rest_rules(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(DomainValidationError, match=message):
        _rule(**overrides)


def _exception(**overrides: object) -> None:
    fields: dict[str, object] = {
        "kind": ExceptionKind.WORK_TO_ABSENCE,
        "employee_id": 1,
        "rh_type": RhType.VACACIONES,
        "date_from": MONDAY,
        "date_to": MONDAY,
    }
    validate_exception(**{**fields, **overrides})  # type: ignore[arg-type]


def test_valid_exceptions_pass() -> None:
    _exception()
    _exception(kind=ExceptionKind.STORE_CLOSED, employee_id=None, rh_type=None)
    _exception(kind=ExceptionKind.REST_TO_WORK, rh_type=None)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"date_to": date(2026, 9, 27)}, "anterior"),
        ({"kind": ExceptionKind.STORE_CLOSED, "rh_type": None}, "aplica a todos"),
        ({"employee_id": None}, "aplica a todos"),
        ({"rh_type": None}, "tipo de ausencia"),
        ({"rh_type": RhType.RETARDO}, "tipo de ausencia"),
        ({"kind": ExceptionKind.REST_TO_WORK}, "Solo las ausencias"),
    ],
)
def test_invalid_exceptions(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(DomainValidationError, match=message):
        _exception(**overrides)


def test_justification_rh_types_depend_on_incident() -> None:
    validate_justification(incident=Incident.LATE, rh_type=RhType.NO_CAPTURAR)
    validate_justification(incident=Incident.ABSENT, rh_type=RhType.INCAPACIDAD)
    with pytest.raises(DomainValidationError):
        validate_justification(incident=Incident.LATE, rh_type=RhType.VACACIONES)
    with pytest.raises(DomainValidationError):
        validate_justification(incident=Incident.ABSENT, rh_type=RhType.RETARDO)


def test_hhmm_round_trip_and_errors() -> None:
    assert parse_hhmm("16:40") == time(16, 40)
    assert format_hhmm(time(9, 5)) == "09:05"
    for bad in ("25:00", "16:60", "1640", "4:40", "aa:bb"):
        with pytest.raises(DomainValidationError, match="HH:MM"):
            parse_hhmm(bad)


def test_tolerance_bounds() -> None:
    validate_tolerance(0)
    validate_tolerance(60)
    with pytest.raises(DomainValidationError):
        validate_tolerance(61)
    with pytest.raises(DomainValidationError):
        validate_tolerance(-1)
```

- [ ] **Step 3: Correr y verificar que fallan**

Run: `uv run pytest tests/domain -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'tabernas.domain.periods'`

- [ ] **Step 4: Implementar `validation.py` y `periods.py`**

`backend/src/tabernas/domain/validation.py`:
```python
"""Validation rules shared by repositories and the API. Raise DomainValidationError."""

from datetime import date, time

from tabernas.domain.types import ExceptionKind, Incident, RhType


class DomainValidationError(ValueError):
    """Input the user can fix. The API maps it to 422 with this message."""


ABSENCE_RH_TYPES = frozenset(
    {
        RhType.FALTA_JUSTIFICADA,
        RhType.VACACIONES,
        RhType.INCAPACIDAD,
        RhType.PERMISO,
        RhType.DESCANSO,
    }
)
JUSTIFICATION_RH_TYPES = {
    Incident.LATE: frozenset({RhType.NO_CAPTURAR, RhType.RETARDO}),
    Incident.ABSENT: ABSENCE_RH_TYPES | {RhType.NO_CAPTURAR},
}
MAX_TOLERANCE_MINUTES = 60


def validate_rest_rule(
    *,
    fixed_weekday: int,
    extra_weekday: int,
    double_rest_anchor: date,
    valid_from: date,
    valid_to: date | None,
) -> None:
    for label, value in (("día fijo", fixed_weekday), ("día extra", extra_weekday)):
        if not 0 <= value <= 6:
            raise DomainValidationError(f"El {label} debe estar entre 0 (lunes) y 6 (domingo)")
    if fixed_weekday == extra_weekday:
        raise DomainValidationError("El día fijo y el día extra deben ser distintos")
    if double_rest_anchor.weekday() != 0:
        raise DomainValidationError("La semana de descanso doble se indica con un lunes")
    if valid_to is not None and valid_to < valid_from:
        raise DomainValidationError("La vigencia termina antes de empezar")


def validate_exception(
    *,
    kind: ExceptionKind,
    employee_id: int | None,
    rh_type: RhType | None,
    date_from: date,
    date_to: date,
) -> None:
    if date_to < date_from:
        raise DomainValidationError("La fecha final es anterior a la inicial")
    if (kind == ExceptionKind.STORE_CLOSED) != (employee_id is None):
        raise DomainValidationError(
            "El cierre del local aplica a todos; las demás excepciones requieren empleado"
        )
    if kind == ExceptionKind.WORK_TO_ABSENCE:
        if rh_type not in ABSENCE_RH_TYPES:
            raise DomainValidationError("Indica el tipo de ausencia para RH")
    elif rh_type is not None:
        raise DomainValidationError("Solo las ausencias llevan tipo de RH")


def validate_justification(*, incident: Incident, rh_type: RhType) -> None:
    if rh_type not in JUSTIFICATION_RH_TYPES[incident]:
        raise DomainValidationError("Tipo de RH no válido para esta incidencia")


def parse_hhmm(value: str) -> time:
    error = DomainValidationError(f"Hora inválida: {value!r} (usa HH:MM)")
    if len(value) != 5 or value[2] != ":":
        raise error
    try:
        return time(int(value[:2]), int(value[3:]))
    except ValueError as exc:
        raise error from exc


def format_hhmm(value: time) -> str:
    return value.strftime("%H:%M")


def validate_tolerance(minutes: int) -> None:
    if not 0 <= minutes <= MAX_TOLERANCE_MINUTES:
        raise DomainValidationError(
            f"La tolerancia debe estar entre 0 y {MAX_TOLERANCE_MINUTES} minutos"
        )
```

`backend/src/tabernas/domain/periods.py`:
```python
"""Date ranges, ISO weeks, months and the double-rest week parity."""

import calendar
from datetime import date, timedelta

from tabernas.domain.validation import DomainValidationError

MAX_RANGE_DAYS = 93


class RangeError(DomainValidationError):
    """Invalid or too-large date range."""


def validate_range(start: date, end: date) -> None:
    if end < start:
        raise RangeError("La fecha final es anterior a la inicial")
    if (end - start).days + 1 > MAX_RANGE_DAYS:
        raise RangeError(f"El rango máximo es de {MAX_RANGE_DAYS} días")


def days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def week_monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def iso_week_range(year: int, week: int) -> tuple[date, date]:
    monday = date.fromisocalendar(year, week, 1)
    return monday, monday + timedelta(days=6)


def month_range(year: int, month: int) -> tuple[date, date]:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def iso_week_key(day: date) -> str:
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def month_key(day: date) -> str:
    return f"{day.year}-{day.month:02d}"


def is_double_rest_week(anchor: date, day: date) -> bool:
    """True when `day` falls in a week with double rest, counting every 2 weeks from `anchor`."""
    weeks_from_anchor = (week_monday(day) - anchor).days // 7
    return weeks_from_anchor % 2 == 0
```

- [ ] **Step 5: Correr y verificar que pasan**

Run: `uv run pytest tests/domain -v && uv run ruff check . && uv run pyright`
Expected: todos PASS; sin errores de lint ni tipos.

- [ ] **Step 6: Commit**

```bash
git add backend/src/tabernas/domain backend/tests/domain
git commit -m "feat: add attendance domain types, periods and validation

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Calendario planeado (`planning.py`)

**Files:**
- Create: `backend/src/tabernas/domain/planning.py`,
  `backend/tests/domain/factories.py`, `backend/tests/domain/test_planning.py`

**Interfaces:**
- Consumes: tipos de Task 3, `periods.days`, `periods.validate_range`,
  `periods.is_double_rest_week`.
- Produces: `planned_calendar(employees: Sequence[Employee], rules: Sequence[RestRule], exceptions: Sequence[ScheduleException], start: date, end: date) -> tuple[list[PlannedDay], list[AttendanceWarning]]`
  (solo empleados activos, ordenado por `employee_id` y luego día);
  `covers(exception, day) -> bool`; `rule_for(rules, day) -> RestRule | None`.
- Produces (tests): `tests/domain/factories.py` con `employee()`, `rule()`,
  `exception()`, `planned()`, `WEEK_39`.

- [ ] **Step 1: Escribir las factories de prueba**

`backend/tests/domain/factories.py`:
```python
"""Synthetic domain objects for tests. Reference week: 2026-W39 (Mon 21 – Sun 27 Sep)."""

from datetime import date

from tabernas.domain.types import (
    Area,
    Employee,
    ExceptionKind,
    Planned,
    PlannedDay,
    RestRule,
    RhType,
    ScheduleException,
)

WEEK_39 = (date(2026, 9, 21), date(2026, 9, 27))
ANCHOR = date(2026, 9, 28)  # Monday, double-rest week


def employee(
    id: int = 1,
    *,
    area: Area = Area.OTHER,
    applies_lateness: bool = True,
    tracks_attendance: bool = True,
    active: bool = True,
    rh_name: str | None = "EMPLEADO RH",
) -> Employee:
    return Employee(
        id=id,
        sr_id=id + 100,
        short_name=f"E{id}",
        rh_name=rh_name,
        area=area,
        applies_lateness=applies_lateness,
        tracks_attendance=tracks_attendance,
        active=active,
    )


def rule(
    employee_id: int = 1,
    *,
    fixed: int = 1,  # Tuesday
    extra: int = 0,  # Monday
    anchor: date = ANCHOR,
    valid_from: date = date(2026, 1, 1),
    valid_to: date | None = None,
    id: int = 1,
) -> RestRule:
    return RestRule(
        id=id,
        employee_id=employee_id,
        fixed_weekday=fixed,
        extra_weekday=extra,
        double_rest_anchor=anchor,
        valid_from=valid_from,
        valid_to=valid_to,
    )


def exception(
    kind: ExceptionKind,
    day: date,
    *,
    until: date | None = None,
    employee_id: int | None = 1,
    rh_type: RhType | None = None,
    comment: str = "",
    id: int = 1,
) -> ScheduleException:
    return ScheduleException(
        id=id,
        kind=kind,
        employee_id=None if kind == ExceptionKind.STORE_CLOSED else employee_id,
        date_from=day,
        date_to=until or day,
        rh_type=rh_type,
        comment=comment,
    )


def planned(
    day: date,
    kind: Planned = Planned.WORK,
    *,
    employee_id: int = 1,
    rh_type: RhType | None = None,
    present_no_checkin: bool = False,
    manual_absence: bool = False,
) -> PlannedDay:
    return PlannedDay(
        employee_id=employee_id,
        day=day,
        planned=kind,
        rh_type=rh_type,
        present_no_checkin=present_no_checkin,
        manual_absence=manual_absence,
    )
```

- [ ] **Step 2: Escribir los tests (fallan)**

`backend/tests/domain/test_planning.py`:
```python
from datetime import date

from tabernas.domain.planning import planned_calendar
from tabernas.domain.types import (
    AttendanceWarning,
    ExceptionKind,
    Planned,
    PlannedDay,
    RhType,
    WarningCode,
)
from tests.domain.factories import WEEK_39, employee, exception, rule


def by_day(planned: list[PlannedDay], employee_id: int = 1) -> dict[date, PlannedDay]:
    return {p.day: p for p in planned if p.employee_id == employee_id}


def test_fixed_weekday_is_rest_every_week() -> None:
    planned, _ = planned_calendar([employee()], [rule()], [], date(2026, 9, 21), date(2026, 10, 4))
    days = by_day(planned)
    assert days[date(2026, 9, 22)].planned == Planned.REST
    assert days[date(2026, 9, 29)].planned == Planned.REST


def test_extra_weekday_is_rest_only_on_double_weeks() -> None:
    planned, _ = planned_calendar([employee()], [rule()], [], date(2026, 9, 21), date(2026, 10, 12))
    days = by_day(planned)
    assert days[date(2026, 9, 21)].planned == Planned.WORK
    assert days[date(2026, 9, 28)].planned == Planned.REST
    assert days[date(2026, 10, 5)].planned == Planned.WORK
    assert days[date(2026, 10, 12)].planned == Planned.REST


def test_two_weeks_have_eleven_working_days() -> None:
    planned, _ = planned_calendar([employee()], [rule()], [], date(2026, 9, 28), date(2026, 10, 11))
    assert sum(p.planned == Planned.WORK for p in planned) == 11


def test_rule_validity_switches_rules() -> None:
    rules = [
        rule(fixed=1, valid_to=date(2026, 9, 27), id=1),
        rule(fixed=3, valid_from=date(2026, 9, 28), id=2),
    ]
    planned, warnings = planned_calendar(
        [employee()], rules, [], date(2026, 9, 21), date(2026, 10, 4)
    )
    days = by_day(planned)
    assert days[date(2026, 9, 22)].planned == Planned.REST  # Tue under rule 1
    assert days[date(2026, 9, 29)].planned == Planned.WORK  # Tue under rule 2
    assert days[date(2026, 10, 1)].planned == Planned.REST  # Thu under rule 2
    assert warnings == []


def test_missing_rule_plans_work_and_warns_once() -> None:
    planned, warnings = planned_calendar([employee()], [], [], *WEEK_39)
    assert {p.planned for p in planned} == {Planned.WORK}
    assert warnings == [
        AttendanceWarning(
            WarningCode.NO_REST_RULE, 1, date(2026, 9, 21), "Sin regla de descanso vigente"
        )
    ]


def test_store_closed_applies_to_everyone_and_wins() -> None:
    closed_day = date(2026, 9, 24)
    exceptions = [
        exception(ExceptionKind.STORE_CLOSED, closed_day, comment="Ley Seca", id=1),
        exception(ExceptionKind.REST_TO_WORK, closed_day, employee_id=1, id=2),
    ]
    planned, _ = planned_calendar(
        [employee(1), employee(2)], [rule(1), rule(2, id=2)], exceptions, *WEEK_39
    )
    closed = [p for p in planned if p.day == closed_day]
    assert [(p.employee_id, p.planned, p.comment) for p in closed] == [
        (1, Planned.CLOSED, "Ley Seca"),
        (2, Planned.CLOSED, "Ley Seca"),
    ]


def test_closure_range_covers_every_day() -> None:
    closure = exception(ExceptionKind.STORE_CLOSED, date(2026, 12, 24), until=date(2026, 12, 25))
    planned, _ = planned_calendar(
        [employee()], [rule()], [closure], date(2026, 12, 21), date(2026, 12, 27)
    )
    days = by_day(planned)
    assert days[date(2026, 12, 24)].planned == Planned.CLOSED
    assert days[date(2026, 12, 25)].planned == Planned.CLOSED
    assert days[date(2026, 12, 26)].planned == Planned.WORK


def test_work_to_absence_is_planned_absence_with_rh_type() -> None:
    vacation = exception(
        ExceptionKind.WORK_TO_ABSENCE,
        date(2026, 9, 23),
        until=date(2026, 9, 25),
        rh_type=RhType.VACACIONES,
        comment="Vacaciones",
    )
    planned, _ = planned_calendar([employee()], [rule()], [vacation], *WEEK_39)
    absent = [p for p in planned if p.planned == Planned.ABSENCE]
    assert [p.day.day for p in absent] == [23, 24, 25]
    assert {(p.rh_type, p.comment) for p in absent} == {(RhType.VACACIONES, "Vacaciones")}


def test_manual_absence_plans_work_flagged() -> None:
    manual = exception(ExceptionKind.MANUAL_ABSENCE, date(2026, 9, 23))
    planned, _ = planned_calendar([employee()], [rule()], [manual], *WEEK_39)
    day = by_day(planned)[date(2026, 9, 23)]
    assert (day.planned, day.manual_absence) == (Planned.WORK, True)


def test_rest_to_work_turns_rest_day_into_work() -> None:
    swap = exception(ExceptionKind.REST_TO_WORK, date(2026, 9, 22))
    planned, _ = planned_calendar([employee()], [rule()], [swap], *WEEK_39)
    assert by_day(planned)[date(2026, 9, 22)].planned == Planned.WORK


def test_present_no_checkin_only_flags_the_day() -> None:
    flag = exception(ExceptionKind.PRESENT_NO_CHECKIN, date(2026, 9, 23))
    planned, _ = planned_calendar([employee()], [rule()], [flag], *WEEK_39)
    day = by_day(planned)[date(2026, 9, 23)]
    assert (day.planned, day.present_no_checkin) == (Planned.WORK, True)


def test_other_employees_exceptions_do_not_apply() -> None:
    swap = exception(ExceptionKind.REST_TO_WORK, date(2026, 9, 22), employee_id=2)
    planned, _ = planned_calendar([employee(1)], [rule(1)], [swap], *WEEK_39)
    assert by_day(planned)[date(2026, 9, 22)].planned == Planned.REST


def test_inactive_employees_are_not_planned() -> None:
    planned, _ = planned_calendar([employee(active=False)], [rule()], [], *WEEK_39)
    assert planned == []


def test_output_is_sorted_by_employee_then_day() -> None:
    planned, _ = planned_calendar(
        [employee(2), employee(1)], [rule(1), rule(2, id=2)], [], *WEEK_39
    )
    assert [(p.employee_id, p.day.day) for p in planned][:2] == [(1, 21), (1, 22)]
    assert planned[7].employee_id == 2
```

- [ ] **Step 3: Correr y verificar que fallan**

Run: `uv run pytest tests/domain/test_planning.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'tabernas.domain.planning'`

- [ ] **Step 4: Implementar `planning.py`**

`backend/src/tabernas/domain/planning.py`:
```python
"""Planned calendar: what each employee should do each day, before looking at check-ins."""

from collections.abc import Sequence
from datetime import date

from tabernas.domain.periods import days, is_double_rest_week, validate_range
from tabernas.domain.types import (
    AttendanceWarning,
    Employee,
    ExceptionKind,
    Planned,
    PlannedDay,
    RestRule,
    ScheduleException,
    WarningCode,
)


def covers(exception: ScheduleException, day: date) -> bool:
    return exception.date_from <= day <= exception.date_to


def rule_for(rules: Sequence[RestRule], day: date) -> RestRule | None:
    return next(
        (
            r
            for r in rules
            if r.valid_from <= day and (r.valid_to is None or day <= r.valid_to)
        ),
        None,
    )


def planned_by_rule(rule: RestRule | None, day: date) -> Planned:
    if rule is None:
        return Planned.WORK
    weekday = day.weekday()
    if weekday == rule.fixed_weekday:
        return Planned.REST
    if weekday == rule.extra_weekday and is_double_rest_week(rule.double_rest_anchor, day):
        return Planned.REST
    return Planned.WORK


def planned_calendar(
    employees: Sequence[Employee],
    rules: Sequence[RestRule],
    exceptions: Sequence[ScheduleException],
    start: date,
    end: date,
) -> tuple[list[PlannedDay], list[AttendanceWarning]]:
    validate_range(start, end)
    period = days(start, end)
    closures = [e for e in exceptions if e.kind == ExceptionKind.STORE_CLOSED]
    active = sorted((e for e in employees if e.active), key=lambda e: e.id)
    planned: list[PlannedDay] = []
    warnings: list[AttendanceWarning] = []
    for employee in active:
        own_rules = [r for r in rules if r.employee_id == employee.id]
        own_exceptions = [e for e in exceptions if e.employee_id == employee.id]
        planned.extend(
            _plan_day(employee.id, day, own_rules, own_exceptions, closures) for day in period
        )
        missing = next((day for day in period if rule_for(own_rules, day) is None), None)
        if missing is not None:
            warnings.append(
                AttendanceWarning(
                    WarningCode.NO_REST_RULE, employee.id, missing, "Sin regla de descanso vigente"
                )
            )
    return planned, warnings


def _find(exceptions: Sequence[ScheduleException], kind: ExceptionKind) -> ScheduleException | None:
    return next((e for e in exceptions if e.kind == kind), None)


def _plan_day(
    employee_id: int,
    day: date,
    rules: Sequence[RestRule],
    exceptions: Sequence[ScheduleException],
    closures: Sequence[ScheduleException],
) -> PlannedDay:
    closure = next((c for c in closures if covers(c, day)), None)
    if closure is not None:
        return PlannedDay(employee_id, day, Planned.CLOSED, comment=closure.comment)
    covering = [e for e in exceptions if covers(e, day)]
    present = _find(covering, ExceptionKind.PRESENT_NO_CHECKIN) is not None
    absence = _find(covering, ExceptionKind.WORK_TO_ABSENCE)
    if absence is not None:
        return PlannedDay(
            employee_id, day, Planned.ABSENCE, rh_type=absence.rh_type, comment=absence.comment
        )
    manual = _find(covering, ExceptionKind.MANUAL_ABSENCE)
    if manual is not None:
        return PlannedDay(
            employee_id, day, Planned.WORK, manual_absence=True, comment=manual.comment
        )
    extra_work = _find(covering, ExceptionKind.REST_TO_WORK)
    if extra_work is not None:
        return PlannedDay(
            employee_id, day, Planned.WORK, present_no_checkin=present, comment=extra_work.comment
        )
    return PlannedDay(
        employee_id, day, planned_by_rule(rule_for(rules, day), day), present_no_checkin=present
    )
```

- [ ] **Step 5: Correr y verificar que pasan**

Run: `uv run pytest tests/domain -v && uv run ruff check . && uv run pyright`
Expected: todos PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/tabernas/domain/planning.py backend/tests/domain
git commit -m "feat: compute planned attendance calendar from rest rules and exceptions

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Planeado vs real (`compare.py`)

**Files:**
- Create: `backend/src/tabernas/domain/compare.py`, `backend/tests/domain/test_compare.py`

**Interfaces:**
- Consumes: `PlannedDay`, `Employee`, `Checkin`, `AttendanceSettings` (Task 3);
  factories `employee()`, `planned()` (Task 4).
- Produces: `compare(planned: Sequence[PlannedDay], employees: Sequence[Employee], checkins: Sequence[Checkin], settings: AttendanceSettings, today: date, now: datetime) -> tuple[list[DayResult], list[AttendanceWarning]]`
  (un `DayResult` por `PlannedDay`, mismo orden); `first_checkins(checkins) -> dict[tuple[int, date], datetime]`;
  `truncate_to_minute(datetime) -> datetime`.

- [ ] **Step 1: Escribir los tests (fallan)**

`backend/tests/domain/test_compare.py`:
```python
from dataclasses import replace
from datetime import date, datetime, time

from tabernas.domain.compare import compare
from tabernas.domain.types import (
    DEFAULT_SETTINGS,
    Area,
    Checkin,
    DayResult,
    Employee,
    Outcome,
    Planned,
    PlannedDay,
    RhType,
    WarningCode,
)
from tests.domain.factories import employee, planned

DAY = date(2026, 9, 23)  # Wednesday
EVENING = datetime(2026, 9, 27, 20, 0)


def at(hour: int, minute: int, second: int = 0, day: date = DAY) -> datetime:
    return datetime.combine(day, time(hour, minute, second))


def checkin(hour: int, minute: int, second: int = 0, *, sr_id: int = 101, day: date = DAY) -> Checkin:
    return Checkin(sr_id=sr_id, at=at(hour, minute, second, day))


def run_one(
    day_plan: PlannedDay,
    checkins: list[Checkin],
    emp: Employee | None = None,
    *,
    today: date = date(2026, 9, 27),
    now: datetime = EVENING,
) -> DayResult:
    results, _ = compare(
        [day_plan], [emp or employee()], checkins, DEFAULT_SETTINGS, today, now
    )
    return results[0]


def test_on_time_until_last_second_of_tolerance() -> None:
    result = run_one(planned(DAY), [checkin(16, 50, 59)])
    assert (result.outcome, result.checkin) == (Outcome.OK, at(16, 50, 59))


def test_late_from_next_minute_counts_minutes_from_entry_time() -> None:
    result = run_one(planned(DAY), [checkin(16, 51, 0)])
    assert (result.outcome, result.minutes_late) == (Outcome.LATE, 11)


def test_kitchen_uses_its_own_entry_time() -> None:
    cook = employee(area=Area.KITCHEN)
    assert run_one(planned(DAY), [checkin(16, 40, 59)], cook).outcome == Outcome.OK
    late = run_one(planned(DAY), [checkin(16, 41, 0)], cook)
    assert (late.outcome, late.minutes_late) == (Outcome.LATE, 11)


def test_first_checkin_of_the_day_counts() -> None:
    result = run_one(planned(DAY), [checkin(16, 55), checkin(16, 35)])
    assert (result.outcome, result.checkin) == (Outcome.OK, at(16, 35))


def test_checkin_on_another_day_does_not_count() -> None:
    result = run_one(planned(DAY), [checkin(16, 35, day=date(2026, 9, 24))])
    assert result.outcome == Outcome.ABSENT


def test_employee_without_lateness_is_never_late() -> None:
    result = run_one(planned(DAY), [checkin(18, 0)], employee(applies_lateness=False))
    assert result.outcome == Outcome.OK


def test_missing_checkin_is_absent() -> None:
    assert run_one(planned(DAY), []).outcome == Outcome.ABSENT


def test_present_without_checkin_is_ok() -> None:
    assert run_one(planned(DAY, present_no_checkin=True), []).outcome == Outcome.OK


def test_today_before_limit_is_pending() -> None:
    result = run_one(planned(DAY), [], today=DAY, now=at(16, 50, 30))
    assert result.outcome == Outcome.PENDING


def test_today_after_limit_without_checkin_is_absent() -> None:
    result = run_one(planned(DAY), [], today=DAY, now=at(16, 51))
    assert result.outcome == Outcome.ABSENT


def test_today_with_checkin_is_evaluated() -> None:
    result = run_one(planned(DAY), [checkin(16, 45)], today=DAY, now=at(16, 46))
    assert result.outcome == Outcome.OK


def test_future_days() -> None:
    result = run_one(planned(DAY), [], today=date(2026, 9, 22))
    assert result.outcome == Outcome.FUTURE


def test_rest_day_with_checkin_is_unregistered_change() -> None:
    result = run_one(planned(DAY, Planned.REST), [checkin(16, 45)])
    assert (result.outcome, result.checkin) == (Outcome.UNREGISTERED_CHANGE, at(16, 45))


def test_rest_day_without_checkin_is_rest() -> None:
    assert run_one(planned(DAY, Planned.REST), []).outcome == Outcome.REST


def test_closed_day_ignores_checkin() -> None:
    assert run_one(planned(DAY, Planned.CLOSED), [checkin(18, 0)]).outcome == Outcome.CLOSED


def test_planned_absence_is_justified_with_rh_type() -> None:
    result = run_one(planned(DAY, Planned.ABSENCE, rh_type=RhType.INCAPACIDAD), [])
    assert (result.outcome, result.rh_type) == (Outcome.JUSTIFIED, RhType.INCAPACIDAD)


def test_manual_absence_is_absent_even_with_checkin() -> None:
    result = run_one(planned(DAY, manual_absence=True), [checkin(16, 30)])
    assert result.outcome == Outcome.ABSENT


def test_untracked_employee_counts_as_present() -> None:
    manager = replace(employee(tracks_attendance=False, applies_lateness=False), sr_id=None)
    assert run_one(planned(DAY), [], manager).outcome == Outcome.OK


def test_unmapped_checkins_are_reported() -> None:
    _, warnings = compare(
        [planned(DAY)], [employee()], [checkin(16, 40, sr_id=999)], DEFAULT_SETTINGS,
        date(2026, 9, 27), EVENING,
    )
    assert [(w.code, w.day) for w in warnings] == [(WarningCode.UNMAPPED_CHECKIN, DAY)]
    assert "999" in warnings[0].detail


def test_checkins_of_deactivated_employee_are_reported_not_lost() -> None:
    # Review Focus #2: employee 2 is inactive, so it has no planned days.
    inactive = employee(2, active=False)
    _, warnings = compare(
        [planned(DAY)], [employee(1), inactive], [checkin(16, 40, sr_id=102)],
        DEFAULT_SETTINGS, date(2026, 9, 27), EVENING,
    )
    assert [w.code for w in warnings] == [WarningCode.UNMAPPED_CHECKIN]
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `uv run pytest tests/domain/test_compare.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'tabernas.domain.compare'`

- [ ] **Step 3: Implementar `compare.py`**

`backend/src/tabernas/domain/compare.py`:
```python
"""Planned vs actual: turns planned days + SR check-ins into per-day outcomes."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import date, datetime, time, timedelta

from tabernas.domain.types import (
    AttendanceSettings,
    AttendanceWarning,
    Checkin,
    DayResult,
    Employee,
    Outcome,
    Planned,
    PlannedDay,
    WarningCode,
)

FirstCheckins = Mapping[tuple[int, date], datetime]


def first_checkins(checkins: Sequence[Checkin]) -> dict[tuple[int, date], datetime]:
    """Earliest check-in per (sr_id, calendar day)."""
    firsts: dict[tuple[int, date], datetime] = {}
    for item in sorted(checkins, key=lambda c: c.at, reverse=True):
        firsts[(item.sr_id, item.at.date())] = item.at
    return firsts


def truncate_to_minute(value: datetime) -> datetime:
    return value.replace(second=0, microsecond=0)


def entry_limit(day: date, entry: time, tolerance_minutes: int) -> datetime:
    return datetime.combine(day, entry) + timedelta(minutes=tolerance_minutes)


def compare(
    planned: Sequence[PlannedDay],
    employees: Sequence[Employee],
    checkins: Sequence[Checkin],
    settings: AttendanceSettings,
    today: date,
    now: datetime,
) -> tuple[list[DayResult], list[AttendanceWarning]]:
    by_id = {e.id: e for e in employees}
    firsts = first_checkins(checkins)
    results = [
        _evaluate(day_plan, by_id[day_plan.employee_id], firsts, settings, today, now)
        for day_plan in planned
    ]
    return results, _unmapped_warnings(firsts, planned, by_id)


def _evaluate(
    day_plan: PlannedDay,
    employee: Employee,
    firsts: FirstCheckins,
    settings: AttendanceSettings,
    today: date,
    now: datetime,
) -> DayResult:
    checkin = None if employee.sr_id is None else firsts.get((employee.sr_id, day_plan.day))
    base = DayResult(
        employee_id=day_plan.employee_id,
        day=day_plan.day,
        planned=day_plan.planned,
        outcome=Outcome.OK,
        checkin=checkin,
        rh_type=day_plan.rh_type,
        comment=day_plan.comment,
    )
    if day_plan.day > today:
        return replace(base, outcome=Outcome.FUTURE)
    if day_plan.planned == Planned.CLOSED:
        return replace(base, outcome=Outcome.CLOSED)
    if day_plan.planned == Planned.ABSENCE:
        return replace(base, outcome=Outcome.JUSTIFIED)
    if day_plan.planned == Planned.REST:
        outcome = Outcome.UNREGISTERED_CHANGE if checkin else Outcome.REST
        return replace(base, outcome=outcome)
    return _evaluate_work(base, day_plan, employee, settings, today, now)


def _evaluate_work(
    base: DayResult,
    day_plan: PlannedDay,
    employee: Employee,
    settings: AttendanceSettings,
    today: date,
    now: datetime,
) -> DayResult:
    if day_plan.manual_absence:
        return replace(base, outcome=Outcome.ABSENT)
    if not employee.tracks_attendance:
        return base
    entry = settings.entry_time(employee.area)
    limit = entry_limit(day_plan.day, entry, settings.tolerance_minutes)
    if base.checkin is not None:
        arrived = truncate_to_minute(base.checkin)
        if employee.applies_lateness and arrived > limit:
            minutes = int((arrived - datetime.combine(day_plan.day, entry)).total_seconds() // 60)
            return replace(base, outcome=Outcome.LATE, minutes_late=minutes)
        return base
    if day_plan.present_no_checkin:
        return base
    if day_plan.day == today and truncate_to_minute(now) <= limit:
        return replace(base, outcome=Outcome.PENDING)
    return replace(base, outcome=Outcome.ABSENT)


def _unmapped_warnings(
    firsts: FirstCheckins, planned: Sequence[PlannedDay], by_id: Mapping[int, Employee]
) -> list[AttendanceWarning]:
    mapped = {by_id[p.employee_id].sr_id for p in planned} - {None}
    return [
        AttendanceWarning(
            WarningCode.UNMAPPED_CHECKIN,
            None,
            day,
            f"Checada del id SR {sr_id} sin empleado activo configurado",
        )
        for sr_id, day in sorted(firsts)
        if sr_id not in mapped
    ]
```

- [ ] **Step 4: Correr y verificar que pasan**

Run: `uv run pytest tests/domain -v && uv run ruff check . && uv run pyright`
Expected: todos PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tabernas/domain/compare.py backend/tests/domain/test_compare.py
git commit -m "feat: compare planned days against SR check-ins

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Justificaciones y filas para RH (`justify.py`, `rh.py`)

**Files:**
- Create: `backend/src/tabernas/domain/justify.py`, `backend/src/tabernas/domain/rh.py`,
  `backend/tests/domain/test_justify.py`, `backend/tests/domain/test_rh.py`
- Modify: `backend/tests/domain/factories.py` (agrega `result()` y `justification()`)

**Interfaces:**
- Consumes: `DayResult`, `Justification`, `Employee`, `RhRow` (Task 3).
- Produces: `default_rh_type(incident: Incident) -> RhType`;
  `apply_justifications(results: Sequence[DayResult], justifications: Sequence[Justification]) -> tuple[list[DayResult], list[AttendanceWarning]]`;
  `rh_type_for(result: DayResult) -> RhType | None`;
  `to_rh_rows(results: Sequence[DayResult], employees: Sequence[Employee]) -> tuple[list[RhRow], list[AttendanceWarning]]`
  (sin `NO_CAPTURAR`; ordenado por nombre y fecha).

- [ ] **Step 1: Agregar factories**

Al final de `backend/tests/domain/factories.py` (y agrega `DayResult`, `Incident`,
`Justification`, `Outcome` al import de `tabernas.domain.types`):
```python
DAY = date(2026, 9, 23)

_PLANNED_FOR_OUTCOME = {
    Outcome.REST: Planned.REST,
    Outcome.UNREGISTERED_CHANGE: Planned.REST,
    Outcome.CLOSED: Planned.CLOSED,
    Outcome.JUSTIFIED: Planned.ABSENCE,
}


def result(
    outcome: Outcome,
    *,
    employee_id: int = 1,
    day: date = DAY,
    rh_type: RhType | None = None,
    justification_id: int | None = None,
    comment: str = "",
) -> DayResult:
    return DayResult(
        employee_id=employee_id,
        day=day,
        planned=_PLANNED_FOR_OUTCOME.get(outcome, Planned.WORK),
        outcome=outcome,
        rh_type=rh_type,
        justification_id=justification_id,
        comment=comment,
    )


def justification(
    incident: Incident,
    rh_type: RhType,
    *,
    employee_id: int = 1,
    day: date = DAY,
    id: int = 7,
    reason: str = "Cita médica",
) -> Justification:
    return Justification(
        id=id, employee_id=employee_id, day=day, incident=incident, reason=reason, rh_type=rh_type
    )
```

- [ ] **Step 2: Escribir los tests (fallan)**

`backend/tests/domain/test_justify.py`:
```python
from datetime import date

from tabernas.domain.justify import apply_justifications, default_rh_type
from tabernas.domain.types import Incident, Outcome, RhType, WarningCode
from tests.domain.factories import DAY, justification, result


def test_default_rh_types() -> None:
    assert default_rh_type(Incident.LATE) == RhType.NO_CAPTURAR
    assert default_rh_type(Incident.ABSENT) == RhType.FALTA_JUSTIFICADA


def test_justification_marks_matching_incident() -> None:
    results, warnings = apply_justifications(
        [result(Outcome.ABSENT)], [justification(Incident.ABSENT, RhType.INCAPACIDAD)]
    )
    assert (results[0].justification_id, results[0].rh_type, results[0].comment) == (
        7,
        RhType.INCAPACIDAD,
        "Cita médica",
    )
    assert results[0].outcome == Outcome.ABSENT
    assert warnings == []


def test_justification_needs_same_incident_type() -> None:
    original = result(Outcome.ABSENT)
    results, warnings = apply_justifications(
        [original], [justification(Incident.LATE, RhType.NO_CAPTURAR)]
    )
    assert results == [original]
    assert [(w.code, w.employee_id, w.day) for w in warnings] == [
        (WarningCode.ORPHAN_JUSTIFICATION, 1, DAY)
    ]


def test_justification_for_other_employee_or_day_does_not_apply() -> None:
    original = result(Outcome.LATE)
    others = [
        justification(Incident.LATE, RhType.NO_CAPTURAR, employee_id=2, id=1),
        justification(Incident.LATE, RhType.NO_CAPTURAR, day=date(2026, 9, 24), id=2),
    ]
    results, warnings = apply_justifications([original], others)
    assert results == [original]
    assert len(warnings) == 2
```

`backend/tests/domain/test_rh.py`:
```python
from datetime import date

import pytest

from tabernas.domain.rh import rh_type_for, to_rh_rows
from tabernas.domain.types import DayResult, Outcome, RhType, WarningCode
from tests.domain.factories import employee, result


@pytest.mark.parametrize(
    ("day_result", "expected"),
    [
        (result(Outcome.LATE), RhType.RETARDO),
        (result(Outcome.LATE, justification_id=7, rh_type=RhType.NO_CAPTURAR), RhType.NO_CAPTURAR),
        (result(Outcome.ABSENT), RhType.FALTA_INJUSTIFICADA),
        (result(Outcome.ABSENT, justification_id=7, rh_type=RhType.VACACIONES), RhType.VACACIONES),
        (result(Outcome.JUSTIFIED, rh_type=RhType.DESCANSO), RhType.DESCANSO),
        (result(Outcome.OK), None),
        (result(Outcome.REST), None),
        (result(Outcome.CLOSED), None),
        (result(Outcome.UNREGISTERED_CHANGE), None),
        (result(Outcome.PENDING), None),
        (result(Outcome.FUTURE), None),
    ],
)
def test_rh_type_for(day_result: DayResult, expected: RhType | None) -> None:
    assert rh_type_for(day_result) == expected


def test_rows_skip_no_capturar_and_sort_by_name_then_day() -> None:
    employees = [employee(1, rh_name="ZAPATA"), employee(2, rh_name="ALVAREZ")]
    results = [
        result(Outcome.LATE, employee_id=1, day=date(2026, 9, 24)),
        result(Outcome.ABSENT, employee_id=1, day=date(2026, 9, 23)),
        result(Outcome.LATE, employee_id=2, justification_id=7, rh_type=RhType.NO_CAPTURAR),
        result(Outcome.ABSENT, employee_id=2, day=date(2026, 9, 25), comment="Sin aviso"),
        result(Outcome.OK, employee_id=2),
    ]
    rows, warnings = to_rh_rows(results, employees)
    assert [(r.name, r.day.day, r.rh_type, r.comment) for r in rows] == [
        ("ALVAREZ", 25, RhType.FALTA_INJUSTIFICADA, "Sin aviso"),
        ("ZAPATA", 23, RhType.FALTA_INJUSTIFICADA, ""),
        ("ZAPATA", 24, RhType.RETARDO, ""),
    ]
    assert warnings == []


def test_missing_rh_name_falls_back_to_short_name_and_warns_once() -> None:
    results = [
        result(Outcome.ABSENT, day=date(2026, 9, 23)),
        result(Outcome.ABSENT, day=date(2026, 9, 24)),
    ]
    rows, warnings = to_rh_rows(results, [employee(1, rh_name=None)])
    assert {r.name for r in rows} == {"E1"}
    assert [(w.code, w.employee_id) for w in warnings] == [(WarningCode.MISSING_RH_NAME, 1)]
```

- [ ] **Step 3: Correr y verificar que fallan**

Run: `uv run pytest tests/domain/test_justify.py tests/domain/test_rh.py -v`
Expected: FAIL con `ModuleNotFoundError`

- [ ] **Step 4: Implementar `justify.py` y `rh.py`**

`backend/src/tabernas/domain/justify.py`:
```python
"""Attach the manager's justifications to late/absent results."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import date

from tabernas.domain.types import (
    AttendanceWarning,
    DayResult,
    Incident,
    Justification,
    Outcome,
    RhType,
    WarningCode,
)

_DEFAULT_RH_TYPE = {Incident.LATE: RhType.NO_CAPTURAR, Incident.ABSENT: RhType.FALTA_JUSTIFICADA}
_INCIDENT_BY_OUTCOME = {Outcome.LATE: Incident.LATE, Outcome.ABSENT: Incident.ABSENT}

Key = tuple[int, date, Incident]


def default_rh_type(incident: Incident) -> RhType:
    return _DEFAULT_RH_TYPE[incident]


def apply_justifications(
    results: Sequence[DayResult], justifications: Sequence[Justification]
) -> tuple[list[DayResult], list[AttendanceWarning]]:
    by_key = {(j.employee_id, j.day, j.incident): j for j in justifications}
    applied = [_apply(r, by_key) for r in results]
    incidents = {
        (r.employee_id, r.day, _INCIDENT_BY_OUTCOME[r.outcome])
        for r in results
        if r.outcome in _INCIDENT_BY_OUTCOME
    }
    warnings = [
        AttendanceWarning(
            WarningCode.ORPHAN_JUSTIFICATION,
            j.employee_id,
            j.day,
            f"Justificación de {j.incident} sin incidencia correspondiente",
        )
        for j in justifications
        if (j.employee_id, j.day, j.incident) not in incidents
    ]
    return applied, warnings


def _apply(result: DayResult, by_key: Mapping[Key, Justification]) -> DayResult:
    incident = _INCIDENT_BY_OUTCOME.get(result.outcome)
    if incident is None:
        return result
    found = by_key.get((result.employee_id, result.day, incident))
    if found is None:
        return result
    return replace(result, justification_id=found.id, rh_type=found.rh_type, comment=found.reason)
```

`backend/src/tabernas/domain/rh.py`:
```python
"""Rows ready to be typed into the HR tool."""

from collections.abc import Sequence

from tabernas.domain.types import (
    AttendanceWarning,
    DayResult,
    Employee,
    Outcome,
    RhRow,
    RhType,
    WarningCode,
)


def rh_type_for(result: DayResult) -> RhType | None:
    justified = result.justification_id is not None
    if result.outcome == Outcome.LATE:
        return result.rh_type if justified else RhType.RETARDO
    if result.outcome == Outcome.ABSENT:
        return result.rh_type if justified else RhType.FALTA_INJUSTIFICADA
    if result.outcome == Outcome.JUSTIFIED:
        return result.rh_type
    return None


def to_rh_rows(
    results: Sequence[DayResult], employees: Sequence[Employee]
) -> tuple[list[RhRow], list[AttendanceWarning]]:
    by_id = {e.id: e for e in employees}
    typed = [(r, rh_type_for(r)) for r in results]
    rows = [
        RhRow(
            employee_id=r.employee_id,
            name=by_id[r.employee_id].rh_name or by_id[r.employee_id].short_name,
            day=r.day,
            rh_type=rh_type,
            comment=r.comment,
        )
        for r, rh_type in typed
        if rh_type is not None and rh_type != RhType.NO_CAPTURAR
    ]
    missing = sorted({row.employee_id for row in rows if not by_id[row.employee_id].rh_name})
    warnings = [
        AttendanceWarning(
            WarningCode.MISSING_RH_NAME,
            employee_id,
            None,
            f"{by_id[employee_id].short_name} no tiene nombre en RH",
        )
        for employee_id in missing
    ]
    return sorted(rows, key=lambda row: (row.name, row.day)), warnings
```

- [ ] **Step 5: Correr y verificar que pasan**

Run: `uv run pytest tests/domain -v && uv run ruff check . && uv run pyright`
Expected: todos PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/tabernas/domain backend/tests/domain
git commit -m "feat: apply justifications and build HR incident rows

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Resumen semanal y mensual (`summary.py`)

**Files:**
- Create: `backend/src/tabernas/domain/summary.py`, `backend/tests/domain/test_summary.py`

**Interfaces:**
- Consumes: `DayResult` (Task 3), `iso_week_key`, `month_key` (Task 3), factory `result()` (Task 6).
- Produces: `Grouping(StrEnum) {WEEK="week", MONTH="month"}`;
  `EmployeeSummary(employee_id, period, worked, late, late_justified, absent, absent_justified, justified_by_type: tuple[tuple[RhType, int], ...], unresolved)`;
  `summarize(results: Sequence[DayResult], grouping: Grouping) -> list[EmployeeSummary]`
  (ordenado por `employee_id`, luego `period`).

- [ ] **Step 1: Escribir los tests (fallan)**

`backend/tests/domain/test_summary.py`:
```python
from datetime import date

from tabernas.domain.summary import EmployeeSummary, Grouping, summarize
from tabernas.domain.types import Outcome, RhType
from tests.domain.factories import result


def d(day: int, month: int = 9) -> date:
    return date(2026, month, day)


def test_weekly_summary_counts_every_outcome() -> None:
    results = [
        result(Outcome.OK, day=d(21)),
        result(Outcome.LATE, day=d(22)),
        result(Outcome.LATE, day=d(23), justification_id=1, rh_type=RhType.NO_CAPTURAR),
        result(Outcome.ABSENT, day=d(24)),
        result(Outcome.ABSENT, day=d(25), justification_id=2, rh_type=RhType.PERMISO),
        result(Outcome.JUSTIFIED, day=d(26), rh_type=RhType.VACACIONES),
        result(Outcome.UNREGISTERED_CHANGE, day=d(27)),
        result(Outcome.REST, employee_id=2, day=d(21)),
    ]
    assert summarize(results, Grouping.WEEK) == [
        EmployeeSummary(
            employee_id=1,
            period="2026-W39",
            worked=3,
            late=2,
            late_justified=1,
            absent=2,
            absent_justified=1,
            justified_by_type=((RhType.VACACIONES, 1),),
            unresolved=1,
        ),
        EmployeeSummary(2, "2026-W39", 0, 0, 0, 0, 0, (), 0),
    ]


def test_monthly_grouping_splits_at_month_boundary() -> None:
    results = [result(Outcome.OK, day=d(30)), result(Outcome.OK, day=d(1, 10))]
    assert [s.period for s in summarize(results, Grouping.MONTH)] == ["2026-09", "2026-10"]


def test_week_grouping_crosses_month_boundary() -> None:
    results = [result(Outcome.OK, day=d(30)), result(Outcome.OK, day=d(1, 10))]
    summaries = summarize(results, Grouping.WEEK)
    assert [(s.period, s.worked) for s in summaries] == [("2026-W40", 2)]
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `uv run pytest tests/domain/test_summary.py -v`
Expected: FAIL con `ModuleNotFoundError`

- [ ] **Step 3: Implementar `summary.py`**

`backend/src/tabernas/domain/summary.py`:
```python
"""Per-employee totals by ISO week or month."""

from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from tabernas.domain.periods import iso_week_key, month_key
from tabernas.domain.types import DayResult, Outcome, RhType


class Grouping(StrEnum):
    WEEK = "week"
    MONTH = "month"


@dataclass(frozen=True)
class EmployeeSummary:
    employee_id: int
    period: str
    worked: int
    late: int
    late_justified: int
    absent: int
    absent_justified: int
    justified_by_type: tuple[tuple[RhType, int], ...]
    unresolved: int


def period_key(day: date, grouping: Grouping) -> str:
    return iso_week_key(day) if grouping == Grouping.WEEK else month_key(day)


def summarize(results: Sequence[DayResult], grouping: Grouping) -> list[EmployeeSummary]:
    groups: defaultdict[tuple[int, str], list[DayResult]] = defaultdict(list)
    for r in results:
        groups[(r.employee_id, period_key(r.day, grouping))].append(r)
    return [
        _summarize_group(employee_id, period, group)
        for (employee_id, period), group in sorted(groups.items())
    ]


def _summarize_group(
    employee_id: int, period: str, results: Sequence[DayResult]
) -> EmployeeSummary:
    late = [r for r in results if r.outcome == Outcome.LATE]
    absent = [r for r in results if r.outcome == Outcome.ABSENT]
    by_type = Counter(
        r.rh_type for r in results if r.outcome == Outcome.JUSTIFIED and r.rh_type is not None
    )
    return EmployeeSummary(
        employee_id=employee_id,
        period=period,
        worked=sum(r.outcome in (Outcome.OK, Outcome.LATE) for r in results),
        late=len(late),
        late_justified=sum(r.justification_id is not None for r in late),
        absent=len(absent),
        absent_justified=sum(r.justification_id is not None for r in absent),
        justified_by_type=tuple(sorted(by_type.items())),
        unresolved=sum(r.outcome == Outcome.UNREGISTERED_CHANGE for r in results),
    )
```

- [ ] **Step 4: Correr y verificar cobertura del dominio**

Run: `uv run pytest tests/domain --cov=tabernas.domain --cov-report=term-missing --cov-fail-under=95`
Expected: todos PASS; cobertura de `tabernas/domain` ≥ 95%. Si alguna línea queda sin
cubrir, agrega el test que falta antes de seguir.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tabernas/domain/summary.py backend/tests/domain/test_summary.py
git commit -m "feat: summarize attendance by ISO week and month

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Conector SR real (`sr/source.py`, `sr/pymssql_source.py`)

**Files:**
- Create: `backend/src/tabernas/sr/__init__.py` (vacío por ahora),
  `backend/src/tabernas/sr/source.py`, `backend/src/tabernas/sr/pymssql_source.py`,
  `backend/tests/sr/__init__.py`, `backend/tests/sr/test_pymssql_source.py`,
  `backend/tests/sr/test_live.py`

**Interfaces:**
- Consumes: `Settings`, `REPO_ROOT` (Task 1); `validate_range`, `RangeError` (Task 3).
- Produces (`tabernas.sr.source`): `SrEmployee(sr_id: int, name: str, kind: int | None, visible: bool)`,
  `SrCheckin(sr_id: int, at: datetime)`,
  `SrServerInfo(server, instance, version, edition, database, login: str; is_datareader, is_denywriter, is_sysadmin: bool)` con propiedad `read_only`,
  `SrSource` (Protocol: `fetch_employees()`, `fetch_checkins(start, end)` inclusivo, `server_info()`),
  `SrUnavailableError`, `SrNotReadOnlyError`, `parse_sr_id(raw) -> int | None`.
- Produces (`tabernas.sr.pymssql_source`): `PymssqlSource(connect: Callable[[], Any])`,
  `PymssqlSource.from_settings(settings)`, constantes `CHECKINS_SQL`, `EMPLOYEES_SQL`,
  `SERVER_INFO_SQL`, `ALL_SQL`.

- [ ] **Step 1: Escribir `source.py`** (modelos + protocolo; se prueba con los tests del paso 2)

`backend/src/tabernas/sr/source.py`:
```python
"""Read-only access to SoftRestaurant: models, errors and the SrSource protocol."""

import logging
from datetime import date, datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class SrUnavailableError(RuntimeError):
    """SR could not be reached or a query failed. Message is safe to show to users."""


class SrNotReadOnlyError(RuntimeError):
    """The configured SR login can write. The app refuses to use it."""


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class SrEmployee(_Frozen):
    sr_id: int
    name: str
    kind: int | None
    visible: bool


class SrCheckin(_Frozen):
    sr_id: int
    at: datetime  # naive, SR local time


class SrServerInfo(_Frozen):
    server: str
    instance: str
    version: str
    edition: str
    database: str
    login: str
    is_datareader: bool
    is_denywriter: bool
    is_sysadmin: bool

    @property
    def read_only(self) -> bool:
        return self.is_denywriter and not self.is_sysadmin


class SrSource(Protocol):
    def fetch_employees(self) -> list[SrEmployee]: ...

    def fetch_checkins(self, start: date, end: date) -> list[SrCheckin]:
        """Check-ins with start <= at.date() <= end. Range limited to 93 days."""
        ...

    def server_info(self) -> SrServerInfo: ...


def parse_sr_id(raw: object) -> int | None:
    """SR stores employee ids as zero-padded varchar ('06'); SR's own reports show 6."""
    try:
        return int(str(raw).strip())
    except ValueError:
        logger.warning("Ignoring SR row with non-numeric employee id %r", raw)
        return None
```

- [ ] **Step 2: Escribir los tests (fallan)**

`backend/tests/sr/test_pymssql_source.py`:
```python
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
    assert source.fetch_employees() == [SrEmployee(sr_id=6, name="EMPLEADO A", kind=1, visible=True)]
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
```

`backend/tests/sr/test_live.py`:
```python
"""Against the real SR server. Local only: `uv run pytest -m sr tests/sr/test_live.py`."""

from datetime import date

import pytest

from tabernas.config import Settings
from tabernas.sr.pymssql_source import PymssqlSource

pytestmark = pytest.mark.sr


@pytest.fixture
def live_source() -> PymssqlSource:
    return PymssqlSource.from_settings(Settings(sr_mode="live"))


def test_login_is_read_only(live_source: PymssqlSource) -> None:
    assert live_source.server_info().read_only


def test_reads_one_week_of_checkins(live_source: PymssqlSource) -> None:
    checkins = live_source.fetch_checkins(date(2026, 8, 3), date(2026, 8, 9))
    assert checkins
    assert all(date(2026, 8, 3) <= c.at.date() <= date(2026, 8, 9) for c in checkins)


def test_reads_employees(live_source: PymssqlSource) -> None:
    assert live_source.fetch_employees()
```

- [ ] **Step 3: Correr y verificar que fallan**

Run: `uv run pytest tests/sr -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'tabernas.sr.pymssql_source'`
(los tests `sr` quedan deseleccionados).

- [ ] **Step 4: Implementar `pymssql_source.py`**

`backend/src/tabernas/sr/pymssql_source.py`:
```python
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
```

- [ ] **Step 5: Correr los tests unitarios**

Run: `uv run pytest tests/sr -v && uv run ruff check . && uv run pyright`
Expected: todos PASS (los 3 de `test_live.py` aparecen como deselected).

- [ ] **Step 6: Correr los tests contra SR real (local, con Tailscale)**

Run: `uv run pytest -m sr tests/sr/test_live.py -v`
Expected: 3 passed. Si falla por conexión, revisa Tailscale y `.env`; no sigas
marcando la tarea como hecha hasta que pasen.

- [ ] **Step 7: Commit**

```bash
git add backend/src/tabernas/sr backend/tests/sr
git commit -m "feat: add read-only SoftRestaurant connector over pymssql

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: SR sintético (`FakeSource`) y selección por `SR_MODE`

**Files:**
- Create: `backend/src/tabernas/sr/fake_source.py`, `backend/tests/sr/test_fake_source.py`,
  `backend/tests/sr/test_factory.py`
- Modify: `backend/src/tabernas/sr/__init__.py`

**Interfaces:**
- Consumes: `SrSource`, modelos (Task 8); `days`, `validate_range`,
  `is_double_rest_week` (Task 3); `DEFAULT_SETTINGS`, `Area` (Task 3).
- Produces: `FakeEmployee(sr_id, name, area, fixed_rest, extra_rest, checks_in=True)`,
  `FAKE_EMPLOYEES` (id 100 = gerente sin checadas; 101–106 = `EMPLEADO A`…`F`),
  `FAKE_DOUBLE_REST_ANCHOR = date(2026, 9, 28)`, `is_fake_rest_day(employee, day)`,
  `FakeSource(today: Callable[[], date] = date.today)`;
  `tabernas.sr.build_sr_source(settings: Settings) -> SrSource`.

- [ ] **Step 1: Escribir los tests (fallan)**

`backend/tests/sr/test_fake_source.py`:
```python
from datetime import date, datetime, timedelta

import pytest

from tabernas.domain.periods import RangeError, days
from tabernas.domain.types import DEFAULT_SETTINGS
from tabernas.sr.fake_source import FAKE_EMPLOYEES, FakeSource, is_fake_rest_day

TODAY = date(2026, 9, 27)
START = date(2026, 7, 1)


def source() -> FakeSource:
    return FakeSource(today=lambda: TODAY)


def test_is_deterministic() -> None:
    first = source().fetch_checkins(START, TODAY)
    assert first
    assert first == source().fetch_checkins(START, TODAY)


def test_never_returns_future_checkins() -> None:
    checkins = source().fetch_checkins(date(2026, 9, 21), date(2026, 10, 4))
    assert max(c.at.date() for c in checkins) <= TODAY
    assert source().fetch_checkins(date(2026, 10, 1), date(2026, 10, 7)) == []


def test_manager_never_checks_in() -> None:
    assert all(c.sr_id != 100 for c in source().fetch_checkins(START, TODAY))


def test_produces_late_absent_and_rest_day_checkins() -> None:
    checkins = source().fetch_checkins(START, TODAY)
    by_key = {(c.sr_id, c.at.date()): c.at for c in checkins}
    checking = [e for e in FAKE_EMPLOYEES if e.checks_in]
    late = absent = on_rest = 0
    for employee in checking:
        entry = DEFAULT_SETTINGS.entry_time(employee.area)
        for day in days(START, TODAY):
            at = by_key.get((employee.sr_id, day))
            if is_fake_rest_day(employee, day):
                on_rest += at is not None
            elif at is None:
                absent += 1
            elif at.replace(second=0) > datetime.combine(day, entry) + timedelta(minutes=10):
                late += 1
    assert late > 0 and absent > 0 and on_rest > 0


def test_range_is_validated() -> None:
    with pytest.raises(RangeError):
        source().fetch_checkins(date(2026, 1, 1), date(2026, 6, 1))


def test_employees_include_manager_and_six_checking_employees() -> None:
    employees = source().fetch_employees()
    assert [e.sr_id for e in employees] == [100, 101, 102, 103, 104, 105, 106]
    assert all(e.name.isupper() for e in employees)


def test_server_info_is_read_only() -> None:
    assert source().server_info().read_only
```

`backend/tests/sr/test_factory.py`:
```python
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
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `uv run pytest tests/sr/test_fake_source.py tests/sr/test_factory.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'tabernas.sr.fake_source'`

- [ ] **Step 3: Implementar `fake_source.py` y `build_sr_source`**

`backend/src/tabernas/sr/fake_source.py`:
```python
"""Synthetic SoftRestaurant for demos, E2E and CI. Deterministic; contains no real data."""

import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from tabernas.domain.periods import days, is_double_rest_week, validate_range
from tabernas.domain.types import DEFAULT_SETTINGS, Area
from tabernas.sr.source import SrCheckin, SrEmployee, SrServerInfo


@dataclass(frozen=True)
class FakeEmployee:
    sr_id: int
    name: str
    area: Area
    fixed_rest: int
    extra_rest: int
    checks_in: bool = True


FAKE_DOUBLE_REST_ANCHOR = date(2026, 9, 28)
FAKE_EMPLOYEES = (
    FakeEmployee(100, "GERENTE DEMO", Area.OTHER, fixed_rest=0, extra_rest=6, checks_in=False),
    FakeEmployee(101, "EMPLEADO A", Area.KITCHEN, fixed_rest=1, extra_rest=0),
    FakeEmployee(102, "EMPLEADO B", Area.KITCHEN, fixed_rest=6, extra_rest=0),
    FakeEmployee(103, "EMPLEADO C", Area.OTHER, fixed_rest=1, extra_rest=0),
    FakeEmployee(104, "EMPLEADO D", Area.OTHER, fixed_rest=6, extra_rest=0),
    FakeEmployee(105, "EMPLEADO E", Area.OTHER, fixed_rest=0, extra_rest=2),
    FakeEmployee(106, "EMPLEADO F", Area.OTHER, fixed_rest=1, extra_rest=0),
)
ABSENCE_RATE = 0.05
LATE_RATE = 0.15
REST_CHECKIN_RATE = 0.05


class FakeSource:
    def __init__(self, today: Callable[[], date] = date.today) -> None:
        self._today = today

    def fetch_employees(self) -> list[SrEmployee]:
        return [
            SrEmployee(sr_id=e.sr_id, name=e.name, kind=1, visible=True) for e in FAKE_EMPLOYEES
        ]

    def fetch_checkins(self, start: date, end: date) -> list[SrCheckin]:
        validate_range(start, end)
        last = min(end, self._today())
        return [
            checkin
            for day in days(start, last)
            for employee in FAKE_EMPLOYEES
            if employee.checks_in
            for checkin in _checkins_for(employee, day)
        ]

    def server_info(self) -> SrServerInfo:
        return SrServerInfo(
            server="FAKE",
            instance="FAKE",
            version="fake",
            edition="fake",
            database="fake",
            login="fake",
            is_datareader=True,
            is_denywriter=True,
            is_sysadmin=False,
        )


def is_fake_rest_day(employee: FakeEmployee, day: date) -> bool:
    weekday = day.weekday()
    if weekday == employee.fixed_rest:
        return True
    return weekday == employee.extra_rest and is_double_rest_week(FAKE_DOUBLE_REST_ANCHOR, day)


def _checkins_for(employee: FakeEmployee, day: date) -> list[SrCheckin]:
    rng = random.Random(f"{employee.sr_id}:{day.isoformat()}")
    roll = rng.random()
    if is_fake_rest_day(employee, day):
        if roll < REST_CHECKIN_RATE:
            return [_checkin(employee, day, rng.randint(-10, 5), rng)]
        return []
    if roll < ABSENCE_RATE:
        return []
    late = roll < ABSENCE_RATE + LATE_RATE
    offset = rng.randint(11, 40) if late else rng.randint(-25, 9)
    return [_checkin(employee, day, offset, rng)]


def _checkin(
    employee: FakeEmployee, day: date, offset_minutes: int, rng: random.Random
) -> SrCheckin:
    entry = datetime.combine(day, DEFAULT_SETTINGS.entry_time(employee.area))
    return SrCheckin(
        sr_id=employee.sr_id,
        at=entry + timedelta(minutes=offset_minutes, seconds=rng.randint(0, 59)),
    )
```

`backend/src/tabernas/sr/__init__.py`:
```python
"""SoftRestaurant access. Pick the implementation with SR_MODE."""

from tabernas.config import Settings
from tabernas.sr.fake_source import FakeSource
from tabernas.sr.pymssql_source import PymssqlSource
from tabernas.sr.source import SrSource


def build_sr_source(settings: Settings) -> SrSource:
    if settings.sr_mode == "fake":
        return FakeSource()
    return PymssqlSource.from_settings(settings)
```

- [ ] **Step 4: Correr y verificar que pasan**

Run: `uv run pytest tests/sr -v && uv run ruff check . && uv run pyright`
Expected: todos PASS. (`test_produces_late_absent_and_rest_day_checkins` es
determinista: si falla, ajusta las tasas, nunca la semilla por test.)

- [ ] **Step 5: Commit**

```bash
git add backend/src/tabernas/sr backend/tests/sr
git commit -m "feat: add deterministic synthetic SR source for demo and CI

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Modelo de datos en Postgres + Alembic

**Files:**
- Create: `backend/src/tabernas/db/__init__.py` (vacío), `backend/src/tabernas/db/models.py`,
  `backend/src/tabernas/db/session.py`, `backend/alembic.ini`, `backend/alembic/env.py`,
  `backend/alembic/script.py.mako`, `backend/alembic/versions/0001_initial_schema.py`,
  `backend/tests/support.py`, `backend/tests/conftest.py`, `backend/tests/db/__init__.py`,
  `backend/tests/db/test_migrations.py`, `backend/tests/db/test_models.py`

**Interfaces:**
- Consumes: enums de Task 3; `Settings.database_url` (Task 1).
- Produces: `tabernas.db.models.Base`, `EmployeeRow`, `RestRuleRow`,
  `ScheduleExceptionRow`, `JustificationRow`, `SettingRow` (tablas `employee`,
  `rest_rule`, `schedule_exception`, `justification`, `setting`);
  `tabernas.db.session.make_engine(url) -> Engine`,
  `make_session_factory(engine) -> sessionmaker[Session]`;
  fixtures de pytest `engine` (sesión), `session_factory`, `session`;
  `tests.support.TEST_DATABASE_URL`, `tests.support.reset_schema(engine)`.

- [ ] **Step 1: Escribir modelos y sesión**

`backend/src/tabernas/db/models.py`:
```python
"""SQLAlchemy tables for our own configuration. Derived attendance is never stored."""

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    MetaData,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from tabernas.domain.types import Area, ExceptionKind, Incident, RhType

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _enum(enum_cls: type) -> SAEnum:
    return SAEnum(enum_cls, native_enum=False, length=32, validate_strings=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EmployeeRow(TimestampMixin, Base):
    __tablename__ = "employee"

    id: Mapped[int] = mapped_column(primary_key=True)
    sr_id: Mapped[int | None] = mapped_column(unique=True)
    short_name: Mapped[str] = mapped_column(String(80))
    rh_name: Mapped[str | None] = mapped_column(String(160))
    area: Mapped[Area] = mapped_column(_enum(Area))
    applies_lateness: Mapped[bool]
    tracks_attendance: Mapped[bool]
    active: Mapped[bool] = mapped_column(default=True)


class RestRuleRow(TimestampMixin, Base):
    __tablename__ = "rest_rule"
    __table_args__ = (
        CheckConstraint("fixed_weekday BETWEEN 0 AND 6", name="fixed_weekday_range"),
        CheckConstraint("extra_weekday BETWEEN 0 AND 6", name="extra_weekday_range"),
        CheckConstraint("fixed_weekday <> extra_weekday", name="distinct_weekdays"),
        CheckConstraint("valid_to IS NULL OR valid_from <= valid_to", name="valid_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employee.id", ondelete="CASCADE"), index=True
    )
    fixed_weekday: Mapped[int] = mapped_column(SmallInteger)
    extra_weekday: Mapped[int] = mapped_column(SmallInteger)
    double_rest_anchor: Mapped[date]
    valid_from: Mapped[date]
    valid_to: Mapped[date | None]


class ScheduleExceptionRow(TimestampMixin, Base):
    __tablename__ = "schedule_exception"
    __table_args__ = (
        CheckConstraint("date_from <= date_to", name="date_range"),
        CheckConstraint(
            "(employee_id IS NULL) = (kind = 'STORE_CLOSED')", name="closure_has_no_employee"
        ),
        CheckConstraint(
            "(rh_type IS NOT NULL) = (kind = 'WORK_TO_ABSENCE')", name="absence_has_rh_type"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[ExceptionKind] = mapped_column(_enum(ExceptionKind))
    employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employee.id", ondelete="CASCADE"), index=True
    )
    date_from: Mapped[date]
    date_to: Mapped[date]
    rh_type: Mapped[RhType | None] = mapped_column(_enum(RhType))
    comment: Mapped[str] = mapped_column(String(500), default="")


class JustificationRow(TimestampMixin, Base):
    __tablename__ = "justification"
    __table_args__ = (UniqueConstraint("employee_id", "day", "incident"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employee.id", ondelete="CASCADE"), index=True
    )
    day: Mapped[date]
    incident: Mapped[Incident] = mapped_column(_enum(Incident))
    reason: Mapped[str] = mapped_column(String(500))
    rh_type: Mapped[RhType] = mapped_column(_enum(RhType))


class SettingRow(TimestampMixin, Base):
    __tablename__ = "setting"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(64))
```

`backend/src/tabernas/db/session.py`:
```python
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def make_engine(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)
```

- [ ] **Step 2: Escribir soporte y fixtures de pruebas**

`backend/tests/support.py`:
```python
import os

from sqlalchemy import Engine, text

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://tabernas:tabernas@localhost:5432/tabernas_test"
)


def reset_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
```

`backend/tests/conftest.py`:
```python
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, make_url, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from tabernas.db.models import Base
from tabernas.db.session import make_engine, make_session_factory
from tests.support import TEST_DATABASE_URL, reset_schema


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    database = make_url(TEST_DATABASE_URL).database or ""
    if not database.endswith("_test"):
        pytest.fail(f"TEST_DATABASE_URL debe apuntar a una base *_test, no a {database!r}")
    eng = make_engine(TEST_DATABASE_URL)
    try:
        eng.connect().close()
    except OperationalError:
        pytest.fail("Postgres de pruebas no disponible: corre `docker compose up -d db`")
    reset_schema(eng)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> Iterator[sessionmaker[Session]]:
    yield make_session_factory(engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE employee, rest_rule, schedule_exception, justification, setting "
                "RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture
def session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as s:
        yield s
        s.rollback()
```

- [ ] **Step 3: Escribir los tests (fallan)**

`backend/tests/db/test_models.py`:
```python
from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tabernas.db.models import EmployeeRow, RestRuleRow, ScheduleExceptionRow
from tabernas.domain.types import Area, ExceptionKind, RhType

DAY = date(2026, 9, 24)


def _employee(session: Session) -> EmployeeRow:
    row = EmployeeRow(
        short_name="EMPLEADO A", area=Area.OTHER, applies_lateness=True, tracks_attendance=True
    )
    session.add(row)
    session.flush()
    return row


def test_closure_cannot_have_employee(session: Session) -> None:
    employee = _employee(session)
    session.add(
        ScheduleExceptionRow(
            kind=ExceptionKind.STORE_CLOSED, employee_id=employee.id, date_from=DAY, date_to=DAY
        )
    )
    with pytest.raises(IntegrityError, match="closure_has_no_employee"):
        session.flush()


def test_absence_requires_rh_type(session: Session) -> None:
    employee = _employee(session)
    session.add(
        ScheduleExceptionRow(
            kind=ExceptionKind.WORK_TO_ABSENCE, employee_id=employee.id, date_from=DAY, date_to=DAY
        )
    )
    with pytest.raises(IntegrityError, match="absence_has_rh_type"):
        session.flush()


def test_absence_with_rh_type_is_valid(session: Session) -> None:
    employee = _employee(session)
    session.add(
        ScheduleExceptionRow(
            kind=ExceptionKind.WORK_TO_ABSENCE,
            employee_id=employee.id,
            date_from=DAY,
            date_to=DAY,
            rh_type=RhType.VACACIONES,
        )
    )
    session.flush()


def test_rest_rule_weekdays_must_differ(session: Session) -> None:
    employee = _employee(session)
    session.add(
        RestRuleRow(
            employee_id=employee.id,
            fixed_weekday=1,
            extra_weekday=1,
            double_rest_anchor=date(2026, 9, 28),
            valid_from=date(2026, 1, 1),
        )
    )
    with pytest.raises(IntegrityError, match="distinct_weekdays"):
        session.flush()
```

`backend/tests/db/test_migrations.py`:
```python
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, text

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
            stored = dict(conn.execute(text("SELECT key, value FROM setting")).tuples().all())
        assert stored == {
            "entry_time_kitchen": "16:30",
            "entry_time_other": "16:40",
            "tolerance_minutes": "10",
        }
    finally:
        reset_schema(engine)
        Base.metadata.create_all(engine)
```

- [ ] **Step 4: Correr los tests de modelos (pasan) y de migraciones (falla)**

Run: `docker compose up -d db && uv run pytest tests/db -v`
Expected: `test_models.py` PASS; `test_migrations.py` FAIL (no existe `alembic.ini`).

- [ ] **Step 5: Configurar Alembic y generar la migración inicial**

```bash
uv run alembic init alembic
```
En `backend/alembic.ini`: deja `script_location = %(here)s/alembic`, vacía la línea
`sqlalchemy.url =` y pon `file_template = %%(rev)s_%%(slug)s`.

Reemplaza `backend/alembic/env.py`:
```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from tabernas.config import get_settings
from tabernas.db.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

Genera la migración contra la base de desarrollo vacía:
```bash
DATABASE_URL=postgresql+psycopg://tabernas:tabernas@localhost:5432/tabernas \
  uv run alembic revision --autogenerate --rev-id 0001 -m "initial schema"
```
Revisa `backend/alembic/versions/0001_initial_schema.py`: debe crear las 5 tablas con
`pk_*`, `uq_employee_sr_id`, `uq_justification_employee_id`, los 7 `ck_*` de los modelos,
los FKs con `ondelete="CASCADE"` y los índices `ix_*_employee_id`. Agrega al final de
`upgrade()` la semilla de settings (los mismos valores que `DEFAULT_SETTINGS`; se
copian literales para que la migración no dependa del código de la app):
```python
    setting = sa.table("setting", sa.column("key", sa.String), sa.column("value", sa.String))
    op.bulk_insert(
        setting,
        [
            {"key": "entry_time_kitchen", "value": "16:30"},
            {"key": "entry_time_other", "value": "16:40"},
            {"key": "tolerance_minutes", "value": "10"},
        ],
    )
```

- [ ] **Step 6: Correr y verificar que pasan**

Run: `uv run pytest tests/db -v && uv run ruff check . && uv run pyright`
Expected: todos PASS. Si `command.check` reporta diferencias, corrige la migración (no
los modelos) hasta que coincidan.

- [ ] **Step 7: Commit**

```bash
git add backend/src/tabernas/db backend/alembic.ini backend/alembic backend/tests
git commit -m "feat: add postgres schema and initial alembic migration

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Repositorios de empleados y settings

**Files:**
- Create: `backend/src/tabernas/repos/__init__.py` (vacío), `repos/errors.py`,
  `repos/common.py`, `repos/employees.py`, `repos/settings.py`,
  `backend/tests/repos/__init__.py`, `backend/tests/repos/helpers.py`,
  `backend/tests/repos/test_employees.py`, `backend/tests/repos/test_settings.py`

**Interfaces:**
- Consumes: filas ORM (Task 10); `Employee`, `AttendanceSettings`, `DEFAULT_SETTINGS`,
  `DomainValidationError`, `parse_hhmm`, `format_hhmm`, `validate_tolerance` (Task 3).
- Produces: `NotFoundError(LookupError)`, `ConflictError(RuntimeError)`;
  `require_employee(session, employee_id) -> EmployeeRow`,
  `ranges_overlap(a_from, a_to, b_from, b_to) -> bool` (`None` = abierto),
  `check_fields(changes, editable)`;
  `EmployeeRepo(session)`: `find_all(*, active_only=False) -> list[Employee]`,
  `find_by_id(id) -> Employee`, `existing_sr_ids() -> set[int]`,
  `create(*, sr_id, short_name, rh_name, area, applies_lateness, tracks_attendance) -> Employee`,
  `update(id, changes: Mapping[str, object]) -> Employee`;
  `SettingsRepo(session)`: `get() -> AttendanceSettings`, `save(AttendanceSettings) -> AttendanceSettings`;
  helper de tests `make_employee(session, sr_id=101, **overrides) -> Employee`.

- [ ] **Step 1: Escribir los tests (fallan)**

`backend/tests/repos/helpers.py`:
```python
from sqlalchemy.orm import Session

from tabernas.domain.types import Area, Employee
from tabernas.repos.employees import EmployeeRepo


def make_employee(
    session: Session,
    sr_id: int | None = 101,
    *,
    short_name: str = "EMPLEADO A",
    area: Area = Area.OTHER,
) -> Employee:
    return EmployeeRepo(session).create(
        sr_id=sr_id,
        short_name=short_name,
        rh_name=None,
        area=area,
        applies_lateness=True,
        tracks_attendance=True,
    )
```

`backend/tests/repos/test_employees.py`:
```python
import pytest
from sqlalchemy.orm import Session

from tabernas.domain.types import Area
from tabernas.domain.validation import DomainValidationError
from tabernas.repos.employees import EmployeeRepo
from tabernas.repos.errors import ConflictError, NotFoundError
from tests.repos.helpers import make_employee


def test_create_and_find(session: Session) -> None:
    created = make_employee(session, area=Area.KITCHEN)
    assert created.active
    assert EmployeeRepo(session).find_by_id(created.id) == created


def test_find_all_orders_by_name_and_filters_active(session: Session) -> None:
    repo = EmployeeRepo(session)
    b = make_employee(session, 102, short_name="EMPLEADO B")
    a = make_employee(session, 101, short_name="EMPLEADO A")
    repo.update(b.id, {"active": False})
    assert [e.id for e in repo.find_all()] == [a.id, b.id]
    assert [e.id for e in repo.find_all(active_only=True)] == [a.id]


def test_duplicate_sr_id_conflicts_and_session_stays_usable(session: Session) -> None:
    make_employee(session, 101)
    with pytest.raises(ConflictError, match="101"):
        make_employee(session, 101, short_name="OTRO")
    assert make_employee(session, 102).sr_id == 102


def test_employees_without_sr_id_can_repeat(session: Session) -> None:
    make_employee(session, None, short_name="GERENTE")
    make_employee(session, None, short_name="OTRO")
    assert len(EmployeeRepo(session).find_all()) == 2


def test_update_returns_new_object(session: Session) -> None:
    created = make_employee(session)
    updated = EmployeeRepo(session).update(created.id, {"rh_name": "APELLIDO NOMBRE"})
    assert updated.rh_name == "APELLIDO NOMBRE"
    assert created.rh_name is None


def test_update_rejects_non_editable_fields(session: Session) -> None:
    created = make_employee(session)
    with pytest.raises(DomainValidationError, match="sr_id"):
        EmployeeRepo(session).update(created.id, {"sr_id": 5})


def test_missing_employee_is_not_found(session: Session) -> None:
    with pytest.raises(NotFoundError):
        EmployeeRepo(session).find_by_id(999)


def test_existing_sr_ids(session: Session) -> None:
    make_employee(session, 101)
    make_employee(session, None, short_name="GERENTE")
    assert EmployeeRepo(session).existing_sr_ids() == {101}
```

`backend/tests/repos/test_settings.py`:
```python
from datetime import time

import pytest
from sqlalchemy.orm import Session

from tabernas.db.models import SettingRow
from tabernas.domain.types import DEFAULT_SETTINGS, AttendanceSettings
from tabernas.domain.validation import DomainValidationError
from tabernas.repos.settings import SettingsRepo


def test_empty_table_returns_defaults(session: Session) -> None:
    # Review Focus #5: a database created without the seed must still work.
    assert SettingsRepo(session).get() == DEFAULT_SETTINGS


def test_partial_rows_are_filled_with_defaults(session: Session) -> None:
    session.add(SettingRow(key="tolerance_minutes", value="5"))
    session.flush()
    settings = SettingsRepo(session).get()
    assert settings.tolerance_minutes == 5
    assert settings.entry_time_other == DEFAULT_SETTINGS.entry_time_other


def test_save_round_trip(session: Session) -> None:
    wanted = AttendanceSettings(time(16, 0), time(16, 15), 5)
    assert SettingsRepo(session).save(wanted) == wanted
    assert SettingsRepo(session).get() == wanted


def test_save_rejects_bad_tolerance(session: Session) -> None:
    with pytest.raises(DomainValidationError):
        SettingsRepo(session).save(AttendanceSettings(time(16, 0), time(16, 15), 90))
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `uv run pytest tests/repos -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'tabernas.repos'`

- [ ] **Step 3: Implementar**

`backend/src/tabernas/repos/errors.py`:
```python
class NotFoundError(LookupError):
    """Requested record does not exist. The API maps it to 404."""


class ConflictError(RuntimeError):
    """Record clashes with existing data (duplicates, overlapping ranges). Maps to 409."""
```

`backend/src/tabernas/repos/common.py`:
```python
from collections.abc import Collection, Mapping
from datetime import date

from sqlalchemy.orm import Session

from tabernas.db.models import EmployeeRow
from tabernas.domain.validation import DomainValidationError
from tabernas.repos.errors import NotFoundError


def require_employee(session: Session, employee_id: int) -> EmployeeRow:
    row = session.get(EmployeeRow, employee_id)
    if row is None:
        raise NotFoundError("Empleado no encontrado")
    return row


def ranges_overlap(
    a_from: date, a_to: date | None, b_from: date, b_to: date | None
) -> bool:
    return a_from <= (b_to or date.max) and b_from <= (a_to or date.max)


def check_fields(changes: Mapping[str, object], editable: Collection[str]) -> None:
    unknown = sorted(set(changes) - set(editable))
    if unknown:
        raise DomainValidationError(f"Campos no editables: {', '.join(unknown)}")
```

`backend/src/tabernas/repos/employees.py`:
```python
"""Employee persistence. Returns immutable domain objects, never ORM rows."""

from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tabernas.db.models import EmployeeRow
from tabernas.domain.types import Area, Employee
from tabernas.repos.common import check_fields, require_employee
from tabernas.repos.errors import ConflictError

EDITABLE_FIELDS = frozenset(
    {"short_name", "rh_name", "area", "applies_lateness", "tracks_attendance", "active"}
)


def to_employee(row: EmployeeRow) -> Employee:
    return Employee(
        id=row.id,
        sr_id=row.sr_id,
        short_name=row.short_name,
        rh_name=row.rh_name,
        area=row.area,
        applies_lateness=row.applies_lateness,
        tracks_attendance=row.tracks_attendance,
        active=row.active,
    )


class EmployeeRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_all(self, *, active_only: bool = False) -> list[Employee]:
        stmt = select(EmployeeRow).order_by(EmployeeRow.short_name, EmployeeRow.id)
        if active_only:
            stmt = stmt.where(EmployeeRow.active.is_(True))
        return [to_employee(row) for row in self._session.scalars(stmt)]

    def find_by_id(self, employee_id: int) -> Employee:
        return to_employee(require_employee(self._session, employee_id))

    def existing_sr_ids(self) -> set[int]:
        ids = self._session.scalars(select(EmployeeRow.sr_id))
        return {sr_id for sr_id in ids if sr_id is not None}

    def create(
        self,
        *,
        sr_id: int | None,
        short_name: str,
        rh_name: str | None,
        area: Area,
        applies_lateness: bool,
        tracks_attendance: bool,
    ) -> Employee:
        row = EmployeeRow(
            sr_id=sr_id,
            short_name=short_name,
            rh_name=rh_name,
            area=area,
            applies_lateness=applies_lateness,
            tracks_attendance=tracks_attendance,
            active=True,
        )
        try:
            with self._session.begin_nested():
                self._session.add(row)
        except IntegrityError as exc:
            raise ConflictError(f"Ya existe un empleado con id SR {sr_id}") from exc
        return to_employee(row)

    def update(self, employee_id: int, changes: Mapping[str, object]) -> Employee:
        check_fields(changes, EDITABLE_FIELDS)
        row = require_employee(self._session, employee_id)
        for field, value in changes.items():
            setattr(row, field, value)  # ORM rows are the mutable persistence boundary
        self._session.flush()
        return to_employee(row)
```

`backend/src/tabernas/repos/settings.py`:
```python
"""Attendance settings stored as key/value rows; missing keys fall back to defaults."""

from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from tabernas.db.models import SettingRow
from tabernas.domain.types import DEFAULT_SETTINGS, AttendanceSettings
from tabernas.domain.validation import format_hhmm, parse_hhmm, validate_tolerance


def serialize_settings(settings: AttendanceSettings) -> dict[str, str]:
    return {
        "entry_time_kitchen": format_hhmm(settings.entry_time_kitchen),
        "entry_time_other": format_hhmm(settings.entry_time_other),
        "tolerance_minutes": str(settings.tolerance_minutes),
    }


def deserialize_settings(values: Mapping[str, str]) -> AttendanceSettings:
    return AttendanceSettings(
        entry_time_kitchen=parse_hhmm(values["entry_time_kitchen"]),
        entry_time_other=parse_hhmm(values["entry_time_other"]),
        tolerance_minutes=int(values["tolerance_minutes"]),
    )


class SettingsRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self) -> AttendanceSettings:
        stored = dict(self._session.execute(select(SettingRow.key, SettingRow.value)).tuples())
        return deserialize_settings({**serialize_settings(DEFAULT_SETTINGS), **stored})

    def save(self, settings: AttendanceSettings) -> AttendanceSettings:
        validate_tolerance(settings.tolerance_minutes)
        for key, value in serialize_settings(settings).items():
            self._session.merge(SettingRow(key=key, value=value))
        self._session.flush()
        return self.get()
```

- [ ] **Step 4: Correr y verificar que pasan**

Run: `uv run pytest tests/repos -v && uv run ruff check . && uv run pyright`
Expected: todos PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tabernas/repos backend/tests/repos
git commit -m "feat: add employee and settings repositories

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: Repositorios de reglas, excepciones y justificaciones

**Files:**
- Create: `backend/src/tabernas/repos/rest_rules.py`, `repos/exceptions.py`,
  `repos/justifications.py`, `backend/tests/repos/test_rest_rules.py`,
  `backend/tests/repos/test_exceptions.py`, `backend/tests/repos/test_justifications.py`

**Interfaces:**
- Consumes: Task 11 (`require_employee`, `ranges_overlap`, `check_fields`, errores,
  `make_employee`); validadores de Task 3; `default_rh_type` (Task 6).
- Produces:
  - `RestRuleRepo(session)`: `find_all(*, employee_id=None) -> list[RestRule]`,
    `find_by_id(id)`, `create(*, employee_id, fixed_weekday, extra_weekday, double_rest_anchor, valid_from, valid_to) -> RestRule`,
    `update(id, changes) -> RestRule` (editables: `fixed_weekday`, `extra_weekday`,
    `double_rest_anchor`, `valid_from`, `valid_to`), `delete(id) -> None`.
  - `ExceptionRepo(session)`: `find_all(*, start=None, end=None, employee_id=None) -> list[ScheduleException]`
    (traslape con el rango), `find_by_id(id)`,
    `create(*, kind, employee_id, date_from, date_to, rh_type, comment) -> ScheduleException`,
    `update(id, changes)` (editables: `date_from`, `date_to`, `rh_type`, `comment`),
    `delete(id)`, `create_rest_swap(*, employee_id, absent_day, worked_day, comment) -> tuple[ScheduleException, ScheduleException]`.
  - `JustificationRepo(session)`: `find_all(*, start, end, employee_id=None) -> list[Justification]`,
    `find_by_id(id)`, `create(*, employee_id, day, incident, reason, rh_type=None) -> Justification`,
    `update(id, changes)` (editables: `reason`, `rh_type`), `delete(id)`.

- [ ] **Step 1: Escribir los tests (fallan)**

`backend/tests/repos/test_rest_rules.py`:
```python
from datetime import date

import pytest
from sqlalchemy.orm import Session

from tabernas.domain.validation import DomainValidationError
from tabernas.repos.errors import ConflictError, NotFoundError
from tabernas.repos.rest_rules import RestRuleRepo
from tests.repos.helpers import make_employee

MONDAY = date(2026, 9, 28)


def create(
    session: Session,
    employee_id: int,
    *,
    valid_from: date = date(2026, 1, 1),
    valid_to: date | None = None,
    anchor: date = MONDAY,
):
    return RestRuleRepo(session).create(
        employee_id=employee_id,
        fixed_weekday=1,
        extra_weekday=0,
        double_rest_anchor=anchor,
        valid_from=valid_from,
        valid_to=valid_to,
    )


def test_create_and_find(session: Session) -> None:
    employee = make_employee(session)
    rule = create(session, employee.id)
    repo = RestRuleRepo(session)
    assert repo.find_by_id(rule.id) == rule
    assert repo.find_all(employee_id=employee.id) == [rule]


def test_unknown_employee_is_not_found(session: Session) -> None:
    with pytest.raises(NotFoundError):
        create(session, 999)


def test_invalid_rule_is_rejected(session: Session) -> None:
    employee = make_employee(session)
    with pytest.raises(DomainValidationError, match="lunes"):
        create(session, employee.id, anchor=date(2026, 9, 29))


def test_overlapping_validity_conflicts(session: Session) -> None:
    employee = make_employee(session)
    create(session, employee.id)
    with pytest.raises(ConflictError, match="traslapa"):
        create(session, employee.id, valid_from=date(2026, 10, 1))


def test_consecutive_rules_and_other_employees_do_not_conflict(session: Session) -> None:
    a = make_employee(session, 101)
    b = make_employee(session, 102, short_name="EMPLEADO B")
    first = create(session, a.id, valid_to=date(2026, 9, 30))
    create(session, a.id, valid_from=date(2026, 10, 1))
    create(session, b.id)
    assert len(RestRuleRepo(session).find_all()) == 3
    assert first.valid_to == date(2026, 9, 30)


def test_update_is_validated_against_other_rules(session: Session) -> None:
    employee = make_employee(session)
    first = create(session, employee.id, valid_to=date(2026, 9, 30))
    create(session, employee.id, valid_from=date(2026, 10, 1))
    repo = RestRuleRepo(session)
    with pytest.raises(ConflictError):
        repo.update(first.id, {"valid_to": None})
    assert repo.update(first.id, {"fixed_weekday": 3}).fixed_weekday == 3


def test_delete(session: Session) -> None:
    employee = make_employee(session)
    rule = create(session, employee.id)
    repo = RestRuleRepo(session)
    repo.delete(rule.id)
    with pytest.raises(NotFoundError):
        repo.find_by_id(rule.id)
```

`backend/tests/repos/test_exceptions.py`:
```python
from datetime import date

import pytest
from sqlalchemy.orm import Session

from tabernas.domain.types import ExceptionKind, RhType
from tabernas.domain.validation import DomainValidationError
from tabernas.repos.errors import ConflictError
from tabernas.repos.exceptions import ExceptionRepo
from tests.repos.helpers import make_employee

DAY = date(2026, 9, 24)


def test_closure_has_no_employee_and_may_overlap_employee_exceptions(session: Session) -> None:
    employee = make_employee(session)
    repo = ExceptionRepo(session)
    repo.create(
        kind=ExceptionKind.REST_TO_WORK, employee_id=employee.id,
        date_from=DAY, date_to=DAY, rh_type=None, comment="",
    )
    closure = repo.create(
        kind=ExceptionKind.STORE_CLOSED, employee_id=None,
        date_from=DAY, date_to=DAY, rh_type=None, comment="Ley Seca",
    )
    assert closure.employee_id is None
    assert len(repo.find_all(start=DAY, end=DAY)) == 2


def test_same_employee_overlap_conflicts(session: Session) -> None:
    employee = make_employee(session)
    repo = ExceptionRepo(session)
    repo.create(
        kind=ExceptionKind.WORK_TO_ABSENCE, employee_id=employee.id, date_from=DAY,
        date_to=date(2026, 9, 26), rh_type=RhType.VACACIONES, comment="",
    )
    with pytest.raises(ConflictError, match="Ya hay una excepción"):
        repo.create(
            kind=ExceptionKind.PRESENT_NO_CHECKIN, employee_id=employee.id,
            date_from=date(2026, 9, 26), date_to=date(2026, 9, 26), rh_type=None, comment="",
        )


def test_find_all_returns_exceptions_overlapping_the_range(session: Session) -> None:
    employee = make_employee(session)
    repo = ExceptionRepo(session)
    repo.create(
        kind=ExceptionKind.WORK_TO_ABSENCE, employee_id=employee.id, date_from=date(2026, 9, 18),
        date_to=date(2026, 9, 22), rh_type=RhType.INCAPACIDAD, comment="",
    )
    assert len(repo.find_all(start=date(2026, 9, 21), end=date(2026, 9, 27))) == 1
    assert repo.find_all(start=date(2026, 9, 23), end=date(2026, 9, 27)) == []


def test_update_dates_and_reject_kind_change(session: Session) -> None:
    employee = make_employee(session)
    repo = ExceptionRepo(session)
    created = repo.create(
        kind=ExceptionKind.REST_TO_WORK, employee_id=employee.id,
        date_from=DAY, date_to=DAY, rh_type=None, comment="",
    )
    moved = repo.update(created.id, {"date_from": date(2026, 9, 25), "date_to": date(2026, 9, 25)})
    assert moved.date_from == date(2026, 9, 25)
    with pytest.raises(DomainValidationError, match="kind"):
        repo.update(created.id, {"kind": ExceptionKind.STORE_CLOSED})


def test_rest_swap_creates_absence_and_extra_workday(session: Session) -> None:
    employee = make_employee(session)
    absence, worked = ExceptionRepo(session).create_rest_swap(
        employee_id=employee.id, absent_day=date(2026, 9, 23), worked_day=date(2026, 9, 29),
        comment="Cambio de descanso",
    )
    assert (absence.kind, absence.rh_type, absence.date_from) == (
        ExceptionKind.WORK_TO_ABSENCE, RhType.DESCANSO, date(2026, 9, 23),
    )
    assert (worked.kind, worked.rh_type, worked.date_from) == (
        ExceptionKind.REST_TO_WORK, None, date(2026, 9, 29),
    )


def test_rest_swap_is_atomic(session: Session) -> None:
    employee = make_employee(session)
    repo = ExceptionRepo(session)
    existing = repo.create(
        kind=ExceptionKind.PRESENT_NO_CHECKIN, employee_id=employee.id,
        date_from=date(2026, 9, 29), date_to=date(2026, 9, 29), rh_type=None, comment="",
    )
    with pytest.raises(ConflictError):
        repo.create_rest_swap(
            employee_id=employee.id, absent_day=date(2026, 9, 23),
            worked_day=date(2026, 9, 29), comment="",
        )
    assert repo.find_all() == [existing]


def test_rest_swap_needs_two_different_days(session: Session) -> None:
    employee = make_employee(session)
    with pytest.raises(DomainValidationError, match="distintos"):
        ExceptionRepo(session).create_rest_swap(
            employee_id=employee.id, absent_day=DAY, worked_day=DAY, comment=""
        )
```

`backend/tests/repos/test_justifications.py`:
```python
from datetime import date

import pytest
from sqlalchemy.orm import Session

from tabernas.domain.types import Incident, RhType
from tabernas.domain.validation import DomainValidationError
from tabernas.repos.errors import ConflictError, NotFoundError
from tabernas.repos.justifications import JustificationRepo
from tests.repos.helpers import make_employee

DAY = date(2026, 9, 23)


def test_create_uses_default_rh_type(session: Session) -> None:
    employee = make_employee(session)
    repo = JustificationRepo(session)
    late = repo.create(employee_id=employee.id, day=DAY, incident=Incident.LATE, reason="Tráfico")
    absent = repo.create(
        employee_id=employee.id, day=DAY, incident=Incident.ABSENT, reason="Enfermo"
    )
    assert late.rh_type == RhType.NO_CAPTURAR
    assert absent.rh_type == RhType.FALTA_JUSTIFICADA


def test_duplicate_conflicts(session: Session) -> None:
    employee = make_employee(session)
    repo = JustificationRepo(session)
    repo.create(employee_id=employee.id, day=DAY, incident=Incident.LATE, reason="Tráfico")
    with pytest.raises(ConflictError):
        repo.create(employee_id=employee.id, day=DAY, incident=Incident.LATE, reason="Otra")


def test_rh_type_is_validated_on_create_and_update(session: Session) -> None:
    employee = make_employee(session)
    repo = JustificationRepo(session)
    with pytest.raises(DomainValidationError):
        repo.create(
            employee_id=employee.id, day=DAY, incident=Incident.LATE,
            reason="x", rh_type=RhType.VACACIONES,
        )
    created = repo.create(employee_id=employee.id, day=DAY, incident=Incident.ABSENT, reason="x")
    assert repo.update(created.id, {"rh_type": RhType.INCAPACIDAD}).rh_type == RhType.INCAPACIDAD
    with pytest.raises(DomainValidationError):
        repo.update(created.id, {"rh_type": RhType.RETARDO})


def test_find_all_by_range_and_delete(session: Session) -> None:
    employee = make_employee(session)
    repo = JustificationRepo(session)
    inside = repo.create(employee_id=employee.id, day=DAY, incident=Incident.LATE, reason="x")
    repo.create(
        employee_id=employee.id, day=date(2026, 9, 30), incident=Incident.LATE, reason="y"
    )
    assert repo.find_all(start=date(2026, 9, 21), end=date(2026, 9, 27)) == [inside]
    repo.delete(inside.id)
    with pytest.raises(NotFoundError):
        repo.find_by_id(inside.id)
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `uv run pytest tests/repos -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'tabernas.repos.rest_rules'`

- [ ] **Step 3: Implementar**

`backend/src/tabernas/repos/rest_rules.py`:
```python
from collections.abc import Mapping
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from tabernas.db.models import RestRuleRow
from tabernas.domain.types import RestRule
from tabernas.domain.validation import validate_rest_rule
from tabernas.repos.common import check_fields, ranges_overlap, require_employee
from tabernas.repos.errors import ConflictError, NotFoundError

EDITABLE_FIELDS = frozenset(
    {"fixed_weekday", "extra_weekday", "double_rest_anchor", "valid_from", "valid_to"}
)


def to_rest_rule(row: RestRuleRow) -> RestRule:
    return RestRule(
        id=row.id,
        employee_id=row.employee_id,
        fixed_weekday=row.fixed_weekday,
        extra_weekday=row.extra_weekday,
        double_rest_anchor=row.double_rest_anchor,
        valid_from=row.valid_from,
        valid_to=row.valid_to,
    )


def _fields_of(row: RestRuleRow) -> dict[str, Any]:
    return {field: getattr(row, field) for field in EDITABLE_FIELDS}


class RestRuleRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_all(self, *, employee_id: int | None = None) -> list[RestRule]:
        stmt = select(RestRuleRow).order_by(RestRuleRow.employee_id, RestRuleRow.valid_from)
        if employee_id is not None:
            stmt = stmt.where(RestRuleRow.employee_id == employee_id)
        return [to_rest_rule(row) for row in self._session.scalars(stmt)]

    def find_by_id(self, rule_id: int) -> RestRule:
        return to_rest_rule(self._require(rule_id))

    def create(
        self,
        *,
        employee_id: int,
        fixed_weekday: int,
        extra_weekday: int,
        double_rest_anchor: date,
        valid_from: date,
        valid_to: date | None,
    ) -> RestRule:
        require_employee(self._session, employee_id)
        fields: dict[str, Any] = {
            "fixed_weekday": fixed_weekday,
            "extra_weekday": extra_weekday,
            "double_rest_anchor": double_rest_anchor,
            "valid_from": valid_from,
            "valid_to": valid_to,
        }
        self._validate(employee_id, fields, exclude_id=None)
        row = RestRuleRow(employee_id=employee_id, **fields)
        self._session.add(row)
        self._session.flush()
        return to_rest_rule(row)

    def update(self, rule_id: int, changes: Mapping[str, Any]) -> RestRule:
        check_fields(changes, EDITABLE_FIELDS)
        row = self._require(rule_id)
        self._validate(row.employee_id, {**_fields_of(row), **changes}, exclude_id=rule_id)
        for field, value in changes.items():
            setattr(row, field, value)
        self._session.flush()
        return to_rest_rule(row)

    def delete(self, rule_id: int) -> None:
        self._session.delete(self._require(rule_id))
        self._session.flush()

    def _require(self, rule_id: int) -> RestRuleRow:
        row = self._session.get(RestRuleRow, rule_id)
        if row is None:
            raise NotFoundError("Regla de descanso no encontrada")
        return row

    def _validate(
        self, employee_id: int, fields: Mapping[str, Any], exclude_id: int | None
    ) -> None:
        validate_rest_rule(**fields)
        others = [r for r in self.find_all(employee_id=employee_id) if r.id != exclude_id]
        if any(
            ranges_overlap(fields["valid_from"], fields["valid_to"], o.valid_from, o.valid_to)
            for o in others
        ):
            raise ConflictError("La vigencia se traslapa con otra regla del mismo empleado")
```

`backend/src/tabernas/repos/exceptions.py`:
```python
from collections.abc import Mapping
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from tabernas.db.models import ScheduleExceptionRow
from tabernas.domain.types import ExceptionKind, RhType, ScheduleException
from tabernas.domain.validation import DomainValidationError, validate_exception
from tabernas.repos.common import check_fields, require_employee
from tabernas.repos.errors import ConflictError, NotFoundError

EDITABLE_FIELDS = frozenset({"date_from", "date_to", "rh_type", "comment"})
_VALIDATED_FIELDS = ("kind", "employee_id", "date_from", "date_to", "rh_type")


def to_exception(row: ScheduleExceptionRow) -> ScheduleException:
    return ScheduleException(
        id=row.id,
        kind=row.kind,
        employee_id=row.employee_id,
        date_from=row.date_from,
        date_to=row.date_to,
        rh_type=row.rh_type,
        comment=row.comment,
    )


class ExceptionRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_all(
        self,
        *,
        start: date | None = None,
        end: date | None = None,
        employee_id: int | None = None,
    ) -> list[ScheduleException]:
        stmt = select(ScheduleExceptionRow).order_by(
            ScheduleExceptionRow.date_from, ScheduleExceptionRow.id
        )
        if start is not None:
            stmt = stmt.where(ScheduleExceptionRow.date_to >= start)
        if end is not None:
            stmt = stmt.where(ScheduleExceptionRow.date_from <= end)
        if employee_id is not None:
            stmt = stmt.where(ScheduleExceptionRow.employee_id == employee_id)
        return [to_exception(row) for row in self._session.scalars(stmt)]

    def find_by_id(self, exception_id: int) -> ScheduleException:
        return to_exception(self._require(exception_id))

    def create(
        self,
        *,
        kind: ExceptionKind,
        employee_id: int | None,
        date_from: date,
        date_to: date,
        rh_type: RhType | None,
        comment: str,
    ) -> ScheduleException:
        fields: dict[str, Any] = {
            "kind": kind,
            "employee_id": employee_id,
            "date_from": date_from,
            "date_to": date_to,
            "rh_type": rh_type,
        }
        self._validate(fields, exclude_id=None)
        row = ScheduleExceptionRow(**fields, comment=comment)
        self._session.add(row)
        self._session.flush()
        return to_exception(row)

    def update(self, exception_id: int, changes: Mapping[str, Any]) -> ScheduleException:
        check_fields(changes, EDITABLE_FIELDS)
        row = self._require(exception_id)
        current = {field: getattr(row, field) for field in _VALIDATED_FIELDS}
        validated = {k: v for k, v in changes.items() if k != "comment"}
        self._validate({**current, **validated}, exclude_id=exception_id)
        for field, value in changes.items():
            setattr(row, field, value)
        self._session.flush()
        return to_exception(row)

    def delete(self, exception_id: int) -> None:
        self._session.delete(self._require(exception_id))
        self._session.flush()

    def create_rest_swap(
        self, *, employee_id: int, absent_day: date, worked_day: date, comment: str
    ) -> tuple[ScheduleException, ScheduleException]:
        """Decision #4: incident on the day not worked; a rest day becomes a workday."""
        if absent_day == worked_day:
            raise DomainValidationError("El día de descanso y el día trabajado deben ser distintos")
        with self._session.begin_nested():
            absence = self.create(
                kind=ExceptionKind.WORK_TO_ABSENCE,
                employee_id=employee_id,
                date_from=absent_day,
                date_to=absent_day,
                rh_type=RhType.DESCANSO,
                comment=comment,
            )
            worked = self.create(
                kind=ExceptionKind.REST_TO_WORK,
                employee_id=employee_id,
                date_from=worked_day,
                date_to=worked_day,
                rh_type=None,
                comment=comment,
            )
        return absence, worked

    def _require(self, exception_id: int) -> ScheduleExceptionRow:
        row = self._session.get(ScheduleExceptionRow, exception_id)
        if row is None:
            raise NotFoundError("Excepción no encontrada")
        return row

    def _validate(self, fields: Mapping[str, Any], exclude_id: int | None) -> None:
        validate_exception(**fields)
        employee_id = fields["employee_id"]
        if employee_id is None:
            return
        require_employee(self._session, employee_id)
        clashing = [
            e
            for e in self.find_all(
                start=fields["date_from"], end=fields["date_to"], employee_id=employee_id
            )
            if e.id != exclude_id
        ]
        if clashing:
            raise ConflictError("Ya hay una excepción para ese empleado en esas fechas")
```

`backend/src/tabernas/repos/justifications.py`:
```python
from collections.abc import Mapping
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tabernas.db.models import JustificationRow
from tabernas.domain.justify import default_rh_type
from tabernas.domain.types import Incident, Justification, RhType
from tabernas.domain.validation import validate_justification
from tabernas.repos.common import check_fields, require_employee
from tabernas.repos.errors import ConflictError, NotFoundError

EDITABLE_FIELDS = frozenset({"reason", "rh_type"})


def to_justification(row: JustificationRow) -> Justification:
    return Justification(
        id=row.id,
        employee_id=row.employee_id,
        day=row.day,
        incident=row.incident,
        reason=row.reason,
        rh_type=row.rh_type,
    )


class JustificationRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_all(
        self, *, start: date, end: date, employee_id: int | None = None
    ) -> list[Justification]:
        stmt = (
            select(JustificationRow)
            .where(JustificationRow.day >= start, JustificationRow.day <= end)
            .order_by(JustificationRow.day, JustificationRow.id)
        )
        if employee_id is not None:
            stmt = stmt.where(JustificationRow.employee_id == employee_id)
        return [to_justification(row) for row in self._session.scalars(stmt)]

    def find_by_id(self, justification_id: int) -> Justification:
        return to_justification(self._require(justification_id))

    def create(
        self,
        *,
        employee_id: int,
        day: date,
        incident: Incident,
        reason: str,
        rh_type: RhType | None = None,
    ) -> Justification:
        chosen = rh_type or default_rh_type(incident)
        validate_justification(incident=incident, rh_type=chosen)
        require_employee(self._session, employee_id)
        row = JustificationRow(
            employee_id=employee_id, day=day, incident=incident, reason=reason, rh_type=chosen
        )
        try:
            with self._session.begin_nested():
                self._session.add(row)
        except IntegrityError as exc:
            raise ConflictError("Esa incidencia ya tiene justificación") from exc
        return to_justification(row)

    def update(self, justification_id: int, changes: Mapping[str, Any]) -> Justification:
        check_fields(changes, EDITABLE_FIELDS)
        row = self._require(justification_id)
        if "rh_type" in changes:
            validate_justification(incident=row.incident, rh_type=changes["rh_type"])
        for field, value in changes.items():
            setattr(row, field, value)
        self._session.flush()
        return to_justification(row)

    def delete(self, justification_id: int) -> None:
        self._session.delete(self._require(justification_id))
        self._session.flush()

    def _require(self, justification_id: int) -> JustificationRow:
        row = self._session.get(JustificationRow, justification_id)
        if row is None:
            raise NotFoundError("Justificación no encontrada")
        return row
```

- [ ] **Step 4: Correr y verificar que pasan**

Run: `uv run pytest tests/repos -v && uv run ruff check . && uv run pyright`
Expected: todos PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tabernas/repos backend/tests/repos
git commit -m "feat: add rest rule, exception and justification repositories

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 13: Base de la API — sobre, errores, dependencias, `create_app` y health

**Files:**
- Create: `backend/src/tabernas/api/__init__.py` (vacío), `api/envelope.py`,
  `api/errors.py`, `api/deps.py`, `api/schemas.py`, `api/routes/__init__.py`,
  `api/routes/health.py`, `backend/src/tabernas/main.py`, `backend/tests/test_main.py`,
  `backend/tests/api/__init__.py`, `backend/tests/api/conftest.py`,
  `backend/tests/api/test_health.py`, `backend/tests/api/test_errors.py`
- Modify: `backend/tests/support.py` (agrega `READ_ONLY_INFO` y `StubSource`)

**Interfaces:**
- Consumes: `Settings`, `get_settings` (Task 1); `build_sr_source`, `SrSource`, errores SR
  (Tasks 8–9); `make_engine`, `make_session_factory` (Task 10); errores de repos (Task 11);
  `DomainValidationError` (Task 3).
- Produces:
  - `tabernas.api.envelope`: `ErrorBody(code, message)`,
    `Envelope[T](success, data, error, meta)`, `ok(data, meta=None) -> Envelope[T]`.
  - `tabernas.api.deps`: `SessionDep` (commit al terminar la ruta, rollback si falla),
    `SrSourceDep`, `ClockDep` (`Callable[[], datetime]`), `AppSettingsDep`.
  - `tabernas.api.schemas.PatchModel` (base para PATCH: `extra="forbid"`, rechaza
    `null` salvo en `NULLABLE`, método `changes() -> dict`).
  - `tabernas.api.routes.ROUTERS: list[APIRouter]` (las tareas siguientes agregan el suyo).
  - `tabernas.main.create_app(*, settings=None, sr_source=None, session_factory=None, clock=None) -> FastAPI`,
    `tabernas.main.local_clock(tz_name, now=datetime.now) -> Callable[[], datetime]`.
  - Tests: `tests.support.StubSource(employees=(), checkins=(), info=READ_ONLY_INFO, error=None)`
    con `.calls: list[tuple[date, date]]`; fixtures `make_client(source=None) -> TestClient`
    y `client`; `tests.api.conftest.FIXED_NOW = datetime(2026, 9, 27, 20, 0)`.
- Códigos de error: `VALIDATION_ERROR` 422, `NOT_FOUND` 404, `CONFLICT` 409,
  `SR_UNAVAILABLE` 503, `SR_NOT_READONLY` 500, `METHOD_NOT_ALLOWED` 405,
  `HTTP_ERROR` (otros), `INTERNAL` 500.

- [ ] **Step 1: Agregar el doble de SR a `tests/support.py`**

`backend/tests/support.py` completo:
```python
import os
from collections.abc import Sequence
from datetime import date

from sqlalchemy import Engine, text

from tabernas.sr.source import SrCheckin, SrEmployee, SrServerInfo

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://tabernas:tabernas@localhost:5432/tabernas_test"
)

READ_ONLY_INFO = SrServerInfo(
    server="SRV",
    instance="INST",
    version="12.0.4100.1",
    edition="Express Edition",
    database="softrestaurant11",
    login="reportes_ro",
    is_datareader=True,
    is_denywriter=True,
    is_sysadmin=False,
)


def reset_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))


class StubSource:
    """SrSource test double: canned data, optional error, records check-in calls."""

    def __init__(
        self,
        *,
        employees: Sequence[SrEmployee] = (),
        checkins: Sequence[SrCheckin] = (),
        info: SrServerInfo = READ_ONLY_INFO,
        error: Exception | None = None,
    ) -> None:
        self._employees = tuple(employees)
        self._checkins = tuple(checkins)
        self._info = info
        self._error = error
        self.calls: list[tuple[date, date]] = []

    def fetch_employees(self) -> list[SrEmployee]:
        self._fail_if_broken()
        return list(self._employees)

    def fetch_checkins(self, start: date, end: date) -> list[SrCheckin]:
        self._fail_if_broken()
        self.calls.append((start, end))
        return [c for c in self._checkins if start <= c.at.date() <= end]

    def server_info(self) -> SrServerInfo:
        self._fail_if_broken()
        return self._info

    def _fail_if_broken(self) -> None:
        if self._error is not None:
            raise self._error
```

- [ ] **Step 2: Escribir los tests (fallan)**

`backend/tests/test_main.py`:
```python
from datetime import UTC, datetime, tzinfo

from tabernas.config import Settings
from tabernas.main import create_app, local_clock
from tabernas.sr.fake_source import FakeSource
from tests.support import TEST_DATABASE_URL


def test_local_clock_uses_business_timezone() -> None:
    # Review Focus #3: 05:30 UTC on the 28th is still 23:30 on the 27th in Monterrey.
    instant = datetime(2026, 9, 28, 5, 30, tzinfo=UTC)

    def fake_now(tz: tzinfo) -> datetime:
        return instant.astimezone(tz)

    clock = local_clock("America/Mexico_City", now=fake_now)
    assert clock() == datetime(2026, 9, 27, 23, 30)


def test_fake_mode_wires_fake_source_without_touching_services() -> None:
    settings = Settings(_env_file=None, sr_mode="fake", database_url=TEST_DATABASE_URL)  # type: ignore[call-arg]
    app = create_app(settings=settings)
    assert isinstance(app.state.sr_source, FakeSource)
```

`backend/tests/api/conftest.py`:
```python
from collections.abc import Callable
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from tabernas.config import Settings
from tabernas.main import create_app
from tabernas.sr.source import SrSource
from tests.support import TEST_DATABASE_URL, StubSource

FIXED_NOW = datetime(2026, 9, 27, 20, 0)
MakeClient = Callable[..., TestClient]


@pytest.fixture
def make_client(session_factory: sessionmaker[Session]) -> MakeClient:
    def _make(source: SrSource | None = None) -> TestClient:
        settings = Settings(_env_file=None, sr_mode="fake", database_url=TEST_DATABASE_URL)  # type: ignore[call-arg]
        app = create_app(
            settings=settings,
            sr_source=source if source is not None else StubSource(),
            session_factory=session_factory,
            clock=lambda: FIXED_NOW,
        )
        return TestClient(app, raise_server_exceptions=False)

    return _make


@pytest.fixture
def client(make_client: MakeClient) -> TestClient:
    return make_client()
```

`backend/tests/api/test_health.py`:
```python
from datetime import datetime

from fastapi.testclient import TestClient

from tabernas.config import Settings
from tabernas.db.session import make_engine, make_session_factory
from tabernas.main import create_app
from tabernas.sr.source import SrUnavailableError
from tests.api.conftest import MakeClient
from tests.support import READ_ONLY_INFO, TEST_DATABASE_URL, StubSource


def test_health_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {"status": "ok", "db": "ok"},
        "error": None,
        "meta": None,
    }


def test_health_reports_database_down() -> None:
    unreachable = make_session_factory(make_engine("postgresql+psycopg://x:x@127.0.0.1:1/none"))
    app = create_app(
        settings=Settings(_env_file=None, sr_mode="fake", database_url=TEST_DATABASE_URL),  # type: ignore[call-arg]
        sr_source=StubSource(),
        session_factory=unreachable,
        clock=lambda: datetime(2026, 9, 27, 20, 0),
    )
    body = TestClient(app, raise_server_exceptions=False).get("/health").json()
    assert body["data"] == {"status": "degraded", "db": "error"}


def test_health_sr_reports_server(client: TestClient) -> None:
    data = client.get("/health/sr").json()["data"]
    assert data["mode"] == "fake"
    assert data["version"] == "12.0.4100.1"
    assert data["is_sysadmin"] is False


def test_health_sr_refuses_writable_login(make_client: MakeClient) -> None:
    writable = READ_ONLY_INFO.model_copy(update={"is_denywriter": False})
    response = make_client(StubSource(info=writable)).get("/health/sr")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "SR_NOT_READONLY"


def test_health_sr_unavailable(make_client: MakeClient) -> None:
    response = make_client(StubSource(error=SrUnavailableError("x"))).get("/health/sr")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SR_UNAVAILABLE"
    assert "Tailscale" in response.json()["error"]["message"]
```

`backend/tests/api/test_errors.py`:
```python
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tabernas.domain.validation import DomainValidationError
from tabernas.repos.errors import ConflictError, NotFoundError
from tabernas.sr.source import SrUnavailableError
from tests.api.conftest import MakeClient

ERRORS: dict[str, Exception] = {
    "validation": DomainValidationError("Dato malo"),
    "missing": NotFoundError("No existe"),
    "conflict": ConflictError("Choca"),
    "sr": SrUnavailableError("x"),
    "crash": RuntimeError("secret detail"),
}


@pytest.fixture
def boom_client(make_client: MakeClient) -> TestClient:
    client = make_client()
    app = cast(FastAPI, client.app)

    def boom(kind: str) -> None:
        raise ERRORS[kind]

    def typed(number: int) -> int:
        return number

    app.add_api_route("/boom/{kind}", boom)
    app.add_api_route("/typed/{number}", typed)
    return client


@pytest.mark.parametrize(
    ("kind", "status", "code", "message"),
    [
        ("validation", 422, "VALIDATION_ERROR", "Dato malo"),
        ("missing", 404, "NOT_FOUND", "No existe"),
        ("conflict", 409, "CONFLICT", "Choca"),
        ("sr", 503, "SR_UNAVAILABLE", "No se pudo leer SoftRestaurant. Revisa Tailscale."),
    ],
)
def test_mapped_errors_use_the_envelope(
    boom_client: TestClient, kind: str, status: int, code: str, message: str
) -> None:
    response = boom_client.get(f"/boom/{kind}")
    assert response.status_code == status
    assert response.json() == {
        "success": False,
        "data": None,
        "error": {"code": code, "message": message},
        "meta": None,
    }


def test_unhandled_error_hides_details(boom_client: TestClient) -> None:
    response = boom_client.get("/boom/crash")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL"
    assert "secret" not in response.text


def test_request_validation_error_lists_fields(boom_client: TestClient) -> None:
    response = boom_client.get("/typed/abc")
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["meta"]["errors"][0]["loc"] == ["path", "number"]


def test_unknown_route_is_404_envelope(client: TestClient) -> None:
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
```

- [ ] **Step 3: Correr y verificar que fallan**

Run: `uv run pytest tests/test_main.py tests/api -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'tabernas.main'`

- [ ] **Step 4: Implementar la base de la API**

`backend/src/tabernas/api/envelope.py`:
```python
"""Common response envelope: {success, data, error, meta}."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorBody(BaseModel):
    code: str
    message: str


class Envelope(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    error: ErrorBody | None = None
    meta: dict[str, Any] | None = None


def ok(data: T, meta: dict[str, Any] | None = None) -> Envelope[T]:
    return Envelope[T](success=True, data=data, meta=meta)
```

`backend/src/tabernas/api/errors.py`:
```python
"""Maps exceptions to enveloped JSON errors. Details stay in the server log."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from tabernas.api.envelope import Envelope, ErrorBody
from tabernas.domain.validation import DomainValidationError
from tabernas.repos.errors import ConflictError, NotFoundError
from tabernas.sr.source import SrNotReadOnlyError, SrUnavailableError

logger = logging.getLogger(__name__)

Handler = Callable[[Request, Exception], Awaitable[JSONResponse]]

SR_UNAVAILABLE_MESSAGE = "No se pudo leer SoftRestaurant. Revisa Tailscale."
_HTTP_CODES = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}
# (exception, status, code, fixed message or None to use str(exc))
_MAPPED: tuple[tuple[type[Exception], int, str, str | None], ...] = (
    (DomainValidationError, 422, "VALIDATION_ERROR", None),
    (NotFoundError, 404, "NOT_FOUND", None),
    (ConflictError, 409, "CONFLICT", None),
    (SrUnavailableError, 503, "SR_UNAVAILABLE", SR_UNAVAILABLE_MESSAGE),
    (SrNotReadOnlyError, 500, "SR_NOT_READONLY", None),
)


def error_response(
    status_code: int, code: str, message: str, meta: dict[str, Any] | None = None
) -> JSONResponse:
    body = Envelope[None](success=False, error=ErrorBody(code=code, message=message), meta=meta)
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


def _mapped(status_code: int, code: str, fixed_message: str | None) -> Handler:
    async def handler(request: Request, exc: Exception) -> JSONResponse:
        return error_response(status_code, code, fixed_message or str(exc))

    return handler


async def _request_validation(request: Request, exc: Exception) -> JSONResponse:
    errors = exc.errors() if isinstance(exc, RequestValidationError) else []
    fields = [{"loc": [str(part) for part in e["loc"]], "msg": e["msg"]} for e in errors]
    return error_response(422, "VALIDATION_ERROR", "Datos inválidos", {"errors": fields})


async def _http(request: Request, exc: Exception) -> JSONResponse:
    status = exc.status_code if isinstance(exc, StarletteHTTPException) else 500
    detail = exc.detail if isinstance(exc, StarletteHTTPException) else "Error"
    return error_response(status, _HTTP_CODES.get(status, "HTTP_ERROR"), str(detail))


async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return error_response(500, "INTERNAL", "Error interno del servidor")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _request_validation)
    app.add_exception_handler(StarletteHTTPException, _http)
    for exc_type, status_code, code, message in _MAPPED:
        app.add_exception_handler(exc_type, _mapped(status_code, code, message))
    app.add_exception_handler(Exception, _unhandled)
```

`backend/src/tabernas/api/deps.py`:
```python
"""Request-scoped dependencies. The session commits before the response is sent."""

from collections.abc import Callable, Iterator
from datetime import datetime
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session, sessionmaker

from tabernas.config import Settings
from tabernas.sr.source import SrSource


def get_session(request: Request) -> Iterator[Session]:
    factory: sessionmaker[Session] = request.app.state.session_factory
    with factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def get_sr_source(request: Request) -> SrSource:
    return request.app.state.sr_source


def get_clock(request: Request) -> Callable[[], datetime]:
    return request.app.state.clock


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


# scope="function": commit runs right after the route returns, before the response is
# sent, so a failed commit becomes an error response instead of a silent loss.
SessionDep = Annotated[Session, Depends(get_session, scope="function")]
SrSourceDep = Annotated[SrSource, Depends(get_sr_source)]
ClockDep = Annotated[Callable[[], datetime], Depends(get_clock)]
AppSettingsDep = Annotated[Settings, Depends(get_app_settings)]
```

`backend/src/tabernas/api/schemas.py`:
```python
"""Shared request-schema helpers."""

from typing import Any, ClassVar, Self

from pydantic import BaseModel, ConfigDict, model_validator


class PatchModel(BaseModel):
    """PATCH body: unknown fields are rejected; null only where NULLABLE allows it."""

    model_config = ConfigDict(extra="forbid")
    NULLABLE: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def _reject_nulls(self) -> Self:
        nulls = sorted(
            field
            for field in self.model_fields_set
            if getattr(self, field) is None and field not in self.NULLABLE
        )
        if nulls:
            raise ValueError(f"Estos campos no pueden ser nulos: {', '.join(nulls)}")
        return self

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)
```

`backend/src/tabernas/api/routes/health.py`:
```python
import logging

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from tabernas.api.deps import AppSettingsDep, SessionDep, SrSourceDep
from tabernas.api.envelope import Envelope, ok
from tabernas.sr.source import SrNotReadOnlyError

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


class HealthOut(BaseModel):
    status: str
    db: str


class SrHealthOut(BaseModel):
    mode: str
    server: str
    instance: str
    version: str
    edition: str
    database: str
    login: str
    is_datareader: bool
    is_denywriter: bool
    is_sysadmin: bool


@router.get("/health")
def health(session: SessionDep) -> Envelope[HealthOut]:
    try:
        session.execute(text("SELECT 1"))
        db = "ok"
    except SQLAlchemyError:
        logger.exception("Database health check failed")
        session.rollback()
        db = "error"
    return ok(HealthOut(status="ok" if db == "ok" else "degraded", db=db))


@router.get("/health/sr")
def health_sr(source: SrSourceDep, settings: AppSettingsDep) -> Envelope[SrHealthOut]:
    info = source.server_info()
    if not info.read_only:
        raise SrNotReadOnlyError(
            "El login de SoftRestaurant puede escribir; usa reportes_ro (solo lectura)"
        )
    return ok(SrHealthOut(mode=settings.sr_mode, **info.model_dump()))
```

`backend/src/tabernas/api/routes/__init__.py`:
```python
from fastapi import APIRouter

from tabernas.api.routes import health

ROUTERS: list[APIRouter] = [health.router]
```

`backend/src/tabernas/main.py`:
```python
"""FastAPI application factory. Run with: uvicorn --factory tabernas.main:create_app"""

from collections.abc import Callable
from datetime import datetime, tzinfo
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from tabernas.api.errors import register_error_handlers
from tabernas.api.routes import ROUTERS
from tabernas.config import Settings, get_settings
from tabernas.db.session import make_engine, make_session_factory
from tabernas.sr import build_sr_source
from tabernas.sr.source import SrSource


def local_clock(
    tz_name: str, now: Callable[[tzinfo], datetime] = datetime.now
) -> Callable[[], datetime]:
    """Naive local time in the business timezone, comparable with SR's naive datetimes."""
    zone = ZoneInfo(tz_name)
    return lambda: now(zone).replace(tzinfo=None)


def create_app(
    *,
    settings: Settings | None = None,
    sr_source: SrSource | None = None,
    session_factory: sessionmaker[Session] | None = None,
    clock: Callable[[], datetime] | None = None,
) -> FastAPI:
    resolved = settings or get_settings()
    app = FastAPI(title="Tabernas Cerveceras API", version="0.1.0")
    app.state.settings = resolved
    app.state.sr_source = sr_source if sr_source is not None else build_sr_source(resolved)
    app.state.session_factory = session_factory or make_session_factory(
        make_engine(resolved.database_url)
    )
    app.state.clock = clock or local_clock(resolved.app_timezone)
    register_error_handlers(app)
    for router in ROUTERS:
        app.include_router(router)
    return app
```

- [ ] **Step 5: Correr y verificar que pasan**

Run: `uv run pytest -v && uv run ruff check . && uv run ruff format --check . && uv run pyright`
Expected: todos PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/tabernas/api backend/src/tabernas/main.py backend/tests
git commit -m "feat: add API envelope, error mapping and health endpoints

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 14: API de empleados (con importación desde SR) y settings

**Files:**
- Create: `backend/src/tabernas/api/routes/employees.py`, `api/routes/settings.py`,
  `backend/tests/api/test_employees.py`, `backend/tests/api/test_settings.py`
- Modify: `backend/src/tabernas/api/routes/__init__.py`

**Interfaces:**
- Consumes: `EmployeeRepo`, `SettingsRepo` (Task 11); deps y `PatchModel` (Task 13).
- Produces (HTTP, todas con sobre):
  - `GET /employees?active_only=` → `list[EmployeeOut]`; `POST /employees` (201) →
    `EmployeeOut`; `GET /employees/{id}`; `PATCH /employees/{id}`.
  - `GET /employees/sr-preview` → `list[SrEmployeeOut{sr_id, name, visible, imported}]`.
  - `POST /employees/import-from-sr` body `{sr_ids: list[int]}` (201) → los creados.
  - `GET /settings`, `PUT /settings` → `SettingsBody{entry_time_kitchen, entry_time_other, tolerance_minutes}`.
  - `EmployeeOut{id, sr_id, short_name, rh_name, area, applies_lateness, tracks_attendance, active}`.

- [ ] **Step 1: Escribir los tests (fallan)**

`backend/tests/api/test_employees.py`:
```python
from fastapi.testclient import TestClient

from tabernas.sr.source import SrEmployee, SrUnavailableError
from tests.api.conftest import MakeClient
from tests.support import StubSource

SR_EMPLOYEES = [
    SrEmployee(sr_id=6, name="EMPLEADO A", kind=1, visible=True),
    SrEmployee(sr_id=11, name="EMPLEADO B", kind=1, visible=True),
]


def test_create_list_get_patch(client: TestClient) -> None:
    response = client.post(
        "/employees", json={"sr_id": 101, "short_name": "EMPLEADO A", "area": "KITCHEN"}
    )
    assert response.status_code == 201
    employee = response.json()["data"]
    assert (employee["area"], employee["active"], employee["rh_name"]) == ("KITCHEN", True, None)
    assert client.get("/employees").json()["data"] == [employee]
    assert client.get(f"/employees/{employee['id']}").json()["data"] == employee
    patched = client.patch(f"/employees/{employee['id']}", json={"rh_name": "APELLIDO NOMBRE"})
    assert patched.json()["data"]["rh_name"] == "APELLIDO NOMBRE"


def test_active_only_filter(client: TestClient) -> None:
    created = client.post("/employees", json={"short_name": "EMPLEADO A"}).json()["data"]
    client.patch(f"/employees/{created['id']}", json={"active": False})
    assert client.get("/employees", params={"active_only": True}).json()["data"] == []


def test_missing_employee_is_404(client: TestClient) -> None:
    response = client.get("/employees/999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_duplicate_sr_id_is_409(client: TestClient) -> None:
    client.post("/employees", json={"sr_id": 101, "short_name": "EMPLEADO A"})
    response = client.post("/employees", json={"sr_id": 101, "short_name": "OTRO"})
    assert response.status_code == 409


def test_invalid_payloads_are_422(client: TestClient) -> None:
    assert client.post("/employees", json={"short_name": "X", "area": "BAR"}).status_code == 422
    assert client.post("/employees", json={"short_name": ""}).status_code == 422
    created = client.post("/employees", json={"short_name": "X"}).json()["data"]
    url = f"/employees/{created['id']}"
    assert client.patch(url, json={"sr_id": 5}).status_code == 422
    assert client.patch(url, json={"short_name": None}).status_code == 422
    assert client.patch(url, json={"rh_name": None}).status_code == 200


def test_sr_preview_marks_imported(make_client: MakeClient) -> None:
    client = make_client(StubSource(employees=SR_EMPLOYEES))
    client.post("/employees", json={"sr_id": 6, "short_name": "EMPLEADO A"})
    data = client.get("/employees/sr-preview").json()["data"]
    assert [(d["sr_id"], d["name"], d["imported"]) for d in data] == [
        (6, "EMPLEADO A", True),
        (11, "EMPLEADO B", False),
    ]


def test_import_from_sr_is_idempotent(make_client: MakeClient) -> None:
    client = make_client(StubSource(employees=SR_EMPLOYEES))
    first = client.post("/employees/import-from-sr", json={"sr_ids": [11, 6]})
    assert first.status_code == 201
    assert [(e["sr_id"], e["short_name"], e["area"]) for e in first.json()["data"]] == [
        (6, "EMPLEADO A", "OTHER"),
        (11, "EMPLEADO B", "OTHER"),
    ]
    again = client.post("/employees/import-from-sr", json={"sr_ids": [6, 11]})
    assert again.json()["data"] == []


def test_import_unknown_sr_id_is_422(make_client: MakeClient) -> None:
    client = make_client(StubSource(employees=SR_EMPLOYEES))
    response = client.post("/employees/import-from-sr", json={"sr_ids": [6, 99]})
    assert response.status_code == 422
    assert "99" in response.json()["error"]["message"]


def test_sr_down_is_503(make_client: MakeClient) -> None:
    client = make_client(StubSource(error=SrUnavailableError("x")))
    assert client.get("/employees/sr-preview").status_code == 503
```

`backend/tests/api/test_settings.py`:
```python
from fastapi.testclient import TestClient

DEFAULTS = {"entry_time_kitchen": "16:30", "entry_time_other": "16:40", "tolerance_minutes": 10}


def test_get_defaults(client: TestClient) -> None:
    assert client.get("/settings").json()["data"] == DEFAULTS


def test_put_round_trip(client: TestClient) -> None:
    wanted = {"entry_time_kitchen": "16:00", "entry_time_other": "16:15", "tolerance_minutes": 5}
    assert client.put("/settings", json=wanted).json()["data"] == wanted
    assert client.get("/settings").json()["data"] == wanted


def test_invalid_settings_are_422(client: TestClient) -> None:
    bad_values = (
        {"entry_time_kitchen": "25:00"},
        {"entry_time_other": "4:40"},
        {"tolerance_minutes": 61},
    )
    for bad in bad_values:
        response = client.put("/settings", json={**DEFAULTS, **bad})
        assert response.status_code == 422, bad
    assert client.get("/settings").json()["data"] == DEFAULTS
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `uv run pytest tests/api/test_employees.py tests/api/test_settings.py -v`
Expected: FAIL con 404 en todas las rutas (aún no existen).

- [ ] **Step 3: Implementar**

`backend/src/tabernas/api/routes/employees.py`:
```python
from typing import ClassVar

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from tabernas.api.deps import SessionDep, SrSourceDep
from tabernas.api.envelope import Envelope, ok
from tabernas.api.schemas import PatchModel
from tabernas.domain.types import Area, Employee
from tabernas.domain.validation import DomainValidationError
from tabernas.repos.employees import EmployeeRepo

router = APIRouter(prefix="/employees", tags=["employees"])


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sr_id: int | None
    short_name: str
    rh_name: str | None
    area: Area
    applies_lateness: bool
    tracks_attendance: bool
    active: bool


class EmployeeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sr_id: int | None = None
    short_name: str = Field(min_length=1, max_length=80)
    rh_name: str | None = Field(default=None, max_length=160)
    area: Area = Area.OTHER
    applies_lateness: bool = True
    tracks_attendance: bool = True


class EmployeeUpdate(PatchModel):
    NULLABLE: ClassVar[frozenset[str]] = frozenset({"rh_name"})

    short_name: str | None = Field(default=None, min_length=1, max_length=80)
    rh_name: str | None = Field(default=None, max_length=160)
    area: Area | None = None
    applies_lateness: bool | None = None
    tracks_attendance: bool | None = None
    active: bool | None = None


class SrEmployeeOut(BaseModel):
    sr_id: int
    name: str
    visible: bool
    imported: bool


class ImportRequest(BaseModel):
    sr_ids: list[int] = Field(min_length=1)


def _out(employee: Employee) -> EmployeeOut:
    return EmployeeOut.model_validate(employee)


@router.get("")
def list_employees(session: SessionDep, active_only: bool = False) -> Envelope[list[EmployeeOut]]:
    return ok([_out(e) for e in EmployeeRepo(session).find_all(active_only=active_only)])


@router.post("", status_code=201)
def create_employee(body: EmployeeCreate, session: SessionDep) -> Envelope[EmployeeOut]:
    return ok(_out(EmployeeRepo(session).create(**body.model_dump())))


@router.get("/sr-preview")
def sr_preview(session: SessionDep, source: SrSourceDep) -> Envelope[list[SrEmployeeOut]]:
    existing = EmployeeRepo(session).existing_sr_ids()
    return ok(
        [
            SrEmployeeOut(
                sr_id=e.sr_id, name=e.name, visible=e.visible, imported=e.sr_id in existing
            )
            for e in sorted(source.fetch_employees(), key=lambda e: e.sr_id)
        ]
    )


@router.post("/import-from-sr", status_code=201)
def import_from_sr(
    body: ImportRequest, session: SessionDep, source: SrSourceDep
) -> Envelope[list[EmployeeOut]]:
    available = {e.sr_id: e for e in source.fetch_employees()}
    unknown = sorted(set(body.sr_ids) - set(available))
    if unknown:
        raise DomainValidationError(f"Ids SR no encontrados: {', '.join(map(str, unknown))}")
    repo = EmployeeRepo(session)
    existing = repo.existing_sr_ids()
    created = [
        repo.create(
            sr_id=sr_id,
            short_name=available[sr_id].name[:80] or f"SR {sr_id}",
            rh_name=None,
            area=Area.OTHER,
            applies_lateness=True,
            tracks_attendance=True,
        )
        for sr_id in sorted(set(body.sr_ids))
        if sr_id not in existing
    ]
    return ok([_out(e) for e in created])


@router.get("/{employee_id}")
def get_employee(employee_id: int, session: SessionDep) -> Envelope[EmployeeOut]:
    return ok(_out(EmployeeRepo(session).find_by_id(employee_id)))


@router.patch("/{employee_id}")
def update_employee(
    employee_id: int, body: EmployeeUpdate, session: SessionDep
) -> Envelope[EmployeeOut]:
    return ok(_out(EmployeeRepo(session).update(employee_id, body.changes())))
```

`backend/src/tabernas/api/routes/settings.py`:
```python
from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel, Field

from tabernas.api.deps import SessionDep
from tabernas.api.envelope import Envelope, ok
from tabernas.domain.types import AttendanceSettings
from tabernas.domain.validation import MAX_TOLERANCE_MINUTES, format_hhmm, parse_hhmm
from tabernas.repos.settings import SettingsRepo

router = APIRouter(prefix="/settings", tags=["settings"])

HHMM = Annotated[str, Field(pattern=r"^\d{2}:\d{2}$", examples=["16:40"])]


class SettingsBody(BaseModel):
    entry_time_kitchen: HHMM
    entry_time_other: HHMM
    tolerance_minutes: int = Field(ge=0, le=MAX_TOLERANCE_MINUTES)


def _body(settings: AttendanceSettings) -> SettingsBody:
    return SettingsBody(
        entry_time_kitchen=format_hhmm(settings.entry_time_kitchen),
        entry_time_other=format_hhmm(settings.entry_time_other),
        tolerance_minutes=settings.tolerance_minutes,
    )


@router.get("")
def read_settings(session: SessionDep) -> Envelope[SettingsBody]:
    return ok(_body(SettingsRepo(session).get()))


@router.put("")
def write_settings(body: SettingsBody, session: SessionDep) -> Envelope[SettingsBody]:
    wanted = AttendanceSettings(
        entry_time_kitchen=parse_hhmm(body.entry_time_kitchen),
        entry_time_other=parse_hhmm(body.entry_time_other),
        tolerance_minutes=body.tolerance_minutes,
    )
    return ok(_body(SettingsRepo(session).save(wanted)))
```

`backend/src/tabernas/api/routes/__init__.py`:
```python
from fastapi import APIRouter

from tabernas.api.routes import employees, health, settings

ROUTERS: list[APIRouter] = [health.router, employees.router, settings.router]
```

- [ ] **Step 4: Correr y verificar que pasan**

Run: `uv run pytest tests/api -v && uv run ruff check . && uv run pyright`
Expected: todos PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tabernas/api backend/tests/api
git commit -m "feat: add employee (with SR import) and settings endpoints

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 15: API de reglas de descanso, excepciones (con cambio de descanso) y justificaciones

**Files:**
- Create: `backend/src/tabernas/api/routes/rest_rules.py`, `api/routes/exceptions.py`,
  `api/routes/justifications.py`, `backend/tests/api/test_rest_rules.py`,
  `backend/tests/api/test_exceptions.py`, `backend/tests/api/test_justifications.py`
- Modify: `backend/src/tabernas/api/routes/__init__.py`

**Interfaces:**
- Consumes: repos de Task 12; `PatchModel`, deps (Task 13); `validate_range` (Task 3).
- Produces (HTTP, con sobre; `from`/`to` son fechas ISO inclusivas):
  - `GET /rest-rules?employee_id=`, `POST /rest-rules` (201), `PATCH /rest-rules/{id}`,
    `DELETE /rest-rules/{id}` → `RestRuleOut{id, employee_id, fixed_weekday, extra_weekday, double_rest_anchor, valid_from, valid_to}`.
  - `GET /exceptions?from&to&employee_id=`, `POST /exceptions` (201),
    `POST /exceptions/rest-swap` (201, body `{employee_id, absent_day, worked_day, comment}` → lista de 2),
    `PATCH /exceptions/{id}`, `DELETE /exceptions/{id}` →
    `ExceptionOut{id, kind, employee_id, date_from, date_to, rh_type, comment}`.
  - `GET /justifications?from&to&employee_id=` (`from`/`to` obligatorios),
    `POST /justifications` (201), `PATCH /justifications/{id}`, `DELETE /justifications/{id}` →
    `JustificationOut{id, employee_id, day, incident, reason, rh_type}`.
  - `DELETE` responde 200 con `data: null`.

- [ ] **Step 1: Escribir los tests (fallan)**

`backend/tests/api/test_rest_rules.py`:
```python
from fastapi.testclient import TestClient


def _employee(client: TestClient) -> int:
    return client.post("/employees", json={"short_name": "EMPLEADO A"}).json()["data"]["id"]


def _rule(employee_id: int, **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "employee_id": employee_id,
        "fixed_weekday": 1,
        "extra_weekday": 0,
        "double_rest_anchor": "2026-09-28",
        "valid_from": "2026-01-01",
    }
    return {**body, **overrides}


def test_crud(client: TestClient) -> None:
    employee_id = _employee(client)
    created = client.post("/rest-rules", json=_rule(employee_id))
    assert created.status_code == 201
    rule = created.json()["data"]
    assert rule["valid_to"] is None
    listed = client.get("/rest-rules", params={"employee_id": employee_id}).json()["data"]
    assert listed == [rule]
    patched = client.patch(f"/rest-rules/{rule['id']}", json={"valid_to": "2026-12-31"})
    assert patched.json()["data"]["valid_to"] == "2026-12-31"
    assert client.delete(f"/rest-rules/{rule['id']}").json() == {
        "success": True,
        "data": None,
        "error": None,
        "meta": None,
    }
    assert client.get("/rest-rules").json()["data"] == []


def test_errors(client: TestClient) -> None:
    employee_id = _employee(client)
    client.post("/rest-rules", json=_rule(employee_id))
    assert client.post("/rest-rules", json=_rule(employee_id)).status_code == 409
    assert client.post("/rest-rules", json=_rule(999)).status_code == 404
    tuesday = _rule(employee_id, double_rest_anchor="2026-09-29", valid_from="2027-01-01")
    assert client.post("/rest-rules", json=tuesday).status_code == 422
    assert client.post("/rest-rules", json=_rule(employee_id, fixed_weekday=7)).status_code == 422
    assert client.patch("/rest-rules/1", json={"fixed_weekday": None}).status_code == 422
```

`backend/tests/api/test_exceptions.py`:
```python
from fastapi.testclient import TestClient


def _employee(client: TestClient) -> int:
    return client.post("/employees", json={"short_name": "EMPLEADO A"}).json()["data"]["id"]


def _single_day(kind: str, employee_id: int | None, day: str, **extra: object) -> dict[str, object]:
    return {"kind": kind, "employee_id": employee_id, "date_from": day, "date_to": day, **extra}


def test_store_closure_for_everyone(client: TestClient) -> None:
    body = {
        "kind": "STORE_CLOSED",
        "date_from": "2026-12-24",
        "date_to": "2026-12-25",
        "comment": "Navidad",
    }
    created = client.post("/exceptions", json=body)
    assert created.status_code == 201
    assert created.json()["data"]["employee_id"] is None
    week = client.get("/exceptions", params={"from": "2026-12-21", "to": "2026-12-27"})
    assert [e["comment"] for e in week.json()["data"]] == ["Navidad"]
    later = client.get("/exceptions", params={"from": "2026-12-28", "to": "2026-12-31"})
    assert later.json()["data"] == []


def test_invalid_exceptions_are_422(client: TestClient) -> None:
    employee_id = _employee(client)
    closure_with_employee = _single_day("STORE_CLOSED", employee_id, "2026-09-24")
    absence_without_type = _single_day("WORK_TO_ABSENCE", employee_id, "2026-09-24")
    assert client.post("/exceptions", json=closure_with_employee).status_code == 422
    assert client.post("/exceptions", json=absence_without_type).status_code == 422


def test_rest_swap_creates_both_and_is_atomic(client: TestClient) -> None:
    employee_id = _employee(client)
    swap = {"employee_id": employee_id, "absent_day": "2026-09-23", "worked_day": "2026-09-29"}
    created = client.post("/exceptions/rest-swap", json=swap)
    assert created.status_code == 201
    assert [(e["kind"], e["rh_type"]) for e in created.json()["data"]] == [
        ("WORK_TO_ABSENCE", "DESCANSO"),
        ("REST_TO_WORK", None),
    ]
    clash = {"employee_id": employee_id, "absent_day": "2026-09-30", "worked_day": "2026-09-29"}
    assert client.post("/exceptions/rest-swap", json=clash).status_code == 409
    listed = client.get("/exceptions", params={"from": "2026-09-21", "to": "2026-10-04"})
    assert len(listed.json()["data"]) == 2


def test_patch_and_delete(client: TestClient) -> None:
    employee_id = _employee(client)
    body = _single_day("WORK_TO_ABSENCE", employee_id, "2026-09-23", rh_type="VACACIONES")
    created = client.post("/exceptions", json=body).json()["data"]
    url = f"/exceptions/{created['id']}"
    patched = client.patch(url, json={"date_to": "2026-09-25", "comment": "Vacaciones"})
    data = patched.json()["data"]
    assert (data["date_to"], data["comment"]) == ("2026-09-25", "Vacaciones")
    assert client.patch(url, json={"kind": "STORE_CLOSED"}).status_code == 422
    assert client.delete(url).status_code == 200
    assert client.delete(url).status_code == 404
```

`backend/tests/api/test_justifications.py`:
```python
from fastapi.testclient import TestClient

WEEK = {"from": "2026-09-21", "to": "2026-09-27"}


def _employee(client: TestClient) -> int:
    return client.post("/employees", json={"short_name": "EMPLEADO A"}).json()["data"]["id"]


def test_create_with_default_rh_type_and_list(client: TestClient) -> None:
    employee_id = _employee(client)
    body = {
        "employee_id": employee_id,
        "day": "2026-09-23",
        "incident": "ABSENT",
        "reason": "Enfermo",
    }
    created = client.post("/justifications", json=body)
    assert created.status_code == 201
    assert created.json()["data"]["rh_type"] == "FALTA_JUSTIFICADA"
    assert client.get("/justifications", params=WEEK).json()["data"] == [created.json()["data"]]
    assert client.post("/justifications", json=body).status_code == 409


def test_list_requires_a_bounded_range(client: TestClient) -> None:
    assert client.get("/justifications").status_code == 422
    too_long = {"from": "2026-01-01", "to": "2026-12-31"}
    assert client.get("/justifications", params=too_long).status_code == 422


def test_patch_validates_rh_type_and_delete(client: TestClient) -> None:
    employee_id = _employee(client)
    body = {"employee_id": employee_id, "day": "2026-09-23", "incident": "LATE", "reason": "x"}
    created = client.post("/justifications", json=body).json()["data"]
    url = f"/justifications/{created['id']}"
    assert client.patch(url, json={"rh_type": "VACACIONES"}).status_code == 422
    assert client.patch(url, json={"reason": ""}).status_code == 422
    assert client.patch(url, json={"reason": "Tráfico"}).json()["data"]["reason"] == "Tráfico"
    assert client.delete(url).status_code == 200
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `uv run pytest tests/api/test_rest_rules.py tests/api/test_exceptions.py tests/api/test_justifications.py -v`
Expected: FAIL (rutas inexistentes → 404).

- [ ] **Step 3: Implementar**

`backend/src/tabernas/api/routes/rest_rules.py`:
```python
from datetime import date
from typing import ClassVar

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from tabernas.api.deps import SessionDep
from tabernas.api.envelope import Envelope, ok
from tabernas.api.schemas import PatchModel
from tabernas.domain.types import RestRule
from tabernas.repos.rest_rules import RestRuleRepo

router = APIRouter(prefix="/rest-rules", tags=["rest-rules"])


class RestRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    fixed_weekday: int
    extra_weekday: int
    double_rest_anchor: date
    valid_from: date
    valid_to: date | None


class RestRuleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_id: int
    fixed_weekday: int = Field(ge=0, le=6)
    extra_weekday: int = Field(ge=0, le=6)
    double_rest_anchor: date
    valid_from: date
    valid_to: date | None = None


class RestRuleUpdate(PatchModel):
    NULLABLE: ClassVar[frozenset[str]] = frozenset({"valid_to"})

    fixed_weekday: int | None = Field(default=None, ge=0, le=6)
    extra_weekday: int | None = Field(default=None, ge=0, le=6)
    double_rest_anchor: date | None = None
    valid_from: date | None = None
    valid_to: date | None = None


def _out(rule: RestRule) -> RestRuleOut:
    return RestRuleOut.model_validate(rule)


@router.get("")
def list_rules(session: SessionDep, employee_id: int | None = None) -> Envelope[list[RestRuleOut]]:
    return ok([_out(r) for r in RestRuleRepo(session).find_all(employee_id=employee_id)])


@router.post("", status_code=201)
def create_rule(body: RestRuleCreate, session: SessionDep) -> Envelope[RestRuleOut]:
    return ok(_out(RestRuleRepo(session).create(**body.model_dump())))


@router.patch("/{rule_id}")
def update_rule(rule_id: int, body: RestRuleUpdate, session: SessionDep) -> Envelope[RestRuleOut]:
    return ok(_out(RestRuleRepo(session).update(rule_id, body.changes())))


@router.delete("/{rule_id}")
def delete_rule(rule_id: int, session: SessionDep) -> Envelope[None]:
    RestRuleRepo(session).delete(rule_id)
    return ok(None)
```

`backend/src/tabernas/api/routes/exceptions.py`:
```python
from datetime import date
from typing import Annotated, ClassVar

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field

from tabernas.api.deps import SessionDep
from tabernas.api.envelope import Envelope, ok
from tabernas.api.schemas import PatchModel
from tabernas.domain.types import ExceptionKind, RhType, ScheduleException
from tabernas.repos.exceptions import ExceptionRepo

router = APIRouter(prefix="/exceptions", tags=["exceptions"])

Comment = Annotated[str, Field(max_length=500)]


class ExceptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: ExceptionKind
    employee_id: int | None
    date_from: date
    date_to: date
    rh_type: RhType | None
    comment: str


class ExceptionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ExceptionKind
    employee_id: int | None = None
    date_from: date
    date_to: date
    rh_type: RhType | None = None
    comment: Comment = ""


class ExceptionUpdate(PatchModel):
    NULLABLE: ClassVar[frozenset[str]] = frozenset({"rh_type"})

    date_from: date | None = None
    date_to: date | None = None
    rh_type: RhType | None = None
    comment: Comment | None = None


class RestSwapCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_id: int
    absent_day: date
    worked_day: date
    comment: Comment = ""


def _out(exception: ScheduleException) -> ExceptionOut:
    return ExceptionOut.model_validate(exception)


@router.get("")
def list_exceptions(
    session: SessionDep,
    start: Annotated[date | None, Query(alias="from")] = None,
    end: Annotated[date | None, Query(alias="to")] = None,
    employee_id: int | None = None,
) -> Envelope[list[ExceptionOut]]:
    found = ExceptionRepo(session).find_all(start=start, end=end, employee_id=employee_id)
    return ok([_out(e) for e in found])


@router.post("", status_code=201)
def create_exception(body: ExceptionCreate, session: SessionDep) -> Envelope[ExceptionOut]:
    return ok(_out(ExceptionRepo(session).create(**body.model_dump())))


@router.post("/rest-swap", status_code=201)
def create_rest_swap(body: RestSwapCreate, session: SessionDep) -> Envelope[list[ExceptionOut]]:
    created = ExceptionRepo(session).create_rest_swap(**body.model_dump())
    return ok([_out(e) for e in created])


@router.patch("/{exception_id}")
def update_exception(
    exception_id: int, body: ExceptionUpdate, session: SessionDep
) -> Envelope[ExceptionOut]:
    return ok(_out(ExceptionRepo(session).update(exception_id, body.changes())))


@router.delete("/{exception_id}")
def delete_exception(exception_id: int, session: SessionDep) -> Envelope[None]:
    ExceptionRepo(session).delete(exception_id)
    return ok(None)
```

`backend/src/tabernas/api/routes/justifications.py`:
```python
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field

from tabernas.api.deps import SessionDep
from tabernas.api.envelope import Envelope, ok
from tabernas.api.schemas import PatchModel
from tabernas.domain.periods import validate_range
from tabernas.domain.types import Incident, Justification, RhType
from tabernas.repos.justifications import JustificationRepo

router = APIRouter(prefix="/justifications", tags=["justifications"])

Reason = Annotated[str, Field(min_length=1, max_length=500)]


class JustificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    day: date
    incident: Incident
    reason: str
    rh_type: RhType


class JustificationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_id: int
    day: date
    incident: Incident
    reason: Reason
    rh_type: RhType | None = None


class JustificationUpdate(PatchModel):
    reason: Reason | None = None
    rh_type: RhType | None = None


def _out(justification: Justification) -> JustificationOut:
    return JustificationOut.model_validate(justification)


@router.get("")
def list_justifications(
    session: SessionDep,
    start: Annotated[date, Query(alias="from")],
    end: Annotated[date, Query(alias="to")],
    employee_id: int | None = None,
) -> Envelope[list[JustificationOut]]:
    validate_range(start, end)
    found = JustificationRepo(session).find_all(start=start, end=end, employee_id=employee_id)
    return ok([_out(j) for j in found])


@router.post("", status_code=201)
def create_justification(
    body: JustificationCreate, session: SessionDep
) -> Envelope[JustificationOut]:
    return ok(_out(JustificationRepo(session).create(**body.model_dump())))


@router.patch("/{justification_id}")
def update_justification(
    justification_id: int, body: JustificationUpdate, session: SessionDep
) -> Envelope[JustificationOut]:
    return ok(_out(JustificationRepo(session).update(justification_id, body.changes())))


@router.delete("/{justification_id}")
def delete_justification(justification_id: int, session: SessionDep) -> Envelope[None]:
    JustificationRepo(session).delete(justification_id)
    return ok(None)
```

`backend/src/tabernas/api/routes/__init__.py`:
```python
from fastapi import APIRouter

from tabernas.api.routes import employees, exceptions, health, justifications, rest_rules, settings

ROUTERS: list[APIRouter] = [
    health.router,
    employees.router,
    settings.router,
    rest_rules.router,
    exceptions.router,
    justifications.router,
]
```

- [ ] **Step 4: Correr y verificar que pasan**

Run: `uv run pytest tests/api -v && uv run ruff check . && uv run pyright`
Expected: todos PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tabernas/api backend/tests/api
git commit -m "feat: add rest rule, exception (with rest swap) and justification endpoints

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 16: Servicio de asistencia, datos demo y endpoints de calendario/incidencias/resumen

**Files:**
- Create: `backend/src/tabernas/services/__init__.py` (vacío),
  `backend/src/tabernas/services/attendance.py`, `backend/src/tabernas/demo.py`,
  `backend/src/tabernas/api/routes/attendance.py`, `backend/tests/services/__init__.py`,
  `backend/tests/services/test_attendance_service.py`, `backend/tests/test_demo.py`,
  `backend/tests/api/test_attendance.py`
- Modify: `backend/src/tabernas/api/routes/__init__.py`

**Interfaces:**
- Consumes: dominio completo (Tasks 3–7); repos (Tasks 11–12); `SrSource` (Task 8);
  `FAKE_EMPLOYEES`, `FAKE_DOUBLE_REST_ANCHOR`, `FakeSource` (Task 9); deps (Task 13);
  `StubSource`, `make_employee` (tests).
- Produces:
  - `AttendanceReport(start, end, employees: tuple[Employee, ...] (activos, por nombre), results: tuple[DayResult, ...], rh_rows: tuple[RhRow, ...], warnings: tuple[AttendanceWarning, ...])`.
  - `AttendanceService(session, source, clock).build(start, end) -> AttendanceReport`
    (consulta SR solo en `[start, min(end, hoy)]`; no consulta si todo es futuro).
  - `tabernas.demo.seed_demo_data(session) -> list[Employee]` (idempotente).
  - HTTP: `GET /attendance/calendar?from&to` → `CalendarOut{start, end, employees: list[EmployeeRef], days: list[DayOut], warnings: list[WarningOut]}`;
    `GET /attendance/incidents?from&to` → `IncidentsOut{start, end, incidents: list[DayOut], rh_rows: list[RhRowOut], warnings}`;
    `GET /attendance/summary?from&to&group=week|month` → `list[SummaryOut]`.
  - `DayOut{employee_id, day, planned, outcome, checkin, minutes_late, rh_type, justification_id, comment}`,
    `EmployeeRef{id, short_name, rh_name, area}`, `WarningOut{code, employee_id, day, detail}`,
    `RhRowOut{employee_id, name, day, rh_type, comment}`,
    `SummaryOut{employee_id, period, worked, late, late_justified, absent, absent_justified, justified_by_type: dict[RhType, int], unresolved}`.

- [ ] **Step 1: Escribir los tests (fallan)**

`backend/tests/services/test_attendance_service.py`:
```python
from datetime import date, datetime

from sqlalchemy.orm import Session

from tabernas.domain.types import Employee, Incident, Outcome, RhType, WarningCode
from tabernas.repos.justifications import JustificationRepo
from tabernas.repos.rest_rules import RestRuleRepo
from tabernas.services.attendance import AttendanceService
from tabernas.sr.source import SrCheckin
from tests.repos.helpers import make_employee
from tests.support import StubSource

WEEK_39 = (date(2026, 9, 21), date(2026, 9, 27))


def setup_employee(session: Session) -> Employee:
    employee = make_employee(session, 7, short_name="EMPLEADO G")
    RestRuleRepo(session).create(
        employee_id=employee.id,
        fixed_weekday=1,
        extra_weekday=0,
        double_rest_anchor=date(2026, 9, 28),
        valid_from=date(2026, 1, 1),
        valid_to=None,
    )
    return employee


def test_range_crossing_today_reads_sr_only_until_today(session: Session) -> None:
    # Review Focus #1
    setup_employee(session)
    source = StubSource()
    thursday_noon = datetime(2026, 9, 24, 12, 0)
    report = AttendanceService(session, source, lambda: thursday_noon).build(*WEEK_39)
    assert source.calls == [(date(2026, 9, 21), date(2026, 9, 24))]
    outcomes = {r.day.day: r.outcome for r in report.results}
    assert outcomes[24] == Outcome.PENDING
    assert {outcomes[25], outcomes[26], outcomes[27]} == {Outcome.FUTURE}


def test_future_range_does_not_call_sr(session: Session) -> None:
    setup_employee(session)
    source = StubSource()
    AttendanceService(session, source, lambda: datetime(2026, 9, 24, 12, 0)).build(
        date(2026, 10, 5), date(2026, 10, 11)
    )
    assert source.calls == []


def test_full_week_end_to_end(session: Session) -> None:
    employee = setup_employee(session)
    checkins = [
        SrCheckin(sr_id=7, at=datetime(2026, 9, 22, 16, 45)),  # Tuesday = rest day
        SrCheckin(sr_id=7, at=datetime(2026, 9, 23, 16, 51)),  # late by 11 minutes
        SrCheckin(sr_id=7, at=datetime(2026, 9, 24, 16, 40)),  # on time
    ]
    JustificationRepo(session).create(
        employee_id=employee.id,
        day=date(2026, 9, 21),
        incident=Incident.ABSENT,
        reason="Enfermo",
        rh_type=RhType.INCAPACIDAD,
    )
    report = AttendanceService(
        session, StubSource(checkins=checkins), lambda: datetime(2026, 9, 27, 20, 0)
    ).build(*WEEK_39)
    assert [r.outcome for r in report.results] == [
        Outcome.ABSENT,
        Outcome.UNREGISTERED_CHANGE,
        Outcome.LATE,
        Outcome.OK,
        Outcome.ABSENT,
        Outcome.ABSENT,
        Outcome.ABSENT,
    ]
    assert [(row.day.day, row.rh_type) for row in report.rh_rows] == [
        (21, RhType.INCAPACIDAD),
        (23, RhType.RETARDO),
        (25, RhType.FALTA_INJUSTIFICADA),
        (26, RhType.FALTA_INJUSTIFICADA),
        (27, RhType.FALTA_INJUSTIFICADA),
    ]
    assert [w.code for w in report.warnings] == [WarningCode.MISSING_RH_NAME]
```

`backend/tests/test_demo.py`:
```python
from datetime import date, datetime

from sqlalchemy.orm import Session

from tabernas.demo import seed_demo_data
from tabernas.domain.types import Outcome, WarningCode
from tabernas.repos.employees import EmployeeRepo
from tabernas.services.attendance import AttendanceService
from tabernas.sr.fake_source import FakeSource


def test_seed_is_idempotent(session: Session) -> None:
    assert len(seed_demo_data(session)) == 7
    assert seed_demo_data(session) == []
    manager = next(e for e in EmployeeRepo(session).find_all() if e.sr_id == 100)
    assert (manager.tracks_attendance, manager.applies_lateness) == (False, False)


def test_seeded_data_matches_fake_source(session: Session) -> None:
    seed_demo_data(session)
    today = date(2026, 9, 27)
    report = AttendanceService(
        session, FakeSource(today=lambda: today), lambda: datetime(2026, 9, 27, 20, 0)
    ).build(date(2026, 9, 1), today)
    codes = {w.code for w in report.warnings}
    assert WarningCode.NO_REST_RULE not in codes
    assert WarningCode.UNMAPPED_CHECKIN not in codes
    assert Outcome.LATE in {r.outcome for r in report.results}
```

`backend/tests/api/test_attendance.py`:
```python
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from tabernas.demo import seed_demo_data
from tabernas.sr.fake_source import FakeSource
from tabernas.sr.source import SrUnavailableError
from tests.api.conftest import MakeClient
from tests.support import StubSource

WEEK = {"from": "2026-09-21", "to": "2026-09-27"}
INCIDENT_OUTCOMES = {"LATE", "ABSENT", "UNREGISTERED_CHANGE", "JUSTIFIED"}


@pytest.fixture
def demo_client(session_factory: sessionmaker[Session], make_client: MakeClient) -> TestClient:
    with session_factory() as session:
        seed_demo_data(session)
        session.commit()
    return make_client(FakeSource(today=lambda: date(2026, 9, 27)))


def test_calendar_has_one_day_per_employee(demo_client: TestClient) -> None:
    data = demo_client.get("/attendance/calendar", params=WEEK).json()["data"]
    assert (data["start"], data["end"]) == ("2026-09-21", "2026-09-27")
    assert len(data["employees"]) == 7
    assert len(data["days"]) == 49
    assert not {w["code"] for w in data["warnings"]} & {"NO_REST_RULE", "UNMAPPED_CHECKIN"}


def test_incidents_and_rh_rows_are_consistent(demo_client: TestClient) -> None:
    data = demo_client.get("/attendance/incidents", params=WEEK).json()["data"]
    assert {d["outcome"] for d in data["incidents"]} <= INCIDENT_OUTCOMES
    incident_keys = {(d["employee_id"], d["day"]) for d in data["incidents"]}
    assert data["rh_rows"]
    assert {(r["employee_id"], r["day"]) for r in data["rh_rows"]} <= incident_keys


def test_monthly_summary(demo_client: TestClient) -> None:
    params = {"from": "2026-09-01", "to": "2026-09-30", "group": "month"}
    data = demo_client.get("/attendance/summary", params=params).json()["data"]
    assert [s["period"] for s in data] == ["2026-09"] * 7
    assert all(isinstance(s["justified_by_type"], dict) for s in data)


def test_bad_ranges_are_422(client: TestClient) -> None:
    assert client.get("/attendance/calendar", params={"from": "2026-09-21"}).status_code == 422
    reversed_range = {"from": "2026-09-27", "to": "2026-09-21"}
    assert client.get("/attendance/calendar", params=reversed_range).status_code == 422
    too_long = {"from": "2026-01-01", "to": "2026-12-31"}
    assert client.get("/attendance/incidents", params=too_long).status_code == 422


def test_sr_down_is_503(make_client: MakeClient) -> None:
    client = make_client(StubSource(error=SrUnavailableError("x")))
    response = client.get("/attendance/calendar", params=WEEK)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SR_UNAVAILABLE"
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `uv run pytest tests/services tests/test_demo.py tests/api/test_attendance.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'tabernas.services'`

- [ ] **Step 3: Implementar el servicio y la semilla demo**

`backend/src/tabernas/services/attendance.py`:
```python
"""Builds attendance reports. The only place that joins Postgres config, SR and the domain."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy.orm import Session

from tabernas.domain.compare import compare
from tabernas.domain.justify import apply_justifications
from tabernas.domain.periods import validate_range
from tabernas.domain.planning import planned_calendar
from tabernas.domain.rh import to_rh_rows
from tabernas.domain.types import AttendanceWarning, Checkin, DayResult, Employee, RhRow
from tabernas.repos.employees import EmployeeRepo
from tabernas.repos.exceptions import ExceptionRepo
from tabernas.repos.justifications import JustificationRepo
from tabernas.repos.rest_rules import RestRuleRepo
from tabernas.repos.settings import SettingsRepo
from tabernas.sr.source import SrSource


@dataclass(frozen=True)
class AttendanceReport:
    start: date
    end: date
    employees: tuple[Employee, ...]
    results: tuple[DayResult, ...]
    rh_rows: tuple[RhRow, ...]
    warnings: tuple[AttendanceWarning, ...]


class AttendanceService:
    def __init__(
        self, session: Session, source: SrSource, clock: Callable[[], datetime]
    ) -> None:
        self._session = session
        self._source = source
        self._clock = clock

    def build(self, start: date, end: date) -> AttendanceReport:
        validate_range(start, end)
        now = self._clock()
        today = now.date()
        employees = EmployeeRepo(self._session).find_all()
        planned, plan_warnings = planned_calendar(
            employees,
            RestRuleRepo(self._session).find_all(),
            ExceptionRepo(self._session).find_all(start=start, end=end),
            start,
            end,
        )
        compared, compare_warnings = compare(
            planned,
            employees,
            self._checkins(start, end, today),
            SettingsRepo(self._session).get(),
            today,
            now,
        )
        results, justify_warnings = apply_justifications(
            compared, JustificationRepo(self._session).find_all(start=start, end=end)
        )
        rows, rh_warnings = to_rh_rows(results, employees)
        return AttendanceReport(
            start=start,
            end=end,
            employees=tuple(e for e in employees if e.active),  # repo orders by name
            results=tuple(results),
            rh_rows=tuple(rows),
            warnings=(*plan_warnings, *compare_warnings, *justify_warnings, *rh_warnings),
        )

    def _checkins(self, start: date, end: date, today: date) -> list[Checkin]:
        if start > today:
            return []
        fetched = self._source.fetch_checkins(start, min(end, today))
        return [Checkin(sr_id=c.sr_id, at=c.at) for c in fetched]
```

`backend/src/tabernas/demo.py`:
```python
"""Synthetic employees and rest rules matching FakeSource. Only for SR_MODE=fake."""

from datetime import date

from sqlalchemy.orm import Session

from tabernas.domain.types import Employee
from tabernas.repos.employees import EmployeeRepo
from tabernas.repos.rest_rules import RestRuleRepo
from tabernas.sr.fake_source import FAKE_DOUBLE_REST_ANCHOR, FAKE_EMPLOYEES

DEMO_RULES_VALID_FROM = date(2024, 1, 1)


def seed_demo_data(session: Session) -> list[Employee]:
    employees = EmployeeRepo(session)
    rules = RestRuleRepo(session)
    existing = employees.existing_sr_ids()
    created: list[Employee] = []
    for fake in FAKE_EMPLOYEES:
        if fake.sr_id in existing:
            continue
        employee = employees.create(
            sr_id=fake.sr_id,
            short_name=fake.name,
            rh_name=f"{fake.name} (RH)",
            area=fake.area,
            applies_lateness=fake.checks_in,
            tracks_attendance=fake.checks_in,
        )
        rules.create(
            employee_id=employee.id,
            fixed_weekday=fake.fixed_rest,
            extra_weekday=fake.extra_rest,
            double_rest_anchor=FAKE_DOUBLE_REST_ANCHOR,
            valid_from=DEMO_RULES_VALID_FROM,
            valid_to=None,
        )
        created.append(employee)
    return created
```

- [ ] **Step 4: Implementar los endpoints**

`backend/src/tabernas/api/routes/attendance.py`:
```python
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from tabernas.api.deps import ClockDep, SessionDep, SrSourceDep
from tabernas.api.envelope import Envelope, ok
from tabernas.domain.summary import EmployeeSummary, Grouping, summarize
from tabernas.domain.types import Area, Outcome, Planned, RhType, WarningCode
from tabernas.services.attendance import AttendanceReport, AttendanceService

router = APIRouter(prefix="/attendance", tags=["attendance"])

StartQuery = Annotated[date, Query(alias="from")]
EndQuery = Annotated[date, Query(alias="to")]
INCIDENT_OUTCOMES = frozenset(
    {Outcome.LATE, Outcome.ABSENT, Outcome.UNREGISTERED_CHANGE, Outcome.JUSTIFIED}
)


class _FromAttributes(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EmployeeRef(_FromAttributes):
    id: int
    short_name: str
    rh_name: str | None
    area: Area


class DayOut(_FromAttributes):
    employee_id: int
    day: date
    planned: Planned
    outcome: Outcome
    checkin: datetime | None
    minutes_late: int | None
    rh_type: RhType | None
    justification_id: int | None
    comment: str


class WarningOut(_FromAttributes):
    code: WarningCode
    employee_id: int | None
    day: date | None
    detail: str


class RhRowOut(_FromAttributes):
    employee_id: int
    name: str
    day: date
    rh_type: RhType
    comment: str


class CalendarOut(BaseModel):
    start: date
    end: date
    employees: list[EmployeeRef]
    days: list[DayOut]
    warnings: list[WarningOut]


class IncidentsOut(BaseModel):
    start: date
    end: date
    incidents: list[DayOut]
    rh_rows: list[RhRowOut]
    warnings: list[WarningOut]


class SummaryOut(BaseModel):
    employee_id: int
    period: str
    worked: int
    late: int
    late_justified: int
    absent: int
    absent_justified: int
    justified_by_type: dict[RhType, int]
    unresolved: int


def get_service(session: SessionDep, source: SrSourceDep, clock: ClockDep) -> AttendanceService:
    return AttendanceService(session, source, clock)


ServiceDep = Annotated[AttendanceService, Depends(get_service)]


def _warnings(report: AttendanceReport) -> list[WarningOut]:
    return [WarningOut.model_validate(w) for w in report.warnings]


def summary_out(summary: EmployeeSummary) -> SummaryOut:
    return SummaryOut(
        employee_id=summary.employee_id,
        period=summary.period,
        worked=summary.worked,
        late=summary.late,
        late_justified=summary.late_justified,
        absent=summary.absent,
        absent_justified=summary.absent_justified,
        justified_by_type=dict(summary.justified_by_type),
        unresolved=summary.unresolved,
    )


@router.get("/calendar")
def calendar(start: StartQuery, end: EndQuery, service: ServiceDep) -> Envelope[CalendarOut]:
    report = service.build(start, end)
    return ok(
        CalendarOut(
            start=report.start,
            end=report.end,
            employees=[EmployeeRef.model_validate(e) for e in report.employees],
            days=[DayOut.model_validate(r) for r in report.results],
            warnings=_warnings(report),
        )
    )


@router.get("/incidents")
def incidents(start: StartQuery, end: EndQuery, service: ServiceDep) -> Envelope[IncidentsOut]:
    report = service.build(start, end)
    return ok(
        IncidentsOut(
            start=report.start,
            end=report.end,
            incidents=[
                DayOut.model_validate(r) for r in report.results if r.outcome in INCIDENT_OUTCOMES
            ],
            rh_rows=[RhRowOut.model_validate(row) for row in report.rh_rows],
            warnings=_warnings(report),
        )
    )


@router.get("/summary")
def summary(
    start: StartQuery, end: EndQuery, service: ServiceDep, group: Grouping = Grouping.WEEK
) -> Envelope[list[SummaryOut]]:
    report = service.build(start, end)
    return ok([summary_out(s) for s in summarize(report.results, group)])
```

En `backend/src/tabernas/api/routes/__init__.py` agrega `attendance` al import y
`attendance.router` al final de `ROUTERS`.

- [ ] **Step 5: Correr y verificar que pasan**

Run: `uv run pytest -v && uv run ruff check . && uv run pyright`
Expected: todos PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/tabernas backend/tests
git commit -m "feat: add attendance service with calendar, incidents and summary endpoints

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 17: Exportación a Excel

**Files:**
- Create: `backend/src/tabernas/export/__init__.py` (vacío), `export/labels.py`,
  `export/xlsx.py`, `backend/tests/export/__init__.py`, `backend/tests/export/test_xlsx.py`
- Modify: `backend/src/tabernas/api/routes/attendance.py` (endpoint),
  `backend/tests/api/test_attendance.py` (test del endpoint)

**Interfaces:**
- Consumes: `AttendanceReport` (Task 16), `EmployeeSummary`, `summarize`, `Grouping`
  (Task 7), `days` (Task 3).
- Produces: `OUTCOME_LABELS: dict[Outcome, str]`, `OUTCOME_FILLS: dict[Outcome, str]`,
  `RH_LABELS: dict[RhType, str]`, `DAY_ABBR`; `XLSX_MEDIA_TYPE`;
  `build_workbook(report, summaries) -> bytes` (hojas `Calendario`, `Incidencias RH`,
  `Resumen`); `cell_text(result) -> str`;
  HTTP `GET /attendance/export.xlsx?from&to` → archivo `asistencia_<from>_<to>.xlsx`.

- [ ] **Step 1: Escribir los tests (fallan)**

`backend/tests/export/test_xlsx.py`:
```python
from datetime import date, datetime
from io import BytesIO

from openpyxl import load_workbook

from tabernas.domain.summary import Grouping, summarize
from tabernas.domain.types import DayResult, Outcome, Planned, RhRow, RhType
from tabernas.export.labels import OUTCOME_FILLS, OUTCOME_LABELS, RH_LABELS
from tabernas.export.xlsx import build_workbook
from tabernas.services.attendance import AttendanceReport
from tests.domain.factories import employee


def sample_report() -> AttendanceReport:
    results = (
        DayResult(
            1, date(2026, 9, 21), Planned.WORK, Outcome.OK, checkin=datetime(2026, 9, 21, 16, 35)
        ),
        DayResult(1, date(2026, 9, 22), Planned.REST, Outcome.REST),
        DayResult(
            1,
            date(2026, 9, 23),
            Planned.WORK,
            Outcome.LATE,
            checkin=datetime(2026, 9, 23, 16, 55),
            minutes_late=15,
        ),
    )
    return AttendanceReport(
        start=date(2026, 9, 21),
        end=date(2026, 9, 23),
        employees=(employee(1, rh_name="APELLIDO UNO"),),
        results=results,
        rh_rows=(RhRow(1, "APELLIDO UNO", date(2026, 9, 23), RhType.RETARDO, ""),),
        warnings=(),
    )


def values(row: tuple) -> list[object]:
    return [cell.value for cell in row]


def test_workbook_sheets_and_content() -> None:
    report = sample_report()
    content = build_workbook(report, summarize(report.results, Grouping.WEEK))
    workbook = load_workbook(BytesIO(content))
    assert workbook.sheetnames == ["Calendario", "Incidencias RH", "Resumen"]

    calendar = workbook["Calendario"]
    assert values(calendar[1]) == ["Empleado", "Lun 21/09", "Mar 22/09", "Mié 23/09"]
    assert values(calendar[2]) == ["E1", "A tiempo 16:35", "Descanso", "Retardo 16:55"]

    rh = workbook["Incidencias RH"]
    assert values(rh[1]) == ["Nombre en RH", "Fecha", "Tipo", "Comentario"]
    assert values(rh[2])[:3] == ["APELLIDO UNO", datetime(2026, 9, 23), "Retardo"]

    summary = workbook["Resumen"]
    assert values(summary[1]) == [
        "Empleado",
        "Periodo",
        "Días trabajados",
        "Retardos",
        "Retardos justificados",
        "Faltas",
        "Faltas justificadas",
        "Pendientes de resolver",
    ]
    assert values(summary[2]) == ["E1", "2026-W39", 2, 1, 0, 0, 0, 0]


def test_labels_cover_every_enum_value() -> None:
    assert set(OUTCOME_LABELS) == set(Outcome)
    assert set(OUTCOME_FILLS) == set(Outcome)
    assert set(RH_LABELS) == set(RhType)
```

Agrega a `backend/tests/api/test_attendance.py` (con `from io import BytesIO` y
`from openpyxl import load_workbook` en los imports de arriba):
```python
def test_export_xlsx(demo_client: TestClient) -> None:
    response = demo_client.get("/attendance/export.xlsx", params=WEEK)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    disposition = response.headers["content-disposition"]
    assert 'filename="asistencia_2026-09-21_2026-09-27.xlsx"' in disposition
    workbook = load_workbook(BytesIO(response.content))
    assert workbook["Calendario"].max_row == 8  # header + 7 employees
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `uv run pytest tests/export tests/api/test_attendance.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'tabernas.export'`

- [ ] **Step 3: Implementar**

`backend/src/tabernas/export/labels.py`:
```python
"""Spanish labels and colors for user-facing exports."""

from tabernas.domain.types import Outcome, RhType

DAY_ABBR = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")

OUTCOME_LABELS: dict[Outcome, str] = {
    Outcome.OK: "A tiempo",
    Outcome.LATE: "Retardo",
    Outcome.ABSENT: "Falta",
    Outcome.UNREGISTERED_CHANGE: "Cambio sin registrar",
    Outcome.REST: "Descanso",
    Outcome.CLOSED: "Cerrado",
    Outcome.JUSTIFIED: "Justificado",
    Outcome.PENDING: "Pendiente",
    Outcome.FUTURE: "",
}

OUTCOME_FILLS: dict[Outcome, str] = {
    Outcome.OK: "E6F4EA",
    Outcome.LATE: "FFF4CE",
    Outcome.ABSENT: "FDE2E1",
    Outcome.UNREGISTERED_CHANGE: "E8DEF8",
    Outcome.REST: "F1F3F4",
    Outcome.CLOSED: "DADCE0",
    Outcome.JUSTIFIED: "E3F2FD",
    Outcome.PENDING: "FFFFFF",
    Outcome.FUTURE: "FFFFFF",
}

RH_LABELS: dict[RhType, str] = {
    RhType.RETARDO: "Retardo",
    RhType.FALTA_INJUSTIFICADA: "Falta injustificada",
    RhType.FALTA_JUSTIFICADA: "Falta justificada",
    RhType.VACACIONES: "Vacaciones",
    RhType.INCAPACIDAD: "Incapacidad",
    RhType.PERMISO: "Permiso",
    RhType.DESCANSO: "Descanso",
    RhType.NO_CAPTURAR: "No se captura",
}
```

`backend/src/tabernas/export/xlsx.py`:
```python
"""Attendance workbook: calendar grid, HR incident list and per-week summary."""

from collections.abc import Sequence
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.worksheet import Worksheet

from tabernas.domain.periods import days
from tabernas.domain.summary import EmployeeSummary
from tabernas.domain.types import DayResult
from tabernas.export.labels import DAY_ABBR, OUTCOME_FILLS, OUTCOME_LABELS, RH_LABELS
from tabernas.services.attendance import AttendanceReport

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
SUMMARY_HEADER = (
    "Empleado",
    "Periodo",
    "Días trabajados",
    "Retardos",
    "Retardos justificados",
    "Faltas",
    "Faltas justificadas",
    "Pendientes de resolver",
)


def cell_text(result: DayResult) -> str:
    label = OUTCOME_LABELS[result.outcome]
    if result.checkin is None:
        return label
    return f"{label} {result.checkin:%H:%M}".strip()


def build_workbook(report: AttendanceReport, summaries: Sequence[EmployeeSummary]) -> bytes:
    workbook = Workbook()
    calendar = workbook.active
    assert calendar is not None
    _calendar_sheet(calendar, report)
    _rh_sheet(workbook.create_sheet("Incidencias RH"), report)
    _summary_sheet(workbook.create_sheet("Resumen"), report, summaries)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _header(sheet: Worksheet, titles: Sequence[str]) -> None:
    sheet.append(list(titles))
    for cell in sheet[1]:
        cell.font = Font(bold=True)


def _calendar_sheet(sheet: Worksheet, report: AttendanceReport) -> None:
    sheet.title = "Calendario"
    period = days(report.start, report.end)
    _header(sheet, ["Empleado", *(f"{DAY_ABBR[d.weekday()]} {d:%d/%m}" for d in period)])
    by_key = {(r.employee_id, r.day): r for r in report.results}
    for employee in report.employees:
        results = [by_key[(employee.id, d)] for d in period]
        sheet.append([employee.short_name, *(cell_text(r) for r in results)])
        for column, result in enumerate(results, start=2):
            sheet.cell(row=sheet.max_row, column=column).fill = PatternFill(
                "solid", fgColor=OUTCOME_FILLS[result.outcome]
            )


def _rh_sheet(sheet: Worksheet, report: AttendanceReport) -> None:
    _header(sheet, ["Nombre en RH", "Fecha", "Tipo", "Comentario"])
    for row in report.rh_rows:
        sheet.append([row.name, row.day, RH_LABELS[row.rh_type], row.comment])
        sheet.cell(row=sheet.max_row, column=2).number_format = "dd/mm/yyyy"


def _summary_sheet(
    sheet: Worksheet, report: AttendanceReport, summaries: Sequence[EmployeeSummary]
) -> None:
    _header(sheet, SUMMARY_HEADER)
    names = {e.id: e.short_name for e in report.employees}
    for s in summaries:
        sheet.append(
            [
                names.get(s.employee_id, str(s.employee_id)),
                s.period,
                s.worked,
                s.late,
                s.late_justified,
                s.absent,
                s.absent_justified,
                s.unresolved,
            ]
        )
```

Agrega a `backend/src/tabernas/api/routes/attendance.py` (imports arriba:
`from fastapi.responses import Response` y
`from tabernas.export.xlsx import XLSX_MEDIA_TYPE, build_workbook`):
```python
@router.get(
    "/export.xlsx",
    response_class=Response,
    responses={200: {"content": {XLSX_MEDIA_TYPE: {}}, "description": "Libro de Excel"}},
)
def export_xlsx(start: StartQuery, end: EndQuery, service: ServiceDep) -> Response:
    report = service.build(start, end)
    content = build_workbook(report, summarize(report.results, Grouping.WEEK))
    filename = f"asistencia_{start.isoformat()}_{end.isoformat()}.xlsx"
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 4: Correr y verificar que pasan**

Run: `uv run pytest -v && uv run ruff check . && uv run pyright`
Expected: todos PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tabernas backend/tests
git commit -m "feat: export attendance calendar, HR list and summary to Excel

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 18: Scripts de semilla demo y de conciliación contra el export de SR

**Files:**
- Create: `backend/src/tabernas/sr/export_reader.py`, `backend/tests/sr/test_export_reader.py`,
  `scripts/seed_demo.py`, `scripts/reconcile_attendance.py`

**Interfaces:**
- Consumes: `seed_demo_data` (Task 16), `PymssqlSource` (Task 8), `Settings`,
  `make_engine`/`make_session_factory` (Task 10).
- Produces: `read_attendance_export(path: Path, start: date, end: date) -> Counter[int]`
  (checadas por id SR dentro del rango); scripts ejecutables con
  `uv run --project backend scripts/<script>.py` desde la raíz.

Formato real del export de SR (verificado, sin datos): primera hoja; unas filas de
título; una fila de encabezado con `FECHA, CLAVEEMPLEADO, NOMBRE, ENTRADA, SALIDA,
HORASTRABAJADAS`; filas de datos con `CLAVEEMPLEADO` entero y `ENTRADA` datetime. La
extensión es `.XLS` pero el contenido es xlsx, y openpyxl rechaza la extensión: hay que
abrirlo desde bytes.

- [ ] **Step 1: Escribir los tests (fallan)**

`backend/tests/sr/test_export_reader.py`:
```python
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import pytest
from openpyxl import Workbook

from tabernas.sr.export_reader import read_attendance_export

HEADER = ["FECHA", "CLAVEEMPLEADO", "NOMBRE", "ENTRADA", "SALIDA", "HORASTRABAJADAS"]


def write_export(path: Path, rows: list[list[object]]) -> Path:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    for row in [["REPORTE DEMO", datetime(2026, 9, 28)], ["EMPRESA DEMO"], HEADER, *rows]:
        sheet.append(row)
    workbook.save(path)
    return path


def test_counts_checkins_per_employee_within_range(tmp_path: Path) -> None:
    export = write_export(
        tmp_path / "ASISTENCIA.XLS",  # SR's misleading extension
        [
            [datetime(2026, 8, 1), 6, "EMPLEADO A", datetime(2026, 8, 1, 16, 41, 31), "/  /", 0],
            [datetime(2026, 8, 2), 6, "EMPLEADO A", datetime(2026, 8, 2, 16, 30, 33), "/  /", 0],
            [datetime(2026, 8, 2), 11, "EMPLEADO B", datetime(2026, 8, 2, 16, 35), "/  /", 0],
            [datetime(2026, 9, 1), 11, "EMPLEADO B", datetime(2026, 9, 1, 16, 35), "/  /", 0],
            [None, None, "TOTAL", None, None, None],
        ],
    )
    counts = read_attendance_export(export, date(2026, 8, 1), date(2026, 8, 31))
    assert counts == Counter({6: 2, 11: 1})


def test_rejects_files_without_the_header(tmp_path: Path) -> None:
    path = tmp_path / "other.xlsx"
    Workbook().save(path)
    with pytest.raises(ValueError, match="export de asistencia"):
        read_attendance_export(path, date(2026, 8, 1), date(2026, 8, 31))
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `uv run pytest tests/sr/test_export_reader.py -v`
Expected: FAIL con `ModuleNotFoundError`

- [ ] **Step 3: Implementar el lector y los scripts**

`backend/src/tabernas/sr/export_reader.py`:
```python
"""Reads SR's attendance export for reconciliation. SR's '.XLS' files are really xlsx."""

from collections import Counter
from collections.abc import Iterator, Sequence
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook

CLAVE_HEADER = "CLAVEEMPLEADO"
ENTRADA_HEADER = "ENTRADA"


def read_attendance_export(path: Path, start: date, end: date) -> Counter[int]:
    # Load from bytes: openpyxl refuses the .XLS extension even though the content is xlsx.
    workbook = load_workbook(BytesIO(path.read_bytes()), read_only=True, data_only=True)
    rows = workbook.worksheets[0].iter_rows(values_only=True)
    clave_col, entrada_col = _find_header(rows)
    counts: Counter[int] = Counter()
    for row in rows:  # the iterator continues after the header row
        if len(row) <= max(clave_col, entrada_col):
            continue
        clave, entrada = row[clave_col], row[entrada_col]
        in_range = isinstance(entrada, datetime) and start <= entrada.date() <= end
        if isinstance(clave, int) and in_range:
            counts[clave] += 1
    return counts


def _find_header(rows: Iterator[Sequence[object]]) -> tuple[int, int]:
    for row in rows:
        values = list(row)
        if CLAVE_HEADER in values and ENTRADA_HEADER in values:
            return values.index(CLAVE_HEADER), values.index(ENTRADA_HEADER)
    raise ValueError("El archivo no parece un export de asistencia de SR")
```

`scripts/seed_demo.py`:
```python
"""Load synthetic employees and rest rules for SR_MODE=fake (portfolio demo, E2E).

Usage (repo root): uv run --project backend scripts/seed_demo.py
Docker:            docker compose run --rm -e SR_MODE=fake backend python /scripts/seed_demo.py
"""

import sys

from tabernas.config import get_settings
from tabernas.db.session import make_engine, make_session_factory
from tabernas.demo import seed_demo_data


def main() -> int:
    settings = get_settings()
    if settings.sr_mode != "fake":
        print("seed_demo solo corre con SR_MODE=fake (no mezcles datos demo con reales)")
        return 1
    factory = make_session_factory(make_engine(settings.database_url))
    with factory() as session:
        created = seed_demo_data(session)
        session.commit()
    print(f"Empleados demo creados: {len(created)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`scripts/reconcile_attendance.py`:
```python
"""Acceptance check: SR check-ins per employee must equal SR's own attendance export.

Local only (reads live SR and a file from db_examples/). Prints ids and counts, never names.
Usage (repo root):
  uv run --project backend scripts/reconcile_attendance.py \
      --from 2026-08-01 --to 2026-08-31 --export db_examples/ASISTENCIA_EMPLEADOS.XLS
"""

import argparse
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from tabernas.config import Settings
from tabernas.sr.export_reader import read_attendance_export
from tabernas.sr.pymssql_source import PymssqlSource


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="start", type=date.fromisoformat, required=True)
    parser.add_argument("--to", dest="end", type=date.fromisoformat, required=True)
    parser.add_argument("--export", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    expected = read_attendance_export(args.export, args.start, args.end)
    source = PymssqlSource.from_settings(Settings(sr_mode="live"))
    actual = Counter(c.sr_id for c in source.fetch_checkins(args.start, args.end))
    print(f"{'id SR':>6} {'SR':>5} {'export':>7}")
    for sr_id in sorted(set(expected) | set(actual)):
        flag = "" if expected[sr_id] == actual[sr_id] else "  <-- difiere"
        print(f"{sr_id:>6} {actual[sr_id]:>5} {expected[sr_id]:>7}{flag}")
    print(f"{'total':>6} {sum(actual.values()):>5} {sum(expected.values()):>7}")
    if expected != actual:
        print("NO coincide")
        return 1
    print("Coincide 1:1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Correr tests y la conciliación real**

Run: `uv run pytest tests/sr/test_export_reader.py -v`
Expected: PASS.

Run (desde la raíz, con Tailscale):
`uv run --project backend scripts/reconcile_attendance.py --from 2026-08-01 --to 2026-08-31 --export db_examples/ASISTENCIA_EMPLEADOS.XLS`
Expected: `Coincide 1:1`, con el total igual al registrado en
`docs/private/reconciliation.md`. **No copies las cifras a archivos versionados.**

- [ ] **Step 5: Commit**

```bash
git add backend/src/tabernas/sr/export_reader.py backend/tests/sr scripts/seed_demo.py scripts/reconcile_attendance.py
git commit -m "feat: add demo seed and SR attendance reconciliation scripts

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 19: CI, documentación y `docker compose up` desde cero

**Files:**
- Create: `.github/workflows/ci.yml`
- Modify: `CLAUDE.md` (sección Commands)

- [ ] **Step 1: Escribir el workflow**

`.github/workflows/ci.yml`:
```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: tabernas
          POSTGRES_PASSWORD: tabernas
          POSTGRES_DB: tabernas_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U tabernas -d tabernas_test"
          --health-interval 5s --health-timeout 3s --health-retries 10
    defaults:
      run:
        working-directory: backend
    env:
      SR_MODE: fake
      TEST_DATABASE_URL: postgresql+psycopg://tabernas:tabernas@localhost:5432/tabernas_test
    steps:
      - uses: actions/checkout@v7
      - uses: astral-sh/setup-uv@v10
      - run: uv sync --frozen
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run pyright
      - run: uv run pytest --cov --cov-report=term-missing
      - run: uv run coverage report --include="*/tabernas/domain/*" --fail-under=95
```

- [ ] **Step 2: Verificar localmente lo mismo que CI**

Run (desde `backend/`):
`uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest --cov --cov-report=term-missing && uv run coverage report --include="*/tabernas/domain/*" --fail-under=95`
Expected: todo en verde; cobertura total ≥ 80%, dominio ≥ 95%.

- [ ] **Step 3: Actualizar `CLAUDE.md`**

Reemplaza la sección `## Commands` por:
```markdown
## Commands

- Start everything: `docker compose up --build` (API docs at http://127.0.0.1:8000/docs)
- Backend tests (from `backend/`, needs `docker compose up -d db`): `uv run pytest`
- Live SR tests (local only, never CI): `uv run pytest -m sr`
- Lint and types (from `backend/`): `uv run ruff check . && uv run ruff format --check . && uv run pyright`
- Check SR connectivity: `uv run --project backend scripts/check_connection.py`
- Reconcile SR check-ins vs an SR export: `uv run --project backend scripts/reconcile_attendance.py --from YYYY-MM-DD --to YYYY-MM-DD --export db_examples/ASISTENCIA_EMPLEADOS.XLS`
- Demo data (only with `SR_MODE=fake`): `docker compose run --rm -e SR_MODE=fake backend python /scripts/seed_demo.py`
```

- [ ] **Step 4: `docker compose up` desde cero (aceptación #1)**

```bash
cd /Users/didiertm/Documents/Projects/TabernasCerveceras
docker compose down -v
docker compose up --build -d
docker compose ps
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/health/sr
```
Expected: `db` y `backend` healthy; `/health` →
`{"success":true,"data":{"status":"ok","db":"ok"},...}`; `/health/sr` →
`"mode":"live"`, `"is_denywriter":true`, `"is_sysadmin":false`.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml CLAUDE.md
git commit -m "ci: run lint, types and tests with coverage gates

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 20: Aceptación con datos reales (con el gerente)

Esta tarea no escribe código: valida los criterios #2 y #3 del spec. Los datos reales
se capturan por la API (Swagger en http://127.0.0.1:8000/docs) y viven solo en Postgres.

- [ ] **Step 1: Configurar empleados reales**

1. `GET /employees/sr-preview` → confirma los ids de SR.
2. `POST /employees/import-from-sr` con los ids de quienes checan y del gerente.
3. Con `PATCH /employees/{id}`: nombre en RH, `area: KITCHEN` para cocina; para el
   gerente `tracks_attendance: false`, `applies_lateness: false`.
4. `POST /rest-rules` por empleado con el día fijo, el día extra y un lunes de semana
   doble, tomados de `docs/private/reconciliation.md`.
5. Excepciones conocidas del periodo (p. ej. cierre del 2026-09-05 por tormenta con
   `STORE_CLOSED`; olvidos de checar con `PRESENT_NO_CHECKIN`).

- [ ] **Step 2: Revisar una semana real con el gerente (aceptación #3)**

`GET /attendance/incidents?from=2026-09-21&to=2026-09-27` y
`GET /attendance/export.xlsx?from=2026-09-21&to=2026-09-27`.
Pide al usuario que compare la lista con su revisión manual de esa semana. **Detente
aquí y espera su confirmación.** Cualquier diferencia: identifica si es una regla de
negocio no capturada (→ nuevo test de dominio + fix) o configuración (→ corregir por API).

- [ ] **Step 3: Registrar el resultado**

- En `docs/private/reconciliation.md` (no versionado): fecha, semana revisada,
  diferencias encontradas y cómo se resolvieron.
- En `docs/db-map.md`, sección "Asistencia → Conciliación ✅", agrega una línea sin
  cifras: `Verificado también vía API (etapa 1) el 2026-MM-DD: checadas 1:1 con el
  export y una semana de incidencias revisada con el gerente.`

- [ ] **Step 4: Commit**

```bash
git add docs/db-map.md
git commit -m "docs: record stage 1 attendance acceptance

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
