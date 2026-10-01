# Plan de desarrollo — Tabernas Cerveceras

> Estado: **aprobado a nivel de etapas** (2026-09-28). Cada etapa tendrá su propio
> diseño detallado antes de escribir código. Mapa de la base de SoftRestaurant en
> [`db-map.md`](db-map.md).

## 1. Contexto

Cada semana se sacan reportes de **asistencia** (para detectar retardos y faltas) y
de **ventas** desde SoftRestaurant (SR), un punto de venta que solo corre en Windows.
Hoy eso implica: prender Tailscale → abrir una VM Windows → abrir SR → exportar →
revisar a mano → capturar incidencias en la herramienta de RH (hecha por el dueño,
sin API).

**Objetivo:** leer la base de SR directamente desde la Mac, calcular incidencias y
tendencias automáticamente, y apoyar las decisiones con agentes de IA — sin tocar
nunca la operación del punto de venta.

**Usuario:** una persona (el gerente), que revisa, justifica y captura en RH.
**Proyecto de portafolio:** el código se publica; los datos del negocio no.

### Fuera de alcance

- Escribir en la base de SR (siempre solo lectura).
- Reemplazar la herramienta de RH o calcular nómina.
- Acceso multiusuario o despliegue en internet (se evalúa después de la etapa 5).

## 2. Arquitectura

