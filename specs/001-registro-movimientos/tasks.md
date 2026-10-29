---

description: "Tareas de implementación de 001-registro-movimientos"
---

# Tasks: Registro de movimientos con mail diario a los socios

**Input**: Design documents from `specs/001-registro-movimientos/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: obligatorios. La constitución (Principio I) exige test-first: en cada historia, las
tareas de tests van primero y **deben fallar** antes de implementar. Cada test lleva en su nombre
el AC del PRD o el FR que cubre (por ejemplo `test_ac68_alta_egreso_guarda_negativo`,
`test_fr033_modificar_eliminado_rechaza`) y en su docstring los RF/RNF del PRD que verifica (por
ejemplo `"""AC-68 (RF-01, RF-05)."""`), para que cada RF/RNF quede citado por su identificador
(Constitución, Principio I).

**Organization**: una fase por historia de usuario, en el orden de prioridad de la spec.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivo distinto, sin dependencias pendientes)
- **[Story]**: historia a la que pertenece (US1..US5)

## Path Conventions

Proyecto único: `app/`, `tests/`, `alembic/` en la raíz del repo (ver plan.md, Project Structure).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: estructura del proyecto y dependencias

- [X] T001 Crear la estructura de carpetas del plan: `app/`, `app/rutas/`, `app/templates/`, `app/static/`, `tests/unit/`, `tests/integration/`, con `app/__init__.py`, `app/rutas/__init__.py`, `tests/__init__.py` vacíos
- [X] T002 Crear `requirements.txt` con: `fastapi==0.115.*`, `uvicorn[standard]`, `jinja2`, `python-multipart`, `sqlalchemy>=2,<3`, `alembic`, `apscheduler>=3.10,<4`, `passlib[bcrypt]==1.7.4`, `bcrypt==4.0.1` (passlib 1.7.4 falla con bcrypt ≥ 4.1, research R1), `itsdangerous`, `python-dotenv`, `tzdata`, `pytest`, `httpx`; instalar con `uv pip install -r requirements.txt`
- [X] T003 [P] Crear `.gitignore` con `.env`, `*.db`, `.venv/`, `__pycache__/`, `.pytest_cache/`, y `.env.example` con las claves vacías `SECRET_KEY=`, `DATABASE_URL=sqlite:///movimientos.db`, `SMTP_HOST=`, `SMTP_PORT=587`, `SMTP_USER=`, `SMTP_PASSWORD=`, `SMTP_FROM=`, `SMTP_SEGURIDAD=starttls`, `TLS_CERT=`, `TLS_KEY=` (RNF-04)
- [X] T004 [P] Crear `pytest.ini` con `testpaths = tests` y `pythonpath = .`
- [X] T005 [P] Descargar htmx 2.0.x a `app/static/htmx.min.js` (archivo local, sin CDN: la red interna puede no tener internet) y crear `app/static/estilos.css` mínimo (tabla, errores en rojo junto al campo)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: hora de Argentina, configuración, base de datos, sesión y seguridad HTTP que usan todas
las historias

**⚠️ CRITICAL**: ninguna historia empieza hasta terminar esta fase

### Tests de la base (escribir primero, deben fallar)

