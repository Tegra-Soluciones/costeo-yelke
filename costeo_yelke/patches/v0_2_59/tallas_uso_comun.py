"""Marca cuáles tallas son "de uso común".

El desglose por talla del producto base ofrecía las trece tallas del grupo --
de XXS a 8XL-- y en la práctica un pedido normal se mueve entre XS y XL. Las
demás no se van: quedan detrás de "Ver todas las tallas".

Esto es un punto de partida, no una regla del sistema: la marca vive en el
catálogo de Tallas y Yelke la cambia cuando quiera, sin tocar código.
"""
import frappe

# grupo (por su nombre de talla) -> tallas que se ofrecen por defecto
COMUNES = {
    "Tallas por letras": ["XS", "S", "M", "L", "XL"],
    "Pantalones / jeans / prendas inferiores": ["28", "30", "32", "34", "36", "38", "40", "42", "44"],
    "Camisas / prendas superiores numéricas": ["36", "37", "38", "39", "40", "41", "42", "43", "44"],
    "Tallas numéricas": ["2", "4", "6", "8", "10", "12", "14", "16"],
    "Numeración impar": ["3", "5", "7", "9", "11", "13", "15", "17"],
}


def execute():
    frappe.reload_doc("costeo_yelke", "doctype", "talla")
    # has_column lee la lista de columnas de un caché en Redis que durante la
    # migración todavía trae la tabla como estaba ANTES de agregar el campo: sin
    # tirar esa entrada, el patch se sale en seco y queda marcado como aplicado
    # sin haber hecho nada. Pasó exactamente eso en sandbox y en producción.
    frappe.cache.hdel("table_columns", "tabTalla")
    if not frappe.db.has_column("Talla", "uso_comun"):
        return

    marcadas = 0
    for grupo in frappe.get_all("Talla", filters={"is_group": 1}, fields=["name", "talla"]):
        comunes = COMUNES.get(grupo.talla)
        if not comunes:
            continue
        for hija in frappe.get_all("Talla", filters={"parent_talla": grupo.name, "is_group": 0},
                                   fields=["name", "talla", "uso_comun"]):
            quiere = 1 if hija.talla in comunes else 0
            # Solo se encienden las comunes; si alguien ya marcó otra a mano,
            # no se le apaga -- este patch propone, no manda.
            if quiere and not hija.uso_comun:
                frappe.db.set_value("Talla", hija.name, "uso_comun", 1, update_modified=False)
                marcadas += 1

    frappe.db.commit()
    print(f"Tallas marcadas como de uso común: {marcadas}")
