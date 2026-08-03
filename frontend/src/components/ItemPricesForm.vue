<template>
  <div class="space-y-8">

    <!-- ══════════════════════════════════════════════════════
         SECCIÓN 1 — PRECIOS POR LISTA
    ═══════════════════════════════════════════════════════ -->
    <div>
      <div class="flex items-start justify-between mb-4">
        <div>
          <h3 class="text-sm font-semibold text-gray-800">Precios por Lista</h3>
          <p class="text-xs text-gray-400 mt-0.5">Precio fijo del artículo en cada lista de precios</p>
        </div>
        <button
          class="px-3 py-1.5 border border-brand-200 text-brand-600 text-xs font-semibold rounded-lg hover:bg-brand-50 transition-colors flex items-center gap-1"
          @click="addPrice"
        >
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
          </svg>
          Agregar precio
        </button>
      </div>

      <div v-if="!prices.length" class="py-10 flex flex-col items-center gap-2.5 border-2 border-dashed border-gray-200 rounded-xl text-gray-400">
        <svg class="w-9 h-9 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z"/>
        </svg>
        <div class="text-center">
          <p class="text-sm font-medium text-gray-500">Sin precios configurados</p>
          <p class="text-xs">Agrega precios para listas de venta o compra</p>
        </div>
        <button class="mt-1 px-4 py-1.5 bg-brand-500 text-white text-xs font-semibold rounded-lg hover:bg-brand-600" @click="addPrice">
          + Agregar precio
        </button>
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="(row, idx) in prices"
          :key="row._id ?? idx"
          class="border rounded-xl p-4 relative group transition-colors"
          :class="row._dirty ? 'border-amber-300 bg-amber-50/40' : 'border-gray-200 bg-white hover:border-gray-300'"
        >
          <span v-if="row._dirty" class="absolute -top-2 left-4 px-2 py-0.5 bg-amber-400 text-white text-xs rounded-full font-medium leading-none pointer-events-none">sin guardar</span>

          <button
            class="absolute top-3 right-3 w-7 h-7 flex items-center justify-center rounded-lg opacity-0 group-hover:opacity-100 hover:bg-red-50 hover:text-red-500 text-gray-300 transition-all"
            @click="$emit('removePrice', idx)"
          >
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
            </svg>
          </button>

          <div class="grid grid-cols-3 gap-3 pr-8">
            <!-- Lista de precios -->
            <div>
              <label class="field-label">Lista de Precios <span class="text-red-400">*</span></label>
              <select v-model="row.price_list" class="field-input" @change="onPriceListChange(row)">
                <option value="">— Seleccionar —</option>
                <optgroup v-if="buyingLists.length" label="Compra">
                  <option v-for="pl in buyingLists" :key="pl.name" :value="pl.name">{{ pl.name }}</option>
                </optgroup>
                <optgroup v-if="sellingLists.length" label="Venta">
                  <option v-for="pl in sellingLists" :key="pl.name" :value="pl.name">{{ pl.name }}</option>
                </optgroup>
              </select>
            </div>

            <!-- Precio — flex prefix para evitar superposición -->
            <div>
              <label class="field-label">Precio <span class="text-red-400">*</span></label>
              <div class="flex items-center border border-gray-200 rounded-md focus-within:ring-2 focus-within:ring-brand-500 bg-white transition-colors">
                <span class="pl-3 pr-1 text-xs font-semibold text-gray-400 flex-shrink-0 select-none">
                  {{ row.currency || '$' }}
                </span>
                <input
                  v-model.number="row.price_list_rate"
                  type="number" min="0" step="0.01"
                  class="flex-1 py-2 pr-3 text-sm focus:outline-none bg-transparent min-w-0"
                  @input="row._dirty = true"
                />
              </div>
            </div>

            <!-- Moneda -->
            <div>
              <label class="field-label">Moneda</label>
              <select v-model="row.currency" class="field-input" @change="row._dirty = true">
                <option value="">— Auto —</option>
                <option v-for="c in currencies" :key="c.name" :value="c.name">{{ c.name }}</option>
              </select>
            </div>

            <!-- UOM — limited to item's own conversion UOMs when available -->
            <div>
              <label class="field-label">UOM</label>
              <select v-model="row.uom" class="field-input" @change="row._dirty = true">
                <option value="">— UOM Stock —</option>
                <option v-for="u in availableUoms" :key="u" :value="u">{{ u }}</option>
              </select>
            </div>

            <!-- Válido desde -->
            <div>
              <label class="field-label">Válido desde</label>
              <input v-model="row.valid_from" type="date" class="field-input" @input="row._dirty = true" />
            </div>

            <!-- Válido hasta -->
            <div>
              <label class="field-label">Válido hasta</label>
              <input v-model="row.valid_upto" type="date" class="field-input" @input="row._dirty = true" />
            </div>

            <!-- Cliente -->
            <div>
              <label class="field-label">Cliente <span class="text-gray-300 font-normal">(específico)</span></label>
              <LinkInput v-model="row.customer" doctype="Customer" placeholder="Dejar vacío = todos" @update:modelValue="row._dirty = true" />
            </div>

            <!-- Proveedor -->
            <div>
              <label class="field-label">Proveedor <span class="text-gray-300 font-normal">(específico)</span></label>
              <LinkInput v-model="row.supplier" doctype="Supplier" placeholder="Dejar vacío = todos" @update:modelValue="row._dirty = true" />
            </div>

            <!-- Nota -->
            <div>
              <label class="field-label">Nota</label>
              <input v-model="row.note" type="text" class="field-input" placeholder="Referencia o nota…" @input="row._dirty = true" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ══════════════════════════════════════════════════════
         SECCIÓN 2 — REGLAS DE PRECIOS
    ═══════════════════════════════════════════════════════ -->
    <div class="border-t border-gray-100 pt-7">
      <div class="flex items-start justify-between mb-4">
        <div>
          <h3 class="text-sm font-semibold text-gray-800">Reglas de Precios</h3>
          <p class="text-xs text-gray-400 mt-0.5">Descuentos o precios especiales por cantidad, cliente o periodo</p>
        </div>
        <button
          class="px-3 py-1.5 border border-purple-200 text-purple-600 text-xs font-semibold rounded-lg hover:bg-purple-50 transition-colors flex items-center gap-1"
          @click="addRule"
        >
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
          </svg>
          Agregar regla
        </button>
      </div>

      <div v-if="!rules.length" class="py-10 flex flex-col items-center gap-2.5 border-2 border-dashed border-gray-200 rounded-xl text-gray-400">
        <svg class="w-9 h-9 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 11h.01M12 11h.01M15 11h.01M4 19h16a2 2 0 002-2V7a2 2 0 00-2-2H4a2 2 0 00-2 2v10a2 2 0 002 2z"/>
        </svg>
        <div class="text-center">
          <p class="text-sm font-medium text-gray-500">Sin reglas de precios</p>
          <p class="text-xs">Ej: 10 % descuento al comprar más de 50 unidades</p>
        </div>
        <button class="mt-1 px-4 py-1.5 bg-purple-500 text-white text-xs font-semibold rounded-lg hover:bg-purple-600" @click="addRule">
          + Agregar regla
        </button>
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="(row, idx) in rules"
          :key="row._id ?? idx"
          class="border rounded-xl p-4 relative group transition-colors"
          :class="row._dirty ? 'border-purple-300 bg-purple-50/30' : 'border-gray-200 bg-white hover:border-gray-300'"
        >
          <span v-if="row._dirty" class="absolute -top-2 left-4 px-2 py-0.5 bg-purple-400 text-white text-xs rounded-full font-medium leading-none pointer-events-none">sin guardar</span>

          <button
            class="absolute top-3 right-3 w-7 h-7 flex items-center justify-center rounded-lg opacity-0 group-hover:opacity-100 hover:bg-red-50 hover:text-red-500 text-gray-300 transition-all"
            @click="$emit('removeRule', idx)"
          >
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
            </svg>
          </button>

          <div class="grid grid-cols-3 gap-3 pr-8">

            <!-- Aplica en (buying/selling checkboxes) -->
            <div class="col-span-3 flex items-center gap-5">
              <label class="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" v-model="row.selling" class="rounded border-gray-300 text-brand-500" @change="row._dirty = true" />
                <span class="text-gray-700 font-medium">Ventas</span>
              </label>
              <label class="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" v-model="row.buying" class="rounded border-gray-300 text-brand-500" @change="row._dirty = true" />
                <span class="text-gray-700 font-medium">Compras</span>
              </label>
              <label class="flex items-center gap-2 text-sm cursor-pointer ml-auto">
                <input type="checkbox" v-model="row.disable" class="rounded border-gray-300 text-red-400" @change="row._dirty = true" />
                <span class="text-gray-500">Deshabilitada</span>
              </label>
            </div>

            <!-- Cant. mínima -->
            <div>
              <label class="field-label">Cant. mínima <span class="text-gray-300 font-normal">(UOM stock)</span></label>
              <input v-model.number="row.min_qty" type="number" min="0" step="1" class="field-input" placeholder="0 = sin mínimo" @input="row._dirty = true" />
            </div>

            <!-- Cant. máxima -->
            <div>
              <label class="field-label">Cant. máxima <span class="text-gray-300 font-normal">(UOM stock)</span></label>
              <input v-model.number="row.max_qty" type="number" min="0" step="1" class="field-input" placeholder="0 = sin máximo" @input="row._dirty = true" />
            </div>

            <!-- Tipo de descuento/precio -->
            <div>
              <label class="field-label">Tipo <span class="text-red-400">*</span></label>
              <select v-model="row.rate_or_discount" class="field-input" @change="row._dirty = true">
                <option value="">— Seleccionar —</option>
                <option value="Rate">Precio fijo</option>
                <option value="Discount Percentage">Descuento %</option>
                <option value="Discount Amount">Descuento monto fijo</option>
              </select>
            </div>

            <!-- Valor — condicional por tipo -->
            <div v-if="row.rate_or_discount === 'Rate'">
              <label class="field-label">Precio fijo <span class="text-red-400">*</span></label>
              <div class="flex items-center border border-gray-200 rounded-md focus-within:ring-2 focus-within:ring-brand-500 bg-white transition-colors">
                <span class="pl-3 pr-1 text-xs font-semibold text-gray-400 flex-shrink-0 select-none">{{ row.currency || '$' }}</span>
                <input v-model.number="row.rate" type="number" min="0" step="0.01" class="flex-1 py-2 pr-3 text-sm focus:outline-none bg-transparent min-w-0" @input="row._dirty = true" />
              </div>
            </div>
            <div v-else-if="row.rate_or_discount === 'Discount Percentage'">
              <label class="field-label">Descuento (%) <span class="text-red-400">*</span></label>
              <div class="flex items-center border border-gray-200 rounded-md focus-within:ring-2 focus-within:ring-brand-500 bg-white transition-colors">
                <input v-model.number="row.discount_percentage" type="number" min="0" max="100" step="0.01" class="flex-1 py-2 pl-3 text-sm focus:outline-none bg-transparent min-w-0" @input="row._dirty = true" />
                <span class="pr-3 pl-1 text-xs font-semibold text-gray-400 flex-shrink-0 select-none">%</span>
              </div>
            </div>
            <div v-else-if="row.rate_or_discount === 'Discount Amount'">
              <label class="field-label">Descuento (monto) <span class="text-red-400">*</span></label>
              <div class="flex items-center border border-gray-200 rounded-md focus-within:ring-2 focus-within:ring-brand-500 bg-white transition-colors">
                <span class="pl-3 pr-1 text-xs font-semibold text-gray-400 flex-shrink-0 select-none">{{ row.currency || '$' }}</span>
                <input v-model.number="row.discount_amount" type="number" min="0" step="0.01" class="flex-1 py-2 pr-3 text-sm focus:outline-none bg-transparent min-w-0" @input="row._dirty = true" />
              </div>
            </div>
            <div v-else class="flex items-end pb-0.5">
              <p class="text-xs text-gray-400 italic">Selecciona el tipo para ingresar el valor</p>
            </div>

            <!-- Moneda -->
            <div>
              <label class="field-label">Moneda <span class="text-red-400">*</span></label>
              <select v-model="row.currency" class="field-input" @change="row._dirty = true">
                <option v-for="c in currencies" :key="c.name" :value="c.name">{{ c.name }}</option>
              </select>
            </div>

            <!-- Para lista de precios -->
            <div>
              <label class="field-label">Para lista de precios</label>
              <select v-model="row.for_price_list" class="field-input" @change="row._dirty = true">
                <option value="">— Todas las listas —</option>
                <option v-for="pl in priceLists" :key="pl.name" :value="pl.name">{{ pl.name }}</option>
              </select>
            </div>

            <!-- Cliente específico -->
            <div>
              <label class="field-label">Cliente <span class="text-gray-300 font-normal">(específico)</span></label>
              <LinkInput v-model="row.customer" doctype="Customer" placeholder="Dejar vacío = todos" @update:modelValue="row._dirty = true" />
            </div>

            <!-- Válido desde -->
            <div>
              <label class="field-label">Válido desde</label>
              <input v-model="row.valid_from" type="date" class="field-input" @input="row._dirty = true" />
            </div>

            <!-- Válido hasta -->
            <div>
              <label class="field-label">Válido hasta</label>
              <input v-model="row.valid_upto" type="date" class="field-input" @input="row._dirty = true" />
            </div>

          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { computed } from "vue";
