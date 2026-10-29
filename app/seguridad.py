"""Contraseñas, sesión por inactividad y controles HTTP (research R1..R4)."""
import ipaddress
from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from passlib.context import CryptContext

from app import fechas

INACTIVIDAD_MAXIMA = 60 * 60  # segundos (RNF-03)
MINIMO_CARACTERES = 8  # RF-31
MAXIMO_BYTES = 72  # límite de bcrypt (RF-48, RF-62)

_contexto = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12)


def validar_contrasena(contrasena: str) -> str | None:
    """Mensaje de error, o None si es válida. No se recorta: se respeta lo escrito (research R1)."""
    if len(contrasena) < MINIMO_CARACTERES:
        return f"La contraseña debe tener al menos {MINIMO_CARACTERES} caracteres."
    if len(contrasena.encode("utf-8")) > MAXIMO_BYTES:
        return (f"La contraseña admite hasta {MAXIMO_BYTES} bytes "
                "(las letras con tilde ocupan dos).")
    return None


def hashear(contrasena: str) -> str:
    return _contexto.hash(contrasena)


def verificar(contrasena: str, hash_guardado: str | None) -> bool:
    if not hash_guardado:
        return False
    return _contexto.verify(contrasena, hash_guardado)


def redirigir(request: Request, destino: str) -> Response:
    """Redirección de página entera, también para pedidos HTMX."""
    if request.headers.get("HX-Request"):
        return Response(status_code=200, headers={"HX-Redirect": destino})
    return RedirectResponse(destino, status_code=303)


def es_publica(ruta: str, publicas: set[str]) -> bool:
    return ruta in publicas or any(ruta.startswith(p + "/") for p in publicas)


def exigir_sesion(publicas: set[str]):
    async def middleware(request: Request, call_next):
        if es_publica(request.url.path, publicas):
            return await call_next(request)
        sesion = request.session
        if sesion.get("operador_id") is None or sesion.get("ultima_actividad") is None:
            return redirigir(request, "/login")
        momento = fechas.ahora().timestamp()
        if momento - sesion["ultima_actividad"] >= INACTIVIDAD_MAXIMA:
            sesion.clear()
            return redirigir(request, "/login?vencida=1")
        sesion["ultima_actividad"] = momento
        return await call_next(request)

    return middleware


def _es_loopback(host: str | None) -> bool:
    try:
        return ipaddress.ip_address(host or "").is_loopback
    except ValueError:
        return False


async def solo_cifrado(request: Request, call_next):
    """FR-035: fuera de la propia máquina, solo por HTTPS."""
    if request.url.scheme == "http" and not _es_loopback(request.client and request.client.host):
        return HTMLResponse(
            "<p>Esta aplicación solo se usa por conexión cifrada. "
            "Usá la dirección https://… que te indicó sistemas.</p>",
            status_code=403,
        )
    return await call_next(request)


async def chequeo_origen(request: Request, call_next):
    """Research R3: todo POST debe venir de una página del propio sitio."""
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origen = request.headers.get("origin") or request.headers.get("referer")
        if not origen or urlsplit(origen).netloc != request.headers.get("host"):
            return HTMLResponse("<p>Pedido rechazado: origen no permitido.</p>", status_code=403)
    return await call_next(request)
