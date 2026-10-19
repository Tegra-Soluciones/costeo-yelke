<!--
  Pedir un texto antes de una acción: el motivo de "Regresar a corregir"
  (obligatorio) o el comentario opcional al enviar o aprobar.
  Hoja desde abajo en celular, modal centrado en pantallas grandes.
-->
<template>
  <Teleport to="body">
    <div v-if="abierto" class="fixed inset-0 z-[70] bg-black/30 flex items-end sm:items-center justify-center" @click.self="emit('cerrar')">
      <div class="w-full sm:max-w-[460px] bg-white rounded-t-[22px] sm:rounded-2xl shadow-xl flex flex-col max-h-[90vh]" style="padding-bottom: max(18px, env(safe-area-inset-bottom))">
        <div class="w-9 h-1 rounded-full bg-zinc-300 mx-auto mt-2 mb-1 sm:hidden"></div>
        <div class="px-5 pt-3 pb-2">
          <p class="text-[17px] font-semibold">{{ titulo }}</p>
          <p v-if="ayuda" class="p-meta mt-0.5 leading-snug" v-html="ayuda"></p>
        </div>
        <div class="overflow-y-auto px-5">
          <div v-if="sugerencias.length" class="flex gap-2 flex-wrap pt-1 pb-3">
            <button
              v-for="s in sugerencias" :key="s" type="button"
              class="h-8 px-3 rounded-full border border-surface-border bg-white text-[12.5px] text-ink-muted font-medium hover:bg-surface-raised"
              @click="agregar(s)"
            >{{ s }}</button>
          </div>
          <label class="text-[12px] font-medium text-ink-muted block mb-1">
            {{ etiqueta }} <span v-if="obligatorio" class="text-red-600">*</span>
          </label>
          <textarea
            ref="caja" v-model="texto" rows="4"
            class="w-full text-[14px] border border-surface-border rounded-lg px-3 py-2.5 leading-snug bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/25 focus:border-brand-400"
            :placeholder="placeholder"
            @keydown.meta.enter="confirmar" @keydown.ctrl.enter="confirmar"
          ></textarea>
          <p v-if="obligatorio" class="text-[11px] text-ink-light mt-1">Obligatorio · queda en la actividad del documento.</p>
          <p v-if="error" class="text-[12px] text-red-700 mt-2">{{ error }}</p>
        </div>
        <div class="px-5 pt-4 flex gap-2">
          <button type="button" class="p-btn-secondary h-12 sm:h-10 flex-1" :disabled="ocupado" @click="emit('cerrar')">Cancelar</button>
          <button
            type="button" class="p-btn h-12 sm:h-10 flex-[1.4] text-white"
            :class="peligro ? 'bg-red-600 hover:bg-red-700' : 'bg-brand-500 hover:bg-brand-600'"
            :disabled="ocupado || (obligatorio && texto.trim().length < 5)"
            @click="confirmar"
          >{{ ocupado ? "Un momento…" : boton }}</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { nextTick, ref, watch } from "vue";

const props = defineProps({
  abierto: { type: Boolean, default: false },
  titulo: { type: String, default: "" },
  ayuda: { type: String, default: "" },
  etiqueta: { type: String, default: "Comentario" },
  placeholder: { type: String, default: "" },
  boton: { type: String, default: "Confirmar" },
  obligatorio: { type: Boolean, default: false },
  peligro: { type: Boolean, default: false },
  sugerencias: { type: Array, default: () => [] },
  ocupado: { type: Boolean, default: false },
  error: { type: String, default: "" },
});
const emit = defineEmits(["cerrar", "confirmar"]);

const texto = ref("");
const caja = ref(null);

watch(() => props.abierto, async (v) => {
  if (!v) return;
  texto.value = "";
  await nextTick();
  caja.value?.focus();
});

function agregar(s) {
  texto.value = (texto.value.trim() ? texto.value.trim() + " " : "") + s + ".";
  caja.value?.focus();
}

function confirmar() {
  if (props.ocupado || (props.obligatorio && texto.value.trim().length < 5)) return;
  emit("confirmar", texto.value.trim());
}
</script>
