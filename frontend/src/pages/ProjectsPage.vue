<template>
  <q-page class="q-pa-md ec-page">
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">{{ t('projects.title') }}</div>
      <q-btn v-if="authStore.canEdit" color="primary" icon="add" :label="t('projects.newProject')" unelevated @click="openCreate" />
    </div>

    <q-table
      :rows="filteredProjects"
      :columns="columns"
      row-key="id"
      :grid="compactGrid"
      :hide-header="compactGrid"
      flat
      bordered
      :loading="pageLoading"
      :pagination="{ rowsPerPage: 50, sortBy: 'created_at', descending: true }"
      :rows-per-page-options="[25, 50, 100, 0]"
      class="ec-card"
    >
      <template #top-right>
        <q-input v-model="search" dense outlined clearable :placeholder="t('projects.searchProjects')">
          <template #prepend>
            <q-icon name="search" />
          </template>
        </q-input>
      </template>

      <template #body-cell-status="props">
        <q-td :props="props">
          <q-badge :color="statusColor(props.value)" :label="statusLabel(props.value)" />
        </q-td>
      </template>

      <template #body-cell-customer_name="props">
        <q-td :props="props">
          {{ props.value || '-' }}
        </q-td>
      </template>

      <template #body-cell-venue_name="props">
        <q-td :props="props">
          {{ props.value || '-' }}
        </q-td>
      </template>

      <template #body-cell-job_count="props">
        <q-td :props="props">
          <q-btn
            v-if="props.value > 0"
            flat
            dense
            no-caps
            color="primary"
            :label="String(props.value)"
            @click="navigateToJobs(props.row)"
          />
          <span v-else>0</span>
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

      <template #body-cell-actions="props">
        <q-td v-if="authStore.canEdit" :props="props" auto-width>
          <q-btn flat round dense icon="add" color="positive" class="q-mr-xs" @click="openNewJob(props.row)" />
          <q-btn
            v-if="productionplannerEnabled"
            flat
            round
            dense
            icon="sync"
            color="info"
            class="q-mr-xs"
            @click="syncToProductionPlanner(props.row)"
            :label="t('jobs.syncToPP')"
            :disable="projectsStore.loading"
          />
          <q-btn
            v-if="productionplannerEnabled && props.row.productionplanner_project_id"
            flat
            round
            dense
            icon="open_in_new"
            color="primary"
            class="q-mr-xs"
            @click="openProductionPlanner(props.row.productionplanner_project_id)"
            :label="t('jobs.openInPP')"
          />
          <q-btn flat round dense icon="edit" color="primary" class="q-mr-xs" @click="openEdit(props.row)" />
          <q-btn flat round dense icon="delete" color="negative" @click="confirmDelete(props.row)" />
        </q-td>
      </template>

      <template #item="props">
        <div class="q-pa-xs col-12">
          <q-card flat bordered>
            <q-card-section class="q-pb-sm">
              <div class="text-subtitle2">{{ props.row.name }}</div>
              <div class="text-caption text-grey-7">
                <q-badge :color="statusColor(props.row.status)" :label="statusLabel(props.row.status)" class="q-mr-sm" />
                {{ props.row.customer_name || '-' }} · {{ props.row.venue_name || '-' }}
              </div>
            </q-card-section>
            <q-card-section class="q-pt-none q-pb-sm">
              <div class="text-caption" v-if="props.row.description">{{ t('projects.description') }}: {{ props.row.description }}</div>
              <div class="text-caption" v-if="props.row.start_date">{{ t('projects.startDate') }}: {{ formatDate(props.row.start_date) }}</div>
              <div class="text-caption" v-if="props.row.end_date">{{ t('projects.endDate') }}: {{ formatDate(props.row.end_date) }}</div>
              <div class="text-caption">{{ t('projects.created') }}: {{ props.row.created_at ? formatDate(props.row.created_at) : '-' }}</div>
            </q-card-section>
            <q-card-actions v-if="authStore.canEdit" align="right">
              <q-btn flat dense icon="add" color="positive" class="q-mr-xs" @click="openNewJob(props.row)" />
              <q-btn
                v-if="productionplannerEnabled"
                flat
                dense
                round
                icon="sync"
                color="info"
                :aria-label="t('jobs.syncToPP')"
                :disable="projectsStore.loading"
                @click="syncToProductionPlanner(props.row)"
              >
                <q-tooltip>{{ t('jobs.syncToPP') }}</q-tooltip>
              </q-btn>
              <q-btn
                v-if="productionplannerEnabled && props.row.productionplanner_project_id"
                flat
                dense
                round
                icon="open_in_new"
                color="primary"
                :aria-label="t('jobs.openInProductionPlanner')"
                @click="openProductionPlanner(props.row.productionplanner_project_id)"
              >
                <q-tooltip>{{ t('jobs.openInProductionPlanner') }}</q-tooltip>
              </q-btn>
              <q-btn flat dense icon="edit" color="primary" @click="openEdit(props.row)" />
              <q-btn flat dense icon="delete" color="negative" @click="confirmDelete(props.row)" />
            </q-card-actions>
          </q-card>
        </div>
      </template>
    </q-table>

    <ProjectDialog v-model="dialogOpen" :project="editing" @saved="onProjectSaved" />
    <ProjectDeleteDialog v-model="deleteDialogOpen" :project="deleteTarget" @deleted="onProjectDeleted" />
    <JobDialog
      v-model="newJobDialogOpen"
      @saved="onNewJobSaved"
      :customers="customersStore.customers"
      :venues="venuesStore.venues"
      :products="inventoryStore.products"
      :initial-values="newJobInitialValues"
    />
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import { useAuthStore } from '../stores/auth'
import { useCustomersStore } from '../stores/customers'
import { useProjectsStore } from '../stores/projects'
import { useVenuesStore } from '../stores/venues'
import { useInventoryStore } from '../stores/inventory'
import { useJobsStore } from '../stores/jobs'
import { useSettingsStore } from '../stores/settings'
import ProjectDialog from '../components/ProjectDialog.vue'
import ProjectDeleteDialog from '../components/ProjectDeleteDialog.vue'
import JobDialog from '../components/JobDialog.vue'

