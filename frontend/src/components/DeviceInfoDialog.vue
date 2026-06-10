<template>
  <q-dialog :model-value="modelValue" :maximized="isPhone" @update:model-value="emit('update:modelValue', $event)">
    <q-card :style="isPhone ? 'width: 100vw; max-width: 100vw; height: 100vh' : 'min-width: 820px; max-width: 96vw'" class="ec-card">
      <q-card-section>
        <div class="text-h6">{{ t('inventory.infoDialogs.deviceTitle', { assetTag: device?.asset_tag || '-' }) }}</div>
        <div class="text-caption text-grey-7">
          {{ device ? (store.products.find(item => item.id === device.product_id)?.name || `Product #${device.product_id}`) : '-' }}
        </div>
      </q-card-section>

      <q-card-section class="q-pt-none" :style="isPhone ? 'max-height: calc(100vh - 140px); overflow: auto;' : ''">
        <div class="row q-col-gutter-sm q-mb-md">
          <div class="col-12 col-md-4"><q-badge color="grey-8" text-color="white" :label="`Status: ${device?.status || '-'}`" /></div>
          <div class="col-12 col-md-4"><q-badge color="grey-7" text-color="white" :label="`Condition: ${device?.condition || '-'}`" /></div>
          <div class="col-12 col-md-4">
            <q-badge
              :color="device?.current_job_code ? 'info' : 'grey'"
              text-color="white"
              :label="device?.current_job_code ? `Current job: ${device.current_job_code}` : 'Current job: none'"
            />
            <q-btn
              v-if="device?.current_job_id"
              flat
              dense
              :round="isPhone"
              color="primary"
              icon="edit"
              class="q-ml-xs"
              :label="isPhone ? void 0 : 'Edit'"
              :aria-label="isPhone ? 'Edit job' : void 0"
              @click="openJobFromLink(device.current_job_id)"
            />
          </div>
          <div class="col-12">
            <q-btn flat dense color="positive" icon="build" label="Create maintenance task" @click="emit('create-maintenance', device?.id)" />
            <q-btn flat dense color="positive" icon="event_repeat" label="Create maintenance schedule" class="q-ml-xs" @click="emit('create-maintenance', device?.id)" />
            <q-btn
              color="warning"
              icon="warning"
              label="Report defect"
              @click="emit('report-defect', device?.id)"
            />
          </div>
          <div class="col-12 col-md-6 text-caption">
            Serialnumber: {{ device?.serial_number || '-' }}
          </div>
          <div class="col-12 col-md-6 text-caption">
            Barcode: {{ device?.barcode || '-' }}
          </div>
          <div class="col-12 col-md-6 text-caption">
            QR-code: {{ device?.qr_code || '-' }}
          </div>
          <div class="col-12 col-md-6 text-caption">
            RFID: {{ device?.rfid || '-' }}
          </div>
          <div class="col-12 col-md-6 text-caption">
            Usage hours: {{ device?.usage_hours || '-' }}
          </div>
          <div class="col-12 col-md-6 text-caption">
            Location: {{ device?.location || '-' }}
          </div>
          <div class="col-12 col-md-6 text-caption">
            Purchase:
            {{ device?.purchase_price == null ? '-' : formatMoney(device.purchase_price) }}
            <template v-if="device?.purchased_from">
              from {{ device.purchased_from }}
            </template>
            <template v-if="device?.purchase_date">
              at {{ device.purchase_date }}
            </template>
          </div>
          <div class="col-12 col-md-6 text-caption">
            Warranty until: {{ device?.warranty_until || '-' }}
          </div>
          <div class="col-12 col-md-6 text-caption">
            Retirement: {{ device?.retirement_date || '-' }} · Reason: {{ device?.retirement_reason || '-' }}
          </div>
          <div class="col-12 col-md-6 text-caption">
            Sold: {{ device?.sold_price == null ? '-' : formatMoney(device?.sold_price) }}
            <template v-if="device?.sold_date">
              at {{ device.sold_date }}
            </template>
          </div>
          <div class="col-12 col-md-6 text-caption">
            Finance up to: {{ device?.finance_upto || '-' }}
          </div>
          <div class="col-12 col-md-6 text-caption">
            Finance company: {{ device?.finance_company || '-' }} · Ref: {{ device?.finance_ref || '-' }}
          </div>
          <div class="col-12 col-md-6 text-caption">
            Pre-prep: {{ device?.pre_prep || '-' }}
          </div>
          <div class="col-12 col-md-6 text-caption">
            Notes: {{ device?.notes || '-' }}
          </div>
        </div>

        <div class="text-subtitle2 q-mb-sm">Parent Product</div>
        <q-list bordered separator class="rounded-borders q-mb-md">
          <q-item>
            <q-item-section>
              <q-item-label>{{ deviceInfoProduct?.sku || '-' }} · {{ deviceInfoProduct?.name || '-' }}</q-item-label>
              <q-item-label caption>
                Type: {{ deviceInfoProduct?.product_type || '-' }} · Category: {{ deviceInfoProduct?.category || 'Uncategorized' }}
              </q-item-label>
              <q-item-label caption>
                Brand: {{ deviceInfoProduct?.brand || '-' }} · Manufacturer: {{ deviceInfoProduct?.manufacturer || '-' }}
              </q-item-label>
              <q-item-label caption>
                Daily rate: {{ formatMoney(deviceInfoProduct?.daily_rate) }} · Supplier: {{ deviceInfoProduct?.supplier_name || '-' }}
              </q-item-label>
              <q-item-label caption>
                Replacement cost: {{ formatMoney(deviceInfoProduct?.replace_cost) }} · Supplier: {{ deviceInfoProduct?.supplier_name || '-' }}
              </q-item-label>
              <q-item-label caption v-if="deviceInfoProduct?.is_rental_product">
                Rental source: {{ deviceInfoProduct?.external_source || '-' }} · External ref: {{ deviceInfoProduct?.external_reference || '-' }}
              </q-item-label>
              <q-item-label caption v-if="deviceInfoProduct?.is_rental_product">
                Eventory available: {{ Number(deviceInfoProduct?.eventory_available_qty || 0) }} · Is rental: {{ deviceInfoProduct?.is_rental_product ? 'yes' : 'no' }}
              </q-item-label>
              <q-item-label caption>
                Weight: {{ deviceInfoProduct?.weight_kg ?? '-' }} kg · Size: {{ deviceInfoProduct?.height_cm ?? '-' }}x{{ deviceInfoProduct?.width_cm ?? '-' }}x{{ deviceInfoProduct?.depth_cm ?? '-' }} cm
              </q-item-label>
              <q-item-label caption>
                Power: {{ deviceInfoProduct?.power_consumption_watts ?? '-' }} W · Maintenance interval: {{ deviceInfoProduct?.maintenance_interval_days ?? '-' }} days
              </q-item-label>
              <q-item-label caption>
                Devices total: {{ Number(deviceInfoProduct?.total_devices || 0) }} · In store: {{ Number(deviceInfoProduct?.in_store_devices || 0) }} · On site: {{ Number(deviceInfoProduct?.on_site_devices || 0) }} · Damaged: {{ Number(deviceInfoProduct?.damaged_devices || 0) }}
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-btn
                flat
                dense
                color="primary"
                icon="edit"
                label="Edit product"
                @click="emit('edit-product', deviceInfoProduct?.id)"
              />
            </q-item-section>
          </q-item>
        </q-list>

        <div class="text-subtitle2 q-mb-sm">Devices At Same Location</div>
        <q-list bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="row in deviceInfoLocationDevices" :key="row.id">
            <q-item-section>
              <q-item-label>{{ row.asset_tag }} · {{ productNameById(row.product_id) }}</q-item-label>
              <q-item-label caption>
                {{ t('inventory.infoDialogs.deviceStatusCondition', { status: row.status, condition: row.condition || t('inventory.infoDialogs.notAvailable') }) }}
                <span v-if="row.current_job_code"> · Job {{ row.current_job_code }}</span>
              </q-item-label>
            </q-item-section>
            <q-item-section side top>
              <div class="row no-wrap items-center q-gutter-xs">
                <q-btn
                  flat
                  dense
                  :round="isPhone"
                  :color="productActionColor"
                  class="inventory-action-contrast"
                  icon="inventory_2"
                  :label="isPhone ? void 0 : 'Product'"
                  :aria-label="isPhone ? 'Open product' : void 0"
                  @click="emit('edit-product', row.product_id)"
                />
                <q-btn
                  flat
                  dense
                  :round="isPhone"
                  :color="infoActionColor"
                  icon="info"
                  :label="isPhone ? void 0 : 'Info'"
                  :aria-label="isPhone ? 'Open device info' : void 0"
                  @click="emit('view-device', row.id)"
                />
                <q-btn
                  flat
                  dense
                  :round="isPhone"
                  color="primary"
                  icon="edit"
                  :label="isPhone ? void 0 : 'Edit'"
                  :aria-label="isPhone ? 'Edit device' : void 0"
                  @click="emit('edit-device', row.id)"
                />
              </div>
            </q-item-section>
          </q-item>
          <q-item v-if="!deviceInfoLocationDevices.length">
            <q-item-section>
              <q-item-label caption>No other devices in this location.</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <div v-if="deviceInfoIsCase" class="text-subtitle2 q-mb-sm">Devices Inside This Case</div>
        <q-list v-if="deviceInfoIsCase" bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="row in deviceInfoContainedDevices" :key="row.id">
            <q-item-section>
              <q-item-label>{{ row.asset_tag }} · {{ productNameById(row.product_id) }}</q-item-label>
              <q-item-label caption>
                {{ t('inventory.infoDialogs.deviceStatusCondition', { status: row.status, condition: row.condition || t('inventory.infoDialogs.notAvailable') }) }}
                <span v-if="row.current_job_code"> · Job {{ row.current_job_code }}</span>
              </q-item-label>
            </q-item-section>
            <q-item-section side top>
              <div class="row no-wrap items-center q-gutter-xs">
                <q-btn
                  flat
                  dense
                  :round="isPhone"
                  :color="productActionColor"
                  class="inventory-action-contrast"
                  icon="inventory_2"
                  :label="isPhone ? void 0 : 'Product'"
                  :aria-label="isPhone ? 'Open product' : void 0"
                  @click="emit('edit-product', row.product_id)"
                />
                <q-btn
                  flat
                  dense
                  :round="isPhone"
                  :color="infoActionColor"
                  icon="info"
                  :label="isPhone ? void 0 : 'Info'"
                  :aria-label="isPhone ? 'Open device info' : void 0"
                  @click="emit('view-device', row.id)"
                />
                <q-btn
                  flat
                  dense
                  :round="isPhone"
                  color="primary"
                  icon="edit"
                  :label="isPhone ? void 0 : 'Edit'"
                  :aria-label="isPhone ? 'Edit device' : void 0"
                  @click="emit('edit-device', row.id)"
                />
              </div>
            </q-item-section>
          </q-item>
          <q-item v-if="!deviceInfoContainedDevices.length">
            <q-item-section>
              <q-item-label caption>No devices are currently assigned to this case.</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <div class="text-subtitle2 q-mb-sm">Maintenance Overview</div>
        <q-list bordered separator class="rounded-borders q-mb-md">
          <q-item v-if="deviceInfoNextMaintenance">
            <q-item-section>
              <q-item-label>Next scheduled task · {{ deviceInfoNextMaintenance.maintenance_type || '-' }}</q-item-label>
              <q-item-label caption>
                Status: {{ deviceInfoNextMaintenance.status || '-' }} · {{ maintenanceTimingLabel(deviceInfoNextMaintenance) }}
              </q-item-label>
              <q-item-label caption v-if="deviceInfoNextMaintenance.notes">{{ deviceInfoNextMaintenance.notes }}</q-item-label>
            </q-item-section>
            <q-item-section side top>
              <div class="row no-wrap items-center q-gutter-xs">
                <q-btn
                  v-if="deviceInfoNextMaintenance.status !== 'completed'"
                  flat
                  dense
                  color="positive"
                  icon="task_alt"
                  @click="emit('complete-maintenance', deviceInfoNextMaintenance)"
                />
                <q-btn flat dense color="primary" icon="edit" @click="emit('edit-maintenance', deviceInfoNextMaintenance)" />
              </div>
            </q-item-section>
          </q-item>
          <q-item v-else>
            <q-item-section>
              <q-item-label caption>No upcoming maintenance task found.</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <div class="text-subtitle2 q-mb-sm">Previous Maintenance Tasks</div>
        <q-list bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="row in deviceInfoPreviousMaintenance" :key="`maint-prev-${row.id}`">
            <q-item-section>
              <q-item-label>{{ row.maintenance_type || '-' }}</q-item-label>
              <q-item-label caption>
                Status: {{ row.status || '-' }} · {{ maintenanceTimingLabel(row) }}
              </q-item-label>
              <q-item-label caption v-if="row.notes">{{ row.notes }}</q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-badge :color="maintenanceStatusColor(row.status)" :label="row.status || '-'" />
            </q-item-section>
          </q-item>
          <q-item v-if="!deviceInfoPreviousMaintenance.length">
            <q-item-section>
              <q-item-label caption>No previous maintenance tasks found.</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <div class="text-subtitle2 q-mb-sm">Jobs History</div>
        <q-list bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="row in deviceJobHistory" :key="`${row.job_id}-${row.last_event_at}`">
            <q-item-section>
              <q-item-label>{{ row.job_code || `Job #${row.job_id}` }}</q-item-label>
              <q-item-label caption>
                First out: {{ formatDateTime(row.first_out_at) || '-' }} · Last in: {{ formatDateTime(row.last_in_at) || '-' }} · Last event: {{ formatDateTime(row.last_event_at) || '-' }}
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-btn
                flat
                dense
                :round="isPhone"
                color="primary"
                icon="edit"
                :label="isPhone ? void 0 : 'Edit'"
                :aria-label="isPhone ? 'Edit job' : void 0"
                @click="openJobFromLink(row.job_id)"
              />
            </q-item-section>
          </q-item>
          <q-item v-if="!deviceJobHistory.length">
            <q-item-section>
              <q-item-label caption>No job history found for this device.</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <div class="text-subtitle2 q-mb-sm">Audit Timeline</div>
        <q-list bordered separator class="rounded-borders">
          <q-item v-for="row in deviceInfoAudits" :key="row.id">
            <q-item-section>
              <q-item-label>{{ row.action }} · {{ row.message }}</q-item-label>
              <q-item-label caption>
                {{ formatDateTime(row.created_at) || '-' }}
                <span v-if="row.job_code"> · Job {{ row.job_code }}</span>
                <span v-if="row.scan_code"> · Scan {{ row.scan_code }}</span>
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-badge :color="row.success ? 'positive' : 'negative'" :label="row.success ? 'ok' : 'failed'" />
            </q-item-section>
          </q-item>
          <q-item v-if="!deviceInfoAudits.length">
            <q-item-section>
              <q-item-label caption>No audit entries found for this device.</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <div class="text-subtitle2 q-mb-sm q-mt-lg">Defect Reports</div>
        <div v-if="!deviceInfoDefects.length" class="text-caption text-grey-6 q-mb-sm">No defect reports for this device.</div>
        <q-list v-else bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="defect in deviceInfoDefects" :key="defect.id">
            <q-item-section>
              <q-input
                :model-value="defect.title"
                dense
                outlined
                class="text-weight-medium"
                @update:model-value="(v) => updateDefectField(defect, 'title', v)"
              />
              <q-input
                :model-value="defect.description"
                dense
                outlined
                type="textarea"
                autogrow
                placeholder="No description"
                class="q-mt-xs"
                @update:model-value="(v) => updateDefectField(defect, 'description', v || null)"
              />
              <div class="row q-gutter-sm q-mt-xs items-center">
                <q-select
                  :model-value="defect.status"
                  :options="defectStatusOptions"
                  dense
                  outlined
                  emit-value
                  map-options
                  size="sm"
                  style="min-width: 130px"
                  @update:model-value="(v) => updateDefectStatus(defect, v)"
                />
                <q-select
                  :model-value="defect.severity"
                  :options="defectSeverityOptions"
                  dense
                  outlined
                  emit-value
                  map-options
                  size="sm"
                  style="min-width: 110px"
                  @update:model-value="(v) => updateDefectSeverity(defect, v)"
                />
                <q-btn dense flat icon="delete" color="negative" size="sm" @click="deleteDefect(defect)" />
              </div>
              <div v-if="defect.comments?.length" class="q-mt-sm">
                <div v-for="comment in defect.comments" :key="comment.id" class="text-caption q-py-xs">
                  <div class="comment-bubble">
                    {{ comment.comment }}
                    <div v-if="comment.created_at" class="text-grey-5 text-right" style="font-size: 0.7rem;">{{ comment.created_at }}</div>
                  </div>
                </div>
              </div>
              <div class="q-mt-xs">
                <q-input
                  v-model="defect.newComment"
                  dense
                  outlined
                  type="textarea"
                  autogrow
                  placeholder="Add a comment..."
                  class="col-grow"
                />
                <q-btn
                  dense
                  flat
                  icon="send"
                  color="primary"
                  :loading="defect.savingComment"
                  :disable="!defect.newComment?.trim()"
                  @click="addDefectComment(defect)"
                  class="q-mt-xs"
                />
              </div>
            </q-item-section>
          </q-item>
        </q-list>

        <EntityAttachmentsPanel
          entity-type="device"
          :entity-id="device?.id || null"
          :title="t('inventory.infoDialogs.deviceDocuments')"
          default-category="device-document"
          :read-only="true"
        />
      </q-card-section>

      <q-card-actions :align="isPhone ? 'stretch' : 'right'" :class="isPhone ? 'q-pa-md bg-grey-2' : ''">
        <q-space />
        <q-btn flat :class="isPhone ? 'full-width' : ''" :label="t('app.actions.close')" @click="emit('update:modelValue', false)" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useInventoryStore } from '../stores/inventory'
