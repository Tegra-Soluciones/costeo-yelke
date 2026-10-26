// v-mayus: lo que se escribe se convierte a MAYÚSCULAS en el momento (catálogo de
// productos y servicios ordenado; el servidor lo vuelve a exigir al guardar, ver
// costeo_yelke/overrides/uppercase_master.py). Sirve en un <input>/<textarea> o en un
// componente que lo envuelva (ej. LinkInput). Escucha en fase de captura: corre ANTES
// que v-model / el @input del componente, así que esos ya leen el texto convertido.
export default {
  mounted(el) {
    const campo = /^(INPUT|TEXTAREA)$/.test(el.tagName) ? el : el.querySelector("input, textarea");
    if (!campo) return;
    campo.style.textTransform = "uppercase";
    campo.addEventListener("input", () => {
      const valor = campo.value;
      const mayus = valor.toUpperCase();
      if (valor === mayus) return;
      const { selectionStart, selectionEnd } = campo;
      campo.value = mayus;
      if (selectionStart !== null) campo.setSelectionRange(selectionStart, selectionEnd);
    }, true);
  },
};
