# Etapa 2 · Plan A — Backend del agente de revisión semanal

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un servicio `worker` que cada jueves 17:30 y lunes 09:00 (o bajo demanda vía
API) calcula los hallazgos de asistencia de la semana, le pide a Claude que los explique
y priorice con herramientas de solo lectura y seudónimos, valida la respuesta y guarda
el borrador en Postgres para que el gerente lo revise y apruebe.

**Architecture:** `domain/review.py` calcula los hallazgos con reglas puras sobre la
salida de `AttendanceService` (Etapa 1). `agents/weekly_review/` corre un loop propio
sobre `client.beta.messages.create` detrás del protocolo `MessagesApi`, con cuatro
herramientas de lectura que solo ven `E{id}`; un validador en código garantiza que la
respuesta cubre exactamente los hallazgos. `services/review.py` arma el contexto, llama
al agente y guarda el snapshot en `weekly_review`. La API solo encola y consulta; el
`worker` es el único que ejecuta corridas.

**Tech Stack:** Python 3.12, uv, FastAPI, Pydantic 2, SQLAlchemy 2.1 + Alembic,
Postgres 16 (JSONB), SDK `anthropic` (Messages API beta: `server-side-fallback-2026-07-01`),
modelo `claude-opus-5-5`, pytest + pytest-cov, ruff, pyright, Docker Compose.

**Spec:** [`docs/specs/2026-10-01-etapa-2-revision-semanal-design.md`](../specs/2026-10-01-etapa-2-revision-semanal-design.md)
(leerlo completo antes de empezar). El código de la Etapa 1 que se reutiliza está
descrito en [`docs/specs/2026-09-29-etapa-1-asistencia-design.md`](../specs/2026-09-29-etapa-1-asistencia-design.md).
El frontend (`/revision`, umbrales en Configuración, enlace a `/semana`) es el **Plan B**.

## Global Constraints

- **SR es producción, solo lectura.** Nada de este plan agrega consultas a SR: todo pasa
  por `AttendanceService.build()`, que ya usa `SrSource`.
- **Ningún nombre real sale hacia la API de Anthropic.** Lo que se envía a Claude solo
  identifica empleados como `E{employee.id}`; los textos libres (comentarios) pasan por
  `scrub()` antes de enviarse.
- **El agente no inventa cifras ni hallazgos:** hallazgos y filas RH salen de `domain/`;
  el validador rechaza ids faltantes, repetidos o desconocidos.
- **Repo público:** tests y evaluación usan datos sintéticos (`ANA PRUEBA`, `EMPLEADO A`…).
  La llave `ANTHROPIC_API_KEY` solo vive en `.env`; logs sin llave, sin nombres y sin el
  contenido de los payloads (solo estado y tokens).
- Modelo por defecto `claude-opus-5-5` (`REVIEW_MODEL`), `output_config.effort = "medium"`,
  `max_tokens = 16000`, tope de **8 vueltas**, **1 reintento** de validación,
  `fallbacks: "default"` con beta `server-side-fallback-2026-07-01`.
- Umbrales por defecto: racha `2` días (1–7), retardos en la semana `2` (1–7), semanas
  con retardo `3` de 5 (1–5). Ranuras: jueves `17:30` (semana en curso), lunes `09:00`
  (semana anterior), recuperación si la ranura venció hace ≤ 24 h.
- Fechas y horas de negocio son *naive* en `America/Mexico_City` (el `clock` de la app).
- `REVIEW_AGENT` por defecto `fake` (como `SR_MODE`): CI y la demo nunca llaman a Claude.
- Dataclasses del dominio `frozen=True`; los repos nunca devuelven objetos ORM.
- Funciones < 50 líneas, archivos < 400 líneas.
- Código, identificadores y commits en inglés; textos para el usuario y para Claude en
  español.
- Comandos de backend **desde `backend/`** salvo que se indique. Si sale
  `No module named 'tabernas'`, usar `.venv/bin/python -m pytest` (ver CLAUDE.md).
- Commits `<type>: <description>` cerrando con
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Comentarios libres con nombres** ("Avisó ANA PRUEBA que…") en excepciones o
   justificaciones: deben llegar a Claude ya con seudónimo. → tests en Task 10 y Task 11.
2. **Textos de avisos con nombres** (`MISSING_RH_NAME` trae el nombre corto en `detail`):
   el hallazgo `CONFIG_WARNING` nunca copia `detail`. → test en Task 4.
3. **Mac dormida en el cambio de año ISO:** el lunes 4 de enero de 2027 a las 09:00
   revisa la semana `2026-W53`. → test en Task 5.
4. **Worker que se cae a la mitad:** una fila `RUNNING` colgada no puede bloquear para
   siempre "Generar de nuevo" (409). → tests en Task 7 y Task 15.
5. **Empleado desactivado después del borrador:** el detalle sigue mostrando su nombre
   en la narrativa, hallazgos y filas RH. → test en Task 13.

---

## Estructura de archivos

```
backend/
  pyproject.toml                       + anthropic; marcador `agent`
  alembic/versions/0002_weekly_review.py
  src/tabernas/
    config.py                          + anthropic_api_key, review_agent, review_model
    domain/
      periods.py                       + validate_iso_week()
      review_types.py                  enums, Finding, Narrative, ReviewContext, WeeklyReview…
      review.py                        find_findings()
      review_schedule.py               last_due_slot(), slot_to_enqueue()
    db/models.py                       + WeeklyReviewRow
    repos/
      review_settings.py               ReviewSettingsRepo
      review_codec.py                  snapshot ↔ JSON
      reviews.py                       ReviewRepo
    agents/
      __init__.py
      pseudonyms.py                    alias, parse_alias, render, scrub, contains_known_name
      weekly_review/
        __init__.py
        agent.py                       ToolCall, ModelTurn, MessagesApi, AgentOutcome, ReviewAgent
        schema.py                      NARRATIVE_SCHEMA, parse_narrative()
        validate.py                    validate_narrative()
        tools.py                       TOOL_DEFINITIONS, ReviewTools
        prompt.py                      SYSTEM_PROMPT, opening_message(), retry_message()
        runner.py                      LiveReviewAgent
        anthropic_api.py               AnthropicMessages (adaptador del SDK)
        fake.py                        FakeReviewAgent
        factory.py                     build_review_agent(), UnconfiguredReviewAgent
    services/review.py                 build_context(), run_review(), review_detail(), render_narrative()
    sr/source.py                       + SR_UNAVAILABLE_MESSAGE (movido desde api/errors.py)
    api/routes/reviews.py              /reviews
    api/routes/settings.py             + /settings/review
    worker.py                          schedule_due(), run_next(), fail_stale(), tick(), main()
  tests/
    conftest.py                        TRUNCATE incluye weekly_review
    domain/test_review_types.py, test_review.py, test_review_schedule.py
    repos/test_review_settings.py, test_reviews.py
    agents/helpers.py, test_pseudonyms.py, test_schema_validate.py, test_tools.py,
      test_runner.py, test_anthropic_api.py, test_fake_and_factory.py
    services/test_review_service.py
    api/test_reviews.py, test_settings.py (+ /settings/review)
    test_worker.py
    eval/__init__.py, scenarios.py, test_weekly_review_eval.py   (@pytest.mark.agent)
docker-compose.yml                     + servicio worker
.env.example                           + REVIEW_AGENT, ANTHROPIC_API_KEY, REVIEW_MODEL
.github/workflows/ci.yml               REVIEW_AGENT=fake explícito
CLAUDE.md, docs/plan.md                estado, layout, comandos
```

---
### Task 1: Dependencia `anthropic` y configuración del agente

**Files:**
- Modify: `backend/pyproject.toml`, `backend/uv.lock` (vía `uv add`)
- Modify: `backend/src/tabernas/config.py`
- Modify: `.env.example`
- Test: `backend/tests/test_config.py`

**Interfaces:**
- Produces: `Settings.anthropic_api_key: SecretStr` (default vacío),
  `Settings.review_agent: Literal["live", "fake"]` (default `"fake"`),
  `Settings.review_model: str` (default `"claude-opus-5-5"`).

- [ ] **Step 1: Write the failing tests**

En `backend/tests/test_config.py`, reemplazar el fixture `_clean_env` (agrega las tres
variables nuevas) y agregar dos tests al final:

```python
@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "SR_MODE",
        "SR_DB_HOST",
        "SR_DB_PASSWORD",
        "DATABASE_URL",
        "APP_TIMEZONE",
        "REVIEW_AGENT",
        "ANTHROPIC_API_KEY",
        "REVIEW_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)
```

```python
def test_review_agent_defaults_to_fake_without_key() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.review_agent == "fake"
    assert settings.review_model == "claude-opus-5-5"
    assert settings.anthropic_api_key.get_secret_value() == ""


def test_anthropic_key_is_secret() -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        review_agent="live",
        anthropic_api_key="sk-test-123",  # type: ignore[arg-type]
    )
    assert settings.anthropic_api_key.get_secret_value() == "sk-test-123"
    assert "sk-test-123" not in repr(settings)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL con `AttributeError: 'Settings' object has no attribute 'review_agent'`.

- [ ] **Step 3: Add the dependency and the settings**

```bash
uv add anthropic
uv run python -c "import anthropic; print(anthropic.__version__)"
```

Expected: imprime la versión instalada. Solo se usa `client.beta.messages.create(...,
betas=[...], extra_body={...})` y las excepciones `RateLimitError`, `APIStatusError`,
`APIConnectionError`, presentes en todas las versiones recientes.

En `backend/src/tabernas/config.py`, dentro de `Settings`, después de `app_timezone`:

```python
    # Weekly review agent (stage 2). fake = deterministic text, no API calls (demo, CI).
    review_agent: Literal["live", "fake"] = "fake"
    anthropic_api_key: SecretStr = SecretStr("")
    review_model: str = "claude-opus-5-5"
```

Al final de `.env.example`:

```
# Weekly review agent (stage 2). live = call Claude; fake = deterministic text (demo, CI).
# Only the worker uses these. Without a key, live drafts are saved without narrative.
REVIEW_AGENT=live
ANTHROPIC_API_KEY=
REVIEW_MODEL=claude-opus-5-5
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS (todos).

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock backend/src/tabernas/config.py .env.example backend/tests/test_config.py
git commit -m "chore: add anthropic SDK and weekly review agent settings

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Tipos de la revisión semanal y validación de semana ISO

**Files:**
- Create: `backend/src/tabernas/domain/review_types.py`
- Modify: `backend/src/tabernas/domain/periods.py`
- Test: `backend/tests/domain/test_review_types.py`, `backend/tests/domain/test_periods.py`

**Interfaces:**
- Consumes: `DayResult`, `Employee`, `RhRow`, `RhType` de `domain/types.py`;
  `DomainValidationError` de `domain/validation.py`.
- Produces (todo en `tabernas.domain.review_types`):
  - `FindingKind` (StrEnum, en este orden): `REST_DAY_CHECKIN`, `ABSENT_NO_EXCEPTION`,
    `NO_CHECKIN_STREAK`, `REPEATED_LATE`, `CONFIG_WARNING`.
  - `Priority`: `HIGH`, `MEDIUM`, `LOW`. `SuggestedAction`: `JUSTIFY`, `REST_SWAP`,
    `ADD_EXCEPTION`, `FIX_CONFIG`, `NONE`.
  - `ReviewStatus`: `QUEUED`, `RUNNING`, `READY`, `READY_NO_NARRATIVE`, `FAILED`,
    `APPROVED`. `ReviewTrigger`: `THURSDAY`, `MONDAY`, `MANUAL`.
  - `Fact = tuple[str, int | str]`.
  - `Finding(id: str, kind: FindingKind, employee_id: int | None, days: tuple[date, ...],
    facts: tuple[Fact, ...] = ())` con `fact(key) -> int | str | None`.
  - `NarrativeItem(finding_id, priority, explanation, suggested_action)`,
    `Narrative(summary: str, items: tuple[NarrativeItem, ...])`.
  - `ProposedRhRow(employee_id, day, rh_type, comment)` y
    `proposed_rows(rows: Sequence[RhRow]) -> tuple[ProposedRhRow, ...]`.
  - `ReviewSettings(streak_days=2, late_week=2, late_weeks=3)`,
    `DEFAULT_REVIEW_SETTINGS`, `REVIEW_SETTING_LIMITS: dict[str, int]`,
    `validate_review_settings(settings) -> None`.
  - `REVIEW_HISTORY_WEEKS = 8`.
  - `ReviewContext(iso_year, iso_week, start, end, as_of, employees, week_results,
    history_results, rh_rows, findings)` — los campos de colección son tuplas.
  - `ReviewResult(status, as_of, findings, rh_rows, narrative, model, input_tokens,
    output_tokens, error)`.
  - `WeeklyReview(id, iso_year, iso_week, trigger, status, created_at, as_of=None,
    findings=(), rh_rows=(), narrative=None, model=None, input_tokens=None,
    output_tokens=None, error=None, approved_at=None)`.
  - En `tabernas.domain.periods`: `validate_iso_week(year: int, week: int) -> None`
    (lanza `RangeError`, subclase de `DomainValidationError`).

- [ ] **Step 1: Write the failing tests**

`backend/tests/domain/test_review_types.py`:

```python
from datetime import date

import pytest

from tabernas.domain.review_types import (
    DEFAULT_REVIEW_SETTINGS,
    Finding,
    FindingKind,
    ProposedRhRow,
    ReviewSettings,
    proposed_rows,
    validate_review_settings,
)
from tabernas.domain.types import RhRow, RhType
from tabernas.domain.validation import DomainValidationError


def test_finding_kinds_are_listed_in_spec_order() -> None:
    assert list(FindingKind) == [
        FindingKind.REST_DAY_CHECKIN,
        FindingKind.ABSENT_NO_EXCEPTION,
        FindingKind.NO_CHECKIN_STREAK,
        FindingKind.REPEATED_LATE,
        FindingKind.CONFIG_WARNING,
    ]


def test_finding_fact_lookup() -> None:
    finding = Finding(
        id="X", kind=FindingKind.NO_CHECKIN_STREAK, employee_id=1, days=(), facts=(("days", 3),)
    )
    assert finding.fact("days") == 3
    assert finding.fact("missing") is None


def test_proposed_rows_drop_the_name() -> None:
    row = RhRow(
        employee_id=4, name="ALGUIEN", day=date(2026, 9, 23), rh_type=RhType.RETARDO, comment=""
    )
    assert proposed_rows([row]) == (
        ProposedRhRow(employee_id=4, day=date(2026, 9, 23), rh_type=RhType.RETARDO, comment=""),
    )


def test_default_and_boundary_review_settings_are_valid() -> None:
    validate_review_settings(DEFAULT_REVIEW_SETTINGS)
    validate_review_settings(ReviewSettings(streak_days=7, late_week=7, late_weeks=5))
    validate_review_settings(ReviewSettings(streak_days=1, late_week=1, late_weeks=1))


@pytest.mark.parametrize(
    ("settings", "message"),
    [
        (ReviewSettings(streak_days=0), "días seguidos sin checar"),
        (ReviewSettings(streak_days=8), "días seguidos sin checar"),
        (ReviewSettings(late_week=0), "retardos en la semana"),
        (ReviewSettings(late_weeks=6), "semanas con retardo"),
    ],
)
def test_out_of_range_review_settings_are_rejected(
    settings: ReviewSettings, message: str
) -> None:
    with pytest.raises(DomainValidationError, match=message):
        validate_review_settings(settings)
```

En `backend/tests/domain/test_periods.py`, agregar `validate_iso_week` a la lista del
`from tabernas.domain.periods import (...)` (ya importa `pytest` y `RangeError`) y este
test al final:

```python
def test_validate_iso_week_accepts_week_53_only_in_long_years() -> None:
    validate_iso_week(2026, 53)  # 2026 starts on a Thursday: 53 ISO weeks
    with pytest.raises(RangeError, match="Semana ISO inválida"):
        validate_iso_week(2025, 53)
    with pytest.raises(RangeError, match="Semana ISO inválida"):
        validate_iso_week(2026, 0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/domain/test_review_types.py tests/domain/test_periods.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'tabernas.domain.review_types'`
e `ImportError` de `validate_iso_week`.

- [ ] **Step 3: Write the implementation**

`backend/src/tabernas/domain/review_types.py`:

```python
"""Weekly review types (stage 2). Pure data: no database, no HTTP, no Claude."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from tabernas.domain.types import DayResult, Employee, RhRow, RhType
from tabernas.domain.validation import DomainValidationError

REVIEW_HISTORY_WEEKS = 8  # weeks of history the agent may look at (get_employee_history)


class FindingKind(StrEnum):
    """Declaration order is the order findings are listed in (spec §4)."""

    REST_DAY_CHECKIN = "REST_DAY_CHECKIN"
    ABSENT_NO_EXCEPTION = "ABSENT_NO_EXCEPTION"
    NO_CHECKIN_STREAK = "NO_CHECKIN_STREAK"
    REPEATED_LATE = "REPEATED_LATE"
    CONFIG_WARNING = "CONFIG_WARNING"


class Priority(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class SuggestedAction(StrEnum):
    JUSTIFY = "JUSTIFY"
    REST_SWAP = "REST_SWAP"
    ADD_EXCEPTION = "ADD_EXCEPTION"
    FIX_CONFIG = "FIX_CONFIG"
    NONE = "NONE"


class ReviewStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    READY = "READY"
    READY_NO_NARRATIVE = "READY_NO_NARRATIVE"
    FAILED = "FAILED"
    APPROVED = "APPROVED"


class ReviewTrigger(StrEnum):
    THURSDAY = "THURSDAY"
    MONDAY = "MONDAY"
    MANUAL = "MANUAL"


Fact = tuple[str, int | str]


@dataclass(frozen=True)
class Finding:
    id: str
    kind: FindingKind
    employee_id: int | None
    days: tuple[date, ...]
    facts: tuple[Fact, ...] = ()

    def fact(self, key: str) -> int | str | None:
        return dict(self.facts).get(key)


@dataclass(frozen=True)
class NarrativeItem:
    finding_id: str
    priority: Priority
    explanation: str
    suggested_action: SuggestedAction


@dataclass(frozen=True)
class Narrative:
    summary: str
    items: tuple[NarrativeItem, ...]


@dataclass(frozen=True)
class ProposedRhRow:
    """An RH row without the employee's name: names are rendered when the draft is served."""

    employee_id: int
    day: date
    rh_type: RhType
    comment: str


def proposed_rows(rows: Sequence[RhRow]) -> tuple[ProposedRhRow, ...]:
    return tuple(ProposedRhRow(r.employee_id, r.day, r.rh_type, r.comment) for r in rows)


@dataclass(frozen=True)
class ReviewSettings:
    streak_days: int = 2  # consecutive unjustified absences that make a streak
    late_week: int = 2  # unjustified lates in the reviewed week
    late_weeks: int = 3  # weeks with any late among the reviewed week and the 4 before


DEFAULT_REVIEW_SETTINGS = ReviewSettings()
REVIEW_SETTING_LIMITS = {"streak_days": 7, "late_week": 7, "late_weeks": 5}
_SETTING_LABELS = {
    "streak_days": "días seguidos sin checar",
    "late_week": "retardos en la semana",
    "late_weeks": "semanas con retardo",
}


def validate_review_settings(settings: ReviewSettings) -> None:
    for field, maximum in REVIEW_SETTING_LIMITS.items():
        value = getattr(settings, field)
        if not 1 <= value <= maximum:
            raise DomainValidationError(
                f"El umbral de {_SETTING_LABELS[field]} debe estar entre 1 y {maximum}"
            )


@dataclass(frozen=True)
class ReviewContext:
    """Everything the agent may see about one week, computed once by the service."""

    iso_year: int
    iso_week: int
    start: date
    end: date
    as_of: datetime
    employees: tuple[Employee, ...]  # all employees, active or not (pseudonyms, scrub)
    week_results: tuple[DayResult, ...]
    history_results: tuple[DayResult, ...]  # REVIEW_HISTORY_WEEKS weeks before `start`
    rh_rows: tuple[ProposedRhRow, ...]
    findings: tuple[Finding, ...]


@dataclass(frozen=True)
class ReviewResult:
    status: ReviewStatus
    as_of: datetime
    findings: tuple[Finding, ...]
    rh_rows: tuple[ProposedRhRow, ...]
    narrative: Narrative | None
    model: str | None
    input_tokens: int
    output_tokens: int
    error: str | None


@dataclass(frozen=True)
class WeeklyReview:
    id: int
    iso_year: int
    iso_week: int
    trigger: ReviewTrigger
    status: ReviewStatus
    created_at: datetime
    as_of: datetime | None = None
    findings: tuple[Finding, ...] = ()
    rh_rows: tuple[ProposedRhRow, ...] = ()
    narrative: Narrative | None = None
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    error: str | None = None
    approved_at: datetime | None = None
```

En `backend/src/tabernas/domain/periods.py`, después de `iso_week_range`:

```python
def validate_iso_week(year: int, week: int) -> None:
    try:
        date.fromisocalendar(year, week, 1)
    except ValueError as exc:
        raise RangeError(f"Semana ISO inválida: {year}-W{week:02d}") from exc
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/domain -v`
Expected: PASS (los nuevos y todos los de la Etapa 1).

- [ ] **Step 5: Commit**

```bash
git add backend/src/tabernas/domain/review_types.py backend/src/tabernas/domain/periods.py backend/tests/domain/test_review_types.py backend/tests/domain/test_periods.py
git commit -m "feat: add weekly review domain types

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Hallazgos — checada en descanso, faltas y rachas

**Files:**
- Create: `backend/src/tabernas/domain/review.py`
- Test: `backend/tests/domain/test_review.py`

**Interfaces:**
- Consumes: `Finding`, `FindingKind`, `ReviewSettings` (Task 2); `DayResult`, `Outcome`,
  `Planned`, `AttendanceWarning` de `domain/types.py`; `result()` y `WEEK_39` de
  `tests/domain/factories.py`.
- Produces:
  - `finding_id(kind: str, employee_id: int | None, first_day: date | None) -> str`
    → `"KIND:<employee_id o ->:<YYYY-MM-DD o ->"`.
  - `find_findings(week_results, history_results, warnings, settings, start, end)
    -> list[Finding]` (firma definitiva; Task 4 agrega los tipos que faltan).

Reglas de esta tarea (spec §4):
- `REST_DAY_CHECKIN`: cada `UNREGISTERED_CHANGE` de la semana; `facts = (("checkin_time", "HH:MM"),)`.
- `NO_CHECKIN_STREAK`: corridas de ≥ `settings.streak_days` días con `planned == WORK`
  consecutivos en `ABSENT` sin `justification_id`. Los días no laborales (descanso,
  cierre, ausencia justificada por excepción) se saltan sin romper la corrida. Cualquier
  otro día laboral (`OK`, `LATE`, `ABSENT` justificado, `PENDING`, `FUTURE`) la rompe. Se
  reporta si el **último** día cae en la semana; la corrida puede empezar en el
  historial. `facts = (("days", n),)`; `id` con el primer día.
- `ABSENT_NO_EXCEPTION`: cada `ABSENT` sin justificar de la semana que no esté en una
  racha reportada.
- Orden: tipo (orden de `FindingKind`), empleado, primer día, id.

- [ ] **Step 1: Write the failing tests**

`backend/tests/domain/test_review.py`:

```python
from collections.abc import Sequence
from dataclasses import replace
from datetime import date, datetime, timedelta

from tabernas.domain.review import find_findings, finding_id
from tabernas.domain.review_types import (
    DEFAULT_REVIEW_SETTINGS,
    Finding,
    FindingKind,
    ReviewSettings,
)
from tabernas.domain.types import AttendanceWarning, DayResult, Outcome
from tests.domain.factories import WEEK_39, result

START, END = WEEK_39
MON, TUE, WED, THU, FRI, SAT, SUN = (START + timedelta(days=offset) for offset in range(7))
PREV_SAT, PREV_SUN = date(2026, 9, 19), date(2026, 9, 20)


def find(
    week: Sequence[DayResult] = (),
    history: Sequence[DayResult] = (),
    warnings: Sequence[AttendanceWarning] = (),
    settings: ReviewSettings = DEFAULT_REVIEW_SETTINGS,
) -> list[Finding]:
    return find_findings(list(week), list(history), list(warnings), settings, START, END)


def kinds(findings: Sequence[Finding]) -> list[FindingKind]:
    return [f.kind for f in findings]


