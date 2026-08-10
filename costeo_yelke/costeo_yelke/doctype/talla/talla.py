import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet


class Talla(NestedSet):
	nsm_parent_field = "parent_talla"

	def autoname(self):
		# Mismo criterio que Chart of Accounts (account_name + abreviado de la compañía):
		# el nombre visible ("S", "36", "Tallas por letras") se repite entre ramas (Dama vs.
		# Caballero, o incluso entre Pantalones y Camisas de Caballero), así que se vuelve
		# único agregando la abreviatura del grupo padre inmediato -- una sola compañía no
		# alcanza aquí porque no hay "compañía", el padre hace ese papel.
		if self.parent_talla:
			parent_abbr = frappe.db.get_value("Talla", self.parent_talla, "abreviatura") or self.parent_talla
			self.name = f"{self.talla} - {parent_abbr}"
		else:
			self.name = self.talla

	def validate(self):
		if self.is_group and not self.abreviatura:
			frappe.throw(_("Los grupos de talla necesitan una Abreviatura (la usan sus hijos para nombrarse sin chocar)."))
