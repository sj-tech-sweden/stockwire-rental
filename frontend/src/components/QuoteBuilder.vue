<template>
  <q-card class="ec-card">
    <q-card-section class="row items-center justify-between q-col-gutter-sm">
      <div class="col">
        <div class="text-h6">{{ t('quotes.title') }}</div>
      </div>
      <div class="col-auto" v-if="authStore.canEdit">
        <q-btn
          color="primary"
          unelevated
          icon="description"
          :label="isPhone ? undefined : t('quotes.generate')"
          :loading="generating"
          @click="generateQuote"
        />
      </div>
    </q-card-section>

    <q-card-section class="q-pt-none">
      <div v-if="loading" class="row justify-center q-py-md">
        <q-spinner color="primary" size="32px" />
      </div>

      <template v-else>
        <div class="row items-center q-gutter-sm q-mb-sm">
          <div class="text-subtitle2">{{ t('quotes.items') }}</div>
          <q-space />
          <q-btn
            v-if="authStore.canEdit"
            flat
            dense
            no-caps
            color="primary"
            icon="inventory_2"
            :label="isPhone ? undefined : t('quotes.addRentalItem')"
            @click="openAdd('rental')"
          />
          <q-btn
            v-if="authStore.canEdit"
            flat
            dense
            no-caps
            color="primary"
            icon="shopping_cart"
            :label="isPhone ? undefined : t('quotes.addVendorItem')"
            @click="openAdd('vendor')"
          />
        </div>

        <div v-if="job && (job.start_date || job.company_name || job.venue_name)" class="text-caption text-grey-8 q-mb-sm">
          <template v-if="job.start_date && job.end_date">
            {{ t('quotes.rentalPeriod') }}: {{ job.start_date }} – {{ job.end_date }} ({{ rentalDays }} {{ t('crew.days') }})
          </template>
          <template v-if="job.company_name"> · {{ job.company_name }}</template>
          <template v-if="job.venue_name"> · {{ job.venue_name }}</template>
        </div>

        <div v-if="itemRows.length" class="column q-gutter-sm">
          <q-card v-for="row in itemRows" :key="`item-${row.id}`" flat bordered class="ec-card">
            <q-card-section>
              <div class="row q-col-gutter-sm items-center">
                <div class="col-12 col-md">
                  <div class="text-subtitle2">{{ row.name }}</div>
                  <div class="text-caption text-grey-7">{{ row.sku }}</div>
                  <q-badge
                    class="q-mt-xs"
                    :color="row.source === 'rental' ? 'primary' : 'secondary'"
                    :label="row.source === 'rental' ? t('quotes.rental') : t('quotes.purchase')"
                  />
                </div>
                <div class="col-6 col-md-2">
                  <q-input
                    :model-value="row.quantity"
                    type="number"
                    min="0"
                    :label="t('quotes.quantity')"
                    outlined
                    dense
                    :disable="!authStore.canEdit"
                    :debounce="400"
                    @update:model-value="val => updateRow(row, 'quantity', val)"
                  />
                </div>
                <div class="col-6 col-md-2">
                  <q-input
                    :model-value="row.unitPrice"
                    type="number"
                    min="0"
                    step="0.01"
                    :label="row.source === 'rental' ? t('quotes.pricePerDay') : t('quotes.unitPrice')"
                    outlined
                    dense
                    :disable="!authStore.canEdit"
                    :debounce="400"
                    @update:model-value="val => updateRow(row, 'unitPrice', val)"
                  />
                </div>
                <div class="col-12 col-md-2 text-right">
                  <div class="text-caption text-grey-7">{{ t('quotes.lineTotal') }}</div>
                  <div class="text-subtitle2">{{ formatMoney(row.lineTotal) }}</div>
                  <div v-if="row.source === 'rental'" class="text-caption text-grey-7">
                    {{ row.days }} {{ t('crew.days') }} × {{ formatMoney(row.unitPrice) }}
                  </div>
                </div>
                <div class="col-12 col-md-auto" v-if="authStore.canEdit">
                  <q-btn flat dense no-caps color="negative" icon="delete" :label="t('scan.clear')" @click="removeRow(row)" />
                </div>
              </div>
            </q-card-section>
          </q-card>
        </div>
        <div v-else class="ec-empty-state">
          <q-icon name="receipt_long" size="32px" class="ec-empty-state__icon" />
          <div class="ec-empty-state__title">{{ t('quotes.noItems') }}</div>
        </div>

        <div class="text-subtitle2 q-mt-lg q-mb-sm">{{ t('quotes.crew') }}</div>
        <div v-if="crewLineRows.length" class="column q-gutter-sm">
          <q-card v-for="row in crewLineRows" :key="`crew-${row.id}`" flat bordered class="ec-card">
            <q-card-section>
              <div class="row q-col-gutter-sm items-center">
                <div class="col-12 col-md">
                  <div class="text-subtitle2">{{ row.role }}</div>
                </div>
                <div class="col-6 col-md-2">
                  <q-input
                    :model-value="row.quantity"
                    type="number"
                    min="0"
                    :label="t('quotes.quantity')"
                    outlined
                    dense
                    :disable="!authStore.canEdit"
                    :debounce="400"
                    @update:model-value="val => updateCrewField(row, 'quantity', val)"
                  />
                </div>
                <div class="col-6 col-md-2">
                  <q-select
                    :model-value="row.rate_basis"
                    :options="basisOptions"
                    :label="t('crew.rateBasis')"
                    outlined
                    dense
                    emit-value
                    map-options
                    :disable="!authStore.canEdit"
                    @update:model-value="val => updateCrewField(row, 'rate_basis', val)"
                  />
                </div>
                <template v-if="row.rate_basis === 'daily'">
                  <div class="col-6 col-md-2">
                    <q-input
                      :model-value="row.days"
                      type="number"
                      min="0"
                      step="0.5"
                      :label="t('crew.days')"
                      outlined
                      dense
                      :disable="!authStore.canEdit"
                      :debounce="400"
                      @update:model-value="val => updateCrewField(row, 'days', val)"
                    />
                  </div>
                  <div class="col-6 col-md-2">
                    <q-input
                      :model-value="row.daily_rate"
                      type="number"
                      min="0"
                      step="0.01"
                      :label="t('crew.dailyRate')"
                      outlined
                      dense
                      :disable="!authStore.canEdit"
                      :debounce="400"
                      @update:model-value="val => updateCrewField(row, 'daily_rate', val)"
                    />
                  </div>
                </template>
                <template v-else>
                  <div class="col-6 col-md-2">
                    <q-input
                      :model-value="row.hours"
                      type="number"
                      min="0"
                      step="0.5"
                      :label="t('quotes.hours')"
                      outlined
                      dense
                      :disable="!authStore.canEdit"
                      :debounce="400"
                      @update:model-value="val => updateCrewField(row, 'hours', val)"
                    />
                  </div>
                  <div class="col-6 col-md-2">
                    <q-input
                      :model-value="row.hourly_rate"
                      type="number"
                      min="0"
                      step="0.01"
                      :label="t('quotes.rate')"
                      outlined
                      dense
                      :disable="!authStore.canEdit"
                      :debounce="400"
                      @update:model-value="val => updateCrewField(row, 'hourly_rate', val)"
                    />
                  </div>
                </template>
                <div class="col-12 col-md-2 text-right">
                  <div class="text-caption text-grey-7">{{ t('quotes.lineTotal') }}</div>
                  <div class="text-subtitle2">{{ formatMoney(row.lineTotal) }}</div>
                </div>
              </div>
            </q-card-section>
          </q-card>
        </div>
        <div v-else class="ec-empty-state q-mt-sm">
          <div class="ec-empty-state__title">{{ t('quotes.noCrew') }}</div>
        </div>

        <q-separator class="q-my-md" />

        <div class="row q-col-gutter-md">
          <div class="col text-right">
            <div class="text-caption text-grey-7">{{ t('quotes.subtotal') }}</div>
            <div class="text-subtitle1">{{ formatMoney(subtotal) }}</div>
          </div>
          <div class="col text-right">
            <div class="text-caption text-grey-7">{{ t('quotes.vat') }} ({{ Math.round(vatRate * 100) }}%)</div>
            <div class="text-subtitle1">{{ formatMoney(vatAmount) }}</div>
          </div>
          <div class="col text-right">
            <div class="text-caption text-grey-7">{{ t('quotes.total') }}</div>
            <div class="text-h6">{{ formatMoney(total) }}</div>
          </div>
        </div>
      </template>
    </q-card-section>

    <q-dialog v-model="addDialogOpen" persistent>
      <q-card style="min-width: 320px" class="ec-card">
        <q-card-section>
          <div class="text-h6">{{ addMode === 'rental' ? t('quotes.addRentalItem') : t('quotes.addVendorItem') }}</div>
        </q-card-section>
        <q-card-section class="q-pt-none column q-gutter-sm">
          <template v-if="addMode === 'rental'">
            <q-select
              v-model="addSelection"
              :options="addOptions"
              :label="t('quotes.selectProduct')"
              outlined
              dense
              use-input
              emit-value
              map-options
              :option-label="opt => opt.label"
              :option-value="opt => opt.value"
              @filter="filterAddOptions"
            />
          </template>
          <template v-else>
            <q-btn
              color="primary"
              outline
              no-caps
              :label="t('vendorCatalog.selectVendorItem')"
              icon="search"
              @click="pickerOpen = true"
            />
            <div v-if="addSelection" class="text-subtitle2">
              {{ addSelection.label || addSelection.name }}
            </div>
          </template>
          <q-input v-model.number="addQty" type="number" min="1" :label="t('quotes.quantity')" outlined dense />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="addDialogOpen = false" />
          <q-btn color="primary" unelevated :label="t('app.actions.add')" :disable="!addSelection" @click="addItem" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <VendorProductPicker v-model="pickerOpen" :title="t('vendorCatalog.selectVendorItem')" @select="onPickVendorProduct" />
  </q-card>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../boot/axios'
