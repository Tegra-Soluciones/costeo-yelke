"""Prueba del candado de uso interno (sandbox.local): un Website User de prueba
llama a métodos de costeo_yelke por las 3 rutas de la API. Crea y borra el usuario."""
import secrets, sys, requests, frappe

BASE, HOST = "http://127.0.0.1:8001", "sandbox.local"
EMAIL = "guard-test-portal@example.test"
METODO = "costeo_yelke.api.costeo_api.get_permisos_validacion_yelke"
RUTAS = [f"/api/method/{METODO}", f"/api/v1/method/{METODO}", f"/api/v2/method/{METODO}",
         "/api/v2/method/Costeo/pp_get_default_suppliers?items=[]", "/api/v2/method/Sales%20Order/get_children_for_tree", "/api/method/frappe.auth.get_logged_user"]


def run():
    frappe.init(site="sandbox.local", sites_path="/Users/trabajo/Trabajo/frappe-bench-v15/sites")
    frappe.connect()
    frappe.set_user("Administrator")
    pwd = secrets.token_urlsafe(16)
    try:
        if frappe.db.exists("User", EMAIL):
            frappe.delete_doc("User", EMAIL, force=True)
        u = frappe.get_doc({"doctype": "User", "email": EMAIL, "first_name": "Guard Test",
                            "user_type": "Website User", "send_welcome_email": 0, "new_password": pwd})
        u.insert(ignore_permissions=True)
        frappe.db.commit()
        s = requests.Session()
        s.headers["Host"] = HOST
        r = s.post(BASE + "/api/method/login", data={"usr": EMAIL, "pwd": pwd})
        print("login", r.status_code)
        for ruta in RUTAS:
            r = s.get(BASE + ruta)
            print(f"{r.status_code}  {ruta}  {r.text[:110]!r}")
    finally:
        frappe.delete_doc("User", EMAIL, force=True, ignore_permissions=True)
        frappe.db.commit()
        print("usuario de prueba borrado:", not frappe.db.exists("User", EMAIL))
        frappe.destroy()


run()
