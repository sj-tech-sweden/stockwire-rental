<template>
  <q-page class="route-planner-page">
    <!-- Header row -->
    <div class="row items-center q-pa-md q-pb-sm">
      <q-icon name="alt_route" size="md" color="primary" class="q-mr-sm" />
      <div class="text-h5">{{ t('routePlanner.title') }}</div>
      <q-space />
      <q-btn
        unelevated
        color="primary"
        icon="add"
        :label="t('routePlanner.newRoute')"
        class="q-mr-sm"
        @click="showCreateRoute = true"
      />
      <q-btn
        unelevated
        color="secondary"
        icon="local_shipping"
        :label="t('routePlanner.vehicles')"
        @click="showVehicles = true"
      />
    </div>

    <!-- Filter row -->
    <div class="row items-center q-px-md q-pb-sm">
      <q-select
        v-model="statusFilter"
        :options="statusOptions"
        emit-value
        map-options
        outlined
        dense
        clearable
        :label="t('routePlanner.routeStatus')"
        style="min-width: 160px"
      />
    </div>

    <!-- Main content -->
    <div class="route-planner-content" :class="{ 'mobile-layout': isMobile }">
      <!-- Mobile: show route list only when nothing selected -->
      <template v-if="!isMobile || !selectedRouteId">
        <div class="route-list-panel">
          <q-scroll-area class="full-height">
            <q-list v-if="store.routes.length > 0" class="q-pa-xs">
              <q-item
                v-for="route in store.routes"
                :key="route.id"
                clickable
                v-ripple
                :active="selectedRouteId === route.id"
                active-class="bg-blue-2 text-weight-medium"
                class="rounded-borders q-mb-xs"
                @click="selectRoute(route.id)"
              >
                <q-item-section>
                  <q-item-label :class="{ 'text-weight-bold': selectedRouteId === route.id }">{{ route.name }}</q-item-label>
                  <q-item-label caption :class="{ 'text-weight-medium': selectedRouteId === route.id }">
                    {{ route.start_date }} · {{ route.stops?.length || 0 }} {{ t('routePlanner.stops') }}
                    <template v-if="route.vehicles?.length > 0"> · <q-icon name="local_shipping" size="xs" /> {{ route.vehicles.map(v => v.vehicle_name).join(' + ') }}</template>
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <div class="row items-center q-gutter-xs">
                    <q-badge :color="statusColor(route.status)" :label="t(`routePlanner.${route.status}`)" />
                    <q-btn flat dense round icon="map" size="sm" color="grey-7" @click.stop="quickOpenMaps(route.id)" />
                    <q-btn flat dense round icon="inventory_2" size="sm" color="grey-7" @click.stop="quickOpenPackList(route)" />
                    <q-btn flat dense round icon="delete" size="sm" color="negative" @click.stop="quickDeleteRoute(route)" />
                  </div>
                </q-item-section>
              </q-item>
            </q-list>
            <div v-else class="text-center text-grey q-pa-xl">
              <q-icon name="alt_route" size="48px" color="grey-4" class="q-mb-md" /><br />
              {{ t('routePlanner.noRoutes') }}
            </div>
          </q-scroll-area>
        </div>
      </template>

      <!-- Detail panel (full width on mobile) -->
      <template v-if="!isMobile || selectedRouteId">
        <div class="route-detail-panel">
          <!-- Mobile back button -->
          <div v-if="isMobile && selectedRouteId" class="q-pa-sm">
            <q-btn flat dense icon="arrow_back" :label="t('common.back')" @click="selectedRouteId = null" />
          </div>
          <q-scroll-area class="full-height" v-if="route">
            <div class="q-pa-md">
              <!-- Route header -->
              <div class="row items-center q-mb-md">
                <div class="text-h6 q-mr-md">{{ route.name }}</div>
                <q-badge :color="statusColor(route.status)" class="q-mr-md">{{ t(`routePlanner.${route.status}`) }}</q-badge>
              </div>

              <!-- Route metadata card -->
              <q-card flat bordered class="q-mb-md">
                <q-card-section class="q-gutter-sm">
                  <div class="row q-gutter-md" :class="{ 'column': isMobile }">
                    <q-input
                      v-model="route.name"
                      :label="t('routePlanner.routeName')"
                      outlined
                      dense
                      class="col"
                      :class="{ 'full-width': isMobile }"
                      @blur="onUpdateRoute"
                    />
                    <q-select
                      v-model="route.status"
                      :options="statusOptions"
                      emit-value
                      map-options
                      outlined
                      dense
                      :label="t('routePlanner.routeStatus')"
                      class="col"
                      :class="{ 'full-width': isMobile }"
                      @update:model-value="onUpdateRoute"
                    />
                    <q-input
                      v-model="route.start_date"
                      :label="t('routePlanner.startDate')"
                      type="date"
                      outlined
                      dense
                      class="col"
                      :class="{ 'full-width': isMobile }"
                      @blur="onUpdateRoute"
                    />
                  </div>
                </q-card-section>
              </q-card>

              <!-- Assigned vehicles -->
              <q-card flat bordered class="q-mb-md">
                <q-card-section class="q-pa-sm">
                  <div class="row items-center q-mb-sm">
                    <div class="text-subtitle2"><q-icon name="local_shipping" size="xs" class="q-mr-xs" />{{ t('routePlanner.assignedVehicles') }}</div>
                    <q-space />
                    <q-select
                      v-model="vehicleToAdd"
                      :options="availableVehicles"
                      emit-value
                      map-options
                      outlined
                      dense
                      clearable
                      :label="t('routePlanner.addVehicle')"
                      style="min-width: 200px"
                      class="q-mr-sm"
                      @update:model-value="onAssignVehicle"
                    />
                  </div>
                  <div v-if="route.vehicles?.length > 0" class="row q-gutter-sm">
                    <q-chip
                      v-for="(v, idx) in sortedVehicles"
                      :key="v.vehicle_id"
                      :color="vehicleChipColor(v.vehicle_type)"
                      text-color="white"
                      icon="local_shipping"
                      removable
                      @remove="onRemoveVehicle(v.vehicle_id)"
                    >
                      {{ v.vehicle_name }}
                      <q-badge v-if="route.vehicles.length > 1" color="white" text-color="dark" class="q-ml-xs">#{{ idx + 1 }}</q-badge>
                    </q-chip>
                  </div>
                  <div v-else class="text-caption text-grey">{{ t('routePlanner.noVehicleAssigned') }}</div>
                </q-card-section>
              </q-card>

              <!-- Stops section -->
              <div class="row items-center q-mb-sm">
                <div class="text-subtitle1 text-weight-medium">{{ t('routePlanner.stops') }} ({{ route.stops?.length || 0 }})</div>
                <q-space />
                <q-btn
                  unelevated
                  icon="add"
                  :label="t('routePlanner.addJobs')"
                  color="primary"
                  size="md"
                  class="q-mr-sm"
                  @click="showJobPicker = true"
                />
                <q-btn
                  unelevated
                  icon="local_shipping"
                  :label="t('routePlanner.suggestVehicle')"
                  color="amber-8"
                  text-color="white"
                  size="md"
                  :disable="!route.stops?.length"
                  @click="onSuggestVehicle"
                />
              </div>

              <!-- Action buttons row -->
              <div v-if="route.stops?.length > 0" class="q-gutter-sm q-mb-md">
                <q-btn
                  unelevated
                  icon="qr_code_scanner"
                  :label="t('routePlanner.startScan')"
                  color="positive"
                  size="md"
                  @click="startScanLastJob"
                />
                <q-btn
                  unelevated
                  icon="map"
                  :label="t('routePlanner.openInMaps')"
                  color="primary"
                  size="md"
                  @click="onOpenMaps"
                />
                <q-btn
                  unelevated
                  icon="inventory_2"
                  :label="t('routePlanner.packingList')"
                  color="primary"
                  size="md"
                  @click="showPackingList = true"
                />
                <q-btn
                  unelevated
                  icon="delete"
                  :label="t('routePlanner.deleteRoute')"
                  color="negative"
                  size="md"
                  @click="onDeleteRoute"
                />
              </div>

              <q-list bordered separator v-if="route.stops?.length > 0" class="rounded-borders">
                <q-item v-for="(stop, idx) in sortedStops" :key="stop.id">
                  <q-item-section avatar>
                    <q-avatar size="32px" :color="idx === 0 ? 'primary' : 'grey-4'" text-color="white">
                      {{ idx + 1 }}
                    </q-avatar>
                  </q-item-section>
                  <q-item-section>
                    <q-item-label class="text-weight-medium">{{ stop.job?.job_code || `Job #${stop.job_id}` }}</q-item-label>
                    <q-item-label caption>
                      {{ stop.job?.customer_name || '—' }}
                      <template v-if="stop.job?.venue_name"> · {{ stop.job.venue_name }}</template>
                      <template v-if="stop.job?.venue_address"> · {{ stop.job.venue_address }}</template>
                    </q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <div class="row q-gutter-xs items-center">
                      <q-btn flat dense round icon="qr_code_scanner" size="sm" color="positive" @click.stop="scanStopJob(stop.job_id)" :title="t('routePlanner.scanThisJob')" />
                      <q-btn flat dense round icon="arrow_upward" size="sm" color="grey-7" @click="moveStopUp(stop.id)" />
                      <q-btn flat dense round icon="arrow_downward" size="sm" color="grey-7" @click="moveStopDown(stop.id)" />
                      <q-btn flat dense round icon="delete" size="sm" color="negative" @click="onRemoveStop(stop.id)" />
                    </div>
                  </q-item-section>
                </q-item>
              </q-list>
              <div v-else class="text-center text-grey q-pa-xl">
                <q-icon name="add_shopping_cart" size="48px" color="grey-4" class="q-mb-sm" /><br />
                {{ t('routePlanner.noStops') }}
              </div>

              <!-- Summary -->
              <div v-if="route.stops?.length > 0" class="q-mt-md text-caption text-grey">
                {{ route.stops.length }} {{ t('routePlanner.stops') }} ·
                {{ t('routePlanner.totalWeight') }}: {{ totalWeight }} kg ·
                {{ t('routePlanner.totalVolume') }}: {{ totalVolume }} m³
              </div>
            </div>
          </q-scroll-area>

          <!-- Empty state -->
          <div v-else class="full-height flex flex-center text-grey">
            <div class="text-center">
              <q-icon name="alt_route" size="64px" color="grey-4" class="q-mb-md" /><br />
              {{ t('routePlanner.selectRoute') }}
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Dialogs -->
    <VehicleDialog v-model="showVehicles" />
    <JobPickerDialog
      v-model="showJobPicker"
      :existing-job-ids="existingJobIds"
      @added="onJobsAdded"
    />
    <PackingListDialog v-model="showPackingList" :route-id="selectedRouteId" />
    <VehicleSuggestionDialog
      v-model="showSuggestion"
      :job-ids="route?.stops?.map(s => s.job_id) || []"
      @selected="onVehicleSelected"
    />

    <!-- Create route dialog -->
    <q-dialog v-model="showCreateRoute" persistent>
      <q-card style="min-width: 400px">
        <q-card-section class="text-h6">{{ t('routePlanner.createRoute') }}</q-card-section>
        <q-card-section>
          <q-form @submit="onCreateRoute" class="q-gutter-md">
            <q-input
              v-model="newRouteName"
              :label="t('routePlanner.routeName')"
              outlined
              autofocus
              :rules="[val => !!val || t('common.required')]"
            />
            <q-input
              v-model="newRouteDate"
              :label="t('routePlanner.startDate')"
              type="date"
              outlined
            />
          </q-form>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('common.cancel')" v-close-popup />
          <q-btn unelevated :label="t('common.save')" color="primary" @click="onCreateRoute" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useRoutePlannerStore } from '../stores/routePlanner'
