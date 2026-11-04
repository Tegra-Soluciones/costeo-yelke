<!--
  Un producto del costeo, por prenda (api/direccion._desglose_costeo): precio y margen,
  costo unitario por concepto, materiales y servicios. Lo usa el detalle de aprobación
  para el costeo y para «Costeo del proyecto» en los demás documentos.
-->
<template>
<div class="p-panel overflow-hidden">
    <div class="px-4 py-3 border-b border-surface-border">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <p class="text-[13.5px] font-semibold leading-snug">{{ p.producto }}</p>
          <p class="p-meta">{{ p.talla ? `${p.talla} · ` : "" }}{{ numero(p.cantidad) }} prendas</p>
        </div>
        <div class="text-right flex-shrink-0">
          <p class="text-[13.5px] font-semibold tabular-nums">{{ dinero(p.precio, p.moneda) }}</p>
          <p class="text-[11.5px] tabular-nums" :class="p.margen < 20 ? 'text-red-700' : 'text-emerald-700'">margen {{ Number(p.margen).toFixed(1) }} %</p>
        </div>
      </div>
    </div>
    <!-- Costo unitario por concepto -->
    <div class="px-4 py-2.5 space-y-1">
      <div v-for="c in p.costos" :key="c.concepto" class="flex items-center gap-3 text-[12.5px]">
        <span class="text-ink-muted flex-1">{{ c.concepto }}</span>
        <span class="w-16 h-1 bg-zinc-100 rounded hidden sm:block"><span class="block h-1 rounded bg-brand-400" :style="`width:${Math.min(100, (c.monto / (p.costo_unitario || 1)) * 100)}%`"></span></span>
        <span class="tabular-nums w-20 text-right">{{ dinero(c.monto, p.moneda) }}</span>
      </div>
      <div class="flex items-center gap-3 text-[12.5px] font-semibold border-t border-surface-border pt-1.5 mt-1">
        <span class="flex-1">Costo por prenda</span><span class="tabular-nums">{{ dinero(p.costo_unitario, p.moneda) }}</span>
      </div>
    </div>
    <!-- Materiales -->
    <details v-if="p.materiales.length" class="border-t border-surface-border group/m" :open="!movil">
      <summary class="px-4 h-10 flex items-center justify-between cursor-pointer list-none text-[12.5px] font-medium">
        Materiales ({{ p.materiales.length }})<span class="text-ink-light group-open/m:rotate-90 transition">›</span>
      </summary>
      <div class="px-4 pb-2">
        <div v-for="(m, j) in p.materiales" :key="j" class="py-1.5 border-t border-surface-border/70 first:border-0">
          <div class="flex justify-between gap-3 text-[12.5px]">
            <span class="font-medium min-w-0">{{ m.descripcion }}<span v-if="m.tipo" class="text-ink-light font-normal"> · {{ m.tipo }}</span></span>
            <span class="tabular-nums whitespace-nowrap">{{ dinero(m.total, p.moneda) }}</span>
          </div>
          <p class="text-[11.5px] text-ink-muted tabular-nums">
            {{ numero(m.cantidad, 4) }} {{ m.unidad }} × {{ dinero(m.precio_unitario, p.moneda) }}<template v-if="m.proveedor"> · {{ m.proveedor }}</template><template v-if="m.pieza"> · {{ m.pieza }}</template>
          </p>
        </div>
      </div>
    </details>
    <!-- Servicios por etapa -->
    <details v-if="p.servicios.length" class="border-t border-surface-border group/s" :open="!movil">
      <summary class="px-4 h-10 flex items-center justify-between cursor-pointer list-none text-[12.5px] font-medium">
        Servicios ({{ p.servicios.length }})<span class="text-ink-light group-open/s:rotate-90 transition">›</span>
      </summary>
      <div class="px-4 pb-2">
        <div v-for="(s, j) in p.servicios" :key="j" class="py-1.5 border-t border-surface-border/70 first:border-0">
          <div class="flex justify-between gap-3 text-[12.5px]">
            <span class="font-medium min-w-0"><span class="text-ink-light font-normal">Etapa {{ s.etapa }} · </span>{{ s.descripcion }}</span>
            <span class="tabular-nums whitespace-nowrap">{{ dinero(s.total, p.moneda) }}</span>
          </div>
          <p class="text-[11.5px] text-ink-muted">{{ s.proveedor || "Sin taller" }}<template v-if="s.pieza"> · {{ s.pieza }}</template></p>
        </div>
      </div>
    </details>
  </div>
</template>

<script setup>
import { dinero, numero } from "@/utils/formato.js";

defineProps({
  p: { type: Object, required: true },
  movil: { type: Boolean, default: false },
});
</script>
