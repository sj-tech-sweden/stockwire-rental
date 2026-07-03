<template>
  <q-page class="q-pa-md ec-page">
    <div class="row items-center justify-between q-col-gutter-sm q-mb-md">
      <div class="col-auto">
        <q-btn flat icon="arrow_back" :label="t('jobs.backToJobs')" @click="goBack" />
      </div>
      <div class="col">
        <div class="text-h5">{{ currentJob?.job_code || t('jobs.viewJob') }}</div>
      </div>
      <div class="col-auto" v-if="currentJob && authStore.canEdit">
        <q-btn color="primary" unelevated :label="t('jobs.saveChanges')" :loading="saving" @click="saveChanges" />
      </div>
    </div>

    <div v-if="pageLoading" class="row justify-center q-py-xl">
      <q-spinner color="primary" size="48px" />
    </div>

    <div v-else-if="!currentJob" class="q-gutter-md">
      <q-banner class="bg-warning text-dark rounded-borders">
        {{ t('jobs.jobNotFound') }}
      </q-banner>
      <q-btn color="primary" unelevated :label="t('jobs.backToJobs')" @click="goBack" />
    </div>

    <div v-else class="column q-gutter-md">
      <q-card class="ec-card">
        <q-card-section>
          <div class="row q-col-gutter-md items-start">
            <div class="col-12 col-md">
              <div class="row items-center q-gutter-sm q-mb-sm">
                <div class="text-h6">{{ currentJob.job_code }}</div>
                <q-badge :color="statusColor(currentJob.status)" :label="statusLabel(currentJob.status)" />
              </div>
              <div class="text-body1 q-mb-sm">{{ currentJob.description || t('jobs.noDescription') }}</div>
              <div class="text-caption text-grey-7">{{ t('jobs.customer') }}: {{ customerDisplayName }}</div>
              <div class="text-caption text-grey-7">{{ t('jobs.venue') }}: {{ venueDisplayName }}</div>
              <div class="text-caption text-grey-7">{{ t('jobs.project') }}: {{ projectDisplayName }}</div>
              <div class="text-caption text-grey-7">{{ formattedDateRange }}</div>
            </div>
            <div class="col-12 col-md-auto">
              <div class="row q-gutter-sm">
                <q-btn
                  color="primary"
                  outline
                  icon="shopping_cart_checkout"
                  :label="t('scan.scanOutJob')"
                  :to="buildScanJobLink('job_out', currentJob)"
                />
                <q-btn
                  color="primary"
                  outline
                  icon="assignment_return"
                  :label="t('scan.scanInJob')"
                  :to="buildScanJobLink('job_in', currentJob)"
                />
              </div>
            </div>
          </div>
        </q-card-section>
      </q-card>

      <q-card class="ec-card">
        <q-card-section class="row items-center justify-between q-col-gutter-sm">
          <div class="col">
            <div class="text-h6">{{ t('jobs.viewJob') }}</div>
          </div>
          <div class="col-auto" v-if="authStore.canEdit">
            <q-btn color="primary" unelevated :label="t('jobs.saveChanges')" :loading="saving" @click="saveChanges" />
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-form ref="formRef" @submit.prevent="saveChanges">
            <div class="row q-col-gutter-sm">
              <div class="col-12 col-md-6">
                <q-input
                  v-model="form.job_code"
                  :label="t('jobs.jobCode')"
                  outlined
                  dense
                  :disable="!authStore.canEdit"
                  :rules="[v => !!v || t('login.required')]"
                />
              </div>
              <div class="col-12 col-md-6">
                <q-select
                  v-model="form.status"
                  :options="statusOptions"
                  :label="t('jobs.status')"
                  outlined
                  dense
                  emit-value
                  map-options
                  :disable="!authStore.canEdit"
                  :rules="[v => !!v || t('login.required')]"
                />
              </div>
            </div>

            <q-input
              v-model="form.description"
              :label="t('jobs.description')"
              type="textarea"
              autogrow
              outlined
              dense
              class="q-mt-sm"
              :disable="!authStore.canEdit"
            />

            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-12 col-md-6">
                <q-select
                  v-model="form.customer_id"
                  :options="filteredCustomerOptions"
                  :label="t('jobs.customer')"
                  outlined
                  dense
                  clearable
                  use-input
                  fill-input
                  input-debounce="0"
                  emit-value
                  map-options
                  :disable="!authStore.canEdit"
                  @filter="filterCustomerOptions"
                />
              </div>
              <div class="col-12 col-md-6">
                <q-select
                  v-model="form.venue_id"
                  :options="filteredVenueOptions"
                  :label="t('jobs.venue')"
                  outlined
                  dense
                  clearable
                  use-input
                  fill-input
                  input-debounce="0"
                  emit-value
                  map-options
                  :disable="!authStore.canEdit"
                  @filter="filterVenueOptions"
                />
              </div>
            </div>

            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-12 col-md-6">
                <q-select
                  v-model="form.project_id"
                  :options="projectOptions"
                  :label="t('jobs.project')"
                  outlined
                  dense
                  clearable
                  emit-value
                  map-options
                  :disable="!authStore.canEdit"
                />
              </div>
              <div class="col-12 col-md-6">
                <q-input
                  v-model="form.location_in_venue"
                  :label="t('jobs.locationInVenue')"
                  outlined
                  dense
                  clearable
                  :disable="!authStore.canEdit"
                />
              </div>
            </div>

            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-12 col-md-6">
                <q-input v-model="form.start_date" :label="t('jobs.startDate')" type="date" outlined dense :disable="!authStore.canEdit" />
              </div>
              <div class="col-12 col-md-6">
                <q-input v-model="form.end_date" :label="t('jobs.endDate')" type="date" outlined dense :disable="!authStore.canEdit" />
              </div>
            </div>

            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-12 col-md-4">
                <q-input
                  v-model.number="form.sales_price"
                  :label="t('jobs.salesPrice')"
                  :suffix="activeCurrencyCode"
                  type="number"
                  min="0"
                  step="0.01"
                  outlined
                  dense
                  :disable="!authStore.canEdit"
                />
              </div>
              <div class="col-12 col-md-4 flex items-center">
                <q-toggle v-model="form.invoice_paid" :label="t('jobs.invoicePaid')" :disable="!authStore.canEdit" />
              </div>
              <div class="col-12 col-md-4">
                <q-input
                  v-model="form.invoice_paid_at"
                  :label="t('jobs.invoicePaidAt')"
                  type="date"
                  outlined
                  dense
                  :disable="!authStore.canEdit || !form.invoice_paid"
                />
              </div>
            </div>

            <q-input
              v-model="form.notes"
              :label="t('jobs.notes')"
              type="textarea"
              autogrow
              outlined
              dense
              class="q-mt-sm"
              :disable="!authStore.canEdit"
            />
          </q-form>
        </q-card-section>
      </q-card>

      <q-card class="ec-card">
        <q-card-section class="row items-center justify-between q-col-gutter-sm">
          <div class="col">
            <div class="text-h6">{{ t('jobs.productRequirements') }}</div>
            <div class="text-caption text-grey-7">{{ t('jobs.pickList') }}</div>
          </div>
          <div class="col-auto" v-if="authStore.canEdit">
            <q-btn color="primary" unelevated icon="add" :label="t('jobs.addProductRequirements')" @click="requirementDialogOpen = true" />
          </div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <div class="text-subtitle2 q-mb-sm">{{ t('jobs.requirementsSummary') }}</div>
          <div class="row q-col-gutter-sm q-mb-md">
            <div class="col-12 col-sm-6 col-lg-3">
              <q-card flat bordered>
                <q-card-section>
                  <div class="text-caption text-grey-7">{{ t('jobs.totalWeight') }}</div>
                  <div class="text-subtitle1">{{ t('jobs.weightKg', { value: formatDecimal(summaryTotals.weightKg) }) }}</div>
                </q-card-section>
              </q-card>
            </div>
            <div class="col-12 col-sm-6 col-lg-3">
              <q-card flat bordered>
                <q-card-section>
                  <div class="text-caption text-grey-7">{{ t('jobs.totalVolume') }}</div>
                  <div class="text-subtitle1">{{ t('jobs.volumeM3', { value: formatDecimal(summaryTotals.volumeM3) }) }}</div>
                </q-card-section>
              </q-card>
            </div>
            <div class="col-12 col-sm-6 col-lg-3">
              <q-card flat bordered>
                <q-card-section>
                  <div class="text-caption text-grey-7">{{ t('jobs.totalReplacementCost') }}</div>
                  <div class="text-subtitle1">{{ formatMoney(summaryTotals.replacementCost) }}</div>
                </q-card-section>
              </q-card>
            </div>
            <div class="col-12 col-sm-6 col-lg-3">
              <q-card flat bordered>
                <q-card-section>
                  <div class="text-caption text-grey-7">{{ t('jobs.projectedPriceFromRequirements') }}</div>
                  <div class="text-subtitle1">{{ formatMoney(summaryTotals.projectedPrice) }}</div>
                </q-card-section>
              </q-card>
            </div>
          </div>

          <div v-if="jobRequirementRows.length" class="column q-gutter-sm">
            <q-card v-for="row in jobRequirementRows" :key="row.product_id" flat bordered>
              <q-card-section>
                <div class="row q-col-gutter-sm items-center">
                  <div class="col-12 col-md">
                    <div class="text-subtitle2">{{ row.product?.name || `${t('jobs.productName')} #${row.product_id}` }}</div>
                    <div class="text-caption text-grey-7">{{ row.product?.sku || '—' }}</div>
                    <div class="row q-gutter-xs q-mt-sm">
                      <q-badge color="primary" text-color="white" :label="`${t('jobs.requiredQty')}: ${Number(row.quantity_required || 0)}`" />
                      <q-badge color="info" text-color="white" :label="`${t('scan.picked')}: ${Number(row.quantity_picked || 0)}`" />
                    </div>
                  </div>
                  <div class="col-12 col-md-2">
                    <q-input
                      :model-value="Number(row.quantity_required || 0)"
                      type="number"
                      min="0"
                      :label="t('jobs.requiredQty')"
                      outlined
                      dense
                      :disable="!authStore.canEdit"
                      @update:model-value="value => setRequirementQty(row.product_id, value)"
                    />
                  </div>
                  <div class="col-12 col-md-auto" v-if="authStore.canEdit">
                    <q-btn flat dense no-caps color="negative" icon="delete" :label="t('scan.clear')" @click="removeRequirementRow(row.product_id)" />
                  </div>
                </div>
              </q-card-section>
            </q-card>
          </div>
          <q-banner v-else class="bg-grey-2 text-grey-8 rounded-borders">
            {{ t('jobs.noRequirements') }}
          </q-banner>

          <div class="text-subtitle2 q-mt-lg q-mb-sm">{{ t('jobs.requirementsSummary') }}</div>
          <div class="row q-col-gutter-sm">
            <div class="col-12 col-sm-6 col-lg-3">
              <q-card flat bordered>
                <q-card-section>
                  <div class="text-caption text-grey-7">{{ t('jobs.totalWeight') }}</div>
                  <div class="text-subtitle1">{{ t('jobs.weightKg', { value: formatDecimal(summaryTotals.weightKg) }) }}</div>
                </q-card-section>
              </q-card>
            </div>
            <div class="col-12 col-sm-6 col-lg-3">
              <q-card flat bordered>
                <q-card-section>
                  <div class="text-caption text-grey-7">{{ t('jobs.totalVolume') }}</div>
                  <div class="text-subtitle1">{{ t('jobs.volumeM3', { value: formatDecimal(summaryTotals.volumeM3) }) }}</div>
                </q-card-section>
              </q-card>
            </div>
            <div class="col-12 col-sm-6 col-lg-3">
              <q-card flat bordered>
                <q-card-section>
                  <div class="text-caption text-grey-7">{{ t('jobs.totalReplacementCost') }}</div>
                  <div class="text-subtitle1">{{ formatMoney(summaryTotals.replacementCost) }}</div>
                </q-card-section>
              </q-card>
            </div>
            <div class="col-12 col-sm-6 col-lg-3">
              <q-card flat bordered>
                <q-card-section>
                  <div class="text-caption text-grey-7">{{ t('jobs.projectedPriceFromRequirements') }}</div>
                  <div class="text-subtitle1">{{ formatMoney(summaryTotals.projectedPrice) }}</div>
                </q-card-section>
              </q-card>
            </div>
          </div>
        </q-card-section>
      </q-card>
    </div>

    <JobProductRequirementDialog
      v-model="requirementDialogOpen"
      v-model:requirementRows="requirementRows"
      :products="inventoryStore.products"
      :start-date="form.start_date"
      :end-date="form.end_date"
      :job-id="currentJob?.id || null"
    />
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'

