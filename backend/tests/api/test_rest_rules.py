from fastapi.testclient import TestClient


def _employee(client: TestClient) -> int:
    return client.post("/employees", json={"short_name": "EMPLEADO A"}).json()["data"]["id"]


def _rule(employee_id: int, **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "employee_id": employee_id,
        "fixed_weekday": 1,
        "extra_weekday": 0,
        "double_rest_anchor": "2026-09-28",
        "valid_from": "2026-01-01",
    }
    return {**body, **overrides}


def test_crud(client: TestClient) -> None:
    employee_id = _employee(client)
    created = client.post("/rest-rules", json=_rule(employee_id))
    assert created.status_code == 201
    rule = created.json()["data"]
    assert rule["valid_to"] is None
    listed = client.get("/rest-rules", params={"employee_id": employee_id}).json()["data"]
    assert listed == [rule]
    patched = client.patch(f"/rest-rules/{rule['id']}", json={"valid_to": "2026-12-31"})
    assert patched.json()["data"]["valid_to"] == "2026-12-31"
    assert client.delete(f"/rest-rules/{rule['id']}").json() == {
        "success": True,
        "data": None,
        "error": None,
        "meta": None,
    }
    assert client.get("/rest-rules").json()["data"] == []


def test_errors(client: TestClient) -> None:
    employee_id = _employee(client)
    client.post("/rest-rules", json=_rule(employee_id))
    assert client.post("/rest-rules", json=_rule(employee_id)).status_code == 409
    assert client.post("/rest-rules", json=_rule(999)).status_code == 404
    tuesday = _rule(employee_id, double_rest_anchor="2026-09-29", valid_from="2027-01-01")
    assert client.post("/rest-rules", json=tuesday).status_code == 422
    assert client.post("/rest-rules", json=_rule(employee_id, fixed_weekday=7)).status_code == 422
    assert client.patch("/rest-rules/1", json={"fixed_weekday": None}).status_code == 422