- [X] T006 Crear `tests/conftest.py` con fixtures: `env_minimo` (monkeypatch de `SECRET_KEY` y `DATABASE_URL=sqlite://`), `app` (crea la app con SQLite en memoria y `StaticPool`, con `crear_app(iniciar_programador=False)`, corre `Base.metadata.create_all`), `reloj` (monkeypatch de `app.fechas.ahora` para fijar fecha y hora de Argentina, por ejemplo `reloj("2026-10-21 10:00")`), `cliente` (cliente de pruebas sin sesión, cabecera `Origin` propia en los POST), `cliente_logueado` (crea el operador `RO` con contraseña y deja la sesión iniciada), `fake_smtp` (doble de `smtplib.SMTP`/`SMTP_SSL` que guarda los mensajes y puede simular rechazo de una dirección o servidor caído)
- [X] T007 [P] Tests de `app.fechas` en `tests/unit/test_fechas.py`: `hoy()` devuelve 20/10/2026 cuando son las 01:30 UTC del 21/10/2026 (base de AC-97); `ahora()` es aware con zona `America/Argentina/Buenos_Aires`
- [X] T008 [P] Tests de `app.formato` en `tests/unit/test_formato.py`: `monto(1200)` → `1.200`, `monto(-1200)` → `-1.200`, `monto(-350)` → `-350`, `monto(1234567)` → `1.234.567`, `fecha(date(2026,10,21))` → `21/10/2026` (base de AC-83, AC-89, AC-87, AC-90)
- [X] T009 [P] Test de arranque en `tests/integration/test_arranque.py`: `test_ac73_sin_secret_key_no_arranca` (crear la app sin `SECRET_KEY` lanza error con mensaje que nombra `SECRET_KEY`); con la configuración del correo vacía la app arranca igual (research R11)
- [X] T010 [P] Tests de acceso y sesión en `tests/integration/test_sesion.py` usando una ruta protegida de prueba: `test_ac38_sin_sesion_redirige_login` (303 a `/login`, sin movimientos), pedido HTMX sin sesión → `HX-Redirect: /login`, `test_ac40_sesion_60_min_vencida` (redirige a `/login?vencida=1`), `test_ac55_sesion_59_min_sigue`, cada pedido renueva el plazo (RNF-03), las rutas de `RUTAS_PUBLICAS` responden sin sesión
- [X] T011 [P] Tests de seguridad HTTP en `tests/integration/test_seguridad_http.py`: `test_fr035_http_desde_otra_maquina_403` (cliente `192.168.0.10` por HTTP → 403 con "https://", sin formulario de login), `test_fr035_http_desde_loopback_ok` (`127.0.0.1` y `::1`), POST sin `Origin` ni `Referer` → 403 y POST con `Origin` ajeno → 403 (research R3), cookie de sesión con `HttpOnly` y `SameSite=strict`, y con `Secure` cuando `TLS_CERT` está configurado

### Implementación de la base

- [X] T012 [P] Implementar `app/fechas.py`: `ZONA = ZoneInfo("America/Argentina/Buenos_Aires")`, `ahora()` (aware, en `ZONA`), `hoy()` = `ahora().date()`; nada más del código usa `date.today()` ni `datetime.now()` sin zona (AGENTS.md)
- [X] T013 [P] Implementar `app/formato.py`: `monto(int) -> str` con punto de miles, sin decimales y signo menos; `fecha(date) -> str` en `DD/MM/AAAA`
- [X] T014 Implementar `app/config.py`: carga `.env` con `python-dotenv`; `Config` con `secret_key` (obligatoria: si falta o está vacía lanza `RuntimeError("Falta SECRET_KEY en .env")`), `database_url`, `smtp_*`, `tls_cert`, `tls_key`; los `SMTP_*` son opcionales para arrancar (research R11)
- [X] T015 Implementar `app/db.py`: engine desde `config.database_url`, `SessionLocal`, `Base` declarativa y dependencia `get_db()`; en SQLite `PRAGMA busy_timeout=5000`
- [X] T016 Implementar `app/modelos.py` según [data-model.md](data-model.md): `Movimiento` (`descripcion` VARCHAR(200) NOT NULL; `tipo` "`INGRESO` o `EGRESO`"; `monto` INTEGER NOT NULL con `CHECK (monto <> 0)`; `clasificacion` VARCHAR(20) NOT NULL; `fecha` DATE NOT NULL; `eliminado` BOOLEAN NOT NULL default false; índice `(eliminado, fecha DESC, id DESC)`), `Operador` (`sigla` UNIQUE "se guarda en mayúsculas", `nombre`, `mail`, `password_hash` VARCHAR(60) NULL "hasta el primer ingreso"), `Socio` (`nombre`, `mail` NOT NULL con índice UNIQUE sobre `lower(mail)`), `EnvioDiario` (`fecha` DATE PK, `iniciado_en` DATETIME); enums `TipoMovimiento`
- [X] T017 Inicializar Alembic (`alembic.ini`, `alembic/env.py` leyendo `config.database_url` y `Base.metadata`) y crear `alembic/versions/0001_inicial.py` con las 4 tablas, restricciones e índices de T016; verificar con `alembic upgrade head` sobre una base vacía
- [X] T018 Implementar `app/seguridad.py` (parte de sesión y HTTP): dependencia `operador_actual(request, db)` que lee `operador_id` y `ultima_actividad` de la sesión, vence con `>= 3600` s (redirige a `/login?vencida=1` o responde `HX-Redirect` si `HX-Request`), renueva `ultima_actividad` y devuelve el `Operador`; middleware `solo_cifrado` (HTTP + cliente no loopback → 403 "Usá la dirección https://…", research R4); middleware `chequeo_origen` (POST sin `Origin`/`Referer` del propio host → 403, research R3)
- [X] T019 Implementar `app/main.py`: `crear_app(iniciar_programador: bool = True)` que lee `Config` (falla sin `SECRET_KEY`), agrega `SessionMiddleware` (`same_site="strict"`, `https_only=bool(config.tls_cert)`), los middlewares de T018, `RUTAS_PUBLICAS = {"/login", "/login/definir", "/static"}`, monta `/static`, configura Jinja2 con autoescape y un `logging.Formatter` cuya hora sale de `fechas.ahora()` (research R9); `app = crear_app()` para uvicorn
- [X] T020 [P] Crear `app/templates/base.html` (carga `htmx.min.js` y `estilos.css`, bloque de contenido, botón "Cerrar sesión" visible solo con sesión) y `app/templates/error.html`
- [X] T021 Correr `pytest`: T007..T011 en verde

