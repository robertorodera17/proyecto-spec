from datetime import date

import pytest

from app.movimientos import validar

HOY = date(2026, 10, 21)


def formulario(**cambios):
    base = {"descripcion": "Sueldo marzo", "tipo": "EGRESO", "monto": "1000",
            "clasificacion": "SUELDOS", "fecha": "2026-10-20"}
    base.update(cambios)
    return base


def test_formulario_valido():
    """RF-01."""
    datos, errores = validar(formulario(), HOY)
    assert errores == {}
    assert datos == {"descripcion": "Sueldo marzo", "tipo": "EGRESO", "monto": -1000,
                     "clasificacion": "SUELDOS", "fecha": date(2026, 10, 20)}


@pytest.mark.parametrize("campo", ["descripcion", "tipo", "monto", "clasificacion"])
def test_ac19_campo_obligatorio_vacio(campo):
    """AC-19 (RF-02): cada campo obligatorio vacío se marca."""
    datos, errores = validar(formulario(**{campo: ""}), HOY)
    assert datos is None
    assert campo in errores


def test_ac19_campo_ausente():
    """AC-19 (RF-02): un campo que no llega cuenta como vacío."""
    form = formulario()
    del form["monto"]
    assert "monto" in validar(form, HOY)[1]


def test_ac21_tipo_fuera_de_la_lista():
    """AC-21 (RF-04): solo Ingreso y Egreso."""
    assert "tipo" in validar(formulario(tipo="TRANSFERENCIA"), HOY)[1]


@pytest.mark.parametrize("monto, ac", [("0", "AC-24"), ("-500", "AC-25"), ("12abc", "AC-26"),
                                       ("12,5", "AC-82"), ("12.5", "AC-82"), ("1.200", "AC-88"),
                                       ("1 200", "AC-88"), ("+500", "AC-25")])
def test_monto_invalido(monto, ac):
    """AC-24, AC-25, AC-26 (RF-07); AC-82 (RF-58); AC-88 (RF-64)."""
    datos, errores = validar(formulario(monto=monto), HOY)
    assert datos is None, ac
    assert "monto" in errores, ac


def test_ac24_monto_cero():
    """AC-24 (RF-07)."""
    assert "monto" in validar(formulario(monto="0"), HOY)[1]


def test_ac25_monto_negativo():
    """AC-25 (RF-07)."""
    assert "monto" in validar(formulario(monto="-500"), HOY)[1]


def test_ac26_monto_no_numerico():
    """AC-26 (RF-07)."""
    assert "monto" in validar(formulario(monto="12abc"), HOY)[1]


def test_ac82_monto_con_decimales():
    """AC-82 (RF-58)."""
    assert "monto" in validar(formulario(monto="12,5"), HOY)[1]


def test_ac88_monto_con_separador_de_miles():
    """AC-88 (RF-64)."""
    assert "monto" in validar(formulario(monto="1.200"), HOY)[1]


def test_ac106_fr003_monto_maximo():
    """AC-106 (RF-72); FR-003 (RF-07): hasta el máximo de 64 bits se acepta; uno más se rechaza."""
    assert validar(formulario(tipo="INGRESO", clasificacion="ALQUILERES",
                              monto="9223372036854775807"), HOY)[1] == {}
    assert "monto" in validar(formulario(monto="9223372036854775808"), HOY)[1]


def test_monto_con_espacios_en_los_extremos_se_acepta():
    """RF-07: los espacios alrededor de los dígitos no cambian el número."""
    datos, errores = validar(formulario(monto=" 1200 "), HOY)
    assert errores == {} and datos["monto"] == -1200


def test_ac22_egreso_se_guarda_negativo():
    """AC-22 (RF-05)."""
    assert validar(formulario(monto="500"), HOY)[0]["monto"] == -500


def test_ac23_ingreso_se_guarda_positivo():
    """AC-23 (RF-06)."""
    datos, _ = validar(formulario(tipo="INGRESO", clasificacion="ALQUILERES", monto="500"), HOY)
    assert datos["monto"] == 500


def test_ac47_fecha_inexistente():
    """AC-47 (RF-44)."""
    assert "fecha" in validar(formulario(fecha="2026-02-30"), HOY)[1]


def test_fecha_con_formato_invalido():
    """RF-44: solo AAAA-MM-DD (lo que manda el control de fecha del navegador)."""
    assert "fecha" in validar(formulario(fecha="30/02/2026"), HOY)[1]


def test_ac46_fecha_vacia_es_hoy():
    """AC-46 (RF-43)."""
    assert validar(formulario(fecha=""), HOY)[0]["fecha"] == HOY
    assert validar(formulario(fecha="   "), HOY)[0]["fecha"] == HOY


def test_ac104_fr004_fecha_futura_rechazada_y_hoy_aceptada():
    """AC-104 (RF-70); FR-004 (RF-44)."""
    assert "fecha" in validar(formulario(fecha="2026-10-22"), HOY)[1]
    assert validar(formulario(fecha="2026-10-21"), HOY)[1] == {}


def test_ac105_fr004_fecha_minima_1900():
    """AC-105 (RF-71); FR-004 (RF-44)."""
    assert "fecha" in validar(formulario(fecha="1899-12-31"), HOY)[1]
    assert validar(formulario(fecha="1900-01-01"), HOY)[1] == {}


def test_ac107_fr034_descripcion_solo_espacios_es_vacia():
    """AC-107 (RF-73); FR-034 (RF-02)."""
    assert "descripcion" in validar(formulario(descripcion="   "), HOY)[1]


def test_ac107_fr034_descripcion_se_recorta():
    """AC-107 (RF-73); FR-034 (RF-01)."""
    assert validar(formulario(descripcion="  Sueldo  "), HOY)[0]["descripcion"] == "Sueldo"


def test_ac108_fr034_descripcion_200_y_201_caracteres():
    """AC-108 (RF-74); FR-034 (RF-01): el máximo se cuenta después de recortar."""
    assert validar(formulario(descripcion="a" * 200), HOY)[1] == {}
    assert validar(formulario(descripcion="  " + "a" * 200 + "  "), HOY)[1] == {}
    assert "descripcion" in validar(formulario(descripcion="a" * 201), HOY)[1]


def test_ac09_egreso_con_clasificacion_de_ingreso():
    """AC-09 (RF-17, FR-015)."""
    datos, errores = validar(formulario(clasificacion="ALQUILERES"), HOY)
    assert datos is None and "clasificacion" in errores


def test_ac10_ingreso_con_clasificacion_de_egreso():
    """AC-10 (RF-17, FR-015)."""
    datos, errores = validar(formulario(tipo="INGRESO", clasificacion="SUELDOS"), HOY)
    assert datos is None and "clasificacion" in errores


def test_clasificacion_inexistente():
    """RF-13, RF-14."""
    assert "clasificacion" in validar(formulario(clasificacion="OTRA"), HOY)[1]


def test_varios_errores_a_la_vez():
    """RF-02: se informan todos los campos con error, no solo el primero."""
    _, errores = validar({"descripcion": "", "tipo": "EGRESO", "monto": "0",
                          "clasificacion": "SUELDOS", "fecha": "2026-02-30"}, HOY)
    assert set(errores) == {"descripcion", "monto", "fecha"}
