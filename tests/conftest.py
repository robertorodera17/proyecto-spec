import base64
import json
import smtplib
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import fechas

SECRET = "clave-de-prueba-no-usar"
CONTRASENA = "secreta123"


class Reloj:
    """Fija la hora de Argentina que devuelve app.fechas.ahora()."""

    def __init__(self, monkeypatch):
        self.actual = datetime(2026, 10, 21, 10, 0, tzinfo=fechas.ZONA)
        monkeypatch.setattr(fechas, "ahora", lambda: self.actual)

    def poner(self, texto):
        self.actual = datetime.strptime(texto, "%Y-%m-%d %H:%M").replace(tzinfo=fechas.ZONA)

    def avanzar(self, **delta):
        self.actual += timedelta(**delta)


class ServidorFalso:
    """Doble de smtplib: guarda los mensajes y simula fallas."""

    def __init__(self):
        self.mensajes = []
        self.conexiones = []
        self.rechazar = set()
        self.caido = False


@pytest.fixture(autouse=True)
def env_minimo(monkeypatch):
    # Aísla los tests del .env del desarrollador.
    monkeypatch.setenv("SECRET_KEY", SECRET)
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    for clave in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM",
                  "SMTP_SEGURIDAD", "TLS_CERT", "TLS_KEY"):
        monkeypatch.delenv(clave, raising=False)


@pytest.fixture
def reloj(monkeypatch):
    return Reloj(monkeypatch)


@pytest.fixture
def engine():
    from app.db import Base
    from app import modelos  # noqa: F401  (registra las tablas)

    motor = create_engine("sqlite://", poolclass=StaticPool,
                          connect_args={"check_same_thread": False})
    Base.metadata.create_all(motor)
    return motor


@pytest.fixture
def sesiones(engine):
    return sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
def db(sesiones):
    with sesiones() as sesion:
        yield sesion


@pytest.fixture
def app(engine, reloj):
    from app.main import crear_app

    return crear_app(iniciar_programador=False, engine=engine)


def _cliente(app, ip="127.0.0.1", base_url="http://testserver"):
    return TestClient(app, base_url=base_url, client=(ip, 50000),
                      headers={"Origin": base_url})


@pytest.fixture
def cliente(app):
    return _cliente(app)


@pytest.fixture
def cliente_desde(app):
    """Cliente con IP y esquema a elección: cliente_desde("192.168.0.10")."""
    return lambda ip, base_url="http://testserver": _cliente(app, ip, base_url)


@pytest.fixture(scope="session")
def hash_contrasena():
    from app import seguridad

    return seguridad.hashear(CONTRASENA)


@pytest.fixture
def crear_operador(db, hash_contrasena):
    from app.modelos import Operador

    def crear(sigla="RO", nombre="Rocío", mail="rocio@empresa.com", con_contrasena=True):
        operador = Operador(sigla=sigla, nombre=nombre, mail=mail,
                            password_hash=hash_contrasena if con_contrasena else None)
        db.add(operador)
        db.commit()
        return operador

    return crear


def cookie_de_sesion(datos):
    """Arma la cookie igual que el SessionMiddleware de Starlette."""
    valor = base64.b64encode(json.dumps(datos).encode())
    return TimestampSigner(SECRET).sign(valor).decode()


@pytest.fixture
def iniciar_sesion(reloj):
    def iniciar(cliente, operador_id):
        datos = {"operador_id": operador_id, "ultima_actividad": reloj.actual.timestamp()}
        # Mismo dominio que usa el cliente de pruebas, para que el servidor pueda borrarla.
        cliente.cookies.set("session", cookie_de_sesion(datos), domain="testserver.local")
        return cliente

    return iniciar


@pytest.fixture
def cliente_logueado(cliente, crear_operador, iniciar_sesion):
    operador = crear_operador()
    return iniciar_sesion(cliente, operador.id)


@pytest.fixture
def fake_smtp(monkeypatch):
    servidor = ServidorFalso()

    class SMTPFalso:
        def __init__(self, host=None, port=0, *args, **kwargs):
            if servidor.caido:
                raise ConnectionRefusedError(f"No se pudo conectar a {host}:{port}")
            servidor.conexiones.append({"host": host, "port": port, "clase": type(self).__name__,
                                        "starttls": False, "login": None})

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self, *args, **kwargs):
            servidor.conexiones[-1]["starttls"] = True

        def login(self, usuario, password):
            servidor.conexiones[-1]["login"] = usuario

        def send_message(self, mensaje, *args, **kwargs):
            destino = mensaje["To"]
            if destino in servidor.rechazar:
                raise smtplib.SMTPRecipientsRefused({destino: (550, b"Direccion rechazada")})
            servidor.mensajes.append(mensaje)
            return {}

        def quit(self):
            pass

    class SMTP_SSLFalso(SMTPFalso):
        pass

    monkeypatch.setattr(smtplib, "SMTP", SMTPFalso)
    monkeypatch.setattr(smtplib, "SMTP_SSL", SMTP_SSLFalso)
    return servidor


@pytest.fixture
def config_smtp():
    """Configuración de correo completa, como la de un .env de producción."""
    from app.config import Config

    return Config(secret_key=SECRET, database_url="sqlite://", smtp_host="smtp.empresa.com",
                  smtp_port=587, smtp_user="app@empresa.com", smtp_password="clave-smtp-secreta",
                  smtp_from="app@empresa.com", smtp_seguridad="starttls", tls_cert="", tls_key="")


@pytest.fixture
def crear_socio(db):
    from app.modelos import Socio

    def crear(nombre="José", mail="jose@empresa.com"):
        socio = Socio(nombre=nombre, mail=mail)
        db.add(socio)
        db.commit()
        return socio

    return crear


@pytest.fixture
def cargar_movimiento(db):
    from datetime import date

    from app.modelos import Movimiento

    def cargar(descripcion="Sueldo marzo", tipo="EGRESO", monto=-1000, clasificacion="SUELDOS",
               fecha=date(2026, 10, 21), eliminado=False):
        movimiento = Movimiento(descripcion=descripcion, tipo=tipo, monto=monto,
                                clasificacion=clasificacion, fecha=fecha, eliminado=eliminado)
        db.add(movimiento)
        db.commit()
        return movimiento

    return cargar
