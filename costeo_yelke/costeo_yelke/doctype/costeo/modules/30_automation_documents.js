// =============================================================================
// BOTONES DE AUTOMATIZACIÓN
// =============================================================================

const TEMPLATE_API = {
    LIST: 'costeo_yelke.api.costeo_template_api.get_costeo_templates',
    CREATE_FROM: 'costeo_yelke.api.costeo_template_api.create_costeo_from_templates',
    SAVE_AS: 'costeo_yelke.api.costeo_template_api.save_as_template',
    REFRESH_PRICES: 'costeo_yelke.api.costeo_template_api.refresh_costeo_prices'
};

function setup_automation_buttons(frm) {
    if (frm.doc.docstatus !== 0) return;

    // ── Plantillas ──────────────────────────────────────────────────────────
    if (frm.doc.es_plantilla) {
        frm.add_custom_button(__('Crear Costeo desde esta Plantilla'),
            () => create_costeo_from_this_template(frm), __('Plantillas'));
    } else {
        frm.add_custom_button(__('Nuevo desde Plantilla'),
            () => new_costeo_from_template_dialog(frm), __('Plantillas'));
        if (!frm.is_new()) {
            frm.add_custom_button(__('Guardar como Plantilla'),
                () => save_costeo_as_template(frm), __('Plantillas'));
            frm.add_custom_button(__('Refrescar Precios'),
                () => refresh_costeo_prices_action(frm), __('Plantillas'));
        }
    }

    // ── Automatización (solo costeos reales, no plantillas) ──────────────────
    if (frm.doc.es_plantilla) return;

    frm.add_custom_button(__('Crear BOMs'), () => create_boms_from_costeo(frm), __('Automatización'));
    frm.add_custom_button(__('Crear Subcontracting BOMs'), () => create_subcontracting_boms(frm), __('Automatización'));
    frm.add_custom_button(__('Crear Cotización'), () => create_quotation_from_costeo(frm), __('Automatización'));
    frm.add_custom_button(__('Crear Orden de Venta'), () => create_sales_order_from_costeo(frm), __('Automatización'));
    frm.add_custom_button(
        __('Desbloquear y Prellenar Plan de Producción'),
        () => unlock_and_prefill_production_plan_tab(frm),
        __('Automatización')
    );
}

// ── Acciones de Plantillas ───────────────────────────────────────────────────
function save_costeo_as_template(frm) {
    if (frm.is_new()) {
        show_error('Guarda el Costeo antes de convertirlo en plantilla');
        return;
    }
    frappe.confirm(
        __('Se guardará cada producto de este Costeo como su propia plantilla independiente (reutilizable sola o combinada con otras). ¿Continuar?'),
        () => {
            frappe.call({
                method: TEMPLATE_API.SAVE_AS,
                args: { costeo: frm.doc.name },
                freeze: true,
                freeze_message: __('Creando plantillas…'),
                callback: (r) => {
                    const creadas = (r.message && r.message.creadas) || [];
                    if (creadas.length) {
                        frappe.show_alert({
                            message: __('{0} plantilla(s) creada(s): {1}', [creadas.length, creadas.map(c => c.nombre).join(', ')]),
                            indicator: 'green'
                        });
                    } else {
                        show_error('No se creó ninguna plantilla (el costeo no tiene productos).');
                    }
                }
            });
        }
    );
}

