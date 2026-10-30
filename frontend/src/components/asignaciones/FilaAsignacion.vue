<!--
  Renglón compacto de una asignación (mismo renglón que las listas de Producción):
  punto de estado · paso y proyecto · quién y cuándo · pill a la derecha. El clic abre
  el detalle en el panel lateral.
-->
<template>
  <FilaLista :estado="punto" :titulo="titulo" :meta="meta" @abrir="emit('abrir', f)">
    <template #derecha>
      <span v-if="pill" :class="pill[1]" class="flex-shrink-0">{{ pill[0] }}</span>
      <span v-else-if="f.fecha" class="text-[12px] text-ink-muted tabular-nums whitespace-nowrap flex-shrink-0">{{ fechaCorta }}</span>
    </template>
  </FilaLista>
</template>

<script setup>
import { computed } from "vue";
import FilaLista from "@/components/produccion/FilaLista.vue";
import { ESTADO } from "@/composables/useEncargos.js";
import { useCompany } from "@/composables/useCompany.js";
import { fecha, haceCuanto } from "@/utils/formato.js";

const props = defineProps({
  f: { type: Object, required: true },
  // Qué nombre enseñar: "para" (responsable), "de" (quien asignó) o "ambos".
  quien: { type: String, default: "ambos" },
  conProyecto: { type: Boolean, default: true },
});
const emit = defineEmits(["abrir"]);
const { state: companyState } = useCompany();

const titulo = computed(() => {
  const paso = (props.f.vista ? props.f.etiqueta : "Proyecto completo") + (props.f.lote ? ` · ${props.f.lote}` : "");
  return props.conProyecto ? `${paso} · ${props.f.proyecto}` : paso;
});
const meta = computed(() => {
  const f = props.f;
  const quien = { para: f.para_nombre, de: `De ${f.de_nombre}` }[props.quien] || `${f.de_nombre} → ${f.para_nombre}`;
  const extra = f.estado === "abierto" ? `asignada ${haceCuanto(f.creado)}` : f.nota || "";
  const otraCompania = f.compania && f.compania !== companyState.selected ? f.compania : "";
  return [quien, props.conProyecto ? f.cliente : "", otraCompania, extra].filter(Boolean).join(" · ");
});
const punto = computed(() => {
  const f = props.f;
  if (f.estado === "abierto") return f.vencido || f.vence_hoy ? "bad" : "wait";
  return { hecho: "ok", regresado: "bad" }[f.estado] || "off";
});
const pill = computed(() => {
  const f = props.f;
  if (f.estado === "abierto") return f.vence_hoy ? ["Vence hoy", "p-pill-bad"] : f.vencido ? ["Vencida", "p-pill-bad"] : null;
  return ESTADO[f.estado];
});
const fechaCorta = computed(() => `vence ${fecha(props.f.fecha).replace(/-\d{4}$/, "")}`);
</script>
