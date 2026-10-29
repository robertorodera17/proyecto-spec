# Data Model: Registro de movimientos con mail diario a los socios

Base SQLite, tablas creadas con Alembic. Nombres en castellano, como el dominio. Ver decisiones en
[research.md](research.md).

## Enumeraciones (en código, no tablas)

**TipoMovimiento**: `INGRESO`, `EGRESO` (FR-002).

**Clasificacion** (FR-011, FR-012), con su tipo y palabra clave:

| Clasificación         | Tipo    | Palabra clave |
|-----------------------|---------|---------------|
| `SUELDOS`             | EGRESO  | `sue`         |
| `IMPUESTOS-TASAS`     | EGRESO  | `imp`         |
| `VIATICOS`            | EGRESO  | `via`         |
| `PAGO-PROVEEDORES`    | EGRESO  | `prov`        |
| `TURISMO`             | EGRESO  | `tur`         |
| `SERVICIOS-PRESTADOS` | INGRESO | `serv`        |
| `ALQUILERES`          | INGRESO | `alq`         |
| `FINANCIEROS`         | INGRESO | `fin`         |

## Tabla `movimientos`

| Campo          | Tipo         | Reglas |
|----------------|--------------|--------|
| `id`           | INTEGER PK   | Autoincremental. Desempata el orden dentro de una fecha (FR-005, AC-91). |
| `descripcion`  | VARCHAR(200) | NOT NULL. Se guarda recortada; vacía tras recortar → "La descripción es obligatoria"; más de 200 caracteres → error en el campo (FR-034). |
| `tipo`         | VARCHAR(7)   | NOT NULL. `INGRESO` o `EGRESO` (FR-002). |
| `monto`        | INTEGER      | NOT NULL, ≠ 0. Negativo si `tipo = EGRESO`, positivo si `INGRESO` (RF-05/06). El texto ingresado debe cumplir `^[0-9]+$`, valor > 0 y ≤ 9.223.372.036.854.775.807 (FR-003, research R6). |
| `clasificacion`| VARCHAR(20)  | NOT NULL. Debe pertenecer al `tipo` (FR-015). |
| `fecha`        | DATE         | NOT NULL. Vacía → `fechas.hoy()`; inexistente → error; posterior a `fechas.hoy()` → error; anterior a 1900-01-01 → error (FR-004, research R5). |
| `eliminado`    | BOOLEAN      | NOT NULL, default `false`. Nunca se borra la fila (RF-12). |

Índice: `(eliminado, fecha DESC, id DESC)` para la grilla y el mail.
Restricción `CHECK (monto <> 0)` y `CHECK (tipo IN ('INGRESO','EGRESO'))`.

**Estados**: `vigente` (`eliminado = false`) → `eliminado` (`eliminado = true`), por baja confirmada
(FR-010). Sin vuelta atrás (FA-09). Modificar o dar de baja un movimiento eliminado → "El movimiento
fue eliminado" (FR-033).

## Tabla `operadores`

| Campo           | Tipo        | Reglas |
|-----------------|-------------|--------|
| `id`            | INTEGER PK  | |
| `sigla`         | VARCHAR     | NOT NULL, UNIQUE. Se guarda en mayúsculas (`upper()`), así la unicidad no distingue mayúsculas (FR-016). Sin validación de formato (FA-06). |
| `nombre`        | VARCHAR     | NOT NULL. |
| `mail`          | VARCHAR     | NOT NULL. Sin validación de formato (FA-06). |
| `password_hash` | VARCHAR(60) | NULL hasta el primer ingreso (RF-41). Hash bcrypt, costo 12 (FR-030). |

**Estados**: `sin contraseña` → `con contraseña` (una sola vez; FR-017). No hay baja ni
modificación (FA-08).

## Tabla `socios`

| Campo    | Tipo       | Reglas |
|----------|------------|--------|
| `id`     | INTEGER PK | |
| `nombre` | VARCHAR    | NOT NULL. |
| `mail`   | VARCHAR    | NOT NULL, no vacío (RF-23). Único sin distinguir mayúsculas: índice UNIQUE sobre `lower(mail)` (RF-49). Sin `\r` ni `\n` (research R10). |

## Tabla `envios_diarios`

| Campo        | Tipo     | Reglas |
|--------------|----------|--------|
| `fecha`      | DATE PK  | Día cuyo mail automático ya se inició. Se inserta **antes** de mandar; la PK impide un segundo envío automático (FR-025). El envío manual no inserta (FR-027). |
| `iniciado_en`| DATETIME | Hora de Argentina en que se inició (para el log y la auditoría). |

## Relaciones

No hay claves foráneas: los movimientos no guardan quién los cargó (FA-10) y el mail se arma con
todos los socios y los movimientos vigentes de la fecha.
