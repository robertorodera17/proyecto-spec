from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import clasificacion, fechas, movimientos, seguridad
from app.db import get_db
from app.modelos import Movimiento, TipoMovimiento

router = APIRouter()

CAMPOS = ("descripcion", "tipo", "monto", "clasificacion", "fecha")


def _render(request: Request, plantilla: str, contexto: dict, status_code: int = 200):
    return request.app.state.templates.TemplateResponse(request, plantilla, contexto,
                                                         status_code=status_code)


def _formulario(request: Request, valores: dict, errores: dict | None = None, status_code: int = 200,
                id_: int | None = None, original: dict | None = None):
    """Alta si id_ es None; si no, modificación del movimiento id_ (con su tipo y clasificación guardados)."""
    tipo = valores.get("tipo", "")
    return _render(request, "formulario.html", {
        "valores": valores,
        "errores": errores or {},
        "tipos": list(TipoMovimiento),
        "clasificaciones": clasificacion.por_tipo(tipo),
        "id": id_,
        "original": original or {},
    }, status_code)


def _error(request: Request, status_code: int, titulo: str, mensaje: str):
    return _render(request, "error.html", {"titulo": titulo, "mensaje": mensaje}, status_code)


def _no_encontrado(request: Request):
    return _error(request, 404, "Movimiento inexistente", "El movimiento no existe o fue eliminado.")


def _ya_eliminado(request: Request):
    return _error(request, 409, "No se pudo guardar", "El movimiento fue eliminado.")


@router.get("/")
def inicio():
    return RedirectResponse("/movimientos", status_code=303)


@router.get("/movimientos")
def grilla(request: Request, pagina: str = "1", db: Session = Depends(get_db)):
    numero = int(pagina) if pagina.isdigit() else 1
    return _render(request, "grilla.html", {"pagina": movimientos.pagina(db, numero)})


@router.get("/movimientos/nuevo")
def nuevo(request: Request):
    valores = dict.fromkeys(CAMPOS, "")
    valores["fecha"] = fechas.hoy().isoformat()
    return _formulario(request, valores)


@router.get("/movimientos/clasificacion")
def fragmento_clasificacion(request: Request, tipo: str = "",
                            clasificacion_actual: str = Query("", alias="clasificacion"),
                            descripcion: str | None = None, tipo_original: str | None = None,
                            clasificacion_original: str = ""):
    opciones = clasificacion.por_tipo(tipo)
    if tipo_original is not None:
        # Modificación: otro tipo vacía la clasificación; volver al original la recupera (RF-46, RF-47).
        seleccion = clasificacion_original if tipo == tipo_original else ""
    elif descripcion is not None:
        # Alta: la propuesta de la descripción reemplaza la elección manual (RF-42, RF-66).
        seleccion = clasificacion.proponer(descripcion, tipo) or ""
    else:
        seleccion = clasificacion_actual if clasificacion_actual in opciones else ""
    return _render(request, "_clasificacion.html", {"clasificaciones": opciones, "seleccion": seleccion})


@router.post("/movimientos")
async def crear(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    valores = {campo: form.get(campo, "") for campo in CAMPOS}
    datos, errores = movimientos.validar(valores, fechas.hoy())
    if errores:
        return _formulario(request, valores, errores, status_code=422)
    movimientos.crear(db, datos)
    return RedirectResponse("/movimientos", status_code=303)


@router.get("/movimientos/{id_}/editar")
def editar(request: Request, id_: int, db: Session = Depends(get_db)):
    try:
        m = movimientos.vigente(db, id_)
    except (movimientos.MovimientoInexistente, movimientos.MovimientoEliminado):
        return _no_encontrado(request)
    valores = {"descripcion": m.descripcion, "tipo": m.tipo, "monto": str(abs(m.monto)),
               "clasificacion": m.clasificacion, "fecha": m.fecha.isoformat()}
    return _formulario(request, valores, id_=id_,
                       original={"tipo": m.tipo, "clasificacion": m.clasificacion})


@router.post("/movimientos/{id_}")
async def guardar_modificacion(request: Request, id_: int, db: Session = Depends(get_db)):
    form = await request.form()
    valores = {campo: form.get(campo, "") for campo in CAMPOS}
    original = {"tipo": form.get("tipo_original", ""), "clasificacion": form.get("clasificacion_original", "")}
    datos, errores = movimientos.validar(valores, fechas.hoy())
    if errores:
        if db.get(Movimiento, id_) is None:
            return _no_encontrado(request)
        return _formulario(request, valores, errores, 422, id_=id_, original=original)
    try:
        movimientos.modificar(db, id_, datos)
    except movimientos.MovimientoInexistente:
        return _no_encontrado(request)
    except movimientos.MovimientoEliminado:
        return _ya_eliminado(request)
    return seguridad.redirigir(request, "/movimientos")


@router.post("/movimientos/{id_}/eliminar")
def eliminar(request: Request, id_: int, db: Session = Depends(get_db)):
    try:
        movimientos.eliminar(db, id_)
    except movimientos.MovimientoInexistente:
        return _no_encontrado(request)
    except movimientos.MovimientoEliminado:
        return _error(request, 409, "No se pudo eliminar", "El movimiento fue eliminado.")
    return seguridad.redirigir(request, "/movimientos")
