<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="$emit('cancel')">
    <div class="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-5">
      <div class="flex items-center gap-2 mb-1">
        <span class="text-[11px] font-semibold px-2 py-0.5 rounded-full" :style="{ background: tipoInfo.bg, color: tipoInfo.textColor }">{{ tipoInfo.icon }} {{ tipoInfo.label }}</span>
      </div>
      <p class="text-sm font-semibold text-ink">Dar de alta "{{ texto }}"</p>
      <p class="text-[12px] text-ink-muted mt-0.5 mb-4">Todavía no existe como artículo en el ERP. Grupo, inventario y demás banderas se asignan solas según el tipo — solo confirma lo de abajo.</p>

      <div class="mb-3">
        <label class="field-label">Código del artículo <span class="text-red-400">*</span></label>
        <input v-model="form.item_code" class="field-input" placeholder="Ej: YLK-TEL-NEG" :class="errors.item_code ? 'border-red-400' : ''" />
      </div>

      <div class="mb-3">
        <label class="field-label">Nombre <span class="text-red-400">*</span></label>
        <input v-model="form.item_name" class="field-input" placeholder="Nombre del artículo" :class="errors.item_name ? 'border-red-400' : ''" />
      </div>

      <div class="mb-3">
        <label class="field-label">UOM <span class="text-red-400">*</span></label>
        <LinkInput v-model="form.stock_uom" doctype="UOM" placeholder="Unidad de medida…" :error="!!errors.stock_uom" />
        <p v-if="suggestedStockUom" class="text-[11px] text-ink-light mt-1">Tomado de la UDM ya capturada en el costeo — ajústala si no es correcta.</p>
      </div>

      <div class="mb-3">
        <label class="field-label">Descripción <span class="text-ink-light font-normal">(opcional)</span></label>
        <textarea v-model="form.description" rows="2" class="field-input resize-none" placeholder="Descripción del artículo…"></textarea>
      </div>

      <div v-if="tipoInfo.hasSupplier" class="mb-3">
        <label class="field-label">Proveedor</label>
        <LinkInput v-model="form.supplier" doctype="Supplier" placeholder="Proveedor…" />
        <p v-if="supplierPrefilled" class="text-[11px] text-ink-light mt-1">Tomado del renglón del costeo — ajústalo si no es correcto.</p>
      </div>

      <div v-if="tipoInfo.hasSupplier" class="mb-3">
        <label class="field-label">Precio de compra</label>
        <div class="relative flex items-center border border-surface-border rounded-lg focus-within:ring-2 focus-within:ring-brand-500/30 focus-within:border-brand-400 bg-white">
          <span class="pl-3 pr-1 text-sm text-ink-light select-none">$</span>
          <input v-model.number="form.precio" type="number" min="0" step="0.01" class="flex-1 min-w-0 py-2 pr-8 text-sm focus:outline-none bg-transparent" />
          <button v-if="rowType === 'material'" type="button" class="absolute right-1 text-ink-light hover:text-brand-600" title="Convertir precio de $/kg a $/m" @click="openTelaConvert">
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><rect x="5" y="3" width="14" height="18" rx="2"/><path stroke-linecap="round" d="M8 7h8M8 11h.01M12 11h.01M16 11h.01M8 15h.01M12 15h.01M16 15h.01"/></svg>
          </button>
          <template v-if="telaConvert.open">
            <div class="fixed inset-0 z-40" @click="closeTelaConvert()"></div>
            <div class="absolute z-50 right-0 top-full mt-1 w-64 bg-white border border-surface-border rounded-lg shadow-lg p-3 text-left">
              <p class="text-xs font-semibold text-ink mb-2">Convertir $/kg → $/m</p>
              <label class="field-label mb-0.5">Precio por kilo (el que te dio el proveedor)</label>
              <div class="relative mb-2"><span class="prefix text-xs">$</span><input v-model.number="telaConvert.precio_kg" type="number" min="0" step="0.01" class="field-input text-right pl-5 py-1" /></div>
              <label class="field-label mb-0.5">Metros que salen de 1 kilo</label>
              <input v-model.number="telaConvert.metros_por_kilo" type="number" min="0" step="0.01" placeholder="ej. 5.2" class="field-input text-right py-1" />
              <p class="text-[11px] text-ink-muted mt-2">Precio por metro: <span class="font-semibold text-brand-600">${{ telaConvertPrecioM.toFixed(2) }}</span></p>
              <p class="text-[10px] text-ink-xlight mt-1">Al usarlo, la UOM del artículo cambia a Metro -- ahí capturas tú el consumo por prenda en Costear.</p>
              <div class="flex items-center justify-end gap-3 mt-3">
                <button type="button" class="text-xs text-ink-light hover:text-ink" @click="closeTelaConvert()">Cancelar</button>
                <button type="button" class="text-xs font-semibold text-white bg-brand-500 hover:bg-brand-600 rounded-lg px-3 py-1.5" @click="aplicarTelaConvert()">Usar este precio</button>
              </div>
            </div>
          </template>
        </div>
        <p v-if="suggestedPrice" class="text-[11px] text-ink-light mt-1">Tomado del precio unitario ya capturado en el costeo.</p>
      </div>

      <!-- Conversión de unidades: el proveedor puede surtir en una UOM distinta a la interna (ej. rollos de 10m) -->
      <div class="mb-3">
        <div class="flex items-center justify-between mb-1">
          <label class="field-label mb-0">Múltiplos de compra <span class="text-ink-light font-normal">(opcional)</span></label>
          <button v-if="!form.uomConversions.length" class="text-[11px] font-medium text-brand-600 hover:text-brand-700" @click="addConversion">+ Agregar</button>
        </div>
        <p class="text-[11px] text-ink-light mb-2">Si el proveedor surte en una unidad distinta a "{{ form.stock_uom || 'UOM base' }}" (ej. rollos, cajas).</p>
        <div v-for="(row, idx) in form.uomConversions" :key="idx" class="grid grid-cols-[1fr_1fr_28px] gap-2 items-center mb-1.5">
          <LinkInput v-model="row.uom" doctype="UOM" placeholder="UOM proveedor…" />
          <div class="flex items-center border border-surface-border rounded-lg bg-white min-w-0">
            <span class="pl-2 text-[11px] text-ink-light select-none whitespace-nowrap">1 {{ row.uom || '?' }} =</span>
            <input v-model.number="row.conversion_factor" type="number" min="0.0001" step="0.001" class="flex-1 min-w-0 py-2 pr-2 pl-1 text-sm focus:outline-none bg-transparent" />
          </div>
          <button class="h-7 w-7 flex items-center justify-center text-ink-muted hover:bg-red-50 hover:text-red-500 rounded-lg" @click="form.uomConversions.splice(idx, 1)">
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
          </button>
        </div>
        <button v-if="form.uomConversions.length" class="text-[11px] font-medium text-brand-600 hover:text-brand-700" @click="addConversion">+ Otra conversión</button>
      </div>

      <div class="mb-3">
        <label class="field-label">Clave de producto/servicio SAT <span class="text-ink-light font-normal">(opcional)</span></label>
        <input v-model="form.mx_product_service_key" class="field-input" placeholder="Ej: 53101800" />
      </div>

      <p class="text-[11px] text-ink-light bg-surface-raised rounded-lg px-3 py-2 mb-1">
        Se asignará automáticamente a <strong>{{ company || '—' }}</strong>
        <span v-if="defaultWarehouse"> · Almacén: <strong>{{ defaultWarehouse }}</strong></span>
        <span v-if="tipoInfo.hasSupplier"> · Lista de precios: <strong>Compra estándar</strong></span>.
      </p>

      <div class="flex gap-2 justify-end mt-4">
        <button class="px-3 py-1.5 text-[13px] text-ink-muted hover:bg-surface-raised rounded-lg" @click="$emit('cancel')">Cancelar</button>
        <button :disabled="saving" class="px-4 py-1.5 text-[13px] font-medium text-white bg-brand-500 hover:bg-brand-600 disabled:opacity-50 rounded-lg flex items-center gap-2" @click="onConfirm">
          <svg v-if="saving" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
          {{ saving ? "Creando…" : "Crear y vincular" }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed, watch } from "vue";
