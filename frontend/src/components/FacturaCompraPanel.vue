<template>
  <!-- Factura del proveedor, como ÚLTIMO paso de su flujo (compra de material o
       maquila): se crea en borrador con lo recibido, se captura el folio y se valida
       ahí mismo. Los datos y acciones viven en la página (pinvDoc/pinvForm). -->
  <div class="space-y-3">
    <!-- Maquila: llegó más trabajo después de la última factura validada. -->
    <div v-if="doc && validated && pendiente > 0" class="flex items-center justify-between gap-3 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
      <p class="text-[12.5px] text-amber-800">Hay trabajo recibido sin facturar: <strong>{{ money(pendiente) }}</strong></p>
      <button v-if="!sinAcciones" :disabled="advancing" class="px-3 py-1.5 text-[12.5px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50" @click="$emit('crear')">Registrar factura de lo pendiente</button>
    </div>

    <div v-if="!doc" class="rounded-lg border border-surface-border bg-white p-4 flex items-center justify-between gap-3 flex-wrap">
      <div>
        <p class="text-[13px] font-medium text-ink">{{ proveedor }}</p>
        <p class="text-[12px] text-ink-muted">Aún no tiene factura de compra. Se crea en borrador con lo recibido{{ pendiente > 0 ? ` (${money(pendiente)})` : '' }}.</p>
      </div>
      <button v-if="!sinAcciones" :disabled="advancing || !habilitado" class="px-4 py-2 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50" @click="$emit('crear')">Crear factura de compra</button>
    </div>

    <div v-else class="flex flex-col lg:flex-row gap-4 items-start">
      <div class="w-full lg:flex-1 lg:min-w-0 rounded-lg border border-surface-border bg-white p-4">
        <div class="flex items-center justify-between mb-3">
          <span class="text-sm font-semibold text-ink">{{ doc.name }} <span class="font-normal text-ink-muted">· {{ doc.supplier_name || doc.supplier }}</span></span>
          <span class="text-[11px] font-semibold px-2 py-0.5 rounded-full" :class="validated ? 'bg-indigo-50 text-indigo-700' : 'bg-amber-50 text-amber-700'">{{ validated ? 'Validada' : 'Borrador' }}</span>
        </div>
        <div class="grid sm:grid-cols-2 gap-x-4">
          <div><label class="field-label">Folio del proveedor (factura)</label><input v-model="form.bill_no" :disabled="validated" class="field-input mb-3" placeholder="Nº de factura del proveedor" /></div>
          <div><label class="field-label">Fecha de factura</label><input v-model="form.posting_date" type="date" :disabled="validated" class="field-input mb-3" /></div>
          <div><label class="field-label">Vencimiento</label><input v-model="form.due_date" type="date" :disabled="validated" class="field-input mb-3" /></div>
          <!-- Factura en moneda extranjera: el tipo de cambio de la FACTURA (el del DOF
               de su fecha) es el que vale para la contabilidad; se captura a mano. -->
          <template v-if="extranjera">
            <div><label class="field-label">Moneda</label><div class="field-input bg-surface-raised/60 mb-3">{{ doc.currency }}</div></div>
            <div>
              <div class="flex items-center justify-between gap-2">
                <label class="field-label">Tipo de cambio de la factura <span class="text-ink-light font-normal">(1 {{ doc.currency }} = ? {{ doc.company_currency }})</span></label>
                <button v-if="!validated" type="button" class="text-[11px] text-brand-600 hover:text-brand-700 mb-1" :disabled="tc.buscando" @click="usarTipoCambioSistema">{{ tc.buscando ? "Buscando…" : "Usar el del sistema" }}</button>
              </div>
              <input v-model.number="form.conversion_rate" type="number" min="0" step="0.0001" :disabled="validated" class="field-input" :class="tc.aviso ? 'mb-1' : 'mb-3'" placeholder="El del CFDI del proveedor" />
              <p v-if="tc.aviso" class="text-[11px] text-red-600 mb-3">{{ tc.aviso }}</p>
            </div>
          </template>
          <div><label class="field-label">Condiciones de pago</label><select v-model="form.payment_terms_template" :disabled="validated" class="field-input mb-3"><option value="">— Sin plantilla —</option><option v-for="p in paymentTermsOptions" :key="p.name" :value="p.name">{{ p.name }}</option></select></div>
        </div>
        <div class="border-t border-surface-border pt-2.5 mb-3 flex flex-wrap gap-x-6 gap-y-1 text-[13px]">
          <span class="text-ink-muted">Subtotal <span class="font-medium text-ink tabular-nums">{{ extranjera ? money(doc.net_total, doc.currency) : money(doc.base_net_total) }}</span></span>
          <span v-if="doc.grand_total !== undefined" class="text-ink-muted">Total con impuestos <span class="font-medium text-ink tabular-nums">{{ money(doc.grand_total, extranjera ? doc.currency : undefined) }}</span></span>
          <span v-if="extranjera" class="text-ink-muted">En {{ doc.company_currency }} <span class="font-medium text-ink tabular-nums">{{ money(doc.base_grand_total, doc.company_currency) }}</span></span>
        </div>
        <div v-if="!sinAcciones" class="flex flex-wrap items-center gap-2">
          <template v-if="!validated">
            <button :disabled="advancing" class="h-8 px-3 text-[13px] font-medium text-ink border border-surface-border rounded-lg hover:bg-surface-raised disabled:opacity-50" @click="$emit('guardar')">Guardar cambios</button>
            <button :disabled="advancing" class="h-8 px-4 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50" @click="$emit('validar')">Validar factura</button>
          </template>
          <button class="doc-action" @click="$emit('descargar')">Descargar</button>
          <button class="doc-action" @click="$emit('imprimir')">Imprimir</button>
          <a class="doc-action" :href="`/app/purchase-invoice/${doc.name}`" target="_blank">Abrir en ERPNext</a>
        </div>
      </div>
      <div class="w-full lg:w-[300px] lg:flex-shrink-0 rounded-lg border border-surface-border bg-white overflow-hidden">
        <div class="flex items-center justify-end px-2 py-1 border-b border-surface-border">
          <button class="doc-action" @click="$emit('ampliar')">Ampliar</button>
        </div>
        <div style="height: 46vh; overflow: auto;">
          <iframe :key="'pinv' + previewKey" :src="previewUrl" style="width: 250%; height: 250%; transform: scale(0.4); transform-origin: top left; border: 0;" title="Vista previa de la factura de compra"></iframe>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive } from "vue";
