// AUTO-GENERATED FILE.
// Source modules: costeo_yelke/costeo_yelke/doctype/costeo/modules/
// Build command: ./costeo_yelke/costeo_yelke/doctype/costeo/build_costeo_js.sh

// -----------------------------------------------------------------------------
// Module: 00_constants.js
// -----------------------------------------------------------------------------
// =============================================================================
// CONFIGURACIÓN Y CONSTANTES
// =============================================================================

const DB = {
    MAIN_DOCTYPE: "Costeo",
    
    T1: {
        FIELD_NAME: "costeo_producto",
        DOCTYPE_ID: "Costeo Producto",
        ITEM: "finished_item",
        QTY: "qty",
        MAT_COST: "material_cost",
        SERV_COST: "services_cost",
        SHIP_COST: "shipping_cost",
        AMOUNT: "amount",
        OVERHEAD_PCT: "overhead_pct",
        OVERHEAD_AMT: "overhead_amt",
        TOTAL_COST: "total_unit_cost",
        SALES_PRICE: "unit_sales_price",
        MARGIN_PCT: "margin_pct",
        TOTAL_SALES: "total_sales_price"
    },

    T2: {
        FIELD_NAME: "costeo_producto_detalle",
        DOCTYPE_ID: "Costeo Producto Detalle",
        FINISHED_ITEM: "finished_item",
        CONCEPT_TYPE: "concept_type",
        ITEM: "item",
        INT_UOM: "internal_uom",
        INT_QTY: "internal_qty",
        SUPPLIER: "supplier",
        SUP_UOM: "supplier_uom",
        CONV_FACTOR: "conversion_factor",
        SUP_QTY: "supplier_qty",
        MIN_SUP_QTY: "min_supplier_qty",
        UNIT_PRICE: "unit_price",
        TOTAL: "total",
        ETAPA: "etapa",
        SERVICIO: "servicio",
        PROVEEDOR_SERVICIO: "proveedor_servicio",
        SUBENSAMBLAJE: "subensamblaje"
    },

    T3: {
        FIELD_NAME: "tabla_etapas_costeo",
        DOCTYPE_ID: "Etapas Costeo",
        PRODUCTO_TERMINADO: "producto_terminado",
        ETAPA: "etapa",
        SERVICIO: "servicio",
        PROVEEDOR: "proveedor",
        SUBENSAMBLAJE: "subensamblaje"
    },

    TREE_VIEW: "tree_view",

    GROUPS: {
        FINISHED: "Productos Terminados",
        RAW: "Materia Prima",
        SERVICES: "Servicios",
        SHIPPING: "Envio",
        SUBASSEMBLY: "Sub-ensamblajes"
    }
};


// -----------------------------------------------------------------------------
// Module: 10_main_form_events.js
// -----------------------------------------------------------------------------
// =============================================================================
// FORMULARIO PRINCIPAL
// =============================================================================

frappe.ui.form.on(DB.MAIN_DOCTYPE, {
    refresh: function(frm) {
        setup_field_filters(frm);
        setup_automation_buttons(frm);
        sync_pp_header_defaults(frm);
        set_pp_tab_lock_state(frm);
        setup_production_plan_queries(frm);
        setup_production_plan_automation_buttons(frm);
        
        setTimeout(() => { 
            update_select_options(frm);
            render_tree_view(frm); 
        }, 500);
        
        inject_css();
        // Asegurar que las tablas técnicas no se muestren en el formulario
        frm.toggle_display('costeo_producto_detalle', false);
        frm.toggle_display('tabla_etapas_costeo', false);
    },

    validate: function(frm) {
        if (!validate_at_least_one_product_to_produce(frm)) {
            frappe.validated = false;
            return;
        }

        if (!validate_unique_services_per_stage(frm)) {
            frappe.validated = false;
            return;
        }
        
        calculate_aggregates(frm);
        render_tree_view(frm);
    },

    before_costeo_producto_remove: function(frm, cdt, cdn) {
        let row = (cdt && cdn && locals[cdt]) ? locals[cdt][cdn] : null;
        let finished_item = row ? row[DB.T1.ITEM] : null;
        if (finished_item) {
            if (!frm.__removed_finished_items) frm.__removed_finished_items = [];
            frm.__removed_finished_items.push(finished_item);
        }
    },

    costeo_producto_remove: function(frm) {
        let removed = frm.__removed_finished_items || [];
        if (removed.length) {
            removed.forEach(item => cleanup_related_rows_for_item(frm, item));
        }
        // respaldo: limpieza global de huérfanos
        cleanup_related_rows(frm);
        frm.__removed_finished_items = [];
        update_select_options(frm);
        render_tree_view(frm);
    },

    costeo_producto_delete: function(frm) {
        // Borrado masivo desde el grid
        cleanup_related_rows(frm);
        update_select_options(frm);
        render_tree_view(frm);
    }
});

// -----------------------------------------------------------------------------
// Module: 20_filters_and_cleanup.js
// -----------------------------------------------------------------------------
// =============================================================================
// CONFIGURACIÓN DE FILTROS
// =============================================================================

function setup_field_filters(frm) {
    try {
        frm.set_query(DB.T1.ITEM, DB.T1.FIELD_NAME, () => ({
            filters: { 'item_group': DB.GROUPS.FINISHED }
        }));
        
        frm.set_query(DB.T2.ITEM, DB.T2.FIELD_NAME, function(doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            let group_filter = get_item_group_filter(row.concept_type);
            return group_filter ? { filters: { 'item_group': group_filter } } : {};
        });

        frm.set_query(DB.T3.SERVICIO, DB.T3.FIELD_NAME, () => ({
            filters: { 'item_group': DB.GROUPS.SERVICES }
        }));

        frm.set_query(DB.T3.SUBENSAMBLAJE, DB.T3.FIELD_NAME, () => ({
            filters: { 'item_group': ['in', [DB.GROUPS.SUBASSEMBLY, DB.GROUPS.FINISHED]] }
        }));

        frm.set_query(DB.T3.PRODUCTO_TERMINADO, DB.T3.FIELD_NAME, () => ({
            filters: { 'item_group': DB.GROUPS.FINISHED }
        }));

        frm.set_query('almacen_materias_primas', () => ({
            filters: { company: frm.doc.compañia }
        }));

        frm.set_query('almacen_trabajo_en_proceso', () => ({
            filters: { company: frm.doc.compañia }
        }));
    } catch (e) {
        console.error('Error configurando filtros:', e);
    }
}

function get_item_group_filter(concept_type) {
    const mapping = {
        "Materia Prima": DB.GROUPS.RAW,
        "Servicio": DB.GROUPS.SERVICES,
        "Envío": DB.GROUPS.SHIPPING
    };
    return mapping[concept_type] || "";
}

function cleanup_related_rows(frm) {
    let productos = frm.doc[DB.T1.FIELD_NAME] || [];
    let valid_items = new Set(productos.map(p => p[DB.T1.ITEM]).filter(Boolean));

    if (frm.doc[DB.T2.FIELD_NAME]) {
        frm.doc[DB.T2.FIELD_NAME] = frm.doc[DB.T2.FIELD_NAME].filter(r => valid_items.has(r[DB.T2.FINISHED_ITEM]));
        frm.refresh_field(DB.T2.FIELD_NAME);
    }

    if (frm.doc[DB.T3.FIELD_NAME]) {
        frm.doc[DB.T3.FIELD_NAME] = frm.doc[DB.T3.FIELD_NAME].filter(r => valid_items.has(r[DB.T3.PRODUCTO_TERMINADO]));
        frm.refresh_field(DB.T3.FIELD_NAME);
    }

    frm.dirty();
}

function cleanup_related_rows_for_item(frm, finished_item) {
    if (!finished_item) return;

    if (frm.doc[DB.T2.FIELD_NAME]) {
        frm.doc[DB.T2.FIELD_NAME] = frm.doc[DB.T2.FIELD_NAME].filter(r => r[DB.T2.FINISHED_ITEM] !== finished_item);
        frm.refresh_field(DB.T2.FIELD_NAME);
    }

    if (frm.doc[DB.T3.FIELD_NAME]) {
        frm.doc[DB.T3.FIELD_NAME] = frm.doc[DB.T3.FIELD_NAME].filter(r => r[DB.T3.PRODUCTO_TERMINADO] !== finished_item);
        frm.refresh_field(DB.T3.FIELD_NAME);
    }

    frm.dirty();
    update_select_options(frm);
    render_tree_view(frm);
}



// -----------------------------------------------------------------------------
// Module: 30_automation_documents.js
// -----------------------------------------------------------------------------
// =============================================================================
// BOTONES DE AUTOMATIZACIÓN
// =============================================================================

