# Feature Specification: Registro de movimientos con mail diario a los socios

**Feature Branch**: `001-registro-movimientos` (no se creó rama; el trabajo sigue en `master`)

**Created**: 2026-10-24

**Status**: Draft

**Input**: User description: "a partir de PRD.md"

**Fuente**: `PRD.md` (PRD-002). Esta spec resume el PRD. Las decisiones de la sección Clarifications
ya se llevaron al PRD como RF-70..78, RNF-05 y AC-104..115. Cada requisito cita su RF/RNF de origen
y cada escenario su AC. Los criterios de aceptación AC-01..AC-115 del PRD forman parte de esta spec
por referencia y son la lista completa a cubrir con tests (Constitución, Principio I). Si esta spec y
el PRD difieren, manda el PRD hasta que se corrija la diferencia.

## Clarifications

### Session 2026-10-24

- Q: ¿Qué hace el sistema ante varios intentos fallidos seguidos de contraseña para una misma
  sigla? → A: Nada especial: intentos ilimitados, sin bloqueo ni demora (riesgo aceptado).
- Q: ¿Qué pasa si dos operadores modifican el mismo movimiento, o uno lo elimina mientras el otro lo
  modifica? → A: Gana el último que guarda; si el movimiento ya estaba eliminado, el guardado se
  rechaza con "El movimiento fue eliminado".
- Q: ¿Se aceptan movimientos con fecha futura? → A: No: se rechaza cualquier fecha posterior al día
  de hoy en Argentina, en alta y en modificación, con error en el campo fecha.
- Q: ¿Qué reglas cumple la descripción (solo espacios, largo máximo)? → A: Se recortan los espacios
  de los extremos; una descripción solo de espacios cuenta como vacía y se rechaza; el máximo es 200
  caracteres y una más larga se rechaza con error en el campo.
- Q: ¿Desde dónde se usa la aplicación y debe exigir conexión cifrada? → A: Desde la red interna de
  la empresa; fuera de la propia máquina se exige conexión cifrada (HTTPS) y la sesión solo viaja
  cifrada.
- Q: ¿Hay una fecha mínima aceptada? → A: Sí: se rechaza cualquier fecha anterior al 01/01/1900, en
  alta y en modificación, con error en el campo fecha (decidido al revisar el plan).
- Q: ¿Hay un monto máximo? → A: Solo el límite técnico de 9.223.372.036.854.775.807; un monto mayor
  se rechaza con error en el campo monto (decidido al revisar el plan).
- Q: ¿Se valida el mail de un socio? → A: Solo se rechaza si tiene saltos de línea, para que no
  altere el mail; el resto del formato sigue sin validarse (decidido al revisar el plan).
- Q: ¿Se puede mandar el mail sin cifrado? → A: Sí, pero si el servidor de correo no es la propia
  máquina, el sistema deja una advertencia en el log en cada envío (decidido al revisar el plan).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cargar y consultar movimientos (Priority: P1)

Rocío, la operadora, carga cada comprobante de papel como un movimiento de Ingreso o Egreso con
descripción, monto, clasificación y fecha. El sistema valida cada dato antes de guardarlo y le
muestra todos los movimientos vigentes en una grilla paginada, del más reciente al más antiguo.

**Why this priority**: es el reemplazo directo del Excel sin validar; sin carga confiable no hay
nada que mandar a los socios.

**Independent Test**: con un operador ya autenticado, cargar movimientos válidos e inválidos y
verificar qué se guarda, con qué signo y cómo se ve en la grilla.

**Acceptance Scenarios**:

1. **Given** el formulario de alta, **When** el operador carga "Sueldo marzo", Egreso, 1000,
   SUELDOS, 20/10/2026 y guarda, **Then** queda registrado con monto -1000 y esos datos (AC-68).
2. **Given** el formulario de alta, **When** falta descripción, tipo, monto o clasificación,
   **Then** se rechaza el guardado y se marca el campo faltante (AC-19).
3. **Given** el formulario de alta, **When** el monto es `0`, `-500`, `12abc`, `12,5` o `1.200`,
   **Then** se rechaza el guardado con error en el campo monto (AC-24..26, AC-82, AC-88).
4. **Given** el formulario de alta, **When** se abre, **Then** la fecha propuesta es la del día de
   Argentina aunque el servidor esté en otra zona horaria (AC-20, AC-97); si se deja vacía se guarda
   esa fecha (AC-46) y una fecha inexistente como 30/02/2026 se rechaza (AC-47).