def test_finding_id_format() -> None:
    assert finding_id(FindingKind.REPEATED_LATE, 4, WED) == "REPEATED_LATE:4:2026-09-23"
    assert finding_id("CONFIG_WARNING/UNMAPPED_CHECKIN", None, None) == (
        "CONFIG_WARNING/UNMAPPED_CHECKIN:-:-"
    )


def test_clean_week_has_no_findings() -> None:
    assert find([result(Outcome.OK, day=d) for d in (MON, WED, THU)]) == []


def test_rest_day_checkin_reports_the_time() -> None:
    checkin = replace(
        result(Outcome.UNREGISTERED_CHANGE, day=TUE), checkin=datetime(2026, 9, 22, 16, 45, 30)
    )
    assert find([checkin]) == [
        Finding(
            id="REST_DAY_CHECKIN:1:2026-09-22",
            kind=FindingKind.REST_DAY_CHECKIN,
            employee_id=1,
            days=(TUE,),
            facts=(("checkin_time", "16:45"),),
        )
    ]


def test_single_unjustified_absence() -> None:
    assert find([result(Outcome.ABSENT, day=WED)]) == [
        Finding(
            id="ABSENT_NO_EXCEPTION:1:2026-09-23",
            kind=FindingKind.ABSENT_NO_EXCEPTION,
            employee_id=1,
            days=(WED,),
        )
    ]


def test_justified_absence_is_not_a_finding() -> None:
    assert find([result(Outcome.ABSENT, day=WED, justification_id=3)]) == []


def test_two_consecutive_absences_are_one_streak() -> None:
    findings = find([result(Outcome.ABSENT, day=WED), result(Outcome.ABSENT, day=THU)])
    assert findings == [
        Finding(
            id="NO_CHECKIN_STREAK:1:2026-09-23",
            kind=FindingKind.NO_CHECKIN_STREAK,
            employee_id=1,
            days=(WED, THU),
            facts=(("days", 2),),
        )
    ]


def test_rest_day_in_the_middle_does_not_break_a_streak() -> None:
    week = [
        result(Outcome.ABSENT, day=MON),
        result(Outcome.REST, day=TUE),
        result(Outcome.ABSENT, day=WED),
    ]
    findings = find(week)
    assert kinds(findings) == [FindingKind.NO_CHECKIN_STREAK]
    assert findings[0].days == (MON, WED)


def test_worked_day_breaks_a_streak() -> None:
    week = [
        result(Outcome.ABSENT, day=MON),
        result(Outcome.OK, day=TUE),
        result(Outcome.ABSENT, day=WED),
    ]
    assert kinds(find(week)) == [FindingKind.ABSENT_NO_EXCEPTION] * 2


def test_justified_absence_breaks_a_streak() -> None:
    week = [
        result(Outcome.ABSENT, day=MON),
        result(Outcome.ABSENT, day=TUE, justification_id=9),
        result(Outcome.ABSENT, day=WED),
    ]
    assert kinds(find(week)) == [FindingKind.ABSENT_NO_EXCEPTION] * 2


def test_streak_can_start_in_the_previous_week() -> None:
    findings = find(
        week=[result(Outcome.ABSENT, day=MON), result(Outcome.OK, day=TUE)],
        history=[result(Outcome.ABSENT, day=PREV_SUN)],
    )
    assert [(f.id, f.days) for f in findings] == [
        ("NO_CHECKIN_STREAK:1:2026-09-20", (PREV_SUN, MON))
    ]


def test_streak_that_ended_last_week_is_not_reported() -> None:
    findings = find(
        week=[result(Outcome.OK, day=MON)],
        history=[result(Outcome.ABSENT, day=PREV_SAT), result(Outcome.ABSENT, day=PREV_SUN)],
    )
    assert findings == []


def test_pending_and_future_days_end_a_streak_and_are_ignored() -> None:
    week = [
        result(Outcome.ABSENT, day=WED),
        result(Outcome.PENDING, day=THU),
        result(Outcome.FUTURE, day=FRI),
    ]
    assert kinds(find(week)) == [FindingKind.ABSENT_NO_EXCEPTION]


def test_streak_length_comes_from_settings() -> None:
    week = [result(Outcome.ABSENT, day=WED), result(Outcome.ABSENT, day=THU)]
    findings = find(week, settings=ReviewSettings(streak_days=3))
    assert kinds(findings) == [FindingKind.ABSENT_NO_EXCEPTION] * 2


def test_findings_are_ordered_and_ids_are_stable() -> None:
    week = [
        result(Outcome.ABSENT, employee_id=2, day=MON),
        replace(
            result(Outcome.UNREGISTERED_CHANGE, employee_id=3, day=TUE),
            checkin=datetime(2026, 9, 22, 16, 45),
        ),
        result(Outcome.ABSENT, employee_id=1, day=WED),
        result(Outcome.ABSENT, employee_id=1, day=THU),
    ]
    first = find(week)
    assert [f.id for f in first] == [
        "REST_DAY_CHECKIN:3:2026-09-22",
        "ABSENT_NO_EXCEPTION:2:2026-09-21",
        "NO_CHECKIN_STREAK:1:2026-09-23",
    ]
    assert find(list(reversed(week))) == first
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/domain/test_review.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'tabernas.domain.review'`.

- [ ] **Step 3: Write the implementation**

`backend/src/tabernas/domain/review.py`:

```python
"""Deterministic weekly-review findings (spec §4). The agent explains them, never creates them."""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import date

from tabernas.domain.review_types import Finding, FindingKind, ReviewSettings
from tabernas.domain.types import AttendanceWarning, DayResult, Outcome, Planned

KIND_ORDER = {kind: index for index, kind in enumerate(FindingKind)}


def finding_id(kind: str, employee_id: int | None, first_day: date | None) -> str:
    employee = "-" if employee_id is None else str(employee_id)
    day = "-" if first_day is None else first_day.isoformat()
    return f"{kind}:{employee}:{day}"


def find_findings(
    week_results: Sequence[DayResult],
    history_results: Sequence[DayResult],
    warnings: Sequence[AttendanceWarning],
    settings: ReviewSettings,
    start: date,
    end: date,
) -> list[Finding]:
    week = [r for r in week_results if start <= r.day <= end]
    history = [r for r in history_results if r.day < start]
    streaks = _streaks([*history, *week], settings.streak_days, start, end)
    in_streak = {(f.employee_id, day) for f in streaks for day in f.days}
    findings = [
        *_rest_day_checkins(week),
        *_absences(week, in_streak),
        *streaks,
    ]
    return sorted(findings, key=_sort_key)


def _sort_key(finding: Finding) -> tuple[int, int, date, str]:
    return (
        KIND_ORDER[finding.kind],
        -1 if finding.employee_id is None else finding.employee_id,
        finding.days[0] if finding.days else date.min,
        finding.id,
    )


def _is_open_absence(result: DayResult) -> bool:
    return result.outcome == Outcome.ABSENT and result.justification_id is None


def _rest_day_checkins(week: Iterable[DayResult]) -> list[Finding]:
    return [
        Finding(
            id=finding_id(FindingKind.REST_DAY_CHECKIN, r.employee_id, r.day),
            kind=FindingKind.REST_DAY_CHECKIN,
            employee_id=r.employee_id,
            days=(r.day,),
            facts=(("checkin_time", r.checkin.strftime("%H:%M")),) if r.checkin else (),
        )
        for r in week
        if r.outcome == Outcome.UNREGISTERED_CHANGE
    ]


def _absences(
    week: Iterable[DayResult], in_streak: set[tuple[int | None, date]]
) -> list[Finding]:
    return [
        Finding(
            id=finding_id(FindingKind.ABSENT_NO_EXCEPTION, r.employee_id, r.day),
            kind=FindingKind.ABSENT_NO_EXCEPTION,
            employee_id=r.employee_id,
            days=(r.day,),
        )
        for r in week
        if _is_open_absence(r) and (r.employee_id, r.day) not in in_streak
    ]


def _streaks(
    results: Sequence[DayResult], min_days: int, start: date, end: date
) -> list[Finding]:
    work_days: defaultdict[int, list[DayResult]] = defaultdict(list)
    for r in sorted(results, key=lambda item: (item.employee_id, item.day)):
        if r.planned == Planned.WORK:
            work_days[r.employee_id].append(r)
    return [
        Finding(
            id=finding_id(FindingKind.NO_CHECKIN_STREAK, employee_id, run[0]),
            kind=FindingKind.NO_CHECKIN_STREAK,
            employee_id=employee_id,
            days=run,
            facts=(("days", len(run)),),
        )
        for employee_id, days in work_days.items()
        for run in _absence_runs(days)
        if len(run) >= min_days and start <= run[-1] <= end
    ]


def _absence_runs(work_days: Sequence[DayResult]) -> list[tuple[date, ...]]:
    """Maximal runs of consecutive unjustified absences among an employee's work days."""
    runs: list[tuple[date, ...]] = []
    current: tuple[date, ...] = ()
    for r in work_days:
        if _is_open_absence(r):
            current = (*current, r.day)
            continue
        if current:
            runs.append(current)
        current = ()
    if current:
        runs.append(current)
    return runs
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/domain/test_review.py -v`
Expected: PASS (14 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/src/tabernas/domain/review.py backend/tests/domain/test_review.py
git commit -m "feat: detect rest-day check-ins, absences and no-check-in streaks

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Hallazgos — retardos repetidos y avisos de configuración

**Files:**
- Modify: `backend/src/tabernas/domain/review.py`
- Test: `backend/tests/domain/test_review.py`

**Interfaces:**
- Consumes: lo de Task 3; `week_monday` de `domain/periods.py`; `WarningCode` de
  `domain/types.py`.
- Produces: `find_findings` ahora también devuelve `REPEATED_LATE` y `CONFIG_WARNING`.
  `HISTORY_WEEKS = 4` (semanas previas que cuentan para el patrón de retardos).

Reglas (spec §4):
- `REPEATED_LATE` (uno por empleado con al menos un `LATE` en la semana): se reporta si
  los `LATE` **sin justificar** de la semana ≥ `settings.late_week`, **o** si las semanas
  con algún `LATE` (justificado o no) entre las 4 previas y la actual ≥
  `settings.late_weeks`. `days` = todos los `LATE` de la semana; `facts =
  (("late_this_week", n), ("unjustified_this_week", u), ("weeks_with_late", k))`.
- `CONFIG_WARNING`: un hallazgo por (código, empleado) entre los avisos **de la semana**.
  `id` = `finding_id(f"CONFIG_WARNING/{code}", employee_id, primer día o None)`;
  `days` = días distintos de los avisos, ordenados; `facts = (("code", code),
  ("occurrences", n))`. **Nunca** copia `detail` (puede traer nombres, Review Focus #2).

- [ ] **Step 1: Write the failing tests**

Agregar a `backend/tests/domain/test_review.py` (y `WarningCode` al import de
`tabernas.domain.types`):

```python
def test_two_unjustified_lates_in_the_week() -> None:
    findings = find([result(Outcome.LATE, day=MON), result(Outcome.LATE, day=WED)])
    assert findings == [
        Finding(
            id="REPEATED_LATE:1:2026-09-21",
            kind=FindingKind.REPEATED_LATE,
            employee_id=1,
            days=(MON, WED),
            facts=(
                ("late_this_week", 2),
                ("unjustified_this_week", 2),
                ("weeks_with_late", 1),
            ),
        )
    ]


def test_justified_lates_do_not_count_for_the_weekly_threshold() -> None:
    week = [result(Outcome.LATE, day=MON), result(Outcome.LATE, day=WED, justification_id=5)]
    assert find(week) == []


def test_lates_in_three_of_the_last_five_weeks() -> None:
    history = [
        result(Outcome.LATE, day=date(2026, 9, 16)),  # W38
        result(Outcome.LATE, day=date(2026, 8, 26), justification_id=2),  # W35, still counts
    ]
    findings = find([result(Outcome.LATE, day=WED)], history)
    assert kinds(findings) == [FindingKind.REPEATED_LATE]
    assert findings[0].fact("weeks_with_late") == 3
    assert findings[0].fact("unjustified_this_week") == 1


def test_history_older_than_four_weeks_is_ignored() -> None:
    history = [
        result(Outcome.LATE, day=date(2026, 8, 18)),  # W34
        result(Outcome.LATE, day=date(2026, 8, 11)),  # W33
    ]
    assert find([result(Outcome.LATE, day=WED)], history) == []


def test_late_history_alone_is_not_a_finding() -> None:
    history = [result(Outcome.LATE, day=date(2026, 9, d)) for d in (2, 9, 16)]
    assert find([result(Outcome.OK, day=WED)], history) == []


def test_late_thresholds_come_from_settings() -> None:
    week = [result(Outcome.LATE, day=WED)]
    assert find(week, settings=ReviewSettings(late_week=1)) != []
    assert find(week, settings=ReviewSettings(late_weeks=1)) != []


def test_config_warnings_are_grouped_by_code_and_employee() -> None:
    warnings = [
        AttendanceWarning(WarningCode.NO_REST_RULE, 1, WED, "Sin regla de descanso vigente"),
        AttendanceWarning(WarningCode.NO_REST_RULE, 1, MON, "Sin regla de descanso vigente"),
    ]
    assert find(warnings=warnings) == [
        Finding(
            id="CONFIG_WARNING/NO_REST_RULE:1:2026-09-21",
            kind=FindingKind.CONFIG_WARNING,
            employee_id=1,
            days=(MON, WED),
            facts=(("code", "NO_REST_RULE"), ("occurrences", 2)),
        )
    ]


def test_warning_detail_never_reaches_the_finding() -> None:
    # Review Focus #2: MISSING_RH_NAME's detail carries the employee's short name.
    warning = AttendanceWarning(
        WarningCode.MISSING_RH_NAME, 1, None, "ANA PRUEBA no tiene nombre en RH"
    )
    (finding,) = find(warnings=[warning])
    assert finding.id == "CONFIG_WARNING/MISSING_RH_NAME:1:-"
    assert finding.days == ()
    assert "ANA" not in repr(finding)


def test_unmapped_checkin_warning_has_no_employee() -> None:
    warning = AttendanceWarning(WarningCode.UNMAPPED_CHECKIN, None, TUE, "Checada de id SR 999")
    (finding,) = find(warnings=[warning])
    assert finding.employee_id is None
    assert finding.id == "CONFIG_WARNING/UNMAPPED_CHECKIN:-:2026-09-22"


def test_every_kind_is_listed_in_order() -> None:
    week = [
        result(Outcome.LATE, employee_id=4, day=MON),
        result(Outcome.LATE, employee_id=4, day=TUE),
        result(Outcome.ABSENT, employee_id=3, day=WED),
        result(Outcome.ABSENT, employee_id=3, day=THU),
        result(Outcome.ABSENT, employee_id=2, day=MON),
        replace(
            result(Outcome.UNREGISTERED_CHANGE, employee_id=1, day=TUE),
            checkin=datetime(2026, 9, 22, 16, 40),
        ),
    ]
    warnings = [AttendanceWarning(WarningCode.NO_SR_ID, 5, MON, "Sin id SR")]
    assert kinds(find(week, warnings=warnings)) == list(FindingKind)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/domain/test_review.py -v`
Expected: los tests nuevos FAIL (devuelven `[]` o les falta un tipo); los de Task 3 PASS.

- [ ] **Step 3: Extend the implementation**

En `backend/src/tabernas/domain/review.py`:

1. Cambiar los imports:

```python
from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import date, timedelta

from tabernas.domain.periods import week_monday
from tabernas.domain.review_types import Finding, FindingKind, ReviewSettings
from tabernas.domain.types import AttendanceWarning, DayResult, Outcome, Planned, WarningCode

HISTORY_WEEKS = 4  # previous weeks that count for the repeated-lateness pattern
KIND_ORDER = {kind: index for index, kind in enumerate(FindingKind)}
```

2. En `find_findings`, la lista queda:

```python
    findings = [
        *_rest_day_checkins(week),
        *_absences(week, in_streak),
        *streaks,
        *_repeated_lates(week, history, settings, start),
        *_config_warnings(warnings),
    ]
```

3. Agregar al final del archivo:

```python
def _repeated_lates(
    week: Sequence[DayResult],
    history: Sequence[DayResult],
    settings: ReviewSettings,
    start: date,
) -> list[Finding]:
    since = start - timedelta(weeks=HISTORY_WEEKS)
    weeks_with_late: defaultdict[int, set[date]] = defaultdict(set)
    for r in [*history, *week]:
        if r.outcome == Outcome.LATE and r.day >= since:
            weeks_with_late[r.employee_id].add(week_monday(r.day))
    lates_this_week: defaultdict[int, list[DayResult]] = defaultdict(list)
    for r in week:
        if r.outcome == Outcome.LATE:
            lates_this_week[r.employee_id].append(r)
    candidates = (
        _late_finding(employee_id, lates, len(weeks_with_late[employee_id]), settings)
        for employee_id, lates in lates_this_week.items()
    )
    return [finding for finding in candidates if finding is not None]


def _late_finding(
    employee_id: int, lates: Sequence[DayResult], weeks_with_late: int, settings: ReviewSettings
) -> Finding | None:
    unjustified = sum(r.justification_id is None for r in lates)
    if unjustified < settings.late_week and weeks_with_late < settings.late_weeks:
        return None
    days = tuple(sorted(r.day for r in lates))
    return Finding(
        id=finding_id(FindingKind.REPEATED_LATE, employee_id, days[0]),
        kind=FindingKind.REPEATED_LATE,
        employee_id=employee_id,
        days=days,
        facts=(
            ("late_this_week", len(lates)),
            ("unjustified_this_week", unjustified),
            ("weeks_with_late", weeks_with_late),
        ),
    )


def _config_warnings(warnings: Iterable[AttendanceWarning]) -> list[Finding]:
    grouped: dict[tuple[WarningCode, int | None], list[AttendanceWarning]] = {}
    for warning in warnings:
        grouped.setdefault((warning.code, warning.employee_id), []).append(warning)
    return [
        _warning_finding(code, employee_id, items)
        for (code, employee_id), items in grouped.items()
    ]


def _warning_finding(
    code: WarningCode, employee_id: int | None, items: Sequence[AttendanceWarning]
) -> Finding:
    """`detail` is never copied: it may contain names (spec §4, Review Focus #2)."""
    days = tuple(sorted({w.day for w in items if w.day is not None}))
    kind_key = f"{FindingKind.CONFIG_WARNING}/{code.value}"
    return Finding(
        id=finding_id(kind_key, employee_id, days[0] if days else None),
        kind=FindingKind.CONFIG_WARNING,
        employee_id=employee_id,
        days=days,
        facts=(("code", code.value), ("occurrences", len(items))),
    )
```

- [ ] **Step 4: Run tests and coverage**

Run: `uv run pytest tests/domain --cov --cov-report=term-missing -q && uv run coverage report --include="*/tabernas/domain/*" --fail-under=95`
Expected: PASS; `review.py` y `review_types.py` al 100%.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tabernas/domain/review.py backend/tests/domain/test_review.py
git commit -m "feat: detect repeated lateness and configuration warnings

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Ranuras de la revisión programada

**Files:**
- Create: `backend/src/tabernas/domain/review_schedule.py`
- Test: `backend/tests/domain/test_review_schedule.py`

**Interfaces:**
- Consumes: `ReviewTrigger` (Task 2), `week_monday` de `domain/periods.py`.
- Produces:
  - `THURSDAY_AT = time(17, 30)`, `MONDAY_AT = time(9, 0)`,
    `CATCH_UP_WINDOW = timedelta(hours=24)`.
  - `Slot(trigger: ReviewTrigger, due_at: datetime, iso_year: int, iso_week: int)`.
  - `last_due_slot(now: datetime) -> Slot` — la ranura más reciente con `due_at <= now`.
    El jueves revisa la semana ISO en curso; el lunes, la anterior.
  - `slot_to_enqueue(now: datetime) -> Slot | None` — la última ranura si venció hace
    ≤ 24 h, si no `None`.

- [ ] **Step 1: Write the failing tests**

`backend/tests/domain/test_review_schedule.py`:

```python
from datetime import datetime

from tabernas.domain.review_schedule import Slot, last_due_slot, slot_to_enqueue
from tabernas.domain.review_types import ReviewTrigger

THU = ReviewTrigger.THURSDAY
MON = ReviewTrigger.MONDAY


def test_thursday_at_1730_reviews_the_current_week() -> None:
    assert last_due_slot(datetime(2026, 9, 24, 17, 30)) == Slot(
        THU, datetime(2026, 9, 24, 17, 30), 2026, 39
    )


def test_before_thursday_1730_the_last_slot_is_monday() -> None:
    assert last_due_slot(datetime(2026, 9, 24, 17, 29)) == Slot(
        MON, datetime(2026, 9, 21, 9, 0), 2026, 38
    )


def test_monday_at_nine_reviews_the_previous_week() -> None:
    assert last_due_slot(datetime(2026, 9, 28, 9, 0)) == Slot(
        MON, datetime(2026, 9, 28, 9, 0), 2026, 39
    )


def test_monday_before_nine_points_to_last_thursday() -> None:
    assert last_due_slot(datetime(2026, 9, 28, 8, 59)) == Slot(
        THU, datetime(2026, 9, 24, 17, 30), 2026, 39
    )


def test_catch_up_window_is_24_hours() -> None:
    assert slot_to_enqueue(datetime(2026, 9, 25, 17, 30)) is not None  # exactly 24 h late
    assert slot_to_enqueue(datetime(2026, 9, 25, 17, 31)) is None
    assert slot_to_enqueue(datetime(2026, 9, 28, 8, 59)) is None


