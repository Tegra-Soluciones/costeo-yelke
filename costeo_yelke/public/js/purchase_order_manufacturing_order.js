// =============================================================================
// ORDEN DE MANUFACTURA EN PURCHASE ORDER (SUBCONTRATACION)
// =============================================================================

const OM_CABALLERO_FIELDS = ["t28", "t30", "t32", "t34", "t36", "t40", "t42", "t44"];
const OM_DAMA_FIELDS = ["t5", "t7", "t9", "t11", "t13", "t15", "t17"];

const OM_HTML_FIELD = "om_tablas_html";
const OM_BACKEND_TABLE_FIELD = "om_tablas_flexibles";
const OM_META_ROW_NAME = "__meta__";
const OM_META_COLUMN_NAME = "__layout__";
const OM_ROW_ID_PREFIX = "r";
const OM_COLUMN_ID_PREFIX = "c";
const OM_FIXED_LINE_TEXT = "Cantidad";

const OM_SECTION_FIELDS = [
    "om_tab_orden_manufactura",
    "om_section_info_general",
    "om_fecha_requerida",
    "om_column_info_general",
    "om_bordado",
    "om_estampado",
    "om_sublimado",
    "om_reflejante",
    "om_aberturas",
    "om_section_detallada",
    "om_modelo",
    "om_tela",
    "om_color_principal",
    "om_column_detallada",
    "om_combinacion",
    "om_color",
    "om_forro",
    "om_ubicacion",
    "om_section_tallas_caballero",
    "om_prendas_caballero_total",
    "om_tallas_caballero",
    "om_section_tallas_dama",
    "om_prendas_dama_total",
    "om_tallas_dama",
    "om_section_procesos",
    "om_procesos",
    "om_section_observaciones",
    "om_observaciones",
    "om_section_tablas_flexibles",
    "om_tablas_html",
    "om_tablas_flexibles",
    "om_section_archivos",
    "om_archivos"
];

function is_subcontract_po(frm) {
    return parseInt(frm.doc.is_subcontracted || 0, 10) === 1;
}

function toggle_om_sections(frm) {
    const visible = is_subcontract_po(frm);
    OM_SECTION_FIELDS.forEach(fieldname => {
        frm.toggle_display(fieldname, visible);
    });

    // Backend table remains hidden. HTML builder is the editable UI.
    frm.toggle_display(OM_BACKEND_TABLE_FIELD, false);
}

function sync_om_required_date(frm) {
    if (!is_subcontract_po(frm)) return;

    const required_date = frm.doc.schedule_date || frm.doc.transaction_date || frappe.datetime.get_today();
    if (!required_date) return;

    if (frm.doc.om_fecha_requerida !== required_date) {
        frm.set_value("om_fecha_requerida", required_date);
    }
}

function sum_row_values(row, fields) {
    return fields.reduce((sum, fieldname) => sum + flt(row[fieldname]), 0);
}

function compute_caballero_totals(frm) {
    let grand_total = 0;

    (frm.doc.om_tallas_caballero || []).forEach(row => {
        row.total = sum_row_values(row, OM_CABALLERO_FIELDS);
        grand_total += flt(row.total);
    });

    frm.refresh_field("om_tallas_caballero");
    if (flt(frm.doc.om_prendas_caballero_total) !== grand_total) {
        frm.set_value("om_prendas_caballero_total", grand_total);
    }
}

function compute_dama_totals(frm) {
    let grand_total = 0;

    (frm.doc.om_tallas_dama || []).forEach(row => {
        row.total = sum_row_values(row, OM_DAMA_FIELDS);
        grand_total += flt(row.total);
    });

    frm.refresh_field("om_tallas_dama");
    if (flt(frm.doc.om_prendas_dama_total) !== grand_total) {
        frm.set_value("om_prendas_dama_total", grand_total);
    }
}

function renumber_process_rows(frm) {
    (frm.doc.om_procesos || []).forEach((row, index) => {
        row.proceso = `Proceso ${index + 1}`;
    });

    frm.refresh_field("om_procesos");
}

