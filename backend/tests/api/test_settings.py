from fastapi.testclient import TestClient

DEFAULTS = {"entry_time_kitchen": "16:30", "entry_time_other": "16:40", "tolerance_minutes": 10}


def test_get_defaults(client: TestClient) -> None:
    assert client.get("/settings").json()["data"] == DEFAULTS


def test_put_round_trip(client: TestClient) -> None:
    wanted = {"entry_time_kitchen": "16:00", "entry_time_other": "16:15", "tolerance_minutes": 5}
    assert client.put("/settings", json=wanted).json()["data"] == wanted
    assert client.get("/settings").json()["data"] == wanted


def test_invalid_settings_are_422(client: TestClient) -> None:
    bad_values = (
        {"entry_time_kitchen": "25:00"},
        {"entry_time_other": "4:40"},
        {"tolerance_minutes": 61},
    )
    for bad in bad_values:
        response = client.put("/settings", json={**DEFAULTS, **bad})
        assert response.status_code == 422, bad
    assert client.get("/settings").json()["data"] == DEFAULTS
