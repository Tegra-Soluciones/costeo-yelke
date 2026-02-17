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