function lock_fixed_size_grid(frm, fieldname) {
    const field = frm.fields_dict[fieldname];
    if (!field || !field.grid) return;

    field.grid.df.cannot_add_rows = 1;
    field.grid.df.cannot_delete_rows = 1;
    field.grid.cannot_add_rows = true;
    field.grid.cannot_delete_rows = true;
    field.grid.refresh();
}

function ensure_single_size_row(frm, fieldname) {
    if (!is_subcontract_po(frm)) return;

    lock_fixed_size_grid(frm, fieldname);

    if (!Array.isArray(frm.doc[fieldname])) {
        frm.doc[fieldname] = [];
    }

    let changed = false;
    let rows = frm.doc[fieldname] || [];

    if (!rows.length) {
        const row = frm.add_child(fieldname);
        row.linea = OM_FIXED_LINE_TEXT;
        rows = frm.doc[fieldname] || [];
        changed = true;
    }

    while (rows.length > 1) {
        const last_row = rows[rows.length - 1];
        if (last_row && last_row.doctype && last_row.name) {
            frappe.model.clear_doc(last_row.doctype, last_row.name);
        } else {
            rows.pop();
        }
        rows = frm.doc[fieldname] || [];
        changed = true;
    }

    const first_row = rows[0];
    if (first_row) {
        first_row.idx = 1;
        if (first_row.linea !== OM_FIXED_LINE_TEXT) {
            first_row.linea = OM_FIXED_LINE_TEXT;
            changed = true;
        }
    }

    if (changed) {
        frm.refresh_field(fieldname);
        frm.dirty();
    }
}

function enforce_fixed_size_tables(frm) {
    ensure_single_size_row(frm, "om_tallas_caballero");
    ensure_single_size_row(frm, "om_tallas_dama");
}

function om_escape_html(value) {
    return $("<div>").text(value || "").html();
}

function om_to_int(value, fallback = 0) {
    const n = parseInt(value, 10);
    return Number.isFinite(n) ? n : fallback;
}

function om_parse_json(value) {
    if (!value) return {};
    try {
        const parsed = JSON.parse(value);
        return parsed && typeof parsed === "object" ? parsed : {};
    } catch (e) {
        return {};
    }
}

function om_unique_non_empty(values) {
    const out = [];
    (values || []).forEach(value => {
        const clean = (value || "").toString().trim();
        if (clean && !out.includes(clean)) {
            out.push(clean);
        }
    });
    return out;
}

function om_next_available_label(prefix, existing_values) {
    const existing = (existing_values || []).map(v => (v || "").toString().trim()).filter(Boolean);
    let n = 1;
    while (existing.includes(`${prefix} ${n}`)) {
        n += 1;
    }
    return `${prefix} ${n}`;
}

function om_next_increment_id(prefix, existing_values) {
    let max = 0;
    const regex = new RegExp(`^${prefix}(\\d+)$`, "i");

    (existing_values || []).forEach(value => {
        const label = (value || "").toString().trim();
        const match = regex.exec(label);
        if (match) {
            max = Math.max(max, om_to_int(match[1], 0));
        }
    });

    return `${prefix}${max + 1}`;
}

function om_default_table(existing_tables) {
    const names = (existing_tables || []).map(t => t.name);
    const table_name = om_next_available_label("Tabla", names);
    const first_column = `${OM_COLUMN_ID_PREFIX}1`;
    const first_row = `${OM_ROW_ID_PREFIX}1`;

    return {
        name: table_name,
        unit: "",
        columns: [first_column],
        rows: [{
            id: first_row,
            cells: { [first_column]: "" }
        }]
    };
}

