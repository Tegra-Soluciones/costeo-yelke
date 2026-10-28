"""Doble captura de datos sensibles (pedido de Yelke, Juan):

1. RFC de clientes y proveedores: obligatorio, se escribe dos veces.
2. Cuentas de banco de clientes y proveedores (número de cuenta, CLABE, tarjeta):
   se escriben dos veces.
(3. El precio de venta del costeo se confirma en el SPA, CosteoDetailPage.)

En pantalla la primera captura se oculta (como una contraseña) y la segunda se ve;
aquí, en el servidor, se exige que coincidan para que no se pueda saltar desde el
escritorio de ERPNext ni desde la API. Se pide al DAR DE ALTA y cada vez que alguien
CAMBIA el dato. Los campos de confirmación (patch v0_2_62) se vacían antes de
guardar: nunca queda una segunda copia del dato.

Solo aplica a lo que una persona captura (hay una petición HTTP): una importación
de datos, un patch o un proceso automático no traen la confirmación y no se frenan.
"""
import re

import frappe
from frappe import _

# RFC: 3 letras (moral) o 4 (física) + fecha AAMMDD + homoclave de 3. Los genéricos
# del SAT (XAXX010101000 público en general, XEXX010101000 extranjero) también pasan.
RFC = re.compile(r"[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}")
PARTES_CON_CUENTA = ("Customer", "Supplier")
CAMPOS_CUENTA = (
    ("bank_account_no", "confirmar_cuenta", _("número de cuenta")),
    ("cuenta_clabe", "confirmar_clabe", _("cuenta CLABE")),
    ("numero_tarjeta", "confirmar_tarjeta", _("número de tarjeta")),
)


def _captura_de_persona(doc):
    if doc.flags.get("ignore_confirmacion"):
        return False
    if frappe.flags.in_import or frappe.flags.in_patch or frappe.flags.in_install or frappe.flags.in_migrate:
        return False
    return bool(getattr(frappe.local, "request", None))


def _nuevo_o_cambiado(doc, campo):
    return doc.is_new() or doc.has_value_changed(campo)


def _rfc(valor):
    # Sin espacios, guiones ni puntos: «MOR-100802-RT9» es el mismo RFC.
    return re.sub(r"[\s\-.]", "", valor or "").upper()


def _cuenta(valor):
    return re.sub(r"[\s-]", "", valor or "")


def validar_rfc(doc, method=None):
    """validate de Customer y Supplier."""
    doc.tax_id = _rfc(doc.get("tax_id")) or None
    confirmacion = _rfc(doc.get("confirmar_rfc"))
    doc.confirmar_rfc = None  # nunca se guarda
    if not _captura_de_persona(doc) or not _nuevo_o_cambiado(doc, "tax_id"):
        return
    etiqueta = _("del cliente") if doc.doctype == "Customer" else _("del proveedor")
    if not doc.tax_id:
        frappe.throw(_("El RFC {0} es obligatorio.").format(etiqueta), title=_("Falta el RFC"))
    if not RFC.fullmatch(doc.tax_id):
        frappe.throw(_("El RFC «{0}» no tiene un formato válido (12 caracteres persona moral, 13 persona física; "
                       "extranjero sin RFC: XEXX010101000).").format(doc.tax_id), title=_("RFC inválido"))
    if confirmacion != doc.tax_id:
        frappe.throw(_("Las dos capturas del RFC no coinciden. Escríbelo de nuevo en «Confirma el RFC»."),
                     title=_("Confirma el RFC"))


def validar_cuenta(doc, method=None):
    """validate de Bank Account: solo las cuentas de clientes y proveedores (las de la
    propia empresa no las pidió Yelke)."""
    confirmaciones = {}
    for campo, confirmar, _etq in CAMPOS_CUENTA:
        if doc.meta.has_field(confirmar):
            confirmaciones[campo] = _cuenta(doc.get(confirmar))
            doc.set(confirmar, None)  # nunca se guarda
    if doc.get("party_type") not in PARTES_CON_CUENTA or not _captura_de_persona(doc):
        return
    for campo, confirmar, etiqueta in CAMPOS_CUENTA:
        if campo not in confirmaciones or not doc.get(campo) or not _nuevo_o_cambiado(doc, campo):
            continue
        if confirmaciones[campo] != _cuenta(doc.get(campo)):
            frappe.throw(_("Las dos capturas del {0} no coinciden. Escríbelo de nuevo en su confirmación.").format(etiqueta),
                         title=_("Confirma la cuenta"))
