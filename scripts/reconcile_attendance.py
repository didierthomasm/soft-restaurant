"""Acceptance check: SR check-ins per employee must equal SR's own attendance export.

Local only (reads live SR and a file from db_examples/). Prints ids and counts, never names.
Usage (repo root):
  uv run --project backend scripts/reconcile_attendance.py \
      --from 2026-08-01 --to 2026-08-31 --export db_examples/ASISTENCIA_EMPLEADOS.XLS
"""

import argparse
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from tabernas.config import Settings
from tabernas.sr.export_reader import read_attendance_export
from tabernas.sr.pymssql_source import PymssqlSource


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="start", type=date.fromisoformat, required=True)
    parser.add_argument("--to", dest="end", type=date.fromisoformat, required=True)
    parser.add_argument("--export", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    expected = read_attendance_export(args.export, args.start, args.end)
    source = PymssqlSource.from_settings(Settings(sr_mode="live"))
    actual = Counter(c.sr_id for c in source.fetch_checkins(args.start, args.end))
    print(f"{'id SR':>6} {'SR':>5} {'export':>7}")
    for sr_id in sorted(set(expected) | set(actual)):
        flag = "" if expected[sr_id] == actual[sr_id] else "  <-- difiere"
        print(f"{sr_id:>6} {actual[sr_id]:>5} {expected[sr_id]:>7}{flag}")
    print(f"{'total':>6} {sum(actual.values()):>5} {sum(expected.values()):>7}")
    if expected != actual:
        print("NO coincide")
        return 1
    print("Coincide 1:1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
