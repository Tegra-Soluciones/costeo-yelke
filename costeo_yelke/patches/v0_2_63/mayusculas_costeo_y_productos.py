"""Catálogo en MAYÚSCULAS (pedido de Yelke, oct 2026): los costeos ya guardados
(título, productos/materiales/servicios en texto libre, descripciones y piezas, ver
uppercase_master.UPPER_COSTEO) y una pasada más sobre los artículos -- el hook los
convierte al guardar desde septiembre, pero algo pudo entrar sin pasar por él."""
from costeo_yelke.overrides.uppercase_master import homologar_costeos, homologar_existentes


def execute():
    homologar_existentes(solo=("Item",))
    homologar_costeos()
