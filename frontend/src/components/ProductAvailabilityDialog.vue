<template>
  <q-dialog :model-value="modelValue" :maximized="isPhone" @update:model-value="emit('update:modelValue', $event)">
    <q-card :style="isPhone ? 'width: 100vw; max-width: 100vw; height: 100vh' : 'min-width: 860px; max-width: 96vw'" class="ec-card">
      <q-card-section>
        <div class="text-h6">{{ t('inventory.availability.title', { sku: product?.sku || '-' }) }}</div>
        <div class="text-caption text-grey-7">{{ product?.name || '-' }}</div>
      </q-card-section>

      <q-card-section class="q-pt-none" :style="isPhone ? 'max-height: calc(100vh - 140px); overflow: auto;' : ''">
        <div class="row items-center q-col-gutter-sm q-mb-sm">
          <div class="col-auto">
            <q-toggle v-model="includeDrafts" color="primary" :label="t('inventory.availability.includeDrafts')" />
          </div>
          <div class="col-auto">
            <q-select
              v-model="days"
              :options="daysOptions"
              :label="t('inventory.availability.range')"
              outlined
              dense
              emit-value
              map-options
            />
          </div>
        </div>

        <div class="row items-center q-col-gutter-xs q-mb-sm text-caption text-grey-7">
          <div class="col-auto">{{ t('inventory.availability.heatmap') }}</div>
          <div class="col-auto"><q-badge color="negative" text-color="white" :label="t('inventory.availability.lowShortage')" /></div>
          <div class="col-auto"><q-badge color="warning" text-color="black" :label="t('inventory.availability.tight')" /></div>
          <div class="col-auto"><q-badge color="positive" text-color="white" :label="t('inventory.availability.healthy')" /></div>
        </div>

        <q-table
          :rows="calendarRows"
          :columns="calendarColumns"
          row-key="date"
          flat
          bordered
          dense
          :pagination="{ rowsPerPage: 0 }"
          :rows-per-page-options="[0]"
        >
          <template #body-cell-reserved="props">
            <q-td :props="props">
              <div class="text-weight-medium">{{ props.row.reserved }}</div>
            </q-td>
          </template>
          <template #body-cell-available="props">
            <q-td :props="props">
              <div
                class="availability-heat-cell"
                :style="heatStyle(props.row)"
                :title="heatLabel(props.row)"
              >
                <span class="availability-heat-value">{{ props.row.available }}</span>
                <span class="availability-heat-ratio">{{ percent(props.row) }}%</span>
              </div>
            </q-td>
          </template>
        </q-table>
      </q-card-section>

      <q-card-actions :align="isPhone ? 'stretch' : 'right'" :class="isPhone ? 'q-pa-md bg-grey-2' : ''">
        <q-space />
        <q-btn flat :class="isPhone ? 'full-width' : ''" :label="t('inventory.availability.close')" @click="emit('update:modelValue', false)" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useInventoryStore } from '../stores/inventory'
import { useJobsStore } from '../stores/jobs'

const props = defineProps({
  modelValue: Boolean,
  product: { type: Object, default: null },
})

const emit = defineEmits([
  'update:modelValue',
])

const $q = useQuasar()
const { t } = useI18n()
const store = useInventoryStore()
const jobsStore = useJobsStore()

const isPhone = computed(() => $q.screen.lt.md)

const includeDrafts = ref(false)
const days = ref(60)

const daysOptions = [
  { label: t('inventory.daysCount', { count: 30 }), value: 30 },
  { label: t('inventory.daysCount', { count: 60 }), value: 60 },
  { label: t('inventory.daysCount', { count: 90 }), value: 90 },
]

const calendarColumns = [
  { name: 'date', label: t('inventory.columnDate'), field: 'date', align: 'left' },
  { name: 'weekday', label: t('inventory.columnDay'), field: 'weekday', align: 'left' },
  { name: 'reserved', label: t('inventory.columnReserved'), field: 'reserved', align: 'left' },
  { name: 'available', label: t('inventory.columnAvailable'), field: 'available', align: 'left' },
]

