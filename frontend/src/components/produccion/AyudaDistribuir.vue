<!--
  "?" junto a «Distribuir por» (costos adicionales de encargo, envío y recibo del
  taller): cuándo conviene repartir el flete por cantidad y cuándo por importe.
-->
<template>
  <span ref="raiz" class="relative inline-flex align-middle ml-1">
    <button
      type="button" title="¿Cantidad o importe?"
      class="w-4 h-4 rounded-full border border-surface-border text-[10px] font-semibold text-ink-light hover:text-brand-600 hover:border-brand-300 flex items-center justify-center leading-none"
      @click.stop="abierto = !abierto"
    >?</button>
    <template v-if="abierto">
      <!-- Hacia arriba: abajo está la barra de acciones fija y lo tapaba. -->
      <span class="absolute z-50 left-0 bottom-full mb-1.5 w-80 rounded-lg bg-white shadow-lg ring-1 ring-surface-border p-3 text-[12px] font-normal normal-case tracking-normal text-ink-muted leading-relaxed text-left">
        <b class="block text-ink mb-1">¿Cómo se reparte el flete entre los materiales?</b>
        El total no cambia; solo a qué material se le carga cuánto.
        <span class="block mt-1.5"><b class="text-ink">Cantidad</b> — cada metro o pieza carga lo mismo. Úsalo si va <b>un solo material</b> o materiales parecidos en la misma unidad (varias telas por metro).</span>
        <span class="block mt-1.5"><b class="text-ink">Importe</b> — cada material carga según lo que vale. Úsalo si se mezclan <b>materiales de valor o unidad muy distintos</b> (tela con botones, rollos con piezas): por cantidad, 20,000 botones se llevarían casi todo el flete.</span>
        <span class="block mt-1.5 text-ink-light">Ante la duda, Importe: deja bien el costo de la materia prima.</span>
      </span>
    </template>
  </span>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";

const abierto = ref(false);
const raiz = ref(null);
// Se cierra con cualquier clic fuera (o con Esc).
const fuera = (e) => { if (abierto.value && raiz.value && !raiz.value.contains(e.target)) abierto.value = false; };
const esc = (e) => { if (e.key === "Escape") abierto.value = false; };
onMounted(() => { document.addEventListener("click", fuera); document.addEventListener("keydown", esc); });
onBeforeUnmount(() => { document.removeEventListener("click", fuera); document.removeEventListener("keydown", esc); });
</script>
