import re
from datetime import date

import pytest

from app.modelos import Movimiento


@pytest.fixture
def cargar(db):
    def cargar(descripcion="Sueldo marzo", tipo="EGRESO", monto=-1000, clasificacion="SUELDOS",
               fecha=date(2026, 10, 21), eliminado=False):
        movimiento = Movimiento(descripcion=descripcion, tipo=tipo, monto=monto,
                                clasificacion=clasificacion, fecha=fecha, eliminado=eliminado)
        db.add(movimiento)
        db.commit()
        return movimiento

    return cargar


def filas(html):
    return re.findall(r"<tr[^>]*data-id=\"\d+\".*?</tr>", html, re.S)


def test_ac11_grilla_muestra_campos(cliente_logueado, cargar):
    """AC-11 (RF-08)."""
    cargar()
    fila = filas(cliente_logueado.get("/movimientos").text)[0]
    for texto in ("Sueldo marzo", "-1.000", "Egreso", "SUELDOS", "21/10/2026"):
        assert texto in fila


def test_ac99_grilla_todas_las_fechas(cliente_logueado, cargar):
    """AC-99 (RF-08)."""
    cargar(descripcion="De hoy")
    cargar(descripcion="Viejo", fecha=date(2026, 1, 1))
    html = cliente_logueado.get("/movimientos").text
    assert "De hoy" in html and "Viejo" in html


def test_ac83_monto_ingreso_1200(cliente_logueado, cargar):
    """AC-83 (RF-59)."""
    cargar(tipo="INGRESO", monto=1200, clasificacion="ALQUILERES")
    assert ">1.200<" in cliente_logueado.get("/movimientos").text


def test_ac89_monto_egreso_1200(cliente_logueado, cargar):
    """AC-89 (RF-59)."""
    cargar(monto=-1200)
    assert ">-1.200<" in cliente_logueado.get("/movimientos").text


def test_ac84_orden_fecha_desc(cliente_logueado, cargar):
    """AC-84 (RF-60)."""
    for dia in (10, 12, 11):
        cargar(descripcion=f"Dia {dia}", fecha=date(2026, 10, dia))
    html = cliente_logueado.get("/movimientos").text
    assert html.index("Dia 12") < html.index("Dia 11") < html.index("Dia 10")


def test_ac85_paginas_de_30(cliente_logueado, cargar):
    """AC-85 (RF-61)."""
    for i in range(31):
        cargar(descripcion=f"Mov {i}")
    assert len(filas(cliente_logueado.get("/movimientos").text)) == 30
    assert len(filas(cliente_logueado.get("/movimientos?pagina=2").text)) == 1


def test_ac91_misma_fecha_ultimo_cargado_arriba(cliente_logueado, cargar):
    """AC-91 (RF-65)."""
    cargar(descripcion="Alquiler local", tipo="INGRESO", monto=5000, clasificacion="ALQUILERES")
    cargar(descripcion="Sueldo marzo")
    html = cliente_logueado.get("/movimientos").text
    assert html.index("Sueldo marzo") < html.index("Alquiler local")


def test_eliminados_no_aparecen(cliente_logueado, cargar):
    """RF-08: la grilla muestra solo los no eliminados."""
    cargar(descripcion="Vigente")
    cargar(descripcion="Borrado", eliminado=True)
    html = cliente_logueado.get("/movimientos").text
    assert "Vigente" in html and "Borrado" not in html


def test_pagina_fuera_de_rango_muestra_la_ultima(cliente_logueado, cargar):
    """Research R12."""
    for i in range(31):
        cargar(descripcion=f"Mov {i}")
    assert len(filas(cliente_logueado.get("/movimientos?pagina=99").text)) == 1
    assert len(filas(cliente_logueado.get("/movimientos?pagina=abc").text)) == 30


def test_grilla_vacia(cliente_logueado):
    """RF-08: sin movimientos, la grilla se muestra vacía."""
    respuesta = cliente_logueado.get("/movimientos")
    assert respuesta.status_code == 200 and filas(respuesta.text) == []


def test_descripcion_con_html_se_muestra_escapada(cliente_logueado, cargar):
    """Research R10: una descripción no puede inyectar código en la grilla."""
    cargar(descripcion="<script>alert(1)</script>")
    html = cliente_logueado.get("/movimientos").text
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_raiz_lleva_a_la_grilla(cliente_logueado):
    """RF-08: la página inicial es la grilla."""
    respuesta = cliente_logueado.get("/", follow_redirects=False)
    assert respuesta.status_code == 303 and respuesta.headers["location"] == "/movimientos"
