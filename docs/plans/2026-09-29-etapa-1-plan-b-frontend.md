# Etapa 1 · Plan B — Frontend de asistencia

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** UI en Next.js para ver la semana (planeado vs real), justificar, resolver
cambios de descanso, copiar la lista para RH, ver el resumen mensual, configurar
empleados/descansos/excepciones/horarios y exportar a Excel, detrás de un login falso.

**Architecture:** Next.js 16 (App Router) en `frontend/`. El navegador solo habla con
Next: `/backend/*` se reescribe a la API FastAPI (`BACKEND_URL`), y `src/proxy.ts`
exige la cookie del login falso para todo excepto `/login` y `/auth/*`. Los datos se
leen con TanStack Query sobre un cliente `openapi-fetch` tipado con tipos generados del
OpenAPI del backend; `unwrap()` convierte el sobre `{success, data, error}` en datos o
en `ApiError`. La lógica pura (fechas, etiquetas, TSV, auth) vive en `src/lib/` con
tests de Vitest; los componentes son presentacionales y las páginas los orquestan.

**Tech Stack:** Next.js 16.3, React 19.3, TypeScript, Tailwind CSS 4.3, shadcn/ui
(CLI 4.21), TanStack Query 5, openapi-fetch 0.17 + openapi-typescript 7.13, Vitest 5 +
Testing Library, Playwright 1.63, Node 24.

**Spec:** [`docs/specs/2026-09-29-etapa-1-asistencia-design.md`](../specs/2026-09-29-etapa-1-asistencia-design.md)
§9 (frontend) y D4/D5. **Prerrequisito:** Plan A terminado
([`2026-09-29-etapa-1-plan-a-backend.md`](2026-09-29-etapa-1-plan-a-backend.md)); los
contratos HTTP de este plan son los de sus Tasks 13–17.

## Global Constraints

- Textos de UI en español; código e identificadores en inglés.
- El navegador nunca llama al backend directo: siempre `/backend/...` (rewrite de Next).
- **Login falso (D4): no es seguridad.** Credenciales de `FAKE_AUTH_USER` /
  `FAKE_AUTH_PASSWORD`; toda la lógica en `src/lib/auth/` para reemplazarla después.
- Next 16: el archivo de interceptación se llama `src/proxy.ts` y exporta `proxy`
  (antes `middleware`). `searchParams` de las páginas es una `Promise`.
- Solo datos sintéticos en tests y E2E (`SR_MODE=fake`, `EMPLEADO A`…).
- Color nunca como única señal: cada celda muestra texto (`Retardo`, `Falta`…).
- Los tipos de la API salen de `src/lib/api/schema.d.ts` (generado, versionado); no
  se escriben a mano tipos que dupliquen el backend.
- Puerto publicado solo en `127.0.0.1:3000`.
- Todos los comandos de frontend se corren **desde `frontend/`** salvo que se indique.
- Commits `<type>: <description>` cerrando con
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Cookie ausente al pedir `/backend/*`** (sesión expirada con la página abierta):
   debe responder 401 en sobre JSON, no una redirección HTML que rompa `unwrap`. →
   test en Task 3.
2. **`?next=` malicioso en el login** (`//evil.com`, `https://…`): después de entrar
   siempre se queda en el sitio. → test en Task 3.
3. **Semana sin `?desde=` alrededor de medianoche:** la semana por defecto se calcula
   en el navegador (hora local), no en el servidor (UTC). → test de `useEnsurePeriod`
   en Task 4.
4. **Comentarios con tabuladores o saltos de línea** al copiar para RH: no deben romper
   las columnas del pegado. → test en Task 6.
5. **SR caído (503):** la vista muestra el mensaje del backend ("Revisa Tailscale") con
   reintento, y la configuración sigue usable. → test de `unwrap` en Task 2 y de
   `QueryError` en Task 4.

---

## Estructura de archivos

```
frontend/
  package.json, next.config.ts, eslint.config.mjs, tsconfig.json, components.json
  vitest.config.mts, vitest.setup.ts, playwright.config.ts, Dockerfile
  e2e/attendance.spec.ts
  src/
    proxy.ts                         login falso: exige cookie
    app/
      layout.tsx, providers.tsx, globals.css
      login/page.tsx, login/login-form.tsx
      auth/login/route.ts, auth/logout/route.ts
      (app)/layout.tsx, (app)/page.tsx
      (app)/semana/page.tsx, (app)/incidencias/page.tsx
      (app)/mes/page.tsx, (app)/configuracion/page.tsx
    lib/
      auth/session.ts                credenciales, cookie, next seguro
      api/schema.d.ts                GENERADO (openapi-typescript)
      api/types.ts                   alias de tipos del schema
      api/client.ts                  api (openapi-fetch), unwrap, ApiError
      api/invalidate.ts              useInvalidate
      api/attendance.ts              hooks de asistencia
      api/config.ts                  hooks de configuración
      dates.ts, labels.ts, tsv.ts, period.ts, utils.ts (shadcn)
    components/
      ui/*                           shadcn + native-select.tsx
      app-shell.tsx, feedback.tsx, export-button.tsx, period-nav.tsx
      attendance/week-grid.tsx, legend.tsx, warnings-list.tsx
      attendance/day-panel.tsx, justify-form.tsx, rest-swap-form.tsx, exception-form.tsx
      attendance/week-view.tsx, incidents-view.tsx, rh-table.tsx
      attendance/month-view.tsx, summary-table.tsx
      config/config-view.tsx, employees-tab.tsx, import-dialog.tsx
      config/rest-rules-tab.tsx, exceptions-tab.tsx, settings-tab.tsx
```

---

### Task 1: Scaffold de Next.js, herramientas y contenedor

**Files:**
- Create: `frontend/` (create-next-app + shadcn), `frontend/Dockerfile`,
  `frontend/vitest.config.mts`, `frontend/vitest.setup.ts`,
  `frontend/src/components/ui/native-select.tsx`
- Modify: `frontend/package.json` (scripts), `frontend/next.config.ts`,
  `frontend/eslint.config.mjs`, `docker-compose.yml`, `.dockerignore`
- Delete: `frontend/src/app/page.tsx`, `frontend/public/*.svg` de la plantilla

**Interfaces:**
- Produces: scripts `lint`, `typecheck`, `test`, `gen:api`, `e2e`; rewrite
  `/backend/:path*` → `${BACKEND_URL}/:path*`; componentes shadcn `button`, `input`,
  `label`, `table`, `sheet`, `tabs`, `card`, `dialog`, `checkbox`, `sonner`;
  `NativeSelect`; servicio compose `frontend` en `127.0.0.1:3000`.

- [ ] **Step 1: Crear la app y agregar dependencias**

```bash
cd /Users/didiertm/Documents/Projects/TabernasCerveceras
npx create-next-app@16 frontend --ts --tailwind --eslint --app --src-dir \
  --import-alias "@/*" --use-npm --yes
cd frontend
npx shadcn@latest init --defaults
npx shadcn@latest add button input label table sheet tabs card dialog checkbox sonner
npm install @tanstack/react-query openapi-fetch
npm install -D openapi-typescript vitest @vitest/coverage-v8 @vitejs/plugin-react \
  vite-tsconfig-paths jsdom @testing-library/react @testing-library/dom \
  @testing-library/user-event @testing-library/jest-dom @playwright/test
rm -f src/app/page.tsx public/*.svg
```
Si `create-next-app` generó archivos de instrucciones para agentes (`AGENTS.md`,
`CLAUDE.md`) dentro de `frontend/`, bórralos: el repo ya tiene su `CLAUDE.md`.

- [ ] **Step 2: Configurar scripts, Next, ESLint y Vitest**

En `frontend/package.json`, deja `scripts` así:
```json
{
  "dev": "next dev",
  "build": "next build",
  "start": "next start",
  "lint": "eslint",
  "typecheck": "tsc --noEmit",
  "test": "vitest run",
  "test:watch": "vitest",
  "gen:api": "openapi-typescript http://127.0.0.1:8000/openapi.json -o src/lib/api/schema.d.ts",
  "e2e": "playwright test"
}
```

`frontend/next.config.ts`:
```ts
import type { NextConfig } from "next";

// Rewrites are resolved at build time: the Docker build receives BACKEND_URL as an arg.
const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [{ source: "/backend/:path*", destination: `${backendUrl}/:path*` }];
  },
};

export default nextConfig;
```

En `frontend/eslint.config.mjs`, agrega a la lista de `ignores` (o crea un objeto
`{ ignores: [...] }` al final del arreglo exportado):
```js
"src/lib/api/schema.d.ts", "playwright-report/**", "test-results/**", "coverage/**"
```

`frontend/vitest.config.mts`:
```ts
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [tsconfigPaths(), react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      include: ["src/lib/**/*.ts", "src/proxy.ts"],
      exclude: ["src/lib/api/schema.d.ts", "src/lib/api/attendance.ts", "src/lib/api/config.ts"],
      thresholds: { lines: 80, functions: 80, branches: 80 },
    },
  },
});
```

`frontend/vitest.setup.ts`:
```ts
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => cleanup());
```

`frontend/src/components/ui/native-select.tsx`:
```tsx
import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

/** Native <select> styled like shadcn inputs: accessible and trivial to test. */
export function NativeSelect({ className, ...props }: ComponentProps<"select">) {
  return (
    <select
      className={cn(
        "h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm shadow-xs",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
      {...props}
    />
  );
}
```

- [ ] **Step 3: Contenedor y compose**

`frontend/Dockerfile`:
```dockerfile
FROM node:24-alpine AS deps
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

FROM node:24-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ ./
ARG BACKEND_URL=http://backend:8000
ENV BACKEND_URL=$BACKEND_URL NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:24-alpine
WORKDIR /app
ENV NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0 NEXT_TELEMETRY_DISABLED=1
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

En `docker-compose.yml`, agrega el servicio (a la altura de `backend`):
```yaml
  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
      args:
        BACKEND_URL: http://backend:8000
    environment:
      FAKE_AUTH_USER: ${FAKE_AUTH_USER:-demo}
      FAKE_AUTH_PASSWORD: ${FAKE_AUTH_PASSWORD:-demo}
    ports:
      - "127.0.0.1:3000:3000"
    depends_on:
      backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "/dev/null", "http://127.0.0.1:3000/login"]
      interval: 10s
      timeout: 5s
      retries: 12
```

En `.dockerignore` agrega `**/coverage`, `**/playwright-report`, `**/test-results`.

- [ ] **Step 4: Verificar**

Run: `npm run lint && npm run typecheck && npm run build`
Expected: sin errores (Vitest aún no tiene tests; se verifica en Task 2).

Run (raíz): `SR_MODE=fake docker compose up -d --build --wait frontend && docker compose ps frontend`
Expected: `frontend` en estado `healthy` (aún no hay páginas propias; el healthcheck
consulta `/login`, que se crea en Task 3 — hasta entonces basta con `running`).

- [ ] **Step 5: Commit**

```bash
cd /Users/didiertm/Documents/Projects/TabernasCerveceras
git add frontend docker-compose.yml .dockerignore
git status --short   # confirma que no entra node_modules/ ni .next/
git commit -m "chore: scaffold Next.js frontend with shadcn, vitest and docker

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Tipos generados y cliente de la API

**Files:**
- Create: `frontend/src/lib/api/schema.d.ts` (generado), `frontend/src/lib/api/types.ts`,
  `frontend/src/lib/api/client.ts`, `frontend/src/lib/api/client.test.ts`

**Interfaces:**
- Consumes: OpenAPI del backend (Plan A, Tasks 13–17).
- Produces: `api` (cliente `openapi-fetch` con `baseUrl: "/backend"`);
  `ApiError(code: string, message: string, status: number)`;
  `unwrap<T>(request) -> Promise<T>` (lanza `ApiError`; código `NETWORK_ERROR` si
  falla la red); `isSrUnavailable(error) -> boolean`; alias de tipos en `types.ts`:
  `CalendarOut, DayOut, EmployeeRef, IncidentsOut, RhRowOut, SummaryOut, WarningOut,
  EmployeeOut, EmployeeUpdate, SrEmployeeOut, RestRuleOut, RestRuleCreate, ExceptionOut,
  ExceptionCreate, RestSwapCreate, JustificationCreate, SettingsBody, Outcome, RhType,
  Incident, ExceptionKind, Area, WarningCode`.

- [ ] **Step 1: Generar los tipos**

```bash
cd /Users/didiertm/Documents/Projects/TabernasCerveceras
SR_MODE=fake docker compose up -d --build backend
cd frontend && npm run gen:api
grep -c "DayOut" src/lib/api/schema.d.ts
```
Expected: `schema.d.ts` creado; el grep cuenta ≥ 1. Si falta algún nombre de
`types.ts` (paso 2), revisa cómo lo nombró el OpenAPI (`/openapi.json`) antes de seguir.