5. **Given** movimientos de varias fechas, **When** se muestra la grilla, **Then** aparecen ordenados
   por fecha descendente, el último cargado primero dentro de cada fecha, en páginas de 30 y con el
   monto formateado como `1.200` / `-1.200` (AC-11, AC-99, AC-83..85, AC-89, AC-91).

Escenarios completos: AC-11, AC-17..26, AC-46, AC-47, AC-68, AC-82..85, AC-88, AC-89, AC-91,
AC-97, AC-99.

---

### User Story 2 - Acceso de operadores (Priority: P1)

Los operadores se dan de alta por consola sin contraseña. En su primer ingreso definen la
contraseña escribiéndola dos veces; después ingresan con sigla y contraseña. Nadie sin sesión ve ni
modifica movimientos, y la sesión vence a los 60 minutos de inactividad.

**Why this priority**: los datos financieros de la empresa no pueden quedar expuestos; la carga
(US1) solo es utilizable detrás de este acceso.

**Independent Test**: dar de alta operadores por consola, recorrer primer ingreso, ingreso normal,
errores, cierre y vencimiento de sesión, y verificar que sin sesión no se accede a nada salvo el
login.

**Acceptance Scenarios**:

1. **Given** un operador sin contraseña, **When** ingresa su sigla, **Then** el sistema le pide
   definirla antes de dejarlo entrar (AC-35); acepta 8 caracteres y rechaza 7 (AC-53, AC-98),
   acepta 72 bytes y rechaza 73 (AC-72, AC-86), y rechaza si las dos escrituras no coinciden
   (AC-103).
2. **Given** un operador con contraseña, **When** ingresa sigla y contraseña correctas, **Then**
   accede a la grilla; con una incorrecta se rechaza el acceso (AC-36, AC-37).
3. **Given** un visitante sin sesión, **When** accede a la grilla o a cualquier acción, **Then** se
   lo redirige al login sin mostrar movimientos (AC-38).
4. **Given** una sesión inactiva 60 minutos, **When** el usuario actúa, **Then** vuelve al login con
   el aviso "Tu sesión venció por inactividad"; a los 59 minutos la acción se ejecuta (AC-40, AC-55,
   AC-56).

Escenarios completos: AC-34..40, AC-44, AC-45, AC-50..57, AC-72, AC-73, AC-86, AC-95, AC-96, AC-98,
AC-103.

---

### User Story 3 - Mail diario a los socios (Priority: P2)

Todos los días a las 17:00 de Argentina, cada socio recibe un mail propio en texto plano con los
movimientos vigentes del día, la cantidad y una línea por movimiento. Si no hubo movimientos, el
mail lo dice. El envío no se repite, no se reintenta solo y se puede hacer a mano para cualquier
fecha.

**Why this priority**: es la métrica de éxito del PRD, pero depende de que existan movimientos
cargados (US1).

**Independent Test**: con socios dados de alta por consola y movimientos de hoy, ayer y eliminados,
disparar el envío de las 17:00 contra un servidor de correo de prueba y revisar destinatarios,
asunto, cuerpo y registro de envío.

**Acceptance Scenarios**:

1. **Given** un movimiento de hoy vigente, uno de hoy eliminado y uno de ayer, **When** son las
   17:00, **Then** cada socio recibe un mail solo con el de hoy vigente (AC-42).
2. **Given** dos socios, **When** son las 17:00, **Then** salen dos mails, cada uno con un único
   destinatario; si la dirección del primero se rechaza, el segundo lo recibe igual y el rechazo
   queda en el log (AC-60, AC-61).
3. **Given** la aplicación apagada a las 17:00, **When** arranca a las 17:30, **Then** manda el mail;
   si arranca a las 18:00, no lo manda y deja en el log el comando para mandarlo a mano (AC-63,
   AC-64, AC-76).
4. **Given** el mail del día ya enviado o fallido, **When** la aplicación sigue corriendo o se
   reinicia, **Then** no lo vuelve a mandar ni a intentar (AC-65, AC-79).
5. **Given** la consola, **When** se pide el envío manual del 10/10/2026, **Then** cada socio recibe
   el mail "Movimientos del 10/10/2026" con los movimientos de ese día, sin marcar el día como
   enviado (AC-66, AC-77).

