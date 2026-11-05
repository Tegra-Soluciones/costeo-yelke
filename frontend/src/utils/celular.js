// Celular (o tableta): pantalla angosta Y táctil. En el celular solo se abren las
// pantallas pensadas para él (meta.movil en el router); una ventana angosta de
// computadora no cuenta, para no bloquear a quien trabaja con la ventana a la mitad.
export const MQ_CELULAR = "(max-width: 1023px) and (pointer: coarse)";

export function esCelular() {
  return typeof window !== "undefined" && window.matchMedia(MQ_CELULAR).matches;
}
