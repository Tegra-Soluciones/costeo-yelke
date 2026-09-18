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

# ── Roles genéricos de flujo de documentos ───────────────────────────────────
# No son de un proceso en particular (a diferencia de ROLES_PROCESO) -- sirven
# para cualquier documento del flujo bajo cualquiera de los dos esquemas que usa
# Yelke:
#   Simple: Enviar Documentos -> Aprobador de Documentos           (Costeo)
#   Doble:  Enviar Documentos -> Revisor de Documentos -> Aprobador de Documentos
#           (Orden de Compra -- materia prima y subcontratada, ver costeo_api.py
#           validar_documento / marcar_revisado_documento)
# Todos los demás documentos importantes (Cotización, Orden de Venta, Factura,
# Plan de Producción, Recibos...) siguen sin gating por rol -- "validación normal".
ROLES_FLUJO_DOCUMENTOS = {
    "Enviar Documentos Yelke":      "Guarda y envía un documento a revisión o validación.",
    "Revisor de Documentos Yelke":  "Da la verificación intermedia de un documento antes de la aprobación final (esquema Doble).",
    "Aprobador de Documentos Yelke": "Da la aprobación/validación final de un documento.",
}

ROLES_YELKE = {**ROLES_PROCESO, **ROLES_APROBACION, **ROLES_FLUJO_DOCUMENTOS}

# Rol que hoy usa item_api._es_ceo() para aprobar precios. Se mantiene por
# compatibilidad; el motor nuevo acepta tanto este como "Director Yelke".
ROL_CEO_LEGACY = "CEO"


def puede_aprobar_documentos(user=None):
    """True si `user` (o el usuario actual) puede dar la aprobación/validación
    final de un documento del flujo -- rol 'Aprobador de Documentos Yelke', o
    System Manager como respaldo de administrador (para no bloquear a nadie
    mientras el rol todavía no está asignado a las personas correctas)."""
    import frappe

    roles = frappe.get_roles(user)
    return "Aprobador de Documentos Yelke" in roles or "System Manager" in roles


def puede_revisar_documentos(user=None):
    """True si `user` (o el usuario actual) puede dar la verificación intermedia
    del esquema Doble -- rol 'Revisor de Documentos Yelke', o quien ya pueda dar
    la aprobación final (un Aprobador siempre puede hacer también el paso previo),
    o System Manager como respaldo de administrador."""
    import frappe

    roles = frappe.get_roles(user)
    return bool({"Revisor de Documentos Yelke", "Aprobador de Documentos Yelke", "System Manager"} & set(roles))
