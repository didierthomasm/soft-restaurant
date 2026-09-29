# Mapa de la base SoftRestaurant (`softrestaurant11`)

Descubierto el 2026-09-28 con el login de solo lectura `reportes_ro`.

## Servidor

| Dato | Valor |
|---|---|
| Instancia | `<servidor>\NATIONALSOFT` (única instancia, puerto 1433) |
| Acceso desde Mac | vía Tailscale; host/puerto en `.env` |
| Versión | SQL Server 2014 SP1 Express (`12.0.4100.1`) |
| Tamaño | 362 tablas, 119 con datos, 47 vistas, 13 procedures |
| Datos desde | tickets desde 2024-11-16, asistencias desde 2024-12-07 |

**TLS:** el servidor solo habla TLS 1.0. `pymssql`/FreeTDS necesita `freetds.conf`
(raíz del proyecto) con `enable tls v1 = yes` y `openssl ciphers = DEFAULT:@SECLEVEL=0`;
los scripts lo cargan vía `FREETDSCONF`. Sin eso: error 20002.

**Límites de Express:** 1 socket / 4 cores, 1410 MB de buffer pool. Consultas de
reporte deben ser acotadas por fecha y usar `WITH (NOLOCK)` para no bloquear al POS.

**Acceso desde Docker:** el contenedor `backend` alcanza SR a través del Tailscale del
host (Docker Desktop enruta por la red de macOS); `freetds.conf` se monta en
`/etc/freetds/freetds.conf`. Verificado el 2026-09-29 con `scripts/check_connection.py`.

## Asistencia

### `registroasistencias` (2,527 filas)

| Columna | Tipo | Notas |
|---|---|---|
| `idmovto` | varchar | PK |
| `idempleado` | varchar | → `meseros.idmesero`; con cero a la izquierda (`'06'`), el reporte SR lo muestra como `6` |
| `entrada` | datetime | hora de checada |
| `salida` | datetime | NULL en 2,490 de 2,527 filas; no se usa |
| `tipo` | smallint | siempre `1` |

### `meseros` (9 filas) — catálogo de empleados

Columnas útiles: `idmesero`, `nombre`, `tipo`, `visible`, `perfil`.
**No leer** `contraseña` ni `fotografia`.

Hay 9 registros; 6 empleados checan. Lista y mapeo a nombres de RH en
`docs/private/reconciliation.md` (no versionado).

### Horarios

`horariosturnos`, `HORARIOCORTE`, `huellameseros` existen pero están **vacías**.
SR no guarda horarios de empleados → viven de nuestro lado.

### Conciliación ✅

Un mes completo de checadas (`entrada` en `[inicio, fin)`) coincide 1:1, por empleado,
con el reporte exportado de SR. Cifras en `docs/private/reconciliation.md`.

## Ventas

### `cheques` (25,086) — un ticket por fila

Columnas clave: `folio` (PK), `fecha` (apertura), `cierre`, `cancelado`, `pagado`,
`idmesero`, `mesa`, `nopersonas`, `idturno`, `descuento` (% a nivel ticket),
`total`, `subtotal`, `propina`, `efectivo`, `tarjeta`, `totalalimentos`, `totalbebidas`.

### `cheqdet` (165,107) — renglones del ticket

`foliodet` → `cheques.folio`. Columnas clave: `idproducto`, `cantidad`, `precio`
(con IVA), `preciocatalogo`, `descuento` (% del renglón), `hora`, `idmeseroproducto`,
`idcortesia`.

### Catálogos

- `productos` (6,405): `idproducto`, `descripcion`, `idgrupo`
- `grupos` (11): `idgrupo`, `descripcion` (BARRIL, IMPORTADAS, NACIONALES, COCINA, …), `clasificacion`
- `chequespagos` (27,031): `folio`, `idformadepago`, `importe`, `propina`
- `cancela` (5,019): renglones cancelados
- `turnos` (646): turno de caja por día (`apertura`/`cierre`)

### Reglas de negocio (derivadas por conciliación)

- **El periodo se filtra por `cheques.cierre`**, no por `fecha`: el bar cierra
  después de medianoche. Excluir `cancelado = 1`.
- **Venta total por renglón** =
  `cantidad * precio * (1 - cheqdet.descuento/100) * (1 - cheques.descuento/100)`
- **Venta a precio de catálogo** = `cantidad * preciocatalogo`

### Conciliación ✅

Un mes completo filtrado por `cierre` y sin cancelados coincide con el reporte
`PRODUCTOSVENDIDOSPERIODO` de SR en productos, unidades, venta total y venta a
catálogo. Cifras en `docs/private/reconciliation.md`.
