<!--
  Menú lateral. Se contrae a solo íconos (botón de abajo; se recuerda en este
  navegador). Cada entrada solo aparece si el usuario tiene la vista que la habilita
  (composables/useAccesos.js · roles.VISTAS); una sección sin entradas no se muestra.
-->
<template>
  <aside
    class="flex-shrink-0 bg-white border-r border-surface-border flex flex-col h-screen select-none transition-[width] duration-150"
    :class="corto ? 'w-[64px]' : 'w-56'"
  >
    <!-- Marca -->
    <div class="h-16 flex items-center flex-shrink-0" :class="corto ? 'justify-center' : 'px-4'">
      <RouterLink to="/" class="flex items-center gap-2.5 min-w-0" title="Costeo Yelke">
        <img :src="logoUrl" alt="Costeo Yelke" class="w-8 h-8 flex-shrink-0" />
        <div v-if="!corto" class="min-w-0">
          <p class="text-[14px] font-semibold text-ink leading-none tracking-tight">Costeo</p>
          <p class="text-[11px] text-ink-light mt-1 leading-none">Yelke</p>
        </div>
      </RouterLink>
    </div>

    <nav class="flex-1 overflow-y-auto overflow-x-hidden py-2 space-y-5" :class="corto ? 'px-2' : 'px-3'">
      <section v-for="sec in secciones" :key="sec.titulo || 'inicio'" class="space-y-0.5">
        <p v-if="sec.titulo && !corto" class="px-2.5 pb-1 text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-xlight">{{ sec.titulo }}</p>
        <div v-else-if="sec.titulo" class="mx-3 mb-2 border-t border-surface-border"></div>
        <RouterLink
          v-for="it in sec.items" :key="it.label" :to="it.to" :title="corto ? it.label : undefined"
          class="relative flex items-center rounded-lg text-[13px] transition-colors h-9"
          :class="[activo(it) ? 'bg-brand-50 text-brand-700 font-semibold' : 'text-ink-muted font-medium hover:text-ink hover:bg-surface-raised',
                   corto ? 'justify-center' : 'gap-3 px-2.5']"
        >
          <component :is="it.icon" class="w-[18px] h-[18px] flex-shrink-0" :class="activo(it) ? 'text-brand-600' : 'text-ink-light'" />
          <span v-if="!corto" class="truncate flex-1">{{ it.label }}</span>
          <span
            v-if="it.cuenta" class="text-[10px] font-semibold text-white bg-brand-500 rounded-full min-w-[18px] h-[18px] px-1 flex items-center justify-center"
            :class="corto ? 'absolute top-0.5 right-0.5 min-w-[16px] h-4' : ''"
          >{{ it.cuenta }}</span>
        </RouterLink>
      </section>
    </nav>

    <!-- Pie: escritorio de ERPNext y contraer/expandir -->
    <div class="py-2 border-t border-surface-border space-y-0.5" :class="corto ? 'px-2' : 'px-3'">
      <a href="/app" :title="corto ? 'Escritorio ERPNext' : undefined"
         class="flex items-center h-8 rounded-lg text-[12px] text-ink-light hover:text-ink hover:bg-surface-raised transition-colors"
         :class="corto ? 'justify-center' : 'gap-3 px-2.5'">
        <IconEscritorio class="w-4 h-4 flex-shrink-0" />
        <span v-if="!corto">Escritorio ERPNext</span>
      </a>
      <button type="button" :title="corto ? 'Expandir menú' : 'Contraer menú'"
              class="w-full flex items-center h-8 rounded-lg text-[12px] text-ink-light hover:text-ink hover:bg-surface-raised transition-colors"
              :class="corto ? 'justify-center' : 'gap-3 px-2.5'" @click="alternar">
        <svg class="w-4 h-4 flex-shrink-0 transition-transform" :class="corto ? 'rotate-180' : ''" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M11 17l-5-5 5-5M18 17l-5-5 5-5"/></svg>
        <span v-if="!corto">Contraer menú</span>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, h, defineComponent } from "vue";
import { RouterLink, useRoute } from "vue-router";
import logoUrl from "@/assets/icon_costeo.svg";
import { cuentaBandeja, refrescarCuentaBandeja, usePermisosAprobacion } from "@/composables/useAprobacion.js";
import { useAccesos } from "@/composables/useAccesos.js";
import { cuenta as cuentaEncargos, refrescarCuenta as refrescarEncargos } from "@/composables/useEncargos.js";

const route = useRoute();
const { puede, rutaPermitida } = useAccesos();

// ── Contraído (solo íconos), recordado en este navegador ─────────────────────
const CLAVE = "yelke-menu-corto";
const corto = ref((() => { try { return localStorage.getItem(CLAVE) === "1"; } catch { return false; } })());
function alternar() {
  corto.value = !corto.value;
  try { localStorage.setItem(CLAVE, corto.value ? "1" : "0"); } catch { /* sin almacenamiento */ }
}

// ── Aprobaciones: el nombre de la entrada depende de lo que la persona hace ──
const permisosAprobacion = usePermisosAprobacion();
const etiquetaAprobaciones = computed(() => {
  const p = permisosAprobacion;
  if (!p.cargado) return "";
  if (p.ve_panel) return "Dirección";
  if (p.puede_aprobar || p.puede_aprobar_precios) return "Aprobaciones";
  if (p.puede_revisar) return "Por revisar";
  return "";
});

