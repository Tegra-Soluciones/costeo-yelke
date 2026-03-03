import frappe


def execute():
    """Ensure OM setup in Purchase Order exists and is ordered correctly."""
    from costeo_yelke.patches.v0_0_4.add_purchase_order_manufacturing_order_fields import (
        execute as patch_v004,
    )
    from costeo_yelke.patches.v0_0_5.add_purchase_order_flexible_tables_html_builder import (
        execute as patch_v005,
    )
    from costeo_yelke.patches.v0_0_6.update_purchase_order_manufacturing_order_layout import (
        execute as patch_v006,
    )
    from costeo_yelke.patches.v0_0_7.reorder_purchase_order_om_fields import (
        execute as patch_v007,
    )
    from costeo_yelke.patches.v0_0_8.fix_purchase_order_om_insert_after_chain import (
        execute as patch_v008,
    )

    patch_v004()
    patch_v005()
    patch_v006()
    patch_v007()
    patch_v008()

    frappe.clear_cache(doctype="Purchase Order")
