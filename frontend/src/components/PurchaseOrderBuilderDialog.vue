<template>
  <q-dialog :model-value="modelValue" persistent style="width: 1000px; max-width: 95vw" @update:model-value="(v) => emit('update:modelValue', v)">
    <q-card style="width: 1000px; max-width: 95vw">
      <q-card-section class="row items-center">
        <div class="text-h6 q-mr-auto">
          {{ poId ? t('purchasing.addToPo') : t('purchasing.newPo') }}
        </div>
        <q-btn
          flat
          dense
          icon="sync"
          :label="t('purchasing.refreshFx')"
          class="q-mr-sm"
          :loading="fxRefreshing"
          @click="refreshFx"
        />
        <q-btn
          flat
          dense
          icon="edit"
          :label="t('purchasing.editRates')"
          class="q-mr-sm"
          @click="fxDialog = true"
        />
        <q-btn flat round icon="close" @click="close" />
      </q-card-section>

      <q-card-section>
        <q-toggle
          v-model="includeRestock"
          :label="t('purchasing.includeRestock')"
          class="q-mb-sm"
        />

        <q-table
          :rows="rows"
          :columns="columns"
          :row-key="(row) => row.__key"
          hide-bottom
          dense
          :no-data-label="t('purchasing.noPos')"
        >
          <template #body-cell-name="props">
            <q-td :props="props">
              {{ props.row.product_name }}
              <q-chip v-if="props.row.is_restock" color="orange" text-color="white" size="xs" dense>
                {{ t('purchasing.restock') }}
              </q-chip>
            </q-td>
          </template>
          <template #body-cell-supplier="props">
            <q-td :props="props">
              <q-select
                v-if="supplierOptions(props.row).length"
                v-model="props.row.chosen"
                :options="supplierOptions(props.row)"
                emit-value
                map-options
                dense
                outlined
                :label="t('purchasing.supplier')"
                @update:model-value="(val) => onSupplierChange(props.row, val)"
              />
              <span v-else class="text-negative">{{ t('purchasing.noSupplierMatch') }}</span>
            </q-td>
          </template>
          <template #body-cell-unit_cost="props">
            <q-td :props="props">
              <q-input
                v-if="props.row.is_restock"
                v-model.number="props.row.unit_cost"
                type="number"
                dense
                borderless
                :placeholder="t('purchasing.enterPrice')"
              />
              <template v-else>{{ chosenCost(props.row) }}</template>
            </q-td>
          </template>
          <template #body-cell-actions="props">
            <q-td :props="props" class="text-right">
              <q-btn
                flat
                dense
                icon="delete"
                color="negative"
                :title="t('purchasing.removeLine')"
                @click="removeRow(props.row)"
              />
            </q-td>
          </template>
        </q-table>

        <div class="text-subtitle2 q-mt-md q-mb-xs">{{ t('purchasing.manualItems') }}</div>
        <q-table
          :rows="manualItems"
          :columns="manualColumns"
          row-key="__id"
          hide-bottom
          dense
        >
          <template #body-cell-pick="props">
            <q-td :props="props" class="text-right">
              <q-btn
                size="sm"
                color="primary"
                outline
                icon="search"
                :label="t('purchasing.pickCatalog')"
                @click.stop="openCatalog(props.row)"
              />
            </q-td>
          </template>
          <template #body-cell-m_name="props">
            <q-td :props="props"><q-input v-model="props.row.name" dense borderless /></q-td>
          </template>
          <template #body-cell-sku="props">
            <q-td :props="props"><q-input v-model="props.row.sku" dense borderless /></q-td>
          </template>
          <template #body-cell-qty="props">
            <q-td :props="props">
              <q-input v-model.number="props.row.qty" type="number" dense borderless min="1" />
            </q-td>
          </template>
          <template #body-cell-m_cost="props">
            <q-td :props="props">
              <q-input v-model.number="props.row.unit_cost" type="number" dense borderless />
            </q-td>
          </template>
          <template #body-cell-currency="props">
            <q-td :props="props">
              <q-select
                v-model="props.row.currency"
                :options="currencyOptions"
                emit-value
                map-options
                dense
                borderless
                use-input
                input-debounce="0"
                new-value-mode="uppercase"
                :label="t('purchasing.currency')"
              />
            </q-td>
          </template>
          <template #body-cell-vendor_company_id="props">
            <q-td :props="props">
              <q-select
                v-model="props.row.vendor_company_id"
                :options="manualCompanyOptions"
                emit-value
                map-options
                dense
                borderless
                :label="t('purchasing.vendorCompany')"
              />
            </q-td>
          </template>
          <template #body-cell-actions="props">
            <q-td :props="props">
              <q-btn flat dense icon="delete" color="negative" @click="removeManual(props.rowIndex)" />
            </q-td>
          </template>
        </q-table>
        <q-btn flat icon="add" color="primary" :label="t('purchasing.addManualItem')" class="q-mt-sm" @click="addManual" />

        <!-- Suggestion engine: scenario explorer + per-supplier totals -->
        <div class="row items-center q-mt-md q-mb-xs">
          <div class="text-subtitle2 q-mr-auto">{{ t('purchasing.options') }}</div>
          <q-select
            v-model="freightPreset"
            :options="freightPresetOptions"
            emit-value
            map-options
            dense
            outlined
            style="width: 220px"
            :label="t('purchasing.freightAssumption')"
            @update:model-value="applyFreightPreset"
          />
        </div>
        <q-list bordered separator dense>
          <q-item
            v-for="o in strategyOptions"
            :key="o.id"
            clickable
            :active="o.cheapest"
            active-class="bg-green-1"
            @click="applyStrategy(o.sel)"
          >
            <q-item-section>
              <div>
                {{ o.label }}
                <q-chip v-if="o.cheapest" color="positive" text-color="white" size="xs" dense>
                  {{ t('purchasing.suggestCheapest') }}
                </q-chip>
              </div>
              <div class="text-caption">
                {{ t('purchasing.suppliersCount') }}: {{ o.suppliers }} ·
                {{ t('purchasing.grandTotal') }}:
                {{ amountsText(o.grand) }}
                <q-chip v-if="o.fxMissing" color="negative" text-color="white" size="xs" dense>
                  {{ t('purchasing.fxMissingShort') }}
                </q-chip>
              </div>
            </q-item-section>
            <q-item-section side>
              <q-btn
                flat
                dense
                icon="check"
                color="primary"
                :label="t('purchasing.applyOption')"
                @click.stop="applyStrategy(o.sel)"
              />
            </q-item-section>
          </q-item>
        </q-list>

        <div class="text-subtitle2 q-mt-md q-mb-xs">{{ t('purchasing.totals') }}</div>
        <q-list bordered separator dense>
          <q-item v-for="g in selectionTotals" :key="g.id">
            <q-item-section>
              <div>{{ g.name || t('purchasing.noSupplier') }}</div>
              <div class="text-caption">
                {{ t('purchasing.goods') }}:
                {{ amountsText(g.goods) }}
                <q-chip v-if="g.fxMissing" color="negative" text-color="white" size="xs" dense>
                  {{ t('purchasing.fxMissingShort') }}
                </q-chip>
              </div>
            </q-item-section>
            <q-item-section side top>
              <q-input
                v-model.number="freightOverrides[g.id]"
                type="number"
                dense
                outlined
                style="width: 130px"
                :label="t('purchasing.freight')"
              />
            </q-item-section>
          </q-item>
          <q-item v-if="!selectionTotals.length">
            <q-item-section class="text-grey">{{ t('purchasing.noSupplierMatch') }}</q-item-section>
          </q-item>
        </q-list>

        <div v-if="anyFxMissing" class="text-caption text-negative q-mb-xs">
          {{ t('purchasing.fxMissingWarning') }}
        </div>
        <div class="row q-mt-xs q-gutter-sm">
          <div class="col">
            <div class="text-caption">{{ t('purchasing.goods') }}</div>
            <div v-if="Object.keys(goodsByCurrency).length">
              <div v-for="(amt, cur) in goodsByCurrency" :key="cur">{{ fmt(amt) }} {{ cur }}</div>
            </div>
            <div v-else class="text-grey">—</div>
          </div>
          <div class="col">
            <div class="text-caption">{{ t('purchasing.freight') }}</div>
            <div>{{ fmt(freightTotal) }} {{ reportCurrency || '—' }}</div>
          </div>
          <div class="col">
            <div class="text-caption">{{ t('purchasing.grandTotal') }}</div>
            <div v-for="(amt, cur) in grandByCurrency" :key="'g-' + cur" class="text-weight-bold">
              {{ fmt(amt) }} {{ cur }}
            </div>
          </div>
          <div class="col">
            <div class="text-caption">{{ t('purchasing.suppliersCount') }}</div>
            <div>{{ selectionTotals.length }}</div>
          </div>
        </div>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="close" />
        <q-btn
          color="primary"
          :label="poId ? t('purchasing.addToPo') : t('app.actions.save')"
          :loading="submitting"
          @click="submit"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>

  <q-dialog v-model="fxDialog" style="width: 700px; max-width: 95vw">
    <q-card style="width: 700px; max-width: 95vw">
      <q-card-section class="row items-center">
        <div class="text-h6 q-mr-auto">{{ t('purchasing.fxTitle') }}</div>
        <q-btn flat round icon="close" @click="fxDialog = false" />
      </q-card-section>
      <q-card-section>
        <FxRatesManager @saved="onFxSaved" />
      </q-card-section>
    </q-card>
  </q-dialog>

  <CatalogPickerDialog
    v-model="showCatalogPicker"
    :vendor-id="allowedSupplierId"
    @select="onCatalogSelect"
  />
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQuasar } from 'quasar'
import { api } from '../boot/axios'
import CatalogPickerDialog from './CatalogPickerDialog.vue'
import FxRatesManager from './FxRatesManager.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  jobIds: { type: Array, default: () => [] },
  poId: { type: Number, default: null },
  allowedSupplierId: { type: Number, default: null },
})
const emit = defineEmits(['update:modelValue', 'done'])

