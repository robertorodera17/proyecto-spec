from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import fechas, seguridad
from app.db import get_db
from app.modelos import Operador

router = APIRouter()


def _render(request: Request, plantilla: str, **contexto):
    return request.app.state.templates.TemplateResponse(request, plantilla, contexto)


def _buscar(db: Session, sigla: str) -> Operador | None:
    return db.scalar(select(Operador).where(Operador.sigla == sigla.strip().upper()))


def _iniciar_sesion(request: Request, operador: Operador):
    request.session.clear()
    request.session.update({"operador_id": operador.id,
                            "ultima_actividad": fechas.ahora().timestamp()})
    return RedirectResponse("/movimientos", status_code=303)


@router.get("/login")
def pantalla_login(request: Request, vencida: str = ""):
    aviso = "Tu sesión venció por inactividad. Volvé a ingresar." if vencida else ""
    return _render(request, "login.html", aviso=aviso, error="", sigla="")


@router.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    sigla = (form.get("sigla") or "").strip().upper()
    operador = _buscar(db, sigla)
    if operador is None:
        return _render(request, "login.html", aviso="", sigla=sigla,
                       error=f"No existe un operador con la sigla {sigla}")
    if operador.password_hash is None:
        return _render(request, "definir.html", sigla=sigla, error="")
    if "password" not in form:
        return _render(request, "contrasena.html", sigla=sigla, error="")
    if not seguridad.verificar(form["password"], operador.password_hash):
        return _render(request, "contrasena.html", sigla=sigla, error="Sigla o contraseña incorrecta")
    return _iniciar_sesion(request, operador)


@router.post("/login/definir")
async def definir_contrasena(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    sigla = (form.get("sigla") or "").strip().upper()
    operador = _buscar(db, sigla)
    if operador is None:
        return _render(request, "login.html", aviso="", sigla=sigla,
                       error=f"No existe un operador con la sigla {sigla}")
    if operador.password_hash is not None:
        return _render(request, "login.html", aviso="", sigla=sigla,
                       error=f"El operador {sigla} ya tiene contraseña: ingresá con ella.")
    password, password2 = form.get("password") or "", form.get("password2") or ""
    error = ("Las contraseñas no coinciden" if password != password2
             else seguridad.validar_contrasena(password))
    if error:
        return _render(request, "definir.html", sigla=sigla, error=error)
    operador.password_hash = seguridad.hashear(password)
    db.commit()
    return _iniciar_sesion(request, operador)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
