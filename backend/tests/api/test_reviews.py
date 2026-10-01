from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tabernas.domain.review_types import (
    Finding,
    FindingKind,
    Narrative,
    NarrativeItem,
    Priority,
    ProposedRhRow,
    ReviewResult,
    ReviewStatus,
    ReviewTrigger,
    SuggestedAction,
)
from tabernas.domain.types import RhType
from tabernas.repos.reviews import ReviewRepo
from tabernas.sr.source import SrUnavailableError
from tests.api.conftest import FIXED_NOW, MakeClient
from tests.repos.helpers import make_employee
from tests.support import StubSource

WEEK_39 = {"year": 2026, "week": 39}


def ready_review(session: Session) -> int:
    employee = make_employee(session, 7, short_name="EMPLEADO G")
    token = "{E" + str(employee.id) + "}"
    repo = ReviewRepo(session)
    review = repo.enqueue(iso_year=2026, iso_week=39, trigger=ReviewTrigger.MANUAL)
    finding = Finding(
        f"ABSENT_NO_EXCEPTION:{employee.id}:2026-09-23",
        FindingKind.ABSENT_NO_EXCEPTION,
        employee.id,
        (date(2026, 9, 23),),
    )
    narrative = Narrative(
        f"Una falta de {token}.",
        (NarrativeItem(finding.id, Priority.HIGH, f"{token} faltó.", SuggestedAction.JUSTIFY),),
    )
    row = ProposedRhRow(employee.id, date(2026, 9, 23), RhType.FALTA_INJUSTIFICADA, "")
    result = ReviewResult(
        status=ReviewStatus.READY,
        as_of=FIXED_NOW,
        findings=(finding,),
        rh_rows=(row,),
        narrative=narrative,
        model="claude-opus-5-5",
        input_tokens=900,
        output_tokens=150,
        error=None,
    )
    repo.complete(review.id, result)
    session.commit()
    return review.id


def test_post_enqueues_and_rejects_a_second_run(client: TestClient) -> None:
    response = client.post("/reviews", json=WEEK_39)
    assert response.status_code == 202
    data = response.json()["data"]
    assert (data["year"], data["week"], data["status"], data["trigger"]) == (
        2026,
        39,
        "QUEUED",
        "MANUAL",
    )
    conflict = client.post("/reviews", json=WEEK_39)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "CONFLICT"


def test_post_rejects_weeks_that_do_not_exist(client: TestClient) -> None:
    assert client.post("/reviews", json={"year": 2026, "week": 54}).status_code == 422
    response = client.post("/reviews", json={"year": 2025, "week": 53})
    assert response.status_code == 422
    assert "Semana ISO inválida" in response.json()["error"]["message"]


def test_list_filters_by_week(client: TestClient) -> None:
    client.post("/reviews", json={"year": 2026, "week": 38})
    client.post("/reviews", json=WEEK_39)
    assert [r["week"] for r in client.get("/reviews").json()["data"]] == [39, 38]
    only_38 = client.get("/reviews", params={"year": 2026, "week": 38}).json()["data"]
    assert [r["week"] for r in only_38] == [38]
    assert client.get("/reviews", params={"year": 2026}).status_code == 422


def test_detail_renders_names_and_flags_stale_data(client: TestClient, session: Session) -> None:
    review_id = ready_review(session)
    data = client.get(f"/reviews/{review_id}").json()["data"]
    assert data["narrative"]["summary"] == "Una falta de EMPLEADO G."
    assert data["narrative"]["items"][0]["explanation"] == "EMPLEADO G faltó."
    assert data["findings"][0]["employee_name"] == "EMPLEADO G"
    assert data["rh_rows"][0]["name"] == "EMPLEADO G"
    assert data["rh_rows"][0]["rh_type"] == "FALTA_INJUSTIFICADA"
    assert (data["model"], data["input_tokens"], data["output_tokens"]) == (
        "claude-opus-5-5",
        900,
        150,
    )
    assert data["stale"] is True  # live data (no check-ins at all) no longer matches


def test_detail_without_sr_has_no_stale_flag(make_client: MakeClient, session: Session) -> None:
    review_id = ready_review(session)
    client = make_client(StubSource(error=SrUnavailableError("down")))
    assert client.get(f"/reviews/{review_id}").json()["data"]["stale"] is None


def test_missing_review_is_404(client: TestClient) -> None:
    assert client.get("/reviews/999").status_code == 404


def test_ready_review_is_approved_once(client: TestClient, session: Session) -> None:
    review_id = ready_review(session)
    approved = client.post(f"/reviews/{review_id}/approve").json()["data"]
    assert approved["status"] == "APPROVED"
    assert approved["approved_at"] == FIXED_NOW.isoformat()
    assert client.post(f"/reviews/{review_id}/approve").status_code == 409


def test_queued_review_cannot_be_approved(client: TestClient) -> None:
    queued = client.post("/reviews", json=WEEK_39).json()["data"]
    assert client.post(f"/reviews/{queued['id']}/approve").status_code == 409
