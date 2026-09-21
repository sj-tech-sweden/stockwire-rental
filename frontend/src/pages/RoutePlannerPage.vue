<template>
  <q-page class="route-planner-page">
    <!-- Header row -->
    <div class="row items-center q-pa-md q-pb-sm">
      <q-icon name="alt_route" size="md" color="primary" class="q-mr-sm" />
      <div class="ec-page-title">{{ t('routePlanner.title') }}</div>
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

    <!-- Metrics -->
    <div class="row q-col-gutter-md q-px-md q-pb-sm">
      <div class="col-6 col-md-3">
        <q-card flat bordered class="ec-card q-pa-md">
          <div class="ec-metric-label">{{ t('routePlanner.totalRoutes') }}</div>
          <div class="ec-metric-value">{{ store.routes.length }}</div>
        </q-card>
      </div>
      <div class="col-6 col-md-3">
        <q-card flat bordered class="ec-card q-pa-md">
          <div class="ec-metric-label">{{ t('routePlanner.plannedRoutes') }}</div>
          <div class="ec-metric-value">{{ plannedRoutesCount }}</div>
        </q-card>
      </div>
      <div class="col-6 col-md-3">
        <q-card flat bordered class="ec-card q-pa-md">
          <div class="ec-metric-label">{{ t('routePlanner.inProgressRoutes') }}</div>
          <div class="ec-metric-value">{{ inProgressRoutesCount }}</div>
        </q-card>
      </div>
      <div class="col-6 col-md-3">
        <q-card flat bordered class="ec-card q-pa-md">
          <div class="ec-metric-label">{{ t('routePlanner.completedRoutes') }}</div>
          <div class="ec-metric-value">{{ completedRoutesCount }}</div>
        </q-card>
      </div>
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
            <div v-else class="ec-empty-state q-pa-xl">
              <q-icon name="alt_route" size="48px" class="ec-empty-state__icon" />
              <div class="ec-empty-state__title">{{ t('routePlanner.noRoutes') }}</div>
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
              <q-card flat bordered class="ec-card q-mb-md">
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
              <q-card flat bordered class="ec-card q-mb-md">
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

              <!-- Route optimization -->
              <div v-if="route.stops?.length > 1" class="row items-center q-gutter-sm q-mb-md">
                 <q-input
                  v-model="originAddress"
                  :label="t('routePlanner.originAddress')"
                  :hint="t('routePlanner.originAddressHint')"
                  outlined
                  dense
                  clearable
                  class="col-grow"
                  @update:model-value="onOriginChange"
                />
                <q-btn
                  unelevated
                  icon="alt_route"
                  :label="t('routePlanner.optimizeRoute')"
                  color="deep-purple-7"
                  size="md"
                  :loading="optimizing"
                  @click="onOptimizeRoute"
                />
                <q-btn
                  outline
                  icon="map"
                  :label="t('routePlanner.previewRoute')"
                  color="primary"
                  size="md"
                  :loading="previewLoading"
                  @click="loadPreview"
                />
              </div>

              <q-banner
                v-if="route.stops?.length > 0 && !driveTimesAvailable && driveTimesNote"
                dense
                class="ec-banner ec-banner--info q-mb-md"
              >
                {{ driveTimesNote }}
              </q-banner>

              <q-card v-if="preview" flat bordered class="ec-card q-mb-md">
                <q-card-section>
                  <div class="text-subtitle2 q-mb-sm">
                    <q-icon name="map" size="xs" class="q-mr-xs" />{{ t('routePlanner.routePreview') }}
                  </div>
                  <div v-if="hasPreviewMap" class="rounded-borders" style="position:relative;border:1px solid #d6dbe2;overflow:hidden;">
                    <div ref="mapEl" style="height:340px;width:100%;background:#eef1f5;"></div>
                    <q-chip v-if="mapLocked" dense class="absolute-top-left q-ma-xs" color="grey-3" text-color="dark" icon="lock">
                      {{ t('routePlanner.mapLocked') }}
                    </q-chip>
                    <q-btn
                      dense
                      round
                      unelevated
                      :icon="mapLocked ? 'lock' : 'lock_open'"
                      :color="mapLocked ? 'grey-8' : 'primary'"
                      class="absolute-top-right q-ma-xs map-control-btn"
                      :title="mapLocked ? t('routePlanner.unlockMap') : t('routePlanner.lockMap')"
                      @click="toggleMapLock"
                    />
                    <q-btn
                      dense
                      round
                      unelevated
                      icon="center_focus_weak"
                      color="primary"
                      class="absolute-bottom-right q-ma-xs map-control-btn"
                      :title="t('routePlanner.resetMapView')"
                      @click="resetMapView"
                    />
                  </div>
                  <div v-else class="text-caption text-grey q-mb-sm">{{ t('routePlanner.previewNoMap') }}</div>
                  <div v-if="(preview.pickup_zones || []).length" class="text-caption text-grey-7 q-mt-sm">
                    {{ t('routePlanner.pickupZones') }}
                  </div>
                  <div v-if="hasPreviewMap" class="row q-gutter-xs q-mt-sm items-center flex-wrap">
                    <q-chip
                      v-for="(p, idx) in previewMapPoints"
                      :key="idx"
                      dense
                      :style="{ backgroundColor: p.color, color: '#fff' }"
                    >
                      {{ p.label }}. {{ p.kind === 'start' ? t('routePlanner.start') : (p.address || '') }}
                    </q-chip>
                  </div>
                  <q-list dense separator class="q-mt-sm">
                    <q-item v-for="(it, i) in previewItems" :key="i">
                      <q-item-section avatar><q-avatar size="24px" :style="{ backgroundColor: it.color }" text-color="white">{{ it.label }}</q-avatar></q-item-section>
                      <q-item-section>
                        <q-item-label>
                          <span v-if="it.kind === 'pickup'" class="text-italic text-grey-8">{{ t('routePlanner.pickup') }}: </span>{{ it.address || '—' }}
                        </q-item-label>
                        <q-item-label caption>
                          <template v-if="it.resolved">{{ it.latitude }}, {{ it.longitude }}</template>
                          <span v-else class="text-negative">{{ t('routePlanner.unresolvedAddress') }}</span>
                        </q-item-label>
                      </q-item-section>
                    </q-item>
                  </q-list>
                  <q-banner v-if="!preview.all_resolved" dense class="ec-banner ec-banner--warning q-mt-sm">
                    {{ t('routePlanner.previewUnresolvedHint') }}
                  </q-banner>
                </q-card-section>
              </q-card>

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
                    <div class="row items-center q-gutter-xs q-mt-xs">
                      <span class="text-caption ec-text-muted">
                        {{ t('routePlanner.cargoWeight') }}: {{ Number(stop.cargo_weight_kg || 0).toFixed(1) }} kg
                        · {{ t('routePlanner.cargoVolume') }}: {{ Number(stop.cargo_volume_m3 || 0).toFixed(2) }} m³
                      </span>
                      <q-chip
                        v-if="stopCapacityWarning(stop).over"
                        dense
                        color="negative"
                        text-color="white"
                        icon="warning"
                        :title="capacityOverDetail(stop)"
                      >
                        {{ capacityOverLabel(stop) }}
                      </q-chip>
                      <q-chip
                        v-else-if="!stopCapacityWarning(stop).assigned && !stopCapacityWarning(stop).routeHasVehicle"
                        dense
                        color="grey-4"
                        text-color="dark"
                      >
                        {{ t('routePlanner.noVehicleForStop') }}
                      </q-chip>
                      <q-chip
                        v-else-if="stopCapacityWarning(stop).vehicleCount > 1"
                        dense
                        color="grey-3"
                        text-color="dark"
                      >
                        {{ t('routePlanner.sharedStop', { count: stopCapacityWarning(stop).vehicleCount }) }}
                      </q-chip>
                      <template v-if="driveTimesAvailable && stopDriveTime(stop)">
                        <q-chip dense color="blue-1" text-color="blue-10" icon="schedule">
                          {{ t('routePlanner.driveTime') }}: {{ formatDuration(stopDriveTime(stop).leg_duration_s) }}
                          · {{ formatDistance(stopDriveTime(stop).leg_distance_m) }}
                        </q-chip>
                      </template>
                    </div>
                  </q-item-section>
                  <q-item-section side>
                    <div class="row q-gutter-xs items-center">
                      <q-btn flat dense round icon="open_in_new" size="sm" color="primary" @click.stop="openJob(stop.job_id)" :title="t('routePlanner.openJob')" />
                      <q-btn flat dense round icon="qr_code_scanner" size="sm" color="positive" @click.stop="scanStopJob(stop.job_id)" :title="t('routePlanner.scanThisJob')" />
                      <q-btn flat dense round icon="arrow_upward" size="sm" color="grey-7" @click="moveStopUp(stop.id)" />
                      <q-btn flat dense round icon="arrow_downward" size="sm" color="grey-7" @click="moveStopDown(stop.id)" />
                      <q-btn flat dense round icon="delete" size="sm" color="negative" @click="onRemoveStop(stop.id)" />
                    </div>
                  </q-item-section>
                </q-item>
              </q-list>
              <div v-else class="ec-empty-state q-pa-xl">
                <q-icon name="add_shopping_cart" size="48px" class="ec-empty-state__icon" />
                <div class="ec-empty-state__title">{{ t('routePlanner.noStops') }}</div>
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
          <div v-else class="full-height flex flex-center ec-empty-state">
            <q-icon name="alt_route" size="64px" class="ec-empty-state__icon" />
            <div class="ec-empty-state__title">{{ t('routePlanner.selectRoute') }}</div>
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
      <q-card style="min-width: 400px" class="ec-card">
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
import { ref, computed, watch, onMounted, nextTick, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useRoutePlannerStore } from '../stores/routePlanner'
import { useSettingsStore } from '../stores/settings'
import VehicleDialog from '../components/VehicleDialog.vue'
import JobPickerDialog from '../components/JobPickerDialog.vue'
import PackingListDialog from '../components/PackingListDialog.vue'
import VehicleSuggestionDialog from '../components/VehicleSuggestionDialog.vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { locationQueryFromParts } from '../utils/maps'

