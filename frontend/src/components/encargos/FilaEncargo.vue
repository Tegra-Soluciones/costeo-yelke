<!--
  Una asignación (api/encargos.py) dentro del proyecto: franja y panel de Asignar.
  `vista` decide qué nombre se enseña: "para_mi" (quién lo encargó), "encargue" (a quién)
  o "equipo" (los dos). Las acciones se abren aquí mismo, sin ventanas del navegador.
-->
<template>
  <div class="px-4 py-3 border-b border-surface-border last:border-0">
    <div class="flex items-start gap-3">
      <span class="p-dot mt-1.5" :class="punto"></span>
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 flex-wrap">
          <button v-if="abrible" type="button" class="text-[13.5px] font-medium text-ink hover:text-brand-700 text-left" @click="abrir">{{ titulo }}</button>
          <p v-else class="text-[13.5px] font-medium text-ink">{{ titulo }}</p>
          <span v-if="f.estado !== 'abierto'" :class="ESTADO[f.estado][1]">{{ ESTADO[f.estado][0] }}</span>
          <span v-else-if="f.vencido || f.vence_hoy" class="p-pill-bad">{{ f.vence_hoy ? "Vence hoy" : "Vencida" }}</span>
        </div>
        <p class="p-meta truncate">{{ meta }}</p>
        <p v-if="f.mensaje" class="mt-1 text-[12.5px] text-ink bg-surface-raised rounded-lg px-2.5 py-1.5 whitespace-pre-line">{{ f.mensaje }}</p>
        <p v-if="f.estado !== 'abierto' && cierre" class="mt-1 text-[12px] text-ink-muted">{{ cierre }}</p>
        <p v-else-if="f.estado === 'abierto' && conRegla" class="mt-1 text-[11.5px]" :class="f.al_dia ? 'text-brand-700' : 'text-ink-light'">{{ f.al_dia ? AL_DIA : f.regla }}</p>

        <!-- Acciones -->
        <div v-if="f.estado === 'abierto' && !modo && (f.puedo_cerrar || f.puedo_cambiar)" class="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[12.5px] font-medium">
          <button v-if="f.puedo_cerrar" type="button" class="text-brand-600 hover:text-brand-700" @click="modo = 'listo'">Hecha</button>
          <button v-if="f.puedo_cerrar && f.para !== f.de" type="button" class="text-ink-muted hover:text-ink" @click="modo = 'regresar'">Regresar</button>
          <button v-if="f.puedo_cambiar && !f.es_mio" type="button" class="text-ink-muted hover:text-ink" :disabled="ocupado" @click="recordar">Recordar</button>
          <button v-if="f.puedo_cambiar" type="button" class="text-ink-muted hover:text-ink" @click="abrirReasignar">Reasignar</button>
          <button v-if="f.puedo_cambiar" type="button" class="text-ink-muted hover:text-red-700" @click="modo = 'quitar'">Quitar</button>
        </div>

        <div v-if="modo" class="mt-2 space-y-2">
          <template v-if="modo === 'listo'">
            <input v-model="texto" class="p-field" placeholder="Nota para quien la asignó (opcional)" @keyup.enter="confirmar" />
            <p v-if="f.auto && !f.al_dia" class="text-[11.5px] text-ink-light">Este paso se marca solo; márcala a mano solo si ya está hecho por otra vía.</p>
          </template>
          <textarea v-else-if="modo === 'regresar'" v-model="texto" rows="2" class="p-field h-auto py-2" placeholder="¿Por qué la regresas? (obligatorio)"></textarea>
          <template v-else-if="modo === 'reasignar'">
            <select v-model="texto" class="p-field">
              <option value="" disabled>{{ candidatos === null ? "Cargando…" : candidatos.length ? "Elige a quién" : "Nadie más tiene este paso" }}</option>
              <option v-for="c in candidatos || []" :key="c.usuario" :value="c.usuario">{{ c.nombre }}{{ c.todo ? " (acceso total)" : "" }}</option>
            </select>
          </template>
          <p v-else-if="modo === 'quitar'" class="text-[12.5px] text-ink">¿Quitarle la asignación a {{ f.para_nombre }}? Le llega un aviso.</p>
          <p v-if="error" class="text-[12px] text-red-700">{{ error }}</p>
          <div class="flex gap-2">
            <button type="button" class="p-btn-primary h-8 text-[12.5px]" :disabled="ocupado || !listoParaConfirmar" @click="confirmar">
              {{ { listo: "Marcar como hecha", regresar: "Regresar", reasignar: "Reasignar", quitar: "Quitar" }[modo] }}
            </button>
            <button type="button" class="p-btn-ghost h-8 text-[12.5px]" @click="cancelar">Cancelar</button>
          </div>
        </div>
        <p v-else-if="aviso" class="mt-1 text-[12px] text-emerald-700">{{ aviso }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import {
  AL_DIA, ESTADO, getOpciones, marcarListo, quitarEncargo, reasignarEncargo, recordarEncargo, regresarEncargo, textoFecha,
} from "@/composables/useEncargos.js";
import { asegurarCompania } from "@/composables/useCompany.js";
import { fecha, fechaHora } from "@/utils/formato.js";

const props = defineProps({
  f: { type: Object, required: true },
  vista: { type: String, default: "equipo" }, // para_mi | encargue | equipo | proyecto
  mostrarProyecto: { type: Boolean, default: true },
  conRegla: { type: Boolean, default: false },
  // Dentro del mismo proyecto: "abrir" solo avisa (la página cambia de paso sin recargar).
  enProyecto: { type: Boolean, default: false },
});
const emit = defineEmits(["cambio", "abrir"]);
const router = useRouter();

const modo = ref("");
const texto = ref("");
const error = ref("");
const aviso = ref("");
const ocupado = ref(false);
const candidatos = ref(null);

const titulo = computed(() => {
  const paso = props.f.vista ? props.f.etiqueta + (props.f.lote ? ` · ${props.f.lote}` : "") : "Proyecto completo";
  return props.mostrarProyecto ? `${paso} · ${props.f.proyecto}` : paso;
});
const meta = computed(() => {
  const f = props.f;
  const quien = { para_mi: `De ${f.de_nombre}`, encargue: `Para ${f.para_nombre}` }[props.vista] || `${f.de_nombre} → ${f.para_nombre}`;
  return [quien, props.mostrarProyecto ? f.cliente : "", textoFecha(f, fecha), `asignada ${fechaHora(f.creado)}`].filter(Boolean).join(" · ");
});
const punto = computed(() => {
  const f = props.f;
  if (f.estado === "abierto") return f.vencido || f.vence_hoy ? "p-dot-bad" : "p-dot-wait";
  return { hecho: "p-dot-ok", regresado: "p-dot-bad" }[f.estado] || "p-dot-off";
});
const cierre = computed(() => {
  const f = props.f;
  const cuando = f.cerrado_en ? ` · ${fechaHora(f.cerrado_en)}` : "";
  if (f.cierre === "Automático") return `Se marcó sola${cuando}`;
  if (f.cierre === "Manual") return `Marcada como hecha${cuando}${f.nota ? `: ${f.nota}` : ""}`;
  if (f.cierre === "Regresado") return `Lo regresó${cuando}: ${f.nota}`;
  return `${f.nota || "Quitada"}${cuando}`;
});
const abrible = computed(() => props.vista !== "proyecto" || props.enProyecto);
const listoParaConfirmar = computed(() => (modo.value === "regresar" || modo.value === "reasignar" ? !!texto.value.trim() : true));

function abrir() {
  if (props.f.compania) asegurarCompania(props.f.compania);
  emit("abrir", props.f);
  if (!props.enProyecto) router.push(props.f.ruta);
}
function cancelar() { modo.value = ""; texto.value = ""; error.value = ""; }

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
  ocupado.value = true; aviso.value = "";
  try { await recordarEncargo(props.f.name); aviso.value = `Se le recordó a ${props.f.para_nombre}.`; }
  catch (e) { error.value = e.message || "No se pudo mandar el recordatorio."; }
  finally { ocupado.value = false; }
}

async function confirmar() {
  if (!listoParaConfirmar.value) return;
  ocupado.value = true; error.value = "";
  try {
    if (modo.value === "listo") await marcarListo(props.f.name, texto.value);
    else if (modo.value === "regresar") await regresarEncargo(props.f.name, texto.value);
    else if (modo.value === "reasignar") await reasignarEncargo(props.f.name, texto.value);
    else if (modo.value === "quitar") await quitarEncargo(props.f.name);
    cancelar();
    emit("cambio");
  } catch (e) { error.value = e.message || "No se pudo guardar."; }
  finally { ocupado.value = false; }
}
</script>
