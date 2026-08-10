<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="$emit('cancel')">
    <div class="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-5">
      <p class="text-sm font-semibold text-ink">Dar de alta el producto terminado</p>
      <p class="text-[12px] text-ink-muted mt-0.5 mb-4">
        <span class="font-medium">"{{ finishedItemText }}"</span> todavía no existe como artículo en el ERP.
        Para pasar a cotización necesitamos crearlo — materiales y servicios se pueden dejar como texto libre por ahora.
      </p>

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
        <label class="field-label">Precio de venta</label>
        <div class="flex items-center border border-surface-border rounded-lg focus-within:ring-2 focus-within:ring-brand-500/30 focus-within:border-brand-400 bg-white">
          <span class="pl-3 pr-1 text-sm text-ink-light select-none">$</span>
          <input v-model.number="form.precio_venta" type="number" min="0" step="0.01" class="flex-1 min-w-0 py-2 pr-3 text-sm focus:outline-none bg-transparent" />
        </div>
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

      <div class="mb-3">
        <label class="field-label">Clave de producto/servicio SAT <span class="text-ink-light font-normal">(opcional)</span></label>
        <input v-model="form.mx_product_service_key" class="field-input" placeholder="Ej: 53101800" />
      </div>

      <p class="text-[11px] text-ink-light bg-surface-raised rounded-lg px-3 py-2 mb-1">
        Se asignará automáticamente a <strong>{{ company || '—' }}</strong> · Lista de precios: <strong>Venta estándar</strong>.
      </p>

      <div class="flex gap-2 justify-end mt-4">
        <button class="px-3 py-1.5 text-[13px] text-ink-muted hover:bg-surface-raised rounded-lg" @click="$emit('cancel')">Cancelar</button>
        <button :disabled="saving" class="px-4 py-1.5 text-[13px] font-medium text-white bg-brand-500 hover:bg-brand-600 disabled:opacity-50 rounded-lg flex items-center gap-2" @click="onConfirm">
          <svg v-if="saving" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
          {{ saving ? "Creando…" : "Crear y continuar" }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, watch } from "vue";
import LinkInput from "@/components/LinkInput.vue";

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

const form = reactive({
  item_code: "", item_name: "", stock_uom: "", description: "", image: "",
  precio_venta: 0, conPrecioVolumen: false, rangos: [], mx_product_service_key: "",
});
const errors = reactive({ item_code: false, item_name: false, stock_uom: false });

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
  form.item_code = suggestCode(props.finishedItemText);
  form.item_name = props.finishedItemText;
  form.stock_uom = "";
  form.precio_venta = props.suggestedPrice || 0;
  form.conPrecioVolumen = false;
  form.rangos = [];
  form.description = props.suggestedDescription || "";
  form.image = props.suggestedImage || "";
  form.mx_product_service_key = "";
  errors.item_code = false; errors.item_name = false; errors.stock_uom = false;
});

function onConfirm() {
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
    mx_product_service_key: form.mx_product_service_key || null,
  });
}
</script>

<style scoped>
.field-label { @apply text-xs font-medium text-ink-muted block mb-1; }
.field-input { @apply w-full text-sm border border-surface-border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400 bg-white transition-colors; }
</style>
