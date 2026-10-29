# Research: Registro de movimientos con mail diario a los socios

Fase 0 de `/speckit-plan`. El stack ya está fijado por la constitución (Restricciones técnicas) y
`AGENTS.md`; acá se resuelven las decisiones técnicas que la spec deja abiertas y los ítems de
`checklists/security.md` que se pueden cerrar como decisión de diseño sin cambiar comportamiento
visible. Lo que sí cambia comportamiento visible se consultó con el usuario y quedó en la spec.

## R1. Hash de contraseñas: passlib + bcrypt fijado en 4.0.1

- **Decision**: `passlib[bcrypt]==1.7.4` con `bcrypt==4.0.1`, esquema bcrypt con `rounds=12`. El
  largo se valida antes de hashear: mínimo 8 caracteres (`len(str)`), máximo 72 bytes
  (`len(str.encode("utf-8"))`); los espacios de la contraseña se conservan (no se recorta).
- **Rationale**: passlib 1.7.4 no se mantiene y falla con `bcrypt>=4.1` (lee `bcrypt.__about__`) y
  con `bcrypt>=5` (su autodiagnóstico hashea una clave de más de 72 bytes, que bcrypt 5 rechaza con
  `ValueError`). `bcrypt==4.0.1` es la última versión compatible. Validar los 72 bytes antes evita
  que bcrypt trunque en silencio (RF-48, RF-62). No recortar la contraseña sigue el Principio II: no
  se modifica lo que escribió el operador (cierra CHK002 y CHK003).
- **Alternatives considered**: `bcrypt` directo sin passlib (funciona, pero `AGENTS.md` fija
  passlib); argon2 (no cumple RNF-02, que pide bcrypt).

## R2. Sesión: cookie firmada con última actividad

- **Decision**: `SessionMiddleware` de Starlette (firma con `itsdangerous` y `SECRET_KEY`). La sesión
  guarda `operador_id` y `ultima_actividad` (epoch UTC). Una dependencia `operador_actual` corre en
  cada ruta protegida: si `ahora - ultima_actividad >= 3600 s`, limpia la sesión y redirige al login
  con `?vencida=1`; si no, renueva `ultima_actividad`. Cookie `HttpOnly`, `SameSite=Strict`, y
  `Secure` cuando la app corre con HTTPS. Para pedidos HTMX vencidos responde `HX-Redirect: /login`
  en lugar de un 303, para que redirija la página entera (cierra CHK013).
- **Rationale**: no hay estado de sesión en el servidor que mantener (una sola instancia, pocos
  operadores). El límite `>=` cumple AC-40 (60 min justos ya vencida) y AC-55 (59 min sigue).
- **Consecuencias aceptadas**: un operador puede tener varias sesiones a la vez (CHK008); cerrar
  sesión borra la cookie de ese navegador pero no invalida copias de la cookie (CHK009); cambiar
  `SECRET_KEY` invalida todas las sesiones (CHK011). No hay tiempo máximo con actividad continua
  (CHK010). Ninguno contradice la spec.
- **Alternatives considered**: sesiones en tabla (permiten invalidar en servidor, pero agregan
  tabla y limpieza sin requisito que lo pida).

## R3. Protección contra pedidos de otro sitio (CSRF)

- **Decision**: cookie `SameSite=Strict` más un chequeo en middleware: todo `POST` debe traer
  cabecera `Origin` (o, si falta, `Referer`) igual al host propio; si no, 403. Sin tokens en
  formularios.
- **Rationale**: cubre CHK012 sin tocar cada formulario; los navegadores actuales mandan `Origin` en
  `POST`. Con `SameSite=Strict` la cookie ni siquiera viaja en pedidos de otro sitio.
- **Alternatives considered**: token CSRF por formulario (más código en cada template y en HTMX, sin
  beneficio extra en este contexto).

## R4. Conexión cifrada (FR-035)

