import frappe


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/costeo-yelke"
        raise frappe.Redirect

    # Herramienta interna: sólo personal interno (System User). Clientes/Website Users = 403.
    if frappe.db.get_value("User", frappe.session.user, "user_type") != "System User":
        raise frappe.PermissionError("Acceso restringido: herramienta de uso interno.")

    context.no_cache = 1