const { t } = useI18n()
const $q = useQuasar()
const router = useRouter()
const store = useRoutePlannerStore()
const settings = useSettingsStore()

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
const originAddress = ref('')
const optimizing = ref(false)

// Default route start = the company address from company settings (unless the
// user enters a different starting address in the origin field).
const companyAddress = computed(() => {
  const p = settings.companyProfile
  if (!p) return ''
  // Prefer the real street address for geocoding; only fall back to the company
  // name when no street address is configured (avoids querying "CompanyName, Country").
  const hasStreet = !!(p.address_line1 || p.address_line2)
  return locationQueryFromParts({
    name: hasStreet ? undefined : p.company_name,
    address: [p.address_line1, p.address_line2].filter(Boolean).join(' '),
    city: p.city,
    postal_code: p.postal_code,
    country: p.country,
  })
})
const driveTimes = ref({}) // stop_id -> { leg_duration_s, leg_distance_m }
const driveTimesAvailable = ref(false)
const driveTimesNote = ref(null)
const preview = ref(null) // RouteLocationsResponse
const previewLoading = ref(false)

const mapEl = ref(null)
const mapInstance = ref(null)
const mapMarkers = []
const mapLocked = ref(true)

const START_COLOR = '#16a34a'
const PICKUP_COLOR = '#0f172a'
const STOP_PALETTE = ['#2563eb', '#f59e0b', '#9333ea', '#dc2626', '#0891b2', '#db2777', '#65a30d', '#ea580c']
function stopColor(i) { return STOP_PALETTE[i % STOP_PALETTE.length] }