`frontend/src/lib/api/types.ts`:
```ts
import type { components } from "./schema";

type Schemas = components["schemas"];

export type CalendarOut = Schemas["CalendarOut"];
export type DayOut = Schemas["DayOut"];
export type EmployeeRef = Schemas["EmployeeRef"];
export type IncidentsOut = Schemas["IncidentsOut"];
export type RhRowOut = Schemas["RhRowOut"];
export type SummaryOut = Schemas["SummaryOut"];
export type WarningOut = Schemas["WarningOut"];
export type EmployeeOut = Schemas["EmployeeOut"];
export type EmployeeUpdate = Schemas["EmployeeUpdate"];
export type SrEmployeeOut = Schemas["SrEmployeeOut"];
export type RestRuleOut = Schemas["RestRuleOut"];
export type RestRuleCreate = Schemas["RestRuleCreate"];
export type ExceptionOut = Schemas["ExceptionOut"];
export type ExceptionCreate = Schemas["ExceptionCreate"];
export type RestSwapCreate = Schemas["RestSwapCreate"];
export type JustificationCreate = Schemas["JustificationCreate"];
export type SettingsBody = Schemas["SettingsBody"];
export type Outcome = Schemas["Outcome"];
export type RhType = Schemas["RhType"];
export type Incident = Schemas["Incident"];
export type ExceptionKind = Schemas["ExceptionKind"];
export type Area = Schemas["Area"];
export type WarningCode = Schemas["WarningCode"];
```

- [ ] **Step 2: Escribir el test de `unwrap` (falla)**

`frontend/src/lib/api/client.test.ts`:
```ts
import { describe, expect, it } from "vitest";

import { ApiError, isSrUnavailable, unwrap } from "./client";

const response = (status: number) => ({ status }) as Response;

describe("unwrap", () => {
  it("returns the envelope data on success", async () => {
    const request = Promise.resolve({ data: { success: true, data: [1, 2] }, response: response(200) });
    await expect(unwrap(request)).resolves.toEqual([1, 2]);
  });

  it("returns null data for successful deletes", async () => {
    const request = Promise.resolve({ data: { success: true, data: null }, response: response(200) });
    await expect(unwrap(request)).resolves.toBeNull();
  });

  it("throws ApiError with the backend code and message", async () => {
    const body = {
      success: false,
      data: null,
      error: { code: "SR_UNAVAILABLE", message: "No se pudo leer SoftRestaurant. Revisa Tailscale." },
    };
    const request = Promise.resolve({ error: body, response: response(503) });
    const error = await unwrap(request).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: "SR_UNAVAILABLE", status: 503 });
    expect(isSrUnavailable(error)).toBe(true);
  });

  it("falls back to HTTP_ERROR when the body is not an envelope", async () => {
    const request = Promise.resolve({ error: "Bad Gateway", response: response(502) });
    await expect(unwrap(request)).rejects.toMatchObject({ code: "HTTP_ERROR", status: 502 });
  });

  it("maps network failures to NETWORK_ERROR", async () => {
    const request = Promise.reject(new TypeError("fetch failed"));
    await expect(unwrap(request)).rejects.toMatchObject({ code: "NETWORK_ERROR", status: 0 });
  });
});
```

- [ ] **Step 3: Correr y verificar que falla**

Run: `npm test -- src/lib/api/client.test.ts`
Expected: FAIL (`Failed to resolve import "./client"`).

- [ ] **Step 4: Implementar `client.ts`**

`frontend/src/lib/api/client.ts`:
```ts
import createClient from "openapi-fetch";

import type { paths } from "./schema";

/** Browser-only client: `/backend/*` is rewritten by Next to the FastAPI backend. */
export const api = createClient<paths>({ baseUrl: "/backend" });

export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type ErrorBody = { code: string; message: string };
type Enveloped<T> = { success: boolean; data?: T | null; error?: ErrorBody | null };
type FetchResult<T> = { data?: Enveloped<T>; error?: unknown; response: Response };

function errorBody(value: unknown): ErrorBody | null {
  if (typeof value !== "object" || value === null || !("error" in value)) return null;
  const error = (value as { error: unknown }).error;
  if (typeof error !== "object" || error === null) return null;
  const { code, message } = error as Partial<ErrorBody>;
  return typeof code === "string" && typeof message === "string" ? { code, message } : null;
}

export async function unwrap<T>(request: Promise<FetchResult<T>>): Promise<T> {
  let result: FetchResult<T>;
  try {
    result = await request;
  } catch {
    throw new ApiError("NETWORK_ERROR", "No se pudo conectar con el servidor", 0);
  }
  const { data, error, response } = result;
  if (data?.success) return (data.data ?? null) as T;
  const body = errorBody(error ?? data);
  throw new ApiError(
    body?.code ?? "HTTP_ERROR",
    body?.message ?? `Error ${response.status}`,
    response.status,
  );
}

export function isSrUnavailable(error: unknown): boolean {
  return error instanceof ApiError && error.code === "SR_UNAVAILABLE";
}
```

- [ ] **Step 5: Correr y verificar**

Run: `npm test -- src/lib/api/client.test.ts && npm run typecheck && npm run lint`
Expected: 5 passed; sin errores.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/api
git commit -m "feat: add typed API client with envelope unwrapping

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Login falso (`proxy.ts`, rutas `/auth/*`, página `/login`)

**Files:**
- Create: `frontend/src/lib/auth/session.ts`, `frontend/src/lib/auth/session.test.ts`,
  `frontend/src/proxy.ts`, `frontend/src/proxy.test.ts`,
  `frontend/src/app/auth/login/route.ts`, `frontend/src/app/auth/logout/route.ts`,
  `frontend/src/app/login/page.tsx`, `frontend/src/app/login/login-form.tsx`

**Interfaces:**
- Produces: `SESSION_COOKIE = "tc_session"`, `SESSION_VALUE`,
  `credentialsMatch(user, password, env?) -> boolean`, `hasSession(value) -> boolean`,
  `safeNext(value) -> string` (ruta interna o `/semana`); `proxy(request)`;
  `POST /auth/login` (JSON `{user, password}` → 200 + cookie, o 401 en sobre);
  `POST /auth/logout`; página `/login?next=`.

- [ ] **Step 1: Escribir los tests (fallan)**

`frontend/src/lib/auth/session.test.ts`:
```ts
import { describe, expect, it } from "vitest";

import { SESSION_VALUE, credentialsMatch, hasSession, safeNext } from "./session";

const env = { FAKE_AUTH_USER: "demo", FAKE_AUTH_PASSWORD: "secreto" };

describe("credentialsMatch", () => {
  it("accepts only the configured pair", () => {
    expect(credentialsMatch("demo", "secreto", env)).toBe(true);
    expect(credentialsMatch("demo", "otra", env)).toBe(false);
    expect(credentialsMatch("otro", "secreto", env)).toBe(false);
  });

  it("rejects everything when credentials are not configured", () => {
    expect(credentialsMatch("", "", {})).toBe(false);
    expect(credentialsMatch("demo", "secreto", { FAKE_AUTH_USER: "demo" })).toBe(false);
  });
});

describe("hasSession", () => {
  it("requires the exact session value", () => {
    expect(hasSession(SESSION_VALUE)).toBe(true);
    expect(hasSession(undefined)).toBe(false);
    expect(hasSession("forged")).toBe(false);
  });
});

describe("safeNext", () => {
  it("keeps internal paths with their query", () => {
    expect(safeNext("/semana?desde=2026-09-21")).toBe("/semana?desde=2026-09-21");
  });

  it.each([undefined, "", "https://evil.com", "//evil.com", "/\\evil.com", "semana"])(
    "falls back to /semana for %s",
    (value) => {
      expect(safeNext(value)).toBe("/semana");
    },
  );
});
```

`frontend/src/proxy.test.ts`:
```ts
// @vitest-environment node
import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { SESSION_COOKIE, SESSION_VALUE } from "@/lib/auth/session";
import { proxy } from "@/proxy";

function request(path: string, withSession = false): NextRequest {
  const headers = withSession ? { cookie: `${SESSION_COOKIE}=${SESSION_VALUE}` } : undefined;
  return new NextRequest(`http://localhost${path}`, { headers });
}

describe("proxy", () => {
  it("redirects pages to /login keeping the destination", () => {
    const response = proxy(request("/semana?desde=2026-09-21"));
    expect(response.status).toBe(307);
    const location = new URL(response.headers.get("location") ?? "");
    expect(location.pathname).toBe("/login");
    expect(location.searchParams.get("next")).toBe("/semana?desde=2026-09-21");
  });

  it("answers API calls without session with a 401 envelope", async () => {
    const response = proxy(request("/backend/attendance/calendar"));
    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toMatchObject({
      success: false,
      error: { code: "UNAUTHENTICATED" },
    });
  });

  it("lets requests with a session through", () => {
    const response = proxy(request("/semana", true));
    expect(response.headers.get("x-middleware-next")).toBe("1");
  });
});
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `npm test -- src/lib/auth src/proxy.test.ts`
Expected: FAIL (módulos inexistentes).

- [ ] **Step 3: Implementar**

`frontend/src/lib/auth/session.ts`:
```ts
/**
 * FAKE LOGIN (spec D4). This is NOT security: a single demo user from env vars and a
 * constant cookie. Everything auth-related lives here so real auth can replace it.
 */

export const SESSION_COOKIE = "tc_session";
export const SESSION_VALUE = "fake-session";
export const SESSION_MAX_AGE_S = 60 * 60 * 12;
const DEFAULT_AFTER_LOGIN = "/semana";

type Env = Record<string, string | undefined>;

export function credentialsMatch(user: string, password: string, env: Env = process.env): boolean {
  const expectedUser = env.FAKE_AUTH_USER;
  const expectedPassword = env.FAKE_AUTH_PASSWORD;
  if (!expectedUser || !expectedPassword) return false;
  return user === expectedUser && password === expectedPassword;
}

export function hasSession(cookieValue: string | undefined): boolean {
  return cookieValue === SESSION_VALUE;
}

/** Only same-site paths: blocks open redirects such as //evil.com or https://…. */
export function safeNext(value: string | undefined): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) {
    return DEFAULT_AFTER_LOGIN;
  }
  return value;
}
```

`frontend/src/proxy.ts`:
```ts
import { NextResponse, type NextRequest } from "next/server";

import { SESSION_COOKIE, hasSession } from "@/lib/auth/session";

export function proxy(request: NextRequest): NextResponse {
  if (hasSession(request.cookies.get(SESSION_COOKIE)?.value)) {
    return NextResponse.next();
  }
  const { pathname, search } = request.nextUrl;
  if (pathname.startsWith("/backend/")) {
    return NextResponse.json(
      {
        success: false,
        data: null,
        error: { code: "UNAUTHENTICATED", message: "Inicia sesión de nuevo" },
        meta: null,
      },
      { status: 401 },
    );
  }
  const login = new URL("/login", request.url);
  login.searchParams.set("next", `${pathname}${search}`);
  return NextResponse.redirect(login);
}

export const config = {
  matcher: ["/((?!login|auth/|_next/static|_next/image|favicon.ico).*)"],
};
```

`frontend/src/app/auth/login/route.ts`:
```ts
import { NextResponse } from "next/server";

import {
  SESSION_COOKIE,
  SESSION_MAX_AGE_S,
  SESSION_VALUE,
  credentialsMatch,
} from "@/lib/auth/session";

function field(body: unknown, name: string): string {
  if (typeof body !== "object" || body === null) return "";
  const value = (body as Record<string, unknown>)[name];
  return typeof value === "string" ? value : "";
}

export async function POST(request: Request): Promise<NextResponse> {
  const body: unknown = await request.json().catch(() => null);
  if (!credentialsMatch(field(body, "user"), field(body, "password"))) {
    return NextResponse.json(
      {
        success: false,
        data: null,
        error: { code: "INVALID_CREDENTIALS", message: "Usuario o contraseña incorrectos" },
        meta: null,
      },
      { status: 401 },
    );
  }
  const response = NextResponse.json({ success: true, data: null, error: null, meta: null });
  response.cookies.set(SESSION_COOKIE, SESSION_VALUE, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_MAX_AGE_S,
  });
  return response;
}
```

`frontend/src/app/auth/logout/route.ts`:
```ts
import { NextResponse } from "next/server";

import { SESSION_COOKIE } from "@/lib/auth/session";

export async function POST(): Promise<NextResponse> {
  const response = NextResponse.json({ success: true, data: null, error: null, meta: null });
  response.cookies.delete(SESSION_COOKIE);
  return response;
}
```

`frontend/src/app/login/page.tsx`:
```tsx
import { safeNext } from "@/lib/auth/session";

import { LoginForm } from "./login-form";

type Props = { searchParams: Promise<{ next?: string }> };

