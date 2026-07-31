<template>
  <q-dialog :model-value="modelValue" @update:model-value="emit('update:modelValue', $event)" persistent>
    <q-card style="min-width: 700px; max-width: 95vw; max-height: 85vh" class="ec-card">
      <q-card-section class="row items-center q-pb-sm">
        <q-icon name="place" size="24px" color="primary" class="q-mr-sm" />
        <div class="text-h6">{{ t('inventory.locateDeviceMap.title') }}</div>
        <q-space />
        <q-btn flat round dense icon="close" @click="emit('update:modelValue', false)" />
      </q-card-section>
      <q-card-section v-if="device" class="q-pt-none">
        <div class="q-mb-sm">
          <q-badge color="primary" outline :label="deviceLabel" class="q-mr-sm" />
          <q-badge v-if="zone" color="green" outline :label="zonePath" />
          <q-badge v-else color="orange" outline :label="t('inventory.deviceDialog.noLocationSet')" />
        </div>
        <div class="text-caption text-grey-6 q-mb-sm">
          {{ t('inventory.locateDeviceMap.devicesInZone', { count: devicesInZoneCount }) }}
        </div>
      </q-card-section>
      <q-card-section v-if="zone" class="q-pt-none" style="height: 420px">
        <WarehouseMap
          :zones="store.zones"
          :zone-tree="store.zoneTree"
          :devices="store.devices"
          :highlight-zone-ids="highlightZoneIds"
          :focus-zone-id="currentFocusZoneId"
          :breadcrumb="currentBreadcrumb"
          @drill-down="onDrillDown"
          @drill-up="onDrillUp"
        />
      </q-card-section>
      <q-card-section v-else class="q-pt-none">
        <q-banner class="bg-orange-1 text-orange-8 rounded-borders">
          <q-icon name="info" class="q-mr-sm" />
          {{ t('inventory.locateDeviceMap.noZone') }}
        </q-banner>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInventoryStore } from '../stores/inventory'
import WarehouseMap from './WarehouseMap.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  device: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue'])

const { t } = useI18n()
const store = useInventoryStore()

const deviceLabel = computed(() => {
  if (!props.device) return ''
  const tag = String(props.device.asset_tag || '').trim()
  const serial = String(props.device.serial_number || '').trim()
  if (tag) return tag
  if (serial) return serial
  return props.device.id ? `Device #${props.device.id}` : ''
})

const zone = computed(() => {
  if (props.device?.location_zone_id) {
    return store.zones.find(z => z.id === props.device.location_zone_id) || null
  }
  if (props.device?.case_device_id) {
    const caseDevice = store.devices.find(d => d.id === props.device.case_device_id)
    if (caseDevice?.location_zone_id) {
      return store.zones.find(z => z.id === caseDevice.location_zone_id) || null
    }
  }
  return null
})

const zonePath = computed(() => {
  if (!zone.value) return ''
  const parts = []
  let current = zone.value
  while (current) {
    parts.unshift(current.name || '')
    current = store.zones.find(z => z.id === current.parent_id)
  }
  return parts.join(' / ')
})

const highlightZoneIds = computed(() => {
  if (!zone.value) return []
  const ids = [zone.value.id]
  const ancestors = []
  let current = zone.value
  while (current?.parent_id) {
    const parent = store.zones.find(z => z.id === current.parent_id)
    if (parent) {
      ancestors.push(parent.id)
      current = parent
    } else break
  }
  return [...ids, ...ancestors.reverse()]
})

const drillDownFocusId = ref(null)

function getTopAncestorId(z) {
  let current = z
  while (current?.parent_id) {
    const parent = store.zones.find(p => p.id === current.parent_id)
    if (parent) current = parent
    else break
  }
  return current?.id || null
}

const initialFocusId = computed(() => {
  if (!zone.value) return null
  return getTopAncestorId(zone.value)
})

const currentFocusZoneId = computed(() => drillDownFocusId.value ?? initialFocusId.value)

const currentBreadcrumb = computed(() => {
  const focusId = currentFocusZoneId.value
  if (!focusId) return []
  const parts = []
  let current = store.zones.find(z => z.id === focusId)
  while (current) {
    parts.unshift({ id: current.id, name: current.name || '' })
    current = store.zones.find(z => z.id === current.parent_id)
  }
  return parts
})

function onDrillDown(treeNode) {
  drillDownFocusId.value = treeNode?.id ?? null
}

function onDrillUp(treeNode) {
  drillDownFocusId.value = treeNode?.id ?? null
}

watch(() => props.modelValue, (open) => {
  if (open) drillDownFocusId.value = null
})

const devicesInZoneCount = computed(() => {
  if (!zone.value) return 0
  return store.devices.filter(d => d.location_zone_id === zone.value.id).length
})
</script>
