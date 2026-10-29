from datetime import date, datetime, timezone

from app import fechas


class _DatetimeFijo(datetime):
    momento_utc = datetime(2026, 10, 21, 1, 30, tzinfo=timezone.utc)

    @classmethod
    def now(cls, tz=None):
        return cls.momento_utc.astimezone(tz) if tz else cls.momento_utc.replace(tzinfo=None)


def test_ac97_hoy_es_el_dia_de_argentina_con_servidor_utc(monkeypatch):
    """AC-97 (RF-03): 01:30 UTC del 21/10 son las 22:30 del 20/10 en Argentina."""
    monkeypatch.setattr(fechas, "datetime", _DatetimeFijo)
    assert fechas.hoy() == date(2026, 10, 20)


def test_ahora_tiene_zona_de_argentina():
    """RF-03: ahora() es aware y en hora de Argentina."""
    momento = fechas.ahora()
    assert momento.tzinfo is not None
    assert momento.utcoffset() == fechas.ZONA.utcoffset(momento)
    assert str(fechas.ZONA) == "America/Argentina/Buenos_Aires"
