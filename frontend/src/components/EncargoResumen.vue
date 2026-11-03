<template>
  <!-- Resumen de UN encargo al taller (Subcontracting Order): qué se le manda, de
       dónde sale y si alcanza, qué va a entregar y cuánto se le paga. Lo usan la
       pestaña del encargo y la de transferencia (antes de enviar), en todas las
       etapas -- datos de sub_get_flujo. -->
  <div class="bg-white rounded-xl border border-surface-border p-4 space-y-4">
    <!-- Folio, taller y estado ya están en el encabezado del paso; aquí solo la fecha. -->
    <p v-if="sco.schedule_date" class="text-[12px] text-ink-muted">Fecha requerida: <span class="text-ink">{{ fecha(sco.schedule_date) }}</span></p>

    <!-- Lo que sale de tus almacenes hacia el taller -->
    <div>
      <p class="section-title mb-1.5">Se le manda al taller <span class="font-normal text-ink-light">→ {{ sco.supplier_warehouse || 'almacén del taller' }}</span></p>
      <div v-if="materiales.length" class="overflow-x-auto">
        <table class="w-full text-[12.5px]">
          <thead>
            <tr class="text-left text-[11px] font-semibold text-ink-light border-b border-surface-border">
              <th class="py-1.5">Material o pieza</th>
              <th class="py-1.5 w-24 text-right">Cantidad</th>
              <th class="py-1.5 w-16 pl-2">UDM</th>
              <th class="py-1.5 w-44">Sale de</th>
              <th class="py-1.5 w-24 text-right">{{ enviado ? 'Enviado' : 'Disponible' }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in materiales" :key="m.rm_item_code" class="border-b border-surface-border/60">
              <td class="py-1.5 pr-2">
                <div class="text-ink">{{ nombre(m.item_name || m.rm_item_code).titulo }}</div>
                <div v-if="nombre(m.item_name || m.rm_item_code).sub" class="text-[10.5px] text-ink-light">{{ nombre(m.item_name || m.rm_item_code).sub }}</div>
              </td>
              <!-- Materiales en unidades cerradas: las fracciones son del reparto interno por pieza. -->
              <td class="py-1.5 pr-2 text-right tabular-nums">{{ enCompra(m, m.required_qty) }}</td>
              <td class="py-1.5 pl-2 text-ink-muted text-[11px]">
                <template v-if="m.uom_envio">{{ m.uom_envio }}<span class="block text-[10.5px] text-ink-light whitespace-nowrap">{{ entero(m.required_qty) }} {{ m.stock_uom }}</span></template>
                <template v-else>{{ m.stock_uom }}</template>
              </td>
              <td class="py-1.5 pr-2 text-ink-muted text-[11.5px]">{{ m.sale_de || '—' }}</td>
              <td v-if="enviado" class="py-1.5 text-right tabular-nums text-ink-muted">{{ enCompra(m, m.supplied_qty) }}</td>
              <td v-else class="py-1.5 text-right tabular-nums" :class="m.falta ? 'text-red-600 font-semibold' : 'text-ink-muted'">{{ m.disponible === null || m.disponible === undefined ? '—' : num(m.uom_envio ? m.disponible / m.factor_envio : m.disponible) }}</td>
            </tr>
          </tbody>
        </table>
        <p v-if="!enviado && materiales.some((m) => m.falta)" class="text-[11.5px] text-red-600 mt-1.5">
          No alcanza lo que hay en el almacén de origen para todo el encargo — recibe la materia prima o la etapa anterior antes de enviar.
        </p>
      </div>
      <p v-else class="text-[12px] text-ink-light">Este encargo no lleva material ni piezas de otra etapa.</p>
    </div>

    <!-- Lo que el taller regresa -->
    <div v-if="piezas.length">
      <p class="section-title mb-1.5">El taller entrega <span class="font-normal text-ink-light">→ {{ sco.set_warehouse || 'almacén de destino' }}</span></p>
      <div class="overflow-x-auto">
        <table class="w-full text-[12.5px]">
          <thead>
            <tr class="text-left text-[11px] font-semibold text-ink-light border-b border-surface-border">
              <th class="py-1.5">Pieza / producto</th>
              <th class="py-1.5 w-24 text-right">Cantidad</th>
              <th class="py-1.5 w-16 pl-2">UDM</th>
              <th class="py-1.5 w-24 text-right">Recibido</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in piezas" :key="p.item_code" class="border-b border-surface-border/60">
              <td class="py-1.5 pr-2">
                <div class="text-ink">{{ nombre(p.item_name || p.item_code).titulo }}</div>
                <div v-if="nombre(p.item_name || p.item_code).sub" class="text-[10.5px] text-ink-light">{{ nombre(p.item_name || p.item_code).sub }}</div>
              </td>
              <td class="py-1.5 pr-2 text-right tabular-nums">{{ num(p.qty) }}</td>
              <td class="py-1.5 pl-2 text-ink-muted text-[11px]">{{ p.stock_uom }}</td>
              <td class="py-1.5 text-right tabular-nums" :class="p.received_qty >= p.qty ? 'text-green-700' : 'text-ink-muted'">{{ num(p.received_qty) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Lo que se le paga -->
    <div v-if="servicios.length">
      <p class="section-title mb-1.5">Se le paga</p>
      <div class="overflow-x-auto">
        <table class="w-full text-[12.5px]">
          <thead>
            <tr class="text-left text-[11px] font-semibold text-ink-light border-b border-surface-border">
              <th class="py-1.5">Servicio</th>
              <th class="py-1.5 w-24 text-right">Cantidad</th>
              <th class="py-1.5 w-24 text-right">Precio</th>
              <th class="py-1.5 w-28 text-right">Importe</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(s, i) in servicios" :key="i" class="border-b border-surface-border/60">
              <td class="py-1.5 pr-2">
                <div class="text-ink">{{ s.item_name || s.item_code }}</div>
                <div class="text-[10.5px] text-ink-light">{{ nombre(s.fg_item || '').sub }}</div>
              </td>
              <td class="py-1.5 pr-2 text-right tabular-nums">{{ num(s.qty) }}</td>
              <td class="py-1.5 pr-2 text-right tabular-nums">{{ money(s.rate) }}</td>
              <td class="py-1.5 text-right tabular-nums">{{ money(s.amount) }}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr>
              <td colspan="3" class="pt-2 text-right text-[11.5px] text-ink-muted">Total del encargo (sin IVA)</td>
              <td class="pt-2 text-right tabular-nums font-semibold text-ink">{{ money(importe) }}</td>
            </tr>
          </tfoot>
        </table>
      </div>
      <p class="text-[11px] text-ink-light mt-1">Cuando un servicio cubre varias piezas, el precio por prenda se cobra completo en una sola de ellas; las demás van en $0 y no se listan.</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  sco: { type: Object, required: true },
  materiales: { type: Array, default: () => [] },
  piezas: { type: Array, default: () => [] },
  servicios: { type: Array, default: () => [] },
  importe: { type: Number, default: 0 },
  // {código de pieza: nombre real} -- «PUNOS» -> «PUÑOS» (el código pierde la ñ).
  nombresPieza: { type: Object, default: () => ({}) },
});

const enviado = computed(() => !!props.sco?.transfer?.done);

// "CHAMARRA-INDUSTRIAL-PRUEBA-XXL · FRENTE-IZQUIERDO-AB" -> pieza arriba, producto abajo.
function nombre(texto) {
  const t = String(texto || "");
  const i = t.indexOf(" · ");
  if (i < 0) return { titulo: t, sub: "" };
  // Sin el sufijo de estado interno de la pieza (-C, -CR…): «BOLSA-C» -> «BOLSA».
  const slug = t.slice(i + 3).replace(/-[A-Z]{1,4}$/, "");
  return { titulo: props.nombresPieza[slug] || slug.replace(/-/g, " "), sub: t.slice(0, i) };
}
const entero = (v) => Math.ceil((Number(v) || 0) - 1e-6).toLocaleString("es-MX");
// En la UDM en que se compró (Rollo de 100 m): paquetes completos si no se divide.
function enCompra(m, v) {
  if (!m.uom_envio) return entero(v);
  const q = (Number(v) || 0) / (Number(m.factor_envio) || 1);
  return m.envio_entero ? entero(q) : num(Math.round(q * 100) / 100);
}
const num = (v) => (Number(v) || 0).toLocaleString("es-MX", { maximumFractionDigits: 3 });
const money = (v) => (Number(v) || 0).toLocaleString("es-MX", { style: "currency", currency: "MXN" });
function fecha(d) {
  const [y, m, dd] = String(d).slice(0, 10).split("-");
  return y && m && dd ? `${dd}/${m}/${y}` : d;
}
</script>
