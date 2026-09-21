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

    <!-- Modal: guardar como plantilla -->
    <div v-if="tplModal.open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="tplModal.open = false">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm p-5">
        <p class="text-sm font-semibold text-ink">Guardar como plantilla</p>
        <p class="text-[12px] text-ink-muted mt-0.5 mb-4">
          Cada producto de este costeo se guarda como su propia plantilla independiente (materiales, etapas y márgenes), sin cliente. Se crearán {{ productosConNombre.length }} plantilla{{ productosConNombre.length === 1 ? "" : "s" }}:
        </p>
        <ul class="text-[13px] text-ink mb-4 list-disc pl-5 space-y-0.5">
          <li v-for="p in productosConNombre" :key="p">{{ p }}</li>
        </ul>
        <div class="flex gap-2 justify-end">
          <button class="px-3 py-1.5 text-[13px] text-ink-muted hover:bg-surface-raised rounded-lg" @click="tplModal.open = false">Cancelar</button>
          <button :disabled="!productosConNombre.length || tplModal.saving" class="px-4 py-1.5 text-[13px] font-medium text-white bg-brand-500 hover:bg-brand-600 disabled:opacity-50 rounded-lg flex items-center gap-2" @click="guardarComoPlantilla">
            <svg v-if="tplModal.saving" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
            {{ tplModal.saving ? "Guardando…" : "Guardar plantillas" }}
          </button>
        </div>
      </div>
    </div>

    <!-- Modal: actualizar cantidades por talla (cuando el cliente ya confirmó) -->
    <div v-if="actualizarTallasModal.open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="actualizarTallasModal.open = false">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-lg p-5">
        <p class="text-sm font-semibold text-ink">Actualizar cantidades por talla</p>
        <p class="text-[12px] text-ink-muted mt-0.5 mb-4">
          Captura la cantidad real que ya confirmó el cliente para cada talla pendiente. Si hay una Cotización u Orden de Venta en borrador ligada a este costeo, sus líneas se actualizan solas.
        </p>
        <div class="space-y-2 max-h-[50vh] overflow-y-auto mb-4">
          <div v-for="f in actualizarTallasModal.filas" :key="f.talla_row" class="flex items-center gap-2 border border-surface-border rounded-lg p-2.5">
            <div class="flex-1 min-w-0">
              <p class="text-[13px] font-medium text-ink truncate">{{ f.finished_item }}</p>
              <p class="text-[12px] text-ink-muted truncate">{{ f.label }}</p>
            </div>
            <input v-model.number="f.qtyNueva" type="number" min="0" class="field-input w-24 text-right" placeholder="Cantidad" />
          </div>
        </div>
        <p v-if="actualizarTallasModal.error" class="text-[12px] text-red-600 mb-3">{{ actualizarTallasModal.error }}</p>
        <div class="flex gap-2 justify-end">
          <button class="px-3 py-1.5 text-[13px] text-ink-muted hover:bg-surface-raised rounded-lg" @click="actualizarTallasModal.open = false">Cancelar</button>
          <button :disabled="actualizarTallasModal.saving" class="px-4 py-1.5 text-[13px] font-medium text-white bg-brand-500 hover:bg-brand-600 disabled:opacity-50 rounded-lg flex items-center gap-2" @click="confirmarActualizarTallas">
            <svg v-if="actualizarTallasModal.saving" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
            {{ actualizarTallasModal.saving ? "Guardando…" : "Confirmar cantidades" }}
          </button>
        </div>
      </div>
    </div>

    <!-- Modal: materializar producto terminado (al pasar a cotización) -->
    <MaterializeProductModal
      :open="materializeModal.open"
      :finished-item-text="materializeModal.text"
      :suggested-price="materializeModal.suggestedPrice"
      :suggested-description="materializeModal.suggestedDescription"
      :suggested-image="materializeModal.suggestedImage"
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
                <button class="action-item" @click="openTplModal">Guardar como plantilla</button>
                <button v-if="tallasPendientes.length" class="action-item text-amber-700" @click="openActualizarTallasModal">
                  Actualizar cantidades por talla
                  <span class="ml-auto text-[10px] font-semibold bg-amber-100 text-amber-700 rounded-full px-1.5 py-0.5">{{ tallasPendientes.length }}</span>
                </button>
                <button class="action-item" @click="actionsOpen = false; showHistorialModal = true">Ver historial</button>
              </template>
              <button class="action-item" @click="printDoc">Imprimir / PDF</button>
              <button class="action-item" @click="openInDesk">Abrir en Desk</button>
            </div>
            <div class="border-t border-surface-border py-1">
              <button v-if="headerDoc.docstatus === 1" class="action-item text-amber-600 hover:bg-amber-50 hover:text-amber-700" @click="openCancel">Cancelar validación</button>
              <button v-if="headerDoc.isCosteo && (headerDoc.docstatus === 1 || headerDoc.docstatus === 2)" class="action-item text-brand-600 hover:bg-brand-50 hover:text-brand-700" @click="openRevisionModal">Crear revisión</button>
              <button v-if="headerDoc.isCosteo" class="action-item text-red-500 hover:bg-red-50 hover:text-red-600" @click="openDelete">Eliminar</button>
            </div>
          </div>
        </Transition>
      </div>

      <span v-if="headerDoc && headerDoc.docstatus === 1" class="h-8 px-3 flex items-center gap-1.5 text-[13px] font-medium text-green-700 bg-green-50 rounded-lg">
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        Validado
      </span>
      <span v-else-if="headerDoc && headerDoc.docstatus === 2" class="h-8 px-3 flex items-center gap-1.5 text-[13px] font-medium text-red-600 bg-red-50 rounded-lg">
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/></svg>
        Cancelado
      </span>

      <button v-if="docState === 0" :disabled="saving" class="h-8 px-3.5 text-[13px] font-medium text-ink border border-surface-border rounded-lg hover:bg-surface-raised transition-colors disabled:opacity-50 flex items-center gap-2" @click="saveDoc">
        <svg v-if="saving" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
        {{ saving ? "Guardando…" : (isNew ? "Guardar Costeo" : "Guardar") }}
      </button>

      <button
        v-if="!isNew && docState === 0"
        :disabled="advancing || !puedeValidarCosteo"
        class="h-8 px-3.5 text-[13px] font-semibold text-brand-700 bg-brand-50 rounded-lg hover:bg-brand-100 transition-colors disabled:opacity-50 flex items-center gap-1.5"
        @click="validarCosteo"
        :title="puedeValidarCosteo ? 'Guarda y valida el costeo para poder avanzar' : 'Necesitas el rol \'Aprobador de Documentos Yelke\' para validar'"
      >
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        Validar
      </button>

      <button v-if="!isNew && cta" :disabled="advancing || !canAdvanceCta" class="h-8 px-4 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 transition-colors disabled:opacity-40 flex items-center gap-1.5" :title="canAdvanceCta ? '' : 'Completa los pendientes'" @click="advance">
        <svg v-if="advancing" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
        {{ cta.label }}
        <svg v-if="!advancing" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 7l5 5-5 5M6 12h12"/></svg>
      </button>
    </PageHeader>

    <CosteoStepper
      v-if="!isNew && docName" :model-value="docStatus" :active-step="activeStep"
      :lotes="lotesParaStepper" :active-lote-ref="loteActivoRef"
      :vender-listo="soValidated"
      :alta-productos-listo="pendientesArticulos.length === 0"
      :flujo-produccion-listo="manufacturaGuardada || hasPlan"
      @select="goStep" @select-lote="goLote" @create-lote="onCrearLoteDesdeStepper"
    />

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

    <!-- Borrador recuperado de este navegador (localStorage) -- por si se recarga o
         se cierra la pestaña sin haber apretado "Guardar Costeo". -->
    <div v-if="draftBanner.show" class="mx-5 mt-4 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 flex items-center justify-between gap-3">
      <div class="flex items-center gap-2.5">
        <svg class="w-4 h-4 text-amber-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M5.07 19h13.86a2 2 0 001.71-3l-6.93-12a2 2 0 00-3.42 0l-6.93 12a2 2 0 001.71 3z"/></svg>
        <p class="text-[13px] text-ink-muted">
          Se encontró un <span class="font-medium text-ink">borrador sin guardar</span> de {{ draftAgeLabel() }} en este navegador.
        </p>
      </div>
      <div class="flex items-center gap-2 flex-shrink-0">
        <button class="text-[12.5px] text-ink-muted hover:text-ink px-2 py-1" @click="discardDraft">Descartar</button>
        <button class="text-[12.5px] font-semibold text-amber-700 hover:text-amber-800 px-2 py-1" @click="restoreDraft">Recuperar</button>
      </div>
    </div>

    <div v-if="loading" class="flex-1 flex items-center justify-center text-ink-light">
      <svg class="w-7 h-7 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
    </div>

    <!-- ══════════ STEP 0 · COSTEAR ══════════ -->
    <div v-else-if="activeStep === 0" class="p-5 pb-40">
      <fieldset :disabled="!canEditCosteo" class="border-0 p-0 m-0 min-w-0" :class="!canEditCosteo ? 'opacity-70' : ''">
      <div class="flex gap-5 items-start max-w-[1400px] mx-auto">
      <div class="flex-1 min-w-0 space-y-4">
        <section class="bg-white rounded-xl border border-surface-border">
          <div class="px-5 py-3 border-b border-surface-border"><h3 class="section-title">Información general</h3></div>
          <div class="p-5 grid grid-cols-2 gap-4">
            <div class="col-span-2">
              <label class="field-label">Título <span class="text-ink-light font-normal">(opcional, para identificarlo más fácil)</span></label>
              <input v-model="form.titulo" type="text" class="field-input" placeholder="Ej: Playeras Polo Ferromex 2026" />
            </div>
            <div><label class="field-label">Cliente <span class="text-red-400">*</span></label><LinkInput v-model="form.cliente" doctype="Customer" placeholder="Buscar cliente…" :error="!!errors.cliente" /></div>
            <div><label class="field-label">Fecha <span class="text-red-400">*</span></label><input v-model="form.fecha" type="date" class="field-input" :class="errors.fecha ? 'border-red-400' : ''" /></div>
            <div><label class="field-label">Compañía <span class="text-red-400">*</span></label><LinkInput v-model="form.compania" doctype="Company" placeholder="Compañía…" :error="!!errors.compania" /></div>
            <div class="flex items-end pb-1.5">
              <label class="flex items-center gap-2 text-[13px] text-ink cursor-pointer select-none">
                <input v-model="form.guardar_como_plantilla" type="checkbox" class="w-4 h-4 rounded border-surface-border" />
                Guardar productos como plantilla al guardar
              </label>
            </div>
          </div>
          <!-- Almacenes y centro de costos: se rellenan solos al elegir la compañía.
               Esta sección solo se muestra cuando get_company_defaults NO logró
               resolver alguno por nombre -- si ya se autocompletaron los 3, se
               mantiene oculta para no meter ruido visual en el flujo normal. -->
          <div v-if="form.compania && faltanAlmacenes" class="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3 pt-3 border-t border-surface-border">
            <div>
              <label class="field-label">Almacén de materia prima <span class="text-red-400">*</span></label>
              <LinkInput v-model="form.almacen_materias_primas" doctype="Warehouse" :filters="warehouseFilters" placeholder="Almacén…" :error="!!errors.almacen_materias_primas" />
            </div>
            <div>
              <label class="field-label">Almacén de trabajo en proceso <span class="text-red-400">*</span></label>
              <LinkInput v-model="form.almacen_trabajo_en_proceso" doctype="Warehouse" :filters="warehouseFilters" placeholder="Almacén…" :error="!!errors.almacen_trabajo_en_proceso" />
            </div>
            <div>
              <label class="field-label">Centro de costos <span class="text-red-400">*</span></label>
              <LinkInput v-model="form.centro_de_costos" doctype="Cost Center" :filters="costCenterFilters" placeholder="Centro de costos…" :error="!!errors.centro_de_costos" />
            </div>
          </div>
          <p v-if="form.compania && faltanAlmacenes" class="text-[11.5px] text-amber-700 mt-2 flex items-start gap-1.5">
            <svg class="w-4 h-4 flex-shrink-0 mt-px" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M5.07 19h13.86a2 2 0 001.71-3l-6.93-12a2 2 0 00-3.42 0l-6.93 12a2 2 0 001.71 3z"/></svg>
            No encontramos los almacenes de esta compañía por su nombre — elígelos aquí arriba para poder guardar.
          </p>
        </section>

        <section class="bg-white rounded-xl border border-surface-border">
          <div class="px-5 py-3 border-b border-surface-border flex items-center justify-between">
            <h3 class="section-title">Productos a costear</h3>
            <button class="add-link" @click="addProducto"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>Agregar producto</button>
          </div>

          <div v-if="!productos.length" class="py-12 flex flex-col items-center gap-2 text-ink-light">
            <svg class="w-9 h-9 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.2"><path stroke-linecap="round" stroke-linejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10"/></svg>
            <p class="text-sm">Agrega al menos un producto terminado</p>
            <button class="text-xs text-brand-600 font-medium hover:underline" @click="addProducto">+ Agregar producto</button>
          </div>

          <div v-else class="divide-y divide-surface-border">
            <div v-for="(prod, idx) in productos" :key="prod._tid">
              <div class="flex items-center gap-3 px-5 py-3 cursor-pointer hover:bg-surface-raised/50 transition-colors group" @click="toggleProduct(prod._tid)">
                <svg class="w-4 h-4 text-ink-light flex-shrink-0 transition-transform" :class="expandedTid === prod._tid ? 'rotate-90' : ''" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
                <img v-if="prod.image" :src="prod.image" class="w-9 h-9 rounded-lg object-cover border border-surface-border flex-shrink-0" alt="" />
                <div v-else class="w-9 h-9 rounded-lg bg-surface-raised border border-surface-border flex items-center justify-center flex-shrink-0">
                  <svg class="w-4 h-4 text-ink-xlight" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.6"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                </div>
                <div class="flex-1 min-w-0">
                  <span v-if="prod.finished_item" class="font-medium text-sm text-ink">{{ prod.finished_item }}</span>
                  <span v-else class="text-sm text-ink-light italic">Sin producto</span>
                  <span v-if="prod.qty" class="ml-2 text-xs text-ink-light">× {{ prod.qty }}</span>
                </div>
                <div class="flex items-center gap-3 text-xs">
                  <span class="text-ink-light">Costo <span class="text-ink font-medium">{{ fmtC(prod.total_unit_cost) }}</span></span>
                  <span class="font-semibold text-ink">{{ fmtC(prod.total_sales_price) }}</span>
                </div>
                <button class="opacity-0 group-hover:opacity-100 w-6 h-6 flex items-center justify-center rounded hover:bg-red-50 hover:text-red-500 text-gray-300 transition-all flex-shrink-0" @click.stop="removeProducto(idx)" title="Eliminar">
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
                </button>
              </div>

              <div v-if="expandedTid === prod._tid" class="bg-surface-raised/40 border-t border-surface-border px-5 pt-4 pb-14 space-y-4">
                <div class="flex gap-4 items-start">
                  <div class="w-36 h-36 flex-shrink-0 rounded-lg border border-surface-border overflow-hidden bg-white relative group/img" :class="canEditCosteo ? 'cursor-pointer' : 'cursor-default'" @click="pickImage(prod)" title="Subir imagen del producto">
                    <img v-if="prod.image" :src="prod.image" class="w-full h-full object-cover" alt="" />
                    <div v-else class="w-full h-full flex items-center justify-center text-ink-xlight">
                      <svg class="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.4"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                    </div>
                    <div class="absolute inset-0 bg-black/50 opacity-0 group-hover/img:opacity-100 transition-opacity flex items-center justify-center">
                      <svg class="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/><path stroke-linecap="round" stroke-linejoin="round" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                    </div>
                  </div>
                  <div class="flex-1 grid grid-cols-3 gap-3">
                    <div class="col-span-2"><label class="field-label">Producto terminado <span class="text-red-400">*</span></label><LinkInput v-model="prod.finished_item" doctype="Item" :filters="ITEM_FILTERS.terminado" placeholder="Producto terminado…" @update:model-value="onProductoItemChange(prod)" /></div>
                    <div><label class="field-label">Cantidad <span class="text-red-400">*</span></label><input v-model.number="prod.qty" type="number" min="1" class="field-input" @input="onProdQtyChange(prod)" /></div>
                    <div class="col-span-3"><label class="field-label">Descripción <span class="text-ink-light font-normal">(opcional)</span></label><textarea v-model="prod.description" rows="2" class="field-input resize-none" placeholder="Descripción del producto…"></textarea></div>
                  </div>
                </div>

                <div class="bg-white rounded-lg border border-surface-border overflow-hidden">
                  <div class="p-4">
                    <div class="flex items-center gap-2 mb-3">
                      <svg class="w-4 h-4 text-ink-light flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V6m0 10v2m9-8a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                      <h4 class="text-[13px] font-semibold text-ink">Costo y precio de venta</h4>
                    </div>
                    <div class="grid grid-cols-6 gap-2">
                      <div><label class="field-label mb-0.5">Overhead %</label><div class="relative"><input v-model.number="prod.overhead_pct" type="number" min="0" max="100" class="field-input py-1.5 pr-7" @input="recalcProducto(prod)" /><span class="suffix">%</span></div></div>
                      <div><label class="field-label mb-0.5">Flete / envío</label><div class="relative"><span class="prefix">$</span><input v-model.number="prod.shipping_cost" type="number" min="0" class="field-input py-1.5 pl-6" @input="recalcProducto(prod)" /></div></div>
                      <div><label class="field-label mb-0.5">Etiquetado</label><div class="relative"><span class="prefix">$</span><input v-model.number="prod.labeling_cost" type="number" min="0" class="field-input py-1.5 pl-6" @input="recalcProducto(prod)" /></div></div>
                      <div><label class="field-label mb-0.5">Empaquetado</label><div class="relative"><span class="prefix">$</span><input v-model.number="prod.packaging_cost" type="number" min="0" class="field-input py-1.5 pl-6" @input="recalcProducto(prod)" /></div></div>
                      <div><label class="field-label mb-0.5">Margen %</label><div class="relative"><input v-model.number="prod.margin_pct" type="number" min="0" max="99" class="field-input py-1.5 pr-7" @input="onMarginChange(prod)" /><span class="suffix">%</span></div></div>
                      <div>
                        <label class="field-label mb-0.5 flex items-center gap-1">Precio unit.<span v-if="prod.precio_manual" class="text-[9.5px] font-normal text-brand-600 bg-brand-50 border border-brand-200 rounded px-1" title="Precio fijado a mano -- no se recalcula aunque cambien costos, el margen se ajusta a él">fijo</span></label>
                        <div class="relative"><span class="prefix text-brand-600">$</span><input v-model.number="prod.unit_sales_price" type="number" min="0" step="0.01" class="field-input py-1.5 pl-6 text-brand-600 font-semibold" @input="onPriceChange(prod)" /></div>
                      </div>
                    </div>
                  </div>

                  <div class="bg-surface-raised/60 border-t border-surface-border px-4 py-3 grid grid-cols-3 gap-3">
                    <div class="metric bg-white">
                      <p class="metric-label">Telas <span class="font-normal text-ink-xlight">/ pza</span></p>
                      <p class="metric-val text-[15px]">{{ fmtC(telasCost(prod)) }}</p>
                      <p class="text-[11px] text-ink-light mt-0.5">{{ fmtC(telasCost(prod) * (prod.qty || 0)) }} <span class="text-ink-xlight">total × {{ prod.qty || 0 }} pzas</span></p>
                    </div>
                    <div class="metric bg-white">
                      <p class="metric-label">Avíos <span class="font-normal text-ink-xlight">/ pza</span></p>
                      <p class="metric-val text-[15px]">{{ fmtC(aviosCost(prod)) }}</p>
                      <p class="text-[11px] text-ink-light mt-0.5">{{ fmtC(aviosCost(prod) * (prod.qty || 0)) }} <span class="text-ink-xlight">total × {{ prod.qty || 0 }} pzas</span></p>
                    </div>
                    <div class="metric bg-white">
                      <p class="metric-label">Servicios y otros <span class="font-normal text-ink-xlight">/ pza</span></p>
                      <p class="metric-val text-[15px]">{{ fmtC(serviciosCost(prod)) }}</p>
                      <p class="text-[11px] text-ink-light mt-0.5">{{ fmtC(serviciosCost(prod) * (prod.qty || 0)) }} <span class="text-ink-xlight">total × {{ prod.qty || 0 }} pzas</span></p>
                    </div>
                  </div>

                  <div class="border-t border-surface-border px-4 py-3">
                    <div class="flex items-center justify-between mb-1.5">
                      <p class="text-[10.5px] font-semibold text-ink-muted uppercase tracking-wide">Resumen</p>
                      <span class="text-[10px] font-medium text-ink-light" title="Estos precios y costos no incluyen IVA">Precios sin IVA</span>
                    </div>
                    <table class="w-full text-sm">
                      <thead>
                        <tr class="text-[11px] text-ink-light">
                          <th class="text-left font-medium pb-1"></th>
                          <th class="text-right font-medium pb-1 w-28">Por pieza</th>
                          <th class="text-right font-medium pb-1 w-28">× {{ prod.qty || 0 }} pzas</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr class="border-t border-surface-border/60">
                          <td class="py-1.5 text-ink-muted">Costo directo</td>
                          <td class="py-1.5 text-right text-ink">{{ fmtC(directCost(prod)) }}</td>
                          <td class="py-1.5 text-right text-ink">{{ fmtC(directCost(prod) * (prod.qty || 0)) }}</td>
                        </tr>
                        <tr>
                          <td class="py-1.5 text-ink-muted">Overhead</td>
                          <td class="py-1.5 text-right text-ink">{{ fmtC(prod.overhead_amt) }}</td>
                          <td class="py-1.5 text-right text-ink">{{ fmtC((prod.overhead_amt || 0) * (prod.qty || 0)) }}</td>
                        </tr>
                        <tr class="border-t border-surface-border font-semibold">
                          <td class="py-1.5 text-ink">Costo total</td>
                          <td class="py-1.5 text-right text-ink">{{ fmtC(prod.total_unit_cost) }}</td>
                          <td class="py-1.5 text-right text-ink">{{ fmtC((prod.total_unit_cost || 0) * (prod.qty || 0)) }}</td>
                        </tr>
                        <tr class="text-green-600">
                          <td class="py-1.5"><span class="inline-flex items-center gap-1.5">Utilidad esperada <span class="text-[10px] font-medium text-green-700 bg-green-50 rounded px-1 py-px">{{ prod.margin_pct || 0 }}%</span></span></td>
                          <td class="py-1.5 text-right">{{ fmtC(expectedProfit(prod)) }}</td>
                          <td class="py-1.5 text-right">{{ fmtC(expectedProfit(prod) * (prod.qty || 0)) }}</td>
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

                <div class="bg-white rounded-lg border border-surface-border p-4">
                    <div v-for="(punto, pi) in puntosDe(prod.finished_item)" :key="punto.grupo_id" class="rounded-lg border border-surface-border mb-3 overflow-visible">
                      <!-- Encabezado del punto: solo el proveedor. El orden real del flujo
                           (quién recibe de quién) se ajusta en Flujo de Producción, no aquí --
                           para que Costear no se infle con una decisión que todavía no toca. -->
                      <div class="bg-surface-raised/60 px-3 py-2 flex items-center gap-2 flex-wrap">
                        <span class="w-5 h-5 rounded-full bg-white ring-1 ring-surface-border flex items-center justify-center text-[10px] font-semibold text-ink-muted flex-shrink-0">{{ pi + 1 }}</span>
                        <LinkInput :model-value="punto.servicios[0].proveedor" @update:model-value="v => setPuntoProveedor(punto, v)" doctype="Supplier" placeholder="Taller / proveedor…" class="w-96 max-w-full" />
                        <button class="del-btn ml-auto" title="Eliminar este punto completo" @click="removePunto(punto, prod)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button>
                      </div>

                      <!-- Servicios de este punto -->
                      <table class="w-full table-fixed text-sm mt-2">
                        <thead><tr class="text-left text-xs font-semibold text-ink-light"><th class="py-1.5 pl-3">Servicio</th><th class="py-1.5 w-28">UDM</th><th class="py-1.5 w-20 text-right">Cantidad</th><th class="py-1.5 w-24 text-right">Costo</th><th class="py-1.5 w-24 text-right pr-3">Total</th><th class="w-7"></th></tr></thead>
                        <tbody>
                          <tr v-for="e in punto.servicios" :key="e._tid" class="align-top">
                            <td class="py-1 pl-3 pr-2"><LinkInput v-model="e.servicio" doctype="Item" :filters="ITEM_FILTERS.servicio" placeholder="Servicio…" @update:model-value="onEtapaServicioChange(e, prod)" /></td>
                            <td class="py-1 pr-2"><LinkInput v-model="e.lote_uom" doctype="UOM" placeholder="UDM" class="min-w-0" /></td>
                            <td class="py-1 pr-2"><input v-model.number="e.operaciones_por_pieza" type="number" min="0" step="1" placeholder="1" class="field-input text-right" title="Cuántas veces se aplica esta operación en CADA pieza -- ej. 4 segmentos de cinta reflejante por prenda" @input="recalcPrecioOperacion(e, prod)" /></td>
                            <td class="py-1 pr-2"><div class="relative"><span class="prefix text-xs">$</span><input v-model.number="e.precio_por_operacion" type="number" min="0" step="0.01" class="field-input text-right pl-4" title="Precio de cada una" @input="recalcPrecioOperacion(e, prod)" /></div></td>
                            <td class="py-1 pr-3 text-right font-medium text-ink pt-2.5">{{ fmtC(precioPorPiezaEtapa(e)) }}</td>
                            <td class="py-1"><button class="del-btn" @click="removeServicioDePunto(e, punto, prod)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button></td>
                          </tr>
                        </tbody>
                      </table>
                      <button class="add-link ml-3 mb-2" @click="addServicioAPunto(punto, prod)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>Agregar servicio a este punto</button>

                      <!-- Materias primas de este punto -->
                      <div class="border-t border-surface-border bg-surface-raised/30 px-3 py-2">
                        <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wide mb-1.5">Materias primas de este punto</p>
                        <table v-if="materialesDelPunto(punto).length" class="w-full text-sm mb-2" style="table-layout: auto;">
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
                          <thead><tr class="text-left text-[11px] font-semibold text-ink-light"><th class="py-1">Artículo</th><th class="py-1">Proveedor</th><th class="py-1">Tipo</th><th class="py-1">UDM</th><th class="py-1">Rendimiento / Consumo</th><th class="py-1 text-right">Precio / UDM</th><th class="py-1 text-right">Total</th><th></th></tr></thead>
                          <tbody>
                            <tr v-for="d in materialesDelPunto(punto)" :key="d._tid" class="align-top">
                              <td class="py-1 pr-2">
                                <div class="flex items-center gap-1 mb-1 invisible" aria-hidden="true"><span class="text-[10px] px-1.5 py-0.5 rounded-full">·</span></div>
                                <LinkInput v-model="d.item" doctype="Item" :filters="ITEM_FILTERS.mp" placeholder="Materia prima…" @update:model-value="onDetalleItemChange(d, prod)" />
                              </td>
                              <td class="py-1 pr-2">
                                <div class="flex items-center gap-1 mb-1 invisible" aria-hidden="true"><span class="text-[10px] px-1.5 py-0.5 rounded-full">·</span></div>
                                <select v-model="d.supplier" @change="onSupplierChange(d, prod)" :disabled="!d.item" class="field-input">
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
                                <select v-model="d.internal_uom" class="field-input" :disabled="!d.tipo_material" @change="onUdmSelectChange(d, prod)">
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
                                <input v-if="qtyModeFor(d) === 'consumo'" v-model.number="d.internal_qty" type="number" min="0" step="0.0001" class="field-input text-right" placeholder="UDM por pza" @input="onConsumoInput(d, prod)" />
                                <input v-else-if="qtyModeFor(d) === 'piezas'" :value="piezasPorPrenda(d)" type="number" min="0" step="0.0001" class="field-input text-right" placeholder="pzas por prenda" @input="onPiezasInput(d, prod, $event.target.value)" />
                                <input v-else v-model.number="d.rendimiento" type="number" min="0" step="0.0001" class="field-input text-right" placeholder="pzas por UDM" @input="onRendimientoInput(d, prod)" />
                                <p class="text-[10.5px] text-ink-light mt-1 truncate">
                                  <template v-if="qtyModeFor(d) === 'consumo'">≈ {{ fmtQty(d.rendimiento) }} pzas/{{ d.internal_uom || 'UDM' }}</template>
                                  <template v-else-if="qtyModeFor(d) === 'piezas'">1 {{ d.internal_uom }} = {{ fmtQty(piezasPorUdm(d)) }} pzas</template>
                                  <template v-else>≈ {{ fmtQty(d.internal_qty) }} {{ d.internal_uom || 'UDM' }}/pza</template>
                                  · total: {{ fmtQty(d.supplier_qty) }} {{ d.internal_uom || 'UDM' }}
                                </p>
                              </td>
                              <td class="py-1 pr-2">
                                <div class="flex items-center gap-1 mb-1 invisible" aria-hidden="true"><span class="text-[10px] px-1.5 py-0.5 rounded-full">·</span></div>
                                <div class="relative">
                                  <span class="prefix text-xs">$</span>
                                  <input v-model.number="d.unit_price" type="number" min="0" step="0.01" class="field-input text-right pl-5" :class="d.tipo_material === 'Tela' ? 'pr-6' : ''" @input="recalcDetalle(d, prod)" />
                                  <button v-if="d.tipo_material === 'Tela'" type="button" class="absolute right-1 top-1/2 -translate-y-1/2 text-ink-light hover:text-brand-600" title="Convertir precio de $/kg a $/m" @click="openTelaConvert(d, prod)">
                                    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><rect x="5" y="3" width="14" height="18" rx="2"/><path stroke-linecap="round" d="M8 7h8M8 11h.01M12 11h.01M16 11h.01M8 15h.01M12 15h.01M16 15h.01"/></svg>
                                  </button>
                                  <template v-if="telaConvertModal.open && telaConvertModal.d === d">
                                    <div class="fixed inset-0 z-40" @click="closeTelaConvert()"></div>
                                    <div class="absolute z-50 right-0 top-full mt-1 w-64 bg-white border border-surface-border rounded-lg shadow-lg p-3 text-left">
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
                              </td>
                              <td class="py-1 pr-2 text-right font-medium text-ink">
                                <div class="flex items-center gap-1 mb-1 invisible" aria-hidden="true"><span class="text-[10px] px-1.5 py-0.5 rounded-full">·</span></div>
                                {{ fmtC(d.total) }}
                              </td>
                              <td class="py-1">
                                <div class="flex items-center gap-1 mb-1 invisible" aria-hidden="true"><span class="text-[10px] px-1.5 py-0.5 rounded-full">·</span></div>
                                <button class="del-btn" @click="removeDetalle(d, prod)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button>
                              </td>
                            </tr>
                          </tbody>
                        </table>
                        <p v-else class="text-[11.5px] text-ink-xlight mb-2">Ninguna todavía.</p>
                        <button class="add-link" @click="addMaterialAPunto(punto, prod)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>Agregar material</button>
                      </div>
                    </div>

                    <button type="button" class="w-full py-4 rounded-lg border-2 border-dashed border-surface-border hover:border-brand-300 hover:bg-brand-50/40 text-ink-muted hover:text-brand-600 flex items-center justify-center gap-2 text-[13px] font-medium transition-colors" @click="addPunto(prod)">
                      <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
                      Agregar paso
                    </button>

                    <!-- Materiales pendientes de asignar a un punto -- NO es un estado normal:
                         todo material siempre se usa en algún punto concreto de verdad, así que
                         esto solo debería aparecer con costeos capturados antes de este árbol.
                         Por eso ya no hay botón para crear materiales sueltos a propósito --
                         solo un aviso con una forma rápida de resolver los que ya existían. -->
                    <div v-if="materialesSinPunto(prod.finished_item).length" class="mt-3 pt-3 border-t border-amber-200">
                      <p class="text-[11px] font-semibold text-amber-700 uppercase tracking-wide mb-1.5 flex items-center gap-1.5">
                        <svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M5.07 19h13.86a2 2 0 001.71-3l-6.93-12a2 2 0 00-3.42 0l-6.93 12a2 2 0 001.71 3z"/></svg>
                        Pendientes de asignar a un punto <span class="font-normal normal-case text-amber-600">— sin esto, el sistema los atribuye solos al arranque del flujo, lo cual puede ser incorrecto</span>
                      </p>
                      <table class="w-full table-fixed text-sm">
                        <tbody>
                          <tr v-for="d in materialesSinPunto(prod.finished_item)" :key="d._tid" class="border-b border-surface-border/60 align-top">
                            <td class="py-1.5 pr-2 w-1/5"><LinkInput v-model="d.item" doctype="Item" :filters="ITEM_FILTERS.mp" placeholder="Materia prima…" @update:model-value="onDetalleItemChange(d, prod)" /></td>
                            <td class="py-1.5 pr-2 w-1/5">
                              <select v-model="d.supplier" @change="onSupplierChange(d, prod)" :disabled="!d.item" class="field-input">
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
                            <td class="py-1.5 w-7"><button class="del-btn" @click="removeDetalle(d, prod)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button></td>
                          </tr>
                        </tbody>
                      </table>
                    </div>

                    <div class="flex items-center justify-between mt-3 pt-3 border-t border-surface-border text-[12px]">
                      <span class="text-ink-muted">Total materias primas + etapas <span class="text-ink-xlight">por pieza</span></span>
                      <span class="font-semibold text-ink">{{ fmtC(totalMaterias(prod) + totalEtapas(prod)) }}</span>
                    </div>
                </div>

                <div class="bg-white rounded-lg border border-surface-border p-4">
                  <div class="flex items-center gap-2 mb-3">
                    <svg class="w-4 h-4 text-ink-light flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M7 4v16M17 4v16M3 8h4m10 0h4M3 16h4m10 0h4"/></svg>
                    <h4 class="text-[13px] font-semibold text-ink">Desglose por talla</h4>
                    <span v-if="tallasDe(prod.finished_item).length" class="px-1.5 py-0.5 rounded-full text-xs bg-surface-raised text-ink-muted">{{ tallasDe(prod.finished_item).length }}</span>
                    <svg class="w-3.5 h-3.5 text-ink-xlight hover:text-ink-light cursor-help flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8" title="Opcional. Puedes mezclar tallas de Dama y Caballero. El sobrecosto (fijo o %) se suma al precio de venta de esa talla, no al costo."><path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    <span v-if="tallasDe(prod.finished_item).length" class="ml-auto text-[11.5px]" :class="tallasAsignadas(prod) === (prod.qty || 0) ? 'text-green-600' : 'text-amber-600'">Asignadas: {{ tallasAsignadas(prod) }} / {{ prod.qty || 0 }}</span>
                  </div>
                  <table v-if="tallasDe(prod.finished_item).length" class="w-full text-sm mb-3">
                    <thead><tr class="border-b border-surface-border text-left text-xs font-semibold text-ink-light"><th class="py-2 w-2/5">Género / Tipo de prenda / Talla</th><th class="py-2 w-24 text-right">Cantidad</th><th class="py-2 w-32">Sobrecosto</th><th class="py-2 w-24 text-right">Valor</th><th class="py-2 w-24 text-right">Precio venta</th><th class="py-2 w-24 text-right">Venta total</th><th class="w-7"></th></tr></thead>
                    <tbody>
                      <template v-for="t in tallasDe(prod.finished_item)" :key="t._tid">
                      <tr class="border-b border-surface-border/60" :class="esTallaPendiente(t) ? 'bg-amber-50/50' : ''">
                        <td class="py-1.5 pr-2">
                          <div class="flex items-center gap-1">
                            <select v-model="t.genero" class="field-input" style="flex: 0 0 92px;" @change="onTallaGeneroChange(t)">
                              <option value="">Género…</option>
                              <option value="Dama">Dama</option>
                              <option value="Caballero">Caballero</option>
                            </select>
                            <select v-model="t.grupo_talla" class="field-input min-w-0" style="flex: 1 1 auto;" :disabled="!t.genero" @change="onTallaGrupoChange(t)">
                              <option value="">{{ t.genero ? 'Tipo de prenda…' : '— elige género —' }}</option>
                              <option v-for="g in gruposDeGenero(t.genero)" :key="g.name" :value="g.name">{{ g.talla }}</option>
                            </select>
                          </div>
                          <div v-if="t.grupo_talla" class="flex flex-wrap gap-1 mt-1">
                            <button
                              v-for="s in tallasDeGrupo(t.grupo_talla)" :key="s.name" type="button"
                              :disabled="tallaUsadaEnOtraFila(t, prod, s.name)"
                              class="px-1.5 py-0.5 rounded text-[10.5px] border transition-colors"
                              :class="tallaSeleccionada(t, s.name)
                                ? 'bg-brand-500 text-white border-brand-500'
                                : tallaUsadaEnOtraFila(t, prod, s.name)
                                  ? 'bg-surface-raised text-ink-xlight border-surface-border cursor-not-allowed'
                                  : 'bg-white text-ink-muted border-surface-border hover:border-brand-300'"
                              :title="tallaUsadaEnOtraFila(t, prod, s.name) ? 'Ya asignada a otra fila' : ''"
                              @click="toggleTallaEnGrupo(t, s.name, prod)"
                            >{{ s.talla }}</button>
                          </div>
                          <p v-else class="text-[10.5px] text-ink-xlight mt-1">Elige género y tipo de prenda para ver las tallas</p>
                        </td>
                        <td class="py-1.5 pr-2">
                          <input v-model.number="t.qty" type="number" min="0" :max="tallaMaxQty(t, prod)" :disabled="esTallaPendiente(t)" class="field-input text-right" @input="onTallaQtyInput(t, prod)" />
                          <label class="flex items-center gap-1 mt-1 text-[10px] cursor-pointer select-none" :class="esTallaPendiente(t) ? 'text-amber-700 font-medium' : 'text-ink-light'">
                            <input type="checkbox" :checked="esTallaPendiente(t)" class="w-3 h-3" @change="toggleTallaPendiente(t, prod, $event.target.checked)" />
                            Pendiente
                          </label>
                        </td>
                        <td class="py-1.5 pr-2">
                          <select v-model="t.sobrecosto_tipo" class="field-input" @change="recalcTalla(t, prod)">
                            <option value="Ninguno">Ninguno</option>
                            <option value="Fijo">Fijo ($)</option>
                            <option value="Porcentaje">Porcentaje (%)</option>
                            <option value="Material">Material</option>
                          </select>
                        </td>
                        <td class="py-1.5 pr-2">
                          <input v-if="t.sobrecosto_tipo === 'Fijo' || t.sobrecosto_tipo === 'Porcentaje'" v-model.number="t.sobrecosto_valor" type="number" min="0" step="0.01" class="field-input text-right" @input="recalcTalla(t, prod)" />
                          <div v-else-if="t.sobrecosto_tipo === 'Material'" class="field-input bg-surface-raised/60 text-ink-muted text-right" title="Se calcula solo: diferencia de precio entre el material original y el alterno">{{ fmtC(t.sobrecosto_valor) }}</div>
                          <div v-else class="field-input bg-surface-raised/60 text-ink-xlight text-right">—</div>
                        </td>
                        <td class="py-1.5 pr-2 text-right font-medium text-brand-600">{{ fmtC(t.precio_venta) }}</td>
                        <td class="py-1.5 pr-2 text-right font-medium text-ink">{{ fmtC((t.precio_venta || 0) * (t.qty || 0)) }}</td>
                        <td class="py-1.5"><button class="del-btn" @click="removeTalla(t, prod)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button></td>
                      </tr>
                      <tr v-if="t.sobrecosto_tipo === 'Material'" class="border-b border-surface-border/60 bg-surface-raised/40">
                        <td colspan="7" class="py-2 px-2">
                          <div class="flex items-center gap-2 text-[12px]">
                            <span class="text-ink-muted flex-shrink-0">Cambia el material</span>
                            <select v-model="t.sobrecosto_material_original" class="field-input flex-1 min-w-0" @change="onTallaMaterialAlternoChange(t, prod)">
                              <option value="">— elige cuál —</option>
                              <option v-for="m in materialesDe(prod.finished_item)" :key="m._tid" :value="m.item">{{ m.item }}</option>
                            </select>
                            <span class="text-ink-light flex-shrink-0">por</span>
                            <div class="flex-1 min-w-0">
                              <LinkInput v-model="t.sobrecosto_material_alterno" doctype="Item" :filters="ITEM_FILTERS.mp" placeholder="Artículo alterno…" @update:model-value="onTallaMaterialAlternoChange(t, prod)" />
                            </div>
                          </div>
                          <p v-if="t.lote_ref" class="text-[11px] text-ink-light mt-1">Ya asignado al lote "{{ t.lote_ref }}" -- ese envío de material usará el artículo alterno.</p>
                        </td>
                      </tr>
                      </template>
                    </tbody>
                  </table>
                  <p v-if="tallasDe(prod.finished_item).length" class="text-[12px] text-ink-muted mb-3">Total de venta con sobrecostos por talla: <span class="font-semibold text-ink">{{ fmtC(tallasVentaTotal(prod)) }}</span></p>
                  <button class="add-link" @click="addTalla(prod)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>Agregar talla</button>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>

      </div>
      </fieldset>
    </div>

    <!-- ══════════ STEP 1 · COTIZAR ══════════ -->
    <div v-else-if="activeStep === 1" class="p-5 pb-20">
      <div class="max-w-6xl mx-auto space-y-3">

        <!-- Lista de cotizaciones del costeo (acordeón, mismo patrón que Productos a costear) -->
        <div v-for="q in related.quotations" :key="q.name" class="group bg-white rounded-xl border border-surface-border overflow-hidden" :id="`doc-hl-${q.name}`" :class="{ 'doc-highlight-flash': highlightTarget === q.name }">
          <div class="flex items-center gap-3 px-5 py-3 cursor-pointer hover:bg-surface-raised/50 transition-colors" @click="toggleQuotation(q)">
            <svg class="w-4 h-4 text-ink-light flex-shrink-0 transition-transform" :class="expandedQuotName === q.name ? 'rotate-90' : ''" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
            <p class="text-sm font-semibold text-ink">{{ q.name }}</p>
            <span class="text-[11px] font-semibold px-2 py-0.5 rounded-full" :class="q.status === 'Lost' ? 'bg-red-50 text-red-600' : (q.docstatus === 2 ? 'bg-surface-raised text-ink-light' : (q.docstatus === 1 ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'))">{{ q.status === 'Lost' ? 'Rechazada' : (q.docstatus === 2 ? 'Cancelada' : (q.docstatus === 1 ? 'Validada' : 'Borrador')) }}</span>
            <span class="ml-auto text-[13px] font-medium text-ink">{{ fmtC(q.grand_total) }}</span>
            <button class="opacity-0 group-hover:opacity-100 w-6 h-6 flex items-center justify-center rounded hover:bg-red-50 hover:text-red-500 text-gray-300 transition-all flex-shrink-0" @click.stop="openDeleteQuot(q.name)" title="Eliminar cotización">
              <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
            </button>
          </div>

          <div v-if="expandedQuotName === q.name" class="bg-surface-raised/40 border-t border-surface-border p-5 space-y-5">
            <!-- La tabla de artículos se quitó a propósito: los productos/precios ya
                 quedaron fijos desde Costear, este paso no permite editarlos -- se
                 siguen guardando/enviando tal cual (cotItems), solo ya no se muestran
                 ni se pueden tocar aquí. -->

            <div class="flex gap-5 items-start">
              <!-- Izquierda: campos manuales -->
              <div class="w-80 flex-shrink-0 bg-white rounded-xl border border-surface-border p-5">
                <p class="text-sm font-semibold text-ink mb-1">Datos de la cotización</p>
                <p class="text-[12px] text-ink-muted mb-4">Completa lo que no viene del costeo. Productos y totales son automáticos.</p>

                <div v-if="q.status === 'Lost'" class="bg-red-50 border border-red-100 rounded-lg px-3 py-2.5 mb-4">
                  <p class="text-[11.5px] font-semibold text-red-700 mb-0.5">Cotización rechazada</p>
                  <p v-if="q.order_lost_reason" class="text-[11.5px] text-red-600 mb-2.5">{{ q.order_lost_reason }}</p>
                  <div class="space-y-1.5">
                    <button :disabled="advancing" class="w-full text-left text-[11.5px] font-medium text-red-700 bg-white border border-red-200 rounded-lg px-2.5 py-1.5 hover:bg-red-100/50 disabled:opacity-50" @click="openRevisionModal">
                      Editar Costeo
                      <span class="block text-[10.5px] font-normal text-red-500">Toda corrección (precio, condiciones, materiales, cantidades…) se hace desde el costeo.</span>
                    </button>
                  </div>
                </div>

                <div v-if="q.docstatus === 2" class="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2.5 mb-4">
                  <p class="text-[11.5px] font-semibold text-ink mb-0.5">Cotización cancelada</p>
                  <p class="text-[11.5px] text-ink-muted mb-2.5">El proyecto quedó marcado como cancelado. Si en realidad sigue en pie, edita el costeo para reactivarlo con una revisión nueva.</p>
                  <button :disabled="advancing" class="w-full text-left text-[11.5px] font-medium text-ink bg-white border border-surface-border rounded-lg px-2.5 py-1.5 hover:bg-surface-raised disabled:opacity-50" @click="openRevisionModal">
                    Editar Costeo
                    <span class="block text-[10.5px] font-normal text-ink-light">Crea una revisión del costeo y reactiva el proyecto.</span>
                  </button>
                </div>

                <label class="field-label">Vigencia (válida hasta)</label>
                <input v-model="cotForm.valid_till" type="date" class="field-input mb-3" :disabled="q.docstatus === 1" />

                <label class="field-label">Condiciones de pago</label>
                <select v-model="cotForm.payment_terms_template" class="field-input mb-3" :disabled="q.docstatus === 1">
                  <option value="">— Sin plantilla —</option>
                  <option v-for="p in cotDefaults.payment_terms_templates" :key="p.name" :value="p.name">{{ p.name }}</option>
                </select>

                <label class="field-label">Términos y condiciones</label>
                <select v-model="cotForm.tc_name" class="field-input mb-3" :disabled="q.docstatus === 1">
                  <option value="">— Sin términos —</option>
                  <option v-for="t in cotDefaults.terms" :key="t.name" :value="t.name">{{ t.name }}</option>
                </select>

                <label class="field-label">Vista de impresión</label>
                <select v-model="cotForm.custom_tipo_formato" class="field-input mb-3" :disabled="q.docstatus === 1" @change="onTipoFormatoChange">
                  <option value="Normal">Normal</option>
                  <option value="Volumen">Por volumen</option>
                </select>

                <label class="field-label">Moneda</label>
                <select v-model="cotForm.currency" class="field-input mb-3" :disabled="q.docstatus === 1">
                  <option v-for="c in cotDefaults.currencies" :key="c.name" :value="c.name">{{ c.name }}</option>
                </select>

                <label class="field-label">Lista de Precios</label>
                <select v-model="cotForm.selling_price_list" class="field-input mb-3" :disabled="q.docstatus === 1">
                  <option value="">— Sin lista —</option>
                  <option v-for="pl in cotDefaults.price_lists" :key="pl.name" :value="pl.name">{{ pl.name }}</option>
                </select>

                <label class="field-label">Impuestos y Cargos</label>
                <select v-model="cotForm.taxes_and_charges" class="field-input mb-3" :disabled="q.docstatus === 1">
                  <option value="">— Sin plantilla —</option>
                  <option v-for="t in cotDefaults.tax_templates" :key="t.name" :value="t.name">{{ t.name }}</option>
                </select>

                <label class="field-label">Email de contacto</label>
                <input v-model="cotForm.contact_email" type="email" class="field-input mb-3" :disabled="q.docstatus === 1" placeholder="correo@cliente.com" />

                <label class="field-label">WhatsApp / Móvil</label>
                <input v-model="cotForm.contact_mobile" type="tel" class="field-input mb-4" :disabled="q.docstatus === 1" placeholder="+52 55 1234 5678" />

                <div class="space-y-2">
                  <template v-if="q.docstatus !== 1">
                    <button :disabled="advancing" class="w-full h-9 text-sm font-medium text-ink border border-surface-border rounded-lg hover:bg-surface-raised disabled:opacity-50" @click="guardarCambiosCotizacion">Guardar cambios</button>
                    <button :disabled="advancing" class="w-full h-9 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center justify-center gap-1.5" @click="validarDoc('Quotation', q.name)">
                      <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Validar cotización
                    </button>
                  </template>
                  <div class="grid grid-cols-2 gap-2 pt-1">
                    <button class="doc-action justify-center" @click="openSend('Quotation', q.name, q.contact_email, q.contact_mobile)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>Enviar</button>
                    <button class="doc-action justify-center" @click="downloadPdf('Quotation', q.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/></svg>Descargar</button>
                    <button class="doc-action justify-center" @click="printDocView('Quotation', q.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2z"/></svg>Imprimir</button>
                    <button class="doc-action justify-center" @click="openAssign('Quotation', q.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>Asignar</button>
                  </div>
                  <a class="doc-action justify-center w-full" :href="`/app/quotation/${q.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>Abrir en ERPNext</a>

                  <div v-if="q.docstatus === 1 && q.status !== 'Lost'" class="pt-2 mt-1 border-t border-surface-border space-y-2">
                    <button
                      class="w-full h-8 text-[12.5px] font-medium text-ink-muted border border-surface-border rounded-lg hover:bg-surface-raised disabled:opacity-50 disabled:hover:bg-transparent disabled:cursor-not-allowed"
                      :disabled="precioAcordadoStatus.todos_validados"
                      :title="precioAcordadoStatus.todos_validados ? 'El precio acordado ya está validado -- no se puede volver a fijar/editar desde aquí.' : ''"
                      @click="openAcordadoModal"
                    >Fijar Precio</button>
                    <div v-if="precioAcordadoStatus.items.length" class="flex items-center justify-between gap-2 px-0.5">
                      <span class="text-[11px] font-medium" :class="precioAcordadoStatus.todos_validados ? 'text-green-600' : 'text-amber-600'">
                        Precio acordado: {{ precioAcordadoStatus.todos_validados ? 'Validado' : 'Borrador' }} ({{ precioAcordadoStatus.items.length }})
                      </span>
                      <button v-if="!precioAcordadoStatus.todos_validados && precioAcordadoStatus.es_ceo" :disabled="advancing" class="text-[11px] font-semibold text-brand-600 hover:text-brand-700 hover:underline disabled:opacity-50" @click="validarPrecioAcordado">Validar</button>
                    </div>
                    <button class="w-full h-8 text-[12.5px] font-medium text-red-500 border border-red-200 rounded-lg hover:bg-red-50" @click="openRechazarModal">Marcar rechazada</button>
                  </div>

                  <div class="pt-3 mt-2 border-t border-surface-border">
                    <AttachmentsPanel doctype="Quotation" :docname="q.name" />
                  </div>
                </div>
              </div>

              <!-- Derecha: vista previa del PDF (zoom reducido) -->
              <div class="flex-1 min-w-0 bg-white rounded-xl border border-surface-border overflow-hidden">
                <div class="flex items-center justify-end px-2 py-1.5 border-b border-surface-border">
                  <button class="doc-action" @click="openPdf('Quotation', q.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 8V4m0 0h4M4 4l5 5m11-5h-4m4 0v4m0-4l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5h-4m4 0v-4m0 4l-5-5"/></svg>Ampliar</button>
                </div>
                <div style="height: 70vh; overflow: auto;">
                  <iframe :key="previewKey" :src="printUrl('Quotation', q.name)" style="width: 143%; height: 143%; transform: scale(0.7); transform-origin: top left; border: 0;" title="Vista previa de la cotización"></iframe>
                </div>
              </div>
            </div>
          </div>
        </div>

        <p v-if="!related.quotations.length" class="text-center text-ink-light text-sm py-10">Todavía no hay cotizaciones para este costeo.</p>

        <!-- Crear la primera cotización -->
        <div v-if="!related.quotations.length" class="w-80 bg-white rounded-xl border border-surface-border p-5">
          <p class="text-sm font-semibold text-ink mb-1">Nueva cotización</p>
          <p class="text-[12px] text-ink-muted mb-4">Completa lo que no viene del costeo. Productos y totales son automáticos.</p>

          <label class="field-label">Vigencia (válida hasta)</label>
          <input v-model="cotForm.valid_till" type="date" class="field-input mb-3" />

          <label class="field-label">Condiciones de pago</label>
          <select v-model="cotForm.payment_terms_template" class="field-input mb-3">
            <option value="">— Sin plantilla —</option>
            <option v-for="p in cotDefaults.payment_terms_templates" :key="p.name" :value="p.name">{{ p.name }}</option>
          </select>

          <label class="field-label">Términos y condiciones</label>
          <select v-model="cotForm.tc_name" class="field-input mb-3">
            <option value="">— Sin términos —</option>
            <option v-for="t in cotDefaults.terms" :key="t.name" :value="t.name">{{ t.name }}</option>
          </select>

          <label class="field-label">Vista de impresión</label>
          <select v-model="cotForm.custom_tipo_formato" class="field-input mb-3" @change="onTipoFormatoChange">
            <option value="Normal">Normal</option>
            <option value="Volumen">Por volumen</option>
          </select>

          <label class="field-label">Moneda</label>
          <select v-model="cotForm.currency" class="field-input mb-3">
            <option v-for="c in cotDefaults.currencies" :key="c.name" :value="c.name">{{ c.name }}</option>
          </select>

          <label class="field-label">Lista de Precios</label>
          <select v-model="cotForm.selling_price_list" class="field-input mb-3">
            <option value="">— Sin lista —</option>
            <option v-for="pl in cotDefaults.price_lists" :key="pl.name" :value="pl.name">{{ pl.name }}</option>
          </select>

          <label class="field-label">Impuestos y Cargos</label>
          <select v-model="cotForm.taxes_and_charges" class="field-input mb-3">
            <option value="">— Sin plantilla —</option>
            <option v-for="t in cotDefaults.tax_templates" :key="t.name" :value="t.name">{{ t.name }}</option>
          </select>

          <label class="field-label">Email de contacto</label>
          <input v-model="cotForm.contact_email" type="email" class="field-input mb-3" placeholder="correo@cliente.com" />

          <label class="field-label">WhatsApp / Móvil</label>
          <input v-model="cotForm.contact_mobile" type="tel" class="field-input mb-4" placeholder="+52 55 1234 5678" />

          <div class="border-t border-surface-border pt-3 mb-4 space-y-1">
            <div class="flex justify-between text-[13px]"><span class="text-ink-muted">Productos</span><span>{{ productos.length }}</span></div>
            <div class="flex justify-between text-[13px]"><span class="text-ink-muted">Total venta</span><span class="font-medium">{{ fmtC(totalVenta) }}</span></div>
          </div>

          <button :disabled="advancing" class="w-full h-9 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center justify-center gap-2" @click="guardarBorradorCotizacion">
            <svg v-if="advancing" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
            Guardar como borrador
          </button>
        </div>
      </div>
    </div>

    <!-- ══════════ STEP 2 · VENDER ══════════ -->
    <div v-else-if="activeStep === 2" class="p-5 pb-20">
      <div class="max-w-6xl mx-auto space-y-3">

        <!-- Generar nueva OV: a nivel costeo, no dentro de una orden en particular --
             toma como base la última OV validada (o la que se elija abajo si hay
             varias) y solo pide ajustar cantidades; el precio ya viene acordado.
             Oculto mientras esa OV base no tenga precio acordado fijado; si lo
             tiene pero ya venció, el botón avisa en vez de desaparecer -- quien
             tenga rol CEO puede destrabarlo desde el propio modal. -->
        <div v-if="nuevaOvGate.show" class="bg-white rounded-xl border p-4 flex items-center justify-between gap-3" :class="nuevaOvGate.vencido ? 'border-amber-200 bg-amber-50/30' : 'border-surface-border'">
          <div>
            <p class="text-sm font-semibold mb-0.5" :class="nuevaOvGate.vencido ? 'text-amber-800' : 'text-ink'">
              {{ nuevaOvGate.vencido ? 'Precio acordado caducado' : 'Generar nueva OV' }}
            </p>
            <p class="text-[12px]" :class="nuevaOvGate.vencido ? 'text-amber-700' : 'text-ink-muted'">
              <template v-if="nuevaOvGate.vencido">
                El precio acordado para un nuevo pedido de este cliente ya venció.
                <template v-if="nuevaOvGate.esCeo">Tienes permiso de CEO para generar la OV de todos modos, o actualízalo desde "Fijar Precio" en la cotización.</template>
                <template v-else>Pide a alguien con rol CEO que la genere, o actualiza el precio desde "Fijar Precio" en la cotización.</template>
              </template>
              <template v-else>Pedido recurrente del mismo cliente: crea otra Orden de Venta con los productos y el precio ya acordado, solo ajustando la cantidad -- sin volver a cotizar.</template>
            </p>
          </div>
          <button
            class="h-9 px-4 text-[13px] font-semibold rounded-lg flex-shrink-0"
            :class="nuevaOvGate.vencido ? 'text-amber-800 bg-amber-100 hover:bg-amber-200' : 'text-white bg-brand-500 hover:bg-brand-600'"
            @click="openNuevaOvModal()"
          >{{ nuevaOvGate.vencido ? 'Precio caducado -- revisar' : '+ Generar nueva OV' }}</button>
        </div>

        <!-- Lista de órdenes de venta del costeo (acordeón, mismo patrón que Cotizar) -->
        <div v-for="so in related.sales_orders" :key="so.name" class="group bg-white rounded-xl border border-surface-border overflow-hidden" :id="`doc-hl-${so.name}`" :class="{ 'doc-highlight-flash': highlightTarget === so.name }">
          <div class="flex items-center gap-3 px-5 py-3 cursor-pointer hover:bg-surface-raised/50 transition-colors" @click="toggleSalesOrder(so)">
            <svg class="w-4 h-4 text-ink-light flex-shrink-0 transition-transform" :class="expandedSOName === so.name ? 'rotate-90' : ''" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
            <p class="text-sm font-semibold text-ink">{{ so.name }}</p>
            <span v-if="activeSOName === so.name" class="text-[10.5px] font-semibold px-2 py-0.5 rounded-full bg-brand-100 text-brand-700">OV activa</span>
            <span class="text-[11px] font-semibold px-2 py-0.5 rounded-full" :class="so.docstatus === 2 ? 'bg-surface-raised text-ink-light' : (so.docstatus === 1 ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700')">{{ so.docstatus === 2 ? 'Cancelada' : (so.docstatus === 1 ? 'Validada' : 'Borrador') }}</span>
            <span class="ml-auto text-[13px] font-medium text-ink">{{ fmtC(so.grand_total) }}</span>
            <button class="opacity-0 group-hover:opacity-100 w-6 h-6 flex items-center justify-center rounded hover:bg-red-50 hover:text-red-500 text-gray-300 transition-all flex-shrink-0" @click.stop="openDeleteSO(so.name)" title="Eliminar orden de venta">
              <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
            </button>
          </div>

          <div v-if="expandedSOName === so.name" class="bg-surface-raised/40 border-t border-surface-border p-5">
            <div class="flex gap-5 items-start">
              <!-- Izquierda: campos manuales -->
              <div class="w-80 flex-shrink-0 bg-white rounded-xl border border-surface-border p-5">
                <div v-if="activeSOName !== so.name" class="mb-3">
                  <button class="w-full h-8 text-[12.5px] font-semibold text-brand-700 bg-brand-50 rounded-lg hover:bg-brand-100" @click="setActiveSO(so.name)">Usar como OV activa para Producir/Enviar/Facturar/Reportar</button>
                </div>
                <p class="text-sm font-semibold text-ink mb-1">Datos de la orden de venta</p>
                <p class="text-[12px] text-ink-muted mb-4">Completa lo que no viene del costeo. Productos y totales son automáticos.</p>

                <label class="field-label">Tiempo de entrega (semanas)</label>
                <input v-model.number="soForm.delivery_weeks" type="number" min="1" step="1" placeholder="Ej: 3" class="field-input mb-1" :disabled="so.docstatus === 1" @input="onDeliveryWeeksChange" />
                <p class="text-[10.5px] text-ink-light mb-3">{{ soForm.delivery_date ? `Vigencia: ${soForm.delivery_date}` : 'Captura las semanas para calcular la fecha' }}</p>

                <label class="field-label">Condiciones de pago</label>
                <select v-model="soForm.payment_terms_template" class="field-input mb-3" :disabled="so.docstatus === 1">
                  <option value="">— Sin plantilla —</option>
                  <option v-for="p in cotDefaults.payment_terms_templates" :key="p.name" :value="p.name">{{ p.name }}</option>
                </select>

                <label class="field-label">Términos y condiciones</label>
                <select v-model="soForm.tc_name" class="field-input mb-3" :disabled="so.docstatus === 1">
                  <option value="">— Sin términos —</option>
                  <option v-for="t in cotDefaults.terms" :key="t.name" :value="t.name">{{ t.name }}</option>
                </select>

                <label class="field-label">OC del Cliente</label>
                <input v-model="soForm.po_no" type="text" class="field-input mb-3" :disabled="so.docstatus === 1" placeholder="Número de orden de compra" />

                <label class="field-label">Moneda</label>
                <select v-model="soForm.currency" class="field-input mb-3" :disabled="so.docstatus === 1">
                  <option v-for="c in cotDefaults.currencies" :key="c.name" :value="c.name">{{ c.name }}</option>
                </select>

                <label class="field-label">Lista de Precios</label>
                <select v-model="soForm.selling_price_list" class="field-input mb-3" :disabled="so.docstatus === 1">
                  <option value="">— Sin lista —</option>
                  <option v-for="pl in cotDefaults.price_lists" :key="pl.name" :value="pl.name">{{ pl.name }}</option>
                </select>

                <label class="field-label">Impuestos y Cargos</label>
                <select v-model="soForm.taxes_and_charges" class="field-input mb-3" :disabled="so.docstatus === 1">
                  <option value="">— Sin plantilla —</option>
                  <option v-for="t in cotDefaults.tax_templates" :key="t.name" :value="t.name">{{ t.name }}</option>
                </select>

                <label class="field-label">Email de contacto</label>
                <input v-model="soForm.contact_email" type="email" class="field-input mb-3" :disabled="so.docstatus === 1" placeholder="correo@cliente.com" />

                <label class="field-label">WhatsApp / Móvil</label>
                <input v-model="soForm.contact_mobile" type="tel" class="field-input mb-4" :disabled="so.docstatus === 1" placeholder="+52 55 1234 5678" />

                <div class="space-y-2">
                  <template v-if="so.docstatus !== 1">
                    <button :disabled="advancing" class="w-full h-9 text-sm font-medium text-ink border border-surface-border rounded-lg hover:bg-surface-raised disabled:opacity-50" @click="guardarCambiosOrdenVenta">Guardar cambios</button>
                    <button :disabled="advancing" class="w-full h-9 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center justify-center gap-1.5" @click="validarDoc('Sales Order', so.name)">
                      <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Validar orden
                    </button>
                  </template>
                  <div class="grid grid-cols-2 gap-2 pt-1">
                    <button class="doc-action justify-center" @click="openSend('Sales Order', so.name, so.contact_email, so.contact_mobile)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>Enviar</button>
                    <button class="doc-action justify-center" @click="downloadPdf('Sales Order', so.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/></svg>Descargar</button>
                    <button class="doc-action justify-center" @click="printDocView('Sales Order', so.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2z"/></svg>Imprimir</button>
                    <button class="doc-action justify-center" @click="openAssign('Sales Order', so.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>Asignar</button>
                  </div>
                  <a class="doc-action justify-center w-full" :href="`/app/sales-order/${so.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>Abrir en ERPNext</a>

                  <div class="pt-3 mt-2 border-t border-surface-border">
                    <AttachmentsPanel doctype="Sales Order" :docname="so.name" />
                  </div>
                </div>
              </div>

              <!-- Derecha: vista previa del PDF -->
              <div class="flex-1 min-w-0 bg-white rounded-xl border border-surface-border overflow-hidden">
                <div class="flex items-center justify-end px-2 py-1.5 border-b border-surface-border">
                  <button class="doc-action" @click="openPdf('Sales Order', so.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 8V4m0 0h4M4 4l5 5m11-5h-4m4 0v4m0-4l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5h-4m4 0v-4m0 4l-5-5"/></svg>Ampliar</button>
                </div>
                <div style="height: 70vh; overflow: auto;">
                  <iframe :key="previewKey" :src="printUrl('Sales Order', so.name)" style="width: 143%; height: 143%; transform: scale(0.7); transform-origin: top left; border: 0;" title="Vista previa de la orden de venta"></iframe>
                </div>
              </div>
            </div>
          </div>
        </div>

        <p v-if="!related.sales_orders.length" class="text-center text-ink-light text-sm py-10">Todavía no hay órdenes de venta para este costeo.</p>

        <!-- Crear la primera orden de venta -->
        <div v-if="!related.sales_orders.length" class="w-80 bg-white rounded-xl border border-surface-border p-5">
          <p class="text-sm font-semibold text-ink mb-1">Nueva orden de venta</p>
          <p class="text-[12px] text-ink-muted mb-4">Completa lo que no viene del costeo. Productos y totales son automáticos.</p>

          <label class="field-label">Tiempo de entrega (semanas)</label>
          <input v-model.number="soForm.delivery_weeks" type="number" min="1" step="1" placeholder="Ej: 3" class="field-input mb-1" @input="onDeliveryWeeksChange" />
          <p class="text-[10.5px] text-ink-light mb-3">{{ soForm.delivery_date ? `Vigencia: ${soForm.delivery_date}` : 'Captura las semanas para calcular la fecha' }}</p>

          <label class="field-label">Condiciones de pago</label>
          <select v-model="soForm.payment_terms_template" class="field-input mb-3">
            <option value="">— Sin plantilla —</option>
            <option v-for="p in cotDefaults.payment_terms_templates" :key="p.name" :value="p.name">{{ p.name }}</option>
          </select>

          <label class="field-label">Términos y condiciones</label>
          <select v-model="soForm.tc_name" class="field-input mb-3">
            <option value="">— Sin términos —</option>
            <option v-for="t in cotDefaults.terms" :key="t.name" :value="t.name">{{ t.name }}</option>
          </select>

          <label class="field-label">OC del Cliente</label>
          <input v-model="soForm.po_no" type="text" class="field-input mb-3" placeholder="Número de orden de compra" />

          <label class="field-label">Moneda</label>
          <select v-model="soForm.currency" class="field-input mb-3">
            <option v-for="c in cotDefaults.currencies" :key="c.name" :value="c.name">{{ c.name }}</option>
          </select>

          <label class="field-label">Lista de Precios</label>
          <select v-model="soForm.selling_price_list" class="field-input mb-3">
            <option value="">— Sin lista —</option>
            <option v-for="pl in cotDefaults.price_lists" :key="pl.name" :value="pl.name">{{ pl.name }}</option>
          </select>

          <label class="field-label">Impuestos y Cargos</label>
          <select v-model="soForm.taxes_and_charges" class="field-input mb-3">
            <option value="">— Sin plantilla —</option>
            <option v-for="t in cotDefaults.tax_templates" :key="t.name" :value="t.name">{{ t.name }}</option>
          </select>

          <label class="field-label">Email de contacto</label>
          <input v-model="soForm.contact_email" type="email" class="field-input mb-3" placeholder="correo@cliente.com" />

          <label class="field-label">WhatsApp / Móvil</label>
          <input v-model="soForm.contact_mobile" type="tel" class="field-input mb-4" placeholder="+52 55 1234 5678" />

          <div class="border-t border-surface-border pt-3 mb-4 space-y-1">
            <div class="flex justify-between text-[13px]"><span class="text-ink-muted">Productos</span><span>{{ productos.length }}</span></div>
            <div class="flex justify-between text-[13px]"><span class="text-ink-muted">Total venta</span><span class="font-medium">{{ fmtC(totalVenta) }}</span></div>
          </div>

          <button :disabled="advancing || related.quotation?.docstatus !== 1" class="w-full h-9 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-40 flex items-center justify-center gap-2" @click="guardarBorradorOrdenVenta">
            <svg v-if="advancing" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
            Guardar como borrador
          </button>
          <p v-if="related.quotation?.docstatus !== 1" class="text-[11px] text-ink-light mt-2 text-center">Primero valida la cotización.</p>
        </div>
      </div>
    </div>

    <!-- Modal: Generar nueva Orden de Venta (a partir de una ya validada, mismo precio acordado) -->
    <div v-if="nuevaOvModal.open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="nuevaOvModal.open = false">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md p-5">
        <p class="text-sm font-semibold text-ink mb-1">Generar nueva OV</p>
        <p class="text-[12px] text-ink-muted mb-3">Crea otra Orden de Venta con los mismos artículos y el precio ya acordado -- ajusta la cantidad de cada uno, sin volver a cotizar.</p>

        <div v-if="sosValidadas.length > 1" class="mb-4">
          <label class="field-label">Basado en</label>
          <select class="field-input" :value="nuevaOvModal.so?.name" @change="cambiarBaseNuevaOv($event.target.value)">
            <option v-for="so in sosValidadas" :key="so.name" :value="so.name">{{ so.name }} · {{ fmtC(so.grand_total) }}</option>
          </select>
        </div>

        <div v-if="nuevaOvModal.loading" class="py-6 text-center text-ink-light text-sm">Cargando…</div>
        <template v-else>
          <div v-if="nuevaOvModal.status && !nuevaOvModal.status.puede_generar" class="rounded-lg px-3 py-2.5 mb-4" :class="nuevaOvModal.status.es_ceo ? 'bg-amber-50 border border-amber-100' : 'bg-red-50 border border-red-100'">
            <p class="text-[11.5px] font-semibold mb-0.5" :class="nuevaOvModal.status.es_ceo ? 'text-amber-700' : 'text-red-700'">
              {{ nuevaOvModal.status.vencido ? 'El precio acordado ya venció' : 'Falta fijar el precio de algún artículo' }}
            </p>
            <p class="text-[11.5px]" :class="nuevaOvModal.status.es_ceo ? 'text-amber-600' : 'text-red-600'">
              <template v-if="nuevaOvModal.status.es_ceo">Tienes permiso de CEO para generarla de todos modos.</template>
              <template v-else-if="nuevaOvModal.status.vencido">Un usuario con rol CEO debe generar esta OV para desbloquearlo, o vuelve a "Fijar Precio" desde la cotización.</template>
              <template v-else>Usa "Fijar Precio" desde la cotización para los artículos que falten.</template>
            </p>
          </div>

          <div class="space-y-2 mb-4 max-h-64 overflow-y-auto">
            <div v-for="row in nuevaOvModal.items" :key="row.item_code" class="flex items-center gap-2 border border-surface-border rounded-lg px-3 py-2">
              <div class="flex-1 min-w-0">
                <p class="text-[13px] font-medium text-ink truncate">{{ row.item_name || row.item_code }}</p>
                <p class="text-[11px] text-ink-light">
                  {{ fmtC(row.rate) }} c/u
                  <template v-if="!row.tiene_precio_acordado"> · sin precio acordado</template>
                  <template v-else-if="!row.vigente"> · vencido {{ row.valid_upto }}</template>
                </p>
              </div>
              <div>
                <label class="text-[10px] text-ink-light block text-right mb-0.5">Cantidad a generar</label>
                <input v-model.number="row.qty" type="number" min="1" step="1" class="field-input text-right" style="width: 100px;" />
              </div>
            </div>
          </div>

          <div class="flex justify-end gap-2">
            <button class="px-3 py-1.5 text-[13px] text-ink-muted hover:bg-surface-raised rounded-lg" @click="nuevaOvModal.open = false">Cancelar</button>
            <button :disabled="nuevaOvModal.generating || (nuevaOvModal.status && !nuevaOvModal.status.puede_generar && !nuevaOvModal.status.es_ceo)" class="px-4 py-1.5 text-[13px] font-medium text-white bg-brand-500 hover:bg-brand-600 disabled:opacity-50 rounded-lg" @click="confirmarNuevaOv">
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
    <div v-else-if="activeStep === 3" class="p-5 pb-20 max-w-5xl mx-auto w-full space-y-4">
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
    <div v-else-if="activeStep === 4" class="px-5 py-7 pb-24 max-w-xl mx-auto w-full">
      <h2 class="text-[15px] font-semibold text-ink">Flujo de Producción</h2>
      <p class="text-[12.5px] text-ink-muted mt-1 leading-relaxed">
        Ya viene armado desde el costeo. Arrastra un paso para reordenarlo y ajusta <span class="text-ink-muted">"recibe de"</span> solo si el material sale de otro paso.
      </p>

      <div v-if="ORDER.indexOf(docStatus) >= 3" class="mt-3 text-[11.5px] text-amber-800 bg-amber-50 border border-amber-200 rounded-md px-3 py-2 flex items-start gap-2">
        <svg class="w-3.5 h-3.5 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"/></svg>
        <span>Ya se generaron documentos de producción con esta configuración. Si cambias "recibe de" aquí, revisa que el sub-ensamblaje resultante siga coincidiendo con lo que ya se creó.</span>
      </div>

      <div v-if="flujoLoading" class="flex justify-center py-16 text-ink-xlight">
        <svg class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
      </div>

      <div v-for="prod in flujoOps" v-else :key="prod.finished_item" class="mt-7 first:mt-6">
        <div class="flex items-baseline justify-between mb-1">
          <span class="text-[12.5px] font-medium text-ink truncate">{{ prod.finished_item }}</span>
          <span class="text-[11.5px] text-ink-light flex-shrink-0 ml-3">{{ (prod.qty || 0).toLocaleString('es-MX') }} pzas</span>
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
                    <button type="button" class="w-3.5 h-3.5 flex-shrink-0 flex items-center justify-center rounded text-ink-xlight hover:text-ink-muted hover:bg-surface-raised leading-none" @click="toggleTree(op, 'servicios')">{{ isTreeOpen(op, 'servicios') ? '−' : '+' }}</button>
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
                    <button type="button" class="w-3.5 h-3.5 flex-shrink-0 flex items-center justify-center rounded text-ink-xlight hover:text-ink-muted hover:bg-surface-raised leading-none" @click="toggleTree(op, 'recibe')">{{ isTreeOpen(op, 'recibe') || flujoEdit[op.op_key] ? '−' : '+' }}</button>
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
                    <button type="button" class="w-3.5 h-3.5 flex-shrink-0 flex items-center justify-center rounded text-ink-xlight hover:text-ink-muted hover:bg-surface-raised leading-none" @click="toggleTree(op, 'materiales')">{{ isTreeOpen(op, 'materiales') || matEdit[op.op_key] ? '−' : '+' }}</button>
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
        </div>

      </div>

      <div class="flex justify-end items-center gap-3 mt-8">
        <span v-if="flujoDirty" class="text-[11.5px] text-ink-light">Cambios sin guardar</span>
        <button :disabled="advancing || flujoLoading" class="px-4 py-2 text-[13px] font-medium text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center gap-1.5 transition-colors" @click="confirmarFlujo">
          {{ advancing ? "Preparando…" : "Confirmar y pasar a producción" }}
          <svg v-if="!advancing" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.4"><path stroke-linecap="round" stroke-linejoin="round" d="M13 7l5 5-5 5M6 12h12"/></svg>
        </button>
      </div>
    </div>


    <!-- ══════════ STEP 5 · PRODUCIR (centro de control) ══════════ -->
    <div v-else-if="activeStep === 5" class="p-5 pb-20 max-w-5xl mx-auto w-full space-y-4">

      <ActiveSOSelector :sales-orders="related.sales_orders" :active-name="activeSOName" @update:active-name="setActiveSO" />

      <ProductionProgressBar
        :materia-prima-pct="materiaPrimaPct"
        :sub-pct="subcontratacionPct"
        :sub-detail="prodComplete.lotes_total ? `${prodComplete.lotes_recibidos}/${prodComplete.lotes_total} lotes recibidos` : ''"
        :envio-pct="null"
      />

      <template v-if="!loteActivoRef">
      <div v-if="prepSteps.length" class="bg-white rounded-xl border border-surface-border p-4">
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
        <p class="text-[13px] text-ink-muted mt-1 mb-4">Se crean los BOMs y el plan (ligado a la orden de venta, con el almacén de materias primas y lo que falta comprar según inventario).</p>
        <button :disabled="advancing" class="px-4 py-2 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50" @click="prepararProduccion">Preparar producción</button>
      </div>

      <template v-else-if="hasPlan">
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

            <div v-if="!planValidated" class="flex items-center gap-2">
              <button :disabled="advancing" class="doc-action" @click="obtenerMateriasPrimas"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>Obtener materias primas</button>
              <div class="flex-1"></div>
              <button :disabled="advancing" class="doc-action" @click="guardarPlan">Guardar</button>
              <button :disabled="advancing" class="h-8 px-3.5 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center gap-1.5" @click="validarPlan"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Validar plan</button>
            </div>

            <div class="border-t border-surface-border pt-3">
              <div class="prod-head"><span class="prod-title"><svg class="w-4 h-4 text-ink-light" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"/></svg>Materias primas a comprar <span class="prod-count">{{ planDetail.mr_items.length }}</span></span></div>
              <div v-for="it in planDetail.mr_items" :key="it.item_code" class="prod-row">
                <span class="flex-1 min-w-0 truncate font-mono text-[12px]">{{ it.item_code }}</span>
                <span class="text-[13px] whitespace-nowrap">× {{ it.quantity }} {{ it.uom }}</span>
                <span class="prod-status">{{ it.warehouse }}</span>
              </div>
              <p v-if="!planDetail.mr_items.length" class="prod-empty">Sin faltantes (inventario suficiente) o pendiente de obtener.</p>
            </div>

            <div v-if="planValidated" class="border-t border-surface-border pt-3 flex items-center justify-between gap-3">
              <div>
                <p class="text-[13px] font-medium text-ink">Producción interna (opcional)</p>
                <p class="text-[11.5px] text-ink-muted">Poco usada si se subcontrata todo el proceso.</p>
              </div>
              <button :disabled="advancing" class="doc-action flex-shrink-0" @click="crearOrdenesTrabajo">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.6"><path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065zM15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                Orden de trabajo <span v-if="downstream.wos.length" class="text-green-600 ml-1">{{ downstream.wos.length }} creada(s)</span>
              </button>
            </div>
          </div>
        </details>

        <!-- ═══ Materia prima ═══ -->
        <div v-if="planValidated" class="bg-white rounded-xl border border-surface-border p-4 space-y-3">
          <div class="prod-head"><span class="prod-title"><svg class="w-4 h-4 text-ink-light" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10"/></svg>Materia prima</span></div>

          <div v-if="!mrDetail" class="text-center py-6">
            <p class="text-sm font-medium text-ink mb-1">Aún no has creado la solicitud de material</p>
            <p class="text-[12.5px] text-ink-muted mb-3">Se crea desde el plan, con el proveedor por materia prima ya asignado (del costeo).</p>
            <button :disabled="advancing" class="px-4 py-2 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50" @click="crearSolicitud">Crear solicitud de material</button>
          </div>

          <template v-else>
            <div :id="`doc-hl-${mrDetail.name}`" :class="{ 'doc-highlight-flash': highlightTarget === mrDetail.name }">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2.5">
                  <span class="text-[13px] font-semibold text-ink">{{ mrDetail.name }}</span>
                  <DocStatusPill :docstatus="mrDetail.docstatus" />
                </div>
                <a class="doc-action" :href="`/app/material-request/${mrDetail.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>ERPNext</a>
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
                 una por una después con "Nuevo lote". -->
            <div v-if="!mrValidated" class="border-t border-surface-border pt-3">
              <div class="flex items-center justify-between mb-1.5">
                <div>
                  <p class="section-title">Lotes de entrega (opcional)</p>
                  <p class="text-[11px] text-ink-light">Si la compra se va a escalonar en varias fechas, defínelo aquí — al validar se crean todas las órdenes de compra de un jalón, ya con su cantidad y fecha.</p>
                </div>
                <button class="add-link shrink-0" @click="addMrLote"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>Lote</button>
              </div>
              <template v-if="mrLotes.length">
                <div v-for="lote in mrLotes" :key="lote.id" class="rounded-lg border border-surface-border p-2.5 mb-2">
                  <div class="flex items-center gap-2 mb-2">
                    <input v-model="lote.lote_ref" class="field-input w-24 text-[11.5px] font-semibold" title="Nombre del lote — usa el mismo que su lote de subcontratación para que aparezcan juntos" />
                    <input v-model="lote.fecha_requerida" type="date" class="field-input w-40" />
                    <span class="text-[11px] text-ink-light flex-1">Fecha requerida — si no divide exacto, el último lote se queda con el registro del resto.</span>
                    <button class="del-btn" @click="removeMrLote(lote.id)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button>
                  </div>
                  <div class="grid grid-cols-2 gap-x-4 gap-y-1">
                    <div v-for="it in mrItems" :key="it.item_code" class="flex items-center gap-2">
                      <span class="text-[11.5px] font-mono flex-1 truncate">{{ it.item_code }}</span>
                      <input v-model.number="lote.cantidades[it.item_code]" type="number" min="0" class="field-input w-24 text-right" />
                    </div>
                  </div>
                </div>
                <div class="flex items-center justify-between">
                  <button class="add-link" @click="repartirMrLotesIgual">Repartir en partes iguales</button>
                  <p class="text-[11px] text-ink-light">Pendiente sin asignar: <span v-for="(it, i) in mrItems" :key="it.item_code">{{ i > 0 ? ' · ' : '' }}{{ it.item_code }}: {{ mrLotePendiente(it.item_code) }}</span></p>
                </div>
              </template>
            </div>

            <div v-if="!mrValidated" class="flex items-center gap-2">
              <div class="flex-1"></div>
              <button :disabled="advancing" class="doc-action" @click="guardarSolicitud">Guardar</button>
              <button :disabled="advancing" class="h-8 px-3.5 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center gap-1.5" @click="validarSolicitud"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>{{ mrLotes.length ? `Validar y dividir en ${mrLotes.length} lote(s)` : 'Validar solicitud' }}</button>
            </div>

          </template>
        </div>

        <!-- ═══ Compra de materia prima -- genera la Orden de Compra de cada
             proveedor (agrupa TODO lo que pide la Solicitud, sin depender de
             ningún "Lote de entrega" opcional). Reusa exactamente el mismo
             docCompra/PurchaseDocPanel que ya se usaba dentro de un lote -- solo
             que aquí no está condicionado a que exista esa división.

             OJO: si la Solicitud SÍ se dividió en Lotes de entrega
             (mr_dividir_en_lotes, ver mrDetail.usa_lotes_entrega), el botón
             genérico de aquí abajo se oculta -- generar de un jalón ignoraría esa
             división y compraría todo junto. En ese caso la OC de cada lote se
             sigue generando desde la vista de su propio lote de producción
             ("Materia prima de este lote"), como siempre. ═══ -->
        <div v-if="mrValidated" class="bg-white rounded-xl border border-surface-border p-4 space-y-3">
          <div class="prod-head"><span class="prod-title"><svg class="w-4 h-4 text-ink-light" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"/></svg>Compra de materia prima</span></div>

          <p v-if="mrDetail.usa_lotes_entrega && !mrResults.ocs.length" class="text-[12.5px] text-ink-muted">Esta Solicitud se dividió en Lotes de entrega — genera la Orden de Compra de cada lote desde la vista de su Lote de producción correspondiente, no aquí (para respetar la división).</p>

          <div v-else-if="!mrResults.ocs.length" class="flex items-center justify-between gap-3">
            <p class="text-[12.5px] text-ink-muted">Genera la Orden de Compra de cada proveedor (una por proveedor) — ahí ajustas UDM y precio si hace falta.</p>
            <button :disabled="advancing" class="h-9 px-4 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex-shrink-0" @click="crearOc()">Generar Orden(es) de Compra</button>
          </div>

          <template v-else>
            <div class="flex flex-wrap gap-1.5">
              <button
                v-for="po in mrResults.ocs" :key="po"
                class="h-8 px-3 text-[12.5px] font-semibold rounded-lg border flex-shrink-0"
                :class="ocSelected === po ? 'bg-brand-50 border-brand-300 text-brand-700' : 'bg-white border-surface-border text-ink hover:bg-surface-raised'"
                @click="selectOC(po)"
              >{{ po }}</button>
            </div>
            <div v-if="docCompra && docCompra.doctype === 'Purchase Order' && mrResults.ocs.includes(docCompra.name)" class="pt-1">
              <PurchaseDocPanel
                :doc="docCompra" :items="docCompraItems" :form="docCompraForm" desk-route="purchase-order"
                :payment-terms-options="cotDefaults.payment_terms_templates" :terms-options="cotDefaults.terms"
                show-pull-prices editable-uom :advancing="advancing"
                :inline-preview-url="printUrl(docCompra.doctype, docCompra.name)" :preview-key="previewKey"
                :requires-review="docCompra.requiere_doble_validacion" :reviewed="docCompra.revisado_yelke"
                :reviewed-by="docCompra.revisado_por_yelke" :reviewed-at="docCompra.revisado_en_yelke"
                :puede-revisar="permisosValidacion.puede_revisar" :puede-aprobar="permisosValidacion.puede_aprobar"
                @save="guardarDocCompra" @validate="validarDocCompra" @review="revisarDocCompra" @pull-prices="jalarPreciosOC"
                @send="openSend(docCompra.doctype, docCompra.name, docCompra.contact_email, docCompra.contact_mobile)"
              />
            </div>
          </template>
        </div>

        <!-- ═══ Continuar a producción -- llamado a la acción claro justo después de
             la Solicitud de Material, para no depender de que se note el pequeño "+"
             del riel de lotes arriba en el stepper (ver CosteoStepper.vue). Mismo
             botón/función que ese "+" -- abrirNuevoLote() ya crea y valida solo lo
             que haga falta y no exige dividir en lotes si no se quiere. ═══ -->
        <div v-if="mrValidated && !nuevoLoteForm.open && !lotesProduccion.length" class="bg-white rounded-xl border border-surface-border p-4 flex items-center justify-between gap-3">
          <div>
            <p class="text-sm font-semibold text-ink mb-0.5">Continuar a producción</p>
            <p class="text-[12.5px] text-ink-muted">Materia prima ya solicitada. Sin dividir en lotes, esto produce todo de un jalón.</p>
          </div>
          <button :disabled="advancing" class="h-9 px-4 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center gap-1.5" @click="abrirNuevoLote">
            Continuar<svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
          </button>
        </div>

        <!-- ═══ Nuevo lote (disparado desde el "+" del riel de lotes en el stepper) ═══ -->
        <div v-if="nuevoLoteForm.open && planValidated" class="bg-white rounded-xl border border-surface-border p-4 space-y-3">
          <div class="prod-head"><span class="prod-title"><svg class="w-4 h-4 text-ink-light" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>Nuevo lote de producción</span></div>

          <!-- Mientras se crean/validan solas las OC de subcontratación (ver
               abrirNuevoLote), se muestra un solo mensaje de carga en vez de dejar
               que se alcancen a ver, parpadeando, las pantallas intermedias de abajo
               (que son el respaldo manual para cuando algo no se pudo automatizar). -->
          <div v-if="nuevoLoteForm.loading && !nuevoLoteForm.porProducto.length" class="text-center py-6">
            <p class="text-sm text-ink-muted">Preparando el lote — creando y validando las órdenes de subcontratación…</p>
          </div>

          <div v-else-if="!subOcs.length" class="text-center py-6">
            <p class="text-sm font-medium text-ink mb-1">Aún no has creado las órdenes de subcontrato</p>
            <p class="text-[12.5px] text-ink-muted mb-3">Se crea una orden por proveedor (corte, costura, bordado…) — las etapas que comparten taller quedan juntas en la misma orden, cada una con su servicio y BOM de subcontratación.</p>
            <button :disabled="advancing" class="px-4 py-2 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50" @click="crearSubcontratos">Crear órdenes de subcontrato</button>
          </div>

          <!-- Prerrequisito: la OC de maquila de algún taller no se pudo validar sola
               (normalmente por permisos) -- respaldo manual. -->
          <template v-else-if="productosCosteo.some((p) => p.root_po && p.root_po_docstatus !== 1)">
            <p class="text-[12.5px] text-ink-muted">Antes de crear el primer lote, valida la orden de compra de maquila de cada taller.</p>
            <template v-if="subPo">
              <PurchaseDocPanel
                :doc="subPo" :items="subItems" :form="subForm" desk-route="purchase-order"
                :payment-terms-options="cotDefaults.payment_terms_templates" :terms-options="cotDefaults.terms"
                show-preview-button :advancing="advancing"
                :requires-review="subPo.requiere_doble_validacion" :reviewed="subPo.revisado_yelke"
                :reviewed-by="subPo.revisado_por_yelke" :reviewed-at="subPo.revisado_en_yelke"
                :puede-revisar="permisosValidacion.puede_revisar" :puede-aprobar="permisosValidacion.puede_aprobar"
                @save="guardarSub" @validate="validarSub" @review="revisarSub" @preview="openPdf('Purchase Order', subPo.name)"
                @send="openSend('Purchase Order', subPo.name, subPo.contact_email, subPo.contact_mobile)"
              />
              <p v-if="!omEsMaestra" class="text-[11.5px] text-ink-light mt-2">Esta ficha técnica se heredó de otra etapa del proyecto — solo se edita desde la primera.</p>
              <OrdenManufacturaForm
                class="mt-3"
                :general="omGeneral" :om-cab="omCab" :om-dama="omDama" :om-proc="omProc" :om-tablas="omTablas" :om-archivos="omArchivos"
                :uploading="omUploading" :disabled="!omEsMaestra" :OM_CAB="OM_CAB" :OM_DAMA="OM_DAMA" :talla-total="tallaTotal"
                :medidas-templates="medidasTemplates"
                @add-proceso="addProceso" @remove-proceso="removeProceso" @add-tabla="addTabla" @add-tabla-plantilla="addTablaPlantilla" @remove-tabla="removeTabla"
                @add-columna="addColumna" @remove-columna="removeColumna" @add-fila="addFila" @remove-fila="removeFila"
                @file="onOmFile" @remove-archivo="removeArchivo"
              />
            </template>
          </template>

          <!-- Cantidad por producto y fecha del lote (una vez validada la primera etapa) -->
          <template v-else>
            <div class="space-y-1.5">
              <div v-for="fila in nuevoLoteForm.porProducto" :key="fila.finished_item" class="flex items-center gap-2">
                <span class="text-[12.5px] text-ink flex-1 truncate" :title="fila.item_name">{{ fila.item_name }}</span>
                <template v-if="fila.po_docstatus === 1">
                  <select
                    v-if="tallasSinLoteDe(fila.finished_item).length"
                    v-model="fila.talla_row" class="field-input w-40 text-[11.5px]" :disabled="nuevoLoteForm.loading"
                    @change="onTallaLoteSelect(fila)"
                  >
                    <option value="">Producción estándar</option>
                    <option v-for="t in tallasSinLoteDe(fila.finished_item)" :key="t.name" :value="t.name">{{ t.talla_label }} · {{ t.qty }} pza(s) · {{ t.material_label }}</option>
                  </select>
                  <input v-model.number="fila.qty" type="number" min="0" step="1" :disabled="nuevoLoteForm.loading" class="field-input w-28" />
                  <span class="text-[11px] text-ink-light w-24 tabular-nums">pendiente {{ fila.saldo }}</span>
                </template>
                <span v-else class="text-[11.5px] text-amber-700 w-56">Valida antes la 1ª OC de este producto</span>
              </div>
              <p v-if="nuevoLoteForm.porProducto.some((f) => tallasSinLoteDe(f.finished_item).length)" class="text-[11px] text-ink-light">
                Si este lote es para una talla con material distinto (ej. cierre más grande), selecciónala arriba -- el envío de material a ese taller usará el artículo alterno correcto en vez del estándar.
              </p>
            </div>
            <div class="flex items-center gap-2">
              <input v-model="nuevoLoteForm.schedule_date" type="date" class="field-input w-40" />
              <button class="doc-action" @click="cerrarNuevoLote">Cancelar</button>
              <button :disabled="advancing || nuevoLoteForm.loading" class="h-8 px-3 text-[12.5px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50" @click="crearNuevoLote">Abrir lote</button>
            </div>
            <p class="text-[11.5px] text-ink-muted">Un lote = un encargo por proveedor. Indica cuánto de cada producto entra en este lote (0 = no entra). Un producto sin pendiente no aparece. La materia prima se envía después, taller por taller.</p>
            <p v-if="nuevoLoteForm.loading" class="text-[11px] text-ink-light">Revisando materia prima disponible…</p>
            <p v-else-if="nuevoLoteForm.porProducto.some((f) => f.limitadoPorStock)" class="text-[11.5px] text-amber-700 flex items-start gap-1.5">
              <svg class="w-4 h-4 flex-shrink-0 mt-px" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M5.07 19h13.86a2 2 0 001.71-3l-6.93-12a2 2 0 00-3.42 0l-6.93 12a2 2 0 001.71 3z"/></svg>
              Alguna cantidad sugerida está limitada por la materia prima en stock — puedes ajustarla a mano.
            </p>
          </template>
        </div>
      </template>
      </template>

      <!-- ═══ Pantalla de un lote: subetapa del flujo Producir ═══ -->
      <template v-else>
        <button class="text-[12.5px] text-ink-muted hover:text-ink flex items-center gap-1 -mb-1" @click="loteActivoRef = ''">
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/></svg>Volver a Producir
        </button>
        <div v-if="loteActivo" class="bg-white rounded-xl border border-surface-border p-4 space-y-3">
          <div class="flex items-start justify-between">
            <span class="prod-title"><svg class="w-4 h-4 text-ink-light flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/></svg>
              <span>{{ loteActivoRef }}<span class="normal-case font-normal text-ink-muted">{{ loteActivo.schedule_date ? ' · ' + loteActivo.schedule_date.slice(0,10) : '' }}</span>
                <span v-if="loteActivo.productos.length" class="block normal-case font-normal text-[11.5px] text-ink-light mt-0.5">
                  {{ loteActivo.productos.map((x) => `${x.item_name}: ${x.qty}`).join('  ·  ') }}
                </span>
              </span>
            </span>
          </div>

          <!-- Materia prima de este lote -->
          <div v-if="proveedoresLote(loteActivo).length" class="border-t border-surface-border pt-3">
            <p class="section-title mb-2">Materia prima de este lote</p>

            <!-- Un grupo por proveedor: sus materiales + sus 4 botones, en el orden
                 real del proceso -- Solicitud de cotización / Presupuesto / OC /
                 Recibo de compra -- cada uno con su propia vista desplegable, ninguno
                 se genera solo. El orden de los proveedores sale de material_items
                 (TODOS los materiales del lote, tengan OC o no) para que la tarjeta de
                 un proveedor no cambie de lugar apenas genera su primer documento. -->
            <div
              v-for="grp in proveedoresLote(loteActivo)" :key="grp.supplier"
              class="mb-2.5 border border-surface-border rounded-lg p-2.5"
            >
              <p class="text-[12px] font-semibold text-ink mb-1.5">{{ grp.supplier }}</p>
              <div v-if="grp.items.length" class="mb-2">
                <div v-for="it in grp.items" :key="it.item_code" class="prod-row">
                  <span class="flex-1 min-w-0 truncate font-mono text-[12px]">{{ it.item_code }}</span>
                  <span class="text-[13px] whitespace-nowrap">× {{ it.qty }} {{ it.uom }}</span>
                </div>
              </div>
              <div class="flex flex-wrap items-center gap-1.5">
                <button
                  :disabled="advancing" class="doc-action"
                  :class="loteDocBtnClass(loteDocOpen.supplier === grp.supplier && loteDocOpen.tab === 'rfq', rfqDeProveedor(loteActivo, grp.supplier)?.docstatus === 1)"
                  @click="toggleLoteDoc(loteActivo, grp, 'rfq')"
                ><svg class="w-3 h-3 transition-transform" :class="{ 'rotate-90': loteDocOpen.supplier === grp.supplier && loteDocOpen.tab === 'rfq' }" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg><svg v-if="rfqDeProveedor(loteActivo, grp.supplier)?.docstatus === 1" class="w-3 h-3 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>{{ rfqDeProveedor(loteActivo, grp.supplier)?.name || 'Solicitud de cotización' }}</button>

                <button
                  :disabled="advancing" class="doc-action"
                  :class="loteDocBtnClass(loteDocOpen.supplier === grp.supplier && loteDocOpen.tab === 'sq', sqDeProveedor(loteActivo, grp.supplier)?.docstatus === 1)"
                  @click="toggleLoteDoc(loteActivo, grp, 'sq')"
                ><svg class="w-3 h-3 transition-transform" :class="{ 'rotate-90': loteDocOpen.supplier === grp.supplier && loteDocOpen.tab === 'sq' }" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg><svg v-if="sqDeProveedor(loteActivo, grp.supplier)?.docstatus === 1" class="w-3 h-3 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>{{ sqDeProveedor(loteActivo, grp.supplier)?.name || 'Presupuesto de proveedor' }}</button>

                <button
                  :disabled="advancing" class="doc-action"
                  :class="loteDocBtnClass(loteDocOpen.supplier === grp.supplier && loteDocOpen.tab === 'oc', grp.po?.docstatus === 1)"
                  @click="toggleLoteDoc(loteActivo, grp, 'oc')"
                ><svg class="w-3 h-3 transition-transform" :class="{ 'rotate-90': loteDocOpen.supplier === grp.supplier && loteDocOpen.tab === 'oc' }" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg><svg v-if="grp.po?.docstatus === 1" class="w-3 h-3 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>{{ grp.po?.name || 'Generar orden de compra' }}<span v-if="grp.po?.enviado_el" class="opacity-70"> · enviado</span></button>

                <button
                  :disabled="advancing || grp.po?.docstatus !== 1" class="doc-action"
                  :class="loteDocBtnClass(loteDocOpen.supplier === grp.supplier && loteDocOpen.tab === 'recibo', grp.po?.receipt_validated)"
                  @click="toggleLoteDoc(loteActivo, grp, 'recibo')"
                ><svg class="w-3 h-3 transition-transform" :class="{ 'rotate-90': loteDocOpen.supplier === grp.supplier && loteDocOpen.tab === 'recibo' }" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg><svg v-if="grp.po?.receipt_validated" class="w-3 h-3 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>{{ grp.po?.receipt ? grp.po.receipt.name : 'Recibo de compra' }}</button>
              </div>

              <div v-if="loteDocOpen.supplier === grp.supplier && loteDocOpen.tab !== 'recibo' && docCompra" :id="`doc-hl-${docCompra.name}`" :class="['mt-2.5 pt-2.5 border-t border-dashed border-surface-border', { 'doc-highlight-flash': highlightTarget === docCompra.name }]">
                <PurchaseDocPanel
                  :doc="docCompra" :items="docCompraItems" :form="docCompraForm"
                  :desk-route="DOC_COMPRA[loteDocOpen.tab].desk"
                  :payment-terms-options="cotDefaults.payment_terms_templates" :terms-options="cotDefaults.terms"
                  :show-pull-prices="loteDocOpen.tab === 'oc'"
                  :editable-uom="docCompra.doctype === 'Purchase Order'"
                  :help-text="loteDocOpen.tab === 'oc' ? 'Precio y UDM se ajustan aquí. Por defecto trae el precio del costeo (si la UDM sigue igual) o el del Presupuesto de proveedor si generaste uno — Jalar precios lo vuelve a calcular.' : ''"
                  :advancing="advancing"
                  :inline-preview-url="printUrl(docCompra.doctype, docCompra.name)" :preview-key="previewKey"
                  :requires-review="docCompra.requiere_doble_validacion" :reviewed="docCompra.revisado_yelke"
                  :reviewed-by="docCompra.revisado_por_yelke" :reviewed-at="docCompra.revisado_en_yelke"
                  :puede-revisar="permisosValidacion.puede_revisar" :puede-aprobar="permisosValidacion.puede_aprobar"
                  @save="guardarDocCompra" @validate="validarDocCompra" @review="revisarDocCompra" @pull-prices="jalarPreciosOC"
                  @send="openSend(docCompra.doctype, docCompra.name, docCompra.contact_email, docCompra.contact_mobile)"
                />
              </div>
              <div v-if="loteDocOpen.supplier === grp.supplier && loteDocOpen.tab === 'recibo' && reciboPr" :id="`doc-hl-${reciboPr.name}`" :class="['mt-2.5 pt-2.5 border-t border-dashed border-surface-border', { 'doc-highlight-flash': highlightTarget === reciboPr.name }]">
                <PurchaseDocPanel
                  :doc="reciboPr" :items="reciboItems" :form="reciboForm"
                  desk-route="purchase-receipt" show-warehouse :show-send="false"
                  help-text="IVA aplicado · al validar entra a inventario y contabilidad."
                  validate-label="Validar recibo" validated-text="Validado (en inventario)"
                  :advancing="advancing" shipping-required
                  @save="guardarRecibo" @validate="validarRecibo"
                  @shipping-missing="showToast('Captura el costo de envío antes de validar (pon 0 si no hubo)', 'error')"
                />
              </div>
            </div>
          </div>

              <!-- Flujo del lote: un CARRIL por producto -- sus paradas (talleres) en
                   orden, con el producto terminado al final. Click en una tarjeta =
                   abrir su detalle abajo. -->
              <div class="border-t border-surface-border pt-3">
                <p class="section-title mb-3">Flujo de este lote</p>
                <div class="space-y-4">
                  <div v-for="track in tracksLote" :key="track.finished_item">
                    <p class="text-[12px] font-semibold text-ink mb-1.5 flex items-center gap-1.5">
                      <svg class="w-3.5 h-3.5 text-ink-light" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M16 4l4 4-3 1v11H7V9L4 8l4-4 2 2h4l2-2z"/></svg>
                      {{ track.item_name }}<span class="font-normal text-ink-muted">· {{ track.qty }} pza(s)</span>
                    </p>
                    <div class="overflow-x-auto -mx-1 px-1">
                      <div class="flex items-stretch gap-2 w-max">
                        <template v-for="(pa, i) in track.paradas" :key="pa.parada_id">
                          <svg v-if="i > 0" class="w-4 h-4 text-ink-xlight self-center flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
                          <button
                            class="text-left w-48 rounded-lg border px-2.5 py-2 transition-colors flex-shrink-0"
                            :class="paradaBtnClass(pa)"
                            @click="seleccionarParada(pa)"
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

            <div v-if="paradaActiva" class="border-t border-surface-border pt-3 space-y-3">
              <!-- Flujo de esta etapa: Orden de compra / Orden de subcontratación / Transferencia / Recibo --
                   mismo patrón de 4 botones desplegables que materia prima, con el flujo real de
                   subcontratación (no aplica RFQ/Presupuesto: el taller ya tiene precio pactado en la OC). -->
              <div class="flex flex-wrap items-center gap-1.5">
                <button
                  :disabled="advancing" class="doc-action"
                  :class="loteDocBtnClass(subStepOpen === 'oc', paradaActiva.po_docstatus === 1)"
                  @click="subStepOpen = 'oc'"
                ><svg class="w-3 h-3 transition-transform" :class="{ 'rotate-90': subStepOpen === 'oc' }" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg><svg v-if="paradaActiva.po_docstatus === 1" class="w-3 h-3 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>{{ subPo?.name || 'Orden de compra' }}</button>

                <button
                  :disabled="advancing || paradaActiva.po_docstatus !== 1" class="doc-action"
                  :class="loteDocBtnClass(subStepOpen === 'sco', paradaActiva.sco_docstatus === 1)"
                  @click="openSubStepSco"
                ><svg class="w-3 h-3 transition-transform" :class="{ 'rotate-90': subStepOpen === 'sco' }" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg><svg v-if="paradaActiva.sco_docstatus === 1" class="w-3 h-3 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>{{ paradaActiva.sco || 'Orden de subcontratación' }}</button>

                <button
                  :disabled="advancing || paradaActiva.sco_docstatus !== 1" class="doc-action"
                  :class="loteDocBtnClass(subStepOpen === 'transfer', paradaActiva.transfer_done)"
                  @click="subStepOpen = 'transfer'"
                ><svg class="w-3 h-3 transition-transform" :class="{ 'rotate-90': subStepOpen === 'transfer' }" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg><svg v-if="paradaActiva.transfer_done" class="w-3 h-3 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>{{ transDoc?.name || 'Transferencia' }}</button>

                <button
                  :disabled="advancing || !paradaActiva.transfer_done" class="doc-action"
                  :class="loteDocBtnClass(subStepOpen === 'recibo', paradaActiva.receipt_validated)"
                  @click="subStepOpen = 'recibo'"
                ><svg class="w-3 h-3 transition-transform" :class="{ 'rotate-90': subStepOpen === 'recibo' }" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg><svg v-if="paradaActiva.receipt_validated" class="w-3 h-3 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>{{ scr?.name || 'Recibo de subcontratación' }}</button>
              </div>

              <!-- Orden de compra -->
              <template v-if="subStepOpen === 'oc'">
                <div v-if="!paradaActiva.po" class="text-center py-6">
                  <p class="text-sm font-medium text-ink mb-1">Aún no has creado las órdenes de subcontrato</p>
                  <p class="text-[12.5px] text-ink-muted mb-3">Se crea una orden por proveedor (corte, costura, bordado…) — las etapas que comparten taller quedan juntas en la misma orden, cada una con su servicio y BOM de subcontratación.</p>
                  <button :disabled="advancing" class="px-4 py-2 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50" @click="crearSubcontratosDesdeLote">Crear órdenes de subcontrato</button>
                </div>
                <template v-else-if="subPo">
                  <p v-if="paradaActiva.po_docstatus !== 1" class="text-[12.5px] text-ink-muted">Valida la orden de compra de {{ paradaActiva.supplier }} para poder avanzar este lote.</p>
                  <div :id="`doc-hl-${subPo.name}`" :class="{ 'doc-highlight-flash': highlightTarget === subPo.name }">
                    <PurchaseDocPanel
                      :doc="subPo" :items="subItems" :form="subForm" desk-route="purchase-order"
                      :payment-terms-options="cotDefaults.payment_terms_templates" :terms-options="cotDefaults.terms"
                      show-preview-button :advancing="advancing"
                      :requires-review="subPo.requiere_doble_validacion" :reviewed="subPo.revisado_yelke"
                      :reviewed-by="subPo.revisado_por_yelke" :reviewed-at="subPo.revisado_en_yelke"
                      :puede-revisar="permisosValidacion.puede_revisar" :puede-aprobar="permisosValidacion.puede_aprobar"
                      @save="guardarSub" @validate="validarSub" @review="revisarSub" @preview="openPdf('Purchase Order', subPo.name)"
                      @send="openSend('Purchase Order', subPo.name, subPo.contact_email, subPo.contact_mobile)"
                    />
                  </div>
                  <p v-if="!omEsMaestra" class="text-[11.5px] text-ink-light mt-2">Esta ficha técnica se heredó de otra etapa del proyecto — solo se edita desde la primera.</p>
                  <OrdenManufacturaForm
                    class="mt-3"
                    :general="omGeneral" :om-cab="omCab" :om-dama="omDama" :om-proc="omProc" :om-tablas="omTablas" :om-archivos="omArchivos"
                    :uploading="omUploading" :disabled="!omEsMaestra" :OM_CAB="OM_CAB" :OM_DAMA="OM_DAMA" :talla-total="tallaTotal"
                    :medidas-templates="medidasTemplates"
                    @add-proceso="addProceso" @remove-proceso="removeProceso" @add-tabla="addTabla" @add-tabla-plantilla="addTablaPlantilla" @remove-tabla="removeTabla"
                    @add-columna="addColumna" @remove-columna="removeColumna" @add-fila="addFila" @remove-fila="removeFila"
                    @file="onOmFile" @remove-archivo="removeArchivo"
                  />
                </template>
              </template>

              <!-- Orden de subcontratación (SCO) -->
              <template v-if="subStepOpen === 'sco'">
                <div v-if="!paradaActiva.sco" class="text-center py-6">
                  <p class="text-sm font-medium text-ink mb-1">{{ paradaActiva.titulo }} · {{ paradaActiva.supplier }} — {{ loteActivoRef }}</p>
                  <template v-if="paradaActiva.productos.some((x) => x.qty > 0) || loteActivo.productos.some((x) => x.qty > 0)">
                    <p class="text-[12.5px] text-ink-muted mb-3">
                      Se encarga con la cantidad del lote ({{ paradaProductosTexto(paradaActiva.productos.some((x) => x.qty > 0) ? paradaActiva.productos : loteActivo.productos) }}) y fecha del lote.
                    </p>
                    <button :disabled="advancing" class="px-4 py-2 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50" @click="abrirParada()">Encargar a {{ paradaActiva.supplier }}</button>
                  </template>
                  <template v-else>
                    <p class="text-[12.5px] text-ink-muted mb-3">Este lote todavía no tiene cantidad definida (nació de materia prima) — indícala aquí.</p>
                    <p v-if="primeraEtapaLoading" class="text-[11px] text-ink-light mb-2">Revisando materia prima disponible…</p>
                    <div class="flex items-center justify-center gap-2 mb-2">
                      <input v-model.number="primeraEtapaQty" type="number" min="0" step="1" placeholder="Cantidad" :disabled="primeraEtapaLoading" class="field-input w-32 text-center" />
                      <button :disabled="advancing || primeraEtapaLoading" class="px-4 py-2 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50" @click="abrirParada(primeraEtapaQty)">Encargar a {{ paradaActiva.supplier }}</button>
                    </div>
                    <p v-if="!primeraEtapaLoading && primeraEtapaLimitado" class="text-[11.5px] text-amber-700 flex items-center justify-center gap-1.5">
                      <svg class="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M5.07 19h13.86a2 2 0 001.71-3l-6.93-12a2 2 0 00-3.42 0l-6.93 12a2 2 0 001.71 3z"/></svg>
                      Cantidad sugerida según la materia prima disponible en stock — puedes ajustarla a mano.
                    </p>
                  </template>
                </div>
                <div v-else-if="scoSel" class="space-y-3">
                  <div class="bg-white rounded-xl border border-surface-border p-4">
                    <div class="flex items-center justify-between mb-3">
                      <div class="flex items-center gap-2.5">
                        <span class="text-sm font-semibold text-ink">{{ scoSel.name }}</span>
                        <DocStatusPill :docstatus="scoSel.docstatus" />
                      </div>
                      <a class="doc-action" :href="`/app/subcontracting-order/${scoSel.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>ERPNext</a>
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                      <div><label class="field-label">Almacén del taller (proveedor)</label><select v-model="scoForm.supplier_warehouse" :disabled="scoValidated" class="field-input"><option value="">— Selecciona —</option><option v-for="w in flujo.warehouses" :key="w.name" :value="w.name">{{ w.warehouse_name || w.name }}</option></select></div>
                      <div><label class="field-label">Almacén de destino (producto terminado)</label><select v-model="scoForm.set_warehouse" :disabled="scoValidated" class="field-input"><option value="">— Selecciona —</option><option v-for="w in flujo.warehouses" :key="w.name" :value="w.name">{{ w.warehouse_name || w.name }}</option></select></div>
                      <div><label class="field-label">Dirección del proveedor</label><select v-model="scoForm.supplier_address" :disabled="scoValidated" class="field-input"><option value="">— Sin dirección —</option><option v-for="a in flujo.address_options" :key="a.value" :value="a.value">{{ a.label }}</option></select></div>
                      <div><label class="field-label">Contacto</label><select v-model="scoForm.contact_person" :disabled="scoValidated" class="field-input"><option value="">— Sin contacto —</option><option v-for="c in flujo.contact_options" :key="c.value" :value="c.value">{{ c.label }}</option></select></div>
                      <div><label class="field-label">Dirección de envío</label><select v-model="scoForm.shipping_address" :disabled="scoValidated" class="field-input"><option value="">— Sin dirección —</option><option v-for="a in flujo.address_options" :key="a.value" :value="a.value">{{ a.label }}</option></select></div>
                      <div><label class="field-label">Distribuir costos adicionales por</label><select v-model="scoForm.distribute_additional_costs_based_on" :disabled="scoValidated" class="field-input"><option value="Qty">Cantidad</option><option value="Amount">Importe</option></select></div>
                    </div>
                  </div>

                  <div class="bg-white rounded-xl border border-surface-border p-4">
                    <div class="flex items-center justify-between mb-1.5">
                      <p class="section-title">Costos adicionales</p>
                      <button v-if="!scoValidated" class="add-link" @click="addCosto"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>Costo</button>
                    </div>
                    <p v-if="!scoCostos.length" class="prod-empty mb-1">Sin costos adicionales.</p>
                    <div v-for="(c, i) in scoCostos" :key="i" class="flex items-center gap-2 mb-1.5">
                      <input v-model="c.description" placeholder="Descripción" :disabled="scoValidated" class="field-input flex-1" />
                      <input v-model.number="c.amount" type="number" min="0" step="0.01" placeholder="Importe" :disabled="scoValidated" class="field-input w-32 text-right" />
                      <button v-if="!scoValidated" class="del-btn" @click="removeCosto(i)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button>
                    </div>
                    <p class="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-2.5 py-1.5 mt-1 flex items-start gap-1.5">
                      <svg class="w-3.5 h-3.5 flex-shrink-0 mt-px" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M5.07 19h13.86a2 2 0 001.71-3l-6.93-12a2 2 0 00-3.42 0l-6.93 12a2 2 0 001.71 3z"/></svg>
                      <span>Esto solo se suma al total a pagar al taller — <strong>no se capitaliza</strong> al valor del material recibido. Para fletes que sí deban afectar el costo del producto (ida al taller, por ejemplo), captúralos en el paso "Transferencia".</span>
                    </p>
                  </div>

                  <div v-if="scoSel.supplied_items.length" class="bg-white rounded-xl border border-surface-border p-4">
                    <p class="section-title mb-2">Materia prima requerida (se transferirá al taller)</p>
                    <table class="w-full text-sm">
                      <thead><tr class="text-left text-xs font-semibold text-ink-light border-b border-surface-border"><th class="py-2">Material</th><th class="py-2 w-24 text-right">Cant.</th><th class="py-2 w-16">UOM</th></tr></thead>
                      <tbody>
                        <tr v-for="(m, i) in scoSel.supplied_items" :key="i" class="border-b border-surface-border/60">
                          <td class="py-1.5 pr-2">{{ m.item_name || m.rm_item_code }}</td>
                          <td class="py-1.5 pr-2 text-right">{{ m.required_qty }}</td>
                          <td class="py-1.5 pr-2 text-ink-muted text-xs">{{ m.stock_uom }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  <div class="flex items-center gap-2 flex-wrap bg-white rounded-xl border border-surface-border p-3">
                    <button class="doc-action" @click="openPdf('Subcontracting Order', scoSel.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>Vista previa</button>
                    <div class="flex-1"></div>
                    <template v-if="!scoValidated">
                      <button :disabled="advancing" class="doc-action" @click="guardarSco">Guardar</button>
                      <button :disabled="advancing" class="h-8 px-4 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center gap-1.5" @click="validarSco"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Validar</button>
                    </template>
                    <span v-else class="text-[13px] text-green-700 font-medium flex items-center gap-1.5"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Validada · continúa con la transferencia</span>
                  </div>
                </div>
              </template>

              <!-- Transferencia de material -->
              <template v-if="subStepOpen === 'transfer'">
                <div v-if="scoValidated">
                  <div v-if="!transDoc" class="bg-white rounded-xl border border-surface-border p-4">
                    <p class="text-[12px] text-ink-muted mb-3">Crea el movimiento de materia prima (Stock Entry · Enviar a subcontratista) hacia el almacén del taller. Se crea en <b>borrador</b> aquí mismo para que ajustes almacenes y lo valides.</p>
                    <div v-if="scoSel?.supplied_items?.length" class="overflow-x-auto">
                      <table class="w-full text-sm">
                        <thead><tr class="text-left text-xs font-semibold text-ink-light border-b border-surface-border"><th class="py-2">Material</th><th class="py-2 w-24 text-right">Cant.</th><th class="py-2 w-16">UOM</th></tr></thead>
                        <tbody>
                          <tr v-for="(m, i) in scoSel.supplied_items" :key="i" class="border-b border-surface-border/60">
                            <td class="py-1.5 pr-2">{{ m.item_name || m.rm_item_code }}</td>
                            <td class="py-1.5 pr-2 text-right">{{ m.required_qty }}</td>
                            <td class="py-1.5 pr-2 text-ink-muted text-xs">{{ m.stock_uom }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                    <p v-else class="prod-empty">La orden de subcontratación no tiene materia prima ligada (revisa el BOM de subcontratación).</p>
                    <!-- Camino rápido: "ya le mandé el material" hace transferencia +
                         validación + recibo en borrador de un jalón. El camino largo
                         (crear la transferencia y revisarla antes de validar) se
                         conserva para cuando hay que ajustar almacenes o cantidades. -->
                    <div class="flex items-center gap-2 mt-3 flex-wrap">
                      <p class="text-[11.5px] text-ink-muted">Al enviar, el recibo queda listo para que confirmes cuánto entregó el taller.</p>
                      <div class="flex-1"></div>
                      <button :disabled="advancing || !scoSel?.supplied_items?.length" class="doc-action" @click="transferirMaterial">Revisar transferencia antes</button>
                      <button :disabled="advancing || !scoSel?.supplied_items?.length" class="h-8 px-4 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center gap-1.5" @click="enviarMaterialTaller()"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/></svg>Enviar al taller</button>
                    </div>
                  </div>
                  <template v-else>
                    <div class="bg-white rounded-xl border border-surface-border p-4">
                      <div class="flex items-center justify-between mb-3">
                        <div class="flex items-center gap-2.5">
                          <span class="text-sm font-semibold text-ink">{{ transDoc.name }}</span>
                          <DocStatusPill :docstatus="transDoc.docstatus" />
                        </div>
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
                          <thead><tr class="text-left text-xs font-semibold text-ink-light border-b border-surface-border"><th class="py-2">Material</th><th class="py-2 w-24 text-right">A transferir</th><th class="py-2 w-44">Almacén de origen</th><th class="py-2 w-24 text-right">Disponible</th><th class="py-2 w-16">UOM</th></tr></thead>
                          <tbody>
                            <tr v-for="it in transDoc.items" :key="it.name" class="border-b border-surface-border/60">
                              <td class="py-1.5 pr-2">{{ it.item_name || it.item_code }}</td>
                              <td class="py-1.5 pr-2"><input v-if="!transValidated" v-model.number="it.qty" type="number" min="0" step="1" class="field-input text-right" /><span v-else class="block text-right">{{ it.qty }}</span></td>
                              <td class="py-1.5 pr-2">
                                <select v-if="!transValidated" v-model="it.s_warehouse" class="field-input" @change="refrescarDisponibleFila(it)"><option value="">— Selecciona —</option><option v-for="w in flujo.warehouses" :key="w.name" :value="w.name">{{ w.warehouse_name || w.name }}</option></select>
                                <span v-else class="text-ink-muted text-xs">{{ it.s_warehouse }}</span>
                              </td>
                              <td class="py-1.5 pr-2 text-right" :class="(it.available ?? 0) < it.qty ? 'text-red-600 font-semibold' : 'text-ink-muted'">{{ it.available === null ? '—' : it.available }}</td>
                              <td class="py-1.5 pr-2 text-ink-muted text-xs">{{ it.uom }}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
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
                        <input v-model.number="c.amount" type="number" min="0" step="0.01" placeholder="Importe" :disabled="transValidated" class="field-input w-32 text-right" />
                        <button v-if="!transValidated" class="del-btn" @click="removeCostoTrans(i)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button>
                      </div>
                      <div v-if="transCostos.length" class="mt-1">
                        <label class="field-label">Distribuir por</label>
                        <select v-model="transForm.distribute_additional_costs_based_on" :disabled="transValidated" class="field-input w-40"><option value="Qty">Cantidad</option><option value="Amount">Importe</option></select>
                      </div>
                    </div>

                    <div class="flex items-center gap-2 flex-wrap bg-white rounded-xl border border-surface-border p-3 mt-3">
                      <button class="doc-action" @click="openPdf('Stock Entry', transDoc.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>Vista previa</button>
                      <div class="flex-1"></div>
                      <template v-if="!transValidated">
                        <button :disabled="advancing" class="doc-action" @click="guardarTrans">Guardar</button>
                        <button :disabled="advancing" class="h-8 px-4 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center gap-1.5" @click="validarTransferencia"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Validar</button>
                      </template>
                      <span v-else class="text-[13px] text-green-700 font-medium flex items-center gap-1.5"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Material transferido · continúa con el recibo</span>
                    </div>
                  </template>
                </div>
              </template>

              <!-- Recibo de subcontratación -->
              <template v-if="subStepOpen === 'recibo'">
                <div v-if="transferDone">
                  <div v-if="!scr" class="bg-white rounded-xl border border-surface-border p-6 text-center">
                    <p class="text-[12.5px] text-ink-muted mb-3">Genera el recibo de subcontratación para ingresar a inventario lo que produjo el taller.</p>
                    <button :disabled="advancing" class="px-4 py-2 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50" @click="crearReciboSub">Crear recibo de subcontratación</button>
                  </div>
                  <template v-else>
                    <div class="bg-white rounded-xl border border-surface-border p-4">
                      <div class="flex items-center justify-between mb-3">
                        <div class="flex items-center gap-2.5">
                          <span class="text-sm font-semibold text-ink">{{ scr.name }}</span>
                          <DocStatusPill :docstatus="scr.docstatus" :label="scrValidated ? 'Validado' : 'Borrador'" />
                        </div>
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
                            <td class="py-1.5 pr-2">{{ it.item_name || it.item_code }}</td>
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
                        <input v-model.number="c.amount" type="number" min="0" step="0.01" placeholder="Importe" :disabled="scrValidated" class="field-input w-32 text-right" />
                        <button v-if="!scrValidated" class="del-btn" @click="removeCostoScr(i)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button>
                      </div>
                      <div v-if="scrCostos.length" class="mt-1">
                        <label class="field-label">Distribuir por</label>
                        <select v-model="scrForm.distribute_additional_costs_based_on" :disabled="scrValidated" class="field-input w-40"><option value="Qty">Cantidad</option><option value="Amount">Importe</option></select>
                      </div>
                    </div>

                    <div class="flex items-center gap-2 flex-wrap bg-white rounded-xl border border-surface-border p-3 mt-3">
                      <button class="doc-action" @click="openPdf('Subcontracting Receipt', scr.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>Vista previa</button>
                      <div class="flex-1"></div>
                      <template v-if="!scrValidated">
                        <button :disabled="advancing" class="doc-action" @click="guardarScr">Guardar</button>
                        <button :disabled="advancing" class="h-8 px-4 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center gap-1.5" @click="onValidarScr"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Validar recibo</button>
                      </template>
                      <span v-else class="text-[13px] text-green-700 font-medium flex items-center gap-1.5"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Recibido · producto en inventario</span>
                    </div>
                  </template>
                </div>
              </template>
            </div>
        </div>
      </template>
    </div>

    <!-- ══════════ STEP 6 · ENVIAR (Remisión) ══════════ -->
    <div v-else-if="activeStep === 6" class="p-5 pb-20">
      <div class="max-w-6xl mx-auto mb-4 space-y-3">
        <ActiveSOSelector :sales-orders="related.sales_orders" :active-name="activeSOName" @update:active-name="setActiveSO" />
        <ProductionProgressBar
          :materia-prima-pct="materiaPrimaPct"
          :sub-pct="subcontratacionPct"
          :sub-detail="prodComplete.lotes_total ? `${prodComplete.lotes_recibidos}/${prodComplete.lotes_total} lotes recibidos` : ''"
          :envio-pct="activeSO ? Math.round(related.delivery_per_delivered || 0) : null"
        />
      </div>
      <div class="flex gap-5 items-start max-w-6xl mx-auto">

        <!-- Izquierda: datos de la remisión -->
        <div class="w-80 flex-shrink-0 bg-white rounded-xl border border-surface-border p-5">
          <div class="flex items-center justify-between mb-1">
            <p class="text-sm font-semibold text-ink">Remisión (entrega)</p>
            <span v-if="related.delivery_notes.length > 1" class="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700">{{ related.delivery_notes.length }} remisiones</span>
          </div>
          <p class="text-[12px] text-ink-muted mb-3">Registra la entrega física al cliente — libera el producto terminado del inventario y genera el costo de venta real. Si el pedido se entrega en varias ubicaciones, crea una remisión por cada una.</p>

          <div v-if="!related.delivery_notes.length">
            <button :disabled="advancing || activeSO?.docstatus !== 1" class="w-full h-9 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-40 flex items-center justify-center gap-2" @click="generarRemision">
              <svg v-if="advancing" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
              Crear remisión
            </button>
            <p v-if="activeSO?.docstatus !== 1" class="text-[11px] text-ink-light mt-2 text-center">Primero valida la orden de venta.</p>
          </div>

          <template v-else>
            <!-- Lista de remisiones (una por dirección/entrega parcial) -->
            <div class="space-y-1 mb-3">
              <button v-for="dn in related.delivery_notes" :key="dn.name" class="w-full flex items-center justify-between gap-2 px-2.5 py-1.5 rounded-lg text-left transition-colors" :class="dn.name === dnSel ? 'bg-brand-50 ring-1 ring-brand-200' : 'hover:bg-surface-raised'" @click="selectDn(dn.name)">
                <span class="text-[12.5px] font-medium text-ink truncate">{{ dn.name }}</span>
                <span class="text-[10.5px] font-semibold px-1.5 py-0.5 rounded-full shrink-0" :class="dn.docstatus === 1 ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'">{{ dn.docstatus === 1 ? 'Validada' : 'Borrador' }}</span>
              </button>
            </div>
            <div v-if="related.delivery_per_delivered > 0" class="text-[11px] text-ink-muted mb-3">Entregado: {{ related.delivery_per_delivered.toFixed(0) }}%</div>
            <button v-if="puedeNuevaRemision" :disabled="advancing" class="w-full h-8 mb-3 text-[13px] font-medium text-brand-600 border border-dashed border-brand-200 rounded-lg hover:bg-brand-50 disabled:opacity-50 flex items-center justify-center gap-1.5" @click="generarRemision">
              <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
              Nueva remisión (otra dirección)
            </button>
            <p v-else-if="related.delivery_notes.some(d => d.docstatus === 0)" class="text-[11px] text-ink-light mb-3">Valida la remisión en borrador antes de crear otra.</p>

            <div v-if="dnDoc" :id="`doc-hl-${dnDoc.name}`" class="pt-3 border-t border-surface-border" :class="{ 'doc-highlight-flash': highlightTarget === dnDoc.name }">
            <label class="field-label">Dirección de envío <span class="text-ink-light font-normal">(si es distinta a la de facturación)</span></label>
            <select v-model="dnForm.shipping_address_name" class="field-input mb-3" :disabled="dnValidated">
              <option value="">— Misma que facturación —</option>
              <option v-for="a in (dnDoc.address_options || [])" :key="a.value" :value="a.value">{{ a.label }}</option>
            </select>

            <label class="field-label">Dirección de facturación</label>
            <select v-model="dnForm.customer_address" class="field-input mb-3" :disabled="dnValidated">
              <option value="">— Sin especificar —</option>
              <option v-for="a in (dnDoc.address_options || [])" :key="a.value" :value="a.value">{{ a.label }}</option>
            </select>

            <label class="field-label">Fecha de entrega</label>
            <input v-model="dnForm.posting_date" type="date" class="field-input mb-3" :disabled="dnValidated" />

            <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-1.5">Costo de envío <span class="normal-case font-normal text-ink-light">(opcional)</span></p>
            <label class="field-label">Proveedor de transporte</label>
            <LinkInput v-model="dnForm.flete_proveedor" doctype="Supplier" placeholder="Paquetería / transportista…" :readonly="dnValidated" class="mb-3" />
            <label class="field-label">Costo de envío</label>
            <div class="flex items-center border border-surface-border rounded-lg focus-within:ring-2 focus-within:ring-brand-500/30 focus-within:border-brand-400 bg-white mb-1">
              <span class="pl-3 pr-1 text-sm text-ink-light select-none">$</span>
              <input v-model.number="dnForm.flete_costo" type="number" min="0" step="0.01" :disabled="dnValidated" class="flex-1 min-w-0 py-2 pr-3 text-sm focus:outline-none bg-transparent disabled:bg-surface-raised/60" />
            </div>
            <p v-if="!dnValidated" class="text-[11px] text-ink-light mb-3">Al validar se registra como póliza contable (cargo a Transporte y Fletes, contra la cuenta por pagar del proveedor).</p>
            <p v-else-if="dnDoc.flete_journal_entry" class="text-[11px] text-ink-light mb-3">Póliza: <a :href="`/app/journal-entry/${dnDoc.flete_journal_entry}`" target="_blank" class="text-brand-600 hover:underline">{{ dnDoc.flete_journal_entry }}</a></p>
            <p v-else class="mb-3"></p>

            <table class="w-full text-sm mb-3">
              <thead><tr class="text-left text-xs font-semibold text-ink-light border-b border-surface-border"><th class="py-2">Producto</th><th class="py-2 w-20 text-right">Cant.</th><th class="py-2">Almacén</th><th class="py-2 w-20 text-right">Disponible</th></tr></thead>
              <tbody>
                <tr v-for="it in dnDoc.items" :key="it.name" class="border-b border-surface-border/60">
                  <td class="py-1.5 pr-2">{{ it.item_name || it.item_code }}</td>
                  <td class="py-1.5 pr-2"><input v-model.number="it.qty" type="number" min="0" class="field-input text-right" :disabled="dnValidated" /></td>
                  <td class="py-1.5 pr-2"><select v-model="it.warehouse" class="field-input" :disabled="dnValidated"><option value="">— Selecciona —</option><option v-for="w in (dnDoc.warehouses || [])" :key="w.name" :value="w.name">{{ w.warehouse_name || w.name }}</option></select></td>
                  <td class="py-1.5 pr-2 text-right" :class="(it.available ?? 0) < it.qty ? 'text-red-600 font-semibold' : 'text-ink-muted'">{{ it.available ?? '—' }}</td>
                </tr>
              </tbody>
            </table>
            <p v-if="dnDoc.items.some(it => (it.available ?? 0) < it.qty)" class="text-[12px] text-red-600 mb-3 flex items-start gap-1.5"><svg class="w-4 h-4 flex-shrink-0 mt-px" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M5.07 19h13.86a2 2 0 001.71-3l-6.93-12a2 2 0 00-3.42 0l-6.93 12a2 2 0 001.71 3z"/></svg>No hay stock suficiente en el almacén elegido para esa cantidad.</p>

            <div class="space-y-2">
              <template v-if="!dnValidated">
                <button :disabled="advancing" class="w-full h-9 text-sm font-medium text-ink border border-surface-border rounded-lg hover:bg-surface-raised disabled:opacity-50" @click="guardarRemision">Guardar cambios</button>
                <button :disabled="advancing" class="w-full h-9 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center justify-center gap-1.5" @click="validarRemision">
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                  Validar remisión
                </button>
              </template>
              <div class="grid grid-cols-2 gap-2 pt-1">
                <button class="doc-action justify-center" @click="openSend('Delivery Note', dnDoc.name, dnDoc.contact_email || activeSO?.contact_email, dnDoc.contact_mobile || activeSO?.contact_mobile)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>Enviar</button>
                <button class="doc-action justify-center" @click="downloadPdf('Delivery Note', dnDoc.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/></svg>Descargar</button>
                <button class="doc-action justify-center" @click="printDocView('Delivery Note', dnDoc.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2z"/></svg>Imprimir</button>
                <button class="doc-action justify-center" @click="openAssign('Delivery Note', dnDoc.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>Asignar</button>
              </div>
              <a class="doc-action justify-center w-full" :href="`/app/delivery-note/${dnDoc.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>Abrir en ERPNext</a>
            </div>
            </div>
          </template>
        </div>

        <!-- Derecha: vista previa del PDF -->
        <div class="flex-1 min-w-0 bg-white rounded-xl border border-surface-border overflow-hidden">
          <div v-if="!dnDoc" class="flex flex-col items-center justify-center gap-2 text-ink-light" style="height: 78vh;">
            <svg class="w-10 h-10 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.2"><path stroke-linecap="round" stroke-linejoin="round" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0l-2 5H6l-2-5m16 0H4m5 5v.01M15 18v.01"/></svg>
            <p class="text-[13px]">La vista previa aparecerá al crear la remisión</p>
          </div>
          <div v-else>
            <div class="flex items-center justify-end px-2 py-1.5 border-b border-surface-border">
              <button class="doc-action" @click="openPdf('Delivery Note', dnDoc.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 8V4m0 0h4M4 4l5 5m11-5h-4m4 0v4m0-4l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5h-4m4 0v-4m0 4l-5-5"/></svg>Ampliar</button>
            </div>
            <div style="height: 78vh; overflow: auto;">
              <iframe :key="previewKey" :src="printUrl('Delivery Note', dnDoc.name)" style="width: 143%; height: 143%; transform: scale(0.7); transform-origin: top left; border: 0;" title="Vista previa de la remisión"></iframe>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ══════════ STEP 7 · FACTURAR ══════════ -->
    <div v-else-if="activeStep === 7" class="p-5 pb-20">
      <!-- Tabs: Venta (cliente) | Compras (proveedores) -->
      <div class="max-w-6xl mx-auto mb-4">
        <ActiveSOSelector :sales-orders="related.sales_orders" :active-name="activeSOName" @update:active-name="setActiveSO" class="mb-3" />
        <div class="flex items-center gap-1.5 bg-green-50 text-green-700 text-[12px] font-medium px-3 py-2 rounded-lg mb-3 w-max"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>{{ related.delivery_notes.length > 1 ? `${related.delivery_notes.length} remisiones validadas` : `Remisión ${related.delivery_notes[0]?.name} validada` }} · mercancía entregada</div>
        <div class="flex items-center gap-1 bg-gray-100 rounded-lg p-0.5 w-max">
          <button class="px-3.5 py-1.5 rounded-md text-[13px] font-medium transition-colors" :class="factTab === 'venta' ? 'bg-white text-ink shadow-sm' : 'text-ink-muted hover:text-ink'" @click="factTab = 'venta'">Venta (cliente)</button>
          <button class="px-3.5 py-1.5 rounded-md text-[13px] font-medium transition-colors" :class="factTab === 'compras' ? 'bg-white text-ink shadow-sm' : 'text-ink-muted hover:text-ink'" @click="selectComprasTab">Compras (proveedores)</button>
        </div>
      </div>

      <!-- ── VENTA ── -->
      <div v-show="factTab === 'venta'" class="flex gap-5 items-start max-w-6xl mx-auto">

        <!-- Izquierda: datos de la factura -->
        <div class="w-80 flex-shrink-0 bg-white rounded-xl border border-surface-border p-5" :id="related.sales_invoice ? `doc-hl-${related.sales_invoice.name}` : null" :class="{ 'doc-highlight-flash': related.sales_invoice && highlightTarget === related.sales_invoice.name }">
          <div class="flex items-center justify-between mb-1">
            <p class="text-sm font-semibold text-ink">Factura de venta</p>
            <span v-if="related.sales_invoice" class="text-[11px] font-semibold px-2 py-0.5 rounded-full" :class="siValidated ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'">{{ siValidated ? 'Validada' : 'Borrador' }}</span>
          </div>
          <p class="text-[12px] text-ink-muted mb-4">Se genera desde la orden de venta. Productos y totales son automáticos.</p>

          <label class="field-label">Fecha de factura</label>
          <input v-model="siForm.posting_date" type="date" class="field-input mb-3" :disabled="siValidated" />

          <label class="field-label">Vencimiento</label>
          <input v-model="siForm.due_date" type="date" class="field-input mb-3" :disabled="siValidated" />

          <label class="field-label">Condiciones de pago</label>
          <select v-model="siForm.payment_terms_template" class="field-input mb-3" :disabled="siValidated">
            <option value="">— Sin plantilla —</option>
            <option v-for="p in cotDefaults.payment_terms_templates" :key="p.name" :value="p.name">{{ p.name }}</option>
          </select>

          <label class="field-label">Términos y condiciones</label>
          <select v-model="siForm.tc_name" class="field-input mb-4" :disabled="siValidated">
            <option value="">— Sin términos —</option>
            <option v-for="t in cotDefaults.terms" :key="t.name" :value="t.name">{{ t.name }}</option>
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
            <template v-if="!siValidated">
              <button :disabled="advancing" class="w-full h-9 text-sm font-medium text-ink border border-surface-border rounded-lg hover:bg-surface-raised disabled:opacity-50" @click="guardarFactura">Guardar cambios</button>
              <button :disabled="advancing" class="w-full h-9 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center justify-center gap-1.5" @click="validarFactura">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Validar factura
              </button>
            </template>
            <div class="grid grid-cols-2 gap-2 pt-1">
              <button class="doc-action justify-center" @click="openSend('Sales Invoice', related.sales_invoice.name, related.sales_invoice.contact_email, related.sales_invoice.contact_mobile)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>Enviar</button>
              <button class="doc-action justify-center" @click="downloadPdf('Sales Invoice', related.sales_invoice.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/></svg>Descargar</button>
              <button class="doc-action justify-center" @click="printDocView('Sales Invoice', related.sales_invoice.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2z"/></svg>Imprimir</button>
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
              <button class="doc-action" @click="openPdf('Sales Invoice', related.sales_invoice.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 8V4m0 0h4M4 4l5 5m11-5h-4m4 0v4m0-4l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5h-4m4 0v-4m0 4l-5-5"/></svg>Ampliar</button>
            </div>
            <div style="height: 78vh; overflow: auto;">
              <iframe :key="previewKey" :src="printUrl('Sales Invoice', related.sales_invoice.name)" style="width: 143%; height: 143%; transform: scale(0.7); transform-origin: top left; border: 0;" title="Vista previa de la factura de venta"></iframe>
            </div>
          </div>
        </div>
      </div>

      <!-- ── COMPRAS (cuentas por pagar) ── -->
      <div v-show="factTab === 'compras'" class="flex gap-5 items-start max-w-6xl mx-auto">
        <!-- Izquierda: fuentes facturables -->
        <div class="w-72 flex-shrink-0 space-y-3">
          <div class="bg-white rounded-xl border border-surface-border p-4">
            <p class="section-title mb-2">Materiales (materia prima)</p>
            <p v-if="!compras.materiales.length" class="prod-empty">Sin recibos de compra.</p>
            <button v-for="m in compras.materiales" :key="m.name" class="w-full text-left p-2.5 rounded-lg border mb-1.5 transition-colors" :class="pinvSel && pinvSel.source_name === m.name ? 'border-brand-400 bg-brand-50' : 'border-surface-border hover:bg-surface-raised'" @click="selectCompra('Purchase Receipt', m)">
              <div class="flex items-center justify-between gap-2">
                <span class="text-[13px] font-medium text-ink truncate">{{ m.supplier_name || m.supplier }}</span>
                <span class="text-[10px] font-semibold px-2 py-0.5 rounded-full shrink-0" :class="facBadge(m.invoice).cls">{{ facBadge(m.invoice).txt }}</span>
              </div>
              <p class="text-[12px] text-ink-muted mt-0.5">{{ fmtC(m.base_net_total) }}</p>
            </button>
          </div>
          <div class="bg-white rounded-xl border border-surface-border p-4">
            <p class="section-title mb-2">Maquila (talleres)</p>
            <p v-if="!compras.maquila.length" class="prod-empty">Sin órdenes de subcontratación.</p>
            <button v-for="m in compras.maquila" :key="m.name" class="w-full text-left p-2.5 rounded-lg border mb-1.5 transition-colors" :class="pinvSel && pinvSel.source_name === m.name ? 'border-brand-400 bg-brand-50' : 'border-surface-border hover:bg-surface-raised'" @click="selectCompra('Purchase Order', m)">
              <div class="flex items-center justify-between gap-2">
                <span class="text-[13px] font-medium text-ink truncate">{{ m.supplier_name || m.supplier }}</span>
                <span class="text-[10px] font-semibold px-2 py-0.5 rounded-full shrink-0" :class="facBadge(m.invoice).cls">{{ facBadge(m.invoice).txt }}</span>
              </div>
              <p class="text-[12px] text-ink-muted mt-0.5">{{ fmtC(m.base_net_total) }}</p>
            </button>
          </div>
        </div>

        <!-- Derecha: detalle de la factura de compra -->
        <div class="flex-1 min-w-0">
          <div v-if="!pinvSel" class="bg-white rounded-xl border border-surface-border flex flex-col items-center justify-center gap-2 text-ink-light" style="height: 60vh;">
            <svg class="w-10 h-10 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 14l2 2 4-4m4 9V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2z"/></svg>
            <p class="text-[13px]">Selecciona una compra para facturar</p>
          </div>
          <div v-else-if="!pinvDoc" class="bg-white rounded-xl border border-surface-border p-8 text-center">
            <p class="text-sm font-medium text-ink">{{ pinvSel.supplier_name }}</p>
            <p class="text-[13px] text-ink-muted mt-1 mb-4">Aún no tiene factura de compra registrada.</p>
            <button :disabled="advancing" class="px-4 py-2 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50" @click="generarFacturaCompra">Registrar factura de compra</button>
          </div>
          <div v-else class="flex gap-5 items-start">
            <div class="w-72 flex-shrink-0 bg-white rounded-xl border border-surface-border p-4" :id="`doc-hl-${pinvDoc.name}`" :class="{ 'doc-highlight-flash': highlightTarget === pinvDoc.name }">
              <div class="flex items-center justify-between mb-3">
                <span class="text-sm font-semibold text-ink truncate">{{ pinvDoc.name }}</span>
                <span class="text-[11px] font-semibold px-2 py-0.5 rounded-full" :class="pinvValidated ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'">{{ pinvValidated ? 'Validada' : 'Borrador' }}</span>
              </div>
              <div><label class="field-label">Proveedor</label><div class="field-input bg-surface-raised/60 truncate mb-3">{{ pinvDoc.supplier_name || pinvDoc.supplier }}</div></div>
              <label class="field-label">Folio del proveedor (factura)</label>
              <input v-model="pinvForm.bill_no" :disabled="pinvValidated" class="field-input mb-3" placeholder="Nº de factura del proveedor" />
              <label class="field-label">Fecha de factura</label>
              <input v-model="pinvForm.posting_date" type="date" :disabled="pinvValidated" class="field-input mb-3" />
              <label class="field-label">Vencimiento</label>
              <input v-model="pinvForm.due_date" type="date" :disabled="pinvValidated" class="field-input mb-3" />
              <label class="field-label">Condiciones de pago</label>
              <select v-model="pinvForm.payment_terms_template" :disabled="pinvValidated" class="field-input mb-4"><option value="">— Sin plantilla —</option><option v-for="p in cotDefaults.payment_terms_templates" :key="p.name" :value="p.name">{{ p.name }}</option></select>
              <div class="border-t border-surface-border pt-3 mb-4 flex justify-between text-[13px]"><span class="text-ink-muted">Total (neto)</span><span class="font-medium">{{ fmtC(pinvDoc.base_net_total) }}</span></div>
              <div class="space-y-2">
                <template v-if="!pinvValidated">
                  <button :disabled="advancing" class="w-full h-9 text-sm font-medium text-ink border border-surface-border rounded-lg hover:bg-surface-raised disabled:opacity-50" @click="guardarPinv">Guardar cambios</button>
                  <button :disabled="advancing" class="w-full h-9 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center justify-center gap-1.5" @click="validarPinv"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Validar factura</button>
                </template>
                <div class="grid grid-cols-3 gap-2 pt-1">
                  <button class="doc-action justify-center" @click="downloadPdf('Purchase Invoice', pinvDoc.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/></svg>Descargar</button>
                  <button class="doc-action justify-center" @click="printDocView('Purchase Invoice', pinvDoc.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2z"/></svg>Imprimir</button>
                  <button class="doc-action justify-center" @click="openPdf('Purchase Invoice', pinvDoc.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 8V4m0 0h4M4 4l5 5m11-5h-4m4 0v4m0-4l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5h-4m4 0v-4m0 4l-5-5"/></svg>Ampliar</button>
                </div>
                <a class="doc-action justify-center w-full" :href="`/app/purchase-invoice/${pinvDoc.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>Abrir en ERPNext</a>
              </div>
              <div class="pt-3 mt-2 border-t border-surface-border">
                <AttachmentsPanel doctype="Purchase Invoice" :docname="pinvDoc.name" />
              </div>
            </div>
            <div class="flex-1 min-w-0 bg-white rounded-xl border border-surface-border overflow-hidden" style="height: 78vh; overflow: auto;">
              <iframe :key="'pinv' + previewKey" :src="printUrl('Purchase Invoice', pinvDoc.name)" style="width: 143%; height: 143%; transform: scale(0.7); transform-origin: top left; border: 0;" title="Vista previa de la factura de compra"></iframe>
            </div>
          </div>
        </div>
      </div>

    </div>

    <div v-else-if="activeStep === 8" class="p-5 pb-20">
      <div class="max-w-5xl mx-auto mb-4">
        <ActiveSOSelector :sales-orders="related.sales_orders" :active-name="activeSOName" @update:active-name="setActiveSO" />
      </div>
      <ReporteFinalPanel :r="reporte" :loading="reporteLoading" />
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

    <!-- Crear revisión modal -->
    <div v-if="showRevisionModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="showRevisionModal = false">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm p-5">
        <p class="text-sm font-semibold text-ink mb-2">Crear revisión</p>
        <p class="text-[12.5px] text-ink-muted mb-4">Se creará una nueva revisión de {{ docName }} para poder editarla. Este costeo queda guardado como historial.</p>
        <label class="field-label">Motivo de la revisión (opcional)</label>
        <textarea v-model="revisionMotivo" rows="3" class="field-input mb-4" placeholder="Ej: cliente pidió ajustar el precio…"></textarea>
        <div class="flex justify-end gap-2">
          <button class="px-3 py-1.5 text-[13px] text-ink-muted hover:bg-surface-raised rounded-lg" @click="showRevisionModal = false">Cancelar</button>
          <button :disabled="revisionCreating" class="px-4 py-1.5 text-[13px] font-medium text-white bg-brand-500 hover:bg-brand-600 disabled:opacity-50 rounded-lg" @click="confirmarRevision">
            {{ revisionCreating ? "Creando…" : "Crear revisión" }}
          </button>
        </div>
      </div>
    </div>

    <!-- Rechazar cotización modal -->
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
      <div v-if="toast.show" class="fixed bottom-5 right-5 z-50 px-4 py-3 rounded-lg text-sm font-medium shadow-lg" :class="toast.type === 'error' ? 'bg-red-600 text-white' : 'bg-green-600 text-white'">{{ toast.msg }}</div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from "vue";
import { useRoute, useRouter } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import CosteoStepper from "@/components/CosteoStepper.vue";
import LinkInput from "@/components/LinkInput.vue";
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
import OrdenManufacturaForm from "@/components/OrdenManufacturaForm.vue";
import ActiveSOSelector from "@/components/ActiveSOSelector.vue";
import { db, call, openDesk as deskOpen, uploadFile, searchLink, fuzzyQuery, getLinkDisplayLabel } from "@/utils/frappe.js";
import { useToast } from "@/composables/useToast.js";
import { useDocumentActions } from "@/composables/useDocumentActions.js";
import { useCompany } from "@/composables/useCompany.js";

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
function statusToStep(status, hasPlanAlready, etapasCount = 0, pendientesCount = 0) {
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
  //   - hay artículos de texto libre sin resolver -> todavía falta Alta de
  //     Productos, aunque ya haya etapas capturadas (pudo dejarlas a medias).
  //   - no hay pendientes pero ya hay etapas capturadas -> Alta de Productos ya
  //     está resuelto, lo que sigue es Flujo de Producción.
  //   - nada de lo anterior (recién validada, nada capturado) -> se queda en
  //     Vender, como antes.
  if (statusIdx === 2) {
    if (hasPlanAlready) target = 4;
    else if (pendientesCount > 0) target = 3;
    else if (etapasCount > 0) target = 4;
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
    nuevaOvGate.show = res.puede_generar || res.vencido;
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
const tplModal = reactive({ open: false, saving: false });
// Tallas "Pendiente por cliente" en TODO el costeo (no solo el producto abierto)
// -- para el badge del kebab y el modal de "Actualizar cantidades por talla".
const tallasPendientes = computed(() => tallas.value.filter(esTallaPendiente));
const actualizarTallasModal = reactive({ open: false, saving: false, error: "", filas: [] });
function openActualizarTallasModal() {
  actionsOpen.value = false;
  actualizarTallasModal.error = "";
  actualizarTallasModal.filas = tallasPendientes.value.map(t => ({
    talla_row: t.name, finished_item: t.finished_item, label: tallaEtiqueta(t), qtyNueva: 0,
  }));
  actualizarTallasModal.open = true;
}
function tallaEtiqueta(t) {
  const codes = tallasSeleccionadasDe(t);
  const labels = codes.map(c => allTallas.value.find(x => x.name === c)?.talla || c);
  return [t.genero, labels.join("/")].filter(Boolean).join(" ") || "(sin talla capturada)";
}
async function confirmarActualizarTallas() {
  const filas = actualizarTallasModal.filas.filter(f => (f.qtyNueva || 0) > 0);
  if (!filas.length) { actualizarTallasModal.error = "Captura al menos una cantidad."; return; }
  actualizarTallasModal.saving = true;
  actualizarTallasModal.error = "";
  try {
    let sincronizados = 0;
    for (const f of filas) {
      const r = await call("costeo_yelke.api.costeo_api.actualizar_talla_cantidad", {
        costeo: docName.value, talla_row: f.talla_row, qty: f.qtyNueva, estado_cantidad: "Definida",
      });
      sincronizados += (r.actualizados || []).length;
    }
    await fillFromDoc(await db.get("Costeo", docName.value));
    actualizarTallasModal.open = false;
    showToast(sincronizados ? `Cantidades confirmadas · ${sincronizados} documento(s) actualizado(s)` : "Cantidades confirmadas");
  } catch (e) {
    actualizarTallasModal.error = e.message || "No se pudieron actualizar las cantidades";
  } finally {
    actualizarTallasModal.saving = false;
  }
}
const productosConNombre = computed(() => productos.value.filter(p => p.finished_item).map(p => p.finished_item));
const materializeModal = reactive({ open: false, saving: false, text: "", suggestedPrice: 0, suggestedDescription: "", suggestedImage: "" });
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

async function triggerHighlight(name, doctype) {
  if (doctype === "Purchase Order" || !doctype) {
    // Sin doctype explícito (o "Purchase Order"): puede ser una OC de materia prima de
    // un lote, la OC (compartida) de una parada de subcontratación, o -- documentos
    // viejos que ya no viven en ningún lote -- alguna de las listas planas de respaldo.
    const matMatch = resolverLoteYGrupoMaterial(name);
    const subMatch = !matMatch ? resolverLoteYParadaPo(name) : null;
    if (matMatch) {
      activeStep.value = 5;
      loteActivoRef.value = matMatch.lote.lote_ref;
      await nextTick();
      await toggleLoteDoc(matMatch.lote, matMatch.grp, "oc");
    } else if (subMatch) {
      activeStep.value = 5;
      loteActivoRef.value = subMatch.lote.lote_ref;
      await seleccionarParada(subMatch.parada);
      subStepOpen.value = "oc";
    } else if (mpLotes.value.some((o) => o.name === name)) {
      await selectOcLote(name);
    } else if (subOcs.value.some((o) => o.name === name)) {
      await selectSub(name);
    }
  } else if (doctype === "Purchase Receipt") {
    // El recibo vive DENTRO de la tarjeta de su OC (del lote y proveedor exactos) --
    // hay que abrir ese lote/proveedor primero para que el panel del recibo se monte.
    const matMatch = resolverLoteYGrupoMaterial(name, { porRecibo: true });
    if (matMatch) {
      activeStep.value = 5;
      loteActivoRef.value = matMatch.lote.lote_ref;
      await nextTick();
      await toggleLoteDoc(matMatch.lote, matMatch.grp, "recibo");
    } else {
      const oc = mpLotes.value.find((o) => (o.receipts || []).includes(name));
      if (oc) await selectOcLote(oc.name);
    }
  } else if (doctype === "Material Request") {
    // La solicitud vive en la vista general de "Producir" (no dentro de ningún lote
    // específico -- un mismo MR se reparte entre todos los lotes del producto).
    loteActivoRef.value = "";
  } else if (doctype === "Delivery Note") {
    await selectDn(name);
  } else if (doctype === "Purchase Invoice") {
    factTab.value = "compras";
    await selectComprasTab();
    const row = [...compras.materiales, ...compras.maquila].find((m) => m.invoice && m.invoice.name === name);
    if (row) await selectCompra(row.source_doctype, row);
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
const related = reactive({ quotation: null, quotations: [], sales_order: null, sales_orders: [], delivery_notes: [], delivery_per_delivered: 0, sales_invoice: null });
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
// nuevo"...) -- se muestran como acordeón (mismo patrón que "Productos a costear",
// expandedTid): solo una expandida a la vez, y expandirla carga sus datos en
// cotForm/cotItems para reusar exactamente el mismo panel de edición de antes.
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
const soForm = reactive({
  delivery_date: "", delivery_weeks: null, payment_terms_template: "", tc_name: "", po_no: "",
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
}
// "OV activa": la que filtra Producir/Enviar/Facturar/Reportar -- por default sigue a
// la expandida en Vender, pero se puede fijar aparte (selector en esos pasos) sin
// perder cuál está expandida en el acordeón de Vender.
const activeSOName = ref(null);
watch(expandedSOName, (name) => { if (name) activeSOName.value = name; });
const siForm = reactive({ posting_date: "", due_date: "", payment_terms_template: "", tc_name: "" });
const dnDoc = ref(null);
const dnSel = ref("");
const dnForm = reactive({ posting_date: "", shipping_address_name: "", customer_address: "", flete_proveedor: "", flete_costo: 0 });
const factTab = ref("venta");
const reporte = ref(null);
const reporteLoading = ref(false);
const compras = reactive({ materiales: [], maquila: [] });
const pinvSel = ref(null);
const pinvDoc = ref(null);
const pinvForm = reactive({ posting_date: "", due_date: "", bill_no: "", bill_date: "", payment_terms_template: "", tc_name: "" });
const cotDefaults = reactive({ payment_terms_templates: [], terms: [], users: [], price_lists: [], currencies: [], tax_templates: [] });
const prepSteps = ref([]);

const form = reactive({ titulo: "", cliente: "", fecha: today(), compania: "", proyecto: "", guardar_como_plantilla: true, centro_de_costos: "", almacen_materias_primas: "", almacen_trabajo_en_proceso: "" });
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
async function loadPuedeValidarCosteo() {
  try { puedeValidarCosteo.value = !!(await call("costeo_yelke.api.costeo_api.puede_validar_costeo")).puede; }
  catch { /* si falla, se deja en true -- el backend igual bloquea si no toca */ }
}
const draftBanner = reactive({ show: false, savedAt: null });
const pendingDraft = ref(null);
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
const expandedTid = ref(null);
const { toast, showToast } = useToast();
const {
  printFmtMap, previewKey,
  pdfModal, sendChooser, waModal, sendModal, assignModal,
  ensurePrintFmt, printUrl, printDocView, downloadPdf,
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
  loadSolicitud, crearSolicitud, guardarSolicitud, validarSolicitud,
  selectOC, selectOcLote, selectRfq, selectSq, guardarDocCompra, validarDocCompra, revisarDocCompra, jalarPreciosOC, crearOc,
  permisosValidacion, loadPermisosValidacion,
  reciboPr, reciboItems, reciboForm,
  selectReciboLote, guardarRecibo, validarRecibo,
  subOcs, subPo, subItems, subForm, subValidated,
  loadSubcontratos, crearSubcontratos, selectSub, guardarSub, validarSub, revisarSub,
  flujo, scoSel, scoValidated, scoForm, scoCostos,
  guardarSco, validarSco, addCosto, removeCosto,
  transDoc, transForm, transCostos, transValidated, transferDone, transferirMaterial, guardarTrans, validarTransferencia, enviarMaterialTaller,
  addCostoTrans, removeCostoTrans,
  scr, scrForm, scrCostos, scrValidated, crearReciboSub, guardarScr, validarScr,
  addCostoScr, removeCostoScr,
  lotesProduccion, productosCosteo, loteActivoRef, loteParadaActiva, nuevoLoteForm,
  loteActivo, paradaActiva, tracksLote, paradaEstado,
  loadLotesProduccion, seleccionarLote, seleccionarParada, verParadaPo,
  abrirNuevoLote, cerrarNuevoLote, crearNuevoLote, abrirParada, siguienteParadaPendiente, generarOcLote,
  tallasSinLoteDe, onTallaLoteSelect,
  primeraEtapaQty, primeraEtapaLoading, primeraEtapaLimitado, sugerirPrimeraEtapaQty,
  crearRfqLote, crearSqLote,
  omGeneral, omCab, omDama, omProc, omTablas, omArchivos, omUploading, omEsMaestra,
  addProceso, removeProceso, addTabla, removeTabla, addColumna, removeColumna, addFila, removeFila,
  medidasTemplates, addTablaPlantilla,
  tallaTotal, onOmFile, removeArchivo,
  prodComplete, loadProdComplete, materiaPrimaPct, subcontratacionPct, mpLotes,
} = useProduccion({ showToast, advancing, ensurePrintFmt, previewKey });
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
// Verde cuando el documento de ese botón ya está validado (para ubicarse rápido en
// qué proveedor sigue pendiente); si no, el color de "abierto" (acordeón desplegado).
function loteDocBtnClass(open, validated) {
  if (validated) return "border-green-500 text-green-700 bg-green-50";
  if (open) return "border-brand-500 text-brand-700 bg-brand-50";
  return "";
}
// Tarjeta de parada (taller) en el flujo del lote: verde si ya recibió; resaltada
// si es la que se está viendo; gris si aún no.
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
function rfqDeProveedor(lote, supplier) { return (lote.material_rfqs || []).find((r) => r.supplier === supplier); }
function sqDeProveedor(lote, supplier) { return (lote.material_sqs || []).find((r) => r.supplier === supplier); }
// Acordeón: qué proveedor+documento está desplegado en la pantalla del lote (uno a
// la vez) -- clic en un botón lo abre (creando el documento si aún no existe) o lo
// cierra si ya estaba abierto.
const loteDocOpen = reactive({ supplier: null, tab: null });
async function toggleLoteDoc(lote, grp, tab) {
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
    else await crearRfqLote(lote, grp.supplier);
  } else if (tab === "sq") {
    const existing = sqDeProveedor(lote, grp.supplier);
    if (existing) await selectSq(existing.name);
    else await crearSqLote(lote, grp.supplier);
  } else if (tab === "oc") {
    if (grp.po) { mrDocTab.value = "oc"; await selectOC(grp.po.name); }
    else await generarOcLote(lote, grp.supplier);
  } else if (tab === "recibo") {
    if (grp.po?.docstatus === 1) await selectReciboLote(grp.po);
  }
}

// Subcontratación de la etapa activa: mismo patrón de 4 botones desplegables que
// materia prima, pero con el flujo real de subcontratación -- Orden de compra (la OC
// validada con el taller) / Orden de subcontratación (SCO, por lote) / Transferencia
// de material / Recibo de subcontratación. Sólo se puede tener uno abierto a la vez;
// el que corresponde según lo ya avanzado se abre solo al cambiar de etapa.
const subStepOpen = ref("oc");
function subStepDefaultFor(parada) {
  if (!parada || parada.po_docstatus !== 1) return "oc";
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
function openSubStepSco() {
  subStepOpen.value = "sco";
  maybeSugerirPrimeraEtapaQty();
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
  await loadLotesProduccion();
  const p2 = loteActivo.value?.paradas.find((x) => x.parada_id === loteParadaActiva.value);
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
  if (step === 6 && related.sales_invoice) return { doctype: "Sales Invoice", name: related.sales_invoice.name, docstatus: related.sales_invoice.docstatus, isCosteo: false };
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
const cta = computed(() => {
  if (docStatus.value === "Orden de Venta" && (activeStep.value === 3 || activeStep.value === 4)) {
    return { label: "Pasar a producción", action: "pasar_produccion" };
  }
  return ({
    "Borrador":       { label: "Pasar a cotización",        action: "cotizar" },
    "Cotizado":       { label: "Generar orden de venta",    action: "vender" },
    "Orden de Venta": { label: "Preparar manufactura",      action: "ir_preparar_manufactura" },
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
  if (docStatus.value === "Cotizado") return related.quotation?.docstatus === 1; // cotización validada
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
  if (action === "ir_preparar_manufactura") return true;
  if (action === "enviar") return (prodComplete.lotes_recibidos || 0) > 0;
  // En "Flujo de Producción" (paso 4) el botón "Confirmar" se persiste solo -- no
  // exige un guardado previo. En "Alta de Productos" (paso 3) sí, porque el flujo
  // todavía no se ha revisado.
  if (action === "pasar_produccion") return activeStep.value === 4 || manufacturaGuardada.value;
  return canAdvance.value;
});
const quotValidated = computed(() => related.quotation?.docstatus === 1);
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
  await Promise.all([
    loadPlan(docName.value, name),
    loadProdComplete(docName.value, name),
  ]);
  if (activeStep.value === 8) await loadReporte();
});
function setActiveSO(name) { activeSOName.value = name; }
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
function fmtC(v) { return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(v || 0); }
function goStep(idx) {
  activeStep.value = idx;
  loteActivoRef.value = "";
  if (idx === 8) loadReporte();
  if (idx === 4) loadFlujoOps();
}
async function goLote(lote_ref) {
  activeStep.value = 5;
  await seleccionarLote(lote_ref);
}
// El "+" del riel de lotes en el stepper lleva a Producir (donde vive el
// formulario de "Nuevo lote") y lo abre directo -- no hace falta entrar primero.
async function onCrearLoteDesdeStepper() {
  activeStep.value = 5;
  loteActivoRef.value = "";
  await abrirNuevoLote();
}
// Un lote es del COSTEO: cubre varios productos. En el stepper aparece UNA vez por
// lote_ref -- el desglose por taller/producto se ve al abrirlo. "done" lo calcula
// el backend (get_lotes_produccion: todas las paradas recibidas + material recibido).
const lotesParaStepper = computed(() =>
  lotesProduccion.value.map((l) => ({ lote_ref: l.lote_ref, label: l.lote_ref, done: !!l.done }))
);

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
function addProducto() { const p = { _tid: uid(), _lastFinishedItem: "", image: "", description: "", finished_item: "", qty: 1, shipping_cost: 0, labeling_cost: 0, packaging_cost: 0, overhead_pct: 0, margin_pct: 0, material_cost: 0, services_cost: 0, overhead_amt: 0, total_unit_cost: 0, unit_sales_price: 0, precio_manual: 0, total_sales_price: 0 }; productos.value.push(p); expandedTid.value = p._tid; }
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
function removeProducto(idx) { const prod = productos.value[idx]; if (!prod) return; const stageIdsDeProd = new Set(etapas.value.filter(e => e.producto_terminado === prod.finished_item).map(e => e.stage_id)); const materialIdsDeProd = new Set(detalles.value.filter(d => d.finished_item === prod.finished_item).map(d => d.material_id)); detalles.value = detalles.value.filter(d => d.finished_item !== prod.finished_item); etapas.value = etapas.value.filter(e => e.producto_terminado !== prod.finished_item); materialesEtapa.value = materialesEtapa.value.filter(r => !materialIdsDeProd.has(r.material_id) && !stageIdsDeProd.has(r.stage_id)); tallas.value = tallas.value.filter(t => t.finished_item !== prod.finished_item); productos.value.splice(idx, 1); if (expandedTid.value === prod._tid) expandedTid.value = null; }
function toggleProduct(tid) { expandedTid.value = expandedTid.value === tid ? null : tid; }
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
// La imagen se sube desde aquí (aunque el producto todavía sea texto libre) para que
// ya esté lista cuando se materialice el Item real al pasar a cotización.
function pickImage(prod) {
  if (!canEditCosteo.value) return;
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "image/*";
  input.onchange = async (ev) => {
    const f = ev.target.files?.[0];
    if (!f) return;
    try {
      const res = await uploadFile(f, docName.value ? { doctype: "Costeo", docname: docName.value } : {});
      if (res?.file_url) prod.image = res.file_url;
    } catch (e) { showToast(e.message || "No se pudo subir la imagen", "error"); }
  };
  input.click();
}
function addDetalle(prod, type) { detalles.value.push({ _tid: uid(), material_id: genStageId(), finished_item: prod.finished_item, concept_type: type, item: "", supplier: "", tipo_material: "", internal_uom: "", rendimiento: 0, internal_qty: 0, supplier_qty: 0, unit_price: 0, total: 0, etapa: "", _supplierOptions: [], _qtyMode: "rendimiento" }); }
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
function esUdmPorPiezas(d) { return d.internal_uom in PIEZAS_POR_UDM; }
function piezasPorUdm(d) { return PIEZAS_POR_UDM[d.internal_uom] || 0; }
// La UDM ya dice qué modo corresponde -- no hace falta guardar el modo aparte ni un
// campo nuevo en el backend: se deriva de internal_uom (que sí se guarda), así que al
// recargar el costeo queda seleccionada la misma pestaña sola. Kilogramo -> rendimiento
// ("1 kilo rinde X piezas"), Metro -> consumo ("cada pieza usa X metros"), Mazo/Gruesa
// -> piezas (cuántas piezas de la prenda salen de ahí). Solo cuando la UDM no cae en
// ninguna de esas reglas (ej. Avío por Pieza, o aún sin UDM) queda libre para elegir
// entre rendimiento/consumo, y ahí sí se respeta lo último que el usuario clickeó.
const QTY_MODE_LABEL = { rendimiento: "Rendimiento", consumo: "Consumo", piezas: "Piezas" };
function qtyModeLocked(d) {
  return d.internal_uom === "KGM - Kilogramo" || d.internal_uom === "MTR - Metro" || esUdmPorPiezas(d);
}
function qtyModeFor(d) {
  if (d.internal_uom === "KGM - Kilogramo") return "rendimiento";
  if (d.internal_uom === "MTR - Metro") return "consumo";
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
// Arma un bloque de texto con las tallas atípicas del producto (si las tiene) para
// anexarlo a la descripción al materializar -- así el maquilero/almacén ve de un
// vistazo qué piezas llevan tela/talla especial, sin perder la descripción que ya
// se había escrito a mano.
function buildTallaDescriptionSuffix(prod) {
  const rows = tallasDe(prod.finished_item).filter(t => t.genero && t.talla && (t.qty || 0) > 0);
  if (!rows.length) return "";
  const lines = rows.map(t => `- Talla ${tallaLabel(t.talla)}: ${t.qty} pza(s)`);
  return `\n\nTallas especiales:\n${lines.join("\n")}`;
}
function addTalla(prod) { loadAllTallas(); tallas.value.push({ _tid: uid(), finished_item: prod.finished_item, genero: "", grupo_talla: "", talla: "", estado_cantidad: "Definida", qty: 0, sobrecosto_tipo: "Ninguno", sobrecosto_valor: 0, sobrecosto_material_original: "", sobrecosto_material_alterno: "", lote_ref: "", costo_unitario: 0, precio_venta: 0, costo_total: 0 }); }
function removeTalla(t, prod) { const i = tallas.value.findIndex(x => x._tid === t._tid); if (i !== -1) tallas.value.splice(i, 1); recalcProducto(prod); }
// No se puede repartir entre tallas más piezas de las que se van a producir en total.
function tallaMaxQty(t, prod) {
  const otherQty = tallasDe(prod.finished_item).filter(x => x._tid !== t._tid).reduce((s, x) => s + (x.qty || 0), 0);
  return Math.max(0, (prod.qty || 0) - otherQty);
}
function onTallaQtyInput(t, prod) {
  const max = tallaMaxQty(t, prod);
  if ((t.qty || 0) > max) t.qty = max;
  recalcProducto(prod);
}
// Precio de UNA talla: el sobrecosto (fijo o %) se suma sobre el PRECIO DE VENTA
// plano del producto (el mismo que se ve en la cotización sin tallas), no sobre
// el costo -- una talla extra no cambia el costo de producción registrado, solo
// lo que se le cobra al cliente por esa pieza. costoFlat/pvFlat son el costo y
// precio de venta "sin sobrecosto" (idénticos para todas las tallas de un mismo
// producto), calculados una sola vez en recalcProducto.
function computeTallaCost(t, costoFlat, pvFlat) {
  // "Material": el sobrecosto es la diferencia de precio entre el material
  // original y el alterno -- ya viene calculada en t.sobrecosto_valor (ver
  // onTallaMaterialAlternoChange), así que se suma igual que "Fijo".
  const sobrecosto = (t.sobrecosto_tipo === "Fijo" || t.sobrecosto_tipo === "Material") ? (t.sobrecosto_valor || 0)
    : t.sobrecosto_tipo === "Porcentaje" ? pvFlat * ((t.sobrecosto_valor || 0) / 100)
    : 0;
  t.precio_venta = round2(pvFlat + sobrecosto);
  t.costo_unitario = round2(costoFlat);
  t.costo_total = round2(t.costo_unitario * (t.qty || 0));
}
function recalcTalla(t, prod) { recalcProducto(prod); }
function tallasAsignadas(prod) { return tallasDe(prod.finished_item).reduce((s, t) => s + (t.qty || 0), 0); }
function tallasVentaTotal(prod) { return tallasDe(prod.finished_item).reduce((s, t) => s + (t.precio_venta || 0) * (t.qty || 0), 0); }
// "Pendiente por cliente": todavía no se sabe cuántas piezas de esta talla se
// van a producir -- qty se bloquea en 0 y se avisa en la cotización como línea
// aparte (ver costeo_api._venta_items_para_producto) para que el cliente diga
// cuántas quiere. "Actualizar cantidades por talla" es donde se confirma.
// "Talla" agrupa una o varias tallas del mismo Tipo de prenda que comparten
// cantidad y sobrecosto (ej. "2XL,3XL" con el mismo sobrecosto de material) --
// se guarda como texto separado por coma (ver doctype Costeo Producto Talla).
function tallasSeleccionadasDe(t) { return (t.talla || "").split(",").filter(Boolean); }
function tallaSeleccionada(t, code) { return tallasSeleccionadasDe(t).includes(code); }
// Evita que la misma talla quede asignada en dos filas del mismo producto a la
// vez (se contaría/facturaría dos veces) -- se ve deshabilitada en la otra fila.
function tallaUsadaEnOtraFila(t, prod, code) {
  return tallasDe(prod.finished_item).some(x => x._tid !== t._tid && tallasSeleccionadasDe(x).includes(code));
}
function toggleTallaEnGrupo(t, code, prod) {
  if (tallaUsadaEnOtraFila(t, prod, code)) return;
  const actuales = tallasSeleccionadasDe(t);
  const idx = actuales.indexOf(code);
  if (idx === -1) actuales.push(code); else actuales.splice(idx, 1);
  t.talla = actuales.join(",");
  recalcTalla(t, prod);
}
function esTallaPendiente(t) { return t.estado_cantidad === "Pendiente por cliente"; }
function toggleTallaPendiente(t, prod, checked) {
  t.estado_cantidad = checked ? "Pendiente por cliente" : "Definida";
  if (checked) t.qty = 0;
  recalcTalla(t, prod);
}
// Al elegir cuál material se reemplaza y por cuál artículo (ver sobrecosto_tipo
// "Material"), el sobrecosto se calcula solo: la diferencia de precio de compra
// entre uno y otro -- no se escribe a mano como en Fijo/Porcentaje.
async function onTallaMaterialAlternoChange(t, prod) {
  if (!t.sobrecosto_material_original || !t.sobrecosto_material_alterno) {
    t.sobrecosto_valor = 0;
    recalcTalla(t, prod);
    return;
  }
  try {
    const [original, alterno] = await Promise.all([
      call("costeo_yelke.api.costeo_api.get_item_price", { item_code: t.sobrecosto_material_original, price_list: "Compra estandar" }),
      call("costeo_yelke.api.costeo_api.get_item_price", { item_code: t.sobrecosto_material_alterno, price_list: "Compra estandar" }),
    ]);
    t.sobrecosto_valor = Math.max(0, (alterno?.price || 0) - (original?.price || 0));
  } catch { /* ignore */ }
  recalcTalla(t, prod);
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
// Cuando el producto tiene desglose por talla, el costo/precio "por pieza" y los
// totales dejan de ser un solo número plano (costo × cantidad) y pasan a ser el
// promedio ponderado real de la mezcla de tallas (cada una con su propio sobrecosto) --
// así el desglose por talla sí afecta todos los cálculos del costeo, no solo su
// propia tabla. Sin renglones de talla, el cálculo es exactamente el de antes.
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

  const tRows = tallasDe(fi);
  const totalTallaQty = tRows.reduce((s, t) => s + (t.qty || 0), 0);

  if (tRows.length && totalTallaQty > 0) {
    // Si las tallas no cubren toda la cantidad a producir, las piezas restantes
    // (sin talla asignada aún) se valúan al precio/costo plano (sin sobrecosto) para
    // que el promedio ponderado represente SIEMPRE las prod.qty piezas totales, no
    // solo las ya asignadas -- si no, los totales se extrapolaban mal cuando la
    // asignación era parcial.
    const totalQty = prod.qty || 0;
    const remainder = Math.max(0, totalQty - totalTallaQty);
    let sumCosto = 0, sumOverheadQty = 0, sumVenta = 0;
    tRows.forEach(t => {
      computeTallaCost(t, costoFlat, pvFlat);
      sumCosto += t.costo_total;
      sumOverheadQty += overheadFlat * (t.qty || 0);
      sumVenta += t.precio_venta * (t.qty || 0);
    });
    if (remainder > 0) {
      sumCosto += costoFlat * remainder;
      sumOverheadQty += overheadFlat * remainder;
      sumVenta += pvFlat * remainder;
    }
    const divisor = totalQty > 0 ? totalQty : totalTallaQty;
    prod.overhead_amt = round2(sumOverheadQty / divisor);
    prod.total_unit_cost = round2(sumCosto / divisor);
    if (prod.precio_manual) {
      // Precio fijo: no se pisa aunque cambien los costos -- el total sí se
      // recalcula (mismas piezas, precio fijo * qty), el margen queda como
      // dato informativo nada más.
      prod.total_sales_price = round2(prod.unit_sales_price * (prod.qty || 0));
      const priceM = prod.unit_sales_price || 0;
      prod.margin_pct = round2(Math.max(0, priceM > 0 ? ((priceM - prod.total_unit_cost) / priceM) * 100 : 0));
    } else {
      prod.unit_sales_price = round2(sumVenta / divisor);
      prod.total_sales_price = round2(sumVenta);
    }
  } else {
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
  }
}
// Editar el precio unitario → recalcula el margen (sentido inverso, sin sobrescribir el
// precio) y marca precio_manual: mientras esté activo, recalcProducto ya NO deriva el
// precio del margen -- es al revés, el precio manda y el margen es solo informativo.
// Así el precio exacto que se tecleó aquí es el que llega a cotización/documentos
// posteriores, sin que un redondeo del margen (o un cambio en materiales/etapas más
// adelante) lo mueva ni un centavo.
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
  d.unit_price = telaConvertPrecioM.value;
  d.internal_uom = "MTR - Metro";
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
  if (!d.item) { recalcDetalle(d, prod); return; }
  try {
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
      doctype: "Talla", fields: ["name", "talla", "is_group", "parent_talla", "genero"],
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
function onTallaGeneroChange(t) { t.grupo_talla = ""; t.talla = ""; }
function onTallaGrupoChange(t) { t.talla = ""; }
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
    ? true : !!Number(data.guardar_como_plantilla);
  form.centro_de_costos = data.centro_de_costos || ""; form.almacen_materias_primas = data.almacen_materias_primas || ""; form.almacen_trabajo_en_proceso = data.almacen_trabajo_en_proceso || "";
  productos.value = (data.costeo_producto || []).map(r => ({ _tid: uid(), image: "", description: "", precio_manual: 0, ...r, _lastFinishedItem: r.finished_item || "" }));
  detalles.value = (data.costeo_producto_detalle || []).map(r => ({ _tid: uid(), _supplierOptions: [], _qtyMode: "rendimiento", ...r, material_id: r.material_id || genStageId() }));
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
  tallas.value = (data.tabla_tallas_costeo || []).map(r => ({ _tid: uid(), sobrecosto_tipo: "Ninguno", estado_cantidad: "Definida", ...r }));
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
}

async function loadRelated() {
  if (!docName.value) return;
  try {
    const r = await call("costeo_yelke.api.costeo_api.get_costeo_related", { costeo: docName.value, sales_order: activeSOName.value || null });
    related.quotation = r.quotation; related.quotations = r.quotations || []; related.sales_order = r.sales_order;
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
      if (!activeSOName.value || !related.sales_orders.some(s => s.name === activeSOName.value)) {
        activeSOName.value = expandedSOName.value || related.sales_orders[0].name;
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
    }
    loadProdComplete(docName.value, activeSOName.value);
    // El backend reconcilia el estado si borraron documentos (p. ej. la cotización) desde ERPNext
    if (r.costeo_status && r.costeo_status !== docStatus.value) {
      docStatus.value = r.costeo_status;
      const idx = ORDER.indexOf(r.costeo_status);
      if (idx >= 0 && activeStep.value > idx) activeStep.value = idx;
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
  } catch { dnDoc.value = null; }
}
async function selectDn(name) {
  dnSel.value = name;
  if (name) await loadRemisionDetalle(name);
  else dnDoc.value = null;
}
async function generarRemision() {
  if (isNew.value) { showToast("Guarda el costeo primero", "error"); return; }
  if (activeSO.value?.docstatus !== 1) { showToast("Primero valida la orden de venta", "error"); return; }
  advancing.value = true;
  try {
    const r = await call("costeo_yelke.api.costeo_api.crear_remision", { costeo: docName.value, sales_order: activeSOName.value });
    dnSel.value = r.name;
    await loadRelated();
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
    });
    await loadRemisionDetalle(dnDoc.value.name);
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
    });
    const rv = await call("costeo_yelke.api.costeo_api.validar_remision", { name: dnDoc.value.name });
    await loadRemisionDetalle(dnDoc.value.name);
    await loadRelated();
    // Solo avanza el costeo a "Entregado" cuando la OV queda 100% entregada -- puede
    // haber más remisiones pendientes a otras direcciones del cliente.
    const completo = (related.delivery_per_delivered || 0) >= 99.99;
    if (completo && ORDER.indexOf(docStatus.value) < ORDER.indexOf("Entregado")) docStatus.value = "Entregado";
    const base = completo ? "Remisión validada · mercancía entregada al cliente" : `Remisión validada · saldo pendiente por entregar (${(100 - related.delivery_per_delivered).toFixed(0)}%)`;
    showToast(rv?.flete_journal_entry ? `${base} · flete registrado (${rv.flete_journal_entry})` : base);
  } catch (e) { showToast(e.message || "No se pudo validar la remisión", "error"); }
  finally { advancing.value = false; }
}

async function generarFactura() {
  if (isNew.value) { showToast("Guarda el costeo primero", "error"); return; }
  if (activeSO.value?.docstatus !== 1) { showToast("Primero valida la orden de venta", "error"); return; }
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.crear_factura_venta", {
      costeo: docName.value,
      posting_date: siForm.posting_date || null, due_date: siForm.due_date || null,
      payment_terms_template: siForm.payment_terms_template || null, tc_name: siForm.tc_name || null,
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
async function selectComprasTab() {
  factTab.value = "compras";
  await loadCompras();
}
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
    const r = await call("costeo_yelke.api.costeo_api.get_facturas_compra", { costeo: docName.value });
    compras.materiales = r.materiales || []; compras.maquila = r.maquila || [];
  } catch { /* ignore */ }
}
async function selectCompra(source_doctype, row) {
  pinvSel.value = { source_doctype, source_name: row.name, supplier_name: row.supplier_name || row.supplier, monto: row.base_net_total };
  if (row.invoice) { await loadPinv(row.invoice.name); } else { pinvDoc.value = null; }
}
async function generarFacturaCompra() {
  if (!pinvSel.value) return;
  advancing.value = true;
  try {
    const r = await call("costeo_yelke.api.costeo_api.crear_factura_compra", { source_doctype: pinvSel.value.source_doctype, source_name: pinvSel.value.source_name });
    await loadCompras();
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
    });
    await loadPinv(pinvDoc.value.name);
    showToast("Factura de compra guardada");
  } catch (e) { showToast(e.message || "Error al guardar", "error"); }
  finally { advancing.value = false; }
}
async function validarPinv() {
  if (!pinvDoc.value) return;
  advancing.value = true;
  try {
    await guardarPinv();
    await call("costeo_yelke.api.costeo_api.validar_documento", { doctype: "Purchase Invoice", name: pinvDoc.value.name });
    await loadCompras();
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
      return { ...p, operaciones: ops };
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
async function confirmarFlujo() {
  if (isNew.value) { showToast("Guarda el costeo primero", "error"); return; }
  advancing.value = true;
  try {
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
    flujoDirty.value = false;
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
  // No guardar borrador mientras se está cargando desde el servidor (fillFromDoc)
  // ni mientras hay un borrador pendiente de decisión -- si no, se pisaría solo.
  if (loading.value || cargandoDoc || draftBanner.show) return;
  clearTimeout(draftTimer);
  draftTimer = setTimeout(saveDraftToLocalStorage, 800);
}
watch([form, productos, detalles, etapas, materialesEtapa, tallas], scheduleDraftSave, { deep: true });

function checkForDraft() {
  const raw = loadDraftFromLocalStorage(docName.value || route.params.name);
  if (!raw || !raw.data) return;
  const UNA_SEMANA = 7 * 24 * 60 * 60 * 1000;
  if (!raw.savedAt || Date.now() - raw.savedAt > UNA_SEMANA) {
    clearDraft(docName.value || route.params.name);
    return;
  }
  pendingDraft.value = raw.data;
  draftBanner.savedAt = raw.savedAt;
  draftBanner.show = true;
}
function restoreDraft() {
  const d = pendingDraft.value;
  if (!d) return;
  Object.assign(form, d.form || {});
  productos.value = d.productos || [];
  detalles.value = d.detalles || [];
  etapas.value = d.etapas || [];
  materialesEtapa.value = d.materialesEtapa || [];
  tallas.value = d.tallas || [];
  draftBanner.show = false;
  pendingDraft.value = null;
  showToast("Borrador recuperado");
}
function discardDraft() {
  clearDraft(docName.value || route.params.name);
  draftBanner.show = false;
  pendingDraft.value = null;
}
function draftAgeLabel() {
  if (!draftBanner.savedAt) return "";
  const mins = Math.round((Date.now() - draftBanner.savedAt) / 60000);
  if (mins < 1) return "hace un momento";
  if (mins < 60) return `hace ${mins} minuto${mins === 1 ? "" : "s"}`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `hace ${hrs} hora${hrs === 1 ? "" : "s"}`;
  const dias = Math.round(hrs / 24);
  return `hace ${dias} día${dias === 1 ? "" : "s"}`;
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
  if (c.action === "enviar") { activeStep.value = 6; return; }
  if (c.action === "ir_preparar_manufactura") { activeStep.value = 3; return; }
  if (c.action === "pasar_produccion") { await (activeStep.value === 4 ? confirmarFlujo() : prepararProduccion()); return; }
  if (!canAdvance.value) { showToast("Completa los pendientes antes de avanzar", "error"); return; }
  advancing.value = true;
  try {
    if (c.action === "cotizar") {
      const ok = await materializeFinishedProductsIfNeeded();
      if (!ok) return;
      await call("costeo_yelke.api.costeo_api.crear_cotizacion", { costeo: docName.value }); docStatus.value = "Cotizado"; showToast("Cotización creada");
    }
    else if (c.action === "vender") { await call("costeo_yelke.api.costeo_api.crear_orden_venta", { costeo: docName.value }); docStatus.value = "Orden de Venta"; showToast("Orden de venta creada"); }
    else if (c.action === "enviar") {
      activeStep.value = 6;
      return;
    }
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
  if (related.quotation?.docstatus !== 1) { showToast("Primero valida la cotización", "error"); return; }
  advancing.value = true;
  try {
    const res = await call("costeo_yelke.api.costeo_api.crear_orden_venta", {
      costeo: docName.value,
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
async function guardarCambiosOrdenVenta() {
  const name = expandedSOName.value;
  if (!name) return;
  advancing.value = true;
  try {
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
    await loadRelated();
    previewKey.value++;
    showToast("Cambios guardados");
  } catch (e) { showToast(e.message || "No se pudieron guardar los cambios", "error"); }
  finally { advancing.value = false; }
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

async function onTipoFormatoChange() {
  const name = expandedQuotName.value;
  if (!name) return;
  const q = related.quotations.find(x => x.name === name);
  if (!q || q.docstatus === 1) return;
  try {
    await call("costeo_yelke.api.costeo_api.set_tipo_formato_cotizacion", {
      name,
      custom_tipo_formato: cotForm.custom_tipo_formato,
    });
    q.custom_tipo_formato = cotForm.custom_tipo_formato;
    if (related.quotation?.name === name) related.quotation.custom_tipo_formato = cotForm.custom_tipo_formato;
    previewKey.value++;
  } catch (e) { showToast(e.message || "No se pudo actualizar la vista de impresión", "error"); }
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
      items: cotItems.value.filter(r => r.item_code).map(r => ({ item_code: r.item_code, item_name: r.item_name, qty: r.qty, rate: r.rate })),
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
    await call("costeo_yelke.api.costeo_api.validar_documento", { doctype, name });
    await loadRelated();
    previewKey.value++;
    if (after) after();
    showToast("Documento validado");
  } catch (e) { showToast(e.message || "No se pudo validar", "error"); }
  finally { advancing.value = false; }
}

async function loadCotDefaults() {
  try {
    const r = await call("costeo_yelke.api.costeo_api.get_cotizacion_defaults", { company: form.compania });
    cotDefaults.payment_terms_templates = r.payment_terms_templates || [];
    cotDefaults.terms = r.terms || [];
    cotDefaults.users = r.users || [];
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
async function materializeFinishedProductsIfNeeded() {
  materializeQueue = productos.value.filter(p => p.finished_item && (p.qty || 0) > 0);
  return new Promise((resolve) => {
    materializeDone = resolve;
    processNextMaterialize();
  });
}

async function processNextMaterialize() {
  if (!materializeQueue.length) { materializeDone && materializeDone(true); return; }
  const prod = materializeQueue[0];
  if (await itemExists(prod.finished_item)) { materializeQueue.shift(); return processNextMaterialize(); }
  materializeCurrentProd = prod;
  materializeModal.text = prod.finished_item;
  materializeModal.suggestedPrice = prod.unit_sales_price || 0;
  materializeModal.suggestedDescription = (prod.description || "") + buildTallaDescriptionSuffix(prod);
  materializeModal.suggestedImage = prod.image || "";
  materializeModal.saving = false;
  materializeModal.open = true;
}

function cancelMaterialize() {
  materializeModal.open = false;
  materializeQueue = [];
  if (materializeDone) materializeDone(false);
}

async function confirmMaterialize(payload) {
  const prod = materializeCurrentProd;
  materializeModal.saving = true;
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
    });
    prod.finished_item = r.item_code;
    prod._lastFinishedItem = r.item_code;
    detalles.value.forEach(d => { if (d.finished_item === oldText) d.finished_item = r.item_code; });
    etapas.value.forEach(e => { if (e.producto_terminado === oldText) e.producto_terminado = r.item_code; });
    tallas.value.forEach(t => { if (t.finished_item === oldText) t.finished_item = r.item_code; });
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
function openTplModal() {
  actionsOpen.value = false;
  if (isNew.value) { showToast("Guarda el costeo primero", "error"); return; }
  tplModal.open = true;
}
async function guardarComoPlantilla() {
  tplModal.saving = true;
  try {
    if (docState.value === 0) await saveDoc();
    const res = await call("costeo_yelke.api.costeo_template_api.save_as_template", {
      costeo: docName.value,
    });
    tplModal.open = false;
    const n = (res?.creadas || []).length;
    showToast(n ? `${n} plantilla${n === 1 ? "" : "s"} guardada${n === 1 ? "" : "s"} · disponibles en Plantillas` : "No se creó ninguna plantilla");
  } catch (e) { showToast(e.message || "No se pudo guardar la plantilla", "error"); }
  finally { tplModal.saving = false; }
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
    const res = await call("costeo_yelke.api.costeo_api.crear_revision_costeo", { costeo: docName.value, motivo: revisionMotivo.value || "" });
    showRevisionModal.value = false;
    showToast(`Revisión creada: ${res.name}`);
    router.push({ name: "CosteoDetail", params: { name: res.name } });
  } catch (e) { showToast(e.message || "Error al crear la revisión", "error"); }
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
async function loadCosteoData() {
  loading.value = true;
  if (isNew.value) {
    if (!form.compania && companyState.selected) form.compania = companyState.selected;
    checkForDraft();
    loading.value = false;
    return;
  }
  try {
    const data = await db.get("Costeo", route.params.name);
    await fillFromDoc(data);
    checkForDraft();
    manufacturaGuardada.value = false;
    await loadRelated();
    await loadCotDefaults();
    await loadPlan(route.params.name, activeSOName.value);
    await loadPendientesArticulos();
    // Abre directo en el último paso alcanzado (no en el primero) -- para que
    // cualquiera que reabra el proyecto siga exactamente donde se quedó.
    activeStep.value = statusToStep(docStatus.value, hasPlan.value, etapas.value.length, pendientesArticulos.value.length);
    await loadRevisionInfo();
    // Llegada desde una lista de documentos (ej. /ordenes-compra): forzar el paso y
    // resaltar el documento exacto -- se consume una sola vez, luego se limpia la URL
    // para que un refresh no repita la animación.
    if (route.query.step !== undefined) activeStep.value = Number(route.query.step);
    if (route.query.highlight) {
      const target = String(route.query.highlight);
      const targetDoctype = route.query.doctype ? String(route.query.doctype) : null;
      // Limpiar la URL DESPUÉS de resaltar/hacer scroll -- router.replace() dispara su
      // propio ciclo de reactividad de forma asíncrona y, si corre en paralelo, puede
      // ganarle la carrera al scroll y dejarlo en 0 justo después de que ya se movió.
      await nextTick();
      await triggerHighlight(target, targetDoctype);
      router.replace({ path: route.path });
    }
    // El costeo se abre directo en el último paso alcanzado -- si ese paso carga
    // datos aparte (Flujo de Producción, Reporte final), hay que dispararlo aquí
    // (goStep solo corre al hacer clic en el stepper, no al montar).
    if (activeStep.value === 4) loadFlujoOps();
    if (activeStep.value === 8) loadReporte();
  } catch { showToast("No se pudo cargar el costeo", "error"); }
  finally { loading.value = false; }
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
