"""Verificación en dos pasos para todos (app de autenticación) y sesión de una semana
(pedido de Yelke, 2026-11-06). El correo del QR y el aviso en pantalla de Frappe se
reemplazan con instrucciones breves en español (Translation: Frappe los pasa por _())."""
import frappe

# Textos fuente EXACTOS de frappe/twofactor.py (si Frappe los cambia, la traducción deja
# de aplicar y vuelve a salir su texto: no rompe nada).
TEXTOS = {
    "One Time Password (OTP) Registration Code from {}": "Activa tu código de acceso · {}",
    "Please click on the following link and follow the instructions on the page. {0}": (
        "<b>Solo esta vez, para activar tu código de acceso:</b><br><br>"
        "1. Instala <b>Google Authenticator</b> o <b>Microsoft Authenticator</b> en tu celular.<br>"
        "2. Abre este enlace y escanea el código QR con esa app:{0}<br><br>"
        "3. Regresa a la pantalla de inicio de sesión y escribe el código de 6 dígitos que muestra la app.<br><br>"
        "El enlace vence en 1 hora. Desde ahora, al iniciar sesión (una vez por semana) se te pedirá "
        "tu contraseña y el código de la app."
    ),
    "Please check your registered email address for instructions on how to proceed. Do not close this window as you will have to return to it.": (
        "Te mandamos un correo con las instrucciones para activar tu código. No cierres esta ventana: "
        "aquí vas a escribir el código de 6 dígitos."
    ),
}


def poner_traducciones():
    for lang in ("es-MX", "es"):
        for fuente, texto in TEXTOS.items():
            nombre = frappe.db.get_value("Translation", {"language": lang, "source_text": fuente})
            if nombre:
                frappe.db.set_value("Translation", nombre, "translated_text", texto)
            else:
                frappe.get_doc({"doctype": "Translation", "language": lang, "source_text": fuente,
                                "translated_text": texto}).insert(ignore_permissions=True)
    frappe.clear_cache()


def execute():
    # Frappe resuelve el segundo paso del inicio de sesión ANTES de fijar el idioma de la
    # petición: usa el `lang` del sitio o inglés. Sin esto el aviso y el correo del QR
    # salían en inglés aunque el usuario tenga español.
    from frappe.installer import update_site_config

    update_site_config("lang", "es-MX")
    poner_traducciones()
    ss = frappe.get_single("System Settings")
    ss.enable_two_factor_auth = 1
    ss.two_factor_method = "OTP App"
    ss.otp_issuer_name = "Yelke"
    ss.lifespan_qrcode_image = 3600
    ss.session_expiry = "168:00"
    ss.flags.ignore_permissions = True
    ss.save()
    # «All» lo tiene todo usuario: así aplica a todos (Frappe nunca se lo pide a Administrator).
    frappe.db.set_value("Role", "All", "two_factor_auth", 1)
    frappe.clear_cache()
