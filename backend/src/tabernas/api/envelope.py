"""Common response envelope: {success, data, error, meta}."""

from typing import Any

from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str


class Envelope[T](BaseModel):
    success: bool
    data: T | None = None
    error: ErrorBody | None = None
    meta: dict[str, Any] | None = None


def ok[T](data: T, meta: dict[str, Any] | None = None) -> Envelope[T]:
    return Envelope[T](success=True, data=data, meta=meta)
