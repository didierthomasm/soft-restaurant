"""Read-only access to SoftRestaurant: models, errors and the SrSource protocol."""

import logging
from datetime import date, datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class SrUnavailableError(RuntimeError):
    """SR could not be reached or a query failed. Message is safe to show to users."""


class SrNotReadOnlyError(RuntimeError):
    """Raised by GET /health/sr when the configured SR login is not read-only."""


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class SrEmployee(_Frozen):
    sr_id: int
    name: str
    kind: int | None
    visible: bool


class SrCheckin(_Frozen):
    sr_id: int
    at: datetime  # naive, SR local time


class SrServerInfo(_Frozen):
    server: str
    instance: str
    version: str
    edition: str
    database: str
    login: str
    is_datareader: bool
    is_denywriter: bool
    is_sysadmin: bool

    @property
    def read_only(self) -> bool:
        return self.is_denywriter and not self.is_sysadmin


class SrSource(Protocol):
    def fetch_employees(self) -> list[SrEmployee]: ...

    def fetch_checkins(self, start: date, end: date) -> list[SrCheckin]:
        """Check-ins with start <= at.date() <= end. Range limited to 93 days."""
        ...

    def server_info(self) -> SrServerInfo: ...


def parse_sr_id(raw: object) -> int | None:
    """SR stores employee ids as zero-padded varchar ('06'); SR's own reports show 6."""
    try:
        return int(str(raw).strip())
    except ValueError:
        logger.warning("Ignoring SR row with non-numeric employee id %r", raw)
        return None