function build_om_tables_state_from_backend(frm) {
    const grouped = {};
    const table_order = [];

    (frm.doc[OM_BACKEND_TABLE_FIELD] || []).forEach(row => {
        const table_name = ((row.tabla || "").toString().trim()) || "Tabla sin nombre";

        if (!grouped[table_name]) {
            grouped[table_name] = {
                name: table_name,
                unit: (row.unidad || "").toString(),
                columns: [],
                rows: [],
                row_map: {},
                layout: null
            };
            table_order.push(table_name);
        }

        const bucket = grouped[table_name];
        if (!bucket.unit && row.unidad) {
            bucket.unit = (row.unidad || "").toString();
        }

        if ((row.fila || "") === OM_META_ROW_NAME && (row.columna || "") === OM_META_COLUMN_NAME) {
            bucket.layout = om_parse_json(row.valor);
            if (bucket.layout.unidad && !bucket.unit) {
                bucket.unit = bucket.layout.unidad;
            }
            return;
        }

        const row_id = ((row.fila || "").toString().trim());
        const column_id = ((row.columna || "").toString().trim());
        if (!row_id || !column_id) return;

        if (!bucket.row_map[row_id]) {
            bucket.row_map[row_id] = {
                id: row_id,
                cells: {}
            };
            bucket.rows.push(bucket.row_map[row_id]);
        }

        if (!bucket.columns.includes(column_id)) {
            bucket.columns.push(column_id);
        }

        bucket.row_map[row_id].cells[column_id] = (row.valor || "").toString();
    });

    const state = [];

    table_order.forEach((table_name, index) => {
        const bucket = grouped[table_name];
        const layout = bucket.layout || {};
        const layout_columns = om_unique_non_empty(layout.columnas);
        const layout_rows = om_unique_non_empty(layout.filas);

        const columns = layout_columns.length ? layout_columns : bucket.columns.slice();
        if (!columns.length) {
            columns.push(`${OM_COLUMN_ID_PREFIX}1`);
        }

        const ordered_row_ids = [];
        layout_rows.forEach(row_id => {
            if (!ordered_row_ids.includes(row_id)) ordered_row_ids.push(row_id);
        });
        (bucket.rows || []).forEach(row => {
            if (row.id && !ordered_row_ids.includes(row.id)) ordered_row_ids.push(row.id);
        });

        const rows = ordered_row_ids.map(row_id => bucket.row_map[row_id] || { id: row_id, cells: {} });
        if (!rows.length) {
            rows.push({ id: `${OM_ROW_ID_PREFIX}1`, cells: {} });
        }

        rows.forEach((row, index) => {
            row.id = ((row.id || "").toString().trim()) || `${OM_ROW_ID_PREFIX}${index + 1}`;
            row.cells = row.cells || {};
            columns.forEach(column => {
                if (row.cells[column] === undefined) {
                    row.cells[column] = "";
                }
            });
        });

        state.push({
            name: bucket.name || `Tabla ${index + 1}`,
            unit: bucket.unit || "",
            columns,
            rows
        });
    });

    return state;
}

function init_om_tables_state(frm) {
    frm.__om_tables_state = build_om_tables_state_from_backend(frm);
}

function sync_om_tables_state_to_backend(frm, refresh_backend_field = false) {
    const state = frm.__om_tables_state || [];
    frm.clear_table(OM_BACKEND_TABLE_FIELD);

    state.forEach((table, table_index) => {
        const table_name = ((table.name || `Tabla ${table_index + 1}`).toString().trim()) || `Tabla ${table_index + 1}`;
        const unit = (table.unit || "").toString();
        let columns = om_unique_non_empty(table.columns);
        if (!columns.length) {
            columns = [`${OM_COLUMN_ID_PREFIX}1`];
        }

        let rows = (table.rows || [])
            .map((row, row_index) => ({
                id: ((row.id || row.name || "").toString().trim()) || `${OM_ROW_ID_PREFIX}${row_index + 1}`,
                cells: row.cells || {}
            }))
            .filter(row => !!row.id);

        if (!rows.length) {
            const empty_cells = {};
            columns.forEach(column_id => {
                empty_cells[column_id] = "";
            });
            rows = [{ id: `${OM_ROW_ID_PREFIX}1`, cells: empty_cells }];
        }

        const meta_row = frm.add_child(OM_BACKEND_TABLE_FIELD);
        meta_row.tabla = table_name;
        meta_row.unidad = unit;
        meta_row.fila = OM_META_ROW_NAME;
        meta_row.columna = OM_META_COLUMN_NAME;
        meta_row.valor = JSON.stringify({
            columnas: columns,
            filas: rows.map(row => row.id),
            unidad: unit
        });

        rows.forEach(row => {
            columns.forEach(column => {
                const value = row.cells[column] !== undefined && row.cells[column] !== null
                    ? String(row.cells[column])
                    : "";

                if (!value) return;

                const child = frm.add_child(OM_BACKEND_TABLE_FIELD);
                child.tabla = table_name;
                child.unidad = unit;
                child.fila = row.id;
                child.columna = column;
                child.valor = value;
            });
        });
    });

    if (refresh_backend_field) {
        frm.refresh_field(OM_BACKEND_TABLE_FIELD);
    }

    frm.dirty();
}

