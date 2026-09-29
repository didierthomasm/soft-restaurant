"""Maps exceptions to enveloped JSON errors. Details stay in the server log."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from tabernas.api.envelope import Envelope, ErrorBody
from tabernas.domain.validation import DomainValidationError
from tabernas.repos.errors import ConflictError, NotFoundError
from tabernas.sr.source import SrNotReadOnlyError, SrUnavailableError

logger = logging.getLogger(__name__)

Handler = Callable[[Request, Exception], Awaitable[JSONResponse]]

SR_UNAVAILABLE_MESSAGE = "No se pudo leer SoftRestaurant. Revisa Tailscale."
_HTTP_CODES = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}
# (exception, status, code, fixed message or None to use str(exc))
_MAPPED: tuple[tuple[type[Exception], int, str, str | None], ...] = (
    (DomainValidationError, 422, "VALIDATION_ERROR", None),
    (NotFoundError, 404, "NOT_FOUND", None),
    (ConflictError, 409, "CONFLICT", None),
    (SrUnavailableError, 503, "SR_UNAVAILABLE", SR_UNAVAILABLE_MESSAGE),
    (SrNotReadOnlyError, 500, "SR_NOT_READONLY", None),
)


def error_response(
    status_code: int, code: str, message: str, meta: dict[str, Any] | None = None
) -> JSONResponse:
    body = Envelope[None](success=False, error=ErrorBody(code=code, message=message), meta=meta)
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


def _mapped(status_code: int, code: str, fixed_message: str | None) -> Handler:
    async def handler(request: Request, exc: Exception) -> JSONResponse:
        return error_response(status_code, code, fixed_message or str(exc))

    return handler


async def _request_validation(request: Request, exc: Exception) -> JSONResponse:
    errors = exc.errors() if isinstance(exc, RequestValidationError) else []
    fields = [{"loc": [str(part) for part in e["loc"]], "msg": e["msg"]} for e in errors]
    return error_response(422, "VALIDATION_ERROR", "Datos inválidos", {"errors": fields})


async def _http(request: Request, exc: Exception) -> JSONResponse:
    status = exc.status_code if isinstance(exc, StarletteHTTPException) else 500
    detail = exc.detail if isinstance(exc, StarletteHTTPException) else "Error"
    return error_response(status, _HTTP_CODES.get(status, "HTTP_ERROR"), str(detail))


async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return error_response(500, "INTERNAL", "Error interno del servidor")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _request_validation)
    app.add_exception_handler(StarletteHTTPException, _http)
    for exc_type, status_code, code, message in _MAPPED:
        app.add_exception_handler(exc_type, _mapped(status_code, code, message))
    app.add_exception_handler(Exception, _unhandled)