const { t } = useI18n()
const $q = useQuasar()

const rows = ref([])
const manualItems = ref([])
const includeRestock = ref(false)
const submitting = ref(false)
const reportCurrency = ref(null)
const companies = ref([])
const freight = ref({})
const freightOverrides = ref({})
const fxRates = ref(null)
let manualSeq = 0
const fxDialog = ref(false)

function freightAmount(sid) {
  if (freightOverrides.value[sid] != null && freightOverrides.value[sid] !== '') {
    return Number(freightOverrides.value[sid]) || 0
  }
  const f = freight.value[sid]
  return f && f.base != null ? Number(f.base) : 0
}

function fmt(n) {
  return n == null ? '—' : Number(n).toFixed(2)
}

const columns = computed(() => [
  { name: 'name', label: t('purchasing.item'), field: 'product_name', align: 'left' },
  { name: 'qty', label: t('purchasing.qty'), field: 'qty', align: 'left', style: 'width:80px' },
  { name: 'supplier', label: t('purchasing.supplier'), field: 'supplier', align: 'left' },
  { name: 'unit_cost', label: t('purchasing.unitCost'), field: 'unit_cost', align: 'right' },
  { name: 'actions', label: '', field: 'actions', align: 'right', style: 'width:40px' },
])

const manualColumns = computed(() => [
  { name: 'pick', label: '', field: 'pick', align: 'right' },
  { name: 'm_name', label: t('purchasing.name'), field: 'name', align: 'left' },
  { name: 'sku', label: t('purchasing.sku'), field: 'sku', align: 'left' },
  { name: 'qty', label: t('purchasing.qty'), field: 'qty', align: 'left' },
  { name: 'm_cost', label: t('purchasing.unitCost'), field: 'unit_cost', align: 'left' },
  { name: 'currency', label: t('purchasing.currency'), field: 'currency', align: 'left' },
  { name: 'vendor_company_id', label: t('purchasing.vendorCompany'), field: 'vendor_company_id', align: 'left' },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
])