function queue_om_backend_sync(frm) {
    if (frm.__om_backend_sync_timer) {
        clearTimeout(frm.__om_backend_sync_timer);
    }

    frm.__om_backend_sync_timer = setTimeout(() => {
        sync_om_tables_state_to_backend(frm, false);
        frm.__om_backend_sync_timer = null;
    }, 250);
}

function flush_om_backend_sync(frm) {
    if (frm.__om_backend_sync_timer) {
        clearTimeout(frm.__om_backend_sync_timer);
        frm.__om_backend_sync_timer = null;
    }
    sync_om_tables_state_to_backend(frm, false);
}

function ensure_om_builder_css() {
    if ($("#om-table-builder-style").length) return;

    const css = `
        <style id="om-table-builder-style">
            .om-builder { border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px; background: #fafafa; }
            .om-builder-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
            .om-table-card { border: 1px solid #d1d5db; border-radius: 8px; background: #fff; margin-bottom: 12px; }
            .om-table-card-header { padding: 10px 12px; border-bottom: 1px solid #e5e7eb; display: flex; justify-content: space-between; gap: 10px; align-items: center; flex-wrap: wrap; }
            .om-table-card-title { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
            .om-table-card-title input { min-width: 180px; }
            .om-table-actions { display: flex; gap: 6px; flex-wrap: wrap; }
            .om-grid-wrap { overflow-x: auto; padding: 10px 12px 12px; }
            .om-grid { min-width: 700px; border-collapse: separate; border-spacing: 0; width: 100%; }
            .om-grid th, .om-grid td { border: 1px solid #e5e7eb; padding: 6px; vertical-align: middle; background: #fff; }
            .om-grid thead th { background: #f8fafc; }
            .om-grid .om-cell-input { min-width: 110px; }
            .om-col-head { display: flex; gap: 6px; align-items: center; justify-content: space-between; }
            .om-col-label { font-size: 12px; color: #4b5563; }
            .om-empty-hint { color: #6b7280; font-size: 12px; }
            .om-delete-btn { white-space: nowrap; }
        </style>
    `;

    $("head").append(css);
}

