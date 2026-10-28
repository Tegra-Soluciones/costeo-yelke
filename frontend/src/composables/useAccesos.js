// Accesos por vista del usuario (roles.VISTAS en el servidor; docs/plan-accesos-ejecucion.md).
// Se leen UNA vez por sesión y los comparten el menú, las rutas, el stepper del costeo y
// cada pantalla. Cada vista se tiene en "editar" (ve y captura) o "ver" (solo lectura).
//
// `simulado` es para "Ver como…" (pantalla de Accesos): reemplaza en la PANTALLA los
// accesos por los de otro usuario o perfil. El servidor sigue tratando a quien mira como
// lo que es.
import { reactive } from "vue";
import { call } from "@/utils/frappe.js";

const estado = reactive({
  cargado: false,
  accesos: {},      // {clave: "editar" | "ver"}
  mapa: {},         // {clave: {etiqueta, grupo, paso, rutas}}
  simulado: null,   // {etiqueta, accesos} mientras se usa "Ver como…"
  crudo: {},        // respuesta completa (puede_aprobar, vistas…) para useProduccion
});
let pendiente = null;

export function cargarAccesos() {
  if (estado.cargado) return Promise.resolve(estado.crudo);
  if (!pendiente) {
    pendiente = call("costeo_yelke.api.costeo_api.get_permisos_validacion_yelke")
      .then((r) => {
        Object.assign(estado, { accesos: r.accesos || {}, mapa: r.mapa_vistas || {}, crudo: r, cargado: true });
        return r;
      })
      .catch(() => estado.crudo)
      .finally(() => { pendiente = null; });
  }
  return pendiente;
}

const vigentes = () => (estado.simulado ? estado.simulado.accesos : estado.accesos);

/** ¿Tiene la vista? Mientras no se sabe, sí (el servidor es la autoridad). */
export function puede(clave, nivel = "ver") {
  if (!estado.cargado) return true;
  const n = vigentes()[clave];
  return n === "editar" || (n === "ver" && nivel === "ver");
}
export const puedeEditar = (clave) => puede(clave, "editar");

/** Vistas que viven en ese paso del costeo (claves de CosteoStepper: costear, producir…). */
export const vistasDelPaso = (paso) => Object.keys(estado.mapa).filter((c) => estado.mapa[c].paso === paso);
/** El paso se ve si tiene al menos una de sus vistas; se edita si alguna está en editar. */
export const pasoVisible = (paso) => !estado.cargado || vistasDelPaso(paso).some((c) => puede(c));
export const pasoEditable = (paso) => !estado.cargado || vistasDelPaso(paso).some((c) => puede(c, "editar"));

/** Vistas que habilitan una ruta del SPA (router name). Sin dueño = libre (Proyectos, Inicio…). */
export const vistasDeRuta = (nombre) => Object.keys(estado.mapa).filter((c) => (estado.mapa[c].rutas || []).includes(nombre));
export function rutaPermitida(nombre, nivel = "ver") {
  const vs = vistasDeRuta(nombre);
  return !estado.cargado || !vs.length || vs.some((c) => puede(c, nivel));
}

/** Nombre de la vista para los mensajes ("lo captura Facturas"). */
export const etiquetaVista = (clave) => estado.mapa[clave]?.etiqueta || clave;

// ── A dónde lleva un documento de una lista ────────────────────────────────────
// Al lugar exacto de su proyecto si el usuario tiene ese paso / vista; si no, null y la
// lista decide (su página de detalle o el Escritorio en solo lectura).
const enCosteo = (costeo, query) => ({ name: "CosteoDetail", params: { name: costeo }, query });
const DESKS = { "Material Request": "material-request", "Purchase Receipt": "purchase-receipt",
  "Delivery Note": "delivery-note", "Purchase Invoice": "purchase-invoice", "Purchase Order": "purchase-order",
  "Quotation": "quotation", "Sales Order": "sales-order", "Sales Invoice": "sales-invoice" };

export function rutaDeDocumento(doctype, r) {
  const c = r?.costeo;
  if (!c) return null;
  const hl = { highlight: r.name, doctype };
  const lote = (paso) => (r.lote_ref ? { step: 5, vista: "lote", lote: r.lote_ref, paso } : null);
  switch (doctype) {
    case "Quotation": return pasoVisible("cotizar") ? enCosteo(c, { step: 1, ...hl }) : null;
    case "Sales Order": return pasoVisible("vender") ? enCosteo(c, { step: 2, ...hl }) : null;
    case "Sales Invoice": return pasoVisible("facturar") ? enCosteo(c, { step: 7, ...hl }) : null;
    case "Material Request": return puede("preparacion") ? enCosteo(c, { step: 5, vista: "preparacion", ...hl }) : null;
    case "Purchase Order":
      if (r.is_subcontracted) {
        if (puede("preparacion")) return enCosteo(c, { step: 5, vista: "ordenes", ...hl });
        return puede("talleres") && lote("talleres") ? enCosteo(c, { ...lote("talleres"), ...hl }) : null;
      }
      return puede("materia") ? enCosteo(c, { ...(lote("materia") || { step: 5, vista: "preparacion" }), ...hl }) : null;
    case "Purchase Receipt":
      if (puede("materia") && lote("materia")) return enCosteo(c, { ...lote("materia"), ...hl });
      return puede("envios") ? enCosteo(c, { step: 5, vista: "envios", filtro_lote: r.lote_ref || undefined, ...hl }) : null;
    case "Delivery Note":
      if (puede("entrega") && lote("entrega")) return enCosteo(c, { ...lote("entrega"), ...hl });
      return puede("envios") ? enCosteo(c, { step: 5, vista: "envios", seg: "remision", ...hl }) : null;
    case "Purchase Invoice": return puede("facturas") ? enCosteo(c, { step: 5, vista: "facturas", filtro_lote: "__todos", ...hl }) : null;
    default: return null;
  }
}
/** El documento en el Escritorio de ERPNext (sus permisos deciden si se edita o solo se ve). */
export const urlEscritorio = (doctype, name) => `/app/${DESKS[doctype] || doctype.toLowerCase().replace(/ /g, "-")}/${encodeURIComponent(name)}`;

export function simular(etiqueta, accesos) { estado.simulado = accesos ? { etiqueta, accesos } : null; }

export function useAccesos() {
  cargarAccesos();
  return { estado, puede, puedeEditar, pasoVisible, pasoEditable, rutaPermitida, etiquetaVista, vistasDelPaso };
}
