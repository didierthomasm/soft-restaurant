"""SoftRestaurant access. Pick the implementation with SR_MODE."""

from tabernas.config import Settings
from tabernas.sr.fake_source import FakeSource
from tabernas.sr.pymssql_source import PymssqlSource
from tabernas.sr.source import SrSource


def build_sr_source(settings: Settings) -> SrSource:
    if settings.sr_mode == "fake":
        return FakeSource()
    return PymssqlSource.from_settings(settings)
