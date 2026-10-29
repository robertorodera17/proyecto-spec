import dataclasses
import logging
from datetime import date

import pytest
from sqlalchemy import select

from app import mail
from app.modelos import EnvioDiario

HOY = date(2026, 10, 21)


@pytest.fixture(autouse=True)
def log_info(caplog):
    caplog.set_level(logging.INFO, logger="app")


def test_ac42_solo_vigentes_de_hoy(sesiones, config_smtp, fake_smtp, crear_socio, cargar_movimiento):
    """AC-42 (RF-24)."""
    crear_socio()
    cargar_movimiento(descripcion="Hoy vigente")
    cargar_movimiento(descripcion="Hoy eliminado", eliminado=True)
    cargar_movimiento(descripcion="Ayer", fecha=date(2026, 10, 20))
    mail.enviar_dia(sesiones, config_smtp, HOY)
    texto = fake_smtp.mensajes[0].get_content()
    assert "Hoy vigente" in texto
    assert "Hoy eliminado" not in texto and "Ayer" not in texto


def test_ac60_un_mail_por_socio(sesiones, config_smtp, fake_smtp, crear_socio):
    """AC-60 (RF-36)."""
    crear_socio("José", "jose@empresa.com")
    crear_socio("Ana", "ana@empresa.com")
    assert mail.enviar_dia(sesiones, config_smtp, HOY) == (2, 2)
    assert sorted(m["To"] for m in fake_smtp.mensajes) == ["ana@empresa.com", "jose@empresa.com"]
    assert all("," not in m["To"] for m in fake_smtp.mensajes)


def test_conexion_starttls_y_login(sesiones, config_smtp, fake_smtp, crear_socio):
    """RNF-04: usa la configuración de .env (starttls, usuario)."""
    crear_socio()
    mail.enviar_dia(sesiones, config_smtp, HOY)
    conexion = fake_smtp.conexiones[0]
    assert (conexion["host"], conexion["port"], conexion["starttls"], conexion["login"]) == (
        "smtp.empresa.com", 587, True, "app@empresa.com")


def test_conexion_ssl(sesiones, config_smtp, fake_smtp, crear_socio):
    """RNF-04: SMTP_SEGURIDAD=ssl usa conexión cifrada desde el inicio."""
    crear_socio()
    mail.enviar_dia(sesiones, dataclasses.replace(config_smtp, smtp_seguridad="ssl", smtp_port=465), HOY)
    assert fake_smtp.conexiones[0]["clase"] == "SMTP_SSLFalso"


def test_ac61_rechazo_no_frena_al_resto(sesiones, config_smtp, fake_smtp, crear_socio, caplog):
    """AC-61 (RF-36, RF-55)."""
    crear_socio("José", "jose@empresa.com")
    crear_socio("Ana", "ana@empresa.com")
    fake_smtp.rechazar.add("jose@empresa.com")
    assert mail.enviar_dia(sesiones, config_smtp, HOY) == (1, 2)
    assert [m["To"] for m in fake_smtp.mensajes] == ["ana@empresa.com"]
    assert "jose@empresa.com" in caplog.text


def test_ac78_servidor_caido_al_log(sesiones, config_smtp, fake_smtp, crear_socio, caplog):
    """AC-78 (RF-55)."""
    crear_socio()
    fake_smtp.caido = True
    assert mail.enviar_dia(sesiones, config_smtp, HOY) == (0, 1)
    assert "No se pudo conectar" in caplog.text


def test_configuracion_incompleta_al_log(sesiones, config_smtp, fake_smtp, crear_socio, caplog):
    """RF-55: sin servidor o remitente configurado, el error queda en el log."""
    crear_socio()
    assert mail.enviar_dia(sesiones, dataclasses.replace(config_smtp, smtp_host=""), HOY) == (0, 1)
    assert "configuración incompleta" in caplog.text.lower()
    assert fake_smtp.conexiones == []


def test_ac115_fr036_sin_cifrado_a_otra_maquina_advierte(sesiones, config_smtp, fake_smtp, crear_socio, caplog):
    """AC-115 (RF-78); FR-036 (RNF-04): advierte y manda igual."""
    crear_socio()
    cfg = dataclasses.replace(config_smtp, smtp_seguridad="ninguna")
    assert mail.enviar_dia(sesiones, cfg, HOY) == (1, 1)
    assert "sin cifrado" in caplog.text


def test_fr036_sin_cifrado_a_la_propia_maquina_no_advierte(sesiones, config_smtp, fake_smtp,
                                                           crear_socio, caplog):
    """RF-78; FR-036: el servidor de prueba local no genera advertencia."""
    crear_socio()
    cfg = dataclasses.replace(config_smtp, smtp_seguridad="ninguna", smtp_host="127.0.0.1",
                              smtp_user="", smtp_password="")
    mail.enviar_dia(sesiones, cfg, HOY)
    assert "sin cifrado" not in caplog.text
    assert fake_smtp.conexiones[0]["login"] is None


def test_sin_socios_registra_el_dia_y_loguea(sesiones, db, config_smtp, fake_smtp, caplog):
    """Research R8 (RF-24): sin socios no se manda nada, pero el día queda iniciado."""
    assert mail.enviar_automatico(sesiones, config_smtp, HOY) is True
    assert "No hay socios" in caplog.text
    assert fake_smtp.mensajes == []
    assert db.get(EnvioDiario, HOY) is not None


def test_enviar_automatico_registra_antes_de_mandar(sesiones, db, config_smtp, fake_smtp, crear_socio):
    """RF-39: el día se registra antes de mandar, aunque el envío falle."""
    crear_socio()
    fake_smtp.caido = True
    mail.enviar_automatico(sesiones, config_smtp, HOY)
    assert db.get(EnvioDiario, HOY) is not None


def test_enviar_automatico_no_repite(sesiones, config_smtp, fake_smtp, crear_socio):
    """RF-39: un segundo envío automático del mismo día no manda nada."""
    crear_socio()
    assert mail.enviar_automatico(sesiones, config_smtp, HOY) is True
    assert mail.enviar_automatico(sesiones, config_smtp, HOY) is False
    assert len(fake_smtp.mensajes) == 1


def test_logs_sin_secretos(sesiones, config_smtp, fake_smtp, crear_socio, caplog):
    """Research R9 (RNF-04): ni la contraseña SMTP ni la SECRET_KEY aparecen en el log."""
    crear_socio()
    fake_smtp.caido = True
    mail.enviar_dia(sesiones, config_smtp, HOY)
    fake_smtp.caido = False
    fake_smtp.rechazar.add("jose@empresa.com")
    mail.enviar_dia(sesiones, config_smtp, HOY)
    assert caplog.text
    assert config_smtp.smtp_password not in caplog.text
    assert config_smtp.secret_key not in caplog.text
