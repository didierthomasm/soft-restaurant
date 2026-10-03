# Asistencia, mejoras · Plan A — Backend

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que cada día del calendario traiga la excepción que lo afecta y que la lista de
incidencias y la de RH se filtren (empleado, tipo, estado) y paginen desde el API.

**Architecture:** La excepción viaja como dato desde `domain/planning.py` (`PlannedDay`)
por `domain/compare.py` (`DayResult`) hasta `DayOut`. Un módulo puro nuevo,
`domain/incident_filter.py`, filtra y pagina; las rutas de `api/routes/attendance.py`
solo arman el filtro, llaman al servicio (sin cambios) y devuelven
`meta {total, page, limit}`. Nada nuevo toca SR.

**Tech Stack:** Python 3.12, uv, FastAPI, Pydantic 2, pytest, ruff, pyright.

**Spec:** [`docs/specs/2026-10-03-asistencia-mejoras-design.md`](../specs/2026-10-03-asistencia-mejoras-design.md)
(leerlo completo antes de empezar; §3 es este plan). El frontend es el **Plan B**
([`2026-10-03-asistencia-mejoras-plan-b-frontend.md`](2026-10-03-asistencia-mejoras-plan-b-frontend.md)).

## Global Constraints

- **SR es producción, solo lectura.** Este plan no agrega consultas a SR: todo pasa por
  `AttendanceService.build()`, que no cambia.
- Rango máximo 93 días (`validate_range`, sin cambios). Página ≥ 1; tamaño 1–100,
  por defecto 25.
- Tipos de incidencia del filtro: `LATE`, `ABSENT`, `UNREGISTERED_CHANGE`, `JUSTIFIED`.
  Estado: `all` (default), `justified`, `unjustified`.
- Justificado = `justification_id` no nulo **o** resultado `JUSTIFIED`. Todo lo demás
  (incluido `UNREGISTERED_CHANGE`) es sin justificar.
- Los cierres del local (`STORE_CLOSED`) **no** se asignan como excepción del día.
- Respuesta: envelope `{success, data, error, meta}`; paginación en
  `meta = {"total", "page", "limit"}`.
- Dataclasses del dominio `frozen=True`; el dominio no importa FastAPI ni SQLAlchemy.
- Funciones < 50 líneas, archivos < 400 líneas.
- Repo público: pruebas con datos sintéticos (demo `FakeSource`, factories).
- Código, identificadores y commits en inglés; mensajes de error en español.
- Comandos **desde `backend/`**, con `docker compose up -d db` levantado. Si sale
  `No module named 'tabernas'`, usar `.venv/bin/python -m pytest` (ver CLAUDE.md).
- Commits `<type>: <description>` cerrando con
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Cada `git commit` en su
  propia llamada (un hook bloquea comandos con `-n`).

## Review Focus

1. **Página más allá del final** (p. ej. se aplica un filtro estando en la página 4):
   devuelve `items` vacío con el `total` real, no 404 ni 422. → test en Task 2 y Task 4.
2. **Excepción de varios días:** cada día del rango trae la **misma** excepción (mismo
   `id`, mismas fechas), no una por día. → test en Task 1 y Task 3.
3. **Falta registrada a mano y además justificada:** el día conserva su excepción y su
   justificación. → test en Task 1.
4. **Filtro de RH por tipo `UNREGISTERED_CHANGE`:** no produce filas (no se capturan en
   RH) y no falla. → test en Task 4.
5. **El aviso de pendientes no depende del filtro de tipo/estado**: con
   `type=LATE`, `unresolved` sigue contando los cambios sin registrar del empleado. →
   test en Task 2 y Task 4.

---

## Estructura de archivos

```
backend/src/tabernas/
  domain/types.py              + PlannedDay.exception, DayResult.exception
  domain/planning.py           _plan_day adjunta la excepción del empleado
  domain/compare.py            copia la excepción al resultado
  domain/incident_filter.py    NUEVO: IncidentType, IncidentStatus, IncidentFilter,
                               filter_incidents, count_unresolved, PageRequest, Page, paginate
  api/routes/attendance.py     ExceptionRef en DayOut; /incidents paginado; /rh-rows nuevo
backend/tests/
  domain/test_planning.py      + excepción por día
  domain/test_compare.py       + excepción en el resultado
  domain/test_justify.py       + falta a mano justificada conserva excepción
  domain/test_incident_filter.py  NUEVO
  api/test_attendance.py       DayOut.exception, filtros, paginación, /rh-rows
```