Escenarios completos: AC-41..43, AC-58..66, AC-74..79, AC-87, AC-90, AC-101, AC-102.

---

### User Story 4 - Clasificación propuesta por palabra clave (Priority: P2)

Al crear un movimiento, el sistema propone la clasificación según palabras clave de la descripción,
solo entre las del tipo elegido. Si no hay coincidencia o hay más de una clasificación posible, no
propone nada y el operador debe elegir.

**Why this priority**: acelera la carga y reduce errores, pero la carga funciona con elección
manual (US1).

**Independent Test**: escribir las descripciones de AC-01..08 y AC-12..16 con cada tipo y verificar
la clasificación propuesta o su ausencia.

**Acceptance Scenarios**:

1. **Given** un movimiento nuevo de tipo Egreso, **When** la descripción es "Sueldo marzo" o
   "VIATICO cordoba", **Then** se propone SUELDOS o VIATICOS respectivamente (AC-01, AC-14).
2. **Given** un movimiento nuevo de tipo Egreso, **When** la descripción es "Compra de café",
   "Impuesto sobre sueldos", "Factura de luz" o "Alquiler oficina", **Then** no se propone
   clasificación y no se puede guardar hasta que el operador elija una (AC-12, AC-13, AC-15, AC-16).
3. **Given** una clasificación elegida a mano, **When** el operador cambia la descripción, **Then**
   la clasificación pasa a la propuesta por la descripción nueva, o queda vacía si no hay propuesta
   (AC-67, AC-92).
4. **Given** un movimiento de tipo Egreso, **When** se intenta guardar con ALQUILERES (o uno de
   Ingreso con SUELDOS), **Then** se rechaza con error en la clasificación (AC-09, AC-10).
5. **Given** 100 descripciones distintas, **When** se mide el tiempo hasta ver la propuesta,
   **Then** al menos 95 tardan menos de 2 s (AC-80).

Escenarios completos: AC-01..10, AC-12..18, AC-67, AC-80, AC-81, AC-92.

---

### User Story 5 - Modificar y dar de baja movimientos (Priority: P3)

Desde la grilla, el operador abre un movimiento con doble click, corrige cualquier campo con las
mismas validaciones del alta o lo marca como eliminado previa confirmación. La baja es lógica: el
registro se conserva.

**Why this priority**: corrige errores de carga; mientras no exista, un error se compensa con otro
movimiento.

**Independent Test**: cargar movimientos, modificarlos y eliminarlos desde la grilla, y verificar
grilla y registro guardado.

**Acceptance Scenarios**:

1. **Given** un movimiento en la grilla, **When** el operador hace doble click, **Then** se abre el
   formulario con sus datos y el monto sin signo (AC-28, AC-69).
2. **Given** un Egreso SUELDOS en modificación, **When** cambia el tipo a Ingreso, **Then** la
   clasificación queda vacía; si vuelve a Egreso, reaparece SUELDOS (AC-70, AC-71).
3. **Given** un Egreso de 500 en modificación, **When** cambia el monto a 800 o pasa a Ingreso con
   ALQUILERES, **Then** queda -800, o Ingreso ALQUILERES 500 (AC-93, AC-94).
4. **Given** el formulario de modificación, **When** presiona "Eliminar" y confirma, **Then** el
   movimiento deja la grilla pero sigue guardado marcado como eliminado; si cancela, no cambia nada
   (AC-32, AC-33, AC-49).

Escenarios completos: AC-27..33, AC-48, AC-49, AC-69..71, AC-93, AC-94, AC-100.

---

### Edge Cases

- Cambio de día en UTC antes que en Argentina: la fecha del día y el mail usan siempre la de
  Argentina (AC-97). Por eso, a las 22:30 del 20/10 de Argentina, la fecha 21/10 todavía es futura
  y se rechaza (FR-004).
- Descripción de solo espacios: se rechaza como vacía. Descripción de 200 caracteres (tras recortar
  extremos): se acepta; de 201: se rechaza (FR-034).
- Fecha posterior a hoy (por ejemplo, un error de tipeo en el año): se rechaza en alta y
  modificación; hoy se acepta (FR-004).
- Fecha anterior al 01/01/1900: se rechaza; el 01/01/1900 se acepta (FR-004).
- Monto 9.223.372.036.854.775.807: se acepta; uno más: se rechaza (FR-003).
- Mail de socio con salto de línea: se rechaza el alta (FR-022).
- Servidor de correo de otra máquina configurado sin cifrado: el mail sale y el log lo advierte
  (FR-036).
