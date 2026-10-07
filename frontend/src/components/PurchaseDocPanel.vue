<template>
  <div class="flex gap-4 items-start">
    <div class="flex-1 min-w-0 bg-white rounded-xl border border-surface-border p-4">
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-2.5">
          <span class="text-sm font-semibold text-ink">{{ doc.name }}</span>
          <DocStatusPill :docstatus="doc.docstatus" :label="validLabel" />
          <span v-if="requiresReview && reviewed" class="text-[11px] font-medium text-brand-700 bg-brand-50 rounded-full px-2 py-0.5 flex items-center gap-1" :title="reviewedAt ? `Revisado el ${reviewedAt}` : ''">
            <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>Revisado{{ reviewedBy ? ` · ${reviewedBy}` : "" }}
          </span>
        </div>
        <a v-if="deskRoute" class="doc-action" :href="`/app/${deskRoute}/${doc.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>ERPNext</a>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <div v-if="doc.supplier">
          <label class="field-label">Proveedor</label>
          <LinkInput
            v-if="!isValidated && editableSupplier"
            :model-value="form.supplier" doctype="Supplier" placeholder="Proveedor" class="text-xs"
            @update:model-value="onSupplierChange"
          />
          <div v-else class="field-input bg-surface-raised/60 truncate">{{ doc.supplier }}</div>
        </div>
        <div v-if="doc.transaction_date"><label class="field-label">Fecha</label><div class="field-input bg-surface-raised/60">{{ doc.transaction_date }}</div></div>
        <div v-if="doc.has_posting_date">
          <label class="field-label">Fecha de recepción</label>
          <input v-if="!isValidated" v-model="form.posting_date" type="date" class="field-input" />
          <div v-else class="field-input bg-surface-raised/60">{{ form.posting_date || '—' }}</div>
        </div>
        <div v-if="doc.has_schedule_date">
          <label class="field-label">Fecha requerida</label>
          <input v-if="!isValidated" v-model="form.schedule_date" type="date" class="field-input" />
          <div v-else class="field-input bg-surface-raised/60">{{ form.schedule_date || '—' }}</div>
        </div>
        <div v-if="doc.has_valid_till">
          <label class="field-label">Vigencia</label>
          <input v-if="!isValidated" v-model="form.valid_till" type="date" class="field-input" />
          <div v-else class="field-input bg-surface-raised/60">{{ form.valid_till || '—' }}</div>
        </div>
        <div v-if="doc.has_payment_terms">
          <label class="field-label">Condiciones de pago</label>
          <select v-if="!isValidated" v-model="form.payment_terms_template" class="field-input"><option value="">— Sin plantilla —</option><option v-for="p in paymentTermsOptions" :key="p.name" :value="p.name">{{ p.name }}</option></select>
          <div v-else class="field-input bg-surface-raised/60 truncate">{{ form.payment_terms_template || '—' }}</div>
        </div>
        <div v-if="doc.has_tc">
          <label class="field-label">Términos y condiciones</label>
          <select v-if="!isValidated" v-model="form.tc_name" class="field-input"><option value="">— Sin términos —</option><option v-for="t in termsOptions" :key="t.name" :value="t.name">{{ t.name }}</option></select>
          <div v-else class="field-input bg-surface-raised/60 truncate">{{ form.tc_name || '—' }}</div>
        </div>
        <div v-if="doc.set_warehouse !== undefined"><label class="field-label">Almacén (aceptado)</label><div class="field-input bg-surface-raised/60 truncate">{{ doc.set_warehouse || (items[0] && items[0].warehouse) || '—' }}</div></div>
        <div v-if="doc.has_shipping">
          <label class="field-label">Costo de envío <span v-if="shippingRequired" class="text-red-400">*</span><span v-else class="text-ink-light font-normal">(flete)</span></label>
          <div v-if="!isValidated" class="flex items-center border rounded-lg focus-within:ring-2 focus-within:ring-brand-500/30 bg-white" :class="shippingRequired && !shippingCaptured ? 'border-red-300 focus-within:border-red-400' : 'border-surface-border focus-within:border-brand-400'">
            <span class="pl-3 pr-1 text-sm text-ink-light select-none">$</span>
            <input v-model.number="form.shipping_cost" type="number" min="0" step="0.01" placeholder="0.00" class="flex-1 min-w-0 py-2 pr-3 text-sm focus:outline-none bg-transparent" />
          </div>
          <div v-else class="field-input bg-surface-raised/60">${{ form.shipping_cost || 0 }}</div>
          <p v-if="shippingRequired && !isValidated" class="text-[11px] text-ink-light mt-1">Obligatorio -- pon 0 si no hubo costo de envío.</p>
        </div>
      </div>

      <table class="w-full text-sm mt-3">
        <thead><tr class="text-left text-xs font-semibold text-ink-light border-b border-surface-border"><th class="py-2">Artículo</th><th class="py-2 w-20 text-right">Cant.</th><th class="py-2 w-16">UOM</th><th v-if="hasRate" class="py-2 w-24 text-right">Precio</th><th v-if="showWarehouse" class="py-2">Almacén</th></tr></thead>
        <tbody>
          <tr v-for="it in filas" :key="it.name" class="border-b border-surface-border/60">
            <td class="py-1.5 pr-2 font-mono text-[12px]">
              {{ it.item_code }}
              <span v-if="it._piezas > 1" class="ml-1.5 font-sans text-[11px] text-ink-muted">· {{ it._piezas }} piezas</span>
            </td>
            <td class="py-1.5 pr-2"><input v-if="!isValidated && editableQty && !agrupaPiezas" v-model.number="it.qty" type="number" min="0" class="field-input text-right" /><span v-else class="block text-right">{{ it.qty }}</span></td>
            <td class="py-1.5 pr-2">
              <LinkInput
                v-if="!isValidated && editableUom && !agrupaPiezas"
                :model-value="it.uom" doctype="UOM" placeholder="UDM" class="w-24 text-xs"
                :options="uomOptionsPorItem[it.item_code] || []"
                extra-action-label="+ Agregar múltiplo de compra"
                @update:model-value="onUomChange(it, $event)"
                @extra-action="abrirMultiploCompra(it)"
              />
              <span v-else class="text-ink-muted text-xs">{{ it.uom }}</span>
            </td>
            <td v-if="hasRate" class="py-1.5 pr-2"><input v-if="!isValidated && it.has_rate && !agrupaPiezas" v-model.number="it.rate" type="number" min="0" step="0.01" class="field-input text-right" /><span v-else class="block text-right">{{ it.rate }}</span></td>
            <td v-if="showWarehouse" class="py-1.5 pr-2 text-ink-muted text-xs">{{ it.warehouse }}</td>
          </tr>
        </tbody>
      </table>
      <p v-if="helpText" class="text-[12px] text-ink-muted mt-2 flex items-center gap-1.5"><svg class="w-3.5 h-3.5 text-green-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>{{ helpText }}</p>

      <!-- `sinAcciones`: dentro de un PanelLateral los botones viven en el PIE del
           panel, no aquí (regla del diseño v2: las acciones siempre en el mismo
           lugar). No se duplica lógica -- el pie emite estos mismos eventos. -->
      <div v-if="!sinAcciones" class="flex items-center gap-2 mt-3 flex-wrap">
        <button v-if="showPullPrices && !isValidated" :disabled="advancing" class="doc-action" @click="emit('pull-prices')"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>Jalar precios</button>
        <button v-if="showPreviewButton" class="doc-action" @click="emit('preview')"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>Vista previa</button>
        <button v-if="showSend" :disabled="advancing" class="doc-action" @click="emit('send')"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>Enviar</button>
        <div class="flex-1"></div>
        <template v-if="!isValidated">
          <button :disabled="advancing" class="doc-action" @click="emit('save')">Guardar</button>
          <button
            v-if="requiresReview && !reviewed"
            :disabled="advancing || !puedeRevisar"
            class="h-8 px-3.5 text-[13px] font-semibold text-brand-700 bg-brand-50 rounded-lg hover:bg-brand-100 disabled:opacity-50 flex items-center gap-1.5"
            :title="puedeRevisar ? 'Marca la revisión intermedia -- requisito antes de Validar' : `Necesitas el rol 'Revisor de Documentos Yelke' para revisar`"
            @click="emit('review')"
          >
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Revisar
          </button>
          <button
            :disabled="advancing || validateBlocked"
            class="h-8 px-3.5 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center gap-1.5"
            :title="validateDisabledReason"
            @click="onValidateClick"
          >
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>{{ validateLabel }}
          </button>
        </template>
        <span v-else-if="validatedText" class="text-[13px] text-green-700 font-medium flex items-center gap-1.5"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>{{ validatedText }}</span>
      </div>
    </div>

    <div v-if="inlinePreviewUrl" class="w-[360px] flex-shrink-0 border border-surface-border rounded-lg overflow-hidden">
      <div style="height: 62vh; overflow: auto;">
        <iframe :key="previewKey" :src="inlinePreviewUrl" style="width: 182%; height: 182%; transform: scale(0.55); transform-origin: top left; border: 0;" title="Vista previa del documento"></iframe>
      </div>
    </div>
  </div>

  <MultiploCompraModal
    :open="multiploModal.open" :item-code="multiploModal.itemCode"
    @cancel="multiploModal.open = false"
    @saved="onMultiploGuardado"
  />