import { JOB_STATUSES, useJobsStore } from '../stores/jobs'
import { useInventoryStore } from '../stores/inventory'
import { useCustomersStore } from '../stores/customers'
import { useVenuesStore } from '../stores/venues'
import { useProjectsStore } from '../stores/projects'
import { useAuthStore } from '../stores/auth'
import { useSettingsStore } from '../stores/settings'
import { normalizeCurrencyCode } from '../constants/currencies'
import { buildScanJobLink } from '../utils/scan-workflow'
import JobProductRequirementDialog from '../components/JobProductRequirementDialog.vue'

const $q = useQuasar()
const route = useRoute()
const router = useRouter()
const { t, locale } = useI18n()

const jobsStore = useJobsStore()
const inventoryStore = useInventoryStore()
const customersStore = useCustomersStore()
const venuesStore = useVenuesStore()
const projectsStore = useProjectsStore()
const authStore = useAuthStore()
const settingsStore = useSettingsStore()

const pageLoading = ref(false)
const saving = ref(false)
const formRef = ref(null)
const requirementDialogOpen = ref(false)
const filteredCustomerOptions = ref([])
const filteredVenueOptions = ref([])
const form = ref(emptyForm())
const requirementRows = ref([])

const activeCurrencyCode = computed(() => normalizeCurrencyCode(settingsStore.companyProfile?.currency, 'SEK'))
const currentJobId = computed(() => Number(route.params.jobId || 0))
const currentJob = computed(() => jobsStore.jobs.find(job => job.id === currentJobId.value) || null)

