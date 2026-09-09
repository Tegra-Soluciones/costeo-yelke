import { createRouter, createWebHistory } from "vue-router";

const routes = [
  { path: "/", redirect: "/inicio" },
  { path: "/inicio", name: "Dashboard", component: () => import("@/pages/DashboardPage.vue") },
  { path: "/costeo", name: "CosteoList", component: () => import("@/pages/CosteoListPage.vue") },
  { path: "/costeo/nuevo", name: "CosteoNuevo", component: () => import("@/pages/CosteoDetailPage.vue") },
  { path: "/costeo/:name", name: "CosteoDetail", component: () => import("@/pages/CosteoDetailPage.vue"), props: true },
  { path: "/plantillas", name: "Plantillas", component: () => import("@/pages/PlantillasPage.vue") },
  { path: "/productos", name: "ProductoList", component: () => import("@/pages/ProductoListPage.vue") },
  { path: "/productos/nuevo", name: "ProductoNuevo", component: () => import("@/pages/ProductoNuevoPage.vue") },
  { path: "/productos/:name", name: "ProductoDetail", component: () => import("@/pages/ProductoDetailPage.vue"), props: true },
  { path: "/precios", name: "Precios", component: () => import("@/pages/PreciosPage.vue") },
  { path: "/cotizaciones", name: "CotizacionList", component: () => import("@/pages/CotizacionListPage.vue") },
  { path: "/cotizaciones/:name", name: "CotizacionDetail", component: () => import("@/pages/CotizacionDetailPage.vue"), props: true },
  { path: "/ordenes-venta", name: "SalesOrderList", component: () => import("@/pages/SalesOrderListPage.vue") },
  { path: "/ordenes-venta/nueva", name: "SalesOrderNueva", component: () => import("@/pages/SalesOrderDetailPage.vue") },
  { path: "/ordenes-venta/:name", name: "SalesOrderDetail", component: () => import("@/pages/SalesOrderDetailPage.vue"), props: true },
  { path: "/ordenes-compra", name: "PurchaseOrderList", component: () => import("@/pages/PurchaseOrderListPage.vue") },
  { path: "/ordenes-compra/nueva", name: "PurchaseOrderNueva", component: () => import("@/pages/PurchaseOrderDetailPage.vue") },
  { path: "/ordenes-compra/:name", name: "PurchaseOrderDetail", component: () => import("@/pages/PurchaseOrderDetailPage.vue"), props: true },
  { path: "/facturas", name: "SalesInvoiceList", component: () => import("@/pages/SalesInvoiceListPage.vue") },
  { path: "/facturas/nueva", name: "SalesInvoiceNueva", component: () => import("@/pages/SalesInvoiceDetailPage.vue") },
  { path: "/facturas/:name", name: "SalesInvoiceDetail", component: () => import("@/pages/SalesInvoiceDetailPage.vue"), props: true },
  { path: "/solicitudes-material", name: "MaterialRequestList", component: () => import("@/pages/MaterialRequestListPage.vue") },
  { path: "/recibos-compra", name: "PurchaseReceiptList", component: () => import("@/pages/PurchaseReceiptListPage.vue") },
  { path: "/remisiones", name: "DeliveryNoteList", component: () => import("@/pages/DeliveryNoteListPage.vue") },
  { path: "/facturas-compra", name: "PurchaseInvoiceList", component: () => import("@/pages/PurchaseInvoiceListPage.vue") },
  { path: "/recordatorios", name: "RecordatoriosList", component: () => import("@/pages/RecordatoriosListPage.vue") },
];

export default createRouter({
  history: createWebHistory("/costeo-yelke"),
  routes,
});
