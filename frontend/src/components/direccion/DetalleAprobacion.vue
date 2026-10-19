<!--
  Detalle de un documento en el panel de Dirección: lo que decide la aprobación
  arriba (monto, contraparte, alertas), renglones plegados, adjuntos, actividad,
  y la barra de acciones fija abajo (regla de Producción: la primaria a la derecha).

  Llena el alto de su contenedor: el cuerpo hace scroll y la barra queda fija.
  `fila` es la tarjeta de la bandeja; aquí se pide la ficha completa
  (api/direccion.get_resumen_documento).
-->
<template>
  <div class="flex flex-col h-full min-h-0 bg-surface">
    <div class="flex-1 overflow-y-auto">
      <div v-if="cargando && !d" class="p-6 text-center p-meta">Cargando…</div>
      <div v-else-if="error && !d" class="p-6"><p class="text-[13px] text-red-700">{{ error }}</p></div>
      <template v-else-if="d">
        <div class="px-5 pt-4 pb-5 bg-white border-b border-surface-border">
          <div class="flex items-center gap-2">
            <span :class="TIPOS_DOC[d.tipo]?.pill || 'p-pill-off'">{{ d.etiqueta }}</span>
            <span class="text-[11.5px] text-ink-light font-mono truncate">{{ fila.tipo === "precio" ? fila.name : d.name }}</span>
          </div>
          <p class="text-[22px] font-semibold tracking-tight mt-2 leading-tight">{{ d.titulo }}</p>
          <p v-if="d.monto != null" class="text-[28px] font-semibold tabular-nums tracking-tight mt-0.5">{{ dinero(d.monto, d.moneda) }}</p>
          <p v-if="d.contexto" class="p-meta mt-1">{{ d.contexto }}</p>
          <div class="flex items-center gap-1.5 mt-3 text-[12px] text-ink-muted flex-wrap">
            <span class="w-5 h-5 rounded-full flex items-center justify-center text-[8.5px] font-semibold" :class="colorAvatar(fila.por)">{{ iniciales(d.por_nombre || fila.por_nombre) }}</span>
            Envió {{ d.por_nombre || fila.por_nombre }} · {{ haceCuanto(d.enviado_en || fila.enviado_en) }}
            <span v-if="d.revisado_por_nombre" class="text-violet-700">· ✓ revisó {{ primerNombre(d.revisado_por_nombre) }}</span>
          </div>
        </div>

        <div class="px-4 py-4 space-y-4">
          <div
            v-for="(a, i) in d.alertas" :key="i"
            class="rounded-xl border px-3.5 py-2.5 text-[12.5px] leading-snug flex gap-2"
            :class="a.tono === 'bad' ? 'bg-red-50 border-red-200 text-red-800' : 'bg-amber-50 border-amber-200 text-amber-900'"
          ><span>{{ a.tono === "bad" ? "⛔" : "⚠️" }}</span><span>{{ a.texto }}</span></div>

          <div class="p-panel divide-y divide-surface-border">
            <div v-for="(r, i) in d.resumen" :key="i" class="flex items-start justify-between gap-4 px-4 py-2.5">
              <span class="p-meta">{{ r.etiqueta }}</span>
              <span class="text-[13px] font-medium text-right tabular-nums break-words min-w-0">{{ valor(r) }}</span>
            </div>
          </div>

          <details v-if="d.renglones.length" class="p-panel group" :open="!movil">
            <summary class="px-4 h-11 flex items-center justify-between cursor-pointer list-none text-[13px] font-medium">
              {{ fila.tipo === "precio" ? "Precios" : "Renglones" }} ({{ d.renglones.length }})
              <span class="text-ink-light group-open:rotate-90 transition">›</span>
            </summary>
            <div class="border-t border-surface-border">
              <div v-for="(r, i) in d.renglones" :key="i" class="px-4 py-2.5 border-b border-surface-border last:border-0">
                <p class="text-[13px] font-medium">{{ r.descripcion }}</p>
                <p class="p-meta tabular-nums flex justify-between gap-3">
                  <span>{{ r.cantidad != null ? `${numero(r.cantidad, 3)} ${r.unidad || ""} × ${dinero(r.precio, r.moneda)}` : "" }}</span>
                  <span class="text-ink font-medium">{{ dinero(r.importe, r.moneda) }}</span>
                </p>
                <p v-if="r.nota" class="text-[11.5px] text-ink-light">{{ r.nota }}</p>
              </div>
            </div>
          </details>

          <div v-if="d.adjuntos.length" class="flex flex-wrap gap-2">
            <a
              v-for="a in d.adjuntos" :key="a.url" :href="a.url" target="_blank"
              class="h-8 px-3 rounded-full border border-surface-border bg-white text-[12.5px] text-ink-muted font-medium inline-flex items-center gap-1.5 hover:bg-surface-raised max-w-full"
            >📎 <span class="truncate">{{ a.nombre }}</span></a>
          </div>

          <div>
            <div class="flex items-center justify-between mb-3">
              <p class="p-eyebrow">Actividad</p>
              <RouterLink v-if="rutaSpa" :to="rutaSpa" class="text-[12px] text-brand-600 font-medium">Abrir el documento completo ›</RouterLink>
            </div>
            <div class="p-panel p-4">
              <ActividadDocumento ref="actividad" :doctype="fila.doctype" :name="fila.name" :ultimos="movil ? 3 : 6" />
            </div>
          </div>
        </div>
      </template>
    </div>

    <div v-if="d && (puedeRegresar || puedeDecidir)" class="flex-shrink-0 bg-white border-t border-surface-border px-4 pt-2.5" :style="movil ? 'padding-bottom: max(14px, env(safe-area-inset-bottom))' : 'padding-bottom: 12px'">
      <p v-if="d.bloqueo" class="text-center text-[11.5px] text-red-700 mb-2">{{ d.bloqueo }}: no se puede aprobar todavía.</p>
      <p v-else-if="error" class="text-center text-[11.5px] text-red-700 mb-2">{{ error }}</p>
      <div class="flex gap-2" :class="movil ? '' : 'justify-end'">
        <button
          v-if="puedeRegresar" type="button"
          class="p-btn bg-white text-red-700 border border-red-200 hover:bg-red-50" :class="movil ? 'h-12 flex-1 text-[14px]' : ''"
          :disabled="ocupado" @click="dialogo = 'regresar'"
        >Regresar</button>
        <button
          v-if="esRevision" type="button"
          class="p-btn bg-violet-600 text-white hover:bg-violet-700" :class="movil ? 'h-12 flex-[1.4] text-[14px]' : ''"
          :disabled="ocupado" @click="ejecutar('marcar_revisado')"
        >{{ ocupado ? "Un momento…" : "Marcar revisado" }}</button>
        <button
          v-else-if="puedeDecidir" type="button"
          class="p-btn-primary" :class="movil ? 'h-12 flex-[1.4] text-[14px]' : ''"
          :disabled="ocupado || !!d.bloqueo" @click="aprobarClic"
        >{{ d.bloqueo ? "No se puede aprobar" : (ocupado ? "Un momento…" : "Aprobar") }}</button>
      </div>
    </div>

    <DialogoMotivo
      :abierto="dialogo === 'regresar'" titulo="Regresar a corregir" peligro obligatorio
      :ayuda="`Le llega a <b>${d?.por_nombre || fila.por_nombre}</b> en la campana y por correo. El documento no se borra: sigue en borrador para que lo corrija.`"
      etiqueta="¿Qué tiene que corregir?" :sugerencias="SUGERENCIAS"
      :boton="`Regresar a ${primerNombre(d?.por_nombre || fila.por_nombre)}`"
      :ocupado="ocupado" :error="error" @cerrar="cerrarDialogo" @confirmar="(t) => ejecutar('regresar', t)"
    />
    <DialogoMotivo
      :abierto="dialogo === 'aprobar'" :titulo="`¿Aprobar ${d?.monto != null ? dinero(d.monto, d.moneda) : ''}?`"
      :ayuda="`${d?.etiqueta} · ${d?.titulo}. Se valida en ERPNext y se le avisa a ${d?.por_nombre || fila.por_nombre}.`"
      etiqueta="Comentario (opcional)" boton="Sí, aprobar"
      :ocupado="ocupado" :error="error" @cerrar="cerrarDialogo" @confirmar="(t) => ejecutar('aprobar', t)"
    />
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import ActividadDocumento from "@/components/aprobacion/ActividadDocumento.vue";
import DialogoMotivo from "@/components/aprobacion/DialogoMotivo.vue";
import { call } from "@/utils/frappe.js";
import { TIPOS_DOC, colorAvatar, dinero, fecha, haceCuanto, iniciales, numero } from "@/utils/formato.js";

