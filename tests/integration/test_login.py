from datetime import date

from sqlalchemy import select

from app.modelos import Movimiento, Operador


def pedir_sigla(cliente, sigla):
    return cliente.post("/login", data={"sigla": sigla}, follow_redirects=False)


def ingresar(cliente, sigla, password):
    return cliente.post("/login", data={"sigla": sigla, "password": password}, follow_redirects=False)


def definir(cliente, sigla, password, password2=None):
    return cliente.post("/login/definir",
                        data={"sigla": sigla, "password": password,
                              "password2": password if password2 is None else password2},
                        follow_redirects=False)


def entra_a_la_grilla(cliente):
    return cliente.get("/movimientos", follow_redirects=False).status_code == 200


def test_login_muestra_formulario_de_sigla(cliente):
    """RF-20: la pantalla de login pide la sigla."""
    respuesta = cliente.get("/login")
    assert respuesta.status_code == 200 and 'name="sigla"' in respuesta.text


def test_ac35_sin_contrasena_pide_definirla(cliente, crear_operador):
    """AC-35 (RF-19)."""
    crear_operador(con_contrasena=False)
    respuesta = pedir_sigla(cliente, "RO")
    assert 'action="/login/definir"' in respuesta.text
    assert 'name="password2"' in respuesta.text
    assert not entra_a_la_grilla(cliente)


def test_ac103_contrasenas_no_coinciden(cliente, crear_operador, db):
    """AC-103 (RF-69)."""
    operador = crear_operador(con_contrasena=False)
    respuesta = definir(cliente, "RO", "secreta123", "secreta124")
    assert "Las contraseñas no coinciden" in respuesta.text
    assert not entra_a_la_grilla(cliente)
    db.refresh(operador)
    assert operador.password_hash is None


def test_ac53_define_7_caracteres_rechaza(cliente, crear_operador):
    """AC-53 (RF-31)."""
    crear_operador(con_contrasena=False)
    respuesta = definir(cliente, "RO", "1234567")
    assert "al menos 8 caracteres" in respuesta.text
    assert not entra_a_la_grilla(cliente)


def test_ac98_define_8_caracteres_entra(cliente, crear_operador):
    """AC-98 (RF-31, RF-19)."""
    crear_operador(con_contrasena=False)
    respuesta = definir(cliente, "RO", "12345678")
    assert respuesta.status_code == 303 and respuesta.headers["location"] == "/movimientos"
    assert entra_a_la_grilla(cliente)


def test_ac72_define_72_bytes_y_vuelve_a_entrar(cliente, crear_operador):
    """AC-72 (RF-48)."""
    crear_operador(con_contrasena=False)
    definir(cliente, "RO", "a" * 72)
    cliente.post("/logout")
    ingresar(cliente, "RO", "a" * 72)
    assert entra_a_la_grilla(cliente)


def test_ac86_define_73_bytes_rechaza(cliente, crear_operador):
    """AC-86 (RF-62)."""
    crear_operador(con_contrasena=False)
    respuesta = definir(cliente, "RO", "a" * 73)
    assert "72 bytes" in respuesta.text
    assert not entra_a_la_grilla(cliente)


def test_ac52_no_redefine_contrasena_existente(cliente, crear_operador, db):
    """AC-52 (RF-19)."""
    operador = crear_operador()
    anterior = operador.password_hash
    respuesta = definir(cliente, "RO", "otraclave99")
    assert "ya tiene contraseña" in respuesta.text
    assert not entra_a_la_grilla(cliente)
    db.refresh(operador)
    assert operador.password_hash == anterior


def test_ac54_sigla_inexistente_no_pide_contrasena(cliente):
    """AC-54 (RF-33)."""
    respuesta = pedir_sigla(cliente, "XX")
    assert "No existe un operador con la sigla XX" in respuesta.text
    assert 'name="password"' not in respuesta.text


def test_con_contrasena_pide_la_contrasena(cliente, crear_operador):
    """RF-20: un operador con contraseña ve el campo de contraseña."""
    crear_operador()
    respuesta = pedir_sigla(cliente, "RO")
    assert 'name="password"' in respuesta.text and 'name="password2"' not in respuesta.text


def test_ac36_login_correcto_accede_grilla(cliente, crear_operador):
    """AC-36 (RF-20)."""
    crear_operador()
    respuesta = ingresar(cliente, "RO", "secreta123")
    assert respuesta.status_code == 303 and respuesta.headers["location"] == "/movimientos"
    assert entra_a_la_grilla(cliente)


def test_ac37_contrasena_incorrecta_rechaza(cliente, crear_operador):
    """AC-37 (RF-20)."""
    crear_operador()
    respuesta = ingresar(cliente, "RO", "incorrecta")
    assert "Sigla o contraseña incorrecta" in respuesta.text
    assert not entra_a_la_grilla(cliente)


def test_sigla_en_minusculas_entra(cliente, crear_operador):
    """RF-29: el login no distingue mayúsculas en la sigla."""
    crear_operador()
    ingresar(cliente, "ro", "secreta123")
    assert entra_a_la_grilla(cliente)


def test_clarificacion_intentos_ilimitados(cliente, crear_operador):
    """RF-20 (Clarifications 2026-10-24): sin bloqueo tras muchos intentos fallidos."""
    crear_operador()
    for _ in range(20):
        assert "Sigla o contraseña incorrecta" in ingresar(cliente, "RO", "incorrecta").text
    ingresar(cliente, "RO", "secreta123")
    assert entra_a_la_grilla(cliente)


def test_ac39_operador_b_ve_movimiento_de_a(cliente, crear_operador, db):
    """AC-39 (RF-22)."""
    crear_operador(sigla="A", nombre="Ana", mail="a@empresa.com")
    crear_operador(sigla="B", nombre="Beto", mail="b@empresa.com")
    ingresar(cliente, "A", "secreta123")
    cliente.post("/movimientos", data={"descripcion": "Cargado por A", "tipo": "EGRESO",
                                       "monto": "100", "clasificacion": "SUELDOS", "fecha": ""})
    cliente.post("/logout")
    ingresar(cliente, "B", "secreta123")
    assert "Cargado por A" in cliente.get("/movimientos").text


def test_ac56_aviso_sesion_vencida(cliente_logueado, reloj):
    """AC-56 (RF-34)."""
    reloj.avanzar(minutes=60)
    respuesta = cliente_logueado.get("/movimientos")
    assert "Tu sesión venció por inactividad" in respuesta.text


def test_ac57_cerrar_sesion(cliente_logueado):
    """AC-57 (RF-32)."""
    assert "Cerrar sesión" in cliente_logueado.get("/movimientos").text
    respuesta = cliente_logueado.post("/logout", follow_redirects=False)
    assert respuesta.status_code == 303 and respuesta.headers["location"] == "/login"
    respuesta = cliente_logueado.get("/movimientos", follow_redirects=False)
    assert respuesta.status_code == 303 and respuesta.headers["location"] == "/login"


def test_ac44_contrasena_definida_se_guarda_como_hash(cliente, crear_operador, db):
    """AC-44 (RNF-02), AC-95 (RNF-02): lo que queda en la tabla es un hash bcrypt de costo 12."""
    operador = crear_operador(con_contrasena=False)
    definir(cliente, "RO", "secreta123")
    db.refresh(operador)
    assert operador.password_hash.startswith("$2b$12$")
    assert "secreta123" not in operador.password_hash
