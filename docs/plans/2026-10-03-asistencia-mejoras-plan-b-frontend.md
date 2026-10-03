# Asistencia, mejoras · Plan B — Frontend

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Editar desde el panel del día la excepción que lo afecta; filtrar y paginar
Incidencias desde el API; pestaña Calendario con vista Semana/Mes y pestaña Resumen con
los totales mensuales.

**Architecture:** La lógica nueva va en módulos puros de `lib/` con pruebas
(`incident-query.ts`, `calendar.ts`, `pages.ts`, helpers de `dates.ts` y `labels.ts`). Los
componentes de `components/attendance/` son presentacionales y las páginas de `app/`
leen la URL y orquestan. El estado de filtros y páginas vive en la URL; el navegador solo
llama a `/backend/...`.

**Tech Stack:** Next.js 16 (App Router, Turbopack), React 19, TypeScript, TanStack Query 5,
`openapi-fetch` + `openapi-typescript`, shadcn/ui sobre Radix, Tailwind, Vitest +
Testing Library, Playwright.

**Spec:** [`docs/specs/2026-10-03-asistencia-mejoras-design.md`](../specs/2026-10-03-asistencia-mejoras-design.md)
(§4 es este plan). Requiere el **Plan A** terminado
([`2026-10-03-asistencia-mejoras-plan-a-backend.md`](2026-10-03-asistencia-mejoras-plan-a-backend.md)).

## Global Constraints

- Node ≥ 24.15 (Homebrew `node@24`). Comandos **desde `frontend/`** salvo que se indique.
- Nunca escribir tipos del API a mano: salen de `src/lib/api/schema.d.ts` generado y se
  re-exportan en `src/lib/api/types.ts`.
- shadcn/ui está en **Radix** (`radix-nova`): `npx shadcn add` sí, `shadcn init` nunca.
- Textos de la UI en español; código e identificadores en inglés.
- URLs:
  - `/calendario?vista=semana&desde=YYYY-MM-DD[&empleado=N&dia=YYYY-MM-DD]` (default)
  - `/calendario?vista=mes&mes=YYYY-MM`
  - `/resumen?mes=YYYY-MM`
  - `/incidencias?desde&hasta[&empleado][&tipo=LATE,ABSENT][&estado][&pag][&pag_rh]`
  - `/semana?…` redirige a `/calendario?vista=semana&…`; `/mes?mes=` a `/resumen?mes=`.
- Navegación: Calendario · Incidencias · Revisión · Resumen · Configuración.
- Página por defecto 25 filas; "Copiar para RH" pide páginas de 100 hasta tener todas.
- Excepciones: el tipo no se edita (M2). Tipo en RH solo para `WORK_TO_ABSENCE`.
- Funciones < 50 líneas; archivos < 400 líneas; sin `console.log`.
- Repo público: fixtures sintéticos (`EMPLEADO A`, `APELLIDO UNO`…).
- Commits `<type>: <description>` cerrando con
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; cada `git commit` en su
  propia llamada.
- Compuertas: `npm run lint && npm run typecheck && npm test` (cobertura de `src/lib`
  ≥ 80% en líneas, funciones y ramas). **Cada tarea termina con las tres en verde.**

## Review Focus

1. **Filtro aplicado estando en una página que ya no existe** (p. ej. página 3 y luego
   filtrar a un empleado con 4 incidencias): cambiar filtros regresa ambas tablas a la
   página 1, y si aun así se llega a una página vacía, "Anterior" lleva a la última
   página con datos. → tests en Task 2 y Task 4.
2. **"Copiar para RH" con la tabla paginada:** copia **todas** las filas del filtro, no
   solo la página visible. → test en Task 3 y Task 8.
3. **Enlaces ya guardados a `/semana?desde&empleado&dia`** (de Revisión o marcadores):
   llegan al mismo día con el panel abierto. → tests en Task 9 y E2E en Task 11.
4. **Abrir un día de otra excepción tras editar una** (el formulario conserva valores
   viejos si React reutiliza el componente): el formulario se monta con `key` por
   excepción. → test en Task 6.
5. **Valores basura en la URL** (`tipo=OK,FOO`, `pag=-3`, `mes=2026-13`): se ignoran y
   se usan los defaults, sin error. → tests en Task 2 y Task 9.

---

## Estructura de archivos

```
frontend/src/
  lib/api/schema.d.ts            regenerado
  lib/api/types.ts               + ExceptionRef, ExceptionUpdate, RhRowsOut, IncidentType, IncidentStatus
  lib/api/client.ts              + unwrapPage(), PageMeta, Paged
  lib/api/attendance.ts          useIncidents/useRhRows(query), fetchAllRhRows, useUpdateException,
                                 useDeleteException (movido desde config.ts)
  lib/api/config.ts              − useDeleteException
  lib/incident-query.ts          NUEVO: URL ⇄ IncidentQuery, parámetros del API
  lib/pages.ts                   NUEVO: collectAll() + pageWindow()
  lib/calendar.ts                NUEVO: hrefs de calendario/resumen, redirecciones, parseFocus
  lib/dates.ts                   + isIsoMonth, isWeekend, formatMonth
  lib/labels.ts                  + OUTCOME_SHORT, INCIDENT_TYPES, STATUS_LABELS, incidentAction
  lib/review.ts                  actionHref → /calendario
  lib/auth/session.ts            DEFAULT_AFTER_LOGIN = /calendario
  components/app-shell.tsx       nueva navegación
  components/pagination.tsx      NUEVO
  components/attendance/
    exception-edit.tsx           NUEVO
    day-panel.tsx                usa ExceptionEdit
    week-grid.tsx                marca "Excepción"
    month-grid.tsx               NUEVO
    view-switch.tsx              NUEVO (Semana | Mes)
    week-view.tsx                hrefs nuevos + ViewSwitch
    calendar-month-view.tsx      NUEVO
    summary-view.tsx             renombrado desde month-view.tsx
    incidents-view.tsx           filtros + dos tablas paginadas
    incident-filters.tsx         NUEVO
    incident-table.tsx           NUEVO (sale de incidents-view.tsx)
    rh-table.tsx                 + loadAll opcional
    legend.tsx                   + abreviaturas opcionales
  components/config/exceptions-tab.tsx   + Editar (diálogo)
  app/(app)/calendario/page.tsx  NUEVO
  app/(app)/resumen/page.tsx     NUEVO
  app/(app)/semana/page.tsx      redirección
  app/(app)/mes/page.tsx         redirección
  app/(app)/incidencias/page.tsx parseIncidentQuery
  app/(app)/page.tsx             → /calendario
frontend/e2e/attendance.spec.ts  flujos nuevos
frontend/e2e/review.spec.ts      enlace /calendario
CLAUDE.md, docs/plan.md          estado y layout
```

---

### Task 1: Tipos del API, `unwrapPage` y adaptación mínima de Incidencias

**Files:**
- Modify: `frontend/src/lib/api/schema.d.ts` (regenerado), `frontend/src/lib/api/types.ts`
- Modify: `frontend/src/lib/api/client.ts`, `frontend/src/lib/api/client.test.ts`
- Modify: `frontend/src/lib/api/attendance.ts`, `frontend/src/lib/api/config.ts`
- Modify: `frontend/src/components/attendance/incidents-view.tsx` (solo rutas de datos)
- Modify: `frontend/src/components/config/exceptions-tab.tsx` (import de `useDeleteException`)
- Modify: `frontend/src/components/attendance/week-grid.test.tsx` (fixture)

**Interfaces:**
- Consumes: endpoints del Plan A.
- Produces:
  - `type PageMeta = { total: number; page: number; limit: number }`
  - `type Paged<T> = { data: T; page: PageMeta }`
  - `unwrapPage<T>(request): Promise<Paged<T>>` (lanza `ApiError("BAD_RESPONSE", …)` si falta `meta`)
  - `type IncidentApiParams = { from: string; to: string; employee_id?: number; type?: IncidentType[]; status: IncidentStatus; page: number; limit: number }`
  - `useIncidents(params: IncidentApiParams)`, `useRhRows(params: IncidentApiParams)`:
    `UseQueryResult<Paged<IncidentsOut>>` / `UseQueryResult<Paged<RhRowsOut>>`
  - `useUpdateException()`: `mutate({ id: number; body: ExceptionUpdate })`
  - `useDeleteException()`: `mutate(id: number)` (ahora en `lib/api/attendance.ts`)

- [ ] **Step 1: Regenerar `schema.d.ts` contra el backend de la rama**

El backend real del puerto 8000 todavía corre `main`; levantar el de la rama en 8001
(no abre conexiones a SR ni a Postgres para servir `/openapi.json`):

```bash
cd ../backend && SR_MODE=fake uv run uvicorn --factory tabernas.main:create_app --port 8001 &
sleep 4
cd ../frontend && npx openapi-typescript http://127.0.0.1:8001/openapi.json -o src/lib/api/schema.d.ts
kill %1
```

Expected: `schema.d.ts` contiene `"/attendance/rh-rows"`, `ExceptionRef`, `RhRowsOut`,
`IncidentType`, `IncidentStatus`, y `DayOut` tiene `exception`.

- [ ] **Step 2: Re-exportar los tipos nuevos**

En `frontend/src/lib/api/types.ts`, después de `export type DayOut = …`:

```ts
export type ExceptionRef = Schemas["ExceptionRef"];
export type RhRowsOut = Schemas["RhRowsOut"];
export type IncidentType = Schemas["IncidentType"];
export type IncidentStatus = Schemas["IncidentStatus"];
```

y después de `export type ExceptionCreate = …`:

```ts
export type ExceptionUpdate = Schemas["ExceptionUpdate"];
```

- [ ] **Step 3: Write the failing tests for `unwrapPage`**

Al final de `frontend/src/lib/api/client.test.ts` (agregar `unwrapPage` al import):

```ts
describe("unwrapPage", () => {
  it("returns the data and the page meta", async () => {
    const body = { success: true, data: { items: [1] }, meta: { total: 30, page: 2, limit: 25 } };
    const request = Promise.resolve({ data: body, response: response(200) });
    await expect(unwrapPage(request)).resolves.toEqual({
      data: { items: [1] },
      page: { total: 30, page: 2, limit: 25 },
    });
  });

  it("rejects a successful response without page meta", async () => {
    const body = { success: true, data: { items: [] }, meta: null };
    const request = Promise.resolve({ data: body, response: response(200) });
    await expect(unwrapPage(request)).rejects.toMatchObject({ code: "BAD_RESPONSE" });
  });

  it("throws the backend error like unwrap", async () => {
    const body = { success: false, data: null, error: { code: "VALIDATION_ERROR", message: "x" } };
    const request = Promise.resolve({ error: body, response: response(422) });
    await expect(unwrapPage(request)).rejects.toMatchObject({ code: "VALIDATION_ERROR", status: 422 });
  });
});
```

Run: `npm test -- src/lib/api/client.test.ts`
Expected: FAIL — `unwrapPage` no existe.

- [ ] **Step 4: Implementar `unwrapPage`**

En `frontend/src/lib/api/client.ts`, reemplazar desde `type Enveloped<T>` hasta el final
de `unwrap` por:

```ts
type Enveloped<T> = {
  success: boolean;
  data?: T | null;
  error?: ErrorBody | null;
  meta?: { [key: string]: unknown } | null;
};
type FetchResult<T> = { data?: Enveloped<T>; error?: unknown; response: Response };

export type PageMeta = { total: number; page: number; limit: number };
export type Paged<T> = { data: T; page: PageMeta };

function errorBody(value: unknown): ErrorBody | null {
  if (typeof value !== "object" || value === null || !("error" in value)) return null;
  const error = (value as { error: unknown }).error;
  if (typeof error !== "object" || error === null) return null;
  const { code, message } = error as Partial<ErrorBody>;
  return typeof code === "string" && typeof message === "string" ? { code, message } : null;
}

async function envelope<T>(request: Promise<FetchResult<T>>): Promise<Enveloped<T>> {
  let result: FetchResult<T>;
  try {
    result = await request;
  } catch {
    throw new ApiError("NETWORK_ERROR", "No se pudo conectar con el servidor", 0);
  }
  const { data, error, response } = result;
  if (data?.success) return data;
  const body = errorBody(error ?? data);
  throw new ApiError(
    body?.code ?? "HTTP_ERROR",
    body?.message ?? fallbackMessage(response.status),
    response.status,
  );
}

export async function unwrap<T>(request: Promise<FetchResult<T>>): Promise<T> {
  return ((await envelope(request)).data ?? null) as T;
}

function pageMeta(meta: Enveloped<unknown>["meta"]): PageMeta {
  const { total, page, limit } = meta ?? {};
  if (typeof total !== "number" || typeof page !== "number" || typeof limit !== "number") {
    throw new ApiError("BAD_RESPONSE", "La respuesta no trae la paginación", 200);
  }
  return { total, page, limit };
}

export async function unwrapPage<T>(request: Promise<FetchResult<T>>): Promise<Paged<T>> {
  const body = await envelope(request);
  return { data: body.data as T, page: pageMeta(body.meta) };
}
```