import { useJobsStore } from '../stores/jobs'
import { useInventoryStore } from '../stores/inventory'
import { useCrewStore } from '../stores/crew'
import { useAuthStore } from '../stores/auth'
import VendorProductPicker from './VendorProductPicker.vue'
import { Notify } from 'quasar'

const props = defineProps({
  jobId: { type: Number, required: true },
  jobCode: { type: String, default: '' },
})

const { t } = useI18n()
const jobsStore = useJobsStore()
const inventoryStore = useInventoryStore()
const crewStore = useCrewStore()
const authStore = useAuthStore()

const loading = ref(false)
const generating = ref(false)
const vendorProductMap = ref({})
const pickerOpen = ref(false)
const quotesSettings = ref({ default_markup_pct: 30, vat_rate: 0.25 })
const crewRows = ref([])
const job = ref(null)

// Number of days the equipment is rented for (derived from the job's start/end
// dates). Rental lines are priced per day x days x quantity.
const rentalDays = computed(() => {
  const s = job.value?.start_date
  const e = job.value?.end_date
  if (s && e) {
    const start = new Date(s)
    const end = new Date(e)
    const days = Math.round((end - start) / 86400000) + 1
    return days > 0 ? days : 1
  }
  return 1
})

const addDialogOpen = ref(false)
const addMode = ref('rental')
const addSelection = ref(null)
const addQty = ref(1)

