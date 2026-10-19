// Permisos de aprobación del usuario (api/aprobaciones.get_permisos_aprobacion),
// leídos UNA vez por sesión y compartidos por todas las pantallas: el menú, las
// pantallas de documento y el panel de Dirección.
import { reactive, ref } from "vue";
import { call } from "@/utils/frappe.js";

const permisos = reactive({
  cargado: false,
  ve_panel: false,
  puede_aprobar: false,
  puede_revisar: false,
  puede_aprobar_precios: false,
});
let pendiente = null;

export function cargarPermisosAprobacion() {
  if (permisos.cargado) return Promise.resolve(permisos);
  if (!pendiente) {
    pendiente = call("costeo_yelke.api.aprobaciones.get_permisos_aprobacion")
      .then((r) => Object.assign(permisos, r, { cargado: true }))
      .catch(() => permisos)
      .finally(() => { pendiente = null; });
  }
  return pendiente;
}

/**
 * ¿Mostrar el botón "Validar" de una pantalla? Con el estado del documento
 * (FranjaAprobacion) manda ese; en un documento nuevo, los permisos del usuario.
 * Mientras no se sabe, se muestra: el backend es la autoridad y rechaza igual.
 */
export function puedeValidarDirecto(estado) {
  if (estado) return !!estado.puede_validar_directo || !estado.aplica;
  return !permisos.cargado || permisos.puede_aprobar;
}

export function usePermisosAprobacion() {
  cargarPermisosAprobacion();
  return permisos;
}

// Cuenta de la bandeja (menú lateral y encabezado del panel). Se refresca al
// resolver algo (la llama el panel, el menú y la campana).

export const cuentaBandeja = ref(0);
export const cuentaDevueltos = ref(0);

export async function refrescarCuentaBandeja() {
  await cargarPermisosAprobacion();
  try {
    const r = await call("costeo_yelke.api.aprobaciones.get_cuenta_bandeja");
    cuentaBandeja.value = r.total || 0;
    cuentaDevueltos.value = r.devueltos || 0;
  } catch { /* el contador es opcional */ }
}