</template>

<script setup>
import { computed, reactive, watch } from "vue";
import DocStatusPill from "./DocStatusPill.vue";
import LinkInput from "./LinkInput.vue";
import MultiploCompraModal from "./MultiploCompraModal.vue";
import { call } from "@/utils/frappe.js";

// Panel genérico para ver/editar CUALQUIER documento de compra-producción (OC, RFQ,
// Presupuesto de proveedor, Recibo de compra, OC de subcontratación...) -- todos
// comparten la misma forma gracias al backend genérico (get_documento_compra /
// guardar_documento_compra). Un componente, muchos usos: evita repetir el mismo
// bloque de cabecera + tabla + acciones cinco veces.
const props = defineProps({
  doc: { type: Object, required: true },
  items: { type: Array, required: true },
  form: { type: Object, required: true },
  deskRoute: { type: String, default: "" },
  paymentTermsOptions: { type: Array, default: () => [] },
  termsOptions: { type: Array, default: () => [] },
  showPullPrices: { type: Boolean, default: false },
  showSend: { type: Boolean, default: true },
  showPreviewButton: { type: Boolean, default: false },
  inlinePreviewUrl: { type: String, default: "" },
  previewKey: { type: [Number, String], default: 0 },
  showWarehouse: { type: Boolean, default: false },
  // Solo la Orden de Compra de materia prima la pone en true -- ahí es donde tiene
  // sentido ajustar la UDM al proveedor real que se terminó eligiendo (puede vender en
  // una unidad distinta a la que se costeó o a la que trae la Solicitud de Material).
  // RFQ, Presupuesto de proveedor, Recibo y las órdenes de subcontratación (que usan
  // este mismo panel) se quedan en el valor por defecto y siguen de solo lectura.
  editableUom: { type: Boolean, default: false },
  // Igual que editableUom: solo la Orden de Compra de materia prima la pone en true --
  // puede hacer falta cambiar de proveedor sobre la marcha (ej. el proveedor del lote 2
  // no tiene material). Al guardar, el precio de cada línea se recalcula solo para el
  // proveedor nuevo (ver guardar_documento_compra / _precio_para_oc).
  editableSupplier: { type: Boolean, default: false },
  // Solo la Orden de Compra de materia prima la pone en false -- ahí la cantidad
  // YA viene bien calculada sola (redondeo a paquete completo + reparto del
  // sobrante entre lotes, ver mr_crear_oc/_es_compra_por_paquete) y respeta el
  // saldo de la Solicitud de Material; editarla a mano aquí se lo saltaría sin que
  // nada lo detecte. El resto de documentos (RFQ, Presupuesto, Recibo,
  // subcontratación) siguen editables como siempre.
  editableQty: { type: Boolean, default: true },
  sinAcciones: { type: Boolean, default: false },
  helpText: { type: String, default: "" },
  validateLabel: { type: String, default: "Validar" },
  validatedText: { type: String, default: "Validada" },
  advancing: { type: Boolean, default: false },
  // Cuando el documento lo requiere (hoy: Recibo de compra), el costo de envío no se
  // puede dejar vacío -- 0 es válido (significa "no hubo"), pero null/"" bloquea el
  // click de Validar antes de siquiera llamar al backend (que también lo bloquea).
  shippingRequired: { type: Boolean, default: false },
  // Doble validación (Enviar -> Revisor -> Aprobador) -- hoy solo la Orden de Compra
  // (materia prima y subcontratada) trae requiresReview=true; para el resto de
  // documentos que usan este mismo panel (RFQ, Presupuesto, Recibo...) estas props
  // se quedan en su default y el botón Validar se comporta exactamente como antes.
  requiresReview: { type: Boolean, default: false },
  reviewed: { type: Boolean, default: false },
  reviewedBy: { type: String, default: "" },
  reviewedAt: { type: String, default: "" },
  puedeRevisar: { type: Boolean, default: true },
  puedeAprobar: { type: Boolean, default: true },
});
const emit = defineEmits(["save", "validate", "review", "pull-prices", "send", "preview", "shipping-missing"]);

