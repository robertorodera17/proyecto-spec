# Contrato: mail diario

Un mensaje por socio, con su dirección como único destinatario (RF-36). Una sola parte
`text/plain; charset=utf-8`, sin HTML (RF-67).

- **De**: `SMTP_FROM`
- **Para**: mail del socio
- **Asunto**: `Movimientos del DD/MM/AAAA` (RF-50)

## Cuerpo con movimientos

```text
Movimientos del 21/10/2026
Cantidad: 3

21/10/2026 | Egreso  | SUELDOS             |       -1.000 | Sueldo marzo
21/10/2026 | Ingreso | ALQUILERES          |        5.000 | Alquiler local
21/10/2026 | Egreso  | VIATICOS            |         -350 | Viáticos Córdoba
```

- Una línea por movimiento vigente de la fecha (RF-68), en el orden de la grilla (último cargado
  primero).
- Campos: fecha, tipo, clasificación, monto (formato de la grilla: punto de miles, signo menos en
  egresos; RF-63) y descripción al final, porque es el único campo de largo variable (RF-25).
- Separador ` | `; las columnas fijas se rellenan con espacios para que se alineen en fuente
  monoespaciada.

## Cuerpo sin movimientos (RF-37)

```text
Movimientos del 21/10/2026
Cantidad: 0

No hubo movimientos.
```
