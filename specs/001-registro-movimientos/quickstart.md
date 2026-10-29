# Quickstart: validar la feature de punta a punta

Guía para comprobar que la app cumple la spec. El detalle de rutas, comandos y mail está en
[contracts/](contracts/); el de tablas, en [data-model.md](data-model.md).

## Requisitos previos

- Python 3.12 y `uv`.
- WSL o Linux. Para el modo red interna, un certificado y su clave (ver "Modo red interna").

## Preparación

```bash
uv venv .venv --python 3.12 && source .venv/bin/activate
uv pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(32))"   # pegar como SECRET_KEY en .env
alembic upgrade head
python -m app.operadores alta RO "Rocío" rocio@empresa.com
python -m app.socios alta "José" jose@empresa.com
```

## 1. Tests automáticos

```bash
pytest
```

Esperado: todo en verde. `pytest -k ac68` corre el test de un AC puntual; cada AC del PRD y cada
FR nuevo de Clarifications tiene al menos un test con su id en el nombre (SC-007).

## 2. Arranque y control de secretos

```bash
SECRET_KEY= uvicorn app.main:app       # Esperado: no arranca, mensaje sobre SECRET_KEY (AC-73)
uvicorn app.main:app --reload --host 0.0.0.0
git ls-files | grep -x .env            # Esperado: sin salida (AC-45)
```

## 3. Recorrido del operador (http://127.0.0.1:8000)

1. Ingresar `ro` → pide definir contraseña. Probar `secreta123` / `secreta124` → "Las contraseñas
   no coinciden" (AC-103). Definir `secreta123` dos veces → entra a la grilla (AC-35, AC-98).
2. "Agregar movimiento": fecha = hoy. Escribir "Sueldo marzo" con tipo Egreso → propone SUELDOS
   (AC-01). Monto `1.200` → error (AC-88); `1200` → guarda y la grilla muestra `-1.200` (AC-89).
3. Fecha de mañana → error en fecha (FR-004). Descripción de solo espacios → error (FR-034).
4. Doble click en la fila → monto `1200` sin signo (AC-69). Cambiar tipo a Ingreso → clasificación
   vacía; volver a Egreso → SUELDOS (AC-70, AC-71).
5. "Eliminar" → confirmar → desaparece de la grilla (AC-32); en la base la fila sigue con
   `eliminado = 1` (AC-33):
   `sqlite3 movimientos.db "select id, eliminado from movimientos"`.
6. "Cerrar sesión" → login; volver a `/movimientos` → login (AC-57).

## 4. Mail sin salir a internet

Terminal 1:

```bash
uvx --from aiosmtpd==1.4.6 aiosmtpd -n -l 127.0.0.1:1025
```

Terminal 2:

```bash
SMTP_HOST=127.0.0.1 SMTP_PORT=1025 SMTP_SEGURIDAD=ninguna SMTP_FROM=app@empresa.com \
  SMTP_USER= SMTP_PASSWORD= python -m app.mail enviar
```

Esperado en la terminal 1: un mensaje por socio, asunto `Movimientos del DD/MM/AAAA`, una sola parte
`text/plain`, la cantidad y una línea por movimiento vigente de hoy (contrato
[mail.md](contracts/mail.md)). Sin movimientos: "No hubo movimientos." (AC-62).

## 5. Modo red interna (FR-035)

```bash
# en .env: TLS_CERT=/ruta/cert.pem  TLS_KEY=/ruta/key.pem
uvicorn app.main:app --host 0.0.0.0 --ssl-certfile "$TLS_CERT" --ssl-keyfile "$TLS_KEY"
```

- Desde otra PC: `https://IP:8000/login` → login; la cookie de sesión tiene `Secure`.
- Arrancado sin TLS, desde otra PC: `http://IP:8000/login` → 403 "Usá la dirección https://…".
- El certificado lo emite el área de sistemas (o es autofirmado e instalado en las PCs de los
  operadores); renovarlo antes de su vencimiento y reiniciar uvicorn.
