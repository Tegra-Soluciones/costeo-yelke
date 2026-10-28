<!--
  Reparto de la entrega de un lote entre direcciones del cliente: un renglón por
  destino con cuántas prendas de cada producto van ahí. Con un solo destino (lo
  normal) ya viene lleno con todo lo pendiente a la dirección de envío de la OV.
  El botón que genera las remisiones vive en la barra de abajo (v-model con el
  reparto); aquí se arma y se valida. Dar de alta una dirección nueva del cliente
  también se hace aquí, sin salir de la entrega.
-->
<template>
  <div class="p-panel p-4">
    <div class="flex items-center justify-between gap-2 mb-3 flex-wrap">
      <div>
        <p class="text-[14px] font-semibold text-ink">¿A dónde se entrega?</p>
        <p class="p-meta">Una remisión por dirección. Si todo va al mismo lugar, deja un solo renglón.</p>
      </div>
      <div class="flex items-center gap-3">
        <button type="button" class="text-[12.5px] font-medium text-brand-600 hover:text-brand-700" :disabled="!libres.length" @click="agregar">+ Agregar dirección</button>
        <button type="button" class="text-[12.5px] text-ink-muted hover:text-ink" @click="nueva.error = ''; nueva.abierto = true">+ Nueva dirección</button>
      </div>
    </div>

    <!-- Alta de una dirección del cliente: modal con todo lo que pide ERPNext. -->
    <DireccionClienteModal :abierto="nueva.abierto" :cliente="cliente" :guardando="nueva.guardando" :error="nueva.error"
                           @cerrar="nueva.abierto = false" @guardar="guardarNueva" />

    <!-- Cuadrícula: dirección | una columna por producto | quitar. Mismas columnas en
         encabezado, renglones y totales, para que todo quede alineado. -->
    <div class="overflow-x-auto">
      <div class="min-w-max">
        <div class="grid gap-x-3 items-end pb-2 border-b border-surface-border text-[11px] font-medium text-ink-light" :style="columnas">
          <span>Dirección de envío</span>
          <span v-for="p in productos" :key="p.item_code" class="text-right leading-tight line-clamp-2 break-words" :title="p.item_name || p.item_code">{{ etiqueta(p) }}</span>
          <span></span>
        </div>
        <div v-for="(r, i) in modelo" :key="i" class="grid gap-x-3 items-start py-3 border-b border-surface-border/60" :style="columnas">
          <div class="min-w-0">
            <select v-model="r.shipping_address_name" class="p-field h-10">
              <option value="">— Elige la dirección —</option>
              <option v-for="d in direcciones" :key="d.value" :value="d.value" :disabled="usadaEnOtro(r, d.value)">{{ d.titulo }}{{ d.tipo === 'Billing' ? ' (facturación)' : '' }}{{ usadaEnOtro(r, d.value) ? ' · ya en otro renglón' : '' }}</option>
            </select>
            <p class="text-[11px] text-ink-light mt-1.5 truncate min-h-[16px]" :title="detalle(r.shipping_address_name)">{{ detalle(r.shipping_address_name) }}</p>
          </div>
          <input v-for="p in productos" :key="p.item_code" v-model.number="r.cantidades[p.item_code]" type="number" min="0" step="1" class="p-field h-10 text-right tabular-nums" />
          <button v-if="modelo.length > 1" type="button" class="h-10 w-8 flex items-center justify-center rounded-lg text-ink-light hover:text-red-600 hover:bg-red-50" title="Quitar este destino" @click="quitar(i)">✕</button>
          <span v-else></span>
        </div>
        <div class="grid gap-x-3 items-center pt-2.5 text-[12px]" :style="columnas">
          <span class="text-ink-muted">Por asignar</span>
          <span v-for="p in productos" :key="p.item_code" class="text-right tabular-nums" :class="falta(p) < 0 ? 'text-red-600 font-semibold' : falta(p) > 0 ? 'text-amber-700' : 'text-emerald-700'">
            {{ falta(p) === 0 ? '✓ completo' : falta(p).toLocaleString('es-MX') }}
          </span>
          <span></span>
        </div>
      </div>
    </div>
    <p v-if="aviso" class="text-[12px] mt-2" :class="avisoError ? 'text-red-600' : 'text-ink-muted'">{{ aviso }}</p>
  </div>
</template>

<script setup>
import { computed, reactive, watch } from "vue";
import { call } from "@/utils/frappe.js";
import DireccionClienteModal from "@/components/DireccionClienteModal.vue";

const props = defineProps({
  costeo: { type: String, required: true },
  salesOrder: { type: String, default: "" },
  // [{item_code, item_name, pendiente}] -- lo que el lote tiene por entregar.
  productos: { type: Array, default: () => [] },
  direcciones: { type: Array, default: () => [] },
  porDefecto: { type: String, default: "" },
  cliente: { type: String, default: "" },
  modelValue: { type: Array, default: () => [] },
});
const emit = defineEmits(["update:modelValue", "direcciones"]);

