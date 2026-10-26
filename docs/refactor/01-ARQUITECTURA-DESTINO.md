# 01 · Arquitectura destino

A dónde vamos y con qué reglas. Las sesiones no deciden la arquitectura: la ejecutan. Si algo
de aquí no se puede cumplir, detente y pregunta.

---

## 1. Principios

Se aplica la idea de fondo de SOLID adaptada a Frappe, **sin** la ceremonia de clases,
interfaces, repositorios ni inyección de dependencias (pelearían con el ORM de Frappe y no
quitarían complejidad):

1. **Una responsabilidad por módulo.** Un archivo = un tema del negocio (encargos a taller,
   recibos, cotización…), de 100 a ~700 líneas.
2. **Dependencias en una sola dirección** (capas, sección 3). Ningún ciclo.
3. **Puertas delgadas.** Una función `@frappe.whitelist()` solo recibe parámetros, revisa
   permisos y llama a un servicio (Fase 3). La lógica vive en servicios.
4. **ERPNext es el motor.** Se usan sus documentos, hooks y funciones de mapeo
   (`make_purchase_receipt`, `make_purchase_invoice`…) por su **API de Python, en el mismo
   proceso**. Nunca su API REST desde el servidor, nunca sobrescribir controladores de ERPNext,
   nunca reimplementar lo que ERPNext ya calcula (impuestos, valuación, estados).
5. **Contratos estables.** Las rutas que usan la pantalla, los hooks y los parches no cambian
   nunca (sección 4).
6. **Mover primero, mejorar después.** La Fase 2 solo mueve código idéntico. La limpieza (Fase 3)
   y la reestructura de funciones críticas (Fase 4) van en sesiones aparte, con pruebas.

## 2. Estructura de carpetas destino

```
costeo_yelke/
  api/                      ← FACHADAS. Mismos nombres de archivo que hoy. Al final de la
    costeo_api.py              Fase 2 solo contienen imports de reexportación (sección 4).
    quotation_api.py …
  dominio/                  ← NUEVO. Todo el código del negocio, por área.
    __init__.py
    comun/                     unidades, moneda, productos, alcance de la OV, contactos,
                               permisos de vista, costos adicionales, constantes
    catalogo/                  artículos, precios, plantillas, cuentas bancarias
    ventas/                    líneas de venta y tallas, cotización, OV, impuestos, precio acordado
    costeo/                    ciclo de vida del costeo, variantes de talla, documentos relacionados
    ingenieria/                piezas, alta de artículos, flujo de operaciones, BOMs
    planeacion/                plan de producción, solicitud de material, lotes de material,
                               posición de material, legado
    compras/                   precios de OC, órdenes, recibos, RFQ/presupuestos, flete de
                               compra, documento de compra
    talleres/                  OM, subcontratos, saldos, encargos, avance, envíos, recibos de
                               taller, sobrantes, lotes, paradas, ramas
    entregas/                  remisión, flete al cliente
    costos/                    costo real del costeo (insumo de la póliza de overhead y del reporte)
    facturacion/               facturas de compra y venta, overhead, contabilidad (hooks)
    reportes/                  reporte final, tablero
    vistas/                    lecturas compuestas para pantalla (hoy: get_lotes_produccion)
    documentos/                validar/cancelar genéricos, impresión, envío por correo/WhatsApp
  costeo_yelke/doctype/…    ← doctypes (sin cambio de lugar). costeo.py adelgaza en M9.
  tests/                    ← NUEVO (Fase 1): contratos, fotos de lectura, integral, unitarias
tools/refactor/             ← NUEVO (Fase 1): herramientas del refactor (fuera del paquete)
frontend/src/
  pages/costeo/CosteoDetailPage.vue   ← cascarón (encabezado, stepper, barra de acciones)
  pages/costeo/pasos/…                ← un componente por paso (Fase 6)
  composables/costeo/…                ← estado y lógica por área (Fase 6)
```

El mapa exacto de **cada función** del monolito a su archivo destino está en
`03-MAPA-SERVIDOR.md` (legible) y en `mapa-servidor.tsv` (lo usan las herramientas). El de la
pantalla, en `04-MAPA-PANTALLA.md`.

