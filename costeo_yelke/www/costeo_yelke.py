import re

import frappe

# El SPA (Vite) genera assets con hash -- INCLUIDO index-<hash>.js -- para que un
# `vite build` nuevo nunca sirva una copia vieja cacheada (los chunks lazy hacen
# `import "./index-<hash>.js"`, así que la entrada también tiene que llevar hash).
# Vite escribe el index.html con las rutas exactas; aquí se leen de ahí para no
# depender de un manifest ni de nombres fijos.
_INDEX_HTML = frappe.get_app_path("costeo_yelke", "public", "costeo-app", "index.html")
_BASE = "/assets/costeo_yelke/costeo-app/"


def _spa_assets():
    try:
        with open(_INDEX_HTML, encoding="utf-8") as fh:
            html = fh.read()
    except OSError:
        return _BASE + "assets/index.js", _BASE + "assets/index.css"

    js = re.search(r'<script[^>]+src="([^"]+\.js)"', html)
    css = re.search(r'<link[^>]+href="([^"]+\.css)"', html)

    def _abs(p):
        if not p:
            return None
        p = p.lstrip("/")
        # Vite ya prefija con base (assets/costeo_yelke/costeo-app/...) o deja
        # "assets/..." relativo -- normalizar a ruta absoluta servible.
        if p.startswith("assets/costeo_yelke/"):
            return "/" + p
        return _BASE + p

    return (
        _abs(js.group(1)) if js else _BASE + "assets/index.js",
        _abs(css.group(1)) if css else _BASE + "assets/index.css",
    )


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/costeo-yelke"
        raise frappe.Redirect

    # Herramienta interna: sólo personal interno (System User). Clientes/Website Users = 403.
    if frappe.db.get_value("User", frappe.session.user, "user_type") != "System User":
        raise frappe.PermissionError("Acceso restringido: herramienta de uso interno.")

    context.no_cache = 1
    context.spa_js, context.spa_css = _spa_assets()
