# Copyright (c) 2026, Yelke and contributors

from frappe.model.document import Document


class OrdenManufactura(Document):
	"""Orden de manufactura GENERAL de un producto base del costeo (su variante de talla
	entra como tallas). De aquí se arma la OM de cada orden de maquila: la info general y
	las tallas para todos los talleres; procesos, observaciones, tablas de medidas y
	archivos solo para los talleres a los que se asignaron (ver api/om_general.py)."""
	pass
