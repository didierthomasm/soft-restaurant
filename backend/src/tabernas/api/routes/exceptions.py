from datetime import date
from typing import Annotated, ClassVar

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field

from tabernas.api.deps import SessionDep
from tabernas.api.envelope import Envelope, ok
from tabernas.api.schemas import PatchModel
from tabernas.domain.types import ExceptionKind, RhType, ScheduleException
from tabernas.repos.exceptions import ExceptionRepo

router = APIRouter(prefix="/exceptions", tags=["exceptions"])

Comment = Annotated[str, Field(max_length=500)]


class ExceptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: ExceptionKind
    employee_id: int | None
    date_from: date
    date_to: date
    rh_type: RhType | None
    comment: str


class ExceptionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ExceptionKind
    employee_id: int | None = None
    date_from: date
    date_to: date
    rh_type: RhType | None = None
    comment: Comment = ""


class ExceptionUpdate(PatchModel):
    NULLABLE: ClassVar[frozenset[str]] = frozenset({"rh_type"})

    date_from: date | None = None
    date_to: date | None = None
    rh_type: RhType | None = None
    comment: Comment | None = None


class RestSwapCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_id: int
    absent_day: date
    worked_day: date
    comment: Comment = ""


def _out(exception: ScheduleException) -> ExceptionOut:
    return ExceptionOut.model_validate(exception)


@router.get("")
def list_exceptions(
    session: SessionDep,
    start: Annotated[date | None, Query(alias="from")] = None,
    end: Annotated[date | None, Query(alias="to")] = None,
    employee_id: int | None = None,
) -> Envelope[list[ExceptionOut]]:
    found = ExceptionRepo(session).find_all(start=start, end=end, employee_id=employee_id)
    return ok([_out(e) for e in found])


@router.post("", status_code=201)
def create_exception(body: ExceptionCreate, session: SessionDep) -> Envelope[ExceptionOut]:
    return ok(_out(ExceptionRepo(session).create(**body.model_dump())))


@router.post("/rest-swap", status_code=201)
def create_rest_swap(body: RestSwapCreate, session: SessionDep) -> Envelope[list[ExceptionOut]]:
    created = ExceptionRepo(session).create_rest_swap(**body.model_dump())
    return ok([_out(e) for e in created])


@router.patch("/{exception_id}")
def update_exception(
    exception_id: int, body: ExceptionUpdate, session: SessionDep
) -> Envelope[ExceptionOut]:
    return ok(_out(ExceptionRepo(session).update(exception_id, body.changes())))


@router.delete("/{exception_id}")
def delete_exception(exception_id: int, session: SessionDep) -> Envelope[None]:
    ExceptionRepo(session).delete(exception_id)
    return ok(None)