import LinkInput from "@/components/LinkInput.vue";

const props = defineProps({
  open: { type: Boolean, default: false },
  rowType: { type: String, default: "material" }, // material | servicio_etapa | subensamblaje_etapa
  texto: { type: String, default: "" },
  suggestedSupplier: { type: String, default: "" },
  suggestedPrice: { type: Number, default: 0 },
  suggestedSupplierUom: { type: String, default: "" },
  suggestedConversionFactor: { type: Number, default: 0 },
  suggestedStockUom: { type: String, default: "" },
  company: { type: String, default: "" },
  defaultWarehouse: { type: String, default: "" },
  saving: { type: Boolean, default: false },
});
const emit = defineEmits(["cancel", "confirm"]);

const TIPOS = {
  material: {
    label: "Materia Prima", icon: "🧵", bg: "#fffbeb", textColor: "#92400e",
    item_group: "Materia prima", hasSupplier: true,
    flags: { is_stock_item: 1, is_sales_item: 0, is_purchase_item: 1, include_item_in_manufacturing: 1 },
  },
  servicio_etapa: {
    label: "Servicio", icon: "⚙️", bg: "#eff6ff", textColor: "#1e40af",
    item_group: "Servicios", hasSupplier: true,
    flags: { is_stock_item: 0, is_sales_item: 0, is_purchase_item: 1, include_item_in_manufacturing: 1 },
  },
  subensamblaje_etapa: {
    label: "Sub-ensamblaje", icon: "🔧", bg: "#f0fdf4", textColor: "#166534",
    item_group: "Sub-Ensamblajes", hasSupplier: false,
    flags: { is_stock_item: 1, is_sales_item: 0, is_purchase_item: 0, include_item_in_manufacturing: 1, is_sub_contracted_item: 1 },
  },
};

