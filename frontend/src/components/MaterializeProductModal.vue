<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="$emit('cancel')">
    <div class="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-5">
      <p class="text-sm font-semibold text-ink">Dar de alta el producto terminado</p>
      <p class="text-[12px] text-ink-muted mt-0.5 mb-4">
        <span class="font-medium">"{{ finishedItemText }}"</span> todavía no existe como artículo en el ERP.
        Para pasar a cotización necesitamos crearlo — o vincular uno que ya hayas dado de alta antes.
      </p>

      <div class="flex gap-1 mb-4 bg-surface-raised rounded-lg p-1">
        <button type="button" class="flex-1 text-[12.5px] font-medium py-1.5 rounded-md transition-colors" :class="mode === 'new' ? 'bg-white shadow-sm text-ink' : 'text-ink-muted hover:text-ink'" @click="mode = 'new'">Crear nuevo</button>
        <button type="button" class="flex-1 text-[12.5px] font-medium py-1.5 rounded-md transition-colors" :class="mode === 'existing' ? 'bg-white shadow-sm text-ink' : 'text-ink-muted hover:text-ink'" @click="mode = 'existing'">Usar existente</button>
      </div>

      <template v-if="mode === 'existing'">
        <div class="mb-3">
          <label class="field-label">Producto terminado existente <span class="text-red-400">*</span></label>
          <LinkInput v-model="existingItemCode" doctype="Item" :filters="EXISTING_ITEM_FILTERS" placeholder="Buscar por código o nombre…" :error="!!errors.existing" @update:model-value="onSelectExisting" />
        </div>
        <div v-if="existingPreview" class="mb-3 flex items-center gap-2 bg-surface-raised rounded-lg p-2.5">
          <img v-if="existingPreview.image" :src="existingPreview.image" class="w-10 h-10 rounded-lg object-cover border border-surface-border flex-shrink-0" alt="" />
          <div class="min-w-0 flex-1">
            <p class="text-[12.5px] font-medium text-ink truncate">{{ existingPreview.item_name }}</p>
            <p class="text-[11px] text-ink-light">UOM: {{ existingPreview.stock_uom }}</p>
          </div>
          <span v-if="existingSuggested" class="text-[10.5px] font-medium text-brand-600 bg-brand-50 rounded-full px-2 py-0.5 flex-shrink-0">Sugerido</span>
        </div>
        <div class="mb-3">
          <label class="field-label flex items-center gap-1.5">Precio de venta <span class="text-[10px] font-normal text-ink-light bg-surface-raised border border-surface-border rounded px-1">sin IVA</span></label>
          <div class="flex items-center border border-surface-border rounded-lg bg-surface-raised/60 text-ink-light">
            <span class="pl-3 pr-1 text-sm select-none">$</span>
            <span class="flex-1 min-w-0 py-2 pr-3 text-sm">{{ (form.precio_venta || 0).toFixed(2) }}</span>
          </div>
          <p class="text-[10.5px] text-ink-light mt-1">Ya se fijó en el costeo — no se puede editar aquí.</p>
        </div>
      </template>

      <template v-else>
        <div class="mb-3">
          <label class="field-label">Código del artículo <span class="text-red-400">*</span></label>
          <input v-model="form.item_code" class="field-input" placeholder="Ej: YLK-CHA-TIM" :class="errors.item_code ? 'border-red-400' : ''" />
        </div>

        <div class="mb-3">
          <label class="field-label">Nombre <span class="text-red-400">*</span></label>
          <input v-model="form.item_name" class="field-input" placeholder="Nombre del producto" :class="errors.item_name ? 'border-red-400' : ''" />
        </div>

        <div class="mb-3">
          <label class="field-label">UOM <span class="text-red-400">*</span></label>
          <LinkInput v-model="form.stock_uom" doctype="UOM" placeholder="Unidad de medida…" :error="!!errors.stock_uom" />
        </div>

        <div v-if="form.image" class="mb-3 flex items-center gap-2">
          <img :src="form.image" class="w-12 h-12 rounded-lg object-cover border border-surface-border" alt="" />
          <p class="text-[11px] text-ink-light">Imagen tomada del costeo — se usará para este artículo.</p>
        </div>

        <div class="mb-3">
          <label class="field-label">Descripción <span class="text-ink-light font-normal">(opcional)</span></label>
          <textarea v-model="form.description" rows="2" class="field-input resize-none" placeholder="Descripción del producto…"></textarea>
        </div>

        <div class="mb-3">
          <label class="field-label flex items-center gap-1.5">Precio de venta <span class="text-[10px] font-normal text-ink-light bg-surface-raised border border-surface-border rounded px-1">sin IVA</span></label>
          <div class="flex items-center border border-surface-border rounded-lg bg-surface-raised/60 text-ink-light">
            <span class="pl-3 pr-1 text-sm select-none">$</span>
            <span class="flex-1 min-w-0 py-2 pr-3 text-sm">{{ (form.precio_venta || 0).toFixed(2) }}</span>
          </div>
          <p class="text-[10.5px] text-ink-light mt-1">Ya se fijó en el costeo — no se puede editar aquí.</p>
        </div>

        <label class="flex items-center gap-2 text-[13px] text-ink cursor-pointer mb-2">
          <input type="checkbox" v-model="form.conPrecioVolumen" class="rounded border-surface-border text-brand-500" />
          Agregar precio por volumen
        </label>

        <div v-if="form.conPrecioVolumen" class="mb-3 border border-surface-border rounded-lg p-3 bg-surface-raised/40">
          <div class="grid grid-cols-[1fr_1fr_1fr_28px] gap-2 mb-1.5 px-0.5">
            <span class="text-[11px] font-medium text-ink-muted">Desde (cant.)</span>
            <span class="text-[11px] font-medium text-ink-muted">Hasta (cant.)</span>
            <span class="text-[11px] font-medium text-ink-muted">Precio</span>
            <span></span>
          </div>
          <div v-for="(r, idx) in form.rangos" :key="idx" class="grid grid-cols-[1fr_1fr_1fr_28px] gap-2 items-center mb-1.5">
            <input v-model.number="r.min_qty" type="number" min="0" step="1" class="field-input min-w-0" />
            <input v-model.number="r.max_qty" type="number" min="0" step="1" class="field-input min-w-0" placeholder="Sin tope" />
            <div class="flex items-center border border-surface-border rounded-lg bg-white min-w-0">
              <span class="pl-2 text-xs text-ink-light select-none">$</span>
              <input v-model.number="r.rate" type="number" min="0" step="0.01" class="flex-1 min-w-0 py-2 pr-2 pl-1 text-sm focus:outline-none bg-transparent" />
            </div>
            <button class="h-7 w-7 flex items-center justify-center text-ink-muted hover:bg-red-50 hover:text-red-500 rounded-lg" @click="form.rangos.splice(idx, 1)">
              <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
            </button>
          </div>
          <button class="text-[12px] font-medium text-brand-600 hover:text-brand-700 mt-1" @click="addRango">+ Agregar rango</button>
        </div>
      </template>

      <p class="text-[11px] text-ink-light bg-surface-raised rounded-lg px-3 py-2 mb-1">
        <template v-if="mode === 'existing'">El producto quedará vinculado a este renglón del costeo.</template>
        <template v-else>Se asignará automáticamente a <strong>{{ company || '—' }}</strong> · Lista de precios: <strong>Venta estándar</strong>.</template>
      </p>

      <div class="flex gap-2 justify-end mt-4">
        <button class="px-3 py-1.5 text-[13px] text-ink-muted hover:bg-surface-raised rounded-lg" @click="$emit('cancel')">Cancelar</button>
        <button :disabled="saving" class="px-4 py-1.5 text-[13px] font-medium text-white bg-brand-500 hover:bg-brand-600 disabled:opacity-50 rounded-lg flex items-center gap-2" @click="onConfirm">
          <svg v-if="saving" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
          {{ saving ? (mode === 'existing' ? "Vinculando…" : "Creando…") : (mode === 'existing' ? "Vincular y continuar" : "Crear y continuar") }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from "vue";
import LinkInput from "@/components/LinkInput.vue";
import { call, searchLink, fuzzyQuery } from "@/utils/frappe.js";

const props = defineProps({
  open: { type: Boolean, default: false },
  finishedItemText: { type: String, default: "" },
  suggestedPrice: { type: Number, default: 0 },
  suggestedDescription: { type: String, default: "" },
  suggestedImage: { type: String, default: "" },
  company: { type: String, default: "" },
  saving: { type: Boolean, default: false },
});
const emit = defineEmits(["cancel", "confirm"]);

const EXISTING_ITEM_FILTERS = [["item_group", "=", "Productos Terminados"]];

const mode = ref("new");
const existingItemCode = ref("");
const existingPreview = ref(null);
const existingSuggested = ref(false);
let suggestReq = 0;

const form = reactive({
  item_code: "", item_name: "", stock_uom: "", description: "", image: "",
  precio_venta: 0, conPrecioVolumen: false, rangos: [],
});
const errors = reactive({ item_code: false, item_name: false, stock_uom: false, existing: false });

async function onSelectExisting(code, { suggested = false } = {}) {
  existingPreview.value = null;
  errors.existing = false;
  existingSuggested.value = suggested;
  if (!code) return;
  try {
    // El precio YA no se trae del artículo existente ni se deja editar aquí --
    // siempre es el que se fijó en el costeo (props.suggestedPrice), fijo.
    const doc = await call("frappe.client.get_value", {
      doctype: "Item",
      filters: { name: code },
      fieldname: ["item_name", "stock_uom", "image"],
    });
    existingPreview.value = doc || null;
  } catch { /* ignore — el usuario puede reintentar la búsqueda */ }
}

// Al abrir el modal, busca de una vez el Item existente más parecido al texto libre
// del producto — así "Usar existente" ya llega con una sugerencia lista en vez de
// obligar a escribir la búsqueda a mano.
async function autoSuggestExisting(text) {
  const req = ++suggestReq;
  try {
    const results = await searchLink("Item", fuzzyQuery(text), EXISTING_ITEM_FILTERS);
    if (req !== suggestReq || existingItemCode.value) return;
    if (results && results.length) {
      existingItemCode.value = results[0].value;
      await onSelectExisting(results[0].value, { suggested: true });
    }
  } catch { /* sin sugerencia — el usuario busca a mano */ }
}

function suggestCode(text) {
  return (text || "")
    .toUpperCase()
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[^A-Z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 30);
}

function addRango() {
  // "Hasta" se deja vacío a propósito — vacío = sin tope, más claro que pedir un 0 literal.
  const prevMax = form.rangos.length ? form.rangos[form.rangos.length - 1].max_qty : 0;
  form.rangos.push({ min_qty: (prevMax || 0) + 1 || 1, max_qty: "", rate: 0 });
}

watch(() => props.open, (isOpen) => {
  if (!isOpen) return;
  mode.value = "new";
  existingItemCode.value = "";
  existingPreview.value = null;
  existingSuggested.value = false;
  autoSuggestExisting(props.finishedItemText);
  form.item_code = suggestCode(props.finishedItemText);
  form.item_name = props.finishedItemText;
  form.stock_uom = "H87 - Pieza"; // default -- la mayoría de los productos terminados se venden por pieza, pero se puede cambiar libremente
  form.precio_venta = props.suggestedPrice || 0;
  form.conPrecioVolumen = false;
  form.rangos = [];
  form.description = props.suggestedDescription || "";
  form.image = props.suggestedImage || "";
  errors.item_code = false; errors.item_name = false; errors.stock_uom = false; errors.existing = false;
});

function onConfirm() {
  if (mode.value === "existing") {
    errors.existing = !existingItemCode.value;
    if (errors.existing) return;
    emit("confirm", {
      item_code: existingItemCode.value,
      item_name: existingPreview.value?.item_name || existingItemCode.value,
      stock_uom: existingPreview.value?.stock_uom || "",
      description: null,
      image: existingPreview.value?.image || null,
      precio_venta: form.precio_venta || 0,
      pricing_rules: [],
    });
    return;
  }

  errors.item_code = !form.item_code.trim();
  errors.item_name = !form.item_name.trim();
  errors.stock_uom = !form.stock_uom;
  if (errors.item_code || errors.item_name || errors.stock_uom) return;

  const pricing_rules = form.conPrecioVolumen
    ? form.rangos
        .filter(r => r.rate > 0)
        .map(r => ({ rate_or_discount: "Rate", min_qty: r.min_qty || 0, max_qty: r.max_qty || 0, rate: r.rate }))
    : [];

  emit("confirm", {
    item_code: form.item_code.trim(),
    item_name: form.item_name.trim(),
    stock_uom: form.stock_uom,
    description: form.description || null,
    image: form.image || null,
    precio_venta: form.precio_venta || 0,
    pricing_rules,
  });
}
</script>

<style scoped>
.field-label { @apply text-xs font-medium text-ink-muted block mb-1; }
.field-input { @apply w-full text-sm border border-surface-border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400 bg-white transition-colors; }
</style>
