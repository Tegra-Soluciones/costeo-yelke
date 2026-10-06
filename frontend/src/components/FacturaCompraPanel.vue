<template>
  <!-- Factura del proveedor, como ÚLTIMO paso de su flujo (compra de material o
       maquila): se crea en borrador con lo recibido, se captura el folio y se valida
       ahí mismo. Los datos y acciones viven en la página (pinvDoc/pinvForm). -->
  <div class="space-y-3">
    <!-- Maquila: llegó más trabajo después de la última factura validada. -->
    <div v-if="doc && validated && pendiente > 0" class="flex items-center justify-between gap-3 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
      <p class="text-[12.5px] text-amber-800">Hay trabajo recibido sin facturar: <strong>{{ money(pendiente) }}</strong></p>
      <button :disabled="advancing" class="px-3 py-1.5 text-[12.5px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50" @click="$emit('crear')">Registrar factura de lo pendiente</button>
    </div>

    <div v-if="!doc" class="rounded-lg border border-surface-border bg-white p-4 flex items-center justify-between gap-3 flex-wrap">
      <div>
        <p class="text-[13px] font-medium text-ink">{{ proveedor }}</p>
        <p class="text-[12px] text-ink-muted">Aún no tiene factura de compra. Se crea en borrador con lo recibido{{ pendiente > 0 ? ` (${money(pendiente)})` : '' }}.</p>
      </div>
      <button :disabled="advancing || !habilitado" class="px-4 py-2 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50" @click="$emit('crear')">Crear factura de compra</button>
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
          <div><label class="field-label">Condiciones de pago</label><select v-model="form.payment_terms_template" :disabled="validated" class="field-input mb-3"><option value="">— Sin plantilla —</option><option v-for="p in paymentTermsOptions" :key="p.name" :value="p.name">{{ p.name }}</option></select></div>
        </div>
        <div class="border-t border-surface-border pt-2.5 mb-3 flex flex-wrap gap-x-6 gap-y-1 text-[13px]">
          <span class="text-ink-muted">Subtotal <span class="font-medium text-ink tabular-nums">{{ money(doc.base_net_total) }}</span></span>
          <span v-if="doc.grand_total !== undefined" class="text-ink-muted">Total con impuestos <span class="font-medium text-ink tabular-nums">{{ money(doc.grand_total) }}</span></span>
        </div>
        <div class="flex flex-wrap items-center gap-2">
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
defineProps({
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
});
defineEmits(["crear", "guardar", "validar", "descargar", "imprimir", "ampliar"]);
const money = (v) => (Number(v) || 0).toLocaleString("es-MX", { style: "currency", currency: "MXN" });
</script>
