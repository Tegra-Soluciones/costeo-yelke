# Copyright (c) 2026, Ixoom and contributors
"""Guard de acceso interno para toda la superficie whitelisted de `costeo_yelke`.

Herramienta de USO INTERNO EXCLUSIVO: ningún cliente/Website User debe invocar sus
métodos ni ver su SPA. Se corre como before_request (la sesión ya está resuelta),
rechazando con 403 cualquier llamada a `costeo_yelke.*` de quien no sea "System User".
El scheduler y `bench execute` no pasan por aquí.
"""

import re

import frappe
from frappe import _

APP_PREFIX = "costeo_yelke."


def is_internal_user():
	user = frappe.session.user
	if not user or user == "Guest":
		return False
	return frappe.db.get_value("User", user, "user_type") == "System User"


# Frappe 15 atiende el mismo método por tres rutas: /api/method/<m>, /api/v1/method/<m>
# y /api/v2/method/<m> (ver frappe/api/__init__.py, API_URL_MAP). Revisar solo la
# primera dejaba las otras dos abiertas a un Website User.
_RUTA_METODO = re.compile(r"^/api/(?:v1/|v2/)?method/(.+)$")


def _metodo_de_doctype(doctype, metodo):
	"""La v2 también acepta /api/v2/method/<doctype>/<método>: Frappe lo resuelve al
	módulo del controlador del doctype (ver frappe.api.v2.handle_rpc_call). Se
	traduce igual aquí para que un doctype de esta app quede bajo el mismo filtro."""
	from frappe.modules.utils import load_doctype_module

	try:
		return f"{load_doctype_module(doctype).__name__}.{metodo}"
	except Exception:
		# Doctype inexistente: Frappe tampoco lo va a poder ejecutar.
		return ""


def _requested_method():
	req = getattr(frappe.local, "request", None)
	if req is not None:
		ruta = _RUTA_METODO.match((req.path or "").strip())
		if ruta:
			metodo = ruta.group(1).strip("/")
			if "/" in metodo:
				doctype, _sep, nombre = metodo.partition("/")
				return _metodo_de_doctype(doctype, nombre)
			return metodo
	try:
		return frappe.form_dict.get("cmd") or ""
	except Exception:
		return ""


def _is_our_override(method):
	"""Un método de otra app (ej. erpnext.*) puede estar reemplazado por una
	implementación de costeo_yelke via override_whitelisted_methods -- el
	request llega con el nombre ORIGINAL (erpnext.*), así que el filtro por
	prefijo de abajo no lo detecta. Se cubre aparte revisando ese hook, para
	que cualquier override futuro quede blindado sin tener que acordarse de
	repetir el chequeo a mano dentro de cada función reemplazada."""
	overrides = frappe.get_hooks("override_whitelisted_methods") or {}
	target = overrides.get(method)
	if isinstance(target, list):
		target = target[0] if target else None
	return bool(target) and target.startswith(APP_PREFIX)


# ── Sin sesión: lista cerrada ─────────────────────────────────────────────────
# El sitio es de uso interno: quien no ha iniciado sesión solo puede entrar, recuperar
# su contraseña y lo técnico que eso necesita. Todo lo demás que Frappe y las otras
# apps abren a invitados (formulario de contacto, solicitud de empleo, blog, búsquedas
# públicas, pasarelas de pago, webhooks de telefonía, métodos de prueba...) se niega.
METODOS_INVITADO = {
	"login",
	"logout",
	"frappe.handler.logout",
	"frappe.handler.web_logout",
	"frappe.www.login.login_via_key",
	"frappe.www.login.login_via_token",
	"frappe.www.login.send_login_link",
	"frappe.core.doctype.user.user.reset_password",
	"frappe.core.doctype.user.user.update_password",
	"frappe.core.doctype.user.user.test_password_strength",
	"frappe.ping",
	"frappe.client.get_time_zone",
	"frappe.translate.get_all_languages",
	"frappe.translate.get_app_translations",
	# socket.io pregunta quién es el usuario (y responde «nadie» a un invitado)
	"frappe.realtime.get_user_info",
	"frappe.realtime.can_subscribe_doc",
	"frappe.realtime.can_subscribe_doctype",
	# acuse de lectura y baja de correos que manda el sistema
	"frappe.core.doctype.communication.email.mark_email_as_seen",
	"frappe.email.queue.unsubscribe",
	"frappe.website.doctype.web_page_view.web_page_view.make_view_log",
}

# Páginas (primer segmento de la ruta) que un invitado puede abrir. El resto -- blog,
# contacto, formularios web, portal, CRM, HR, Builder -- da 403.
PAGINAS_INVITADO = {
	"", "login", "update-password", "message", "website_script.js", "robots.txt",
	"qrcode",  # verificación en dos pasos: el QR que llega por correo al primer inicio
	"app", "desk", "costeo-yelke", "manual-costeo", "printview", "unsubscribe",
	# lo que no es página de Frappe: API (filtrada arriba), archivos (con su propio
	# permiso) y estáticos
	"api", "private", "files", "assets", "socket.io", ".well-known", "favicon.ico",
}


def _es_invitado():
	return (frappe.session.user or "Guest") == "Guest"


def guard_guest():
	if not _es_invitado():
		return
	# Sin el rastro del error (rutas y código del servidor) en las respuestas a invitados.
	frappe.local.flags.disable_traceback = True
	req = getattr(frappe.local, "request", None)
	ruta = ((req.path if req is not None else "") or "").strip("/")
	if ruta.split("/", 1)[0] not in PAGINAS_INVITADO:
		raise frappe.PermissionError(_("Inicia sesión para continuar."))
	method = _requested_method()
	if method and method not in METODOS_INVITADO:
		raise frappe.PermissionError(_("Inicia sesión para continuar."))


def guard_internal():
	guard_guest()
	method = _requested_method()
	if not (method.startswith(APP_PREFIX) or _is_our_override(method)):
		return
	if not is_internal_user():
		frappe.throw(
			_("Acceso restringido: esta herramienta es de uso interno."),
			frappe.PermissionError,
		)
