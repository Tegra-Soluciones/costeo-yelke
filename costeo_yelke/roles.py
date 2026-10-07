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

# ── Roles por VISTA de Producción ────────────────────────────────────────────
# El paso "Producción" del costeo es una app completa (ver docs/plan-ui-produccion.md):
# un menú con un puñado de vistas, cada una el trabajo de una persona distinta. Hay un
# rol por vista; quien necesita dos vistas recibe los dos roles.
#
# A diferencia de ROLES_PROCESO (que hoy es documentación y no controla nada), estos
# SÍ se revisan: el menú solo muestra lo permitido y los endpoints que escriben lo
# exigen (ver requiere_vista).
VISTAS_PRODUCCION = {
    "tablero":     "Producción Tablero Yelke",
    "preparacion": "Producción Preparación Yelke",
    "om":          "Producción Orden de Manufactura Yelke",
    "materia":     "Producción Materia Prima Yelke",
    "flujo":       "Producción Flujo Yelke",
    "talleres":    "Producción Talleres Yelke",
    "envios":      "Producción Envíos Yelke",
    "facturas":    "Producción Facturas Yelke",
    "entrega":     "Producción Entrega Yelke",
}

# Nombre que ve el usuario en los mensajes de "no tienes acceso a ...".
ETIQUETAS_VISTA = {
    "tablero":     "Tablero",
    "preparacion": "Preparación",
    "om":          "Orden de manufactura",
    "materia":     "Materia prima",
    "flujo":       "Flujo",
    "talleres":    "Talleres",
    "envios":      "Envíos",
    "facturas":    "Facturas",
    "entrega":     "Entrega",
}

ROLES_VISTA_PRODUCCION = {
    VISTAS_PRODUCCION["tablero"]:     "Ve el tablero de producción de la orden de venta (solo lectura).",
    VISTAS_PRODUCCION["preparacion"]: "Prepara producción: plan, solicitud de material, lotes de entrega, órdenes a talleres y apertura de lotes.",
    VISTAS_PRODUCCION["om"]:          "Captura la orden de manufactura general por producto.",
    VISTAS_PRODUCCION["materia"]:     "Compra la materia prima de cada lote: cotizaciones, orden de compra y recibo.",
    VISTAS_PRODUCCION["flujo"]:       "Ve la matriz del lote y crea los encargos a talleres.",
    VISTAS_PRODUCCION["talleres"]:    "Lleva cada taller: encargos, envío de material y recibo del trabajo.",
    VISTAS_PRODUCCION["envios"]:      "Almacén: recibe material, envía a talleres, recibe de talleres y registra devoluciones.",
    VISTAS_PRODUCCION["facturas"]:    "Captura y valida las facturas de compra (material y maquila).",
    VISTAS_PRODUCCION["entrega"]:     "Crea la remisión de cada lote terminado.",
}

# Quien ve y hace TODO en Producción, sin necesidad de los roles por vista.
PASE_LIBRE_PRODUCCION = ("System Manager", "Director Yelke", "Supervisor Yelke")

ROLES_YELKE = {**ROLES_PROCESO, **ROLES_APROBACION, **ROLES_FLUJO_DOCUMENTOS,
               **ROLES_VISTA_PRODUCCION}

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


# ── Permisos por vista de Producción ─────────────────────────────────────────
def vistas_produccion(user=None):
    """Claves de vista de Producción que `user` (o el usuario actual) puede abrir.
    Con pase libre (ver PASE_LIBRE_PRODUCCION), todas."""
    import frappe

    roles = set(frappe.get_roles(user))
    if roles & set(PASE_LIBRE_PRODUCCION):
        return list(VISTAS_PRODUCCION)
    return [clave for clave, rol in VISTAS_PRODUCCION.items() if rol in roles]


def puede_ver(clave, user=None):
    """True si `user` puede abrir esa vista de Producción."""
    return clave in vistas_produccion(user)


def requiere_vista(*claves, user=None):
    """Exige al menos UNA de las vistas; si no, lanza PermissionError en español.

    Se pone al inicio de cada endpoint que ESCRIBE (las lecturas no se restringen).
    Se suma a la doble validación por documento, no la reemplaza."""
    import frappe
    from frappe import _

    if not claves:
        return
    permitidas = set(vistas_produccion(user))
    if permitidas & set(claves):
        return
    roles = [VISTAS_PRODUCCION[c] for c in claves if c in VISTAS_PRODUCCION]
    if len(roles) == 1:
        frappe.throw(_("Necesitas el rol {0} para esto.").format(roles[0]),
                     frappe.PermissionError)
    frappe.throw(
        _("Necesitas alguno de estos roles para esto: {0}.").format(", ".join(roles)),
        frappe.PermissionError)