const currencyOptions = [
  'SEK', 'EUR', 'USD', 'GBP', 'NOK', 'DKK', 'CHF', 'PLN', 'CZK', 'HUF',
].map((c) => ({ label: c, value: c }))

const showCatalogPicker = ref(false)
const pickRow = ref(null)
function openCatalog(row) {
  pickRow.value = row
  showCatalogPicker.value = true
}
function onCatalogSelect(payload) {
  const row = pickRow.value
  showCatalogPicker.value = false
  pickRow.value = null
  if (!row || !payload) return
  if (payload.type === 'vendor') {
    const vp = payload.data
    row.vendor_product_id = vp.id
    row.vendor_company_id = vp.vendor_id
    row.name = vp.name
    row.sku = vp.sku || row.sku
    if (vp.unit_cost != null) row.unit_cost = vp.unit_cost
    if (vp.currency) row.currency = vp.currency
    return
  }
  // inventory Product: fill name/sku, then resolve best purchasable source.
  const p = payload.data
  row.name = p.name
  row.sku = p.sku || row.sku
  api
    .get(`/api/v1/inventory/products/${p.id}/purchase-info`)
    .then(({ data }) => {
      if (data.vendor_product_id) row.vendor_product_id = data.vendor_product_id
      if (data.supplier_company_id) row.vendor_company_id = data.supplier_company_id
      if (data.unit_cost != null) row.unit_cost = data.unit_cost
      if (data.currency) row.currency = data.currency
    })
    .catch(() => {})
}