Run: `npm test -- src/lib/api/client.test.ts`
Expected: PASS.

- [ ] **Step 5: Hooks de incidencias y excepciones**

En `frontend/src/lib/api/attendance.ts`:

1. Imports:

```ts
import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";

import { api, unwrap, unwrapPage } from "./client";
import { useInvalidate } from "./invalidate";
import type {
  ExceptionCreate,
  ExceptionUpdate,
  Grouping,
  IncidentStatus,
  IncidentType,
  JustificationCreate,
  JustificationUpdate,
  RestSwapCreate,
} from "./types";

export type IncidentApiParams = {
  from: string;
  to: string;
  employee_id?: number;
  type?: IncidentType[];
  status: IncidentStatus;
  page: number;
  limit: number;
};
```

2. Claves: reemplazar `incidents: …` por

```ts
  incidents: (params: IncidentApiParams) => ["attendance", "incidents", params] as const,
  rhRows: (params: IncidentApiParams) => ["attendance", "rh-rows", params] as const,
```

3. Reemplazar `useIncidents` por:

```ts
export function useIncidents(params: IncidentApiParams) {
  return useQuery({
    queryKey: attendanceKeys.incidents(params),
    queryFn: () => unwrapPage(api.GET("/attendance/incidents", { params: { query: params } })),
    placeholderData: keepPreviousData,
  });
}

export function useRhRows(params: IncidentApiParams) {
  return useQuery({
    queryKey: attendanceKeys.rhRows(params),
    queryFn: () => unwrapPage(api.GET("/attendance/rh-rows", { params: { query: params } })),
    placeholderData: keepPreviousData,
  });
}
```

4. Al final:

```ts
export function useUpdateException() {
  const invalidate = useInvalidate(attendanceKeys.all, ["exceptions"]);
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: ExceptionUpdate }) =>
      unwrap(
        api.PATCH("/exceptions/{exception_id}", {
          params: { path: { exception_id: id } },
          body,
        }),
      ),
    onSuccess: invalidate,
  });
}

export function useDeleteException() {
  const invalidate = useInvalidate(attendanceKeys.all, ["exceptions"]);
  return useMutation({
    mutationFn: (id: number) =>
      unwrap(
        api.DELETE("/exceptions/{exception_id}", { params: { path: { exception_id: id } } }),
      ),
    onSuccess: invalidate,
  });
}
```

5. En `frontend/src/lib/api/config.ts`, borrar `useDeleteException`; en
`frontend/src/components/config/exceptions-tab.tsx` importar `useDeleteException` desde
`@/lib/api/attendance` (junto a `useCreateException`) y quitarlo del import de config.

- [ ] **Step 6: Adaptar Incidencias al nuevo contrato (sin UI nueva todavía)**

En `frontend/src/components/attendance/incidents-view.tsx`, dentro de `Incidents`:

```tsx
  const params = { from, to, status: "all" as const, page: 1, limit: 100 };
  const incidents = useIncidents(params);
  const rhRows = useRhRows(params);
```

y cambiar los usos: `incidents.data.warnings` → `incidents.data.data.warnings`,
`incidents.data.incidents` → `incidents.data.data.items` (dos lugares, incluido
`unresolved`), y la tabla de RH:

```tsx
          <section className="space-y-2">
            <h2 className="text-lg font-semibold">Para capturar en RH</h2>
            {rhRows.isError && <QueryError error={rhRows.error} onRetry={() => rhRows.refetch()} />}
            {rhRows.data && <RhTable rows={rhRows.data.data.items} />}
          </section>
```

Importar `useRhRows` junto a `useIncidents`. (La Task 8 reemplaza esta vista completa.)

- [ ] **Step 7: Fixture de `DayOut`**

En `frontend/src/components/attendance/week-grid.test.tsx`, en `day()`, agregar
`exception: null,` después de `comment: "",`.

- [ ] **Step 8: Compuertas**

Run: `npm run lint && npm run typecheck && npm test`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add src/lib/api src/components/attendance/incidents-view.tsx src/components/attendance/week-grid.test.tsx src/components/config/exceptions-tab.tsx
git commit -m "feat: consume paginated incident endpoints and exception updates

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: `lib/incident-query.ts` (URL ⇄ consulta)

**Files:**
- Create: `frontend/src/lib/incident-query.ts`, `frontend/src/lib/incident-query.test.ts`
- Modify: `frontend/src/lib/labels.ts`, `frontend/src/lib/labels.test.ts`

**Interfaces:**
- Consumes: `IncidentType`, `IncidentStatus`, `IncidentApiParams` (Task 1); `isIsoDate`.
- Produces:
  - `INCIDENT_TYPES: IncidentType[]` y `STATUS_LABELS: Record<IncidentStatus, string>` en `lib/labels.ts`
  - `type IncidentQuery = { from: string; to: string; employeeId: number | null; types: IncidentType[]; status: IncidentStatus; page: number; rhPage: number }`
  - `type UrlParams = Record<string, string | string[] | undefined>`
  - `parseIncidentQuery(params: UrlParams): IncidentQuery | null` (null si falta/inválido el rango)
  - `incidentQueryString(query: IncidentQuery): string` (omite defaults)
  - `withFilters(query, changes: Partial<Pick<IncidentQuery, "from" | "to" | "employeeId" | "types" | "status">>): IncidentQuery` (páginas a 1)
  - `toApiParams(query: IncidentQuery, page: number, limit?: number): IncidentApiParams`
  - `PAGE_SIZE = 25`, `COPY_PAGE_SIZE = 100`

- [ ] **Step 1: Write the failing tests**

`frontend/src/lib/incident-query.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import {
  incidentQueryString,
  parseIncidentQuery,
  toApiParams,
  withFilters,
  type IncidentQuery,
} from "./incident-query";

const BASE: IncidentQuery = {
  from: "2026-09-01",
  to: "2026-09-30",
  employeeId: null,
  types: [],
  status: "all",
  page: 1,
  rhPage: 1,
};

describe("parseIncidentQuery", () => {
  it("needs a valid range", () => {
    expect(parseIncidentQuery({})).toBeNull();
    expect(parseIncidentQuery({ desde: "2026-09-01", hasta: "nope" })).toBeNull();
  });

  it("reads every filter and page", () => {
    const query = parseIncidentQuery({
      desde: "2026-09-01",
      hasta: "2026-09-30",
      empleado: "7",
      tipo: "LATE,ABSENT",
      estado: "unjustified",
      pag: "3",
      pag_rh: "2",
    });
    expect(query).toEqual({
      ...BASE,
      employeeId: 7,
      types: ["LATE", "ABSENT"],
      status: "unjustified",
      page: 3,
      rhPage: 2,
    });
  });

  it("ignores garbage and falls back to defaults", () => {
    const query = parseIncidentQuery({
      desde: "2026-09-01",
      hasta: "2026-09-30",
      empleado: "abc",
      tipo: "OK,FOO,LATE,LATE",
      estado: "toString",
      pag: "-3",
      pag_rh: "1.5",
    });
    expect(query).toEqual({ ...BASE, types: ["LATE"] });
  });

  it("uses the first value of repeated params", () => {
    const query = parseIncidentQuery({ desde: ["2026-09-01", "x"], hasta: "2026-09-30" });
    expect(query?.from).toBe("2026-09-01");
  });
});

describe("incidentQueryString", () => {
  it("omits defaults", () => {
    expect(incidentQueryString(BASE)).toBe("desde=2026-09-01&hasta=2026-09-30");
  });

  it("round-trips through parse", () => {
    const query = { ...BASE, employeeId: 7, types: ["LATE" as const], status: "justified" as const, page: 2, rhPage: 3 };
    const params = Object.fromEntries(new URLSearchParams(incidentQueryString(query)));
    expect(parseIncidentQuery(params)).toEqual(query);
  });
});

describe("withFilters", () => {
  it("resets both pages to 1", () => {
    const query = withFilters({ ...BASE, page: 4, rhPage: 2 }, { employeeId: 3 });
    expect(query).toEqual({ ...BASE, employeeId: 3 });
  });
});

describe("toApiParams", () => {
  it("only sends the filters that are set", () => {
    expect(toApiParams(BASE, 2)).toEqual({
      from: "2026-09-01",
      to: "2026-09-30",
      status: "all",
      page: 2,
      limit: 25,
    });
    expect(toApiParams({ ...BASE, employeeId: 7, types: ["ABSENT"] }, 1, 100)).toEqual({
      from: "2026-09-01",
      to: "2026-09-30",
      employee_id: 7,
      type: ["ABSENT"],
      status: "all",
      page: 1,
      limit: 100,
    });
  });
});
```

Al final de `frontend/src/lib/labels.test.ts` (agregar `INCIDENT_TYPES`, `STATUS_LABELS`
al import):

```ts
describe("incident filter labels", () => {
  it("lists the four incident types in display order", () => {
    expect(INCIDENT_TYPES).toEqual(["LATE", "ABSENT", "UNREGISTERED_CHANGE", "JUSTIFIED"]);
  });

  it("labels every status", () => {
    expect(STATUS_LABELS).toEqual({
      all: "Todas",
      justified: "Justificadas",
      unjustified: "Sin justificar",
    });
  });
});
```

Run: `npm test -- src/lib/incident-query.test.ts src/lib/labels.test.ts`
Expected: FAIL — módulo y exports inexistentes.

- [ ] **Step 2: Labels**

En `frontend/src/lib/labels.ts` (agregar `IncidentStatus`, `IncidentType` al import de tipos):

```ts
export const INCIDENT_TYPES: IncidentType[] = ["LATE", "ABSENT", "UNREGISTERED_CHANGE", "JUSTIFIED"];

export const STATUS_LABELS: Record<IncidentStatus, string> = {
  all: "Todas",
  justified: "Justificadas",
  unjustified: "Sin justificar",
};
```

- [ ] **Step 3: Implementar el módulo**

`frontend/src/lib/incident-query.ts`:

```ts
import type { IncidentApiParams } from "@/lib/api/attendance";
import type { IncidentStatus, IncidentType } from "@/lib/api/types";

import { isIsoDate } from "./dates";
import { INCIDENT_TYPES, STATUS_LABELS } from "./labels";

export const PAGE_SIZE = 25;
export const COPY_PAGE_SIZE = 100;

export type IncidentQuery = {
  from: string;
  to: string;
  employeeId: number | null;
  types: IncidentType[];
  status: IncidentStatus;
  page: number;
  rhPage: number;
};

export type UrlParams = Record<string, string | string[] | undefined>;
type FilterChanges = Partial<Pick<IncidentQuery, "from" | "to" | "employeeId" | "types" | "status">>;

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function positiveInt(value: string | undefined): number | null {
  if (value === undefined || !/^\d+$/.test(value)) return null;
  const parsed = Number(value);
  return parsed >= 1 ? parsed : null;
}

function parseTypes(value: string | undefined): IncidentType[] {
  const wanted = new Set((value ?? "").split(","));
  return INCIDENT_TYPES.filter((type) => wanted.has(type));
}

function parseStatus(value: string | undefined): IncidentStatus {
  return value !== undefined && Object.hasOwn(STATUS_LABELS, value) ? (value as IncidentStatus) : "all";
}

export function parseIncidentQuery(params: UrlParams): IncidentQuery | null {
  const from = first(params.desde);
  const to = first(params.hasta);
  if (!isIsoDate(from) || !isIsoDate(to)) return null;
  return {
    from,
    to,
    employeeId: positiveInt(first(params.empleado)),
    types: parseTypes(first(params.tipo)),
    status: parseStatus(first(params.estado)),
    page: positiveInt(first(params.pag)) ?? 1,
    rhPage: positiveInt(first(params.pag_rh)) ?? 1,
  };
}

export function incidentQueryString(query: IncidentQuery): string {
  const params = new URLSearchParams({ desde: query.from, hasta: query.to });
  if (query.employeeId !== null) params.set("empleado", String(query.employeeId));
  if (query.types.length > 0) params.set("tipo", query.types.join(","));
  if (query.status !== "all") params.set("estado", query.status);
  if (query.page > 1) params.set("pag", String(query.page));
  if (query.rhPage > 1) params.set("pag_rh", String(query.rhPage));
  return params.toString().replaceAll("%2C", ",");
}

export function withFilters(query: IncidentQuery, changes: FilterChanges): IncidentQuery {
  return { ...query, ...changes, page: 1, rhPage: 1 };
}

export function toApiParams(
  query: IncidentQuery,
  page: number,
  limit: number = PAGE_SIZE,
): IncidentApiParams {
  return {
    from: query.from,
    to: query.to,
    ...(query.employeeId !== null && { employee_id: query.employeeId }),
    ...(query.types.length > 0 && { type: query.types }),
    status: query.status,
    page,
    limit,
  };
}
```

`IncidentApiParams` vive en `lib/api/attendance.ts`, que es un módulo con hooks: el import
es solo de tipo (`import type`), así que no arrastra React a las pruebas.

