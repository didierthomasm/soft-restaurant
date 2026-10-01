# Etapa 2 · Plan B — Frontend de la revisión semanal

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vista `/revision` donde el gerente ve el borrador semanal (resumen, hallazgos por
prioridad con su acción sugerida, lista para RH), lo genera bajo demanda, ve si los datos
cambiaron y lo aprueba; más los umbrales en Configuración y el enlace directo al panel
del día en `/semana`.

**Architecture:** Igual que la Etapa 1: `lib/api/reviews.ts` (hooks TanStack Query sobre
`openapi-fetch`, con sondeo cada 3 s mientras un borrador está `QUEUED`/`RUNNING`),
`lib/review.ts` (etiquetas y funciones puras con pruebas), componentes presentacionales
en `components/review/` y la página en `app/(app)/revision/`. El navegador solo llama a
`/backend/...`.

**Tech Stack:** Next.js 16 (App Router), TypeScript, Tailwind, shadcn/ui (Radix),
TanStack Query 5, openapi-fetch + tipos generados, Vitest + Testing Library, Playwright.

**Spec:** [`docs/specs/2026-10-01-etapa-2-revision-semanal-design.md`](../specs/2026-10-01-etapa-2-revision-semanal-design.md) §8.
**Depende del Plan A** ([`2026-10-01-etapa-2-plan-a-backend.md`](2026-10-01-etapa-2-plan-a-backend.md)):
la API `/reviews`, `/settings/review` y el servicio `worker` deben existir antes de
empezar.

## Global Constraints

- Texto de UI en español; código en inglés. Nunca escribir a mano tipos de la API:
  `npm run gen:api` con el backend del Plan A corriendo.
- El navegador solo habla con `/backend/*`. Nada de nombres reales en pruebas ni E2E
  (`EMPLEADO A`… del modo demo).
- Node ≥ 24.15. Desde `frontend/`: `npm run lint && npm run typecheck && npm test`.
- shadcn/ui está en Radix: `npx shadcn add` sí; nunca `shadcn init`.
- Sondeo: `POLL_MS = 3000` solo mientras el borrador está `QUEUED` o `RUNNING`.
- Accesibilidad como en la Etapa 1: estados con texto (no solo color), `role="status"`
  para avisos y `role="alert"` para errores.
- Commits `<type>: <description>` cerrando con
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Racha que empezó la semana anterior:** el botón del hallazgo debe abrir un día de
   la semana revisada, no uno de la semana pasada. → test en Task 2.
2. **Lista y detalle desfasados:** la lista dice `RUNNING` pero el detalle ya está
   `READY`; la vista debe mostrar el borrador, no "Generando…" para siempre. → test en
   Task 4.
3. **Borrador sin narrativa:** los hallazgos y la lista RH se muestran igual, con el
   motivo. → test en Task 3.
4. **Enlace a `/semana` con un día fuera de la semana o un empleado inexistente:** la
   página carga normal sin abrir el panel. → test en Task 5.
5. **Cambio de año ISO:** navegar a la semana del 28-dic-2026 pide `2026-W53`, no
   `2027-W53`. → test en Task 1.

---

## Estructura de archivos

```
frontend/
  src/lib/api/schema.d.ts            regenerado
  src/lib/api/types.ts               + alias de revisión
  src/lib/api/reviews.ts             hooks
  src/lib/dates.ts                   + isoWeekYear, isoWeekMonday, formatDateTime
  src/lib/review.ts                  etiquetas y helpers puros (+ review.test.ts)
  src/components/review/finding-card.tsx
  src/components/review/review-detail.tsx   (+ test)
  src/components/review/review-view.tsx     (+ test)
  src/components/attendance/week-view.tsx   + foco desde la URL
  src/components/attendance/week-grid.tsx   + findDaySelection (+ test)
  src/components/config/review-settings-tab.tsx  (+ test)
  src/components/config/config-view.tsx     + pestaña
  src/components/app-shell.tsx              + "Revisión"
  src/app/(app)/revision/page.tsx
  src/app/(app)/semana/page.tsx             + empleado, dia
  e2e/review.spec.ts
  vitest.config.ts                          excluir hooks de cobertura
CLAUDE.md, docs/plan.md
```

---

### Task 1: Tipos generados, hooks y fechas ISO

**Files:**
- Modify: `frontend/src/lib/api/schema.d.ts` (generado), `frontend/src/lib/api/types.ts`
- Create: `frontend/src/lib/api/reviews.ts`
- Modify: `frontend/src/lib/dates.ts`, `frontend/src/lib/dates.test.ts`
- Modify: `frontend/vitest.config.ts`

**Interfaces:**
- Consumes: API del Plan A (Task 14 y Task 6).
- Produces:
  - Tipos: `ReviewSummaryOut`, `ReviewDetailOut`, `FindingOut`, `NarrativeItemOut`,
    `ProposedRowOut`, `ReviewSettingsBody`, `FindingKind`, `Priority`, `SuggestedAction`,
    `ReviewStatus`, `ReviewTrigger`.
  - `dates.isoWeekYear(value: string): number`, `dates.isoWeekMonday(year, week): string`,
    `dates.formatDateTime(value: string | null | undefined): string` (`"24/09/2026 17:30"`,
    para fechas *naive* del backend).
  - Hooks: `reviewKeys`, `POLL_MS`, `useWeekReviews(year, week)`, `useReview(id | null)`,
    `useCreateReview()`, `useApproveReview()`, `useReviewSettings()`,
    `useSaveReviewSettings()`. `isInProgress` lo produce Task 2; aquí se define primero en
    `lib/review.ts` con solo esa función (Task 2 completa el archivo).

- [ ] **Step 1: Regenerate the API types**

Con el Plan A integrado (desde la raíz del repo):

```bash
docker compose up -d --build --wait backend
cd frontend && npm run gen:api
grep -c "ReviewDetailOut\|ReviewSettingsBody\|FindingKind" src/lib/api/schema.d.ts
```

Expected: el conteo es mayor que 0.

- [ ] **Step 2: Write the failing date tests**

En `frontend/src/lib/dates.test.ts`, agregar `formatDateTime`, `isoWeekMonday` e
`isoWeekYear` al import y estos casos dentro del `describe("dates", ...)`:

```ts
  it("finds the ISO week-numbering year", () => {
    expect(isoWeekYear("2026-09-21")).toBe(2026);
    expect(isoWeekYear("2026-12-28")).toBe(2026); // W53
    expect(isoWeekYear("2027-01-01")).toBe(2026); // still 2026-W53
    expect(isoWeekYear("2027-01-04")).toBe(2027);
  });

  it("finds the Monday of an ISO week", () => {
    expect(isoWeekMonday(2026, 39)).toBe("2026-09-21");
    expect(isoWeekMonday(2026, 53)).toBe("2026-12-28");
    expect(isoWeekMonday(2027, 1)).toBe("2027-01-04");
  });

  it("formats naive backend datetimes", () => {
    expect(formatDateTime("2026-09-24T17:30:00")).toBe("24/09/2026 17:30");
    expect(formatDateTime(null)).toBe("");
  });
```

Run: `npm test -- src/lib/dates.test.ts`
Expected: FAIL (`isoWeekYear is not a function`, etc.).

- [ ] **Step 3: Implement dates, types and hooks**

Al final de `frontend/src/lib/dates.ts`:

