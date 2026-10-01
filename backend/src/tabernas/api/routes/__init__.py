from fastapi import APIRouter

from tabernas.api.routes import (
    attendance,
    employees,
    exceptions,
    health,
    justifications,
    rest_rules,
    reviews,
    settings,
)

ROUTERS: list[APIRouter] = [
    health.router,
    employees.router,
    settings.router,
    rest_rules.router,
    exceptions.router,
    justifications.router,
    attendance.router,
    reviews.router,
]