- [ ] **Step 4: Run tests**

Run: `npm test -- src/lib/incident-query.test.ts src/lib/labels.test.ts`
Expected: PASS.

- [ ] **Step 5: Compuertas y commit**

Run: `npm run lint && npm run typecheck && npm test`

```bash
git add src/lib/incident-query.ts src/lib/incident-query.test.ts src/lib/labels.ts src/lib/labels.test.ts
git commit -m "feat: parse and serialize incident filters in the URL

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `lib/pages.ts` (todas las páginas y ventana de página)

**Files:**
- Create: `frontend/src/lib/pages.ts`, `frontend/src/lib/pages.test.ts`
- Modify: `frontend/src/lib/api/attendance.ts` (`fetchAllRhRows`)

**Interfaces:**
- Consumes: `PageMeta` (Task 1), `toApiParams`, `COPY_PAGE_SIZE`, `IncidentQuery` (Task 2).
- Produces:
  - `collectAll<T>(fetchPage: (page: number) => Promise<{ items: T[]; total: number }>, maxPages?: number): Promise<T[]>`
  - `type PageWindow = { first: number; last: number; lastPage: number; beyond: boolean }`
  - `pageWindow(meta: PageMeta): PageWindow`
  - `fetchAllRhRows(query: IncidentQuery): Promise<RhRowOut[]>`

- [ ] **Step 1: Write the failing tests**

`frontend/src/lib/pages.test.ts`:

```ts
import { describe, expect, it, vi } from "vitest";

import { collectAll, pageWindow } from "./pages";

describe("collectAll", () => {
  it("requests pages until it has the total", async () => {
    const data = [1, 2, 3, 4, 5];
    const fetchPage = vi.fn(async (page: number) => ({
      items: data.slice((page - 1) * 2, page * 2),
      total: data.length,
    }));
    await expect(collectAll(fetchPage)).resolves.toEqual(data);
    expect(fetchPage).toHaveBeenCalledTimes(3);
  });

  it("stops on an empty page even if the total says otherwise", async () => {
    const fetchPage = vi.fn(async (page: number) => ({ items: page === 1 ? [1] : [], total: 9 }));
    await expect(collectAll(fetchPage)).resolves.toEqual([1]);
    expect(fetchPage).toHaveBeenCalledTimes(2);
  });

  it("never loops forever", async () => {
    const fetchPage = vi.fn(async () => ({ items: [0], total: 1_000_000 }));
    await expect(collectAll(fetchPage, 3)).resolves.toHaveLength(3);
  });
});

describe("pageWindow", () => {
  it("describes a middle page", () => {
    expect(pageWindow({ total: 65, page: 2, limit: 25 })).toEqual({
      first: 26,
      last: 50,
      lastPage: 3,
      beyond: false,
    });
  });

  it("handles an empty result", () => {
    expect(pageWindow({ total: 0, page: 1, limit: 25 })).toEqual({
      first: 0,
      last: 0,
      lastPage: 1,
      beyond: false,
    });
  });

  it("flags a page past the end", () => {
    expect(pageWindow({ total: 4, page: 3, limit: 25 })).toEqual({
      first: 0,
      last: 0,
      lastPage: 1,
      beyond: true,
    });
  });
});
```

Run: `npm test -- src/lib/pages.test.ts`
Expected: FAIL — módulo inexistente.

- [ ] **Step 2: Implementar**

`frontend/src/lib/pages.ts`:

```ts
import type { PageMeta } from "@/lib/api/client";

const MAX_PAGES = 50;

type PageResult<T> = { items: T[]; total: number };

/** Fetches page 1, 2, … until every item is in, an empty page arrives, or maxPages. */
export async function collectAll<T>(
  fetchPage: (page: number) => Promise<PageResult<T>>,
  maxPages: number = MAX_PAGES,
): Promise<T[]> {
  const collected: T[] = [];
  for (let page = 1; page <= maxPages; page += 1) {
    const { items, total } = await fetchPage(page);
    collected.push(...items);
    if (items.length === 0 || collected.length >= total) break;
  }
  return collected;
}

export type PageWindow = { first: number; last: number; lastPage: number; beyond: boolean };

export function pageWindow({ total, page, limit }: PageMeta): PageWindow {
  const lastPage = Math.max(1, Math.ceil(total / limit));
  const beyond = page > lastPage;
  if (total === 0 || beyond) return { first: 0, last: 0, lastPage, beyond };
  return { first: (page - 1) * limit + 1, last: Math.min(page * limit, total), lastPage, beyond };
}
```

(`collected` es un arreglo local que se arma en la función; no hay estado compartido.)

- [ ] **Step 3: `fetchAllRhRows`**

Al final de `frontend/src/lib/api/attendance.ts`:

```ts
export function fetchAllRhRows(query: IncidentQuery): Promise<RhRowOut[]> {
  return collectAll(async (page) => {
    const params = toApiParams(query, page, COPY_PAGE_SIZE);
    const result = await unwrapPage(api.GET("/attendance/rh-rows", { params: { query: params } }));
    return { items: result.data.items, total: result.page.total };
  });
}
```

con imports `import { COPY_PAGE_SIZE, type IncidentQuery, toApiParams } from "@/lib/incident-query";`,
`import { collectAll } from "@/lib/pages";` y `RhRowOut` en el import de `./types`.

- [ ] **Step 4: Run tests y compuertas**

Run: `npm test -- src/lib/pages.test.ts && npm run lint && npm run typecheck && npm test`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/lib/pages.ts src/lib/pages.test.ts src/lib/api/attendance.ts
git commit -m "feat: collect every RH row page and describe page windows

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Componente `Pagination`

**Files:**
- Create: `frontend/src/components/pagination.tsx`, `frontend/src/components/pagination.test.tsx`

**Interfaces:**
- Consumes: `PageMeta` (Task 1), `pageWindow` (Task 3).
- Produces: `<Pagination meta={PageMeta} label={string} onPage={(page: number) => void} />`;
  no renderiza nada si todo cabe en una página y estamos en la 1.

- [ ] **Step 1: Write the failing test**

`frontend/src/components/pagination.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Pagination } from "./pagination";

