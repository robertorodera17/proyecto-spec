from datetime import date

from app import formato


def test_ac83_monto_ingreso_con_punto_de_miles():
    """AC-83 (RF-59)."""
    assert formato.monto(1200) == "1.200"


def test_ac89_monto_egreso_con_signo_menos():
    """AC-89 (RF-59)."""
    assert formato.monto(-1200) == "-1.200"


def test_montos_chicos_y_grandes():
    """RF-59, RF-63: sin decimales; miles con punto."""
    assert formato.monto(-350) == "-350"
    assert formato.monto(5) == "5"
    assert formato.monto(1234567) == "1.234.567"
    assert formato.monto(-1000000) == "-1.000.000"


def test_fecha_dd_mm_aaaa():
    """RF-50: fechas en DD/MM/AAAA."""
    assert formato.fecha(date(2026, 10, 21)) == "21/10/2026"
    assert formato.fecha(date(2026, 1, 5)) == "05/01/2026"