const manualCompanyOptions = computed(() => {
  if (props.allowedSupplierId) {
    const c = companies.value.find((x) => x.id === props.allowedSupplierId)
    return [{ label: c ? c.name : t('purchasing.lockedSupplier'), value: props.allowedSupplierId }]
  }
  return companies.value.map((c) => ({ label: c.name, value: c.id }))
})

function supplierOptions(row) {
  let candidates = row.candidates || []
  if (props.allowedSupplierId) {
    candidates = candidates.filter((c) => c.vendor_id === props.allowedSupplierId)
  }
  const groupEta = row.next_restock_date
  return candidates.map((c) => {
    let label = `${c.vendor_name || '—'} — ${c.unit_cost != null ? c.unit_cost : '?'} ${c.currency || ''}`
    if (!c.in_stock) {
      const ed = c.expected_delivery_date || groupEta
      label += ed ? ` (out · ETA ${ed.slice(0, 10)})` : ' (out)'
    }
    return { label, value: c.vendor_product_id }
  })
}

function chosenCost(row) {
  const c = (row.candidates || []).find((x) => x.vendor_product_id === row.chosen)
  if (!c) return '—'
  const showConv =
    c.converted_unit_cost != null &&
    reportCurrency.value &&
    c.currency &&
    c.currency !== reportCurrency.value
  if (showConv) {
    return `${fmt(c.converted_unit_cost)} ${reportCurrency.value} (${c.unit_cost} ${c.currency})`
  }
  return `${c.unit_cost != null ? c.unit_cost : '?'} ${c.currency || ''}`
}

// Frontend mirror of the backend `convert()` so the displayed goods/freight total
// matches the PO's persisted `total_base` (which is converted server-side).
function convertManual(amount, currency) {
  if (amount == null) return null
  const fx = fxRates.value
  const base = (fx?.base || 'EUR').toUpperCase()
  const target = (reportCurrency.value || base).toUpperCase()
  const cur = (currency || '').toUpperCase() || null
  if (!cur || cur === target) return Number(amount)
  const rates = {}
  for (const [k, v] of Object.entries(fx?.rates || {})) rates[k.toUpperCase()] = Number(v)
  let inBase
  if (cur === base) inBase = Number(amount)
  else {
    const r = rates[cur]
    if (r == null) return null
    inBase = Number(amount) * r
  }
  if (target === base) return inBase
  const tr = rates[target]
  if (tr == null) return null
  return inBase / tr
}

// A row's effective selected candidate. Requirement rows resolve via the chosen
// vendor product; restock rows already carry a single fixed candidate (their
// linked vendor), so they must be counted even though their vendor_product_id is
// null and requirement_id is None.
function effectiveCandidate(r, sel) {
  if (r.is_restock) {
    const manual = r.unit_cost != null ? r.unit_cost : null
    const c = (r.candidates || [])[0] || null
    if (c) {
      return { ...c, unit_cost: manual != null ? manual : c.unit_cost }
    }
    // No linked vendor at all: count the manually entered price only.
    if (manual != null) {
      return {
        vendor_id: null,
        vendor_product_id: null,
        vendor_name: null,
        currency: r.currency || reportCurrency.value || 'SEK',
        unit_cost: manual,
        converted_unit_cost: null,
      }
    }
    return null
  }
  const vpId = sel ? sel[r.__key] : r.chosen
  if (vpId == null) return null
  return (r.candidates || []).find((x) => x.vendor_product_id === vpId) || null
}

