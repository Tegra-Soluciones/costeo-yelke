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

// =============================================================================
// REINICIO DE BOMs Y SUBCONTRACTING BOMs
// =============================================================================

function reset_boms_and_subcontracting(frm) {
    if (frm.is_new()) {
        show_error('Debes guardar el documento antes de reiniciar BOMs');
        return;
    }

    let targets = get_reset_bom_targets(frm);
    if (!targets.bom_items.length && !targets.subcontracting_items.length) {
        show_warning('No hay items configurados para reiniciar BOMs');
        return;
    }

    frappe.confirm(
        get_reset_bom_confirmation_message(targets),
        () => {
            frappe.show_alert({ message: 'Buscando BOMs para reiniciar...', indicator: 'blue' });
            fetch_subcontracting_boms_for_reset(targets, (subcontracting_docs) => {
                fetch_boms_for_reset(targets, (bom_docs) => {
                    const ordered_subcontracting_docs = sort_docs_by_creation_desc(subcontracting_docs);
                    const ordered_bom_docs = sort_docs_by_creation_desc(bom_docs);
                    let result = {
                        canceled_boms: 0,
                        deleted_boms: 0,
                        deleted_subcontracting: 0,
                        errors: []
                    };

                    // Importante: borrar primero Subcontracting BOMs para liberar referencia a BOM.
                    delete_docs_sequentially("Subcontracting BOM", ordered_subcontracting_docs, 0, result, () => {
                        process_bom_reset_sequence(ordered_bom_docs, result, () => {
                            reset_bom_references_in_costeo(frm, targets);
                            show_reset_bom_summary(result, ordered_bom_docs.length, ordered_subcontracting_docs.length);
                        });
                    });
                });
            });
        }
    );
}

function get_reset_bom_targets(frm) {
    let productos = frm.doc[DB.T1.FIELD_NAME] || [];
    let materiales = frm.doc[DB.T2.FIELD_NAME] || [];
    let etapas = frm.doc[DB.T3.FIELD_NAME] || [];

    let bom_tasks = build_bom_tasks(productos, materiales, etapas);
    let subcontracting_tasks = build_subcontracting_tasks(productos, etapas);

    let bom_items = Array.from(new Set(bom_tasks.map(t => t.bom_item).filter(Boolean)));
    let subcontracting_items = Array.from(new Set(subcontracting_tasks.map(t => t.finished_good).filter(Boolean)));
    let reset_items = Array.from(new Set([...bom_items, ...subcontracting_items]));

    return { bom_items, subcontracting_items, reset_items };
}

function get_reset_bom_confirmation_message(targets) {
    return `Se eliminarán BOMs y Subcontracting BOMs de los items configurados en este Costeo.<br><br>
        <b>Items con BOM:</b> ${targets.bom_items.length}<br>
        <b>Items con Subcontracting BOM:</b> ${targets.subcontracting_items.length}<br><br>
        Esta acción busca reiniciar esta parte para volver a generarla.`;
}

function fetch_boms_for_reset(targets, callback) {
    if (!targets.bom_items.length) {
        callback([]);
        return;
    }

    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "BOM",
            filters: {
                item: ["in", targets.bom_items],
                docstatus: ["in", [0, 1]],
                is_active: 1,
                is_default: 1
            },
            fields: ["name", "item", "docstatus", "creation"],
            limit_page_length: 2000,
            order_by: "creation desc"
        },
        callback: (r) => callback(r.message || []),
        error: () => callback([])
    });
}

function fetch_subcontracting_boms_for_reset(targets, callback) {
    if (!targets.subcontracting_items.length) {
        callback([]);
        return;
    }

    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Subcontracting BOM",
            filters: {
                finished_good: ["in", targets.subcontracting_items],
                is_active: 1
            },
            fields: ["name", "finished_good", "docstatus", "creation"],
            limit_page_length: 2000,
            order_by: "creation desc"
        },
        callback: (r) => callback(r.message || []),
        error: () => callback([])
    });
}

function sort_docs_by_creation_desc(docs) {
    return (docs || []).slice().sort((a, b) => {
        const a_creation = (a && a.creation) ? a.creation : "";
        const b_creation = (b && b.creation) ? b.creation : "";
        if (a_creation === b_creation) {
            const a_name = (a && a.name) ? a.name : "";
            const b_name = (b && b.name) ? b.name : "";
            return b_name.localeCompare(a_name);
        }
        return b_creation.localeCompare(a_creation);
    });
}

function process_bom_reset_sequence(bom_docs, result, done) {
    cancel_boms_in_reverse_creation(bom_docs, 0, result, () => {
        delete_boms_in_reverse_creation(bom_docs, 0, result, done);
    });
}