const markupFactor = computed(() => 1 + (Number(quotesSettings.value.default_markup_pct) || 0) / 100)
const vatRate = computed(() => Number(quotesSettings.value.vat_rate) || 0)

const isPhone = computed(() => window.innerWidth < 600)

const addOptions = ref([])

const itemRows = computed(() => {
  const reqs = (jobsStore.requirements || []).filter(r => r.job_id === props.jobId)
  return reqs.map(r => {
    if (r.vendor_product_id) {
      const vp = vendorProductMap.value[r.vendor_product_id]
      const cost = Number(vp?.unit_cost ?? 0)
      const unitPrice = r.unit_price != null ? Number(r.unit_price) : cost * markupFactor.value
      return {
        id: r.id,
        source: 'purchase',
        name: vp?.name || `${t('quotes.vendor')} #${r.vendor_product_id}`,
        sku: vp?.sku || '—',
        quantity: Number(r.quantity_required || 0),
        unitPrice,
        lineTotal: unitPrice * Number(r.quantity_required || 0),
      }
    }
    const p = (inventoryStore.products || []).find(p => p.id === r.product_id)
    const defaultPrice = p ? Number(p.rental_price ?? p.daily_rate ?? 0) : 0
    const unitPrice = r.unit_price != null ? Number(r.unit_price) : defaultPrice
    const quantity = Number(r.quantity_required || 0)
    return {
      id: r.id,
      source: 'rental',
      name: p?.name || `${t('quotes.product')} #${r.product_id}`,
      sku: p?.sku || '—',
      quantity,
      days: rentalDays.value,
      unitPrice,
      lineTotal: unitPrice * rentalDays.value * quantity,
    }
  })
})

