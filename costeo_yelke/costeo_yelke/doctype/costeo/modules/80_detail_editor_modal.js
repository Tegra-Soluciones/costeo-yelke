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

