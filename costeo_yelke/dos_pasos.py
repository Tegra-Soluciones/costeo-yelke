"""Verificación en dos pasos dada de alta en la misma pantalla de inicio de sesión.

Frappe, al primer inicio con «OTP App», manda un correo con una liga a /qrcode y la
persona tiene que ir y volver entre el correo y la página. Aquí, en cuanto la
contraseña es correcta y aún no tiene registrada la app, la respuesta del login trae
el QR, la liga otpauth:// (abre la app de autenticación en el celular) y la clave en
texto; la pantalla de login (public/js/dos_pasos.js) los muestra y pide ahí mismo el
primer código. Con ese código Frappe marca la app como registrada (`_otplogin`) y de
ahí en adelante solo pide el código. No se manda ningún correo.

El código se acepta con un paso de 30 s de holgura hacia cada lado (el reloj del
celular puede ir un poco adelantado o atrasado). Si alguien pierde su celular, en el
Escritorio > Usuario > «Reset OTP Secret» se le vuelve a mostrar el QR al entrar.

Se instala al importar costeo_yelke.security (before_request de cada petición).
"""
import pyotp

import frappe
import frappe.auth
import frappe.twofactor as tf
from frappe import _

# Minutos para dar de alta la app (instalarla, escanear) antes de que el login caduque;
# Frappe da 3 minutos.
_MINUTOS_ALTA = 15


def _en_alta(user):
	return tf.get_verification_method() == "OTP App" and not tf.get_default(user + "_otplogin")


def _authenticate_for_2factor(user):
	if not frappe.form_dict.get("otp") and _en_alta(user):
		frappe.flags.otp_expiry = _MINUTOS_ALTA * 60
	return _ORIGINAL["authenticate_for_2factor"](user)


def _get_verification_obj(user, token, otp_secret):
	if not _en_alta(user):
		return _ORIGINAL["get_verification_obj"](user, token, otp_secret)
	emisor = frappe.db.get_single_value("System Settings", "otp_issuer_name") or "Yelke"
	uri = pyotp.TOTP(otp_secret).provisioning_uri(user, issuer_name=emisor)
	# login.js pasa `verification.qrcode` tal cual a continue_otp_app: ahí van los datos.
	return {"method": "OTP App", "setup": False,
	        "qrcode": {"svg": tf.get_qr_svg_code(uri).decode(), "uri": uri, "clave": otp_secret,
	                   "minutos": _MINUTOS_ALTA}}


def _confirm_otp_token(login_manager, otp=None, tmp_id=None):
	"""La de Frappe con ±1 paso de holgura para «OTP App»; SMS y correo, igual que Frappe."""
	if tf.get_verification_method() != "OTP App":
		return _ORIGINAL["confirm_otp_token"](login_manager, otp, tmp_id)
	from frappe.auth import get_login_attempt_tracker

	otp = (otp or frappe.form_dict.get("otp") or "").replace(" ", "")
	if not otp:
		return not tf.two_factor_is_enabled_for_(login_manager.user)
	otp_secret = frappe.cache.get((tmp_id or frappe.form_dict.get("tmp_id") or "") + "_otp_secret")
	if not otp_secret:
		raise tf.ExpiredLoginException(_("Login session expired, refresh page to retry"))

	tracker = get_login_attempt_tracker(login_manager.user)
	if pyotp.TOTP(frappe.safe_decode(otp_secret)).verify(otp, valid_window=1):
		if not tf.get_default(login_manager.user + "_otplogin"):
			tf.set_default(login_manager.user + "_otplogin", 1)
			tf.delete_qrimage(login_manager.user)
		tracker.add_success_attempt()
		return True
	tracker.add_failure_attempt()
	login_manager.fail(_("Incorrect Verification code"), login_manager.user)


_ORIGINAL = {}


def instalar():
	if _ORIGINAL:
		return
	_ORIGINAL.update(authenticate_for_2factor=tf.authenticate_for_2factor,
	                 get_verification_obj=tf.get_verification_obj, confirm_otp_token=tf.confirm_otp_token)
	# frappe.auth importó las dos primeras por nombre; authenticate_for_2factor busca
	# get_verification_obj en su módulo.
	tf.authenticate_for_2factor = frappe.auth.authenticate_for_2factor = _authenticate_for_2factor
	tf.confirm_otp_token = frappe.auth.confirm_otp_token = _confirm_otp_token
	tf.get_verification_obj = _get_verification_obj
