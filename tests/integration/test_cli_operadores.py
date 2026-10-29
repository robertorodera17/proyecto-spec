import pytest
from sqlalchemy import select

from app import operadores
from app.modelos import Operador


def alta(sesiones, *args):
    return operadores.main(["alta", *args], sesiones=sesiones)


def test_ac51_alta_sin_contrasena(sesiones, db, capsys):
    """AC-51 (RF-30, RF-41)."""
    assert alta(sesiones, "JP", "Juan", "juan@empresa.com") == 0
    operador = db.scalars(select(Operador)).one()
    assert operador.password_hash is None
    assert "Operador JP creado" in capsys.readouterr().out


def test_ac96_alta_guarda_sigla_nombre_mail(sesiones, db):
    """AC-96 (RF-18)."""
    alta(sesiones, "JP", "Juan", "juan@empresa.com")
    operador = db.scalars(select(Operador)).one()
    assert (operador.sigla, operador.nombre, operador.mail) == ("JP", "Juan", "juan@empresa.com")


def test_sigla_se_guarda_en_mayusculas(sesiones, db):
    """RF-29: la sigla se guarda en mayúsculas."""
    alta(sesiones, "jp", "Juan", "juan@empresa.com")
    assert db.scalars(select(Operador.sigla)).one() == "JP"


def test_ac34_sigla_repetida_rechaza(sesiones, db, capsys):
    """AC-34 (RF-29)."""
    alta(sesiones, "RO", "Rocío", "rocio@empresa.com")
    assert alta(sesiones, "RO", "Otra", "otra@empresa.com") == 1
    assert "Ya existe un operador con la sigla RO" in capsys.readouterr().err
    assert len(db.scalars(select(Operador)).all()) == 1


def test_ac50_sigla_repetida_minusculas_rechaza(sesiones, db):
    """AC-50 (RF-29)."""
    alta(sesiones, "RO", "Rocío", "rocio@empresa.com")
    assert alta(sesiones, "ro", "Otra", "otra@empresa.com") == 1
    assert len(db.scalars(select(Operador)).all()) == 1


def test_argumentos_faltantes_codigo_2(sesiones):
    """RF-30: uso incorrecto termina con código 2 (contracts/cli.md)."""
    with pytest.raises(SystemExit) as salida:
        alta(sesiones, "RO", "Rocío")
    assert salida.value.code == 2
