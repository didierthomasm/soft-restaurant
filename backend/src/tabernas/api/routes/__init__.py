from fastapi import APIRouter

from tabernas.api.routes import health

ROUTERS: list[APIRouter] = [health.router]
