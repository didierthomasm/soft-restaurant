from fastapi.testclient import TestClient


def _employee(client: TestClient) -> int:
    return client.post("/employees", json={"short_name": "EMPLEADO A"}).json()["data"]["id"]


def _single_day(kind: str, employee_id: int | None, day: str, **extra: object) -> dict[str, object]:
    return {"kind": kind, "employee_id": employee_id, "date_from": day, "date_to": day, **extra}


def test_store_closure_for_everyone(client: TestClient) -> None:
    body = {
        "kind": "STORE_CLOSED",
        "date_from": "2026-12-24",
        "date_to": "2026-12-25",
        "comment": "Navidad",
    }
    created = client.post("/exceptions", json=body)
    assert created.status_code == 201
    assert created.json()["data"]["employee_id"] is None
    week = client.get("/exceptions", params={"from": "2026-12-21", "to": "2026-12-27"})
    assert [e["comment"] for e in week.json()["data"]] == ["Navidad"]
    later = client.get("/exceptions", params={"from": "2026-12-28", "to": "2026-12-31"})
    assert later.json()["data"] == []


def test_invalid_exceptions_are_422(client: TestClient) -> None:
    employee_id = _employee(client)
    closure_with_employee = _single_day("STORE_CLOSED", employee_id, "2026-09-24")
    absence_without_type = _single_day("WORK_TO_ABSENCE", employee_id, "2026-09-24")
    assert client.post("/exceptions", json=closure_with_employee).status_code == 422
    assert client.post("/exceptions", json=absence_without_type).status_code == 422


def test_rest_swap_creates_both_and_is_atomic(client: TestClient) -> None:
    employee_id = _employee(client)
    swap = {"employee_id": employee_id, "absent_day": "2026-09-23", "worked_day": "2026-09-29"}
    created = client.post("/exceptions/rest-swap", json=swap)
    assert created.status_code == 201
    assert [(e["kind"], e["rh_type"]) for e in created.json()["data"]] == [
        ("WORK_TO_ABSENCE", "DESCANSO"),
        ("REST_TO_WORK", None),
    ]
    clash = {"employee_id": employee_id, "absent_day": "2026-09-30", "worked_day": "2026-09-29"}
    assert client.post("/exceptions/rest-swap", json=clash).status_code == 409
    listed = client.get("/exceptions", params={"from": "2026-09-21", "to": "2026-10-04"})
    assert len(listed.json()["data"]) == 2


def test_patch_and_delete(client: TestClient) -> None:
    employee_id = _employee(client)
    body = _single_day("WORK_TO_ABSENCE", employee_id, "2026-09-23", rh_type="VACACIONES")
    created = client.post("/exceptions", json=body).json()["data"]
    url = f"/exceptions/{created['id']}"
    patched = client.patch(url, json={"date_to": "2026-09-25", "comment": "Vacaciones"})
    data = patched.json()["data"]
    assert (data["date_to"], data["comment"]) == ("2026-09-25", "Vacaciones")
    assert client.patch(url, json={"kind": "STORE_CLOSED"}).status_code == 422
    assert client.delete(url).status_code == 200
    assert client.delete(url).status_code == 404
