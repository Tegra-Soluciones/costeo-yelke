<!--
  "Prestar permisos" (solo Dirección, api/permisos_temporales.py): los permisos de un
  usuario a otro por unos días -- p. ej. alguien cubre a quien sale de vacaciones.
  Aparte de "Delegar mis aprobaciones": aquí nunca se prestan los roles de aprobar.
-->
<template>
  <div v-if="d" class="p-panel p-4">
    <p class="text-[14px] font-semibold">Permisos prestados</p>
    <p class="p-meta mt-0.5">Alguien cubre a otra persona unos días con sus mismos permisos. Se terminan solos.</p>

    <div v-if="vigentes.length" class="mt-3 divide-y divide-surface-border border border-surface-border rounded-xl">
      <div v-for="f in vigentes" :key="f.name" class="px-3 py-2.5 flex items-center gap-3">
        <div class="flex-1 min-w-0">
          <p class="text-[13px] font-medium truncate">{{ f.a_nombre }} <span class="text-ink-muted font-normal">con los permisos de</span> {{ f.de_nombre }}</p>
          <p class="p-meta">{{ f.estado === "Activo" ? "Hasta" : `Del ${fecha(f.desde)} al` }} {{ fecha(f.hasta) }}<template v-if="f.motivo"> · {{ f.motivo }}</template></p>
        </div>
        <span :class="f.estado === 'Activo' ? 'p-pill-ok' : 'p-pill-wait'">{{ f.estado }}</span>
        <button type="button" class="p-btn-secondary h-8 text-[12px]" :disabled="ocupado" @click="terminar(f)">{{ f.estado === "Activo" ? "Terminar" : "Cancelar" }}</button>
      </div>
    </div>
    <button type="button" class="p-btn-primary w-full h-11 mt-3" @click="abrir">Prestar permisos</button>
    <p v-if="error" class="text-[12px] text-red-700 mt-2">{{ error }}</p>
  </div>

  <Teleport to="body">
    <div v-if="hoja" class="fixed inset-0 z-[70] bg-black/30 flex items-end sm:items-center justify-center" @click.self="hoja = false">
      <div class="w-full sm:max-w-[480px] bg-white rounded-t-[22px] sm:rounded-2xl shadow-xl flex flex-col max-h-[92vh]" style="padding-bottom: max(18px, env(safe-area-inset-bottom))">
        <div class="w-9 h-1 rounded-full bg-zinc-300 mx-auto mt-2 mb-1 sm:hidden"></div>
        <div class="px-5 pt-3 pb-2">
          <p class="text-[17px] font-semibold">Prestar permisos</p>
          <p class="p-meta mt-0.5 leading-snug">Quien cubre recibe los permisos de la otra persona. Los de aprobar no se prestan aquí.</p>
        </div>
        <div class="px-5 space-y-3 overflow-y-auto">
          <div>
            <label class="text-[12px] font-medium text-ink-muted block mb-1">¿De quién son los permisos?</label>
            <select v-model="de" class="p-field h-10 text-[14px]">
              <option value="">Elige a la persona…</option>
              <option v-for="u in conPermisos" :key="u.name" :value="u.name">{{ u.nombre }}</option>
            </select>
          </div>
          <div>
            <label class="text-[12px] font-medium text-ink-muted block mb-1">¿Quién la cubre?</label>
            <select v-model="a" class="p-field h-10 text-[14px]">
              <option value="">Elige a la persona…</option>
              <option v-for="u in d.usuarios.filter((x) => x.name !== de)" :key="u.name" :value="u.name">{{ u.nombre }}</option>
            </select>
          </div>
          <div class="grid grid-cols-2 gap-2">
            <div><label class="text-[12px] font-medium text-ink-muted block mb-1">Desde</label><input v-model="desde" type="date" :min="d.hoy" class="p-field h-10 text-[14px]" /></div>
            <div><label class="text-[12px] font-medium text-ink-muted block mb-1">Hasta</label><input v-model="hasta" type="date" :min="desde || d.hoy" class="p-field h-10 text-[14px]" /></div>
          </div>
          <div><label class="text-[12px] font-medium text-ink-muted block mb-1">Motivo (opcional)</label><input v-model="motivo" class="p-field h-10 text-[14px]" placeholder="Vacaciones" /></div>
          <div v-if="de && a" class="text-[12px] text-ink-muted bg-surface-raised rounded-lg px-3 py-2 leading-snug">
            <template v-if="nuevos.length">
              <b>{{ nombre(a) }}</b> recibirá {{ nuevos.length }} permiso(s) de {{ nombre(de) }}:
              <span class="text-ink">{{ nuevos.map(etiquetaRol).join(", ") }}</span>.
              Al terminar se le quitan solo esos.
            </template>
            <template v-else>{{ nombre(a) }} ya tiene todos los permisos de {{ nombre(de) }}.</template>
          </div>
          <p v-if="errorHoja" class="text-[12px] text-red-700">{{ errorHoja }}</p>
        </div>
        <div class="px-5 pt-4 flex gap-2">
          <button type="button" class="p-btn-secondary h-12 sm:h-10 flex-1" :disabled="ocupado" @click="hoja = false">Cancelar</button>
          <button type="button" class="p-btn-primary h-12 sm:h-10 flex-[1.4]" :disabled="ocupado || !de || !a || !nuevos.length || !desde || !hasta || hasta < desde" @click="prestar">
            {{ ocupado ? "Un momento…" : "Prestar" }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { call } from "@/utils/frappe.js";
import { fecha } from "@/utils/formato.js";

const d = ref(null);
const ocupado = ref(false);
const error = ref("");
const hoja = ref(false);
const errorHoja = ref("");
const de = ref("");
const a = ref("");
const desde = ref("");
const hasta = ref("");
const motivo = ref("");

const vigentes = computed(() => [...(d.value?.activos || []), ...(d.value?.programados || [])]);
const conPermisos = computed(() => (d.value?.usuarios || []).filter((u) => u.roles.length));
const nombre = (user) => d.value?.usuarios.find((u) => u.name === user)?.nombre || user;
// Los que recibiría: los de la persona que se cubre que quien cubre todavía no tiene.
const nuevos = computed(() => {
  const origen = d.value?.usuarios.find((u) => u.name === de.value)?.roles || [];
  const ya = new Set(d.value?.usuarios.find((u) => u.name === a.value)?.roles || []);
  return origen.filter((r) => !ya.has(r));
});
const etiquetaRol = (r) => d.value?.etiquetas?.[r] || r.replace(/ Yelke$/, "");

function masDias(iso, n) {
  const x = new Date(`${iso}T12:00:00`);
  x.setDate(x.getDate() + n);
  return x.toISOString().slice(0, 10);
}

async function cargar() {
  try { d.value = await call("costeo_yelke.api.permisos_temporales.get_permisos_temporales"); }
  catch (e) { error.value = e.message || "No se pudieron cargar los permisos prestados."; }
}
function abrir() {
  errorHoja.value = ""; de.value = ""; a.value = ""; motivo.value = "";
  desde.value = d.value?.hoy || new Date().toISOString().slice(0, 10);
  hasta.value = masDias(desde.value, 7);
  hoja.value = true;
}
async function prestar() {
  ocupado.value = true; errorHoja.value = "";
  try {
    d.value = await call("costeo_yelke.api.permisos_temporales.crear_permiso_temporal", {
      de_usuario: de.value, a_usuario: a.value, desde: desde.value, hasta: hasta.value, motivo: motivo.value,
    });
    hoja.value = false;
  } catch (e) { errorHoja.value = e.message || "No se pudieron prestar los permisos."; }
  finally { ocupado.value = false; }
}
async function terminar(f) {
  ocupado.value = true; error.value = "";
  try { d.value = await call("costeo_yelke.api.permisos_temporales.terminar_permiso_temporal", { name: f.name }); }
  catch (e) { error.value = e.message || "No se pudo terminar el préstamo."; }
  finally { ocupado.value = false; }
}

onMounted(cargar);
</script>