const tipoInfo = computed(() => TIPOS[props.rowType] || TIPOS.material);

const form = reactive({
  item_code: "", item_name: "", stock_uom: "", description: "", supplier: "", precio: 0,
  uomConversions: [], mx_product_service_key: "",
});
const errors = reactive({ item_code: false, item_name: false, stock_uom: false });
const supplierPrefilled = computed(() => !!props.suggestedSupplier);

function suggestCode(text) {
  return (text || "")
    .toUpperCase()
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[^A-Z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 30);
}

function addConversion() {
  form.uomConversions.push({ uom: "", conversion_factor: 1 });
}

// Mismo conversor $/kg -> $/m que ya existe en Costear (telaConvertModal en
// CosteoDetailPage.vue) -- aquí el artículo todavía NO existe, así que no hay
// nada que guardar en el Item (metros_por_kilo se persiste allá, no aquí); solo
// calcula y aplica el precio por metro + cambia la UOM del alta a Metro.
const telaConvert = reactive({ open: false, precio_kg: 0, metros_por_kilo: null });
const telaConvertPrecioM = computed(() => {
  const kg = telaConvert.metros_por_kilo || 0;
  return kg > 0 ? Math.round(((telaConvert.precio_kg || 0) / kg) * 100) / 100 : 0;
});
function openTelaConvert() {
  telaConvert.open = true;
  telaConvert.precio_kg = form.precio || 0;
  telaConvert.metros_por_kilo = null;
}
function closeTelaConvert() { telaConvert.open = false; }
function aplicarTelaConvert() {
  form.precio = telaConvertPrecioM.value;
  form.stock_uom = "MTR - Metro";
  closeTelaConvert();
}

watch(() => props.open, (isOpen) => {
  if (!isOpen) return;
  form.item_code = suggestCode(props.texto);
  form.item_name = props.texto;
  form.stock_uom = props.suggestedStockUom || "";
  form.supplier = props.suggestedSupplier || "";
  form.precio = props.suggestedPrice || 0;
  form.description = "";
  form.mx_product_service_key = "";
  form.uomConversions = (props.suggestedSupplierUom && props.suggestedConversionFactor)
    ? [{ uom: props.suggestedSupplierUom, conversion_factor: props.suggestedConversionFactor }]
    : [];
  errors.item_code = false; errors.item_name = false; errors.stock_uom = false;
});

function onConfirm() {
  errors.item_code = !form.item_code.trim();
  errors.item_name = !form.item_name.trim();
  errors.stock_uom = !form.stock_uom;
  if (errors.item_code || errors.item_name || errors.stock_uom) return;

  const info = tipoInfo.value;
  const prefill = {
    item_name: form.item_name.trim(),
    item_group: info.item_group,
    stock_uom: form.stock_uom,
    ...info.flags,
  };
  if (form.description) prefill.description = form.description;
  if (form.mx_product_service_key) prefill.mx_product_service_key = form.mx_product_service_key;
  const uomConversions = form.uomConversions.filter(r => r.uom && r.conversion_factor > 0);
  if (uomConversions.length) prefill.uom_conversions = uomConversions;

  emit("confirm", {
    item_code: form.item_code.trim(),
    prefill,
    supplier: info.hasSupplier ? (form.supplier || null) : null,
    precio: info.hasSupplier ? (form.precio || null) : null,
  });
}
</script>

<style scoped>
.field-label { @apply text-xs font-medium text-ink-muted block mb-1; }
.field-input { @apply w-full text-sm border border-surface-border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400 bg-white transition-colors; }
</style>
