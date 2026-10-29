"""Alta de socios por consola (RF-35): python -m app.socios alta "Nombre" mail"""
import argparse
import sys

from sqlalchemy import func, select

from app import db
from app.modelos import Socio


def main(argv: list[str] | None = None, sesiones=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.socios")
    subcomandos = parser.add_subparsers(dest="comando", required=True)
    alta = subcomandos.add_parser("alta", help="Da de alta un socio que recibe el mail diario")
    alta.add_argument("nombre")
    alta.add_argument("mail", nargs="?", default="")
    args = parser.parse_args(argv)

    mail = args.mail.strip(" \t")
    if not mail:
        print("El socio necesita un mail", file=sys.stderr)
        return 1
    if "\r" in mail or "\n" in mail:
        print("El mail no puede tener saltos de línea", file=sys.stderr)
        return 1

    sesiones = sesiones or db.crear_sesiones(db.crear_engine())
    with sesiones() as sesion:
        if sesion.scalar(select(Socio).where(func.lower(Socio.mail) == mail.lower())):
            print(f"Ya existe un socio con el mail {mail}", file=sys.stderr)
            return 1
        sesion.add(Socio(nombre=args.nombre, mail=mail))
        sesion.commit()
    print(f"Socio {args.nombre} creado: recibirá el mail diario en {mail}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
