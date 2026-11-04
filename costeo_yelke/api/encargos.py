"""Encargos: alguien le encarga a una persona un paso de un proyecto (docs/plan-encargos.md).

Un encargo es un ToDo de Frappe ligado al Costeo (también se ve en el Escritorio, en
"Asignado a") con campos propios (patch v0_2_72). Le avisa a la persona por la campana
y por correo, se ve en su Inicio, en el proyecto y en el panel de Dirección, y se
marca solo cuando el paso se atiende (ver revisar).

"Se marca solo": cada paso sabe si tiene algo pendiente (_pendiente). El encargo se
cierra cuando el paso TUVO algo pendiente después de encargarse (visto_yelke) y ya no
lo tiene. Así no se cierra antes de que el paso arranque, y el de un paso que ya
estaba hecho se queda para cerrar a mano.
"""
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, formatdate, getdate, now_datetime, nowdate

from costeo_yelke.api.aprobaciones import EN_APROBACION, _avisar
from costeo_yelke.roles import PASE_LIBRE, VISTAS, accesos, puede, puede_ver_panel_direccion

ABIERTO = "Open"
AUTOMATICO, MANUAL, REGRESADO, QUITADO = "Automático", "Manual", "Regresado", "Quitado"
DIAS_TERMINADOS = 7
_ESTADOS_FLUJO = ("En Producción", "Entregado", "Completado")

# Pasos que se pueden encargar (los que viven dentro del proyecto), en el orden del
# proyecto. "" = encargo general del proyecto.
ENCARGABLES = [c for c, v in VISTAS.items() if v.get("paso")]
GENERAL = ""
# Pasos que van por lote: el encargo puede ser de un lote en particular.
CON_LOTE = ("materia", "flujo", "talleres", "envios", "entrega")
# Cuándo se marca solo cada paso (lo que se le enseña a quien encarga).
REGLAS = {
    "costear": _("al validar el costeo o enviarlo a aprobación"),
    "cotizar": _("al validar una cotización del proyecto o enviarla a aprobación"),
    "vender": _("al validar la orden de venta o enviarla a aprobación"),
    "alta": _("cuando ya no queden artículos por dar de alta"),
    "flujo_produccion": _("al confirmar el flujo de producción"),
    "preparacion": _("cuando la solicitud de material y las órdenes a talleres estén validadas"),
    "materia": _("cuando la materia prima esté pedida y recibida"),
    "talleres": _("cuando los talleres entreguen todo"),
    "envios": _("cuando el material esté recibido, enviado a los talleres y su trabajo recibido"),
    "facturas": _("cuando todas las compras del proyecto estén facturadas"),
    "entrega": _("cuando se entregue todo (con lote: al validar su remisión)"),
    "facturar": _("cuando la orden de venta esté facturada completa"),
}
# El paso que normalmente sigue, para "encargar el siguiente" al terminar uno.
SIGUIENTE = {
    "costear": "cotizar", "cotizar": "vender", "vender": "alta", "alta": "flujo_produccion",
    "flujo_produccion": "preparacion", "preparacion": "materia", "materia": "talleres",
    "talleres": "entrega", "envios": "entrega", "entrega": "facturar", "facturas": "facturar",
    "facturar": "reporte",
}

_CAMPOS = ["name", "allocated_to", "assigned_by", "reference_name as costeo", "description", "date", "status",
           "creation", "modified", "vista_yelke", "lote_yelke", "mensaje_yelke", "visto_yelke", "cierre_yelke",
           "cerrado_en_yelke", "nota_cierre_yelke", "avisos_yelke"]


def _hay_encargos():
    return frappe.db.has_column("ToDo", "encargo_yelke")


def _etiqueta(vista):
    return VISTAS[vista]["etiqueta"] if vista in VISTAS else _("General del proyecto")


def _nombre(user):
    return frappe.db.get_value("User", user, "full_name") or user


def _pase_libre(user=None):
    return bool(set(frappe.get_roles(user)) & set(PASE_LIBRE))


def _costeo(costeo):
    campos = ["name", "titulo", "cliente", "costeo_status", "docstatus", "modified"]
    for extra in ("compañia", "estado_aprobacion_yelke"):
        if frappe.db.has_column("Costeo", extra):
            campos.append(extra)
    return frappe.db.get_value("Costeo", costeo, campos, as_dict=True)


# ─────────────────────────────────────────────────────────────────────────────
# A dónde lleva un encargo (ruta del SPA)
# ─────────────────────────────────────────────────────────────────────────────

def _query_paso(vista, lote=None):
    lote = lote or None
    paso = {"costear": 0, "cotizar": 1, "vender": 2, "alta": 3, "flujo_produccion": 4, "facturar": 7, "reporte": 8}
    if vista in paso:
        return {"step": paso[vista]}
    prod = {"step": 5}
    if vista in ("materia", "flujo", "talleres", "entrega") and lote:
        return {**prod, "vista": "lote", "lote": lote, "paso": "talleres" if vista == "flujo" else vista}
    return {**prod, **{
        "tablero": {"vista": "tablero"}, "preparacion": {"vista": "preparacion"},
        "om": {"vista": "preparacion", "prep": 3}, "materia": {"vista": "preparacion", "prep": 2},
        "flujo": {"vista": "tablero"}, "talleres": {"vista": "tablero"}, "entrega": {"vista": "tablero"},
        "envios": {"vista": "envios", "filtro_lote": lote}, "facturas": {"vista": "facturas", "filtro_lote": lote or "__todos"},
    }.get(vista, {"vista": "tablero"})}


def ruta(costeo, vista=GENERAL, lote=None, compania=None, extra=None):
    """Ruta del SPA (sin /costeo-yelke) al proyecto, en el paso y lote del encargo."""
    q = _query_paso(vista, lote) if vista else {}
    if compania:
        q["compania"] = compania
    q.update(extra or {})
    q = {k: v for k, v in q.items() if v not in (None, "")}
    return f"/costeo/{quote(costeo)}" + ("?" + "&".join(f"{k}={quote(str(v))}" for k, v in q.items()) if q else "")


