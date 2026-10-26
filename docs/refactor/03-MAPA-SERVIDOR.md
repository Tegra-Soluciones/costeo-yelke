# 03 · Mapa del servidor

A dónde va cada pieza del servidor. Generado del código el 15-oct-2026 (commit `519ce25` +
cambios de seguridad de ese día) y revisado a mano para que las 14 capas queden sin ciclos.

- **Fuente de verdad para las herramientas:** `mapa-servidor.tsv` (una fila por símbolo:
  nombre, tipo, si es expuesto, línea y tamaño originales, destino, y desde qué otras áreas se
  usa). Las herramientas buscan por **nombre**, no por línea: los números de línea son solo
  referencia del día en que se generó.
- **Si aparece una función que no está en el mapa** (alguien la agregó después), la herramienta
  `mover.py` se detiene y la lista. La sesión le asigna destino según la sección 3 de
  `01-ARQUITECTURA-DESTINO.md`, agrega la fila al `.tsv` y lo anota en `PROGRESO.md`.
- **⚠️ legado** = función expuesta sin uso conocido en la pantalla. Se mueve igual que las demás y
  solo se retira en la Fase 3 (sesión L6), después de confirmarlo.

## 1. Resumen por área (`costeo_api.py`)

| Capa | Área | Líneas aprox. | Archivos destino | Sesión |
|---|---|---|---|---|
| 1 | comun | 320 | constantes, unidades, moneda, productos, alcance, contactos, permisos, costos_adicionales | M0 |
| 2 | catalogo | 32 | precios | M1 |
| 3 | ventas | 768 | lineas, cotizacion, orden_venta, impuestos, precio_acordado | M1 |
| 4 | costeo | 505 | ciclo, variantes, relacionados | M1 |
| 5 | ingenieria | 1,404 | piezas, articulos, flujo, boms | M2 |
| 6 | planeacion | 1,283 | plan, solicitud, lotes_material, posicion, legado | M3 |
| 7 | compras | 1,038 | precios, ordenes, recibos, cotizaciones_proveedor, flete, documento | M4 |
| 8 | talleres | 2,911 | orden_manufactura, subcontratos, saldos, encargos, avance · envios, recibos, sobrantes, lotes, paradas, ramas | M5 · M6 |
| 9 | entregas | 314 | remision, flete_cliente | M7 |
| 10 | costos | 223 | costo_real | M7 |
| 11 | facturacion | 492 | venta, compra, overhead | M7 |
| 12 | reportes | 504 | reporte_final, tablero | M7 |
| 13 | vistas | 439 | lotes (`get_lotes_produccion`) | M7 |
| 14 | documentos | 274 | validacion, impresion, contactos, envio | M7 |

El archivo destino más grande queda en ~720 líneas (`talleres/lotes.py`).

## 2. Los demás módulos de `api/` y el doctype (sesiones M8 y M9)

Se mueven completos a su área y dejan **su propia fachada** en `api/<mismo nombre>.py`, igual
que `costeo_api.py`. El reparto por función dentro de cada uno lo arma la sesión con la misma
herramienta (`mapa.py --modulo <archivo>`), respetando las capas.

| Módulo actual | Líneas | Destino | Notas |
|---|---|---|---|
| `api/quotation_api.py` | 452 | `ventas/pantalla_cotizacion.py` | backend de la pantalla independiente; se unifica en F8 |
| `api/sales_order_api.py` | 354 | `ventas/pantalla_orden_venta.py` | ídem |
| `api/tallas_ov.py` | 187 | `ventas/tallas_ov.py` | |
| `api/sales_invoice_api.py` | 328 | `facturacion/pantalla_factura_venta.py` | ídem |
| `api/contabilidad.py` | 352 | `facturacion/contabilidad.py` | casi todo son `doc_events` |
| `api/purchase_order_api.py` | 422 | `compras/pantalla_orden_compra.py` | ídem |
| `api/fletes.py` | 203 | `compras/flete.py` (recibo y factura del flete) y `entregas/flete_cliente.py` (remisión) | se reparte por función |
| `api/tallas_lote.py` | 285 | `talleres/tallas_lote.py` | |
| `api/om_general.py` | 341 | `talleres/om_general.py` | |
| `api/impresion.py` | 479 | `documentos/impresion.py` | |
| `api/documentos_api.py` | 157 | `documentos/documentos.py` | |
| `api/item_api.py` | 1,109 | `catalogo/articulos.py` (alta, edición, UDM) y `catalogo/precios.py` (listas de precios, precio acordado, vigencias) | se parte en dos |
| `api/costeo_template_api.py` | 439 | `catalogo/plantillas.py` | |
| `api/bank_account_api.py` | ~50 | `catalogo/cuentas_bancarias.py` | |
| `costeo_yelke/doctype/costeo/costeo.py` | 1,963 | estados de pieza (`_resolve_piece_states`, `_ops_prenda_armada` y auxiliares) → `ingenieria/piezas.py`; métodos `pp_*` → `planeacion/plan_escritorio.py` | el controlador conserva los métodos que llama el escritorio, como envolturas |
| `overrides/`, `security.py`, `roles.py`, `install.py`, `compania_setup.py`, `hooks.py` | — | **se quedan donde están** | |

## 3. Detalle por archivo destino (`costeo_api.py`)

"Usado también desde" = otras áreas que llaman a ese símbolo. Sirve para saber qué
reexportaciones o imports hacen falta y por qué el orden de las sesiones es el que es.