```ts
/** Year the ISO week belongs to (the year of its Thursday): 2027-01-01 is 2026-W53. */
export function isoWeekYear(value: string): number {
  const date = parseIsoDate(value);
  const thursday = new Date(
    date.getFullYear(),
    date.getMonth(),
    date.getDate() + 3 - ((date.getDay() + 6) % 7),
  );
  return thursday.getFullYear();
}

/** Monday of ISO week `week` of `year` (week 1 contains January 4th). */
export function isoWeekMonday(year: number, week: number): string {
  const january4 = toIsoDate(new Date(year, 0, 4));
  return addDays(weekStart(january4), (week - 1) * 7);
}

/** "YYYY-MM-DDTHH:MM…" (naive business time from the backend) → "DD/MM/YYYY HH:MM". */
export function formatDateTime(datetime: string | null | undefined): string {
  return datetime ? `${formatDate(datetime.slice(0, 10))} ${formatTime(datetime)}` : "";
}
```

Al final de `frontend/src/lib/api/types.ts`:

```ts
export type ReviewSummaryOut = Schemas["ReviewSummaryOut"];
export type ReviewDetailOut = Schemas["ReviewDetailOut"];
export type FindingOut = Schemas["FindingOut"];
export type NarrativeItemOut = Schemas["NarrativeItemOut"];
export type ProposedRowOut = Schemas["ProposedRowOut"];
export type ReviewSettingsBody = Schemas["ReviewSettingsBody"];
export type FindingKind = Schemas["FindingKind"];
export type Priority = Schemas["Priority"];
export type SuggestedAction = Schemas["SuggestedAction"];
export type ReviewStatus = Schemas["ReviewStatus"];
export type ReviewTrigger = Schemas["ReviewTrigger"];
```

`frontend/src/lib/review.ts` (Task 2 lo completa):

```ts
import type { ReviewStatus } from "@/lib/api/types";

export function isInProgress(status: ReviewStatus): boolean {
  return status === "QUEUED" || status === "RUNNING";
}
```

`frontend/src/lib/api/reviews.ts`:

```ts
"use client";

import { useMutation, useQuery } from "@tanstack/react-query";

import { isInProgress } from "@/lib/review";

import { api, unwrap } from "./client";
import { useInvalidate } from "./invalidate";
import type { ReviewSettingsBody } from "./types";

export const POLL_MS = 3_000;

export const reviewKeys = {
  all: ["reviews"] as const,
  week: (year: number, week: number) => ["reviews", "week", year, week] as const,
  detail: (id: number) => ["reviews", "detail", id] as const,
  settings: ["settings", "review"] as const,
};

export function useWeekReviews(year: number, week: number) {
  return useQuery({
    queryKey: reviewKeys.week(year, week),
    queryFn: () => unwrap(api.GET("/reviews", { params: { query: { year, week } } })),
    refetchInterval: (query) =>
      query.state.data?.some((review) => isInProgress(review.status)) ? POLL_MS : false,
  });
}

export function useReview(id: number | null) {
  return useQuery({
    queryKey: reviewKeys.detail(id ?? 0),
    queryFn: () =>
      unwrap(api.GET("/reviews/{review_id}", { params: { path: { review_id: id ?? 0 } } })),
    enabled: id !== null,
    refetchInterval: (query) =>
      query.state.data && isInProgress(query.state.data.status) ? POLL_MS : false,
  });
}

export function useCreateReview() {
  const invalidate = useInvalidate(reviewKeys.all);
  return useMutation({
    mutationFn: (body: { year: number; week: number }) =>
      unwrap(api.POST("/reviews", { body })),
    onSuccess: invalidate,
  });
}

export function useApproveReview() {
  const invalidate = useInvalidate(reviewKeys.all);
  return useMutation({
    mutationFn: (id: number) =>
      unwrap(api.POST("/reviews/{review_id}/approve", { params: { path: { review_id: id } } })),
    onSuccess: invalidate,
  });
}

export function useReviewSettings() {
  return useQuery({
    queryKey: reviewKeys.settings,
    queryFn: () => unwrap(api.GET("/settings/review")),
  });
}

export function useSaveReviewSettings() {
  const invalidate = useInvalidate(reviewKeys.settings);
  return useMutation({
    mutationFn: (body: ReviewSettingsBody) => unwrap(api.PUT("/settings/review", { body })),
    onSuccess: invalidate,
  });
}
```

En `frontend/vitest.config.ts`, agregar `"src/lib/api/reviews.ts"` a `coverage.exclude`
(los hooks, como `attendance.ts` y `config.ts`, se prueban a través de los componentes).

- [ ] **Step 4: Run checks**

Run: `npm test -- src/lib/dates.test.ts && npm run typecheck && npm run lint`
Expected: PASS; sin errores de tipos (si `typecheck` falla en `reviews.ts`, los tipos
generados no coinciden con el Plan A: regenerar con el backend reconstruido).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api/schema.d.ts frontend/src/lib/api/types.ts frontend/src/lib/api/reviews.ts frontend/src/lib/review.ts frontend/src/lib/dates.ts frontend/src/lib/dates.test.ts frontend/vitest.config.ts
git commit -m "feat: add review API hooks and ISO week helpers

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Etiquetas y helpers de la revisión (`lib/review.ts`)

**Files:**
- Modify: `frontend/src/lib/review.ts`
- Test: `frontend/src/lib/review.test.ts`

**Interfaces:**
- Consumes: tipos de Task 1; `formatDate` y `WARNING_LABELS` existentes.
- Produces:
  - `FINDING_LABELS`, `PRIORITY_LABELS`, `PRIORITY_ORDER`, `ACTION_LABELS`,
    `STATUS_LABELS`, `TRIGGER_LABELS`.
  - `isInProgress(status)`, `canApprove(status)`.
  - `describeFacts(finding: FindingOut): string`, `formatDays(days: string[]): string`.
  - `ReviewEntry = { finding: FindingOut; item: NarrativeItemOut | null }` y
    `groupByPriority(findings, items | null): { priority: Priority | null; entries: ReviewEntry[] }[]`
    — sin narrativa, un solo grupo con `priority: null`.
  - `actionHref(finding, weekMonday): string | null` — `CONFIG_WARNING` →
    `/configuracion`; con empleado y días → `/semana?desde=<lunes>&empleado=<id>&dia=<día>`
    usando el primer día **dentro** de la semana revisada; si no, `null`.
  - `actionLabel(finding, item): string`.

- [ ] **Step 1: Write the failing tests**

