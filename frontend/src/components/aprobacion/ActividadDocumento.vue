<!--
  Línea de tiempo de un documento: lo mismo que el timeline del escritorio de
  ERPNext (creación, cambios, adjuntos, correos, comentarios) más los pasos de la
  aprobación (envío, revisión, devolución, aprobación). Ver api/actividad.py.

  `ultimos` > 0 muestra solo esos eventos y un "Ver N anteriores" (celular).
-->
<template>
  <div>
    <div v-if="cargando && !eventos.length" class="py-6 text-center p-meta">Cargando la actividad…</div>
    <p v-else-if="error" class="text-[12.5px] text-red-700">{{ error }}</p>
    <template v-else>
      <button
        v-if="ocultos > 0" type="button"
        class="text-[12.5px] text-brand-600 font-medium mb-3"
        @click="verTodo = true"
      >Ver {{ ocultos }} {{ ocultos === 1 ? "evento anterior" : "eventos anteriores" }}</button>

      <div class="relative">
        <div class="absolute left-[13px] top-2 bottom-2 w-px bg-surface-border"></div>
        <div v-for="(e, i) in visibles" :key="i" class="relative flex gap-3 pb-3.5 last:pb-0">
          <span
            class="w-7 h-7 rounded-full flex items-center justify-center text-[12px] flex-shrink-0 z-10 ring-4 ring-white"
            :class="ICONO[e.tipo]?.[1] || 'bg-zinc-100 text-ink-muted'"
          >{{ ICONO[e.tipo]?.[0] || "•" }}</span>
          <div class="min-w-0 flex-1 pt-0.5">
            <p class="text-[12.5px] leading-snug"><b class="font-semibold">{{ e.nombre }}</b> {{ e.texto }}</p>
            <ul v-if="e.detalle?.length" class="mt-1 space-y-0.5">
              <li v-for="(d, j) in e.detalle" :key="j" class="text-[12px] text-ink-muted leading-snug">{{ d }}</li>
            </ul>
            <p
              v-if="e.cita" class="mt-1 text-[12.5px] leading-snug rounded-lg px-3 py-2 whitespace-pre-line"
              :class="e.tipo === 'devuelto' ? 'bg-red-50 text-red-900' : e.tipo === 'aprobado' ? 'bg-emerald-50 text-emerald-900' : 'bg-surface-raised text-ink'"
            >{{ e.cita }}</p>
            <p class="text-[11px] text-ink-light mt-0.5" :title="e.en">{{ fechaHora(e.en) }} · {{ haceCuanto(e.en) }}</p>
          </div>
        </div>
      </div>
    </template>

    <form v-if="conComentario" class="flex items-end gap-2 mt-4" @submit.prevent="comentar">
      <textarea
        v-model="nuevo" rows="1"
        class="flex-1 min-h-[40px] max-h-40 text-[13px] border border-surface-border rounded-2xl px-3.5 py-2.5 leading-snug bg-white resize-none focus:outline-none focus:ring-2 focus:ring-brand-500/25 focus:border-brand-400"
        placeholder="Escribe un comentario…"
        @input="crecer" @keydown.meta.enter="comentar" @keydown.ctrl.enter="comentar"
      ></textarea>
      <button type="submit" class="p-btn-primary h-10 px-3.5" :disabled="!nuevo.trim() || enviando">
        {{ enviando ? "…" : "Enviar" }}
      </button>
    </form>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { call } from "@/utils/frappe.js";
import { fechaHora, haceCuanto } from "@/utils/formato.js";

const props = defineProps({
  doctype: { type: String, required: true },
  name: { type: String, required: true },
  ultimos: { type: Number, default: 0 },
  conComentario: { type: Boolean, default: true },
});
const emit = defineEmits(["cuenta"]);

// Ícono y color por tipo de evento (mismos del mockup docs/mockups/direccion.html).
const ICONO = {
  crea: ["＋", "bg-zinc-100 text-ink-muted"],
  cambio: ["✎", "bg-zinc-100 text-ink-muted"],
  adjunto: ["⧉", "bg-zinc-100 text-ink-muted"],
  correo: ["✉", "bg-zinc-100 text-ink-muted"],
  info: ["•", "bg-zinc-100 text-ink-muted"],
  aviso: ["!", "bg-amber-50 text-amber-800"],
  envio: ["➜", "bg-brand-50 text-brand-700"],
  revision: ["✓", "bg-violet-50 text-violet-700"],
  comentario: ["💬", "bg-sky-50 text-sky-700"],
  devuelto: ["↩", "bg-red-50 text-red-700"],
  aprobado: ["✓", "bg-emerald-50 text-emerald-700"],
  validado: ["✓", "bg-emerald-50 text-emerald-700"],
  cancelado: ["✕", "bg-zinc-100 text-ink-muted"],
};

const eventos = ref([]);
const cargando = ref(false);
const error = ref("");
const verTodo = ref(false);
const nuevo = ref("");
const enviando = ref(false);

const visibles = computed(() =>
  props.ultimos > 0 && !verTodo.value ? eventos.value.slice(-props.ultimos) : eventos.value,
);
const ocultos = computed(() => eventos.value.length - visibles.value.length);

function aplicar(r) {
  eventos.value = r.eventos || [];
  emit("cuenta", r.comentarios || 0);
}

async function cargar() {
  if (!props.doctype || !props.name) return;
  cargando.value = true;
  error.value = "";
  try {
    aplicar(await call("costeo_yelke.api.actividad.get_actividad", { doctype: props.doctype, name: props.name }));
  } catch (e) {
    error.value = e.message || "No se pudo cargar la actividad.";
  } finally {
    cargando.value = false;
  }
}

async function comentar() {
  if (!nuevo.value.trim() || enviando.value) return;
  enviando.value = true;
  try {
    aplicar(await call("costeo_yelke.api.actividad.agregar_comentario", {
      doctype: props.doctype, name: props.name, texto: nuevo.value.trim(),
    }));
    nuevo.value = "";
    verTodo.value = true;
  } catch (e) {
    error.value = e.message || "No se pudo guardar el comentario.";
  } finally {
    enviando.value = false;
  }
}

function crecer(ev) {
  const t = ev.target;
  t.style.height = "auto";
  t.style.height = Math.min(t.scrollHeight, 160) + "px";
}

watch(() => [props.doctype, props.name], () => { verTodo.value = false; cargar(); }, { immediate: true });
defineExpose({ recargar: cargar });
</script>