import { useJobsStore } from '../stores/jobs'
import { useSettingsStore } from '../stores/settings'
import { normalizeCurrencyCode } from '../constants/currencies'
import { api } from '../boot/axios'
import EntityAttachmentsPanel from './EntityAttachmentsPanel.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  device: { type: Object, default: null },
  isPhone: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'edit-device', 'edit-product', 'view-device', 'open-job', 'report-defect', 'create-maintenance', 'edit-maintenance', 'complete-maintenance'])

const $q = useQuasar()
const { t } = useI18n()
const store = useInventoryStore()
const jobsStore = useJobsStore()
const settingsStore = useSettingsStore()

const deviceInfoAudits = ref([])
const deviceInfoDefects = ref([])
const defectFieldTimers = {}

const productActionColor = computed(() => ($q.dark.isActive ? 'green-4' : 'secondary'))
const infoActionColor = computed(() => ($q.dark.isActive ? 'teal-4' : 'secondary'))

const defectStatusOptions = [
  { label: 'Open', value: 'open' },
  { label: 'In Progress', value: 'in_progress' },
  { label: 'Resolved', value: 'resolved' },
  { label: 'Closed', value: 'closed' },
]

const defectSeverityOptions = [
  { label: 'Low', value: 'low' },
  { label: 'Medium', value: 'medium' },
  { label: 'High', value: 'high' },
  { label: 'Critical', value: 'critical' },
]

