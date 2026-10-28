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

export function simular(etiqueta, accesos) { estado.simulado = accesos ? { etiqueta, accesos } : null; }

export function useAccesos() {
  cargarAccesos();
  return { estado, puede, puedeEditar, pasoVisible, pasoEditable, rutaPermitida, etiquetaVista, vistasDelPaso };
}
