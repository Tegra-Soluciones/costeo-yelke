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
