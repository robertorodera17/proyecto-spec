from fastapi import Request
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app import config


class Base(DeclarativeBase):
    pass


def crear_engine(url: str | None = None) -> Engine:
    url = url or config.database_url()
    motor = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})
    if url.startswith("sqlite"):
        @event.listens_for(motor, "connect")
        def _pragmas(conexion, _registro):
            conexion.execute("PRAGMA busy_timeout=5000")
    return motor


def crear_sesiones(motor: Engine) -> sessionmaker:
    return sessionmaker(motor, expire_on_commit=False)


def get_db(request: Request):
    with request.app.state.sesiones() as sesion:
        yield sesion
