"""La app en el celular de Juan (PWA): ícono en la pantalla de inicio, notificaciones en
el teléfono y el numerito sobre el ícono.

- `manifest` y `service_worker` se sirven desde aquí (no como archivos de /assets): el
  service worker necesita la cabecera Service-Worker-Allowed para controlar
  /costeo-yelke/, y el manifest abre directo el panel de Dirección.
- Web Push sin dependencias nuevas: cifrado aes128gcm (RFC 8291) con `cryptography` y la
  firma VAPID (RFC 8292) con PyJWT, las dos ya vienen con Frappe.
- Cada Notification Log nuevo (hook after_insert) de alguien que activó los avisos en su
  celular se manda como notificación del teléfono, con el número de avisos sin leer para
  el ícono. Solo Dirección puede activarlos (pantalla de Dirección).
"""
import base64
import json
import os
from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.utils import now_datetime, strip_html
from werkzeug.wrappers import Response

from costeo_yelke.roles import ROL_DIRECTOR

ASUNTO_VAPID = "mailto:notificaciones@yelke.com.mx"
INICIO = "/costeo-yelke/direccion"
ICONO = "/assets/costeo_yelke/images/pwa-192.png"


def _b64u(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _b64u_dec(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


# ── Llaves VAPID: se generan una vez por sitio y se guardan en los defaults globales ──
def _llave_privada():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    pem = frappe.db.get_global("pwa_vapid_privada")
    if not pem:
        llave = ec.generate_private_key(ec.SECP256R1())
        pem = llave.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                  serialization.NoEncryption()).decode()
        frappe.db.set_global("pwa_vapid_privada", pem)
        frappe.db.commit()
    return serialization.load_pem_private_key(pem.encode(), password=None)


def _llave_publica_b64():
    from cryptography.hazmat.primitives import serialization

    pub = _llave_privada().public_key().public_bytes(serialization.Encoding.X962,
                                                     serialization.PublicFormat.UncompressedPoint)
    return _b64u(pub)


def es_direccion(user=None):
    """La app del celular es de Dirección (Juan): el rol Director, no el pase libre."""
    return ROL_DIRECTOR in frappe.get_roles(user)


# ── Lo que pide el celular ────────────────────────────────────────────────────────
@frappe.whitelist()
def manifest():
    datos = {
        "name": "Yelke · Dirección", "short_name": "Yelke", "lang": "es-MX",
        "start_url": INICIO, "scope": "/costeo-yelke/", "display": "standalone",
        "background_color": "#ffffff", "theme_color": "#ff6c15",
        "icons": [
            {"src": "/assets/costeo_yelke/images/pwa-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "/assets/costeo_yelke/images/pwa-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": "/assets/costeo_yelke/images/pwa-512-maskable.png", "sizes": "512x512", "type": "image/png",
             "purpose": "maskable"},
        ],
    }
    return Response(json.dumps(datos, ensure_ascii=False), mimetype="application/manifest+json",
                    headers={"Cache-Control": "no-cache"})


_SW = """
// Service worker de la app de Dirección (api/pwa.py). Sin caché: solo avisos.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
self.addEventListener("push", (e) => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (err) { d = { body: e.data && e.data.text() }; }
  const tareas = [self.registration.showNotification(d.title || "Yelke", {
    body: d.body || "", tag: d.tag || undefined, renotify: !!d.tag,
    icon: "%(icono)s", badge: "/assets/costeo_yelke/images/pwa-badge.png",
    data: { url: d.url || "%(inicio)s" },
  })];
  if (typeof d.badge === "number" && self.navigator.setAppBadge) {
    tareas.push(d.badge > 0 ? self.navigator.setAppBadge(d.badge) : self.navigator.clearAppBadge());
  }
  e.waitUntil(Promise.all(tareas).catch(() => {}));
});
self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || "%(inicio)s";
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((ventanas) => {
    for (const v of ventanas) {
      if ("focus" in v) { if ("navigate" in v) v.navigate(url); return v.focus(); }
    }
    return self.clients.openWindow(url);
  }));
});
"""


@frappe.whitelist()
def service_worker():
    return Response(_SW % {"icono": ICONO, "inicio": INICIO}, mimetype="application/javascript",
                    headers={"Service-Worker-Allowed": "/costeo-yelke/", "Cache-Control": "no-cache"})


@frappe.whitelist()
def get_config() -> dict:
    """Para la pantalla: si este usuario puede activar los avisos y la llave pública."""
    puede = es_direccion()
    return {"puede": puede, "llave": _llave_publica_b64() if puede else None,
            "suscripciones": frappe.db.count("Suscripcion Push Yelke", {"usuario": frappe.session.user})}


@frappe.whitelist(methods=["POST"])
def suscribir(endpoint: str, p256dh: str, auth: str, dispositivo: str = None) -> dict:
    if not es_direccion():
        frappe.throw(_("Los avisos en el celular son para Dirección."), frappe.PermissionError)
    if not (endpoint or "").startswith("https://"):
        frappe.throw(_("Suscripción no válida."))
    existente = frappe.db.get_value("Suscripcion Push Yelke", {"endpoint": endpoint}, "name")
    datos = {"usuario": frappe.session.user, "p256dh": p256dh, "auth": auth, "dispositivo": (dispositivo or "")[:140]}
    if existente:
        frappe.db.set_value("Suscripcion Push Yelke", existente, datos)
    else:
        frappe.get_doc({"doctype": "Suscripcion Push Yelke", "endpoint": endpoint, **datos}).insert(ignore_permissions=True)
    return {"ok": True}


@frappe.whitelist(methods=["POST"])
def desuscribir(endpoint: str) -> dict:
    for n in frappe.get_all("Suscripcion Push Yelke", filters={"endpoint": endpoint, "usuario": frappe.session.user},
                            pluck="name"):
        frappe.delete_doc("Suscripcion Push Yelke", n, ignore_permissions=True, force=True)
    return {"ok": True}


@frappe.whitelist()
def sin_leer() -> int:
    """El número del ícono: avisos sin leer de quien pregunta."""
    return frappe.db.count("Notification Log", {"for_user": frappe.session.user, "read": 0})


# ── Envío ─────────────────────────────────────────────────────────────────────────
def al_crear_aviso(doc, method=None):
    """after_insert de Notification Log: si su destinatario activó los avisos en el
    celular, se manda después del commit. Un solo envío por persona y documento a la
    vez (job_id): si la misma acción genera dos avisos, sale el último (ver
    aprobaciones._reemplazar_aviso_reciente)."""
    if not doc.for_user or not frappe.db.exists("Suscripcion Push Yelke", {"usuario": doc.for_user}):
        return
    clave = f"{doc.document_type or ''}:{doc.document_name or doc.name}"
    frappe.enqueue("costeo_yelke.api.pwa.enviar_ultimo_aviso", queue="short", enqueue_after_commit=True,
                   job_id=f"push-yelke::{doc.for_user}::{clave}", deduplicate=True,
                   user=doc.for_user, document_type=doc.document_type, document_name=doc.document_name, log=doc.name)


def enviar_ultimo_aviso(user, document_type=None, document_name=None, log=None):
    filtros = {"for_user": user, "read": 0}
    if document_type and document_name:
        filtros.update({"document_type": document_type, "document_name": document_name})
    else:
        filtros["name"] = log
    ultimo = frappe.get_all("Notification Log", filters=filtros, fields=["subject", "email_content", "link"],
                            order_by="creation desc", limit=1)
    if not ultimo:
        return
    a = ultimo[0]
    titulo = strip_html(a.subject or "").strip() or "Yelke"
    cuerpo = strip_html(a.email_content or "").strip()
    url = a.link if (a.link or "").startswith("/costeo-yelke") else INICIO
    enviar(user, titulo, cuerpo[:240], url=url, tag=f"{document_type or ''}:{document_name or log}")


def enviar(user, titulo, cuerpo="", url=INICIO, tag=None):
    """Notificación al celular de `user` (a cada navegador suscrito)."""
    import requests

    datos = json.dumps({"title": titulo[:120], "body": cuerpo, "url": url, "tag": tag,
                        "badge": frappe.db.count("Notification Log", {"for_user": user, "read": 0})},
                       ensure_ascii=False).encode()
    for s in frappe.get_all("Suscripcion Push Yelke", filters={"usuario": user},
                            fields=["name", "endpoint", "p256dh", "auth"]):
        try:
            r = requests.post(s.endpoint, data=_cifrar(s.p256dh, s.auth, datos), timeout=10, headers={
                "Authorization": _vapid(s.endpoint), "Content-Encoding": "aes128gcm",
                "Content-Type": "application/octet-stream", "TTL": "86400", "Urgency": "high"})
        except Exception:
            frappe.log_error(title="Aviso al celular: no se pudo enviar")
            continue
        if r.status_code in (404, 410):
            # El navegador ya no existe (se desinstaló o se quitaron los permisos).
            frappe.delete_doc("Suscripcion Push Yelke", s.name, ignore_permissions=True, force=True)
        elif r.status_code >= 400:
            frappe.log_error(title="Aviso al celular rechazado", message=f"{r.status_code} {r.text[:500]}")
        else:
            frappe.db.set_value("Suscripcion Push Yelke", s.name, "ultimo_envio", now_datetime(), update_modified=False)
    frappe.db.commit()


def _vapid(endpoint):
    import time

    import jwt

    destino = urlparse(endpoint)
    token = jwt.encode({"aud": f"{destino.scheme}://{destino.netloc}", "exp": int(time.time()) + 12 * 3600,
                        "sub": ASUNTO_VAPID}, _llave_privada(), algorithm="ES256")
    return f"vapid t={token}, k={_llave_publica_b64()}"


def _cifrar(p256dh, auth, datos):
    """RFC 8291 (aes128gcm): lo único que el servicio de avisos del teléfono acepta."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF

    def hkdf(sal, info, largo, ikm):
        return HKDF(algorithm=hashes.SHA256(), length=largo, salt=sal, info=info).derive(ikm)

    ua_pub = _b64u_dec(p256dh)
    secreto_auth = _b64u_dec(auth)
    propia = ec.generate_private_key(ec.SECP256R1())
    as_pub = propia.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    compartido = propia.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_pub))
    ikm = hkdf(secreto_auth, b"WebPush: info\x00" + ua_pub + as_pub, 32, compartido)
    sal = os.urandom(16)
    cek = hkdf(sal, b"Content-Encoding: aes128gcm\x00", 16, ikm)
    nonce = hkdf(sal, b"Content-Encoding: nonce\x00", 12, ikm)
    cifrado = AESGCM(cek).encrypt(nonce, datos + b"\x02", None)
    return sal + (4096).to_bytes(4, "big") + bytes([len(as_pub)]) + as_pub + cifrado