function refresh_costeo_prices_action(frm) {
    frappe.confirm(
        __('¿Actualizar los precios de materias primas y servicios contra las listas de compra vigentes? Se recalcularán los costos.'),
        () => {
            frappe.call({
                method: TEMPLATE_API.REFRESH_PRICES,
                args: { costeo: frm.doc.name, only_missing: 0 },
                freeze: true,
                freeze_message: __('Refrescando precios…'),
                callback: (r) => {
                    if (r.message) {
                        frappe.show_alert({
                            message: __('{0} precio(s) actualizado(s)', [r.message.updated]),
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    }
                }
            });
        }
    );
}

function create_costeo_from_this_template(frm) {
    frappe.prompt(
        [
            { fieldname: 'cliente', fieldtype: 'Link', options: 'Customer', label: __('Cliente'), reqd: 1 },
            { fieldname: 'compania', fieldtype: 'Link', options: 'Company', label: __('Compañía'),
              default: frm.doc.compañia || frappe.defaults.get_user_default('company') }
        ],
        (values) => run_create_from_templates([frm.doc.name], values.cliente, values.compania),
        __('Crear Costeo desde Plantilla'),
        __('Crear')
    );
}

function new_costeo_from_template_dialog(frm) {
    frappe.call({
        method: TEMPLATE_API.LIST,
        freeze: true,
        callback: (r) => {
            const templates = r.message || [];
            if (!templates.length) {
                show_error('No hay plantillas todavía. Crea una desde un Costeo con "Guardar como Plantilla".');
                return;
            }
            // Como un carrito de compras: selecciona una o varias plantillas (cada
            // una es un solo producto) y se combinan en un costeo nuevo.
            const check_options = templates.map(t => ({
                label: `${t.nombre_plantilla || t.finished_item || t.name}${t.finished_item ? ' — ' + t.finished_item : ''}`,
                value: t.name,
                checked: 0
            }));

            frappe.prompt(
                [
                    { fieldname: 'plantillas', fieldtype: 'MultiCheck', label: __('Plantillas'),
                      options: check_options, reqd: 1, columns: 1 },
                    { fieldname: 'cliente', fieldtype: 'Link', options: 'Customer', label: __('Cliente'), reqd: 1 },
                    { fieldname: 'compania', fieldtype: 'Link', options: 'Company', label: __('Compañía'),
                      default: frm.doc.compañia || frappe.defaults.get_user_default('company') }
                ],
                (values) => {
                    if (!values.plantillas || !values.plantillas.length) {
                        show_error('Selecciona al menos una plantilla.');
                        return;
                    }
                    run_create_from_templates(values.plantillas, values.cliente, values.compania);
                },
                __('Nuevo Costeo desde Plantillas'),
                __('Crear')
            );
        }
    });
}

function run_create_from_templates(templates, cliente, compania) {
    frappe.call({
        method: TEMPLATE_API.CREATE_FROM,
        args: { templates, cliente, compania },
        freeze: true,
        freeze_message: __('Creando costeo con precios frescos…'),
        callback: (r) => {
            if (r.message && r.message.name) {
                frappe.show_alert({ message: __('Costeo creado: {0}', [r.message.name]), indicator: 'green' });
                frappe.set_route('Form', 'Costeo', r.message.name);
            }
        }
    });
}

function create_quotation_from_costeo(frm) {
    if (frm.is_new()) {
        show_error('Debes guardar el documento antes de crear la cotización');
        return;
    }
    if (!frm.doc.cliente) {
        show_error('Debes seleccionar un Cliente antes de crear la cotización');
        return;
    }
    if (!frm.doc.compañia) {
        show_error('Debes seleccionar la Compañía antes de crear la cotización');
        return;
    }

    let productos = frm.doc[DB.T1.FIELD_NAME] || [];
    let items = productos
        .filter(p => p[DB.T1.ITEM] && flt(p[DB.T1.QTY]) > 0)
        .map(p => ({
            item_code: p[DB.T1.ITEM],
            qty: flt(p[DB.T1.QTY]),
            rate: flt(p[DB.T1.SALES_PRICE]) || 0,
            price_list_rate: flt(p[DB.T1.SALES_PRICE]) || 0
        }));

    if (items.length === 0) {
        show_error('No hay productos finales con cantidad para la cotización');
        return;
    }

    enrich_items_with_details(items, () => {
        // Intentar usar plantilla de impuestos de la compañía (IVA)
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Sales Taxes and Charges Template",
                filters: { company: frm.doc.compañia },
                fields: ["name"],
                limit: 1
            },
            callback: function(r) {
                let tax_template = (r.message && r.message.length) ? r.message[0].name : null;
                make_quotation_doc(frm, items, tax_template);
            },
            error: function() {
                make_quotation_doc(frm, items, null);
            }
        });
    });
}

function make_quotation_doc(frm, items, tax_template) {
    frappe.model.with_doctype('Quotation', () => {
        let doc = frappe.model.get_new_doc('Quotation');
        doc.quotation_to = 'Customer';
        doc.party_name = frm.doc.cliente;
        doc.company = frm.doc.compañia;

        if (frappe.meta.has_field('Quotation', 'costeo')) {
            doc.costeo = frm.doc.name;
        }

        if (tax_template) {
            doc.taxes_and_charges = tax_template;
        }

        items.forEach(it => {
            let row = frappe.model.add_child(doc, 'Quotation Item', 'items');
            row.item_code = it.item_code;
            row.qty = it.qty;
            row.rate = it.rate;
            row.price_list_rate = it.price_list_rate;
            if (it.item_name) row.item_name = it.item_name;
            if (it.uom) row.uom = it.uom;
        });

        frappe.set_route('Form', 'Quotation', doc.name);
        if (!tax_template) {
            show_alert('No se encontró plantilla de impuestos para la compañía; agrega el IVA manualmente.', 'orange');
        }
    });
}

