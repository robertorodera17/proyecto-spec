import re
from datetime import date

import pytest

from app.modelos import Movimiento


@pytest.fixture
def egreso(cargar_movimiento):
    return cargar_movimiento(descripcion="Sueldo marzo", tipo="EGRESO", monto=-500,
                             clasificacion="SUELDOS", fecha=date(2026, 10, 17))


def modificar(cliente, movimiento, **cambios):
    datos = {"descripcion": movimiento.descripcion, "tipo": movimiento.tipo,
             "monto": str(abs(movimiento.monto)), "clasificacion": movimiento.clasificacion,
             "fecha": movimiento.fecha.isoformat()}
    datos.update(cambios)
    return cliente.post(f"/movimientos/{movimiento.id}", data=datos, follow_redirects=False)


def releer(db, movimiento):
    db.expire_all()
    return db.get(Movimiento, movimiento.id)


def seleccionada(html):
    encontrada = re.search(r'<option value="([^"]+)" selected>', html)
    return encontrada.group(1) if encontrada else None


def test_ac28_doble_click_abre_formulario(cliente_logueado, egreso):
    """AC-28 (RF-10)."""
    grilla = cliente_logueado.get("/movimientos").text
    fila = re.search(rf'<tr[^>]*data-id="{egreso.id}"[^>]*>', grilla).group(0)
    assert f'hx-get="/movimientos/{egreso.id}/editar"' in fila
    assert 'hx-trigger="dblclick"' in fila
    formulario = cliente_logueado.get(f"/movimientos/{egreso.id}/editar").text
    assert 'value="Sueldo marzo"' in formulario
    assert 'value="2026-10-17"' in formulario
    assert '<option value="EGRESO" selected>' in formulario
    assert '<option value="SUELDOS" selected>' in formulario
    assert f'action="/movimientos/{egreso.id}"' in formulario


def test_ac69_monto_sin_signo(cliente_logueado, egreso):
    """AC-69 (RF-45)."""
    assert 'name="monto" value="500"' in cliente_logueado.get(f"/movimientos/{egreso.id}/editar").text


def test_ac29_cambia_descripcion(cliente_logueado, egreso):
    """AC-29 (RF-26)."""
    respuesta = modificar(cliente_logueado, egreso, descripcion="Sueldo abril")
    assert respuesta.status_code == 303 and respuesta.headers["location"] == "/movimientos"
    assert "Sueldo abril" in cliente_logueado.get("/movimientos").text


def test_ac48_cambia_fecha(cliente_logueado, egreso, db):
    """AC-48 (RF-27)."""
    modificar(cliente_logueado, egreso, fecha="2026-10-10")
    assert releer(db, egreso).fecha == date(2026, 10, 10)
    assert "10/10/2026" in cliente_logueado.get("/movimientos").text


def test_ac93_egreso_a_ingreso(cliente_logueado, egreso, db):
    """AC-93 (RF-27, RF-06)."""
    modificar(cliente_logueado, egreso, tipo="INGRESO", clasificacion="ALQUILERES")
    movimiento = releer(db, egreso)
    assert (movimiento.tipo, movimiento.clasificacion, movimiento.monto) == ("INGRESO", "ALQUILERES", 500)


def test_ac94_cambia_monto_egreso(cliente_logueado, egreso, db):
    """AC-94 (RF-27, RF-05)."""
    modificar(cliente_logueado, egreso, monto="800")
    assert releer(db, egreso).monto == -800


def test_ac30_clasificacion_de_otro_tipo_rechaza(cliente_logueado, egreso, db):
    """AC-30 (RF-17)."""
    respuesta = modificar(cliente_logueado, egreso, tipo="INGRESO", clasificacion="SUELDOS")
    assert respuesta.status_code == 422 and 'id="error-clasificacion"' in respuesta.text
    assert releer(db, egreso).tipo == "EGRESO"


def test_ac31_monto_cero_rechaza(cliente_logueado, egreso, db):
    """AC-31 (RF-07, RF-26)."""
    respuesta = modificar(cliente_logueado, egreso, monto="0")
    assert respuesta.status_code == 422 and 'id="error-monto"' in respuesta.text
    assert releer(db, egreso).monto == -500


