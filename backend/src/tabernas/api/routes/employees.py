from typing import ClassVar

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from tabernas.api.deps import SessionDep, SrSourceDep
from tabernas.api.envelope import Envelope, ok
from tabernas.api.schemas import PatchModel
from tabernas.domain.types import Area, Employee
from tabernas.domain.validation import DomainValidationError
from tabernas.repos.employees import EmployeeRepo

router = APIRouter(prefix="/employees", tags=["employees"])


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sr_id: int | None
    short_name: str
    rh_name: str | None
    area: Area
    applies_lateness: bool
    tracks_attendance: bool
    active: bool


class EmployeeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sr_id: int | None = None
    short_name: str = Field(min_length=1, max_length=80)
    rh_name: str | None = Field(default=None, max_length=160)
    area: Area = Area.OTHER
    applies_lateness: bool = True
    tracks_attendance: bool = True


class EmployeeUpdate(PatchModel):
    NULLABLE: ClassVar[frozenset[str]] = frozenset({"rh_name"})

    short_name: str | None = Field(default=None, min_length=1, max_length=80)
    rh_name: str | None = Field(default=None, max_length=160)
    area: Area | None = None
    applies_lateness: bool | None = None
    tracks_attendance: bool | None = None
    active: bool | None = None


class SrEmployeeOut(BaseModel):
    sr_id: int
    name: str
    visible: bool
    imported: bool


class ImportRequest(BaseModel):
    sr_ids: list[int] = Field(min_length=1)


def _out(employee: Employee) -> EmployeeOut:
    return EmployeeOut.model_validate(employee)


@router.get("")
def list_employees(session: SessionDep, active_only: bool = False) -> Envelope[list[EmployeeOut]]:
    return ok([_out(e) for e in EmployeeRepo(session).find_all(active_only=active_only)])


@router.post("", status_code=201)
def create_employee(body: EmployeeCreate, session: SessionDep) -> Envelope[EmployeeOut]:
    return ok(_out(EmployeeRepo(session).create(**body.model_dump())))


@router.get("/sr-preview")
def sr_preview(session: SessionDep, source: SrSourceDep) -> Envelope[list[SrEmployeeOut]]:
    existing = EmployeeRepo(session).existing_sr_ids()
    return ok(
        [
            SrEmployeeOut(
                sr_id=e.sr_id, name=e.name, visible=e.visible, imported=e.sr_id in existing
            )
            for e in sorted(source.fetch_employees(), key=lambda e: e.sr_id)
        ]
    )


@router.post("/import-from-sr", status_code=201)
def import_from_sr(
    body: ImportRequest, session: SessionDep, source: SrSourceDep
) -> Envelope[list[EmployeeOut]]:
    available = {e.sr_id: e for e in source.fetch_employees()}
    unknown = sorted(set(body.sr_ids) - set(available))
    if unknown:
        raise DomainValidationError(f"Ids SR no encontrados: {', '.join(map(str, unknown))}")
    repo = EmployeeRepo(session)
    existing = repo.existing_sr_ids()
    created = [
        repo.create(
            sr_id=sr_id,
            short_name=available[sr_id].name[:80] or f"SR {sr_id}",
            rh_name=None,
            area=Area.OTHER,
            applies_lateness=True,
            tracks_attendance=True,
        )
        for sr_id in sorted(set(body.sr_ids))
        if sr_id not in existing
    ]
    return ok([_out(e) for e in created])


@router.get("/{employee_id}")
def get_employee(employee_id: int, session: SessionDep) -> Envelope[EmployeeOut]:
    return ok(_out(EmployeeRepo(session).find_by_id(employee_id)))


@router.patch("/{employee_id}")
def update_employee(
    employee_id: int, body: EmployeeUpdate, session: SessionDep
) -> Envelope[EmployeeOut]:
    return ok(_out(EmployeeRepo(session).update(employee_id, body.changes())))
