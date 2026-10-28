// v-solo-lectura="true": deshabilita TODOS los campos y botones de un bloque (un paso del
// costeo, una vista de Producción) cuando el usuario solo tiene la vista en "ver".
// Así no hay que tocar control por control en pantallas con cientos de ellos.
//
// Lo que debe seguir activo aunque sea solo lectura (Vista previa, Descargar PDF,
// abrir un documento, cambiar de OV, Actividad…) va dentro de un elemento con
// `data-libre` (y la navegación, ver NAVEGACION). Un observador vuelve a aplicar la regla cuando Vue re-pinta el bloque.
const CONTROLES = "input, select, textarea, button";
// Navegar no es capturar: filas de lista (FilaLista, renglones del tablero), filtros
// segmentados y los botones marcados `data-nav` (abrir un taller, un documento, una
// columna del tablero) siguen activos en solo lectura.
const NAVEGACION = ".p-row, .p-seg button, [data-nav]";

function aplicar(el) {
  const on = !!el._soloLectura;
  el.classList.toggle("yk-solo-lectura", on);
  el.querySelectorAll(CONTROLES).forEach((c) => {
    if (c.closest("[data-libre]") || c.matches(NAVEGACION)) return;
    if (on && !c.disabled) {
      c.disabled = true;
      c.dataset.ykSl = "1";
    } else if (!on && c.dataset.ykSl) {
      c.disabled = false;
      delete c.dataset.ykSl;
    }
  });
}

export default {
  mounted(el, { value }) {
    el._soloLectura = !!value;
    aplicar(el);
    el._ykObs = new MutationObserver(() => { if (el._soloLectura) aplicar(el); });
    // `attributes: disabled`: Vue puede volver a habilitar un control al re-pintarlo.
    el._ykObs.observe(el, { childList: true, subtree: true, attributes: true, attributeFilter: ["disabled"] });
  },
  updated(el, { value }) {
    if (el._soloLectura === !!value) return;
    el._soloLectura = !!value;
    aplicar(el);
  },
  unmounted(el) { el._ykObs?.disconnect(); },
};
