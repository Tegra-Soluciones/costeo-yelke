<!--
  Resumen (solo Director): los indicadores del tablero de Inicio (mismo cálculo,
  dashboard_metrics), lo que requiere atención y la delegación de aprobaciones.
-->
<template>
  <div class="px-4 lg:px-0 py-4 space-y-4">
    <div v-if="cargando && !r" class="p-8 text-center p-meta">Cargando…</div>
    <p v-else-if="error" class="text-[13px] text-red-700">{{ error }}</p>
    <template v-else-if="r">
      <div class="grid grid-cols-2 lg:grid-cols-3 gap-px bg-surface-border rounded-xl overflow-hidden border border-surface-border">
        <div v-for="k in kpis" :key="k.l" class="bg-white p-4">
          <p class="p-meta">{{ k.l }}</p>
          <p class="text-[21px] font-semibold tabular-nums mt-0.5 tracking-tight">{{ k.v }}</p>
          <p v-if="k.s" class="text-[11.5px] text-ink-muted mt-0.5">{{ k.s }}</p>
          <div v-if="k.w != null" class="h-1 bg-zinc-100 rounded mt-2"><div class="h-1 bg-brand-500 rounded" :style="`width:${Math.min(100, k.w)}%`"></div></div>
        </div>
      </div>

      <div>
        <p class="p-eyebrow mb-2">Requiere tu atención</p>
        <div class="p-panel divide-y divide-surface-border">
          <button v-for="a in atencion" :key="a.t" type="button" class="w-full text-left px-4 h-12 flex items-center gap-3 text-[13px]" @click="emit('ir', a.ir)">
            <span class="p-dot" :class="a.d"></span><span class="flex-1">{{ a.t }}</span><span class="text-ink-light">›</span>
          </button>
          <p v-if="!atencion.length" class="px-4 h-12 flex items-center gap-2 text-[13px] text-ink-muted"><Icono nombre="check-circulo" class="w-4 h-4 text-emerald-600" />Nada pendiente</p>
        </div>
      </div>
    </template>

    <!-- Delegación de aprobaciones (vacaciones) -->
    <div v-if="dlg" class="p-panel p-4">
      <template v-if="dlg.activa">
        <p class="text-[14px] font-semibold">Delegación activa</p>
        <p class="p-meta mt-0.5">{{ dlg.activa.a_nombre }} aprueba por ti del {{ fecha(dlg.activa.desde) }} al {{ fecha(dlg.activa.hasta) }}. Termina sola.</p>
        <button type="button" class="p-btn-secondary w-full h-11 mt-3" :disabled="ocupado" @click="terminar(dlg.activa)">Terminar ahora</button>
      </template>
      <template v-else-if="dlg.programadas.length">
        <p class="text-[14px] font-semibold">Delegación programada</p>
        <p class="p-meta mt-0.5">{{ dlg.programadas[0].a_nombre }} aprobará por ti del {{ fecha(dlg.programadas[0].desde) }} al {{ fecha(dlg.programadas[0].hasta) }}.</p>
        <button type="button" class="p-btn-secondary w-full h-11 mt-3" :disabled="ocupado" @click="terminar(dlg.programadas[0])">Cancelarla</button>
      </template>
      <template v-else>
        <p class="text-[14px] font-semibold">¿Vas a salir unos días?</p>
        <p class="p-meta mt-0.5">Deja a alguien aprobando por ti. Se termina sola en la fecha que elijas.</p>
        <button type="button" class="p-btn-primary w-full h-11 mt-3" @click="emit('delegar')">Delegar mis aprobaciones</button>
      </template>
      <p v-if="errorDlg" class="text-[12px] text-red-700 mt-2">{{ errorDlg }}</p>
    </div>
    <p class="text-[11px] text-ink-light text-center pb-2">Año en curso, solo lo validado. Mismo cálculo que Inicio.</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import Icono from "@/components/Icono.vue";
import { call } from "@/utils/frappe.js";
import { dineroCorto, fecha, numero } from "@/utils/formato.js";

const props = defineProps({
  pendientes: { type: Number, default: 0 },
  bloqueadas: { type: Number, default: 0 },
  dlg: { type: Object, default: null },
});
const emit = defineEmits(["ir", "delegar", "delegacion"]);

const r = ref(null);
const cargando = ref(false);
const error = ref("");
const ocupado = ref(false);
const errorDlg = ref("");

// Los mismos indicadores (y el mismo cálculo) que Inicio, del año en curso.
const kpis = computed(() => {
  const t = r.value?.tablero;
  if (!t) return [];
  const v = t.ventas, c = t.compras, prod = t.produccion, mon = t.moneda;
  const pct = (a, b) => (b ? Math.round((a / b) * 100) : 0);
  return [
    { l: "Vendido", v: dineroCorto(v.vendido, mon), s: `${v.ordenes} órdenes · ${numero(v.prendas)} prendas` },
    { l: "Facturado", v: dineroCorto(v.facturado, mon), s: `${pct(v.facturado, v.vendido)} % de lo vendido`, w: pct(v.facturado, v.vendido) },
    { l: "Cotizaciones ganadas", v: v.conversion == null ? "—" : `${Math.round(v.conversion)} %`, s: `${dineroCorto(v.ganado, mon)} de ${dineroCorto(v.cotizado, mon)}`, w: v.conversion },
    { l: "Margen estimado", v: v.margen == null ? "—" : `${v.margen.toFixed(1)} %`, s: "ponderado por lo vendido" },
    { l: "Compras", v: dineroCorto(c.material + c.maquila, mon), s: `material ${dineroCorto(c.material, mon)} · maquila ${dineroCorto(c.maquila, mon)}` },
    { l: "Maquila en curso", v: prod.avance == null ? "—" : `${Math.round(prod.avance)} %`, s: `${prod.completas} de ${prod.total} órdenes completas`, w: prod.avance },
  ];
});

const atencion = computed(() => {
  const out = [];
  if (props.pendientes) out.push({ d: "p-dot-wait", t: `${props.pendientes} documento(s) por aprobar`, ir: "aprobar" });
  if (r.value?.atrasados) out.push({ d: "p-dot-bad", t: `${r.value.atrasados} proyecto(s) con entrega vencida`, ir: "atrasados" });
  if (props.bloqueadas) out.push({ d: "p-dot-bad", t: `${props.bloqueadas} documento(s) bloqueados: les falta un adjunto`, ir: "aprobar" });
  return out;
});

async function cargar() {
  cargando.value = true;
  error.value = "";
  try {
    r.value = await call("costeo_yelke.api.direccion.get_resumen");
  } catch (e) {
    error.value = e.message || "No se pudo cargar el resumen.";
  } finally {
    cargando.value = false;
  }
}

async function terminar(f) {
  ocupado.value = true;
  errorDlg.value = "";
  try {
    emit("delegacion", await call("costeo_yelke.api.delegacion.terminar_delegacion", { name: f.name }), "terminada");
  } catch (e) {
    errorDlg.value = e.message || "No se pudo terminar la delegación.";
  } finally {
    ocupado.value = false;
  }
}

onMounted(cargar);
defineExpose({ recargar: cargar });
</script>
