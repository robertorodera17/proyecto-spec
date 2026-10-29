"""Hora de Argentina: único punto del código que sabe qué día y qué hora es."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

ZONA = ZoneInfo("America/Argentina/Buenos_Aires")


def ahora() -> datetime:
    return datetime.now(ZONA)


def hoy() -> date:
    return ahora().date()
