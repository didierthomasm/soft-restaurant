# Etapa 1 — Base del sistema + Asistencia: diseño

> Estado: **diseño aprobado en conversación (2026-09-29)**, pendiente de revisión del
> documento. Deriva de [`plan.md`](../plan.md) §5 Etapa 1 y de
> [`db-map.md`](../db-map.md). Reglas de negocio y decisiones resueltas de `plan.md`
> §4 y §6 aplican tal cual; aquí solo se detalla cómo se implementan.

## 1. Objetivo y criterios de éxito

Reemplazar el reporte de asistencia de SR con uno que calcule retardos y faltas
contra lo planeado, permita justificarlos y entregue la lista para capturar en RH.

**Aceptación** (de `plan.md`):
1. `docker compose up` desde cero levanta todo y `GET /health/sr` responde OK.
2. Las checadas de agosto 2026 coinciden 1:1 con el export de SR
   (`scripts/reconcile_attendance.py`).
3. Retardos y faltas de una semana real coinciden con la revisión manual del gerente.
4. Cobertura ≥ 80% en `domain/` (objetivo real: > 95%).

## 2. Decisiones de diseño

| # | Decisión | Motivo |
|---|---|---|
| D1 | **SR es la fuente de verdad y se consulta en vivo**, acotado por fechas, en cada petición. No se copian checadas a Postgres. | `registroasistencias` es chica (~2.5k filas); cero sincronización, cero datos atrasados. |
| D2 | **Nada derivado se persiste.** El calendario se calcula en memoria en cada petición: config de Postgres + checadas de SR → `domain/`. | Cambiar una regla o justificar se refleja al instante; no hay caché que invalidar. |
| D3 | **Quien no controla asistencia en SR (el gerente) cuenta como asistido salvo aviso.** Sus faltas se registran como excepción `MANUAL_ABSENCE`. Nunca genera retardos. | Regla del negocio: le aplican faltas, no retardos, y no checa. |
| D4 | **Login falso** en el frontend: usuario/contraseña de demo en `.env`, cookie + `proxy.ts` de Next. El backend no se protege; todos los puertos se publican solo en `127.0.0.1`. | Deja lista la forma del flujo; la auth real se diseña después. **No es seguridad.** |
| D5 | **`SR_MODE=live|fake`.** `fake` sirve empleados y checadas sintéticos y deterministas. | Demo pública del portafolio, E2E y CI sin acceso a SR. |
| D6 | Horario de entrada **por área** (cocina / resto), no por empleado. | Es la regla vigente; YAGNI. |
| D7 | Empleados se **importan de `meseros`** desde la UI; el nombre en RH se captura en la UI. | Ningún nombre real existe en el código ni en migraciones. |
| D8 | Un solo spec, **dos planes**: Plan A = infraestructura + backend (1a–1e); Plan B = frontend (1f). | El backend se valida contra SR antes de construir la UI. |

## 3. Estructura del repositorio

```
backend/
  pyproject.toml            # reemplaza al pyproject de la raíz
  alembic.ini, alembic/
  src/tabernas/
    config.py               # pydantic-settings (lee .env)
    main.py                 # app FastAPI, routers, manejadores de error
    sr/                     # conector SR
      source.py             #   protocolo SrSource + modelos SrEmployee, SrCheckin
      pymssql_source.py     #   implementación real
      fake_source.py        #   implementación sintética
    domain/                 # lógica pura (sin DB, sin HTTP)
      types.py, periods.py, planning.py, compare.py,
      justify.py, summary.py, rh.py
    db/                     # modelos SQLAlchemy + sesión
    repos/                  # repositorios (un archivo por tabla)
    services/attendance.py  # orquesta repos + SR + dominio (§8.3)
    api/                    # routers, esquemas de request/response, envelope
    export/xlsx.py          # openpyxl
  tests/
    domain/  repos/  api/  sr/  export/
frontend/                   # Next.js (Plan B)
scripts/
  check_connection.py       # existente
  reconcile_attendance.py   # nuevo (aceptación #2)
  seed_demo.py              # nuevo: empleados/reglas sintéticos para SR_MODE=fake
docker-compose.yml
freetds.conf, .env.example
.github/workflows/ci.yml
```