- **Decision**: dos modos de arranque.
  - **Local** (desarrollo, WSL): `uvicorn ... --host 0.0.0.0` en HTTP, como dice `AGENTS.md`.
  - **Red interna**: `uvicorn ... --host 0.0.0.0 --ssl-certfile ... --ssl-keyfile ...`; rutas de
    certificado en `.env` (`TLS_CERT`, `TLS_KEY`), certificado emitido por la empresa o
    autofirmado e instalado en las PCs de los operadores.
  - Middleware `solo_cifrado`: si el pedido llega por HTTP y el cliente no es loopback
    (`127.0.0.1`, `::1`), responde 403 con el texto "Usá la dirección https://…" y no muestra login
    ni movimientos.
- **Rationale**: con el reenvío de localhost de WSL2, el navegador de Windows llega como `127.0.0.1`,
  así que "la propia máquina" incluye Windows → WSL (cierra CHK014). 403 en vez de redirección:
  uvicorn escucha un solo puerto, no hay un HTTPS al cual redirigir en el mismo puerto (CHK015). El
  origen y la renovación del certificado quedan como dependencia operativa en `quickstart.md`
  (CHK016).
- **Riesgo**: si se usa el modo "mirrored" de red de WSL, los clientes de la red pueden aparecer con
  su IP real (correcto) o, detrás de un proxy, como loopback (incorrecto). No se usa proxy.
- **Alternatives considered**: proxy inverso (Caddy/nginx) con TLS (otra pieza a instalar y operar);
  redirigir HTTP→HTTPS (requiere dos puertos).

## R5. Fechas y hora de Argentina

- **Decision**: `app/fechas.py` con `ZONA = ZoneInfo("America/Argentina/Buenos_Aires")`,
  `ahora() -> datetime` aware y `hoy() -> date`. Todo el código de negocio llama a estas funciones;
  los tests las reemplazan con `monkeypatch`. El formulario usa `<input type="date">` (envía
  `AAAA-MM-DD`); el servidor parsea solo ISO y muestra `DD/MM/AAAA`. Fecha mínima aceptada:
  1900-01-01, confirmada y llevada a la spec (FR-004) (CHK026).
- **Rationale**: Argentina no tiene horario de verano; una sola zona fija alcanza. `tzdata` como
  dependencia por si el sistema no trae la base de zonas (Windows/contenedores mínimos). El formato
  ISO lo produce el propio control de fecha del navegador (cierra CHK023).
- **Alternatives considered**: `freezegun` (dependencia extra; monkeypatch alcanza porque hay un
  solo punto de entrada a la hora).

## R6. Monto

- **Decision**: se valida el texto con `^[0-9]+$`, luego `int(...) > 0`. Máximo técnico
  9.223.372.036.854.775.807 (entero de 64 bits de SQLite); un monto mayor se rechaza con error en el
  campo monto; confirmado y llevado a la spec (FR-003) (CHK024).
- **Rationale**: el PRD dice "sin monto máximo", pero SQLite no guarda enteros mayores a 64 bits;
  rechazar es mejor que guardar un valor distinto (Principio II).

## R7. Clasificación por palabra clave

- **Decision**: función pura `proponer(descripcion, tipo) -> Clasificacion | None` en
  `app/clasificacion.py`. Normaliza con `unicodedata.normalize("NFD")`, quita marcas diacríticas y
  pasa a minúsculas; separa palabras con `re.findall(r"\w+")`; una palabra coincide si
  `startswith(clave)`. Junta las clasificaciones distintas encontradas: 1 → la propone; 0 o >1 →
  `None`. La propuesta se pide al servidor con HTMX (`hx-trigger="input changed delay:300ms"`).
- **Rationale**: cumple RF-15/16 y AC-01..16, AC-81; determinista y testeable sin red. Un pedido
  local cuesta milisegundos: RNF-01 (2 s p95) holgado.

## R8. Mail diario y programador

- **Decision**: `APScheduler` 3.x `BackgroundScheduler(timezone=ZONA)` con
  `CronTrigger(hour=17, minute=0)`, arrancado en el `lifespan` de FastAPI. Al arrancar, si
  `17:00 <= ahora < 18:00` y no hay fila en `envios_diarios` para hoy, envía; si `ahora >= 18:00` y
  no hay fila, loguea `python -m app.mail enviar --fecha AAAA-MM-DD`. El envío automático primero
  inserta la fila (`fecha` es clave primaria: un segundo intento falla por unicidad) y después
  manda. `smtplib` con `starttls`/`ssl`/`ninguna` según `SMTP_SEGURIDAD`; `EmailMessage` de una sola
  parte `text/plain; charset=utf-8`. Un `try` por socio: un rechazo se loguea y sigue con el
  siguiente.
