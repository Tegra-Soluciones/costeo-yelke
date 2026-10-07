"""Bank Account: en México no se usan IBAN ni código de sucursal (se usa la CLABE, v0_2_48)."""
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def execute():
    for campo in ("iban", "branch_code"):
        make_property_setter("Bank Account", campo, "hidden", 1, "Check", validate_fields_for_doctype=False)