Limpieza: se borra `main.py` de la raíz (plantilla de PyCharm) y el `pyproject.toml`
de la raíz se mueve a `backend/`. Los scripts corren con `uv run --project backend`.
`CLAUDE.md` se actualiza con los comandos nuevos.

## 4. Infraestructura (1a)

- **`docker-compose.yml`**: servicios `db` (postgres:16, volumen nombrado,
  healthcheck `pg_isready`), `backend` (uvicorn, depende de `db` sano, corre
  `alembic upgrade head` al iniciar), `frontend` (Plan B). Puertos publicados como
  `127.0.0.1:<puerto>:<puerto>`.
- **FreeTDS**: `freetds.conf` se monta en el backend y `FREETDSCONF` apunta a él.
- **Primer riesgo (spike, primera tarea del Plan A):** desde el contenedor `backend`,
  `GET /health/sr` debe alcanzar SR a través del Tailscale del host (Docker Desktop
  enruta por la pila de red de macOS). Si falla: sidecar `tailscale/tailscale` y
  `network_mode: service:tailscale` para el backend. El resultado se documenta en
  `docs/db-map.md`.
- **Variables** (`.env.example` sin valores reales): `SR_MODE`, `SR_DB_*`,
  `DATABASE_URL`, `APP_TIMEZONE=America/Mexico_City`, `FAKE_AUTH_USER`,
  `FAKE_AUTH_PASSWORD`, `BACKEND_URL` (para el frontend).
- **Health**:
  - `GET /health` → `{status: "ok", db: "ok"|"error"}`.
  - `GET /health/sr` → versión del servidor, login, `es_datareader`,
    `es_denywriter`, `es_sysadmin`. Responde **503** si no hay conexión y **500 con
    código `SR_NOT_READONLY`** si el login no es de solo lectura (sysadmin o sin
    `db_denydatawriter`). En `SR_MODE=fake` responde `mode: "fake"`.
- **CI** (GitHub Actions): ruff, pyright, pytest con servicio Postgres y
  `SR_MODE=fake`; en Plan B se agregan ESLint, Vitest y Playwright.

## 5. Conector SR (1b)

```python
class SrSource(Protocol):
    def fetch_employees(self) -> list[SrEmployee]: ...
    def fetch_checkins(self, start: date, end: date) -> list[SrCheckin]: ...  # [start, end] inclusivo
    def server_info(self) -> SrServerInfo: ...

class SrEmployee(BaseModel, frozen=True):  sr_id: int; name: str; kind: int | None; visible: bool
class SrCheckin(BaseModel, frozen=True):   sr_id: int; at: datetime  # naive, hora local de SR
```

- **Consultas** (únicas permitidas; parámetros con `%s`, nunca interpolación):
  ```sql
  SELECT idempleado, entrada FROM registroasistencias WITH (NOLOCK)
  WHERE entrada >= %s AND entrada < %s          -- [start, end + 1 día)

  SELECT idmesero, nombre, tipo, visible FROM meseros WITH (NOLOCK)
  ```
  `meseros.contraseña` y `meseros.fotografia` **nunca** se seleccionan; un test
  verifica que el SQL no las mencione.
- **Normalización**: `idempleado`/`idmesero` → `int` (`'06'` → `6`). Un id no
  numérico se registra en log y se descarta esa fila (error de datos, no falla toda
  la consulta).
- **Límites**: `end - start ≤ 93 días` (si no, `ValueError` → 422 en API);
  `login_timeout=10`, `timeout=20`; una conexión por llamada (volumen bajo, sin pool).
- **Errores**: cualquier `pymssql.Error` se envuelve en `SrUnavailableError` (sin
  credenciales en el mensaje) → la API responde **503 `SR_UNAVAILABLE`**.
