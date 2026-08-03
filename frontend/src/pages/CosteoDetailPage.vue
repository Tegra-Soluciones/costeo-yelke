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
      title="Cancelar Costeo"
      :message="`¿Cancelar la validación de ${docName}? Después podrás eliminarlo.`"
      confirm-label="Cancelar validación" :loading="confirmCancel.loading"
      @confirm="doCancel" @cancel="confirmCancel.open = false"
    />

    <!-- Modal: guardar como plantilla -->
    <div v-if="tplModal.open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="tplModal.open = false">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm p-5">
        <p class="text-sm font-semibold text-ink">Guardar como plantilla</p>
        <p class="text-[12px] text-ink-muted mt-0.5 mb-4">Crea una plantilla reutilizable a partir de este costeo (materiales, etapas y márgenes), sin cliente.</p>
        <label class="field-label">Nombre de la plantilla</label>
        <input v-model="tplModal.nombre" class="field-input mb-3" placeholder="Ej: Chamarra industrial base" />
        <label class="field-label">Familia de prenda</label>
        <input v-model="tplModal.familia" list="familias-list" class="field-input mb-4" placeholder="Ej: Chamarra" />
        <div class="flex gap-2 justify-end">
          <button class="px-3 py-1.5 text-[13px] text-ink-muted hover:bg-surface-raised rounded-lg" @click="tplModal.open = false">Cancelar</button>
          <button :disabled="!tplModal.nombre || tplModal.saving" class="px-4 py-1.5 text-[13px] font-medium text-white bg-brand-500 hover:bg-brand-600 disabled:opacity-50 rounded-lg flex items-center gap-2" @click="guardarComoPlantilla">
            <svg v-if="tplModal.saving" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
            {{ tplModal.saving ? "Guardando…" : "Guardar plantilla" }}
          </button>
        </div>
      </div>
    </div>

    <!-- Header -->
    <PageHeader :title="isNew ? 'Nuevo Costeo' : (docName || '…')" :subtitle="headerSubtitle" back>
      <div v-if="!isNew" class="relative" ref="actionsRef">
        <button class="h-8 w-8 flex items-center justify-center text-ink-muted border border-surface-border rounded-lg hover:bg-surface-raised transition-colors" :class="actionsOpen ? 'bg-surface-raised' : ''" @click.stop="actionsOpen = !actionsOpen" aria-label="Acciones">
          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="5" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="12" cy="19" r="1.6"/></svg>
        </button>
        <Transition name="panel">
          <div v-if="actionsOpen" class="absolute right-0 top-full mt-1.5 w-48 bg-white border border-surface-border rounded-xl shadow-xl overflow-hidden z-50">
            <div class="py-1">
              <button class="action-item" @click="duplicateDoc">Duplicar</button>
              <button class="action-item" @click="openTplModal">Guardar como plantilla</button>
              <button class="action-item" @click="printDoc">Imprimir / PDF</button>
              <button class="action-item" @click="openInDesk">Abrir en Desk</button>
            </div>
            <div class="border-t border-surface-border py-1">
              <button v-if="docState === 1" class="action-item text-amber-600 hover:bg-amber-50 hover:text-amber-700" @click="openCancel">Cancelar validación</button>
              <button class="action-item text-red-500 hover:bg-red-50 hover:text-red-600" @click="openDelete">Eliminar</button>
            </div>
          </div>
        </Transition>
      </div>

      <span v-if="docState === 1" class="h-8 px-3 flex items-center gap-1.5 text-[13px] font-medium text-green-700 bg-green-50 rounded-lg">
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        Validado
      </span>
      <span v-else-if="docState === 2" class="h-8 px-3 flex items-center gap-1.5 text-[13px] font-medium text-red-600 bg-red-50 rounded-lg">
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/></svg>
        Cancelado
      </span>

      <button v-if="docState === 0" :disabled="saving" class="h-8 px-3.5 text-[13px] font-medium text-ink border border-surface-border rounded-lg hover:bg-surface-raised transition-colors disabled:opacity-50 flex items-center gap-2" @click="saveDoc">
        <svg v-if="saving" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
        {{ saving ? "Guardando…" : (isNew ? "Crear Costeo" : "Guardar") }}
      </button>

      <button v-if="!isNew && docState === 0" :disabled="advancing" class="h-8 px-3.5 text-[13px] font-semibold text-brand-700 bg-brand-50 rounded-lg hover:bg-brand-100 transition-colors disabled:opacity-50 flex items-center gap-1.5" @click="validarCosteo" title="Guarda y valida el costeo para poder avanzar">
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        Validar
      </button>

      <button v-if="!isNew && cta" :disabled="advancing || !canAdvance" class="h-8 px-4 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 transition-colors disabled:opacity-40 flex items-center gap-1.5" :title="canAdvance ? '' : 'Completa los pendientes'" @click="advance">
        <svg v-if="advancing" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
        {{ cta.label }}
        <svg v-if="!advancing" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 7l5 5-5 5M6 12h12"/></svg>
      </button>
    </PageHeader>

    <CosteoStepper v-if="!isNew && docName" :model-value="docStatus" :active-step="activeStep" @select="goStep" />

    <div v-if="loading" class="flex-1 flex items-center justify-center text-ink-light">
      <svg class="w-7 h-7 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
    </div>

    <!-- ══════════ STEP 0 · COSTEAR ══════════ -->
    <div v-else-if="activeStep === 0" class="p-5 pb-40 flex gap-5 items-start">
      <div class="flex-1 min-w-0 space-y-4">
        <section class="bg-white rounded-xl border border-surface-border">
          <div class="px-5 py-3 border-b border-surface-border"><h3 class="section-title">Información general</h3></div>
          <div class="p-5 grid grid-cols-2 gap-4">
            <div><label class="field-label">Cliente <span class="text-red-400">*</span></label><LinkInput v-model="form.cliente" doctype="Customer" placeholder="Buscar cliente…" :error="!!errors.cliente" /></div>
            <div><label class="field-label">Fecha <span class="text-red-400">*</span></label><input v-model="form.fecha" type="date" class="field-input" :class="errors.fecha ? 'border-red-400' : ''" /></div>
            <div><label class="field-label">Compañía <span class="text-red-400">*</span></label><LinkInput v-model="form.compania" doctype="Company" placeholder="Compañía…" :error="!!errors.compania" /></div>
            <div>
              <label class="field-label">Familia de prenda</label>
              <input v-model="form.familia_prenda" list="familias-list" type="text" class="field-input" placeholder="Ej: Camisola industrial" />
              <datalist id="familias-list"><option v-for="f in familias" :key="f" :value="f" /></datalist>
            </div>
            <div><label class="field-label">Centro de costos <span class="text-red-400">*</span></label><LinkInput v-model="form.centro_de_costos" doctype="Cost Center" placeholder="Centro de costos…" :error="!!errors.centro_de_costos" /></div>
            <div><label class="field-label">Proyecto</label><LinkInput v-model="form.proyecto" doctype="Project" placeholder="Proyecto (opcional)" /></div>
            <div><label class="field-label">Almacén materias primas <span class="text-red-400">*</span></label><LinkInput v-model="form.almacen_materias_primas" doctype="Warehouse" placeholder="Almacén MP…" :error="!!errors.almacen_materias_primas" /></div>
            <div><label class="field-label">Almacén trabajo en proceso <span class="text-red-400">*</span></label><LinkInput v-model="form.almacen_trabajo_en_proceso" doctype="Warehouse" placeholder="Almacén WIP…" :error="!!errors.almacen_trabajo_en_proceso" /></div>
          </div>
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
                <img v-if="prod._image" :src="prod._image" class="w-9 h-9 rounded-lg object-cover border border-surface-border flex-shrink-0" alt="" />
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
                <div class="flex gap-4">
                  <div class="w-20 h-20 flex-shrink-0 rounded-lg border border-surface-border overflow-hidden bg-white">
                    <img v-if="prod._image" :src="prod._image" class="w-full h-full object-cover" alt="" />
                    <div v-else class="w-full h-full flex items-center justify-center text-ink-xlight">
                      <svg class="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.4"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                    </div>
                  </div>
                  <div class="flex-1 grid grid-cols-4 gap-3">
                    <div class="col-span-2"><label class="field-label">Producto terminado <span class="text-red-400">*</span></label><LinkInput v-model="prod.finished_item" doctype="Item" :filters="ITEM_FILTERS.terminado" placeholder="Producto terminado…" @update:model-value="onProductoItemChange(prod)" /></div>
                    <div><label class="field-label">Cantidad <span class="text-red-400">*</span></label><input v-model.number="prod.qty" type="number" min="1" class="field-input" @input="recalcProducto(prod)" /></div>
                    <div><label class="field-label">Overhead %</label><div class="relative"><input v-model.number="prod.overhead_pct" type="number" min="0" max="100" class="field-input pr-7" @input="recalcProducto(prod)" /><span class="suffix">%</span></div></div>
                    <div><label class="field-label">Flete / envío</label><div class="relative"><span class="prefix">$</span><input v-model.number="prod.shipping_cost" type="number" min="0" class="field-input pl-6" @input="recalcProducto(prod)" /></div></div>
                    <div><label class="field-label">Margen %</label><div class="relative"><input v-model.number="prod.margin_pct" type="number" min="0" max="99" class="field-input pr-7" @input="recalcProducto(prod)" /><span class="suffix">%</span></div></div>
                    <div class="col-span-1"><label class="field-label">Precio unit.</label><div class="relative"><span class="prefix text-brand-600">$</span><input v-model.number="prod.unit_sales_price" type="number" min="0" step="0.01" class="field-input pl-6 text-brand-600 font-semibold" @input="onPriceChange(prod)" /></div></div>
                  </div>
                </div>

                <div>
                  <div class="flex border-b border-surface-border mb-3">
                    <button v-for="tab in TABS" :key="tab.key" class="px-4 py-2 text-xs font-medium border-b-2 transition-colors -mb-px" :class="activeTab(prod._tid) === tab.key ? 'border-brand-500 text-brand-600' : 'border-transparent text-ink-muted hover:text-ink'" @click="setTab(prod._tid, tab.key)">
                      {{ tab.label }}<span v-if="tabCount(prod, tab.key) > 0" class="ml-1.5 px-1.5 py-0.5 rounded-full text-xs" :class="activeTab(prod._tid) === tab.key ? 'bg-brand-100 text-brand-700' : 'bg-surface-raised text-ink-muted'">{{ tabCount(prod, tab.key) }}</span>
                    </button>
                  </div>

                  <div v-if="activeTab(prod._tid) === 'materiales'" class="pb-8">
                    <table class="w-full text-sm mb-3">
                      <thead><tr class="border-b border-surface-border text-left text-xs font-semibold text-ink-light"><th class="py-2 w-1/4">Artículo</th><th class="py-2 w-1/5">Proveedor</th><th class="py-2 w-16">Etapa</th><th class="py-2 w-24 text-right">Cant.</th><th class="py-2 w-28 text-right">Precio unit.</th><th class="py-2 w-28 text-right">Total</th><th class="w-7"></th></tr></thead>
                      <tbody>
                        <tr v-for="d in materialesDe(prod.finished_item)" :key="d._tid" class="border-b border-surface-border/60">
                          <td class="py-1.5 pr-2"><LinkInput v-model="d.item" doctype="Item" :filters="ITEM_FILTERS.mp" placeholder="Materia prima…" @update:model-value="onDetalleItemChange(d, prod)" /></td>
                          <td class="py-1.5 pr-2">
                            <select v-model="d.supplier" @change="onSupplierChange(d, prod)" :disabled="!d.item" class="field-input">
                              <option value="">{{ !d.item ? 'Elige artículo' : ((d._supplierOptions || []).length ? '— Proveedor —' : 'Sin proveedor con precio') }}</option>
                              <option v-for="o in d._supplierOptions || []" :key="o.supplier" :value="o.supplier">{{ o.supplier_name || o.supplier }}</option>
                            </select>
                          </td>
                          <td class="py-1.5 pr-2"><input v-model="d.etapa" class="field-input" placeholder="1" /></td>
                          <td class="py-1.5 pr-2"><input v-model.number="d.supplier_qty" type="number" min="0" step="0.01" class="field-input text-right" @input="recalcDetalle(d, prod)" /></td>
                          <td class="py-1.5 pr-2"><div class="relative"><span class="prefix text-xs">$</span><input v-model.number="d.unit_price" type="number" min="0" step="0.01" class="field-input text-right pl-5" @input="recalcDetalle(d, prod)" /></div></td>
                          <td class="py-1.5 pr-2 text-right font-medium text-ink">{{ fmtC(d.total) }}</td>
                          <td class="py-1.5"><button class="del-btn" @click="removeDetalle(d, prod)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button></td>
                        </tr>
                      </tbody>
                    </table>
                    <button class="add-link" @click="addDetalle(prod, 'Materia Prima')"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>Agregar material</button>
                  </div>

                  <div v-else-if="activeTab(prod._tid) === 'etapas'" class="pb-8">
                    <table class="w-full text-sm mb-3">
                      <thead><tr class="border-b border-surface-border text-left text-xs font-semibold text-ink-light"><th class="py-2 w-16">Etapa</th><th class="py-2">Servicio</th><th class="py-2">Proveedor</th><th class="py-2 w-28 text-right">Precio</th><th class="py-2">Sub-ensamblaje</th><th class="w-7"></th></tr></thead>
                      <tbody>
                        <tr v-for="e in etapasDe(prod.finished_item)" :key="e._tid" class="border-b border-surface-border/60">
                          <td class="py-1.5 pr-2"><input v-model="e.etapa" class="field-input" placeholder="1" /></td>
                          <td class="py-1.5 pr-2"><LinkInput v-model="e.servicio" doctype="Item" :filters="ITEM_FILTERS.servicio" placeholder="Servicio…" @update:model-value="onEtapaServicioChange(e, prod)" /></td>
                          <td class="py-1.5 pr-2"><LinkInput v-model="e.proveedor" doctype="Supplier" placeholder="Taller…" /></td>
                          <td class="py-1.5 pr-2"><div class="relative"><span class="prefix text-xs">$</span><input v-model.number="e.precio_servicio" type="number" min="0" step="0.01" class="field-input text-right pl-5" @input="recalcProducto(prod)" /></div></td>
                          <td class="py-1.5 pr-2"><LinkInput v-model="e.subensamblaje" doctype="Item" :filters="ITEM_FILTERS.sub" placeholder="Sub-ensamblaje…" /></td>
                          <td class="py-1.5"><button class="del-btn" @click="removeEtapa(e, prod)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button></td>
                        </tr>
                      </tbody>
                    </table>
                    <button class="add-link" @click="addEtapa(prod)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>Agregar etapa</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>

      <div class="w-64 flex-shrink-0 space-y-3 sticky top-5 self-start max-h-[calc(100vh-80px)] overflow-y-auto">
        <div class="grid grid-cols-2 gap-2">
          <div class="metric"><p class="metric-label">Costo total</p><p class="metric-val">{{ fmtC(totalCosto) }}</p></div>
          <div class="metric"><p class="metric-label">Precio venta</p><p class="metric-val">{{ fmtC(totalVenta) }}</p></div>
          <div class="metric"><p class="metric-label">Margen</p><p class="metric-val text-green-600">{{ margenPct }}%</p></div>
          <div class="metric"><p class="metric-label">Productos</p><p class="metric-val">{{ productos.length }}</p></div>
        </div>
        <div v-if="!isNew && cta" class="bg-white rounded-xl border border-surface-border p-4">
          <p class="section-title mb-2">Listo para {{ cta.label.toLowerCase() }}</p>
          <div v-for="item in checklist" :key="item.label" class="flex items-center gap-2 text-[13px] py-1">
            <svg v-if="item.ok" class="w-4 h-4 text-green-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            <svg v-else class="w-4 h-4 text-ink-light flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>
            <span :class="item.ok ? 'text-ink' : 'text-ink-muted'">{{ item.label }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ══════════ STEP 1 · COTIZAR ══════════ -->
    <div v-else-if="activeStep === 1" class="p-5 pb-20">
      <div class="flex gap-5 items-start max-w-6xl mx-auto">

        <!-- Izquierda: campos manuales -->
        <div class="w-80 flex-shrink-0 bg-white rounded-xl border border-surface-border p-5">
          <div class="flex items-center justify-between mb-1">
            <p class="text-sm font-semibold text-ink">Datos de la cotización</p>
            <span v-if="related.quotation" class="text-[11px] font-semibold px-2 py-0.5 rounded-full" :class="quotValidated ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'">{{ quotValidated ? 'Validada' : 'Borrador' }}</span>
          </div>
          <p class="text-[12px] text-ink-muted mb-4">Completa lo que no viene del costeo. Productos y totales son automáticos.</p>

          <label class="field-label">Vigencia (válida hasta)</label>
          <input v-model="cotForm.valid_till" type="date" class="field-input mb-3" :disabled="quotValidated" />

          <label class="field-label">Condiciones de pago</label>
          <select v-model="cotForm.payment_terms_template" class="field-input mb-3" :disabled="quotValidated">
            <option value="">— Sin plantilla —</option>
            <option v-for="p in cotDefaults.payment_terms_templates" :key="p.name" :value="p.name">{{ p.name }}</option>
          </select>

          <label class="field-label">Términos y condiciones</label>
          <select v-model="cotForm.tc_name" class="field-input mb-4" :disabled="quotValidated">
            <option value="">— Sin términos —</option>
            <option v-for="t in cotDefaults.terms" :key="t.name" :value="t.name">{{ t.name }}</option>
          </select>

          <div class="border-t border-surface-border pt-3 mb-4 space-y-1">
            <div class="flex justify-between text-[13px]"><span class="text-ink-muted">Productos</span><span>{{ productos.length }}</span></div>
            <div class="flex justify-between text-[13px]"><span class="text-ink-muted">Total venta</span><span class="font-medium">{{ fmtC(totalVenta) }}</span></div>
          </div>

          <button v-if="!related.quotation" :disabled="advancing" class="w-full h-9 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center justify-center gap-2" @click="guardarBorradorCotizacion">
            <svg v-if="advancing" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
            Guardar como borrador
          </button>

          <div v-else class="space-y-2">
            <template v-if="!quotValidated">
              <button :disabled="advancing" class="w-full h-9 text-sm font-medium text-ink border border-surface-border rounded-lg hover:bg-surface-raised disabled:opacity-50" @click="guardarCambiosCotizacion">Guardar cambios</button>
              <button :disabled="advancing" class="w-full h-9 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center justify-center gap-1.5" @click="validarDoc('Quotation', related.quotation.name)">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Validar cotización
              </button>
            </template>
            <div class="grid grid-cols-2 gap-2 pt-1">
              <button class="doc-action justify-center" @click="openSend('Quotation', related.quotation.name, related.quotation.contact_email)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>Enviar</button>
              <button class="doc-action justify-center" @click="downloadPdf('Quotation', related.quotation.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/></svg>Descargar</button>
              <button class="doc-action justify-center" @click="printDocView('Quotation', related.quotation.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2z"/></svg>Imprimir</button>
              <button class="doc-action justify-center" @click="openAssign('Quotation', related.quotation.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>Asignar</button>
            </div>
            <a class="doc-action justify-center w-full" :href="`/app/quotation/${related.quotation.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>Abrir en ERPNext</a>
          </div>
        </div>

        <!-- Derecha: vista previa del PDF (zoom reducido) -->
        <div class="flex-1 min-w-0 bg-white rounded-xl border border-surface-border overflow-hidden">
          <div v-if="!related.quotation" class="flex flex-col items-center justify-center gap-2 text-ink-light" style="height: 78vh;">
            <svg class="w-10 h-10 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
            <p class="text-[13px]">La vista previa aparecerá al guardar el borrador</p>
          </div>
          <div v-else style="height: 78vh; overflow: auto;">
            <iframe :key="previewKey" :src="printUrl('Quotation', related.quotation.name)" style="width: 143%; height: 143%; transform: scale(0.7); transform-origin: top left; border: 0;" title="Vista previa de la cotización"></iframe>
          </div>
        </div>
      </div>
    </div>

    <!-- ══════════ STEP 2 · VENDER ══════════ -->
    <div v-else-if="activeStep === 2" class="p-5 pb-20">
      <div class="flex gap-5 items-start max-w-6xl mx-auto">

        <!-- Izquierda: campos manuales -->
        <div class="w-80 flex-shrink-0 bg-white rounded-xl border border-surface-border p-5">
          <div class="flex items-center justify-between mb-1">
            <p class="text-sm font-semibold text-ink">Datos de la orden de venta</p>
            <span v-if="related.sales_order" class="text-[11px] font-semibold px-2 py-0.5 rounded-full" :class="soValidated ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'">{{ soValidated ? 'Validada' : 'Borrador' }}</span>
          </div>
          <p class="text-[12px] text-ink-muted mb-4">Completa lo que no viene del costeo. Productos y totales son automáticos.</p>

          <label class="field-label">Fecha de envío / entrega</label>
          <input v-model="soForm.delivery_date" type="date" class="field-input mb-3" :disabled="soValidated" />

          <label class="field-label">Condiciones de pago</label>
          <select v-model="soForm.payment_terms_template" class="field-input mb-3" :disabled="soValidated">
            <option value="">— Sin plantilla —</option>
            <option v-for="p in cotDefaults.payment_terms_templates" :key="p.name" :value="p.name">{{ p.name }}</option>
          </select>

          <label class="field-label">Términos y condiciones</label>
          <select v-model="soForm.tc_name" class="field-input mb-4" :disabled="soValidated">
            <option value="">— Sin términos —</option>
            <option v-for="t in cotDefaults.terms" :key="t.name" :value="t.name">{{ t.name }}</option>
          </select>

          <div class="border-t border-surface-border pt-3 mb-4 space-y-1">
            <div class="flex justify-between text-[13px]"><span class="text-ink-muted">Productos</span><span>{{ productos.length }}</span></div>
            <div class="flex justify-between text-[13px]"><span class="text-ink-muted">Total venta</span><span class="font-medium">{{ fmtC(totalVenta) }}</span></div>
          </div>

          <div v-if="!related.sales_order">
            <button :disabled="advancing || related.quotation?.docstatus !== 1" class="w-full h-9 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-40 flex items-center justify-center gap-2" @click="guardarBorradorOrdenVenta">
              <svg v-if="advancing" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
              Guardar como borrador
            </button>
            <p v-if="related.quotation?.docstatus !== 1" class="text-[11px] text-ink-light mt-2 text-center">Primero valida la cotización.</p>
          </div>

          <div v-else class="space-y-2">
            <template v-if="!soValidated">
              <button :disabled="advancing" class="w-full h-9 text-sm font-medium text-ink border border-surface-border rounded-lg hover:bg-surface-raised disabled:opacity-50" @click="guardarCambiosOrdenVenta">Guardar cambios</button>
              <button :disabled="advancing" class="w-full h-9 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center justify-center gap-1.5" @click="validarDoc('Sales Order', related.sales_order.name)">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Validar orden
              </button>
            </template>
            <div class="grid grid-cols-2 gap-2 pt-1">
              <button class="doc-action justify-center" @click="openSend('Sales Order', related.sales_order.name, related.sales_order.contact_email)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>Enviar</button>
              <button class="doc-action justify-center" @click="downloadPdf('Sales Order', related.sales_order.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/></svg>Descargar</button>
              <button class="doc-action justify-center" @click="printDocView('Sales Order', related.sales_order.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2z"/></svg>Imprimir</button>
              <button class="doc-action justify-center" @click="openAssign('Sales Order', related.sales_order.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>Asignar</button>
            </div>
            <a class="doc-action justify-center w-full" :href="`/app/sales-order/${related.sales_order.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>Abrir en ERPNext</a>
          </div>
        </div>

        <!-- Derecha: vista previa del PDF -->
        <div class="flex-1 min-w-0 bg-white rounded-xl border border-surface-border overflow-hidden">
          <div v-if="!related.sales_order" class="flex flex-col items-center justify-center gap-2 text-ink-light" style="height: 78vh;">
            <svg class="w-10 h-10 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"/></svg>
            <p class="text-[13px]">La vista previa aparecerá al guardar el borrador</p>
          </div>
          <div v-else style="height: 78vh; overflow: auto;">
            <iframe :key="previewKey" :src="printUrl('Sales Order', related.sales_order.name)" style="width: 143%; height: 143%; transform: scale(0.7); transform-origin: top left; border: 0;" title="Vista previa de la orden de venta"></iframe>
          </div>
        </div>
      </div>
    </div>

    <!-- ══════════ STEP 3 · PRODUCIR (centro de control) ══════════ -->
    <div v-else-if="activeStep === 3" class="p-5 pb-20 max-w-5xl mx-auto w-full">
      <div class="flex items-center justify-between mb-4">
        <p class="text-sm font-semibold text-ink">Plan de producción</p>
        <button v-if="!hasPlan" :disabled="advancing" class="h-8 px-3.5 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center gap-1.5" @click="prepararProduccion">
          <svg v-if="advancing" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
          Preparar producción
        </button>
      </div>

      <div v-if="prepSteps.length" class="bg-white rounded-xl border border-surface-border p-4 mb-4">
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

      <div v-else-if="hasPlan" class="space-y-4">
        <!-- Barra de progreso secundaria -->
        <div class="flex items-center gap-1 bg-white rounded-xl border border-surface-border p-1.5">
          <button class="prod-tab" :class="prodTab === 0 ? 'prod-tab--active' : ''" @click="goProdTab(0)">
            <span class="prod-tab-num" :class="planValidated ? 'bg-brand-500 text-white' : (prodTab === 0 ? 'bg-brand-50 text-brand-600 border border-brand-500' : 'bg-surface-raised text-ink-light')">
              <svg v-if="planValidated" class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
              <span v-else>1</span>
            </span>
            Plan de producción
          </button>
          <svg class="w-4 h-4 text-ink-xlight flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
          <button class="prod-tab" :class="prodTab === 1 ? 'prod-tab--active' : ''" :disabled="!planValidated" @click="goProdTab(1)">
            <span class="prod-tab-num" :class="mrValidated ? 'bg-brand-500 text-white' : (prodTab === 1 ? 'bg-brand-50 text-brand-600 border border-brand-500' : 'bg-surface-raised text-ink-light')">
              <svg v-if="mrValidated" class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
              <span v-else>2</span>
            </span>
            Solicitud de material
          </button>
          <svg class="w-4 h-4 text-ink-xlight flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
          <button class="prod-tab" :class="prodTab === 2 ? 'prod-tab--active' : ''" :disabled="!anyOcValidated" @click="goProdTab(2)">
            <span class="prod-tab-num" :class="reciboValidated ? 'bg-brand-500 text-white' : (prodTab === 2 ? 'bg-brand-50 text-brand-600 border border-brand-500' : 'bg-surface-raised text-ink-light')">
              <svg v-if="reciboValidated" class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
              <span v-else>3</span>
            </span>
            Recibo de compra
          </button>
          <svg class="w-4 h-4 text-ink-xlight flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
          <button class="prod-tab" :class="prodTab === 3 ? 'prod-tab--active' : ''" :disabled="!planValidated" @click="goProdTab(3)">
            <span class="prod-tab-num" :class="subDone ? 'bg-brand-500 text-white' : (prodTab === 3 ? 'bg-brand-50 text-brand-600 border border-brand-500' : 'bg-surface-raised text-ink-light')">
              <svg v-if="subDone" class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
              <span v-else>4</span>
            </span>
            Subcontratación
          </button>
        </div>

        <!-- ═══ TAB 0 · Plan de producción ═══ -->
        <template v-if="prodTab === 0">
        <!-- Todo el plan en un solo recuadro -->
        <div class="bg-white rounded-xl border border-surface-border">
          <!-- Cabecera + campos -->
          <div class="p-5">
            <div class="flex items-center justify-between mb-4">
              <div class="flex items-center gap-2.5">
                <span class="text-sm font-semibold text-ink">{{ planDetail.name }}</span>
                <span class="text-[11px] font-semibold px-2 py-0.5 rounded-full" :class="planValidated ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'">{{ planValidated ? 'Validado' : 'Borrador' }}</span>
              </div>
              <a class="doc-action" :href="`/app/production-plan/${planDetail.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>ERPNext</a>
            </div>

            <div class="grid grid-cols-3 gap-4">
              <div>
                <label class="field-label">Almacén materias primas</label>
                <LinkInput v-if="!planValidated" v-model="planWh" doctype="Warehouse" placeholder="Almacén MP…" />
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

            <div v-if="!planValidated" class="flex items-center gap-2 mt-4">
              <button :disabled="advancing" class="doc-action" @click="obtenerMateriasPrimas"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>Obtener materias primas</button>
              <div class="flex-1"></div>
              <button :disabled="advancing" class="doc-action" @click="guardarPlan">Guardar</button>
              <button :disabled="advancing" class="h-8 px-3.5 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center gap-1.5" @click="validarPlan"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Validar plan</button>
            </div>
          </div>

          <!-- Productos a fabricar -->
          <div class="border-t border-surface-border px-5 py-4">
            <div class="prod-head"><span class="prod-title"><svg class="w-4 h-4 text-ink-light" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10"/></svg>Productos a fabricar <span class="prod-count">{{ planDetail.po_items.length }}</span></span></div>
            <div v-for="it in planDetail.po_items" :key="it.item_code" class="prod-row">
              <span class="flex-1 min-w-0 truncate"><span class="font-mono text-[12px]">{{ it.item_code }}</span> <span v-if="it.sales_order" class="text-ink-muted">· {{ it.sales_order }}</span></span>
              <span class="text-[13px] whitespace-nowrap">× {{ it.planned_qty }}</span>
              <span class="prod-status">{{ it.bom_no || 'sin BOM' }}</span>
            </div>
          </div>

          <!-- Materias primas a comprar -->
          <div class="border-t border-surface-border px-5 py-4">
            <div class="prod-head"><span class="prod-title"><svg class="w-4 h-4 text-ink-light" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"/></svg>Materias primas a comprar <span class="prod-count">{{ planDetail.mr_items.length }}</span></span></div>
            <div v-for="it in planDetail.mr_items" :key="it.item_code" class="prod-row">
              <span class="flex-1 min-w-0 truncate font-mono text-[12px]">{{ it.item_code }}</span>
              <span class="text-[13px] whitespace-nowrap">× {{ it.quantity }} {{ it.uom }}</span>
              <span class="prod-status">{{ it.warehouse }}</span>
            </div>
            <p v-if="!planDetail.mr_items.length" class="prod-empty">Sin faltantes (inventario suficiente) o pendiente de obtener.</p>
          </div>
        </div>

        <!-- Otras acciones (al validar el plan) -->
        <div class="bg-white rounded-xl border border-surface-border p-4">
          <p class="section-title mb-1">Otras acciones de producción</p>
          <p class="text-[12px] text-ink-muted mb-3">Producción interna (poco usada si se subcontrata todo). La subcontratación tiene su propia pestaña.</p>
          <div class="grid grid-cols-2 gap-2">
            <button :disabled="!planValidated || advancing" class="prod-next" @click="crearOrdenesTrabajo">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.6"><path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065zM15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
              Orden de trabajo
              <span v-if="downstream.wos.length" class="prod-done">{{ downstream.wos.length }} creada(s)</span>
            </button>
          </div>
        </div>
        </template>

        <!-- ═══ TAB 1 · Solicitud de material ═══ -->
        <template v-else-if="prodTab === 1">
          <!-- Sin solicitud -->
          <div v-if="!mrDetail" class="bg-white rounded-xl border border-surface-border p-8 text-center">
            <div class="w-12 h-12 rounded-xl bg-brand-50 flex items-center justify-center mx-auto mb-3"><svg class="w-6 h-6 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/></svg></div>
            <p class="text-sm font-medium text-ink">Aún no has creado la solicitud de material</p>
            <p class="text-[13px] text-ink-muted mt-1 mb-4">Se crea desde el plan, con el proveedor por materia prima ya asignado (del costeo).</p>
            <button :disabled="advancing" class="px-4 py-2 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50" @click="crearSolicitud">Crear solicitud de material</button>
          </div>

          <!-- Con solicitud -->
          <div v-else class="bg-white rounded-xl border border-surface-border">
            <div class="p-5">
              <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-2.5">
                  <span class="text-sm font-semibold text-ink">{{ mrDetail.name }}</span>
                  <span class="text-[11px] font-semibold px-2 py-0.5 rounded-full" :class="mrValidated ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'">{{ mrValidated ? 'Validada' : 'Borrador' }}</span>
                </div>
                <a class="doc-action" :href="`/app/material-request/${mrDetail.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>ERPNext</a>
              </div>
              <div class="grid grid-cols-3 gap-4">
                <div><label class="field-label">Tipo</label><div class="field-input bg-surface-raised/60">{{ mrDetail.material_request_type }}</div></div>
                <div>
                  <label class="field-label">Fecha requerida</label>
                  <input v-if="!mrValidated" v-model="mrSchedule" type="date" class="field-input" />
                  <div v-else class="field-input bg-surface-raised/60">{{ mrSchedule || '—' }}</div>
                </div>
                <div><label class="field-label">Estatus</label><div class="field-input bg-surface-raised/60">{{ mrDetail.status }}</div></div>
              </div>
              <div v-if="!mrValidated" class="flex items-center gap-2 mt-4">
                <div class="flex-1"></div>
                <button :disabled="advancing" class="doc-action" @click="guardarSolicitud">Guardar</button>
                <button :disabled="advancing" class="h-8 px-3.5 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center gap-1.5" @click="validarSolicitud"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Validar solicitud</button>
              </div>
            </div>

            <!-- Materiales -->
            <div class="border-t border-surface-border px-5 py-4">
              <div class="prod-head"><span class="prod-title"><svg class="w-4 h-4 text-ink-light" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10"/></svg>Materiales <span class="prod-count">{{ mrItems.length }}</span></span></div>
              <table class="w-full text-sm">
                <thead><tr class="text-left text-xs font-semibold text-ink-light border-b border-surface-border"><th class="py-2">Artículo</th><th class="py-2 w-24 text-right">Cantidad</th><th class="py-2 w-24">UOM</th><th class="py-2 w-1/3">Proveedor</th></tr></thead>
                <tbody>
                  <tr v-for="it in mrItems" :key="it.name" class="border-b border-surface-border/60">
                    <td class="py-1.5 pr-2 font-mono text-[12px]">{{ it.item_code }}</td>
                    <td class="py-1.5 pr-2"><input v-if="!mrValidated" v-model.number="it.qty" type="number" min="0" class="field-input text-right" /><span v-else class="text-right block">{{ it.qty }}</span></td>
                    <td class="py-1.5 pr-2 text-ink-muted text-xs">{{ it.uom }}</td>
                    <td class="py-1.5 pr-2"><LinkInput v-if="!mrValidated" v-model="it.supplier" doctype="Supplier" placeholder="Proveedor…" /><span v-else>{{ it.supplier || '—' }}</span></td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Documentos de compra (sub-pestañas + detalle editable) -->
            <div class="border-t border-surface-border px-5 py-4">
              <p class="section-title mb-1">Documentos de compra</p>
              <p v-if="!mrValidated" class="text-[12px] text-ink-muted mb-3">Valida la solicitud para desbloquear su creación.</p>
              <div v-else class="mb-3"></div>
              <div class="grid grid-cols-3 gap-2">
                <button :disabled="!mrValidated || advancing" class="prod-next" :class="mrDocTab === 'oc' ? 'prod-next--active' : ''" @click="selectDocTab('oc')">
                  <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.6"><path stroke-linecap="round" stroke-linejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"/></svg>
                  Orden de compra
                  <span v-if="mrResults.ocs.length" class="prod-done">{{ mrResults.ocs.length }}</span>
                </button>
                <button :disabled="!mrValidated || advancing" class="prod-next" :class="mrDocTab === 'rfq' ? 'prod-next--active' : ''" @click="selectDocTab('rfq')">
                  <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.6"><path stroke-linecap="round" stroke-linejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 3v-3z"/></svg>
                  Solicitud de cotización
                  <span v-if="mrResults.rfq" class="prod-done">1</span>
                </button>
                <button :disabled="!mrValidated || advancing" class="prod-next" :class="mrDocTab === 'sq' ? 'prod-next--active' : ''" @click="selectDocTab('sq')">
                  <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.6"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                  Presupuesto de proveedor
                  <span v-if="mrResults.sq" class="prod-done">1</span>
                </button>
              </div>

              <!-- Detalle del documento seleccionado -->
              <div v-if="docCompra && mrDocTab" class="mt-3">
                <div v-if="mrDocTab === 'oc' && mrResults.ocs.length > 1" class="flex items-center gap-2 mb-2 flex-wrap">
                  <span class="text-[12px] text-ink-muted">OC por proveedor:</span>
                  <button v-for="po in mrResults.ocs" :key="po" class="text-[12px] px-2.5 py-1 rounded-full border transition-colors" :class="ocSelected === po ? 'border-brand-500 text-brand-700 bg-brand-50' : 'border-surface-border text-ink-muted hover:bg-surface-raised'" @click="selectOC(po)">{{ po }}</button>
                </div>

                <div class="flex gap-4 items-start">
                  <!-- Izquierda: campos + items -->
                  <div class="flex-1 min-w-0 border border-surface-border rounded-lg p-4">
                    <div class="flex items-center justify-between mb-3">
                      <div class="flex items-center gap-2.5">
                        <span class="text-sm font-semibold text-ink">{{ docCompra.name }}</span>
                        <span class="text-[11px] font-semibold px-2 py-0.5 rounded-full" :class="docCompraValidated ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'">{{ docCompraValidated ? 'Validado' : 'Borrador' }}</span>
                      </div>
                      <a class="doc-action" :href="`/app/${DOC_COMPRA[mrDocTab].desk}/${docCompra.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>ERPNext</a>
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                      <div v-if="docCompra.supplier"><label class="field-label">Proveedor</label><div class="field-input bg-surface-raised/60 truncate">{{ docCompra.supplier }}</div></div>
                      <div><label class="field-label">Fecha</label><div class="field-input bg-surface-raised/60">{{ docCompra.transaction_date || '—' }}</div></div>
                      <div v-if="docCompra.has_schedule_date"><label class="field-label">Fecha requerida</label><input v-if="!docCompraValidated" v-model="docCompraForm.schedule_date" type="date" class="field-input" /><div v-else class="field-input bg-surface-raised/60">{{ docCompraForm.schedule_date || '—' }}</div></div>
                      <div v-if="docCompra.has_valid_till"><label class="field-label">Vigencia</label><input v-if="!docCompraValidated" v-model="docCompraForm.valid_till" type="date" class="field-input" /><div v-else class="field-input bg-surface-raised/60">{{ docCompraForm.valid_till || '—' }}</div></div>
                      <div v-if="docCompra.has_payment_terms">
                        <label class="field-label">Condiciones de pago</label>
                        <select v-if="!docCompraValidated" v-model="docCompraForm.payment_terms_template" class="field-input"><option value="">— Sin plantilla —</option><option v-for="p in cotDefaults.payment_terms_templates" :key="p.name" :value="p.name">{{ p.name }}</option></select>
                        <div v-else class="field-input bg-surface-raised/60 truncate">{{ docCompraForm.payment_terms_template || '—' }}</div>
                      </div>
                      <div v-if="docCompra.has_tc">
                        <label class="field-label">Términos y condiciones</label>
                        <select v-if="!docCompraValidated" v-model="docCompraForm.tc_name" class="field-input"><option value="">— Sin términos —</option><option v-for="t in cotDefaults.terms" :key="t.name" :value="t.name">{{ t.name }}</option></select>
                        <div v-else class="field-input bg-surface-raised/60 truncate">{{ docCompraForm.tc_name || '—' }}</div>
                      </div>
                    </div>
                    <table class="w-full text-sm mt-3">
                      <thead><tr class="text-left text-xs font-semibold text-ink-light border-b border-surface-border"><th class="py-2">Artículo</th><th class="py-2 w-20 text-right">Cant.</th><th class="py-2 w-16">UOM</th><th v-if="docCompraHasRate" class="py-2 w-24 text-right">Precio</th></tr></thead>
                      <tbody>
                        <tr v-for="it in docCompraItems" :key="it.name" class="border-b border-surface-border/60">
                          <td class="py-1.5 pr-2 font-mono text-[12px]">{{ it.item_code }}</td>
                          <td class="py-1.5 pr-2"><input v-if="!docCompraValidated" v-model.number="it.qty" type="number" min="0" class="field-input text-right" /><span v-else class="block text-right">{{ it.qty }}</span></td>
                          <td class="py-1.5 pr-2 text-ink-muted text-xs">{{ it.uom }}</td>
                          <td v-if="docCompraHasRate" class="py-1.5 pr-2"><input v-if="!docCompraValidated && it.has_rate" v-model.number="it.rate" type="number" min="0" step="0.01" class="field-input text-right" /><span v-else class="block text-right">{{ it.rate }}</span></td>
                        </tr>
                      </tbody>
                    </table>
                    <div class="flex items-center gap-2 mt-3 flex-wrap">
                      <button v-if="!docCompraValidated && docCompra.doctype === 'Purchase Order'" :disabled="advancing" class="doc-action" @click="jalarPreciosOC"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>Jalar precios</button>
                      <button :disabled="advancing" class="doc-action" @click="openSend(docCompra.doctype, docCompra.name, '')"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>Enviar</button>
                      <div class="flex-1"></div>
                      <template v-if="!docCompraValidated">
                        <button :disabled="advancing" class="doc-action" @click="guardarDocCompra">Guardar</button>
                        <button :disabled="advancing" class="h-8 px-3.5 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center gap-1.5" @click="validarDocCompra"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Validar</button>
                      </template>
                    </div>
                  </div>

                  <!-- Derecha: vista previa del PDF -->
                  <div class="w-[360px] flex-shrink-0 border border-surface-border rounded-lg overflow-hidden">
                    <div style="height: 62vh; overflow: auto;">
                      <iframe :key="'dc' + previewKey" :src="printUrl(docCompra.doctype, docCompra.name)" style="width: 182%; height: 182%; transform: scale(0.55); transform-origin: top left; border: 0;" title="Vista previa del documento"></iframe>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- ═══ TAB 2 · Recibo de compra ═══ -->
        <template v-else-if="prodTab === 2">
          <div v-if="!reciboOcs.length" class="bg-white rounded-xl border border-surface-border p-8 text-center">
            <p class="text-sm font-medium text-ink">Valida una orden de compra primero</p>
            <p class="text-[13px] text-ink-muted mt-1">El recibo de compra se crea desde una OC validada.</p>
          </div>
          <div v-else class="space-y-3">
            <div v-if="reciboOcs.length > 1" class="flex items-center gap-2 flex-wrap">
              <span class="text-[12px] text-ink-muted">OC:</span>
              <button v-for="o in reciboOcs" :key="o.name" class="text-[12px] px-2.5 py-1 rounded-full border transition-colors" :class="reciboOcSel === o.name ? 'border-brand-500 text-brand-700 bg-brand-50' : 'border-surface-border text-ink-muted hover:bg-surface-raised'" @click="selectReciboOc(o.name)">{{ o.name }} · {{ o.supplier_name || o.supplier }}</button>
            </div>

            <div v-if="!reciboPr" class="bg-white rounded-xl border border-surface-border p-8 text-center">
              <div class="w-12 h-12 rounded-xl bg-brand-50 flex items-center justify-center mx-auto mb-3"><svg class="w-6 h-6 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10"/></svg></div>
              <p class="text-sm font-medium text-ink">Aún no has recibido esta OC</p>
              <p class="text-[13px] text-ink-muted mt-1 mb-4">El recibo de compra registra la entrada a inventario (con el almacén de materias primas del costeo e IVA).</p>
              <button :disabled="advancing" class="px-4 py-2 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50" @click="crearRecibo">Crear recibo de compra</button>
            </div>

            <div v-else class="bg-white rounded-xl border border-surface-border">
              <div class="p-5">
                <div class="flex items-center justify-between mb-3">
                  <div class="flex items-center gap-2.5">
                    <span class="text-sm font-semibold text-ink">{{ reciboPr.name }}</span>
                    <span class="text-[11px] font-semibold px-2 py-0.5 rounded-full" :class="reciboValidated ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'">{{ reciboValidated ? 'Validado (en inventario)' : 'Borrador' }}</span>
                  </div>
                  <a class="doc-action" :href="`/app/purchase-receipt/${reciboPr.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>ERPNext</a>
                </div>
                <div class="grid grid-cols-3 gap-3">
                  <div v-if="reciboPr.supplier"><label class="field-label">Proveedor</label><div class="field-input bg-surface-raised/60 truncate">{{ reciboPr.supplier }}</div></div>
                  <div><label class="field-label">Fecha de recepción</label><input v-if="!reciboValidated" v-model="reciboForm.posting_date" type="date" class="field-input" /><div v-else class="field-input bg-surface-raised/60">{{ reciboForm.posting_date || '—' }}</div></div>
                  <div><label class="field-label">Almacén (aceptado)</label><div class="field-input bg-surface-raised/60 truncate">{{ reciboPr.set_warehouse || (reciboItems[0] && reciboItems[0].warehouse) || '—' }}</div></div>
                </div>
              </div>
              <div class="border-t border-surface-border px-5 py-4">
                <div class="prod-head"><span class="prod-title"><svg class="w-4 h-4 text-ink-light" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10"/></svg>Materiales recibidos <span class="prod-count">{{ reciboItems.length }}</span></span></div>
                <table class="w-full text-sm">
                  <thead><tr class="text-left text-xs font-semibold text-ink-light border-b border-surface-border"><th class="py-2">Artículo</th><th class="py-2 w-24 text-right">Cantidad</th><th class="py-2 w-20">UOM</th><th class="py-2">Almacén</th></tr></thead>
                  <tbody>
                    <tr v-for="it in reciboItems" :key="it.name" class="border-b border-surface-border/60">
                      <td class="py-1.5 pr-2 font-mono text-[12px]">{{ it.item_code }}</td>
                      <td class="py-1.5 pr-2"><input v-if="!reciboValidated" v-model.number="it.qty" type="number" min="0" class="field-input text-right" /><span v-else class="block text-right">{{ it.qty }}</span></td>
                      <td class="py-1.5 pr-2 text-ink-muted text-xs">{{ it.uom }}</td>
                      <td class="py-1.5 pr-2 text-ink-muted text-xs">{{ it.warehouse }}</td>
                    </tr>
                  </tbody>
                </table>
                <p class="text-[12px] text-ink-muted mt-2 flex items-center gap-1.5"><svg class="w-3.5 h-3.5 text-green-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>IVA aplicado · al validar entra a inventario y contabilidad.</p>
                <div v-if="!reciboValidated" class="flex items-center gap-2 mt-3">
                  <div class="flex-1"></div>
                  <button :disabled="advancing" class="doc-action" @click="guardarRecibo">Guardar</button>
                  <button :disabled="advancing" class="h-8 px-3.5 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center gap-1.5" @click="validarRecibo"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Validar recibo</button>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- ═══ TAB 3 · Subcontratación (maquila) ═══ -->
        <template v-else-if="prodTab === 3">
          <div v-if="!subOcs.length" class="bg-white rounded-xl border border-surface-border p-8 text-center">
            <div class="w-12 h-12 rounded-xl bg-brand-50 flex items-center justify-center mx-auto mb-3"><svg class="w-6 h-6 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/></svg></div>
            <p class="text-sm font-medium text-ink">Aún no has creado las órdenes de subcontrato</p>
            <p class="text-[13px] text-ink-muted mt-1 mb-4">Se crea una orden por etapa (corte, costura, bordado…), con su servicio, taller y BOM de subcontratación.</p>
            <button :disabled="advancing" class="px-4 py-2 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50" @click="crearSubcontratos">Crear órdenes de subcontrato</button>
          </div>

          <div v-else class="space-y-3">
            <div v-if="subOcs.length > 1" class="flex items-center gap-2 flex-wrap">
              <span class="text-[12px] text-ink-muted">Etapa / taller:</span>
              <button v-for="o in subOcs" :key="o.name" class="text-[12px] px-2.5 py-1 rounded-full border transition-colors" :class="subSel === o.name ? 'border-brand-500 text-brand-700 bg-brand-50' : 'border-surface-border text-ink-muted hover:bg-surface-raised'" @click="selectSub(o.name)">{{ o.name }} · {{ o.supplier_name || o.supplier }}</button>
            </div>

            <div v-if="subPo" class="space-y-3">
              <!-- Sub-stepper: proceso de ESTA OC (cada OC es una rama independiente) -->
              <div class="flex items-center gap-1 overflow-x-auto bg-white rounded-xl border border-surface-border p-1.5">
                <button v-for="s in subSteps" :key="s.key" @click="goSubTab(s)"
                  class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12.5px] font-medium whitespace-nowrap transition-colors"
                  :class="subTab === s.key ? 'bg-brand-500 text-white' : s.locked ? 'text-ink-muted/40 cursor-not-allowed' : 'text-ink-muted hover:bg-surface-raised'">
                  <span class="w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-semibold" :class="subTab === s.key ? 'bg-white/25 text-white' : s.done ? 'bg-green-100 text-green-700' : 'bg-surface-raised text-ink-muted'">
                    <svg v-if="s.locked" class="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
                    <svg v-else-if="s.done" class="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
                    <span v-else>{{ s.key + 1 }}</span>
                  </span>
                  {{ s.label }}
                </button>
              </div>

              <!-- ── Paso 1 · Orden de manufactura (OC + instrucciones) ── -->
              <div v-show="subTab === 0" class="space-y-3">
              <div class="border border-surface-border rounded-lg p-4">
                <div class="flex items-center justify-between mb-3">
                  <div class="flex items-center gap-2.5">
                    <span class="text-sm font-semibold text-ink">{{ subPo.name }}</span>
                    <span class="text-[11px] font-semibold px-2 py-0.5 rounded-full" :class="subValidated ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'">{{ subValidated ? 'Validada' : 'Borrador' }}</span>
                  </div>
                  <a class="doc-action" :href="`/app/purchase-order/${subPo.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>ERPNext</a>
                </div>
                <div class="grid grid-cols-2 gap-3">
                  <div v-if="subPo.supplier"><label class="field-label">Taller (proveedor)</label><div class="field-input bg-surface-raised/60 truncate">{{ subPo.supplier }}</div></div>
                  <div><label class="field-label">Fecha</label><div class="field-input bg-surface-raised/60">{{ subPo.transaction_date || '—' }}</div></div>
                  <div v-if="subPo.has_schedule_date"><label class="field-label">Fecha requerida</label><input v-if="!subValidated" v-model="subForm.schedule_date" type="date" class="field-input" /><div v-else class="field-input bg-surface-raised/60">{{ subForm.schedule_date || '—' }}</div></div>
                  <div v-if="subPo.has_payment_terms">
                    <label class="field-label">Condiciones de pago</label>
                    <select v-if="!subValidated" v-model="subForm.payment_terms_template" class="field-input"><option value="">— Sin plantilla —</option><option v-for="p in cotDefaults.payment_terms_templates" :key="p.name" :value="p.name">{{ p.name }}</option></select>
                    <div v-else class="field-input bg-surface-raised/60 truncate">{{ subForm.payment_terms_template || '—' }}</div>
                  </div>
                  <div v-if="subPo.has_tc">
                    <label class="field-label">Términos y condiciones</label>
                    <select v-if="!subValidated" v-model="subForm.tc_name" class="field-input"><option value="">— Sin términos —</option><option v-for="t in cotDefaults.terms" :key="t.name" :value="t.name">{{ t.name }}</option></select>
                    <div v-else class="field-input bg-surface-raised/60 truncate">{{ subForm.tc_name || '—' }}</div>
                  </div>
                </div>
                <table class="w-full text-sm mt-3">
                  <thead><tr class="text-left text-xs font-semibold text-ink-light border-b border-surface-border"><th class="py-2">Servicio</th><th class="py-2 w-20 text-right">Cant.</th><th class="py-2 w-16">UOM</th><th v-if="subHasRate" class="py-2 w-24 text-right">Precio</th></tr></thead>
                  <tbody>
                    <tr v-for="it in subItems" :key="it.name" class="border-b border-surface-border/60">
                      <td class="py-1.5 pr-2 font-mono text-[12px]">{{ it.item_code }}</td>
                      <td class="py-1.5 pr-2"><input v-if="!subValidated" v-model.number="it.qty" type="number" min="0" class="field-input text-right" /><span v-else class="block text-right">{{ it.qty }}</span></td>
                      <td class="py-1.5 pr-2 text-ink-muted text-xs">{{ it.uom }}</td>
                      <td v-if="subHasRate" class="py-1.5 pr-2"><input v-if="!subValidated && it.has_rate" v-model.number="it.rate" type="number" min="0" step="0.01" class="field-input text-right" /><span v-else class="block text-right">{{ it.rate }}</span></td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- Orden de manufactura (todos los campos) -->
              <div class="bg-white rounded-xl border border-surface-border p-4">
                <p class="section-title mb-1">Orden de manufactura · instrucciones de confección</p>
                <p class="text-[12px] text-ink-muted mb-3">Se guarda junto con la orden, con el botón "Guardar" de arriba.</p>

                <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-2">Info general</p>
                <div class="grid grid-cols-4 gap-3 mb-4">
                  <div><label class="field-label">Modelo</label><input v-model="omGeneral.om_modelo" :disabled="subValidated" class="field-input" /></div>
                  <div><label class="field-label">Tela</label><input v-model="omGeneral.om_tela" :disabled="subValidated" class="field-input" /></div>
                  <div><label class="field-label">Color</label><input v-model="omGeneral.om_color" :disabled="subValidated" class="field-input" /></div>
                  <div><label class="field-label">Color principal</label><input v-model="omGeneral.om_color_principal" :disabled="subValidated" class="field-input" /></div>
                  <div><label class="field-label">Forro</label><input v-model="omGeneral.om_forro" :disabled="subValidated" class="field-input" /></div>
                  <div><label class="field-label">Combinación</label><input v-model="omGeneral.om_combinacion" :disabled="subValidated" class="field-input" /></div>
                  <div><label class="field-label">Ubicación</label><input v-model="omGeneral.om_ubicacion" :disabled="subValidated" class="field-input" /></div>
                  <div><label class="field-label">Aberturas</label><input v-model.number="omGeneral.om_aberturas" type="number" :disabled="subValidated" class="field-input" /></div>
                  <div><label class="field-label">Fecha requerida</label><input v-model="omGeneral.om_fecha_requerida" type="date" :disabled="subValidated" class="field-input" /></div>
                </div>
                <div class="flex items-center gap-4 mb-4 text-[13px]">
                  <label class="flex items-center gap-1.5"><input type="checkbox" v-model="omGeneral.om_bordado" :true-value="1" :false-value="0" :disabled="subValidated" class="accent-brand-500" />Bordado</label>
                  <label class="flex items-center gap-1.5"><input type="checkbox" v-model="omGeneral.om_estampado" :true-value="1" :false-value="0" :disabled="subValidated" class="accent-brand-500" />Estampado</label>
                  <label class="flex items-center gap-1.5"><input type="checkbox" v-model="omGeneral.om_sublimado" :true-value="1" :false-value="0" :disabled="subValidated" class="accent-brand-500" />Sublimado</label>
                  <label class="flex items-center gap-1.5"><input type="checkbox" v-model="omGeneral.om_reflejante" :true-value="1" :false-value="0" :disabled="subValidated" class="accent-brand-500" />Reflejante</label>
                </div>

                <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-1">Tallas caballero</p>
                <div class="overflow-x-auto mb-4">
                  <table class="text-sm">
                    <thead><tr class="text-xs text-ink-light"><th class="px-2 py-1 text-left">Línea</th><th v-for="s in OM_CAB" :key="s" class="px-1 py-1 w-12 text-center">{{ s.slice(1) }}</th><th class="px-2 py-1">Total</th></tr></thead>
                    <tbody>
                      <tr v-for="row in omCab" :key="row.name || 'c'">
                        <td class="px-2 py-1 text-ink-muted text-xs">{{ row.linea || 'Cantidad' }}</td>
                        <td v-for="s in OM_CAB" :key="s" class="px-0.5 py-1"><input v-model.number="row[s]" type="number" min="0" :disabled="subValidated" class="field-input text-center px-1" /></td>
                        <td class="px-2 py-1 text-right font-medium">{{ tallaTotal(row, OM_CAB) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wider mb-1">Tallas dama</p>
                <div class="overflow-x-auto mb-4">
                  <table class="text-sm">
                    <thead><tr class="text-xs text-ink-light"><th class="px-2 py-1 text-left">Línea</th><th v-for="s in OM_DAMA" :key="s" class="px-1 py-1 w-12 text-center">{{ s.slice(1) }}</th><th class="px-2 py-1">Total</th></tr></thead>
                    <tbody>
                      <tr v-for="row in omDama" :key="row.name || 'd'">
                        <td class="px-2 py-1 text-ink-muted text-xs">{{ row.linea || 'Cantidad' }}</td>
                        <td v-for="s in OM_DAMA" :key="s" class="px-0.5 py-1"><input v-model.number="row[s]" type="number" min="0" :disabled="subValidated" class="field-input text-center px-1" /></td>
                        <td class="px-2 py-1 text-right font-medium">{{ tallaTotal(row, OM_DAMA) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div class="flex items-center justify-between mb-1">
                  <p class="text-[11px] font-semibold text-ink-muted uppercase tracking-wider">Procesos</p>
                  <button v-if="!subValidated" class="add-link" @click="addProceso"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>Proceso</button>
                </div>
                <div v-for="(p, i) in omProc" :key="i" class="grid grid-cols-4 gap-2 mb-1.5 items-center">
                  <input v-model="p.nombre_proceso" placeholder="Nombre del proceso" :disabled="subValidated" class="field-input" />
                  <input v-model="p.ubicacion" placeholder="Ubicación" :disabled="subValidated" class="field-input" />
                  <input v-model="p.colores" placeholder="Colores" :disabled="subValidated" class="field-input" />
                  <button v-if="!subValidated" class="del-btn justify-self-start" @click="removeProceso(i)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button>
                </div>
                <p v-if="!omProc.length" class="prod-empty mb-2">Sin procesos.</p>

                <label class="field-label mt-3">Observaciones</label>
                <textarea v-model="omGeneral.om_observaciones" rows="2" :disabled="subValidated" class="field-input"></textarea>

                <!-- Tablas de medidas flexibles -->
                <div class="flex items-center justify-between mt-4 mb-1.5">
                  <label class="field-label">Tablas de medidas</label>
                  <button v-if="!subValidated" class="add-link" @click="addTabla"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>Tabla</button>
                </div>
                <p v-if="!omTablas.length" class="prod-empty mb-2">Sin tablas de medidas.</p>
                <div v-for="(t, ti) in omTablas" :key="'t'+ti" class="border border-surface-border rounded-lg p-3 mb-2.5 bg-surface-raised/40">
                  <div class="flex items-center gap-2 mb-2 flex-wrap">
                    <input v-model="t.name" placeholder="Nombre de la tabla" :disabled="subValidated" class="field-input flex-1 min-w-[140px]" />
                    <input v-model="t.unit" placeholder="Unidad (ej. cm)" :disabled="subValidated" class="field-input w-28" />
                    <button v-if="!subValidated" class="del-btn" @click="removeTabla(ti)" title="Eliminar tabla"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button>
                  </div>
                  <div class="overflow-x-auto">
                    <table class="w-full text-[13px]">
                      <thead>
                        <tr>
                          <th v-for="(c, ci) in t.columns" :key="c" class="p-1 text-center font-medium text-ink-muted">
                            <div class="flex items-center justify-center gap-1">
                              <span>{{ ci + 1 }}</span>
                              <button v-if="!subValidated" class="text-ink-muted hover:text-red-500" @click="removeColumna(t, ci)" title="Eliminar columna"><svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button>
                            </div>
                          </th>
                          <th class="w-6"></th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(r, ri) in t.rows" :key="r.id">
                          <td v-for="c in t.columns" :key="c" class="p-0.5"><input v-model="r.cells[c]" :disabled="subValidated" class="field-input text-center" /></td>
                          <td class="p-0.5 text-center"><button v-if="!subValidated" class="text-ink-muted hover:text-red-500" @click="removeFila(t, ri)" title="Eliminar fila"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button></td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  <div v-if="!subValidated" class="flex items-center gap-3 mt-2">
                    <button class="add-link" @click="addColumna(t)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>Columna</button>
                    <button class="add-link" @click="addFila(t)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>Fila</button>
                  </div>
                </div>

                <!-- Diagramas / archivos -->
                <div class="flex items-center justify-between mt-4 mb-1.5">
                  <label class="field-label">Diagramas / archivos</label>
                  <label v-if="!subValidated" class="add-link cursor-pointer">
                    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
                    {{ omUploading ? 'Subiendo…' : 'Archivo' }}
                    <input type="file" multiple class="hidden" :disabled="omUploading" @change="onOmFile" />
                  </label>
                </div>
                <p v-if="!omArchivos.length" class="prod-empty mb-2">Sin archivos.</p>
                <div v-for="(a, i) in omArchivos" :key="'a'+i" class="flex items-center gap-2 mb-1.5">
                  <a :href="a.archivo" target="_blank" class="doc-action shrink-0"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"/></svg>Ver</a>
                  <input v-model="a.descripcion" placeholder="Descripción" :disabled="subValidated" class="field-input flex-1" />
                  <button v-if="!subValidated" class="del-btn" @click="removeArchivo(i)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button>
                </div>
              </div>

              <!-- Barra de acciones (abajo) -->
              <div class="flex items-center gap-2 flex-wrap bg-white rounded-xl border border-surface-border p-3">
                <button class="doc-action" @click="openPdf('Purchase Order', subPo.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>Vista previa</button>
                <button :disabled="advancing" class="doc-action" @click="openSend('Purchase Order', subPo.name, '')"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>Enviar</button>
                <div class="flex-1"></div>
                <template v-if="!subValidated">
                  <button :disabled="advancing" class="doc-action" @click="guardarSub">Guardar</button>
                  <button :disabled="advancing" class="h-8 px-4 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center gap-1.5" @click="validarSub"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Validar</button>
                </template>
                <span v-else class="text-[13px] text-green-700 font-medium flex items-center gap-1.5"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Validada</span>
              </div>
              </div><!-- /paso 1 -->

              <!-- ── Paso 2 · Orden de subcontratación (SCO) ── -->
              <div v-show="subTab === 1" class="space-y-3">
                <div v-if="!flujo.po_validated" class="bg-white rounded-xl border border-surface-border p-8 text-center">
                  <div class="w-12 h-12 rounded-xl bg-amber-50 flex items-center justify-center mx-auto mb-3"><svg class="w-6 h-6 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M5.07 19h13.86a2 2 0 001.71-3l-6.93-12a2 2 0 00-3.42 0l-6.93 12a2 2 0 001.71 3z"/></svg></div>
                  <p class="text-sm font-medium text-ink">Primero valida la orden de compra</p>
                  <p class="text-[13px] text-ink-muted mt-1">Ve al paso <b>Orden de manufactura</b> y valida la OC para poder generar la orden de subcontratación.</p>
                </div>
                <div v-else-if="!scoExists" class="bg-white rounded-xl border border-surface-border p-8 text-center">
                  <div class="w-12 h-12 rounded-xl bg-brand-50 flex items-center justify-center mx-auto mb-3"><svg class="w-6 h-6 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg></div>
                  <p class="text-sm font-medium text-ink">Genera la orden de subcontratación</p>
                  <p class="text-[13px] text-ink-muted mt-1 mb-4">Crea la orden de subcontratación (materia prima, servicio y taller) a partir de esta OC.</p>
                  <button :disabled="advancing" class="px-4 py-2 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50" @click="crearSco">Crear orden de subcontratación</button>
                </div>
                <template v-else>
                  <div class="bg-white rounded-xl border border-surface-border p-4">
                    <div class="flex items-center justify-between mb-3">
                      <div class="flex items-center gap-2.5">
                        <span class="text-sm font-semibold text-ink">{{ flujo.sco.name }}</span>
                        <span class="text-[11px] font-semibold px-2 py-0.5 rounded-full" :class="scoValidated ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'">{{ scoValidated ? 'Validada' : 'Borrador' }}</span>
                      </div>
                      <a class="doc-action" :href="`/app/subcontracting-order/${flujo.sco.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>ERPNext</a>
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
                    <p v-if="!scoCostos.length" class="prod-empty mb-1">Sin costos adicionales (fletes, maniobras…).</p>
                    <div v-for="(c, i) in scoCostos" :key="i" class="flex items-center gap-2 mb-1.5">
                      <input v-model="c.description" placeholder="Descripción" :disabled="scoValidated" class="field-input flex-1" />
                      <input v-model.number="c.amount" type="number" min="0" step="0.01" placeholder="Importe" :disabled="scoValidated" class="field-input w-32 text-right" />
                      <button v-if="!scoValidated" class="del-btn" @click="removeCosto(i)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button>
                    </div>
                  </div>

                  <div v-if="flujo.sco.supplied_items.length" class="bg-white rounded-xl border border-surface-border p-4">
                    <p class="section-title mb-2">Materia prima requerida (se transferirá al taller)</p>
                    <table class="w-full text-sm">
                      <thead><tr class="text-left text-xs font-semibold text-ink-light border-b border-surface-border"><th class="py-2">Material</th><th class="py-2 w-24 text-right">Cant.</th><th class="py-2 w-16">UOM</th></tr></thead>
                      <tbody>
                        <tr v-for="(m, i) in flujo.sco.supplied_items" :key="i" class="border-b border-surface-border/60">
                          <td class="py-1.5 pr-2">{{ m.item_name || m.rm_item_code }}</td>
                          <td class="py-1.5 pr-2 text-right">{{ m.required_qty }}</td>
                          <td class="py-1.5 pr-2 text-ink-muted text-xs">{{ m.stock_uom }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  <div class="flex items-center gap-2 flex-wrap bg-white rounded-xl border border-surface-border p-3">
                    <button class="doc-action" @click="openPdf('Subcontracting Order', flujo.sco.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>Vista previa</button>
                    <div class="flex-1"></div>
                    <template v-if="!scoValidated">
                      <button :disabled="advancing" class="doc-action" @click="guardarSco">Guardar</button>
                      <button :disabled="advancing" class="h-8 px-4 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center gap-1.5" @click="validarSco"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Validar</button>
                    </template>
                    <span v-else class="text-[13px] text-green-700 font-medium flex items-center gap-1.5"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Validada · continúa en Transferencia de material</span>
                  </div>
                </template>
              </div><!-- /paso 2 -->

              <!-- ── Paso 3 · Transferencia de material ── -->
              <div v-show="subTab === 2" class="space-y-3">
                <!-- Sin borrador aún: crear la transferencia -->
                <div v-if="!transDoc" class="bg-white rounded-xl border border-surface-border p-4">
                  <p class="section-title mb-1">Transferencia de material al taller</p>
                  <p class="text-[12px] text-ink-muted mb-3">Crea el movimiento de materia prima (Stock Entry · Enviar a subcontratista) hacia el almacén del taller — igual que el botón "Transferencia → Materiales al proveedor" de ERPNext. Se crea en <b>borrador</b> aquí mismo para que ajustes almacenes y lo valides.</p>
                  <div v-if="flujo.sco && flujo.sco.supplied_items.length" class="overflow-x-auto">
                    <table class="w-full text-sm">
                      <thead><tr class="text-left text-xs font-semibold text-ink-light border-b border-surface-border"><th class="py-2">Material</th><th class="py-2 w-24 text-right">Cant.</th><th class="py-2 w-16">UOM</th></tr></thead>
                      <tbody>
                        <tr v-for="(m, i) in flujo.sco.supplied_items" :key="i" class="border-b border-surface-border/60">
                          <td class="py-1.5 pr-2">{{ m.item_name || m.rm_item_code }}</td>
                          <td class="py-1.5 pr-2 text-right">{{ m.required_qty }}</td>
                          <td class="py-1.5 pr-2 text-ink-muted text-xs">{{ m.stock_uom }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  <p v-else class="prod-empty">La orden de subcontratación no tiene materia prima ligada (revisa el BOM de subcontratación).</p>
                  <div class="flex items-center gap-2 mt-3">
                    <div class="flex-1"></div>
                    <button :disabled="advancing || !(flujo.sco && flujo.sco.supplied_items.length)" class="h-8 px-4 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center gap-1.5" @click="transferirMaterial"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/></svg>Crear transferencia</button>
                  </div>
                </div>

                <!-- Con borrador/validada: detalle del Stock Entry en el SPA -->
                <template v-else>
                  <div class="bg-white rounded-xl border border-surface-border p-4">
                    <div class="flex items-center justify-between mb-3">
                      <div class="flex items-center gap-2.5">
                        <span class="text-sm font-semibold text-ink">{{ transDoc.name }}</span>
                        <span class="text-[11px] font-semibold px-2 py-0.5 rounded-full" :class="transValidated ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'">{{ transValidated ? 'Validada' : 'Borrador' }}</span>
                      </div>
                      <a class="doc-action" :href="`/app/stock-entry/${transDoc.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>ERPNext</a>
                    </div>
                    <div class="grid grid-cols-2 gap-3 mb-3">
                      <div>
                        <label class="field-label">Almacén de origen (de dónde sale la materia prima)</label>
                        <select v-model="transForm.from_warehouse" :disabled="transValidated" class="field-input"><option value="">— Selecciona —</option><option v-for="w in flujo.warehouses" :key="w.name" :value="w.name">{{ w.warehouse_name || w.name }}</option></select>
                        <button v-if="!transValidated && transDoc.recommended_source && transForm.from_warehouse !== transDoc.recommended_source" class="add-link mt-1" @click="transForm.from_warehouse = transDoc.recommended_source"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>Usar recomendado por etapa ({{ transDoc.recommended_source }})</button>
                      </div>
                      <div><label class="field-label">Almacén destino (taller / proveedor)</label><select v-model="transForm.to_warehouse" :disabled="transValidated" class="field-input"><option value="">— Selecciona —</option><option v-for="w in flujo.warehouses" :key="w.name" :value="w.name">{{ w.warehouse_name || w.name }}</option></select></div>
                    </div>
                    <div class="overflow-x-auto">
                      <table class="w-full text-sm">
                        <thead><tr class="text-left text-xs font-semibold text-ink-light border-b border-surface-border"><th class="py-2">Material</th><th class="py-2 w-24 text-right">A transferir</th><th class="py-2 w-24 text-right">Disponible</th><th class="py-2 w-16">UOM</th></tr></thead>
                        <tbody>
                          <tr v-for="it in transDoc.items" :key="it.name" class="border-b border-surface-border/60">
                            <td class="py-1.5 pr-2">{{ it.item_name || it.item_code }}</td>
                            <td class="py-1.5 pr-2"><input v-if="!transValidated" v-model.number="it.qty" type="number" min="0" class="field-input text-right" /><span v-else class="block text-right">{{ it.qty }}</span></td>
                            <td class="py-1.5 pr-2 text-right" :class="(it.available ?? 0) < it.qty ? 'text-red-600 font-semibold' : 'text-ink-muted'">{{ it.available === null ? '—' : it.available }}</td>
                            <td class="py-1.5 pr-2 text-ink-muted text-xs">{{ it.uom }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                    <p v-if="!transValidated && transDoc.items.some(it => (it.available ?? 0) < it.qty)" class="text-[12px] text-red-600 mt-2 flex items-start gap-1.5"><svg class="w-4 h-4 flex-shrink-0 mt-px" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M5.07 19h13.86a2 2 0 001.71-3l-6.93-12a2 2 0 00-3.42 0l-6.93 12a2 2 0 001.71 3z"/></svg>No hay stock suficiente en el almacén de origen. Cámbialo por el almacén donde recibiste la materia prima, o cómprala/recíbela primero (Recibo de compra).</p>
                  </div>

                  <!-- Acciones abajo -->
                  <div class="flex items-center gap-2 flex-wrap bg-white rounded-xl border border-surface-border p-3">
                    <button class="doc-action" @click="openPdf('Stock Entry', transDoc.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>Vista previa</button>
                    <div class="flex-1"></div>
                    <template v-if="!transValidated">
                      <button :disabled="advancing" class="doc-action" @click="guardarTrans">Guardar</button>
                      <button :disabled="advancing" class="h-8 px-4 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center gap-1.5" @click="validarTransferencia"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Validar</button>
                    </template>
                    <span v-else class="text-[13px] text-green-700 font-medium flex items-center gap-1.5"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Material transferido · continúa en Recibo</span>
                  </div>
                </template>
              </div><!-- /paso 3 -->

              <!-- ── Paso 4 · Recibo de subcontratación ── -->
              <div v-show="subTab === 3" class="space-y-3">
                <div v-if="!scr" class="bg-white rounded-xl border border-surface-border p-8 text-center">
                  <div class="w-12 h-12 rounded-xl bg-brand-50 flex items-center justify-center mx-auto mb-3"><svg class="w-6 h-6 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg></div>
                  <p class="text-sm font-medium text-ink">Recibe el producto del taller</p>
                  <p class="text-[13px] text-ink-muted mt-1 mb-4">Genera el recibo de subcontratación para ingresar a inventario lo que produjo el taller: producto terminado, semiterminado o subensamblaje, según la etapa.</p>
                  <button :disabled="advancing || !transferDone" class="px-4 py-2 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50" @click="crearReciboSub">Crear recibo de subcontratación</button>
                </div>
                <template v-else>
                  <div class="bg-white rounded-xl border border-surface-border p-4">
                    <div class="flex items-center justify-between mb-3">
                      <div class="flex items-center gap-2.5">
                        <span class="text-sm font-semibold text-ink">{{ scr.name }}</span>
                        <span class="text-[11px] font-semibold px-2 py-0.5 rounded-full" :class="scrValidated ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'">{{ scrValidated ? 'Validado' : 'Borrador' }}</span>
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
                  <div class="flex items-center gap-2 flex-wrap bg-white rounded-xl border border-surface-border p-3">
                    <button class="doc-action" @click="openPdf('Subcontracting Receipt', scr.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>Vista previa</button>
                    <div class="flex-1"></div>
                    <template v-if="!scrValidated">
                      <button :disabled="advancing" class="doc-action" @click="guardarScr">Guardar</button>
                      <button :disabled="advancing" class="h-8 px-4 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center gap-1.5" @click="validarScr"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Validar recibo</button>
                    </template>
                    <span v-else class="text-[13px] text-green-700 font-medium flex items-center gap-1.5"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Recibido · producto en inventario</span>
                  </div>
                </template>
              </div><!-- /paso 4 -->
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- ══════════ STEP 4 · FACTURAR ══════════ -->
    <div v-else class="p-5 pb-20">

      <!-- Gate: la remisión es obligatoria antes de poder facturar -->
      <div v-if="!dnValidated" class="max-w-2xl mx-auto">
        <div class="bg-white rounded-xl border border-surface-border p-8 text-center">
          <div class="w-12 h-12 rounded-xl bg-brand-50 flex items-center justify-center mx-auto mb-3">
            <svg class="w-6 h-6 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0l-2 5H6l-2-5m16 0H4m5 5v.01M15 18v.01"/></svg>
          </div>
          <p class="text-sm font-medium text-ink">Registra la remisión antes de facturar</p>
          <p class="text-[13px] text-ink-muted mt-1 mb-4 max-w-md mx-auto">La entrega física al cliente se registra primero: libera el producto terminado del inventario y genera el costo de venta real. No se puede facturar sin esto.</p>

          <div v-if="!related.delivery_note">
            <button :disabled="advancing || related.sales_order?.docstatus !== 1" class="px-4 py-2 text-sm font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50" @click="generarRemision">Crear remisión</button>
            <p v-if="related.sales_order?.docstatus !== 1" class="text-[11px] text-ink-light mt-2">Primero valida la orden de venta.</p>
          </div>

          <div v-else-if="dnDoc" class="text-left bg-surface-raised/40 rounded-lg p-4 mt-2">
            <div class="flex items-center justify-between mb-3">
              <span class="text-sm font-semibold text-ink">{{ dnDoc.name }}</span>
              <span class="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700">Borrador</span>
            </div>
            <label class="field-label">Fecha de entrega</label>
            <input v-model="dnForm.posting_date" type="date" class="field-input mb-3" />
            <table class="w-full text-sm mb-3">
              <thead><tr class="text-left text-xs font-semibold text-ink-light border-b border-surface-border"><th class="py-2">Producto</th><th class="py-2 w-20 text-right">Cant.</th><th class="py-2">Almacén</th><th class="py-2 w-20 text-right">Disponible</th></tr></thead>
              <tbody>
                <tr v-for="it in dnDoc.items" :key="it.name" class="border-b border-surface-border/60">
                  <td class="py-1.5 pr-2">{{ it.item_name || it.item_code }}</td>
                  <td class="py-1.5 pr-2"><input v-model.number="it.qty" type="number" min="0" class="field-input text-right" /></td>
                  <td class="py-1.5 pr-2"><select v-model="it.warehouse" class="field-input"><option value="">— Selecciona —</option><option v-for="w in (dnDoc.warehouses || [])" :key="w.name" :value="w.name">{{ w.warehouse_name || w.name }}</option></select></td>
                  <td class="py-1.5 pr-2 text-right" :class="(it.available ?? 0) < it.qty ? 'text-red-600 font-semibold' : 'text-ink-muted'">{{ it.available ?? '—' }}</td>
                </tr>
              </tbody>
            </table>
            <p v-if="dnDoc.items.some(it => (it.available ?? 0) < it.qty)" class="text-[12px] text-red-600 mb-3 flex items-start gap-1.5"><svg class="w-4 h-4 flex-shrink-0 mt-px" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M5.07 19h13.86a2 2 0 001.71-3l-6.93-12a2 2 0 00-3.42 0l-6.93 12a2 2 0 001.71 3z"/></svg>No hay stock suficiente en el almacén elegido para esa cantidad.</p>
            <div class="flex items-center gap-2 flex-wrap">
              <button class="doc-action" @click="openPdf('Delivery Note', dnDoc.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>Vista previa</button>
              <div class="flex-1"></div>
              <button :disabled="advancing" class="doc-action" @click="guardarRemision">Guardar</button>
              <button :disabled="advancing" class="h-8 px-4 text-[13px] font-semibold text-white bg-brand-500 rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center gap-1.5" @click="validarRemision"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Validar remisión</button>
            </div>
          </div>
        </div>
      </div>

      <template v-else>
      <!-- Tabs: Venta (cliente) | Compras (proveedores) -->
      <div class="max-w-6xl mx-auto mb-4">
        <div class="flex items-center gap-1.5 bg-green-50 text-green-700 text-[12px] font-medium px-3 py-2 rounded-lg mb-3 w-max"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Remisión {{ related.delivery_note.name }} validada · mercancía entregada</div>
        <div class="flex items-center gap-1 bg-gray-100 rounded-lg p-0.5 w-max">
          <button class="px-3.5 py-1.5 rounded-md text-[13px] font-medium transition-colors" :class="factTab === 'venta' ? 'bg-white text-ink shadow-sm' : 'text-ink-muted hover:text-ink'" @click="factTab = 'venta'">Venta (cliente)</button>
          <button class="px-3.5 py-1.5 rounded-md text-[13px] font-medium transition-colors" :class="factTab === 'compras' ? 'bg-white text-ink shadow-sm' : 'text-ink-muted hover:text-ink'" @click="selectComprasTab">Compras (proveedores)</button>
        </div>
      </div>

      <!-- ── VENTA ── -->
      <div v-show="factTab === 'venta'" class="flex gap-5 items-start max-w-6xl mx-auto">

        <!-- Izquierda: datos de la factura -->
        <div class="w-80 flex-shrink-0 bg-white rounded-xl border border-surface-border p-5">
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
              <button class="doc-action justify-center" @click="openSend('Sales Invoice', related.sales_invoice.name, related.sales_invoice.contact_email)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>Enviar</button>
              <button class="doc-action justify-center" @click="downloadPdf('Sales Invoice', related.sales_invoice.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/></svg>Descargar</button>
              <button class="doc-action justify-center" @click="printDocView('Sales Invoice', related.sales_invoice.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2z"/></svg>Imprimir</button>
              <button class="doc-action justify-center" @click="openAssign('Sales Invoice', related.sales_invoice.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>Asignar</button>
            </div>
            <a class="doc-action justify-center w-full" :href="`/app/sales-invoice/${related.sales_invoice.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>Abrir en ERPNext</a>
          </div>
        </div>

        <!-- Derecha: vista previa del PDF -->
        <div class="flex-1 min-w-0 bg-white rounded-xl border border-surface-border overflow-hidden">
          <div v-if="!related.sales_invoice" class="flex flex-col items-center justify-center gap-2 text-ink-light" style="height: 78vh;">
            <svg class="w-10 h-10 text-gray-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 14l2 2 4-4m4 9V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2z"/></svg>
            <p class="text-[13px]">La vista previa aparecerá al generar la factura</p>
          </div>
          <div v-else style="height: 78vh; overflow: auto;">
            <iframe :key="previewKey" :src="printUrl('Sales Invoice', related.sales_invoice.name)" style="width: 143%; height: 143%; transform: scale(0.7); transform-origin: top left; border: 0;" title="Vista previa de la factura de venta"></iframe>
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
            <div class="w-72 flex-shrink-0 bg-white rounded-xl border border-surface-border p-4">
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
                <div class="grid grid-cols-2 gap-2 pt-1">
                  <button class="doc-action justify-center" @click="downloadPdf('Purchase Invoice', pinvDoc.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/></svg>Descargar</button>
                  <button class="doc-action justify-center" @click="printDocView('Purchase Invoice', pinvDoc.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2z"/></svg>Imprimir</button>
                </div>
                <a class="doc-action justify-center w-full" :href="`/app/purchase-invoice/${pinvDoc.name}`" target="_blank"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>Abrir en ERPNext</a>
              </div>
            </div>
            <div class="flex-1 min-w-0 bg-white rounded-xl border border-surface-border overflow-hidden" style="height: 78vh; overflow: auto;">
              <iframe :key="'pinv' + previewKey" :src="printUrl('Purchase Invoice', pinvDoc.name)" style="width: 143%; height: 143%; transform: scale(0.7); transform-origin: top left; border: 0;" title="Vista previa de la factura de compra"></iframe>
            </div>
          </div>
        </div>
      </div>
      </template>
    </div>

    <!-- Send modal -->
    <div v-if="sendModal.open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="sendModal.open = false">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md p-5">
        <p class="text-sm font-semibold text-ink mb-3">Enviar {{ sendModal.name }}</p>
        <label class="field-label">Para</label>
        <input v-model="sendModal.recipients" type="text" class="field-input mb-3" placeholder="correo@cliente.com" />
        <label class="field-label">Asunto</label>
        <input v-model="sendModal.subject" type="text" class="field-input mb-3" />
        <label class="field-label">Mensaje</label>
        <textarea v-model="sendModal.message" rows="3" class="field-input mb-4"></textarea>
        <div class="flex justify-end gap-2">
          <button class="px-3 py-1.5 text-[13px] text-ink-muted hover:bg-surface-raised rounded-lg" @click="sendModal.open = false">Cancelar</button>
          <button :disabled="!sendModal.recipients || sendModal.sending" class="px-4 py-1.5 text-[13px] font-medium text-white bg-brand-500 hover:bg-brand-600 disabled:opacity-50 rounded-lg flex items-center gap-2" @click="doSend">
            <svg v-if="sendModal.sending" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
            {{ sendModal.sending ? "Enviando…" : "Enviar" }}
          </button>
        </div>
      </div>
    </div>

    <!-- Assign modal -->
    <div v-if="assignModal.open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="assignModal.open = false">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm p-5">
        <p class="text-sm font-semibold text-ink mb-3">Asignar {{ assignModal.name }}</p>
        <div class="max-h-64 overflow-y-auto border border-surface-border rounded-lg divide-y divide-surface-border mb-4">
          <label v-for="u in cotDefaults.users" :key="u.name" class="flex items-center gap-2.5 px-3 py-2 text-[13px] cursor-pointer hover:bg-surface-raised">
            <input type="checkbox" :value="u.name" v-model="assignModal.selected" class="accent-brand-500" />
            <span>{{ u.full_name || u.name }}</span>
          </label>
        </div>
        <div class="flex justify-end gap-2">
          <button class="px-3 py-1.5 text-[13px] text-ink-muted hover:bg-surface-raised rounded-lg" @click="assignModal.open = false">Cancelar</button>
          <button :disabled="!assignModal.selected.length || assignModal.sending" class="px-4 py-1.5 text-[13px] font-medium text-white bg-brand-500 hover:bg-brand-600 disabled:opacity-50 rounded-lg flex items-center gap-2" @click="doAssign">
            <svg v-if="assignModal.sending" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
            {{ assignModal.sending ? "Asignando…" : "Asignar" }}
          </button>
        </div>
      </div>
    </div>

    <!-- PDF modal -->
    <div v-if="pdfModal.open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" @click.self="pdfModal.open = false">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-4xl flex flex-col overflow-hidden" style="height: 90vh;">
        <div class="flex items-center justify-between px-4 py-2.5 border-b border-surface-border flex-shrink-0">
          <span class="text-sm font-semibold text-ink truncate">{{ pdfModal.name }}</span>
          <div class="flex items-center gap-2 flex-shrink-0">
            <button class="doc-action" @click="printDocView(pdfModal.doctype, pdfModal.name)"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2z"/></svg>Imprimir</button>
            <button class="w-8 h-8 flex items-center justify-center rounded-lg text-ink-muted hover:bg-surface-raised" @click="pdfModal.open = false" aria-label="Cerrar"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button>
          </div>
        </div>
        <iframe :key="'pm' + previewKey" :src="printUrl(pdfModal.doctype, pdfModal.name)" class="flex-1 w-full" style="border: 0;" title="Vista previa del documento"></iframe>
      </div>
    </div>

    <Transition name="fade">
      <div v-if="toast.show" class="fixed bottom-5 right-5 z-50 px-4 py-3 rounded-lg text-sm font-medium shadow-lg" :class="toast.type === 'error' ? 'bg-red-600 text-white' : 'bg-green-600 text-white'">{{ toast.msg }}</div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import CosteoStepper from "@/components/CosteoStepper.vue";
import LinkInput from "@/components/LinkInput.vue";
import ConfirmDialog from "@/components/ConfirmDialog.vue";
import { db, call, openDesk as deskOpen, uploadFile, defaultPrintFormat } from "@/utils/frappe.js";

const ITEM_FILTERS = {
  terminado: [["item_group", "=", "Productos Terminados"]],
  mp:        [["item_group", "in", ["Materia prima", "Sub-Ensamblajes", "Consumible"]]],
  servicio:  [["item_group", "=", "Servicios"]],
  sub:       [["item_group", "in", ["Sub-Ensamblajes", "Productos Terminados"]]],
};
const TABS = [{ key: "materiales", label: "Materias primas" }, { key: "etapas", label: "Etapas de manufactura" }];
const ORDER = ["Borrador", "Cotizado", "Orden de Venta", "En Producción", "Completado"];

const route = useRoute();
const router = useRouter();
const isNew = computed(() => !route.params.name);
const loading = ref(!isNew.value);
const saving = ref(false);
const advancing = ref(false);

const actionsRef = ref(null);
const actionsOpen = ref(false);
const confirmDelete = reactive({ open: false, loading: false });
const confirmCancel = reactive({ open: false, loading: false });
const familias = ref([]);
const tplModal = reactive({ open: false, nombre: "", familia: "", saving: false });

const docName = ref(null);
const docStatus = ref("Borrador");
const docState = ref(0); // docstatus del Costeo: 0 borrador, 1 validado
const activeStep = ref(0);
const previewKey = ref(0); // fuerza recarga del iframe de preview
const related = reactive({ quotation: null, sales_order: null, delivery_note: null, sales_invoice: null });
const cotForm = reactive({ valid_till: "", payment_terms_template: "", tc_name: "" });
const soForm = reactive({ delivery_date: "", payment_terms_template: "", tc_name: "" });
const siForm = reactive({ posting_date: "", due_date: "", payment_terms_template: "", tc_name: "" });
const dnDoc = ref(null);
const dnForm = reactive({ posting_date: "" });
const prodComplete = reactive({ complete: false, total: 0, recibidas: 0 });
const factTab = ref("venta");
const compras = reactive({ materiales: [], maquila: [] });
const pinvSel = ref(null);
const pinvDoc = ref(null);
const pinvForm = reactive({ posting_date: "", due_date: "", bill_no: "", bill_date: "", payment_terms_template: "", tc_name: "" });
const cotDefaults = reactive({ payment_terms_templates: [], terms: [], users: [] });
const assignModal = reactive({ open: false, doctype: "", name: "", selected: [], sending: false });
const planDetail = ref(null);
const planWh = ref("");
const prepSteps = ref([]);
const downstream = ref({ mrs: [], wos: [], sub: [] });
const prodTab = ref(0);
const mrDetail = ref(null);
const mrItems = ref([]);
const mrSchedule = ref("");
const mrResults = ref({ ocs: [], rfq: null, sq: null });
const mrDocTab = ref(null);
const docCompra = ref(null);
const docCompraItems = ref([]);
const docCompraForm = reactive({ schedule_date: "", valid_till: "", payment_terms_template: "", tc_name: "" });
const ocSelected = ref("");
const DOC_COMPRA = {
  oc:  { doctype: "Purchase Order", label: "Orden de compra", desk: "purchase-order" },
  rfq: { doctype: "Request for Quotation", label: "Solicitud de cotización", desk: "request-for-quotation" },
  sq:  { doctype: "Supplier Quotation", label: "Presupuesto de proveedor", desk: "supplier-quotation" },
};
const reciboOcs = ref([]);
const reciboOcSel = ref("");
const reciboPr = ref(null);
const reciboItems = ref([]);
const reciboForm = reactive({ posting_date: "" });
const subOcs = ref([]);
const subSel = ref("");
const subPo = ref(null);
const subItems = ref([]);
const subForm = reactive({ schedule_date: "", payment_terms_template: "", tc_name: "" });
const subTab = ref(0);
const flujo = reactive({ po_validated: false, supplier: "", sco: null, transfer: { done: false, entries: [] }, receipts: [], warehouses: [], address_options: [], contact_options: [] });
const scoForm = reactive({ supplier_warehouse: "", set_warehouse: "", supplier_address: "", contact_person: "", shipping_address: "", distribute_additional_costs_based_on: "Qty" });
const scoCostos = ref([]);
const scr = ref(null);
const scrForm = reactive({ set_warehouse: "", rejected_warehouse: "", supplier_warehouse: "" });
const transDoc = ref(null);
const transForm = reactive({ from_warehouse: "", to_warehouse: "" });
const OM_CAB = ["t28", "t30", "t32", "t34", "t36", "t40", "t42", "t44"];
const OM_DAMA = ["t5", "t7", "t9", "t11", "t13", "t15", "t17"];
const omGeneral = reactive({ om_modelo: "", om_tela: "", om_color: "", om_color_principal: "", om_forro: "", om_combinacion: "", om_fecha_requerida: "", om_ubicacion: "", om_aberturas: 0, om_bordado: 0, om_estampado: 0, om_sublimado: 0, om_reflejante: 0, om_observaciones: "" });
const omCab = ref([]);
const omDama = ref([]);
const omProc = ref([]);
const omTablas = ref([]);
const omArchivos = ref([]);
const omUploading = ref(false);
const pdfModal = reactive({ open: false, doctype: "", name: "" });
const printFmtMap = reactive({}); // doctype -> formato de impresión predeterminado
async function ensurePrintFmt(doctype) {
  if (doctype in printFmtMap) return printFmtMap[doctype];
  printFmtMap[doctype] = "Standard"; // placeholder para evitar fetch duplicado
  printFmtMap[doctype] = await defaultPrintFormat(doctype);
  previewKey.value++; // recarga los iframes con el formato correcto
  return printFmtMap[doctype];
}

const form = reactive({ cliente: "", fecha: today(), compania: "", proyecto: "", familia_prenda: "", centro_de_costos: "", almacen_materias_primas: "", almacen_trabajo_en_proceso: "" });
const errors = reactive({});
const productos = ref([]);
const detalles = ref([]);
const etapas = ref([]);
const expandedTid = ref(null);
const tabState = ref({});
const toast = reactive({ show: false, msg: "", type: "success" });
const sendModal = reactive({ open: false, doctype: "", name: "", recipients: "", subject: "", message: "", sending: false });

// ── Computed ──
const headerSubtitle = computed(() => isNew.value ? "Completa los datos del costeo" : [form.cliente, form.familia_prenda].filter(Boolean).join(" · "));
const totalVenta = computed(() => productos.value.reduce((s, p) => s + (p.total_sales_price || 0), 0));
const totalCosto = computed(() => productos.value.reduce((s, p) => s + (p.total_unit_cost || 0) * (p.qty || 0), 0));
const margenPct = computed(() => { const v = totalVenta.value; return v > 0 ? Math.round(((v - totalCosto.value) / v) * 100) : 0; });

const cta = computed(() => ({
  "Borrador":       { label: "Pasar a cotización",        action: "cotizar" },
  "Cotizado":       { label: "Generar orden de venta",    action: "vender" },
  "Orden de Venta": { label: "Preparar producción",       action: "producir" },
  "En Producción":  { label: "Ir a facturar",             action: "facturar" },
  "Completado":     null,
}[docStatus.value] || null));

const checklist = computed(() => {
  const items = [
    { label: "Cliente y compañía", ok: !!(form.cliente && form.compania) },
    { label: "Al menos un producto con cantidad", ok: productos.value.some(p => p.finished_item && (p.qty || 0) > 0) },
  ];
  if (docStatus.value === "Orden de Venta") {
    items.push({ label: "Almacenes configurados", ok: !!(form.almacen_materias_primas && form.almacen_trabajo_en_proceso) });
    items.push({ label: "Materias primas con proveedor", ok: detalles.value.filter(d => d.concept_type === "Materia Prima" && d.item).every(d => d.supplier) });
    items.push({ label: "Etapas con servicio y proveedor", ok: etapas.value.filter(e => e.etapa).every(e => e.servicio && e.proveedor) });
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
  if (docStatus.value === "Orden de Venta") return related.sales_order?.docstatus === 1;
  if (docStatus.value === "En Producción") return prodComplete.complete;  // toda la maquila recibida
  return true;
});
const canAdvance = computed(() => checklist.value.every(i => i.ok) && phaseReady.value);
const quotValidated = computed(() => related.quotation?.docstatus === 1);
const soValidated = computed(() => related.sales_order?.docstatus === 1);
const siValidated = computed(() => related.sales_invoice?.docstatus === 1);
const dnValidated = computed(() => related.delivery_note?.docstatus === 1);
const pinvValidated = computed(() => pinvDoc.value?.docstatus === 1);
function facBadge(inv) {
  if (!inv) return { txt: "Sin factura", cls: "bg-gray-100 text-gray-500" };
  return inv.docstatus === 1 ? { txt: "Validada", cls: "bg-green-50 text-green-700" } : { txt: "Borrador", cls: "bg-amber-50 text-amber-700" };
}
const hasPlan = computed(() => !!planDetail.value);
const planValidated = computed(() => planDetail.value?.docstatus === 1);
const mrValidated = computed(() => mrDetail.value?.docstatus === 1);
const docCompraValidated = computed(() => docCompra.value?.docstatus === 1);
const docCompraHasRate = computed(() => docCompraItems.value.some(i => i.has_rate));
const anyOcValidated = computed(() => reciboOcs.value.length > 0);
const reciboValidated = computed(() => reciboPr.value?.docstatus === 1);
const subValidated = computed(() => subPo.value?.docstatus === 1);
const subHasRate = computed(() => subItems.value.some(i => i.has_rate));
const scoExists = computed(() => !!flujo.sco);
const scoValidated = computed(() => flujo.sco?.docstatus === 1);
const transferDone = computed(() => flujo.transfer?.done);
const transValidated = computed(() => transDoc.value?.docstatus === 1);
const scrValidated = computed(() => scr.value?.docstatus === 1);
const subSteps = computed(() => [
  { key: 0, label: "Orden de manufactura", done: subValidated.value, locked: false },
  { key: 1, label: "Orden de subcontratación", done: scoValidated.value, locked: false },
  { key: 2, label: "Transferencia de material", done: transferDone.value, locked: !scoValidated.value },
  { key: 3, label: "Recibo de subcontratación", done: scrValidated.value, locked: !transferDone.value },
]);
const subDone = computed(() => subOcs.value.length > 0 && subOcs.value.every(o => o.docstatus === 1));

// ── Helpers ──
let _seq = 0;
function uid() { return `_${++_seq}_${Date.now()}`; }
function today() { return new Date().toISOString().slice(0, 10); }
function fmtC(v) { return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(v || 0); }
function showToast(msg, type = "success") { toast.msg = msg; toast.type = type; toast.show = true; setTimeout(() => (toast.show = false), 3500); }
function goStep(idx) { activeStep.value = idx; }

// ── PDF / print helpers ──
function printUrl(doctype, name) { return `/printview?doctype=${encodeURIComponent(doctype)}&name=${encodeURIComponent(name)}&format=${encodeURIComponent(printFmtMap[doctype] || "Standard")}&no_letterhead=0&trigger_print=0&_v=${previewKey.value}`; }
function printDocView(doctype, name) { window.open(printUrl(doctype, name).replace("trigger_print=0", "trigger_print=1"), "_blank"); }
// Descargar via impresión del navegador (Guardar como PDF): no depende de wkhtmltopdf.
function downloadPdf(doctype, name) { window.open(printUrl(doctype, name).replace("trigger_print=0", "trigger_print=1"), "_blank"); }

// ── Send ──
function openSend(doctype, name, email) {
  sendModal.doctype = doctype; sendModal.name = name;
  sendModal.recipients = email || "";
  sendModal.subject = `${doctype === "Quotation" ? "Cotización" : doctype} ${name}`;
  sendModal.message = "Estimado cliente, adjunto encontrará el documento. Quedamos atentos.";
  sendModal.open = true;
}
async function doSend() {
  sendModal.sending = true;
  try {
    await call("costeo_yelke.api.costeo_api.enviar_por_correo", { doctype: sendModal.doctype, name: sendModal.name, recipients: sendModal.recipients, subject: sendModal.subject, message: sendModal.message });
    sendModal.open = false;
    showToast("Correo enviado");
  } catch (e) { showToast(e.message || "No se pudo enviar", "error"); }
  finally { sendModal.sending = false; }
}

// ── Tabs / filters ──
function activeTab(tid) { return tabState.value[tid] || "materiales"; }
function setTab(tid, tab) { tabState.value[tid] = tab; }
function tabCount(prod, tab) { if (!prod.finished_item) return 0; if (tab === "materiales") return materialesDe(prod.finished_item).length; if (tab === "etapas") return etapasDe(prod.finished_item).length; return 0; }
function materialesDe(fi) { return detalles.value.filter(d => d.finished_item === fi && d.concept_type === "Materia Prima"); }
function etapasDe(fi) { return etapas.value.filter(e => e.producto_terminado === fi); }

// ── Product / detail / stage ──
function addProducto() { const p = { _tid: uid(), _image: "", finished_item: "", qty: 1, shipping_cost: 0, overhead_pct: 0, margin_pct: 0, material_cost: 0, services_cost: 0, overhead_amt: 0, total_unit_cost: 0, unit_sales_price: 0, total_sales_price: 0 }; productos.value.push(p); expandedTid.value = p._tid; }
function removeProducto(idx) { const prod = productos.value[idx]; if (!prod) return; detalles.value = detalles.value.filter(d => d.finished_item !== prod.finished_item); etapas.value = etapas.value.filter(e => e.producto_terminado !== prod.finished_item); productos.value.splice(idx, 1); if (expandedTid.value === prod._tid) expandedTid.value = null; }
function toggleProduct(tid) { expandedTid.value = expandedTid.value === tid ? null : tid; }
async function onProductoItemChange(prod) { recalcProducto(prod); prod._image = await fetchItemImage(prod.finished_item); }
function addDetalle(prod, type) { detalles.value.push({ _tid: uid(), finished_item: prod.finished_item, concept_type: type, item: "", supplier: "", supplier_qty: 0, unit_price: 0, total: 0, etapa: "", internal_qty: 0, _supplierOptions: [] }); }
function removeDetalle(d, prod) { const i = detalles.value.findIndex(x => x._tid === d._tid); if (i !== -1) detalles.value.splice(i, 1); recalcProducto(prod); }
function recalcDetalle(d, prod) { d.total = (d.supplier_qty || d.internal_qty || 0) * (d.unit_price || 0); recalcProducto(prod); }
function addEtapa(prod) { etapas.value.push({ _tid: uid(), producto_terminado: prod.finished_item, etapa: "", servicio: "", proveedor: "", precio_servicio: 0, subensamblaje: "" }); }
function removeEtapa(e, prod) { const i = etapas.value.findIndex(x => x._tid === e._tid); if (i !== -1) etapas.value.splice(i, 1); if (prod) recalcProducto(prod); }
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
  const stageServ = etapas.value.filter(e => e.producto_terminado === fi && e.servicio).reduce((s, e) => s + (e.precio_servicio || 0), 0);
  prod.services_cost = detServ + stageServ;
  const base = prod.material_cost + prod.services_cost + (prod.shipping_cost || 0);
  prod.overhead_amt = base * ((prod.overhead_pct || 0) / 100);
  prod.total_unit_cost = base + prod.overhead_amt;
  const m = (prod.margin_pct || 0) / 100;
  const price = (m > 0 && m < 1) ? prod.total_unit_cost / (1 - m) : prod.total_unit_cost;
  prod.unit_sales_price = Math.round(price * 100) / 100;
  prod.total_sales_price = prod.unit_sales_price * (prod.qty || 0);
}
// Editar el precio unitario → recalcula el margen (sentido inverso, sin sobrescribir el precio)
function onPriceChange(prod) {
  const price = prod.unit_sales_price || 0;
  const cost = prod.total_unit_cost || 0;
  let m = price > 0 ? ((price - cost) / price) * 100 : 0;
  if (m < 0) m = 0;
  prod.margin_pct = Math.round(m * 100) / 100;
  prod.total_sales_price = price * (prod.qty || 0);
}
async function fetchItemImage(code) { if (!code) return ""; try { const rows = await db.getList("Item", { fields: ["image"], filters: [["name", "=", code]], limit: 1 }); return rows?.[0]?.image || ""; } catch { return ""; } }
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
    recalcDetalle(d, prod);
  } catch { /* ignore */ }
}
function onSupplierChange(d, prod) {
  const opt = (d._supplierOptions || []).find(o => o.supplier === d.supplier);
  if (opt) d.unit_price = opt.rate;
  recalcDetalle(d, prod);
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
  for (const f of ["cliente", "fecha", "compania", "centro_de_costos", "almacen_materias_primas", "almacen_trabajo_en_proceso"]) { if (!form[f]) { errors[f] = "Requerido"; ok = false; } }
  if (!productos.value.some(p => p.finished_item && (p.qty || 0) > 0)) { showToast("Agrega al menos un producto con cantidad > 0", "error"); ok = false; }
  return ok;
}
function stripLocal(obj) { const out = {}; for (const k in obj) { if (!k.startsWith("_")) out[k] = obj[k]; } return out; }
function buildPayload() {
  return {
    doctype: "Costeo", cliente: form.cliente, fecha: form.fecha, "compañia": form.compania,
    proyecto: form.proyecto || "", familia_prenda: form.familia_prenda || "", centro_de_costos: form.centro_de_costos,
    almacen_materias_primas: form.almacen_materias_primas, almacen_trabajo_en_proceso: form.almacen_trabajo_en_proceso,
    costeo_status: docStatus.value || "Borrador",
    costeo_producto: productos.value.map(stripLocal),
    costeo_producto_detalle: detalles.value.map(stripLocal),
    tabla_etapas_costeo: etapas.value.map(stripLocal),
  };
}
async function fillFromDoc(data) {
  docName.value = data.name;
  docStatus.value = data.costeo_status || "Borrador";
  docState.value = data.docstatus || 0;
  form.cliente = data.cliente || ""; form.fecha = data.fecha || today(); form.compania = data["compañia"] || "";
  form.proyecto = data.proyecto || ""; form.familia_prenda = data.familia_prenda || "";
  form.centro_de_costos = data.centro_de_costos || ""; form.almacen_materias_primas = data.almacen_materias_primas || ""; form.almacen_trabajo_en_proceso = data.almacen_trabajo_en_proceso || "";
  productos.value = (data.costeo_producto || []).map(r => ({ _tid: uid(), _image: "", ...r }));
  detalles.value = (data.costeo_producto_detalle || []).map(r => ({ _tid: uid(), _supplierOptions: [], ...r }));
  etapas.value = (data.tabla_etapas_costeo || []).map(r => ({ _tid: uid(), ...r }));
  for (const p of productos.value) { if (p.finished_item) p._image = await fetchItemImage(p.finished_item); }
  hydrateSupplierOptions();
}

async function loadRelated() {
  if (!docName.value) return;
  try {
    const r = await call("costeo_yelke.api.costeo_api.get_costeo_related", { costeo: docName.value });
    related.quotation = r.quotation; related.sales_order = r.sales_order;
    related.delivery_note = r.delivery_note; related.sales_invoice = r.sales_invoice;
    if (r.quotation) ensurePrintFmt("Quotation");
    if (r.sales_order) ensurePrintFmt("Sales Order");
    if (r.delivery_note) {
      ensurePrintFmt("Delivery Note");
      dnForm.posting_date = r.delivery_note.posting_date || "";
      await loadRemisionDetalle(r.delivery_note.name);
    }
    if (r.sales_invoice) {
      ensurePrintFmt("Sales Invoice");
      siForm.posting_date = r.sales_invoice.posting_date || "";
      siForm.due_date = r.sales_invoice.due_date || "";
      siForm.payment_terms_template = r.sales_invoice.payment_terms_template || "";
      siForm.tc_name = r.sales_invoice.tc_name || "";
    }
    loadProdComplete();
    // El backend reconcilia el estado si borraron documentos (p. ej. la cotización) desde ERPNext
    if (r.costeo_status && r.costeo_status !== docStatus.value) {
      docStatus.value = r.costeo_status;
      const idx = ORDER.indexOf(r.costeo_status);
      if (idx >= 0 && activeStep.value > idx) activeStep.value = idx;
    }
    if (r.quotation) {
      cotForm.valid_till = r.quotation.valid_till || "";
      cotForm.payment_terms_template = r.quotation.payment_terms_template || "";
      cotForm.tc_name = r.quotation.tc_name || "";
    }
    if (r.sales_order) {
      soForm.delivery_date = r.sales_order.delivery_date || "";
      soForm.payment_terms_template = r.sales_order.payment_terms_template || "";
      soForm.tc_name = r.sales_order.tc_name || "";
    }
  } catch { /* ignore */ }
}
async function loadProdComplete() {
  if (!docName.value) { return; }
  try {
    const r = await call("costeo_yelke.api.costeo_api.produccion_completa", { costeo: docName.value });
    prodComplete.complete = !!r.complete; prodComplete.total = r.total || 0; prodComplete.recibidas = r.recibidas || 0;
  } catch { /* ignore */ }
}
// ── Nota de remisión (entrega) ──
async function loadRemisionDetalle(name) {
  try { dnDoc.value = await call("costeo_yelke.api.costeo_api.get_remision", { name }); }
  catch { dnDoc.value = null; }
}
async function generarRemision() {
  if (isNew.value) { showToast("Guarda el costeo primero", "error"); return; }
  if (related.sales_order?.docstatus !== 1) { showToast("Primero valida la orden de venta", "error"); return; }
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.crear_remision", { costeo: docName.value });
    await loadRelated();
    showToast("Remisión creada (borrador)");
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
    });
    await call("costeo_yelke.api.costeo_api.validar_documento", { doctype: "Delivery Note", name: dnDoc.value.name });
    await loadRelated();
    showToast("Remisión validada · mercancía entregada al cliente");
  } catch (e) { showToast(e.message || "No se pudo validar la remisión", "error"); }
  finally { advancing.value = false; }
}

async function generarFactura() {
  if (isNew.value) { showToast("Guarda el costeo primero", "error"); return; }
  if (related.sales_order?.docstatus !== 1) { showToast("Primero valida la orden de venta", "error"); return; }
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.crear_factura_venta", {
      costeo: docName.value,
      posting_date: siForm.posting_date || null, due_date: siForm.due_date || null,
      payment_terms_template: siForm.payment_terms_template || null, tc_name: siForm.tc_name || null,
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
async function loadPlan() {
  if (!docName.value) return;
  try {
    const r = await call("costeo_yelke.api.costeo_api.get_plan_detail", { costeo: docName.value });
    planDetail.value = r.plan;
    if (r.plan) { planWh.value = r.plan.for_warehouse || ""; await loadSolicitud(); await loadRecibos(); await loadSubcontratos(); }
  } catch { /* ignore */ }
}
async function loadSolicitud() {
  if (!planDetail.value) return;
  try {
    const r = await call("costeo_yelke.api.costeo_api.get_solicitud_material", { plan: planDetail.value.name });
    mrDetail.value = r.detail;
    if (r.detail) {
      mrItems.value = r.detail.items.map(i => ({ ...i }));
      mrSchedule.value = r.detail.schedule_date || "";
      mrResults.value = { ocs: r.detail.linked_ocs || [], rfq: mrResults.value.rfq, sq: mrResults.value.sq };
    } else {
      mrItems.value = []; mrSchedule.value = "";
    }
    mrDocTab.value = null; docCompra.value = null;
  } catch { /* ignore */ }
}
function goProdTab(idx) {
  if (idx === 1 && !planValidated.value) return;
  if (idx === 2 && !anyOcValidated.value) return;
  if (idx === 3 && !planValidated.value) return;
  prodTab.value = idx;
  if (idx === 2) loadRecibos();
  if (idx === 3) loadSubcontratos();
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
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.validar_documento", { doctype: "Material Request", name: mrDetail.value.name });
    await loadSolicitud();
    showToast("Solicitud validada");
  } catch (e) { showToast(e.message || "No se pudo validar", "error"); }
  finally { advancing.value = false; }
}
async function selectDocTab(tab) {
  if (!mrValidated.value) return;
  mrDocTab.value = tab;
  advancing.value = true;
  try {
    if (tab === "oc") {
      if (!mrResults.value.ocs.length) {
        const r = await call("costeo_yelke.api.costeo_api.mr_crear_oc", { mr: mrDetail.value.name });
        mrResults.value.ocs = r.purchase_orders || [];
      }
      ocSelected.value = mrResults.value.ocs.includes(ocSelected.value) ? ocSelected.value : (mrResults.value.ocs[0] || "");
      if (ocSelected.value) await loadDocCompra("Purchase Order", ocSelected.value);
    } else if (tab === "rfq") {
      if (!mrResults.value.rfq) {
        const r = await call("costeo_yelke.api.costeo_api.mr_crear_rfq", { mr: mrDetail.value.name });
        mrResults.value.rfq = r.rfq;
      }
      if (mrResults.value.rfq) await loadDocCompra("Request for Quotation", mrResults.value.rfq);
    } else if (tab === "sq") {
      if (!mrResults.value.sq) {
        const r = await call("costeo_yelke.api.costeo_api.mr_crear_presupuesto_proveedor", { mr: mrDetail.value.name });
        mrResults.value.sq = r.supplier_quotation;
      }
      if (mrResults.value.sq) await loadDocCompra("Supplier Quotation", mrResults.value.sq);
    }
  } catch (e) { showToast(e.message || "Error", "error"); }
  finally { advancing.value = false; }
}
async function loadDocCompra(doctype, name) {
  const r = await call("costeo_yelke.api.costeo_api.get_documento_compra", { doctype, name });
  docCompra.value = r;
  ensurePrintFmt(doctype);
  docCompraItems.value = (r.items || []).map(i => ({ ...i }));
  docCompraForm.schedule_date = r.schedule_date || "";
  docCompraForm.valid_till = r.valid_till || "";
  docCompraForm.payment_terms_template = r.payment_terms_template || "";
  docCompraForm.tc_name = r.tc_name || "";
  previewKey.value++;
}
async function selectOC(po) { ocSelected.value = po; advancing.value = true; try { await loadDocCompra("Purchase Order", po); } finally { advancing.value = false; } }
async function guardarDocCompra() {
  if (!docCompra.value) return;
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.guardar_documento_compra", {
      doctype: docCompra.value.doctype, name: docCompra.value.name,
      schedule_date: docCompraForm.schedule_date || null, valid_till: docCompraForm.valid_till || null,
      payment_terms_template: docCompraForm.payment_terms_template || null, tc_name: docCompraForm.tc_name || null,
      items: JSON.stringify(docCompraItems.value),
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
    await call("costeo_yelke.api.costeo_api.validar_documento", { doctype: docCompra.value.doctype, name: docCompra.value.name });
    await loadDocCompra(docCompra.value.doctype, docCompra.value.name);
    showToast("Validado");
  } catch (e) { showToast(e.message || "No se pudo validar", "error"); }
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

// ── Recibo de compra ──
async function loadRecibos() {
  if (!planDetail.value) return;
  try {
    const r = await call("costeo_yelke.api.costeo_api.get_recibos", { plan: planDetail.value.name });
    reciboOcs.value = r.ocs || [];
    if (!reciboOcs.value.some(o => o.name === reciboOcSel.value)) reciboOcSel.value = reciboOcs.value[0]?.name || "";
    const sel = reciboOcs.value.find(o => o.name === reciboOcSel.value);
    if (sel && sel.receipts.length) await loadRecibo(sel.receipts[0]);
    else reciboPr.value = null;
  } catch { /* ignore */ }
}
async function selectReciboOc(po) {
  reciboOcSel.value = po;
  const sel = reciboOcs.value.find(o => o.name === po);
  if (sel && sel.receipts.length) await loadRecibo(sel.receipts[0]);
  else reciboPr.value = null;
}
async function loadRecibo(pr) {
  const r = await call("costeo_yelke.api.costeo_api.get_documento_compra", { doctype: "Purchase Receipt", name: pr });
  reciboPr.value = r;
  reciboItems.value = (r.items || []).map(i => ({ ...i }));
  reciboForm.posting_date = r.posting_date || "";
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
    });
    await loadRecibo(reciboPr.value.name);
    showToast("Recibo guardado");
  } catch (e) { showToast(e.message || "Error al guardar", "error"); }
  finally { advancing.value = false; }
}
async function validarRecibo() {
  if (!reciboPr.value) return;
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.validar_documento", { doctype: "Purchase Receipt", name: reciboPr.value.name });
    await loadRecibo(reciboPr.value.name);
    await loadRecibos();
    showToast("Recibo validado — inventario actualizado");
  } catch (e) { showToast(e.message || "No se pudo validar", "error"); }
  finally { advancing.value = false; }
}

