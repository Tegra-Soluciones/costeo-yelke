<!--
  Asignaciones de un proyecto (panel lateral): asignar un paso a alguien y ver las que
  ya hay. El paso y el lote arrancan en lo que se está viendo (o en ?encargar= del aviso
  "terminó", que propone el siguiente paso).
-->
<template>
  <PanelLateral :abierto="abierto" eyebrow="Asignaciones" :titulo="titulo" meta="Quién hace cada paso de este proyecto" @cerrar="emit('cerrar')">
    <!-- Nuevo encargo -->
    <section v-if="op.pasos.length" class="p-panel p-4 space-y-3">
      <p class="text-[13px] font-semibold text-ink">Asignar un paso</p>
      <div class="grid grid-cols-2 gap-3">
        <label class="col-span-2 sm:col-span-1">
          <span class="p-field-label">Paso</span>
          <select v-model="form.vista" class="p-field">
            <optgroup v-for="g in grupos" :key="g.grupo" :label="g.grupo">
              <option v-for="p in g.pasos" :key="p.clave" :value="p.clave">{{ p.etiqueta }}</option>
            </optgroup>
          </select>
        </label>
        <label v-if="paso?.con_lote" class="col-span-2 sm:col-span-1">
          <span class="p-field-label">Lote</span>
          <select v-model="form.lote" class="p-field">
            <option value="">Todos los lotes</option>
            <option v-for="l in op.lotes" :key="l" :value="l">{{ l }}</option>
          </select>
        </label>
        <label class="col-span-2">
          <span class="p-field-label">A quién</span>
          <select v-model="form.usuario" class="p-field" :disabled="!paso?.candidatos.length">
            <option value="" disabled>{{ paso?.candidatos.length ? "Elige a la persona" : "Nadie tiene este paso en Editar" }}</option>
            <option v-for="c in paso?.candidatos || []" :key="c.usuario" :value="c.usuario">{{ c.nombre }}{{ c.todo ? " (acceso total)" : "" }}</option>
          </select>
          <span v-if="paso && !paso.candidatos.length" class="block mt-1 text-[11.5px] text-ink-light">Asígnale el paso a alguien en Administración › Accesos.</span>
        </label>
        <label class="col-span-2">
          <span class="p-field-label">Mensaje</span>
          <textarea v-model="form.mensaje" rows="3" class="p-field h-auto py-2" placeholder="Qué necesitas, para cuándo, cualquier detalle"></textarea>
        </label>
        <label class="col-span-2 sm:col-span-1">
          <span class="p-field-label">Fecha límite (opcional)</span>
          <input v-model="form.fecha" type="date" class="p-field" :min="hoy" />
        </label>
        <ArchivosAsignacion v-model="archivos" class="col-span-2" />
      </div>
      <p v-if="paso" class="text-[11.5px] text-ink-light">{{ paso.regla }}</p>
      <p v-if="error" class="text-[12px] text-red-700">{{ error }}</p>
      <p v-if="hecho" class="text-[12px] text-emerald-700">{{ hecho }}</p>
      <div class="flex justify-end">
        <button type="button" class="p-btn-primary" :disabled="ocupado || !form.usuario" @click="encargar">{{ ocupado ? "Asignando…" : "Asignar" }}</button>
      </div>
    </section>
    <p v-else-if="!cargando" class="p-meta">No tienes ningún paso de este proyecto para asignar.</p>

    <!-- Encargos del proyecto -->
    <section class="mt-5">
      <p class="p-eyebrow mb-2">En este proyecto</p>
      <div v-if="cargando && !lista.length" class="p-meta">Cargando…</div>
      <div v-else-if="!lista.length" class="p-meta">Todavía no hay asignaciones.</div>
      <div v-else class="p-panel">
        <FilaEncargo v-for="f in lista" :key="f.name" :f="f" vista="proyecto" :mostrar-proyecto="false" con-regla @cambio="cargar" />
      </div>
    </section>
  </PanelLateral>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import PanelLateral from "@/components/produccion/PanelLateral.vue";
