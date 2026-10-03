from datetime import date
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy.orm import Session, sessionmaker

from tabernas.demo import seed_demo_data
from tabernas.sr.fake_source import FakeSource
from tabernas.sr.source import SrUnavailableError
from tests.api.conftest import MakeClient
from tests.support import StubSource

WEEK = {"from": "2026-09-21", "to": "2026-09-27"}
INCIDENT_OUTCOMES = {"LATE", "ABSENT", "UNREGISTERED_CHANGE", "JUSTIFIED"}


@pytest.fixture
def demo_client(session_factory: sessionmaker[Session], make_client: MakeClient) -> TestClient:
    with session_factory() as session:
        seed_demo_data(session)
        session.commit()
    return make_client(FakeSource(today=lambda: date(2026, 9, 27)))


def test_calendar_has_one_day_per_employee(demo_client: TestClient) -> None:
    data = demo_client.get("/attendance/calendar", params=WEEK).json()["data"]
    assert (data["start"], data["end"]) == ("2026-09-21", "2026-09-27")
    assert len(data["employees"]) == 7
    assert len(data["days"]) == 49
    assert not {w["code"] for w in data["warnings"]} & {"NO_REST_RULE", "UNMAPPED_CHECKIN"}


def test_calendar_days_carry_their_exception(demo_client: TestClient) -> None:
    employee_id = demo_client.get("/employees").json()["data"][0]["id"]
    body = {
        "kind": "WORK_TO_ABSENCE",
        "employee_id": employee_id,
        "date_from": "2026-09-23",
        "date_to": "2026-09-24",
        "rh_type": "VACACIONES",
        "comment": "Viaje",
    }
    created = demo_client.post("/exceptions", json=body).json()["data"]
    days = demo_client.get("/attendance/calendar", params=WEEK).json()["data"]["days"]
    own = {d["day"]: d for d in days if d["employee_id"] == employee_id}
    expected = {k: created[k] for k in ("id", "kind", "date_from", "date_to", "rh_type", "comment")}
    assert own["2026-09-23"]["exception"] == expected
    assert own["2026-09-24"]["exception"] == expected
    assert own["2026-09-21"]["exception"] is None


MONTH = {"from": "2026-09-01", "to": "2026-09-27"}


def _items(client: TestClient, path: str, **params: object) -> list[dict[str, object]]:
    response = client.get(path, params={**MONTH, "limit": 100, **params})
    assert response.status_code == 200, response.text
    return response.json()["data"]["items"]


def test_incidents_and_rh_rows_are_consistent(demo_client: TestClient) -> None:
    incidents = _items(demo_client, "/attendance/incidents")
    rows = _items(demo_client, "/attendance/rh-rows")
    assert {d["outcome"] for d in incidents} <= INCIDENT_OUTCOMES
    assert rows
    assert {(r["employee_id"], r["day"]) for r in rows} <= {
        (d["employee_id"], d["day"]) for d in incidents
    }


def test_incidents_are_paginated_with_meta(demo_client: TestClient) -> None:
    first = demo_client.get("/attendance/incidents", params={**MONTH, "limit": 5}).json()
    total = first["meta"]["total"]
    assert (first["meta"]["page"], first["meta"]["limit"]) == (1, 5)
    assert total > 5
    assert len(first["data"]["items"]) == 5
    last_page = (total + 4) // 5
    last = demo_client.get(
        "/attendance/incidents", params={**MONTH, "limit": 5, "page": last_page}
    ).json()
    assert len(last["data"]["items"]) == total - 5 * (last_page - 1)
    beyond = demo_client.get(
        "/attendance/incidents", params={**MONTH, "limit": 5, "page": last_page + 1}
    ).json()
    assert (beyond["data"]["items"], beyond["meta"]["total"]) == ([], total)


