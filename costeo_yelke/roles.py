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

# ── Vistas: cada pantalla / etapa con su propio rol (docs/plan-accesos-ejecucion.md) ──
# Una entrada por vista, en dos niveles:
#   editar  -> "<Grupo> <Vista> Yelke"      (ve y captura)
#   ver     -> "Ver <Grupo> <Vista> Yelke"  (solo lectura)
# Editar incluye ver. Quien necesita varias vistas recibe varios roles; lo normal es
# asignarlos con un Role Profile por puesto (Compras, Almacén...).
#
# De aquí sale TODO: el menú, los pasos del costeo, las rutas, el modo solo lectura,
# los candados del servidor (requiere_vista) y los permisos de ERPNext por doctype.
#   paso    clave del paso del costeo (CosteoStepper.vue) donde vive la vista
#   rutas   nombres de ruta del SPA (router/index.js) que habilita
#   doctypes  qué puede hacer en el Escritorio de ERPNext: "editar" o "ver"
#
# Las 9 de Producción conservan su clave y el nombre de su rol de editar de siempre
# (las usan los candados y los perfiles de producción); solo ganan su rol de ver.
VISTAS = {
    # ── Comercial ──
    "costear":   {"etiqueta": "Costear", "grupo": "Comercial", "rol": "Comercial Costear Yelke",
                  "paso": "costear", "rutas": ["CosteoNuevo", "Plantillas"],
                  "doctypes": {"Costeo": "editar", "Item": "ver", "Supplier": "ver", "Customer": "editar"},
                  "descripcion": "Arma el costeo: productos, materiales, etapas, precios y márgenes."},
    "cotizar":   {"etiqueta": "Cotizar", "grupo": "Comercial", "rol": "Comercial Cotizar Yelke",
                  "paso": "cotizar", "rutas": ["CotizacionList", "CotizacionDetail"],
                  "doctypes": {"Quotation": "editar", "Customer": "editar", "Address": "editar", "Contact": "editar"},
                  "descripcion": "Genera, envía y da seguimiento a la cotización."},
    "vender":    {"etiqueta": "Vender", "grupo": "Comercial", "rol": "Comercial Vender Yelke",
                  "paso": "vender", "rutas": ["SalesOrderList", "SalesOrderDetail", "SalesOrderNueva"],
                  "doctypes": {"Sales Order": "editar", "Customer": "editar", "Address": "editar", "Contact": "editar"},
                  "descripcion": "Convierte la cotización en orden de venta (OC del cliente, cancelación)."},
    "precios":   {"etiqueta": "Precios", "grupo": "Comercial", "rol": "Comercial Precios Yelke",
                  "rutas": ["Precios", "RecordatoriosList"],
                  "doctypes": {"Item Price": "editar", "Pricing Rule": "editar", "Price List": "ver"},
                  "descripcion": "Precios acordados con el cliente y tabla de precios por volumen."},
    # ── Ingeniería ──
    "alta":      {"etiqueta": "Alta de productos", "grupo": "Ingeniería", "rol": "Ingeniería Alta de Productos Yelke",
                  "paso": "preparar_manufactura", "rutas": ["ProductoList", "ProductoDetail", "ProductoNuevo"],
                  "doctypes": {"Item": "editar", "BOM": "editar", "UOM": "ver", "Item Group": "ver", "Costeo": "editar"},
                  "descripcion": "Da de alta los productos terminados, piezas y servicios."},
    "flujo_produccion": {"etiqueta": "Flujo de producción", "grupo": "Ingeniería",
                  "rol": "Ingeniería Flujo de Producción Yelke", "paso": "flujo_manufactura", "rutas": [],
                  "doctypes": {"BOM": "editar", "Subcontracting BOM": "editar", "Costeo": "editar"},
                  "descripcion": "Arma, confirma y revierte el flujo de producción del costeo."},
    "plantillas": {"etiqueta": "Plantillas", "grupo": "Ingeniería", "rol": "Ingeniería Plantillas Yelke",
                  "rutas": ["Plantillas"], "doctypes": {},
                  "descripcion": "Plantillas de costeo reutilizables."},
    # ── Producción (las 9 de siempre) ──
    "tablero":     {"etiqueta": "Tablero", "grupo": "Producción", "rol": "Producción Tablero Yelke",
                    "paso": "producir", "rutas": [], "doctypes": {},
                    "descripcion": "Ve el tablero de producción de la orden de venta."},
    "preparacion": {"etiqueta": "Preparación", "grupo": "Producción", "rol": "Producción Preparación Yelke",
                    "paso": "producir", "rutas": ["MaterialRequestList"],
                    "doctypes": {"Production Plan": "editar", "Material Request": "editar", "Purchase Order": "editar", "Costeo": "editar"},
                    "descripcion": "Plan, solicitud de material, lotes de entrega, órdenes a talleres y apertura de lotes."},
    "om":          {"etiqueta": "Orden de manufactura", "grupo": "Producción", "rol": "Producción Orden de Manufactura Yelke",
                    "paso": "producir", "rutas": [], "doctypes": {"Costeo": "editar"},
                    "descripcion": "Captura la orden de manufactura general por producto."},
    "materia":     {"etiqueta": "Materia prima", "grupo": "Producción", "rol": "Producción Materia Prima Yelke",
                    "paso": "producir", "rutas": ["PurchaseOrderList", "PurchaseOrderDetail", "PurchaseOrderNueva", "PurchaseReceiptList"],
                    "doctypes": {"Purchase Order": "editar", "Supplier Quotation": "editar", "Request for Quotation": "editar",
                                 "Purchase Receipt": "editar", "Supplier": "editar", "Address": "editar", "Contact": "editar",
                                 "Bank Account": "editar"},
                    "descripcion": "Compra la materia prima: cotizaciones a proveedor, orden de compra y recibo."},
    "flujo":       {"etiqueta": "Flujo del lote", "grupo": "Producción", "rol": "Producción Flujo Yelke",
                    "paso": "producir", "rutas": [], "doctypes": {"Subcontracting Order": "editar"},
                    "descripcion": "Ve la matriz del lote y crea los encargos a talleres."},
    "talleres":    {"etiqueta": "Talleres", "grupo": "Producción", "rol": "Producción Talleres Yelke",
                    "paso": "producir", "rutas": ["PurchaseOrderList", "PurchaseOrderDetail"],
                    "doctypes": {"Purchase Order": "editar", "Subcontracting Order": "editar", "Subcontracting Receipt": "editar",
                                 "Stock Entry": "editar", "Supplier": "editar", "Address": "editar", "Contact": "editar",
                                 "Bank Account": "editar"},
                    "descripcion": "Lleva cada taller: encargos, envío de material y recibo del trabajo."},
    "envios":      {"etiqueta": "Envíos", "grupo": "Producción", "rol": "Producción Envíos Yelke",
                    "paso": "producir", "rutas": ["PurchaseReceiptList", "DeliveryNoteList"],
                    "doctypes": {"Purchase Receipt": "editar", "Stock Entry": "editar", "Subcontracting Receipt": "editar",
                                 "Delivery Note": "ver", "Supplier": "editar"},
                    "descripcion": "Almacén: recibe material, envía a talleres, recibe de talleres y devoluciones."},
    "facturas":    {"etiqueta": "Facturas de compra", "grupo": "Producción", "rol": "Producción Facturas Yelke",
                    "paso": "producir", "rutas": ["PurchaseInvoiceList"],
                    "doctypes": {"Purchase Invoice": "editar"},
                    "descripcion": "Captura y valida las facturas de compra: material, maquila y fletes."},
    "entrega":     {"etiqueta": "Entrega", "grupo": "Producción", "rol": "Producción Entrega Yelke",
                    "paso": "producir", "rutas": ["DeliveryNoteList"],
                    "doctypes": {"Delivery Note": "editar", "Address": "editar", "Contact": "editar"},
                    "descripcion": "Crea y valida las remisiones de cada lote terminado."},
    # ── Finanzas ──
    "facturar":  {"etiqueta": "Facturar", "grupo": "Finanzas", "rol": "Finanzas Facturar Yelke",
                  "paso": "facturar", "rutas": ["SalesInvoiceList", "SalesInvoiceDetail", "SalesInvoiceNueva"],
                  "doctypes": {"Sales Invoice": "editar", "Payment Entry": "editar", "Journal Entry": "ver"},
                  "descripcion": "Emite la factura de venta y registra cobros."},
    "reporte":   {"etiqueta": "Reporte final", "grupo": "Finanzas", "rol": "Finanzas Reporte Final Yelke",
                  "paso": "reportar", "rutas": [], "doctypes": {},
                  "descripcion": "Rentabilidad real de cada proyecto y su PDF."},
    "indicadores": {"etiqueta": "Indicadores financieros", "grupo": "Finanzas", "rol": "Finanzas Indicadores Yelke",
                  "rutas": [], "doctypes": {},
                  "descripcion": "Inicio con ventas, márgenes, utilidad y pagos a talleres."},
    # ── Dirección y administración ──
    "direccion": {"etiqueta": "Panel de Dirección", "grupo": "Dirección", "rol": "Dirección Panel Yelke",
                  "rutas": ["Direccion"], "doctypes": {},
                  "descripcion": "Proyectos y resumen de toda la empresa."},
    "accesos":   {"etiqueta": "Accesos", "grupo": "Administración", "rol": "Administración Accesos Yelke",
                  "rutas": ["Accesos"], "doctypes": {},
                  "descripcion": "Asigna vistas a los puestos y usuarios."},
}
for _clave, _v in VISTAS.items():
    _v["rol_ver"] = f"Ver {_v['rol']}"