**Checkpoint**: la app arranca, protege todo salvo el login y sabe qué día es en Argentina

---

## Phase 3: User Story 1 - Cargar y consultar movimientos (Priority: P1) 🎯 MVP

**Goal**: el operador carga movimientos validados y los ve en la grilla paginada

**Independent Test**: con `cliente_logueado`, cargar movimientos válidos e inválidos y verificar qué
se guarda, con qué signo y cómo se ve en la grilla

### Tests for User Story 1 (escribir primero, deben fallar) ⚠️

- [X] T022 [P] [US1] Tests de validación en `tests/unit/test_validacion_movimiento.py` sobre `app.movimientos.validar(form, hoy)`: `test_ac19_*` (descripción, tipo, monto y clasificación vacíos, uno por vez, marcan ese campo); monto `0` (AC-24), `-500` (AC-25), `12abc` (AC-26), `12,5` (AC-82), `1.200` (AC-88), `9223372036854775807` aceptado y `9223372036854775808` rechazado (FR-003); signo: Egreso 500 → -500 (AC-22), Ingreso 500 → 500 (AC-23); fecha `2026-02-30` rechazada (AC-47), vacía → `hoy` (AC-46), mañana rechazada, hoy aceptada, `1899-12-31` rechazada y `1900-01-01` aceptada (FR-004); descripción `"   "` rechazada como vacía, `"  Sueldo  "` guardada como `"Sueldo"`, 200 caracteres aceptada y 201 rechazada (FR-034); Egreso con ALQUILERES rechazado (AC-09) e Ingreso con SUELDOS rechazado (AC-10), con error en clasificación (FR-015)
- [X] T023 [P] [US1] Tests HTTP de alta en `tests/integration/test_alta.py`: `test_ac68_alta_egreso_guarda_negativo` (POST `/movimientos` y lectura en la base); POST inválido → 422 con el error junto al campo; `test_ac27_agregar_muestra_formulario_vacio_con_hoy`; `test_ac20_fecha_por_defecto_hoy`; `test_ac97_fecha_por_defecto_argentina_con_servidor_utc` (reloj 22:30 del 20/10 en Argentina → `2026-10-20`); `test_ac21_tipos_ingreso_egreso`; `test_ac17_clasificaciones_ingreso` y `test_ac18_clasificaciones_egreso` sobre el fragmento `GET /movimientos/clasificacion?tipo=…`; el formulario de alta no tiene botón "Eliminar"
- [X] T024 [P] [US1] Tests HTTP de grilla en `tests/integration/test_grilla.py`: `test_ac11_grilla_muestra_campos`, `test_ac99_grilla_todas_las_fechas`, `test_ac83_monto_ingreso_1200` (`1.200`), `test_ac89_monto_egreso_1200` (`-1.200`), `test_ac84_orden_fecha_desc`, `test_ac85_paginas_de_30` (31 movimientos → 30 + 1), `test_ac91_misma_fecha_ultimo_cargado_arriba`, los eliminados no aparecen, `?pagina=99` muestra la última página (research R12), una descripción `<script>alert(1)</script>` aparece escapada (research R10)

### Implementation for User Story 1