function setup_automation_buttons(frm) {
    if (frm.doc.docstatus === 0) {
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
    const targets = {
        raw_materials_label: 'Materia primas',
        wip_label: 'Trabajos en Proceso'
    };

    return Promise.all([
        resolve_warehouse_by_label(company, targets.raw_materials_label),
        resolve_warehouse_by_label(company, targets.wip_label)
    ]).then(([raw_wh, wip_wh]) => {
        if (!raw_wh || !wip_wh) {
            let missing = [];
            if (!raw_wh) missing.push(`Materia primas (almacén de materias primas)`);
            if (!wip_wh) missing.push(`Trabajos en Proceso (almacén de WIP)`);
            show_error(`No se encontraron los almacenes requeridos: ${missing.join(', ')}. Revisa el nombre exacto en Warehouse o dime los nombres correctos.`);
            return null;
        }
        return { raw_materials: raw_wh, wip: wip_wh };
    });
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

// -----------------------------------------------------------------------------
// Module: 35_validations.js
// -----------------------------------------------------------------------------
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

// -----------------------------------------------------------------------------
// Module: 37_production_plan_tab.js
// -----------------------------------------------------------------------------
// =============================================================================
// PLAN DE PRODUCCION EMBEBIDO EN COSTEO
// =============================================================================

const PP_API = {
    GET_SALES_ORDERS: "costeo_yelke.costeo_yelke.doctype.costeo.costeo.pp_get_open_sales_orders",
    GET_MATERIAL_REQUESTS: "costeo_yelke.costeo_yelke.doctype.costeo.costeo.pp_get_pending_material_requests",
    GET_ITEMS: "costeo_yelke.costeo_yelke.doctype.costeo.costeo.pp_get_items",
    COMBINE_ITEMS: "costeo_yelke.costeo_yelke.doctype.costeo.costeo.pp_combine_so_items",
    GET_SUB_ASSEMBLY_ITEMS: "costeo_yelke.costeo_yelke.doctype.costeo.costeo.pp_get_sub_assembly_items",
    VALIDATE_SALES_ORDER: "costeo_yelke.costeo_yelke.doctype.costeo.costeo.pp_validate_sales_order",
    MAKE_WORK_ORDERS: "costeo_yelke.costeo_yelke.doctype.costeo.costeo.pp_make_work_orders",
    MAKE_SUBCONTRACT_PO: "costeo_yelke.costeo_yelke.doctype.costeo.costeo.pp_make_subcontracting_purchase_orders",
    MAKE_MATERIAL_REQUEST: "costeo_yelke.costeo_yelke.doctype.costeo.costeo.pp_make_material_request",
    GET_DEFAULT_SUPPLIERS: "costeo_yelke.costeo_yelke.doctype.costeo.costeo.pp_get_default_suppliers"
};

const PP_LOCKED_FIELDS = [
    "naming_series",
    "company",
    "get_items_from",
    "posting_date",
    "filters",
    "item_code",
    "customer",
    "warehouse",
    "project",
    "sales_order_status",
    "from_date",
    "to_date",
    "from_delivery_date",
    "to_delivery_date",
    "sales_orders_detail",
    "get_sales_orders",
    "sales_orders",
    "material_request_detail",
    "get_material_request",
    "material_requests",
    "select_items_to_manufacture_section",
    "get_items",
    "combine_items",
    "po_items",
    "section_break_25",
    "prod_plan_references",
    "section_break_24",
    "combine_sub_items",
    "sub_assembly_warehouse",
    "section_break_ucc4",
    "skip_available_sub_assembly_item",
    "column_break_igxl",
    "get_sub_assembly_items",
    "section_break_g4ip",
    "sub_assembly_items",
    "download_materials_request_plan_section_section",
    "download_materials_required",
    "material_request_planning",
    "include_non_stock_items",
    "include_subcontracted_items",
    "consider_minimum_order_qty",
    "include_safety_stock",
    "ignore_existing_ordered_qty",
    "column_break_25",
    "for_warehouse",
    "get_items_for_mr",
    "transfer_materials",
    "section_break_27",
    "mr_items",
    "other_details",
    "total_planned_qty",
    "total_produced_qty",
    "column_break_32",
    "status",
    "warehouses",
    "amended_from"
];

const PP_ACTION_FORM_FIELDS = [
    "pp_actions_section",
    "pp_make_work_orders",
    "pp_column_break_work_orders",
    "pp_make_subcontracting_po",
    "pp_column_break_subcontract",
    "pp_make_material_request"
];

function is_pp_tab_unlocked(frm) {
    return parseInt(frm.doc.pp_tab_unlocked || 0, 10) === 1;
}

function set_pp_tab_lock_state(frm) {
    const unlocked = is_pp_tab_unlocked(frm);

    PP_LOCKED_FIELDS.forEach(fieldname => {
        frm.toggle_display(fieldname, unlocked);
    });

    frm.toggle_display("pp_lock_notice", !unlocked);

    if (!frm.fields_dict.pp_lock_notice) return;
    const message = unlocked
        ? ""
        : `
            <div style="padding: 14px; border: 1px solid #f59e0b; background: #fffbeb; border-radius: 8px;">
                <div style="font-weight: 600; color: #92400e; margin-bottom: 6px;">Plan de Producción bloqueado</div>
                <div style="color: #78350f;">
                    Completa la primera pestaña y usa el botón
                    <b>Desbloquear y Prellenar Plan de Producción</b> para habilitar esta sección.
                </div>
            </div>
        `;
    frm.fields_dict.pp_lock_notice.$wrapper.html(message);

    // Las acciones se gestionan solo por botón custom desplegable ("Crear").
    PP_ACTION_FORM_FIELDS.forEach(fieldname => {
        frm.toggle_display(fieldname, false);
    });
}

function sync_pp_header_defaults(frm) {
    if (!frm.doc.company && frm.doc.compañia) {
        frm.set_value("company", frm.doc.compañia);
    }

    if (!frm.doc.posting_date) {
        frm.set_value("posting_date", frm.doc.fecha || frappe.datetime.get_today());
    }

    if (!frm.doc.customer && frm.doc.cliente) {
        frm.set_value("customer", frm.doc.cliente);
    }

    if (!frm.doc.project && frm.doc.proyecto) {
        frm.set_value("project", frm.doc.proyecto);
    }

    if (!frm.doc.get_items_from) {
        frm.set_value("get_items_from", "Sales Order");
    }
}

function setup_production_plan_queries(frm) {
    frm.set_query("sales_order", "sales_orders", () => ({
        query: "erpnext.manufacturing.doctype.production_plan.production_plan.sales_order_query",
        filters: {
            company: frm.doc.company,
            item_code: frm.doc.item_code
        }
    }));

    frm.set_query("for_warehouse", doc => ({
        filters: {
            company: doc.company,
            is_group: 0
        }
    }));

    frm.set_query("sub_assembly_warehouse", doc => ({
        filters: {
            company: doc.company
        }
    }));

    frm.set_query("material_request", "material_requests", () => ({
        filters: {
            material_request_type: "Manufacture",
            docstatus: 1,
            status: ["!=", "Stopped"]
        }
    }));

    frm.set_query("item_code", "po_items", () => ({
        query: "erpnext.controllers.queries.item_query",
        filters: {
            is_stock_item: 1
        }
    }));

    frm.set_query("bom_no", "po_items", (doc, cdt, cdn) => {
        const row = locals[cdt][cdn];
        if (row.item_code) {
            return {
                query: "erpnext.controllers.queries.bom",
                filters: { item: row.item_code, docstatus: 1 }
            };
        }
        frappe.msgprint(__("Please enter Item first"));
        return {};
    });

    frm.set_query("warehouse", "mr_items", doc => ({
        filters: { company: doc.company }
    }));

    frm.set_query("warehouse", "po_items", doc => ({
        filters: { company: doc.company }
    }));
}

function setup_production_plan_automation_buttons(frm) {
    if (!is_pp_tab_unlocked(frm)) return;
    if (frm.is_new() || frm.doc.__unsaved) return;

    frm.add_custom_button(__("Crear Work Orders"), () => frm.trigger("pp_make_work_orders"), __("Crear"));
    frm.add_custom_button(__("Crear Subcontracting PO"), () => frm.trigger("pp_make_subcontracting_po"), __("Crear"));
    frm.add_custom_button(__("Crear Solicitud Materia Prima"), () => frm.trigger("pp_make_material_request"), __("Crear"));
    style_create_actions_button(frm);
}

function style_create_actions_button(frm) {
    if (!frm.page || !frm.page.inner_toolbar) return;

    const encoded_group_label = encodeURIComponent(__("Crear"));
    const $button = frm.page.inner_toolbar.find(
        `.inner-group-button[data-label="${encoded_group_label}"] > button`
    );

    if (!$button.length) return;

    $button.removeClass("btn-default btn-primary").addClass("costeo-black-create-btn");
}

function replace_child_table(frm, fieldname, rows) {
    frm.clear_table(fieldname);

    (rows || []).forEach(row => {
        const d = frm.add_child(fieldname);
        Object.keys(row || {}).forEach(key => {
            if (
                [
                    "name",
                    "idx",
                    "doctype",
                    "parent",
                    "parenttype",
                    "parentfield",
                    "docstatus",
                    "owner",
                    "creation",
                    "modified",
                    "modified_by"
                ].includes(key)
            ) {
                return;
            }
            if (row[key] === undefined) return;
            d[key] = row[key];
        });
    });

    frm.refresh_field(fieldname);
    frm.dirty();
}

function call_pp_api(frm, method, args, callback) {
    frappe.call({
        method,
        freeze: true,
        args: Object.assign({ doc: frm.doc }, args || {}),
        callback: r => {
            if (callback) callback(r.message || {});
        }
    });
}

function call_pp_api_promise(frm, method, args) {
    return new Promise((resolve, reject) => {
        frappe.call({
            method,
            freeze: true,
            args: Object.assign({ doc: frm.doc }, args || {}),
            callback: r => resolve(r.message || {}),
            error: reject
        });
    });
}

function collect_first_tab_unlock_issues(frm) {
    const required = [
        ["cliente", "Cliente"],
        ["fecha", "Fecha"],
        ["compañia", "Compañía"],
        ["centro_de_costos", "Centro de Costos"],
        ["almacen_materias_primas", "Almacén Materias Primas"],
        ["almacen_trabajo_en_proceso", "Almacén Trabajo en Proceso"]
    ];

    const missing = required.filter(([fieldname]) => !frm.doc[fieldname]).map(([, label]) => label);
    const has_products = (frm.doc.costeo_producto || []).some(row => row.finished_item && flt(row.qty) > 0);

    if (!has_products) {
        missing.push("Al menos un producto terminado con cantidad a producir");
    }

    return missing;
}

function is_first_tab_ready_for_pp_unlock(frm) {
    return collect_first_tab_unlock_issues(frm).length === 0;
}

function validate_first_tab_for_pp_unlock(frm) {
    const missing = collect_first_tab_unlock_issues(frm);
    if (missing.length > 0) {
        show_error(
            `Completa la primera pestaña antes de desbloquear el Plan de Producción:<br>- ${missing.join("<br>- ")}`
        );
        return false;
    }

    return true;
}

function set_sales_order_on_pp_tab(frm, sales_order) {
    replace_child_table(frm, "sales_orders", [{ sales_order }]);

    return new Promise(resolve => {
        frappe.call({
            method: "erpnext.manufacturing.doctype.production_plan.production_plan.get_so_details",
            args: { sales_order },
            callback: function(r) {
                const details = r.message || {};
                if (frm.doc.sales_orders && frm.doc.sales_orders.length > 0) {
                    const row = frm.doc.sales_orders[0];
                    row.sales_order_date = details.transaction_date;
                    row.customer = details.customer;
                    row.grand_total = details.grand_total;
                    frm.refresh_field("sales_orders");
                }
                resolve();
            },
            error: () => resolve()
        });
    });
}

function get_default_planned_start_date(frm) {
    const posting_date = frm.doc.posting_date || frm.doc.fecha || frappe.datetime.get_today();
    return `${posting_date} 00:00:00`;
}

function get_qty_by_finished_item(frm) {
    const qty_map = {};
    (frm.doc.costeo_producto || []).forEach(row => {
        if (row.finished_item) {
            qty_map[row.finished_item] = flt(row.qty) || 1;
        }
    });
    return qty_map;
}

function normalize_concept_label(value) {
    return (value || "")
        .toString()
        .trim()
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "");
}

function is_raw_material_concept(value) {
    const normalized = normalize_concept_label(value);
    return normalized === "materia prima" || normalized === "materiaprima";
}

function build_raw_material_supplier_map(frm) {
    const supplier_map = {};
    const conflicts = new Set();

    (frm.doc.costeo_producto_detalle || []).forEach(row => {
        if (!row.item || !row.supplier) return;
        if (!is_raw_material_concept(row.concept_type)) return;

        if (!supplier_map[row.item]) {
            supplier_map[row.item] = row.supplier;
            return;
        }

        if (supplier_map[row.item] !== row.supplier) {
            conflicts.add(row.item);
        }
    });

    if (conflicts.size && !frm.__raw_material_supplier_conflicts_warned) {
        frm.__raw_material_supplier_conflicts_warned = true;
        show_warning(
            `Hay materias primas con más de un proveedor en Costeo. Se tomará el primero para MR:<br>${Array.from(
                conflicts
            ).join("<br>")}`
        );
    }

    return supplier_map;
}

function apply_raw_material_suppliers_to_mr_items(frm) {
    const supplier_map = build_raw_material_supplier_map(frm);
    if (!Object.keys(supplier_map).length) return;

    (frm.doc.mr_items || []).forEach(row => {
        if (!row.item_code) return;
        if (!supplier_map[row.item_code]) return;
        row.supplier = supplier_map[row.item_code];
    });

    frm.refresh_field("mr_items");
}

function fetch_item_data_for_plan(item_code) {
    return new Promise(resolve => {
        if (!item_code) {
            resolve({});
            return;
        }

        frappe.call({
            method: "erpnext.manufacturing.doctype.production_plan.production_plan.get_item_data",
            args: { item_code },
            callback: r => {
                const data = r.message || {};
                if (data.bom_no) {
                    resolve(data);
                    return;
                }

                // Fallback: tomar cualquier BOM activo/enviado del item.
                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "BOM",
                        filters: {
                            item: item_code,
                            docstatus: 1,
                            is_active: 1
                        },
                        fields: ["name"],
                        order_by: "is_default desc, modified desc",
                        limit: 1
                    },
                    callback: bom_result => {
                        const bom_name =
                            bom_result.message && bom_result.message.length ? bom_result.message[0].name : "";
                        resolve({
                            bom_no: data.bom_no || bom_name,
                            stock_uom: data.stock_uom || ""
                        });
                    },
                    error: () => resolve(data)
                });
            },
            error: () => resolve({})
        });
    });
}

