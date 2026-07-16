<template>
  <q-page class="q-pa-md ec-page">
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">{{ t('maintenance.title') }}</div>
      <q-btn color="primary" icon="refresh" :label="t('maintenance.refresh')" unelevated @click="refresh" :loading="loading" />
    </div>

    <q-tabs v-model="tab" inline-label align="left" class="q-mb-md">
      <q-tab name="defects" icon="report_problem" :label="t('maintenance.tabs.defects')">
        <q-badge v-if="defectReports.length" color="negative" floating>{{ defectReports.length }}</q-badge>
      </q-tab>
      <q-tab name="tasks" icon="build_circle" :label="t('maintenance.tabs.tasks')">
        <q-badge v-if="pendingTaskCount" color="warning" floating>{{ pendingTaskCount }}</q-badge>
      </q-tab>
      <q-tab name="schedules" icon="event_repeat" :label="t('maintenance.tabs.schedules')" />
    </q-tabs>

    <q-tab-panels v-model="tab" animated>
    <!-- ==================== DEFECTS TAB ==================== -->
    <q-tab-panel name="defects" class="q-pa-none">
      <div class="row items-center q-mb-sm">
        <q-input v-model="defectSearch" dense outlined clearable :placeholder="t('maintenance.searchDefects')" class="col">
          <template #prepend><q-icon name="search" /></template>
        </q-input>
        <q-btn class="q-ml-sm" color="negative" icon="report_problem" :label="t('maintenance.createDefect')" unelevated @click="defectDialogOpen = true" />
      </div>
      <div class="row q-col-gutter-sm q-mb-sm">
        <div class="col-12 col-md-3">
          <q-select v-model="defectStatusFilter" :options="defectStatusFilterOptions" :label="t('maintenance.filterStatus')" outlined dense emit-value map-options clearable />
        </div>
        <div class="col-12 col-md-3">
          <q-select v-model="defectSeverityFilter" :options="defectSeverityFilterOptions" :label="t('maintenance.filterSeverity')" outlined dense emit-value map-options clearable />
        </div>
        <div class="col-12 col-md-3">
          <q-input v-model="defectAssetFilter" dense outlined clearable :label="t('maintenance.filterAssetTag')" />
        </div>
        <div class="col-12 col-md-3">
          <q-input v-model="defectSearch" dense outlined clearable :placeholder="t('maintenance.searchDefects')">
            <template #prepend><q-icon name="search" /></template>
          </q-input>
        </div>
      </div>

      <div v-if="selectedDefects.length" class="row items-center q-gutter-sm q-mb-sm">
        <q-badge color="primary" :label="t('maintenance.selectedCount', { count: selectedDefects.length })" />
        <q-btn color="negative" icon="delete" :label="t('maintenance.bulkDelete')" unelevated @click="runBulkDeleteDefects" />
        <q-btn flat :label="t('maintenance.clear')" @click="selectedDefects = []" />
      </div>

      <q-table
        :rows="filteredDefects"
        :columns="defectColumns"
        row-key="id"
        selection="multiple"
        v-model:selected="selectedDefects"
        :grid="compactGrid"
        :hide-header="compactGrid"
        flat bordered class="ec-card"
        :loading="loading"
        :pagination="{ rowsPerPage: 25 }"
        :rows-per-page-options="[25, 50, 100]"
      >
        <template #body-cell-asset_tag="props">
          <q-td :props="props">
            <a class="link" @click="openDeviceInfo(props.row.device_id)">{{ props.value }}</a>
          </q-td>
        </template>
        <template #body-cell-product_name="props">
          <q-td :props="props">
            <a v-if="props.row.product_id" class="link" @click="openProductInfo(props.row)">{{ props.value }}</a>
            <span v-else>{{ props.value }}</span>
          </q-td>
        </template>
        <template #body-cell-status="props">
          <q-td :props="props">
            <q-select :model-value="props.row.status" :options="defectStatusOptions" dense outlined emit-value map-options size="sm" style="min-width: 120px" @update:model-value="(v) => updateDefectField(props.row, 'status', v)" />
          </q-td>
        </template>
        <template #body-cell-severity="props">
          <q-td :props="props">
            <q-select :model-value="props.row.severity" :options="defectSeverityOptions" dense outlined emit-value map-options size="sm" style="min-width: 100px" @update:model-value="(v) => updateDefectField(props.row, 'severity', v)" />
          </q-td>
        </template>
        <template #body-cell-title="props">
          <q-td :props="props">
            <q-input :model-value="props.row.title" dense outlined @update:model-value="(v) => updateDefectField(props.row, 'title', v)" />
          </q-td>
        </template>
        <template #body-cell-description="props">
          <q-td :props="props">
            <q-input :model-value="props.row.description" dense outlined type="textarea" autogrow @update:model-value="(v) => updateDefectField(props.row, 'description', v || null)" />
          </q-td>
        </template>
        <template #body-cell-actions="props">
          <q-td :props="props" class="q-gutter-xs">
            <q-btn dense flat icon="chat" color="primary" @click="toggleDefectComments(props.row)">
              <q-badge v-if="props.row.commentCount" color="primary" floating>{{ props.row.commentCount }}</q-badge>
            </q-btn>
            <q-btn dense flat icon="delete" color="negative" @click="deleteDefect(props.row)" />
          </q-td>
        </template>
        <template #top-row>
          <tr v-if="expandedDefectId">
            <td :colspan="defectColumns.length" class="q-pa-md bg-grey-1">
              <div class="text-subtitle2 q-mb-sm">{{ t('maintenance.comments') }}</div>
              <div v-if="!expandedDefectComments.length" class="text-caption text-grey-6 q-mb-sm">{{ t('maintenance.noComments') }}</div>
              <div v-for="comment in expandedDefectComments" :key="comment.id" class="q-mb-xs">
                <div class="comment-bubble">{{ comment.comment }}</div>
              </div>
              <div class="row items-center q-mt-sm">
                <q-input v-model="newDefectComment" dense outlined type="textarea" autogrow :placeholder="t('maintenance.addComment')" class="col-grow" />
                <q-btn dense flat icon="send" color="primary" :loading="savingComment" :disable="!newDefectComment?.trim()" @click="addDefectComment(expandedDefectId)" class="q-ml-xs" />
              </div>
            </td>
          </tr>
        </template>
        <template #item="props">
          <div class="q-pa-xs col-12">
            <q-card flat bordered>
              <q-card-section class="q-pb-sm">
                <div class="text-subtitle2">
                  <a class="link" @click="openDeviceInfo(props.row.device_id)">{{ props.row.asset_tag }}</a>
                </div>
                <div class="text-caption text-grey-7">
                  <a v-if="props.row.product_id" class="link" @click="openProductInfo(props.row)">{{ props.row.product_name }}</a>
                  <span v-else>{{ props.row.product_name }}</span>
                </div>
              </q-card-section>
              <q-card-section class="q-pt-none q-pb-sm">
                <div class="row q-col-gutter-xs">
                  <div class="col-6">
                    <q-select :model-value="props.row.status" :options="defectStatusOptions" dense outlined emit-value map-options size="sm" @update:model-value="(v) => updateDefectField(props.row, 'status', v)" />
                  </div>
                  <div class="col-6">
                    <q-select :model-value="props.row.severity" :options="defectSeverityOptions" dense outlined emit-value map-options size="sm" @update:model-value="(v) => updateDefectField(props.row, 'severity', v)" />
                  </div>
                  <div class="col-12 q-mt-xs">
                    <q-input :model-value="props.row.title" dense outlined :placeholder="t('maintenance.titlePlaceholder')" @update:model-value="(v) => updateDefectField(props.row, 'title', v)" />
                  </div>
                  <div class="col-12" v-if="props.row.description">
                    <div class="text-caption q-mt-xs">{{ props.row.description }}</div>
                  </div>
                  <div class="col-12 text-caption text-grey-6 q-mt-xs">{{ t('maintenance.created') }}: {{ props.row.created_at }}</div>
                  <div class="col-12" v-if="expandedDefectId === props.row.id">
                    <div class="text-subtitle2 q-mt-sm q-mb-sm">{{ t('maintenance.comments') }}</div>
                    <div v-if="!expandedDefectComments.length" class="text-caption text-grey-6 q-mb-sm">{{ t('maintenance.noComments') }}</div>
                    <div v-for="comment in expandedDefectComments" :key="comment.id" class="q-mb-xs">
                      <div class="comment-bubble">{{ comment.comment }}</div>
                    </div>
                    <div class="row items-center q-mt-sm">
                      <q-input v-model="newDefectComment" dense outlined type="textarea" autogrow :placeholder="t('maintenance.addComment')" class="col-grow" />
                      <q-btn dense flat icon="send" color="primary" :loading="savingComment" :disable="!newDefectComment?.trim()" @click="addDefectComment(expandedDefectId)" class="q-ml-xs" />
                    </div>
                  </div>
                </div>
              </q-card-section>
              <q-card-actions align="right">
                <q-btn dense flat icon="chat" color="primary" @click="toggleDefectComments(props.row)">
                  <q-badge v-if="props.row.commentCount" color="primary" floating>{{ props.row.commentCount }}</q-badge>
                </q-btn>
                <q-btn dense flat icon="delete" color="negative" @click="deleteDefect(props.row)" />
              </q-card-actions>
            </q-card>
          </div>
        </template>
      </q-table>
    </q-tab-panel>

    <!-- ==================== TASKS TAB ==================== -->
    <q-tab-panel name="tasks" class="q-pa-none">
      <div class="row items-center q-mb-sm">
        <q-input v-model="maintenanceSearch" dense outlined clearable :placeholder="t('maintenance.searchTasks')" class="col">
          <template #prepend><q-icon name="search" /></template>
        </q-input>
        <q-btn class="q-ml-sm" color="secondary" icon="build" :label="t('maintenance.createTask')" unelevated @click="openCreateMaintenance('task')" />
      </div>

      <div v-if="selectedMaintenance.length" class="row items-center q-gutter-sm q-mb-sm">
        <q-badge color="primary" :label="t('maintenance.selectedCount', { count: selectedMaintenance.length })" />
        <q-btn color="secondary" icon="edit" :label="t('maintenance.bulkEdit')" unelevated @click="bulkMaintenanceDialogOpen = true" />
        <q-btn color="negative" icon="delete" :label="t('maintenance.bulkDelete')" unelevated @click="runBulkDeleteMaintenance" />
        <q-btn flat :label="t('maintenance.clear')" @click="selectedMaintenance = []" />
      </div>

      <q-table
        :rows="filteredMaintenance"
        :columns="maintenanceColumns"
        row-key="id"
        selection="multiple"
        v-model:selected="selectedMaintenance"
        :grid="compactGrid"
        :hide-header="compactGrid"
        flat bordered class="ec-card"
        :loading="store.loading"
        :pagination="{ rowsPerPage: 50 }"
        :rows-per-page-options="[10, 25, 50, 100, 200]"
      >
        <template #body-cell-source="props">
          <q-td :props="props">
            <q-badge :label="maintenanceSourceLabel(props.row)" :color="maintenanceSourceColor(props.row)" />
          </q-td>
        </template>
        <template #body-cell-status="props">
          <q-td :props="props"><q-badge :label="props.value" :color="maintenanceStatusColor(props.value)" /></q-td>
        </template>
        <template #body-cell-actions="props">
          <q-td :props="props" auto-width>
            <q-btn v-if="props.row.status !== 'completed'" flat dense round icon="task_alt" color="positive" class="q-mr-xs" @click="completeMaintenanceRow(props.row)" />
            <q-btn v-if="props.row.schedule_id" flat dense round icon="event_repeat" color="positive" class="q-mr-xs" @click="openEditMaintenanceSchedule(props.row)" />
            <q-btn flat dense round icon="edit" color="primary" class="q-mr-xs" @click="openEditMaintenance(props.row)" />
            <q-btn flat dense round icon="delete" color="negative" @click="deleteMaintenanceTask(props.row)" />
          </q-td>
        </template>
        <template #item="props">
          <div class="q-pa-xs col-12">
            <q-card flat bordered>
              <q-card-section class="q-pb-sm">
                <div class="text-subtitle2">{{ props.row.asset_tag || t('maintenance.noAssetTag') }}</div>
                <div class="text-caption text-grey-7">{{ props.row.product_name || t('maintenance.unknown') }} · {{ props.row.maintenance_type }}</div>
                <div class="q-mt-xs"><q-badge :label="maintenanceSourceLabel(props.row)" :color="maintenanceSourceColor(props.row)" /></div>
              </q-card-section>
              <q-card-section class="q-pt-none q-pb-sm">
                <div class="row q-col-gutter-xs items-center">
                  <div class="col-12"><q-badge :color="maintenanceStatusColor(props.row.status)" :label="props.row.status" /></div>
                  <div class="col-12 text-caption">{{ t('maintenance.scheduled') }}: {{ props.row.scheduled_date || '-' }}</div>
                  <div class="col-12 text-caption" v-if="props.row.completed_date">{{ t('maintenance.completed') }}: {{ props.row.completed_date }}</div>
                  <div class="col-12 text-caption" v-if="props.row.notes">{{ props.row.notes }}</div>
                </div>
              </q-card-section>
              <q-card-actions align="right">
                <q-btn v-if="props.row.status !== 'completed'" flat dense icon="task_alt" color="positive" @click="completeMaintenanceRow(props.row)" />
                <q-btn v-if="props.row.schedule_id" flat dense icon="event_repeat" color="positive" @click="openEditMaintenanceSchedule(props.row)" />
                <q-btn flat dense icon="edit" color="primary" @click="openEditMaintenance(props.row)" />
                <q-btn flat dense icon="delete" color="negative" @click="deleteMaintenanceTask(props.row)" />
              </q-card-actions>
            </q-card>
          </div>
        </template>
      </q-table>
    </q-tab-panel>

    <!-- ==================== SCHEDULES TAB ==================== -->
    <q-tab-panel name="schedules" class="q-pa-none">
      <div class="row items-center q-mb-sm">
        <q-input v-model="scheduleSearch" dense outlined clearable :placeholder="t('maintenance.searchSchedules')" class="col">
          <template #prepend><q-icon name="search" /></template>
        </q-input>
        <q-btn class="q-ml-sm" color="positive" icon="event_repeat" :label="t('maintenance.createSchedule')" unelevated @click="openCreateMaintenance('schedule')" />
      </div>

      <div v-if="selectedSchedules.length" class="row items-center q-gutter-sm q-mb-sm">
        <q-badge color="primary" :label="t('maintenance.selectedCount', { count: selectedSchedules.length })" />
        <q-btn color="secondary" icon="edit" :label="t('maintenance.bulkEdit')" unelevated @click="bulkScheduleDialogOpen = true" />
        <q-btn color="negative" icon="delete" :label="t('maintenance.bulkDelete')" unelevated @click="runBulkDeleteSchedules" />
        <q-btn flat :label="t('maintenance.clear')" @click="selectedSchedules = []" />
      </div>

      <q-table
        :rows="filteredSchedules"
        :columns="scheduleColumns"
        row-key="id"
        selection="multiple"
        v-model:selected="selectedSchedules"
        :grid="compactGrid"
        :hide-header="compactGrid"
        flat bordered class="ec-card"
        :loading="store.loading"
        :pagination="{ rowsPerPage: 50 }"
        :rows-per-page-options="[10, 25, 50, 100, 200]"
      >
        <template #body-cell-id="props">
          <q-td :props="props">#{{ props.row.id }}</q-td>
        </template>
        <template #body-cell-interval="props">
          <q-td :props="props">{{ scheduleIntervalLabel(props.row) }}</q-td>
        </template>
        <template #body-cell-task_count="props">
          <q-td :props="props">{{ scheduleTaskCount(props.row.id) }}</q-td>
        </template>
        <template #body-cell-updated_at="props">
          <q-td :props="props">{{ formatDateTime(props.row.updated_at) }}</q-td>
        </template>
        <template #body-cell-actions="props">
          <q-td :props="props" auto-width>
            <q-btn flat dense round icon="edit" color="primary" class="q-mr-xs" @click="openEditMaintenanceSchedule(props.row)" />
            <q-btn flat dense round icon="delete" color="negative" @click="deleteSchedule(props.row)" />
          </q-td>
        </template>
        <template #item="props">
          <div class="q-pa-xs col-12">
            <q-card flat bordered>
              <q-card-section class="q-pb-sm">
                <div class="text-subtitle2">{{ t('maintenance.scheduleLabel', { id: props.row.id }) }}</div>
                <div class="text-caption text-grey-7">{{ props.row.maintenance_type || '-' }} · {{ scheduleIntervalLabel(props.row) }}</div>
              </q-card-section>
              <q-card-section class="q-pt-none q-pb-sm">
                <div class="row q-col-gutter-xs items-center">
                  <div class="col-12 text-caption">{{ t('maintenance.tasks') }}: {{ scheduleTaskCount(props.row.id) }}</div>
                  <div class="col-12 text-caption">{{ t('maintenance.scheduled') }}: {{ props.row.scheduled_date || '-' }}</div>
                  <div class="col-12 text-caption" v-if="props.row.notes">{{ props.row.notes }}</div>
                </div>
              </q-card-section>
              <q-card-actions align="right">
                <q-btn flat dense icon="edit" color="primary" @click="openEditMaintenanceSchedule(props.row)" />
                <q-btn flat dense icon="delete" color="negative" @click="deleteSchedule(props.row)" />
              </q-card-actions>
            </q-card>
          </div>
        </template>
      </q-table>
    </q-tab-panel>
    </q-tab-panels>

    <!-- ==================== DIALOGS ==================== -->
    <MaintenanceDialog v-model="maintenanceDialogOpen" :task="maintenanceEditing" :mode="maintenanceDialogMode" :initial-device-id="maintenanceInitialDeviceId" @saved="onMaintenanceSaved" />
    <MaintenanceScheduleDialog v-model="maintenanceScheduleDialogOpen" :schedule="maintenanceScheduleEditing" @saved="onMaintenanceScheduleSaved" />
    <MaintenanceCompleteDialog v-model="maintenanceCompleteDialogOpen" :task="maintenanceCompleteTarget" @saved="onMaintenanceCompleteSaved" />
    <BulkMaintenanceDialog v-model="bulkMaintenanceDialogOpen" :selected-tasks="selectedMaintenance" @saved="onBulkMaintenanceSaved" />
    <BulkScheduleDialog v-model="bulkScheduleDialogOpen" :selected-schedules="selectedSchedules" @saved="onBulkSchedulesSaved" />

    <ProductInfoDialog v-model="productInfoDialogOpen" :product="productInfoTarget" @edit-product="openProductEdit(productInfoTarget)" @view-device="(id) => openDeviceInfo(id)" />
    <ProductDialog v-model="productDialogOpen" :product="productEditing" @saved="onProductDialogSaved" />
    <DeviceInfoDialog v-model="deviceInfoDialogOpen" :device="deviceInfoTarget" @edit-device="(id) => openDeviceInfo(id)" @view-device="(id) => openDeviceInfo(id)" />
    <DefectReportDialog v-model="defectDialogOpen" @success="onDefectCreated" />
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQuasar } from 'quasar'
import { useInventoryStore } from '../stores/inventory'
import { useCompactGrid } from '../composables/useCompactGrid'
import MaintenanceDialog from '../components/MaintenanceDialog.vue'
import MaintenanceScheduleDialog from '../components/MaintenanceScheduleDialog.vue'
import MaintenanceCompleteDialog from '../components/MaintenanceCompleteDialog.vue'
import BulkMaintenanceDialog from '../components/BulkMaintenanceDialog.vue'
import BulkScheduleDialog from '../components/BulkScheduleDialog.vue'
import DefectReportDialog from '../components/DefectReportDialog.vue'
import ProductDialog from '../components/ProductDialog.vue'
import ProductInfoDialog from '../components/ProductInfoDialog.vue'
import DeviceInfoDialog from '../components/DeviceInfoDialog.vue'