- [X] T025 [P] [US1] Crear `app/clasificacion.py` con la tabla de [data-model.md](data-model.md) (clasificación, tipo, palabra clave) y `por_tipo(tipo) -> list[str]` en el orden de RF-13/RF-14; sin `proponer()` todavía (va en US4)
- [X] T026 [US1] Implementar en `app/movimientos.py` `validar(form, hoy) -> (datos | None, errores: dict[campo, mensaje])` con todas las reglas de T022 (monto con `^[0-9]+$`, > 0, ≤ 9.223.372.036.854.775.807; fecha ISO, `1900-01-01 <= fecha <= hoy`; descripción recortada, 1..200 caracteres; clasificación en `por_tipo(tipo)`); el signo se aplica según el tipo
- [X] T027 [US1] Implementar en `app/movimientos.py` `crear(db, datos)` y `pagina(db, numero) -> (filas, numero_real, total_paginas)` con `eliminado = false`, `ORDER BY fecha DESC, id DESC`, 30 por página y página fuera de rango → última
- [X] T028 [US1] Implementar `app/rutas/movimientos.py`: `GET /movimientos` (grilla), `GET /movimientos/nuevo` (formulario de alta, fecha = `fechas.hoy()`), `GET /movimientos/clasificacion` (fragmento con `por_tipo(tipo)`, sin propuesta), `POST /movimientos` (valida, guarda, `303 /movimientos`; si falla, 422 con el formulario), todas con `Depends(operador_actual)`; registrar el router en `app/main.py`
- [X] T029 [P] [US1] Crear `app/templates/grilla.html` (columnas descripción, monto con `formato.monto`, tipo, clasificación, fecha con `formato.fecha`; botón "Agregar movimiento"; navegación de páginas), `app/templates/formulario.html` (descripción, tipo con solo Ingreso/Egreso, monto, clasificación, fecha `type="date"`; errores por campo; el select de tipo pide el fragmento con `hx-get="/movimientos/clasificacion"`) y `app/templates/_clasificacion.html`
- [X] T030 [US1] Correr `pytest`: T022..T024 en verde; refactor con los tests en verde

**Checkpoint**: US1 completa y probada por sí sola (MVP de carga)

---

## Phase 4: User Story 2 - Acceso de operadores (Priority: P1)

**Goal**: alta de operadores por consola, primer ingreso con definición de contraseña, login,
cierre y vencimiento de sesión

**Independent Test**: dar de alta operadores por consola y recorrer primer ingreso, ingreso normal,
errores, cierre y vencimiento de sesión

### Tests for User Story 2 (escribir primero, deben fallar) ⚠️

- [X] T031 [P] [US2] Tests de contraseñas en `tests/unit/test_contrasenas.py` sobre `app.seguridad`: `test_ac53_7_caracteres_rechaza`, `test_ac98_8_caracteres_acepta`, `test_ac72_72_bytes_acepta`, `test_ac86_73_bytes_rechaza`, una contraseña de 36 caracteres con tilde (72+ bytes) se mide en bytes, los espacios de los extremos se conservan (research R1), `test_ac44_hash_no_es_texto_plano`, `test_ac95_hash_bcrypt_costo_12` (empieza con `$2b$12$`), verificación correcta e incorrecta
- [X] T032 [P] [US2] Tests de la CLI en `tests/integration/test_cli_operadores.py` (invocando `app.operadores.main(argv)`): `test_ac51_alta_sin_contrasena`, `test_ac96_alta_guarda_sigla_nombre_mail`, `test_ac34_sigla_repetida_rechaza`, `test_ac50_sigla_repetida_minusculas_rechaza`, `ro` se guarda como `RO`, códigos de salida 0/1/2 según [contracts/cli.md](contracts/cli.md)
- [X] T033 [P] [US2] Tests de login en `tests/integration/test_login.py`: `test_ac35_sin_contrasena_pide_definirla`, `test_ac103_contrasenas_no_coinciden`, `test_ac53`/`test_ac98` por HTTP, `test_ac52_no_redefine_contrasena_existente`, `test_ac54_sigla_inexistente_no_pide_contrasena` ("No existe un operador con la sigla XX"), `test_ac36_login_correcto_accede_grilla`, `test_ac37_contrasena_incorrecta_rechaza`, la sigla `ro` entra como `RO`, `test_clarif_intentos_ilimitados` (20 intentos fallidos y luego uno correcto entra), `test_ac39_operador_b_ve_movimiento_de_a`, `test_ac56_aviso_sesion_vencida`, `test_ac57_cerrar_sesion`
- [X] T034 [P] [US2] Test de secretos en `tests/integration/test_repo_sin_secretos.py`: `test_ac45_env_no_versionado` (`.env` está en `.gitignore` y no figura en `git ls-files`) y ningún archivo versionado tiene `SECRET_KEY=` o `SMTP_PASSWORD=` con valor

### Implementation for User Story 2