def _ruta_aviso(costeo, vista=GENERAL, lote=None, extra=None):
    c = _costeo(costeo) or {}
    return "/costeo-yelke" + ruta(costeo, vista, lote, c.get("compañia"), extra)


# ─────────────────────────────────────────────────────────────────────────────
# ¿Tiene el paso algo pendiente? (True / False; None = se cierra a mano)
# ─────────────────────────────────────────────────────────────────────────────

def _validado_desde(doctype, costeo, desde):
    """Validado -- o enviado a aprobación: ahí ya terminó su parte quien lo hizo -- después
    de asignarse."""
    if not frappe.db.has_column(doctype, "costeo"):
        return False
    base = {"costeo": costeo, "modified": [">=", desde]}
    if frappe.db.exists(doctype, {**base, "docstatus": 1}):
        return True
    return frappe.db.has_column(doctype, "estado_aprobacion_yelke") and bool(
        frappe.db.exists(doctype, {**base, "docstatus": 0, "estado_aprobacion_yelke": ["in", list(EN_APROBACION)]}))


def _filas_mi_panel(vista, c, lote=None):
    from costeo_yelke.api import mi_panel

    fn = mi_panel.SECCIONES.get(vista)
    filas = fn({c.name: c}) if fn else []
    filas = [f for f in filas if f["costeo"] == c.name]
    if lote:
        filas = [f for f in filas if (f["ruta"].get("query") or {}).get("lote") == lote]
    return filas


def _pendiente(e, c):
    vista, lote = e.vista_yelke or GENERAL, e.lote_yelke or None
    if vista == "costear":
        return not (c.docstatus == 1 or c.get("estado_aprobacion_yelke") in EN_APROBACION)
    if vista == "cotizar":
        return not _validado_desde("Quotation", c.name, e.creation)
    if vista == "vender":
        return not _validado_desde("Sales Order", c.name, e.creation)
    if vista == "flujo_produccion":
        return c.costeo_status not in _ESTADOS_FLUJO
    if vista == "alta":
        if c.costeo_status in _ESTADOS_FLUJO:
            return False
        if c.costeo_status != "Orden de Venta":
            return True  # todavía no hay qué dar de alta: el paso no arranca
        from costeo_yelke.api.costeo_api import get_articulos_pendientes

        grupos = get_articulos_pendientes(c.name).get("grupos") or []
        return any(g.get("row_type") != "subensamblaje_etapa" for g in grupos)
    if vista == "preparacion":
        mrs = frappe.get_all("Material Request", filters={"costeo": c.name, "docstatus": ["<", 2]}, pluck="docstatus")
        pos = frappe.get_all("Purchase Order", filters={"costeo": c.name, "is_subcontracted": 1, "docstatus": ["<", 2]},
                             pluck="docstatus")
        return not (mrs and pos and all(d == 1 for d in mrs + pos))
    if vista == "entrega" and lote:
        if not frappe.db.has_column("Delivery Note", "lote_ref"):
            return None
        dns = frappe.get_all("Delivery Note", filters={"lote_ref": lote, "docstatus": ["<", 2], "modified": [">=", e.creation],
                                                       **({"costeo": c.name} if frappe.db.has_column("Delivery Note", "costeo") else {})},
                             pluck="docstatus")
        return not (dns and all(d == 1 for d in dns))
    if vista == "envios":
        if _filas_mi_panel("materia", c, lote) or _filas_mi_panel("talleres", c, lote) or _filas_mi_panel("envios", c, lote):
            return True
        # Sin encargos a talleres todavía, falta todo lo de mandarles material y recibir
        # su trabajo: no hay "nada pendiente" solo porque aún no existen.
        return not _talleres_terminados(c.name, lote)
    if vista == "talleres":
        return bool(_filas_mi_panel("talleres", c, lote)) or not _talleres_terminados(c.name, lote)
    if vista == "facturas":
        # Lo pendiente de hoy, y también las órdenes que todavía no llegan (otro lote,
        # maquila en proceso): mientras alguna no esté facturada, falta trabajo.
        return bool(_filas_mi_panel("facturas", c)) or bool(frappe.db.exists(
            "Purchase Order", {"costeo": c.name, "docstatus": 1, "per_billed": ["<", 99.99], "status": ["!=", "Closed"]}))
    if vista == "facturar":
        return bool(_filas_mi_panel("facturar", c)) or bool(frappe.db.exists(
            "Sales Order", {"costeo": c.name, "docstatus": 1, "per_billed": ["<", 99.99], "status": ["!=", "Closed"]}))
    if vista == "materia":
        return bool(_filas_mi_panel(vista, c, lote)) or _material_sin_pedir(c.name, lote)
    if vista == "entrega":
        return bool(_filas_mi_panel(vista, c, lote))
    return None


def _material_sin_pedir(costeo, lote=None):
    """Renglones de la solicitud (del lote, si se indica) que todavía no tienen orden de
    compra. La solicitud no lleva lote, así que Mi panel no la cuenta para el lote: antes
    de generar las órdenes, la materia prima del lote parecía no tener nada pendiente."""
    filtros = {"parent": ["in", frappe.get_all("Material Request", filters={"costeo": costeo, "docstatus": 1},
                                               pluck="name") or [""]]}
    if lote and frappe.db.has_column("Material Request Item", "lote_ref"):
        filtros["lote_ref"] = lote
    renglones = frappe.get_all("Material Request Item", filters=filtros, pluck="name")
    if not renglones:
        return False
    pedidos = set(frappe.get_all("Purchase Order Item", filters={"material_request_item": ["in", renglones], "docstatus": ["<", 2]},
                                 pluck="material_request_item"))
    return any(r not in pedidos for r in renglones)


