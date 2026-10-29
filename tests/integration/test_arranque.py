import pytest


def test_ac73_sin_secret_key_no_arranca(monkeypatch, engine):
    """AC-73 (RF-57, RNF-04): sin SECRET_KEY la app no se crea."""
    from app.main import crear_app

    monkeypatch.delenv("SECRET_KEY")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        crear_app(iniciar_programador=False, engine=engine)


def test_ac73_secret_key_vacia_no_arranca(monkeypatch, engine):
    """AC-73 (RF-57)."""
    from app.main import crear_app

    monkeypatch.setenv("SECRET_KEY", "  ")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        crear_app(iniciar_programador=False, engine=engine)


def test_arranca_sin_configuracion_de_correo(engine):
    """RF-55: sin SMTP_* la app arranca; el envío fallará y quedará en el log."""
    from app.main import crear_app

    assert crear_app(iniciar_programador=False, engine=engine) is not None