import VehicleDialog from '../components/VehicleDialog.vue'
import JobPickerDialog from '../components/JobPickerDialog.vue'
import PackingListDialog from '../components/PackingListDialog.vue'
import VehicleSuggestionDialog from '../components/VehicleSuggestionDialog.vue'

const { t } = useI18n()
const $q = useQuasar()
const router = useRouter()
const store = useRoutePlannerStore()

const selectedRouteId = ref(null)
const statusFilter = ref(null)
const showVehicles = ref(false)
const showJobPicker = ref(false)
const showPackingList = ref(false)
const showSuggestion = ref(false)
const showCreateRoute = ref(false)
const newRouteName = ref('')
const newRouteDate = ref(new Date().toISOString().slice(0, 10))
const vehicleToAdd = ref(null)

const statusOptions = [
  { label: t('routePlanner.planned'), value: 'planned' },
  { label: t('routePlanner.inProgress'), value: 'in_progress' },
  { label: t('routePlanner.completed'), value: 'completed' },
  { label: t('routePlanner.cancelled'), value: 'cancelled' },
]

const isMobile = computed(() => {
  if (typeof window === 'undefined') return false
  return window.innerWidth <= 768
})

const route = computed(() => store.currentRoute)

const sortedStops = computed(() => {
  if (!route.value?.stops) return []
  return [...route.value.stops].sort((a, b) => a.stop_order - b.stop_order)
})

