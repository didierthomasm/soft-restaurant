from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict

from tabernas.api.deps import ClockDep, SessionDep, SrSourceDep
from tabernas.api.envelope import Envelope, ok
from tabernas.domain.incident_filter import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    IncidentFilter,
    IncidentStatus,
    IncidentType,
    Page,
    PageRequest,
    count_unresolved,
    filter_incidents,
    paginate,
)
from tabernas.domain.rh import to_rh_rows
from tabernas.domain.summary import EmployeeSummary, Grouping, summarize
from tabernas.domain.types import Area, ExceptionKind, Outcome, Planned, RhType, WarningCode
from tabernas.export.xlsx import XLSX_MEDIA_TYPE, build_workbook
from tabernas.services.attendance import AttendanceReport, AttendanceService

router = APIRouter(prefix="/attendance", tags=["attendance"])

StartQuery = Annotated[date, Query(alias="from")]
EndQuery = Annotated[date, Query(alias="to")]


class _FromAttributes(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EmployeeRef(_FromAttributes):
    id: int
    short_name: str
    rh_name: str | None
    area: Area


class ExceptionRef(_FromAttributes):
    id: int
    kind: ExceptionKind
    date_from: date
    date_to: date
    rh_type: RhType | None
    comment: str


class DayOut(_FromAttributes):
    employee_id: int
    day: date
    planned: Planned
    outcome: Outcome
    checkin: datetime | None
    minutes_late: int | None
    rh_type: RhType | None
    justification_id: int | None
    comment: str
    exception: ExceptionRef | None


class WarningOut(_FromAttributes):
    code: WarningCode
    employee_id: int | None
    day: date | None
    detail: str


class RhRowOut(_FromAttributes):
    employee_id: int
    name: str
    day: date
    rh_type: RhType
    comment: str


class CalendarOut(BaseModel):
    start: date
    end: date
    employees: list[EmployeeRef]
    days: list[DayOut]
    warnings: list[WarningOut]


class IncidentsOut(BaseModel):
    start: date
    end: date
    items: list[DayOut]
    unresolved: int
    warnings: list[WarningOut]


class RhRowsOut(BaseModel):
    start: date
    end: date
    items: list[RhRowOut]


class SummaryOut(BaseModel):
    employee_id: int
    period: str
    worked: int
    late: int
    late_justified: int
    absent: int
    absent_justified: int
    justified_by_type: dict[RhType, int]
    unresolved: int


def get_service(session: SessionDep, source: SrSourceDep, clock: ClockDep) -> AttendanceService:
    return AttendanceService(session, source, clock)


ServiceDep = Annotated[AttendanceService, Depends(get_service)]


def incident_filter(
    employee_id: int | None = None,
    types: Annotated[list[IncidentType] | None, Query(alias="type")] = None,
    status: IncidentStatus = IncidentStatus.ALL,
) -> IncidentFilter:
    return IncidentFilter(employee_id=employee_id, types=frozenset(types or ()), status=status)


def page_request(
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> PageRequest:
    return PageRequest(page=page, limit=limit)


FilterDep = Annotated[IncidentFilter, Depends(incident_filter)]
PageDep = Annotated[PageRequest, Depends(page_request)]


def _page_meta[T](found: Page[T]) -> dict[str, int]:
    return {"total": found.total, "page": found.page, "limit": found.limit}


def _warnings(report: AttendanceReport) -> list[WarningOut]:
    return [WarningOut.model_validate(w) for w in report.warnings]


def summary_out(summary: EmployeeSummary) -> SummaryOut:
    return SummaryOut(
        employee_id=summary.employee_id,
        period=summary.period,
        worked=summary.worked,
        late=summary.late,
        late_justified=summary.late_justified,
        absent=summary.absent,
        absent_justified=summary.absent_justified,
        justified_by_type=dict(summary.justified_by_type),
        unresolved=summary.unresolved,
    )


@router.get("/calendar")
def calendar(start: StartQuery, end: EndQuery, service: ServiceDep) -> Envelope[CalendarOut]:
    report = service.build(start, end)
    return ok(
        CalendarOut(
            start=report.start,
            end=report.end,
            employees=[EmployeeRef.model_validate(e) for e in report.employees],
            days=[DayOut.model_validate(r) for r in report.results],
            warnings=_warnings(report),
        )
    )


@router.get("/incidents")
def incidents(
    start: StartQuery, end: EndQuery, service: ServiceDep, where: FilterDep, page: PageDep
) -> Envelope[IncidentsOut]:
    report = service.build(start, end)
    found = paginate(filter_incidents(report.results, where), page)
    return ok(
        IncidentsOut(
            start=report.start,
            end=report.end,
            items=[DayOut.model_validate(r) for r in found.items],
            unresolved=count_unresolved(report.results, where.employee_id),
            warnings=_warnings(report),
        ),
        meta=_page_meta(found),
    )


@router.get("/rh-rows")
def rh_rows(
    start: StartQuery, end: EndQuery, service: ServiceDep, where: FilterDep, page: PageDep
) -> Envelope[RhRowsOut]:
    report = service.build(start, end)
    rows, _ = to_rh_rows(filter_incidents(report.results, where), report.employees)
    found = paginate(rows, page)
    return ok(
        RhRowsOut(
            start=report.start,
            end=report.end,
            items=[RhRowOut.model_validate(row) for row in found.items],
        ),
        meta=_page_meta(found),
    )


@router.get("/summary")
def summary(
    start: StartQuery, end: EndQuery, service: ServiceDep, group: Grouping = Grouping.WEEK
) -> Envelope[list[SummaryOut]]:
    report = service.build(start, end)
    return ok([summary_out(s) for s in summarize(report.results, group)])


@router.get(
    "/export.xlsx",
    response_class=Response,
    responses={200: {"content": {XLSX_MEDIA_TYPE: {}}, "description": "Libro de Excel"}},
)
def export_xlsx(
    start: StartQuery, end: EndQuery, service: ServiceDep, group: Grouping = Grouping.WEEK
) -> Response:
    report = service.build(start, end)
    content = build_workbook(report, summarize(report.results, group))
    filename = f"asistencia_{start.isoformat()}_{end.isoformat()}.xlsx"
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