# Compatibilidad: lo que ya importaban otros módulos, derivado del catálogo.
VISTAS_PRODUCCION = {c: v["rol"] for c, v in VISTAS.items() if v["grupo"] == "Producción"}
ETIQUETAS_VISTA = {c: v["etiqueta"] for c, v in VISTAS.items()}
ROLES_VISTA = {**{v["rol"]: v["descripcion"] for v in VISTAS.values()},
               **{v["rol_ver"]: f"Solo lectura: {v['descripcion']}" for v in VISTAS.values()}}
ROLES_VISTA_PRODUCCION = {v["rol"]: v["descripcion"] for v in VISTAS.values() if v["grupo"] == "Producción"}

# ── Permisos de ERPNext por vista (Escritorio y API estándar; patch v0_2_71) ──
# Lo que TODA vista necesita leer para que carguen los formularios y los PDF.
LECTURA_BASE = (
    "Costeo", "Company", "Warehouse", "Currency", "UOM", "Item", "Item Group", "Brand", "Customer", "Customer Group",
    "Supplier", "Supplier Group", "Territory", "Country", "Address", "Contact", "Payment Terms Template",
    "Terms and Conditions", "Sales Taxes and Charges Template", "Purchase Taxes and Charges Template",
    "Item Tax Template", "Mode of Payment", "Price List", "Talla", "Letter Head", "Print Format", "Bank",
    "Cost Center", "Sales Order", "Quotation",
)
PERMISOS_VER = ("read", "print", "email", "report", "export")
PERMISOS_EDITAR = PERMISOS_VER + ("write", "create")
# Quien administra (Director, Supervisor): además valida, cancela, corrige y borra.
ROLES_ADMIN_DOCS = ("Director Yelke", "Supervisor Yelke")
PERMISOS_ADMIN = PERMISOS_EDITAR + ("submit", "cancel", "amend", "delete")


