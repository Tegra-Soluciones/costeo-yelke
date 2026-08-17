<template>
  <!-- Elegir cómo enviar -->
  <div v-if="sendChooser.open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="sendChooser.open = false">
    <div class="bg-white rounded-2xl shadow-xl w-full max-w-xs p-5">
      <p class="text-sm font-semibold text-ink mb-3">Enviar {{ sendChooser.name }}</p>
      <div class="space-y-2">
        <button class="w-full flex items-center gap-3 px-3 py-2.5 border border-surface-border rounded-xl hover:border-brand-300 hover:bg-brand-50/50 transition-colors text-left" @click="onChooseEmail">
          <div class="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
            <svg class="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
          </div>
          <span class="text-[13px] font-medium text-ink">Correo</span>
        </button>
        <button class="w-full flex items-center gap-3 px-3 py-2.5 border border-surface-border rounded-xl hover:border-green-300 hover:bg-green-50/50 transition-colors text-left" @click="onChooseWhatsapp">
          <div class="w-8 h-8 rounded-lg bg-green-50 flex items-center justify-center flex-shrink-0">
            <svg class="w-4 h-4 text-green-600" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
          </div>
          <span class="text-[13px] font-medium text-ink">WhatsApp</span>
        </button>
      </div>
    </div>
  </div>

  <!-- WhatsApp modal -->
  <div v-if="waModal.open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="waModal.open = false">
    <div class="bg-white rounded-2xl shadow-xl w-full max-w-md p-5">
      <p class="text-sm font-semibold text-ink mb-3">Enviar {{ waModal.name }} por WhatsApp</p>
      <label class="field-label">Número de WhatsApp</label>
      <input v-model="waModal.phone" type="tel" class="field-input mb-3" placeholder="+52 55 1234 5678" />
      <label class="field-label">Mensaje</label>
      <textarea v-model="waModal.message" rows="3" class="field-input mb-3"></textarea>
      <p class="text-[11.5px] text-ink-light mb-4">Se descargará el PDF y se abrirá WhatsApp Web — adjúntalo ahí con el botón 📎.</p>
      <div class="flex justify-end gap-2">
        <button class="px-3 py-1.5 text-[13px] text-ink-muted hover:bg-surface-raised rounded-lg" @click="waModal.open = false">Cancelar</button>
        <button :disabled="!waModal.phone" class="px-4 py-1.5 text-[13px] font-medium text-white bg-green-600 hover:bg-green-700 disabled:opacity-50 rounded-lg" @click="onSendWhatsapp">Enviar</button>
      </div>
    </div>
  </div>

  <!-- Send modal -->
  <div v-if="sendModal.open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="sendModal.open = false">
    <div class="bg-white rounded-2xl shadow-xl w-full max-w-md p-5">
      <p class="text-sm font-semibold text-ink mb-3">Enviar {{ sendModal.name }}</p>
      <label class="field-label">Para</label>
      <input v-model="sendModal.recipients" type="text" class="field-input mb-3" placeholder="correo@cliente.com" />
      <label class="field-label">Asunto</label>
      <input v-model="sendModal.subject" type="text" class="field-input mb-3" />
      <label class="field-label">Mensaje</label>
      <textarea v-model="sendModal.message" rows="3" class="field-input mb-4"></textarea>
      <div class="flex justify-end gap-2">
        <button class="px-3 py-1.5 text-[13px] text-ink-muted hover:bg-surface-raised rounded-lg" @click="sendModal.open = false">Cancelar</button>
        <button :disabled="!sendModal.recipients || sendModal.sending" class="px-4 py-1.5 text-[13px] font-medium text-white bg-brand-500 hover:bg-brand-600 disabled:opacity-50 rounded-lg flex items-center gap-2" @click="onSend">
          <svg v-if="sendModal.sending" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
          {{ sendModal.sending ? "Enviando…" : "Enviar" }}
        </button>
      </div>
    </div>
  </div>

  <!-- Assign modal -->
  <div v-if="assignModal.open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="assignModal.open = false">
    <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm p-5">
      <p class="text-sm font-semibold text-ink mb-3">Asignar {{ assignModal.name }}</p>
      <div class="max-h-64 overflow-y-auto border border-surface-border rounded-lg divide-y divide-surface-border mb-4">
        <label v-for="u in users" :key="u.name" class="flex items-center gap-2.5 px-3 py-2 text-[13px] cursor-pointer hover:bg-surface-raised">
          <input type="checkbox" :value="u.name" v-model="assignModal.selected" class="accent-brand-500" />
          <span>{{ u.full_name || u.name }}</span>
        </label>
      </div>
      <div class="flex justify-end gap-2">
        <button class="px-3 py-1.5 text-[13px] text-ink-muted hover:bg-surface-raised rounded-lg" @click="assignModal.open = false">Cancelar</button>
        <button :disabled="!assignModal.selected.length || assignModal.sending" class="px-4 py-1.5 text-[13px] font-medium text-white bg-brand-500 hover:bg-brand-600 disabled:opacity-50 rounded-lg flex items-center gap-2" @click="onAssign">
          <svg v-if="assignModal.sending" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
          {{ assignModal.sending ? "Asignando…" : "Asignar" }}
        </button>
      </div>
    </div>
  </div>

  <!-- PDF modal -->
  <div v-if="pdfModal.open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" @click.self="pdfModal.open = false">
    <div class="bg-white rounded-2xl shadow-xl w-full max-w-4xl flex flex-col overflow-hidden" style="height: 90vh;">
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-surface-border flex-shrink-0">
        <span class="text-sm font-semibold text-ink truncate">{{ pdfModal.name }}</span>
        <div class="flex items-center gap-2 flex-shrink-0">
          <button class="doc-action" @click="onPrint(pdfModal.doctype, pdfModal.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2z"/></svg>Imprimir</button>
          <button class="w-8 h-8 flex items-center justify-center rounded-lg text-ink-muted hover:bg-surface-raised" @click="pdfModal.open = false" aria-label="Cerrar"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button>
        </div>
      </div>
      <iframe :key="'pm' + previewKey" :src="printUrl(pdfModal.doctype, pdfModal.name)" class="flex-1 w-full" style="border: 0;" title="Vista previa del documento"></iframe>
    </div>
  </div>
</template>

<script setup>
// Modales genéricos de "acciones sobre documentos" (enviar, asignar, PDF).
// El estado y la lógica viven en el composable useDocumentActions; este
// componente es solo la vista sobre esos objetos reactivos.
defineProps({
  sendChooser: { type: Object, required: true },
  waModal: { type: Object, required: true },
  sendModal: { type: Object, required: true },
  assignModal: { type: Object, required: true },
  pdfModal: { type: Object, required: true },
  users: { type: Array, default: () => [] },
  previewKey: { type: Number, required: true },
  printUrl: { type: Function, required: true },
  onChooseEmail: { type: Function, required: true },
  onChooseWhatsapp: { type: Function, required: true },
  onSendWhatsapp: { type: Function, required: true },
  onSend: { type: Function, required: true },
  onAssign: { type: Function, required: true },
  onPrint: { type: Function, required: true },
});
</script>