function makePinIcon(color, label) {
  return L.divIcon({
    className: 'route-pin',
    html: `<div class="route-pin-inner" style="--pin-color:${color}"><span>${label}</span></div>`,
    iconSize: [26, 34],
    iconAnchor: [13, 33],
    popupAnchor: [0, -28],
    tooltipAnchor: [0, -30],
  })
}

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

// Points shown on the preview map, in routing order: optional origin, then the
// equipment pickup zones (derived from the jobs' equipment), then each delivery
// stop with its color.
const previewMapPoints = computed(() => {
  if (!preview.value) return []
  const points = []
  const origin = preview.value.origin
  if (origin) {
    points.push({
      kind: 'start',
      color: START_COLOR,
      label: 'S',
      address: origin.address,
      resolved: !!origin.resolved,
      lat: origin.resolved ? Number(origin.latitude) : null,
      lon: origin.resolved ? Number(origin.longitude) : null,
    })
  }
  const seenPickups = new Set()
  for (const z of (preview.value.pickup_zones || [])) {
    const dedupKey = z.effective_latitude != null
      ? `${z.effective_latitude},${z.effective_longitude}`
      : (z.effective_address || z.address || z.name)
    if (seenPickups.has(dedupKey)) continue
    seenPickups.add(dedupKey)
    const resolved = !!z.resolved
    points.push({
      kind: 'pickup',
      color: PICKUP_COLOR,
      label: 'P',
      address: z.effective_address || z.address || z.name,
      resolved,
      lat: resolved ? Number(z.effective_latitude) : null,
      lon: resolved ? Number(z.effective_longitude) : null,
    })
  }
  for (let i = 0; i < sortedStops.value.length; i++) {
    const stop = sortedStops.value[i]
    const loc = preview.value.stops.find(s => s.stop_id === stop.id)
    const resolved = !!(loc && loc.resolved)
    points.push({
      kind: 'stop',
      color: stopColor(i),
      label: String(i + 1),
      address: loc?.address,
      resolved,
      lat: resolved ? Number(loc.latitude) : null,
      lon: resolved ? Number(loc.longitude) : null,
    })
  }
  return points
})

