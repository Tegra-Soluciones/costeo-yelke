<template>
  <aside
    class="w-52 flex-shrink-0 bg-white border-r border-surface-border flex flex-col h-screen select-none"
  >
    <!-- Logo / App identity -->
    <div class="h-16 px-4 flex items-center border-b border-surface-border flex-shrink-0">
      <div class="flex items-center gap-2.5">
        <img :src="logoUrl" alt="Costeo Yelke" class="w-8 h-8 flex-shrink-0" />
        <div>
          <p class="text-[13px] font-semibold text-ink leading-none">Costeo</p>
          <p class="text-[10px] text-ink-muted mt-0.5">Yelke</p>
        </div>
      </div>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 overflow-y-auto px-2 py-3 space-y-4">

      <!-- Inicio -->
      <section>
        <NavItem to="/inicio" :icon="IconHome" label="Inicio" :activeRoutes="['Dashboard']" />
      </section>

      <!-- Costeo -->
      <section>
        <p class="nav-section-label">Costeo</p>
        <NavItem to="/costeo"       :icon="IconPipeline" label="Proyectos"      :activeRoutes="['CosteoList', 'CosteoDetail']" />
        <NavItem to="/plantillas"   :icon="IconTemplate" label="Plantillas"     :activeRoutes="['Plantillas']" />
      </section>

      <!-- Documentos del proceso: listan TODOS los documentos de ese tipo (de cualquier
           costeo) y al abrir uno te llevan directo al paso del Costeo donde vive, con
           un resaltado -- para archivar/revisar sin tener que recordar en qué costeo
           quedó cada documento. -->
      <section>
        <p class="nav-section-label">Documentos</p>
        <NavItem to="/cotizaciones"        :icon="IconQuote"  label="Cotizaciones"          :activeRoutes="['CotizacionList', 'CotizacionDetail']" />
        <NavItem to="/ordenes-venta"       :icon="IconCart"   label="Órdenes de Venta"       :activeRoutes="['SalesOrderList', 'SalesOrderDetail', 'SalesOrderNueva']" />
        <NavItem to="/solicitudes-material" :icon="IconList"  label="Solicitudes de Material" :activeRoutes="['MaterialRequestList']" />
        <NavItem to="/ordenes-compra"      :icon="IconTruck"  label="Órdenes de Compra"      :activeRoutes="['PurchaseOrderList', 'PurchaseOrderDetail', 'PurchaseOrderNueva']" />
        <NavItem to="/recibos-compra"      :icon="IconInbox"  label="Recibos de Compra"      :activeRoutes="['PurchaseReceiptList']" />
        <NavItem to="/remisiones"          :icon="IconShip"   label="Remisiones"             :activeRoutes="['DeliveryNoteList']" />
        <NavItem to="/facturas"            :icon="IconInvoice" label="Facturas de Venta"     :activeRoutes="['SalesInvoiceList', 'SalesInvoiceDetail', 'SalesInvoiceNueva']" />
        <NavItem to="/facturas-compra"     :icon="IconInvoiceIn" label="Facturas de Compra"  :activeRoutes="['PurchaseInvoiceList']" />
      </section>

      <!-- Producción (links a ERPNext) -->
      <section>
        <p class="nav-section-label">Producción</p>
        <ExternalNavItem href="/app/production-plan"      :icon="IconPlan" label="Plan de Producción"/>
        <ExternalNavItem href="/app/work-order"           :icon="IconGear" label="Órdenes de Trabajo"/>
        <ExternalNavItem href="/app/subcontracting-order" :icon="IconSub"  label="Subcontratación"/>
      </section>

      <!-- Ventas -->
      <section>
        <p class="nav-section-label">Ventas</p>
        <NavItem to="/recordatorios" :icon="IconBell" label="Recordatorios de Precio" :activeRoutes="['RecordatoriosList']" />
      </section>

    </nav>

    <!-- Footer -->
    <div class="px-3 py-3 border-t border-surface-border">
      <a
        href="/app"
        class="flex items-center gap-2 px-2 py-1.5 rounded-md text-[12px] text-ink-muted hover:text-ink hover:bg-surface-raised transition-colors"
      >
        <svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
        </svg>
        Escritorio ERPNext
      </a>
    </div>
  </aside>
</template>

<script setup>
import { h, defineComponent } from "vue";
import { RouterLink, useRoute } from "vue-router";
import logoUrl from "@/assets/icon_costeo.svg";

const route = useRoute();

// ── NavItem interno (RouterLink) ─────────────────────────────────────────────
const NavItem = defineComponent({
  props: {
    to: String,
    label: String,
    icon: Object,
    exact: Boolean,
    // Explicit list of route names that mark this item as active.
    activeRoutes: Array,
  },
  setup(props) {
    return () => {
      const active = props.activeRoutes
        ? props.activeRoutes.includes(route.name)
        : route.path === props.to;

      return h(
        RouterLink,
        { to: props.to, class: ["nav-item", active ? "nav-item--active" : "nav-item--idle"] },
        () => [
          h(props.icon, { class: "w-[15px] h-[15px] flex-shrink-0" }),
          h("span", { class: "truncate" }, props.label),
        ],
      );
    };
  },
});

// ── ExternalNavItem (href externo) ───────────────────────────────────────────
const ExternalNavItem = defineComponent({
  props: { href: String, label: String, icon: Object },
  setup(props) {
    return () =>
      h(
        "a",
        { href: props.href, target: "_blank", class: "nav-item nav-item--idle" },
        [
          h(props.icon, { class: "w-[15px] h-[15px] flex-shrink-0 text-ink-light" }),
          h("span", { class: "truncate flex-1" }, props.label),
          h(IconExternal, { class: "w-3 h-3 flex-shrink-0 text-ink-xlight opacity-70" }),
        ],
      );
  },
});

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
const IconPlan     = svgIcon("M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01");
const IconGear     = svgIcon("M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z");
const IconSub      = svgIcon("M13 10V3L4 14h7v7l9-11h-7z");
const IconTruck    = svgIcon("M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z");
const IconQuote    = svgIcon("M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z");
const IconCart     = svgIcon("M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2");
const IconList     = svgIcon("M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01");
const IconInbox    = svgIcon("M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0l-2 5H6l-2-5m16 0H4m5 5v.01M15 18v.01");
const IconShip     = svgIcon("M12 19l9 2-9-18-9 18 9-2zm0 0v-8");
const IconInvoice  = svgIcon("M9 14l2 2 4-4m4 9V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2z");
const IconInvoiceIn = svgIcon("M3 10h18M7 15h1m4 0h1m-9 4h16a1 1 0 001-1V6a1 1 0 00-1-1H4a1 1 0 00-1 1v12a1 1 0 001 1z");
const IconExternal = svgIcon("M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14");
const IconBell     = svgIcon("M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9");
</script>

<style scoped>
.nav-section-label {
  @apply px-2 mb-1 text-[10px] font-semibold uppercase tracking-widest text-ink-light;
}

.nav-item {
  @apply flex items-center gap-2.5 w-full px-2.5 py-[7px] rounded-md text-[13px] font-medium transition-colors duration-100 no-underline;
}

.nav-item--idle {
  @apply text-ink-muted hover:text-ink hover:bg-surface-raised;
}

.nav-item--active {
  @apply bg-brand-50 text-brand-700 font-semibold;
}
</style>