---

### Task 1: La excepción del empleado viaja con su día (dominio)

**Files:**
- Modify: `backend/src/tabernas/domain/types.py` (`PlannedDay`, `DayResult`)
- Modify: `backend/src/tabernas/domain/planning.py` (`_plan_day`)
- Modify: `backend/src/tabernas/domain/compare.py` (`_evaluate`)
- Test: `backend/tests/domain/test_planning.py`, `test_compare.py`, `test_justify.py`

**Interfaces:**
- Produces: `PlannedDay.exception: ScheduleException | None = None` y
  `DayResult.exception: ScheduleException | None = None` (último campo de cada
  dataclass, con default, para no romper constructores posicionales existentes).

- [ ] **Step 1: Write the failing tests**

Al final de `backend/tests/domain/test_planning.py`:

```python
def test_each_employee_exception_travels_with_its_day() -> None:
    absence = exception(
        ExceptionKind.WORK_TO_ABSENCE,
        date(2026, 9, 23),
        until=date(2026, 9, 24),
        rh_type=RhType.VACACIONES,
        id=5,
    )
    manual = exception(ExceptionKind.MANUAL_ABSENCE, date(2026, 9, 25), id=6)
    extra = exception(ExceptionKind.REST_TO_WORK, date(2026, 9, 22), id=7)  # Tue = rest
    present = exception(ExceptionKind.PRESENT_NO_CHECKIN, date(2026, 9, 26), id=8)
    planned, _ = planned_calendar(
        [employee()], [rule()], [absence, manual, extra, present], *WEEK_39
    )
    days = by_day(planned)
    assert days[date(2026, 9, 23)].exception == absence
    assert days[date(2026, 9, 24)].exception == absence  # same object for the whole range
    assert days[date(2026, 9, 25)].exception == manual
    assert days[date(2026, 9, 22)].exception == extra
    assert days[date(2026, 9, 26)].exception == present
    assert days[date(2026, 9, 21)].exception is None


def test_store_closure_is_not_the_employee_exception() -> None:
    closure = exception(ExceptionKind.STORE_CLOSED, date(2026, 9, 24), id=1)
    planned, _ = planned_calendar([employee()], [rule()], [closure], *WEEK_39)
    assert by_day(planned)[date(2026, 9, 24)].exception is None
```

Al final de `backend/tests/domain/test_compare.py` (agregar `ExceptionKind` al import de
`tabernas.domain.types` y `exception` al de `tests.domain.factories`):

```python
def test_result_keeps_the_planned_exception() -> None:
    absence = exception(ExceptionKind.WORK_TO_ABSENCE, DAY, rh_type=RhType.VACACIONES)
    day_plan = replace(planned(DAY, Planned.ABSENCE, rh_type=RhType.VACACIONES), exception=absence)
    result = run_one(day_plan, [])
    assert (result.outcome, result.exception) == (Outcome.JUSTIFIED, absence)


def test_late_result_keeps_a_present_no_checkin_exception() -> None:
    present = exception(ExceptionKind.PRESENT_NO_CHECKIN, DAY)
    day_plan = replace(planned(DAY, present_no_checkin=True), exception=present)
    result = run_one(day_plan, [checkin(17, 5)])
    assert (result.outcome, result.exception) == (Outcome.LATE, present)
```

Al final de `backend/tests/domain/test_justify.py` (agregar los imports que falten:
`from dataclasses import replace`, `ExceptionKind`, `Incident`, `Outcome`, `RhType` y de
factories `exception`, `justification`, `result`, `DAY`):

```python
def test_justified_manual_absence_keeps_its_exception() -> None:
    manual = exception(ExceptionKind.MANUAL_ABSENCE, DAY)
    absent = replace(result(Outcome.ABSENT), exception=manual)
    applied, _ = apply_justifications([absent], [justification(Incident.ABSENT, RhType.PERMISO)])
    assert (applied[0].exception, applied[0].justification_id) == (manual, 7)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/domain/test_planning.py tests/domain/test_compare.py tests/domain/test_justify.py -q`