// Full ordered route shown in the preview list: optional origin, then the
// equipment pickup zones (deduplicated by resolved location), then the delivery
// stops. Pickups appear here so the route reflects where equipment is collected.
const previewItems = computed(() => {
  if (!preview.value) return []
  const items = []
  const origin = preview.value.origin
  if (origin) {
    items.push({
      kind: 'start',
      label: 'S',
      color: START_COLOR,
      title: t('routePlanner.start'),
      address: origin.address,
      resolved: !!origin.resolved,
      latitude: origin.resolved ? origin.latitude : null,
      longitude: origin.resolved ? origin.longitude : null,
    })
  }
  const seen = new Set()
  for (const z of (preview.value.pickup_zones || [])) {
    const key = z.effective_latitude != null
      ? `${z.effective_latitude},${z.effective_longitude}`
      : (z.effective_address || z.address || z.name)
    if (seen.has(key)) continue
    seen.add(key)
    items.push({
      kind: 'pickup',
      label: 'P',
      color: PICKUP_COLOR,
      title: t('routePlanner.pickup'),
      address: z.effective_address || z.address || z.name,
      resolved: !!z.resolved,
      latitude: z.resolved ? z.effective_latitude : null,
      longitude: z.resolved ? z.effective_longitude : null,
    })
  }
  for (let i = 0; i < sortedStops.value.length; i++) {
    const stop = sortedStops.value[i]
    const loc = preview.value.stops.find(s => s.stop_id === stop.id)
    items.push({
      kind: 'stop',
      label: String(i + 1),
      color: stopColor(i),
      title: `${i + 1}.`,
      address: loc?.address,
      resolved: !!(loc && loc.resolved),
      latitude: loc?.resolved ? loc.latitude : null,
      longitude: loc?.resolved ? loc.longitude : null,
    })
  }
  return items
})

const hasPreviewMap = computed(() => previewMapPoints.value.some(p => p.resolved))

function applyMapLockState() {
  const map = mapInstance.value
  if (!map) return
  const handlers = ['dragging', 'scrollWheelZoom', 'doubleClickZoom', 'boxZoom', 'keyboard', 'touchZoom']
  for (const h of handlers) {
    const layer = map[h]
    if (!layer) continue
    if (mapLocked.value) layer.disable()
    else layer.enable()
  }
}

