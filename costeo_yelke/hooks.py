app_name = "costeo_yelke"
app_title = "Costeo Yelke"
app_publisher = "Tegra Soluciones"
app_description = "Motor de costeo y BOMs"
app_email = "daniel@tegra.mx"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

fixtures = [
	{
		"doctype": "Item Group",
		"filters": [["name", "in", ["Productos Terminados"]]],
	},
	{
		"doctype": "Talla",
	},
]

website_route_rules = [
	{"from_route": "/costeo-yelke/<path:name>", "to_route": "costeo-yelke"},
]

add_to_apps_screen = [
	{
		"name": "costeo_yelke",
		"logo": "/assets/costeo_yelke/images/logo.svg",
		"title": "Costeo Yelke",
		"route": "/costeo-yelke",
	}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/costeo_yelke/css/costeo_yelke.css"
# app_include_js = "/assets/costeo_yelke/js/costeo_yelke.js"

# include js, css files in header of web template
# web_include_css = "/assets/costeo_yelke/css/costeo_yelke.css"
# web_include_js = "/assets/costeo_yelke/js/costeo_yelke.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "costeo_yelke/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Purchase Order": "public/js/purchase_order_manufacturing_order.js",
	"Precio Acordado Recordatorio": "public/js/precio_acordado_recordatorio.js",
	# doble_captura.js va primero: define la ayuda que usan los otros tres.
	"Supplier": ["public/js/doble_captura.js", "public/js/supplier.js"],
	"Customer": ["public/js/doble_captura.js", "public/js/customer.js"],
	"Bank Account": ["public/js/doble_captura.js", "public/js/bank_account.js"],
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "costeo_yelke/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "costeo_yelke.utils.jinja_methods",
# 	"filters": "costeo_yelke.utils.jinja_filters"
# }
jinja = {
	# OM de cada taller dentro del formato "Orden de Maquila".
	"methods": ["costeo_yelke.api.om_general.om_de_oc",
		# Tallas del lote dentro del formato "Encargo a Taller" (la OC de
		# subcontratación cubre todos los lotes; el encargo es de uno solo).
		"costeo_yelke.api.tallas_lote.tallas_de_encargo",
		"costeo_yelke.api.impresion.firmas_documento",
		"costeo_yelke.api.impresion.fuentes_css",
		"costeo_yelke.api.impresion.logo_yelke",
		"costeo_yelke.api.impresion.titulo_documento",
		"costeo_yelke.api.impresion.estado_documento",
		"costeo_yelke.api.impresion.cantidad_uom",
		"costeo_yelke.api.impresion.importe_letra",
		"costeo_yelke.api.impresion.contacto_documento",
		"costeo_yelke.api.impresion.datos_empresa",
		"costeo_yelke.api.impresion.fecha_corta",
		"costeo_yelke.api.impresion.rfc_tercero",
		"costeo_yelke.api.impresion.direccion_lineas",
		"costeo_yelke.api.impresion.descripcion_html",
		"costeo_yelke.api.impresion.imagen_articulo",
		"costeo_yelke.api.impresion.tallas_atipicas",
		# "Al terminar, entregar a" en la Orden de Maquila.
		"costeo_yelke.api.entregas_taller.entregas_impresion",
		# Reporte final del costeo en PDF (formato "Reporte Final Yelke").
		"costeo_yelke.api.reporte_impresion.reporte_final_impresion"],
}

# Installation
# ------------

# before_install = "costeo_yelke.install.before_install"
after_install = "costeo_yelke.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "costeo_yelke.uninstall.before_uninstall"
# after_uninstall = "costeo_yelke.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "costeo_yelke.utils.before_app_install"
# after_app_install = "costeo_yelke.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "costeo_yelke.utils.before_app_uninstall"
# after_app_uninstall = "costeo_yelke.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "costeo_yelke.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	# Cuenta bancaria del proveedor: CLABE / tarjeta y su resumen en la ficha (v0_2_48).
	"Bank Account": {
		# Primero la doble captura (compara lo tecleado), después la limpieza y el formato.
		"validate": ["costeo_yelke.api.confirmaciones.validar_cuenta", "costeo_yelke.api.bank_account_api.validar"],
		"on_update": "costeo_yelke.api.bank_account_api.sincronizar_proveedor",
	},
	# La orden de compra del CLIENTE va adjunta a la OV y es obligatoria para
	# validarla (v0_2_56). El candado va en el doctype, no solo en la app, para que
	# tampoco se pueda saltar desde el escritorio de ERPNext.
	"Sales Order": {
		"before_submit": "costeo_yelke.api.costeo_api.validar_oc_cliente_adjunta",
	},
	"Purchase Receipt": {
		"validate": "costeo_yelke.api.contabilidad.validar_recepcion_contra_oc",
		"before_submit": [
			"costeo_yelke.api.costeo_api.validar_envio_capturado_recibo",
			"costeo_yelke.api.fletes.validar_flete_recibo",
		],
		# Envío cobrado por una paquetería externa: su factura de flete (api/fletes.py).
		"on_submit": "costeo_yelke.api.fletes.factura_flete_recibo",
		"on_cancel": "costeo_yelke.api.fletes.soltar_factura_flete_recibo",
	},
	"Subcontracting Receipt": {
		"validate": [
			"costeo_yelke.api.costeo_api.ajustar_consumo_a_existencia_taller",
			"costeo_yelke.api.contabilidad.cuenta_servicio_recibo_taller",
		],
		"before_submit": [
			"costeo_yelke.api.costeo_api.validar_envio_capturado_recibo",
			"costeo_yelke.api.contabilidad.validar_proveedor_flete",
		],
		"on_submit": "costeo_yelke.api.contabilidad.despues_de_validar_recibo_taller",
		"on_cancel": "costeo_yelke.api.contabilidad.al_cancelar_recibo_taller",
	},
	"Stock Entry": {
		"before_submit": "costeo_yelke.api.contabilidad.validar_proveedor_flete",
		"on_submit": "costeo_yelke.api.contabilidad.al_validar_transferencia",
		"on_cancel": "costeo_yelke.api.contabilidad.al_cancelar_transferencia",
	},
	"Subcontracting Order": {
		"validate": "costeo_yelke.api.costeo_api.redondear_materia_prima_sco",
	},
	"Purchase Order": {
		"on_submit": "costeo_yelke.overrides.purchase_order.registrar_precios_oficiales",
		# Orden a un taller: no se valida sin la orden de manufactura (por ninguna vía).
		"before_submit": "costeo_yelke.api.om_general.exigir_om_para_validar",
	},
}

