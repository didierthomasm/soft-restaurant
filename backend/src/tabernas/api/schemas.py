"""Shared request-schema helpers."""

from typing import Any, ClassVar, Self

from pydantic import BaseModel, ConfigDict, model_validator


class PatchModel(BaseModel):
    """PATCH body: unknown fields are rejected; null only where NULLABLE allows it."""

    model_config = ConfigDict(extra="forbid")
    NULLABLE: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def _reject_nulls(self) -> Self:
        nulls = sorted(
            field
            for field in self.model_fields_set
            if getattr(self, field) is None and field not in self.NULLABLE
        )
        if nulls:
            raise ValueError(f"Estos campos no pueden ser nulos: {', '.join(nulls)}")
        return self

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)