- **`FakeSource`**: 6 empleados sintéticos (`EMPLEADO A`…`F`, ids 101–106) y
  checadas generadas de forma determinista por fecha (semilla fija), con algunos
  retardos, faltas y una checada en día de descanso por semana.
- **Tests**: unitarios con un cursor falso (SQL enviado, normalización, límites,
  errores); `@pytest.mark.sr` contra SR real, excluidos por defecto
  (`-m "not sr"`).

## 6. Modelo de datos propio (1c)

Todas las tablas tienen `id` (PK entera), `created_at`, `updated_at`.

| Tabla | Columnas | Restricciones |
|---|---|---|
| `employee` | `sr_id` int null, `short_name`, `rh_name` null, `area` (`KITCHEN`/`OTHER`), `applies_lateness` bool, `tracks_attendance` bool, `active` bool | `sr_id` único cuando no es null (el gerente sí tiene `sr_id`, pero no checa) |
| `rest_rule` | `employee_id` FK, `fixed_weekday` 0–6, `extra_weekday` 0–6, `double_rest_anchor` date (un lunes), `valid_from` date, `valid_to` date null | `fixed ≠ extra`; ancla es lunes; sin vigencias traslapadas por empleado (validado en repo → 409) |
| `schedule_exception` | `kind`, `employee_id` FK null, `date_from`, `date_to`, `rh_type` null, `comment` | `employee_id` null ⇔ `kind = STORE_CLOSED`; `rh_type` obligatorio ⇔ `kind = WORK_TO_ABSENCE`; `date_from ≤ date_to` |
| `justification` | `employee_id` FK, `day`, `incident` (`LATE`/`ABSENT`), `reason`, `rh_type` | único (`employee_id`, `day`, `incident`) |
| `setting` | `key` PK, `value` (texto) | claves: `entry_time_kitchen` (`16:30`), `entry_time_other` (`16:40`), `tolerance_minutes` (`10`); sembradas en la migración inicial |

- **Tipos de excepción** (de `plan.md` §6 + D3): `STORE_CLOSED`,
  `PRESENT_NO_CHECKIN`, `REST_TO_WORK`, `WORK_TO_ABSENCE`, `MANUAL_ABSENCE`.
- **Cierre del local (`STORE_CLOSED`)** cubre todo día en que el local no abre y
  aplica a todos: Ley Seca, 24 y 25 de diciembre, cierres imprevistos (tormenta).
  No es vacaciones ni falta: nadie debía trabajar, no genera filas para RH y se
  muestra como "Cerrado" con su comentario (p. ej. "Ley Seca"). Se captura por día o
  rango; en la UI es una acción propia ("Cerrar el local"), no un tipo escondido
  entre las excepciones de empleado. Sin recurrencia anual automática (YAGNI): los
  cierres fijos se capturan cada año.
- **Una sola excepción de empleado por empleado-día**: crear una que traslape otra
  del mismo empleado → 409. `STORE_CLOSED` puede coexistir y tiene precedencia.
- **`RhType`**: `RETARDO`, `FALTA_INJUSTIFICADA`, `FALTA_JUSTIFICADA`, `VACACIONES`,
  `INCAPACIDAD`, `PERMISO`, `DESCANSO`, `NO_CAPTURAR` (solo en justificaciones).
  Etiquetas en español viven en el frontend y en el export.
- Borrado físico en `schedule_exception` y `justification` (el efecto es
  recalculable); `employee` se desactiva (`active=false`), no se borra.
- Repositorios: `list`, `get`, `create`, `update`, `delete` por tabla; devuelven
  modelos de dominio inmutables (no objetos ORM) para que `domain/` no conozca
  SQLAlchemy.

## 7. Dominio (1d)

Todo en `domain/`, funciones puras, dataclasses `frozen=True`. Entradas explícitas;
"hoy" y "ahora" se reciben como parámetros (nunca `datetime.now()` dentro).

### 7.1 Tipos principales