const isValidated = computed(() => Number(props.doc.docstatus) === 1);
const hasRate = computed(() => props.items.some((i) => i.has_rate));

// Maquila por pieza: el documento lleva un renglón por PIEZA (frente, espalda,
// puños...) porque es lo que permite moverlas por separado, pero el precio del
// servicio se cobra una sola vez por prenda y viaja completo en una de ellas.
// Mostrar los renglones crudos deja la pantalla con el mismo servicio repetido y
// casi todos en $0. Aquí se agrupan igual que el formato impreso del taller: un
// renglón por servicio y producto, cantidad en PRENDAS y precio por prenda.
// Solo aplica cuando el backend mandó `prendas` (OC de subcontratación).
const agrupaPiezas = computed(() => props.items.some((i) => Number(i.prendas) > 0));
const filas = computed(() => {
  if (!agrupaPiezas.value) return props.items;
  const grupos = new Map();
  for (const it of props.items) {
    const prendas = Number(it.prendas) || 0;
    if (!prendas) { grupos.set(`solo:${it.name}`, { ...it, _piezas: 0 }); continue; }
    const k = `${it.item_code}||${it.producto_terminado || ""}`;
    const g = grupos.get(k);
    if (g) { g._importe += Number(it.amount) || 0; g._piezas += 1; }
    else {
      grupos.set(k, {
        ...it, name: k, qty: prendas, uom: "prendas",
        _importe: Number(it.amount) || 0, _piezas: 1,
      });
    }
  }
  return [...grupos.values()].map((g) => ({
    ...g,
    rate: g._piezas ? Math.round((g._importe / (Number(g.qty) || 1)) * 100) / 100 : g.rate,
  }));
});
const shippingCaptured = computed(() => props.form.shipping_cost !== null && props.form.shipping_cost !== "" && props.form.shipping_cost !== undefined);
const validateDisabledReason = computed(() => {
  if (!props.requiresReview) return "";
  if (!props.reviewed) return "Esta orden necesita revisión antes de poder validarse";
  if (!props.puedeAprobar) return "Necesitas el rol 'Aprobador de Documentos Yelke' para validar";
  return "";
});
const validateBlocked = computed(() => !!validateDisabledReason.value);
function onValidateClick() {
  if (validateBlocked.value) return;
  if (props.shippingRequired && !shippingCaptured.value) {
    emit("shipping-missing");
    return;
  }
  emit("validate");
}
// "Enviado" -- solo aplica a documentos con enviado_el (por ahora, Purchase Order,
// vía el botón Enviar) -- para el resto (RFQ, SQ, recibos) el campo simplemente no
// viene y este estado nunca se muestra.
const validLabel = computed(() => {
  if (!isValidated.value) return "Borrador";
  return props.doc.enviado_el ? "Enviado" : "Validado";
});