function cheapestCandidate(row) {
  let candidates = row.candidates || []
  if (props.allowedSupplierId) {
    candidates = candidates.filter((c) => c.vendor_id === props.allowedSupplierId)
  }
  if (!candidates.length) return null
  return candidates.reduce((best, c) => {
    const cv = c.converted_unit_cost != null ? c.converted_unit_cost : c.unit_cost
    const bv = best.converted_unit_cost != null ? best.converted_unit_cost : best.unit_cost
    return cv != null && (bv == null || cv < bv) ? c : best
  }, candidates[0])
}

function bestOptionForSupplier(opts, line) {
  const lineOpts = opts.filter((o) => o.line === line)
  if (!lineOpts.length) return null
  lineOpts.sort((a, b) => Number(b.inStock) - Number(a.inStock) || a.price - b.price)
  return lineOpts[0]
}

// Build the per-supplier option list for every requirement line so the
// consolidation optimiser and the per-item picker can reuse it.
function supplierOptionMap() {
  const map = {}
  for (const r of rows.value) {
    for (const c of r.candidates || []) {
      const price = c.converted_unit_cost != null ? c.converted_unit_cost : c.unit_cost
      ;(map[c.vendor_id] ||= []).push({
        line: r,
        vpId: c.vendor_product_id,
        price: price != null ? Number(price) : Infinity,
        inStock: c.in_stock,
      })
    }
  }
  return map
}

// Cheapest-per-item: each line takes its cheapest supplier (ignores freight/
// consolidation entirely).
function computeSplitSelection() {
  const sel = {}
  for (const r of rows.value) {
    const c = cheapestCandidate(r)
    if (c) sel[r.__key] = c.vendor_product_id
  }
  return sel
}

// Greedy consolidation: repeatedly pick the supplier (not yet used) that covers
// the most still-unmet lines at the lowest marginal cost (its freight + the items
// it can supply), so splitting across many suppliers only happens when it truly
// saves money after shipping is accounted for.
function computeConsolidatedSelection() {
  const supplierLines = supplierOptionMap()
  let remaining = new Set(rows.value.filter((r) => (r.candidates || []).length))
  const chosen = new Set()
  const pick = {}
  while (remaining.size) {
    let best = null
    for (const sid of Object.keys(supplierLines)) {
      if (chosen.has(sid)) continue
      const freightCost = freightAmount(Number(sid))
      let covered = 0
      let cost = 0
      remaining.forEach((r) => {
        const opt = bestOptionForSupplier(supplierLines[sid], r)
        if (opt && isFinite(opt.price)) {
          covered += 1
          cost += opt.price * (r.qty || 0)
        }
      })
      if (!covered) continue
      const marginal = freightCost + cost
      if (!best || marginal < best.marginal) {
        best = { sid: Number(sid), marginal }
      }
    }
    if (!best) break
    chosen.add(best.sid)
    const still = new Set()
    remaining.forEach((r) => {
      const opt = bestOptionForSupplier(supplierLines[best.sid], r)
      if (opt && isFinite(opt.price)) pick[r.__key] = opt.vpId
      else still.add(r)
    })
    remaining = still
  }
  return pick
}

