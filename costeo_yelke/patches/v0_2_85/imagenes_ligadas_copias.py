"""Segunda pasada de v0_2_84: costeos que ya tenían la misma imagen ligada con otro
nombre (Frappe no liga duplicados) ahora apuntan a esa copia."""
from costeo_yelke.patches.v0_2_84.imagenes_ligadas_al_costeo import execute  # noqa: F401