const statusOptions = computed(() => JOB_STATUSES.map(status => ({ label: statusLabel(status.value), value: status.value })))
const customerOptions = computed(() => customersStore.customers.map(customer => ({
  label: customer.email ? `${customer.name} · ${customer.email}` : customer.name,
  value: customer.id,
})))
const venueOptions = computed(() => venuesStore.venues.map(venue => ({
  label: [venue.name, venue.city].filter(Boolean).join(' · '),
  value: venue.id,
})))
const projectOptions = computed(() => projectsStore.projects.map(project => ({
  label: project.name,
  value: project.id,
})))

function emptyForm() {
  return {
    job_code: '',
    status: 'draft',
    description: '',
    customer_id: null,
    customer_name: '',
    venue_id: null,
    venue_name: '',
    project_id: null,
    location_in_venue: '',
    start_date: null,
    end_date: null,
    sales_price: null,
    invoice_paid: false,
    invoice_paid_at: null,
    notes: '',
  }
}

function normalizeDate(value) {
  if (!value) return null
  if (typeof value === 'string') {
    const match = value.match(/^(\d{4}-\d{2}-\d{2})/)
    return match ? match[1] : null
  }
  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    const year = value.getFullYear()
    const month = String(value.getMonth() + 1).padStart(2, '0')
    const day = String(value.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }
  return null
}