## 3. Capas (orden de dependencias)

Una capa solo puede importar de capas **anteriores** de esta lista (o de sí misma):

```
 1 comun → 2 catalogo → 3 ventas → 4 costeo → 5 ingenieria → 6 planeacion → 7 compras →
 8 talleres → 9 entregas → 10 costos → 11 facturacion → 12 reportes → 13 vistas → 14 documentos
```

- El mapa se armó para que el código actual cumpla esto **sin ciclos** (verificado: 0
  violaciones al 15-oct-2026). Cuatro funciones se reubicaron a propósito para romper ciclos:
  `get_lotes_produccion` → `vistas`, `_party_links` → `comun.contactos`,
  `_vistas_de_documento` → `comun.permisos` y `_get_plan_for_so` → `comun.alcance`. Además, el
  costo real va en su propia capa `costos` (lo usan la póliza de overhead y el reporte).
- `tools/refactor/verificar_capas.py` (lo crea R1) lo revisa en cada sesión.
- **Imports dentro de funciones:** el código actual tiene 48 (`from costeo_yelke.api import
  tallas_ov` dentro de una función, etc.). Se conservan tal cual en la Fase 2 porque evitan
  ciclos de importación con los otros módulos de `api/`. En la Fase 3 se eliminan los que ya no
  hagan falta.
- **Prohibido** importar `costeo_yelke.api.*` desde `costeo_yelke.dominio.*` a nivel de
  módulo: `api/` son fachadas que importan de `dominio/`; al revés se arma un ciclo. Si un
  módulo de `dominio` necesita algo de `api/<otro>.py` que todavía no se ha migrado, usa un
  import dentro de la función, igual que hoy.

## 4. La fachada (cómo no se rompe nada al mover)

Al mover una función, en `api/costeo_api.py` queda una reexportación:

```python
# ── Fachada: estas funciones viven en costeo_yelke.dominio.ventas.cotizacion ──
from costeo_yelke.dominio.ventas.cotizacion import (  # noqa: F401
    actualizar_cotizacion,
    crear_cotizacion,
    get_cotizacion_defaults,
    set_tipo_formato_cotizacion,
)
```

Por qué funciona (la sesión M0 lo **prueba** antes de mover nada en serio):

- `@frappe.whitelist()` registra el **objeto función** al importarse el módulo nuevo. La
  reexportación es el mismo objeto, así que `frappe.is_whitelisted` lo acepta llamado por
  `costeo_yelke.api.costeo_api.crear_cotizacion`.
- `frappe.get_attr("costeo_yelke.api.costeo_api.X")` resuelve atributos del módulo, así que
  `doc_events`, `override_whitelisted_methods`, `frappe.enqueue("…")` y los parches siguen
  funcionando.
- Las funciones que aún no se mueven y llaman a una ya movida la encuentran por nombre en los
  globales del módulo (la reexportación la pone ahí).
- No hay "monkeypatching" de `costeo_api` en el código (verificado), que sería lo único que la
  fachada no cubre.

Reglas de la fachada:

1. **Es permanente.** Los parches viejos importan de `costeo_api` y se ejecutan en cada
   instalación nueva. Nunca se borra una reexportación que esté en `tests/contratos/contratos.json`.
2. Reexporta **todo** lo que alguien de fuera use: métodos expuestos, funciones de `doc_events`
   y nombres privados que importen otros módulos o parches (p. ej. `_precio_para_oc`,
   `FLETE_DESCRIPTION`, `_get_sales_tax_template`).
3. La pantalla, `hooks.py` y los parches **no se cambian** en la Fase 2. En la Fase 3 los
   `doc_events` pueden apuntar a la ruta nueva; la fachada se queda igual.
4. Al terminar la Fase 2, `costeo_api.py` = solo docstring + bloques de reexportación.

## 5. Dentro de cada área (destino al cerrar la Fase 3)

```
dominio/talleres/
  __init__.py      vacío
  api.py           puertas: TODAS las funciones @frappe.whitelist() del área, delgadas
  encargos.py      servicios: reglas y orquestación de documentos ERPNext (sin whitelist)
  envios.py        …
  consultas.py     lecturas masivas reutilizables (Fase 4: una consulta por tipo de doc)
```

