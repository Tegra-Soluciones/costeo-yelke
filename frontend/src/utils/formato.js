// Formatos compartidos del panel de Dirección, las aprobaciones y la actividad.

export function dinero(n, moneda = "MXN") {
  if (n === null || n === undefined || n === "") return "";
  const v = Number(n) || 0;
  const txt = Math.abs(v).toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const signo = v < 0 ? "−" : "";
  return moneda && moneda !== "MXN" ? `${signo}${txt} ${moneda}` : `${signo}$${txt}`;
}

/** $2.61 M · $221 k · $1,120.00 -- para indicadores y celular. */
export function dineroCorto(n, moneda = "MXN") {
  const v = Number(n) || 0;
  const s = moneda && moneda !== "MXN" ? ` ${moneda}` : "";
  const p = moneda && moneda !== "MXN" ? "" : "$";
  if (Math.abs(v) >= 1e6) return `${p}${(v / 1e6).toFixed(2)} M${s}`;
  if (Math.abs(v) >= 1e4) return `${p}${Math.round(v / 1e3)} k${s}`;
  return dinero(v, moneda);
}

export function numero(n, decimales = 0) {
  return (Number(n) || 0).toLocaleString("es-MX", { maximumFractionDigits: decimales });
}

function aFecha(valor) {
  if (!valor) return null;
  if (valor instanceof Date) return valor;
  // "2026-10-19 07:30:00.123" (Frappe) -> ISO local
  return new Date(String(valor).replace(" ", "T"));
}

export function haceCuanto(valor) {
  const d = aFecha(valor);
  if (!d || isNaN(d)) return "";
  const s = Math.floor((Date.now() - d.getTime()) / 1000);
  if (s < 60) return "hace un momento";
  if (s < 3600) return `hace ${Math.floor(s / 60)} min`;
  if (s < 86400) return `hace ${Math.floor(s / 3600)} h`;
  const dias = Math.floor(s / 86400);
  return dias === 1 ? "hace 1 día" : `hace ${dias} días`;
}

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

/** 19-oct-2026 */
export function fecha(valor) {
  const d = aFecha(valor && String(valor).length === 10 ? `${valor} 00:00` : valor);
  if (!d || isNaN(d)) return "—";
  return `${d.getDate()}-${MESES[d.getMonth()]}-${d.getFullYear()}`;
}

/** 19-oct 07:30 */
export function fechaHora(valor) {
  const d = aFecha(valor);
  if (!d || isNaN(d)) return "";
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${d.getDate()}-${MESES[d.getMonth()]} ${hh}:${mm}`;
}

export function iniciales(nombre) {
  const partes = String(nombre || "?").replace(/@.*/, "").split(/[\s._-]+/).filter(Boolean);
  return ((partes[0]?.[0] || "?") + (partes[1]?.[0] || "")).toUpperCase();
}

const COLORES = [
  "bg-sky-100 text-sky-700", "bg-violet-100 text-violet-700", "bg-emerald-100 text-emerald-700",
  "bg-amber-100 text-amber-800", "bg-pink-100 text-pink-700", "bg-indigo-100 text-indigo-700",
];
export function colorAvatar(clave) {
  let h = 0;
  for (const c of String(clave || "")) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return COLORES[h % COLORES.length];
}

/** Pill del tipo de documento en la bandeja (mismo vocabulario que el mockup). */
export const TIPOS_DOC = {
  "oc-mp": { pill: "p-pill-now" },
  "oc-maq": { pill: "p-pill-fac" },
  cot: { pill: "p-pill-ok" },
  ov: { pill: "p-pill-ok" },
  fc: { pill: "p-pill-wait" },
  costeo: { pill: "p-pill-off" },
  precio: { pill: "p-pill-off" },
};