function dateSortKey(value) {
  const normalized = normalizeDate(value)
  return normalized ? Number(normalized.replaceAll('-', '')) : null
}

function formatDate(value) {
  const normalized = normalizeDate(value)
  if (!normalized) return '—'
  const [year, month, day] = normalized.split('-').map(Number)
  const currentLocale = String(locale.value || 'en').toLowerCase().startsWith('sv') ? 'sv-SE' : 'en-US'
  return new Date(year, month - 1, day).toLocaleDateString(currentLocale)
}

function formatMoney(value) {
  const amount = Number(value || 0)
  const currentCurrency = normalizeCurrencyCode(settingsStore.companyProfile?.currency, 'SEK')
  try {
    return new Intl.NumberFormat('sv-SE', {
      style: 'currency',
      currency: currentCurrency,
      maximumFractionDigits: 2,
    }).format(amount)
  } catch {
    return new Intl.NumberFormat('sv-SE', {
      style: 'currency',
      currency: 'SEK',
      maximumFractionDigits: 2,
    }).format(amount)
  }
}

function formatDecimal(value) {
  return new Intl.NumberFormat('sv-SE', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(Number(value || 0))
}

function statusColor(value) {
  return JOB_STATUSES.find(status => status.value === value)?.color ?? 'grey'
}

function statusLabel(value) {
  const normalized = String(value || '').toLowerCase()
  const mapping = {
    draft: t('jobs.statusDraft'),
    confirmed: t('jobs.statusConfirmed'),
    in_progress: t('jobs.statusInProgress'),
    completed: t('jobs.statusCompleted'),
    cancelled: t('jobs.statusCancelled'),
  }
  return mapping[normalized] || value
}

function cloneRequirementRows(rows = []) {
  return rows.map(row => ({
    ...row,
    product_id: Number(row.product_id),
    quantity_required: Number(row.quantity_required || 0),
    quantity_picked: Number(row.quantity_picked || 0),
    notes: row.notes || null,
  }))
}

function filterCustomerOptions(val, update) {
  update(() => {
    const needle = val.trim().toLowerCase()
    if (!needle) {
      filteredCustomerOptions.value = customerOptions.value
      return
    }
    filteredCustomerOptions.value = customerOptions.value.filter(option => option.label.toLowerCase().includes(needle))
  })
}

function filterVenueOptions(val, update) {
  update(() => {
    const needle = val.trim().toLowerCase()
    if (!needle) {
      filteredVenueOptions.value = venueOptions.value
      return
    }
    filteredVenueOptions.value = venueOptions.value.filter(option => option.label.toLowerCase().includes(needle))
  })
}

watch(customerOptions, (options) => {
  filteredCustomerOptions.value = options
}, { immediate: true })

watch(venueOptions, (options) => {
  filteredVenueOptions.value = options
}, { immediate: true })

watch(() => form.value.invoice_paid, (paid) => {
  if (paid && !form.value.invoice_paid_at) {
    form.value.invoice_paid_at = normalizeDate(new Date())
  }
  if (!paid) {
    form.value.invoice_paid_at = null
  }
})

watch(() => form.value.start_date, (startDate) => {
  const normalizedStart = normalizeDate(startDate)
  if (!normalizedStart) return

  if (form.value.start_date !== normalizedStart) {
    form.value.start_date = normalizedStart
  }

  const normalizedEnd = normalizeDate(form.value.end_date)
  if (!normalizedEnd || dateSortKey(normalizedEnd) < dateSortKey(normalizedStart)) {
    form.value.end_date = normalizedStart
    return
  }

  if (form.value.end_date !== normalizedEnd) {
    form.value.end_date = normalizedEnd
  }
})

const productById = computed(() => {
  const map = new Map()
  for (const product of inventoryStore.products || []) map.set(product.id, product)
  return map
})

const jobRequirementRows = computed(() => (
  cloneRequirementRows(requirementRows.value)
    .map(row => ({ ...row, product: productById.value.get(row.product_id) || null }))
    .sort((a, b) => String(a.product?.name || '').localeCompare(String(b.product?.name || '')))
))

const summaryTotals = computed(() => {
  return jobRequirementRows.value.reduce((totals, row) => {
    const qty = Math.max(0, Number(row.quantity_required || 0))
    const product = row.product
    if (!product || qty <= 0) return totals

    const weight = Number(product.weight_kg || 0)
    const height = Number(product.height_cm || 0)
    const width = Number(product.width_cm || 0)
    const depth = Number(product.depth_cm || 0)
    const replaceCost = Number(product.replace_cost || 0)
    const dailyRate = Number(product.daily_rate || 0)

    totals.weightKg += weight * qty
    totals.volumeM3 += ((height * width * depth) / 1000000) * qty
    totals.replacementCost += replaceCost * qty
    totals.projectedPrice += dailyRate * qty
    return totals
  }, {
    weightKg: 0,
    volumeM3: 0,
    replacementCost: 0,
    projectedPrice: 0,
  })
})

const customerDisplayName = computed(() => {
  const selected = customersStore.customers.find(customer => customer.id === (form.value.customer_id || currentJob.value?.customer_id))
  return selected?.name || form.value.customer_name || currentJob.value?.customer_name || t('jobs.unassigned')
})

const venueDisplayName = computed(() => {
  const selected = venuesStore.venues.find(venue => venue.id === (form.value.venue_id || currentJob.value?.venue_id))
  return selected?.name || form.value.venue_name || currentJob.value?.venue_name || t('jobs.unassigned')
})

const projectDisplayName = computed(() => (
  projectsStore.projects.find(project => project.id === (form.value.project_id || currentJob.value?.project_id))?.name || t('jobs.unassigned')
))

const formattedDateRange = computed(() => `${formatDate(form.value.start_date || currentJob.value?.start_date)} ${t('jobs.to')} ${formatDate(form.value.end_date || currentJob.value?.end_date)}`)

function syncFromJob(job) {
  if (!job) {
    form.value = emptyForm()
    requirementRows.value = []
    return
  }

  form.value = {
    job_code: job.job_code ?? '',
    status: job.status ?? 'draft',
    description: job.description ?? '',
    customer_id: job.customer_id ?? null,
    customer_name: job.customer_name ?? '',
    venue_id: job.venue_id ?? null,
    venue_name: job.venue_name ?? '',
    project_id: job.project_id ?? null,
    location_in_venue: job.location_in_venue ?? '',
    start_date: normalizeDate(job.start_date),
    end_date: normalizeDate(job.end_date),
    sales_price: job.sales_price == null ? null : Number(job.sales_price),
    invoice_paid: Boolean(job.invoice_paid),
    invoice_paid_at: normalizeDate(job.invoice_paid_at),
    notes: job.notes ?? '',
  }

  requirementRows.value = jobsStore.requirements
    .filter(req => req.job_id === job.id)
    .map(req => ({
      product_id: req.product_id,
      quantity_required: req.quantity_required,
      quantity_picked: req.quantity_picked,
      notes: req.notes || null,
    }))
}

function setRequirementQty(productId, value) {
  const qty = Math.max(0, Number(value || 0))
  const row = requirementRows.value.find(item => item.product_id === productId)
  if (row) {
    row.quantity_required = qty
    if (qty === 0) removeRequirementRow(productId)
    return
  }
  if (qty > 0) {
    requirementRows.value.push({ product_id: productId, quantity_required: qty, quantity_picked: 0, notes: null })
  }
}

function removeRequirementRow(productId) {
  requirementRows.value = requirementRows.value.filter(item => item.product_id !== productId)
}

async function loadData() {
  pageLoading.value = true
  try {
    await Promise.all([
      jobsStore.fetchAll(),
      inventoryStore.fetchAll(),
      customersStore.fetchAll(),
      venuesStore.fetchAll(),
      projectsStore.fetchAll(),
      settingsStore.fetchCompanyProfile(),
    ])
    syncFromJob(currentJob.value)
  } finally {
    pageLoading.value = false
  }
}

async function saveChanges() {
  if (!currentJob.value || !authStore.canEdit) return

  const valid = await formRef.value?.validate()
  if (!valid) return

  saving.value = true
  try {
    const selectedCustomer = customersStore.customers.find(customer => customer.id === form.value.customer_id)
    const selectedVenue = venuesStore.venues.find(venue => venue.id === form.value.venue_id)

    const payload = {
      ...currentJob.value,
      ...form.value,
      customer_name: selectedCustomer?.name || form.value.customer_name || currentJob.value.customer_name || '',
      venue_name: selectedVenue?.name || form.value.venue_name || currentJob.value.venue_name || '',
      start_date: normalizeDate(form.value.start_date),
      end_date: normalizeDate(form.value.end_date),
      sales_price: form.value.sales_price == null || form.value.sales_price === '' ? null : Number(form.value.sales_price),
      invoice_paid: Boolean(form.value.invoice_paid),
      invoice_paid_at: form.value.invoice_paid ? normalizeDate(form.value.invoice_paid_at) : null,
    }

    const savedJob = await jobsStore.updateJob(currentJob.value.id, payload)
    await jobsStore.bulkUpsertRequirements(savedJob.id, requirementRows.value.map(item => ({
      product_id: item.product_id,
      quantity_required: Number(item.quantity_required || 0),
      quantity_picked: Number(item.quantity_picked || 0),
      notes: item.notes || null,
    })))

    syncFromJob(savedJob)
    $q.notify({ type: 'positive', message: t('jobs.jobUpdated') })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('common.errorOccurred') })
  } finally {
    saving.value = false
  }
}

function goBack() {
  router.push('/jobs')
}

onMounted(async () => {
  await loadData()
})

watch(currentJob, (job) => {
  syncFromJob(job)
})

watch(() => route.params.jobId, async (next, prev) => {
  if (next === prev) return
  await loadData()
})
</script>
