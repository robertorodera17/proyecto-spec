"""Configuración leída de .env (RNF-04). Las variables del entorno pisan las de .env."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv(override=False)


def database_url() -> str:
    return os.environ.get("DATABASE_URL") or "sqlite:///movimientos.db"


@dataclass(frozen=True)
class Config:
    secret_key: str
    database_url: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_from: str
    smtp_seguridad: str
    tls_cert: str
    tls_key: str


def _env(clave: str, defecto: str = "") -> str:
    return (os.environ.get(clave) or defecto).strip()


def cargar(exigir_secret_key: bool = True) -> Config:
    """La app exige SECRET_KEY (RF-57); los comandos de consola no la usan."""
    secret_key = _env("SECRET_KEY")
    if exigir_secret_key and not secret_key:
        raise RuntimeError("Falta SECRET_KEY en .env: la aplicación no puede arrancar")
    return Config(
        secret_key=secret_key,
        database_url=database_url(),
        smtp_host=_env("SMTP_HOST"),
        smtp_port=int(_env("SMTP_PORT", "587")),
        smtp_user=_env("SMTP_USER"),
        smtp_password=_env("SMTP_PASSWORD"),
        smtp_from=_env("SMTP_FROM"),
        smtp_seguridad=_env("SMTP_SEGURIDAD", "starttls").lower(),
        tls_cert=_env("TLS_CERT"),
        tls_key=_env("TLS_KEY"),
    )
