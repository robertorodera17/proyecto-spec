"""Programa el mail de las 17:00 y recupera el del día al arrancar (RF-24, RF-38, RF-52, RF-53)."""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app import fechas, mail
from app.config import Config
from app.modelos import EnvioDiario

log = logging.getLogger(__name__)

ID_TRABAJO = "mail_diario"
HORA_ENVIO = 17
HORA_LIMITE = 18


def mandar_mail_del_dia(sesiones, cfg: Config) -> None:
    mail.enviar_automatico(sesiones, cfg, fechas.hoy())


def iniciar(sesiones, cfg: Config) -> BackgroundScheduler:
    planificador = BackgroundScheduler(timezone=fechas.ZONA)
    planificador.add_job(mandar_mail_del_dia, CronTrigger(hour=HORA_ENVIO, minute=0, timezone=fechas.ZONA),
                         args=(sesiones, cfg), id=ID_TRABAJO, coalesce=True,
                         misfire_grace_time=(HORA_LIMITE - HORA_ENVIO) * 3600 - 1)
    planificador.start()
    return planificador


def recuperar_al_arrancar(sesiones, cfg: Config) -> None:
    momento = fechas.ahora()
    hoy = momento.date()
    with sesiones() as sesion:
        ya_iniciado = sesion.scalar(select(EnvioDiario).where(EnvioDiario.fecha == hoy)) is not None
    if ya_iniciado or momento.hour < HORA_ENVIO:
        return
    if momento.hour < HORA_LIMITE:
        log.info("La aplicación arrancó a las %s sin haber mandado el mail del día: se manda ahora",
                 momento.strftime("%H:%M"))
        mail.enviar_automatico(sesiones, cfg, hoy)
    else:
        log.warning("El mail del %s no se mandó (la aplicación no estaba corriendo entre las 17 y las 18). "
                    "Para mandarlo a mano: python -m app.mail enviar --fecha %s",
                    hoy.strftime("%d/%m/%Y"), hoy.isoformat())
