// =============================================================================
// CREACIÓN DE BOMs
// =============================================================================

function create_boms_from_costeo(frm) {
    if (frm.is_new()) {
        show_error('Debes guardar el documento antes de crear BOMs');
        return;
    }
    
    let productos = frm.doc[DB.T1.FIELD_NAME] || [];
    let materiales = frm.doc[DB.T2.FIELD_NAME] || [];
    let todas_etapas = frm.doc[DB.T3.FIELD_NAME] || [];
    
    if (!validate_bom_prerequisites(productos, todas_etapas)) return;
    
    frappe.confirm(
        get_bom_confirmation_message(productos, todas_etapas, materiales),
        () => {
            frappe.show_alert({ message: 'Iniciando creación de BOMs...', indicator: 'blue' });
            process_all_boms(frm, productos, materiales, todas_etapas);
        }
    );
}

function validate_bom_prerequisites(productos, etapas) {
    if (productos.length === 0) {
        show_warning('No hay productos terminados para procesar');
        return false;
    }
    
    if (etapas.length === 0) {
        show_warning('No hay etapas configuradas');
        return false;
    }
    
    return true;
}

function get_bom_confirmation_message(productos, etapas, materiales) {
    return `¿Deseas crear BOMs automáticamente para todos los productos?<br><br>
        <b>Productos a procesar:</b> ${productos.length}<br>
        <b>Etapas configuradas:</b> ${etapas.length}<br>
        <b>Materiales totales:</b> ${materiales.length}`;
}

function process_all_boms(frm, productos, materiales, todas_etapas) {
    let sequential_tasks = build_bom_tasks(productos, materiales, todas_etapas);
    let errors = [];
    
    process_boms_sequentially(sequential_tasks, 0, 0, errors, (total_created) => {
        show_completion_message(total_created, errors, 'BOMs Creadas');
    });
}

function build_bom_tasks(productos, materiales, todas_etapas) {
    let tasks = [];
    
    productos.forEach(producto => {
        let finished_item = producto[DB.T1.ITEM];
        let etapas = todas_etapas.filter(e => e[DB.T3.PRODUCTO_TERMINADO] === finished_item);
        
        if (etapas.length === 0) return;
        
        let materiales_producto = materiales.filter(m => m[DB.T2.FINISHED_ITEM] === finished_item);
        let etapas_ordenadas = etapas.slice().sort((a, b) => parseInt(a[DB.T3.ETAPA]) - parseInt(b[DB.T3.ETAPA]));
        
        etapas_ordenadas.forEach((etapa_config, index) => {
            let task = build_single_bom_task(etapa_config, index, etapas_ordenadas, materiales_producto, finished_item);
            if (task) tasks.push(task);
        });
    });
    
    return tasks;
}

function build_single_bom_task(etapa_config, index, etapas_ordenadas, materiales_producto, finished_item) {
    let etapa_num = etapa_config[DB.T3.ETAPA];
    let subensamblaje = etapa_config[DB.T3.SUBENSAMBLAJE];
    let es_ultima_etapa = (index === etapas_ordenadas.length - 1);
    
    let bom_item = es_ultima_etapa ? finished_item : subensamblaje;
    if (!bom_item) return null;
    
    let items_bom = [];
    
    if (index > 0) {
        let subensamblaje_anterior = etapas_ordenadas[index - 1][DB.T3.SUBENSAMBLAJE];
        if (subensamblaje_anterior) {
            items_bom.push({ item_code: subensamblaje_anterior, qty: 1, source_warehouse: '' });
        }
    }
    
    let materiales_etapa = materiales_producto.filter(m => m[DB.T2.ETAPA] == etapa_num);
    materiales_etapa.forEach(m => {
        items_bom.push({
            item_code: m[DB.T2.ITEM],
            qty: flt(m[DB.T2.INT_QTY]) || 1,
            source_warehouse: ''
        });
    });
    
    if (items_bom.length === 0) return null;
    
    return { bom_item, etapa_num, items_bom, finished_item };
}

function process_boms_sequentially(tasks, index, total_created, errors, final_callback) {
    if (index >= tasks.length) {
        final_callback(total_created);
        return;
    }
    
    let task = tasks[index];
    
    check_and_create_bom(task.bom_item, task.etapa_num, task.items_bom, task.finished_item, (success) => {
        if (success) total_created++;
        
        setTimeout(() => {
            process_boms_sequentially(tasks, index + 1, total_created, errors, final_callback);
        }, 1000);
    });
}

function check_and_create_bom(item, etapa, items_bom, producto_terminado, callback) {
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "BOM",
            filters: { item: item, docstatus: ["in", [0, 1]] },
            fields: ["name", "docstatus"],
            limit: 1
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                show_alert(`BOM ya existe: ${r.message[0].name} - ${item}`, 'orange');
                callback(false);
            } else {
                create_single_bom(item, etapa, items_bom, callback);
            }
        },
        error: () => create_single_bom(item, etapa, items_bom, callback)
    });
}

function create_single_bom(item, etapa, items_bom, callback) {
    get_item_uom(item, (item_uom) => {
        get_items_with_uom(items_bom, (bom_items_formatted) => {
            insert_bom(item, bom_items_formatted, etapa, callback);
        });
    });
}

function get_item_uom(item, callback) {
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "Item",
            filters: { name: item },
            fieldname: ["stock_uom"]
        },
        callback: (r) => callback(r.message ? r.message.stock_uom : "Unidad"),
        error: () => callback("Unidad")
    });
}

function get_items_with_uom(items_bom, callback) {
    let promises = items_bom.map(item_data => {
        return new Promise((resolve) => {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Item",
                    filters: { name: item_data.item_code },
                    fieldname: ["stock_uom"]
                },
                callback: (r) => {
                    let stock_uom = r.message ? r.message.stock_uom : "Unidad";
                    resolve({
                        item_code: item_data.item_code,
                        qty: item_data.qty,
                        uom: stock_uom,
                        stock_uom: stock_uom,
                        rate: 0,
                        source_warehouse: item_data.source_warehouse || ''
                    });
                },
                error: () => resolve({
                    item_code: item_data.item_code,
                    qty: item_data.qty,
                    uom: "Unidad",
                    stock_uom: "Unidad",
                    rate: 0,
                    source_warehouse: item_data.source_warehouse || ''
                })
            });
        });
    });
    
    Promise.all(promises).then(callback);
}

function insert_bom(item, items, etapa, callback) {
    frappe.call({
        method: "frappe.client.insert",
        args: {
            doc: {
                doctype: "BOM",
                item: item,
                quantity: 1,
                is_active: 1,
                is_default: 1,
                with_operations: 0,
                rm_cost_as_per: "Price List",
                buying_price_list: "Compra estandar",
                items: items
            }
        },
        callback: (r) => {
            if (r.message) {
                submit_bom(r.message, item, etapa, callback);
            }
        },
        error: () => {
            show_alert(`Error creando BOM para ${item}`, 'red');
            callback(false);
        }
    });
}

function submit_bom(bom_doc, item, etapa, callback) {
    frappe.call({
        method: "frappe.client.submit",
        args: { doc: bom_doc },
        callback: (r) => {
            if (r.message) {
                show_alert(`BOM creada y validada: ${bom_doc.name} - ${item} (Etapa ${etapa})`, 'green');
                callback(true);
            }
        },
        error: () => {
            show_alert(`BOM creada pero no se pudo validar: ${bom_doc.name}`, 'orange');
            callback(true);
        }
    });
}

