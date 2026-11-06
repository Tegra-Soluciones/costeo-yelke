<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="$emit('cancel')">
    <div class="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-5">
      <p class="text-sm font-semibold text-ink">{{ soloTallas ? "Tallas extra de " + finishedItemText : "Dar de alta el producto terminado" }}</p>
      <p v-if="soloTallas" class="text-[12px] text-ink-muted mt-0.5 mb-4">
        El producto ya está dado de alta. Sus tallas extra se crean ahora, cada una con su propio precio.
      </p>
      <template v-if="!soloTallas">
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
        <div v-if="existingPreview" class="mb-3">
          <label class="field-label">Imagen del producto <span class="text-ink-light font-normal">(opcional)</span></label>
          <div class="flex items-center gap-3">
            <button type="button" class="w-16 h-16 flex-shrink-0 rounded-lg border border-surface-border bg-surface-raised overflow-hidden flex items-center justify-center text-zinc-300" title="Subir o cambiar la imagen" @click="dialogoImagen = true">
              <img v-if="imagenActual" :src="imagenActual" class="w-full h-full object-cover" alt="" />
              <svg v-else class="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round" aria-hidden="true"><path d="M8.5 3.5L4 5.8 2.5 10.2l3 1.3L6.3 10V20.5h11.4V10l.8 1.5 3-1.3L20 5.8l-4.5-2.3c-.6 1.6-1.9 2.5-3.5 2.5s-2.9-.9-3.5-2.5z"/></svg>
            </button>
            <div class="space-y-1">
              <button type="button" class="p-btn-secondary h-8 text-[12.5px]" @click="dialogoImagen = true">{{ imagenActual ? "Cambiar imagen" : "Subir imagen" }}</button>
              <button v-if="imagenActual" type="button" class="block text-[12px] text-ink-muted hover:text-red-600" @click="ponerImagen('')">Quitar</button>
            </div>
          </div>
          <p class="text-[10.5px] text-ink-light mt-1">Se guarda en el artículo y en el producto del costeo.</p>
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
          <input v-model="form.item_code" v-mayus class="field-input" placeholder="Ej: YLK-CHA-TIM" :class="errors.item_code ? 'border-red-400' : ''" />
        </div>

        <div class="mb-3">
          <label class="field-label">Nombre <span class="text-red-400">*</span></label>
          <input v-model="form.item_name" v-mayus class="field-input" placeholder="Nombre del producto" :class="errors.item_name ? 'border-red-400' : ''" />
        </div>

        <div class="mb-3">
          <label class="field-label">UOM <span class="text-red-400">*</span></label>
          <LinkInput v-model="form.stock_uom" doctype="UOM" placeholder="Unidad de medida…" :error="!!errors.stock_uom" />
        </div>

        <div class="mb-3">
          <label class="field-label">Imagen del producto <span class="text-ink-light font-normal">(opcional)</span></label>
          <div class="flex items-center gap-3">
            <button type="button" class="w-16 h-16 flex-shrink-0 rounded-lg border border-surface-border bg-surface-raised overflow-hidden flex items-center justify-center text-zinc-300" title="Subir o cambiar la imagen" @click="dialogoImagen = true">
              <img v-if="imagenActual" :src="imagenActual" class="w-full h-full object-cover" alt="" />
              <svg v-else class="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round" aria-hidden="true"><path d="M8.5 3.5L4 5.8 2.5 10.2l3 1.3L6.3 10V20.5h11.4V10l.8 1.5 3-1.3L20 5.8l-4.5-2.3c-.6 1.6-1.9 2.5-3.5 2.5s-2.9-.9-3.5-2.5z"/></svg>
            </button>
            <div class="space-y-1">
              <button type="button" class="p-btn-secondary h-8 text-[12.5px]" @click="dialogoImagen = true">{{ imagenActual ? "Cambiar imagen" : "Subir imagen" }}</button>
              <button v-if="imagenActual" type="button" class="block text-[12px] text-ink-muted hover:text-red-600" @click="ponerImagen('')">Quitar</button>
            </div>
          </div>
          <p class="text-[10.5px] text-ink-light mt-1">Se guarda en el artículo y en el producto del costeo.</p>
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
            <div class="flex items-center border rounded-lg bg-white min-w-0" :class="bajoPiso(r, form.precio_venta) ? 'border-red-400' : 'border-surface-border'">
              <span class="pl-2 text-xs text-ink-light select-none">$</span>
              <input v-model.number="r.rate" type="number" min="0" step="0.01" class="flex-1 min-w-0 py-2 pr-2 pl-1 text-sm focus:outline-none bg-transparent" />
            </div>
            <button class="h-7 w-7 flex items-center justify-center text-ink-muted hover:bg-red-50 hover:text-red-500 rounded-lg" @click="form.rangos.splice(idx, 1)">
              <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
            </button>
          </div>
          <p v-if="form.rangos.some(r => bajoPiso(r, form.precio_venta))" class="text-[11px] text-red-600 mt-1">Ningún precio puede ser menor al del costeo (${{ (form.precio_venta || 0).toFixed(2) }}).</p>
          <button class="text-[12px] font-medium text-brand-600 hover:text-brand-700 mt-1" @click="addRango">+ Agregar rango</button>
        </div>
      </template>
      </template>

      <!-- Tallas extra de este producto: se dan de alta solas junto con él, cada una con
           su propio precio; aquí se le puede capturar su propia escala por volumen. -->
      <div v-if="tallasExtra.length" class="mb-3 border-t border-surface-border pt-3">
        <p class="text-[13px] font-medium text-ink mb-0.5">Tallas extra</p>
        <p class="text-[11px] text-ink-light mb-2">Se dan de alta solas con su propio precio. La escala por volumen de cada talla es opcional y se aplica según la cantidad de su propia línea.</p>
        <div v-for="t in tallasExtra" :key="t.text" class="border border-surface-border rounded-lg mb-2 overflow-hidden">
          <div class="flex items-center gap-2 px-3 py-2 bg-white">
            <div class="flex-1 min-w-0">
              <p class="text-[12.5px] font-medium text-ink truncate">{{ t.label || t.text }}</p>
              <p class="text-[11px] text-ink-light">Precio ${{ (t.precio || 0).toFixed(2) }}<template v-if="rangosConPrecio(t).length"> · {{ rangosConPrecio(t).length }} rango(s) por volumen</template></p>
            </div>
            <button type="button" class="text-[12px] font-medium text-brand-600 hover:text-brand-700 flex-shrink-0" @click="toggleTalla(t)">
              {{ tallasForm[t.text]?.abierto ? "Ocultar" : "Precios por volumen" }}
            </button>
          </div>
          <div v-if="tallasForm[t.text]?.abierto" class="p-3 bg-surface-raised/40 border-t border-surface-border">
            <div class="grid grid-cols-[1fr_1fr_1fr_28px] gap-2 mb-1.5 px-0.5">
              <span class="text-[11px] font-medium text-ink-muted">Desde (cant.)</span>
              <span class="text-[11px] font-medium text-ink-muted">Hasta (cant.)</span>
              <span class="text-[11px] font-medium text-ink-muted">Precio</span>
              <span></span>
            </div>
            <div v-for="(r, idx) in tallasForm[t.text].rangos" :key="idx" class="grid grid-cols-[1fr_1fr_1fr_28px] gap-2 items-center mb-1.5">
              <input v-model.number="r.min_qty" type="number" min="0" step="1" class="field-input min-w-0" />
              <input v-model.number="r.max_qty" type="number" min="0" step="1" class="field-input min-w-0" placeholder="Sin tope" />
              <div class="flex items-center border rounded-lg bg-white min-w-0" :class="bajoPiso(r, t.precio) ? 'border-red-400' : 'border-surface-border'">
                <span class="pl-2 text-xs text-ink-light select-none">$</span>
                <input v-model.number="r.rate" type="number" min="0" step="0.01" class="flex-1 min-w-0 py-2 pr-2 pl-1 text-sm focus:outline-none bg-transparent" />
              </div>
              <button class="h-7 w-7 flex items-center justify-center text-ink-muted hover:bg-red-50 hover:text-red-500 rounded-lg" @click="tallasForm[t.text].rangos.splice(idx, 1)">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
              </button>
            </div>
            <p v-if="tallasForm[t.text].rangos.some(r => bajoPiso(r, t.precio))" class="text-[11px] text-red-600 mt-1">Ningún precio puede ser menor al del costeo (${{ (t.precio || 0).toFixed(2) }}).</p>
            <button class="text-[12px] font-medium text-brand-600 hover:text-brand-700 mt-1" @click="addRangoTalla(t)">+ Agregar rango</button>
          </div>
        </div>
      </div>

      <p v-if="!soloTallas" class="text-[11px] text-ink-light bg-surface-raised rounded-lg px-3 py-2 mb-1">
        <template v-if="mode === 'existing'">El producto quedará vinculado a este renglón del costeo.</template>
        <template v-else>Se asignará automáticamente a <strong>{{ company || '—' }}</strong> · Lista de precios: <strong>Venta estándar</strong>.</template>
      </p>

      <div class="flex gap-2 justify-end mt-4">
        <button class="px-3 py-1.5 text-[13px] text-ink-muted hover:bg-surface-raised rounded-lg" @click="$emit('cancel')">Cancelar</button>
        <button :disabled="saving || hayPrecioBajoPiso()" class="px-4 py-1.5 text-[13px] font-medium text-white bg-brand-500 hover:bg-brand-600 disabled:opacity-50 rounded-lg flex items-center gap-2" @click="onConfirm">
          <svg v-if="saving" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
          {{ saving ? (mode === 'existing' ? "Vinculando…" : "Creando…") : soloTallas ? "Crear tallas y continuar" : (mode === 'existing' ? "Vincular y continuar" : "Crear y continuar") }}
        </button>
      </div>
    </div>
    <DialogoImagen
      :abierto="dialogoImagen" :producto="mode === 'existing' ? (existingPreview?.item_name || '') : (form.item_name || finishedItemText)"
      :actual="imagenActual" doctype="Costeo" :docname="costeo"
      @cerrar="dialogoImagen = false" @elegida="ponerImagen"
    />
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import DialogoImagen from "@/components/DialogoImagen.vue";
import LinkInput from "@/components/LinkInput.vue";
import { call, searchLink, fuzzyQuery } from "@/utils/frappe.js";

