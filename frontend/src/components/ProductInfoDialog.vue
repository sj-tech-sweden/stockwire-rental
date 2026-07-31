<template>
  <q-dialog :model-value="modelValue" :maximized="isPhone" @update:model-value="emit('update:modelValue', $event)">
    <q-card :style="isPhone ? 'width: 100vw; max-width: 100vw; height: 100vh' : 'min-width: 860px; max-width: 96vw'" class="ec-card">
      <q-card-section class="row items-start no-wrap">
        <q-img
          v-if="productImageUrl"
          :src="productImageUrl"
          style="width: 80px; height: 80px; border-radius: 8px"
          fit="cover"
          class="q-mr-md"
        >
          <template #error>
            <div class="absolute-full flex flex-center bg-grey-3">
              <q-icon name="broken_image" color="grey-6" size="24px" />
            </div>
          </template>
        </q-img>
        <q-avatar v-else color="grey-3" text-color="grey-6" size="80px" class="q-mr-md">
          <q-icon name="inventory_2" size="36px" />
        </q-avatar>
        <div>
          <div class="text-h6">{{ t('inventory.infoDialogs.productTitle', { sku: product?.sku || '-' }) }}</div>
          <div class="text-caption text-grey-7">{{ product?.name || '-' }}</div>
        </div>
        <q-space />
        <q-btn
          v-if="isPhone"
          flat
          round
          dense
          icon="close"
          :aria-label="t('app.actions.close')"
          @click="emit('update:modelValue', false)"
        />
      </q-card-section>

      <q-card-section class="q-pt-none" :style="isPhone ? 'max-height: calc(100vh - 140px); overflow: auto;' : ''">
        <div class="row q-col-gutter-sm q-mb-md">
          <div class="col-12 col-md-4"><q-badge color="positive" text-color="white" :label="t('inventory.infoDialogs.available', { count: availability.available })" /></div>
          <div class="col-12 col-md-4"><q-badge color="warning" text-color="black" :label="t('inventory.infoDialogs.reserved', { count: availability.reserved })" /></div>
          <div class="col-12 col-md-4"><q-badge color="info" text-color="white" :label="t('inventory.infoDialogs.inUse', { count: availability.in_use })" /></div>
        </div>

        <q-list bordered separator class="rounded-borders q-mb-md">
          <q-item>
            <q-item-section>
              <q-item-label>Type: {{ translateProductType(product?.product_type, t) }}</q-item-label>
              <q-item-label caption>
                {{ t('inventory.infoDialogs.categoryBrandManufacturer', { category: translateCategory(product?.category, t), brand: product?.brand || '-', manufacturer: product?.manufacturer || '-' }) }}
              </q-item-label>
              <q-item-label caption>
                {{
                  t('inventory.infoDialogs.dailyRateMaintenanceInterval', {
                    dailyRate: formatMoney(product?.daily_rate),
                    days: product?.maintenance_interval_days ?? '-'
                  })
                }}
              </q-item-label>
              <q-item-label caption>
                {{ t('inventory.infoDialogs.replaceCost', {
                  replaceCost: formatMoney(product?.replace_cost)
                }) }}
              </q-item-label>
              <q-item-label caption>
                {{ t('inventory.infoDialogs.weightSize', { weight: product?.weight_kg ?? '-', height: product?.height_cm ?? '-', width: product?.width_cm ?? '-', depth: product?.depth_cm ?? '-' }) }}
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
                :aria-label="isPhone ? 'Edit product' : void 0"
                @click="emit('edit-product')"
              />
            </q-item-section>
          </q-item>
        </q-list>

        <div v-if="product?.suppliers?.length" class="text-subtitle2 q-mb-sm">Suppliers</div>
        <q-list v-if="product?.suppliers?.length" bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="sup in product.suppliers" :key="`sup-${sup.id}`">
            <q-item-section>
              <q-item-label>{{ supplierNameById(sup.supplier_id) }}</q-item-label>
              <q-item-label caption>
                {{ sup.is_primary ? 'Primary' : 'Secondary' }}
                <span v-if="sup.lead_time_days"> · {{ sup.lead_time_days }} days lead time</span>
                <span v-if="sup.unit_cost"> · {{ formatMoney(sup.unit_cost) }}</span>
              </q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <div v-if="product?.product_type === 'consumable' && (product?.min_stock_level != null || product?.min_order_qty != null)" class="text-subtitle2 q-mb-sm">Reorder Info</div>
        <q-list v-if="product?.product_type === 'consumable' && (product?.min_stock_level != null || product?.min_order_qty != null)" bordered separator class="rounded-borders q-mb-md">
          <q-item>
            <q-item-section>
              <q-item-label caption>
                Min stock level: {{ product?.min_stock_level ?? '-' }} · Min order qty: {{ product?.min_order_qty ?? '-' }}
              </q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <div v-if="productDeviceZoneIds.length" class="q-mb-md">
          <q-expansion-item
            v-model="mapExpanded"
            :label="t('inventory.infoDialogs.deviceLocations') || 'Device Locations'"
            header-class="text-subtitle2"
            @after-show="fitMapToView"
          >
            <div style="height: 320px; border: 1px solid rgba(128,128,128,0.2); border-radius: 4px; overflow: hidden">
              <WarehouseMap
                ref="warehouseMapRef"
                :zones="store.zones"
                :zone-tree="store.zoneTree"
                :devices="store.devices"
                :highlight-zone-ids="productDeviceZoneIds"
                :focus-zone-id="drillDownFocusId"
                :breadcrumb="currentBreadcrumb"
                @drill-down="onDrillDown"
                @drill-up="onDrillUp"
              />
            </div>
          </q-expansion-item>
        </div>

        <div class="text-subtitle2 q-mb-sm row items-center">
          <span class="col">{{ t('inventory.infoDialogs.linkedDevices') }}</span>
          <q-btn
            v-if="linkedDevices.length"
            flat dense color="orange" icon="lightbulb" size="sm"
            :label="t('warehouseLeds.actions.locateAll')"
            @click="locateAllDevicesLed"
          />
        </div>
        <q-list bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="row in linkedDevices" :key="row.id">
            <q-item-section>
              <q-item-label>{{ row.asset_tag }}</q-item-label>
              <q-item-label caption>
                {{ t('inventory.infoDialogs.deviceStatusConditionLocation', {
                  status: row.status,
                  condition: row.condition || t('inventory.infoDialogs.notAvailable'),
                  location: getEffectiveDeviceLocation(row),
                }) }}
              </q-item-label>
            </q-item-section>
            <q-item-section side top>
              <div class="row no-wrap items-center q-gutter-xs">
                <q-btn v-if="getEffectiveDeviceZoneId(row)" flat dense round color="primary" icon="place" size="sm" @click="openDeviceLocate(row)">
                  <q-tooltip>{{ t('inventory.deviceDialog.locateOnMap') }}</q-tooltip>
                </q-btn>
                <q-btn v-if="getEffectiveDeviceZoneId(row)" flat dense round color="orange" icon="lightbulb" size="sm" @click="locateDeviceLed(row.id)">
                  <q-tooltip>{{ t('warehouseLeds.actions.locate') }}</q-tooltip>
                </q-btn>
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
          <q-item v-if="!linkedDevices.length">
            <q-item-section><q-item-label caption>{{ t('inventory.infoDialogs.noDevicesLinkedToProduct') }}</q-item-label></q-item-section>
          </q-item>
        </q-list>

        <div class="text-subtitle2 q-mb-sm">{{ t('inventory.infoDialogs.linkedJobs') }}</div>
        <q-list bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="row in linkedJobs" :key="`product-job-${row.job_id}`">
            <q-item-section>
              <q-item-label>{{ row.job_code || `Job #${row.job_id}` }}</q-item-label>
              <q-item-label caption>
                {{ t('inventory.infoDialogs.requiredPicked', { required: row.quantity_required_total, picked: row.quantity_picked_total }) }}
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
                :aria-label="isPhone ? 'Edit linked job' : void 0"
                @click="emit('open-job', row.job_id)"
              />
            </q-item-section>
          </q-item>
          <q-item v-if="!linkedJobs.length">
            <q-item-section><q-item-label caption>{{ t('inventory.infoDialogs.noLinkedJobsForProduct') }}</q-item-label></q-item-section>
          </q-item>
        </q-list>

        <div v-if="product?.accessories?.length" class="text-subtitle2 q-mb-sm">Accessories</div>
        <q-list v-if="product?.accessories?.length" bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="row in product.accessories" :key="`acc-${row.accessory_product_id}`">
            <q-item-section>
              <q-item-label>{{ productNameById(row.accessory_product_id) }}</q-item-label>
              <q-item-label caption>{{ row.required ? 'Required' : 'Optional' }} · Qty {{ row.quantity }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <div v-if="product?.components?.length" class="text-subtitle2 q-mb-sm">Components</div>
        <q-list v-if="product?.components?.length" bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="row in product.components" :key="`cmp-${row.component_product_id}`">
            <q-item-section>
              <q-item-label>{{ productNameById(row.component_product_id) }}</q-item-label>
              <q-item-label caption>Qty {{ row.quantity }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <div v-if="infoCustomFieldValues.length" class="text-subtitle2 q-mb-sm">Custom Fields</div>
        <q-list v-if="infoCustomFieldValues.length" bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="field in infoCustomFieldValues" :key="field.field_definition_id">
            <q-item-section>
              <q-item-label>{{ field.label }}</q-item-label>
              <q-item-label caption>{{ field.value ?? '-' }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <EntityAttachmentsPanel
          entity-type="product"
          :entity-id="product?.id || null"
          :title="t('inventory.infoDialogs.productDocuments')"
          default-category="product-document"
          :read-only="true"
        />
      </q-card-section>

      <q-card-actions :align="isPhone ? 'stretch' : 'right'" :class="isPhone ? 'q-pa-md bg-grey-2' : ''">
        <q-space />
        <q-btn flat :class="isPhone ? 'full-width' : ''" :label="t('app.actions.close')" @click="emit('update:modelValue', false)" />
      </q-card-actions>
    </q-card>
  </q-dialog>

  <LocateDeviceMapDialog
    v-model="deviceLocateOpen"
    :device="deviceLocateTarget"
  />
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useInventoryStore } from '../stores/inventory'
import { useJobsStore } from '../stores/jobs'
import { useCustomersStore } from '../stores/customers'
import { useSettingsStore } from '../stores/settings'
import { useCustomFieldsStore } from '../stores/customFields'
import { useWarehouseLedsStore } from '../stores/warehouseLeds'
import { normalizeCurrencyCode } from '../constants/currencies'
import { buildZonePath, getEffectiveZoneId, formatMoney } from '../utils/inventory-helpers'
import { translateProductType, translateCategory } from '../utils/translate-helpers'
import { useProductImage } from '../composables/useProductImage'
import EntityAttachmentsPanel from './EntityAttachmentsPanel.vue'
import LocateDeviceMapDialog from './LocateDeviceMapDialog.vue'
import WarehouseMap from './WarehouseMap.vue'

const props = defineProps({
  modelValue: Boolean,
  product: { type: Object, default: null },
})

const emit = defineEmits([
  'update:modelValue',
  'edit-product',
  'view-device',
  'edit-device',
  'open-job',
])

const $q = useQuasar()
const { t } = useI18n()
const store = useInventoryStore()
const jobsStore = useJobsStore()
const customersStore = useCustomersStore()
const settingsStore = useSettingsStore()
const customFieldsStore = useCustomFieldsStore()
const warehouseLedsStore = useWarehouseLedsStore()

const infoCustomFieldValues = ref([])
const { imageUrl: productImageUrl, fetchImage: fetchProductImage, cleanup: cleanupProductImage } = useProductImage()

const mapExpanded = ref(false)
const warehouseMapRef = ref(null)
const drillDownFocusId = ref(null)

function onDrillDown(treeNode) {
  drillDownFocusId.value = treeNode?.id ?? null
}

function onDrillUp(treeNode) {
  drillDownFocusId.value = treeNode?.id ?? null
}

const currentBreadcrumb = computed(() => {
  const focusId = drillDownFocusId.value
  if (!focusId) return []
  const parts = []
  let current = store.zones.find(z => z.id === focusId)
  while (current) {
    parts.unshift({ id: current.id, name: current.name || '' })
    current = store.zones.find(z => z.id === current.parent_id)
  }
  return parts
})

function fitMapToView() {
  setTimeout(() => {
    warehouseMapRef.value?.fitToView()
  }, 300)
}

const deviceLocateOpen = ref(false)
const deviceLocateTarget = ref(null)

function openDeviceLocate(row) {
  const zoneId = getEffectiveDeviceZoneId(row)
  deviceLocateTarget.value = { location_zone_id: zoneId, asset_tag: row.asset_tag, serial_number: row.serial_number, id: row.id }
  deviceLocateOpen.value = true
}

async function locateDeviceLed(deviceId) {
  try {
    const result = await warehouseLedsStore.locateDevice(deviceId)
    $q.notify({ type: 'positive', message: t('warehouseLeds.locateSuccess', { tag: result.asset_tag || '' }) })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
  }
}

async function locateAllDevicesLed() {
  if (!props.product?.id) return
  const devices = (store.devices || []).filter(d => d.product_id === props.product.id && d.location_zone_id)
  if (!devices.length) {
    $q.notify({ type: 'warning', message: t('warehouseLeds.noDevicesWithLocation') })
    return
  }
  let successCount = 0
  for (const device of devices) {
    try {
      await warehouseLedsStore.locateDevice(device.id)
      successCount++
    } catch { /* skip */ }
  }
  $q.notify({ type: 'positive', message: t('warehouseLeds.locateAllSuccess', { count: successCount }) })
}

watch(() => props.modelValue, async (open) => {
  if (open) {
    drillDownFocusId.value = null
    mapExpanded.value = false
    if (!customersStore.customers.length) {
      customersStore.fetchAll().catch(() => {})
    }
    if (props.product?.id) {
      if (!customFieldsStore.definitions.length) {
        await customFieldsStore.fetchDefinitions('product')
      }
      try {
        const data = await customFieldsStore.fetchEntityValues('product', props.product.id)
        infoCustomFieldValues.value = Array.isArray(data?.values) ? data.values : []
      } catch {
        infoCustomFieldValues.value = []
      }
    }
  }
})

const isPhone = computed(() => $q.screen.lt.md)
const infoActionColor = computed(() => ($q.dark.isActive ? 'teal-4' : 'secondary'))

const zoneById = computed(() => {
  const map = new Map()
  for (const zone of store.zones) map.set(zone.id, zone)
  return map
})

function zoneNameById(id) {
  if (!id) return null
  return zoneById.value.get(id)?.name ?? null
}

function zonePathById(id) {
  return buildZonePath(id, store.zones)
}

function getEffectiveDeviceZoneId(device) {
  return getEffectiveZoneId(device, store.devices)
}

function getEffectiveDeviceLocation(device) {
  const zoneId = getEffectiveDeviceZoneId(device)
  if (zoneId) return zonePathById(zoneId)
  if (device.case_asset_tag) return t('inventory.infoDialogs.caseLocation', { assetTag: device.case_asset_tag })
  return t('inventory.infoDialogs.unassigned')
}

function formatMoneyLocal(value) {
  const currency = normalizeCurrencyCode(settingsStore.companyProfile?.currency, 'SEK')
  return formatMoney(value, currency)
}

const productDeviceZoneIds = computed(() => {
  if (!props.product?.id) return []
  const devices = (store.devices || []).filter(d => d.product_id === props.product.id && d.location_zone_id)
  const ids = new Set()
  for (const d of devices) {
    ids.add(d.location_zone_id)
    let current = store.zones.find(z => z.id === d.location_zone_id)
    while (current?.parent_id) {
      ids.add(current.parent_id)
      current = store.zones.find(z => z.id === current.parent_id)
    }
  }
  return [...ids]
})

const linkedDevices = computed(() => {
  if (!props.product?.id) return []
  return (store.devices || [])
    .filter(item => item.product_id === props.product.id)
    .slice()
    .sort((a, b) => String(a.asset_tag || '').localeCompare(String(b.asset_tag || '')))
})

const availability = computed(() => {
  const bucket = { available: 0, reserved: 0, in_use: 0, maintenance: 0 }
  for (const row of linkedDevices.value) {
    const status = String(row.status || '').toLowerCase()
    if (status === 'available') bucket.available += 1
    else if (status === 'reserved') bucket.reserved += 1
    else if (status === 'in_use') bucket.in_use += 1
    else if (status === 'maintenance') bucket.maintenance += 1
  }
  return bucket
})

function linkedJobsForProductId(productId) {
  const targetId = Number(productId || 0)
  if (!targetId) return []

  const jobsById = new Map((jobsStore.jobs || []).map(job => [job.id, job]))
  const bucket = new Map()

  for (const requirement of jobsStore.requirements || []) {
    if (Number(requirement?.product_id || 0) !== targetId) continue
    const jobId = Number(requirement?.job_id || 0)
    if (!jobId) continue

    const existing = bucket.get(jobId) || {
      job_id: jobId,
      job_code: jobsById.get(jobId)?.job_code || null,
      quantity_required_total: 0,
      quantity_picked_total: 0,
      start_date: jobsById.get(jobId)?.start_date || null,
      end_date: jobsById.get(jobId)?.end_date || null,
      status: jobsById.get(jobId)?.status || null,
    }

    existing.quantity_required_total += Math.max(Number(requirement?.quantity_required || 0), 0)
    existing.quantity_picked_total += Math.max(Number(requirement?.quantity_picked || 0), 0)
    bucket.set(jobId, existing)
  }

  return [...bucket.values()].sort((a, b) => {
    const startA = String(a.start_date || '')
    const startB = String(b.start_date || '')
    return startB.localeCompare(startA)
  })
}

const linkedJobs = computed(() => linkedJobsForProductId(props.product?.id))

function productNameById(productId) {
  const item = store.products.find(row => row.id === productId)
  if (!item) return `Product #${productId}`
  return `${item.sku} - ${item.name}`
}

function supplierNameById(supplierId) {
  const supplier = customersStore.customers.find(c => c.id === supplierId)
  return supplier?.name || `Supplier #${supplierId}`
}

watch(() => props.modelValue, (open) => {
  if (open) {
    fetchProductImage(props.product?.id)
  } else {
    cleanupProductImage()
  }
})
</script>
