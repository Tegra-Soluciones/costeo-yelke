<!--
  Detalle de una asignación (api/encargos.py) en el panel lateral: de quién, para quién,
  el mensaje, cuándo se marca sola y las acciones. Las acciones que piden un dato
  (nota, motivo, a quién) lo piden aquí mismo, sin ventanas del navegador.
-->
<template>
  <PanelLateral
    :abierto="!!f" eyebrow="Asignación" :titulo="f ? titulo : ''" :meta="f ? `${f.proyecto}${f.cliente ? ' · ' + f.cliente : ''}` : ''"
    :acciones="acciones" :ocupado="ocupado" @cerrar="cerrar"
  >
    <template #pill>
      <span v-if="f" :class="pill[1]">{{ pill[0] }}</span>
    </template>
    <template v-if="f">
      <dl class="grid grid-cols-2 gap-x-6 gap-y-3 text-[13px]">
        <div><dt class="p-meta">Asignó</dt><dd class="font-medium">{{ f.de_nombre }}</dd></div>
        <div><dt class="p-meta">Responsable</dt><dd class="font-medium">{{ f.para_nombre }}</dd></div>
        <div><dt class="p-meta">Paso</dt><dd>{{ f.vista ? f.etiqueta : "Proyecto completo" }}{{ f.lote ? ` · ${f.lote}` : "" }}</dd></div>
        <div>
          <dt class="p-meta">Fecha límite</dt>
          <dd :class="f.estado === 'abierto' && (f.vencido || f.vence_hoy) ? 'text-red-700 font-medium' : ''">{{ f.fecha ? fecha(f.fecha) : "Sin fecha" }}{{ f.vence_hoy && f.estado === 'abierto' ? " · hoy" : f.vencido && f.estado === 'abierto' ? " · vencida" : "" }}</dd>
        </div>
        <div><dt class="p-meta">Asignada</dt><dd>{{ fechaHora(f.creado) }}</dd></div>
        <div v-if="f.estado !== 'abierto'"><dt class="p-meta">Cerrada</dt><dd>{{ fechaHora(f.cerrado_en) }}</dd></div>
      </dl>

      <div v-if="f.mensaje" class="mt-5">
        <p class="p-eyebrow mb-1.5">Mensaje</p>
        <p class="text-[13.5px] leading-relaxed bg-surface-raised rounded-lg px-3.5 py-3 whitespace-pre-line">{{ f.mensaje }}</p>
      </div>

      <ArchivosAsignacion :encargo="f.name" class="mt-5" />

      <div v-if="f.estado !== 'abierto'" class="mt-5 rounded-lg px-3.5 py-3 text-[13px]" :class="f.estado === 'hecho' ? 'bg-emerald-50 text-emerald-900' : f.estado === 'regresado' ? 'bg-red-50 text-red-900' : 'bg-surface-raised text-ink'">
        <p class="font-medium">{{ { hecho: f.cierre === "Automático" ? "Se marcó sola" : "Marcada como hecha", regresado: "La regresó " + f.para_nombre, quitado: "Se quitó" }[f.estado] }}</p>
        <p v-if="f.nota" class="mt-0.5">{{ f.nota }}</p>
      </div>
      <p v-else class="mt-5 flex items-start gap-2 text-[12.5px] text-ink-muted">
        <Icono :nombre="f.auto ? 'check-circulo' : 'reloj'" class="w-4 h-4 mt-px flex-shrink-0" :grosor="2" />{{ f.al_dia ? AL_DIA : f.regla }}
      </p>

      <button type="button" class="mt-5 p-btn-secondary w-full" @click="abrirPaso">Abrir {{ f.vista ? `el paso ${f.etiqueta}` : "el proyecto" }} ›</button>

      <!-- Acción en curso: el dato que pide -->
      <div v-if="modo" class="mt-5 p-panel p-4 space-y-2">
        <p class="text-[13px] font-semibold">{{ { hecha: "Marcar como hecha", regresar: "Regresar la asignación", reasignar: "Reasignar", quitar: "Quitar la asignación" }[modo] }}</p>
        <template v-if="modo === 'hecha'">
          <input v-model="texto" class="p-field" placeholder="Nota para quien la asignó (opcional)" @keyup.enter="confirmar" />
          <p v-if="f.auto && !f.al_dia" class="text-[11.5px] text-ink-light">Este paso se marca solo; márcala a mano solo si ya está hecho por otra vía.</p>
        </template>
        <textarea v-else-if="modo === 'regresar'" v-model="texto" rows="3" class="p-field h-auto py-2" placeholder="¿Por qué la regresas? (obligatorio)"></textarea>
        <select v-else-if="modo === 'reasignar'" v-model="texto" class="p-field">
          <option value="" disabled>{{ candidatos === null ? "Cargando…" : candidatos.length ? "Elige a quién" : "Nadie más tiene este paso" }}</option>
          <option v-for="c in candidatos || []" :key="c.usuario" :value="c.usuario">{{ c.nombre }}{{ c.todo ? " (acceso total)" : "" }}</option>
        </select>
        <p v-else-if="modo === 'quitar'" class="text-[12.5px]">A {{ f.para_nombre }} le llega un aviso de que ya no la tiene.</p>
      </div>
      <p v-if="error" class="mt-3 text-[12.5px] text-red-700">{{ error }}</p>
      <p v-if="aviso" class="mt-3 text-[12.5px] text-emerald-700">{{ aviso }}</p>
    </template>
  </PanelLateral>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import Icono from "@/components/Icono.vue";