const sortedVehicles = computed(() => {
  if (!route.value?.vehicles) return []
  return [...route.value.vehicles].sort((a, b) => a.load_order - b.load_order)
})

const assignedVehicleIds = computed(() =>
  route.value?.vehicles?.map(v => v.vehicle_id) || []
)

const availableVehicles = computed(() =>
  store.vehicles
    .filter(v => !assignedVehicleIds.value.includes(v.id))
    .map(v => ({ label: v.name, value: v.id }))
)

const existingJobIds = computed(() =>
  route.value?.stops?.map(s => s.job_id) || []
)

const totalWeight = computed(() => {
  if (!route.value?.stops) return '0'
  let w = 0
  for (const stop of route.value.stops) {
    for (const p of stop.job?.products || []) {
      w += Number(p.weight_kg || 0) * (p.quantity || 1)
    }
  }
  return w.toFixed(1)
})

const totalVolume = computed(() => {
  if (!route.value?.stops) return '0'
  let v = 0
  for (const stop of route.value.stops) {
    for (const p of stop.job?.products || []) {
      v += Number(p.volume_m3 || 0) * (p.quantity || 1)
    }
  }
  return v.toFixed(2)
})

function statusColor(status) {
  const map = { planned: 'blue', in_progress: 'orange', completed: 'green', cancelled: 'grey' }
  return map[status] || 'grey'
}