describe("Pagination", () => {
  it("shows the visible range and moves between pages", async () => {
    const onPage = vi.fn();
    render(<Pagination meta={{ total: 65, page: 2, limit: 25 }} label="Incidencias" onPage={onPage} />);
    expect(screen.getByRole("navigation", { name: "Incidencias" })).toHaveTextContent("26–50 de 65");
    await userEvent.click(screen.getByRole("button", { name: "← Anterior" }));
    await userEvent.click(screen.getByRole("button", { name: "Siguiente →" }));
    expect(onPage.mock.calls).toEqual([[1], [3]]);
  });

  it("disables the ends", () => {
    render(<Pagination meta={{ total: 30, page: 1, limit: 25 }} label="RH" onPage={() => undefined} />);
    expect(screen.getByRole("button", { name: "← Anterior" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Siguiente →" })).toBeEnabled();
  });

  it("renders nothing when everything fits", () => {
    const { container } = render(
      <Pagination meta={{ total: 3, page: 1, limit: 25 }} label="RH" onPage={() => undefined} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("sends a page past the end back to the last page", async () => {
    const onPage = vi.fn();
    render(<Pagination meta={{ total: 30, page: 5, limit: 25 }} label="RH" onPage={onPage} />);
    expect(screen.getByRole("navigation", { name: "RH" })).toHaveTextContent("Sin resultados en esta página");
    await userEvent.click(screen.getByRole("button", { name: "← Anterior" }));
    expect(onPage).toHaveBeenCalledWith(2);
  });
});
```

Run: `npm test -- src/components/pagination.test.tsx`
Expected: FAIL — módulo inexistente.

- [ ] **Step 2: Implementar**

`frontend/src/components/pagination.tsx`:

```tsx
import { Button } from "@/components/ui/button";
import type { PageMeta } from "@/lib/api/client";
import { pageWindow } from "@/lib/pages";

type Props = { meta: PageMeta; label: string; onPage: (page: number) => void };

export function Pagination({ meta, label, onPage }: Props) {
  const { first, last, lastPage, beyond } = pageWindow(meta);
  if (meta.page === 1 && lastPage === 1) return null;
  const summary = beyond ? "Sin resultados en esta página" : `${first}–${last} de ${meta.total}`;
  return (
    <nav aria-label={label} className="flex items-center justify-end gap-2 text-sm">
      <span className="text-muted-foreground">{summary}</span>
      <Button
        size="sm"
        variant="outline"
        disabled={meta.page <= 1}
        onClick={() => onPage(beyond ? lastPage : meta.page - 1)}
      >
        ← Anterior
      </Button>
      <Button
        size="sm"
        variant="outline"
        disabled={meta.page >= lastPage}
        onClick={() => onPage(meta.page + 1)}
      >
        Siguiente →
      </Button>
    </nav>
  );
}
```

- [ ] **Step 3: Run tests y compuertas**

Run: `npm test -- src/components/pagination.test.tsx && npm run lint && npm run typecheck && npm test`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/components/pagination.tsx src/components/pagination.test.tsx
git commit -m "feat: add pagination control

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Componente `ExceptionEdit`

**Files:**
- Create: `frontend/src/components/attendance/exception-edit.tsx`,
  `frontend/src/components/attendance/exception-edit.test.tsx`

**Interfaces:**
- Consumes: `useUpdateException`, `useDeleteException` (Task 1); `ExceptionRef`;
  `ABSENCE_RH_TYPES`, `EXCEPTION_KIND_LABELS`, `RH_LABELS`; `formatDate`.
- Produces: `<ExceptionEdit exception={ExceptionRef} onDone={() => void} />`. Acepta
  también un `ExceptionOut` (tiene los mismos campos y además `employee_id`).

- [ ] **Step 1: Write the failing test**

`frontend/src/components/attendance/exception-edit.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ExceptionRef } from "@/lib/api/types";

import { ExceptionEdit } from "./exception-edit";

const update = vi.fn();
const remove = vi.fn();

vi.mock("@/lib/api/attendance", () => ({
  useUpdateException: () => ({ mutate: update, error: null, isPending: false }),
  useDeleteException: () => ({ mutate: remove, error: null, isPending: false }),
}));

const VACATION: ExceptionRef = {
  id: 12,
  kind: "WORK_TO_ABSENCE",
  date_from: "2026-09-30",
  date_to: "2026-10-02",
  rh_type: "VACACIONES",
  comment: "Enfermedad.",
};

describe("ExceptionEdit", () => {
  beforeEach(() => {
    update.mockReset();
    remove.mockReset();
  });

  it("shows the existing exception filled in", () => {
    render(<ExceptionEdit exception={VACATION} onDone={() => undefined} />);
    expect(screen.getByRole("heading", { name: "Excepción · Ausencia justificada" })).toBeInTheDocument();
    expect(screen.getByText(/Aplica del 30\/09\/2026 al 02\/10\/2026/)).toBeInTheDocument();
    expect(screen.getByLabelText("Tipo en RH")).toHaveValue("VACACIONES");
    expect(screen.getByLabelText("Comentario")).toHaveValue("Enfermedad.");
    expect(screen.getByLabelText("Desde")).toHaveValue("2026-09-30");
    expect(screen.getByLabelText("Hasta")).toHaveValue("2026-10-02");
  });

  it("saves the edited fields", async () => {
    render(<ExceptionEdit exception={VACATION} onDone={() => undefined} />);
    await userEvent.selectOptions(screen.getByLabelText("Tipo en RH"), "INCAPACIDAD");
    await userEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));
    expect(update).toHaveBeenCalledWith(
      {
        id: 12,
        body: {
          date_from: "2026-09-30",
          date_to: "2026-10-02",
          comment: "Enfermedad.",
          rh_type: "INCAPACIDAD",
        },
      },
      expect.anything(),
    );
  });

  it("does not offer an RH type for non-absence exceptions", async () => {
    const present = { ...VACATION, kind: "PRESENT_NO_CHECKIN" as const, rh_type: null, date_to: "2026-09-30" };
    render(<ExceptionEdit exception={present} onDone={() => undefined} />);
    expect(screen.queryByLabelText("Tipo en RH")).not.toBeInTheDocument();
    expect(screen.queryByText(/Aplica del/)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));
    expect(update.mock.calls[0][0].body).not.toHaveProperty("rh_type");
  });

  it("deletes after confirming", async () => {
    render(<ExceptionEdit exception={VACATION} onDone={() => undefined} />);
    await userEvent.click(screen.getByRole("button", { name: "Eliminar excepción" }));
    await userEvent.click(screen.getByRole("button", { name: /Confirmar/ }));
    expect(remove).toHaveBeenCalledWith(12, expect.anything());
  });
});
```

Run: `npm test -- src/components/attendance/exception-edit.test.tsx`
Expected: FAIL — módulo inexistente.

- [ ] **Step 2: Implementar**

`frontend/src/components/attendance/exception-edit.tsx`:

```tsx
"use client";

import type { FormEvent } from "react";
import { toast } from "sonner";

import { ConfirmDeleteButton } from "@/components/confirm-delete-button";
import { FormError } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { useDeleteException, useUpdateException } from "@/lib/api/attendance";
import type { ExceptionRef, ExceptionUpdate, RhType } from "@/lib/api/types";
import { formatDate } from "@/lib/dates";
import { ABSENCE_RH_TYPES, EXCEPTION_KIND_LABELS, RH_LABELS } from "@/lib/labels";

type Props = { exception: ExceptionRef; onDone: () => void };

function bodyFrom(form: FormData, isAbsence: boolean): ExceptionUpdate {
  return {
    date_from: String(form.get("date_from")),
    date_to: String(form.get("date_to")),
    comment: String(form.get("comment") ?? "").trim(),
    ...(isAbsence && { rh_type: String(form.get("rh_type")) as RhType }),
  };
}

export function ExceptionEdit({ exception, onDone }: Props) {
  const update = useUpdateException();
  const remove = useDeleteException();
  const isAbsence = exception.kind === "WORK_TO_ABSENCE";

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const body = bodyFrom(new FormData(event.currentTarget), isAbsence);
    update.mutate(
      { id: exception.id, body },
      {
        onSuccess: () => {
          toast.success("Excepción actualizada");
          onDone();
        },
      },
    );
  }

  function onDelete() {
    remove.mutate(exception.id, {
      onSuccess: () => {
        toast.success("Excepción eliminada");
        onDone();
      },
    });
  }

  return (
    <section className="space-y-3">
      <h3 className="font-medium">Excepción · {EXCEPTION_KIND_LABELS[exception.kind]}</h3>
      {exception.date_from !== exception.date_to && (
        <p className="text-sm text-muted-foreground">
          Aplica del {formatDate(exception.date_from)} al {formatDate(exception.date_to)}; los
          cambios afectan todo el rango.
        </p>
      )}
      <form onSubmit={onSubmit} className="space-y-3">
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <Label htmlFor="exception_edit_from">Desde</Label>
            <Input id="exception_edit_from" name="date_from" type="date" defaultValue={exception.date_from} required />
          </div>
          <div className="space-y-1">
            <Label htmlFor="exception_edit_to">Hasta</Label>
            <Input id="exception_edit_to" name="date_to" type="date" defaultValue={exception.date_to} required />
          </div>
        </div>
        {isAbsence && (
          <div className="space-y-1">
            <Label htmlFor="exception_edit_rh_type">Tipo en RH</Label>
            <NativeSelect
              id="exception_edit_rh_type"
              name="rh_type"
              defaultValue={exception.rh_type ?? ABSENCE_RH_TYPES[0]}
            >
              {ABSENCE_RH_TYPES.map((option) => (
                <option key={option} value={option}>
                  {RH_LABELS[option]}
                </option>
              ))}
            </NativeSelect>
          </div>
        )}
        <div className="space-y-1">
          <Label htmlFor="exception_edit_comment">Comentario</Label>
          <Input id="exception_edit_comment" name="comment" maxLength={500} defaultValue={exception.comment} />
        </div>
        <FormError error={update.error} />
        <Button type="submit" disabled={update.isPending}>
          Guardar cambios
        </Button>
      </form>
      <FormError error={remove.error} />
      <ConfirmDeleteButton label="Eliminar excepción" pending={remove.isPending} onConfirm={onDelete} />
    </section>
  );
}
```

- [ ] **Step 3: Run tests y compuertas**

Run: `npm test -- src/components/attendance/exception-edit.test.tsx && npm run lint && npm run typecheck && npm test`
Expected: PASS. Si `formatDate` no produce `30/09/2026`, ajustar el test a su formato
real (ver `src/lib/dates.test.ts`), no la función.

- [ ] **Step 4: Commit**

```bash
git add src/components/attendance/exception-edit.tsx src/components/attendance/exception-edit.test.tsx
git commit -m "feat: add exception edit form

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Panel del día y celda con excepción

**Files:**
- Modify: `frontend/src/components/attendance/day-panel.tsx`
- Create: `frontend/src/components/attendance/day-panel.test.tsx`
- Modify: `frontend/src/components/attendance/week-grid.tsx`, `week-grid.test.tsx`

**Interfaces:**
- Consumes: `ExceptionEdit` (Task 5); `DayOut.exception`.
- Produces: comportamiento — con excepción: muestra `ExceptionEdit` (con
  `key={exception.id}-{day}`), oculta "Agregar excepción", cambio de descanso y el
  comentario suelto. La celda dice "Excepción" si hay excepción y el resultado no es
  `JUSTIFIED`.

- [ ] **Step 1: Write the failing tests**

`frontend/src/components/attendance/day-panel.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { DayOut, EmployeeRef } from "@/lib/api/types";

import { DayPanel } from "./day-panel";

const mutation = () => ({ mutate: vi.fn(), error: null, isPending: false });

vi.mock("@/lib/api/attendance", () => ({
  useCreateJustification: mutation,
  useUpdateJustification: mutation,
  useDeleteJustification: mutation,
  useRestSwap: mutation,
  useCreateException: mutation,
  useUpdateException: mutation,
  useDeleteException: mutation,
}));

const employee: EmployeeRef = { id: 1, short_name: "EMPLEADO A", rh_name: null, area: "OTHER" };

function day(overrides: Partial<DayOut>): DayOut {
  return {
    employee_id: 1,
    day: "2026-09-30",
    planned: "WORK",
    outcome: "ABSENT",
    checkin: null,
    minutes_late: null,
    rh_type: null,
    justification_id: null,
    comment: "",
    exception: null,
    ...overrides,
  };
}

describe("DayPanel", () => {
  it("edits the exception that justified the day instead of offering a new one", () => {
    const justified = day({
      planned: "ABSENCE",
      outcome: "JUSTIFIED",
      rh_type: "VACACIONES",
      comment: "Enfermedad.",
      exception: {
        id: 12,
        kind: "WORK_TO_ABSENCE",
        date_from: "2026-09-30",
        date_to: "2026-09-30",
        rh_type: "VACACIONES",
        comment: "Enfermedad.",
      },
    });
    render(<DayPanel selection={{ day: justified, employee }} onClose={() => undefined} />);
    expect(screen.getByRole("heading", { name: "Excepción · Ausencia justificada" })).toBeInTheDocument();
    expect(screen.getByLabelText("Comentario")).toHaveValue("Enfermedad.");
    expect(screen.queryByRole("heading", { name: "Agregar excepción" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Cambio de descanso" })).not.toBeInTheDocument();
  });

  it("offers to justify and to add an exception on a plain absence", () => {
    render(<DayPanel selection={{ day: day({}), employee }} onClose={() => undefined} />);
    expect(screen.getByRole("heading", { name: "Justificar falta" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Agregar excepción" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Cambio de descanso" })).toBeInTheDocument();
  });
});
```

En `frontend/src/components/attendance/week-grid.test.tsx`, dentro de
`describe("WeekGrid")`:

```tsx
  it("marks days changed by an exception", () => {
    const present = {
      ...calendar,
      days: [
        day({
          exception: {
            id: 3,
            kind: "PRESENT_NO_CHECKIN",
            date_from: "2026-09-21",
            date_to: "2026-09-21",
            rh_type: null,
            comment: "",
          },
        }),
      ],
    };
    render(<WeekGrid calendar={present} onSelect={() => undefined} />);
    expect(screen.getByRole("button", { name: /lun 21\/09: A tiempo \(excepción\)/ })).toHaveTextContent(
      "Excepción",
    );
  });
```

Run: `npm test -- src/components/attendance/day-panel.test.tsx src/components/attendance/week-grid.test.tsx`
Expected: FAIL — el panel muestra "Agregar excepción" y no hay sección de excepción; la
celda no dice "Excepción".

- [ ] **Step 2: Panel**

En `frontend/src/components/attendance/day-panel.tsx`, importar
`import { ExceptionEdit } from "./exception-edit";` y reemplazar `DayDetail` por:

```tsx
function DayDetail({ selection, onDone }: { selection: DaySelection; onDone: () => void }) {
  const { day, employee } = selection;
  const incident = incidentFor(day.outcome);
  const exception = day.exception;
  const canSwap =
    exception === null && (day.outcome === "ABSENT" || day.outcome === "UNREGISTERED_CHANGE");
  const looseComment = day.comment && day.justification_id === null && exception === null;
  return (
    <>
      <SheetHeader>
        <SheetTitle>
          {employee.short_name} · {formatDay(day.day)}
        </SheetTitle>
        <SheetDescription>{describe(selection)}</SheetDescription>
      </SheetHeader>
      <div className="space-y-8 p-4">
        {looseComment && <p className="text-sm">{day.comment}</p>}
        {incident && day.justification_id === null && (
          <JustifyForm employeeId={employee.id} day={day.day} incident={incident} onDone={onDone} />
        )}
        {incident && day.justification_id !== null && (
          <JustificationEdit
            justificationId={day.justification_id}
            incident={incident}
            rhType={day.rh_type}
            reason={day.comment}
            onDone={onDone}
          />
        )}
        {exception && (
          <ExceptionEdit key={`${exception.id}-${day.day}`} exception={exception} onDone={onDone} />
        )}
        {canSwap && <RestSwapForm employeeId={employee.id} day={day} onDone={onDone} />}
        {exception === null && <ExceptionForm employeeId={employee.id} day={day.day} onDone={onDone} />}
      </div>
    </>
  );
}
```

- [ ] **Step 3: Celda**

En `frontend/src/components/attendance/week-grid.tsx`, `DayCell`:

```tsx
function DayCell({ day, onClick }: { day: DayOut; onClick: () => void }) {
  const label = OUTCOME_LABELS[day.outcome];
  const time = formatTime(day.checkin);
  const justified = day.justification_id !== null;
  const changed = day.exception !== null && day.outcome !== "JUSTIFIED";
  const notes = [justified && "justificado", changed && "excepción"].filter(Boolean).join(", ");
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={day.outcome === "FUTURE"}
      aria-label={`${formatDay(day.day)}: ${label}${time ? ` ${time}` : ""}${notes ? ` (${notes})` : ""}`}
      className={cn(
        "flex h-14 w-full flex-col items-center justify-center rounded-md text-xs",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-default",
        OUTCOME_STYLES[day.outcome],
      )}
    >
      <span className="font-medium">{label}</span>
      {time && <span>{time}</span>}
      {justified && <span className="text-[10px]">Justificado</span>}
      {changed && <span className="text-[10px]">Excepción</span>}
    </button>
  );
}
```

- [ ] **Step 4: Run tests y compuertas**

Run: `npm run lint && npm run typecheck && npm test`
Expected: PASS (incluida la prueba existente `"(justificado)"` si la hay; el texto de
`aria-label` con solo justificación sigue siendo `… (justificado)`).

- [ ] **Step 5: Commit**

```bash
git add src/components/attendance/day-panel.tsx src/components/attendance/day-panel.test.tsx src/components/attendance/week-grid.tsx src/components/attendance/week-grid.test.tsx
git commit -m "fix: edit the day's existing exception from the day panel

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Editar excepciones en Configuración

**Files:**
- Modify: `frontend/src/components/config/exceptions-tab.tsx`

**Interfaces:**
- Consumes: `ExceptionEdit` (Task 5), `Dialog*` de `@/components/ui/dialog`.
- Produces: botón "Editar" por fila (aria-label `Editar <tipo> del <fecha>`) que abre un
  diálogo "Editar excepción" con `ExceptionEdit`; se cierra al guardar o eliminar.

- [ ] **Step 1: Write the failing test**

`frontend/src/components/config/exceptions-tab.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ExceptionsTab } from "./exceptions-tab";

const mutation = () => ({ mutate: vi.fn(), error: null, isPending: false });

vi.mock("@/lib/api/attendance", () => ({
  useCreateException: mutation,
  useUpdateException: mutation,
  useDeleteException: mutation,
}));

vi.mock("@/lib/api/config", () => ({
  useEmployees: () => ({ data: [{ id: 1, short_name: "EMPLEADO A" }] }),
  useExceptions: () => ({
    isPending: false,
    isError: false,
    data: [
      {
        id: 5,
        kind: "WORK_TO_ABSENCE",
        employee_id: 1,
        date_from: "2026-09-30",
        date_to: "2026-09-30",
        rh_type: "VACACIONES",
        comment: "Viaje",
      },
    ],
  }),
}));

