# Asistencia — mejoras de uso: diseño

> Estado: **aprobado en conversación** (2026-10-03), pendiente de revisión del documento.
> Mejora la Etapa 1 ([`2026-09-29-etapa-1-asistencia-design.md`](2026-09-29-etapa-1-asistencia-design.md))
> con lo que el gerente notó usándola. Va antes de los planes de la Etapa 3. Cierra el
> pendiente de `plan.md` §5 Etapa 1: «`DayOut` no indica si un día viene de una excepción».

## 1. Objetivo y criterios de éxito

El gerente revisa incidencias de rangos largos (un mes o más) y corrige días desde el
calendario. Hoy (a) la lista de incidencias trae todo el rango sin filtros ni páginas,
(b) no hay calendario mensual y (c) un día «Justificado» por una excepción no se puede
corregir desde su panel: solo aparece un formulario vacío para crear otra excepción, que
el API rechaza por choque de fechas.

**Aceptación**
1. Al abrir un día cuya situación viene de una excepción (ausencia justificada, asistió
   sin checada, descanso → laboral, falta registrada a mano), el panel muestra esa
   excepción con sus datos y permite editar fechas, tipo en RH (solo ausencias) y
   comentario, o eliminarla. «Agregar excepción» no aparece en ese día.
2. En Incidencias, filtrar por empleado, tipo y estado reduce **las dos** tablas
   (RH y todas las incidencias); cada tabla pagina desde el API; los filtros y la página
   viven en la URL.
3. La pestaña Calendario muestra la semana por defecto y cambia a mes; un clic en
   cualquier día del mes abre el mismo panel que en la semana.
4. La pestaña Resumen muestra los totales mensuales que hoy están en «Mes».
5. Los enlaces existentes `/semana?...` y `/mes?...` (incluidos los de Revisión) siguen
   llevando al mismo lugar.
6. CI en verde; cobertura del backend ≥ 80% y de `domain/` ≥ 95%; E2E de los flujos
   nuevos sobre la demo.

## 2. Decisiones de diseño

| # | Decisión | Motivo |
|---|---|---|
| M1 | **Cada día trae su excepción** (`exception` en `DayOut`), calculada en `domain/planning.py`. | El API ya garantiza a lo sumo una excepción por empleado y día (409 por choque), así que basta un campo; el panel no necesita otra consulta. |
| M2 | **El tipo de excepción no se edita**; para cambiarlo se elimina y se crea otra. | `PATCH /exceptions/{id}` no acepta `kind` y cada tipo tiene reglas distintas. |
| M3 | **Paginación y filtros en el API**, no en el navegador. | Decisión del gerente: la información crecerá y el navegador no debe cargarlo todo. |
| M4 | **Dos endpoints paginados** (`/attendance/incidents` y `/attendance/rh-rows`) con los mismos filtros. | Cada tabla pagina por separado; un solo endpoint con dos paginaciones sería confuso. |
| M5 | **Las filas de RH salen de los días ya filtrados.** | Filtrar a un empleado debe reducir toda la página, no solo una tabla. |
| M6 | **El cálculo contra SR no cambia**: cada petición sigue derivando el rango completo (≤ 93 días, < 200 ms con 7 empleados). La paginación reduce la respuesta y el trabajo del navegador. | La asistencia es derivada, no se guarda; guardarla es otro diseño. |
| M7 | **Calendario = cuadrícula; Resumen = totales.** La vista mensual no repite la tabla de totales. | Decisión del gerente: corregir días y leer números son tareas distintas. |
| M8 | **Las rutas viejas redirigen** (`/semana` → `/calendario?vista=semana`, `/mes` → `/resumen`). | Marcadores y enlaces ya compartidos siguen funcionando. |
| M9 | **Exportar a Excel no cambia** (rango completo, sin filtros). | Fuera de alcance. |

## 3. Backend

### 3.1 Excepción por día (M1)

- `domain/types.py`: `PlannedDay` y `DayResult` ganan `exception: ScheduleException | None = None`.
- `domain/planning.py` `_plan_day`: la excepción del empleado que cubre el día viaja en
  `PlannedDay.exception` en todos los casos (ausencia, falta a mano, descanso → laboral,
  asistió sin checada). Los cierres del local **no** se asignan: se administran en
  Configuración y el día ya muestra `CLOSED`.
- `domain/compare.py` copia `exception` de `PlannedDay` a `DayResult`.
- API: `DayOut.exception: ExceptionRef | None` con `id, kind, date_from, date_to,
  rh_type, comment`. Aplica a `/attendance/calendar` y `/attendance/incidents`.

### 3.2 Filtros y paginación (M3–M5)

Función pura nueva en `domain/incident_filter.py`:

```python
@dataclass(frozen=True)
class IncidentFilter:
    employee_id: int | None = None
    outcomes: frozenset[Outcome] = INCIDENT_OUTCOMES   # LATE, ABSENT, UNREGISTERED_CHANGE, JUSTIFIED
    status: IncidentStatus = IncidentStatus.ALL        # ALL | JUSTIFIED | UNJUSTIFIED

def filter_incidents(results: Sequence[DayResult], f: IncidentFilter) -> list[DayResult]: ...
def paginate[T](items: Sequence[T], page: int, limit: int) -> Page[T]: ...  # Page: items, total, page, limit
```

- Un día está **justificado** si `justification_id` no es nulo o su resultado es
  `JUSTIFIED`; los demás (incluido `UNREGISTERED_CHANGE`) están **sin justificar**.
- `INCIDENT_OUTCOMES` sale de `api/routes/attendance.py` al dominio.
- Una página fuera de rango devuelve `items` vacío con el `total` real (no es error).

Endpoints (`api/routes/attendance.py`), mismos parámetros en ambos:

