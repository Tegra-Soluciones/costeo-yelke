<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="$emit('cancel')">
    <div class="bg-white rounded-2xl shadow-xl w-full max-w-md p-5">
      <p class="text-sm font-semibold text-ink">UDM y múltiplos de compra</p>
      <p class="text-[12px] text-ink-muted mt-0.5 mb-4">
        "Múltiplos" es como Yelke le llama a las conversiones de unidad de este
        artículo (ej. Mazo, Gruesa, Pieza) -- <span class="font-mono">{{ itemCode }}</span>.
        Aquí se corrigen los factores, se marca cuáles se compran en paquete completo
        y se agregan los que falten.
      </p>

      <div class="mb-4">
        <label class="field-label mb-1.5">UDM dadas de alta</label>
        <div v-if="loading" class="text-xs text-ink-light">Cargando…</div>
        <ul v-else class="space-y-1.5">
          <li v-for="(u, i) in existentes" :key="u.uom" class="bg-surface-raised rounded-lg px-3 py-2">
            <div class="flex items-center gap-2 text-[12.5px]">
              <span class="font-medium text-ink flex-1 min-w-0 truncate">
                {{ u.uom }}<span v-if="u.uom === stockUom" class="ml-1 text-[10px] font-semibold text-ink-muted">UDM base</span>
              </span>
              <!-- La UDM base no tiene factor que editar: es 1 por definición. -->
              <span v-if="u.uom === stockUom" class="text-ink-muted text-[11.5px]">factor 1</span>
              <template v-else>
                <span class="text-[11px] text-ink-light whitespace-nowrap">1 {{ u.uom }} =</span>
                <input
                  v-model.number="u.conversion_factor" type="number" min="0.0000001" step="any"
                  class="w-28 border border-surface-border rounded-lg px-2 py-1 text-[12.5px] text-right bg-white focus:outline-none"
                />
                <span class="text-[11px] text-ink-light whitespace-nowrap">{{ stockUom }}</span>
                <button
                  type="button" title="Quitar este múltiplo"
                  class="h-6 w-6 flex items-center justify-center text-ink-muted hover:bg-red-50 hover:text-red-500 rounded-lg shrink-0"
                  @click="existentes.splice(i, 1)"
                >✕</button>
              </template>
            </div>
            <label class="flex items-center gap-1.5 text-[11.5px] text-ink-muted mt-1">
              <input v-model="u.compra_por_paquete_completo" type="checkbox" class="rounded" />
              Se compra en paquetes completos (no se puede pedir una fracción — se redondea hacia arriba)
            </label>
          </li>
        </ul>
        <p class="text-[11px] text-ink-light mt-1.5">
          Cambiar un factor afecta a lo que se capture de aquí en adelante: los documentos ya validados conservan la cantidad con la que se guardaron.
        </p>
      </div>

      <div class="mb-3">
        <label class="field-label mb-1">Agregar un múltiplo nuevo</label>
        <div v-for="(row, idx) in nuevos" :key="idx" class="mb-2.5">
          <div class="grid grid-cols-[1fr_1fr_28px] gap-2 items-center mb-1">
            <LinkInput v-model="row.uom" doctype="UOM" placeholder="UOM del proveedor…" />
            <div class="flex items-center border border-surface-border rounded-lg bg-white min-w-0">
              <span class="pl-2 text-[11px] text-ink-light select-none whitespace-nowrap">1 {{ row.uom || '?' }} =</span>
              <input v-model.number="row.conversion_factor" type="number" min="0.0000001" step="any" class="flex-1 min-w-0 py-2 pr-2 pl-1 text-sm focus:outline-none bg-transparent" />
            </div>
            <button type="button" class="h-7 w-7 flex items-center justify-center text-ink-muted hover:bg-red-50 hover:text-red-500 rounded-lg" @click="nuevos.splice(idx, 1)">
              <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
            </button>
          </div>
          <label class="flex items-center gap-1.5 text-[11.5px] text-ink-muted pl-0.5">
            <input v-model="row.compra_por_paquete_completo" type="checkbox" class="rounded" />
            Se compra en paquetes completos (no se puede pedir una fracción -- se redondea hacia arriba)
          </label>
        </div>
        <button type="button" class="text-[11px] font-medium text-brand-600 hover:text-brand-700" @click="addRow">+ Otro múltiplo</button>
        <p class="text-[11px] text-ink-light mt-2">
          Ej. si un Mazo trae 1728 piezas: UOM = Pieza, factor = 1 ÷ 1728 = 0.000578704
          (cuántos "{{ stockUom || 'UDM base' }}" es UNA pieza).
        </p>
      </div>

      <p v-if="errorMsg" class="text-[12px] text-red-500 mb-2">{{ errorMsg }}</p>

      <div class="flex gap-2 justify-end mt-4">
        <button type="button" class="px-3 py-1.5 text-[13px] text-ink-muted hover:bg-surface-raised rounded-lg" @click="$emit('cancel')">Cancelar</button>
        <button type="button" :disabled="saving" class="px-4 py-1.5 text-[13px] font-medium text-white bg-brand-500 hover:bg-brand-600 disabled:opacity-50 rounded-lg flex items-center gap-2" @click="onConfirm">
          <svg v-if="saving" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
          {{ saving ? "Guardando…" : "Guardar" }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from "vue";
import LinkInput from "@/components/LinkInput.vue";
import { call } from "@/utils/frappe.js";

const props = defineProps({
  open: { type: Boolean, default: false },
  itemCode: { type: String, default: "" },
});
// "saved" lleva la UOM del último múltiplo agregado, para que quien abrió el modal
// (ej. la línea de la OC) pueda seleccionarla sola al cerrar.
const emit = defineEmits(["cancel", "saved"]);

const loading  = ref(false);
const saving   = ref(false);
const errorMsg = ref("");
const stockUom = ref("");
const existentes = ref([]);
const nuevos = reactive([]);

function fmt(n) {
  const v = Number(n) || 0;
  return v < 0.001 ? v.toFixed(9).replace(/0+$/, "") : String(Math.round(v * 1e6) / 1e6);
}

function addRow() { nuevos.push({ uom: "", conversion_factor: null, compra_por_paquete_completo: false }); }

async function cargar() {
  loading.value = true;
  errorMsg.value = "";
  try {
    const r = await call("costeo_yelke.api.item_api.get_item_uoms", { item_code: props.itemCode });
    stockUom.value = r.stock_uom || "";
    existentes.value = r.uoms || [];
  } catch (e) {
    errorMsg.value = e.message || "No se pudo cargar";
  } finally {
    loading.value = false;
  }
}

watch(() => props.open, (isOpen) => {
  if (!isOpen) return;
  nuevos.splice(0, nuevos.length, { uom: "", conversion_factor: null, compra_por_paquete_completo: false });
  errorMsg.value = "";
  cargar();
});

async function onConfirm() {
  const validos = nuevos.filter((r) => r.uom && r.conversion_factor > 0);
  // Ya no hace falta agregar nada: se puede abrir solo para corregir un factor o
  // marcar el check de una UDM que ya existía (el caso de los artículos dados de
  // alta antes de que el check existiera).
  const aMedias = nuevos.find((r) => (r.uom && !(r.conversion_factor > 0)) || (!r.uom && r.conversion_factor > 0));
  if (aMedias) { errorMsg.value = "Al múltiplo nuevo le falta la UOM o el factor — complétalo o quítalo de la lista."; return; }
  const sinFactor = existentes.value.find((e) => e.uom !== stockUom.value && !(e.conversion_factor > 0));
  if (sinFactor) { errorMsg.value = `El factor de ${sinFactor.uom} tiene que ser mayor que cero.`; return; }
  const yaExiste = validos.find((r) => existentes.value.some((e) => e.uom === r.uom));
  if (yaExiste) { errorMsg.value = `${yaExiste.uom} ya está dado de alta — corrige su factor arriba en vez de agregarlo otra vez.`; return; }

  saving.value = true;
  errorMsg.value = "";
  try {
    const todos = [...existentes.value, ...validos].map((r) => ({
      uom: r.uom, conversion_factor: r.conversion_factor,
      compra_por_paquete_completo: !!r.compra_por_paquete_completo,
    }));
    await call("costeo_yelke.api.item_api.save_item_uoms", {
      item_code: props.itemCode, uoms: JSON.stringify(todos),
    });
    emit("saved", validos.length ? validos[validos.length - 1].uom : null);
  } catch (e) {
    errorMsg.value = e.message || "No se pudo guardar";
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped>
.field-label { @apply text-xs font-medium text-ink-muted block mb-1; }
</style>
