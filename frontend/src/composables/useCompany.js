import { reactive } from "vue";
import { call } from "@/utils/frappe.js";

const STORAGE_KEY = "costeo_yelke.selected_company";

// Singleton a nivel de módulo: todas las páginas comparten la MISMA instancia
// reactiva (no hay Pinia/Vuex en este proyecto), así que cambiar la compañía
// en el navbar se refleja en cualquier página que la esté observando.
const state = reactive({
  companies: [], // [{ name, default_currency, is_default }]
  selected: localStorage.getItem(STORAGE_KEY) || "",
  loaded: false,
  loading: false,
});

let loadPromise = null;

function pickInitialSelection() {
  if (state.selected && state.companies.some((c) => c.name === state.selected)) return;
  const def = state.companies.find((c) => c.is_default) || state.companies[0];
  state.selected = def ? def.name : "";
  localStorage.setItem(STORAGE_KEY, state.selected);
}

async function ensureLoaded() {
  if (state.loaded) return;
  if (!loadPromise) {
    state.loading = true;
    loadPromise = call("costeo_yelke.api.item_api.get_companies")
      .then((list) => {
        state.companies = list || [];
        pickInitialSelection();
        state.loaded = true;
      })
      .catch((e) => {
        console.error("useCompany: no se pudo cargar la lista de compañías", e);
        loadPromise = null; // permite reintentar en el próximo useCompany()
      })
      .finally(() => {
        state.loading = false;
      });
  }
  return loadPromise;
}

function setCompany(name) {
  state.selected = name || "";
  localStorage.setItem(STORAGE_KEY, state.selected);
}

export function useCompany() {
  ensureLoaded();
  return { state, setCompany };
}