describe("ExceptionsTab", () => {
  it("opens the exception in an edit dialog", async () => {
    render(<ExceptionsTab />);
    await userEvent.click(screen.getByRole("button", { name: "Editar Ausencia justificada del 30/09/2026" }));
    const dialog = screen.getByRole("dialog", { name: "Editar excepción" });
    expect(dialog).toHaveTextContent("EMPLEADO A");
    expect(screen.getByLabelText("Comentario")).toHaveValue("Viaje");
  });
});
```

Si `ClosureForm` (en el mismo archivo) usa otros hooks de `@/lib/api/config` o
`@/lib/api/attendance`, agregarlos a los mocks con `mutation`. El label "Comentario" del
diálogo es único porque `ExceptionEdit` usa `id="exception_edit_comment"`; si
`ClosureForm` también tiene un "Comentario", usar
`within(dialog).getByLabelText("Comentario")`.

Run: `npm test -- src/components/config/exceptions-tab.test.tsx`
Expected: FAIL — no hay botón "Editar".

- [ ] **Step 2: Implementar**

En `frontend/src/components/config/exceptions-tab.tsx`:

1. Imports nuevos:

```tsx
import { ExceptionEdit } from "@/components/attendance/exception-edit";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import type { ExceptionOut } from "@/lib/api/types";
```

2. Componente al final del archivo:

```tsx
function EditExceptionDialog({ exception, owner }: { exception: ExceptionOut; owner: string }) {
  const [open, setOpen] = useState(false);
  const kind = EXCEPTION_KIND_LABELS[exception.kind];
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline" aria-label={`Editar ${kind} del ${formatDate(exception.date_from)}`}>
          Editar
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Editar excepción</DialogTitle>
          <DialogDescription>{owner}</DialogDescription>
        </DialogHeader>
        <ExceptionEdit exception={exception} onDone={() => setOpen(false)} />
      </DialogContent>
    </Dialog>
  );
}
```

3. En la celda de acciones de cada fila, antes de `ConfirmDeleteButton`:

```tsx
                <TableCell className="space-x-2 text-right">
                  <EditExceptionDialog
                    exception={exception}
                    owner={exception.employee_id === null ? "Todos" : (names.get(exception.employee_id) ?? "")}
                  />
                  <ConfirmDeleteButton … (sin cambios) />
                </TableCell>
```

4. Texto de ayuda: "Las de un empleado se agregan desde la vista Semana (clic en el día)."
→ "Las de un empleado se agregan desde el Calendario (clic en el día)."

- [ ] **Step 3: Run tests y compuertas**

Run: `npm run lint && npm run typecheck && npm test`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/components/config/exceptions-tab.tsx src/components/config/exceptions-tab.test.tsx
git commit -m "feat: edit exceptions from the configuration tab

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Incidencias con filtros, dos tablas paginadas y copia completa para RH

**Files:**
- Create: `frontend/src/components/attendance/incident-filters.tsx`,
  `incident-filters.test.tsx`, `incident-table.tsx`
- Modify: `frontend/src/components/attendance/incidents-view.tsx` (reescritura),
  `frontend/src/app/(app)/incidencias/page.tsx`
- Modify: `frontend/src/components/attendance/rh-table.tsx`, `rh-table.test.tsx`
- Modify: `frontend/src/lib/labels.ts`, `frontend/src/lib/labels.test.ts` (`incidentAction`)

**Interfaces:**
- Consumes: `IncidentQuery`, `parseIncidentQuery`, `incidentQueryString`, `withFilters`,
  `toApiParams` (Task 2); `useIncidents`, `useRhRows`, `fetchAllRhRows` (Tasks 1, 3);
  `Pagination` (Task 4); `DayPanel` (Task 6).
- Produces:
  - `incidentAction(day: DayOut): "Justificar" | "Editar" | "Resolver" | null`
  - `<IncidentFilters query employees onApply />`
  - `<IncidentTable days byId onSelect />`
  - `<RhTable rows loadAll? />` — con `loadAll`, "Copiar para RH" copia lo que devuelve.
  - `IncidentsView({ query: IncidentQuery | null })`

- [ ] **Step 1: Write the failing tests**

En `frontend/src/lib/labels.test.ts` (agregar `incidentAction` al import y
`import type { DayOut } from "@/lib/api/types";`):

```ts
describe("incidentAction", () => {
  const base: DayOut = {
    employee_id: 1,
    day: "2026-09-23",
    planned: "WORK",
    outcome: "LATE",
    checkin: null,
    minutes_late: 5,
    rh_type: null,
    justification_id: null,
    comment: "",
    exception: null,
  };

  it("offers the right action per incident", () => {
    expect(incidentAction(base)).toBe("Justificar");
    expect(incidentAction({ ...base, justification_id: 4 })).toBe("Editar");
    expect(incidentAction({ ...base, outcome: "JUSTIFIED", planned: "ABSENCE" })).toBe("Editar");
    expect(incidentAction({ ...base, outcome: "UNREGISTERED_CHANGE", planned: "REST" })).toBe("Resolver");
    expect(incidentAction({ ...base, outcome: "OK" })).toBeNull();
  });
});
```

`frontend/src/components/attendance/incident-filters.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { IncidentQuery } from "@/lib/incident-query";

import { IncidentFilters } from "./incident-filters";

const QUERY: IncidentQuery = {
  from: "2026-09-01",
  to: "2026-09-30",
  employeeId: null,
  types: [],
  status: "all",
  page: 3,
  rhPage: 2,
};
const employees = [
  { id: 1, short_name: "EMPLEADO A", rh_name: null, area: "OTHER" as const },
  { id: 2, short_name: "EMPLEADO B", rh_name: null, area: "KITCHEN" as const },
];

describe("IncidentFilters", () => {
  it("applies employee, types and status and goes back to page 1", async () => {
    const onApply = vi.fn();
    render(<IncidentFilters query={QUERY} employees={employees} onApply={onApply} />);
    await userEvent.selectOptions(screen.getByLabelText("Empleado"), "2");
    await userEvent.click(screen.getByLabelText("Retardo"));
    await userEvent.click(screen.getByLabelText("Falta"));
    await userEvent.selectOptions(screen.getByLabelText("Estado"), "unjustified");
    await userEvent.click(screen.getByRole("button", { name: "Ver" }));
    expect(onApply).toHaveBeenCalledWith({
      ...QUERY,
      employeeId: 2,
      types: ["LATE", "ABSENT"],
      status: "unjustified",
      page: 1,
      rhPage: 1,
    });
  });

  it("clears the filters but keeps the range", async () => {
    const onApply = vi.fn();
    const filtered = { ...QUERY, employeeId: 1, types: ["LATE" as const], status: "justified" as const };
    render(<IncidentFilters query={filtered} employees={employees} onApply={onApply} />);
    expect(screen.getByLabelText("Retardo")).toBeChecked();
    await userEvent.click(screen.getByRole("button", { name: "Limpiar filtros" }));
    expect(onApply).toHaveBeenCalledWith({ ...QUERY, page: 1, rhPage: 1 });
  });
});
```

En `frontend/src/components/attendance/rh-table.test.tsx`, nuevo caso:

```tsx
  it("copies every row from loadAll, not only the visible page", async () => {
    const user = userEvent.setup();
    const writeText = vi.spyOn(navigator.clipboard, "writeText");
    const second = { ...rows[0], name: "APELLIDO DOS", day: "2026-09-24" };
    render(<RhTable rows={rows} loadAll={async () => [...rows, second]} />);
    await user.click(screen.getByRole("button", { name: "Copiar para RH" }));
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining("APELLIDO DOS\t24/09/2026"));
    expect(screen.getByText("Copia todas las filas del filtro, no solo esta página.")).toBeInTheDocument();
  });
```

Run: `npm test -- src/lib/labels.test.ts src/components/attendance/incident-filters.test.tsx src/components/attendance/rh-table.test.tsx`
Expected: FAIL.

- [ ] **Step 2: `incidentAction`**

En `frontend/src/lib/labels.ts` (agregar `DayOut` al import de tipos):

```ts
export function incidentAction(day: DayOut): "Justificar" | "Editar" | "Resolver" | null {
  const incident = incidentFor(day.outcome);
  if (incident && day.justification_id === null) return "Justificar";
  if (incident || day.outcome === "JUSTIFIED") return "Editar";
  if (day.outcome === "UNREGISTERED_CHANGE") return "Resolver";
  return null;
}
```

- [ ] **Step 3: `RhTable` con `loadAll`**

En `frontend/src/components/attendance/rh-table.tsx`:

```tsx
type Props = { rows: RhRowOut[]; loadAll?: () => Promise<RhRowOut[]> };

export function RhTable({ rows, loadAll }: Props) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">Sin incidencias para capturar en RH.</p>;
  }

  async function copy() {
    try {
      const all = loadAll ? await loadAll() : rows;
      await navigator.clipboard.writeText(rhRowsToTsv(all));
      toast.success(`Lista copiada (${all.length} filas)`);
    } catch {
      toast.error("No se pudo copiar; selecciona la tabla manualmente");
    }
  }
```

y en el encabezado de botones:

```tsx
      <div className="flex items-center justify-end gap-3">
        {loadAll && (
          <span className="text-xs text-muted-foreground">
            Copia todas las filas del filtro, no solo esta página.
          </span>
        )}
        <Button variant="outline" onClick={copy}>
          Copiar para RH
        </Button>
      </div>
```

- [ ] **Step 4: `IncidentTable`**

`frontend/src/components/attendance/incident-table.tsx` — mover `IncidentTable` e
`IncidentRow` desde `incidents-view.tsx`, con la acción de `incidentAction`:

```tsx
"use client";

import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { DayOut, EmployeeRef } from "@/lib/api/types";
import { formatDay, formatTime } from "@/lib/dates";
import { OUTCOME_LABELS, RH_LABELS, incidentAction } from "@/lib/labels";

type Props = {
  days: DayOut[];
  byId: Map<number, EmployeeRef>;
  onSelect: (day: DayOut) => void;
};

export function IncidentTable({ days, byId, onSelect }: Props) {
  if (days.length === 0) return <p className="text-sm text-muted-foreground">Sin incidencias.</p>;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Empleado</TableHead>
          <TableHead>Día</TableHead>
          <TableHead>Resultado</TableHead>
          <TableHead>Estado</TableHead>
          <TableHead>
            <span className="sr-only">Acciones</span>
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {days.map((day) => (
          <IncidentRow key={`${day.employee_id}-${day.day}`} day={day} byId={byId} onSelect={onSelect} />
        ))}
      </TableBody>
    </Table>
  );
}

function IncidentRow({ day, byId, onSelect }: { day: DayOut } & Omit<Props, "days">) {
  const action = incidentAction(day);
  const status =
    day.justification_id !== null || day.outcome === "JUSTIFIED"
      ? `Justificada${day.rh_type ? ` · ${RH_LABELS[day.rh_type]}` : ""}`
      : "Sin justificar";
  return (
    <TableRow>
      <TableCell>{byId.get(day.employee_id)?.short_name ?? day.employee_id}</TableCell>
      <TableCell>{formatDay(day.day)}</TableCell>
      <TableCell>
        {OUTCOME_LABELS[day.outcome]} {formatTime(day.checkin)}
      </TableCell>
      <TableCell>{status}</TableCell>
      <TableCell className="text-right">
        {action && (
          <Button size="sm" variant="outline" onClick={() => onSelect(day)}>
            {action}
          </Button>
        )}
      </TableCell>
    </TableRow>
  );
}
```

- [ ] **Step 5: `IncidentFilters`**

`frontend/src/components/attendance/incident-filters.tsx`:

```tsx
"use client";

import type { FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import type { EmployeeRef, IncidentStatus, IncidentType } from "@/lib/api/types";
import { type IncidentQuery, withFilters } from "@/lib/incident-query";
import { INCIDENT_TYPES, OUTCOME_LABELS, STATUS_LABELS } from "@/lib/labels";

type Props = {
  query: IncidentQuery;
  employees: EmployeeRef[];
  onApply: (query: IncidentQuery) => void;
};

function readForm(query: IncidentQuery, form: FormData): IncidentQuery {
  const employee = String(form.get("empleado") ?? "");
  const wanted = new Set(form.getAll("tipo").map(String));
  return withFilters(query, {
    from: String(form.get("desde")),
    to: String(form.get("hasta")),
    employeeId: employee === "" ? null : Number(employee),
    types: INCIDENT_TYPES.filter((type: IncidentType) => wanted.has(type)),
    status: String(form.get("estado")) as IncidentStatus,
  });
}

export function IncidentFilters({ query, employees, onApply }: Props) {
  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onApply(readForm(query, new FormData(event.currentTarget)));
  }
  const clear = () => onApply(withFilters(query, { employeeId: null, types: [], status: "all" }));
  return (
    <form onSubmit={onSubmit} className="flex flex-wrap items-end gap-3">
      <div className="space-y-1">
        <Label htmlFor="desde">Desde</Label>
        <Input id="desde" name="desde" type="date" defaultValue={query.from} required />
      </div>
      <div className="space-y-1">
        <Label htmlFor="hasta">Hasta</Label>
        <Input id="hasta" name="hasta" type="date" defaultValue={query.to} required />
      </div>
      <div className="space-y-1">
        <Label htmlFor="empleado">Empleado</Label>
        <NativeSelect id="empleado" name="empleado" defaultValue={query.employeeId ?? ""}>
          <option value="">Todos</option>
          {employees.map((employee) => (
            <option key={employee.id} value={employee.id}>
              {employee.short_name}
            </option>
          ))}
        </NativeSelect>
      </div>
      <fieldset className="flex flex-wrap items-center gap-3 pb-2">
        <legend className="sr-only">Tipo</legend>
        {INCIDENT_TYPES.map((type) => (
          <label key={type} className="flex items-center gap-1 text-sm">
            <input
              type="checkbox"
              name="tipo"
              value={type}
              defaultChecked={query.types.includes(type)}
              className="size-4 accent-primary"
            />
            {OUTCOME_LABELS[type]}
          </label>
        ))}
      </fieldset>
      <div className="space-y-1">
        <Label htmlFor="estado">Estado</Label>
        <NativeSelect id="estado" name="estado" defaultValue={query.status}>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </NativeSelect>
      </div>
      <Button type="submit" variant="outline">
        Ver
      </Button>
      <Button type="button" variant="ghost" onClick={clear}>
        Limpiar filtros
      </Button>
    </form>
  );
}
```

Ningún tipo vale "todos" de forma implícita: sin casillas marcadas no se filtra por tipo.

- [ ] **Step 6: Reescribir `IncidentsView` y la página**

`frontend/src/app/(app)/incidencias/page.tsx`:

```tsx
import { IncidentsView } from "@/components/attendance/incidents-view";
import { parseIncidentQuery, type UrlParams } from "@/lib/incident-query";