import LinkInput from "@/components/LinkInput.vue";

const props = defineProps({
  prices:     { type: Array, required: true },
  rules:      { type: Array, required: true },
  priceLists: { type: Array, default: () => [] },
  currencies: { type: Array, default: () => [] },
  uoms:       { type: Array, default: () => [] },
  // Conversion rows {uom, conversion_factor} from the item's own UOM table.
  // When provided and non-empty the price UOM dropdown is restricted to these.
  itemUoms:   { type: Array, default: () => [] },
  defaultCurrency: { type: String, default: "MXN" },
});

const emit = defineEmits(["addPrice", "removePrice", "addRule", "removeRule"]);

const buyingLists  = computed(() => props.priceLists.filter(p => p.buying));
const sellingLists = computed(() => props.priceLists.filter(p => p.selling));

// UOMs available for the price UOM dropdown.
// When the item has its own conversion table use only those;
// otherwise fall back to the full global UOM list.
const availableUoms = computed(() =>
  props.itemUoms.length
    ? props.itemUoms.map(r => r.uom)
    : props.uoms.map(u => u.name)
);

let _id = 0;

function addPrice() {
  emit("addPrice", {
    _id: ++_id, _dirty: true, name: null,
    price_list: "", price_list_rate: 0, currency: props.defaultCurrency,
    uom: "", valid_from: "", valid_upto: "", customer: "", supplier: "", note: "",
  });
}

function addRule() {
  emit("addRule", {
    _id: ++_id, _dirty: true, name: null,
    selling: true, buying: false, disable: false,
    min_qty: 0, max_qty: 0,
    rate_or_discount: "Discount Percentage",
    rate: 0, discount_percentage: 0, discount_amount: 0,
    currency: props.defaultCurrency,
    for_price_list: "", customer: "", valid_from: "", valid_upto: "",
  });
}

function onPriceListChange(row) {
  row._dirty = true;
  const pl = props.priceLists.find(p => p.name === row.price_list);
  if (pl?.currency && !row.currency) row.currency = pl.currency;
}
</script>

<style scoped>
.field-label {
  @apply text-xs font-medium text-gray-500 block mb-1;
}
.field-input {
  @apply w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white transition-colors;
}
</style>
