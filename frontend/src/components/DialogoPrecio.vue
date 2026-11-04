<!--
  Precio de venta escrito dos veces (pedido de Yelke), las dos a la vista. El precio
  solo se aplica cuando las dos coinciden.
-->
<template>
  <Teleport to="body">
    <div v-if="abierto" class="fixed inset-0 z-[70] bg-black/30 flex items-center justify-center p-4" @click.self="emit('cerrar')">
      <form class="w-full max-w-[400px] bg-white rounded-2xl shadow-xl p-5" @submit.prevent="confirmar">
        <p class="text-[16px] font-semibold">Precio de venta</p>
        <p class="p-meta mt-0.5">{{ producto }}<template v-if="actual"> · hoy {{ dinero(actual) }}</template></p>

        <label class="text-[12px] font-medium text-ink-muted block mt-4 mb-1">Precio unitario</label>
        <div class="relative">
          <span class="absolute left-3 top-1/2 -translate-y-1/2 text-ink-light text-[14px]">$</span>
          <input ref="primero" v-model="uno" type="text" inputmode="decimal" autocomplete="off"
                 class="w-full h-10 pl-7 pr-3 text-[15px] tabular-nums border border-surface-border rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/25 focus:border-brand-400" />
        </div>

        <label class="text-[12px] font-medium text-ink-muted block mt-3 mb-1">Escríbelo otra vez</label>
        <div class="relative">
          <span class="absolute left-3 top-1/2 -translate-y-1/2 text-ink-light text-[14px]">$</span>
          <input v-model="dos" type="text" inputmode="decimal" autocomplete="off"
                 class="w-full h-10 pl-7 pr-3 text-[15px] tabular-nums border rounded-lg focus:outline-none focus:ring-2"
                 :class="estado === 'no' ? 'border-red-300 focus:ring-red-500/20' : estado === 'si' ? 'border-emerald-300 focus:ring-emerald-500/20' : 'border-surface-border focus:ring-brand-500/25'" />
        </div>
        <p v-if="estado === 'si'" class="text-[12px] text-emerald-700 font-medium mt-1.5 flex items-center gap-1"><Icono nombre="check" class="w-3.5 h-3.5" :grosor="2.4" />Coinciden: {{ dinero(valor(uno)) }}</p>
        <p v-else-if="estado === 'no'" class="text-[12px] text-red-700 font-medium mt-1.5">No coinciden. Revisa el precio.</p>
        <p v-else-if="estado === 'invalido'" class="text-[12px] text-red-700 font-medium mt-1.5">Escribe un precio mayor que cero.</p>

        <div class="flex gap-2 mt-5">
          <button type="button" class="p-btn-secondary h-10 flex-1" @click="emit('cerrar')">Cancelar</button>
          <button type="submit" class="p-btn-primary h-10 flex-[1.4]" :disabled="estado !== 'si'">Aplicar precio</button>
        </div>
      </form>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, ref, watch } from "vue";
import Icono from "@/components/Icono.vue";
import { dinero } from "@/utils/formato.js";

const props = defineProps({
  abierto: { type: Boolean, default: false },
  producto: { type: String, default: "" },
  actual: { type: Number, default: 0 },
});
const emit = defineEmits(["cerrar", "confirmar"]);

const uno = ref("");
const dos = ref("");
const primero = ref(null);

/** "1,250.50" / "1250.5" / "$385" -> número (redondeado a centavos), o null. */
function valor(txt) {
  const limpio = String(txt || "").replace(/[$,\s]/g, "");
  if (!/^\d+(\.\d{0,2})?$|^\.\d{1,2}$/.test(limpio)) return null;
  return Math.round(parseFloat(limpio) * 100) / 100;
}
const estado = computed(() => {
  if (!uno.value || !dos.value) return "";
  const a = valor(uno.value), b = valor(dos.value);
  if (a == null || b == null || a <= 0 || b <= 0) return "invalido";
  return a === b ? "si" : "no";
});

watch(() => props.abierto, async (v) => {
  if (!v) return;
  uno.value = "";
  dos.value = "";
  await nextTick();
  primero.value?.focus();
});

function confirmar() {
  if (estado.value === "si") emit("confirmar", valor(uno.value));
}
</script>