type Props = { searchParams: Promise<UrlParams> };

export default async function IncidenciasPage({ searchParams }: Props) {
  return <IncidentsView query={parseIncidentQuery(await searchParams)} />;
}
```

`frontend/src/components/attendance/incidents-view.tsx` (archivo completo):

```tsx
"use client";

import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";

import { ExportButton } from "@/components/export-button";
import { Loading, QueryError } from "@/components/feedback";
import { Pagination } from "@/components/pagination";
import { Button } from "@/components/ui/button";
import { fetchAllRhRows, useIncidents, useRhRows } from "@/lib/api/attendance";
import { useEmployees } from "@/lib/api/config";
import type { DayOut, EmployeeRef } from "@/lib/api/types";
import { addDays, weekStart } from "@/lib/dates";
import {
  type IncidentQuery,
  incidentQueryString,
  toApiParams,
  withFilters,
} from "@/lib/incident-query";
import { useEnsurePeriod } from "@/lib/period";

import { DayPanel } from "./day-panel";
import { IncidentFilters } from "./incident-filters";
import { IncidentTable } from "./incident-table";
import { RhTable } from "./rh-table";
import { WarningsList } from "./warnings-list";
import type { DaySelection } from "./week-grid";

export function IncidentsView({ query }: { query: IncidentQuery | null }) {
  const buildQuery = useCallback((today: string) => {
    const start = weekStart(today);
    return `desde=${start}&hasta=${addDays(start, 6)}`;
  }, []);
  useEnsurePeriod(query ? query.from : null, buildQuery);
  if (!query) return <Loading />;
  return <Incidents query={query} />;
}

function Incidents({ query }: { query: IncidentQuery }) {
  const router = useRouter();
  const go = (next: IncidentQuery) =>
    router.push(`/incidencias?${incidentQueryString(next)}`, { scroll: false });
  const incidents = useIncidents(toApiParams(query, query.page));
  const rhRows = useRhRows(toApiParams(query, query.rhPage));
  const employees = useEmployees();
  const [selection, setSelection] = useState<DaySelection | null>(null);
  const byId = new Map<number, EmployeeRef>((employees.data ?? []).map((e) => [e.id, e]));
  const select = (day: DayOut) => {
    const employee = byId.get(day.employee_id);
    if (employee) setSelection({ day, employee });
  };
  const unresolved = incidents.data?.data.unresolved ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <IncidentFilters
          key={incidentQueryString(query)}
          query={query}
          employees={(employees.data ?? []).filter((e) => e.active)}
          onApply={go}
        />
        <ExportButton from={query.from} to={query.to} group="week" />
      </div>
      {incidents.data && <WarningsList warnings={incidents.data.data.warnings} />}
      {unresolved > 0 && (
        <p role="status" className="flex items-center gap-2 text-sm">
          {unresolved} {unresolved === 1 ? "cambio sin registrar" : "cambios sin registrar"}
          <Button
            size="sm"
            variant="link"
            onClick={() => go(withFilters(query, { types: ["UNREGISTERED_CHANGE"], status: "all" }))}
          >
            Ver
          </Button>
        </p>
      )}
      <section className="space-y-2">
        <h2 className="text-lg font-semibold">Para capturar en RH</h2>
        {rhRows.isPending && <Loading />}
        {rhRows.isError && <QueryError error={rhRows.error} onRetry={() => rhRows.refetch()} />}
        {rhRows.data && (
          <>
            <RhTable rows={rhRows.data.data.items} loadAll={() => fetchAllRhRows(query)} />
            <Pagination
              meta={rhRows.data.page}
              label="Páginas de RH"
              onPage={(rhPage) => go({ ...query, rhPage })}
            />
          </>
        )}
      </section>
      <section className="space-y-2">
        <h2 className="text-lg font-semibold">Todas las incidencias</h2>
        {incidents.isPending && <Loading />}
        {incidents.isError && <QueryError error={incidents.error} onRetry={() => incidents.refetch()} />}
        {incidents.data && (
          <>
            <IncidentTable days={incidents.data.data.items} byId={byId} onSelect={select} />
            <Pagination
              meta={incidents.data.page}
              label="Páginas de incidencias"
              onPage={(page) => go({ ...query, page })}
            />
          </>
        )}
      </section>
      <DayPanel selection={selection} onClose={() => setSelection(null)} />
    </div>
  );
}
```

`useEmployees` devuelve también inactivos (`EmployeeOut.active`); el selector solo
muestra activos, que son los únicos con días en el reporte.

- [ ] **Step 7: Run tests y compuertas**

Run: `npm run lint && npm run typecheck && npm test`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/components/attendance src/app/\(app\)/incidencias/page.tsx src/lib/labels.ts src/lib/labels.test.ts
git commit -m "feat: filter and paginate incidents, copy every RH row

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Rutas de Calendario y Resumen, navegación y redirecciones

**Files:**
- Create: `frontend/src/lib/calendar.ts`, `frontend/src/lib/calendar.test.ts`
- Modify: `frontend/src/lib/dates.ts`, `frontend/src/lib/dates.test.ts`
- Create: `frontend/src/app/(app)/calendario/page.tsx`, `frontend/src/app/(app)/resumen/page.tsx`
- Modify: `frontend/src/app/(app)/semana/page.tsx`, `frontend/src/app/(app)/mes/page.tsx`,
  `frontend/src/app/(app)/page.tsx`
- Rename: `frontend/src/components/attendance/month-view.tsx` → `summary-view.tsx`
- Create: `frontend/src/components/attendance/view-switch.tsx`
- Modify: `frontend/src/components/attendance/week-view.tsx`, `frontend/src/components/app-shell.tsx`
- Modify: `frontend/src/lib/review.ts`, `review.test.ts`,
  `frontend/src/components/review/review-detail.test.tsx`
- Modify: `frontend/src/lib/auth/session.ts`, `session.test.ts`

**Interfaces:**
- Produces (`lib/calendar.ts`):
  - `type DayFocus = { employeeId: number; day: string }` (se mueve aquí desde `week-view.tsx`)
  - `weekHref(start: string, focus?: DayFocus | null): string`
  - `monthHref(month: string): string`
  - `summaryHref(month: string): string`
  - `parseFocus(empleado: string | undefined, dia: string | undefined): DayFocus | null`
  - `legacyWeekHref(params: { desde?: string; empleado?: string; dia?: string }): string`
  - `legacySummaryHref(params: { mes?: string }): string`
- Produces (`lib/dates.ts`): `isIsoMonth(value): value is string`, `isWeekend(value: string): boolean`,
  `formatMonth(month: string): string` (`"septiembre 2026"`), `MONTH_NAMES`.

- [ ] **Step 1: Write the failing tests**

`frontend/src/lib/calendar.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import {
  legacySummaryHref,
  legacyWeekHref,
  monthHref,
  parseFocus,
  summaryHref,
  weekHref,
} from "./calendar";

describe("calendar hrefs", () => {
  it("builds week, month and summary links", () => {
    expect(weekHref("2026-09-21")).toBe("/calendario?vista=semana&desde=2026-09-21");
    expect(weekHref("2026-09-21", { employeeId: 7, day: "2026-09-23" })).toBe(
      "/calendario?vista=semana&desde=2026-09-21&empleado=7&dia=2026-09-23",
    );
    expect(monthHref("2026-09")).toBe("/calendario?vista=mes&mes=2026-09");
    expect(summaryHref("2026-09")).toBe("/resumen?mes=2026-09");
  });

  it("parses a deep-link focus", () => {
    expect(parseFocus("7", "2026-09-23")).toEqual({ employeeId: 7, day: "2026-09-23" });
    expect(parseFocus("0", "2026-09-23")).toBeNull();
    expect(parseFocus("7", "ayer")).toBeNull();
    expect(parseFocus(undefined, undefined)).toBeNull();
  });
});

describe("legacy redirects", () => {
  it("keeps the week and the focused day", () => {
    expect(legacyWeekHref({ desde: "2026-09-21", empleado: "7", dia: "2026-09-23" })).toBe(
      "/calendario?vista=semana&desde=2026-09-21&empleado=7&dia=2026-09-23",
    );
    expect(legacyWeekHref({})).toBe("/calendario?vista=semana");
  });

  it("drops invalid values", () => {
    expect(legacyWeekHref({ desde: "x", empleado: "7", dia: "y" })).toBe("/calendario?vista=semana");
  });

  it("sends the month summary to /resumen", () => {
    expect(legacySummaryHref({ mes: "2026-09" })).toBe("/resumen?mes=2026-09");
    expect(legacySummaryHref({ mes: "2026-13" })).toBe("/resumen");
    expect(legacySummaryHref({})).toBe("/resumen");
  });
});
```

Al final de `frontend/src/lib/dates.test.ts` (agregar `formatMonth`, `isIsoMonth`,
`isWeekend` al import):

```ts
describe("month helpers", () => {
  it("validates YYYY-MM", () => {
    expect(isIsoMonth("2026-09")).toBe(true);
    expect(isIsoMonth("2026-13")).toBe(false);
    expect(isIsoMonth("2026-9")).toBe(false);
    expect(isIsoMonth(undefined)).toBe(false);
  });

  it("formats a month in Spanish", () => {
    expect(formatMonth("2026-09")).toBe("septiembre 2026");
  });

  it("detects weekends", () => {
    expect(isWeekend("2026-09-26")).toBe(true); // Saturday
    expect(isWeekend("2026-09-27")).toBe(true); // Sunday
    expect(isWeekend("2026-09-28")).toBe(false); // Monday
  });
});
```

Actualizar expectativas existentes:
- `src/lib/review.test.ts`: `"/semana?desde=2026-09-21&empleado=7&dia=…"` →
  `"/calendario?vista=semana&desde=2026-09-21&empleado=7&dia=…"` (dos lugares).
- `src/components/review/review-detail.test.tsx`: el mismo cambio en el `href` esperado.
- `src/lib/auth/session.test.ts`: `"falls back to /semana for %s"` →
  `"falls back to /calendario for %s"` y `toBe("/semana")` → `toBe("/calendario")`.
  (Las pruebas de `safeNext("/semana?desde=…")` siguen igual: `/semana` es una ruta
  válida que ahora redirige.)

Run: `npm test -- src/lib/calendar.test.ts src/lib/dates.test.ts src/lib/review.test.ts src/lib/auth/session.test.ts src/components/review/review-detail.test.tsx`
Expected: FAIL.

- [ ] **Step 2: Fechas**

En `frontend/src/lib/dates.ts`:

```ts
export const MONTH_NAMES = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];

export function isIsoMonth(value: string | undefined | null): value is string {
  return typeof value === "string" && /^\d{4}-\d{2}$/.test(value) && isIsoDate(`${value}-01`);
}

export function formatMonth(month: string): string {
  const [year, monthNumber] = month.split("-").map(Number);
  return `${MONTH_NAMES[monthNumber - 1]} ${year}`;
}

export function isWeekend(value: string): boolean {
  const weekday = parseIsoDate(value).getDay();
  return weekday === 0 || weekday === 6;
}
```

Si `isIsoDate("2026-13-01")` devolviera `true`, revisar `isIsoDate` (debe validar la
fecha real); el test de `isIsoMonth("2026-13")` lo detecta.

- [ ] **Step 3: `lib/calendar.ts`**

```ts
import { isIsoDate, isIsoMonth } from "./dates";

export type DayFocus = { employeeId: number; day: string };

export function parseFocus(empleado: string | undefined, dia: string | undefined): DayFocus | null {
  const employeeId = Number(empleado);
  if (!Number.isInteger(employeeId) || employeeId <= 0 || !isIsoDate(dia)) return null;
  return { employeeId, day: dia };
}

