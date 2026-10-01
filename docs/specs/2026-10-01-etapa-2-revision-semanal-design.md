# Etapa 2 — Agente de revisión semanal: diseño

> Estado: **aprobado** (2026-10-01; ajustes del 2026-10-01 al escribir el plan: loop manual en
> vez del Tool Runner, sin APScheduler, umbrales en `/settings/review`). Deriva de [`plan.md`](../plan.md) §5 Etapa 2 y se
> apoya en todo lo construido en la Etapa 1
> ([`2026-09-29-etapa-1-asistencia-design.md`](2026-09-29-etapa-1-asistencia-design.md)).
> Reglas de negocio de `plan.md` §4 y §6 aplican tal cual.

## 1. Objetivo y criterios de éxito

Cada semana, un agente prepara el borrador del reporte de incidencias: señala lo raro,
lo explica en lenguaje natural y deja la lista propuesta para RH. El gerente revisa,
justifica con las acciones que ya existen y aprueba desde la UI.

**Aceptación**
1. El jueves a las 17:30 y el lunes a las 09:00 aparece un borrador sin intervención,
   aunque la Mac haya estado dormida a esa hora (se genera al despertar, §6.2).
2. "Generar ahora" desde la UI produce un borrador para cualquier semana.
3. En la evaluación (§10.2) el agente **nunca** omite ni inventa hallazgos (lo garantiza
   el validador) y la prioridad/acción sugerida coincide con lo esperado en los casos
   claros.
4. Ningún nombre real de empleado sale hacia la API de Anthropic (verificado en la
   evaluación registrando los payloads).
5. Cobertura ≥ 80% del backend; `domain/` > 95%.

## 2. Decisiones de diseño

| # | Decisión | Motivo |
|---|---|---|
| E1 | **Periodos:** el jueves se revisa la semana ISO en curso (lun–jue reales, vie–dom futuros); el lunes se revisa la semana anterior completa. | Así se envía a RH: jueves ~17:30 con ajustes hasta el domingo (`plan.md` §4). |
| E2 | **El código detecta, el agente explica.** Los hallazgos son reglas deterministas en `domain/review.py`; el agente prioriza, explica y sugiere acción. La lista para RH sale de `to_rh_rows`, nunca del modelo. | Principio 5 de `plan.md`: los agentes no inventan números. Hace la evaluación objetiva. |
| E3 | **Agente con herramientas** (loop propio sobre `client.beta.messages.create` del SDK `anthropic`), solo de lectura, sobre datos ya calculados por `services/` (nunca SR ni Postgres directo). | Elección del enfoque B: el agente decide qué contexto consultar. Loop propio en vez del Tool Runner (beta): el runner de Python no reanuda `pause_turn`, complica el reintento de validación en la misma conversación y no se puede sustituir por un cliente falso en tests. |
| E4 | **Seudónimos:** hacia la API solo viajan `E{employee.id}`; el backend sustituye el nombre corto al servir el borrador. | Ningún nombre real sale del equipo. |
| E5 | **Validador en código** con un reintento; si falla, el borrador queda sin narrativa (`READY_NO_NARRATIVE`). | La garantía "no omite, no inventa" no depende del prompt. Los hallazgos siguen sirviendo sin texto. |
| E6 | **Servicio `worker`** (misma imagen), un loop cada 10 s que programa y ejecuta; único ejecutor de corridas. La API solo encola. | Sin corridas duplicadas, la API no se bloquea con llamadas largas. La misma regla de recuperación (§6.2) cubre las corridas a tiempo, así que no hace falta APScheduler. |
| E7 | **El borrador se persiste como snapshot** (hallazgos, filas RH, narrativa). | Excepción explícita a D2 de la Etapa 1: un borrador es un documento fechado. La UI avisa si los datos cambiaron (`stale`). |
| E8 | **`REVIEW_AGENT=live\|fake`.** `fake` genera narrativa determinista con plantilla. | Demo pública, E2E y CI sin llave ni costo, igual que `SR_MODE`. |
| E9 | **Modelo `claude-opus-5-5`**, `effort: "medium"`, `fallbacks: "default"` (beta `server-side-fallback-2026-07-01`) para rechazos. Configurable con `REVIEW_MODEL`. | Modelo por defecto actual; dos corridas por semana cuestan centavos. |
| E10 | **Solo aviso en la UI.** Sin correo ni otros canales. | YAGNI; decisión del gerente. |

