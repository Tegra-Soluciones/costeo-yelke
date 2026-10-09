"""Correo y teléfono de contacto de las compañías de Yelke, para el encabezado y el
pie de los formatos de impresión (impresion.datos_empresa). Solo llena lo que esté
vacío: no pisa lo que ya se haya capturado en la compañía (SUS INDUSTRIAL ya trae
los suyos)."""
import frappe

CORREO = "jmcuellar@yelke.com.mx"
TELEFONO = "4423481220"


def execute():
    for c in frappe.get_all("Company", filters={"company_name": ["like", "%YELKE%"]},
                            fields=["name", "email", "phone_no"]):
        cambios = {}
        if not c.email:
            cambios["email"] = CORREO
        if not c.phone_no:
            cambios["phone_no"] = TELEFONO
        if cambios:
            frappe.db.set_value("Company", c.name, cambios, update_modified=False)