- **Casos límite resueltos** (CHK032..034):
  - Sin socios dados de alta: se registra el día y se loguea "No hay socios: no se mandó el mail".
  - Envío manual con `--fecha` inválida: la CLI termina con error y código 2, sin mandar. Fecha
    futura: se acepta (el mail dirá "No hubo movimientos"); no hay requisito que lo prohíba.
  - Manual y automático al mismo tiempo: pueden salir dos mails ese día; es consecuencia aceptada
    de RF-54 (el manual siempre manda).
- **Cifrado con el servidor de correo** (CHK017): `SMTP_SEGURIDAD=ninguna` queda solo para el
  servidor de prueba local; con un host que no sea loopback y `ninguna`, se loguea una advertencia.
  No se bloquea; confirmado y llevado a la spec (FR-036).
- **Alternatives considered**: cron del sistema (no funciona igual en WSL/Windows y separa la lógica
  de la app); reintentos automáticos (prohibidos por RF-56).

## R9. Logs

- **Decision**: `logging` estándar con un `Formatter` cuya hora sale de `fechas.ahora()`. Nunca se
  loguean contraseñas, `SECRET_KEY` ni `SMTP_PASSWORD`; los errores SMTP se loguean con el mensaje
  de la excepción y la dirección del socio (cierra CHK018).

## R10. Salida segura en grilla y mail

- **Decision**: Jinja2 con autoescape activado: una descripción con `<script>` se muestra como texto
  (CHK019). En el mail, el asunto es fijo y las direcciones se pasan por `email.headerregistry`
  (`EmailMessage["To"] = ...`), que rechaza saltos de línea; además el alta de socio rechaza mails
  con saltos de línea (`\r`, `\n`); confirmado y llevado a la spec (FR-022) (CHK020).

## R11. Configuración y secretos

- **Decision**: `python-dotenv` carga `.env` al importar `app/config.py`. Obligatoria al arrancar:
  `SECRET_KEY` (RF-57). El correo (`SMTP_*`) no es obligatorio para arrancar: si falta, el envío
  falla con "configuración incompleta" en el log (RF-55) (cierra CHK021). `.env` en `.gitignore`;
  `.env.example` con valores vacíos.

## R12. Grilla y paginación

- **Decision**: `ORDER BY fecha DESC, id DESC`, `LIMIT 30 OFFSET (pagina-1)*30`. Una página fuera de
  rango muestra la última página existente (o la grilla vacía si no hay movimientos) (CHK030).

## R13. Concurrencia (FR-033)

- **Decision**: sin control de versión: gana el último que guarda. La modificación y la baja son un
  único `UPDATE movimientos SET … WHERE id = ? AND eliminado = false`; si no afecta ninguna fila, se
  relee el movimiento para distinguir "inexistente" (404) de "eliminado" (409, "El movimiento fue
  eliminado").
- **Rationale**: una sola sentencia es atómica en SQLite, así que no hay ventana entre comprobar y
  escribir. Reemplaza la idea inicial de `BEGIN IMMEDIATE`, que exigía configurar a mano el manejo de
  transacciones del driver de SQLite sin ninguna ventaja.

## R14. Tests (Principio I)

- **Decision**: `pytest` + `httpx` (cliente de pruebas de FastAPI). Base SQLite en memoria por test
  con `StaticPool`. SMTP de prueba: un doble en memoria (`FakeSMTP`) inyectado por monkeypatch en los
  tests unitarios, y `aiosmtpd` solo en la validación manual del `quickstart.md`. Cada test lleva en
  su nombre o docstring el AC o FR que cubre (`test_ac68_alta_egreso_guarda_negativo`). Las reglas
  nuevas de Clarifications (FR-004 ampliado, FR-033..035) se cubren con tests nombrados por FR, ya
  que no tienen AC en el PRD (CHK036).
