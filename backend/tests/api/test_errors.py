from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tabernas.domain.validation import DomainValidationError
from tabernas.repos.errors import ConflictError, NotFoundError
from tabernas.sr.source import SrUnavailableError
from tests.api.conftest import MakeClient

ERRORS: dict[str, Exception] = {
    "validation": DomainValidationError("Dato malo"),
    "missing": NotFoundError("No existe"),
    "conflict": ConflictError("Choca"),
    "sr": SrUnavailableError("x"),
    "crash": RuntimeError("secret detail"),
}


@pytest.fixture
def boom_client(make_client: MakeClient) -> TestClient:
    client = make_client()
    app = cast(FastAPI, client.app)

    def boom(kind: str) -> None:
        raise ERRORS[kind]

    def typed(number: int) -> int:
        return number

    app.add_api_route("/boom/{kind}", boom)
    app.add_api_route("/typed/{number}", typed)
    return client


@pytest.mark.parametrize(
    ("kind", "status", "code", "message"),
    [
        ("validation", 422, "VALIDATION_ERROR", "Dato malo"),
        ("missing", 404, "NOT_FOUND", "No existe"),
        ("conflict", 409, "CONFLICT", "Choca"),
        ("sr", 503, "SR_UNAVAILABLE", "No se pudo leer SoftRestaurant. Revisa Tailscale."),
    ],
)
def test_mapped_errors_use_the_envelope(
    boom_client: TestClient, kind: str, status: int, code: str, message: str
) -> None:
    response = boom_client.get(f"/boom/{kind}")
    assert response.status_code == status
    assert response.json() == {
        "success": False,
        "data": None,
        "error": {"code": code, "message": message},
        "meta": None,
    }


def test_unhandled_error_hides_details(boom_client: TestClient) -> None:
    response = boom_client.get("/boom/crash")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL"
    assert "secret" not in response.text


def test_request_validation_error_lists_fields(boom_client: TestClient) -> None:
    response = boom_client.get("/typed/abc")
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["meta"]["errors"][0]["loc"] == ["path", "number"]


def test_unknown_route_is_404_envelope(client: TestClient) -> None:
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