const $q = useQuasar()
const router = useRouter()
const { t } = useI18n()
const authStore = useAuthStore()
const customersStore = useCustomersStore()
const projectsStore = useProjectsStore()
const venuesStore = useVenuesStore()
const inventoryStore = useInventoryStore()
const jobsStore = useJobsStore()
const settingsStore = useSettingsStore()

const productionplannerEnabled = computed(() => settingsStore.integrations?.productionplanner?.enabled === true)

const search = ref('')
const pageLoading = ref(false)
const dialogOpen = ref(false)
const editing = ref(null)
const deleteDialogOpen = ref(false)
const deleteTarget = ref(null)
const newJobDialogOpen = ref(false)
const newJobInitialValues = ref(null)

const compactGrid = computed(() => $q.screen.width < 600)

const columns = computed(() => [
  { name: 'name', label: t('projects.name'), field: 'name', sortable: true, align: 'left' },
  { name: 'status', label: t('projects.status'), field: 'status', sortable: true, align: 'left' },
  { name: 'description', label: t('projects.description'), field: 'description', sortable: true, align: 'left' },
  { name: 'customer_name', label: t('projects.customer'), field: 'customer_name', sortable: true, align: 'left' },
  { name: 'venue_name', label: t('projects.venue'), field: 'venue_name', sortable: true, align: 'left' },
  { name: 'start_date', label: t('projects.startDate'), field: 'start_date', sortable: true, align: 'left', format: formatDate },
  { name: 'end_date', label: t('projects.endDate'), field: 'end_date', sortable: true, align: 'left', format: formatDate },
  { name: 'job_count', label: t('projects.jobs'), field: 'job_count', sortable: true, align: 'left' },
  { name: 'productionplanner', label: t('jobs.productionPlanner'), field: 'productionplanner_project_id', sortable: false, align: 'left' },
  { name: 'created_at', label: t('projects.created'), field: 'created_at', sortable: true, align: 'left', format: formatDate },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
])

