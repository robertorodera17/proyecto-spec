"""Alta de operadores por consola (RF-30): python -m app.operadores alta SIGLA "Nombre" mail"""
import argparse
import sys

from sqlalchemy import select

from app import db
from app.modelos import Operador


def main(argv: list[str] | None = None, sesiones=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.operadores")
    subcomandos = parser.add_subparsers(dest="comando", required=True)
    alta = subcomandos.add_parser("alta", help="Da de alta un operador sin contraseña")
    alta.add_argument("sigla")
    alta.add_argument("nombre")
    alta.add_argument("mail")
    args = parser.parse_args(argv)

    sesiones = sesiones or db.crear_sesiones(db.crear_engine())
    sigla = args.sigla.strip().upper()
    with sesiones() as sesion:
        if sesion.scalar(select(Operador).where(Operador.sigla == sigla)):
            print(f"Ya existe un operador con la sigla {sigla}", file=sys.stderr)
            return 1
        sesion.add(Operador(sigla=sigla, nombre=args.nombre, mail=args.mail))
        sesion.commit()
    print(f"Operador {sigla} creado. Define su contraseña en el primer ingreso.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
