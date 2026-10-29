import re
from datetime import date

from sqlalchemy import select

from app.modelos import Movimiento


def opciones(html, nombre):
    """Valores de las <option> del <select name=nombre>, sin la opción vacía."""
    bloque = re.search(rf'<select[^>]*name="{nombre}".*?</select>', html, re.S).group(0)
    return [v for v in re.findall(r'<option value="([^"]*)"', bloque) if v]


def alta(cliente, **campos):
    datos = {"descripcion": "Sueldo marzo", "tipo": "EGRESO", "monto": "1000",
             "clasificacion": "SUELDOS", "fecha": "2026-10-20"}
    datos.update(campos)
    return cliente.post("/movimientos", data=datos, follow_redirects=False)


def test_ac68_alta_egreso_guarda_negativo(cliente_logueado, db):
    """AC-68 (RF-01, RF-05)."""
    respuesta = alta(cliente_logueado)
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/movimientos"
    movimiento = db.scalars(select(Movimiento)).one()
    assert (movimiento.descripcion, movimiento.tipo, movimiento.monto, movimiento.clasificacion,
            movimiento.fecha, movimiento.eliminado) == (
        "Sueldo marzo", "EGRESO", -1000, "SUELDOS", date(2026, 10, 20), False)


def test_ac19_alta_invalida_devuelve_errores_por_campo(cliente_logueado, db):
    """AC-19 (RF-02): 422 con el formulario y el error junto al campo; no guarda."""
    respuesta = alta(cliente_logueado, monto="0", descripcion="")
    assert respuesta.status_code == 422
    assert 'id="error-monto"' in respuesta.text
    assert 'id="error-descripcion"' in respuesta.text
    assert db.scalars(select(Movimiento)).first() is None


def test_alta_invalida_conserva_lo_escrito(cliente_logueado):
    """RF-02: el operador no pierde lo que cargó."""
    respuesta = alta(cliente_logueado, monto="12abc", descripcion="Compra de café")
    assert 'value="Compra de café"' in respuesta.text
    assert 'value="12abc"' in respuesta.text


def test_ac27_agregar_muestra_formulario_vacio_con_hoy(cliente_logueado):
    """AC-27 (RF-09)."""
    grilla = cliente_logueado.get("/movimientos").text
    assert 'href="/movimientos/nuevo"' in grilla and "Agregar movimiento" in grilla
    formulario = cliente_logueado.get("/movimientos/nuevo").text
    assert 'name="descripcion" value=""' in formulario
    assert 'name="fecha" value="2026-10-21"' in formulario


def test_ac20_fecha_por_defecto_hoy(cliente_logueado, reloj):
    """AC-20 (RF-03)."""
    reloj.poner("2026-03-05 09:00")
    assert 'name="fecha" value="2026-03-05"' in cliente_logueado.get("/movimientos/nuevo").text


def test_ac97_fecha_por_defecto_argentina_con_servidor_utc(cliente_logueado, reloj):
    """AC-97 (RF-03): 22:30 del 20/10 en Argentina (01:30 del 21/10 UTC)."""
    reloj.poner("2026-10-20 22:30")
    assert 'name="fecha" value="2026-10-20"' in cliente_logueado.get("/movimientos/nuevo").text


def test_ac46_alta_con_fecha_vacia_guarda_hoy(cliente_logueado, db):
    """AC-46 (RF-43)."""
    alta(cliente_logueado, fecha="")
    assert db.scalars(select(Movimiento)).one().fecha == date(2026, 10, 21)


def test_ac47_alta_con_fecha_inexistente(cliente_logueado):
    """AC-47 (RF-44)."""
    respuesta = alta(cliente_logueado, fecha="2026-02-30")
    assert respuesta.status_code == 422 and 'id="error-fecha"' in respuesta.text


def test_ac21_tipos_ingreso_egreso(cliente_logueado):
    """AC-21 (RF-04)."""
    assert opciones(cliente_logueado.get("/movimientos/nuevo").text, "tipo") == ["INGRESO", "EGRESO"]


def test_ac17_clasificaciones_ingreso(cliente_logueado):
    """AC-17 (RF-13)."""
    html = cliente_logueado.get("/movimientos/clasificacion", params={"tipo": "INGRESO"}).text
    assert opciones(html, "clasificacion") == ["SERVICIOS-PRESTADOS", "ALQUILERES", "FINANCIEROS"]


def test_ac18_clasificaciones_egreso(cliente_logueado):
    """AC-18 (RF-14)."""
    html = cliente_logueado.get("/movimientos/clasificacion", params={"tipo": "EGRESO"}).text
    assert opciones(html, "clasificacion") == ["SUELDOS", "IMPUESTOS-TASAS", "VIATICOS",
                                               "PAGO-PROVEEDORES", "TURISMO"]


def test_formulario_de_alta_sin_eliminar(cliente_logueado):
    """RF-11: el alta no tiene botón Eliminar."""
    assert "Eliminar" not in cliente_logueado.get("/movimientos/nuevo").text


def test_ac09_alta_egreso_con_alquileres_por_http(cliente_logueado):
    """AC-09 (RF-17): el servidor rechaza aunque el formulario se manipule."""
    respuesta = alta(cliente_logueado, clasificacion="ALQUILERES")
    assert respuesta.status_code == 422 and 'id="error-clasificacion"' in respuesta.text


def test_ac10_alta_ingreso_con_sueldos_por_http(cliente_logueado):
    """AC-10 (RF-17)."""
    respuesta = alta(cliente_logueado, tipo="INGRESO", clasificacion="SUELDOS")
    assert respuesta.status_code == 422 and 'id="error-clasificacion"' in respuesta.text


def test_fragmento_conserva_la_clasificacion_si_sigue_siendo_del_tipo(cliente_logueado):
    """RF-14, RF-17: al pedir de nuevo el selector, la elección vale solo si es del tipo."""
    html = cliente_logueado.get("/movimientos/clasificacion",
                                params={"tipo": "EGRESO", "clasificacion": "SUELDOS"}).text
    assert '<option value="SUELDOS" selected>' in html
    html = cliente_logueado.get("/movimientos/clasificacion",
                                params={"tipo": "INGRESO", "clasificacion": "SUELDOS"}).text
    assert "selected" not in html
