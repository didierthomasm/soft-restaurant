from datetime import date
from typing import ClassVar

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from tabernas.api.deps import SessionDep
from tabernas.api.envelope import Envelope, ok
from tabernas.api.schemas import PatchModel
from tabernas.domain.types import RestRule
from tabernas.repos.rest_rules import RestRuleRepo

router = APIRouter(prefix="/rest-rules", tags=["rest-rules"])


class RestRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    fixed_weekday: int
    extra_weekday: int
    double_rest_anchor: date
    valid_from: date
    valid_to: date | None


class RestRuleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_id: int
    fixed_weekday: int = Field(ge=0, le=6)
    extra_weekday: int = Field(ge=0, le=6)
    double_rest_anchor: date
    valid_from: date
    valid_to: date | None = None


class RestRuleUpdate(PatchModel):
    NULLABLE: ClassVar[frozenset[str]] = frozenset({"valid_to"})

    fixed_weekday: int | None = Field(default=None, ge=0, le=6)
    extra_weekday: int | None = Field(default=None, ge=0, le=6)
    double_rest_anchor: date | None = None
    valid_from: date | None = None
    valid_to: date | None = None


def _out(rule: RestRule) -> RestRuleOut:
    return RestRuleOut.model_validate(rule)


@router.get("")
def list_rules(session: SessionDep, employee_id: int | None = None) -> Envelope[list[RestRuleOut]]:
    return ok([_out(r) for r in RestRuleRepo(session).find_all(employee_id=employee_id)])


@router.post("", status_code=201)
def create_rule(body: RestRuleCreate, session: SessionDep) -> Envelope[RestRuleOut]:
    return ok(_out(RestRuleRepo(session).create(**body.model_dump())))


@router.patch("/{rule_id}")
def update_rule(rule_id: int, body: RestRuleUpdate, session: SessionDep) -> Envelope[RestRuleOut]:
    return ok(_out(RestRuleRepo(session).update(rule_id, body.changes())))


@router.delete("/{rule_id}")
def delete_rule(rule_id: int, session: SessionDep) -> Envelope[None]:
    RestRuleRepo(session).delete(rule_id)
    return ok(None)