- Descripción con palabras clave de dos clasificaciones ("Impuesto sobre sueldos"): no se propone
  nada (AC-13); la misma palabra repetida cuenta como una sola (AC-81).
- Palabra clave en medio de una palabra ("Factura" contiene "tur"): no coincide (AC-15).
- Contraseña de más de 72 bytes, o con tildes que suman bytes: se rechaza con mensaje (AC-86).
- Sigla o mail de socio repetidos con otras mayúsculas: se rechaza el alta (AC-50, AC-59).
- Intento de redefinir la contraseña de un operador que ya tiene una: se rechaza (AC-52).
- Muchos intentos fallidos seguidos de contraseña para una sigla: cada uno se rechaza igual que el
  primero, sin bloqueo ni demora; un intento correcto posterior entra normalmente.
- Dos operadores guardan el mismo movimiento: queda lo del último, sin aviso. Si otro operador lo
  eliminó mientras estaba abierto, guardar o eliminar se rechaza con "El movimiento fue eliminado"
  (FR-033).
- Día sin movimientos: el mail sale igual con "No hubo movimientos" (AC-62).
- Servidor de correo caído o configuración incompleta: el error queda en el log, sin reintento
  (AC-78, AC-79).
- Falta la clave de firma de sesión: la aplicación no arranca (AC-73).
- Acceso sin cifrar desde otra máquina de la red: no se muestra el login ni se aceptan contraseñas
  (FR-035).
- Envío de un formulario manipulado con clasificación de otro tipo: se rechaza en el servidor (AC-09,
  AC-10, AC-30).

## Requirements *(mandatory)*

### Functional Requirements

**Alta y validación** (origen: RF-01..07, RF-43, RF-44, RF-58, RF-64)

- **FR-001**: El sistema MUST permitir dar de alta un movimiento con descripción, tipo, monto,
  clasificación y fecha; descripción, tipo, monto y clasificación son obligatorios (RF-01, RF-02).
- **FR-034**: La descripción MUST guardarse sin los espacios de los extremos; si queda vacía se
  rechaza como faltante, y si supera los 200 caracteres se rechaza con error en el campo
  descripción, en alta y modificación (RF-73, RF-74).
- **FR-002**: El tipo MUST ser solo Ingreso o Egreso; el monto se guarda negativo en los egresos y
  positivo en los ingresos (RF-04..06).
- **FR-003**: El monto MUST ser un entero mayor que 0 escrito solo con dígitos; se rechazan 0,
  negativos, no numéricos, decimales y separador de miles, en alta y modificación (RF-07, RF-58,
  RF-64). Un monto mayor a 9.223.372.036.854.775.807 MUST rechazarse con error en el campo monto
  (RF-72).
- **FR-004**: La fecha MUST proponerse con el día de Argentina; vacía se guarda con ese día y una
  fecha inexistente se rechaza (RF-03, RF-43, RF-44). Una fecha posterior al día de hoy en
  Argentina, o anterior al 01/01/1900, MUST rechazarse con error en el campo fecha, en alta y
  modificación (RF-70, RF-71).

**Grilla, modificación y baja** (origen: RF-08..12, RF-26..28, RF-45..47, RF-59..61, RF-65)

- **FR-005**: El sistema MUST mostrar una grilla con los movimientos no eliminados de cualquier
  fecha (descripción, monto, tipo, clasificación, fecha), ordenada por fecha descendente y, dentro
  de cada fecha, del último cargado al primero, en páginas de 30 (RF-08, RF-60, RF-61, RF-65).
- **FR-006**: La grilla y el mail MUST mostrar el monto con punto de miles, sin decimales y con
  signo menos en los egresos (RF-59, RF-63).
- **FR-007**: El botón "Agregar movimiento" MUST abrir el alta; el doble click en una fila MUST abrir
  la modificación con todos los campos editables y el monto sin signo (RF-09, RF-10, RF-27, RF-45).
- **FR-008**: La modificación MUST aplicar las mismas validaciones que el alta (RF-26).
- **FR-009**: Al cambiar el tipo en la modificación, la clasificación MUST vaciarse si no pertenece
  al tipo nuevo y recuperarse al volver al tipo original (RF-46, RF-47).