`frontend/src/lib/review.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import type { FindingOut, NarrativeItemOut } from "@/lib/api/types";

import {
  actionHref,
  actionLabel,
  canApprove,
  describeFacts,
  formatDays,
  groupByPriority,
  isInProgress,
} from "./review";

const MONDAY = "2026-09-21";

function finding(overrides: Partial<FindingOut>): FindingOut {
  return {
    id: "ABSENT_NO_EXCEPTION:7:2026-09-23",
    kind: "ABSENT_NO_EXCEPTION",
    employee_id: 7,
    employee_name: "EMPLEADO G",
    days: ["2026-09-23"],
    facts: {},
    ...overrides,
  };
}

function item(findingId: string, overrides: Partial<NarrativeItemOut> = {}): NarrativeItemOut {
  return {
    finding_id: findingId,
    priority: "HIGH",
    explanation: "Revisar.",
    suggested_action: "JUSTIFY",
    ...overrides,
  };
}

describe("review helpers", () => {
  it("knows which statuses are in progress or approvable", () => {
    expect(isInProgress("QUEUED")).toBe(true);
    expect(isInProgress("READY")).toBe(false);
    expect(canApprove("READY_NO_NARRATIVE")).toBe(true);
    expect(canApprove("APPROVED")).toBe(false);
  });

  it("describes facts in Spanish", () => {
    expect(describeFacts(finding({ facts: { checkin_time: "16:45" } }))).toBe("checó 16:45");
    expect(
      describeFacts(finding({ facts: { late_this_week: 2, unjustified_this_week: 1, weeks_with_late: 3 } })),
    ).toBe("2 retardos esta semana · 1 sin justificar · 3 de las últimas 5 semanas con retardo");
    expect(describeFacts(finding({ facts: { code: "NO_REST_RULE", occurrences: 4 } }))).toBe(
      "Sin regla de descanso · 4 veces",
    );
  });

  it("formats day lists and long ranges", () => {
    expect(formatDays(["2026-09-23"])).toBe("23/09/2026");
    expect(formatDays(["2026-09-21", "2026-09-22", "2026-09-23", "2026-09-24"])).toBe(
      "21/09/2026 – 24/09/2026 (4 días)",
    );
  });

  it("groups findings by priority in order", () => {
    const high = finding({ id: "a" });
    const low = finding({ id: "b", kind: "CONFIG_WARNING" });
    const groups = groupByPriority([low, high], [item("b", { priority: "LOW" }), item("a")]);
    expect(groups.map((g) => [g.priority, g.entries.map((e) => e.finding.id)])).toEqual([
      ["HIGH", ["a"]],
      ["LOW", ["b"]],
    ]);
  });

  it("keeps every finding in one group when there is no narrative", () => {
    const groups = groupByPriority([finding({ id: "a" }), finding({ id: "b" })], null);
    expect(groups).toHaveLength(1);
    expect(groups[0].priority).toBeNull();
    expect(groups[0].entries.every((e) => e.item === null)).toBe(true);
  });

  it("links a finding to its day panel inside the reviewed week", () => {
    expect(actionHref(finding({}), MONDAY)).toBe(
      "/semana?desde=2026-09-21&empleado=7&dia=2026-09-23",
    );
    // Review Focus #1: a streak that began last week opens a day of this week.
    const streak = finding({ kind: "NO_CHECKIN_STREAK", days: ["2026-09-20", "2026-09-21"] });
    expect(actionHref(streak, MONDAY)).toBe("/semana?desde=2026-09-21&empleado=7&dia=2026-09-21");
    expect(actionHref(finding({ kind: "CONFIG_WARNING", employee_id: null, days: [] }), MONDAY)).toBe(
      "/configuracion",
    );
    expect(actionHref(finding({ employee_id: null }), MONDAY)).toBeNull();
  });

  it("labels the action button", () => {
    expect(actionLabel(finding({}), item("x"))).toBe("Justificar");
    expect(actionLabel(finding({}), item("x", { suggested_action: "NONE" }))).toBe("Ver día");
    expect(actionLabel(finding({}), null)).toBe("Ver día");
    expect(actionLabel(finding({ kind: "CONFIG_WARNING" }), null)).toBe("Ir a configuración");
  });
});
```

Run: `npm test -- src/lib/review.test.ts`
Expected: FAIL (funciones no exportadas).

- [ ] **Step 2: Implement**

Reemplazar `frontend/src/lib/review.ts` completo:

```ts
import type {
  FindingKind,
  FindingOut,
  NarrativeItemOut,
  Priority,
  ReviewStatus,
  ReviewTrigger,
  SuggestedAction,
  WarningCode,
} from "@/lib/api/types";

import { formatDate } from "./dates";
import { WARNING_LABELS } from "./labels";

export const FINDING_LABELS: Record<FindingKind, string> = {
  REST_DAY_CHECKIN: "Checada en día de descanso",
  ABSENT_NO_EXCEPTION: "Falta sin justificar",
  NO_CHECKIN_STREAK: "Varios días sin checar",
  REPEATED_LATE: "Retardos repetidos",
  CONFIG_WARNING: "Aviso de configuración",
};

export const PRIORITY_LABELS: Record<Priority, string> = { HIGH: "Alta", MEDIUM: "Media", LOW: "Baja" };
export const PRIORITY_ORDER: Priority[] = ["HIGH", "MEDIUM", "LOW"];

export const ACTION_LABELS: Record<SuggestedAction, string> = {
  JUSTIFY: "Justificar",
  REST_SWAP: "Registrar cambio de descanso",
  ADD_EXCEPTION: "Registrar excepción",
  FIX_CONFIG: "Corregir configuración",
  NONE: "",
};

export const STATUS_LABELS: Record<ReviewStatus, string> = {
  QUEUED: "En cola",
  RUNNING: "Generando",
  READY: "Listo",
  READY_NO_NARRATIVE: "Listo sin redacción",
  FAILED: "Falló",
  APPROVED: "Aprobado",
};

export const TRIGGER_LABELS: Record<ReviewTrigger, string> = {
  THURSDAY: "Jueves",
  MONDAY: "Lunes",
  MANUAL: "Manual",
};

export function isInProgress(status: ReviewStatus): boolean {
  return status === "QUEUED" || status === "RUNNING";
}

export function canApprove(status: ReviewStatus): boolean {
  return status === "READY" || status === "READY_NO_NARRATIVE";
}

const FACTS: Record<string, (value: number | string) => string> = {
  checkin_time: (v) => `checó ${v}`,
  days: (v) => `${v} días`,
  late_this_week: (v) => `${v} retardos esta semana`,
  unjustified_this_week: (v) => `${v} sin justificar`,
  weeks_with_late: (v) => `${v} de las últimas 5 semanas con retardo`,
  occurrences: (v) => `${v} veces`,
};

export function describeFacts(finding: FindingOut): string {
  const code = finding.facts.code;
  const warning = typeof code === "string" && code in WARNING_LABELS ? [WARNING_LABELS[code as WarningCode]] : [];
  const described = Object.entries(finding.facts)
    .filter(([key]) => key in FACTS)
    .map(([key, value]) => FACTS[key](value));
  return [...warning, ...described].join(" · ");
}

export function formatDays(days: string[]): string {
  if (days.length <= 3) return days.map(formatDate).join(", ");
  return `${formatDate(days[0])} – ${formatDate(days[days.length - 1])} (${days.length} días)`;
}

export type ReviewEntry = { finding: FindingOut; item: NarrativeItemOut | null };
export type ReviewGroup = { priority: Priority | null; entries: ReviewEntry[] };

export function groupByPriority(findings: FindingOut[], items: NarrativeItemOut[] | null): ReviewGroup[] {
  if (items === null) {
    return [{ priority: null, entries: findings.map((finding) => ({ finding, item: null })) }];
  }
  const byId = new Map(items.map((entry) => [entry.finding_id, entry]));
  return PRIORITY_ORDER.map((priority) => ({
    priority,
    entries: findings
      .filter((finding) => byId.get(finding.id)?.priority === priority)
      .map((finding) => ({ finding, item: byId.get(finding.id) ?? null })),
  })).filter((group) => group.entries.length > 0);
}

export function actionHref(finding: FindingOut, weekMonday: string): string | null {
  if (finding.kind === "CONFIG_WARNING") return "/configuracion";
  if (finding.employee_id === null || finding.days.length === 0) return null;
  const day = finding.days.find((d) => d >= weekMonday) ?? finding.days[finding.days.length - 1];
  return `/semana?desde=${weekMonday}&empleado=${finding.employee_id}&dia=${day}`;
}

export function actionLabel(finding: FindingOut, item: NarrativeItemOut | null): string {
  const suggested = item ? ACTION_LABELS[item.suggested_action] : "";
  if (suggested) return suggested;
  return finding.kind === "CONFIG_WARNING" ? "Ir a configuración" : "Ver día";
}
```