function fetch_item_default_warehouse(item_code, company) {
    return new Promise(resolve => {
        if (!item_code) {
            resolve("");
            return;
        }

        const filters = { parent: item_code };
        if (company) filters.company = company;

        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Item Default",
                filters,
                fields: ["default_warehouse"],
                limit: 1
            },
            callback: r => {
                const warehouse =
                    r.message && r.message.length && r.message[0].default_warehouse
                        ? r.message[0].default_warehouse
                        : "";
                resolve(warehouse);
            },
            error: () => resolve("")
        });
    });
}

async function ensure_po_items_required_fields(frm) {
    const qty_by_item = get_qty_by_finished_item(frm);
    const first_finished_item = Object.keys(qty_by_item)[0];

    if (!(frm.doc.po_items || []).length && first_finished_item) {
        const row = frm.add_child("po_items");
        row.item_code = first_finished_item;
        row.planned_qty = qty_by_item[first_finished_item] || 1;
        row.planned_start_date = get_default_planned_start_date(frm);
        row.warehouse = frm.doc.almacen_trabajo_en_proceso || "";
        row.include_exploded_items = 1;
    }

    for (const row of frm.doc.po_items || []) {
        if (!row.item_code && first_finished_item) {
            row.item_code = first_finished_item;
        }

        if (!row.planned_qty || flt(row.planned_qty) <= 0) {
            row.planned_qty = row.item_code && qty_by_item[row.item_code] ? qty_by_item[row.item_code] : 1;
        }

        if (!row.planned_start_date) {
            row.planned_start_date = get_default_planned_start_date(frm);
        }

        if (!row.warehouse && frm.doc.almacen_trabajo_en_proceso) {
            row.warehouse =
                (await fetch_item_default_warehouse(row.item_code, frm.doc.company || frm.doc.compañia)) ||
                frm.doc.almacen_trabajo_en_proceso;
        }

        if (row.item_code && (!row.bom_no || !row.stock_uom)) {
            const item_data = await fetch_item_data_for_plan(row.item_code);
            if (!row.bom_no && item_data.bom_no) row.bom_no = item_data.bom_no;
            if (!row.stock_uom && item_data.stock_uom) row.stock_uom = item_data.stock_uom;
        }
    }

    frm.refresh_field("po_items");

    const missing_rows = [];
    (frm.doc.po_items || []).forEach((row, index) => {
        const missing = [];
        if (!row.item_code) missing.push("Código del Producto");
        if (!row.bom_no) missing.push("Lista de materiales (LdM) No.");
        if (!row.planned_qty || flt(row.planned_qty) <= 0) missing.push("Cant. planificada");
        if (!row.stock_uom) missing.push("UdM");
        if (!row.planned_start_date) missing.push("Fecha prevista de inicio");

        if (missing.length) {
            missing_rows.push(`Fila ${index + 1}: ${missing.join(", ")}`);
        }
    });

    if (missing_rows.length) {
        show_warning(`Campos faltantes en Artículos de montaje:<br>${missing_rows.join("<br>")}`);
    }
}

function get_stage_rows_grouped_by_product(frm) {
    const grouped = {};
    (frm.doc.tabla_etapas_costeo || []).forEach(row => {
        if (!row.producto_terminado || !row.etapa) return;
        grouped[row.producto_terminado] = grouped[row.producto_terminado] || [];
        grouped[row.producto_terminado].push(row);
    });

    Object.keys(grouped).forEach(producto => {
        grouped[producto] = grouped[producto]
            .slice()
            .sort((a, b) => parseInt(a.etapa || "0", 10) - parseInt(b.etapa || "0", 10));
    });

    return grouped;
}

function find_matching_subassembly_row(rows, candidate) {
    return (rows || []).find(row => {
        if ((row.production_item || "") !== (candidate.production_item || "")) return false;
        if ((row.parent_item_code || "") !== (candidate.parent_item_code || "")) return false;

        // Allow enriching rows without supplier first, but keep supplier-specific rows isolated.
        if (candidate.supplier && row.supplier && row.supplier !== candidate.supplier) return false;

        // Use stage number as additional discriminator when available.
        if (
            candidate.bom_level !== undefined &&
            row.bom_level !== undefined &&
            parseInt(row.bom_level || "0", 10) !== parseInt(candidate.bom_level || "0", 10)
        ) {
            return false;
        }

        return true;
    });
}

function get_subassembly_exact_key(row) {
    return `${row.parent_item_code || ""}::${row.bom_level || ""}::${row.production_item || ""}`;
}

function get_subassembly_item_key(row) {
    return `${row.parent_item_code || ""}::${row.production_item || ""}`;
}

function get_po_row_by_finished_item(frm, finished_item) {
    return (frm.doc.po_items || []).find(row => row.item_code === finished_item) || null;
}

function get_preserved_subassembly_fields(source) {
    const preserved = {};
    [
        "actual_qty",
        "projected_qty",
        "ordered_qty",
        "received_qty",
        "wo_produced_qty",
        "item_name",
        "description",
        "purchase_order"
    ].forEach(fieldname => {
        if (source && source[fieldname] !== undefined && source[fieldname] !== null && source[fieldname] !== "") {
            preserved[fieldname] = source[fieldname];
        }
    });
    return preserved;
}

async function ensure_stage_rows_in_subassembly(frm, warehouses) {
    const stages_by_product = get_stage_rows_grouped_by_product(frm);
    const products = Object.keys(stages_by_product);
    if (!products.length) return;

    const qty_by_item = get_qty_by_finished_item(frm);
    const company = frm.doc.company || frm.doc.compañia;
    const has_service_stages = products.some(product =>
        (stages_by_product[product] || []).some(row => row.servicio)
    );
    if (!has_service_stages) return;

    const existing_rows = (frm.doc.sub_assembly_items || []).slice();
    const exact_map = {};
    const item_map = {};
    existing_rows.forEach(row => {
        exact_map[get_subassembly_exact_key(row)] = row;
        item_map[get_subassembly_item_key(row)] = row;
    });

    const item_data_cache = {};
    const default_wh_cache = {};
    const get_item_data_cached = async item_code => {
        if (!item_code) return {};
        if (!item_data_cache[item_code]) {
            item_data_cache[item_code] = await fetch_item_data_for_plan(item_code);
        }
        return item_data_cache[item_code];
    };
    const get_default_wh_cached = async item_code => {
        if (!item_code) return "";
        if (default_wh_cache[item_code] === undefined) {
            default_wh_cache[item_code] = await fetch_item_default_warehouse(item_code, company);
        }
        return default_wh_cache[item_code];
    };

    const stage_rows = [];
    const stage_unique_map = {};

    for (const finished_item of products) {
        const etapas = stages_by_product[finished_item] || [];
        const service_stages = etapas.filter(row => !!row.servicio);
        if (!service_stages.length) continue;

        const finished_qty = flt(qty_by_item[finished_item]) || 1;
        const po_row = get_po_row_by_finished_item(frm, finished_item);
        const planned_date =
            (po_row && po_row.planned_start_date) ||
            get_default_planned_start_date(frm);

        for (let index = 0; index < service_stages.length; index++) {
            const etapa = service_stages[index];
            const is_last_stage = index === service_stages.length - 1;
            const parsed_stage = parseInt(etapa.etapa || "", 10);
            const stage_number = Number.isFinite(parsed_stage) && parsed_stage > 0
                ? parsed_stage
                : index + 1;
            const production_item = is_last_stage ? finished_item : (etapa.subensamblaje || finished_item);
            if (!production_item) continue;
            const stage_key = `${finished_item}::${stage_number}`;
            if (stage_unique_map[stage_key]) continue;
            stage_unique_map[stage_key] = 1;

            const service_supplier = etapa.proveedor || "";
            const candidate = {
                production_item,
                parent_item_code: finished_item,
                bom_level: stage_number,
                supplier: service_supplier
            };

            let fg_warehouse = "";
            if (is_last_stage) {
                fg_warehouse = (po_row && po_row.warehouse) ||
                    (await get_default_wh_cached(finished_item)) ||
                    warehouses.wip ||
                    "";
            } else {
                fg_warehouse = warehouses.wip || (await get_default_wh_cached(production_item)) || "";
            }

            const item_data = await get_item_data_cached(production_item);
            const exact_key = get_subassembly_exact_key(candidate);
            const item_key = get_subassembly_item_key(candidate);
            const existing = exact_map[exact_key] || item_map[item_key] || find_matching_subassembly_row(existing_rows, candidate);

            const built_row = {
                production_item,
                parent_item_code: finished_item,
                qty: finished_qty,
                schedule_date: planned_date,
                type_of_manufacturing: "Subcontract",
                supplier: service_supplier,
                fg_warehouse: fg_warehouse,
                bom_no: item_data.bom_no || (existing && existing.bom_no) || "",
                stock_uom: item_data.stock_uom || (existing && existing.stock_uom) || "",
                uom: item_data.stock_uom || (existing && existing.uom) || "",
                bom_level: stage_number,
                indent: index
            };

            Object.assign(built_row, get_preserved_subassembly_fields(existing));
            stage_rows.push(built_row);
        }
    }

    if (!stage_rows.length) return;

    frm.clear_table("sub_assembly_items");
    stage_rows.forEach(row_data => {
        const row = frm.add_child("sub_assembly_items");
        Object.keys(row_data).forEach(key => {
            row[key] = row_data[key];
        });
    });

    frm.refresh_field("sub_assembly_items");
    frm.dirty();
}

async function apply_sub_assembly_defaults(frm, warehouses) {
    const supplier_map = build_subassembly_supplier_map(frm);
    const missing_suppliers = new Set();

    (frm.doc.sub_assembly_items || []).forEach(row => {
        if (!row.fg_warehouse) {
            row.fg_warehouse = warehouses.wip;
        }
        if (row.production_item && supplier_map[row.production_item] && !row.supplier) {
            row.supplier = supplier_map[row.production_item];
        }

        if (row.type_of_manufacturing === "Subcontract" && !row.supplier && row.production_item) {
            missing_suppliers.add(row.production_item);
        }
    });

    if (missing_suppliers.size) {
        const defaults = await call_pp_api_promise(frm, PP_API.GET_DEFAULT_SUPPLIERS, {
            items: Array.from(missing_suppliers),
            company: frm.doc.company || frm.doc.compañia
        });

        (frm.doc.sub_assembly_items || []).forEach(row => {
            if (row.type_of_manufacturing === "Subcontract" && !row.supplier && defaults[row.production_item]) {
                row.supplier = defaults[row.production_item];
            }
        });
    }

    frm.refresh_field("sub_assembly_items");

    const unresolved_rows = [];
    (frm.doc.sub_assembly_items || []).forEach((row, index) => {
        if (row.type_of_manufacturing === "Subcontract" && !row.supplier) {
            unresolved_rows.push(`Fila ${index + 1}: ${row.production_item || "Sin Item"}`);
        }
    });

    if (unresolved_rows.length) {
        show_warning(`No se pudo asignar Proveedor automático en Elementos del subconjunto:<br>${unresolved_rows.join("<br>")}`);
    }
}