function render_om_tables_builder(frm) {
    const html_field = frm.fields_dict[OM_HTML_FIELD];
    if (!html_field || !html_field.$wrapper) return;

    const $wrapper = html_field.$wrapper;
    ensure_om_builder_css();

    if (!is_subcontract_po(frm)) {
        $wrapper.html(`<div class="text-muted small" style="padding:8px 0;">Disponible solo cuando la OC es Subcontratada.</div>`);
        return;
    }

    const state = frm.__om_tables_state || [];

    let html = "";
    html += `<div class="om-builder">`;
    html += `<div class="om-builder-toolbar">`;
    html += `<div class="small text-muted">Editor de tablas flexibles (persistencia en tabla ERPNext)</div>`;
    html += `<button class="btn btn-sm btn-primary om-add-table">+ Tabla</button>`;
    html += `</div>`;

    if (!state.length) {
        html += `<div class="om-empty-hint">No hay tablas. Usa <b>+ Tabla</b> para agregar la primera.</div>`;
    }

    state.forEach((table, table_index) => {
        const table_name = om_escape_html(table.name || `Tabla ${table_index + 1}`);
        const table_unit = om_escape_html(table.unit || "");
        const columns = table.columns || [];
        const rows = table.rows || [];

        html += `<div class="om-table-card" data-table-index="${table_index}">`;
        html += `<div class="om-table-card-header">`;
        html += `<div class="om-table-card-title">`;
        html += `<input class="form-control input-xs om-table-name" data-table-index="${table_index}" value="${table_name}" placeholder="Nombre de tabla">`;
        html += `<input class="form-control input-xs om-table-unit" data-table-index="${table_index}" value="${table_unit}" placeholder="Unidad (ej. pulgadas)">`;
        html += `</div>`;
        html += `<div class="om-table-actions">`;
        html += `<button class="btn btn-xs btn-default om-add-column" data-table-index="${table_index}">+ Columna</button>`;
        html += `<button class="btn btn-xs btn-default om-add-row" data-table-index="${table_index}">+ Fila</button>`;
        html += `<button class="btn btn-xs btn-danger om-remove-table om-delete-btn" data-table-index="${table_index}">Eliminar tabla</button>`;
        html += `</div>`;
        html += `</div>`;

        html += `<div class="om-grid-wrap">`;
        html += `<table class="om-grid">`;
        html += `<thead><tr>`;
        columns.forEach((column_id, column_index) => {
            html += `<th>`;
            html += `<div class="om-col-head">`;
            html += `<span class="om-col-label">${column_index + 1}</span>`;
            html += `<button class="btn btn-xs btn-default om-remove-column" data-table-index="${table_index}" data-col-index="${column_index}" title="Eliminar columna">x</button>`;
            html += `</div>`;
            html += `</th>`;
        });
        html += `<th></th>`;
        html += `</tr></thead>`;

        html += `<tbody>`;
        rows.forEach((row, row_index) => {
            html += `<tr>`;
            columns.forEach((column_id, column_index) => {
                const cell_value = row.cells && row.cells[column_id] !== undefined ? row.cells[column_id] : "";
                html += `<td class="om-cell-input">`;
                html += `<input class="form-control input-xs om-cell-value" data-table-index="${table_index}" data-row-index="${row_index}" data-col-index="${column_index}" value="${om_escape_html(cell_value)}">`;
                html += `</td>`;
            });

            html += `<td>`;
            html += `<button class="btn btn-xs btn-default om-remove-row" data-table-index="${table_index}" data-row-index="${row_index}" title="Eliminar fila">x</button>`;
            html += `</td>`;
            html += `</tr>`;
        });
        html += `</tbody>`;
        html += `</table>`;
        html += `</div>`;

        html += `</div>`;
    });

    html += `</div>`;
    $wrapper.html(html);

    bind_om_builder_events(frm);
}

