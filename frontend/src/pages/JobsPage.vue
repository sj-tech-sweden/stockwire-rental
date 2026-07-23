<template>
  <q-page class="q-pa-md ec-page">
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">{{ t('jobs.title') }}</div>
      <q-btn v-if="authStore.canEdit" color="primary" icon="add" :label="t('jobs.newJob')" unelevated @click="openCreate" />
    </div>

    <q-banner
      v-if="showCachedOfflineBanner"
      class="bg-warning text-dark rounded-borders q-mb-md"
      dense
    >
      {{ t('jobs.cachedOfflineBanner') }}
    </q-banner>

    <div class="row q-col-gutter-sm q-mb-md items-end">
      <div class="col-12 col-sm-6 col-md-3">
        <q-select
          v-model="selectedStatuses"
          :options="statusOptions"
          emit-value
          map-options
          outlined
          dense
          use-chips
          multiple
          :label="t('jobs.filterByStatus')"
          clearable
        />
      </div>
      <div class="col-12 col-sm-6 col-md-3">
        <q-select
          v-model="filterCustomerId"
          :options="customerOptions"
          emit-value
          map-options
          outlined
          dense
          clearable
          :label="t('jobs.filterByCustomer')"
        />
      </div>
      <div class="col-12 col-sm-6 col-md-3">
        <q-select
          v-model="filterVenueId"
          :options="venueOptions"
          emit-value
          map-options
          outlined
          dense
          clearable
          :label="t('jobs.filterByVenue')"
        />
      </div>
      <div class="col-12 col-sm-6 col-md-3">
        <q-select
          v-model="filterProjectIdLocal"
          :options="projectOptions"
          emit-value
          map-options
          outlined
          dense
          clearable
          :label="t('jobs.filterByProject')"
        />
      </div>
      <div class="col-6 col-sm-3 col-md-2">
        <q-input v-model="filterStartDateFrom" type="date" outlined dense clearable :label="t('jobs.startDateFrom')" />
      </div>
      <div class="col-6 col-sm-3 col-md-2">
        <q-input v-model="filterStartDateTo" type="date" outlined dense clearable :label="t('jobs.startDateTo')" />
      </div>
      <div class="col-12 col-sm-6 col-md-3">
        <q-input v-model="search" dense outlined clearable :placeholder="t('jobs.searchJobs')">
          <template #prepend>
            <q-icon name="search" />
          </template>
        </q-input>
      </div>
      <div v-if="hasActiveFilters" class="col-auto">
        <q-btn flat dense color="negative" icon="filter_alt_off" :label="t('jobs.clearFilters')" @click="clearAllFilters" />
      </div>
    </div>

    <q-table
      :rows="visibleJobs"
      :columns="columns"
      row-key="id"
      :grid="compactGrid"
      :hide-header="compactGrid"
      flat
      bordered
      :loading="pageLoading || jobsStore.loading"
      :pagination="{ rowsPerPage: 50, sortBy: 'start_date', descending: false }"
      :rows-per-page-options="[25, 50, 100, 0]"
      class="ec-card"
      @row-dblclick="(evt, row) => router.push(`/jobs/${row.id}`)"
    >
      <template #body-cell-status="props">
        <q-td :props="props">
          <q-badge :color="statusColor(props.value)" :label="statusLabel(props.value)" />
        </q-td>
      </template>

      <template #body-cell-productionplanner="props">
        <q-td :props="props">
          <div class="row items-center q-gutter-xs">
            <q-btn
              v-if="productionplannerEnabled && props.row.productionplanner_project_id"
              flat
              dense
              round
              icon="open_in_new"
              color="positive"
              :aria-label="t('jobs.openInProductionPlanner')"
              @click="openProductionPlanner(props.row.productionplanner_project_id)"
            >
              <q-tooltip>{{ t('jobs.openInProductionPlanner') }}</q-tooltip>
            </q-btn>
            <q-icon v-else name="link_off" color="grey" />
          </div>
        </q-td>
      </template>

      <template #body-cell-sales_price="props">
        <q-td :props="props">
          {{ formatMoney(props.value) }}
        </q-td>
      </template>

      <template #body-cell-venue_name="props">
        <q-td :props="props">
          <div class="row items-center q-gutter-xs no-wrap">
            <span>{{ props.value || t('jobs.unassigned') }}</span>
            <q-btn
              v-if="jobVenueMapLink(props.row)"
              flat
              dense
              round
              icon="open_in_new"
              color="secondary"
              size="sm"
              :href="jobVenueMapLink(props.row)"
              target="_blank"
              rel="noopener noreferrer"
              :aria-label="t('jobs.openVenueMap')"
            />
          </div>
        </q-td>
      </template>

      <template #body-cell-invoice_paid="props">
        <q-td :props="props">
          <q-badge :color="props.value ? 'positive' : 'warning'" :label="props.value ? t('jobs.paid') : t('jobs.unpaid')" />
        </q-td>
      </template>

      <template #body-cell-actions="props">
        <q-td :props="props" auto-width>
          <q-btn flat round dense icon="visibility" color="grey-7" class="q-mr-xs" :to="`/jobs/${props.row.id}`" />
          <template v-if="authStore.canEdit">
            <q-btn flat round dense icon="edit" color="primary" class="q-mr-xs" @click="openEdit(props.row)" />
            <q-btn v-if="productionplannerEnabled" flat round dense icon="sync" color="info" class="q-mr-xs" @click="syncToProductionPlanner(props.row)" :label="t('jobs.syncToPP')" :disable="jobsStore.loading" />
            <q-btn v-if="productionplannerEnabled && props.row.productionplanner_project_id" flat round dense icon="open_in_new" color="primary" class="q-mr-xs" @click="openProductionPlanner(props.row.productionplanner_project_id)" :label="t('jobs.openInPP')" />
            <q-btn flat round dense icon="delete" color="negative" @click="confirmDelete(props.row)" />
          </template>
        </q-td>
      </template>

      <template #item="props">
        <div class="q-pa-xs col-12">
          <q-card flat bordered>
            <q-card-section class="q-pb-sm">
              <div class="row items-center justify-between">
                <div class="text-subtitle2">{{ props.row.job_code }}</div>
                <q-badge :color="statusColor(props.row.status)" :label="statusLabel(props.row.status)" />
              </div>
              <div class="text-caption text-grey-7">{{ props.row.description || t('jobs.noDescription') }}</div>
            </q-card-section>
            <q-card-section class="q-pt-none q-pb-sm">
              <div class="text-caption">{{ t('jobs.customerLabel') }}: {{ customerNameForId(props.row.customer_id) || t('jobs.unassigned') }}</div>
              <div class="text-caption">
                {{ t('jobs.venueLabel') }}: {{ venueNameForId(props.row.venue_id) || t('jobs.unassigned') }}
                <a
                  v-if="jobVenueMapLink(props.row)"
                  :href="jobVenueMapLink(props.row)"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-primary q-ml-xs"
                >
                  {{ t('jobs.openVenueMap') }}
                </a>
              </div>
              <div class="text-caption">{{ t('jobs.salesLabel') }}: {{ formatMoney(props.row.sales_price) }}</div>
              <div class="text-caption">{{ t('jobs.invoiceLabel') }}: {{ props.row.invoice_paid ? t('jobs.paid') : t('jobs.unpaid') }}</div>
              <div class="text-caption">{{ props.row.start_date || '-' }} {{ t('jobs.to') }} {{ props.row.end_date || '-' }}</div>
            </q-card-section>
            <q-card-actions align="right">
              <q-btn flat dense icon="visibility" color="grey-7" :to="`/jobs/${props.row.id}`" />
              <template v-if="authStore.canEdit">
              <q-btn v-if="productionplannerEnabled" flat dense round icon="sync" color="info" :aria-label="t('jobs.syncToPP')" :disable="jobsStore.loading" @click="syncToProductionPlanner(props.row)">
                <q-tooltip>{{ t('jobs.syncToPP') }}</q-tooltip>
              </q-btn>
              <q-btn v-if="productionplannerEnabled && props.row.productionplanner_project_id" flat dense round icon="open_in_new" color="primary" :aria-label="t('jobs.openInProductionPlanner')" @click="openProductionPlanner(props.row.productionplanner_project_id)">
                <q-tooltip>{{ t('jobs.openInProductionPlanner') }}</q-tooltip>
              </q-btn>
              <q-btn flat dense icon="edit" color="primary" @click="openEdit(props.row)" />
              <q-btn flat dense icon="delete" color="negative" @click="confirmDelete(props.row)" />
              </template>
            </q-card-actions>
          </q-card>
        </div>
      </template>
    </q-table>

    <JobDeleteDialog
      v-model="deleteDialogOpen"
      :job="deleteTarget"
      @deleted="onJobDeleted"
    />
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useQuasar } from 'quasar'

