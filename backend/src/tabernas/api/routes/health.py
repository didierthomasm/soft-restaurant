import logging

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from tabernas.api.deps import AppSettingsDep, SessionDep, SrSourceDep
from tabernas.api.envelope import Envelope, ok
from tabernas.sr.source import SrNotReadOnlyError

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


class HealthOut(BaseModel):
    status: str
    db: str


class SrHealthOut(BaseModel):
    mode: str
    server: str
    instance: str
    version: str
    edition: str
    database: str
    login: str
    is_datareader: bool
    is_denywriter: bool
    is_sysadmin: bool


@router.get("/health")
def health(session: SessionDep) -> Envelope[HealthOut]:
    try:
        session.execute(text("SELECT 1"))
        db = "ok"
    except SQLAlchemyError:
        logger.exception("Database health check failed")
        session.rollback()
        db = "error"
    return ok(HealthOut(status="ok" if db == "ok" else "degraded", db=db))


@router.get("/health/sr")
def health_sr(source: SrSourceDep, settings: AppSettingsDep) -> Envelope[SrHealthOut]:
    info = source.server_info()
    if not info.read_only:
        raise SrNotReadOnlyError(
            "El login de SoftRestaurant puede escribir; usa reportes_ro (solo lectura)"
        )
    return ok(SrHealthOut(mode=settings.sr_mode, **info.model_dump()))