function unlock_and_prefill_production_plan_tab(frm) {
    if (!validate_first_tab_for_pp_unlock(frm)) return;

    if (frm.is_new()) {
        frm.save()
            .then(() => unlock_and_prefill_production_plan_tab(frm))
            .catch(() => show_error("No se pudo guardar el Costeo para continuar con el desbloqueo"));
        return;
    }

    sync_pp_header_defaults(frm);
    frm.set_value("company", frm.doc.compañia);
    frm.set_value("posting_date", frm.doc.fecha || frappe.datetime.get_today());
    frm.set_value("customer", frm.doc.cliente || "");
    frm.set_value("project", frm.doc.proyecto || "");
    frm.set_value("get_items_from", "Sales Order");
    frm.set_value("for_warehouse", frm.doc.almacen_materias_primas);
    frm.set_value("sub_assembly_warehouse", frm.doc.almacen_trabajo_en_proceso);
    frm.set_value(
        "include_non_stock_items",
        parseInt(frm.doc.include_non_stock_items || 0, 10) ? frm.doc.include_non_stock_items : 1
    );
    frm.set_value(
        "include_subcontracted_items",
        parseInt(frm.doc.include_subcontracted_items || 0, 10) ? frm.doc.include_subcontracted_items : 1
    );

    get_related_sales_order(frm, async sales_order => {
        if (!sales_order) {
            show_error("No se encontró una Orden de Venta relacionada para prellenar el Plan de Producción");
            return;
        }

        try {
            await set_sales_order_on_pp_tab(frm, sales_order);

            const items_result = await call_pp_api_promise(frm, PP_API.GET_ITEMS, {});
            replace_child_table(frm, "po_items", items_result.po_items || []);
            replace_child_table(frm, "prod_plan_references", items_result.prod_plan_references || []);
            await ensure_po_items_required_fields(frm);

            const subassembly_result = await call_pp_api_promise(frm, PP_API.GET_SUB_ASSEMBLY_ITEMS, {});
            replace_child_table(frm, "sub_assembly_items", subassembly_result.sub_assembly_items || []);
            await ensure_stage_rows_in_subassembly(frm, {
                raw_materials: frm.doc.almacen_materias_primas,
                wip: frm.doc.almacen_trabajo_en_proceso
            });
            await apply_sub_assembly_defaults(frm, {
                raw_materials: frm.doc.almacen_materias_primas,
                wip: frm.doc.almacen_trabajo_en_proceso
            });

            get_items_for_material_requests(frm, [{ warehouse: frm.doc.for_warehouse }]);

            frm.set_value("pp_tab_unlocked", 1);
            set_pp_tab_lock_state(frm);
            show_alert("Plan de Producción desbloqueado y prellenado", "green");

            if (frm.layout && frm.layout.show_tab) {
                frm.layout.show_tab("tab_plan_produccion");
            }
        } catch (error) {
            console.error(error);
            show_error("Ocurrió un error al prellenar el Plan de Producción");
        }
    });
}

function get_items_for_material_requests(frm, warehouses) {
    frappe.call({
        method: "erpnext.manufacturing.doctype.production_plan.production_plan.get_items_for_material_requests",
        freeze: true,
        args: {
            doc: frm.doc,
            warehouses: warehouses || []
        },
        callback: function(r) {
            if (r.message) {
                replace_child_table(frm, "mr_items", r.message);
            } else {
                frm.refresh_field("mr_items");
            }

            apply_raw_material_suppliers_to_mr_items(frm);
        }
    });
}

function show_production_plan_progress(frm) {
    if (!frm.doc.po_items || !frm.doc.po_items.length) return;

    const total_planned = flt(frm.doc.total_planned_qty);
    if (total_planned <= 0) return;

    let item_wise_qty = {};
    (frm.doc.po_items || []).forEach(data => {
        item_wise_qty[data.item_code] = (item_wise_qty[data.item_code] || 0) + flt(data.produced_qty);
    });

    let title = "";
    Object.keys(item_wise_qty).forEach(key => {
        title += __("Item {0}: {1} qty produced. ", [key, item_wise_qty[key]]);
    });

    const bars = [{
        title,
        width: `${(flt(frm.doc.total_produced_qty) / total_planned) * 100}%`,
        progress_class: "progress-bar-success"
    }];

    if (bars[0].width === "0%") bars[0].width = "0.5%";
    frm.dashboard.add_progress(__("Estado Plan Produccion"), bars, title);
}

frappe.ui.form.on(DB.MAIN_DOCTYPE, {
    setup: function(frm) {
        setup_production_plan_queries(frm);
    },

    company: function(frm) {
        if (!frm.doc.compañia && frm.doc.company) {
            frm.set_value("compañia", frm.doc.company);
        }
    },

    compañia: function(frm) {
        if (!frm.doc.company && frm.doc.compañia) {
            frm.set_value("company", frm.doc.compañia);
        }
    },

    fecha: function(frm) {
        if (!frm.doc.posting_date && frm.doc.fecha) {
            frm.set_value("posting_date", frm.doc.fecha);
        }
    },

    cliente: function(frm) {
        if (!frm.doc.customer && frm.doc.cliente) {
            frm.set_value("customer", frm.doc.cliente);
        }
    },

    proyecto: function(frm) {
        if (!frm.doc.project && frm.doc.proyecto) {
            frm.set_value("project", frm.doc.proyecto);
        }
    },

    get_sales_orders: function(frm) {
        call_pp_api(frm, PP_API.GET_SALES_ORDERS, {}, message => {
            replace_child_table(frm, "sales_orders", message.sales_orders || []);
        });
    },

    get_material_request: function(frm) {
        call_pp_api(frm, PP_API.GET_MATERIAL_REQUESTS, {}, message => {
            replace_child_table(frm, "material_requests", message.material_requests || []);
        });
    },

    get_items: function(frm) {
        frm.clear_table("prod_plan_references");
        call_pp_api(frm, PP_API.GET_ITEMS, {}, message => {
            replace_child_table(frm, "po_items", message.po_items || []);
            replace_child_table(frm, "prod_plan_references", message.prod_plan_references || []);
            show_production_plan_progress(frm);
        });
    },

    combine_items: function(frm) {
        frm.clear_table("prod_plan_references");
        call_pp_api(frm, PP_API.COMBINE_ITEMS, {}, message => {
            replace_child_table(frm, "po_items", message.po_items || []);
            replace_child_table(frm, "prod_plan_references", message.prod_plan_references || []);
            if ((frm.doc.sub_assembly_items || []).length > 0) {
                frm.trigger("get_sub_assembly_items");
            }
            show_production_plan_progress(frm);
        });
    },

    combine_sub_items: function(frm) {
        if ((frm.doc.sub_assembly_items || []).length > 0) {
            frm.clear_table("sub_assembly_items");
            frm.trigger("get_sub_assembly_items");
        }
    },

    get_sub_assembly_items: async function(frm) {
        try {
            const message = await call_pp_api_promise(frm, PP_API.GET_SUB_ASSEMBLY_ITEMS, {});
            replace_child_table(frm, "sub_assembly_items", message.sub_assembly_items || []);

            await ensure_stage_rows_in_subassembly(frm, {
                raw_materials: frm.doc.almacen_materias_primas,
                wip: frm.doc.almacen_trabajo_en_proceso
            });

            await apply_sub_assembly_defaults(frm, {
                raw_materials: frm.doc.almacen_materias_primas,
                wip: frm.doc.almacen_trabajo_en_proceso
            });
        } catch (error) {
            console.error(error);
            show_error("No se pudieron cargar correctamente los Elementos del subconjunto");
        }
    },

    get_items_for_mr: function(frm) {
        if (!frm.doc.for_warehouse) {
            frm.toggle_reqd("for_warehouse", true);
            frappe.throw(__("Select the Warehouse"));
        }

        get_items_for_material_requests(frm, [{ warehouse: frm.doc.for_warehouse }]);
    },

    transfer_materials: function(frm) {
        if (!frm.doc.for_warehouse) {
            frm.toggle_reqd("for_warehouse", true);
            frappe.throw(__("Select the Warehouse"));
        }

        frm.set_value("consider_minimum_order_qty", 0);

        if (frm.doc.ignore_existing_ordered_qty) {
            get_items_for_material_requests(frm);
            return;
        }

        const dialog = new frappe.ui.Dialog({
            title: __("Transfer Materials For Warehouse {0}", [frm.doc.for_warehouse]),
            fields: [
                {
                    label: __("Transfer From Warehouses"),
                    fieldtype: "Table MultiSelect",
                    fieldname: "warehouses",
                    options: "Production Plan Material Request Warehouse",
                    get_query: function() {
                        return {
                            filters: {
                                company: frm.doc.company
                            }
                        };
                    }
                },
                {
                    label: __("For Warehouse"),
                    fieldtype: "Link",
                    fieldname: "target_warehouse",
                    read_only: true,
                    default: frm.doc.for_warehouse
                }
            ]
        });

        dialog.show();
        dialog.set_primary_action(__("Get Items"), () => {
            const values = dialog.get_values() || {};
            get_items_for_material_requests(frm, values.warehouses || []);
            dialog.hide();
        });
    },

    download_materials_required: function(frm) {
        const warehouses_data = [];
        if (frm.doc.for_warehouse) {
            warehouses_data.push({ warehouse: frm.doc.for_warehouse });
        }

        frappe.prompt(
            [
                {
                    fieldname: "warehouses",
                    fieldtype: "Table MultiSelect",
                    label: __("Warehouses"),
                    default: warehouses_data,
                    options: "Production Plan Material Request Warehouse",
                    reqd: 1,
                    get_query: function() {
                        return {
                            filters: {
                                company: frm.doc.company
                            }
                        };
                    }
                }
            ],
            row => {
                open_url_post(frappe.request.url, {
                    cmd: "erpnext.manufacturing.doctype.production_plan.production_plan.download_raw_materials",
                    doc: frm.doc,
                    warehouses: row.warehouses
                });
            },
            __("Select Warehouses to get Stock for Materials Planning"),
            __("Get Stock")
        );
    },

    pp_make_work_orders: function(frm) {
        if (frm.is_new()) {
            show_error("Guarda el Costeo antes de crear Work Orders");
            return;
        }

        call_pp_api(frm, PP_API.MAKE_WORK_ORDERS, {}, () => {
            show_alert("Proceso de Work Orders finalizado", "green");
        });
    },

    pp_make_subcontracting_po: function(frm) {
        if (frm.is_new()) {
            show_error("Guarda el Costeo antes de crear Subcontracting PO");
            return;
        }

        call_pp_api(frm, PP_API.MAKE_SUBCONTRACT_PO, {}, () => {
            show_alert("Proceso de Subcontracting PO finalizado", "green");
        });
    },

    pp_make_material_request: function(frm) {
        if (frm.is_new()) {
            show_error("Guarda el Costeo antes de crear Solicitud de Materia Prima");
            return;
        }

        frappe.confirm(
            __("Do you want to submit the material request"),
            () => {
                call_pp_api(frm, PP_API.MAKE_MATERIAL_REQUEST, { submit: 1 }, () => {
                    show_alert("Solicitud de Materia Prima creada y enviada", "green");
                });
            },
            () => {
                call_pp_api(frm, PP_API.MAKE_MATERIAL_REQUEST, { submit: 0 }, () => {
                    show_alert("Solicitud de Materia Prima creada en borrador", "orange");
                });
            }
        );
    }
});