const { t } = useI18n()
const $q = useQuasar()
const store = useInventoryStore()
const compactGrid = useCompactGrid(1024)

const tab = ref('defects')
const loading = ref(false)
const savingComment = ref(false)

const productInfoDialogOpen = ref(false)
const productInfoTarget = ref(null)
const productDialogOpen = ref(false)
const productEditing = ref(null)
const deviceInfoDialogOpen = ref(false)
const deviceInfoTarget = ref(null)

const defectReports = computed(() => store.defectReports)
const pendingTaskCount = computed(() => store.maintenances.filter(m => m.status !== 'completed' && m.status !== 'canceled').length)

const { defectReports: _dr } = store

function formatDateTime(val) {
  if (!val) return '-'
  try { return new Date(val).toLocaleString() } catch { return val }
}

function selectedRowIds(rows) {
  return (rows || []).map(r => r.id || r).filter(Boolean)
}

// ==================== DEFECTS ====================
const defectSearch = ref('')
const defectStatusFilter = ref(null)
const defectSeverityFilter = ref(null)
const defectAssetFilter = ref('')
const selectedDefects = ref([])
const expandedDefectId = ref(null)
const expandedDefectComments = ref([])
const newDefectComment = ref('')
const defectDialogOpen = ref(false)

const defectStatusOptions = [
  { label: t('maintenance.defectStatusOpen'), value: 'open' },
  { label: t('maintenance.defectStatusInProgress'), value: 'in_progress' },
  { label: t('maintenance.defectStatusResolved'), value: 'resolved' },
  { label: t('maintenance.defectStatusClosed'), value: 'closed' },
]
const defectSeverityOptions = [
  { label: t('maintenance.defectSeverityLow'), value: 'low' },
  { label: t('maintenance.defectSeverityMedium'), value: 'medium' },
  { label: t('maintenance.defectSeverityHigh'), value: 'high' },
  { label: t('maintenance.defectSeverityCritical'), value: 'critical' },
]
const defectStatusFilterOptions = computed(() => [{ label: t('maintenance.all'), value: null }, ...defectStatusOptions])
const defectSeverityFilterOptions = computed(() => [{ label: t('maintenance.all'), value: null }, ...defectSeverityOptions])