function vehicleChipColor(type) {
  const map = { truck: 'blue', van: 'teal', trailer: 'orange', car: 'purple' }
  return map[type] || 'grey'
}

onMounted(async () => {
  await Promise.all([store.fetchRoutes(), store.fetchVehicles()])
})

watch(statusFilter, async (val) => {
  const params = {}
  if (val) params.status = val
  await store.fetchRoutes(params)
})

async function selectRoute(id) {
  selectedRouteId.value = id
  await store.fetchRoute(id)
}

async function onCreateRoute() {
  try {
    const r = await store.createRoute({
      name: newRouteName.value,
      start_date: newRouteDate.value,
    })
    showCreateRoute.value = false
    newRouteName.value = ''
    newRouteDate.value = new Date().toISOString().slice(0, 10)
    await selectRoute(r.id)
    $q.notify({ type: 'positive', message: t('common.saved') })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
  }
}

async function onUpdateRoute() {
  if (!route.value) return
  try {
    await store.updateRoute(route.value.id, {
      name: route.value.name,
      status: route.value.status,
      start_date: route.value.start_date,
    })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
  }
}

async function onDeleteRoute() {
  if (!route.value) return
  $q.dialog({
    title: t('common.confirm'),
    message: t('common.deleteConfirm'),
    cancel: t('common.cancel'),
    ok: t('common.delete'),
    color: 'negative',
  }).onOk(async () => {
    try {
      await store.deleteRoute(route.value.id)
      selectedRouteId.value = null
      $q.notify({ type: 'positive', message: t('common.deleted') })
    } catch (err) {
      $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
    }
  })
}

async function onJobsAdded(jobIds) {
  if (!route.value) return
  try {
    for (const jid of jobIds) {
      await store.addStop(route.value.id, jid)
    }
    $q.notify({ type: 'positive', message: t('common.saved') })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
  }
}

async function onRemoveStop(stopId) {
  if (!route.value) return
  try {
    await store.removeStop(route.value.id, stopId)
    $q.notify({ type: 'positive', message: t('common.deleted') })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
  }
}