# Factura de flete: se valida con folio del CFDI y sus adjuntos (api/fletes.py).
# Proveedor sin alta en el SAT: sus compras van sin IVA (overrides/sin_alta_sat.py).
for _dt in ("Purchase Order", "Purchase Receipt", "Purchase Invoice"):
	_ev = doc_events.setdefault(_dt, {})
	_prev = _ev.get("validate")
	_ev["validate"] = ([_prev] if isinstance(_prev, str) else list(_prev or [])) + [
		"costeo_yelke.overrides.sin_alta_sat.quitar_iva_sin_alta_sat",
		# Flete que cobra el mismo proveedor: su IVA, si lo cobra (api/fletes.py).
		"costeo_yelke.api.fletes.ajustar_iva_flete"]

# Préstamo de permisos: el Perfil de Rol reescribe los roles al guardar el usuario;
# esto vuelve a poner los prestados mientras sigan vigentes (api/permisos_temporales.py).
doc_events.setdefault("User", {})["validate"] = "costeo_yelke.api.permisos_temporales.conservar_roles_prestados"

# Tabla de precios por volumen: nunca por debajo del precio de venta del costeo.
doc_events.setdefault("Pricing Rule", {})["validate"] = "costeo_yelke.overrides.pricing_rule.precio_minimo_del_costeo"

doc_events.setdefault("Purchase Invoice", {})["before_submit"] = [
	"costeo_yelke.api.contabilidad.validar_archivos_factura",
	"costeo_yelke.api.fletes.validar_factura_flete",
]
# Toda factura (compra y venta) se valida con su PDF; el XML es opcional.
doc_events.setdefault("Sales Invoice", {})["before_submit"] = "costeo_yelke.api.contabilidad.validar_archivos_factura"

# Factura de venta cancelada: su póliza de overhead se cancela con ella.
doc_events.setdefault("Sales Invoice", {})["on_cancel"] = "costeo_yelke.api.contabilidad.al_cancelar_factura_venta"
doc_events["Sales Invoice"]["before_insert"] = "costeo_yelke.api.contabilidad.factura_venta_sin_poliza_heredada"

# Aprobaciones de Dirección (api/aprobaciones.py, docs/plan-panel-direccion.md): el
# candado único de validación, el estado Aprobado al validar y la marca de "cambió
# después de enviarse". Se SUMAN a los eventos que el documento ya tenga.
from costeo_yelke.roles import DOCUMENTOS_CON_APROBACION as _DOCS_APROBACION