import { JOB_STATUSES, useJobsStore } from '../stores/jobs'
import { useCustomersStore } from '../stores/customers'
import { useVenuesStore } from '../stores/venues'
import { useInventoryStore } from '../stores/inventory'
import { useAuthStore } from '../stores/auth'
import { useSettingsStore } from '../stores/settings'
import { useProjectsStore } from '../stores/projects'
import { useCompactGrid } from '../composables/useCompactGrid'
import { normalizeCurrencyCode } from '../constants/currencies'
import { googleMapsSearchUrl, locationQueryFromParts } from '../utils/maps'
import JobDeleteDialog from '../components/JobDeleteDialog.vue'

const compactGrid = useCompactGrid(1024)
const jobsStore = useJobsStore()
const customersStore = useCustomersStore()
const venuesStore = useVenuesStore()
const inventoryStore = useInventoryStore()
const authStore = useAuthStore()
const settingsStore = useSettingsStore()
const projectsStore = useProjectsStore()
const route = useRoute()
const router = useRouter()
const { t, locale } = useI18n()
const $q = useQuasar()

const pageLoading = ref(false)
const search = ref('')
const selectedStatuses = ref([])
const filterCustomerId = ref(null)
const filterVenueId = ref(null)
const filterProjectIdLocal = ref(null)
const filterStartDateFrom = ref('')
const filterStartDateTo = ref('')
const showCachedOfflineBanner = computed(() => (
  jobsStore.fetchSource === 'snapshot' || inventoryStore.fetchSource === 'snapshot'
))

