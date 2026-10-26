<!--
  Estado de aprobación de un documento, con los botones que le tocan a quien lo
  ve (docs/plan-panel-direccion.md §3 y §5.2). Va arriba de cada documento que
  pasa por aprobación (roles.DOCUMENTOS_CON_APROBACION).

    Regresado  → franja ámbar con el motivo · [Ya lo corregí · Reenviar]
    Pendiente  → "En aprobación, enviado por…" · Revisor/Dirección: [Regresar] [Revisar|Aprobar]
    Borrador   → quien NO puede aprobar: "Necesita aprobación" · [Enviar a aprobación]
                 quien sí puede: nada (valida directo con el botón de la pantalla)

  Emite `estado` cada vez que lo lee, para que la pantalla oculte su botón de
  Validar a quien no puede usarlo, y `cambio` después de cada acción.
-->
<template>
  <div v-if="e && e.aplica && e.docstatus === 0 && visible && conContenido" class="rounded-xl border px-4 py-3" :class="caja">
    <!-- Regresado -->
    <template v-if="e.estado === 'Devuelto'">
      <div class="flex items-start gap-3">
        <span class="w-7 h-7 rounded-full bg-amber-100 text-amber-800 flex items-center justify-center flex-shrink-0"><Icono nombre="regresar" class="w-4 h-4" /></span>
        <div class="flex-1 min-w-0">
          <p class="text-[13px] font-semibold text-amber-950">
            {{ e.devuelto_por_nombre || "Dirección" }} lo regresó para corregir
          </p>
          <p v-if="e.motivo_devolucion" class="mt-1.5 text-[13.5px] leading-snug text-amber-950 bg-white/70 rounded-lg px-3 py-2 whitespace-pre-line">“{{ e.motivo_devolucion }}”</p>
          <p class="text-[11.5px] text-amber-800 mt-1.5">Corrígelo y vuelve a enviarlo. Lo que se dijo está en Actividad.</p>
        </div>
        <button v-if="e.puede_enviar" type="button" class="p-btn-primary flex-shrink-0" :disabled="ocupado" @click="dialogo = 'enviar'">
          Ya lo corregí · Reenviar
        </button>
      </div>
    </template>

    <!-- En aprobación -->
    <template v-else-if="e.estado === 'Pendiente' || e.estado === 'Revisado'">
      <div class="flex items-center gap-3 flex-wrap">
        <span class="p-dot" :class="e.estado === 'Revisado' ? 'p-dot-fac' : 'p-dot-now'"></span>
        <div class="flex-1 min-w-[200px]">
          <p class="text-[13px] font-semibold text-ink">
            {{ e.estado === "Revisado" ? "Revisado · esperando a Dirección" : (e.nivel === "doble" ? "En revisión" : "Esperando aprobación de Dirección") }}
          </p>
          <p class="p-meta">
            Envió {{ e.enviado_por_nombre || "—" }}<template v-if="e.enviado_en"> · {{ haceCuanto(e.enviado_en) }}</template>
            <template v-if="e.revisado_por"> · <Icono nombre="check" class="w-3.5 h-3.5 inline -mt-0.5" :grosor="2.2" /> revisó {{ e.revisado_por }}</template>
          </p>
          <p v-if="e.cambio_tras_envio" class="text-[12px] text-amber-800 mt-0.5"><Icono nombre="alerta" class="w-3.5 h-3.5 inline -mt-0.5" /> Cambió después de enviarse: quien decide lo verá en la Actividad.</p>
        </div>
        <div v-if="e.puede_regresar || e.puede_revisar || e.puede_aprobar" class="flex gap-2 flex-shrink-0">
          <button v-if="e.puede_regresar" type="button" class="p-btn-secondary text-red-700 border-red-200 hover:bg-red-50" :disabled="ocupado" @click="dialogo = 'regresar'">Regresar</button>
          <button v-if="e.puede_revisar" type="button" class="p-btn bg-violet-600 text-white hover:bg-violet-700" :disabled="ocupado" @click="dialogo = 'revisar'">Marcar revisado</button>
          <button v-if="e.puede_aprobar" type="button" class="p-btn-primary" :disabled="ocupado" @click="dialogo = 'aprobar'">Aprobar</button>
        </div>
      </div>
    </template>

    <!-- Borrador, para quien no puede validar -->
    <template v-else-if="e.puede_enviar && !e.puede_validar_directo">
      <div class="flex items-center gap-3 flex-wrap">
        <span class="p-dot p-dot-off"></span>
        <p class="flex-1 min-w-[200px] text-[13px] text-ink-muted">
          {{ e.nivel === "doble" ? "Pasa por revisión y después por Dirección." : "Necesita la aprobación de Dirección para validarse." }}
        </p>
        <button type="button" class="p-btn-primary flex-shrink-0" :disabled="ocupado" @click="dialogo = 'enviar'">Enviar a aprobación</button>
      </div>
    </template>

    <p v-if="error" class="text-[12.5px] text-red-700 mt-2">{{ error }}</p>
  </div>

  <DialogoMotivo
    :abierto="dialogo === 'regresar'" titulo="Regresar a corregir" peligro obligatorio
    :ayuda="`Le llega a <b>${e?.enviado_por_nombre || 'quien lo capturó'}</b> en la campana y por correo. El documento no se borra: sigue en borrador para que lo corrija.`"
    etiqueta="¿Qué tiene que corregir?" :sugerencias="SUGERENCIAS"
    :boton="`Regresar a ${(e?.enviado_por_nombre || 'su autor').split(' ')[0]}`"
    :ocupado="ocupado" :error="error" @cerrar="cerrar" @confirmar="(t) => accion('regresar', { motivo: t })"
  />
  <DialogoMotivo
    :abierto="dialogo === 'enviar'" :titulo="e?.estado === 'Devuelto' ? 'Reenviar a aprobación' : 'Enviar a aprobación'"
    :ayuda="e?.nivel === 'doble' ? 'Primero lo revisa el revisor y después Dirección. A los dos les llega el aviso.' : 'Le llega a Dirección en la campana y por correo.'"
    :etiqueta="e?.estado === 'Devuelto' ? '¿Qué corregiste? (opcional, ayuda a quien revisa)' : 'Comentario (opcional)'"
    :boton="e?.estado === 'Devuelto' ? 'Reenviar' : 'Enviar'" :ocupado="ocupado" :error="error"
    @cerrar="cerrar" @confirmar="(t) => accion('enviar_a_aprobacion', { comentario: t })"
  />
  <DialogoMotivo
    :abierto="dialogo === 'revisar'" titulo="Marcar revisado" etiqueta="Comentario (opcional)"
    ayuda="Pasa a la bandeja de Dirección y le llega el aviso." boton="Marcar revisado"
    :ocupado="ocupado" :error="error" @cerrar="cerrar" @confirmar="(t) => accion('marcar_revisado', { comentario: t })"
  />
  <DialogoMotivo
    :abierto="dialogo === 'aprobar'" titulo="Aprobar" etiqueta="Comentario (opcional)"
    :ayuda="`Se valida en ERPNext y se le avisa a ${e?.enviado_por_nombre || 'quien lo envió'}.`" boton="Sí, aprobar"
    :ocupado="ocupado" :error="error" @cerrar="cerrar" @confirmar="(t) => accion('aprobar', { comentario: t })"
  />