const props = defineProps({
  open: { type: Boolean, default: false },
  finishedItemText: { type: String, default: "" },
  suggestedPrice: { type: Number, default: 0 },
  suggestedDescription: { type: String, default: "" },
  suggestedImage: { type: String, default: "" },
  // Variante de talla: su código sale del artículo base (lo calcula la página) y no
  // se le sugiere "usar existente" -- el parecido más cercano sería su propio base.
  suggestedCode: { type: String, default: "" },
  esVariante: { type: Boolean, default: false },
  // Variantes de talla de este producto aún sin artículo: [{text, label, precio}].
  tallasExtra: { type: Array, default: () => [] },
  // El producto base ya es artículo: el modal solo pide la escala de sus tallas extra.
  soloTallas: { type: Boolean, default: false },
  company: { type: String, default: "" },
  // Costeo al que se liga la imagen mientras el artículo aún no existe (DialogoImagen);
  // el servidor la liga después al artículo (costeo_api._imagen_del_producto).
  costeo: { type: String, default: "" },
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

// Imagen del producto: en "nuevo" la del formulario; en "existente" la del artículo
// elegido (cambiarla actualiza la del artículo).
const dialogoImagen = ref(false);
const imagenExistente = ref("");
const imagenActual = computed(() => (mode.value === "existing" ? imagenExistente.value : form.image));
function ponerImagen(url) {
  if (mode.value === "existing") imagenExistente.value = url || "";
  else form.image = url || "";
  dialogoImagen.value = false;
}
const tallasForm = reactive({});
// Rangos del producto base cuando YA es artículo (modo solo tallas): se leen de sus
// reglas de precio para proponer los mismos "desde/hasta" en cada talla.
const rangosBase = ref([]);
async function cargarRangosBase(itemCode) {
  try {
    const reglas = await call("costeo_yelke.api.item_api.get_pricing_rules", { item_code: itemCode });
    rangosBase.value = (reglas || []).filter(r => r.selling && !r.disable && r.rate_or_discount === "Rate")
      .map(r => ({ min_qty: r.min_qty, max_qty: r.max_qty || "" }));
  } catch { rangosBase.value = []; }
}

// Al abrir la escala de una talla se proponen los mismos rangos (desde/hasta) que se
// capturaron para el producto base, con el precio vacío: el precio lo pone el usuario.
function toggleTalla(t) {
  const f = tallasForm[t.text];
  f.abierto = !f.abierto;
  if (f.abierto && !f.rangos.length) {
    const base = form.conPrecioVolumen && form.rangos.length ? form.rangos : rangosBase.value;
    f.rangos = base.length
      ? base.map(r => ({ min_qty: r.min_qty, max_qty: r.max_qty, rate: null }))
      : [{ min_qty: 1, max_qty: "", rate: null }];
  }
}
function addRangoTalla(t) {
  const rangos = tallasForm[t.text].rangos;
  const prevMax = rangos.length ? rangos[rangos.length - 1].max_qty : 0;
  rangos.push({ min_qty: (prevMax || 0) + 1 || 1, max_qty: "", rate: null });
}
const rangosConPrecio = (t) => (tallasForm[t.text]?.rangos || []).filter(r => r.rate > 0);
function tallasPrecios() {
  return Object.fromEntries(props.tallasExtra
    .map(t => [t.text, rangosConPrecio(t).map(r => ({ rate_or_discount: "Rate", min_qty: r.min_qty || 0, max_qty: r.max_qty || 0, rate: r.rate }))])
    .filter(([, reglas]) => reglas.length));
}

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
    imagenExistente.value = doc?.image || "";
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
    .slice(0, 30)
    // Después de recortar: si el corte cae en un guion, no se deja colgando.
    .replace(/^-+|-+$/g, "");
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
  if (!props.esVariante) autoSuggestExisting(props.finishedItemText);
  form.item_code = props.suggestedCode || suggestCode(props.finishedItemText);
  form.item_name = props.finishedItemText;
  form.stock_uom = "Pieza"; // default -- la mayoría de los productos terminados se venden por pieza, pero se puede cambiar libremente
  form.precio_venta = props.suggestedPrice || 0;
  form.conPrecioVolumen = false;
  form.rangos = [];
  form.description = props.suggestedDescription || "";
  form.image = props.suggestedImage || "";
  Object.keys(tallasForm).forEach(k => delete tallasForm[k]);
  props.tallasExtra.forEach(t => { tallasForm[t.text] = { abierto: false, rangos: [] }; });
  rangosBase.value = [];
  if (props.soloTallas) cargarRangosBase(props.finishedItemText);
  errors.item_code = false; errors.item_name = false; errors.stock_uom = false; errors.existing = false;
});