const defectColumns = [
  { name: 'id', label: t('maintenance.columnId'), field: 'id', sortable: true, style: 'width: 60px' },
  { name: 'asset_tag', label: t('maintenance.columnDevice'), field: 'asset_tag', sortable: true },
  { name: 'product_name', label: t('maintenance.columnProduct'), field: 'product_name', sortable: true },
  { name: 'title', label: t('maintenance.columnTitle'), field: 'title', sortable: true, style: 'min-width: 180px' },
  { name: 'description', label: t('maintenance.columnDescription'), field: 'description', style: 'min-width: 200px' },
  { name: 'status', label: t('maintenance.columnStatus'), field: 'status', sortable: true },
  { name: 'severity', label: t('maintenance.columnSeverity'), field: 'severity', sortable: true },
  { name: 'created_at', label: t('maintenance.columnCreated'), field: 'created_at', sortable: true },
  { name: 'actions', label: '', field: 'actions', style: 'width: 90px' },
]

const filteredDefects = computed(() => {
  let result = defectReports.value
  if (defectStatusFilter.value) result = result.filter(d => d.status === defectStatusFilter.value)
  if (defectSeverityFilter.value) result = result.filter(d => d.severity === defectSeverityFilter.value)
  const assetTag = defectAssetFilter.value?.trim().toLowerCase()
  if (assetTag) result = result.filter(d => String(d.asset_tag || '').toLowerCase().includes(assetTag))
  const needle = defectSearch.value?.trim().toLowerCase()
  if (needle) result = result.filter(d => String(d.title || '').toLowerCase().includes(needle))
  return result
})

