import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
# Valores de ejemplo de AGENTS.md: no son credenciales reales.
EJEMPLOS_DE_DOCUMENTACION = {"cuenta@gmail.com", "contraseña-de-aplicación"}


def archivos_versionados():
    salida = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                            cwd=RAIZ, capture_output=True, text=True, check=True).stdout
    return [RAIZ / linea for linea in salida.splitlines() if linea]


def test_ac45_env_no_versionado():
    """AC-45 (RNF-04): .env está ignorado y no entra al repositorio."""
    assert ".env" in (RAIZ / ".gitignore").read_text().splitlines()
    assert all(archivo.name != ".env" for archivo in archivos_versionados())


def test_ac45_sin_credenciales_en_archivos_versionables():
    """AC-45 (RNF-04): ningún archivo del repo asigna un valor a una credencial."""
    patron = re.compile(r"^\s*(SECRET_KEY|SMTP_PASSWORD|SMTP_USER)=(\S+)", re.M)
    con_credenciales = []
    for archivo in archivos_versionados():
        if archivo.is_file() and archivo.suffix not in {".db", ".png", ".ico"}:
            texto = archivo.read_text(errors="ignore")
            for clave, valor in patron.findall(texto):
                if valor not in EJEMPLOS_DE_DOCUMENTACION:
                    con_credenciales.append(f"{archivo.relative_to(RAIZ)}: {clave}")
    assert con_credenciales == []
