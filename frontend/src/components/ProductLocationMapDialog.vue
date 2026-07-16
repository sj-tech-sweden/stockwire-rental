<template>
  <q-dialog :model-value="modelValue" @update:model-value="emit('update:modelValue', $event)" persistent>
    <q-card style="min-width: 750px; max-width: 95vw; max-height: 85vh" class="ec-card column">
      <q-card-section class="row items-center q-pb-sm shrink-0">
        <q-icon name="inventory_2" size="24px" color="primary" class="q-mr-sm" />
        <div class="text-h6">{{ t('inventory.productLocationMap.title') }}</div>
        <q-space />
        <q-btn flat round dense icon="close" @click="emit('update:modelValue', false)" />
      </q-card-section>
      <q-card-section v-if="product" class="q-pt-none shrink-0">
        <div class="q-mb-sm">
          <q-badge color="primary" outline :label="product.name" class="q-mr-sm" />
          <q-badge v-if="product.sku" color="grey-7" outline :label="product.sku" class="q-mr-sm" />
        </div>
        <div class="row q-col-gutter-xs q-mb-sm">
          <div class="col-auto">
            <q-badge color="blue" :label="t('inventory.productLocationMap.totalDevices', { count: product.total_devices || 0 })" />
          </div>
          <div class="col-auto">
            <q-badge color="green" :label="t('inventory.productLocationMap.inStoreDevices', { count: product.in_store_devices || 0 })" />
          </div>
          <div class="col-auto">
            <q-badge color="orange" :label="t('inventory.productLocationMap.onSiteDevices', { count: product.on_site_devices || 0 })" />
          </div>
          <div class="col-auto">
            <q-badge color="purple" :label="t('inventory.productLocationMap.locationsCount', { count: zoneDeviceCounts.length })" />
          </div>
        </div>
      </q-card-section>
      <q-card-section v-if="zoneDeviceCounts.length" class="q-pt-none col" style="min-height: 300px">
        <WarehouseMap
          :zones="store.zones"
          :zone-tree="store.zoneTree"
          :devices="store.devices"
          :highlight-zone-ids="highlightZoneIds"
          :focus-zone-id="drillDownFocusId"
          @drill-down="onDrillDown"
          @drill-up="onDrillUp"
        />
      </q-card-section>
      <q-card-section v-else class="q-pt-none shrink-0">
        <q-banner class="bg-orange-1 text-orange-8 rounded-borders">
          <q-icon name="info" class="q-mr-sm" />
          {{ t('inventory.productLocationMap.noLocations') }}
        </q-banner>
      </q-card-section>
      <q-card-section v-if="zoneDeviceCounts.length" class="q-pt-none shrink-0" style="max-height: 200px; overflow: auto">
        <div class="text-subtitle2 q-mb-xs">Locations</div>
        <q-list dense bordered separator class="rounded-borders">
          <q-item v-for="zc in zoneDeviceCounts" :key="zc.zone.id">
            <q-item-section avatar>
              <q-icon name="place" color="primary" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ zc.path }}</q-item-label>
              <q-item-label caption>{{ zc.zone.name }} ({{ zc.zone.zone_type }})</q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-badge color="primary" :label="`${zc.count} device${zc.count !== 1 ? 's' : ''}`" />
            </q-item-section>
          </q-item>
        </q-list>
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
  product: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue'])

const { t } = useI18n()
const store = useInventoryStore()

const drillDownFocusId = ref(null)

function onDrillDown(treeNode) {
  drillDownFocusId.value = treeNode?.id ?? null
}

function onDrillUp(treeNode) {
  drillDownFocusId.value = treeNode?.id ?? null
}

watch(() => props.modelValue, (open) => {
  if (open) drillDownFocusId.value = null
})

const zoneDeviceCounts = computed(() => {
  if (!props.product) return []
  const devices = store.devices.filter(d => d.product_id === props.product.id && d.location_zone_id)
  const counts = {}
  for (const d of devices) {
    const zid = d.location_zone_id
    counts[zid] = (counts[zid] || 0) + 1
  }
  return Object.entries(counts)
    .map(([zid, count]) => {
      const zone = store.zones.find(z => z.id === Number(zid))
      if (!zone) return null
      const parts = []
      let current = zone
      while (current) {
        parts.unshift(current.name || '')
        current = store.zones.find(z => z.id === current.parent_id)
      }
      return { zone, count, path: parts.join(' / ') }
    })
    .filter(Boolean)
    .sort((a, b) => a.path.localeCompare(b.path))
})

const highlightZoneIds = computed(() => {
  const ids = new Set()
  for (const zc of zoneDeviceCounts.value) {
    ids.add(zc.zone.id)
    let current = zc.zone
    while (current?.parent_id) {
      const parent = store.zones.find(z => z.id === current.parent_id)
      if (parent) {
        ids.add(parent.id)
        current = parent
      } else break
    }
  }
  return [...ids]
})
</script>