- [X] T035 [US2] Agregar a `app/seguridad.py` `validar_contrasena(p) -> str | None` (≥ 8 caracteres, ≤ 72 bytes UTF-8, sin recortar), `hashear(p)` y `verificar(p, h)` con `CryptContext(schemes=["bcrypt"], bcrypt__rounds=12)`
- [X] T036 [P] [US2] Implementar `app/operadores.py` con `main(argv)` y `if __name__ == "__main__"`: subcomando `alta SIGLA "Nombre" mail`, sigla en mayúsculas, rechazo de repetida con el mensaje de [contracts/cli.md](contracts/cli.md)
- [X] T037 [US2] Implementar `app/rutas/login.py` según [contracts/rutas-http.md](contracts/rutas-http.md): `GET /login` (aviso con `?vencida=1`), `POST /login` (paso sigla → definir o contraseña; paso contraseña → sesión con `operador_id` y `ultima_actividad`, `303 /movimientos`), `POST /login/definir` (solo sin contraseña previa; valida coincidencia, mínimo y máximo en ese orden), `POST /logout` (limpia la sesión, `303 /login`); registrar el router
- [X] T038 [P] [US2] Crear `app/templates/login.html` (sigla, mensaje de sesión vencida y de sigla inexistente), `app/templates/contrasena.html` y `app/templates/definir.html` (contraseña dos veces y errores)
- [X] T039 [US2] Correr `pytest`: T031..T034 en verde; refactor

**Checkpoint**: US1 + US2 forman una app usable de punta a punta

---

## Phase 5: User Story 3 - Mail diario a los socios (Priority: P2)

**Goal**: alta de socios por consola, mail de las 17:00 una sola vez por día, recuperación al
arrancar y envío manual

**Independent Test**: con socios y movimientos de hoy, ayer y eliminados, disparar el envío contra
`fake_smtp` y revisar destinatarios, asunto, cuerpo y la tabla `envios_diarios`

### Tests for User Story 3 (escribir primero, deben fallar) ⚠️

- [X] T040 [P] [US3] Tests de armado en `tests/unit/test_mail_armado.py` sobre `app.mail.armar(socio, fecha, movimientos)`: `test_ac74_asunto` ("Movimientos del 21/10/2026"), `test_ac75_cantidad`, `test_ac43_campos_por_movimiento`, `test_ac87_monto_ingreso` (`1.200`), `test_ac90_monto_egreso` (`-1.200`), `test_ac101_una_parte_text_plain`, `test_ac102_una_linea_por_movimiento`, `test_ac62_sin_movimientos` ("No hubo movimientos."), destinatario único, formato exacto de [contracts/mail.md](contracts/mail.md)
- [X] T041 [P] [US3] Tests de la CLI de socios en `tests/integration/test_cli_socios.py`: `test_ac58_alta_socio`, `test_ac41_socio_sin_mail_rechaza`, `test_ac59_mail_repetido_mayusculas_rechaza`, `test_fr022_mail_con_salto_de_linea_rechaza`
- [X] T042 [P] [US3] Tests de envío en `tests/integration/test_mail_envio.py` con `fake_smtp` y `caplog`: `test_ac42_solo_vigentes_de_hoy`, `test_ac60_un_mail_por_socio`, `test_ac61_rechazo_no_frena_al_resto` (y el rechazo queda en el log), `test_ac78_servidor_caido_al_log`, configuración incompleta al log (RF-55), `test_fr036_sin_cifrado_a_otra_maquina_advierte` (y manda igual), sin socios registra el día y loguea "No hay socios", ningún log contiene `SMTP_PASSWORD` ni `SECRET_KEY` (research R9)
- [X] T043 [P] [US3] Tests del envío manual en `tests/integration/test_mail_cli.py` (invocando `app.mail.main(argv)`): `test_ac66_manual_con_fecha` (asunto "Movimientos del 10/10/2026" y movimientos de ese día), `test_ac77_manual_no_registra_dia` (después el automático manda igual), `--fecha 2026-13-01` → código 2 sin mandar, resumen "Enviados N de M"
- [X] T044 [P] [US3] Tests del programador en `tests/integration/test_programador.py` con `reloj`: el trabajo queda programado a las 17:00 de `America/Argentina/Buenos_Aires`; `test_ac63_arranca_1730_manda`; `test_ac64_arranca_1800_no_manda`; `test_ac76_log_con_comando_manual` (`python -m app.mail enviar --fecha 2026-10-21`); `test_ac65_reinicio_no_repite`; `test_ac79_falla_no_reintenta` (sigue corriendo y reinicio a las 17:30); dos llamadas simultáneas a `enviar_automatico` mandan una sola vez (PK de `envios_diarios`); un test verifica que `crear_app(iniciar_programador=False)` no crea ningún trabajo programado