#### `dominio/catalogo/precios.py` — 2 símbolos, ~32 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `get_item_price` | sí | 11 |  | Returns price of an item from a given (or default) price list. |
| `proveedores_para_item` | sí | 21 |  | Proveedores que tienen este ítem en su lista de precios de COMPRA (Item Price buying), |

#### `dominio/compras/cotizaciones_proveedor.py` — 3 símbolos, ~67 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_dedupe_items_por_proveedor` |  | 10 |  |  |
| `mr_crear_rfq` | sí | 30 |  | Crea una Solicitud de Cotización (RFQ) para UN proveedor -- se dispara con su |
| `mr_crear_presupuesto_proveedor` | sí | 27 |  | Crea un Presupuesto de Proveedor (Supplier Quotation) para UN proveedor -- mismo |

#### `dominio/compras/documento.py` — 4 símbolos, ~304 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `get_documento_compra` | sí | 85 |  | Detalle genérico de un documento de compra (OC / RFQ / Presupuesto de proveedor). |
| `preview_conversion_uom_oc` | sí | 11 |  | Recálculo instantáneo (solo lectura, no guarda nada) al cambiar la UDM de una |
| `guardar_documento_compra` | sí | 152 |  | Guarda ediciones de un documento de compra en borrador. |
| `_validar_sobrecompra_contra_solicitud` |  | 56 |  | Deja comprar de más SOLO si todavía hay prendas por hacer. |