// El selector de UDM de una línea SOLO debe ofrecer las UDM que ese artículo ya
// tiene dadas de alta (get_item_uoms) -- no el catálogo completo de UDM del
// sistema (ver LinkInput `options`, que desactiva la búsqueda en servidor). Un
// artículo nuevo en la lista dispara la carga sola (watch de abajo); "+ Agregar
// múltiplo de compra" la refresca al agregar una.
const uomOptionsPorItem = reactive({});
async function cargarUomsItem(itemCode, forzar = false) {
  if (!itemCode || (!forzar && uomOptionsPorItem[itemCode])) return;
  try {
    const r = await call("costeo_yelke.api.item_api.get_item_uoms", { item_code: itemCode });
    uomOptionsPorItem[itemCode] = (r.uoms || []).map((u) => ({ value: u.uom, description: u.uom }));
  } catch {
    uomOptionsPorItem[itemCode] = [];
  }
}
watch(() => props.items, (items) => {
  (items || []).forEach((it) => cargarUomsItem(it.item_code));
}, { immediate: true, deep: false });

// Recálculo instantáneo al cambiar UDM o proveedor -- sin esto había que dar clic
// en Guardar para ver la cantidad/precio nuevos (guardar_documento_compra hacía la
// cuenta, pero solo al guardar). preview_conversion_uom_oc usa exactamente la
// misma lógica que el guardado real (_convertir_uom_compra / _precio_para_oc), así
// que lo que se ve aquí es lo mismo que va a quedar guardado.
// Hace la conversión de verdad (llama al servidor) y aplica el resultado a la fila
// -- separado de onUomChange para que también se pueda forzar SIN el atajo de
// "misma UDM que ya tenía" (ver onMultiploGuardado: corregir el factor de un
// múltiplo que la fila YA tiene seleccionado también debe recalcular, aunque la
// UDM en sí no haya cambiado de nombre -- si no, la fila se quedaba con la
// cantidad vieja calculada con el factor equivocado).
async function aplicarPreviewUom(row, nuevoUom) {
  row.uom = nuevoUom; // se ve el cambio de inmediato; se corrige abajo si hace falta
  try {
    const r = await call("costeo_yelke.api.costeo_api.preview_conversion_uom_oc", {
      item_code: row.item_code, qty: row.qty, conversion_factor_actual: row.conversion_factor || 1,
      nuevo_uom: nuevoUom, supplier: props.form.supplier || props.doc.supplier,
      company: props.doc.company, costeo: props.doc.costeo,
    });
    row.qty = r.qty;
    row.conversion_factor = r.conversion_factor;
    if (r.rate !== null && r.rate !== undefined && filaTienePrecio(row)) row.rate = r.rate;
  } catch { /* si falla la vista previa, se recalcula igual de bien al Guardar */ }
}
async function onUomChange(row, nuevoUom) {
  if (!nuevoUom || nuevoUom === row.uom) { row.uom = nuevoUom; return; }
  await aplicarPreviewUom(row, nuevoUom);
}
function filaTienePrecio(row) { return row.has_rate !== false; }

