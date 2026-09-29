from fastapi import APIRouter

from tabernas.api.routes import employees, health, settings

ROUTERS: list[APIRouter] = [health.router, employees.router, settings.router]