// Total (goods + freight) for a concrete selection, kept per currency so that
// lines which could not be converted (fx_missing) are not silently summed into
// the report currency.
function totalsForSelection(sel) {
  const goods = {}
  const suppliers = new Set()
  let fxMissing = false
  for (const r of rows.value) {
    const c = effectiveCandidate(r, sel)
    if (!c) continue
    const q = r.qty || 0
    const converted = c.converted_unit_cost != null
    const currency = converted ? reportCurrency.value || c.currency : c.currency
    const amt = (converted ? c.converted_unit_cost : c.unit_cost) || 0
    goods[currency] = (goods[currency] || 0) + amt * q
    if (!converted) fxMissing = true
    suppliers.add(c.vendor_id)
  }
  for (const m of manualItems.value) {
    if (!m.vendor_company_id) continue
    const q = m.qty || 0
    const converted = convertManual(m.unit_cost, m.currency)
    if (converted != null) {
      const cur = reportCurrency.value || m.currency
      goods[cur] = (goods[cur] || 0) + converted * q
      suppliers.add(m.vendor_company_id)
    } else {
      const cur = m.currency || reportCurrency.value
      goods[cur] = (goods[cur] || 0) + (m.unit_cost || 0) * q
      suppliers.add(m.vendor_company_id)
      fxMissing = true
    }
  }
  let freight = 0
  suppliers.forEach((sid) => {
    freight += freightAmount(sid)
  })
  const grand = { ...goods }
  if (reportCurrency.value) {
    grand[reportCurrency.value] = (grand[reportCurrency.value] || 0) + freight
  }
  return { goods, freight, grand, suppliers: suppliers.size, fxMissing }
}

function applyStrategy(sel) {
  rows.value.forEach((r) => {
    if (sel[r.__key] != null) r.chosen = sel[r.__key]
  })
}

// Concrete, comparable options the user can pick between. Because freight is
// often unknown, changing the freight assumption (below) recomputes these so the
// user can see how the best choice shifts before committing.
const strategyOptions = computed(() => {
  const opts = []
  const seen = new Set()
  const push = (id, label, sel) => {
    const key = JSON.stringify(sel)
    if (seen.has(key)) return
    seen.add(key)
    const t = totalsForSelection(sel)
    opts.push({ id, label, sel, ...t })
  }
  push('split', t('purchasing.optCheapestPerItem'), computeSplitSelection())
  push('consol', t('purchasing.optConsolidated'), computeConsolidatedSelection())
  // Only compare totals when every option resolves to a single currency; mixed
  // (fx-missing) baskets cannot be ranked against each other meaningfully.
  let min = Infinity
  opts.forEach((o) => {
    const keys = Object.keys(o.grand)
    o.comparable = keys.length === 1 ? o.grand[keys[0]] : Infinity
    if (o.comparable < min) min = o.comparable
  })
  opts.forEach((o) => {
    o.cheapest = o.comparable === min && isFinite(min)
  })
  return opts
})

// Freight-assumption presets let the user explore "what if shipping is cheap /
// expensive" without knowing exact costs. Applying a preset seeds every supplier's
// editable freight; the user can still tweak individual suppliers afterwards.
const freightPreset = ref('custom')
function applyFreightPreset(val) {
  if (val === 'custom') return
  const amt = { none: 0, low: 150, medium: 400, high: 800 }[val]
  const ids = new Set()
  rows.value.forEach((r) => (r.candidates || []).forEach((c) => ids.add(c.vendor_id)))
  manualItems.value.forEach((m) => {
    if (m.vendor_company_id) ids.add(m.vendor_company_id)
  })
  const map = {}
  ids.forEach((id) => {
    map[id] = amt
  })
  freightOverrides.value = map
}

const freightPresetOptions = [
  { label: t('purchasing.freightNone'), value: 'none' },
  { label: t('purchasing.freightLow'), value: 'low' },
  { label: t('purchasing.freightMedium'), value: 'medium' },
  { label: t('purchasing.freightHigh'), value: 'high' },
  { label: t('purchasing.freightCustom'), value: 'custom' },
]

const selectionTotals = computed(() => {
  const groups = {}
  const addGoods = (vendorId, name, amount, currency, converted) => {
    const g = groups[vendorId] || (groups[vendorId] = { id: vendorId, name, goods: {}, fxMissing: false })
    g.goods[currency] = (g.goods[currency] || 0) + amount
    if (!converted) g.fxMissing = true
  }
  for (const r of rows.value) {
    const c = effectiveCandidate(r, null)
    if (!c) continue
    const q = r.qty || 0
    const converted = c.converted_unit_cost != null
    const currency = converted ? reportCurrency.value || c.currency : c.currency
    const amt = (converted ? c.converted_unit_cost : c.unit_cost) || 0
    addGoods(c.vendor_id, c.vendor_name, amt * q, currency, converted)
  }
  for (const m of manualItems.value) {
    if (!m.vendor_company_id) continue
    const q = m.qty || 0
    const name = (companies.value.find((x) => x.id === m.vendor_company_id) || {}).name
    const converted = convertManual(m.unit_cost, m.currency)
    if (converted != null) {
      addGoods(m.vendor_company_id, name, converted * q, reportCurrency.value, true)
    } else {
      const currency = m.currency || reportCurrency.value
      addGoods(m.vendor_company_id, name, (m.unit_cost || 0) * q, currency, false)
    }
  }
  return Object.values(groups).map((g) => {
    g.freight = freightAmount(g.id)
    return g
  })
})

