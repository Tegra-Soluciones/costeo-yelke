// =============================================================================
// CREACIÓN DE SUBCONTRACTING BOMs
// =============================================================================

function create_subcontracting_boms(frm) {
    if (frm.is_new()) {
        show_error('Debes guardar el documento antes de crear Subcontracting BOMs');
        return;
    }
    
    let productos = frm.doc[DB.T1.FIELD_NAME] || [];
    let todas_etapas = frm.doc[DB.T3.FIELD_NAME] || [];
    
    if (!validate_bom_prerequisites(productos, todas_etapas)) return;
    
    let total_subcontracting = count_subcontracting_boms(productos, todas_etapas);
    
    frappe.confirm(
        get_subcontracting_confirmation_message(productos, total_subcontracting),
        () => {
            frappe.show_alert({ message: 'Iniciando creación de Subcontracting BOMs...', indicator: 'blue' });
            process_all_subcontracting_boms(frm, productos, todas_etapas);
        }
    );
}

function count_subcontracting_boms(productos, todas_etapas) {
    let total = 0;
    productos.forEach(producto => {
        let etapas = todas_etapas.filter(e => e[DB.T3.PRODUCTO_TERMINADO] === producto[DB.T1.ITEM]);
        total += etapas.length;
    });
    return total;
}

function get_subcontracting_confirmation_message(productos, total) {
    return `¿Deseas crear Subcontracting BOMs automáticamente?<br><br>
        <b>Productos a procesar:</b> ${productos.length}<br>
        <b>Subcontracting BOMs a crear:</b> ${total}`;
}

function process_all_subcontracting_boms(frm, productos, todas_etapas) {
    let sequential_tasks = build_subcontracting_tasks(productos, todas_etapas);
    let errors = [];
    
    process_subcontracting_boms_sequentially(sequential_tasks, 0, 0, errors, (total_created) => {
        show_completion_message(total_created, errors, 'Subcontracting BOMs Creadas');
    });
}

function build_subcontracting_tasks(productos, todas_etapas) {
    let tasks = [];
    
    productos.forEach(producto => {
        let finished_item = producto[DB.T1.ITEM];
        let etapas = todas_etapas.filter(e => e[DB.T3.PRODUCTO_TERMINADO] === finished_item);
        
        if (etapas.length === 0) return;
        
        let etapas_ordenadas = etapas.slice().sort((a, b) => parseInt(a[DB.T3.ETAPA]) - parseInt(b[DB.T3.ETAPA]));
        
        etapas_ordenadas.forEach((etapa_config, index) => {
            let task = build_single_subcontracting_task(etapa_config, index, etapas_ordenadas, finished_item);
            if (task) tasks.push(task);
        });
    });
    
    return tasks;
}

function build_single_subcontracting_task(etapa_config, index, etapas_ordenadas, finished_item) {
    let etapa_num = etapa_config[DB.T3.ETAPA];
    let servicio = etapa_config[DB.T3.SERVICIO];
    let subensamblaje = etapa_config[DB.T3.SUBENSAMBLAJE];
    
    let es_ultima_etapa = (index === etapas_ordenadas.length - 1);
    let finished_good = es_ultima_etapa ? finished_item : subensamblaje;
    
    if (!finished_good || !servicio) return null;
    
    return {
        finished_good,
        service_item: servicio,
        etapa_num,
        producto_terminado: finished_item
    };
}

function process_subcontracting_boms_sequentially(tasks, index, total_created, errors, final_callback) {
    if (index >= tasks.length) {
        final_callback(total_created);
        return;
    }
    
    let task = tasks[index];
    
    check_and_create_subcontracting_bom(
        task.finished_good,
        task.service_item,
        task.etapa_num,
        task.producto_terminado,
        (success) => {
            if (success) total_created++;
            
            setTimeout(() => {
                process_subcontracting_boms_sequentially(tasks, index + 1, total_created, errors, final_callback);
            }, 1500);
        }
    );
}