def _talleres_terminados(costeo, lote=None):
    """Cada orden a taller del proyecto ya tiene su encargo (del lote, si se indica) y
    todo se recibió completo. Por orden y no por encargo: los encargos de los talleres
    siguientes se crean conforme avanza el lote, y mientras no existan no hay que dar
    por terminado nada."""
    pos = frappe.get_all("Purchase Order", filters={"costeo": costeo, "is_subcontracted": 1, "docstatus": 1},
                         fields=["name", "per_received"])
    if not pos:
        return False
    if not lote or not frappe.db.has_column("Subcontracting Order", "lote_ref"):
        return all(flt(p.per_received) >= 99.99 for p in pos)
    for p in pos:
        recibido = frappe.get_all("Subcontracting Order", filters={"purchase_order": p.name, "lote_ref": lote, "docstatus": 1},
                                  pluck="per_received")
        if not recibido or any(flt(x) < 99.99 for x in recibido):
            return False
    return True


def _regla(vista):
    r = REGLAS.get(vista)
    return _("Se marca sola {0}.").format(r) if r else _("Se marca a mano con «Hecha».")


# ─────────────────────────────────────────────────────────────────────────────
# Revisar (cierra solos los que ya se atendieron)
# ─────────────────────────────────────────────────────────────────────────────

def _cerrar(e, cierre, nota=None, estado="Closed"):
    # db_set y no save: al cambiar de estado, el ToDo de Frappe escribe en el proyecto
    # "X eliminó su asignación", que suena a que la borró. La actividad de la app ya
    # cuenta quién la terminó y cómo (eventos_actividad).
    todo = frappe.get_doc("ToDo", e.name)
    todo.db_set({"status": estado, "cierre_yelke": cierre, "cerrado_en_yelke": now_datetime(),
                 "nota_cierre_yelke": nota or None})
    todo.update_in_reference()


def _titulo(e, c=None):
    c = c or _costeo(e.costeo) or {}
    lote = f" · {e.lote_yelke}" if e.get("lote_yelke") else ""
    return f"{_etiqueta(e.vista_yelke)}{lote} · {c.get('titulo') or e.costeo}"


def revisar(costeo):
    """Cierra los encargos abiertos del proyecto cuyo paso ya se atendió y marca los
    que ya tienen algo pendiente. Nunca truena: un error aquí no debe tumbar el
    guardado del documento que lo disparó."""
    if not costeo or not _hay_encargos():
        return
    abiertos = frappe.get_all("ToDo", filters={"reference_type": "Costeo", "reference_name": costeo, "status": ABIERTO,
                                               "encargo_yelke": 1}, fields=_CAMPOS)
    if not abiertos:
        return
    try:
        c = _costeo(costeo)
        # Solo un proyecto CANCELADO quita lo abierto. "Completado" llega en cuanto se
        # genera la factura de venta (aún en borrador): ahí sigue habiendo trabajo
        # (validarla, cobrar, el reporte), así que se evalúa con su regla normal.
        if not c or c.docstatus == 2 or c.costeo_status == "Cancelado":
            motivo = _("El proyecto se canceló.")
            for e in abiertos:
                _cerrar(e, QUITADO, motivo, estado="Cancelled")
                _avisar([e.allocated_to], _("Asignación cerrada: {0}").format(_titulo(e, c)), "Costeo", costeo,
                        mensaje=motivo, ruta=_ruta_aviso(costeo), correo=False)
            return
        for e in abiertos:
            p = _pendiente(e, c)
            if p is None:
                continue
            if p:
                if not e.visto_yelke:
                    frappe.db.set_value("ToDo", e.name, "visto_yelke", 1, update_modified=False)
            elif e.visto_yelke:
                _cerrar(e, AUTOMATICO, _("Se marcó sola: {0}.").format(REGLAS.get(e.vista_yelke, "")))
                _avisar_terminado(e, c, automatico=True)
    except frappe.QueryDeadlockError:
        # Otra petición está cerrando la misma asignación al mismo tiempo (p. ej. al
        # generar la factura y recargar la pantalla): esa la deja bien; no es error.
        pass
    except Exception:
        frappe.log_error(title=f"Encargos: no se pudo revisar {costeo}")


def _avisar_terminado(e, c, automatico=False, nota=None):
    quien = _nombre(e.allocated_to)
    sig = SIGUIENTE.get(e.vista_yelke)
    extra = {"encargar": sig} if sig else None
    texto = _("Se marcó sola: {0}.").format(REGLAS.get(e.vista_yelke, "")) if automatico else (nota or "")
    if sig:
        texto = (texto + "\n" if texto else "") + _("Siguiente paso: {0}.").format(_etiqueta(sig))
    _avisar([e.assigned_by], _("{0} terminó: {1}").format(quien, _titulo(e, c)), "Costeo", c.name,
            mensaje=texto, ruta=_ruta_aviso(c.name, e.vista_yelke, e.lote_yelke, extra),
            boton=_("Abrir el proyecto"), correo=False)


def _costeo_de_documento(doc):
    if doc.doctype == "Costeo":
        return doc.name
    for campo in ("costeo", "flete_costeo"):
        if doc.get(campo):
            return doc.get(campo)
    po = sco = so = None
    for it in doc.get("items") or []:
        po = po or it.get("purchase_order")
        sco = sco or it.get("subcontracting_order")
        so = so or it.get("against_sales_order") or it.get("sales_order")
    if doc.doctype == "Subcontracting Order":
        po = doc.get("purchase_order") or po
    if doc.doctype == "Stock Entry":
        sco = doc.get("subcontracting_order") or sco
    if sco and not po:
        po = frappe.db.get_value("Subcontracting Order", sco, "purchase_order")
    if po and frappe.db.has_column("Purchase Order", "costeo"):
        return frappe.db.get_value("Purchase Order", po, "costeo")
    if so:
        return frappe.db.get_value("Sales Order", so, "costeo")
    return None


