"""Reglas de captura: que clientes, proveedores, direcciones, contactos, cuentas y folios
queden escritos de una sola forma, se capturen en la app o en el Escritorio de ERPNext
(docs/plan-accesos-ejecucion.md, fase 1).

Dos niveles:
- **Normalizar** (siempre, también en importaciones y procesos automáticos): espacios,
  mayúsculas, estado oficial, teléfono a `442 467 8939`, correo en minúsculas. Solo se
  corrige lo que tiene una sola forma correcta.
- **Rechazar** (solo cuando lo captura una persona, ver confirmaciones._captura_de_persona):
  lo que no se puede adivinar -- un estado que no existe, un CP de 4 dígitos, un correo
  sin @. Un correo entrante, una importación o un patch nunca se detienen por esto.

Las reglas mexicanas (estado, CP, teléfono a 10 dígitos) solo aplican con país México.
"""
import re
import unicodedata

import frappe
from frappe import _

from costeo_yelke.api.confirmaciones import _captura_de_persona

# Las 32 entidades, como se escriben en la app (mayúsculas, con acentos).
ESTADOS_MX = (
    "AGUASCALIENTES", "BAJA CALIFORNIA", "BAJA CALIFORNIA SUR", "CAMPECHE", "CHIAPAS", "CHIHUAHUA",
    "CIUDAD DE MÉXICO", "COAHUILA", "COLIMA", "DURANGO", "ESTADO DE MÉXICO", "GUANAJUATO", "GUERRERO",
    "HIDALGO", "JALISCO", "MICHOACÁN", "MORELOS", "NAYARIT", "NUEVO LEÓN", "OAXACA", "PUEBLA", "QUERÉTARO",
    "QUINTANA ROO", "SAN LUIS POTOSÍ", "SINALOA", "SONORA", "TABASCO", "TAMAULIPAS", "TLAXCALA", "VERACRUZ",
    "YUCATÁN", "ZACATECAS",
)
# Formas en que llegan escritos (ya sin acentos ni puntuación, ver _clave).
_ALIAS = {
    "AGS": "AGUASCALIENTES", "BC": "BAJA CALIFORNIA", "BCN": "BAJA CALIFORNIA", "BCS": "BAJA CALIFORNIA SUR",
    "CAMP": "CAMPECHE", "CHIS": "CHIAPAS", "CHIH": "CHIHUAHUA",
    "CDMX": "CIUDAD DE MÉXICO", "CD MX": "CIUDAD DE MÉXICO", "DF": "CIUDAD DE MÉXICO",
    "DISTRITO FEDERAL": "CIUDAD DE MÉXICO", "CIUDAD DE MEXICO": "CIUDAD DE MÉXICO", "CD DE MEXICO": "CIUDAD DE MÉXICO",
    "MEXICO DF": "CIUDAD DE MÉXICO",
    "COAH": "COAHUILA", "COAHUILA DE ZARAGOZA": "COAHUILA", "COL": "COLIMA", "DGO": "DURANGO",
    "EDO DE MEXICO": "ESTADO DE MÉXICO", "EDO MEX": "ESTADO DE MÉXICO", "EDOMEX": "ESTADO DE MÉXICO",
    "EDO MEXICO": "ESTADO DE MÉXICO", "ESTADO DE MEXICO": "ESTADO DE MÉXICO", "MEX": "ESTADO DE MÉXICO",
    "MEXICO": "ESTADO DE MÉXICO",
    "GTO": "GUANAJUATO", "GRO": "GUERRERO", "HGO": "HIDALGO", "JAL": "JALISCO",
    "MICH": "MICHOACÁN", "MICHOACAN": "MICHOACÁN", "MICHOACAN DE OCAMPO": "MICHOACÁN",
    "MOR": "MORELOS", "NAY": "NAYARIT", "NL": "NUEVO LEÓN", "NUEVO LEON": "NUEVO LEÓN", "OAX": "OAXACA",
    "PUE": "PUEBLA", "QRO": "QUERÉTARO", "QUERETARO": "QUERÉTARO", "QUERETARO DE ARTEAGA": "QUERÉTARO",
    "QROO": "QUINTANA ROO", "Q ROO": "QUINTANA ROO", "SLP": "SAN LUIS POTOSÍ", "SAN LUIS POTOSI": "SAN LUIS POTOSÍ",
    "SIN": "SINALOA", "SON": "SONORA", "TAB": "TABASCO", "TAMPS": "TAMAULIPAS", "TAMS": "TAMAULIPAS",
    "TLAX": "TLAXCALA", "VER": "VERACRUZ", "VERACRUZ DE IGNACIO DE LA LLAVE": "VERACRUZ",
    "YUC": "YUCATÁN", "YUCATAN": "YUCATÁN", "ZAC": "ZACATECAS",
}
RFC_GENERICOS = ("XAXX010101000", "XEXX010101000")


class Invalido(ValueError):
    """Un valor que no se puede corregir solo; el mensaje es para la persona."""


# ── Funciones puras ──────────────────────────────────────────────────────────
def _sin_acentos(v):
    return "".join(c for c in unicodedata.normalize("NFD", v) if unicodedata.category(c) != "Mn")