const props = defineProps({
  fila: { type: Object, required: true },
  movil: { type: Boolean, default: false },
});
const emit = defineEmits(["resuelto"]);

const SUGERENCIAS = ["Falta un adjunto", "Precio incorrecto", "Cantidad incorrecta", "Pide otra cotización"];
// A partir de este monto, Aprobar pide confirmación (plan §4.2).
const MONTO_CONFIRMAR = 100000;

const d = ref(null);
const cargando = ref(false);
const error = ref("");
const ocupado = ref(false);
const dialogo = ref("");
const actividad = ref(null);

const primerNombre = (n) => String(n || "").split(" ")[0];
const esPrecio = computed(() => props.fila.tipo === "precio");
const est = computed(() => d.value?.estado || {});
const esRevision = computed(() => !esPrecio.value && est.value.puede_revisar && !est.value.puede_aprobar);
const puedeDecidir = computed(() => est.value.puede_aprobar || esRevision.value);
const puedeRegresar = computed(() => !!est.value.puede_regresar);
const rutaSpa = computed(() => (d.value?.ruta || "").replace(/^\/costeo-yelke/, "") || null);

function valor(r) {
  if (r.tipo === "moneda") return dinero(r.valor, r.moneda);
  if (r.tipo === "porcentaje") return `${Number(r.valor || 0).toFixed(1)} %`;
  if (r.tipo === "fecha") return fecha(r.valor);
  return r.valor;
}

