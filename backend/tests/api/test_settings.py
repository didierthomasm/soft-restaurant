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


REVIEW_DEFAULTS = {"streak_days": 2, "late_week": 2, "late_weeks": 3}


def test_review_settings_defaults(client: TestClient) -> None:
    assert client.get("/settings/review").json()["data"] == REVIEW_DEFAULTS


def test_review_settings_round_trip_leaves_attendance_settings_alone(client: TestClient) -> None:
    wanted = {"streak_days": 3, "late_week": 1, "late_weeks": 5}
    assert client.put("/settings/review", json=wanted).json()["data"] == wanted
    assert client.get("/settings/review").json()["data"] == wanted
    assert client.get("/settings").json()["data"] == DEFAULTS


def test_invalid_review_settings_are_422(client: TestClient) -> None:
    for bad in ({"streak_days": 0}, {"late_week": 8}, {"late_weeks": 6}):
        response = client.put("/settings/review", json={**REVIEW_DEFAULTS, **bad})
        assert response.status_code == 422, bad
    assert client.get("/settings/review").json()["data"] == REVIEW_DEFAULTS