- **FR-010**: El sistema MUST permitir eliminar un movimiento desde la modificación, previa
  confirmación, marcándolo como eliminado sin borrarlo (RF-11, RF-12, RF-28).
- **FR-033**: Si dos operadores modifican el mismo movimiento, MUST quedar lo que guardó el último,
  sin aviso. Si al guardar una modificación, o al confirmar una baja, el movimiento ya está
  eliminado, el sistema MUST rechazar la operación con "El movimiento fue eliminado" y dejarlo como
  estaba (RF-75, RF-76).

**Clasificación** (origen: RF-13..17, RF-42, RF-66)

- **FR-011**: Las clasificaciones MUST ser SERVICIOS-PRESTADOS, ALQUILERES y FINANCIEROS para
  Ingreso, y SUELDOS, IMPUESTOS-TASAS, VIATICOS, PAGO-PROVEEDORES y TURISMO para Egreso (RF-13,
  RF-14).
- **FR-012**: Al crear, el sistema MUST proponer la clasificación según la tabla de palabras clave
  del PRD, solo del tipo elegido, sin distinguir mayúsculas ni tildes y con la palabra clave al
  inicio de una palabra (RF-15).
- **FR-013**: Sin coincidencia o con coincidencias de más de una clasificación, el sistema MUST no
  proponer nada y exigir que el operador elija (RF-16).
- **FR-014**: Cada cambio de descripción al crear MUST reemplazar la clasificación por la nueva
  propuesta, o vaciarla si no hay propuesta, aunque se haya elegido a mano (RF-42, RF-66).
- **FR-015**: El sistema MUST rechazar, en alta y modificación, una clasificación que no pertenezca
  al tipo (RF-17).

**Usuarios y acceso** (origen: RF-18..22, RF-29..34, RF-41, RF-48, RF-57, RF-62, RF-69)

- **FR-016**: Los operadores MUST darse de alta solo por consola con sigla, nombre y mail, sin
  contraseña; la sigla es única sin distinguir mayúsculas y se guarda en mayúsculas (RF-18, RF-29,
  RF-30, RF-41).
- **FR-017**: Un operador sin contraseña MUST definirla en su primer ingreso, escribiéndola dos
  veces, con 8 caracteres como mínimo y 72 bytes como máximo; no se puede redefinir una existente
  (RF-19, RF-31, RF-48, RF-62, RF-69).
- **FR-018**: El ingreso MUST requerir sigla y contraseña coincidentes; una sigla inexistente se
  informa con "No existe un operador con la sigla …" sin pedir contraseña (RF-20, RF-33).
- **FR-019**: Todo, salvo el login, MUST exigir sesión; todos los usuarios autenticados ven los
  mismos movimientos (RF-21, RF-22).
- **FR-020**: El operador MUST poder cerrar sesión; una sesión vencida por inactividad se avisa en
  el login (RF-32, RF-34).
- **FR-021**: La aplicación MUST negarse a arrancar si falta la clave que firma las sesiones
  (RF-57).
- **FR-035**: La aplicación se usa desde la red interna de la empresa. Todo acceso que no venga de la
  propia máquina MUST hacerse por conexión cifrada (HTTPS): un pedido sin cifrar no muestra el
  login ni movimientos ni acepta contraseñas, y la sesión del operador solo se envía por conexión
  cifrada. El acceso desde la propia máquina puede ser sin cifrar (RNF-05).

**Mail a los socios** (origen: RF-23..25, RF-35..40, RF-49..56, RF-63, RF-67, RF-68)

- **FR-022**: Los socios MUST darse de alta solo por consola con nombre y mail obligatorio, sin
  mails repetidos (sin distinguir mayúsculas); no tienen acceso a la aplicación (RF-23, RF-35,
  RF-49). Un mail con saltos de línea MUST rechazarse (RF-77).
- **FR-023**: Todos los días a las 17:00 de Argentina el sistema MUST mandar un mail separado a cada
  socio con los movimientos no eliminados de la fecha (RF-24, RF-36).
- **FR-024**: El mail MUST ser texto plano, con asunto "Movimientos del DD/MM/AAAA", la cantidad de
  movimientos y una línea por movimiento con descripción, monto, tipo, clasificación y fecha; sin
  movimientos dice "No hubo movimientos" (RF-25, RF-37, RF-50, RF-51, RF-67, RF-68).