## 3. Estructura nueva

```
backend/src/tabernas/
  domain/review_types.py        # enums y dataclasses de la revisión, ReviewSettings
  domain/review.py              # hallazgos deterministas (§4)
  domain/review_schedule.py     # ranuras jueves/lunes y recuperación (§6.2)
  agents/
    pseudonyms.py               # E{id} ↔ empleado, render de {E12}, scrub
    weekly_review/
      agent.py                  # protocolos ReviewAgent y MessagesApi, AgentOutcome
      tools.py                  # 4 herramientas de lectura (§5.2)
      prompt.py                 # prompt de sistema fijo (español)
      schema.py                 # salida estructurada (esquema + Pydantic)
      validate.py               # validador (§5.4)
      runner.py                 # LiveReviewAgent: loop propio + reintento
      anthropic_api.py          # adaptador del SDK anthropic (MessagesApi)
      fake.py                   # FakeReviewAgent (REVIEW_AGENT=fake)
      factory.py                # build_review_agent(settings)
  services/review.py            # orquesta: reporte → hallazgos → agente → snapshot
  repos/reviews.py, repos/review_codec.py, repos/review_settings.py
  api/routes/reviews.py         # §7; /settings/review en api/routes/settings.py
  worker.py                     # loop: programa, recupera y ejecuta (§6)
backend/tests/
  domain/  agents/  services/  repos/  api/  test_worker.py
  eval/                         # @pytest.mark.agent (§10.2)
frontend/src/app/(app)/revision/  + lib/api/reviews.ts + components/review/
```

## 4. Hallazgos (`domain/review.py`)

Función pura:

```python
find_findings(week_results, history_results, warnings, employees, settings,
              week_start, week_end) -> list[Finding]

@dataclass(frozen=True)
class Finding:
    id: str                    # f"{kind}:{employee_id or '-'}:{first_day or '-'}"
    kind: FindingKind
    employee_id: int | None
    days: tuple[date, ...]
    facts: Mapping[str, int | str]   # p. ej. {"late_count": 3, "weeks_with_late": 3}
```

`week_results` y `history_results` son `DayResult` ya justificados (salida de
`AttendanceService.build`). El historial cubre las 4 semanas ISO previas.

| `FindingKind` | Regla | Días |
|---|---|---|
| `REST_DAY_CHECKIN` | `UNREGISTERED_CHANGE` en la semana | ese día (uno por día) |
| `ABSENT_NO_EXCEPTION` | `ABSENT` sin `justification_id`, que no forme parte de una racha | ese día (uno por día) |
| `NO_CHECKIN_STREAK` | ≥ `review_streak_days` (2) días laborales consecutivos en `ABSENT` sin justificar; la racha puede empezar en la semana anterior siempre que termine dentro de la semana revisada | todos los de la racha (uno por racha) |
| `REPEATED_LATE` | `LATE` **sin justificar** ≥ `review_late_week` (2) en la semana, **o** semanas con algún `LATE` (justificado o no: cuenta el patrón) ≥ `review_late_weeks` (3) entre las 4 previas y la actual | los retardos de la semana (uno por empleado) |
| `CONFIG_WARNING` | cada aviso del reporte de la semana (`NO_REST_RULE`, `UNMAPPED_CHECKIN`, `MISSING_RH_NAME`, `ORPHAN_JUSTIFICATION`, `NO_SR_ID`), deduplicado por código + empleado. `facts` guarda el código y el número de ocurrencias, **nunca** el texto del aviso (puede traer nombres) | los del aviso, si tiene |

- "Consecutivos" se mide sobre días **laborales planeados** (`planned == WORK`): un
  descanso o cierre en medio no rompe la racha; un día `OK`/`LATE` sí.
- Las faltas que entran en `NO_CHECKIN_STREAK` no generan además `ABSENT_NO_EXCEPTION`.
- Días `FUTURE` y `PENDING` se ignoran.
- `REPEATED_LATE` exige al menos un retardo en la semana revisada.
- Orden de salida: tipo (orden de la tabla), luego empleado, luego primer día.
- Los umbrales viven en `setting` (claves `review_streak_days`, `review_late_week`,
  `review_late_weeks`), sembrados por migración y editables en Configuración
  (`GET/PUT /settings/review`, que valida enteros 1–7, 1–7 y 1–5; `/settings` no cambia).

Los ids son estables: correr dos veces sobre los mismos datos produce los mismos ids, lo
que permite comparar el snapshot contra el estado actual (`stale`).

