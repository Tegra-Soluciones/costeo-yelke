// Asignaciones (en el código "encargos": api/encargos.py, docs/plan-encargos.md). `version` sube después de cada
// cambio para que Inicio, el proyecto y Dirección se recarguen solos.
import { ref } from "vue";
import { call } from "@/utils/frappe.js";

const API = "costeo_yelke.api.encargos";
export const version = ref(0);

async function hacer(metodo, args) {
  const r = await call(`${API}.${metodo}`, args);
  version.value++;
  refrescarCuenta();
  return r;
}

export const getOpciones = (costeo) => call(`${API}.get_opciones`, { costeo });
export const getDelProyecto = (costeo) => call(`${API}.get_del_proyecto`, { costeo });
export const getMios = (company) => call(`${API}.get_mios`, { company: company || undefined });
export const getEquipo = (company) => call(`${API}.get_equipo`, { company: company || undefined });
export const getPorProyecto = (costeos) => call(`${API}.get_por_proyecto`, { costeos: JSON.stringify(costeos) });

// Para el menú: cuántos tengo abiertos y si veo los del equipo. Se refresca al cambiar algo.
export const cuenta = ref({ para_mi: 0, ve_equipo: false });
export async function refrescarCuenta() {
  try { cuenta.value = await call(`${API}.get_cuenta`); } catch { /* opcional */ }
}

export const crearEncargo = (a) => hacer("crear", a);
export const crearProyecto = (a) => hacer("crear_proyecto", a);
export const marcarListo = (name, nota) => hacer("marcar_listo", { name, nota });
export const regresarEncargo = (name, motivo) => hacer("regresar", { name, motivo });
export const quitarEncargo = (name) => hacer("quitar", { name });
export const reasignarEncargo = (name, usuario) => hacer("reasignar", { name, usuario });
export const recordarEncargo = (name) => hacer("recordar", { name });

/** Texto corto de la fecha límite: "vence hoy", "venció 27-oct", "vence 30-oct". */
export function textoFecha(f, fecha) {
  if (!f.fecha) return "";
  if (f.estado !== "abierto") return `límite ${fecha(f.fecha)}`;
  if (f.vence_hoy) return "vence hoy";
  return f.vencido ? `venció ${fecha(f.fecha)}` : `vence ${fecha(f.fecha)}`;
}

// Paso que ya estaba al día cuando se asignó: no se va a marcar sola.
export const AL_DIA = "Este paso ya está al día: márcala como hecha cuando lo revises.";

export const ESTADO = {
  abierto: ["Abierta", "p-pill-wait"],
  hecho: ["Hecha", "p-pill-ok"],
  regresado: ["Regresada", "p-pill-bad"],
  quitado: ["Quitada", "p-pill-off"],
};

// Sube los archivos juntados al asignar (ArchivosAsignacion sin encargo) al encargo ya creado.
export async function subirArchivosAsignacion(encargo, files) {
  const { uploadToMethod } = await import("@/utils/frappe.js");
  for (const f of files || []) await uploadToMethod("costeo_yelke.api.encargos.subir_archivo", f, { name: encargo });
}
