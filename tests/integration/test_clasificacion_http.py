import time

from sqlalchemy import select

from app.modelos import Movimiento


def fragmento(cliente, **params):
    return cliente.get("/movimientos/clasificacion", params=params).text


def seleccionada(html):
    import re

    encontrada = re.search(r'<option value="([^"]+)" selected>', html)
    return encontrada.group(1) if encontrada else None


def test_ac01_propuesta_viene_seleccionada(cliente_logueado):
    """AC-01 (RF-15)."""
    assert seleccionada(fragmento(cliente_logueado, tipo="EGRESO", descripcion="Sueldo marzo")) == "SUELDOS"


def test_ac12_sin_propuesta_selector_vacio_y_no_guarda(cliente_logueado, db):
    """AC-12 (RF-16)."""
    assert seleccionada(fragmento(cliente_logueado, tipo="EGRESO", descripcion="Compra de café")) is None
    respuesta = cliente_logueado.post("/movimientos", data={
        "descripcion": "Compra de café", "tipo": "EGRESO", "monto": "100", "clasificacion": "",
        "fecha": ""})
    assert respuesta.status_code == 422 and 'id="error-clasificacion"' in respuesta.text
    assert db.scalars(select(Movimiento)).first() is None


def test_ac67_nueva_descripcion_reemplaza_eleccion_manual(cliente_logueado):
    """AC-67 (RF-42)."""
    html = fragmento(cliente_logueado, tipo="EGRESO", descripcion="Sueldo marzo", clasificacion="VIATICOS")
    assert seleccionada(html) == "SUELDOS"


def test_ac92_descripcion_sin_propuesta_vacia_clasificacion(cliente_logueado):
    """AC-92 (RF-66)."""
    html = fragmento(cliente_logueado, tipo="EGRESO", descripcion="Compra de café", clasificacion="VIATICOS")
    assert seleccionada(html) is None


def test_formulario_pide_la_propuesta_al_escribir(cliente_logueado):
    """RF-15, RF-42: la descripción y el tipo disparan el pedido del selector."""
    html = cliente_logueado.get("/movimientos/nuevo").text
    descripcion = html[html.index('name="descripcion"') - 300: html.index('name="descripcion"') + 300]
    assert 'hx-get="/movimientos/clasificacion"' in descripcion
    assert "input changed delay:300ms" in descripcion


def test_ac80_propuesta_menos_de_2s_p95(cliente_logueado):
    """AC-80 (RNF-01): se mide el servidor; el margen cubre la demora de 300 ms del formulario."""
    tiempos = []
    for i in range(100):
        inicio = time.perf_counter()
        fragmento(cliente_logueado, tipo="EGRESO", descripcion=f"Sueldo número {i} de prueba")
        tiempos.append(time.perf_counter() - inicio)
    tiempos.sort()
    assert tiempos[94] < 1.7