def _clave(v):
    """«Edo. de México» -> «EDO DE MEXICO» (para buscar alias); la Ñ se conserva."""
    v = (v or "").upper().replace("Ñ", "\0")
    v = _sin_acentos(v).replace("\0", "Ñ")
    return re.sub(r"\s+", " ", re.sub(r"[^A-ZÑ0-9 ]", " ", v)).strip()


def texto(v):
    """Espacios al inicio, al final y dobles fuera; MAYÚSCULAS con acentos y Ñ."""
    if not isinstance(v, str):
        return v
    return re.sub(r"\s+", " ", v).strip().upper()


def recortar(v):
    return re.sub(r"[ \t]+\n", "\n", v).strip() if isinstance(v, str) else v


_OFICIALES = {_clave(e): e for e in ESTADOS_MX}


def estado_mx(v):
    if not (v or "").strip():
        return ""
    k = _clave(v)
    if k in _OFICIALES:
        return _OFICIALES[k]
    if k in _ALIAS:
        return _ALIAS[k]
    # Siglas con puntos o espacios: «D.F.», «Q. Roo», «N.L.».
    junto = k.replace(" ", "")
    for alias, oficial in _ALIAS.items():
        if alias.replace(" ", "") == junto:
            return oficial
    raise Invalido(_("«{0}» no es un estado de México. Elige uno de la lista.").format(texto(v)))


def cp_mx(v):
    if not (v or "").strip():
        return ""
    d = re.sub(r"\D", "", v)
    if len(d) != 5:
        raise Invalido(_("El código postal «{0}» debe tener 5 dígitos.").format(v.strip()))
    return d


# Ciudades con clave de 2 dígitos: su número se escribe 2-4-4 (33 3122 4455).
_LADA_2 = ("33", "55", "56", "81")


def telefono_mx(v):
    """10 dígitos como `442 467 8939` (o `33 3122 4455` en Guadalajara, CDMX y
    Monterrey); quita +52 / 52 / 521. Conserva una extensión como `#12`: el campo de
    teléfono de ERPNext no acepta letras ("ext") y rechazaba guardar."""
    if not (v or "").strip():
        return ""
    partes = re.split(r"(?i)\s*(?:ext\.?|extensi[oó]n|x|#)\s*(?=\d)", v.strip(), maxsplit=1)
    # Extensión sin "ext": 10 dígitos y, separada por espacios, la extensión
    # («462 623 8480  4756»).
    m = re.fullmatch(r"\D*((?:\d\D*){10})\s+(\d{1,5})", partes[0]) if len(partes) == 1 else None
    if m and not re.sub(r"\D", "", m.group(1)).startswith("52"):
        partes = [m.group(1), m.group(2)]
    d = re.sub(r"\D", "", partes[0])
    if len(d) == 13 and d.startswith("521"):
        d = d[3:]
    elif len(d) == 12 and d.startswith("52"):
        d = d[2:]
    if len(d) != 10:
        raise Invalido(_("El teléfono «{0}» debe tener 10 dígitos (ej. 442 467 8939).").format(v.strip()))
    numero = f"{d[:2]} {d[2:6]} {d[6:]}" if d[:2] in _LADA_2 else f"{d[:3]} {d[3:6]} {d[6:]}"
    ext = re.sub(r"\D", "", partes[1]) if len(partes) > 1 else ""
    return f"{numero} #{ext}" if ext else numero


def telefono_libre(v):
    """Teléfono de otro país: solo espacios."""
    return re.sub(r"\s+", " ", v).strip() if isinstance(v, str) else v


def telefono(v):
    """Un número con lada de otro país («+1 …», «+34 …») se deja como viene; el resto es
    mexicano (con o sin +52)."""
    if isinstance(v, str) and v.strip().startswith("+") and not re.sub(r"\s", "", v).startswith("+52"):
        return telefono_libre(v)
    return telefono_mx(v)


CORREO = re.compile(r"[^@\s]+@[^@\s]+\.[a-z]{2,}")


def correo(v):
    if not (v or "").strip():
        return ""
    c = re.sub(r"\s", "", v).lower()
    if not CORREO.fullmatch(c):
        raise Invalido(_("El correo «{0}» no tiene un formato válido.").format(v.strip()))
    return c


def rfc(v):
    return re.sub(r"[\s\-.]", "", v or "").upper()


def clabe(v):
    d = re.sub(r"\D", "", v or "")
    if not d:
        return ""
    if len(d) != 18:
        raise Invalido(_("La CLABE debe tener 18 dígitos."))
    pesos = (3, 7, 1) * 6
    suma = sum((int(x) * pesos[i]) % 10 for i, x in enumerate(d[:17]))
    if (10 - suma % 10) % 10 != int(d[17]):
        raise Invalido(_("La CLABE «{0}» no es válida: el dígito verificador no coincide. Revísala.").format(d))
    return d