const basisOptions = [
  { label: t('crew.hourly'), value: 'hourly' },
  { label: t('crew.daily'), value: 'daily' },
]

const crewLineRows = computed(() =>
  (crewRows.value || []).map(c => {
    const qty = Number(c.quantity || 0)
    const basis = c.rate_basis || 'hourly'
    let rate, lineTotal
    if (basis === 'daily') {
      const days = c.days != null ? Number(c.days) : 1
      const dailyRate = c.daily_rate != null ? Number(c.daily_rate) : 0
      rate = dailyRate
      lineTotal = dailyRate * qty * days
      return {
        id: c.id,
        role: c.crew_role_name || c.custom_role_name || t('crew.unknownRole'),
        quantity: qty,
        rate_basis: basis,
        hours: c.hours != null ? Number(c.hours) : 8,
        daily_rate: dailyRate,
        days,
        hourly_rate: c.hourly_rate != null ? Number(c.hourly_rate) : 0,
        rate,
        lineTotal,
      }
    }
    const hours = c.hours != null ? Number(c.hours) : 8
    const hourlyRate = c.hourly_rate != null ? Number(c.hourly_rate) : 0
    rate = hourlyRate
    lineTotal = hourlyRate * qty * hours
    return {
      id: c.id,
      role: c.crew_role_name || c.custom_role_name || t('crew.unknownRole'),
      quantity: qty,
      rate_basis: basis,
      hours,
      daily_rate: c.daily_rate != null ? Number(c.daily_rate) : 0,
      days: c.days != null ? Number(c.days) : 1,
      hourly_rate: hourlyRate,
      rate,
      lineTotal,
    }
  }),
)

const subtotal = computed(
  () =>
    itemRows.value.reduce((s, r) => s + r.lineTotal, 0) +
    crewLineRows.value.reduce((s, r) => s + r.lineTotal, 0),
)
const vatAmount = computed(() => subtotal.value * vatRate.value)
const total = computed(() => subtotal.value + vatAmount.value)

