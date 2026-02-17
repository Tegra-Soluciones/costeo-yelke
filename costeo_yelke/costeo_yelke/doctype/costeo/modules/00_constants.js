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

