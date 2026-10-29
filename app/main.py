import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.engine import Engine
from starlette.middleware.sessions import SessionMiddleware

from app import config, db, fechas, formato, seguridad

# Únicas rutas sin sesión (RF-21). Todo lo demás exige haber iniciado sesión.
RUTAS_PUBLICAS = {"/login", "/login/definir", "/static"}

CARPETA = Path(__file__).parent


class FormatterArgentina(logging.Formatter):
    """La hora de los logs es la de Argentina (research R9)."""

    def formatTime(self, record, datefmt=None):
        return fechas.ahora().strftime(datefmt or "%Y-%m-%d %H:%M:%S")


def configurar_log() -> None:
    registro = logging.getLogger("app")
    if not registro.handlers:
        manejador = logging.StreamHandler()
        manejador.setFormatter(FormatterArgentina("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        registro.addHandler(manejador)
        registro.setLevel(logging.INFO)


def crear_templates() -> Jinja2Templates:
    templates = Jinja2Templates(directory=CARPETA / "templates")
    templates.env.filters["monto"] = formato.monto
    templates.env.filters["fecha"] = formato.fecha
    return templates


def crear_app(iniciar_programador: bool = True, engine: Engine | None = None) -> FastAPI:
    cfg = config.cargar()
    configurar_log()
    motor = engine or db.crear_engine(cfg.database_url)
    sesiones = db.crear_sesiones(motor)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        _app.state.programador = None
        if iniciar_programador:
            from app import programador

            programador.recuperar_al_arrancar(sesiones, cfg)
            _app.state.programador = programador.iniciar(sesiones, cfg)
        yield
        if _app.state.programador:
            _app.state.programador.shutdown(wait=False)

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.config = cfg
    app.state.sesiones = sesiones
    app.state.templates = crear_templates()

    # El último agregado es el más externo: cifrado → origen → sesión → exigir sesión → rutas.
    app.middleware("http")(seguridad.exigir_sesion(RUTAS_PUBLICAS))
    app.add_middleware(SessionMiddleware, secret_key=cfg.secret_key, max_age=None,
                       same_site="strict", https_only=bool(cfg.tls_cert))
    app.middleware("http")(seguridad.chequeo_origen)
    app.middleware("http")(seguridad.solo_cifrado)

    app.mount("/static", StaticFiles(directory=CARPETA / "static"), name="static")
    for router in _routers():
        app.include_router(router)
    return app


def _routers():
    import importlib

    routers = []
    for nombre in ("login", "movimientos"):
        try:
            routers.append(importlib.import_module(f"app.rutas.{nombre}").router)
        except ModuleNotFoundError as error:
            if error.name != f"app.rutas.{nombre}":
                raise
    return routers


def middleware_de_sesion(app: FastAPI) -> dict:
    for middleware in app.user_middleware:
        if middleware.cls is SessionMiddleware:
            return dict(getattr(middleware, "kwargs", None) or middleware.options)
    raise LookupError("La app no tiene SessionMiddleware")


def __getattr__(nombre: str):
    # uvicorn app.main:app crea la app recién al pedirla, así importar el módulo
    # (por ejemplo, en los tests) no exige un .env completo.
    if nombre == "app":
        globals()["app"] = crear_app()
        return globals()["app"]
    raise AttributeError(nombre)