function cancel_boms_in_reverse_creation(bom_docs, index, result, done) {
    if (index >= bom_docs.length) {
        done();
        return;
    }

    const doc = bom_docs[index];
    if (!doc || cint(doc.docstatus) !== 1) {
        setTimeout(() => cancel_boms_in_reverse_creation(bom_docs, index + 1, result, done), 80);
        return;
    }

    frappe.call({
        method: "frappe.client.cancel",
        args: { doctype: "BOM", name: doc.name },
        callback: () => {
            doc.docstatus = 0;
            result.canceled_boms += 1;
            setTimeout(() => cancel_boms_in_reverse_creation(bom_docs, index + 1, result, done), 80);
        },
        error: (r) => {
            result.errors.push(`BOM ${doc.name}: ${get_reset_error_message(r) || "No se pudo cancelar"}`);
            setTimeout(() => cancel_boms_in_reverse_creation(bom_docs, index + 1, result, done), 80);
        }
    });
}

function delete_boms_in_reverse_creation(bom_docs, index, result, done) {
    if (index >= bom_docs.length) {
        done();
        return;
    }

    const doc = bom_docs[index];
    if (!doc || cint(doc.docstatus) !== 0) {
        setTimeout(() => delete_boms_in_reverse_creation(bom_docs, index + 1, result, done), 80);
        return;
    }

    frappe.call({
        method: "frappe.client.delete",
        args: { doctype: "BOM", name: doc.name },
        callback: () => {
            result.deleted_boms += 1;
            setTimeout(() => delete_boms_in_reverse_creation(bom_docs, index + 1, result, done), 80);
        },
        error: (r) => {
            result.errors.push(`BOM ${doc.name}: ${get_reset_error_message(r) || "No se pudo eliminar"}`);
            setTimeout(() => delete_boms_in_reverse_creation(bom_docs, index + 1, result, done), 80);
        }
    });
}

function delete_docs_sequentially(doctype, docs, index, result, done) {
    if (index >= docs.length) {
        done();
        return;
    }

    let doc = docs[index];
    cancel_and_delete_doc(doctype, doc, (success, error_msg) => {
        if (success) {
            if (doctype === "BOM") {
                result.deleted_boms += 1;
            } else {
                result.deleted_subcontracting += 1;
            }
        } else {
            result.errors.push(`${doctype} ${doc.name}: ${error_msg || "No se pudo cancelar/eliminar"}`);
        }

        setTimeout(() => {
            delete_docs_sequentially(doctype, docs, index + 1, result, done);
        }, 120);
    });
}

function cancel_and_delete_doc(doctype, doc, callback) {
    if (!doc || !doc.name) {
        callback(false, "Documento inválido");
        return;
    }

    const proceed_delete = () => {
        frappe.call({
            method: "frappe.client.delete",
            args: { doctype, name: doc.name },
            callback: () => callback(true),
            error: (r) => callback(false, get_reset_error_message(r))
        });
    };

    if (cint(doc.docstatus) === 1) {
        frappe.call({
            method: "frappe.client.cancel",
            args: { doctype, name: doc.name },
            callback: () => proceed_delete(),
            error: (r) => callback(false, get_reset_error_message(r))
        });
    } else {
        proceed_delete();
    }
}

function get_reset_error_message(response) {
    let message = get_error_message(response);
    if (message && typeof message === "object") {
        if (message.message) return message.message;
        return JSON.stringify(message);
    }
    if (typeof message === "string") {
        let trimmed = message.trim();
        if (trimmed.startsWith("{") && trimmed.endsWith("}")) {
            try {
                let parsed = JSON.parse(trimmed);
                if (parsed && parsed.message) return parsed.message;
            } catch (e) {
                // usar mensaje original
            }
        }
    }
    return message;
}

function reset_bom_references_in_costeo(frm, targets) {
    let changed = false;
    let item_set = new Set(targets.reset_items || []);

    (frm.doc.po_items || []).forEach(row => {
        if (row && row.bom_no && row.item_code && item_set.has(row.item_code)) {
            row.bom_no = "";
            changed = true;
        }
    });

    (frm.doc.sub_assembly_items || []).forEach(row => {
        let production_item = row ? (row.production_item || row.item_code) : "";
        if (row && row.bom_no && production_item && item_set.has(production_item)) {
            row.bom_no = "";
            changed = true;
        }
    });

    if (changed) {
        frm.refresh_field("po_items");
        frm.refresh_field("sub_assembly_items");
        frm.dirty();
    }
}

function show_reset_bom_summary(result, total_boms_found, total_subcontracting_found) {
    let has_errors = result.errors.length > 0;
    let total_deleted = result.deleted_boms + result.deleted_subcontracting;

    let message = `
        <b>BOMs encontradas:</b> ${total_boms_found}<br>
        <b>Subcontracting BOMs encontradas:</b> ${total_subcontracting_found}<br><br>
        <b>BOMs canceladas:</b> ${result.canceled_boms || 0}<br>
        <b>BOMs eliminadas:</b> ${result.deleted_boms}<br>
        <b>Subcontracting BOMs eliminadas:</b> ${result.deleted_subcontracting}<br>
        <b>Total eliminadas:</b> ${total_deleted}
    `;

    if (has_errors) {
        message += `<br><br><b>Advertencias:</b><br>${result.errors.join("<br>")}`;
    }

    frappe.msgprint({
        title: has_errors ? "Reinicio completado con advertencias" : "Reinicio de BOMs completado",
        indicator: has_errors ? "orange" : "green",
        message: message
    });
}