// -----------------------------------------------------------------------------
// Module: 38_production_plan_child_events.js
// -----------------------------------------------------------------------------
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

// -----------------------------------------------------------------------------
// Module: 40_bom_creation.js
// -----------------------------------------------------------------------------
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


// -----------------------------------------------------------------------------
// Module: 50_subcontracting_bom_creation.js
// -----------------------------------------------------------------------------
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


// -----------------------------------------------------------------------------
// Module: 60_child_table_events.js
// -----------------------------------------------------------------------------
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

// -----------------------------------------------------------------------------
// Module: 70_tree_view.js
// -----------------------------------------------------------------------------
// =============================================================================
// TREE VIEW
// =============================================================================

function render_tree_view(frm) {
    if (!frm.fields_dict[DB.TREE_VIEW]) return;

    let productos = frm.doc[DB.T1.FIELD_NAME] || [];
    let detalles = frm.doc[DB.T2.FIELD_NAME] || [];
    let etapas = frm.doc[DB.T3.FIELD_NAME] || [];
    
    fetch_items_cache(productos, detalles, (items_cache) => {
        render_tree_html(frm, productos, detalles, etapas, items_cache);
    });
}

function fetch_items_cache(productos, detalles, callback) {
    let all_items = new Set();
    productos.forEach(prod => { if (prod[DB.T1.ITEM]) all_items.add(prod[DB.T1.ITEM]); });
    detalles.forEach(det => { if (det[DB.T2.ITEM]) all_items.add(det[DB.T2.ITEM]); });
    
    if (all_items.size === 0) {
        callback({});
        return;
    }
    
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Item",
            filters: { name: ["in", Array.from(all_items)] },
            fields: ["name", "item_name", "image", "stock_uom"],
            limit_page_length: 500
        },
        callback: function(r) {
            let cache = {};
            if (r.message) {
                r.message.forEach(item => {
                    cache[item.name] = {
                        item_name: item.item_name,
                        image: item.image,
                        stock_uom: item.stock_uom
                    };
                });
            }
            callback(cache);
        }
    });
}

function load_all_service_prices(etapas, callback) {
    // Ya no se autocompleta el precio desde lista de precios
    callback();
}

function render_tree_html(frm, productos, detalles, etapas, items_cache) {
    let html = '<div class="costeo-tree">';

    productos.forEach(prod => {
        let finished = prod[DB.T1.ITEM];
        if (!finished) return;

        let prod_detalles = detalles.filter(d => d[DB.T2.FINISHED_ITEM] === finished);
        let prod_etapas = etapas.filter(e => e[DB.T3.PRODUCTO_TERMINADO] === finished);
        
        // Calcular costo de materiales
        let costo_materiales = prod_detalles.reduce((sum, d) => sum + (d[DB.T2.TOTAL] || 0), 0);
        
        // Calcular costo de servicios desde las etapas
        let costo_servicios = prod_etapas.reduce((sum, e) => sum + (flt(e.precio_servicio) || 0), 0);
        
        // El shipping_cost viene directamente del campo en T1
        let costo_envio = flt(prod[DB.T1.SHIP_COST]) || 0;
        
        let costo_total = costo_materiales + costo_servicios + costo_envio;
        
        html += render_product_card(prod, finished, prod_detalles, prod_etapas, costo_materiales, costo_servicios, costo_envio, costo_total, items_cache, frm);
    });

    html += '</div>';
    frm.fields_dict[DB.TREE_VIEW].$wrapper.html(html);
    
    // Bind eventos después de renderizar
    bind_tree_view_events(frm);
}

function render_product_card(prod, finished, detalles, etapas, costo_materiales, costo_servicios, costo_envio, costo_total, items_cache, frm) {
    let prod_info = items_cache[finished] || { image: null, item_name: finished };
    let prod_image = prod_info.image || '/assets/frappe/images/no-image.png';
    let prod_name = prod_info.item_name || finished;
    let qty = prod[DB.T1.QTY] || 1;
    
    // Calcular valores
    let overhead_pct = flt(prod[DB.T1.OVERHEAD_PCT]) || 0;
    let overhead_amt = costo_total * (overhead_pct / 100);
    let total_cost = costo_total + overhead_amt;
    let sales_price = flt(prod[DB.T1.SALES_PRICE]) || 0;
    let margin_pct = flt(prod[DB.T1.MARGIN_PCT]) || 0;
    
    // Si hay precio de venta pero no margen, calcularlo
    if (sales_price > 0 && total_cost > 0 && margin_pct === 0) {
        margin_pct = ((sales_price - total_cost) / sales_price) * 100;
    }
    
    return `
        <div class="tree-product">
            <div class="tree-header">
                <div class="tree-header-left">
                    <div class="tree-product-image">
                        <img src="${prod_image}" alt="${finished}">
                    </div>
                    <div class="tree-product-info">
                        <div class="tree-title">
                            <span class="indicator orange"></span> 
                            <b>${prod_name}</b>
                        </div>
                        <div class="tree-subtitle">
                            <span><span class="label">Código:</span> ${finished}</span>
                            <span><span class="label">Cantidad:</span> ${qty} ${prod_info.stock_uom || 'unidades'}</span>
                        </div>
                    </div>
                </div>
                <div class="tree-actions">
                    <div class="tree-total-badge">
                        <span class="label-text">Costo Total</span>
                        <span class="total-amount">$ ${format_currency(total_cost)}</span>
                    </div>
                    <button class="btn btn-xs edit-detail" data-item="${finished}">Editar Desglose</button>
                </div>
            </div>
            
            <!-- Desglose de costos -->
            <div class="tree-cost-breakdown">
                <div class="cost-item">
                    <span class="cost-label">Materiales:</span>
                    <span class="cost-value">$ ${format_currency(costo_materiales)}</span>
                </div>
                <div class="cost-item">
                    <span class="cost-label">Servicios:</span>
                    <span class="cost-value">$ ${format_currency(costo_servicios)}</span>
                </div>
                <div class="cost-item">
                    <span class="cost-label">Envío:</span>
                    <span class="cost-value">$ ${format_currency(costo_envio)}</span>
                </div>
                <div class="cost-item cost-subtotal">
                    <span class="cost-label">Subtotal:</span>
                    <span class="cost-value">$ ${format_currency(costo_total)}</span>
                </div>
            </div>
            
            <!-- Sección de campos editables -->
            <div class="tree-fields-section">
                <div class="tree-field-group">
                    <label class="tree-field-label">Gastos de Operación (%)</label>
                    <div class="tree-field-input-group">
                        <input type="number" 
                               class="form-control tree-field-input overhead-input" 
                               data-item="${finished}"
                               data-row-name="${prod.name}"
                               value="${overhead_pct}"
                               step="0.01"
                               min="0">
                        <span class="tree-field-suffix">%</span>
                    </div>
                    <div class="tree-field-help">Overhead: $ ${format_currency(overhead_amt)}</div>
                </div>
                
                <div class="tree-field-group">
                    <label class="tree-field-label">Precio de Venta</label>
                    <div class="tree-field-input-group">
                        <span class="tree-field-prefix">$</span>
                        <input type="number" 
                               class="form-control tree-field-input sales-price-input" 
                               data-item="${finished}"
                               data-row-name="${prod.name}"
                               value="${sales_price}"
                               step="0.01"
                               min="0">
                    </div>
                    <div class="tree-field-help">Costo: $ ${format_currency(total_cost)}</div>
                </div>
                
                <div class="tree-field-group">
                    <label class="tree-field-label">Margen (%)</label>
                    <div class="tree-field-input-group">
                        <input type="number" 
                               class="form-control tree-field-input margin-input" 
                               data-item="${finished}"
                               data-row-name="${prod.name}"
                               value="${margin_pct.toFixed(2)}"
                               step="0.01"
                               min="0"
                               max="100">
                        <span class="tree-field-suffix">%</span>
                    </div>
                    <div class="tree-field-help">Utilidad: $ ${format_currency(sales_price - total_cost)}</div>
                </div>
            </div>
            
            <ul class="tree-details">
                ${render_product_details(detalles, etapas, items_cache)}
            </ul>
        </div>
    `;
}

function bind_tree_view_events(frm) {
    // Evento para botón de editar desglose
    $(frm.fields_dict[DB.TREE_VIEW].$wrapper).off('click', '.edit-detail');
    $(frm.fields_dict[DB.TREE_VIEW].$wrapper).on('click', '.edit-detail', function(e) {
        e.preventDefault();
        let finished_item = $(this).data("item");
        open_detail_editor(frm, finished_item);
    });
    
    // Evento para overhead
    $(frm.fields_dict[DB.TREE_VIEW].$wrapper).off('change', '.overhead-input');
    $(frm.fields_dict[DB.TREE_VIEW].$wrapper).on('change', '.overhead-input', function() {
        let row_name = $(this).data('row-name');
        let value = flt($(this).val());
        update_product_field(frm, row_name, DB.T1.OVERHEAD_PCT, value);
    });
    
    // Evento para precio de venta
    $(frm.fields_dict[DB.TREE_VIEW].$wrapper).off('change', '.sales-price-input');
    $(frm.fields_dict[DB.TREE_VIEW].$wrapper).on('change', '.sales-price-input', function() {
        let row_name = $(this).data('row-name');
        let value = flt($(this).val());
        
        frappe.model.set_value(DB.T1.DOCTYPE_ID, row_name, DB.T1.SALES_PRICE, value);
        
        // Recalcular el margen basado en el nuevo precio
        let row = locals[DB.T1.DOCTYPE_ID][row_name];
        if (row && row[DB.T1.TOTAL_COST] > 0) {
            recalc_margin(frm, DB.T1.DOCTYPE_ID, row_name);
        }
        
        frm.dirty();
        render_tree_view(frm);
    });
    
    // Evento para margen
    $(frm.fields_dict[DB.TREE_VIEW].$wrapper).off('change', '.margin-input');
    $(frm.fields_dict[DB.TREE_VIEW].$wrapper).on('change', '.margin-input', function() {
        let row_name = $(this).data('row-name');
        let value = flt($(this).val());
        
        frappe.model.set_value(DB.T1.DOCTYPE_ID, row_name, DB.T1.MARGIN_PCT, value);
        
        // Recalcular el precio basado en el nuevo margen
        let row = locals[DB.T1.DOCTYPE_ID][row_name];
        if (row && row[DB.T1.TOTAL_COST] > 0) {
            recalc_sales_price(frm, DB.T1.DOCTYPE_ID, row_name);
        }
        
        frm.dirty();
        render_tree_view(frm);
    });
}

function update_product_field(frm, row_name, fieldname, value) {
    frappe.model.set_value(DB.T1.DOCTYPE_ID, row_name, fieldname, value);
    
    // Si es overhead, recalcular totales
    if (fieldname === DB.T1.OVERHEAD_PCT) {
        let row = locals[DB.T1.DOCTYPE_ID][row_name];
        if (row) {
            calc_t1_row(frm, DB.T1.DOCTYPE_ID, row_name);
        }
    }
    
    frm.dirty();
    render_tree_view(frm);
}

function render_product_details(detalles, etapas, items_cache) {
    if (detalles.length === 0 && etapas.length === 0) {
        return '<li class="muted">Sin costos asociados</li>';
    }
    
    let html = '';
    
    // Primero renderizar servicios de etapas
    if (etapas.length > 0) {
        etapas.forEach(etapa => {
            if (etapa[DB.T3.SERVICIO]) {
                html += render_service_row(etapa, items_cache);
            }
        });
    }
    
    // Luego renderizar materiales
    detalles.forEach(d => {
        html += render_detail_row(d, items_cache);
    });
    
    return html;
}