const filteredProjects = computed(() => {
  const term = search.value.trim().toLowerCase()
  if (!term) return projectsWithCounts.value
  return projectsWithCounts.value.filter(p => {
    return [p.name, p.description, p.customer_name, p.venue_name, p.status]
      .filter(Boolean)
      .some(v => String(v).toLowerCase().includes(term))
  })
})

const projectsWithCounts = computed(() => {
  return projectsStore.projects.map(p => ({
    ...p,
    customer_name: customerNameForId(p.customer_id),
    venue_name: venueNameForId(p.venue_id),
    job_count: projectJobs(p.id).length,
  }))
})

function projectJobs(projectId) {
  return jobsStore.jobs.filter(j => j.project_id === projectId)
}

function customerNameForId(id) {
  return customersStore.customers.find(c => c.id === id)?.name || ''
}

function venueNameForId(id) {
  return venuesStore.venues.find(v => v.id === id)?.name || ''
}

function statusColor(status) {
  const map = { active: 'info', completed: 'positive', cancelled: 'negative' }
  return map[status] || 'grey'
}

function statusLabel(status) {
  const map = { active: t('projects.statusActive'), completed: t('projects.statusCompleted'), cancelled: t('projects.statusCancelled') }
  return map[status] || status
}

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleDateString()
}

function openCreate() {
  editing.value = null
  dialogOpen.value = true
}

function openEdit(project) {
  editing.value = project
  dialogOpen.value = true
}

function confirmDelete(project) {
  deleteTarget.value = project
  deleteDialogOpen.value = true
}

function onProjectSaved() {
  dialogOpen.value = false
  editing.value = null
}

function onProjectDeleted() {
  deleteDialogOpen.value = false
  deleteTarget.value = null
}

function openNewJob(project) {
  newJobInitialValues.value = {
    customer_id: project.customer_id,
    venue_id: project.venue_id,
    project_id: project.id,
  }
  newJobDialogOpen.value = true
}

function onNewJobSaved() {
  newJobDialogOpen.value = false
  newJobInitialValues.value = null
}

function navigateToJobs(project) {
  router.push({ path: '/jobs', query: { projectId: project.id } })
}

async function syncToProductionPlanner(project) {
  try {
    const result = await projectsStore.syncProjectToProductionPlanner(project.id)
    if (result?.success !== true) {
      console.error('ProductionPlanner sync failed:', result?.message || 'Unknown error')
      $q.notify({ type: 'negative', message: result?.message || t('jobs.syncPPFailed') })
      return
    }
    await projectsStore.fetchAll()
    $q.notify({ type: 'positive', message: t('jobs.syncPPSuccess') })
  } catch (error) {
    console.error('Failed to sync to ProductionPlanner:', error)
    $q.notify({ type: 'negative', message: t('jobs.syncPPFailed') })
  }
}

function openProductionPlanner(productionPlannerProjectId) {
  if (productionPlannerProjectId) {
    window.open(projectsStore.getProductionPlannerUrl(productionPlannerProjectId), '_blank', 'noopener,noreferrer')
  }
}

async function loadData() {
  pageLoading.value = true
  try {
    await Promise.all([
      projectsStore.fetchAll(),
      customersStore.fetchAll(),
      venuesStore.fetchAll(),
      inventoryStore.fetchAll(),
      jobsStore.fetchAll(),
      settingsStore.fetchIntegrations(),
    ])
  } finally {
    pageLoading.value = false
  }
}

onMounted(loadData)
</script>
