import re

import pytest
from sqlalchemy import func, select

from app.modelos import Movimiento


@pytest.fixture
def movimiento(cargar_movimiento):
    return cargar_movimiento(descripcion="Para borrar")


def test_ac32_eliminar_confirmado_sale_de_la_grilla(cliente_logueado, movimiento):
    """AC-32 (RF-11, RF-28)."""
    respuesta = cliente_logueado.post(f"/movimientos/{movimiento.id}/eliminar", follow_redirects=False)
    assert respuesta.status_code == 303 and respuesta.headers["location"] == "/movimientos"
    assert "Para borrar" not in cliente_logueado.get("/movimientos").text


def test_eliminar_desde_htmx_redirige_a_la_grilla(cliente_logueado, movimiento):
    """RF-11: el botón usa HTMX; la respuesta lleva a la grilla."""
    respuesta = cliente_logueado.post(f"/movimientos/{movimiento.id}/eliminar",
                                      headers={"HX-Request": "true"}, follow_redirects=False)
    assert respuesta.headers["HX-Redirect"] == "/movimientos"


def test_ac33_baja_logica_conserva_fila(cliente_logueado, movimiento, db):
    """AC-33 (RF-12)."""
    cliente_logueado.post(f"/movimientos/{movimiento.id}/eliminar")
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Movimiento)) == 1
    assert db.get(Movimiento, movimiento.id).eliminado is True


def test_ac49_eliminar_pide_confirmacion(cliente_logueado, movimiento, db):
    """AC-49 (RF-28): el navegador pide confirmar; si se cancela no se manda nada."""
    html = cliente_logueado.get(f"/movimientos/{movimiento.id}/editar").text
    boton = re.search(r"<button[^>]*>\s*Eliminar\s*</button>", html, re.S).group(0)
    assert f'hx-post="/movimientos/{movimiento.id}/eliminar"' in boton
    assert "hx-confirm=" in boton
    # Cancelar la confirmación no hace ningún pedido: el movimiento sigue igual.
    assert "Para borrar" in cliente_logueado.get("/movimientos").text
    assert db.get(Movimiento, movimiento.id).eliminado is False


def test_ac111_fr033_eliminar_ya_eliminado_rechaza(cliente_logueado, movimiento):
    """AC-111 (RF-76); FR-033 (RF-12)."""
    cliente_logueado.post(f"/movimientos/{movimiento.id}/eliminar")
    respuesta = cliente_logueado.post(f"/movimientos/{movimiento.id}/eliminar")
    assert respuesta.status_code == 409
    assert "El movimiento fue eliminado" in respuesta.text


def test_eliminar_inexistente_404(cliente_logueado):
    """RF-11."""
    assert cliente_logueado.post("/movimientos/9999/eliminar").status_code == 404