// La tabla por volumen nunca baja del precio de venta del costeo (el piso): ni en el
// producto base ni en las tallas extra. El servidor lo vuelve a revisar.
function bajoPiso(r, piso) {
  return Number(r.rate) > 0 && Number(piso) > 0 && Math.round(Number(r.rate) * 100) < Math.round(Number(piso) * 100);
}
function hayPrecioBajoPiso() {
  if (form.conPrecioVolumen && !props.soloTallas && form.rangos.some(r => bajoPiso(r, form.precio_venta))) return true;
  return props.tallasExtra.some(t => (tallasForm[t.text]?.rangos || []).some(r => bajoPiso(r, t.precio)));
}

function onConfirm() {
  if (hayPrecioBajoPiso()) return;
  if (props.soloTallas) {
    emit("confirm", { solo_tallas: true, tallas_precios: tallasPrecios() });
    return;
  }
  if (mode.value === "existing") {
    errors.existing = !existingItemCode.value;
    if (errors.existing) return;
    emit("confirm", {
      item_code: existingItemCode.value,
      item_name: existingPreview.value?.item_name || existingItemCode.value,
      stock_uom: existingPreview.value?.stock_uom || "",
      description: null,
      image: imagenExistente.value || null,
      precio_venta: form.precio_venta || 0,
      pricing_rules: [],
      tallas_precios: tallasPrecios(),
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
    tallas_precios: tallasPrecios(),
  });
}
</script>

<style scoped>
.field-label { @apply text-xs font-medium text-ink-muted block mb-1; }
.field-input { @apply w-full text-sm border border-surface-border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400 bg-white transition-colors; }
</style>