- [ ] **Step 3: Run tests and checks**

Run: `npm test -- src/lib/review.test.ts && npm run lint && npm run typecheck`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/review.ts frontend/src/lib/review.test.ts
git commit -m "feat: add weekly review labels and helpers

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Componentes del borrador (`FindingCard`, `ReviewDetail`)

**Files:**
- Create: `frontend/src/components/review/finding-card.tsx`
- Create: `frontend/src/components/review/review-detail.tsx`
- Test: `frontend/src/components/review/review-detail.test.tsx`

**Interfaces:**
- Consumes: helpers de Task 2; `useApproveReview` (Task 1); `RhTable` existente (acepta
  `ProposedRowOut`, que tiene la misma forma que `RhRowOut`); `FormError`.
- Produces:
  - `FindingCard({ finding, item, weekMonday })` — `<li>` con tipo, empleado, días,
    cifras, explicación y botón-enlace.
  - `ReviewDetail({ review, weekMonday, onRegenerate, regenerating })` — encabezado con
    estado y botones **Generar de nuevo** / **Aprobar** (solo si `canApprove`), aviso de
    `stale`, resumen o aviso de "sin redacción", grupos por prioridad y **Lista para RH**.

- [ ] **Step 1: Write the failing tests**

`frontend/src/components/review/review-detail.test.tsx`:

```tsx
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ReviewDetailOut } from "@/lib/api/types";

import { ReviewDetail } from "./review-detail";

const approve = vi.fn();

vi.mock("@/lib/api/reviews", () => ({
  useApproveReview: () => ({ mutate: approve, error: null, isPending: false }),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const ABSENT = "ABSENT_NO_EXCEPTION:7:2026-09-23";
const CONFIG = "CONFIG_WARNING/MISSING_RH_NAME:7:-";

function review(overrides: Partial<ReviewDetailOut> = {}): ReviewDetailOut {
  return {
    id: 5,
    year: 2026,
    week: 39,
    trigger: "THURSDAY",
    status: "READY",
    created_at: "2026-09-24T23:30:00Z",
    as_of: "2026-09-24T17:30:00",
    approved_at: null,
    error: null,
    findings: [
      { id: ABSENT, kind: "ABSENT_NO_EXCEPTION", employee_id: 7, employee_name: "EMPLEADO G", days: ["2026-09-23"], facts: {} },
      { id: CONFIG, kind: "CONFIG_WARNING", employee_id: 7, employee_name: "EMPLEADO G", days: [], facts: { code: "MISSING_RH_NAME", occurrences: 1 } },
    ],
    narrative: {
      summary: "Una falta de EMPLEADO G sin justificar.",
      items: [
        { finding_id: ABSENT, priority: "HIGH", explanation: "EMPLEADO G faltó el miércoles.", suggested_action: "JUSTIFY" },
        { finding_id: CONFIG, priority: "LOW", explanation: "Falta su nombre en RH.", suggested_action: "FIX_CONFIG" },
      ],
    },
    rh_rows: [{ employee_id: 7, name: "EMPLEADO G", day: "2026-09-23", rh_type: "FALTA_INJUSTIFICADA", comment: "" }],
    model: "claude-opus-5-5",
    input_tokens: 900,
    output_tokens: 150,
    stale: false,
    ...overrides,
  };
}

function renderDetail(data: ReviewDetailOut, onRegenerate = vi.fn()) {
  render(<ReviewDetail review={data} weekMonday="2026-09-21" onRegenerate={onRegenerate} regenerating={false} />);
  return onRegenerate;
}

describe("ReviewDetail", () => {
  beforeEach(() => approve.mockReset());

  it("shows the summary and findings grouped by priority with their actions", () => {
    renderDetail(review());
    expect(screen.getByText("Una falta de EMPLEADO G sin justificar.")).toBeInTheDocument();
    const high = screen.getByRole("region", { name: "Prioridad alta" });
    expect(within(high).getByText("EMPLEADO G faltó el miércoles.")).toBeInTheDocument();
    expect(within(high).getByRole("link", { name: "Justificar" })).toHaveAttribute(
      "href",
      "/semana?desde=2026-09-21&empleado=7&dia=2026-09-23",
    );
    const low = screen.getByRole("region", { name: "Prioridad baja" });
    expect(within(low).getByText(/Falta nombre en RH · 1 veces/)).toBeInTheDocument();
    expect(within(low).getByRole("link", { name: "Corregir configuración" })).toHaveAttribute(
      "href",
      "/configuracion",
    );
  });

  it("lists the RH rows", () => {
    renderDetail(review());
    expect(screen.getByRole("heading", { name: "Lista para RH" })).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /EMPLEADO G/ })).toHaveTextContent("Falta injustificada");
  });

  it("shows findings and the reason when there is no narrative", () => {
    // Review Focus #3
    renderDetail(review({ status: "READY_NO_NARRATIVE", narrative: null, error: "Falta ANTHROPIC_API_KEY" }));
    expect(screen.getByRole("status")).toHaveTextContent(/no pudo redactar.*Falta ANTHROPIC_API_KEY/);
    const all = screen.getByRole("region", { name: "Hallazgos" });
    expect(within(all).getByRole("link", { name: "Ver día" })).toBeInTheDocument();
    expect(within(all).getByRole("link", { name: "Ir a configuración" })).toBeInTheDocument();
  });

  it("warns when the data changed", () => {
    renderDetail(review({ stale: true }));
    expect(screen.getByRole("status")).toHaveTextContent("Los datos cambiaron desde este borrador");
  });

  it("approves a ready draft and regenerates", async () => {
    const onRegenerate = renderDetail(review());
    await userEvent.click(screen.getByRole("button", { name: "Aprobar" }));
    expect(approve).toHaveBeenCalledWith(5, expect.anything());
    await userEvent.click(screen.getByRole("button", { name: "Generar de nuevo" }));
    expect(onRegenerate).toHaveBeenCalled();
  });

  it("shows when it was approved and hides the approve button", () => {
    renderDetail(review({ status: "APPROVED", approved_at: "2026-09-24T18:05:00" }));
    expect(screen.queryByRole("button", { name: "Aprobar" })).not.toBeInTheDocument();
    expect(screen.getByText(/aprobado el 24\/09\/2026 18:05/)).toBeInTheDocument();
  });

  it("says when the week has no findings", () => {
    renderDetail(review({ findings: [], narrative: { summary: "Semana sin pendientes.", items: [] }, rh_rows: [] }));
    expect(screen.getByText("Sin hallazgos esta semana.")).toBeInTheDocument();
  });
});
```

Run: `npm test -- src/components/review`
Expected: FAIL (módulo `./review-detail` no existe).

- [ ] **Step 2: Implement the components**

`frontend/src/components/review/finding-card.tsx`:

