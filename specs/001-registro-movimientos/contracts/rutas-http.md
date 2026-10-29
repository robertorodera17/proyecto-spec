# Contrato: rutas HTTP

Aplicación de páginas con Jinja2 + HTMX. Todas las respuestas son HTML. Los formularios usan
`application/x-www-form-urlencoded`.

## Reglas comunes

- **Públicas** (`RUTAS_PUBLICAS` en `app/main.py`): `GET /login`, `POST /login`,
  `POST /login/definir`, `GET /static/*`. Todo lo demás exige sesión (FR-019).
- **Sin sesión o vencida** en ruta protegida: navegación normal → `303 /login` (vencida:
  `/login?vencida=1`); pedido HTMX (`HX-Request: true`) → `200` con cabecera `HX-Redirect: /login…`.
- **Cada pedido autenticado** renueva el plazo de 60 minutos (FR-031).
- **POST** sin `Origin`/`Referer` del propio host → `403` (research R3).
- **HTTP sin cifrar desde un cliente que no es loopback** → `403` con "Usá la dirección https://…",
  sin login ni movimientos (FR-035).
- **Errores de validación**: `422` con el mismo formulario y el mensaje junto a cada campo inválido.

## Login

| Método y ruta | Entrada | Resultado |
|---|---|---|
| `GET /login` | `?vencida=1` opcional | Formulario de sigla. Con `vencida=1` muestra "Tu sesión venció por inactividad" (RF-34). |
| `POST /login` | `sigla` | Sigla inexistente (sin distinguir mayúsculas) → "No existe un operador con la sigla XX", sin pedir contraseña (RF-33). Operador sin contraseña → formulario de definir contraseña (RF-19). Con contraseña → formulario de contraseña. |
| `POST /login` | `sigla`, `password` | Correcta → sesión nueva y `303 /movimientos`. Incorrecta → "Sigla o contraseña incorrecta", sin sesión (RF-20). Sin límite de intentos (Clarifications). |
| `POST /login/definir` | `sigla`, `password`, `password2` | Solo si el operador no tiene contraseña; si ya tiene → rechazo y la contraseña no cambia (AC-52). Validaciones en orden: coinciden ("Las contraseñas no coinciden"), ≥ 8 caracteres, ≤ 72 bytes. Válida → guarda hash, inicia sesión, `303 /movimientos`. |
| `POST /logout` | — | Borra la sesión, `303 /login` (RF-32). |

## Movimientos

| Método y ruta | Entrada | Resultado |
|---|---|---|
| `GET /movimientos` | `?pagina=N` (default 1) | Grilla de vigentes, 30 por página, `fecha DESC, id DESC`, monto `1.200` / `-1.200`, fecha `DD/MM/AAAA`. Página fuera de rango → última página. Botón "Agregar movimiento". Doble click en fila → `GET /movimientos/{id}/editar` vía HTMX. |
| `GET /movimientos/nuevo` | — | Formulario de alta vacío, fecha = `hoy()`, tipo sin elegir, sin botón "Eliminar" (RF-09). |
| `GET /movimientos/clasificacion` | `tipo`; opcionales `descripcion` (alta) o `tipo_original` + `clasificacion_original` (modificación) | Fragmento HTMX: selector con las clasificaciones del tipo (FR-011). En el alta, con `descripcion`: la propuesta seleccionada, o vacío si no hay (FR-012..014). En la modificación: si `tipo == tipo_original` selecciona `clasificacion_original`; si no, vacío; nunca propone por descripción (FR-009, RF-15). |
| `POST /movimientos` | `descripcion`, `tipo`, `monto`, `clasificacion`, `fecha` | Válido → guarda y `303 /movimientos`. Inválido → `422` con errores por campo. |
| `GET /movimientos/{id}/editar` | — | Formulario de modificación con los datos, monto sin signo y botón "Eliminar". Movimiento eliminado o inexistente → `404`. El cambio de tipo pide el fragmento de clasificación con `tipo_original` y `clasificacion_original`, que vacía o recupera la clasificación (FR-009). |
| `POST /movimientos/{id}` | mismos campos que el alta | Mismas validaciones (FR-008). Eliminado → "El movimiento fue eliminado" (FR-033). Válido → `303 /movimientos`. |
| `POST /movimientos/{id}/eliminar` | — | La confirmación la pide el navegador (`hx-confirm`) antes de enviar (RF-28). Marca `eliminado = true`; ya eliminado → "El movimiento fue eliminado". `303 /movimientos`. |
