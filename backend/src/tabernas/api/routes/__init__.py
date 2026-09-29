from fastapi import APIRouter

from tabernas.api.routes import employees, exceptions, health, justifications, rest_rules, settings

ROUTERS: list[APIRouter] = [
    health.router,
    employees.router,
    settings.router,
    rest_rules.router,
    exceptions.router,
    justifications.router,
]