```tsx
import Link from "next/link";

import { Button } from "@/components/ui/button";
import type { FindingOut, NarrativeItemOut } from "@/lib/api/types";
import { FINDING_LABELS, actionHref, actionLabel, describeFacts, formatDays } from "@/lib/review";

type Props = { finding: FindingOut; item: NarrativeItemOut | null; weekMonday: string };

export function FindingCard({ finding, item, weekMonday }: Props) {
  const title = `${FINDING_LABELS[finding.kind]}${finding.employee_name ? ` · ${finding.employee_name}` : ""}`;
  const facts = describeFacts(finding);
  const href = actionHref(finding, weekMonday);
  return (
    <li className="space-y-1 rounded-lg border p-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="font-medium">{title}</p>
        {finding.days.length > 0 && (
          <p className="text-xs text-muted-foreground">{formatDays(finding.days)}</p>
        )}
      </div>
      {facts && <p className="text-sm text-muted-foreground">{facts}</p>}
      {item && <p className="text-sm">{item.explanation}</p>}
      {href && (
        <Button asChild variant="outline" size="sm">
          <Link href={href}>{actionLabel(finding, item)}</Link>
        </Button>
      )}
    </li>
  );
}
```

`frontend/src/components/review/review-detail.tsx`:

```tsx
"use client";

import { toast } from "sonner";

import { RhTable } from "@/components/attendance/rh-table";
import { FormError } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { useApproveReview } from "@/lib/api/reviews";
import type { ReviewDetailOut } from "@/lib/api/types";
import { formatDateTime } from "@/lib/dates";
import { PRIORITY_LABELS, STATUS_LABELS, canApprove, groupByPriority } from "@/lib/review";

import { FindingCard } from "./finding-card";

type Props = {
  review: ReviewDetailOut;
  weekMonday: string;
  onRegenerate: () => void;
  regenerating: boolean;
};

export function ReviewDetail({ review, weekMonday, onRegenerate, regenerating }: Props) {
  const approve = useApproveReview();
  const groups = groupByPriority(review.findings, review.narrative?.items ?? null);
  const approvedAt = review.approved_at ? ` · aprobado el ${formatDateTime(review.approved_at)}` : "";
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">
          {STATUS_LABELS[review.status]} · datos al {formatDateTime(review.as_of)}
          {approvedAt}
        </p>
        <div className="flex gap-2">
          <Button variant="outline" onClick={onRegenerate} disabled={regenerating}>
            Generar de nuevo
          </Button>
          {canApprove(review.status) && (
            <Button
              disabled={approve.isPending}
              onClick={() => approve.mutate(review.id, { onSuccess: () => toast.success("Borrador aprobado") })}
            >
              Aprobar
            </Button>
          )}
        </div>
      </div>
      <FormError error={approve.error} />
      {review.stale && (
        <div role="status" className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm">
          Los datos cambiaron desde este borrador. Genera uno nuevo para verlos.
        </div>
      )}
      {review.narrative ? (
        <p className="whitespace-pre-line">{review.narrative.summary}</p>
      ) : (
        <div role="status" className="rounded-lg border p-3 text-sm">
          El agente no pudo redactar este borrador{review.error ? `: ${review.error}` : "."} Los
          hallazgos y la lista para RH están completos.
        </div>
      )}
      {review.findings.length === 0 ? (
        <p className="text-sm text-muted-foreground">Sin hallazgos esta semana.</p>
      ) : (
        groups.map((group) => {
          const label = group.priority ? `Prioridad ${PRIORITY_LABELS[group.priority].toLowerCase()}` : "Hallazgos";
          return (
            <section key={group.priority ?? "all"} aria-label={label} className="space-y-2">
              <h3 className="font-medium">{label}</h3>
              <ul className="space-y-2">
                {group.entries.map(({ finding, item }) => (
                  <FindingCard key={finding.id} finding={finding} item={item} weekMonday={weekMonday} />
                ))}
              </ul>
            </section>
          );
        })
      )}
      <section className="space-y-2">
        <h3 className="font-medium">Lista para RH</h3>
        <RhTable rows={review.rh_rows} />
      </section>
    </div>
  );
}
```

- [ ] **Step 3: Run tests and checks**

Run: `npm test -- src/components/review && npm run lint && npm run typecheck`
Expected: PASS. (Si `getByRole("status")` encuentra dos elementos en el caso
`stale` + sin narrativa, no aplica a estos tests: cada test activa solo uno.)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/review/finding-card.tsx frontend/src/components/review/review-detail.tsx frontend/src/components/review/review-detail.test.tsx
git commit -m "feat: show weekly review drafts grouped by priority

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Vista `/revision` (semana, generar, sondeo e historial) y menú

**Files:**
- Create: `frontend/src/components/review/review-view.tsx`
- Create: `frontend/src/app/(app)/revision/page.tsx`
- Modify: `frontend/src/components/app-shell.tsx`
- Test: `frontend/src/components/review/review-view.test.tsx`

**Interfaces:**
- Consumes: `useWeekReviews`, `useReview`, `useCreateReview` (Task 1); `ReviewDetail`
  (Task 3); `PeriodNav`, `useEnsurePeriod`, `Loading`, `QueryError`, `FormError`.
