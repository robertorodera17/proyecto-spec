# Registro de Movimientos Constitution

## Core Principles

### I. Test-First (NO NEGOCIABLE)

- Todo cambio de comportamiento MUST empezar por un test que falla (rojo); recién después se escribe
  la implementación mínima que lo hace pasar (verde) y luego se refactoriza con los tests en verde.
- Ningún código de producción se mergea sin un test que lo ejercite y que se haya visto fallar antes
  de la implementación.
- Cada requerimiento (RF/RNF) y criterio de aceptación (AC) del PRD MUST tener al menos un test
  automatizado (pytest) que lo cite por su identificador.
- Un bug se corrige escribiendo primero el test que lo reproduce.

**Razón**: los tests escritos primero fijan el comportamiento esperado antes de que el código lo
condicione, y dan la red de seguridad para refactorizar sin miedo.

### II. Fuente de verdad y revisión humana

- El sistema MUST NOT inventar, completar ni inferir datos que no estén en su fuente de verdad (la
  base de datos y lo que carga el operador).
- Ante ambigüedad o falta de información, el sistema MUST derivar la decisión a una persona en lugar
  de elegir por su cuenta (por ejemplo: si ninguna palabra clave coincide, la clasificación queda
  vacía y la elige el operador).
- Los reportes y mails MUST reflejar exactamente los registros guardados; si un dato falta o falla,
  se informa el error, no se rellena.

**Razón**: los socios toman decisiones con estos datos; un dato inventado es peor que un dato
faltante señalado.

### III. Cero secretos en el código

- Contraseñas, API keys, credenciales SMTP y `SECRET_KEY` MUST NOT aparecer en el código, en los
  tests ni en ningún archivo versionado; se leen de `.env`, que no se versiona.
- `.env.example` documenta las variables con valores vacíos o ficticios.
- Si falta un secreto obligatorio, la aplicación MUST fallar al arrancar con un mensaje claro, sin
  usar valores por defecto.
- Las contraseñas de usuarios se guardan solo como hash bcrypt (costo ≥ 12).

**Razón**: un secreto en el repositorio queda expuesto para siempre en su historial.

## Restricciones técnicas

- Stack: Python 3.12, FastAPI, Jinja2 + HTMX (sin SPA), SQLite con SQLAlchemy 2.x y Alembic,
  APScheduler, `smtplib`, pytest. Cambiar una pieza del stack requiere enmendar esta sección.
- "Hoy" y toda hora de negocio se calculan en hora de Argentina (`app.fechas.hoy()`); se prohíbe
  `date.today()` y `datetime.now()` sin zona.
- Las bajas de movimientos son lógicas (campo "eliminado"); nunca se borran físicamente.
- Toda ruta exige sesión salvo las listadas en `RUTAS_PUBLICAS` (`app/main.py`).
- Fuera de alcance: integración con bancos o billeteras virtuales.

## Flujo de desarrollo y puertas de calidad

- Orden de trabajo por tarea: test rojo → implementación → test verde → refactor → commit.
- Antes de cada commit, `pytest` MUST pasar completo.
- Toda revisión de código verifica: tests escritos primero (Principio I), ningún dato inventado ni
  decisión ambigua tomada sin operador (Principio II), y ningún secreto en el diff (Principio III).
- La sección "Constitution Check" de cada `plan.md` MUST evaluar los tres principios; toda
  excepción se justifica por escrito en la tabla de complejidad del plan.

## Governance

- Esta constitución prevalece sobre cualquier otra práctica o guía del proyecto; `AGENTS.md` aporta
  la guía operativa diaria y no puede contradecirla.
- Enmiendas: se proponen por escrito con su motivo, se registran en el Sync Impact Report y se
  commitean junto con los ajustes que requieran en specs o planes vigentes.
- Versionado semántico: MAJOR al quitar o redefinir un principio; MINOR al agregar un principio o
  sección o ampliar su alcance; PATCH para aclaraciones de redacción.
- Cumplimiento: cada plan y cada revisión de código verifican los principios; un incumplimiento sin
  justificación bloquea el avance.

**Version**: 1.0.0 | **Ratified**: 2026-10-24 | **Last Amended**: 2026-10-24