import { call } from "@/utils/frappe.js";

const props = defineProps({
  doc: { type: Object, default: null },
  form: { type: Object, required: true },
  validated: { type: Boolean, default: false },
  proveedor: { type: String, default: "" },
  pendiente: { type: Number, default: 0 },
  habilitado: { type: Boolean, default: true },
  advancing: { type: Boolean, default: false },
  paymentTermsOptions: { type: Array, default: () => [] },
  previewUrl: { type: String, default: "" },
  previewKey: { type: Number, default: 0 },
  // Dentro de un PanelLateral los botones viven en el PIE del panel, no aquí
  // (regla del diseño v2: las acciones siempre en el mismo lugar). La lógica no
  // se duplica: el pie emite estos mismos eventos.
  sinAcciones: { type: Boolean, default: false },
});
defineEmits(["crear", "guardar", "validar", "descargar", "imprimir", "ampliar"]);
const money = (v, moneda) => (Number(v) || 0).toLocaleString("es-MX", { style: "currency", currency: moneda || props.doc?.company_currency || "MXN" });
const tc = reactive({ buscando: false, aviso: "" });
/** "Usar el del sistema": tipo de cambio de referencia de la fecha de la factura.
 *  Lo normal es capturar el del CFDI del proveedor; esto es la alternativa. */
async function usarTipoCambioSistema() {
  tc.buscando = true;
  try {
    const r = await call("costeo_yelke.api.costeo_api.tipo_cambio_referencia", {
      moneda: props.doc.currency, company: props.doc.company, fecha: props.form.posting_date || props.doc.posting_date || null,
    });
    tc.aviso = r.tipo_cambio ? "" : "El sistema no tiene tipo de cambio para esa fecha; captúralo a mano.";
    if (r.tipo_cambio) props.form.conversion_rate = r.tipo_cambio;
  } finally { tc.buscando = false; }
}
const extranjera = computed(() => !!props.doc?.currency && !!props.doc?.company_currency && props.doc.currency !== props.doc.company_currency);
</script>