```python
class Planned(Enum):  WORK, REST, CLOSED, ABSENCE
@dataclass(frozen=True) class PlannedDay:  employee_id; day; planned; rh_type: RhType | None; present_no_checkin: bool; manual_absence: bool

class Outcome(Enum): OK, LATE, ABSENT, UNREGISTERED_CHANGE, REST, CLOSED, JUSTIFIED, PENDING, FUTURE
@dataclass(frozen=True) class DayResult:  employee_id; day; planned; outcome; checkin: datetime | None; minutes_late: int | None; rh_type: RhType | None; justification_id: int | None
```

### 7.2 `periods.py`
`iso_week_range(year, week)`, `month_range(year, month)`, `days(start, end)`,
`week_monday(d)`. Rango máximo 93 días (misma regla que SR).

### 7.3 `planning.planned_calendar(employees, rules, exceptions, start, end) -> list[PlannedDay]`

Por cada empleado activo y cada día, en este orden de precedencia:
1. `STORE_CLOSED` que cubra el día → `CLOSED`.
2. `WORK_TO_ABSENCE` → `ABSENCE` con su `rh_type`.
3. `MANUAL_ABSENCE` → `WORK` con `manual_absence=True`.
4. `REST_TO_WORK` → `WORK`.
5. Regla de descanso vigente ese día:
   - `day.weekday() == fixed_weekday` → `REST`.
   - `day.weekday() == extra_weekday` **y** semana doble → `REST`.
     Semana doble ⇔ `((week_monday(day) - double_rest_anchor).days // 7) % 2 == 0`.
   - si no → `WORK`.
6. Sin regla vigente → `WORK` (y se reporta un aviso `NO_REST_RULE`).

`PRESENT_NO_CHECKIN` no cambia lo planeado: marca `present_no_checkin=True`.

### 7.4 `compare.compare(planned, checkins, settings, today, now) -> list[DayResult]`

- Checadas agrupadas por (`sr_id`, fecha calendario de `at`); se usa **la primera**.
- Hora límite = hora de entrada del área + tolerancia. **Retardo** ⇔
  `at.replace(second=0, microsecond=0).time() > límite`;
  `minutes_late` = minutos entre la hora de entrada y la checada truncada.
  (16:40 + 10: `16:50:59` a tiempo; `16:51:00` retardo de 11 min.)

| Planeado | Condición | Outcome |
|---|---|---|
| cualquiera | `day > today` | `FUTURE` |
| `CLOSED` | — | `CLOSED` |
| `ABSENCE` | — | `JUSTIFIED` (con `rh_type`; la checada, si hay, se muestra) |
| `REST` | hay checada | `UNREGISTERED_CHANGE` |
| `REST` | sin checada | `REST` |
| `WORK` + `manual_absence` | — | `ABSENT` |
| `WORK`, empleado sin `tracks_attendance` | — | `OK` |
| `WORK` | hay checada, a tiempo o `applies_lateness=False` | `OK` |
| `WORK` | hay checada, tarde | `LATE` |
| `WORK` | sin checada, `present_no_checkin` | `OK` |
| `WORK` | sin checada, `day == today` y `now ≤ límite` | `PENDING` |
| `WORK` | sin checada | `ABSENT` |

Checadas de `sr_id` sin empleado configurado → aviso `UNMAPPED_CHECKIN`
(se devuelven en `warnings`, nunca se descartan en silencio).

### 7.5 `justify.apply_justifications(results, justifications) -> list[DayResult]`
Asocia cada justificación a su `LATE`/`ABSENT` del mismo empleado-día y fija
`justification_id` y `rh_type`. Una justificación sin incidencia correspondiente (p.
ej. se agregó la excepción después) se reporta como aviso `ORPHAN_JUSTIFICATION`.

### 7.6 `rh.to_rh_rows(results, employees) -> list[RhRow]`