const defectFieldTimers = {}
function updateDefectField(defect, field, value) {
  defect[field] = value
  const key = `${defect.id}-${field}`
  if (defectFieldTimers[key]) clearTimeout(defectFieldTimers[key])
  defectFieldTimers[key] = setTimeout(async () => {
    try { await store.updateDefectReport(defect.id, { [field]: value }) } catch { /* overwritten on refresh */ }
  }, 600)
}

async function toggleDefectComments(defect) {
  if (expandedDefectId.value === defect.id) {
    expandedDefectId.value = null
    expandedDefectComments.value = []
    return
  }
  expandedDefectId.value = defect.id
  expandedDefectComments.value = []
  try { expandedDefectComments.value = await store.fetchDefectComments(defect.id) } catch { expandedDefectComments.value = [] }
}

async function addDefectComment(defectId) {
  const text = (newDefectComment.value || '').trim()
  if (!text || !defectId) return
  savingComment.value = true
  try {
    const comment = await store.createDefectComment(defectId, text)
    expandedDefectComments.value.push(comment)
    newDefectComment.value = ''
    const defect = defectReports.value.find(d => d.id === defectId)
    if (defect) defect.commentCount = (defect.commentCount || 0) + 1
  } catch { /* ignore */ } finally { savingComment.value = false }
}