# ── Aplicar a un documento ───────────────────────────────────────────────────
def _aplicar(doc, objeto, campo, fn, errores):
    """Normaliza `objeto.campo` con `fn`; si no se puede, anota el error."""
    valor = objeto.get(campo)
    if not valor:
        return
    try:
        nuevo = fn(valor)
    except Invalido as e:
        errores.append(str(e))
        return
    if nuevo != valor:
        objeto.set(campo, nuevo)


def _rechazar(doc, errores):
    """Solo detiene la captura de una persona; en procesos del sistema se deja pasar."""
    if errores and _captura_de_persona(doc):
        frappe.throw("<br>".join(dict.fromkeys(errores)), title=_("Revisa los datos"))


def _es_mexico(pais):
    return (pais or "Mexico") in ("Mexico", "México", "MEXICO", "MÉXICO")


def parte(doc, method=None):
    """before_validate de Customer y Supplier."""
    for campo in ("customer_name", "supplier_name", "nombre_comercial"):
        if doc.get(campo):
            doc.set(campo, texto(doc.get(campo)))


def rfc_unico(doc, method=None):
    """validate de Customer y Supplier: otro registro con el mismo RFC (salvo genéricos)."""
    r = rfc(doc.get("tax_id"))
    if not r or r in RFC_GENERICOS or not _captura_de_persona(doc):
        return
    if not (doc.is_new() or doc.has_value_changed("tax_id")):
        return
    otro = frappe.db.get_value(doc.doctype, {"tax_id": r, "name": ["!=", doc.name or ""]},
                               ["name", "customer_name" if doc.doctype == "Customer" else "supplier_name"], as_dict=True)
    if otro:
        nombre = otro.get("customer_name") or otro.get("supplier_name") or otro.name
        quien = _("un cliente") if doc.doctype == "Customer" else _("un proveedor")
        frappe.throw(_("Ya existe {0} con el RFC {1}: {2}. Usa ese registro en lugar de crear otro.")
                     .format(quien, r, nombre), title=_("RFC duplicado"))


def direccion(doc, method=None):
    """before_validate de Address (los textos ya los pasa a mayúsculas uppercase_master)."""
    errores = []
    if not doc.get("country"):
        doc.country = "Mexico"
    if _es_mexico(doc.country):
        _aplicar(doc, doc, "state", estado_mx, errores)
        _aplicar(doc, doc, "pincode", cp_mx, errores)
        for campo in ("phone", "fax"):
            _aplicar(doc, doc, campo, telefono_mx, errores)
    else:
        for campo in ("phone", "fax"):
            _aplicar(doc, doc, campo, telefono_libre, errores)
    _aplicar(doc, doc, "email_id", correo, errores)
    _rechazar(doc, errores)


def direccion_ligada(doc, method=None):
    """validate de Address: toda dirección pertenece a un cliente, proveedor o la compañía."""
    if not _captura_de_persona(doc) or doc.get("is_your_company_address"):
        return
    if not any(l.link_doctype in ("Customer", "Supplier", "Company") and l.link_name for l in (doc.links or [])):
        frappe.throw(_("Liga la dirección a un cliente, proveedor o a la compañía (tabla «Ligas»)."),
                     title=_("Dirección sin dueño"))


def contacto(doc, method=None):
    """before_validate de Contact: correos y teléfonos, en los campos y en sus tablas."""
    errores = []
    tel = telefono
    _aplicar(doc, doc, "email_id", correo, errores)
    for fila in doc.get("email_ids") or []:
        _aplicar(doc, fila, "email_id", correo, errores)
    for campo in ("phone", "mobile_no"):
        _aplicar(doc, doc, campo, tel, errores)
    for fila in doc.get("phone_nos") or []:
        _aplicar(doc, fila, "phone", tel, errores)
    _rechazar(doc, errores)


def contacto_ligado(doc, method=None):
    """validate de Contact: los que captura una persona van ligados a un cliente o
    proveedor. Los del sistema (correo entrante, usuarios) no pasan por aquí."""
    if not _captura_de_persona(doc) or doc.get("user"):
        return
    if not any(l.link_doctype in ("Customer", "Supplier", "Lead", "Company") and l.link_name for l in (doc.links or [])):
        frappe.throw(_("Liga el contacto a un cliente o proveedor (tabla «Ligas»)."), title=_("Contacto sin dueño"))


def cuenta_bancaria(doc, method=None):
    """validate de Bank Account: dígito verificador de la CLABE."""
    errores = []
    _aplicar(doc, doc, "cuenta_clabe", clabe, errores)
    _rechazar(doc, errores)


def folio_oc_cliente(doc, method=None):
    """before_validate de Sales Order: la OC del cliente."""
    if doc.get("po_no"):
        doc.po_no = texto(doc.po_no)


def folio_proveedor(doc, method=None):
    """before_validate de Purchase Invoice: el folio de la factura del proveedor."""
    if doc.get("bill_no"):
        doc.bill_no = texto(doc.bill_no)


def articulo(doc, method=None):
    """before_validate de Item: la descripción sin espacios sobrantes al inicio y al final."""
    if doc.get("description"):
        doc.description = recortar(doc.description)


@frappe.whitelist()
def catalogo_estados():
    return list(ESTADOS_MX)