function renderPreviewMap() {
  const el = mapEl.value
  if (!el || !preview.value) return
  if (mapInstance.value && mapInstance.value.getContainer() !== el) {
    mapInstance.value.remove()
    mapInstance.value = null
  }
  const markers = previewMapPoints.value.filter(p => p.resolved && p.lat != null && p.lon != null)
  if (!markers.length) return
  if (!mapInstance.value) {
    const map = L.map(el, { zoomControl: true }).setView([markers[0].lat, markers[0].lon], 12)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map)
    mapInstance.value = map
  }
  const map = mapInstance.value
  mapMarkers.forEach(m => map.removeLayer(m))
  mapMarkers.length = 0
  const latlngs = []
  for (const p of markers) {
    const title = (p.kind === 'start'
      ? t('routePlanner.start') + ': '
      : p.kind === 'pickup'
        ? t('routePlanner.pickup') + ': '
        : `${p.label}. `) + (p.address || '')
    const marker = L.marker([p.lat, p.lon], { icon: makePinIcon(p.color, p.label) })
      .bindTooltip(title, { direction: 'top', opacity: 0.95 })
      .bindPopup(title)
      .addTo(map)
    mapMarkers.push(marker)
    latlngs.push([p.lat, p.lon])
  }
  if (latlngs.length) map.fitBounds(L.latLngBounds(latlngs).pad(0.2))
  map.invalidateSize()
  applyMapLockState()
}

function toggleMapLock() {
  mapLocked.value = !mapLocked.value
  applyMapLockState()
}

function resetMapView() {
  const map = mapInstance.value
  if (!map) return
  const latlngs = previewMapPoints.value
    .filter(p => p.resolved && p.lat != null && p.lon != null)
    .map(p => [p.lat, p.lon])
  if (latlngs.length) {
    map.fitBounds(L.latLngBounds(latlngs).pad(0.2))
    map.invalidateSize()
  }
}

onBeforeUnmount(() => {
  if (mapInstance.value) {
    mapInstance.value.remove()
    mapInstance.value = null
  }
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
    w += Number(stop.cargo_weight_kg || 0)
  }
  return w.toFixed(1)
})

const totalVolume = computed(() => {
  if (!route.value?.stops) return '0'
  let v = 0
  for (const stop of route.value.stops) {
    v += Number(stop.cargo_volume_m3 || 0)
  }
  return v.toFixed(2)
})

function vehicleCapacity(vehicle) {
  if (!vehicle) return { maxWeight: null, maxVolume: null }
  const maxWeight = vehicle.vehicle_type === 'trailer' && vehicle.max_payload_kg != null
    ? Number(vehicle.max_payload_kg)
    : (vehicle.max_weight_kg != null ? Number(vehicle.max_weight_kg) : null)
  let maxVolume = null
  if (vehicle.max_volume_m3 != null) {
    maxVolume = Number(vehicle.max_volume_m3)
  } else if (vehicle.interior_length_cm && vehicle.interior_width_cm && vehicle.interior_height_cm) {
    maxVolume = (vehicle.interior_length_cm * vehicle.interior_width_cm * vehicle.interior_height_cm) / 1000000
  }
  return { maxWeight, maxVolume }
}

function stopCapacityWarning(stop) {
  const routeVehicles = route.value?.vehicles || []
  const weight = Number(stop.cargo_weight_kg || 0)
  const volume = Number(stop.cargo_volume_m3 || 0)
  if (routeVehicles.length === 0) {
    return { assigned: false, over: false, routeHasVehicle: false, weight, volume }
  }
  // All vehicles on the route serve all stops and can share the load, so a
  // stop only overloads the route when its cargo exceeds the COMBINED
  // capacity of every assigned vehicle.
  let combWeight = 0
  let combVolume = 0
  let weightKnown = true
  let volumeKnown = true
  for (const rv of routeVehicles) {
    const vehicle = store.vehicles.find(v => v.id === rv.vehicle_id)
    if (!vehicle) continue
    const cap = vehicleCapacity(vehicle)
    if (cap.maxWeight != null) combWeight += cap.maxWeight
    else weightKnown = false
    if (cap.maxVolume != null) combVolume += cap.maxVolume
    else volumeKnown = false
  }
  const overWeight = weightKnown && weight > combWeight
  const overVolume = volumeKnown && volume > combVolume
  return {
    assigned: true,
    over: overWeight || overVolume,
    routeHasVehicle: true,
    vehicleCount: routeVehicles.length,
    combinedWeight: weightKnown ? combWeight : null,
    combinedVolume: volumeKnown ? combVolume : null,
    overWeight,
    overVolume,
    weight,
    volume,
  }
}

