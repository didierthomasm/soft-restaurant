from sqlalchemy.orm import Session

from tabernas.domain.types import Area, Employee
from tabernas.repos.employees import EmployeeRepo


def make_employee(
    session: Session,
    sr_id: int | None = 101,
    *,
    short_name: str = "EMPLEADO A",
    area: Area = Area.OTHER,
) -> Employee:
    return EmployeeRepo(session).create(
        sr_id=sr_id,
        short_name=short_name,
        rh_name=None,
        area=area,
        applies_lateness=True,
        tracks_attendance=True,
    )