def permisos_por_rol():
    """{(doctype, rol): set(ptypes)} que dan las vistas. Editar = leer y capturar, y
    VALIDAR los documentos validables de su vista (las aprobaciones siguen frenando lo
    que las lleve; el Costeo solo lo valida Costear). Cancelar, corregir y borrar,
    solo Director y Supervisor."""
    out = {}

    def dar(dt, rol, ptypes):
        out.setdefault((dt, rol), set()).update(ptypes)

    todos = set(LECTURA_BASE)
    for clave, v in VISTAS.items():
        for dt in LECTURA_BASE:
            dar(dt, v["rol"], PERMISOS_VER)
            dar(dt, v["rol_ver"], PERMISOS_VER)
        for dt, nivel in v.get("doctypes", {}).items():
            todos.add(dt)
            dar(dt, v["rol_ver"], PERMISOS_VER)
            if nivel == "editar":
                dar(dt, v["rol"], PERMISOS_EDITAR + (("submit",) if dt != "Costeo" or clave == "costear" else ()))
            else:
                dar(dt, v["rol"], PERMISOS_VER)
    for dt in todos:
        for rol in ROLES_ADMIN_DOCS:
            dar(dt, rol, PERMISOS_ADMIN)
    return out


# Quien ve y hace TODO, sin necesidad de los roles por vista. "CEO" es el rol legado.
PASE_LIBRE = ("System Manager", "Director Yelke", "Supervisor Yelke", "CEO")
PASE_LIBRE_PRODUCCION = PASE_LIBRE