// Cambiar de proveedor recalcula el precio sugerido de TODAS las líneas (la
// cantidad no depende del proveedor, solo el precio) -- misma razón que arriba.
async function onSupplierChange(nuevoSupplier) {
  props.form.supplier = nuevoSupplier;
  if (!nuevoSupplier) return;
  for (const row of props.items) {
    if (!filaTienePrecio(row)) continue;
    try {
      const r = await call("costeo_yelke.api.costeo_api.preview_conversion_uom_oc", {
        item_code: row.item_code, qty: row.qty, conversion_factor_actual: row.conversion_factor || 1,
        nuevo_uom: row.uom, supplier: nuevoSupplier, company: props.doc.company, costeo: props.doc.costeo,
      });
      if (r.rate !== null && r.rate !== undefined) row.rate = r.rate;
    } catch { /* se recalcula igual de bien al Guardar */ }
  }
}

// "+ Agregar múltiplo de compra" (ver LinkInput extra-action-label) -- abre el
// modal para dar de alta una conversión de UDM que se le haya pasado al artículo,
// sin salir de la OC. Al guardar, esa línea se queda seleccionada en la UDM nueva.
const multiploModal = reactive({ open: false, itemCode: "", row: null });
function abrirMultiploCompra(row) {
  multiploModal.itemCode = row.item_code;
  multiploModal.row = row;
  multiploModal.open = true;
}
function onMultiploGuardado(nuevaUom) {
  cargarUomsItem(multiploModal.itemCode, true); // refresca la lista con la recién agregada
  // Siempre recalcula, aunque la fila ya estuviera en esta misma UDM -- lo que
  // cambió es el FACTOR del múltiplo (ej. el usuario lo corrigió), no el nombre
  // de la UDM, así que el atajo de onUomChange no debe aplicar aquí.
  if (multiploModal.row) aplicarPreviewUom(multiploModal.row, nuevaUom);
  multiploModal.open = false;
}
</script>