def al_mover_documento(doc, method=None):
    """doc_events (on_change) de los documentos del proyecto."""
    if not _hay_encargos() or not frappe.db.exists("ToDo", {"status": ABIERTO, "encargo_yelke": 1}):
        return
    try:
        costeo = _costeo_de_documento(doc)
    except Exception:
        costeo = None
    if costeo:
        revisar(costeo)


def revisar_todos():
    """Cada hora: lo que cambió por caminos sin eventos (db.set_value, conciliaciones)."""
    if not _hay_encargos():
        return
    for costeo in set(frappe.get_all("ToDo", filters={"status": ABIERTO, "encargo_yelke": 1, "reference_type": "Costeo"},
                                     pluck="reference_name")):
        revisar(costeo)


def avisos_vencimiento():
    """Una vez al día: "vence hoy" a la persona y "venció" a ella y a quien encargó."""
    if not _hay_encargos():
        return
    hoy = getdate(nowdate())
    for e in frappe.get_all("ToDo", filters={"status": ABIERTO, "encargo_yelke": 1, "date": ["is", "set"]}, fields=_CAMPOS):
        fecha, avisos = getdate(e.date), cint(e.avisos_yelke)
        if fecha == hoy and avisos < 1:
            _avisar([e.allocated_to], _("Vence hoy: {0}").format(_titulo(e)), "Costeo", e.costeo,
                    mensaje=e.mensaje_yelke or "", ruta=_ruta_aviso(e.costeo, e.vista_yelke, e.lote_yelke))
            frappe.db.set_value("ToDo", e.name, "avisos_yelke", 1, update_modified=False)
        elif fecha < hoy and avisos < 2:
            asunto = _("Venció el {0}: {1}").format(formatdate(fecha), _titulo(e))
            _avisar([e.allocated_to, e.assigned_by], asunto, "Costeo", e.costeo, mensaje=e.mensaje_yelke or "",
                    ruta=_ruta_aviso(e.costeo, e.vista_yelke, e.lote_yelke))
            frappe.db.set_value("ToDo", e.name, "avisos_yelke", 2, update_modified=False)


def al_cambiar_todo(doc, method=None):
    """Un encargo cerrado o quitado desde el Escritorio cuenta como "Listo" / "Quitado"."""
    if frappe.flags.encargo_yelke_api or not doc.get("encargo_yelke") or doc.is_new():
        return
    antes = doc.get_doc_before_save()
    if not antes or antes.status == doc.status or antes.status != ABIERTO:
        return
    cierre = MANUAL if doc.status == "Closed" else QUITADO
    doc.db_set({"cierre_yelke": cierre, "cerrado_en_yelke": now_datetime()}, update_modified=False)
    e = frappe._dict(doc.as_dict(), costeo=doc.reference_name)
    c = _costeo(doc.reference_name)
    if c and cierre == MANUAL and frappe.session.user != doc.assigned_by:
        _avisar_terminado(e, c)
    elif c and cierre == QUITADO and frappe.session.user != doc.allocated_to:
        _avisar([doc.allocated_to], _("Te quitaron la asignación: {0}").format(_titulo(e, c)), "Costeo", c.name,
                ruta=_ruta_aviso(c.name), correo=False)


# ─────────────────────────────────────────────────────────────────────────────
# Quién puede
# ─────────────────────────────────────────────────────────────────────────────

def _puede_encargar(vista):
    if puede_ver_panel_direccion() or _pase_libre():
        return True
    if vista == GENERAL:
        return any(puede(v, "editar") for v in ENCARGABLES)
    return puede(vista, "editar")


def _candidatos(vista):
    """Usuarios que pueden hacer el paso (lo tienen en Editar). Pase libre al final."""
    out = []
    for u in frappe.get_all("User", filters={"enabled": 1, "user_type": "System User", "name": ["not in", ["Administrator", "Guest"]]},
                            fields=["name", "full_name"], order_by="full_name asc"):
        mis = accesos(u.name)
        if vista == GENERAL:
            ok = any(mis.get(v) == "editar" for v in ENCARGABLES)
        else:
            ok = mis.get(vista) == "editar"
        if ok:
            out.append({"usuario": u.name, "nombre": u.full_name or u.name, "todo": _pase_libre(u.name)})
    out.sort(key=lambda x: (x["todo"], x["nombre"]))
    return out


def _encargo(name):
    e = frappe.db.get_value("ToDo", name, _CAMPOS, as_dict=True)
    if not e or not frappe.db.get_value("ToDo", name, "encargo_yelke"):
        frappe.throw(_("No existe la asignación {0}.").format(name))
    return e


def _exigir_encargado(e):
    if frappe.session.user != e.allocated_to and not _pase_libre():
        frappe.throw(_("Solo {0} puede marcar esta asignación.").format(_nombre(e.allocated_to)), frappe.PermissionError)
    if e.status != ABIERTO:
        frappe.throw(_("Esta asignación ya está cerrada."))


def _exigir_quien_encargo(e):
    if frappe.session.user != e.assigned_by and not _pase_libre() and not puede_ver_panel_direccion():
        frappe.throw(_("Solo {0} (quien la asignó) puede cambiar esta asignación.").format(_nombre(e.assigned_by)),
                     frappe.PermissionError)
    if e.status != ABIERTO:
        frappe.throw(_("Esta asignación ya está cerrada."))


# ─────────────────────────────────────────────────────────────────────────────
# Filas para las pantallas
# ─────────────────────────────────────────────────────────────────────────────