import FilaEncargo from "@/components/encargos/FilaEncargo.vue";
import ArchivosAsignacion from "@/components/asignaciones/ArchivosAsignacion.vue";
import { crearEncargo, getDelProyecto, getOpciones, subirArchivosAsignacion, version } from "@/composables/useEncargos.js";

const props = defineProps({
  abierto: { type: Boolean, default: false },
  costeo: { type: String, required: true },
  titulo: { type: String, default: "" },
  pasoInicial: { type: String, default: "" },
  loteInicial: { type: String, default: "" },
});
const emit = defineEmits(["cerrar", "cambio"]);

const op = reactive({ pasos: [], lotes: [] });
const lista = ref([]);
const cargando = ref(false);
const ocupado = ref(false);
const error = ref("");
const hecho = ref("");
const form = reactive({ vista: "", lote: "", usuario: "", mensaje: "", fecha: "" });
const archivos = ref([]);
const hoy = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);

const paso = computed(() => op.pasos.find((p) => p.clave === form.vista));
const grupos = computed(() => {
  const out = [];
  for (const p of op.pasos) {
    let g = out.find((x) => x.grupo === p.grupo);
    if (!g) out.push((g = { grupo: p.grupo, pasos: [] }));
    g.pasos.push(p);
  }
  return out;
});

watch(() => form.vista, () => {
  form.usuario = paso.value?.candidatos.length === 1 ? paso.value.candidatos[0].usuario : "";
  if (!paso.value?.con_lote) form.lote = "";
});

function preparar() {
  const claves = op.pasos.map((p) => p.clave);
  const inicial = props.pasoInicial === "general" ? "" : props.pasoInicial;
  form.vista = claves.includes(inicial) ? inicial : claves[0] ?? "";
  form.lote = op.lotes.includes(props.loteInicial) ? props.loteInicial : "";
  form.mensaje = ""; form.fecha = ""; error.value = "";
}

async function cargar() {
  cargando.value = true;
  try {
    const [o, l] = await Promise.all([op.pasos.length ? null : getOpciones(props.costeo), getDelProyecto(props.costeo)]);
    if (o) { op.pasos = o.pasos || []; op.lotes = o.lotes || []; preparar(); }
    lista.value = l.encargos || [];
    emit("cambio", lista.value.filter((f) => f.estado === "abierto").length);
  } catch (e) { error.value = e.message || "No se pudieron cargar las asignaciones."; }
  finally { cargando.value = false; }
}

async function encargar() {
  ocupado.value = true; error.value = ""; hecho.value = "";
  try {
    const r = await crearEncargo({ costeo: props.costeo, vista: form.vista, usuario: form.usuario, mensaje: form.mensaje,
      fecha: form.fecha || undefined, lote: form.lote || undefined });
    if (archivos.value.length) await subirArchivosAsignacion(r.name, archivos.value);
    archivos.value = [];
    const quien = paso.value?.candidatos.find((c) => c.usuario === form.usuario)?.nombre || form.usuario;
    hecho.value = `Listo: se le avisó a ${quien}.`;
    form.mensaje = ""; form.fecha = "";
    await cargar();
  } catch (e) { error.value = e.message || "No se pudo asignar."; }
  finally { ocupado.value = false; }
}

// immediate: Dirección › Por asignar lo monta ya abierto.
watch(() => props.abierto, (a) => { if (a) { hecho.value = ""; if (op.pasos.length) preparar(); cargar(); } }, { immediate: true });
watch(() => [props.pasoInicial, props.loteInicial], () => { if (props.abierto && op.pasos.length) preparar(); });
watch(() => props.costeo, () => { op.pasos = []; lista.value = []; });
watch(version, () => { if (props.abierto) cargar(); });
</script>
