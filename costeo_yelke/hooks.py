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
	"Supplier": "public/js/supplier.js",
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
		"costeo_yelke.api.impresion.direccion_lineas"],
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
		"validate": "costeo_yelke.api.bank_account_api.validar",
		"on_update": "costeo_yelke.api.bank_account_api.sincronizar_proveedor",
	},
	"Purchase Receipt": {
		"validate": "costeo_yelke.api.contabilidad.validar_recepcion_contra_oc",
		"before_submit": "costeo_yelke.api.costeo_api.validar_envio_capturado_recibo",
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
	},
}

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

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"costeo_yelke.api.item_api.revisar_vigencias_precio_acordado",
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
