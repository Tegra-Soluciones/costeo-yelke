// =============================================================================
// CÁLCULOS Y HELPERS
// =============================================================================

function get_conversion_factor_t2(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    if (row[DB.T2.SUP_UOM] == row[DB.T2.INT_UOM]) {
        frappe.model.set_value(cdt, cdn, DB.T2.CONV_FACTOR, 1);
        calc_t2_row(frm, cdt, cdn);
    } else {
        frappe.call({
            method: "frappe.client.get",
            args: { doctype: "Item", name: row[DB.T2.ITEM] },
            callback: function(r) {
                let factor = 1;
                if (r.message && r.message.uoms) {
                    let uom = r.message.uoms.find(d => d.uom == row[DB.T2.SUP_UOM]);
                    if (uom) factor = uom.conversion_factor;
                }
                frappe.model.set_value(cdt, cdn, DB.T2.CONV_FACTOR, factor);
                calc_t2_row(frm, cdt, cdn);
            }
        });
    }
}

function calc_t2_row(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let qty = flt(row[DB.T2.INT_QTY]);
    let factor = flt(row[DB.T2.CONV_FACTOR]) || 1;
    let price = flt(row[DB.T2.UNIT_PRICE]);

    let sup_qty = qty / factor;
    let total = sup_qty * price;

    frappe.model.set_value(cdt, cdn, DB.T2.SUP_QTY, sup_qty);
    frappe.model.set_value(cdt, cdn, DB.T2.MIN_SUP_QTY, Math.ceil(sup_qty));
    frappe.model.set_value(cdt, cdn, DB.T2.TOTAL, total);
    
    calculate_aggregates(frm);
}

function calculate_aggregates(frm) {
    let productos = frm.doc[DB.T1.FIELD_NAME] || [];
    let detalles = frm.doc[DB.T2.FIELD_NAME] || [];
    let etapas = frm.doc[DB.T3.FIELD_NAME] || [];

    productos.forEach(producto => {
        let costos = calculate_product_costs(producto, detalles, etapas);
        update_product_costs(frm, producto, costos);
    });
}

function calculate_product_costs(producto, detalles, etapas) {
    let costos = { mat: 0, srv: 0, shp: 0 };
    let producto_detalles = detalles.filter(d => d[DB.T2.FINISHED_ITEM] == producto[DB.T1.ITEM]);
    let producto_etapas = etapas.filter(e => e[DB.T3.PRODUCTO_TERMINADO] == producto[DB.T1.ITEM]);
    
    // Sumar costos de materiales
    producto_detalles.forEach(detalle => {
        let valor = flt(detalle[DB.T2.TOTAL]);
        let tipo = detalle[DB.T2.CONCEPT_TYPE];
        
        if (tipo == "Materia Prima" || !tipo) costos.mat += valor;
        else if (tipo == "Servicio") costos.srv += valor;
        else if (tipo == "Envío") costos.shp += valor;
    });
    
    // Sumar costos de servicios de etapas (esta es la parte clave)
    producto_etapas.forEach(etapa => {
        if (etapa[DB.T3.SERVICIO] && etapa.precio_servicio) {
            costos.srv += flt(etapa.precio_servicio);
        }
    });
    
    // El shipping_cost ya está en el producto, solo lo mantenemos
    costos.shp = flt(producto[DB.T1.SHIP_COST]) || 0;
    
    return costos;
}

function update_product_costs(frm, producto, costos) {
    frappe.model.set_value(producto.doctype, producto.name, DB.T1.MAT_COST, costos.mat);
    frappe.model.set_value(producto.doctype, producto.name, DB.T1.SERV_COST, costos.srv);
    frappe.model.set_value(producto.doctype, producto.name, DB.T1.SHIP_COST, costos.shp);
    calc_t1_row(frm, producto.doctype, producto.name);
}

function calc_t1_row(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let base = flt(row[DB.T1.MAT_COST]) + flt(row[DB.T1.SERV_COST]) + flt(row[DB.T1.SHIP_COST]);
    let overhead = base * (flt(row[DB.T1.OVERHEAD_PCT]) / 100);
    let total = base + overhead;
    
    row[DB.T1.AMOUNT] = base;
    row[DB.T1.OVERHEAD_AMT] = overhead;
    row[DB.T1.TOTAL_COST] = total;
    
    // Si hay margen, recalcular precio de venta
    if (row[DB.T1.MARGIN_PCT] && row[DB.T1.MARGIN_PCT] > 0) {
        recalc_sales_price(frm, cdt, cdn);
    }
    // Si hay precio de venta, recalcular margen
    else if (row[DB.T1.SALES_PRICE] && row[DB.T1.SALES_PRICE] > 0) {
        recalc_margin(frm, cdt, cdn);
    }
    
    frm.refresh_field(DB.T1.FIELD_NAME);
}

function recalc_sales_price(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row[DB.T1.TOTAL_COST] > 0) {
        let margin = flt(row[DB.T1.MARGIN_PCT]) / 100;
        if (margin >= 0 && margin < 1) {
            row[DB.T1.SALES_PRICE] = row[DB.T1.TOTAL_COST] / (1 - margin);
            row[DB.T1.TOTAL_SALES] = row[DB.T1.SALES_PRICE] * flt(row[DB.T1.QTY]);
            frm.refresh_field(DB.T1.FIELD_NAME);
        }
    }
}

function recalc_margin(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row[DB.T1.SALES_PRICE] > 0 && row[DB.T1.TOTAL_COST] > 0) {
        row[DB.T1.MARGIN_PCT] = ((row[DB.T1.SALES_PRICE] - row[DB.T1.TOTAL_COST]) / row[DB.T1.SALES_PRICE]) * 100;
        row[DB.T1.TOTAL_SALES] = row[DB.T1.SALES_PRICE] * flt(row[DB.T1.QTY]);
        frm.refresh_field(DB.T1.FIELD_NAME);
    }
}

function update_select_options(frm) {
    let productos = frm.doc[DB.T1.FIELD_NAME] || [];
    let options = ["", ...new Set(productos.map(r => r[DB.T1.ITEM]).filter(d => d))].join("\n");
    
    if (frm.fields_dict[DB.T2.FIELD_NAME]?.grid) {
        let grid = frm.fields_dict[DB.T2.FIELD_NAME].grid;
        grid.update_docfield_property(DB.T2.FINISHED_ITEM, "options", options);
        let df = grid.docfields.find(d => d.fieldname === DB.T2.FINISHED_ITEM);
        if (df) df.options = options;
    }
}