async function deleteDefect(defect) {
  $q.dialog({
    title: t('maintenance.deleteDefect'),
    message: t('maintenance.deleteDefectConfirm', { title: defect.title || defect.id }),
    cancel: true, persistent: true,
    ok: { label: t('maintenance.delete'), color: 'negative' },
  }).onOk(async () => {
    try {
      await store.deleteDefectReport(defect.id)
      if (expandedDefectId.value === defect.id) { expandedDefectId.value = null; expandedDefectComments.value = [] }
    } catch (error) {
      $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('maintenance.failedDelete') })
    }
  })
}

async function runBulkDeleteDefects() {
  const ids = selectedRowIds(selectedDefects.value)
  if (!ids.length) return
  $q.dialog({
    title: t('maintenance.bulkDeleteDefects'),
    message: t('maintenance.bulkDeleteDefectsConfirm', { count: ids.length }),
    cancel: true, persistent: true,
    ok: { label: t('maintenance.delete'), color: 'negative' },
  }).onOk(async () => {
    loading.value = true
    try {
      const result = await store.bulkDeleteDefectReports(ids)
      selectedDefects.value = []
      $q.notify({ type: 'positive', message: t('maintenance.defectsDeleted', { count: result?.deleted || 0 }) })
    } catch (error) {
      $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('maintenance.failedDelete') })
    } finally { loading.value = false }
  })
}