for _dt in _DOCS_APROBACION:
	for _evento, _metodo in (
		("before_insert", "costeo_yelke.api.aprobaciones.nace_en_borrador"),
		("before_submit", "costeo_yelke.api.aprobaciones.candado_aprobacion"),
		("on_submit", "costeo_yelke.api.aprobaciones.al_validar"),
		("on_update", "costeo_yelke.api.aprobaciones.al_guardar"),
	):
		_actual = doc_events.setdefault(_dt, {}).get(_evento)
		_lista = [] if not _actual else ([_actual] if isinstance(_actual, str) else list(_actual))
		doc_events[_dt][_evento] = [_metodo, *_lista] if _evento.startswith("before_") else [*_lista, _metodo]

# Costeo en MAYÚSCULAS (ver uppercase_master.UPPER_COSTEO): al crear, al guardar y al
# editar ya validado (crear_variante_talla, guardar_subensamblajes...). Se SUMA a los
# eventos de aprobaciones de arriba.
for _evento in ("before_insert", "before_validate", "before_update_after_submit"):
	_actual = doc_events.setdefault("Costeo", {}).get(_evento)
	_lista = [] if not _actual else ([_actual] if isinstance(_actual, str) else list(_actual))
	doc_events["Costeo"][_evento] = ["costeo_yelke.overrides.uppercase_master.upper_costeo", *_lista]

# Remisión cancelada: su factura de flete (borrador) se va con ella (api/fletes.py).
doc_events.setdefault("Delivery Note", {})["on_cancel"] = "costeo_yelke.api.fletes.soltar_factura_remision"

# Movimientos de inventario sin fecha futura (api/contabilidad.sin_fecha_futura).
for _dt in ("Delivery Note", "Purchase Receipt", "Subcontracting Receipt", "Stock Entry"):
	_actual = doc_events.setdefault(_dt, {}).get("validate")
	_lista = [] if not _actual else ([_actual] if isinstance(_actual, str) else list(_actual))
	doc_events[_dt]["validate"] = [*_lista, "costeo_yelke.api.contabilidad.sin_fecha_futura"]

# Un documento contable/de inventario CANCELADO no se borra: Frappe libera el folio
# del último de la serie y el siguiente documento lo reutilizaría (ver
# costeo_yelke.api.contabilidad.bloquear_borrado_cancelado).
for _dt in (
	"Stock Entry", "Subcontracting Receipt", "Purchase Receipt", "Purchase Invoice",
	"Delivery Note", "Sales Invoice", "Journal Entry",
):
	doc_events.setdefault(_dt, {})["on_trash"] = "costeo_yelke.api.contabilidad.bloquear_borrado_cancelado"

# Homologación a MAYÚSCULAS de los campos de nombre/código de los datos maestros
# (ver costeo_yelke/overrides/uppercase_master.py). before_insert corre antes del
# autoname para que el nombre del documento también quede en mayúsculas.
for _dt in (
	"Customer", "Supplier", "Item", "Address", "Contact", "Lead",
	"Warehouse", "Brand", "Item Group", "Customer Group", "Supplier Group", "Territory",
):
	doc_events[_dt] = {
		"before_insert": "costeo_yelke.overrides.uppercase_master.upper",
		"before_validate": "costeo_yelke.overrides.uppercase_master.upper",
	}

# El almacén default GLOBAL (de otra compañía) se cuela en los Item Defaults vacíos
# (ver costeo_yelke.api.item_api.limpiar_almacen_de_otra_compania).
doc_events["Item"]["before_validate"] = [
	"costeo_yelke.overrides.uppercase_master.upper",
	"costeo_yelke.api.item_api.limpiar_almacen_de_otra_compania",
]

# Va DESPUÉS del bloque de mayúsculas, que reemplaza el diccionario de estos doctypes.
# Doble captura del RFC (api/confirmaciones.py): obligatorio y escrito dos veces.
for _dt in ("Customer", "Supplier"):
	_actual = doc_events.setdefault(_dt, {}).get("validate")
	_lista = [] if not _actual else ([_actual] if isinstance(_actual, str) else list(_actual))
	doc_events[_dt]["validate"] = [*_lista, "costeo_yelke.api.confirmaciones.validar_rfc"]

# Reglas de captura (overrides/captura.py): datos maestros y folios escritos de una sola
# forma, en la app y en el Escritorio. Después de los bloques de arriba y como listas.
_CAPTURA = {
	"Customer": {"before_validate": ["parte"], "validate": ["rfc_unico"]},
	"Supplier": {"before_validate": ["parte"], "validate": ["rfc_unico"]},
	"Address": {"before_validate": ["direccion"], "validate": ["direccion_ligada"]},
	"Contact": {"before_validate": ["contacto"], "validate": ["contacto_ligado"]},
	"Bank Account": {"validate": ["cuenta_bancaria"]},
	"Sales Order": {"before_validate": ["folio_oc_cliente"]},
	"Purchase Invoice": {"before_validate": ["folio_proveedor"]},
	"Item": {"before_validate": ["articulo"]},
}
for _dt, _eventos in _CAPTURA.items():
	for _evento, _fns in _eventos.items():
		_actual = doc_events.setdefault(_dt, {}).get(_evento)
		_lista = [] if not _actual else ([_actual] if isinstance(_actual, str) else list(_actual))
		doc_events[_dt][_evento] = [*_lista, *[f"costeo_yelke.overrides.captura.{f}" for f in _fns]]