export function weekHref(start: string, focus: DayFocus | null = null): string {
  const params = new URLSearchParams({ vista: "semana", desde: start });
  if (focus) {
    params.set("empleado", String(focus.employeeId));
    params.set("dia", focus.day);
  }
  return `/calendario?${params}`;
}

export function monthHref(month: string): string {
  return `/calendario?vista=mes&mes=${month}`;
}

export function summaryHref(month: string): string {
  return `/resumen?mes=${month}`;
}

export function legacyWeekHref(params: { desde?: string; empleado?: string; dia?: string }): string {
  if (!isIsoDate(params.desde)) return "/calendario?vista=semana";
  return weekHref(params.desde, parseFocus(params.empleado, params.dia));
}

export function legacySummaryHref(params: { mes?: string }): string {
  return isIsoMonth(params.mes) ? summaryHref(params.mes) : "/resumen";
}
```

- [ ] **Step 4: Enlaces y sesión**

- `frontend/src/lib/review.ts`, en `actionHref`: `return weekHref(weekMonday, { employeeId: finding.employee_id, day });`
  (importar `weekHref` desde `./calendar`).
- `frontend/src/lib/auth/session.ts`: `const DEFAULT_AFTER_LOGIN = "/calendario";`
- `frontend/src/app/(app)/page.tsx`: `redirect("/calendario");`

- [ ] **Step 5: Resumen**

```bash
git mv src/components/attendance/month-view.tsx src/components/attendance/summary-view.tsx
```

En `summary-view.tsx`: renombrar `MonthView` → `SummaryView` y `Month` → `Summary`;
borrar la constante local `MONTHS`; label `formatMonth(month)`; hrefs
`summaryHref(addDays(from, -1).slice(0, 7))` y `summaryHref(addDays(to, 1).slice(0, 7))`;
encima de la tabla un título `<h1 className="text-lg font-semibold">Resumen del mes</h1>`.
Imports: `formatMonth` de `@/lib/dates`, `summaryHref` de `@/lib/calendar`.

`frontend/src/app/(app)/resumen/page.tsx`:

```tsx
import { SummaryView } from "@/components/attendance/summary-view";
import { isIsoMonth } from "@/lib/dates";

type Props = { searchParams: Promise<{ mes?: string }> };

export default async function ResumenPage({ searchParams }: Props) {
  const { mes } = await searchParams;
  return <SummaryView month={isIsoMonth(mes) ? mes : null} />;
}
```

- [ ] **Step 6: Selector Semana | Mes y vista de semana**

`frontend/src/components/attendance/view-switch.tsx`:

```tsx
import Link from "next/link";

import { cn } from "@/lib/utils";

type Props = { view: "semana" | "mes"; weekHref: string; monthHref: string };

export function ViewSwitch({ view, weekHref, monthHref }: Props) {
  const options = [
    { key: "semana", label: "Semana", href: weekHref },
    { key: "mes", label: "Mes", href: monthHref },
  ] as const;
  return (
    <nav aria-label="Vista del calendario" className="inline-flex rounded-md border p-0.5">
      {options.map((option) => (
        <Link
          key={option.key}
          href={option.href}
          aria-current={view === option.key ? "page" : undefined}
          className={cn(
            "rounded px-3 py-1 text-sm",
            view === option.key ? "bg-muted font-medium" : "text-muted-foreground hover:text-foreground",
          )}
        >
          {option.label}
        </Link>
      ))}
    </nav>
  );
}
```

En `frontend/src/components/attendance/week-view.tsx`:
- borrar `export type DayFocus` e importar `type DayFocus, monthHref, weekHref` desde `@/lib/calendar`;
- `buildQuery`: `` (today: string) => `vista=semana&desde=${weekStart(today)}` ``;
- `PeriodNav`: `previousHref={weekHref(addDays(from, -7))}` y `nextHref={weekHref(addDays(from, 7))}`;
- en la barra superior, antes de `PeriodNav`:
  `<ViewSwitch view="semana" weekHref={weekHref(from)} monthHref={monthHref(from.slice(0, 7))} />`
  (agrupar `ViewSwitch` y `PeriodNav` en un `<div className="flex flex-wrap items-center gap-3">`).

- [ ] **Step 7: Páginas**

`frontend/src/app/(app)/calendario/page.tsx` (la vista de mes llega en la Task 10; por
ahora `vista=mes` muestra la semana):

```tsx
import { WeekView } from "@/components/attendance/week-view";
import { parseFocus } from "@/lib/calendar";
import { isIsoDate } from "@/lib/dates";

type Props = {
  searchParams: Promise<{ vista?: string; desde?: string; mes?: string; empleado?: string; dia?: string }>;
};

export default async function CalendarioPage({ searchParams }: Props) {
  const { desde, empleado, dia } = await searchParams;
  return <WeekView requestedStart={isIsoDate(desde) ? desde : null} focus={parseFocus(empleado, dia)} />;
}
```

`frontend/src/app/(app)/semana/page.tsx`:

```tsx
import { redirect } from "next/navigation";

import { legacyWeekHref } from "@/lib/calendar";

type Props = { searchParams: Promise<{ desde?: string; empleado?: string; dia?: string }> };

export default async function SemanaPage({ searchParams }: Props) {
  redirect(legacyWeekHref(await searchParams));
}
```

`frontend/src/app/(app)/mes/page.tsx`:

```tsx
import { redirect } from "next/navigation";

import { legacySummaryHref } from "@/lib/calendar";

type Props = { searchParams: Promise<{ mes?: string }> };

export default async function MesPage({ searchParams }: Props) {
  redirect(legacySummaryHref(await searchParams));
}
```

- [ ] **Step 8: Navegación**

En `frontend/src/components/app-shell.tsx`:

```tsx
const LINKS = [
  { href: "/calendario", label: "Calendario" },
  { href: "/incidencias", label: "Incidencias" },
  { href: "/revision", label: "Revisión" },
  { href: "/resumen", label: "Resumen" },
  { href: "/configuracion", label: "Configuración" },
] as const;
```

- [ ] **Step 9: Run tests y compuertas**

Run: `npm run lint && npm run typecheck && npm test`
Expected: PASS. `grep -rn '"/semana\|/mes?' src --include=*.ts --include=*.tsx` solo
debe mostrar `proxy.test.ts`, `session.test.ts` y `period.test.tsx` (rutas de ejemplo
que siguen siendo válidas).

- [ ] **Step 10: Commit**

```bash
git add -A src
git commit -m "feat: calendar and summary routes with legacy redirects

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Vista de mes del calendario

**Files:**
- Create: `frontend/src/components/attendance/month-grid.tsx`, `month-grid.test.tsx`
- Create: `frontend/src/components/attendance/calendar-month-view.tsx`
- Modify: `frontend/src/lib/labels.ts`, `labels.test.ts` (`OUTCOME_SHORT`)
- Modify: `frontend/src/components/attendance/legend.tsx`
- Modify: `frontend/src/app/(app)/calendario/page.tsx`

**Interfaces:**
- Consumes: `useCalendar`, `DayPanel`, `findDaySelection`/`DaySelection`, `Legend`,
  `PeriodNav`, `ExportButton`, `ViewSwitch`, `weekHref`, `monthHref`, `formatMonth`,
  `monthRange`, `isWeekend`, `isIsoMonth`.
- Produces: `OUTCOME_SHORT: Record<Outcome, string>`;
  `<MonthGrid calendar onSelect />`; `CalendarMonthView({ month: string | null })`;
  `<Legend short? />`.

- [ ] **Step 1: Write the failing tests**

En `frontend/src/lib/labels.test.ts` (agregar `OUTCOME_SHORT`):

```ts
describe("OUTCOME_SHORT", () => {
  it("abbreviates every visible outcome with a distinct letter", () => {
    const shown = ["OK", "LATE", "ABSENT", "UNREGISTERED_CHANGE", "JUSTIFIED", "REST", "CLOSED"] as const;
    const letters = shown.map((outcome) => OUTCOME_SHORT[outcome]);
    expect(letters).toEqual(["A", "R", "F", "C", "J", "D", "X"]);
    expect(new Set(letters).size).toBe(letters.length);
  });
});
```

`frontend/src/components/attendance/month-grid.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { CalendarOut, DayOut } from "@/lib/api/types";

import { MonthGrid } from "./month-grid";

function day(overrides: Partial<DayOut>): DayOut {
  return {
    employee_id: 1,
    day: "2026-09-25",
    planned: "WORK",
    outcome: "OK",
    checkin: null,
    minutes_late: null,
    rh_type: null,
    justification_id: null,
    comment: "",
    exception: null,
    ...overrides,
  };
}

const calendar: CalendarOut = {
  start: "2026-09-25",
  end: "2026-09-27",
  employees: [{ id: 1, short_name: "EMPLEADO A", rh_name: null, area: "OTHER" }],
  days: [
    day({ outcome: "LATE", checkin: "2026-09-25T16:55:00", minutes_late: 15 }),
    day({ day: "2026-09-26", outcome: "REST", planned: "REST" }),
    day({ day: "2026-09-27", outcome: "FUTURE" }),
  ],
  warnings: [],
};

describe("MonthGrid", () => {
  it("shows one compact cell per day with the details in its label", () => {
    render(<MonthGrid calendar={calendar} onSelect={() => undefined} />);
    expect(screen.getByRole("columnheader", { name: "vie 25/09" })).toHaveTextContent("25");
    const late = screen.getByRole("button", { name: "vie 25/09: Retardo 16:55" });
    expect(late).toHaveTextContent("R");
    expect(late).toHaveAttribute("title", "vie 25/09: Retardo 16:55");
    expect(screen.getByRole("button", { name: /sáb 26\/09: Descanso/ })).toHaveTextContent("D");
  });

  it("selects a day and disables future days", async () => {
    const onSelect = vi.fn();
    render(<MonthGrid calendar={calendar} onSelect={onSelect} />);
    await userEvent.click(screen.getByRole("button", { name: /vie 25\/09/ }));
    expect(onSelect).toHaveBeenCalledWith(calendar.days[0], calendar.employees[0]);
    expect(screen.getByRole("button", { name: /dom 27\/09/ })).toBeDisabled();
  });
});
```

`formatDay` produce encabezados como `"lun 21/09"` (ver `week-grid.test.tsx`); el
encabezado de mes muestra solo el número pero conserva el nombre accesible con
`aria-label`. Si el formato de `formatDay` difiere ("sá" en vez de "sáb"), ajustar los
regex del test a `formatDay`, no al revés.

Run: `npm test -- src/lib/labels.test.ts src/components/attendance/month-grid.test.tsx`
Expected: FAIL.

- [ ] **Step 2: `OUTCOME_SHORT` y leyenda**

En `frontend/src/lib/labels.ts`:

```ts
export const OUTCOME_SHORT: Record<Outcome, string> = {
  OK: "A",
  LATE: "R",
  ABSENT: "F",
  UNREGISTERED_CHANGE: "C",
  REST: "D",
  CLOSED: "X",
  JUSTIFIED: "J",
  PENDING: "P",
  FUTURE: "",
};
```

En `frontend/src/components/attendance/legend.tsx`:

```tsx
export function Legend({ short = false }: { short?: boolean }) {
  return (
    <ul aria-label="Leyenda" className="flex flex-wrap gap-2 text-xs">
      {SHOWN.map((outcome) => (
        <li key={outcome} className={cn("rounded px-2 py-1", OUTCOME_STYLES[outcome])}>
          {short && <span className="mr-1 font-semibold">{OUTCOME_SHORT[outcome]}</span>}
          {OUTCOME_LABELS[outcome]}
        </li>
      ))}
    </ul>
  );
}
```

(importar `OUTCOME_SHORT`).

- [ ] **Step 3: `MonthGrid`**

`frontend/src/components/attendance/month-grid.tsx`:

