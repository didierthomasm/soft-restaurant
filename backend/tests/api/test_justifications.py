from fastapi.testclient import TestClient

WEEK = {"from": "2026-09-21", "to": "2026-09-27"}


def _employee(client: TestClient) -> int:
    return client.post("/employees", json={"short_name": "EMPLEADO A"}).json()["data"]["id"]


def test_create_with_default_rh_type_and_list(client: TestClient) -> None:
    employee_id = _employee(client)
    body = {
        "employee_id": employee_id,
        "day": "2026-09-23",
        "incident": "ABSENT",
        "reason": "Enfermo",
    }
    created = client.post("/justifications", json=body)
    assert created.status_code == 201
    assert created.json()["data"]["rh_type"] == "FALTA_JUSTIFICADA"
    assert client.get("/justifications", params=WEEK).json()["data"] == [created.json()["data"]]
    assert client.post("/justifications", json=body).status_code == 409


def test_list_requires_a_bounded_range(client: TestClient) -> None:
    assert client.get("/justifications").status_code == 422
    too_long = {"from": "2026-01-01", "to": "2026-12-31"}
    assert client.get("/justifications", params=too_long).status_code == 422


def test_patch_validates_rh_type_and_delete(client: TestClient) -> None:
    employee_id = _employee(client)
    body = {"employee_id": employee_id, "day": "2026-09-23", "incident": "LATE", "reason": "x"}
    created = client.post("/justifications", json=body).json()["data"]
    url = f"/justifications/{created['id']}"
    assert client.patch(url, json={"rh_type": "VACACIONES"}).status_code == 422
    assert client.patch(url, json={"reason": ""}).status_code == 422
    assert client.patch(url, json={"reason": "Tráfico"}).json()["data"]["reason"] == "Tráfico"
    assert client.delete(url).status_code == 200