### Implementation for User Story 3

- [X] T045 [P] [US3] Implementar `app/socios.py` con `main(argv)`: `alta "Nombre" mail`; rechaza mail vacío, repetido (comparando en minúsculas) o con `\r`/`\n`, con los mensajes de [contracts/cli.md](contracts/cli.md)
- [X] T046 [US3] Implementar en `app/mail.py` `armar(socio, fecha, movimientos) -> EmailMessage` (texto plano según [contracts/mail.md](contracts/mail.md), con `formato.monto` y `formato.fecha`) y `movimientos_del_dia(db, fecha)` (vigentes, orden de la grilla)
- [X] T047 [US3] Implementar en `app/mail.py` `enviar_dia(db, fecha) -> (enviados, total)`: abre la conexión según `SMTP_SEGURIDAD` (`starttls` | `ssl` | `ninguna`), advierte en el log si es `ninguna` y el host no es loopback (FR-036), un `try` por socio que loguea el error y sigue (RF-55, RF-36); y `enviar_automatico(db, fecha)`: inserta `EnvioDiario(fecha, iniciado_en=fechas.ahora())` y hace commit **antes** de mandar; si la fecha ya existe, no hace nada (RF-39); sin socios loguea y no manda; sin reintentos (RF-56)
- [X] T048 [US3] Agregar a `app/mail.py` `main(argv)` y `if __name__ == "__main__"`: `enviar [--fecha AAAA-MM-DD]` llama a `enviar_dia` sin registrar el día (RF-54); fecha inválida → código 2
- [X] T049 [US3] Implementar `app/programador.py`: `iniciar(sesion_factory)` crea `BackgroundScheduler(timezone=fechas.ZONA)` con `CronTrigger(hour=17, minute=0)` que llama a `enviar_automatico(hoy)`, y `recuperar_al_arrancar(db)` (17:00 ≤ ahora < 18:00 y sin fila → manda; ahora ≥ 18:00 y sin fila → loguea el comando manual); conectarlo al `lifespan` de `app/main.py`: si `iniciar_programador` es verdadero, llama a `recuperar_al_arrancar` y arranca el programador, y lo apaga al cerrar; los tests crean la app con `iniciar_programador=False` y prueban `iniciar` y `recuperar_al_arrancar` llamándolos directo con `reloj`
- [X] T050 [US3] Correr `pytest`: T040..T044 en verde; refactor

**Checkpoint**: US3 manda el mail correcto una vez por día y se puede reenviar a mano

---

## Phase 6: User Story 4 - Clasificación propuesta por palabra clave (Priority: P2)

**Goal**: al crear, la clasificación se propone según la descripción y el tipo; sin propuesta,
decide el operador

**Independent Test**: escribir las descripciones de AC-01..08 y AC-12..16 con cada tipo y verificar
la propuesta o su ausencia

### Tests for User Story 4 (escribir primero, deben fallar) ⚠️

- [X] T051 [P] [US4] Tests de `proponer(descripcion, tipo)` en `tests/unit/test_clasificacion.py`: `test_ac01`..`test_ac08` (una por descripción del PRD), `test_ac12_compra_de_cafe_sin_propuesta`, `test_ac13_dos_clasificaciones_sin_propuesta`, `test_ac14_mayusculas_sin_tilde`, `test_ac15_factura_no_coincide_con_tur`, `test_ac16_alquiler_en_egreso_sin_propuesta`, `test_ac81_misma_clave_repetida_cuenta_una`, tildes en la descripción ("Viáticos") coinciden
- [X] T052 [P] [US4] Tests HTTP en `tests/integration/test_clasificacion_http.py` sobre `GET /movimientos/clasificacion?descripcion=…&tipo=…`: la propuesta viene seleccionada; sin propuesta el selector queda vacío y el alta sin clasificación se rechaza (AC-12 por HTTP); `test_ac67_nueva_descripcion_reemplaza_eleccion_manual`; `test_ac92_descripcion_sin_propuesta_vacia_clasificacion`; `test_ac80_propuesta_menos_de_2s_p95` (100 descripciones distintas, al menos 95 bajo 2 s)

### Implementation for User Story 4

