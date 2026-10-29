import logging
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import programador
from app.modelos import EnvioDiario

HOY = date(2026, 10, 21)


@pytest.fixture(autouse=True)
def log_info(caplog):
    caplog.set_level(logging.INFO, logger="app")


def test_trabajo_programado_a_las_17_de_argentina(sesiones, config_smtp):
    """RF-24: el mail sale a las 17:00 de America/Argentina/Buenos_Aires."""
    planificador = programador.iniciar(sesiones, config_smtp)
    try:
        trabajo = planificador.get_job(programador.ID_TRABAJO)
        campos = {campo.name: str(campo) for campo in trabajo.trigger.fields}
        assert (campos["hour"], campos["minute"]) == ("17", "0")
        assert str(trabajo.trigger.timezone) == "America/Argentina/Buenos_Aires"
    finally:
        planificador.shutdown(wait=False)


def test_ac42_el_trabajo_manda_el_mail_de_hoy(sesiones, config_smtp, fake_smtp, crear_socio, reloj):
    """AC-42 (RF-24): lo que corre a las 17:00 manda el mail del día."""
    crear_socio()
    reloj.poner("2026-10-21 17:00")
    programador.mandar_mail_del_dia(sesiones, config_smtp)
    assert fake_smtp.mensajes[0]["Subject"] == "Movimientos del 21/10/2026"


def test_ac63_arranca_1730_manda(sesiones, db, config_smtp, fake_smtp, crear_socio, reloj):
    """AC-63 (RF-38)."""
    crear_socio()
    reloj.poner("2026-10-21 17:30")
    programador.recuperar_al_arrancar(sesiones, config_smtp)
    assert len(fake_smtp.mensajes) == 1
    assert db.get(EnvioDiario, HOY) is not None


def test_arranca_antes_de_las_17_no_manda(sesiones, config_smtp, fake_smtp, crear_socio, reloj):
    """RF-24: antes de las 17:00 no se adelanta el mail."""
    crear_socio()
    reloj.poner("2026-10-21 16:59")
    programador.recuperar_al_arrancar(sesiones, config_smtp)
    assert fake_smtp.mensajes == []


def test_ac64_arranca_1800_no_manda(sesiones, db, config_smtp, fake_smtp, crear_socio, reloj, caplog):
    """AC-64 (RF-52)."""
    crear_socio()
    reloj.poner("2026-10-21 18:00")
    programador.recuperar_al_arrancar(sesiones, config_smtp)
    assert fake_smtp.mensajes == []
    assert db.get(EnvioDiario, HOY) is None
    assert "no se mandó" in caplog.text


def test_ac76_log_con_comando_manual(sesiones, config_smtp, fake_smtp, crear_socio, reloj, caplog):
    """AC-76 (RF-53)."""
    crear_socio()
    reloj.poner("2026-10-21 18:00")
    programador.recuperar_al_arrancar(sesiones, config_smtp)
    assert "python -m app.mail enviar --fecha 2026-10-21" in caplog.text


def test_ac65_reinicio_no_repite(sesiones, config_smtp, fake_smtp, crear_socio, reloj):
    """AC-65 (RF-39)."""
    crear_socio()
    reloj.poner("2026-10-21 17:00")
    programador.mandar_mail_del_dia(sesiones, config_smtp)
    reloj.poner("2026-10-21 17:30")
    programador.recuperar_al_arrancar(sesiones, config_smtp)
    assert len(fake_smtp.mensajes) == 1


def test_ac79_falla_no_reintenta(sesiones, config_smtp, fake_smtp, crear_socio, reloj):
    """AC-79 (RF-56): ni mientras sigue corriendo ni al reiniciar a las 17:30."""
    crear_socio()
    fake_smtp.caido = True
    reloj.poner("2026-10-21 17:00")
    programador.mandar_mail_del_dia(sesiones, config_smtp)
    fake_smtp.caido = False
    reloj.poner("2026-10-21 17:30")
    programador.recuperar_al_arrancar(sesiones, config_smtp)
    reloj.poner("2026-10-21 18:00")
    programador.mandar_mail_del_dia(sesiones, config_smtp)
    assert fake_smtp.mensajes == []
    assert fake_smtp.conexiones == []


def test_dos_llamadas_seguidas_mandan_una_vez(sesiones, config_smtp, fake_smtp, crear_socio, reloj):
    """RF-39: la clave de envios_diarios impide el segundo envío automático."""
    crear_socio()
    reloj.poner("2026-10-21 17:00")
    programador.mandar_mail_del_dia(sesiones, config_smtp)
    programador.mandar_mail_del_dia(sesiones, config_smtp)
    assert len(fake_smtp.mensajes) == 1


def test_crear_app_sin_programador_no_programa_nada(app):
    """RF-24 (tasks T044): los tests crean la app sin programador."""
    with TestClient(app):
        assert app.state.programador is None


def test_crear_app_con_programador_lo_inicia_y_recupera(engine, reloj, monkeypatch):
    """RF-24, RF-38: al arrancar la app se recupera el mail pendiente y se programa el de las 17."""
    from app.main import crear_app

    llamadas = []

    class PlanificadorFalso:
        def shutdown(self, wait=True):
            llamadas.append("shutdown")

    monkeypatch.setattr(programador, "recuperar_al_arrancar", lambda s, c: llamadas.append("recuperar"))
    monkeypatch.setattr(programador, "iniciar", lambda s, c: llamadas.append("iniciar") or PlanificadorFalso())
    app = crear_app(iniciar_programador=True, engine=engine)
    with TestClient(app):
        assert app.state.programador is not None
    assert llamadas == ["recuperar", "iniciar", "shutdown"]