| Resultado | `rh_type` para RH |
|---|---|
| `LATE` sin justificar | `RETARDO` |
| `LATE` justificado | el de la justificación (por defecto `NO_CAPTURAR`) |
| `ABSENT` sin justificar | `FALTA_INJUSTIFICADA` |
| `ABSENT` justificado | el de la justificación (por defecto `FALTA_JUSTIFICADA`) |
| `JUSTIFIED` | el `rh_type` de la excepción |
| demás | no genera fila |

Filas con `NO_CAPTURAR` se omiten. `RhRow` = nombre en RH (o nombre corto si falta,
con aviso `MISSING_RH_NAME`), fecha, tipo, comentario. Orden: empleado, fecha.
`UNREGISTERED_CHANGE` no genera fila pero cuenta como **pendiente de resolver** en
el resumen; se resuelve con "cambio de descanso" (`POST /exceptions/rest-swap`, §8.2) o `REST_TO_WORK`.

### 7.7 `summary.summarize(results, grouping) -> list[EmployeeSummary]`
Por empleado y por semana ISO o mes: días trabajados, retardos (total/justificados),
faltas (total/justificadas), ausencias justificadas por tipo, pendientes de resolver.

## 8. API (1e)

### 8.1 Convenciones
- Sobre común: `{"success": bool, "data": ..., "error": {"code", "message"} | null,
  "meta": {...} | null}`. Manejadores globales convierten `RequestValidationError`
  → 422 `VALIDATION_ERROR`, `NotFound` → 404, `Conflict` → 409,
  `SrUnavailableError` → 503 `SR_UNAVAILABLE`, cualquier otra → 500 `INTERNAL`
  (detalle solo en log).
- Rangos: `from` y `to` como fechas ISO, **inclusivos**, máx. 93 días.
- Endpoints síncronos (`def`): pymssql bloquea; FastAPI los corre en threadpool.
- Mensajes de error en español (UI); códigos en inglés.

### 8.2 Endpoints

