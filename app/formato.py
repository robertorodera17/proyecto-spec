"""Cómo se muestran montos y fechas en la grilla y en el mail (RF-59, RF-63)."""
from datetime import date


def monto(valor: int) -> str:
    signo = "-" if valor < 0 else ""
    return signo + f"{abs(valor):,}".replace(",", ".")


def fecha(valor: date) -> str:
    return valor.strftime("%d/%m/%Y")
