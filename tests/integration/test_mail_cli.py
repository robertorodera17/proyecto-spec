from datetime import date

import pytest

from app import mail
from app.modelos import EnvioDiario


def enviar(sesiones, cfg, *args):
    return mail.main(["enviar", *args], sesiones=sesiones, cfg=cfg)


def test_ac66_manual_con_fecha(sesiones, config_smtp, fake_smtp, crear_socio, cargar_movimiento, capsys):
    """AC-66 (RF-40, RF-50)."""
    crear_socio()
    cargar_movimiento(descripcion="Del diez", fecha=date(2026, 10, 10))
    cargar_movimiento(descripcion="De otro día", fecha=date(2026, 10, 11))
    assert enviar(sesiones, config_smtp, "--fecha", "2026-10-10") == 0
    mensaje = fake_smtp.mensajes[0]
    assert mensaje["Subject"] == "Movimientos del 10/10/2026"
    assert "Del diez" in mensaje.get_content() and "De otro día" not in mensaje.get_content()
    assert "Enviados 1 de 1 mails del 10/10/2026" in capsys.readouterr().out


def test_manual_sin_fecha_usa_hoy(sesiones, config_smtp, fake_smtp, crear_socio, reloj):
    """RF-40: sin --fecha se manda el día de hoy en Argentina."""
    crear_socio()
    reloj.poner("2026-10-20 22:30")
    enviar(sesiones, config_smtp)
    assert fake_smtp.mensajes[0]["Subject"] == "Movimientos del 20/10/2026"


def test_ac77_manual_no_registra_dia(sesiones, db, config_smtp, fake_smtp, crear_socio):
    """AC-77 (RF-54): después del manual, el automático manda igual."""
    crear_socio()
    enviar(sesiones, config_smtp, "--fecha", "2026-10-21")
    assert db.get(EnvioDiario, date(2026, 10, 21)) is None
    assert mail.enviar_automatico(sesiones, config_smtp, date(2026, 10, 21)) is True
    assert len(fake_smtp.mensajes) == 2


def test_fecha_invalida_codigo_2(sesiones, config_smtp, fake_smtp, crear_socio):
    """contracts/cli.md: --fecha inválida termina con código 2 sin mandar."""
    crear_socio()
    with pytest.raises(SystemExit) as salida:
        enviar(sesiones, config_smtp, "--fecha", "2026-13-01")
    assert salida.value.code == 2
    assert fake_smtp.mensajes == []


def test_falla_parcial_codigo_1(sesiones, config_smtp, fake_smtp, crear_socio, capsys):
    """RF-55: si algún mail falla, el comando termina con código 1."""
    crear_socio("José", "jose@empresa.com")
    crear_socio("Ana", "ana@empresa.com")
    fake_smtp.rechazar.add("ana@empresa.com")
    assert enviar(sesiones, config_smtp, "--fecha", "2026-10-21") == 1
    assert "Enviados 1 de 2" in capsys.readouterr().out
