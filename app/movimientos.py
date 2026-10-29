"""Validación y casos de uso de movimientos (RF-01..17, FR-003, FR-004, FR-034)."""
import re
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app import clasificacion
from app.modelos import Movimiento, TipoMovimiento

POR_PAGINA = 30
LARGO_DESCRIPCION = 200
MONTO_MAXIMO = 2**63 - 1  # máximo entero de SQLite (research R6)
FECHA_MINIMA = date(1900, 1, 1)
TIPOS = [t.value for t in TipoMovimiento]


def _texto(form: dict, campo: str) -> str:
    return (form.get(campo) or "").strip()


def validar(form: dict, hoy: date) -> tuple[dict | None, dict[str, str]]:
    """Devuelve (datos listos para guardar, {}) o (None, {campo: mensaje})."""
    errores: dict[str, str] = {}

    descripcion = _texto(form, "descripcion")
    if not descripcion:
        errores["descripcion"] = "La descripción es obligatoria."
    elif len(descripcion) > LARGO_DESCRIPCION:
        errores["descripcion"] = f"La descripción admite hasta {LARGO_DESCRIPCION} caracteres."

    tipo = _texto(form, "tipo")
    if not tipo:
        errores["tipo"] = "Elegí el tipo de movimiento."
    elif tipo not in TIPOS:
        errores["tipo"] = "El tipo debe ser Ingreso o Egreso."

    texto_monto = _texto(form, "monto")
    monto = None
    if not texto_monto:
        errores["monto"] = "El monto es obligatorio."
    elif not re.fullmatch(r"[0-9]+", texto_monto):
        errores["monto"] = "Escribí el monto solo con dígitos, sin puntos, comas ni signo (por ejemplo 1200)."
    elif int(texto_monto) == 0:
        errores["monto"] = "El monto debe ser mayor que 0."
    elif int(texto_monto) > MONTO_MAXIMO:
        errores["monto"] = "El monto es demasiado grande."
    else:
        monto = int(texto_monto)

    nombre_clasificacion = _texto(form, "clasificacion")
    if not nombre_clasificacion:
        errores["clasificacion"] = "Elegí una clasificación."
    elif "tipo" not in errores and nombre_clasificacion not in clasificacion.por_tipo(tipo):
        errores["clasificacion"] = "La clasificación no corresponde al tipo de movimiento."

    texto_fecha = _texto(form, "fecha")
    fecha = hoy
    if texto_fecha:
        try:
            fecha = date.fromisoformat(texto_fecha) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", texto_fecha) else None
        except ValueError:
            fecha = None
        if fecha is None:
            errores["fecha"] = "La fecha no existe."
        elif fecha > hoy:
            errores["fecha"] = "La fecha no puede ser posterior a hoy."
        elif fecha < FECHA_MINIMA:
            errores["fecha"] = "La fecha no puede ser anterior al 01/01/1900."

    if errores:
        return None, errores
    signo = -1 if tipo == TipoMovimiento.EGRESO.value else 1
    return {"descripcion": descripcion, "tipo": tipo, "monto": signo * monto,
            "clasificacion": nombre_clasificacion, "fecha": fecha}, {}


def crear(db: Session, datos: dict) -> Movimiento:
    movimiento = Movimiento(**datos)
    db.add(movimiento)
    db.commit()
    return movimiento


@dataclass
class Pagina:
    filas: list[Movimiento]
    numero: int
    total: int


def pagina(db: Session, numero: int) -> Pagina:
    vigentes = select(Movimiento).where(Movimiento.eliminado.is_(False))
    cantidad = db.scalar(select(func.count()).select_from(vigentes.subquery()))
    total = max(1, -(-cantidad // POR_PAGINA))
    numero = min(max(1, numero), total)
    filas = db.scalars(vigentes.order_by(Movimiento.fecha.desc(), Movimiento.id.desc())
                       .limit(POR_PAGINA).offset((numero - 1) * POR_PAGINA)).all()
    return Pagina(list(filas), numero, total)


class MovimientoInexistente(Exception):
    pass


class MovimientoEliminado(Exception):
    """FR-033: otro operador lo eliminó mientras estaba abierto."""


def vigente(db: Session, id_: int) -> Movimiento:
    movimiento = db.get(Movimiento, id_)
    if movimiento is None:
        raise MovimientoInexistente(id_)
    if movimiento.eliminado:
        raise MovimientoEliminado(id_)
    return movimiento


def _actualizar_vigente(db: Session, id_: int, valores: dict) -> None:
    """Un solo UPDATE condicionado a que siga vigente: atómico sin bloqueos (research R13).

    Si dos operadores guardan, queda lo del último (FR-033).
    """
    filas = db.execute(update(Movimiento)
                       .where(Movimiento.id == id_, Movimiento.eliminado.is_(False))
                       .values(**valores)).rowcount
    if filas == 0:
        db.rollback()
        vigente(db, id_)  # lanza Inexistente o Eliminado
    db.commit()


def modificar(db: Session, id_: int, datos: dict) -> None:
    _actualizar_vigente(db, id_, datos)


def eliminar(db: Session, id_: int) -> None:
    """Baja lógica: nunca se borra la fila (RF-12)."""
    _actualizar_vigente(db, id_, {"eliminado": True})
