# Tabernas Cerveceras

Reports and AI agents on top of a SoftRestaurant (SR) point-of-sale database:
attendance incidents (retardos/faltas) and sales trends. Read before designing or
coding a stage:
- `docs/plan.md` — roadmap, stack, business rules, open decisions.
- `docs/db-map.md` — SR schema, reconciled queries, gotchas.
- `docs/specs/` and `docs/plans/` — design spec and implementation plan per stage.
- `docs/private/` (gitignored, local only) — real employee mapping, rest-day rules,
  reconciliation figures, and `setup_employees.py` (configures the real employees
  through the API). Use it; never copy its contents into versioned files.

Status: Stage 1 backend (Plan A) is done and accepted; the Stage 1 frontend (Plan B,
`docs/plans/2026-09-29-etapa-1-plan-b-frontend.md`) is implemented (UI, unit tests, E2E,
CI); acceptance with the manager is pending.

## Backend layout (`backend/src/tabernas/`)

- `domain/` — pure attendance logic (planned calendar, planned vs actual,
  justifications, HR rows, summaries); frozen dataclasses, "today"/"now" as parameters.
- `sr/` — `pymssql_source.py` is the only module that sends SQL to SR;
  `fake_source.py` serves synthetic data when `SR_MODE=fake`.
- `db/` + `alembic/` — our own tables; `repos/` return frozen domain objects, never ORM rows.
- `services/attendance.py` — the only place that joins Postgres config, SR and the domain.
- `api/` — thin routers, response envelope `{success, data, error, meta}`, error mapping.
- `export/` — Excel workbook (Spanish labels).

## Hard rules

- **SR is a live production POS. Read-only, always.** Connect only as `reportes_ro`.
  Only `SELECT`; always `WITH (NOLOCK)`; always bound queries by date. Never run
  DDL/DML against SR, never connect as `sa`.
- Never select `meseros.contraseña` or `meseros.fotografia`.
- **This repo is a public portfolio.** Never commit real employee names, IPs,
  hostnames, sales figures, or files from `db_examples/`. Tests and demo data are
  synthetic. Secrets and connection details live in `.env` (see `.env.example`).
- Any new SR-derived figure must be reconciled against an SR export before it is
  trusted (method in `docs/db-map.md`).

## Gotchas

- SR runs SQL Server 2014 SP1 and only speaks **TLS 1.0**. pymssql fails with
  error 20002 unless `FREETDSCONF` points to the repo's `freetds.conf`.
- `registroasistencias.idempleado` is a zero-padded varchar (`'06'`); SR's own
  reports show it as `6`. `salida` is almost always NULL — only `entrada` matters.
- Sales periods filter on `cheques.cierre`, not `fecha` (the bar closes after
  midnight). Line revenue applies both line and ticket discounts.
- SR "`.XLS`" exports are actually xlsx.
- macOS: `No module named 'tabernas'` → uv marks the editable-install `.pth` hidden and
  Python 3.12.13 skips hidden `.pth` files; run
  `chflags nohidden backend/.venv/lib/python3.12/site-packages/*.pth` (uv re-hides it
  whenever it reinstalls the project), or run tests with `.venv/bin/python -m pytest`.
- `scripts/create_readonly_user.py` is the only sanctioned use of `sa` (one-off,
  already done); the app refuses `SR_DB_USER=sa`.
- Demo data (`seed_demo.py`) refuses to run on a database that already has real
  employees.
- The local Postgres password is not the documented default: it lives in `.env`
  (`POSTGRES_PASSWORD`, `DATABASE_URL`), and tests read `TEST_DATABASE_URL` from `.env`
  when it is not exported (CI exports it).
- The default compose project's Postgres holds the real configuration: never `docker compose down -v` it or start it with `SR_MODE=fake`. Demo/E2E runs use `-p tabernas-demo`.

## Conventions

- Code, identifiers and commit messages in English; UI text in Spanish.
- Business logic lives in `backend/.../domain/` as pure functions (no DB, no HTTP)
  and is where most tests go.
- Agents never compute figures themselves: they call backend tools and interpret.
  Actions with external side effects (e.g. writing to the RH tool) require explicit
  user approval.
- Each stage in `docs/plan.md` gets a design spec in `docs/specs/` before code.

## Commands

- Start everything (default project, uses `.env`, live SR): `docker compose up --build` (API docs at http://127.0.0.1:8000/docs)
- Backend tests (from `backend/`, needs `docker compose up -d db`): `uv run pytest`
- Coverage gates as in CI (from `backend/`): `uv run pytest --cov && uv run coverage report --include="*/tabernas/domain/*" --fail-under=95`
- Live SR tests (local only, never CI): `uv run pytest -m sr`
- New migration (from `backend/`): `uv run alembic revision --autogenerate -m "..."`; the backend container runs `alembic upgrade head` on start
- Lint and types (from `backend/`): `uv run ruff check . && uv run ruff format --check . && uv run pyright`
- Check SR connectivity: `uv run --project backend scripts/check_connection.py`
- Reconcile SR check-ins vs an SR export: `uv run --project backend scripts/reconcile_attendance.py --from YYYY-MM-DD --to YYYY-MM-DD --export db_examples/ASISTENCIA_EMPLEADOS.XLS`
- Configure real employees and rest rules (private, idempotent): `python3 docs/private/setup_employees.py --dry-run`, then without `--dry-run`
- Frontend dev (from `frontend/`, backend at :8000): `BACKEND_URL=http://127.0.0.1:8000 FAKE_AUTH_USER=demo FAKE_AUTH_PASSWORD=demo npm run dev`
- Frontend checks (from `frontend/`): `npm run lint && npm run typecheck && npm test`
- Regenerate API types after backend changes (backend running): `npm run gen:api`
- E2E (demo stack up and seeded): `npm run e2e`
- Full demo without SR, isolated from the real data (separate compose project and volume; stop the real stack first with `docker compose stop`): `SR_MODE=fake docker compose -p tabernas-demo up -d --build --wait && SR_MODE=fake docker compose -p tabernas-demo run --rm backend python /scripts/seed_demo.py` → http://127.0.0.1:3000 (demo/demo); clean up with `docker compose -p tabernas-demo down -v`

## Important - debugging and fixing

- When troubleshooting problems, always identify the root cause before attempting to fix it.
- Prove the problem first - don't assume you know the cause - if you can't reproduce it, you can't fix it.
- Try one test at the time. Be methodical and systematic. Don't make multiple changes at once.
- Don't jump to conclusions. Gather data, analyze it, and then make informed decisions.
