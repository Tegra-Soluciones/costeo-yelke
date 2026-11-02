<template>
  <div class="flex flex-col min-h-0">
    <ConfirmDialog
      v-model="confirmDelete.open"
      title="Eliminar Costeo"
      :message="`¿Seguro que deseas eliminar ${docName}? Esta acción no se puede deshacer.`"
      confirm-label="Eliminar" :loading="confirmDelete.loading"
      @confirm="doDelete" @cancel="confirmDelete.open = false"
    />
    <ConfirmDialog
      v-model="confirmFlujoDlg.open" variant="warning"
      title="¿Confirmar el flujo de producción?"
      message="Revisa bien antes de continuar: se crean las BOMs, los Subcontracting BOMs y el plan de producción con este flujo, y después ya no se podrá editar (solo revirtiéndolo)."
      confirm-label="Sí, confirmar y pasar a producción"
      @confirm="aceptarConfirmarFlujo" @cancel="confirmFlujoDlg.open = false"
    >
      <div v-if="resumenConfirmarFlujo.length" class="mt-3 max-h-72 overflow-y-auto space-y-2">
        <div v-for="r in resumenConfirmarFlujo" :key="r.producto" class="rounded-lg border border-gray-200 px-3 py-2 text-[12px]">
          <p class="font-semibold text-gray-900 truncate">{{ r.producto }}</p>
          <p class="text-gray-500">{{ r.pasos }} {{ r.pasos === 1 ? "paso" : "pasos" }}<template v-if="r.piezas"> · {{ r.piezas }} piezas · se unen en {{ r.union || "el paso final" }}</template></p>
          <ul v-if="r.avisos.length" class="mt-1 space-y-0.5 text-amber-700">
            <li v-for="(a, i) in r.avisos" :key="i">• {{ a }}</li>
          </ul>
        </div>
      </div>
    </ConfirmDialog>
    <ConfirmDialog
      v-model="confirmRevertir.open"
      title="¿Revertir el flujo de producción?"
      :message="`Se cancelan y borran las BOMs, los Subcontracting BOMs y el plan de producción de ${docName}, y el proyecto regresa a Flujo de Producción para corregirlo. Después tendrás que volver a confirmarlo. Solo se puede si todavía no hay solicitudes de material, órdenes de compra ni órdenes de trabajo.`"
      confirm-label="Sí, revertir" :loading="confirmRevertir.loading"
      @confirm="revertirFlujo" @cancel="confirmRevertir.open = false"
    />
    <ConfirmDialog
      v-model="confirmDeshacerEncargo.open" variant="warning"
      title="¿Deshacer este encargo?"
      :message="`Se cancela el encargo ${confirmDeshacerEncargo.sco} a ${confirmDeshacerEncargo.supplier || 'este taller'}${confirmDeshacerEncargo.enviado ? ' y su envío de material (el material regresa a tu almacén)' : ''}. ${confirmDeshacerEncargo.piezas.length > 1 ? `Van juntas en él: ${confirmDeshacerEncargo.piezas.join(', ')}; todas` : 'Sus piezas'} vuelven a quedar «Por encargar» en el tablero. El encargo cancelado queda en el historial.`"
      confirm-label="Sí, deshacer" :loading="confirmDeshacerEncargo.loading"
      @confirm="deshacerEncargo" @cancel="confirmDeshacerEncargo.open = false"
    />
    <ConfirmDialog
      v-model="confirmCancel.open"
      :title="headerDoc && headerDoc.isCosteo ? 'Cancelar Costeo' : `Cancelar ${headerDoc?.doctype || ''}`"
      :message="`¿Cancelar la validación de ${headerDoc?.name || docName}?${headerDoc && headerDoc.isCosteo ? ' Después podrás eliminarlo.' : ''}`"
      confirm-label="Cancelar validación" :loading="confirmCancel.loading"
      @confirm="doCancel" @cancel="confirmCancel.open = false"
    />
    <ConfirmDialog
      v-model="confirmDeleteQuot.open"
      title="Eliminar cotización"
      :message="`¿Seguro que deseas eliminar ${confirmDeleteQuot.name}? Esta acción no se puede deshacer.`"
      confirm-label="Eliminar" :loading="confirmDeleteQuot.loading"
      @confirm="doDeleteQuot" @cancel="confirmDeleteQuot.open = false"
    />
    <ConfirmDialog
      v-model="confirmDeleteSO.open"
      title="Eliminar orden de venta"
      :message="`¿Seguro que deseas eliminar ${confirmDeleteSO.name}? Esta acción no se puede deshacer.`"
      confirm-label="Eliminar" :loading="confirmDeleteSO.loading"
      @confirm="doDeleteSO" @cancel="confirmDeleteSO.open = false"
    />

    <!-- Precio de venta escrito dos veces (la primera oculta) -->
    <DialogoPrecio
      :abierto="!!precioEnEdicion" :producto="precioEnEdicion?.finished_item || 'Producto'"
      :actual="precioEnEdicion?.unit_sales_price || 0" @cerrar="precioEnEdicion = null" @confirmar="aplicarPrecio"
    />

    <!-- Imagen del producto: del equipo, pegada o desde un enlace -->
    <DialogoImagen
      :abierto="!!imagenEnEdicion" :producto="imagenEnEdicion?.finished_item || 'Producto nuevo'"
      :actual="imagenEnEdicion?.image || ''" doctype="Costeo" :docname="docName || ''"
      @cerrar="imagenEnEdicion = null" @elegida="aplicarImagen"
    />

    <!-- Modal: materializar producto terminado (al pasar a cotización) -->
    <MaterializeProductModal
      :open="materializeModal.open"
      :finished-item-text="materializeModal.text"
      :suggested-price="materializeModal.suggestedPrice"
      :suggested-description="materializeModal.suggestedDescription"
      :suggested-image="materializeModal.suggestedImage"
      :suggested-code="materializeModal.suggestedCode"
      :es-variante="materializeModal.esVariante"
      :tallas-extra="materializeModal.tallasExtra"
      :solo-tallas="materializeModal.soloTallas"
      :company="form.compania"
      :saving="materializeModal.saving"
      @cancel="cancelMaterialize"
      @confirm="confirmMaterialize"
    />

    <!-- Modal: materializar artículo (material/servicio/subensamblaje) desde el checklist -->
    <MaterializeArticuloModal
      :open="articuloModal.open"
      :row-type="articuloModal.group?.row_type || 'material'"
      :texto="articuloModal.group?.texto || ''"
      :suggested-supplier="articuloModal.group?.supplier || ''"
      :suggested-price="articuloModal.group?.unit_price || 0"
      :suggested-supplier-uom="articuloModal.group?.supplier_uom || ''"
      :suggested-conversion-factor="articuloModal.group?.conversion_factor || 0"
      :suggested-stock-uom="articuloModal.group?.internal_uom || ''"
      :suggested-precio-compra="articuloModal.group?.precio_compra || 0"
      :company="pendientesContext.company"
      :default-warehouse="articuloModal.group?.row_type === 'subensamblaje_etapa' ? pendientesContext.almacen_trabajo_en_proceso : pendientesContext.almacen_materias_primas"
      :saving="articuloModal.saving"
      @cancel="cancelArticuloModal"
      @confirm="confirmArticuloModal"
    />

    <!-- Header -->
    <PageHeader :title="isNew ? 'Nuevo Costeo' : (form.titulo || docName || '…')" :subtitle="headerSubtitle" back>
      <div v-if="headerDoc" class="relative" ref="actionsRef">
        <button class="h-8 w-8 flex items-center justify-center text-ink-muted border border-surface-border rounded-lg hover:bg-surface-raised transition-colors" :class="actionsOpen ? 'bg-surface-raised' : ''" @click.stop="actionsOpen = !actionsOpen" :aria-label="`Acciones de ${headerDoc.doctype}`">
          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="5" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="12" cy="19" r="1.6"/></svg>
        </button>
        <Transition name="panel">
          <div v-if="actionsOpen" class="absolute right-0 top-full mt-1.5 w-52 bg-white border border-surface-border rounded-xl shadow-xl overflow-hidden z-50">
            <p class="px-3 pt-2 pb-1 text-[10.5px] font-semibold uppercase tracking-wide text-ink-xlight">{{ headerDoc.doctype === 'Costeo' ? 'Costeo' : headerDoc.doctype }} · {{ headerDoc.name }}</p>
            <div class="py-1">
              <template v-if="headerDoc.isCosteo">
                <button class="action-item" @click="duplicateDoc">Duplicar</button>
                <button class="action-item" @click="actionsOpen = false; showHistorialModal = true">Ver historial</button>
              </template>
              <button class="action-item" @click="printDoc">Imprimir / PDF</button>
              <button class="action-item" @click="openInDesk">Abrir en Desk</button>
            </div>
            <div class="border-t border-surface-border py-1">
              <button v-if="headerDoc.docstatus === 1" class="action-item text-amber-600 hover:bg-amber-50 hover:text-amber-700" @click="openCancel">Cancelar validación</button>
              <button v-if="headerDoc.isCosteo && headerDoc.docstatus === 1" class="action-item text-brand-600 hover:bg-brand-50 hover:text-brand-700" @click="openRevisionModal">Editar costeo</button>
              <button v-if="headerDoc.isCosteo" class="action-item text-red-500 hover:bg-red-50 hover:text-red-600" @click="openDelete">Eliminar</button>
            </div>
          </div>
        </Transition>
      </div>

      <!-- La del documento del paso (cotización, OV, remisión, factura) o, si el paso
           no tiene uno propio (Producción, Flujo…), la del costeo. -->
      <BotonActividad data-libre
        v-if="!isNew && docName"
        :doctype="headerDoc?.name ? headerDoc.doctype : 'Costeo'" :name="headerDoc?.name || docName"
      />
      <!-- Asignaciones del proyecto (api/encargos.py): quién hace cada paso. -->
      <button
        v-if="!isNew && docName" data-libre type="button"
        class="px-3 py-1.5 border border-gray-200 text-gray-600 text-sm font-medium rounded-md hover:bg-gray-50 flex items-center gap-1.5"
        title="Asignar un paso a alguien y ver las asignaciones del proyecto" @click="abrirEncargos()"
      >
        <Icono nombre="persona" class="w-3.5 h-3.5" :grosor="2" />
        Asignar
        <span v-if="encargosAbiertos" class="min-w-[18px] h-[18px] px-1 rounded-full bg-amber-100 text-amber-800 text-[10.5px] font-bold flex items-center justify-center">{{ encargosAbiertos }}</span>
      </button>

      <span v-if="headerDoc && headerDoc.docstatus === 1" class="h-8 px-3 flex items-center gap-1.5 text-[13px] font-medium text-green-700 bg-green-50 rounded-lg">
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        Validado
      </span>
      <span v-else-if="headerDoc && headerDoc.docstatus === 2" class="h-8 px-3 flex items-center gap-1.5 text-[13px] font-medium text-red-600 bg-red-50 rounded-lg">
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/></svg>
        Cancelado
      </span>

      <button v-if="docState === 0 && (isNew || puedeEditar('costear'))" :disabled="saving" class="h-8 px-3.5 text-[13px] font-medium text-ink border border-surface-border rounded-lg hover:bg-surface-raised transition-colors disabled:opacity-50 flex items-center gap-2" @click="saveDoc">
        <svg v-if="saving" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
        {{ saving ? "Guardando…" : (isNew ? "Guardar Costeo" : "Guardar") }}
      </button>

      <button
        v-if="!isNew && docState === 0 && validaDirecto(docName) && puedeEditar('costear')"
        :disabled="advancing || !puedeValidarCosteo"
        class="h-8 px-3.5 text-[13px] font-semibold text-brand-700 bg-brand-50 rounded-lg hover:bg-brand-100 transition-colors disabled:opacity-50 flex items-center gap-1.5"
        @click="validarCosteo"
        :title="puedeValidarCosteo ? 'Guarda y valida el costeo para poder avanzar' : 'Necesitas el rol \'Aprobador de Documentos Yelke\' para validar'"
      >
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        Validar
      </button>

      <button v-if="!isNew && cta" :disabled="advancing || !canAdvanceCta" class="h-8 px-4 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 transition-colors disabled:opacity-40 flex items-center gap-1.5" :title="canAdvanceCta ? '' : (cta.action === 'ir_preparar_manufactura' ? 'Primero valida la orden de venta' : cta.action === 'enviar' ? 'Se habilita cuando recibas prendas terminadas del último taller (confección)' : 'Completa los pendientes')" @click="advance">
        <svg v-if="advancing" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
        {{ cta.label }}
        <svg v-if="!advancing" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 7l5 5-5 5M6 12h12"/></svg>
      </button>
    </PageHeader>

    <CosteoStepper
      v-if="!isNew && docName" :model-value="docStatus" :active-step="activeStep"
      :vender-listo="soValidated"
      :con-ordenes-venta="related.sales_orders.length > 0"
      :alta-productos-listo="pendientesArticulos.length === 0"
      :flujo-produccion-listo="manufacturaGuardada || hasPlan"
      :permitidos="accesosListos ? pasosPermitidos : null"
      @select="goStep"
    />
    <!-- Sin ninguna etapa asignada en este proyecto (accesos por vista). -->
    <div v-if="!isNew && docName && accesosListos && !pasosPermitidos.length" class="max-w-xl mx-auto mt-16 p-panel p-6 text-center">
      <p class="text-[14px] font-semibold text-ink">No tienes etapas asignadas en este proyecto</p>
      <p class="p-meta mt-1">Pídele a quien administra los accesos que te asigne la etapa en la que trabajas.</p>
    </div>

    <!-- Lo que a esta persona le asignaron en este proyecto. -->
    <div v-if="!isNew && docName && encargos.length" class="mx-5 mt-4">
      <FranjaEncargos :encargos="encargos" @ir="irAMiEncargo" @cambio="cargarEncargos" />
    </div>
    <PanelEncargos
      v-if="!isNew && docName" :abierto="encargosPanel.abierto" :costeo="docName" :titulo="form.titulo || docName"
      :paso-inicial="encargosPanel.paso" :lote-inicial="encargosPanel.lote"
      @cerrar="encargosPanel.abierto = false" @cambio="cargarEncargos"
    />

    <!-- Aprobación del Costeo (api/aprobaciones.py): quien no puede validarlo lo envía. -->
    <div v-if="!isNew && docName && docState === 0" class="mx-5 mt-4">
      <FranjaAprobacion
        doctype="Costeo" :name="docName" :guardar="guardarCosteoParaAprobacion"
        @estado="(s) => (aprobPanel[docName] = s)" @cambio="trasAprobacionCosteo"
      />
    </div>

    <div v-if="docState === 2" class="mx-5 mt-4 bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 flex items-center justify-between gap-3">
      <div class="flex items-center gap-2.5">
        <svg class="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        <p class="text-[13px] text-ink-muted">
          <template v-if="siguienteCosteo">Este costeo fue <span class="font-medium text-ink">reemplazado por una revisión</span> y ya no se puede editar.</template>
          <template v-else>Este costeo está <span class="font-medium text-ink">cancelado</span> y ya no se puede editar.</template>
        </p>
      </div>
      <router-link v-if="siguienteCosteo" :to="{ name: 'CosteoDetail', params: { name: siguienteCosteo } }" class="flex-shrink-0 text-[12.5px] font-semibold text-brand-600 hover:text-brand-700 hover:underline whitespace-nowrap">
        Ir a la revisión →
      </router-link>
    </div>

    <div v-if="docStatus === 'Cancelado' && docState !== 2" class="mx-5 mt-4 bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 flex items-center justify-between gap-3">
      <div class="flex items-center gap-2.5">
        <svg class="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        <p class="text-[13px] text-ink-muted">Este proyecto quedó <span class="font-medium text-ink">cancelado</span> (la cotización se canceló) — usa "Editar Costeo" en la pestaña Cotizar para reactivarlo.</p>
      </div>
    </div>

    <div v-if="loading" class="flex-1 flex items-center justify-center text-ink-light">
      <svg class="w-7 h-7 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
    </div>

    <!-- ══════════ STEP 0 · COSTEAR ══════════ -->
    <!-- Mismo contenido de siempre, con el lenguaje de Producción/Dirección (p-*):
         datos generales en una franja, y cada producto en dos columnas -- a la
         izquierda qué es y cómo se hace (pasos, servicios, materias primas), a la
         derecha cuánto cuesta y en cuánto se vende, fija mientras se baja. -->
    <!-- Sin etapas asignadas: no se pinta ningún paso (el aviso va bajo el stepper). -->
    <div v-else-if="!isNew && docName && accesosListos && !pasosPermitidos.length"></div>
    <div v-else-if="activeStep === 0" class="px-5 lg:px-8 py-6 pb-40" v-solo-lectura="soloLecturaPaso">
      <!-- Solo lectura: el usuario tiene esta etapa en "ver" (accesos por vista). -->
      <p v-if="soloLecturaPaso" class="max-w-5xl mx-auto mb-4 text-[12.5px] text-ink-muted bg-surface-raised rounded-lg px-3 py-2">
        <b class="text-ink">Solo lectura.</b> Puedes consultar esta etapa; la captura la hace quien la tiene asignada.
      </p>
      <fieldset :disabled="!canEditCosteo" class="border-0 p-0 m-0 min-w-0" :class="!canEditCosteo ? 'opacity-70' : ''">
      <div class="max-w-[1320px] mx-auto space-y-6">
        <section class="p-panel">
          <div class="px-5 pt-4"><p class="p-eyebrow">Datos del costeo</p></div>
          <div class="px-5 pt-3 pb-5 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-x-4 gap-y-3.5">
            <div class="md:col-span-2">
              <label class="p-field-label">Título <span class="text-ink-light font-normal">(opcional, para identificarlo más fácil)</span></label>
              <input v-model="form.titulo" v-mayus type="text" class="p-field" placeholder="Ej: Playeras Polo Ferromex 2026" />
            </div>
            <div><label class="p-field-label">Cliente <span class="text-red-400">*</span></label><LinkInput v-model="form.cliente" doctype="Customer" placeholder="Buscar cliente…" :error="!!errors.cliente" /></div>
            <div><label class="p-field-label">Fecha <span class="text-red-400">*</span></label><input v-model="form.fecha" type="date" class="p-field" :class="errors.fecha ? 'border-red-400' : ''" /></div>
            <div><label class="p-field-label">Compañía <span class="text-red-400">*</span></label><LinkInput v-model="form.compania" doctype="Company" placeholder="Compañía…" :error="!!errors.compania" /></div>
            <div class="md:col-span-1 xl:col-span-3 flex items-end pb-2">
              <label class="flex items-center gap-2 text-[13px] text-ink-muted cursor-pointer select-none">
                <input v-model="form.guardar_como_plantilla" type="checkbox" class="w-4 h-4 rounded border-surface-border accent-brand-500" />
                Guardar productos como plantilla al guardar
              </label>
            </div>
          </div>
          <!-- Almacenes y centro de costos: se rellenan solos al elegir la compañía.
               Esta sección solo se muestra cuando get_company_defaults NO logró
               resolver alguno por nombre -- si ya se autocompletaron los 3, se
               mantiene oculta para no meter ruido visual en el flujo normal. -->
          <div v-if="form.compania && faltanAlmacenes" class="px-5 py-4 border-t border-surface-border">
            <p class="text-[12px] text-amber-800 mb-3 flex items-start gap-1.5">
              <Icono nombre="alerta" class="w-4 h-4 flex-shrink-0 mt-px" />
              No encontramos los almacenes de esta compañía por su nombre — elígelos aquí para poder guardar.
            </p>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label class="p-field-label">Almacén de materia prima <span class="text-red-400">*</span></label>
                <LinkInput v-model="form.almacen_materias_primas" doctype="Warehouse" :filters="warehouseFilters" placeholder="Almacén…" :error="!!errors.almacen_materias_primas" />
              </div>
              <div>
                <label class="p-field-label">Almacén de trabajo en proceso <span class="text-red-400">*</span></label>
                <LinkInput v-model="form.almacen_trabajo_en_proceso" doctype="Warehouse" :filters="warehouseFilters" placeholder="Almacén…" :error="!!errors.almacen_trabajo_en_proceso" />
              </div>
              <div>
                <label class="p-field-label">Centro de costos <span class="text-red-400">*</span></label>
                <LinkInput v-model="form.centro_de_costos" doctype="Cost Center" :filters="costCenterFilters" placeholder="Centro de costos…" :error="!!errors.centro_de_costos" />
              </div>
            </div>
          </div>
          <!-- Configuración contable incompleta de la compañía (ver compania_setup.diagnostico_compania):
               solo avisa, no bloquea -- con esto el inventario/maquila no se reflejan bien en contabilidad. -->
          <div v-if="form.compania && diagCompania.faltantes.length" class="px-5 py-3 border-t border-surface-border bg-amber-50/60 rounded-b-xl text-[12px] text-amber-900">
            <p class="font-semibold mb-0.5 flex items-center gap-1.5"><Icono nombre="alerta" class="w-3.5 h-3.5" />La configuración contable de {{ form.compania }} está incompleta</p>
            <ul class="list-disc pl-9 space-y-0.5">
              <li v-for="f in diagCompania.faltantes" :key="f">{{ f }}</li>
            </ul>
          </div>
        </section>

        <section>
          <div class="flex items-end justify-between gap-3 mb-3">
            <div>
              <p class="p-eyebrow">Productos a costear</p>
              <p v-if="productos.length" class="p-meta mt-0.5">{{ productos.length }} {{ productos.length === 1 ? "producto" : "productos" }} · precios sin IVA</p>
            </div>
            <button type="button" class="p-btn-secondary h-8 px-3" @click="addProducto"><Icono nombre="mas" class="w-3.5 h-3.5" :grosor="2.2" />Agregar producto</button>
          </div>

          <div v-if="!productos.length" class="p-panel py-12 flex flex-col items-center gap-2 text-ink-light">
            <Icono nombre="paquete" class="w-8 h-8 text-ink-xlight" :grosor="1.3" />
            <p class="text-[13px]">Agrega al menos un producto terminado</p>
            <button type="button" class="add-link" @click="addProducto"><Icono nombre="mas" class="w-3.5 h-3.5" :grosor="2.2" />Agregar producto</button>
          </div>

          <div v-else class="space-y-3">
            <div v-for="prod in productosApilados" :key="prod._tid" class="p-panel" :class="{ 'ml-8': prod.variante_talla_de }">
              <!-- Renglón del producto: siempre visible, abre/cierra el detalle -->
              <div class="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-zinc-50 rounded-xl transition-colors group" :class="expandedTids.has(prod._tid) ? 'rounded-b-none' : ''" @click="toggleProduct(prod._tid)">
                <svg class="w-4 h-4 text-ink-light flex-shrink-0 transition-transform" :class="expandedTids.has(prod._tid) ? 'rotate-90' : ''" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
                <img v-if="prod.image" :src="prod.image" class="w-10 h-10 rounded-lg object-cover border border-surface-border flex-shrink-0" alt="" />
                <div v-else class="w-10 h-10 rounded-lg bg-surface-raised flex items-center justify-center flex-shrink-0">
                  <svg class="w-4 h-4 text-ink-xlight" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.6"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                </div>
                <div class="flex-1 min-w-0">
                  <p class="flex items-center gap-2 min-w-0">
                    <span v-if="prod.finished_item" class="font-semibold text-[14px] text-ink truncate">{{ prod.finished_item }}</span>
                    <span v-else class="text-[14px] text-ink-light italic">Sin producto</span>
                  </p>
                  <p v-if="prod.variante_talla_de" class="mt-1"><span class="p-pill-now h-5 text-[11px]">Variante de talla de {{ prod.variante_talla_de }}<template v-if="prod.talla_grupo_label"> · {{ prod.talla_grupo_label }}</template></span></p>
                </div>
                <div class="hidden sm:flex items-center gap-6 text-right">
                  <!-- Sin cantidad (p. ej. una talla extra que el cliente aún no define) no se muestra nada. -->
                  <div v-if="prod.qty > 0">
                    <p class="text-[10.5px] text-ink-light">Cantidad</p>
                    <p class="text-[13px] font-medium text-ink tabular-nums">{{ Number(prod.qty).toLocaleString("es-MX") }} pzas</p>
                  </div>
                  <div>
                    <p class="text-[10.5px] text-ink-light">Costo unitario</p>
                    <p class="text-[13px] font-medium text-ink tabular-nums">{{ fmtC(prod.total_unit_cost) }}</p>
                  </div>
                  <div>
                    <p class="text-[10.5px] text-ink-light">Venta total</p>
                    <p class="text-[14px] font-semibold text-ink tabular-nums">{{ fmtC(prod.total_sales_price) }}</p>
                  </div>
                </div>
                <button type="button" class="opacity-0 group-hover:opacity-100 w-7 h-7 flex items-center justify-center rounded-md hover:bg-red-50 hover:text-red-500 text-ink-xlight transition-all flex-shrink-0" title="Eliminar" @click.stop="removeProducto(productos.indexOf(prod))">
                  <Icono nombre="x" class="w-3.5 h-3.5" :grosor="2" />
                </button>
              </div>

              <div v-if="expandedTids.has(prod._tid)" class="border-t border-surface-border p-5 space-y-6">
                  <div class="flex gap-4 items-start">
                    <div class="w-28 h-28 flex-shrink-0 rounded-xl border border-surface-border overflow-hidden bg-surface-raised relative group/img" :class="canEditCosteo ? 'cursor-pointer' : 'cursor-default'" title="Cambiar imagen del producto (archivo, pegar o enlace)" @click="pickImage(prod)">
                      <img v-if="prod.image" :src="prod.image" class="w-full h-full object-cover" alt="" />
                      <div v-else class="w-full h-full flex flex-col items-center justify-center gap-1 text-ink-xlight">
                        <svg class="w-9 h-9" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.4"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                        <span class="text-[10.5px]">Imagen</span>
                      </div>
                      <div class="absolute inset-0 bg-black/45 opacity-0 group-hover/img:opacity-100 transition-opacity flex items-center justify-center">
                        <svg class="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/><path stroke-linecap="round" stroke-linejoin="round" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                      </div>
                    </div>
                    <div class="flex-1 min-w-0 grid grid-cols-3 gap-x-3 gap-y-3">
                      <div class="col-span-2"><label class="p-field-label">Producto terminado <span class="text-red-400">*</span></label><LinkInput v-model="prod.finished_item" v-mayus doctype="Item" :filters="ITEM_FILTERS.terminado" placeholder="Producto terminado…" @update:model-value="onProductoItemChange(prod)" /></div>
                      <div><label class="p-field-label">Cantidad <span class="text-red-400">*</span></label><input v-model.number="prod.qty" type="number" min="1" class="p-field tabular-nums" @input="onProdQtyChange(prod)" /></div>
                      <div class="col-span-3"><label class="p-field-label">Descripción <span class="text-ink-light font-normal">(opcional)</span></label><textarea v-model="prod.description" v-mayus rows="2" class="p-field h-auto py-2 resize-none" placeholder="Descripción del producto…"></textarea></div>
                    </div>
                  </div>

                  <!-- Costo y precio de venta: una franja, arriba de los pasos para que las tablas usen todo el ancho. -->
                  <div class="rounded-xl bg-zinc-50/70 border border-surface-border p-4 grid md:grid-cols-2 xl:grid-cols-[1.05fr_1fr_1.1fr] gap-x-7 gap-y-5">
                    <div class="space-y-4">
                    <!-- Precio de venta: se escribe dos veces, la primera oculta (pedido de Yelke): DialogoPrecio. -->
                    <div>
                      <p class="p-eyebrow flex items-center gap-1.5">Precio de venta unitario
                        <span v-if="prod.precio_manual" class="normal-case tracking-normal text-[10px] font-medium text-brand-700 bg-brand-50 border border-brand-200 rounded px-1" title="Precio fijado a mano -- no se recalcula aunque cambien costos, el margen se ajusta a él">fijo</span>
                      </p>
                      <button
                        type="button" class="mt-1.5 w-full flex items-center justify-between gap-2 rounded-xl bg-white border border-surface-border px-3.5 py-2.5 text-left hover:border-brand-300 transition-colors disabled:hover:border-surface-border"
                        :disabled="!canEditCosteo" title="Cambiar el precio de venta (se escribe dos veces)" @click="abrirPrecio(prod)"
                      >
                        <span class="text-[22px] font-semibold tracking-tight text-brand-600 tabular-nums truncate">{{ fmtC(prod.unit_sales_price) }}</span>
                        <span v-if="canEditCosteo" class="flex items-center gap-1 text-[12px] font-medium text-ink-muted flex-shrink-0"><Icono nombre="editar" class="w-3.5 h-3.5" />Cambiar</span>
                      </button>
                    </div>

                    <div>
                      <p class="p-eyebrow mb-2">Costo y margen</p>
                      <div class="grid grid-cols-3 gap-x-2.5 gap-y-2.5">
                        <div><label class="p-field-label">Overhead</label><div class="relative"><input v-model.number="prod.overhead_pct" type="number" min="0" max="100" class="p-field pr-7 tabular-nums" @input="recalcProducto(prod)" /><span class="suffix">%</span></div></div>
                        <div><label class="p-field-label">Margen</label><div class="relative"><input v-model.number="prod.margin_pct" type="number" min="0" max="99" class="p-field pr-7 tabular-nums" @input="onMarginChange(prod)" /><span class="suffix">%</span></div></div>
                        <div><label class="p-field-label">Flete / envío</label><div class="relative"><span class="prefix">$</span><input v-model.number="prod.shipping_cost" type="number" min="0" class="p-field pl-6 tabular-nums" @input="recalcProducto(prod)" /></div></div>
                        <div><label class="p-field-label">Etiquetado</label><div class="relative"><span class="prefix">$</span><input v-model.number="prod.labeling_cost" type="number" min="0" class="p-field pl-6 tabular-nums" @input="recalcProducto(prod)" /></div></div>
                        <div><label class="p-field-label">Empaquetado</label><div class="relative"><span class="prefix">$</span><input v-model.number="prod.packaging_cost" type="number" min="0" class="p-field pl-6 tabular-nums" @input="recalcProducto(prod)" /></div></div>
                      </div>
                    </div>

                    </div>

                    <!-- De qué se compone el costo por pieza: barra 100 % apilada (paleta
                         validada del tablero) + la lista con montos, que es la que se lee. -->
                    <div>
                      <p class="p-eyebrow mb-2">Composición por pieza</p>
                      <div v-if="telasCost(prod) + aviosCost(prod) + serviciosCost(prod) > 0" class="flex h-2 gap-[2px] rounded-full overflow-hidden mb-2.5" role="img" aria-label="Telas, avíos y servicios por pieza">
                        <div v-for="c in composicionCosto(prod).filter(c => c.pct > 0)" :key="c.etiqueta" :style="{ width: `${c.pct}%`, background: c.color }" :title="`${c.etiqueta}: ${fmtC(c.monto)} (${c.pct.toFixed(1)} %)`"></div>
                      </div>
                      <table class="w-full text-[12.5px]">
                        <thead><tr class="text-[10.5px] text-ink-light"><th class="text-left font-medium pb-1"></th><th class="text-right font-medium pb-1">Por pieza</th><th class="text-right font-medium pb-1">Total × {{ prod.qty || 0 }} pzas</th></tr></thead>
                        <tbody>
                          <tr v-for="c in composicionCosto(prod)" :key="c.etiqueta">
                            <td class="py-1 text-ink-muted"><span class="inline-flex items-center gap-1.5"><span class="w-2 h-2 rounded-[3px]" :style="{ background: c.color }"></span>{{ c.etiqueta }}</span></td>
                            <td class="py-1 text-right text-ink tabular-nums">{{ fmtC(c.monto) }}</td>
                            <td class="py-1 text-right text-ink-muted tabular-nums">{{ fmtC(c.monto * (prod.qty || 0)) }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>

                    <div>
                      <div class="flex items-center justify-between mb-1.5">
                        <p class="p-eyebrow">Resumen</p>
                        <span class="text-[10.5px] text-ink-light" title="Estos precios y costos no incluyen IVA">Precios sin IVA</span>
                      </div>
                      <div class="rounded-xl bg-white border border-surface-border px-3.5 py-2">
                        <table class="w-full text-[12.5px]">
                          <thead>
                            <tr class="text-[10.5px] text-ink-light">
                              <th class="text-left font-medium pb-1"></th>
                              <th class="text-right font-medium pb-1">Por pieza</th>
                              <th class="text-right font-medium pb-1">× {{ prod.qty || 0 }} pzas</th>
                            </tr>
                          </thead>
                          <tbody class="tabular-nums">
                            <tr>
                              <td class="py-1 text-ink-muted">Costo directo</td>
                              <td class="py-1 text-right text-ink">{{ fmtC(directCost(prod)) }}</td>
                              <td class="py-1 text-right text-ink">{{ fmtC(directCost(prod) * (prod.qty || 0)) }}</td>
                            </tr>
                            <tr>
                              <td class="py-1 text-ink-muted">Overhead</td>
                              <td class="py-1 text-right text-ink">{{ fmtC(prod.overhead_amt) }}</td>
                              <td class="py-1 text-right text-ink">{{ fmtC((prod.overhead_amt || 0) * (prod.qty || 0)) }}</td>
                            </tr>
                            <tr class="border-t border-surface-border font-semibold">
                              <td class="py-1.5 text-ink">Costo total</td>
                              <td class="py-1.5 text-right text-ink">{{ fmtC(prod.total_unit_cost) }}</td>
                              <td class="py-1.5 text-right text-ink">{{ fmtC((prod.total_unit_cost || 0) * (prod.qty || 0)) }}</td>
                            </tr>
                            <tr class="text-emerald-700">
                              <td class="py-1"><span class="inline-flex items-center gap-1.5">Utilidad esperada <span class="text-[10px] font-medium bg-emerald-50 rounded px-1 py-px">{{ prod.margin_pct || 0 }}%</span></span></td>
                              <td class="py-1 text-right">{{ fmtC(expectedProfit(prod)) }}</td>
                              <td class="py-1 text-right">{{ fmtC(expectedProfit(prod) * (prod.qty || 0)) }}</td>
                            </tr>
                            <tr class="border-t border-surface-border font-semibold text-brand-600">
                              <td class="py-1.5">Precio de venta</td>
                              <td class="py-1.5 text-right">{{ fmtC(prod.unit_sales_price) }}</td>
                              <td class="py-1.5 text-right">{{ fmtC(prod.total_sales_price) }}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>

                  <!-- Pasos de producción: cada uno es un taller/proveedor con sus servicios
                       y las materias primas que se usan ahí. -->
                  <div>
                    <div class="flex items-baseline justify-between gap-3 mb-2.5">
                      <p class="p-eyebrow">Pasos de producción</p>
                      <p class="p-meta">Materias primas + etapas: <b class="font-semibold text-ink tabular-nums">{{ fmtC(totalMaterias(prod) + totalEtapas(prod)) }}</b> <span class="text-ink-light">por pieza</span></p>
                    </div>

                    <div class="space-y-3">
                      <div v-for="(punto, pi) in puntosDe(prod.finished_item)" :key="punto.grupo_id" class="rounded-xl border border-surface-border overflow-visible">
                        <!-- Encabezado del punto: solo el proveedor. El orden real del flujo
                             (quién recibe de quién) se ajusta en Flujo de Producción, no aquí --
                             para que Costear no se infle con una decisión que todavía no toca. -->
                        <div class="px-3 py-2.5 flex items-center gap-2.5 flex-wrap border-b border-surface-border">
                          <span class="w-6 h-6 rounded-full bg-zinc-100 flex items-center justify-center text-[11px] font-semibold text-ink-muted flex-shrink-0">{{ pi + 1 }}</span>
                          <LinkInput :model-value="punto.servicios[0].proveedor" doctype="Supplier" placeholder="Taller / proveedor…" class="w-96 max-w-full" @update:model-value="v => setPuntoProveedor(punto, v)" />
                          <button type="button" class="del-btn ml-auto" title="Eliminar este punto completo" @click="removePunto(punto, prod)"><Icono nombre="x" class="w-3.5 h-3.5" :grosor="2" /></button>
                        </div>

                        <!-- Servicios de este punto -->
                        <div class="px-3 pt-2.5 pb-1">
                          <p class="flex items-center gap-1.5 text-[11.5px] font-medium text-ink-muted mb-1"><Icono nombre="servicio" class="w-3.5 h-3.5 text-ink-light" />Servicios</p>
                          <table class="w-full table-fixed text-[13px]">
                            <thead><tr class="text-left text-[11px] font-medium text-ink-light"><th class="py-1 font-medium">Servicio</th><th class="py-1 w-28 font-medium">UDM</th><th class="py-1 w-24 text-right font-medium" title="Cuántas veces se cobra el servicio por cada prenda (normalmente 1)">Operaciones por prenda</th><th class="py-1 w-24 text-right font-medium">Costo</th><th class="py-1 w-24 text-right pr-1 font-medium">Total</th><th class="w-7"></th></tr></thead>
                            <tbody>
                              <tr v-for="e in punto.servicios" :key="e._tid" class="align-top">
                                <td class="py-1 pr-2"><LinkInput v-model="e.servicio" v-mayus doctype="Item" :filters="filtrosServicio(punto)" :placeholder="placeholderServicio(punto)" @update:model-value="onEtapaServicioChange(e, prod)" /></td>
                                <td class="py-1 pr-2"><LinkInput v-model="e.lote_uom" doctype="UOM" placeholder="UDM" class="min-w-0" /></td>
                                <td class="py-1 pr-2"><input v-model.number="e.operaciones_por_pieza" type="number" min="0" step="1" placeholder="1" class="field-input text-right" title="Cuántas veces se aplica esta operación en CADA pieza -- ej. 4 segmentos de cinta reflejante por prenda" @input="recalcPrecioOperacion(e, prod)" /></td>
                                <td class="py-1 pr-2"><div class="relative"><span class="prefix text-xs">$</span><input v-model.number="e.precio_por_operacion" type="number" min="0" step="0.01" class="field-input text-right pl-4" title="Precio de cada una" @input="recalcPrecioOperacion(e, prod)" /></div></td>
                                <td class="py-1 pr-1 text-right font-medium text-ink tabular-nums pt-2.5">{{ fmtC(precioPorPiezaEtapa(e)) }}</td>
                                <td class="py-1"><button type="button" class="del-btn mt-1.5" @click="removeServicioDePunto(e, punto, prod)"><Icono nombre="x" class="w-3.5 h-3.5" :grosor="2" /></button></td>
                              </tr>
                            </tbody>
                          </table>
                          <button type="button" class="add-link -ml-2.5" @click="addServicioAPunto(punto, prod)"><Icono nombre="mas" class="w-3.5 h-3.5" :grosor="2.2" />Agregar servicio a este punto</button>
                        </div>

                        <!-- Materias primas de este punto -->
                        <div class="border-t border-surface-border/70 px-3 pt-2.5 pb-1">
                          <p class="flex items-center gap-1.5 text-[11.5px] font-medium text-ink-muted mb-1"><Icono nombre="material" class="w-3.5 h-3.5 text-ink-light" />Materias primas de este punto</p>
                          <table v-if="materialesDelPunto(punto).length" class="w-full text-[13px] mb-1" style="table-layout: auto;">
                            <colgroup>
                              <col style="width: 22%">
                              <col style="width: 20%">
                              <col style="width: 9%">
                              <col style="width: 12%">
                              <col style="width: 17%">
                              <col style="width: 11%">
                              <col style="width: 9%">
                              <col style="width: 28px">
                            </colgroup>
                            <thead><tr class="text-left text-[11px] text-ink-light"><th class="py-1 font-medium">Artículo</th><th class="py-1 font-medium">Proveedor</th><th class="py-1 font-medium">Tipo</th><th class="py-1 font-medium">UDM</th><th class="py-1 font-medium">Rendimiento / Consumo</th><th class="py-1 text-right font-medium">Precio / UDM</th><th class="py-1 text-right font-medium">Total</th><th></th></tr></thead>
                            <tbody>
                              <tr v-for="d in materialesDelPunto(punto)" :key="d._tid" class="align-top">
                                <td class="py-1 pr-2">
                                  <div class="flex items-center gap-1 mb-1 invisible" aria-hidden="true"><span class="text-[10px] px-1.5 py-0.5 rounded-full">·</span></div>
                                  <LinkInput v-model="d.item" v-mayus doctype="Item" :filters="ITEM_FILTERS.mp" placeholder="Materia prima…" @update:model-value="onDetalleItemChange(d, prod)" />
                                </td>
                                <td class="py-1 pr-2">
                                  <div class="flex items-center gap-1 mb-1 invisible" aria-hidden="true"><span class="text-[10px] px-1.5 py-0.5 rounded-full">·</span></div>
                                  <select v-model="d.supplier" :disabled="!d.item" class="field-input" @change="onSupplierChange(d, prod)">
                                    <option value="">{{ !d.item ? 'Elige artículo' : '— Proveedor —' }}</option>
                                    <option v-for="o in allSuppliers" :key="o.name" :value="o.name">{{ o.nombre_comercial || o.supplier_name || o.name }}</option>
                                  </select>
                                </td>
                                <td class="py-1 pr-2">
                                  <div class="flex items-center gap-1 mb-1 invisible" aria-hidden="true"><span class="text-[10px] px-1.5 py-0.5 rounded-full">·</span></div>
                                  <select v-model="d.tipo_material" class="field-input" @change="onTipoMaterialChange(d, prod)">
                                    <option value="">— Tipo —</option>
                                    <option value="Tela">Tela</option>
                                    <option value="Avío">Avío</option>
                                  </select>
                                </td>
                                <td class="py-1 pr-2">
                                  <div class="flex items-center gap-1 mb-1 invisible" aria-hidden="true"><span class="text-[10px] px-1.5 py-0.5 rounded-full">·</span></div>
                                  <!-- Con articulo elegido, la UDM es la BASE de ese articulo y no se
                                       escoge a mano: el consumo del costeo siempre va en esa unidad.
                                       Sin articulo (material en texto libre) sigue el selector por tipo. -->
                                  <div v-if="d.item && udmBaseDe(d)" class="field-input bg-surface-raised/60 truncate" :title="`UDM base de ${d.item} — el consumo se captura en esta unidad`">
                                    {{ udmBaseDe(d) }}
                                  </div>
                                  <select v-else v-model="d.internal_uom" class="field-input" :disabled="!d.tipo_material" @change="onUdmSelectChange(d, prod)">
                                    <option value="">{{ d.tipo_material ? '— UDM —' : 'Elige tipo' }}</option>
                                    <option v-for="o in udmOptionsFor(d)" :key="o.value" :value="o.value">{{ o.label }}</option>
                                  </select>
                                </td>
                                <td class="py-1 pr-2">
                                  <div class="flex items-center gap-1 mb-1">
                                    <template v-if="qtyModeLocked(d)">
                                      <span class="text-[10px] px-1.5 py-0.5 rounded-full bg-brand-100 text-brand-700 font-semibold">{{ QTY_MODE_LABEL[qtyModeFor(d)] }}</span>
                                    </template>
                                    <template v-else>
                                      <button type="button" class="text-[10px] px-1.5 py-0.5 rounded-full" :class="qtyModeFor(d) === 'rendimiento' ? 'bg-brand-100 text-brand-700 font-semibold' : 'text-ink-light hover:bg-surface-raised'" @click="d._qtyMode = 'rendimiento'">Rendimiento</button>
                                      <button type="button" class="text-[10px] px-1.5 py-0.5 rounded-full" :class="qtyModeFor(d) === 'consumo' ? 'bg-brand-100 text-brand-700 font-semibold' : 'text-ink-light hover:bg-surface-raised'" @click="d._qtyMode = 'consumo'">Consumo</button>
                                    </template>
                                  </div>
                                  <input v-if="qtyModeFor(d) === 'consumo'" v-model.number="d.internal_qty" type="number" min="0" step="1" class="field-input text-right" placeholder="UDM por pza" @input="onConsumoInput(d, prod)" />
                                  <input v-else-if="qtyModeFor(d) === 'piezas'" :value="piezasPorPrenda(d)" type="number" min="0" step="1" class="field-input text-right" placeholder="pzas por prenda" @input="onPiezasInput(d, prod, $event.target.value)" />
                                  <input v-else v-model.number="d.rendimiento" type="number" min="0" step="1" class="field-input text-right" placeholder="pzas por UDM" @input="onRendimientoInput(d, prod)" />
                                  <p class="text-[10.5px] text-ink-light mt-1 truncate">
                                    <template v-if="qtyModeFor(d) === 'consumo'">≈ {{ fmtQty(d.rendimiento) }} pzas/{{ d.internal_uom || 'UDM' }}</template>
                                    <template v-else-if="qtyModeFor(d) === 'piezas'">1 {{ d.internal_uom }} = {{ fmtQty(piezasPorUdm(d)) }} pzas</template>
                                    <template v-else>≈ {{ fmtQty(d.internal_qty) }} {{ d.internal_uom || 'UDM' }}/pza</template>
                                    · total: {{ fmtQty(d.supplier_qty) }} {{ d.supplier_uom || d.internal_uom || 'UDM' }}
                                  </p>
                                </td>
                                <td class="py-1 pr-2">
                                  <div class="flex items-center gap-1 mb-1 invisible" aria-hidden="true"><span class="text-[10px] px-1.5 py-0.5 rounded-full">·</span></div>
                                  <div class="relative">
                                    <span class="prefix text-xs">$</span>
                                    <input v-model.number="d.precio_compra" type="number" min="0" step="0.01" class="field-input text-right pl-5" :class="d.tipo_material === 'Tela' ? 'pr-6' : ''" @input="onPrecioCompraInput(d, prod)" />
                                    <button v-if="d.tipo_material === 'Tela'" type="button" class="absolute right-1 top-1/2 -translate-y-1/2 text-ink-light hover:text-brand-600" title="Convertir precio de $/kg a $/m" @click="openTelaConvert(d, prod)">
                                      <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><rect x="5" y="3" width="14" height="18" rx="2"/><path stroke-linecap="round" d="M8 7h8M8 11h.01M12 11h.01M16 11h.01M8 15h.01M12 15h.01M16 15h.01"/></svg>
                                    </button>
                                    <template v-if="telaConvertModal.open && telaConvertModal.d === d">
                                      <div class="fixed inset-0 z-40" @click="closeTelaConvert()"></div>
                                      <div class="absolute z-50 right-0 top-full mt-1 w-64 bg-white border border-surface-border rounded-xl shadow-lg p-3 text-left">
                                        <p class="text-xs font-semibold text-ink mb-2">Convertir $/kg → $/m</p>
                                        <label class="field-label mb-0.5">Precio por kilo (el que te dio el proveedor)</label>
                                        <div class="relative mb-2"><span class="prefix text-xs">$</span><input v-model.number="telaConvertModal.precio_kg" type="number" min="0" step="0.01" class="field-input text-right pl-5 py-1" /></div>
                                        <label class="field-label mb-0.5">Metros que salen de 1 kilo</label>
                                        <input v-model.number="telaConvertModal.metros_por_kilo" type="number" min="0" step="0.01" placeholder="ej. 5.2" class="field-input text-right py-1" />
                                        <p class="text-[11px] text-ink-muted mt-2">Precio por metro: <span class="font-semibold text-brand-600">{{ fmtC(telaConvertPrecioM) }}</span></p>
                                        <p v-if="telaConvertModal.itemExists" class="text-[10px] text-ink-xlight mt-1">Se guarda en el artículo para no repetirlo la próxima vez.</p>
                                        <p v-else class="text-[10px] text-ink-xlight mt-1">Este artículo aún no existe como Item -- no se podrá guardar para después.</p>
                                        <p class="text-[10px] text-ink-xlight mt-1">Al usar este precio la UDM del renglón cambia a Metro -- ahí capturas tú el consumo por prenda.</p>
                                        <div class="flex items-center justify-end gap-3 mt-3">
                                          <button type="button" class="text-xs text-ink-light hover:text-ink" @click="closeTelaConvert()">Cancelar</button>
                                          <button type="button" class="text-xs font-semibold text-white bg-brand-500 hover:bg-brand-600 rounded-lg px-3 py-1.5" @click="aplicarTelaConvert()">Usar este precio</button>
                                        </div>
                                      </div>
                                    </template>
                                  </div>
                                  <!-- En que UDM cotiza el proveedor. El precio se teclea tal como lo
                                       da (725.76 el Mazo) y el unitario por UDM base se deriva solo:
                                       asi nadie tiene que dividir a mano. Solo aparece cuando el
                                       articulo tiene mas de una UDM dada de alta. -->
                                  <select
                                    v-if="udmsCompraDe(d).length > 1"
                                    v-model="d.supplier_uom" class="field-input mt-1 text-[11px] py-0.5"
                                    title="UDM en la que el proveedor cotiza este precio"
                                    @change="onUdmCompraChange(d, prod)"
                                  >
                                    <option v-for="u in udmsCompraDe(d)" :key="u.uom" :value="u.uom">
                                      por {{ u.uom }}{{ u.uom === udmBaseDe(d) ? '' : ` (${fmtQty(u.conversion_factor)} ${udmBaseDe(d)})` }}
                                    </option>
                                  </select>
                                  <p v-if="factorCompra(d) !== 1" class="text-[10.5px] text-ink-light mt-0.5 text-right">
                                    = {{ fmtC(d.unit_price) }} / {{ udmBaseDe(d) || 'UDM' }}
                                  </p>
                                </td>
                                <td class="py-1 pr-2 text-right font-medium text-ink tabular-nums">
                                  <div class="flex items-center gap-1 mb-1 invisible" aria-hidden="true"><span class="text-[10px] px-1.5 py-0.5 rounded-full">·</span></div>
                                  <span class="inline-block pt-2">{{ fmtC(d.total) }}</span>
                                </td>
                                <td class="py-1">
                                  <div class="flex items-center gap-1 mb-1 invisible" aria-hidden="true"><span class="text-[10px] px-1.5 py-0.5 rounded-full">·</span></div>
                                  <button type="button" class="del-btn mt-1.5" @click="removeDetalle(d, prod)"><Icono nombre="x" class="w-3.5 h-3.5" :grosor="2" /></button>
                                </td>
                              </tr>
                            </tbody>
                          </table>
                          <p v-else class="text-[12px] text-ink-xlight py-1">Ninguna todavía.</p>
                          <button type="button" class="add-link -ml-2.5" @click="addMaterialAPunto(punto, prod)"><Icono nombre="mas" class="w-3.5 h-3.5" :grosor="2.2" />Agregar material</button>
                        </div>
                      </div>

                      <button type="button" class="w-full h-11 rounded-xl border border-dashed border-surface-border hover:border-brand-300 hover:bg-brand-50/40 text-ink-muted hover:text-brand-600 flex items-center justify-center gap-2 text-[13px] font-medium transition-colors" @click="addPunto(prod)">
                        <Icono nombre="mas" class="w-4 h-4" :grosor="2" />
                        Agregar paso
                      </button>
                    </div>

                    <!-- Materiales pendientes de asignar a un punto -- NO es un estado normal:
                         todo material siempre se usa en algún punto concreto de verdad, así que
                         esto solo debería aparecer con costeos capturados antes de este árbol.
                         Por eso ya no hay botón para crear materiales sueltos a propósito --
                         solo un aviso con una forma rápida de resolver los que ya existían. -->
                    <div v-if="materialesSinPunto(prod.finished_item).length" class="mt-3 rounded-xl border border-amber-200 bg-amber-50/50 px-3 py-2.5">
                      <p class="text-[12px] font-semibold text-amber-800 mb-1.5 flex items-start gap-1.5">
                        <Icono nombre="alerta" class="w-3.5 h-3.5 flex-shrink-0 mt-px" />
                        <span>Pendientes de asignar a un punto <span class="font-normal text-amber-700">— sin esto, el sistema los atribuye solos al arranque del flujo, lo cual puede ser incorrecto</span></span>
                      </p>
                      <table class="w-full table-fixed text-[13px]">
                        <tbody>
                          <tr v-for="d in materialesSinPunto(prod.finished_item)" :key="d._tid" class="border-b border-amber-200/60 last:border-0 align-top">
                            <td class="py-1.5 pr-2 w-1/5"><LinkInput v-model="d.item" v-mayus doctype="Item" :filters="ITEM_FILTERS.mp" placeholder="Materia prima…" @update:model-value="onDetalleItemChange(d, prod)" /></td>
                            <td class="py-1.5 pr-2 w-1/5">
                              <select v-model="d.supplier" :disabled="!d.item" class="field-input" @change="onSupplierChange(d, prod)">
                                <option value="">{{ !d.item ? 'Elige artículo' : '— Proveedor —' }}</option>
                                <option v-for="o in allSuppliers" :key="o.name" :value="o.name">{{ o.supplier_name || o.name }}</option>
                              </select>
                            </td>
                            <td class="py-1.5 pr-2 w-20">
                              <select v-model="d.tipo_material" class="field-input" @change="onTipoMaterialChange(d, prod)">
                                <option value="">— Tipo —</option>
                                <option value="Tela">Tela</option>
                                <option value="Avío">Avío</option>
                              </select>
                            </td>
                            <td class="py-1.5 pr-2 w-24"><div class="relative"><span class="prefix text-xs">$</span><input v-model.number="d.unit_price" type="number" min="0" step="0.01" class="field-input text-right pl-5" @input="recalcDetalle(d, prod)" /></div></td>
                            <td class="py-1.5 pr-2 w-44">
                              <select :value="''" :disabled="!puntosDe(prod.finished_item).length" class="field-input" :class="!puntosDe(prod.finished_item).length ? '' : 'ring-1 ring-amber-300'" @change="asignarMaterialAPunto(d, prod, $event.target.value)">
                                <option value="" disabled>{{ puntosDe(prod.finished_item).length ? 'Asignar a un punto…' : 'Agrega un punto primero' }}</option>
                                <option v-for="(pt, pti) in puntosDe(prod.finished_item)" :key="pt.grupo_id" :value="pt.grupo_id">Punto {{ pti + 1 }} · {{ nombreProveedor(pt.servicios[0].proveedor) || 'sin proveedor' }}</option>
                              </select>
                            </td>
                            <td class="py-1.5 w-7"><button type="button" class="del-btn" @click="removeDetalle(d, prod)"><Icono nombre="x" class="w-3.5 h-3.5" :grosor="2" /></button></td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <!-- Variante de talla: para una talla que necesita MÁS/DISTINTO material
                       (no solo un ajuste de precio) -- se costea como su propio producto,
                       independiente, con sus propios materiales/etapas/precio. -->
                  <button
                    v-if="!prod.finished_item || varianteWizard.finished_item !== prod.finished_item"
                    type="button" class="add-link -ml-2.5 disabled:opacity-40" :disabled="!prod.finished_item"
                    :title="prod.finished_item ? '' : 'Elige primero el producto terminado'"
                    @click="abrirVarianteWizard(prod)"
                  ><Icono nombre="mas" class="w-3.5 h-3.5" :grosor="2.2" />Agregar variante por talla</button>

                  <!-- Variante por talla en UN solo formulario: qué tallas cubre, cuántas piezas
                       y qué materiales cambian -- todo se manda junto al crearla
                       (crear_variante_talla con ``materiales``). Antes había un segundo paso
                       para los materiales y lo escrito se perdía si no se presionaba
                       "Agregar material" antes de "Listo". -->
                  <div v-else class="rounded-xl border border-surface-border overflow-hidden">
                    <div class="px-4 py-3 border-b border-surface-border flex items-start justify-between gap-3">
                      <div>
                        <p class="text-[13.5px] font-semibold text-ink">Nueva variante por talla</p>
                        <p class="p-meta mt-0.5">Se crea como un producto aparte, con su propio artículo, precio y materiales, y su propia línea en cotización, orden de venta y factura.</p>
                      </div>
                      <button type="button" class="p-btn-ghost h-7 px-2 text-[12px] flex-shrink-0" @click="cerrarVarianteWizard">Cancelar</button>
                    </div>

                    <div class="p-4 space-y-5">
                      <div>
                        <p class="p-eyebrow mb-2">Talla y cantidad</p>
                        <div class="grid sm:grid-cols-[150px_minmax(0,1fr)_130px] gap-3 items-end">
                          <div>
                            <label class="p-field-label">Género</label>
                            <select v-model="varianteWizard.genero" class="p-field" @change="varianteWizard.grupo_talla = ''; varianteWizard.talla = '';">
                              <option value="">Género…</option>
                              <option value="Dama">Dama</option>
                              <option value="Caballero">Caballero</option>
                            </select>
                          </div>
                          <div>
                            <label class="p-field-label">Tipo de prenda</label>
                            <select v-model="varianteWizard.grupo_talla" class="p-field" :disabled="!varianteWizard.genero" @change="varianteWizard.talla = ''">
                              <option value="">{{ varianteWizard.genero ? 'Tipo de prenda…' : '— elige género —' }}</option>
                              <option v-for="g in gruposDeGenero(varianteWizard.genero)" :key="g.name" :value="g.name">{{ g.talla }}</option>
                            </select>
                          </div>
                          <div>
                            <label class="p-field-label">Cantidad</label>
                            <input v-model.number="varianteWizard.qty" type="number" min="0" :disabled="varianteWizard.pendiente" class="p-field text-right tabular-nums" />
                          </div>
                        </div>
                        <div v-if="varianteWizard.grupo_talla" class="mt-3">
                          <p class="p-field-label">Tallas que cubre</p>
                          <div class="flex flex-wrap gap-1.5">
                            <button
                              v-for="s in tallasDeGrupo(varianteWizard.grupo_talla)" :key="s.name" type="button"
                              class="h-7 min-w-[36px] px-2.5 rounded-md text-[12px] border transition-colors"
                              :class="varianteWizardTallas.includes(s.name) ? 'bg-brand-500 text-white border-brand-500' : 'bg-white text-ink-muted border-surface-border hover:border-brand-300'"
                              @click="toggleVarianteWizardTalla(s.name)"
                            >{{ s.talla }}</button>
                          </div>
                        </div>
                        <label class="mt-3 inline-flex items-center gap-1.5 text-[12.5px] text-ink-muted cursor-pointer select-none">
                          <input v-model="varianteWizard.pendiente" type="checkbox" class="w-3.5 h-3.5 accent-brand-500" />
                          Cantidad pendiente por confirmar
                        </label>
                      </div>

                      <div v-if="materialesBaseVariante(prod).length">
                        <p class="p-eyebrow">Materiales de esta talla</p>
                        <p class="p-meta mt-0.5 mb-2">Vienen igual que el producto base. Cambia solo los que esta talla lleva de más o de menos.</p>
                        <div class="rounded-lg border border-surface-border divide-y divide-surface-border">
                          <div class="grid grid-cols-[minmax(0,1fr)_120px_190px] gap-3 px-3 py-1.5 text-[11px] text-ink-light bg-zinc-50/70">
                            <span>Material</span><span class="text-right">Base</span><span class="text-right">Esta talla</span>
                          </div>
                          <div
                            v-for="d in materialesBaseVariante(prod)" :key="d.material_id"
                            class="grid grid-cols-[minmax(0,1fr)_120px_190px] gap-3 px-3 py-2 items-center"
                            :class="cambiaEnTalla(d) ? 'bg-brand-50/40' : ''"
                          >
                            <div class="min-w-0">
                              <p class="text-[12.5px] text-ink truncate" :title="d.item">{{ d.item }}</p>
                              <p class="text-[11px] text-ink-light truncate">{{ unidadDeFila(d).etiqueta }}<template v-if="unidadDeFila(d).ayuda"> · {{ unidadDeFila(d).ayuda }}</template></p>
                            </div>
                            <span class="text-right text-[12.5px] text-ink-muted tabular-nums">{{ consumoBase(d) }}</span>
                            <div class="flex items-center justify-end gap-2">
                              <span v-if="cambiaEnTalla(d)" class="text-[11px] font-semibold tabular-nums" :class="diferenciaTalla(d) > 0 ? 'text-brand-700' : 'text-ink-muted'">{{ diferenciaTalla(d) > 0 ? '+' : '' }}{{ diferenciaTalla(d) }}</span>
                              <input
                                :value="valorTalla(d)" type="number" min="0" step="any"
                                class="p-field h-8 w-28 text-right tabular-nums" :class="cambiaEnTalla(d) ? 'border-brand-300 ring-1 ring-brand-200' : ''"
                                @input="varianteWizard.consumos[d.material_id] = $event.target.value"
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div class="px-4 py-3 border-t border-surface-border bg-zinc-50/60 flex items-center justify-between gap-3">
                      <p class="p-meta">{{ cambiosVariante(prod) ? `${cambiosVariante(prod)} ${cambiosVariante(prod) === 1 ? "material cambia" : "materiales cambian"} en esta talla` : "Mismos materiales que el producto base" }}</p>
                      <button type="button" :disabled="varianteWizard.loading || !varianteWizardTallas.length || (!varianteWizard.pendiente && !varianteWizard.qty)" class="p-btn-primary" @click="crearVarianteTalla(prod)">
                        {{ varianteWizard.loading ? "Creando…" : "Crear variante" }}
                      </button>
                    </div>
                  </div>

              </div>
            </div>
          </div>
        </section>
      </div>
      </fieldset>
    </div>

    <!-- ══════════ STEP 1 · COTIZAR ══════════ -->
    <!-- Lenguaje de Producción/Dirección (p-*), igual que Costear: cada cotización es
         una tarjeta; al abrirla, a la izquierda sus datos y acciones, a la derecha la
         vista previa del PDF. -->
    <div v-else-if="activeStep === 1" class="px-5 lg:px-8 py-6 pb-20" v-solo-lectura="soloLecturaPaso">
      <!-- Solo lectura: el usuario tiene esta etapa en "ver" (accesos por vista). -->
      <p v-if="soloLecturaPaso" class="max-w-5xl mx-auto mb-4 text-[12.5px] text-ink-muted bg-surface-raised rounded-lg px-3 py-2">
        <b class="text-ink">Solo lectura.</b> Puedes consultar esta etapa; la captura la hace quien la tiene asignada.
      </p>
      <div class="max-w-[1320px] mx-auto space-y-3">
        <div v-if="related.quotations.length" class="flex items-end justify-between gap-3 mb-1">
          <div>
            <p class="p-eyebrow">Cotizaciones</p>
            <p class="p-meta mt-0.5">{{ related.quotations.length }} {{ related.quotations.length === 1 ? "cotización" : "cotizaciones" }} de este costeo</p>
          </div>
        </div>

        <!-- Lista de cotizaciones del costeo (acordeón, mismo patrón que Productos a costear) -->
        <div v-for="q in related.quotations" :key="q.name" class="group p-panel" :id="`doc-hl-${q.name}`" :class="{ 'doc-highlight-flash': highlightTarget === q.name }">
          <div class="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-zinc-50 rounded-xl transition-colors" :class="expandedQuotName === q.name ? 'rounded-b-none' : ''" @click="toggleQuotation(q)">
            <svg class="w-4 h-4 text-ink-light flex-shrink-0 transition-transform" :class="expandedQuotName === q.name ? 'rotate-90' : ''" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
            <Icono nombre="documento" class="w-4 h-4 text-ink-light flex-shrink-0" />
            <p class="text-[14px] font-semibold text-ink">{{ q.name }}</p>
            <span :class="q.status === 'Lost' ? 'p-pill-bad' : (q.docstatus === 2 ? 'p-pill-off' : (q.docstatus === 1 ? 'p-pill-ok' : 'p-pill-wait'))">{{ q.status === 'Lost' ? 'Rechazada' : (q.docstatus === 2 ? 'Cancelada' : (q.docstatus === 1 ? 'Validada' : 'Borrador')) }}</span>
            <div class="ml-auto text-right">
              <p class="text-[10.5px] text-ink-light">Total</p>
              <p class="text-[14px] font-semibold text-ink tabular-nums">{{ fmtC(q.grand_total) }}</p>
            </div>
            <button type="button" class="opacity-0 group-hover:opacity-100 w-7 h-7 flex items-center justify-center rounded-md hover:bg-red-50 hover:text-red-500 text-ink-xlight transition-all flex-shrink-0" title="Eliminar cotización" @click.stop="openDeleteQuot(q.name)">
              <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
            </button>
          </div>

          <div v-if="expandedQuotName === q.name" class="border-t border-surface-border grid lg:grid-cols-[360px_minmax(0,1fr)]">
            <!-- La tabla de artículos se quitó a propósito: los productos/precios ya
                 quedaron fijos desde Costear, este paso no permite editarlos -- se
                 siguen guardando/enviando tal cual (cotItems), solo ya no se muestran
                 ni se pueden tocar aquí. -->

            <!-- Izquierda: campos manuales y acciones -->
            <div class="min-w-0 p-5 space-y-5 lg:border-r border-surface-border">
              <div v-if="q.status === 'Lost'" class="rounded-xl bg-red-50/70 border border-red-100 px-3.5 py-3">
                <p class="text-[12.5px] font-semibold text-red-700 flex items-center gap-1.5"><Icono nombre="alerta" class="w-3.5 h-3.5" />Cotización rechazada</p>
                <p v-if="q.order_lost_reason" class="text-[12px] text-red-600 mt-0.5">{{ q.order_lost_reason }}</p>
                <button type="button" :disabled="advancing" class="mt-2.5 w-full text-left rounded-lg bg-white border border-red-200 px-3 py-2 hover:bg-red-50 disabled:opacity-50" @click="openRevisionModal">
                  <span class="block text-[12.5px] font-semibold text-red-700">Editar Costeo</span>
                  <span class="block text-[11px] text-red-500">Toda corrección (precio, condiciones, materiales, cantidades…) se hace desde el costeo.</span>
                </button>
              </div>

              <div v-if="q.docstatus === 2" class="rounded-xl bg-zinc-50 border border-surface-border px-3.5 py-3">
                <p class="text-[12.5px] font-semibold text-ink">Cotización cancelada</p>
                <p class="text-[12px] text-ink-muted mt-0.5">El proyecto quedó marcado como cancelado. Si en realidad sigue en pie, edita el costeo para reactivarlo con una revisión nueva.</p>
                <button type="button" :disabled="advancing" class="mt-2.5 w-full text-left rounded-lg bg-white border border-surface-border px-3 py-2 hover:bg-surface-raised disabled:opacity-50" @click="openRevisionModal">
                  <span class="block text-[12.5px] font-semibold text-ink">Editar Costeo</span>
                  <span class="block text-[11px] text-ink-light">Regresa el costeo a borrador y reactiva el proyecto.</span>
                </button>
              </div>

              <div>
                <p class="p-eyebrow">Datos de la cotización</p>
                <p class="p-meta mt-0.5 mb-3">Completa lo que no viene del costeo. Productos y totales son automáticos.</p>
                <div class="grid grid-cols-2 gap-x-3 gap-y-3">
                  <div><label class="p-field-label">Vigencia (válida hasta)</label><input v-model="cotForm.valid_till" type="date" class="p-field" :disabled="q.docstatus === 1" /></div>
                  <div><label class="p-field-label">Moneda</label>
                    <select v-model="cotForm.currency" class="p-field" :disabled="q.docstatus === 1">
                      <option v-for="c in cotDefaults.currencies" :key="c.name" :value="c.name">{{ c.name }}</option>
                    </select>
                  </div>
                  <div class="col-span-2"><label class="p-field-label">Condiciones de pago</label>
                    <select v-model="cotForm.payment_terms_template" class="p-field" :disabled="q.docstatus === 1">
                      <option value="">— Sin plantilla —</option>
                      <option v-for="p in cotDefaults.payment_terms_templates" :key="p.name" :value="p.name">{{ p.name }}</option>
                    </select>
                  </div>
                  <div class="col-span-2"><label class="p-field-label">Términos y condiciones</label>
                    <select v-model="cotForm.tc_name" class="p-field" :disabled="q.docstatus === 1">
                      <option value="">— Sin términos —</option>
                      <option v-for="t in terminosPara(cotDefaults.terms, 'venta', form.cliente, cotForm.tc_name)" :key="t.name" :value="t.name">{{ t.name }}</option>
                    </select>
                  </div>
                  <div class="col-span-2"><label class="p-field-label">Lista de Precios</label>
                    <select v-model="cotForm.selling_price_list" class="p-field" :disabled="q.docstatus === 1">
                      <option value="">— Sin lista —</option>
                      <option v-for="pl in cotDefaults.price_lists" :key="pl.name" :value="pl.name">{{ pl.name }}</option>
                    </select>
                  </div>
                  <div class="col-span-2"><label class="p-field-label">Impuestos y Cargos</label>
                    <select v-model="cotForm.taxes_and_charges" class="p-field" :disabled="q.docstatus === 1">
                      <option value="">— Sin plantilla —</option>
                      <option v-for="t in cotDefaults.tax_templates" :key="t.name" :value="t.name">{{ t.name }}</option>
                    </select>
                  </div>
                  <div class="col-span-2"><label class="p-field-label">Email de contacto</label><input v-model="cotForm.contact_email" type="email" class="p-field" :disabled="q.docstatus === 1" placeholder="correo@cliente.com" /></div>
                  <div class="col-span-2"><label class="p-field-label">WhatsApp / Móvil</label><input v-model="cotForm.contact_mobile" type="tel" class="p-field" :disabled="q.docstatus === 1" placeholder="+52 55 1234 5678" /></div>
                </div>
              </div>

              <div class="space-y-2">
                <template v-if="q.docstatus !== 1">
                  <FranjaAprobacion
                    doctype="Quotation" :name="q.name" :guardar="guardarCambiosCotizacion"
                    @estado="(s) => (aprobPanel[q.name] = s)" @cambio="trasAprobacionVenta"
                  />
                  <button v-if="validaDirecto(q.name) && !enAprobacion(q.name)" type="button" :disabled="advancing" class="p-btn-primary w-full" @click="validarDoc('Quotation', q.name)">
                    <Icono nombre="check-circulo" class="w-4 h-4" />Validar cotización
                  </button>
                  <button type="button" :disabled="advancing" class="p-btn-secondary w-full" @click="guardarCambiosCotizacion">Guardar cambios</button>
                </template>
                <div class="flex flex-wrap gap-1.5 pt-1">
                  <button v-if="q.docstatus === 1" type="button" class="doc-action" @click="openSend('Quotation', q.name, q.contact_email, q.contact_mobile)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>Enviar</button>
                  <button data-libre type="button" class="doc-action" @click="downloadPdf('Quotation', q.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/></svg>Descargar</button>
                  <button data-libre type="button" class="doc-action" @click="printDocView('Quotation', q.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2z"/></svg>Imprimir</button>
                  <button type="button" class="doc-action" @click="openAssign('Quotation', q.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>Asignar</button>
                  <a class="doc-action" :href="`/app/quotation/${q.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>Abrir en ERPNext</a>
                </div>
              </div>

              <div v-if="q.docstatus === 1 && q.status !== 'Lost'" class="pt-4 border-t border-surface-border space-y-2">
                <p class="p-eyebrow">Precio acordado</p>
                <button
                  type="button"
                  class="p-btn w-full bg-orange-500 text-white hover:bg-orange-600 disabled:hover:bg-orange-500"
                  :disabled="precioAcordadoStatus.todos_validados"
                  :title="precioAcordadoStatus.todos_validados ? 'El precio acordado ya está validado -- no se puede volver a fijar/editar desde aquí.' : ''"
                  @click="openAcordadoModal"
                >Fijar Precio</button>
                <div v-if="precioAcordadoStatus.items.length" class="flex items-center justify-between gap-2">
                  <span :class="precioAcordadoStatus.todos_validados ? 'p-pill-ok' : 'p-pill-wait'">
                    Precio acordado: {{ precioAcordadoStatus.todos_validados ? 'Validado' : 'Borrador' }} ({{ precioAcordadoStatus.items.length }})
                  </span>
                  <button v-if="!precioAcordadoStatus.todos_validados && precioAcordadoStatus.es_ceo" type="button" :disabled="advancing" class="text-[12px] font-semibold text-brand-600 hover:text-brand-700 hover:underline disabled:opacity-50" @click="validarPrecioAcordado">Validar</button>
                </div>
                <button type="button" class="p-btn w-full h-8 text-[12.5px] font-medium text-red-600 border border-red-200 hover:bg-red-50" @click="openRechazarModal">Marcar rechazada</button>
              </div>

              <div class="pt-4 border-t border-surface-border">
                <AttachmentsPanel doctype="Quotation" :docname="q.name" />
              </div>
            </div>

            <!-- Derecha: vista previa del PDF (zoom reducido) -->
            <div class="min-w-0 border-t lg:border-t-0 border-surface-border flex flex-col">
              <div class="flex items-center justify-between px-4 py-2 border-b border-surface-border">
                <p class="p-eyebrow">Vista previa</p>
                <button data-libre type="button" class="doc-action" @click="openPdf('Quotation', q.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 8V4m0 0h4M4 4l5 5m11-5h-4m4 0v4m0-4l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5h-4m4 0v-4m0 4l-5-5"/></svg>Ampliar</button>
              </div>
              <!-- Crece hasta el final del formulario de la izquierda (nunca menos de 70vh):
                   el iframe va absoluto y escalado a 0.7, así llena el contenedor sin
                   depender de una altura fija. -->
              <div class="relative flex-1 bg-zinc-50 rounded-br-xl overflow-hidden" style="min-height: 70vh;">
                <iframe :key="previewKey" :src="printUrl('Quotation', q.name)" class="absolute top-0 left-0" style="width: 143%; height: 143%; transform: scale(0.7); transform-origin: top left; border: 0;" title="Vista previa de la cotización"></iframe>
              </div>
            </div>
          </div>
        </div>

        <!-- Crear la primera cotización -->
        <div v-if="!related.quotations.length" class="p-panel max-w-[560px] mx-auto mt-4">
          <div class="px-5 pt-5">
            <p class="p-eyebrow">Nueva cotización</p>
            <p class="p-h1 mt-1">Todavía no hay cotizaciones para este costeo.</p>
            <p class="p-meta mt-1">Completa lo que no viene del costeo. Productos y totales son automáticos.</p>
          </div>
          <div class="px-5 pt-4 pb-5 grid grid-cols-2 gap-x-3 gap-y-3">
            <div><label class="p-field-label">Vigencia (válida hasta)</label><input v-model="cotForm.valid_till" type="date" class="p-field" /></div>
            <div><label class="p-field-label">Moneda</label>
              <select v-model="cotForm.currency" class="p-field">
                <option v-for="c in cotDefaults.currencies" :key="c.name" :value="c.name">{{ c.name }}</option>
              </select>
            </div>
            <div><label class="p-field-label">Condiciones de pago</label>
              <select v-model="cotForm.payment_terms_template" class="p-field">
                <option value="">— Sin plantilla —</option>
                <option v-for="p in cotDefaults.payment_terms_templates" :key="p.name" :value="p.name">{{ p.name }}</option>
              </select>
            </div>
            <div><label class="p-field-label">Términos y condiciones</label>
              <select v-model="cotForm.tc_name" class="p-field">
                <option value="">— Sin términos —</option>
                <option v-for="t in terminosPara(cotDefaults.terms, 'venta', form.cliente, cotForm.tc_name)" :key="t.name" :value="t.name">{{ t.name }}</option>
              </select>
            </div>
            <div class="col-span-2"><label class="p-field-label">Lista de Precios</label>
              <select v-model="cotForm.selling_price_list" class="p-field">
                <option value="">— Sin lista —</option>
                <option v-for="pl in cotDefaults.price_lists" :key="pl.name" :value="pl.name">{{ pl.name }}</option>
              </select>
            </div>
            <div class="col-span-2"><label class="p-field-label">Impuestos y Cargos</label>
              <select v-model="cotForm.taxes_and_charges" class="p-field">
                <option value="">— Sin plantilla —</option>
                <option v-for="t in cotDefaults.tax_templates" :key="t.name" :value="t.name">{{ t.name }}</option>
              </select>
            </div>
            <div><label class="p-field-label">Email de contacto</label><input v-model="cotForm.contact_email" type="email" class="p-field" placeholder="correo@cliente.com" /></div>
            <div><label class="p-field-label">WhatsApp / Móvil</label><input v-model="cotForm.contact_mobile" type="tel" class="p-field" placeholder="+52 55 1234 5678" /></div>
          </div>
          <div class="px-5 py-4 border-t border-surface-border flex items-center justify-between gap-4 bg-zinc-50/60 rounded-b-xl">
            <div class="flex items-center gap-6">
              <div><p class="text-[10.5px] text-ink-light">Productos</p><p class="text-[14px] font-semibold tabular-nums">{{ productos.length }}</p></div>
              <div><p class="text-[10.5px] text-ink-light">Total venta</p><p class="text-[14px] font-semibold tabular-nums">{{ fmtC(totalVenta) }}</p></div>
            </div>
            <button type="button" :disabled="advancing" class="p-btn-primary" @click="guardarBorradorCotizacion">
              <svg v-if="advancing" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
              Guardar como borrador
            </button>
          </div>
        </div>

        <!-- Historial: cotizaciones de revisiones anteriores del costeo (la rechazada
             que llevó a "Editar Costeo" se queda en el costeo viejo). Solo lectura. -->
        <div v-if="related.quotations_historial.length" class="pt-4">
          <p class="p-eyebrow">Historial</p>
          <p class="p-meta mt-0.5 mb-2">Cotizaciones de revisiones anteriores de este costeo. Solo consulta.</p>
          <div class="p-panel divide-y divide-surface-border">
            <div v-for="q in related.quotations_historial" :key="q.name" class="flex items-center gap-3 px-4 py-3">
              <Icono nombre="documento" class="w-4 h-4 text-ink-xlight flex-shrink-0" />
              <div class="min-w-0">
                <p class="text-[13.5px] font-semibold text-ink-muted">{{ q.name }}</p>
                <p class="text-[11.5px] text-ink-light truncate">
                  {{ q.transaction_date }} · Costeo {{ q.costeo }}<template v-if="q.order_lost_reason"> · Motivo: {{ q.order_lost_reason }}</template>
                </p>
              </div>
              <span class="flex-shrink-0" :class="q.status === 'Lost' ? 'p-pill-bad' : (q.docstatus === 2 ? 'p-pill-off' : (q.docstatus === 1 ? 'p-pill-ok' : 'p-pill-wait'))">{{ q.status === 'Lost' ? 'Rechazada' : (q.docstatus === 2 ? 'Cancelada' : (q.docstatus === 1 ? 'Validada' : 'Borrador')) }}</span>
              <p class="ml-auto text-[13.5px] font-semibold text-ink-muted tabular-nums flex-shrink-0">{{ fmtC(q.grand_total) }}</p>
              <button data-libre type="button" class="doc-action flex-shrink-0" @click="openPdf('Quotation', q.name)"><Icono nombre="documento" class="w-3.5 h-3.5" />Ver PDF</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ══════════ STEP 2 · VENDER ══════════ -->
    <div v-else-if="activeStep === 2" class="px-5 lg:px-8 py-6 pb-20" v-solo-lectura="soloLecturaPaso">
      <!-- Solo lectura: el usuario tiene esta etapa en "ver" (accesos por vista). -->
      <p v-if="soloLecturaPaso" class="max-w-5xl mx-auto mb-4 text-[12.5px] text-ink-muted bg-surface-raised rounded-lg px-3 py-2">
        <b class="text-ink">Solo lectura.</b> Puedes consultar esta etapa; la captura la hace quien la tiene asignada.
      </p>
      <div class="max-w-[1320px] mx-auto space-y-3">
        <div v-if="related.sales_orders.length" class="flex items-end justify-between gap-3 mb-1">
          <div>
            <p class="p-eyebrow">Órdenes de venta</p>
            <p class="p-meta mt-0.5">{{ related.sales_orders.length }} {{ related.sales_orders.length === 1 ? "orden" : "órdenes" }} de este costeo</p>
          </div>
        </div>

        <!-- Generar nueva OV: a nivel costeo, no dentro de una orden en particular --
             toma como base la última OV validada (o la que se elija abajo si hay
             varias) y solo pide ajustar cantidades; el precio ya viene acordado.
             Oculto mientras esa OV base no tenga precio acordado fijado; si lo
             tiene pero ya venció, el botón avisa en vez de desaparecer -- quien
             tenga rol CEO puede destrabarlo desde el propio modal. -->
        <div v-if="nuevaOvGate.show" class="p-panel px-4 py-3.5 flex items-center justify-between gap-4" :class="nuevaOvGate.vencido ? '!border-amber-200 !bg-amber-50/50' : ''">
          <div class="flex items-start gap-3 min-w-0">
            <span class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" :class="nuevaOvGate.vencido ? 'bg-amber-100 text-amber-700' : 'bg-brand-50 text-brand-600'">
              <Icono :nombre="nuevaOvGate.vencido ? 'reloj' : 'actualizar'" class="w-4 h-4" />
            </span>
            <div class="min-w-0">
              <p class="text-[13.5px] font-semibold" :class="nuevaOvGate.vencido ? 'text-amber-800' : 'text-ink'">
                {{ nuevaOvGate.vencido ? 'Precio acordado caducado' : 'Generar nueva OV' }}
              </p>
              <p class="text-[12px] mt-0.5" :class="nuevaOvGate.vencido ? 'text-amber-700' : 'text-ink-muted'">
                <template v-if="nuevaOvGate.vencido">
                  El precio acordado para un nuevo pedido de este cliente ya venció.
                  <template v-if="nuevaOvGate.esCeo">Tienes permiso para aprobar precios: puedes generar la OV de todos modos, o actualízalo desde "Fijar Precio" en la cotización.</template>
                  <template v-else>Pide a alguien que apruebe precios que la genere, o actualiza el precio desde "Fijar Precio" en la cotización.</template>
                </template>
                <template v-else>Pedido recurrente del mismo cliente: crea otra Orden de Venta con los mismos productos, solo ajustando la cantidad -- sin volver a cotizar. Usa el precio acordado y, si un producto no lo tiene, el último precio con que se le vendió.</template>
              </p>
            </div>
          </div>
          <button
            type="button"
            class="p-btn flex-shrink-0"
            :class="nuevaOvGate.vencido ? 'text-amber-800 bg-amber-100 hover:bg-amber-200' : 'text-white bg-brand-500 hover:bg-brand-600'"
            @click="openNuevaOvModal()"
          ><Icono v-if="!nuevaOvGate.vencido" nombre="mas" class="w-3.5 h-3.5" :grosor="2.2" />{{ nuevaOvGate.vencido ? 'Precio caducado -- revisar' : 'Generar nueva OV' }}</button>
        </div>

        <!-- Lista de órdenes de venta del costeo (acordeón, mismo patrón que Cotizar) -->
        <div v-for="so in related.sales_orders" :key="so.name" class="group p-panel" :id="`doc-hl-${so.name}`" :class="{ 'doc-highlight-flash': highlightTarget === so.name }">
          <div class="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-zinc-50 rounded-xl transition-colors" :class="expandedSOName === so.name ? 'rounded-b-none' : ''" @click="toggleSalesOrder(so)">
            <svg class="w-4 h-4 text-ink-light flex-shrink-0 transition-transform" :class="expandedSOName === so.name ? 'rotate-90' : ''" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
            <Icono nombre="factura" class="w-4 h-4 text-ink-light flex-shrink-0" />
            <p class="text-[14px] font-semibold text-ink">{{ so.name }}</p>
            <span v-if="activeSOName === so.name" class="p-pill-now">OV activa</span>
            <span :class="so.docstatus === 2 ? 'p-pill-off' : (so.docstatus === 1 ? 'p-pill-ok' : 'p-pill-wait')">{{ so.docstatus === 2 ? 'Cancelada' : (so.docstatus === 1 ? 'Validada' : 'Borrador') }}</span>
            <div class="ml-auto text-right">
              <p class="text-[10.5px] text-ink-light">Total</p>
              <p class="text-[14px] font-semibold text-ink tabular-nums">{{ fmtC(so.grand_total) }}</p>
            </div>
            <button v-if="so.docstatus !== 2" type="button" class="opacity-0 group-hover:opacity-100 w-7 h-7 flex items-center justify-center rounded-md hover:bg-red-50 hover:text-red-500 text-ink-xlight transition-all flex-shrink-0" title="Eliminar orden de venta" @click.stop="openDeleteSO(so.name)">
              <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
            </button>
          </div>

          <div v-if="expandedSOName === so.name" class="border-t border-surface-border">
            <!-- Tallas del pedido, a todo el ancho y antes que los datos: es lo que más
                 se captura en la OV y con columnas por talla se lee de un vistazo. -->
            <div v-if="hayTallasOV(so)" class="p-5 border-b border-surface-border bg-zinc-50/70 space-y-6">
              <!-- Desglose por talla del PRODUCTO PRINCIPAL (tallas normales). La suma
                   debe ser exacta a la cantidad del producto (la del costeo); al guardar
                   se escribe como lista debajo de la descripción y la Orden de
                   Manufactura lo toma para su desglose de tallas (api/tallas_ov.py).
                   Solo las tallas de uso común del tipo elegido (ver tallasRegulares):
                   las demás son tallas extra y van abajo, con su propio precio. Se
                   puede repartir entre Caballero y Dama (un bloque por género). -->
              <div v-if="so.docstatus === 0 && soDesgloseForm.length">
                <div class="flex items-end justify-between gap-3 mb-3">
                  <div>
                    <p class="p-eyebrow">Desglose por talla · tallas regulares</p>
                    <p class="p-meta mt-0.5">Debe sumar exacto la cantidad del producto para validar. Se guarda con «Guardar cambios» o «Validar orden».</p>
                  </div>
                </div>
                <div class="rounded-xl bg-white border border-surface-border divide-y divide-surface-border">
                  <div v-for="d in soDesgloseForm" :key="d.row" class="px-4 py-3">
                    <div class="flex items-center gap-2.5">
                      <span class="flex-1 min-w-0 text-[13px] font-medium text-ink truncate" :title="d.item_name">{{ d.item_name }}</span>
                      <span class="tabular-nums w-24 justify-center" :class="sumaDesglose(d) === d.qty ? 'p-pill-ok' : 'p-pill-wait'">{{ sumaDesglose(d) }} / {{ d.qty }}</span>
                    </div>
                    <div v-for="(b, bi) in d.bloques" :key="bi" class="mt-3">
                      <div class="flex items-center gap-2.5 flex-wrap">
                        <select v-model="b.genero" class="p-field h-8 w-36 text-[12.5px]" @change="b.grupo = ''; limpiarDesglose(d)">
                          <option value="">Género…</option>
                          <option v-for="g in generosLibres(d, b)" :key="g" :value="g">{{ g }}</option>
                        </select>
                        <select v-model="b.grupo" class="p-field h-8 w-72 max-w-full text-[12.5px]" :disabled="!b.genero" @change="limpiarDesglose(d)">
                          <option value="">Tipo de talla…</option>
                          <option v-for="g in gruposDeGenero(b.genero)" :key="g.name" :value="g.name">{{ g.talla }}</option>
                        </select>
                        <button v-if="d.bloques.length > 1" type="button" class="h-8 w-8 flex items-center justify-center rounded-md text-ink-light hover:bg-red-50 hover:text-red-500" title="Quitar este género" @click="d.bloques.splice(bi, 1); limpiarDesglose(d)">
                          <Icono nombre="x" class="w-3.5 h-3.5" :grosor="2" />
                        </button>
                      </div>
                      <div v-if="b.grupo" class="mt-2 flex flex-wrap items-end gap-2">
                        <label v-for="t in tallasRegulares(d, b)" :key="t.name" class="w-[68px]">
                          <span class="block text-[11.5px] font-medium text-ink-muted text-center mb-1">{{ t.talla }}</span>
                          <input v-model.number="d.valores[t.name]" type="number" min="0" step="1" class="p-field h-8 px-1.5 text-[13px] text-center tabular-nums" />
                        </label>
                        <button v-if="hayTallasOcultas(d, b)" type="button" class="add-link h-8" @click="b.todas = true">Ver todas las tallas</button>
                        <button v-else-if="b.todas" type="button" class="add-link h-8" @click="b.todas = false; limpiarDesglose(d)">Solo las comunes</button>
                      </div>
                    </div>
                    <button v-if="d.bloques.length < 2" type="button" class="add-link mt-3" @click="d.bloques.push({ genero: generosLibres(d)[0] || '', grupo: '' })">
                      <Icono nombre="mas" class="w-3.5 h-3.5" :grosor="2.2" />Agregar {{ generosLibres(d)[0] || "otro género" }}
                    </button>
                  </div>
                </div>
              </div>
              <!-- OV validada: el desglose ya no se edita, pero se sigue viendo. -->
              <div v-else-if="so.docstatus === 1 && soDesgloseForm.some((d) => (d.filas || []).length)">
                <p class="p-eyebrow mb-2">Desglose por talla · tallas regulares</p>
                <div class="rounded-xl bg-white border border-surface-border divide-y divide-surface-border">
                  <div v-for="d in soDesgloseForm.filter((x) => (x.filas || []).length)" :key="d.row" class="px-4 py-3">
                    <div class="flex items-center gap-3">
                      <span class="flex-1 min-w-0 text-[13px] font-medium text-ink truncate" :title="d.item_name">{{ d.item_name }}</span>
                      <span class="p-pill-ok tabular-nums flex-shrink-0">{{ sumaDesglose(d) }} / {{ d.qty }}</span>
                    </div>
                    <div class="flex flex-wrap gap-1.5 mt-2">
                      <span v-for="f in d.filas" :key="f.talla" class="p-pill-off">{{ f.etiqueta }} <b class="font-semibold text-ink">{{ f.qty }}</b></span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Cantidades confirmadas por talla -- solo aquí (OV), nunca en la
                   Cotización: es en esta etapa donde el cliente confirma las
                   cantidades oficiales de cada variante, o las quita si no las
                   quiere. Se refleja en el Costeo hasta Validar esta orden. -->
              <div v-if="so.docstatus === 0 && variantesDelCosteo.length">
                <div class="flex items-end justify-between gap-3 mb-3">
                  <div>
                    <p class="p-eyebrow">Tallas extra</p>
                    <p class="p-meta mt-0.5">Piezas que confirmó el cliente por talla. Con 0 se quita del pedido. Se guarda con «Guardar cambios» o «Validar orden».</p>
                  </div>
                </div>
                <div v-if="soVariantesLoading" class="p-meta py-2 text-center">Cargando…</div>
                <div v-else class="space-y-3">
                  <div v-for="g in soVariantesGrupos" :key="g.base" class="rounded-xl bg-white border border-surface-border">
                    <p class="px-4 pt-3 pb-2 text-[13px] font-medium text-ink truncate border-b border-surface-border" :title="g.base">{{ g.nombre }}</p>
                    <div class="divide-y divide-surface-border">
                      <!-- Cada talla de la variante con sus piezas; el total es la suma. Se
                           puede agregar cualquier talla NO regular de su tipo (ej. 5XL): entra
                           en la línea de esta variante, con su mismo precio. -->
                      <div v-for="v in g.variantes" :key="v.item_code" class="px-4 py-3">
                        <div class="flex items-center gap-3">
                          <p class="flex-1 min-w-0 text-[13px] font-medium truncate" :class="totalVariante(v) ? 'text-ink' : 'text-ink-light'" :title="v.talla_grupo_label">{{ v.talla_grupo_label }}</p>
                          <span class="tabular-nums" :class="totalVariante(v) ? 'p-pill-ok' : 'p-pill-off'">{{ totalVariante(v) }} pzas</span>
                        </div>
                        <div class="mt-2 flex flex-wrap items-end gap-2">
                          <label v-for="t in v.codigos" :key="t.code" class="w-[68px]">
                            <span class="block text-[11.5px] font-medium text-ink-muted text-center mb-1">{{ t.label }}</span>
                            <input v-model.number="v.desglose[t.code]" type="number" min="0" step="1" class="p-field h-8 px-1.5 text-[13px] text-center tabular-nums" />
                          </label>
                          <select v-if="tallasExtraDisponibles(v).length" class="p-field h-8 w-44 text-[12.5px]" value="" @change="agregarTallaVariante(v, $event.target.value); $event.target.value = ''">
                            <option value="">+ Agregar talla</option>
                            <option v-for="t in tallasExtraDisponibles(v)" :key="t.name" :value="t.name">{{ t.talla }}</option>
                          </select>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <!-- OV validada: las tallas extra ya no se editan, pero se siguen viendo. -->
              <div v-else-if="so.docstatus === 1 && soVariantesForm.length">
                <p class="p-eyebrow mb-2">Tallas extra</p>
                <div class="space-y-3">
                  <div v-for="g in soVariantesGrupos" :key="g.base" class="rounded-xl bg-white border border-surface-border">
                    <p class="px-4 pt-3 pb-2 text-[13px] font-medium text-ink truncate border-b border-surface-border" :title="g.base">{{ g.nombre }}</p>
                    <div class="divide-y divide-surface-border">
                      <div v-for="v in g.variantes" :key="v.item_code" class="px-4 py-3 flex flex-wrap items-center gap-x-6 gap-y-2">
                        <p class="w-48 min-w-0 text-[13px] font-medium text-ink truncate" :title="v.talla_grupo_label">{{ v.talla_grupo_label }}</p>
                        <p class="w-24 text-[13px]"><span class="text-[11.5px] text-ink-muted">Total</span> <b class="font-semibold tabular-nums">{{ v.qty }}</b></p>
                        <div v-if="tallasConPiezas(v).length" class="flex-1 flex flex-wrap items-center gap-1.5 pl-6 border-l border-surface-border">
                          <span v-for="t in tallasConPiezas(v)" :key="t.code" class="p-pill-off">{{ t.label }} <b class="font-semibold text-ink">{{ t.qty }}</b></span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

          <div class="grid lg:grid-cols-[360px_minmax(0,1fr)]">
            <!-- Izquierda: campos manuales y acciones -->
            <div class="min-w-0 p-5 space-y-5 lg:border-r border-surface-border">
              <!-- Cancelada: se queda como historial, solo lectura y nunca como OV activa. -->
              <div v-if="so.docstatus === 2" class="rounded-xl bg-zinc-50 border border-surface-border px-3.5 py-3">
                <p class="text-[12.5px] font-semibold text-ink flex items-center gap-1.5"><Icono nombre="alerta" class="w-3.5 h-3.5" />Orden de venta cancelada</p>
                <p v-if="so.motivo_cancelacion" class="text-[12px] text-ink-muted mt-0.5">{{ so.motivo_cancelacion }}</p>
              </div>
              <button v-else-if="activeSOName !== so.name" type="button" class="p-btn w-full h-auto min-h-[2.25rem] py-2 whitespace-normal text-[12.5px] text-brand-700 bg-brand-50 hover:bg-brand-100" @click="setActiveSO(so.name)">Usar como OV activa para Producir/Enviar/Facturar/Reportar</button>

              <div>
                <p class="p-eyebrow">Datos de la orden de venta</p>
                <p class="p-meta mt-0.5 mb-3">Completa lo que no viene del costeo. Productos y totales son automáticos.</p>
                <div class="grid grid-cols-2 gap-x-3 gap-y-3">
                  <div class="col-span-2">
                    <label class="p-field-label">Tiempo de entrega (semanas)</label>
                    <div class="flex items-center gap-3">
                      <input v-model.number="soForm.delivery_weeks" type="number" min="1" step="1" placeholder="Ej: 3" class="p-field w-28 tabular-nums" :disabled="so.docstatus !== 0" @input="onDeliveryWeeksChange" />
                      <p class="text-[11.5px] text-ink-light">{{ soForm.delivery_date ? `Vigencia: ${soForm.delivery_date}` : 'Captura las semanas para calcular la fecha' }}</p>
                    </div>
                  </div>
                  <div class="col-span-2"><label class="p-field-label">Condiciones de pago</label>
                    <select v-model="soForm.payment_terms_template" class="p-field" :disabled="so.docstatus !== 0">
                      <option value="">— Sin plantilla —</option>
                      <option v-for="p in cotDefaults.payment_terms_templates" :key="p.name" :value="p.name">{{ p.name }}</option>
                    </select>
                  </div>
                  <div class="col-span-2"><label class="p-field-label">Términos y condiciones</label>
                    <select v-model="soForm.tc_name" class="p-field" :disabled="so.docstatus !== 0">
                      <option value="">— Sin términos —</option>
                      <option v-for="t in terminosPara(cotDefaults.terms, 'venta', form.cliente, soForm.tc_name)" :key="t.name" :value="t.name">{{ t.name }}</option>
                    </select>
                  </div>
                  <div class="col-span-2">
                    <label class="p-field-label">OC del Cliente <span v-if="ocClienteEsArchivo" class="text-red-500">*</span></label>
                    <!-- Con el campo disponible (patch v0_2_56) la OC del cliente es el
                         ARCHIVO y es obligatoria; en un sitio que todavía no lo corrió se
                         sigue capturando el número, para no dejar el paso sin el dato. -->
                    <OcClienteAdjunto
                      v-if="ocClienteEsArchivo"
                      v-model="soForm.oc_cliente_archivo"
                      :solo-lectura="so.docstatus !== 0" :subiendo="ocClienteSubiendo"
                      @archivo="(ev) => subirOcCliente(ev, 'Sales Order', so.name)"
                      @quitar="quitarOcCliente('Sales Order', so.name)"
                    />
                    <input v-model="soForm.po_no" type="text" class="p-field" :class="{ 'mt-2': ocClienteEsArchivo }" :disabled="so.docstatus !== 0"
                           :placeholder="ocClienteEsArchivo ? 'Folio de la OC del cliente (opcional)' : 'Número de orden de compra'" />
                  </div>
                  <div><label class="p-field-label">Moneda</label>
                    <select v-model="soForm.currency" class="p-field" :disabled="so.docstatus !== 0">
                      <option v-for="c in cotDefaults.currencies" :key="c.name" :value="c.name">{{ c.name }}</option>
                    </select>
                  </div>
                  <div><label class="p-field-label">Lista de Precios</label>
                    <select v-model="soForm.selling_price_list" class="p-field" :disabled="so.docstatus !== 0">
                      <option value="">— Sin lista —</option>
                      <option v-for="pl in cotDefaults.price_lists" :key="pl.name" :value="pl.name">{{ pl.name }}</option>
                    </select>
                  </div>
                  <div class="col-span-2"><label class="p-field-label">Impuestos y Cargos</label>
                    <select v-model="soForm.taxes_and_charges" class="p-field" :disabled="so.docstatus !== 0">
                      <option value="">— Sin plantilla —</option>
                      <option v-for="t in cotDefaults.tax_templates" :key="t.name" :value="t.name">{{ t.name }}</option>
                    </select>
                  </div>
                  <div class="col-span-2"><label class="p-field-label">Email de contacto</label><input v-model="soForm.contact_email" type="email" class="p-field" :disabled="so.docstatus !== 0" placeholder="correo@cliente.com" /></div>
                  <div class="col-span-2"><label class="p-field-label">WhatsApp / Móvil</label><input v-model="soForm.contact_mobile" type="tel" class="p-field" :disabled="so.docstatus !== 0" placeholder="+52 55 1234 5678" /></div>
                </div>
              </div>

              <div class="space-y-2">
                <template v-if="so.docstatus === 0">
                  <FranjaAprobacion
                    doctype="Sales Order" :name="so.name" :guardar="guardarCambiosOrdenVenta"
                    @estado="(s) => (aprobPanel[so.name] = s)" @cambio="trasAprobacionVenta"
                  />
                  <button v-if="validaDirecto(so.name) && !enAprobacion(so.name)" type="button" :disabled="advancing" class="p-btn-primary w-full" @click="validarDoc('Sales Order', so.name)">
                    <Icono nombre="check-circulo" class="w-4 h-4" />Validar orden
                  </button>
                  <button type="button" :disabled="advancing" class="p-btn-secondary w-full" @click="guardarCambiosOrdenVenta">Guardar cambios</button>
                </template>
                <div class="flex flex-wrap gap-1.5 pt-1">
                  <button v-if="so.docstatus === 1" type="button" class="doc-action" @click="openSend('Sales Order', so.name, so.contact_email, so.contact_mobile)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>Enviar</button>
                  <button data-libre v-if="so.docstatus !== 2" type="button" class="doc-action" @click="downloadPdf('Sales Order', so.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/></svg>Descargar</button>
                  <button data-libre v-if="so.docstatus !== 2" type="button" class="doc-action" @click="printDocView('Sales Order', so.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2z"/></svg>Imprimir</button>
                  <button type="button" class="doc-action" @click="openAssign('Sales Order', so.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>Asignar</button>
                  <a class="doc-action" :href="`/app/sales-order/${so.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>Abrir en ERPNext</a>
                </div>
              </div>

              <!-- Cancelar: solo quien valida documentos. Pide motivo; la OV se queda como historial. -->
              <div v-if="so.docstatus === 1 && permisosAprob.puede_aprobar" class="pt-4 border-t border-surface-border">
                <button type="button" class="p-btn w-full h-8 text-[12.5px] font-medium text-red-600 border border-red-200 hover:bg-red-50" @click="abrirCancelarOV(so)">Cancelar orden de venta</button>
              </div>

              <div class="pt-4 border-t border-surface-border">
                <AttachmentsPanel doctype="Sales Order" :docname="so.name" />
              </div>
            </div>

            <!-- Derecha: vista previa del PDF -->
            <div class="min-w-0 border-t lg:border-t-0 border-surface-border flex flex-col">
              <div class="flex items-center justify-between px-4 py-2 border-b border-surface-border">
                <p class="p-eyebrow">Vista previa</p>
                <button data-libre v-if="so.docstatus !== 2" type="button" class="doc-action" @click="openPdf('Sales Order', so.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 8V4m0 0h4M4 4l5 5m11-5h-4m4 0v4m0-4l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5h-4m4 0v-4m0 4l-5-5"/></svg>Ampliar</button>
              </div>
              <!-- Crece hasta el final del formulario de la izquierda (nunca menos de 70vh):
                   el iframe va absoluto y escalado a 0.7, así llena el contenedor sin
                   depender de una altura fija. -->
              <div class="relative flex-1 bg-zinc-50 rounded-br-xl overflow-hidden" style="min-height: 70vh;">
                <!-- ERPNext no imprime documentos cancelados: en su lugar, un aviso. -->
                <div v-if="so.docstatus === 2" class="absolute inset-0 flex items-center justify-center p-6 text-center">
                  <p class="p-meta">Orden de venta cancelada: sin vista previa.</p>
                </div>
                <iframe v-else :key="previewKey" :src="printUrl('Sales Order', so.name)" class="absolute top-0 left-0" style="width: 143%; height: 143%; transform: scale(0.7); transform-origin: top left; border: 0;" title="Vista previa de la orden de venta"></iframe>
              </div>
            </div>
          </div>
          </div>
        </div>

        <!-- Crear la orden de venta: la primera, o una nueva si todas las anteriores
             están canceladas (esas se quedan arriba como historial). -->
        <div v-if="!soVivas.length" class="p-panel max-w-[560px] mx-auto mt-4">
          <div class="px-5 pt-5">
            <p class="p-eyebrow">Nueva orden de venta</p>
            <p class="p-h1 mt-1">{{ related.sales_orders.length ? "Todas las órdenes de venta de este costeo están canceladas." : "Todavía no hay órdenes de venta para este costeo." }}</p>
            <p class="p-meta mt-1">Completa lo que no viene del costeo. Productos y totales son automáticos.</p>
          </div>
          <div class="px-5 pt-4 pb-5 grid grid-cols-2 gap-x-3 gap-y-3">
            <div class="col-span-2">
              <label class="p-field-label">Tiempo de entrega (semanas)</label>
              <div class="flex items-center gap-3">
                <input v-model.number="soForm.delivery_weeks" type="number" min="1" step="1" placeholder="Ej: 3" class="p-field w-28 tabular-nums" @input="onDeliveryWeeksChange" />
                <p class="text-[11.5px] text-ink-light">{{ soForm.delivery_date ? `Vigencia: ${soForm.delivery_date}` : 'Captura las semanas para calcular la fecha' }}</p>
              </div>
            </div>
            <div><label class="p-field-label">Condiciones de pago</label>
              <select v-model="soForm.payment_terms_template" class="p-field">
                <option value="">— Sin plantilla —</option>
                <option v-for="p in cotDefaults.payment_terms_templates" :key="p.name" :value="p.name">{{ p.name }}</option>
              </select>
            </div>
            <div><label class="p-field-label">Términos y condiciones</label>
              <select v-model="soForm.tc_name" class="p-field">
                <option value="">— Sin términos —</option>
                <option v-for="t in terminosPara(cotDefaults.terms, 'venta', form.cliente, soForm.tc_name)" :key="t.name" :value="t.name">{{ t.name }}</option>
              </select>
            </div>
            <div class="col-span-2">
              <label class="p-field-label">OC del Cliente <span v-if="ocClienteEsArchivo" class="text-red-500">*</span></label>
              <OcClienteAdjunto
                v-if="ocClienteEsArchivo"
                v-model="soForm.oc_cliente_archivo"
                :subiendo="ocClienteSubiendo"
                @archivo="(ev) => subirOcCliente(ev, 'Costeo', docName)"
                @quitar="quitarOcCliente('Costeo', docName)"
              />
              <input v-model="soForm.po_no" type="text" class="p-field" :class="{ 'mt-2': ocClienteEsArchivo }"
                     :placeholder="ocClienteEsArchivo ? 'Folio de la OC del cliente (opcional)' : 'Número de orden de compra'" />
            </div>
            <div><label class="p-field-label">Moneda</label>
              <select v-model="soForm.currency" class="p-field">
                <option v-for="c in cotDefaults.currencies" :key="c.name" :value="c.name">{{ c.name }}</option>
              </select>
            </div>
            <div><label class="p-field-label">Lista de Precios</label>
              <select v-model="soForm.selling_price_list" class="p-field">
                <option value="">— Sin lista —</option>
                <option v-for="pl in cotDefaults.price_lists" :key="pl.name" :value="pl.name">{{ pl.name }}</option>
              </select>
            </div>
            <div class="col-span-2"><label class="p-field-label">Impuestos y Cargos</label>
              <select v-model="soForm.taxes_and_charges" class="p-field">
                <option value="">— Sin plantilla —</option>
                <option v-for="t in cotDefaults.tax_templates" :key="t.name" :value="t.name">{{ t.name }}</option>
              </select>
            </div>
            <div><label class="p-field-label">Email de contacto</label><input v-model="soForm.contact_email" type="email" class="p-field" placeholder="correo@cliente.com" /></div>
            <div><label class="p-field-label">WhatsApp / Móvil</label><input v-model="soForm.contact_mobile" type="tel" class="p-field" placeholder="+52 55 1234 5678" /></div>
          </div>
          <div class="px-5 py-4 border-t border-surface-border flex items-center justify-between gap-4 bg-zinc-50/60 rounded-b-xl">
            <div class="flex items-center gap-6">
              <div><p class="text-[10.5px] text-ink-light">Productos</p><p class="text-[14px] font-semibold tabular-nums">{{ productos.length }}</p></div>
              <div><p class="text-[10.5px] text-ink-light">Total venta</p><p class="text-[14px] font-semibold tabular-nums">{{ fmtC(totalVenta) }}</p></div>
            </div>
            <div class="text-right">
              <button type="button" :disabled="advancing || !quotValidated" class="p-btn-primary" @click="guardarBorradorOrdenVenta">
                <svg v-if="advancing" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                Guardar como borrador
              </button>
              <p v-if="!quotValidated" class="text-[11px] text-ink-light mt-1.5">Primero valida la cotización.</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal: Generar nueva Orden de Venta (a partir de una ya validada, mismo precio acordado) -->
    <div v-if="nuevaOvModal.open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="nuevaOvModal.open = false">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md p-5">
        <p class="text-[16px] font-semibold text-ink">Generar nueva OV</p>
        <p class="p-meta mt-0.5 mb-4">Crea otra Orden de Venta con los mismos artículos -- ajusta la cantidad de cada uno, sin volver a cotizar. Cada precio es el acordado o, si no hay, el último con que se le vendió al cliente.</p>

        <div v-if="sosValidadas.length > 1" class="mb-4">
          <label class="p-field-label">Basado en</label>
          <select class="p-field" :value="nuevaOvModal.so?.name" @change="cambiarBaseNuevaOv($event.target.value)">
            <option v-for="so in sosValidadas" :key="so.name" :value="so.name">{{ so.name }} · {{ fmtC(so.grand_total) }}</option>
          </select>
        </div>

        <div v-if="nuevaOvModal.loading" class="py-6 text-center p-meta">Cargando…</div>
        <template v-else>
          <div v-if="nuevaOvModal.status && !nuevaOvModal.status.puede_generar" class="rounded-xl px-3.5 py-3 mb-4" :class="nuevaOvModal.status.es_ceo ? 'bg-amber-50 border border-amber-100' : 'bg-red-50 border border-red-100'">
            <p class="text-[12.5px] font-semibold" :class="nuevaOvModal.status.es_ceo ? 'text-amber-800' : 'text-red-700'">
              {{ nuevaOvModal.status.vencido ? 'El precio acordado ya venció' : 'Falta fijar el precio de algún artículo' }}
            </p>
            <p class="text-[12px] mt-0.5" :class="nuevaOvModal.status.es_ceo ? 'text-amber-700' : 'text-red-600'">
              <template v-if="nuevaOvModal.status.es_ceo">Tienes permiso para aprobar precios: puedes generarla de todos modos.</template>
              <template v-else-if="nuevaOvModal.status.vencido">Alguien que apruebe precios debe generar esta OV, o vuelve a "Fijar Precio" desde la cotización.</template>
              <template v-else>Usa "Fijar Precio" desde la cotización para los artículos que falten.</template>
            </p>
          </div>

          <div class="mb-5 max-h-64 overflow-y-auto rounded-xl border border-surface-border divide-y divide-surface-border">
            <div v-for="row in nuevaOvModal.items" :key="row.item_code" class="flex items-center gap-3 px-3.5 py-2.5">
              <div class="flex-1 min-w-0">
                <p class="text-[13px] font-medium text-ink truncate">{{ row.item_name || row.item_code }}</p>
                <p class="text-[11.5px] text-ink-light tabular-nums">
                  {{ fmtC(row.rate) }} c/u
                  <template v-if="!row.tiene_precio_acordado"> · último precio vendido</template>
                  <template v-else-if="!row.vigente"> · <span class="text-amber-700">precio acordado vencido {{ row.valid_upto }}</span></template>
                  <template v-else> · <span class="text-emerald-700">precio acordado</span></template>
                </p>
              </div>
              <div>
                <label class="text-[10.5px] text-ink-light block text-right mb-0.5">Cantidad a generar</label>
                <input v-model.number="row.qty" type="number" min="1" step="1" class="p-field text-right tabular-nums" style="width: 100px;" />
              </div>
            </div>
          </div>

          <div class="flex justify-end gap-2">
            <button type="button" class="p-btn-ghost" @click="nuevaOvModal.open = false">Cancelar</button>
            <button type="button" :disabled="nuevaOvModal.generating || (nuevaOvModal.status && !nuevaOvModal.status.puede_generar && !nuevaOvModal.status.es_ceo)" class="p-btn-primary" @click="confirmarNuevaOv">
              {{ nuevaOvModal.generating ? "Generando…" : "Generar nueva OV" }}
            </button>
          </div>
        </template>
      </div>
    </div>

    <!-- ══════════ STEP 3 · ALTA DE PRODUCTOS (artículos pendientes) ══════════ -->
    <!-- Fijo a nivel Costeo -- NO se filtra por OV activa (a diferencia de Producir/
         Enviar/Facturar/Reportar): cómo se fabrica una prenda no cambia entre réplicas
         de pedido, solo la cantidad -- por eso no lleva ActiveSOSelector. -->
    <div v-else-if="activeStep === 3" class="p-5 pb-20 max-w-5xl mx-auto w-full space-y-4" v-solo-lectura="soloLecturaPaso">
      <!-- Solo lectura: el usuario tiene esta etapa en "ver" (accesos por vista). -->
      <p v-if="soloLecturaPaso" class="max-w-5xl mx-auto mb-4 text-[12.5px] text-ink-muted bg-surface-raised rounded-lg px-3 py-2">
        <b class="text-ink">Solo lectura.</b> Puedes consultar esta etapa; la captura la hace quien la tiene asignada.
      </p>
      <div class="bg-white rounded-xl border border-surface-border p-4">
        <p class="text-sm font-semibold text-ink mb-1">Alta de Productos</p>
        <p class="text-[12.5px] text-ink-muted">Ya con la Orden de Venta confirmada: registra los materiales/servicios que quedaron como texto libre -- esto ya no se captura en Costear, para no perder tiempo en un pedido que todavía podría no concretarse. El siguiente paso, "Flujo de Producción", es donde se arma el proceso completo.</p>
      </div>

      <div v-if="pendientesAdvertencias.length" class="bg-amber-50/40 rounded-xl border border-amber-200 p-3">
        <p v-for="(a, i) in pendientesAdvertencias" :key="i" class="text-[12px] text-amber-700 flex items-start gap-2">
          <svg class="w-4 h-4 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>
          <span>{{ a }}</span>
        </p>
      </div>

      <div v-if="pendientesArticulos.length" class="bg-amber-50/40 rounded-xl border border-amber-200 p-4">
        <div class="flex items-center justify-between mb-1">
          <p class="text-sm font-semibold text-ink">Artículos pendientes de materializar</p>
          <span class="text-[11px] font-medium text-amber-700 bg-amber-100 rounded-full px-2 py-0.5">{{ pendientesArticulos.length }} pendiente{{ pendientesArticulos.length === 1 ? '' : 's' }}</span>
        </div>
        <p class="text-[12px] text-ink-muted mb-3">Se capturaron como texto libre en el costeo. Resuélvelos (vincula uno existente o crea uno nuevo) antes de preparar producción.</p>
        <div class="space-y-2">
          <div v-for="g in pendientesArticulos" :key="g.row_type + '::' + g.texto" class="flex items-center gap-3 bg-white rounded-lg border border-surface-border p-3">
            <span class="text-[11px] font-semibold px-2 py-0.5 rounded-full flex-shrink-0" :class="tipoBadgeClass(g.row_type)">{{ tipoLabel(g.row_type) }}</span>
            <div class="flex-1 min-w-0">
              <p class="text-[13px] font-medium text-ink truncate">{{ g.texto }}</p>
              <p class="text-[11px] text-ink-light truncate">Usado en: {{ g.productos.join(', ') }}<span v-if="g.supplier"> · Proveedor: {{ g.supplier }}</span></p>
            </div>
            <div class="w-52 flex-shrink-0">
              <div v-if="g._suggested && !g._suggestedDismissed" class="flex items-center gap-1.5">
                <button
                  class="flex-1 min-w-0 text-left text-[12px] px-2.5 py-1.5 rounded-lg border border-brand-200 bg-brand-50 hover:bg-brand-100 transition-colors"
                  :title="g._suggested.item_code"
                  @click="resolverArticuloExistente(g, g._suggested.item_code)"
                >
                  <span class="text-[10px] font-semibold text-brand-600 uppercase tracking-wide block leading-tight">Sugerido</span>
                  <span class="text-ink truncate block">{{ g._suggested.label }}</span>
                </button>
                <button class="text-ink-muted hover:text-ink flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-lg hover:bg-surface-raised" title="Buscar otro" @click="g._suggestedDismissed = true">✕</button>
              </div>
              <div v-else class="flex items-center gap-1.5">
                <LinkInput v-model="g._vincularValor" doctype="Item" :filters="ROW_TYPE_ITEM_FILTERS[g.row_type] || []" placeholder="Vincular existente…" class="flex-1 min-w-0" />
                <button
                  v-if="g._vincularValor"
                  type="button"
                  class="flex-shrink-0 text-[11px] font-semibold text-white bg-brand-500 hover:bg-brand-600 rounded-lg px-2.5 py-2"
                  title="Confirmar vinculación"
                  @click="confirmarVincularExistente(g)"
                >Vincular</button>
              </div>
            </div>
            <button class="doc-action justify-center flex-shrink-0" @click="openArticuloModal(g)">+ Crear</button>
          </div>
        </div>
      </div>

      <!-- Nada pendiente: los materiales/servicios del costeo ya resuelven todos a un
           Item real (se capturaron con código, se materializaron antes, o el costeo
           partió de una plantilla). No hay nada que hacer aquí -- se confirma y se
           deja un botón explícito para seguir, en vez de una pantalla en blanco. -->
      <div v-if="!pendientesArticulos.length && !pendientesAdvertencias.length" class="bg-white rounded-xl border border-surface-border p-6 flex flex-col items-center text-center gap-2">
        <span class="w-11 h-11 rounded-full bg-green-50 text-green-600 flex items-center justify-center">
          <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        </span>
        <p class="text-sm font-semibold text-ink">Todos los productos ya están dados de alta</p>
        <p class="text-[12.5px] text-ink-muted max-w-md">Los materiales y servicios de este costeo ya resuelven a artículos reales — no quedó nada capturado como texto libre. Puedes continuar al flujo de producción.</p>
        <button class="mt-2 px-4 py-2 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 flex items-center gap-1.5" @click="goStep(4)">
          Continuar a Flujo de Producción
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 7l5 5-5 5M6 12h12"/></svg>
        </button>
      </div>

    </div>

    <!-- ══════════ STEP 4 · FLUJO DE PRODUCCIÓN ══════════ -->
    <!-- Vista de CONFIRMACIÓN: el orden y el agrupado de servicios salen solos de las
         etapas del costeo (get_flujo_operaciones -> _resolve_production_operations).
         El usuario solo puede: reordenar los pasos (arrastrando la tarjeta) y decir
         de qué paso recibe el material cada uno. El nombre de la pieza es automático.
         Nada de servicio/proveedor/precio aquí -- eso vive en Costear. -->
    <div v-else-if="activeStep === 4" class="px-5 py-7 pb-24 max-w-6xl mx-auto w-full" v-solo-lectura="soloLecturaPaso">
      <!-- Solo lectura: el usuario tiene esta etapa en "ver" (accesos por vista). -->
      <p v-if="soloLecturaPaso" class="max-w-5xl mx-auto mb-4 text-[12.5px] text-ink-muted bg-surface-raised rounded-lg px-3 py-2">
        <b class="text-ink">Solo lectura.</b> Puedes consultar esta etapa; la captura la hace quien la tiene asignada.
      </p>
      <h2 class="text-[15px] font-semibold text-ink">Flujo de Producción</h2>
      <p class="text-[12.5px] text-ink-muted mt-1 leading-relaxed max-w-3xl">
        Ya viene armado desde el costeo. Arrastra un paso para reordenarlo y ajusta <span class="text-ink-muted">"recibe de"</span> solo si el material sale de otro paso.
      </p>

      <!-- Flujo ya confirmado: solo lectura. Para corregirlo hay que revertirlo
           (revertir_flujo_produccion), lo que borra BOMs/Subcontracting BOMs/plan y lo
           vuelve editable. -->
      <div v-if="flujoBloqueado" class="mt-3 rounded-lg bg-amber-50 border border-amber-200 px-3.5 py-2.5 flex items-center gap-3">
        <svg class="w-4 h-4 text-amber-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"/></svg>
        <p class="flex-1 text-[12px] text-amber-900">
          <span class="font-semibold">El flujo ya está confirmado</span> y sus documentos de producción (BOMs, Subcontracting BOMs y plan) ya se crearon, así que no se puede editar.
          Si hay que corregir algo, revierte el flujo: se borran esos documentos y esta pantalla se vuelve a poder editar.
        </p>
        <button v-if="docStatus === 'En Producción'" type="button" class="flex-shrink-0 px-3 py-1.5 text-[12.5px] font-medium text-red-700 bg-white border border-red-200 rounded-lg hover:bg-red-50" @click="confirmRevertir.open = true">Revertir flujo</button>
      </div>

      <div v-if="flujoLoading" class="flex justify-center py-16 text-ink-xlight">
        <svg class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
      </div>

      <fieldset v-else :disabled="flujoBloqueado" class="border-0 p-0 m-0 min-w-0">
      <div v-for="prod in flujoOps" :key="prod.finished_item" class="mt-7 first:mt-6">
        <div class="flex items-baseline justify-between mb-1">
          <span class="text-[12.5px] font-medium text-ink truncate">{{ prod.finished_item }}</span>
          <span class="text-[11.5px] text-ink-light flex-shrink-0 ml-3">{{ (prod.qty || 0).toLocaleString('es-MX') }} pzas</span>
        </div>

        <div v-if="(prod.avisos || []).length" class="mb-2 text-[11.5px] text-amber-800 bg-amber-50 border border-amber-200 rounded-md px-3 py-2 space-y-0.5">
          <p v-for="(a, i) in prod.avisos" :key="i">{{ a }}</p>
        </div>

        <p v-if="!prod.operaciones.length" class="text-[12px] text-ink-light py-2">Sin servicios de manufactura en el costeo.</p>

        <div v-else>
          <TransitionGroup tag="div" name="flujo-card" class="space-y-2">
            <div
              v-for="(op, idx) in prod.operaciones" :key="op.op_key"
              class="group relative flex gap-3 bg-white border rounded-lg px-3 py-3 transition-shadow"
              :class="flujoEdit[op.op_key] ? 'border-brand-200 ring-1 ring-brand-100' : 'border-surface-border hover:shadow-card'"
            >
              <!-- Marcador + subir/bajar -->
              <div class="relative flex-shrink-0 pt-px flex flex-col items-center gap-1">
                <button type="button" class="mini-icon-btn" :disabled="idx === 0" title="Subir un paso" @click="moverOperacion(prod, idx, -1)">
                  <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 15l7-7 7 7"/></svg>
                </button>
                <span
                  class="w-[26px] h-[26px] rounded-full flex items-center justify-center text-[11px] font-semibold"
                  :class="terminalKeysVivo(prod).includes(op.op_key) ? 'bg-green-500 text-white' : 'bg-surface-raised text-ink-muted'"
                >{{ idx + 1 }}</span>
                <button type="button" class="mini-icon-btn" :disabled="idx === prod.operaciones.length - 1" title="Bajar un paso" @click="moverOperacion(prod, idx, 1)">
                  <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg>
                </button>
              </div>

              <!-- Contenido -->
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-1.5">
                  <span class="text-[13px] font-medium text-ink truncate">{{ supplierLabel(prod, op) }}</span>
                  <span v-if="etiquetaArmado(prod, op) === 'arma'" class="flex-shrink-0 text-[10.5px] font-medium text-green-700 bg-green-50 ring-1 ring-green-200 rounded px-1.5 py-px">Aquí se arma la prenda</span>
                  <span v-else-if="etiquetaArmado(prod, op) === 'armada'" class="flex-shrink-0 text-[10.5px] font-medium text-ink-muted bg-surface-raised rounded px-1.5 py-px">Recibe la prenda armada</span>
                  <span v-if="opIncompleta(op)" class="relative flex-shrink-0">
                    <svg class="w-3.5 h-3.5 text-amber-500 cursor-pointer" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" @click="toggleWarn(op, 'incompleto')"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/></svg>
                    <div v-if="isWarnOpen(op, 'incompleto')" class="absolute z-20 left-0 top-full mt-1 w-56 bg-white border border-amber-200 rounded-lg shadow-lg p-2 text-[11px] leading-snug text-amber-800">Faltan datos en este paso (proveedor o servicio) -- revísalo en Costear.</div>
                  </span>
                  <span v-if="esHuerfano(prod, op)" class="relative flex-shrink-0">
                    <svg class="w-3.5 h-3.5 text-amber-500 cursor-pointer" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" @click="toggleWarn(op, 'huerfano')"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"/></svg>
                    <div v-if="isWarnOpen(op, 'huerfano')" class="absolute z-20 left-0 top-full mt-1 w-56 bg-white border border-amber-200 rounded-lg shadow-lg p-2 text-[11px] leading-snug text-amber-800">Este paso no alimenta a ningún otro -- revisa si al siguiente paso le falta indicar que recibe de aquí, o si en realidad debería conectarse a otro.</div>
                  </span>
                </div>
                <!-- Árbol: Servicios / Recibe de / Materia Prima / Entrega -->
                <div class="mt-1.5 text-[12px]">
                  <!-- Servicios (solo lectura) -->
                  <div v-if="op.servicios.length" class="flex items-center gap-1">
                    <button data-nav type="button" class="w-3.5 h-3.5 flex-shrink-0 flex items-center justify-center rounded text-ink-xlight hover:text-ink-muted hover:bg-surface-raised leading-none" @click="toggleTree(op, 'servicios')">{{ isTreeOpen(op, 'servicios') ? '−' : '+' }}</button>
                    <span class="text-ink-muted">Servicios</span>
                  </div>
                  <ul v-if="op.servicios.length && isTreeOpen(op, 'servicios')" class="ml-[18px] mt-0.5 mb-1 space-y-px border-l border-surface-border pl-2.5">
                    <li v-for="s in op.servicios" :key="s.item" class="flex items-baseline gap-2 text-[11px] leading-snug">
                      <span class="text-ink-xlight truncate flex-1">{{ s.item }}</span>
                      <span class="text-ink-light flex-shrink-0 tabular-nums">{{ fmtC(s.precio) }}</span>
                      <button
                        v-if="op.servicios.length > 1 || s.no_agrupar"
                        type="button"
                        class="flex-shrink-0 text-brand-600 hover:text-brand-700"
                        :disabled="agrupandoTid === s.stage_id"
                        :title="s.no_agrupar ? 'Este servicio quedó separado -- únelo de nuevo con los demás de este proveedor' : 'Sacar este servicio del bloque y darle su propio paso'"
                        @click="alternarNoAgrupar(s)"
                      >{{ s.no_agrupar ? 'unir' : 'separar' }}</button>
                    </li>
                  </ul>

                  <!-- Recibe de (editable) -->
                  <div class="group/recibe flex items-center gap-1 mt-0.5">
                    <button data-nav type="button" class="w-3.5 h-3.5 flex-shrink-0 flex items-center justify-center rounded text-ink-xlight hover:text-ink-muted hover:bg-surface-raised leading-none" @click="toggleTree(op, 'recibe')">{{ isTreeOpen(op, 'recibe') || flujoEdit[op.op_key] ? '−' : '+' }}</button>
                    <span class="text-ink-muted">Recibe de</span>
                    <button v-if="idx > 0" type="button" class="text-[11px] text-brand-600 hover:text-brand-700 ml-0.5" :class="flujoEdit[op.op_key] ? 'font-medium' : ''" @click="flujoEdit[op.op_key] = !flujoEdit[op.op_key]">{{ flujoEdit[op.op_key] ? 'listo' : 'editar' }}</button>
                    <span v-if="recibeRedundantesVivo(prod, op).size" class="relative flex-shrink-0">
                      <svg class="w-3.5 h-3.5 text-amber-500 cursor-pointer" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" @click="toggleWarn(op, 'redundante')"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/></svg>
                      <div v-if="isWarnOpen(op, 'redundante')" class="absolute z-20 left-0 top-full mt-1 w-64 bg-white border border-amber-200 rounded-lg shadow-lg p-2 text-[11px] leading-snug text-amber-800">Ya recibes de {{ recibeRedundanteTexto(prod, op) }} de forma indirecta, a través de otro de tus pasos seleccionados. Si es una pieza que se une aparte (un camino en paralelo que también llega completo hasta aquí), déjalo así; si fue una selección de más, quítala.</div>
                    </span>
                  </div>
                  <ul v-if="!flujoEdit[op.op_key] && isTreeOpen(op, 'recibe')" class="ml-[18px] mt-0.5 mb-1 space-y-px border-l border-surface-border pl-2.5">
                    <li v-for="nombre in recibeDeLista(prod, op)" :key="nombre" class="text-[11px] text-ink-xlight truncate">{{ nombre }}</li>
                  </ul>
                  <div v-if="flujoEdit[op.op_key]" class="ml-[18px] mt-0.5 mb-1 rounded-lg bg-white ring-1 ring-surface-border p-1 max-w-xs">
                    <button
                      type="button"
                      class="w-full text-left text-[12px] px-2 py-1.5 rounded-md flex items-center gap-2 hover:bg-surface-raised/70 transition-colors"
                      @click="setTrabajaMateriaPrima(op)"
                    >
                      <span class="w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0" :class="!op.recibe_de.length ? 'bg-brand-500 text-white' : 'ring-1 ring-inset ring-ink-xlight'">
                        <svg v-if="!op.recibe_de.length" class="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
                      </span>
                      <span :class="!op.recibe_de.length ? 'text-ink font-medium' : 'text-ink-muted'">Materia prima</span>
                    </button>
                    <button
                      v-for="prev in prod.operaciones.slice(0, idx)" :key="prev.op_key"
                      type="button"
                      class="w-full text-left text-[12px] px-2 py-1.5 rounded-md flex items-center gap-2 hover:bg-surface-raised/70 transition-colors"
                      @click="toggleTrabajaSobre(op, prev.op_key)"
                    >
                      <span class="w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0" :class="op.recibe_de.includes(prev.op_key) ? 'bg-brand-500 text-white' : 'ring-1 ring-inset ring-ink-xlight'">
                        <svg v-if="op.recibe_de.includes(prev.op_key)" class="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
                      </span>
                      <span class="truncate" :class="op.recibe_de.includes(prev.op_key) ? 'text-ink font-medium' : 'text-ink-muted'">{{ supplierLabel(prod, prev) }}</span>
                      <span v-if="opIncompleta(prev)" class="ml-auto flex-shrink-0 text-[10px] text-amber-600" title="Este paso todavía tiene datos incompletos (proveedor o servicio vacío) -- revísalo en Costear antes de encadenarlo">incompleto</span>
                    </button>
                  </div>

                  <!-- Materia Prima (editable) -->
                  <div v-if="prod.materiales && prod.materiales.length" class="group/mat flex items-center gap-1 mt-0.5">
                    <button data-nav type="button" class="w-3.5 h-3.5 flex-shrink-0 flex items-center justify-center rounded text-ink-xlight hover:text-ink-muted hover:bg-surface-raised leading-none" @click="toggleTree(op, 'materiales')">{{ isTreeOpen(op, 'materiales') || matEdit[op.op_key] ? '−' : '+' }}</button>
                    <span class="text-ink-muted">Materia Prima</span>
                    <button type="button" class="text-[11px] text-brand-600 hover:text-brand-700 ml-0.5" :class="matEdit[op.op_key] ? 'font-medium' : ''" @click="matEdit[op.op_key] = !matEdit[op.op_key]">{{ matEdit[op.op_key] ? 'listo' : 'editar' }}</button>
                  </div>
                  <ul v-if="prod.materiales && prod.materiales.length && !matEdit[op.op_key] && isTreeOpen(op, 'materiales')" class="ml-[18px] mt-0.5 mb-1 space-y-px border-l border-surface-border pl-2.5">
                    <li v-if="!materialesDirectosDe(prod, op).length" class="text-[11px] text-ink-light">ninguno</li>
                    <li v-for="mat in materialesDirectosDe(prod, op)" :key="mat.material_id" class="text-[11px] text-ink-xlight truncate">{{ mat.item }}</li>
                  </ul>
                  <div v-if="prod.materiales && prod.materiales.length && matEdit[op.op_key]" class="ml-[18px] mt-0.5 mb-1 rounded-lg bg-white ring-1 ring-surface-border p-1 max-w-xs">
                    <button
                      v-for="mat in prod.materiales" :key="mat.material_id"
                      type="button"
                      class="w-full text-left text-[12px] px-2 py-1.5 rounded-md flex items-center gap-2 hover:bg-surface-raised/70 transition-colors"
                      @click="toggleMaterialOp(mat, op.op_key)"
                    >
                      <span class="w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0" :class="mat.op_key === op.op_key ? 'bg-brand-500 text-white' : 'ring-1 ring-inset ring-ink-xlight'">
                        <svg v-if="mat.op_key === op.op_key" class="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
                      </span>
                      <span class="truncate" :class="mat.op_key === op.op_key ? 'text-ink font-medium' : 'text-ink-muted'">{{ mat.item }}</span>
                    </button>
                  </div>

                </div>
              </div>
            </div>
          </TransitionGroup>

          <!-- Piezas y por dónde pasa cada una.
               Tabla VOLTEADA respecto al diseño anterior: los servicios van de
               FILAS y las piezas de columnas. Los nombres de servicio son largos
               ("BORDADO-MANGA-DER-GRUPO-MEXICO") y de encabezado quedaban
               recortados a unos pocos caracteres; los de pieza son cortos
               ("Puños") y sí caben arriba. Cada casilla se marca por SERVICIO, que
               es el grano con el que después se decide qué servicio cobra sobre
               qué pieza (ver _resolve_piece_states). El paso final no se marca:
               toda pieza llega ahí. -->
          <div v-if="prod.operaciones.length > 1" class="mt-5">
            <div class="flex items-center justify-between mb-1.5">
              <span class="text-[12px] font-medium text-ink-muted">Piezas de este producto</span>
              <button type="button" class="text-[11px] text-brand-600 hover:text-brand-700" @click="agregarSubEnsamblaje(prod)">+ agregar pieza</button>
            </div>
            <p v-if="!prod.sub_ensamblajes.length" class="text-[11px] text-ink-light leading-relaxed max-w-3xl">
              Ninguna declarada -- úsalo solo si este producto se arma de piezas que siguen caminos distintos (puños, mangas, cuellos...). Con piezas declaradas, cada una avanza con su taller sin esperar a las demás.
            </p>
            <div v-else class="overflow-x-auto rounded-lg ring-1 ring-surface-border bg-white">
              <table class="w-full text-[11.5px] border-collapse">
                <thead>
                  <tr class="bg-surface-raised">
                    <th class="text-left font-medium text-ink-muted px-3 py-2 min-w-[220px]">Servicio</th>
                    <th v-for="(sub, si) in prod.sub_ensamblajes" :key="si" class="px-2 py-1.5 align-top" style="width: 96px">
                      <input
                        v-model="sub.nombre" v-mayus type="text" placeholder="Ej. PUÑOS"
                        class="w-full text-[11.5px] text-center px-1 py-0.5 rounded ring-1 ring-inset ring-surface-border focus:ring-brand-400 focus:outline-none"
                        @input="flujoDirty = true; piezasEditando = true"
                      />
                      <div class="flex items-center justify-center gap-1 mt-1">
                        <span class="text-[10px] text-ink-light">×</span>
                        <input
                          v-model.number="sub.multiplicador" type="number" min="1" step="1"
                          title="Cuántas de esta pieza lleva UNA prenda (2 puños, 1 frente)"
                          class="w-9 text-[10.5px] text-center px-0.5 py-px rounded ring-1 ring-inset ring-surface-border focus:ring-brand-400 focus:outline-none"
                          @input="flujoDirty = true; piezasEditando = true"
                        />
                        <button type="button" class="mini-icon-btn" title="Quitar pieza" @click="quitarSubEnsamblaje(prod, si)">
                          <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
                        </button>
                      </div>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="c in columnasMatriz(prod)" :key="c.stage_id" class="border-t border-surface-border">
                    <td class="px-3 py-1.5">
                      <div class="text-ink truncate" :title="c.titulo">{{ c.titulo }}</div>
                      <div class="text-[10.5px] text-ink-light truncate">{{ c.supplier }}</div>
                      <div v-if="c.arma" class="text-[10.5px] font-medium text-green-700">Aquí se unen todas las piezas<span v-if="!c.elegida" class="font-normal text-ink-light"> · detectado automáticamente</span></div>
                      <div v-else-if="c.armada" class="text-[10.5px] text-ink-muted">Trabaja la prenda armada</div>
                      <button
                        v-if="!c.terminal && c.primero && prod.sub_ensamblajes.length && (c.elegida || !c.conPiezas)"
                        type="button"
                        class="mt-0.5 text-[10.5px] font-medium"
                        :class="c.elegida ? 'text-ink-light hover:text-ink-muted' : 'text-brand-600 hover:text-brand-700'"
                        :title="c.elegida ? 'Ya no es el paso donde se unen las piezas' : 'En este paso se juntan todas las piezas para armar la prenda; de aquí en adelante se trabaja la prenda armada'"
                        @click="elegirUnion(prod, c.op_key)"
                      >{{ c.elegida ? "Quitar unión" : (c.arma ? "Confirmar: aquí se unen" : "Aquí se unen las piezas") }}</button>
                    </td>
                    <td v-for="(sub, si) in prod.sub_ensamblajes" :key="si" class="text-center px-2 py-1.5">
                      <!-- Donde se arma: todas las piezas llegan aquí y salen como UNA prenda.
                           Sigue siendo clic-able: marcar una pieza aquí dice que se trabaja
                           por separado, y entonces la unión se recalcula. -->
                      <span v-if="c.elegida" class="w-5 h-5 rounded-full flex items-center justify-center mx-auto bg-green-50 text-green-600 ring-1 ring-inset ring-green-300" title="Aquí se unen todas las piezas en una sola prenda">
                        <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.6"><path stroke-linecap="round" stroke-linejoin="round" d="M6 4v5a6 6 0 006 6m6-11v5a6 6 0 01-6 6m0 0v5"/></svg>
                      </span>
                      <button
                        v-else-if="(c.arma || c.armada) && !c.terminal"
                        type="button"
                        class="w-5 h-5 rounded-full flex items-center justify-center mx-auto transition-colors"
                        :class="c.arma ? 'bg-green-50 text-green-600 ring-1 ring-inset ring-green-300 hover:ring-green-500' : 'text-ink-light hover:text-ink-muted'"
                        :title="c.arma ? `Aquí se unen todas las piezas en una sola prenda. Márcala solo si ${sub.nombre || 'esta pieza'} se trabaja aquí por separado.` : 'Recibe la prenda ya armada'"
                        @click="toggleSubEnsamblajeStage(sub, c.stage_id)"
                      >
                        <svg v-if="c.arma" class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.6"><path stroke-linecap="round" stroke-linejoin="round" d="M6 4v5a6 6 0 006 6m6-11v5a6 6 0 01-6 6m0 0v5"/></svg>
                        <span v-else class="text-[12px] leading-none text-ink-xlight">—</span>
                      </button>
                      <button
                        v-else-if="!c.terminal"
                        type="button"
                        class="w-5 h-5 rounded flex items-center justify-center mx-auto transition-colors"
                        :class="sub.stage_ids.includes(c.stage_id) ? 'bg-brand-500 text-white' : 'ring-1 ring-inset ring-ink-xlight hover:ring-ink-light'"
                        :title="`${sub.nombre || 'Esta pieza'} pasa por ${c.titulo}`"
                        @click="toggleSubEnsamblajeStage(sub, c.stage_id)"
                      >
                        <svg v-if="sub.stage_ids.includes(c.stage_id)" class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
                      </button>
                      <span v-else class="flex items-center justify-center text-green-600" :title="c.armada ? 'Recibe la prenda ya armada' : 'Toda pieza llega al paso final -- no hace falta marcarlo'">
                        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p v-if="prod.sub_ensamblajes.length && !prod.union_op_key" class="mt-2 text-[11px] text-ink-light">Marca por qué servicios pasa cada pieza y, en el paso donde se juntan para armar la prenda, presiona "Aquí se unen las piezas".</p>
          </div>
        </div>
      </div>

      </fieldset>

      <div v-if="!flujoBloqueado" class="flex justify-end items-center gap-3 mt-8">
        <span v-if="flujoDirty" class="text-[11.5px] text-ink-light">Cambios sin guardar</span>
        <button :disabled="advancing || flujoLoading || guardandoFlujo" class="px-4 py-2 text-[13px] font-medium text-ink bg-white border border-surface-border rounded-lg hover:bg-surface-raised disabled:opacity-50 transition-colors" @click="guardarCambiosFlujo">
          {{ guardandoFlujo ? "Guardando…" : "Guardar cambios" }}
        </button>
        <button :disabled="advancing || flujoLoading || guardandoFlujo" class="px-4 py-2 text-[13px] font-medium text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center gap-1.5 transition-colors" @click="pedirConfirmarFlujo(confirmarFlujo)">
          {{ advancing ? "Preparando…" : "Confirmar y pasar a producción" }}
          <svg v-if="!advancing" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.4"><path stroke-linecap="round" stroke-linejoin="round" d="M13 7l5 5-5 5M6 12h12"/></svg>
        </button>
      </div>
    </div>


    <!-- ══════════ STEP 5 · PRODUCIR (centro de control) ══════════ -->
    <div v-else-if="activeStep === 5" class="w-full">
      <!-- ══════════════════════════════════════════════════════════════════════
           PRODUCCIÓN v2 (docs/plan-ui-produccion.md). Menú a la izquierda, una
           vista por trabajo, y SIEMPRE la misma barra de acciones abajo.
           ══════════════════════════════════════════════════════════════════════ -->
      <ProduccionLayout
        :menu="menuProduccion" :vista="pVista" :lote-ref="loteActivoRef"
        :encabezado="pEncabezado" :pasos="pPasos" :paso-actual="pPasoSel"
        :barra="pBarra" :ocupado="advancing" :puede-ver="puedeVer" :solo-lectura="pSoloLectura"
        @ir="irProduccion" @ir-paso="onIrPaso" @nuevo-lote="abrirNuevoLotePanel" @cambiar-ov="setActiveSO"
      >
        <template #encabezado-derecha>
          <!-- Dentro de un taller: su orden de compra y su ficha de manufactura
               (cada una en un panel), no el filtro de producto del lote. -->
          <div v-if="pVista === 'lote' && pTallerAbierto" class="flex gap-2">
            <button data-nav type="button" class="p-btn-secondary h-8" @click="abrirOcDelTaller">Orden de compra</button>
            <button data-nav type="button" class="p-btn-secondary h-8" @click="abrirOmDelTaller">Orden de manufactura</button>
          </div>
          <!-- Filtro de producto: solo si el lote trae más de uno con cantidad. -->
          <Segmentado
            v-else-if="pVista === 'lote' && pPasoLote !== 'entrega' && filtroProductoOpciones.length > 2"
            v-model="filtroProducto" :opciones="filtroProductoOpciones"
          />
        </template>

        <!-- ═══════════ TABLERO ═══════════ -->
        <div v-if="pVista === 'tablero'" class="space-y-4">
          <VacioEstado
            v-if="!hasPlan" icono="lista" titulo="Aún no has creado el plan de producción"
            detalle="Se crean los BOMs y el plan (ligado a la orden de venta, con el almacén de materias primas y lo que falta comprar según inventario)."
          />
          <template v-else>
            <div class="grid grid-cols-3 gap-px bg-surface-border rounded-xl overflow-hidden border border-surface-border">
              <div class="bg-white p-4">
                <p class="p-meta">Materia prima recibida</p>
                <p class="text-[22px] font-semibold p-num mt-1">{{ Math.round(materiaPrimaPct) }}%</p>
                <div class="h-1 bg-zinc-100 rounded mt-2"><div class="h-1 bg-emerald-500 rounded" :style="{ width: Math.min(100, materiaPrimaPct) + '%' }"></div></div>
              </div>
              <div class="bg-white p-4">
                <p class="p-meta">Maquila recibida</p>
                <p class="text-[22px] font-semibold p-num mt-1">{{ Math.round(subcontratacionPct) }}%</p>
                <p class="p-meta">{{ prodComplete.lotes_total ? `${prodComplete.lotes_recibidos} de ${prodComplete.lotes_total} encargos` : "" }}</p>
                <div class="h-1 bg-zinc-100 rounded mt-2"><div class="h-1 bg-brand-500 rounded" :style="{ width: Math.min(100, subcontratacionPct) + '%' }"></div></div>
              </div>
              <div class="bg-white p-4">
                <p class="p-meta">Entregado al cliente</p>
                <p class="text-[22px] font-semibold p-num mt-1">{{ Math.round(related.delivery_per_delivered || 0) }}%</p>
                <div class="h-1 bg-zinc-100 rounded mt-2"><div class="h-1 bg-sky-500 rounded" :style="{ width: Math.min(100, related.delivery_per_delivered || 0) + '%' }"></div></div>
              </div>
            </div>

            <div v-if="lotesProduccion.length">
              <h2 class="p-eyebrow mb-2">Lotes</h2>
              <div class="p-panel">
                <FilaLista
                  v-for="l in lotesProduccion" :key="l.lote_ref"
                  :estado="menuLotes.find((m) => m.lote_ref === l.lote_ref)?.estado || 'off'"
                  :titulo="`${l.lote_ref}${l.schedule_date ? ' · ' + l.schedule_date.slice(0, 10) : ''}`"
                  :meta="(l.productos || []).map((x) => `${x.item_name} ${x.qty.toLocaleString('es-MX')}`).join(' · ')"
                  @abrir="irProduccion({ vista: 'lote', lote: l.lote_ref })"
                >
                  <template #derecha>
                    <Pasos class="w-[260px] hidden md:flex" compacto :pasos="pasosDeLoteParaLista(l)" />
                    <Pill :estado="pillLote(l).estado" :texto="pillLote(l).texto" ancho="w-28" />
                  </template>
                </FilaLista>
              </div>
              <p class="p-meta mt-1.5">Cada lote: 1 Materia prima · 2 Talleres · 3 Entrega</p>
            </div>

            <div v-if="porHacer.length">
              <h2 class="p-eyebrow mb-2">Por hacer</h2>
              <div class="p-panel">
                <FilaLista
                  v-for="(t, i) in porHacer" :key="i" :estado="t.estado" :titulo="t.titulo" :meta="t.meta"
                  @abrir="t.ir()"
                >
                  <template #derecha><span class="p-meta hidden md:inline">{{ t.donde }}</span></template>
                </FilaLista>
              </div>
            </div>
            <VacioEstado v-else icono="check-circulo" titulo="No hay nada pendiente" detalle="Todo lo de esta orden de venta está al día." />
          </template>
        </div>

        <!-- ═══════════ PREPARACIÓN ═══════════ -->
        <div v-else-if="pVista === 'preparacion'" class="space-y-4">
      <div v-if="prepSteps.length && pPrepPaso === 1" class="bg-white rounded-xl border border-surface-border p-4">
        <p class="section-title mb-2">Resultado de la preparación</p>
        <div v-for="s in prepSteps" :key="s.label" class="flex items-center gap-2 text-[13px] py-1">
          <svg v-if="s.ok" class="w-4 h-4 text-green-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          <svg v-else class="w-4 h-4 text-amber-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>
          <span class="flex-1">{{ s.label }}</span>
          <span class="text-ink-muted text-xs">{{ s.skipped ? 'ya existía' : s.detail }}</span>
        </div>
      </div>

      <div v-if="!hasPlan && !prepSteps.length" class="bg-white rounded-xl border border-surface-border p-8 text-center">
        <div class="w-12 h-12 rounded-xl bg-brand-50 flex items-center justify-center mx-auto mb-3">
          <svg class="w-6 h-6 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"/></svg>
        </div>
        <p class="text-sm font-medium text-ink">Aún no has creado el plan de producción</p>
        <p class="text-[13px] text-ink-muted mt-1">Se crean los BOMs y el plan (ligado a la orden de venta, con el almacén de materias primas y lo que falta comprar según inventario).</p>
      </div>

      <template v-else-if="hasPlan">
        <!-- ─── Paso 1 · Plan ─── -->
        <template v-if="pPrepPaso === 1">
        <!-- ═══ Plan de producción (se colapsa solo, una vez validado) ═══ -->
        <details class="bg-white rounded-xl border border-surface-border group" :open="!planValidated">
          <summary class="flex items-center justify-between p-4 cursor-pointer select-none list-none">
            <div class="flex items-center gap-2.5">
              <svg class="w-4 h-4 text-ink-light transition-transform group-open:rotate-90 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
              <p class="text-sm font-semibold text-ink">Plan de producción</p>
              <span class="text-[12px] text-ink-muted">{{ planDetail.name }}</span>
            </div>
            <DocStatusPill :docstatus="planDetail.docstatus" />
          </summary>
          <div class="border-t border-surface-border p-4 space-y-4">
            <div class="flex items-center justify-end">
              <a class="doc-action" :href="`/app/production-plan/${planDetail.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>ERPNext</a>
            </div>
            <div class="grid grid-cols-3 gap-4">
              <div>
                <label class="field-label">Almacén materias primas</label>
                <LinkInput v-if="!planValidated" v-model="planWh" doctype="Warehouse" :filters="warehouseFilters" placeholder="Almacén MP…" />
                <div v-else class="field-input bg-surface-raised/60">{{ planDetail.for_warehouse || '—' }}</div>
              </div>
              <div>
                <label class="field-label">Orden de venta</label>
                <div class="field-input bg-surface-raised/60 truncate">{{ planDetail.sales_order || '—' }}</div>
              </div>
              <div>
                <label class="field-label">Cant. total planeada</label>
                <div class="field-input bg-surface-raised/60">{{ planDetail.total_planned_qty || 0 }}</div>
              </div>
            </div>

            <div class="border-t border-surface-border pt-3">
              <div class="prod-head"><span class="prod-title"><svg class="w-4 h-4 text-ink-light" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M20 13V7a2 2 0 00-2-2H6a2 2 0 00-2 2v6m16 0v4a2 2 0 01-2 2H6a2 2 0 01-2-2v-4m16 0H4"/></svg>Cantidad a producir <span class="prod-count">{{ planDetail.po_items.length }}</span></span></div>
              <div v-for="it in planDetail.po_items" :key="it.name" class="prod-row">
                <span class="flex-1 min-w-0 truncate font-mono text-[12px]">{{ it.item_code }}</span>
                <input
                  v-if="!planValidated" v-model.number="it.planned_qty" type="number" min="0" step="1"
                  :max="Math.round(it.planned_qty_original * 1.05 * 100) / 100"
                  class="field-input w-24 text-right"
                  :class="it.planned_qty > it.planned_qty_original * 1.05 + 0.001 ? 'border-red-400' : ''"
                />
                <span v-else class="text-[13px] whitespace-nowrap">{{ it.planned_qty }}</span>
              </div>
              <p v-if="!planValidated" class="text-[11px] text-ink-light">Puedes planear hasta 5% más de lo requerido (imprevistos: piezas defectuosas, muestras…) — de ahí no se deja pasar. Al validar, este margen se refleja solo en materiales y subcontratación.</p>
            </div>


            <div class="border-t border-surface-border pt-3">
              <div class="prod-head"><span class="prod-title"><svg class="w-4 h-4 text-ink-light" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"/></svg>Materias primas a comprar <span class="prod-count">{{ planDetail.mr_items.length }}</span></span></div>
              <!-- Una columna POR PRODUCTO con su consumo por prenda (lo capturado en
                   el costeo), al lado del total que pide el plan. Es informativo: deja
                   comprobar de un vistazo que el total cuadra, y con dos productos que
                   comparten material se ve el renglón de cada uno sin leer un párrafo. -->
              <div class="overflow-x-auto -mx-4">
                <table class="p-tbl">
                  <thead>
                    <tr>
                      <th>Material</th>
                      <th v-for="col in columnasConsumo" :key="col.code" class="text-right whitespace-nowrap">
                        {{ col.nombre }}<span class="block font-normal text-ink-xlight">por prenda</span>
                      </th>
                      <th class="text-right whitespace-nowrap">Total a comprar</th>
                      <th>Almacén</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="it in planDetail.mr_items" :key="it.item_code">
                      <td class="font-mono text-[12px]">{{ it.item_code }}</td>
                      <td v-for="col in columnasConsumo" :key="col.code" class="text-right whitespace-nowrap p-num"
                          :class="consumoDe(it, col.code)?.origen === 'bom' ? 'text-amber-700' : ''"
                          :title="consumoTitulo(it)">
                        <template v-if="consumoDe(it, col.code)">
                          {{ fmtConsumo(consumoDe(it, col.code)) }}
                          <span v-if="consumoDe(it, col.code).origen === 'bom'" title="Viene del BOM del producto: este costeo no lo declara, así que su costo no entró en el precio.">*</span>
                        </template>
                        <span v-else class="text-ink-xlight">—</span>
                      </td>
                      <td class="text-right whitespace-nowrap p-num">× {{ it.quantity }} {{ it.uom }}</td>
                      <td><span class="prod-status">{{ it.warehouse }}</span></td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p v-if="planDetail.mr_items.some((x) => consumoFueraDelCosteo(x))" class="text-[11px] text-amber-700 mt-1.5">
                * Sale del BOM del producto, no del costeo: se compra pero su costo no entró en el precio.
              </p>
              <p v-if="!planDetail.mr_items.length" class="prod-empty">Sin faltantes (inventario suficiente) o pendiente de obtener.</p>
            </div>

            <div v-if="planValidated" class="border-t border-surface-border pt-3 flex items-center justify-between gap-3">
              <div>
                <p class="text-[13px] font-medium text-ink">Producción interna (opcional)</p>
                <p class="text-[11.5px] text-ink-muted">Poco usada si se subcontrata todo el proceso.</p>
              </div>
              <span v-if="downstream.wos.length" class="p-pill-ok flex-shrink-0">{{ downstream.wos.length }} creada(s)</span>
              <span v-else class="p-meta flex-shrink-0">Con el botón “Orden de trabajo” de abajo.</span>
            </div>
          </div>
        </details>
        </template>

        <!-- ─── Paso 2 · Materia prima ─── -->
        <template v-else-if="pPrepPaso === 2">
        <!-- ═══ Materia prima ═══ -->
        <div v-if="planValidated" class="bg-white rounded-xl border border-surface-border p-4 space-y-3">
          <div class="prod-head"><span class="prod-title"><svg class="w-4 h-4 text-ink-light" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10"/></svg>Materia prima</span></div>

          <div v-if="!mrDetail" class="text-center py-6">
            <p class="text-sm font-medium text-ink mb-1">Aún no has creado la solicitud de material</p>
            <p class="text-[12.5px] text-ink-muted">Se crea desde el plan, con el proveedor por materia prima ya asignado (del costeo).</p>
          </div>

          <template v-else>
            <div :id="`doc-hl-${mrDetail.name}`" :class="{ 'doc-highlight-flash': highlightTarget === mrDetail.name }">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2.5">
                  <span class="text-[13px] font-semibold text-ink">{{ mrDetail.name }}</span>
                  <DocStatusPill :docstatus="mrDetail.docstatus" />
                </div>
                <div class="flex items-center gap-2">
                  <button data-libre class="doc-action" @click="openPdf('Material Request', mrDetail.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>Vista previa</button>
                  <a class="doc-action" :href="`/app/material-request/${mrDetail.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>ERPNext</a>
                </div>
              </div>
              <div class="grid grid-cols-3 gap-3">
                <div><label class="field-label">Tipo</label><div class="field-input bg-surface-raised/60">{{ mrDetail.material_request_type }}</div></div>
                <div>
                  <label class="field-label">Fecha requerida</label>
                  <input v-if="!mrValidated" v-model="mrSchedule" type="date" class="field-input" />
                  <div v-else class="field-input bg-surface-raised/60">{{ mrSchedule || '—' }}</div>
                </div>
                <div><label class="field-label">Estatus</label><div class="field-input bg-surface-raised/60">{{ mrDetail.status }}</div></div>
              </div>
              <table class="w-full text-sm">
                <thead><tr class="text-left text-xs font-semibold text-ink-light border-b border-surface-border"><th class="py-2">Artículo</th><th class="py-2 w-24 text-right">Cantidad</th><th class="py-2 w-20">UOM</th><th class="py-2 w-1/4">Proveedor</th></tr></thead>
                <tbody>
                  <tr v-for="it in mrItems" :key="it.name" class="border-b border-surface-border/60">
                    <td class="py-1.5 pr-2 font-mono text-[12px]">{{ it.item_code }}</td>
                    <td class="py-1.5 pr-2"><input v-if="!mrValidated" v-model.number="it.qty" type="number" :min="Math.round((it.qty_original || it.qty) * 0.95 * 100) / 100" :max="Math.round((it.qty_original || it.qty) * 1.05 * 100) / 100" class="field-input text-right" :class="(it.qty > (it.qty_original || it.qty) * 1.05 + 0.001 || it.qty < (it.qty_original || it.qty) * 0.95 - 0.001) ? 'border-red-400' : ''" /><span v-else class="text-right block">{{ it.qty }}</span></td>
                    <td class="py-1.5 pr-2 text-ink-muted text-xs">{{ it.uom }}</td>
                    <td class="py-1.5 pr-2"><LinkInput v-if="!mrValidated" v-model="it.supplier" doctype="Supplier" placeholder="Proveedor…" /><span v-else>{{ it.supplier || '—' }}</span></td>
                  </tr>
                </tbody>
              </table>
              <p v-if="!mrValidated" class="text-[11px] text-ink-light -mt-1">Puedes ajustar hasta 5% de más o de menos de lo requerido (mermas/control de calidad, compra en múltiplos…) — de ahí no se deja pasar.</p>
              <p v-if="!mrValidated" class="text-[11px] text-ink-light -mt-1">La UDM y el precio se ajustan en la Orden de Compra que generes desde aquí, no en esta pantalla — ahí ya se sabe con qué proveedor específico se está comprando.</p>
            </div>

            <!-- Lotes de entrega: se definen ANTES de validar, para que al validar se
                 generen de un jalón todas las OC ya con su fecha -- en vez de crearlas
                 una por una después con "Nuevo lote". Se captura por PIEZAS de cada
                 producto terminado (igual que "Cantidad a producir" arriba) -- la
                 materia prima de cada lote se deriva sola (misma explosión de BOM que
                 ya usa el plan), en vez de calcularla a mano material por material. -->
            <div v-if="!mrValidated" class="border-t border-surface-border pt-3">
              <div class="flex items-center justify-between mb-1.5">
                <div>
                  <p class="section-title">Lotes de entrega (opcional)</p>
                  <p class="text-[11px] text-ink-light">Si la producción se va a escalonar en varias tandas, indica aquí cuántas PRENDAS lleva cada lote — la materia prima que le corresponde se calcula sola. Al validar se crean todas las órdenes de compra de un jalón, ya con su cantidad y fecha. Si no la divides, toda la solicitud queda como un solo lote.<template v-if="hayTallasEnLotes"> Los productos con tallas capturadas en la orden de venta se reparten TALLA POR TALLA: cada talla debe sumar exacto lo que pide la orden de venta, y las prendas del lote salen de esa suma.</template></p>
                </div>
                <button class="add-link shrink-0" @click="addMrLote(); actualizarPreviewLotes()"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>Lote</button>
              </div>
              <template v-if="mrLotes.length">
                <div v-for="lote in mrLotes" :key="lote.id" class="rounded-lg border border-surface-border p-2.5 mb-2">
                  <div class="flex items-center gap-2 mb-2">
                    <input v-model="lote.lote_ref" class="field-input w-24 text-[11.5px] font-semibold" title="Nombre del lote — usa el mismo que su lote de subcontratación para que aparezcan juntos" @change="actualizarPreviewLotes()" />
                    <input v-model="lote.fecha_requerida" type="date" class="field-input w-40" />
                    <span class="text-[11px] text-ink-light flex-1">Fecha requerida — si no divide exacto, el último lote se queda con el registro del resto.</span>
                    <button class="del-btn" @click="removeMrLote(lote.id)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button>
                  </div>
                  <!-- Productos SIN desglose por talla en la orden de venta: una sola
                       cantidad de prendas, igual que siempre. -->
                  <div class="grid grid-cols-2 gap-x-4 gap-y-1">
                    <div v-for="p in (planDetail.po_items || []).filter((x) => !tieneTallas(x.item_code))" :key="p.item_code" class="flex items-center gap-2">
                      <span class="text-[11.5px] font-mono flex-1 truncate" :title="`de ${p.planned_qty} pzas`">{{ p.item_code }}</span>
                      <input
                        v-model.number="lote.piezas[p.item_code]" type="number" min="0"
                        class="field-input w-24 text-right"
                        :class="mrLoteProductoExcedido(p.item_code) ? 'border-red-400 ring-1 ring-red-400' : ''"
                        @input="actualizarPreviewLotes()"
                      />
                    </div>
                  </div>
                  <!-- Productos CON desglose: se captura talla por talla. Las prendas del
                       lote NO se capturan, se derivan de la suma (api/tallas_lote.py), para
                       que el número grande y el detalle no puedan contradecirse. -->
                  <div
                    v-for="p in (planDetail.po_items || []).filter((x) => tieneTallas(x.item_code))"
                    v-show="lote.tallas && lote.tallas[p.item_code]"
                    :key="`tallas_${p.item_code}`" class="mt-1.5 first:mt-0"
                  >
                    <div class="flex items-baseline gap-2 mb-1">
                      <span class="text-[11.5px] font-mono truncate">{{ p.item_code }}</span>
                      <span
                        class="text-[11px]"
                        :class="mrLoteTotalFueraDeMargen(p.item_code) ? 'text-red-600 font-medium' : 'text-ink-light'"
                        :title="`entre todos los lotes: ${mrLoteTotalDeProducto(p.item_code)} de ${mrLoteMargenTotal(p.item_code).planned} (se permite de ${mrLoteMargenTotal(p.item_code).piso} a ${mrLoteMargenTotal(p.item_code).tope})`"
                      >{{ lote.piezas[p.item_code] || 0 }} prendas en este lote</span>
                    </div>
                    <div class="flex flex-wrap gap-1.5">
                      <label v-for="f in tallasDeLote(p.item_code)" :key="f.clave" class="flex flex-col">
                        <span
                          class="text-[10px] leading-none mb-0.5 text-center"
                          :class="mrLoteTallaDescuadrada(p.item_code, f.clave) ? 'text-amber-700 font-medium' : 'text-ink-light'"
                          :title="`${f.etiqueta || f.talla}: la orden de venta pide ${f.cantidad}`"
                        >{{ f.talla || f.etiqueta }}</span>
                        <input
                          v-model.number="lote.tallas[p.item_code][f.clave]" type="number" min="0"
                          class="field-input w-[4.5rem] !px-2 text-right text-[12px] tabular-nums"
                          :class="mrLoteTallaDescuadrada(p.item_code, f.clave) ? 'border-amber-400 ring-1 ring-amber-400' : ''"
                          @input="sincronizarPiezasDeTallas(lote); actualizarPreviewLotes()"
                        />
                      </label>
                    </div>
                  </div>
                  <div v-if="mrLotesPreview[lote.lote_ref] && Object.keys(mrLotesPreview[lote.lote_ref]).length" class="mt-2 pt-2 border-t border-surface-border text-[11px] text-ink-light">
                    <span class="text-ink-muted">Materiales estimados: </span>
                    <span v-for="(m, mat, i) in mrLotesPreview[lote.lote_ref]" :key="mat">{{ i > 0 ? ' · ' : '' }}{{ mat }}: {{ m.qty }} {{ m.uom }}</span>
                  </div>
                </div>
                <div class="flex items-center justify-between">
                  <button class="add-link" @click="repartirMrLotesIgual">Repartir en partes iguales</button>
                  <p class="text-[11px]">
                    <span class="text-ink-light">Pendiente sin asignar: </span>
                    <span
                      v-for="(p, i) in planDetail.po_items" :key="p.item_code"
                      :class="mrLoteProductoExcedido(p.item_code) ? 'text-red-600 font-medium' : (mrLoteProductoIncompleto(p.item_code) ? 'text-amber-700 font-medium' : 'text-ink-light')"
                    >{{ i > 0 ? ' · ' : '' }}{{ p.item_code }}: {{ mrLotePendiente(p.item_code) }} pzas</span>
                  </p>
                </div>
                <!-- Qué talla falta (o sobra) para cuadrar con la orden de venta: sin
                     esto hay que ir sumando columna por columna a mano. -->
                <p
                  v-for="p in (planDetail.po_items || []).filter((x) => mrLoteTallasDescuadradas(x.item_code))"
                  :key="`desc_${p.item_code}`" class="text-[11px] mt-0.5 text-amber-700"
                >
                  <span class="font-mono">{{ p.item_code }}</span> —
                  <template v-for="(f, i) in tallasDeLote(p.item_code).filter((x) => mrLoteTallaDescuadrada(p.item_code, x.clave))" :key="f.clave">
                    {{ i > 0 ? ' · ' : '' }}{{ f.talla || f.etiqueta }}:
                    {{ mrLoteTallaPendiente(p.item_code, f.clave) > 0
                       ? `faltan ${mrLoteTallaPendiente(p.item_code, f.clave)}`
                       : `sobran ${-mrLoteTallaPendiente(p.item_code, f.clave)}` }}
                  </template>
                </p>
                <p v-if="mrLotesInvalidos" class="text-[11.5px] mt-1" :class="(planDetail.po_items || []).some((p) => mrLoteProductoExcedido(p.item_code)) ? 'text-red-600' : 'text-amber-700'">
                  {{ (planDetail.po_items || []).some((p) => mrLoteTotalFueraDeMargen(p.item_code))
                    ? 'El total repartido de algún producto se sale del 5% que permite el plan — ajústalo antes de validar.'
                    : (planDetail.po_items || []).some((p) => mrLoteTallasDescuadradas(p.item_code))
                      ? 'El reparto por talla no cuadra con la orden de venta — cada talla debe sumar exacto entre todos los lotes.'
                      : (planDetail.po_items || []).some((p) => mrLoteProductoExcedido(p.item_code))
                        ? 'Algún producto tiene más piezas repartidas entre los lotes de las que pide el plan — ajústalo antes de validar.'
                        : 'Todavía quedan piezas sin repartir en ningún lote — los lotes deben sumar exacto el total del plan antes de validar.' }}
                </p>
              </template>
            </div>


          </template>
        </div>

        </template>

        <!-- ─── Paso 3 · Orden de manufactura ───
             Va ANTES de mandar las órdenes a los talleres: así cada orden sale ya
             con la ficha que le toca a ese taller (om_de_oc la arma al momento
             desde esta general, así que nunca se desincroniza). -->
        <template v-else>
          <OmGeneralEditor
            :costeo="docName" :sales-order="activeSOName || ''"
            :medidas-templates="medidasTemplates" :disabled="!puedeEditar('om')"
            :tablas-de-plantilla="tablasDePlantilla" :show-toast="showToast"
            @saved="onOmGuardada" @cargado="(c) => (omCapturadas = c)"
          />
        </template>
      </template>
        </div>

        <!-- ═══════════ ÓRDENES A TALLERES ═══════════
             Una por taller: se validan una vez y sirven para todos los lotes. Cada
             una ya lleva heredada la ficha de manufactura del paso anterior. -->
        <div v-else-if="pVista === 'ordenes'" class="space-y-3">
          <VacioEstado
            v-if="!subOcs.length" icono="taller"
            titulo="Aún no has creado las órdenes a talleres"
            detalle="Se crea una orden por proveedor (corte, costura, bordado…) — las etapas que comparten taller quedan juntas en la misma orden, cada una con su servicio y BOM de subcontratación."
          />
          <template v-else>
            <div v-if="!omCompleta" class="p-note">
              Todavía falta capturar la orden de manufactura ({{ omCapturadas.capturadas }} de {{ omCapturadas.total }}).
              Hasta tenerla no se pueden validar estas órdenes: cada una le lleva su ficha al taller.
            </div>
            <div class="p-panel">
              <FilaLista
                v-for="oc in subOcs" :key="oc.name"
                :estado="oc.docstatus === 1 ? 'ok' : 'wait'"
                :titulo="oc.supplier_name || oc.supplier" :meta="oc.name"
                @abrir="abrirOcTaller(oc)"
              >
                <template #derecha>
                  <span class="p-num text-[13px] w-28 text-right">{{ fmtC(oc.grand_total ?? oc.base_net_total) }}</span>
                  <Pill :estado="oc.docstatus === 1 ? 'ok' : 'wait'" :texto="oc.docstatus === 1 ? (oc.enviado_el ? 'Enviada' : 'Validada') : 'Borrador'" ancho="w-24" />
                </template>
              </FilaLista>
            </div>
            <p class="p-meta">Se abre cada una para revisarla, validarla y ver la ficha de manufactura que recibe ese taller.</p>
          </template>
        </div>

        <!-- ═══════════ LOTE ═══════════ -->
        <template v-else-if="pVista === 'lote'">
          <VacioEstado
            v-if="!loteActivo" icono="paquete" titulo="Elige un lote en el menú"
            detalle="O abre uno nuevo con “+ Nuevo lote”."
          />
          <template v-else>
            <!-- 1 · Materia prima (plan §5.5) -->
            <div v-if="pPasoLote === 'materia'" class="space-y-3">
              <!-- Neteo contra existencias propias (MRP): la OC se generó por menos de
                   lo que pide la solicitud porque este costeo ya tiene parte en el
                   almacén. Se avisa porque en tela el remanente puede ser de otro lote
                   de tintura y no servir -- la OC está en borrador y es editable. -->
              <div v-if="neteoOc.length" class="rounded-lg bg-blue-50 ring-1 ring-blue-200 px-3 py-2">
                <p class="text-[12px] font-medium text-blue-900 mb-1">Se descontó lo que ya tienes en almacén</p>
                <p v-for="n in neteoOc" :key="n.item_code" class="text-[11.5px] text-blue-900 tabular-nums">
                  {{ n.item_code }} · la solicitud pide {{ n.solicitud.toLocaleString('es-MX') }} · ya tienes {{ n.ya_tienes.toLocaleString('es-MX') }} ·
                  <b>se compran {{ n.comprar.toLocaleString('es-MX') }} {{ n.uom }}</b>
                </p>
                <p class="text-[11px] text-blue-800 mt-1">Si ese material no sirve para este pedido (otro lote de tintura, por ejemplo), sube la cantidad en la orden de compra antes de validarla.</p>
              </div>

              <!-- Un renglón por proveedor. El detalle (orden de compra, recibo y
                   factura) se abre en el panel lateral: la lista solo dice en qué va
                   cada quien. El ORDEN sale de material_items (todos los materiales
                   del lote, tengan OC o no) para que un proveedor no cambie de lugar
                   apenas genera su primer documento. -->
              <div v-if="proveedoresLote(loteActivo).length" class="p-panel">
                <FilaLista
                  v-for="grp in proveedoresLote(loteActivo)" :key="grp.supplier"
                  :estado="estadoProveedor(grp)" :titulo="grp.supplier" :meta="materialesDeProveedor(grp)"
                  @abrir="abrirPanelProveedor(grp)"
                >
                  <template #derecha>
                    <div class="hidden md:flex items-center gap-1.5 text-[11.5px] text-ink-light">
                      <template v-for="(paso, i) in caminoProveedor(grp)" :key="paso.clave">
                        <span v-if="i" aria-hidden="true">›</span>
                        <Pill v-if="paso.actual" :estado="paso.estado" :texto="paso.texto" />
                        <span v-else :class="paso.sinEnviar ? 'text-amber-600' : paso.estado === 'ok' || paso.estado === 'fac' ? 'text-emerald-600' : ''">{{ paso.texto }}</span>
                      </template>
                    </div>
                  </template>
                </FilaLista>
              </div>
              <VacioEstado
                v-else icono="paquete" titulo="Este lote todavía no tiene materiales"
                detalle="Se reparten al dividir la solicitud de material en lotes de entrega, en Preparación."
              />
            </div>

            <!-- 2 · Talleres (antes dos pasos: Flujo y Talleres) ───────────────
                 La matriz pieza x etapa ES el índice de talleres: sus columnas son
                 exactamente las paradas del lote (rama_etapas + rama_cadena =
                 paradas), y es la única vista que dice con qué piezas se trabaja.
                 Tener además una lista de talleres era la misma información dos
                 veces, en su versión sin piezas. Clic en una columna abre ese
                 taller; se vuelve con "← Talleres" de la barra. -->
            <div v-else-if="pPasoLote === 'talleres'" class="space-y-3">
            <template v-if="!pTallerAbierto">
              <!-- Flujo del lote: un CARRIL por producto -- sus paradas (talleres) en
                   orden, con el producto terminado al final. Click en una tarjeta =
                   abrir su detalle abajo. -->
              <div>
                <!-- Una RAMA por pieza, con SOLO los pasos por los que esa pieza
                     pasa: la espalda va directo del corte a la confección, el
                     frente lleva tres etapas. La vista por producto (abajo, para
                     costeos sin piezas declaradas) repetía las mismas cuatro
                     tarjetas en todas. -->
                <!-- MATRIZ pieza × etapa. Columnas fijas por etapa: una pieza que
                     se brinca una etapa deja "no aplica" en su columna en vez de
                     recorrer las demás, para poder comparar las piezas de un
                     vistazo. La selección es por celda y cruza talleres: marcas
                     dos mangas del bordado y los puños del reflejante, y salen
                     dos órdenes, una por taller. -->
                <div v-if="loteActivo.ramas && loteActivo.ramas.length" class="space-y-3">
                  <!-- Resumen: cuántas piezas hay en cada estado, con el mismo color
                       que su celda abajo (sirve de leyenda). -->
                  <div class="flex items-center gap-2 flex-wrap">
                    <span v-for="c in contadoresRamas" :key="c.k" class="inline-flex items-center gap-1.5 rounded-full bg-white ring-1 ring-surface-border px-2.5 py-1 text-[12px] text-ink-muted">
                      <EstadoPunto :estado="estadoContador(c.k)" /><b class="text-ink tabular-nums">{{ c.n }}</b> {{ c.txt }}
                    </span>
                  </div>

                  <!-- TABLERO pieza × taller. Cada columna es un taller (su etapa, su
                       proveedor y su precio; el título abre ese taller); cada fila, una
                       pieza. La celda dice SOLO en qué va esa pieza en ese taller:
                       "Por encargar" se marca (cruza talleres: una orden por taller),
                       lo que ya va en camino se abre, "—" es que no pasa por ahí. El
                       servicio solo se repite en la celda cuando la columna junta
                       servicios distintos (bordado del frente y de las mangas). -->
                  <div class="p-panel overflow-x-auto">
                    <div class="w-max min-w-full p-3">
                      <div class="flex gap-2 items-start pb-2 border-b border-surface-border">
                        <div class="w-32 flex-shrink-0 px-1 pt-0.5 text-[11px] font-medium text-ink-light">Pieza</div>
                        <div v-for="e in loteActivo.rama_etapas" :key="e.parada_id" class="w-48 flex-shrink-0 px-1">
                          <!-- Solo informa: al taller se entra por sus piezas (la celda). -->
                          <div class="w-full text-left">
                            <span class="flex items-start gap-2 min-w-0">
                              <span class="w-5 h-5 rounded-full bg-zinc-100 text-ink-muted text-[11px] font-semibold flex items-center justify-center flex-shrink-0">{{ e.orden }}</span>
                              <span class="text-[12.5px] font-semibold text-ink leading-snug line-clamp-2">{{ e.titulo }}</span>
                            </span>
                            <span class="block pl-7 mt-0.5 text-[11.5px] text-ink-muted truncate" :title="e.supplier">{{ e.supplier }}</span>
                            <span class="block pl-7 text-[11px] text-ink-light tabular-nums">${{ e.precio_prenda.toLocaleString('es-MX', { minimumFractionDigits: 2 }) }} por prenda</span>
                          </div>
                          <button data-nav v-if="e.listas" type="button" class="mt-1 ml-7 text-[11.5px] font-medium text-brand-600 hover:text-brand-700" @click="toggleColumna(e)">
                            {{ columnaTodaSel(e) ? 'Quitar selección' : `Elegir las ${e.listas} listas` }}
                          </button>
                        </div>
                      </div>

                      <div v-for="r in loteActivo.ramas" :key="r.pieza" class="flex gap-2 items-center py-1.5 border-b border-surface-border/60 last:border-0">
                        <div class="w-32 flex-shrink-0 px-1">
                          <p class="text-[13px] font-semibold text-ink leading-tight">{{ r.pieza }}</p>
                          <p class="text-[11px] text-ink-light tabular-nums">{{ r.por_prenda > 1 ? `×${r.por_prenda} · ${(r.por_prenda * prendasDelLote()).toLocaleString('es-MX')} pzas` : `${prendasDelLote().toLocaleString('es-MX')} pzas` }}</p>
                        </div>
                        <div v-for="e in loteActivo.rama_etapas" :key="e.parada_id" class="w-48 flex-shrink-0">
                          <div v-if="!celdaDe(r, e.parada_id)" class="h-12 flex items-center justify-center text-ink-xlight text-[13px]" title="Esta pieza no pasa por este taller">—</div>
                          <div v-else-if="celdaDe(r, e.parada_id).estado === 'bloqueado'" class="h-12 rounded-xl bg-zinc-50 px-3 flex items-center gap-2 text-[12px] text-ink-light" :title="tituloCelda(celdaDe(r, e.parada_id), r.pieza, e)">
                            <Icono nombre="reloj" class="w-3.5 h-3.5 flex-shrink-0" />
                            <span class="min-w-0"><span class="block">En espera</span><span v-if="variosServicios(e)" class="block text-[10.5px] truncate">{{ celdaDe(r, e.parada_id).servicio }}</span></span>
                          </div>
                          <div v-else class="relative group/celda">
                          <button data-nav
                            type="button"
                            :aria-pressed="celdaSeleccionada(r.pieza, e.parada_id)"
                            class="w-full h-12 rounded-xl px-3 flex items-center gap-2.5 text-left transition-colors"
                            :class="[celdaClass(celdaDe(r, e.parada_id), r.pieza, e), mismoEncargoEnHover(celdaDe(r, e.parada_id), e) ? 'ring-2 ring-offset-1 ring-ink/40 brightness-[0.97]' : '']"
                            :title="tituloCelda(celdaDe(r, e.parada_id), r.pieza, e)"
                            @mouseenter="hoverEncargo = encargoDeCelda(celdaDe(r, e.parada_id), e)"
                            @mouseleave="hoverEncargo = null"
                            @click="celdaDe(r, e.parada_id).estado === 'listo' ? marcarCelda(celdaDe(r, e.parada_id), r.pieza, e.parada_id) : entrarCelda(celdaDe(r, e.parada_id), r.pieza)"
                          >
                            <!-- Por encargar: casilla redonda; marcada se llena. -->
                            <span v-if="celdaDe(r, e.parada_id).estado === 'listo'" class="w-[18px] h-[18px] rounded-full flex-shrink-0 flex items-center justify-center border-2" :class="celdaSeleccionada(r.pieza, e.parada_id) ? 'bg-white border-white' : 'border-brand-300'">
                              <svg v-if="celdaSeleccionada(r.pieza, e.parada_id)" class="w-3 h-3 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="4"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
                            </span>
                            <svg v-else-if="celdaDe(r, e.parada_id).estado === 'recibido'" class="w-[18px] h-[18px] flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.7-9.3a1 1 0 00-1.4-1.4L9 10.6 7.7 9.3a1 1 0 00-1.4 1.4l2 2a1 1 0 001.4 0l4-4z" clip-rule="evenodd"/></svg>
                            <span class="min-w-0 flex-1">
                              <span class="block text-[12.5px] font-medium leading-tight truncate">{{ textoCelda(celdaDe(r, e.parada_id), r.pieza, e) }}</span>
                              <span v-if="variosServicios(e)" class="block text-[10.5px] opacity-75 truncate">{{ celdaDe(r, e.parada_id).servicio }}</span>
                              <!-- En camino: encargo → envío → recibo, en tres rayitas. -->
                              <span v-else-if="['encargado', 'enviado'].includes(celdaDe(r, e.parada_id).estado)" class="flex gap-1 mt-1">
                                <span v-for="p in pasosDeCelda(celdaDe(r, e.parada_id))" :key="p.clave" class="h-1 flex-1 rounded-full" :class="p.estado === 'hecho' ? 'bg-amber-500' : p.estado === 'actual' ? 'bg-amber-200' : 'bg-amber-100'" :title="p.texto"></span>
                              </span>
                            </span>
                            <span v-if="celdaDe(r, e.parada_id).estado !== 'listo'" class="flex-shrink-0 opacity-50 text-[15px] leading-none">›</span>
                          </button>
                          <!-- Deshacer el encargo, discreto: solo al pasar el mouse por una
                               pieza encargada que el taller todavía no entrega. -->
                          <button
                            v-if="celdaDe(r, e.parada_id).estado === 'encargado' && (celdaDe(r, e.parada_id).scos || []).length && puedeEditar('talleres')"
                            type="button" title="Deshacer este encargo"
                            class="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-white ring-1 ring-surface-border text-ink-light hover:text-red-600 hover:ring-red-200 flex items-center justify-center opacity-0 group-hover/celda:opacity-100 focus:opacity-100 transition-opacity"
                            @click.stop="pedirDeshacerCelda(celdaDe(r, e.parada_id), e)"
                          >
                            <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M3 10h10a5 5 0 015 5v2M3 10l5-5M3 10l5 5"/></svg>
                          </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Lo seleccionado NO se repite aquí: la barra de abajo dice cuántas
                       piezas, de qué talleres y tiene el botón para crear sus órdenes. -->
                  <!-- Después de las ramas: donde se unen las piezas (confección) y, si la
                       prenda armada todavía pasa por más talleres (acabado...), cada uno
                       en orden. Sin ensamble intermedio es solo la tarjeta final. -->
                  <template v-if="cadenaFinal.length">
                    <h2 class="p-eyebrow mt-8 mb-2">Después de las piezas</h2>
                    <div class="p-panel">
                      <FilaLista
                        v-for="(t, i) in cadenaFinal" :key="t.parada_id"
                        :orden="loteActivo.rama_etapas.length + 1 + i"
                        :estatica="!cadenaAbrible(t)"
                        @abrir="abrirTallerDeCadena(t)"
                      >
                        <template #titulo>
                          {{ t.titulo }}
                          <Pill v-if="t.arma_prenda" estado="off" texto="arma la prenda" class="ml-1" />
                        </template>
                        <template #meta>
                          {{ t.supplier }}<span v-if="t.facturado" class="ml-1.5 text-indigo-700 font-medium">· facturado</span>
                        </template>
                        <template #derecha>
                          <div v-if="t.arma_prenda" class="w-48 hidden md:block">
                            <p class="p-meta mb-1">{{ t.piezas_listas }} de {{ t.piezas_total }} piezas listas</p>
                            <div class="h-1 rounded bg-zinc-100 overflow-hidden">
                              <div class="h-full bg-emerald-500 rounded" :style="{ width: (t.piezas_listas / (t.piezas_total || 1) * 100) + '%' }"></div>
                            </div>
                          </div>
                          <p v-else class="p-meta w-48 hidden md:block">Recibe la prenda armada de {{ cadenaFinal[i - 1]?.supplier }}</p>
                          <Pasos v-if="paradaDeEtapa(t)" class="hidden lg:flex" compacto :pasos="pasosDeParada(paradaDeEtapa(t))" />
                          <Pill :estado="estadoCadena(t)" :texto="textoCadena(t)" ancho="w-28" />
                          <!-- Encargarla es UN solo botón, el de la barra de abajo
                               ("Encargar confección"): aquí repetirlo confundía. -->
                        </template>
                      </FilaLista>
                    </div>
                  </template>
                </div>

                <div v-else class="space-y-4">
                  <div v-for="track in tracksLote" :key="track.finished_item">
                    <p class="text-[12px] font-semibold text-ink mb-1.5 flex items-center gap-1.5">
                      <svg class="w-3.5 h-3.5 text-ink-light" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M16 4l4 4-3 1v11H7V9L4 8l4-4 2 2h4l2-2z"/></svg>
                      {{ track.item_name }}<span class="font-normal text-ink-muted">· {{ track.qty }} pza(s)</span>
                    </p>
                    <div class="overflow-x-auto -mx-1 px-1">
                      <div class="flex items-stretch gap-2 w-max">
                        <template v-for="(pa, i) in track.paradas" :key="pa.parada_id">
                          <svg v-if="i > 0" class="w-4 h-4 text-ink-xlight self-center flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
                          <button data-nav
                            class="text-left w-48 rounded-lg border px-2.5 py-2 transition-colors flex-shrink-0"
                            :class="paradaBtnClass(pa)"
                            @click="irAParada(pa)"
                          >
                            <div class="flex items-center gap-1.5 mb-0.5">
                              <span class="w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0" :class="paradaDotClass(pa)">
                                <svg v-if="pa.receipt_validated" class="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="4"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
                              </span>
                              <span class="text-[12px] font-semibold text-ink truncate">{{ pa.titulo }}</span>
                            </div>
                            <p class="text-[11px] text-ink-muted truncate">{{ pa.supplier }}</p>
                            <p class="text-[10.5px] text-ink-light">{{ (pa.productos.find((x) => x.finished_item === track.finished_item) || {}).qty }} pza(s)</p>
                            <p class="text-[10.5px] mt-0.5" :class="paradaEstadoColor(pa)">{{ paradaEstadoTexto(pa) }}</p>
                          </button>
                        </template>
                        <!-- Producto terminado -->
                        <svg class="w-4 h-4 text-ink-xlight self-center flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
                        <div
                          class="w-40 rounded-lg border-2 px-2.5 py-2.5 flex-shrink-0 flex flex-col items-center text-center"
                          :class="track.done ? 'border-green-400 bg-green-50' : 'border-surface-border bg-white'"
                        >
                          <img v-if="track.image" :src="track.image" :alt="track.item_name" class="w-16 h-16 object-cover rounded mb-1.5" />
                          <div v-else class="w-16 h-16 rounded bg-surface-raised flex items-center justify-center mb-1.5">
                            <svg class="w-8 h-8 text-ink-xlight" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.4"><path stroke-linecap="round" stroke-linejoin="round" d="M16 4l4 4-3 1v11H7V9L4 8l4-4 2 2h4l2-2z"/></svg>
                          </div>
                          <span class="text-[11.5px] font-semibold text-ink leading-tight">{{ track.item_name }}</span>
                          <span class="text-[10.5px] text-ink-muted mt-0.5">{{ track.qty }} pza(s)</span>
                          <span class="text-[10px] mt-0.5 font-medium" :class="track.done ? 'text-green-700' : 'text-ink-light'">{{ track.done ? 'Terminado' : 'En proceso' }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </template>
            <div v-else-if="paradaActiva" class="space-y-3">
              <!-- SOLO INFORMACIÓN: con qué piezas se está trabajando en este taller.
                   Qué piezas se encargan (todas, una, dos...) se decide en la matriz de
                   Talleres, que es donde está la selección; aquí nada se marca ni se
                   abre, para que esta pantalla sea la del DOCUMENTO y no otra lista de
                   piezas que compite con la matriz. -->
              <!-- Qué piezas van en este taller se ve (y se elige) en el tablero; aquí
                   solo el botón para volver a él. -->
              <button type="button" class="p-btn-secondary h-9 text-[13px] inline-flex items-center gap-1.5" @click="salirDelTaller">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/></svg>
                Volver al tablero de piezas
              </button>
              <!-- Encargo hecho por error (p. ej. una sola pieza del corte): se deshace
                   mientras el taller no haya entregado nada. -->
              <button
                v-if="puedeDeshacerEncargo" type="button"
                class="ml-2 h-9 px-3 text-[13px] text-red-600 hover:bg-red-50 rounded-lg inline-flex items-center gap-1.5"
                @click="pedirDeshacerEncargo(scoSel.name, scoSel.supplier, !!scoSel.transfer?.done, paradaActiva?.parada_id)"
              >
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 10h10a5 5 0 015 5v2M3 10l5-5M3 10l5 5"/></svg>
                Deshacer encargo
              </button>
              <!-- El "siguiente paso" de esta parada (guiaParada) vive ahora en la
                   barra de abajo: su título y detalle en la línea de estado, su acción
                   en la primaria y la alterna como secundaria. Los cuatro documentos
                   son el stepper del encabezado; la orden de compra del taller y su
                   ficha de manufactura, los dos botones de arriba a la derecha. -->
              <!-- Lo que se capturó en la orden del taller (a dónde entrega cada pieza y su
                   orden de manufactura), a la vista en Encargo y Envío. Solo lectura. -->
              <TituloDocumento
                v-if="subStepOpen === 'sco'" titulo="Encargo al taller"
                :codigo="scoSel?.name || ''" :docstatus="scoSel?.docstatus || 0"
              />
              <TituloDocumento
                v-else-if="subStepOpen === 'transfer'" titulo="Envío de material"
                :codigo="transDoc?.name || ''" :docstatus="transDoc?.docstatus || 0" :etiqueta="transValidated ? 'Enviado' : ''"
              />
              <TituloDocumento
                v-else-if="subStepOpen === 'recibo'" titulo="Recibo del taller"
                :codigo="scr?.name || ''" :docstatus="scr?.docstatus || 0" :etiqueta="scrValidated ? 'Recibido' : ''"
              />
              <InfoOrdenTaller v-if="paradaActiva.po && subStepOpen === 'sco'" :po="paradaActiva.po" class="mb-3" />
              <!-- Orden de subcontratación (SCO) -->
              <template v-if="subStepOpen === 'sco'">
                <!-- Encargos (Subcontracting Order) de esta parada: una parada puede
                     tener VARIOS cuando el taller va entregando por tandas (ver
                     parada_registrar_entrega). OJO con el vocabulario: cada uno es
                     el ENCARGO al taller, no su entrega -- lo que el taller
                     devuelve es el recibo de maquila, un paso después. -->
                <!-- Con piezas NO va: el tablero ya encarga (marcar + Crear orden), dice qué
                     falta y abre cada encargo desde su pieza. Queda solo para costeos sin
                     piezas, donde es la única forma de encargar por tandas. -->
                <div v-if="paradaActiva.sco && !loteActivo.ramas?.length" class="mb-3">
                  <div class="flex items-center justify-between mb-1.5">
                    <span class="text-[11.5px] font-medium text-ink-muted uppercase tracking-wide">Encargos a este taller</span>
                    <button type="button" class="text-[11px] text-brand-600 hover:text-brand-700" @click="abrirNuevaEntrega">+ Otro encargo</button>
                  </div>
                  <div class="space-y-1">
                    <button
                      v-for="e in paradaActiva.entregas" :key="e.sco"
                      type="button"
                      class="w-full flex items-center justify-between gap-2 text-[12px] px-2.5 py-1.5 rounded-md transition-colors"
                      :class="scoSel && scoSel.name === e.sco ? 'bg-brand-50 ring-1 ring-brand-200' : 'hover:bg-surface-raised'"
                      @click="subStepOpen = 'sco'; verEntrega(e)"
                    >
                      <span class="min-w-0 text-left">
                        <span class="block truncate text-ink">{{ e.referencia_entrega || 'Sin referencia' }}</span>
                        <span class="block text-[10.5px] text-ink-light">{{ e.sco }}</span>
                      </span>
                      <span class="flex items-center gap-2 flex-shrink-0 text-ink-light tabular-nums">
                        <span>{{ (e.cantidad || 0).toLocaleString('es-MX') }} prendas</span>
                        <span v-if="e.receipt_validated" class="flex items-center gap-1 text-green-700"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>recibido</span>
                        <span v-else-if="e.transfer_done" class="text-brand-600">enviado, falta recibir</span>
                        <span v-else class="text-amber-700">por enviar</span>
                      </span>
                    </button>
                  </div>

                  <!-- Checklist de sub-ensamblajes declarados (vacío si el producto no declaró ninguno) -->
                  <div v-if="paradaActiva.sub_ensamblajes.length" class="flex flex-wrap gap-1.5 mt-2">
                    <span
                      v-for="s in paradaActiva.sub_ensamblajes" :key="s.nombre"
                      class="text-[11px] px-2 py-0.5 rounded-full"
                      :class="s.pendiente ? 'bg-surface-raised text-ink-light' : 'bg-green-50 text-green-700 ring-1 ring-green-200'"
                    >{{ s.nombre }}</span>
                  </div>

                  <div v-if="nuevaEntregaForm.open" class="mt-2 rounded-lg ring-1 ring-surface-border p-2.5 space-y-2">
                    <div class="flex items-center gap-2">
                      <input v-model.number="nuevaEntregaForm.cantidad" type="number" min="0" step="1" placeholder="Cantidad" class="field-input w-28" />
                      <select v-if="paradaActiva.sub_ensamblajes.length" v-model="nuevaEntregaForm.sub_ensamblaje" class="field-input flex-1">
                        <option value="">Todas las piezas, de una vez</option>
                        <option v-for="s in paradaActiva.sub_ensamblajes" :key="s.nombre" :value="s.nombre">Solo {{ s.nombre }}</option>
                      </select>
                      <input v-else v-model="nuevaEntregaForm.referencia" type="text" placeholder="Referencia (opcional)" class="field-input flex-1" />
                    </div>
                    <div class="flex justify-end gap-2">
                      <button type="button" class="px-3 py-1.5 text-[12px] text-ink-muted hover:text-ink" @click="cerrarNuevaEntrega">Cancelar</button>
                      <button type="button" :disabled="nuevaEntregaForm.loading" class="px-3 py-1.5 text-[12px] font-medium text-white bg-brand-500 rounded-md hover:bg-brand-600 disabled:opacity-50" @click="confirmarNuevaEntrega">{{ nuevaEntregaForm.loading ? 'Encargando…' : 'Encargar' }}</button>
                    </div>
                  </div>
                </div>

                <!-- Una parada con varias piezas (Puños, Mangas...) NO necesita
                     nada especial aquí: se encarga igual que cualquier otra, con
                     la cantidad del lote, y el sistema abre esas prendas a piezas
                     (los puños van 2, ver _piezas_por_prenda_de_po). Hubo un
                     formulario aparte que pedía cantidad y pieza a mano; sobraba
                     -- las dos cosas ya se saben. Encargar UNA sola pieza sigue
                     disponible, pero donde tiene sentido: en "+ Otro encargo",
                     para los pasos encadenados en el mismo taller que sí llegan
                     por tandas (bordado -> sublimado -> bordado). -->
                <!-- Con piezas, se encarga desde el tablero: aquí solo se dice eso. -->
                <VacioEstado
                  v-if="!paradaActiva.sco && piezasDeParada(paradaActiva.parada_id).length"
                  icono="bandeja" titulo="Todavía no le encargas nada a este taller"
                  detalle="Vuelve a Talleres, toca las piezas «Por encargar» y crea la orden. Se usa la cantidad y la fecha del lote."
                />
                <div v-else-if="!paradaActiva.sco" class="text-center py-6">
                  <p class="text-sm font-medium text-ink mb-1">{{ paradaActiva.titulo }} · {{ paradaActiva.supplier }} — {{ loteActivoRef }}</p>
                  <template v-if="paradaActiva.productos.some((x) => x.qty > 0) || loteActivo.productos.some((x) => x.qty > 0)">
                    <p class="text-[12.5px] text-ink-muted mb-3">
                      Se encarga con la cantidad del lote ({{ paradaProductosTexto(paradaActiva.productos.some((x) => x.qty > 0) ? paradaActiva.productos : loteActivo.productos) }}) y fecha del lote.
                      <template v-if="paradaActiva.sub_ensamblajes.length">
                        <br />Incluye las {{ paradaActiva.sub_ensamblajes.length }} piezas ({{ paradaActiva.sub_ensamblajes.map((s) => s.nombre).join(', ') }}); los puños y demás se multiplican solos.
                      </template>
                    </p>
                    <!-- Un solo lugar para encargar. Cuando el lote tiene piezas,
                         ese lugar es la MATRIZ de arriba: ahí se eligen las piezas
                         y se crea una orden por taller. Aquí abajo solo se guía
                         hacia allá -- antes convivían tres botones que hacían casi
                         lo mismo y no se sabía cuál usar. Sin piezas declaradas la
                         matriz no existe, y entonces sí este es el botón. -->
                    <template v-if="piezasDeParada(paradaActiva.parada_id).length">
                      <p class="text-[12.5px] text-ink-muted">
                        Elige las piezas en la matriz de arriba y pulsa <strong class="text-ink">Crear orden</strong>.
                      </p>
                    </template>
                    <button data-nav v-else :disabled="advancing" class="px-4 py-2 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50" @click="abrirParada()">Encargar a {{ paradaActiva.supplier }}</button>
                  </template>
                  <template v-else>
                    <p class="text-[12.5px] text-ink-muted mb-3">Este lote todavía no tiene cantidad definida (nació de materia prima) — indícala aquí.</p>
                    <p v-if="primeraEtapaLoading" class="text-[11px] text-ink-light mb-2">Revisando materia prima disponible…</p>
                    <div class="flex items-center justify-center gap-2 mb-2">
                      <input v-model.number="primeraEtapaQty" type="number" min="0" step="1" placeholder="Cantidad" :disabled="primeraEtapaLoading" class="field-input w-32 text-center" />
                      <button data-nav :disabled="advancing || primeraEtapaLoading" class="px-4 py-2 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50" @click="abrirParada(primeraEtapaQty)">Encargar a {{ paradaActiva.supplier }}</button>
                    </div>
                    <p v-if="!primeraEtapaLoading && primeraEtapaLimitado" class="text-[11.5px] text-amber-700 flex items-center justify-center gap-1.5">
                      <svg class="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M5.07 19h13.86a2 2 0 001.71-3l-6.93-12a2 2 0 00-3.42 0l-6.93 12a2 2 0 001.71 3z"/></svg>
                      Cantidad sugerida según la materia prima disponible en stock — puedes ajustarla a mano.
                    </p>
                  </template>
                </div>

                <div v-else-if="scoSel" class="space-y-3">
                  <details class="p-panel group" :open="!scoValidated">
                    <summary class="px-5 py-3 cursor-pointer text-[13px] font-medium flex items-center justify-between list-none">
                      <span>Datos del encargo</span>
                      <span class="p-meta group-open:hidden">almacenes · direcciones · contacto</span>
                    </summary>
                    <div class="px-4 pb-4">
                    <div class="flex justify-end mb-2">
                      <a class="doc-action" :href="`/app/subcontracting-order/${scoSel.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>ERPNext</a>
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                      <div><label class="field-label">Almacén del taller (proveedor)</label><select v-model="scoForm.supplier_warehouse" :disabled="scoValidated" class="field-input"><option value="">— Selecciona —</option><option v-for="w in flujo.warehouses" :key="w.name" :value="w.name">{{ w.warehouse_name || w.name }}</option></select></div>
                      <div><label class="field-label">Almacén de destino (producto terminado)</label><select v-model="scoForm.set_warehouse" :disabled="scoValidated" class="field-input"><option value="">— Selecciona —</option><option v-for="w in flujo.warehouses" :key="w.name" :value="w.name">{{ w.warehouse_name || w.name }}</option></select></div>
                      <div><label class="field-label">Dirección del proveedor</label><select v-model="scoForm.supplier_address" :disabled="scoValidated" class="field-input"><option value="">— Sin dirección —</option><option v-for="a in flujo.address_options" :key="a.value" :value="a.value">{{ a.label }}</option></select></div>
                      <div><label class="field-label">Contacto</label><select v-model="scoForm.contact_person" :disabled="scoValidated" class="field-input"><option value="">— Sin contacto —</option><option v-for="c in flujo.contact_options" :key="c.value" :value="c.value">{{ c.label }}</option></select></div>
                      <div><label class="field-label">Dirección de envío</label><select v-model="scoForm.shipping_address" :disabled="scoValidated" class="field-input"><option value="">— Sin dirección —</option><option v-for="a in flujo.address_options" :key="a.value" :value="a.value">{{ a.label }}</option></select></div>
                      <div><label class="field-label">Distribuir costos adicionales por<AyudaDistribuir /></label><select v-model="scoForm.distribute_additional_costs_based_on" :disabled="scoValidated" class="field-input"><option value="Qty">Cantidad</option><option value="Amount">Importe</option></select></div>
                    </div>
                    </div>
                  </details>
                  <EncargoResumen :sco="scoSel" :materiales="materialesSco" :piezas="piezasSco" :servicios="serviciosSco" :importe="importeSco" :nombres-pieza="nombrePorSlug" />

                  <!-- Los costos adicionales de la orden de subcontratación NO los copia ERPNext al
                       recibo: nunca llegaban al inventario ni a cuentas por pagar. Los fletes se
                       capturan en la transferencia (ida) o en el recibo (regreso). Aquí solo se
                       muestran los que ya existían, de solo lectura. -->
                  <details v-if="scoCostos.length" class="p-panel group">
                    <summary class="px-5 py-3 cursor-pointer text-[13px] font-medium list-none">Costos adicionales (registro anterior)</summary>
                    <div class="px-4 pb-4">
                    <div v-for="(c, i) in scoCostos" :key="i" class="flex items-center gap-2 mb-1.5">
                      <input v-model="c.description" disabled class="field-input flex-1" />
                      <input v-model.number="c.amount" type="number" disabled class="field-input w-32 text-right" />
                    </div>
                    <p class="text-[11px] text-ink-muted mt-1">Los fletes se registran en la transferencia al taller (ida) o en el recibo del taller (regreso), donde sí se suman al costo del producto y a lo que se le debe al transportista.</p>
                    </div>
                  </details>

                  <!-- Guardar / Validar están en la barra de abajo. -->
                  <div class="flex items-center gap-2 flex-wrap">
                    <button data-libre class="doc-action" @click="openPdf('Subcontracting Order', scoSel.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>Vista previa</button>
                    <span v-if="scoValidated" class="text-[13px] text-green-700 font-medium flex items-center gap-1.5"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Validada · continúa con la transferencia</span>
                  </div>
                </div>
              </template>

              <!-- Transferencia de material -->
              <template v-if="subStepOpen === 'transfer'">
                <div v-if="scoValidated" class="space-y-3">
                  <!-- Arriba, el documento a revisar (abierto mientras está en borrador:
                       almacenes y cantidades por material, fletes); debajo, el resumen
                       de lo que se le manda al taller. -->
                  <details v-if="transDoc" class="p-panel group" :open="!transValidated">
                    <summary class="px-5 py-3 cursor-pointer text-[13px] font-medium flex items-center justify-between list-none">
                      <span>Datos del envío</span>
                      <span class="p-meta group-open:hidden">almacenes · cantidades · fletes</span>
                    </summary>
                    <div class="px-4 pb-4">
                    <div class="bg-white rounded-xl border border-surface-border p-4">
                      <!-- Folio y estado ya van en el encabezado del paso (TituloDocumento). -->
                      <div class="flex items-center justify-end mb-3">
                        <a class="doc-action" :href="`/app/stock-entry/${transDoc.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>ERPNext</a>
                        </div>
                      <div class="grid grid-cols-2 gap-3 mb-3">
                        <div>
                          <label class="field-label">Almacén de origen <span class="text-ink-light font-normal">(por defecto, para las filas de abajo)</span></label>
                          <select v-model="transForm.from_warehouse" :disabled="transValidated" class="field-input"><option value="">— Selecciona —</option><option v-for="w in flujo.warehouses" :key="w.name" :value="w.name">{{ w.warehouse_name || w.name }}</option></select>
                          <div class="flex items-center gap-3 mt-1 flex-wrap">
                            <button v-if="!transValidated && transDoc.recommended_source" class="add-link" @click="aplicarAlmacenOrigenATodos(transDoc.recommended_source)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>Usar recomendado en todas ({{ transDoc.recommended_source }})</button>
                            <button v-if="!transValidated && transForm.from_warehouse" class="add-link" @click="aplicarAlmacenOrigenATodos(transForm.from_warehouse)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/></svg>Aplicar a todas las filas</button>
                          </div>
                        </div>
                        <div><label class="field-label">Almacén destino (taller / proveedor)</label><select v-model="transForm.to_warehouse" :disabled="transValidated" class="field-input"><option value="">— Selecciona —</option><option v-for="w in flujo.warehouses" :key="w.name" :value="w.name">{{ w.warehouse_name || w.name }}</option></select></div>
                      </div>
                      <p v-if="!transValidated" class="text-[11px] text-ink-light -mt-2 mb-2">Cada material puede salir de un almacén distinto (ej. un semiterminado de Trabajo en Proceso, un avío comprado directo de Materia Prima) — ajusta el almacén por fila si hace falta.</p>
                      <div class="overflow-x-auto">
                        <table class="w-full text-sm">
                          <thead><tr class="text-left text-xs font-semibold text-ink-light border-b border-surface-border"><th class="py-2">Material</th><th class="py-2 w-24 text-right">A transferir</th><th class="py-2 w-44">Almacén de origen</th><th class="py-2 w-24 text-right">{{ transValidated ? 'Quedó en almacén' : 'Disponible' }}</th><th class="py-2 w-16">UOM</th></tr></thead>
                          <tbody>
                            <!-- Un renglón por MATERIAL, no por pieza: al taller se le
                                 entrega un montón de tela, no un corte por cada pieza
                                 que la va a usar. El documento sí conserva el detalle
                                 por pieza (ERPNext lo necesita para conciliar lo
                                 consumido); cambiar aquí el total lo reparte entre
                                 ellas en la misma proporción. -->
                            <tr v-for="g in transAgrupado" :key="g.item_code" class="border-b border-surface-border/60">
                              <td class="py-1.5 pr-2">
                                <span class="block text-ink">{{ nombreVisible(g.item_name || g.item_code).titulo }}</span>
                                <span v-if="nombreVisible(g.item_name || g.item_code).sub" class="block text-[10.5px] text-ink-light">{{ nombreVisible(g.item_name || g.item_code).sub }}</span>
                              </td>
                              <td class="py-1.5 pr-2"><input v-if="!transValidated" :value="cantidadVisible(g.qty)" type="number" min="0" step="1" class="field-input text-right" @change="cambiarCantidadMaterial(g, $event.target.value)" /><span v-else class="block text-right tabular-nums">{{ cantidadVisible(g.qty).toLocaleString('es-MX') }}</span></td>
                              <td class="py-1.5 pr-2">
                                <select v-if="!transValidated" :value="g.s_warehouse" class="field-input" @change="cambiarAlmacenDeMaterial(g, $event.target.value)"><option value="">— Selecciona —</option><option v-for="w in flujo.warehouses" :key="w.name" :value="w.name">{{ w.warehouse_name || w.name }}</option></select>
                                <span v-else class="text-ink-muted text-xs">{{ g.s_warehouse }}</span>
                              </td>
                              <td class="py-1.5 pr-2 text-right tabular-nums" :class="!transValidated && (g.available ?? 0) < g.qty ? 'text-red-600 font-semibold' : 'text-ink-muted'">{{ g.available === null ? '—' : g.available.toLocaleString('es-MX', { maximumFractionDigits: 3 }) }}</td>
                              
                              <td class="py-1.5 pr-2 text-ink-muted text-xs">{{ g.uom }}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                      <!-- El descuento ya viene aplicado desde que se crea la
                           transferencia (_descontar_lo_que_ya_tiene_el_taller): la
                           regla es que mientras queden prendas por hacer el taller
                           usa su sobrante. Aquí solo se avisa, sin botón: volver a
                           descontarlo a mano lo restaría dos veces. -->
                      <!-- Nota discreta, no aviso: el sobrante sale del reparto interno por pieza. -->
                      <p v-if="!transValidated && transAgrupado.some(g => sobranteVisible(g.ya_en_taller))" class="text-[11.5px] text-ink-light mt-2">
                        Incluye {{ transAgrupado.filter(g => sobranteVisible(g.ya_en_taller)).map(g => `${Math.floor(g.ya_en_taller).toLocaleString('es-MX')} ${String(g.uom || '').split(' - ')[0]} de ${nombreVisible(g.item_name || g.item_code).titulo.toLowerCase()}`).join(', ') }} que el taller ya tenía de un envío anterior.
                      </p>
                      <p v-if="transValidated" class="text-[11px] text-ink-light mt-2">El material ya salió al almacén del taller. "Quedó en almacén" es lo que permaneció en el almacén de origen — no es un faltante.</p>
                      <p v-if="!transValidated && transDoc.items.some(it => (it.available ?? 0) < it.qty)" class="text-[12px] text-red-600 mt-2 flex items-start gap-1.5"><svg class="w-4 h-4 flex-shrink-0 mt-px" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M5.07 19h13.86a2 2 0 001.71-3l-6.93-12a2 2 0 00-3.42 0l-6.93 12a2 2 0 001.71 3z"/></svg>No hay stock suficiente en el almacén de origen. Cámbialo por el almacén donde recibiste la materia prima, o cómprala/recíbela primero (Recibo de compra).</p>
                    </div>

                    <div class="bg-white rounded-xl border border-surface-border p-4 mt-3">
                      <div class="flex items-center justify-between mb-1.5">
                        <p class="section-title">Costos adicionales</p>
                        <button v-if="!transValidated" class="add-link" @click="addCostoTrans"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>Costo</button>
                      </div>
                      <p v-if="!transCostos.length" class="prod-empty mb-1">Sin costos adicionales (fletes, maniobras…) — se capitalizan al valor del material transferido.</p>
                      <div v-for="(c, i) in transCostos" :key="i" class="flex items-center gap-2 mb-1.5">
                        <input v-model="c.description" placeholder="Descripción" :disabled="transValidated" class="field-input flex-1" />
                        <div class="w-56 flex-shrink-0" :title="c.factura_flete ? 'Factura del flete ' + c.factura_flete : c.poliza_flete ? 'Póliza ' + c.poliza_flete : 'Proveedor de paquetería al que se le paga el flete'">
                          <LinkInput v-model="c.proveedor_flete" doctype="Supplier" :filters="FILTRO_TRANSPORTISTA" placeholder="Transportista…" :readonly="transValidated" :error="!transValidated && c.amount > 0 && !c.proveedor_flete" />
                        </div>
                        <input v-model.number="c.amount" type="number" min="0" step="0.01" placeholder="Importe" :disabled="transValidated" class="field-input w-32 text-right" />
                        <label class="flex items-center gap-1 text-[11.5px] text-ink-muted whitespace-nowrap" title="Marca si el importe que capturaste ya trae IVA. Al inventario va la base sin IVA; el IVA se acredita en la factura del flete.">
                          <input v-model="c.flete_incluye_iva" type="checkbox" :true-value="1" :false-value="0" :disabled="transValidated" />IVA incluido
                        </label>
                        <button v-if="!transValidated" class="del-btn" @click="removeCostoTrans(i)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button>
                      </div>
                      <div v-if="transCostos.length" class="mt-1">
                        <label class="field-label">Distribuir por<AyudaDistribuir /></label>
                        <select v-model="transForm.distribute_additional_costs_based_on" :disabled="transValidated" class="field-input w-40"><option value="Qty">Cantidad</option><option value="Amount">Importe</option></select>
                      </div>
                    </div>

                    <!-- Guardar / Validar viven en la barra de abajo; aquí solo
                         queda la vista previa, que no avanza el flujo. -->
                    <div class="flex items-center gap-2 flex-wrap mt-3">
                      <button data-libre class="doc-action" @click="openPdf('Stock Entry', transDoc.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>Vista previa</button>
                      <span v-if="transValidated" class="text-[13px] text-green-700 font-medium flex items-center gap-1.5"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Material transferido · continúa con el recibo</span>
                    </div>
                    </div>
                  </details>
                  <div class="p-panel p-4">
                    <p v-if="!transDoc" class="p-meta mb-3">Crea el movimiento de materia prima (Stock Entry · Enviar a subcontratista) hacia el almacén del taller. Se crea en <b>borrador</b> para que ajustes almacenes y lo valides.</p>
                    <p v-if="scoSel" class="p-eyebrow mb-2">Lo que se le manda · según el encargo {{ scoSel.name }}</p>
                    <EncargoResumen v-if="scoSel" :sco="scoSel" :materiales="materialesSco" :piezas="piezasSco" :servicios="serviciosSco" :importe="importeSco" :nombres-pieza="nombrePorSlug" />
                    <p v-else class="prod-empty">Selecciona el encargo para ver qué se le va a mandar al taller.</p>
                    <p v-if="!transDoc" class="p-meta mt-3">Al enviar, el recibo queda listo para que confirmes cuánto entregó el taller.</p>
                  </div>
                </div>
              </template>

              <!-- Recibo de subcontratación -->
              <template v-if="subStepOpen === 'recibo'">
                <div v-if="transferDone">
                  <div v-if="!scr" class="bg-white rounded-xl border border-surface-border p-6 text-center">
                    <p class="text-[12.5px] text-ink-muted">Genera el recibo de subcontratación para ingresar a inventario lo que produjo el taller.</p>
                  </div>
                  <template v-else>
                    <!-- Con un solo recibo la tira solo repetía el encabezado del paso. -->
                    <TiraRecibos
                      v-if="(scoSel?.receipts || []).length > 1"
                      :recibos="scoSel.receipts" :activo="scr?.name"
                      :completo="scoSel.estado_recibos?.recibido_completo" :pendiente="scoSel.estado_recibos?.pendiente_recibir"
                      @abrir="(n) => loadScr(n)"
                    />
                    <div class="bg-white rounded-xl border border-surface-border p-4">
                      <div class="flex items-center justify-end mb-3">
                        <a class="doc-action" :href="`/app/subcontracting-receipt/${scr.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>ERPNext</a>
                      </div>
                      <div class="grid grid-cols-3 gap-3 mb-3">
                        <div><label class="field-label">Almacén aceptado</label><select v-model="scrForm.set_warehouse" :disabled="scrValidated" class="field-input"><option value="">— Selecciona —</option><option v-for="w in flujo.warehouses" :key="w.name" :value="w.name">{{ w.warehouse_name || w.name }}</option></select></div>
                        <div><label class="field-label">Almacén rechazado</label><select v-model="scrForm.rejected_warehouse" :disabled="scrValidated" class="field-input"><option value="">— Selecciona —</option><option v-for="w in flujo.warehouses" :key="w.name" :value="w.name">{{ w.warehouse_name || w.name }}</option></select></div>
                        <div><label class="field-label">Almacén del taller (proveedor)</label><select v-model="scrForm.supplier_warehouse" :disabled="scrValidated" class="field-input"><option value="">— Selecciona —</option><option v-for="w in flujo.warehouses" :key="w.name" :value="w.name">{{ w.warehouse_name || w.name }}</option></select></div>
                      </div>
                      <table class="w-full text-sm">
                        <thead><tr class="text-left text-xs font-semibold text-ink-light border-b border-surface-border"><th class="py-2">Producto</th><th class="py-2 w-20 text-right">Aceptado</th><th class="py-2 w-20 text-right">Rechazado</th><th class="py-2 w-16">UOM</th></tr></thead>
                        <tbody>
                          <tr v-for="it in scr.items" :key="it.name" class="border-b border-surface-border/60">
                            <td class="py-1.5 pr-2">
                              <span class="block text-ink">{{ nombreVisible(it.item_name || it.item_code).titulo }}</span>
                              <span v-if="nombreVisible(it.item_name || it.item_code).sub" class="block text-[10.5px] text-ink-light">{{ nombreVisible(it.item_name || it.item_code).sub }}</span>
                            </td>
                            <td class="py-1.5 pr-2"><input v-if="!scrValidated" v-model.number="it.qty" type="number" min="0" class="field-input text-right" /><span v-else class="block text-right">{{ it.qty }}</span></td>
                            <td class="py-1.5 pr-2"><input v-if="!scrValidated && it.rejected_qty !== null" v-model.number="it.rejected_qty" type="number" min="0" class="field-input text-right" /><span v-else class="block text-right">{{ it.rejected_qty ?? 0 }}</span></td>
                            <td class="py-1.5 pr-2 text-ink-muted text-xs">{{ it.stock_uom }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>

                    <div class="bg-white rounded-xl border border-surface-border p-4 mt-3">
                      <div class="flex items-center justify-between mb-1.5">
                        <p class="section-title">Costos adicionales <span v-if="!scrValidated" class="text-red-400">*</span></p>
                        <button v-if="!scrValidated" class="add-link" @click="addCostoScr"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>Costo</button>
                      </div>
                      <p v-if="!scrCostos.length" class="text-[12px] mb-1" :class="scrValidated ? 'text-ink-muted' : 'text-red-500'">{{ scrValidated ? 'Sin costos adicionales.' : 'Obligatorio -- agrega al menos uno (fletes, maniobras…), aunque sea con importe $0.' }}</p>
                      <div v-for="(c, i) in scrCostos" :key="i" class="flex items-center gap-2 mb-1.5">
                        <input v-model="c.description" placeholder="Descripción" :disabled="scrValidated" class="field-input flex-1" />
                        <div class="w-56 flex-shrink-0" :title="c.factura_flete ? 'Factura del flete ' + c.factura_flete : c.poliza_flete ? 'Póliza ' + c.poliza_flete : 'Proveedor de paquetería al que se le paga el flete'">
                          <LinkInput v-model="c.proveedor_flete" doctype="Supplier" :filters="FILTRO_TRANSPORTISTA" placeholder="Transportista…" :readonly="scrValidated" :error="!scrValidated && c.amount > 0 && !c.proveedor_flete" />
                        </div>
                        <input v-model.number="c.amount" type="number" min="0" step="0.01" placeholder="Importe" :disabled="scrValidated" class="field-input w-32 text-right" />
                        <label class="flex items-center gap-1 text-[11.5px] text-ink-muted whitespace-nowrap" title="Marca si el importe que capturaste ya trae IVA. Al inventario va la base sin IVA; el IVA se acredita en la factura del flete.">
                          <input v-model="c.flete_incluye_iva" type="checkbox" :true-value="1" :false-value="0" :disabled="scrValidated" />IVA incluido
                        </label>
                        <button v-if="!scrValidated" class="del-btn" @click="removeCostoScr(i)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button>
                      </div>
                      <div v-if="scrCostos.length" class="mt-1">
                        <label class="field-label">Distribuir por<AyudaDistribuir /></label>
                        <select v-model="scrForm.distribute_additional_costs_based_on" :disabled="scrValidated" class="field-input w-40"><option value="Qty">Cantidad</option><option value="Amount">Importe</option></select>
                      </div>
                    </div>

                    <div class="flex items-center gap-2 flex-wrap bg-white rounded-xl border border-surface-border p-3 mt-3">
                      <button data-libre class="doc-action" @click="openPdf('Subcontracting Receipt', scr.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>Vista previa</button>
                      <div class="flex-1"></div>
                      <span v-if="scrValidated" class="text-[13px] text-green-700 font-medium flex items-center gap-1.5"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Recibido · producto en inventario</span>
                    </div>
                  </template>
                </div>
              </template>
            </div>

            <!-- Lote sin NINGUNA parada todavía (nunca se corrió "Crear órdenes de
                 subcontrato" para este costeo): tracksLote sale vacío (depende de
                 loteActivo.paradas) y paradaActiva también, así que sin este bloque
                 el botón para generarlas queda inalcanzable -- la sección se veía
                 en blanco debajo de "Flujo de este lote". -->
            <VacioEstado
              v-if="!(loteActivo.paradas || []).length" icono="taller"
              titulo="Este lote todavía no tiene talleres"
              detalle="Se crea una orden por proveedor (corte, costura, bordado…) — las etapas que comparten taller quedan juntas en la misma orden, cada una con su servicio y BOM de subcontratación."
            />
            </div>
            <!-- 4 · Entrega (plan §5.8). La remisión sale con lo que produjo ESTE
                 lote y del almacén donde quedaron las prendas (crear_remision con
                 lote_ref). El botón vive en la barra de abajo. -->
            <div v-else-if="pPasoLote === 'entrega'" class="space-y-3">
              <VacioEstado
                v-if="!loteActivo.entrega || !loteActivo.entrega.producido"
                icono="reloj" titulo="Todavía no hay prendas terminadas"
                :detalle="`${talleresPendientesLote} taller(es) por entregar. La remisión se arma sola con lo que produzca este lote.`"
              />
              <template v-else>
                <!-- Lote cerrado: se dice de una vez, sin que haya que leer la tabla. -->
                <div v-if="!loteActivo.entrega.pendiente && loteActivo.entrega.remisiones.every((r) => r.docstatus === 1)" class="p-panel p-6 flex items-center gap-4">
                  <div class="w-10 h-10 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center text-lg flex-shrink-0">✓</div>
                  <div class="flex-1 min-w-0">
                    <p class="text-[14px] font-semibold">Lote terminado y entregado</p>
                    <p class="p-meta">
                      {{ loteActivo.entrega.producido.toLocaleString('es-MX') }} prendas
                      <template v-if="loteActivo.entrega.remisiones.length">
                        · remisión {{ loteActivo.entrega.remisiones.map((r) => r.name).join(', ') }}
                        {{ loteActivo.entrega.remisiones.every((r) => r.docstatus === 1) ? 'validada' : 'en borrador' }}
                      </template>
                    </p>
                  </div>
                </div>

                <div class="p-panel overflow-x-auto">
                  <table class="p-tbl">
                    <thead>
                      <tr>
                        <th>Producto</th><th>Almacén</th>
                        <th class="text-right">Producido</th><th class="text-right">En remisión</th><th class="text-right">Por entregar</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(d, item) in loteActivo.entrega.productos" :key="item">
                        <td>{{ item }}</td>
                        <td class="text-ink-muted">{{ d.almacen || '—' }}</td>
                        <td class="text-right p-num">{{ (d.producido || 0).toLocaleString('es-MX') }}</td>
                        <td class="text-right p-num text-ink-muted">{{ (d.entregado || 0).toLocaleString('es-MX') }}</td>
                        <td class="text-right p-num font-medium" :class="d.pendiente > 0 ? 'text-ink' : 'text-ink-light'">{{ (d.pendiente || 0).toLocaleString('es-MX') }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <!-- Reparto entre direcciones del cliente: una remisión por destino. El
                     botón que las genera está en la barra de abajo. -->
                <RepartoEntrega
                  v-if="loteActivo.entrega.lista"
                  v-model="repartoEntrega" :costeo="docName" :sales-order="activeSOName || ''"
                  :productos="productosPorEntregar" :direcciones="entregaDir.direcciones"
                  :por-defecto="entregaDir.default || ''" :cliente="entregaDir.customer || ''"
                  @direcciones="(d) => (entregaDir.direcciones = d)"
                />

<!-- Las remisiones de este lote. Antes esto solo llevaba al paso "Enviar";
                     ahora cada una se abre en su panel y ahí mismo se captura y se
                     valida, sin salir del lote. -->
                <template v-if="loteActivo.entrega.remisiones.length">
                  <h2 class="p-eyebrow mt-6 mb-2">Remisiones de este lote</h2>
                  <div class="p-panel">
                    <FilaLista
                      v-for="r in loteActivo.entrega.remisiones" :key="r.name"
                      :titulo="r.name" :estado="r.docstatus === 1 ? 'ok' : 'wait'"
                      :meta="[r.direccion ? `→ ${r.direccion}` : 'sin dirección de envío', r.prendas ? `${Number(r.prendas).toLocaleString('es-MX')} prendas` : '', r.docstatus === 1 ? 'entregada al cliente' : 'revisa flete y valídala'].filter(Boolean).join(' · ')"
                      @abrir="abrirPanelRemision(r.name)"
                    >
                      <template #derecha>
                        <Pill :estado="r.docstatus === 1 ? 'ok' : 'wait'" :texto="r.docstatus === 1 ? 'Validada' : 'Borrador'" ancho="w-24" />
                      </template>
                    </FilaLista>
                  </div>
                </template>
              </template>
            </div>
          </template>
        </template>

        <!-- ═══════════ ENVÍOS (bandeja) ═══════════ -->
        <div v-else-if="pVista === 'envios'" class="space-y-3">
          <!-- Todos los movimientos del lote: entradas, envíos y recibos de taller,
               devoluciones y remisiones. Solo se filtra por lote. -->
          <div class="flex items-center gap-x-4 gap-y-2 flex-wrap">
            <label class="flex items-center gap-2"><span class="p-meta">Lote</span>
              <select data-nav v-model="bandejaLote" class="p-field h-8 py-0 w-auto min-w-[9rem] text-[12.5px]">
                <option v-for="o in filtroLoteOpciones" :key="o.valor" :value="o.valor">{{ o.texto }}</option>
              </select></label>
            <label class="flex items-center gap-2"><span class="p-meta">Tipo</span>
              <select data-nav v-model="bandejaTipo" class="p-field h-8 py-0 w-auto min-w-[11rem] text-[12.5px]">
                <option v-for="o in envTipoOpciones" :key="o.valor" :value="o.valor">{{ o.texto }} ({{ o.conteo }})</option>
              </select></label>
          </div>
          <div v-if="envFilas.length" class="p-panel">
            <FilaLista
              v-for="(f, i) in envFilas" :key="i" :estado="f.estado" :titulo="f.titulo" :meta="f.meta"
              @abrir="f.ir()"
            >
              <template #derecha>
                <span class="w-40 flex-shrink-0 text-right text-[11.5px] text-ink-muted whitespace-nowrap">{{ TIPO_MOV[f.tipo] }}</span>
                <Pill :estado="f.pill.estado" :texto="f.pill.texto" ancho="w-24" />
              </template>
            </FilaLista>
          </div>
          <VacioEstado v-else icono="bandeja" titulo="Sin movimientos con este filtro" detalle="Aquí aparece todo lo que entra y sale: material, envíos y recibos de talleres, devoluciones y remisiones." />

          <!-- Material que quedó en los almacenes de los talleres. Sale del redondeo
               hacia arriba de cada transferencia: se manda un poco de más y el recibo
               consume la cantidad exacta del BOM. Dos salidas legítimas y solo la
               persona sabe cuál pasó -- por eso esto informa y ofrece la devolución,
               pero no decide solo. -->
          <div v-if="talleresSaldo.length" class="p-panel p-4">
            <p class="section-title mb-2">Sobrante en talleres</p>
            <p v-if="prodComplete.complete" class="text-[12px] text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-2">
              La producción ya terminó: pídele a cada taller este sobrante y registra su devolución para que vuelva a tu inventario.
            </p>
            <p v-else class="text-[11.5px] text-ink-light mb-2 leading-relaxed">
              Sobró al redondear las transferencias. Mientras queden prendas por hacer, el taller lo usa en la siguiente transferencia (se descuenta solo); al terminar, registra la devolución para que vuelva a tu inventario.
            </p>
            <div class="space-y-2">
              <div v-for="t in talleresSaldo" :key="t.warehouse" class="rounded-lg ring-1 ring-surface-border px-3 py-2">
                <div class="flex items-center justify-between gap-2 mb-1">
                  <span class="text-[12.5px] font-medium text-ink">{{ t.supplier }}</span>
                  <button type="button" :disabled="advancing" class="text-[11.5px] text-brand-600 hover:text-brand-700 disabled:opacity-50" @click="devolverMaterialTaller(t)">Registrar devolución</button>
                </div>
                <div v-for="m in t.materiales" :key="m.item_code" class="flex items-center justify-between text-[12px] text-ink-muted tabular-nums">
                  <span class="truncate">{{ m.item_name }}</span>
                  <span class="flex-shrink-0">{{ m.libre.toLocaleString('es-MX') }} {{ m.uom }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- La remisión de TODA la orden de venta (sin lote). Las de cada lote se
               crean desde su paso Entrega; esta queda aquí para los pedidos que no se
               parten en lotes y para no perder el camino que tenía el paso "Enviar". -->
          <div v-if="puedeNuevaRemision" class="p-panel p-3 flex items-center justify-between gap-3 flex-wrap">
            <p class="p-meta">¿El pedido no se entrega por lotes? Crea una remisión con todo el saldo pendiente de la orden de venta.</p>
            <button type="button" class="p-btn-secondary h-8 text-[12.5px]" :disabled="advancing" @click="generarRemision">
              Nueva remisión de toda la orden de venta
            </button>
          </div>
        </div>

        <!-- ═══════════ FACTURAS (bandeja) ═══════════ -->
        <div v-else-if="pVista === 'facturas'" class="space-y-3">
          <div class="grid grid-cols-3 gap-px bg-surface-border rounded-xl overflow-hidden border border-surface-border">
            <div class="bg-white p-4"><p class="p-meta">Por facturar</p><p class="text-[20px] font-semibold p-num mt-1">{{ fmtC(facturasTotales.porFacturar) }}</p><p class="p-meta">maquila recibida</p></div>
            <div class="bg-white p-4"><p class="p-meta">En borrador</p><p class="text-[20px] font-semibold p-num mt-1">{{ fmtC(facturasTotales.borrador) }}</p><p class="p-meta">{{ facturasTotales.nBorrador }} documento(s)</p></div>
            <div class="bg-white p-4"><p class="p-meta">Validadas</p><p class="text-[20px] font-semibold p-num mt-1">{{ fmtC(facturasTotales.validadas) }}</p></div>
          </div>
          <div class="flex items-center gap-x-4 gap-y-2 flex-wrap">
            <label class="flex items-center gap-2"><span class="p-meta">Lote</span>
              <select data-nav v-model="bandejaLote" class="p-field h-8 py-0 w-auto min-w-[9rem] text-[12.5px]">
                <option v-for="o in filtroLoteOpciones" :key="o.valor" :value="o.valor">{{ o.texto }}</option>
              </select></label>
            <label class="flex items-center gap-2"><span class="p-meta">Tipo</span>
              <select data-nav v-model="bandejaTipo" class="p-field h-8 py-0 w-auto min-w-[11rem] text-[12.5px]">
                <option v-for="o in facTipoOpciones" :key="o.valor" :value="o.valor">{{ o.texto }} ({{ o.conteo }})</option>
              </select></label>
          </div>
          <div v-if="facturasFilas.length" class="p-panel">
            <FilaLista
              v-for="(f, i) in facturasFilas" :key="i" :estado="f.estado" :titulo="f.titulo" :meta="f.meta"
              @abrir="f.ir()"
            >
              <template #derecha>
                <span class="w-32 flex-shrink-0 text-right text-[11.5px] text-ink-muted whitespace-nowrap">{{ TIPO_FAC[f.tipo] }}</span>
                <span class="p-num text-[13px] w-28 text-right">{{ fmtC(f.importe) }}</span>
                <Pill :estado="f.pill.estado" :texto="f.pill.texto" ancho="w-24" />
              </template>
            </FilaLista>
          </div>
          <VacioEstado v-else icono="factura" titulo="Sin facturas con este filtro" detalle="Aquí aparecen las de material, maquila, fletes y la de venta al cliente." />
        </div>

        <!-- Vista pedida por URL que este usuario no puede abrir (§6.3). -->
        <VacioEstado v-else icono="candado" :titulo="`No tienes acceso a ${sinAcceso.vista}`">
          <template #detalle>
            <template v-if="sinAcceso.rol">Necesitas el rol <b class="text-ink">{{ sinAcceso.rol }}</b>. Pídeselo a quien administra los usuarios.</template>
            <template v-else>Pídele a quien administra los usuarios el rol que te falta.</template>
          </template>
        </VacioEstado>
      </ProduccionLayout>

      <!-- ═══ Panel lateral · Remisión (el paso "Enviar", movido al lote) ═══
           Mismo patrón que el panel del proveedor: el documento se captura aquí y
           las acciones viven en el pie. -->
      <PanelLateral
        :abierto="panelRemision.abierto" :eyebrow="panelRemision.eyebrow"
        :titulo="panelRemision.titulo" :meta="panelRemisionMeta"
        :acciones="accionesPanelRemision" :ocupado="advancing"
        :solo-lectura="dnValidated ? 'Validada: ya no se puede cambiar.' : ''"
        @cerrar="cerrarPanelRemision"
      >
        <template #pill>
          <Pill v-if="dnDoc" :estado="dnValidated ? 'ok' : 'wait'" :texto="dnValidated ? 'Validada' : 'Borrador'" />
        </template>
        <template #enlaces>
          <button data-libre v-if="dnDoc" class="p-btn-ghost h-8 text-[12.5px] px-2" @click="openPdf('Delivery Note', dnDoc.name)">Vista previa</button>
          <button v-if="dnDoc && dnDoc.docstatus === 1" class="p-btn-ghost h-8 text-[12.5px] px-2" @click="openSend('Delivery Note', dnDoc.name, dnDoc.contact_email || activeSO?.contact_email, dnDoc.contact_mobile || activeSO?.contact_mobile)">Enviar</button>
          <button data-libre v-if="dnDoc" class="p-btn-ghost h-8 text-[12.5px] px-2" @click="downloadPdf('Delivery Note', dnDoc.name)">Descargar</button>
          <a v-if="dnDoc" class="p-btn-ghost h-8 text-[12.5px] px-2" :href="`/app/delivery-note/${dnDoc.name}`" target="_blank">ERPNext ↗</a>
        </template>

        <VacioEstado v-if="panelRemision.error" icono="alerta" titulo="No se pudo abrir la remisión" :detalle="panelRemision.error" />
        <p v-else-if="panelRemision.cargando" class="p-meta">Preparando la remisión…</p>
        <template v-else-if="dnDoc">
          <p v-if="dnDoc.lote_ref" class="p-meta mb-3">Cantidades y almacén tomados de lo que produjo el {{ dnDoc.lote_ref }}.</p>

          <div class="grid sm:grid-cols-2 gap-x-3">
            <div>
              <label class="field-label">Dirección de envío <span class="text-ink-light font-normal">(si es distinta a la de facturación)</span></label>
              <select v-model="dnForm.shipping_address_name" class="field-input mb-3" :disabled="dnValidated">
                <option value="">— Misma que facturación —</option>
                <option v-for="a in (dnDoc.address_options || [])" :key="a.value" :value="a.value">{{ a.label }}</option>
              </select>
            </div>
            <div>
              <label class="field-label">Dirección de facturación</label>
              <select v-model="dnForm.customer_address" class="field-input mb-3" :disabled="dnValidated">
                <option value="">— Sin especificar —</option>
                <option v-for="a in (dnDoc.address_options || [])" :key="a.value" :value="a.value">{{ a.label }}</option>
              </select>
            </div>
            <div>
              <label class="field-label">Fecha de entrega</label>
              <input v-model="dnForm.posting_date" type="date" :max="hoyLocal" class="field-input mb-3" :disabled="dnValidated" />
            </div>
            <div>
              <label class="field-label">Proveedor de paquetería <span v-if="Number(dnForm.flete_costo) > 0" class="text-red-400">*</span><span v-else class="text-ink-light font-normal">(si hay costo de envío)</span></label>
              <LinkInput v-model="dnForm.flete_proveedor" doctype="Supplier" :filters="FILTRO_TRANSPORTISTA" placeholder="Paquetería / transportista…" :readonly="dnValidated" :error="!dnValidated && Number(dnForm.flete_costo) > 0 && !dnForm.flete_proveedor" class="mb-3" />
            </div>
            <div class="sm:col-span-2">
              <label class="field-label">Costo de envío</label>
              <div class="flex items-center border border-surface-border rounded-lg focus-within:ring-2 focus-within:ring-brand-500/30 focus-within:border-brand-400 bg-white mb-1">
                <span class="pl-3 pr-1 text-sm text-ink-light select-none">$</span>
                <input v-model.number="dnForm.flete_costo" type="number" min="0" step="0.01" :disabled="dnValidated" class="flex-1 min-w-0 py-2 pr-3 text-sm focus:outline-none bg-transparent disabled:bg-surface-raised/60" />
              </div>
              <label class="flex items-center gap-1.5 text-[12px] text-ink-muted mb-1">
                <input v-model="dnForm.flete_incluye_iva" type="checkbox" :true-value="1" :false-value="0" :disabled="dnValidated" />El importe incluye IVA
              </label>
              <p v-if="!dnValidated" class="p-meta mb-3">Al validar se crea en borrador la factura del proveedor de paquetería (gasto de Transporte y Fletes sin IVA, IVA acreditable y, si aplica, retención de 4%). Ahí se captura el folio y se adjuntan el CFDI y la carta porte.</p>
              <p v-else-if="dnDoc.flete_factura" class="p-meta mb-3">Factura del flete: <a :href="`/app/purchase-invoice/${dnDoc.flete_factura}`" target="_blank" class="text-brand-600 hover:underline">{{ dnDoc.flete_factura }}</a> · se completa en la bandeja de Facturas</p>
              <p v-else-if="dnDoc.flete_journal_entry" class="p-meta mb-3">Póliza: <a :href="`/app/journal-entry/${dnDoc.flete_journal_entry}`" target="_blank" class="text-brand-600 hover:underline">{{ dnDoc.flete_journal_entry }}</a></p>
            </div>
          </div>

          <div class="p-panel overflow-x-auto mb-3">
            <table class="p-tbl">
              <thead>
                <tr>
                  <th>Producto</th><th class="text-right w-24">Cant.</th><th class="w-40">Almacén</th>
                  <th class="text-right w-20">{{ dnValidated ? 'Quedó' : 'Disponible' }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="it in dnDoc.items" :key="it.name">
                  <td>{{ it.item_name || it.item_code }}</td>
                  <td><input v-model.number="it.qty" type="number" min="0" class="field-input text-right w-24" :disabled="dnValidated" /></td>
                  <td>
                    <select v-model="it.warehouse" class="field-input" :disabled="dnValidated">
                      <option value="">— Selecciona —</option>
                      <option v-for="w in (dnDoc.warehouses || [])" :key="w.name" :value="w.name">{{ w.warehouse_name || w.name }}</option>
                    </select>
                  </td>
                  <td class="text-right p-num" :class="!dnValidated && (it.available ?? 0) < it.qty ? 'text-red-600 font-semibold' : 'text-ink-muted'">{{ it.available ?? '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-if="faltaStockRemision && !dnValidated" class="text-[12px] text-red-600 mb-3">
            No hay stock suficiente en el almacén elegido para esa cantidad.
          </p>

          <div class="rounded-xl border border-surface-border overflow-hidden">
            <iframe :key="previewKey" :src="printUrl('Delivery Note', dnDoc.name)" style="width: 200%; height: 520px; transform: scale(0.5); transform-origin: top left; border: 0;" title="Vista previa de la remisión"></iframe>
          </div>
        </template>
      </PanelLateral>

      <!-- ═══ Panel lateral · Proveedor de materia prima del lote (plan §5.5) ═══
           Un solo panel para los tres pasos del proveedor. Dentro van los MISMOS
           PurchaseDocPanel / FacturaCompraPanel de siempre, sin sus botones: las
           acciones viven en el pie. La solicitud de cotización y el presupuesto del
           proveedor, que casi nunca se usan, están en el menú "⋯". -->
      <PanelLateral
        :abierto="panelProv.abierto" :eyebrow="`${loteActivoRef} · Materia prima`"
        :titulo="panelProv.supplier" :meta="panelProvMeta"
        :pasos="pasosPanelProv" :paso-actual="panelProv.tab"
        :acciones="accionesPanelProv" :ocupado="advancing"
        :solo-lectura="panelProvSoloLectura"
        @cerrar="cerrarPanelProveedor" @ir-paso="irPasoProveedor"
      >
        <template #pill><Pill :estado="pillPanelProv.estado" :texto="pillPanelProv.texto" /></template>
        <template #mas>
          <!-- Un solo botón: cotizar es UN proceso de dos pasos (se pide y el
               proveedor contesta), no dos cosas sueltas que haya que recordar. -->
          <button data-nav class="p-rail-item" @click="abrirDocProveedor('rfq')">Solicitar cotización al proveedor</button>
        </template>
        <template #enlaces>
          <button data-libre v-if="docPanelProv" class="p-btn-ghost h-8 text-[12.5px] px-2" @click="openPdf(docPanelProv.doctype, docPanelProv.name)">Vista previa</button>
          <a v-if="docPanelProv" class="p-btn-ghost h-8 text-[12.5px] px-2" :href="`/app/${deskDelPaso}/${docPanelProv.name}`" target="_blank">ERPNext ↗</a>
        </template>

        <!-- Mientras carga, y si algo falló: estados propios, para no dejar nunca un
             "Preparando el documento…" eterno ni el documento del paso anterior. -->
        <VacioEstado v-if="panelProv.error" icono="alerta" titulo="No se pudo abrir el documento" :detalle="panelProv.error" />
        <p v-else-if="panelProv.cargando" class="p-meta">Preparando el documento…</p>

        <!-- Orden de compra (y, desde "⋯", solicitud de cotización / presupuesto) -->
        <div v-else-if="!['recibo', 'factura'].includes(panelProv.tab)">
          <FranjaAprobacion
            v-if="docCompra && docCompra.doctype === 'Purchase Order' && Number(docCompra.docstatus) === 0"
            class="mb-4" doctype="Purchase Order" :name="docCompra.name" :guardar="guardarDocCompra"
            @estado="(s) => (aprobPanel[docCompra.name] = s)" @cambio="trasAprobacionDocCompra"
          />
          <PurchaseDocPanel
            v-if="docCompra" sin-acciones
            :doc="docCompra" :items="docCompraItems" :form="docCompraForm"
            :desk-route="DOC_COMPRA[panelProv.tab].desk"
            :payment-terms-options="cotDefaults.payment_terms_templates" :terms-options="cotDefaults.terms"
            :editable-uom="docCompra.doctype === 'Purchase Order'"
            :editable-supplier="docCompra.doctype === 'Purchase Order'"
            :editable-qty="docCompra.doctype !== 'Purchase Order'"
            :help-text="panelProv.tab === 'oc' ? 'Proveedor, precio y UDM se ajustan aquí. Por defecto trae el precio del costeo (si la UDM sigue igual) o el del presupuesto del proveedor. La cantidad respeta la solicitud de material.' : ''"
            :advancing="advancing"
            :requires-review="docCompra.requiere_doble_validacion" :reviewed="docCompra.revisado_yelke"
            :reviewed-by="docCompra.revisado_por_yelke" :reviewed-at="docCompra.revisado_en_yelke"
            :puede-revisar="permisosValidacion.puede_revisar" :puede-aprobar="permisosValidacion.puede_aprobar"
          />
          <VacioEstado
            v-else icono="documento" :titulo="VACIO_PASO[panelProv.tab]?.titulo || 'Todavía no hay documento'"
            :detalle="VACIO_PASO[panelProv.tab]?.detalle || 'Créalo con el botón de abajo.'"
          />
        </div>

        <!-- Recibo de compra -->
        <div v-else-if="panelProv.tab === 'recibo'">
          <!-- El proveedor puede entregar por partes: un recibo por entrega. La tira
               dice cuántos van, cuál se está viendo y cuánto falta (ver
               estado_recibos_oc en el backend). -->
          <TiraRecibos
            v-if="grpPanelProv?.po?.receipts?.length"
            :recibos="grpPanelProv.po.receipts" :activo="reciboPr?.name"
            :completo="grpPanelProv.po.recibido_completo" :pendiente="grpPanelProv.po.pendiente_recibir"
            @abrir="(n) => loadRecibo(n)"
          />
          <PurchaseDocPanel
            v-if="reciboPr" sin-acciones
            :doc="reciboPr" :items="reciboItems" :form="reciboForm"
            desk-route="purchase-receipt" show-warehouse :show-send="false"
            help-text="IVA aplicado · al validar entra a inventario y contabilidad."
            validate-label="Validar recibo" validated-text="Validado (en inventario)"
            :advancing="advancing" shipping-required
          />
          <VacioEstado
            v-else icono="bandeja" titulo="Todavía no hay recibo de compra"
            detalle="Se crea con lo que pide la orden; después confirmas cuánto llegó de verdad."
          />
        </div>

        <!-- Factura del proveedor -->
        <!-- Con documento Y bloqueo: se ve, pero el pie no trae acciones. -->
        <p v-if="panelFactura.bloqueo && pinvDoc" class="rounded-lg bg-amber-50 ring-1 ring-amber-200 px-3 py-2 text-[12.5px] text-amber-900 mb-3">
          ⏳ {{ panelFactura.bloqueo }}
        </p>
        <FranjaAprobacion
          v-if="pinvDoc && !pinvValidated" class="mb-4" doctype="Purchase Invoice" :name="pinvDoc.name"
          :guardar="guardarPinv" @estado="(s) => (aprobPanel[pinvDoc.name] = s)" @cambio="trasAprobacionPinv"
        />
        <FacturaCompraPanel
          v-if="!panelFactura.error && !panelFactura.cargando && !(panelFactura.bloqueo && !pinvDoc)" sin-acciones
          :doc="pinvDoc" :form="pinvForm" :validated="pinvValidated" :proveedor="panelProv.supplier"
          :advancing="advancing" :payment-terms-options="cotDefaults.payment_terms_templates"
          :preview-url="pinvDoc ? printUrl('Purchase Invoice', pinvDoc.name) : ''" :preview-key="previewKey"
        />
        <ActividadPlegable data-libre v-if="docPanelProv && !panelProv.cargando" :doctype="docPanelProv.doctype" :name="docPanelProv.name" />
      </PanelLateral>

      <!-- ═══ Panel lateral · Orden a un taller (Preparación · paso 3) ═══
           Dentro va el MISMO PurchaseDocPanel de siempre, sin sus botones
           (`sin-acciones`): las acciones viven en el pie del panel. Debajo, la
           ficha de manufactura tal como la recibe ese taller. -->
      <PanelLateral
        :abierto="panelOcTaller.abierto" eyebrow="Orden a taller"
        :titulo="panelOcTaller.titulo" :meta="panelOcTaller.meta"
        :acciones="accionesOcTaller" :ocupado="advancing"
        @cerrar="panelOcTaller.abierto = false"
      >
        <template #pill>
          <Pill :estado="subValidated ? 'ok' : 'wait'" :texto="subValidated ? (subPo?.enviado_el ? 'Enviada' : 'Validada') : 'Borrador'" />
        </template>
        <template #enlaces>
          <!-- Dos PDF distintos del MISMO documento: la orden de compra a ese taller
               (reagrupada por servicio y precio por prenda) y su ficha de manufactura.
               Se descargan por separado porque no siempre se mandan juntas: si cambia
               la ficha se reenvía sola, sin volver a mandar la orden. -->
          <button data-libre v-if="subPo" class="p-btn-ghost h-8 text-[12.5px] px-2" title="PDF de la orden de compra a este taller"
                  @click="downloadPdfFmt('Purchase Order', subPo.name, 'Orden de Maquila')">Orden ⤓</button>
          <button v-if="subPo" class="p-btn-ghost h-8 text-[12.5px] px-2" title="PDF de la ficha de manufactura de este taller, con sus PDF anexos unidos al final"
                  @click="descargarFicha(subPo.name)">Ficha ⤓</button>
          <button data-libre v-if="subPo" class="p-btn-ghost h-8 text-[12.5px] px-2" @click="panelOcTaller.abierto = false; openPdf('Purchase Order', subPo.name)">Vista previa</button>
          <a v-if="subPo" class="p-btn-ghost h-8 text-[12.5px] px-2" :href="`/app/purchase-order/${subPo.name}`" target="_blank">ERPNext ↗</a>
        </template>
        <VacioEstado v-if="panelOcTaller.error" icono="alerta" titulo="No se pudo abrir la orden" :detalle="panelOcTaller.error" />
        <p v-else-if="panelOcTaller.cargando || !subPo" class="p-meta">Cargando la orden…</p>
        <template v-else>
          <FranjaAprobacion
            v-if="!subValidated" class="mb-4" doctype="Purchase Order" :name="subPo.name" :guardar="guardarSub"
            @estado="(s) => (aprobPanel[subPo.name] = s)" @cambio="trasAprobacionSub"
          />
          <!-- Datos fiscales del taller: sin alta en el SAT no emite factura, así que la
               orden (y su factura interna) van sin IVA. Es dato del proveedor: vale para
               todas sus órdenes nuevas (costeo_api.marcar_proveedor_sin_alta_sat). -->
          <div class="rounded-xl border border-surface-border px-4 py-3 mb-4">
            <p class="p-eyebrow mb-2">Datos fiscales del taller</p>
            <label class="flex items-start gap-2.5" :class="subValidated ? 'opacity-70' : 'cursor-pointer'">
              <input type="checkbox" class="mt-0.5 accent-brand-500" :checked="!!subPo.sin_alta_sat" :disabled="subValidated || advancing" @change="cambiarAltaSat($event.target.checked)" />
              <span>
                <span class="block text-[13px] font-medium text-ink">Sin alta en el SAT</span>
                <span class="block text-[11.5px] text-ink-muted">No emite factura: la orden va sin IVA y el pago se respalda con un recibo interno.</span>
              </span>
            </label>
          </div>
          <EntregasTaller :po="subPo.name" />
          <PurchaseDocPanel
            sin-acciones con-importes
            :doc="subPo" :items="subItems" :form="subForm" desk-route="purchase-order"
            :payment-terms-options="cotDefaults.payment_terms_templates" :terms-options="cotDefaults.terms"
            :advancing="advancing"
            :requires-review="subPo.requiere_doble_validacion" :reviewed="subPo.revisado_yelke"
            :reviewed-by="subPo.revisado_por_yelke" :reviewed-at="subPo.revisado_en_yelke"
            :puede-revisar="permisosValidacion.puede_revisar" :puede-aprobar="permisosValidacion.puede_aprobar"
            @save="guardarSub" @validate="validarSub" @review="revisarSub"
          />
          <!-- La ficha del taller: o la general heredada (solo lectura, se arma al
               vuelo con om_de_oc), o -- si este costeo no tiene ficha general -- el
               formulario viejo, que SÍ se captura dentro de la propia orden.
               Las dos ramas van en <template> para que la condición sea una sola:
               con un v-if suelto en medio, el v-else se encadenaba a ESE y salían
               las dos fichas a la vez. -->
          <OmTallerView v-if="omDeOc.some((r) => r.origen === 'general')" class="mt-3" :registros="omDeOc" />
          <template v-else>
          <p class="p-meta mt-3">Hay una sola ficha técnica por proyecto: lo que captures aquí se copia solo a las demás etapas.</p>
          <OrdenManufacturaForm
            class="mt-3"
            :general="omGeneral" :om-cab="omCab" :om-dama="omDama" :om-proc="omProc" :om-tablas="omTablas" :om-archivos="omArchivos"
            :uploading="omUploading" :disabled="!omEditable" :OM_CAB="OM_CAB" :OM_DAMA="OM_DAMA" :talla-total="tallaTotal"
            :medidas-templates="medidasTemplates"
            @add-proceso="addProceso" @remove-proceso="removeProceso" @add-tabla="addTabla" @add-tabla-plantilla="addTablaPlantilla" @remove-tabla="removeTabla"
            @add-columna="addColumna" @remove-columna="removeColumna" @add-fila="addFila" @remove-fila="removeFila"
            @file="onOmFile" @remove-archivo="removeArchivo"
          />
          </template>
          <ActividadPlegable data-libre doctype="Purchase Order" :name="subPo.name" />
        </template>
      </PanelLateral>

      <!-- ═══ Panel lateral · Ficha de manufactura como la recibe un taller ═══ -->
      <PanelLateral
        :abierto="panelOmTaller.abierto" eyebrow="Orden de manufactura"
        :titulo="panelOmTaller.titulo" meta="Así se imprime en su orden de maquila"
        :acciones="accionesOmTaller" :ocupado="advancing"
        @cerrar="panelOmTaller.abierto = false"
      >
        <OmTallerView v-if="omDeOc.some((r) => r.origen === 'general')" :registros="omDeOc" />
        <OrdenManufacturaForm v-else
          :general="omGeneral" :om-cab="omCab" :om-dama="omDama" :om-proc="omProc" :om-tablas="omTablas" :om-archivos="omArchivos"
          :uploading="omUploading" :disabled="!omEditable" :OM_CAB="OM_CAB" :OM_DAMA="OM_DAMA" :talla-total="tallaTotal"
          :medidas-templates="medidasTemplates"
          @add-proceso="addProceso" @remove-proceso="removeProceso" @add-tabla="addTabla" @add-tabla-plantilla="addTablaPlantilla" @remove-tabla="removeTabla"
          @add-columna="addColumna" @remove-columna="removeColumna" @add-fila="addFila" @remove-fila="removeFila"
          @file="onOmFile" @remove-archivo="removeArchivo"
        />
      </PanelLateral>

      <!-- ═══ Panel lateral · Factura de compra (bandeja de Facturas) ═══ -->
      <PanelLateral
        :abierto="panelFactura.abierto" :eyebrow="panelFactura.eyebrow" :titulo="panelFactura.titulo"
        :meta="panelFactura.meta" :acciones="accionesPanelFactura" :ocupado="advancing"
        :solo-lectura="puedeEditar('facturas') ? '' : 'La captura la hace Facturas'"
        @cerrar="cerrarPanelFactura"
      >
        <template #enlaces>
          <button data-libre v-if="pinvDoc" class="p-btn-ghost h-8 text-[12.5px] px-2" @click="downloadPdf('Purchase Invoice', pinvDoc.name)">Descargar</button>
          <button data-libre v-if="pinvDoc" class="p-btn-ghost h-8 text-[12.5px] px-2" @click="panelFactura.abierto = false; openPdf('Purchase Invoice', pinvDoc.name)">Vista previa</button>
          <button data-libre v-if="pinvDoc" class="p-btn-ghost h-8 text-[12.5px] px-2" @click="printDocView('Purchase Invoice', pinvDoc.name)">Imprimir</button>
          <a v-if="pinvDoc" class="p-btn-ghost h-8 text-[12.5px] px-2" :href="`/app/purchase-invoice/${pinvDoc.name}`" target="_blank">ERPNext ↗</a>
        </template>
        <VacioEstado v-if="panelFactura.error" icono="alerta" titulo="No se pudo abrir la factura" :detalle="panelFactura.error" />
        <p v-else-if="panelFactura.cargando" class="p-meta">Preparando la factura…</p>
        <VacioEstado
          v-else-if="panelFactura.bloqueo && !pinvDoc" icono="reloj"
          titulo="Todavía no se factura este taller" :detalle="panelFactura.bloqueo"
        />
        <!-- Con documento Y bloqueo: se ve, pero el pie no trae acciones. -->
        <p v-if="panelFactura.bloqueo && pinvDoc" class="rounded-lg bg-amber-50 ring-1 ring-amber-200 px-3 py-2 text-[12.5px] text-amber-900 mb-3">
          ⏳ {{ panelFactura.bloqueo }}
        </p>
        <FranjaAprobacion
          v-if="pinvDoc && !pinvValidated && !panelFactura.cargando" class="mb-4" doctype="Purchase Invoice" :name="pinvDoc.name"
          :guardar="guardarPinv" @estado="(s) => (aprobPanel[pinvDoc.name] = s)" @cambio="trasAprobacionPinv"
        />
        <FacturaCompraPanel
          v-if="!panelFactura.error && !panelFactura.cargando && !(panelFactura.bloqueo && !pinvDoc)" sin-acciones
          :doc="pinvDoc" :form="pinvForm" :validated="pinvValidated" :proveedor="panelFactura.titulo"
          :pendiente="panelFactura.pendiente" :habilitado="true"
          :advancing="advancing" :payment-terms-options="cotDefaults.payment_terms_templates"
          :preview-url="pinvDoc ? printUrl('Purchase Invoice', pinvDoc.name) : ''" :preview-key="previewKey"
          @crear="crearFacturaInline" @guardar="guardarPinv" @validar="validarFacturaInline"
          @descargar="downloadPdf('Purchase Invoice', pinvDoc.name)" @imprimir="printDocView('Purchase Invoice', pinvDoc.name)"
          @ampliar="openPdf('Purchase Invoice', pinvDoc.name)"
        />
        <ActividadPlegable data-libre v-if="pinvDoc && !panelFactura.cargando" doctype="Purchase Invoice" :name="pinvDoc.name" />
      </PanelLateral>

      <!-- ═══ Panel lateral · Nuevo lote (antes G9-d, dentro de la pantalla) ═══ -->
      <PanelLateral
        :abierto="nuevoLoteForm.open" eyebrow="Producción" titulo="Nuevo lote"
        :meta="`Se abre como ${siguienteLoteRef()}`"
        :acciones="accionesNuevoLote" :ocupado="advancing"
        @cerrar="cerrarNuevoLote"
      >
        <div v-if="nuevoLoteForm.loading" class="text-[13px] text-ink-muted py-6 text-center">Preparando el lote…</div>
        <div v-else class="space-y-4">
          <p class="p-lede">Cuánto de cada producto entra en este lote (0 = no entra). La materia prima se envía después, taller por taller.</p>
          <div class="p-panel">
            <div v-for="pr in nuevoLoteForm.porProducto" :key="pr.finished_item" class="p-row static">
              <span class="flex-1 text-[13px] min-w-0 truncate">{{ pr.item_name }}</span>
              <input v-model.number="pr.qty" type="number" min="0" class="p-field w-28 text-right" :disabled="pr.po_docstatus !== 1">
              <span class="p-meta w-32 text-right">
                {{ pr.po_docstatus === 1 ? `pendiente ${Number(pr.saldo || 0).toLocaleString("es-MX")}` : "Valida antes la 1ª OC de este producto" }}
              </span>
            </div>
          </div>
          <div><label class="p-field-label">Fecha requerida</label><input v-model="nuevoLoteForm.schedule_date" type="date" class="p-field w-48"></div>
          <p v-if="nuevoLoteForm.porProducto.some((x) => x.limitadoPorStock)" class="p-note">Alguna cantidad sugerida está limitada por la materia prima en stock — puedes ajustarla a mano.</p>
        </div>
      </PanelLateral>
    </div>
    <!-- ══════════ STEP 6 · ENVIAR (Remisión) ══════════ -->
    <!-- El paso 6 ("Enviar") ya no tiene pantalla propia: la remisión se arma y se
         valida en el paso Entrega de cada lote (panel lateral) y se sigue en la
         bandeja de Envíos. `?step=6` cae en Producción. -->

    <!-- ══════════ STEP 7 · FACTURAR ══════════ -->
    <div v-else-if="activeStep === 7" class="p-5 pb-20" v-solo-lectura="soloLecturaPaso">
      <!-- Solo lectura: el usuario tiene esta etapa en "ver" (accesos por vista). -->
      <p v-if="soloLecturaPaso" class="max-w-5xl mx-auto mb-4 text-[12.5px] text-ink-muted bg-surface-raised rounded-lg px-3 py-2">
        <b class="text-ink">Solo lectura.</b> Puedes consultar esta etapa; la captura la hace quien la tiene asignada.
      </p>
      <!-- Solo la factura de VENTA: las de compra viven como último paso de cada flujo (Producción). -->
      <div class="max-w-6xl mx-auto mb-4">
        <ActiveSOSelector data-libre :sales-orders="soVivas" :active-name="activeSOName" @update:active-name="setActiveSO" class="mb-3" />
        <div class="flex items-center gap-1.5 bg-green-50 text-green-700 text-[12px] font-medium px-3 py-2 rounded-lg mb-3 w-max"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>{{ related.delivery_notes.length > 1 ? `${related.delivery_notes.length} remisiones validadas` : `Remisión ${related.delivery_notes[0]?.name} validada` }} · mercancía entregada</div>
      </div>

      <!-- ── VENTA ── -->
      <div class="flex gap-5 items-start max-w-6xl mx-auto">

        <!-- Izquierda: datos de la factura -->
        <div class="w-80 flex-shrink-0 bg-white rounded-xl border border-surface-border p-5" :id="related.sales_invoice ? `doc-hl-${related.sales_invoice.name}` : null" :class="{ 'doc-highlight-flash': related.sales_invoice && highlightTarget === related.sales_invoice.name }">
          <div class="flex items-center justify-between mb-1">
            <p class="text-sm font-semibold text-ink">Factura de venta</p>
            <span v-if="related.sales_invoice" class="text-[11px] font-semibold px-2 py-0.5 rounded-full" :class="siValidated ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'">{{ siValidated ? 'Validada' : 'Borrador' }}</span>
          </div>
          <p class="text-[12px] text-ink-muted mb-4">Se genera desde la orden de venta. Productos y totales son automáticos.</p>

          <label class="field-label">Fecha de factura</label>
          <input v-model="siForm.posting_date" type="date" class="field-input mb-3" :disabled="siValidated" />

          <label class="field-label">Condiciones de pago</label>
          <select v-model="siForm.payment_terms_template" class="field-input mb-3" :disabled="siValidated">
            <option value="">— Sin plantilla —</option>
            <option v-for="p in cotDefaults.payment_terms_templates" :key="p.name" :value="p.name">{{ p.name }}</option>
          </select>

          <!-- Con condición de pago el vencimiento sale de ella (y de la fecha de
               factura); a mano solo sin plantilla. -->
          <label class="field-label">Vencimiento</label>
          <input v-model="siForm.due_date" type="date" class="field-input" :class="siForm.payment_terms_template ? 'mb-1' : 'mb-3'" :disabled="siValidated || !!siForm.payment_terms_template" />
          <p v-if="siForm.payment_terms_template && !siValidated" class="text-[11px] text-ink-light mb-3">Según las condiciones de pago y la fecha de factura.</p>

          <label class="field-label">Términos y condiciones</label>
          <select v-model="siForm.tc_name" class="field-input mb-4" :disabled="siValidated">
            <option value="">— Sin términos —</option>
            <option v-for="t in terminosPara(cotDefaults.terms, 'venta', form.cliente, siForm.tc_name)" :key="t.name" :value="t.name">{{ t.name }}</option>
          </select>

          <div class="border-t border-surface-border pt-3 mb-4 space-y-1">
            <div class="flex justify-between text-[13px]"><span class="text-ink-muted">Productos</span><span>{{ productos.length }}</span></div>
            <div class="flex justify-between text-[13px]"><span class="text-ink-muted">Total factura</span><span class="font-medium">{{ related.sales_invoice ? fmtC(related.sales_invoice.grand_total) : fmtC(totalVenta) }}</span></div>
          </div>

          <div v-if="!related.sales_invoice">
            <button :disabled="advancing || !soValidated" class="w-full h-9 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-40 flex items-center justify-center gap-2" @click="generarFactura">
              <svg v-if="advancing" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
              Generar factura de venta
            </button>
            <p v-if="!soValidated" class="text-[11px] text-ink-light mt-2 text-center">Primero valida la orden de venta.</p>
          </div>

          <div v-else class="space-y-2">
            <!-- La factura timbrada en el otro sistema: PDF obligatorio, XML opcional. -->
            <FacturaArchivos
              v-if="related.sales_invoice.archivos_factura" class="mb-2"
              doctype="Sales Invoice" :docname="related.sales_invoice.name" apilado
              v-model:pdf="related.sales_invoice.factura_pdf" v-model:xml="related.sales_invoice.factura_xml"
              :solo-lectura="siValidated"
            />
            <template v-if="!siValidated">
              <button :disabled="advancing" class="w-full h-9 text-sm font-medium text-ink border border-surface-border rounded-lg hover:bg-surface-raised disabled:opacity-50" @click="guardarFactura">Guardar cambios</button>
              <button :disabled="advancing" class="w-full h-9 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center justify-center gap-1.5" @click="validarFactura">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Validar factura
              </button>
            </template>
            <div class="grid grid-cols-2 gap-2 pt-1">
              <button v-if="siValidated" class="doc-action justify-center" @click="openSend('Sales Invoice', related.sales_invoice.name, related.sales_invoice.contact_email, related.sales_invoice.contact_mobile)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>Enviar</button>
              <button data-libre class="doc-action justify-center" @click="downloadPdf('Sales Invoice', related.sales_invoice.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/></svg>Descargar</button>
              <button data-libre class="doc-action justify-center" @click="printDocView('Sales Invoice', related.sales_invoice.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2z"/></svg>Imprimir</button>
              <button class="doc-action justify-center" @click="openAssign('Sales Invoice', related.sales_invoice.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>Asignar</button>
            </div>
            <a class="doc-action justify-center w-full" :href="`/app/sales-invoice/${related.sales_invoice.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>Abrir en ERPNext</a>

            <div class="pt-3 mt-2 border-t border-surface-border">
              <AttachmentsPanel doctype="Sales Invoice" :docname="related.sales_invoice.name" />
            </div>
          </div>
        </div>

        <!-- Derecha: vista previa del PDF -->
        <div class="flex-1 min-w-0 bg-white rounded-xl border border-surface-border overflow-hidden">
          <div v-if="!related.sales_invoice" class="flex flex-col items-center justify-center gap-2 text-ink-light" style="height: 78vh;">
            <svg class="w-10 h-10 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 14l2 2 4-4m4 9V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2z"/></svg>
            <p class="text-[13px]">La vista previa aparecerá al generar la factura</p>
          </div>
          <div v-else>
            <div class="flex items-center justify-end px-2 py-1.5 border-b border-surface-border">
              <button data-libre class="doc-action" @click="openPdf('Sales Invoice', related.sales_invoice.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 8V4m0 0h4M4 4l5 5m11-5h-4m4 0v4m0-4l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5h-4m4 0v-4m0 4l-5-5"/></svg>Ampliar</button>
            </div>
            <div style="height: 78vh; overflow: auto;">
              <iframe :key="previewKey" :src="printUrl('Sales Invoice', related.sales_invoice.name)" style="width: 143%; height: 143%; transform: scale(0.7); transform-origin: top left; border: 0;" title="Vista previa de la factura de venta"></iframe>
            </div>
          </div>
        </div>
      </div>

    </div>

    <div v-else-if="activeStep === 8" class="p-5 pb-20">
      <div class="max-w-5xl mx-auto mb-4">
        <ActiveSOSelector data-libre :sales-orders="soVivas" :active-name="activeSOName" @update:active-name="setActiveSO" />
      </div>
      <ReporteFinalPanel :r="reporte" :loading="reporteLoading" :costeo="docName" :sales-order="activeSOName || ''" />
    </div>

    <!-- Precio acordado modal -->
    <div v-if="showAcordadoModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="showAcordadoModal = false">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm p-5">
        <p class="text-sm font-semibold text-ink mb-2">Fijar Precio</p>
        <p class="text-[12px] text-ink-muted mb-4">
          Fija el precio de {{ productos.filter(p => p.finished_item).length }} artículo(s) de este costeo como precio
          acordado para {{ form.cliente }}. Mientras esté vigente, podrás generar réplicas de la Orden de Venta con este
          precio directamente, sin volver a cotizar.
        </p>
        <label class="field-label">Vigente hasta</label>
        <input v-model="acordadoValidUpto" type="date" class="field-input mb-4" />
        <div class="flex justify-end gap-2">
          <button class="px-3 py-1.5 text-[13px] text-ink-muted hover:bg-surface-raised rounded-lg" @click="showAcordadoModal = false">Cancelar</button>
          <button :disabled="advancing" class="px-4 py-1.5 text-[13px] font-medium text-white bg-brand-500 hover:bg-brand-600 disabled:opacity-50 rounded-lg" @click="guardarPrecioAcordado">
            {{ advancing ? "Guardando…" : "Guardar" }}
          </button>
        </div>
      </div>
    </div>

    <HistorialModal :open="showHistorialModal" :costeo="docName" @close="showHistorialModal = false" />

    <!-- Editar costeo (lo regresa a borrador, ver costeo_api.reabrir_costeo) -->
    <div v-if="showRevisionModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="showRevisionModal = false">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm p-5">
        <p class="text-sm font-semibold text-ink mb-2">Editar costeo</p>
        <p class="text-[12.5px] text-ink-muted mb-4">{{ docName }} vuelve a borrador para corregirlo. La cotización rechazada se queda en el historial de este mismo costeo. Al terminar, valídalo de nuevo y crea la nueva cotización.</p>
        <label class="field-label">Qué se va a corregir (opcional)</label>
        <textarea v-model="revisionMotivo" rows="3" class="field-input mb-4" placeholder="Ej: cliente pidió ajustar el precio…"></textarea>
        <div class="flex justify-end gap-2">
          <button class="px-3 py-1.5 text-[13px] text-ink-muted hover:bg-surface-raised rounded-lg" @click="showRevisionModal = false">Cancelar</button>
          <button :disabled="revisionCreating" class="px-4 py-1.5 text-[13px] font-medium text-white bg-brand-500 hover:bg-brand-600 disabled:opacity-50 rounded-lg" @click="confirmarRevision">
            {{ revisionCreating ? "Abriendo…" : "Editar costeo" }}
          </button>
        </div>
      </div>
    </div>

    <!-- Rechazar cotización modal -->
    <div v-if="cancelarOV.name" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="cancelarOV.name = ''">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm p-5">
        <p class="text-sm font-semibold text-ink mb-1">Cancelar {{ cancelarOV.name }}</p>
        <p class="text-[12px] text-ink-muted mb-3">La orden se queda en el costeo como historial.</p>
        <label class="field-label">Motivo <span class="text-red-500">*</span></label>
        <textarea v-model="cancelarOV.motivo" rows="3" class="field-input mb-4" placeholder="Ej: el cliente canceló el pedido…"></textarea>
        <div class="flex justify-end gap-2">
          <button class="px-3 py-1.5 text-[13px] text-ink-muted hover:bg-surface-raised rounded-lg" @click="cancelarOV.name = ''">Volver</button>
          <button :disabled="advancing || cancelarOV.motivo.trim().length < 5" class="px-4 py-1.5 text-[13px] font-medium text-white bg-red-500 hover:bg-red-600 disabled:opacity-50 rounded-lg" @click="confirmarCancelarOV">
            {{ advancing ? "Cancelando…" : "Cancelar orden" }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showRechazarModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="showRechazarModal = false">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm p-5">
        <p class="text-sm font-semibold text-ink mb-2">Marcar como rechazada</p>
        <label class="field-label">Motivo (opcional, queda guardado en el historial)</label>
        <textarea v-model="rechazarMotivo" rows="3" class="field-input mb-4" placeholder="Ej: precio alto, tiempo de entrega…"></textarea>
        <div class="flex justify-end gap-2">
          <button class="px-3 py-1.5 text-[13px] text-ink-muted hover:bg-surface-raised rounded-lg" @click="showRechazarModal = false">Cancelar</button>
          <button :disabled="advancing" class="px-4 py-1.5 text-[13px] font-medium text-white bg-red-500 hover:bg-red-600 disabled:opacity-50 rounded-lg" @click="confirmarCotizacionRechazada">
            {{ advancing ? "Guardando…" : "Marcar rechazada" }}
          </button>
        </div>
      </div>
    </div>

    <DocumentActionModals
      :send-chooser="sendChooser"
      :wa-modal="waModal"
      :send-modal="sendModal"
      :assign-modal="assignModal"
      :pdf-modal="pdfModal"
      :users="cotDefaults.users"
      :preview-key="previewKey"
      :print-url="printUrl"
      :on-choose-email="chooseEmail"
      :on-choose-whatsapp="chooseWhatsApp"
      :on-send-whatsapp="sendWhatsAppGeneric"
      :on-send="doSend"
      :on-assign="doAssign"
      :on-print="printDocView"
    />

    <Transition name="fade">
      <!-- z-[60]: por encima del panel lateral (z-50). Al teletransportarse al final
           del body, el panel ganaba con el mismo z-index y tapaba el aviso -- y lo
           tapaba justo en la esquina donde sale, así que cada error que ocurría con
           un panel abierto (validar un recibo, una transferencia…) se perdía y
           parecía que el botón "no hacía nada". -->
      <div v-if="toast.show" class="fixed bottom-5 left-5 z-[60] px-4 py-3 rounded-lg text-sm font-medium shadow-lg max-w-[min(92vw,30rem)]" :class="toast.type === 'error' ? 'bg-red-600 text-white' : 'bg-green-600 text-white'">{{ toast.msg }}</div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick, provide } from "vue";
import { useRoute, useRouter } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import CosteoStepper from "@/components/CosteoStepper.vue";
import LinkInput from "@/components/LinkInput.vue";
import EncargoResumen from "@/components/EncargoResumen.vue";
import ProduccionLayout from "@/components/produccion/ProduccionLayout.vue";
import PanelLateral from "@/components/produccion/PanelLateral.vue";
import FilaLista from "@/components/produccion/FilaLista.vue";
import Pasos from "@/components/produccion/Pasos.vue";
import Pill from "@/components/produccion/Pill.vue";
import EstadoPunto from "@/components/produccion/EstadoPunto.vue";
import Segmentado from "@/components/produccion/Segmentado.vue";
import VacioEstado from "@/components/produccion/VacioEstado.vue";
import { useProduccionRuta } from "@/composables/useProduccionRuta.js";
import FacturaCompraPanel from "@/components/FacturaCompraPanel.vue";
import FacturaArchivos from "@/components/FacturaArchivos.vue";
import ConfirmDialog from "@/components/ConfirmDialog.vue";
import MaterializeProductModal from "@/components/MaterializeProductModal.vue";
import HistorialModal from "@/components/HistorialModal.vue";
import AttachmentsPanel from "@/components/AttachmentsPanel.vue";
import MaterializeArticuloModal from "@/components/MaterializeArticuloModal.vue";
import DocumentActionModals from "@/components/DocumentActionModals.vue";
import DocStatusPill from "@/components/DocStatusPill.vue";
import ProductionProgressBar from "@/components/ProductionProgressBar.vue";
import PurchaseDocPanel from "@/components/PurchaseDocPanel.vue";
import ReporteFinalPanel from "@/components/ReporteFinalPanel.vue";
import OcClienteAdjunto from "@/components/OcClienteAdjunto.vue";
import TiraRecibos from "@/components/TiraRecibos.vue";
import OrdenManufacturaForm from "@/components/OrdenManufacturaForm.vue";
import OmGeneralEditor from "@/components/OmGeneralEditor.vue";
import OmTallerView from "@/components/OmTallerView.vue";
import EntregasTaller from "@/components/EntregasTaller.vue";
import InfoOrdenTaller from "@/components/produccion/InfoOrdenTaller.vue";
import TituloDocumento from "@/components/produccion/TituloDocumento.vue";
import RepartoEntrega from "@/components/produccion/RepartoEntrega.vue";
import AyudaDistribuir from "@/components/produccion/AyudaDistribuir.vue";
import ActiveSOSelector from "@/components/ActiveSOSelector.vue";
import DialogoPrecio from "@/components/DialogoPrecio.vue";
import Icono from "@/components/Icono.vue";
import DialogoImagen from "@/components/DialogoImagen.vue";
import FranjaAprobacion from "@/components/aprobacion/FranjaAprobacion.vue";
import BotonActividad from "@/components/aprobacion/BotonActividad.vue";
import FranjaEncargos from "@/components/encargos/FranjaEncargos.vue";
import PanelEncargos from "@/components/encargos/PanelEncargos.vue";
import { getDelProyecto, version as versionEncargos } from "@/composables/useEncargos.js";
import ActividadPlegable from "@/components/aprobacion/ActividadPlegable.vue";
import { puedeValidarDirecto, usePermisosAprobacion } from "@/composables/useAprobacion.js";
import { fecha as fmtFecha } from "@/utils/formato.js";
import { useAccesos } from "@/composables/useAccesos.js";
import { db, call, openDesk as deskOpen, uploadFile, searchLink, fuzzyQuery, getLinkDisplayLabel, FILTRO_TRANSPORTISTA } from "@/utils/frappe.js";
import { terminosPara } from "@/utils/terminos.js";
import { useToast } from "@/composables/useToast.js";
import { useDocumentActions } from "@/composables/useDocumentActions.js";
import { asegurarCompania, useCompany } from "@/composables/useCompany.js";

const { state: companyState } = useCompany();
import { useProduccion } from "@/composables/useProduccion.js";

// Almacenes / centros de costos de la compañía elegida -- se acotan a ella para que
// el buscador no ofrezca los de otra empresa del mismo sitio.
const warehouseFilters = computed(() => [["company", "=", form.compania || ""], ["is_group", "=", 0], ["disabled", "=", 0]]);
const costCenterFilters = computed(() => [["company", "=", form.compania || ""], ["is_group", "=", 0]]);
const faltanAlmacenes = computed(() => !form.almacen_materias_primas || !form.almacen_trabajo_en_proceso || !form.centro_de_costos);
const ITEM_FILTERS = {
  terminado: [["item_group", "=", "Productos Terminados"]],
  mp:        [["item_group", "in", ["Materia prima", "Sub-Ensamblajes", "Consumible"]]],
  servicio:  [["item_group", "=", "Servicios"]],
  sub:       [["item_group", "in", ["Sub-Ensamblajes", "Productos Terminados"]]],
};
const ROW_TYPE_ITEM_FILTERS = {
  material: ITEM_FILTERS.mp,
  servicio_etapa: ITEM_FILTERS.servicio,
  subensamblaje_etapa: ITEM_FILTERS.sub,
};
const ORDER = ["Borrador", "Cotizado", "Orden de Venta", "En Producción", "Entregado", "Completado"];
// Mismo mapeo ORDER -> STEPS que usa CosteoStepper.vue para colorear la barra (no son
// el mismo índice: p. ej. "En Producción" es ORDER[3] pero corresponde a STEPS[5]
// "Producir", no a STEPS[3] "Alta de Productos" -- usar ORDER.indexOf() directo como
// índice de paso mandaba de vuelta a "Alta de Productos" en cuanto ya se estaba
// trabajando en Producir). Se usa para abrir el proyecto directo en el último paso
// alcanzado. null en las posiciones 3 y 4 -- "Alta de Productos" y "Flujo de
// Producción" son dos vistas de la misma preparación bajo "Orden de Venta", ninguna
// dispara su propio costeo_status.
const STEP_ORDER_IDX = [0, 1, 2, null, null, 3, null, 4, null];
function statusToStep(status, hasPlanAlready, etapasCount = 0, pendientesCount = 0, ovValidada = false) {
  const statusIdx = Math.max(ORDER.indexOf(status), 0);
  if (statusIdx >= 5) return 8; // Completado -- ya no queda nada más que ver salvo Reportar
  let target = 0;
  for (let i = 0; i < STEP_ORDER_IDX.length; i++) {
    const lvl = STEP_ORDER_IDX[i];
    if (lvl !== null && lvl <= statusIdx) target = i;
  }
  // "Orden de Venta" cubre Vender (recién validada), Alta de Productos y Flujo de
  // Producción -- costeo_status no distingue entre esos tres, así que se usa lo que
  // YA existe para adivinar dónde se quedó exactamente:
  //   - ya hay Plan de producción -> el flujo ya se guardó y se pasó a producción,
  //     de sobra pasado Flujo de Producción.
  //   - no hay pendientes pero ya hay etapas capturadas -> Alta de Productos ya
  //     está resuelto, lo que sigue es Flujo de Producción.
  //   - lo demás (OV recién validada, Alta de Productos sin empezar) -> se queda
  //     en Vender: después de validar todavía falta ENVIAR la OV al cliente, y
  //     Alta de Productos ya queda habilitada para abrirla cuando toque.
  //   - pero nada de eso cuenta mientras la OV activa siga en borrador: el estado
  //     "Orden de Venta" llega desde que la OV se crea, y sin validarla no se pasa
  //     de Vender (ni al reabrir el proyecto ni desde la barra de etapas).
  if (statusIdx === 2) {
    if (!ovValidada) target = 2;
    else if (hasPlanAlready) target = 4;
    else if (pendientesCount === 0 && etapasCount > 0) target = 4;
    else target = 2;
  }
  return target;
}

const route = useRoute();
const router = useRouter();
const isNew = computed(() => !route.params.name);
const loading = ref(!isNew.value);
const saving = ref(false);
const advancing = ref(false);

const actionsRef = ref(null);
const actionsOpen = ref(false);
const confirmDelete = reactive({ open: false, loading: false });
const confirmDeleteQuot = reactive({ open: false, loading: false, name: "" });
const confirmDeleteSO = reactive({ open: false, loading: false, name: "" });
// Generar nueva OV: pedido recurrente del mismo cliente -- reusa los mismos
// artículos/precio acordado de una OV YA VALIDADA del costeo, sin volver a
// Costear/Cotizar; solo se ajusta la cantidad de cada uno. Bloqueada si el
// precio acordado venció, salvo rol CEO (get_precio_acordado_status/
// generar_replica_ov revalidan del lado servidor, esto solo evita el intento
// cuando ya se sabe que va a fallar). El botón vive a nivel costeo (arriba de
// la lista de OVs, no colgado de una en particular) -- si hay más de una OV
// validada, el modal deja elegir de cuál partir.
const sosValidadas = computed(() => related.sales_orders.filter(s => s.docstatus === 1));
// La OV que se usaría por default si se pulsa "Generar nueva OV" sin elegir
// una en particular: la activa si está validada, si no la última validada.
function _baseSoParaNuevaOv() {
  return (activeSO.value?.docstatus === 1 ? activeSO.value : null)
    || sosValidadas.value[sosValidadas.value.length - 1]
    || null;
}
// Estado del botón de arriba (a nivel costeo, no depende de abrir el modal):
// oculto mientras esa OV base no tenga precio acordado fijado; "vencido" si lo
// tiene pero ya caducó (el botón cambia a avisar en vez de desaparecer, para
// que quien tenga permiso de CEO lo note y pueda destrabarlo).
const nuevaOvGate = reactive({ show: false, vencido: false, esCeo: false, loading: false });
async function refreshNuevaOvGate() {
  const base = _baseSoParaNuevaOv();
  if (!base) { nuevaOvGate.show = false; nuevaOvGate.vencido = false; return; }
  nuevaOvGate.loading = true;
  try {
    const res = await call("costeo_yelke.api.costeo_api.get_precio_acordado_status", { sales_order: base.name });
    // Siempre que haya una OV validada de base: sin precio acordado se usa el último
    // precio vendido (ver _precio_nueva_ov); solo un acordado vencido pide permiso.
    nuevaOvGate.show = true;
    nuevaOvGate.vencido = !!res.vencido;
    nuevaOvGate.esCeo = !!res.es_ceo;
  } catch { nuevaOvGate.show = false; nuevaOvGate.vencido = false; }
  finally { nuevaOvGate.loading = false; }
}
const nuevaOvModal = reactive({ open: false, loading: false, generating: false, so: null, status: null, items: [] });
async function _cargarPrecioAcordado(so) {
  nuevaOvModal.so = so;
  nuevaOvModal.loading = true;
  nuevaOvModal.status = null;
  nuevaOvModal.items = [];
  try {
    const res = await call("costeo_yelke.api.costeo_api.get_precio_acordado_status", { sales_order: so.name });
    nuevaOvModal.status = res;
    nuevaOvModal.items = (res.items || []).map(i => ({ ...i }));
  } catch (e) { showToast(e.message || "No se pudo revisar el precio acordado", "error"); nuevaOvModal.open = false; }
  finally { nuevaOvModal.loading = false; }
}
// so opcional -- sin argumento (botón de arriba) toma la OV activa si está
// validada, si no la última OV validada del costeo.
function openNuevaOvModal(so) {
  const base = so || _baseSoParaNuevaOv();
  if (!base) { showToast("Necesitas al menos una Orden de Venta validada para generar otra", "error"); return; }
  nuevaOvModal.open = true;
  _cargarPrecioAcordado(base);
}
function cambiarBaseNuevaOv(soName) {
  const so = sosValidadas.value.find(s => s.name === soName);
  if (so) _cargarPrecioAcordado(so);
}
async function confirmarNuevaOv() {
  if (!nuevaOvModal.so) return;
  nuevaOvModal.generating = true;
  try {
    const res = await call("costeo_yelke.api.costeo_api.generar_replica_ov", {
      sales_order: nuevaOvModal.so.name,
      items: nuevaOvModal.items.map(r => ({ item_code: r.item_code, qty: r.qty, rate: r.rate })),
    });
    nuevaOvModal.open = false;
    expandedSOName.value = res.name;
    activeSOName.value = res.name;
    await loadRelated();
    previewKey.value++;
    showToast(`Nueva OV creada: ${res.name}`);
  } catch (e) { showToast(e.message || "No se pudo generar la nueva OV", "error"); }
  finally { nuevaOvModal.generating = false; }
}
const confirmCancel = reactive({ open: false, loading: false });
// ── Confirmar / revertir el flujo de producción ──
// Confirmado = el costeo ya está en producción: el flujo es de solo lectura (el
// servidor también lo exige, ver _exigir_flujo_editable) hasta revertirlo.
const flujoBloqueado = computed(() => ORDER.indexOf(docStatus.value) >= 3);
const confirmFlujoDlg = reactive({ open: false, accion: null });
const confirmRevertir = reactive({ open: false, loading: false });
// Resumen para revisar antes de confirmar: por producto, pasos, piezas, dónde se
// unen (elegido o deducido) y los avisos que la pantalla ya marca con ícono.
const resumenConfirmarFlujo = computed(() => (flujoOps.value || []).map((prod) => {
  const ops = prod.operaciones || [];
  const armado = armadoVivo(prod);
  const union = ops.find((o) => o.op_key === armado.ensamble);
  const avisos = [...(prod.avisos || [])];
  ops.forEach((op) => {
    if (opIncompleta(op)) avisos.push(`"${supplierLabel(prod, op)}" tiene datos incompletos (proveedor o servicio).`);
    if (esHuerfano(prod, op)) avisos.push(`"${supplierLabel(prod, op)}" no alimenta a ningún otro paso.`);
    if (recibeRedundantesVivo(prod, op).size) avisos.push(`"${supplierLabel(prod, op)}" recibe de más pasos de los necesarios (${recibeRedundanteTexto(prod, op)}).`);
  });
  return {
    producto: prod.finished_item, pasos: ops.length, piezas: (prod.sub_ensamblajes || []).filter((s) => (s.nombre || "").trim()).length,
    union: union ? `${supplierLabel(prod, union)}${armado.elegida ? "" : " (deducido por el sistema)"}` : "",
    avisos,
  };
}));
function pedirConfirmarFlujo(accion) {
  confirmFlujoDlg.accion = accion;
  confirmFlujoDlg.open = true;
}
async function aceptarConfirmarFlujo() {
  const accion = confirmFlujoDlg.accion;
  confirmFlujoDlg.open = false;
  if (accion) await accion();
}
const confirmDeshacerEncargo = reactive({ open: false, loading: false, sco: "", supplier: "", enviado: false, piezas: [] });
/** Abre la confirmación: dice qué piezas van en ese encargo (se deshacen juntas). */
function pedirDeshacerEncargo(sco, supplier, enviado, paradaId) {
  const piezas = (loteActivo.value?.ramas || [])
    .filter((r) => (celdaDe(r, paradaId)?.scos || []).includes(sco)).map((r) => r.pieza);
  Object.assign(confirmDeshacerEncargo, { open: true, sco, supplier, enviado, piezas });
}
/** Encargo de una celda del tablero (el más reciente), para resaltar en hover las
 *  demás piezas que van JUNTAS en él: al dar clic se abre ese mismo encargo. */
const hoverEncargo = ref(null);
function encargoDeCelda(celda, etapa) {
  const sco = (celda?.scos || [])[(celda?.scos || []).length - 1];
  return sco ? { parada_id: etapa.parada_id, sco } : null;
}
function mismoEncargoEnHover(celda, etapa) {
  const h = hoverEncargo.value;
  return !!h && h.parada_id === etapa.parada_id && (celda?.scos || []).includes(h.sco);
}
/** Desde el tablero: el encargo más reciente de esa celda. */
function pedirDeshacerCelda(celda, etapa) {
  const sco = (celda.scos || [])[celda.scos.length - 1];
  if (sco) pedirDeshacerEncargo(sco, etapa.supplier, celda.estado === "enviado", etapa.parada_id);
}
/** Solo un encargo vivo al que todavía no se le envía material: con el envío
 *  validado la mercancía ya está con el taller y no se regresa con un botón. */
const puedeDeshacerEncargo = computed(() => {
  const s = scoSel.value;
  if (!s || s.docstatus === 2 || !puedeEditar("talleres")) return false;
  return !s.transfer?.done && !(s.receipts || []).some((r) => r.docstatus === 1);
});
async function deshacerEncargo() {
  const sco = confirmDeshacerEncargo.sco;
  if (!sco) return;
  confirmDeshacerEncargo.loading = true;
  try {
    await call("costeo_yelke.api.costeo_api.deshacer_encargo", { sco });
    confirmDeshacerEncargo.open = false;
    salirDelTaller();
    await loadLotesProduccion();
    showToast(`Encargo ${sco} deshecho: sus piezas ya están otra vez por encargar`);
  } catch (e) {
    showToast(e.message || "No se pudo deshacer el encargo", "error");
  } finally {
    confirmDeshacerEncargo.loading = false;
  }
}
// ── Disfraz visual del reparto interno por pieza ──────────────────────────────
// Por dentro el material de una etapa se reparte entre sus piezas (truco para poder
// avanzar pieza por pieza) y eso deja cantidades como 17,014.867 m o sobrantes de
// 1.133 m. Yelke no gestiona por piezas: en pantalla se ve en unidades cerradas y
// los residuos de menos de una unidad no se muestran. El documento NO cambia (el
// campo solo escribe si la persona edita la cantidad).
const cantidadVisible = (q) => Math.ceil((Number(q) || 0) - 1e-6);
const sobranteVisible = (q) => (Number(q) || 0) >= 1;
/** «CAMISOLA-GABARDINA-NARANJA · BOLSA-C» -> «BOLSA», con el producto abajo: el
 *  sufijo (-C, -CR…) es el estado interno de la pieza en el flujo. */
function nombreVisible(texto) {
  const t = String(texto || "");
  const i = t.indexOf(" · ");
  if (i < 0) return { titulo: t, sub: "" };
  const slug = t.slice(i + 3).replace(/-[A-Z]{1,4}$/, "");
  return { titulo: nombrePorSlug.value[slug] || slug.replace(/-/g, " "), sub: t.slice(0, i) };
}
// El código de la pieza pierde acentos y ñ («PUÑOS» -> «PUNOS»): se traduce al
// nombre real con las piezas del lote.
const slugPieza = (n) => String(n || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
  .toUpperCase().replace(/[^A-Z0-9]+/g, "-").replace(/^-+|-+$/g, "");
const nombrePorSlug = computed(() => Object.fromEntries(
  (loteActivo.value?.ramas || []).map((r) => [slugPieza(r.pieza), r.pieza])));
async function revertirFlujo() {
  confirmRevertir.loading = true;
  try {
    const r = await call("costeo_yelke.api.costeo_api.revertir_flujo_produccion", { costeo: docName.value });
    confirmRevertir.open = false;
    await loadCosteoData();
    activeStep.value = 4;
    await loadFlujoOps();
    showToast(`Flujo revertido: se borraron ${r.boms.length} BOM y ${r.subcontracting_boms.length} Subcontracting BOM. Ya puedes corregirlo.`);
  } catch (e) {
    showToast(e.message || "No se pudo revertir el flujo", "error");
  } finally {
    confirmRevertir.loading = false;
  }
}
const materializeModal = reactive({ open: false, saving: false, text: "", suggestedPrice: 0, suggestedDescription: "", suggestedImage: "", suggestedCode: "", esVariante: false, tallasExtra: [], soloTallas: false });
const pendientesArticulos = ref([]);
const pendientesContext = reactive({ company: "", almacen_materias_primas: "", almacen_trabajo_en_proceso: "" });
const pendientesAdvertencias = ref([]);
const articuloModal = reactive({ open: false, saving: false, group: null });

const docName = ref(null);
const docStatus = ref("Borrador");

// Resaltado al llegar desde una lista de documentos (ej. /ordenes-compra): pinta un
// borde naranja una vez sobre la tarjeta/OC exacta para que no haya que buscarla a
// mano entre todos los lotes del paso "Producir".
const highlightTarget = ref(null);

// La OC de materia prima de un lote vive DENTRO de "Pantalla de un lote" (requiere
// loteProductoActivo + loteActivoRef ya puestos) -- busca en TODOS los productos/lotes
// del costeo (no solo el que esté activo ahora mismo) cuál lote+proveedor tiene esta
// OC/Recibo, para poder pararse ahí sin que el usuario tenga que ir clic por clic.
function resolverLoteYGrupoMaterial(name, { porRecibo = false } = {}) {
  for (const lote of lotesProduccion.value) {
    const po = (lote.material_pos || []).find((p) => porRecibo ? p.receipt?.name === name : p.name === name);
    if (po) {
      const grp = proveedoresLote(lote).find((g) => g.po?.name === po.name);
      if (grp) return { lote, grp };
    }
  }
  return null;
}
// La OC de subcontratación puede agrupar VARIAS etapas del mismo proveedor en
// líneas separadas (ver _create_subcontracting_pos_from_stages en el backend --
// ej. 3 servicios de bordado distintos, mismo bordador, en una sola OC), así que
// más de una "etapa" puede compartir el mismo `e.po`. Encuentra la PRIMERA que
// haga match -- no hace falta desambiguar más: todas las etapas que comparten OC
// comparten también el mismo estado de OC/SCO/transferencia/recibo (es el mismo
// documento), así que abrir cualquiera de ellas muestra la información correcta.
function resolverLoteYParadaPo(name) {
  for (const lote of lotesProduccion.value) {
    const parada = (lote.paradas || []).find((p) => p.po === name);
    if (parada) return { lote, parada };
  }
  return null;
}

// Factura de compra de MATERIAL: la trae la OC del proveedor dentro de su lote
// (material_pos[].factura, ver get_lotes_produccion).
function resolverLoteYFacturaMaterial(name) {
  for (const lote of lotesProduccion.value) {
    const po = (lote.material_pos || []).find((p) => p.factura?.name === name);
    if (po) {
      const grp = proveedoresLote(lote).find((g) => g.po?.name === po.name);
      if (grp) return { lote, grp };
    }
  }
  return null;
}
/** El lote y la parada de un encargo, su envío o su recibo de maquila. */
function resolverLoteYParadaPorDocumento(name, doctype) {
  for (const lote of lotesProduccion.value) {
    for (const parada of lote.paradas || []) {
      for (const e of parada.entregas || []) {
        if (doctype === "Subcontracting Order" && e.sco === name) return { lote, parada };
        if (doctype === "Subcontracting Receipt" && e.receipt?.name === name) return { lote, parada };
      }
      // El envío (Stock Entry) no viaja en la respuesta; se abre la parada que
      // todavía tiene material en camino, que es donde vive ese movimiento.
      if (doctype === "Stock Entry" && (parada.entregas || []).some((e) => e.transfer_done)) return { lote, parada };
    }
  }
  return null;
}

// Factura de MAQUILA: la OC de un taller cubre varios lotes, así que puede aparecer
// en más de una parada -- se abre la primera, que es el mismo documento.
function resolverLoteYParadaFactura(name) {
  for (const lote of lotesProduccion.value) {
    const parada = (lote.paradas || []).find((p) => p.factura?.name === name);
    if (parada) return { lote, parada };
  }
  return null;
}

// Dónde vive cada documento en la Producción nueva (plan §7.3). Llegar desde una
// lista de documentos abre la vista exacta, con su panel o su paso ya abiertos.
async function abrirLoteEnPaso(lote_ref, paso) {
  activeStep.value = 5;
  await irProduccion({ vista: "lote", lote: lote_ref, paso });
}

async function triggerHighlight(name, doctype) {
  if (doctype === "Purchase Order" || !doctype) {
    // Sin doctype explícito (o "Purchase Order"): puede ser una OC de materia prima
    // de un lote, la OC (compartida) de un taller, o -- documentos viejos que ya no
    // viven en ningún lote -- alguna de las listas planas de respaldo.
    const matMatch = resolverLoteYGrupoMaterial(name);
    const subMatch = !matMatch ? resolverLoteYParadaPo(name) : null;
    if (matMatch) {
      await abrirLoteEnPaso(matMatch.lote.lote_ref, "materia");
      await abrirPanelProveedor(matMatch.grp, "oc");
    } else if (subMatch) {
      // La OC de maquila es de la PREPARACIÓN (una por taller, cubre todos los
      // lotes), no de un lote en particular.
      activeStep.value = 5;
      prodRuta.irPreparacion(3);
      await nextTick();
      await abrirOcTaller({ name, supplier: subMatch.parada.supplier, supplier_name: subMatch.parada.supplier });
    } else if (mpLotes.value.some((o) => o.name === name)) {
      await selectOcLote(name);
    } else if (subOcs.value.some((o) => o.name === name)) {
      activeStep.value = 5;
      prodRuta.irPreparacion(3);
      await nextTick();
      await abrirOcTaller(subOcs.value.find((o) => o.name === name));
    }
  } else if (doctype === "Purchase Receipt") {
    const matMatch = resolverLoteYGrupoMaterial(name, { porRecibo: true });
    if (matMatch) {
      await abrirLoteEnPaso(matMatch.lote.lote_ref, "materia");
      await abrirPanelProveedor(matMatch.grp, "recibo");
    } else {
      const oc = mpLotes.value.find((o) => (o.receipts || []).includes(name));
      if (oc) await selectOcLote(oc.name);
    }
  } else if (doctype === "Material Request") {
    // La solicitud es de la Preparación (paso 2): un mismo MR se reparte entre
    // todos los lotes, no vive dentro de ninguno.
    activeStep.value = 5;
    loteActivoRef.value = "";
    prodRuta.irPreparacion(2);
  } else if (["Subcontracting Order", "Subcontracting Receipt", "Stock Entry"].includes(doctype)) {
    // Encargo / envío / recibo de un taller: su sub-pantalla, en el paso que toca.
    const m = resolverLoteYParadaPorDocumento(name, doctype);
    if (m) {
      await abrirLoteEnPaso(m.lote.lote_ref, "talleres");
      await irAParada(m.parada, { "Subcontracting Order": "sco", "Stock Entry": "transfer",
                                  "Subcontracting Receipt": "recibo" }[doctype]);
    }
  } else if (doctype === "Delivery Note") {
    await selectDn(name);
  } else if (doctype === "Purchase Invoice") {
    // Las facturas de compra viven en su bandeja de Producción (antes mandaba a una
    // pestaña "compras" del paso 7 que ya no existe, así que el enlace no llevaba a
    // ninguna parte).
    activeStep.value = 5;
    await cargarDatosProduccion();
    const fila = facturasTodas.value.find((f) => f.nombre && (
      (f.tipo === "material" && resolverLoteYFacturaMaterial(name)) ||
      (f.tipo === "maquila" && resolverLoteYParadaFactura(name))));
    prodRuta.irVista("facturas", { filtro_lote: "__todos" });
    await nextTick();
    const objetivo = facturasTodas.value.find((f) => f.nombre === fila?.nombre) || null;
    if (objetivo) await objetivo.ir();
  }
  // Quotation / Sales Order / Sales Invoice: un solo documento ya cargado por
  // loadRelated() -- no hace falta "seleccionar" nada más.
  highlightTarget.value = name;
  await nextTick();
  await scrollToStable(`doc-hl-${name}`);
  setTimeout(() => { if (highlightTarget.value === name) highlightTarget.value = null; }, 1200);
}
// Paneles anidados varios niveles (ej. el recibo de una OC de materia prima, debajo del
// panel de la OC que trae su propio iframe de vista previa del PDF) siguen corriendo su
// layout bastante después de montarse -- el iframe puede tardar más de un segundo en
// cargar y, al hacerlo, empuja hacia abajo todo lo que está debajo, dejando un
// scrollIntoView ya hecho apuntando a la posición vieja. En vez de adivinar cuánto tarda
// con un número fijo de reintentos, re-scrollear cada 250ms hasta que la posición del
// elemento en pantalla deje de moverse dos veces seguidas (o se agote el tiempo máximo).
async function scrollToStable(id, maxMs = 3000) {
  // OJO: re-consulta el elemento en CADA vuelta (no guarda la referencia) -- si algo
  // reactivo lo vuelve a montar (destruye/crea el nodo) a media carrera, el siguiente
  // tick agarra el nodo nuevo solo. Corre el tiempo completo sin salir antes "porque ya
  // se ve estable", que fue justo lo que dejaba el scroll apuntando al nodo viejo.
  const start = Date.now();
  let first = true;
  while (Date.now() - start < maxMs) {
    const el = document.getElementById(id);
    if (el) {
      // "smooth" solo en el primer intento (se ve bien) -- pedirlo de nuevo en cada
      // reintento cancela la animación anterior a medio camino y el navegador se queda
      // sin moverse nunca; los reintentos de corrección van "instant" a propósito.
      el.scrollIntoView({ behavior: first ? "smooth" : "instant", block: "center" });
      first = false;
    }
    await new Promise((r) => setTimeout(r, 300));
  }
}
const docState = ref(0); // docstatus del Costeo: 0 borrador, 1 validado
const activeStep = ref(0);
const related = reactive({ quotation: null, quotations: [], quotations_historial: [], sales_order: null, sales_orders: [], delivery_notes: [], delivery_per_delivered: 0, sales_invoice: null });
const cotForm = reactive({
  valid_till: "", payment_terms_template: "", tc_name: "", custom_tipo_formato: "Normal",
  currency: "MXN", selling_price_list: "", taxes_and_charges: "", contact_email: "", contact_mobile: "",
});
// Artículos de la cotización -- editable aparte de lo que crear_cotizacion generó del
// Costeo (cantidad, precio, o artículos extra que no vienen del Costeo). Se carga con
// get_quotation (mismo endpoint que usa la página dedicada de Cotización) y se guarda
// con actualizar_cotizacion cuando se le da "Guardar cambios".
const cotItems = ref([]);
async function loadCotItems(name) {
  if (!name) { cotItems.value = []; return; }
  try {
    const data = await call("costeo_yelke.api.quotation_api.get_quotation", { name });
    cotItems.value = (data.items || []).map(r => ({ ...r, amount: round2((r.qty || 0) * (r.rate || 0)) }));
  } catch { cotItems.value = []; }
}
// Un Costeo puede acumular varias cotizaciones (rechazada + nueva, "Cotizar de
// nuevo"...) -- a diferencia de "Productos a costear" (expandedTids, varios
// abiertos a la vez), aquí SÍ solo una expandida: expandirla carga sus datos en
// cotForm/cotItems, un solo panel de edición compartido para reusarlo tal cual.
const expandedQuotName = ref(null);
let quotAutoExpandDone = false;
function applyQuotToForm(q) {
  cotForm.valid_till = q.valid_till || "";
  cotForm.payment_terms_template = q.payment_terms_template || "";
  cotForm.tc_name = q.tc_name || "";
  cotForm.custom_tipo_formato = q.custom_tipo_formato || "Normal";
  cotForm.currency = q.currency || "MXN";
  cotForm.selling_price_list = q.selling_price_list || "";
  cotForm.taxes_and_charges = q.taxes_and_charges || "";
  cotForm.contact_email = q.contact_email || "";
  cotForm.contact_mobile = q.contact_mobile || "";
}
async function toggleQuotation(q) {
  if (expandedQuotName.value === q.name) { expandedQuotName.value = null; return; }
  expandedQuotName.value = q.name;
  applyQuotToForm(q);
  await loadCotItems(q.name);
}
/** Las columnas de consumo: un producto terminado por columna. El orden lo manda el
 *  plan (po_items), que es el mismo del costeo; si algún producto solo aparece en el
 *  consumo, se agrega al final para no perderlo. */
const columnasConsumo = computed(() => {
  const nombres = new Map();
  for (const it of planDetail.value?.mr_items || []) {
    for (const c of it.consumo || []) {
      if (!nombres.has(c.finished_item)) nombres.set(c.finished_item, c.item_name || c.finished_item);
    }
  }
  const orden = (planDetail.value?.po_items || []).map((p) => p.item_code).filter((x) => nombres.has(x));
  for (const code of nombres.keys()) if (!orden.includes(code)) orden.push(code);
  return orden.map((code) => ({ code, nombre: nombres.get(code) }));
});
/** El consumo de ESE material para ESE producto, o null si no lo lleva. */
function consumoDe(it, code) {
  return (it.consumo || []).find((c) => c.finished_item === code) || null;
}
function fmtConsumo(c) {
  return `${Number(c.qty || 0).toLocaleString("es-MX", { maximumFractionDigits: 4 })} ${c.uom || ""}`.trim();
}

/** Consumo por prenda de un material del plan, para la línea informativa.
 *  Con un solo producto se omite su nombre (sobra); con varios se listan todos,
 *  porque es justo lo que hay que poder comparar. */
function consumoTexto(it) {
  const c = it.consumo || [];
  if (!c.length) return "";
  const n = (x) => Number(x.qty || 0).toLocaleString("es-MX", { maximumFractionDigits: 4 });
  const base = c.length === 1
    ? `${n(c[0])} ${c[0].uom || ""} por prenda`
    : "por prenda: " + c.map((x) => `${x.item_name} ${n(x)} ${x.uom || ""}`).join(" · ");
  // Avisa cuando el consumo NO salió del costeo: el plan lo pide porque está en el
  // BOM del producto, pero este costeo nunca lo costeó.
  return consumoFueraDelCosteo(it) ? `${base} — del BOM, no está en el costeo` : base;
}
/** ¿Algún renglón de consumo salió del BOM en vez del costeo? */
function consumoFueraDelCosteo(it) {
  return (it.consumo || []).some((c) => c.origen === "bom");
}
/** El tooltip explica la trampa de las unidades: el plan pide en UDM de compra. */
function consumoTitulo(it) {
  const c = it.consumo || [];
  if (!c.length) return "";
  const lineas = c.map((x) => `${x.item_name}: ${x.qty} ${x.uom || ""} por prenda`
    + (x.origen === "bom" ? "  (del BOM del producto)" : "")).join("\n");
  const aviso = consumoFueraDelCosteo(it)
    ? "\n\nOJO: este material NO está declarado en el costeo. El plan lo pide porque "
      + "viene en el BOM del producto, así que su costo no entró en el precio."
    : "";
  return lineas
    + `\n\nEl plan pide ${it.quantity} ${it.uom || ""} en total (unidad de compra); `
    + "el consumo va en la unidad con la que se costeó." + aviso;
}

// ── OC del cliente: el archivo, no un número escrito a mano ─────────────────
const ocClienteSubiendo = ref(false);
/** ¿Este sitio ya tiene el campo de archivo? Lo dice el backend (patch v0_2_56). Sin
 *  él la pantalla sigue pidiendo el NÚMERO de OC, como siempre: nunca se queda sin el
 *  dato por una migración pendiente. */
const ocClienteEsArchivo = computed(() => !!cotDefaults.oc_cliente_archivo_disponible);
/** Sube el archivo y lo deja adjunto a `doctype/docname`: la Orden de Venta cuando ya
 *  existe, o el Costeo mientras no -- un adjunto necesita un documento guardado. */
async function subirOcCliente(ev, doctype, docname) {
  const file = ev?.target?.files?.[0];
  if (!file) return;
  if (!docname) { showToast("Guarda el costeo antes de adjuntar la OC del cliente", "error"); return; }
  ocClienteSubiendo.value = true;
  try {
    const res = await uploadFile(file, { doctype, docname });
    soForm.oc_cliente_archivo = res?.file_url || "";
    // Si la OV ya existe, el campo se persiste de una; si no, viaja al crearla.
    if (doctype === "Sales Order") {
      await call("frappe.client.set_value", {
        doctype: "Sales Order", name: docname,
        fieldname: "oc_cliente_archivo", value: soForm.oc_cliente_archivo,
      });
    }
    showToast("OC del cliente adjuntada");
  } catch (e) {
    showToast(e.message || "No se pudo subir el archivo", "error");
  } finally {
    ocClienteSubiendo.value = false;
    if (ev?.target) ev.target.value = "";   // deja re-elegir el mismo archivo
  }
}
async function quitarOcCliente(doctype, docname) {
  soForm.oc_cliente_archivo = "";
  if (doctype === "Sales Order" && docname) {
    try {
      await call("frappe.client.set_value", {
        doctype: "Sales Order", name: docname, fieldname: "oc_cliente_archivo", value: "",
      });
    } catch (e) { showToast(e.message || "No se pudo quitar", "error"); }
  }
}

const soForm = reactive({
  delivery_date: "", delivery_weeks: null, payment_terms_template: "", tc_name: "", po_no: "",
  oc_cliente_archivo: "",
  currency: "MXN", selling_price_list: "", taxes_and_charges: "", contact_email: "", contact_mobile: "",
});
// El usuario captura el tiempo de entrega en SEMANAS (lo que de verdad conoce al
// cotizar) -- delivery_date (la fecha real que se guarda en la Orden de Venta
// nativa) se calcula sola a partir de hoy + esas semanas, en vez de pedirle que
// calcule la fecha exacta a mano.
function onDeliveryWeeksChange() {
  const weeks = Number(soForm.delivery_weeks);
  if (!weeks || weeks <= 0) { soForm.delivery_date = ""; return; }
  const d = new Date();
  d.setDate(d.getDate() + Math.round(weeks * 7));
  soForm.delivery_date = d.toISOString().slice(0, 10);
}
// Igual patrón que las cotizaciones: puede haber varias OV bajo un mismo Costeo
// (réplicas de un pedido recurrente) -- acordeón, solo una expandida a la vez, y esa
// misma es la que "activa" (activeSOName) filtra Producir/Enviar/Facturar/Reportar.
const expandedSOName = ref(null);
let soAutoExpandDone = false;
function applySOToForm(so) {
  soForm.delivery_date = so.delivery_date || "";
  // Reconstruye las semanas mostradas a partir de la fecha ya guardada (redondeo
  // razonable) -- solo para mostrar algo sensato al reabrir; en cuanto el usuario
  // vuelve a tocar el campo de semanas, delivery_date se recalcula desde cero.
  if (so.delivery_date) {
    const dias = Math.round((new Date(so.delivery_date) - new Date(today())) / 86400000);
    soForm.delivery_weeks = dias > 0 ? Math.round(dias / 7) : null;
  } else {
    soForm.delivery_weeks = null;
  }
  soForm.payment_terms_template = so.payment_terms_template || "";
  soForm.tc_name = so.tc_name || "";
  soForm.po_no = so.po_no || "";
  soForm.oc_cliente_archivo = so.oc_cliente_archivo || "";
  soForm.currency = so.currency || "MXN";
  soForm.selling_price_list = so.selling_price_list || "";
  soForm.taxes_and_charges = so.taxes_and_charges || "";
  soForm.contact_email = so.contact_email || "";
  soForm.contact_mobile = so.contact_mobile || "";
}
function toggleSalesOrder(so) {
  if (expandedSOName.value === so.name) { expandedSOName.value = null; return; }
  expandedSOName.value = so.name;
  applySOToForm(so);
  loadSoVariantesForm(so);
  loadSoDesgloseForm(so);
}

// ── Cantidades confirmadas por talla (solo en la OV, nunca en la Cotización) ──
// Las variantes de talla de este Costeo ya están cargadas en `productos` --
// no hace falta pedirlas aparte al servidor.
const variantesDelCosteo = computed(() => productos.value.filter(p => p.variante_talla_de));
// Las tallas extra de la OV agrupadas bajo su producto: "Caballero XXL" a secas no dice
// si es del pantalón o de la camisola.
const soVariantesGrupos = computed(() => {
  const grupos = [];
  for (const v of soVariantesForm.value) {
    let g = grupos.find(x => x.base === v.base);
    if (!g) grupos.push(g = { base: v.base, nombre: v.base_nombre, variantes: [] });
    g.variantes.push(v);
  }
  return grupos;
});
// ¿La OV abierta tiene algo de tallas que mostrar (capturable o ya validado)?
function hayTallasOV(so) {
  if (so.docstatus === 0) return !!(soDesgloseForm.value.length || variantesDelCosteo.value.length);
  if (so.docstatus === 1) return soDesgloseForm.value.some((d) => (d.filas || []).length) || !!soVariantesForm.value.length;
  return false;
}
// Orden de la lista de Costear: cada variante de talla justo debajo de su producto base
// (en el orden en que se crearon), no al final de todos los productos. Solo cambia
// cómo se dibuja: `productos` conserva su orden (es el que se guarda).
const productosApilados = computed(() => {
  const lista = productos.value;
  const bases = new Set(lista.filter(p => !p.variante_talla_de).map(p => p.finished_item));
  const out = [];
  for (const p of lista) {
    if (p.variante_talla_de && bases.has(p.variante_talla_de)) continue;
    out.push(p);
    if (!p.variante_talla_de && p.finished_item) out.push(...lista.filter(v => v.variante_talla_de === p.finished_item));
  }
  return out;
});

// ── Desglose por talla del producto principal (api/tallas_ov.py) ──
const soDesgloseForm = ref([]);
// De qué OV (y en qué estado) es lo que hay cargado ahora en soDesgloseForm.
// Sirve para poder llamar al cargador desde varios lados sin repetir la llamada
// ni pisar lo que el usuario esté capturando.
const soDesgloseDe = ref(null);
function sumaDesglose(d) {
  return Object.values(d.valores).reduce((a, b) => a + (Number(b) || 0), 0);
}
async function loadSoDesgloseForm(so, forzar = false) {
  if (!so || so.docstatus === 2) { soDesgloseForm.value = []; soDesgloseDe.value = null; return; }
  const firma = `${so.name}:${so.docstatus}`;
  if (!forzar && soDesgloseDe.value === firma) return;
  soDesgloseDe.value = firma;
  try {
    await loadAllTallas();
    const filas = await call("costeo_yelke.api.tallas_ov.get_desglose_tallas_ov", { sales_order: so.name });
    soDesgloseForm.value = (filas || []).map((f) => {
      const valores = {};
      for (const x of f.filas || []) valores[x.talla] = x.qty;
      // Un bloque por cada tipo de talla que ya trae piezas (Caballero y Dama pueden ir juntos).
      const bloques = [];
      for (const x of f.filas || []) {
        const t = allTallas.value.find((y) => y.name === x.talla);
        if (t && !bloques.some((b) => b.grupo === t.parent_talla)) bloques.push({ genero: t.genero || "", grupo: t.parent_talla || "" });
      }
      return { ...f, valores, bloques: bloques.length ? bloques : [{ genero: "", grupo: "" }] };
    });
  } catch { soDesgloseForm.value = []; soDesgloseDe.value = null; }
}
// Guarda el desglose regular de la OV (lo usan su botón y «Guardar cambios»/«Validar
// orden»). Puede ir a medias mientras la OV está en borrador; exacto se exige al validar.
async function persistirDesgloseOV(so) {
  if (!soDesgloseForm.value.length || soDesgloseDe.value !== `${so.name}:0`) return;
  for (const d of soDesgloseForm.value) {
    const suma = sumaDesglose(d);
    if (suma > d.qty) throw new Error(`El desglose de "${d.item_name}" suma ${suma} y el producto lleva ${d.qty}`);
  }
  // Guardar las tallas extra reconstruye los renglones de la OV (cambian de nombre):
  // se vuelve a pedir el renglón vigente de cada producto antes de escribirle su desglose.
  const vigentes = await call("costeo_yelke.api.tallas_ov.get_desglose_tallas_ov", { sales_order: so.name }) || [];
  for (const d of soDesgloseForm.value) {
    const actual = vigentes.find((v) => v.row === d.row) || vigentes.find((v) => v.item_code === d.item_code);
    if (actual) d.row = actual.row;
  }
  for (const d of soDesgloseForm.value) {
    limpiarDesglose(d);
    const filas = Object.entries(d.valores).filter(([, q]) => Number(q) > 0).map(([talla, qty]) => ({ talla, qty: Number(qty) }));
    await call("costeo_yelke.api.tallas_ov.guardar_desglose_tallas_ov", { sales_order: so.name, row: d.row, filas: JSON.stringify(filas) });
  }
}
const soVariantesForm = ref([]);
const soVariantesLoading = ref(false);
// Igual que soDesgloseDe: de qué OV y en qué estado es lo que está cargado.
const soVariantesDe = ref(null);

// Las tallas de una variante que de verdad llevan piezas -- para enseñarlas
// cuando la OV ya está validada y el desglose ya no se puede editar.
function tallasConPiezas(v) {
  return (v.codigos || [])
    .map((t) => ({ ...t, qty: Number(v.desglose?.[t.code]) || 0 }))
    .filter((t) => t.qty > 0);
}
function totalVariante(v) {
  return Object.values(v.desglose || {}).reduce((a, b) => a + (Number(b) || 0), 0);
}
// Tallas que se le pueden agregar a una variante: las NO regulares (sin uso común) del
// mismo tipo de talla que ya cubre -- las regulares van en el desglose del producto base.
function tallasExtraDisponibles(v) {
  const grupos = new Set(v.codigos.map(t => allTallas.value.find(x => x.name === t.code)?.parent_talla).filter(Boolean));
  if (!grupos.size) for (const g of gruposDeGenero(v.genero)) grupos.add(g.name);
  const ya = new Set(v.codigos.map(t => t.code));
  return allTallas.value.filter(t => !t.is_group && grupos.has(t.parent_talla) && !t.uso_comun && !ya.has(t.name));
}
function agregarTallaVariante(v, code) {
  const t = allTallas.value.find(x => x.name === code);
  if (!t || v.codigos.some(c => c.code === code)) return;
  v.codigos.push({ code, label: t.talla });
  v.desglose[code] = 0;
}
// Recupera el reparto guardado de la descripción de la línea ("- 5XL × 3 pza(s)"),
// incluidas tallas que se agregaron en la OV y que la variante no traía de origen.
function desgloseGuardadoVariante(description, v) {
  const out = {};
  for (const m of (description || "").replace(/<[^>]+>/g, "\n").matchAll(/-\s*(.+?)\s*×\s*([\d.,]+)\s*pza/g)) {
    const label = m[1].trim();
    const propia = v.tallas.find(t => t.label === label);
    // Una misma etiqueta ("46") existe en varios tipos de talla: primero el de la variante.
    const grupos = new Set(v.tallas.map(c => allTallas.value.find(x => x.name === c.code)?.parent_talla));
    const candidatas = allTallas.value.filter(x => !x.is_group && x.talla === label && (!v.genero || x.genero === v.genero));
    const t = propia ? { name: propia.code } : (candidatas.find(x => grupos.has(x.parent_talla)) || candidatas[0]);
    if (t) out[t.name] = Number(m[2].replace(/,/g, ""));
  }
  return Object.keys(out).length ? out : null;
}

async function loadSoVariantesForm(so, forzar = false) {
  // Una OV validada ya no se edita, pero el desglose se tiene que seguir
  // viendo: antes esta función se salía en seco y la sección entera
  // desaparecía en cuanto se validaba la orden.
  if (!so || !variantesDelCosteo.value.length || so.docstatus === 2) {
    soVariantesForm.value = []; soVariantesDe.value = null; return;
  }
  const firma = `${so.name}:${so.docstatus}`;
  if (!forzar && soVariantesDe.value === firma) return;
  soVariantesDe.value = firma;
  const soloLectura = so.docstatus !== 0;
  soVariantesLoading.value = true;
  try {
    await loadAllTallas();
    const [data, variantes] = await Promise.all([
      call("costeo_yelke.api.sales_order_api.get_sales_order", { name: so.name }),
      call("costeo_yelke.api.costeo_api.listar_variantes_de_costeo", { costeo: docName.value }),
    ]);
    const porItem = Object.fromEntries((data.items || []).map(it => [it.item_code, it]));
    soVariantesForm.value = variantes.map(v => {
      const linea = porItem[v.finished_item];
      const qty = linea ? linea.qty : 0;
      const tallas = v.tallas || [];
      // El desglose no tiene un campo propio donde vivir -- se recupera de
      // la descripción ya guardada (que es justo el desglose en texto, ver
      // _build_variante_description), para no perder lo que el usuario
      // ajustó a mano cada vez que se recarga este formulario tras guardar.
      // Solo si no hay nada que recuperar (variante nueva, sin guardar
      // todavía) se arranca con un reparto parejo de punto de partida.
      const desglose = {};
      const recuperado = desgloseGuardadoVariante(linea?.description, { tallas, genero: v.genero });
      if (recuperado) {
        Object.assign(desglose, recuperado);
      } else if (tallas.length) {
        // Sin reparto guardado: parejo entre sus tallas como punto de partida.
        const base = Math.floor(qty / tallas.length);
        let resto = Math.round(qty) - base * tallas.length;
        for (const t of tallas) {
          desglose[t.code] = base + (resto > 0 ? 1 : 0);
          if (resto > 0) resto--;
        }
      }
      // Sus tallas de origen, más las que se le agregaron en la OV.
      const codigos = [...tallas];
      for (const code of Object.keys(desglose)) {
        if (!codigos.some(t => t.code === code)) codigos.push({ code, label: allTallas.value.find(x => x.name === code)?.talla || code });
      }
      return {
        item_code: v.finished_item,
        talla_grupo_label: v.talla_grupo_label || v.finished_item,
        base: v.variante_talla_de,
        base_nombre: v.producto_base_nombre || v.variante_talla_de,
        genero: v.genero || "",
        tallas,
        codigos,
        qty,
        rate: linea ? linea.rate : (productos.value.find(p => p.finished_item === v.finished_item)?.unit_sales_price || 0),
        desglose,
      };
    });
    // En una OV validada solo se enseña lo que de verdad se vendió.
    if (soloLectura) soVariantesForm.value = soVariantesForm.value.filter((v) => Number(v.qty) > 0);
  } catch (e) {
    showToast(e.message || "No se pudieron cargar las variantes de esta orden", "error");
    soVariantesForm.value = []; soVariantesDe.value = null;
  } finally {
    soVariantesLoading.value = false;
  }
}

// Guarda las tallas extra confirmadas de la OV (lo usan su botón y «Guardar
// cambios»/«Validar orden»).
async function persistirVariantesOV(so) {
  if (!soVariantesForm.value.length || soVariantesDe.value !== `${so.name}:0`) return;
  // El total de cada variante es la suma de sus tallas.
  for (const v of soVariantesForm.value) v.qty = totalVariante(v);
  const data = await call("costeo_yelke.api.sales_order_api.get_sales_order", { name: so.name });
  const variantCodes = new Set(soVariantesForm.value.map(v => v.item_code));
  // Las líneas que NO son variantes se mandan tal cual venían -- esta sección
  // solo toca las de variante, nunca el resto de los productos de la orden.
  const items = (data.items || [])
    .filter(it => !variantCodes.has(it.item_code))
    .map(it => ({
      item_code: it.item_code, item_name: it.item_name, description: it.description,
      qty: it.qty, uom: it.uom, conversion_factor: it.conversion_factor,
      rate: it.rate, discount_percentage: it.discount_percentage,
      warehouse: it.warehouse, delivery_date: it.delivery_date,
    }));
  // Almacén de referencia para una variante que se agrega por primera vez --
  // el mismo de cualquier otra línea ya presente (todas entregan del mismo
  // almacén). set_missing_values() no lo completa solo en un save() sobre un
  // documento ya existente (a diferencia de un insert() nuevo), así que hay
  // que mandarlo explícito o la línea nueva queda sin almacén y truena.
  const almacenRef = items[0]?.warehouse || "";
  const incluidas = soVariantesForm.value.filter(v => Number(v.qty) > 0);
  // Descripción (con el desglose por talla, si hay más de una en el grupo)
  // y UOM correctos, armados del lado del servidor con la misma lógica que
  // ya usa crear_cotizacion/crear_orden_venta -- reconstruirlos a mano aquí
  // ya se le olvidó el UOM una vez.
  const desglose = {}, cantidades = {};
  for (const v of incluidas) {
    desglose[v.item_code] = Object.fromEntries(Object.entries(v.desglose).filter(([, q]) => Number(q) > 0));
    cantidades[v.item_code] = v.qty;
  }
  // Precio de cada variante: su tabla por volumen para esa cantidad, o su precio de venta.
  const lineas = incluidas.length
    ? await call("costeo_yelke.api.costeo_api.lineas_venta_variantes", {
        costeo: docName.value, finished_items: JSON.stringify(incluidas.map(v => v.item_code)),
        desglose: JSON.stringify(desglose), cantidades: JSON.stringify(cantidades),
      })
    : {};
  for (const v of incluidas) {
    const linea = lineas[v.item_code] || {};
    items.push({
      item_code: v.item_code, qty: v.qty, rate: linea.rate || v.rate,
      description: linea.description || "", uom: linea.uom || "",
      warehouse: almacenRef, delivery_date: data.delivery_date,
    });
  }
  await call("costeo_yelke.api.sales_order_api.save_sales_order", {
    data: JSON.stringify({ name: so.name, items }),
  });
}
// "OV activa": la que filtra Producir/Enviar/Facturar/Reportar -- por default sigue a
// la expandida en Vender, pero se puede fijar aparte (selector en esos pasos) sin
// perder cuál está expandida en el acordeón de Vender.
const activeSOName = ref(null);
// Las OV que pueden ser "activa": una cancelada se queda solo como historial.
const soVivas = computed(() => related.sales_orders.filter(s => s.docstatus !== 2));
watch(expandedSOName, (name) => { if (name && soVivas.value.some(s => s.name === name)) activeSOName.value = name; });
const siForm = reactive({ posting_date: "", due_date: "", payment_terms_template: "", tc_name: "" });
const dnDoc = ref(null);
const dnSel = ref("");
const dnForm = reactive({ posting_date: "", shipping_address_name: "", customer_address: "", flete_proveedor: "", flete_costo: 0 , flete_incluye_iva: 0 });
const reporte = ref(null);
const reporteLoading = ref(false);
const compras = reactive({ materiales: [], maquila: [], fletes: [] });
const pinvSel = ref(null);
const pinvDoc = ref(null);
const pinvForm = reactive({ posting_date: "", due_date: "", bill_no: "", bill_date: "", payment_terms_template: "", tc_name: "", conversion_rate: 1, flete_cobra_iva: 0 });
const cotDefaults = reactive({ payment_terms_templates: [], terms: [], users: [], price_lists: [], currencies: [], tax_templates: [],
  // Lo rellena get_cotizacion_defaults; en falso la OC del cliente se captura como
  // número (sitio sin el patch v0_2_56).
  oc_cliente_archivo_disponible: false });
const prepSteps = ref([]);

const form = reactive({ titulo: "", cliente: "", fecha: today(), compania: "", proyecto: "", guardar_como_plantilla: false, centro_de_costos: "", almacen_materias_primas: "", almacen_trabajo_en_proceso: "" });
// Centro de costos y almacenes ya no se capturan a mano -- se derivan solos de
// la compañía (mismo criterio en costeo_api.get_company_defaults), para no
// pedirle al usuario que repita en cada costeo algo que siempre es igual.
// LinkInput emite el texto crudo en cada tecleo (no solo al seleccionar), así
// que tecleando "Tegra" se disparan 5 llamadas solapadas; sin esta guarda de
// petición vigente, una respuesta vieja (p.ej. de "Teg") puede resolverse
// después de la buena y borrar los almacenes en silencio, bloqueando el guardado.
let companyDefaultsReq = 0;
// `cargandoDoc` evita que abrir un costeo ya guardado dispare la autodetección y
// PISE los almacenes con los que se guardó: fillFromDoc asigna la compañía y luego
// los almacenes, pero el watcher es asíncrono y su respuesta llegaba después,
// sobrescribiéndolos (y borrándolos si esa compañía no los tiene con el nombre
// esperado).
let cargandoDoc = false;
const diagCompania = reactive({ faltantes: [] });
let diagReq = 0;
async function cargarDiagnosticoCompania(company) {
  const req = ++diagReq;
  if (!company) { diagCompania.faltantes = []; return; }
  try {
    const r = await call("costeo_yelke.compania_setup.diagnostico_compania", { company });
    if (req === diagReq) diagCompania.faltantes = r?.faltantes || [];
  } catch { if (req === diagReq) diagCompania.faltantes = []; }
}
watch(() => form.compania, (c) => cargarDiagnosticoCompania(c), { immediate: true });
async function applyCompanyDefaults(company) {
  if (!company || cargandoDoc) return;
  const req = ++companyDefaultsReq;
  try {
    const r = await call("costeo_yelke.api.costeo_api.get_company_defaults", { company });
    if (req !== companyDefaultsReq) return;
    // Sólo se escribe lo que el backend SÍ pudo resolver. Si no encontró un almacén,
    // se respeta lo que el usuario haya capturado a mano en vez de borrárselo -- ése
    // era el callejón sin salida: se limpiaba el campo y no había dónde corregirlo.
    if (r?.centro_de_costos) form.centro_de_costos = r.centro_de_costos;
    if (r?.almacen_materias_primas) form.almacen_materias_primas = r.almacen_materias_primas;
    if (r?.almacen_trabajo_en_proceso) form.almacen_trabajo_en_proceso = r.almacen_trabajo_en_proceso;
  } catch { /* ignore */ }
}
// Al CAMBIAR de compañía (no al cargar) los almacenes de la anterior ya no aplican:
// se limpian para que la autodetección -- o el usuario -- ponga los de la nueva.
watch(() => form.compania, (val, prev) => {
  if (prev && val !== prev && !cargandoDoc) {
    form.centro_de_costos = "";
    form.almacen_materias_primas = "";
    form.almacen_trabajo_en_proceso = "";
  }
  applyCompanyDefaults(val);
});
const errors = reactive({});
// Rol 'Aprobador de Documentos Yelke' (o System Manager) -- ver costeo_api.py
// puede_validar_costeo/validar_documento. Empieza en true (optimista) para no
// parpadear el botón deshabilitado mientras carga; el backend igual lo exige.
const puedeValidarCosteo = ref(true);
// Estado de aprobación de cada documento abierto en esta pantalla, por nombre
// (lo emite FranjaAprobacion). Decide si se ofrece "Validar" o si los botones
// viven en la franja (Enviar / Revisar / Aprobar / Regresar).
const aprobPanel = reactive({});
const permisosAprob = usePermisosAprobacion();
function validaDirecto(name) { return puedeValidarDirecto(aprobPanel[name]); }
function enAprobacion(name) { return ["Pendiente", "Revisado"].includes(aprobPanel[name]?.estado); }
async function guardarCosteoParaAprobacion() {
  if (!validate()) throw new Error("Completa lo obligatorio del costeo antes de enviarlo.");
  if (!(await saveDoc())) throw new Error("No se pudo guardar el costeo.");
}
async function trasAprobacionCosteo() { await loadCosteoData(); }
async function trasAprobacionVenta() { await loadRelated(); previewKey.value++; }
async function trasAprobacionDocCompra() { await loadLotesProduccion(); await irPasoProveedor(panelProv.tab); }
async function trasAprobacionSub() { if (subPo.value) await selectSub(subPo.value.name); await loadLotesProduccion(); }
async function trasAprobacionPinv() { if (pinvDoc.value) await loadPinv(pinvDoc.value.name); await loadCompras(); }

async function loadPuedeValidarCosteo() {
  try { puedeValidarCosteo.value = !!(await call("costeo_yelke.api.costeo_api.puede_validar_costeo")).puede; }
  catch { /* si falla, se deja en true -- el backend igual bloquea si no toca */ }
}
const productos = ref([]);
const detalles = ref([]);
const etapas = ref([]);
// Reparto de un material entre varias etapas, con cantidad explícita por etapa
// (ej. 4 de cinta reflejante = 2 en la manga + 2 en el frente). Lista PLANA
// hermana de 'detalles' (igual que 'tallas'), relacionada por material_id +
// stage_id, espejo de Costeo.tabla_materiales_etapa (patch v0_2_19).
const materialesEtapa = ref([]);
const tallas = ref([]);
const allSuppliers = ref([]);
const allTallas = ref([]);
// Cada producto se abre/cierra de forma independiente -- a diferencia del
// acordeón de Cotizaciones (expandedQuotName, un solo panel de edición
// compartido), aquí cada renglón ya trae sus propios datos siempre cargados
// (detalles/etapas/tallas se filtran por finished_item), así que no hay
// ningún estado compartido que obligue a mantener solo uno abierto a la vez.
const expandedTids = reactive(new Set());
const { toast, showToast } = useToast();
const {
  printFmtMap, previewKey,
  pdfModal, sendChooser, waModal, sendModal, assignModal,
  ensurePrintFmt, printUrl, printDocView, downloadPdf, downloadPdfFmt,
  openPdf, openSend, chooseEmail, chooseWhatsApp, sendWhatsAppGeneric, doSend,
  openAssign, doAssign,
} = useDocumentActions(showToast);
const {
  OM_CAB, OM_DAMA, DOC_COMPRA,
  planDetail, planWh, hasPlan, planValidated, downstream,
  loadPlan, obtenerMateriasPrimas, guardarPlan, validarPlan, crearOrdenesTrabajo,
  mrDetail, mrItems, mrSchedule, mrResults, mrDocTab, mrValidated,
  docCompra, docCompraItems, docCompraForm, docCompraValidated, ocSelected,
  mrLotes, addMrLote, removeMrLote, repartirMrLotesIgual, mrLotePendiente,
  mrLotesPreview, actualizarPreviewLotes, mrLoteProductoExcedido, mrLoteProductoIncompleto, mrLotesInvalidos,
  tallasDe: tallasDeLote, tieneTallas, hayTallasEnLotes, sincronizarPiezasDeTallas,
  mrLoteTallaPendiente, mrLoteTallaDescuadrada, mrLoteTallasDescuadradas,
  mrLoteMargenTotal, mrLoteTotalDeProducto, mrLoteTotalFueraDeMargen,
  loadSolicitud, crearSolicitud, guardarSolicitud, validarSolicitud,
  selectOC, selectOcLote, selectRfq, selectSq, guardarDocCompra, validarDocCompra, revisarDocCompra, jalarPreciosOC,
  permisosValidacion, loadPermisosValidacion,
  reciboPr, reciboItems, reciboForm,
  selectReciboLote, nuevoReciboLote, loadRecibo, guardarRecibo, validarRecibo,
  subOcs, subPo, subItems, subForm, subValidated,
  loadSubcontratos, crearSubcontratos, selectSub, loadSub, guardarSub, validarSub, revisarSub,
  flujo, scoActivo, scoSel, scoValidated, materialesSco, piezasSco, serviciosSco, importeSco, scoForm, scoCostos, selectSco,
  guardarSco, validarSco, addCosto, removeCosto,
  transDoc, transForm, transCostos, transValidated, transferDone, transferirMaterial, guardarTrans, validarTransferencia,
  talleresSaldo, devolverMaterialTaller,
  addCostoTrans, removeCostoTrans,
  scr, scrForm, scrCostos, scrValidated, crearReciboSub, loadScr, guardarScr, validarScr,
  addCostoScr, removeCostoScr,
  lotesProduccion, productosCosteo, loteActivoRef, loteParadaActiva, nuevoLoteForm,
  loteActivo, paradaActiva, tracksLote, paradaEstado,
  loadLotesProduccion, seleccionarLote, seleccionarParada, verParadaPo,
  abrirNuevoLote, cerrarNuevoLote, crearNuevoLote, abrirParada, siguienteParadaPendiente, generarOcLote, neteoOc,
  siguienteLoteRef,
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
  medidasTemplates, addTablaPlantilla, tablasDePlantilla, omDeOc, loadOm,
  tallaTotal, onOmFile, removeArchivo,
  prodComplete, loadProdComplete, materiaPrimaPct, subcontratacionPct, mpLotes,
} = useProduccion({ showToast, advancing, ensurePrintFmt, previewKey });

// ═══════════════════════════════════════════════════════════════════════════════
// PRODUCCIÓN v2 · armazón (docs/plan-ui-produccion.md §4)
//
// El paso 5 dejó de ser una pantalla larga y pasó a ser una app con menú: una
// vista por trabajo (Tablero, Preparación, Orden de manufactura, cada Lote con
// sus 4 pasos, y las bandejas de Envíos y Facturas). Lo que cambia es DÓNDE vive
// cada bloque; las funciones que hacen el trabajo son exactamente las mismas.
// ═══════════════════════════════════════════════════════════════════════════════
const prodRuta = useProduccionRuta(route, router, { costeo: docName, sales_order: activeSOName });

/** ¿Este usuario puede abrir esa vista? El backend es la autoridad; esto solo
 *  evita mostrar lo que de todos modos va a rebotar (ver roles.vistas_produccion). */
function puedeVer(clave) {
  const v = permisosValidacion.vistas;
  return !Array.isArray(v) || v.includes(clave);
}
// El paso "Talleres" acepta cualquiera de los dos roles: la matriz (encargar piezas)
// es de Flujo y el detalle de cada taller es de Talleres. "flujo" ya no es un paso.
// Envíos (almacén) también entra a Materia prima y a Talleres: ahí recibe el material
// y hace el envío y el recibo de cada taller. Lo que puede CAPTURAR en cada parte lo
// decide PASOS_LOTE_EDITA (y el panel de cada proveedor, panelProvSoloLectura).
const PASOS_LOTE_VISTA = { materia: ["materia", "envios"], talleres: ["flujo", "talleres", "envios"], entrega: "entrega" };
const PASOS_LOTE_EDITA = { materia: ["materia"], talleres: ["flujo", "talleres"], entrega: "entrega" };
const CLAVES_PASO_LOTE = ["materia", "talleres", "entrega"];
/** ¿Puede ver ese paso del lote? Un paso con dos roles basta con tener uno. */
const puedeVerPasoLote = (clave) => [].concat(PASOS_LOTE_VISTA[clave] || []).some(puedeVer);
/** Primera vista que el usuario SÍ puede abrir -- a dónde mandarlo si pide una prohibida. */
const primeraVistaPermitida = computed(() =>
  ["tablero", "preparacion", "ordenes", "lote", "envios", "facturas"].find(vistaPermitida) || "");

/** ¿La vista que pide la URL está permitida para este usuario? */
function vistaPermitida(v) {
  if (!v) return false;
  if (v === "lote") return CLAVES_PASO_LOTE.some(puedeVerPasoLote);
  // Preparación incluye la ficha de manufactura (paso 3): basta con cualquiera de
  // los dos roles para entrar; los pasos que no toquen salen con candado.
  if (v === "preparacion") return puedeVer("preparacion") || puedeVer("om");
  if (v === "ordenes") return puedeVer("preparacion");
  return puedeVer(v);
}
/** La vista que se está viendo. Sin `?vista=` cae en la primera permitida; si la
 *  URL pide una prohibida se marca como "sin-acceso" para explicarlo (§6.3). */
const pVista = computed(() => {
  const v = prodRuta.vista.value;
  if (!v) return primeraVistaPermitida.value;
  // Compatibilidad: ?vista=om era la ficha de manufactura, que ahora es el paso 3
  // de Preparación. Un enlace viejo sigue llevando al mismo sitio.
  if (v === "om") return vistaPermitida("preparacion") ? "preparacion" : "sin-acceso";
  return vistaPermitida(v) ? v : "sin-acceso";
});
/** El rol que le falta para la vista que pidió -- se le dice cuál es. */
const ETIQUETA_VISTA = {
  tablero: "Tablero", preparacion: "Preparación", ordenes: "Órdenes a talleres",
  om: "Orden de manufactura", lote: "los lotes", envios: "Envíos", facturas: "Facturas",
  materia: "Materia prima", flujo: "Flujo", talleres: "Talleres", entrega: "Entrega",   // flujo: solo como nombre de rol
};
const ROL_DE_VISTA = {
  tablero: "Producción Tablero Yelke", preparacion: "Producción Preparación Yelke",
  ordenes: "Producción Preparación Yelke",
  om: "Producción Orden de Manufactura Yelke", materia: "Producción Materia Prima Yelke",
  flujo: "Producción Flujo Yelke", talleres: "Producción Talleres Yelke",
  envios: "Producción Envíos Yelke", facturas: "Producción Facturas Yelke",
  entrega: "Producción Entrega Yelke",
};
const sinAcceso = computed(() => {
  const v = prodRuta.vista.value;
  return {
    vista: ETIQUETA_VISTA[v] || v,
    rol: ROL_DE_VISTA[v] || "",
    destino: ETIQUETA_VISTA[primeraVistaPermitida.value] || "",
  };
});

/** Pasos del lote que este usuario puede abrir, en orden. */
const pasosLotePermitidos = computed(() => CLAVES_PASO_LOTE.filter(puedeVerPasoLote));

// ── Estado de cada paso del lote (§5.4) ───────────────────────────────────────
// materia: todas las OC del lote con recibo validado
// talleres: todas las paradas recibidas (índigo si además todo está facturado)
// talleres: todas las paradas recibidas (índigo si además todo está facturado)
// entrega: ya no queda nada por remisionar y sí se produjo algo
function estadoPasosLote(lote) {
  if (!lote) return {};
  const pos = lote.material_pos || [];
  const paradas = lote.paradas || [];
  const materia = pos.length > 0 && pos.every((p) => p.receipt_validated);
  const talleresOk = paradas.length > 0 && paradas.every((p) => p.receipt_validated);
  const talleresFac = talleresOk && paradas.every((p) => Number(p.maquila_pendiente || 0) <= 0);
  // Entregado = todo en remisión Y validadas: una remisión en borrador todavía no salió.
  const entrega = (lote.entrega?.producido || 0) > 0 && (lote.entrega?.pendiente || 0) === 0
    && (lote.entrega?.remisiones || []).every((r) => r.docstatus === 1);
  return {
    materia: materia ? "hecho" : "",
    talleres: talleresFac ? "facturado" : talleresOk ? "hecho" : "",
    entrega: entrega ? "hecho" : "",
  };
}
/** Por qué Entrega sigue cerrada: los talleres que todavía no entregaron. Vacío
 *  cuando ya se puede entrar. Un lote SIN talleres no espera a nadie, así que
 *  tampoco se bloquea (nada que producir fuera de casa). */
const faltaParaEntrega = computed(() => {
  const paradas = loteActivo.value?.paradas || [];
  if (!paradas.length) return "";
  const pend = paradas.filter((p) => !p.receipt_validated);
  if (!pend.length) return "";
  return pend.length === 1
    ? `Falta que ${pend[0].supplier} entregue ${pend[0].titulo}.`
    : `Faltan ${pend.length} talleres por entregar.`;
});
/** Motivo por el que un paso del lote no se puede abrir todavía (vacío = se puede).
 *  Entrega es el único con prerrequisito: sin las prendas de vuelta no hay nada que
 *  registrar, y el almacén rebota la remisión de todos modos. */
function bloqueoPasoLote(clave) {
  return clave === "entrega" ? faltaParaEntrega.value : "";
}
/** El primer paso NO terminado: es el "actual" (naranja) y donde se abre el lote. */
function pasoActualDeLote(lote) {
  const est = estadoPasosLote(lote);
  const permitidos = pasosLotePermitidos.value;
  return permitidos.find((k) => !est[k]) || permitidos[permitidos.length - 1] || "materia";
}
const ETIQUETA_PASO_LOTE = { materia: "Materia prima", talleres: "Talleres", entrega: "Entrega" };

/** El paso del lote que se está viendo (de la URL, o el actual). */
const pPasoLote = computed(() => {
  const p = prodRuta.pasoLote.value;
  if (p && puedeVerPasoLote(p) && !bloqueoPasoLote(p)) return p;
  return pasoActualDeLote(loteActivo.value);
});

const pPasosLote = computed(() => {
  const est = estadoPasosLote(loteActivo.value);
  const actual = pasoActualDeLote(loteActivo.value);
  return CLAVES_PASO_LOTE.map((clave) => {
    const permitido = puedeVerPasoLote(clave);
    const motivo = !permitido
      ? `Necesitas el rol de ${ETIQUETA_PASO_LOTE[clave]} para abrir este paso.`
      : bloqueoPasoLote(clave);
    return {
      clave, texto: ETIQUETA_PASO_LOTE[clave],
      estado: est[clave] || (clave === actual ? "actual" : "espera"),
      bloqueado: !!motivo, candado: !permitido, motivo,
    };
  });
});

// ── Navegación ────────────────────────────────────────────────────────────────
async function irProduccion({ vista, lote, paso, parada, tpaso, seg, filtro_lote } = {}) {
  activeStep.value = 5;
  if (vista === "lote" && lote) {
    const obj = lotesProduccion.value.find((l) => l.lote_ref === lote);
    // Al abrir un lote se cae en su paso ACTUAL (el primero no terminado), salvo
    // que el enlace pida uno en concreto.
    prodRuta.irLote(lote, paso || pasoActualDeLote(obj), { parada: parada || null, tpaso: tpaso || null });
    await seleccionarLote(lote);
    return;
  }
  if (vista) {
    loteActivoRef.value = "";
    prodRuta.irVista(vista, { seg: seg || null, filtro_lote: filtro_lote || null });
  }
}
/** A donde se entrega: el primer lote con prendas por remisionar (ahí se crea su
 *  remisión) y, si no hay ninguno, la bandeja de Envíos con sus remisiones. Sustituye
 *  al salto al paso 6, que ya no existe. */
async function irAEntregar() {
  const l = lotesProduccion.value.find((x) => Number(x.entrega?.pendiente || 0) > 0);
  if (l) { await irProduccion({ vista: "lote", lote: l.lote_ref, paso: "entrega" }); return; }
  await irProduccion({ vista: "envios", seg: "remisiones" });
}

function irPasoLote(paso) {
  if (!puedeVerPasoLote(paso)) return;
  const motivo = bloqueoPasoLote(paso);
  if (motivo) { showToast(motivo, "error"); return; }
  prodRuta.irPasoLote(paso);
}
async function irAParada(parada, tpaso = "") {
  if (!parada) return;
  await seleccionarParada(parada);
  // seleccionarParada deja subStepOpen en el paso que toca (subStepDefaultFor);
  // `tpaso` solo manda cuando el llamador pide uno en concreto (un enlace directo).
  if (tpaso) subStepOpen.value = tpaso;
  prodRuta.irTaller(parada.parada_id, subStepOpen.value || "sco");
}

// ── Datos del menú (§4.2) ─────────────────────────────────────────────────────
/** Cantidades por producto de la OV activa + cuántos lotes: la meta de la tarjeta
 *  de arriba del menú ("2,880 + 175 XXL-3XL · 2 lotes"). Las cantidades salen de las
 *  líneas de la OV, que es justo lo que se está produciendo. */
const resumenOV = computed(() => {
  const so = (related.sales_orders || []).find((x) => x.name === activeSOName.value);
  const cant = (so?.cantidades || []).map((i) => Number(i.qty || 0).toLocaleString("es-MX")).join(" + ");
  const n = lotesProduccion.value.length;
  return [cant, n ? `${n} lote${n === 1 ? "" : "s"}` : "sin lotes"].filter(Boolean).join(" · ");
});
const menuLotes = computed(() => lotesProduccion.value.map((l) => {
  const est = estadoPasosLote(l);
  const actual = pasoActualDeLote(l);
  const entregado = est.entrega === "hecho";
  const todos = CLAVES_PASO_LOTE;
  return {
    lote_ref: l.lote_ref,
    estado: entregado ? "ok" : l.done ? "ok" : "now",
    resumen: entregado ? "entregado" : `${todos.indexOf(actual) + 1} · ${ETIQUETA_PASO_LOTE[actual]}`,
    titulo_largo: (l.productos || []).map((x) => `${x.item_name}: ${x.qty}`).join(" · "),
  };
}));
/** Preparación: plan · solicitud · órdenes a talleres (n/3). */
const prepHechos = computed(() => {
  let n = 0;
  if (planValidated.value) n++;
  if (mrValidated.value) n++;
  if (omCompleta.value) n++;
  return n;
});
const menuPrep = computed(() => ({
  hechos: prepHechos.value,
  estado: prepHechos.value >= 3 ? "ok" : prepHechos.value ? "now" : "wait",
}));
/** Orden de manufactura: cuántas fichas por producto base están capturadas.
 *  Alimenta el paso 3 de Preparación y su punto de estado en el menú. */
const omCapturadas = ref({ capturadas: 0, total: 0 });
function onOmGuardada() {
  if (subPo.value) loadOm(subPo.value.name);
  omCapturadas.value = { ...omCapturadas.value, capturadas: omCapturadas.value.total };
}
/** Órdenes a talleres: cuántas están ya validadas. */
const menuOrdenes = computed(() => {
  const total = subOcs.value.length;
  const validadas = subOcs.value.filter((o) => o.docstatus === 1).length;
  return { validadas, total, estado: !total ? "wait" : validadas >= total ? "ok" : "now" };
});
/** Pendientes de las bandejas, para los conteos naranjas del menú. */
const conteosBandejas = computed(() => {
  let envios = 0;
  for (const l of lotesProduccion.value) {
    // Entradas: OC validada sin recibo validado.
    envios += (l.material_pos || []).filter((p) => p.docstatus === 1 && !p.receipt_validated).length;
    for (const pa of l.paradas || []) {
      // Salidas: encargo validado sin transferencia; regresos: transferido sin recibo.
      for (const e of pa.entregas || []) {
        if (e.sco_docstatus === 1 && !e.transfer_done) envios++;
        else if (e.transfer_done && !e.receipt_validated) envios++;
      }
    }
  }
  const facturas = (compras.materiales || []).filter((m) => !m.invoice || m.invoice.docstatus === 0).length
    + (compras.maquila || []).filter((m) => Number(m.pendiente_facturar || 0) > 0).length
    + (compras.fletes || []).filter((f) => f.docstatus === 0).length;
  return { envios, facturas };
});
const menuProduccion = computed(() => ({
  salesOrders: related.sales_orders || [],
  activeSOName: activeSOName.value || "",
  resumenOV: resumenOV.value,
  lotes: menuLotes.value,
  prep: menuPrep.value,
  ordenes: menuOrdenes.value,
  conteos: conteosBandejas.value,
}));

// Compartido con los componentes de vista (los que se vayan extrayendo): el objeto
// de useProduccion más las funciones de página. Un solo origen de estado -- ver el
// riesgo de los watchers en §10 del plan.
provide("produccion", {
  puedeVer, irProduccion, irPasoLote, irAParada,
  estadoPasosLote, pasoActualDeLote, ETIQUETA_PASO_LOTE,
});

// ── Encabezado y stepper de cada vista (§4.2) ─────────────────────────────────
// La ficha de manufactura se captura ANTES de mandar las órdenes, para que cada
// taller la reciba ya heredada (om_de_oc la arma al momento desde la general).
const ETIQUETA_PREP = { 1: "Plan", 2: "Materia prima", 3: "Orden de manufactura" };
/** El rol que manda en cada paso de Preparación -- el 3 es de la vista "om". */
const VISTA_DE_PREP = { 1: "preparacion", 2: "preparacion", 3: "om" };
/** Vistas del catálogo que cubren lo que se está viendo en Producción. */
function clavesVistaActual() {
  const v = pVista.value;
  if (v === "lote") {
    const paso = prodRuta.pasoLote.value;
    // Envío de material y recibo del taller: también de Envíos (como en el servidor).
    if (paso === "talleres" && paradaActiva.value && ["transfer", "recibo"].includes(subStepOpen.value)) return ["talleres", "envios"];
    return [].concat(PASOS_LOTE_EDITA[paso] || []);
  }
  if (v === "preparacion") return [VISTA_DE_PREP[Number(prodRuta.prepPaso.value)] || "preparacion"];
  if (v === "ordenes") return ["preparacion"];
  return [v];
}
/** Texto de solo lectura de la vista actual de Producción; vacío si se puede capturar. */
const pSoloLectura = computed(() => {
  if (!accesosListos.value || pVista.value === "sin-acceso") return "";
  const cs = clavesVistaActual().filter(Boolean);
  if (!cs.length || cs.some((c) => puedeEditar(c))) return "";
  return "Solo lectura";
});
/** ¿Están capturadas todas las fichas de manufactura del costeo? */
const omCompleta = computed(() =>
  omCapturadas.value.total > 0 && omCapturadas.value.capturadas >= omCapturadas.value.total);
/** Paso de Preparación que se está viendo: el de la URL, o el primero pendiente. */
const pPrepPaso = computed(() => {
  if (prodRuta.vista.value === "om") return 3;   // enlace viejo a la ficha
  const p = prodRuta.prepPaso.value;
  if (p >= 1 && p <= 3) return p;
  // Sin paso en la URL: el primero pendiente que este usuario SÍ pueda abrir --
  // quien solo tiene el rol de la ficha entra directo al paso 3.
  const pendiente = !planValidated.value ? 1 : !mrValidated.value ? 2 : 3;
  if (puedeVer(VISTA_DE_PREP[pendiente])) return pendiente;
  return [1, 2, 3].find((i) => puedeVer(VISTA_DE_PREP[i])) || pendiente;
});
const pPasosPrep = computed(() => {
  const hecho = [false, planValidated.value, mrValidated.value, omCompleta.value];
  const actual = [1, 2, 3].find((i) => !hecho[i]) || 0;
  return [1, 2, 3].map((i) => {
    const permitido = puedeVer(VISTA_DE_PREP[i]);
    return {
      clave: String(i), texto: ETIQUETA_PREP[i],
      estado: hecho[i] ? "hecho" : i === actual ? "actual" : "espera",
      bloqueado: !permitido, candado: !permitido,
      motivo: permitido ? "" : `Necesitas el rol de ${ETIQUETA_PREP[i]} para abrir este paso.`,
    };
  });
});

const pEncabezado = computed(() => {
  switch (pVista.value) {
    case "tablero":
      return { eyebrow: "Producción", titulo: "Tablero",
               ayuda: "Todo lo de esta orden de venta. Abajo a la derecha está siempre lo siguiente que conviene hacer." };
    case "preparacion":
      return { eyebrow: "Producción · Preparar", titulo: "Preparación",
               ayuda: pPrepPaso.value === 3
                 ? "Una ficha por producto. La info general y las tallas van a todos los talleres; lo demás, solo a los que marques en “Para”."
                 : "Una vez por orden de venta: plan, materia prima y ficha de manufactura. Después se mandan las órdenes a los talleres." };
    case "ordenes":
      return { eyebrow: "Producción · Preparar", titulo: "Órdenes a talleres",
               ayuda: "Una por taller, con su servicio y precio por prenda. Cada una lleva la ficha de manufactura que le toca a ese taller." };
    case "lote":
      // Dentro de un taller manda su propio encabezado (plan §5.7): el del lote
      // ya se ve en el menú y se vuelve con "← Talleres".
      if (pTallerAbierto.value) {
        const pa = paradaActiva.value;
        const i = (loteActivo.value?.paradas || []).findIndex((x) => x.parada_id === pa.parada_id);
        const n = (loteActivo.value?.paradas || []).length;
        return {
          eyebrow: `${loteActivoRef.value} · Talleres · ${i + 1} de ${n}`,
          titulo: `${pa.titulo} · ${pa.supplier}`,
          meta: metaTallerDetalle(pa),
        };
      }
      return loteActivo.value
        ? { eyebrow: "Producción · Lotes", titulo: loteActivoRef.value,
            meta: [loteActivo.value.schedule_date ? loteActivo.value.schedule_date.slice(0, 10) : "",
                   (loteActivo.value.productos || []).map((x) => `${x.item_name} ${Number(x.qty).toLocaleString("es-MX")}`).join(" · ")]
              .filter(Boolean).join(" · "),
            ayuda: ayudaPasoLote(pPasoLote.value) }
        : { eyebrow: "Producción · Lotes", titulo: "Lotes" };
    case "envios":
      return { eyebrow: "Producción · Bandeja", titulo: "Envíos",
               ayuda: "Todo lo que entra y sale: material, talleres, devoluciones y remisiones." };
    case "facturas":
      return { eyebrow: "Producción · Bandeja", titulo: "Facturas",
               ayuda: "Todas las de la operación: material, maquila, fletes y la venta al cliente." };
    case "sin-acceso":
      return { eyebrow: "Producción", titulo: "Sin acceso" };
    default:
      return { eyebrow: "Producción", titulo: "Producción" };
  }
});
const AYUDA_PASO_LOTE = {
  materia: "Compra lo de este lote. Cada proveedor avanza igual: orden de compra → recibo → factura.",
  talleres: "Toca las piezas por encargar y crea sus órdenes; toca una pieza ya encargada para enviarle material al taller, recibir y facturar.",
  entrega: "Lo que este lote ya produjo y lo que falta remisionar.",
};
/** Un costeo SIN piezas declaradas no tiene matriz: se ve un carril por producto,
 *  así que el texto de ayuda del paso Flujo no puede hablar de columnas ni piezas. */
const loteTienePiezas = computed(() => !!(loteActivo.value?.ramas || []).length);
function ayudaPasoLote(paso) {
  if (paso === "talleres" && pTallerAbierto.value) {
    return "Encargo → envío de material → recibo → factura. Arriba, las piezas que lleva este taller.";
  }
  if (paso === "talleres" && !loteTienePiezas.value) {
    return "El recorrido de cada producto por sus talleres. Clic en una tarjeta para abrir ese taller.";
  }
  return AYUDA_PASO_LOTE[paso] || "";
}

/** El stepper del encabezado: el del lote, el de la preparación, o ninguno. */
const pPasos = computed(() => {
  if (pVista.value === "lote" && pTallerAbierto.value) return pPasosTaller.value;
  if (pVista.value === "lote" && loteActivo.value) return pPasosLote.value;
  if (pVista.value === "preparacion") return pPasosPrep.value;
  return [];
});
const pPasoSel = computed(() =>
  pVista.value === "lote"
    ? (pTallerAbierto.value ? subStepOpen.value : pPasoLote.value)
    : pVista.value === "preparacion" ? String(pPrepPaso.value) : "");

function onIrPaso(clave) {
  if (pVista.value === "lote" && pTallerAbierto.value) irPasoTaller(clave);
  else if (pVista.value === "lote") irPasoLote(clave);
  else if (pVista.value === "preparacion") prodRuta.set({ prep: clave });
}

// ── Filtro de producto del lote (§4.7) ────────────────────────────────────────
const filtroProducto = computed({
  get: () => prodRuta.producto.value || "__todos",
  set: (v) => prodRuta.set({ producto: v === "__todos" ? null : v }),
});
const filtroProductoOpciones = computed(() => {
  const prods = (loteActivo.value?.productos || []).filter((x) => Number(x.qty) > 0);
  if (prods.length < 2) return [];
  return [{ valor: "__todos", texto: "Todos" },
          ...prods.map((x) => ({ valor: x.finished_item, texto: x.item_name || x.finished_item }))];
});

// ── Tablero (§5.1) ────────────────────────────────────────────────────────────
function pasosDeLoteParaLista(lote) {
  const est = estadoPasosLote(lote);
  const actual = pasoActualDeLote(lote);
  return CLAVES_PASO_LOTE.map((clave) => ({
    clave, texto: ETIQUETA_PASO_LOTE[clave],
    estado: est[clave] || (clave === actual ? "actual" : "espera"),
  }));
}
function pillLote(lote) {
  const est = estadoPasosLote(lote);
  if (est.entrega === "hecho") return { estado: "ok", texto: "Entregado" };
  const actual = pasoActualDeLote(lote);
  return { estado: "now", texto: ETIQUETA_PASO_LOTE[actual] };
}

/** "Por hacer": hasta 8 pendientes, cada uno con su destino exacto (§5.1). */
const porHacer = computed(() => {
  const out = [];
  const nf = (n) => Number(n || 0).toLocaleString("es-MX");
  for (const l of lotesProduccion.value) {
    const provs = proveedoresLote(l);
    const sinOc = provs.filter((g) => !g.po);
    if (sinOc.length) {
      out.push({ estado: "now", titulo: `Generar las órdenes de compra del ${l.lote_ref}`,
        meta: `${sinOc.length} proveedor(es) · ${sinOc.map((g) => g.supplier).slice(0, 3).join(", ")}`,
        donde: `${l.lote_ref} · Materia prima`, ir: () => irProduccion({ vista: "lote", lote: l.lote_ref, paso: "materia" }) });
    }
    const porRecibir = (l.material_pos || []).filter((po) => po.docstatus === 1 && !po.receipt_validated);
    if (porRecibir.length) {
      out.push({ estado: "wait", titulo: `Recibir material del ${l.lote_ref}`,
        meta: `${porRecibir.length} orden(es) de compra validada(s) sin recibo`,
        donde: `${l.lote_ref} · Materia prima`, ir: () => irProduccion({ vista: "lote", lote: l.lote_ref, paso: "materia" }) });
    }
    for (const pa of l.paradas || []) {
      const sinEnviar = (pa.entregas || []).filter((e) => e.sco_docstatus === 1 && !e.transfer_done);
      if (sinEnviar.length) {
        out.push({ estado: "bad", titulo: `Enviar material · ${pa.titulo} · ${pa.supplier}`,
          meta: `${l.lote_ref} · ${sinEnviar.length} encargo(s) por enviar`,
          donde: `${l.lote_ref} · Talleres`, ir: () => irProduccion({ vista: "lote", lote: l.lote_ref, paso: "talleres", parada: pa.parada_id, tpaso: "transfer" }) });
      }
      const sinRecibir = (pa.entregas || []).filter((e) => e.transfer_done && !e.receipt_validated);
      if (sinRecibir.length) {
        out.push({ estado: "wait", titulo: `Recibir trabajo de ${pa.supplier}`,
          meta: `${l.lote_ref} · ${pa.titulo}`,
          donde: `${l.lote_ref} · Talleres`, ir: () => irProduccion({ vista: "lote", lote: l.lote_ref, paso: "talleres", parada: pa.parada_id, tpaso: "recibo" }) });
      }
    }
    if (l.entrega?.lista) {
      out.push({ estado: "ok", titulo: `Crear la remisión del ${l.lote_ref}`,
        meta: `${nf(l.entrega.pendiente)} prendas terminadas por entregar`,
        donde: `${l.lote_ref} · Entrega`, ir: () => irProduccion({ vista: "lote", lote: l.lote_ref, paso: "entrega" }) });
    }
  }
  const borradores = (compras.materiales || []).filter((m) => m.invoice && m.invoice.docstatus === 0);
  if (borradores.length) {
    out.push({ estado: "wait", titulo: `Validar ${borradores.length} factura(s) de material en borrador`,
      meta: `${fmtC(borradores.reduce((a, m) => a + Number(m.base_net_total || 0), 0))} subtotal`,
      donde: "Facturas", ir: () => irProduccion({ vista: "facturas" }) });
  }
  const maqPend = (compras.maquila || []).filter((m) => Number(m.pendiente_facturar || 0) > 0);
  if (maqPend.length) {
    out.push({ estado: "wait", titulo: `Facturar la maquila recibida de ${maqPend.length} taller(es)`,
      meta: `${fmtC(maqPend.reduce((a, m) => a + Number(m.pendiente_facturar || 0), 0))} por facturar`,
      donde: "Facturas", ir: () => irProduccion({ vista: "facturas" }) });
  }
  if (talleresSaldo.value.length) {
    out.push({ estado: "off", titulo: `Material sobrante en ${talleresSaldo.value.length} taller(es)`,
      meta: "Se descuenta solo en la siguiente transferencia; al terminar, registra la devolución",
      donde: "Envíos", ir: () => irProduccion({ vista: "envios", seg: "sobrantes" }) });
  }
  return out.slice(0, 8);
});

// ── Bandejas (Envíos y Facturas) ─────────────────────────────────────────────
// Cada bandeja es UNA lista con TODOS los documentos de la operación; lo único que
// se filtra es el lote (por defecto el primero). El tipo de documento va como
// etiqueta en cada renglón, y lo pendiente sale arriba.
const bandejaLote = computed({
  get: () => {
    const f = prodRuta.filtroLote.value;
    if (f === "__todos" || lotesProduccion.value.some((l) => l.lote_ref === f)) return f;
    return lotesProduccion.value[0]?.lote_ref || "__todos";
  },
  set: (v) => prodRuta.set({ filtro_lote: v }),
});
const filtroLoteOpciones = computed(() => [
  ...lotesProduccion.value.map((l) => ({ valor: l.lote_ref, texto: l.lote_ref })),
  { valor: "__todos", texto: "Todos los lotes" },
]);
// Segundo filtro, opcional: el tipo de documento (sin filtro por defecto). Vive en la
// URL (`seg`) como el lote; un valor que no aplique a la bandeja abierta = todos.
const bandejaTipo = computed({
  get: () => {
    const t = prodRuta.seg.value === "remisiones" ? "remision" : prodRuta.seg.value;
    return t && (pVista.value === "facturas" ? TIPO_FAC : TIPO_MOV)[t] ? t : "__todos";
  },
  set: (v) => prodRuta.set({ seg: v === "__todos" ? null : v }),
});
/** Opciones de tipo: solo los que hay en el lote elegido, con su conteo. */
function opcionesTipo(filas, nombres) {
  const n = {};
  for (const f of filas) n[f.tipo] = (n[f.tipo] || 0) + 1;
  return [{ valor: "__todos", texto: "Todos", conteo: filas.length },
    ...Object.keys(nombres).filter((t) => n[t]).map((t) => ({ valor: t, texto: nombres[t], conteo: n[t] }))];
}
// Un documento sin lote (remisión o factura de toda la OV) se ve en cualquier lote.
const enLote = (...lotes) => bandejaLote.value === "__todos" || !lotes.some(Boolean) || lotes.includes(bandejaLote.value);
const etiquetaLote = (lote) => (bandejaLote.value === "__todos" ? (lote || "Toda la OV") : (lote ? "" : "Toda la OV"));
const juntar = (...xs) => xs.filter(Boolean).join(" · ");
// Pendientes arriba; luego lo más reciente.
const ordenBandeja = (a, b) => (b.pendiente - a.pendiente) || String(b.fecha || "").localeCompare(String(a.fecha || ""));

// Movimientos físicos ya capturados (recibos, envíos, recibos del taller,
// devoluciones), en borrador o validados -- antes solo se veía lo pendiente.
const movimientos = ref([]);
async function loadMovimientos() {
  if (!docName.value) return;
  try {
    movimientos.value = await call("costeo_yelke.api.costeo_api.get_movimientos_produccion", {
      costeo: docName.value, sales_order: activeSOName.value || null,
    }) || [];
  } catch { /* sin permiso: la bandeja se queda con lo pendiente */ }
}
// Cada acción de producción recarga los lotes: con eso se refrescan los movimientos.
watch(lotesProduccion, () => { if (activeStep.value === 5) loadMovimientos(); });

/** Dónde se abre lo de un encargo: la parada del taller que lo tiene. */
function irAEncargo(lote, sco) {
  for (const l of lotesProduccion.value) {
    for (const pa of l.paradas || []) {
      if ((pa.entregas || []).some((e) => e.sco === sco)) {
        return irProduccion({ vista: "lote", lote: l.lote_ref, paso: "talleres", parada: pa.parada_id });
      }
    }
  }
  return irProduccion({ vista: "lote", lote, paso: "talleres" });
}

const TIPO_MOV = {
  entrada: "Entrada de material", envio: "Envío a taller", recibo_taller: "Recibo del taller",
  devolucion: "Devolución de taller", devolucion_proveedor: "Devolución a proveedor", remision: "Remisión",
};
const envFilasLote = computed(() => {
  const filas = [];
  // Lo que todavía no tiene documento: OC por recibir, encargos por enviar y lo que
  // está en el taller.
  for (const l of lotesProduccion.value) {
    if (!enLote(l.lote_ref)) continue;
    for (const po of l.material_pos || []) {
      if (po.docstatus !== 1 || po.receipt_validated) continue;
      filas.push({ tipo: "entrada", estado: "wait", pendiente: 1, fecha: "",
        titulo: po.supplier_name || po.supplier,
        meta: juntar(etiquetaLote(l.lote_ref), `OC ${po.name}`, po.recibido_parcial ? `faltan ${fmtCantidad(po.pendiente_recibir)}` : "aún no llega"),
        pill: { estado: "off", texto: po.recibido_parcial ? "Parcial" : "Por recibir" },
        ir: () => irProduccion({ vista: "lote", lote: l.lote_ref, paso: "materia" }) });
    }
    for (const pa of l.paradas || []) {
      for (const e of pa.entregas || []) {
        const ir = () => irProduccion({ vista: "lote", lote: l.lote_ref, paso: "talleres", parada: pa.parada_id });
        if (e.sco_docstatus === 1 && !e.transfer_done) {
          filas.push({ tipo: "envio", estado: "bad", pendiente: 1, fecha: "", titulo: `${pa.supplier} · ${pa.titulo}`,
            meta: juntar(etiquetaLote(l.lote_ref), `${Number(e.cantidad).toLocaleString("es-MX")} prendas`, "falta mandarle el material"),
            pill: { estado: "now", texto: "Por enviar" }, ir });
        } else if (e.transfer_done && !e.receipt_validated) {
          filas.push({ tipo: "recibo_taller", estado: "wait", pendiente: 1, fecha: "", titulo: `${pa.supplier} · ${pa.titulo}`,
            meta: juntar(etiquetaLote(l.lote_ref), e.recibido_parcial ? `faltan ${fmtCantidad(e.pendiente_recibir)}` : "trabajando en el taller"),
            pill: { estado: "off", texto: e.recibido_parcial ? "Parcial" : "Por recibir" }, ir });
        }
      }
    }
  }
  // Todos los documentos ya capturados.
  for (const m of movimientos.value) {
    if (!enLote(m.lote_ref)) continue;
    const borr = m.docstatus === 0;
    filas.push({ tipo: m.tipo, estado: borr ? "wait" : "ok", pendiente: borr ? 1 : 0, fecha: m.fecha,
      titulo: m.tercero, meta: juntar(etiquetaLote(m.lote_ref), m.name, fmtFecha(m.fecha)),
      pill: borr ? { estado: "wait", texto: "Borrador" } : { estado: "ok", texto: "Validado" },
      ir: () => (m.tipo === "entrada" || m.tipo === "devolucion_proveedor"
        ? irProduccion({ vista: "lote", lote: m.lote_ref, paso: "materia" }) : irAEncargo(m.lote_ref, m.referencia)) });
  }
  for (const dn of related.delivery_notes || []) {
    if (!enLote(dn.lote_ref)) continue;
    const borr = dn.docstatus !== 1;
    filas.push({ tipo: "remision", estado: borr ? "wait" : "ok", pendiente: borr ? 1 : 0, fecha: dn.posting_date,
      titulo: dn.customer_name || "Cliente",
      meta: juntar(etiquetaLote(dn.lote_ref), dn.name, dn.shipping_address_name ? `→ ${dn.shipping_address_name}` : "", fmtFecha(dn.posting_date)),
      pill: borr ? { estado: "wait", texto: "Borrador" } : { estado: "ok", texto: "Validada" },
      ir: () => abrirPanelRemision(dn.name, dn.lote_ref ? `${dn.lote_ref} · Remisión` : "Remisión · toda la orden de venta") });
  }
  return filas.sort(ordenBandeja);
});
const envPendientes = computed(() => envFilasLote.value.filter((f) => f.pendiente).length);
const envTipoOpciones = computed(() => opcionesTipo(envFilasLote.value, TIPO_MOV));
const envFilas = computed(() => envFilasLote.value.filter((f) => bandejaTipo.value === "__todos" || f.tipo === bandejaTipo.value));

// ── Facturas ──
// Todas, sin filtrar por lote: abrirFacturaDesde* busca aquí la fila exacta.
const facturasTodas = computed(() => {
  const filas = [];
  // `ir` se asigna DESPUÉS de armar la fila: el panel necesita la fila ya calculada
  // (tipo, nombre, título, meta), no el renglón crudo de `compras` -- pasándole el
  // crudo, el panel abría sin título y sin encontrar la factura, y ofrecía "Crear
  // factura de compra" sobre una que YA existía.
  const conIr = (fila, doctype) => {
    fila.ir = () => abrirFacturaDesdeBandeja(doctype, fila);
    return fila;
  };
  for (const m of compras.materiales || []) {
    const ds = m.invoice?.docstatus;
    // Una fila por orden de compra (puede haber llegado en varias entregas). La
    // factura se registra cuando llegó todo: antes, solo lectura.
    const falta = m.recibido_todo === false && !m.invoice;
    const nRec = (m.recibos || []).length;
    filas.push(conIr({
      tipo: "material", nombre: m.name, lotes: m.lotes?.length ? m.lotes : [m.lote_ref || ""],
      estado: falta ? "wait" : ds === 1 ? "fac" : m.invoice ? "wait" : "off",
      titulo: m.supplier_name || m.supplier,
      meta: juntar(m.invoice?.name, m.purchase_order || `recibo ${m.name}`,
             nRec > 1 ? `${nRec} entregas` : "",
             falta ? `faltan ${fmtCantidad(m.pendiente_recibir)} por recibir` : ""),
      importe: Number(m.base_net_total || 0),
      pill: falta ? { estado: "wait", texto: "Por recibir" }
        : ds === 1 ? { estado: "fac", texto: "Validada" } : m.invoice ? { estado: "wait", texto: "Borrador" } : { estado: "off", texto: "Sin factura" },
      pendiente: ds !== 1 ? 1 : 0,
      bloqueo: falta
        ? `La orden ${m.purchase_order || ""} todavía tiene ${fmtCantidad(m.pendiente_recibir)} por recibir. La factura se registra cuando llegue todo.`
        : "",
    }, "Purchase Receipt"));
  }
  for (const m of compras.maquila || []) {
    const ds = m.invoice?.docstatus;
    const pend = Number(m.pendiente_facturar || 0);
    // La factura de maquila es UNA por orden de compra del taller y cubre TODOS sus
    // lotes, así que no se captura hasta que devolvió todo: con una pieza de vuelta
    // la OC ya muestra el total del servicio (pieza portadora) y se habría facturado
    // un trabajo a medias.
    const falta = !m.recibido_todo;
    filas.push(conIr({
      tipo: "maquila", nombre: m.name, lotes: m.lotes || [],
      estado: falta ? "wait" : ds === 1 && pend <= 0 ? "fac" : m.invoice && ds === 0 ? "wait" : "off",
      titulo: m.supplier_name || m.supplier,
      meta: juntar(m.invoice?.name, m.name, (m.lotes || []).length > 1 ? `cubre ${(m.lotes || []).join(" y ")}` : "",
             falta ? `recibido ${Math.round(Number(m.per_received) || 0)}%` : ""),
      importe: pend > 0 ? pend : Number(m.base_net_total || 0), porFacturar: pend,
      pill: falta ? { estado: "wait", texto: "Por recibir" }
          : pend > 0 ? (m.invoice && ds === 0 ? { estado: "wait", texto: "Borrador" } : { estado: "off", texto: "Sin factura" })
          : { estado: "fac", texto: "Validada" },
      pendiente: falta || pend > 0 || ds === 0 ? 1 : 0,
      // El panel no ofrece crear la factura mientras falte trabajo por recibir.
      bloqueo: falta
        ? `Este taller todavía no devuelve todo lo que se le encargó (${Math.round(Number(m.per_received) || 0)}% recibido). La factura es una sola por su orden de compra y se captura cuando termine.`
        : "",
    }, "Purchase Order"));
  }
  // Facturas de FLETE (proveedor de paquetería): nacen solas en borrador al validar el
  // envío; aquí se captura el folio, se adjuntan el CFDI y la carta porte y se validan.
  const ORIGEN_FLETE = { "Purchase Receipt": "entrada", "Stock Entry": "envío al taller",
    "Subcontracting Receipt": "recibo del taller", "Delivery Note": "remisión" };
  for (const f of compras.fletes || []) {
    filas.push(conIr({
      tipo: "flete", nombre: f.name, lotes: [f.lote_ref || ""], estado: f.docstatus === 1 ? "fac" : "wait",
      titulo: f.supplier_name || f.supplier,
      meta: juntar(f.name, `${ORIGEN_FLETE[f.flete_origen_doctype] || "documento"} ${f.flete_origen || ""}`, f.bill_no ? `folio ${f.bill_no}` : "sin folio"),
      importe: Number(f.base_net_total || 0),
      pill: f.docstatus === 1 ? { estado: "fac", texto: "Validada" } : { estado: "wait", texto: "Por completar" },
      pendiente: f.docstatus !== 1 ? 1 : 0,
    }, "Purchase Invoice"));
  }
  // La factura al cliente (una por orden de venta): se captura en el paso Facturar.
  const si = related.sales_invoice;
  if (si) {
    filas.push({
      tipo: "venta", nombre: si.name, lotes: [""], estado: si.docstatus === 1 ? "fac" : "wait",
      titulo: si.customer_name || "Cliente", meta: juntar(si.name, si.due_date ? `vence ${fmtFecha(si.due_date)}` : ""),
      importe: Number(si.base_net_total ?? si.grand_total ?? 0),
      pill: si.docstatus === 1 ? { estado: "fac", texto: "Validada" } : { estado: "wait", texto: "Borrador" },
      pendiente: si.docstatus !== 1 ? 1 : 0,
      ir: () => goStep(7),
    });
  }
  return filas;
});
const TIPO_FAC = { material: "Material", maquila: "Maquila", flete: "Flete", venta: "Venta al cliente" };
const facturasLote = computed(() => facturasTodas.value
  .filter((f) => enLote(...f.lotes))
  .map((f) => ({ ...f, meta: juntar(etiquetaLote(f.lotes.filter(Boolean).join(" y ")), f.meta) }))
  .sort((a, b) => (b.pendiente - a.pendiente) || (b.importe - a.importe)));
const facTipoOpciones = computed(() => opcionesTipo(facturasLote.value, TIPO_FAC));
const facturasFilas = computed(() => facturasLote.value.filter((f) => bandejaTipo.value === "__todos" || f.tipo === bandejaTipo.value));
// Los totales son del lote completo, no del tipo elegido.
const facturasTotales = computed(() => {
  const compra = facturasLote.value.filter((f) => f.tipo !== "venta");
  const conFactura = (f) => f.pill.texto === "Borrador" || f.pill.texto === "Por completar";
  return {
    porFacturar: compra.filter((f) => f.tipo === "maquila" && f.estado !== "fac" && f.pill.texto !== "Por recibir")
      .reduce((a, f) => a + f.importe, 0),
    borrador: compra.filter(conFactura).reduce((a, f) => a + f.importe, 0),
    nBorrador: compra.filter(conFactura).length,
    validadas: compra.filter((f) => f.estado === "fac").reduce((a, f) => a + f.importe, 0),
  };
});

// ── Panel "Orden a un taller" (Preparación · paso 3) ──────────────────────────
const panelOcTaller = reactive({ abierto: false, titulo: "", meta: "", cargando: false, error: "" });
// Validar la orden a un taller exige la ficha completa: la orden se le manda con ella.
async function validarSubConFicha() {
  if (!omCompleta.value) { showToast("Primero captura la orden de manufactura (Preparación · paso 3).", "error"); return; }
  await validarSub();
}
async function cambiarAltaSat(sinAlta) {
  if (!subPo.value) return;
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.marcar_proveedor_sin_alta_sat", { po: subPo.value.name, sin_alta: sinAlta ? 1 : 0 });
    await loadSub(subPo.value.name);
    await loadSubcontratos();
    showToast(sinAlta ? "Taller sin alta en el SAT: la orden queda sin IVA" : "Taller con alta en el SAT: la orden lleva IVA");
  } catch (e) { showToast(e.message || "No se pudo cambiar el dato fiscal del taller", "error"); }
  finally { advancing.value = false; }
}
async function abrirOcTaller(oc) {
  cerrarPaneles();
  // Igual que en el panel del proveedor: `subPo` es de una orden a la vez, así que
  // se suelta la anterior antes de pedir esta -- si no, mientras carga (o si falla)
  // se veía la orden de OTRO taller.
  subPo.value = null;
  panelOcTaller.titulo = oc.supplier_name || oc.supplier;
  panelOcTaller.meta = `${oc.name} · cubre todos los lotes`;
  panelOcTaller.error = "";
  panelOcTaller.abierto = true;
  panelOcTaller.cargando = true;
  try {
    await Promise.all([selectSub(oc.name), cargarContactoTaller(oc.supplier)]);
  } catch (e) {
    panelOcTaller.error = e.message || "No se pudo abrir la orden.";
  } finally {
    panelOcTaller.cargando = false;
  }
}
/** Contacto principal del taller (se resuelve del proveedor: la OC no lo trae). */
const contactoTaller = reactive({ contacto: null, nombre: "", email: "", telefono: "" });
async function cargarContactoTaller(supplier) {
  Object.assign(contactoTaller, { contacto: null, nombre: "", email: "", telefono: "" });
  if (!supplier) return;
  try {
    Object.assign(contactoTaller, await call(
      "costeo_yelke.api.costeo_api.contacto_principal_proveedor", { supplier }));
  } catch { /* sin contacto: el envío se abre con el correo vacío */ }
}
/** Manda al taller su orden Y su ficha en un solo correo (dos PDF adjuntos). */
// La ficha NO se descarga con el visor de impresión como los demás documentos: pasa
// por su propio endpoint, que le une los PDF adjuntos al final como hojas aparte
// (impresion.descargar_om). El navegador no sabe unir PDF.
function descargarFicha(po) {
  window.open(`/api/method/costeo_yelke.api.impresion.descargar_om?po=${encodeURIComponent(po)}`, "_blank");
}

function enviarOrdenAlTaller() {
  if (!subPo.value) return;
  // Sin correo o sin teléfono no es un error: la ventana de envío dice qué tiene
  // registrado el taller y lo que falte se escribe al enviar.
  openSend("Purchase Order", subPo.value.name, contactoTaller.email, contactoTaller.telefono, {
    printFormats: ["Orden de Maquila", "Orden de Manufactura"],
    asunto: `Orden de maquila ${subPo.value.name} · ${panelOcTaller.titulo}`,
    mensaje: `Estimado ${contactoTaller.nombre || panelOcTaller.titulo}, adjunto la orden de maquila y su ficha de manufactura. Quedamos atentos.`,
    // Enviada: el panel y la lista lo muestran (y el botón pasa a "Reenviar").
    alEnviar: async () => { await loadSub(subPo.value.name); await loadSubcontratos(); },
  });
}

/** Manda la orden de compra (materia prima) al proveedor; al enviarse queda "Enviada". */
async function enviarOcProveedor() {
  const d = docCompra.value;
  if (!d) return;
  await cargarContactoTaller(d.supplier);
  openSend("Purchase Order", d.name, contactoTaller.email || d.contact_email, contactoTaller.telefono || d.contact_mobile, {
    printFormats: ["Orden de Compra Yelke"],
    asunto: `Orden de compra ${d.name} · ${d.supplier_name || d.supplier}`,
    mensaje: `Estimado ${contactoTaller.nombre || d.supplier_name || d.supplier}, adjunto la orden de compra. Quedamos atentos.`,
    alEnviar: async () => { await loadLotesProduccion(); await irPasoProveedor("oc"); },
  });
}

/** Doble validación: Revisar → Validar, con los permisos de cada quien. Enviarla al
 *  taller solo aparece ya validada: un borrador todavía puede cambiar. */
const accionesOcTaller = computed(() => {
  if (!subPo.value) return [];
  if (subValidated.value) {
    return [pri(subPo.value.enviado_el ? "Reenviar al taller" : "Enviar al taller", enviarOrdenAlTaller)];
  }
  const out = [sec("Guardar", guardarSub)];
  // En aprobación, o para quien no puede validarla: los botones van en la franja.
  if (!validaDirecto(subPo.value.name) || enAprobacion(subPo.value.name)) return out;
  if (subPo.value.requiere_doble_validacion && !subPo.value.revisado_yelke) {
    out.push(pri("Revisar", revisarSub, {
      deshabilitado: !permisosValidacion.puede_revisar,
      motivo: "Necesitas el rol 'Revisor de Documentos Yelke' para revisar.",
    }));
  } else {
    out.push(pri("Validar", validarSubConFicha, {
      deshabilitado: !permisosValidacion.puede_aprobar || !omCompleta.value,
      motivo: !omCompleta.value ? "Primero captura la orden de manufactura." : "Necesitas el rol 'Aprobador de Documentos Yelke' para validar.",
    }));
  }
  return out;
});

const accionesOmTaller = computed(() => (puedeEditar("om")
  ? [sec("Editar la ficha", () => { panelOmTaller.abierto = false; activeStep.value = 5; prodRuta.irPreparacion(3); })]
  : []));

/** Abre una factura de la bandeja en el panel lateral. */
const panelFactura = reactive({ abierto: false, titulo: "", eyebrow: "", meta: "", pendiente: 0, bloqueo: "", cargando: false, error: "" });
async function abrirFacturaDesdeBandeja(source_doctype, fila) {
  cerrarPaneles();
  // `pinvDoc` es de una factura a la vez y lo comparten esta bandeja, el panel del
  // proveedor y el paso Factura de cada taller: se suelta antes de pedir la nueva.
  pinvDoc.value = null;
  panelFactura.eyebrow = `Factura de compra · ${{ maquila: "maquila", flete: "flete (paquetería)" }[fila.tipo] || "material"}`;
  panelFactura.titulo = fila.titulo;
  panelFactura.meta = fila.meta;
  panelFactura.pendiente = fila.tipo === "maquila" ? Number(fila.porFacturar) || 0 : 0;
  panelFactura.bloqueo = fila.bloqueo || "";
  panelFactura.error = "";
  panelFactura.abierto = true;
  panelFactura.cargando = true;
  try {
    await abrirFacturaFuente(source_doctype, fila.nombre, fila.titulo);
  } catch (e) {
    panelFactura.error = e.message || "No se pudo abrir la factura.";
  } finally {
    panelFactura.cargando = false;
  }
}
function cerrarPanelFactura() {
  panelFactura.abierto = false;
  panelFactura.cargando = false;
  panelFactura.error = "";
  panelFactura.bloqueo = "";
  pinvDoc.value = null;
}
const accionesPanelFactura = computed(() => {
  if (!puedeEditar("facturas")) return [];
  // Maquila con trabajo sin recibir: solo lectura. Ni crear ni validar -- validar es
  // justo donde se mueve el dinero. Un borrador que ya exista se puede mirar y, si
  // sobra, descartar desde ERPNext.
  if (panelFactura.bloqueo) return [];
  if (!pinvDoc.value) return [pri("Crear factura de compra", crearFacturaInline)];
  if (pinvValidated.value) {
    return panelFactura.pendiente > 0 ? [pri("Registrar factura de lo pendiente", crearFacturaInline)] : [];
  }
  if (!validaDirecto(pinvDoc.value.name) || enAprobacion(pinvDoc.value.name)) return [sec("Guardar", guardarPinv)];
  return [sec("Guardar", guardarPinv), pri("Validar factura", validarFacturaInline)];
});

// ── Panel "Nuevo lote" ────────────────────────────────────────────────────────
// Un solo punto de entrada desde el menú, la primaria de Preparación y el Tablero
// (ver el riesgo en §10 del plan). Si todavía no hay OC de taller, abrirNuevoLote
// las crea y valida; si no pudo, manda a Preparación · paso 3.
async function abrirNuevoLotePanel() {
  cerrarPaneles();
  activeStep.value = 5;
  // Mismo orden que la barra: ficha completa → órdenes a talleres validadas → lote.
  if (!omCompleta.value) {
    showToast("Primero captura la orden de manufactura.", "error");
    prodRuta.irPreparacion(3);
    return;
  }
  if (!subOcs.value.length || subOcs.value.some((o) => o.docstatus === 0)) {
    showToast(subOcs.value.length ? "Primero revisa y valida todas las órdenes a talleres." : "Primero crea las órdenes a talleres.", "error");
    irProduccion({ vista: "ordenes" });
    return;
  }
  await abrirNuevoLote();
  if (!nuevoLoteForm.porProducto.length) {
    cerrarNuevoLote();
    showToast("Primero valida las órdenes a talleres.", "error");
    irProduccion({ vista: "ordenes" });
  }
}
/** Al abrir el costeo en Producción: la vista de la URL manda (enlaces que se
 *  comparten); si no trae nada, la última de este navegador para ESTE costeo y
 *  ESTA orden de venta; si tampoco, el Tablero. */
/** Datos que Producción necesita de entrada: las facturas de compra (Tablero,
 *  conteo del menú y bandeja de Facturas) y cuántas fichas de manufactura están
 *  capturadas. Antes solo se cargaban al abrir el paso 7 / la vista de OM, así que
 *  el Tablero arrancaba sin sus pendientes. */
async function cargarDatosProduccion() {
  await Promise.all([
    loadCompras(),
    loadMovimientos(),
    (async () => {
      if (!docName.value) return;
      try {
        const r = await call("costeo_yelke.api.om_general.get_oms_generales", {
          costeo: docName.value, sales_order: activeSOName.value || null,
        });
        const prods = r.productos || [];
        omCapturadas.value = { total: prods.length, capturadas: prods.filter((x) => x.om).length };
      } catch { /* sin permiso de OM: el menú se queda en 0 */ }
    })(),
  ]);
}

async function restaurarVistaProduccion() {
  cargarDatosProduccion();
  let d = prodRuta.vista.value ? null : prodRuta.recordado();
  if (d && d.vista) prodRuta.set(d);
  else d = null;
  const lote = prodRuta.loteRef.value;
  if (lote && lotesProduccion.value.some((l) => l.lote_ref === lote)) {
    await seleccionarLote(lote);
    const pid = prodRuta.paradaId.value;
    const parada = (loteActivo.value?.paradas || []).find((x) => x.parada_id === pid);
    if (parada) {
      await seleccionarParada(parada);
      // La PIEZA y el PASO del taller también viajan en la URL. Sin restaurarlos, un
      // refresh (o un enlace compartido) abría el taller correcto pero sin pieza
      // enfocada: la guía y los documentos hablaban de la parada completa y no de la
      // pieza del enlace, que es lo que la persona estaba mirando.
      const pz = prodRuta.pieza.value;
      const celda = pz
        ? (loteActivo.value?.ramas || [])
            .filter((r) => r.pieza === pz).map((r) => celdaDe(r, pid)).find(Boolean)
        : cadenaFinal.value.find((x) => x.parada_id === pid);
      if (celda) await abrirCelda(celda, pz || null);
      const tp = prodRuta.pasoTaller.value;
      if (tp && tp !== subStepOpen.value) await irPasoTaller(tp);
    }
  } else if (lote) {
    // El lote recordado ya no existe en esta OV (ver Fase 0): se limpia.
    prodRuta.set({ lote: null, paso: null, parada: null, tpaso: null });
  }
}

// ── Paso 4 · Entrega (§5.8) ───────────────────────────────────────────────────
/** Cuántos talleres del lote faltan por entregar -- lo que explica el estado vacío. */
const talleresPendientesLote = computed(() =>
  (loteActivo.value?.paradas || []).filter((p) => !p.receipt_validated).length);

// ── Paso 2 · Flujo (§5.6) ─────────────────────────────────────────────────────
/** Los contadores de la matriz, en el vocabulario de color de Producción. */
const estadoContador = (k) => ({ recibido: "ok", listo: "now", encargado: "wait", bloqueado: "off" }[k] || "off");
/** Estado y texto de una tarjeta de la cadena final (confección, acabado…). */
function estadoCadena(t) {
  if (t.estado === "recibido") return t.facturado ? "fac" : "ok";
  if (t.estado === "listo") return "now";
  if (t.estado === "bloqueado") return "off";
  return "wait";
}
function textoCadena(t) {
  if (t.estado === "recibido") return t.arma_prenda ? "Confección recibida" : "Recibido";
  if (t.estado === "listo") return t.arma_prenda ? "Lista para encargar" : "Lista";
  if (t.estado === "bloqueado") {
    return t.arma_prenda ? `Faltan ${t.piezas_total - t.piezas_listas}` : "En espera";
  }
  return "Encargada";
}
// ── Paso 1 · Materia prima: lista de proveedores y su panel (§5.5) ────────────
/** Materiales de un proveedor, en una línea ("Gabardina naranja · 2,871.55 m"). */
function materialesDeProveedor(grp) {
  return (grp.items || [])
    .map((it) => `${it.item_name || it.item_code} ${Number(it.qty || 0).toLocaleString("es-MX")} ${it.uom || ""}`.trim())
    .join(" · ");
}
/** Los tres pasos del proveedor, con su estado. El "actual" es el primero no hecho. */
/** Los pasos de un proveedor, EN EL ORDEN REAL del proceso.
 *
 *  Cotizar es opcional y son DOS pasos que van juntos: se le pide la cotización al
 *  proveedor y el proveedor contesta con su presupuesto. Con "Solicitar cotización
 *  al proveedor" (menú "⋯") entran los dos al camino de una vez; el presupuesto se
 *  crea al llegar a su paso, no antes. Quien compra directo sigue viendo tres pasos.
 *
 *  `conOpcionales` en false deja solo los tres fijos -- es lo que cabe en el
 *  mini-camino de la lista de proveedores. */
function caminoProveedor(grp, { conOpcionales = false } = {}) {
  const po = grp.po;
  const orden = [];
  if (conOpcionales) {
    const rfq = rfqDeProveedor(loteActivo.value, grp.supplier);
    const sq = sqDeProveedor(loteActivo.value, grp.supplier);
    // Basta con que exista uno de los dos para pintar los DOS: son un solo proceso.
    if (rfq || sq) {
      orden.push(["rfq", "Solicitud de cotización", rfq?.docstatus === 1]);
      orden.push(["sq", "Presupuesto de proveedor", sq?.docstatus === 1]);
    }
  }
  // En la lista se ve si la orden ya se le mandó al proveedor; el stepper del panel
  // (conOpcionales) conserva el nombre del paso.
  // Solo mientras falta recibir: ya recibida, que se haya mandado o no ya no importa.
  const avisoEnvio = !conOpcionales && po?.docstatus === 1 && !po.hay_recibo_validado;
  orden.push(["oc", avisoEnvio ? (po.enviado_el ? "Orden enviada" : "Orden sin enviar") : "Orden de compra",
    po?.docstatus === 1]);
  orden.push(["recibo", "Recibo", !!po?.receipt_validated]);
  orden.push(["factura", "Factura", po?.factura?.docstatus === 1]);

  const hechos = Object.fromEntries(orden.map(([k, , h]) => [k, h]));
  const actual = orden.map(([k]) => k).find((k) => !hechos[k]);
  return orden.map(([clave, texto]) => ({
    clave, texto,
    estado: hechos[clave] ? (clave === "factura" ? "fac" : "ok")
      : clave !== actual ? "off"
      : clave === "rfq" || clave === "sq" ? "now"
      : !po ? "off"
      : clave === "factura" && po.factura ? "wait" : "now",
    actual: clave === actual,
    sinEnviar: clave === "oc" && avisoEnvio && !po.enviado_el,
  }));
}
function estadoProveedor(grp) {
  const po = grp.po;
  if (!po) return "off";
  if (po.factura?.docstatus === 1) return "fac";
  if (po.factura) return "wait";
  if (po.receipt_validated) return "ok";
  return "now";
}

const panelProv = reactive({ abierto: false, supplier: "", tab: "oc", cargando: false, error: "" });

/** Suelta los documentos de compra que tiene cargados `useProduccion`.
 *
 *  Son de UN documento a la vez (§10 del plan): `docCompra`, `reciboPr` y `pinvDoc`
 *  se comparten entre todos los proveedores y todos los pasos. Si al cambiar de paso
 *  o de proveedor el nuevo no se alcanza a cargar -- o no existe todavía -- la
 *  pantalla seguía mostrando el del anterior: se veía la orden de OTRO proveedor
 *  como si fuera la de este. Se limpian ANTES de cada carga. */
function limpiarDocsCompra() {
  docCompra.value = null;
  reciboPr.value = null;
  pinvDoc.value = null;
}
/** El grupo vivo del proveedor abierto -- se vuelve a buscar en cada recarga de
 *  lotes para no quedarse con un objeto congelado (mismo motivo que celdaRef). */
const grpPanelProv = computed(() =>
  proveedoresLote(loteActivo.value || { material_items: [], material_pos: [] })
    .find((g) => g.supplier === panelProv.supplier) || null);

/** Uno a la vez: abrir un panel cierra los demás (comparten el estado de
 *  useProduccion -- ver §10 del plan). */
function cerrarPaneles() {
  panelProv.abierto = false;
  panelOcTaller.abierto = false;
  panelFactura.abierto = false;
  panelRemision.abierto = false;
  if (nuevoLoteForm.open) cerrarNuevoLote();
}

// ── Panel "Remisión" (el paso Enviar, movido aquí) ───────────────────────────
// El paso "Enviar" del stepper principal se quitó: la remisión se arma y se valida
// desde el lote que la produjo (paso Entrega) y las que no son de ningún lote se
// siguen en la bandeja de Envíos. Reusa `dnDoc`/`dnForm`/`selectDn`, los de siempre.
const panelRemision = reactive({ abierto: false, titulo: "", eyebrow: "", cargando: false, error: "" });

async function abrirPanelRemision(name, eyebrow = "") {
  cerrarPaneles();
  // `dnDoc` es de UNA remisión a la vez y lo comparten este panel y la bandeja: se
  // suelta antes de pedir la nueva (misma trampa que docCompra/pinvDoc, §10 del plan).
  dnDoc.value = null;
  panelRemision.eyebrow = eyebrow || `${loteActivoRef.value || "Costeo"} · Remisión`;
  panelRemision.titulo = name;
  panelRemision.error = "";
  panelRemision.abierto = true;
  panelRemision.cargando = true;
  try {
    await selectDn(name);
    if (!dnDoc.value) panelRemision.error = "No se pudo cargar esta remisión.";
  } catch (e) {
    panelRemision.error = e.message || "No se pudo cargar esta remisión.";
  } finally {
    panelRemision.cargando = false;
  }
}
function cerrarPanelRemision() {
  panelRemision.abierto = false;
  panelRemision.cargando = false;
  panelRemision.error = "";
}
const panelRemisionMeta = computed(() => {
  const d = dnDoc.value;
  if (!d) return "";
  const prendas = (d.items || []).reduce((a, it) => a + (Number(it.qty) || 0), 0);
  return [d.customer_name || d.customer, d.lote_ref || "",
          prendas ? `${prendas.toLocaleString("es-MX")} prendas` : "",
          fmtC(d.grand_total || 0)].filter(Boolean).join(" · ");
});
const accionesPanelRemision = computed(() => {
  if (!dnDoc.value || dnValidated.value) return [];
  return [sec("Guardar", guardarRemision), pri("Validar remisión", validarRemision)];
});
/** Lo que no alcanza en el almacén elegido, para avisar ANTES de validar. */
const faltaStockRemision = computed(() =>
  (dnDoc.value?.items || []).some((it) => (it.available ?? 0) < (Number(it.qty) || 0)));

/** Abrir una remisión desde donde sea: ya no salta al paso Enviar (ya no existe). */
async function irARemision(name) {
  await abrirPanelRemision(name);
}

async function abrirPanelProveedor(grp, tab = "", { crear = false } = {}) {
  cerrarPaneles();
  limpiarDocsCompra();
  panelProv.supplier = grp.supplier;
  panelProv.error = "";
  panelProv.abierto = true;
  // Se abre en el primer paso no terminado que de verdad se pueda abrir.
  await nextTick();
  const pasos = pasosPanelProv.value;
  const destino = tab
    || pasos.find((x) => x.estado === "actual" && !x.bloqueado)?.clave
    || pasos.find((x) => !x.bloqueado)?.clave
    || "oc";
  panelProv.tab = destino;   // el paso lo fija SIEMPRE quien abre, aunque la carga falle
  await irPasoProveedor(destino, { crear });
}
function cerrarPanelProveedor() {
  panelProv.abierto = false;
  panelProv.cargando = false;
  panelProv.error = "";
  limpiarDocsCompra();
  loteDocOpen.supplier = null;
  loteDocOpen.tab = null;
}
/** Cambiar de paso dentro del panel = cargar ese documento (lo hace toggleLoteDoc,
 *  que además lo CREA si no existe). Se fuerza a abrir, nunca a cerrar. */
async function irPasoProveedor(tab, { poEsperada = "", crear = false, forzar = false } = {}) {
  // "rfq"/"sq" son documentos sueltos del menú "⋯", no pasos: no se revisan contra
  // el stepper. Un paso bloqueado (prerrequisito o rol) no se abre.
  //
  // `forzar` salta SOLO el prerrequisito, para la transición que dispara el propio
  // "Validar": ese prerrequisito se mide con los datos del LOTE (grp.po.docstatus,
  // grp.po.receipt_validated), que en ese instante pueden no reflejar todavía lo que
  // acabamos de validar. Sin esto la guarda contestaba "Primero valida la orden de
  // compra" y el panel se quedaba en la OC -- lo que se veía como "no pasó al recibo".
  if (!forzar && ["oc", "recibo", "factura"].includes(tab)) {
    const paso = pasosPanelProv.value.find((x) => x.clave === tab);
    if (paso?.bloqueado) { showToast(paso.motivo, "error"); return; }
  }
  const grp = grpPanelProv.value;
  panelProv.tab = tab;
  // Se suelta lo anterior ANTES de cargar: así, pase lo que pase, nunca se ve el
  // documento del paso o del proveedor de antes.
  limpiarDocsCompra();
  panelProv.error = "";
  if (!grp) {
    panelProv.cargando = false;
    panelProv.error = "No se encontró este proveedor en el lote. Vuelve a abrirlo desde la lista.";
    return;
  }
  loteDocOpen.supplier = null;
  loteDocOpen.tab = null;
  panelProv.cargando = true;
  try {
    // `poEsperada` ata el paso a la orden de compra concreta que se acaba de
    // validar, en vez de confiar en el grupo (que puede venir de una lista recién
    // recargada y traer la OC de otro proveedor).
    const grpUsado = poEsperada && grp.po?.name !== poEsperada
      ? { ...grp, po: { ...(grp.po || {}), name: poEsperada, docstatus: 1 } }
      : grp;
    await toggleLoteDoc(loteActivo.value, grpUsado, tab, { crear });
    // Varias de las funciones que crean el documento (generarOcLote, crearRfqLote…)
    // avisan del fallo con un toast y regresan sin lanzar: si solo se mirara la
    // excepción, el panel se quedaba en "Preparando el documento…" para siempre y
    // sin botones. Se comprueba que el documento de verdad haya quedado cargado.
    //
    // Solo es un fallo si de verdad se pidió CREAR el documento y aun así no quedó
    // cargado: navegar a un paso cuyo documento todavía no existe es normal, y ahí
    // lo que se ve es su estado vacío con el botón para crearlo.
    await nextTick();
    if (crear && !docPanelProv.value) {
      panelProv.error = MSG_SIN_DOC[panelProv.tab] || MSG_SIN_DOC.oc;
    }
  } catch (e) {
    panelProv.error = e.message || "No se pudo abrir el documento.";
  } finally {
    panelProv.cargando = false;
  }
}
/** Estado vacío de cada paso del proveedor: qué es y qué pasa al crearlo. */
const VACIO_PASO = {
  oc: { titulo: "Todavía no hay orden de compra",
        detalle: "Se genera con lo que este proveedor tiene asignado en la solicitud de material, en borrador." },
  rfq: { titulo: "Todavía no has pedido la cotización",
         detalle: "Se le manda al proveedor para que ponga su precio." },
  sq: { titulo: "Todavía no has registrado el presupuesto",
        detalle: "Es la respuesta del proveedor a la cotización; de aquí sale el precio de la orden." },
};
const MSG_SIN_DOC = {
  oc: "No se pudo preparar la orden de compra. Revisa el aviso que apareció arriba: suele ser que no quedan materiales pendientes de este proveedor en la solicitud, o que te faltan permisos para crear órdenes de compra.",
  rfq: "No se pudo preparar la solicitud de cotización.",
  sq: "No se pudo preparar el presupuesto del proveedor.",
  recibo: "No se pudo preparar el recibo. La orden de compra tiene que estar validada.",
};
/** El menú "⋯" es una acción explícita: sí genera el documento si no existe. */
const abrirDocProveedor = (tab) => irPasoProveedor(tab, { crear: true });

const pasosPanelProv = computed(() => {
  const grp = grpPanelProv.value;
  if (!grp) return [];
  const po = grp.po;
  // Prerrequisitos en cadena, los mismos que deshabilitaban los botones de antes:
  // sin OC validada no hay recibo, y sin recibo validado no hay factura. La
  // cotización y el presupuesto no tienen prerrequisito: van antes de todo.
  const falta = {
    rfq: "", sq: "",
    oc: "",
    recibo: po?.docstatus === 1 ? "" : "Primero valida la orden de compra",
    // La factura se registra cuando llegó TODO lo de la orden, no con una entrega parcial.
    factura: po?.recibido_completo || po?.factura ? ""
      : po?.hay_recibo_validado ? `Falta recibir ${fmtCantidad(po.pendiente_recibir)}; la factura se registra cuando llegue todo`
      : "Primero valida el recibo de compra",
  };
  return caminoProveedor(grp, { conOpcionales: true }).map((x) => {
    const permitido = x.clave === "factura" ? puedeVer("facturas") : puedeVer("materia") || puedeVer("envios");
    const motivo = !permitido ? "No tienes el rol de esta vista." : falta[x.clave];
    return {
      clave: x.clave, texto: x.texto,
      estado: x.estado === "ok" ? "hecho" : x.estado === "fac" ? "facturado"
        : x.actual ? "actual" : "espera",
      bloqueado: !!motivo, candado: !permitido,
      motivo,
    };
  });
});
/** La ruta de ERPNext del paso abierto. DOC_COMPRA solo conoce oc/rfq/sq, así que
 *  el recibo y la factura caían en "purchase-order" y el enlace abría una Orden de
 *  Compra con el nombre de un Recibo: una pantalla vacía, como si el documento no
 *  existiera. */
const DESK_DE_PASO = { recibo: "purchase-receipt", factura: "purchase-invoice" };
const deskDelPaso = computed(() =>
  DESK_DE_PASO[panelProv.tab] || DOC_COMPRA[panelProv.tab]?.desk || "purchase-order");

const docPanelProv = computed(() =>
  panelProv.tab === "recibo" ? reciboPr.value
    : panelProv.tab === "factura" ? pinvDoc.value
      : docCompra.value);
const panelProvMeta = computed(() => {
  if (!grpPanelProv.value) return "";
  // Solo el documento del paso abierto: la cotización y el presupuesto ya se ven
  // como pasos del stepper cuando existen, no hace falta repetirlos aquí.
  return docPanelProv.value?.name || "sin documento todavía";
});
const pillPanelProv = computed(() => {
  const d = docPanelProv.value;
  if (!d) return { estado: "off", texto: "Sin crear" };
  if (panelProv.tab === "factura") return pinvValidated.value ? { estado: "fac", texto: "Validada" } : { estado: "wait", texto: "Borrador" };
  if (Number(d.docstatus) === 1 && panelProv.tab === "oc" && d.doctype === "Purchase Order")
    return { estado: "ok", texto: d.enviado_el ? "Enviada" : "Validada" };
  return Number(d.docstatus) === 1 ? { estado: "ok", texto: "Validado" } : { estado: "wait", texto: "Borrador" };
});
/** Un paso que pertenece a otra vista se ve, pero no se captura desde aquí (§6.3). */
const panelProvSoloLectura = computed(() => {
  if (panelProv.tab === "factura" && !puedeEditar("facturas")) return "La captura la hace Facturas";
  if (panelProv.tab === "recibo" && !puedeEditar("materia") && !puedeEditar("envios")) return "La captura la hace Envíos";
  if (!["recibo", "factura"].includes(panelProv.tab) && !puedeEditar("materia")) return "La captura la hace Materia prima";
  return "";
});
/** El paso que sigue en el camino de ESTE proveedor (el camino depende de si
 *  cotizó o no, ver caminoProveedor). Null si ya es el último. */
function pasoSiguienteProveedor(desde) {
  const grp = grpPanelProv.value;
  if (!grp) return null;
  const pasos = caminoProveedor(grp, { conOpcionales: true });
  const i = pasos.findIndex((x) => x.clave === desde);
  return i >= 0 ? pasos[i + 1] || null : null;
}

/** "Pasar a ..." : el botón de un paso ya terminado. Lleva al siguiente del camino
 *  de ESE proveedor y, cuando ese paso genera su documento solo (el recibo), lo trae
 *  ya creado -- así no hay que pasar por el paso y pulsar otro botón. */
// Etiqueta completa por paso: "a el recibo" no se escribe así, y armarla por partes
// obliga a cuidar contracciones -- es más sencillo tenerlas escritas.
const BOTON_PASAR_A = {
  rfq: "Pasar a la cotización",
  sq: "Pasar al presupuesto",
  oc: "Pasar a la orden de compra",
  recibo: "Pasar al recibo",
  factura: "Pasar a la factura",
};
/** Pasos cuyo documento se genera al llegar (los demás se capturan a mano). */
const PASO_AUTOCREA = { recibo: true };
function accionPasarA(desde) {
  const sig = pasoSiguienteProveedor(desde);
  if (!sig) return null;
  return pri(BOTON_PASAR_A[sig.clave] || `Pasar a ${sig.texto}`,
    () => irPasoProveedor(sig.clave, { crear: !!PASO_AUTOCREA[sig.clave] }));
}

const accionesPanelProv = computed(() => {
  // Con error, lo único útil es volver a intentarlo -- nunca dejar el pie vacío.
  if (panelProv.error) return [pri("Reintentar", () => irPasoProveedor(panelProv.tab))];
  if (panelProvSoloLectura.value) return [];
  if (panelProv.tab === "factura") {
    if (!pinvDoc.value) return [pri("Crear factura de compra", crearFacturaInline)];
    if (pinvValidated.value) return [];
    if (!validaDirecto(pinvDoc.value.name) || enAprobacion(pinvDoc.value.name)) return [sec("Guardar", guardarPinv)];
    return [sec("Guardar", guardarPinv), pri("Validar factura", validarFacturaInline)];
  }
  if (panelProv.tab === "recibo") {
    // Recibo ya validado: si la orden todavía tiene pendiente (entrega parcial), lo
    // que sigue es registrar otro recibo con lo que falta. La factura espera a que
    // llegue todo.
    if (reciboPr.value && Number(reciboPr.value.docstatus) === 1) {
      const po = grpPanelProv.value?.po;
      if (po?.puede_nuevo_recibo) {
        return [pri(`Registrar otro recibo · faltan ${fmtCantidad(po.pendiente_recibir)}`, () => nuevoReciboLote(po))];
      }
      return [accionPasarA("recibo")].filter(Boolean);
    }
    if (!reciboPr.value) {
      return [pri("Crear recibo de compra", () => irPasoProveedor("recibo", { crear: true }), {
        deshabilitado: grpPanelProv.value?.po?.docstatus !== 1,
        motivo: "Primero valida la orden de compra.",
      })];
    }
    return [sec("Guardar", guardarRecibo), pri("Validar recibo", validarReciboYSeguir)];
  }
  const d = docCompra.value;
  // Documento ya validado: un solo botón que PASA al paso siguiente y, si ese paso
  // crea su documento solo (el recibo), lo trae ya hecho. Validar también avanza
  // (validarDocYSeguir); esto es para cuando se vuelve atrás a revisar.
  if (d && Number(d.docstatus) === 1) {
    // Orden de compra validada: primero se le manda al proveedor, luego se recibe.
    if (panelProv.tab === "oc" && d.doctype === "Purchase Order") {
      const pasar = accionPasarA("oc");
      return d.enviado_el
        ? [sec("Reenviar al proveedor", enviarOcProveedor), pasar].filter(Boolean)
        : [pri("Enviar al proveedor", enviarOcProveedor), pasar && sec(pasar.texto, pasar.accion)].filter(Boolean);
    }
    return [accionPasarA(panelProv.tab)].filter(Boolean);
  }
  // Sin documento todavía: su botón para generarlo, cada uno con su nombre.
  if (!d) {
    // OJO: si la orden YA existe (grp.po) pero no quedó cargada, ofrecer "Generar
    // orden de compra" es falso y duplicaría -- lo que toca es seguir al recibo. Es
    // la pantalla contradictoria que se veía: el paso 1 con ✓ y el cuerpo diciendo
    // "Todavía no hay orden de compra".
    if (panelProv.tab === "oc" && grpPanelProv.value?.po) {
      return [accionPasarA("oc")].filter(Boolean);
    }
    const crear = {
      oc: "Generar orden de compra",
      rfq: "Solicitar cotización al proveedor",
      sq: "Registrar presupuesto del proveedor",
    }[panelProv.tab];
    return crear ? [pri(crear, () => irPasoProveedor(panelProv.tab, { crear: true }))] : [];
  }
  const out = [];
  if (panelProv.tab === "oc") out.push(sec("Jalar precios", jalarPreciosOC));
  out.push(sec("Guardar", guardarDocCompra));
  if (d.doctype === "Purchase Order" && (!validaDirecto(d.name) || enAprobacion(d.name))) return out;
  if (d.requiere_doble_validacion && !d.revisado_yelke) {
    out.push(pri("Revisar", revisarDocCompra, {
      deshabilitado: !permisosValidacion.puede_revisar,
      motivo: "Necesitas el rol 'Revisor de Documentos Yelke' para revisar.",
    }));
  } else {
    out.push(pri("Validar", validarDocYSeguir, {
      deshabilitado: !permisosValidacion.puede_aprobar,
      motivo: "Necesitas el rol 'Aprobador de Documentos Yelke' para validar.",
    }));
  }
  return out;
});

/** Validar la orden de compra y pasar SOLO al recibo, que `validarDocCompra` ya dejó
 *  creado. Si la validación no pasó, el panel se queda donde está (con su aviso).
 *  Se recarga el lote antes de cambiar de paso: el recibo se busca por la OC del
 *  proveedor (grp.po.receipt) y ese dato acaba de nacer -- sin refrescar, el paso
 *  Recibo se abría con el documento del proveedor anterior. */
async function validarDocYSeguir() {
  const esOc = panelProv.tab === "oc";
  const poValidada = esOc ? docCompra.value?.name : "";
  await validarDocCompra();
  if (Number(docCompra.value?.docstatus) !== 1) return;   // no se validó: nada que avanzar
  await loadLotesProduccion();
  await nextTick();
  // La orden de compra se queda abierta: lo que sigue es mandársela al proveedor
  // ("Enviar al proveedor"); de ahí se pasa al recibo.
  if (esOc) return;
  const sig = pasoSiguienteProveedor(panelProv.tab);
  if (!sig) return;
  // Al salir de la OC se ata el salto a esa orden concreta y se pide `crear`: al
  // validar, el backend ya dejó hecho su recibo (crear_recibo_oc es idempotente y
  // devuelve el que exista), así que el paso Recibo abre con el documento puesto en
  // vez de pedir un clic más. Entre cotización y presupuesto no hay nada que atar.
  await irPasoProveedor(sig.clave, esOc ? { poEsperada: poValidada, crear: true, forzar: true } : { forzar: true });
}
/** Validar el recibo y pasar solo a la factura, para no tener que volver al
 *  stepper. Si no se validó, el panel se queda donde está con su aviso. */
async function validarReciboYSeguir() {
  if (!puedeValidarReciboAhora()) return;
  await validarRecibo();
  if (Number(reciboPr.value?.docstatus) !== 1) return;
  await loadLotesProduccion();
  await nextTick();
  // Entrega parcial: se queda en el recibo, donde está "Registrar otro recibo".
  const po = grpPanelProv.value?.po;
  if (po?.puede_nuevo_recibo) {
    showToast(`Entrega parcial registrada · faltan ${fmtCantidad(po.pendiente_recibir)} por recibir`);
    return;
  }
  await irPasoProveedor("factura", { forzar: true });
}

/** El recibo exige costo de envío (aunque sea 0) -- antes lo avisaba el propio
 *  panel; ahora el botón vive afuera, así que se revisa aquí. */
function puedeValidarReciboAhora() {
  if (reciboForm.shipping_cost === "" || reciboForm.shipping_cost === null || reciboForm.shipping_cost === undefined) {
    showToast("Captura el costo de envío antes de validar (pon 0 si no hubo)", "error");
    return false;
  }
  return true;
}
// ── Paso 2 · Talleres: la matriz es el índice, cada columna un taller ─────────
/** La parada (taller) que hay detrás de una columna de la matriz o de una tarjeta
 *  de la cadena final. Las columnas SON las paradas: rama_etapas + rama_cadena
 *  coincide exactamente con paradas. */
function paradaDeEtapa(e) {
  return (loteActivo.value?.paradas || []).find((p) => p.parada_id === e.parada_id) || null;
}
/** ¿La tarjeta de la cadena final abre su detalle? Solo cuando ya hay algo que
 *  trabajar ahí: con piezas faltantes no hay documentos que ver, y estando lista hay
 *  que pulsar su botón (el clic en la fila creaba el encargo sin avisar). */
const cadenaAbrible = (t) => !["bloqueado", "listo"].includes(t.estado);

/** Clic en una tarjeta de la cadena final ya en marcha: abre su detalle. */
async function abrirTallerDeCadena(t) {
  if (!cadenaAbrible(t)) return;
  if (!puedeVer("talleres")) { showToast("Necesitas el rol Producción Talleres Yelke para abrir un taller.", "error"); return; }
  await abrirConfeccion(t);
}
/** El botón de la tarjeta lista: encarga el trabajo y pasa a su detalle. */
async function encargarCadena(t) {
  if (!puedeEditar("flujo")) { showToast("Necesitas el rol Producción Flujo Yelke para encargar.", "error"); return; }
  await abrirConfeccion(t);
}

// ── Sub-pantalla de un taller (§5.7) ──────────────────────────────────────────
/** Meta del encabezado de un taller: piezas · prendas · servicios $ por prenda. */
function metaTallerDetalle(pa) {
  const piezas = piezasDeParada(pa.parada_id).length;
  const prendas = (pa.productos || []).map((x) => Number(x.qty || 0).toLocaleString("es-MX")).filter((x) => x !== "0").join(" + ");
  // El precio por prenda sale del encabezado de la etapa (rama_etapas.precio_prenda),
  // no de los renglones del encargo: ahí el cobro viaja completo en una pieza
  // portadora y las demás salen en $0 (ver _ramas_por_pieza).
  const etapa = (loteActivo.value?.rama_etapas || []).find((e) => e.parada_id === pa.parada_id);
  const servicios = etapa && etapa.precio_prenda ? `${fmtC(etapa.precio_prenda)} por prenda` : "";
  return [piezas ? `${piezas} pieza${piezas === 1 ? "" : "s"}` : "",
          prendas ? `${prendas} prendas` : "",
          servicios].filter(Boolean).join(" · ");
}
/** Los pasos de la sub-pantalla del taller. El estado sale de pasoHecho(), que ya
 *  mira la CELDA abierta y no la parada (varias piezas comparten taller).
 *
 *  La FACTURA no está aquí a propósito: es UNA por orden de compra de
 *  subcontratación (el comportamiento nativo de ERPNext), no una por lote ni por
 *  pieza, y solo se captura cuando el taller devolvió todo lo de TODOS sus lotes.
 *  Su seguimiento vive en la bandeja de Facturas. */
const PASOS_TALLER_UI = [["sco", "Encargo"], ["transfer", "Envío"], ["recibo", "Recibo"]];
const pPasosTaller = computed(() => {
  const pa = paradaActiva.value;
  if (!pa) return [];
  const hechos = {
    sco: pasoHecho("sco"), transfer: pasoHecho("transfer"), recibo: pasoHecho("recibo"),
  };
  const actual = PASOS_TALLER_UI.map(([k]) => k).find((k) => !hechos[k]);
  // Prerrequisitos en cadena, los mismos que deshabilitaban los botones de antes.
  const falta = {
    sco: pa.po_docstatus === 1 ? "" : `Valida antes la orden de compra de ${pa.supplier}`,
    transfer: pasoHecho("sco") ? "" : "Primero crea el encargo",
    recibo: pasoHecho("transfer") ? "" : "Primero envía el material",
  };
  return PASOS_TALLER_UI.map(([clave, texto]) => {
    const permitido = puedeVer("talleres") || puedeVer("envios");
    const motivo = !permitido ? "No tienes el rol de esta vista." : falta[clave];
    return {
      clave, texto,
      estado: hechos[clave] ? "hecho" : clave === actual ? "actual" : "espera",
      bloqueado: !!motivo, candado: !permitido, motivo,
    };
  });
});
async function irPasoTaller(clave) {
  const paso = pPasosTaller.value.find((x) => x.clave === clave);
  if (paso?.bloqueado) { showToast(paso.motivo, "error"); return; }
  subStepOpen.value = clave;
  prodRuta.set({ tpaso: clave });
  if (clave === "sco") await maybeSugerirPrimeraEtapaQty();
}

// ── Paneles del taller: su orden de compra y su ficha de manufactura ──────────
const panelOmTaller = reactive({ abierto: false, titulo: "" });
async function abrirOcDelTaller() {
  const pa = paradaActiva.value;
  if (!pa?.po) { showToast("Este taller todavía no tiene orden de compra.", "error"); return; }
  await abrirOcTaller({ name: pa.po, supplier: pa.supplier, supplier_name: pa.supplier });
}
async function abrirOmDelTaller() {
  const pa = paradaActiva.value;
  if (!pa?.po) { showToast("Este taller todavía no tiene orden de compra.", "error"); return; }
  cerrarPaneles();
  panelOmTaller.titulo = `Como la recibe ${pa.supplier}`;
  panelOmTaller.abierto = true;
  if (!subPo.value || subPo.value.name !== pa.po) await selectSub(pa.po);
}

/** Se está viendo UN taller (sub-pantalla) y no la lista: lo dice la URL. */
const pTallerAbierto = computed(() => !!prodRuta.paradaId.value && !!paradaActiva.value);

function metaParada(pa) {
  // Las PIEZAS de verdad (de la matriz), no los renglones de la OC: una parada con
  // dos servicios sobre las mismas piezas trae el doble de renglones.
  const piezas = piezasDeParada(pa.parada_id).length || (pa.fg_items || []).length;
  const prendas = (pa.productos || []).reduce((a, x) => a + Number(x.qty || 0), 0);
  return [pa.supplier,
          piezas ? `${piezas} pieza${piezas === 1 ? "" : "s"}` : "",
          prendas ? `${prendas.toLocaleString("es-MX")} prendas` : "",
          pa.es_terminal ? "último taller" : ""].filter(Boolean).join(" · ");
}
/** Los 4 pasos de un taller, con su estado real. */
function pasosDeParada(pa) {
  const hechos = {
    encargo: !!pa.sco, envio: !!pa.transfer_done, recibo: !!pa.receipt_validated,
  };
  const orden = ["encargo", "envio", "recibo"];
  const actual = orden.find((k) => !hechos[k]);
  return orden.map((clave, i) => ({
    clave, texto: ["Encargo", "Envío", "Recibo"][i],
    estado: hechos[clave] ? "hecho" : clave === actual ? "actual" : "espera",
  }));
}
/** Los 4 pasos DE UNA PIEZA en su taller, para la celda de la matriz. El avance es
 *  por celda y no por parada: una parada sirve a varias piezas y casi siempre se
 *  encarga de a una o de a dos, así que el cuello puede ir ya recibido mientras los
 *  puños siguen listos para encargar -- el stepper de la parada decía lo mismo para
 *  las dos. Los estados de la celda (ver pasoEstadoTexto) son acumulativos:
 *  listo -> encargado -> enviado -> recibido (+ facturado). */
function pasosDeCelda(c) {
  const hechos = {
    encargo: ["encargado", "enviado", "recibido"].includes(c.estado),
    envio: ["enviado", "recibido"].includes(c.estado),
    recibo: c.estado === "recibido",
  };
  const orden = ["encargo", "envio", "recibo"];
  const actual = orden.find((k) => !hechos[k]);
  return orden.map((clave, i) => ({
    clave, texto: ["Encargo", "Envío", "Recibo"][i],
    estado: hechos[clave] ? "hecho" : clave === actual ? "actual" : "espera",
  }));
}

// ── LA BARRA DE ACCIONES (§4.6) ───────────────────────────────────────────────
// Regla: a la derecha SIEMPRE el botón que avanza -- la acción pendiente del paso
// o, si ya terminó, "Siguiente: <paso> →". A su izquierda las secundarias; en el
// centro, una línea que explica por qué el botón está como está.
const sec = (texto, accion, extra = {}) => ({ texto, tipo: "secundaria", accion, ...extra });
const pri = (texto, accion, extra = {}) => ({ texto, tipo: "primaria", accion, ...extra });
/** Cantidad corta para avisos ("1,250" o "217.5"). */
const fmtCantidad = (n) => Number(n || 0).toLocaleString("es-MX", { maximumFractionDigits: 3 });

/** Lote siguiente al activo (para el "Siguiente: Lote N →" del último paso). */
const loteSiguiente = computed(() => {
  const i = lotesProduccion.value.findIndex((l) => l.lote_ref === loteActivoRef.value);
  return i >= 0 ? lotesProduccion.value[i + 1] || null : null;
});

function barraPreparacion() {
  const atras = { texto: "Tablero", ir: () => irProduccion({ vista: "tablero" }) };
  const paso = pPrepPaso.value;
  if (paso === 1) {
    if (!hasPlan.value) {
      return { atras, estado: { color: "wait", texto: "Todavía no hay plan de producción" },
        acciones: [pri("Preparar producción", prepararProduccion)] };
    }
    if (!planValidated.value) {
      return { atras, estado: { color: "wait", texto: "Plan en borrador" },
        acciones: [sec("Obtener materias primas", obtenerMateriasPrimas), sec("Guardar", guardarPlan),
                   pri("Validar plan", validarPlan)] };
    }
    return { atras, estado: { color: "ok", texto: "Plan validado" },
      acciones: [sec("Orden de trabajo", crearOrdenesTrabajo),
                 pri("Siguiente: Materia prima →", () => prodRuta.set({ prep: 2 }))] };
  }
  if (paso === 2) {
    const atras2 = { texto: "Plan", ir: () => prodRuta.set({ prep: 1 }) };
    if (!mrDetail.value) {
      return { atras: atras2, estado: { color: "wait", texto: "Todavía no hay solicitud de material" },
        acciones: [pri("Crear solicitud de material", crearSolicitud)] };
    }
    if (!mrValidated.value) {
      return { atras: atras2,
        estado: mrLotesInvalidos.value
          ? { color: "bad", texto: "Revisa las cantidades de los lotes de entrega" }
          : { color: "wait", texto: "Solicitud en borrador" },
        acciones: [sec("Guardar", guardarSolicitud),
                   pri(mrLotes.value.length ? `Validar y dividir en ${mrLotes.value.length} lote(s)` : `Validar solicitud (todo en ${siguienteLoteRef()})`,
                       validarSolicitud, { deshabilitado: mrLotesInvalidos.value,
                         motivo: "Alguna cantidad por lote no cuadra con el pendiente." })] };
    }
    return { atras: atras2, estado: { color: "ok", texto: "Solicitud validada" },
      acciones: [pri("Siguiente: Orden de manufactura →", () => prodRuta.set({ prep: 3 }))] };
  }
  // Paso 3 · Orden de manufactura. Se captura aquí para que las órdenes del paso
  // siguiente salgan con la ficha de cada taller ya heredada.
  const atras3 = { texto: "Materia prima", ir: () => prodRuta.set({ prep: 2 }) };
  // No se pasa a Órdenes a talleres sin la ficha completa: cada orden la lleva.
  const siguienteOm = pri("Siguiente: Órdenes a talleres →", () => irProduccion({ vista: "ordenes" }), {
    deshabilitado: !omCompleta.value,
    motivo: "Primero captura la orden de manufactura de todos los productos.",
  });
  if (!puedeEditar("om")) {
    return { atras: atras3, estado: omCompleta.value
        ? { color: "ok", texto: "Ficha capturada" }
        : { color: "wait", texto: "Falta que Orden de manufactura capture la ficha" },
      acciones: [siguienteOm] };
  }
  // "Guardar" vive dentro del editor (es por producto, no de la pantalla completa),
  // igual que "+ Agregar" de cada sección.
  return { atras: atras3,
    estado: omCompleta.value
      ? { color: "ok", texto: `Ficha capturada (${omCapturadas.value.capturadas} de ${omCapturadas.value.total})` }
      : { color: "wait", texto: `Falta capturar la ficha (${omCapturadas.value.capturadas} de ${omCapturadas.value.total})` },
    acciones: [siguienteOm] };
}

/** Barra de la vista "Órdenes a talleres" (antes era el paso 3 de Preparación). */
function barraOrdenesTalleres() {
  const atras = { texto: "Preparación", ir: () => prodRuta.irPreparacion(3) };
  // Se cuenta sobre las órdenes reales (subOcs, borradores incluidos): las paradas de
  // productosCosteo solo ven órdenes ya validadas, y ahora se validan a mano.
  const vivas = (subOcs.value || []).filter((o) => o.docstatus !== 2);
  if (!vivas.length) {
    return { atras, estado: omCompleta.value
        ? { color: "wait", texto: "Todavía no hay órdenes a talleres" }
        : { color: "wait", texto: "Falta la orden de manufactura" },
      acciones: [pri("Crear órdenes a talleres", crearSubcontratosDesdeLote, {
        deshabilitado: !omCompleta.value,
        motivo: "Primero captura la orden de manufactura (Preparación · paso 3).",
      })] };
  }
  const pendientes = vivas.filter((o) => o.docstatus === 0);
  if (pendientes.length) {
    return { atras, estado: { color: "wait", texto: `${pendientes.length} por revisar y validar` },
      acciones: [pri("Revisar y validar →", () => abrirOcTaller(pendientes[0]))] };
  }
  if (!lotesProduccion.value.length) {
    return { atras, estado: { color: "ok", texto: "Todo listo para abrir el primer lote" },
      acciones: [pri("Abrir primer lote →", abrirNuevoLotePanel)] };
  }
  return { atras, estado: { color: "ok", texto: "Preparación completa" },
    acciones: [pri(`Siguiente: ${lotesProduccion.value[0].lote_ref} →`,
      () => irProduccion({ vista: "lote", lote: lotesProduccion.value[0].lote_ref }))] };
}

function barraLote() {
  const l = loteActivo.value;
  if (!l) {
    return { atras: { texto: "Tablero", ir: () => irProduccion({ vista: "tablero" }) },
      estado: { color: "off", texto: "Elige un lote en el menú" }, acciones: [] };
  }
  const est = estadoPasosLote(l);
  const permitidos = pasosLotePermitidos.value;
  const siguiente = (desde) => {
    const i = permitidos.indexOf(desde);
    return i >= 0 && i < permitidos.length - 1 ? permitidos[i + 1] : null;
  };
  const avanzar = (desde) => {
    const sig = siguiente(desde);
    if (sig) {
      const motivo = bloqueoPasoLote(sig);
      return pri(`Siguiente: ${ETIQUETA_PASO_LOTE[sig]} →`, () => irPasoLote(sig),
                 { deshabilitado: !!motivo, motivo });
    }
    const sl = loteSiguiente.value;
    return sl ? pri(`Siguiente: ${sl.lote_ref} →`, () => irProduccion({ vista: "lote", lote: sl.lote_ref }))
              : pri("Ir al Tablero →", () => irProduccion({ vista: "tablero" }));
  };
  const anterior = (desde) => {
    const i = permitidos.indexOf(desde);
    return i > 0 ? { texto: ETIQUETA_PASO_LOTE[permitidos[i - 1]], ir: () => irPasoLote(permitidos[i - 1]) }
                 : { texto: "Tablero", ir: () => irProduccion({ vista: "tablero" }) };
  };

  if (pPasoLote.value === "materia") {
    const provs = proveedoresLote(l);
    const sinOc = provs.filter((g) => !g.po);
    const porRecibir = provs.filter((g) => g.po && g.po.docstatus === 1 && !g.po.receipt_validated);
    const borradores = provs.filter((g) => g.po?.factura && g.po.factura.docstatus === 0);
    const base = { atras: anterior("materia") };
    // El recibo manda sobre generar otra orden: en cuanto se valida una OC, lo que
    // sigue en ESE proveedor es recibirla. Antes `sinOc` iba primero, así que tras
    // validar la barra brincaba a "Generar orden · <otro proveedor>" y el recibo que
    // se acababa de habilitar no se ofrecía. Las órdenes que faltan siguen a mano
    // como secundaria (y en la lista de arriba).
    if (porRecibir.length) {
      return { ...base, estado: { color: "wait", texto: `${porRecibir.length} por recibir` },
        acciones: [
          ...(sinOc.length ? [sec(`Generar orden · ${sinOc[0].supplier}`,
                                  () => abrirPanelProveedor(sinOc[0], "oc", { crear: true }))] : []),
          pri(`Pasar al recibo · ${porRecibir[0].supplier}`,
              () => abrirPanelProveedor(porRecibir[0], "recibo", { crear: true })),
        ] };
    }
    if (sinOc.length) {
      return { ...base, estado: { color: "now", texto: `${sinOc.length} proveedor(es) sin orden de compra` },
        acciones: [
          ...(sinOc.length > 1 ? [sec(`Generar las ${sinOc.length}`, () => generarTodasLasOc(l, sinOc))] : []),
          // `crear: true`: el botón GENERA la orden. Antes solo abría el panel, y ahí
          // había que pulsar "Generar orden de compra" -- el mismo botón dos veces.
          pri(`Generar orden · ${sinOc[0].supplier}`, () => abrirPanelProveedor(sinOc[0], "oc", { crear: true })),
        ] };
    }
    if (borradores.length) {
      return { ...base, estado: { color: "wait", texto: `${borradores.length} factura(s) en borrador` },
        acciones: [pri(`Validar factura · ${borradores[0].supplier}`, () => abrirPanelProveedor(borradores[0], "factura"))] };
    }
    return { ...base, estado: { color: est.materia ? "ok" : "off", texto: est.materia ? "Material recibido" : "Sin materiales en este lote" },
      acciones: [avanzar("materia")] };
  }

  /** La barra de la MATRIZ (el índice de talleres): encargar piezas y la cadena
   *  final. Antes era el paso "Flujo"; ahora es la vista de entrada de Talleres. */
  function barraMatriz() {
    const base = { atras: anterior("talleres") };
    const nSel = celdasSel.value.length;
    if (nSel) {
      const nTalleres = gruposSel.value.length;
      const detalle = gruposSel.value.map((g) => `${g.supplier} · ${g.titulo}`).join(" / ");
      return { ...base, estado: { color: "now", texto: `${nSel} pieza(s) en ${nTalleres} taller(es) — ${detalle}` },
        acciones: [sec("Limpiar", limpiarCeldas),
                   pri(nTalleres === 1 ? "Crear orden" : `Crear ${nTalleres} órdenes`, crearOrdenesSeleccion, {
                     deshabilitado: !puedeEditar("flujo"),
                     motivo: "Necesitas el rol Producción Flujo Yelke para encargar piezas.",
                   })] };
    }
    const listo = cadenaFinal.value.find((t) => t.estado === "listo");
    if (listo) {
      return { ...base, estado: { color: "ok", texto: listo.arma_prenda ? "Todas las piezas listas" : `${listo.titulo} puede encargarse` },
        acciones: [pri(listo.arma_prenda ? "Encargar confección" : `Encargar ${listo.titulo}`, () => encargarCadena(listo))] };
    }
    if (!loteTienePiezas.value) {
      // Sin piezas declaradas se encarga desde cada taller, no desde una matriz.
      // El que sigue es el primero sin encargo y, si ya todos lo tienen, el primero
      // que no haya entregado -- si no, con todos encargados la barra se quedaba con
      // "Siguiente: Entrega" deshabilitado y NINGUNA forma de entrar al taller a
      // enviar el material (pasó en producción con el pantalón, una sola etapa).
      const sinEncargo = (l.paradas || []).find((pa) => !pa.sco);
      const pend = sinEncargo || (l.paradas || []).find((pa) => !pa.receipt_validated);
      const texto = !pend ? "Todos los talleres entregaron"
        : sinEncargo ? `${pend.titulo} · ${pend.supplier} sin encargar`
        : `${pend.titulo} · ${pend.supplier}`;
      return { ...base,
        estado: { color: pend ? "now" : "ok", texto },
        acciones: pend ? [pri(`Abrir ${pend.titulo} →`, () => irAParada(pend))] : [avanzar("talleres")] };
    }
    const listas = (contadoresRamas.value.find((x) => x.k === "listo") || {}).n || 0;
    const pendiente = (l.paradas || []).find((pa) => !pa.receipt_validated);
    if (listas) {
      const falta = bloqueoPasoLote("entrega");
      return { ...base,
        estado: { color: "now",
          texto: `${listas} pieza(s) listas para encargar${falta ? ` · ${falta}` : ""}` },
        acciones: [avanzar("talleres")] };
    }
    // Nada que encargar. Al taller se entra SOLO desde el tablero (la pieza): ahí se
    // sabe qué piezas van en cada encargo; un botón "Abrir <taller>" no lo sabe.
    return { ...base,
      estado: pendiente
        ? { color: "now", texto: `Falta que ${pendiente.supplier} entregue · toca sus piezas para seguir` }
        : { color: "ok", texto: "Todos los talleres entregaron" },
      acciones: [avanzar("talleres")] };
  }

  if (pPasoLote.value === "talleres") {
    const base = { atras: anterior("talleres") };
    // Sin taller abierto manda la matriz, que es el índice.
    if (!pTallerAbierto.value) return barraMatriz();
    // Dentro de un taller manda su propia guía (guiaParada), que ya resuelve el
    // estado real de la parada y la acción que toca.
    if (pTallerAbierto.value && guiaParada.value) {
      const g = guiaParada.value;
      // Primero: si el paso ABIERTO tiene un documento en borrador, lo que toca es
      // guardarlo o validarlo -- eso manda sobre la guía general de la parada
      // (plan §4.6, renglones "Taller · ...").
      const porDoc = barraDocTaller();
      if (porDoc) return porDoc;
      // Si no, la guía ya resuelve el estado real de la parada y qué toca hacer;
      // aquí solo se reparte: título/detalle a la línea de estado, la acción a la
      // primaria y la alterna a una secundaria.
      const sigTaller = siguienteTallerPendiente();
      const falta = faltanteEnvio.value && ["encargado", "listo"].includes(celdaAbierta.value?.estado || "");
      return { atras: { texto: "Talleres", ir: salirDelTaller },
        estado: falta
          ? { color: "bad", texto: `No alcanza: ${faltanteEnvio.value}` }
          : { color: colorGuia(g), texto: `${g.titulo}${g.detalle ? " · " + g.detalle : ""}` },
        acciones: [
          ...(g.alternaTexto ? [sec(g.alternaTexto, g.alterna)] : []),
          ...(g.accionTexto
            ? [pri(g.accionTexto, g.accion)]
            : sigTaller
              ? (loteActivo.value?.ramas?.length
                  ? []   // con piezas, al siguiente taller se llega por el tablero
                  : [pri(`Siguiente taller: ${sigTaller.titulo} →`, () => irAParada(sigTaller))])
              : [avanzar("talleres")]),
        ] };
    }
    const pendiente = (l.paradas || []).find((pa) => !pa.receipt_validated);
    if (pendiente) {
      return { ...base, estado: { color: "now", texto: `${pendiente.titulo} · ${pendiente.supplier}` },
        acciones: loteActivo.value?.ramas?.length ? [avanzar("talleres")]
          : [pri(`Abrir ${pendiente.titulo} →`, () => irAParada(pendiente))] };
    }
    return { ...base, estado: { color: "ok", texto: "Todos los talleres entregaron" }, acciones: [avanzar("talleres")] };
  }

  // Entrega
  const base = { atras: anterior("entrega") };
  const e = l.entrega || {};
  const remision = (e.remisiones || [])[0];
  const acciones = remision ? [sec("Ver remisión", () => irARemision(remision.name))] : [];
  if (e.lista) {
    const destinos = repartoEntrega.value.filter((r) => r.items.length);
    const malo = repartoMalo.value;
    return { ...base, estado: { color: "ok", texto: `${Number(e.pendiente).toLocaleString("es-MX")} prendas por entregar` },
      acciones: [...acciones, pri(destinos.length > 1 ? `Generar ${destinos.length} remisiones` : "Generar remisión",
        () => crearRemisionesLote(l.lote_ref), { deshabilitado: !!malo, motivo: malo })] };
  }
  const borradores = (e.remisiones || []).filter((r) => r.docstatus === 0);
  if (e.producido && !e.pendiente && borradores.length) {
    // Todo repartido, pero falta validar: la siguiente en borrador es lo que toca.
    return { ...base, estado: { color: "wait", texto: `${borradores.length} remisión(es) en borrador · revisa flete y valídalas` },
      acciones: [pri(`Abrir ${borradores[0].name}${borradores[0].direccion ? ` → ${borradores[0].direccion}` : ""}`,
        () => abrirPanelRemision(borradores[0].name, `${l.lote_ref} · Remisión`))] };
  }
  if (e.producido && !e.pendiente) {
    return { ...base, estado: { color: "ok", texto: "Lote entregado: todas sus remisiones están validadas" },
      acciones: [...acciones, avanzar("entrega")] };
  }
  return { ...base, estado: { color: "off", texto: "Esperando fin de producción" },
    acciones: [...acciones, pri("Crear remisión", () => {}, { deshabilitado: true, motivo: "Falta que los talleres entreguen el lote." })] };
}

/** La barra cuando el paso abierto del taller tiene su propio documento que
 *  guardar/validar/crear. Devuelve null si no aplica y manda la guía de la parada. */
function barraDocTaller() {
  const atras = { texto: "Talleres", ir: salirDelTaller };
  const paso = subStepOpen.value;

  if (paso === "sco" && scoSel.value && !scoValidated.value) {
    return { atras, estado: { color: "wait", texto: `Encargo ${scoSel.value.name} en borrador` },
      acciones: [sec("Guardar", guardarSco), pri("Validar encargo", validarSco)] };
  }
  if (paso === "transfer" && transDoc.value && !transValidated.value) {
    return { atras,
      // Si no hay material, decirlo AQUÍ: validar la transferencia rebota con "stock
      // negativo" del lado del servidor y desde fuera parece que el botón no hace nada.
      estado: faltanteEnvio.value
        ? { color: "bad", texto: `No alcanza: ${faltanteEnvio.value}` }
        : { color: "wait", texto: `Envío ${transDoc.value.name} en borrador` },
      acciones: [sec("Guardar", guardarTrans), pri("Enviar al taller", validarEnvioYSeguir)] };
  }
  if (paso === "recibo" && transferDone.value) {
    if (!scr.value) {
      return { atras, estado: { color: "now", texto: "El taller ya tiene el material; falta registrar lo que entregó" },
        acciones: [pri("Crear recibo de subcontratación", crearReciboSub)] };
    }
    if (!scrValidated.value) {
      const faltanCostos = !(scrCostos.value || []).length;
      return { atras,
        estado: faltanCostos ? { color: "wait", texto: "Costos adicionales obligatorios (pon 0 si no hubo)" }
                             : { color: "wait", texto: `Recibo ${scr.value.name} en borrador` },
        acciones: [sec("Guardar", guardarScr), pri("Validar recibo", onValidarScr)] };
    }
    // Recibo validado pero el taller todavía debe piezas: entrega por partes.
    const est = scoSel.value?.estado_recibos;
    if (est?.puede_nuevo_recibo) {
      return { atras,
        estado: { color: "wait", texto: `Entrega parcial: faltan ${fmtCantidad(est.pendiente_recibir)} por recibir` },
        acciones: [pri(`Registrar otro recibo · faltan ${fmtCantidad(est.pendiente_recibir)}`, () => crearReciboSub(true))] };
    }
  }
  return null;
}

/** Qué material NO alcanza para el envío abierto, en una línea ("gabardina 31 de
 *  968.7 m"). Sale de `materialesSco`, el mismo cálculo que pinta en rojo la columna
 *  "Disponible" de la tarjeta "Se le manda al taller", para que la barra y la tabla
 *  nunca digan cosas distintas. Vacío = alcanza todo. */
const faltanteEnvio = computed(() => {
  const n = (v) => Number(v || 0).toLocaleString("es-MX", { maximumFractionDigits: 3 });
  return (materialesSco.value || [])
    .filter((m) => m.falta)
    .map((m) => `${m.item_name || m.rm_item_code} ${n(m.disponible)} de ${n(m.required_qty)} ${m.stock_uom || ""}`.trim())
    .join(" · ");
});

/** Validar la transferencia y pasar al Recibo.
 *
 *  `validarTransferencia` valida y recarga, pero se quedaba en el mismo paso con el
 *  mismo documento a la vista: desde fuera parecía que el botón no hacía nada. Ahora
 *  se refresca el flujo del taller y, si de verdad quedó validada, se avanza -- y si
 *  no, el aviso de por qué se queda en la barra. */
async function validarEnvioYSeguir() {
  // validarTransferencia ya recarga el flujo y los lotes por dentro.
  await validarTransferencia();
  if (!transValidated.value) return;        // no pasó: el toast ya dijo por qué
  await nextTick();
  await irPasoTaller("recibo");
}

/** Volver a la lista de talleres desde la sub-pantalla de uno. */
function salirDelTaller() {
  loteParadaActiva.value = "";
  celdaRef.value = null;
  prodRuta.salirTaller();
}
/** El siguiente taller del lote que todavía no entrega, después del abierto. */
function siguienteTallerPendiente() {
  const paradas = loteActivo.value?.paradas || [];
  const i = paradas.findIndex((x) => x.parada_id === paradaActiva.value?.parada_id);
  return paradas.slice(i + 1).find((x) => !x.receipt_validated) || null;
}

/** El color de la guía de la parada sale de su clase de fondo (ver guiaParada). */
function colorGuia(g) {
  const c = g.cls || "";
  if (c.includes("amber")) return "wait";
  if (c.includes("brand")) return "now";
  if (c.includes("green")) return "ok";
  if (c.includes("red")) return "bad";
  return "off";
}

const pBarra = computed(() => {
  switch (pVista.value) {
    case "tablero": {
      const t = porHacer.value[0];
      return { estado: t ? { color: t.estado, texto: t.titulo } : { color: "ok", texto: "No hay nada pendiente" },
        acciones: t ? [pri(`Ir a ${t.donde} →`, t.ir)] : [] };
    }
    case "preparacion": return barraPreparacion();
    case "ordenes": return barraOrdenesTalleres();
    case "lote": return barraLote();
    case "envios": {
      const n = envPendientes.value;
      const primera = envFilas.value.find((f) => f.pendiente);
      return { atras: { texto: "Tablero", ir: () => irProduccion({ vista: "tablero" }) },
        estado: { color: n ? "now" : "ok", texto: n ? `${n} pendiente(s) en este lote` : "Nada pendiente en almacén" },
        acciones: primera ? [pri("Atender el primero →", primera.ir)] : [] };
    }
    case "facturas": {
      const primera = facturasFilas.value.find((f) => f.pendiente);
      return { atras: { texto: "Tablero", ir: () => irProduccion({ vista: "tablero" }) },
        estado: { color: conteosBandejas.value.facturas ? "wait" : "ok",
          texto: conteosBandejas.value.facturas ? `${conteosBandejas.value.facturas} pendientes` : "Todas las facturas al día" },
        acciones: primera ? [pri("Capturar la siguiente →", primera.ir)] : [] };
    }
    case "sin-acceso":
      return { estado: { color: "bad", texto: `Te falta el rol ${sinAcceso.value.rol || "de esta vista"}` },
        acciones: primeraVistaPermitida.value
          ? [pri(`Ir a ${sinAcceso.value.destino} →`, () => irProduccion({ vista: primeraVistaPermitida.value }))]
          : [] };
    default: return { estado: { color: "off", texto: "" }, acciones: [] };
  }
});

/** "Generar las N": crea en secuencia la OC de cada proveedor que aún no la tiene. */
async function generarTodasLasOc(lote, grupos) {
  for (const g of grupos) {
    try { await generarOcLote(lote, g.supplier); }
    catch (e) { showToast(e.message || `No se pudo generar la orden de ${g.supplier}`, "error"); break; }
  }
  await loadLotesProduccion();
}

const accionesNuevoLote = computed(() => [
  { texto: "Cancelar", tipo: "secundaria", accion: cerrarNuevoLote },
  { texto: "Abrir lote", tipo: "primaria",
    deshabilitado: !nuevoLoteForm.porProducto.some((x) => Number(x.qty) > 0),
    motivo: "Captura al menos una cantidad.",
    accion: async () => { await crearNuevoLote(); if (loteActivoRef.value) prodRuta.irLote(loteActivoRef.value, pasoActualDeLote(loteActivo.value)); } },
]);
async function onValidarScr() { await validarScr(() => loadProdComplete(docName.value, activeSOName.value)); }
// "Almacén de origen" del header es solo un default de conveniencia -- este botón lo
// aplica a TODAS las filas de un jalón (en vez de forzarlo siempre al guardar, que
// pisaría cualquier ajuste fila por fila para materiales que salen de otro almacén,
// ej. avíos comprados directo mientras el semiterminado sale de trabajo en proceso).
function aplicarAlmacenOrigenATodos(warehouse) {
  transForm.from_warehouse = warehouse;
  for (const it of transDoc.value?.items || []) {
    it.s_warehouse = warehouse;
    refrescarDisponibleFila(it);
  }
}
// Cambio de almacén desde la vista agrupada por material: se aplica a todas las
// filas de ese material y se refresca la existencia una sola vez (todas comparten
// almacén, así que el dato es el mismo para las tres o las seis).
async function cambiarAlmacenDeMaterial(grupo, warehouse) {
  const primera = cambiarAlmacenMaterial(grupo, warehouse);
  await refrescarDisponibleFila(primera);
  for (const f of grupo.filas) f.available = primera.available;
}
async function refrescarDisponibleFila(it) {
  if (!it.s_warehouse) { it.available = null; return; }
  try {
    const r = await call("costeo_yelke.api.costeo_api.get_stock_disponible", { item_code: it.item_code, warehouse: it.s_warehouse });
    it.available = r.available;
  } catch { /* ignore */ }
}
// Materiales de un lote, agrupados por proveedor -- cada proveedor tiene sus propios
// 4 botones (Solicitud de cotización / Presupuesto / OC / Recibo), ninguno se genera
// solo ni junta varios proveedores en un mismo documento. El orden sale de
// material_items (TODOS los materiales del lote, no sólo los que aún no tienen OC)
// para que la tarjeta de un proveedor no cambie de lugar cuando genera su primer
// documento -- si sólo se listaran los pendientes, ese proveedor desaparecería de
// esa lista y su tarjeta "saltaría" al final, apareciendo de nuevo sólo por material_pos.
function proveedoresLote(lote) {
  const map = new Map();
  for (const it of lote.material_items || []) {
    const sup = it.supplier || "Sin proveedor";
    if (!map.has(sup)) map.set(sup, { supplier: sup, items: [], po: null });
    map.get(sup).items.push(it);
  }
  for (const po of lote.material_pos || []) {
    const sup = po.supplier || "Sin proveedor";
    if (!map.has(sup)) map.set(sup, { supplier: sup, items: [], po: null });
    map.get(sup).po = po;
  }
  return Array.from(map.values());
}
// Tarjeta de parada (taller) en el flujo del lote: verde si ya recibió; resaltada
// si es la que se está viendo; gris si aún no.
// --- Estilos de los pasos de una RAMA de pieza -----------------------------
// El estado ya viene resuelto del backend (_ramas_por_pieza): recibido / enviado
// / encargado / listo / bloqueado. Un paso bloqueado no es clicable: encargarlo
// no tendría qué transferir.
// El resaltado va por PIEZA, no por parada: varias piezas comparten taller, y
// marcar por parada pintaba de golpe todas las de ese proveedor. Si eliges dos o
// más piezas, las dos se pintan (ver pasoSeleccionado).
// Abrir una celda de la matriz: selecciona su parada Y deja abajo el documento
// que toca. Antes solo cambiaba la parada y el panel se quedaba en el paso
// anterior -- parecía que el clic no había hecho nada y había que pulsar otra vez.
async function marcarCelda(celda, pieza, paradaId) {
  // SOLO se marcan las listas. Una ya encargada volvería a encargarse (dos encargos
  // del mismo trabajo) y una bloqueada le falta su etapa anterior: en esos casos lo
  // útil es entrar a su detalle, que es justo lo que no se podía hacer.
  if (celda.estado !== "listo") { await entrarCelda(celda, pieza); return; }
  const yaEstaba = celdaSeleccionada(pieza, paradaId);
  toggleCelda(pieza, paradaId);
  // Al MARCAR se selecciona abajo la parada de esa celda, para que la barra hable
  // del taller correcto. Al desmarcar no se mueve nada.
  if (!yaEstaba) await abrirCelda(celda, pieza);
}

/** ENTRAR al detalle de una celda: su taller, su pieza y el paso que toca.
 *  `abrirCelda` solo selecciona la parada en memoria; lo que hace que la matriz
 *  ceda el lugar a la sub-pantalla del taller es `?parada=` en la URL
 *  (pTallerAbierto). Sin esto, el clic en una tarjeta ya avanzada no hacía NADA
 *  visible -- no se podía ver el detalle de una pieza en camino. */
async function entrarCelda(celda, pieza) {
  if (!puedeVer("talleres")) {
    showToast("Necesitas el rol Producción Talleres Yelke para abrir un taller.", "error");
    return;
  }
  await abrirCelda(celda, pieza);
  if (!paradaActiva.value) {
    showToast("Esa etapa todavía no tiene orden de compra al taller.", "error");
    return;
  }
  prodRuta.irTaller(celda.parada_id, subStepOpen.value || "sco", pieza || "");
}

/** Qué hace el clic en una celda, para su tooltip. */
function tituloCelda(c, pieza, etapa) {
  if (c.estado === "bloqueado") return `${pieza} espera su etapa anterior`;
  if (c.estado === "listo") return `Marcar ${pieza} para encargarla a ${etapa.supplier}`;
  return `Abrir ${pieza} · ${etapa.titulo} · ${etapa.supplier}`;
}

// Celda abierta: de ella salen la guía y los documentos de abajo. Es la CELDA y
// no la parada porque varias piezas comparten taller -- el cuello y los puños van
// los dos con Alfredo, y mirar el estado de la parada mostraba los documentos de
// los puños al abrir el cuello.
// Guardada por REFERENCIA (pieza + parada), no como objeto: al avanzar un paso se
// recargan los lotes y el objeto viejo quedaba congelado -- la guía seguía
// diciendo "enviar el material" después de haberlo enviado.
const celdaRef = ref(null);
const celdaAbierta = computed(() => {
  const k = celdaRef.value;
  if (!k) return null;
  if (!k.pieza) return cadenaFinal.value.find((t) => t.parada_id === k.parada_id) || null;
  const rama = (loteActivo.value?.ramas || []).find((r) => r.pieza === k.pieza);
  return rama ? (rama.pasos || []).find((p) => p.parada_id === k.parada_id) || null : null;
});

// ¿Ese paso ya está hecho PARA LA CELDA abierta? Las palomitas de los cuatro
// documentos leían el estado de la parada, y como varias piezas comparten taller
// salían todas en verde al abrir una pieza que apenas empieza -- el cuello se
// veía transferido y recibido porque los puños, del mismo Alfredo, ya lo estaban.
function pasoHecho(cual) {
  const c = celdaAbierta.value;
  const p = paradaActiva.value;
  if (!p) return false;
  if (cual === "oc") return p.po_docstatus === 1;
  if (!c) {
    return cual === "sco" ? p.sco_docstatus === 1
      : cual === "transfer" ? !!p.transfer_done
      : !!p.receipt_validated;
  }
  // Un encargo en borrador todavía no cuenta como hecho: falta revisarlo y validarlo.
  if (cual === "sco") return (c.scos || []).length > 0 && !c.borrador && scoSel.value?.docstatus !== 0;
  if (cual === "transfer") return c.estado === "enviado" || c.estado === "recibido";
  return c.estado === "recibido";
}
watch(() => loteActivoRef.value, () => { celdaRef.value = null; });

// El panel de documentos sigue SIEMPRE al encargo de la celda abierta. No basta
// con fijarlo al pulsar: cada acción (enviar material, validar) recarga el flujo
// del proveedor, y ahí el panel podía volver al primer encargo de la parada --
// con el frente abierto se veía el recibo YA VALIDADO de la manga derecha, sin
// botón de validar, porque era otro documento.
watch(() => (celdaAbierta.value && celdaAbierta.value.scos || [])[0], async (sco) => {
  if (sco && scoActivo.value !== sco) await selectSco(sco);
}, { flush: "post" });

// La confección no se marca por piezas: se encarga entera. El botón de su
// tarjeta abre su parada y, si ya se puede, crea el encargo de una vez.
// Tarjetas después de las ramas, en orden (ver _ramas_por_pieza): confección y,
// si la prenda armada sigue a otro taller, los que vengan. Un backend anterior
// solo mandaba rama_terminal.
const cadenaFinal = computed(() => {
  const l = loteActivo.value;
  if (!l) return [];
  if ((l.rama_cadena || []).length) return l.rama_cadena;
  return l.rama_terminal ? [{ ...l.rama_terminal, arma_prenda: true, es_terminal: true }] : [];
});
async function abrirConfeccion(tarjeta) {
  const t0 = tarjeta || loteActivo.value?.rama_terminal;
  if (!t0) return;
  if (t0.estado === "listo") {
    await abrirCelda(t0, null);
    await abrirParada();
  }
  // Encargar recarga los lotes: hay que volver a tomar la tarjeta o se entra con el
  // objeto viejo (todavía sin encargo) y el paso abierto sale equivocado.
  const t = cadenaFinal.value.find((x) => x.parada_id === t0.parada_id) || t0;
  await entrarCelda(t, null);
}

async function abrirCelda(celda, pieza) {
  celdaRef.value = { pieza, parada_id: celda.parada_id };
  await irAPasoDePieza(celda, pieza);
  const p = paradaActiva.value;
  if (!p) return;
  // Los encargos de ESTA pieza, no el primero de la parada.
  const scos = celda.scos;
  if (scos && scos.length && scoActivo.value !== scos[0]) await selectSco(scos[0]);
  const tieneEncargo = scos ? scos.length > 0 : !!p.sco;
  subStepOpen.value =
    p.po_docstatus !== 1 ? "sco"
    : !tieneEncargo ? "sco"
    : (celda.borrador || scoSel.value?.docstatus === 0) ? "sco"   // encargo en borrador: primero se revisa y se valida
    : celda.estado === "encargado" ? "transfer"
    : "recibo";
}

// Qué sigue en la parada abierta. Son cuatro pasos encadenados -- encargo,
// transferencia, recibo-- y hasta ahora, después de crear el encargo, la pantalla
// no decía cuál venía. Devuelve el texto y UNA acción principal.
const guiaParada = computed(() => {
  const p = paradaActiva.value;
  if (!p) return null;
  const taller = p.supplier;

  if (p.po_docstatus !== 1) {
    return {
      cls: "bg-amber-50 ring-1 ring-amber-200",
      titulo: "Falta validar la orden de compra de este taller",
      detalle: "Sin ella no se puede encargar nada. Ábrela abajo y valídala.",
      accionTexto: "Ver orden de compra", accion: abrirOcDelTaller,
    };
  }
  // El estado que manda es el de la CELDA abierta: varias piezas comparten
  // taller y parada, y el avance de una no dice nada de la otra. Sin celda
  // (producto sin piezas) se cae al estado de la parada, como siempre.
  const c = celdaAbierta.value;
  const estado = c ? c.estado
    : !p.sco ? "listo" : !p.transfer_done ? "encargado" : !p.receipt_validated ? "enviado" : "recibido";
  const scoDeLaCelda = (c && c.scos && c.scos.length) ? c.scos[0] : p.sco;
  const dePieza = c && c.servicio ? ` (${c.servicio})` : "";

  if (estado === "bloqueado") {
    const esPieza = !!celdaRef.value?.pieza;
    return {
      cls: "bg-surface-raised ring-1 ring-surface-border",
      titulo: esPieza ? "Esta pieza todavía no puede entrar aquí"
                      : `${p.titulo} todavía no puede empezar`,
      detalle: esPieza
        ? "Le falta terminar su etapa anterior; en cuanto la recibas se habilita."
        : "Espera a que los talleres anteriores entreguen; en cuanto lo hagan se habilita.",
    };
  }
  if (estado === "listo") {
    // Una etapa que NO se reparte en piezas -- la confección, o cualquier paso de
    // un producto sin piezas declaradas-- se encarga entera desde aquí. Solo las
    // que sí tienen piezas mandan a elegirlas en la matriz.
    const conPiezas = piezasDeParada(p.parada_id).length > 0;
    if (!conPiezas) {
      return {
        cls: "bg-brand-50 ring-1 ring-brand-200",
        titulo: `Siguiente: encargar el trabajo a ${taller}`,
        detalle: "Se encarga con la cantidad y la fecha del lote.",
        accionTexto: `Encargar a ${taller}`, accion: () => abrirParada(),
      };
    }
    return {
      cls: "bg-surface-raised ring-1 ring-surface-border",
      titulo: `Siguiente: encargar el trabajo${dePieza}`,
      detalle: "Vuelve a Talleres, marca las piezas que vas a encargar y pulsa Crear orden.",
    };
  }
  if (estado === "encargado" && c && !celdaRef.value?.pieza) {
    // Tarjeta de la cadena final (confección, acabado…): su encargo nace al abrir el
    // lote, pero su material son las piezas de las etapas anteriores. Mientras no
    // lleguen, enviar solo daría "falta material".
    const i = cadenaFinal.value.findIndex((t) => t.parada_id === c.parada_id);
    const previoOk = i <= 0
      ? (c.piezas_listas ?? 0) >= (c.piezas_total ?? 0)
      : cadenaFinal.value[i - 1]?.estado === "recibido";
    if (!previoOk) {
      return {
        cls: "bg-surface-raised ring-1 ring-surface-border",
        titulo: `Ya está encargado a ${taller}; falta que lleguen las piezas`,
        detalle: i <= 0
          ? `Llevas ${c.piezas_listas ?? 0} de ${c.piezas_total ?? 0} piezas listas. Cuando estén todas, aquí se habilita enviar el material.`
          : `Espera a que ${cadenaFinal.value[i - 1]?.supplier || "el taller anterior"} entregue; en cuanto lo recibas se habilita.`,
      };
    }
  }
  if (estado === "encargado") {
    return {
      cls: "bg-brand-50 ring-1 ring-brand-200",
      titulo: `Siguiente: preparar el envío de material a ${taller}`,
      detalle: "Se crea la transferencia en borrador para revisarla; nada sale del almacén hasta «Enviar al taller».",
      // Primero el documento (borrador) y su revisión en el paso Envío; el envío de
      // verdad es otro clic ("Enviar al taller", barraDocTaller). Antes este botón
      // enviaba directo y no daba chance de revisar almacenes y cantidades.
      accionTexto: "Crear transferencia",
      accion: async () => { await transferirMaterial(); if (transDoc.value) await irPasoTaller("transfer"); },
    };
  }
  if (estado === "enviado") {
    return {
      cls: "bg-brand-50 ring-1 ring-brand-200",
      titulo: "Siguiente: confirmar lo que entregó el taller",
      detalle: "Captura cuánto entregó de cada pieza y valida el recibo — ahí entra a tu inventario.",
      accionTexto: "Ir al recibo", accion: () => { subStepOpen.value = "recibo"; },
    };
  }
  // Pieza terminada en esta etapa: se apunta a lo siguiente que ya se pueda
  // encargar en TODO el lote, sin importar el taller.
  const pend = [];
  for (const r of loteActivo.value?.ramas || []) {
    for (const paso of r.pasos || []) if (paso.estado === "listo") pend.push(`${r.pieza} en ${paso.titulo}`);
  }
  // Facturar NO es parte del flujo del lote: la factura de maquila es UNA por orden
  // de compra del taller y se captura en la bandeja de Facturas, cuando ya devolvió
  // todo lo de todos sus lotes. Aquí solo se dice qué sigue en producción.
  return {
    cls: "bg-green-50 ring-1 ring-green-200",
    titulo: c ? `${c.servicio || "Esta etapa"}: pieza recibida` : "Esta etapa ya está recibida",
    detalle: pend.length
      ? `Sigue: ${pend.slice(0, 3).join(" · ")}${pend.length > 3 ? ` y ${pend.length - 3} más` : ""} — márcalas en la matriz.`
      : "No queda nada pendiente de encargar en este lote.",
  };
});

// Contadores del encabezado: cuántas celdas hay en cada estado.
const contadoresRamas = computed(() => {
  const n = { recibido: 0, listo: 0, encargado: 0, enviado: 0, bloqueado: 0 };
  for (const r of loteActivo.value?.ramas || []) for (const p of r.pasos || []) n[p.estado] = (n[p.estado] || 0) + 1;
  return [
    { k: "listo", n: n.listo, txt: "por encargar", cls: "bg-brand-50 text-brand-700" },
    { k: "encargado", n: n.encargado + n.enviado, txt: "en taller", cls: "bg-brand-50 text-brand-700" },
    { k: "recibido", n: n.recibido, txt: "recibidas", cls: "bg-green-50 text-green-700" },
    { k: "bloqueado", n: n.bloqueado, txt: "en espera", cls: "bg-surface-raised text-ink-muted" },
  ].filter((c) => c.n > 0);
});

// Estilo de una celda del tablero. La seleccionada manda sobre todo lo demás.
function celdaClass(c, pieza, etapa) {
  if (celdaSeleccionada(pieza, etapa.parada_id)) return "bg-brand-500 text-white shadow-sm";
  // Las que ya tienen encargo no se oscurecen solas al pasar el mouse: se resalta
  // el ENCARGO completo, todas sus piezas igual (mismoEncargoEnHover).
  if (c.estado === "recibido") return c.facturado ? "bg-indigo-50 text-indigo-700" : "bg-emerald-50 text-emerald-700";
  if (c.estado === "listo") return "bg-white text-ink ring-1 ring-brand-200 hover:ring-brand-400 hover:bg-brand-50/40";
  // Encargada / enviada: no se vuelve a marcar, pero sí se entra a ella para
  // seguir con su transferencia y su recibo.
  // Ámbar, como el punto "en taller" del resumen: pendiente de que el taller entregue.
  return "bg-amber-50 text-amber-800";
}
/** Lo que dice la celda: corto, en el idioma de la pieza. */
function textoCelda(c, pieza, etapa) {
  if (c.estado === "listo") return celdaSeleccionada(pieza, etapa.parada_id) ? "Seleccionada" : "Por encargar";
  if (c.estado === "recibido") return c.facturado ? "Facturada" : "Recibida";
  if (c.estado === "encargado" && c.borrador) return "Por revisar";
  return { encargado: "Encargada", enviado: "En el taller" }[c.estado] || pasoEstadoTexto(c);
}
/** ¿La columna junta servicios distintos? Entonces la celda dice cuál le toca. */
function variosServicios(etapa) {
  const servicios = new Set((loteActivo.value?.ramas || [])
    .map((r) => celdaDe(r, etapa.parada_id)?.servicio).filter(Boolean));
  return servicios.size > 1;
}
function pasoEstadoTexto(p) {
  if (p.estado === "recibido" && p.facturado) return "Recibido · facturado";
  return {
    recibido: "Recibido",
    enviado: "Material enviado",
    encargado: "Encargo creado",
    listo: "Listo para encargar",
    bloqueado: "Espera el paso anterior",
  }[p.estado] || "";
}
function pasoEstadoColor(p) {
  if (p.estado === "recibido" && p.facturado) return "text-indigo-700";
  return {
    recibido: "text-green-700",
    enviado: "text-brand-700",
    encargado: "text-brand-700",
    listo: "text-brand-600 font-medium",
    bloqueado: "text-ink-light",
  }[p.estado] || "text-ink-light";
}
function paradaBtnClass(p) {
  if (p.receipt_validated) return "border-green-500 bg-green-50";
  if (loteParadaActiva.value === p.parada_id) return "border-brand-500 bg-brand-50";
  if (p.sco) return "border-brand-200 bg-white hover:bg-surface-raised";
  return "border-surface-border bg-white hover:bg-surface-raised";
}
function paradaDotClass(p) {
  if (p.receipt_validated) return "bg-green-500 text-white";
  if (p.transfer_done) return "bg-brand-500 text-white";
  if (p.sco) return "bg-brand-200";
  return "bg-surface-raised";
}
function paradaEstadoTexto(p) {
  return { done: "Recibido", transfer: "Material enviado", sco: "Encargo creado", pending: "Pendiente de encargar" }[paradaEstado(p)];
}
function paradaEstadoColor(p) {
  return { done: "text-green-700", transfer: "text-brand-700", sco: "text-brand-700", pending: "text-ink-light" }[paradaEstado(p)];
}
// Cantidad por producto de una parada, en corto: "Playera 1500 · Camisa 1000".
// Usa la 1ª palabra del nombre (el tipo de prenda) -- si dos productos empiezan
// igual, cae al nombre completo para no confundir.
function paradaProductosTexto(productos) {
  const rows = (productos || []).filter((x) => x.qty > 0);
  if (!rows.length) return "sin cantidad";
  const primeras = rows.map((x) => (x.item_name || x.finished_item).split(" ")[0]);
  const ambiguo = new Set(primeras).size < primeras.length;
  return rows.map((x, i) => `${ambiguo ? (x.item_name || x.finished_item) : primeras[i]} ${x.qty}`).join(" · ");
}
function rfqDeProveedor(lote, supplier) { return (lote?.material_rfqs || []).find((r) => r.supplier === supplier); }
function sqDeProveedor(lote, supplier) { return (lote?.material_sqs || []).find((r) => r.supplier === supplier); }
// Acordeón: qué proveedor+documento está desplegado en la pantalla del lote (uno a
// la vez) -- clic en un botón lo abre (creando el documento si aún no existe) o lo
// cierra si ya estaba abierto.
const loteDocOpen = reactive({ supplier: null, tab: null });
/** Carga el documento de un paso del proveedor. Con `crear`, lo genera si no existe.
 *
 *  Moverse por el stepper NO crea nada: cada paso tiene su propio botón ("Generar
 *  orden de compra", "Crear recibo de compra"…) en el pie del panel. Antes se creaba
 *  al entrar al paso, y eso hacía que pasar por ahí de curioso dejara documentos
 *  sueltos -- con el riesgo de duplicarlos si se volvía a entrar. */
async function toggleLoteDoc(lote, grp, tab, { crear = false } = {}) {
  if (loteDocOpen.supplier === grp.supplier && loteDocOpen.tab === tab) {
    loteDocOpen.supplier = null;
    loteDocOpen.tab = null;
    return;
  }
  loteDocOpen.supplier = grp.supplier;
  loteDocOpen.tab = tab;
  if (tab === "rfq") {
    const existing = rfqDeProveedor(lote, grp.supplier);
    if (existing) await selectRfq(existing.name);
    else if (crear) await crearRfqLote(lote, grp.supplier);
  } else if (tab === "sq") {
    const existing = sqDeProveedor(lote, grp.supplier);
    if (existing) await selectSq(existing.name);
    else if (crear) await crearSqLote(lote, grp.supplier);
  } else if (tab === "oc") {
    if (grp.po) { mrDocTab.value = "oc"; await selectOC(grp.po.name); }
    else if (crear) await generarOcLote(lote, grp.supplier);
  } else if (tab === "recibo") {
    // selectReciboLote crea el recibo si la OC no lo tiene: solo se le deja hacerlo
    // cuando lo pidió el botón.
    if (grp.po?.docstatus === 1 && (grp.po.receipt || crear)) await selectReciboLote(grp.po);
  } else if (tab === "factura") {
    // Con varios recibos, la factura junta todos los validados sin facturar (ver
    // crear_factura_compra): cualquiera de ellos sirve de punto de partida.
    const fuente = grp.po?.ultimo_recibo_validado || grp.po?.receipt?.name;
    if (fuente) await abrirFacturaFuente("Purchase Receipt", fuente, grp.supplier);
  }
}

// Subcontratación de la etapa activa: mismo patrón de 4 botones desplegables que
// materia prima, pero con el flujo real de subcontratación -- Orden de compra (la OC
// validada con el taller) / Orden de subcontratación (SCO, por lote) / Transferencia
// de material / Recibo de subcontratación. Sólo se puede tener uno abierto a la vez;
// el que corresponde según lo ya avanzado se abre solo al cambiar de etapa.
const subStepOpen = ref("sco");
function subStepDefaultFor(parada) {
  // "oc" dejó de ser un paso del taller (ahora es el panel "Orden de compra" del
  // encabezado): sin OC validada el primer paso sigue siendo el encargo, y la barra
  // se encarga de bloquearlo con su motivo.
  if (!parada || parada.po_docstatus !== 1) return "sco";
  if (parada.sco_docstatus !== 1) return "sco";
  if (!parada.transfer_done) return "transfer";
  return "recibo";
}
// Si se entra a "Orden de subcontratación" de una parada de un lote que todavía no
// tiene cantidad establecida (nació de materia prima), se sugiere una según el stock.
async function maybeSugerirPrimeraEtapaQty() {
  const p = paradaActiva.value;
  const sinCantidad = p && !p.sco
    && !p.productos.some((x) => x.qty > 0)
    && !(loteActivo.value?.productos || []).some((x) => x.qty > 0);
  if (subStepOpen.value === "sco" && sinCantidad) await sugerirPrimeraEtapaQty(p);
}
watch(() => `${loteActivoRef.value}::${loteParadaActiva.value}`, async () => {
  if (!loteParadaActiva.value) return;
  subStepOpen.value = subStepDefaultFor(paradaActiva.value);
  await maybeSugerirPrimeraEtapaQty();
});
// La OC de subcontratación de cada taller se crea UNA VEZ (plan_crear_subcontratacion)
// -- si el lote se armó primero por materia prima, al entrar aquí puede no existir
// todavía; se ofrece crearla sin salir de la pantalla del lote.
async function crearSubcontratosDesdeLote() {
  await crearSubcontratos();
  // Se quedan en Borrador a propósito: cada orden se revisa (proveedor, IVA, fechas)
  // y se valida a mano desde su panel. Se abre la primera para empezar.
  await loadLotesProduccion();
  const primera = subOcs.value.find((o) => o.docstatus === 0);
  if (primera) await abrirOcTaller(primera);
  // Antes de crear las OC de subcontrato el lote no tenía ninguna parada, así
  // que loteParadaActiva seguía vacío -- sin este fallback, tras crearlas la
  // pantalla se habría quedado igual de "en blanco" (paradaActiva nunca se
  // vuelve a fijar solo). Se abre la primera parada pendiente, igual que
  // seleccionarLote.
  const lote = loteActivo.value;
  const p2 = lote?.paradas.find((x) => x.parada_id === loteParadaActiva.value)
    || siguienteParadaPendiente(lote);
  if (p2) await seleccionarParada(p2);
}
const showAcordadoModal = ref(false);
const acordadoValidUpto = ref("");
const precioAcordadoStatus = reactive({ items: [], todos_validados: false, es_ceo: false });
const showRechazarModal = ref(false);
const rechazarMotivo = ref("");
const showRevisionModal = ref(false);
const revisionMotivo = ref("");
const revisionCreating = ref(false);
const showHistorialModal = ref(false);
const siguienteCosteo = ref(null);
async function loadRevisionInfo() {
  siguienteCosteo.value = null;
  if (!docName.value) return;
  try {
    const r = await call("costeo_yelke.api.costeo_api.get_revisiones_costeo", { costeo: docName.value });
    siguienteCosteo.value = r?.siguiente || null;
  } catch { /* no bloquear la carga por esto */ }
}

// ── Computed ──
// Nombre Comercial del cliente en el subtítulo del encabezado (form.cliente es el
// Link crudo -- LinkInput ya resuelve esto para su propio campo, pero el
// subtítulo es texto aparte, ver getLinkDisplayLabel).
const clienteDisplayName = ref("");
watch(() => form.cliente, async (val) => {
  clienteDisplayName.value = val ? ((await getLinkDisplayLabel("Customer", val)) || val) : "";
}, { immediate: true });
const headerSubtitle = computed(() => isNew.value ? "Completa los datos del costeo" : [form.titulo && docName.value, clienteDisplayName.value].filter(Boolean).join(" · "));
const totalVenta = computed(() => productos.value.reduce((s, p) => s + (p.total_sales_price || 0), 0));

// El menú de acciones (⋮) y la insignia de estado del header deben corresponder al
// documento que se está viendo según el paso activo del stepper, no siempre al Costeo
// -- si no, "Cancelar validación" o "Imprimir" desde el paso "Cotizar" actuaría sobre
// el Costeo en vez de sobre la cotización, que es justo lo que se ve en pantalla.
// "Producir" no tiene un único documento (son varios: OM, orden de subcontratación,
// transferencia, recibo), así que ahí no se muestra menú de documento.
const headerDoc = computed(() => {
  if (isNew.value) return null;
  const step = activeStep.value;
  if (step === 0) return { doctype: "Costeo", name: docName.value, docstatus: docState.value, isCosteo: true };
  if (step === 1 && related.quotation) return { doctype: "Quotation", name: related.quotation.name, docstatus: related.quotation.docstatus, isCosteo: false };
  if (step === 2 && related.sales_order) return { doctype: "Sales Order", name: related.sales_order.name, docstatus: related.sales_order.docstatus, isCosteo: false };
  if (step === 5 && dnDoc.value) return { doctype: "Delivery Note", name: dnDoc.value.name, docstatus: dnDoc.value.docstatus, isCosteo: false };
  if (step === 7 && related.sales_invoice) return { doctype: "Sales Invoice", name: related.sales_invoice.name, docstatus: related.sales_invoice.docstatus, isCosteo: false };
  return null;
});

// Un costeo validado o cancelado ya no debe poder editarse desde aquí -- si necesita
// ajustes, el camino es crear una revisión (que sí queda editable). Sin este candado,
// el usuario podía seguir tocando campos de un costeo "cerrado" sin ningún botón para
// guardar esos cambios, lo cual es confuso (parece editable pero no pasa nada).
const canEditCosteo = computed(() => isNew.value || docState.value === 0);

// Estando YA parado en "Alta de Productos" o "Flujo de Producción" (activeStep 3 o
// 4 -- las dos vistas de la preparación de manufactura), el botón principal deja de
// ofrecer "ir a Preparar manufactura" (redundante, ya estás ahí) y pasa a ofrecer el
// siguiente paso real: crear los documentos de producción. canAdvanceCta sigue
// exigiendo manufacturaGuardada, así que en "Alta de Productos" el botón se ve pero
// queda deshabilitado hasta guardar el flujo en el siguiente paso.
// Qué vista pide cada botón principal: los que CREAN algo piden editar; los que solo
// llevan a otro paso, verlo (accesos por vista).
const ACCESO_CTA = {
  cotizar: [["cotizar"], "editar"], vender: [["vender"], "editar"],
  ir_preparar_manufactura: [["alta"], "ver"], pasar_produccion: [["flujo_produccion", "preparacion"], "editar"],
  enviar: [["entrega"], "ver"], facturar: [["facturar"], "ver"],
};
const cta = computed(() => {
  const c = ctaBase.value;
  if (!c || !ACCESO_CTA[c.action]) return c;
  const [vistas, nivel] = ACCESO_CTA[c.action];
  return vistas.some((v) => puedeAcceso(v, nivel)) ? c : null;
});
const ctaBase = computed(() => {
  if (docStatus.value === "Orden de Venta" && (activeStep.value === 3 || activeStep.value === 4)) {
    return { label: "Pasar a producción", action: "pasar_produccion" };
  }
  return ({
    "Borrador":       { label: "Pasar a cotización",        action: "cotizar" },
    "Cotizado":       { label: "Generar orden de venta",    action: "vender" },
    "Orden de Venta": { label: "Alta de productos",         action: "ir_preparar_manufactura" },
    "En Producción":  { label: "Registrar entrega",         action: "enviar" },
    "Entregado":      { label: "Ir a facturar",             action: "facturar" },
    "Completado":     null,
  }[docStatus.value] || null);
});

const checklist = computed(() => {
  const items = [
    { label: "Cliente y compañía", ok: !!(form.cliente && form.compania) },
    { label: "Al menos un producto con cantidad", ok: productos.value.some(p => p.finished_item && (p.qty || 0) > 0) },
  ];
  if (docStatus.value === "Orden de Venta") {
    items.push({ label: "Almacenes configurados", ok: !!(form.almacen_materias_primas && form.almacen_trabajo_en_proceso) });
    items.push({ label: "Materias primas con proveedor", ok: detalles.value.filter(d => d.concept_type === "Materia Prima" && d.item).every(d => d.supplier) });
    items.push({ label: "Etapas con servicio y proveedor", ok: etapas.value.every(e => e.servicio && e.proveedor) });
  }
  if (docStatus.value === "En Producción") {
    items.push({ label: `Producción terminada — recibos de subcontratación (${prodComplete.recibidas}/${prodComplete.total})`, ok: prodComplete.complete });
  }
  return items;
});
// No se puede avanzar sin validar el documento de la fase actual.
const phaseReady = computed(() => {
  if (docStatus.value === "Borrador") return docState.value === 1;              // costeo validado
  if (docStatus.value === "Cotizado") return quotValidated.value; // cotización validada y no rechazada
  // Ahora que Producción es por OV (no por costeo completo), lo que debe estar
  // validado es la OV ACTIVA -- puede haber varias OV bajo el mismo costeo y no
  // necesariamente la más reciente es la que se va a producir.
  if (docStatus.value === "Orden de Venta") return activeSO.value?.docstatus === 1;
  if (docStatus.value === "En Producción") return prodComplete.complete;  // toda la maquila recibida
  return true;
});
const canAdvance = computed(() => checklist.value.every(i => i.ok) && phaseReady.value);
// "Preparar manufactura" solo cambia de pestaña (ver advance()) -- no crea ni
// valida ningún documento, así que no debe esperar el checklist completo. En
// particular, "Etapas con servicio y proveedor" ya no tiene sentido como
// requisito PREVIO a "Preparar manufactura": ese es justo el paso donde las
// etapas se arman (agregar/quitar, asignar servicio) -- exigirlas antes de
// poder entrar bloqueaba el botón aunque la OV ya estuviera validada.
// "Registrar entrega" (enviar) NO entra en esta excepción de "sin checklist" --
// antes se dejaba pasar siempre (bug reportado: el botón se desbloqueaba sin
// haber recibido nada de producción todavía). Pero tampoco debe esperar el
// 100% (canAdvance/prodComplete.complete): las remisiones son POR LOTE, así que
// basta con que al menos un lote ya esté recibido para poder ir registrando
// entregas parciales conforme van llegando -- exigir el 100% aquí bloquearía
// ese flujo de entregas parciales a propósito soportado en "Enviar".
const canAdvanceCta = computed(() => {
  const action = cta.value?.action;
  // Preparar manufactura solo con la OV activa validada: sin eso se saltaba Vender.
  if (action === "ir_preparar_manufactura") return soValidated.value;
  // Solo con prendas TERMINADAS recibidas (la última etapa): recibir el corte o
  // cualquier etapa intermedia no deja nada que entregar al cliente.
  if (action === "enviar") return (prodComplete.lotes_terminados || 0) > 0;
  // En "Flujo de Producción" (paso 4) el botón "Confirmar" se persiste solo -- no
  // exige un guardado previo. En "Alta de Productos" (paso 3) sí, porque el flujo
  // todavía no se ha revisado.
  if (action === "pasar_produccion") return activeStep.value === 4 || manufacturaGuardada.value;
  return canAdvance.value;
});
// Validada y NO rechazada: una cotización rechazada se queda en el historial del
// costeo y no puede pasar a orden de venta.
const quotValidated = computed(() => related.quotation?.docstatus === 1 && related.quotation?.status !== "Lost");
// La OV "activa" (elegida en el acordeón de Vender) es la que filtra Producir,
// Enviar, Facturar y Reportar -- por default es la más reciente (activeSOName se
// inicializa así en loadRelated), pero se puede cambiar sin perder cuál está
// expandida en el acordeón.
const activeSO = computed(() => related.sales_orders.find(s => s.name === activeSOName.value) || null);
const soValidated = computed(() => activeSO.value?.docstatus === 1);
// Cambiar la OV activa recarga todo lo que depende de ella: el plan/producción
// (Producir tiene un plan POR OV, ver get_plan_detail), el avance de maquila
// (Facturar se desbloquea por OV) y, si ya se está viendo, el Reporte -- así el
// selector persistente de OV activa (Producir/Enviar/Facturar/Reportar) se siente
// instantáneo en vez de tener que recargar la página. Se salta la primera vez que se
// asigna (transición desde null) porque loadCosteoData ya carga esos datos explícito
// para la OV inicial -- solo hace falta recargar cuando el usuario CAMBIA de OV activa.
watch(activeSOName, async (name, oldName) => {
  if (!name || oldName == null) return;
  loteActivoRef.value = ""; // los lotes son por OV -- no tiene sentido seguir viendo uno de la OV anterior
  if (activeStep.value === 5) prodRuta.reiniciar();
  await Promise.all([
    loadPlan(docName.value, name),
    loadProdComplete(docName.value, name),
  ]);
  if (activeStep.value === 8) await loadReporte();
});
function setActiveSO(name) { if (soVivas.value.some(s => s.name === name)) activeSOName.value = name; }
const siValidated = computed(() => related.sales_invoice?.docstatus === 1);
const dnValidated = computed(() => dnDoc.value?.docstatus === 1);
// Se puede crear otra remisión (a otra dirección) si la OV no está 100% entregada y no
// hay ya un borrador de remisión sin validar esperando (evita mapear el mismo saldo dos veces).
const puedeNuevaRemision = computed(() =>
  activeSO.value?.docstatus === 1 &&
  (related.delivery_per_delivered || 0) < 99.99 &&
  !related.delivery_notes.some(d => d.docstatus === 0)
);
const pinvValidated = computed(() => pinvDoc.value?.docstatus === 1);
function facBadge(inv) {
  if (!inv) return { txt: "Sin factura", cls: "bg-gray-100 text-gray-500" };
  return inv.docstatus === 1 ? { txt: "Validada", cls: "bg-green-50 text-green-700" } : { txt: "Borrador", cls: "bg-amber-50 text-amber-700" };
}

// ── Helpers ──
let _seq = 0;
function uid() { return `_${++_seq}_${Date.now()}`; }
function today() { return new Date().toISOString().slice(0, 10); }
// Tope de la fecha de la remisión: hoy en la hora local (sin fechas futuras, ver
// contabilidad.sin_fecha_futura).
const hoyLocal = new Date().toLocaleDateString("en-CA");
function fmtC(v) { return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(v || 0); }
// ── Accesos por vista (composables/useAccesos.js) ──
// Claves de CosteoStepper, en el mismo orden que activeStep.
const STEP_KEYS = ["costear", "cotizar", "vender", "preparar_manufactura", "flujo_manufactura", "producir", "enviar", "facturar", "reportar"];
const { estado: accesosEstado, puede: puedeAcceso, puedeEditar, pasoVisible, pasoEditable } = useAccesos();
const accesosListos = computed(() => accesosEstado.cargado);
const pasosPermitidos = computed(() => STEP_KEYS.filter((k) => k !== "enviar" && pasoVisible(k)));
/** El paso actual solo se consulta: la etapa está en "ver". */
const soloLecturaPaso = computed(() => accesosListos.value && !isNew.value && !pasoEditable(STEP_KEYS[activeStep.value]));
/** El paso permitido más cercano: el anterior más próximo o, si no hay, el primero. */
function pasoPermitidoCercano(idx) {
  const ok = pasosPermitidos.value.map((k) => STEP_KEYS.indexOf(k));
  if (!ok.length || ok.includes(idx)) return idx;
  return [...ok].reverse().find((i) => i <= idx) ?? ok[0];
}
// Al abrir el proyecto (o con ?step=) en un paso que no tiene, cae en el más cercano.
watch([activeStep, accesosListos, () => pasosPermitidos.value.join()], () => {
  if (!accesosListos.value || isNew.value) return;
  const destino = pasoPermitidoCercano(activeStep.value);
  if (destino !== activeStep.value) goStep(destino);
});
function goStep(idx) {
  if (accesosListos.value && !isNew.value && !pasosPermitidos.value.includes(STEP_KEYS[idx])) return;
  activeStep.value = idx;
  if (idx === 8) loadReporte();
  if (idx === 4) loadFlujoOps();
  // Producción recuerda dónde te quedaste (menú, lote, paso); los demás pasos no
  // tienen lote, así que se suelta el que estuviera abierto.
  if (idx === 5) restaurarVistaProduccion();
  else loteActivoRef.value = "";
}
// ── Encargos (api/encargos.py, docs/plan-encargos.md) ──
const encargos = ref([]);
const encargosPanel = reactive({ abierto: false, paso: "", lote: "" });
const encargosAbiertos = computed(() => encargos.value.filter((f) => f.estado === "abierto").length);
async function cargarEncargos() {
  if (isNew.value || !docName.value) { encargos.value = []; return; }
  try { encargos.value = (await getDelProyecto(docName.value)).encargos || []; } catch { /* opcional */ }
}
watch(versionEncargos, cargarEncargos);
// Avanzar el proyecto (confirmar flujo, validar, cambiar de paso) puede cerrar una
// asignación en el servidor: la franja se vuelve a pedir.
watch(() => [docStatus.value, activeStep.value], () => { if (!isNew.value) cargarEncargos(); });
/** El paso (vista) que se está viendo, para proponerlo al encargar. */
function vistaActualParaEncargo() {
  const porPaso = { 0: "costear", 1: "cotizar", 2: "vender", 3: "alta", 4: "flujo_produccion", 7: "facturar", 8: "reporte" };
  if (activeStep.value !== 5) return porPaso[activeStep.value] || "";
  const q = route.query;
  if (q.vista === "lote") return { materia: "materia", talleres: "talleres", flujo: "talleres", entrega: "entrega" }[q.paso] || "talleres";
  if (q.vista === "preparacion") return { 2: "materia", 3: "om" }[q.prep] || "preparacion";
  return { ordenes: "preparacion", envios: "envios", facturas: "facturas", om: "om" }[q.vista] || "tablero";
}
function abrirEncargos(paso) {
  encargosPanel.paso = paso ?? vistaActualParaEncargo();
  encargosPanel.lote = String(route.query.lote || route.query.filtro_lote || loteActivoRef.value || "");
  encargosPanel.abierto = true;
}
/** "Abrir" un encargo propio desde la franja: va a su paso sin salir del proyecto. */
async function irAMiEncargo(f) {
  const q = Object.fromEntries(new URL(f.ruta, location.origin).searchParams);
  const step = Number(q.step ?? activeStep.value);
  delete q.step; delete q.compania;
  if (step === 5) await router.replace({ path: route.path, query: q });
  goStep(step);
}

// Recuerda DÓNDE te quedaste en Producción para que un refresh o volver a abrir el
// costeo regrese justo ahí. Ya no es solo el lote: la vista completa (menú, paso,
// taller) vive en la URL y se recuerda por costeo + OV -- ver useProduccionRuta.
watch(() => [activeStep.value, route.query.vista, route.query.lote, route.query.paso,
             route.query.parada, route.query.tpaso, route.query.seg], () => {
  if (activeStep.value !== 5 || isNew.value) return;
  prodRuta.recordar();
});

// ── Filters ──
function materialesDe(fi) { return detalles.value.filter(d => d.finished_item === fi && d.concept_type === "Materia Prima"); }
function etapasDe(fi) { return etapas.value.filter(e => e.producto_terminado === fi); }

// ═══════════════════════════════════════════════════════════════════════
// "Puntos" del proceso -- agrupa en Costear las etapas que comparten taller,
// para capturar en un solo lugar los servicios Y la materia prima de cada
// punto (en vez de dos tablas sueltas). Es puramente de PRESENTACIÓN: por
// debajo se sigue guardando exactamente lo mismo que antes -- un renglón de
// `tabla_etapas_costeo` por servicio (con su propio proveedor/precio/recibe_de,
// idénticos entre sí dentro de un mismo punto) y `tabla_materiales_etapa` para
// la materia prima asignada -- así Flujo de Producción (que arma BOMs y todo
// lo demás) no necesita saber que este agrupador existe: sigue leyendo los
// mismos campos de siempre, capturados aquí de otra forma.
//
// `_grupo_id` es un campo SOLO del cliente (nunca se manda al backend --
// stripLocal() ya quita todo lo que empieza con "_"), así que un costeo viejo
// que se vuelva a abrir en otra sesión no pierde nada: se re-calcula solo al
// cargar (ver asignarGruposEtapas).
function puntosDe(fi) {
  const grupos = [];
  const porId = new Map();
  for (const e of etapasDe(fi)) {
    let g = porId.get(e._grupo_id);
    if (!g) { g = { grupo_id: e._grupo_id, servicios: [] }; porId.set(e._grupo_id, g); grupos.push(g); }
    g.servicios.push(e);
  }
  return grupos;
}
// Costeos ya guardados no traen _grupo_id -- se reconstruye agrupando etapas
// CONSECUTIVAS del mismo producto que comparten proveedor y "recibe de"
// (exactamente el criterio con el que el backend ya las fusiona en una sola
// tarjeta en Flujo de Producción), así el árbol nuevo muestra de entrada lo
// mismo que ya se veía fusionado allá.
function asignarGruposEtapas() {
  const porProducto = {};
  for (const e of etapas.value) { (porProducto[e.producto_terminado] ||= []).push(e); }
  for (const fi in porProducto) {
    let prevKey = null, grupoId = null;
    for (const e of porProducto[fi]) {
      const key = `${e.proveedor || ""}||${e.recibe_de || ""}`;
      if (key !== prevKey) { grupoId = uid(); prevKey = key; }
      e._grupo_id = grupoId;
    }
  }
}
// El "recibe de" NO se toca aquí -- se deja siempre vacío. Con todas las
// etapas de un producto en blanco, el backend usa su propio "modo lineal"
// (una cadena recta en el orden en que se capturaron) como default -- Costear
// no necesita calcular ni repetir esa lógica. Ajustar el orden real del flujo
// (arranques en paralelo, uniones) es trabajo de Flujo de Producción.
function addPunto(prod) {
  const fi = prod.finished_item;
  const next = etapasDe(fi).length + 1;
  etapas.value.push({
    _tid: uid(), _grupo_id: uid(), producto_terminado: fi, etapa: String(next), stage_id: genStageId(),
    recibe_de: "", servicio: "", proveedor: "", precio_servicio: 0,
    lote_qty: 1, lote_uom: "H87 - Pieza", modo_precio: "Por operación", operaciones_por_pieza: 1,
    precio_por_operacion: 0, subensamblaje: "",
  });
  manufacturaGuardada.value = false;
}
// Un servicio más DENTRO del mismo punto: mismo proveedor, mismo "recibe de"
// -- es justo la combinación que el backend fusiona en una sola tarjeta.
function addServicioAPunto(punto, prod) {
  const anchor = punto.servicios[0];
  const next = etapasDe(prod.finished_item).length + 1;
  etapas.value.push({
    _tid: uid(), _grupo_id: punto.grupo_id, producto_terminado: prod.finished_item, etapa: String(next),
    stage_id: genStageId(), recibe_de: anchor.recibe_de, servicio: "", proveedor: anchor.proveedor,
    precio_servicio: 0, lote_qty: 1, lote_uom: "H87 - Pieza", modo_precio: "Por operación",
    operaciones_por_pieza: 1, precio_por_operacion: 0, subensamblaje: "",
  });
  manufacturaGuardada.value = false;
}
// El proveedor se edita una sola vez, arriba del punto -- se propaga a todos
// los servicios del grupo (todos deben compartirlo; es lo que los mantiene
// fusionados como un solo punto).
function setPuntoProveedor(punto, valor) {
  punto.servicios.forEach(e => { e.proveedor = valor; });
  cargarServiciosProveedor(valor);
}
// Servicios registrados a cada taller (costeo_api.servicios_de_proveedor): con el taller
// ya elegido, el buscador de servicios del paso muestra solo los suyos. Si no tiene
// ninguno registrado se ofrecen todos, y el texto libre se puede usar siempre.
const serviciosPorProveedor = reactive({});
async function cargarServiciosProveedor(proveedor) {
  if (!proveedor || serviciosPorProveedor[proveedor]) return;
  serviciosPorProveedor[proveedor] = [];
  try {
    serviciosPorProveedor[proveedor] = await call("costeo_yelke.api.costeo_api.servicios_de_proveedor", { supplier: proveedor }) || [];
  } catch { /* sin filtro: se ofrecen todos */ }
}
function serviciosDelPunto(punto) { return serviciosPorProveedor[punto.servicios[0]?.proveedor] || []; }
function filtrosServicio(punto) {
  const suyos = serviciosDelPunto(punto);
  return suyos.length ? [...ITEM_FILTERS.servicio, ["name", "in", suyos]] : ITEM_FILTERS.servicio;
}
function placeholderServicio(punto) {
  return serviciosDelPunto(punto).length ? "Servicio de este taller…" : "Servicio…";
}
function removeServicioDePunto(e, punto, prod) {
  // Si se borra el ANCLA de un punto con más de un servicio, primero hay que
  // migrarle sus referencias (materia prima asignada, y quién "recibe de" él)
  // al que va a quedar como nueva ancla -- si no, se pierden colgadas.
  if (punto.servicios.length > 1 && punto.servicios[0]._tid === e._tid) {
    const nuevaAncla = punto.servicios[1];
    materialesEtapa.value.forEach(r => { if (r.stage_id === e.stage_id) r.stage_id = nuevaAncla.stage_id; });
    etapas.value.forEach(et => {
      const ids = (et.recibe_de || "").split(",").map(s => s.trim()).filter(Boolean);
      if (ids.includes(e.stage_id)) et.recibe_de = ids.map(id => id === e.stage_id ? nuevaAncla.stage_id : id).join(",");
    });
  }
  removeEtapa(e, prod);
}
function removePunto(punto, prod) {
  [...punto.servicios].forEach(e => removeServicioDePunto(e, punto, prod));
}
// Materia prima asignada a este punto (vive en materialesEtapa, igual que en
// Flujo de Producción -- solo que aquí se captura desde que se arma el costeo).
function materialesDelPunto(punto) {
  const stageId = punto.servicios[0]?.stage_id;
  if (!stageId) return [];
  return materialesEtapa.value
    .filter(r => r.stage_id === stageId)
    .map(r => detalles.value.find(d => d.material_id === r.material_id))
    .filter(Boolean);
}
// Materiales del producto que todavía no se asignaron a ningún punto -- siguen
// funcionando "automático" (se atribuyen solos al arranque del flujo), igual
// que si nunca se hubiera tocado nada.
function materialesSinPunto(fi) {
  const asignados = new Set(materialesEtapa.value.map(r => r.material_id));
  return materialesDe(fi).filter(d => !asignados.has(d.material_id));
}
function addMaterialAPunto(punto, prod) {
  addDetalle(prod, "Materia Prima");
  const nuevo = detalles.value[detalles.value.length - 1];
  materialesEtapa.value.push({ _tid: uid(), material_id: nuevo.material_id, stage_id: punto.servicios[0].stage_id, qty: 0 });
}
// Resuelve un material "pendiente" (de un costeo capturado antes de este árbol)
// asignándolo a un punto ya existente -- misma mecánica que addMaterialAPunto,
// sin crear un material nuevo.
function asignarMaterialAPunto(d, prod, grupoId) {
  const punto = puntosDe(prod.finished_item).find(p => p.grupo_id === grupoId);
  if (!punto) return;
  materialesEtapa.value.push({ _tid: uid(), material_id: d.material_id, stage_id: punto.servicios[0].stage_id, qty: d.internal_qty || 0 });
}

// ── Reparto de un material entre varias etapas ──
// El consumo capturado en el costeo (internal_qty, "Consumo por pieza") es el total
// que lleva UNA pieza de producto terminado. Cuando ese insumo lo aplican dos
// operaciones distintas (ej. 4 de cinta reflejante: 2 en la manga, 2 en el frente)
// hace falta decir cuánto va en cada etapa -- eso vive en materialesEtapa y es lo
// que crear_boms_spa usa como cantidad de cada BOM.
function matTotal(m) { return Number(m.internal_qty) || 0; }
// 'etapa' (escalar, dato viejo) se mantiene apuntando a la PRIMERA etapa asignada:
// es el respaldo que usa crear_boms_spa para los costeos que nunca declararon
// reparto, y dejarlo desincronizado haría que un costeo viejo reabierto y guardado
// cambiara de comportamiento sin que nadie lo tocara.
function syncMaterialEtapaEscalar(m) {
  const primera = materialesEtapa.value.find(r => r.material_id === m.material_id);
  m.etapa = primera ? primera.stage_id : "";
}
// Costeos guardados antes del reparto explícito: su único dato es el escalar
// 'etapa' (stage_id nuevo, o número de etapa en los más viejos). Se convierte a
// filas al abrir para que el diagrama tenga una sola fuente de verdad; el backend
// mantiene el mismo respaldo por si el costeo nunca se reabre.
function migrarMaterialesEtapaLegado() {
  if (materialesEtapa.value.length) return;
  detalles.value.forEach(m => {
    if (m.concept_type !== "Materia Prima" || !m.etapa) return;
    const candidatas = etapasDe(m.finished_item);
    const etapa = candidatas.find(e => e.stage_id === m.etapa) || candidatas.find(e => String(e.etapa || "") === String(m.etapa));
    if (!etapa) return;
    materialesEtapa.value.push({ _tid: uid(), material_id: m.material_id, stage_id: etapa.stage_id, qty: matTotal(m) });
    m.etapa = etapa.stage_id;
  });
}
function genStageId() { return Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4); }


// ── Product / detail / stage ──
function addProducto() { const p = { _tid: uid(), _lastFinishedItem: "", image: "", description: "", finished_item: "", variante_talla_de: "", talla_grupo_label: "", qty: 1, shipping_cost: 0, labeling_cost: 0, packaging_cost: 0, overhead_pct: 0, margin_pct: 0, material_cost: 0, services_cost: 0, overhead_amt: 0, total_unit_cost: 0, unit_sales_price: 0, precio_manual: 0, total_sales_price: 0 }; productos.value.push(p); expandedTids.add(p._tid); }
function directCost(prod) { return (prod.material_cost || 0) + (prod.services_cost || 0) + (prod.shipping_cost || 0) + (prod.labeling_cost || 0) + (prod.packaging_cost || 0); }
// Desglose informativo de directCost por grupo -- telas y avíos son subconjuntos
// de material_cost (según tipo_material de cada renglón), servicios agrupa todo
// lo que no es materia prima (etapas de manufactura + materiales tipo "Servicio"
// + flete/etiquetado/empaquetado), así telas+avios+servicios siempre suma directCost.
function telasCost(prod) { return materialesDe(prod.finished_item).filter(d => d.tipo_material === "Tela").reduce((s, d) => s + (d.total || 0), 0); }
// Avíos = el resto de material_cost (no solo lo marcado tipo_material === "Avío"),
// así Telas + Avíos siempre cuadra con material_cost aunque algún renglón tenga
// el Tipo sin seleccionar todavía -- no se pierde ese costo del desglose.
function aviosCost(prod) { return (prod.material_cost || 0) - telasCost(prod); }
function serviciosCost(prod) { return (prod.services_cost || 0) + (prod.shipping_cost || 0) + (prod.labeling_cost || 0) + (prod.packaging_cost || 0); }
// Telas / Avíos / Servicios y otros por pieza, con su parte del todo para la barra de
// "Composición por pieza" (paleta validada del tablero, components/tablero).
function composicionCosto(prod) {
  const partes = [
    { etiqueta: "Telas", monto: telasCost(prod), color: "#2a78d6" },
    { etiqueta: "Avíos", monto: aviosCost(prod), color: "#eb6834" },
    { etiqueta: "Servicios y otros", monto: serviciosCost(prod), color: "#1baf7a" },
  ];
  const total = partes.reduce((s, c) => s + Math.max(0, c.monto), 0);
  return partes.map((c) => ({ ...c, pct: total ? (Math.max(0, c.monto) / total) * 100 : 0 }));
}
// Totales de las dos tablas del costeo, por PIEZA (el x cantidad se muestra aparte).
// Se calculan sobre las mismas filas que se ven en pantalla, así que siempre cuadran
// con lo listado aunque haya renglones a medio capturar.
function totalMaterias(prod) {
  return round2(materialesDe(prod.finished_item).reduce((s, d) => s + (Number(d.total) || 0), 0));
}
function totalEtapas(prod) {
  return round2(etapasDe(prod.finished_item).reduce((s, e) => s + precioPorPiezaEtapa(e), 0));
}
function expectedProfit(prod) { return (prod.unit_sales_price || 0) - (prod.total_unit_cost || 0); }
function removeProducto(idx) { const prod = productos.value[idx]; if (!prod) return; const stageIdsDeProd = new Set(etapas.value.filter(e => e.producto_terminado === prod.finished_item).map(e => e.stage_id)); const materialIdsDeProd = new Set(detalles.value.filter(d => d.finished_item === prod.finished_item).map(d => d.material_id)); detalles.value = detalles.value.filter(d => d.finished_item !== prod.finished_item); etapas.value = etapas.value.filter(e => e.producto_terminado !== prod.finished_item); materialesEtapa.value = materialesEtapa.value.filter(r => !materialIdsDeProd.has(r.material_id) && !stageIdsDeProd.has(r.stage_id)); tallas.value = tallas.value.filter(t => t.finished_item !== prod.finished_item); productos.value.splice(idx, 1); expandedTids.delete(prod._tid); }
function toggleProduct(tid) { if (expandedTids.has(tid)) expandedTids.delete(tid); else expandedTids.add(tid); }
// Materiales, etapas y tallas se vinculan al producto por el VALOR de finished_item
// (son tablas hermanas, no anidadas -- Frappe no guarda tablas dentro de tablas), no
// por la fila del producto en sí. Si aquí solo se actualizara prod.finished_item,
// esas filas se quedarían apuntando al valor viejo: se desconectan de la vista de
// inmediato (los filtros de esta página buscan por el valor ACTUAL) y, peor, se
// BORRAN al guardar (cleanup_orphan_children las trata como huérfanas de un
// producto eliminado). Por eso hay que reescribirlas en cascada al mismo valor
// nuevo -- es un cambio de nombre del mismo producto, no borrar uno y crear otro.
async function onProductoItemChange(prod) {
  const anterior = prod._lastFinishedItem;
  const nuevo = prod.finished_item;
  if (anterior && nuevo && anterior !== nuevo) {
    detalles.value.forEach(d => { if (d.finished_item === anterior) d.finished_item = nuevo; });
    etapas.value.forEach(e => { if (e.producto_terminado === anterior) e.producto_terminado = nuevo; });
    tallas.value.forEach(t => { if (t.finished_item === anterior) t.finished_item = nuevo; });
    // tabla_materiales_etapa se vincula por stage_id (de las etapas), no directo
    // por finished_item, así que no necesita reescritura aquí.
  }
  prod._lastFinishedItem = nuevo;
  recalcProducto(prod);
  const fetched = await fetchItemImage(prod.finished_item);
  if (fetched) prod.image = fetched;
}
// La imagen se elige desde aquí (aunque el producto todavía sea texto libre) para que
// ya esté lista cuando se materialice el Item real al pasar a cotización. DialogoImagen
// acepta archivo, imagen pegada o enlace (que el servidor descarga).
const imagenEnEdicion = ref(null);
function pickImage(prod) {
  if (!canEditCosteo.value) return;
  imagenEnEdicion.value = prod;
}
function aplicarImagen(url) {
  if (imagenEnEdicion.value) imagenEnEdicion.value.image = url || "";
  imagenEnEdicion.value = null;
}
function addDetalle(prod, type) { detalles.value.push({ _tid: uid(), material_id: genStageId(), finished_item: prod.finished_item, concept_type: type, item: "", supplier: "", tipo_material: "", internal_uom: "", rendimiento: 0, internal_qty: 0, supplier_qty: 0, unit_price: 0, precio_compra: 0, supplier_uom: "", conversion_factor: 1, total: 0, etapa: "", _supplierOptions: [], _qtyMode: "rendimiento" }); }
// ── Tipo de materia prima (Tela/Avío) ──
// Filtra qué UDM tiene sentido según el tipo, y para avíos que se compran por Mazo o
// Gruesa (botones, broches…) ya trae la equivalencia fija en piezas, para poder
// capturar "cuántas piezas lleva la prenda" en vez de la fracción de mazo/gruesa que
// eso representa (que nadie captura a mano de forma natural).
const UDM_POR_TIPO = {
  Tela: [
    { value: "KGM - Kilogramo", label: "Kilogramo" },
    { value: "MTR - Metro", label: "Metro" },
  ],
  "Avío": [
    { value: "MTR - Metro", label: "Metro" },
    { value: "KGM - Kilogramo", label: "Kilogramo" },
    { value: "Mazo", label: "Mazo — 1,728 pzas" },
    { value: "Gruesa", label: "Gruesa — 144 pzas" },
    { value: "H87 - Pieza", label: "Pieza" },
  ],
};
const PIEZAS_POR_UDM = { Mazo: 1728, Gruesa: 144 };
function udmOptionsFor(d) { return UDM_POR_TIPO[d.tipo_material] || []; }

// ── UDM reales de cada artículo (api/item_api.get_item_uoms) ──────────────
// El costeo siempre consume en la UDM BASE del artículo: si el botón se da de alta
// en piezas, el consumo es "4 piezas por prenda" y no "0.0023 mazos". El precio, en
// cambio, se captura como lo cotiza el proveedor (el mazo) y se deriva el unitario.
// Antes la UDM salía de una lista fija por tipo de material (UDM_POR_TIPO), que no
// sabía nada del artículo.
const uomsPorItem = reactive({});
async function cargarUomsDeItem(code) {
  if (!code || uomsPorItem[code]) return uomsPorItem[code];
  try {
    const r = await call("costeo_yelke.api.item_api.get_item_uoms", { item_code: code });
    uomsPorItem[code] = { base: r.stock_uom || "", uoms: r.uoms || [] };
  } catch { uomsPorItem[code] = { base: "", uoms: [] }; }
  return uomsPorItem[code];
}
function udmBaseDe(d) { return d.item ? (uomsPorItem[d.item]?.base || "") : ""; }
function udmsCompraDe(d) { return d.item ? (uomsPorItem[d.item]?.uoms || []) : []; }
function factorDeUdm(d, uom) {
  const fila = udmsCompraDe(d).find(u => u.uom === uom);
  return Number(fila?.conversion_factor) || 1;
}
// Cuántas UDM base trae una unidad de compra; 1 cuando se cotiza en la base.
function factorCompra(d) { return Number(d.conversion_factor) || 1; }
function precioDerivado(d) {
  const f = factorCompra(d);
  return f > 0 ? round8((Number(d.precio_compra) || 0) / f) : 0;
}
function onPrecioCompraInput(d, prod) {
  d.unit_price = precioDerivado(d);
  recalcDetalle(d, prod);
}
function onUdmCompraChange(d, prod) {
  d.conversion_factor = factorDeUdm(d, d.supplier_uom);
  d.unit_price = precioDerivado(d);
  recalcDetalle(d, prod);
}
function esUdmPorPiezas(d) { return d.internal_uom in PIEZAS_POR_UDM; }
function piezasPorUdm(d) { return PIEZAS_POR_UDM[d.internal_uom] || 0; }
// La UDM ya dice qué modo corresponde -- no hace falta guardar el modo aparte ni un
// campo nuevo en el backend: se deriva de internal_uom (que sí se guarda), así que al
// recargar el costeo queda seleccionada la misma pestaña sola. Kilogramo -> rendimiento
// ("1 kilo rinde X piezas"), Metro -> consumo ("cada pieza usa X metros"), Mazo/Gruesa
// -> piezas (cuántas piezas de la prenda salen de ahí), Pieza -> consumo ("cada prenda
// lleva X piezas": botones, etiquetas... aunque se compren por Mazo). Solo cuando la UDM
// no cae en ninguna de esas reglas (o aún sin UDM) queda libre para elegir entre
// rendimiento/consumo, y ahí sí se respeta lo último que el usuario clickeó.
const QTY_MODE_LABEL = { rendimiento: "Rendimiento", consumo: "Consumo", piezas: "Piezas" };
function qtyModeLocked(d) {
  return d.internal_uom === "KGM - Kilogramo" || d.internal_uom === "MTR - Metro" || d.internal_uom === "H87 - Pieza" || esUdmPorPiezas(d);
}
function qtyModeFor(d) {
  if (d.internal_uom === "KGM - Kilogramo") return "rendimiento";
  if (d.internal_uom === "MTR - Metro" || d.internal_uom === "H87 - Pieza") return "consumo";
  if (esUdmPorPiezas(d)) return "piezas";
  return d._qtyMode || "rendimiento";
}
function round8(n) { return Math.round((n || 0) * 100000000) / 100000000; }
// Mientras se está tecleando, muestra el número de piezas TAL CUAL lo escribió (no lo
// que resulta de deshacer internal_qty y multiplicar otra vez por 1728/144 -- con
// factores tan grandes esa vuelta pierde precisión visible si internal_qty no se
// guarda con suficientes decimales, ej. "5" se mostraba como "5.0008" al recargar
// -- por eso internal_qty se redondea a 8 decimales aquí, no 4 o 6: con 6 el error
// (hasta 0.0000005) se amplifica x1728 a casi 0.001, visible al reconstruir).
function piezasPorPrenda(d) {
  if (d._piezas_input !== undefined && d._piezas_input !== null && d._piezas_input !== "") return d._piezas_input;
  return round4((d.internal_qty || 0) * piezasPorUdm(d));
}
function onPiezasInput(d, prod, val) {
  d._piezas_input = val === "" ? "" : Number(val);
  const piezas = Number(val) || 0;
  const factor = piezasPorUdm(d);
  d.internal_qty = factor > 0 ? round8(piezas / factor) : 0;
  d.rendimiento = d.internal_qty > 0 ? round4(1 / d.internal_qty) : 0;
  recalcDetalle(d, prod);
}
function onTipoMaterialChange(d, prod) {
  const validos = udmOptionsFor(d).map(o => o.value);
  if (!validos.includes(d.internal_uom)) {
    d.internal_uom = "";
    d._piezas_input = undefined;
  }
  recalcDetalle(d, prod);
}
function onUdmSelectChange(d, prod) {
  if (!esUdmPorPiezas(d)) d._piezas_input = undefined;
  recalcDetalle(d, prod);
}
function removeDetalle(d, prod) { const i = detalles.value.findIndex(x => x._tid === d._tid); if (i !== -1) detalles.value.splice(i, 1); materialesEtapa.value = materialesEtapa.value.filter(r => r.material_id !== d.material_id); recalcProducto(prod); }
function round2(n) { return Math.round((n || 0) * 100) / 100; }
function round4(n) { return Math.round((n || 0) * 10000) / 10000; }
function fmtQty(n) { return round4(n).toString(); }
// El consumo por prenda (internal_qty) es la fuente de verdad -- rendimiento es solo
// otra forma de expresar el mismo número (piezas por UDM en vez de UDM por pieza),
// para que Sandra pueda capturar el que le resulte natural según la materia prima
// (ej. "1 kilo rinde 4 chamarras" vs. "cada chamarra usa 1.5 metros").
function onRendimientoInput(d, prod) { d.internal_qty = d.rendimiento > 0 ? round4(1 / d.rendimiento) : 0; recalcDetalle(d, prod); }
function onConsumoInput(d, prod) { d.rendimiento = d.internal_qty > 0 ? round4(1 / d.internal_qty) : 0; recalcDetalle(d, prod); }
function recalcDetalle(d, prod) {
  // El costo de la materia prima siempre es por UNA sola pieza del producto terminado
  // (no se multiplica por la cantidad del pedido) -- supplier_qty sigue siendo la
  // cantidad total a comprar, pero es solo informativo, no entra en el costo.
  d.supplier_qty = round2((d.internal_qty || 0) * (prod?.qty || 0));
  d.total = round2((d.internal_qty || 0) * (d.unit_price || 0));
  // Si este material ya está asignado a una etapa (se hace en "Flujo de Producción",
  // no aquí -- Costear se mantiene simple porque el pedido todavía podría no
  // concretarse), mantiene su cantidad sincronizada para que no se quede con el
  // consumo viejo aunque aquí se corrija.
  const asignada = materialesEtapa.value.find(r => r.material_id === d.material_id);
  if (asignada) asignada.qty = d.internal_qty || 0;
  recalcProducto(prod);
}
function onProdQtyChange(prod) {
  for (const d of materialesDe(prod.finished_item)) {
    d.supplier_qty = round2((d.internal_qty || 0) * (prod.qty || 0));
  }
  recalcProducto(prod);
}
function addEtapa(prod) {
  const next = etapasDe(prod.finished_item).length + 1;
  etapas.value.push({ _tid: uid(), producto_terminado: prod.finished_item, etapa: String(next), stage_id: genStageId(), recibe_de: "", servicio: "", proveedor: "", precio_servicio: 0, lote_qty: 1, lote_uom: "H87 - Pieza", modo_precio: "Por operación", operaciones_por_pieza: 1, precio_por_operacion: 0, subensamblaje: "" });
  manufacturaGuardada.value = false;
}
// Precio de la etapa por UNA pieza -- si el proveedor cobra por lote (ej. $19 por 25
// confecciones), precio_servicio es el precio del lote completo, no de la pieza.
function precioPorPiezaEtapa(e) { return round2((e.precio_servicio || 0) / (e.lote_qty || 1)); }
// Modo "Por operación": lo opuesto a "Por lote" -- en vez de dividir un precio de
// lote entre varias piezas, MULTIPLICA cuántas veces se repite la operación
// DENTRO de cada pieza por el precio de cada una (ej. 4 segmentos de cinta
// reflejante por prenda a $1.87 c/u = $7.48/prenda). precio_servicio queda
// siempre como el precio final por pieza -- lote_qty no se usa en este modo
// (se deja en 1, sin agrupar por lote).
function recalcPrecioOperacion(e, prod) {
  e.precio_servicio = round2((e.operaciones_por_pieza || 0) * (e.precio_por_operacion || 0));
  recalcProducto(prod);
}
function removeEtapa(e, prod) {
  const i = etapas.value.findIndex(x => x._tid === e._tid);
  if (i !== -1) etapas.value.splice(i, 1);
  const ownKey = e.stage_id;
  if (prod) {
    // Renumerar para que la secuencia 1..N nunca tenga huecos -- el número de etapa
    // ya no es editable a mano, así que debe mantenerse consistente solo. stage_id NO
    // se toca (es estable a propósito) -- pero si alguien más "recibía de" la etapa
    // eliminada, esa referencia queda colgante y hay que limpiarla, si no el grafo
    // apuntaría a un nodo que ya no existe.
    etapasDe(prod.finished_item).forEach((et, idx) => { et.etapa = String(idx + 1); });
    if (ownKey) {
      etapasDe(prod.finished_item).forEach(et => {
        const ids = (et.recibe_de || "").split(",").map(s => s.trim()).filter(Boolean);
        if (ids.includes(ownKey)) et.recibe_de = ids.filter(id => id !== ownKey).join(",");
      });
    }
    materialesEtapa.value = materialesEtapa.value.filter(r => r.stage_id !== e.stage_id);
    detalles.value.forEach(d => { if (d.etapa === e.stage_id) syncMaterialEtapaEscalar(d); });
    recalcProducto(prod);
    manufacturaGuardada.value = false;
  }
}
function tallasDe(fi) { return tallas.value.filter(t => t.finished_item === fi); }
// `talla` puede traer varias agrupadas separadas por coma (ej. "2XL,3XL") -- se
// juntan con "/" para mostrarlas juntas donde antes solo se esperaba una.
function tallaLabel(tallaField) {
  const codes = (tallaField || "").split(",").filter(Boolean);
  return codes.map(code => allTallas.value.find(x => x.name === code)?.talla || code).join("/");
}
// "Variante de talla": una talla que necesita más/distinto material se costea
// como su propio producto (Costeo Producto nuevo, con su propio artículo,
// materiales, etapas y precio), enlazado solo para mostrarlo agrupado en
// pantalla (variante_talla_de) -- nunca se fusiona de vuelta en
// Cotización/Orden de Venta/Factura, genera su propia línea igual que
// cualquier otro producto del costeo.
// Paso 1: género/tipo de prenda/talla(s) + cantidad (o pendiente) -- mismo
// widget que "Tallas incluidas", pero aquí decide qué cubre la variante nueva,
// no un ajuste de precio. Paso 2: una vez creada, tabla para ir marcando solo
// los materiales cuyo consumo por pieza cambia para esta talla (el resto ya
// quedó clonado igual que el producto base).
const varianteWizard = reactive({
  finished_item: "", step: 1, loading: false,
  genero: "", grupo_talla: "", talla: "", qty: 0, pendiente: false,
  // Consumo de esta talla por material del base (material_id -> lo que se escribió, en
  // la unidad de captura de ese material, ver unidadDeFila).
  consumos: {},
});
const varianteWizardTallas = computed(() => (varianteWizard.talla || "").split(",").filter(Boolean));
function toggleVarianteWizardTalla(code) {
  const actuales = varianteWizardTallas.value.slice();
  const idx = actuales.indexOf(code);
  if (idx === -1) actuales.push(code); else actuales.splice(idx, 1);
  varianteWizard.talla = actuales.join(",");
}
// Unidad en la que se captura el consumo de un material en la variante: la misma que
// en Costear -- lo que se compra por Mazo/Gruesa en PIEZAS por prenda (se convierte
// solo, ver PIEZAS_POR_UDM), todo lo demás en su UDM por prenda. El servidor siempre
// recibe internal_qty en la UDM del renglón; antes se mandaba el número tal cual y
// "4 botones" se guardaba como 4 mazos.
function nombreUdm(u) { return (u || "").includes(" - ") ? u.split(" - ").slice(1).join(" - ") : (u || "UDM"); }
function unidadDeFila(d) {
  if (esUdmPorPiezas(d)) {
    const f = piezasPorUdm(d);
    return { etiqueta: "piezas por prenda", ayuda: `se compra por ${nombreUdm(d.internal_uom)} de ${f.toLocaleString("es-MX")} piezas`,
             aBase: (v) => round8((Number(v) || 0) / f), deBase: (q) => round4((Number(q) || 0) * f) };
  }
  return { etiqueta: `${nombreUdm(d.internal_uom || udmBaseDe(d))} por prenda`, ayuda: "",
           aBase: (v) => Number(v) || 0, deBase: (q) => round4(Number(q) || 0) };
}
function materialesBaseVariante(prod) { return materialesDe(prod.finished_item).filter((d) => d.item && d.material_id); }
function consumoBase(d) { return unidadDeFila(d).deBase(d.internal_qty); }
function valorTalla(d) {
  const v = varianteWizard.consumos[d.material_id];
  return v === undefined ? consumoBase(d) : v;
}
function cambiaEnTalla(d) {
  const v = varianteWizard.consumos[d.material_id];
  return v !== undefined && v !== "" && Number(v) !== consumoBase(d);
}
function diferenciaTalla(d) { return round4(Number(valorTalla(d)) - consumoBase(d)); }
function cambiosVariante(prod) { return materialesBaseVariante(prod).filter(cambiaEnTalla).length; }
function abrirVarianteWizard(prod) {
  Object.assign(varianteWizard, {
    finished_item: prod.finished_item, step: 1, loading: false,
    genero: "", grupo_talla: "", talla: "", qty: 0, pendiente: false,
    consumos: {},
  });
}
function cerrarVarianteWizard() { varianteWizard.finished_item = ""; }
async function crearVarianteTalla(prod) {
  varianteWizard.loading = true;
  try {
    // crear_variante_talla trabaja directo sobre lo último guardado en el
    // servidor -- si hay cambios sin guardar en pantalla (ej. un producto que
    // acabas de borrar, o un material que acabas de corregir), se guardan
    // PRIMERO. Si no, la recarga de abajo los pisaría y los perdería sin
    // avisar, y la variante se crearía a partir de datos viejos.
    if (!(await saveDoc())) return;
    const r = await call("costeo_yelke.api.costeo_api.crear_variante_talla", {
      costeo: docName.value,
      producto_base: prod.finished_item,
      genero: varianteWizard.genero,
      talla: varianteWizard.talla,
      qty: varianteWizard.qty,
      pendiente: varianteWizard.pendiente,
      materiales: JSON.stringify(materialesBaseVariante(prod).filter(cambiaEnTalla).map((d) => ({
        material_id: d.material_id, internal_qty: unidadDeFila(d).aBase(varianteWizard.consumos[d.material_id]),
      }))),
    });
    cerrarVarianteWizard();
    showToast(`Variante ${r.item_code} creada`);
    await recargarConservandoExpandido(prod.finished_item);
  } catch (e) {
    showToast(e.message || "No se pudo crear la variante", "error");
  } finally {
    varianteWizard.loading = false;
  }
}
// loadCosteoData reemplaza productos.value por completo -- cada renglón recibe
// un _tid nuevo, así que expandedTids (que apunta a los _tid viejos) dejaría
// de calzar con nada y TODAS las tarjetas abiertas se colapsarían solas en
// cada paso del wizard. Se recuerdan los finished_item (estables) de lo que
// estaba abierto antes de recargar, y se vuelve a expandir cada uno.
async function recargarConservandoExpandido(finished_item) {
  const abiertos = new Set(
    productos.value.filter((p) => expandedTids.has(p._tid)).map((p) => p.finished_item)
  );
  abiertos.add(finished_item);
  await loadCosteoData({ silencioso: true });
  expandedTids.clear();
  for (const p of productos.value) {
    if (abiertos.has(p.finished_item)) expandedTids.add(p._tid);
  }
}
async function onEtapaServicioChange(e, prod) {
  if (e.servicio && !e.precio_servicio) {
    try {
      const res = await call("costeo_yelke.api.costeo_api.get_item_price", { item_code: e.servicio, price_list: "Compra estandar" });
      if (res?.price) e.precio_servicio = res.price;
    } catch { /* ignore */ }
  }
  recalcProducto(prod);
}
function recalcProducto(prod) {
  const fi = prod.finished_item;
  prod.material_cost = detalles.value.filter(d => d.finished_item === fi && d.concept_type === "Materia Prima").reduce((s, d) => s + (d.total || 0), 0);
  const detServ = detalles.value.filter(d => d.finished_item === fi && d.concept_type === "Servicio").reduce((s, d) => s + (d.total || 0), 0);
  const stageServ = etapas.value.filter(e => e.producto_terminado === fi && e.servicio).reduce((s, e) => s + precioPorPiezaEtapa(e), 0);
  prod.services_cost = detServ + stageServ;
  const base = prod.material_cost + prod.services_cost + (prod.shipping_cost || 0) + (prod.labeling_cost || 0) + (prod.packaging_cost || 0);
  const m = (prod.margin_pct || 0) / 100;
  const overheadFlat = base * ((prod.overhead_pct || 0) / 100);
  const costoFlat = round2(base + overheadFlat);
  const pvFlat = round2((m > 0 && m < 1) ? costoFlat / (1 - m) : costoFlat);
  prod.overhead_amt = round2(overheadFlat);
  prod.total_unit_cost = costoFlat;
  if (prod.precio_manual) {
    // Precio fijado a mano (onPriceChange): NO se deriva de margin_pct como de
    // costumbre -- es al revés, el margen se recalcula contra el costo nuevo
    // manteniendo ESE precio exacto fijo, para que cotización/documentos
    // posteriores siempre reciban el número que se tecleó, sin que el
    // redondeo del % (ni un cambio posterior en materiales/etapas) lo mueva.
    const priceM = prod.unit_sales_price || 0;
    prod.margin_pct = round2(Math.max(0, priceM > 0 ? ((priceM - prod.total_unit_cost) / priceM) * 100 : 0));
  } else {
    prod.unit_sales_price = pvFlat;
  }
  prod.total_sales_price = round2(prod.unit_sales_price * (prod.qty || 0));
  // El renglón de talla de una variante (crear_variante_talla) lleva el costo y precio
  // de su producto, al día con cualquier cambio de materiales/etapas.
  for (const t of tallasDe(fi)) {
    t.costo_unitario = prod.total_unit_cost;
    t.precio_venta = prod.unit_sales_price;
    t.costo_total = round2(t.costo_unitario * (t.qty || 0));
  }
}
// Editar el precio unitario → recalcula el margen (sentido inverso, sin sobrescribir el
// precio) y marca precio_manual: mientras esté activo, recalcProducto ya NO deriva el
// precio del margen -- es al revés, el precio manda y el margen es solo informativo.
// Así el precio exacto que se tecleó aquí es el que llega a cotización/documentos
// posteriores, sin que un redondeo del margen (o un cambio en materiales/etapas más
// adelante) lo mueva ni un centavo.
// El precio a mano se captura dos veces (DialogoPrecio); al coincidir se aplica igual
// que antes se aplicaba al teclearlo en la celda.
const precioEnEdicion = ref(null);
function abrirPrecio(prod) { precioEnEdicion.value = prod; }
function aplicarPrecio(valor) {
  const prod = precioEnEdicion.value;
  precioEnEdicion.value = null;
  if (!prod) return;
  prod.unit_sales_price = valor;
  onPriceChange(prod);
}
function onPriceChange(prod) {
  const price = prod.unit_sales_price || 0;
  const cost = prod.total_unit_cost || 0;
  let m = price > 0 ? ((price - cost) / price) * 100 : 0;
  if (m < 0) m = 0;
  prod.margin_pct = Math.round(m * 100) / 100;
  prod.total_sales_price = price * (prod.qty || 0);
  prod.precio_manual = 1;
}
// Volver a escribir el Margen % a mano deshace el precio fijo -- el precio vuelve a
// derivarse del margen, como el comportamiento de siempre.
function onMarginChange(prod) {
  prod.precio_manual = 0;
  recalcProducto(prod);
}
// Conversor $/kg -> $/m de telas: el proveedor cotiza por kilo, pero el consumo por
// prenda se captura en metros -- la usuaria ya sabe (por experiencia con esa tela)
// cuántos metros salen de 1 kilo, aquí solo se divide el precio por kilo entre esa
// cantidad para sacar el precio por metro (y de paso cambia la UDM del renglón a
// Metro); el consumo por prenda lo sigue capturando ella a mano en "Rendimiento /
// Consumo", eso no se automatiza. metros_por_kilo se guarda en el Item (no en el
// renglón del Costeo) para no volver a capturarlo la próxima vez que esa misma tela
// se use en otro costeo -- si el "item" (texto libre) todavía no existe como Item
// real, el conversor sigue funcionando pero avisa que no podrá guardarlo.
const telaConvertModal = reactive({ open: false, d: null, prod: null, precio_kg: 0, metros_por_kilo: null, itemExists: false });
const telaConvertPrecioM = computed(() => {
  const kg = telaConvertModal.metros_por_kilo || 0;
  return kg > 0 ? round2((telaConvertModal.precio_kg || 0) / kg) : 0;
});
async function openTelaConvert(d, prod) {
  telaConvertModal.open = true;
  telaConvertModal.d = d;
  telaConvertModal.prod = prod;
  telaConvertModal.precio_kg = d.internal_uom === "KGM - Kilogramo" ? (d.unit_price || 0) : 0;
  telaConvertModal.metros_por_kilo = null;
  telaConvertModal.itemExists = false;
  if (!d.item) return;
  try {
    const res = await call("costeo_yelke.api.item_api.get_tela_conversion_fields", { item_code: d.item });
    telaConvertModal.itemExists = !!(res && Object.keys(res).length);
    if (res) telaConvertModal.metros_por_kilo = res.metros_por_kilo || null;
  } catch { /* ignore */ }
}
function closeTelaConvert() { telaConvertModal.open = false; telaConvertModal.d = null; telaConvertModal.prod = null; }
async function aplicarTelaConvert() {
  const d = telaConvertModal.d, prod = telaConvertModal.prod;
  if (!d) return;
  // El convertidor entrega el precio YA por metro, que aqui pasa a ser la UDM base
  // del renglon: queda cotizado en su propia unidad, sin factor.
  d.unit_price = telaConvertPrecioM.value;
  d.precio_compra = telaConvertPrecioM.value;
  d.internal_uom = "MTR - Metro";
  d.supplier_uom = "MTR - Metro";
  d.conversion_factor = 1;
  onUdmSelectChange(d, prod);
  if (telaConvertModal.itemExists && telaConvertModal.metros_por_kilo) {
    try { await call("costeo_yelke.api.item_api.guardar_tela_conversion", { item_code: d.item, metros_por_kilo: telaConvertModal.metros_por_kilo }); }
    catch { /* no crítico -- el precio ya se aplicó al renglón */ }
  }
  closeTelaConvert();
}
async function fetchItemImage(code) { if (!code) return ""; try { const rows = await db.getList("Item", { fields: ["image"], filters: [["name", "=", code]], limit: 1 }); return rows?.[0]?.image || ""; } catch { return ""; } }
// Al elegir la materia prima (ahora buscable contra el catálogo real de Artículos,
// no texto libre -- ver ITEM_FILTERS.mp), se le cargan de una vez los datos que ya
// se conocen de ese artículo: proveedor + precio de compra (si ya tiene alguno
// capturado), y si es una tela ya identificada como tal (ver metros_por_kilo,
// patch v0_2_5) se marca sola como "Tela" para no tener que elegirlo a mano.
// Si se escribe un nombre que no coincide con ningún artículo existente, se deja
// tal cual -- sigue funcionando como antes, y se resuelve más adelante en "Pasar a
// Producción" (materializeArticulosIfNeeded).
async function onDetalleItemChange(d, prod) {
  d._supplierOptions = [];
  d.supplier = "";
  d.unit_price = 0;
  d.precio_compra = 0;
  if (!d.item) { recalcDetalle(d, prod); return; }
  try {
    // La UDM del artículo manda sobre la lista por tipo de material: el consumo se
    // captura en la base y el precio arranca cotizado en esa misma base.
    const info = await cargarUomsDeItem(d.item);
    if (info.base) {
      d.internal_uom = info.base;
      d.supplier_uom = info.base;
      d.conversion_factor = 1;
    }
    d._supplierOptions = await call("costeo_yelke.api.costeo_api.proveedores_para_item", { item_code: d.item }) || [];
    // Si solo hay un proveedor con precio, selecciónalo y aplica su precio
    if (d._supplierOptions.length === 1) {
      d.supplier = d._supplierOptions[0].supplier;
      d.unit_price = d._supplierOptions[0].rate;
    } else {
      // Precio de referencia de la lista de compra estándar mientras se elige proveedor
      const res = await call("costeo_yelke.api.costeo_api.get_item_price", { item_code: d.item, price_list: "Compra estandar" });
      if (res?.price) d.unit_price = res.price;
    }
    // El precio que llega de la lista o del proveedor viene por UDM base.
    d.precio_compra = d.unit_price;
    if (!d.tipo_material) {
      const item = await call("frappe.client.get_value", { doctype: "Item", filters: d.item, fieldname: "metros_por_kilo" });
      if (item?.metros_por_kilo) d.tipo_material = "Tela";
    }
    recalcDetalle(d, prod);
  } catch { /* ignore */ }
}
function onSupplierChange(d, prod) {
  const opt = (d._supplierOptions || []).find(o => o.supplier === d.supplier);
  if (opt) d.unit_price = opt.rate;
  recalcDetalle(d, prod);
}
async function loadAllSuppliers() {
  if (allSuppliers.value.length) return;
  try {
    allSuppliers.value = await call("frappe.client.get_list", {
      doctype: "Supplier", fields: ["name", "supplier_name", "nombre_comercial"],
      filters: [["disabled", "=", 0]], limit_page_length: 500, order_by: "supplier_name asc",
    }) || [];
  } catch { /* ignore */ }
}
// Nombre Comercial del proveedor (si lo capturó) en vez de su nombre real -- para
// cualquier texto plano que no pase por LinkInput (LinkInput ya lo resuelve solo,
// ver getLinkDisplayLabel). Cae al nombre real si no tiene Nombre Comercial
// capturado, o si `name` no matchea ningún proveedor cargado todavía.
function nombreProveedor(name) {
  if (!name) return name;
  const s = allSuppliers.value.find(o => o.name === name);
  return (s && (s.nombre_comercial || s.supplier_name)) || name;
}
// Catálogo completo de Talla (~110 registros) cargado una sola vez -- de ahí se arman
// en el cliente los 3 selects encadenados (Género → Tipo de prenda → Talla) sin ir
// al servidor por cada nivel, caminando el árbol un nivel a la vez con parent_talla.
async function loadAllTallas() {
  if (allTallas.value.length) return;
  try {
    allTallas.value = await call("frappe.client.get_list", {
      doctype: "Talla", fields: ["name", "talla", "is_group", "parent_talla", "genero", "uso_comun"],
      filters: [["disabled", "=", 0]], limit_page_length: 0, order_by: "lft asc",
    }) || [];
  } catch { /* ignore */ }
}
function gruposDeGenero(genero) {
  if (!genero) return [];
  const root = allTallas.value.find(t => t.is_group && !t.parent_talla && t.talla === genero);
  if (!root) return [];
  const wrapper = allTallas.value.find(t => t.is_group && t.parent_talla === root.name);
  if (!wrapper) return [];
  return allTallas.value.filter(t => t.is_group && t.parent_talla === wrapper.name);
}
function tallasDeGrupo(grupoName) {
  if (!grupoName) return [];
  return allTallas.value.filter(t => !t.is_group && t.parent_talla === grupoName);
}
// Tallas REGULARES de un producto base: solo las de uso común del catálogo (XS a XL
// en letras, y su equivalente en cada sistema). Las demás son tallas extra: se venden
// con su propio precio en "Tallas extra", nunca aquí. Una talla no común que ya traiga
// piezas (capturada antes de esta regla) se sigue mostrando para no perderla.
function tallasRegulares(d, b) {
  const todas = tallasDeGrupo(b.grupo);
  if (b.todas) return todas;
  const comunes = todas.filter(t => t.uso_comun || Number(d.valores?.[t.name]) > 0);
  // Un tipo de talla sin ninguna marcada como común se comporta como antes.
  return comunes.length ? comunes : todas;
}
// Hay tallas del tipo que no se están mostrando (no son de uso común): se ofrecen con
// «Ver todas», para poder capturar cualquier talla que pida el cliente.
function hayTallasOcultas(d, b) {
  return !b.todas && tallasRegulares(d, b).length < tallasDeGrupo(b.grupo).length;
}
// Géneros que todavía no tienen bloque (b = el bloque que se está editando).
function generosLibres(d, b = null) {
  return ["Caballero", "Dama"].filter(g => (b && b.genero === g) || !d.bloques.some(x => x !== b && x.genero === g));
}
// Quita las piezas de tallas que ya no pertenecen a ningún bloque (cambió el género o
// el tipo de talla, o se quitó el bloque): si no, seguirían sumando sin verse.
function limpiarDesglose(d) {
  const validas = new Set(d.bloques.flatMap(b => tallasRegulares(d, b).map(t => t.name)));
  for (const code of Object.keys(d.valores)) if (!validas.has(code)) delete d.valores[code];
}
async function hydrateSupplierOptions() {
  for (const d of detalles.value) {
    if (d.concept_type !== "Materia Prima" || !d.item) continue;
    try {
      const opts = await call("costeo_yelke.api.costeo_api.proveedores_para_item", { item_code: d.item }) || [];
      // Conserva el proveedor guardado aunque ya no esté en la lista de precios
      if (d.supplier && !opts.some(o => o.supplier === d.supplier)) {
        opts.push({ supplier: d.supplier, supplier_name: d.supplier, rate: d.unit_price || 0 });
      }
      d._supplierOptions = opts;
    } catch { /* ignore */ }
  }
}

// ── Validate / payload ──
function validate() {
  Object.keys(errors).forEach(k => delete errors[k]);
  let ok = true;
  for (const f of ["cliente", "fecha", "compania"]) { if (!form[f]) { errors[f] = "Requerido"; ok = false; } }
  const warehouseFields = ["centro_de_costos", "almacen_materias_primas", "almacen_trabajo_en_proceso"];
  const missingWarehouse = warehouseFields.some(f => !form[f]);
  if (missingWarehouse) {
    warehouseFields.forEach(f => { if (!form[f]) errors[f] = "Requerido"; });
    ok = false;
    // El mensaje anterior ("selecciona la compañía de nuevo") mandaba a repetir justo
    // lo que ya había fallado: si la compañía nombra sus almacenes distinto, volver a
    // elegirla da exactamente el mismo resultado vacío. Ahora los campos están en la
    // pantalla y se apunta a ellos.
    showToast("Faltan los almacenes o el centro de costos — complétalos arriba, junto a la compañía", "error");
  }
  if (!productos.value.some(p => p.finished_item && (p.qty || 0) > 0)) { showToast("Agrega al menos un producto con cantidad > 0", "error"); ok = false; }
  return ok;
}
function stripLocal(obj) { const out = {}; for (const k in obj) { if (!k.startsWith("_")) out[k] = obj[k]; } return out; }
function buildPayload() {
  return {
    doctype: "Costeo", titulo: form.titulo || "", cliente: form.cliente, fecha: form.fecha, "compañia": form.compania,
    proyecto: form.proyecto || "", guardar_como_plantilla: form.guardar_como_plantilla ? 1 : 0, centro_de_costos: form.centro_de_costos,
    almacen_materias_primas: form.almacen_materias_primas, almacen_trabajo_en_proceso: form.almacen_trabajo_en_proceso,
    costeo_status: docStatus.value || "Borrador",
    costeo_producto: productos.value.map(stripLocal),
    costeo_producto_detalle: detalles.value.map(stripLocal),
    tabla_etapas_costeo: etapas.value.map(stripLocal),
    tabla_materiales_etapa: materialesEtapa.value.map(stripLocal),
    tabla_tallas_costeo: tallas.value.map(stripLocal),
  };
}
// De qué costeo son los productos que hay en pantalla (ver fillFromDoc).
let costeoEnPantalla = "";
async function fillFromDoc(data) {
  // Se marca la carga para que el watcher de compañía no autodetecte almacenes
  // encima de los que trae el documento guardado (ver applyCompanyDefaults).
  cargandoDoc = true;
  docName.value = data.name;
  docStatus.value = data.costeo_status || "Borrador";
  docState.value = data.docstatus || 0;
  form.titulo = data.titulo || "";
  form.cliente = data.cliente || ""; form.fecha = data.fecha || today(); form.compania = data["compañia"] || "";
  form.proyecto = data.proyecto || "";
  form.guardar_como_plantilla = (data.guardar_como_plantilla === undefined || data.guardar_como_plantilla === null)
    ? false : !!Number(data.guardar_como_plantilla);
  form.centro_de_costos = data.centro_de_costos || ""; form.almacen_materias_primas = data.almacen_materias_primas || ""; form.almacen_trabajo_en_proceso = data.almacen_trabajo_en_proceso || "";
  // Cada recarga crea renglones nuevos (_tid nuevo): las tarjetas que estaban abiertas
  // se vuelven a abrir por su producto, o al guardar se cerrarían todas solas.
  const abiertosAntes = data.name === costeoEnPantalla
    ? new Set(productos.value.filter((p) => expandedTids.has(p._tid)).map((p) => p.finished_item))
    : new Set();
  costeoEnPantalla = data.name;
  [...new Set((data.tabla_etapas_costeo || []).map((e) => e.proveedor).filter(Boolean))].forEach(cargarServiciosProveedor);
  productos.value = (data.costeo_producto || []).map(r => ({ _tid: uid(), image: "", description: "", precio_manual: 0, ...r, _lastFinishedItem: r.finished_item || "" }));
  if (abiertosAntes.size) {
    expandedTids.clear();
    for (const p of productos.value) if (abiertosAntes.has(p.finished_item)) expandedTids.add(p._tid);
  }
  // Los renglones anteriores a la captura por UDM de compra no traen precio_compra
  // ni factor: su precio ya estaba en la UDM base, asi que se copia tal cual.
  detalles.value = (data.costeo_producto_detalle || []).map(r => ({
    _tid: uid(), _supplierOptions: [], _qtyMode: "rendimiento", ...r,
    material_id: r.material_id || genStageId(),
    conversion_factor: Number(r.conversion_factor) || 1,
    supplier_uom: r.supplier_uom || r.internal_uom || "",
    precio_compra: Number(r.precio_compra) || Number(r.unit_price) || 0,
  }));
  // Las UDM de cada articulo se piden en segundo plano: el selector de precio las
  // necesita, pero la tabla ya se puede ver mientras llegan.
  [...new Set(detalles.value.map(d => d.item).filter(Boolean))].forEach(cargarUomsDeItem);
  // La etapa se captura SIEMPRE como cantidad x costo (multiplicación). Los costeos
  // viejos que usaban precio por lote (precio ÷ lote_qty) se convierten al abrirlos:
  // 1 operación al precio por pieza que ya tenían, con lote_qty de vuelta en 1 --
  // el costo por prenda no cambia, y lote_qty>1 dejaría de significar lo mismo para
  // crear_subcontracting_bom ("1 lote de servicio produce N piezas").
  etapas.value = (data.tabla_etapas_costeo || []).map(r => {
    const e = { _tid: uid(), ...r, lote_qty: r.lote_qty || 1, lote_uom: r.lote_uom || "H87 - Pieza", modo_precio: "Por operación", operaciones_por_pieza: r.operaciones_por_pieza || 1, precio_por_operacion: r.precio_por_operacion || 0, stage_id: r.stage_id || genStageId() };
    if ((r.modo_precio || "Por lote") !== "Por operación") {
      e.operaciones_por_pieza = 1;
      e.precio_por_operacion = round2((Number(r.precio_servicio) || 0) / (Number(r.lote_qty) || 1));
      e.precio_servicio = e.precio_por_operacion;
      e.lote_qty = 1;
    }
    return e;
  });
  asignarGruposEtapas();
  materialesEtapa.value = (data.tabla_materiales_etapa || []).map(r => ({ _tid: uid(), ...r }));
  migrarMaterialesEtapaLegado();
  tallas.value = (data.tabla_tallas_costeo || []).map(r => ({ _tid: uid(), estado_cantidad: "Definida", ...r }));
  for (const p of productos.value) { if (p.finished_item) { const fetched = await fetchItemImage(p.finished_item); if (fetched) p.image = fetched; } }
  // Recalcular siempre al cargar (no confiar en la foto guardada la última vez) --
  // así los KPIs reflejan la fórmula actual (con tallas) aunque el costeo se haya
  // guardado antes de este cambio, o si se abrió sin tocar ningún campo todavía.
  productos.value.forEach(p => recalcProducto(p));
  hydrateSupplierOptions();
  // Se libera después de un tick: el watcher de compañía es asíncrono y si se
  // liberara aquí mismo alcanzaría a correr con la compañía recién asignada.
  await nextTick();
  cargandoDoc = false;
  // Un borrador que nació sin almacenes (creado desde otra pantalla o una versión
  // anterior): se le proponen los de su compañía, igual que al crearlo aquí.
  if (data.docstatus === 0 && faltanAlmacenes.value) applyCompanyDefaults(form.compania);
}

async function loadRelated() {
  if (!docName.value) return;
  // Cualquier acción que recarga los documentos del proyecto (enviar a aprobación,
  // validar, crear…) puede haber cerrado una asignación: se vuelven a pedir.
  cargarEncargos();
  try {
    const r = await call("costeo_yelke.api.costeo_api.get_costeo_related", { costeo: docName.value, sales_order: activeSOName.value || null });
    related.quotation = r.quotation; related.quotations = r.quotations || []; related.quotations_historial = r.quotations_historial || []; related.sales_order = r.sales_order;
    related.sales_orders = r.sales_orders || [];
    related.delivery_notes = r.delivery_notes || []; related.delivery_per_delivered = r.delivery_per_delivered || 0;
    related.sales_invoice = r.sales_invoice;
    if (related.sales_orders.length) {
      ensurePrintFmt("Sales Order");
      if (!soAutoExpandDone && expandedSOName.value === null) {
        soAutoExpandDone = true;
        expandedSOName.value = related.sales_orders[0].name;
        applySOToForm(related.sales_orders[0]);
      } else if (expandedSOName.value && !related.sales_orders.some(s => s.name === expandedSOName.value)) {
        expandedSOName.value = null;
      }
      // El desglose por talla se carga aquí y no solo en toggleSalesOrder: la
      // tarjeta de la OV se abre sola al entrar al costeo, y por ese camino el
      // desglose se quedaba vacío -- con lo cual la tabla no se pintaba nunca.
      const soAbierta = related.sales_orders.find(s => s.name === expandedSOName.value);
      if (soAbierta) { loadSoDesgloseForm(soAbierta); loadSoVariantesForm(soAbierta); }
      else if (!expandedSOName.value) {
        soDesgloseForm.value = []; soDesgloseDe.value = null;
        soVariantesForm.value = []; soVariantesDe.value = null;
      }
      const vivas = related.sales_orders.filter(s => s.docstatus !== 2);
      if (!activeSOName.value || !vivas.some(s => s.name === activeSOName.value)) {
        activeSOName.value = (vivas.find(s => s.name === expandedSOName.value) || vivas[0])?.name || null;
      }
    } else {
      activeSOName.value = null;
    }
    refreshNuevaOvGate();
    if (related.quotations.length) {
      ensurePrintFmt("Quotation");
      if (!quotAutoExpandDone && expandedQuotName.value === null) {
        // La primera vez que hay cotizaciones, se abre sola la más reciente (mismo
        // efecto que antes de tener acordeón, donde siempre se veía "la" cotización) --
        // después, si la usuaria la colapsa a propósito, no se vuelve a forzar abierta.
        quotAutoExpandDone = true;
        expandedQuotName.value = related.quotations[0].name;
        applyQuotToForm(related.quotations[0]);
        await loadCotItems(related.quotations[0].name);
      } else if (expandedQuotName.value && related.quotations.some(q => q.name === expandedQuotName.value)) {
        await loadCotItems(expandedQuotName.value);
      } else {
        expandedQuotName.value = null;
      }
    } else {
      cotItems.value = [];
    }
    if (r.sales_order) ensurePrintFmt("Sales Order");
    if (related.delivery_notes.length) {
      ensurePrintFmt("Delivery Note");
      // Preferir el borrador pendiente (necesita atención); si no hay, la más reciente.
      const preferida = related.delivery_notes.find(d => d.docstatus === 0) || related.delivery_notes[related.delivery_notes.length - 1];
      if (!related.delivery_notes.some(d => d.name === dnSel.value)) dnSel.value = preferida.name;
      await selectDn(dnSel.value);
    } else {
      dnSel.value = ""; dnDoc.value = null;
    }
    if (r.sales_invoice) {
      ensurePrintFmt("Sales Invoice");
      siForm.posting_date = r.sales_invoice.posting_date || "";
      siForm.due_date = r.sales_invoice.due_date || "";
      siForm.payment_terms_template = r.sales_invoice.payment_terms_template || "";
      siForm.tc_name = r.sales_invoice.tc_name || "";
    } else if (activeSO.value && !siForm.posting_date) {
      // Aún sin factura: hoy, y las condiciones que se pactaron en la OV.
      siForm.posting_date = today();
      siForm.payment_terms_template = activeSO.value.payment_terms_template || "";
      siForm.tc_name = activeSO.value.tc_name || "";
    }
    loadProdComplete(docName.value, activeSOName.value);
    // El backend reconcilia el estado si borraron documentos (p. ej. la cotización) desde ERPNext
    // Solo si el estado RETROCEDE se saca a la persona del paso; avanzar (p. ej. al
    // validar la última remisión: En Producción -> Entregado) la deja donde está.
    // ORDER y los pasos no son el mismo índice: se traduce con STEP_ORDER_IDX.
    if (r.costeo_status && r.costeo_status !== docStatus.value) {
      const antes = ORDER.indexOf(docStatus.value);
      docStatus.value = r.costeo_status;
      const idx = ORDER.indexOf(r.costeo_status);
      if (idx >= 0 && idx < antes) {
        const tope = idx === 2 ? 4 : STEP_ORDER_IDX.reduce((t, lvl, i) => (lvl !== null && lvl <= idx ? i : t), 0);
        if (activeStep.value > tope) activeStep.value = tope;
      }
    }
  } catch { /* ignore */ }
}
// ── Notas de remisión (entrega, pueden ser varias a distintas direcciones) ──
async function loadRemisionDetalle(name) {
  try {
    dnDoc.value = await call("costeo_yelke.api.costeo_api.get_remision", { name });
    dnForm.posting_date = dnDoc.value.posting_date || "";
    dnForm.shipping_address_name = dnDoc.value.shipping_address_name || "";
    dnForm.customer_address = dnDoc.value.customer_address || "";
    dnForm.flete_proveedor = dnDoc.value.flete_proveedor || "";
    dnForm.flete_costo = dnDoc.value.flete_costo || 0;
    dnForm.flete_incluye_iva = dnDoc.value.flete_incluye_iva || 0;
  } catch { dnDoc.value = null; }
}
async function selectDn(name) {
  dnSel.value = name;
  if (name) await loadRemisionDetalle(name);
  else dnDoc.value = null;
}
// ── Entrega de un lote repartida entre direcciones del cliente ─────────────────
// Una remisión en borrador por destino (crear_remisiones_lote, todas o ninguna);
// cantidades, almacén y lote los valida el servidor contra lo que el lote produjo.
const repartoEntrega = ref([]);
const entregaDir = reactive({ direcciones: [], default: null, customer: null });
const productosPorEntregar = computed(() => {
  const e = loteActivo.value?.entrega?.productos || {};
  const nombres = Object.fromEntries((loteActivo.value?.productos || []).map((p) => [p.finished_item, p.item_name]));
  // En el orden del lote: el producto base antes que sus variantes (tallas extra).
  const orden = (loteActivo.value?.productos || []).map((p) => p.finished_item);
  return Object.entries(e).filter(([, d]) => d.pendiente > 0)
    .map(([item, d]) => ({ item_code: item, item_name: nombres[item] || item, pendiente: d.pendiente }))
    .sort((a, b) => (orden.indexOf(a.item_code) + 1 || 99) - (orden.indexOf(b.item_code) + 1 || 99) || a.item_code.length - b.item_code.length);
});
/** Por qué no se puede generar todavía (vacío = se puede). */
const repartoMalo = computed(() => {
  const r = repartoEntrega.value.filter((x) => x.items.length);
  if (!r.length) return "Pon cuántas prendas van a cada dirección.";
  if (repartoEntrega.value.some((x) => x.items.length && !x.shipping_address_name)) return "Elige la dirección de cada envío.";
  for (const p of productosPorEntregar.value) {
    const suma = r.reduce((s, x) => s + (x.items.find((i) => i.item_code === p.item_code)?.qty || 0), 0);
    if (suma > p.pendiente + 0.001) return "Repartiste más de lo que el lote tiene por entregar.";
  }
  return "";
});
async function cargarDireccionesEntrega() {
  try {
    Object.assign(entregaDir, await call("costeo_yelke.api.costeo_api.get_direcciones_entrega", {
      costeo: docName.value, sales_order: activeSOName.value || null }));
  } catch { /* sin direcciones: el formulario permite dar de alta una */ }
}
watch(() => pPasoLote.value === "entrega" && !!loteActivo.value?.entrega?.lista, (v) => { if (v) cargarDireccionesEntrega(); }, { immediate: true });
async function crearRemisionesLote(lote_ref) {
  if (activeSO.value?.docstatus !== 1) { showToast("Primero valida la orden de venta", "error"); return; }
  if (repartoMalo.value) { showToast(repartoMalo.value, "error"); return; }
  advancing.value = true;
  try {
    const r = await call("costeo_yelke.api.costeo_api.crear_remisiones_lote", {
      costeo: docName.value, sales_order: activeSOName.value, lote_ref,
      repartos: JSON.stringify(repartoEntrega.value.filter((x) => x.items.length)),
    });
    await loadRelated();
    // Sin recargar los lotes, `entrega.pendiente` se quedaba con el valor viejo.
    await loadLotesProduccion();
    const n = r.remisiones.length;
    if (n === 1) await abrirPanelRemision(r.remisiones[0], `${lote_ref} · Remisión`);
    showToast(n > 1 ? `${n} remisiones creadas (borrador) — abre cada una para revisar flete y validarla`
                    : "Remisión creada (borrador) — revisa flete y valídala");
  } catch (e) { showToast(e.message || "No se pudieron crear las remisiones", "error"); }
  finally { advancing.value = false; }
}
// Factura de compra como ÚLTIMO paso de cada flujo (material o maquila), sin salir
// de Producción: se carga la factura de esa fuente (o queda lista para crearla).
async function abrirFacturaFuente(source_doctype, source_name, supplier_name) {
  // Factura de flete: ya existe (se creó sola al validar el envío), se abre directo.
  if (source_doctype === "Purchase Invoice") {
    pinvSel.value = { source_doctype, source_name, supplier_name, pendiente: 0 };
    await loadPinv(source_name);
    return;
  }
  await loadCompras();
  const fila = [...compras.materiales, ...compras.maquila].find((m) => m.name === source_name);
  if (fila) await selectCompra(source_doctype, fila);
  else { pinvSel.value = { source_doctype, source_name, supplier_name, pendiente: 0 }; pinvDoc.value = null; }
}
async function crearFacturaInline() {
  await generarFacturaCompra();
  await loadLotesProduccion();
  refrescarPendientePanel();
}
async function validarFacturaInline() {
  await validarPinv();
  await loadLotesProduccion();
  refrescarPendientePanel();
}
// Lo pendiente de facturar del panel se tomó de la fila al abrirlo; tras crear o
// validar se vuelve a leer (si no, "Registrar factura de lo pendiente" salía aunque
// la factura recién validada ya lo cubría todo).
function refrescarPendientePanel() {
  if (!panelFactura.abierto || !pinvSel.value) return;
  const m = (compras.maquila || []).find((x) => x.name === pinvSel.value.source_name);
  panelFactura.pendiente = m ? Number(m.pendiente_facturar) || 0 : 0;
}
async function generarRemision() {
  if (isNew.value) { showToast("Guarda el costeo primero", "error"); return; }
  if (activeSO.value?.docstatus !== 1) { showToast("Primero valida la orden de venta", "error"); return; }
  advancing.value = true;
  try {
    const r = await call("costeo_yelke.api.costeo_api.crear_remision", { costeo: docName.value, sales_order: activeSOName.value });
    dnSel.value = r.name;
    await loadRelated();
    await abrirPanelRemision(r.name, "Remisión · toda la orden de venta");
    showToast(related.delivery_notes.length > 1 ? "Nueva remisión creada (borrador)" : "Remisión creada (borrador)");
  } catch (e) { showToast(e.message || "No se pudo crear la remisión", "error"); }
  finally { advancing.value = false; }
}
async function guardarRemision() {
  if (!dnDoc.value) return;
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.actualizar_remision", {
      name: dnDoc.value.name, posting_date: dnForm.posting_date || null,
      items: JSON.stringify(dnDoc.value.items),
      shipping_address_name: dnForm.shipping_address_name || null,
      customer_address: dnForm.customer_address || null,
      flete_proveedor: dnForm.flete_proveedor || null,
      flete_costo: dnForm.flete_costo || 0,
      flete_incluye_iva: dnForm.flete_incluye_iva ? 1 : 0,
    });
    await loadRemisionDetalle(dnDoc.value.name);
    // La lista del lote dice dirección y prendas de cada remisión: se refresca al
    // momento, sin tener que recargar la página.
    await loadLotesProduccion();
    showToast("Remisión guardada");
  } catch (e) { showToast(e.message || "Error al guardar", "error"); }
  finally { advancing.value = false; }
}
async function validarRemision() {
  if (!dnDoc.value) return;
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.actualizar_remision", {
      name: dnDoc.value.name, posting_date: dnForm.posting_date || null,
      items: JSON.stringify(dnDoc.value.items),
      shipping_address_name: dnForm.shipping_address_name || null,
      customer_address: dnForm.customer_address || null,
      flete_proveedor: dnForm.flete_proveedor || null,
      flete_costo: dnForm.flete_costo || 0,
      flete_incluye_iva: dnForm.flete_incluye_iva ? 1 : 0,
    });
    const rv = await call("costeo_yelke.api.costeo_api.validar_remision", { name: dnDoc.value.name });
    await loadRemisionDetalle(dnDoc.value.name);
    await loadRelated();
    // La lista de remisiones del lote (y su estado) sale de los lotes: sin esto la
    // remisión validada seguía diciendo "Borrador" hasta recargar la página.
    await loadLotesProduccion();
    // Solo avanza el costeo a "Entregado" cuando la OV queda 100% entregada -- puede
    // haber más remisiones pendientes a otras direcciones del cliente.
    const completo = (related.delivery_per_delivered || 0) >= 99.99;
    if (completo && ORDER.indexOf(docStatus.value) < ORDER.indexOf("Entregado")) docStatus.value = "Entregado";
    const base = completo ? "Remisión validada · mercancía entregada al cliente" : `Remisión validada · saldo pendiente por entregar (${(100 - related.delivery_per_delivered).toFixed(0)}%)`;
    showToast(rv?.flete_journal_entry ? `${base} · flete registrado (${rv.flete_journal_entry})` : base);
  } catch (e) { showToast(e.message || "No se pudo validar la remisión", "error"); }
  finally { advancing.value = false; }
}

// El vencimiento sigue a la condición de pago y a la fecha de factura (mismo cálculo
// que hace ERPNext al guardar: el último plazo del calendario).
watch(() => [siForm.payment_terms_template, siForm.posting_date], async ([plantilla, fecha]) => {
  if (!plantilla || siValidated.value) return;
  try {
    const v = await call("costeo_yelke.api.costeo_api.vencimiento_por_condicion", { plantilla, fecha: fecha || null });
    if (v && siForm.payment_terms_template === plantilla) siForm.due_date = v;
  } catch { /* se queda la fecha anterior; ERPNext la recalcula al guardar */ }
});
async function generarFactura() {
  if (isNew.value) { showToast("Guarda el costeo primero", "error"); return; }
  if (activeSO.value?.docstatus !== 1) { showToast("Primero valida la orden de venta", "error"); return; }
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.crear_factura_venta", {
      costeo: docName.value,
      posting_date: siForm.posting_date || null, due_date: siForm.due_date || null,
      payment_terms_template: siForm.payment_terms_template, tc_name: siForm.tc_name || null,
      sales_order: activeSOName.value,
    });
    docStatus.value = "Completado";
    await loadRelated();
    showToast("Factura de venta creada");
  } catch (e) { showToast(e.message || "No se pudo crear la factura", "error"); }
  finally { advancing.value = false; }
}
async function guardarFactura() {
  if (!related.sales_invoice) return;
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.actualizar_factura_venta", {
      name: related.sales_invoice.name,
      posting_date: siForm.posting_date || null, due_date: siForm.due_date || null,
      payment_terms_template: siForm.payment_terms_template || null, tc_name: siForm.tc_name || null,
    });
    await loadRelated();
    showToast("Factura guardada");
  } catch (e) { showToast(e.message || "Error al guardar", "error"); }
  finally { advancing.value = false; }
}
// ── Facturas de compra (cuentas por pagar) ──
async function loadReporte() {
  if (!docName.value) return;
  reporteLoading.value = true;
  try {
    reporte.value = await call("costeo_yelke.api.costeo_api.get_reporte_final", { costeo: docName.value, sales_order: activeSOName.value || null });
  } catch (e) { showToast(e.message || "No se pudo calcular el reporte", "error"); reporte.value = null; }
  finally { reporteLoading.value = false; }
}
async function loadCompras() {
  try {
    const r = await call("costeo_yelke.api.costeo_api.get_facturas_compra", {
      costeo: docName.value, sales_order: activeSOName.value || null,
    });
    compras.materiales = r.materiales || []; compras.maquila = r.maquila || []; compras.fletes = r.fletes || [];
  } catch { /* ignore */ }
}
async function selectCompra(source_doctype, row) {
  pinvSel.value = { source_doctype, source_name: row.name, supplier_name: row.supplier_name || row.supplier, monto: row.base_net_total, pendiente: row.pendiente_facturar || 0 };
  if (row.invoice) { await loadPinv(row.invoice.name); } else { pinvDoc.value = null; }
}
async function generarFacturaCompra() {
  if (!pinvSel.value) return;
  advancing.value = true;
  try {
    const r = await call("costeo_yelke.api.costeo_api.crear_factura_compra", { source_doctype: pinvSel.value.source_doctype, source_name: pinvSel.value.source_name });
    await loadCompras();
    const fila = [...compras.maquila, ...compras.materiales].find((m) => m.name === pinvSel.value.source_name);
    if (fila) pinvSel.value.pendiente = fila.pendiente_facturar || 0;
    if (r.name) await loadPinv(r.name);
    showToast("Factura de compra registrada (borrador)");
  } catch (e) { showToast(e.message || "No se pudo registrar la factura", "error"); }
  finally { advancing.value = false; }
}
async function loadPinv(name) {
  try {
    const r = await call("costeo_yelke.api.costeo_api.get_factura_compra", { name });
    pinvDoc.value = r;
    pinvForm.posting_date = r.posting_date || ""; pinvForm.due_date = r.due_date || "";
    pinvForm.bill_no = r.bill_no || ""; pinvForm.bill_date = r.bill_date || "";
    pinvForm.payment_terms_template = r.payment_terms_template || ""; pinvForm.tc_name = r.tc_name || "";
    pinvForm.conversion_rate = r.conversion_rate || 1;
    pinvForm.flete_cobra_iva = r.flete_cobra_iva ? 1 : 0;
    ensurePrintFmt("Purchase Invoice"); previewKey.value++;
  } catch { /* ignore */ }
}
async function guardarPinv() {
  if (!pinvDoc.value) return;
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.actualizar_factura_compra", {
      name: pinvDoc.value.name, posting_date: pinvForm.posting_date || null, due_date: pinvForm.due_date || null,
      bill_no: pinvForm.bill_no || "", bill_date: pinvForm.bill_date || null,
      payment_terms_template: pinvForm.payment_terms_template || null, tc_name: pinvForm.tc_name || null,
      conversion_rate: Number(pinvForm.conversion_rate) || null,
      ...(pinvDoc.value.flete_importe > 0 ? { flete_cobra_iva: pinvForm.flete_cobra_iva ? 1 : 0 } : {}),
    });
    await loadPinv(pinvDoc.value.name);
    showToast("Factura de compra guardada");
  } catch (e) { showToast(e.message || "Error al guardar", "error"); }
  finally { advancing.value = false; }
}
async function validarPinv() {
  if (!pinvDoc.value) return;
  // Factura de flete: folio del CFDI y sus archivos antes de validar (también lo
  // exige el servidor, ver fletes.validar_factura_flete).
  if (pinvDoc.value.es_factura_flete && !(pinvForm.bill_no || "").trim()) {
    showToast("Captura el folio del CFDI del proveedor de paquetería antes de validar", "error");
    return;
  }
  advancing.value = true;
  try {
    await guardarPinv();
    await call("costeo_yelke.api.costeo_api.validar_documento", { doctype: "Purchase Invoice", name: pinvDoc.value.name });
    await loadCompras();
    const fila = [...compras.maquila, ...compras.materiales].find((m) => m.name === pinvSel.value?.source_name);
    if (fila && pinvSel.value) pinvSel.value.pendiente = fila.pendiente_facturar || 0;
    await loadPinv(pinvDoc.value.name);
    showToast("Factura de compra validada");
  } catch (e) { showToast(e.message || "No se pudo validar la factura", "error"); }
  finally { advancing.value = false; }
}

async function validarFactura() {
  if (!related.sales_invoice) return;
  advancing.value = true;
  try {
    await guardarFactura();
    await call("costeo_yelke.api.costeo_api.validar_documento", { doctype: "Sales Invoice", name: related.sales_invoice.name });
    await loadRelated();
    showToast("Factura de venta validada");
  } catch (e) { showToast(e.message || "No se pudo validar la factura", "error"); }
  finally { advancing.value = false; }
}

// ── Flujo de Producción (paso 4) -- confirmación ──
// get_flujo_operaciones devuelve las operaciones ya resueltas y agrupadas (mismo
// _resolve_production_operations que arma BOMs/OC). El usuario solo puede: reordenar
// los pasos (arrastrando la tarjeta) y, si el proceso no es lineal, decir de qué
// paso(s) recibe el material (op.recibe_de). El nombre de la pieza (op.produce) es
// automático y de solo lectura. Por defecto cada paso recibe del anterior; en
// cuanto se toca "Cambiar", ese paso queda "fijado" (recibe_custom) y ya no se
// reengancha solo al reordenar. Al confirmar se persiste vía
// guardar_flujo_operaciones y corre preparar_produccion.
const flujoOps = ref([]);
const flujoLoading = ref(false);
const flujoDirty = ref(false);
const flujoEdit = reactive({});
// Igual que flujoEdit, pero para el editor de "materiales directos" de cada
// tarjeta -- se abren independientes, cada uno con su propio op_key.
const matEdit = reactive({});
// Árbol de cada tarjeta (Servicios / Recibe de / Materia Prima / Entrega),
// contraído por default -- key "op_key::seccion". Windows-style: "+" despliega,
// "−" contrae; editar (recibe de / materia prima) fuerza la sección abierta.
const treeOpen = reactive({});
// "Recibe de" y "Materia Prima" arrancan desplegados (se ve el detalle sin tocar
// nada); "Servicios" y "Entrega" arrancan contraídos. Solo importa mientras el
// usuario no lo haya tocado a mano -- ahí manda lo que haya elegido.
function isTreeOpen(op, section) {
  if (flujoBloqueado.value) return true;
  const k = `${op.op_key}::${section}`;
  if (!(k in treeOpen)) return section === "recibe" || section === "materiales";
  return !!treeOpen[k];
}
function toggleTree(op, section) { const k = `${op.op_key}::${section}`; treeOpen[k] = !treeOpen[k]; }
// Marca si el flujo de manufactura ya se revisó/guardó -- lo lee el stepper
// (flujo-produccion-listo) y el botón principal. En Costear se pone en false al
// tocar etapas/materiales; al confirmar el Flujo de Producción pasa a true.
const manufacturaGuardada = ref(false);
// ¿op.recibe_de es EXACTAMENTE "del paso inmediato anterior"? Solo eso se re-engancha
// solo al reordenar. Un paso que arranca de materia prima (recibe_de vacío) se
// considera una decisión deliberada y NO se toca aunque se mueva de lugar.
function esRecibeLineal(ops, idx) {
  const r = ops[idx].recibe_de;
  return idx > 0 && r.length === 1 && r[0] === ops[idx - 1].op_key;
}
async function loadFlujoOps() {
  if (!docName.value) return;
  flujoLoading.value = true;
  flujoDirty.value = false;
  piezasEditando.value = false;
  Object.keys(flujoEdit).forEach(k => delete flujoEdit[k]);
  Object.keys(matEdit).forEach(k => delete matEdit[k]);
  Object.keys(treeOpen).forEach(k => delete treeOpen[k]);
  try {
    const r = await call("costeo_yelke.api.costeo_api.get_flujo_operaciones", { costeo: docName.value });
    flujoOps.value = (r?.productos || []).map(p => {
      const ops = (p.operaciones || []).map(o => ({ ...o, recibe_de: [...(o.recibe_de || [])] }));
      // Marca como "fijado" lo que NO es el default lineal -- eso es lo que el
      // reordenar debe respetar; el resto se reengancha solo.
      ops.forEach((o, i) => { o.recibe_custom = !esRecibeLineal(ops, i); });
      const subs = (p.sub_ensamblajes || []).map(s => ({ ...s, stage_ids: [...(s.stage_ids || [])] }));
      // Paso elegido a mano como "Aquí se unen las piezas" (Etapas Costeo.une_piezas).
      return { ...p, operaciones: ops, sub_ensamblajes: subs, union_op_key: (ops.find(o => o.une_piezas) || {}).op_key || "" };
    });
  } catch (e) { showToast(e.message || "No se pudo cargar el flujo", "error"); }
  finally { flujoLoading.value = false; }
}
// "Separar"/"unir" un servicio puntual de la fusión automática por proveedor+origen
// (ver toggle_no_agrupar) -- se guarda de inmediato en el servidor (no espera al
// botón "Confirmar"), porque cambia la forma misma del flujo (cuántos bloques hay),
// no solo un enlace de "recibe de" dentro de la forma ya calculada. Si había
// reacomodos sin guardar (flujoDirty), se pierden al recargar -- se avisa antes.
const agrupandoTid = ref("");
async function alternarNoAgrupar(servicio) {
  if (!servicio.stage_id || agrupandoTid.value) return;
  if (flujoDirty.value && !confirm("Tienes cambios de orden sin guardar en este paso -- se perderán al aplicar esto. ¿Continuar?")) return;
  agrupandoTid.value = servicio.stage_id;
  try {
    await call("costeo_yelke.api.costeo_api.toggle_no_agrupar", {
      costeo: docName.value, stage_id: servicio.stage_id, no_agrupar: servicio.no_agrupar ? 0 : 1,
    });
    await loadFlujoOps();
    showToast(servicio.no_agrupar ? "Servicio unido de nuevo con los demás" : "Servicio separado en su propio paso");
  } catch (e) { showToast(e.message || "No se pudo cambiar la agrupación", "error"); }
  finally { agrupandoTid.value = ""; }
}
// Reengancha los pasos NO fijados al paso inmediato anterior (según el orden actual).
function relinkLineal(prod) {
  prod.operaciones.forEach((o, i) => {
    if (o.recibe_custom) return;
    o.recibe_de = i === 0 ? [] : [prod.operaciones[i - 1].op_key];
  });
}
// Sube o baja UN paso a la vez (intercambio simple con el vecino inmediato) --
// reemplaza al arrastrar-y-soltar anterior: con la posición calculada a partir
// de coordenadas del mouse, un solo gesto podía interpretarse como un salto de
// varias posiciones y "mover todo" en vez de solo el paso tocado. Con botones
// subir/bajar el resultado es siempre exactamente ese: un intercambio con el
// vecino, nada más -- y el <TransitionGroup> de la plantilla anima el
// deslizamiento de ambas tarjetas a su nueva posición.
function moverOperacion(prod, idx, delta) {
  const to = idx + delta;
  if (to < 0 || to >= prod.operaciones.length) return;
  const arr = prod.operaciones;
  [arr[idx], arr[to]] = [arr[to], arr[idx]];
  // Una referencia "fijada" a un paso que ahora quedó DESPUÉS ya no es válida
  // (un paso no puede trabajar sobre algo que todavía no existe) -- se limpia.
  arr.forEach((o, i) => {
    const validos = new Set(arr.slice(0, i).map(x => x.op_key));
    const filtrado = o.recibe_de.filter(k => validos.has(k));
    if (filtrado.length !== o.recibe_de.length) { o.recibe_de = filtrado; o.recibe_custom = filtrado.length > 0; }
  });
  relinkLineal(prod);
  flujoDirty.value = true;
}
// Lista de nombres reales (no "el paso anterior" ni números) de dónde recibe
// esta operación -- "Materia prima" si no recibe de ningún paso.
function recibeDeLista(prod, op) {
  if (!op.recibe_de.length) return ["Materia prima"];
  return op.recibe_de
    .map(k => prod.operaciones.find(o => o.op_key === k))
    .filter(Boolean)
    .map(o => supplierLabel(prod, o));
}
// Nombre de una tarjeta: el proveedor solo, salvo que ese MISMO proveedor haga
// más de un paso no fusionado de este producto -- ahí se le agrega "(paso N)"
// para poder distinguirlos (ej. un taller que corta al inicio y también
// confecciona al final, con otros talleres en medio).
function supplierLabel(prod, op) {
  const nombre = op.supplier || "sin taller";
  const etiqueta = op.supplier ? nombreProveedor(op.supplier) : nombre;
  const mismos = prod.operaciones.filter(o => (o.supplier || "sin taller") === nombre);
  if (mismos.length <= 1) return etiqueta;
  const n = mismos.findIndex(o => o.op_key === op.op_key) + 1;
  return `${etiqueta} (${n})`;
}
// ¿esta operación tiene datos incompletos (sin proveedor o sin ningún servicio)?
// Pasa con etapas capturadas a medias en Costear -- avisa antes de que alguien
// "reciba de" un paso que en realidad todavía no tiene nada armado, sin bloquear
// nada (la referencia se puede guardar igual; el motor la tolera).
function opIncompleta(op) {
  return !op.supplier || !(op.servicios && op.servicios.length);
}
// Operaciones "terminales" EN VIVO -- las que nadie referencia en su recibe_de,
// recalculado sobre el estado actual en memoria (no el que vino del servidor) para
// que el aviso reaccione al instante mientras se edita/reordena. Debería haber
// exactamente una (la que entrega el producto terminado); más de una casi
// siempre significa que a alguna le falta indicar de cuál recibe.
function terminalKeysVivo(prod) {
  const referenciados = new Set();
  prod.operaciones.forEach(o => o.recibe_de.forEach(k => referenciados.add(k)));
  return prod.operaciones.filter(o => !referenciados.has(o.op_key)).map(o => o.op_key);
}
// ¿esta operación es una "terminal" sobrante (nadie la consume) cuando hay más de
// una? El ÚLTIMO paso de la lista NUNCA se marca -- ese sabemos que es el final
// real; el aviso es solo para el/los que quedaron sueltos ANTES de él.
function esHuerfano(prod, op) {
  const term = terminalKeysVivo(prod);
  if (term.length <= 1) return false;
  const esUltimo = prod.operaciones[prod.operaciones.length - 1]?.op_key === op.op_key;
  return term.includes(op.op_key) && !esUltimo;
}
// Cierre transitivo de "recibe_de" EN VIVO (mismo cálculo que _upstream_de en el
// backend, ver _resolve_production_operations) -- sobre el estado actual en
// memoria, no el que vino del servidor, para que el aviso reaccione al instante
// mientras se editan los checkboxes de "Recibe de".
function upstreamDeVivo(prod, key, visto) {
  visto = visto || new Set();
  const op = prod.operaciones.find(o => o.op_key === key);
  if (!op) return visto;
  for (const u of op.recibe_de) {
    if (!visto.has(u)) { visto.add(u); upstreamDeVivo(prod, u, visto); }
  }
  return visto;
}
// De los "recibe de" elegidos en ESTE paso, ¿cuáles también son alcanzables vía
// OTRO de los mismos elegidos? Ya no se quita nada por esto -- solo se avisa (ver
// _resolve_production_operations, "sin reducción transitiva"): puede ser
// exactamente lo que se quiere (una pieza que se une aparte, en paralelo a otro
// camino que también llega hasta aquí) o una selección de más -- la persona
// decide, el motor ya no borra solo.
function recibeRedundantesVivo(prod, op) {
  const directos = op.recibe_de;
  const redundantes = new Set();
  for (const a of directos) {
    for (const b of directos) {
      if (a !== b && upstreamDeVivo(prod, b).has(a)) redundantes.add(a);
    }
  }
  return redundantes;
}
function recibeRedundanteTexto(prod, op) {
  return [...recibeRedundantesVivo(prod, op)].map(k => {
    const o = prod.operaciones.find(x => x.op_key === k);
    return o ? supplierLabel(prod, o) : "?";
  }).join(", ");
}
// Advertencias por tarjeta: solo un ícono chico: un click lo abre/cierra --
// nada de banners genéricos, el aviso vive en el paso exacto que hay que revisar.
const warnOpen = reactive({});
function toggleWarn(op, tipo) {
  const k = `${op.op_key}::${tipo}`;
  warnOpen[k] = !warnOpen[k];
}
function isWarnOpen(op, tipo) {
  return !!warnOpen[`${op.op_key}::${tipo}`];
}
function toggleTrabajaSobre(op, key) {
  const i = op.recibe_de.indexOf(key);
  if (i === -1) op.recibe_de.push(key); else op.recibe_de.splice(i, 1);
  op.recibe_custom = true;
  flujoDirty.value = true;
}
function setTrabajaMateriaPrima(op) {
  op.recibe_de = [];
  op.recibe_custom = true;
  flujoDirty.value = true;
}
// A qué paso se le manda un material directo -- "" = automática (se atribuye
// sola al/los paso(s) que arrancan de materia prima directa). Un material solo
// puede estar asignado a UN paso a la vez: elegirlo en éste lo quita de
// cualquier otro donde estuviera.
function toggleMaterialOp(mat, opKey) {
  mat.op_key = mat.op_key === opKey ? "" : opKey;
  flujoDirty.value = true;
}
function materialesDirectosDe(prod, op) {
  return prod.materiales.filter(m => m.op_key === op.op_key);
}
// Sub-ensamblajes declarados (ver Costeo Sub Ensamblaje) -- filas puramente
// locales hasta que se guardan junto con el resto de "Flujo de Producción"
// (ver confirmarFlujo). Se marcan POR SERVICIO (`stage_ids`), no por tarjeta: un
// taller con varios servicios distintos necesita decir cuál es de cuál pieza, y
// ese detalle se perdía al marcar la tarjeta completa. El/los paso(s) terminal(es)
// nunca se marcan: toda pieza llega ahí, se muestran fijos (ver plantilla).
// Dónde se arma la prenda, EN VIVO sobre lo que está en pantalla -- misma regla que
// el backend (costeo._ops_prenda_armada): la PRIMERA operación no final que
// (1) ninguna pieza marca, (2) no tiene trabajo por pieza aguas abajo y (3) a la que
// llega la última operación de cada pieza. Las que siguen trabajan la prenda armada.
// Sin ensamble intermedio, se arma en la final (como siempre).
function armadoVivo(prod) {
  const ops = prod.operaciones || [];
  const terminales = new Set(terminalKeysVivo(prod));
  const noFinales = ops.filter((o) => !terminales.has(o.op_key));
  const piezas = (prod.sub_ensamblajes || []).filter((s) => (s.nombre || "").trim());
  const vacio = { ensamble: null, despues: new Set(), hayPiezas: false };
  const hijos = {};
  ops.forEach((o) => { hijos[o.op_key] = new Set(); });
  ops.forEach((o) => (o.recibe_de || []).forEach((u) => hijos[u] && hijos[u].add(o.op_key)));
  const memo = {};
  const abajo = (k) => {
    if (memo[k]) return memo[k];
    memo[k] = new Set();
    for (const h of hijos[k] || []) { memo[k].add(h); abajo(h).forEach((x) => memo[k].add(x)); }
    return memo[k];
  };
  // Elegido a mano ("Aquí se unen las piezas"): es una decisión, no una suposición,
  // así que se muestra en vivo aunque se estén capturando piezas.
  if (prod.union_op_key && noFinales.some((o) => o.op_key === prod.union_op_key)) {
    if (!piezas.length) return vacio;
    const e = prod.union_op_key;
    return { ensamble: e, despues: new Set(ops.filter((o) => abajo(e).has(o.op_key)).map((o) => o.op_key)), hayPiezas: true, elegida: true };
  }
  if (piezasEditando.value) return vacio;
  const piezasDe = {};
  for (const o of noFinales) {
    const st = new Set(o.stage_ids || (o.servicios || []).map((sv) => sv.stage_id));
    piezasDe[o.op_key] = piezas.filter((s) => s.stage_ids.some((x) => st.has(x))).map((s) => s.nombre);
  }
  const marcadas = new Set(noFinales.filter((o) => piezasDe[o.op_key].length).map((o) => o.op_key));
  if (!marcadas.size) return { ...vacio, hayPiezas: piezas.length > 0 };
  const ultima = {};
  for (const o of noFinales) for (const n of piezasDe[o.op_key]) ultima[n] = o.op_key;
  const e = noFinales.find((o) => !piezasDe[o.op_key].length && ![...abajo(o.op_key)].some((k) => marcadas.has(k)));
  if (!e || Object.values(ultima).some((u) => !abajo(u).has(e.op_key))) return { ...vacio, hayPiezas: true };
  return { ensamble: e.op_key, despues: new Set(ops.filter((o) => abajo(e.op_key).has(o.op_key)).map((o) => o.op_key)), hayPiezas: true };
}
// "arma" (aquí se unen todas las piezas), "armada" (recibe la prenda ya armada) o null.
function etiquetaArmado(prod, op) {
  const a = armadoVivo(prod);
  if (!a.hayPiezas) return null;
  if (a.ensamble) return op.op_key === a.ensamble ? "arma" : a.despues.has(op.op_key) ? "armada" : null;
  return terminalKeysVivo(prod).includes(op.op_key) ? "arma" : null;
}
function columnasMatriz(prod) {
  const terminales = terminalKeysVivo(prod);
  const armado = armadoVivo(prod);
  return (prod.operaciones || []).flatMap((op) =>
    (op.servicios || []).map((sv) => ({
      stage_id: sv.stage_id,
      // SIEMPRE el nombre del servicio: la fila ya trae el taller debajo, y poner
      // el taller arriba cuando hay un solo servicio lo dejaba repetido dos veces.
      titulo: sv.item,
      supplier: op.supplier,
      terminal: terminales.includes(op.op_key),
      arma: armado.ensamble === op.op_key,
      armada: armado.despues.has(op.op_key),
      op_key: op.op_key,
      elegida: !!armado.elegida && armado.ensamble === op.op_key,
      // El botón "Aquí se unen las piezas" va una vez por paso, en su primer servicio,
      // y solo si ninguna pieza tiene palomita en ese paso: si alguna se trabaja ahí
      // por separado, ahí no se pueden unir.
      primero: op.servicios[0] === sv,
      conPiezas: (prod.sub_ensamblajes || []).some((s) =>
        s.stage_ids.some((x) => (op.stage_ids || (op.servicios || []).map((v) => v.stage_id)).includes(x))),
    })),
  );
}
// Mientras se capturan las piezas no se muestra dónde se unen: la regla (ver
// armadoVivo) se cumple a medias con cada palomita -- con solo Corte marcado ya
// "cumple" el paso siguiente -- y el símbolo de unión brincaba de renglón en renglón.
// Se vuelve a mostrar al guardar (loadFlujoOps), ya con todo capturado.
const piezasEditando = ref(false);
// "Aquí se unen las piezas": la persona dice en qué paso se juntan para armar la
// prenda (antes solo se deducía de las casillas vacías, y eso no lo sabe nadie).
// En ese paso ya no se trabaja ninguna pieza por separado: se le quitan sus marcas.
function elegirUnion(prod, opKey) {
  const nueva = prod.union_op_key === opKey ? "" : opKey;
  prod.union_op_key = nueva;
  if (nueva) {
    const op = prod.operaciones.find((o) => o.op_key === nueva);
    const st = new Set(op?.stage_ids || (op?.servicios || []).map((sv) => sv.stage_id));
    prod.sub_ensamblajes.forEach((s) => { s.stage_ids = s.stage_ids.filter((x) => !st.has(x)); });
  }
  flujoDirty.value = true;
}
function agregarSubEnsamblaje(prod) {
  prod.sub_ensamblajes.push({ nombre: "", stage_ids: [], multiplicador: 1 });
  flujoDirty.value = true;
  piezasEditando.value = true;
}
function quitarSubEnsamblaje(prod, idx) {
  prod.sub_ensamblajes.splice(idx, 1);
  flujoDirty.value = true;
  piezasEditando.value = true;
}
function toggleSubEnsamblajeStage(s, stageId) {
  const i = s.stage_ids.indexOf(stageId);
  if (i === -1) s.stage_ids.push(stageId); else s.stage_ids.splice(i, 1);
  flujoDirty.value = true;
  piezasEditando.value = true;
}
// Guarda el flujo tal como está en pantalla (orden, "recibe de", materia prima por
// paso y piezas) SIN preparar producción -- para poder avanzar por partes. Lo usan
// "Guardar cambios" y "Confirmar y pasar a producción".
async function guardarFlujo() {
    const cambios = [];
    const materiales = [];
    for (const prod of flujoOps.value) {
      prod.operaciones.forEach((op, idx) => {
        cambios.push({
          op_key: op.op_key,
          orden: idx + 1,
          recibe_op_keys: op.recibe_de,
        });
      });
      (prod.materiales || []).forEach((mat) => {
        materiales.push({ material_id: mat.material_id, op_key: mat.op_key || "" });
      });
    }
    await call("costeo_yelke.api.costeo_api.guardar_flujo_operaciones", {
      costeo: docName.value, cambios: JSON.stringify(cambios), materiales: JSON.stringify(materiales),
    });
    for (const prod of flujoOps.value) {
      const filas = (prod.sub_ensamblajes || [])
        .filter(s => (s.nombre || "").trim())
        .map(s => ({ nombre: s.nombre.trim(), stage_ids: s.stage_ids, multiplicador: s.multiplicador || 1 }));
      const opUnion = prod.operaciones.find((o) => o.op_key === prod.union_op_key);
      await call("costeo_yelke.api.costeo_api.guardar_subensamblajes", {
        costeo: docName.value, producto: prod.finished_item, filas: JSON.stringify(filas),
        union_stage_id: opUnion?.servicios?.[0]?.stage_id || (opUnion?.stage_ids || [])[0] || "",
      });
    }
    flujoDirty.value = false;
}
const guardandoFlujo = ref(false);
async function guardarCambiosFlujo() {
  if (isNew.value) { showToast("Guarda el costeo primero", "error"); return; }
  guardandoFlujo.value = true;
  try {
    await guardarFlujo();
    // Recarga para ver lo que entendió el sistema con lo guardado (dónde se arma
    // la prenda, avisos de piezas).
    await loadFlujoOps();
    showToast("Flujo guardado");
  } catch (e) { showToast(e.message || "No se pudo guardar el flujo", "error"); }
  finally { guardandoFlujo.value = false; }
}
async function confirmarFlujo() {
  if (isNew.value) { showToast("Guarda el costeo primero", "error"); return; }
  advancing.value = true;
  try {
    await guardarFlujo();
    manufacturaGuardada.value = true;
    const ok = await materializeArticulosIfNeeded();
    if (!ok) return;
    const r = await call("costeo_yelke.api.costeo_api.preparar_produccion", { costeo: docName.value, sales_order: activeSOName.value || null });
    prepSteps.value = r.steps || [];
    activeStep.value = 5;
    if (!r.ok) { showToast("Hubo errores al preparar producción — revisa el detalle", "error"); return; }
    if (ORDER.indexOf(docStatus.value) < 3) docStatus.value = "En Producción";
    await loadPlan(docName.value, activeSOName.value);
    showToast("Plan de producción listo");
  } catch (e) { showToast(e.message || "Error al preparar producción", "error"); }
  finally { advancing.value = false; }
}
// Se llama desde "Preparar Manufactura" (una vez guardado el flujo) y también
// queda disponible en Producir como reintento.
async function prepararProduccion() {
  if (isNew.value) { showToast("Guarda el costeo primero", "error"); return; }
  advancing.value = true;
  try {
    if (!(await saveDoc())) return;
    manufacturaGuardada.value = true;
    const ok = await materializeArticulosIfNeeded();
    if (!ok) return;
    const r = await call("costeo_yelke.api.costeo_api.preparar_produccion", { costeo: docName.value, sales_order: activeSOName.value || null });
    prepSteps.value = r.steps || [];
    activeStep.value = 5;
    if (!r.ok) { showToast("Hubo errores al preparar producción — revisa el detalle", "error"); return; }
    if (ORDER.indexOf(docStatus.value) < 3) docStatus.value = "En Producción";
    await loadPlan(docName.value, activeSOName.value);
    showToast("Plan de producción listo");
  } catch (e) { showToast(e.message || "Error al preparar producción", "error"); }
  finally { advancing.value = false; }
}

// ── Borrador local (localStorage) ──────────────────────────────────────────
// Evita perder el avance si se recarga o se cierra la pestaña sin guardar (se
// vio en capacitación). Vive SOLO en este navegador -- no es un guardado real,
// nunca sustituye a "Guardar Costeo".
function draftStorageKey(id) { return `costeo-draft:${id || "new"}`; }

function hasMeaningfulDraftContent() {
  return !!(
    form.titulo || form.cliente || form.proyecto ||
    productos.value.length || detalles.value.length || etapas.value.length || tallas.value.length
  );
}

function saveDraftToLocalStorage() {
  if (!hasMeaningfulDraftContent()) return;
  try {
    localStorage.setItem(draftStorageKey(docName.value || route.params.name), JSON.stringify({
      savedAt: Date.now(),
      data: {
        form: { ...form },
        productos: productos.value,
        detalles: detalles.value,
        etapas: etapas.value,
        materialesEtapa: materialesEtapa.value,
        tallas: tallas.value,
      },
    }));
  } catch { /* localStorage lleno o bloqueado (modo privado) -- no es crítico */ }
}
function loadDraftFromLocalStorage(id) {
  try {
    const raw = localStorage.getItem(draftStorageKey(id));
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}
function clearDraft(id) {
  try { localStorage.removeItem(draftStorageKey(id)); } catch { /* ignore */ }
}

let draftTimer = null;
function scheduleDraftSave() {
  // No guardar borrador mientras se está cargando desde el servidor (fillFromDoc).
  if (loading.value || cargandoDoc) return;
  clearTimeout(draftTimer);
  draftTimer = setTimeout(saveDraftToLocalStorage, 800);
}
watch([form, productos, detalles, etapas, materialesEtapa, tallas], scheduleDraftSave, { deep: true });

// Ya no se avisa ni se ofrece recuperar nada -- cada quien es responsable de
// apretar "Guardar Costeo". Este respaldo en localStorage sigue escribiéndose
// solo por si alguien necesita rescatarlo a mano desde las herramientas del
// navegador tras un cierre accidental, pero se descarta solo pasada una semana
// para no ir acumulando borradores viejos sin que nadie los use.
function pruneDraftSiSeVencio() {
  const raw = loadDraftFromLocalStorage(docName.value || route.params.name);
  if (!raw) return;
  const UNA_SEMANA = 7 * 24 * 60 * 60 * 1000;
  if (!raw.savedAt || Date.now() - raw.savedAt > UNA_SEMANA) {
    clearDraft(docName.value || route.params.name);
  }
}

async function saveDoc() {
  // "Guardar Costeo" guarda tal cual está, falten o no datos -- ya no bloquea con
  // validate() (eso quedó solo para "Validar", ver validarCosteo). Un borrador a
  // medio capturar debe poderse guardar para no perder el avance.
  saving.value = true;
  try {
    const payload = buildPayload();
    if (isNew.value) { const created = await db.create("Costeo", payload); clearDraft("new"); router.replace({ name: "CosteoDetail", params: { name: created.name } }); await fillFromDoc(created); showToast("Costeo guardado"); }
    else { const updated = await db.update("Costeo", docName.value, payload); clearDraft(docName.value); await fillFromDoc(updated); showToast("Cambios guardados"); }
    return true;
  } catch (e) { showToast(e.message || "Error al guardar", "error"); return false; }
  finally { saving.value = false; }
}

// ── Advance ──
async function advance() {
  if (isNew.value) { showToast("Guarda el costeo primero", "error"); return; }
  const c = cta.value; if (!c) return;
  // "enviar" solo cambia de pestaña (no crea ni valida ningún documento) -- el
  // botón ya está deshabilitado por canAdvanceCta hasta que haya al menos un
  // lote recibido, así que llegar aquí ya implica que hay algo que entregar;
  // no espera el 100% porque las remisiones son por lote (parciales).
  if (c.action === "enviar") { await irAEntregar(); return; }
  if (c.action === "ir_preparar_manufactura") { if (soValidated.value) activeStep.value = 3; return; }
  if (c.action === "pasar_produccion") { pedirConfirmarFlujo(activeStep.value === 4 ? confirmarFlujo : prepararProduccion); return; }
  if (!canAdvance.value) { showToast("Completa los pendientes antes de avanzar", "error"); return; }
  advancing.value = true;
  try {
    if (c.action === "cotizar") {
      const ok = await materializeFinishedProductsIfNeeded();
      if (!ok) return;
      await call("costeo_yelke.api.costeo_api.crear_cotizacion", { costeo: docName.value }); docStatus.value = "Cotizado"; showToast("Cotización creada");
    }
    else if (c.action === "vender") { await call("costeo_yelke.api.costeo_api.crear_orden_venta", { costeo: docName.value }); docStatus.value = "Orden de Venta"; showToast("Orden de venta creada"); }
    else if (c.action === "enviar") { await irAEntregar(); return; }
    else if (c.action === "facturar") {
      activeStep.value = 7;
      return;
    }
    await loadRelated();
    activeStep.value = ORDER.indexOf(docStatus.value);
  } catch (e) { showToast(e.message || "No se pudo avanzar de fase", "error"); }
  finally { advancing.value = false; }
}

// ── Acciones específicas de cada paso ──
async function guardarBorradorOrdenVenta() {
  if (isNew.value) { showToast("Guarda el costeo primero", "error"); return; }
  if (!quotValidated.value) { showToast("Primero valida la cotización", "error"); return; }
  advancing.value = true;
  try {
    const res = await call("costeo_yelke.api.costeo_api.crear_orden_venta", {
      costeo: docName.value,
      delivery_date: soForm.delivery_date || null,
      payment_terms_template: soForm.payment_terms_template || null,
      tc_name: soForm.tc_name || null,
      po_no: soForm.po_no || null,
      oc_cliente_archivo: soForm.oc_cliente_archivo || null,
      currency: soForm.currency || null,
      selling_price_list: soForm.selling_price_list || null,
      taxes_and_charges: soForm.taxes_and_charges || null,
      contact_email: soForm.contact_email || null,
      contact_mobile: soForm.contact_mobile || null,
    });
    if (ORDER.indexOf(docStatus.value) < 2) docStatus.value = "Orden de Venta";
    soAutoExpandDone = true;
    expandedSOName.value = res.name;
    activeSOName.value = res.name;
    await loadRelated();
    previewKey.value++;
    showToast("Orden de venta guardada como borrador");
  } catch (e) { showToast(e.message || "No se pudo guardar la orden de venta", "error"); }
  finally { advancing.value = false; }
}
// Todo lo editable de la OV en borrador, de un solo golpe: sus datos, las tallas extra
// y el desglose por talla. Lo usan «Guardar cambios», «Validar orden» y el envío a
// aprobación, para no tener que guardar cada recuadro por separado.
async function persistirOrdenVenta(name) {
  await call("costeo_yelke.api.costeo_api.actualizar_orden_venta", {
    name,
    delivery_date: soForm.delivery_date || null,
    payment_terms_template: soForm.payment_terms_template || null,
    tc_name: soForm.tc_name || null,
    po_no: soForm.po_no || null,
    currency: soForm.currency || null,
    selling_price_list: soForm.selling_price_list || null,
    taxes_and_charges: soForm.taxes_and_charges || null,
    contact_email: soForm.contact_email || null,
    contact_mobile: soForm.contact_mobile || null,
  });
  const so = related.sales_orders.find((x) => x.name === name);
  if (so && so.docstatus === 0) {
    // Primero las tallas extra (reescriben las líneas de variante) y al final el
    // desglose regular, que reescribe la descripción del producto principal.
    await persistirVariantesOV(so);
    await persistirDesgloseOV(so);
  }
}
async function guardarCambiosOrdenVenta() {
  const name = expandedSOName.value;
  if (!name) return;
  advancing.value = true;
  try {
    await persistirOrdenVenta(name);
    await recargarFormulariosOV(name);
    showToast("Cambios guardados");
  } catch (e) { showToast(e.message || "No se pudieron guardar los cambios", "error"); }
  finally { advancing.value = false; }
}
async function recargarFormulariosOV(name) {
  await loadRelated();
  previewKey.value++;
  const so = related.sales_orders.find((x) => x.name === name);
  if (so) await Promise.all([loadSoDesgloseForm(so, true), loadSoVariantesForm(so, true)]);
}

// ── Validar / borrador ──
async function validarCosteo() {
  if (isNew.value) { showToast("Guarda el costeo primero", "error"); return; }
  if (!validate()) return;
  advancing.value = true;
  try {
    await saveDoc();
    const r = await call("costeo_yelke.api.costeo_api.validar_documento", { doctype: "Costeo", name: docName.value });
    docState.value = r.docstatus;
    showToast("Costeo validado");
  } catch (e) { showToast(e.message || "No se pudo validar el costeo", "error"); }
  finally { advancing.value = false; }
}
async function guardarBorradorCotizacion() {
  if (isNew.value) { showToast("Guarda el costeo primero", "error"); return; }
  advancing.value = true;
  try {
    const ok = await materializeFinishedProductsIfNeeded();
    if (!ok) return;
    const res = await call("costeo_yelke.api.costeo_api.crear_cotizacion", {
      costeo: docName.value,
      valid_till: cotForm.valid_till || null,
      payment_terms_template: cotForm.payment_terms_template || null,
      tc_name: cotForm.tc_name || null,
      custom_tipo_formato: cotForm.custom_tipo_formato || "Normal",
      currency: cotForm.currency || null,
      selling_price_list: cotForm.selling_price_list || null,
      taxes_and_charges: cotForm.taxes_and_charges || null,
      contact_email: cotForm.contact_email || null,
      contact_mobile: cotForm.contact_mobile || null,
    });
    if (ORDER.indexOf(docStatus.value) < 1) docStatus.value = "Cotizado";
    quotAutoExpandDone = true;
    expandedQuotName.value = res.name;
    await loadRelated();
    previewKey.value++;
    showToast("Cotización guardada como borrador");
  } catch (e) { showToast(e.message || "No se pudo guardar la cotización", "error"); }
  finally { advancing.value = false; }
}
// Cancelar una OV validada (solo quien valida documentos, ver costeo_api.cancelar_orden_venta).
const cancelarOV = reactive({ name: "", motivo: "" });
function abrirCancelarOV(so) { cancelarOV.name = so.name; cancelarOV.motivo = ""; }
async function confirmarCancelarOV() {
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.cancelar_orden_venta", { name: cancelarOV.name, motivo: cancelarOV.motivo });
    if (activeSOName.value === cancelarOV.name) activeSOName.value = null;
    showToast(`${cancelarOV.name} cancelada`);
    cancelarOV.name = "";
    await loadCosteoData({ silencioso: true });
  } catch (e) { showToast(e.message || "No se pudo cancelar la orden de venta", "error"); }
  finally { advancing.value = false; }
}
function openRechazarModal() { rechazarMotivo.value = ""; showRechazarModal.value = true; }
async function confirmarCotizacionRechazada() {
  const name = expandedQuotName.value;
  if (!name) return;
  advancing.value = true;
  try {
    const res = await call("costeo_yelke.api.quotation_api.marcar_rechazada", { name, motivo: rechazarMotivo.value || null });
    const q = related.quotations.find(x => x.name === name);
    if (q) { q.status = res.status; q.order_lost_reason = res.order_lost_reason; }
    if (related.quotation?.name === name) { related.quotation.status = res.status; related.quotation.order_lost_reason = res.order_lost_reason; }
    showRechazarModal.value = false;
    showToast("Cotización marcada como rechazada");
  } catch (e) { showToast(e.message || "Error al marcar como rechazada", "error"); }
  finally { advancing.value = false; }
}

function openAcordadoModal() {
  const d = new Date();
  d.setFullYear(d.getFullYear() + 1);
  acordadoValidUpto.value = d.toISOString().slice(0, 10);
  showAcordadoModal.value = true;
}

async function guardarPrecioAcordado() {
  const items = productos.value.filter(p => p.finished_item);
  if (!items.length) { showToast("El costeo no tiene productos", "error"); return; }
  advancing.value = true;
  try {
    for (const p of items) {
      await call("costeo_yelke.api.item_api.crear_precio_acordado", {
        item_code: p.finished_item,
        customer: form.cliente,
        price_list_rate: p.unit_sales_price || 0,
        valid_from: today(),
        valid_upto: acordadoValidUpto.value || null,
        costeo: docName.value || null,
      });
    }
    showAcordadoModal.value = false;
    showToast(`Precio acordado guardado para ${items.length} artículo(s) -- pendiente de validar`);
    await loadPrecioAcordadoStatus();
  } catch (e) { showToast(e.message || "Error al guardar el precio acordado", "error"); }
  finally { advancing.value = false; }
}

async function loadPrecioAcordadoStatus() {
  if (!docName.value) return;
  try {
    const r = await call("costeo_yelke.api.item_api.get_precio_acordado_costeo_status", { costeo: docName.value });
    Object.assign(precioAcordadoStatus, r);
  } catch { /* ignore */ }
}

async function validarPrecioAcordado() {
  if (!docName.value) return;
  advancing.value = true;
  try {
    const r = await call("costeo_yelke.api.item_api.validar_precios_acordados_costeo", { costeo: docName.value });
    showToast(`Precio acordado validado (${r.validated} artículo(s))`);
    await loadPrecioAcordadoStatus();
  } catch (e) { showToast(e.message || "No se pudo validar", "error"); }
  finally { advancing.value = false; }
}

async function guardarCambiosCotizacion() {
  const name = expandedQuotName.value;
  if (!name) return;
  if (!cotItems.value.some(r => r.item_code)) { showToast("La cotización necesita al menos un artículo", "error"); return; }
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.actualizar_cotizacion", {
      name,
      valid_till: cotForm.valid_till || null,
      payment_terms_template: cotForm.payment_terms_template || null,
      tc_name: cotForm.tc_name || null,
      custom_tipo_formato: cotForm.custom_tipo_formato || "Normal",
      currency: cotForm.currency || null,
      selling_price_list: cotForm.selling_price_list || null,
      taxes_and_charges: cotForm.taxes_and_charges || null,
      contact_email: cotForm.contact_email || null,
      contact_mobile: cotForm.contact_mobile || null,
      items: cotItems.value.filter(r => r.item_code).map(r => ({ name: r.name, item_code: r.item_code, item_name: r.item_name, description: r.description, qty: r.qty, rate: r.rate })),
    });
    await loadRelated();
    previewKey.value++;
    showToast("Cambios guardados");
  } catch (e) { showToast(e.message || "No se pudieron guardar los cambios", "error"); }
  finally { advancing.value = false; }
}
async function validarDoc(doctype, name, after) {
  advancing.value = true;
  try {
    // Validar una Cotización/OV puede terminar tocando el Costeo del lado del
    // servidor (la cantidad de alguna variante, ver
    // sincronizar_qty_variantes_a_costeo) -- se guarda cualquier edición local
    // pendiente ANTES de validar, para que ese guardado no pise después el
    // valor recién sincronizado al recargar (mismo cuidado que en
    // crearVarianteTalla).
    if (doctype === "Quotation" || doctype === "Sales Order") {
      if (!(await saveDoc())) return;
    }
    // La OV se valida con lo que se ve en pantalla: sus datos, tallas extra y desglose.
    if (doctype === "Sales Order") await persistirOrdenVenta(name);
    const res = await call("costeo_yelke.api.costeo_api.validar_documento", { doctype, name });
    await loadRelated();
    previewKey.value++;
    if (after) after();
    if (res.variantes_sincronizadas?.length) {
      const nombres = res.variantes_sincronizadas.map(v => v.talla_grupo_label || v.finished_item).join(", ");
      showToast(`Documento validado -- cantidad actualizada en el Costeo (${nombres})`);
      await recargarConservandoExpandido();
    } else {
      showToast("Documento validado");
    }
  } catch (e) { showToast(e.message || "No se pudo validar", "error"); }
  finally { advancing.value = false; }
}

async function loadCotDefaults() {
  try {
    const r = await call("costeo_yelke.api.costeo_api.get_cotizacion_defaults", { company: form.compania });
    cotDefaults.payment_terms_templates = r.payment_terms_templates || [];
    cotDefaults.terms = r.terms || [];
    cotDefaults.users = r.users || [];
    cotDefaults.oc_cliente_archivo_disponible = !!r.oc_cliente_archivo_disponible;
    cotDefaults.price_lists = r.price_lists || [];
    cotDefaults.currencies = r.currencies || [];
    cotDefaults.tax_templates = r.tax_templates || [];
  } catch { /* ignore */ }
}

// ── Materializar Producto Terminado (al pasar a cotización) ──
let materializeQueue = [];
let materializeCurrentProd = null;
let materializeDone = null;

async function itemExists(itemCode) {
  if (!itemCode) return false;
  const rows = await call("frappe.client.get_list", { doctype: "Item", filters: { name: itemCode }, fields: ["name"], limit_page_length: 1 });
  return !!(rows && rows.length);
}

// Recorre los productos del costeo; por cada finished_item que todavía no exista
// como Item real, pide al usuario materializarlo (modal) antes de seguir. Devuelve
// una promesa que resuelve `true` si todos quedaron listos, `false` si se canceló.
// Las variantes de talla entran aunque su cantidad siga pendiente (0): la cotización
// les pone una línea de referencia y para eso necesitan su artículo. Van DESPUÉS de
// todos los productos base, para que su código salga del artículo ya dado de alta.
async function materializeFinishedProductsIfNeeded() {
  materializeQueue = productos.value
    .filter(p => p.finished_item && ((p.qty || 0) > 0 || p.variante_talla_de))
    .sort((a, b) => (a.variante_talla_de ? 1 : 0) - (b.variante_talla_de ? 1 : 0));
  return new Promise((resolve) => {
    materializeDone = resolve;
    processNextMaterialize();
  });
}

async function processNextMaterialize() {
  if (!materializeQueue.length) { materializeDone && materializeDone(true); return; }
  const prod = materializeQueue[0];
  if (await itemExists(prod.finished_item)) { materializeQueue.shift(); return processNextMaterialize(); }
  // Variante cuyo producto base ya es artículo (se dio de alta antes): el modal abre
  // en modo "solo tallas" con TODAS las tallas pendientes de ese base, para capturar
  // su escala de precios por volumen antes de crearlas.
  materializeModal.soloTallas = !!(prod.variante_talla_de && await itemExists(prod.variante_talla_de));
  const baseDeTallas = materializeModal.soloTallas ? prod.variante_talla_de : prod.finished_item;
  materializeModal.tallasExtra = prod.variante_talla_de && !materializeModal.soloTallas ? [] : productos.value
    .filter(p => p.variante_talla_de === baseDeTallas)
    .map(p => ({ text: p.finished_item, label: p.talla_grupo_label || p.finished_item, precio: p.unit_sales_price || 0 }));
  materializeCurrentProd = prod;
  if (materializeModal.soloTallas) {
    materializeModal.text = prod.variante_talla_de;
    materializeModal.saving = false;
    materializeModal.open = true;
    return;
  }
  materializeModal.text = prod.finished_item;
  materializeModal.suggestedPrice = prod.unit_sales_price || 0;
  materializeModal.suggestedDescription = prod.description || "";
  materializeModal.suggestedImage = prod.image || "";
  materializeModal.esVariante = !!prod.variante_talla_de;
  materializeModal.suggestedCode = prod.variante_talla_de && await itemExists(prod.variante_talla_de)
    ? codigoVarianteTalla(prod.variante_talla_de, prod.talla_grupo_label) : "";
  materializeModal.saving = false;
  materializeModal.open = true;
}
// Mismo código que arma el servidor para una variante cuyo producto base ya era
// artículo (costeo_api._slug_item_code): "<artículo base>-<CABALLERO-XXL-3XL>".
function codigoVarianteTalla(base, etiqueta) {
  const slug = (etiqueta || "").replace(/[^\p{L}\p{N}_-]/gu, "-").replace(/^-+|-+$/g, "").toUpperCase();
  return slug ? `${base}-${slug}` : `${base}-VAR`;
}

// El servidor ya renombró el texto libre por el código del artículo en todas las tablas
// del costeo; aquí se hace lo mismo en la copia de la pantalla, o el siguiente guardado
// regresaría los nombres viejos (y cleanup_orphan_children borraría filas).
function renombrarProductoLocal(oldText, code) {
  if (!oldText || oldText === code) return;
  productos.value.forEach(p => {
    if (p.finished_item === oldText) { p.finished_item = code; p._lastFinishedItem = code; }
    if (p.variante_talla_de === oldText) p.variante_talla_de = code;
  });
  detalles.value.forEach(d => { if (d.finished_item === oldText) d.finished_item = code; });
  etapas.value.forEach(e => { if (e.producto_terminado === oldText) e.producto_terminado = code; });
  tallas.value.forEach(t => { if (t.finished_item === oldText) t.finished_item = code; });
}

function cancelMaterialize() {
  materializeModal.open = false;
  materializeQueue = [];
  if (materializeDone) materializeDone(false);
}

async function confirmMaterialize(payload) {
  const prod = materializeCurrentProd;
  materializeModal.saving = true;
  if (payload.solo_tallas) {
    try {
      const r = await call("costeo_yelke.api.costeo_api.materializar_variantes_talla", {
        costeo: docName.value, producto_base: prod.variante_talla_de,
        precios_variantes: JSON.stringify(payload.tallas_precios || {}),
      });
      (r?.variantes || []).forEach(v => renombrarProductoLocal(v.old, v.item_code));
      materializeModal.open = false;
      materializeQueue.shift();
      await processNextMaterialize();
    } catch (e) { showToast(e.message || "No se pudieron dar de alta las tallas extra", "error"); }
    finally { materializeModal.saving = false; }
    return;
  }
  try {
    const oldText = prod.finished_item;
    const r = await call("costeo_yelke.api.costeo_api.materializar_producto_terminado", {
      costeo: docName.value,
      old_finished_item: oldText,
      item_code: payload.item_code,
      item_name: payload.item_name,
      stock_uom: payload.stock_uom,
      precio_venta: payload.precio_venta,
      pricing_rules: JSON.stringify(payload.pricing_rules || []),
      description: payload.description || null,
      image: payload.image || null,
      precios_variantes: JSON.stringify(payload.tallas_precios || {}),
    });
    renombrarProductoLocal(oldText, r.item_code);
    // Sus variantes de talla se dieron de alta solas en el servidor (r.variantes).
    (r.variantes || []).forEach(v => renombrarProductoLocal(v.old, v.item_code));
    materializeModal.open = false;
    materializeQueue.shift();
    await processNextMaterialize();
  } catch (e) { showToast(e.message || "No se pudo crear el producto", "error"); }
  finally { materializeModal.saving = false; }
}

// ── Checklist de materialización (Fase 3, antes de preparar producción) ──
function tipoLabel(rowType) {
  return { material: "Materia Prima", servicio_etapa: "Servicio", subensamblaje_etapa: "Sub-ensamblaje" }[rowType] || rowType;
}
function tipoBadgeClass(rowType) {
  return {
    material: "bg-amber-50 text-amber-700",
    servicio_etapa: "bg-blue-50 text-blue-700",
    subensamblaje_etapa: "bg-green-50 text-green-700",
  }[rowType] || "bg-surface-raised text-ink-muted";
}
async function loadPendientesArticulos() {
  if (!docName.value) { pendientesArticulos.value = []; return; }
  try {
    const r = await call("costeo_yelke.api.costeo_api.get_articulos_pendientes", { costeo: docName.value });
    // Los sub-ensamblajes NO se muestran aquí -- son artículos internos del
    // proceso (nunca se compran ni se revisan uno por uno) y se materializan
    // solos, sin intervención, vía auto_materializar_subensamblajes justo antes
    // de "Pasar a producción" (ver materializeArticulosIfNeeded). Mostrarlos en
    // este checklist obligaría a resolverlos a mano cuando no hace falta.
    pendientesArticulos.value = (r?.grupos || []).filter(g => g.row_type !== "subensamblaje_etapa");
    pendientesAdvertencias.value = r?.advertencias || [];
    pendientesContext.company = r?.company || "";
    pendientesContext.almacen_materias_primas = r?.almacen_materias_primas || "";
    pendientesContext.almacen_trabajo_en_proceso = r?.almacen_trabajo_en_proceso || "";
    pendientesArticulos.value.forEach(sugerirArticuloExistente);
  } catch { /* ignore */ }
}
// Busca de una vez el Item existente más parecido al texto libre de cada grupo
// pendiente — si hay coincidencia, "Vincular existente" ya llega con una
// recomendación lista para confirmar; si no hay ninguna, se queda en blanco y se
// busca a mano, igual que antes.
async function sugerirArticuloExistente(g) {
  g._suggested = null;
  g._suggestedDismissed = false;
  try {
    const filters = ROW_TYPE_ITEM_FILTERS[g.row_type] || [];
    const results = await searchLink("Item", fuzzyQuery(g.texto), filters);
    if (results && results.length) {
      g._suggested = { item_code: results[0].value, label: results[0].description || results[0].value };
    }
  } catch { /* sin sugerencia — el usuario busca a mano */ }
}
// materializar_articulo reescribe el texto libre por el item_code directo en la
// BD (frappe.db.set_value), sin pasar por saveDoc() -- si no replicamos el mismo
// cambio aquí en el estado local, el próximo saveDoc() (p. ej. al reintentar
// "Guardar y preparar producción") vuelve a mandar el texto libre viejo y
// sobreescribe el Item recién creado/vinculado.
function applyMaterializacionLocal(rowType, texto, itemCode) {
  if (rowType === "material") {
    detalles.value.forEach(d => { if (d.concept_type === "Materia Prima" && d.item === texto) d.item = itemCode; });
  } else if (rowType === "servicio_etapa") {
    etapas.value.forEach(e => { if (e.servicio === texto) e.servicio = itemCode; });
  } else if (rowType === "subensamblaje_etapa") {
    etapas.value.forEach(e => { if (e.subensamblaje === texto) e.subensamblaje = itemCode; });
  }
}
async function resolverArticuloExistente(g, itemCode) {
  try {
    await call("costeo_yelke.api.costeo_api.materializar_articulo", {
      costeo: docName.value, row_type: g.row_type, texto: g.texto, item_code: itemCode,
      solo_vincular: true,
    });
    applyMaterializacionLocal(g.row_type, g.texto, itemCode);
    await loadPendientesArticulos();
    showToast(`"${g.texto}" vinculado a ${itemCode}`);
  } catch (e) { showToast(e.message || "No se pudo vincular el artículo", "error"); }
}
// El campo de búsqueda de "Vincular existente" es solo un BORRADOR (g._vincularValor)
// -- nunca dispara la vinculación por sí solo. Antes, como LinkInput emite
// update:model-value en cada tecla (no solo al elegir de la lista), escribir un
// par de letras ya alcanzaba a llamar a resolverArticuloExistente con ese texto a
// medias, reescribiendo el renglón del costeo (y, si no existía, hasta creando un
// Item nuevo con ese código truncado). Ahora hace falta un clic explícito en
// "Vincular" para confirmar -- ver confirmarVincularExistente.
function confirmarVincularExistente(g) {
  const v = (g._vincularValor || "").trim();
  if (!v) return;
  resolverArticuloExistente(g, v);
  g._vincularValor = "";
}
function openArticuloModal(g) { articuloModal.group = g; articuloModal.open = true; }
function cancelArticuloModal() { articuloModal.open = false; articuloModal.group = null; }
async function confirmArticuloModal(payload) {
  const g = articuloModal.group;
  articuloModal.saving = true;
  try {
    await call("costeo_yelke.api.costeo_api.materializar_articulo", {
      costeo: docName.value, row_type: g.row_type, texto: g.texto,
      item_code: payload.item_code, prefill: JSON.stringify(payload.prefill),
      supplier: payload.supplier, precio: payload.precio,
    });
    applyMaterializacionLocal(g.row_type, g.texto, payload.item_code);
    articuloModal.open = false; articuloModal.group = null;
    await loadPendientesArticulos();
    showToast(`"${g.texto}" creado y vinculado`);
  } catch (e) { showToast(e.message || "No se pudo crear el artículo", "error"); }
  finally { articuloModal.saving = false; }
}
// Se llama antes de disparar preparar_produccion. Los sub-ensamblajes se
// materializan solos (siempre son iguales: UDM Pieza, subcontratados) sin pedirle
// nada al usuario -- a diferencia de materiales/servicios, que sí requieren
// revisión manual (proveedor, precio) y quedan bloqueando el checklist. Si
// después de eso quedan artículos sin materializar, navega al checklist (paso 3)
// y bloquea el avance — evita que crear_boms_spa/crear_subcontracting_bom truenen
// a medio camino con texto libre.
async function materializeArticulosIfNeeded() {
  try {
    const r = await call("costeo_yelke.api.costeo_api.auto_materializar_subensamblajes", { costeo: docName.value });
    (r?.creados || []).forEach(itemCode => applyMaterializacionLocal("subensamblaje_etapa", itemCode, itemCode));
  } catch (e) { showToast(e.message || "No se pudieron crear los sub-ensamblajes automáticamente", "error"); return false; }
  await loadPendientesArticulos();
  if (pendientesArticulos.value.length) {
    activeStep.value = 3;
    showToast("Resuelve los artículos pendientes antes de preparar producción", "error");
    return false;
  }
  if (pendientesAdvertencias.value.length) {
    activeStep.value = 3;
    showToast(pendientesAdvertencias.value[0], "error");
    return false;
  }
  return true;
}

// ── Kebab ──
function onDocClick(e) { if (actionsRef.value && !actionsRef.value.contains(e.target)) actionsOpen.value = false; }

// Campos numéricos (cantidad, precio, %...) casi siempre arrancan en 0 -- sin
// esto, escribir encima significa primero borrar ese 0 a mano. Al enfocar
// cualquier <input type="number"> de esta página, se selecciona todo su
// contenido: el siguiente caracter que se teclee lo reemplaza de una vez: si
// solo se pasa de largo (tab/click afuera) sin escribir nada, el valor
// original se queda intacto -- no se vacía el campo por accidente.
function onNumberFocus(e) {
  if (e.target?.tagName === "INPUT" && e.target.type === "number") e.target.select();
}
function openCancel() { actionsOpen.value = false; confirmCancel.open = true; }
async function doCancel() {
  if (!headerDoc.value) return;
  const { doctype, name, isCosteo } = headerDoc.value;
  confirmCancel.loading = true;
  try {
    const r = await call("costeo_yelke.api.costeo_api.cancelar_documento", { doctype, name });
    if (isCosteo) docState.value = r.docstatus;
    else if (doctype === "Quotation") {
      if (related.quotation?.name === name) related.quotation.docstatus = r.docstatus;
      const qRow = related.quotations.find(x => x.name === name);
      if (qRow) qRow.docstatus = r.docstatus;
    }
    else if (doctype === "Sales Order") {
      if (related.sales_order?.name === name) related.sales_order.docstatus = r.docstatus;
      const soRow = related.sales_orders.find(x => x.name === name);
      if (soRow) soRow.docstatus = r.docstatus;
    }
    else if (doctype === "Delivery Note") {
      if (dnDoc.value?.name === name) dnDoc.value.docstatus = r.docstatus;
      const row = related.delivery_notes.find(d => d.name === name);
      if (row) row.docstatus = r.docstatus;
    }
    else if (doctype === "Sales Invoice" && related.sales_invoice) related.sales_invoice.docstatus = r.docstatus;
    confirmCancel.open = false;
    showToast(isCosteo ? "Costeo cancelado. Ahora puedes eliminarlo." : `${doctype} cancelado.`);
  } catch (e) { showToast(e.message || "No se pudo cancelar", "error"); }
  finally { confirmCancel.loading = false; }
}
function openDelete() { actionsOpen.value = false; confirmDelete.open = true; }
async function doDelete() { confirmDelete.loading = true; try { await call("costeo_yelke.api.costeo_api.delete_costeo", { name: docName.value }); confirmDelete.open = false; router.replace({ name: "CosteoList" }); } catch (e) { showToast(e.message || "Error al eliminar", "error"); } finally { confirmDelete.loading = false; } }
function openDeleteQuot(name) { confirmDeleteQuot.name = name; confirmDeleteQuot.open = true; }
async function doDeleteQuot() {
  confirmDeleteQuot.loading = true;
  try {
    await call("costeo_yelke.api.costeo_api.delete_quotation", { name: confirmDeleteQuot.name });
    if (expandedQuotName.value === confirmDeleteQuot.name) expandedQuotName.value = null;
    confirmDeleteQuot.open = false;
    await loadRelated();
    showToast("Cotización eliminada");
  } catch (e) { showToast(e.message || "No se pudo eliminar la cotización", "error"); }
  finally { confirmDeleteQuot.loading = false; }
}
function openDeleteSO(name) { confirmDeleteSO.name = name; confirmDeleteSO.open = true; }
async function doDeleteSO() {
  confirmDeleteSO.loading = true;
  try {
    await call("costeo_yelke.api.costeo_api.delete_sales_order", { name: confirmDeleteSO.name });
    if (expandedSOName.value === confirmDeleteSO.name) expandedSOName.value = null;
    if (activeSOName.value === confirmDeleteSO.name) activeSOName.value = null;
    confirmDeleteSO.open = false;
    await loadRelated();
    showToast("Orden de venta eliminada");
  } catch (e) { showToast(e.message || "No se pudo eliminar la orden de venta", "error"); }
  finally { confirmDeleteSO.loading = false; }
}
async function duplicateDoc() { actionsOpen.value = false; try { const res = await call("costeo_yelke.api.costeo_api.duplicate_costeo", { name: docName.value }); showToast("Costeo duplicado"); router.push({ name: "CosteoDetail", params: { name: res.name } }); } catch (e) { showToast(e.message || "Error al duplicar", "error"); } }
function openRevisionModal() { actionsOpen.value = false; revisionMotivo.value = ""; showRevisionModal.value = true; }
async function confirmarRevision() {
  revisionCreating.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.reabrir_costeo", { costeo: docName.value, motivo: revisionMotivo.value || "" });
    showRevisionModal.value = false;
    await loadCosteoData({ silencioso: true });
    activeStep.value = 0;
    showToast("El costeo está en borrador: corrígelo y vuelve a validarlo");
  } catch (e) { showToast(e.message || "No se pudo abrir el costeo para editar", "error"); }
  finally { revisionCreating.value = false; }
}
function printDoc() { actionsOpen.value = false; if (headerDoc.value) openPdf(headerDoc.value.doctype, headerDoc.value.name); }
function openInDesk() { actionsOpen.value = false; if (headerDoc.value) deskOpen(headerDoc.value.doctype, headerDoc.value.name); }

// ── Lifecycle ──
// Extraído de onMounted para poder recargar cuando se navega DENTRO de la misma
// página a otro Costeo (p.ej. al redirigir a la revisión recién creada) -- Vue Router
// reusa la instancia del componente cuando solo cambia el :name de la misma ruta, así
// que sin esto onMounted nunca se vuelve a disparar y la pantalla se queda mostrando
// el documento anterior con la URL ya apuntando al nuevo.
// De qué costeo ya se eligió el paso inicial (ver statusToStep en loadCosteoData).
let pasoAbiertoDe = null;
// `silencioso`: recarga del MISMO costeo después de una acción (crear variante,
// ajustar un material...) -- sin el spinner de pantalla completa, que desmonta el paso
// y regresa el scroll hasta arriba.
async function loadCosteoData(opciones = {}) {
  const silencioso = !!opciones?.silencioso;
  if (!silencioso) loading.value = true;
  if (isNew.value) {
    if (!form.compania && companyState.selected) form.compania = companyState.selected;
    pruneDraftSiSeVencio();
    loading.value = false;
    return;
  }
  try {
    const data = await db.get("Costeo", route.params.name);
    await fillFromDoc(data);
    // Abierto desde el panel de Dirección, un aviso o un enlace: el filtro de compañía
    // pasa a la del costeo.
    asegurarCompania(data["compañia"] || data.company);
    pruneDraftSiSeVencio();
    manufacturaGuardada.value = false;
    await loadRelated();
    await loadCotDefaults();
    await loadPlan(route.params.name, activeSOName.value);
    await loadPendientesArticulos();
    // Abre directo en el último paso alcanzado (no en el primero) -- para que
    // cualquiera que reabra el proyecto siga exactamente donde se quedó. Solo al
    // ABRIR el proyecto: las recargas de este mismo costeo (al validar la OV, al
    // sincronizar tallas, tras una aprobación...) dejan a la persona donde está --
    // validar la OV no debe brincar a Alta de Productos, todavía falta enviarla.
    if (pasoAbiertoDe !== route.params.name) {
      activeStep.value = statusToStep(docStatus.value, hasPlan.value, etapas.value.length, pendientesArticulos.value.length, soValidated.value);
      pasoAbiertoDe = route.params.name;
    }
    await loadRevisionInfo();
    cargarEncargos();
    // Llegada desde una lista de documentos (ej. /ordenes-compra): forzar el paso y
    // resaltar el documento exacto -- se consume una sola vez, luego se limpia la URL
    // para que un refresh no repita la animación.
    if (route.query.step !== undefined) {
      const q = Number(route.query.step);
      // El paso 6 ("Enviar") ya no existe: su pantalla se movió al paso Entrega de
      // cada lote y a la bandeja de Envíos. Los enlaces viejos caen en Producción.
      activeStep.value = q === 6 ? 5 : q;
    }
    if (route.query.highlight) {
      const target = String(route.query.highlight);
      const targetDoctype = route.query.doctype ? String(route.query.doctype) : null;
      // Limpiar la URL DESPUÉS de resaltar/hacer scroll -- router.replace() dispara su
      // propio ciclo de reactividad de forma asíncrona y, si corre en paralelo, puede
      // ganarle la carrera al scroll y dejarlo en 0 justo después de que ya se movió.
      await nextTick();
      await triggerHighlight(target, targetDoctype);
      // Solo se quita el resaltado: la vista de Producción (vista, lote, paso) que traiga
      // el enlace de una lista o de Mi panel tiene que quedarse.
      const { highlight: _h, doctype: _d, step: _s, ...resto } = route.query;
      router.replace({ path: route.path, query: activeStep.value === 5 ? resto : {} });
    }
    // El costeo se abre directo en el último paso alcanzado -- si ese paso carga
    // datos aparte (Flujo de Producción, Reporte final), hay que dispararlo aquí
    // (goStep solo corre al hacer clic en el stepper, no al montar).
    if (activeStep.value === 4) loadFlujoOps();
    if (activeStep.value === 8) loadReporte();
    // "Producción" (5) además recuerda el LOTE en el que te quedaste -- sin esto,
    // reabrir el costeo siempre dejaba la vista general de Producción, sin volver
    // a entrar al lote que se estaba trabajando (reportado en vivo). Se prioriza
    // la URL (?lote=, mismo patrón que ?step=, para links compartidos) y si no
    // trae nada, el último guardado en este navegador.
    if (activeStep.value === 5) await restaurarVistaProduccion();
    // Aviso "terminó X" / "regresó el encargo": abre Encargos con el paso propuesto.
    if (route.query.encargar) {
      const { encargar, ...resto } = route.query;
      abrirEncargos(String(encargar));
      router.replace({ path: route.path, query: resto });
    }
  } catch { showToast("No se pudo cargar el costeo", "error"); }
  finally { if (!silencioso) loading.value = false; }
}

onMounted(async () => {
  document.addEventListener("click", onDocClick, true);
  document.addEventListener("focusin", onNumberFocus);
  loadAllSuppliers();
  loadAllTallas();
  loadPuedeValidarCosteo();
  loadPermisosValidacion();
  await loadCosteoData();
  await loadPrecioAcordadoStatus();
});
watch(() => route.params.name, (newName, oldName) => {
  if (newName && newName !== oldName) loadCosteoData();
});
onUnmounted(() => {
  document.removeEventListener("click", onDocClick, true);
  document.removeEventListener("focusin", onNumberFocus);
});
</script>

<style scoped>
/* section-title/field-label/field-input/add-link/del-btn/doc-action/prod-* viven en
   src/style.css (@layer components) para que los componentes hijos también las usen. */
.prefix { @apply absolute left-3 top-1/2 -translate-y-1/2 text-ink-light text-sm; }
.suffix { @apply absolute right-3 top-1/2 -translate-y-1/2 text-ink-light text-sm; }
.action-item { @apply flex items-center gap-2.5 w-full px-4 py-2 text-sm text-ink hover:bg-surface-raised transition-colors text-left; }
.metric { @apply bg-white/60 rounded-lg px-3 py-2.5; }
.metric-label { @apply text-[11px] text-ink-muted; }
.metric-val { @apply text-lg font-semibold text-ink mt-0.5; }
.panel-enter-active { transition: opacity 0.12s ease, transform 0.12s ease; }
.panel-leave-active { transition: opacity 0.08s ease, transform 0.08s ease; }

/* "Flujo de Producción" (lista de pasos): al subir/bajar un paso con los botones,
   la tarjeta movida Y la que le cede el lugar se deslizan juntas a su nueva
   posición en vez de saltar de golpe -- así se ve claramente que solo se
   intercambiaron esas dos, nada más. */
.flujo-card-move { transition: transform 0.25s ease; }
/* Flujo confirmado (fieldset deshabilitado): los enlaces de edición -- "editar",
   "separar/unir", "+ agregar pieza", "Aquí se unen las piezas" -- se ocultan en vez
   de verse naranjas y activos sin hacer nada. */
fieldset:disabled button.text-brand-600 { display: none; }

/* "Flujo de Producción" (lista de pasos) -- botones e interruptor chicos a propósito,
   para que no compitan con los campos del paso (servicio/proveedor/precio). */
.mini-icon-btn {
  @apply w-5 h-5 flex-shrink-0 flex items-center justify-center rounded text-ink-light hover:bg-surface-raised hover:text-ink transition-colors disabled:opacity-30 disabled:hover:bg-transparent;
}
.mini-icon-btn svg { @apply w-3 h-3; }
.mini-icon-btn.danger:hover { @apply text-red-500 bg-red-50; }
.mini-switch { @apply relative inline-block; width: 26px; height: 15px; }
.mini-switch input { @apply absolute opacity-0 w-full h-full m-0 cursor-pointer z-10; }
.mini-track {
  @apply absolute inset-0 rounded-full bg-ink-xlight transition-colors;
}
.mini-track::before {
  content: ""; position: absolute; width: 11px; height: 11px; left: 2px; top: 2px;
  border-radius: 999px; background: #fff; box-shadow: 0 1px 2px rgb(0 0 0 / 0.25);
  transition: transform 0.15s ease;
}
.mini-switch input:checked + .mini-track { @apply bg-brand-500; }
.mini-switch input:checked + .mini-track::before { transform: translateX(11px); }

/* Llegada desde una lista de documentos: un borde naranja que ilumina una vez la
   tarjeta/panel exacto, para ubicarlo sin tener que buscarlo entre los demás lotes. */
.doc-highlight-flash {
  border-radius: 0.75rem;
  animation: doc-highlight-pulse 1.6s ease-out;
}
@keyframes doc-highlight-pulse {
  0%   { box-shadow: 0 0 0 0 rgba(249, 115, 22, 0.55); }
  15%  { box-shadow: 0 0 0 4px rgba(249, 115, 22, 0.45); }
  100% { box-shadow: 0 0 0 0 rgba(249, 115, 22, 0); }
}
.panel-enter-from, .panel-leave-to { opacity: 0; transform: translateY(-4px) scale(0.98); }
</style>