const goodsByCurrency = computed(() => {
  const m = {}
  for (const g of selectionTotals.value) {
    for (const [cur, amt] of Object.entries(g.goods || {})) {
      m[cur] = (m[cur] || 0) + amt
    }
  }
  return m
})
const freightTotal = computed(() =>
  selectionTotals.value.reduce((s, g) => s + (g.freight || 0), 0)
)
const grandByCurrency = computed(() => {
  const m = { ...goodsByCurrency.value }
  if (reportCurrency.value) {
    m[reportCurrency.value] = (m[reportCurrency.value] || 0) + freightTotal.value
  }
  return m
})

const fxRefreshing = ref(false)
async function refreshFx() {
  fxRefreshing.value = true
  try {
    await api.post('/api/v1/settings/fx-rates/refresh')
    $q.notify({ type: 'positive', message: t('purchasing.fxRefreshed') })
    await loadPreview()
  } catch {
    $q.notify({ type: 'negative', message: 'FX refresh failed' })
  } finally {
    fxRefreshing.value = false
  }
}
function onFxSaved() {
  fxDialog.value = false
  loadPreview()
}
const anyFxMissing = computed(() => selectionTotals.value.some((g) => g.fxMissing))

function amountsText(map) {
  return Object.entries(map || {})
    .map(([cur, amt]) => `${fmt(amt)} ${cur}`)
    .join(', ')
}

async function loadAux() {
  try {
    const comp = await api.get('/api/v1/companies', { params: { type: 'product_supplier', limit: 500 } })
    const compData = comp.data
    companies.value = Array.isArray(compData) ? compData : (compData.items || [])
  } catch {
    companies.value = []
  }
  try {
    const fx = await api.get('/api/v1/settings/fx-rates')
    fxRates.value = fx.data || null
  } catch {
    fxRates.value = null
  }
}

function asList(resp) {
  if (Array.isArray(resp)) return resp
  if (resp && Array.isArray(resp.items)) return resp.items
  if (resp && resp.data && Array.isArray(resp.data)) return resp.data
  return []
}

async function loadPreview() {
  try {
    const { data } = await api.post('/api/v1/purchasing/purchase-orders/preview', {
      job_ids: props.jobIds || [],
      include_restock: includeRestock.value,
    })
    rows.value = (data.lines || []).map((r, i) => {
      const cand = (r.candidates || [])[0]
      // Restock lines don't carry a top-level unit_cost; seed the editable price
      // field from the resolved supplier candidate so it's visible (and still
      // overridable). Requirement rows drive their price from `chosen` instead.
      const unitCost = r.unit_cost != null ? r.unit_cost : r.is_restock && cand ? cand.unit_cost : null
      return {
        ...r,
        __key: r.requirement_id != null ? `req-${r.requirement_id}` : `restock-${r.product_id}-${i}`,
        chosen: r.selected_vendor_product_id,
        unit_cost: unitCost,
      }
    })
    reportCurrency.value = data.report_currency || null
    freight.value = data.freight || {}
    const overrides = {}
    for (const [sid, f] of Object.entries(freight.value)) {
      if (f && f.base != null) overrides[sid] = f.base
    }
    freightOverrides.value = overrides
  } catch {
    rows.value = []
    freight.value = {}
    freightOverrides.value = {}
  }
}

function removeRow(row) {
  rows.value = rows.value.filter((r) => r.__key !== row.__key)
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      manualItems.value = []
      loadAux()
      loadPreview()
    }
  }
)
watch(includeRestock, () => {
  if (props.modelValue) loadPreview()
})

function addManual() {
  manualItems.value.push({
    __id: ++manualSeq,
    product_id: null,
    name: '',
    sku: '',
    qty: 1,
    unit_cost: null,
    currency: null,
    vendor_company_id: props.allowedSupplierId || null,
  })
}
function removeManual(index) {
  manualItems.value.splice(index, 1)
}