export default async function LoginPage({ searchParams }: Props) {
  const { next } = await searchParams;
  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <LoginForm next={safeNext(next)} />
    </main>
  );
}
```

`frontend/src/app/login/login-form.tsx`:
```tsx
"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function LoginForm({ next }: { next: string }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setPending(true);
    setError(null);
    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user: form.get("user"), password: form.get("password") }),
      });
      if (!response.ok) {
        setError("Usuario o contraseña incorrectos");
        return;
      }
      router.replace(next);
      router.refresh();
    } catch {
      setError("No se pudo conectar con el servidor");
    } finally {
      setPending(false);
    }
  }

  return (
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle>Tabernas Cerveceras</CardTitle>
        <CardDescription>Acceso de demostración (no es autenticación real).</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="user">Usuario</Label>
            <Input id="user" name="user" autoComplete="username" required />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Contraseña</Label>
            <Input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
            />
          </div>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <Button type="submit" className="w-full" disabled={pending}>
            {pending ? "Entrando…" : "Entrar"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 4: Correr y verificar**

Run: `npm test -- src/lib/auth src/proxy.test.ts && npm run typecheck && npm run lint`
Expected: todos PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "feat: add fake login with proxy guard (placeholder for real auth)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Utilidades compartidas, layout de la app y componentes de estado

**Files:**
- Create: `frontend/src/lib/dates.ts`, `dates.test.ts`, `frontend/src/lib/labels.ts`,
  `labels.test.ts`, `frontend/src/lib/period.ts`, `period.test.tsx`,
  `frontend/src/lib/api/invalidate.ts`, `frontend/src/app/providers.tsx`,
  `frontend/src/app/(app)/layout.tsx`, `frontend/src/app/(app)/page.tsx`,
  `frontend/src/components/app-shell.tsx`, `frontend/src/components/feedback.tsx`,
  `frontend/src/components/feedback.test.tsx`, `frontend/src/components/export-button.tsx`,
  `frontend/src/components/period-nav.tsx`
- Modify: `frontend/src/app/layout.tsx`

**Interfaces:**
- Produces (`dates.ts`, fechas como `YYYY-MM-DD` en hora local):
  `toIsoDate(Date)`, `parseIsoDate(s) -> Date`, `isIsoDate(s) -> boolean`,
  `todayIso(now?)`, `addDays(s, n)`, `weekStart(s)`, `monthRange(s) -> {from, to}`,
  `daysBetween(from, to) -> string[]`, `isoWeekNumber(s)`, `formatDay(s)` (`"mié 23/09"`),
  `formatDate(s)` (`"23/09/2026"`), `formatTime(datetime | null | undefined)` (`"16:51"`).
- Produces (`labels.ts`): `OUTCOME_LABELS`, `OUTCOME_STYLES`, `RH_LABELS`,
  `EXCEPTION_KIND_LABELS`, `WEEKDAY_LABELS`, `ABSENCE_RH_TYPES`, `JUSTIFICATION_RH_TYPES`,
  `WARNING_LABELS`, `incidentFor(outcome) -> Incident | null`.
- Produces (`period.ts`): `useEnsurePeriod(requested: string | null, buildQuery: (today: string) => string)`.
- Produces: `useInvalidate(...keys)`; `Providers`; `AppShell`; `QueryError({error, onRetry})`,
  `FormError({error})`, `Loading()`; `ExportButton({from, to})`;
  `PeriodNav({label, previousHref, nextHref})`.

- [ ] **Step 1: Escribir los tests (fallan)**

`frontend/src/lib/dates.test.ts`:
```ts
import { describe, expect, it } from "vitest";

import {
  addDays,
  daysBetween,
  formatDate,
  formatDay,
  formatTime,
  isIsoDate,
  isoWeekNumber,
  monthRange,
  todayIso,
  weekStart,
} from "./dates";

describe("dates", () => {
  it("finds the Monday of the week", () => {
    expect(weekStart("2026-09-27")).toBe("2026-09-21");
    expect(weekStart("2026-09-21")).toBe("2026-09-21");
  });

  it("adds days across months and years", () => {
    expect(addDays("2026-09-30", 1)).toBe("2026-10-01");
    expect(addDays("2027-01-01", -1)).toBe("2026-12-31");
  });

  it("builds month ranges", () => {
    expect(monthRange("2026-02-15")).toEqual({ from: "2026-02-01", to: "2026-02-28" });
  });

  it("lists days inclusively", () => {
    expect(daysBetween("2026-09-29", "2026-10-01")).toEqual([
      "2026-09-29",
      "2026-09-30",
      "2026-10-01",
    ]);
  });

  it("computes ISO week numbers at year boundaries", () => {
    expect(isoWeekNumber("2026-09-23")).toBe(39);
    expect(isoWeekNumber("2027-01-01")).toBe(53);
    expect(isoWeekNumber("2026-01-01")).toBe(1);
  });

  it("validates ISO dates", () => {
    expect(isIsoDate("2026-09-21")).toBe(true);
    expect(isIsoDate("2026-02-30")).toBe(false);
    expect(isIsoDate("21/09/2026")).toBe(false);
    expect(isIsoDate(undefined)).toBe(false);
  });

  it("uses local time for today", () => {
    expect(todayIso(new Date(2026, 8, 27, 23, 30))).toBe("2026-09-27");
  });

  it("formats for display", () => {
    expect(formatDay("2026-09-23")).toBe("mié 23/09");
    expect(formatDate("2026-09-23")).toBe("23/09/2026");
    expect(formatTime("2026-09-23T16:51:07")).toBe("16:51");
    expect(formatTime(null)).toBe("");
  });
});
```

`frontend/src/lib/labels.test.ts`:
```ts
import { describe, expect, it } from "vitest";

import { JUSTIFICATION_RH_TYPES, incidentFor } from "./labels";

describe("labels", () => {
  it("maps outcomes to justifiable incidents", () => {
    expect(incidentFor("LATE")).toBe("LATE");
    expect(incidentFor("ABSENT")).toBe("ABSENT");
    expect(incidentFor("UNREGISTERED_CHANGE")).toBeNull();
    expect(incidentFor("OK")).toBeNull();
  });

  it("defaults justifications like the backend", () => {
    expect(JUSTIFICATION_RH_TYPES.LATE[0]).toBe("NO_CAPTURAR");
    expect(JUSTIFICATION_RH_TYPES.ABSENT[0]).toBe("FALTA_JUSTIFICADA");
  });
});
```

`frontend/src/lib/period.test.tsx`:
```tsx
import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useEnsurePeriod } from "./period";

const { replace } = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  usePathname: () => "/semana",
}));

describe("useEnsurePeriod", () => {
  beforeEach(() => replace.mockClear());

  it("fills the default period from the browser's local date", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 8, 27, 23, 30)); // Sunday night, local time
    renderHook(() => useEnsurePeriod(null, (today) => `desde=${today}`));
    expect(replace).toHaveBeenCalledWith("/semana?desde=2026-09-27");
    vi.useRealTimers();
  });

  it("does nothing when the period is in the URL", () => {
    renderHook(() => useEnsurePeriod("2026-09-21", (today) => `desde=${today}`));
    expect(replace).not.toHaveBeenCalled();
  });
});
```

`frontend/src/components/feedback.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";

import { FormError, QueryError } from "./feedback";

describe("QueryError", () => {
  it("shows the backend message and retries", async () => {
    const onRetry = vi.fn();
    const error = new ApiError("SR_UNAVAILABLE", "No se pudo leer SoftRestaurant. Revisa Tailscale.", 503);
    render(<QueryError error={error} onRetry={onRetry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Revisa Tailscale");
    await userEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("hides details of unexpected errors", () => {
    render(<QueryError error={new Error("stack trace")} onRetry={() => undefined} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Ocurrió un error inesperado");
  });
});

describe("FormError", () => {
  it("renders nothing without error", () => {
    const { container } = render(<FormError error={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `npm test`
Expected: FAIL (módulos inexistentes).

- [ ] **Step 3: Implementar utilidades**

`frontend/src/lib/dates.ts`:
```ts
/** Dates as local "YYYY-MM-DD" strings, matching the backend's naive local dates. */

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const DAY_MS = 86_400_000;
const WEEKDAY_SHORT = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];

const pad = (value: number) => String(value).padStart(2, "0");

export function toIsoDate(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function parseIsoDate(value: string): Date {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function isIsoDate(value: string | undefined | null): value is string {
  return !!value && ISO_DATE.test(value) && toIsoDate(parseIsoDate(value)) === value;
}

export function todayIso(now: Date = new Date()): string {
  return toIsoDate(now);
}

export function addDays(value: string, days: number): string {
  const date = parseIsoDate(value);
  return toIsoDate(new Date(date.getFullYear(), date.getMonth(), date.getDate() + days));
}

export function weekStart(value: string): string {
  const mondayOffset = (parseIsoDate(value).getDay() + 6) % 7;
  return addDays(value, -mondayOffset);
}

export function monthRange(value: string): { from: string; to: string } {
  const date = parseIsoDate(value);
  return {
    from: toIsoDate(new Date(date.getFullYear(), date.getMonth(), 1)),
    to: toIsoDate(new Date(date.getFullYear(), date.getMonth() + 1, 0)),
  };
}

export function daysBetween(from: string, to: string): string[] {
  const count = Math.round((parseIsoDate(to).getTime() - parseIsoDate(from).getTime()) / DAY_MS);
  return Array.from({ length: Math.max(count + 1, 0) }, (_, offset) => addDays(from, offset));
}

export function isoWeekNumber(value: string): number {
  const date = parseIsoDate(value);
  const thursday = new Date(
    date.getFullYear(),
    date.getMonth(),
    date.getDate() + 3 - ((date.getDay() + 6) % 7),
  );
  const yearStart = new Date(thursday.getFullYear(), 0, 1);
  return Math.floor(Math.round((thursday.getTime() - yearStart.getTime()) / DAY_MS) / 7) + 1;
}

export function formatDay(value: string): string {
  const date = parseIsoDate(value);
  return `${WEEKDAY_SHORT[date.getDay()]} ${pad(date.getDate())}/${pad(date.getMonth() + 1)}`;
}

export function formatDate(value: string): string {
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}

export function formatTime(datetime: string | null | undefined): string {
  return datetime ? datetime.slice(11, 16) : "";
}
```

`frontend/src/lib/labels.ts`:
```ts
import type { ExceptionKind, Incident, Outcome, RhType, WarningCode } from "@/lib/api/types";

export const OUTCOME_LABELS: Record<Outcome, string> = {
  OK: "A tiempo",
  LATE: "Retardo",
  ABSENT: "Falta",
  UNREGISTERED_CHANGE: "Cambio sin registrar",
  REST: "Descanso",
  CLOSED: "Cerrado",
  JUSTIFIED: "Justificado",
  PENDING: "Pendiente",
  FUTURE: "",
};

export const OUTCOME_STYLES: Record<Outcome, string> = {
  OK: "bg-emerald-50 text-emerald-900",
  LATE: "bg-amber-100 text-amber-950",
  ABSENT: "bg-red-100 text-red-950",
  UNREGISTERED_CHANGE: "bg-violet-100 text-violet-950",
  REST: "bg-muted text-muted-foreground",
  CLOSED: "bg-zinc-200 text-zinc-800",
  JUSTIFIED: "bg-sky-100 text-sky-950",
  PENDING: "border border-dashed text-muted-foreground",
  FUTURE: "text-muted-foreground",
};

export const RH_LABELS: Record<RhType, string> = {
  RETARDO: "Retardo",
  FALTA_INJUSTIFICADA: "Falta injustificada",
  FALTA_JUSTIFICADA: "Falta justificada",
  VACACIONES: "Vacaciones",
  INCAPACIDAD: "Incapacidad",
  PERMISO: "Permiso",
  DESCANSO: "Descanso",
  NO_CAPTURAR: "No se captura",
};

export const EXCEPTION_KIND_LABELS: Record<ExceptionKind, string> = {
  STORE_CLOSED: "Cierre del local",
  PRESENT_NO_CHECKIN: "Asistió sin checada",
  REST_TO_WORK: "Descanso → laboral",
  WORK_TO_ABSENCE: "Ausencia justificada",
  MANUAL_ABSENCE: "Falta registrada a mano",
};

export const WARNING_LABELS: Record<WarningCode, string> = {
  NO_REST_RULE: "Sin regla de descanso",
  UNMAPPED_CHECKIN: "Checada sin empleado",
  ORPHAN_JUSTIFICATION: "Justificación sin incidencia",
  MISSING_RH_NAME: "Falta nombre en RH",
};

/** Index = backend weekday (0 = Monday … 6 = Sunday). */
export const WEEKDAY_LABELS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];

export const ABSENCE_RH_TYPES: RhType[] = [
  "FALTA_JUSTIFICADA",
  "VACACIONES",
  "INCAPACIDAD",
  "PERMISO",
  "DESCANSO",
];

/** First option = backend default. */
export const JUSTIFICATION_RH_TYPES: Record<Incident, RhType[]> = {
  LATE: ["NO_CAPTURAR", "RETARDO"],
  ABSENT: [...ABSENCE_RH_TYPES, "NO_CAPTURAR"],
};

export function incidentFor(outcome: Outcome): Incident | null {
  if (outcome === "LATE") return "LATE";
  if (outcome === "ABSENT") return "ABSENT";
  return null;
}
```

`frontend/src/lib/period.ts`:
```ts
"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { todayIso } from "./dates";

/**
 * Pages without a period in the URL get one computed in the browser (local time), never
 * on the server, which runs in UTC and would show the wrong week around midnight.
 */
export function useEnsurePeriod(
  requested: string | null,
  buildQuery: (today: string) => string,
): void {
  const router = useRouter();
  const pathname = usePathname();
  useEffect(() => {
    if (requested === null) router.replace(`${pathname}?${buildQuery(todayIso())}`);
  }, [requested, pathname, router, buildQuery]);
}
```

`frontend/src/lib/api/invalidate.ts`:
```ts
"use client";

import { type QueryKey, useQueryClient } from "@tanstack/react-query";

export function useInvalidate(...keys: QueryKey[]): () => Promise<void> {
  const client = useQueryClient();
  return async () => {
    await Promise.all(keys.map((queryKey) => client.invalidateQueries({ queryKey })));
  };
}
```

- [ ] **Step 4: Implementar layout y componentes compartidos**

`frontend/src/app/layout.tsx`:
```tsx
import type { Metadata } from "next";
import type { ReactNode } from "react";

import { Toaster } from "@/components/ui/sonner";

import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tabernas Cerveceras",
  description: "Asistencia y reportes sobre SoftRestaurant",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body className="min-h-screen bg-background text-foreground antialiased">
        <Providers>{children}</Providers>
        <Toaster richColors />
      </body>
    </html>
  );
}
```

`frontend/src/app/providers.tsx`:
```tsx
"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";