```
 SoftRestaurant (SQL Server 2014 Express, solo lectura)     Herramienta RH (web, sin API)
        │ Tailscale                                                ▲ (etapa 5)
        ▼                                                          │
┌───────────────────────────── docker compose ─────────────────────┼──────────┐
│                                                                  │          │
│  backend   FastAPI · Python · uv                                 │          │
│   ├─ sr/        conector SR (pymssql, SELECT + NOLOCK)           │          │
│   ├─ domain/    lógica pura (planeado vs real, métricas)         │          │
│   ├─ repos/     acceso a Postgres (SQLAlchemy)                   │          │
│   ├─ api/       REST + exportación Excel                         │          │
│   └─ agents/    agentes con Claude (etapas 2, 4, 5) ─────────────┘          │
│                                                                             │
│  db        PostgreSQL: configuración, excepciones, justificaciones,         │
│            copia analítica de ventas (etapa 3)                              │
│                                                                             │
│  frontend  Next.js · TypeScript → consume solo la API                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Stack

| Capa | Tecnología | Por qué |
|---|---|---|
| Backend | Python 3.12, **uv**, **FastAPI**, Pydantic v2, pydantic-settings | Tipado, OpenAPI automático, mismo lenguaje que el análisis de datos |
| Conector SR | **pymssql** (FreeTDS) + `freetds.conf` con TLS 1.0 | Única opción probada contra este SQL Server 2014 |
| Base propia | **PostgreSQL 16**, SQLAlchemy 2.0, **Alembic** | Migraciones versionadas, estándar de producción |
| Excel | openpyxl | Exportación con formato |
| Frontend | **Next.js** (App Router), TypeScript, Tailwind CSS, shadcn/ui, TanStack Query | Stack moderno y demostrable |
| Contrato API | Tipos TS generados del OpenAPI (`openapi-typescript`) | Front y back nunca se desalinean |
| Gráficas | Recharts (etapa 3) | Integración directa con React |
| Agentes | Claude vía Messages API (SDK `anthropic`), `claude-opus-5-5`, loop propio con herramientas | Decidido en el diseño de la etapa 2 |
| Automatización web | Playwright (Python) (etapa 5) | Robusto para leer/capturar en RH |
| Pronóstico | pandas + statsmodels (etapa 4) | Modelos estadísticos simples y explicables |
| Calidad | pytest + pytest-cov, ruff, pyright · Vitest, ESLint · Playwright E2E | TDD con 80%+ de cobertura |
| Infra | Docker Compose, GitHub Actions (lint + tests) | Un comando para levantar todo |

### Estructura del repositorio

```
backend/          FastAPI (pyproject.toml, src/, tests/, alembic/)
frontend/         Next.js
docs/             plan.md, db-map.md, specs/ (diseño por etapa)
sql/              scripts de administración de SR (usuario de solo lectura)
scripts/          utilidades (check de conexión)
docker-compose.yml
freetds.conf
.env.example
```

## 3. Principios transversales

1. **SR es producción: solo lectura.** Login `reportes_ro` (`db_datareader` +
   `db_denydatawriter`), solo `SELECT`, siempre `WITH (NOLOCK)` y siempre acotado
   por fechas. Es SQL Server Express: consultas ligeras.
2. **Conciliación contra SR como prueba de aceptación.** Toda cifra nueva se valida
   contra un reporte exportado de SR antes de darse por buena (ver `db-map.md`).
3. **Lógica de negocio pura y probada.** `domain/` no conoce bases de datos ni HTTP;
   recibe datos y devuelve resultados. Ahí vive el grueso de los tests.
4. **Los datos reales no entran al repo.** Nombres de empleados, IPs, ventas y
   reportes de ejemplo viven en `.env`, en Postgres o en carpetas ignoradas. Tests y
   demo usan **datos sintéticos**.
5. **Los agentes no inventan números.** El código calcula; el agente interpreta,
   resume y señala. Toda acción con efectos externos (etapa 5) requiere aprobación.
6. **Configuración, no código.** Horarios, tolerancias y reglas de descanso se
   editan desde la UI, no están fijos en el código.

## 4. Reglas de negocio conocidas

### Asistencia

- Los empleados solo checan **entrada** en SR; la salida no se usa.
- **Hora de entrada:** cocina 16:30, resto 16:40. **Tolerancia:** 10 min.
  Retardo = checada posterior a hora de entrada + tolerancia.
- **Descansos:** cada empleado tiene un día fijo por semana y, cada 2 semanas, un día
  extra (compensa que se abre en festivos). Se abre todos los días.
  → 11 días de trabajo por cada 2 semanas.
- **Cambios de descanso** ocurren (reposiciones, cubrir días) y se justifican.
- No existen horas extra ni días extra.
- Hay un empleado (el gerente) al que aplican faltas pero **no** retardos, y que no
  checa en SR: sus incidencias se registran manualmente.
- **Periodo de nómina:** semanal, lunes a domingo (semana ISO), pagado el lunes
  siguiente. El reporte se envía el jueves; se aceptan modificaciones hasta el domingo.
- **Retardo:** se ignoran los segundos (pasando el minuto ya es retardo).

### Comparación planeado vs real

| Planeado | Checada en SR | Resultado |
|---|---|---|
| Trabaja | A tiempo | OK |
| Trabaja | Tarde | **Retardo** (justificable) |
| Trabaja | Ninguna | **Falta** (justificable) |
| Descanso | Sí | **Cambio sin registrar** (se confirma o corrige) |
| Vacaciones / incapacidad / permiso | — | Justificado |

### Ventas (derivadas por conciliación)

- El periodo se filtra por `cheques.cierre` (el bar cierra después de medianoche).
- Excluir tickets con `cancelado = 1`.
- Venta por renglón = `cantidad × precio × (1 − desc_renglón%) × (1 − desc_ticket%)`.
- Cocina vs barra se distingue por el grupo de producto.

## 5. Etapas

### Etapa 1 — Base del sistema + Asistencia

> Estado: **cerrada el 2026-09-30.** Backend (1a–1e) terminado y aceptado (Plan A);
> frontend (1f) terminado (Plan B: UI, pruebas unitarias, E2E y CI; PR #3 con CI en
> verde).
>
> Pendientes conocidos (no bloquean; se retoman cuando haga falta):
> - `DayOut` no indica si un día viene de una excepción, así que la celda de la semana
>   solo marca justificaciones (§9 del spec pide ambas). Requiere un campo en el backend.
> - Mejoras menores de UI: validaciones del lado del cliente en formularios (rango de
>   fechas, ancla en lunes), más pruebas de componentes y detalles de accesibilidad.
> - La exportación a Excel es un enlace directo: si el backend responde con error, el
>   navegador descarga un archivo inválido en lugar de mostrar el mensaje.

**Objetivo:** reemplazar el reporte semanal/mensual de asistencia de SR con uno que
ya calcule retardos y faltas contra lo planeado, permita justificarlos y deje lista
la lista para capturar en RH.

**1a. Infraestructura**
- Monorepo, `docker-compose.yml` con `backend`, `db`, `frontend`.
- **Primer riesgo a validar:** que el contenedor del backend alcance SR por el
  Tailscale del host. Plan B: contenedor sidecar de Tailscale.
- `GET /health` y `GET /health/sr` (versión del servidor, login, rol de solo lectura).
- CI: ruff, pyright, pytest, ESLint, Vitest.

**1b. Conector SR** (`sr/`)
- `fetch_checadas(desde, hasta)` y `fetch_empleados()` con esquemas Pydantic.
- Normaliza `idempleado` (`'06'` ↔ `6`). Nunca selecciona columnas sensibles
  (`contraseña`, `fotografia`).
- Test de integración (marcado, opcional) contra SR real; unitarios con datos sintéticos.

**1c. Modelo de datos propio** (Postgres + Alembic)

| Tabla | Contenido |
|---|---|
| `employee` | id SR, nombre corto, nombre en RH, es_cocina, aplica_retardos, controla_asistencia, activo |
| `rest_rule` | empleado, día fijo, día extra, semana ancla de descanso doble, vigencia |
| `schedule_exception` | empleado, fecha(s), tipo (cambio de descanso, día cubierto, vacaciones, incapacidad, permiso…), comentario |
| `justification` | empleado, fecha, incidencia (retardo/falta), motivo, tipo RH al que se mapea |
| `setting` | horas de entrada, tolerancia |

**1d. Dominio** (`domain/`)
- `planned_calendar(empleados, reglas, excepciones, rango)` → estado planeado por día.
- `compare(planeado, checadas, settings)` → incidencias por empleado/día.
- `summarize(incidencias, periodo)` → totales semanales y mensuales.
- Mapeo a los tipos de incidencia de RH (Retardo, Falta injustificada, Falta
  justificada, Vacaciones, Incapacidad…, Descanso).

**1e. API**
- CRUD de empleados, reglas de descanso, excepciones y justificaciones.
- `GET /attendance/calendar?from&to` — planeado vs real por día.
- `GET /attendance/incidents?period=` — incidencias del periodo.
- `GET /attendance/export.xlsx?from&to` — exportación.

**1f. Frontend**
- **Semana:** cuadrícula empleado × día (como el calendario de RH) con planeado vs
  real y colores por resultado.
- **Incidencias del periodo:** lista lista para copiar a RH, con acción de justificar.
- **Mes:** resumen por empleado (retardos, faltas, justificadas).
- **Configuración:** empleados, reglas de descanso, horarios, tolerancia.
- Botón de exportar a Excel.

**Criterios de aceptación**
- `docker compose up` desde cero levanta todo y `/health/sr` responde OK.
- Las checadas de agosto 2026 coinciden 1:1 con el reporte exportado de SR.
- Retardos y faltas de una semana real coinciden con la revisión manual del gerente.
- Cobertura ≥ 80% en `domain/`.

### Etapa 2 — Agente de revisión semanal

> Estado: **en implementación** (Plan A, backend, terminado en la rama `feat/etapa-2-backend`; Plan B, frontend, implementado en la rama `feat/etapa-2-frontend`, PR pendiente) — diseño en
> [`specs/2026-10-01-etapa-2-revision-semanal-design.md`](specs/2026-10-01-etapa-2-revision-semanal-design.md);
> Plan A (backend) en [`plans/2026-10-01-etapa-2-plan-a-backend.md`](plans/2026-10-01-etapa-2-plan-a-backend.md)
> y Plan B (frontend) en [`plans/2026-10-01-etapa-2-plan-b-frontend.md`](plans/2026-10-01-etapa-2-plan-b-frontend.md).

**Objetivo:** cada jueves (día de envío a RH), un agente prepara el borrador del
reporte de incidencias.

- Usa las herramientas de la API de la etapa 1 (no consulta SR directo).
- Señala lo raro: checadas en día de descanso, retardos repetidos, faltas sin
  excepción, empleados sin checada en varios días.
- Produce un resumen en lenguaje natural + la lista propuesta; el gerente justifica y
  aprueba desde la UI.
- Ejecución programada (scheduler en el backend o contenedor `worker`; se decide en
  su diseño) y bajo demanda desde la UI.
- Evaluación: casos sintéticos con resultado esperado (el agente no debe inventar
  incidencias ni omitir las que calcula el dominio).

### Etapa 3 — Tendencias de ventas

**Objetivo:** tablero de tendencias por hora, día de la semana, producto, grupo y
área (cocina/barra).

- **Sincronización incremental** de `cheques`/`cheqdet`/catálogos de SR a Postgres
  (copia analítica): las consultas pesadas no tocan el punto de venta.
- Conciliación: ventas de agosto 2026 contra `PRODUCTOSVENDIDOSPERIODO`.
- Vistas: mapa de calor día × hora, top productos y su evolución, ticket promedio,
  personas por mesa, mezcla cocina vs barra, comparativos semana contra semana.

### Etapa 4 — Agente de pronóstico (cocina y barra)

**Objetivo:** anticipar la carga de cocina y barra de la próxima semana.

- **Modelos estadísticos** en código: línea base por día de la semana × hora,
  tendencia reciente, estacionalidad; validación con backtesting (error medido) antes
  de mostrarse.
- El agente interpreta: "el viernes se esperan ~30% más platillos entre 20 y 22 h",
  "el barril X lleva 3 semanas subiendo; revisar inventario".
- Salida visible en la UI junto a las tendencias.

### Etapa 5 — Agente para RH

**Objetivo:** eliminar la doble captura con la herramienta de RH.

- Playwright con la sesión del gerente (credenciales en `.env`).
- **Lectura:** calendario planeado de RH → reemplaza a las reglas + excepciones
  locales como fuente de lo planeado (el dominio no cambia).
- **Escritura:** captura en RH solo incidencias **ya aprobadas** en la UI, con
  confirmación final.
- Riesgo: la herramienta cambia sin aviso → pruebas de humo antes de cada uso y
  degradación a captura manual.

## 6. Decisiones resueltas

| # | Pregunta | Decisión (2026-09-28) |
|---|---|---|
| 1 | Periodo de pago | **Semanal, lunes a domingo** (semana ISO; p. ej. periodo 39 = 21–27 sep 2026), pagado el lunes siguiente. El calendario de RH usa las mismas semanas. |
| 2 | Días sin ninguna checada (5 y 6 sep 2026) | Pueden ser **cierre** (sábado: sin luz por tormenta) u **olvido de checar** (domingo: sí se abrió). Ambos se registran como excepción; ver tipos abajo. |
| 3 | Precisión del retardo | **Se ignoran los segundos**: retardo si `HH:MM` de la checada > hora de entrada + tolerancia (con 16:40 + 10: `16:50:59` a tiempo, `16:51:00` retardo). |
| 4 | Cambio de descanso en RH | La incidencia se marca **el día que no vino**, y el siguiente día de descanso se cambia a laboral en el calendario. |

### Tipos de excepción (etapa 1)

| Tipo | Alcance | Efecto en el cálculo |
|---|---|---|
| Cierre del local | todos, un día | Nadie debía trabajar; no hay faltas ni retardos ese día |
| Asistió sin checada | empleado, día | Cuenta como asistencia (sin evaluar retardo) |
| Descanso → laboral | empleado, día | Ese día se planea como trabajo (reposición/cobertura) |
| Laboral → descanso / ausencia justificada | empleado, día(s) | No es falta; se mapea al tipo de RH elegido (falta justificada, vacaciones, incapacidad, permiso, descanso) |

## 7. Glosario

| Término | Significado |
|---|---|
| SR | SoftRestaurant, el punto de venta |
| Checada | Registro de entrada de un empleado en SR |
| Incidencia | Retardo, falta, vacaciones, incapacidad, permiso o descanso capturado en RH |
| Descanso doble | Semana en que el empleado descansa su día fijo + el día extra |
| Cheque / ticket | Una cuenta en SR (`cheques`); sus renglones están en `cheqdet` |