## 5. Agente (`agents/weekly_review/`)

### 5.1 Ejecución

- `ReviewAgent` (protocolo): `run(context: ReviewContext) -> AgentOutcome`.
  `LiveReviewAgent` corre un loop propio (solo agrega mensajes, nunca edita el
  historial) sobre `client.beta.messages.create` con `claude-opus-5-5`,
  `output_config={"effort": "medium", "format": <esquema §5.3>}`, prompt de sistema con
  `cache_control`, `max_tokens` 16000 y tope de **8 vueltas** (exceder = fallo de
  narrativa). Un adaptador (`MessagesApi`) aísla al SDK para poder probar el loop con
  respuestas guionizadas.
- Se revisa `stop_reason` antes de leer contenido (`refusal`, `max_tokens`).
- `ReviewContext` = semana, `as_of`, hallazgos, reporte de la semana e historial ya
  calculados por el servicio: las herramientas responden de memoria y no vuelven a
  consultar SR durante el loop.
- El reloj ("hoy"/"ahora") llega como parámetro, como en la Etapa 1.

### 5.2 Herramientas (solo lectura, alcance fijo a la semana de la corrida)

| Herramienta | Entrada | Devuelve |
|---|---|---|
| `get_week_findings` | — | hallazgos (§4) con seudónimos |
| `get_week_incidents` | — | incidencias (`LATE`, `ABSENT`, `UNREGISTERED_CHANGE`, `JUSTIFIED`) y filas RH propuestas |
| `get_employee_history` | `employee` (`E12`), `weeks` 1–8 | resumen semanal (`summarize`) de ese empleado |
| `get_employee_week` | `employee` | día a día: planeado, outcome, hora de checada, minutos tarde, `rh_type`, comentario de excepción/justificación |

- Comentarios de excepciones y justificaciones son texto libre del gerente: antes de
  enviarse se reemplaza cualquier nombre corto o nombre RH conocido por su seudónimo.
- Un seudónimo desconocido o un `weeks` fuera de rango devuelve `tool_result` con
  `is_error: true` y un mensaje claro; no se lanza excepción.
- `get_employee_history` necesita hasta 8 semanas previas: el servicio construye el
  historial una vez (≤ 63 días, dentro del límite de 93).

### 5.3 Salida estructurada (`schema.py`)

```python
class ReviewItem(BaseModel):
    finding_id: str
    priority: Literal["HIGH", "MEDIUM", "LOW"]
    explanation: str                     # 1–3 frases, puede usar {E12}
    suggested_action: Literal["JUSTIFY", "REST_SWAP", "ADD_EXCEPTION", "FIX_CONFIG", "NONE"]

class ReviewNarrative(BaseModel):
    summary: str                         # 3–6 frases, puede usar {E12}
    items: list[ReviewItem]
```

Las acciones corresponden a acciones que ya existen en la UI: justificar,
`POST /exceptions/rest-swap`, crear excepción y corregir configuración.

### 5.4 Validador (`validate.py`)

Función pura `validate(narrative, findings, aliases) -> list[ValidationError]`:
- Los `finding_id` de `items` son **exactamente** los de `findings`: sin faltantes, sin
  repetidos y sin ids desconocidos.
- Todo `{E..}` en `summary` y `explanation` es un seudónimo existente.
- Ningún texto contiene un nombre real conocido (defensa en profundidad).

Si hay errores, se reintenta **una vez** en la misma conversación, enviando la lista de
errores concretos. Si el segundo intento falla, el resultado es `READY_NO_NARRATIVE`
con los errores en `error`. Una semana sin hallazgos es válida (`items` vacío).

### 5.5 Prompt de sistema (`prompt.py`)

Fijo y en español: el rol (preparar el borrador semanal para el gerente), las reglas de
negocio de `plan.md` §4 resumidas, el significado de cada `FindingKind` y de cada
acción, la regla "no calcules ni inventes cifras: usa las herramientas" y el uso de
`{E12}` para nombrar empleados. No incluye fechas ni datos variables, para que el
caché funcione; la semana y `as_of` van en el primer mensaje del usuario.

### 5.6 Seudónimos (`agents/pseudonyms.py`)

- `alias(employee_id) -> "E{id}"` y `render(text, employees) -> str`, que sustituye
  `{E12}` por el nombre corto (o deja `{E12}` si el empleado ya no existe).