import { ApiError } from "@/lib/api/client";

function shouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false;
  return failureCount < 2;
}

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 30_000, retry: shouldRetry, refetchOnWindowFocus: false },
        },
      }),
  );
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
```

`frontend/src/app/(app)/layout.tsx`:
```tsx
import type { ReactNode } from "react";

import { AppShell } from "@/components/app-shell";

export default function AppLayout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
```

`frontend/src/app/(app)/page.tsx`:
```tsx
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/semana");
}
```

`frontend/src/components/app-shell.tsx`:
```tsx
"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/semana", label: "Semana" },
  { href: "/incidencias", label: "Incidencias" },
  { href: "/mes", label: "Mes" },
  { href: "/configuracion", label: "Configuración" },
] as const;

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  async function logout() {
    await fetch("/auth/logout", { method: "POST" }).catch(() => undefined);
    router.replace("/login");
    router.refresh();
  }

  return (
    <div className="min-h-screen">
      <header className="border-b">
        <nav aria-label="Principal" className="mx-auto flex max-w-7xl flex-wrap items-center gap-1 px-4 py-2">
          <span className="mr-4 font-semibold">Tabernas Cerveceras</span>
          {LINKS.map((link) => {
            const active = pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "rounded-md px-3 py-1.5 text-sm",
                  active ? "bg-muted font-medium" : "text-muted-foreground hover:text-foreground",
                )}
              >
                {link.label}
              </Link>
            );
          })}
          <Button variant="ghost" size="sm" className="ml-auto" onClick={logout}>
            Salir
          </Button>
        </nav>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
    </div>
  );
}
```

`frontend/src/components/feedback.tsx`:
```tsx
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";

export function Loading() {
  return <p className="text-sm text-muted-foreground">Cargando…</p>;
}

export function QueryError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const message = error instanceof ApiError ? error.message : "Ocurrió un error inesperado";
  return (
    <div
      role="alert"
      className="flex items-center justify-between gap-4 rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm"
    >
      <span>{message}</span>
      <Button variant="outline" size="sm" onClick={onRetry}>
        Reintentar
      </Button>
    </div>
  );
}

export function FormError({ error }: { error: unknown }) {
  if (!error) return null;
  const message = error instanceof ApiError ? error.message : "No se pudo guardar";
  return (
    <p role="alert" className="text-sm text-destructive">
      {message}
    </p>
  );
}
```

`frontend/src/components/export-button.tsx`:
```tsx
import { Button } from "@/components/ui/button";

export function ExportButton({ from, to }: { from: string; to: string }) {
  const query = new URLSearchParams({ from, to }).toString();
  return (
    <Button asChild variant="outline">
      <a href={`/backend/attendance/export.xlsx?${query}`} download>
        Exportar a Excel
      </a>
    </Button>
  );
}
```

`frontend/src/components/period-nav.tsx`:
```tsx
import Link from "next/link";

import { Button } from "@/components/ui/button";

type Props = { label: string; previousHref: string; nextHref: string };

export function PeriodNav({ label, previousHref, nextHref }: Props) {
  return (
    <div className="flex items-center gap-2">
      <Button asChild variant="outline" size="sm">
        <Link href={previousHref}>← Anterior</Link>
      </Button>
      <span className="text-sm font-medium">{label}</span>
      <Button asChild variant="outline" size="sm">
        <Link href={nextHref}>Siguiente →</Link>
      </Button>
    </div>
  );
}
```

- [ ] **Step 5: Correr y verificar**

Run: `npm test && npm run typecheck && npm run lint`
Expected: todos PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src
git commit -m "feat: add date/label utilities, app shell and feedback components

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Vista semanal (cuadrícula + panel del día con acciones)

**Files:**
- Create: `frontend/src/lib/api/attendance.ts`,
  `frontend/src/components/attendance/week-grid.tsx`, `week-grid.test.tsx`,
  `legend.tsx`, `warnings-list.tsx`, `justify-form.tsx`, `rest-swap-form.tsx`,
  `exception-form.tsx`, `day-panel.tsx`, `week-view.tsx`,
  `frontend/src/app/(app)/semana/page.tsx`

**Interfaces:**
- Consumes: `api`, `unwrap` (Task 2); utilidades y componentes (Task 4).
- Produces (`attendance.ts`): `attendanceKeys`; `useCalendar(from, to)`,
  `useIncidents(from, to)`, `useSummary(from, to, group)`; mutaciones
  `useCreateJustification()`, `useRestSwap()`, `useCreateException()` (invalidan
  `["attendance"]` y `["exceptions"]`).
- Produces: `WeekGrid({calendar, onSelect(day, employee)})`; `DaySelection = {day: DayOut, employee: EmployeeRef}`;
  `DayPanel({selection, onClose})`; `WeekView({requestedStart})`; página
  `/semana?desde=YYYY-MM-DD`.

- [ ] **Step 1: Escribir el test de la cuadrícula (falla)**

`frontend/src/components/attendance/week-grid.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { CalendarOut, DayOut } from "@/lib/api/types";

import { WeekGrid } from "./week-grid";

function day(overrides: Partial<DayOut>): DayOut {
  return {
    employee_id: 1,
    day: "2026-09-21",
    planned: "WORK",
    outcome: "OK",
    checkin: null,
    minutes_late: null,
    rh_type: null,
    justification_id: null,
    comment: "",
    ...overrides,
  };
}

const calendar: CalendarOut = {
  start: "2026-09-21",
  end: "2026-09-22",
  employees: [{ id: 1, short_name: "EMPLEADO A", rh_name: null, area: "OTHER" }],
  days: [
    day({ outcome: "LATE", checkin: "2026-09-21T16:51:00", minutes_late: 11 }),
    day({ day: "2026-09-22", outcome: "FUTURE" }),
  ],
  warnings: [],
};

describe("WeekGrid", () => {
  it("shows outcome text and check-in time per cell", () => {
    render(<WeekGrid calendar={calendar} onSelect={() => undefined} />);
    expect(screen.getByRole("columnheader", { name: "lun 21/09" })).toBeInTheDocument();
    const row = screen.getByRole("row", { name: /EMPLEADO A/ });
    expect(row).toHaveTextContent("Retardo");
    expect(row).toHaveTextContent("16:51");
  });

  it("selects a day and disables future days", async () => {
    const onSelect = vi.fn();
    render(<WeekGrid calendar={calendar} onSelect={onSelect} />);
    await userEvent.click(screen.getByRole("button", { name: /lun 21\/09: Retardo 16:51/ }));
    expect(onSelect).toHaveBeenCalledWith(calendar.days[0], calendar.employees[0]);
    expect(screen.getByRole("button", { name: /mar 22\/09/ })).toBeDisabled();
  });
});
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `npm test -- src/components/attendance/week-grid.test.tsx`
Expected: FAIL (módulo inexistente).

- [ ] **Step 3: Implementar hooks y cuadrícula**

`frontend/src/lib/api/attendance.ts`:
```ts
"use client";

import { useMutation, useQuery } from "@tanstack/react-query";

import { api, unwrap } from "./client";
import { useInvalidate } from "./invalidate";
import type { ExceptionCreate, JustificationCreate, RestSwapCreate } from "./types";

export const attendanceKeys = {
  all: ["attendance"] as const,
  calendar: (from: string, to: string) => ["attendance", "calendar", from, to] as const,
  incidents: (from: string, to: string) => ["attendance", "incidents", from, to] as const,
  summary: (from: string, to: string, group: string) =>
    ["attendance", "summary", from, to, group] as const,
};

export function useCalendar(from: string, to: string) {
  return useQuery({
    queryKey: attendanceKeys.calendar(from, to),
    queryFn: () => unwrap(api.GET("/attendance/calendar", { params: { query: { from, to } } })),
  });
}

export function useIncidents(from: string, to: string) {
  return useQuery({
    queryKey: attendanceKeys.incidents(from, to),
    queryFn: () => unwrap(api.GET("/attendance/incidents", { params: { query: { from, to } } })),
  });
}

export function useSummary(from: string, to: string, group: "week" | "month") {
  return useQuery({
    queryKey: attendanceKeys.summary(from, to, group),
    queryFn: () =>
      unwrap(api.GET("/attendance/summary", { params: { query: { from, to, group } } })),
  });
}

export function useCreateJustification() {
  const invalidate = useInvalidate(attendanceKeys.all);
  return useMutation({
    mutationFn: (body: JustificationCreate) => unwrap(api.POST("/justifications", { body })),
    onSuccess: invalidate,
  });
}

export function useRestSwap() {
  const invalidate = useInvalidate(attendanceKeys.all, ["exceptions"]);
  return useMutation({
    mutationFn: (body: RestSwapCreate) => unwrap(api.POST("/exceptions/rest-swap", { body })),
    onSuccess: invalidate,
  });
}

export function useCreateException() {
  const invalidate = useInvalidate(attendanceKeys.all, ["exceptions"]);
  return useMutation({
    mutationFn: (body: ExceptionCreate) => unwrap(api.POST("/exceptions", { body })),
    onSuccess: invalidate,
  });
}
```

`frontend/src/components/attendance/week-grid.tsx`:
```tsx
import type { CalendarOut, DayOut, EmployeeRef } from "@/lib/api/types";
import { daysBetween, formatDay, formatTime } from "@/lib/dates";
import { OUTCOME_LABELS, OUTCOME_STYLES } from "@/lib/labels";
import { cn } from "@/lib/utils";

export type DaySelection = { day: DayOut; employee: EmployeeRef };

type Props = {
  calendar: CalendarOut;
  onSelect: (day: DayOut, employee: EmployeeRef) => void;
};

export function WeekGrid({ calendar, onSelect }: Props) {
  const dates = daysBetween(calendar.start, calendar.end);
  const byKey = new Map(calendar.days.map((d) => [`${d.employee_id}|${d.day}`, d]));
  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full min-w-[720px] text-sm">
        <thead>
          <tr>
            <th scope="col" className="p-2 text-left font-medium">
              Empleado
            </th>
            {dates.map((date) => (
              <th key={date} scope="col" className="p-2 text-center font-medium">
                {formatDay(date)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {calendar.employees.map((employee) => (
            <tr key={employee.id} className="border-t">
              <th scope="row" className="p-2 text-left font-medium">
                {employee.short_name}
              </th>
              {dates.map((date) => {
                const day = byKey.get(`${employee.id}|${date}`);
                return (
                  <td key={date} className="p-1">
                    {day && <DayCell day={day} onClick={() => onSelect(day, employee)} />}
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

function DayCell({ day, onClick }: { day: DayOut; onClick: () => void }) {
  const label = OUTCOME_LABELS[day.outcome];
  const time = formatTime(day.checkin);
  const justified = day.justification_id !== null;
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={day.outcome === "FUTURE"}
      aria-label={`${formatDay(day.day)}: ${label}${time ? ` ${time}` : ""}${justified ? " (justificado)" : ""}`}
      className={cn(
        "flex h-14 w-full flex-col items-center justify-center rounded-md text-xs",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-default",
        OUTCOME_STYLES[day.outcome],
      )}
    >
      <span className="font-medium">{label}</span>
      {time && <span>{time}</span>}
      {justified && <span className="text-[10px]">Justificado</span>}
    </button>
  );
}
```

- [ ] **Step 4: Correr el test de la cuadrícula**

Run: `npm test -- src/components/attendance/week-grid.test.tsx`
Expected: 2 passed.

- [ ] **Step 5: Implementar leyenda, avisos, formularios, panel y página**

`frontend/src/components/attendance/legend.tsx`:
```tsx
import type { Outcome } from "@/lib/api/types";
import { OUTCOME_LABELS, OUTCOME_STYLES } from "@/lib/labels";
import { cn } from "@/lib/utils";

const SHOWN: Outcome[] = ["OK", "LATE", "ABSENT", "UNREGISTERED_CHANGE", "JUSTIFIED", "REST", "CLOSED"];

export function Legend() {
  return (
    <ul aria-label="Leyenda" className="flex flex-wrap gap-2 text-xs">
      {SHOWN.map((outcome) => (
        <li key={outcome} className={cn("rounded px-2 py-1", OUTCOME_STYLES[outcome])}>
          {OUTCOME_LABELS[outcome]}
        </li>
      ))}
    </ul>
  );
}
```

`frontend/src/components/attendance/warnings-list.tsx`:
```tsx
import type { WarningOut } from "@/lib/api/types";
import { WARNING_LABELS } from "@/lib/labels";

export function WarningsList({ warnings }: { warnings: WarningOut[] }) {
  if (warnings.length === 0) return null;
  return (
    <section aria-label="Avisos" className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm">
      <ul className="space-y-1">
        {warnings.map((warning, index) => (
          <li key={`${warning.code}-${warning.employee_id}-${warning.day}-${index}`}>
            <span className="font-medium">{WARNING_LABELS[warning.code]}:</span> {warning.detail}
          </li>
        ))}
      </ul>
    </section>
  );
}
```

