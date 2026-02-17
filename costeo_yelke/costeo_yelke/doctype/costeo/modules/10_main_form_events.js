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