Expected: FAIL — `AttributeError: 'PlannedDay' object has no attribute 'exception'` y
`TypeError: ... unexpected keyword argument 'exception'`.

- [ ] **Step 3: Add the fields**

En `backend/src/tabernas/domain/types.py`, último campo de `PlannedDay`:

```python
    comment: str = ""
    exception: ScheduleException | None = None
```

y último campo de `DayResult`:

```python
    comment: str = ""
    exception: ScheduleException | None = None
```

- [ ] **Step 4: Attach the exception in planning**

En `backend/src/tabernas/domain/planning.py`, reemplazar `_plan_day` desde
`covering = ...` hasta el final:

```python
    covering = [e for e in exceptions if covers(e, day)]
    present = _find(covering, ExceptionKind.PRESENT_NO_CHECKIN)
    absence = _find(covering, ExceptionKind.WORK_TO_ABSENCE)
    if absence is not None:
        return PlannedDay(
            employee_id,
            day,
            Planned.ABSENCE,
            rh_type=absence.rh_type,
            comment=absence.comment,
            exception=absence,
        )
    manual = _find(covering, ExceptionKind.MANUAL_ABSENCE)
    if manual is not None:
        return PlannedDay(
            employee_id,
            day,
            Planned.WORK,
            manual_absence=True,
            comment=manual.comment,
            exception=manual,
        )
    extra_work = _find(covering, ExceptionKind.REST_TO_WORK)
    if extra_work is not None:
        return PlannedDay(
            employee_id,
            day,
            Planned.WORK,
            present_no_checkin=present is not None,
            comment=extra_work.comment,
            exception=extra_work,
        )
    return PlannedDay(
        employee_id,
        day,
        planned_by_rule(rule_for(rules, day), day),
        present_no_checkin=present is not None,
        exception=present,
    )
```

- [ ] **Step 5: Copy it in compare**

En `backend/src/tabernas/domain/compare.py`, `_evaluate`, el `base`:

```python
    base = DayResult(
        employee_id=day_plan.employee_id,
        day=day_plan.day,
        planned=day_plan.planned,
        outcome=Outcome.OK,
        checkin=checkin,
        rh_type=day_plan.rh_type,
        comment=day_plan.comment,
        exception=day_plan.exception,
    )
```

- [ ] **Step 6: Run domain tests**

Run: `uv run pytest tests/domain -q`
Expected: PASS (todos, incluidos los existentes).

- [ ] **Step 7: Commit**

```bash
git add src/tabernas/domain/types.py src/tabernas/domain/planning.py src/tabernas/domain/compare.py tests/domain/test_planning.py tests/domain/test_compare.py tests/domain/test_justify.py
git commit -m "feat: attach the employee's schedule exception to each planned and result day

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Filtro y paginación de incidencias (dominio)

**Files:**
- Create: `backend/src/tabernas/domain/incident_filter.py`
- Test: `backend/tests/domain/test_incident_filter.py`

**Interfaces:**
- Consumes: `DayResult`, `Outcome` (Task 1 no cambia su uso aquí).
- Produces:
  - `class IncidentType(StrEnum)`: `LATE`, `ABSENT`, `UNREGISTERED_CHANGE`, `JUSTIFIED`
  - `INCIDENT_OUTCOMES: frozenset[Outcome]`
  - `class IncidentStatus(StrEnum)`: `ALL = "all"`, `JUSTIFIED = "justified"`, `UNJUSTIFIED = "unjustified"`
  - `@dataclass(frozen=True) class IncidentFilter(employee_id: int | None = None, types: frozenset[IncidentType] = frozenset(), status: IncidentStatus = IncidentStatus.ALL)`
  - `filter_incidents(results: Sequence[DayResult], incident_filter: IncidentFilter) -> list[DayResult]`
  - `count_unresolved(results: Sequence[DayResult], employee_id: int | None) -> int`
  - `MAX_PAGE_SIZE = 100`, `DEFAULT_PAGE_SIZE = 25`
  - `@dataclass(frozen=True) class PageRequest(page: int = 1, limit: int = DEFAULT_PAGE_SIZE)`
  - `@dataclass(frozen=True) class Page[T](items: tuple[T, ...], total: int, page: int, limit: int)`
  - `paginate[T](items: Sequence[T], request: PageRequest) -> Page[T]` (lanza `DomainValidationError`)

- [ ] **Step 1: Write the failing tests**

`backend/tests/domain/test_incident_filter.py`:

```python
from datetime import date

