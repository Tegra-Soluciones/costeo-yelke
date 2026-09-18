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
        <div v-if="doc.supplier"><label class="field-label">Proveedor</label><div class="field-input bg-surface-raised/60 truncate">{{ doc.supplier }}</div></div>
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
          <tr v-for="it in items" :key="it.name" class="border-b border-surface-border/60">
            <td class="py-1.5 pr-2 font-mono text-[12px]">{{ it.item_code }}</td>
            <td class="py-1.5 pr-2"><input v-if="!isValidated" v-model.number="it.qty" type="number" min="0" class="field-input text-right" /><span v-else class="block text-right">{{ it.qty }}</span></td>
            <td class="py-1.5 pr-2 text-ink-muted text-xs">{{ it.uom }}</td>
            <td v-if="hasRate" class="py-1.5 pr-2"><input v-if="!isValidated && it.has_rate" v-model.number="it.rate" type="number" min="0" step="0.01" class="field-input text-right" /><span v-else class="block text-right">{{ it.rate }}</span></td>
            <td v-if="showWarehouse" class="py-1.5 pr-2 text-ink-muted text-xs">{{ it.warehouse }}</td>
          </tr>
        </tbody>
      </table>
      <p v-if="helpText" class="text-[12px] text-ink-muted mt-2 flex items-center gap-1.5"><svg class="w-3.5 h-3.5 text-green-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>{{ helpText }}</p>

      <div class="flex items-center gap-2 mt-3 flex-wrap">
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
</template>

<script setup>
import { computed } from "vue";
import DocStatusPill from "./DocStatusPill.vue";

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
</script>