- Produces:
  - `ReviewView({ requestedStart })` — sin `?desde`, redirige a la semana actual (como
    `/semana`).
  - `WeekReviews({ monday })` (exportado para pruebas): navegación de semanas;
    **Generar borrador** si no hay ninguno; el más reciente con su estado; historial.
  - `LatestReview` usa el estado del **detalle** cuando ya llegó (Review Focus #2).
  - Página `/revision?desde=YYYY-MM-DD` y enlace **Revisión** en el menú (entre
    "Incidencias" y "Mes").

- [ ] **Step 1: Write the failing tests**

`frontend/src/components/review/review-view.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ReviewDetailOut, ReviewSummaryOut } from "@/lib/api/types";

import { WeekReviews } from "./review-view";

const create = vi.fn();
const state: { list: ReviewSummaryOut[]; detail: ReviewDetailOut | undefined } = {
  list: [],
  detail: undefined,
};

vi.mock("@/lib/api/reviews", () => ({
  useWeekReviews: () => ({ data: state.list, isPending: false, isError: false }),
  useReview: () => ({ data: state.detail, isPending: state.detail === undefined, isError: false }),
  useCreateReview: () => ({ mutate: create, error: null, isPending: false }),
  useApproveReview: () => ({ mutate: vi.fn(), error: null, isPending: false }),
}));
vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: ReactNode }) => <a href={href}>{children}</a>,
}));

function summary(overrides: Partial<ReviewSummaryOut> = {}): ReviewSummaryOut {
  return {
    id: 5,
    year: 2026,
    week: 39,
    trigger: "MANUAL",
    status: "READY",
    created_at: "2026-09-24T23:30:00Z",
    as_of: "2026-09-24T17:30:00",
    approved_at: null,
    error: null,
    ...overrides,
  };
}

function detail(overrides: Partial<ReviewDetailOut> = {}): ReviewDetailOut {
  return {
    ...summary(),
    findings: [],
    narrative: { summary: "Semana sin pendientes.", items: [] },
    rh_rows: [],
    model: "fake",
    input_tokens: 0,
    output_tokens: 0,
    stale: false,
    ...overrides,
  };
}

describe("WeekReviews", () => {
  beforeEach(() => {
    create.mockReset();
    state.list = [];
    state.detail = undefined;
  });

  it("offers to generate the first draft of the week", async () => {
    render(<WeekReviews monday="2026-09-21" />);
    expect(screen.getByText("Todavía no hay borrador para esta semana.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Generar borrador" }));
    expect(create).toHaveBeenCalledWith({ year: 2026, week: 39 }, expect.anything());
  });

  it("asks for ISO week 53 of 2026 at the end of December", async () => {
    // Review Focus #5
    render(<WeekReviews monday="2026-12-28" />);
    await userEvent.click(screen.getByRole("button", { name: "Generar borrador" }));
    expect(create).toHaveBeenCalledWith({ year: 2026, week: 53 }, expect.anything());
  });

  it("shows progress while the draft is generated", () => {
    state.list = [summary({ status: "RUNNING", as_of: null })];
    render(<WeekReviews monday="2026-09-21" />);
    expect(screen.getByRole("status")).toHaveTextContent("Generando borrador");
  });

  it("trusts the detail when the list is behind", () => {
    // Review Focus #2
    state.list = [summary({ status: "RUNNING" })];
    state.detail = detail();
    render(<WeekReviews monday="2026-09-21" />);
    expect(screen.getByText("Semana sin pendientes.")).toBeInTheDocument();
  });

  it("explains a failed run and lets the manager retry", async () => {
    state.list = [summary({ status: "FAILED", error: "No se pudo leer SoftRestaurant. Revisa Tailscale." })];
    state.detail = detail({ status: "FAILED", narrative: null, error: "No se pudo leer SoftRestaurant. Revisa Tailscale." });
    render(<WeekReviews monday="2026-09-21" />);
    expect(screen.getByRole("alert")).toHaveTextContent("No se pudo leer SoftRestaurant");
    await userEvent.click(screen.getByRole("button", { name: "Intentar de nuevo" }));
    expect(create).toHaveBeenCalled();
  });

  it("lists earlier drafts of the week", () => {
    state.list = [summary({ id: 6 }), summary({ id: 5, trigger: "THURSDAY", status: "APPROVED" })];
    state.detail = detail({ id: 6 });
    render(<WeekReviews monday="2026-09-21" />);
    expect(screen.getByText("Borradores anteriores de esta semana (1)")).toBeInTheDocument();
    expect(screen.getByText(/Jueves · Aprobado · datos al 24\/09\/2026 17:30/)).toBeInTheDocument();
  });
});
```

Run: `npm test -- src/components/review/review-view.test.tsx`
Expected: FAIL (módulo no existe).

- [ ] **Step 2: Implement the view, the page and the menu link**

`frontend/src/components/review/review-view.tsx`:

```tsx
"use client";

import { useCallback } from "react";
import { toast } from "sonner";

import { FormError, Loading, QueryError } from "@/components/feedback";
import { PeriodNav } from "@/components/period-nav";
import { Button } from "@/components/ui/button";
import { useCreateReview, useReview, useWeekReviews } from "@/lib/api/reviews";
import type { ReviewSummaryOut } from "@/lib/api/types";
import { addDays, formatDate, formatDateTime, isoWeekNumber, isoWeekYear, weekStart } from "@/lib/dates";
import { useEnsurePeriod } from "@/lib/period";
import { STATUS_LABELS, TRIGGER_LABELS, isInProgress } from "@/lib/review";

import { ReviewDetail } from "./review-detail";

export function ReviewView({ requestedStart }: { requestedStart: string | null }) {
  const buildQuery = useCallback((today: string) => `desde=${weekStart(today)}`, []);
  useEnsurePeriod(requestedStart, buildQuery);
  if (requestedStart === null) return <Loading />;
  return <WeekReviews monday={weekStart(requestedStart)} />;
}

export function WeekReviews({ monday }: { monday: string }) {
  const year = isoWeekYear(monday);
  const week = isoWeekNumber(monday);
  const reviews = useWeekReviews(year, week);
  const create = useCreateReview();
  const latest = reviews.data?.[0] ?? null;
  const generate = () =>
    create.mutate({ year, week }, { onSuccess: () => toast.success("Generando borrador…") });
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <PeriodNav
          label={`Semana ${week} · ${formatDate(monday)} – ${formatDate(addDays(monday, 6))}`}
          previousHref={`/revision?desde=${addDays(monday, -7)}`}
          nextHref={`/revision?desde=${addDays(monday, 7)}`}
        />
        {reviews.data && !latest && (
          <Button onClick={generate} disabled={create.isPending}>
            Generar borrador
          </Button>
        )}
      </div>
      <FormError error={create.error} />
      {reviews.isPending && <Loading />}
      {reviews.isError && <QueryError error={reviews.error} onRetry={() => reviews.refetch()} />}
      {reviews.data?.length === 0 && (
        <p className="text-sm text-muted-foreground">Todavía no hay borrador para esta semana.</p>
      )}
      {latest && (
        <LatestReview summary={latest} monday={monday} onRegenerate={generate} busy={create.isPending} />
      )}
      {reviews.data && reviews.data.length > 1 && <History reviews={reviews.data.slice(1)} />}
    </div>
  );
}

type LatestProps = {
  summary: ReviewSummaryOut;
  monday: string;
  onRegenerate: () => void;
  busy: boolean;
};

function LatestReview({ summary, monday, onRegenerate, busy }: LatestProps) {
  const detail = useReview(summary.id);
  const status = detail.data?.status ?? summary.status;
  if (isInProgress(status)) {
    return (
      <p role="status" className="text-sm">
        Generando borrador… ({STATUS_LABELS[status].toLowerCase()})
      </p>
    );
  }
  if (status === "FAILED") {
    return (
      <div role="alert" className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm">
        <span>No se pudo generar el borrador: {detail.data?.error ?? summary.error}</span>
        <Button variant="outline" size="sm" onClick={onRegenerate} disabled={busy}>
          Intentar de nuevo
        </Button>
      </div>
    );
  }
  if (detail.isError) return <QueryError error={detail.error} onRetry={() => detail.refetch()} />;
  if (!detail.data) return <Loading />;
  return <ReviewDetail review={detail.data} weekMonday={monday} onRegenerate={onRegenerate} regenerating={busy} />;
}

function History({ reviews }: { reviews: ReviewSummaryOut[] }) {
  return (
    <details className="text-sm">
      <summary className="cursor-pointer text-muted-foreground">
        Borradores anteriores de esta semana ({reviews.length})
      </summary>
      <ul className="mt-2 space-y-1">
        {reviews.map((review) => (
          <li key={review.id}>
            {TRIGGER_LABELS[review.trigger]} · {STATUS_LABELS[review.status]}
            {review.as_of && ` · datos al ${formatDateTime(review.as_of)}`}
          </li>
        ))}
      </ul>
    </details>
  );
}
```

`frontend/src/app/(app)/revision/page.tsx`:

```tsx
import { ReviewView } from "@/components/review/review-view";
import { isIsoDate } from "@/lib/dates";

type Props = { searchParams: Promise<{ desde?: string }> };

export default async function RevisionPage({ searchParams }: Props) {
  const { desde } = await searchParams;
  return <ReviewView requestedStart={isIsoDate(desde) ? desde : null} />;
}
```

En `frontend/src/components/app-shell.tsx`, `LINKS` pasa a:

```tsx
const LINKS = [
  { href: "/semana", label: "Semana" },
  { href: "/incidencias", label: "Incidencias" },
  { href: "/revision", label: "Revisión" },
  { href: "/mes", label: "Mes" },
  { href: "/configuracion", label: "Configuración" },
] as const;
```

- [ ] **Step 3: Run tests and checks**

Run: `npm test && npm run lint && npm run typecheck`
Expected: PASS (todos, incluidos los de la Etapa 1).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/review/review-view.tsx frontend/src/components/review/review-view.test.tsx "frontend/src/app/(app)/revision/page.tsx" frontend/src/components/app-shell.tsx
git commit -m "feat: add weekly review page with on-demand generation

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Enlace directo al panel del día en `/semana`

**Files:**
- Modify: `frontend/src/components/attendance/week-grid.tsx` (+ `findDaySelection`)
- Modify: `frontend/src/components/attendance/week-view.tsx`
- Modify: `frontend/src/app/(app)/semana/page.tsx`
- Test: `frontend/src/components/attendance/week-grid.test.tsx`

**Interfaces:**
- Consumes: `CalendarOut`, `DaySelection`, `DayPanel` existentes.
- Produces:
  - `findDaySelection(calendar: CalendarOut, employeeId: number, day: string): DaySelection | null`.
  - `WeekView({ requestedStart, focus })` con `focus: { employeeId: number; day: string } | null`:
    al cargar el calendario abre el panel de ese día; al cerrarlo no se vuelve a abrir.
    Sin `useEffect` (estado derivado), para no pelear con la regla de lint de React.
  - `/semana?desde=…&empleado=<id>&dia=<YYYY-MM-DD>`; valores inválidos se ignoran.

- [ ] **Step 1: Write the failing tests**

Agregar a `frontend/src/components/attendance/week-grid.test.tsx` (y `findDaySelection`
al import de `./week-grid`):

```tsx
describe("findDaySelection", () => {
  it("finds the employee and day of a deep link", () => {
    expect(findDaySelection(calendar, 1, "2026-09-21")).toEqual({
      day: calendar.days[0],
      employee: calendar.employees[0],
    });
  });

  it("ignores unknown employees and days outside the calendar", () => {
    // Review Focus #4
    expect(findDaySelection(calendar, 99, "2026-09-21")).toBeNull();
    expect(findDaySelection(calendar, 1, "2026-10-05")).toBeNull();
  });
});
```

Run: `npm test -- src/components/attendance/week-grid.test.tsx`
Expected: FAIL (`findDaySelection` no existe).

- [ ] **Step 2: Implement**

En `frontend/src/components/attendance/week-grid.tsx`, después del tipo `DaySelection`:

```tsx
export function findDaySelection(
  calendar: CalendarOut,
  employeeId: number,
  day: string,
): DaySelection | null {
  const employee = calendar.employees.find((e) => e.id === employeeId);
  const found = calendar.days.find((d) => d.employee_id === employeeId && d.day === day);
  return employee && found ? { day: found, employee } : null;
}
```

En `frontend/src/components/attendance/week-view.tsx`:

```tsx
export type DayFocus = { employeeId: number; day: string };

export function WeekView({
  requestedStart,
  focus = null,
}: {
  requestedStart: string | null;
  focus?: DayFocus | null;
}) {
  const buildQuery = useCallback((today: string) => `desde=${weekStart(today)}`, []);
  useEnsurePeriod(requestedStart, buildQuery);
  if (requestedStart === null) return <Loading />;
  return <Week from={weekStart(requestedStart)} focus={focus} />;
}

function Week({ from, focus }: { from: string; focus: DayFocus | null }) {
  const to = addDays(from, 6);
  const calendar = useCalendar(from, to);
  const [selection, setSelection] = useState<DaySelection | null>(null);
  const [focusDismissed, setFocusDismissed] = useState(false);
  const focused =
    !focusDismissed && focus && calendar.data
      ? findDaySelection(calendar.data, focus.employeeId, focus.day)
      : null;
  function close() {
    setSelection(null);
    setFocusDismissed(true);
  }
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <PeriodNav
          label={`Semana ${isoWeekNumber(from)} · ${formatDate(from)} – ${formatDate(to)}`}
          previousHref={`/semana?desde=${addDays(from, -7)}`}
          nextHref={`/semana?desde=${addDays(from, 7)}`}
        />
        <ExportButton from={from} to={to} group="week" />
      </div>
      {calendar.isPending && <Loading />}
      {calendar.isError && <QueryError error={calendar.error} onRetry={() => calendar.refetch()} />}
      {calendar.data && (
        <>
          <WarningsList warnings={calendar.data.warnings} />
          <WeekGrid
            calendar={calendar.data}
            onSelect={(day, employee) => setSelection({ day, employee })}
          />
          <Legend />
        </>
      )}
      <DayPanel selection={selection ?? focused} onClose={close} />
    </div>
  );
}
```

El import de `./week-grid` pasa a
`import { type DaySelection, findDaySelection, WeekGrid } from "./week-grid";`; los
demás imports del archivo no cambian.

`frontend/src/app/(app)/semana/page.tsx`:

```tsx
import { WeekView } from "@/components/attendance/week-view";
import { isIsoDate } from "@/lib/dates";

type Props = { searchParams: Promise<{ desde?: string; empleado?: string; dia?: string }> };

function parseFocus(empleado: string | undefined, dia: string | undefined) {
  const employeeId = Number(empleado);
  if (!Number.isInteger(employeeId) || employeeId <= 0 || !isIsoDate(dia)) return null;
  return { employeeId, day: dia };
}

export default async function SemanaPage({ searchParams }: Props) {
  const { desde, empleado, dia } = await searchParams;
  return (
    <WeekView requestedStart={isIsoDate(desde) ? desde : null} focus={parseFocus(empleado, dia)} />
  );
}
```

- [ ] **Step 3: Run tests and checks**

Run: `npm test && npm run lint && npm run typecheck`
Expected: PASS.

- [ ] **Step 4: Manual check in the browser**

Con el stack de demo levantado y sembrado (comando en CLAUDE.md, con
`REVIEW_AGENT=fake`), `npm run dev -- --port 3001`, entrar como demo y abrir
`http://127.0.0.1:3001/semana?desde=2026-09-21&empleado=2&dia=2026-09-23`.
Expected: se abre el panel del día de ese empleado; al cerrarlo no vuelve a abrirse; con
`empleado=999` la semana carga sin panel.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/attendance/week-grid.tsx frontend/src/components/attendance/week-grid.test.tsx frontend/src/components/attendance/week-view.tsx "frontend/src/app/(app)/semana/page.tsx"
git commit -m "feat: open the day panel from a week deep link

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Umbrales de la revisión en Configuración

**Files:**
- Create: `frontend/src/components/config/review-settings-tab.tsx`
- Modify: `frontend/src/components/config/config-view.tsx`
- Test: `frontend/src/components/config/review-settings-tab.test.tsx`

**Interfaces:**
- Consumes: `useReviewSettings`, `useSaveReviewSettings` (Task 1).
- Produces: pestaña **Revisión semanal** con tres campos numéricos (1–7, 1–7, 1–5) y
  botón **Guardar umbrales**.

- [ ] **Step 1: Write the failing test**

`frontend/src/components/config/review-settings-tab.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ReviewSettingsTab } from "./review-settings-tab";

const save = vi.fn();

vi.mock("@/lib/api/reviews", () => ({
  useReviewSettings: () => ({
    data: { streak_days: 2, late_week: 2, late_weeks: 3 },
    isPending: false,
    isError: false,
  }),
  useSaveReviewSettings: () => ({ mutate: save, error: null, isPending: false }),
}));

describe("ReviewSettingsTab", () => {
  it("shows the current thresholds and saves new ones", async () => {
    render(<ReviewSettingsTab />);
    const streak = screen.getByLabelText(/Días seguidos sin checar/);
    expect(streak).toHaveValue(2);
    expect(screen.getByLabelText(/Semanas con retardo/)).toHaveAttribute("max", "5");
    await userEvent.clear(streak);
    await userEvent.type(streak, "3");
    await userEvent.click(screen.getByRole("button", { name: "Guardar umbrales" }));
    expect(save).toHaveBeenCalledWith(
      { streak_days: 3, late_week: 2, late_weeks: 3 },
      expect.anything(),
    );
  });
});
```

Run: `npm test -- src/components/config/review-settings-tab.test.tsx`
Expected: FAIL (módulo no existe).

- [ ] **Step 2: Implement**

`frontend/src/components/config/review-settings-tab.tsx`:

```tsx
"use client";

import type { FormEvent } from "react";
import { toast } from "sonner";

import { FormError, Loading, QueryError } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useReviewSettings, useSaveReviewSettings } from "@/lib/api/reviews";

const FIELDS = [
  { name: "streak_days", label: "Días seguidos sin checar para marcar una racha", max: 7 },
  { name: "late_week", label: "Retardos sin justificar en la semana para marcar retardos repetidos", max: 7 },
  { name: "late_weeks", label: "Semanas con retardo (de las últimas 5) para marcar retardos repetidos", max: 5 },
] as const;

export function ReviewSettingsTab() {
  const settings = useReviewSettings();
  const save = useSaveReviewSettings();

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    save.mutate(
      {
        streak_days: Number(form.get("streak_days")),
        late_week: Number(form.get("late_week")),
        late_weeks: Number(form.get("late_weeks")),
      },
      { onSuccess: () => toast.success("Umbrales guardados") },
    );
  }

  if (settings.isPending) return <Loading />;
  if (settings.isError) return <QueryError error={settings.error} onRetry={() => settings.refetch()} />;
  return (
    <form onSubmit={onSubmit} className="grid max-w-md gap-3">
      <p className="text-sm text-muted-foreground">
        Cuándo el borrador semanal marca un hallazgo. Aplican al siguiente borrador que se genere.
      </p>
      {FIELDS.map((field) => (
        <div key={field.name} className="space-y-1">
          <Label htmlFor={field.name}>{field.label}</Label>
          <Input
            id={field.name}
            name={field.name}
            type="number"
            min={1}
            max={field.max}
            required
            defaultValue={settings.data[field.name]}
          />
        </div>
      ))}
      <FormError error={save.error} />
      <Button type="submit" disabled={save.isPending}>
        Guardar umbrales
      </Button>
    </form>
  );
}
```

En `frontend/src/components/config/config-view.tsx`, importar `ReviewSettingsTab` y
agregar la pestaña al final:

```tsx
        <TabsTrigger value="review">Revisión semanal</TabsTrigger>
```

```tsx
      <TabsContent value="review">
        <ReviewSettingsTab />
      </TabsContent>
```

- [ ] **Step 3: Run tests and checks**

Run: `npm test && npm run lint && npm run typecheck`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/config/review-settings-tab.tsx frontend/src/components/config/review-settings-tab.test.tsx frontend/src/components/config/config-view.tsx
git commit -m "feat: edit weekly review thresholds in settings

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: E2E, documentación y verificación final

**Files:**
- Create: `frontend/e2e/review.spec.ts`
- Modify: `CLAUDE.md`, `docs/plan.md`, `docs/specs/2026-10-01-etapa-2-revision-semanal-design.md`

**Interfaces:**
- Consumes: todo lo anterior; el stack de demo con `worker` y `REVIEW_AGENT=fake`
  (Plan A Task 15 y Task 17 ya agregan `REVIEW_AGENT: fake` al job `e2e` de CI).
- Produces: flujo E2E generar → leer → aprobar.

- [ ] **Step 1: Write the E2E test**

`frontend/e2e/review.spec.ts`:

```ts
import { expect, test } from "@playwright/test";

const USER = process.env.FAKE_AUTH_USER ?? "demo";
const PASSWORD = process.env.FAKE_AUTH_PASSWORD ?? "demo";

test("generate, read and approve the weekly draft", async ({ page }) => {
  await page.goto("/revision?desde=2026-09-21");
  await page.getByLabel("Usuario").fill(USER);
  await page.getByLabel("Contraseña").fill(PASSWORD);
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(/\/revision\?desde=2026-09-21/);

  // First run creates the draft; later runs (the demo DB persists) regenerate it.
  const generate = page.getByRole("button", { name: "Generar borrador" });
  const regenerate = page.getByRole("button", { name: "Generar de nuevo" });
  await expect(generate.or(regenerate)).toBeVisible();
  await ((await generate.isVisible()) ? generate : regenerate).click();

  // The worker polls every 10 s; the page polls every 3 s.
  await expect(page.getByRole("status").filter({ hasText: "Generando borrador" })).toBeVisible();
  await expect(page.getByText(/Borrador de demostración/)).toBeVisible({ timeout: 45_000 });
  await expect(page.getByRole("heading", { name: "Lista para RH" })).toBeVisible();

  await page.getByRole("button", { name: "Aprobar" }).click();
  await expect(page.getByText("Borrador aprobado")).toBeVisible();
  await expect(page.getByText(/aprobado el/)).toBeVisible();
});
```

- [ ] **Step 2: Run the E2E locally**

Desde la raíz del repo (stack de demo aislado; ver CLAUDE.md):

```bash
docker compose stop
SR_MODE=fake REVIEW_AGENT=fake docker compose -p tabernas-demo up -d --build --wait
SR_MODE=fake docker compose -p tabernas-demo run --rm backend python /scripts/seed_demo.py
cd frontend && npm run e2e
cd .. && docker compose -p tabernas-demo down -v && docker compose start
```

Expected: los dos archivos de `e2e/` pasan.

- [ ] **Step 3: Documentation**

1. `CLAUDE.md`, sección **Frontend layout**, agregar:

```markdown
- `lib/api/reviews.ts` — weekly-review hooks; drafts poll every 3 s only while `QUEUED`
  or `RUNNING`. `lib/review.ts` holds the review labels and pure helpers.
- `components/review/` — `/revision`: the latest draft of a week (summary, findings by
  priority with links to `/semana?desde&empleado&dia`, RH list, approve).
```

   y en **Status**, cuando el PR del Plan B esté en verde, cambiar la línea de la Etapa 2
   a: `Stage 2 (weekly review agent) is closed (<fecha>): backend (Plan A) and frontend
   (Plan B) merged with CI green.` (con la fecha real del merge).
2. `docs/plan.md`, estado de la Etapa 2: agregar el enlace al Plan B
   (`plans/2026-10-01-etapa-2-plan-b-frontend.md`) y, al cerrar, `cerrada el <fecha>`
   con los pendientes conocidos que hayan quedado.
3. `docs/specs/2026-10-01-etapa-2-revision-semanal-design.md`, línea de estado:
   `implementado` con la fecha, al cerrar.

- [ ] **Step 4: Full verification**

Run (desde `frontend/`):

```bash
npm run lint && npm run typecheck && npm test -- --coverage
```

Expected: todo en verde; umbrales de cobertura de `vitest.config.ts` (80%) cumplidos.

- [ ] **Step 5: Commit**

```bash
git add frontend/e2e/review.spec.ts CLAUDE.md docs/plan.md docs/specs/2026-10-01-etapa-2-revision-semanal-design.md
git commit -m "test: add weekly review E2E flow and document the review UI

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Commands

| Acción | Comando (desde `frontend/`) |
|---|---|
| Checks | `npm run lint && npm run typecheck && npm test` |
| Tipos de la API (backend corriendo) | `npm run gen:api` |
| Dev (si el frontend de Docker ocupa 3000) | `npm run dev -- --port 3001` |
| E2E (stack de demo arriba y sembrado) | `npm run e2e` |
