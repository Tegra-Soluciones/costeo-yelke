"""Las imágenes de producto copiadas desde plantillas o respaldos quedaron sin registro
File ligado a su costeo y nadie las podía ver (p. ej. el chaleco 00015). Se ligan todas;
de aquí en adelante lo hace Costeo.on_update (ligar_imagenes_al_costeo)."""
import frappe

from costeo_yelke.costeo_yelke.doctype.costeo.costeo import ligar_imagenes_al_costeo


def execute():
    for nombre in frappe.get_all("Costeo Producto", filters={"image": ["is", "set"], "parenttype": "Costeo"},
                                 distinct=True, pluck="parent"):
        if frappe.db.exists("Costeo", nombre):
            ligar_imagenes_al_costeo(frappe.get_doc("Costeo", nombre))