def test_incident_filters_combine(demo_client: TestClient) -> None:
    every = _items(demo_client, "/attendance/incidents")
    employee_id = every[0]["employee_id"]
    found = _items(
        demo_client,
        "/attendance/incidents",
        employee_id=employee_id,
        type=["LATE", "ABSENT"],
        status="unjustified",
    )
    assert found == [
        d
        for d in every
        if d["employee_id"] == employee_id
        and d["outcome"] in {"LATE", "ABSENT"}
        and d["justification_id"] is None
    ]


def test_unresolved_ignores_type_and_status(demo_client: TestClient) -> None:
    every = _items(demo_client, "/attendance/incidents")
    changes = sum(d["outcome"] == "UNREGISTERED_CHANGE" for d in every)
    params = {**MONTH, "type": "LATE", "status": "justified"}
    data = demo_client.get("/attendance/incidents", params=params).json()["data"]
    assert data["unresolved"] == changes


def test_rh_rows_follow_the_incident_filters(demo_client: TestClient) -> None:
    every = _items(demo_client, "/attendance/rh-rows")
    employee_id = every[0]["employee_id"]
    assert _items(demo_client, "/attendance/rh-rows", employee_id=employee_id) == [
        r for r in every if r["employee_id"] == employee_id
    ]
    assert {r["rh_type"] for r in _items(demo_client, "/attendance/rh-rows", type="LATE")} <= {
        "RETARDO"
    }
    assert _items(demo_client, "/attendance/rh-rows", type="UNREGISTERED_CHANGE") == []


def test_rh_rows_are_paginated(demo_client: TestClient) -> None:
    every = _items(demo_client, "/attendance/rh-rows")
    page = demo_client.get("/attendance/rh-rows", params={**MONTH, "limit": 2}).json()
    assert page["data"]["items"] == every[:2]
    assert page["meta"] == {"total": len(every), "page": 1, "limit": 2}


@pytest.mark.parametrize(
    "bad", [{"limit": 101}, {"limit": 0}, {"page": 0}, {"type": "OK"}, {"status": "todas"}]
)
def test_bad_incident_queries_are_422(client: TestClient, bad: dict[str, object]) -> None:
    for path in ("/attendance/incidents", "/attendance/rh-rows"):
        assert client.get(path, params={**WEEK, **bad}).status_code == 422


def test_monthly_summary(demo_client: TestClient) -> None:
    params = {"from": "2026-09-01", "to": "2026-09-30", "group": "month"}
    data = demo_client.get("/attendance/summary", params=params).json()["data"]
    assert [s["period"] for s in data] == ["2026-09"] * 7
    assert all(isinstance(s["justified_by_type"], dict) for s in data)


def test_bad_ranges_are_422(client: TestClient) -> None:
    assert client.get("/attendance/calendar", params={"from": "2026-09-21"}).status_code == 422
    reversed_range = {"from": "2026-09-27", "to": "2026-09-21"}
    assert client.get("/attendance/calendar", params=reversed_range).status_code == 422
    too_long = {"from": "2026-01-01", "to": "2026-12-31"}
    assert client.get("/attendance/incidents", params=too_long).status_code == 422


def test_sr_down_is_503(make_client: MakeClient) -> None:
    client = make_client(StubSource(error=SrUnavailableError("x")))
    response = client.get("/attendance/calendar", params=WEEK)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SR_UNAVAILABLE"


def test_export_xlsx(demo_client: TestClient) -> None:
    response = demo_client.get("/attendance/export.xlsx", params=WEEK)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    disposition = response.headers["content-disposition"]
    assert 'filename="asistencia_2026-09-21_2026-09-27.xlsx"' in disposition
    workbook = load_workbook(BytesIO(response.content))
    assert workbook["Calendario"].max_row == 8  # header + 7 employees


def test_export_xlsx_summary_grouped_by_month(demo_client: TestClient) -> None:
    params = {"from": "2026-09-01", "to": "2026-09-30", "group": "month"}
    response = demo_client.get("/attendance/export.xlsx", params=params)
    assert response.status_code == 200
    workbook = load_workbook(BytesIO(response.content))
    resumen = workbook["Resumen"]
    periods = {str(row[1].value) for row in resumen.iter_rows(min_row=2)}
    assert periods == {"2026-09"}