#### `dominio/compras/flete.py` — 5 símbolos, ~78 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `FLETE_DESCRIPTION` |  | 1 | compras.precios |  |
| `_get_shipping_row_amount` |  | 6 | compras.documento, costos.costo_real | Lee el monto de la fila de flete (si existe) de la tabla 'taxes' del documento. |
| `_set_purchase_shipping_row` |  | 41 | compras.documento | Agrega/edita la fila de flete en 'taxes' (Purchase Taxes and Charges), |
| `_envio_capturado_taxes` |  | 2 | compras.documento |  |
| `validar_envio_capturado_recibo` |  | 28 |  | Hook before_submit (ver hooks.py, doc_events) -- en TODO recibo (materia prima o |

#### `dominio/compras/ordenes.py` — 4 símbolos, ~305 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `mr_crear_oc` | sí | 169 |  | Crea Orden(es) de Compra desde la MR (una OC por proveedor) y jala el precio (ver |
| `mr_crear_ocs_por_lotes` | sí | 21 |  | Genera de un jalón varias Órdenes de Compra, una por lote, cada una con su |
| `mr_generar_oc_lote` | sí | 104 |  | Genera la Orden de Compra de UN lote específico, con la cantidad y fecha que |
| `oc_jalar_precios` | sí | 11 |  | Re-jala los precios de una OC en borrador (Presupuesto de Proveedor → precio |

#### `dominio/compras/precios.py` — 4 símbolos, ~109 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_precio_costeo_material` |  | 16 | compras.recibos | Precio y UDM con los que se costeó este material (costeo_producto_detalle, |
| `_precio_para_oc` |  | 56 | compras.documento | Precio para la OC, en orden de preferencia: |
| `_aplicar_impuestos_doc` |  | 20 | compras.recibos | Aplica la plantilla de impuestos de compra que le toca al PROVEEDOR del documento |
| `_aplicar_precios_oc` |  | 17 | compras.ordenes |  |

#### `dominio/compras/recibos.py` — 10 símbolos, ~175 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `get_recibos` | sí | 76 |  | OC validadas (materia prima) ligadas al plan + sus recibos de compra. |
| `_TOL_RECIBO` |  | 1 | talleres.recibos |  |
| `_pendiente_por_recibir` |  | 4 |  | Cantidad total que falta por recibir de los renglones de una OC o encargo |
| `_recibos_de` |  | 12 |  | Recibos (no cancelados) de una OC o encargo, del más viejo al más nuevo: |
| `_estado_recibos` |  | 17 |  | Resumen para la pantalla. ``receipt`` es el que se abre al entrar al paso: el |
| `estado_recibos_oc` |  | 3 | facturacion.compra, vistas.lotes |  |
| `estado_recibos_sco` |  | 4 | talleres.recibos, talleres.subcontratos, vistas.lotes |  |
| `crear_recibo_oc` | sí | 38 |  | Recibo de Compra de la OC (entrada a inventario), con el almacén de materias |
| `get_estado_recibos` | sí | 5 |  | Estado de recibos de una OC ("Purchase Order") o encargo ("Subcontracting Order"). |
| `_quitar_renglones_en_cero` |  | 15 | compras.documento, talleres.recibos | En un recibo PARCIAL lo que no llegó se deja en 0: esos renglones se quitan |

#### `dominio/comun/alcance.py` — 5 símbolos, ~105 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_get_plan_for_so` |  | 18 | planeacion.plan | Nombre del Production Plan (no cancelado) que ya está ligado a esa OV específica, |
| `_lote_refs_del_costeo` |  | 23 | vistas.lotes | Todos los nombres de lote ya usados en un costeo, de cualquier OV: los |
| `_ovs_del_costeo` |  | 5 |  | Órdenes de venta vivas (no canceladas) de un costeo. |
| `_ov_del_plan` |  | 3 |  | La OV a la que está ligado un Production Plan (tabla hija nativa), o None. |
| `_alcance_ov` |  | 56 | facturacion.compra, vistas.lotes | Qué documentos de producción pertenecen a UNA orden de venta del costeo. |

#### `dominio/comun/constantes.py` — 1 símbolos, ~1 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `LOTE_UOM` |  | 1 | ingenieria.articulos, ingenieria.boms |  |

#### `dominio/comun/contactos.py` — 1 símbolos, ~15 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_party_links` |  | 15 | entregas.remision, talleres.subcontratos | Direcciones/contactos ligados a un proveedor o cliente (Dynamic Link). |

#### `dominio/comun/costos_adicionales.py` — 2 símbolos, ~38 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_default_landed_cost_account` |  | 10 | compras.flete | Cuenta por defecto para costos que se CAPITALIZAN al valor del inventario |
| `_landed_cost_row` |  | 28 | talleres.encargos, talleres.envios, talleres.recibos | Arma una fila de 'Landed Cost Taxes and Charges' (additional_costs de SCO/Stock |

#### `dominio/comun/moneda.py` — 5 símbolos, ~46 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_monedas_activas` |  | 2 | compras.documento |  |
| `_moneda_compania` |  | 2 | compras.documento, facturacion.compra |  |
| `_tipo_cambio` |  | 10 |  | Tipo de cambio moneda -> moneda de la compañía (registros de Currency Exchange |
| `tipo_cambio_referencia` | sí | 8 |  | El tipo de cambio de referencia del sistema para una fecha: registros de |
| `_aplicar_moneda` |  | 24 | compras.documento | Cambia la moneda de un documento de compra en borrador conservando su VALOR: los |

#### `dominio/comun/permisos.py` — 1 símbolos, ~27 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_vistas_de_documento` |  | 27 | compras.documento, documentos.validacion | Vistas de Producción que autorizan a escribir/validar ESE documento -- basta |

#### `dominio/comun/productos.py` — 2 símbolos, ~21 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_producto_de_fg` |  | 14 | talleres.encargos, talleres.lotes, talleres.paradas, talleres.saldos, vistas.lotes | Producto terminado al que pertenece un ``fg_item`` de OC/SCO de maquila. |
| `_productos_terminados_de_costeo` |  | 7 | entregas.remision, talleres.encargos, talleres.lotes, talleres.paradas, talleres.saldos, vistas.lotes | Códigos de producto terminado de un costeo, ordenados de más largo a más |

#### `dominio/comun/unidades.py` — 3 símbolos, ~67 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_uom_conversion_factor` |  | 13 | compras.precios | Factor de conversión de `uom` a la UDM de almacén del artículo -- SOLO si `uom` |
| `_convertir_uom_compra` |  | 23 | compras.documento | Recalcula qty + conversion_factor al cambiar la UDM de una línea de compra -- |
| `_es_compra_por_paquete` |  | 31 | compras.documento, compras.ordenes, planeacion.lotes_material | True si, en ESA UDM puntual, este artículo se compra en paquetes completos -- |

#### `dominio/costeo/ciclo.py` — 8 símbolos, ~152 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `get_costeo_list` ⚠️ legado | sí | 9 |  | Lista de costeos con campos para el pipeline. |
| `get_company_defaults` | sí | 68 |  | Centro de costos y almacenes (materia prima / trabajo en proceso) que le |
| `set_costeo_status` ⚠️ legado | sí | 7 |  | Actualiza el estatus del pipeline. |
| `crear_revision_costeo` | sí | 26 |  | Crea una nueva revisión (borrador) de un Costeo ya validado o cancelado, enlazada |
| `get_revisiones_costeo` | sí | 10 |  | Devuelve la cadena de revisiones de un Costeo: la anterior (si esto es una |
| `delete_costeo` | sí | 4 |  | Elimina un Costeo (y sus tablas hijas en cascada). |
| `eliminar_orden_y_costeo` | sí | 20 |  | Elimina una Orden de Venta ya cancelada junto con su Costeo relacionado. |
| `duplicate_costeo` | sí | 8 |  | Crea una copia del Costeo con estatus Borrador. |

#### `dominio/costeo/relacionados.py` — 3 símbolos, ~167 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `get_costeo_related` | sí | 116 |  | Documentos generados a partir del Costeo (cotización, orden de venta, remisión, factura). |
| `_get_cadena_costeo` |  | 33 |  | Camina el campo amended_from en ambos sentidos -- Costeo funciona como una lista |
| `get_historial_costeo` | sí | 18 |  | Historial completo para trazabilidad: todas las revisiones del costeo (de la |

#### `dominio/costeo/variantes.py` — 4 símbolos, ~186 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_CHILD_ROW_SYSTEM_FIELDS` |  | 2 |  |  |
| `_slug_item_code` |  | 3 |  |  |
| `crear_variante_talla` | sí | 153 |  | Crea una 'Variante de talla' de un producto ya cargado en el Costeo: un |
| `ajustar_material_variante_talla` | sí | 28 |  | Ajusta el consumo por pieza (Costeo Producto Detalle.internal_qty) de UN |

#### `dominio/costos/costo_real.py` — 8 símbolos, ~223 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_pinvs_validadas_de_oc` |  | 9 |  | Facturas de compra VALIDADAS que facturan esta OC (directo o vía su recibo: |
| `_facturado_de_oc` |  | 27 |  | Renglones ya FACTURADOS por el proveedor contra esta OC, agrupados por renglón. |
| `_costo_real_de_oc` |  | 21 | reportes.reporte_final | Renglones del costo REAL de una OC y de dónde salieron, en este orden: |
| `_por_facturar_de_oc` |  | 9 | reportes.reporte_final | Cuánto de esta OC falta por facturar: lo contratado menos lo ya facturado. Es lo |
| `_flete_materiales_de_oc` |  | 16 | reportes.reporte_final | Flete real de una OC de materia prima, con la misma preferencia que el costo: |
| `_maquila_recibida_de_oc` |  | 21 |  | Renglones de maquila REALMENTE recibida (recepciones de servicio nacidas de los |
| `_material_sobrante_de_costeo` |  | 60 | reportes.reporte_final | Valor de la materia prima del costeo que NO se consumió y sigue siendo inventario |
| `_costo_directo_real` |  | 60 | facturacion.overhead | Suma de todo el costo real del costeo: materiales (+ su flete), subcontratación |

#### `dominio/documentos/contactos.py` — 1 símbolos, ~35 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `contacto_principal_proveedor` | sí | 35 |  | Contacto al que se le manda un documento a ese proveedor. |

#### `dominio/documentos/envio.py` — 3 símbolos, ~68 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `exigir_documento_enviable` |  | 11 |  | Solo se manda por correo o WhatsApp un documento VALIDADO, y solo si el usuario |
| `validar_envio_documento` | sí | 4 |  | La app lo consulta antes de abrir el envío (correo o WhatsApp). |
| `enviar_por_correo` | sí | 53 |  | Envía un documento por correo. |

#### `dominio/documentos/impresion.py` — 1 símbolos, ~24 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `get_default_print_format` | sí | 24 | documentos.envio | Formato de impresión que le toca a ESE documento. |

#### `dominio/documentos/validacion.py` — 9 símbolos, ~147 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `DOCTYPES_FLUJO_COSTEO` |  | 6 |  |  |
| `_exigir_doctype_del_flujo` |  | 6 |  |  |
| `validar_documento` | sí | 57 |  | Valida (submit) un documento en borrador. |
| `marcar_revisado_documento` | sí | 21 |  | Marca la verificación intermedia del esquema Doble (hoy solo Purchase |
| `puede_validar_costeo` | sí | 5 |  | Si el usuario actual puede validar un Costeo (rol 'Aprobador de Documentos |
| `get_permisos_validacion_yelke` | sí | 13 |  | Roles del usuario actual frente al motor de validación (Simple y Doble) -- |
| `_marcar_costeo_cancelado_si_aplica` |  | 11 |  | Al cancelar de verdad una cotización (docstatus 1 -> 2), el proyecto se da por |
| `cancelar_documento` | sí | 13 |  | Cancela un documento validado (docstatus 1 -> 2). Paso previo para poder eliminarlo. |
| `asignar_documento` | sí | 15 |  | Asigna un documento a uno o más usuarios (ToDo), como en ERPNext. |

#### `dominio/entregas/flete_cliente.py` — 2 símbolos, ~61 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_payable_account_para_proveedor` |  | 21 |  | Cuenta por pagar a usar en la póliza de flete: primero la cuenta específica del |
| `_crear_poliza_flete_remision` |  | 40 | entregas.remision | Registra el costo de envío al cliente como póliza contable: cargo a Fletes y |

#### `dominio/entregas/remision.py` — 6 símbolos, ~253 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_stock_warehouse_for` |  | 8 |  | Almacén con más existencia disponible para un ítem (para pre-llenar la remisión |
| `_entrega_de_lote` |  | 38 | vistas.lotes | Lo que un lote de producción ya puede entregar, por producto terminado. |
| `crear_remision` | sí | 96 |  | Crea una Nota de Remisión (Delivery Note) en BORRADOR desde la Orden de Venta |
| `get_remision` | sí | 38 |  | Detalle de la remisión para la vista editable (almacén y cantidad por línea, |
| `actualizar_remision` | sí | 42 |  | Actualiza fecha, almacén y cantidad de las líneas, y direcciones de envío/facturación |
| `validar_remision` | sí | 31 |  | Valida (submit) la remisión: libera el producto terminado del inventario, genera |

#### `dominio/facturacion/compra.py` — 11 símbolos, ~351 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_pinv_for` |  | 10 |  | Factura de compra (no cancelada) ligada a un documento origen vía Purchase Invoice Item. |
| `get_facturas_compra` | sí | 127 |  | Fuentes facturables de compra del costeo, con su factura si ya existe. |
| `_pinvs_de_oc` |  | 12 |  |  |
| `_recepciones_servicio_de_oc` |  | 15 |  | Recepciones de servicio (nacidas de recibos de taller) validadas de una OC de maquila. |
| `_asegurar_recepciones_servicio` |  | 12 |  | Crea la recepción de servicio de los recibos de taller de esta OC que no la |
| `_maquila_pendiente_de_facturar` |  | 5 | vistas.lotes |  |
| `_factura_de_recepciones` |  | 12 | vistas.lotes | La factura de compra (la más reciente, borrador o validada) que toma alguna de |
| `_estado_factura_sco` |  | 21 | vistas.lotes | ¿La maquila de este encargo ya está facturada? Se mira la recepción de servicio |
| `crear_factura_compra` | sí | 76 |  | Crea una Factura de Compra (Purchase Invoice) en borrador desde un Recibo de compra |
| `get_factura_compra` | sí | 35 |  | Detalle de una factura de compra para la vista editable. |
| `actualizar_factura_compra` | sí | 26 |  | Actualiza los datos manuales de una factura de compra en borrador. |

#### `dominio/facturacion/overhead.py` — 3 símbolos, ~86 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_contabilizar_overhead_factura` |  | 15 | documentos.validacion | Al validar la factura de venta, registra el overhead absorbido como póliza |
| `_overhead_pct_promedio` |  | 11 |  | % de overhead FIJO promedio (ponderado por costo) capturado en el paso Costear -- |
| `_crear_poliza_overhead_venta` |  | 60 |  | Registra el overhead (nóminas, luz, internet, renta -- indirectos que contabilidad |

#### `dominio/facturacion/venta.py` — 2 símbolos, ~55 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `crear_factura_venta` | sí | 39 |  | Crea una Factura de Venta (Sales Invoice) en BORRADOR desde la Orden de Venta del costeo. |
| `actualizar_factura_venta` | sí | 16 |  | Actualiza los datos manuales de una factura de venta en borrador. |

#### `dominio/ingenieria/articulos.py` — 4 símbolos, ~368 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `materializar_producto_terminado` | sí | 140 |  | Materializa el Producto Terminado de un renglón de Costeo: crea el Item (si |
| `get_articulos_pendientes` | sí | 110 |  | Checklist previo a preparar_produccion: agrupa por texto libre único los |
| `materializar_articulo` | sí | 81 |  | Resuelve un grupo de renglones de material/servicio/subensamblaje en texto |
| `auto_materializar_subensamblajes` | sí | 37 | planeacion.plan | Crea automáticamente (sin checklist ni modal) un Item para cada sub-ensamblaje |

#### `dominio/ingenieria/boms.py` — 13 símbolos, ~543 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_stage_sort_key_int` |  | 6 |  | Sort stage rows numerically when possible, then alphabetically. |
| `_match_material_stage` |  | 15 |  | A qué etapa corresponde un material, dado el valor libre que trae en su |
| `_split_materials_by_stage` |  | 50 |  | Reparte cada materia prima entre las etapas que la consumen. |
| `_repair_stale_bom_no` |  | 40 |  | Si este BOM ya existía de un intento anterior que falló A MEDIAS (ej. el BOM |
| `_splits_por_pieza` |  | 12 |  | {(material_id, pieza): qty} de Costeo Material Etapa -- atribución EXPLÍCITA de |
| `_materiales_por_pieza` |  | 39 |  | Reparte la materia prima de una etapa entre las PIEZAS que esa etapa produce. |
| `_fila_bom_semi` |  | 29 |  | Renglón de BOM para un semiterminado (estado de pieza, kit o sub-ensamblaje). |
| `_fila_bom_material` |  | 2 |  |  |
| `_uom_material` |  | 6 |  |  |
| `_bom_specs_de_producto` |  | 80 |  | Los BOM que hay que crear para un producto, en orden de creación (cada uno |
| `crear_boms_spa` | sí | 126 | planeacion.plan | Crea BOMs siguiendo exactamente la lógica del botón del doctype antiguo: |
| `_crear_un_subcontracting_bom` |  | 80 |  | Crea el Subcontracting BOM de UNA pieza. Uso interno de |
| `crear_subcontracting_bom` | sí | 58 | planeacion.plan | Crea un Subcontracting BOM por PIEZA de cada operación (ver |

#### `dominio/ingenieria/flujo.py` — 4 símbolos, ~464 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `get_flujo_operaciones` | sí | 206 |  | Vista del paso "Flujo de Producción": las operaciones ya resueltas y |
| `guardar_flujo_operaciones` | sí | 163 |  | Persiste los (pocos) cambios que permite el paso "Flujo de Producción": |
| `guardar_subensamblajes` | sí | 63 |  | Persiste la declaración de sub-ensamblajes de UN producto BASE (ver |
| `toggle_no_agrupar` | sí | 32 |  | Marca/desmarca 'no_agrupar' (ver doctype Etapas Costeo) en UNA etapa |

#### `dominio/ingenieria/piezas.py` — 2 símbolos, ~29 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_piece_states_de` |  | 21 | ingenieria.articulos, ingenieria.boms, ingenieria.flujo, talleres.envios, talleres.lotes, talleres.paradas, talleres.ramas, vistas.lotes | Estados de pieza de un producto del costeo -- ver _resolve_piece_states. |
| `_items_intermedios` |  | 8 | ingenieria.articulos, talleres.envios | Artículos internos que hay que crear para un producto: los estados de pieza y |

#### `dominio/planeacion/legado.py` — 6 símbolos, ~184 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `crear_boms` ⚠️ legado | sí | 10 |  | Wrapper para la creación de BOMs server-side (llama a la lógica existente). |
| `crear_solicitud_material` | sí | 38 |  | Creates a Material Request (Purchase) from raw-material rows. |
| `crear_ordenes_trabajo` ⚠️ legado | sí | 51 |  | Creates Work Orders for each finished item (requires an active BOM). |
| `crear_pos_subcontratacion` ⚠️ legado | sí | 21 |  | Creates Subcontracting Purchase Orders from stage (etapa) rows. |
| `plan_dividir_lotes` ⚠️ legado | sí | 55 |  | Divide la cantidad planificada de un producto del plan en varios lotes |
| `plan_crear_ordenes_trabajo` | sí | 9 |  | Crea las Órdenes de Trabajo DESDE el plan (nativo, quedan asociadas). |

#### `dominio/planeacion/lotes_material.py` — 6 símbolos, ~329 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `mr_dividir_en_lotes` | sí | 59 |  | Divide las líneas de la MR (todavía en BORRADOR) en una fila por lote, cada |
| `_material_por_pieza` |  | 47 |  | {item_code_material: qty_por_pieza} de UN producto -- explosión de BOM |
| `_materiales_de_lotes_por_piezas` |  | 19 |  | {lote_ref: {item_code_material: qty}} -- para cada lote (```lotes``` = |
| `mr_preview_lotes_materiales` | sí | 15 |  | Vista previa (solo lectura, no guarda nada) de cuánta materia prima |
| `mr_dividir_en_lotes_por_piezas` | sí | 152 |  | Como mr_dividir_en_lotes, pero cada lote se define por PIEZAS de cada |
| `_guardar_piezas_por_lote` |  | 37 |  | Persiste ``[{lote_ref, schedule_date, piezas:{producto: qty}}]`` en |

#### `dominio/planeacion/plan.py` — 10 símbolos, ~498 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `desbloquear_plan_produccion` | sí | 87 |  | Crea un Production Plan LIGADO a una Orden de Venta específica del Costeo. |
| `_fill_mr_items_from_inventory` |  | 37 |  | Ejecuta 'Obtener materias primas para comprar' del Production Plan neteando |
| `_fill_po_items_from_costeo` |  | 24 |  | Fallback: arma po_items directamente de los productos del costeo (sin OV). |
| `preparar_produccion` | sí | 59 |  | Ejecuta toda la preparación de producción en un paso (idempotente por OV): |
| `get_produccion_docs` | sí | 63 |  | Documentos de producción ligados al costeo, agrupados para el panel. |
| `get_plan_detail` | sí | 86 |  | Detalle del Production Plan ligado al costeo, para el panel Producir. |
| `_QTY_TOLERANCIA_PCT` |  | 1 | planeacion.solicitud |  |
| `guardar_plan` | sí | 48 |  | ``items``, si se manda, edita la cantidad a PRODUCIR de cada producto del plan |
| `plan_obtener_materias_primas` | sí | 12 |  | Re-ejecuta 'Obtener materias primas para comprar' sobre un plan en borrador. |
| `plan_crear_subcontratacion` | sí | 81 |  | Crea las OC de subcontratación por ETAPA (misma lógica del costeo, se conserva) |

#### `dominio/planeacion/posicion.py` — 1 símbolos, ~116 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `posicion_material_costeo` | sí | 116 | compras.ordenes | Posición neta de cada materia prima de un costeo -- el cálculo de MRP de toda |

#### `dominio/planeacion/solicitud.py` — 5 símbolos, ~156 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_mrs_activos_del_plan` |  | 16 | compras.recibos | Nombres de Solicitud de Material ligadas a este plan, SIN las canceladas -- |
| `plan_crear_solicitud_material` | sí | 24 |  | Crea las Solicitudes de Material DESDE el plan (nativo, quedan asociadas) y |
| `_asignar_proveedores_a_mrs` |  | 25 |  | Pone el proveedor en cada línea de materia prima: primero el del Costeo |
| `get_solicitud_material` | sí | 47 |  | MR(s) ligadas al plan + detalle de la principal, para la pestaña Solicitud de material. |
| `guardar_solicitud_material` | sí | 44 |  | Guarda ediciones de la MR en borrador -- SOLO proveedor y cantidad por línea, más |

#### `dominio/reportes/reporte_final.py` — 1 símbolos, ~371 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `get_reporte_final` | sí | 371 |  | Reporte final del costeo: compara lo ESTIMADO (capturado en el paso 'Costear', |

#### `dominio/reportes/tablero.py` — 1 símbolos, ~133 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `dashboard_metrics` | sí | 133 |  | Métricas del flujo de costeo → venta → producción subcontratada → facturación. |

#### `dominio/talleres/avance.py` — 1 símbolos, ~180 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `produccion_completa` | sí | 180 |  | True si TODAS las OC de subcontratación del costeo (o de la OV activa, si se |

#### `dominio/talleres/encargos.py` — 10 símbolos, ~517 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_sub_qty_disponible_info` |  | 109 |  | Cuántas unidades del servicio se pueden subcontratar YA, según la materia prima |
| `sub_qty_disponible` | sí | 5 |  | Ver _sub_qty_disponible_info -- expuesta tal cual por API para la sugerencia |
| `_piezas_por_prenda_de_po` |  | 27 |  | ``{fg_item: piezas que lleva UNA prenda}`` leído de la propia orden de compra. |
| `_repartir_qty_en_filas` |  | 37 |  | Reparte ``q`` piezas entre ``filas`` que comparten item_code (la misma pieza |
| `_precios_de_la_oc` |  | 17 |  | Cada servicio del encargo con EXACTAMENTE el precio de su renglón de la OC. |
| `sub_crear_sco` | sí | 226 | talleres.lotes, talleres.paradas | Crea una Subcontracting Order (borrador) a partir de la OC validada. |
| `_redondear_arriba_por_material` |  | 39 | talleres.envios | Redondea hacia arriba el TOTAL de cada material, no cada renglón suelto. |
| `redondear_materia_prima_sco` |  | 15 |  | Hook 'validate' de Subcontracting Order (ver hooks.py, doc_events) -- la materia |
| `sub_guardar_sco` | sí | 34 |  | Guarda almacenes, dirección/contacto y costos adicionales en la SCO en borrador. |
| `sub_validar_sco` | sí | 8 | talleres.lotes, talleres.paradas | Valida (submit) la orden de subcontratación. |

#### `dominio/talleres/envios.py` — 18 símbolos, ~590 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_etapas_rows_for_po` |  | 38 |  | Operaciones que corresponden a esta OC de subcontratación -- inversa de |
| `_stage_material_warehouses` |  | 32 | talleres.encargos, talleres.subcontratos | Devuelve (mp, wip, semi_terminados) para las etapas de esta OC de |
| `_stage_source_warehouse_for_po` |  | 36 |  | Almacén de origen recomendado (UN solo valor, para el botón 'usar recomendado |
| `_stage_source_warehouse` |  | 3 |  |  |
| `_aplicar_almacenes_origen_por_material` |  | 17 |  | Fija el almacén de origen POR RENGLÓN del Stock Entry -- una etapa puede necesitar |
| `_redondear_qty_arriba` |  | 20 |  | Redondea hacia arriba (nunca hacia abajo) la transferencia al taller -- la |
| `sub_transferir_material` | sí | 46 |  | Crea el Stock Entry 'Send to Subcontractor' EN BORRADOR (igual que el botón nativo |
| `_necesidad_exacta_sco` |  | 20 |  | ``{material: cantidad que pide el BOM}``, SIN el redondeo hacia arriba. |
| `_ajustar_a_existencia` |  | 80 |  | Baja a la existencia real lo que solo se pasa por el redondeo hacia arriba. |
| `_descontar_lo_que_ya_tiene_el_taller` |  | 41 |  | Baja de la transferencia el material que el taller YA tiene libre. |
| `_comprometido_en_talleres` |  | 31 | talleres.sobrantes | {(proveedor, material): qty} que YA está en el almacén de un taller pero |
| `_repartir_lo_que_ya_tiene` |  | 29 |  | Lista paralela a ``filas``: cuánto de SU material ya está en el taller. |
| `sub_get_transferencia` | sí | 64 |  | Detalle del Stock Entry de transferencia (almacenes + materiales + disponibilidad). |
| `get_stock_disponible` | sí | 8 |  | Existencia real (Bin) de un artículo en un almacén -- para refrescar "Disponible" |
| `sub_guardar_transferencia` | sí | 57 |  | Guarda almacenes de origen/destino, cantidades y costos adicionales (flete al enviar |
| `sub_validar_transferencia` | sí | 10 |  | Valida (submit) el Stock Entry de transferencia. Puede lanzar NegativeStockError si la |
| `_exigir_existencia_envio` |  | 27 |  | Antes de validar un envío al taller: si falta existencia de algo, lo dice claro. |
| `sub_enviar_material` | sí | 31 |  | Manda la materia prima al taller y deja listo el recibo: crea la transferencia, |

#### `dominio/talleres/lotes.py` — 3 símbolos, ~281 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_lote_paradas` |  | 164 | talleres.paradas, vistas.lotes | Descompone el trabajo de maquila de un lote (``cantidades`` = {producto: qty}) |
| `lote_abrir` | sí | 86 |  | Abre un lote de producción de un jalón: crea y valida la Subcontracting Order |
| `_productos_del_lote` |  | 31 | talleres.paradas | ``{producto: prendas}`` de un lote, con el MISMO conjunto de productos que usa |

#### `dominio/talleres/orden_manufactura.py` — 8 símbolos, ~230 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_OM_GENERAL` |  | 4 |  |  |
| `_OM_CAB` |  | 1 |  |  |
| `_OM_DAMA` |  | 1 |  |  |
| `_om_decode_tables` |  | 59 |  | Decodifica om_tablas_flexibles (formato meta/celda de ERPNext) a una |
| `_om_encode_tables` |  | 31 |  | Vuelca la estructura amigable del SPA a om_tablas_flexibles con el formato |
| `get_om` | sí | 35 |  | Campos de la Orden de Manufactura (instrucciones de confección) de una OC subcontratada. |
| `_guardar_om_una` |  | 60 |  | Guarda la Orden de Manufactura en UNA OC subcontratada. Uso interno -- ver |
| `guardar_om` | sí | 39 |  | Guarda la Orden de Manufactura y la replica sola al resto de OC de |

#### `dominio/talleres/paradas.py` — 4 símbolos, ~286 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_parada_entregas_registradas` |  | 29 |  | Entregas (SCO Item) ya registradas de esta parada -- mismo `po` + `lote_ref`, |
| `_parada_subensamblajes` |  | 43 | talleres.lotes, talleres.ramas, vistas.lotes | Piezas que esta parada puede entregar POR SEPARADO, en el orden de la OC. |
| `_parada_stage_ids` |  | 14 |  | stage_id (Etapas Costeo) que caen dentro de las operaciones de esta |
| `parada_registrar_entrega` | sí | 200 |  | Registra UNA ENTREGA MÁS en una parada de un lote YA abierto -- para cuando |

#### `dominio/talleres/ramas.py` — 2 símbolos, ~192 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_transitive_upstream` |  | 21 | talleres.lotes | {op_key: set(TODOS los op_key aguas arriba, transitivos)} sobre el grafo de |
| `_ramas_por_pieza` |  | 171 | vistas.lotes | Una RAMA por pieza: solo los pasos por los que esa pieza pasa, en orden, con |

#### `dominio/talleres/recibos.py` — 4 símbolos, ~154 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `ajustar_consumo_a_existencia_taller` |  | 40 |  | Hook 'validate' de Subcontracting Receipt (ver hooks.py): si lo que el recibo |
| `sub_crear_recibo` | sí | 26 | talleres.envios | Subcontracting Receipt (borrador) para recibir lo que entregó el taller. Igual |
| `sub_get_recibo` | sí | 33 |  | Datos del Subcontracting Receipt (almacenes aceptado/rechazado/proveedor + líneas). |
| `sub_guardar_recibo` | sí | 55 |  | Guarda los almacenes, cantidades y costos adicionales (flete de regreso del taller, |

#### `dominio/talleres/saldos.py` — 3 símbolos, ~107 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_po_subcontratacion_lineas` |  | 84 | talleres.encargos, talleres.subcontratos | Detalle por línea (una por Purchase Order Item) del avance de subcontratación |
| `_po_saldo_por_producto` |  | 13 | talleres.encargos | {producto: saldo_pendiente} de una OC de maquila -- el saldo de cada producto |
| `_po_saldo_por_fg` |  | 10 | talleres.encargos, talleres.paradas | {fg_item: saldo_pendiente} de una OC de maquila -- _po_subcontratacion_lineas |

#### `dominio/talleres/sobrantes.py` — 2 símbolos, ~181 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `sub_saldo_talleres` | sí | 51 | costos.costo_real, talleres.envios | Material que quedó en los almacenes de los talleres de este costeo. |
| `sub_devolver_material` | sí | 130 |  | Registra la DEVOLUCIÓN de material que un taller regresa al almacén de materia |

#### `dominio/talleres/subcontratos.py` — 3 símbolos, ~193 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `get_subcontratos` | sí | 27 |  | OC de subcontratación (maquila) ligadas al plan. |
| `_po_for_bom_item` |  | 25 |  | OC de subcontratación cuya línea de servicio produce `bom_item` (el |
| `sub_get_flujo` | sí | 141 |  | Estado del flujo de subcontratación de una OC: validada → Subcontracting Order(s) |

#### `dominio/ventas/cotizacion.py` — 4 símbolos, ~133 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `crear_cotizacion` | sí | 46 |  | Crea una Quotation en BORRADOR desde el Costeo con los datos manuales. |
| `actualizar_cotizacion` | sí | 46 |  | Actualiza los datos manuales de una cotización en borrador. |
| `set_tipo_formato_cotizacion` | sí | 10 |  | Cambia solo la vista de impresión (Normal/Volumen) de una cotización en |
| `get_cotizacion_defaults` | sí | 31 |  | Opciones para los campos manuales de la cotización/orden de venta. |

#### `dominio/ventas/impuestos.py` — 2 símbolos, ~28 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_get_sales_tax_template` |  | 17 | ventas.cotizacion, ventas.orden_venta |  |
| `_aplicar_impuestos_venta` |  | 11 | ventas.cotizacion, ventas.orden_venta | Aplica una plantilla de impuestos de venta (IVA) poblando doc.taxes -- fijar |

#### `dominio/ventas/lineas.py` — 15 símbolos, ~390 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_tallas_extra_para_producto` |  | 8 |  | Filas de tabla_tallas_costeo de este producto que llevan sobrecosto -- |
| `_talla_label` |  | 2 |  |  |
| `_tallas_label` |  | 6 | costeo.variantes | `tallas_field` puede traer VARIAS tallas agrupadas separadas por coma (ej. |
| `_es_talla_pendiente` |  | 2 |  |  |
| `_sobrecosto_titulo` |  | 4 |  |  |
| `_build_talla_extra_description` |  | 26 |  | Descripción autogenerada para la línea de tallas extra: mismo producto, |
| `_build_variante_description` |  | 20 |  | Descripción para la línea de venta de una VARIANTE de talla -- SOLO el |
| `_venta_items_para_producto` |  | 83 | ventas.cotizacion, ventas.orden_venta | Arma las líneas de Item (Quotation o Sales Order, misma forma en ambos) |
| `actualizar_talla_cantidad` | sí | 26 |  | Confirma la cantidad real de una talla que estaba 'Pendiente por cliente' |
| `_sync_venta_items_desde_tallas` |  | 32 |  | Reconstruye, para los documentos de venta EN BORRADOR ligados a este |
| `_variantes_de_costeo` |  | 36 |  | `finished_item -> {variante_talla_de, talla_grupo_label, genero, tallas}` |
| `adjuntar_info_variante` |  | 18 |  | Le agrega a cada dict de `items` (ya trae `item_code`) las claves |
| `listar_variantes_de_costeo` | sí | 7 |  | Todas las variantes de talla de este Costeo (estén o no presentes en |
| `lineas_venta_variantes` | sí | 40 |  | Arma la línea de venta (item_code/description con la talla/rate/ |
| `sincronizar_qty_variantes_a_costeo` |  | 80 | documentos.validacion | `venta_doc` = Sales Order o Quotation YA VALIDADO (docstatus=1), con |

#### `dominio/ventas/orden_venta.py` — 7 símbolos, ~174 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `validar_oc_cliente_adjunta` |  | 18 |  | before_submit de Sales Order: sin la orden de compra del CLIENTE adjunta no se |
| `crear_orden_venta` | sí | 51 |  | Crea una Sales Order en BORRADOR desde el Costeo con los datos manuales. |
| `_ligar_orden_venta_a_cotizacion` |  | 26 |  | Liga cada renglón de la OV con el de la cotización validada del costeo |
| `actualizar_orden_venta` | sí | 25 |  | Actualiza los datos manuales de una orden de venta en borrador. |
| `delete_quotation` | sí | 8 |  | Elimina una cotización -- mismo mecanismo estándar de Frappe que usa el botón |
| `delete_sales_order` | sí | 6 |  | Elimina una Orden de Venta -- mismo mecanismo estándar de Frappe que usa el |
| `generar_replica_ov` | sí | 40 |  | Crea una Orden de Venta nueva reusando los mismos artículos y precios |

#### `dominio/ventas/precio_acordado.py` — 3 símbolos, ~43 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `_precio_acordado_price_list` |  | 2 |  |  |
| `_precio_acordado_vigente` |  | 16 | ventas.orden_venta | Precio acordado (Item Price con cliente) más reciente para ese artículo, y si |
| `get_precio_acordado_status` | sí | 25 |  | Estado del precio acordado de cada artículo de la OV -- para habilitar o |

#### `dominio/vistas/lotes.py` — 1 símbolos, ~439 líneas

| Símbolo | Exp. | Líneas | Usado también desde | Qué hace |
|---|---|---|---|---|
| `get_lotes_produccion` | sí | 439 |  | Vista por LOTE de la subcontratación. Cada lote se descompone en PARADAS (ver |