def test_ac100_monto_decimal_rechaza(cliente_logueado, egreso):
    """AC-100 (RF-58)."""
    respuesta = modificar(cliente_logueado, egreso, monto="12,5")
    assert respuesta.status_code == 422 and 'id="error-monto"' in respuesta.text


def test_ac104_fr004_fecha_futura_rechazada_al_modificar(cliente_logueado, egreso):
    """AC-104 (RF-70); FR-004 (RF-26)."""
    assert modificar(cliente_logueado, egreso, fecha="2026-10-22").status_code == 422


def test_ac108_fr034_descripcion_larga_rechazada_al_modificar(cliente_logueado, egreso):
    """AC-108 (RF-74); FR-034 (RF-26)."""
    assert modificar(cliente_logueado, egreso, descripcion="a" * 201).status_code == 422


def test_modificacion_invalida_vuelve_al_formulario_de_modificacion(cliente_logueado, egreso):
    """RF-26: el formulario con errores sigue siendo el de modificación."""
    respuesta = modificar(cliente_logueado, egreso, monto="0")
    assert f'action="/movimientos/{egreso.id}"' in respuesta.text
    assert "Eliminar" in respuesta.text


def test_ac70_cambio_de_tipo_vacia_clasificacion(cliente_logueado):
    """AC-70 (RF-46)."""
    html = cliente_logueado.get("/movimientos/clasificacion", params={
        "tipo": "INGRESO", "clasificacion": "SUELDOS",
        "tipo_original": "EGRESO", "clasificacion_original": "SUELDOS"}).text
    assert seleccionada(html) is None
    assert '<option value="ALQUILERES"' in html


def test_ac71_volver_al_tipo_original_recupera(cliente_logueado):
    """AC-71 (RF-47)."""
    html = cliente_logueado.get("/movimientos/clasificacion", params={
        "tipo": "EGRESO", "clasificacion": "", "tipo_original": "EGRESO",
        "clasificacion_original": "SUELDOS"}).text
    assert seleccionada(html) == "SUELDOS"


def test_formulario_de_modificacion_manda_el_original_y_no_propone(cliente_logueado, egreso):
    """RF-15, RF-46, RF-47: al modificar no se propone por descripción."""
    html = cliente_logueado.get(f"/movimientos/{egreso.id}/editar").text
    assert 'name="tipo_original" value="EGRESO"' in html
    assert 'name="clasificacion_original" value="SUELDOS"' in html
    descripcion = re.search(r'<input[^>]*name="descripcion"[^>]*>', html).group(0)
    assert "hx-get" not in descripcion
    tipo = re.search(r'<select[^>]*name="tipo"[^>]*>', html, re.S).group(0)
    assert "[name=tipo_original]" in tipo and "[name=descripcion]" not in tipo


def test_ac109_fr033_ultimo_que_guarda_gana(cliente_logueado, egreso, db):
    """AC-109 (RF-75); FR-033 (RF-26)."""
    modificar(cliente_logueado, egreso, descripcion="Versión de A")
    modificar(cliente_logueado, egreso, descripcion="Versión de B")
    assert releer(db, egreso).descripcion == "Versión de B"


def test_ac110_fr033_modificar_eliminado_rechaza(cliente_logueado, egreso, db):
    """AC-110 (RF-76); FR-033 (RF-12)."""
    cliente_logueado.post(f"/movimientos/{egreso.id}/eliminar")
    respuesta = modificar(cliente_logueado, egreso, descripcion="Tarde")
    assert respuesta.status_code == 409
    assert "El movimiento fue eliminado" in respuesta.text
    movimiento = releer(db, egreso)
    assert movimiento.descripcion == "Sueldo marzo" and movimiento.eliminado


def test_editar_eliminado_o_inexistente_404(cliente_logueado, cargar_movimiento):
    """RF-08, FA-09: un eliminado no se puede abrir."""
    borrado = cargar_movimiento(eliminado=True)
    assert cliente_logueado.get(f"/movimientos/{borrado.id}/editar").status_code == 404
    assert cliente_logueado.get("/movimientos/9999/editar").status_code == 404
    assert cliente_logueado.post("/movimientos/9999", data={}).status_code == 404