function bind_om_builder_events(frm) {
    const html_field = frm.fields_dict[OM_HTML_FIELD];
    if (!html_field || !html_field.$wrapper) return;

    const $wrapper = html_field.$wrapper;
    $wrapper.off(".om_builder");

    $wrapper.on("click.om_builder", ".om-add-table", function (e) {
        e.preventDefault();

        const state = frm.__om_tables_state || [];
        state.push(om_default_table(state));
        frm.__om_tables_state = state;

        sync_om_tables_state_to_backend(frm, false);
        render_om_tables_builder(frm);
    });

    $wrapper.on("click.om_builder", ".om-remove-table", function (e) {
        e.preventDefault();

        const table_index = om_to_int($(this).data("tableIndex"), -1);
        const state = frm.__om_tables_state || [];
        if (table_index < 0 || table_index >= state.length) return;

        state.splice(table_index, 1);
        frm.__om_tables_state = state;

        sync_om_tables_state_to_backend(frm, false);
        render_om_tables_builder(frm);
    });

    $wrapper.on("input.om_builder", ".om-table-name", function () {
        const table_index = om_to_int($(this).data("tableIndex"), -1);
        const state = frm.__om_tables_state || [];
        const table = state[table_index];
        if (!table) return;

        table.name = ($(this).val() || "").toString();
        queue_om_backend_sync(frm);
    });

    $wrapper.on("input.om_builder", ".om-table-unit", function () {
        const table_index = om_to_int($(this).data("tableIndex"), -1);
        const state = frm.__om_tables_state || [];
        const table = state[table_index];
        if (!table) return;

        table.unit = ($(this).val() || "").toString();
        queue_om_backend_sync(frm);
    });

    $wrapper.on("click.om_builder", ".om-add-column", function (e) {
        e.preventDefault();

        const table_index = om_to_int($(this).data("tableIndex"), -1);
        const state = frm.__om_tables_state || [];
        const table = state[table_index];
        if (!table) return;

        const column_id = om_next_increment_id(OM_COLUMN_ID_PREFIX, table.columns || []);
        table.columns = table.columns || [];
        table.columns.push(column_id);

        (table.rows || []).forEach(row => {
            row.cells = row.cells || {};
            row.cells[column_id] = row.cells[column_id] || "";
        });

        sync_om_tables_state_to_backend(frm, false);
        render_om_tables_builder(frm);
    });

    $wrapper.on("click.om_builder", ".om-remove-column", function (e) {
        e.preventDefault();

        const table_index = om_to_int($(this).data("tableIndex"), -1);
        const column_index = om_to_int($(this).data("colIndex"), -1);
        const state = frm.__om_tables_state || [];
        const table = state[table_index];
        if (!table || column_index < 0 || column_index >= (table.columns || []).length) return;

        if ((table.columns || []).length <= 1) {
            frappe.show_alert({ message: "La tabla debe conservar al menos una columna", indicator: "orange" });
            return;
        }

        const removed_column = table.columns[column_index];
        table.columns.splice(column_index, 1);

        (table.rows || []).forEach(row => {
            if (row.cells && Object.prototype.hasOwnProperty.call(row.cells, removed_column)) {
                delete row.cells[removed_column];
            }
        });

        sync_om_tables_state_to_backend(frm, false);
        render_om_tables_builder(frm);
    });

    $wrapper.on("click.om_builder", ".om-add-row", function (e) {
        e.preventDefault();

        const table_index = om_to_int($(this).data("tableIndex"), -1);
        const state = frm.__om_tables_state || [];
        const table = state[table_index];
        if (!table) return;

        table.rows = table.rows || [];
        table.columns = table.columns || [`${OM_COLUMN_ID_PREFIX}1`];

        const row_id = om_next_increment_id(
            OM_ROW_ID_PREFIX,
            table.rows.map(row => row.id || row.name)
        );

        const row = { id: row_id, cells: {} };
        table.columns.forEach(column_id => {
            row.cells[column_id] = "";
        });

        table.rows.push(row);

        sync_om_tables_state_to_backend(frm, false);
        render_om_tables_builder(frm);
    });

    $wrapper.on("click.om_builder", ".om-remove-row", function (e) {
        e.preventDefault();

        const table_index = om_to_int($(this).data("tableIndex"), -1);
        const row_index = om_to_int($(this).data("rowIndex"), -1);
        const state = frm.__om_tables_state || [];
        const table = state[table_index];
        if (!table || row_index < 0 || row_index >= (table.rows || []).length) return;

        if ((table.rows || []).length <= 1) {
            frappe.show_alert({ message: "La tabla debe conservar al menos una fila", indicator: "orange" });
            return;
        }

        table.rows.splice(row_index, 1);

        sync_om_tables_state_to_backend(frm, false);
        render_om_tables_builder(frm);
    });

    $wrapper.on("input.om_builder", ".om-cell-value", function () {
        const table_index = om_to_int($(this).data("tableIndex"), -1);
        const row_index = om_to_int($(this).data("rowIndex"), -1);
        const column_index = om_to_int($(this).data("colIndex"), -1);

        const state = frm.__om_tables_state || [];
        const table = state[table_index];
        if (!table) return;

        const row = (table.rows || [])[row_index];
        const column = (table.columns || [])[column_index];
        if (!row || !column) return;

        row.cells = row.cells || {};
        row.cells[column] = ($(this).val() || "").toString();
        queue_om_backend_sync(frm);
    });
}

