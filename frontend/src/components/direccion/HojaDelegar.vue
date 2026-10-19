<!--
  "Delegar mis aprobaciones": a quién, desde y hasta (api/delegacion.py).
  Hoja desde abajo en celular, modal en pantallas grandes.
-->
<template>
  <Teleport to="body">
    <div v-if="abierto" class="fixed inset-0 z-[70] bg-black/30 flex items-end sm:items-center justify-center" @click.self="emit('cerrar')">
      <div class="w-full sm:max-w-[460px] bg-white rounded-t-[22px] sm:rounded-2xl shadow-xl flex flex-col max-h-[92vh]" style="padding-bottom: max(18px, env(safe-area-inset-bottom))">
        <div class="w-9 h-1 rounded-full bg-zinc-300 mx-auto mt-2 mb-1 sm:hidden"></div>
        <div class="px-5 pt-3 pb-2">
          <p class="text-[17px] font-semibold">Delegar mis aprobaciones</p>
          <p class="p-meta mt-0.5 leading-snug">Esa persona podrá aprobar y regresar documentos en tu lugar. No verá Proyectos ni Resumen.</p>
        </div>
        <div class="px-5 space-y-3 overflow-y-auto">
          <div>
            <label class="text-[12px] font-medium text-ink-muted block mb-1">¿Quién aprueba por ti?</label>
            <div class="space-y-1.5 max-h-[230px] overflow-y-auto">
              <label
                v-for="c in candidatos" :key="c.name"
                class="flex items-center gap-3 p-panel px-3 h-12 cursor-pointer"
                :class="a === c.name ? 'border-brand-400 bg-brand-50/50' : ''"
              >
                <input v-model="a" type="radio" :value="c.name" class="accent-brand-500" />
                <span class="w-7 h-7 rounded-full flex items-center justify-center text-[10.5px] font-semibold flex-shrink-0" :class="colorAvatar(c.name)">{{ iniciales(c.nombre) }}</span>
                <span class="text-[13.5px] font-medium flex-1 truncate">{{ c.nombre }}</span>
                <span class="p-meta">{{ c.rol }}</span>
              </label>
              <p v-if="!candidatos.length" class="p-meta">No hay otros usuarios activos.</p>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-2">
            <div><label class="text-[12px] font-medium text-ink-muted block mb-1">Desde</label><input v-model="desde" type="date" :min="hoy" class="p-field h-10 text-[14px]" /></div>
            <div><label class="text-[12px] font-medium text-ink-muted block mb-1">Hasta</label><input v-model="hasta" type="date" :min="desde || hoy" class="p-field h-10 text-[14px]" /></div>
          </div>
          <div><label class="text-[12px] font-medium text-ink-muted block mb-1">Motivo (opcional)</label><input v-model="motivo" class="p-field h-10 text-[14px]" placeholder="Vacaciones" /></div>
          <p class="text-[12px] text-ink-muted bg-surface-raised rounded-lg px-3 py-2 leading-snug">
            <template v-if="elegido && desde && hasta">
              <b>{{ elegido.nombre }}</b> podrá aprobar por ti del {{ fecha(desde) }} al {{ fecha(hasta) }}.
            </template>
            Se termina sola el día “Hasta” y la puedes terminar antes. Mientras dure, los avisos te siguen llegando a ti también.
          </p>
          <p v-if="error" class="text-[12px] text-red-700">{{ error }}</p>
        </div>
        <div class="px-5 pt-4 flex gap-2">
          <button type="button" class="p-btn-secondary h-12 sm:h-10 flex-1" :disabled="ocupado" @click="emit('cerrar')">Cancelar</button>
          <button type="button" class="p-btn-primary h-12 sm:h-10 flex-[1.4]" :disabled="ocupado || !a || !desde || !hasta || hasta < desde" @click="delegar">
            {{ ocupado ? "Un momento…" : "Delegar" }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { call } from "@/utils/frappe.js";
import { colorAvatar, fecha, iniciales } from "@/utils/formato.js";

const props = defineProps({
  abierto: { type: Boolean, default: false },
  candidatos: { type: Array, default: () => [] },
  hoy: { type: String, default: "" },
});
const emit = defineEmits(["cerrar", "hecho"]);

const a = ref("");
const desde = ref("");
const hasta = ref("");
const motivo = ref("");
const ocupado = ref(false);
const error = ref("");

const elegido = computed(() => props.candidatos.find((c) => c.name === a.value));

function masDias(iso, n) {
  const d = new Date(`${iso}T12:00:00`);
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}

watch(() => props.abierto, (v) => {
  if (!v) return;
  error.value = "";
  motivo.value = "";
  a.value = props.candidatos[0]?.name || "";
  desde.value = props.hoy || new Date().toISOString().slice(0, 10);
  hasta.value = masDias(desde.value, 7);
});

async function delegar() {
  ocupado.value = true;
  error.value = "";
  try {
    const r = await call("costeo_yelke.api.delegacion.crear_delegacion", {
      a_usuario: a.value, desde: desde.value, hasta: hasta.value, motivo: motivo.value,
    });
    emit("hecho", r, elegido.value);
  } catch (e) {
    error.value = e.message || "No se pudo crear la delegación.";
  } finally {
    ocupado.value = false;
  }
}
</script>
