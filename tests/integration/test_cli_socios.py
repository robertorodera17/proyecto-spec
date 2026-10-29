from sqlalchemy import select

from app import socios
from app.modelos import Socio


def alta(sesiones, *args):
    return socios.main(["alta", *args], sesiones=sesiones)


def test_ac58_alta_socio(sesiones, db, capsys):
    """AC-58 (RF-35)."""
    assert alta(sesiones, "José", "jose@empresa.com") == 0
    socio = db.scalars(select(Socio)).one()
    assert (socio.nombre, socio.mail) == ("José", "jose@empresa.com")
    assert "Socio José creado" in capsys.readouterr().out


def test_ac41_socio_sin_mail_rechaza(sesiones, db, capsys):
    """AC-41 (RF-23)."""
    assert alta(sesiones, "José") == 1
    assert alta(sesiones, "José", "   ") == 1
    assert "El socio necesita un mail" in capsys.readouterr().err
    assert db.scalars(select(Socio)).first() is None


def test_ac59_mail_repetido_mayusculas_rechaza(sesiones, db, capsys):
    """AC-59 (RF-49)."""
    alta(sesiones, "José", "jose@empresa.com")
    assert alta(sesiones, "Otro", "JOSE@empresa.com") == 1
    assert "Ya existe un socio con el mail JOSE@empresa.com" in capsys.readouterr().err
    assert len(db.scalars(select(Socio)).all()) == 1


def test_ac112_fr022_mail_con_salto_de_linea_rechaza(sesiones, db, capsys):
    """AC-112 (RF-77); FR-022 (RF-23): un salto de línea podría alterar el mail."""
    assert alta(sesiones, "José", "jose@empresa.com\nBcc: otro@x.com") == 1
    assert alta(sesiones, "José", "jose@empresa.com\r") == 1
    assert "saltos de línea" in capsys.readouterr().err
    assert db.scalars(select(Socio)).first() is None