`frontend/src/components/attendance/justify-form.tsx`:
```tsx
"use client";

import type { FormEvent } from "react";
import { toast } from "sonner";

import { FormError } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { useCreateJustification } from "@/lib/api/attendance";
import type { Incident, RhType } from "@/lib/api/types";
import { JUSTIFICATION_RH_TYPES, RH_LABELS } from "@/lib/labels";

type Props = { employeeId: number; day: string; incident: Incident; onDone: () => void };

export function JustifyForm({ employeeId, day, incident, onDone }: Props) {
  const mutation = useCreateJustification();
  const options = JUSTIFICATION_RH_TYPES[incident];

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    mutation.mutate(
      {
        employee_id: employeeId,
        day,
        incident,
        reason: String(form.get("reason") ?? "").trim(),
        rh_type: String(form.get("rh_type")) as RhType,
      },
      {
        onSuccess: () => {
          toast.success("Justificación guardada");
          onDone();
        },
      },
    );
  }

  return (
    <form onSubmit={onSubmit} className="space-y-3">
      <h3 className="font-medium">Justificar {incident === "LATE" ? "retardo" : "falta"}</h3>
      <div className="space-y-1">
        <Label htmlFor="reason">Motivo</Label>
        <Input id="reason" name="reason" required maxLength={500} />
      </div>
      <div className="space-y-1">
        <Label htmlFor="rh_type">Tipo en RH</Label>
        <NativeSelect id="rh_type" name="rh_type" defaultValue={options[0]}>
          {options.map((option) => (
            <option key={option} value={option}>
              {RH_LABELS[option]}
            </option>
          ))}
        </NativeSelect>
      </div>
      <FormError error={mutation.error} />
      <Button type="submit" disabled={mutation.isPending}>
        Guardar justificación
      </Button>
    </form>
  );
}
```

`frontend/src/components/attendance/rest-swap-form.tsx`:
```tsx
"use client";

import type { FormEvent } from "react";
import { toast } from "sonner";

import { FormError } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useRestSwap } from "@/lib/api/attendance";
import type { DayOut } from "@/lib/api/types";

type Props = { employeeId: number; day: DayOut; onDone: () => void };

/**
 * Decision #4: the incident goes on the day not worked; another rest day becomes a
 * workday. From an absence we ask for the worked day; from a check-in on a rest day we
 * ask for the day that becomes rest.
 */
export function RestSwapForm({ employeeId, day, onDone }: Props) {
  const mutation = useRestSwap();
  const fromAbsence = day.outcome === "ABSENT";
  const askedLabel = fromAbsence ? "Día de descanso que trabajará" : "Día que descansó a cambio";

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const other = String(new FormData(event.currentTarget).get("other_day"));
    mutation.mutate(
      {
        employee_id: employeeId,
        absent_day: fromAbsence ? day.day : other,
        worked_day: fromAbsence ? other : day.day,
        comment: "Cambio de descanso",
      },
      {
        onSuccess: () => {
          toast.success("Cambio de descanso registrado");
          onDone();
        },
      },
    );
  }

  return (
    <form onSubmit={onSubmit} className="space-y-3">
      <h3 className="font-medium">Cambio de descanso</h3>
      <div className="space-y-1">
        <Label htmlFor="other_day">{askedLabel}</Label>
        <Input id="other_day" name="other_day" type="date" required />
      </div>
      <FormError error={mutation.error} />
      <Button type="submit" variant="outline" disabled={mutation.isPending}>
        Registrar cambio
      </Button>
    </form>
  );
}
```

`frontend/src/components/attendance/exception-form.tsx`:
```tsx
"use client";

import { type FormEvent, useState } from "react";
import { toast } from "sonner";

import { FormError } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { useCreateException } from "@/lib/api/attendance";
import type { ExceptionKind, RhType } from "@/lib/api/types";
import { ABSENCE_RH_TYPES, EXCEPTION_KIND_LABELS, RH_LABELS } from "@/lib/labels";

const EMPLOYEE_KINDS: ExceptionKind[] = [
  "WORK_TO_ABSENCE",
  "PRESENT_NO_CHECKIN",
  "REST_TO_WORK",
  "MANUAL_ABSENCE",
];

type Props = { employeeId: number; day: string; onDone: () => void };

export function ExceptionForm({ employeeId, day, onDone }: Props) {
  const mutation = useCreateException();
  const [kind, setKind] = useState<ExceptionKind>("WORK_TO_ABSENCE");

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    mutation.mutate(
      {
        kind,
        employee_id: employeeId,
        date_from: day,
        date_to: String(form.get("date_to") || day),
        rh_type: kind === "WORK_TO_ABSENCE" ? (String(form.get("rh_type")) as RhType) : null,
        comment: String(form.get("comment") ?? "").trim(),
      },
      {
        onSuccess: () => {
          toast.success("Excepción registrada");
          onDone();
        },
      },
    );
  }

  return (
    <form onSubmit={onSubmit} className="space-y-3">
      <h3 className="font-medium">Agregar excepción</h3>
      <div className="space-y-1">
        <Label htmlFor="kind">Tipo</Label>
        <NativeSelect id="kind" value={kind} onChange={(e) => setKind(e.target.value as ExceptionKind)}>
          {EMPLOYEE_KINDS.map((option) => (
            <option key={option} value={option}>
              {EXCEPTION_KIND_LABELS[option]}
            </option>
          ))}
        </NativeSelect>
      </div>
      {kind === "WORK_TO_ABSENCE" && (
        <div className="space-y-1">
          <Label htmlFor="exception_rh_type">Tipo en RH</Label>
          <NativeSelect id="exception_rh_type" name="rh_type" defaultValue="VACACIONES">
            {ABSENCE_RH_TYPES.map((option) => (
              <option key={option} value={option}>
                {RH_LABELS[option]}
              </option>
            ))}
          </NativeSelect>
        </div>
      )}
      <div className="space-y-1">
        <Label htmlFor="date_to">Hasta (opcional)</Label>
        <Input id="date_to" name="date_to" type="date" min={day} />
      </div>
      <div className="space-y-1">
        <Label htmlFor="comment">Comentario</Label>
        <Input id="comment" name="comment" maxLength={500} />
      </div>
      <FormError error={mutation.error} />
      <Button type="submit" variant="outline" disabled={mutation.isPending}>
        Guardar excepción
      </Button>
    </form>
  );
}
```

`frontend/src/components/attendance/day-panel.tsx`:
```tsx
"use client";

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { formatDay, formatTime } from "@/lib/dates";
import { OUTCOME_LABELS, RH_LABELS, incidentFor } from "@/lib/labels";

import { ExceptionForm } from "./exception-form";
import { JustifyForm } from "./justify-form";
import { RestSwapForm } from "./rest-swap-form";
import type { DaySelection } from "./week-grid";

type Props = { selection: DaySelection | null; onClose: () => void };

export function DayPanel({ selection, onClose }: Props) {
  return (
    <Sheet open={selection !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-md">
        {selection && <DayDetail selection={selection} onDone={onClose} />}
      </SheetContent>
    </Sheet>
  );
}

function describe({ day }: DaySelection): string {
  const parts = [OUTCOME_LABELS[day.outcome]];
  if (day.checkin) parts.push(`checó ${formatTime(day.checkin)}`);
  if (day.minutes_late) parts.push(`${day.minutes_late} min tarde`);
  if (day.rh_type) parts.push(RH_LABELS[day.rh_type]);
  return parts.join(" · ");
}

function DayDetail({ selection, onDone }: { selection: DaySelection; onDone: () => void }) {
  const { day, employee } = selection;
  const incident = incidentFor(day.outcome);
  const canSwap = day.outcome === "ABSENT" || day.outcome === "UNREGISTERED_CHANGE";
  return (
    <>
      <SheetHeader>
        <SheetTitle>
          {employee.short_name} · {formatDay(day.day)}
        </SheetTitle>
        <SheetDescription>{describe(selection)}</SheetDescription>
      </SheetHeader>
      <div className="space-y-8 p-4">
        {day.comment && <p className="text-sm">{day.comment}</p>}
        {incident && day.justification_id === null && (
          <JustifyForm employeeId={employee.id} day={day.day} incident={incident} onDone={onDone} />
        )}
        {canSwap && <RestSwapForm employeeId={employee.id} day={day} onDone={onDone} />}
        <ExceptionForm employeeId={employee.id} day={day.day} onDone={onDone} />
      </div>
    </>
  );
}
```

`frontend/src/components/attendance/week-view.tsx`:
```tsx
"use client";

import { useCallback, useState } from "react";

import { ExportButton } from "@/components/export-button";
import { Loading, QueryError } from "@/components/feedback";
import { PeriodNav } from "@/components/period-nav";
import { useCalendar } from "@/lib/api/attendance";
import { addDays, formatDate, isoWeekNumber, weekStart } from "@/lib/dates";
import { useEnsurePeriod } from "@/lib/period";

import { DayPanel } from "./day-panel";
import { Legend } from "./legend";
import { WarningsList } from "./warnings-list";
import { type DaySelection, WeekGrid } from "./week-grid";

export function WeekView({ requestedStart }: { requestedStart: string | null }) {
  const buildQuery = useCallback((today: string) => `desde=${weekStart(today)}`, []);
  useEnsurePeriod(requestedStart, buildQuery);
  if (requestedStart === null) return <Loading />;
  return <Week from={weekStart(requestedStart)} />;
}

function Week({ from }: { from: string }) {
  const to = addDays(from, 6);
  const calendar = useCalendar(from, to);
  const [selection, setSelection] = useState<DaySelection | null>(null);
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <PeriodNav
          label={`Semana ${isoWeekNumber(from)} · ${formatDate(from)} – ${formatDate(to)}`}
          previousHref={`/semana?desde=${addDays(from, -7)}`}
          nextHref={`/semana?desde=${addDays(from, 7)}`}
        />
        <ExportButton from={from} to={to} />
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
      <DayPanel selection={selection} onClose={() => setSelection(null)} />
    </div>
  );
}
```

`frontend/src/app/(app)/semana/page.tsx`:
```tsx
import { WeekView } from "@/components/attendance/week-view";
import { isIsoDate } from "@/lib/dates";

type Props = { searchParams: Promise<{ desde?: string }> };

export default async function SemanaPage({ searchParams }: Props) {
  const { desde } = await searchParams;
  return <WeekView requestedStart={isIsoDate(desde) ? desde : null} />;
}
```

- [ ] **Step 6: Verificar a mano con el stack en modo demo**

```bash
cd /Users/didiertm/Documents/Projects/TabernasCerveceras
SR_MODE=fake docker compose up -d --build
SR_MODE=fake docker compose run --rm backend python /scripts/seed_demo.py
cd frontend && BACKEND_URL=http://127.0.0.1:8000 FAKE_AUTH_USER=demo FAKE_AUTH_PASSWORD=demo npm run dev
```
Abre http://localhost:3000 → login `demo`/`demo` → `/semana`. Verifica: 7 filas
`EMPLEADO A…F` + `GERENTE DEMO`, celdas con texto y hora; clic en una `Falta` abre el
panel; justificar la cambia a "Justificado" sin recargar.

Run: `npm test && npm run typecheck && npm run lint`
Expected: todos PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src
git commit -m "feat: add weekly attendance grid with justify, rest swap and exception actions

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Vista de incidencias (lista para RH)

**Files:**
- Create: `frontend/src/lib/tsv.ts`, `frontend/src/lib/tsv.test.ts`,
  `frontend/src/components/attendance/rh-table.tsx`, `rh-table.test.tsx`,
  `incidents-view.tsx`, `frontend/src/app/(app)/incidencias/page.tsx`
- Modify: `frontend/src/lib/api/config.ts` (se crea aquí con `useEmployees`; Task 8 lo amplía)

**Interfaces:**
- Consumes: `useIncidents`, `DayPanel`, `DaySelection` (Task 5).
- Produces: `rhRowsToTsv(rows) -> string` (encabezado + filas separadas por tab, fecha
  `dd/mm/aaaa`, tabs/saltos de línea del comentario reemplazados por espacio);
  `RhTable({rows})`; `IncidentsView({from, to})`; `useEmployees()`;
  página `/incidencias?desde=&hasta=`.

- [ ] **Step 1: Escribir los tests (fallan)**

`frontend/src/lib/tsv.test.ts`:
```ts
import { describe, expect, it } from "vitest";

import type { RhRowOut } from "@/lib/api/types";

import { rhRowsToTsv } from "./tsv";

const row = (overrides: Partial<RhRowOut>): RhRowOut => ({
  employee_id: 1,
  name: "APELLIDO UNO",
  day: "2026-09-23",
  rh_type: "RETARDO",
  comment: "",
  ...overrides,
});

describe("rhRowsToTsv", () => {
  it("renders a header and one line per row with Spanish labels", () => {
    expect(rhRowsToTsv([row({}), row({ day: "2026-09-24", rh_type: "VACACIONES" })])).toBe(
      [
        "Nombre\tFecha\tTipo\tComentario",
        "APELLIDO UNO\t23/09/2026\tRetardo\t",
        "APELLIDO UNO\t24/09/2026\tVacaciones\t",
      ].join("\n"),
    );
  });

  it("keeps columns intact when comments contain tabs or newlines", () => {
    const tsv = rhRowsToTsv([row({ comment: "cita\tmédica\nIMSS" })]);
    expect(tsv.split("\n")[1]).toBe("APELLIDO UNO\t23/09/2026\tRetardo\tcita médica IMSS");
  });
});
```