# IVA separado (api/cuentas_mx.py): la cuenta genérica "IVA" se cambia por IVA
# acreditable en compras y por IVA trasladado en ventas. Al final de la lista, para
# corregir también los renglones que agregan los hooks de arriba (IVA del flete).
for _dt in ("Supplier Quotation", "Purchase Order", "Purchase Receipt", "Purchase Invoice",
            "Quotation", "Sales Order", "Delivery Note", "Sales Invoice"):
	_actual = doc_events.setdefault(_dt, {}).get("validate")
	_lista = [] if not _actual else ([_actual] if isinstance(_actual, str) else list(_actual))
	doc_events[_dt]["validate"] = [*_lista, "costeo_yelke.api.cuentas_mx.corregir_cuenta_iva"]

# IVA en base a flujo de efectivo: al pagar/cobrar (o cancelar el pago) la parte del IVA
# de cada factura pasa de pendiente a pagado/cobrado (api/cuentas_mx.py).
for _dt, _fn in (("Payment Entry", "al_mover_pago"), ("Journal Entry", "al_mover_pago"),
                 ("Purchase Invoice", "al_mover_factura"), ("Sales Invoice", "al_mover_factura")):
	for _evento in ("on_submit", "on_cancel"):
		_actual = doc_events.setdefault(_dt, {}).get(_evento)
		_lista = [] if not _actual else ([_actual] if isinstance(_actual, str) else list(_actual))
		doc_events[_dt][_evento] = [*_lista, f"costeo_yelke.api.cuentas_mx.{_fn}"]

# Encargos (api/encargos.py, docs/plan-encargos.md): cualquier movimiento de un documento
# del proyecto revisa si ya se atendió algún encargo; un ToDo cerrado en el Escritorio
# cuenta como "Listo".
for _dt in ("Costeo", "Quotation", "Sales Order", "Material Request", "Purchase Order", "Purchase Receipt",
            "Subcontracting Order", "Subcontracting Receipt", "Stock Entry", "Delivery Note",
            "Purchase Invoice", "Sales Invoice"):
	_actual = doc_events.setdefault(_dt, {}).get("on_change")
	_lista = [] if not _actual else ([_actual] if isinstance(_actual, str) else list(_actual))
	doc_events[_dt]["on_change"] = [*_lista, "costeo_yelke.api.encargos.al_mover_documento"]
doc_events.setdefault("ToDo", {})["on_update"] = "costeo_yelke.api.encargos.al_cambiar_todo"

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"costeo_yelke.api.item_api.revisar_vigencias_precio_acordado",
		"costeo_yelke.api.aprobaciones.recordatorio_pendientes",
		"costeo_yelke.api.delegacion.avisos_delegacion",
		"costeo_yelke.api.encargos.avisos_vencimiento",
	],
	# Préstamo de permisos: aplica los que empiezan y retira los vencidos.
	"hourly": [
		"costeo_yelke.api.permisos_temporales.procesar_permisos_temporales",
		# Pagos conciliados con la herramienta de conciliación (no disparan eventos).
		"costeo_yelke.api.cuentas_mx.revisar_iva_pendiente",
		# Encargos que se atendieron por caminos sin eventos (db.set_value).
		"costeo_yelke.api.encargos.revisar_todos",
	],
}

# Testing
# -------

# before_tests = "costeo_yelke.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "costeo_yelke.event.get_events"
# }
override_whitelisted_methods = {
	"erpnext.stock.doctype.material_request.material_request.make_purchase_order": "costeo_yelke.overrides.material_request.make_purchase_order"
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "costeo_yelke.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# Guard de uso interno: rechaza (403) cualquier llamada a costeo_yelke.* que no
# provenga de un usuario interno (System User). Clientes/Website Users quedan fuera.
before_request = ["costeo_yelke.security.guard_internal"]
# after_request = ["costeo_yelke.utils.after_request"]

# Job Events
# ----------
# before_job = ["costeo_yelke.utils.before_job"]
# after_job = ["costeo_yelke.utils.after_job"]

after_migrate = ["costeo_yelke.install.after_migrate"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"costeo_yelke.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

# Las asignaciones de ERPNext ("assigned a new task") no mandan su correo genérico: el
# aviso sale con el diseño de Yelke (costeo_api.asignar_documento, api/correos.py).
notification_skip_email_types = ["Assignment"]
