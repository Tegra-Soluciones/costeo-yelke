import frappe

# Mismo criterio de acceso que costeo_yelke.py (el SPA): el manual documenta una
# herramienta de uso interno, así que se protege igual -- adentro del sistema,
# no público. Sin sesión -> a login; con sesión pero de un Website User (ej. un
# cliente con acceso de portal) -> 403, igual que el resto de la app.


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/manual-costeo"
        raise frappe.Redirect

    if frappe.db.get_value("User", frappe.session.user, "user_type") != "System User":
        raise frappe.PermissionError("Acceso restringido: manual de uso interno.")

    context.no_cache = 1
