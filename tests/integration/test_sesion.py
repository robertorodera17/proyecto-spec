import pytest
from fastapi.responses import PlainTextResponse


@pytest.fixture
def ruta_protegida(app):
    @app.get("/protegida-de-prueba")
    def protegida():
        return PlainTextResponse("contenido protegido")

    return "/protegida-de-prueba"


def test_ac38_sin_sesion_redirige_al_login(cliente, ruta_protegida):
    """AC-38 (RF-21): sin sesión, cualquier ruta que no es pública lleva al login."""
    respuesta = cliente.get(ruta_protegida, follow_redirects=False)
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/login"
    assert "contenido protegido" not in respuesta.text


def test_ac38_sin_sesion_post_redirige_al_login(cliente):
    """AC-38 (RF-21): también las acciones (POST) a rutas inexistentes o protegidas."""
    respuesta = cliente.post("/movimientos", data={}, follow_redirects=False)
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/login"


def test_ac38_pedido_htmx_sin_sesion_usa_hx_redirect(cliente, ruta_protegida):
    """AC-38 (RF-21): en pedidos HTMX la redirección es de página entera."""
    respuesta = cliente.get(ruta_protegida, headers={"HX-Request": "true"}, follow_redirects=False)
    assert respuesta.status_code == 200
    assert respuesta.headers["HX-Redirect"] == "/login"
    assert "contenido protegido" not in respuesta.text


def test_con_sesion_accede(cliente_logueado, ruta_protegida):
    """RF-21: con sesión válida se accede."""
    respuesta = cliente_logueado.get(ruta_protegida)
    assert respuesta.status_code == 200
    assert respuesta.text == "contenido protegido"


def test_ac40_sesion_inactiva_60_minutos_vencida(cliente_logueado, ruta_protegida, reloj):
    """AC-40 (RNF-03): a los 60 minutos justos la sesión ya venció."""
    reloj.avanzar(minutes=60)
    respuesta = cliente_logueado.get(ruta_protegida, follow_redirects=False)
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/login?vencida=1"
    # La sesión quedó limpia: aunque se vuelva atrás en el tiempo no hay acceso.
    reloj.avanzar(minutes=-60)
    assert cliente_logueado.get(ruta_protegida, follow_redirects=False).status_code == 303


def test_ac40_pedido_htmx_con_sesion_vencida(cliente_logueado, ruta_protegida, reloj):
    """AC-40 (RNF-03, RF-34): pedido HTMX vencido redirige la página entera con el aviso."""
    reloj.avanzar(minutes=61)
    respuesta = cliente_logueado.get(ruta_protegida, headers={"HX-Request": "true"},
                                     follow_redirects=False)
    assert respuesta.headers["HX-Redirect"] == "/login?vencida=1"


def test_ac55_sesion_inactiva_59_minutos_sigue(cliente_logueado, ruta_protegida, reloj):
    """AC-55 (RNF-03)."""
    reloj.avanzar(minutes=59)
    assert cliente_logueado.get(ruta_protegida).status_code == 200


def test_cada_accion_renueva_el_plazo(cliente_logueado, ruta_protegida, reloj):
    """RNF-03: cada acción renueva los 60 minutos."""
    for _ in range(3):
        reloj.avanzar(minutes=50)
        assert cliente_logueado.get(ruta_protegida).status_code == 200


def test_rutas_publicas_sin_sesion(cliente):
    """RF-21: el login y los archivos estáticos no exigen sesión."""
    from app.main import RUTAS_PUBLICAS

    assert RUTAS_PUBLICAS == {"/login", "/login/definir", "/static"}
    assert cliente.get("/static/estilos.css").status_code == 200