| Parámetro | Valor |
|---|---|
| `from`, `to` | obligatorios; mismas reglas de rango que hoy |
| `employee_id` | opcional |
| `type` | repetible: `LATE`, `ABSENT`, `UNREGISTERED_CHANGE`, `JUSTIFIED`; vacío = todos |
| `status` | `all` (default), `justified`, `unjustified` |
| `page` | ≥ 1, default 1 |
| `limit` | 1–100, default 25 |

- `GET /attendance/incidents` → `data: {start, end, items: DayOut[], unresolved: int,
  warnings: WarningOut[]}`, `meta: {total, page, limit}`. `unresolved` cuenta los
  `UNREGISTERED_CHANGE` del rango con el filtro de empleado, sin los de tipo y estado,
  para el aviso de pendientes.
- `GET /attendance/rh-rows` (nuevo) → `data: {start, end, items: RhRowOut[]}`,
  `meta: {total, page, limit}`. Aplica `filter_incidents` y luego `to_rh_rows`; orden
  actual (nombre, día).
- Orden de incidencias: el actual (empleado, día).
- `IncidentsOut.rh_rows` desaparece; el frontend es el único consumidor.

## 4. Frontend

### 4.1 Panel del día (M1, M2)

- `components/attendance/exception-edit.tsx` (nuevo), con el mismo patrón que
  `justification-edit.tsx`: muestra tipo (solo lectura), «Aplica del X al Y» si abarca
  más de un día, y un formulario con fechas, tipo en RH (solo `WORK_TO_ABSENCE`) y
  comentario; botones «Guardar cambios» y «Eliminar excepción» (`ConfirmDeleteButton`).
- Hooks nuevos `useUpdateException` en `lib/api/attendance.ts`; `useDeleteException` se
  mueve ahí desde `config.ts` e invalida asistencia y excepciones.
- `day-panel.tsx`: si `day.exception` existe, muestra `ExceptionEdit` y oculta
  `ExceptionForm` y `RestSwapForm`. El comentario suelto deja de mostrarse cuando lo
  muestra la sección de excepción.
- Celda de la cuadrícula: marca «Excepción» cuando `day.exception` existe y no es
  ausencia justificada (que ya se ve como «Justificado»).
- Configuración → Excepciones gana un botón «Editar» que abre el mismo formulario en
  un diálogo.

### 4.2 Incidencias (M3–M5)

- URL: `/incidencias?desde&hasta&empleado&tipo=LATE,ABSENT&estado&pag&pag_rh`.
- `lib/incident-query.ts` (puro, con pruebas): lee y escribe esos parámetros y los
  valida (valores desconocidos se ignoran).
- Barra de filtros: rango, empleado (select), tipo (casillas), estado (select), botón
  «Limpiar filtros». Cambiar un filtro regresa ambas tablas a la página 1.
- `components/pagination.tsx`: «1–25 de 65» con Anterior/Siguiente.
- Hooks `useIncidents(query)` y `useRhRows(query)` con `placeholderData:
  keepPreviousData` para que la tabla no parpadee al cambiar de página.
- «Pendientes de resolver» se reemplaza por un aviso «N cambios sin registrar · Ver»
  (de `unresolved`) que aplica `tipo=UNREGISTERED_CHANGE`.
- Las filas `JUSTIFIED` muestran «Editar» y abren el panel del día.

### 4.3 Calendario y Resumen (M7, M8)

- Navegación: Calendario · Incidencias · Revisión · Resumen · Configuración.
- `/calendario?vista=semana&desde=…[&empleado&dia]` (default) y
  `/calendario?vista=mes&mes=YYYY-MM`; selector Semana | Mes que conserva el periodo
  (semana → mes de su lunes; mes → primera semana del mes).
- Vista mes: `month-grid.tsx`, empleados en filas y un día por columna; celda compacta
  con color, abreviatura (`OUTCOME_SHORT`: A, R, F, C, J, D, X) y hora en `title` y
  `aria-label`; encabezado con número de día y fin de semana sombreado; desplazamiento
  horizontal en pantallas angostas. Mismo `DayPanel`.
- `/resumen?mes=YYYY-MM`: el `MonthView` actual renombrado a `SummaryView`.
- Redirecciones en `page.tsx` de `/semana` y `/mes` conservando parámetros;
  `actionHref` de Revisión, el login (`DEFAULT_AFTER_LOGIN`) y `/` apuntan a la ruta nueva.

## 5. Errores

- Filtros inválidos en el API → 422 con el envelope de validación existente.
- Editar una excepción que choca con otra → 409 «Ya hay una excepción…» mostrado en el
  formulario con `FormError`.
- Si la excepción se eliminó desde otra pestaña → 404 mostrado en el formulario; al
  invalidar, el panel se refresca.

## 6. Pruebas

- **Dominio (TDD):** excepción por día en cada tipo y su ausencia en cierres;
  `filter_incidents` por empleado, tipos, estado y combinaciones; `paginate` (primera,
  última, fuera de rango, vacío).
- **API:** ambos endpoints con demo (`total`, páginas, filtros, `unresolved`, 422 por
  `limit` y `type` inválidos); `DayOut.exception` en calendario.
- **Frontend (Vitest):** `incident-query`, `ExceptionEdit` (muestra datos, guarda,
  elimina, oculta RH si no es ausencia), `DayPanel` con y sin excepción, `MonthGrid`,
  `Pagination`, redirecciones y `actionHref`.
- **E2E (demo):** editar una ausencia justificada desde el calendario; filtrar
  incidencias por empleado y pasar de página; cambiar de semana a mes y abrir un día.

## 7. Fuera de alcance

- Exportar con filtros.
- Guardar la asistencia calculada para no recalcular contra SR (M6).
- Filtros en el calendario (por empleado o área).
