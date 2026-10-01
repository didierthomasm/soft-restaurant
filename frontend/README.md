# Tabernas Cerveceras — frontend

Next.js (App Router) UI for the attendance reports: weekly planned-vs-actual grid,
incidents and justifications, rest swaps, exceptions, monthly summary, configuration
and Excel export. The browser only talks to Next; `/backend/*` is rewritten to the
FastAPI backend (`BACKEND_URL`). Access is behind a fake demo login (not security).
UI text is in Spanish; code is in English.

## Commands (run from `frontend/`)

Before starting local development, run `cp .env.example .env.local`. Next.js reads
environment files in `frontend/`; the repository root `.env` is used by Docker
Compose. The example configures the fake login as `demo` / `demo`.

If the Docker frontend is already running on port 3000, use `npm run dev -- --port
3001` and open http://localhost:3001 to avoid overlapping local and Docker servers.

```bash
npm install
npm run dev          # http://localhost:3000, needs the backend on BACKEND_URL
npm test             # Vitest unit/component tests (add -- --coverage)
npm run typecheck
npm run lint
npm run build
npm run gen:api      # regenerate src/lib/api/schema.d.ts from the running backend
npm run e2e          # Playwright against the demo stack (below)
```

## Demo stack (synthetic data, never touches real data)

From the repo root, in a separate compose project:

```bash
SR_MODE=fake docker compose -p tabernas-demo up -d --build --wait backend
SR_MODE=fake docker compose -p tabernas-demo run --rm backend python /scripts/seed_demo.py
docker compose -p tabernas-demo down -v   # when done
```

## More

See the root `CLAUDE.md` for conventions and hard rules, and `docs/plans/` for the
Stage 1 frontend plan.