const deviceInfoProduct = computed(() => {
  if (!props.device) return null
  return store.products.find(item => item.id === props.device.product_id) || null
})
const deviceInfoIsCase = computed(() => deviceInfoProduct.value?.product_type === 'case')

const deviceInfoLocationDevices = computed(() => {
  if (!props.device?.location_zone_id) return []
  const sourceId = props.device.id
  return store.devices.filter(item => item.location_zone_id === props.device.location_zone_id && item.id !== sourceId)
})

const deviceInfoContainedDevices = computed(() => {
  if (!props.device?.id) return []
  const caseId = props.device.id
  return store.devices.filter(item => item.case_device_id === caseId)
})

const deviceInfoMaintenance = computed(() => {
  if (!props.device?.id) return []
  const targetId = Number(props.device.id)
  return (store.maintenances || [])
    .filter(item => Number(item.device_id) === targetId)
    .slice()
    .sort((a, b) => maintenanceSortTimestamp(a) - maintenanceSortTimestamp(b))
})

const deviceInfoNextMaintenance = computed(() => {
  const currentUsageHours = Number(props.device?.usage_hours)
  const hasUsageHours = Number.isFinite(currentUsageHours)
  const rows = deviceInfoMaintenance.value
    .filter(item => ['scheduled', 'in_progress'].includes(String(item.status || '').toLowerCase()))
    .slice()
    .sort((a, b) => compareUpcomingMaintenance(a, b, hasUsageHours ? currentUsageHours : null))
  return rows.length ? rows[0] : null
})

