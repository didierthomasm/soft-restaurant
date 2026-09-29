from fastapi.testclient import TestClient

from tabernas.sr.source import SrEmployee, SrUnavailableError
from tests.api.conftest import MakeClient
from tests.support import StubSource

SR_EMPLOYEES = [
    SrEmployee(sr_id=6, name="EMPLEADO A", kind=1, visible=True),
    SrEmployee(sr_id=11, name="EMPLEADO B", kind=1, visible=True),
]


def test_create_list_get_patch(client: TestClient) -> None:
    response = client.post(
        "/employees", json={"sr_id": 101, "short_name": "EMPLEADO A", "area": "KITCHEN"}
    )
    assert response.status_code == 201
    employee = response.json()["data"]
    assert (employee["area"], employee["active"], employee["rh_name"]) == ("KITCHEN", True, None)
    assert client.get("/employees").json()["data"] == [employee]
    assert client.get(f"/employees/{employee['id']}").json()["data"] == employee
    patched = client.patch(f"/employees/{employee['id']}", json={"rh_name": "APELLIDO NOMBRE"})
    assert patched.json()["data"]["rh_name"] == "APELLIDO NOMBRE"


def test_active_only_filter(client: TestClient) -> None:
    created = client.post("/employees", json={"short_name": "EMPLEADO A"}).json()["data"]
    client.patch(f"/employees/{created['id']}", json={"active": False})
    assert client.get("/employees", params={"active_only": True}).json()["data"] == []


def test_missing_employee_is_404(client: TestClient) -> None:
    response = client.get("/employees/999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_duplicate_sr_id_is_409(client: TestClient) -> None:
    client.post("/employees", json={"sr_id": 101, "short_name": "EMPLEADO A"})
    response = client.post("/employees", json={"sr_id": 101, "short_name": "OTRO"})
    assert response.status_code == 409


def test_invalid_payloads_are_422(client: TestClient) -> None:
    assert client.post("/employees", json={"short_name": "X", "area": "BAR"}).status_code == 422
    assert client.post("/employees", json={"short_name": ""}).status_code == 422
    created = client.post("/employees", json={"short_name": "X"}).json()["data"]
    url = f"/employees/{created['id']}"
    assert client.patch(url, json={"sr_id": 5}).status_code == 422
    assert client.patch(url, json={"short_name": None}).status_code == 422
    assert client.patch(url, json={"rh_name": None}).status_code == 200


def test_sr_preview_marks_imported(make_client: MakeClient) -> None:
    client = make_client(StubSource(employees=SR_EMPLOYEES))
    client.post("/employees", json={"sr_id": 6, "short_name": "EMPLEADO A"})
    data = client.get("/employees/sr-preview").json()["data"]
    assert [(d["sr_id"], d["name"], d["imported"]) for d in data] == [
        (6, "EMPLEADO A", True),
        (11, "EMPLEADO B", False),
    ]


def test_import_from_sr_is_idempotent(make_client: MakeClient) -> None:
    client = make_client(StubSource(employees=SR_EMPLOYEES))
    first = client.post("/employees/import-from-sr", json={"sr_ids": [11, 6]})
    assert first.status_code == 201
    assert [(e["sr_id"], e["short_name"], e["area"]) for e in first.json()["data"]] == [
        (6, "EMPLEADO A", "OTHER"),
        (11, "EMPLEADO B", "OTHER"),
    ]
    again = client.post("/employees/import-from-sr", json={"sr_ids": [6, 11]})
    assert again.json()["data"] == []


def test_import_unknown_sr_id_is_422(make_client: MakeClient) -> None:
    client = make_client(StubSource(employees=SR_EMPLOYEES))
    response = client.post("/employees/import-from-sr", json={"sr_ids": [6, 99]})
    assert response.status_code == 422
    assert "99" in response.json()["error"]["message"]


def test_sr_down_is_503(make_client: MakeClient) -> None:
    client = make_client(StubSource(error=SrUnavailableError("x")))
    assert client.get("/employees/sr-preview").status_code == 503