- `scrub(text, employees) -> str` reemplaza nombres conocidos por su seudónimo; lo
  usan las herramientas para los comentarios libres.
- En la base el borrador se guarda **con seudónimos**; `render` se aplica al servirlo.

## 6. Ejecución programada (`worker.py`)

### 6.1 Cola

- Servicio `worker` en `docker-compose.yml`: misma imagen que `backend`, comando
  `python -m tabernas.worker`, mismas variables, `depends_on: db` sano.
- Cada 10 s toma la fila `QUEUED` más antigua (`SELECT … FOR UPDATE SKIP LOCKED`), la
  pasa a `RUNNING` y llama a `ReviewService.run(review_id)`.
- Al arrancar, toda fila `RUNNING` con más de 15 min pasa a `FAILED` ("se interrumpió
  la corrida").

### 6.2 Programación y recuperación

- Sin librería de cron; zona `APP_TIMEZONE`. Ranuras: **jueves 17:30** → semana ISO en curso
  (`trigger=THURSDAY`); **lunes 09:00** → semana anterior (`trigger=MONDAY`). Las horas
  son constantes en `domain/review_schedule.py`, no UI.
- En cada vuelta del loop (10 s), el worker calcula la última ranura vencida; si venció hace
  ≤ 24 h y no existe ninguna corrida con ese `trigger` para esa semana, la encola. Así
  la Mac dormida a la hora programada genera el borrador al despertar.
- Encolar es idempotente: si ya hay una `QUEUED`/`RUNNING` para la semana, no se crea
  otra.

## 7. Persistencia y API

### 7.1 Tabla `weekly_review`

| Columna | Tipo | Notas |
|---|---|---|
| `id`, `created_at`, `updated_at` | | como el resto |
| `iso_year`, `iso_week` | int | semana revisada |
| `trigger` | `THURSDAY` / `MONDAY` / `MANUAL` | |
| `status` | `QUEUED` / `RUNNING` / `READY` / `READY_NO_NARRATIVE` / `FAILED` / `APPROVED` | |
| `as_of` | timestamp null | cuándo se tomaron los datos (hora local naive, como el reloj de la app) |
| `findings`, `rh_rows` | jsonb null | snapshot con seudónimos |
| `narrative` | jsonb null | `ReviewNarrative` con seudónimos |
| `model`, `input_tokens`, `output_tokens` | null | registro de la corrida |
| `error` | text null | mensaje en español, sin secretos |
| `approved_at` | timestamp null | hora local naive |

- Índice único parcial: una sola fila `QUEUED`/`RUNNING` por (`iso_year`, `iso_week`).
- Solo `READY` y `READY_NO_NARRATIVE` pueden aprobarse; aprobar es definitivo (para
  corregir se genera otro borrador).
- El repo devuelve dataclasses inmutables, como en la Etapa 1.

### 7.2 Endpoints

| Método y ruta | Descripción |
|---|---|
| `POST /reviews` `{year, week}` | encola `MANUAL` → **202** con la fila; 409 `CONFLICT` si ya hay una en curso |
| `GET /reviews?year&week` | lista de la semana (o las 20 más recientes sin filtros), más reciente primero (sin `stale`) |
| `GET /reviews/{id}` | detalle con nombres ya sustituidos y `stale: bool \| null` (§7.3) |
| `POST /reviews/{id}/approve` | → `APPROVED`; 409 si el estado no lo permite |

### 7.3 `stale`

Al pedir el detalle de un borrador `READY`/`READY_NO_NARRATIVE`/`APPROVED`, el servicio
recalcula hallazgos y filas RH de esa semana y compara ids y filas con el snapshot.
`true` si difieren. Si SR no responde, `null` (la UI no muestra el aviso).

### 7.4 Configuración nueva (`config.py`, `.env.example`)

`ANTHROPIC_API_KEY` (SecretStr, vacío por defecto), `REVIEW_AGENT=live|fake` (por
defecto `fake`, como `SR_MODE`), `REVIEW_MODEL=claude-opus-5-5`. Con `live` y sin
llave, cada corrida termina en `READY_NO_NARRATIVE` con el motivo; la app no se niega a
arrancar.

## 8. Frontend (`/revision`)

- Entrada nueva en el menú: **Revisión**. Selector de semana ISO (por defecto la
  semana del borrador más reciente).
- Estado `QUEUED`/`RUNNING`: aviso "Generando borrador…" y sondeo cada 3 s.
- Borrador listo:
  - **Resumen** del agente.
  - **Hallazgos** agrupados por prioridad (Alta, Media, Baja). Cada tarjeta muestra los
    datos del hallazgo (tipo, empleado, días, cifras de `facts`), la explicación del
    agente y un botón con la acción sugerida que abre `/semana?desde=<lunes>&empleado=<id>&dia=<fecha>`;
    `/semana` aprende a abrir el panel del día con esos parámetros.
  - Sin narrativa: se muestran los hallazgos sin prioridad ni explicación, con el aviso
    "El agente no pudo redactar este borrador" y el motivo.
  - **Lista para RH** con botón de copiar (mismo componente que `/incidencias`).
  - Aviso si `stale`: "Los datos cambiaron desde este borrador" + "Generar de nuevo".
  - Botones **Generar de nuevo** y **Aprobar**; un borrador aprobado muestra la fecha.
- Historial de borradores de la semana (estado, disparador, hora).
- Tipos generados de OpenAPI (`npm run gen:api`), hooks TanStack Query en
  `lib/api/reviews.ts`.

## 9. Manejo de errores y seguridad

| Falla | Resultado |
|---|---|
| SR no responde al construir el reporte | `FAILED`, "No se pudo leer SoftRestaurant. Revisa Tailscale." |
| Error de la API de Anthropic tras los reintentos del SDK (2) | `READY_NO_NARRATIVE` con el motivo; hallazgos y filas RH guardados |
| `stop_reason` `refusal` sin fallback disponible, `max_tokens`, o > 8 vueltas | `READY_NO_NARRATIVE` |
| Validador falla dos veces | `READY_NO_NARRATIVE` con los errores |
| Excepción inesperada | `FAILED`, detalle solo en log |

- Errores de Anthropic se atrapan del más específico al más general
  (`RateLimitError`, `APIStatusError`, `APIConnectionError`).
- La llave solo vive en `.env`; logs sin llave, sin nombres reales y sin el contenido
  completo de los payloads (solo conteos y tokens).
- Herramientas sin efectos secundarios; el agente no puede escribir nada.
- SR sigue intacto: el agente solo ve lo que ya calculó `AttendanceService`.

## 10. Pruebas y evaluación

### 10.1 Pruebas (CI, `REVIEW_AGENT=fake`, sin red)

| Capa | Qué cubre |
|---|---|
| `domain/review.py` (TDD) | cada regla de §4 con sus bordes: umbrales exactos, racha que cruza semanas, descanso en medio de racha, futuros/pendientes ignorados, justificadas excluidas, deduplicación, orden e ids estables |
| `pseudonyms`, `validate` | alias/render/scrub; faltantes, repetidos, inventados, seudónimo desconocido, nombre real filtrado |
| `tools` | salida con seudónimos, errores `is_error`, límites de `weeks` |
| `runner` | cliente Anthropic falso con respuestas guionizadas: éxito, hallazgo omitido → reintento → éxito, dos fallos → sin narrativa, `refusal`, `max_tokens`, tope de vueltas |
| `services/review` | flujo completo con `FakeSource` + `FakeReviewAgent`, `stale`, SR caído |
| `repos/reviews`, `api/reviews` | índice único, transiciones de estado, 202/409, sobre |
| `worker` | cálculo de ranuras y recuperación (reloj inyectado), toma de cola, filas colgadas |
| Frontend | Vitest de componentes de revisión; E2E: generar → borrador → aprobar |

### 10.2 Evaluación del agente (`@pytest.mark.agent`, local, cuesta dinero, nunca CI)

- 6–8 semanas sintéticas con resultado esperado: semana limpia, racha sin checar,
  descanso con checada, retardos repetidos (semana e historial), avisos de config y una
  mezcla de todo.
- Por caso se registra: validador aprobado a la primera, prioridad `HIGH` esperada en
  casos claros (racha, falta sin excepción), acción sugerida esperada, número de vueltas,
  tokens y costo.
- Un interceptor registra los payloads enviados y falla si aparece cualquier
  `short_name` o `rh_name` de los empleados sintéticos.
- Comando: `uv run pytest -m agent` (requiere `ANTHROPIC_API_KEY`).

## 11. Fuera de alcance (etapa 2)

Notificaciones (correo, mensajería), escribir en la herramienta de RH (etapa 5), chat
libre con el agente, editar la narrativa a mano, horarios de corrida editables desde la
UI y auth real.