function render_service_row(etapa, items_cache) {
    let servicio_code = etapa[DB.T3.SERVICIO] || '';
    let servicio_info = items_cache[servicio_code] || { item_name: servicio_code };
    let display_name = servicio_info.item_name || servicio_code || 'Sin Servicio';
    let etapa_badge = etapa[DB.T3.ETAPA] ? `<span class="etapa-badge">Etapa ${etapa[DB.T3.ETAPA]}</span>` : '';
    let precio = flt(etapa.precio_servicio) || 0;
    
    return `
        <li>
            <div class="material-row">
                <div class="material-info">
                    <div class="material-name">
                        <b>${display_name}</b>${etapa_badge}<span class="service-badge">SERVICIO</span>
                    </div>
                    <div class="material-details">
                        <span class="detail-item"><span class="detail-label">Código:</span> <span class="detail-value">${servicio_code}</span></span>
                        <span class="detail-item"><span class="detail-label">Proveedor:</span> <span class="detail-value">${etapa[DB.T3.PROVEEDOR] || 'Sin Proveedor'}</span></span>
                        ${etapa[DB.T3.SUBENSAMBLAJE] ? `<span class="detail-item"><span class="detail-label">Sub-ensamblaje:</span> <span class="detail-value">${etapa[DB.T3.SUBENSAMBLAJE]}</span></span>` : ''}
                    </div>
                </div>
                <div class="material-total">
                    <span class="total-label">Total</span>
                    <span class="total-value">$ ${format_currency(precio)}</span>
                </div>
            </div>
        </li>
    `;
}

function render_detail_row(detalle, items_cache) {
    let item_info = items_cache[detalle[DB.T2.ITEM]] || { item_name: detalle[DB.T2.ITEM] };
    let display_name = item_info.item_name || detalle[DB.T2.ITEM] || 'Sin Item';
    let item_code = detalle[DB.T2.ITEM] || '';
    let etapa_badge = detalle[DB.T2.ETAPA] ? `<span class="etapa-badge">Etapa ${detalle[DB.T2.ETAPA]}</span>` : '';
    
    return `
        <li>
            <div class="material-row">
                <div class="material-info">
                    <div class="material-name">
                        <b>${display_name}</b>${etapa_badge}
                    </div>
                    <div class="material-details">
                        <span class="detail-item"><span class="detail-label">Código:</span> <span class="detail-value">${item_code}</span></span>
                        <span class="detail-item"><span class="detail-label">Consumo:</span> <span class="detail-value">${flt(detalle[DB.T2.INT_QTY])} ${detalle[DB.T2.INT_UOM] || ''}</span></span>
                        <span class="detail-item"><span class="detail-label">Proveedor:</span> <span class="detail-value">${detalle[DB.T2.SUPPLIER] || 'Sin Proveedor'}</span></span>
                        <span class="detail-item"><span class="detail-label">Precio Unitario:</span> <span class="detail-value">$ ${format_currency(detalle[DB.T2.UNIT_PRICE])}</span></span>
                    </div>
                </div>
                <div class="material-total">
                    <span class="total-label">Total</span>
                    <span class="total-value">$ ${format_currency(detalle[DB.T2.TOTAL])}</span>
                </div>
            </div>
        </li>
    `;
}


// -----------------------------------------------------------------------------
// Module: 80_detail_editor_modal.js
// -----------------------------------------------------------------------------
// =============================================================================
// EDITOR MODAL
// =============================================================================

function open_detail_editor(frm, finished_item) {
    let materiales = (frm.doc[DB.T2.FIELD_NAME] || [])
        .filter(r => r[DB.T2.FINISHED_ITEM] === finished_item)
        .map(clone_row_data);
    let etapas = (frm.doc[DB.T3.FIELD_NAME] || [])
        .filter(e => e[DB.T3.PRODUCTO_TERMINADO] === finished_item)
        .map(clone_row_data);
    
    // Obtener el producto para el shipping_cost
    let producto = (frm.doc[DB.T1.FIELD_NAME] || []).find(p => p[DB.T1.ITEM] === finished_item);
    let shipping_cost = producto ? flt(producto[DB.T1.SHIP_COST]) : 0;
    
    let dialog = create_editor_dialog(finished_item, etapas, materiales, shipping_cost, frm);
    dialog.show();
    
    setup_dialog_events(dialog);
}

function create_editor_dialog(finished_item, etapas, materiales, shipping_cost, frm) {
    return new frappe.ui.Dialog({
        title: `Desglose: ${finished_item}`,
        size: "extra-large",
        fields: get_dialog_fields(etapas, materiales, shipping_cost),
        primary_action_label: "Aceptar",
        primary_action(values) {
            if (!validate_dialog_data(values)) return;
            
            save_dialog_data(frm, finished_item, values);
            
            calculate_aggregates(frm);
            render_tree_view(frm);
            
            show_alert('Cambios aplicados. Guarda el documento para confirmar.', 'green');
            this.hide();
        }
    });
}

function get_dialog_fields(etapas, materiales, shipping_cost) {
    return [
        { fieldname: "section_shipping", fieldtype: "Section Break", label: "💰 Costos de Envío" },
        {
            fieldname: "shipping_cost_temp",
            fieldtype: "Currency",
            label: "Costo de Envío Unitario",
            description: "Ingresa el costo de envío por unidad de producto",
            default: shipping_cost
        },
        { fieldname: "section_etapas", fieldtype: "Section Break", label: "🔧 Etapas de Producción" },
        {
            fieldname: "etapas_temp",
            fieldtype: "Table",
            label: "Configuración de Etapas",
            cannot_add_rows: false,
            in_place_edit: true,
            data: etapas,
            fields: [
                { fieldname: DB.T3.ETAPA, label: "Etapa", fieldtype: "Select", options: "1\n2\n3\n4\n5", in_list_view: 1, reqd: 1, columns: 1 },
                { fieldname: DB.T3.SERVICIO, label: "Servicio", fieldtype: "Link", options: "Item", in_list_view: 1, columns: 2 },
                { fieldname: DB.T3.PROVEEDOR, label: "Proveedor", fieldtype: "Link", options: "Supplier", in_list_view: 1, columns: 2 },
                { fieldname: "precio_servicio", label: "Precio", fieldtype: "Currency", in_list_view: 1, columns: 1 },
                { fieldname: DB.T3.SUBENSAMBLAJE, label: "Sub-ensamblaje", fieldtype: "Link", options: "Item", in_list_view: 1, columns: 2 }
            ]
        },
        { fieldname: "section_materiales", fieldtype: "Section Break", label: "📦 Materiales y Servicios" },
        {
            fieldname: "detalle_temp",
            fieldtype: "Table",
            label: "Costos Directos",
            cannot_add_rows: false,
            in_place_edit: true,
            data: materiales,
            fields: [
                { fieldname: DB.T2.ETAPA, label: "Etapa", fieldtype: "Select", options: "\n1\n2\n3\n4\n5", in_list_view: 1, columns: 1 },
                { fieldname: DB.T2.ITEM, label: "Producto", fieldtype: "Link", options: "Item", in_list_view: 1, reqd: 1, columns: 2 },
                { fieldname: DB.T2.INT_QTY, label: "Consumo", fieldtype: "Float", in_list_view: 1, columns: 1, reqd: 1 },
                { fieldname: DB.T2.INT_UOM, label: "UOM", fieldtype: "Data", in_list_view: 1, columns: 1, read_only: 1 },
                { fieldname: DB.T2.SUPPLIER, label: "Proveedor", fieldtype: "Link", options: "Supplier", in_list_view: 1, columns: 2, reqd: 1 },
                { fieldname: DB.T2.SUP_UOM, label: "UOM Prov", fieldtype: "Data", in_list_view: 1, columns: 1, read_only: 1 },
                { fieldname: DB.T2.SUP_QTY, label: "Cant. Compra", fieldtype: "Float", in_list_view: 1, columns: 1, read_only: 1 },
                { fieldname: DB.T2.UNIT_PRICE, label: "Precio U.", fieldtype: "Currency", in_list_view: 1, columns: 1, read_only: 1 },
                { fieldname: DB.T2.TOTAL, label: "Total", fieldtype: "Currency", in_list_view: 1, columns: 1, read_only: 1 },
                { fieldname: DB.T2.CONV_FACTOR, fieldtype: "Float", hidden: 1 },
                { fieldname: DB.T2.CONCEPT_TYPE, fieldtype: "Data", hidden: 1 }
            ]
        },
        { fieldname: "section_instrucciones", fieldtype: "Section Break", label: "📋 Instrucciones" },
        {
            fieldname: "instrucciones_html",
            fieldtype: "HTML",
            options: `
                <div style="background: #f8f9fa; padding: 15px; border-radius: 6px; border-left: 4px solid #FF6B15;">
                    <h5 style="margin-top: 0; color: #FF6B15;">Reglas:</h5>
                    <ul style="margin-bottom: 0; line-height: 1.8;">
                        <li><strong>Envío:</strong> Ingresa el costo unitario de envío en el campo de arriba</li>
                        <li><strong>Etapa 1:</strong> Debe contener toda la materia prima necesaria</li>
                        <li><strong>Servicio único:</strong> Un servicio por etapa</li>
                        <li><strong>Proveedores:</strong> En Etapas = proveedor del servicio | En Materiales = proveedor del material</li>
                        <li><strong>Costos de servicios:</strong> Se calculan automáticamente desde las etapas</li>
                    </ul>
                </div>
            `
        }
    ];
}

function validate_dialog_data(values) {
    let etapas = values.etapas_temp || [];
    let servicios_por_etapa = {};
    
    for (let row of etapas) {
        let etapa = row[DB.T3.ETAPA];
        let servicio = row[DB.T3.SERVICIO];
        
        if (etapa && servicio) {
            if (servicios_por_etapa[etapa] && servicios_por_etapa[etapa] !== servicio) {
                show_error(`La Etapa ${etapa} tiene más de un servicio. Solo uno por etapa.`);
                return false;
            }
            servicios_por_etapa[etapa] = servicio;
        }
    }
    
    return true;
}

function save_dialog_data(frm, finished_item, values) {
    let etapas_temp = values.etapas_temp || [];
    let shipping_cost_temp = flt(values.shipping_cost_temp) || 0;
    let etapa_info = build_etapa_info_map(etapas_temp);
    
    // IMPORTANTE: Guardar shipping_cost PRIMERO antes de guardar etapas y materiales
    save_shipping_cost_to_product(frm, finished_item, shipping_cost_temp);
    
    save_etapas_to_doc(frm, finished_item, etapas_temp);
    save_materiales_to_doc(frm, finished_item, values.detalle_temp || [], etapa_info);
    
    frm.refresh_field(DB.T3.FIELD_NAME);
    frm.refresh_field(DB.T2.FIELD_NAME);
    frm.refresh_field(DB.T1.FIELD_NAME);
    frm.dirty();
}

function build_etapa_info_map(etapas) {
    let map = {};
    etapas.forEach(e => {
        if (e[DB.T3.ETAPA]) {
            map[e[DB.T3.ETAPA]] = {
                servicio: e[DB.T3.SERVICIO] || '',
                proveedor: e[DB.T3.PROVEEDOR] || '',
                subensamblaje: e[DB.T3.SUBENSAMBLAJE] || '',
                precio_servicio: flt(e.precio_servicio) || 0
            };
        }
    });
    return map;
}

