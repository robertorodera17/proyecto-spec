from datetime import date

from app import mail
from app.modelos import Movimiento, Socio

FECHA = date(2026, 10, 21)
SOCIO = Socio(nombre="José", mail="jose@empresa.com")


def mov(descripcion, tipo, monto, clasificacion, fecha=FECHA):
    return Movimiento(descripcion=descripcion, tipo=tipo, monto=monto, clasificacion=clasificacion,
                      fecha=fecha, eliminado=False)


MOVIMIENTOS = [
    mov("Sueldo marzo", "EGRESO", -1000, "SUELDOS"),
    mov("Alquiler local", "INGRESO", 5000, "ALQUILERES"),
    mov("Viáticos Córdoba", "EGRESO", -350, "VIATICOS"),
]


def cuerpo(mensaje):
    return mensaje.get_content()


def lineas_de_movimiento(mensaje):
    return [linea for linea in cuerpo(mensaje).splitlines() if linea.count(" | ") == 4]


def test_ac74_asunto():
    """AC-74 (RF-50)."""
    assert mail.armar(SOCIO, FECHA, MOVIMIENTOS, "app@empresa.com")["Subject"] == "Movimientos del 21/10/2026"


def test_ac75_cantidad():
    """AC-75 (RF-51)."""
    assert "Cantidad: 3" in cuerpo(mail.armar(SOCIO, FECHA, MOVIMIENTOS, "app@empresa.com"))


def test_ac43_campos_por_movimiento():
    """AC-43 (RF-25): descripción, monto, tipo, clasificación y fecha."""
    linea = lineas_de_movimiento(mail.armar(SOCIO, FECHA, MOVIMIENTOS, "app@empresa.com"))[0]
    for texto in ("21/10/2026", "Egreso", "SUELDOS", "-1.000", "Sueldo marzo"):
        assert texto in linea


def test_ac87_monto_ingreso():
    """AC-87 (RF-63)."""
    mensaje = mail.armar(SOCIO, FECHA, [mov("Alquiler", "INGRESO", 1200, "ALQUILERES")], "a@b.com")
    assert " 1.200 |" in cuerpo(mensaje)


def test_ac90_monto_egreso():
    """AC-90 (RF-63)."""
    mensaje = mail.armar(SOCIO, FECHA, [mov("Sueldo", "EGRESO", -1200, "SUELDOS")], "a@b.com")
    assert " -1.200 |" in cuerpo(mensaje)


def test_ac101_una_parte_text_plain():
    """AC-101 (RF-67)."""
    mensaje = mail.armar(SOCIO, FECHA, MOVIMIENTOS, "app@empresa.com")
    assert not mensaje.is_multipart()
    assert mensaje.get_content_type() == "text/plain"
    assert mensaje.get_content_charset() == "utf-8"


def test_ac102_una_linea_por_movimiento():
    """AC-102 (RF-68)."""
    assert len(lineas_de_movimiento(mail.armar(SOCIO, FECHA, MOVIMIENTOS, "app@empresa.com"))) == 3


def test_ac62_sin_movimientos():
    """AC-62 (RF-37)."""
    texto = cuerpo(mail.armar(SOCIO, FECHA, [], "app@empresa.com"))
    assert "No hubo movimientos." in texto
    assert "Cantidad: 0" in texto
    assert "Movimientos del 21/10/2026" in texto


def test_ac60_destinatario_unico():
    """AC-60 (RF-36): el mail va solo al socio."""
    mensaje = mail.armar(SOCIO, FECHA, MOVIMIENTOS, "app@empresa.com")
    assert mensaje["To"] == "jose@empresa.com"
    assert mensaje["From"] == "app@empresa.com"
    assert mensaje["Cc"] is None and mensaje["Bcc"] is None


def test_formato_exacto_del_contrato():
    """contracts/mail.md: columnas fijas alineadas y la descripción al final."""
    esperado = (
        "Movimientos del 21/10/2026\n"
        "Cantidad: 3\n"
        "\n"
        "21/10/2026 | Egreso  | SUELDOS             |       -1.000 | Sueldo marzo\n"
        "21/10/2026 | Ingreso | ALQUILERES          |        5.000 | Alquiler local\n"
        "21/10/2026 | Egreso  | VIATICOS            |         -350 | Viáticos Córdoba\n"
    )
    assert cuerpo(mail.armar(SOCIO, FECHA, MOVIMIENTOS, "app@empresa.com")) == esperado