def _filas(encargos):
    if not encargos:
        return []
    costeos = {c: _costeo(c) or {} for c in {e.costeo for e in encargos}}
    usuarios = {e.allocated_to for e in encargos} | {e.assigned_by for e in encargos}
    nombres = {u.name: u.full_name or u.name for u in frappe.get_all("User", filters={"name": ["in", list(usuarios)]},
                                                                      fields=["name", "full_name"])}
    yo, libre = frappe.session.user, _pase_libre()
    hoy = getdate(nowdate())
    out = []
    for e in encargos:
        c = costeos[e.costeo]
        abierto = e.status == ABIERTO
        fecha = getdate(e.date) if e.date else None
        out.append({
            "name": e.name, "vista": e.vista_yelke or "", "etiqueta": _etiqueta(e.vista_yelke), "lote": e.lote_yelke or "",
            "mensaje": e.mensaje_yelke or "", "regla": _regla(e.vista_yelke),
            "auto": e.vista_yelke in REGLAS,
            "al_dia": abierto and _al_dia(e, c),
            "fecha": str(fecha) if fecha else "", "vencido": bool(abierto and fecha and fecha < hoy),
            "vence_hoy": bool(abierto and fecha and fecha == hoy),
            "creado": str(e.creation), "de": e.assigned_by, "de_nombre": nombres.get(e.assigned_by, e.assigned_by),
            "para": e.allocated_to, "para_nombre": nombres.get(e.allocated_to, e.allocated_to),
            "costeo": e.costeo, "proyecto": c.get("titulo") or e.costeo, "cliente": c.get("cliente") or "",
            "compania": c.get("compañia") or "",
            "ruta": ruta(e.costeo, e.vista_yelke, e.lote_yelke, c.get("compañia")),
            "estado": "abierto" if abierto else {AUTOMATICO: "hecho", MANUAL: "hecho", REGRESADO: "regresado"}.get(e.cierre_yelke, "quitado"),
            "cierre": e.cierre_yelke or "", "cerrado_en": str(e.cerrado_en_yelke or ""), "nota": e.nota_cierre_yelke or "",
            "es_mio": yo == e.allocated_to, "lo_encargue": yo == e.assigned_by,
            "puedo_cerrar": abierto and (yo == e.allocated_to or libre),
            "puedo_cambiar": abierto and (yo == e.assigned_by or libre or puede_ver_panel_direccion()),
        })
    return out


def _al_dia(e, c):
    """El paso ya no tenía nada pendiente cuando se asignó (p. ej. el alta de un
    proyecto duplicado): no se va a marcar sola, así que se le dice que la marque."""
    if e.vista_yelke not in REGLAS or e.visto_yelke or not c:
        return False
    try:
        return _pendiente(e, c) is False
    except Exception:
        return False


def _orden(filas):
    # Abiertos primero (vencidos, luego por fecha límite), después los cerrados recientes.
    return sorted(filas, key=lambda f: (f["estado"] != "abierto", not f["vencido"], f["fecha"] or "9999", f["creado"]))


def _recientes():
    return add_days(now_datetime(), -DIAS_TERMINADOS)


def _filtro_compania(encargos, company):
    if not company or not frappe.db.has_column("Costeo", "compañia"):
        return encargos
    de = dict(frappe.get_all("Costeo", filters={"name": ["in", list({e.costeo for e in encargos}) or [""]]},
                             fields=["name", "compañia"], as_list=True))
    return [e for e in encargos if de.get(e.costeo) in (company, None, "")]


def _consulta(filtros_extra, company=None):
    base = {"reference_type": "Costeo", "encargo_yelke": 1}
    abiertos = frappe.get_all("ToDo", filters={**base, **filtros_extra, "status": ABIERTO}, fields=_CAMPOS)
    cerrados = frappe.get_all("ToDo", filters={**base, **filtros_extra, "status": ["!=", ABIERTO],
                                               "cerrado_en_yelke": [">=", _recientes()]}, fields=_CAMPOS)
    return _filtro_compania(abiertos + cerrados, company)


# ─────────────────────────────────────────────────────────────────────────────
# API
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_opciones(costeo: str = None) -> dict:
    """Pasos que el usuario puede encargar en este proyecto, a quién y sus lotes."""
    if not _hay_encargos():
        return {"pasos": [], "lotes": []}
    from costeo_yelke.api.costeo_api import _lote_refs_del_costeo

    pasos = []
    for v in [*ENCARGABLES, GENERAL]:
        if not _puede_encargar(v):
            continue
        pasos.append({"clave": v, "etiqueta": _etiqueta(v), "grupo": VISTAS[v]["grupo"] if v else _("Proyecto"),
                      "con_lote": v in CON_LOTE, "regla": _regla(v), "candidatos": _candidatos(v)})
    try:
        lotes = sorted(_lote_refs_del_costeo(costeo), key=lambda x: (len(x), x)) if costeo else []
    except Exception:
        lotes = []
    return {"pasos": pasos, "lotes": lotes}


