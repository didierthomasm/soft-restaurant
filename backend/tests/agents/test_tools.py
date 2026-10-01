import json
from dataclasses import replace
from datetime import date, datetime
from typing import Any

import pytest

from tabernas.agents.weekly_review.tools import TOOL_DEFINITIONS, ReviewTools, ToolError
from tabernas.domain.types import DayResult, Outcome
from tests.agents.helpers import make_context
from tests.domain.factories import result

TUE, WED = date(2026, 9, 22), date(2026, 9, 23)


def week_with_comments() -> list[DayResult]:
    return [
        result(
            Outcome.ABSENT,
            employee_id=1,
            day=WED,
            comment="Avisó Beto Prueba que Ana Prueba estaba enferma",
        ),
        replace(
            result(Outcome.UNREGISTERED_CHANGE, employee_id=2, day=TUE),
            checkin=datetime(2026, 9, 22, 16, 41),
        ),
        result(Outcome.OK, employee_id=2, day=WED),
    ]


def call(tools: ReviewTools, name: str, **arguments: Any) -> Any:
    return json.loads(tools.call(name, arguments))


def test_tool_definitions_are_strict_and_closed() -> None:
    assert [t["name"] for t in TOOL_DEFINITIONS] == [
        "get_week_findings",
        "get_week_incidents",
        "get_employee_history",
        "get_employee_week",
    ]
    for tool in TOOL_DEFINITIONS:
        assert tool["strict"] is True
        assert tool["input_schema"]["additionalProperties"] is False


def test_week_findings_use_pseudonyms() -> None:
    findings = call(ReviewTools(make_context(week_with_comments())), "get_week_findings")
    assert [(f["kind"], f["employee"]) for f in findings] == [
        ("REST_DAY_CHECKIN", "E2"),
        ("ABSENT_NO_EXCEPTION", "E1"),
    ]
    assert findings[0]["facts"] == {"checkin_time": "16:41"}
    assert findings[1]["days"] == ["2026-09-23"]


def test_free_text_comments_are_scrubbed() -> None:
    # Review Focus #1: the manager's free text may name employees.
    raw = ReviewTools(make_context(week_with_comments())).call("get_week_incidents", {})
    assert "prueba" not in raw.casefold()
    data = json.loads(raw)
    absent = next(i for i in data["incidents"] if i["outcome"] == "ABSENT")
    assert absent["comment"] == "Avisó E2 que E1 estaba enferma"
    assert data["rh_rows"] == [
        {
            "employee": "E1",
            "day": "2026-09-23",
            "rh_type": "FALTA_INJUSTIFICADA",
            "comment": "Avisó E2 que E1 estaba enferma",
        }
    ]


def test_employee_week_lists_each_day() -> None:
    days = call(ReviewTools(make_context(week_with_comments())), "get_employee_week", employee="E2")
    assert [(d["day"], d["weekday"], d["outcome"], d["checkin"]) for d in days] == [
        ("2026-09-22", "martes", "UNREGISTERED_CHANGE", "16:41"),
        ("2026-09-23", "miércoles", "OK", None),
    ]


def test_employee_history_covers_only_the_requested_weeks() -> None:
    history = [
        result(Outcome.LATE, employee_id=1, day=date(2026, 9, 16)),  # W38
        result(Outcome.ABSENT, employee_id=1, day=date(2026, 9, 9)),  # W37
        result(Outcome.LATE, employee_id=2, day=date(2026, 9, 16)),
    ]
    tools = ReviewTools(make_context(history=history))
    assert call(tools, "get_employee_history", employee="E1", weeks=1) == [
        {
            "week": "2026-W38",
            "worked": 1,
            "late": 1,
            "late_justified": 0,
            "absent": 0,
            "absent_justified": 0,
            "unresolved": 0,
        }
    ]
    two_weeks = call(tools, "get_employee_history", employee="E1", weeks=2)
    assert [w["week"] for w in two_weeks] == ["2026-W37", "2026-W38"]


@pytest.mark.parametrize(
    "arguments",
    [
        {"employee": "E99", "weeks": 1},
        {"employee": "Ana", "weeks": 1},
        {"employee": "E1", "weeks": 0},
        {"employee": "E1", "weeks": 9},
        {"employee": "E1", "weeks": True},
        {"employee": "E1"},
        {},
    ],
)
def test_bad_history_arguments_raise_tool_errors(arguments: dict[str, Any]) -> None:
    with pytest.raises(ToolError):
        ReviewTools(make_context()).call("get_employee_history", arguments)


def test_unknown_tool_raises() -> None:
    with pytest.raises(ToolError, match="desconocida"):
        ReviewTools(make_context()).call("drop_tables", {})
