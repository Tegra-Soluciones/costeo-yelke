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