@frappe.whitelist()
def crear(costeo: str, vista: str, usuario: str, mensaje: str = None, fecha: str = None, lote: str = None) -> dict:
    vista = vista or GENERAL
    if vista != GENERAL and vista not in ENCARGABLES:
        frappe.throw(_("Ese paso no se puede asignar."))
    if not _puede_encargar(vista):
        frappe.throw(_("No tienes el paso {0} para asignarlo.").format(_etiqueta(vista)), frappe.PermissionError)
    if usuario not in {x["usuario"] for x in _candidatos(vista)}:
        frappe.throw(_("{0} no tiene el paso {1}: pídele a quien administra los accesos que se lo asigne.")
                     .format(_nombre(usuario), _etiqueta(vista)))
    c = _costeo(costeo)
    if not c:
        frappe.throw(_("No existe el proyecto {0}.").format(costeo))
    if c.docstatus == 2 or c.costeo_status == "Cancelado":
        frappe.throw(_("El proyecto está cancelado."))
    if fecha and getdate(fecha) < getdate(nowdate()):
        frappe.throw(_("La fecha límite ya pasó."))
    lote = (lote or "").strip() if vista in CON_LOTE else ""
    mensaje = (mensaje or "").strip()
    if frappe.db.exists("ToDo", {"reference_type": "Costeo", "reference_name": costeo, "status": ABIERTO, "encargo_yelke": 1,
                                 "vista_yelke": vista if vista else ["is", "not set"], "lote_yelke": lote or ["is", "not set"],
                                 "allocated_to": usuario}):
        frappe.throw(_("{0} ya tiene esa asignación abierta en este proyecto.").format(_nombre(usuario)))

    titulo = _titulo(frappe._dict(vista_yelke=vista, lote_yelke=lote, costeo=costeo), c)
    todo = frappe.get_doc({
        "doctype": "ToDo", "allocated_to": usuario, "assigned_by": frappe.session.user,
        "reference_type": "Costeo", "reference_name": costeo, "date": fecha or None, "priority": "Medium",
        "description": f"<b>{frappe.utils.escape_html(titulo)}</b>" + (f"<br>{frappe.utils.escape_html(mensaje)}" if mensaje else ""),
        "encargo_yelke": 1, "vista_yelke": vista, "lote_yelke": lote, "mensaje_yelke": mensaje,
    })
    frappe.flags.encargo_yelke_api = True
    try:
        todo.insert(ignore_permissions=True)
    finally:
        frappe.flags.encargo_yelke_api = False
    if not fecha:  # el ToDo trae "hoy" por omisión: sin fecha límite, sin fecha
        frappe.db.set_value("ToDo", todo.name, "date", None, update_modified=False)

    texto = mensaje
    if fecha:
        texto = (texto + "\n" if texto else "") + _("Fecha límite: {0}").format(formatdate(fecha))
    _avisar([usuario], _("{0} te asignó: {1}").format(_nombre(frappe.session.user), titulo), "Costeo", costeo,
            mensaje=texto, ruta=_ruta_aviso(costeo, vista, lote), boton=_("Abrir la asignación"))
    revisar(costeo)  # marca de una vez si el paso ya tiene algo pendiente
    return {"name": todo.name}


@frappe.whitelist()
def crear_proyecto(titulo: str, cliente: str, usuario: str, compania: str = None, mensaje: str = None, fecha: str = None,
                   cliente_nuevo: str = None) -> dict:
    """Proyecto nuevo encargado: crea el costeo en borrador y el encargo de Costear.
    `cliente_nuevo`: el nombre de un cliente que aún no está dado de alta; se da de
    alta antes de cotizar (Costeo.before_submit)."""
    if not _puede_encargar("costear"):
        frappe.throw(_("No puedes asignar proyectos nuevos."), frappe.PermissionError)
    titulo = (titulo or "").strip()
    cliente_nuevo = (cliente_nuevo or "").strip().upper() if not cliente else ""
    if not titulo or not (cliente or cliente_nuevo):
        frappe.throw(_("Escribe el nombre del proyecto y elige el cliente."))
    from costeo_yelke.api.costeo_api import get_company_defaults

    compania = compania or frappe.defaults.get_user_default("Company")
    # Los almacenes y el centro de costos de la compañía, como al crearlo en pantalla.
    defaults = {k: v for k, v in (get_company_defaults(compania) or {}).items() if v} if compania else {}
    doc = frappe.get_doc({"doctype": "Costeo", "titulo": titulo, "cliente": cliente or None,
                          "cliente_nuevo": cliente_nuevo, "fecha": nowdate(),
                          "compañia": compania, **defaults})
    doc.insert()
    r = crear(doc.name, "costear", usuario, mensaje=mensaje, fecha=fecha)
    return {"costeo": doc.name, "encargo": r["name"]}


@frappe.whitelist()
def get_del_proyecto(costeo: str) -> dict:
    """Encargos del proyecto (abiertos y los cerrados de los últimos días), revisados."""
    if not _hay_encargos():
        return {"encargos": []}
    revisar(costeo)
    abiertos = frappe.get_all("ToDo", filters={"reference_type": "Costeo", "reference_name": costeo, "encargo_yelke": 1,
                                               "status": ABIERTO}, fields=_CAMPOS)
    cerrados = frappe.get_all("ToDo", filters={"reference_type": "Costeo", "reference_name": costeo, "encargo_yelke": 1,
                                               "status": ["!=", ABIERTO]}, fields=_CAMPOS, order_by="cerrado_en_yelke desc",
                              limit=20)
    return {"encargos": _orden(_filas(abiertos + cerrados))}


@frappe.whitelist()
def get_mios(company: str = None) -> dict:
    """Lo que me asignaron y lo que asigné (abiertas y cerradas de los últimos días)."""
    if not _hay_encargos():
        return {"para_mi": [], "encargue": []}
    yo = frappe.session.user
    for costeo in set(frappe.get_all("ToDo", filters={"status": ABIERTO, "encargo_yelke": 1, "reference_type": "Costeo",
                                                      "allocated_to": yo}, pluck="reference_name")):
        revisar(costeo)
    para_mi = _filas(_consulta({"allocated_to": yo}, company))
    encargue = _filas([e for e in _consulta({"assigned_by": yo}, company) if e.allocated_to != yo])
    return {"para_mi": _orden(para_mi), "encargue": _orden(encargue)}


def _ve_equipo():
    return puede_ver_panel_direccion() or _pase_libre()


@frappe.whitelist()
def get_cuenta() -> dict:
    """Para el menú: cuántos encargos abiertos tengo y si veo los del equipo."""
    if not _hay_encargos():
        return {"para_mi": 0, "ve_equipo": False}
    n = frappe.db.count("ToDo", {"status": ABIERTO, "encargo_yelke": 1, "allocated_to": frappe.session.user})
    return {"para_mi": n, "ve_equipo": _ve_equipo()}


@frappe.whitelist()
def get_por_proyecto(costeos) -> dict:
    """Lista de proyectos: los encargos abiertos de cada uno, en corto."""
    import json

    costeos = json.loads(costeos) if isinstance(costeos, str) else (costeos or [])
    if not costeos or not _hay_encargos():
        return {}
    filas = _filas(frappe.get_all("ToDo", filters={"reference_type": "Costeo", "reference_name": ["in", costeos[:300]],
                                                   "status": ABIERTO, "encargo_yelke": 1}, fields=_CAMPOS))
    out = {}
    for f in _orden(filas):
        out.setdefault(f["costeo"], []).append({k: f[k] for k in ("etiqueta", "vista", "lote", "para_nombre", "vencido", "vence_hoy", "fecha")})
    return out