import pytest

from tabernas.domain.incident_filter import (
    DEFAULT_PAGE_SIZE,
    INCIDENT_OUTCOMES,
    IncidentFilter,
    IncidentStatus,
    IncidentType,
    PageRequest,
    count_unresolved,
    filter_incidents,
    paginate,
)
from tabernas.domain.types import Outcome
from tabernas.domain.validation import DomainValidationError
from tests.domain.factories import result

OK_1 = result(Outcome.OK, employee_id=1, day=date(2026, 9, 21))
REST_2 = result(Outcome.REST, employee_id=2, day=date(2026, 9, 22))
LATE_1 = result(Outcome.LATE, employee_id=1)
LATE_2_JUSTIFIED = result(Outcome.LATE, employee_id=2, justification_id=9)
ABSENT_1 = result(Outcome.ABSENT, employee_id=1, day=date(2026, 9, 24))
CHANGE_2 = result(Outcome.UNREGISTERED_CHANGE, employee_id=2, day=date(2026, 9, 25))
VACATION_1 = result(Outcome.JUSTIFIED, employee_id=1, day=date(2026, 9, 26))
ALL = [OK_1, REST_2, LATE_1, LATE_2_JUSTIFIED, ABSENT_1, CHANGE_2, VACATION_1]


def test_incident_types_are_the_incident_outcomes() -> None:
    assert {Outcome(t.value) for t in IncidentType} == INCIDENT_OUTCOMES


def test_default_filter_keeps_only_incidents_in_input_order() -> None:
    assert filter_incidents(ALL, IncidentFilter()) == [
        LATE_1,
        LATE_2_JUSTIFIED,
        ABSENT_1,
        CHANGE_2,
        VACATION_1,
    ]


def test_filter_by_employee() -> None:
    assert filter_incidents(ALL, IncidentFilter(employee_id=2)) == [LATE_2_JUSTIFIED, CHANGE_2]


def test_filter_by_types() -> None:
    types = frozenset({IncidentType.LATE, IncidentType.JUSTIFIED})
    assert filter_incidents(ALL, IncidentFilter(types=types)) == [
        LATE_1,
        LATE_2_JUSTIFIED,
        VACATION_1,
    ]


def test_justified_status_includes_justifications_and_exception_absences() -> None:
    found = filter_incidents(ALL, IncidentFilter(status=IncidentStatus.JUSTIFIED))
    assert found == [LATE_2_JUSTIFIED, VACATION_1]


def test_unjustified_status_includes_unregistered_changes() -> None:
    found = filter_incidents(ALL, IncidentFilter(status=IncidentStatus.UNJUSTIFIED))
    assert found == [LATE_1, ABSENT_1, CHANGE_2]


def test_filters_combine() -> None:
    combined = IncidentFilter(
        employee_id=1,
        types=frozenset({IncidentType.LATE, IncidentType.ABSENT}),
        status=IncidentStatus.UNJUSTIFIED,
    )
    assert filter_incidents(ALL, combined) == [LATE_1, ABSENT_1]


def test_count_unresolved_respects_only_the_employee() -> None:
    assert count_unresolved(ALL, None) == 1
    assert count_unresolved(ALL, 2) == 1
    assert count_unresolved(ALL, 1) == 0


@pytest.mark.parametrize(
    ("page", "expected"), [(1, [0, 1]), (2, [2, 3]), (3, [4]), (4, [])]
)
def test_paginate_slices_and_reports_the_real_total(page: int, expected: list[int]) -> None:
    found = paginate(list(range(5)), PageRequest(page=page, limit=2))
    assert (list(found.items), found.total, found.page, found.limit) == (expected, 5, page, 2)