function save_etapas_to_doc(frm, finished_item, etapas_temp) {
    let current_etapas = frm.doc[DB.T3.FIELD_NAME] || [];
    let otras_etapas = current_etapas.filter(e => e[DB.T3.PRODUCTO_TERMINADO] !== finished_item);
    
    frm.doc[DB.T3.FIELD_NAME] = [];
    
    otras_etapas.forEach(etapa => {
        let new_row = frappe.model.add_child(frm.doc, DB.T3.DOCTYPE_ID, DB.T3.FIELD_NAME);
        copy_row_data(etapa, new_row);
    });
    
    etapas_temp.forEach(etapa_modal => {
        let new_row = frappe.model.add_child(frm.doc, DB.T3.DOCTYPE_ID, DB.T3.FIELD_NAME);
        new_row[DB.T3.PRODUCTO_TERMINADO] = finished_item;
        copy_row_data(etapa_modal, new_row, [DB.T3.PRODUCTO_TERMINADO]);
        // Asegurar que el precio quede persistido en Etapas Costeo
        if (etapa_modal && etapa_modal.precio_servicio !== undefined) {
            new_row.precio_servicio = flt(etapa_modal.precio_servicio) || 0;
        }
    });
}

function save_materiales_to_doc(frm, finished_item, materiales_temp, etapa_info) {
    let clean_materials = frm.doc[DB.T2.FIELD_NAME].filter(r => r[DB.T2.FINISHED_ITEM] !== finished_item);
    frm.doc[DB.T2.FIELD_NAME] = clean_materials;

    materiales_temp.forEach(r => {
        let new_row = frappe.model.add_child(frm.doc, DB.T2.DOCTYPE_ID, DB.T2.FIELD_NAME);
        copy_row_data(r, new_row);
        new_row[DB.T2.FINISHED_ITEM] = finished_item;
        new_row[DB.T2.CONCEPT_TYPE] = new_row[DB.T2.CONCEPT_TYPE] || "Materia Prima";
        
        let etapa_num = r[DB.T2.ETAPA];
        if (etapa_num && etapa_info[etapa_num]) {
            new_row[DB.T2.SERVICIO] = etapa_info[etapa_num].servicio;
            new_row[DB.T2.PROVEEDOR_SERVICIO] = etapa_info[etapa_num].proveedor;
            new_row[DB.T2.SUBENSAMBLAJE] = etapa_info[etapa_num].subensamblaje;
        }
    });
}

function save_shipping_cost_to_product(frm, finished_item, shipping_cost) {
    let productos = frm.doc[DB.T1.FIELD_NAME] || [];
    
    for (let i = 0; i < productos.length; i++) {
        if (productos[i][DB.T1.ITEM] === finished_item) {
            // Usar set_value para que el cambio quede registrado en el modelo
            frappe.model.set_value(
                productos[i].doctype,
                productos[i].name,
                DB.T1.SHIP_COST,
                flt(shipping_cost)
            );
            
            // Recalcular costos
            calc_t1_row(frm, productos[i].doctype, productos[i].name);
            
            break;
        }
    }
}

function copy_row_data(source, target, exclude = []) {
    Object.keys(source).forEach(key => {
        if (!key.startsWith('__') && key !== 'idx' && key !== 'docstatus' && !exclude.includes(key)) {
            target[key] = source[key];
        }
    });
}

function clone_row_data(source) {
    let obj = {};
    Object.keys(source || {}).forEach(key => {
        if (!key.startsWith('__') && key !== 'idx' && key !== 'docstatus' && key !== 'name' && key !== 'doctype') {
            obj[key] = source[key];
        }
    });
    return obj;
}

function setup_dialog_events(dialog) {
    setup_etapas_grid_filters(dialog);
    setup_materiales_grid_events(dialog);
    enable_grid_links(dialog);
}

function enable_grid_links(dialog) {
    // Habilitar links en tabla de etapas
    setTimeout(() => {
        let etapas_grid = dialog.fields_dict.etapas_temp.grid;
        if (etapas_grid && etapas_grid.$wrapper) {
            etapas_grid.$wrapper.on('click', 'a[data-doctype]', function(e) {
                e.preventDefault();
                let doctype = $(this).data('doctype');
                let docname = $(this).data('name');
                if (doctype && docname) {
                    frappe.set_route('Form', doctype, docname);
                }
            });
        }
        
        // Habilitar links en tabla de materiales
        let materiales_grid = dialog.fields_dict.detalle_temp.grid;
        if (materiales_grid && materiales_grid.$wrapper) {
            materiales_grid.$wrapper.on('click', 'a[data-doctype]', function(e) {
                e.preventDefault();
                let doctype = $(this).data('doctype');
                let docname = $(this).data('name');
                if (doctype && docname) {
                    frappe.set_route('Form', doctype, docname);
                }
            });
        }
    }, 500);
}

function setup_etapas_grid_filters(dialog) {
    let grid = dialog.fields_dict.etapas_temp.grid;
    
    setTimeout(() => {
        grid.grid_rows.forEach(grid_row => {
            set_grid_field_filter(grid_row, DB.T3.SERVICIO, DB.GROUPS.SERVICES);
            set_grid_field_filter(grid_row, DB.T3.SUBENSAMBLAJE, [DB.GROUPS.SUBASSEMBLY, DB.GROUPS.FINISHED]);
            setup_etapa_row_events(grid, grid_row);
        });
    }, 300);
    
    // Interceptar la adición de nuevas filas
    let original_add_row = grid.add_new_row;
    grid.add_new_row = function(idx, callback, show) {
        let result = original_add_row.call(this, idx, callback, show);
        setTimeout(() => {
            if (grid.grid_rows && grid.grid_rows.length > 0) {
                let new_row = grid.grid_rows[grid.grid_rows.length - 1];
                set_grid_field_filter(new_row, DB.T3.SERVICIO, DB.GROUPS.SERVICES);
                set_grid_field_filter(new_row, DB.T3.SUBENSAMBLAJE, [DB.GROUPS.SUBASSEMBLY, DB.GROUPS.FINISHED]);
                setup_etapa_row_events(grid, new_row);
            }
        }, 200);
        return result;
    };
}

function set_grid_field_filter(grid_row, fieldname, item_group) {
    let field = grid_row.get_field(fieldname);
    if (field && field.df) {
        field.df.get_query = () => {
            if (Array.isArray(item_group)) {
                return { filters: { 'item_group': ['in', item_group] } };
            }
            return { filters: { 'item_group': item_group } };
        };
    }
}

function setup_etapa_row_events(grid, grid_row) {
    if (!grid_row || !grid_row.doc) return;
    
    let row = grid_row.doc;
}

function setup_materiales_grid_events(dialog) {
    let grid = dialog.fields_dict.detalle_temp.grid;
    
    setTimeout(() => {
        grid.grid_rows.forEach(grid_row => setup_modal_row_events(grid, grid_row));
    }, 300);
    
    let original_add_row = grid.add_new_row;
    grid.add_new_row = function(idx, callback, show) {
        let result = original_add_row.call(this, idx, callback, show);
        setTimeout(() => {
            if (grid.grid_rows && grid.grid_rows.length > 0) {
                setup_modal_row_events(grid, grid.grid_rows[grid.grid_rows.length - 1]);
            }
        }, 200);
        return result;
    };
}

function setup_modal_row_events(grid, grid_row) {
    if (!grid_row || !grid_row.doc) return;
    
    let row = grid_row.doc;
    
    setup_item_select_event(grid, grid_row, row);
    setup_supplier_select_event(grid, grid_row, row);
    setup_qty_change_event(grid, grid_row, row);
}

function setup_item_select_event(grid, grid_row, row) {
    let field = grid_row.get_field(DB.T2.ITEM);
    if (field && field.$input) {
        field.$input.off('awesomplete-selectcomplete.modal_auto');
        field.$input.on('awesomplete-selectcomplete.modal_auto', function() {
            setTimeout(() => {
                if (row[DB.T2.ITEM]) {
                    frappe.db.get_value('Item', row[DB.T2.ITEM], 'stock_uom', (r) => {
                        if (r && r.stock_uom) {
                            row[DB.T2.INT_UOM] = r.stock_uom;
                            grid.refresh_row(row.name);
                            
                            if (row[DB.T2.SUPPLIER]) {
                                fetch_modal_item_price(grid, row);
                            }
                        }
                    });
                }
            }, 250);
        });
    }
}

function setup_supplier_select_event(grid, grid_row, row) {
    let field = grid_row.get_field(DB.T2.SUPPLIER);
    if (field && field.$input) {
        field.$input.off('awesomplete-selectcomplete.modal_auto');
        field.$input.on('awesomplete-selectcomplete.modal_auto', function() {
            setTimeout(() => {
                if (row[DB.T2.ITEM] && row[DB.T2.SUPPLIER]) {
                    fetch_modal_item_price(grid, row);
                }
            }, 250);
        });
    }
}

function setup_qty_change_event(grid, grid_row, row) {
    let field = grid_row.get_field(DB.T2.INT_QTY);
    if (field && field.$input) {
        field.$input.off('change.modal_auto');
        field.$input.on('change.modal_auto', function() {
            setTimeout(() => {
                row[DB.T2.INT_QTY] = flt($(this).val());
                calculate_modal_row(grid, row);
            }, 100);
        });
    }
}

function fetch_modal_item_price(grid, row) {
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
                row[DB.T2.UNIT_PRICE] = data.price_list_rate;
                row[DB.T2.SUP_UOM] = data.uom;
                grid.refresh_row(row.name);
                calculate_modal_conversion(grid, row);
            } else {
                show_alert('No hay lista de precios para este proveedor', 'orange');
                row[DB.T2.UNIT_PRICE] = 0;
                row[DB.T2.SUP_UOM] = row[DB.T2.INT_UOM];
                grid.refresh_row(row.name);
                calculate_modal_conversion(grid, row);
            }
        }
    });
}

function calculate_modal_conversion(grid, row) {
    let uom_int = row[DB.T2.INT_UOM];
    let uom_sup = row[DB.T2.SUP_UOM];

    if (!uom_sup || uom_sup === uom_int) {
        row[DB.T2.CONV_FACTOR] = 1;
        calculate_modal_row(grid, row);
    } else {
        frappe.call({
            method: "frappe.client.get",
            args: { doctype: "Item", name: row[DB.T2.ITEM] },
            callback: function(r) {
                let factor = 1;
                if (r.message && r.message.uoms) {
                    let uom = r.message.uoms.find(d => d.uom == uom_sup);
                    if (uom) factor = uom.conversion_factor;
                }
                row[DB.T2.CONV_FACTOR] = factor;
                calculate_modal_row(grid, row);
            }
        });
    }
}

function calculate_modal_row(grid, row) {
    let int_qty = flt(row[DB.T2.INT_QTY]);
    let factor = flt(row[DB.T2.CONV_FACTOR]) || 1;
    let price = flt(row[DB.T2.UNIT_PRICE]);

    row[DB.T2.SUP_QTY] = int_qty / factor;
    row[DB.T2.TOTAL] = row[DB.T2.SUP_QTY] * price;
    
    grid.refresh_row(row.name);
}


// -----------------------------------------------------------------------------
// Module: 90_calculations.js
// -----------------------------------------------------------------------------
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


// -----------------------------------------------------------------------------
// Module: 99_utils_and_styles.js
// -----------------------------------------------------------------------------
// =============================================================================
// UTILIDADES
// =============================================================================

