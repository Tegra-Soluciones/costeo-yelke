// =============================================================================
// VALIDACIONES
// =============================================================================

function validate_at_least_one_product_to_produce(frm) {
    const has_products = (frm.doc[DB.T1.FIELD_NAME] || []).some(row => {
        return row[DB.T1.ITEM] && flt(row[DB.T1.QTY]) > 0;
    });

    if (!has_products) {
        show_error("Debes capturar al menos un producto terminado con cantidad a producir mayor a 0.");
        return false;
    }

    return true;
}

function validate_unique_services_per_stage(frm) {
    let etapas = frm.doc[DB.T3.FIELD_NAME] || [];
    let servicios_por_producto_etapa = {};
    
    for (let row of etapas) {
        let producto = row[DB.T3.PRODUCTO_TERMINADO];
        let etapa = row[DB.T3.ETAPA];
        let servicio = row[DB.T3.SERVICIO];
        
        if (producto && etapa && servicio) {
            let key = `${producto}_${etapa}`;
            
            if (servicios_por_producto_etapa[key] && servicios_por_producto_etapa[key] !== servicio) {
                frappe.msgprint({
                    title: 'Error de Validación',
                    indicator: 'red',
                    message: `El producto ${producto} en la Etapa ${etapa} tiene más de un servicio asignado. Solo se permite un servicio por etapa.`
                });
                return false;
            }
            servicios_por_producto_etapa[key] = servicio;
        }
    }
    
    return true;
}