// ── Subcontratación (maquila) ──
async function loadSubcontratos() {
  if (!planDetail.value) return;
  try {
    const r = await call("costeo_yelke.api.costeo_api.get_subcontratos", { plan: planDetail.value.name });
    subOcs.value = r.ocs || [];
    if (!subOcs.value.some(o => o.name === subSel.value)) subSel.value = subOcs.value[0]?.name || "";
    if (subSel.value) await loadSub(subSel.value); else subPo.value = null;
  } catch { /* ignore */ }
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
  subItems.value = (r.items || []).map(i => ({ ...i }));
  subForm.schedule_date = r.schedule_date || "";
  subForm.payment_terms_template = r.payment_terms_template || "";
  subForm.tc_name = r.tc_name || "";
  previewKey.value++;
  subTab.value = 0;
  await loadOm(po);
  await loadFlujo(po);
}
function emptyTalla(sizes) { const o = { linea: "Cantidad", total: 0 }; sizes.forEach(s => (o[s] = 0)); return o; }

function goSubTab(step) {
  if (step.locked) { showToast("Completa el paso anterior primero", "error"); return; }
  subTab.value = step.key;
}

async function loadFlujo(po) {
  try {
    const r = await call("costeo_yelke.api.costeo_api.sub_get_flujo", { po });
    Object.assign(flujo, { po_validated: r.po_validated, supplier: r.supplier, sco: r.sco, transfer: r.transfer, receipts: r.receipts, warehouses: r.warehouses || [], address_options: r.address_options || [], contact_options: r.contact_options || [] });
    if (r.sco) {
      scoForm.supplier_warehouse = r.sco.supplier_warehouse || "";
      scoForm.set_warehouse = r.sco.set_warehouse || "";
      scoForm.supplier_address = r.sco.supplier_address || "";
      scoForm.contact_person = r.sco.contact_person || "";
      scoForm.shipping_address = r.sco.shipping_address || "";
      scoForm.distribute_additional_costs_based_on = r.sco.distribute_additional_costs_based_on || "Qty";
      scoCostos.value = (r.sco.additional_costs || []).map(c => ({ ...c }));
    }
    if ((r.receipts || []).length) { await loadScr(r.receipts[0].name); }
    else { scr.value = null; }
    const te = (r.transfer?.entries || []);
    const target = te.find(e => e.docstatus === 0) || te[te.length - 1];
    if (target) { await loadTrans(target.name); } else { transDoc.value = null; }
  } catch { /* ignore */ }
}
async function loadTrans(name) {
  try {
    const r = await call("costeo_yelke.api.costeo_api.sub_get_transferencia", { stock_entry: name });
    transDoc.value = r;
    transForm.from_warehouse = r.from_warehouse || r.items?.[0]?.s_warehouse || r.recommended_source || "";
    transForm.to_warehouse = r.to_warehouse || r.items?.[0]?.t_warehouse || "";
  } catch { /* ignore */ }
}