const deviceInfoPreviousMaintenance = computed(() => {
  const nextId = deviceInfoNextMaintenance.value?.id
  return deviceInfoMaintenance.value
    .filter(item => item.id !== nextId)
    .slice()
    .sort((a, b) => maintenanceSortTimestamp(b) - maintenanceSortTimestamp(a))
    .slice(0, 12)
})

const deviceJobHistory = computed(() => {
  const byJob = new Map()
  for (const row of deviceInfoAudits.value || []) {
    if (!row?.job_id) continue
    const existing = byJob.get(row.job_id) || {
      job_id: row.job_id,
      job_code: row.job_code || null,
      first_out_at: null,
      last_in_at: null,
      last_event_at: row.created_at,
    }

    if (!existing.job_code && row.job_code) existing.job_code = row.job_code
    if (!existing.last_event_at || String(row.created_at) > String(existing.last_event_at)) {
      existing.last_event_at = row.created_at
    }
    if (row.action === 'job_out') {
      if (!existing.first_out_at || String(row.created_at) < String(existing.first_out_at)) {
        existing.first_out_at = row.created_at
      }
    }
    if (row.action === 'job_in') {
      if (!existing.last_in_at || String(row.created_at) > String(existing.last_in_at)) {
        existing.last_in_at = row.created_at
      }
    }
    byJob.set(row.job_id, existing)
  }
  return [...byJob.values()].sort((a, b) => String(b.last_event_at || '').localeCompare(String(a.last_event_at || '')))
})

function formatDateTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString()
}

function formatMoney(value) {
  const amount = Number(value || 0)
  if (!Number.isFinite(amount)) return '0.00'
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

function productNameById(productId) {
  const item = store.products.find(row => row.id === productId)
  if (!item) return `Product #${productId}`
  return `${item.sku} - ${item.name}`
}

function maintenanceSortTimestamp(row) {
  if (!row) return 0
  const scheduledTs = row.scheduled_date ? new Date(`${row.scheduled_date}T00:00:00`).getTime() : Number.NaN
  const completedTs = row.completed_date ? new Date(`${row.completed_date}T00:00:00`).getTime() : Number.NaN
  const createdTs = row.created_at ? new Date(row.created_at).getTime() : 0
  if (Number.isFinite(scheduledTs)) return scheduledTs
  if (Number.isFinite(completedTs)) return completedTs
  return Number.isFinite(createdTs) ? createdTs : 0
}

function maintenanceUpcomingPriority(row, currentUsageHours = null) {
  const status = String(row?.status || '').toLowerCase()
  const statusRank = status === 'in_progress' ? 0 : 1

  const dueUsageHours = Number(row?.due_usage_hours)
  if (row?.interval_mode === 'runtime' && Number.isFinite(dueUsageHours) && Number.isFinite(currentUsageHours)) {
    const remainingHours = dueUsageHours - currentUsageHours
    const dueRank = remainingHours <= 0 ? 0 : 1
    return [statusRank, 0, dueRank, remainingHours]
  }

  const scheduledTs = row?.scheduled_date ? new Date(`${row.scheduled_date}T00:00:00`).getTime() : Number.NaN
  if (Number.isFinite(scheduledTs)) {
    const todayTs = new Date(new Date().toDateString()).getTime()
    const dayDelta = Math.floor((scheduledTs - todayTs) / 86400000)
    const dueRank = dayDelta <= 0 ? 0 : 1
    return [statusRank, 1, dueRank, dayDelta]
  }

  return [statusRank, 2, 1, maintenanceSortTimestamp(row)]
}

function compareUpcomingMaintenance(a, b, currentUsageHours = null) {
  const pa = maintenanceUpcomingPriority(a, currentUsageHours)
  const pb = maintenanceUpcomingPriority(b, currentUsageHours)
  for (let i = 0; i < pa.length; i += 1) {
    if (pa[i] === pb[i]) continue
    return pa[i] < pb[i] ? -1 : 1
  }
  return maintenanceSortTimestamp(a) - maintenanceSortTimestamp(b)
}

function maintenanceTimingLabel(row) {
  if (!row) return 'No date set'
  if (row.interval_mode === 'runtime' && row.due_usage_hours != null) {
    const dueUsageHours = Number(row.due_usage_hours)
    const currentUsageHours = Number(props.device?.usage_hours)
    if (Number.isFinite(dueUsageHours) && Number.isFinite(currentUsageHours)) {
      const remaining = Number((dueUsageHours - currentUsageHours).toFixed(1))
      if (remaining <= 0) return `Runtime due now (${Math.abs(remaining)}h overdue)`
      return `Runtime due in ${remaining}h (at ${dueUsageHours}h)`
    }
    return `Due at ${row.due_usage_hours} usage hours`
  }
  if (row.scheduled_date) return `Scheduled: ${row.scheduled_date}`
  if (row.completed_date) return `Completed: ${row.completed_date}`
  return 'No date set'
}

function maintenanceStatusColor(status) {
  if (status === 'completed') return 'positive'
  if (status === 'in_progress') return 'warning'
  if (status === 'canceled') return 'grey'
  return 'info'
}

function openJobFromLink(jobId) {
  emit('open-job', jobId)
}

async function loadDeviceData(device) {
  if (!device?.id) return
  deviceInfoAudits.value = []
  deviceInfoDefects.value = []
  try {
    deviceInfoAudits.value = await store.fetchDeviceAuditLogs(device.id, 300)
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || 'Failed to load device history' })
  }
  try {
    const { data: defects } = await api.get('/api/v1/inventory/defect-reports', {
      params: { device_id: device.id }
    })
    deviceInfoDefects.value = defects || []
    for (const defect of deviceInfoDefects.value) {
      try {
        const { data: comments } = await api.get(`/api/v1/inventory/defect-reports/${defect.id}/comments`)
        defect.comments = comments || []
      } catch {
        defect.comments = []
      }
      defect.newComment = ''
      defect.savingComment = false
    }
  } catch {
    deviceInfoDefects.value = []
  }
}