def test_monday_after_new_year_reviews_week_53() -> None:
    # Review Focus #3: 2026 has 53 ISO weeks; 2027-01-04 is the first Monday of 2027.
    assert slot_to_enqueue(datetime(2027, 1, 4, 9, 30)) == Slot(
        MON, datetime(2027, 1, 4, 9, 0), 2026, 53
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/domain/test_review_schedule.py -v`
Expected: FAIL con `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

`backend/src/tabernas/domain/review_schedule.py`:

```python
"""When the weekly review runs (spec §6.2): Thursday 17:30 reviews the current ISO week,
Monday 09:00 the previous one. A slot missed while the Mac slept runs within 24 hours."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from tabernas.domain.periods import week_monday
from tabernas.domain.review_types import ReviewTrigger

THURSDAY_AT = time(17, 30)
MONDAY_AT = time(9, 0)
CATCH_UP_WINDOW = timedelta(hours=24)


@dataclass(frozen=True)
class Slot:
    trigger: ReviewTrigger
    due_at: datetime
    iso_year: int
    iso_week: int


def _slot(trigger: ReviewTrigger, due_at: datetime, reviewed_day: date) -> Slot:
    year, week, _ = reviewed_day.isocalendar()
    return Slot(trigger, due_at, year, week)


def last_due_slot(now: datetime) -> Slot:
    monday = week_monday(now.date())
    previous_monday = monday - timedelta(weeks=1)
    candidates = (
        _slot(
            ReviewTrigger.THURSDAY,
            datetime.combine(monday + timedelta(days=3), THURSDAY_AT),
            monday,
        ),
        _slot(ReviewTrigger.MONDAY, datetime.combine(monday, MONDAY_AT), previous_monday),
        _slot(
            ReviewTrigger.THURSDAY,
            datetime.combine(previous_monday + timedelta(days=3), THURSDAY_AT),
            previous_monday,
        ),
    )
    return max((s for s in candidates if s.due_at <= now), key=lambda s: s.due_at)


def slot_to_enqueue(now: datetime) -> Slot | None:
    slot = last_due_slot(now)
    return slot if now - slot.due_at <= CATCH_UP_WINDOW else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/domain/test_review_schedule.py -v && uv run ruff check . && uv run ruff format --check . && uv run pyright`
Expected: PASS y sin errores de lint, formato ni tipos.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tabernas/domain/review_schedule.py backend/tests/domain/test_review_schedule.py
git commit -m "feat: compute weekly review schedule slots with catch-up

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Tabla `weekly_review`, migración y umbrales editables

**Files:**
- Modify: `backend/src/tabernas/db/models.py`
- Create: `backend/alembic/versions/0002_weekly_review.py`
- Create: `backend/src/tabernas/repos/review_settings.py`
- Modify: `backend/src/tabernas/api/routes/settings.py`
- Modify: `backend/tests/conftest.py` (TRUNCATE), `backend/tests/db/test_migrations.py`
- Test: `backend/tests/repos/test_review_settings.py`, `backend/tests/api/test_settings.py`

**Interfaces:**
- Consumes: `ReviewSettings`, `DEFAULT_REVIEW_SETTINGS`, `REVIEW_SETTING_LIMITS`,
  `validate_review_settings`, `ReviewStatus`, `ReviewTrigger` (Task 2).
- Produces:
  - `WeeklyReviewRow` (tabla `weekly_review`, spec §7.1) con índice único parcial
    `uq_weekly_review_in_progress` sobre (`iso_year`, `iso_week`) donde
    `status IN ('QUEUED', 'RUNNING')`. `as_of` y `approved_at` son `DateTime()` *naive*.
  - Claves de `setting` sembradas: `review_streak_days=2`, `review_late_week=2`,
    `review_late_weeks=3`.
  - `ReviewSettingsRepo(session).get() -> ReviewSettings`,
    `.save(settings: ReviewSettings) -> ReviewSettings` (valida antes de escribir).
  - `GET /settings/review` y `PUT /settings/review` con cuerpo
    `{streak_days, late_week, late_weeks}`; `GET/PUT /settings` no cambian.

- [ ] **Step 1: Write the failing tests**

`backend/tests/repos/test_review_settings.py`:

```python
import pytest
from sqlalchemy.orm import Session

from tabernas.domain.review_types import DEFAULT_REVIEW_SETTINGS, ReviewSettings
from tabernas.domain.types import DEFAULT_SETTINGS
from tabernas.domain.validation import DomainValidationError
from tabernas.repos.review_settings import ReviewSettingsRepo
from tabernas.repos.settings import SettingsRepo


def test_empty_table_returns_defaults(session: Session) -> None:
    assert ReviewSettingsRepo(session).get() == DEFAULT_REVIEW_SETTINGS


def test_save_round_trip(session: Session) -> None:
    wanted = ReviewSettings(streak_days=3, late_week=1, late_weeks=4)
    assert ReviewSettingsRepo(session).save(wanted) == wanted
    assert ReviewSettingsRepo(session).get() == wanted


def test_review_keys_do_not_disturb_attendance_settings(session: Session) -> None:
    ReviewSettingsRepo(session).save(ReviewSettings(streak_days=3, late_week=1, late_weeks=4))
    assert SettingsRepo(session).get() == DEFAULT_SETTINGS


def test_invalid_values_are_rejected_before_writing(session: Session) -> None:
    with pytest.raises(DomainValidationError):
        ReviewSettingsRepo(session).save(ReviewSettings(streak_days=0))
    assert ReviewSettingsRepo(session).get() == DEFAULT_REVIEW_SETTINGS
```

Agregar al final de `backend/tests/api/test_settings.py`:

```python
REVIEW_DEFAULTS = {"streak_days": 2, "late_week": 2, "late_weeks": 3}


def test_review_settings_defaults(client: TestClient) -> None:
    assert client.get("/settings/review").json()["data"] == REVIEW_DEFAULTS


def test_review_settings_round_trip_leaves_attendance_settings_alone(client: TestClient) -> None:
    wanted = {"streak_days": 3, "late_week": 1, "late_weeks": 5}
    assert client.put("/settings/review", json=wanted).json()["data"] == wanted
    assert client.get("/settings/review").json()["data"] == wanted
    assert client.get("/settings").json()["data"] == DEFAULTS


def test_invalid_review_settings_are_422(client: TestClient) -> None:
    for bad in ({"streak_days": 0}, {"late_week": 8}, {"late_weeks": 6}):
        response = client.put("/settings/review", json={**REVIEW_DEFAULTS, **bad})
        assert response.status_code == 422, bad
    assert client.get("/settings/review").json()["data"] == REVIEW_DEFAULTS
```

En `backend/tests/db/test_migrations.py`, el `assert stored == {...}` pasa a:

```python
        assert stored == {
            "entry_time_kitchen": "16:30",
            "entry_time_other": "16:40",
            "tolerance_minutes": "10",
            "review_streak_days": "2",
            "review_late_week": "2",
            "review_late_weeks": "3",
        }
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/repos/test_review_settings.py tests/api/test_settings.py tests/db/test_migrations.py -v`
Expected: FAIL (`ModuleNotFoundError: tabernas.repos.review_settings`, 404 en
`/settings/review`, y la migración sin las claves nuevas).

- [ ] **Step 3: Model, migration, repo and routes**

En `backend/src/tabernas/db/models.py`:
- Docstring del módulo: `"""SQLAlchemy tables for our own configuration. Derived attendance is never
  stored; weekly review drafts are the one dated snapshot (stage 2, spec E7)."""`
- Imports:

```python
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    MetaData,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from tabernas.domain.review_types import ReviewStatus, ReviewTrigger
from tabernas.domain.types import Area, ExceptionKind, Incident, RhType
```

- Al final del archivo:

```python
class WeeklyReviewRow(TimestampMixin, Base):
    __tablename__ = "weekly_review"
    __table_args__ = (
        CheckConstraint("iso_week BETWEEN 1 AND 53", name="iso_week_range"),
        Index(
            "uq_weekly_review_in_progress",
            "iso_year",
            "iso_week",
            unique=True,
            postgresql_where=text("status IN ('QUEUED', 'RUNNING')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    iso_year: Mapped[int]
    iso_week: Mapped[int] = mapped_column(SmallInteger)
    trigger: Mapped[ReviewTrigger] = mapped_column(_enum(ReviewTrigger))
    status: Mapped[ReviewStatus] = mapped_column(_enum(ReviewStatus))
    as_of: Mapped[datetime | None] = mapped_column(DateTime())  # naive business time
    findings: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    rh_rows: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    narrative: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    model: Mapped[str | None] = mapped_column(String(64))
    input_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]
    error: Mapped[str | None] = mapped_column(String(1000))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime())  # naive business time
```

`backend/alembic/versions/0002_weekly_review.py`:

```python
"""weekly review

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-01 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REVIEW_SETTINGS = [
    {"key": "review_streak_days", "value": "2"},
    {"key": "review_late_week", "value": "2"},
    {"key": "review_late_weeks", "value": "3"},
]


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "weekly_review",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("iso_year", sa.Integer(), nullable=False),
        sa.Column("iso_week", sa.SmallInteger(), nullable=False),
        sa.Column(
            "trigger",
            sa.Enum(
                "THURSDAY", "MONDAY", "MANUAL", name="reviewtrigger", native_enum=False, length=32
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "QUEUED",
                "RUNNING",
                "READY",
                "READY_NO_NARRATIVE",
                "FAILED",
                "APPROVED",
                name="reviewstatus",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("as_of", sa.DateTime(), nullable=True),
        sa.Column("findings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("rh_rows", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("narrative", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("error", sa.String(length=1000), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "iso_week BETWEEN 1 AND 53", name=op.f("ck_weekly_review_iso_week_range")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_weekly_review")),
    )
    op.create_index(
        "uq_weekly_review_in_progress",
        "weekly_review",
        ["iso_year", "iso_week"],
        unique=True,
        postgresql_where=sa.text("status IN ('QUEUED', 'RUNNING')"),
    )
    setting = sa.table("setting", sa.column("key", sa.String), sa.column("value", sa.String))
    op.bulk_insert(setting, REVIEW_SETTINGS)


def downgrade() -> None:
    """Downgrade schema."""
    keys = ", ".join(f"'{row['key']}'" for row in REVIEW_SETTINGS)
    op.execute(f"DELETE FROM setting WHERE key IN ({keys})")
    op.drop_index("uq_weekly_review_in_progress", table_name="weekly_review")
    op.drop_table("weekly_review")
```

`backend/src/tabernas/repos/review_settings.py`:

```python
"""Weekly-review thresholds, stored in the setting table as review_<field> keys."""

from dataclasses import asdict, fields

from sqlalchemy import select
from sqlalchemy.orm import Session

from tabernas.db.models import SettingRow
from tabernas.domain.review_types import (
    DEFAULT_REVIEW_SETTINGS,
    ReviewSettings,
    validate_review_settings,
)

KEY_PREFIX = "review_"


def setting_key(field: str) -> str:
    return f"{KEY_PREFIX}{field}"


class ReviewSettingsRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self) -> ReviewSettings:
        keys = [setting_key(f.name) for f in fields(ReviewSettings)]
        stmt = select(SettingRow.key, SettingRow.value).where(SettingRow.key.in_(keys))
        stored = dict(self._session.execute(stmt).all())
        values = {
            name: int(stored.get(setting_key(name), default))
            for name, default in asdict(DEFAULT_REVIEW_SETTINGS).items()
        }
        return ReviewSettings(**values)

    def save(self, settings: ReviewSettings) -> ReviewSettings:
        validate_review_settings(settings)
        for name, value in asdict(settings).items():
            self._session.merge(SettingRow(key=setting_key(name), value=str(value)))
        self._session.flush()
        return self.get()
```

En `backend/src/tabernas/api/routes/settings.py`, agregar imports y rutas:

```python
from dataclasses import asdict

from tabernas.domain.review_types import REVIEW_SETTING_LIMITS, ReviewSettings
from tabernas.repos.review_settings import ReviewSettingsRepo


class ReviewSettingsBody(BaseModel):
    streak_days: int = Field(ge=1, le=REVIEW_SETTING_LIMITS["streak_days"])
    late_week: int = Field(ge=1, le=REVIEW_SETTING_LIMITS["late_week"])
    late_weeks: int = Field(ge=1, le=REVIEW_SETTING_LIMITS["late_weeks"])


@router.get("/review")
def read_review_settings(session: SessionDep) -> Envelope[ReviewSettingsBody]:
    return ok(ReviewSettingsBody(**asdict(ReviewSettingsRepo(session).get())))


@router.put("/review")
def write_review_settings(
    body: ReviewSettingsBody, session: SessionDep
) -> Envelope[ReviewSettingsBody]:
    saved = ReviewSettingsRepo(session).save(ReviewSettings(**body.model_dump()))
    return ok(ReviewSettingsBody(**asdict(saved)))
```

En `backend/tests/conftest.py`, el `TRUNCATE` del fixture `session_factory` incluye la
tabla nueva:

```python
            text(
                "TRUNCATE employee, rest_rule, schedule_exception, justification, setting, "
                "weekly_review RESTART IDENTITY CASCADE"
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/repos/test_review_settings.py tests/api/test_settings.py tests/db -v`
Expected: PASS. `test_migrations_match_models_and_seed_settings` corre `alembic check`:
si falla, el modelo y la migración difieren (comparar nombres de columnas, tipos y
`nullable` hasta que coincidan).

- [ ] **Step 5: Commit**

```bash
git add backend/src/tabernas/db/models.py backend/alembic/versions/0002_weekly_review.py backend/src/tabernas/repos/review_settings.py backend/src/tabernas/api/routes/settings.py backend/tests/conftest.py backend/tests/db/test_migrations.py backend/tests/repos/test_review_settings.py backend/tests/api/test_settings.py
git commit -m "feat: add weekly_review table and editable review thresholds

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Repositorio de borradores (`ReviewRepo`)

**Files:**
- Create: `backend/src/tabernas/repos/review_codec.py`
- Create: `backend/src/tabernas/repos/reviews.py`
- Test: `backend/tests/repos/test_reviews.py`

**Interfaces:**
- Consumes: `WeeklyReviewRow` (Task 6); tipos de Task 2; `validate_iso_week`;
  `ConflictError`, `NotFoundError` de `repos/errors.py`.
- Produces (`tabernas.repos.reviews`):
  - `STALE_RUNNING_AFTER = timedelta(minutes=15)`,
    `STALE_RUNNING_MESSAGE = "La corrida se interrumpió; genera el borrador de nuevo."`.
  - `ReviewRepo(session)` con:
    - `enqueue(*, iso_year, iso_week, trigger) -> WeeklyReview` — `QUEUED`;
      `DomainValidationError` si la semana no existe; `ConflictError` si ya hay una
      `QUEUED`/`RUNNING` para esa semana.
    - `find_by_id(review_id) -> WeeklyReview` (`NotFoundError`).
    - `find_all(*, iso_year=None, iso_week=None, limit=20) -> list[WeeklyReview]`, más
      reciente primero.
    - `exists(*, iso_year, iso_week, trigger) -> bool` (cualquier estado).
    - `claim_next() -> WeeklyReview | None` — la `QUEUED` más antigua pasa a `RUNNING`
      (`FOR UPDATE SKIP LOCKED`).
    - `complete(review_id, result: ReviewResult) -> WeeklyReview` (recorta `error` a 1000).
    - `fail(review_id, error: str) -> WeeklyReview`.
    - `approve(review_id, approved_at: datetime) -> WeeklyReview` — solo desde `READY` o
      `READY_NO_NARRATIVE`; si no, `ConflictError`.
    - `fail_stale_running() -> int` — `RUNNING` con `updated_at` de hace > 15 min →
      `FAILED` con `STALE_RUNNING_MESSAGE`.
  - `tabernas.repos.review_codec`: `finding_to_json/finding_from_json`,
    `rh_row_to_json/rh_row_from_json`, `narrative_to_json/narrative_from_json`.

- [ ] **Step 1: Write the failing tests**

`backend/tests/repos/test_reviews.py`:

```python
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import func, update
from sqlalchemy.orm import Session

from tabernas.db.models import WeeklyReviewRow
from tabernas.domain.review_types import (
    Finding,
    FindingKind,
    Narrative,
    NarrativeItem,
    Priority,
    ProposedRhRow,
    ReviewResult,
    ReviewStatus,
    ReviewTrigger,
    SuggestedAction,
    WeeklyReview,
)
from tabernas.domain.types import RhType
from tabernas.domain.validation import DomainValidationError
from tabernas.repos.errors import ConflictError, NotFoundError
from tabernas.repos.reviews import STALE_RUNNING_MESSAGE, ReviewRepo

AS_OF = datetime(2026, 9, 24, 17, 30)
FINDING = Finding(
    id="NO_CHECKIN_STREAK:1:2026-09-23",
    kind=FindingKind.NO_CHECKIN_STREAK,
    employee_id=1,
    days=(date(2026, 9, 23), date(2026, 9, 24)),
    facts=(("days", 2),),
)
NARRATIVE = Narrative(
    summary="Dos días sin checar de {E1}.",
    items=(
        NarrativeItem(
            FINDING.id, Priority.HIGH, "Revisar con {E1}.", SuggestedAction.ADD_EXCEPTION
        ),
    ),
)
ROW = ProposedRhRow(
    employee_id=1, day=date(2026, 9, 23), rh_type=RhType.FALTA_INJUSTIFICADA, comment=""
)


def make_result(
    status: ReviewStatus = ReviewStatus.READY,
    narrative: Narrative | None = NARRATIVE,
    error: str | None = None,
) -> ReviewResult:
    return ReviewResult(
        status=status,
        as_of=AS_OF,
        findings=(FINDING,),
        rh_rows=(ROW,),
        narrative=narrative,
        model="claude-opus-5-5",
        input_tokens=1200,
        output_tokens=300,
        error=error,
    )


def enqueue(
    repo: ReviewRepo, week: int = 39, trigger: ReviewTrigger = ReviewTrigger.MANUAL
) -> WeeklyReview:
    return repo.enqueue(iso_year=2026, iso_week=week, trigger=trigger)


def test_enqueue_creates_a_queued_review(session: Session) -> None:
    review = enqueue(ReviewRepo(session))
    assert (review.iso_year, review.iso_week, review.status) == (2026, 39, ReviewStatus.QUEUED)
    assert review.created_at is not None
    assert review.findings == ()
    assert review.narrative is None


def test_only_one_review_in_progress_per_week(session: Session) -> None:
    repo = ReviewRepo(session)
    enqueue(repo)
    with pytest.raises(ConflictError, match="Ya se está generando"):
        enqueue(repo, trigger=ReviewTrigger.THURSDAY)
    enqueue(repo, week=40)  # another week is fine


def test_a_finished_review_frees_the_week(session: Session) -> None:
    repo = ReviewRepo(session)
    first = enqueue(repo)
    repo.fail(first.id, "algo falló")
    assert enqueue(repo).id != first.id


def test_invalid_iso_week_is_rejected(session: Session) -> None:
    with pytest.raises(DomainValidationError):
        ReviewRepo(session).enqueue(iso_year=2025, iso_week=53, trigger=ReviewTrigger.MANUAL)


def test_claim_next_takes_the_oldest_queued(session: Session) -> None:
    repo = ReviewRepo(session)
    older, newer = enqueue(repo, week=38), enqueue(repo, week=39)
    first = repo.claim_next()
    assert first is not None and first.id == older.id and first.status == ReviewStatus.RUNNING
    second = repo.claim_next()
    assert second is not None and second.id == newer.id
    assert repo.claim_next() is None


def test_complete_round_trips_the_snapshot(session: Session) -> None:
    repo = ReviewRepo(session)
    review = enqueue(repo)
    repo.complete(review.id, make_result())
    loaded = repo.find_by_id(review.id)
    assert loaded.status == ReviewStatus.READY
    assert loaded.as_of == AS_OF
    assert loaded.findings == (FINDING,)
    assert loaded.rh_rows == (ROW,)
    assert loaded.narrative == NARRATIVE
    assert (loaded.model, loaded.input_tokens, loaded.output_tokens) == (
        "claude-opus-5-5",
        1200,
        300,
    )


def test_complete_without_narrative_truncates_long_errors(session: Session) -> None:
    repo = ReviewRepo(session)
    review = enqueue(repo)
    done = repo.complete(
        review.id, make_result(ReviewStatus.READY_NO_NARRATIVE, narrative=None, error="x" * 1500)
    )
    assert done.narrative is None
    assert done.findings == (FINDING,)
    assert done.error == "x" * 1000


def test_exists_is_per_trigger(session: Session) -> None:
    repo = ReviewRepo(session)
    enqueue(repo, trigger=ReviewTrigger.THURSDAY)
    assert repo.exists(iso_year=2026, iso_week=39, trigger=ReviewTrigger.THURSDAY)
    assert not repo.exists(iso_year=2026, iso_week=39, trigger=ReviewTrigger.MONDAY)


def test_only_ready_reviews_can_be_approved_once(session: Session) -> None:
    repo = ReviewRepo(session)
    review = enqueue(repo)
    with pytest.raises(ConflictError):
        repo.approve(review.id, AS_OF)
    repo.complete(review.id, make_result())
    approved = repo.approve(review.id, datetime(2026, 9, 24, 18, 0))
    assert approved.status == ReviewStatus.APPROVED
    assert approved.approved_at == datetime(2026, 9, 24, 18, 0)
    with pytest.raises(ConflictError):
        repo.approve(review.id, AS_OF)


def test_stale_running_reviews_fail_and_free_the_week(session: Session) -> None:
    # Review Focus #4: a crashed worker must not block the week forever.
    repo = ReviewRepo(session)
    stale, fresh = enqueue(repo, week=38), enqueue(repo, week=39)
    repo.claim_next()
    repo.claim_next()
    session.execute(
        update(WeeklyReviewRow)
        .where(WeeklyReviewRow.id == stale.id)
        .values(updated_at=func.now() - timedelta(minutes=20))
    )
    assert repo.fail_stale_running() == 1
    failed = repo.find_by_id(stale.id)
    assert (failed.status, failed.error) == (ReviewStatus.FAILED, STALE_RUNNING_MESSAGE)
    assert repo.find_by_id(fresh.id).status == ReviewStatus.RUNNING
    enqueue(repo, week=38)


def test_find_all_filters_and_orders_newest_first(session: Session) -> None:
    repo = ReviewRepo(session)
    a, b = enqueue(repo, week=38), enqueue(repo, week=39)
    assert [r.id for r in repo.find_all()] == [b.id, a.id]
    assert [r.id for r in repo.find_all(iso_year=2026, iso_week=38)] == [a.id]


def test_missing_review_is_not_found(session: Session) -> None:
    with pytest.raises(NotFoundError):
        ReviewRepo(session).find_by_id(999)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/repos/test_reviews.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'tabernas.repos.reviews'`.

- [ ] **Step 3: Write the implementation**

`backend/src/tabernas/repos/review_codec.py`:

```python
"""JSON shape of a review snapshot (jsonb columns). Keep keys stable: old rows must load."""

from datetime import date
from typing import Any

from tabernas.domain.review_types import (
    Finding,
    FindingKind,
    Narrative,
    NarrativeItem,
    Priority,
    ProposedRhRow,
    SuggestedAction,
)
from tabernas.domain.types import RhType

Json = dict[str, Any]


def finding_to_json(finding: Finding) -> Json:
    return {
        "id": finding.id,
        "kind": finding.kind.value,
        "employee_id": finding.employee_id,
        "days": [day.isoformat() for day in finding.days],
        "facts": [[key, value] for key, value in finding.facts],
    }


def finding_from_json(data: Json) -> Finding:
    return Finding(
        id=str(data["id"]),
        kind=FindingKind(data["kind"]),
        employee_id=data["employee_id"],
        days=tuple(date.fromisoformat(day) for day in data["days"]),
        facts=tuple((str(key), value) for key, value in data["facts"]),
    )


def rh_row_to_json(row: ProposedRhRow) -> Json:
    return {
        "employee_id": row.employee_id,
        "day": row.day.isoformat(),
        "rh_type": row.rh_type.value,
        "comment": row.comment,
    }


def rh_row_from_json(data: Json) -> ProposedRhRow:
    return ProposedRhRow(
        employee_id=int(data["employee_id"]),
        day=date.fromisoformat(data["day"]),
        rh_type=RhType(data["rh_type"]),
        comment=str(data["comment"]),
    )


def narrative_to_json(narrative: Narrative) -> Json:
    return {
        "summary": narrative.summary,
        "items": [
            {
                "finding_id": item.finding_id,
                "priority": item.priority.value,
                "explanation": item.explanation,
                "suggested_action": item.suggested_action.value,
            }
            for item in narrative.items
        ],
    }


def narrative_from_json(data: Json) -> Narrative:
    return Narrative(
        summary=str(data["summary"]),
        items=tuple(
            NarrativeItem(
                finding_id=str(item["finding_id"]),
                priority=Priority(item["priority"]),
                explanation=str(item["explanation"]),
                suggested_action=SuggestedAction(item["suggested_action"]),
            )
            for item in data["items"]
        ),
    )
```

`backend/src/tabernas/repos/reviews.py`:

```python
"""Weekly review drafts. Returns immutable domain objects, never ORM rows."""

from datetime import datetime, timedelta
from typing import Any, cast

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tabernas.db.models import WeeklyReviewRow
from tabernas.domain.periods import validate_iso_week
from tabernas.domain.review_types import ReviewResult, ReviewStatus, ReviewTrigger, WeeklyReview
from tabernas.repos.errors import ConflictError, NotFoundError
from tabernas.repos.review_codec import (
    finding_from_json,
    finding_to_json,
    narrative_from_json,
    narrative_to_json,
    rh_row_from_json,
    rh_row_to_json,
)

STALE_RUNNING_AFTER = timedelta(minutes=15)
STALE_RUNNING_MESSAGE = "La corrida se interrumpió; genera el borrador de nuevo."
APPROVABLE = frozenset({ReviewStatus.READY, ReviewStatus.READY_NO_NARRATIVE})
MAX_ERROR_LENGTH = 1000


def to_review(row: WeeklyReviewRow) -> WeeklyReview:
    return WeeklyReview(
        id=row.id,
        iso_year=row.iso_year,
        iso_week=row.iso_week,
        trigger=row.trigger,
        status=row.status,
        created_at=row.created_at,
        as_of=row.as_of,
        findings=tuple(finding_from_json(item) for item in row.findings or ()),
        rh_rows=tuple(rh_row_from_json(item) for item in row.rh_rows or ()),
        narrative=narrative_from_json(row.narrative) if row.narrative is not None else None,
        model=row.model,
        input_tokens=row.input_tokens,
        output_tokens=row.output_tokens,
        error=row.error,
        approved_at=row.approved_at,
    )


def _truncate(error: str | None) -> str | None:
    return None if error is None else error[:MAX_ERROR_LENGTH]


class ReviewRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def enqueue(self, *, iso_year: int, iso_week: int, trigger: ReviewTrigger) -> WeeklyReview:
        validate_iso_week(iso_year, iso_week)
        row = WeeklyReviewRow(
            iso_year=iso_year, iso_week=iso_week, trigger=trigger, status=ReviewStatus.QUEUED
        )
        try:
            with self._session.begin_nested():
                self._session.add(row)
        except IntegrityError as exc:
            raise ConflictError("Ya se está generando un borrador para esa semana") from exc
        self._session.refresh(row)
        return to_review(row)

    def find_by_id(self, review_id: int) -> WeeklyReview:
        return to_review(self._require(review_id))

    def find_all(
        self, *, iso_year: int | None = None, iso_week: int | None = None, limit: int = 20
    ) -> list[WeeklyReview]:
        stmt = select(WeeklyReviewRow).order_by(WeeklyReviewRow.id.desc()).limit(limit)
        if iso_year is not None:
            stmt = stmt.where(WeeklyReviewRow.iso_year == iso_year)
        if iso_week is not None:
            stmt = stmt.where(WeeklyReviewRow.iso_week == iso_week)
        return [to_review(row) for row in self._session.scalars(stmt)]

    def exists(self, *, iso_year: int, iso_week: int, trigger: ReviewTrigger) -> bool:
        stmt = select(WeeklyReviewRow.id).where(
            WeeklyReviewRow.iso_year == iso_year,
            WeeklyReviewRow.iso_week == iso_week,
            WeeklyReviewRow.trigger == trigger,
        )
        return self._session.scalar(stmt.limit(1)) is not None

    def claim_next(self) -> WeeklyReview | None:
        stmt = (
            select(WeeklyReviewRow)
            .where(WeeklyReviewRow.status == ReviewStatus.QUEUED)
            .order_by(WeeklyReviewRow.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        row = self._session.scalars(stmt).first()
        if row is None:
            return None
        row.status = ReviewStatus.RUNNING  # ORM rows are the mutable persistence boundary
        return self._flushed(row)

    def complete(self, review_id: int, result: ReviewResult) -> WeeklyReview:
        row = self._require(review_id)
        row.status = result.status
        row.as_of = result.as_of
        row.findings = [finding_to_json(item) for item in result.findings]
        row.rh_rows = [rh_row_to_json(item) for item in result.rh_rows]
        row.narrative = narrative_to_json(result.narrative) if result.narrative else None
        row.model = result.model
        row.input_tokens = result.input_tokens
        row.output_tokens = result.output_tokens
        row.error = _truncate(result.error)
        return self._flushed(row)

    def fail(self, review_id: int, error: str) -> WeeklyReview:
        row = self._require(review_id)
        row.status = ReviewStatus.FAILED
        row.error = _truncate(error)
        return self._flushed(row)

    def approve(self, review_id: int, approved_at: datetime) -> WeeklyReview:
        row = self._require(review_id)
        if row.status not in APPROVABLE:
            raise ConflictError("Solo se puede aprobar un borrador listo que no esté aprobado")
        row.status = ReviewStatus.APPROVED
        row.approved_at = approved_at
        return self._flushed(row)

    def fail_stale_running(self) -> int:
        stmt = (
            update(WeeklyReviewRow)
            .where(
                WeeklyReviewRow.status == ReviewStatus.RUNNING,
                WeeklyReviewRow.updated_at < func.now() - STALE_RUNNING_AFTER,
            )
            .values(status=ReviewStatus.FAILED, error=STALE_RUNNING_MESSAGE)
        )
        result = cast("CursorResult[Any]", self._session.execute(stmt))
        return result.rowcount

    def _flushed(self, row: WeeklyReviewRow) -> WeeklyReview:
        self._session.flush()
        return to_review(row)

    def _require(self, review_id: int) -> WeeklyReviewRow:
        row = self._session.get(WeeklyReviewRow, review_id)
        if row is None:
            raise NotFoundError("Borrador no encontrado")
        return row
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/repos -v && uv run pyright`
Expected: PASS, 0 errores de tipos.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tabernas/repos/review_codec.py backend/src/tabernas/repos/reviews.py backend/tests/repos/test_reviews.py
git commit -m "feat: add weekly review repository with queue and approval

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Seudónimos

**Files:**
- Create: `backend/src/tabernas/agents/__init__.py` (vacío)
- Create: `backend/src/tabernas/agents/pseudonyms.py`
- Create: `backend/tests/agents/__init__.py` (vacío), `backend/tests/agents/helpers.py`
- Test: `backend/tests/agents/test_pseudonyms.py`

**Interfaces:**
- Consumes: `Employee` de `domain/types.py`; `find_findings` (Task 3–4); `to_rh_rows`;
  `ReviewContext`, `proposed_rows` (Task 2).
- Produces (`tabernas.agents.pseudonyms`):
  - `alias(employee_id: int) -> str` → `"E12"`.
  - `parse_alias(value: str) -> int | None` (`" E7 "` → 7; cualquier otra cosa → `None`).
  - `aliases_in(text: str) -> set[str]` — seudónimos entre llaves (`{E12}` → `"E12"`).
  - `render(text: str, employees: Sequence[Employee]) -> str` — `{E12}` → nombre corto;
    deja `{E99}` si no existe.
  - `scrub(text: str, employees: Sequence[Employee]) -> str` — reemplaza nombre corto y
    nombre RH (sin distinguir mayúsculas, palabra completa, el más largo primero) por `E12`.
  - `contains_known_name(text: str, employees: Sequence[Employee]) -> bool` — ignora los
    tokens `{E12}`.
- Produces (`tests.agents.helpers`, para Tasks 9–12 y la evaluación): `WEEK_START`,
  `WEEK_END`, `AS_OF`, `person()`, `ANA`, `BETO`, `STAFF`, `make_context()`.

Nota: los empleados de prueba de `tests/domain/factories.py` se llaman `E1`, `E2`…, igual
que los seudónimos; por eso las pruebas de agentes usan `tests/agents/helpers.py`.

- [ ] **Step 1: Write the helpers and the failing tests**

`backend/tests/agents/helpers.py`:

```python
"""Synthetic employees and review contexts for agent tests. No real data."""

from collections.abc import Sequence
from datetime import date, datetime

from tabernas.domain.review import find_findings
from tabernas.domain.review_types import (
    DEFAULT_REVIEW_SETTINGS,
    ReviewContext,
    ReviewSettings,
    proposed_rows,
)
from tabernas.domain.rh import to_rh_rows
from tabernas.domain.types import Area, AttendanceWarning, DayResult, Employee

WEEK_START, WEEK_END = date(2026, 9, 21), date(2026, 9, 27)  # 2026-W39
AS_OF = datetime(2026, 9, 24, 17, 30)


def person(employee_id: int, short_name: str, rh_name: str | None = None) -> Employee:
    return Employee(
        id=employee_id,
        sr_id=100 + employee_id,
        short_name=short_name,
        rh_name=rh_name,
        area=Area.OTHER,
        applies_lateness=True,
        tracks_attendance=True,
        active=True,
    )


ANA = person(1, "ANA PRUEBA", "ANA PRUEBA LOPEZ")
BETO = person(2, "BETO PRUEBA", "ALBERTO PRUEBA RUIZ")
STAFF = (ANA, BETO)


def make_context(
    week: Sequence[DayResult] = (),
    history: Sequence[DayResult] = (),
    warnings: Sequence[AttendanceWarning] = (),
    employees: Sequence[Employee] = STAFF,
    settings: ReviewSettings = DEFAULT_REVIEW_SETTINGS,
) -> ReviewContext:
    findings = find_findings(
        list(week), list(history), list(warnings), settings, WEEK_START, WEEK_END
    )
    rows, _ = to_rh_rows(list(week), list(employees))
    return ReviewContext(
        iso_year=2026,
        iso_week=39,
        start=WEEK_START,
        end=WEEK_END,
        as_of=AS_OF,
        employees=tuple(employees),
        week_results=tuple(week),
        history_results=tuple(history),
        rh_rows=proposed_rows(rows),
        findings=tuple(findings),
    )
```

`backend/tests/agents/test_pseudonyms.py`:

```python
from tabernas.agents.pseudonyms import (
    alias,
    aliases_in,
    contains_known_name,
    parse_alias,
    render,
    scrub,
)
from tests.agents.helpers import STAFF, person


def test_alias_round_trip() -> None:
    assert alias(12) == "E12"
    assert parse_alias("E12") == 12
    assert parse_alias(" E7 ") == 7
    for bad in ("E", "12", "{E12}", "e12x", "Ana"):
        assert parse_alias(bad) is None


def test_aliases_in_only_reads_braced_tokens() -> None:
    assert aliases_in("Hablar con {E1} y {E22}; E3 sin llaves no cuenta") == {"E1", "E22"}


def test_render_uses_short_names_and_keeps_unknown_aliases() -> None:
    text = "{E1} cubrió a {E2}; {E9} ya no existe"
    assert render(text, STAFF) == "ANA PRUEBA cubrió a BETO PRUEBA; {E9} ya no existe"


def test_scrub_replaces_short_and_rh_names_ignoring_case() -> None:
    text = "Avisó ana prueba lopez que cubría a Beto Prueba y a ALBERTO PRUEBA RUIZ"
    assert scrub(text, STAFF) == "Avisó E1 que cubría a E2 y a E2"


def test_scrub_prefers_the_longest_name_and_whole_words() -> None:
    employees = [person(1, "ANA"), person(2, "ANA MARIA")]
    assert scrub("ANA MARIA y ANA comieron BANANA", employees) == "E2 y E1 comieron BANANA"


def test_scrub_without_employees_changes_nothing() -> None:
    assert scrub("hola", []) == "hola"


def test_contains_known_name_ignores_alias_tokens() -> None:
    assert not contains_known_name("Revisar con {E1}.", STAFF)
    assert contains_known_name("Revisar con Ana Prueba.", STAFF)
    assert not contains_known_name("Revisar con alguien.", [])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/agents/test_pseudonyms.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'tabernas.agents'`.

- [ ] **Step 3: Write the implementation**

`backend/src/tabernas/agents/__init__.py`: vacío.

`backend/src/tabernas/agents/pseudonyms.py`:

```python
"""Pseudonyms (spec E4): Claude only ever sees E{id}, never an employee's name."""

import re
from collections.abc import Iterable, Sequence

from tabernas.domain.types import Employee

_ALIAS = re.compile(r"E(\d+)")
_ALIAS_TOKEN = re.compile(r"\{(E\d+)\}")


def alias(employee_id: int) -> str:
    return f"E{employee_id}"


def parse_alias(value: str) -> int | None:
    match = _ALIAS.fullmatch(value.strip())
    return int(match.group(1)) if match else None


def aliases_in(text: str) -> set[str]:
    return set(_ALIAS_TOKEN.findall(text))


def render(text: str, employees: Sequence[Employee]) -> str:
    names = {alias(e.id): e.short_name for e in employees}
    return _ALIAS_TOKEN.sub(lambda m: names.get(m.group(1), m.group(0)), text)


def scrub(text: str, employees: Sequence[Employee]) -> str:
    index = _name_index(employees)
    pattern = _name_pattern(index)
    if pattern is None:
        return text
    return pattern.sub(lambda m: alias(index[m.group(1).casefold()]), text)


def contains_known_name(text: str, employees: Sequence[Employee]) -> bool:
    pattern = _name_pattern(_name_index(employees))
    return pattern is not None and pattern.search(_ALIAS_TOKEN.sub(" ", text)) is not None


def _name_index(employees: Sequence[Employee]) -> dict[str, int]:
    index: dict[str, int] = {}
    for employee in employees:
        for name in (employee.short_name, employee.rh_name):
            if name and name.strip():
                index.setdefault(name.strip().casefold(), employee.id)
    return index


def _name_pattern(names: Iterable[str]) -> re.Pattern[str] | None:
    ordered = sorted(names, key=len, reverse=True)  # longest first: "ANA MARIA" before "ANA"
    if not ordered:
        return None
    alternatives = "|".join(re.escape(name) for name in ordered)
    return re.compile(rf"(?<!\w)({alternatives})(?!\w)", re.IGNORECASE)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/agents/test_pseudonyms.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/src/tabernas/agents/__init__.py backend/src/tabernas/agents/pseudonyms.py backend/tests/agents/__init__.py backend/tests/agents/helpers.py backend/tests/agents/test_pseudonyms.py
git commit -m "feat: pseudonymize employees for the review agent

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Esquema de salida y validador

**Files:**
- Create: `backend/src/tabernas/agents/weekly_review/__init__.py` (vacío)
- Create: `backend/src/tabernas/agents/weekly_review/schema.py`
- Create: `backend/src/tabernas/agents/weekly_review/validate.py`
- Test: `backend/tests/agents/test_schema_validate.py`

**Interfaces:**
- Consumes: `Narrative`, `NarrativeItem`, `Priority`, `SuggestedAction`, `Finding`
  (Task 2); `alias`, `aliases_in`, `contains_known_name` (Task 8).
- Produces:
  - `schema.NARRATIVE_SCHEMA: dict[str, Any]` — JSON Schema cerrado
    (`additionalProperties: false`), sin `$ref`, para `output_config.format`.
  - `schema.NarrativeFormatError(ValueError)`;
    `schema.parse_narrative(text: str) -> Narrative` (recorta espacios de `summary` y
    `explanation`).
  - `validate.validate_narrative(narrative, findings, employees) -> list[str]` — lista
    vacía si es válida; mensajes en español, que se le devuelven a Claude y se guardan
    en `error`.

- [ ] **Step 1: Write the failing tests**

`backend/tests/agents/test_schema_validate.py`:

```python
import json
from datetime import date

import pytest

from tabernas.agents.weekly_review.schema import (
    NARRATIVE_SCHEMA,
    NarrativeFormatError,
    parse_narrative,
)
from tabernas.agents.weekly_review.validate import validate_narrative
from tabernas.domain.review_types import (
    Finding,
    FindingKind,
    Narrative,
    NarrativeItem,
    Priority,
    SuggestedAction,
)
from tests.agents.helpers import STAFF

F1 = Finding(
    "ABSENT_NO_EXCEPTION:1:2026-09-23", FindingKind.ABSENT_NO_EXCEPTION, 1, (date(2026, 9, 23),)
)
F2 = Finding(
    "REST_DAY_CHECKIN:2:2026-09-22", FindingKind.REST_DAY_CHECKIN, 2, (date(2026, 9, 22),)
)


def item(finding_id: str, explanation: str = "Revisar a {E1}.") -> NarrativeItem:
    return NarrativeItem(finding_id, Priority.HIGH, explanation, SuggestedAction.JUSTIFY)


def narrative(*items: NarrativeItem, summary: str = "Pendientes de {E1} y {E2}.") -> Narrative:
    return Narrative(summary, items)


def test_schema_is_closed_and_matches_the_domain_enums() -> None:
    item_schema = NARRATIVE_SCHEMA["properties"]["items"]["items"]
    assert NARRATIVE_SCHEMA["additionalProperties"] is False
    assert item_schema["additionalProperties"] is False
    assert item_schema["properties"]["priority"]["enum"] == [p.value for p in Priority]
    assert item_schema["properties"]["suggested_action"]["enum"] == [
        a.value for a in SuggestedAction
    ]
    assert "$ref" not in json.dumps(NARRATIVE_SCHEMA)


def test_parse_valid_narrative() -> None:
    text = json.dumps(
        {
            "summary": "  Una falta.  ",
            "items": [
                {
                    "finding_id": F1.id,
                    "priority": "HIGH",
                    "explanation": " Falta de {E1}. ",
                    "suggested_action": "JUSTIFY",
                }
            ],
        }
    )
    assert parse_narrative(text) == Narrative(
        "Una falta.",
        (NarrativeItem(F1.id, Priority.HIGH, "Falta de {E1}.", SuggestedAction.JUSTIFY),),
    )


@pytest.mark.parametrize(
    "text",
    [
        "no es json",
        '{"summary": "x"}',
        '{"summary": "x", "items": [], "extra": 1}',
        '{"summary": "x", "items": [{"finding_id": "a", "priority": "URGENT", '
        '"explanation": "", "suggested_action": "NONE"}]}',
    ],
)
def test_parse_rejects_bad_payloads(text: str) -> None:
    with pytest.raises(NarrativeFormatError, match="no cumple el esquema"):
        parse_narrative(text)


def test_complete_narrative_is_valid() -> None:
    answer = narrative(item(F1.id), item(F2.id, "Cambio de descanso de {E2}."))
    assert validate_narrative(answer, [F1, F2], STAFF) == []


def test_week_without_findings_accepts_empty_items() -> None:
    assert validate_narrative(narrative(summary="Semana sin pendientes."), [], STAFF) == []


def test_missing_repeated_and_unknown_findings_are_reported() -> None:
    answer = narrative(item(F1.id), item(F1.id), item("INVENTADO:1:-"))
    errors = validate_narrative(answer, [F1, F2], STAFF)
    assert f"Faltan hallazgos: {F2.id}" in errors
    assert f"Hallazgos repetidos: {F1.id}" in errors
    assert "Hallazgos que no existen: INVENTADO:1:-" in errors


def test_unknown_alias_is_reported() -> None:
    errors = validate_narrative(narrative(item(F1.id, "Habló con {E99}.")), [F1], STAFF)
    assert errors == ["Seudónimos desconocidos: {E99}"]


def test_real_names_are_reported() -> None:
    errors = validate_narrative(narrative(item(F1.id), summary="Ana Prueba faltó."), [F1], STAFF)
    assert len(errors) == 1 and "nombres reales" in errors[0]


def test_blank_summary_is_reported() -> None:
    assert validate_narrative(narrative(item(F1.id), summary="  "), [F1], STAFF) == [
        "El resumen está vacío."
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/agents/test_schema_validate.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'tabernas.agents.weekly_review'`.

- [ ] **Step 3: Write the implementation**

`backend/src/tabernas/agents/weekly_review/__init__.py`: vacío.

`backend/src/tabernas/agents/weekly_review/schema.py`:

```python
"""Structured final answer of the weekly-review agent (spec §5.3)."""

from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from tabernas.domain.review_types import Narrative, NarrativeItem, Priority, SuggestedAction

_ITEM_FIELDS = ["finding_id", "priority", "explanation", "suggested_action"]

NARRATIVE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "finding_id": {"type": "string"},
                    "priority": {"type": "string", "enum": [p.value for p in Priority]},
                    "explanation": {"type": "string"},
                    "suggested_action": {
                        "type": "string",
                        "enum": [a.value for a in SuggestedAction],
                    },
                },
                "required": _ITEM_FIELDS,
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "items"],
    "additionalProperties": False,
}


class NarrativeFormatError(ValueError):
    """The final answer is not JSON matching NARRATIVE_SCHEMA."""


class _ItemModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    finding_id: str
    priority: Priority
    explanation: str
    suggested_action: SuggestedAction


class _NarrativeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str
    items: list[_ItemModel]


def parse_narrative(text: str) -> Narrative:
    try:
        parsed = _NarrativeModel.model_validate_json(text)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc']) or 'raíz'}: {error['msg']}"
            for error in exc.errors()[:3]
        )
        raise NarrativeFormatError(f"La respuesta no cumple el esquema ({details})") from exc
    return Narrative(
        summary=parsed.summary.strip(),
        items=tuple(
            NarrativeItem(
                finding_id=item.finding_id,
                priority=item.priority,
                explanation=item.explanation.strip(),
                suggested_action=item.suggested_action,
            )
            for item in parsed.items
        ),
    )
```

`backend/src/tabernas/agents/weekly_review/validate.py`:

```python
"""Checks the agent's answer against the deterministic findings (spec §5.4).

The guarantee "never omits, never invents" lives here, not in the prompt."""

from collections import Counter
from collections.abc import Sequence

from tabernas.agents.pseudonyms import alias, aliases_in, contains_known_name
from tabernas.domain.review_types import Finding, Narrative
from tabernas.domain.types import Employee

NAME_ERROR = (
    "El texto usa nombres reales; nombra a los empleados solo con su seudónimo, p. ej. {E12}."
)


def validate_narrative(
    narrative: Narrative, findings: Sequence[Finding], employees: Sequence[Employee]
) -> list[str]:
    return [*_coverage_errors(narrative, findings), *_text_errors(narrative, employees)]


def _coverage_errors(narrative: Narrative, findings: Sequence[Finding]) -> list[str]:
    expected = [finding.id for finding in findings]
    counts = Counter(item.finding_id for item in narrative.items)
    missing = [finding_id for finding_id in expected if finding_id not in counts]
    repeated = sorted(finding_id for finding_id, count in counts.items() if count > 1)
    unknown = sorted(set(counts) - set(expected))
    checks = (
        ("Faltan hallazgos", missing),
        ("Hallazgos repetidos", repeated),
        ("Hallazgos que no existen", unknown),
    )
    return [f"{label}: {', '.join(ids)}" for label, ids in checks if ids]


def _text_errors(narrative: Narrative, employees: Sequence[Employee]) -> list[str]:
    texts = [narrative.summary, *(item.explanation for item in narrative.items)]
    valid = {alias(employee.id) for employee in employees}
    unknown = sorted({found for text in texts for found in aliases_in(text)} - valid)
    errors: list[str] = []
    if not narrative.summary.strip():
        errors.append("El resumen está vacío.")
    if unknown:
        errors.append("Seudónimos desconocidos: " + ", ".join(f"{{{a}}}" for a in unknown))
    if any(contains_known_name(text, employees) for text in texts):
        errors.append(NAME_ERROR)
    return errors
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/agents/test_schema_validate.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tabernas/agents/weekly_review/__init__.py backend/src/tabernas/agents/weekly_review/schema.py backend/src/tabernas/agents/weekly_review/validate.py backend/tests/agents/test_schema_validate.py
git commit -m "feat: add review narrative schema and validator

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Herramientas de lectura del agente

**Files:**
- Create: `backend/src/tabernas/agents/weekly_review/tools.py`
- Test: `backend/tests/agents/test_tools.py`

**Interfaces:**
- Consumes: `ReviewContext`, `Finding`, `REVIEW_HISTORY_WEEKS` (Task 2); `alias`,
  `parse_alias`, `scrub` (Task 8); `summarize`, `Grouping` de `domain/summary.py`.
- Produces (`tabernas.agents.weekly_review.tools`):
  - `ToolError(ValueError)` — entrada inválida; el loop la devuelve como `tool_result`
    con `is_error: true`.
  - `TOOL_DEFINITIONS: list[dict[str, Any]]` — `get_week_findings`, `get_week_incidents`,
    `get_employee_history` (`employee`, `weeks` 1–8), `get_employee_week` (`employee`);
    todas `strict: True` con esquemas cerrados.
  - `ReviewTools(context).call(name: str, arguments: Mapping[str, Any]) -> str` — JSON
    (`ensure_ascii=False`); empleados como `E12`; comentarios pasados por `scrub`.

Formas de salida:
- hallazgo: `{"id", "kind", "employee": "E12" | null, "days": ["YYYY-MM-DD"], "facts": {...}}`
- día: `{"employee", "day", "weekday", "planned", "outcome", "checkin": "HH:MM" | null,
  "minutes_late", "rh_type", "justified": bool, "comment"}`
- incidencias: `{"incidents": [día…], "rh_rows": [{"employee", "day", "rh_type", "comment"}]}`
- historial: `[{"week": "2026-W38", "worked", "late", "late_justified", "absent",
  "absent_justified", "unresolved"}]` — solo las `weeks` semanas previas a la revisada.

- [ ] **Step 1: Write the failing tests**

`backend/tests/agents/test_tools.py`:

```python
import json
from dataclasses import replace
from datetime import date, datetime
from typing import Any

import pytest

from tabernas.agents.weekly_review.tools import TOOL_DEFINITIONS, ReviewTools, ToolError
from tabernas.domain.types import DayResult, Outcome
from tests.agents.helpers import make_context
from tests.domain.factories import result

TUE, WED = date(2026, 9, 22), date(2026, 9, 23)


def week_with_comments() -> list[DayResult]:
    return [
        result(
            Outcome.ABSENT,
            employee_id=1,
            day=WED,
            comment="Avisó Beto Prueba que Ana Prueba estaba enferma",
        ),
        replace(
            result(Outcome.UNREGISTERED_CHANGE, employee_id=2, day=TUE),
            checkin=datetime(2026, 9, 22, 16, 41),
        ),
        result(Outcome.OK, employee_id=2, day=WED),
    ]


def call(tools: ReviewTools, name: str, **arguments: Any) -> Any:
    return json.loads(tools.call(name, arguments))


def test_tool_definitions_are_strict_and_closed() -> None:
    assert [t["name"] for t in TOOL_DEFINITIONS] == [
        "get_week_findings",
        "get_week_incidents",
        "get_employee_history",
        "get_employee_week",
    ]
    for tool in TOOL_DEFINITIONS:
        assert tool["strict"] is True
        assert tool["input_schema"]["additionalProperties"] is False


def test_week_findings_use_pseudonyms() -> None:
    findings = call(ReviewTools(make_context(week_with_comments())), "get_week_findings")
    assert [(f["kind"], f["employee"]) for f in findings] == [
        ("REST_DAY_CHECKIN", "E2"),
        ("ABSENT_NO_EXCEPTION", "E1"),
    ]
    assert findings[0]["facts"] == {"checkin_time": "16:41"}
    assert findings[1]["days"] == ["2026-09-23"]


def test_free_text_comments_are_scrubbed() -> None:
    # Review Focus #1: the manager's free text may name employees.
    raw = ReviewTools(make_context(week_with_comments())).call("get_week_incidents", {})
    assert "prueba" not in raw.casefold()
    data = json.loads(raw)
    absent = next(i for i in data["incidents"] if i["outcome"] == "ABSENT")
    assert absent["comment"] == "Avisó E2 que E1 estaba enferma"
    assert data["rh_rows"] == [
        {
            "employee": "E1",
            "day": "2026-09-23",
            "rh_type": "FALTA_INJUSTIFICADA",
            "comment": "Avisó E2 que E1 estaba enferma",
        }
    ]


def test_employee_week_lists_each_day() -> None:
    days = call(ReviewTools(make_context(week_with_comments())), "get_employee_week", employee="E2")
    assert [(d["day"], d["weekday"], d["outcome"], d["checkin"]) for d in days] == [
        ("2026-09-22", "martes", "UNREGISTERED_CHANGE", "16:41"),
        ("2026-09-23", "miércoles", "OK", None),
    ]


def test_employee_history_covers_only_the_requested_weeks() -> None:
    history = [
        result(Outcome.LATE, employee_id=1, day=date(2026, 9, 16)),  # W38
        result(Outcome.ABSENT, employee_id=1, day=date(2026, 9, 9)),  # W37
        result(Outcome.LATE, employee_id=2, day=date(2026, 9, 16)),
    ]
    tools = ReviewTools(make_context(history=history))
    assert call(tools, "get_employee_history", employee="E1", weeks=1) == [
        {
            "week": "2026-W38",
            "worked": 1,
            "late": 1,
            "late_justified": 0,
            "absent": 0,
            "absent_justified": 0,
            "unresolved": 0,
        }
    ]
    two_weeks = call(tools, "get_employee_history", employee="E1", weeks=2)
    assert [w["week"] for w in two_weeks] == ["2026-W37", "2026-W38"]


@pytest.mark.parametrize(
    "arguments",
    [
        {"employee": "E99", "weeks": 1},
        {"employee": "Ana", "weeks": 1},
        {"employee": "E1", "weeks": 0},
        {"employee": "E1", "weeks": 9},
        {"employee": "E1", "weeks": True},
        {"employee": "E1"},
        {},
    ],
)
def test_bad_history_arguments_raise_tool_errors(arguments: dict[str, Any]) -> None:
    with pytest.raises(ToolError):
        ReviewTools(make_context()).call("get_employee_history", arguments)


def test_unknown_tool_raises() -> None:
    with pytest.raises(ToolError, match="desconocida"):
        ReviewTools(make_context()).call("drop_tables", {})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/agents/test_tools.py -v`
Expected: FAIL con `ModuleNotFoundError: ... weekly_review.tools`.

- [ ] **Step 3: Write the implementation**

`backend/src/tabernas/agents/weekly_review/tools.py`:

```python
"""Read-only tools of the weekly-review agent (spec §5.2).

They answer from the ReviewContext computed by the service: no SR, no Postgres, no
writes. Employees appear only as E{id}; free text goes through scrub()."""

import json
from collections.abc import Callable, Mapping
from datetime import timedelta
from typing import Any

from tabernas.agents.pseudonyms import alias, parse_alias, scrub
from tabernas.domain.review_types import REVIEW_HISTORY_WEEKS, Finding, ReviewContext
from tabernas.domain.summary import Grouping, summarize
from tabernas.domain.types import DayResult, Outcome

INCIDENT_OUTCOMES = frozenset(
    {Outcome.LATE, Outcome.ABSENT, Outcome.UNREGISTERED_CHANGE, Outcome.JUSTIFIED}
)
WEEKDAYS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
_EMPLOYEE = {"type": "string", "description": "Seudónimo del empleado, p. ej. E12"}


class ToolError(ValueError):
    """Bad tool input. Sent back to Claude as an is_error tool_result."""


def _schema(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "get_week_findings",
        "description": "Hallazgos de la semana calculados por el sistema. Cada uno debe "
        "aparecer exactamente una vez en tu respuesta, con su id tal cual.",
        "input_schema": _schema({}),
        "strict": True,
    },
    {
        "name": "get_week_incidents",
        "description": "Incidencias de la semana (retardos, faltas, checadas en descanso, "
        "ausencias justificadas) y filas propuestas para capturar en RH.",
        "input_schema": _schema({}),
        "strict": True,
    },
    {
        "name": "get_employee_history",
        "description": "Resumen por semana de un empleado en las semanas anteriores a la "
        f"revisada (de 1 a {REVIEW_HISTORY_WEEKS}).",
        "input_schema": _schema(
            {"employee": _EMPLOYEE, "weeks": {"type": "integer", "description": "Semanas previas"}}
        ),
        "strict": True,
    },
    {
        "name": "get_employee_week",
        "description": "Día a día de un empleado en la semana revisada: lo planeado, el "
        "resultado, la hora de checada y comentarios.",
        "input_schema": _schema({"employee": _EMPLOYEE}),
        "strict": True,
    },
]


class ReviewTools:
    def __init__(self, context: ReviewContext) -> None:
        self._context = context
        self._employee_ids = {employee.id for employee in context.employees}

    def call(self, name: str, arguments: Mapping[str, Any]) -> str:
        handlers: dict[str, Callable[[], Any]] = {
            "get_week_findings": self._week_findings,
            "get_week_incidents": self._week_incidents,
            "get_employee_history": lambda: self._employee_history(
                self._employee(arguments), self._weeks(arguments)
            ),
            "get_employee_week": lambda: self._employee_week(self._employee(arguments)),
        }
        handler = handlers.get(name)
        if handler is None:
            raise ToolError(f"Herramienta desconocida: {name}")
        return json.dumps(handler(), ensure_ascii=False)

    def _week_findings(self) -> list[dict[str, Any]]:
        return [_finding_json(finding) for finding in self._context.findings]

    def _week_incidents(self) -> dict[str, Any]:
        incidents = [
            self._day_json(r) for r in self._context.week_results if r.outcome in INCIDENT_OUTCOMES
        ]
        rows = [
            {
                "employee": alias(row.employee_id),
                "day": row.day.isoformat(),
                "rh_type": row.rh_type.value,
                "comment": self._scrub(row.comment),
            }
            for row in self._context.rh_rows
        ]
        return {"incidents": incidents, "rh_rows": rows}

    def _employee_history(self, employee_id: int, weeks: int) -> list[dict[str, Any]]:
        start = self._context.start
        since = start - timedelta(weeks=weeks)
        results = [
            r
            for r in self._context.history_results
            if r.employee_id == employee_id and since <= r.day < start
        ]
        return [
            {
                "week": s.period,
                "worked": s.worked,
                "late": s.late,
                "late_justified": s.late_justified,
                "absent": s.absent,
                "absent_justified": s.absent_justified,
                "unresolved": s.unresolved,
            }
            for s in summarize(results, Grouping.WEEK)
        ]

    def _employee_week(self, employee_id: int) -> list[dict[str, Any]]:
        week = self._context.week_results
        return [self._day_json(r) for r in week if r.employee_id == employee_id]

    def _day_json(self, r: DayResult) -> dict[str, Any]:
        return {
            "employee": alias(r.employee_id),
            "day": r.day.isoformat(),
            "weekday": WEEKDAYS[r.day.weekday()],
            "planned": r.planned.value,
            "outcome": r.outcome.value,
            "checkin": r.checkin.strftime("%H:%M") if r.checkin else None,
            "minutes_late": r.minutes_late,
            "rh_type": r.rh_type.value if r.rh_type else None,
            "justified": r.justification_id is not None,
            "comment": self._scrub(r.comment),
        }

    def _scrub(self, text: str) -> str:
        return scrub(text, self._context.employees)

    def _employee(self, arguments: Mapping[str, Any]) -> int:
        raw = arguments.get("employee")
        employee_id = parse_alias(raw) if isinstance(raw, str) else None
        if employee_id is None or employee_id not in self._employee_ids:
            raise ToolError(f"Empleado desconocido: {raw!r}. Usa un seudónimo como E12.")
        return employee_id

    def _weeks(self, arguments: Mapping[str, Any]) -> int:
        weeks = arguments.get("weeks")
        error = ToolError(f"weeks debe ser un entero entre 1 y {REVIEW_HISTORY_WEEKS}")
        if isinstance(weeks, bool) or not isinstance(weeks, int):
            raise error
        if not 1 <= weeks <= REVIEW_HISTORY_WEEKS:
            raise error
        return weeks


def _finding_json(finding: Finding) -> dict[str, Any]:
    employee = alias(finding.employee_id) if finding.employee_id is not None else None
    return {
        "id": finding.id,
        "kind": finding.kind.value,
        "employee": employee,
        "days": [day.isoformat() for day in finding.days],
        "facts": dict(finding.facts),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/agents/test_tools.py -v && uv run ruff check . && uv run ruff format --check . && uv run pyright`
Expected: PASS; sin errores de lint, formato ni tipos.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tabernas/agents/weekly_review/tools.py backend/tests/agents/test_tools.py
git commit -m "feat: add read-only, pseudonymized tools for the review agent

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Loop del agente (`LiveReviewAgent`) y prompt

**Files:**
- Create: `backend/src/tabernas/agents/weekly_review/agent.py`
- Create: `backend/src/tabernas/agents/weekly_review/prompt.py`
- Create: `backend/src/tabernas/agents/weekly_review/runner.py`
- Test: `backend/tests/agents/test_runner.py`

**Interfaces:**
- Consumes: `ReviewTools`, `TOOL_DEFINITIONS`, `ToolError` (Task 10);
  `NARRATIVE_SCHEMA`, `parse_narrative`, `NarrativeFormatError`, `validate_narrative`
  (Task 9); `ReviewContext`, `Narrative` (Task 2).
- Produces:
  - `agent.ToolCall(id, name, input)`, `agent.ModelTurn(stop_reason, content, text,
    tool_calls, input_tokens, output_tokens)`, `agent.AgentApiError(RuntimeError)`,
    `agent.MessagesApi` (Protocol: `send(params: Mapping[str, Any]) -> ModelTurn`),
    `agent.AgentOutcome(narrative, error, model, input_tokens=0, output_tokens=0,
    attempts=0)`, `agent.ReviewAgent` (Protocol: `run(context) -> AgentOutcome`).
  - `prompt.SYSTEM_PROMPT: str`, `prompt.opening_message(context) -> str`,
    `prompt.retry_message(errors: Sequence[str]) -> str`.
  - `runner.LiveReviewAgent(api: MessagesApi, model: str)` implementa `ReviewAgent`;
    constantes `MAX_TURNS = 8`, `MAX_RETRIES = 1`, `MAX_TOKENS = 16000`,
    `EFFORT = "medium"`.

Contrato del loop (spec §5.1 y §5.4):
- Historial **solo se agrega**: cada respuesta se agrega tal cual (`content`), nunca se
  edita un mensaje anterior (requisito de *preserved thinking* de Opus 5.5).
- `stop_reason == "tool_use"` → ejecutar todas las llamadas y mandar todos los
  `tool_result` en **un** mensaje de usuario.
- `stop_reason == "end_turn"` → parsear y validar. Válido → listo. Inválido → un
  reintento con `retry_message(errors)`; si vuelve a fallar → sin narrativa, `error`
  empieza con `"Validación fallida: "`.
- Cualquier otro `stop_reason` (`refusal`, `max_tokens`, `pause_turn`…) → sin narrativa
  con mensaje en español.
- `AgentApiError` → sin narrativa, `error = str(exc)`.
- Más de 8 llamadas al API → sin narrativa, `"El agente excedió el límite de 8 vueltas."`.

- [ ] **Step 1: Write the failing tests**

`backend/tests/agents/test_runner.py`:

```python
import copy
import json
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

import pytest

from tabernas.agents.weekly_review.agent import AgentApiError, ModelTurn, ToolCall
from tabernas.agents.weekly_review.prompt import SYSTEM_PROMPT
from tabernas.agents.weekly_review.runner import MAX_TURNS, LiveReviewAgent
from tabernas.agents.weekly_review.schema import NARRATIVE_SCHEMA
from tabernas.agents.weekly_review.tools import TOOL_DEFINITIONS
from tabernas.domain.review_types import FindingKind, ReviewContext, SuggestedAction
from tabernas.domain.types import Outcome
from tests.agents.helpers import make_context
from tests.domain.factories import result

MODEL = "claude-opus-5-5"
FINDINGS_CALL = ToolCall("tu_1", "get_week_findings", {})


class ScriptedApi:
    """MessagesApi double: replays turns (or raises them) and records every request."""

    def __init__(self, turns: Sequence[ModelTurn | Exception]) -> None:
        self._turns = list(turns)
        self.requests: list[dict[str, Any]] = []

    def send(self, params: Mapping[str, Any]) -> ModelTurn:
        self.requests.append(copy.deepcopy(dict(params)))
        turn = self._turns.pop(0)
        if isinstance(turn, Exception):
            raise turn
        return turn


def tool_turn(*calls: ToolCall) -> ModelTurn:
    content = tuple(
        {"type": "tool_use", "id": c.id, "name": c.name, "input": dict(c.input)} for c in calls
    )
    return ModelTurn("tool_use", content, "", calls, input_tokens=100, output_tokens=10)


def final_turn(payload: Mapping[str, Any] | str, stop_reason: str = "end_turn") -> ModelTurn:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    content = ({"type": "text", "text": text},)
    return ModelTurn(stop_reason, content, text, (), input_tokens=200, output_tokens=50)


def answer(context: ReviewContext, skip: int = 0) -> dict[str, Any]:
    return {
        "summary": "Hay pendientes esta semana.",
        "items": [
            {
                "finding_id": f.id,
                "priority": "HIGH",
                "explanation": "Revisar el caso.",
                "suggested_action": "JUSTIFY",
            }
            for f in context.findings[skip:]
        ],
    }


def busy_context() -> ReviewContext:
    return make_context(
        [
            result(
                Outcome.ABSENT, employee_id=1, day=date(2026, 9, 23), comment="Avisó ANA PRUEBA"
            ),
            result(Outcome.ABSENT, employee_id=2, day=date(2026, 9, 21)),
        ]
    )


def run(api: ScriptedApi, context: ReviewContext | None = None) -> Any:
    return LiveReviewAgent(api, MODEL).run(context or busy_context())


def test_system_prompt_documents_every_kind_and_action() -> None:
    for value in [*(k.value for k in FindingKind), *(a.value for a in SuggestedAction)]:
        assert value in SYSTEM_PROMPT


def test_happy_path_reads_findings_and_returns_a_valid_narrative() -> None:
    context = busy_context()
    api = ScriptedApi([tool_turn(FINDINGS_CALL), final_turn(answer(context))])
    outcome = run(api, context)
    assert outcome.error is None and outcome.narrative is not None
    assert [i.finding_id for i in outcome.narrative.items] == [f.id for f in context.findings]
    assert (outcome.model, outcome.attempts) == (MODEL, 1)
    assert (outcome.input_tokens, outcome.output_tokens) == (300, 60)
    tool_message = api.requests[1]["messages"][-1]
    assert tool_message["role"] == "user"
    assert tool_message["content"][0]["tool_use_id"] == "tu_1"
    assert json.loads(tool_message["content"][0]["content"])[0]["id"] == context.findings[0].id


def test_request_shape() -> None:
    context = busy_context()
    api = ScriptedApi([final_turn(answer(context))])
    run(api, context)
    request = api.requests[0]
    assert (request["model"], request["max_tokens"]) == (MODEL, 16000)
    assert request["output_config"] == {
        "effort": "medium",
        "format": {"type": "json_schema", "schema": NARRATIVE_SCHEMA},
    }
    assert request["system"] == [
        {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}
    ]
    assert request["tools"] == TOOL_DEFINITIONS
    assert request["messages"][0]["role"] == "user"
    assert "2026-W39" in request["messages"][0]["content"]


def test_history_is_append_only() -> None:
    context = busy_context()
    api = ScriptedApi([tool_turn(FINDINGS_CALL), final_turn(answer(context))])
    run(api, context)
    first, second = api.requests[0]["messages"], api.requests[1]["messages"]
    assert second[: len(first)] == first


def test_missing_finding_triggers_one_retry() -> None:
    context = busy_context()
    api = ScriptedApi([final_turn(answer(context, skip=1)), final_turn(answer(context))])
    outcome = run(api, context)
    assert outcome.narrative is not None and outcome.attempts == 2
    retry = api.requests[1]["messages"][-1]
    assert retry["role"] == "user" and "Faltan hallazgos" in retry["content"]


def test_two_invalid_answers_give_no_narrative() -> None:
    context = busy_context()
    api = ScriptedApi([final_turn("no es json"), final_turn(answer(context, skip=1))])
    outcome = run(api, context)
    assert outcome.narrative is None and outcome.attempts == 2
    assert outcome.error is not None and outcome.error.startswith("Validación fallida: ")


def test_tool_errors_go_back_as_is_error_results() -> None:
    context = busy_context()
    bad = ToolCall("tu_9", "get_employee_week", {"employee": "E99"})
    api = ScriptedApi([tool_turn(bad), final_turn(answer(context))])
    assert run(api, context).narrative is not None
    block = api.requests[1]["messages"][-1]["content"][0]
    assert block["is_error"] is True and "E99" in block["content"]


@pytest.mark.parametrize(
    ("stop_reason", "message"),
    [("refusal", "declinó"), ("max_tokens", "se cortó"), ("pause_turn", "inesperadamente")],
)
def test_other_stop_reasons_give_no_narrative(stop_reason: str, message: str) -> None:
    outcome = run(ScriptedApi([final_turn("{}", stop_reason=stop_reason)]))
    assert outcome.narrative is None and message in (outcome.error or "")


def test_turn_limit() -> None:
    api = ScriptedApi([tool_turn(FINDINGS_CALL)] * MAX_TURNS)
    outcome = run(api)
    assert outcome.narrative is None and "límite" in (outcome.error or "")
    assert len(api.requests) == MAX_TURNS


def test_api_errors_are_reported() -> None:
    outcome = run(ScriptedApi([AgentApiError("No se pudo conectar con la API de Claude.")]))
    assert outcome.narrative is None
    assert outcome.error == "No se pudo conectar con la API de Claude."


def test_empty_week_is_a_valid_narrative() -> None:
    api = ScriptedApi([final_turn({"summary": "Semana sin pendientes.", "items": []})])
    assert run(api, make_context()).narrative is not None


def test_no_employee_name_is_ever_sent() -> None:
    # Review Focus #1: names must not reach the API, not even through tool results.
    context = busy_context()
    calls = [
        FINDINGS_CALL,
        ToolCall("tu_2", "get_week_incidents", {}),
        ToolCall("tu_3", "get_employee_week", {"employee": "E1"}),
        ToolCall("tu_4", "get_employee_history", {"employee": "E1", "weeks": 8}),
    ]
    api = ScriptedApi([tool_turn(*calls), final_turn(answer(context))])
    run(api, context)
    sent = json.dumps(api.requests, ensure_ascii=False).casefold()
    for employee in context.employees:
        for name in (employee.short_name, employee.rh_name or employee.short_name):
            assert name.casefold() not in sent
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/agents/test_runner.py -v`
Expected: FAIL con `ModuleNotFoundError: ... weekly_review.agent`.

- [ ] **Step 3: Write the implementation**

`backend/src/tabernas/agents/weekly_review/agent.py`:

```python
"""Contracts of the weekly-review agent: what the loop needs from the Messages API and
what any agent (live, fake, unconfigured) returns to the service."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from tabernas.domain.review_types import Narrative, ReviewContext


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    input: Mapping[str, Any]


@dataclass(frozen=True)
class ModelTurn:
    """One Messages API response, reduced to what the loop reads.

    `content` holds the raw blocks and is sent back unchanged (append-only history)."""

    stop_reason: str
    content: tuple[Any, ...]
    text: str
    tool_calls: tuple[ToolCall, ...]
    input_tokens: int
    output_tokens: int


class AgentApiError(RuntimeError):
    """The Messages API failed after the SDK's retries. The message is safe to store."""


class MessagesApi(Protocol):
    def send(self, params: Mapping[str, Any]) -> ModelTurn: ...


@dataclass(frozen=True)
class AgentOutcome:
    narrative: Narrative | None
    error: str | None
    model: str | None
    input_tokens: int = 0
    output_tokens: int = 0
    attempts: int = 0


class ReviewAgent(Protocol):
    def run(self, context: ReviewContext) -> AgentOutcome: ...
```

`backend/src/tabernas/agents/weekly_review/prompt.py`:

```python
"""Fixed system prompt (cacheable: no dates, no data) and the per-run user messages."""

from collections.abc import Sequence

from tabernas.domain.review_types import ReviewContext

SYSTEM_PROMPT = """\
Eres el asistente que prepara el borrador semanal de incidencias de asistencia de un \
bar-restaurante. El gerente lo revisa y aprueba antes de capturarlo en la herramienta de RH.

Contexto del negocio:
- Los empleados solo checan entrada. Hora de entrada: cocina 16:30, resto 16:40, con 10 \
minutos de tolerancia; pasando el minuto ya es retardo.
- Cada empleado descansa un día fijo por semana y, cada dos semanas, un día extra. Los \
cambios de descanso se registran como excepciones.
- El periodo es la semana ISO de lunes a domingo. El jueves se envía el reporte de la \
semana en curso y se aceptan ajustes hasta el domingo.

Tu trabajo:
1. Llama a get_week_findings. Esos hallazgos los calculó el sistema y son la base del \
borrador.
2. Usa las demás herramientas solo si necesitas contexto para explicar o priorizar un \
hallazgo.
3. Responde con el JSON del esquema: un resumen de 3 a 6 frases y exactamente un elemento \
por hallazgo, con su finding_id tal cual.

Reglas:
- No inventes hallazgos, fechas ni cifras. No calcules totales: si mencionas un número, \
debe venir tal cual de una herramienta.
- Nombra a los empleados solo con su seudónimo entre llaves, por ejemplo {E12}. No uses \
ni adivines nombres.
- Prioridad: HIGH si cambia lo que se capturará en RH esta semana y requiere acción del \
gerente (faltas sin justificar, rachas sin checar); MEDIUM si requiere revisión pero no \
cambia la captura (checada en descanso, retardos repetidos); LOW para avisos de \
configuración.
- Acción sugerida, según lo que el gerente puede hacer en la aplicación: JUSTIFY \
(justificar el retardo o la falta), REST_SWAP (registrar un cambio de descanso), \
ADD_EXCEPTION (registrar ausencia, cierre o asistencia sin checada), FIX_CONFIG (corregir \
empleados o reglas de descanso), NONE (solo informativo).
- Si no hay hallazgos, el resumen dice que la semana no tiene pendientes e items queda vacío.
- Escribe en español, claro y breve.

Tipos de hallazgo:
- REST_DAY_CHECKIN: checó en su día de descanso; suele ser un cambio de descanso sin registrar.
- ABSENT_NO_EXCEPTION: falta sin justificación ni excepción.
- NO_CHECKIN_STREAK: varios días laborales seguidos sin checar; puede ser olvido, ausencia \
larga o baja.
- REPEATED_LATE: retardos repetidos en la semana o en varias semanas recientes.
- CONFIG_WARNING: problema de configuración (sin regla de descanso, checadas de un id sin \
empleado, falta el nombre en RH, justificación sin incidencia o empleado sin id de SR).
"""


def opening_message(context: ReviewContext) -> str:
    return (
        f"Prepara el borrador de la semana {context.iso_year}-W{context.iso_week:02d} "
        f"(del lunes {context.start.isoformat()} al domingo {context.end.isoformat()}). "
        f"Datos tomados el {context.as_of:%Y-%m-%d %H:%M}; los días posteriores todavía "
        "no ocurren."
    )


def retry_message(errors: Sequence[str]) -> str:
    listed = "\n".join(f"- {error}" for error in errors)
    return (
        "Tu respuesta no pasó la validación. Corrige estos puntos y responde de nuevo con "
        f"el JSON completo:\n{listed}"
    )
```

`backend/src/tabernas/agents/weekly_review/runner.py`:

```python
"""LiveReviewAgent: an append-only tool loop over the Messages API (spec §5.1, §5.4)."""

from collections.abc import Sequence
from typing import Any

from tabernas.agents.weekly_review.agent import AgentApiError, AgentOutcome, MessagesApi, ToolCall
from tabernas.agents.weekly_review.prompt import SYSTEM_PROMPT, opening_message, retry_message
from tabernas.agents.weekly_review.schema import (
    NARRATIVE_SCHEMA,
    NarrativeFormatError,
    parse_narrative,
)
from tabernas.agents.weekly_review.tools import TOOL_DEFINITIONS, ReviewTools, ToolError
from tabernas.agents.weekly_review.validate import validate_narrative
from tabernas.domain.review_types import Narrative, ReviewContext

MAX_TURNS = 8
MAX_RETRIES = 1
MAX_TOKENS = 16000
EFFORT = "medium"
STOP_MESSAGES = {
    "refusal": "Claude declinó redactar este borrador.",
    "max_tokens": "La respuesta del agente se cortó por longitud.",
}
TURN_LIMIT_MESSAGE = f"El agente excedió el límite de {MAX_TURNS} vueltas."
Tokens = tuple[int, int]


class LiveReviewAgent:
    def __init__(self, api: MessagesApi, model: str) -> None:
        self._api = api
        self._model = model

    def run(self, context: ReviewContext) -> AgentOutcome:
        tools = ReviewTools(context)
        messages: list[dict[str, Any]] = [{"role": "user", "content": opening_message(context)}]
        tokens: Tokens = (0, 0)
        attempts = 0
        try:
            for _ in range(MAX_TURNS):
                turn = self._api.send(self._params(messages))
                tokens = (tokens[0] + turn.input_tokens, tokens[1] + turn.output_tokens)
                messages.append({"role": "assistant", "content": list(turn.content)})
                if turn.stop_reason == "tool_use":
                    results = tool_results(tools, turn.tool_calls)
                    messages.append({"role": "user", "content": results})
                    continue
                if turn.stop_reason != "end_turn":
                    return self._outcome(None, stop_message(turn.stop_reason), tokens, attempts)
                attempts += 1
                narrative, errors = check_answer(turn.text, context)
                if not errors:
                    return self._outcome(narrative, None, tokens, attempts)
                if attempts > MAX_RETRIES:
                    failure = "Validación fallida: " + "; ".join(errors)
                    return self._outcome(None, failure, tokens, attempts)
                messages.append({"role": "user", "content": retry_message(errors)})
        except AgentApiError as exc:
            return self._outcome(None, str(exc), tokens, attempts)
        return self._outcome(None, TURN_LIMIT_MESSAGE, tokens, attempts)

    def _params(self, messages: Sequence[dict[str, Any]]) -> dict[str, Any]:
        return {
            "model": self._model,
            "max_tokens": MAX_TOKENS,
            "system": [
                {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}
            ],
            "tools": TOOL_DEFINITIONS,
            "output_config": {
                "effort": EFFORT,
                "format": {"type": "json_schema", "schema": NARRATIVE_SCHEMA},
            },
            "messages": list(messages),
        }

    def _outcome(
        self, narrative: Narrative | None, error: str | None, tokens: Tokens, attempts: int
    ) -> AgentOutcome:
        return AgentOutcome(
            narrative=narrative,
            error=error,
            model=self._model,
            input_tokens=tokens[0],
            output_tokens=tokens[1],
            attempts=attempts,
        )


def stop_message(stop_reason: str) -> str:
    return STOP_MESSAGES.get(stop_reason, f"El agente se detuvo inesperadamente ({stop_reason}).")


def tool_results(tools: ReviewTools, calls: Sequence[ToolCall]) -> list[dict[str, Any]]:
    return [_tool_result(tools, call) for call in calls]


def _tool_result(tools: ReviewTools, call: ToolCall) -> dict[str, Any]:
    try:
        content = tools.call(call.name, call.input)
    except ToolError as exc:
        block = {"type": "tool_result", "tool_use_id": call.id, "content": str(exc)}
        return {**block, "is_error": True}
    return {"type": "tool_result", "tool_use_id": call.id, "content": content}


def check_answer(text: str, context: ReviewContext) -> tuple[Narrative | None, list[str]]:
    try:
        narrative = parse_narrative(text)
    except NarrativeFormatError as exc:
        return None, [str(exc)]
    return narrative, validate_narrative(narrative, context.findings, context.employees)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/agents -v && uv run ruff check . && uv run ruff format --check . && uv run pyright`
Expected: PASS; sin errores. (Si `ruff format --check` marca algo, correr
`uv run ruff format .` y volver a correr las pruebas.)

- [ ] **Step 5: Commit**

```bash
git add backend/src/tabernas/agents/weekly_review/agent.py backend/src/tabernas/agents/weekly_review/prompt.py backend/src/tabernas/agents/weekly_review/runner.py backend/tests/agents/test_runner.py
git commit -m "feat: add append-only tool loop for the weekly review agent

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: Adaptador del SDK, agente falso y fábrica

**Files:**
- Create: `backend/src/tabernas/agents/weekly_review/anthropic_api.py`
- Create: `backend/src/tabernas/agents/weekly_review/fake.py`
- Create: `backend/src/tabernas/agents/weekly_review/factory.py`
- Test: `backend/tests/agents/test_anthropic_api.py`, `backend/tests/agents/test_fake_and_factory.py`

**Interfaces:**
- Consumes: `ModelTurn`, `ToolCall`, `AgentApiError`, `AgentOutcome`, `ReviewAgent`
  (Task 11); `LiveReviewAgent` (Task 11); `Settings` (Task 1); `alias` (Task 8).
- Produces:
  - `anthropic_api.FALLBACK_BETA = "server-side-fallback-2026-07-01"`;
    `anthropic_api.AnthropicMessages(client: anthropic.Anthropic)` implementa
    `MessagesApi`: llama `client.beta.messages.create(**params, betas=[FALLBACK_BETA],
    extra_body={"fallbacks": "default"})` y traduce errores del SDK a `AgentApiError`.
  - `anthropic_api.to_model_turn(message: Any) -> ModelTurn` (los tokens de entrada
    incluyen los leídos y escritos en caché).
  - `fake.FAKE_MODEL = "fake"`, `fake.FakeReviewAgent` (determinista, pasa el validador),
    `fake.PRIORITY_BY_KIND`, `fake.ACTION_BY_KIND`.
  - `factory.MISSING_KEY_MESSAGE`, `factory.UnconfiguredReviewAgent`,
    `factory.build_review_agent(settings: Settings) -> ReviewAgent`.

- [ ] **Step 1: Write the failing tests**

`backend/tests/agents/test_anthropic_api.py`:

```python
from types import SimpleNamespace
from typing import Any, cast

import anthropic
import httpx
import pytest

from tabernas.agents.weekly_review.agent import AgentApiError, ToolCall
from tabernas.agents.weekly_review.anthropic_api import (
    FALLBACK_BETA,
    AnthropicMessages,
    to_model_turn,
)

REQUEST = httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def message(stop_reason: str = "tool_use") -> SimpleNamespace:
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[
            SimpleNamespace(type="thinking", thinking=""),
            SimpleNamespace(type="text", text="Reviso los hallazgos. "),
            SimpleNamespace(type="tool_use", id="tu_1", name="get_week_findings", input={}),
        ],
        usage=SimpleNamespace(
            input_tokens=10,
            output_tokens=5,
            cache_read_input_tokens=100,
            cache_creation_input_tokens=None,
        ),
    )


class FakeMessages:
    def __init__(self, outcome: Any) -> None:
        self._outcome = outcome
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome


def client_with(outcome: Any) -> tuple[anthropic.Anthropic, FakeMessages]:
    messages = FakeMessages(outcome)
    client = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    return cast(anthropic.Anthropic, client), messages


def test_to_model_turn_reduces_the_sdk_message() -> None:
    turn = to_model_turn(message())
    assert turn.stop_reason == "tool_use"
    assert turn.text == "Reviso los hallazgos. "
    assert turn.tool_calls == (ToolCall("tu_1", "get_week_findings", {}),)
    assert (turn.input_tokens, turn.output_tokens) == (110, 5)
    assert len(turn.content) == 3  # thinking blocks are kept to be sent back unchanged


def test_send_adds_the_fallback_beta_and_passes_params_through() -> None:
    client, messages = client_with(message("end_turn"))
    AnthropicMessages(client).send({"model": "claude-opus-5-5", "max_tokens": 10, "messages": []})
    assert messages.calls == [
        {
            "model": "claude-opus-5-5",
            "max_tokens": 10,
            "messages": [],
            "betas": [FALLBACK_BETA],
            "extra_body": {"fallbacks": "default"},
        }
    ]


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            anthropic.RateLimitError(
                "rate", response=httpx.Response(429, request=REQUEST), body=None
            ),
            "limitando",
        ),
        (
            anthropic.InternalServerError(
                "boom", response=httpx.Response(500, request=REQUEST), body=None
            ),
            "500",
        ),
        (anthropic.APIConnectionError(request=REQUEST), "conectar"),
    ],
)
def test_sdk_errors_become_agent_api_errors(error: Exception, expected: str) -> None:
    client, _ = client_with(error)
    with pytest.raises(AgentApiError, match=expected):
        AnthropicMessages(client).send({})
```

`backend/tests/agents/test_fake_and_factory.py`:

```python
from dataclasses import replace
from datetime import date, datetime

from tabernas.agents.weekly_review.factory import (
    MISSING_KEY_MESSAGE,
    UnconfiguredReviewAgent,
    build_review_agent,
)
from tabernas.agents.weekly_review.fake import FAKE_MODEL, FakeReviewAgent
from tabernas.agents.weekly_review.runner import LiveReviewAgent
from tabernas.agents.weekly_review.validate import validate_narrative
from tabernas.config import Settings
from tabernas.domain.review_types import FindingKind, ReviewContext, SuggestedAction
from tabernas.domain.types import AttendanceWarning, Outcome, WarningCode
from tests.agents.helpers import make_context
from tests.domain.factories import result

MON, TUE, WED, THU = (date(2026, 9, d) for d in (21, 22, 23, 24))


def every_kind() -> ReviewContext:
    week = [
        replace(
            result(Outcome.UNREGISTERED_CHANGE, employee_id=1, day=TUE),
            checkin=datetime(2026, 9, 22, 16, 41),
        ),
        result(Outcome.ABSENT, employee_id=2, day=MON),
        result(Outcome.ABSENT, employee_id=1, day=WED),
        result(Outcome.ABSENT, employee_id=1, day=THU),
        result(Outcome.LATE, employee_id=2, day=WED),
        result(Outcome.LATE, employee_id=2, day=THU),
    ]
    warnings = [AttendanceWarning(WarningCode.MISSING_RH_NAME, 2, None, "sin nombre RH")]
    return make_context(week, warnings=warnings)


def test_fake_agent_output_passes_the_validator() -> None:
    context = every_kind()
    assert {f.kind for f in context.findings} == set(FindingKind)
    outcome = FakeReviewAgent().run(context)
    assert outcome.narrative is not None and outcome.model == FAKE_MODEL
    assert validate_narrative(outcome.narrative, context.findings, context.employees) == []
    actions = {
        next(f.kind for f in context.findings if f.id == item.finding_id): item.suggested_action
        for item in outcome.narrative.items
    }
    assert actions[FindingKind.REST_DAY_CHECKIN] == SuggestedAction.REST_SWAP
    assert actions[FindingKind.CONFIG_WARNING] == SuggestedAction.FIX_CONFIG


def test_fake_agent_on_an_empty_week() -> None:
    outcome = FakeReviewAgent().run(make_context())
    assert outcome.narrative is not None
    assert outcome.narrative.items == ()
    assert "sin pendientes" in outcome.narrative.summary


def test_factory_returns_the_fake_agent_in_fake_mode() -> None:
    settings = Settings(_env_file=None, review_agent="fake")  # type: ignore[call-arg]
    assert isinstance(build_review_agent(settings), FakeReviewAgent)


def test_live_mode_without_key_saves_drafts_without_narrative() -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        review_agent="live",
        anthropic_api_key="",  # type: ignore[arg-type]
    )
    agent = build_review_agent(settings)
    assert isinstance(agent, UnconfiguredReviewAgent)
    outcome = agent.run(make_context())
    assert (outcome.narrative, outcome.error) == (None, MISSING_KEY_MESSAGE)


def test_live_mode_with_key_builds_the_real_agent() -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        review_agent="live",
        anthropic_api_key="sk-test",  # type: ignore[arg-type]
    )
    assert isinstance(build_review_agent(settings), LiveReviewAgent)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/agents/test_anthropic_api.py tests/agents/test_fake_and_factory.py -v`
Expected: FAIL con `ModuleNotFoundError` de `anthropic_api`, `fake` y `factory`.

- [ ] **Step 3: Write the implementation**

`backend/src/tabernas/agents/weekly_review/anthropic_api.py`:

```python
"""Adapter from the anthropic SDK to MessagesApi: SDK types and errors stop here."""

from collections.abc import Mapping
from typing import Any

import anthropic

from tabernas.agents.weekly_review.agent import AgentApiError, ModelTurn, ToolCall

# Server-side fallback on refusals: Anthropic picks the fallback model by refusal category.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicMessages:
    def __init__(self, client: anthropic.Anthropic) -> None:
        self._client = client

    def send(self, params: Mapping[str, Any]) -> ModelTurn:
        try:
            message = self._client.beta.messages.create(
                **params, betas=[FALLBACK_BETA], extra_body={"fallbacks": "default"}
            )
        except anthropic.RateLimitError as exc:
            raise AgentApiError(
                "La API de Claude está limitando las solicitudes; intenta más tarde."
            ) from exc
        except anthropic.APIStatusError as exc:
            status = exc.status_code
            raise AgentApiError(f"La API de Claude respondió con error {status}.") from exc
        except anthropic.APIConnectionError as exc:
            raise AgentApiError("No se pudo conectar con la API de Claude.") from exc
        return to_model_turn(message)


def to_model_turn(message: Any) -> ModelTurn:
    content = tuple(message.content)
    usage = message.usage
    cached = (getattr(usage, "cache_read_input_tokens", None) or 0) + (
        getattr(usage, "cache_creation_input_tokens", None) or 0
    )
    return ModelTurn(
        stop_reason=message.stop_reason or "",
        content=content,
        text="".join(block.text for block in content if block.type == "text"),
        tool_calls=tuple(
            ToolCall(id=block.id, name=block.name, input=dict(block.input))
            for block in content
            if block.type == "tool_use"
        ),
        input_tokens=usage.input_tokens + cached,
        output_tokens=usage.output_tokens,
    )
```

Si `pyright` no puede elegir una sobrecarga de `create` con `**params` (error
`reportCallIssue`), agregar al final de esa línea `# pyright: ignore[reportCallIssue]`:
los parámetros los arma `LiveReviewAgent._params` y la prueba de forma de petición de
Task 11 los fija.

`backend/src/tabernas/agents/weekly_review/fake.py`:

```python
"""Deterministic agent for REVIEW_AGENT=fake (demo, E2E, CI): no API calls, same contract."""

from collections.abc import Sequence

from tabernas.agents.pseudonyms import alias
from tabernas.agents.weekly_review.agent import AgentOutcome
from tabernas.domain.review_types import (
    Finding,
    FindingKind,
    Narrative,
    NarrativeItem,
    Priority,
    ReviewContext,
    SuggestedAction,
)

FAKE_MODEL = "fake"
PRIORITY_BY_KIND = {
    FindingKind.REST_DAY_CHECKIN: Priority.MEDIUM,
    FindingKind.ABSENT_NO_EXCEPTION: Priority.HIGH,
    FindingKind.NO_CHECKIN_STREAK: Priority.HIGH,
    FindingKind.REPEATED_LATE: Priority.MEDIUM,
    FindingKind.CONFIG_WARNING: Priority.LOW,
}
ACTION_BY_KIND = {
    FindingKind.REST_DAY_CHECKIN: SuggestedAction.REST_SWAP,
    FindingKind.ABSENT_NO_EXCEPTION: SuggestedAction.JUSTIFY,
    FindingKind.NO_CHECKIN_STREAK: SuggestedAction.ADD_EXCEPTION,
    FindingKind.REPEATED_LATE: SuggestedAction.NONE,
    FindingKind.CONFIG_WARNING: SuggestedAction.FIX_CONFIG,
}
TEMPLATES = {
    FindingKind.REST_DAY_CHECKIN: "{who} checó en su día de descanso; probablemente fue un "
    "cambio de descanso sin registrar.",
    FindingKind.ABSENT_NO_EXCEPTION: "{who} faltó sin justificación ni excepción registrada.",
    FindingKind.NO_CHECKIN_STREAK: "{who} lleva varios días laborales seguidos sin checar.",
    FindingKind.REPEATED_LATE: "{who} acumula retardos repetidos.",
    FindingKind.CONFIG_WARNING: "Hay un aviso de configuración que conviene corregir.",
}


class FakeReviewAgent:
    def run(self, context: ReviewContext) -> AgentOutcome:
        items = tuple(_item(finding) for finding in context.findings)
        narrative = Narrative(summary=_summary(context, items), items=items)
        return AgentOutcome(narrative=narrative, error=None, model=FAKE_MODEL, attempts=1)


def _who(finding: Finding) -> str:
    if finding.employee_id is None:
        return "Un empleado"
    return "{" + alias(finding.employee_id) + "}"


def _item(finding: Finding) -> NarrativeItem:
    return NarrativeItem(
        finding_id=finding.id,
        priority=PRIORITY_BY_KIND[finding.kind],
        explanation=TEMPLATES[finding.kind].format(who=_who(finding)),
        suggested_action=ACTION_BY_KIND[finding.kind],
    )


def _summary(context: ReviewContext, items: Sequence[NarrativeItem]) -> str:
    week = f"{context.iso_year}-W{context.iso_week:02d}"
    if not items:
        return f"Semana {week}: sin pendientes. Borrador de demostración."
    high = sum(item.priority == Priority.HIGH for item in items)
    return (
        f"Semana {week}: {len(items)} hallazgos, {high} de prioridad alta. "
        "Borrador de demostración."
    )
```

`backend/src/tabernas/agents/weekly_review/factory.py`:

```python
"""Picks the weekly-review agent from settings (spec E8)."""

import anthropic

from tabernas.agents.weekly_review.agent import AgentOutcome, ReviewAgent
from tabernas.agents.weekly_review.anthropic_api import AnthropicMessages
from tabernas.agents.weekly_review.fake import FakeReviewAgent
from tabernas.agents.weekly_review.runner import LiveReviewAgent
from tabernas.config import Settings
from tabernas.domain.review_types import ReviewContext

API_TIMEOUT_SECONDS = 120.0
API_MAX_RETRIES = 2
MISSING_KEY_MESSAGE = "Falta ANTHROPIC_API_KEY: el borrador se guardó sin narrativa."


class UnconfiguredReviewAgent:
    """REVIEW_AGENT=live without a key: drafts keep findings and RH rows, no narrative."""

    def run(self, context: ReviewContext) -> AgentOutcome:
        return AgentOutcome(narrative=None, error=MISSING_KEY_MESSAGE, model=None)


def build_review_agent(settings: Settings) -> ReviewAgent:
    if settings.review_agent == "fake":
        return FakeReviewAgent()
    key = settings.anthropic_api_key.get_secret_value()
    if not key:
        return UnconfiguredReviewAgent()
    client = anthropic.Anthropic(
        api_key=key, timeout=API_TIMEOUT_SECONDS, max_retries=API_MAX_RETRIES
    )
    return LiveReviewAgent(AnthropicMessages(client), settings.review_model)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/agents -v && uv run ruff check . && uv run ruff format --check . && uv run pyright`
Expected: PASS; sin errores.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tabernas/agents/weekly_review/anthropic_api.py backend/src/tabernas/agents/weekly_review/fake.py backend/src/tabernas/agents/weekly_review/factory.py backend/tests/agents/test_anthropic_api.py backend/tests/agents/test_fake_and_factory.py
git commit -m "feat: add Anthropic adapter, fake review agent and agent factory

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 13: Servicio de revisión (contexto, corrida, detalle y `stale`)

**Files:**
- Create: `backend/src/tabernas/services/review.py`
- Modify: `backend/src/tabernas/sr/source.py`, `backend/src/tabernas/api/errors.py`
  (mover `SR_UNAVAILABLE_MESSAGE`)
- Test: `backend/tests/services/test_review_service.py`

**Interfaces:**
- Consumes: `AttendanceService` (Etapa 1); `find_findings`; `ReviewSettingsRepo`,
  `ReviewRepo`, `EmployeeRepo`; `ReviewAgent`, `AgentOutcome`; `render` (Task 8);
  `FakeReviewAgent` (tests).
- Produces (`tabernas.services.review`):
  - `build_context(session, source, clock, iso_year, iso_week) -> ReviewContext` —
    semana completa + 8 semanas previas (dos llamadas a `AttendanceService.build`, ≤ 93
    días cada una); `employees` = todos (activos o no).
  - `run_review(factory, source, clock, agent, review_id) -> WeeklyReview` — SR caído →
    `FAILED` con `SR_UNAVAILABLE_MESSAGE`; narrativa → `READY`; sin narrativa →
    `READY_NO_NARRATIVE` con `error`. La llamada al agente ocurre **sin** transacción
    abierta.
  - `to_result(context, outcome) -> ReviewResult`.
  - `ReviewDetail(review, employees, stale)` y
    `review_detail(session, source, clock, review_id) -> ReviewDetail`.
  - `is_stale(session, source, clock, review) -> bool | None` — `None` si el estado no
    es `READY`/`READY_NO_NARRATIVE`/`APPROVED` o si SR no responde.
  - `render_narrative(narrative, employees) -> Narrative`.
- `tabernas.sr.source.SR_UNAVAILABLE_MESSAGE` (antes en `api/errors.py`).

- [ ] **Step 1: Write the failing tests**

`backend/tests/services/test_review_service.py`:

```python
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session, sessionmaker

from tabernas.agents.weekly_review.agent import AgentOutcome
from tabernas.agents.weekly_review.fake import FakeReviewAgent
from tabernas.domain.review_types import FindingKind, ReviewContext, ReviewStatus, ReviewTrigger
from tabernas.domain.types import Employee, Incident
from tabernas.repos.employees import EmployeeRepo
from tabernas.repos.justifications import JustificationRepo
from tabernas.repos.rest_rules import RestRuleRepo
from tabernas.repos.reviews import ReviewRepo
from tabernas.services.review import build_context, render_narrative, review_detail, run_review
from tabernas.sr.source import SR_UNAVAILABLE_MESSAGE, SrCheckin, SrUnavailableError
from tests.repos.helpers import make_employee
from tests.support import StubSource

Factory = sessionmaker[Session]
NOW = datetime(2026, 9, 27, 20, 0)  # Sunday evening of 2026-W39
HISTORY_START = date(2026, 7, 27)  # 8 weeks before 2026-09-21
EXPECTED_KINDS = [
    FindingKind.REST_DAY_CHECKIN,  # Tue 22 is his rest day and he checked in
    FindingKind.ABSENT_NO_EXCEPTION,  # Mon 21
    FindingKind.NO_CHECKIN_STREAK,  # Fri 25 – Sun 27
    FindingKind.CONFIG_WARNING,  # MISSING_RH_NAME
]


def clock() -> datetime:
    return NOW


def setup_employee(factory: Factory) -> Employee:
    with factory() as session:
        employee = make_employee(session, 7, short_name="EMPLEADO G")
        RestRuleRepo(session).create(
            employee_id=employee.id,
            fixed_weekday=1,  # Tuesday
            extra_weekday=0,  # Monday, only in double-rest weeks (not W39)
            double_rest_anchor=date(2026, 9, 28),
            valid_from=date(2026, 1, 1),
            valid_to=None,
        )
        session.commit()
        return employee


def checkins() -> StubSource:
    history = [
        SrCheckin(sr_id=7, at=datetime.combine(HISTORY_START + timedelta(days=d), time(16, 30)))
        for d in range(56)
    ]
    week = [
        SrCheckin(sr_id=7, at=datetime(2026, 9, 22, 16, 45)),  # rest day
        SrCheckin(sr_id=7, at=datetime(2026, 9, 23, 16, 51)),  # late (single: no finding)
        SrCheckin(sr_id=7, at=datetime(2026, 9, 24, 16, 40)),  # on time
    ]
    return StubSource(checkins=history + week)


def enqueue(factory: Factory) -> int:
    with factory() as session:
        review = ReviewRepo(session).enqueue(
            iso_year=2026, iso_week=39, trigger=ReviewTrigger.MANUAL
        )
        session.commit()
        return review.id


class NoNarrativeAgent:
    def run(self, context: ReviewContext) -> AgentOutcome:
        return AgentOutcome(None, "La API de Claude respondió con error 500.", "claude-opus-5-5")


def test_build_context_collects_week_history_and_findings(session_factory: Factory) -> None:
    employee = setup_employee(session_factory)
    with session_factory() as session:
        context = build_context(session, checkins(), clock, 2026, 39)
    assert [f.kind for f in context.findings] == EXPECTED_KINDS
    assert context.as_of == NOW
    assert min(r.day for r in context.history_results) == HISTORY_START
    assert max(r.day for r in context.history_results) == date(2026, 9, 20)
    assert [row.day.day for row in context.rh_rows] == [21, 23, 25, 26, 27]
    assert context.employees == (employee,)


def test_run_review_stores_a_ready_snapshot(session_factory: Factory) -> None:
    setup_employee(session_factory)
    review_id = enqueue(session_factory)
    done = run_review(session_factory, checkins(), clock, FakeReviewAgent(), review_id)
    assert done.status == ReviewStatus.READY
    assert [f.kind for f in done.findings] == EXPECTED_KINDS
    assert done.narrative is not None and len(done.narrative.items) == len(EXPECTED_KINDS)
    assert (done.as_of, done.model) == (NOW, "fake")
    with session_factory() as session:
        assert ReviewRepo(session).find_by_id(review_id) == done


def test_agent_failure_keeps_findings_without_narrative(session_factory: Factory) -> None:
    setup_employee(session_factory)
    review_id = enqueue(session_factory)
    done = run_review(session_factory, checkins(), clock, NoNarrativeAgent(), review_id)
    assert done.status == ReviewStatus.READY_NO_NARRATIVE
    assert done.error == "La API de Claude respondió con error 500."
    assert len(done.findings) == len(EXPECTED_KINDS) and len(done.rh_rows) == 5


def test_sr_unavailable_fails_the_review(session_factory: Factory) -> None:
    setup_employee(session_factory)
    review_id = enqueue(session_factory)
    source = StubSource(error=SrUnavailableError("down"))
    done = run_review(session_factory, source, clock, FakeReviewAgent(), review_id)
    assert (done.status, done.error) == (ReviewStatus.FAILED, SR_UNAVAILABLE_MESSAGE)


def test_detail_flags_stale_data_after_a_justification(session_factory: Factory) -> None:
    employee = setup_employee(session_factory)
    review_id = enqueue(session_factory)
    source = checkins()
    run_review(session_factory, source, clock, FakeReviewAgent(), review_id)
    with session_factory() as session:
        assert review_detail(session, source, clock, review_id).stale is False
        JustificationRepo(session).create(
            employee_id=employee.id,
            day=date(2026, 9, 21),
            incident=Incident.ABSENT,
            reason="Enfermo",
        )
        assert review_detail(session, source, clock, review_id).stale is True


def test_no_stale_flag_before_running_or_without_sr(session_factory: Factory) -> None:
    setup_employee(session_factory)
    review_id = enqueue(session_factory)
    with session_factory() as session:
        assert review_detail(session, checkins(), clock, review_id).stale is None
    run_review(session_factory, checkins(), clock, FakeReviewAgent(), review_id)
    down = StubSource(error=SrUnavailableError("down"))
    with session_factory() as session:
        assert review_detail(session, down, clock, review_id).stale is None


def test_detail_renders_names_of_deactivated_employees(session_factory: Factory) -> None:
    # Review Focus #5
    employee = setup_employee(session_factory)
    review_id = enqueue(session_factory)
    run_review(session_factory, checkins(), clock, FakeReviewAgent(), review_id)
    with session_factory() as session:
        EmployeeRepo(session).update(employee.id, {"active": False})
        session.commit()
        detail = review_detail(session, checkins(), clock, review_id)
    assert detail.review.narrative is not None
    rendered = render_narrative(detail.review.narrative, detail.employees)
    assert rendered.items[0].explanation.startswith("EMPLEADO G")
    assert "{E" not in rendered.summary + "".join(i.explanation for i in rendered.items)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/services/test_review_service.py -v`
Expected: FAIL con `ImportError` de `SR_UNAVAILABLE_MESSAGE` y
`ModuleNotFoundError: tabernas.services.review`.

- [ ] **Step 3: Write the implementation**

En `backend/src/tabernas/sr/source.py`, después de `logger = ...`:

```python
SR_UNAVAILABLE_MESSAGE = "No se pudo leer SoftRestaurant. Revisa Tailscale."
```

En `backend/src/tabernas/api/errors.py`, borrar la línea
`SR_UNAVAILABLE_MESSAGE = "No se pudo leer SoftRestaurant. Revisa Tailscale."` y cambiar
el import a:

```python
from tabernas.sr.source import SR_UNAVAILABLE_MESSAGE, SrNotReadOnlyError, SrUnavailableError
```

`backend/src/tabernas/services/review.py`:

```python
"""Weekly review drafts (spec §5–§7): builds the context, runs the agent, stores the
snapshot and answers the detail view."""

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from sqlalchemy.orm import Session, sessionmaker

from tabernas.agents.pseudonyms import render
from tabernas.agents.weekly_review.agent import AgentOutcome, ReviewAgent
from tabernas.domain.periods import iso_week_range
from tabernas.domain.review import find_findings
from tabernas.domain.review_types import (
    REVIEW_HISTORY_WEEKS,
    Narrative,
    ReviewContext,
    ReviewResult,
    ReviewStatus,
    WeeklyReview,
    proposed_rows,
)
from tabernas.domain.types import Employee
from tabernas.repos.employees import EmployeeRepo
from tabernas.repos.review_settings import ReviewSettingsRepo
from tabernas.repos.reviews import ReviewRepo
from tabernas.services.attendance import AttendanceService
from tabernas.sr.source import SR_UNAVAILABLE_MESSAGE, SrSource, SrUnavailableError

logger = logging.getLogger(__name__)

Clock = Callable[[], datetime]
STALE_CHECK_STATUSES = frozenset(
    {ReviewStatus.READY, ReviewStatus.READY_NO_NARRATIVE, ReviewStatus.APPROVED}
)


@dataclass(frozen=True)
class ReviewDetail:
    review: WeeklyReview
    employees: tuple[Employee, ...]
    stale: bool | None


def build_context(
    session: Session, source: SrSource, clock: Clock, iso_year: int, iso_week: int
) -> ReviewContext:
    start, end = iso_week_range(iso_year, iso_week)
    attendance = AttendanceService(session, source, clock)
    week = attendance.build(start, end)
    history = attendance.build(
        start - timedelta(weeks=REVIEW_HISTORY_WEEKS), start - timedelta(days=1)
    )
    settings = ReviewSettingsRepo(session).get()
    findings = find_findings(week.results, history.results, week.warnings, settings, start, end)
    return ReviewContext(
        iso_year=iso_year,
        iso_week=iso_week,
        start=start,
        end=end,
        as_of=clock(),
        employees=tuple(EmployeeRepo(session).find_all()),
        week_results=week.results,
        history_results=history.results,
        rh_rows=proposed_rows(week.rh_rows),
        findings=tuple(findings),
    )


def run_review(
    factory: sessionmaker[Session],
    source: SrSource,
    clock: Clock,
    agent: ReviewAgent,
    review_id: int,
) -> WeeklyReview:
    with factory() as session:
        review = ReviewRepo(session).find_by_id(review_id)
        try:
            context = build_context(session, source, clock, review.iso_year, review.iso_week)
        except SrUnavailableError:
            logger.warning("Weekly review %s failed: SR unavailable", review_id)
            failed = ReviewRepo(session).fail(review_id, SR_UNAVAILABLE_MESSAGE)
            session.commit()
            return failed
    outcome = agent.run(context)  # may take a minute: no open transaction meanwhile
    with factory() as session:
        done = ReviewRepo(session).complete(review_id, to_result(context, outcome))
        session.commit()
    logger.info(
        "Weekly review %s: %s, %d findings, tokens in/out %d/%d",
        review_id,
        done.status,
        len(done.findings),
        outcome.input_tokens,
        outcome.output_tokens,
    )
    return done


def to_result(context: ReviewContext, outcome: AgentOutcome) -> ReviewResult:
    ready = outcome.narrative is not None
    return ReviewResult(
        status=ReviewStatus.READY if ready else ReviewStatus.READY_NO_NARRATIVE,
        as_of=context.as_of,
        findings=context.findings,
        rh_rows=context.rh_rows,
        narrative=outcome.narrative,
        model=outcome.model,
        input_tokens=outcome.input_tokens,
        output_tokens=outcome.output_tokens,
        error=outcome.error,
    )


def review_detail(
    session: Session, source: SrSource, clock: Clock, review_id: int
) -> ReviewDetail:
    review = ReviewRepo(session).find_by_id(review_id)
    employees = tuple(EmployeeRepo(session).find_all())
    return ReviewDetail(
        review=review, employees=employees, stale=is_stale(session, source, clock, review)
    )


def is_stale(
    session: Session, source: SrSource, clock: Clock, review: WeeklyReview
) -> bool | None:
    """True when today's findings or RH rows differ from the snapshot (spec §7.3)."""
    if review.status not in STALE_CHECK_STATUSES:
        return None
    try:
        current = build_context(session, source, clock, review.iso_year, review.iso_week)
    except SrUnavailableError:
        return None
    same_findings = [f.id for f in current.findings] == [f.id for f in review.findings]
    return not (same_findings and current.rh_rows == review.rh_rows)


def render_narrative(narrative: Narrative, employees: Sequence[Employee]) -> Narrative:
    return Narrative(
        summary=render(narrative.summary, employees),
        items=tuple(
            replace(item, explanation=render(item.explanation, employees))
            for item in narrative.items
        ),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/services tests/api -v`
Expected: PASS (los nuevos y los de la Etapa 1; `test_errors.py` sigue verde con el
mensaje movido).

- [ ] **Step 5: Commit**

```bash
git add backend/src/tabernas/services/review.py backend/src/tabernas/sr/source.py backend/src/tabernas/api/errors.py backend/tests/services/test_review_service.py
git commit -m "feat: add weekly review service with snapshot and stale check

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 14: API `/reviews`

**Files:**
- Create: `backend/src/tabernas/api/routes/reviews.py`
- Modify: `backend/src/tabernas/api/routes/__init__.py`
- Test: `backend/tests/api/test_reviews.py`

**Interfaces:**
- Consumes: `ReviewRepo` (Task 7); `review_detail`, `render_narrative`, `ReviewDetail`
  (Task 13); `SessionDep`, `SrSourceDep`, `ClockDep`, `Envelope`, `ok` (Etapa 1).
- Produces (contrato que usa el Plan B; spec §7.2):
  - `POST /reviews` `{year: 2000–2100, week: 1–53}` → **202** `ReviewSummaryOut`;
    409 `CONFLICT` si hay una en curso; 422 si la semana ISO no existe.
  - `GET /reviews?year&week` → `list[ReviewSummaryOut]` (sin filtros: las 20 más
    recientes; un solo filtro → 422).
  - `GET /reviews/{id}` → `ReviewDetailOut`; 404 si no existe.
  - `POST /reviews/{id}/approve` → `ReviewSummaryOut`; 409 si no está lista o ya se
    aprobó. `approved_at` = reloj de la app.
  - `ReviewSummaryOut = {id, year, week, trigger, status, created_at, as_of, approved_at, error}`.
  - `ReviewDetailOut = ReviewSummaryOut + {findings: [{id, kind, employee_id,
    employee_name, days, facts}], narrative: {summary, items: [{finding_id, priority,
    explanation, suggested_action}]} | null, rh_rows: [{employee_id, name, day, rh_type,
    comment}], model, input_tokens, output_tokens, stale}`. Los textos llegan con nombres
    cortos ya sustituidos; `rh_rows` usa el nombre en RH (o el corto) y va ordenado por
    nombre y día.

- [ ] **Step 1: Write the failing tests**

`backend/tests/api/test_reviews.py`:

```python
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tabernas.domain.review_types import (
    Finding,
    FindingKind,
    Narrative,
    NarrativeItem,
    Priority,
    ProposedRhRow,
    ReviewResult,
    ReviewStatus,
    ReviewTrigger,
    SuggestedAction,
)
from tabernas.domain.types import RhType
from tabernas.repos.reviews import ReviewRepo
from tabernas.sr.source import SrUnavailableError
from tests.api.conftest import FIXED_NOW, MakeClient
from tests.repos.helpers import make_employee
from tests.support import StubSource

WEEK_39 = {"year": 2026, "week": 39}


def ready_review(session: Session) -> int:
    employee = make_employee(session, 7, short_name="EMPLEADO G")
    token = "{E" + str(employee.id) + "}"
    repo = ReviewRepo(session)
    review = repo.enqueue(iso_year=2026, iso_week=39, trigger=ReviewTrigger.MANUAL)
    finding = Finding(
        f"ABSENT_NO_EXCEPTION:{employee.id}:2026-09-23",
        FindingKind.ABSENT_NO_EXCEPTION,
        employee.id,
        (date(2026, 9, 23),),
    )
    narrative = Narrative(
        f"Una falta de {token}.",
        (NarrativeItem(finding.id, Priority.HIGH, f"{token} faltó.", SuggestedAction.JUSTIFY),),
    )
    row = ProposedRhRow(employee.id, date(2026, 9, 23), RhType.FALTA_INJUSTIFICADA, "")
    result = ReviewResult(
        status=ReviewStatus.READY,
        as_of=FIXED_NOW,
        findings=(finding,),
        rh_rows=(row,),
        narrative=narrative,
        model="claude-opus-5-5",
        input_tokens=900,
        output_tokens=150,
        error=None,
    )
    repo.complete(review.id, result)
    session.commit()
    return review.id


def test_post_enqueues_and_rejects_a_second_run(client: TestClient) -> None:
    response = client.post("/reviews", json=WEEK_39)
    assert response.status_code == 202
    data = response.json()["data"]
    assert (data["year"], data["week"], data["status"], data["trigger"]) == (
        2026,
        39,
        "QUEUED",
        "MANUAL",
    )
    conflict = client.post("/reviews", json=WEEK_39)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "CONFLICT"


def test_post_rejects_weeks_that_do_not_exist(client: TestClient) -> None:
    assert client.post("/reviews", json={"year": 2026, "week": 54}).status_code == 422
    response = client.post("/reviews", json={"year": 2025, "week": 53})
    assert response.status_code == 422
    assert "Semana ISO inválida" in response.json()["error"]["message"]


def test_list_filters_by_week(client: TestClient) -> None:
    client.post("/reviews", json={"year": 2026, "week": 38})
    client.post("/reviews", json=WEEK_39)
    assert [r["week"] for r in client.get("/reviews").json()["data"]] == [39, 38]
    only_38 = client.get("/reviews", params={"year": 2026, "week": 38}).json()["data"]
    assert [r["week"] for r in only_38] == [38]
    assert client.get("/reviews", params={"year": 2026}).status_code == 422


def test_detail_renders_names_and_flags_stale_data(client: TestClient, session: Session) -> None:
    review_id = ready_review(session)
    data = client.get(f"/reviews/{review_id}").json()["data"]
    assert data["narrative"]["summary"] == "Una falta de EMPLEADO G."
    assert data["narrative"]["items"][0]["explanation"] == "EMPLEADO G faltó."
    assert data["findings"][0]["employee_name"] == "EMPLEADO G"
    assert data["rh_rows"][0]["name"] == "EMPLEADO G"
    assert data["rh_rows"][0]["rh_type"] == "FALTA_INJUSTIFICADA"
    assert (data["model"], data["input_tokens"], data["output_tokens"]) == (
        "claude-opus-5-5",
        900,
        150,
    )
    assert data["stale"] is True  # live data (no check-ins at all) no longer matches


def test_detail_without_sr_has_no_stale_flag(make_client: MakeClient, session: Session) -> None:
    review_id = ready_review(session)
    client = make_client(StubSource(error=SrUnavailableError("down")))
    assert client.get(f"/reviews/{review_id}").json()["data"]["stale"] is None


def test_missing_review_is_404(client: TestClient) -> None:
    assert client.get("/reviews/999").status_code == 404


def test_ready_review_is_approved_once(client: TestClient, session: Session) -> None:
    review_id = ready_review(session)
    approved = client.post(f"/reviews/{review_id}/approve").json()["data"]
    assert approved["status"] == "APPROVED"
    assert approved["approved_at"] == FIXED_NOW.isoformat()
    assert client.post(f"/reviews/{review_id}/approve").status_code == 409


def test_queued_review_cannot_be_approved(client: TestClient) -> None:
    queued = client.post("/reviews", json=WEEK_39).json()["data"]
    assert client.post(f"/reviews/{queued['id']}/approve").status_code == 409
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/api/test_reviews.py -v`
Expected: FAIL (404 en todas las rutas `/reviews`).

- [ ] **Step 3: Write the implementation**

`backend/src/tabernas/api/routes/reviews.py`:

```python
"""Weekly review drafts (spec §7.2). The API only enqueues and reads; the worker runs them."""

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from tabernas.api.deps import ClockDep, SessionDep, SrSourceDep
from tabernas.api.envelope import Envelope, ok
from tabernas.domain.review_types import (
    FindingKind,
    Narrative,
    Priority,
    ReviewStatus,
    ReviewTrigger,
    SuggestedAction,
    WeeklyReview,
)
from tabernas.domain.types import Employee, RhType
from tabernas.domain.validation import DomainValidationError
from tabernas.repos.reviews import ReviewRepo
from tabernas.services.review import ReviewDetail, render_narrative, review_detail

router = APIRouter(prefix="/reviews", tags=["reviews"])


class ReviewCreate(BaseModel):
    year: int = Field(ge=2000, le=2100)
    week: int = Field(ge=1, le=53)


class ReviewSummaryOut(BaseModel):
    id: int
    year: int
    week: int
    trigger: ReviewTrigger
    status: ReviewStatus
    created_at: datetime
    as_of: datetime | None
    approved_at: datetime | None
    error: str | None


class FindingOut(BaseModel):
    id: str
    kind: FindingKind
    employee_id: int | None
    employee_name: str | None
    days: list[date]
    facts: dict[str, int | str]


class NarrativeItemOut(BaseModel):
    finding_id: str
    priority: Priority
    explanation: str
    suggested_action: SuggestedAction


class NarrativeOut(BaseModel):
    summary: str
    items: list[NarrativeItemOut]


class ProposedRowOut(BaseModel):
    employee_id: int
    name: str
    day: date
    rh_type: RhType
    comment: str


class ReviewDetailOut(ReviewSummaryOut):
    findings: list[FindingOut]
    narrative: NarrativeOut | None
    rh_rows: list[ProposedRowOut]
    model: str | None
    input_tokens: int | None
    output_tokens: int | None
    stale: bool | None


def summary_out(review: WeeklyReview) -> ReviewSummaryOut:
    return ReviewSummaryOut(
        id=review.id,
        year=review.iso_year,
        week=review.iso_week,
        trigger=review.trigger,
        status=review.status,
        created_at=review.created_at,
        as_of=review.as_of,
        approved_at=review.approved_at,
        error=review.error,
    )


def _short_name(by_id: Mapping[int, Employee], employee_id: int | None) -> str | None:
    employee = by_id.get(employee_id) if employee_id is not None else None
    return employee.short_name if employee else None


def _rh_name(by_id: Mapping[int, Employee], employee_id: int) -> str:
    employee = by_id.get(employee_id)
    if employee is None:
        return f"Empleado {employee_id}"
    return employee.rh_name or employee.short_name


def _narrative_out(
    narrative: Narrative | None, employees: Sequence[Employee]
) -> NarrativeOut | None:
    if narrative is None:
        return None
    rendered = render_narrative(narrative, employees)
    items = [
        NarrativeItemOut(
            finding_id=item.finding_id,
            priority=item.priority,
            explanation=item.explanation,
            suggested_action=item.suggested_action,
        )
        for item in rendered.items
    ]
    return NarrativeOut(summary=rendered.summary, items=items)


def detail_out(detail: ReviewDetail) -> ReviewDetailOut:
    review = detail.review
    by_id = {employee.id: employee for employee in detail.employees}
    findings = [
        FindingOut(
            id=f.id,
            kind=f.kind,
            employee_id=f.employee_id,
            employee_name=_short_name(by_id, f.employee_id),
            days=list(f.days),
            facts=dict(f.facts),
        )
        for f in review.findings
    ]
    rows = [
        ProposedRowOut(
            employee_id=r.employee_id,
            name=_rh_name(by_id, r.employee_id),
            day=r.day,
            rh_type=r.rh_type,
            comment=r.comment,
        )
        for r in review.rh_rows
    ]
    return ReviewDetailOut(
        **summary_out(review).model_dump(),
        findings=findings,
        narrative=_narrative_out(review.narrative, detail.employees),
        rh_rows=sorted(rows, key=lambda row: (row.name, row.day)),
        model=review.model,
        input_tokens=review.input_tokens,
        output_tokens=review.output_tokens,
        stale=detail.stale,
    )


@router.post("", status_code=202)
def create_review(body: ReviewCreate, session: SessionDep) -> Envelope[ReviewSummaryOut]:
    review = ReviewRepo(session).enqueue(
        iso_year=body.year, iso_week=body.week, trigger=ReviewTrigger.MANUAL
    )
    return ok(summary_out(review))


@router.get("")
def list_reviews(
    session: SessionDep,
    year: Annotated[int | None, Query()] = None,
    week: Annotated[int | None, Query()] = None,
) -> Envelope[list[ReviewSummaryOut]]:
    if (year is None) != (week is None):
        raise DomainValidationError("Indica año y semana juntos, o ninguno")
    reviews = ReviewRepo(session).find_all(iso_year=year, iso_week=week)
    return ok([summary_out(review) for review in reviews])


@router.get("/{review_id}")
def get_review(
    review_id: int, session: SessionDep, source: SrSourceDep, clock: ClockDep
) -> Envelope[ReviewDetailOut]:
    return ok(detail_out(review_detail(session, source, clock, review_id)))


@router.post("/{review_id}/approve")
def approve_review(
    review_id: int, session: SessionDep, clock: ClockDep
) -> Envelope[ReviewSummaryOut]:
    return ok(summary_out(ReviewRepo(session).approve(review_id, clock())))
```

En `backend/src/tabernas/api/routes/__init__.py`, agregar `reviews` al import y
`reviews.router` al final de `ROUTERS`:

```python
from tabernas.api.routes import (
    attendance,
    employees,
    exceptions,
    health,
    justifications,
    rest_rules,
    reviews,
    settings,
)

ROUTERS: list[APIRouter] = [
    health.router,
    employees.router,
    settings.router,
    rest_rules.router,
    exceptions.router,
    justifications.router,
    attendance.router,
    reviews.router,
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/api -v && uv run ruff check . && uv run ruff format --check . && uv run pyright`
Expected: PASS; sin errores.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tabernas/api/routes/reviews.py backend/src/tabernas/api/routes/__init__.py backend/tests/api/test_reviews.py
git commit -m "feat: add weekly review API

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 15: Worker y servicio en Docker Compose

**Files:**
- Create: `backend/src/tabernas/worker.py`
- Modify: `docker-compose.yml`
- Test: `backend/tests/test_worker.py`

**Interfaces:**
- Consumes: `slot_to_enqueue` (Task 5); `ReviewRepo` (Task 7); `run_review` (Task 13);
  `build_review_agent` (Task 12); `local_clock` de `tabernas.main`; `build_sr_source`.
- Produces (`tabernas.worker`):
  - `POLL_SECONDS = 10`, `INTERNAL_ERROR_MESSAGE`.
  - `schedule_due(factory, clock) -> WeeklyReview | None` — encola la ranura vencida
    (≤ 24 h) si no existe una corrida con ese disparador para esa semana; si hay una
    manual en curso, espera a la siguiente vuelta.
  - `fail_stale(factory) -> int`.
  - `run_next(factory, source, clock, agent) -> WeeklyReview | None` — toma una de la
    cola y la corre; una excepción inesperada deja la fila en `FAILED` con
    `INTERNAL_ERROR_MESSAGE` (detalle solo en log).
  - `tick(factory, source, clock, agent) -> None` — `fail_stale`, `schedule_due` y
    vacía la cola.
  - `main()` — loop infinito cada `POLL_SECONDS`; una vuelta que falla (p. ej. Postgres
    caído) se registra y se reintenta.
- Servicio `worker` en `docker-compose.yml`: misma imagen que `backend`, comando
  `python -m tabernas.worker`, `REVIEW_AGENT` por defecto `fake`, arranca cuando el
  backend está sano (el backend corre las migraciones).

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_worker.py`:

```python
from collections.abc import Callable
from datetime import datetime, timedelta

from sqlalchemy import func, update
from sqlalchemy.orm import Session, sessionmaker

from tabernas.agents.weekly_review.agent import AgentOutcome
from tabernas.agents.weekly_review.fake import FakeReviewAgent
from tabernas.db.models import WeeklyReviewRow
from tabernas.domain.review_types import ReviewContext, ReviewStatus, ReviewTrigger
from tabernas.repos.reviews import STALE_RUNNING_MESSAGE, ReviewRepo
from tabernas.worker import INTERNAL_ERROR_MESSAGE, fail_stale, run_next, schedule_due, tick
from tests.support import StubSource

Factory = sessionmaker[Session]
THURSDAY_EVENING = datetime(2026, 9, 24, 17, 31)
SATURDAY_NOON = datetime(2026, 9, 26, 12, 0)


def at(moment: datetime) -> Callable[[], datetime]:
    return lambda: moment


class ExplodingAgent:
    def run(self, context: ReviewContext) -> AgentOutcome:
        raise RuntimeError("boom")


def statuses(factory: Factory) -> list[ReviewStatus]:
    with factory() as session:
        return [review.status for review in ReviewRepo(session).find_all()]


def test_schedule_due_enqueues_the_thursday_slot_once(session_factory: Factory) -> None:
    review = schedule_due(session_factory, at(THURSDAY_EVENING))
    assert review is not None
    assert (review.trigger, review.iso_year, review.iso_week) == (
        ReviewTrigger.THURSDAY,
        2026,
        39,
    )
    assert schedule_due(session_factory, at(THURSDAY_EVENING)) is None
    assert statuses(session_factory) == [ReviewStatus.QUEUED]


def test_schedule_due_skips_slots_older_than_a_day(session_factory: Factory) -> None:
    assert schedule_due(session_factory, at(SATURDAY_NOON)) is None
    assert statuses(session_factory) == []


def test_schedule_due_waits_for_a_manual_run_of_the_same_week(session_factory: Factory) -> None:
    with session_factory() as session:
        ReviewRepo(session).enqueue(iso_year=2026, iso_week=39, trigger=ReviewTrigger.MANUAL)
        session.commit()
    assert schedule_due(session_factory, at(THURSDAY_EVENING)) is None
    assert statuses(session_factory) == [ReviewStatus.QUEUED]


def test_run_next_processes_the_queue(session_factory: Factory) -> None:
    schedule_due(session_factory, at(THURSDAY_EVENING))
    clock = at(THURSDAY_EVENING)
    done = run_next(session_factory, StubSource(), clock, FakeReviewAgent())
    assert done is not None and done.status == ReviewStatus.READY
    assert run_next(session_factory, StubSource(), clock, FakeReviewAgent()) is None


def test_unexpected_errors_fail_the_review(session_factory: Factory) -> None:
    schedule_due(session_factory, at(THURSDAY_EVENING))
    failed = run_next(session_factory, StubSource(), at(THURSDAY_EVENING), ExplodingAgent())
    assert failed is not None
    assert (failed.status, failed.error) == (ReviewStatus.FAILED, INTERNAL_ERROR_MESSAGE)


def test_fail_stale_frees_interrupted_runs(session_factory: Factory) -> None:
    # Review Focus #4
    schedule_due(session_factory, at(THURSDAY_EVENING))
    with session_factory() as session:
        ReviewRepo(session).claim_next()
        session.execute(
            update(WeeklyReviewRow).values(updated_at=func.now() - timedelta(minutes=20))
        )
        session.commit()
    assert fail_stale(session_factory) == 1
    with session_factory() as session:
        (review,) = ReviewRepo(session).find_all()
    assert (review.status, review.error) == (ReviewStatus.FAILED, STALE_RUNNING_MESSAGE)


def test_tick_schedules_and_runs(session_factory: Factory) -> None:
    tick(session_factory, StubSource(), at(THURSDAY_EVENING), FakeReviewAgent())
    assert statuses(session_factory) == [ReviewStatus.READY]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_worker.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'tabernas.worker'`.

- [ ] **Step 3: Write the worker and the compose service**

`backend/src/tabernas/worker.py`:

```python
"""Background worker (spec §6): schedules weekly reviews and runs queued ones.

Run with `python -m tabernas.worker` (compose service `worker`). It is the only process
that executes reviews; the API only enqueues them."""

import logging
import time
from collections.abc import Callable
from datetime import datetime

from sqlalchemy.orm import Session, sessionmaker

from tabernas.agents.weekly_review.agent import ReviewAgent
from tabernas.agents.weekly_review.factory import build_review_agent
from tabernas.config import get_settings
from tabernas.db.session import make_engine, make_session_factory
from tabernas.domain.review_schedule import slot_to_enqueue
from tabernas.domain.review_types import WeeklyReview
from tabernas.main import local_clock
from tabernas.repos.errors import ConflictError
from tabernas.repos.reviews import ReviewRepo
from tabernas.services.review import run_review
from tabernas.sr import build_sr_source
from tabernas.sr.source import SrSource

logger = logging.getLogger("tabernas.worker")

POLL_SECONDS = 10
INTERNAL_ERROR_MESSAGE = "Error interno al generar el borrador; revisa los logs del worker."
Factory = sessionmaker[Session]
Clock = Callable[[], datetime]


def schedule_due(factory: Factory, clock: Clock) -> WeeklyReview | None:
    slot = slot_to_enqueue(clock())
    if slot is None:
        return None
    with factory() as session:
        repo = ReviewRepo(session)
        if repo.exists(iso_year=slot.iso_year, iso_week=slot.iso_week, trigger=slot.trigger):
            return None
        try:
            review = repo.enqueue(
                iso_year=slot.iso_year, iso_week=slot.iso_week, trigger=slot.trigger
            )
        except ConflictError:
            return None  # a manual run of that week is in progress; next tick retries
        session.commit()
    logger.info("Enqueued %s review for %s-W%02d", slot.trigger, slot.iso_year, slot.iso_week)
    return review


def fail_stale(factory: Factory) -> int:
    with factory() as session:
        count = ReviewRepo(session).fail_stale_running()
        session.commit()
    if count:
        logger.warning("Marked %d interrupted review(s) as failed", count)
    return count


def run_next(
    factory: Factory, source: SrSource, clock: Clock, agent: ReviewAgent
) -> WeeklyReview | None:
    with factory() as session:
        claimed = ReviewRepo(session).claim_next()
        session.commit()
    if claimed is None:
        return None
    try:
        return run_review(factory, source, clock, agent, claimed.id)
    except Exception:
        logger.exception("Weekly review %s failed unexpectedly", claimed.id)
        with factory() as session:
            failed = ReviewRepo(session).fail(claimed.id, INTERNAL_ERROR_MESSAGE)
            session.commit()
        return failed


def tick(factory: Factory, source: SrSource, clock: Clock, agent: ReviewAgent) -> None:
    fail_stale(factory)
    schedule_due(factory, clock)
    while run_next(factory, source, clock, agent) is not None:
        continue


def main() -> None:  # pragma: no cover - process entry point, exercised through compose
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    settings = get_settings()
    factory = make_session_factory(make_engine(settings.database_url))
    source = build_sr_source(settings)
    clock = local_clock(settings.app_timezone)
    agent = build_review_agent(settings)
    logger.info("Worker started (review agent: %s)", settings.review_agent)
    while True:
        try:
            tick(factory, source, clock, agent)
        except Exception:
            logger.exception("Worker tick failed; retrying in %ss", POLL_SECONDS)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":  # pragma: no cover
    main()
```

En `docker-compose.yml`, agregar el servicio después de `backend` (antes de `frontend`):

```yaml
  worker:
    build:
      context: .
      dockerfile: backend/Dockerfile
    command: ["python", "-m", "tabernas.worker"]
    env_file:
      - path: .env
        required: false  # CI and the public demo run without a .env
    environment:
      SR_MODE: ${SR_MODE:-fake}
      REVIEW_AGENT: ${REVIEW_AGENT:-fake}  # the real machine's .env sets REVIEW_AGENT=live
      DATABASE_URL: postgresql+psycopg://tabernas:${POSTGRES_PASSWORD:-tabernas}@db:5432/tabernas
      FREETDSCONF: /etc/freetds/freetds.conf
    volumes:
      - ./freetds.conf:/etc/freetds/freetds.conf:ro
    depends_on:
      backend:
        condition: service_healthy  # the backend applies the migrations on start
    restart: unless-stopped
```

- [ ] **Step 4: Run tests and verify the worker in the demo stack**

Run: `uv run pytest tests/test_worker.py -v`
Expected: PASS (7 tests).

Luego, desde la raíz del repo, comprobar el worker de punta a punta con el stack de
demo (aislado de los datos reales; ver CLAUDE.md). `docker compose stop` detiene el
stack real; al final se restaura con `start`, que **no** crea el worker en el stack
real (ese paso lo decide el gerente en Task 17):

```bash
docker compose config --services            # debe incluir: db backend worker frontend
docker compose stop
SR_MODE=fake REVIEW_AGENT=fake docker compose -p tabernas-demo up -d --build --wait
SR_MODE=fake docker compose -p tabernas-demo run --rm backend python /scripts/seed_demo.py
curl -s -X POST http://127.0.0.1:8000/reviews -H 'content-type: application/json' -d '{"year": 2026, "week": 39}'
for i in 1 2 3 4 5 6; do curl -s 'http://127.0.0.1:8000/reviews?year=2026&week=39' | grep -o '"status":"[A-Z_]*"' | head -1; sleep 5; done
docker compose -p tabernas-demo logs worker | tail -5
docker compose -p tabernas-demo down -v
docker compose start
```

Expected: el estado pasa de `QUEUED` a `READY` en unos segundos; el log del worker
muestra `Worker started (review agent: fake)` y `Weekly review 1: READY, …`.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tabernas/worker.py backend/tests/test_worker.py docker-compose.yml
git commit -m "feat: add review worker and compose service

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 16: Evaluación del agente con la API real (`@pytest.mark.agent`)

**Files:**
- Modify: `backend/pyproject.toml` (marcador `agent`, excluido por defecto)
- Create: `backend/tests/eval/__init__.py` (vacío), `backend/tests/eval/scenarios.py`
- Create: `backend/tests/eval/test_weekly_review_eval.py`

**Interfaces:**
- Consumes: `make_context`, `ANA`, `BETO` (Task 8); `LiveReviewAgent` (Task 11);
  `AnthropicMessages` (Task 12); `Settings` (Task 1).
- Produces: `Scenario(name, context, expected_high, expected_actions)` y `SCENARIOS`
  (7 semanas sintéticas); el comando `uv run pytest -m agent -s`.

Esta suite **cuesta dinero** (≈ 7 corridas de Opus 5.5) y nunca corre en CI: el
`addopts` excluye `agent` igual que `sr`. Cubre la aceptación #3 y #4 del spec: el
validador pasa a la primera, prioridades y acciones esperadas en casos claros, y ningún
nombre sale hacia la API (se registra cada payload).

- [ ] **Step 1: Register the marker**

En `backend/pyproject.toml`, `[tool.pytest.ini_options]`:

```toml
addopts = "-m 'not sr and not agent' --strict-markers"
markers = [
    "sr: needs the live SoftRestaurant server (local only, never in CI)",
    "agent: calls the real Claude API (costs money; local only, never in CI)",
]
```

Run: `uv run pytest -q`
Expected: la suite completa pasa como antes (nada marcado todavía).

- [ ] **Step 2: Write the scenarios and the evaluation**

`backend/tests/eval/scenarios.py`:

```python
"""Synthetic weeks with expected agent behavior (spec §10.2). No real data."""

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import date, datetime

from tabernas.domain.review_types import FindingKind, ReviewContext, SuggestedAction
from tabernas.domain.types import AttendanceWarning, DayResult, Outcome, WarningCode
from tests.agents.helpers import make_context
from tests.domain.factories import result

MON, TUE, WED, THU, FRI = (date(2026, 9, d) for d in (21, 22, 23, 24, 25))
JUSTIFY_OR_EXCEPTION = frozenset({SuggestedAction.JUSTIFY, SuggestedAction.ADD_EXCEPTION})


@dataclass(frozen=True)
class Scenario:
    name: str
    context: ReviewContext
    expected_high: frozenset[FindingKind] = frozenset()
    expected_actions: Mapping[FindingKind, frozenset[SuggestedAction]] = field(
        default_factory=dict
    )


def _ok_days(employee_id: int, days: tuple[date, ...]) -> list[DayResult]:
    return [result(Outcome.OK, employee_id=employee_id, day=d) for d in days]


STREAK = [result(Outcome.ABSENT, employee_id=1, day=d) for d in (WED, THU, FRI)]
REST_CHECKIN = [
    replace(
        result(Outcome.UNREGISTERED_CHANGE, employee_id=2, day=TUE),
        checkin=datetime(2026, 9, 22, 16, 38),
    )
]
LATES = [result(Outcome.LATE, employee_id=1, day=d) for d in (MON, TUE)]
LATE_HISTORY = [result(Outcome.LATE, employee_id=1, day=date(2026, 9, d)) for d in (9, 16)]
ABSENCE_WITH_NOTE = [
    result(Outcome.ABSENT, employee_id=2, day=MON, comment="Avisó BETO PRUEBA por teléfono")
]
NO_RULE = [AttendanceWarning(WarningCode.NO_REST_RULE, 2, MON, "Sin regla de descanso vigente")]

SCENARIOS = (
    Scenario("semana limpia", make_context(_ok_days(1, (MON, WED)) + _ok_days(2, (MON, WED)))),
    Scenario(
        "racha sin checar",
        make_context(STREAK + _ok_days(2, (WED, THU))),
        expected_high=frozenset({FindingKind.NO_CHECKIN_STREAK}),
        expected_actions={FindingKind.NO_CHECKIN_STREAK: JUSTIFY_OR_EXCEPTION},
    ),
    Scenario(
        "checada en descanso",
        make_context(REST_CHECKIN),
        expected_actions={FindingKind.REST_DAY_CHECKIN: frozenset({SuggestedAction.REST_SWAP})},
    ),
    Scenario(
        "retardos repetidos",
        make_context(LATES, history=LATE_HISTORY),
        expected_actions={
            FindingKind.REPEATED_LATE: frozenset({SuggestedAction.NONE, SuggestedAction.JUSTIFY})
        },
    ),
    Scenario(
        "aviso de configuración",
        make_context(warnings=NO_RULE),
        expected_actions={FindingKind.CONFIG_WARNING: frozenset({SuggestedAction.FIX_CONFIG})},
    ),
    Scenario(
        "falta con comentario",
        make_context(ABSENCE_WITH_NOTE),
        expected_high=frozenset({FindingKind.ABSENT_NO_EXCEPTION}),
        expected_actions={FindingKind.ABSENT_NO_EXCEPTION: JUSTIFY_OR_EXCEPTION},
    ),
    Scenario(
        "semana mezclada",
        make_context(STREAK + REST_CHECKIN + ABSENCE_WITH_NOTE, warnings=NO_RULE),
        expected_high=frozenset(
            {FindingKind.NO_CHECKIN_STREAK, FindingKind.ABSENT_NO_EXCEPTION}
        ),
        expected_actions={
            FindingKind.REST_DAY_CHECKIN: frozenset({SuggestedAction.REST_SWAP}),
            FindingKind.CONFIG_WARNING: frozenset({SuggestedAction.FIX_CONFIG}),
        },
    ),
)
```

`backend/tests/eval/test_weekly_review_eval.py`:

```python
"""Live evaluation of the weekly-review agent (spec §10.2). Costs money: local only.

Run from backend/: uv run pytest -m agent -s   (needs ANTHROPIC_API_KEY in .env)"""

import json
from collections.abc import Mapping
from typing import Any

import anthropic
import pytest

from tabernas.agents.weekly_review.agent import ModelTurn
from tabernas.agents.weekly_review.anthropic_api import AnthropicMessages
from tabernas.agents.weekly_review.runner import LiveReviewAgent
from tabernas.config import Settings
from tabernas.domain.review_types import Priority
from tests.eval.scenarios import SCENARIOS, Scenario

pytestmark = pytest.mark.agent

INPUT_USD_PER_MTOK = 4.0  # claude-opus-5-5 list price; cache reads are cheaper
OUTPUT_USD_PER_MTOK = 20.0


class RecordingMessages:
    """Wraps the real adapter and keeps every payload sent, to check for names."""

    def __init__(self, inner: AnthropicMessages) -> None:
        self._inner = inner
        self.payloads: list[str] = []

    def send(self, params: Mapping[str, Any]) -> ModelTurn:
        self.payloads.append(json.dumps(params, ensure_ascii=False, default=str))
        return self._inner.send(params)


@pytest.fixture(scope="module")
def live() -> tuple[anthropic.Anthropic, str]:
    settings = Settings()
    key = settings.anthropic_api_key.get_secret_value()
    if not key:
        pytest.skip("ANTHROPIC_API_KEY no está configurada")
    return anthropic.Anthropic(api_key=key, timeout=120.0, max_retries=2), settings.review_model


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_agent_on_synthetic_week(
    scenario: Scenario, live: tuple[anthropic.Anthropic, str]
) -> None:
    client, model = live
    api = RecordingMessages(AnthropicMessages(client))
    outcome = LiveReviewAgent(api, model).run(scenario.context)
    cost = (
        outcome.input_tokens * INPUT_USD_PER_MTOK + outcome.output_tokens * OUTPUT_USD_PER_MTOK
    ) / 1_000_000
    print(
        f"\n[{scenario.name}] intentos={outcome.attempts} llamadas={len(api.payloads)} "
        f"tokens={outcome.input_tokens}/{outcome.output_tokens} costo≈${cost:.4f}"
    )
    sent = "\n".join(api.payloads).casefold()
    for employee in scenario.context.employees:
        for name in filter(None, (employee.short_name, employee.rh_name)):
            assert name.casefold() not in sent, f"{name} salió hacia la API"
    assert outcome.narrative is not None, outcome.error
    assert outcome.attempts == 1, "el validador debe pasar a la primera"
    kinds = {finding.id: finding.kind for finding in scenario.context.findings}
    for item in outcome.narrative.items:
        kind = kinds[item.finding_id]
        if kind in scenario.expected_high:
            assert item.priority == Priority.HIGH, item
        allowed = scenario.expected_actions.get(kind)
        if allowed:
            assert item.suggested_action in allowed, item
```

- [ ] **Step 3: Check that the suite is collected but excluded by default**

Run: `uv run pytest -q` y luego `uv run pytest -m agent --collect-only -q`
Expected: la primera no corre ninguna prueba de `tests/eval`; la segunda lista 7.

- [ ] **Step 4: Run the live evaluation (local, with the user's approval of the cost)**

Pedir aprobación al gerente antes de correrla (≈ 7 corridas de Opus 5.5, centavos de
dólar). Con `ANTHROPIC_API_KEY` en `.env`:

Run: `uv run pytest -m agent -s`
Expected: 7 PASS; cada línea `[escenario] intentos=1 …` con su costo. Si un escenario
falla por prioridad o acción, ajustar `prompt.py` (no los umbrales del validador) y
volver a correr solo ese escenario con `-k "<nombre>"`. Registrar los costos en la
descripción del PR.

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/tests/eval
git commit -m "test: add live evaluation suite for the weekly review agent

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 17: CI, documentación y verificación final

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `CLAUDE.md`
- Modify: `docs/plan.md`

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: CI con `REVIEW_AGENT=fake` explícito; documentación del layout, reglas y
  comandos nuevos.

- [ ] **Step 1: CI**

En `.github/workflows/ci.yml`, en el `env` del job `backend`, agregar:

```yaml
      REVIEW_AGENT: fake
```

Y en el `env` del job `e2e` (junto a `SR_MODE: fake`):

```yaml
      REVIEW_AGENT: fake
```

- [ ] **Step 2: CLAUDE.md**

1. En el párrafo de **Status**, reemplazar
   `Next is Stage 2 (weekly review agent), which needs its design spec in `docs/specs/` before any code.`
   por:
   `Stage 2 (weekly review agent) is in progress: spec
   `docs/specs/2026-10-01-etapa-2-revision-semanal-design.md`, plans
   `docs/plans/2026-10-01-etapa-2-plan-*.md` (A = backend, B = frontend).`
2. En **Backend layout**, agregar al final de la lista:

```markdown
- `domain/review*.py` — weekly-review findings (`review.py`), types and the Thu 17:30 /
  Mon 09:00 schedule slots; pure, like the rest of `domain/`.
- `agents/` — Claude agents. `pseudonyms.py`: Claude only ever sees `E{id}`.
  `weekly_review/`: append-only tool loop (`runner.py`) behind the `MessagesApi`
  protocol, read-only tools over a precomputed `ReviewContext`, and a validator that
  enforces exact coverage of the findings. `anthropic_api.py` is the only SDK adapter.
- `services/review.py` — builds the review context, runs the agent, stores the snapshot.
- `worker.py` — the only process that runs reviews (compose service `worker`,
  `python -m tabernas.worker`); the API only enqueues.
```

3. En **Hard rules**, agregar:

```markdown
- **Nothing sent to the Anthropic API may identify an employee.** Agent tools return
  `E{id}`, free text goes through `scrub()`, and the validator rejects names.
```

4. En **Gotchas**, agregar:

```markdown
- `REVIEW_AGENT` defaults to `fake` (no API calls). With `live` and no
  `ANTHROPIC_API_KEY`, drafts are saved without narrative. On the real stack the worker
  enqueues the last due slot (Thu 17:30 / Mon 09:00) if it is less than 24 h old, so the
  first `docker compose up` after a slot can call Claude right away.
```

5. En **Commands**, agregar:

```markdown
- Worker logs: `docker compose logs -f worker`
- Live agent evaluation (costs money; local only, never CI; from `backend/`): `uv run pytest -m agent -s`
```

   y en el comando de **Full demo** cambiar
   `SR_MODE=fake docker compose -p tabernas-demo up -d --build --wait` por
   `SR_MODE=fake REVIEW_AGENT=fake docker compose -p tabernas-demo up -d --build --wait`.

- [ ] **Step 3: docs/plan.md**

En la sección `### Etapa 2 — Agente de revisión semanal`, reemplazar la línea de estado
por:

```markdown
> Estado: **en implementación** — diseño en
> [`specs/2026-10-01-etapa-2-revision-semanal-design.md`](specs/2026-10-01-etapa-2-revision-semanal-design.md);
> Plan A (backend) en [`plans/2026-10-01-etapa-2-plan-a-backend.md`](plans/2026-10-01-etapa-2-plan-a-backend.md)
> y Plan B (frontend) en [`plans/2026-10-01-etapa-2-plan-b-frontend.md`](plans/2026-10-01-etapa-2-plan-b-frontend.md).
```

Y en la tabla de stack, la fila **Agentes** pasa a:
`| Agentes | Claude vía Messages API (SDK `anthropic`), `claude-opus-5-5`, loop propio con herramientas | Decidido en el diseño de la etapa 2 |`

- [ ] **Step 4: Full verification**

Run (desde `backend/`):

```bash
uv run ruff check . && uv run ruff format --check . && uv run pyright
uv run pytest --cov --cov-report=term-missing
uv run coverage report --include="*/tabernas/domain/*" --fail-under=95
```

Expected: todo en verde; cobertura global ≥ 80%; `domain/` ≥ 95%. Revisar que en el
reporte `agents/`, `services/review.py`, `repos/reviews.py` y `worker.py` (salvo
`main()`) estén cubiertos.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml CLAUDE.md docs/plan.md
git commit -m "docs: document the weekly review agent and run CI with the fake agent

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 6: Primera corrida real (con el gerente)**

No es código: el gerente decide cuándo encender el worker en el stack real. Con
`REVIEW_AGENT=live` y la llave en `.env`:

```bash
docker compose up -d --build backend worker
docker compose logs -f worker
```

Generar desde la API el borrador de una semana ya revisada a mano
(`POST /reviews {year, week}`) y comparar con esa revisión: los hallazgos deben coincidir
con lo que el gerente marcó, y la lista para RH con la que capturó. Anotar diferencias
como ajustes de umbrales o reglas en un issue antes del Plan B.

---

## Commands

| Acción | Comando (desde `backend/`) |
|---|---|
| Pruebas | `uv run pytest` |
| Cobertura (como CI) | `uv run pytest --cov && uv run coverage report --include="*/tabernas/domain/*" --fail-under=95` |
| Lint y tipos | `uv run ruff check . && uv run ruff format --check . && uv run pyright` |
| Evaluación con Claude (local, cuesta) | `uv run pytest -m agent -s` |
| Worker en el stack | `docker compose up -d --build worker && docker compose logs -f worker` |