async function crearSco() {
  if (!subPo.value) return;
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.sub_crear_sco", { po: subPo.value.name });
    await loadFlujo(subPo.value.name);
    showToast("Orden de subcontratación creada");
  } catch (e) { showToast(e.message || "No se pudo crear", "error"); }
  finally { advancing.value = false; }
}
async function guardarSco() {
  if (!flujo.sco) return;
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.sub_guardar_sco", { sco: flujo.sco.name, campos: JSON.stringify(scoForm), costos: JSON.stringify(scoCostos.value) });
    await loadFlujo(subPo.value.name);
    showToast("Orden de subcontratación guardada");
  } catch (e) { showToast(e.message || "Error al guardar", "error"); }
  finally { advancing.value = false; }
}
async function validarSco() {
  if (!flujo.sco) return;
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.sub_guardar_sco", { sco: flujo.sco.name, campos: JSON.stringify(scoForm), costos: JSON.stringify(scoCostos.value) });
    await call("costeo_yelke.api.costeo_api.sub_validar_sco", { sco: flujo.sco.name });
    await loadFlujo(subPo.value.name);
    showToast("Orden de subcontratación validada");
  } catch (e) { showToast(e.message || "No se pudo validar", "error"); }
  finally { advancing.value = false; }
}
function addCosto() { scoCostos.value.push({ description: "", amount: 0, expense_account: "" }); }
function removeCosto(i) { scoCostos.value.splice(i, 1); }