function check_and_create_subcontracting_bom(finished_good, service_item, etapa, producto_terminado, callback) {
    if (!service_item) {
        show_error(`El servicio para ${finished_good} está vacío. Verifica la configuración de etapas.`);
        callback(false);
        return;
    }
    
    validate_service_item(service_item, (is_valid, service_uom) => {
        if (!is_valid) {
            callback(false);
            return;
        }
        
        check_existing_subcontracting_bom(finished_good, (exists) => {
            if (exists) {
                callback(false);
            } else {
                create_single_subcontracting_bom(finished_good, service_item, service_uom, etapa, callback);
            }
        });
    });
}

function validate_service_item(service_item, callback) {
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "Item",
            filters: { name: service_item },
            fieldname: ["name", "disabled", "is_stock_item", "stock_uom"]
        },
        callback: (r) => {
            if (!r.message) {
                show_error(`El servicio "${service_item}" no existe en el sistema`);
                callback(false);
                return;
            }
            
            if (r.message.disabled) {
                show_error(`El servicio "${service_item}" está deshabilitado`);
                callback(false);
                return;
            }
            
            if (r.message.is_stock_item) {
                show_error(`El item "${service_item}" es un item de stock. Para Subcontracting BOM debe ser un servicio (no mantiene stock)`);
                callback(false);
                return;
            }
            
            callback(true, r.message.stock_uom);
        },
        error: () => {
            show_error(`No se pudo verificar el servicio "${service_item}"`);
            callback(false);
        }
    });
}

function check_existing_subcontracting_bom(finished_good, callback) {
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Subcontracting BOM",
            filters: { finished_good: finished_good },
            fields: ["name"],
            limit: 1
        },
        callback: (r) => {
            if (r.message && r.message.length > 0) {
                show_alert(`Subcontracting BOM ya existe: ${r.message[0].name}`, 'orange');
                callback(true);
            } else {
                callback(false);
            }
        },
        error: () => callback(false)
    });
}

function create_single_subcontracting_bom(finished_good, service_item, service_uom, etapa, callback) {
    get_finished_good_bom(finished_good, (bom_name) => {
        if (!bom_name) {
            show_error(`No existe un BOM validado para "${finished_good}". Debes crear los BOMs normales primero.`);
            callback(false);
            return;
        }
        
        get_item_uom(finished_good, (finished_good_uom) => {
            insert_subcontracting_bom(finished_good, bom_name, finished_good_uom, service_item, service_uom, callback);
        });
    });
}

function get_finished_good_bom(finished_good, callback) {
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "BOM",
            filters: {
                item: finished_good,
                is_active: 1,
                is_default: 1,
                docstatus: 1
            },
            fields: ["name"],
            limit: 1
        },
        callback: (r) => {
            callback(r.message && r.message.length > 0 ? r.message[0].name : null);
        },
        error: () => callback(null)
    });
}

function insert_subcontracting_bom(finished_good, bom_name, finished_good_uom, service_item, service_uom, callback) {
    let conversion_factor = service_uom !== finished_good_uom ? 1 : 1;
    
    frappe.call({
        method: "frappe.client.insert",
        args: {
            doc: {
                doctype: "Subcontracting BOM",
                finished_good: finished_good,
                finished_good_bom: bom_name,
                finished_good_uom: finished_good_uom,
                finished_good_qty: 1,
                is_active: 1,
                service_item: service_item,
                service_item_qty: 1,
                service_item_uom: service_uom || "Nos.",
                conversion_factor: conversion_factor
            }
        },
        callback: (r) => {
            if (r.message) {
                show_alert(`Subcontracting BOM creada: ${r.message.name} - ${finished_good}`, 'green');
                callback(true);
            }
        },
        error: (r) => {
            let error_msg = get_error_message(r);
            frappe.msgprint({
                title: 'Error al crear Subcontracting BOM',
                indicator: 'red',
                message: `Item: ${finished_good}<br>Servicio: ${service_item}<br>BOM: ${bom_name}<br>Error: ${error_msg}`
            });
            callback(false);
        }
    });
}