def test_paginate_empty_uses_the_default_size() -> None:
    found = paginate([], PageRequest())
    assert (found.items, found.total, found.page, found.limit) == ((), 0, 1, DEFAULT_PAGE_SIZE)


@pytest.mark.parametrize(
    "bad", [PageRequest(page=0), PageRequest(limit=0), PageRequest(limit=101)]
)
def test_paginate_rejects_bad_requests(bad: PageRequest) -> None:
    with pytest.raises(DomainValidationError):
        paginate([1], bad)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/domain/test_incident_filter.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'tabernas.domain.incident_filter'`.

- [ ] **Step 3: Write the module**

`backend/src/tabernas/domain/incident_filter.py`:

```python
"""Filters and pages the incident list. Pure: no database, no HTTP."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from tabernas.domain.types import DayResult, Outcome
from tabernas.domain.validation import DomainValidationError

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 25


class IncidentType(StrEnum):
    """The outcomes that count as incidents (same values as `Outcome`)."""

    LATE = "LATE"
    ABSENT = "ABSENT"
    UNREGISTERED_CHANGE = "UNREGISTERED_CHANGE"
    JUSTIFIED = "JUSTIFIED"


INCIDENT_OUTCOMES = frozenset(Outcome(t.value) for t in IncidentType)


class IncidentStatus(StrEnum):
    ALL = "all"
    JUSTIFIED = "justified"
    UNJUSTIFIED = "unjustified"


@dataclass(frozen=True)
class IncidentFilter:
    employee_id: int | None = None
    types: frozenset[IncidentType] = frozenset()  # empty = every type
    status: IncidentStatus = IncidentStatus.ALL


@dataclass(frozen=True)
class PageRequest:
    page: int = 1
    limit: int = DEFAULT_PAGE_SIZE


@dataclass(frozen=True)
class Page[T]:
    items: tuple[T, ...]
    total: int
    page: int
    limit: int


def is_justified(result: DayResult) -> bool:
    return result.justification_id is not None or result.outcome == Outcome.JUSTIFIED


def _matches(result: DayResult, incident_filter: IncidentFilter) -> bool:
    if incident_filter.employee_id not in (None, result.employee_id):
        return False
    if incident_filter.types and IncidentType(result.outcome.value) not in incident_filter.types:
        return False
    if incident_filter.status == IncidentStatus.ALL:
        return True
    return is_justified(result) == (incident_filter.status == IncidentStatus.JUSTIFIED)


def filter_incidents(
    results: Sequence[DayResult], incident_filter: IncidentFilter
) -> list[DayResult]:
    return [
        r for r in results if r.outcome in INCIDENT_OUTCOMES and _matches(r, incident_filter)
    ]


def count_unresolved(results: Sequence[DayResult], employee_id: int | None) -> int:
    """Unregistered changes of the range; ignores the type and status filters on purpose."""
    only_changes = IncidentFilter(
        employee_id=employee_id, types=frozenset({IncidentType.UNREGISTERED_CHANGE})
    )
    return len(filter_incidents(results, only_changes))


def paginate[T](items: Sequence[T], request: PageRequest) -> Page[T]:
    if request.page < 1:
        raise DomainValidationError("La página empieza en 1")
    if not 1 <= request.limit <= MAX_PAGE_SIZE:
        raise DomainValidationError(f"El tamaño de página va de 1 a {MAX_PAGE_SIZE}")
    start = (request.page - 1) * request.limit
    return Page(
        items=tuple(items[start : start + request.limit]),
        total=len(items),
        page=request.page,
        limit=request.limit,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/domain/test_incident_filter.py -q && uv run pyright src/tabernas/domain/incident_filter.py`
Expected: PASS; pyright `0 errors`.

- [ ] **Step 5: Commit**

```bash
git add src/tabernas/domain/incident_filter.py tests/domain/test_incident_filter.py
git commit -m "feat: add pure incident filter and pagination

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `DayOut.exception` en el API

**Files:**
- Modify: `backend/src/tabernas/api/routes/attendance.py`
- Test: `backend/tests/api/test_attendance.py`

**Interfaces:**
- Consumes: `DayResult.exception` (Task 1); `INCIDENT_OUTCOMES` (Task 2) reemplaza la
  constante local de la ruta.
- Produces: esquema `ExceptionRef {id, kind, date_from, date_to, rh_type, comment}` y
  `DayOut.exception: ExceptionRef | None` en `/attendance/calendar` y `/attendance/incidents`.

- [ ] **Step 1: Write the failing test**

En `backend/tests/api/test_attendance.py`, después de `test_calendar_has_one_day_per_employee`:

```python
def test_calendar_days_carry_their_exception(demo_client: TestClient) -> None:
    employee_id = demo_client.get("/employees").json()["data"][0]["id"]
    body = {
        "kind": "WORK_TO_ABSENCE",
        "employee_id": employee_id,
        "date_from": "2026-09-23",
        "date_to": "2026-09-24",
        "rh_type": "VACACIONES",
        "comment": "Viaje",
    }
    created = demo_client.post("/exceptions", json=body).json()["data"]
    days = demo_client.get("/attendance/calendar", params=WEEK).json()["data"]["days"]
    own = {d["day"]: d for d in days if d["employee_id"] == employee_id}
    expected = {k: created[k] for k in ("id", "kind", "date_from", "date_to", "rh_type", "comment")}
    assert own["2026-09-23"]["exception"] == expected
    assert own["2026-09-24"]["exception"] == expected
    assert own["2026-09-21"]["exception"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/api/test_attendance.py::test_calendar_days_carry_their_exception -q`
Expected: FAIL — `KeyError: 'exception'`.

- [ ] **Step 3: Add `ExceptionRef` to `DayOut`**

En `backend/src/tabernas/api/routes/attendance.py`:

1. Imports: agregar `ExceptionKind` a `from tabernas.domain.types import ...` y
   `from tabernas.domain.incident_filter import INCIDENT_OUTCOMES`; borrar la constante
   local `INCIDENT_OUTCOMES = frozenset({...})`.
2. Antes de `class DayOut`:

```python
class ExceptionRef(_FromAttributes):
    id: int
    kind: ExceptionKind
    date_from: date
    date_to: date
    rh_type: RhType | None
    comment: str
```

3. Último campo de `DayOut`:

```python
    comment: str
    exception: ExceptionRef | None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/api/test_attendance.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/tabernas/api/routes/attendance.py tests/api/test_attendance.py
git commit -m "feat: expose each day's schedule exception in the attendance API

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: `/attendance/incidents` paginado y `/attendance/rh-rows` nuevo

**Files:**
- Modify: `backend/src/tabernas/api/routes/attendance.py`
- Test: `backend/tests/api/test_attendance.py`

**Interfaces:**
- Consumes: `IncidentFilter`, `IncidentStatus`, `IncidentType`, `PageRequest`, `Page`,
  `filter_incidents`, `count_unresolved`, `paginate`, `MAX_PAGE_SIZE`,
  `DEFAULT_PAGE_SIZE` (Task 2); `to_rh_rows` de `tabernas.domain.rh`.
- Produces (los consume el Plan B vía `schema.d.ts`):
  - `GET /attendance/incidents?from&to&employee_id&type*&status&page&limit` →
    `data: IncidentsOut {start, end, items: DayOut[], unresolved: int, warnings: WarningOut[]}`,
    `meta: {total, page, limit}`.
  - `GET /attendance/rh-rows?…mismos…` → `data: RhRowsOut {start, end, items: RhRowOut[]}`,
    `meta: {total, page, limit}`.
  - `IncidentsOut.incidents` y `IncidentsOut.rh_rows` dejan de existir.

- [ ] **Step 1: Write the failing tests**

En `backend/tests/api/test_attendance.py`, **reemplazar**
`test_incidents_and_rh_rows_are_consistent` por:

```python
MONTH = {"from": "2026-09-01", "to": "2026-09-27"}


def _items(client: TestClient, path: str, **params: object) -> list[dict[str, object]]:
    response = client.get(path, params={**MONTH, "limit": 100, **params})
    assert response.status_code == 200, response.text
    return response.json()["data"]["items"]


def test_incidents_and_rh_rows_are_consistent(demo_client: TestClient) -> None:
    incidents = _items(demo_client, "/attendance/incidents")
    rows = _items(demo_client, "/attendance/rh-rows")
    assert {d["outcome"] for d in incidents} <= INCIDENT_OUTCOMES
    assert rows
    assert {(r["employee_id"], r["day"]) for r in rows} <= {
        (d["employee_id"], d["day"]) for d in incidents
    }


def test_incidents_are_paginated_with_meta(demo_client: TestClient) -> None:
    first = demo_client.get("/attendance/incidents", params={**MONTH, "limit": 5}).json()
    total = first["meta"]["total"]
    assert (first["meta"]["page"], first["meta"]["limit"]) == (1, 5)
    assert total > 5
    assert len(first["data"]["items"]) == 5
    last_page = (total + 4) // 5
    last = demo_client.get(
        "/attendance/incidents", params={**MONTH, "limit": 5, "page": last_page}
    ).json()
    assert len(last["data"]["items"]) == total - 5 * (last_page - 1)
    beyond = demo_client.get(
        "/attendance/incidents", params={**MONTH, "limit": 5, "page": last_page + 1}
    ).json()
    assert (beyond["data"]["items"], beyond["meta"]["total"]) == ([], total)


def test_incident_filters_combine(demo_client: TestClient) -> None:
    every = _items(demo_client, "/attendance/incidents")
    employee_id = every[0]["employee_id"]
    found = _items(
        demo_client,
        "/attendance/incidents",
        employee_id=employee_id,
        type=["LATE", "ABSENT"],
        status="unjustified",
    )
    assert found == [
        d
        for d in every
        if d["employee_id"] == employee_id
        and d["outcome"] in {"LATE", "ABSENT"}
        and d["justification_id"] is None
    ]


def test_unresolved_ignores_type_and_status(demo_client: TestClient) -> None:
    every = _items(demo_client, "/attendance/incidents")
    changes = sum(d["outcome"] == "UNREGISTERED_CHANGE" for d in every)
    params = {**MONTH, "type": "LATE", "status": "justified"}
    data = demo_client.get("/attendance/incidents", params=params).json()["data"]
    assert data["unresolved"] == changes


def test_rh_rows_follow_the_incident_filters(demo_client: TestClient) -> None:
    every = _items(demo_client, "/attendance/rh-rows")
    employee_id = every[0]["employee_id"]
    assert _items(demo_client, "/attendance/rh-rows", employee_id=employee_id) == [
        r for r in every if r["employee_id"] == employee_id
    ]
    assert {r["rh_type"] for r in _items(demo_client, "/attendance/rh-rows", type="LATE")} <= {
        "RETARDO"
    }
    assert _items(demo_client, "/attendance/rh-rows", type="UNREGISTERED_CHANGE") == []


def test_rh_rows_are_paginated(demo_client: TestClient) -> None:
    every = _items(demo_client, "/attendance/rh-rows")
    page = demo_client.get("/attendance/rh-rows", params={**MONTH, "limit": 2}).json()
    assert page["data"]["items"] == every[:2]
    assert page["meta"] == {"total": len(every), "page": 1, "limit": 2}


@pytest.mark.parametrize(
    "bad", [{"limit": 101}, {"limit": 0}, {"page": 0}, {"type": "OK"}, {"status": "todas"}]
)
def test_bad_incident_queries_are_422(client: TestClient, bad: dict[str, object]) -> None:
    for path in ("/attendance/incidents", "/attendance/rh-rows"):
        assert client.get(path, params={**WEEK, **bad}).status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/api/test_attendance.py -q`
Expected: FAIL — `KeyError: 'items'` y 404 en `/attendance/rh-rows`.

- [ ] **Step 3: Implement the routes**

En `backend/src/tabernas/api/routes/attendance.py`:

1. Imports (reemplazar el import de Task 3 por el completo):

```python
from tabernas.domain.incident_filter import (
    DEFAULT_PAGE_SIZE,
    INCIDENT_OUTCOMES,
    MAX_PAGE_SIZE,
    IncidentFilter,
    IncidentStatus,
    IncidentType,
    Page,
    PageRequest,
    count_unresolved,
    filter_incidents,
    paginate,
)
from tabernas.domain.rh import to_rh_rows
```

`INCIDENT_OUTCOMES` deja de usarse en la ruta: quitarlo del import si ruff lo marca
(`F401`).

2. Reemplazar `class IncidentsOut` por:

```python
class IncidentsOut(BaseModel):
    start: date
    end: date
    items: list[DayOut]
    unresolved: int
    warnings: list[WarningOut]


class RhRowsOut(BaseModel):
    start: date
    end: date
    items: list[RhRowOut]
```

3. Después de `ServiceDep`, las dependencias de consulta:

```python
def incident_filter(
    employee_id: int | None = None,
    types: Annotated[list[IncidentType] | None, Query(alias="type")] = None,
    status: IncidentStatus = IncidentStatus.ALL,
) -> IncidentFilter:
    return IncidentFilter(employee_id=employee_id, types=frozenset(types or ()), status=status)


def page_request(
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> PageRequest:
    return PageRequest(page=page, limit=limit)


FilterDep = Annotated[IncidentFilter, Depends(incident_filter)]
PageDep = Annotated[PageRequest, Depends(page_request)]


def _page_meta(found: Page[object]) -> dict[str, int]:
    return {"total": found.total, "page": found.page, "limit": found.limit}
```

Si pyright se queja de la varianza de `Page[object]`, tipar `_page_meta` como genérico:
`def _page_meta[T](found: Page[T]) -> dict[str, int]:`.

4. Reemplazar la ruta `incidents` y agregar `rh_rows` debajo:

```python
@router.get("/incidents")
def incidents(
    start: StartQuery, end: EndQuery, service: ServiceDep, where: FilterDep, page: PageDep
) -> Envelope[IncidentsOut]:
    report = service.build(start, end)
    found = paginate(filter_incidents(report.results, where), page)
    return ok(
        IncidentsOut(
            start=report.start,
            end=report.end,
            items=[DayOut.model_validate(r) for r in found.items],
            unresolved=count_unresolved(report.results, where.employee_id),
            warnings=_warnings(report),
        ),
        meta=_page_meta(found),
    )


@router.get("/rh-rows")
def rh_rows(
    start: StartQuery, end: EndQuery, service: ServiceDep, where: FilterDep, page: PageDep
) -> Envelope[RhRowsOut]:
    report = service.build(start, end)
    rows, _ = to_rh_rows(filter_incidents(report.results, where), report.employees)
    found = paginate(rows, page)
    return ok(
        RhRowsOut(
            start=report.start,
            end=report.end,
            items=[RhRowOut.model_validate(row) for row in found.items],
        ),
        meta=_page_meta(found),
    )
```

Los avisos de `to_rh_rows` (`MISSING_RH_NAME`) se descartan aquí a propósito: ya llegan
en `IncidentsOut.warnings` desde `report.warnings`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/api/test_attendance.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/tabernas/api/routes/attendance.py tests/api/test_attendance.py
git commit -m "feat: filter and paginate incidents and RH rows in the API

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Verificación completa del backend

**Files:** ninguno nuevo (solo correcciones que salgan de las herramientas).

- [ ] **Step 1: Lint, formato y tipos**

Run: `uv run ruff check . && uv run ruff format --check . && uv run pyright`
Expected: sin errores. Si `ruff format --check` falla, correr `uv run ruff format .` y
revisar el diff.

- [ ] **Step 2: Suite completa con cobertura (mismas compuertas que CI)**

Run: `uv run pytest --cov && uv run coverage report --include="*/tabernas/domain/*" --fail-under=95`
Expected: PASS; total ≥ 80%, `domain/` ≥ 95%.

- [ ] **Step 3: Revisar que el agente no recibe la excepción**

Run: `grep -n "exception" src/tabernas/agents/weekly_review/tools.py`
Expected: sin coincidencias nuevas. Las herramientas arman su JSON campo por campo
(`_day_json`), así que el nuevo `DayResult.exception` **no** llega a Claude. Si alguna
herramienta usara `asdict(DayResult)`, detenerse: el comentario de la excepción tendría
que pasar por `scrub()`.

- [ ] **Step 4: Commit (solo si hubo correcciones)**

```bash
git add -A src tests
git commit -m "chore: lint and type fixes for attendance filters

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