ROLES_YELKE = {**ROLES_PROCESO, **ROLES_APROBACION, **ROLES_FLUJO_DOCUMENTOS, **ROLES_VISTA}

# Rol que hoy usa item_api._es_ceo() para aprobar precios. Se mantiene por
# compatibilidad; el motor nuevo acepta tanto este como "Director Yelke".
ROL_CEO_LEGACY = "CEO"

# ── Aprobaciones (docs/plan-panel-direccion.md §3) ───────────────────────────
# Documentos que pasan por aprobación y con qué esquema:
#   simple: Enviar a aprobación -> Aprobador
#   doble:  Enviar a aprobación -> Revisor -> Aprobador
# Agregar un documento aquí es todo lo que hace falta del lado de las reglas; el
# patch de campos (v0_2_60) y los hooks de hooks.py leen esta misma lista.
DOCUMENTOS_CON_APROBACION = {
    "Costeo": "simple",
    "Quotation": "simple",
    "Sales Order": "simple",
    "Purchase Invoice": "simple",
    "Purchase Order": "doble",  # materia prima y maquila: mismo doctype
}

ROL_DIRECTOR = "Director Yelke"
ROL_APROBADOR = "Aprobador de Documentos Yelke"
ROL_REVISOR = "Revisor de Documentos Yelke"

# Quién valida los precios acordados (item_api._es_ceo). "CEO" es el rol legado.
ROLES_APROBAR_PRECIOS = (ROL_CEO_LEGACY, ROL_DIRECTOR, "Aprobador de Precios Yelke")


def nivel_aprobacion(doctype):
    """'simple', 'doble' o None si el documento no pasa por aprobación."""
    return DOCUMENTOS_CON_APROBACION.get(doctype)


def puede_ver_panel_direccion(user=None):
    """El panel completo de Dirección (proyectos y resumen, además de la bandeja).
    Ver el panel y aprobar son cosas distintas: aprobar lo decide
    puede_aprobar_documentos."""
    import frappe

    return bool({ROL_DIRECTOR, "System Manager"} & set(frappe.get_roles(user))) or puede("direccion", "ver", user)


# Quién ve las cifras financieras de la empresa (ventas, márgenes, utilidad, clientes,
# lo que se paga a cada taller). El resto del equipo ve el tablero operativo de Inicio.
ROLES_FINANZAS = (ROL_DIRECTOR, "Supervisor Yelke", "Analista de Costos Yelke", "System Manager")


def puede_ver_finanzas(user=None):
    import frappe

    return bool(set(ROLES_FINANZAS) & set(frappe.get_roles(user))) or puede("indicadores", "ver", user)


def puede_aprobar_precios(user=None):
    import frappe

    return bool(set(ROLES_APROBAR_PRECIOS) & set(frappe.get_roles(user))) or bool(delegacion_vigente(user))


def usuarios_con_rol(*roles):
    """Usuarios internos habilitados que tienen alguno de `roles`, directo o por su
    Perfil de Rol. System Manager no cuenta como destinatario: es el pase de
    desarrollador y no debe llenarle la campana a nadie."""
    import frappe

    if not roles:
        return []
    directos = frappe.get_all(
        "Has Role", filters={"role": ["in", roles], "parenttype": "User"}, pluck="parent")
    perfiles = frappe.get_all(
        "Has Role", filters={"role": ["in", roles], "parenttype": "Role Profile"}, pluck="parent")
    por_perfil = frappe.get_all(
        "User", filters={"role_profile_name": ["in", perfiles]}, pluck="name") if perfiles else []
    candidatos = set(directos) | set(por_perfil)
    candidatos -= {"Administrator", "Guest"}
    if not candidatos:
        return []
    return frappe.get_all(
        "User",
        filters={"name": ["in", list(candidatos)], "enabled": 1, "user_type": "System User"},
        pluck="name",
    )


def delegacion_vigente(user=None):
    """La delegación de Dirección que `user` tiene HOY (o None). Una delegación no
    reparte roles: da el permiso de aprobar mientras sus fechas estén vigentes y
    deja de darlo sola (ver api/delegacion.py). Se guarda por petición porque los
    permisos se consultan muchas veces."""
    import frappe

    user = user or frappe.session.user
    cache = getattr(frappe.local, "delegacion_yelke", None)
    if cache is None:
        cache = frappe.local.delegacion_yelke = {}
    if user not in cache:
        fila = None
        if frappe.db.table_exists("Delegacion Aprobacion"):
            hoy = frappe.utils.nowdate()
            fila = frappe.db.get_value(
                "Delegacion Aprobacion",
                {"a_usuario": user, "cancelada": 0, "desde": ["<=", hoy], "hasta": [">=", hoy]},
                ["name", "de_usuario", "desde", "hasta"], as_dict=True, order_by="hasta desc")
        cache[user] = fila
    return cache[user]