- [X] T053 [US4] Agregar a `app/clasificacion.py` `proponer(descripcion, tipo) -> str | None`: normaliza con `unicodedata.normalize("NFD")`, quita diacríticos, pasa a minúsculas, separa con `re.findall(r"\w+")`, coincide si la palabra empieza con la clave del tipo; 1 clasificación distinta → la devuelve, 0 o más de 1 → `None` (research R7)
- [X] T054 [US4] Hacer que `GET /movimientos/clasificacion` en `app/rutas/movimientos.py` use `proponer()` cuando recibe `descripcion` (solo en el alta) y en `app/templates/formulario.html` disparar el fragmento desde descripción (`hx-trigger="input changed delay:300ms"`) y desde tipo, con `hx-include` de ambos campos
- [X] T055 [US4] Correr `pytest`: T051..T052 en verde; refactor

**Checkpoint**: US4 propone la clasificación sin romper el alta manual de US1

---

## Phase 7: User Story 5 - Modificar y dar de baja movimientos (Priority: P3)

**Goal**: doble click abre la modificación con las mismas validaciones; "Eliminar" con
confirmación hace la baja lógica

**Independent Test**: cargar movimientos, modificarlos y eliminarlos, y verificar grilla y base

### Tests for User Story 5 (escribir primero, deben fallar) ⚠️

- [X] T056 [P] [US5] Tests en `tests/integration/test_modificacion.py`: `test_ac28_doble_click_abre_formulario` (la fila tiene `hx-trigger="dblclick"` hacia `/movimientos/{id}/editar` y esa ruta trae los datos), `test_ac69_monto_sin_signo`, `test_ac29_cambia_descripcion`, `test_ac48_cambia_fecha`, `test_ac93_egreso_a_ingreso`, `test_ac94_cambia_monto_egreso`, `test_ac30_clasificacion_de_otro_tipo_rechaza`, `test_ac31_monto_cero_rechaza`, `test_ac100_monto_decimal_rechaza`, fecha futura y descripción de 201 caracteres rechazadas también al modificar (FR-004, FR-034), `test_ac70_cambio_de_tipo_vacia_clasificacion` y `test_ac71_volver_al_tipo_original_recupera` (sobre el fragmento con `tipo_original` y `clasificacion_original`), la modificación no propone clasificación por descripción (RF-15), `test_fr033_ultimo_que_guarda_gana`, `test_fr033_modificar_eliminado_rechaza` ("El movimiento fue eliminado"), editar un eliminado → 404
- [X] T057 [P] [US5] Tests en `tests/integration/test_baja.py`: `test_ac32_eliminar_confirmado_sale_de_la_grilla`, `test_ac33_baja_logica_conserva_fila`, `test_ac49_cancelar_no_cambia_nada` (el botón tiene `hx-confirm` y sin POST el movimiento sigue igual), `test_fr033_eliminar_ya_eliminado_rechaza`

### Implementation for User Story 5

- [X] T058 [US5] Agregar a `app/movimientos.py` `modificar(db, id, datos)` y `eliminar(db, id)`: con un único `UPDATE … WHERE eliminado = false`; si no afecta filas, distinguen inexistente de eliminado ("El movimiento fue eliminado"); gana el último que guarda; la baja marca `eliminado = true`, nunca `DELETE` (RF-12, research R13)
- [X] T059 [US5] Agregar a `app/rutas/movimientos.py` `GET /movimientos/{id}/editar` (404 si no existe o está eliminado; monto en valor absoluto), `POST /movimientos/{id}` (mismo `validar()` que el alta) y `POST /movimientos/{id}/eliminar`; extender `GET /movimientos/clasificacion` con `tipo_original` y `clasificacion_original` (mismo tipo → selecciona la original; otro tipo → vacío; sin propuesta por descripción), según [contracts/rutas-http.md](contracts/rutas-http.md)
- [X] T060 [US5] En `app/templates/grilla.html` agregar `hx-get` + `hx-trigger="dblclick"` en cada fila; en `app/templates/formulario.html` el modo modificación con botón "Eliminar" (`hx-post` a `/movimientos/{id}/eliminar` con `hx-confirm="¿Eliminar este movimiento?"`) y el fragmento de clasificación con `tipo_original`/`clasificacion_original`
- [X] T061 [US5] Correr `pytest`: T056..T057 en verde; refactor

**Checkpoint**: las cinco historias funcionan y se prueban por separado

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: trazabilidad, documentación y validación final