@frappe.whitelist()
def get_equipo(company: str = None) -> dict:
    """Panel de Dirección: los encargos de todo el equipo."""
    if not _ve_equipo():
        frappe.throw(_("Solo Dirección ve las asignaciones de todo el equipo."), frappe.PermissionError)
    if not _hay_encargos():
        return {"encargos": []}
    return {"encargos": _orden(_filas(_consulta({}, company)))}


@frappe.whitelist()
def get_por_asignar(company: str = None) -> dict:
    """Panel de Dirección › Por asignar: todo lo que ya se puede hacer en los proyectos
    activos, por proyecto, paso y lote, con quién lo tiene asignado.

    Son los pendientes de Mi panel (api/mi_panel) de TODOS los pasos, no solo los de
    quien consulta, incluidos los que todavía no tienen documento ("Lote 1: faltan las
    órdenes de compra"). Así Dirección ve lo que ya pasó al siguiente paso y nadie ha
    empezado, y lo asigna. Una asignación del paso sin lote cubre todos sus lotes."""
    if not _ve_equipo():
        frappe.throw(_("Solo Dirección ve lo que falta por asignar."), frappe.PermissionError)
    from costeo_yelke.api import mi_panel

    cs = mi_panel._activos(company)
    grupos = {}
    for vista, fn in mi_panel.SECCIONES.items():
        try:
            filas = fn(cs)
        except Exception:
            frappe.log_error(title=f"Por asignar: sección {vista}")
            continue
        for f in filas:
            if f["costeo"] not in cs:
                continue
            lote = (f.get("lote") or "") if vista in CON_LOTE else ""
            g = grupos.setdefault((f["costeo"], vista, lote), {
                "costeo": f["costeo"], "proyecto": f["proyecto"], "cliente": f["cliente"], "vista": vista,
                "etiqueta": _etiqueta(vista), "lote": lote, "ruta": f["ruta"], "fecha": f["fecha"],
                "sin_documento": False, "pendientes": [], "asignado": []})
            g["pendientes"].append({"titulo": f["titulo"], "detalle": f["detalle"], "ruta": f["ruta"],
                                    "sin_documento": bool(f.get("sin_documento"))})
            g["sin_documento"] = g["sin_documento"] or bool(f.get("sin_documento"))
            g["fecha"] = max(g["fecha"], f["fecha"])

    if grupos and _hay_encargos():
        for e in frappe.get_all("ToDo", filters={"reference_type": "Costeo", "reference_name": ["in", list(cs)],
                                                 "status": ABIERTO, "encargo_yelke": 1},
                                fields=["name", "allocated_to", "reference_name", "vista_yelke", "lote_yelke", "creation"]):
            for (costeo, vista, lote), g in grupos.items():
                if costeo != e.reference_name:
                    continue
                if (e.vista_yelke or "") in (vista, GENERAL) and (not e.lote_yelke or e.lote_yelke == lote):
                    g["asignado"].append({"name": e.name, "usuario": e.allocated_to, "nombre": _nombre(e.allocated_to),
                                          "desde": str(e.creation), "general": not e.vista_yelke,
                                          "todos_los_lotes": bool(lote) and not e.lote_yelke})

    orden = {v: i for i, v in enumerate(ENCARGABLES)}
    out = sorted(grupos.values(), key=lambda g: (bool(g["asignado"]), g["proyecto"], orden.get(g["vista"], 99), g["lote"]))
    return {"grupos": out, "sin_asignar": sum(1 for g in out if not g["asignado"])}


@frappe.whitelist()
def marcar_listo(name: str, nota: str = None) -> dict:
    e = _encargo(name)
    _exigir_encargado(e)
    _cerrar(e, MANUAL, (nota or "").strip())
    c = _costeo(e.costeo)
    if c and frappe.session.user != e.assigned_by:
        _avisar_terminado(e, c, nota=(nota or "").strip())
    return {"ok": True}


@frappe.whitelist()
def regresar(name: str, motivo: str) -> dict:
    """La persona no puede o no le toca: lo regresa a quien lo encargó."""
    e = _encargo(name)
    _exigir_encargado(e)
    motivo = (motivo or "").strip()
    if not motivo:
        frappe.throw(_("Escribe por qué lo regresas."))
    _cerrar(e, REGRESADO, motivo, estado="Cancelled")
    _avisar([e.assigned_by], _("{0} regresó la asignación: {1}").format(_nombre(e.allocated_to), _titulo(e)), "Costeo", e.costeo,
            mensaje=motivo, ruta=_ruta_aviso(e.costeo, e.vista_yelke, e.lote_yelke, {"encargar": e.vista_yelke or "general"}),
            boton=_("Asignarla a alguien más"))
    return {"ok": True}


@frappe.whitelist()
def quitar(name: str) -> dict:
    e = _encargo(name)
    _exigir_quien_encargo(e)
    _cerrar(e, QUITADO, _("Lo quitó {0}.").format(_nombre(frappe.session.user)), estado="Cancelled")
    _avisar([e.allocated_to], _("Te quitaron la asignación: {0}").format(_titulo(e)), "Costeo", e.costeo,
            ruta=_ruta_aviso(e.costeo), correo=False)
    return {"ok": True}