function capacityOverDetail(stop) {
  const w = stopCapacityWarning(stop)
  const lines = []
  if (w.overWeight) {
    lines.push(t('routePlanner.exceedsWeight', {
      weight: w.weight.toFixed(1),
      maxWeight: w.combinedWeight != null ? w.combinedWeight.toFixed(1) : '—',
    }))
  }
  if (w.overVolume) {
    lines.push(t('routePlanner.exceedsVolume', {
      volume: w.volume.toFixed(2),
      maxVolume: w.combinedVolume != null ? w.combinedVolume.toFixed(2) : '—',
    }))
  }
  return lines.join('\n')
}

function capacityOverLabel(stop) {
  const w = stopCapacityWarning(stop)
  if (w.overWeight && w.overVolume) return t('routePlanner.overCapacityBoth')
  if (w.overWeight) return t('routePlanner.overCapacityWeight')
  if (w.overVolume) return t('routePlanner.overCapacityVolume')
  return t('routePlanner.overCapacity')
}

function formatDuration(seconds) {
  if (seconds == null) return '—'
  const mins = Math.round(seconds / 60)
  if (mins < 60) return `${mins} min`
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return m ? `${h} h ${m} min` : `${h} h`
}

function formatDistance(meters) {
  if (meters == null) return '—'
  if (meters < 1000) return `${Math.round(meters)} m`
  return `${(meters / 1000).toFixed(1)} km`
}

function stopDriveTime(stop) {
  return driveTimes.value[stop.id] || null
}

async function loadPreview() {
  if (!route.value) return
  previewLoading.value = true
  try {
    preview.value = await store.getRouteLocations(route.value.id, originAddress.value || null)
    await nextTick()
    renderPreviewMap()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
  } finally {
    previewLoading.value = false
  }
}

const plannedRoutesCount = computed(() => store.routes.filter(r => r.status === 'planned').length)
const inProgressRoutesCount = computed(() => store.routes.filter(r => r.status === 'in_progress').length)
const completedRoutesCount = computed(() => store.routes.filter(r => r.status === 'completed').length)

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
  try {
    await settings.fetchCompanyProfile()
  } catch (e) {
    // Company profile is optional for the route planner; ignore if unavailable.
  }
})

watch(statusFilter, async (val) => {
  const params = {}
  if (val) params.status = val
  await store.fetchRoutes(params)
})

async function selectRoute(id) {
  selectedRouteId.value = id
  await store.fetchRoute(id)
  originAddress.value = companyAddress.value || ''
  await loadDriveTimes(id)
}

async function loadDriveTimes(id) {
  driveTimes.value = {}
  driveTimesAvailable.value = false
  driveTimesNote.value = null
  try {
    const res = await store.getRouteDriveTimes(id, originAddress.value || null)
    driveTimesAvailable.value = res.available
    driveTimesNote.value = res.note || null
    const map = {}
    for (const leg of res.stops || []) {
      map[leg.stop_id] = { leg_duration_s: leg.leg_duration_s, leg_distance_m: leg.leg_distance_m }
    }
    driveTimes.value = map
  } catch (err) {
    driveTimesNote.value = err.response?.data?.detail || err.message
  }
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

function openJob(jobId) {
  if (!jobId) return
  router.push({ path: `/jobs/${jobId}` })
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

async function onOptimizeRoute() {
  if (!route.value || route.value.stops?.length < 2) return
  optimizing.value = true
  try {
    const updated = await store.optimizeRoute(route.value.id, originAddress.value || null)
    store.currentRoute = updated
    const idx = store.routes.findIndex(r => r.id === route.value.id)
    if (idx >= 0) store.routes[idx] = updated
    await loadDriveTimes(route.value.id)
    $q.notify({ type: 'positive', message: t('routePlanner.optimizedRoute') })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
  } finally {
    optimizing.value = false
  }
}

async function onOriginChange() {
  preview.value = null
  if (route.value) await loadDriveTimes(route.value.id)
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

/* Floating map control buttons must sit above the Leaflet panes */
.map-control-btn {
  z-index: 1000;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.35);
}

/* Custom Leaflet pin markers (dynamically inserted, so use :deep) */
:deep(.route-pin-inner) {
  width: 26px;
  height: 26px;
  border-radius: 50% 50% 50% 0;
  background: var(--pin-color, #2563eb);
  transform: rotate(-45deg);
  border: 2px solid #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
}
:deep(.route-pin-inner span) {
  transform: rotate(45deg);
  color: #fff;
  font-weight: 700;
  font-size: 12px;
  line-height: 1;
}
</style>