| Método y ruta | Descripción |
|---|---|
| `GET /health`, `GET /health/sr` | §4 |
| `GET/POST /employees`, `GET/PATCH /employees/{id}` | CRUD (sin DELETE; se desactiva) |
| `GET /employees/sr-preview` | empleados de `meseros` con marca de ya importado |
| `POST /employees/import-from-sr` | crea los `sr_id` indicados que no existan (`area=OTHER`, `applies_lateness=true`, `tracks_attendance=true` por defecto) |
| `GET/POST /rest-rules`, `PATCH/DELETE /rest-rules/{id}` | filtro `employee_id` |
| `GET/POST /exceptions`, `PATCH/DELETE /exceptions/{id}` | filtros `from`, `to`, `employee_id` |
| `POST /exceptions/rest-swap` | crea en una transacción `WORK_TO_ABSENCE(DESCANSO)` en `absent_day` + `REST_TO_WORK` en `worked_day` (decisión #4) |
| `GET/POST /justifications`, `PATCH/DELETE /justifications/{id}` | filtros `from`, `to` |
| `GET /settings`, `PUT /settings` | valida formato `HH:MM` y tolerancia 0–60 |
| `GET /attendance/calendar?from&to` | `PlannedDay` + `DayResult` por empleado-día, `warnings` |
| `GET /attendance/incidents?from&to` | `LATE`, `ABSENT`, `UNREGISTERED_CHANGE`, `JUSTIFIED` + filas RH |
| `GET /attendance/summary?from&to&group=week\|month` | §7.7 |
| `GET /attendance/export.xlsx?from&to` | §8.4 |

### 8.3 Servicio de asistencia
`services/attendance.py` orquesta: lee config de repos, pide checadas a `SrSource`
(`[from, to]`, saltando la llamada si todo el rango es futuro), llama a `domain/` y
arma la respuesta. Es el único lugar que junta DB + SR + dominio. `today`/`now` se
calculan aquí con `APP_TIMEZONE`.

### 8.4 Export Excel
Libro con tres hojas: **Semana/Calendario** (empleado × día, celda con hora de
checada y color por outcome), **Incidencias RH** (nombre RH, fecha, tipo,
comentario — lista para copiar) y **Resumen**. Nombre:
`asistencia_<from>_<to>.xlsx`. Tests abren el archivo con openpyxl y validan
contenido, no estilos.

## 9. Frontend (1f, Plan B)

- Next.js (App Router), TypeScript, Tailwind, shadcn/ui, TanStack Query; tipos
  generados con `openapi-typescript` desde `/openapi.json` (script `gen:api`,
  archivo generado versionado).
- El navegador solo habla con Next.js: `rewrites` de `/backend/*` → `BACKEND_URL`.
- **Login falso (D4)**: `/login` → route handler compara con `FAKE_AUTH_USER` /
  `FAKE_AUTH_PASSWORD` y pone cookie `httpOnly` `tc_session`; `proxy.ts` (Next 16 renombró `middleware`)
  redirige a `/login` sin cookie; botón "Salir" la borra. Todo en `lib/auth/` para
  reemplazarlo después.
- **Vistas**:
  - `/semana` (inicio): selector de semana ISO; cuadrícula empleado × día, celda =
    hora de checada + color por outcome, indicador de excepción/justificación;
    clic en celda abre panel con detalle y acciones (justificar, cambio de descanso,
    agregar excepción).
  - `/incidencias`: rango (semana por defecto); tabla de filas RH con botón copiar;
    sección "Pendientes de resolver" (`UNREGISTERED_CHANGE`); acción justificar.
  - `/mes`: resumen por empleado del mes.
  - `/configuracion`: empleados (importar de SR, editar nombre RH, área, flags),
    reglas de descanso, excepciones, horarios y tolerancia.
  - Botón "Exportar a Excel" en semana, incidencias y mes.
- Errores: `503 SR_UNAVAILABLE` → aviso "No se pudo leer SoftRestaurant. Revisa
  Tailscale." con reintentar; la configuración sigue usable.
- Paleta de outcomes fija y accesible (texto + color, no solo color).

## 10. Manejo de errores y seguridad

- SR: solo `reportes_ro`, solo las dos consultas de §5, `NOLOCK`, acotadas.
  `/health/sr` alerta si el login no es de solo lectura.
- Secretos solo en `.env`; logs sin credenciales ni cadenas de conexión.
- Validación Pydantic en todo request; fechas, rangos y enums estrictos.
- ORM parametrizado en Postgres; SQL de SR con parámetros.
- Datos de prueba y demo sintéticos; ningún nombre, IP o cifra real en el repo.

## 11. Pruebas

| Capa | Herramienta | Datos | Qué cubre |
|---|---|---|---|
| `domain/` | pytest (TDD) | sintéticos | cada fila de las tablas §7.3, §7.4, §7.6; bordes de tolerancia (`:59`/`:00`), paridad de semana doble, precedencia de excepciones, `today`/`now` |
| `sr/` | pytest + cursor falso | sintéticos | SQL exacto, columnas prohibidas, normalización, límites, errores |
| `repos/` | pytest + Postgres real | sintéticos | restricciones, traslapes → 409, inmutabilidad de lo devuelto |
| `api/` | pytest + `TestClient`, `FakeSource` | sintéticos | sobre, códigos de error, flujo calendario/incidencias/export |
| SR real | `@pytest.mark.sr` | reales (solo local) | conexión, consultas; nunca en CI |
| Conciliación | `scripts/reconcile_attendance.py` | `db_examples/` (local) | aceptación #2: conteo por empleado de agosto 2026 = export SR |
| Frontend | Vitest, Playwright E2E (`SR_MODE=fake`) | sintéticos | login → semana → justificar → incidencias → exportar |

Cobertura: ≥ 80% global del backend; `domain/` > 95%.

## 12. Fuera de alcance (etapa 1)

Auth real, multiusuario, despliegue fuera de la Mac, agentes (etapa 2), ventas
(etapa 3), lectura/escritura en RH (etapa 5), horario por empleado, historial de
cambios (auditoría).