@frappe.whitelist()
def reasignar(name: str, usuario: str) -> dict:
    e = _encargo(name)
    _exigir_quien_encargo(e)
    if usuario == e.allocated_to:
        return {"name": e.name}
    r = crear(e.costeo, e.vista_yelke or GENERAL, usuario, mensaje=e.mensaje_yelke, fecha=str(e.date) if e.date else None,
              lote=e.lote_yelke)
    _cerrar(e, QUITADO, _("Se reasignó a {0}.").format(_nombre(usuario)), estado="Cancelled")
    _avisar([e.allocated_to], _("Se reasignó a {0}: {1}").format(_nombre(usuario), _titulo(e)), "Costeo", e.costeo,
            ruta=_ruta_aviso(e.costeo), correo=False)
    return r


@frappe.whitelist()
def recordar(name: str) -> dict:
    e = _encargo(name)
    _exigir_quien_encargo(e)
    _avisar([e.allocated_to], _("Recordatorio de {0}: {1}").format(_nombre(frappe.session.user), _titulo(e)), "Costeo",
            e.costeo, mensaje=e.mensaje_yelke or "", ruta=_ruta_aviso(e.costeo, e.vista_yelke, e.lote_yelke),
            boton=_("Abrir la asignación"))
    return {"ok": True}


# ─────────────────────────────────────────────────────────────────────────────
# Comentarios y actividad
# ─────────────────────────────────────────────────────────────────────────────

def avisar_comentario(costeo, texto):
    """Un comentario en el proyecto le llega a la contraparte de cada encargo abierto
    de quien comenta (encargado ↔ quien encargó)."""
    if not costeo or not _hay_encargos():
        return
    yo = frappe.session.user
    destino = set()
    for e in frappe.get_all("ToDo", filters={"reference_type": "Costeo", "reference_name": costeo, "status": ABIERTO,
                                             "encargo_yelke": 1}, fields=["allocated_to", "assigned_by"]):
        if e.allocated_to == yo:
            destino.add(e.assigned_by)
        elif e.assigned_by == yo:
            destino.add(e.allocated_to)
    if destino:
        c = _costeo(costeo) or {}
        _avisar(list(destino), _("{0} comentó en {1}").format(_nombre(yo), c.get("titulo") or costeo), "Costeo", costeo,
                mensaje=texto, ruta=_ruta_aviso(costeo), correo=False)


def eventos_actividad(costeo):
    """Para la línea de tiempo del proyecto (api/actividad.get_actividad)."""
    if not _hay_encargos():
        return []
    out = []
    for e in frappe.get_all("ToDo", filters={"reference_type": "Costeo", "reference_name": costeo, "encargo_yelke": 1},
                            fields=_CAMPOS):
        paso = (_etiqueta(e.vista_yelke) + (f" · {e.lote_yelke}" if e.lote_yelke else "")) if e.vista_yelke else _("el proyecto")
        out.append({"tipo": "encargo", "usuario": e.assigned_by, "en": e.creation,
                    "texto": _("le asignó {0} a {1}").format(paso, _nombre(e.allocated_to)), "cita": e.mensaje_yelke or None})
        if e.status != ABIERTO and e.cerrado_en_yelke:
            texto, usuario = {
                AUTOMATICO: (_("terminó la asignación de {0} (se marcó sola)"), e.allocated_to),
                MANUAL: (_("marcó como hecha la asignación de {0}"), e.allocated_to),
                REGRESADO: (_("regresó la asignación de {0}"), e.allocated_to),
            }.get(e.cierre_yelke, (_("quitó la asignación de {0}"), e.assigned_by))
            tipo = {AUTOMATICO: "validado", MANUAL: "validado", REGRESADO: "devuelto"}.get(e.cierre_yelke, "info")
            out.append({"tipo": tipo, "usuario": usuario,
                        "en": e.cerrado_en_yelke, "texto": texto.format(paso),
                        "cita": e.nota_cierre_yelke if e.cierre_yelke != AUTOMATICO else None})
    return out


# ── Fotos y adjuntos de la asignación ──────────────────────────────────────────
# Viven como File ligados al ToDo. Los ven y agregan quien asignó, el responsable y
# Dirección; se suben por aquí (no por upload_file) para no depender de los permisos
# del ToDo en el Escritorio.
IMAGENES = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".heif", ".bmp")


def _exigir_acceso_archivos(name):
    e = _encargo(name)
    if frappe.session.user not in (e.allocated_to, e.assigned_by) and not _ve_equipo():
        frappe.throw(_("No tienes acceso a esta asignación."), frappe.PermissionError)
    return e


@frappe.whitelist()
def get_archivos(name: str) -> list:
    _exigir_acceso_archivos(name)
    archivos = frappe.get_all("File", filters={"attached_to_doctype": "ToDo", "attached_to_name": name},
                              fields=["name", "file_name", "file_url", "owner", "creation"], order_by="creation asc")
    for a in archivos:
        a["es_foto"] = (a.file_name or a.file_url or "").lower().endswith(IMAGENES)
    return archivos


@frappe.whitelist()
def subir_archivo(name: str) -> dict:
    _exigir_acceso_archivos(name)
    f = frappe.request.files.get("file") if frappe.request else None
    if not f:
        frappe.throw(_("No llegó ningún archivo."))
    doc = frappe.get_doc({"doctype": "File", "file_name": f.filename, "content": f.stream.read(), "is_private": 1,
                          "attached_to_doctype": "ToDo", "attached_to_name": name})
    doc.insert(ignore_permissions=True)
    return {"name": doc.name, "file_url": doc.file_url}


@frappe.whitelist()
def quitar_archivo(name: str, archivo: str) -> dict:
    e = _exigir_acceso_archivos(name)
    f = frappe.db.get_value("File", archivo, ["attached_to_doctype", "attached_to_name", "owner"], as_dict=True)
    if not f or f.attached_to_doctype != "ToDo" or f.attached_to_name != name:
        frappe.throw(_("Ese archivo no es de esta asignación."))
    if frappe.session.user not in (f.owner, e.assigned_by) and not _ve_equipo():
        frappe.throw(_("Solo quien lo subió o quien asignó puede quitarlo."), frappe.PermissionError)
    frappe.delete_doc("File", archivo, ignore_permissions=True)
    return {"ok": True}