async function cargar() {
  cargando.value = true;
  error.value = "";
  try {
    d.value = await call("costeo_yelke.api.direccion.get_resumen_documento", {
      doctype: props.fila.doctype, name: props.fila.name, tipo: props.fila.tipo === "precio" ? "precio" : null,
    });
  } catch (e) {
    error.value = e.message || "No se pudo cargar el documento.";
  } finally {
    cargando.value = false;
  }
}

function aprobarClic() {
  if ((d.value?.monto || 0) >= MONTO_CONFIRMAR) dialogo.value = "aprobar";
  else ejecutar("aprobar", "");
}

function cerrarDialogo() {
  dialogo.value = "";
  error.value = "";
}

async function ejecutar(accion, texto) {
  ocupado.value = true;
  error.value = "";
  try {
    if (esPrecio.value) {
      if (accion === "aprobar") await call("costeo_yelke.api.aprobaciones.aprobar_precios", { costeo: props.fila.name, comentario: texto });
      else await call("costeo_yelke.api.aprobaciones.regresar_precios", { costeo: props.fila.name, motivo: texto });
    } else {
      const args = { doctype: props.fila.doctype, name: props.fila.name };
      if (accion === "regresar") args.motivo = texto; else args.comentario = texto;
      await call(`costeo_yelke.api.aprobaciones.${accion}`, args);
    }
    dialogo.value = "";
    emit("resuelto", { accion, fila: props.fila, texto });
  } catch (e) {
    error.value = e.message || "No se pudo completar.";
  } finally {
    ocupado.value = false;
  }
}

watch(() => [props.fila.doctype, props.fila.name, props.fila.tipo], cargar, { immediate: true });
</script>