def olvidar_delegaciones():
    """Al crear o terminar una delegación, que la misma petición ya lo vea."""
    import frappe

    frappe.local.delegacion_yelke = {}


def puede_aprobar_documentos(user=None):
    """True si `user` (o el usuario actual) puede dar la aprobación/validación
    final de un documento del flujo -- rol 'Aprobador de Documentos Yelke', una
    delegación vigente de Dirección, o System Manager como respaldo de
    administrador (para no bloquear a nadie mientras el rol todavía no está
    asignado a las personas correctas)."""
    import frappe

    roles = frappe.get_roles(user)
    if "Aprobador de Documentos Yelke" in roles or "System Manager" in roles:
        return True
    return bool(delegacion_vigente(user))


def puede_revisar_documentos(user=None):
    """True si `user` (o el usuario actual) puede dar la verificación intermedia
    del esquema Doble -- rol 'Revisor de Documentos Yelke', o quien ya pueda dar
    la aprobación final (un Aprobador siempre puede hacer también el paso previo),
    o System Manager como respaldo de administrador."""
    import frappe

    roles = frappe.get_roles(user)
    if {"Revisor de Documentos Yelke", "Aprobador de Documentos Yelke", "System Manager"} & set(roles):
        return True
    return bool(delegacion_vigente(user))


# ── Permisos por vista de Producción ─────────────────────────────────────────
def accesos(user=None):
    """{clave: "editar" | "ver"} de las vistas que `user` (o el actual) puede abrir.
    Editar gana sobre ver. Con pase libre, todas en editar. Los préstamos de permisos
    agregan roles, así que entran solos."""
    import frappe

    roles = set(frappe.get_roles(user))
    if roles & set(PASE_LIBRE):
        return {c: "editar" for c in VISTAS}
    out = {}
    for clave, v in VISTAS.items():
        if v["rol"] in roles:
            out[clave] = "editar"
        elif v["rol_ver"] in roles:
            out[clave] = "ver"
    # Roles de antes que ya daban acceso a algo (no quitarlo al estrenar el catálogo).
    if "indicadores" not in out and set(ROLES_FINANZAS) & roles:
        out["indicadores"] = "ver"
    if "direccion" not in out and ROL_DIRECTOR in roles:
        out["direccion"] = "editar"
    return out


def puede(clave, nivel="ver", user=None):
    """True si `user` tiene la vista en ese nivel (editar incluye ver)."""
    n = accesos(user).get(clave)
    return n == "editar" or (n == "ver" and nivel == "ver")


def vistas_produccion(user=None):
    """Claves de vista de Producción que `user` puede abrir (ver o editar)."""
    return [c for c in accesos(user) if c in VISTAS_PRODUCCION]


def puede_ver(clave, user=None):
    """True si `user` puede abrir esa vista (compatibilidad)."""
    return puede(clave, "ver", user)


def requiere_vista(*claves, nivel="editar", user=None):
    """Exige al menos UNA de las vistas en ese nivel; si no, PermissionError en español.

    Por omisión pide EDITAR: es lo que llevan los endpoints que escriben."""
    import frappe
    from frappe import _

    if not claves:
        return
    if any(puede(c, nivel, user) for c in claves):
        return
    roles = [VISTAS[c]["rol"] if nivel == "editar" else VISTAS[c]["rol_ver"] for c in claves if c in VISTAS]
    if len(roles) == 1:
        frappe.throw(_("Necesitas el rol {0} para esto.").format(roles[0]), frappe.PermissionError)
    frappe.throw(_("Necesitas alguno de estos roles: {0}.").format(", ".join(roles)), frappe.PermissionError)


def mapa_vistas():
    """Lo que la pantalla necesita del catálogo: etiqueta, grupo, paso y rutas."""
    return {c: {"etiqueta": v["etiqueta"], "grupo": v["grupo"], "paso": v.get("paso"), "rutas": v.get("rutas", [])}
            for c, v in VISTAS.items()}