async function refreshDeviceInfoTarget() {
  if (!props.device?.id) return
  try {
    const { data } = await api.get(`/api/v1/inventory/devices/${props.device.id}`)
    Object.assign(props.device, data)
  } catch {
    // ignore
  }
  await loadDeviceData(props.device)
}

async function updateDefectStatus(defect, newStatus) {
  try {
    const { data } = await api.put(`/api/v1/inventory/defect-reports/${defect.id}`, { status: newStatus })
    Object.assign(defect, data)
    await refreshDeviceInfoTarget()
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || 'Failed to update status' })
  }
}

async function updateDefectSeverity(defect, newSeverity) {
  try {
    const { data } = await api.put(`/api/v1/inventory/defect-reports/${defect.id}`, { severity: newSeverity })
    Object.assign(defect, data)
    await refreshDeviceInfoTarget()
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || 'Failed to update severity' })
  }
}

function deleteDefect(defect) {
  $q.dialog({
    title: 'Delete Defect',
    message: `Permanently delete defect "${defect.title || defect.id}"?`,
    cancel: true,
    persistent: true,
    ok: { label: 'Delete', color: 'negative' },
  }).onOk(async () => {
    try {
      await api.delete(`/api/v1/inventory/defect-reports/${defect.id}`)
      deviceInfoDefects.value = deviceInfoDefects.value.filter(d => d.id !== defect.id)
      await refreshDeviceInfoTarget()
    } catch (error) {
      $q.notify({ type: 'negative', message: error?.response?.data?.detail || 'Failed to delete defect' })
    }
  })
}