</template>

<script setup>
import { computed, ref, watch } from "vue";
import DialogoMotivo from "@/components/aprobacion/DialogoMotivo.vue";
import Icono from "@/components/Icono.vue";
import { call } from "@/utils/frappe.js";
import { haceCuanto } from "@/utils/formato.js";

const props = defineProps({
  doctype: { type: String, required: true },
  name: { type: String, default: "" },
  // La pantalla guarda lo que esté editando antes de enviarlo (devuelve una promesa).
  guardar: { type: Function, default: null },
  // Para el documento que esté abierto pero no sea el de la franja (p. ej. otro paso).
  visible: { type: Boolean, default: true },
});
const emit = defineEmits(["estado", "cambio"]);

const SUGERENCIAS = ["Falta un adjunto", "Precio incorrecto", "Cantidad incorrecta", "Pide otra cotización"];

const e = ref(null);
const dialogo = ref("");
const ocupado = ref(false);
const error = ref("");

// Solo se dibuja si alguna rama tiene algo que decir: para quien valida directo, un
// borrador no lleva franja (antes quedaba una caja gris vacía arriba del documento).
const conContenido = computed(() => !!e.value && (
  ["Devuelto", "Pendiente", "Revisado"].includes(e.value.estado)
  || (e.value.puede_enviar && !e.value.puede_validar_directo)));
const caja = computed(() => {
  if (!e.value) return "";
  if (e.value.estado === "Devuelto") return "bg-amber-50 border-amber-300";
  if (e.value.estado === "Pendiente" || e.value.estado === "Revisado") return "bg-brand-50/60 border-brand-200";
  return "bg-surface-raised border-surface-border";
});

async function cargar() {
  if (!props.name || props.name === "nueva" || props.name === "nuevo") { e.value = null; emit("estado", null); return; }
  try {
    e.value = await call("costeo_yelke.api.aprobaciones.estado_aprobacion", { doctype: props.doctype, name: props.name });
  } catch {
    e.value = null;
  }
  emit("estado", e.value);
}

function cerrar() {
  dialogo.value = "";
  error.value = "";
}

async function accion(metodo, args) {
  ocupado.value = true;
  error.value = "";
  try {
    if (metodo === "enviar_a_aprobacion" && props.guardar) await props.guardar();
    await call(`costeo_yelke.api.aprobaciones.${metodo}`, { doctype: props.doctype, name: props.name, ...args });
    dialogo.value = "";
    await cargar();
    emit("cambio", metodo);
  } catch (err) {
    error.value = err.message || "No se pudo completar.";
  } finally {
    ocupado.value = false;
  }
}

watch(() => [props.doctype, props.name], cargar, { immediate: true });
defineExpose({ recargar: cargar });
</script>
