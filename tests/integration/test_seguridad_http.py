from fastapi.testclient import TestClient


def test_ac113_fr035_http_desde_otra_maquina_403(cliente_desde):
    """AC-113 (RNF-05); FR-035: sin cifrar desde otra PC no se muestra el login."""
    respuesta = cliente_desde("192.168.0.10").get("/login", follow_redirects=False)
    assert respuesta.status_code == 403
    assert "https://" in respuesta.text
    assert "sigla" not in respuesta.text.lower()


def test_ac113_fr035_http_desde_otra_maquina_no_acepta_contrasenas(cliente_desde):
    """AC-113 (RNF-05); FR-035: tampoco se aceptan contraseñas por HTTP desde la red."""
    respuesta = cliente_desde("192.168.0.10").post(
        "/login", data={"sigla": "RO", "password": "secreta123"}, follow_redirects=False)
    assert respuesta.status_code == 403


def test_ac114_fr035_http_desde_loopback_ok(cliente_desde):
    """AC-114 (RNF-05); FR-035: desde la propia máquina (IPv4 e IPv6) se permite HTTP."""
    assert cliente_desde("127.0.0.1").get("/static/estilos.css").status_code == 200
    assert cliente_desde("::1").get("/static/estilos.css").status_code == 200


def test_fr035_https_desde_otra_maquina_ok(cliente_desde):
    """RNF-05; FR-035: cifrado desde la red se atiende."""
    cliente = cliente_desde("192.168.0.10", "https://testserver")
    assert cliente.get("/static/estilos.css").status_code == 200


def test_post_sin_origin_ni_referer_403(app):
    """Research R3: protección contra pedidos de otro sitio."""
    cliente = TestClient(app, client=("127.0.0.1", 50000))
    assert cliente.post("/logout", follow_redirects=False).status_code == 403


def test_post_con_origin_ajeno_403(app):
    """Research R3."""
    cliente = TestClient(app, client=("127.0.0.1", 50000), headers={"Origin": "http://malo.example"})
    assert cliente.post("/logout", follow_redirects=False).status_code == 403


def test_post_con_referer_propio_sin_origin_pasa_el_chequeo(app):
    """Research R3: sin Origin, alcanza un Referer del propio host."""
    cliente = TestClient(app, client=("127.0.0.1", 50000),
                         headers={"Referer": "http://testserver/movimientos"})
    assert cliente.post("/logout", follow_redirects=False).status_code != 403


def test_cookie_de_sesion_httponly_samesite_strict(app, crear_operador, reloj, cliente):
    """Research R2: la cookie no es accesible desde JavaScript ni viaja a otros sitios."""
    from app.main import middleware_de_sesion

    opciones = middleware_de_sesion(app)
    assert opciones["same_site"] == "strict"
    assert opciones["https_only"] is False


def test_cookie_de_sesion_secure_con_tls(monkeypatch, engine, reloj):
    """RNF-05; FR-035: con TLS configurado, la sesión solo viaja cifrada."""
    from app.main import crear_app, middleware_de_sesion

    monkeypatch.setenv("TLS_CERT", "/ruta/cert.pem")
    monkeypatch.setenv("TLS_KEY", "/ruta/key.pem")
    app = crear_app(iniciar_programador=False, engine=engine)
    assert middleware_de_sesion(app)["https_only"] is True