- **FR-025**: El envío automático de un día MUST ocurrir una sola vez: se registra el día antes de
  mandar y un envío fallido no se reintenta (RF-39, RF-56).
- **FR-026**: Si la aplicación arranca entre las 17:00 y las 18:00 sin haber mandado el mail del
  día, MUST mandarlo; desde las 18:00 no lo manda y deja en el log el comando para mandarlo a mano
  (RF-38, RF-52, RF-53).
- **FR-027**: El sistema MUST permitir el envío manual por consola para el día o una fecha dada, sin
  registrarlo como envío automático (RF-40, RF-54).
- **FR-028**: Cada error de envío (servidor caído, dirección rechazada, configuración incompleta)
  MUST quedar en el log (RF-55).
- **FR-036**: Si el mail se manda sin cifrado a un servidor de correo que no es la propia máquina,
  el sistema MUST dejar una advertencia en el log y mandarlo igual (RF-78).

**No funcionales** (origen: RNF-01..04)

- **FR-029**: La clasificación propuesta MUST mostrarse en menos de 2 s en el 95 % de los casos
  (RNF-01).
- **FR-030**: Las contraseñas MUST guardarse solo como hash irreversible con el costo mínimo que fija
  el PRD, nunca en texto plano (RNF-02).
- **FR-031**: La sesión MUST vencer a los 60 minutos de inactividad; cada acción renueva el plazo
  (RNF-03).
- **FR-032**: El código y el repositorio MUST tener 0 credenciales; la configuración secreta vive
  fuera del repositorio (RNF-04).

### Key Entities *(include if feature involves data)*

- **Movimiento**: descripción, tipo (Ingreso/Egreso), monto entero con signo según el tipo,
  clasificación del tipo, fecha, marca de eliminado y orden de carga (para desempatar en la grilla).
  Lo comparten todos los operadores.
- **Clasificación**: lista fija de 8 rubros, cada uno de un solo tipo, con sus palabras clave.
- **Operador**: sigla única en mayúsculas, nombre, mail y contraseña (vacía hasta el primer
  ingreso). Inicia sesión y opera movimientos.
- **Socio**: nombre y mail único. Solo recibe el mail diario.
- **Envío diario**: fecha de un mail automático ya iniciado; impide repetirlo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Los socios reciben el mail de movimientos el 100 % de los días en que la aplicación
  está corriendo entre las 17:00 y las 18:00; los días restantes quedan avisados en el log con el
  comando para reenviarlos.
- **SC-002**: El 95 % de las clasificaciones propuestas se muestran en menos de 2 s.
- **SC-003**: El 0 % de los movimientos guardados tiene monto, fecha, tipo o clasificación inválidos
  según las reglas de esta spec.
- **SC-004**: El contenido de cada mail coincide al 100 % con los movimientos vigentes guardados para
  esa fecha.
- **SC-005**: Ninguna pantalla ni acción, salvo el login, es accesible sin sesión.
- **SC-006**: El repositorio contiene 0 credenciales.
- **SC-008**: El 0 % de las contraseñas y sesiones viaja sin cifrar fuera de la propia máquina.
- **SC-007**: El 100 % de los AC del PRD está cubierto por al menos un test automatizado que lo cita.

## Assumptions

- El PRD (`PRD.md`) es la fuente de verdad; sus "Decisiones confirmadas" se aplican sin volver a
  preguntarlas.
- Volumen: unos 200 movimientos por día, unos 50.000 por año, cargados por uno o pocos operadores.
- Fuera de alcance (FA-01..13): comprobantes, bancos, billeteras virtuales, pantallas de
  administración de operadores o socios, validación de formato de mail o sigla (salvo saltos de
  línea en el mail de socios, FR-022), recuperación de
  contraseña, baja o modificación de operadores y socios, restauración de movimientos eliminados,
  historial de cambios, búsqueda, filtros y exportación, varias monedas, roles distintos.
- Riesgos aceptados: la sigla de un operador nuevo permite que otro defina su contraseña primero; el
  mensaje de sigla inexistente revela qué siglas existen; una contraseña olvidada no se recupera;
  no hay límite de intentos de contraseña, así que se pueden probar contraseñas sin freno.
- Dependencias: un servidor de correo saliente configurado fuera del repositorio, una única
  instancia de la aplicación corriendo contra la base de datos y un certificado para la conexión
  cifrada en la red interna.
