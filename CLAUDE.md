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

## Conventions

- Code, identifiers and commit messages in English; UI text in Spanish.
- Business logic lives in `backend/.../domain/` as pure functions (no DB, no HTTP)
  and is where most tests go.
- Agents never compute figures themselves: they call backend tools and interpret.
  Actions with external side effects (e.g. writing to the RH tool) require explicit
  user approval.
- Each stage in `docs/plan.md` gets a design spec in `docs/specs/` before code.

## Commands

- Check SR connectivity (reads `.env`): `uv run scripts/check_connection.py`

## Important - debugging and fixing

- When troubleshooting problems, always identify the root cause before attempting to fix it.
- Prove the problem first - don't assume you know the cause - if you can't reproduce it, you can't fix it.
- Try one test at the time. Be methodical and systematic. Don't make multiple changes at once.
- Don't jump to conclusions. Gather data, analyze it, and then make informed decisions.