const deleteDialogOpen = ref(false)
const deleteTarget = ref(null)

const productionplannerEnabled = computed(() => settingsStore.integrations?.productionplanner?.enabled === true)

const statusFilters = computed(() => JOB_STATUSES.map(status => ({
  ...status,
  label: statusLabel(status.value),
})))

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

const statusOptions = computed(() =>
  statusFilters.value.map(s => ({ label: s.label, value: s.value }))
)

const customerOptions = computed(() =>
  customersStore.customers
    .map(c => ({ label: c.name, value: c.id }))
    .sort((a, b) => a.label.localeCompare(b.label))
)

const venueOptions = computed(() =>
  venuesStore.venues
    .map(v => ({ label: v.name, value: v.id }))
    .sort((a, b) => a.label.localeCompare(b.label))
)

const projectOptions = computed(() =>
  projectsStore.projects
    .map(p => ({ label: p.name, value: p.id }))
    .sort((a, b) => a.label.localeCompare(b.label))
)

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

const columns = computed(() => [
  { name: 'job_code', label: t('jobs.jobCode'), field: 'job_code', sortable: true, align: 'left' },
  { name: 'description', label: t('jobs.description'), field: 'description', sortable: true, align: 'left' },
  { name: 'customer_name', label: t('jobs.customer'), field: 'customer_name', sortable: true, align: 'left' },
  { name: 'venue_name', label: t('jobs.venue'), field: 'venue_name', sortable: true, align: 'left' },
  { name: 'project_name', label: t('jobs.project'), field: 'project_name', sortable: true, align: 'left' },
  { name: 'status', label: t('jobs.status'), field: 'status', sortable: true, align: 'left' },
  { name: 'productionplanner', label: t('jobs.productionPlanner'), field: 'productionplanner_project_id', sortable: false, align: 'left' },
  { name: 'sales_price', label: t('jobs.salesLabel'), field: 'sales_price', sortable: true, align: 'right' },
  { name: 'invoice_paid', label: t('jobs.invoiceLabel'), field: 'invoice_paid', sortable: true, align: 'left' },
  { name: 'start_date', label: t('jobs.start'), field: 'start_date', sortable: true, align: 'left', format: formatDate },
  { name: 'end_date', label: t('jobs.end'), field: 'end_date', sortable: true, align: 'left', format: formatDate },
  { name: 'created_at', label: t('jobs.created'), field: 'created_at', sortable: true, align: 'left', format: formatDate },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
])

const jobsWithProject = computed(() =>
  jobsStore.jobs.map(job => ({
    ...job,
    project_name: projectsStore.projects.find(p => p.id === job.project_id)?.name || '',
  }))
)

const filterProjectId = computed(() => {
  const raw = route.query.projectId
  return raw ? Number(raw) : null
})