async function transferirMaterial() {
  if (!flujo.sco) return;
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.sub_transferir_material", { sco: flujo.sco.name });
    await loadFlujo(subPo.value.name);
    showToast("Transferencia creada en borrador · revisa almacenes y valida");
  } catch (e) { showToast(e.message || "No se pudo crear la transferencia", "error"); }
  finally { advancing.value = false; }
}
async function guardarTrans() {
  if (!transDoc.value) return;
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.sub_guardar_transferencia", {
      stock_entry: transDoc.value.name,
      from_warehouse: transForm.from_warehouse || null,
      to_warehouse: transForm.to_warehouse || null,
      items: JSON.stringify(transDoc.value.items),
    });
    await loadTrans(transDoc.value.name);
    showToast("Transferencia guardada");
  } catch (e) { showToast(e.message || "Error al guardar", "error"); }
  finally { advancing.value = false; }
}
async function validarTransferencia() {
  if (!transDoc.value) return;
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.sub_guardar_transferencia", {
      stock_entry: transDoc.value.name,
      from_warehouse: transForm.from_warehouse || null,
      to_warehouse: transForm.to_warehouse || null,
      items: JSON.stringify(transDoc.value.items),
    });
    await call("costeo_yelke.api.costeo_api.sub_validar_transferencia", { stock_entry: transDoc.value.name });
    await loadFlujo(subPo.value.name);
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
  if (!flujo.sco) return;
  advancing.value = true;
  try {
    const r = await call("costeo_yelke.api.costeo_api.sub_crear_recibo", { sco: flujo.sco.name });
    await loadFlujo(subPo.value.name);
    if (r.scr) await loadScr(r.scr);
    subTab.value = 3;
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
  } catch { /* ignore */ }
}
async function guardarScr() {
  if (!scr.value) return;
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.sub_guardar_recibo", { scr: scr.value.name, set_warehouse: scrForm.set_warehouse || null, rejected_warehouse: scrForm.rejected_warehouse || null, supplier_warehouse: scrForm.supplier_warehouse || null, items: JSON.stringify(scr.value.items) });
    await loadScr(scr.value.name);
    showToast("Recibo guardado");
  } catch (e) { showToast(e.message || "Error al guardar", "error"); }
  finally { advancing.value = false; }
}
async function validarScr() {
  if (!scr.value) return;
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.sub_guardar_recibo", { scr: scr.value.name, set_warehouse: scrForm.set_warehouse || null, rejected_warehouse: scrForm.rejected_warehouse || null, supplier_warehouse: scrForm.supplier_warehouse || null, items: JSON.stringify(scr.value.items) });
    await call("costeo_yelke.api.costeo_api.validar_documento", { doctype: "Subcontracting Receipt", name: scr.value.name });
    await loadFlujo(subPo.value.name);
    await loadProdComplete();  // desbloquea "Ir a facturar" si ya se recibió toda la maquila
    showToast("Recibo de subcontratación validado · producto en inventario");
  } catch (e) { showToast(e.message || "No se pudo validar", "error"); }
  finally { advancing.value = false; }
}
function tallaTotal(row, sizes) { return sizes.reduce((s, k) => s + (Number(row[k]) || 0), 0); }
async function loadOm(po) {
  try {
    const r = await call("costeo_yelke.api.costeo_api.get_om", { po });
    Object.assign(omGeneral, r.general);
    omCab.value = r.tallas_caballero.length ? r.tallas_caballero : [emptyTalla(OM_CAB)];
    omDama.value = r.tallas_dama.length ? r.tallas_dama : [emptyTalla(OM_DAMA)];
    omProc.value = r.procesos || [];
    omTablas.value = r.tablas || [];
    omArchivos.value = r.archivos || [];
  } catch { /* ignore */ }
}
async function guardarOm() {
  if (!subPo.value) return;
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.guardar_om", {
      po: subPo.value.name,
      general: JSON.stringify(omGeneral),
      tallas_caballero: JSON.stringify(omCab.value),
      tallas_dama: JSON.stringify(omDama.value),
      procesos: JSON.stringify(omProc.value),
      tablas: JSON.stringify(omTablas.value),
      archivos: JSON.stringify(omArchivos.value),
    });
    await loadOm(subPo.value.name);
    showToast("Orden de manufactura guardada");
  } catch (e) { showToast(e.message || "Error al guardar", "error"); }
  finally { advancing.value = false; }
}
function addProceso() { omProc.value.push({ proceso: "", nombre_proceso: "", ubicacion: "", colores: "" }); }
function removeProceso(i) { omProc.value.splice(i, 1); }

