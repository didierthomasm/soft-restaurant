from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field

from tabernas.api.deps import SessionDep
from tabernas.api.envelope import Envelope, ok
from tabernas.api.schemas import PatchModel
from tabernas.domain.periods import validate_range
from tabernas.domain.types import Incident, Justification, RhType
from tabernas.repos.justifications import JustificationRepo

router = APIRouter(prefix="/justifications", tags=["justifications"])

Reason = Annotated[str, Field(min_length=1, max_length=500)]


class JustificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    day: date
    incident: Incident
    reason: str
    rh_type: RhType


class JustificationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_id: int
    day: date
    incident: Incident
    reason: Reason
    rh_type: RhType | None = None


class JustificationUpdate(PatchModel):
    reason: Reason | None = None
    rh_type: RhType | None = None


def _out(justification: Justification) -> JustificationOut:
    return JustificationOut.model_validate(justification)


@router.get("")
def list_justifications(
    session: SessionDep,
    start: Annotated[date, Query(alias="from")],
    end: Annotated[date, Query(alias="to")],
    employee_id: int | None = None,
) -> Envelope[list[JustificationOut]]:
    validate_range(start, end)
    found = JustificationRepo(session).find_all(start=start, end=end, employee_id=employee_id)
    return ok([_out(j) for j in found])


@router.post("", status_code=201)
def create_justification(
    body: JustificationCreate, session: SessionDep
) -> Envelope[JustificationOut]:
    return ok(_out(JustificationRepo(session).create(**body.model_dump())))


@router.patch("/{justification_id}")
def update_justification(
    justification_id: int, body: JustificationUpdate, session: SessionDep
) -> Envelope[JustificationOut]:
    return ok(_out(JustificationRepo(session).update(justification_id, body.changes())))


@router.delete("/{justification_id}")
def delete_justification(justification_id: int, session: SessionDep) -> Envelope[None]:
    JustificationRepo(session).delete(justification_id)
    return ok(None)