- En la **Fase 2** las funciones expuestas se mueven tal cual a su módulo de servicio (con su
  decorador). En la **Fase 3** se separan: la puerta va a `api.py` y llama al servicio. La
  fachada de `api/costeo_api.py` pasa a importar de `dominio/<area>/api.py`.
- Nombre de la puerta = nombre actual (contrato). Nombre del servicio = verbo en español que
  diga qué hace (`crear_encargo`, `registrar_entrega`…).
- Los hooks (`doc_events`) van en `dominio/<area>/eventos.py`.

### Puerta tipo (Fase 3)

```python
@frappe.whitelist()
def sub_crear_sco(po: str, cantidades: str | None = None, lote_ref: str | None = None):
	"""Crea el encargo a taller (borrador) de una OC de maquila. Ver encargos.crear_encargo."""
	requiere_vista("talleres")
	return encargos.crear_encargo(po, cantidades=frappe.parse_json(cantidades), lote_ref=lote_ref)
```

## 6. Transacciones y errores (Fase 3)

- Frappe hace `commit` solo al terminar una petición sin error. Un `frappe.db.commit()` a mitad
  de proceso deja el trabajo a medias si algo truena después.
- **Regla:** se quita un `commit()` intermedio solo si la función únicamente se llama desde
  peticiones web (no desde jobs, scheduler ni parches que dependan de él) **y** ningún paso
  posterior necesita ver los datos confirmados (`frappe.enqueue`, otro proceso, correo). Cada
  `commit()` se clasifica en `PROGRESO.md` (quitado / se queda y por qué).
- Conocidos que se quedan hasta analizarlos: `mr_dividir_en_lotes` (y su ruta).
- `except Exception: pass` → prohibido. Si el error se puede ignorar, `frappe.log_error(...)` con
  título claro. Hay 6 casos que tragan el error en silencio: se resuelven en la Fase 3.
- Mensajes al usuario: siempre `_("…")` con `.format(...)`, nunca `_(f"…")`.

## 7. Permisos (Fase 5, bloqueada hasta la matriz)

Decorador único en `dominio/comun/permisos.py`:

```python
@frappe.whitelist()
@puerta(vistas=("talleres",), roles=("Aprobador de Documentos Yelke",))
def sub_validar_sco(name): ...
```

Se aplica a las 55 puertas que escriben con `ignore_permissions` y sin candado propio. La matriz
(qué rol escribe qué) la define el usuario; hasta entonces **no** se agregan permisos nuevos.

## 8. Pantalla destino (Fase 6)

- `CosteoDetailPage.vue` queda como **cascarón**: carga del costeo, encabezado, stepper,
  barra de acciones, menú del documento y cambio de paso.
- **Un componente por paso** en `pages/costeo/pasos/`, cargado con `defineAsyncComponent`
  (solo se descarga el paso que se abre).
- **Estado compartido** en composables por área (`useCosteoDoc`, `useVenta`, `useFacturacion`,
  `useEntregas`…), creados en el cascarón y compartidos con `provide/inject`, igual que ya se hace
  con `provide("produccion", …)`. No se agrega Pinia salvo que una sesión demuestre que hace falta.
- Las pantallas independientes (Cotización, OV, Factura, OC) reutilizan los mismos paneles y
  composables (Fase 6, F8).
- Pruebas de composables con **Vitest**; estilo con **ESLint** (Fase 1, R6).

## 9. Convenciones

- Nombres en español para todo lo nuevo, como el código actual. Docstrings que expliquen el
  **porqué** (estilo actual: decisiones y errores reales que motivaron la regla).
- La sangría de cada archivo movido se conserva (el monolito usa 4 espacios). El formateo con
  `ruff format` (tabuladores, según `pyproject.toml`) se aplica **solo** en la Fase 3, archivo
  por archivo y en un commit aparte de "solo formato".
- Sin cambios de nombre de funciones expuestas, nunca.
- Todo lo nuevo pasa `ruff check` sin errores. Lo movido en la Fase 2 puede arrastrar las
  observaciones que ya tenía (se limpian en la Fase 3).