function updateDefectField(defect, field, value) {
  defect[field] = value
  if (defectFieldTimers[`${defect.id}-${field}`]) {
    clearTimeout(defectFieldTimers[`${defect.id}-${field}`])
  }
  defectFieldTimers[`${defect.id}-${field}`] = setTimeout(async () => {
    try {
      const { data } = await api.put(`/api/v1/inventory/defect-reports/${defect.id}`, { [field]: value })
      Object.assign(defect, data)
    } catch (error) {
      $q.notify({ type: 'negative', message: error?.response?.data?.detail || 'Failed to update' })
    }
  }, 600)
}

async function addDefectComment(defect) {
  const text = (defect.newComment || '').trim()
  if (!text) return
  defect.savingComment = true
  try {
    const { data } = await api.post(`/api/v1/inventory/defect-reports/${defect.id}/comments`, { comment: text })
    defect.comments.push(data)
    defect.newComment = ''
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || 'Failed to add comment' })
  } finally {
    defect.savingComment = false
  }
}

watch(() => props.device, (device) => {
  if (props.modelValue && device) {
    void loadDeviceData(device)
  }
})

watch(() => props.modelValue, (open) => {
  if (open && props.device) {
    void loadDeviceData(props.device)
  }
})
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
:deep(.inventory-action-contrast) {
  color: var(--q-secondary, #26a69a) !important;
}
</style>