// ==================== MAINTENANCE TASKS ====================
const maintenanceSearch = ref('')
const selectedMaintenance = ref([])
const maintenanceDialogOpen = ref(false)
const maintenanceEditing = ref(null)
const maintenanceDialogMode = ref('task')
const maintenanceInitialDeviceId = ref(null)
const maintenanceScheduleDialogOpen = ref(false)
const maintenanceScheduleEditing = ref(null)
const maintenanceCompleteDialogOpen = ref(false)
const maintenanceCompleteTarget = ref(null)
const bulkMaintenanceDialogOpen = ref(false)
const bulkScheduleDialogOpen = ref(false)

const maintenanceColumns = [
  { name: 'asset_tag', label: t('maintenance.columnAssetTag'), field: 'asset_tag', sortable: true, align: 'left' },
  { name: 'product_name', label: t('maintenance.columnProduct'), field: 'product_name', sortable: true, align: 'left' },
  { name: 'maintenance_type', label: t('maintenance.columnType'), field: 'maintenance_type', sortable: true, align: 'left' },
  { name: 'source', label: t('maintenance.columnSource'), field: row => maintenanceSourceLabel(row), sortable: false, align: 'left' },
  { name: 'status', label: t('maintenance.columnStatus'), field: 'status', sortable: true, align: 'left' },
  { name: 'scheduled_date', label: t('maintenance.columnScheduled'), field: 'scheduled_date', sortable: true, align: 'left' },
  { name: 'completed_date', label: t('maintenance.columnCompleted'), field: 'completed_date', sortable: true, align: 'left' },
  { name: 'notes', label: t('maintenance.columnNotes'), field: 'notes', sortable: false, align: 'left' },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
]