// --- Editor de tablas de medidas flexibles ---
function nextId(prefix, existing) {
  let max = 0;
  (existing || []).forEach((v) => { const m = new RegExp(`^${prefix}(\\d+)$`).exec(String(v || "")); if (m) max = Math.max(max, parseInt(m[1], 10)); });
  return `${prefix}${max + 1}`;
}
function addTabla() {
  omTablas.value.push({ name: `Tabla ${omTablas.value.length + 1}`, unit: "", columns: ["c1"], rows: [{ id: "r1", cells: { c1: "" } }] });
}
function removeTabla(ti) { omTablas.value.splice(ti, 1); }
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

// --- Archivos / diagramas ---
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
async function openPdf(doctype, name) {
  pdfModal.doctype = doctype; pdfModal.name = name;
  await ensurePrintFmt(doctype);
  previewKey.value++; pdfModal.open = true;
}
async function guardarSub() {
  if (!subPo.value) return;
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.guardar_documento_compra", {
      doctype: "Purchase Order", name: subPo.value.name,
      schedule_date: subForm.schedule_date || null, payment_terms_template: subForm.payment_terms_template || null,
      tc_name: subForm.tc_name || null, items: JSON.stringify(subItems.value),
    });
    await call("costeo_yelke.api.costeo_api.guardar_om", {
      po: subPo.value.name, general: JSON.stringify(omGeneral),
      tallas_caballero: JSON.stringify(omCab.value), tallas_dama: JSON.stringify(omDama.value),
      procesos: JSON.stringify(omProc.value),
      tablas: JSON.stringify(omTablas.value), archivos: JSON.stringify(omArchivos.value),
    });
    await loadSub(subPo.value.name);
    showToast("Guardado (orden + manufactura)");
  } catch (e) { showToast(e.message || "Error al guardar", "error"); }
  finally { advancing.value = false; }
}
async function validarSub() {
  if (!subPo.value) return;
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.validar_documento", { doctype: "Purchase Order", name: subPo.value.name });
    await loadSub(subPo.value.name);
    await loadSubcontratos();
    showToast("Orden de subcontrato validada");
  } catch (e) { showToast(e.message || "No se pudo validar", "error"); }
  finally { advancing.value = false; }
}
async function prepararProduccion() {
  if (isNew.value) { showToast("Guarda el costeo primero", "error"); return; }
  advancing.value = true;
  try {
    const r = await call("costeo_yelke.api.costeo_api.preparar_produccion", { costeo: docName.value });
    prepSteps.value = r.steps || [];
    if (ORDER.indexOf(docStatus.value) < 3) docStatus.value = "En Producción";
    await loadPlan();
    showToast("Plan de producción listo");
  } catch (e) { showToast(e.message || "Error al preparar producción", "error"); }
  finally { advancing.value = false; }
}
async function obtenerMateriasPrimas() {
  if (!planDetail.value) return;
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.plan_obtener_materias_primas", { plan: planDetail.value.name, warehouse: planWh.value || null });
    await loadPlan();
    showToast("Materias primas actualizadas");
  } catch (e) { showToast(e.message || "Error", "error"); }
  finally { advancing.value = false; }
}
async function guardarPlan() {
  if (!planDetail.value) return;
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.guardar_plan", { plan: planDetail.value.name, for_warehouse: planWh.value || null });
    await loadPlan();
    showToast("Plan guardado");
  } catch (e) { showToast(e.message || "Error al guardar", "error"); }
  finally { advancing.value = false; }
}
async function validarPlan() {
  if (!planDetail.value) return;
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.validar_documento", { doctype: "Production Plan", name: planDetail.value.name });
    await loadPlan();
    showToast("Plan validado");
  } catch (e) { showToast(e.message || "No se pudo validar el plan", "error"); }
  finally { advancing.value = false; }
}
async function crearSolicitudMaterial() {
  advancing.value = true;
  try {
    const r = await call("costeo_yelke.api.costeo_api.plan_crear_solicitud_material", { plan: planDetail.value.name });
    downstream.value.mrs = r.material_requests || [];
    showToast(`${(r.material_requests || []).length} solicitud(es) de material creada(s)`);
  } catch (e) { showToast(e.message || "Error", "error"); }
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
async function crearSubcontratacion() {
  advancing.value = true;
  try {
    const r = await call("costeo_yelke.api.costeo_api.plan_crear_subcontratacion", { plan: planDetail.value.name });
    downstream.value.sub = r.purchase_orders || [];
    showToast(`${(r.purchase_orders || []).length} orden(es) de subcontrato creada(s)`);
  } catch (e) { showToast(e.message || "Error", "error"); }
  finally { advancing.value = false; }
}

async function saveDoc() {
  if (!validate()) return;
  saving.value = true;
  try {
    const payload = buildPayload();
    if (isNew.value) { const created = await db.create("Costeo", payload); router.replace({ name: "CosteoDetail", params: { name: created.name } }); await fillFromDoc(created); showToast("Costeo creado"); }
    else { const updated = await db.update("Costeo", docName.value, payload); await fillFromDoc(updated); showToast("Cambios guardados"); }
  } catch (e) { showToast(e.message || "Error al guardar", "error"); }
  finally { saving.value = false; }
}

// ── Advance ──
async function advance() {
  if (isNew.value) { showToast("Guarda el costeo primero", "error"); return; }
  const c = cta.value; if (!c) return;
  if (!canAdvance.value) { showToast("Completa los pendientes antes de avanzar", "error"); return; }
  advancing.value = true;
  try {
    if (c.action === "cotizar") { await call("costeo_yelke.api.costeo_api.crear_cotizacion", { costeo: docName.value }); docStatus.value = "Cotizado"; showToast("Cotización creada"); }
    else if (c.action === "vender") { await call("costeo_yelke.api.costeo_api.crear_orden_venta", { costeo: docName.value }); docStatus.value = "Orden de Venta"; showToast("Orden de venta creada"); }
    else if (c.action === "producir") {
      const r = await call("costeo_yelke.api.costeo_api.preparar_produccion", { costeo: docName.value });
      prepSteps.value = r.steps || [];
      docStatus.value = "En Producción";
      await loadPlan();
      showToast("Producción preparada");
    }
    else if (c.action === "facturar") {
      activeStep.value = 4;
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
    await call("costeo_yelke.api.costeo_api.crear_orden_venta", {
      costeo: docName.value,
      delivery_date: soForm.delivery_date || null,
      payment_terms_template: soForm.payment_terms_template || null,
      tc_name: soForm.tc_name || null,
    });
    if (ORDER.indexOf(docStatus.value) < 2) docStatus.value = "Orden de Venta";
    await loadRelated();
    previewKey.value++;
    showToast("Orden de venta guardada como borrador");
  } catch (e) { showToast(e.message || "No se pudo guardar la orden de venta", "error"); }
  finally { advancing.value = false; }
}
async function guardarCambiosOrdenVenta() {
  if (!related.sales_order) return;
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.actualizar_orden_venta", {
      name: related.sales_order.name,
      delivery_date: soForm.delivery_date || null,
      payment_terms_template: soForm.payment_terms_template || null,
      tc_name: soForm.tc_name || null,
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
    await call("costeo_yelke.api.costeo_api.crear_cotizacion", {
      costeo: docName.value,
      valid_till: cotForm.valid_till || null,
      payment_terms_template: cotForm.payment_terms_template || null,
      tc_name: cotForm.tc_name || null,
    });
    if (ORDER.indexOf(docStatus.value) < 1) docStatus.value = "Cotizado";
    await loadRelated();
    previewKey.value++;
    showToast("Cotización guardada como borrador");
  } catch (e) { showToast(e.message || "No se pudo guardar la cotización", "error"); }
  finally { advancing.value = false; }
}
async function guardarCambiosCotizacion() {
  if (!related.quotation) return;
  advancing.value = true;
  try {
    await call("costeo_yelke.api.costeo_api.actualizar_cotizacion", {
      name: related.quotation.name,
      valid_till: cotForm.valid_till || null,
      payment_terms_template: cotForm.payment_terms_template || null,
      tc_name: cotForm.tc_name || null,
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

// ── Asignar ──
function openAssign(doctype, name) { assignModal.doctype = doctype; assignModal.name = name; assignModal.selected = []; assignModal.open = true; }
async function doAssign() {
  if (!assignModal.selected.length) return;
  assignModal.sending = true;
  try {
    await call("costeo_yelke.api.costeo_api.asignar_documento", { doctype: assignModal.doctype, name: assignModal.name, assign_to: assignModal.selected.join(",") });
    assignModal.open = false;
    showToast("Asignado");
  } catch (e) { showToast(e.message || "No se pudo asignar", "error"); }
  finally { assignModal.sending = false; }
}
async function loadCotDefaults() {
  try { const r = await call("costeo_yelke.api.costeo_api.get_cotizacion_defaults", { company: form.compania }); cotDefaults.payment_terms_templates = r.payment_terms_templates || []; cotDefaults.terms = r.terms || []; cotDefaults.users = r.users || []; } catch { /* ignore */ }
}

// ── Kebab ──
function onDocClick(e) { if (actionsRef.value && !actionsRef.value.contains(e.target)) actionsOpen.value = false; }
async function loadFamilias() {
  try { familias.value = await call("costeo_yelke.api.costeo_template_api.get_familias") || []; }
  catch { /* ignore */ }
}
function openTplModal() {
  actionsOpen.value = false;
  if (isNew.value) { showToast("Guarda el costeo primero", "error"); return; }
  tplModal.nombre = form.familia_prenda || form.cliente || "";
  tplModal.familia = form.familia_prenda || "";
  tplModal.open = true;
}
async function guardarComoPlantilla() {
  tplModal.saving = true;
  try {
    if (docState.value === 0) await saveDoc();
    await call("costeo_yelke.api.costeo_template_api.save_as_template", {
      costeo: docName.value, nombre: tplModal.nombre, familia_prenda: tplModal.familia || null,
    });
    tplModal.open = false;
    showToast("Plantilla guardada · disponible en Plantillas");
    loadFamilias();
  } catch (e) { showToast(e.message || "No se pudo guardar la plantilla", "error"); }
  finally { tplModal.saving = false; }
}
function openCancel() { actionsOpen.value = false; confirmCancel.open = true; }
async function doCancel() {
  confirmCancel.loading = true;
  try {
    const r = await call("costeo_yelke.api.costeo_api.cancelar_documento", { doctype: "Costeo", name: docName.value });
    docState.value = r.docstatus;
    confirmCancel.open = false;
    showToast("Costeo cancelado. Ahora puedes eliminarlo.");
  } catch (e) { showToast(e.message || "No se pudo cancelar", "error"); }
  finally { confirmCancel.loading = false; }
}
function openDelete() { actionsOpen.value = false; confirmDelete.open = true; }
async function doDelete() { confirmDelete.loading = true; try { await call("costeo_yelke.api.costeo_api.delete_costeo", { name: docName.value }); confirmDelete.open = false; router.replace({ name: "CosteoList" }); } catch (e) { showToast(e.message || "Error al eliminar", "error"); } finally { confirmDelete.loading = false; } }
async function duplicateDoc() { actionsOpen.value = false; try { const res = await call("costeo_yelke.api.costeo_api.duplicate_costeo", { name: docName.value }); showToast("Costeo duplicado"); router.push({ name: "CosteoDetail", params: { name: res.name } }); } catch (e) { showToast(e.message || "Error al duplicar", "error"); } }
function printDoc() { actionsOpen.value = false; printDocView("Costeo", docName.value); }
function openInDesk() { actionsOpen.value = false; if (docName.value) deskOpen("Costeo", docName.value); }

// ── Lifecycle ──
onMounted(async () => {
  document.addEventListener("click", onDocClick, true);
  loadFamilias();
  if (isNew.value) { loading.value = false; return; }
  try {
    const data = await db.get("Costeo", route.params.name);
    await fillFromDoc(data);
    activeStep.value = Math.max(ORDER.indexOf(docStatus.value), 0);
    await loadRelated();
    await loadCotDefaults();
    await loadPlan();
  } catch { showToast("No se pudo cargar el costeo", "error"); }
  finally { loading.value = false; }
});
onUnmounted(() => document.removeEventListener("click", onDocClick, true));
</script>

<style scoped>
.section-title { @apply text-[11px] font-semibold text-ink-light uppercase tracking-wider; }
.field-label { @apply text-xs font-medium text-ink-muted block mb-1; }
.field-input { @apply w-full text-sm border border-surface-border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400 bg-white transition-colors; }
.prefix { @apply absolute left-3 top-1/2 -translate-y-1/2 text-ink-light text-sm; }
.suffix { @apply absolute right-3 top-1/2 -translate-y-1/2 text-ink-light text-sm; }
.add-link { @apply flex items-center gap-1.5 text-xs font-medium text-brand-600 hover:text-brand-700 px-2.5 py-1.5 rounded-md hover:bg-brand-50 transition-colors; }
.del-btn { @apply w-6 h-6 flex items-center justify-center rounded hover:bg-red-50 hover:text-red-400 text-gray-300; }
.action-item { @apply flex items-center gap-2.5 w-full px-4 py-2 text-sm text-ink hover:bg-surface-raised transition-colors text-left; }
.doc-action { @apply h-8 px-3 flex items-center gap-1.5 text-[13px] font-medium text-ink-muted border border-surface-border rounded-lg hover:bg-surface-raised transition-colors no-underline; }
.prod-card { @apply bg-white rounded-xl border border-surface-border p-4; }
.prod-head { @apply flex items-center justify-between mb-2; }
.prod-title { @apply text-[13px] font-semibold text-ink flex items-center gap-2; }
.prod-count { @apply text-[11px] font-medium text-ink-muted bg-surface-raised rounded-full px-2 py-0.5; }
.prod-row { @apply flex items-center gap-3 py-1.5 border-b border-surface-border/60 last:border-0; }
.prod-status { @apply text-[11px] font-medium text-ink-muted bg-surface-raised rounded-full px-2 py-0.5 whitespace-nowrap; }
.prod-empty { @apply text-[12px] text-ink-light py-1; }
.prod-next { @apply flex flex-col items-center gap-1.5 p-3 rounded-lg border border-surface-border text-[12.5px] font-medium text-ink hover:bg-surface-raised hover:border-brand-200 transition-colors disabled:opacity-40 disabled:cursor-not-allowed text-center; }
.prod-next--active { @apply border-brand-500 bg-brand-50 text-brand-700; }
.prod-done { @apply text-[11px] font-normal text-green-600; }
.prod-tab { @apply flex items-center gap-2 px-3 py-1.5 rounded-lg text-[13px] font-medium text-ink-muted transition-colors disabled:opacity-40 disabled:cursor-not-allowed; }
.prod-tab--active { @apply bg-surface-raised text-ink; }
.prod-tab-num { @apply w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-semibold flex-shrink-0; }
.metric { @apply bg-surface-raised rounded-lg px-3 py-2.5; }
.metric-label { @apply text-[11px] text-ink-muted; }
.metric-val { @apply text-lg font-semibold text-ink mt-0.5; }
.panel-enter-active { transition: opacity 0.12s ease, transform 0.12s ease; }
.panel-leave-active { transition: opacity 0.08s ease, transform 0.08s ease; }
.panel-enter-from, .panel-leave-to { opacity: 0; transform: translateY(-4px) scale(0.98); }
</style>
