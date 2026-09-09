# Copyright (c) 2026, Ixoom and contributors
"""Guard de acceso interno para toda la superficie whitelisted de `costeo_yelke`.

Herramienta de USO INTERNO EXCLUSIVO: ningún cliente/Website User debe invocar sus
métodos ni ver su SPA. Se corre como before_request (la sesión ya está resuelta),
rechazando con 403 cualquier llamada a `costeo_yelke.*` de quien no sea "System User".
El scheduler y `bench execute` no pasan por aquí.
"""

import frappe
from frappe import _

APP_PREFIX = "costeo_yelke."


def is_internal_user():
	user = frappe.session.user
	if not user or user == "Guest":
		return False
	return frappe.db.get_value("User", user, "user_type") == "System User"


def _requested_method():
	req = getattr(frappe.local, "request", None)
	if req is not None:
		path = (req.path or "").strip()
		if path.startswith("/api/method/"):
			return path[len("/api/method/"):].strip("/")
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


def guard_internal():
	method = _requested_method()
	if not (method.startswith(APP_PREFIX) or _is_our_override(method)):
		return
	if not is_internal_user():
		frappe.throw(
			_("Acceso restringido: esta herramienta es de uso interno."),
			frappe.PermissionError,
		)