function onSupplierChange(row, val) {
  row.chosen = val
  // For restock rows the editable price should follow the chosen supplier's
  // catalog price (unless the user has manually overridden it elsewhere this is
  // the natural default).
  if (row.is_restock) {
    const c = (row.candidates || []).find((x) => x.vendor_product_id === val)
    if (c && c.unit_cost != null) row.unit_cost = c.unit_cost
  }
}

function close() {
  emit('update:modelValue', false)
}

function buildFreightMap() {
  const used = new Set()
  for (const r of rows.value) {
    let vid = null
    if (r.chosen != null) {
      const c = (r.candidates || []).find((x) => x.vendor_product_id === r.chosen)
      vid = c ? c.vendor_id : null
    } else if (r.is_restock && (r.candidates || []).length) {
      vid = r.candidates[0].vendor_id
    }
    if (vid) used.add(vid)
  }
  for (const m of manualItems.value) {
    if (m.vendor_company_id) used.add(m.vendor_company_id)
  }
  const map = {}
  for (const sid of used) {
    const amt = freightAmount(sid)
    if (amt != null) map[sid] = amt
  }
  return map
}

async function submit() {
  submitting.value = true
  try {
    const lines = rows.value
      .filter((r) => r.requirement_id != null && r.chosen != null)
      .map((r) => ({
        requirement_id: r.requirement_id,
        vendor_product_id: r.chosen,
        qty: r.qty,
      }))
    // Restock rows are sent explicitly as extra items (with product_id) so the
    // user can add/remove them like any other line instead of relying on the
    // server to blindly regenerate every below-limit product. Only include those
    // that resolved a supplier, otherwise an unlinked product would reject the
    // whole build.
    const restockItems = rows.value
      .filter((r) => r.is_restock)
      .map((r) => {
        const c = (r.candidates || [])[0] || {}
        const vendorCompanyId = c.vendor_id || null
        const vendorProductId = c.vendor_product_id || null
        const unitCost = r.unit_cost != null ? r.unit_cost : c.unit_cost ?? null
        const currency = c.currency || r.currency || 'SEK'
        // No linked vendor: fall back to a manual supplier name so the line is
        // still accepted (and the user-provided price is used).
        const supplierName = vendorCompanyId || vendorProductId ? null : 'Manuell'
        return {
          name: r.product_name,
          description: null,
          sku: r.sku || null,
          qty: r.qty,
          unit_cost: unitCost,
          currency,
          vendor_company_id: vendorCompanyId,
          vendor_product_id: vendorProductId,
          supplier_name: supplierName,
          product_id: r.product_id || null,
          is_restock: true,
        }
      })
      .filter(
        (it) =>
          (it.vendor_company_id || it.vendor_product_id || it.supplier_name) &&
          it.unit_cost != null
      )
    const extra_items = [
      ...manualItems.value
        .filter((m) => m.name && (props.allowedSupplierId || m.vendor_company_id))
        .map((m) => ({
          name: m.name,
          sku: m.sku || null,
          qty: m.qty || 1,
          unit_cost: m.unit_cost,
          currency: m.currency,
          vendor_company_id: m.vendor_company_id || props.allowedSupplierId,
          vendor_product_id: m.vendor_product_id || null,
          product_id: m.product_id || null,
        })),
      ...restockItems,
    ]
    const freight = buildFreightMap()

    let result
    if (props.poId) {
      const { data } = await api.post(
        `/api/v1/purchasing/purchase-orders/${props.poId}/add-lines`,
        { lines, extra_items, freight }
      )
      result = data
    } else {
      const { data } = await api.post('/api/v1/purchasing/purchase-orders/build', {
        lines,
        extra_items,
        include_restock: false,
        freight,
      })
      result = data
    }
    const count = Array.isArray(result) ? result.length : 1
    $q.notify({
      type: 'positive',
      message: props.poId
        ? t('purchasing.addToPo')
        : t('purchasing.combinedCreated', { count }),
    })
    emit('done', result)
    close()
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Error' })
  } finally {
    submitting.value = false
  }
}
</script>
