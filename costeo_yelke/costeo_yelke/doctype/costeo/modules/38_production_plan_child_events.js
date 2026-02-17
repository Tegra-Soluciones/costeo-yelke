// =============================================================================
// EVENTOS DE CHILD TABLES DE PLAN DE PRODUCCION
// =============================================================================

frappe.ui.form.on("Production Plan Item", {
    item_code(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.item_code) return;

        frappe.call({
            method: "erpnext.manufacturing.doctype.production_plan.production_plan.get_item_data",
            args: {
                item_code: row.item_code
            },
            callback: function(r) {
                const data = r.message || {};
                Object.keys(data).forEach(key => frappe.model.set_value(cdt, cdn, key, data[key]));
            }
        });
    }
});

frappe.ui.form.on("Material Request Plan Item", {
    item_code(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.item_code) return;

        const supplier_map = build_raw_material_supplier_map(frm);
        if (supplier_map[row.item_code]) {
            frappe.model.set_value(cdt, cdn, "supplier", supplier_map[row.item_code]);
        }
    },

    warehouse(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.warehouse || !row.item_code || !frm.doc.company) return;

        frappe.call({
            method: "erpnext.manufacturing.doctype.production_plan.production_plan.get_bin_details",
            args: {
                row: row,
                company: frm.doc.company,
                for_warehouse: row.warehouse
            },
            callback: function(r) {
                if (r.message && r.message.length > 0) {
                    const details = r.message[0];
                    frappe.model.set_value(cdt, cdn, {
                        projected_qty: details.projected_qty,
                        actual_qty: details.actual_qty
                    });
                }
            }
        });
    },

    material_request_type(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.from_warehouse && row.material_request_type !== "Material Transfer") {
            frappe.model.set_value(cdt, cdn, "from_warehouse", "");
        }
    }
});

frappe.ui.form.on("Production Plan Sales Order", {
    sales_order(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        const sales_order = row.sales_order;
        if (!sales_order) return;

        frappe.call({
            method: PP_API.VALIDATE_SALES_ORDER,
            args: {
                doc: frm.doc,
                sales_order: sales_order
            },
            callback: function() {
                frappe.call({
                    method: "erpnext.manufacturing.doctype.production_plan.production_plan.get_so_details",
                    args: { sales_order: sales_order },
                    callback: function(r) {
                        const data = r.message || {};
                        frappe.model.set_value(cdt, cdn, "sales_order_date", data.transaction_date);
                        frappe.model.set_value(cdt, cdn, "customer", data.customer);
                        frappe.model.set_value(cdt, cdn, "grand_total", data.grand_total);
                    }
                });
            }
        });
    }
});

frappe.ui.form.on("Production Plan Sub Assembly Item", {
    fg_warehouse(frm, cdt, cdn) {
        erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "sub_assembly_items", "fg_warehouse");

        const row = locals[cdt][cdn];
        if (!row.fg_warehouse || !row.production_item) return;

        frappe.call({
            method: "erpnext.manufacturing.doctype.production_plan.production_plan.get_bin_details",
            args: {
                row: {
                    item_code: row.production_item,
                    warehouse: row.fg_warehouse
                },
                company: frm.doc.company,
                for_warehouse: row.fg_warehouse
            },
            callback: function(r) {
                if (r.message && r.message.length > 0) {
                    frappe.model.set_value(cdt, cdn, "actual_qty", r.message[0].actual_qty);
                }
            }
        });
    }
});