function create_sales_order_from_costeo(frm) {
    if (frm.is_new()) {
        show_error('Debes guardar el documento antes de crear la orden de venta');
        return;
    }
    if (!frm.doc.cliente) {
        show_error('Debes seleccionar un Cliente antes de crear la orden de venta');
        return;
    }
    if (!frm.doc.compañia) {
        show_error('Debes seleccionar la Compañía antes de crear la orden de venta');
        return;
    }

    let productos = frm.doc[DB.T1.FIELD_NAME] || [];
    let items = productos
        .filter(p => p[DB.T1.ITEM] && flt(p[DB.T1.QTY]) > 0)
        .map(p => ({
            item_code: p[DB.T1.ITEM],
            qty: flt(p[DB.T1.QTY]),
            rate: flt(p[DB.T1.SALES_PRICE]) || 0,
            price_list_rate: flt(p[DB.T1.SALES_PRICE]) || 0
        }));

    if (items.length === 0) {
        show_error('No hay productos finales con cantidad para la orden de venta');
        return;
    }

    enrich_items_with_details(items, () => {
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Sales Taxes and Charges Template",
                filters: { company: frm.doc.compañia },
                fields: ["name"],
                limit: 1
            },
            callback: function(r) {
                let tax_template = (r.message && r.message.length) ? r.message[0].name : null;
                make_sales_order_doc(frm, items, tax_template);
            },
            error: function() {
                make_sales_order_doc(frm, items, null);
            }
        });
    });
}

function make_sales_order_doc(frm, items, tax_template) {
    frappe.model.with_doctype('Sales Order', () => {
        let doc = frappe.model.get_new_doc('Sales Order');
        doc.customer = frm.doc.cliente;
        doc.company = frm.doc.compañia;

        has_custom_field('Sales Order', 'costeo').then((has) => {
            if (has) doc.costeo = frm.doc.name;
        });

        if (tax_template) {
            doc.taxes_and_charges = tax_template;
        }

        items.forEach(it => {
            let row = frappe.model.add_child(doc, 'Sales Order Item', 'items');
            row.item_code = it.item_code;
            row.qty = it.qty;
            row.rate = it.rate;
            row.price_list_rate = it.price_list_rate;
            if (it.item_name) row.item_name = it.item_name;
            if (it.uom) row.uom = it.uom;
        });

        frappe.set_route('Form', 'Sales Order', doc.name);
        if (!tax_template) {
            show_alert('No se encontró plantilla de impuestos para la compañía; agrega el IVA manualmente.', 'orange');
        }
    });
}

function enrich_items_with_details(items, done) {
    let promises = items.map(it => new Promise(resolve => {
        if (!it.item_code) {
            resolve();
            return;
        }
        frappe.db.get_value('Item', it.item_code, ['item_name', 'stock_uom'], (r) => {
            if (r && r.item_name) it.item_name = r.item_name;
            if (r && r.stock_uom) it.uom = r.stock_uom;
            resolve();
        });
    }));
    Promise.all(promises).then(() => done());
}

function create_production_plan_from_costeo(frm) {
    if (frm.is_new()) {
        show_error('Debes guardar el documento antes de crear el plan de producción');
        return;
    }
    if (!frm.doc.compañia) {
        show_error('Debes seleccionar la Compañía antes de crear el plan de producción');
        return;
    }
    if (!frm.doc.almacen_materias_primas || !frm.doc.almacen_trabajo_en_proceso) {
        show_error('Debes seleccionar los almacenes de Materias Primas y Trabajo en Proceso en el Costeo');
        return;
    }

    get_related_sales_order(frm, (sales_order) => {
        if (!sales_order) {
            show_error('No se encontró una Orden de Venta relacionada (debe estar enviada)');
            return;
        }

        make_production_plan_doc(frm, sales_order, {
            raw_materials: frm.doc.almacen_materias_primas,
            wip: frm.doc.almacen_trabajo_en_proceso
        });
    });
}

function get_related_sales_order(frm, callback) {
    // 1) Si existe un campo en Costeo, usarlo
    if (frm.doc.orden_de_venta) {
        callback(frm.doc.orden_de_venta);
        return;
    }

    // 2) Buscar por campo costeo en Sales Order (Custom Field)
    has_custom_field('Sales Order', 'costeo').then((has) => {
        if (!has) {
            show_error('No existe un enlace entre Costeo y Orden de Venta. Crea un campo Link en Sales Order (costeo) o en Costeo (orden_de_venta).');
            callback(null);
            return;
        }

        frappe.db.get_list('Sales Order', {
            fields: ['name'],
            filters: { costeo: frm.doc.name, docstatus: 1 },
            order_by: 'modified desc',
            limit: 1
        }).then(r => {
            callback(r && r.length ? r[0].name : null);
        }).catch(() => callback(null));
    });
}

