import { reactive, ref, computed, watch } from "vue";
import { call, uploadFile } from "@/utils/frappe.js";

export const OM_CAB = ["t28", "t30", "t32", "t34", "t36", "t40", "t42", "t44"];
export const OM_DAMA = ["t5", "t7", "t9", "t11", "t13", "t15", "t17"];

export const DOC_COMPRA = {
  oc:  { doctype: "Purchase Order", label: "Orden de compra", desk: "purchase-order" },
  rfq: { doctype: "Request for Quotation", label: "Solicitud de cotización", desk: "request-for-quotation" },
  sq:  { doctype: "Supplier Quotation", label: "Presupuesto de proveedor", desk: "supplier-quotation" },
};

function emptyTalla(sizes) {
  const o = { linea: "Cantidad", total: 0 };
  sizes.forEach((s) => (o[s] = 0));
  return o;
}

// Todo el estado y las acciones de la etapa "Producir": plan (con lotes), materia
// prima (solicitud -> OC/RFQ/SQ -> recibo), subcontratación (OC -> SCO por lotes ->
// transferencia -> recibo) y el avance global. Un solo lugar en vez de repartido en
// la página, para poder reusar la lógica desde componentes más chicos.
export function useProduccion({ showToast, advancing, ensurePrintFmt, previewKey }) {
  // ── Plan de producción ──
  const planDetail = ref(null);
  const planWh = ref("");
  const hasPlan = computed(() => !!planDetail.value);
  const planValidated = computed(() => planDetail.value?.docstatus === 1);
  // Recuerda de qué costeo (y de qué OV) es el plan actual, para poder recargar
  // (loadPlan) sin tener que pasar esos datos en cada acción secundaria. planSalesOrder
  // es la OV activa elegida en el SPA -- cada OV tiene su propio plan (ver
  // desbloquear_plan_produccion/get_plan_detail en el backend).
  const planCosteoName = ref(null);
  const planSalesOrder = ref(null);
  const downstream = ref({ mrs: [], wos: [], sub: [] });

  async function loadPlan(costeoName, salesOrder = null) {
    if (!costeoName) return;
    planCosteoName.value = costeoName;
    planSalesOrder.value = salesOrder || null;
    try {
      const r = await call("costeo_yelke.api.costeo_api.get_plan_detail", { costeo: costeoName, sales_order: planSalesOrder.value });
      planDetail.value = r.plan;
      if (r.plan) {
        planWh.value = r.plan.for_warehouse || "";
        await loadSolicitud();
        await loadRecibos();
        await loadSubcontratos();
      }
    } catch { /* ignore */ }
  }
  async function obtenerMateriasPrimas() {
    if (!planDetail.value) return;
    advancing.value = true;
    try {
      await call("costeo_yelke.api.costeo_api.plan_obtener_materias_primas", { plan: planDetail.value.name, warehouse: planWh.value || null });
      await loadPlan(planCosteoName.value, planSalesOrder.value);
      showToast("Materias primas actualizadas");
    } catch (e) { showToast(e.message || "Error", "error"); }
    finally { advancing.value = false; }
  }
  async function guardarPlan() {
    if (!planDetail.value) return;
    advancing.value = true;
    try {
      const items = (planDetail.value.po_items || []).map((it) => ({ name: it.name, planned_qty: it.planned_qty }));
      await call("costeo_yelke.api.costeo_api.guardar_plan", {
        plan: planDetail.value.name, for_warehouse: planWh.value || null, items: JSON.stringify(items),
      });
      await loadPlan(planCosteoName.value, planSalesOrder.value);
      showToast("Plan guardado");
    } catch (e) { showToast(e.message || "Error al guardar", "error"); }
    finally { advancing.value = false; }
  }
  async function validarPlan() {
    if (!planDetail.value) return;
    advancing.value = true;
    try {
      // guarda cambios pendientes (almacén, cantidad a producir…) antes de validar --
      // si no, se pierden en silencio al dar "Validar" directo sin pasar por "Guardar".
      const items = (planDetail.value.po_items || []).map((it) => ({ name: it.name, planned_qty: it.planned_qty }));
      await call("costeo_yelke.api.costeo_api.guardar_plan", {
        plan: planDetail.value.name, for_warehouse: planWh.value || null, items: JSON.stringify(items),
      });
      await call("costeo_yelke.api.costeo_api.validar_documento", { doctype: "Production Plan", name: planDetail.value.name });
      await loadPlan(planCosteoName.value, planSalesOrder.value);
      showToast("Plan validado");
    } catch (e) { showToast(e.message || "No se pudo validar el plan", "error"); }
    finally { advancing.value = false; }
  }
  async function crearOrdenesTrabajo() {
    advancing.value = true;
    try {
      const r = await call("costeo_yelke.api.costeo_api.plan_crear_ordenes_trabajo", { plan: planDetail.value.name });
      downstream.value.wos = r.work_orders || [];
      showToast(`${(r.work_orders || []).length} orden(es) de trabajo creada(s)`);
    } catch (e) { showToast(e.message || "Error", "error"); }
    finally { advancing.value = false; }
  }

  // ── Materia prima: Solicitud -> OC / RFQ / SQ ──
  const mrDetail = ref(null);
  const mrItems = ref([]);
  const mrSchedule = ref("");
  const mrResults = ref({ ocs: [] });
  const mrDocTab = ref(null);
  const rfqSelected = ref("");
  const sqSelected = ref("");
  const mrValidated = computed(() => mrDetail.value?.docstatus === 1);
  const anyOcValidated = computed(() => reciboOcs.value.length > 0);

  const docCompra = ref(null);
  const docCompraItems = ref([]);
  const docCompraForm = reactive({ schedule_date: "", valid_till: "", payment_terms_template: "", tc_name: "", shipping_cost: 0, supplier: "" });
  const docCompraValidated = computed(() => docCompra.value?.docstatus === 1);
  const docCompraHasRate = computed(() => docCompraItems.value.some((i) => i.has_rate));
  const ocSelected = ref("");

  // Doble validación (Enviar -> Revisor -> Aprobador) -- hoy solo aplica a la
  // Orden de Compra (materia prima y subcontratada); el resto de docs de este
  // composable sigue con validación normal. Los roles se cargan una sola vez.
  // `vistas`: claves de vista de Producción que este usuario puede abrir (ver
  // roles.vistas_produccion). Arranca con todas para no parpadear mientras carga; el
  // backend es la autoridad.
  const permisosValidacion = reactive({
    puede_revisar: true, puede_aprobar: true,
    vistas: ["tablero", "preparacion", "om", "materia", "flujo", "talleres", "envios", "facturas", "entrega"],
  });
  async function loadPermisosValidacion() {
    try { Object.assign(permisosValidacion, await call("costeo_yelke.api.costeo_api.get_permisos_validacion_yelke")); }
    catch { /* si falla, se dejan en true -- el backend igual bloquea si no toca */ }
  }

  // Lote actual (cantidad por material) para crear una OC parcial contra la MR.
  const loteOc = reactive({ open: false, items: [], schedule_date: "", lote_ref: "" });

  // Lotes de entrega definidos ANTES de validar la solicitud -- para no tener que ir
  // creando "Nuevo lote" uno por uno después de validar cuando ya se sabe de entrada
  // en cuántas tandas y con qué fechas se va a comprar. Al validar, se generan todas
  // las OC de un jalón (mr_crear_ocs_por_lotes). Estado 100% local (no se persiste
  // hasta que se validan).
  //
  // Se captura por PIEZAS de cada producto terminado (igual que "Cantidad a
  // producir" del plan) -- la materia prima de cada lote se deriva sola
  // (mr_preview_lotes_materiales / mr_dividir_en_lotes_por_piezas, misma
  // explosión de BOM que ya usa el Production Plan), en vez de pedirle a la
  // persona que calcule a mano cuánta tela/cinta/botón corresponde a esa
  // cantidad de prendas.
  const mrLotes = ref([]);
  const mrLotesPreview = reactive({});
  let _mrLoteSeq = 0;
  function addMrLote() {
    const piezas = {};
    (planDetail.value?.po_items || []).forEach((it) => { piezas[it.item_code] = 0; });
    mrLotes.value.push({ id: `mrlote_${++_mrLoteSeq}`, fecha_requerida: "", piezas, lote_ref: siguienteLoteLibre() });
  }
  function removeMrLote(id) {
    mrLotes.value = mrLotes.value.filter((l) => l.id !== id);
    actualizarPreviewLotes();
  }
  // Reparte el saldo de cada producto en partes iguales entre los lotes ya creados;
  // el ÚLTIMO lote se lleva el residuo del redondeo (para que la suma cuadre exacto).
  function repartirMrLotesIgual() {
    const n = mrLotes.value.length;
    if (!n) return;
    (planDetail.value?.po_items || []).forEach((it) => {
      const total = Number(it.planned_qty) || 0;
      const base = Math.floor(total / n);
      let asignado = 0;
      mrLotes.value.forEach((lote, i) => {
        const qty = i === n - 1 ? total - asignado : base;
        lote.piezas[it.item_code] = qty;
        asignado += qty;
      });
    });
    actualizarPreviewLotes();
  }
  function mrLotePendiente(item_code_producto) {
    const total = planDetail.value?.po_items?.find((it) => it.item_code === item_code_producto)?.planned_qty || 0;
    const asignado = mrLotes.value.reduce((s, l) => s + (Number(l.piezas[item_code_producto]) || 0), 0);
    return Math.round((total - asignado) * 100) / 100;
  }
  // Pendiente negativo = entre todos los lotes ya se pidieron más piezas de
  // ese producto de las que el plan tiene -- marca en rojo TODOS los campos
  // de ese producto (en cualquier lote) para que se note dónde ajustar, sin
  // importar cuál de ellos fue el que hizo que se pasara.
  function mrLoteProductoExcedido(item_code_producto) {
    return mrLotePendiente(item_code_producto) < -0.001;
  }
  // Pendiente positivo = todavía queda repartir piezas de ese producto en
  // algún lote -- no es un error (nadie escribió de más), pero mientras
  // exista no se puede validar: los lotes tienen que cubrir el 100% del
  // plan, no dejar un sobrante fuera del flujo de lotes.
  function mrLoteProductoIncompleto(item_code_producto) {
    return mrLotePendiente(item_code_producto) > 0.001;
  }
  // Ningún producto debe quedar excedido NI con piezas sin repartir para
  // poder validar y dividir -- los lotes tienen que sumar EXACTO el total
  // del plan. El backend (mr_dividir_en_lotes_por_piezas) solo hace cumplir
  // el "no excedido"; el "completo" se exige aquí, antes de siquiera
  // intentarlo.
  const mrLotesInvalidos = computed(() =>
    mrLotes.value.length > 0
    && (planDetail.value?.po_items || []).some((p) => mrLoteProductoExcedido(p.item_code) || mrLoteProductoIncompleto(p.item_code))
  );
  // Las cantidades de la solicitud salen de multiplicar consumo x piezas y sumar,
  // así que arrastran ruido de coma flotante: 29 llega como 28.99999998 y en
  // pantalla se ve sucio. Se limpia al RECIBIR el dato (no al pintarlo) para que el
  // valor que se reenvía al guardar también vaya limpio. 6 decimales deja intactas
  // las cantidades finas de verdad (0.007523 Mazo por prenda) y solo mata el ruido.
  function limpiaNum(v) {
    const n = Number(v);
    return Number.isFinite(n) ? Math.round(n * 1e6) / 1e6 : v;
  }

  // Vista previa de materiales por lote (informativa, solo lectura) -- se
  // recalcula sola cada vez que cambian las piezas capturadas; debounce corto
  // para no disparar una llamada por cada tecla mientras se escribe.
  let _previewTimer = null;
  function actualizarPreviewLotes() {
    clearTimeout(_previewTimer);
    _previewTimer = setTimeout(async () => {
      if (!planDetail.value || !mrLotes.value.length) { Object.keys(mrLotesPreview).forEach((k) => delete mrLotesPreview[k]); return; }
      const lotes = mrLotes.value
        .filter((l) => l.lote_ref)
        .map((l) => ({ lote_ref: l.lote_ref, piezas: l.piezas }));
      if (!lotes.length) return;
      try {
        const r = await call("costeo_yelke.api.costeo_api.mr_preview_lotes_materiales", {
          plan: planDetail.value.name, lotes: JSON.stringify(lotes),
        });
        Object.keys(mrLotesPreview).forEach((k) => delete mrLotesPreview[k]);
        // La vista previa ya viene redondeada del servidor (mr_preview_lotes_materiales).
        Object.assign(mrLotesPreview, r);
      } catch { /* la vista previa es informativa -- si falla, no interrumpe la captura */ }
    }, 400);
  }

  async function loadSolicitud() {
    if (!planDetail.value) return;
    // guardarSolicitud() recarga la MR después de cada guardado (para reflejar lo
    // persistido) -- los lotes definidos en el paso previo a validar son estado
    // 100% local (no viven en el backend), así que sólo se descartan cuando de
    // verdad cambiamos de Material Request, no en cada recarga de la misma.
    const prevMrName = mrDetail.value?.name || null;
    try {
      const r = await call("costeo_yelke.api.costeo_api.get_solicitud_material", { plan: planDetail.value.name });
      mrDetail.value = r.detail;
      if (r.detail) {
        mrItems.value = r.detail.items.map((i) => ({ ...i, qty: limpiaNum(i.qty) }));
        mrSchedule.value = r.detail.schedule_date || "";
        mrResults.value = { ocs: r.detail.linked_ocs || [] };
      } else {
        mrItems.value = []; mrSchedule.value = "";
      }
      if ((r.detail?.name || null) !== prevMrName) mrLotes.value = [];
      mrDocTab.value = null; docCompra.value = null;
    } catch { /* ignore */ }
  }
  async function crearSolicitud() {
    advancing.value = true;
    try {
      await call("costeo_yelke.api.costeo_api.plan_crear_solicitud_material", { plan: planDetail.value.name });
      await loadSolicitud();
      showToast("Solicitud de material creada");
    } catch (e) { showToast(e.message || "Error", "error"); }
    finally { advancing.value = false; }
  }
  async function guardarSolicitud() {
    advancing.value = true;
    try {
      await call("costeo_yelke.api.costeo_api.guardar_solicitud_material", { mr: mrDetail.value.name, items: JSON.stringify(mrItems.value), schedule_date: mrSchedule.value || null });
      await loadSolicitud();
      showToast("Solicitud guardada");
    } catch (e) { showToast(e.message || "Error al guardar", "error"); }
    finally { advancing.value = false; }
  }
  async function validarSolicitud() {
    if (mrLotesInvalidos.value) {
      showToast("Los lotes tienen que sumar exacto el total del plan (ni de más ni de menos) antes de poder validar", "error");
      return;
    }
    advancing.value = true;
    try {
      await call("costeo_yelke.api.costeo_api.guardar_solicitud_material", { mr: mrDetail.value.name, items: JSON.stringify(mrItems.value), schedule_date: mrSchedule.value || null });
      const lotesConDatos = mrLotes.value
        .map((l) => ({
          schedule_date: l.fecha_requerida || null,
          lote_ref: l.lote_ref || null,
          piezas: Object.fromEntries(Object.entries(l.piezas).filter(([, q]) => Number(q) > 0).map(([k, q]) => [k, Number(q)])),
        }))
        .filter((l) => Object.keys(l.piezas).length);
      // Divide las líneas por lote ANTES de validar (la MR debe seguir en borrador
      // para poder reescribir sus renglones) -- no crea ninguna OC todavía, eso se
      // dispara después, por lote, desde su propia pantalla. La materia prima de
      // cada lote se deriva sola de las piezas (mr_dividir_en_lotes_por_piezas).
      if (lotesConDatos.length) {
        await call("costeo_yelke.api.costeo_api.mr_dividir_en_lotes_por_piezas", {
          mr: mrDetail.value.name, plan: planDetail.value.name, lotes: JSON.stringify(lotesConDatos),
        });
      }
      await call("costeo_yelke.api.costeo_api.validar_documento", { doctype: "Material Request", name: mrDetail.value.name });
      mrLotes.value = [];
      await loadSolicitud();
      if (lotesConDatos.length) await loadLotesProduccion();
      showToast(lotesConDatos.length ? `Solicitud validada · ${lotesConDatos.length} lote(s) listo(s) para generar su OC` : "Solicitud validada");
    } catch (e) { showToast(e.message || "No se pudo validar", "error"); }
    finally { advancing.value = false; }
  }

  function abrirLoteOc() {
    loteOc.open = true;
    loteOc.items = mrItems.value.map((it) => ({ item_code: it.item_code, qty: 0, pendiente: it.qty }));
    loteOc.schedule_date = "";
    loteOc.lote_ref = siguienteLoteLibre();
  }
  function cerrarLoteOc() { loteOc.open = false; }

  async function crearOc(lote) {
    advancing.value = true;
    try {
      const params = { mr: mrDetail.value.name };
      if (lote) {
        const items = loteOc.items.filter((i) => Number(i.qty) > 0).map((i) => ({ item_code: i.item_code, qty: Number(i.qty) }));
        if (!items.length) { showToast("Indica la cantidad de al menos un material", "error"); advancing.value = false; return; }
        params.items = JSON.stringify(items);
        if (loteOc.schedule_date) params.schedule_date = loteOc.schedule_date;
        if (loteOc.lote_ref) params.lote_ref = loteOc.lote_ref;
      }
      const r = await call("costeo_yelke.api.costeo_api.mr_crear_oc", params);
      mrResults.value.ocs = [...new Set([...(mrResults.value.ocs || []), ...(r.purchase_orders || [])])];
      cerrarLoteOc();
      if (lote) await loadLotesProduccion();
      const nuevo = (r.purchase_orders || [])[0];
      if (nuevo) {
        reciboOcSel.value = nuevo; reciboPr.value = null; // OC nueva: aún sin recibo
        await selectOcLote(nuevo);
      }
      showToast((lote ? "Nuevo lote de OC creado" : "Orden de compra creada") + _mensajeRedondeos(r.redondeos));
      return r.purchase_orders || [];
    } catch (e) { showToast(e.message || "Error", "error"); return []; }
    finally { advancing.value = false; }
  }

  async function selectRfq(name) { mrDocTab.value = "rfq"; rfqSelected.value = name; advancing.value = true; try { await loadDocCompra("Request for Quotation", name); } finally { advancing.value = false; } }
  async function selectSq(name) { mrDocTab.value = "sq"; sqSelected.value = name; advancing.value = true; try { await loadDocCompra("Supplier Quotation", name); } finally { advancing.value = false; } }

  // Genera la Solicitud de cotización / Presupuesto de proveedor de UN proveedor de
  // este lote -- por su propio botón, no se crean solos ni se agrupan todos los
  // proveedores en un mismo documento (algunos proveedores no siempre los necesitan).
  function _itemsPendientesProveedor(lote, supplier) {
    return (lote.material_items || [])
      .filter((it) => it.supplier === supplier)
      .map((it) => ({ item_code: it.item_code, qty: it.qty }));
  }
  async function crearRfqLote(lote, supplier) {
    const items = _itemsPendientesProveedor(lote, supplier);
    if (!items.length) return;
    advancing.value = true;
    try {
      const r = await call("costeo_yelke.api.costeo_api.mr_crear_rfq", {
        mr: lote.material_mr, supplier, items: JSON.stringify(items), lote_ref: lote.lote_ref,
      });
      await loadLotesProduccion();
      await selectRfq(r.rfq);
      showToast("Solicitud de cotización creada");
    } catch (e) { showToast(e.message || "Error", "error"); }
    finally { advancing.value = false; }
  }
  async function crearSqLote(lote, supplier) {
    const items = _itemsPendientesProveedor(lote, supplier);
    if (!items.length) return;
    advancing.value = true;
    try {
      const r = await call("costeo_yelke.api.costeo_api.mr_crear_presupuesto_proveedor", {
        mr: lote.material_mr, supplier, items: JSON.stringify(items), lote_ref: lote.lote_ref,
      });
      await loadLotesProduccion();
      await selectSq(r.supplier_quotation);
      showToast("Presupuesto de proveedor creado");
    } catch (e) { showToast(e.message || "Error", "error"); }
    finally { advancing.value = false; }
  }
  async function loadDocCompra(doctype, name) {
    const r = await call("costeo_yelke.api.costeo_api.get_documento_compra", { doctype, name });
    docCompra.value = r;
    ensurePrintFmt(doctype, name);
    docCompraItems.value = (r.items || []).map((i) => ({ ...i }));
    docCompraForm.schedule_date = r.schedule_date || "";
    docCompraForm.valid_till = r.valid_till || "";
    docCompraForm.payment_terms_template = r.payment_terms_template || "";
    docCompraForm.tc_name = r.tc_name || "";
    docCompraForm.shipping_cost = r.shipping_cost || 0;
    docCompraForm.supplier = r.supplier || "";
    previewKey.value++;
  }
  async function selectOC(po) { ocSelected.value = po; advancing.value = true; try { await loadDocCompra("Purchase Order", po); } finally { advancing.value = false; } }
  // Selecciona un lote de materia prima (una OC) y sincroniza su recibo -- usado por
  // las LoteCard de la sección Materia Prima, que muestran OC + Recibo juntos.
  async function selectOcLote(po) {
    mrDocTab.value = "oc";
    await selectOC(po);
    await selectReciboOc(po);
  }
  async function guardarDocCompra() {
    if (!docCompra.value) return;
    advancing.value = true;
    try {
      await call("costeo_yelke.api.costeo_api.guardar_documento_compra", {
        doctype: docCompra.value.doctype, name: docCompra.value.name,
        schedule_date: docCompraForm.schedule_date || null, valid_till: docCompraForm.valid_till || null,
        payment_terms_template: docCompraForm.payment_terms_template || null, tc_name: docCompraForm.tc_name || null,
        items: JSON.stringify(docCompraItems.value),
        shipping_cost: docCompra.value.has_shipping ? (docCompraForm.shipping_cost || 0) : null,
        supplier: docCompraForm.supplier || null,
      });
      await loadDocCompra(docCompra.value.doctype, docCompra.value.name);
      showToast("Guardado");
    } catch (e) { showToast(e.message || "Error al guardar", "error"); }
    finally { advancing.value = false; }
  }
  async function validarDocCompra() {
    if (!docCompra.value) return;
    advancing.value = true;
    try {
      // guarda cambios pendientes (precios, cantidades, fechas…) antes de validar --
      // si no, se pierden en silencio al dar "Validar" directo sin pasar por "Guardar".
      await call("costeo_yelke.api.costeo_api.guardar_documento_compra", {
        doctype: docCompra.value.doctype, name: docCompra.value.name,
        schedule_date: docCompraForm.schedule_date || null, valid_till: docCompraForm.valid_till || null,
        payment_terms_template: docCompraForm.payment_terms_template || null, tc_name: docCompraForm.tc_name || null,
        items: JSON.stringify(docCompraItems.value),
        shipping_cost: docCompra.value.has_shipping ? (docCompraForm.shipping_cost || 0) : null,
        supplier: docCompraForm.supplier || null,
      });
      await call("costeo_yelke.api.costeo_api.validar_documento", { doctype: docCompra.value.doctype, name: docCompra.value.name });
      const poName = docCompra.value.doctype === "Purchase Order" ? docCompra.value.name : null;
      await loadDocCompra(docCompra.value.doctype, docCompra.value.name);
      if (poName) {
        await loadSolicitud();
        // desbloquea el recibo de esta OC solo, ya prellenado -- no hace falta un
        // click extra para "crear el recibo" después de validar
        try {
          const r = await call("costeo_yelke.api.costeo_api.crear_recibo_oc", { po: poName });
          if (r.name) { reciboOcSel.value = poName; await loadRecibo(r.name); }
        } catch { /* no aplica (p. ej. ya no tiene almacén de materias primas) -- se ignora */ }
      }
      // refresca los lotes (RFQ/Presupuesto/OC/Recibo, docstatus incluido) para que
      // el botón se pinte de verde al instante, sin tener que recargar la página
      await loadLotesProduccion();
      showToast("Validado");
    } catch (e) { showToast(e.message || "No se pudo validar", "error"); }
    finally { advancing.value = false; }
  }
  // Paso de revisión intermedia (esquema Doble) -- hoy solo aplica cuando
  // docCompra.doctype es Purchase Order (materia prima o subcontratada, ver
  // requiere_doble_validacion en get_documento_compra).
  async function revisarDocCompra() {
    if (!docCompra.value) return;
    advancing.value = true;
    try {
      await call("costeo_yelke.api.costeo_api.marcar_revisado_documento", { doctype: docCompra.value.doctype, name: docCompra.value.name });
      await loadDocCompra(docCompra.value.doctype, docCompra.value.name);
      await loadLotesProduccion();
      showToast("Orden de compra revisada");
    } catch (e) { showToast(e.message || "No se pudo revisar", "error"); }
    finally { advancing.value = false; }
  }
  async function jalarPreciosOC() {
    if (!docCompra.value) return;
    advancing.value = true;
    try {
      await call("costeo_yelke.api.costeo_api.oc_jalar_precios", { po: docCompra.value.name });
      await loadDocCompra("Purchase Order", docCompra.value.name);
      showToast("Precios actualizados desde la lista / presupuesto");
    } catch (e) { showToast(e.message || "Error", "error"); }
    finally { advancing.value = false; }
  }

  // ── Recibo de compra (materia prima) ──
  const reciboOcs = ref([]);
  const reciboOcSel = ref("");
  const reciboPr = ref(null);
  const reciboItems = ref([]);
  const reciboForm = reactive({ posting_date: "", shipping_cost: null });
  const reciboValidated = computed(() => reciboPr.value?.docstatus === 1);
  // % de avance de materia prima -- ya calculado en el backend contra el total de
  // TODA la Solicitud de Material (los 3 lotes, aunque sus OC individuales no
  // existan todavía), ver get_recibos. null = todavía no hay Solicitud validada.
  const pctRecibidoMateriaPrima = ref(null);

  async function loadRecibos() {
    if (!planDetail.value) return;
    try {
      const r = await call("costeo_yelke.api.costeo_api.get_recibos", { plan: planDetail.value.name });
      reciboOcs.value = r.ocs || [];
      pctRecibidoMateriaPrima.value = r.pct_recibido ?? null;
      if (!reciboOcs.value.some((o) => o.name === reciboOcSel.value)) reciboOcSel.value = reciboOcs.value[0]?.name || "";
      const sel = reciboOcs.value.find((o) => o.name === reciboOcSel.value);
      if (sel && sel.receipts.length) await loadRecibo(sel.receipts[sel.receipts.length - 1]);
      else reciboPr.value = null;
    } catch { /* ignore */ }
  }
  async function selectReciboOc(po) {
    reciboOcSel.value = po;
    const sel = reciboOcs.value.find((o) => o.name === po);
    if (sel && sel.receipts.length) await loadRecibo(sel.receipts[sel.receipts.length - 1]);
    else reciboPr.value = null;
  }
  // Pestaña de recibo de UNA OC de un lote -- usa directo el `receipt` que ya trae
  // get_lotes_produccion (no depende de reciboOcs/loadRecibos, que son de la lista
  // general de recibos y pueden no estar cargados en la pantalla del lote). Al
  // validar la OC ya se desbloquea solo (ver validarDocCompra); esto sólo cubre el
  // caso de una OC validada antes de ese cambio, que todavía no tenga recibo.
  async function selectReciboLote(po) {
    reciboOcSel.value = po.name;
    advancing.value = true;
    try {
      if (po.receipt) {
        await loadRecibo(po.receipt.name);
      } else {
        const r = await call("costeo_yelke.api.costeo_api.crear_recibo_oc", { po: po.name });
        if (r.name) await loadRecibo(r.name);
        await loadLotesProduccion();
      }
    } catch (e) { showToast(e.message || "Error", "error"); }
    finally { advancing.value = false; }
  }
  async function loadRecibo(pr) {
    const r = await call("costeo_yelke.api.costeo_api.get_documento_compra", { doctype: "Purchase Receipt", name: pr });
    reciboPr.value = r;
    reciboItems.value = (r.items || []).map((i) => ({ ...i }));
    reciboForm.posting_date = r.posting_date || "";
    // OJO: sin "|| 0" -- null significa "nadie lo ha capturado todavía" (obligatorio,
    // ver PurchaseDocPanel shipping-required), distinto de "0 porque no hubo envío".
    reciboForm.shipping_cost = r.shipping_cost;
  }
  async function crearRecibo() {
    if (!reciboOcSel.value) return;
    advancing.value = true;
    try {
      const r = await call("costeo_yelke.api.costeo_api.crear_recibo_oc", { po: reciboOcSel.value });
      await loadRecibos();
      if (r.name) await loadRecibo(r.name);
      showToast("Recibo de compra creado");
    } catch (e) { showToast(e.message || "Error al crear el recibo", "error"); }
    finally { advancing.value = false; }
  }
  async function guardarRecibo() {
    if (!reciboPr.value) return;
    advancing.value = true;
    try {
      await call("costeo_yelke.api.costeo_api.guardar_documento_compra", {
        doctype: "Purchase Receipt", name: reciboPr.value.name,
        posting_date: reciboForm.posting_date || null, items: JSON.stringify(reciboItems.value),
        shipping_cost: reciboForm.shipping_cost === "" ? null : reciboForm.shipping_cost,
      });
      await loadRecibo(reciboPr.value.name);
      showToast("Recibo guardado");
    } catch (e) { showToast(e.message || "Error al guardar", "error"); }
    finally { advancing.value = false; }
  }
  async function validarRecibo() {
    if (!reciboPr.value) return;
    if (reciboForm.shipping_cost === null || reciboForm.shipping_cost === "" || reciboForm.shipping_cost === undefined) {
      showToast("Captura el costo de envío antes de validar (pon 0 si no hubo)", "error");
      return;
    }
    advancing.value = true;
    try {
      // guarda cambios pendientes (cantidades, fecha…) antes de validar -- si no, se
      // pierden en silencio al dar "Validar" directo sin pasar por "Guardar".
      await call("costeo_yelke.api.costeo_api.guardar_documento_compra", {
        doctype: "Purchase Receipt", name: reciboPr.value.name,
        posting_date: reciboForm.posting_date || null, items: JSON.stringify(reciboItems.value),
        shipping_cost: reciboForm.shipping_cost,
      });
      await call("costeo_yelke.api.costeo_api.validar_documento", { doctype: "Purchase Receipt", name: reciboPr.value.name });
      await loadRecibo(reciboPr.value.name);
      await loadRecibos();
      // refresca los lotes para que el botón "Recibo de compra" se pinte de verde
      // al instante, sin tener que recargar la página
      await loadLotesProduccion();
      showToast("Recibo validado — inventario actualizado");
    } catch (e) { showToast(e.message || "No se pudo validar", "error"); }
    finally { advancing.value = false; }
  }

  // ── Subcontratación (maquila) ──
  const subOcs = ref([]);
  const subSel = ref("");
  const subPo = ref(null);
  const subItems = ref([]);
  const subForm = reactive({ schedule_date: "", payment_terms_template: "", tc_name: "", shipping_cost: 0 });
  const subValidated = computed(() => subPo.value?.docstatus === 1);
  const subHasRate = computed(() => subItems.value.some((i) => i.has_rate));
  const subDone = computed(() => subOcs.value.length > 0 && subOcs.value.every((o) => o.docstatus === 1));

  const flujo = reactive({ po_validated: false, supplier: "", qty_total: 0, qty_subcontratada: 0, qty_pendiente: 0, scos: [], warehouses: [], address_options: [], contact_options: [] });
  const scoActivo = ref("");
  const scoSel = computed(() => flujo.scos.find((s) => s.name === scoActivo.value) || null);
  const scoValidated = computed(() => scoSel.value?.docstatus === 1);

  // Materia prima de la SCO agrupada POR MATERIAL. Con el modelo por pieza el mismo
  // material aparece una vez por cada pieza que lo usa (6 renglones de gabardina en
  // el corte), y lo que de verdad se le entrega al taller es un solo montón. El
  // redondeo hacia arriba también es sobre el total (ver
  // _redondear_arriba_por_material), así que esta suma es exactamente lo que va a
  // decir la transferencia.
  const materialesSco = computed(() => {
    const g = new Map();
    for (const m of scoSel.value?.supplied_items || []) {
      const k = m.rm_item_code;
      const prev = g.get(k);
      if (prev) { prev.required_qty += Number(m.required_qty) || 0; prev.piezas += 1; }
      else g.set(k, { ...m, required_qty: Number(m.required_qty) || 0, piezas: 1 });
    }
    return [...g.values()].map((m) => ({
      ...m, required_qty: Math.round(m.required_qty * 1e6) / 1e6,
      // Disponible es por almacén (no por renglón): el mismo material sale de un solo lugar.
      falta: m.disponible !== null && m.disponible !== undefined && Number(m.disponible) < Math.round(m.required_qty * 1e6) / 1e6 - 1e-6,
    }));
  });
  // Lo que el taller va a ENTREGAR, agrupado por artículo (el cuello que pasa por
  // dos servicios viene en dos renglones de porción).
  const piezasSco = computed(() => {
    const g = new Map();
    for (const it of scoSel.value?.items || []) {
      const prev = g.get(it.item_code);
      if (prev) { prev.qty += Number(it.qty) || 0; prev.received_qty += Number(it.received_qty) || 0; }
      else g.set(it.item_code, { ...it, qty: Number(it.qty) || 0, received_qty: Number(it.received_qty) || 0 });
    }
    return [...g.values()];
  });
  // Lo que se le paga: servicio × pieza con su cantidad, precio e importe.
  const serviciosSco = computed(() => (scoSel.value?.service_items || []).filter((s) => Number(s.amount) > 0 || Number(s.rate) > 0));
  const importeSco = computed(() => (scoSel.value?.service_items || []).reduce((a, s) => a + (Number(s.amount) || 0), 0));
  const scoForm = reactive({ supplier_warehouse: "", set_warehouse: "", supplier_address: "", contact_person: "", shipping_address: "", distribute_additional_costs_based_on: "Qty" });
  const scoCostos = ref([]);

  const transDoc = ref(null);
  const transForm = reactive({ from_warehouse: "", to_warehouse: "", distribute_additional_costs_based_on: "Qty" });
  const transCostos = ref([]);
  const transValidated = computed(() => transDoc.value?.docstatus === 1);
  const transferDone = computed(() => scoSel.value?.transfer?.done);

  const scr = ref(null);
  const scrForm = reactive({ set_warehouse: "", rejected_warehouse: "", supplier_warehouse: "", distribute_additional_costs_based_on: "Qty" });
  const scrCostos = ref([]);
  const scrValidated = computed(() => scr.value?.docstatus === 1);

  const omGeneral = reactive({ om_modelo: "", om_tela: "", om_color: "", om_color_principal: "", om_forro: "", om_combinacion: "", om_fecha_requerida: "", om_ubicacion: "", om_aberturas: 0, om_bordado: 0, om_estampado: 0, om_sublimado: 0, om_reflejante: 0, om_observaciones: "" });
  const omCab = ref([]);
  const omDama = ref([]);
  const omProc = ref([]);
  const omTablas = ref([]);
  const omArchivos = ref([]);
  const omUploading = ref(false);
  // La Orden de Manufactura se edita desde CUALQUIER etapa: hay una sola ficha por
  // proyecto y al guardar se replica a todas las demás OC de subcontratación (ver
  // guardar_om). Solo deja de ser editable si la OC está cancelada. Arranca en
  // `false` a propósito -- mientras se resuelve loadOm() de la etapa recién abierta,
  // el formulario no aparece editable "de más" ni por un instante.
  const omEditable = ref(false);

  async function loadSubcontratos() {
    if (!planDetail.value) return;
    try {
      const r = await call("costeo_yelke.api.costeo_api.get_subcontratos", { plan: planDetail.value.name });
      subOcs.value = r.ocs || [];
      if (!subOcs.value.some((o) => o.name === subSel.value)) subSel.value = subOcs.value[0]?.name || "";
      if (subSel.value) await loadSub(subSel.value); else subPo.value = null;
    } catch { /* ignore */ }
    await loadLotesProduccion();
  }
  async function crearSubcontratos() {
    advancing.value = true;
    try {
      await call("costeo_yelke.api.costeo_api.plan_crear_subcontratacion", { plan: planDetail.value.name });
      await loadSubcontratos();
      showToast("Órdenes de subcontrato creadas");
    } catch (e) { showToast(e.message || "Error", "error"); }
    finally { advancing.value = false; }
  }
  async function selectSub(po) { subSel.value = po; advancing.value = true; try { await loadSub(po); } finally { advancing.value = false; } }
  async function loadSub(po) {
    const r = await call("costeo_yelke.api.costeo_api.get_documento_compra", { doctype: "Purchase Order", name: po });
    subPo.value = r;
    subItems.value = (r.items || []).map((i) => ({ ...i }));
    subForm.schedule_date = r.schedule_date || "";
    subForm.payment_terms_template = r.payment_terms_template || "";
    subForm.tc_name = r.tc_name || "";
    subForm.shipping_cost = r.shipping_cost || 0;
    previewKey.value++;
    await loadOm(po);
    await loadFlujo(po);
  }

  async function loadFlujo(po) {
    try {
      const r = await call("costeo_yelke.api.costeo_api.sub_get_flujo", { po });
      Object.assign(flujo, {
        po_validated: r.po_validated, supplier: r.supplier,
        qty_total: r.qty_total || 0, qty_subcontratada: r.qty_subcontratada || 0, qty_pendiente: r.qty_pendiente || 0,
        scos: r.scos || [], warehouses: r.warehouses || [], address_options: r.address_options || [], contact_options: r.contact_options || [],
      });
      if (!flujo.scos.some((s) => s.name === scoActivo.value)) {
        scoActivo.value = flujo.scos[flujo.scos.length - 1]?.name || "";
      }
      await selectSco(scoActivo.value, true);
    } catch { /* ignore */ }
  }
  async function selectSco(name, _recargado = false) {
    scoActivo.value = name;
    const s = flujo.scos.find((x) => x.name === name);
    // Un encargo recién creado (desde la matriz) todavía no está en la lista del
    // taller: se vuelve a pedir una vez en vez de dejar el detalle en blanco.
    if (!s && name && !_recargado && subPo.value?.name) {
      await loadFlujo(subPo.value.name);
      if (flujo.scos.some((x) => x.name === name)) return selectSco(name, true);
    }
    if (!s && !flujo.scos.some((x) => x.name === name)) { scr.value = null; transDoc.value = null; return; }
    scoForm.supplier_warehouse = s.supplier_warehouse || "";
    scoForm.set_warehouse = s.set_warehouse || "";
    scoForm.supplier_address = s.supplier_address || "";
    scoForm.contact_person = s.contact_person || "";
    scoForm.shipping_address = s.shipping_address || "";
    scoForm.distribute_additional_costs_based_on = s.distribute_additional_costs_based_on || "Qty";
    scoCostos.value = (s.additional_costs || []).map((c) => ({ ...c }));
    if ((s.receipts || []).length) { await loadScr(s.receipts[0].name); }
    else { scr.value = null; }
    const te = (s.transfer?.entries || []);
    const target = te.find((e) => e.docstatus === 0) || te[te.length - 1];
    if (target) { await loadTrans(target.name); } else { transDoc.value = null; }
  }
  async function loadTrans(name) {
    try {
      const r = await call("costeo_yelke.api.costeo_api.sub_get_transferencia", { stock_entry: name });
      transDoc.value = r;
      transForm.from_warehouse = r.from_warehouse || r.items?.[0]?.s_warehouse || r.recommended_source || "";
      transForm.to_warehouse = r.to_warehouse || r.items?.[0]?.t_warehouse || "";
      transForm.distribute_additional_costs_based_on = r.distribute_additional_costs_based_on || "Qty";
      transCostos.value = (r.additional_costs || []).map((c) => ({ ...c }));
    } catch { /* ignore */ }
  }

  // El taller puede haberse quedado con material de una tanda anterior (sobrante de
  // redondeo, ver sub_saldo_talleres). Esto baja cada renglón por lo que ya tiene,
  // para no mandarle de más. Es MANUAL a propósito: el sobrante puede quedarse con
  // él o regresar al almacén, y solo la persona sabe cuál de las dos pasó.

  const talleresSaldo = ref([]);
  async function loadSaldoTalleres() {
    if (!planCosteoName.value) return;
    try {
      const r = await call("costeo_yelke.api.costeo_api.sub_saldo_talleres", { costeo: planCosteoName.value });
      talleresSaldo.value = r.talleres || [];
    } catch { talleresSaldo.value = []; }
  }
  async function devolverMaterialTaller(taller) {
    advancing.value = true;
    try {
      const r = await call("costeo_yelke.api.costeo_api.sub_devolver_material", {
        costeo: planCosteoName.value, warehouse: taller.warehouse,
      });
      const docs = r.stock_entries?.length ? r.stock_entries.join(", ") : r.stock_entry;
      showToast(`Devolución creada en borrador (${docs}) — revísala y valídala`);
      await loadSaldoTalleres();
    } catch (e) { showToast(e.message || "No se pudo crear la devolución", "error"); }
    finally { advancing.value = false; }
  }

  async function guardarSco() {
    if (!scoSel.value) return;
    advancing.value = true;
    try {
      await call("costeo_yelke.api.costeo_api.sub_guardar_sco", { sco: scoSel.value.name, campos: JSON.stringify(scoForm), costos: JSON.stringify(scoCostos.value) });
      await loadFlujo(subPo.value.name);
      showToast("Orden de subcontratación guardada");
    } catch (e) { showToast(e.message || "Error al guardar", "error"); }
    finally { advancing.value = false; }
  }
  async function validarSco() {
    if (!scoSel.value) return;
    advancing.value = true;
    try {
      await call("costeo_yelke.api.costeo_api.sub_guardar_sco", { sco: scoSel.value.name, campos: JSON.stringify(scoForm), costos: JSON.stringify(scoCostos.value) });
      await call("costeo_yelke.api.costeo_api.sub_validar_sco", { sco: scoSel.value.name });
      await loadFlujo(subPo.value.name);
      // refresca el estado por etapa (sco_docstatus) para que el botón de
      // Transferencia se habilite de inmediato, sin recargar la página
      await loadLotesProduccion();
      showToast("Orden de subcontratación validada");
    } catch (e) { showToast(e.message || "No se pudo validar", "error"); }
    finally { advancing.value = false; }
  }
  function addCosto() { scoCostos.value.push({ description: "", amount: 0, expense_account: "" }); }
  function removeCosto(i) { scoCostos.value.splice(i, 1); }
  function addCostoTrans() { transCostos.value.push({ description: "", amount: 0, expense_account: "", proveedor_flete: "" }); }
  function removeCostoTrans(i) { transCostos.value.splice(i, 1); }
  // Descripción default "Envío" -- si el usuario deja la fila sin tocar y guarda, no se
  // pierde en silencio (el backend descarta filas sin descripción) y de una vez cubre
  // el caso más común (el costo obligatorio de este recibo es justo el de envío).
  function addCostoScr() { scrCostos.value.push({ description: "Envío", amount: 0, expense_account: "", proveedor_flete: "" }); }
  function removeCostoScr(i) { scrCostos.value.splice(i, 1); }

  // Cuando lo único que sobraba era el redondeo hacia arriba, el backend recorta a
  // la existencia real en vez de bloquear por un faltante inexistente
  // (_ajustar_a_existencia). Se dice, para que nadie se pregunte por qué salió un
  // número distinto al de la orden.
  function _mensajeAjusteExistencia(r) {
    const a = r?.ajustado_a_existencia || (r?.transferencia && r.transferencia.ajustado_a_existencia);
    const keys = a ? Object.keys(a) : [];
    if (!keys.length) return "";
    return " · se ajustó a la existencia por redondeo (" +
      keys.map((k) => `${k} -${a[k]}`).join(", ") + ")";
  }

  async function transferirMaterial() {
    if (!scoSel.value) return;
    advancing.value = true;
    try {
      const r = await call("costeo_yelke.api.costeo_api.sub_transferir_material", { sco: scoSel.value.name });
      await loadFlujo(subPo.value.name);
      showToast("Transferencia creada en borrador · revisa almacenes y valida" + _mensajeAjusteExistencia(r));
    } catch (e) { showToast(e.message || "No se pudo crear la transferencia", "error"); }
    finally { advancing.value = false; }
  }
  async function guardarTrans() {
    if (!transDoc.value) return;
    advancing.value = true;
    try {
      // OJO: from_warehouse NO se manda -- cada fila ya trae su propio s_warehouse
      // (editable por material, ver el selector por renglón); mandar el del header
      // aparte pisaría esos ajustes y forzaría el mismo almacén en todas las filas.
      await call("costeo_yelke.api.costeo_api.sub_guardar_transferencia", {
        stock_entry: transDoc.value.name,
        to_warehouse: transForm.to_warehouse || null,
        items: JSON.stringify(transDoc.value.items),
        costos: JSON.stringify(transCostos.value),
        distribute_additional_costs_based_on: transForm.distribute_additional_costs_based_on,
      });
      await loadTrans(transDoc.value.name);
      showToast("Transferencia guardada");
    } catch (e) { showToast(e.message || "Error al guardar", "error"); }
    finally { advancing.value = false; }
  }
  async function validarTransferencia() {
    if (!transDoc.value) return;
    if (transCostos.value.some((c) => Number(c.amount) > 0 && !c.proveedor_flete)) {
      showToast("Indica el transportista de cada costo adicional con importe", "error");
      return;
    }
    advancing.value = true;
    try {
      await call("costeo_yelke.api.costeo_api.sub_guardar_transferencia", {
        stock_entry: transDoc.value.name,
        to_warehouse: transForm.to_warehouse || null,
        items: JSON.stringify(transDoc.value.items),
        costos: JSON.stringify(transCostos.value),
        distribute_additional_costs_based_on: transForm.distribute_additional_costs_based_on,
      });
      await call("costeo_yelke.api.costeo_api.sub_validar_transferencia", { stock_entry: transDoc.value.name });
      await loadFlujo(subPo.value.name);
      // refresca el estado por etapa (transfer_done) para que el botón de Recibo se
      // habilite de inmediato, sin recargar la página
      await loadLotesProduccion();
      showToast("Transferencia validada · material enviado al taller");
    } catch (e) {
      const msg = /NegativeStock|negative stock|stock negativo/i.test(e.message || "")
        ? "Stock negativo: la materia prima aún no está en el almacén de origen. Cómprala y recíbela (Recibo de compra) antes de transferir."
        : (e.message || "No se pudo validar la transferencia");
      showToast(msg, "error");
    }
    finally { advancing.value = false; }
  }

  async function crearReciboSub() {
    if (!scoSel.value) return;
    advancing.value = true;
    try {
      const r = await call("costeo_yelke.api.costeo_api.sub_crear_recibo", { sco: scoSel.value.name });
      await loadFlujo(subPo.value.name);
      if (r.scr) await loadScr(r.scr);
      showToast("Recibo de subcontratación creado");
    } catch (e) { showToast(e.message || "No se pudo crear el recibo", "error"); }
    finally { advancing.value = false; }
  }
  async function loadScr(name) {
    try {
      const r = await call("costeo_yelke.api.costeo_api.sub_get_recibo", { scr: name });
      scr.value = r;
      scrForm.set_warehouse = r.set_warehouse || "";
      scrForm.rejected_warehouse = r.rejected_warehouse || "";
      scrForm.supplier_warehouse = r.supplier_warehouse || "";
      scrForm.distribute_additional_costs_based_on = r.distribute_additional_costs_based_on || "Qty";
      scrCostos.value = (r.additional_costs || []).map((c) => ({ ...c }));
    } catch { /* ignore */ }
  }
  async function guardarScr() {
    if (!scr.value) return;
    advancing.value = true;
    try {
      await call("costeo_yelke.api.costeo_api.sub_guardar_recibo", { scr: scr.value.name, set_warehouse: scrForm.set_warehouse || null, rejected_warehouse: scrForm.rejected_warehouse || null, supplier_warehouse: scrForm.supplier_warehouse || null, items: JSON.stringify(scr.value.items), costos: JSON.stringify(scrCostos.value), distribute_additional_costs_based_on: scrForm.distribute_additional_costs_based_on });
      await loadScr(scr.value.name);
      showToast("Recibo guardado");
    } catch (e) { showToast(e.message || "Error al guardar", "error"); }
    finally { advancing.value = false; }
  }
  async function validarScr(onDone) {
    if (!scr.value) return;
    if (!scrCostos.value.some((c) => (c.description || "").trim())) {
      showToast("Registra al menos un costo adicional antes de validar (pon 0 si no hubo)", "error");
      return;
    }
    if (scrCostos.value.some((c) => Number(c.amount) > 0 && !c.proveedor_flete)) {
      showToast("Indica el transportista de cada costo adicional con importe", "error");
      return;
    }
    advancing.value = true;
    try {
      await call("costeo_yelke.api.costeo_api.sub_guardar_recibo", { scr: scr.value.name, set_warehouse: scrForm.set_warehouse || null, rejected_warehouse: scrForm.rejected_warehouse || null, supplier_warehouse: scrForm.supplier_warehouse || null, items: JSON.stringify(scr.value.items), costos: JSON.stringify(scrCostos.value), distribute_additional_costs_based_on: scrForm.distribute_additional_costs_based_on });
      await call("costeo_yelke.api.costeo_api.validar_documento", { doctype: "Subcontracting Receipt", name: scr.value.name });
      await loadFlujo(subPo.value.name);
      // refresca el estado por etapa (receipt_validated) para que el botón se pinte
      // de verde de inmediato, sin recargar la página
      await loadLotesProduccion();
      if (onDone) await onDone(); // recarga produccion_completa -- desbloquea "Enviar"/"Facturar"
      showToast("Recibo de subcontratación validado · producto en inventario");
    } catch (e) { showToast(e.message || "No se pudo validar", "error"); }
    finally { advancing.value = false; }
  }

  // OM de esta orden de maquila armada desde la OM general del producto (un registro
  // por producto, solo lo asignado a este taller). Vacía = costeo sin OM general: se
  // usa el formulario de siempre, capturado directo en la orden de compra.
  const omDeOc = ref([]);
  async function loadOm(po) {
    try {
      omDeOc.value = await call("costeo_yelke.api.om_general.om_de_oc", { po });
    } catch { omDeOc.value = []; }
    try {
      const r = await call("costeo_yelke.api.costeo_api.get_om", { po });
      Object.assign(omGeneral, r.general);
      omCab.value = r.tallas_caballero.length ? r.tallas_caballero : [emptyTalla(OM_CAB)];
      omDama.value = r.tallas_dama.length ? r.tallas_dama : [emptyTalla(OM_DAMA)];
      omProc.value = r.procesos || [];
      omTablas.value = r.tablas || [];
      omArchivos.value = r.archivos || [];
      omEditable.value = r.editable !== false;
    } catch { /* ignore */ }
  }
  function addProceso() { omProc.value.push({ proceso: "", nombre_proceso: "", ubicacion: "", colores: "" }); }
  function removeProceso(i) { omProc.value.splice(i, 1); }
  function nextId(prefix, existing) {
    let max = 0;
    (existing || []).forEach((v) => { const m = new RegExp(`^${prefix}(\\d+)$`).exec(String(v || "")); if (m) max = Math.max(max, parseInt(m[1], 10)); });
    return `${prefix}${max + 1}`;
  }
  function addTabla() { omTablas.value.push({ name: `Tabla ${omTablas.value.length + 1}`, unit: "", columns: ["c1"], rows: [{ id: "r1", cells: { c1: "" } }] }); }
  function removeTabla(ti) { omTablas.value.splice(ti, 1); }

  // ── Plantillas de tablas de medidas ──
  // La primera fila de `matrix` es el encabezado (se captura como texto normal, igual
  // que cualquier fila -- la tabla no distingue encabezado de datos, es una grilla
  // libre). `matrix[i][j] === null` deja esa celda vacía en vez de "null".
  function tablaDesdeMatriz(name, unit, matrix) {
    const nCols = matrix[0].length;
    const columns = Array.from({ length: nCols }, (_, i) => `c${i + 1}`);
    const rows = matrix.map((rowVals, ri) => {
      const cells = {};
      columns.forEach((c, ci) => { cells[c] = rowVals[ci] != null ? String(rowVals[ci]) : ""; });
      return { id: `r${ri + 1}`, cells };
    });
    return { name, unit, columns, rows };
  }
  const MEDIDAS_PLANTILLAS = [
    {
      key: "alpla-centro",
      label: "Moldes Alpla Zona Centro",
      tablas: [
        tablaDesdeMatriz("Medidas Playera Polo (Terminadas) - Alpla Centro", "cm", [
          ["TALLA", "Caballero Alto", "Caballero Ancho", "Dama Alto", "Dama Ancho"],
          ["XCH", 66, 50, 60, 46],
          ["CH", 69, 52, 63, 48],
          ["M", 72, 54, 66, 50],
          ["G", 75, 56, 69, 51],
          ["XG", 78, 59, 71, 55],
          ["2XG", 80, 62, 71, 58],
          ["3XG", 80, 65, 73, 61],
          ["4XG", 82, 68, 73, 64],
          ["5XG", 82, 71, 75, 67],
          ["Aletilla", 15, 3.5, 15, 2.5],
        ]),
        tablaDesdeMatriz("Medidas de Tejido de Cuellos y Puños Playera Polo - Alpla Centro", "cm", [
          ["TALLA", "XCH", "CH", "M", "G", "XG", "2XG", "3XG", "4XG", "5XG"],
          ["Caballero", null, null, null, null, null, null, null, null, null],
          ["Largo de cuello (cm)", 40, 40, 40, 40, 40, 42, 42, 42, 42],
          ["Ancho de cuello (cm)", 8.5, 8.5, 8.5, 8.5, 8.5, 8.5, 8.5, 8.5, 8.5],
          ["Largo puño (cm)", 41, 41, 41, 41, 41, 41, 41, 41, 41],
          ["Ancho puño (cm)", 3.5, 3.5, 3.5, 3.5, 3.5, 3.5, 3.5, 3.5, 3.5],
          ["Dama", null, null, null, null, null, null, null, null, null],
          ["Largo de cuello (cm)", 38, 38, 38, 38, 38, 40, 40, 40, 40],
          ["Ancho de cuello (cm)", 8, 8, 8, 8, 8, 8, 8, 8, 8],
          ["Largo puño (cm)", 41, 41, 41, 41, 41, 41, 41, 41, 41],
          ["Ancho puño (cm)", 3.5, 3.5, 3.5, 3.5, 3.5, 3.5, 3.5, 3.5, 3.5],
        ]),
      ],
    },
    {
      key: "alpla-norte",
      label: "Playera Polo Alpla Zona Norte",
      tablas: [
        tablaDesdeMatriz("Medidas Playera Polo (Terminadas) - Alpla Norte", "cm", [
          ["TALLA", "Caballero Alto", "Caballero Ancho", "Dama Alto", "Dama Ancho"],
          ["S", 72, 52, 65, 48],
          ["M", 75, 54, 67, 50],
          ["G", 78, 56, 69, 51],
          ["XG", 80, 59, 71, 55],
          ["2XG", 82, 62, 73, 58],
          ["3XG", 82, 65, 76, 61],
          ["4XG", 84, 68, 76, 64],
          ["5XG", 84, 71, 78, 67],
          ["Aletilla", 15, 3.5, 15, 2.5],
        ]),
      ],
    },
    {
      key: "polo-blanca",
      label: "Playera Polo Blanca (cm)",
      tablas: [
        tablaDesdeMatriz("Tabla de Medidas Playera Polo Blanca (cm)", "cm", [
          ["TALLA", "CH", "M", "G", "XG", "2XG", "3XG", "4XG", "5XG", "Tolerancia"],
          ["Ancho hombros (a)", 42.5, 43, 45, 49, 53.5, 55, 58.5, 61, "± 2 cm"],
          ["Ancho torso (b)", 50, 52, 54, 57, 61, 63, 64.5, 66, "± 2 cm"],
          ["Largo espalda (c)", 67, 69.5, 71, 74, 76.5, 76.5, 77, 78, "± 2 cm"],
        ]),
      ],
    },
    {
      key: "camisola-gabardina",
      label: "Camisola Gabardina (cm)",
      tablas: [
        tablaDesdeMatriz("Tabla Medidas Camisola Gabardina (cm)", "cm", [
          ["TALLA NÚMERO", 30, 32, 34, 36, "38 (G)", "40 (G)", 42, 44, 46, 48, 50, 52, 54, 56, 58, 60, "Tolerancia"],
          ["Ancho hombros (a)", 42, 44, 46.5, 47, 48.5, 50, 52, 54, 57, 61, 63, 65, 67, 69, 71, 73, "± 2 cm"],
          ["Ancho torso (b)", 53, 55, 56.5, 58, 60, 62, 64, 67, 69, 71, 73, 75, 77, 78.5, 80, 83.5, "± 2 cm"],
          ["Largo espalda (c)", 75, 75, 75, 77, 77, 77, 79, 79, 83, 83, 83, 85, 85, 87, 87, 87, "± 2 cm"],
        ]),
      ],
    },
    {
      key: "pantalon-gabardina",
      label: "Pantalón Gabardina (pulgadas)",
      tablas: [
        tablaDesdeMatriz("Tabla Medidas Pantalón Gabardina (pulgadas)", "pulg", [
          ["TALLA", 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 58, 60, "Tolerancia"],
          ["Contorno cintura (a)", 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 58, 60, "± 1 pulg."],
          ["Contorno pierna (b)", 18.5, 19.3, 20.1, 20.9, 21.7, 22.4, 23, 23.6, 24.4, 25.6, 26.7, 27.5, 28.3, 29.1, 30, 30.8, 31.5, "± 1 pulg."],
        ]),
      ],
    },
    {
      key: "chaleco-gabardina",
      label: "Chaleco Gabardina (cm)",
      tablas: [
        tablaDesdeMatriz("Tabla Medidas Chaleco Gabardina (cm)", "cm", [
          ["TALLA", "CH", "M", "G", "XG", "2XG", "3XG", "4XG", "5XG", "Tolerancia"],
          ["Ancho espalda (a)", 44, 48, 52, 56, 60, 64, 68, 72, "± 2 cm"],
          ["Ancho sisas (b)", 56, 59, 64, 66, 68, 72, 74, 77, "± 2 cm"],
          ["Largo espalda (c)", 73, 74, 77, 77, 77, 80, 80, 80, "± 2 cm"],
        ]),
      ],
    },
    {
      key: "cuello-redondo",
      label: "Playera Cuello Redondo (cm)",
      tablas: [
        tablaDesdeMatriz("Tabla Medidas Playera Cuello Redondo (cm)", "cm", [
          ["TALLA", "CH", "M", "G", "XG", "2XG", "3XG", "4XG", "5XG", "Tolerancia"],
          ["Ancho espalda (a)", 39, 42, 46, 50, 52, 55, 58, 61, "± 2 cm"],
          ["Ancho sisas (b)", 44, 50, 55, 58, 60, 63, 0, 0, "± 2 cm"],
          ["Largo espalda (c)", 65, 66, 72, 76, 77, 77, 78, 78, "± 2 cm"],
        ]),
      ],
    },
    {
      key: "mezclilla-caballero",
      label: "Pantalón Mezclilla Caballero (pulgadas)",
      tablas: [
        tablaDesdeMatriz("Tabla de Medidas Pantalón Mezclilla Caballero — Pulgadas, 100% Algodón", "pulg", [
          ["TALLAS", 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48, "Tol +/-"],
          ["Cintura", 30, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50, "1/2"],
          ["Cadera", "37 1/4", "39 1/4", "41 1/4", "43 1/4", "45 1/4", "47 1/4", "49 1/4", "51 1/4", "53 1/4", "55 1/4", "57 1/4", "3/4"],
          ["Rodilla", "16 1/2", "17 1/2", "18 1/2", "19 1/2", "20 1/2", "21 1/2", "22 1/2", "23 1/2", "24 1/2", "25 1/2", "26 1/2", "3/4"],
          ["Valenciana", "15 1/8", "16 1/8", "17 1/8", "18 1/8", "19 1/8", "20 1/8", "21 1/8", "22 1/8", "23 1/8", "24 1/8", "25 1/8", "3/4"],
          ["Tiro delantero", "8 1/4", "8 3/4", "9 1/4", "9 3/4", "10 1/4", "10 3/4", "11 1/4", "11 3/4", "12 1/4", "12 3/4", "13 1/4", "3/4"],
          ["Tiro trasero", "13 5/8", "14 1/8", "14 5/8", "15 1/8", "15 5/8", "16 1/8", "16 5/8", "17 1/8", "17 5/8", "18 1/8", "18 5/8", "3/4"],
          ["Largo entrepierna", 32, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32, null],
        ]),
      ],
    },
    {
      key: "mezclilla-dama",
      label: "Pantalón Mezclilla Stretch Dama",
      tablas: [
        tablaDesdeMatriz("Tabla de Medidas Pantalón Mezclilla Stretch Dama", "", [
          ["TALLAS", 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, "Tol +/-"],
          ["Contorno cintura (pulgadas)", "28\"", "29.5\"", "30.7\"", "32.28\"", "33.5\"", "34.6\"", "36.22\"", "37.4\"", "38.6\"", "39.8\"", "40.9\"", "41.7\"", "1/2 pulg."],
          ["Ancho cintura (cm)", 36, 37.5, 39, 41, 42.5, 44, 46, 47.5, 49, 50.5, 52, 53, "1 cm"],
          ["Tiro delantero (cm)", 24, 25, 26, 27, 28, 29, 29, 29, 30, 31, 32, 33, "1 cm"],
          ["Tiro trasero (cm)", 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, "1 cm"],
          ["Largo entrepierna (cm)", 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, null],
        ]),
      ],
    },
  ];
  const medidasTemplates = MEDIDAS_PLANTILLAS.map(t => ({ key: t.key, label: t.label }));
  // Copia de las tablas de una plantilla, para el editor de la OM general.
  function tablasDePlantilla(key) {
    const tpl = MEDIDAS_PLANTILLAS.find(t => t.key === key);
    return tpl ? JSON.parse(JSON.stringify(tpl.tablas)) : [];
  }
  function addTablaPlantilla(key) {
    const tpl = MEDIDAS_PLANTILLAS.find(t => t.key === key);
    if (!tpl) return;
    for (const tabla of tpl.tablas) {
      omTablas.value.push(JSON.parse(JSON.stringify(tabla)));
    }
  }
  function addColumna(t) {
    const cid = nextId("c", t.columns);
    t.columns.push(cid);
    t.rows.forEach((r) => { r.cells[cid] = r.cells[cid] || ""; });
  }
  function removeColumna(t, ci) {
    if (t.columns.length <= 1) { showToast("La tabla debe conservar al menos una columna", "error"); return; }
    const cid = t.columns[ci];
    t.columns.splice(ci, 1);
    t.rows.forEach((r) => { delete r.cells[cid]; });
  }
  function addFila(t) {
    const rid = nextId("r", t.rows.map((r) => r.id));
    const cells = {};
    t.columns.forEach((c) => { cells[c] = ""; });
    t.rows.push({ id: rid, cells });
  }
  function removeFila(t, ri) {
    if (t.rows.length <= 1) { showToast("La tabla debe conservar al menos una fila", "error"); return; }
    t.rows.splice(ri, 1);
  }
  function tallaTotal(row, sizes) { return sizes.reduce((s, k) => s + (Number(row[k]) || 0), 0); }
  async function onOmFile(ev) {
    const files = Array.from(ev.target.files || []);
    if (!files.length || !subPo.value) return;
    omUploading.value = true;
    try {
      for (const f of files) {
        const res = await uploadFile(f, { doctype: "Purchase Order", docname: subPo.value.name });
        if (res?.file_url) omArchivos.value.push({ archivo: res.file_url, descripcion: res.file_name || "" });
      }
      showToast("Archivo(s) subido(s). Recuerda Guardar.");
    } catch (e) { showToast(e.message || "Error al subir", "error"); }
    finally { omUploading.value = false; ev.target.value = ""; }
  }
  function removeArchivo(i) { omArchivos.value.splice(i, 1); }

  async function _guardarSubDatos() {
    // Si la OC de maquila ya se validó sola (ver abrirNuevoLote/lote_abrir --
    // se auto-valida por conveniencia), ya no hay nada que guardar AHÍ (fecha,
    // items, envío son términos comerciales, no se pueden tocar post-validación)
    // -- pero eso no debe impedir guardar la Orden de Manufactura de abajo, que
    // SÍ se permite editar aunque la OC ya esté validada (ver guardar_om /
    // _guardar_om_una, om_* con allow_on_submit). Antes esta llamada tronaba
    // ("El documento ya está validado") y ni siquiera llegaba a intentar
    // guardar_om -- por eso no dejaba capturar la ficha técnica en una OC que
    // se abrió y validó sola al abrir el lote.
    if (subPo.value.docstatus === 0) {
      await call("costeo_yelke.api.costeo_api.guardar_documento_compra", {
        doctype: "Purchase Order", name: subPo.value.name,
        schedule_date: subForm.schedule_date || null, payment_terms_template: subForm.payment_terms_template || null,
        tc_name: subForm.tc_name || null, items: JSON.stringify(subItems.value),
        shipping_cost: subPo.value.has_shipping ? (subForm.shipping_cost || 0) : null,
      });
    }
    // Sólo la OC maestra puede escribir la Orden de Manufactura -- en las demás el
    // formulario ya está deshabilitado (nada que guardar) y el backend la rechazaría.
    // Este intento va en SU PROPIO try/catch, separado del guardado de la OC de
    // arriba: si por lo que sea (omEditable desactualizado, dos pestañas abiertas...)
    // el backend lo rechaza, que NO tumbe el guardado/validado de la OC misma -- antes
    // ambos pasos compartían el mismo try, así que un rechazo de la OM aparecía como
    // "no se pudo guardar/validar" la orden completa, aunque sus propios cambios
    // (fecha, items, etc.) sí eran válidos.
    if (omEditable.value) {
      try {
        await call("costeo_yelke.api.costeo_api.guardar_om", {
          po: subPo.value.name, general: JSON.stringify(omGeneral),
          tallas_caballero: JSON.stringify(omCab.value), tallas_dama: JSON.stringify(omDama.value),
          procesos: JSON.stringify(omProc.value),
          tablas: JSON.stringify(omTablas.value), archivos: JSON.stringify(omArchivos.value),
        });
      } catch { /* la OC en sí ya se guardó bien arriba -- no tumbar todo por esto */ }
    }
  }
  async function guardarSub() {
    if (!subPo.value) return;
    advancing.value = true;
    try {
      await _guardarSubDatos();
      await loadSub(subPo.value.name);
      showToast("Guardado (orden + manufactura)");
    } catch (e) { showToast(e.message || "Error al guardar", "error"); }
    finally { advancing.value = false; }
  }
  async function validarSub() {
    if (!subPo.value) return;
    advancing.value = true;
    try {
      // guarda la orden + la Orden de Manufactura antes de validar -- si no, se
      // pierden en silencio al dar "Validar" directo sin pasar por "Guardar".
      await _guardarSubDatos();
      await call("costeo_yelke.api.costeo_api.validar_documento", { doctype: "Purchase Order", name: subPo.value.name });
      await loadSub(subPo.value.name);
      await loadSubcontratos();
      showToast("Orden de subcontrato validada");
    } catch (e) { showToast(e.message || "No se pudo validar", "error"); }
    finally { advancing.value = false; }
  }
  // Revisión intermedia de la Orden de Compra subcontratada (mismo esquema Doble
  // que la de materia prima, ver revisarDocCompra -- es el mismo doctype).
  async function revisarSub() {
    if (!subPo.value) return;
    advancing.value = true;
    try {
      await call("costeo_yelke.api.costeo_api.marcar_revisado_documento", { doctype: "Purchase Order", name: subPo.value.name });
      await loadSub(subPo.value.name);
      showToast("Orden de subcontrato revisada");
    } catch (e) { showToast(e.message || "No se pudo revisar", "error"); }
    finally { advancing.value = false; }
  }

  // ── Lotes de producción (vista por PARADAS) ──
  // Un lote es del COSTEO (cubre varios productos, cada uno a su cantidad) y se
  // descompone en PARADAS: un paso del flujo en un taller = 1 Subcontracting Order
  // + 1 envío + 1 recibo. `lotesProduccion` = r.lotes (lista plana); cada lote trae
  // `paradas` en orden de flujo, con `nivel` (columna) y `recibe_de` (dependencias).
  const lotesProduccion = ref([]);
  // Nombres de lote ya usados en TODO el costeo, también los de otras órdenes de
  // venta. El nombre del lote es la llave con la que se buscan la tabla de lotes del
  // costeo, las remisiones y las cotizaciones de proveedor -- que son del costeo, no
  // de la OV -- así que la numeración sigue corrida entre OV aunque cada una solo vea
  // los suyos (ver get_lotes_produccion).
  const loteRefsCosteo = ref([]);
  const productosCosteo = ref([]);      // r.productos: [{finished_item, item_name, root_po, root_po_docstatus}]
  const loteActivoRef = ref("");
  const loteParadaActiva = ref("");     // parada_id de la parada abierta en el detalle
  const nuevoLoteForm = reactive({ open: false, schedule_date: "", loading: false, porProducto: [] });

  const loteActivo = computed(() =>
    lotesProduccion.value.find((l) => l.lote_ref === loteActivoRef.value) || null
  );
  const paradaActiva = computed(() =>
    loteActivo.value?.paradas.find((p) => p.parada_id === loteParadaActiva.value) || null
  );
  // Un "carril" por producto del lote: sus paradas en orden de flujo + el producto
  // terminado al final. Una parada que cubre varios productos (mismo taller) aparece
  // en el carril de cada uno -- así cada proceso se lee por separado.
  const tracksLote = computed(() => {
    const lote = loteActivo.value;
    if (!lote) return [];
    return (lote.productos || []).map((prod) => {
      const paradas = (lote.paradas || [])
        .filter((p) => (p.productos || []).some((x) => x.finished_item === prod.finished_item))
        .slice()
        .sort((a, b) => a.nivel - b.nivel || a.orden - b.orden);
      const terminal = paradas.find((p) => p.es_terminal);
      return { ...prod, paradas, done: !!terminal && !!terminal.receipt_validated };
    });
  });
  // Si el panel "Nuevo lote" sigue abierto cuando se valida una OC de taller
  // (prerrequisito), se recalculan las cantidades sugeridas.
  watch(
    () => productosCosteo.value.map((p) => p.root_po_docstatus).join(","),
    () => { if (nuevoLoteForm.open) abrirNuevoLote(); }
  );

  async function loadLotesProduccion() {
    if (!planDetail.value) return;
    try {
      const r = await call("costeo_yelke.api.costeo_api.get_lotes_produccion", { plan: planDetail.value.name });
      // Mismo ruido de coma flotante que en la solicitud (ver limpiaNum): estas
      // cantidades salen de repartir el material entre lotes. Se limpian aquí
      // porque no solo se pintan -- también son el qty que se manda al crear la
      // solicitud de cotización y la orden de compra de ese lote.
      lotesProduccion.value = (r.lotes || []).map((l) => ({
        ...l,
        material_items: (l.material_items || []).map((m) => ({ ...m, qty: limpiaNum(m.qty) })),
      }));
      loteRefsCosteo.value = r.lote_refs_costeo || [];
      productosCosteo.value = r.productos || [];
    } catch { /* ignore */ }
    await loadSaldoTalleres();
  }
  function paradaEstado(p) {
    if (p.receipt_validated) return "done";
    if (p.transfer_done) return "transfer";
    if (p.sco) return "sco";
    return "pending";
  }
  function siguienteLoteLibre() {
    const existentes = new Set(lotesProduccion.value.map((l) => l.lote_ref));
    loteRefsCosteo.value.forEach((r) => { if (r) existentes.add(r); });
    mrLotes.value.forEach((l) => { if (l.lote_ref) existentes.add(l.lote_ref); });
    let n = 1;
    while (existentes.has(`Lote ${n}`)) n++;
    return `Lote ${n}`;
  }
  const siguienteLoteRef = siguienteLoteLibre;
  function siguienteParadaPendiente(lote) {
    return (lote?.paradas || []).find((p) => !p.receipt_validated) || null;
  }
  // Selecciona un lote y abre su primera parada pendiente (o la última si todas
  // están recibidas, para revisar).
  async function seleccionarLote(lote_ref) {
    loteActivoRef.value = lote_ref;
    const lote = lotesProduccion.value.find((l) => l.lote_ref === lote_ref);
    if (!lote || !(lote.paradas || []).length) { loteParadaActiva.value = ""; return; }
    const obj = siguienteParadaPendiente(lote) || lote.paradas[lote.paradas.length - 1];
    await seleccionarParada(obj);
  }
  async function seleccionarParada(parada) {
    if (loteParadaActiva.value !== parada.parada_id) { piezasSel.value = []; piezaFoco.value = null; }
    loteParadaActiva.value = parada.parada_id;
    // Primera entrega de la parada: la cantidad ya está decidida -- son las prendas
    // que este lote declaró al dividir la Solicitud de Material. Se prellena en vez
    // de pedirla otra vez. En las entregas siguientes se deja vacía a propósito:
    // ahí sí la decide la persona (el tamaño de la tanda que va a mandar).
    if (!parada.sco) {
      const q = prendasDelLoteParaParada(parada);
      if (q > 0) nuevaEntregaForm.cantidad = q;
    }
    if (!parada.po) return;
    advancing.value = true;
    try {
      await selectSub(parada.po);
      if (parada.sco) { scoActivo.value = parada.sco; await selectSco(parada.sco); }
    } finally { advancing.value = false; }
  }
  // Ver/validar la OC de un taller (paso único, no por lote) desde el prerrequisito
  // de "Nuevo lote".
  async function verParadaPo(parada) {
    loteParadaActiva.value = parada.parada_id;
    if (!parada.po) return;
    advancing.value = true;
    try { await selectSub(parada.po); } finally { advancing.value = false; }
  }
  // Cuando NO se quiere dividir la producción en varios lotes explícitos, este
  // paso debe sentirse tan "normal" como cualquier otro -- no debe hacer falta ir
  // clic por clic creando y validando cada OC de subcontratación (maquila) antes
  // de poder producir. Por eso, al abrir "Nuevo lote", si todavía no existen esas
  // OC raíz se crean solas, y si ya existen pero siguen en borrador se revisan y
  // validan solas -- con las MISMAS funciones de siempre (plan_crear_subcontratacion,
  // marcar_revisado_documento, validar_documento); esto no cambia nada de cómo se
  // arma un lote ni de cómo se reparten las paradas, solo evita la espera manual
  // entre cada paso intermedio. Si alguna no se puede validar sola (por permisos,
  // el rol "Aprobador de Documentos Yelke" es de alguien más), se cae de vuelta al
  // panel manual de esa OC, igual que antes.
  async function abrirNuevoLote() {
    if (nuevoLoteForm.loading) return; // evita reentradas (el watch de abajo puede disparar de nuevo a medias)
    nuevoLoteForm.open = true;
    nuevoLoteForm.schedule_date = "";
    nuevoLoteForm.porProducto = [];
    nuevoLoteForm.loading = true;
    try {
      if (!subOcs.value.length) {
        try {
          await call("costeo_yelke.api.costeo_api.plan_crear_subcontratacion", { plan: planDetail.value.name });
        } catch (e) {
          showToast(e.message || "No se pudieron crear las órdenes de subcontrato", "error");
        }
      }
      const rsub = await call("costeo_yelke.api.costeo_api.get_subcontratos", { plan: planDetail.value.name });
      subOcs.value = rsub.ocs || [];

      for (const po of subOcs.value) {
        if (po.docstatus !== 0) continue;
        try {
          await call("costeo_yelke.api.costeo_api.marcar_revisado_documento", { doctype: "Purchase Order", name: po.name });
        } catch { /* ya revisada, o sin permiso -- se intenta validar de todos modos */ }
        try {
          await call("costeo_yelke.api.costeo_api.validar_documento", { doctype: "Purchase Order", name: po.name });
        } catch (e) {
          showToast(`No se pudo validar ${po.name} automáticamente (${e.message || "revisa permisos"}) -- valídala a mano abajo.`, "error");
        }
      }

      const r = await call("costeo_yelke.api.costeo_api.get_lotes_produccion", { plan: planDetail.value.name });
      lotesProduccion.value = r.lotes || [];
      loteRefsCosteo.value = r.lote_refs_costeo || [];
      productosCosteo.value = r.productos || [];

      if (productosCosteo.value.every((p) => !p.root_po)) return; // template ofrece "Crear órdenes de subcontrato" a mano
      const pendiente = productosCosteo.value.find((p) => p.root_po && p.root_po_docstatus !== 1);
      if (pendiente) { await loadSub(pendiente.root_po); subSel.value = pendiente.root_po; return; } // respaldo manual (no se pudo validar sola)

      nuevoLoteForm.porProducto = productosCosteo.value.map((p) => ({
        finished_item: p.finished_item,
        item_name: p.item_name || p.finished_item,
        po: p.root_po || null,
        po_docstatus: p.root_po_docstatus ?? null,
        qty: 0, sugerido: 0, saldo: 0, limitadoPorStock: false,
      }));
      // Secuencial (no Promise.all): varios productos pueden compartir la misma OC
      // raíz y sub_qty_disponible crea/borra una SCO borrador contra ella -- dos
      // llamadas en paralelo sobre la misma OC se pisan y una devuelve 0.
      for (const fila of nuevoLoteForm.porProducto) {
        if (!fila.po || fila.po_docstatus !== 1) continue;
        try {
          const rr = await call("costeo_yelke.api.costeo_api.sub_qty_disponible",
            { po: fila.po, producto: fila.finished_item });
          fila.sugerido = rr.sugerido || 0;
          fila.saldo = rr.saldo_pendiente || 0;
          // Prefill con la cantidad que el stock soporta; si no hay material aún
          // (sugerido 0), con el pendiente completo -- abrir el lote no exige stock
          // (el candado vive en la transferencia), solo se avisa del límite.
          fila.qty = rr.sugerido || rr.saldo_pendiente || 0;
          fila.limitadoPorStock = !!rr.limitado_por_stock;
        } catch { /* fila en 0, se captura a mano */ }
      }
    } finally { nuevoLoteForm.loading = false; }
  }
  function cerrarNuevoLote() { nuevoLoteForm.open = false; }
  // Abre el lote COMPLETO: crea y valida la SCO de CADA parada (ver lote_abrir).
  // El material todavía no tiene que existir: lo que exige existencias es "Enviar al
  // taller", no el encargo.
  async function crearNuevoLote() {
    if (!planDetail.value) { showToast("No hay plan de producción", "error"); return; }
    const cantidades = {};
    nuevoLoteForm.porProducto.forEach((f) => {
      if (f.qty > 0) cantidades[f.finished_item] = f.qty;
    });
    if (!Object.keys(cantidades).length) { showToast("Indica la cantidad de al menos un producto", "error"); return; }
    advancing.value = true;
    try {
      const lote_ref = siguienteLoteRef();
      const r = await call("costeo_yelke.api.costeo_api.lote_abrir", {
        plan: planDetail.value.name, lote_ref, cantidades,
        schedule_date: nuevoLoteForm.schedule_date || null,
      });
      cerrarNuevoLote();
      await loadLotesProduccion();
      await seleccionarLote(lote_ref);
      const n = (r.creadas || []).length;
      if ((r.errores || []).length) showToast(`${lote_ref}: ${n} encargo(s) · ${r.errores[0]}`, "error");
      else showToast(`${lote_ref} abierto — ${n} encargo${n === 1 ? "" : "s"} a talleres`);
    } catch (e) { showToast(e.message || "No se pudo abrir el lote", "error"); }
    finally { advancing.value = false; }
  }
  // Un solo paso para "ya le mandé el material al taller": crea y VALIDA la
  // transferencia y deja el recibo en borrador esperando la cantidad real entregada
  // (lo único que el sistema no puede deducir). Sustituye 4 acciones por 1.
  async function enviarMaterialTaller(sco) {
    const name = sco || scoSel.value?.name;
    if (!name) return;
    advancing.value = true;
    try {
      const r = await call("costeo_yelke.api.costeo_api.sub_enviar_material", { sco: name });
      if (subPo.value?.name) await loadFlujo(subPo.value.name);
      await loadLotesProduccion();
      showToast("Material enviado al taller · recibo listo para confirmar cantidad" + _mensajeAjusteExistencia(r));
    } catch (e) {
      showToast(
        /negativ|no.*suficiente|necesar/i.test(e.message || "")
          ? "Falta materia prima en el almacén de origen: recíbela (Recibo de compra) o espera la etapa anterior."
          : e.message || "No se pudo enviar el material",
        "error",
      );
    } finally { advancing.value = false; }
  }
  // Genera la OC de materia prima de UN proveedor de un lote (ya dividido al
  // validar la solicitud) -- por su propio botón, junto a los de Solicitud de
  // cotización / Presupuesto, no automáticamente ni junta a otros proveedores.
  // Mensaje corto cuando mr_crear_oc redondeó algún material a paquete completo
  // (Mazo/Gruesa/Pieza...) -- para que el ajuste no sea una sorpresa silenciosa.
  function _mensajeRedondeos(redondeos) {
    const entries = Object.entries(redondeos || {});
    if (!entries.length) return "";
    return " · redondeado a paquete completo: " + entries
      .map(([item, r]) => `${item} a ${r.ajustada} ${r.uom}`)
      .join(", ");
  }
  // Ajuste por existencias propias del último "Generar orden de compra":
  // [{item_code, solicitud, comprar, ya_tienes, uom}]. Se limpia al cambiar de lote.
  const neteoOc = ref([]);

  // ---- Transferencia al taller, vista por MATERIAL -------------------------
  // El documento lleva un renglón por PIEZA que consume el material (ERPNext liga
  // cada uno a su `subcontracted_item` para llevar la cuenta de lo entregado y
  // consumido, así que no se pueden fusionar en el documento). Pero lo que de
  // verdad se le entrega al taller es un montón por material, así que la pantalla
  // muestra uno por material y los cambios se reparten hacia abajo.
  const transAgrupado = computed(() => {
    const g = new Map();
    for (const it of transDoc.value?.items || []) {
      const prev = g.get(it.item_code);
      if (prev) {
        prev.qty += Number(it.qty) || 0;
        prev.ya_en_taller += Number(it.ya_en_taller) || 0;
        if (prev.s_warehouse !== it.s_warehouse) prev.s_warehouse = "";
        if (it.available !== null && it.available !== undefined) {
          prev.available = prev.available === null ? it.available
            : Math.min(prev.available, it.available);
        }
        prev.filas.push(it);
      } else {
        g.set(it.item_code, {
          item_code: it.item_code, item_name: it.item_name, uom: it.uom,
          qty: Number(it.qty) || 0, available: it.available ?? null,
          ya_en_taller: Number(it.ya_en_taller) || 0,
          s_warehouse: it.s_warehouse, filas: [it],
        });
      }
    }
    return [...g.values()].map((x) => ({ ...x, qty: Math.round(x.qty * 1e6) / 1e6 }));
  });

  // Cambiar el total de un material lo reparte entre sus renglones en la misma
  // proporción que traían -- esa proporción es cuánto consume cada pieza, y hay
  // que conservarla o la conciliación por pieza de ERPNext deja de cuadrar. El
  // residuo del redondeo se carga al renglón más grande para que la suma dé exacta.
  function cambiarCantidadMaterial(grupo, nuevoTotal) {
    const total = Number(nuevoTotal);
    if (!Number.isFinite(total) || total < 0) return;
    const filas = grupo.filas;
    const actual = filas.reduce((a, f) => a + (Number(f.qty) || 0), 0);
    if (!filas.length) return;
    if (actual <= 0) { filas[0].qty = Math.round(total * 1e6) / 1e6; return; }
    let acum = 0;
    const mayor = filas.reduce((a, b) => ((Number(b.qty) || 0) > (Number(a.qty) || 0) ? b : a));
    for (const f of filas) {
      if (f === mayor) continue;
      const v = Math.round(((Number(f.qty) || 0) * total / actual) * 1e6) / 1e6;
      f.qty = v; acum += v;
    }
    mayor.qty = Math.round((total - acum) * 1e6) / 1e6;
  }

  // El almacén de origen se fija por material, no por pieza: todas las filas del
  // grupo salen del mismo lugar. Devuelve la primera fila para que la pantalla
  // refresque la existencia (ese cálculo vive allá, junto al resto de la vista).
  function cambiarAlmacenMaterial(grupo, warehouse) {
    for (const f of grupo.filas) f.s_warehouse = warehouse;
    return grupo.filas[0];
  }

  async function generarOcLote(lote, supplier) {
    if (!lote?.material_mr) return;
    advancing.value = true;
    try {
      const r = await call("costeo_yelke.api.costeo_api.mr_generar_oc_lote", {
        mr: lote.material_mr, lote_ref: lote.lote_ref, supplier: supplier || null,
      });
      await loadLotesProduccion();
      const po = (r.purchase_orders || [])[0];
      if (po) { mrDocTab.value = "oc"; ocSelected.value = po; await loadDocCompra("Purchase Order", po); }
      // Lo que se descontó por existencias propias queda visible como aviso: la OC
      // está en borrador y la cantidad es editable por si el remanente no sirve.
      neteoOc.value = r.neteo || [];
      showToast("Orden de compra generada" + _mensajeRedondeos(r.redondeos));
    } catch (e) { showToast(e.message || "No se pudo generar la orden de compra", "error"); }
    finally { advancing.value = false; }
  }
  // Cantidad a usar cuando se abre la SCO de una parada de un lote que nació del
  // lado de materia prima -- ahí la parada no trae cantidad, hay que pedirla; se
  // sugiere según el stock real (mismo cálculo que "Nuevo lote").
  const primeraEtapaQty = ref(0);
  const primeraEtapaLoading = ref(false);
  const primeraEtapaLimitado = ref(false);
  async function sugerirPrimeraEtapaQty(parada) {
    primeraEtapaQty.value = 0;
    primeraEtapaLimitado.value = false;
    if (!parada?.po || parada.po_docstatus !== 1) return;
    primeraEtapaLoading.value = true;
    try {
      const r = await call("costeo_yelke.api.costeo_api.sub_qty_disponible", { po: parada.po });
      primeraEtapaQty.value = r.sugerido || 0;
      primeraEtapaLimitado.value = !!r.limitado_por_stock;
    } catch { /* se queda en 0 */ }
    finally { primeraEtapaLoading.value = false; }
  }
  // Crea y valida la SCO de UNA parada que aún no la tiene -- con la cantidad de
  // cada producto de la parada (o la del lote, o `qtyOverride` si el lote nació de
  // materia prima y no trae cantidad).
  async function abrirParada(qtyOverride) {
    const parada = paradaActiva.value;
    const lote = loteActivo.value;
    if (!parada || !lote) return;
    if (!parada.po) { showToast("La orden de compra de este taller aún no está validada", "error"); return; }
    const cantidades = {};
    if (qtyOverride != null && qtyOverride > 0) {
      parada.productos.forEach((pp) => { cantidades[pp.finished_item] = qtyOverride; });
    } else {
      parada.productos.forEach((pp) => { if (pp.qty > 0) cantidades[pp.finished_item] = pp.qty; });
      if (!Object.keys(cantidades).length) {
        (lote.productos || []).forEach((pp) => { if (pp.qty > 0) cantidades[pp.finished_item] = pp.qty; });
      }
    }
    if (!Object.keys(cantidades).length) { showToast("Indica la cantidad", "error"); return; }
    advancing.value = true;
    try {
      const r = await call("costeo_yelke.api.costeo_api.sub_crear_sco", {
        po: parada.po, cantidades, fg_items: parada.fg_items, validar_stock: false,
        schedule_date: lote.schedule_date || null, lote_ref: lote.lote_ref,
      });
      await call("costeo_yelke.api.costeo_api.sub_validar_sco", { sco: r.sco });
      await loadLotesProduccion();
      const p2 = loteActivo.value?.paradas.find((x) => x.parada_id === parada.parada_id);
      if (p2) await seleccionarParada(p2);
      showToast(`${parada.titulo} encargado a ${parada.supplier}`);
    } catch (e) { showToast(e.message || "No se pudo crear el encargo", "error"); }
    finally { advancing.value = false; }
  }

  // Una entrega MÁS sobre una parada que ya tiene al menos una (ver
  // parada_registrar_entrega) -- para cuando el taller entrega el trabajo en
  // varias tandas ("olas") de un sub-ensamblaje físico distinto (puños,
  // mangas...) que el costeo declaró (Flujo de Producción · "Sub-ensamblajes")
  // o, si no declaró ninguno, con solo una referencia de texto libre. Crea su
  // PROPIA Subcontracting Order -- no toca las anteriores.
  const nuevaEntregaForm = reactive({ open: false, cantidad: null, sub_ensamblaje: "", referencia: "", loading: false });

  // ---- Ramas por pieza -----------------------------------------------------
  // Piezas SELECCIONADAS para el próximo encargo. Es una lista porque un taller
  // puede recibir varias de un jalón (las dos mangas hoy, el frente cuando vuelva
  // de reflejante) -- antes solo se podía encargar una por vez.
  const piezasSel = ref([]);

  // Estado de cada pieza EN una parada concreta, sacado de las ramas del lote.
  function piezasDeParada(paradaId) {
    const out = [];
    for (const r of loteActivo.value?.ramas || []) {
      const paso = (r.pasos || []).find((p) => p.parada_id === paradaId);
      if (paso) out.push({ nombre: r.pieza, por_prenda: r.por_prenda, ...paso });
    }
    return out;
  }
  // Las que se pueden encargar ahora mismo en esa parada.
  function piezasListas(paradaId) {
    return piezasDeParada(paradaId).filter((p) => p.estado === "listo");
  }
  function togglePiezaSel(nombre) {
    const i = piezasSel.value.indexOf(nombre);
    if (i >= 0) piezasSel.value.splice(i, 1);
    else piezasSel.value.push(nombre);
  }
  // Pieza sobre la que se hizo clic. Se guarda aparte de `piezasSel` para poder
  // resaltar también un paso que NO se puede encargar (uno ya recibido, o uno
  // bloqueado): se consulta igual, aunque no entre en la selección.
  const piezaFoco = ref(null);

  // Entrar a un paso desde su rama: selecciona la parada y deja marcada esa pieza.
  // Marca SOLO la que se pulsó -- varias piezas comparten proveedor y parada, y
  // resaltar por parada pintaba todas las de ese taller de golpe.
  async function irAPasoDePieza(paso, pieza) {
    const parada = (loteActivo.value?.paradas || []).find((x) => x.parada_id === paso.parada_id);
    if (!parada) return;
    piezaFoco.value = pieza;
    await seleccionarParada(parada);
    piezasSel.value = paso.estado === "listo" && pieza ? [pieza] : [];
  }

  // ¿Este paso va resaltado? Solo si es de la parada abierta Y su pieza está
  // seleccionada (o es la que se pulsó, cuando no hay nada seleccionable).
  function pasoSeleccionado(paso, pieza) {
    if (loteParadaActiva.value !== paso.parada_id) return false;
    if (piezasSel.value.length) return piezasSel.value.includes(pieza);
    return piezaFoco.value === pieza;
  }

  // ---- Matriz pieza × etapa ------------------------------------------------
  // La selección es por CELDA y puede cruzar etapas y talleres: marcas las dos
  // mangas del bordado y los puños del reflejante, y salen dos órdenes, una por
  // taller. `celdasSel` guarda "pieza|parada_id".
  const celdasSel = ref([]);
  const celdaKey = (pieza, paradaId) => `${pieza}|${paradaId}`;
  const celdaSeleccionada = (pieza, paradaId) => celdasSel.value.includes(celdaKey(pieza, paradaId));

  function toggleCelda(pieza, paradaId) {
    const k = celdaKey(pieza, paradaId);
    const i = celdasSel.value.indexOf(k);
    if (i >= 0) celdasSel.value.splice(i, 1);
    else celdasSel.value.push(k);
  }
  function limpiarCeldas() { celdasSel.value = []; }
  /** Suelta las celdas que ya no se pueden encargar (se encargaron, o su etapa
   *  anterior cambió). Se llama después de recargar los lotes: si no, se quedaban
   *  pintadas como seleccionadas aunque ya no cuenten para la orden. */
  function podarCeldasSel() {
    celdasSel.value = celdasSel.value.filter((k) => {
      const i = k.lastIndexOf("|");
      const pieza = k.slice(0, i), paradaId = k.slice(i + 1);
      const rama = (loteActivo.value?.ramas || []).find((r) => r.pieza === pieza);
      const celda = rama && celdaDe(rama, paradaId);
      return !!celda && celda.estado === "listo";
    });
  }

  // La celda de una pieza en una etapa, o null si esa pieza se brinca la etapa.
  function celdaDe(rama, paradaId) {
    return (rama.pasos || []).find((p) => p.parada_id === paradaId) || null;
  }
  // "Seleccionar listas" de una columna: marca (o desmarca) sus celdas listas.
  function toggleColumna(etapa) {
    const listas = (loteActivo.value?.ramas || [])
      .map((r) => celdaDe(r, etapa.parada_id) && celdaDe(r, etapa.parada_id).estado === "listo" ? r.pieza : null)
      .filter(Boolean);
    const todas = listas.length > 0 && listas.every((pz) => celdaSeleccionada(pz, etapa.parada_id));
    for (const pz of listas) {
      const k = celdaKey(pz, etapa.parada_id);
      const i = celdasSel.value.indexOf(k);
      if (todas && i >= 0) celdasSel.value.splice(i, 1);
      else if (!todas && i < 0) celdasSel.value.push(k);
    }
  }
  function columnaTodaSel(etapa) {
    const listas = (loteActivo.value?.ramas || [])
      .filter((r) => { const c = celdaDe(r, etapa.parada_id); return c && c.estado === "listo"; });
    return listas.length > 0 && listas.every((r) => celdaSeleccionada(r.pieza, etapa.parada_id));
  }

  // Lo seleccionado, agrupado por TALLER: una orden por proveedor.
  const gruposSel = computed(() => {
    const porParada = new Map();
    for (const k of celdasSel.value) {
      const i = k.lastIndexOf("|");
      const pieza = k.slice(0, i), paradaId = k.slice(i + 1);
      const rama = (loteActivo.value?.ramas || []).find((r) => r.pieza === pieza);
      const etapa = (loteActivo.value?.rama_etapas || []).find((e) => e.parada_id === paradaId);
      const celda = rama && celdaDe(rama, paradaId);
      if (!rama || !etapa || !celda) continue;
      // Solo entran las LISTAS. La selección sobrevive a una recarga, así que una
      // celda marcada puede haberse encargado en el intento anterior (o por otra
      // pestaña): si se colara aquí saldría un SEGUNDO encargo del mismo trabajo.
      if (celda.estado !== "listo") continue;
      const g = porParada.get(paradaId) || {
        parada_id: paradaId, titulo: etapa.titulo, supplier: etapa.supplier,
        piezas: [], prendas: prendasDelLote(),
      };
      g.piezas.push(rama.por_prenda > 1 ? `${pieza} ×${rama.por_prenda}` : pieza);
      g.nombres = (g.nombres || []).concat([pieza]);
      porParada.set(paradaId, g);
    }
    return [...porParada.values()];
  });

  function prendasDelLote() {
    return (loteActivo.value?.productos || []).reduce((a, p) => a + (Number(p.qty) || 0), 0);
  }

  // Crea una orden POR TALLER con las piezas marcadas de ese taller.
  async function crearOrdenesSeleccion() {
    const grupos = gruposSel.value;
    if (!grupos.length || !loteActivo.value) return;
    advancing.value = true;
    const hechas = [];
    try {
      for (const g of grupos) {
        // Secuencial a propósito: cada llamada valida saldo contra ERPNext, y si
        // una falla hay que poder decir exactamente cuáles sí se crearon.
        await call("costeo_yelke.api.costeo_api.parada_registrar_entrega", {
          plan: planDetail.value.name, lote_ref: loteActivo.value.lote_ref,
          parada_id: g.parada_id, cantidad: g.prendas,
          sub_ensamblaje: JSON.stringify(g.nombres),
        });
        hechas.push(g.titulo);
      }
      limpiarCeldas();
      await loadLotesProduccion();
      if (subPo.value?.name) await loadFlujo(subPo.value.name);
      showToast(hechas.length > 1
        ? `Se generaron ${hechas.length} órdenes, una por taller · sigue enviar material`
        : "Orden de subcontratación generada · sigue enviar material");
    } catch (e) {
      await loadLotesProduccion();
      // Las que sí salieron ya no están listas: se sueltan para que un segundo
      // intento no las vuelva a encargar.
      podarCeldasSel();
      showToast(hechas.length
        ? `Se crearon ${hechas.length} (${hechas.join(", ")}) y falló la siguiente: ${e.message}`
        : (e.message || "No se pudieron crear las órdenes"), "error");
    } finally { advancing.value = false; }
  }

  // Prendas que este lote declaró para los productos que pasan por esta parada.
  // Sale de lo capturado al dividir la Solicitud de Material (Costeo Lote), no de
  // la orden de compra: la OC cubre TODO el costeo y se va consumiendo lote a lote.
  function prendasDelLoteParaParada(parada) {
    const lote = loteActivo.value;
    if (!lote || !parada) return 0;
    const porProducto = Object.fromEntries(
      (lote.productos || []).map((p) => [p.finished_item, Number(p.qty) || 0]));
    return (parada.productos || []).reduce(
      (acc, p) => acc + (porProducto[p.finished_item] || 0), 0);
  }
  function abrirNuevaEntrega() {
    Object.assign(nuevaEntregaForm, { open: true, cantidad: null, sub_ensamblaje: "", referencia: "", loading: false });
  }
  function cerrarNuevaEntrega() {
    nuevaEntregaForm.open = false;
  }
  async function confirmarNuevaEntrega() {
    const parada = paradaActiva.value;
    const lote = loteActivo.value;
    if (!parada || !lote) return;
    if (!nuevaEntregaForm.cantidad || nuevaEntregaForm.cantidad <= 0) {
      showToast("Indica la cantidad de esta entrega", "error");
      return;
    }
    // Sin pieza elegida la entrega cubre TODAS las de la parada, que es lo normal
    // (del mismo tendido de tela salen las seis piezas del corte). Antes esto se
    // bloqueaba porque una entrega sin nombre no marcaba nada en el checklist; eso
    // ya no pasa: el checklist se mide sobre los renglones reales de la SCO, no
    // sobre el texto de la referencia (ver get_lotes_produccion).
    nuevaEntregaForm.loading = true;
    try {
      await call("costeo_yelke.api.costeo_api.parada_registrar_entrega", {
        plan: planDetail.value.name, lote_ref: lote.lote_ref, parada_id: parada.parada_id,
        cantidad: nuevaEntregaForm.cantidad,
        // Lista: el taller puede recibir varias piezas en el mismo encargo.
        sub_ensamblaje: piezasSel.value.length ? JSON.stringify(piezasSel.value) : null,
        referencia: piezasSel.value.length ? null : (nuevaEntregaForm.referencia || null),
      });
      cerrarNuevaEntrega();
      piezasSel.value = [];
      await loadLotesProduccion();
      const p2 = loteActivo.value?.paradas.find((x) => x.parada_id === parada.parada_id);
      if (p2) await seleccionarParada(p2);
      showToast("Encargo registrado");
    } catch (e) { showToast(e.message || "No se pudo registrar la entrega", "error"); }
    finally { nuevaEntregaForm.loading = false; }
  }
  // Clic en una entrega ya registrada: carga esa Subcontracting Order
  // específica en el mismo detalle de siempre (Orden de subcontratación /
  // Transferencia / Recibo) -- reusa selectSco tal cual, que ya resuelve
  // cualquier SCO de la OC activa, no solo la primera. `subStepOpen` vive en
  // la página (no en este composable), así que el clic real lo pone en "sco"
  // aparte -- ver template.
  async function verEntrega(entrega) {
    await selectSco(entrega.sco);
  }

  // ── Progreso general ──
  const prodComplete = reactive({ complete: false, total: 0, recibidas: 0, lotes_total: 0, lotes_recibidos: 0, pct_recibido: 0 });
  async function loadProdComplete(costeoName, salesOrder = null) {
    if (!costeoName) return;
    try {
      const r = await call("costeo_yelke.api.costeo_api.produccion_completa", { costeo: costeoName, sales_order: salesOrder || null });
      Object.assign(prodComplete, {
        complete: !!r.complete, total: r.total || 0, recibidas: r.recibidas || 0,
        lotes_total: r.lotes_total || 0, lotes_recibidos: r.lotes_recibidos || 0,
        pct_recibido: r.pct_recibido || 0,
      });
    } catch { /* ignore */ }
  }

  // Porcentaje de materia prima recibida -- ya viene calculado del backend
  // (get_recibos) contra el total de TODA la Solicitud de Material (los 3 lotes,
  // aunque sus OC individuales todavía no existan). Antes se ponderaba solo contra
  // las OC que YA existían (reciboOcs) -- en cuanto se recibía la primera OC del
  // lote 1, la barra saltaba a ~100% aunque faltaran 2 lotes más sin generar
  // siquiera su OC (bug real, reportado en vivo).
  const materiaPrimaPct = computed(() => {
    if (pctRecibidoMateriaPrima.value !== null) return pctRecibidoMateriaPrima.value;
    return mrValidated.value ? 0 : null;
  });
  // Porcentaje de subcontratación (maquila) recibida: igual que materiaPrimaPct,
  // ponderado por el IMPORTE de cada OC de etapa -- así un producto con 2+ etapas
  // subcontratadas no salta a 100% en cuanto se recibe la ÚLTIMA si las etapas
  // anteriores representan la mayor parte del costo, y sube lote a lote conforme
  // se reciben (escalonado), no de golpe al completar TODOS los lotes de una OC.
  const subcontratacionPct = computed(() => {
    if (!subOcs.value.length) return null;
    return Math.round(prodComplete.pct_recibido || 0);
  });

  // Lotes de compra de materia prima para las LoteCard: une las OC en borrador
  // (mrResults.ocs, recién creadas) con las ya validadas (reciboOcs, que ya traen
  // proveedor/recibos) en una sola lista.
  const mpLotes = computed(() => {
    const map = {};
    for (const name of (mrResults.value.ocs || [])) {
      map[name] = { name, docstatus: 0, supplier_name: "", per_received: 0, receipts: [] };
    }
    for (const oc of (reciboOcs.value || [])) {
      map[oc.name] = { ...oc, docstatus: 1 };
    }
    return Object.values(map);
  });

  return {
    // constantes
    OM_CAB, OM_DAMA, DOC_COMPRA,
    // plan
    planDetail, planWh, hasPlan, planValidated, downstream,
    loadPlan, obtenerMateriasPrimas, guardarPlan, validarPlan, crearOrdenesTrabajo,
    // materia prima
    mrDetail, mrItems, mrSchedule, mrResults, mrDocTab, mrValidated, anyOcValidated,
    rfqSelected, sqSelected,
    docCompra, docCompraItems, docCompraForm, docCompraValidated, docCompraHasRate, ocSelected,
    loteOc, abrirLoteOc, cerrarLoteOc, crearOc,
    mrLotes, addMrLote, removeMrLote, repartirMrLotesIgual, mrLotePendiente,
    mrLotesPreview, actualizarPreviewLotes, mrLoteProductoExcedido, mrLoteProductoIncompleto, mrLotesInvalidos,
    loadSolicitud, crearSolicitud, guardarSolicitud, validarSolicitud,
    loadDocCompra, selectOC, selectOcLote, selectRfq, selectSq, guardarDocCompra, validarDocCompra, revisarDocCompra, jalarPreciosOC,
    // doble validación (Enviar -> Revisor -> Aprobador) -- hoy solo la Orden de Compra
    permisosValidacion, loadPermisosValidacion,
    // recibo de compra
    reciboOcs, reciboOcSel, reciboPr, reciboItems, reciboForm, reciboValidated,
    loadRecibos, selectReciboOc, selectReciboLote, loadRecibo, crearRecibo, guardarRecibo, validarRecibo,
    // subcontratación
    subOcs, subSel, subPo, subItems, subForm, subValidated, subHasRate, subDone,
    loadSubcontratos, crearSubcontratos, selectSub, loadSub, guardarSub, validarSub, revisarSub,
    flujo, scoActivo, scoSel, scoValidated, materialesSco, piezasSco, serviciosSco, importeSco, scoForm, scoCostos,
    loadFlujo, selectSco, guardarSco, validarSco, addCosto, removeCosto,
    transDoc, transForm, transCostos, transValidated, transferDone, loadTrans, transferirMaterial, guardarTrans, validarTransferencia, enviarMaterialTaller,
    talleresSaldo, loadSaldoTalleres, devolverMaterialTaller,
    addCostoTrans, removeCostoTrans,
    scr, scrForm, scrCostos, scrValidated, crearReciboSub, loadScr, guardarScr, validarScr,
    addCostoScr, removeCostoScr,
    // lotes de producción (por paradas)
    lotesProduccion, productosCosteo, loteActivoRef, loteParadaActiva, nuevoLoteForm,
    loteActivo, paradaActiva, tracksLote, paradaEstado,
    loadLotesProduccion, seleccionarLote, seleccionarParada, verParadaPo,
    abrirNuevoLote, cerrarNuevoLote, crearNuevoLote, abrirParada, siguienteParadaPendiente, generarOcLote, neteoOc,
    siguienteLoteRef, loteRefsCosteo,
    transAgrupado, cambiarCantidadMaterial, cambiarAlmacenMaterial,
    nuevaEntregaForm, abrirNuevaEntrega, cerrarNuevaEntrega, confirmarNuevaEntrega, verEntrega,
    piezasSel, piezasDeParada, piezasListas, togglePiezaSel, irAPasoDePieza,
    piezaFoco, pasoSeleccionado,
    celdasSel, celdaSeleccionada, toggleCelda, limpiarCeldas, celdaDe,
    toggleColumna, columnaTodaSel, gruposSel, crearOrdenesSeleccion, prendasDelLote,
    primeraEtapaQty, primeraEtapaLoading, primeraEtapaLimitado, sugerirPrimeraEtapaQty,
    crearRfqLote, crearSqLote,
    omGeneral, omCab, omDama, omProc, omTablas, omArchivos, omUploading, omEditable,
    addProceso, removeProceso, addTabla, removeTabla, addColumna, removeColumna, addFila, removeFila,
    medidasTemplates, addTablaPlantilla, tablasDePlantilla, omDeOc,
    tallaTotal, onOmFile, removeArchivo, loadOm,
    // progreso
    prodComplete, loadProdComplete, materiaPrimaPct, subcontratacionPct, mpLotes,
  };
}