async function moveStopUp(stopId) {
  if (!route.value?.stops) return
  const ids = sortedStops.value.map(s => s.id)
  const idx = ids.indexOf(stopId)
  if (idx <= 0) return
  ;[ids[idx - 1], ids[idx]] = [ids[idx], ids[idx - 1]]
  try {
    await store.reorderStops(route.value.id, ids)
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
  }
}

async function moveStopDown(stopId) {
  if (!route.value?.stops) return
  const ids = sortedStops.value.map(s => s.id)
  const idx = ids.indexOf(stopId)
  if (idx < 0 || idx >= ids.length - 1) return
  ;[ids[idx], ids[idx + 1]] = [ids[idx + 1], ids[idx]]
  try {
    await store.reorderStops(route.value.id, ids)
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
  }
}

async function onAssignVehicle(vehicleId) {
  if (!route.value || !vehicleId) return
  try {
    const loadOrder = route.value.vehicles?.length || 0
    await store.assignVehicle(route.value.id, vehicleId, loadOrder)
    vehicleToAdd.value = null
    $q.notify({ type: 'positive', message: t('common.saved') })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
  }
}

async function onRemoveVehicle(vehicleId) {
  if (!route.value) return
  try {
    await store.removeVehicle(route.value.id, vehicleId)
    $q.notify({ type: 'positive', message: t('common.deleted') })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
  }
}

function onSuggestVehicle() {
  if (!route.value?.stops?.length) return
  showSuggestion.value = true
}

async function onVehicleSelected(suggestion) {
  if (!route.value) return
  try {
    const existing = route.value.vehicles || []
    for (const v of existing) {
      await store.removeVehicle(route.value.id, v.vehicle_id)
    }
    for (let i = 0; i < suggestion.vehicles.length; i++) {
      await store.assignVehicle(route.value.id, suggestion.vehicles[i].id, i)
    }
    $q.notify({ type: 'positive', message: t('common.saved') })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
  }
}

async function quickOpenMaps(routeId) {
  try {
    const result = await store.exportGoogleMaps(routeId)
    window.open(result.url, '_blank')
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
  }
}

async function quickOpenPackList(route) {
  selectedRouteId.value = route.id
  await store.fetchRoute(route.id)
  showPackingList.value = true
}

function quickDeleteRoute(route) {
  $q.dialog({
    title: t('common.confirm'),
    message: t('common.deleteConfirm'),
    cancel: t('common.cancel'),
    ok: t('common.delete'),
    color: 'negative',
  }).onOk(async () => {
    try {
      await store.deleteRoute(route.id)
      if (selectedRouteId.value === route.id) selectedRouteId.value = null
      $q.notify({ type: 'positive', message: t('common.deleted') })
    } catch (err) {
      $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
    }
  })
}

function startScanLastJob() {
  if (!route.value?.stops?.length) return
  const sorted = [...route.value.stops].sort((a, b) => b.stop_order - a.stop_order)
  const lastJobId = sorted[0]?.job_id
  if (lastJobId) {
    router.push({ path: '/scan', query: { action: 'job_out', jobId: lastJobId } })
  }
}

function scanStopJob(jobId) {
  if (!jobId) return
  router.push({ path: '/scan', query: { action: 'job_out', jobId } })
}

async function onOpenMaps() {
  if (!route.value) return
  try {
    const result = await store.exportGoogleMaps(route.value.id)
    window.open(result.url, '_blank')
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
  }
}
</script>

<style scoped>
.route-planner-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 100px);
}

.route-planner-content {
  flex: 1;
  display: flex;
  min-height: 0;
}

.route-list-panel {
  width: 35%;
  min-width: 280px;
  border-right: 1px solid rgba(0, 0, 0, 0.12);
  display: flex;
  flex-direction: column;
}

.route-detail-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.full-height {
  height: 100%;
}

/* Mobile responsive */
.mobile-layout {
  flex-direction: column;
}

.mobile-layout .route-list-panel {
  width: 100%;
  min-width: 0;
  border-right: none;
  border-bottom: 1px solid rgba(0, 0, 0, 0.12);
  max-height: 50vh;
}

.mobile-layout .route-detail-panel {
  flex: 1;
}

/* Improve selected route visibility */
:deep(.q-item.active) {
  border-left: 3px solid var(--q-primary);
}

/* Fix suggest vehicle button in dark mode */
.q-btn.bg-amber-8 {
  color: white !important;
}
</style>
