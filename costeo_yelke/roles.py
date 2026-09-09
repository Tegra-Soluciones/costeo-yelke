"""Catálogo de roles de la app -- una entrada por proceso del flujo del Costeo, más
los roles transversales de aprobación. Todos llevan el sufijo " Yelke" para que se
distingan de los roles nativos de Frappe/ERPNext al asignar permisos.

Este módulo es la ÚNICA fuente de verdad de los nombres: el patch que los crea
(patches/v0_2_21) y cualquier chequeo de permisos en la app deben importar de aquí,
nunca escribir el string a mano.
"""

# ── Roles por proceso (etapa del flujo) ──────────────────────────────────────
# Quien tiene el rol puede CAPTURAR/EDITAR los documentos de esa etapa. Validarlos
# depende del nivel de aprobación configurado (ver ROLES_APROBACION y el motor de
# flujos de aprobación).
ROLES_PROCESO = {
    "Costeador Yelke":                "Arma el costeo: BOM, materiales, servicios, precios estimados y márgenes.",
    "Cotizador Yelke":               "Genera la cotización al cliente a partir del costeo.",
    "Vendedor Yelke":                "Convierte la cotización en Orden de Venta y gestiona la relación comercial.",
    "Ingeniería de Producto Yelke":  "Da de alta los artículos terminados y sus BOM de producción.",
    "Planeador de Producción Yelke": "Arma el plan de producción: flujo de operaciones, etapas y lotes.",
    "Comprador Yelke":               "Genera solicitudes de material, órdenes de compra y cotizaciones a proveedor.",
    "Almacenista Yelke":             "Recibe la materia prima (recibos de compra) y captura fletes de entrada.",
    "Coordinador de Maquila Yelke":  "Encarga la maquila al taller, envía el material y recibe el trabajo terminado.",
    "Embarques Yelke":               "Prepara y entrega las remisiones al cliente.",
    "Facturador Yelke":              "Emite las facturas de venta (y su CFDI).",
    "Analista de Costos Yelke":      "Consulta el reporte final de rentabilidad (solo lectura).",
}

# ── Roles transversales de aprobación ────────────────────────────────────────
ROLES_APROBACION = {
    "Aprobador de Precios Yelke": "Aprueba los precios acordados con el cliente (vigencia de Item Price).",
    "Doble Verificador Yelke":   "Da la segunda firma en los documentos marcados como sensibles antes de que el Director los apruebe.",
    "Director Yelke":            "Aprobación final de todos los documentos importantes del flujo. Único que delega su autoridad.",
    "Supervisor Yelke":          "Configura los niveles de validación, administra las delegaciones y actúa de respaldo del Director.",
}

ROLES_YELKE = {**ROLES_PROCESO, **ROLES_APROBACION}

# Rol que hoy usa item_api._es_ceo() para aprobar precios. Se mantiene por
# compatibilidad; el motor nuevo acepta tanto este como "Director Yelke".
ROL_CEO_LEGACY = "CEO"
