"""Clasificaciones por tipo de movimiento y sus palabras clave (RF-13..16)."""
import re
import unicodedata
from typing import NamedTuple


class Clasificacion(NamedTuple):
    nombre: str
    tipo: str
    clave: str


CLASIFICACIONES = (
    Clasificacion("SERVICIOS-PRESTADOS", "INGRESO", "serv"),
    Clasificacion("ALQUILERES", "INGRESO", "alq"),
    Clasificacion("FINANCIEROS", "INGRESO", "fin"),
    Clasificacion("SUELDOS", "EGRESO", "sue"),
    Clasificacion("IMPUESTOS-TASAS", "EGRESO", "imp"),
    Clasificacion("VIATICOS", "EGRESO", "via"),
    Clasificacion("PAGO-PROVEEDORES", "EGRESO", "prov"),
    Clasificacion("TURISMO", "EGRESO", "tur"),
)


def por_tipo(tipo: str) -> list[str]:
    return [c.nombre for c in CLASIFICACIONES if c.tipo == tipo]


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto)
    return "".join(c for c in sin_tildes if not unicodedata.combining(c)).lower()


def proponer(descripcion: str, tipo: str) -> str | None:
    """La clasificación del tipo cuya palabra clave inicia alguna palabra de la descripción.

    Sin coincidencias, o con coincidencias de más de una clasificación, no propone nada:
    elige el operador (RF-16, Constitución Principio II).
    """
    palabras = re.findall(r"\w+", _normalizar(descripcion))
    encontradas = {c.nombre for c in CLASIFICACIONES
                   if c.tipo == tipo and any(p.startswith(c.clave) for p in palabras)}
    return encontradas.pop() if len(encontradas) == 1 else None