```tsx
import type { CalendarOut, DayOut, EmployeeRef } from "@/lib/api/types";
import { daysBetween, formatDay, formatTime, isWeekend } from "@/lib/dates";
import { OUTCOME_LABELS, OUTCOME_SHORT, OUTCOME_STYLES } from "@/lib/labels";
import { cn } from "@/lib/utils";

type Props = {
  calendar: CalendarOut;
  onSelect: (day: DayOut, employee: EmployeeRef) => void;
};

export function MonthGrid({ calendar, onSelect }: Props) {
  const dates = daysBetween(calendar.start, calendar.end);
  const byKey = new Map(calendar.days.map((d) => [`${d.employee_id}|${d.day}`, d]));
  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full min-w-[960px] table-fixed text-xs">
        <thead>
          <tr>
            <th scope="col" className="w-28 p-1 text-left font-medium">
              Empleado
            </th>
            {dates.map((date) => (
              <th
                key={date}
                scope="col"
                aria-label={formatDay(date)}
                className={cn("p-1 text-center font-medium", isWeekend(date) && "bg-muted/60")}
              >
                {Number(date.slice(8))}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {calendar.employees.map((employee) => (
            <tr key={employee.id} className="border-t">
              <th scope="row" className="truncate p-1 text-left font-medium">
                {employee.short_name}
              </th>
              {dates.map((date) => {
                const day = byKey.get(`${employee.id}|${date}`);
                return (
                  <td key={date} className="p-0.5">
                    {day && <MonthCell day={day} onClick={() => onSelect(day, employee)} />}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function describeDay(day: DayOut): string {
  const time = formatTime(day.checkin);
  const notes = [
    day.justification_id !== null && "justificado",
    day.exception !== null && day.outcome !== "JUSTIFIED" && "excepción",
  ].filter(Boolean);
  const base = `${formatDay(day.day)}: ${OUTCOME_LABELS[day.outcome]}${time ? ` ${time}` : ""}`;
  return notes.length > 0 ? `${base} (${notes.join(", ")})` : base;
}

function MonthCell({ day, onClick }: { day: DayOut; onClick: () => void }) {
  const description = describeDay(day);
  const marked = day.justification_id !== null || (day.exception !== null && day.outcome !== "JUSTIFIED");
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={day.outcome === "FUTURE"}
      title={description}
      aria-label={description}
      className={cn(
        "flex h-9 w-full items-center justify-center rounded text-[11px] font-medium",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-default",
        OUTCOME_STYLES[day.outcome],
        marked && "ring-1 ring-inset ring-sky-500",
      )}
    >
      {OUTCOME_SHORT[day.outcome]}
    </button>
  );
}
```

- [ ] **Step 4: `CalendarMonthView` y página**

`frontend/src/components/attendance/calendar-month-view.tsx`:

```tsx
"use client";

import { useCallback, useState } from "react";

import { ExportButton } from "@/components/export-button";
import { Loading, QueryError } from "@/components/feedback";
import { PeriodNav } from "@/components/period-nav";
import { useCalendar } from "@/lib/api/attendance";
import { monthHref, weekHref } from "@/lib/calendar";
import { addDays, formatMonth, monthRange, weekStart } from "@/lib/dates";
import { useEnsurePeriod } from "@/lib/period";

import { DayPanel } from "./day-panel";
import { Legend } from "./legend";
import { MonthGrid } from "./month-grid";
import { ViewSwitch } from "./view-switch";
import { WarningsList } from "./warnings-list";
import type { DaySelection } from "./week-grid";

export function CalendarMonthView({ month }: { month: string | null }) {
  const buildQuery = useCallback((today: string) => `vista=mes&mes=${today.slice(0, 7)}`, []);
  useEnsurePeriod(month, buildQuery);
  if (month === null) return <Loading />;
  return <Month month={month} />;
}

function Month({ month }: { month: string }) {
  const { from, to } = monthRange(`${month}-01`);
  const calendar = useCalendar(from, to);
  const [selection, setSelection] = useState<DaySelection | null>(null);
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <ViewSwitch view="mes" weekHref={weekHref(weekStart(from))} monthHref={monthHref(month)} />
          <PeriodNav
            label={formatMonth(month)}
            previousHref={monthHref(addDays(from, -1).slice(0, 7))}
            nextHref={monthHref(addDays(to, 1).slice(0, 7))}
          />
        </div>
        <ExportButton from={from} to={to} group="month" />
      </div>
      {calendar.isPending && <Loading />}
      {calendar.isError && <QueryError error={calendar.error} onRetry={() => calendar.refetch()} />}
      {calendar.data && (
        <>
          <WarningsList warnings={calendar.data.warnings} />
          <MonthGrid
            calendar={calendar.data}
            onSelect={(day, employee) => setSelection({ day, employee })}
          />
          <Legend short />
        </>
      )}
      <DayPanel selection={selection} onClose={() => setSelection(null)} />
    </div>
  );
}
```

`frontend/src/app/(app)/calendario/page.tsx` (reemplazar el cuerpo):

```tsx
import { CalendarMonthView } from "@/components/attendance/calendar-month-view";
import { WeekView } from "@/components/attendance/week-view";
import { parseFocus } from "@/lib/calendar";
import { isIsoDate, isIsoMonth } from "@/lib/dates";

type Props = {
  searchParams: Promise<{ vista?: string; desde?: string; mes?: string; empleado?: string; dia?: string }>;
};

export default async function CalendarioPage({ searchParams }: Props) {
  const { vista, desde, mes, empleado, dia } = await searchParams;
  if (vista === "mes") return <CalendarMonthView month={isIsoMonth(mes) ? mes : null} />;
  return <WeekView requestedStart={isIsoDate(desde) ? desde : null} focus={parseFocus(empleado, dia)} />;
}
```

`useEnsurePeriod` usa `pathname` (`/calendario`), así que la consulta construida debe
incluir `vista=mes`, como arriba.

- [ ] **Step 5: Run tests y compuertas**

Run: `npm run lint && npm run typecheck && npm test`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/components/attendance src/lib/labels.ts src/lib/labels.test.ts src/app/\(app\)/calendario/page.tsx
git commit -m "feat: monthly calendar view

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: E2E de los flujos nuevos

**Files:**
- Modify: `frontend/e2e/attendance.spec.ts`, `frontend/e2e/review.spec.ts`

**Interfaces:**
- Consumes: la UI completa (Tasks 1–10) sobre la demo (`tabernas-demo`).

- [ ] **Step 1: Levantar la demo con el código de la rama**

Desde la raíz del repo (el stack real se detiene, **no** se borra):

```bash
docker compose stop
SR_MODE=fake REVIEW_AGENT=fake docker compose -p tabernas-demo up -d --build --wait
SR_MODE=fake docker compose -p tabernas-demo run --rm backend python /scripts/seed_demo.py
```

Expected: `Empleados demo creados: 7` (o 0 si ya existían).

- [ ] **Step 2: Actualizar y escribir las pruebas**

`frontend/e2e/review.spec.ts`: `a[href^="/semana?"]` → `a[href^="/calendario?"]`.

`frontend/e2e/attendance.spec.ts` (archivo completo):

```ts
import { expect, type Page, test } from "@playwright/test";

const USER = process.env.FAKE_AUTH_USER ?? "demo";
const PASSWORD = process.env.FAKE_AUTH_PASSWORD ?? "demo";

async function login(page: Page, path: string) {
  await page.goto(path);
  await expect(page).toHaveURL(/\/login\?next=/);
  await page.getByLabel("Usuario").fill(USER);
  await page.getByLabel("Contraseña").fill(PASSWORD);
  await page.getByRole("button", { name: "Entrar" }).click();
}

test("login through a legacy week link, justify an incident and export", async ({ page }) => {
  await login(page, "/semana?desde=2026-09-21");
  await expect(page).toHaveURL(/\/calendario\?vista=semana&desde=2026-09-21/);
  await expect(page.getByRole("row", { name: /EMPLEADO A/ })).toBeVisible();

  await page.goto("/incidencias?desde=2026-09-01&hasta=2026-09-27");
  await expect(page.getByRole("heading", { name: "Para capturar en RH" })).toBeVisible();
  await page.getByRole("button", { name: "Justificar" }).first().click();
  await page.getByLabel("Motivo").fill("Prueba E2E");
  await page.getByRole("button", { name: "Guardar justificación" }).click();
  await expect(page.getByText("Justificación guardada")).toBeVisible();

  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "Exportar a Excel" }).click();
  expect((await download).suggestedFilename()).toBe("asistencia_2026-09-01_2026-09-27.xlsx");
});

test("create, edit and delete an absence exception from the calendar", async ({ page }) => {
  await login(page, "/calendario?vista=semana&desde=2026-09-21");
  const cell = page.getByRole("row", { name: /EMPLEADO A/ }).getByRole("button", { name: /lun 21\/09/ });

  await cell.click();
  await page.getByLabel("Comentario").fill("E2E vacaciones");
  await page.getByRole("button", { name: "Guardar excepción" }).click();
  await expect(page.getByText("Excepción registrada")).toBeVisible();

  await cell.click();
  const panel = page.getByRole("dialog");
  await expect(panel.getByRole("heading", { name: "Excepción · Ausencia justificada" })).toBeVisible();
  await expect(panel.getByLabel("Comentario")).toHaveValue("E2E vacaciones");
  await expect(panel.getByRole("heading", { name: "Agregar excepción" })).toHaveCount(0);
  await panel.getByLabel("Tipo en RH").selectOption("INCAPACIDAD");
  await panel.getByRole("button", { name: "Guardar cambios" }).click();
  await expect(page.getByText("Excepción actualizada")).toBeVisible();

  await cell.click();
  await expect(page.getByRole("dialog").getByLabel("Tipo en RH")).toHaveValue("INCAPACIDAD");
  await page.getByRole("button", { name: "Eliminar excepción" }).click();
  await page.getByRole("button", { name: /Confirmar/ }).click();
  await expect(page.getByText("Excepción eliminada")).toBeVisible();
});

test("filter incidents by employee and page through them", async ({ page }) => {
  await login(page, "/incidencias?desde=2026-09-01&hasta=2026-09-30");
  const pages = page.getByRole("navigation", { name: "Páginas de incidencias" });
  await expect(pages).toContainText(/^1–25 de \d+/);
  await pages.getByRole("button", { name: "Siguiente →" }).click();
  await expect(page).toHaveURL(/pag=2/);
  await expect(pages).toContainText(/^26–/);

  await page.getByLabel("Empleado").selectOption({ label: "EMPLEADO A" });
  await page.getByRole("button", { name: "Ver" }).click();
  await expect(page).toHaveURL(/empleado=\d+/);
  await expect(page).not.toHaveURL(/pag=/);
  const rows = page
    .getByRole("heading", { name: "Todas las incidencias" })
    .locator("xpath=..")
    .getByRole("row")
    .filter({ hasNot: page.getByRole("columnheader") });
  for (const row of await rows.all()) await expect(row).toContainText("EMPLEADO A");
});

test("switch from week to month and open a day", async ({ page }) => {
  await login(page, "/calendario?vista=semana&desde=2026-09-21");
  await page.getByRole("link", { name: "Mes" }).click();
  await expect(page).toHaveURL(/vista=mes&mes=2026-09/);
  await page.getByRole("row", { name: /EMPLEADO A/ }).getByRole("button", { name: /lun 21\/09/ }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
});

test("the API rejects requests without a session", async ({ request }) => {
  const response = await request.get("/backend/attendance/calendar?from=2026-09-21&to=2026-09-27");
  expect(response.status()).toBe(401);
});
```

El día `lun 21/09` de EMPLEADO A podría ser de descanso en la demo; no importa: una
ausencia justificada se puede registrar en cualquier día y la prueba la elimina al
final. Si la prueba falla porque ya existe una excepción ese día (corrida anterior
interrumpida), borrarla desde Configuración → Excepciones y repetir.

- [ ] **Step 3: Correr E2E**

Run (desde `frontend/`): `npm run e2e`
Expected: 6 passed (5 aquí + 1 de `review.spec.ts`).

- [ ] **Step 4: Bajar la demo y restaurar el stack real**

```bash
docker compose -p tabernas-demo down -v
docker compose up -d
```

- [ ] **Step 5: Commit**

```bash
git add e2e
git commit -m "test: e2e for exception editing, incident filters and month view

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: Documentación y verificación final

**Files:**
- Modify: `CLAUDE.md`, `docs/plan.md`

- [ ] **Step 1: CLAUDE.md**

- Status: agregar después del párrafo de la Etapa 2:
  "**Attendance improvements** (2026-10-03): exception editing from the day panel,
  API-side filters and pagination for incidents (`/attendance/incidents`,
  `/attendance/rh-rows`), Calendario (week/month) and Resumen tabs; spec
  `docs/specs/2026-10-03-asistencia-mejoras-design.md`, plans
  `docs/plans/2026-10-03-asistencia-mejoras-plan-{a-backend,b-frontend}.md`."
- Backend layout, `domain/`: "`incident_filter.py` — pure filters and pagination of
  the incident list."
- Frontend layout: `/revision` enlaza a `/calendario?vista=semana&desde&empleado&dia`;
  agregar "`lib/incident-query.ts` — Incidencias filters ⇄ URL; `lib/calendar.ts` —
  calendar/summary hrefs and legacy `/semana`, `/mes` redirects; `lib/pages.ts` —
  page windows and fetching every page (RH copy)."

- [ ] **Step 2: docs/plan.md**

En §5 Etapa 1, "Pendientes conocidos": quitar el punto de "`DayOut` no indica si un día
viene de una excepción…" y agregar debajo del estado de la etapa:
"> Mejoras de uso (2026-10-03): editar excepciones desde el día, filtros y paginación
> en Incidencias, calendario mensual y pestaña Resumen
> ([spec](specs/2026-10-03-asistencia-mejoras-design.md))."

- [ ] **Step 3: Compuertas completas**

```bash
cd frontend && npm run lint && npm run typecheck && npm test -- --coverage
cd ../backend && uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest --cov && uv run coverage report --include="*/tabernas/domain/*" --fail-under=95
```

Expected: todo en verde; cobertura de `src/lib` ≥ 80%.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md docs/plan.md
git commit -m "docs: record attendance improvements

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
