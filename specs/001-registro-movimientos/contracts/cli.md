# Contrato: comandos de consola

Todos leen `.env`. Salida a stdout en éxito y a stderr en error. Códigos: `0` éxito, `1` rechazo de
negocio, `2` uso incorrecto (argumentos).

## `python -m app.operadores alta SIGLA "Nombre" mail`

- Crea un operador sin contraseña; guarda la sigla en mayúsculas (FR-016).
- Sigla ya existente, sin distinguir mayúsculas → `Ya existe un operador con la sigla RO`, código 1
  (AC-34, AC-50).
- Éxito: `Operador RO creado. Define su contraseña en el primer ingreso.`

## `python -m app.socios alta "Nombre" mail`

- Crea un socio (FR-022).
- Mail vacío → `El socio necesita un mail`, código 1 (AC-41).
- Mail ya existente, sin distinguir mayúsculas → `Ya existe un socio con el mail …`, código 1
  (AC-59).
- Mail con salto de línea → `El mail no puede tener saltos de línea`, código 1 (research R10).

## `python -m app.mail enviar [--fecha AAAA-MM-DD]`

- Manda a cada socio el mail de la fecha (default: `hoy()` de Argentina) (FR-027).
- No inserta en `envios_diarios` (RF-54): no impide el automático de las 17:00.
- `--fecha` con formato inválido → mensaje de uso, código 2, sin mandar.
- Resumen al terminar: `Enviados 2 de 2 mails del 10/10/2026`; cada falla se loguea (RF-55) y el
  código es 1 si falló alguno.
