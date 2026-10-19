"""Delegación temporal de las aprobaciones de Dirección (docs/plan-panel-direccion.md,
Fase 7). Las reglas viven en api/delegacion.py; aquí solo lo que el documento debe
cumplir sin importar por dónde se guarde."""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate


class DelegacionAprobacion(Document):
	def validate(self):
		if self.de_usuario == self.a_usuario:
			frappe.throw(_("No puedes delegarte a ti mismo."))
		if getdate(self.desde) > getdate(self.hasta):
			frappe.throw(_("La fecha 'Desde' no puede ser posterior a 'Hasta'."))
		if self.is_new() and getdate(self.hasta) < getdate(nowdate()):
			frappe.throw(_("La delegación ya habría terminado: revisa las fechas."))
		if not frappe.db.get_value("User", {"name": self.a_usuario, "enabled": 1, "user_type": "System User"}):
			frappe.throw(_("{0} no es un usuario activo del sistema.").format(self.a_usuario))
		if not self.cancelada:
			cruzada = frappe.db.exists("Delegacion Aprobacion", {
				"name": ["!=", self.name or ""], "de_usuario": self.de_usuario, "cancelada": 0,
				"desde": ["<=", self.hasta], "hasta": [">=", self.desde],
			})
			if cruzada:
				frappe.throw(_("Ya hay una delegación en esas fechas. Termínala antes de crear otra."))
