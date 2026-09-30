"""Load synthetic employees and rest rules for SR_MODE=fake (portfolio demo, E2E).

Usage (repo root): uv run --project backend scripts/seed_demo.py
Docker (demo project): SR_MODE=fake docker compose -p tabernas-demo run --rm backend python /scripts/seed_demo.py
"""

import sys

from tabernas.config import get_settings
from tabernas.db.session import make_engine, make_session_factory
from tabernas.demo import seed_demo_data
from tabernas.domain.validation import DomainValidationError


def main() -> int:
    settings = get_settings()
    if settings.sr_mode != "fake":
        print("seed_demo solo corre con SR_MODE=fake (no mezcles datos demo con reales)")
        return 1
    factory = make_session_factory(make_engine(settings.database_url))
    with factory() as session:
        try:
            created = seed_demo_data(session)
        except DomainValidationError as exc:
            print(str(exc))
            return 1
        session.commit()
    print(f"Empleados demo creados: {len(created)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
