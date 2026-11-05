// App de Dirección en el celular (api/pwa.py): service worker, avisos del teléfono y el
// numerito del ícono. Solo Dirección (el servidor pone el manifest solo para ella).
import { reactive } from "vue";
import { call } from "@/utils/frappe.js";

const SW = "/api/method/costeo_yelke.api.pwa.service_worker";

export const pwa = reactive({
  soportado: typeof window !== "undefined" && "serviceWorker" in navigator && "PushManager" in window && "Notification" in window,
  instalada: typeof window !== "undefined" && (window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true),
  ios: typeof navigator !== "undefined" && /iphone|ipad|ipod/i.test(navigator.userAgent),
  puede: false,
  activa: false,   // este celular ya recibe avisos
  ocupado: false,
  error: "",
});

let registro = null;
let llave = null;

function aBytes(b64) {
  const s = (b64 + "=".repeat((4 - (b64.length % 4)) % 4)).replace(/-/g, "+").replace(/_/g, "/");
  return Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
}

/** Registra el service worker y averigua si este celular ya tiene los avisos. */
export async function prepararPwa() {
  if (!("serviceWorker" in navigator)) return;
  try {
    const cfg = await call("costeo_yelke.api.pwa.get_config");
    pwa.puede = !!cfg?.puede;
    llave = cfg?.llave || null;
    if (!pwa.puede) return;
    registro = await navigator.serviceWorker.register(SW, { scope: "/costeo-yelke/" });
    const sub = pwa.soportado ? await registro.pushManager.getSubscription() : null;
    pwa.activa = !!sub && Notification.permission === "granted";
  } catch { /* sin PWA: la app funciona igual */ }
}

/** Pide permiso (tiene que ser con un toque del usuario) y suscribe este celular. */
export async function activarAvisos() {
  pwa.error = "";
  if (!pwa.soportado || !llave) { pwa.error = "Este navegador no permite avisos."; return; }
  pwa.ocupado = true;
  try {
    const permiso = await Notification.requestPermission();
    if (permiso !== "granted") { pwa.error = "No se dio permiso de notificaciones. Actívalo en los ajustes del celular."; return; }
    registro = registro || await navigator.serviceWorker.register(SW, { scope: "/costeo-yelke/" });
    await navigator.serviceWorker.ready;
    const sub = (await registro.pushManager.getSubscription())
      || await registro.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: aBytes(llave) });
    const j = sub.toJSON();
    await call("costeo_yelke.api.pwa.suscribir", {
      endpoint: j.endpoint, p256dh: j.keys.p256dh, auth: j.keys.auth, dispositivo: navigator.userAgent,
    });
    pwa.activa = true;
  } catch (e) {
    pwa.error = e?.message || "No se pudieron activar los avisos.";
  } finally { pwa.ocupado = false; }
}

/** El número sobre el ícono de la app (avisos sin leer). */
export function ponerNumero(n) {
  try {
    if (!("setAppBadge" in navigator)) return;
    if (n > 0) navigator.setAppBadge(n); else navigator.clearAppBadge();
  } catch { /* sin soporte */ }
}