- [X] T062 Test de trazabilidad en `tests/test_trazabilidad.py` (SC-007, Constitución Principio I): lee de `PRD.md` todos los `AC-NN`, `RF-NN` y `RNF-NN`, y de `spec.md` los FR nuevos de Clarifications (FR-003 ampliado, FR-004, FR-022, FR-033..036); recorre los tests con `ast` y verifica que cada AC y FR aparece en el nombre de al menos un test (`test_acNN_…` / `test_frNNN_…`) y que cada RF/RNF aparece en el docstring de al menos un test; el mensaje de falla lista los ids faltantes; corregir los que falten
- [X] T063 [P] Actualizar `AGENTS.md`: `bcrypt==4.0.1` fijado y por qué; modo red interna con `TLS_CERT`/`TLS_KEY`; corregir la referencia de secretos de RNF-02 a RNF-04
- [X] T064 [P] Llevar a `PRD.md` las decisiones nuevas de la spec (Clarifications: intentos ilimitados, concurrencia, fecha futura y mínima, reglas de descripción, HTTPS, monto máximo, mail de socio sin saltos de línea, advertencia por SMTP sin cifrar) como RF y AC nuevos, y quitar del encabezado de `spec.md` la excepción "salvo en las decisiones de la sección Clarifications"
- [X] T065 Revisar el código contra la constitución: ningún `date.today()`/`datetime.now()` sin zona (`grep -rn "date.today\|datetime.now()" app/`), ningún `DELETE` de movimientos, ninguna ruta pública fuera de `RUTAS_PUBLICAS`, ningún secreto en el repo
- [X] T066 Validación manual con [quickstart.md](quickstart.md): secciones 2 a 5, incluido el mail contra `aiosmtpd` y el modo HTTPS
- [X] T067 Correr `pytest` completo antes del commit final (constitución, Flujo de desarrollo)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias
- **Foundational (Phase 2)**: depende de Setup; bloquea todas las historias
- **US1..US5 (Phases 3–7)**: dependen de Foundational
- **Polish (Phase 8)**: depende de las historias que se quieran entregar

### User Story Dependencies

- **US1 (P1)**: solo Foundational. Sus tests usan `cliente_logueado`, que crea la sesión sin
  pasar por la pantalla de login (que es US2).
- **US2 (P1)**: solo Foundational. Agrega el login real que usan las demás en producción.
- **US3 (P2)**: solo Foundational. Sus tests cargan los movimientos directo en la base.
- **US4 (P2)**: depende de US1 (amplía el fragmento de clasificación y el formulario de alta).
- **US5 (P3)**: depende de US1 (reusa `validar()`, la grilla y el formulario).

### Within Each User Story

- Tests primero y en rojo → modelos/lógica → rutas → templates → `pytest` en verde → refactor
- Commit al cerrar cada historia, con `pytest` completo en verde

### Parallel Opportunities

- Setup: T003, T004 y T005
- Foundational: los tests T007..T011; luego T012 y T013, y T020
- Una vez terminado Foundational, US1, US2 y US3 pueden avanzar en paralelo; US4 y US5 después de US1
- En cada historia, todas las tareas de tests marcadas [P]

---

## Parallel Example: User Story 3

```bash
# Tests de US3 juntos (archivos distintos):
Task: "Tests de armado en tests/unit/test_mail_armado.py"
Task: "Tests de la CLI de socios en tests/integration/test_cli_socios.py"
Task: "Tests de envío en tests/integration/test_mail_envio.py"
Task: "Tests del envío manual en tests/integration/test_mail_cli.py"
Task: "Tests del programador en tests/integration/test_programador.py"

# Luego, en paralelo con la lógica del mail:
Task: "Implementar app/socios.py"
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Phase 1 y Phase 2
2. Phase 3 (US1): carga validada y grilla
3. Phase 4 (US2): login real; sin esto la app no se puede usar fuera de los tests
4. **STOP and VALIDATE**: quickstart secciones 2 y 3

### Incremental Delivery

1. Setup + Foundational
2. US1 + US2 → MVP usable por el operador
3. US3 → los socios reciben el mail (métrica de éxito del PRD)
4. US4 → carga más rápida con clasificación propuesta
5. US5 → corrección y baja de errores de carga

---

## Notes

- Los AC-09/AC-10 figuran en US4 en la spec, pero se prueban en US1 (T022) porque la validación de
  clasificación por tipo es parte de guardar cualquier movimiento; US4 solo agrega la propuesta.
- El cambio de clasificación al cambiar el tipo en la modificación (AC-70/71) se resuelve en el
  servidor (T059) para poder probarlo con pytest; el contrato de rutas ya lo define así.
- [P] = archivos distintos, sin dependencias pendientes
- Verificar que cada test falla antes de implementar (Principio I)