`frontend/src/components/attendance/rh-table.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { RhTable } from "./rh-table";

const rows = [
  { employee_id: 1, name: "APELLIDO UNO", day: "2026-09-23", rh_type: "RETARDO" as const, comment: "" },
];

describe("RhTable", () => {
  it("lists rows with Spanish labels", () => {
    render(<RhTable rows={rows} />);
    const row = screen.getByRole("row", { name: /APELLIDO UNO/ });
    expect(row).toHaveTextContent("23/09/2026");
    expect(row).toHaveTextContent("Retardo");
  });

  it("copies the list as TSV", async () => {
    const user = userEvent.setup();
    const writeText = vi.spyOn(navigator.clipboard, "writeText");
    render(<RhTable rows={rows} />);
    await user.click(screen.getByRole("button", { name: "Copiar para RH" }));
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining("APELLIDO UNO\t23/09/2026"));
  });

  it("says when there is nothing to capture", () => {
    render(<RhTable rows={[]} />);
    expect(screen.getByText("Sin incidencias para capturar en RH.")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `npm test -- src/lib/tsv.test.ts src/components/attendance/rh-table.test.tsx`
Expected: FAIL (módulos inexistentes).

- [ ] **Step 3: Implementar**

`frontend/src/lib/tsv.ts`:
```ts
import type { RhRowOut } from "@/lib/api/types";

import { formatDate } from "./dates";
import { RH_LABELS } from "./labels";

const HEADER = ["Nombre", "Fecha", "Tipo", "Comentario"];

const clean = (value: string) => value.replace(/[\t\r\n]+/g, " ").trim();

/** Tab-separated rows: pastes cleanly into a spreadsheet or the HR tool. */
export function rhRowsToTsv(rows: RhRowOut[]): string {
  const lines = rows.map((row) =>
    [clean(row.name), formatDate(row.day), RH_LABELS[row.rh_type], clean(row.comment)].join("\t"),
  );
  return [HEADER.join("\t"), ...lines].join("\n");
}
```

`frontend/src/components/attendance/rh-table.tsx`:
```tsx
"use client";

import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { RhRowOut } from "@/lib/api/types";
import { formatDate } from "@/lib/dates";
import { RH_LABELS } from "@/lib/labels";
import { rhRowsToTsv } from "@/lib/tsv";

export function RhTable({ rows }: { rows: RhRowOut[] }) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">Sin incidencias para capturar en RH.</p>;
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(rhRowsToTsv(rows));
      toast.success("Lista copiada");
    } catch {
      toast.error("No se pudo copiar; selecciona la tabla manualmente");
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex justify-end">
        <Button variant="outline" onClick={copy}>
          Copiar para RH
        </Button>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Nombre en RH</TableHead>
            <TableHead>Fecha</TableHead>
            <TableHead>Tipo</TableHead>
            <TableHead>Comentario</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row) => (
            <TableRow key={`${row.employee_id}-${row.day}-${row.rh_type}`}>
              <TableCell>{row.name}</TableCell>
              <TableCell>{formatDate(row.day)}</TableCell>
              <TableCell>{RH_LABELS[row.rh_type]}</TableCell>
              <TableCell>{row.comment}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
```

`frontend/src/lib/api/config.ts` (versión inicial; Task 8 la amplía):
```ts
"use client";

import { useQuery } from "@tanstack/react-query";

import { api, unwrap } from "./client";

export const configKeys = {
  employees: ["employees"] as const,
  srPreview: ["employees", "sr-preview"] as const,
  restRules: ["rest-rules"] as const,
  exceptions: (from: string, to: string) => ["exceptions", from, to] as const,
  settings: ["settings"] as const,
};

export function useEmployees() {
  return useQuery({
    queryKey: configKeys.employees,
    queryFn: () => unwrap(api.GET("/employees")),
  });
}
```

`frontend/src/components/attendance/incidents-view.tsx`:
```tsx
"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useCallback, useState } from "react";

import { ExportButton } from "@/components/export-button";
import { Loading, QueryError } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useIncidents } from "@/lib/api/attendance";
import { useEmployees } from "@/lib/api/config";
import type { DayOut, EmployeeRef } from "@/lib/api/types";
import { addDays, formatDay, formatTime, weekStart } from "@/lib/dates";
import { OUTCOME_LABELS, RH_LABELS, incidentFor } from "@/lib/labels";
import { useEnsurePeriod } from "@/lib/period";

import { DayPanel } from "./day-panel";
import { RhTable } from "./rh-table";
import { WarningsList } from "./warnings-list";
import type { DaySelection } from "./week-grid";

type Props = { from: string | null; to: string | null };

export function IncidentsView({ from, to }: Props) {
  const buildQuery = useCallback((today: string) => {
    const start = weekStart(today);
    return `desde=${start}&hasta=${addDays(start, 6)}`;
  }, []);
  useEnsurePeriod(from && to ? from : null, buildQuery);
  if (!from || !to) return <Loading />;
  return <Incidents from={from} to={to} />;
}

function RangeForm({ from, to }: { from: string; to: string }) {
  const router = useRouter();
  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    router.push(`/incidencias?desde=${form.get("desde")}&hasta=${form.get("hasta")}`);
  }
  return (
    <form onSubmit={onSubmit} className="flex flex-wrap items-end gap-2">
      <div className="space-y-1">
        <Label htmlFor="desde">Desde</Label>
        <Input id="desde" name="desde" type="date" defaultValue={from} required />
      </div>
      <div className="space-y-1">
        <Label htmlFor="hasta">Hasta</Label>
        <Input id="hasta" name="hasta" type="date" defaultValue={to} required />
      </div>
      <Button type="submit" variant="outline">
        Ver
      </Button>
    </form>
  );
}

function Incidents({ from, to }: { from: string; to: string }) {
  const incidents = useIncidents(from, to);
  const employees = useEmployees();
  const [selection, setSelection] = useState<DaySelection | null>(null);
  const byId = new Map<number, EmployeeRef>((employees.data ?? []).map((e) => [e.id, e]));
  const select = (day: DayOut) => {
    const employee = byId.get(day.employee_id);
    if (employee) setSelection({ day, employee });
  };
  const unresolved = incidents.data?.incidents.filter((d) => d.outcome === "UNREGISTERED_CHANGE") ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <RangeForm from={from} to={to} />
        <ExportButton from={from} to={to} />
      </div>
      {incidents.isPending && <Loading />}
      {incidents.isError && <QueryError error={incidents.error} onRetry={() => incidents.refetch()} />}
      {incidents.data && (
        <>
          <WarningsList warnings={incidents.data.warnings} />
          <section className="space-y-2">
            <h2 className="text-lg font-semibold">Para capturar en RH</h2>
            <RhTable rows={incidents.data.rh_rows} />
          </section>
          {unresolved.length > 0 && (
            <section className="space-y-2">
              <h2 className="text-lg font-semibold">Pendientes de resolver</h2>
              <IncidentTable days={unresolved} byId={byId} onSelect={select} />
            </section>
          )}
          <section className="space-y-2">
            <h2 className="text-lg font-semibold">Todas las incidencias</h2>
            <IncidentTable days={incidents.data.incidents} byId={byId} onSelect={select} />
          </section>
        </>
      )}
      <DayPanel selection={selection} onClose={() => setSelection(null)} />
    </div>
  );
}

type TableProps = {
  days: DayOut[];
  byId: Map<number, EmployeeRef>;
  onSelect: (day: DayOut) => void;
};

