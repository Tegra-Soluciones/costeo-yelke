<template>
  <div class="bg-white rounded-xl border border-surface-border p-4">
    <p class="section-title mb-1">Orden de manufactura · instrucciones de confección</p>
    <p class="text-[12px] text-ink-muted mb-3">Se guarda junto con la orden, con el botón "Guardar" de arriba.</p>

    <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-2">Info general</p>
    <div class="grid grid-cols-4 gap-3 mb-4">
      <div><label class="field-label">Modelo</label><input v-model="general.om_modelo" :disabled="disabled" class="field-input" /></div>
      <div><label class="field-label">Tela</label><input v-model="general.om_tela" :disabled="disabled" class="field-input" /></div>
      <div><label class="field-label">Color</label><input v-model="general.om_color" :disabled="disabled" class="field-input" /></div>
      <div><label class="field-label">Color principal</label><input v-model="general.om_color_principal" :disabled="disabled" class="field-input" /></div>
      <div><label class="field-label">Forro</label><input v-model="general.om_forro" :disabled="disabled" class="field-input" /></div>
      <div><label class="field-label">Combinación</label><input v-model="general.om_combinacion" :disabled="disabled" class="field-input" /></div>
      <div><label class="field-label">Ubicación</label><input v-model="general.om_ubicacion" :disabled="disabled" class="field-input" /></div>
      <div><label class="field-label">Aberturas</label><input v-model.number="general.om_aberturas" type="number" :disabled="disabled" class="field-input" /></div>
      <div><label class="field-label">Fecha requerida</label><input v-model="general.om_fecha_requerida" type="date" :disabled="disabled" class="field-input" /></div>
    </div>
    <div class="flex items-center gap-4 mb-4 text-[13px]">
      <label class="flex items-center gap-1.5"><input type="checkbox" v-model="general.om_bordado" :true-value="1" :false-value="0" :disabled="disabled" class="accent-brand-500" />Bordado</label>
      <label class="flex items-center gap-1.5"><input type="checkbox" v-model="general.om_estampado" :true-value="1" :false-value="0" :disabled="disabled" class="accent-brand-500" />Estampado</label>
      <label class="flex items-center gap-1.5"><input type="checkbox" v-model="general.om_sublimado" :true-value="1" :false-value="0" :disabled="disabled" class="accent-brand-500" />Sublimado</label>
      <label class="flex items-center gap-1.5"><input type="checkbox" v-model="general.om_reflejante" :true-value="1" :false-value="0" :disabled="disabled" class="accent-brand-500" />Reflejante</label>
    </div>

    <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-1">Tallas caballero</p>
    <div class="overflow-x-auto mb-4">
      <table class="text-sm">
        <thead><tr class="text-xs text-ink-light"><th class="px-2 py-1 text-left">Línea</th><th v-for="s in OM_CAB" :key="s" class="px-1 py-1 w-12 text-center">{{ s.slice(1) }}</th><th class="px-2 py-1">Total</th></tr></thead>
        <tbody>
          <tr v-for="row in omCab" :key="row.name || 'c'">
            <td class="px-2 py-1 text-ink-muted text-xs">{{ row.linea || 'Cantidad' }}</td>
            <td v-for="s in OM_CAB" :key="s" class="px-0.5 py-1"><input v-model.number="row[s]" type="number" min="0" :disabled="disabled" class="field-input text-center px-1" /></td>
            <td class="px-2 py-1 text-right font-medium">{{ tallaTotal(row, OM_CAB) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-1">Tallas dama</p>
    <div class="overflow-x-auto mb-4">
      <table class="text-sm">
        <thead><tr class="text-xs text-ink-light"><th class="px-2 py-1 text-left">Línea</th><th v-for="s in OM_DAMA" :key="s" class="px-1 py-1 w-12 text-center">{{ s.slice(1) }}</th><th class="px-2 py-1">Total</th></tr></thead>
        <tbody>
          <tr v-for="row in omDama" :key="row.name || 'd'">
            <td class="px-2 py-1 text-ink-muted text-xs">{{ row.linea || 'Cantidad' }}</td>
            <td v-for="s in OM_DAMA" :key="s" class="px-0.5 py-1"><input v-model.number="row[s]" type="number" min="0" :disabled="disabled" class="field-input text-center px-1" /></td>
            <td class="px-2 py-1 text-right font-medium">{{ tallaTotal(row, OM_DAMA) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="flex items-center justify-between mb-1">
      <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wider">Procesos</p>
      <button v-if="!disabled" class="add-link" @click="$emit('add-proceso')"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>Proceso</button>
    </div>
    <div v-for="(p, i) in omProc" :key="i" class="grid grid-cols-4 gap-2 mb-1.5 items-center">
      <input v-model="p.nombre_proceso" placeholder="Nombre del proceso" :disabled="disabled" class="field-input" />
      <input v-model="p.ubicacion" placeholder="Ubicación" :disabled="disabled" class="field-input" />
      <input v-model="p.colores" placeholder="Colores" :disabled="disabled" class="field-input" />
      <button v-if="!disabled" class="del-btn justify-self-start" @click="$emit('remove-proceso', i)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button>
    </div>
    <p v-if="!omProc.length" class="prod-empty mb-2">Sin procesos.</p>

    <label class="field-label mt-3">Observaciones</label>
    <textarea v-model="general.om_observaciones" rows="2" :disabled="disabled" class="field-input"></textarea>

    <!-- Tablas de medidas flexibles -->
    <div class="flex items-center justify-between mt-4 mb-1.5 flex-wrap gap-2">
      <label class="field-label">Tablas de medidas</label>
      <div v-if="!disabled" class="flex items-center gap-2">
        <select
          class="field-input text-[12.5px] py-1"
          :value="''"
          @change="$event.target.value && $emit('add-tabla-plantilla', $event.target.value); $event.target.value = ''"
        >
          <option value="">Usar plantilla…</option>
          <option v-for="t in medidasTemplates" :key="t.key" :value="t.key">{{ t.label }}</option>
        </select>
        <button class="add-link" @click="$emit('add-tabla')"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>Tabla en blanco</button>
      </div>
    </div>
    <p v-if="!omTablas.length" class="prod-empty mb-2">Sin tablas de medidas.</p>
    <div v-for="(t, ti) in omTablas" :key="'t'+ti" class="border border-surface-border rounded-lg p-3 mb-2.5 bg-surface-raised/40">
      <div class="flex items-center gap-2 mb-2 flex-wrap">
        <input v-model="t.name" placeholder="Nombre de la tabla" :disabled="disabled" class="field-input flex-1 min-w-[140px]" />
        <input v-model="t.unit" placeholder="Unidad (ej. cm)" :disabled="disabled" class="field-input w-28" />
        <button v-if="!disabled" class="del-btn" @click="$emit('remove-tabla', ti)" title="Eliminar tabla"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-[13px]">
          <thead>
            <tr>
              <th v-for="(c, ci) in t.columns" :key="c" class="p-1 text-center font-medium text-ink-muted">
                <div class="flex items-center justify-center gap-1">
                  <span>{{ ci + 1 }}</span>
                  <button v-if="!disabled" class="text-ink-muted hover:text-red-500" @click="$emit('remove-columna', t, ci)" title="Eliminar columna"><svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button>
                </div>
              </th>
              <th class="w-6"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(r, ri) in t.rows" :key="r.id">
              <td v-for="c in t.columns" :key="c" class="p-0.5"><input v-model="r.cells[c]" :disabled="disabled" class="field-input text-center" /></td>
              <td class="p-0.5 text-center"><button v-if="!disabled" class="text-ink-muted hover:text-red-500" @click="$emit('remove-fila', t, ri)" title="Eliminar fila"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="!disabled" class="flex items-center gap-3 mt-2">
        <button class="add-link" @click="$emit('add-columna', t)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>Columna</button>
        <button class="add-link" @click="$emit('add-fila', t)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>Fila</button>
      </div>
    </div>

    <!-- Diagramas / archivos -->
    <div class="flex items-center justify-between mt-4 mb-1.5">
      <label class="field-label">Diagramas / imágenes de referencia</label>
      <label v-if="!disabled" class="add-link cursor-pointer">
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
        {{ uploading ? 'Subiendo…' : 'Imagen / archivo' }}
        <input type="file" multiple accept="image/*,.pdf" class="hidden" :disabled="uploading" @change="$emit('file', $event)" />
      </label>
    </div>
    <p v-if="!omArchivos.length" class="prod-empty mb-2">Sin imágenes ni archivos.</p>
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 mb-2">
      <div v-for="(a, i) in omArchivos" :key="'a'+i" class="flex gap-2 border border-surface-border rounded-lg p-2 bg-surface-raised/40">
        <a :href="a.archivo" target="_blank" class="shrink-0">
          <img v-if="isImageFile(a.archivo)" :src="a.archivo" class="w-16 h-16 object-cover rounded-lg border border-surface-border" alt="" />
          <span v-else class="w-16 h-16 flex items-center justify-center rounded-lg border border-surface-border text-ink-muted"><svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg></span>
        </a>
        <div class="flex-1 min-w-0 flex flex-col gap-1">
          <textarea v-model="a.descripcion" rows="2" placeholder="Descripción de la imagen…" :disabled="disabled" class="field-input resize-none flex-1"></textarea>
          <button v-if="!disabled" class="del-btn self-end" @click="$emit('remove-archivo', i)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// Formulario de instrucciones de confección (tallas, procesos, tablas de medidas
// flexibles, archivos) ligado a la OC de subcontratación de una etapa. Es un formulario
// grande pero de UN SOLO documento (no por lote), así que vive una vez por etapa, arriba
// de la lista de lotes (SCO) de esa etapa.
function isImageFile(url) {
  return /\.(png|jpe?g|gif|webp|svg|bmp)(\?.*)?$/i.test(url || "");
}
defineProps({
  general: { type: Object, required: true },
  omCab: { type: Array, required: true },
  omDama: { type: Array, required: true },
  omProc: { type: Array, required: true },
  omTablas: { type: Array, required: true },
  omArchivos: { type: Array, required: true },
  uploading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  OM_CAB: { type: Array, required: true },
  OM_DAMA: { type: Array, required: true },
  tallaTotal: { type: Function, required: true },
  medidasTemplates: { type: Array, default: () => [] },
});
defineEmits([
  "add-proceso", "remove-proceso", "add-tabla", "add-tabla-plantilla", "remove-tabla",
  "add-columna", "remove-columna", "add-fila", "remove-fila",
  "file", "remove-archivo",
]);
</script>
