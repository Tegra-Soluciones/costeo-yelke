<!--
  Tarjeta de un documento por aprobar o revisar (bandeja del panel de Dirección).
  `fila` = una tarjeta de api/aprobaciones.get_bandeja. En escritorio se pinta
  como renglón de la lista (`renglon`), con la seleccionada marcada.
-->
<template>
  <button
    type="button"
    class="w-full text-left transition-colors"
    :class="renglon
      ? ['px-4 py-3 border-b border-surface-border last:border-0 hover:bg-zinc-50', seleccionada ? 'bg-brand-50/60 hover:bg-brand-50/60 shadow-[inset_3px_0_0_#ff6b15]' : 'bg-white']
      : 'p-panel px-4 py-3.5 active:bg-zinc-50 space-y-1.5'"
    @click="emit('abrir', fila)"
  >
    <div class="flex items-center gap-2">
      <span :class="[TIPOS_DOC[fila.tipo]?.pill || 'p-pill-off', 'h-[22px] text-[11px]']">{{ fila.etiqueta }}</span>
      <span v-if="fila.horas > 48" class="p-pill-wait h-[22px] text-[11px]">+48 h</span>
      <span v-if="fila.bloqueo" class="p-pill-bad h-[22px] text-[11px]">Bloqueada</span>
      <span class="ml-auto text-[15px] font-semibold tabular-nums">{{ fila.monto != null ? dinero(fila.monto, fila.moneda) : "" }}</span>
    </div>
    <p v-if="fila.compania" class="text-[10.5px] font-semibold uppercase tracking-[0.06em] text-ink-light truncate" :class="renglon ? 'mt-1.5' : ''">{{ fila.compania }}</p>
    <p class="text-[14.5px] font-semibold leading-tight truncate" :class="renglon && !fila.compania ? 'mt-1' : ''">{{ fila.titulo }}</p>
    <p v-if="fila.sub" class="p-meta leading-snug" :class="renglon ? 'truncate' : 'line-clamp-2'">{{ fila.sub }}</p>
    <div class="flex items-center gap-1.5 text-[11.5px] text-ink-light" :class="renglon ? 'mt-0.5' : 'pt-1'">
      <span class="w-5 h-5 rounded-full flex items-center justify-center text-[8.5px] font-semibold flex-shrink-0" :class="colorAvatar(fila.por)">{{ iniciales(fila.por_nombre) }}</span>
      <span class="truncate">{{ primerNombre(fila.por_nombre) }} · {{ haceCuanto(fila.enviado_en) }}</span>
      <span v-if="fila.revisado_por" class="ml-auto text-violet-700 font-medium whitespace-nowrap inline-flex items-center gap-1"><Icono nombre="check" class="w-3.5 h-3.5" :grosor="2.2" />Revisó {{ primerNombre(fila.revisado_por_nombre) }}</span>
      <span v-else-if="fila.cambio_tras_envio" class="ml-auto text-amber-700 font-medium whitespace-nowrap">Cambió tras enviarse</span>
    </div>
  </button>
</template>

<script setup>
import { TIPOS_DOC, colorAvatar, dinero, haceCuanto, iniciales } from "@/utils/formato.js";
import Icono from "@/components/Icono.vue";

defineProps({
  fila: { type: Object, required: true },
  renglon: { type: Boolean, default: false },
  seleccionada: { type: Boolean, default: false },
});
const emit = defineEmits(["abrir"]);

const primerNombre = (n) => String(n || "").split(" ")[0];
</script>