const modelo = reactive([]);
const nueva = reactive({ abierto: false, guardando: false, error: "" });

function renglon(dir, todo) {
  return { shipping_address_name: dir || "",
           cantidades: Object.fromEntries(props.productos.map((p) => [p.item_code, todo ? p.pendiente : 0])) };
}
// Al cambiar lo pendiente (otro lote, o ya se generaron remisiones) se reinicia: un
// solo destino, la dirección de envío de la OV, con todo.
watch(() => props.productos.map((p) => `${p.item_code}:${p.pendiente}`).join("|"), () => {
  modelo.splice(0, modelo.length, renglon(props.porDefecto, true));
}, { immediate: true });
watch(modelo, () => emit("update:modelValue", repartos.value), { deep: true, immediate: true });
// La dirección de la OV llega después (se pide aparte): se pone en el primer renglón
// que siga sin dirección.
watch(() => props.porDefecto, (d) => {
  const vacio = modelo.find((r) => !r.shipping_address_name);
  if (d && vacio && !modelo.some((r) => r.shipping_address_name === d)) vacio.shipping_address_name = d;
}, { immediate: true });

const repartos = computed(() => modelo.map((r) => ({
  shipping_address_name: r.shipping_address_name,
  items: props.productos.map((p) => ({ item_code: p.item_code, qty: Number(r.cantidades[p.item_code]) || 0 }))
    .filter((i) => i.qty > 0),
})));
const asignado = (p) => modelo.reduce((s, r) => s + (Number(r.cantidades[p.item_code]) || 0), 0);
const falta = (p) => Math.round((Number(p.pendiente) - asignado(p)) * 1000) / 1000;
const columnas = computed(() => ({ gridTemplateColumns: `minmax(18rem, 1fr) repeat(${props.productos.length}, 8.5rem) 2rem` }));
const libres = computed(() => props.direcciones.filter((d) => !modelo.some((r) => r.shipping_address_name === d.value)));
// Todas las direcciones a la vista; la que ya usa OTRO renglón se ve pero no se elige.
const usadaEnOtro = (r, v) => modelo.some((x) => x !== r && x.shipping_address_name === v);
const detalle = (v) => props.direcciones.find((d) => d.value === v)?.detalle || "";
// Variante de otro producto del lote («… - CABALLERO XXL»): solo lo que la distingue.
// Producto base que tiene variantes en el lote: «Tallas regulares», como en la OV.
const etiqueta = (p) => {
  const n = p.item_name || p.item_code;
  const base = props.productos.find((q) => q !== p && n.startsWith(`${q.item_name || q.item_code} - `));
  if (base) return n.slice((base.item_name || base.item_code).length + 3);
  const tieneVariantes = props.productos.some((q) => q !== p && (q.item_name || q.item_code).startsWith(`${n} - `));
  return tieneVariantes ? "TALLAS REGULARES" : n;
};

// Quien agrega un destino suele querer partir lo que falta: el nuevo trae lo pendiente.
function agregar() {
  const r = renglon(libres.value[0]?.value || "", false);
  for (const p of props.productos) r.cantidades[p.item_code] = Math.max(falta(p), 0);
  modelo.push(r);
}
function quitar(i) { modelo.splice(i, 1); }

const avisoError = computed(() => props.productos.some((p) => falta(p) < 0) || modelo.some((r) => !r.shipping_address_name));
const aviso = computed(() => {
  if (props.productos.some((p) => falta(p) < 0)) return "Repartiste más de lo que el lote tiene por entregar.";
  if (modelo.some((r) => !r.shipping_address_name)) return "Elige la dirección de cada renglón.";
  if (props.productos.some((p) => falta(p) > 0)) return "Lo que quede sin asignar se podrá remisionar después.";
  return "";
});

async function guardarNueva(datos) {
  nueva.guardando = true; nueva.error = "";
  try {
    const r = await call("costeo_yelke.api.costeo_api.crear_direccion_cliente", {
      costeo: props.costeo, sales_order: props.salesOrder || null, datos: JSON.stringify(datos),
    });
    emit("direcciones", r.direcciones);
    // Se usa de una vez: en el primer renglón sin dirección o en uno nuevo.
    const vacio = modelo.find((x) => !x.shipping_address_name);
    if (vacio) vacio.shipping_address_name = r.name;
    else { const n = renglon(r.name, false); for (const p of props.productos) n.cantidades[p.item_code] = Math.max(falta(p), 0); modelo.push(n); }
    nueva.abierto = false;
  } catch (e) { nueva.error = e.message || "No se pudo guardar la dirección."; }
  finally { nueva.guardando = false; }
}
</script>
