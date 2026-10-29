"""Mail diario a los socios (RF-24..25, RF-36..40, RF-50..56, RF-63, RF-67..68, FR-036).

Envío manual: python -m app.mail enviar [--fecha AAAA-MM-DD]
"""
import argparse
import ipaddress
import logging
import smtplib
import sys
from datetime import date
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import config, db, fechas, formato
from app.config import Config
from app.modelos import EnvioDiario, Movimiento, Socio, TipoMovimiento

log = logging.getLogger(__name__)


def movimientos_del_dia(sesion, fecha: date) -> list[Movimiento]:
    consulta = (select(Movimiento)
                .where(Movimiento.fecha == fecha, Movimiento.eliminado.is_(False))
                .order_by(Movimiento.id.desc()))
    return list(sesion.scalars(consulta))


def _linea(m: Movimiento) -> str:
    tipo = TipoMovimiento(m.tipo).etiqueta
    return (f"{formato.fecha(m.fecha)} | {tipo:<7} | {m.clasificacion:<19} | "
            f"{formato.monto(m.monto):>12} | {m.descripcion}")


def armar(socio: Socio, fecha: date, movimientos: list[Movimiento], remitente: str) -> EmailMessage:
    titulo = f"Movimientos del {formato.fecha(fecha)}"
    lineas = [titulo, f"Cantidad: {len(movimientos)}", ""]
    lineas += [_linea(m) for m in movimientos] if movimientos else ["No hubo movimientos."]
    mensaje = EmailMessage()
    mensaje["Subject"] = titulo
    mensaje["From"] = remitente
    mensaje["To"] = socio.mail
    mensaje.set_content("\n".join(lineas) + "\n")
    return mensaje


def _es_local(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _conectar(cfg: Config):
    if cfg.smtp_seguridad == "ssl":
        servidor = smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, timeout=30)
    else:
        servidor = smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=30)
        if cfg.smtp_seguridad == "starttls":
            servidor.starttls()
        elif not _es_local(cfg.smtp_host):
            log.warning("El mail se manda sin cifrado a %s (SMTP_SEGURIDAD=ninguna)", cfg.smtp_host)
    if cfg.smtp_user:
        servidor.login(cfg.smtp_user, cfg.smtp_password)
    return servidor


def enviar_dia(sesiones, cfg: Config, fecha: date) -> tuple[int, int]:
    """Manda a cada socio el mail de la fecha. Devuelve (enviados, socios). Sin reintentos (RF-56)."""
    with sesiones() as sesion:
        socios = list(sesion.scalars(select(Socio).order_by(Socio.id)))
        movimientos = movimientos_del_dia(sesion, fecha)
    dia = formato.fecha(fecha)
    if not socios:
        log.warning("No hay socios: no se mandó el mail del %s", dia)
        return 0, 0
    if not cfg.smtp_host or not cfg.smtp_from:
        log.error("No se mandó el mail del %s: configuración incompleta (falta SMTP_HOST o SMTP_FROM)", dia)
        return 0, len(socios)
    try:
        servidor = _conectar(cfg)
    except (OSError, smtplib.SMTPException) as error:
        log.error("No se mandó el mail del %s: %s", dia, error)
        return 0, len(socios)

    enviados = 0
    try:
        for socio in socios:
            try:
                servidor.send_message(armar(socio, fecha, movimientos, cfg.smtp_from))
                enviados += 1
            except (OSError, smtplib.SMTPException) as error:
                log.error("No se pudo mandar el mail del %s a %s: %s", dia, socio.mail, error)
    finally:
        try:
            servidor.quit()
        except (OSError, smtplib.SMTPException):
            pass
    log.info("Mail del %s: enviados %d de %d", dia, enviados, len(socios))
    return enviados, len(socios)


def enviar_automatico(sesiones, cfg: Config, fecha: date) -> bool:
    """Envío de las 17:00: registra el día antes de mandar, así nunca se repite (RF-39)."""
    with sesiones() as sesion:
        sesion.add(EnvioDiario(fecha=fecha, iniciado_en=fechas.ahora().replace(tzinfo=None)))
        try:
            sesion.commit()
        except IntegrityError:
            sesion.rollback()
            log.info("El mail automático del %s ya se había iniciado: no se repite", formato.fecha(fecha))
            return False
    enviar_dia(sesiones, cfg, fecha)
    return True


def _fecha(texto: str) -> date:
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise argparse.ArgumentTypeError(f"fecha inválida: {texto} (usar AAAA-MM-DD)")


def main(argv: list[str] | None = None, sesiones=None, cfg: Config | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.mail")
    subcomandos = parser.add_subparsers(dest="comando", required=True)
    enviar = subcomandos.add_parser("enviar", help="Manda a mano el mail de un día (no lo registra)")
    enviar.add_argument("--fecha", type=_fecha, help="AAAA-MM-DD; por defecto, hoy en Argentina")
    args = parser.parse_args(argv)

    cfg = cfg or config.cargar(exigir_secret_key=False)
    sesiones = sesiones or db.crear_sesiones(db.crear_engine(cfg.database_url))
    fecha = args.fecha or fechas.hoy()
    enviados, total = enviar_dia(sesiones, cfg, fecha)
    print(f"Enviados {enviados} de {total} mails del {formato.fecha(fecha)}")
    return 0 if enviados == total else 1


if __name__ == "__main__":
    from app.main import configurar_log

    configurar_log()
    sys.exit(main())