function toYmd(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function normalizeYmd(value) {
  if (!value) return ''
  return String(value).slice(0, 10)
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

function eventoryPacklistsForDate(product, dateYmd) {
  if (!Array.isArray(product?.eventory_packlists)) return []
  return product.eventory_packlists.filter(packlist => {
    if (!packlist || typeof packlist !== 'object') return false
    const status = String(packlist?.job_status || '').toLowerCase()
    if (status && ['cancelled', 'canceled', 'completed', 'returned'].includes(status)) return false
    const start = normalizeYmd(packlist?.start_date)
    const end = normalizeYmd(packlist?.end_date)
    if (!start || !end) return false
    return !(dateYmd < start || dateYmd > end)
  })
}

const calendarRows = computed(() => {
  if (!props.product) return []

  const today = new Date()
  const isRental = String(props.product?.product_type || '').toLowerCase() === 'rental'
    || props.product?.is_rental_product
  const baseOperational = isRental
    ? Math.max(0, Number(props.product?.eventory_available_qty || 0))
    : (store.devices || []).filter(device => {
      if (device.product_id !== props.product.id) return false
      const condition = String(device.condition || '').toLowerCase()
      const status = String(device.status || '').toLowerCase()
      const retired = device.retire_date ? new Date(device.retire_date) <= today : false
      if (retired) return false
      if (condition === 'damaged') return false
      if (status === 'maintenance') return false
      return true
    }).length

  const reservingStatuses = includeDrafts.value
    ? new Set(['draft', 'confirmed', 'in_progress'])
    : new Set(['confirmed', 'in_progress'])

  const jobsById = new Map((jobsStore.jobs || []).map(job => [job.id, job]))
  const requirements = (jobsStore.requirements || []).filter(req => req.product_id === props.product.id)
  const rows = []

  for (let i = 0; i < Number(days.value || 60); i += 1) {
    const date = new Date(today)
    date.setDate(today.getDate() + i)
    const dateYmd = toYmd(date)

    let reserved = 0
    let externalReserved = 0
    for (const req of requirements) {
      const job = jobsById.get(req.job_id)
      if (!job) continue
      if (!reservingStatuses.has(String(job.status || '').toLowerCase())) continue
      const start = normalizeYmd(job.start_date)
      const end = normalizeYmd(job.end_date)
      if (!start || !end) continue
      if (dateYmd < start || dateYmd > end) continue
      reserved += Math.max(Number(req.quantity_required || 0), Number(req.quantity_picked || 0))
    }

    if (isRental) {
      for (const packlist of eventoryPacklistsForDate(props.product, dateYmd)) {
        externalReserved += Math.max(Number(packlist?.quantity || 0), Number(packlist?.out || 0), 0)
      }
    }

    const totalReserved = reserved + externalReserved

    rows.push({
      date: dateYmd,
      weekday: date.toLocaleDateString(undefined, { weekday: 'short' }),
      reserved: totalReserved,
      available: Math.max(baseOperational - totalReserved, 0),
      total_operational: baseOperational,
    })
  }

  return rows
})

function percent(row) {
  const total = Math.max(Number(row?.total_operational || 0), 0)
  const available = Math.max(Number(row?.available || 0), 0)
  if (!total) return available > 0 ? 100 : 0
  return Math.round((available / total) * 100)
}

function heat(row) {
  const total = Math.max(Number(row?.total_operational || 0), 0)
  const available = Math.max(Number(row?.available || 0), 0)
  const reserved = Math.max(Number(row?.reserved || 0), 0)

  if (total <= 0) {
    if (reserved > 0) return { rgb: '220, 53, 69', alpha: 0.34, level: t('inventory.availability.lowShortage') }
    return { rgb: '245, 124, 0', alpha: 0.2, level: t('inventory.availability.tight') }
  }

  const availabilityRatio = available / total
  const utilization = clamp(reserved / total, 0, 1.6)

  if (availabilityRatio <= 0.25) {
    return { rgb: '220, 53, 69', alpha: 0.18 + (utilization * 0.18), level: t('inventory.availability.lowShortage') }
  }
  if (availabilityRatio <= 0.55) {
    return { rgb: '245, 124, 0', alpha: 0.14 + (utilization * 0.14), level: t('inventory.availability.tight') }
  }
  return { rgb: '46, 125, 50', alpha: 0.12 + ((1 - availabilityRatio) * 0.16), level: t('inventory.availability.healthy') }
}

function heatStyle(row) {
  const h = heat(row)
  return {
    backgroundColor: `rgba(${h.rgb}, ${clamp(h.alpha, 0.1, 0.42).toFixed(3)})`,
    border: `1px solid rgba(${h.rgb}, 0.35)`,
  }
}

function heatLabel(row) {
  const h = heat(row)
  const pct = percent(row)
  return `${h.level} • ${pct}% available (${row.available}/${row.total_operational})`
}
</script>