import PanelLateral from "@/components/produccion/PanelLateral.vue";
import ArchivosAsignacion from "@/components/asignaciones/ArchivosAsignacion.vue";
import { asegurarCompania } from "@/composables/useCompany.js";
import {
  AL_DIA, ESTADO, getOpciones, marcarListo, quitarEncargo, reasignarEncargo, recordarEncargo, regresarEncargo,
} from "@/composables/useEncargos.js";
import { fecha, fechaHora } from "@/utils/formato.js";

const props = defineProps({ f: { type: Object, default: null } });
const emit = defineEmits(["cerrar", "cambio", "abrir"]);
const router = useRouter();

const modo = ref("");
const texto = ref("");
const error = ref("");
const aviso = ref("");
const ocupado = ref(false);
const candidatos = ref(null);

watch(() => props.f?.name, () => { modo.value = ""; texto.value = ""; error.value = ""; aviso.value = ""; candidatos.value = null; });

const titulo = computed(() => (props.f.vista ? props.f.etiqueta : "Proyecto completo") + (props.f.lote ? ` · ${props.f.lote}` : ""));
const pill = computed(() => {
  const f = props.f;
  if (f.estado === "abierto" && f.vence_hoy) return ["Vence hoy", "p-pill-bad"];
  if (f.estado === "abierto" && f.vencido) return ["Vencida", "p-pill-bad"];
  return ESTADO[f.estado];
});
const listoParaConfirmar = computed(() => (["regresar", "reasignar"].includes(modo.value) ? !!texto.value.trim() : true));

const acciones = computed(() => {
  const f = props.f;
  if (!f || f.estado !== "abierto") return [];
  if (modo.value) {
    return [
      { texto: "Cancelar", accion: () => { modo.value = ""; texto.value = ""; error.value = ""; } },
      { texto: { hecha: "Marcar como hecha", regresar: "Regresar", reasignar: "Reasignar", quitar: "Quitar" }[modo.value],
        tipo: "primaria", deshabilitado: !listoParaConfirmar.value, accion: confirmar },
    ];
  }
  const out = [];
  if (f.puedo_cambiar) {
    out.push({ texto: "Quitar", accion: () => (modo.value = "quitar") });
    out.push({ texto: "Reasignar", accion: abrirReasignar });
    if (!f.es_mio) out.push({ texto: "Recordar", accion: recordar });
  }
  if (f.puedo_cerrar) {
    if (f.para !== f.de) out.push({ texto: "Regresar", accion: () => (modo.value = "regresar") });
    out.push({ texto: "Marcar como hecha", tipo: "primaria", accion: () => (modo.value = "hecha") });
  }
  return out;
});

function cerrar() { emit("cerrar"); }
function abrirPaso() {
  if (props.f.compania) asegurarCompania(props.f.compania);
  emit("abrir", props.f);
  router.push(props.f.ruta);
}
async function abrirReasignar() {
  modo.value = "reasignar"; texto.value = "";
  if (candidatos.value === null) {
    try {
      const op = await getOpciones(props.f.costeo);
      const paso = (op.pasos || []).find((p) => p.clave === (props.f.vista || ""));
      candidatos.value = (paso?.candidatos || []).filter((c) => c.usuario !== props.f.para);
    } catch { candidatos.value = []; }
  }
}
async function recordar() {
  ocupado.value = true; aviso.value = ""; error.value = "";
  try { await recordarEncargo(props.f.name); aviso.value = `Se le recordó a ${props.f.para_nombre}.`; }
  catch (e) { error.value = e.message || "No se pudo mandar el recordatorio."; }
  finally { ocupado.value = false; }
}
async function confirmar() {
  if (!listoParaConfirmar.value) return;
  ocupado.value = true; error.value = "";
  try {
    if (modo.value === "hecha") await marcarListo(props.f.name, texto.value);
    else if (modo.value === "regresar") await regresarEncargo(props.f.name, texto.value);
    else if (modo.value === "reasignar") await reasignarEncargo(props.f.name, texto.value);
    else if (modo.value === "quitar") await quitarEncargo(props.f.name);
    modo.value = ""; texto.value = "";
    emit("cambio");
    emit("cerrar");
  } catch (e) { error.value = e.message || "No se pudo guardar."; }
  finally { ocupado.value = false; }
}
</script>