// Menú: los documentos listan TODOS los de ese tipo (de cualquier costeo) y al abrir
// uno llevan al paso del Costeo donde vive. `rutas[0]` es la ruta que se revisa; `ve`
// sustituye esa revisión en las entradas de arriba.
const SECCIONES = () => [
  { titulo: "", items: [
    { to: "/inicio", icon: IconHome, label: "Inicio", rutas: ["Dashboard"] },
    { to: "/asignaciones", icon: IconEncargos, label: "Asignaciones", rutas: ["Asignaciones"], ve: true, cuenta: cuentaEncargos.value.para_mi },
    { to: "/prospecto-comercial", icon: IconLevantar, label: "Prospecto Comercial", rutas: ["Levantamiento"], ve: puede("levantamiento", "editar") },
    { to: "/direccion", icon: IconAprobar, label: etiquetaAprobaciones.value, rutas: ["Direccion"], ve: !!etiquetaAprobaciones.value, cuenta: cuentaBandeja.value },
  ] },
  { titulo: "Costeo", items: [
    { to: "/costeo", icon: IconPipeline, label: "Proyectos", rutas: ["CosteoList", "CosteoDetail"] },
    { to: "/plantillas", icon: IconTemplate, label: "Plantillas", rutas: ["Plantillas"] },
  ] },
  { titulo: "Documentos", items: [
    { to: "/cotizaciones", icon: IconQuote, label: "Cotizaciones", rutas: ["CotizacionList", "CotizacionDetail"] },
    { to: "/ordenes-venta", icon: IconCart, label: "Órdenes de Venta", rutas: ["SalesOrderList", "SalesOrderDetail", "SalesOrderNueva"] },
    { to: "/solicitudes-material", icon: IconList, label: "Solicitudes de Material", rutas: ["MaterialRequestList"] },
    { to: "/ordenes-compra", icon: IconTruck, label: "Órdenes de Compra", rutas: ["PurchaseOrderList", "PurchaseOrderDetail", "PurchaseOrderNueva"] },
    { to: "/recibos-compra", icon: IconInbox, label: "Recibos de Compra", rutas: ["PurchaseReceiptList"] },
    { to: "/remisiones", icon: IconShip, label: "Remisiones", rutas: ["DeliveryNoteList"] },
    { to: "/facturas", icon: IconInvoice, label: "Facturas de Venta", rutas: ["SalesInvoiceList", "SalesInvoiceDetail", "SalesInvoiceNueva"] },
    { to: "/facturas-compra", icon: IconInvoiceIn, label: "Facturas de Compra", rutas: ["PurchaseInvoiceList"] },
    { to: "/recordatorios", icon: IconBell, label: "Recordatorios de Precio", rutas: ["RecordatoriosList"] },
  ] },
  { titulo: "Administración", items: [
    { to: "/accesos", icon: IconLlave, label: "Accesos", rutas: ["Accesos"] },
  ] },
];
const secciones = computed(() => SECCIONES()
  .map((sec) => ({ ...sec, items: sec.items.filter((it) => ("ve" in it ? it.ve : rutaPermitida(it.rutas[0]))) }))
  .filter((sec) => sec.items.length));
const activo = (it) => it.rutas.includes(route.name);

let relojBandeja;
onMounted(() => {
  refrescarCuentaBandeja();
  refrescarEncargos();
  relojBandeja = setInterval(() => { if (document.visibilityState === "visible") { refrescarCuentaBandeja(); refrescarEncargos(); } }, 60000);
});
onBeforeUnmount(() => clearInterval(relojBandeja));

// ── Iconos SVG inline ────────────────────────────────────────────────────────
function svgIcon(d) {
  return defineComponent({
    setup(_, { attrs }) {
      return () =>
        h(
          "svg",
          { fill: "none", viewBox: "0 0 24 24", stroke: "currentColor", "stroke-width": "1.8", ...attrs },
          [h("path", { "stroke-linecap": "round", "stroke-linejoin": "round", d })],
        );
    },
  });
}

const IconHome     = svgIcon("M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6");
const IconPipeline = svgIcon("M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2");
const IconTemplate = svgIcon("M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2");
const IconTruck    = svgIcon("M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z");
const IconQuote    = svgIcon("M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z");
const IconCart     = svgIcon("M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2");
const IconList     = svgIcon("M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01");
const IconInbox    = svgIcon("M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0l-2 5H6l-2-5m16 0H4m5 5v.01M15 18v.01");
const IconShip     = svgIcon("M12 19l9 2-9-18-9 18 9-2zm0 0v-8");
const IconInvoice  = svgIcon("M9 14l2 2 4-4m4 9V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2z");
const IconInvoiceIn = svgIcon("M3 10h18M7 15h1m4 0h1m-9 4h16a1 1 0 001-1V6a1 1 0 00-1-1H4a1 1 0 00-1 1v12a1 1 0 001 1z");
const IconLevantar = svgIcon("M9 4h6l1 2h3a1 1 0 011 1v12a1 1 0 01-1 1H5a1 1 0 01-1-1V7a1 1 0 011-1h3zM12 10v6M9 13h6");
const IconEncargos = svgIcon("M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7zM19 8v6M22 11h-6");
const IconAprobar  = svgIcon("M9 12l2 2 4-4M7 4h10a3 3 0 013 3v10a3 3 0 01-3 3H7a3 3 0 01-3-3V7a3 3 0 013-3z");
const IconLlave    = svgIcon("M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z");
const IconEscritorio = svgIcon("M4 5h16a1 1 0 011 1v10a1 1 0 01-1 1H4a1 1 0 01-1-1V6a1 1 0 011-1zM8 21h8M12 17v4");
const IconBell     = svgIcon("M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9");
</script>
