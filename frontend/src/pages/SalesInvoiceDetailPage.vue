<template>
  <div class="flex flex-col min-h-0">

    <PageHeader
      :title="isNew ? 'Nueva Factura de Venta' : (inv.name || 'Cargando…')"
      :subtitle="isNew ? 'Nueva factura' : (inv.customer_name || inv.customer || '')"
      back
    >
      <template v-if="!isNew">
        <button class="btn-icon" title="Imprimir" @click="openPrint">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/></svg>
        </button>

        <template v-if="inv.docstatus === 1">
          <!-- Registrar Pago -->
          <button
            class="px-3 py-1.5 bg-green-600 text-white text-sm font-semibold rounded-md hover:bg-green-700 flex items-center gap-1.5 transition-colors"
            @click="openPayment"
          >
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"/></svg>
            Registrar Pago
          </button>
          <!-- Enviar -->
          <button
            class="px-3 py-1.5 bg-brand-500 text-white text-sm font-semibold rounded-md hover:bg-brand-600 flex items-center gap-1.5 transition-colors"
            @click="showSendModal = true"
          >
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>
            Enviar
          </button>
          <div class="w-px h-5 bg-gray-200" />
        </template>

        <a :href="`/app/sales-invoice/${encodeURIComponent(inv.name)}`" target="_blank"
          class="px-3 py-1.5 border border-gray-200 text-gray-600 text-sm font-medium rounded-md hover:bg-gray-50 flex items-center gap-1.5">
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
          Desk
        </a>
      </template>
    </PageHeader>

    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <svg class="w-7 h-7 animate-spin text-gray-300" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
      </svg>
    </div>

    <div v-else class="p-5 pb-40 flex gap-5 items-start">

      <div class="flex-1 min-w-0 space-y-4">

        <!-- Status bar -->
        <div v-if="!isNew" class="flex items-center gap-3 bg-white border border-gray-200 rounded-xl px-4 py-2.5">
          <StatusBadge :docstatus="inv.docstatus" :status="inv.status" />
          <span class="text-xs text-gray-300">·</span>
          <span class="text-xs font-mono text-gray-400">{{ inv.name }}</span>
          <div class="flex-1" />
          <span v-if="inv.outstanding_amount > 0 && inv.docstatus === 1" class="text-xs font-semibold text-red-600 bg-red-50 px-2 py-0.5 rounded-full">
            Saldo: {{ fmtC(inv.outstanding_amount) }}
          </span>
          <span v-else-if="inv.docstatus === 1" class="text-xs font-semibold text-green-600 bg-green-50 px-2 py-0.5 rounded-full">
            Pagada
          </span>
        </div>

        <!-- Dirty bar -->
        <div v-if="isDirty && canEdit" class="flex items-center justify-between bg-amber-50 border border-amber-200 rounded-xl px-4 py-2.5">
          <p class="text-xs text-amber-700 font-medium flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full bg-amber-400 inline-block" />
            Cambios sin guardar
          </p>
          <div class="flex items-center gap-2">
            <button v-if="!isNew" class="px-3 py-1.5 border border-gray-200 text-gray-500 text-xs font-medium rounded-lg hover:bg-gray-50" @click="discardChanges">Descartar</button>
            <button :disabled="saving" class="px-4 py-1.5 bg-brand-500 text-white text-xs font-semibold rounded-lg hover:bg-brand-600 disabled:opacity-50 flex items-center gap-1.5" @click="save">
              <svg v-if="saving" class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
              {{ saving ? 'Guardando…' : 'Guardar' }}
            </button>
          </div>
        </div>

        <!-- Tabs -->
        <div class="bg-white rounded-t-xl border border-gray-200 border-b-0 px-4 pt-3 flex gap-1">
          <button v-for="tab in TABS" :key="tab.key"
            class="px-3 py-2 text-xs font-medium border-b-2 transition-colors -mb-px whitespace-nowrap"
            :class="activeTab === tab.key ? 'border-brand-500 text-brand-600' : 'border-transparent text-gray-500 hover:text-gray-700'"
            @click="activeTab = tab.key"
          >{{ tab.label }}
            <span v-if="tab.key === 'items'" class="ml-1 px-1.5 py-0.5 rounded-full text-xs" :class="activeTab==='items' ? 'bg-brand-100 text-brand-700' : 'bg-gray-100 text-gray-500'">{{ form.items.length }}</span>
          </button>
        </div>

        <div class="bg-white rounded-b-xl rounded-tr-xl border border-gray-200 p-6">

          <!-- General -->
          <div v-if="activeTab === 'general'" class="space-y-5">
            <div class="grid grid-cols-2 gap-x-6 gap-y-4">

              <div>
                <label class="field-label">Cliente <span class="text-red-400">*</span></label>
                <select v-model="form.customer" :disabled="!canEdit" class="field-input">
                  <option value="">— Seleccionar cliente —</option>
                  <option v-for="c in defaults.customers" :key="c.name" :value="c.name">{{ c.nombre_comercial || c.customer_name }}</option>
                </select>
              </div>

              <div>
                <label class="field-label">Empresa <span class="text-red-400">*</span></label>
                <input v-model="form.company" type="text" :disabled="!canEdit" class="field-input" />
              </div>

              <div>
                <label class="field-label">Fecha de Emisión <span class="text-red-400">*</span></label>
                <input v-model="form.posting_date" type="date" :disabled="!canEdit" class="field-input" />
              </div>

              <div>
                <label class="field-label">Fecha de Vencimiento</label>
                <input v-model="form.due_date" type="date" :disabled="!canEdit" class="field-input" />
              </div>

              <div>
                <label class="field-label">Moneda</label>
                <select v-model="form.currency" :disabled="!canEdit" class="field-input">
                  <option v-for="c in defaults.currencies" :key="c.name" :value="c.name">{{ c.name }}</option>
                </select>
              </div>

              <div>
                <label class="field-label">Lista de Precios</label>
                <select v-model="form.selling_price_list" :disabled="!canEdit" class="field-input">
                  <option value="">— Sin lista —</option>
                  <option v-for="pl in defaults.price_lists" :key="pl.name" :value="pl.name">{{ pl.name }}</option>
                </select>
              </div>

              <div>
                <label class="field-label">Impuestos y Cargos</label>
                <select v-model="form.taxes_and_charges" :disabled="!canEdit" class="field-input">
                  <option value="">— Sin plantilla —</option>
                  <option v-for="t in defaults.tax_templates" :key="t.name" :value="t.name">{{ t.name }}</option>
                </select>
              </div>

              <div>
                <label class="field-label">OC del Cliente</label>
                <input v-model="form.po_no" type="text" :disabled="!canEdit" class="field-input" placeholder="Núm. orden de compra" />
              </div>

              <div>
                <label class="field-label">Email de contacto</label>
                <input v-model="form.contact_email" type="email" :disabled="!canEdit" class="field-input" />
              </div>

              <div>
                <label class="field-label">WhatsApp / Móvil</label>
                <input v-model="form.contact_mobile" type="tel" :disabled="!canEdit" class="field-input" />
              </div>

            </div>
          </div>

          <!-- Items -->
          <div v-if="activeTab === 'items'" class="space-y-4">
            <div class="overflow-x-auto">
              <table class="w-full text-sm min-w-[760px]">
                <thead>
                  <tr class="border-b border-gray-100">
                    <th class="text-left text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3 pr-3 w-10">#</th>
                    <th class="text-left text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3 pr-3">Artículo</th>
                    <th class="text-left text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3 pr-3 w-24">Cant.</th>
                    <th class="text-left text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3 pr-3 w-24">UOM</th>
                    <th class="text-right text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3 pr-3 w-32">Precio</th>
                    <th class="text-right text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3 pr-3 w-20">Desc %</th>
                    <th class="text-right text-xs font-semibold text-gray-400 uppercase tracking-wider pb-3 pr-3 w-32">Importe</th>
                    <th v-if="canEdit" class="w-8 pb-3"></th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-50">
                  <tr v-for="(row, idx) in form.items" :key="idx" class="group">
                    <td class="py-3 pr-3 text-xs text-gray-400">{{ idx + 1 }}</td>
                    <td class="py-3 pr-3">
                      <div class="flex items-start gap-2.5">
                        <div class="w-10 h-10 rounded-lg flex-shrink-0 overflow-hidden bg-gray-100 border border-gray-200">
                          <img v-if="row.image" :src="row.image" :alt="row.item_name" class="w-full h-full object-cover" @error="row.image=''" />
                          <div v-else class="w-full h-full flex items-center justify-center">
                            <svg class="w-4 h-4 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10"/></svg>
                          </div>
                        </div>
                        <div class="flex-1 space-y-1 min-w-0">
                          <input v-if="canEdit" v-model="row.item_code" type="text" list="item-datalist-sinv" class="field-input text-xs" placeholder="Código" @change="fillItemDefaults(row)" />
                          <span v-else class="font-medium text-gray-800 text-xs block">{{ row.item_code }}</span>
                          <p v-if="row.item_name && row.item_name !== row.item_code" class="text-xs text-gray-400 truncate">{{ row.item_name }}</p>
                        </div>
                      </div>
                    </td>
                    <td class="py-3 pr-3">
                      <input v-if="canEdit" v-model.number="row.qty" type="number" min="0.001" step="any" class="field-input text-xs w-20" @input="recalcRow(row)" />
                      <span v-else class="text-gray-800 text-xs">{{ row.qty }}</span>
                    </td>
                    <td class="py-3 pr-3">
                      <select v-if="canEdit" v-model="row.uom" class="field-input text-xs w-24">
                        <option v-for="u in defaults.uoms" :key="u.name" :value="u.name">{{ u.name }}</option>
                      </select>
                      <span v-else class="text-gray-600 text-xs">{{ row.uom }}</span>
                    </td>
                    <td class="py-3 pr-3 text-right">
                      <input v-if="canEdit" v-model.number="row.rate" type="number" min="0" step="any" class="field-input text-xs text-right w-28" @input="recalcRow(row)" />
                      <span v-else class="font-medium text-gray-800 text-xs">{{ fmtN(row.rate) }}</span>
                    </td>
                    <td class="py-3 pr-3 text-right">
                      <input v-if="canEdit" v-model.number="row.discount_percentage" type="number" min="0" max="100" step="0.1" class="field-input text-xs text-right w-16" @input="recalcRow(row)" />
                      <span v-else class="text-gray-600 text-xs">{{ row.discount_percentage || 0 }}%</span>
                    </td>
                    <td class="py-3 pr-3 text-right">
                      <span class="font-semibold text-gray-800 text-xs">{{ fmtN(row.amount) }}</span>
                    </td>
                    <td v-if="canEdit" class="py-3">
                      <button class="w-6 h-6 flex items-center justify-center rounded opacity-0 group-hover:opacity-100 hover:bg-red-50 hover:text-red-500 text-gray-300 transition-all" @click="form.items.splice(idx, 1)">
                        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
                      </button>
                    </td>
                  </tr>
                  <tr v-if="!form.items.length">
                    <td :colspan="canEdit ? 8 : 7" class="py-10 text-center text-gray-400 text-sm">Sin artículos.</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <datalist id="item-datalist-sinv">
              <option v-for="item in itemIndex" :key="item.name" :value="item.name">{{ item.item_name }}</option>
            </datalist>
            <button v-if="canEdit" class="flex items-center gap-2 px-4 py-2 border border-dashed border-gray-300 rounded-xl text-sm text-gray-500 hover:border-brand-400 hover:text-brand-600 transition-colors w-full justify-center" @click="addItem">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
              Agregar artículo
            </button>
          </div>

          <!-- Términos -->
          <div v-if="activeTab === 'terminos'" class="space-y-4">
            <div>
              <label class="field-label">Plantilla de Términos</label>
              <select v-model="form.tc_name" :disabled="!canEdit" class="field-input">
                <option value="">— Sin plantilla —</option>
                <option v-for="t in defaults.terms_templates" :key="t.name" :value="t.name">{{ t.name }}</option>
              </select>
            </div>
            <div>
              <label class="field-label">Términos y Condiciones</label>
              <textarea v-model="form.terms" :disabled="!canEdit" rows="8" class="field-input resize-y" />
            </div>
          </div>

        </div>

        <!-- Bottom actions (draft) -->
        <div v-if="canEdit" class="flex items-center justify-between gap-3">
          <div>
            <button v-if="!isNew && inv.docstatus === 0"
              :disabled="!!(acting || saving)"
              class="px-4 py-2 border border-red-200 text-red-600 text-sm font-medium rounded-xl hover:bg-red-50 disabled:opacity-50"
              @click="cancelInv">
              Cancelar Factura
            </button>
          </div>
          <div class="flex items-center gap-3">
            <button v-if="!isNew"
              :disabled="!!(saving || acting)"
              class="px-5 py-2 border border-gray-200 text-gray-600 text-sm font-medium rounded-xl hover:bg-gray-50 disabled:opacity-50 flex items-center gap-2"
              @click="save">
              <svg v-if="saving" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
              {{ saving ? 'Guardando…' : 'Guardar borrador' }}
            </button>
            <button
              :disabled="!!(saving || acting)"
              class="px-5 py-2 bg-brand-500 text-white text-sm font-semibold rounded-xl hover:bg-brand-600 disabled:opacity-50 flex items-center gap-2"
              @click="doSubmit">
              <svg v-if="saving || acting === 'submit'" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
              <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
              {{ saving ? 'Guardando…' : acting === 'submit' ? 'Validando…' : 'Validar Factura' }}
            </button>
          </div>
        </div>

        <div v-if="!isNew && inv.docstatus === 1" class="flex justify-end">
          <button :disabled="acting === 'cancel'" class="px-4 py-2 border border-red-200 text-red-600 text-sm font-medium rounded-xl hover:bg-red-50 disabled:opacity-50" @click="cancelInv">
            Cancelar Factura
          </button>
        </div>

      </div>

      <!-- Right sidebar -->
      <div class="w-60 flex-shrink-0 space-y-4 sticky top-5 self-start max-h-[calc(100vh-80px)] overflow-y-auto">

        <div class="bg-white rounded-xl border border-gray-200 p-4 space-y-2.5">
          <p class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Totales</p>
          <div class="flex justify-between items-center text-sm">
            <span class="text-gray-500">Subtotal</span>
            <span class="font-medium text-gray-800">{{ fmtC(totals.subtotal) }}</span>
          </div>
          <div v-if="form.additional_discount_percentage" class="flex justify-between items-center text-sm">
            <span class="text-gray-500">Descuento ({{ form.additional_discount_percentage }}%)</span>
            <span class="text-red-600 font-medium">-{{ fmtC(totals.discountAmount) }}</span>
          </div>
          <div v-if="inv.total_taxes_and_charges" class="flex justify-between items-center text-sm">
            <span class="text-gray-500">Impuestos</span>
            <span class="font-medium text-gray-800">{{ fmtC(inv.total_taxes_and_charges) }}</span>
          </div>
          <div class="flex justify-between items-center text-base font-bold border-t border-gray-100 pt-2.5 mt-1">
            <span class="text-gray-800">Total</span>
            <span class="text-brand-600">{{ fmtC(totals.grand) }} <span class="text-xs font-normal text-gray-400">{{ form.currency }}</span></span>
          </div>
          <div v-if="inv.outstanding_amount !== undefined && inv.docstatus === 1" class="flex justify-between items-center text-sm border-t border-gray-100 pt-2 mt-1">
            <span class="text-gray-500">Saldo pendiente</span>
            <span :class="inv.outstanding_amount > 0 ? 'text-red-600 font-bold' : 'text-green-600 font-bold'">{{ fmtC(inv.outstanding_amount) }}</span>
          </div>
        </div>

        <div v-if="form.customer" class="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
          <p class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Cliente</p>
          <p class="text-sm font-semibold text-gray-800">{{ customerDisplayName }}</p>
          <div v-if="form.contact_email" class="flex items-center gap-2">
            <svg class="w-3.5 h-3.5 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
            <span class="text-xs text-gray-600 truncate">{{ form.contact_email }}</span>
          </div>
        </div>

        <div class="bg-white rounded-xl border border-gray-200 p-4 space-y-2.5 text-sm">
          <div v-if="!isNew">
            <p class="text-xs text-gray-400">Estado</p>
            <StatusBadge :docstatus="inv.docstatus" :status="inv.status" class="mt-0.5" />
          </div>
          <div v-if="form.posting_date">
            <p class="text-xs text-gray-400">Fecha Emisión</p>
            <p class="font-medium text-gray-700">{{ fmtDate(form.posting_date) }}</p>
          </div>
          <div v-if="form.due_date">
            <p class="text-xs text-gray-400">Vencimiento</p>
            <p class="font-medium" :class="isDueOverdue ? 'text-red-500' : 'text-gray-700'">{{ fmtDate(form.due_date) }}</p>
          </div>
        </div>

        <div class="bg-white rounded-xl border border-gray-200 p-4">
          <p class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Artículos ({{ form.items.length }})</p>
          <div class="space-y-2 max-h-52 overflow-y-auto">
            <div v-for="(row, i) in form.items" :key="i" class="flex items-center gap-2">
              <div class="w-7 h-7 rounded-md flex-shrink-0 bg-gray-100 overflow-hidden border border-gray-200">
                <img v-if="row.image" :src="row.image" :alt="row.item_name" class="w-full h-full object-cover" @error="row.image=''" />
                <div v-else class="w-full h-full flex items-center justify-center"><span class="text-xs text-gray-300">·</span></div>
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-xs text-gray-700 truncate font-medium">{{ row.item_name || row.item_code }}</p>
                <p class="text-xs text-gray-400">{{ row.qty }} {{ row.uom }}</p>
              </div>
            </div>
            <p v-if="!form.items.length" class="text-xs text-gray-400">Sin artículos</p>
          </div>
        </div>

        <div v-if="!isNew" class="bg-white rounded-xl border border-gray-200 p-4 space-y-2 text-xs text-gray-400">
          <div v-if="inv.creation"><p class="font-medium text-gray-500">Creada</p><p>{{ fmtDatetime(inv.creation) }}</p></div>
          <div v-if="inv.modified"><p class="font-medium text-gray-500">Modificada</p><p>{{ fmtDatetime(inv.modified) }}</p></div>
        </div>

      </div>
    </div>

    <!-- Send Picker Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showSendModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm" @click.self="showSendModal = false">
          <div class="bg-white rounded-2xl shadow-2xl w-full max-w-sm">
            <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <h3 class="text-base font-semibold text-gray-800">Enviar factura</h3>
              <button class="w-7 h-7 rounded-full hover:bg-gray-100 flex items-center justify-center text-gray-400" @click="showSendModal = false">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>
            <div class="px-6 py-5 space-y-3">
              <button class="w-full flex items-center gap-4 px-4 py-3.5 border border-gray-200 rounded-xl hover:border-brand-400 hover:bg-brand-50 transition-colors text-left group" @click="showSendModal = false; showEmailModal = true">
                <div class="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center flex-shrink-0">
                  <svg class="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
                </div>
                <div><p class="text-sm font-semibold text-gray-800">Correo electrónico</p><p class="text-xs text-gray-400 mt-0.5">Enviar PDF adjunto por email</p></div>
              </button>
              <button class="w-full flex items-center gap-4 px-4 py-3.5 border border-gray-200 rounded-xl hover:border-gray-400 hover:bg-gray-50 transition-colors text-left group" @click="showSendModal = false; openPrint()">
                <div class="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0">
                  <svg class="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/></svg>
                </div>
                <div><p class="text-sm font-semibold text-gray-800">Imprimir / PDF</p><p class="text-xs text-gray-400 mt-0.5">Vista previa de impresión</p></div>
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Email Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showEmailModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm" @click.self="showEmailModal = false">
          <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg">
            <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <h3 class="text-base font-semibold text-gray-800">Enviar por correo</h3>
              <button class="w-7 h-7 rounded-full hover:bg-gray-100 flex items-center justify-center text-gray-400" @click="showEmailModal = false">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>
            <div class="px-6 py-4 space-y-4">
              <div><label class="field-label">Para <span class="text-red-400">*</span></label><input v-model="emailForm.to" type="email" class="field-input" /></div>
              <div><label class="field-label">Asunto</label><input v-model="emailForm.subject" type="text" class="field-input" /></div>
              <div><label class="field-label">Mensaje</label><textarea v-model="emailForm.message" rows="5" class="field-input resize-y" /></div>
              <label class="flex items-center gap-2 cursor-pointer">
                <input v-model="emailForm.attach_pdf" type="checkbox" class="w-4 h-4 rounded text-brand-600" />
                <span class="text-sm text-gray-700">Adjuntar PDF</span>
              </label>
            </div>
            <div class="flex justify-end gap-3 px-6 py-4 border-t border-gray-100">
              <button class="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-xl hover:bg-gray-50" @click="showEmailModal = false">Cancelar</button>
              <button :disabled="sendingEmail || !emailForm.to" class="px-5 py-2 bg-brand-500 text-white text-sm font-semibold rounded-xl hover:bg-brand-600 disabled:opacity-50 flex items-center gap-2" @click="sendEmail">
                <svg v-if="sendingEmail" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                {{ sendingEmail ? 'Enviando…' : 'Enviar correo' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Toast -->
    <Transition name="fade">
      <div v-if="toast.show" class="fixed bottom-5 right-5 z-50 px-4 py-3 rounded-lg text-sm font-medium shadow-lg" :class="toast.type === 'error' ? 'bg-red-600 text-white' : 'bg-green-600 text-white'">
        {{ toast.msg }}
      </div>
    </Transition>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch, defineComponent, h } from "vue";
import { useRouter } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import { call, defaultPrintFormat } from "@/utils/frappe.js";

const props  = defineProps({ name: { type: String, default: "" } });
const router = useRouter();

const StatusBadge = defineComponent({
  props: { docstatus: Number, status: String },
  setup(p) {
    const LABELS = {
      "Draft": "Borrador", "Unpaid": "Sin Pagar", "Paid": "Pagada",
      "Partly Paid": "Pago Parcial", "Overdue": "Vencida",
      "Return": "Devolución", "Cancelled": "Cancelada",
    };
    const STATUS_COLOR = {
      "Unpaid": "bg-amber-100 text-amber-700",
      "Paid": "bg-green-100 text-green-700",
      "Partly Paid": "bg-blue-100 text-blue-700",
      "Overdue": "bg-red-100 text-red-700",
    };
    return () => {
      const ds    = p.docstatus ?? 0;
      const label = ds === 0 ? "Borrador" : ds === 2 ? "Cancelada" : (LABELS[p.status] || p.status || "Emitida");
      const cls   = ds === 0 ? "bg-gray-100 text-gray-600" : ds === 2 ? "bg-gray-100 text-gray-400" : (STATUS_COLOR[p.status] || "bg-blue-100 text-blue-700");
      return h("span", { class: `inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${cls}` }, label);
    };
  },
});

const TABS = [
  { key: "general",  label: "General" },
  { key: "items",    label: "Artículos" },
  { key: "terminos", label: "Términos" },
];

const loading      = ref(true);
const saving       = ref(false);
const acting       = ref("");
const sendingEmail = ref(false);
const activeTab    = ref("general");
const toast        = reactive({ show: false, msg: "", type: "success" });

const showSendModal  = ref(false);
const showEmailModal = ref(false);
const emailForm = reactive({ to: "", subject: "", message: "", attach_pdf: true });

const isNew = computed(() => !props.name || props.name === "nueva");

const inv = reactive({
  name: "", docstatus: 0, status: "", creation: "", modified: "",
  total_taxes_and_charges: 0, outstanding_amount: 0, customer_name: "",
});

const form = reactive({
  name: "", customer: "", company: "",
  posting_date: "", due_date: "",
  currency: "MXN", selling_price_list: "", conversion_rate: 1,
  taxes_and_charges: "", additional_discount_percentage: 0,
  tc_name: "", terms: "", customer_address: "",
  contact_person: "", contact_email: "", contact_mobile: "", po_no: "",
  items: [],
});
const formOriginal = ref({});

const defaults = reactive({
  customers: [], price_lists: [], currencies: [], tax_templates: [],
  terms_templates: [], warehouses: [], uoms: [],
  default_currency: "MXN", default_price_list: "",
});

const itemIndex = ref([]);

const canEdit = computed(() => isNew.value || inv.docstatus === 0);

const isDirty = computed(() => {
  const orig = formOriginal.value;
  if (!orig || !Object.keys(orig).length) return isNew.value;
  const keys = ["customer","company","posting_date","due_date","currency",
    "selling_price_list","taxes_and_charges","tc_name","terms","contact_email","po_no"];
  if (!keys.every(k => (form[k] ?? "") === (orig[k] ?? ""))) return true;
  if (form.items.length !== (orig.items || []).length) return true;
  return form.items.some(r => r._dirty);
});

const isDueOverdue = computed(() => {
  if (!form.due_date || inv.docstatus !== 1) return false;
  return new Date(form.due_date + "T23:59:59") < new Date() && (inv.outstanding_amount || 0) > 0;
});

const customerDisplayName = computed(() => {
  const c = defaults.customers.find(c => c.name === form.customer);
  return c?.nombre_comercial || c?.customer_name || form.customer;
});

const totals = computed(() => {
  const subtotal = form.items.reduce((s, r) => s + (r.amount || 0), 0);
  const discountAmount = subtotal * (form.additional_discount_percentage || 0) / 100;
  const taxes = isNew.value ? 0 : (inv.total_taxes_and_charges || 0);
  return { subtotal, discountAmount, grand: subtotal - discountAmount + taxes };
});

function fmtC(v) { return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(v || 0); }
function fmtN(v) { return new Intl.NumberFormat("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(v || 0); }
function fmtDate(s) { if (!s) return "—"; const d = s.includes("T") ? new Date(s) : new Date(s + "T00:00:00"); return d.toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" }); }
function fmtDatetime(s) { if (!s) return ""; return new Date(s).toLocaleString("es-MX", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }); }
function today() { return new Date().toISOString().split("T")[0]; }
function addDays(n) { const d = new Date(); d.setDate(d.getDate() + n); return d.toISOString().split("T")[0]; }
function showToast(msg, type = "success") { toast.msg = msg; toast.type = type; toast.show = true; setTimeout(() => (toast.show = false), 3500); }

function addItem() {
  form.items.push({
    item_code: "", item_name: "", description: "", image: "",
    qty: 1, uom: "", stock_uom: "", conversion_factor: 1,
    rate: 0, price_list_rate: 0, discount_percentage: 0,
    amount: 0, warehouse: "", _dirty: true,
  });
  activeTab.value = "items";
}

function recalcRow(row) {
  const base = (row.rate || 0) * (row.qty || 1);
  row.amount = base - base * (row.discount_percentage || 0) / 100;
}

async function fillItemDefaults(row) {
  if (!row.item_code) return;
  row._dirty = true;
  try {
    const res = await call("costeo_yelke.api.sales_invoice_api.get_item_details_for_sinv", {
      item_code: row.item_code, price_list: form.selling_price_list || "",
    });
    if (res) {
      row.item_name       = res.item_name || row.item_code;
      row.description     = res.description || "";
      row.stock_uom       = res.stock_uom || "";
      row.uom             = res.uom || res.stock_uom || "";
      row.rate            = res.rate || 0;
      row.price_list_rate = res.price_list_rate || 0;
      row.image           = res.image || "";
      recalcRow(row);
    }
  } catch { /* ignore */ }
}

async function loadItemIndex() {
  try {
    const items = await call("frappe.client.get_list", {
      doctype: "Item", fields: ["name","item_name"],
      filters: [["disabled","=",0]], limit_page_length: 500, order_by: "item_name asc",
    });
    itemIndex.value = items || [];
  } catch { /* ignore */ }
}

function syncFromInv(data) {
  Object.assign(inv, {
    name: data.name, docstatus: data.docstatus, status: data.status,
    creation: data.creation, modified: data.modified,
    total_taxes_and_charges: data.total_taxes_and_charges || 0,
    outstanding_amount: data.outstanding_amount || 0,
    customer_name: data.customer_name || "",
  });
  const scalars = ["customer","company","posting_date","due_date","currency",
    "selling_price_list","conversion_rate","taxes_and_charges","additional_discount_percentage",
    "tc_name","terms","customer_address","contact_person","contact_email","contact_mobile","po_no"];
  scalars.forEach(k => {
    const v = data[k];
    form[k] = v !== null && v !== undefined ? v : (typeof form[k] === "number" ? 0 : "");
  });
  form.items = (data.items || []).map(r => ({ ...r, image: r.image || "", _dirty: false }));
  form.name  = data.name;
  formOriginal.value = JSON.parse(JSON.stringify({ ...form }));
}

function discardChanges() {
  if (formOriginal.value && Object.keys(formOriginal.value).length) {
    const saved = formOriginal.value;
    Object.keys(form).forEach(k => { if (k !== "items") form[k] = saved[k] ?? form[k]; });
    form.items = (saved.items || []).map(r => ({ ...r, _dirty: false }));
  }
}

async function save() {
  saving.value = true;
  let ok = false;
  try {
    const payload = {
      name: isNew.value ? "" : form.name,
      customer: form.customer, company: form.company,
      posting_date: form.posting_date, due_date: form.due_date,
      currency: form.currency, selling_price_list: form.selling_price_list,
      conversion_rate: form.conversion_rate || 1,
      taxes_and_charges: form.taxes_and_charges,
      additional_discount_percentage: form.additional_discount_percentage || 0,
      apply_discount_on: "Grand Total",
      tc_name: form.tc_name, terms: form.terms,
      customer_address: form.customer_address,
      contact_email: form.contact_email, contact_mobile: form.contact_mobile, po_no: form.po_no,
      items: form.items.map(r => ({
        item_code: r.item_code, item_name: r.item_name, description: r.description,
        qty: r.qty, uom: r.uom, conversion_factor: r.conversion_factor || 1,
        rate: r.rate, discount_percentage: r.discount_percentage || 0,
        warehouse: r.warehouse,
      })),
    };
    const saved = await call("costeo_yelke.api.sales_invoice_api.save_sales_invoice", {
      data: JSON.stringify(payload),
    });
    syncFromInv(saved);
    showToast(isNew.value ? "Factura creada" : "Factura guardada");
    if (isNew.value) router.replace(`/facturas/${encodeURIComponent(saved.name)}`);
    ok = true;
  } catch (e) {
    showToast(e.message || "Error al guardar", "error");
  } finally {
    saving.value = false;
  }
  return ok;
}

async function doSubmit() {
  if (isDirty.value || isNew.value) {
    const saved = await save();
    if (!saved) return;
  }
  if (inv.docstatus !== 0) return;
  acting.value = "submit";
  try {
    const res = await call("costeo_yelke.api.sales_invoice_api.submit_sales_invoice", { name: inv.name });
    Object.assign(inv, { docstatus: res.docstatus, status: res.status });
    showToast("Factura validada");
  } catch (e) {
    showToast(e.message || "Error al validar", "error");
  } finally {
    acting.value = "";
  }
}

async function cancelInv() {
  if (!confirm("¿Cancelar esta factura?")) return;
  acting.value = "cancel";
  try {
    const res = await call("costeo_yelke.api.sales_invoice_api.cancel_sales_invoice", { name: inv.name });
    Object.assign(inv, { docstatus: res.docstatus, status: res.status });
    showToast("Factura cancelada");
  } catch (e) {
    showToast(e.message || "Error al cancelar", "error");
  } finally {
    acting.value = "";
  }
}

function openPayment() {
  window.open(`/app/payment-entry/new-payment-entry-1?party_type=Customer&party=${encodeURIComponent(form.customer)}&reference_doctype=Sales Invoice&reference_name=${encodeURIComponent(inv.name)}`, "_blank");
}

async function openPrint() {
  const fmt = await defaultPrintFormat("Sales Invoice");
  window.open(`/printview?doctype=Sales+Invoice&name=${encodeURIComponent(inv.name)}&format=${encodeURIComponent(fmt)}&no_letterhead=0`, "_blank");
}

function prepareEmailForm() {
  emailForm.to      = form.contact_email || "";
  emailForm.subject = `Factura ${inv.name} - ${customerDisplayName.value}`;
  emailForm.message = `Estimado cliente,\n\nAdjunto la factura ${inv.name} por un total de ${fmtC(totals.value?.grand || 0)} ${form.currency}.\n\nSaludos`;
  emailForm.attach_pdf = true;
}

async function sendEmail() {
  if (!emailForm.to) return;
  sendingEmail.value = true;
  try {
    await call("costeo_yelke.api.quotation_api.send_quotation_email", {
      name: inv.name, recipients: JSON.stringify([emailForm.to]),
      subject: emailForm.subject,
      message: emailForm.message.replace(/\n/g, "<br>"),
      print_format: "Standard", attach_pdf: emailForm.attach_pdf ? 1 : 0,
    });
    showToast("Correo enviado");
    showEmailModal.value = false;
  } catch (e) {
    showToast(e.message || "Error al enviar", "error");
  } finally {
    sendingEmail.value = false;
  }
}

onMounted(async () => {
  loading.value = true;
  try {
    const defs = await call("costeo_yelke.api.sales_invoice_api.get_sales_invoice_form_defaults");
    await loadItemIndex();
    defaults.customers      = defs.customers      || [];
    defaults.price_lists    = defs.price_lists    || [];
    defaults.currencies     = defs.currencies     || [];
    defaults.tax_templates  = defs.tax_templates  || [];
    defaults.terms_templates = defs.terms_templates || [];
    defaults.warehouses     = defs.warehouses     || [];
    defaults.uoms           = defs.uoms           || [];
    form.company            = defs.company          || "";
    form.currency           = defs.default_currency || "MXN";
    form.selling_price_list = defs.default_price_list || "";
    form.posting_date       = today();
    form.due_date           = addDays(30);
    if (!isNew.value) {
      const data = await call("costeo_yelke.api.sales_invoice_api.get_sales_invoice", { name: props.name });
      syncFromInv(data);
    }
    prepareEmailForm();
  } catch (e) {
    showToast(e.message || "Error al cargar", "error");
  } finally {
    loading.value = false;
  }
});

watch(showEmailModal, (v) => { if (v) prepareEmailForm(); });
watch(() => form.items, (items) => { items.forEach(r => recalcRow(r)); }, { deep: true });
</script>

<style scoped>
.field-label { @apply text-xs font-medium text-gray-500 block mb-1; }
.field-input  { @apply w-full text-sm border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white transition-colors disabled:bg-gray-50 disabled:text-gray-500; }
.btn-icon     { @apply w-8 h-8 border border-gray-200 rounded-md flex items-center justify-center text-gray-500 hover:bg-gray-50 transition-colors; }
.fade-enter-active, .fade-leave-active   { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to         { opacity: 0; }
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s, transform 0.2s; }
.modal-enter-from, .modal-leave-to       { opacity: 0; transform: scale(0.95); }
</style>