const visibleJobs = computed(() => {
  const term = search.value.trim().toLowerCase()
  return jobsWithProject.value.filter(job => {
    if (filterProjectId.value && job.project_id !== filterProjectId.value) return false
    if (selectedStatuses.value?.length && !selectedStatuses.value.includes(job.status)) return false
    if (filterCustomerId.value && job.customer_id !== filterCustomerId.value) return false
    if (filterVenueId.value && job.venue_id !== filterVenueId.value) return false
    if (filterProjectIdLocal.value && job.project_id !== filterProjectIdLocal.value) return false
    if (filterStartDateFrom.value && job.start_date < filterStartDateFrom.value) return false
    if (filterStartDateTo.value && job.start_date > filterStartDateTo.value) return false
    if (!term) return true
    return [job.job_code, job.description, job.customer_name, job.venue_name, job.project_name, job.status]
      .filter(Boolean)
      .some(value => String(value).toLowerCase().includes(term))
  })
})

const hasActiveFilters = computed(() =>
  (selectedStatuses.value?.length || 0) > 0 ||
  filterCustomerId.value !== null ||
  filterVenueId.value !== null ||
  filterProjectIdLocal.value !== null ||
  filterStartDateFrom.value !== '' ||
  filterStartDateTo.value !== '' ||
  search.value.trim() !== ''
)

function clearAllFilters() {
  selectedStatuses.value = []
  filterCustomerId.value = null
  filterVenueId.value = null
  filterProjectIdLocal.value = null
  filterStartDateFrom.value = ''
  filterStartDateTo.value = ''
  search.value = ''
}

watch(selectedStatuses, (val) => {
  if (val === null) selectedStatuses.value = []
})

async function loadData() {
  pageLoading.value = true
  try {
    await Promise.all([
      jobsStore.fetchAll(),
      customersStore.fetchAll(),
      venuesStore.fetchAll(),
      inventoryStore.fetchAll(),
      settingsStore.fetchIntegrations(),
      settingsStore.fetchCompanyProfile(),
      projectsStore.fetchAll(),
    ])
  } finally {
    pageLoading.value = false
  }
}

async function applyRouteContext() {
  const status = String(route.query.status || '').trim().toLowerCase()
  if (status && JOB_STATUSES.some(item => item.value === status)) {
    selectedStatuses.value = [status]
  }

  const focusJobId = Number(route.query.focusJobId || 0)
  if (focusJobId > 0) {
    const target = jobsStore.jobs.find(item => item.id === focusJobId)
    if (target) {
      await router.replace(`/jobs/${target.id}`)
      return
    }
  }

  if (route.query.focusJobId || route.query.status) {
    const nextQuery = { ...route.query }
    delete nextQuery.focusJobId
    delete nextQuery.status
    await router.replace({ path: '/jobs', query: nextQuery })
  }
}

onMounted(async () => {
  await loadData()
  await applyRouteContext()
})

watch(
  () => [route.query.focusJobId, route.query.status],
  async ([focusJobId, status]) => {
    if (!focusJobId && !status) return
    await applyRouteContext()
  }
)

function customerNameForId(id) {
  return customersStore.customers.find(customer => customer.id === id)?.name ?? ''
}

function venueNameForId(id) {
  return venuesStore.venues.find(venue => venue.id === id)?.name ?? ''
}

function jobVenueMapLink(job) {
  if (!job) return ''
  const venue = venuesStore.venues.find(item => item.id === job.venue_id)
  return googleMapsSearchUrl(locationQueryFromParts(venue || { name: job.venue_name }))
}

function openCreate() {
  router.push('/jobs/new')
}

function openEdit(job) {
  router.push(`/jobs/${job.id}`)
}

function confirmDelete(job) {
  deleteTarget.value = job
  deleteDialogOpen.value = true
}

async function syncToProductionPlanner(job) {
  try {
    const result = await jobsStore.syncJobToProductionPlanner(job.id)
    if (result?.success !== true) {
      console.error('ProductionPlanner sync failed:', result?.message || 'Unknown error')
      $q.notify({ type: 'negative', message: result?.message || t('jobs.syncPPFailed') })
      return
    }
    await jobsStore.fetchAll()
    $q.notify({ type: 'positive', message: t('jobs.syncPPSuccess') })
  } catch (error) {
    console.error('Failed to sync to ProductionPlanner:', error)
    $q.notify({ type: 'negative', message: t('jobs.syncPPFailed') })
  }
}

function openProductionPlanner(productionPlannerProjectId) {
  if (productionPlannerProjectId) {
    window.open(jobsStore.getProductionPlannerUrl(productionPlannerProjectId), '_blank', 'noopener,noreferrer')
  }
}

function onJobDeleted() {
  deleteDialogOpen.value = false
  deleteTarget.value = null
}
</script>