const filteredMaintenance = computed(() => {
  const needle = maintenanceSearch.value.trim().toLowerCase()
  if (!needle) return store.maintenances
  return store.maintenances.filter(item =>
    [item.asset_tag, item.product_name, item.maintenance_type, item.status, item.notes]
      .filter(Boolean)
      .some(value => String(value).toLowerCase().includes(needle))
  )
})

function maintenanceStatusColor(status) {
  if (status === 'completed') return 'positive'
  if (status === 'in_progress') return 'warning'
  if (status === 'canceled') return 'grey'
  return 'info'
}
function maintenanceSourceLabel(row) {
  return Number(row?.schedule_id || 0) ? `Schedule #${row.schedule_id}` : 'Manual'
}
function maintenanceSourceColor(row) {
  return Number(row?.schedule_id || 0) ? 'secondary' : 'grey-7'
}

function openCreateMaintenance(mode = 'schedule', preferredDeviceId = null) {
  maintenanceDialogMode.value = mode === 'task' ? 'task' : 'schedule'
  maintenanceEditing.value = null
  maintenanceInitialDeviceId.value = preferredDeviceId || null
  maintenanceDialogOpen.value = true
}
function openEditMaintenance(item) {
  maintenanceEditing.value = item
  maintenanceDialogOpen.value = true
}
async function openEditMaintenanceSchedule(item) {
  const scheduleId = Number(item?.schedule_id || item?.id || 0)
  if (!scheduleId) return
  try {
    maintenanceScheduleEditing.value = await store.fetchMaintenanceSchedule(scheduleId)
    maintenanceScheduleDialogOpen.value = true
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('maintenance.failedLoadSchedule') })
  }
}
function completeMaintenanceRow(item) {
  maintenanceCompleteTarget.value = item || null
  maintenanceCompleteDialogOpen.value = true
}
function onMaintenanceSaved() { maintenanceDialogOpen.value = false; maintenanceEditing.value = null }
function onMaintenanceScheduleSaved() { maintenanceScheduleDialogOpen.value = false; maintenanceScheduleEditing.value = null }
function onMaintenanceCompleteSaved() { maintenanceCompleteDialogOpen.value = false; maintenanceCompleteTarget.value = null }
function onBulkMaintenanceSaved() { selectedMaintenance.value = [] }
function onBulkSchedulesSaved() { selectedSchedules.value = [] }

async function deleteMaintenanceTask(item) {
  $q.dialog({
    title: t('maintenance.deleteTask'),
    message: t('maintenance.deleteTaskConfirm', { id: item.id }),
    cancel: true, persistent: true,
    ok: { label: t('maintenance.delete'), color: 'negative' },
  }).onOk(async () => {
    try {
      await store.bulkDeleteMaintenance([item.id])
      $q.notify({ type: 'positive', message: t('maintenance.taskDeleted') })
    } catch (error) {
      $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('maintenance.failedDelete') })
    }
  })
}

async function runBulkDeleteMaintenance() {
  const ids = selectedRowIds(selectedMaintenance.value)
  if (!ids.length) return
  $q.dialog({
    title: t('maintenance.bulkDeleteTasks'),
    message: t('maintenance.bulkDeleteTasksConfirm', { count: ids.length }),
    cancel: true, persistent: true,
    ok: { label: t('maintenance.delete'), color: 'negative' },
  }).onOk(async () => {
    loading.value = true
    try {
      const result = await store.bulkDeleteMaintenance(ids)
      selectedMaintenance.value = []
      $q.notify({ type: 'positive', message: t('maintenance.tasksDeleted', { count: result?.deleted || 0 }) })
    } catch (error) {
      $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('maintenance.failedDelete') })
    } finally { loading.value = false }
  })
}

// ==================== SCHEDULES ====================
const scheduleSearch = ref('')
const selectedSchedules = ref([])

const scheduleColumns = [
  { name: 'id', label: t('maintenance.columnId'), field: 'id', sortable: true, align: 'left' },
  { name: 'maintenance_type', label: t('maintenance.columnType'), field: 'maintenance_type', sortable: true, align: 'left' },
  { name: 'interval', label: t('maintenance.columnInterval'), field: row => scheduleIntervalLabel(row), sortable: false, align: 'left' },
  { name: 'scheduled_date', label: t('maintenance.columnScheduled'), field: 'scheduled_date', sortable: true, align: 'left' },
  { name: 'task_count', label: t('maintenance.columnLinkedTasks'), field: row => scheduleTaskCount(row.id), sortable: false, align: 'left' },
  { name: 'notes', label: t('maintenance.columnNotes'), field: 'notes', sortable: false, align: 'left' },
  { name: 'updated_at', label: t('maintenance.columnUpdated'), field: 'updated_at', sortable: true, align: 'left' },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
]