frappe.ui.form.on("Purchase Order", {
    refresh(frm) {
        toggle_om_sections(frm);
        sync_om_required_date(frm);
        enforce_fixed_size_tables(frm);
        compute_caballero_totals(frm);
        compute_dama_totals(frm);
        renumber_process_rows(frm);
        init_om_tables_state(frm);
        render_om_tables_builder(frm);
    },

    is_subcontracted(frm) {
        toggle_om_sections(frm);
        sync_om_required_date(frm);
        enforce_fixed_size_tables(frm);
        compute_caballero_totals(frm);
        compute_dama_totals(frm);
        init_om_tables_state(frm);
        render_om_tables_builder(frm);
    },

    transaction_date(frm) {
        sync_om_required_date(frm);
    },

    schedule_date(frm) {
        sync_om_required_date(frm);
    },

    om_tallas_caballero_add(frm) {
        enforce_fixed_size_tables(frm);
        compute_caballero_totals(frm);
    },

    om_tallas_caballero_remove(frm) {
        enforce_fixed_size_tables(frm);
        compute_caballero_totals(frm);
    },

    om_tallas_dama_add(frm) {
        enforce_fixed_size_tables(frm);
        compute_dama_totals(frm);
    },

    om_tallas_dama_remove(frm) {
        enforce_fixed_size_tables(frm);
        compute_dama_totals(frm);
    },

    om_procesos_add(frm) {
        renumber_process_rows(frm);
    },

    om_procesos_remove(frm) {
        renumber_process_rows(frm);
    },

    validate(frm) {
        sync_om_required_date(frm);
        enforce_fixed_size_tables(frm);
        compute_caballero_totals(frm);
        compute_dama_totals(frm);
        renumber_process_rows(frm);
        flush_om_backend_sync(frm);
    }
});

frappe.ui.form.on("Orden Manufactura Talla Caballero", {
    linea(frm, cdt, cdn) {
        const row = locals[cdt] && locals[cdt][cdn];
        if (row && row.linea !== OM_FIXED_LINE_TEXT) {
            frappe.model.set_value(cdt, cdn, "linea", OM_FIXED_LINE_TEXT);
        }
        compute_caballero_totals(frm);
    },
    t28(frm) { compute_caballero_totals(frm); },
    t30(frm) { compute_caballero_totals(frm); },
    t32(frm) { compute_caballero_totals(frm); },
    t34(frm) { compute_caballero_totals(frm); },
    t36(frm) { compute_caballero_totals(frm); },
    t40(frm) { compute_caballero_totals(frm); },
    t42(frm) { compute_caballero_totals(frm); },
    t44(frm) { compute_caballero_totals(frm); }
});

frappe.ui.form.on("Orden Manufactura Talla Dama", {
    linea(frm, cdt, cdn) {
        const row = locals[cdt] && locals[cdt][cdn];
        if (row && row.linea !== OM_FIXED_LINE_TEXT) {
            frappe.model.set_value(cdt, cdn, "linea", OM_FIXED_LINE_TEXT);
        }
        compute_dama_totals(frm);
    },
    t5(frm) { compute_dama_totals(frm); },
    t7(frm) { compute_dama_totals(frm); },
    t9(frm) { compute_dama_totals(frm); },
    t11(frm) { compute_dama_totals(frm); },
    t13(frm) { compute_dama_totals(frm); },
    t15(frm) { compute_dama_totals(frm); },
    t17(frm) { compute_dama_totals(frm); }
});

frappe.ui.form.on("Orden Manufactura Proceso", {
    form_render(frm) {
        renumber_process_rows(frm);
    }
});
