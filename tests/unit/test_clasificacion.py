from app.clasificacion import proponer


def test_ac01_sueldo_marzo():
    """AC-01 (RF-15)."""
    assert proponer("Sueldo marzo", "EGRESO") == "SUELDOS"


def test_ac02_impuesto_municipal():
    """AC-02 (RF-15)."""
    assert proponer("Impuesto municipal", "EGRESO") == "IMPUESTOS-TASAS"


def test_ac03_viaticos_cordoba():
    """AC-03 (RF-15)."""
    assert proponer("Viáticos Córdoba", "EGRESO") == "VIATICOS"


def test_ac04_proveedor_de_resmas():
    """AC-04 (RF-15)."""
    assert proponer("Proveedor de resmas", "EGRESO") == "PAGO-PROVEEDORES"


def test_ac05_turismo_bariloche():
    """AC-05 (RF-15)."""
    assert proponer("Turismo Bariloche", "EGRESO") == "TURISMO"


def test_ac06_servicio_de_consultoria():
    """AC-06 (RF-15)."""
    assert proponer("Servicio de consultoría", "INGRESO") == "SERVICIOS-PRESTADOS"


def test_ac07_alquiler_local():
    """AC-07 (RF-15)."""
    assert proponer("Alquiler local", "INGRESO") == "ALQUILERES"


def test_ac08_financiacion_cliente():
    """AC-08 (RF-15)."""
    assert proponer("Financiación cliente", "INGRESO") == "FINANCIEROS"


def test_ac12_compra_de_cafe_sin_propuesta():
    """AC-12 (RF-16)."""
    assert proponer("Compra de café", "EGRESO") is None


def test_ac13_dos_clasificaciones_sin_propuesta():
    """AC-13 (RF-16)."""
    assert proponer("Impuesto sobre sueldos", "EGRESO") is None


def test_ac14_mayusculas_sin_tilde():
    """AC-14 (RF-15)."""
    assert proponer("VIATICO cordoba", "EGRESO") == "VIATICOS"


def test_ac15_factura_no_coincide_con_tur():
    """AC-15 (RF-15): la clave tiene que estar al inicio de una palabra."""
    assert proponer("Factura de luz", "EGRESO") is None


def test_ac16_alquiler_en_egreso_sin_propuesta():
    """AC-16 (RF-15): solo cuentan las claves del tipo elegido."""
    assert proponer("Alquiler oficina", "EGRESO") is None


def test_ac81_misma_clave_repetida_cuenta_una():
    """AC-81 (RF-16)."""
    assert proponer("Sueldo marzo y sueldo abril", "EGRESO") == "SUELDOS"


def test_tildes_en_la_clave_y_en_la_descripcion():
    """RF-15: la comparación no distingue tildes."""
    assert proponer("SERVÍCIO técnico", "INGRESO") == "SERVICIOS-PRESTADOS"
    assert proponer("Viático", "EGRESO") == "VIATICOS"


def test_sin_tipo_o_sin_descripcion_no_propone():
    """RF-15: sin tipo elegido, o sin descripción, no hay propuesta."""
    assert proponer("Sueldo marzo", "") is None
    assert proponer("", "EGRESO") is None


def test_palabra_pegada_a_puntuacion():
    """RF-15: la puntuación separa palabras."""
    assert proponer("Pago: sueldos/marzo", "EGRESO") == "SUELDOS"
