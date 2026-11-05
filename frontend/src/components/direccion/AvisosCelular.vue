<!--
  App de Dirección en el celular (composables/usePwa.js): primero, cómo agregar el ícono
  a la pantalla de inicio; ya instalada, activar los avisos del teléfono. Desaparece
  cuando este celular ya los recibe (o si se oculta).
-->
<template>
  <div v-if="visible" class="mx-4 mt-3 rounded-xl border border-brand-200 bg-brand-50/60 px-4 py-3">
    <template v-if="!pwa.instalada">
      <p class="text-[13.5px] font-semibold text-ink">Pon Yelke en tu pantalla de inicio</p>
      <p v-if="pwa.ios" class="text-[12.5px] text-ink-muted mt-1">En Safari, toca <b>Compartir</b> <span aria-hidden="true">(□↑)</span> y luego <b>«Agregar a pantalla de inicio»</b>. Ábrela desde el ícono para activar los avisos.</p>
      <p v-else class="text-[12.5px] text-ink-muted mt-1">En Chrome, toca el menú <b>⋮</b> y luego <b>«Instalar app»</b> (o «Agregar a la pantalla principal»). Ábrela desde el ícono para activar los avisos.</p>
    </template>
    <template v-else>
      <p class="text-[13.5px] font-semibold text-ink">Activa los avisos en este celular</p>
      <p class="text-[12.5px] text-ink-muted mt-1">Te llega una notificación por cada cosa que te toca aprobar o atender, y el ícono muestra cuántas tienes pendientes. Sin correos.</p>
      <button type="button" class="mt-2.5 h-9 px-4 rounded-full bg-brand-500 text-white text-[13px] font-semibold active:bg-brand-600 disabled:opacity-60" :disabled="pwa.ocupado" @click="activarAvisos">
        {{ pwa.ocupado ? "Activando…" : "Activar avisos" }}
      </button>
      <p v-if="pwa.error" class="text-[12px] text-red-700 mt-1.5">{{ pwa.error }}</p>
    </template>
    <button type="button" class="block mt-2 text-[12px] text-ink-light" @click="ocultar">Ahora no</button>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { activarAvisos, pwa } from "@/composables/usePwa.js";

const CLAVE = "yelke-avisos-oculto";
const oculto = ref((() => { try { return localStorage.getItem(CLAVE) === (pwa.instalada ? "app" : "web"); } catch { return false; } })());
const visible = computed(() => pwa.puede && !pwa.activa && !oculto.value);
function ocultar() {
  oculto.value = true;
  try { localStorage.setItem(CLAVE, pwa.instalada ? "app" : "web"); } catch { /* sin almacenamiento */ }
}
</script>
