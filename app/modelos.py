"""Tablas según specs/001-registro-movimientos/data-model.md."""
import enum
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TipoMovimiento(str, enum.Enum):
    INGRESO = "INGRESO"
    EGRESO = "EGRESO"

    @property
    def etiqueta(self) -> str:
        return self.value.capitalize()


class Movimiento(Base):
    __tablename__ = "movimientos"
    __table_args__ = (
        CheckConstraint("monto <> 0", name="ck_movimientos_monto"),
        CheckConstraint("tipo IN ('INGRESO','EGRESO')", name="ck_movimientos_tipo"),
        Index("ix_movimientos_grilla", "eliminado", "fecha", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    descripcion: Mapped[str] = mapped_column(String(200))
    tipo: Mapped[str] = mapped_column(String(7))
    monto: Mapped[int] = mapped_column(Integer)
    clasificacion: Mapped[str] = mapped_column(String(20))
    fecha: Mapped[date] = mapped_column(Date)
    eliminado: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")


class Operador(Base):
    __tablename__ = "operadores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sigla: Mapped[str] = mapped_column(String, unique=True)
    nombre: Mapped[str] = mapped_column(String)
    mail: Mapped[str] = mapped_column(String)
    password_hash: Mapped[str | None] = mapped_column(String(60), nullable=True)


class Socio(Base):
    __tablename__ = "socios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String)
    mail: Mapped[str] = mapped_column(String)


Index("ux_socios_mail", func.lower(Socio.mail), unique=True)


class EnvioDiario(Base):
    __tablename__ = "envios_diarios"

    fecha: Mapped[date] = mapped_column(Date, primary_key=True)
    iniciado_en: Mapped[datetime] = mapped_column(DateTime)