function scheduleTaskCount(scheduleId) {
  const targetId = Number(scheduleId || 0)
  if (!targetId) return 0
  return (store.maintenances || []).filter(item => Number(item?.schedule_id || 0) === targetId).length
}
function scheduleIntervalLabel(schedule) {
  const mode = String(schedule?.interval_mode || '').toLowerCase()
  const value = Number(schedule?.interval_value)
  if (!Number.isFinite(value) || value <= 0) return mode === 'runtime' ? 'Runtime' : 'Calendar'
  return mode === 'runtime' ? `Every ${value}h` : `Every ${value}d`
}
const filteredSchedules = computed(() => {
  const needle = scheduleSearch.value.trim().toLowerCase()
  if (!needle) return store.schedules
  return store.schedules.filter(item =>
    [item.id, item.maintenance_type, item.interval_mode, item.interval_value, item.scheduled_date, item.notes]
      .filter(value => value !== null && value !== undefined)
      .some(value => String(value).toLowerCase().includes(needle))
  )
})

async function deleteSchedule(schedule) {
  $q.dialog({
    title: t('maintenance.deleteSchedule'),
    message: t('maintenance.deleteScheduleConfirm', { id: schedule.id }),
    cancel: true, persistent: true,
    ok: { label: t('maintenance.delete'), color: 'negative' },
  }).onOk(async () => {
    try {
      await store.bulkDeleteMaintenanceSchedules([schedule.id])
      $q.notify({ type: 'positive', message: t('maintenance.scheduleDeleted') })
    } catch (error) {
      $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('maintenance.failedDelete') })
    }
  })
}

async function runBulkDeleteSchedules() {
  const ids = selectedRowIds(selectedSchedules.value)
  if (!ids.length) return
  $q.dialog({
    title: t('maintenance.bulkDeleteSchedules'),
    message: t('maintenance.bulkDeleteSchedulesConfirm', { count: ids.length }),
    cancel: true, persistent: true,
    ok: { label: t('maintenance.delete'), color: 'negative' },
  }).onOk(async () => {
    loading.value = true
    try {
      const result = await store.bulkDeleteMaintenanceSchedules(ids)
      selectedSchedules.value = []
      $q.notify({ type: 'positive', message: t('maintenance.schedulesDeleted', { count: result?.deleted || 0 }) })
    } catch (error) {
      $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('maintenance.failedDelete') })
    } finally { loading.value = false }
  })
}

// ==================== INFO DIALOGS ====================
async function openDeviceInfo(deviceId) {
  const targetId = Number(deviceId || 0)
  if (!targetId) return
  let device = store.devices.find(d => d.id === targetId)
  if (!device) {
    try { const { data } = await (await import('../boot/axios')).api.get(`/api/v1/inventory/devices/${targetId}`); device = data } catch { return }
  }
  deviceInfoTarget.value = device
  deviceInfoDialogOpen.value = true
}

async function openProductInfo(row) {
  if (!row?.product_id) return
  let product = store.products.find(p => p.id === row.product_id)
  if (!product) {
    try { const { data } = await (await import('../boot/axios')).api.get(`/api/v1/inventory/products/${row.product_id}`); product = data } catch { return }
  }
  productInfoTarget.value = product
  productInfoDialogOpen.value = true
}

function openProductEdit(product) { productEditing.value = product; productDialogOpen.value = true }
function onProductDialogSaved() { refresh() }

function onDefectCreated() {
  defectDialogOpen.value = false
  store.fetchDefectReports()
}

// ==================== REFRESH ====================
async function refresh() {
  loading.value = true
  try {
    await Promise.all([
      store.fetchDefectReports().then(defects => {
        for (const d of defects) d.commentCount = 0
        return Promise.all(defects.map(async d => {
          try { const comments = await store.fetchDefectComments(d.id); d.commentCount = comments.length } catch { d.commentCount = 0 }
        }))
      }),
      store.fetchMaintenance(),
      store.fetchMaintenanceSchedules(),
    ])
  } finally { loading.value = false }
}

onMounted(refresh)
</script>

<style lang="scss" scoped>
.comment-bubble {
  background: #f5f5f5;
  border-radius: 6px;
  padding: 6px 10px;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.85rem;
  line-height: 1.4;
}
.link {
  color: var(--q-primary);
  cursor: pointer;
  text-decoration: none;
}
.link:hover { text-decoration: underline; }
</style>

<style lang="scss">
body.body--dark .comment-bubble { background: #333; }
</style>