function IncidentTable({ days, byId, onSelect }: TableProps) {
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

function IncidentRow({ day, byId, onSelect }: { day: DayOut } & Omit<TableProps, "days">) {
  const justifiable = incidentFor(day.outcome) !== null && day.justification_id === null;
  const action = justifiable ? "Justificar" : day.outcome === "UNREGISTERED_CHANGE" ? "Resolver" : null;
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

`frontend/src/app/(app)/incidencias/page.tsx`:
```tsx
import { IncidentsView } from "@/components/attendance/incidents-view";
import { isIsoDate } from "@/lib/dates";

type Props = { searchParams: Promise<{ desde?: string; hasta?: string }> };

export default async function IncidenciasPage({ searchParams }: Props) {
  const { desde, hasta } = await searchParams;
  const valid = isIsoDate(desde) && isIsoDate(hasta);
  return <IncidentsView from={valid ? desde : null} to={valid ? hasta : null} />;
}
```

- [ ] **Step 4: Correr y verificar**

Run: `npm test && npm run typecheck && npm run lint`
Expected: todos PASS. Verificación manual (stack demo de Task 5): `/incidencias`
muestra la lista para RH; "Copiar para RH" pega columnas limpias en una hoja de cálculo.

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "feat: add incidents view with copy-ready HR list

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Vista mensual (resumen por empleado)

**Files:**
- Create: `frontend/src/components/attendance/summary-table.tsx`,
  `summary-table.test.tsx`, `month-view.tsx`, `frontend/src/app/(app)/mes/page.tsx`

**Interfaces:**
- Consumes: `useSummary` (Task 5), `useEmployees` (Task 6), `monthRange` (Task 4).
- Produces: `SummaryTable({summaries, names})`; `MonthView({month})` (`month` =
  `"YYYY-MM"` o `null`); página `/mes?mes=YYYY-MM`.

- [ ] **Step 1: Escribir el test (falla)**

`frontend/src/components/attendance/summary-table.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { SummaryOut } from "@/lib/api/types";

import { SummaryTable } from "./summary-table";

const summary: SummaryOut = {
  employee_id: 1,
  period: "2026-09",
  worked: 20,
  late: 3,
  late_justified: 1,
  absent: 2,
  absent_justified: 1,
  justified_by_type: { VACACIONES: 2 },
  unresolved: 1,
};

describe("SummaryTable", () => {
  it("shows totals with justified counts and absence types", () => {
    render(<SummaryTable summaries={[summary]} names={new Map([[1, "EMPLEADO A"]])} />);
    const row = screen.getByRole("row", { name: /EMPLEADO A/ });
    expect(row).toHaveTextContent("20");
    expect(row).toHaveTextContent("3 (1 just.)");
    expect(row).toHaveTextContent("2 (1 just.)");
    expect(row).toHaveTextContent("Vacaciones: 2");
  });
});
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `npm test -- src/components/attendance/summary-table.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implementar**

`frontend/src/components/attendance/summary-table.tsx`:
```tsx
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { RhType, SummaryOut } from "@/lib/api/types";
import { RH_LABELS } from "@/lib/labels";

type Props = { summaries: SummaryOut[]; names: Map<number, string> };

function withJustified(total: number, justified: number): string {
  return justified > 0 ? `${total} (${justified} just.)` : String(total);
}

function absenceTypes(byType: SummaryOut["justified_by_type"]): string {
  return Object.entries(byType)
    .map(([type, count]) => `${RH_LABELS[type as RhType]}: ${count}`)
    .join(", ");
}

export function SummaryTable({ summaries, names }: Props) {
  if (summaries.length === 0) return <p className="text-sm text-muted-foreground">Sin datos.</p>;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Empleado</TableHead>
          <TableHead>Días trabajados</TableHead>
          <TableHead>Retardos</TableHead>
          <TableHead>Faltas</TableHead>
          <TableHead>Ausencias justificadas</TableHead>
          <TableHead>Pendientes</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {summaries.map((s) => (
          <TableRow key={`${s.employee_id}-${s.period}`}>
            <TableCell>{names.get(s.employee_id) ?? s.employee_id}</TableCell>
            <TableCell>{s.worked}</TableCell>
            <TableCell>{withJustified(s.late, s.late_justified)}</TableCell>
            <TableCell>{withJustified(s.absent, s.absent_justified)}</TableCell>
            <TableCell>{absenceTypes(s.justified_by_type)}</TableCell>
            <TableCell>{s.unresolved}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
```

`frontend/src/components/attendance/month-view.tsx`:
```tsx
"use client";

import { useCallback } from "react";

import { ExportButton } from "@/components/export-button";
import { Loading, QueryError } from "@/components/feedback";
import { PeriodNav } from "@/components/period-nav";
import { useSummary } from "@/lib/api/attendance";
import { useEmployees } from "@/lib/api/config";
import { addDays, monthRange } from "@/lib/dates";
import { useEnsurePeriod } from "@/lib/period";

import { SummaryTable } from "./summary-table";

const MONTHS = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];

export function MonthView({ month }: { month: string | null }) {
  const buildQuery = useCallback((today: string) => `mes=${today.slice(0, 7)}`, []);
  useEnsurePeriod(month, buildQuery);
  if (month === null) return <Loading />;
  return <Month month={month} />;
}

function Month({ month }: { month: string }) {
  const { from, to } = monthRange(`${month}-01`);
  const summary = useSummary(from, to, "month");
  const employees = useEmployees();
  const names = new Map((employees.data ?? []).map((e) => [e.id, e.short_name]));
  const [year, monthNumber] = month.split("-").map(Number);
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <PeriodNav
          label={`${MONTHS[monthNumber - 1]} ${year}`}
          previousHref={`/mes?mes=${addDays(from, -1).slice(0, 7)}`}
          nextHref={`/mes?mes=${addDays(to, 1).slice(0, 7)}`}
        />
        <ExportButton from={from} to={to} />
      </div>
      {summary.isPending && <Loading />}
      {summary.isError && <QueryError error={summary.error} onRetry={() => summary.refetch()} />}
      {summary.data && <SummaryTable summaries={summary.data} names={names} />}
    </div>
  );
}
```

`frontend/src/app/(app)/mes/page.tsx`:
```tsx
import { MonthView } from "@/components/attendance/month-view";
import { isIsoDate } from "@/lib/dates";

type Props = { searchParams: Promise<{ mes?: string }> };

export default async function MesPage({ searchParams }: Props) {
  const { mes } = await searchParams;
  return <MonthView month={mes && isIsoDate(`${mes}-01`) ? mes : null} />;
}
```

- [ ] **Step 4: Correr y verificar**

Run: `npm test && npm run typecheck && npm run lint`
Expected: todos PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "feat: add monthly attendance summary view

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Configuración (empleados, descansos, excepciones/cierres, horario)

**Files:**
- Create: `frontend/src/components/config/config-view.tsx`, `employees-tab.tsx`,
  `import-dialog.tsx`, `rest-rules-tab.tsx`, `exceptions-tab.tsx`, `settings-tab.tsx`,
  `frontend/src/app/(app)/configuracion/page.tsx`
- Modify: `frontend/src/lib/api/config.ts`

**Interfaces:**
- Consumes: `configKeys`, `useEmployees` (Task 6); `useCreateException` (Task 5);
  `useInvalidate` (Task 4).
- Produces (`config.ts`): `useUpdateEmployee()` (`{id, changes: EmployeeUpdate}`),
  `useSrPreview(enabled)`, `useImportEmployees()` (`sr_ids: number[]`),
  `useRestRules()`, `useCreateRestRule()`, `useDeleteRestRule()` (`id`),
  `useExceptions(from, to)`, `useDeleteException()` (`id`), `useSettings()`,
  `useSaveSettings()`; `ConfigView`; página `/configuracion`.

La configuración no depende de SR (salvo "Importar de SR"): con SR caído debe seguir
usable (Review Focus #5).

- [ ] **Step 1: Ampliar `config.ts`**

Agrega a `frontend/src/lib/api/config.ts` (y `useMutation` al import de
`@tanstack/react-query`, `useInvalidate` de `./invalidate`, y los tipos
`EmployeeUpdate, RestRuleCreate, SettingsBody` de `./types`):
```ts
const ATTENDANCE = ["attendance"] as const;

export function useUpdateEmployee() {
  const invalidate = useInvalidate(configKeys.employees, ATTENDANCE);
  return useMutation({
    mutationFn: ({ id, changes }: { id: number; changes: EmployeeUpdate }) =>
      unwrap(
        api.PATCH("/employees/{employee_id}", {
          params: { path: { employee_id: id } },
          body: changes,
        }),
      ),
    onSuccess: invalidate,
  });
}

export function useSrPreview(enabled: boolean) {
  return useQuery({
    queryKey: configKeys.srPreview,
    queryFn: () => unwrap(api.GET("/employees/sr-preview")),
    enabled,
  });
}

export function useImportEmployees() {
  const invalidate = useInvalidate(configKeys.employees, ATTENDANCE);
  return useMutation({
    mutationFn: (srIds: number[]) =>
      unwrap(api.POST("/employees/import-from-sr", { body: { sr_ids: srIds } })),
    onSuccess: invalidate,
  });
}

export function useRestRules() {
  return useQuery({
    queryKey: configKeys.restRules,
    queryFn: () => unwrap(api.GET("/rest-rules")),
  });
}

export function useCreateRestRule() {
  const invalidate = useInvalidate(configKeys.restRules, ATTENDANCE);
  return useMutation({
    mutationFn: (body: RestRuleCreate) => unwrap(api.POST("/rest-rules", { body })),
    onSuccess: invalidate,
  });
}

export function useDeleteRestRule() {
  const invalidate = useInvalidate(configKeys.restRules, ATTENDANCE);
  return useMutation({
    mutationFn: (id: number) =>
      unwrap(api.DELETE("/rest-rules/{rule_id}", { params: { path: { rule_id: id } } })),
    onSuccess: invalidate,
  });
}

export function useExceptions(from: string, to: string) {
  return useQuery({
    queryKey: configKeys.exceptions(from, to),
    queryFn: () => unwrap(api.GET("/exceptions", { params: { query: { from, to } } })),
  });
}

export function useDeleteException() {
  const invalidate = useInvalidate(["exceptions"], ATTENDANCE);
  return useMutation({
    mutationFn: (id: number) =>
      unwrap(
        api.DELETE("/exceptions/{exception_id}", { params: { path: { exception_id: id } } }),
      ),
    onSuccess: invalidate,
  });
}

export function useSettings() {
  return useQuery({
    queryKey: configKeys.settings,
    queryFn: () => unwrap(api.GET("/settings")),
  });
}

export function useSaveSettings() {
  const invalidate = useInvalidate(configKeys.settings, ATTENDANCE);
  return useMutation({
    mutationFn: (body: SettingsBody) => unwrap(api.PUT("/settings", { body })),
    onSuccess: invalidate,
  });
}
```

- [ ] **Step 2: Implementar las pestañas**

`frontend/src/components/config/config-view.tsx`:
```tsx
"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

import { EmployeesTab } from "./employees-tab";
import { ExceptionsTab } from "./exceptions-tab";
import { RestRulesTab } from "./rest-rules-tab";
import { SettingsTab } from "./settings-tab";

export function ConfigView() {
  return (
    <Tabs defaultValue="employees" className="space-y-4">
      <TabsList>
        <TabsTrigger value="employees">Empleados</TabsTrigger>
        <TabsTrigger value="rest">Descansos</TabsTrigger>
        <TabsTrigger value="exceptions">Excepciones y cierres</TabsTrigger>
        <TabsTrigger value="settings">Horario</TabsTrigger>
      </TabsList>
      <TabsContent value="employees">
        <EmployeesTab />
      </TabsContent>
      <TabsContent value="rest">
        <RestRulesTab />
      </TabsContent>
      <TabsContent value="exceptions">
        <ExceptionsTab />
      </TabsContent>
      <TabsContent value="settings">
        <SettingsTab />
      </TabsContent>
    </Tabs>
  );
}
```

`frontend/src/components/config/employees-tab.tsx`:
```tsx
"use client";

import { toast } from "sonner";

import { FormError, Loading, QueryError } from "@/components/feedback";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useEmployees, useUpdateEmployee } from "@/lib/api/config";
import type { Area, EmployeeOut, EmployeeUpdate } from "@/lib/api/types";

import { ImportDialog } from "./import-dialog";

const FLAGS = [
  { field: "applies_lateness", label: "Aplica retardos" },
  { field: "tracks_attendance", label: "Checa en SR" },
  { field: "active", label: "Activo" },
] as const;

export function EmployeesTab() {
  const employees = useEmployees();
  const update = useUpdateEmployee();
  const save = (id: number, changes: EmployeeUpdate) =>
    update.mutate({ id, changes }, { onSuccess: () => toast.success("Empleado actualizado") });

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <ImportDialog />
      </div>
      <FormError error={update.error} />
      {employees.isPending && <Loading />}
      {employees.isError && <QueryError error={employees.error} onRetry={() => employees.refetch()} />}
      {employees.data && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Id SR</TableHead>
              <TableHead>Nombre corto</TableHead>
              <TableHead>Nombre en RH</TableHead>
              <TableHead>Área</TableHead>
              {FLAGS.map((flag) => (
                <TableHead key={flag.field}>{flag.label}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {employees.data.map((employee) => (
              <EmployeeRow key={employee.id} employee={employee} onSave={save} />
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}

type RowProps = { employee: EmployeeOut; onSave: (id: number, changes: EmployeeUpdate) => void };

function EmployeeRow({ employee, onSave }: RowProps) {
  return (
    <TableRow>
      <TableCell>{employee.sr_id ?? "—"}</TableCell>
      <TableCell>{employee.short_name}</TableCell>
      <TableCell>
        <Input
          aria-label={`Nombre en RH de ${employee.short_name}`}
          defaultValue={employee.rh_name ?? ""}
          maxLength={160}
          onBlur={(event) => {
            const value = event.target.value.trim() || null;
            if (value !== employee.rh_name) onSave(employee.id, { rh_name: value });
          }}
        />
      </TableCell>
      <TableCell>
        <NativeSelect
          aria-label={`Área de ${employee.short_name}`}
          value={employee.area}
          onChange={(event) => onSave(employee.id, { area: event.target.value as Area })}
        >
          <option value="OTHER">Barra / servicio</option>
          <option value="KITCHEN">Cocina</option>
        </NativeSelect>
      </TableCell>
      {FLAGS.map((flag) => (
        <TableCell key={flag.field}>
          <Checkbox
            aria-label={`${flag.label}: ${employee.short_name}`}
            checked={employee[flag.field]}
            onCheckedChange={(checked) =>
              onSave(employee.id, { [flag.field]: checked === true } as EmployeeUpdate)
            }
          />
        </TableCell>
      ))}
    </TableRow>
  );
}
```

`frontend/src/components/config/import-dialog.tsx`:
```tsx
"use client";

import { type FormEvent, useState } from "react";
import { toast } from "sonner";

import { FormError, Loading, QueryError } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useImportEmployees, useSrPreview } from "@/lib/api/config";

export function ImportDialog() {
  const [open, setOpen] = useState(false);
  const preview = useSrPreview(open);
  const importer = useImportEmployees();

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const ids = new FormData(event.currentTarget).getAll("sr_id").map(Number);
    if (ids.length === 0) return;
    importer.mutate(ids, {
      onSuccess: (created) => {
        toast.success(`Importados: ${created.length}`);
        setOpen(false);
      },
    });
  }

  const pending = preview.data?.filter((e) => !e.imported) ?? [];
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline">Importar de SoftRestaurant</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Importar empleados</DialogTitle>
          <DialogDescription>Empleados de SoftRestaurant que aún no están aquí.</DialogDescription>
        </DialogHeader>
        {preview.isPending && <Loading />}
        {preview.isError && <QueryError error={preview.error} onRetry={() => preview.refetch()} />}
        {preview.data && (
          <form id="import-form" onSubmit={onSubmit} className="space-y-2">
            {pending.length === 0 && <p className="text-sm">Todos ya están importados.</p>}
            {pending.map((employee) => (
              <label key={employee.sr_id} className="flex items-center gap-2 text-sm">
                <Checkbox name="sr_id" value={String(employee.sr_id)} defaultChecked={employee.visible} />
                {employee.sr_id} · {employee.name}
              </label>
            ))}
          </form>
        )}
        <FormError error={importer.error} />
        <DialogFooter>
          <Button type="submit" form="import-form" disabled={importer.isPending || pending.length === 0}>
            Importar seleccionados
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```
(El `Checkbox` de shadcn/Radix envía su `value` en `FormData` cuando tiene `name` y
está dentro de un `<form>`; si la versión instalada no lo hace, reemplázalo aquí por
`<input type="checkbox" name="sr_id" …>`.)

`frontend/src/components/config/rest-rules-tab.tsx`:
```tsx
"use client";

import type { FormEvent } from "react";
import { toast } from "sonner";

import { FormError, Loading, QueryError } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useCreateRestRule, useDeleteRestRule, useEmployees, useRestRules } from "@/lib/api/config";
import { formatDate } from "@/lib/dates";
import { WEEKDAY_LABELS } from "@/lib/labels";

export function RestRulesTab() {
  const rules = useRestRules();
  const employees = useEmployees();
  const remove = useDeleteRestRule();
  const names = new Map((employees.data ?? []).map((e) => [e.id, e.short_name]));

  return (
    <div className="space-y-6">
      <RestRuleForm employees={employees.data ?? []} />
      <FormError error={remove.error} />
      {rules.isPending && <Loading />}
      {rules.isError && <QueryError error={rules.error} onRetry={() => rules.refetch()} />}
      {rules.data && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Empleado</TableHead>
              <TableHead>Día fijo</TableHead>
              <TableHead>Día extra (cada 2 semanas)</TableHead>
              <TableHead>Semana doble desde</TableHead>
              <TableHead>Vigencia</TableHead>
              <TableHead>
                <span className="sr-only">Acciones</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rules.data.map((rule) => (
              <TableRow key={rule.id}>
                <TableCell>{names.get(rule.employee_id) ?? rule.employee_id}</TableCell>
                <TableCell>{WEEKDAY_LABELS[rule.fixed_weekday]}</TableCell>
                <TableCell>{WEEKDAY_LABELS[rule.extra_weekday]}</TableCell>
                <TableCell>{formatDate(rule.double_rest_anchor)}</TableCell>
                <TableCell>
                  {formatDate(rule.valid_from)} – {rule.valid_to ? formatDate(rule.valid_to) : "vigente"}
                </TableCell>
                <TableCell className="text-right">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => remove.mutate(rule.id, { onSuccess: () => toast.success("Regla eliminada") })}
                  >
                    Eliminar
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}

function WeekdaySelect({ id, name, defaultValue }: { id: string; name: string; defaultValue: number }) {
  return (
    <NativeSelect id={id} name={name} defaultValue={String(defaultValue)}>
      {WEEKDAY_LABELS.map((label, index) => (
        <option key={label} value={index}>
          {label}
        </option>
      ))}
    </NativeSelect>
  );
}

function RestRuleForm({ employees }: { employees: { id: number; short_name: string }[] }) {
  const create = useCreateRestRule();

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const validTo = String(form.get("valid_to") ?? "");
    create.mutate(
      {
        employee_id: Number(form.get("employee_id")),
        fixed_weekday: Number(form.get("fixed_weekday")),
        extra_weekday: Number(form.get("extra_weekday")),
        double_rest_anchor: String(form.get("double_rest_anchor")),
        valid_from: String(form.get("valid_from")),
        valid_to: validTo || null,
      },
      { onSuccess: () => toast.success("Regla creada") },
    );
  }

  return (
    <form onSubmit={onSubmit} className="grid gap-3 rounded-lg border p-4 sm:grid-cols-3">
      <h3 className="font-medium sm:col-span-3">Nueva regla de descanso</h3>
      <div className="space-y-1">
        <Label htmlFor="rule_employee">Empleado</Label>
        <NativeSelect id="rule_employee" name="employee_id" required>
          {employees.map((e) => (
            <option key={e.id} value={e.id}>
              {e.short_name}
            </option>
          ))}
        </NativeSelect>
      </div>
      <div className="space-y-1">
        <Label htmlFor="fixed_weekday">Día fijo</Label>
        <WeekdaySelect id="fixed_weekday" name="fixed_weekday" defaultValue={1} />
      </div>
      <div className="space-y-1">
        <Label htmlFor="extra_weekday">Día extra</Label>
        <WeekdaySelect id="extra_weekday" name="extra_weekday" defaultValue={0} />
      </div>
      <div className="space-y-1">
        <Label htmlFor="double_rest_anchor">Un lunes con descanso doble</Label>
        <Input id="double_rest_anchor" name="double_rest_anchor" type="date" required />
      </div>
      <div className="space-y-1">
        <Label htmlFor="valid_from">Vigente desde</Label>
        <Input id="valid_from" name="valid_from" type="date" required />
      </div>
      <div className="space-y-1">
        <Label htmlFor="valid_to">Hasta (opcional)</Label>
        <Input id="valid_to" name="valid_to" type="date" />
      </div>
      <div className="space-y-2 sm:col-span-3">
        <FormError error={create.error} />
        <Button type="submit" disabled={create.isPending || employees.length === 0}>
          Crear regla
        </Button>
      </div>
    </form>
  );
}
```

`frontend/src/components/config/exceptions-tab.tsx`:
```tsx
"use client";

import { type FormEvent, useState } from "react";
import { toast } from "sonner";

import { FormError, Loading, QueryError } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useCreateException } from "@/lib/api/attendance";
import { useDeleteException, useEmployees, useExceptions } from "@/lib/api/config";
import { addDays, formatDate, todayIso } from "@/lib/dates";
import { EXCEPTION_KIND_LABELS, RH_LABELS } from "@/lib/labels";

const WINDOW_DAYS = 45;

export function ExceptionsTab() {
  const [today] = useState(todayIso);
  const from = addDays(today, -WINDOW_DAYS);
  const to = addDays(today, WINDOW_DAYS);
  const exceptions = useExceptions(from, to);
  const employees = useEmployees();
  const remove = useDeleteException();
  const names = new Map((employees.data ?? []).map((e) => [e.id, e.short_name]));

  return (
    <div className="space-y-6">
      <ClosureForm />
      <p className="text-sm text-muted-foreground">
        Excepciones del {formatDate(from)} al {formatDate(to)}. Las de un empleado se agregan
        desde la vista Semana (clic en el día).
      </p>
      <FormError error={remove.error} />
      {exceptions.isPending && <Loading />}
      {exceptions.isError && <QueryError error={exceptions.error} onRetry={() => exceptions.refetch()} />}
      {exceptions.data && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Tipo</TableHead>
              <TableHead>Empleado</TableHead>
              <TableHead>Fechas</TableHead>
              <TableHead>Tipo en RH</TableHead>
              <TableHead>Comentario</TableHead>
              <TableHead>
                <span className="sr-only">Acciones</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {exceptions.data.map((exception) => (
              <TableRow key={exception.id}>
                <TableCell>{EXCEPTION_KIND_LABELS[exception.kind]}</TableCell>
                <TableCell>
                  {exception.employee_id === null ? "Todos" : names.get(exception.employee_id)}
                </TableCell>
                <TableCell>
                  {formatDate(exception.date_from)}
                  {exception.date_to !== exception.date_from && ` – ${formatDate(exception.date_to)}`}
                </TableCell>
                <TableCell>{exception.rh_type ? RH_LABELS[exception.rh_type] : ""}</TableCell>
                <TableCell>{exception.comment}</TableCell>
                <TableCell className="text-right">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() =>
                      remove.mutate(exception.id, { onSuccess: () => toast.success("Excepción eliminada") })
                    }
                  >
                    Eliminar
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}

/** Spec §6: store closures (Ley Seca, 24–25 Dec, storms) apply to everyone. */
function ClosureForm() {
  const create = useCreateException();

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const dateFrom = String(form.get("closure_from"));
    create.mutate(
      {
        kind: "STORE_CLOSED",
        employee_id: null,
        date_from: dateFrom,
        date_to: String(form.get("closure_to") || dateFrom),
        rh_type: null,
        comment: String(form.get("closure_comment") ?? "").trim(),
      },
      { onSuccess: () => toast.success("Cierre registrado") },
    );
  }

  return (
    <form onSubmit={onSubmit} className="grid gap-3 rounded-lg border p-4 sm:grid-cols-3">
      <h3 className="font-medium sm:col-span-3">Cerrar el local (aplica a todos)</h3>
      <div className="space-y-1">
        <Label htmlFor="closure_from">Desde</Label>
        <Input id="closure_from" name="closure_from" type="date" required />
      </div>
      <div className="space-y-1">
        <Label htmlFor="closure_to">Hasta (opcional)</Label>
        <Input id="closure_to" name="closure_to" type="date" />
      </div>
      <div className="space-y-1">
        <Label htmlFor="closure_comment">Motivo</Label>
        <Input id="closure_comment" name="closure_comment" placeholder="Ley Seca, Navidad…" maxLength={500} />
      </div>
      <div className="space-y-2 sm:col-span-3">
        <FormError error={create.error} />
        <Button type="submit" disabled={create.isPending}>
          Registrar cierre
        </Button>
      </div>
    </form>
  );
}
```

`frontend/src/components/config/settings-tab.tsx`:
```tsx
"use client";

import type { FormEvent } from "react";
import { toast } from "sonner";

import { FormError, Loading, QueryError } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSaveSettings, useSettings } from "@/lib/api/config";

export function SettingsTab() {
  const settings = useSettings();
  const save = useSaveSettings();

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    save.mutate(
      {
        entry_time_kitchen: String(form.get("entry_time_kitchen")),
        entry_time_other: String(form.get("entry_time_other")),
        tolerance_minutes: Number(form.get("tolerance_minutes")),
      },
      { onSuccess: () => toast.success("Horario guardado") },
    );
  }

  if (settings.isPending) return <Loading />;
  if (settings.isError) return <QueryError error={settings.error} onRetry={() => settings.refetch()} />;
  return (
    <form onSubmit={onSubmit} className="grid max-w-md gap-3">
      <div className="space-y-1">
        <Label htmlFor="entry_time_kitchen">Entrada cocina</Label>
        <Input id="entry_time_kitchen" name="entry_time_kitchen" type="time" required defaultValue={settings.data.entry_time_kitchen} />
      </div>
      <div className="space-y-1">
        <Label htmlFor="entry_time_other">Entrada barra / servicio</Label>
        <Input id="entry_time_other" name="entry_time_other" type="time" required defaultValue={settings.data.entry_time_other} />
      </div>
      <div className="space-y-1">
        <Label htmlFor="tolerance_minutes">Tolerancia (minutos)</Label>
        <Input
          id="tolerance_minutes"
          name="tolerance_minutes"
          type="number"
          min={0}
          max={60}
          required
          defaultValue={settings.data.tolerance_minutes}
        />
      </div>
      <FormError error={save.error} />
      <Button type="submit" disabled={save.isPending}>
        Guardar horario
      </Button>
    </form>
  );
}
```

`frontend/src/app/(app)/configuracion/page.tsx`:
```tsx
import { ConfigView } from "@/components/config/config-view";

export default function ConfiguracionPage() {
  return <ConfigView />;
}
```

- [ ] **Step 3: Verificar**

Run: `npm test && npm run typecheck && npm run lint && npm run build`
Expected: todo en verde.

Verificación manual (stack demo): editar nombre RH y área se refleja en `/semana`;
crear una regla que se traslapa muestra el mensaje 409 del backend; "Registrar cierre"
para un día pinta la columna como "Cerrado" en la semana; con el backend detenido
(`docker compose stop backend`) cada pestaña muestra el error con "Reintentar".

- [ ] **Step 4: Commit**

```bash
git add frontend/src
git commit -m "feat: add configuration for employees, rest rules, closures and schedule

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: E2E con Playwright, CI del frontend y documentación

**Files:**
- Create: `frontend/playwright.config.ts`, `frontend/e2e/attendance.spec.ts`
- Modify: `.github/workflows/ci.yml` (jobs `frontend` y `e2e`), `CLAUDE.md`,
  `.gitignore`

**Interfaces:**
- Consumes: stack completo en `SR_MODE=fake` + `seed_demo.py` (Plan A, Task 18).
- Produces: `npm run e2e` (flujo crítico: login → semana → justificar → exportar).

- [ ] **Step 1: Escribir el E2E (falla si el stack no está arriba)**

`frontend/playwright.config.ts`:
```ts
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
```

`frontend/e2e/attendance.spec.ts`:
```ts
import { expect, test } from "@playwright/test";

const USER = process.env.FAKE_AUTH_USER ?? "demo";
const PASSWORD = process.env.FAKE_AUTH_PASSWORD ?? "demo";

test("login, review the week, justify an incident and export", async ({ page }) => {
  await page.goto("/semana?desde=2026-09-21");
  await expect(page).toHaveURL(/\/login\?next=/);

  await page.getByLabel("Usuario").fill(USER);
  await page.getByLabel("Contraseña").fill(PASSWORD);
  await page.getByRole("button", { name: "Entrar" }).click();

  await expect(page).toHaveURL(/\/semana\?desde=2026-09-21/);
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

test("the API rejects requests without a session", async ({ request }) => {
  const response = await request.get("/backend/attendance/calendar?from=2026-09-21&to=2026-09-27");
  expect(response.status()).toBe(401);
});
```

Agrega a `.gitignore`: `frontend/playwright-report/`, `frontend/test-results/`,
`frontend/coverage/`.

- [ ] **Step 2: Correr el E2E contra el stack demo**

```bash
cd /Users/didiertm/Documents/Projects/TabernasCerveceras
docker compose down -v
SR_MODE=fake docker compose up -d --build --wait
SR_MODE=fake docker compose run --rm backend python /scripts/seed_demo.py
cd frontend && npx playwright install chromium && npm run e2e
```
Expected: 2 passed. (Cada corrida consume una incidencia sin justificar; para repetir
desde cero, `docker compose down -v` y vuelve a sembrar.)

- [ ] **Step 3: Agregar jobs de CI**

Agrega a `.github/workflows/ci.yml`, bajo `jobs:`:
```yaml
  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-node@v7
        with:
          node-version: 24
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm test -- --coverage

  e2e:
    runs-on: ubuntu-latest
    needs: [backend, frontend]
    env:
      SR_MODE: fake
      FAKE_AUTH_USER: demo
      FAKE_AUTH_PASSWORD: demo
    steps:
      - uses: actions/checkout@v7
      - run: docker compose up -d --build --wait
      - run: docker compose run --rm backend python /scripts/seed_demo.py
      - uses: actions/setup-node@v7
        with:
          node-version: 24
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
        working-directory: frontend
      - run: npx playwright install --with-deps chromium
        working-directory: frontend
      - run: npm run e2e
        working-directory: frontend
      - if: failure()
        uses: actions/upload-artifact@v7
        with:
          name: playwright-report
          path: frontend/playwright-report
      - if: always()
        run: docker compose logs --no-color > compose.log && docker compose down -v
```

- [ ] **Step 4: Documentar comandos**

Agrega a la sección `## Commands` de `CLAUDE.md`:
```markdown
- Frontend dev (from `frontend/`, backend at :8000): `BACKEND_URL=http://127.0.0.1:8000 FAKE_AUTH_USER=demo FAKE_AUTH_PASSWORD=demo npm run dev`
- Frontend checks (from `frontend/`): `npm run lint && npm run typecheck && npm test`
- Regenerate API types after backend changes (backend running): `npm run gen:api`
- E2E (demo stack up and seeded): `npm run e2e`
- Full demo without SR: `SR_MODE=fake docker compose up -d --build --wait && SR_MODE=fake docker compose run --rm backend python /scripts/seed_demo.py` → http://127.0.0.1:3000 (demo/demo)
```

- [ ] **Step 5: Verificación final de la etapa**

Run (raíz): `docker compose down -v && docker compose up -d --build --wait` (con `.env`
real, `SR_MODE=live`) y abre http://127.0.0.1:3000.
Expected: login → `/semana` muestra la semana actual con datos reales de SR (tras la
configuración de Plan A, Task 20); `/incidencias` coincide con lo revisado con el
gerente.

- [ ] **Step 6: Commit**

```bash
git add frontend/playwright.config.ts frontend/e2e .github/workflows/ci.yml CLAUDE.md .gitignore
git commit -m "test: add attendance E2E flow and frontend CI jobs

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
