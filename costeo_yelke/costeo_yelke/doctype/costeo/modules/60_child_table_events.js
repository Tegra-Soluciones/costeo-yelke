// =============================================================================
// EVENTOS DE TABLAS
// =============================================================================

frappe.ui.form.on(DB.T1.DOCTYPE_ID, {
    [DB.T1.ITEM]: (frm, cdt, cdn) => { 
        update_select_options(frm);
        render_tree_view(frm);
        let row = locals[cdt][cdn];
        if (!row || !row[DB.T1.ITEM]) {
            cleanup_related_rows(frm);
        }
    },
    [DB.T1.QTY]: (frm, cdt, cdn) => { 
        calc_t1_row(frm, cdt, cdn); 
        render_tree_view(frm); 
    },
    [DB.T1.OVERHEAD_PCT]: (frm, cdt, cdn) => calc_t1_row(frm, cdt, cdn),
    [DB.T1.MARGIN_PCT]: (frm, cdt, cdn) => recalc_sales_price(frm, cdt, cdn),
    [DB.T1.SALES_PRICE]: (frm, cdt, cdn) => recalc_margin(frm, cdt, cdn),
    // NUEVO: Evento para shipping_cost
    [DB.T1.SHIP_COST]: (frm, cdt, cdn) => {
        calc_t1_row(frm, cdt, cdn);
        render_tree_view(frm);
    }
});

frappe.ui.form.on(DB.T2.DOCTYPE_ID, {
    form_render: (frm) => update_select_options(frm),
    
    [DB.T2.ITEM]: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row[DB.T2.ITEM]) return;
        
        frappe.db.get_value('Item', row[DB.T2.ITEM], 'stock_uom', (r) => {
            if (r && r.stock_uom) {
                frappe.model.set_value(cdt, cdn, DB.T2.INT_UOM, r.stock_uom);
            }
        });
    },
    
    [DB.T2.SUPPLIER]: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row[DB.T2.ITEM] || !row[DB.T2.SUPPLIER]) return;
        
        fetch_item_price(row, cdt, cdn, frm);
    },
    
    [DB.T2.INT_QTY]: (frm, cdt, cdn) => calc_t2_row(frm, cdt, cdn),
    [DB.T2.UNIT_PRICE]: (frm, cdt, cdn) => calc_t2_row(frm, cdt, cdn)
});

frappe.ui.form.on(DB.T3.DOCTYPE_ID, {
    [DB.T3.SERVICIO]: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row[DB.T3.PRODUCTO_TERMINADO] || !row[DB.T3.ETAPA] || !row[DB.T3.SERVICIO]) return;
        
        let servicio_existente = find_existing_service(frm, row);
        
        if (servicio_existente && servicio_existente !== row[DB.T3.SERVICIO]) {
            show_error(`El producto ${row[DB.T3.PRODUCTO_TERMINADO]} en la Etapa ${row[DB.T3.ETAPA]} ya tiene el servicio "${servicio_existente}". Solo un servicio por etapa.`);
            frappe.model.set_value(cdt, cdn, DB.T3.SERVICIO, '');
        }
    }
});

function find_existing_service(frm, current_row) {
    let etapas = frm.doc[DB.T3.FIELD_NAME] || [];
    
    for (let etapa of etapas) {
        if (etapa.name !== current_row.name && 
            etapa[DB.T3.PRODUCTO_TERMINADO] === current_row[DB.T3.PRODUCTO_TERMINADO] &&
            etapa[DB.T3.ETAPA] === current_row[DB.T3.ETAPA] && 
            etapa[DB.T3.SERVICIO]) {
            return etapa[DB.T3.SERVICIO];
        }
    }
    
    return null;
}

function fetch_item_price(row, cdt, cdn, frm) {
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Item Price",
            filters: { 
                item_code: row[DB.T2.ITEM], 
                supplier: row[DB.T2.SUPPLIER], 
                buying: 1 
            },
            fields: ["price_list_rate", "uom"], 
            limit: 1
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                let data = r.message[0];
                frappe.model.set_value(cdt, cdn, DB.T2.UNIT_PRICE, data.price_list_rate);
                frappe.model.set_value(cdt, cdn, DB.T2.SUP_UOM, data.uom);
                get_conversion_factor_t2(frm, cdt, cdn);
            } else {
                show_alert('No hay lista de precios para este proveedor', 'orange');
            }
        }
    });
}
