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

    <div class="row items-center justify-between q-mb-md q-gutter-sm">
      <div class="row q-gutter-xs">
        <q-chip
          v-for="status in statusFilters"
          :key="status.value"
          clickable
          dense
          :color="status.color"
          :text-color="activeFilter === status.value ? 'white' : status.color"
          :outline="activeFilter !== status.value"
          @click="activeFilter = activeFilter === status.value ? null : status.value"
        >
          {{ status.label }}
        </q-chip>
      </div>

      <q-input v-model="search" dense outlined clearable :placeholder="t('jobs.searchJobs')">
        <template #prepend>
          <q-icon name="search" />
        </template>
      </q-input>
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
                <q-btn flat dense icon="edit" color="primary" @click="openEdit(props.row)" />
                <q-btn flat dense icon="delete" color="negative" @click="confirmDelete(props.row)" />
              </template>
            </q-card-actions>
          </q-card>
        </div>
      </template>
    </q-table>

    <JobDialog
      v-model="dialogOpen"
      :job="editing"
      :customers="customersStore.customers"
      :venues="venuesStore.venues"
      :products="inventoryStore.products"
      @saved="onJobSaved"
    />
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
import JobDialog from '../components/JobDialog.vue'
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

const pageLoading = ref(false)
const search = ref('')
const activeFilter = ref(null)
const showCachedOfflineBanner = computed(() => (
  jobsStore.fetchSource === 'snapshot' || inventoryStore.fetchSource === 'snapshot'
))

const dialogOpen = ref(false)
const editing = ref(null)
const deleteDialogOpen = ref(false)
const deleteTarget = ref(null)

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
    if (activeFilter.value && job.status !== activeFilter.value) return false
    if (!term) return true
    return [job.job_code, job.description, job.customer_name, job.venue_name, job.project_name, job.status]
      .filter(Boolean)
      .some(value => String(value).toLowerCase().includes(term))
  })
})

async function loadData() {
  pageLoading.value = true
  try {
    await Promise.all([
      jobsStore.fetchAll(),
      customersStore.fetchAll(),
      venuesStore.fetchAll(),
      inventoryStore.fetchAll(),
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
    activeFilter.value = status
  }

  const focusJobId = Number(route.query.focusJobId || 0)
  if (focusJobId > 0) {
    const target = jobsStore.jobs.find(item => item.id === focusJobId)
    if (target && authStore.canEdit) {
      openEdit(target)
    } else if (target) {
      search.value = String(target.job_code || '').trim()
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
  editing.value = null
  dialogOpen.value = true
}

function openEdit(job) {
  editing.value = job
  dialogOpen.value = true
}

function confirmDelete(job) {
  deleteTarget.value = job
  deleteDialogOpen.value = true
}

function onJobSaved() {
  dialogOpen.value = false
  editing.value = null
}

function onJobDeleted() {
  deleteDialogOpen.value = false
  deleteTarget.value = null
}
</script>
