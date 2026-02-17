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


