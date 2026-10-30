import { createRouter, createWebHistory } from "vue-router";
import { cargarPermisosAprobacion } from "@/composables/useAprobacion.js";
import { asegurarCompania } from "@/composables/useCompany.js";
import { cargarAccesos, rutaPermitida, vistasDeRuta, etiquetaVista } from "@/composables/useAccesos.js";

const routes = [
  // El Director aterriza en su panel; los demás, en Inicio.
  { path: "/", component: { render: () => null },
    beforeEnter: async () => ((await cargarPermisosAprobacion()).es_director ? "/direccion" : "/inicio") },
  // `movil`: en celular se pinta sin el menú ni la barra de la app (App.vue).
  { path: "/direccion", name: "Direccion", component: () => import("@/pages/DireccionPage.vue"), meta: { movil: true } },
  { path: "/inicio", name: "Dashboard", component: () => import("@/pages/DashboardPage.vue") },
  { path: "/asignaciones", name: "Asignaciones", component: () => import("@/pages/AsignacionesPage.vue") },
  { path: "/encargos", redirect: "/asignaciones" },
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
  { path: "/accesos", name: "Accesos", component: () => import("@/pages/AccesosPage.vue") },
  { path: "/recordatorios", name: "RecordatoriosList", component: () => import("@/pages/RecordatoriosListPage.vue") },
];

const router = createRouter({
  history: createWebHistory("/costeo-yelke"),
  routes,
});

// Los enlaces de los avisos y del panel de Dirección traen ?compania= (ver
// api/aprobaciones._ruta_doc): el filtro de compañía pasa a la del documento ANTES de
// abrir la pantalla, para que una lista o un documento de otra compañía no salga vacío.
router.beforeEach(async (to) => {
  if (to.query.compania) await asegurarCompania(String(to.query.compania));
  // Accesos por vista (composables/useAccesos.js): una pantalla de una vista que el
  // usuario no tiene lo regresa a Inicio con el aviso. Crear ("…Nueva/Nuevo") pide editar.
  await cargarAccesos();
  const nivel = /Nuev[ao]$/.test(String(to.name || "")) ? "editar" : "ver";
  if (to.name && !rutaPermitida(String(to.name), nivel)) {
    const v = vistasDeRuta(String(to.name))[0];
    return { name: "Dashboard", query: { sin_acceso: etiquetaVista(v) } };
  }
});

export default router;
