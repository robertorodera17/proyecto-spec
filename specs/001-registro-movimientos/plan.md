# Implementation Plan: Registro de movimientos con mail diario a los socios

**Branch**: `001-registro-movimientos` (sin rama propia; se trabaja en `master`) | **Date**: 2026-10-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-registro-movimientos/spec.md`

## Summary

App web interna para que los operadores carguen, modifiquen y den de baja (lógica) movimientos de
ingreso/egreso, con clasificación propuesta por palabra clave, y un mail diario en texto plano a
cada socio a las 17:00 de Argentina. Enfoque: FastAPI con páginas Jinja2 + HTMX, SQLite con
SQLAlchemy/Alembic, sesión en cookie firmada con vencimiento por inactividad, APScheduler para el
mail y `smtplib` para enviarlo. Todo se desarrolla test-first contra los AC del PRD y los FR nuevos
de Clarifications. Decisiones en [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI 0.115, Uvicorn, Jinja2, python-multipart, HTMX 2 (archivo local
en `app/static/`), SQLAlchemy 2.x, Alembic, APScheduler 3.x, passlib 1.7.4 + bcrypt 4.0.1,
itsdangerous, python-dotenv, tzdata

**Storage**: SQLite (`movimientos.db`, ruta en `.env` como `DATABASE_URL`)

**Testing**: pytest + httpx (cliente de pruebas de FastAPI), SQLite en memoria, SMTP de prueba en
memoria; `aiosmtpd` solo para la validación manual

**Target Platform**: Linux / WSL2, una sola instancia; navegadores de escritorio de la red interna

**Project Type**: web-service con páginas server-side + comandos de consola

**Performance Goals**: clasificación propuesta < 2 s p95 (RNF-01); grilla de 30 filas sobre ~50.000
movimientos por año sin demora perceptible (índice por `eliminado, fecha, id`)

**Constraints**: hora de Argentina en todo cálculo de "hoy" (`app.fechas`); baja lógica; 0 secretos
en el repo; HTTPS fuera de loopback; un solo programador de mails (una instancia)

**Scale/Scope**: 1 a pocos operadores, ~200 movimientos/día, pocos socios; 4 tablas, ~10 rutas,
3 comandos de consola

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / regla | Cómo lo cumple el plan | Estado |
|---|---|---|
| I. Test-First | `tasks.md` ordena test rojo → implementación → refactor por cada FR/AC; tests con el id en el nombre; `pytest` completo antes de cada commit (R14) | ✅ |
| II. Fuente de verdad y revisión humana | Clasificación: 0 o >1 coincidencias → no propone, elige el operador (R7). Mail armado solo desde la base. Montos fuera del rango representable se rechazan en vez de alterarse (R6). Las reglas nuevas que propuso el plan las confirmó el usuario y están en la spec | ✅ |
| III. Cero secretos | `.env` fuera del repo, `.env.example` vacío, `SECRET_KEY` obligatoria al arrancar, logs sin secretos, bcrypt costo 12 (R1, R9, R11) | ✅ |
| Restricciones técnicas: stack | Coincide con la constitución; se suman librerías auxiliares (python-multipart, itsdangerous, python-dotenv, tzdata, passlib/bcrypt de `AGENTS.md`), no se cambia ninguna pieza | ✅ |
| Restricciones: `app.fechas.hoy()` | Único punto de hora (R5) | ✅ |
| Restricciones: baja lógica | Campo `eliminado`, sin `DELETE` (data-model) | ✅ |
| Restricciones: `RUTAS_PUBLICAS` | Lista explícita en `app/main.py` (contrato rutas-http) | ✅ |
| Restricciones: sin bancos ni billeteras | Fuera del diseño | ✅ |

Sin violaciones: no hace falta Complexity Tracking.

**Re-check post-diseño (Fase 1)**: el modelo de datos, los contratos y el quickstart no introducen
dependencias ni rutas públicas nuevas. Sigue ✅. Las reglas nuevas que propuso el diseño (fecha
mínima, monto máximo, mail de socio sin saltos de línea, advertencia por SMTP sin cifrar) fueron
confirmadas por el usuario y están en la spec (FR-003, FR-004, FR-022, FR-036), como pide el
Principio II.

## Project Structure

### Documentation (this feature)

```text
specs/001-registro-movimientos/
├── plan.md              # Este archivo
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/
│   ├── rutas-http.md
│   ├── cli.md
│   └── mail.md
├── checklists/
│   ├── requirements.md
│   └── security.md
└── tasks.md             # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── __init__.py
├── main.py              # FastAPI, RUTAS_PUBLICAS, middlewares, lifespan (arranca el programador)
├── config.py            # Carga .env; SECRET_KEY obligatoria; SMTP_*, TLS_*, DATABASE_URL
├── fechas.py            # ZONA, ahora(), hoy()
├── db.py                # Engine y sesión SQLAlchemy
├── modelos.py           # Movimiento, Operador, Socio, EnvioDiario
├── formato.py           # Monto "1.200"/"-1.200", fecha "DD/MM/AAAA"
├── clasificacion.py     # Tabla de palabras clave y proponer()
├── movimientos.py       # Validación y casos de uso: alta, modificación, baja, grilla
├── seguridad.py         # Hash de contraseñas, sesión/inactividad, solo_cifrado, chequeo de Origin
├── rutas/
│   ├── __init__.py
│   ├── login.py
│   └── movimientos.py
├── mail.py              # Armar y enviar el mail; CLI "python -m app.mail enviar"
├── programador.py       # APScheduler 17:00 y recuperación al arrancar
├── operadores.py        # CLI "python -m app.operadores alta"
├── socios.py            # CLI "python -m app.socios alta"
├── templates/           # base.html, login.html, definir.html, grilla.html, formulario.html, fragmentos
└── static/              # htmx.min.js, estilos.css

alembic/
├── env.py
└── versions/            # 0001_inicial.py

tests/
├── conftest.py          # App con SQLite en memoria, reloj fijo, FakeSMTP, operador logueado
├── unit/                # fechas, formato, clasificacion, validación de movimientos, armado del mail
└── integration/         # rutas HTTP, sesión, CLIs, programador y envío

.env.example
requirements.txt
alembic.ini
```

**Structure Decision**: proyecto único (`app/` + `tests/`) porque las páginas se renderizan en el
servidor; no hay frontend separado. Los módulos `app.operadores`, `app.socios`, `app.mail` y
`app.fechas` siguen los nombres que ya usa `AGENTS.md`.

## Complexity Tracking

Sin violaciones de la constitución.
