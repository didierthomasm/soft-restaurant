from collections import Counter
from datetime import date, datetime
from pathlib import Path

import pytest
from openpyxl import Workbook

from tabernas.sr.export_reader import read_attendance_export

HEADER = ["FECHA", "CLAVEEMPLEADO", "NOMBRE", "ENTRADA", "SALIDA", "HORASTRABAJADAS"]


def write_export(path: Path, rows: list[list[object]]) -> Path:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    for row in [["REPORTE DEMO", datetime(2026, 9, 28)], ["EMPRESA DEMO"], HEADER, *rows]:
        sheet.append(row)
    workbook.save(path)
    return path


def test_counts_checkins_per_employee_within_range(tmp_path: Path) -> None:
    export = write_export(
        tmp_path / "ASISTENCIA.XLS",  # SR's misleading extension
        [
            [datetime(2026, 8, 1), 6, "EMPLEADO A", datetime(2026, 8, 1, 16, 41, 31), "/  /", 0],
            [datetime(2026, 8, 2), 6, "EMPLEADO A", datetime(2026, 8, 2, 16, 30, 33), "/  /", 0],
            [datetime(2026, 8, 2), 11, "EMPLEADO B", datetime(2026, 8, 2, 16, 35), "/  /", 0],
            [datetime(2026, 9, 1), 11, "EMPLEADO B", datetime(2026, 9, 1, 16, 35), "/  /", 0],
            [None, None, "TOTAL", None, None, None],
        ],
    )
    counts = read_attendance_export(export, date(2026, 8, 1), date(2026, 8, 31))
    assert counts == Counter({6: 2, 11: 1})


def test_rejects_files_without_the_header(tmp_path: Path) -> None:
    path = tmp_path / "other.xlsx"
    Workbook().save(path)
    with pytest.raises(ValueError, match="export de asistencia"):
        read_attendance_export(path, date(2026, 8, 1), date(2026, 8, 31))
