# Tabernas Cerveceras

Reports and AI agents on top of a SoftRestaurant (SR) point-of-sale database:
attendance incidents (retardos/faltas) and sales trends. Read before designing or
coding a stage:
- `docs/plan.md` — roadmap, stack, business rules, open decisions.
- `docs/db-map.md` — SR schema, reconciled queries, gotchas.
- `docs/private/` (gitignored, local only) — real employee mapping, rest-day rules,
  reconciliation figures. Use it; never copy its contents into versioned files.

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

## Conventions

- Code, identifiers and commit messages in English; UI text in Spanish.
- Business logic lives in `backend/.../domain/` as pure functions (no DB, no HTTP)
  and is where most tests go.
- Agents never compute figures themselves: they call backend tools and interpret.
  Actions with external side effects (e.g. writing to the RH tool) require explicit
  user approval.
- Each stage in `docs/plan.md` gets a design spec in `docs/specs/` before code.

## Commands

- Start everything: `docker compose up --build` (API docs at http://127.0.0.1:8000/docs)
- Backend tests (from `backend/`, needs `docker compose up -d db`): `uv run pytest`
- Live SR tests (local only, never CI): `uv run pytest -m sr`
- Lint and types (from `backend/`): `uv run ruff check . && uv run ruff format --check . && uv run pyright`
- Check SR connectivity: `uv run --project backend scripts/check_connection.py`
- Reconcile SR check-ins vs an SR export: `uv run --project backend scripts/reconcile_attendance.py --from YYYY-MM-DD --to YYYY-MM-DD --export db_examples/ASISTENCIA_EMPLEADOS.XLS`
- Demo data (only with `SR_MODE=fake`): `docker compose run --rm -e SR_MODE=fake backend python /scripts/seed_demo.py`

## Important - debugging and fixing

- When troubleshooting problems, always identify the root cause before attempting to fix it.
- Prove the problem first - don't assume you know the cause - if you can't reproduce it, you can't fix it.
- Try one test at the time. Be methodical and systematic. Don't make multiple changes at once.
- Don't jump to conclusions. Gather data, analyze it, and then make informed decisions.