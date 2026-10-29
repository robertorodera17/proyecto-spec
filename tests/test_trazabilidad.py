"""SC-007 y Constitución, Principio I: cada AC, RF y RNF del PRD, y cada FR nuevo de la spec,
tiene al menos un test que lo cita (los AC y FR en el nombre, por ejemplo test_ac104_fr004_…;
los RF/RNF en el docstring)."""
import ast
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PRD = (RAIZ / "PRD.md").read_text(encoding="utf-8")
# FR que agregó Clarifications; también tienen AC en el PRD (AC-104..115), pero se exigen por nombre.
FR_NUEVOS = {3, 4, 22, 33, 34, 35, 36}


def _tests():
    for archivo in (RAIZ / "tests").rglob("test_*.py"):
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.FunctionDef) and nodo.name.startswith("test_"):
                yield nodo.name, ast.get_docstring(nodo) or ""


def _ids_del_prd(prefijo):
    return {int(n) for n in re.findall(rf"\*\*{prefijo}-(\d+)", PRD)}


def test_cada_ac_del_prd_tiene_un_test_con_su_id_en_el_nombre():
    """Constitución Principio I (SC-007)."""
    citados = {int(n) for nombre, _ in _tests() for n in re.findall(r"^test_ac(\d+)_", nombre)}
    faltan = sorted(_ids_del_prd("AC") - citados)
    assert faltan == [], f"AC sin test: {', '.join(f'AC-{n:02d}' for n in faltan)}"


def test_cada_rf_y_rnf_del_prd_aparece_en_el_docstring_de_un_test():
    """Constitución Principio I (SC-007)."""
    docstrings = " ".join(doc for _, doc in _tests())
    faltan = []
    for prefijo in ("RF", "RNF"):
        citados = {int(n) for n in re.findall(rf"\b{prefijo}-(\d+)", docstrings)}
        faltan += [f"{prefijo}-{n:02d}" for n in sorted(_ids_del_prd(prefijo) - citados)]
    assert faltan == [], f"Requisitos sin test: {', '.join(faltan)}"


def test_cada_fr_nuevo_de_la_spec_tiene_un_test_con_su_id_en_el_nombre():
    """Constitución Principio I (SC-007): FR agregados por Clarifications."""
    citados = {int(n) for nombre, _ in _tests() for n in re.findall(r"(?:^test_|_)fr(\d{3})_", nombre)}
    faltan = sorted(FR_NUEVOS - citados)
    assert faltan == [], f"FR sin test: {', '.join(f'FR-{n:03d}' for n in faltan)}"