function has_custom_field(doctype, fieldname) {
    return frappe.db.get_list('Custom Field', {
        fields: ['name'],
        filters: { dt: doctype, fieldname: fieldname },
        limit: 1
    }).then(r => (r && r.length > 0)).catch(() => false);
}

function make_production_plan_doc(frm, sales_order, wh) {
    frappe.model.with_doctype('Production Plan', () => {
        let doc = frappe.model.get_new_doc('Production Plan');
        doc.company = frm.doc.compañia;
        doc.get_items_from = 'Sales Order';
        doc.for_warehouse = wh.raw_materials;
        doc.sub_assembly_warehouse = wh.wip;

        let proveedor_map = build_subassembly_supplier_map(frm);

        let so_row = frappe.model.add_child(doc, 'Production Plan Sales Order', 'sales_orders');
        so_row.sales_order = sales_order;

        // 1) Obtener items desde la orden de venta
        frappe.call({
            method: 'get_items',
            doc: doc,
            freeze: true,
            callback: function () {
                // 2) Obtener sub-ensambles
                frappe.call({
                    method: 'get_sub_assembly_items',
                    doc: doc,
                    freeze: true,
                    callback: function () {
                        // Setear almacén de sub-ensambles (WIP)
                        (doc.sub_assembly_items || []).forEach(row => {
                            row.fg_warehouse = wh.wip;
                            if (row.production_item && proveedor_map[row.production_item]) {
                                row.supplier = proveedor_map[row.production_item];
                            }
                        });

                        // 3) Obtener materias primas (MR items) para el almacén definido
                        frappe.call({
                            method: 'erpnext.manufacturing.doctype.production_plan.production_plan.get_items_for_material_requests',
                            args: {
                                doc: doc,
                                warehouses: [{ warehouse: doc.for_warehouse }]
                            },
                            freeze: true,
                            callback: function (r) {
                                doc.mr_items = [];
                                (r.message || []).forEach(row => {
                                    let d = frappe.model.add_child(doc, 'Material Request Plan Item', 'mr_items');
                                    Object.keys(row).forEach(key => {
                                        if (key !== 'name') d[key] = row[key];
                                    });
                                    d.warehouse = doc.for_warehouse;
                                });

                                frappe.set_route('Form', 'Production Plan', doc.name);
                            }
                        });
                    }
                });
            }
        });
    });
}

function build_subassembly_supplier_map(frm) {
    let map = {};
    let etapas = frm.doc[DB.T3.FIELD_NAME] || [];
    etapas.forEach(e => {
        let sub = e[DB.T3.SUBENSAMBLAJE];
        let prov = e[DB.T3.PROVEEDOR];
        if (sub && prov && !map[sub]) {
            map[sub] = prov;
        }
    });
    return map;
}

function resolve_required_warehouses(company) {
    return Promise.all([
        resolve_warehouse_by_labels(company, ['Materia Prima', 'Materia primas']),
        resolve_warehouse_by_labels(company, ['Trabajos en Proceso', 'Trabajo en Proceso'])
    ]).then(([raw_wh, wip_wh]) => {
        if (!raw_wh || !wip_wh) {
            let missing = [];
            if (!raw_wh) missing.push(`Materia Prima (almacén de materias primas)`);
            if (!wip_wh) missing.push(`Trabajos en Proceso (almacén de WIP)`);
            show_error(`No se encontraron los almacenes requeridos: ${missing.join(', ')}. Revisa el nombre exacto en Warehouse o dime los nombres correctos.`);
            return null;
        }
        return { raw_materials: raw_wh, wip: wip_wh };
    });
}

function resolve_warehouse_by_labels(company, labels) {
    let sequence = Promise.resolve(null);

    (labels || []).forEach(label => {
        sequence = sequence.then(found => found || resolve_warehouse_by_label(company, label));
    });

    return sequence;
}

function resolve_warehouse_by_label(company, label) {
    // 1) match exact warehouse_name
    return frappe.db.get_list('Warehouse', {
        fields: ['name', 'warehouse_name'],
        filters: { company: company, warehouse_name: label },
        limit: 1
    }).then(r => {
        if (r && r.length) return r[0].name;
        // 2) match exact name
        return frappe.db.get_list('Warehouse', {
            fields: ['name', 'warehouse_name'],
            filters: { company: company, name: label },
            limit: 1
        });
    }).then(r => {
        if (r && r.length) return r[0].name;
        // 3) fuzzy match by warehouse_name contains label
        return frappe.db.get_list('Warehouse', {
            fields: ['name', 'warehouse_name'],
            filters: { company: company, warehouse_name: ['like', `%${label}%`] },
            limit: 1
        });
    }).then(r => {
        if (r && r.length) return r[0].name;
        return null;
    }).catch(() => null);
}