function show_error(message) {
    frappe.msgprint({ title: 'Error', indicator: 'red', message });
}

function show_warning(message) {
    frappe.msgprint({ title: 'Advertencia', indicator: 'orange', message });
}

function show_alert(message, indicator) {
    frappe.show_alert({ message, indicator }, 3);
}

function show_completion_message(total, errors, title) {
    if (errors.length > 0) {
        frappe.msgprint({
            title: `${title} con Advertencias`,
            indicator: 'orange',
            message: `Se crearon ${total} documentos.<br><br><b>Advertencias:</b><br>${errors.join('<br>')}`
        });
    } else {
        frappe.msgprint({
            title: 'Éxito',
            indicator: 'green',
            message: `Se crearon ${total} documentos correctamente`
        });
    }
}

function get_error_message(response) {
    if (response._server_messages) {
        try {
            let messages = JSON.parse(response._server_messages);
            return messages.join('<br>');
        } catch (e) {}
    }
    return response.message || 'Error desconocido';
}

function format_currency(value) {
    return flt(value).toLocaleString(undefined, { minimumFractionItems: 2, maximumFractionDigits: 2 });
}

function inject_css() {
    let css = `
        <style>
            .costeo-tree { 
                padding: 0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
                background: #ffffff;
            }

            .costeo-tree .tree-product:first-child { margin-top: 16px; }
            .costeo-tree .tree-product { margin-left: 0; margin-right: 0; }

            .costeo-black-create-btn,
            .costeo-black-create-btn:hover,
            .costeo-black-create-btn:focus,
            .costeo-black-create-btn:active {
                background: #111111 !important;
                border-color: #111111 !important;
                color: #ffffff !important;
            }
            
            .tree-product { 
                border: 1px solid #e4e7eb;
                border-radius: 8px;
                margin-bottom: 16px;
                background: #ffffff;
                overflow: hidden;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
            }
            
            .tree-header { 
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 14px 18px;
                background: #ffffff;
                border-bottom: 1px solid #f0f2f5;
                flex-wrap: wrap;
                gap: 12px;
            }
            
            .tree-header-left {
                display: flex;
                align-items: center;
                gap: 14px;
                flex: 1;
                min-width: 280px;
            }
            
            .tree-product-image {
                width: 60px;
                height: 60px;
                border-radius: 6px;
                overflow: hidden;
                border: 1px solid #e4e7eb;
                background: #f8f9fa;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
            }
            
            .tree-product-image img {
                max-width: 100%;
                max-height: 100%;
                object-fit: contain;
            }
            
            .tree-product-info {
                display: flex;
                flex-direction: column;
                gap: 6px;
                flex: 1;
                min-width: 0;
            }
            
            .tree-title {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 15px;
                font-weight: 600;
                color: #1a202c;
                letter-spacing: -0.2px;
                word-wrap: break-word;
            }
            
            .tree-subtitle {
                display: flex;
                align-items: center;
                gap: 14px;
                font-size: 12px;
                color: #64748b;
                flex-wrap: wrap;
            }
            
            .tree-subtitle .label {
                font-weight: 500;
                color: #475569;
            }
            
            .indicator.orange {
                background-color: #FF6B15 !important;
                width: 7px;
                height: 7px;
                border-radius: 50%;
                display: inline-block;
                flex-shrink: 0;
            }
            
            .tree-actions {
                display: flex;
                align-items: center;
                gap: 14px;
                flex-wrap: wrap;
            }
            
            .tree-total-badge {
                display: flex;
                flex-direction: column;
                align-items: flex-end;
                gap: 2px;
            }
            
            .tree-total-badge .label-text {
                font-size: 10px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.4px;
                color: #64748b;
            }
            
            .total-amount {
                font-size: 20px;
                font-weight: 700;
                color: #1a202c;
                letter-spacing: -0.4px;
            }
            
            .edit-detail {
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 500;
                border-radius: 6px;
                border: 1px solid #e4e7eb;
                background: #ffffff;
                color: #475569;
                white-space: nowrap;
            }
            
            /* Desglose de costos */
            .tree-cost-breakdown {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: 10px;
                padding: 14px 18px;
                background: #f8f9fa;
                border-bottom: 1px solid #e4e7eb;
            }
            
            .cost-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 8px 12px;
                background: #ffffff;
                border-radius: 6px;
                border: 1px solid #e4e7eb;
            }
            
            .cost-item.cost-subtotal {
                background: #fff4ed;
                border-color: #FF6B15;
                font-weight: 600;
            }
            
            .cost-label {
                font-size: 11px;
                font-weight: 600;
                color: #64748b;
                text-transform: uppercase;
                letter-spacing: 0.3px;
            }
            
            .cost-item.cost-subtotal .cost-label {
                color: #FF6B15;
            }
            
            .cost-value {
                font-size: 13px;
                font-weight: 700;
                color: #1a202c;
            }
            
            .cost-item.cost-subtotal .cost-value {
                color: #FF6B15;
                font-size: 14px;
            }
            
            /* Sección de campos editables */
            .tree-fields-section {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
                gap: 14px;
                padding: 16px 18px;
                background: #f8f9fa;
                border-bottom: 1px solid #e4e7eb;
            }
            
            .tree-field-group {
                display: flex;
                flex-direction: column;
                gap: 6px;
            }
            
            .tree-field-label {
                font-size: 11px;
                font-weight: 600;
                color: #475569;
                text-transform: uppercase;
                letter-spacing: 0.4px;
                margin: 0;
            }
            
            .tree-field-input-group {
                display: flex;
                align-items: center;
                gap: 6px;
                position: relative;
            }
            
            .tree-field-input {
                flex: 1;
                padding: 8px 10px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
                color: #1a202c;
                background: #ffffff;
                transition: all 0.2s;
            }
            
            .tree-field-input:focus {
                outline: none;
                border-color: #FF6B15;
                box-shadow: 0 0 0 2px rgba(255, 107, 21, 0.1);
            }
            
            .tree-field-prefix,
            .tree-field-suffix {
                font-size: 13px;
                font-weight: 600;
                color: #64748b;
                min-width: 20px;
                text-align: center;
            }
            
            .tree-field-help {
                font-size: 11px;
                color: #64748b;
                margin-top: 2px;
            }
            
            .tree-details { 
                list-style: none;
                padding: 0;
                margin: 0;
            }
            
            .tree-details li { 
                padding: 12px 18px;
                border-bottom: 1px solid #f0f2f5;
            }
            
            .tree-details li:last-child {
                border-bottom: none;
            }
            
            .material-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 20px;
                flex-wrap: wrap;
            }
            
            .material-info {
                flex: 1;
                display: flex;
                flex-direction: column;
                gap: 6px;
                min-width: 240px;
            }
            
            .material-name {
                font-size: 13px;
                font-weight: 600;
                color: #1a202c;
                display: flex;
                align-items: center;
                gap: 8px;
                flex-wrap: wrap;
            }
            
            .etapa-badge {
                display: inline-flex;
                align-items: center;
                padding: 3px 8px;
                background: #FF6B15;
                color: #ffffff;
                font-size: 10px;
                font-weight: 600;
                border-radius: 4px;
                letter-spacing: 0.3px;
                text-transform: uppercase;
                white-space: nowrap;
            }
            
            .service-badge {
                display: inline-flex;
                align-items: center;
                padding: 3px 8px;
                background: #3b82f6;
                color: #ffffff;
                font-size: 10px;
                font-weight: 600;
                border-radius: 4px;
                letter-spacing: 0.3px;
                text-transform: uppercase;
                white-space: nowrap;
            }
            
            .material-details {
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
                font-size: 12px;
            }
            
            .detail-item {
                display: inline-flex;
                align-items: center;
                gap: 5px;
                color: #64748b;
            }
            
            .detail-label {
                font-weight: 600;
                color: #475569;
            }
            
            .detail-value {
                color: #1a202c;
            }
            
            .material-total {
                display: flex;
                flex-direction: column;
                align-items: flex-end;
                gap: 2px;
                min-width: 100px;
            }
            
            .total-label {
                font-size: 10px;
                text-transform: uppercase;
                color: #64748b;
                font-weight: 600;
                letter-spacing: 0.4px;
            }
            
            .total-value {
                font-size: 16px;
                font-weight: 700;
                color: #1a202c;
            }
            
            .tree-details .muted {
                padding: 16px 18px;
                color: #94a3b8;
                font-style: italic;
                text-align: center;
                font-size: 12px;
            }
            
            @media (max-width: 1024px) {
                .costeo-tree { padding: 0; }
                .costeo-tree .tree-product { margin-left: 0; margin-right: 0; }
                .tree-header { padding: 12px 16px; }
                .tree-header-left { min-width: 240px; gap: 12px; }
                .tree-product-image { width: 55px; height: 55px; }
                .tree-title { font-size: 14px; }
                .tree-subtitle { font-size: 11px; gap: 10px; }
                .total-amount { font-size: 18px; }
                .tree-cost-breakdown {
                    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
                    gap: 8px;
                    padding: 12px 16px;
                }
                .tree-fields-section { 
                    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                    gap: 12px;
                    padding: 14px 16px;
                }
                .tree-details li { padding: 11px 16px; }
                .material-row { gap: 14px; }
            }
            
            @media (max-width: 768px) {
                .costeo-tree { padding: 0; }
                .costeo-tree .tree-product { margin-left: 0; margin-right: 0; }
                .tree-product { border-radius: 6px; margin-bottom: 14px; }
                .tree-header { flex-direction: column; align-items: flex-start; padding: 12px 14px; }
                .tree-header-left { width: 100%; min-width: unset; }
                .tree-product-image { width: 50px; height: 50px; }
                .tree-title { font-size: 13px; }
                .tree-subtitle { flex-direction: column; align-items: flex-start; gap: 4px; font-size: 11px; }
                .tree-actions { width: 100%; flex-direction: column; align-items: flex-start; gap: 10px; }
                .tree-total-badge { width: 100%; flex-direction: row; justify-content: space-between; align-items: center; }
                .tree-total-badge .label-text { font-size: 10px; }
                .total-amount { font-size: 16px; }
                .edit-detail { width: 100%; text-align: center; padding: 8px 14px; }
                .tree-cost-breakdown {
                    grid-template-columns: 1fr;
                    gap: 8px;
                    padding: 12px 14px;
                }
                .cost-item {
                    padding: 7px 10px;
                }
                .tree-fields-section {
                    grid-template-columns: 1fr;
                    gap: 12px;
                    padding: 14px;
                }
                .tree-details li { padding: 10px 14px; }
                .material-row { flex-direction: column; gap: 10px; align-items: flex-start; }
                .material-info { min-width: unset; width: 100%; }
                .material-name { font-size: 12px; }
                .material-details { gap: 10px; font-size: 11px; }
                .detail-item { width: 100%; }
                .material-total { width: 100%; flex-direction: row; justify-content: space-between; align-items: center; padding-top: 8px; border-top: 1px solid #f0f2f5; }
                .total-value { font-size: 15px; }
            }
            
            @media (max-width: 480px) {
                .tree-product-image { width: 45px; height: 45px; }
                .tree-title { font-size: 12px; }
                .tree-subtitle { font-size: 10px; }
                .etapa-badge, .service-badge { font-size: 9px; padding: 2px 6px; }
                .material-details { font-size: 10px; }
                .total-amount { font-size: 15px; }
                .total-value { font-size: 14px; }
                .tree-field-input { padding: 7px 9px; font-size: 12px; }
            }
        </style>
    `;
    $('head').append(css);
}