function formatMoney(value) {
  const n = Number(value || 0)
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function load() {
  loading.value = true
  try {
    const [qsRes, crewRes, jobRes] = await Promise.all([
      api.get('/api/v1/quotes/settings'),
      crewStore.fetchJobCrewRequirements(props.jobId),
      api.get(`/api/v1/jobs/${props.jobId}`).catch(() => null),
    ])
    if (qsRes.data) quotesSettings.value = qsRes.data
    crewRows.value = crewRes || []
    job.value = jobRes?.data || null
    await loadReferencedVendorProducts()
    if (!inventoryStore.products || !inventoryStore.products.length) {
      try {
        await inventoryStore.fetchAll()
      } catch (e) {
        /* non-fatal: rental prices simply unavailable */
      }
    }
  } catch (e) {
    Notify.create({ type: 'negative', message: t('quotes.failedToLoad') })
  } finally {
    loading.value = false
  }
}

// Fetch only the supplier products actually referenced by this job's
// requirements, so we never load the full 16k+ item catalog into the browser.
async function loadReferencedVendorProducts() {
  const ids = (jobsStore.requirements || [])
    .filter((r) => r.job_id === props.jobId && r.vendor_product_id)
    .map((r) => r.vendor_product_id)
  if (!ids.length) {
    vendorProductMap.value = {}
    return
  }
  try {
    const { data } = await api.get('/api/v1/vendor-products', {
      params: { ids: ids.join(','), limit: ids.length, active_only: false },
    })
    const map = {}
    for (const v of data || []) map[v.id] = v
    vendorProductMap.value = map
  } catch {
    vendorProductMap.value = {}
  }
}

async function loadCrewRows() {
  try {
    crewRows.value = (await crewStore.fetchJobCrewRequirements(props.jobId)) || []
  } catch {
    /* keep current rows on transient error */
  }
}

// Keep the quote's crew lines in sync with edits made elsewhere on the job.
// Note: Pinia unwraps store refs, so read `crewStore.crewRevision` (not `.value`).
watch(() => crewStore.crewRevision, loadCrewRows)

function openAdd(mode) {
  addMode.value = mode
  addSelection.value = null
  addQty.value = 1
  addOptions.value =
    mode === 'rental'
      ? (inventoryStore.products || []).map(p => ({
          label: `${p.name}${p.sku ? ' (' + p.sku + ')' : ''}`,
          value: p.id,
          rentalPrice: Number(p.rental_price ?? p.daily_rate ?? 0),
        }))
      : []
  addDialogOpen.value = true
}

function onPickVendorProduct(product) {
  addSelection.value = { value: product.id, label: product.name, cost: Number(product.unit_cost ?? 0) }
}

async function addItem() {
  // addSelection is the option object (no emit-value) or the id (with emit-value);
  // normalise to a numeric id and reject free-text input that has no match.
  const raw = addSelection.value
  const selectedId = raw && typeof raw === 'object' ? (raw.value ?? raw.id) : raw
  const id = Number(selectedId)
  if (!Number.isFinite(id) || id <= 0) {
    Notify.create({ type: 'negative', message: t('quotes.failedToAdd') })
    return
  }
  const payload = { job_id: props.jobId, quantity_required: Number(addQty.value) || 1 }
  if (addMode.value === 'rental') payload.product_id = id
  else payload.vendor_product_id = id
  try {
    await jobsStore.createRequirement(payload)
    addDialogOpen.value = false
    await loadReferencedVendorProducts()
    Notify.create({ type: 'positive', message: t('quotes.itemAdded') })
  } catch (e) {
    Notify.create({ type: 'negative', message: e?.response?.data?.detail || t('quotes.failedToAdd') })
  }
}

async function updateRow(row, field, value) {
  const payload = {}
  if (field === 'quantity') payload.quantity_required = Number(value) || 0
  if (field === 'unitPrice') payload.unit_price = value === '' || value == null ? null : Number(value)
  try {
    await jobsStore.updateRequirement(row.id, payload)
  } catch (e) {
    Notify.create({ type: 'negative', message: e?.response?.data?.detail || t('quotes.failedToUpdate') })
  }
}

async function removeRow(row) {
  try {
    await jobsStore.deleteRequirement(row.id)
  } catch (e) {
    Notify.create({ type: 'negative', message: e?.response?.data?.detail || t('quotes.failedToRemove') })
  }
}

async function updateCrewField(crewRow, field, value) {
  const isStr = field === 'rate_basis'
  const num = value === '' || value == null ? null : Number(value)
  const storeVal = isStr ? value : num
  const payloadValue = field === 'quantity' && num == null ? 0 : storeVal
  const payload = { [field]: payloadValue }
  try {
    await crewStore.updateJobCrewRequirement(props.jobId, crewRow.id, payload)
    const idx = crewRows.value.findIndex(c => c.id === crewRow.id)
    if (idx !== -1) crewRows.value[idx] = { ...crewRows.value[idx], [field]: storeVal }
  } catch (e) {
    Notify.create({ type: 'negative', message: e?.response?.data?.detail || t('quotes.failedToUpdate') })
  }
}

function filterAddOptions(val, update, abort) {
  const needle = (val || '').toLowerCase()
  const source =
    addMode.value === 'rental'
      ? (inventoryStore.products || [])
      : Object.values(vendorProductMap.value || {})
  const mapped = source.map(item =>
    addMode.value === 'rental'
      ? {
          label: `${item.name}${item.sku ? ' (' + item.sku + ')' : ''}`,
          value: item.id,
          rentalPrice: Number(item.rental_price ?? item.daily_rate ?? 0),
        }
      : {
          label: `${item.name}${item.sku ? ' (' + item.sku + ')' : ''}`,
          value: item.id,
          cost: Number(item.unit_cost ?? 0),
        },
  )
  update(() => {
    addOptions.value = needle
      ? mapped.filter(o => o.label.toLowerCase().includes(needle))
      : mapped
  })
}

async function generateQuote() {
  generating.value = true
  try {
    const resp = await api.post(`/api/v1/quotes/jobs/${props.jobId}/generate`, {}, { responseType: 'blob' })
    const blobUrl = URL.createObjectURL(new Blob([resp.data], { type: 'application/pdf' }))
    const a = document.createElement('a')
    a.href = blobUrl
    a.download = `quote_${props.jobCode || props.jobId}.pdf`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(blobUrl)
    Notify.create({ type: 'positive', message: t('quotes.generated') })
  } catch (e) {
    Notify.create({ type: 'negative', message: t('quotes.failedToGenerate') })
  } finally {
    generating.value = false
  }
}

onMounted(load)
</script>
