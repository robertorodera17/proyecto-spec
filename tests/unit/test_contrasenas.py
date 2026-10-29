from app import seguridad


def test_ac53_7_caracteres_rechaza():
    """AC-53 (RF-31)."""
    assert seguridad.validar_contrasena("1234567") is not None


def test_ac98_8_caracteres_acepta():
    """AC-98 (RF-31)."""
    assert seguridad.validar_contrasena("12345678") is None


def test_ac72_72_bytes_acepta():
    """AC-72 (RF-48)."""
    assert seguridad.validar_contrasena("a" * 72) is None


def test_ac86_73_bytes_rechaza():
    """AC-86 (RF-62)."""
    assert seguridad.validar_contrasena("a" * 73) is not None


def test_ac86_tildes_cuentan_como_dos_bytes():
    """AC-86 (RF-62, RF-48): 37 "á" son 37 caracteres pero 74 bytes."""
    assert seguridad.validar_contrasena("á" * 36) is None
    assert seguridad.validar_contrasena("á" * 37) is not None


def test_minimo_se_cuenta_en_caracteres():
    """RF-31: 8 caracteres con tilde alcanzan aunque sean más bytes; 7 no."""
    assert seguridad.validar_contrasena("ñ" * 8) is None
    assert seguridad.validar_contrasena("ñ" * 7) is not None


def test_espacios_de_los_extremos_se_conservan():
    """Research R1: la contraseña no se recorta."""
    hash_ = seguridad.hashear(" clave con espacios ")
    assert seguridad.verificar(" clave con espacios ", hash_)
    assert not seguridad.verificar("clave con espacios", hash_)


def test_ac44_hash_no_es_texto_plano():
    """AC-44 (RNF-02)."""
    hash_ = seguridad.hashear("secreta123")
    assert "secreta123" not in hash_


def test_ac95_hash_bcrypt_costo_12():
    """AC-95 (RNF-02)."""
    assert seguridad.hashear("secreta123").startswith("$2b$12$")


def test_verificar_correcta_e_incorrecta():
    """RF-20."""
    hash_ = seguridad.hashear("secreta123")
    assert seguridad.verificar("secreta123", hash_)
    assert not seguridad.verificar("secreta124", hash_)
    assert not seguridad.verificar("secreta123", None)
