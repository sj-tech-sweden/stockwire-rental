<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="$emit('update:modelValue', $event)">
    <q-card style="width: 840px; max-width: 98vw" class="ec-card">
      <q-card-section>
        <div class="text-h6">Import Data</div>
      </q-card-section>
      <q-card-section class="q-pt-none">
        <div class="row q-col-gutter-sm q-mb-sm">
          <div class="col-12 col-md-4">
            <q-select
              v-model="importEntityType"
              :options="importEntityOptions"
              label="Import to"
              outlined
              dense
              emit-value
              map-options
              @update:model-value="onImportEntityChanged"
            />
          </div>
          <div class="col-12 col-md-8">
            <q-file
              v-model="importFile"
              label="JSON or CSV file"
              outlined
              dense
              accept=".json,.csv,application/json,text/csv"
              @update:model-value="parseImportFile"
            />
          </div>
        </div>

        <q-banner v-if="importDialogError" class="bg-negative text-white q-mb-sm rounded-borders" dense>
          {{ importDialogError }}
        </q-banner>

        <div v-if="importRows.length" class="q-mb-sm text-caption text-grey-7">
          Parsed {{ importRows.length }} records. Map Stockwire fields to source fields below.
        </div>

        <q-table
          :rows="mappingRows"
          :columns="mappingColumns"
          row-key="targetField"
          flat
          bordered
          dense
          class="q-mb-sm"
        >
          <template #body-cell-sourceKey="props">
            <q-td :props="props">
              <q-select
                v-model="importMapping[props.row.targetField]"
                :options="importSourceKeyOptions"
                outlined
                dense
                clearable
                emit-value
                map-options
              />
            </q-td>
          </template>
          <template #body-cell-required="props">
            <q-td :props="props">
              <q-badge :label="props.row.required ? 'Required' : 'Optional'" :color="props.row.required ? 'negative' : 'grey'" />
            </q-td>
          </template>
        </q-table>

        <div class="q-mb-sm row items-center q-gutter-sm">
          <div class="col-auto">
            <q-btn size="sm" flat label="Load HireHop preset" @click="loadHirehopPreset" />
          </div>
          <div class="col-auto">
            <q-toggle dense v-model="importUseServer" label="Use server import" />
          </div>
          <div class="col-auto">
            <q-toggle dense v-model="updateExistingDevices" label="Update existing devices" />
          </div>
        </div>

        <div class="text-caption text-grey-7 q-mb-md">
          HireHop imports require server import for serial numbers, barcodes, quantity expansion, and device metadata. This is enabled automatically when a HireHop file or preset is detected.
        </div>

        <div v-if="importPreviewRows.length" class="q-mt-md">
          <div class="text-subtitle2 q-mb-xs">Preview (first 10 transformed rows)</div>
          <q-table
            :rows="importPreviewRows"
            :columns="importPreviewColumns"
            row-key="_preview_id"
            flat
            bordered
            dense
          >
            <template #body-cell-_status="props">
              <q-td :props="props">
                <q-badge
                  :label="props.row._error ? 'Invalid' : 'Valid'"
                  :color="props.row._error ? 'negative' : 'positive'"
                />
                <div v-if="props.row._error" class="text-caption text-negative q-mt-xs">{{ props.row._error }}</div>
              </q-td>
            </template>
          </q-table>
        </div>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat label="Cancel" @click="$emit('update:modelValue', false)" />
        <q-btn color="primary" unelevated label="Run Import" :loading="importing" @click="runJsonImport" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useInventoryStore } from 'src/stores/inventory'
import { useSettingsStore } from 'src/stores/settings'
import { api } from 'src/boot/axios'
import { collectImportSourceKeys, convertDimensionValueToCm, getImportValueBySourceKey, parseImportRows, resolveImportEntityType } from 'src/utils/import-data'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const $q = useQuasar()
const { t } = useI18n()
const store = useInventoryStore()
const settingsStore = useSettingsStore()

const importing = ref(false)
const importDialogError = ref('')
const importEntityType = ref('product')
const importFile = ref(null)
const importRows = ref([])
const importSourceKeys = ref([])
const importMapping = ref({})
const importUseServer = ref(false)
const updateExistingDevices = ref(false)

watch(() => props.modelValue, (open) => {
  if (open) {
    importEntityType.value = 'product'
    importDialogError.value = ''
    importRows.value = []
    importSourceKeys.value = []
    importFile.value = null
    importUseServer.value = false
    updateExistingDevices.value = false
    resetImportMapping()
  }
})

const importEntityOptions = [
  { label: 'Products', value: 'product' },
  { label: 'Devices', value: 'device' },
  { label: 'Products + Devices', value: 'mixed' },
  { label: 'Locations', value: 'location' },
]

const importFieldConfigs = {
  product: [
    { targetField: 'sku', label: 'SKU', required: true },
    { targetField: 'name', label: 'Name', required: true },
    { targetField: 'brand', label: 'Brand', required: false },
    { targetField: 'manufacturer', label: 'Manufacturer', required: false },
    { targetField: 'product_type', label: 'Product Type', required: false },
    { targetField: 'category_id', label: 'Category (id/name)', required: false },
    { targetField: 'daily_rate', label: 'Daily Rate', required: false },
    { targetField: 'replace_cost', label: 'Replacement Cost', required: false },
    { targetField: 'weight_kg', label: 'Weight (kg)', required: false },
    { targetField: 'height_cm', label: 'Height (cm)', required: false },
    { targetField: 'width_cm', label: 'Width (cm)', required: false },
    { targetField: 'depth_cm', label: 'Depth (cm)', required: false },
    { targetField: 'maintenance_interval_days', label: 'Maintenance Interval Days', required: false },
    { targetField: 'power_consumption_watts', label: 'Power Consumption Watts', required: false },
  ],
  device: [
    { targetField: 'product_id', label: 'Product (id/sku/name)', required: true },
    { targetField: 'asset_tag', label: 'Asset Tag', required: true },
    { targetField: 'serial_number', label: 'Serial Number', required: false },
    { targetField: 'barcode', label: 'Barcode', required: false },
    { targetField: 'qr_code', label: 'QR Code', required: false },
    { targetField: 'rfid', label: 'RFID', required: false },
    { targetField: 'location_zone_id', label: 'Location (id/code/name)', required: false },
    { targetField: 'status', label: 'Status', required: false },
    { targetField: 'condition', label: 'Condition', required: false },
    { targetField: 'purchase_date', label: 'Purchase Date', required: false },
    { targetField: 'purchase_price', label: 'Purchase Price', required: false },
    { targetField: 'purchased_from', label: 'Purchased From', required: false },
    { targetField: 'sold_price', label: 'Sold Price', required: false },
    { targetField: 'finance_upto', label: 'Finance Up To', required: false },
    { targetField: 'finance_company', label: 'Finance Company', required: false },
    { targetField: 'finance_ref', label: 'Finance Reference', required: false },
    { targetField: 'pre_prep', label: 'Pre-prep', required: false },
    { targetField: 'warranty_end_date', label: 'Warranty End Date', required: false },
    { targetField: 'retire_date', label: 'Retire Date', required: false },
    { targetField: 'usage_hours', label: 'Usage Hours', required: false },
    { targetField: 'notes', label: 'Notes', required: false },
  ],
  mixed: [
    { targetField: 'entity_type', label: 'Entity Type (product/device)', required: false },
    { targetField: 'sku', label: 'SKU', required: false },
    { targetField: 'name', label: 'Name', required: false },
    { targetField: 'brand', label: 'Brand', required: false },
    { targetField: 'manufacturer', label: 'Manufacturer', required: false },
    { targetField: 'supplier_name', label: 'Supplier', required: false },
    { targetField: 'daily_rate', label: 'Daily Rate', required: false },
    { targetField: 'product_type', label: 'Product Type', required: false },
    { targetField: 'category_id', label: 'Category (id/name)', required: false },
    { targetField: 'weight_kg', label: 'Weight (kg)', required: false },
    { targetField: 'height_cm', label: 'Height (cm)', required: false },
    { targetField: 'width_cm', label: 'Width (cm)', required: false },
    { targetField: 'depth_cm', label: 'Depth (cm)', required: false },
    { targetField: 'maintenance_interval_days', label: 'Maintenance Interval Days', required: false },
    { targetField: 'power_consumption_watts', label: 'Power Consumption Watts', required: false },
    { targetField: 'replace_cost', label: 'Replacement Cost', required: false },
    { targetField: 'product_id', label: 'Product (id/sku/name)', required: false },
    { targetField: 'asset_tag', label: 'Asset Tag', required: false },
    { targetField: 'serial_number', label: 'Serial Number', required: false },
    { targetField: 'barcode', label: 'Barcode', required: false },
    { targetField: 'qr_code', label: 'QR Code', required: false },
    { targetField: 'rfid', label: 'RFID', required: false },
    { targetField: 'location_zone_id', label: 'Location (id/code/name)', required: false },
    { targetField: 'status', label: 'Status', required: false },
    { targetField: 'condition', label: 'Condition', required: false },
    { targetField: 'purchase_date', label: 'Purchase Date', required: false },
    { targetField: 'purchase_price', label: 'Purchase Price', required: false },
    { targetField: 'purchased_from', label: 'Purchased From', required: false },
    { targetField: 'sold_price', label: 'Sold Price', required: false },
    { targetField: 'finance_upto', label: 'Finance Up To', required: false },
    { targetField: 'finance_company', label: 'Finance Company', required: false },
    { targetField: 'finance_ref', label: 'Finance Reference', required: false },
    { targetField: 'pre_prep', label: 'Pre-prep', required: false },
    { targetField: 'warranty_end_date', label: 'Warranty End Date', required: false },
    { targetField: 'retire_date', label: 'Retire Date', required: false },
    { targetField: 'usage_hours', label: 'Usage Hours', required: false },
    { targetField: 'notes', label: 'Notes', required: false },
  ],
  location: [
    { targetField: 'code', label: 'Code', required: true },
    { targetField: 'name', label: 'Name', required: true },
    { targetField: 'zone_type', label: 'Location Type', required: false },
    { targetField: 'parent_id', label: 'Parent (id/code/name)', required: false },
    { targetField: 'sort_order', label: 'Sort Order', required: false },
    { targetField: 'is_active', label: 'Is Active', required: false },
  ],
}

const mappingColumns = [
  { name: 'label', label: 'Stockwire Field', field: 'label', align: 'left' },
  { name: 'sourceKey', label: 'Source Field', field: 'sourceKey', align: 'left' },
  { name: 'required', label: 'Required', field: 'required', align: 'left' },
]

const mappingRows = computed(() => importFieldConfigs[importEntityType.value] || [])
const importSourceKeyOptions = computed(() => importSourceKeys.value.map(key => ({ label: key, value: key })))

const locationTypeOptions = computed(() => {
  const values = Array.isArray(store.locationTypes) && store.locationTypes.length
    ? store.locationTypes
    : ['rack', 'shelf', 'bin', 'pallet', 'stage', 'truck', 'warehouse', 'workshop']
  return values.map(value => ({ label: value, value }))
})

const importPreviewRows = computed(() => {
  return (importRows.value || []).slice(0, 10).map((rawRow, idx) => {
    const rowEntityType = resolveRowEntityType(rawRow)
    const payload = normalizeImportPayload(rawRow, rowEntityType)
    const error = validateImportPayload(payload, rowEntityType)
    return {
      _preview_id: idx + 1,
      _index: idx + 1,
      _entity_type: rowEntityType,
      _status: error ? 'invalid' : 'valid',
      _error: error,
      ...payload,
    }
  })
})

const importPreviewColumns = computed(() => {
  const cols = [
    { name: '_index', label: '#', field: '_index', align: 'left' },
    { name: '_status', label: 'Status', field: '_status', align: 'left' },
  ]
  if (importEntityType.value === 'mixed') {
    cols.push({
      name: '_entity_type',
      label: 'Entity Type',
      field: row => formatPreviewValue(row._entity_type),
      align: 'left',
    })
  }
  for (const field of mappingRows.value) {
    if (field.targetField === 'entity_type') continue
    cols.push({
      name: field.targetField,
      label: field.label,
      field: row => formatPreviewValue(row[field.targetField]),
      align: 'left',
    })
  }
  return cols
})

function onImportEntityChanged() {
  resetImportMapping()
}

function resetImportMapping() {
  const map = {}
  for (const field of importFieldConfigs[importEntityType.value] || []) {
    map[field.targetField] = field.targetField
  }
  importMapping.value = map
}

function isLikelyHirehopRows(rows) {
  if (!Array.isArray(rows)) return false
  return rows.some(row =>
    Array.isArray(row?.serialnumbers) ||
    (row?.ID !== undefined && (row?.TITLE !== undefined || row?.REPLACE_COST !== undefined || row?.serialnumbers !== undefined))
  )
}

async function loadHirehopPreset() {
  const fallbackProductPreset = {
    sku: 'ID',
    name: 'TITLE',
    title: 'TITLE',
    description: 'DESCRIPTION',
    brand: 'fields.tillverkare.value',
    manufacturer: 'fields.tillverkare.value',
    replace_cost: 'REPLACE_COST',
    weight: 'WEIGHT',
    category_id: 'CATEGORY_ID',
    barcode: 'BARCODE',
    height_cm: 'HEIGHT',
    width_cm: 'WIDTH',
    depth_cm: 'LENGTH',
  }

  let preset = {}
  try {
    const res = await api.get('/api/v1/inventory/import/presets/hirehop')
    preset = res.data || {}
  } catch (err) {
    preset = {}
  }

  importEntityType.value = 'product'
  importUseServer.value = true
  resetImportMapping()

  const p = { ...fallbackProductPreset, ...(preset.product || {}) }
  const map = { ...importMapping.value }

  map['sku'] = p.sku || p.external_id || 'ID'
  map['name'] = p.name || p.title || 'TITLE'
  map['brand'] = p.brand || 'fields.tillverkare.value'
  map['manufacturer'] = p.manufacturer || 'fields.tillverkare.value'
  map['description'] = p.description || 'DESCRIPTION'
  map['weight_kg'] = p.weight || 'WEIGHT'
  map['category_id'] = p.category_id || 'CATEGORY_ID'
  map['replace_cost'] = p.replace_cost || 'REPLACE_COST'
  map['daily_rate'] = p.daily_rate || 'PRICE1'
  map['rental_price'] = p.rental_price || 'PRICE2'
  map['barcode'] = p.barcode || 'BARCODE'
  map['height_cm'] = p.height_cm || 'HEIGHT'
  map['width_cm'] = p.width_cm || 'WIDTH'
  map['depth_cm'] = p.depth_cm || 'LENGTH'

  importMapping.value = map
  importSourceKeys.value = [
    'ID', 'TITLE', 'DESCRIPTION', 'BARCODE', 'REPLACE_COST', 'WEIGHT', 'CATEGORY_ID',
    'fields.tillverkare.value',
    'HEIGHT', 'WIDTH', 'LENGTH',
    'PRICE1', 'PRICE2', 'STATUS', 'LOCATION', 'MEMO', 'PART_NUMBER',
  ]

  if (preset.product) {
    $q.notify({ type: 'positive', message: 'HireHop preset loaded' })
  } else {
    $q.notify({ type: 'warning', message: 'HireHop preset endpoint unavailable; loaded built-in preset' })
  }
}

async function parseImportFile(file) {
  importDialogError.value = ''
  importRows.value = []
  importSourceKeys.value = []
  if (!file) return

  try {
    const text = await file.text()
    const rows = parseImportRows(text, file?.name || '')
    if (isLikelyHirehopRows(rows)) {
      importUseServer.value = true
    }
    const detectedTypes = Array.from(new Set(rows.slice(0, 100).map(row => resolveImportEntityType(row)).filter(Boolean)))
    if (detectedTypes.length > 1 && detectedTypes.includes('product') && detectedTypes.includes('device')) {
      importEntityType.value = 'mixed'
      const isDefaultMap = Object.keys(importMapping.value || {}).length > 0 && Object.entries(importMapping.value).every(([k, v]) => v === k)
      if (isDefaultMap) resetImportMapping()
    }
    importRows.value = rows
    importSourceKeys.value = collectImportSourceKeys(rows)
    const map = { ...importMapping.value }
    for (const field of importFieldConfigs[importEntityType.value] || []) {
      const currentVal = map[field.targetField]
      if (!currentVal || currentVal === field.targetField) {
        map[field.targetField] = importSourceKeys.value.includes(field.targetField) ? field.targetField : null
      }
    }
    importMapping.value = map
  } catch (error) {
    importDialogError.value = error?.message || 'Invalid import file'
  }
}

function toBoolean(value) {
  if (typeof value === 'boolean') return value
  const normalized = String(value || '').trim().toLowerCase()
  return ['1', 'true', 'yes', 'y'].includes(normalized)
}

function resolveCategoryId(value) {
  if (value === null || value === undefined || value === '') return null
  if (typeof value === 'number') return value
  const asNumber = Number(value)
  if (!Number.isNaN(asNumber)) return asNumber
  const needle = String(value).trim().toLowerCase()
  const byName = store.categories.find(item => String(item.name || '').toLowerCase() === needle)
  return byName?.id ?? null
}

function resolveProductId(value) {
  if (value === null || value === undefined || value === '') return null
  if (typeof value === 'number') return value
  const asNumber = Number(value)
  if (!Number.isNaN(asNumber)) return asNumber
  const needle = String(value).trim().toLowerCase()
  const bySku = store.products.find(item => String(item.sku || '').toLowerCase() === needle)
  if (bySku) return bySku.id
  const byName = store.products.find(item => String(item.name || '').toLowerCase() === needle)
  return byName?.id ?? null
}

function resolveZoneId(value) {
  if (value === null || value === undefined || value === '') return null
  if (typeof value === 'number') return value
  const asNumber = Number(value)
  if (!Number.isNaN(asNumber)) return asNumber
  const needle = String(value).trim().toLowerCase()
  const byCode = store.zones.find(item => String(item.code || '').toLowerCase() === needle)
  if (byCode) return byCode.id
  const byName = store.zones.find(item => String(item.name || '').toLowerCase() === needle)
  return byName?.id ?? null
}

function resolveRowEntityType(rawRow) {
  if (importEntityType.value !== 'mixed') return importEntityType.value
  if (rawRow && (Array.isArray(rawRow.serialnumbers) || Array.isArray(getImportValueBySourceKey(rawRow, 'serialnumbers')))) return 'product'

  const entityTypeSourceKey = importMapping.value.entity_type
  const mappedEntityValue = entityTypeSourceKey ? getImportValueBySourceKey(rawRow, entityTypeSourceKey) : undefined
  const resolved = resolveImportEntityType({ ...rawRow, entity_type: mappedEntityValue }, null)
  if (['product', 'device'].includes(resolved)) return resolved
  return null
}

function normalizeImportPayload(rawRow, rowEntityType = resolveRowEntityType(rawRow)) {
  const payload = {}
  const fields = importFieldConfigs[rowEntityType] || []
  for (const field of fields) {
    const sourceKey = importMapping.value[field.targetField]
    if (!sourceKey) continue
    const rawValue = getImportValueBySourceKey(rawRow, sourceKey)
    if (['height_cm', 'width_cm', 'depth_cm'].includes(field.targetField)) {
      payload[field.targetField] = convertDimensionValueToCm(rawValue, sourceKey)
    } else {
      payload[field.targetField] = rawValue
    }
  }

  if (rowEntityType === 'product') {
    payload.category_id = resolveCategoryId(payload.category_id)
    if (!payload.product_type) payload.product_type = 'equipment'
  }
  if (rowEntityType === 'device') {
    payload.product_id = resolveProductId(payload.product_id)
    payload.location_zone_id = resolveZoneId(payload.location_zone_id)
    if (!payload.status) payload.status = 'available'
    if (!payload.condition) payload.condition = 'good'
  }
  if (rowEntityType === 'location') {
    payload.parent_id = resolveZoneId(payload.parent_id)
    if (!payload.zone_type) payload.zone_type = locationTypeOptions.value[0]?.value || 'rack'
    if (payload.sort_order === '' || payload.sort_order === undefined || payload.sort_order === null) payload.sort_order = 0
    payload.is_active = payload.is_active === undefined ? true : toBoolean(payload.is_active)
  }

  return payload
}

function validateImportPayload(payload, rowEntityType) {
  if (!rowEntityType) {
    if (importEntityType.value === 'mixed') return 'Entity Type must be product or device'
    return 'Entity type is invalid'
  }
  const required = (importFieldConfigs[rowEntityType] || []).filter(field => field.required)
  for (const field of required) {
    const value = payload[field.targetField]
    if (value === undefined || value === null || value === '') {
      return `${field.label} is required`
    }
  }
  return null
}

function formatPreviewValue(value) {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

async function runJsonImport() {
  if (!importRows.value.length) {
    importDialogError.value = 'Load a JSON or CSV file first'
    return
  }

  importing.value = true
  importDialogError.value = ''

  if (importUseServer.value) {
    if (!importFile.value) {
      importDialogError.value = 'No file selected for server import'
      importing.value = false
      return
    }
    if (!isLikelyHirehopRows(importRows.value)) {
      importDialogError.value = 'Server import is only supported for HireHop JSON files. Disable "Use server import" to import other file types.'
      importing.value = false
      return
    }
    try {
      const fd = new FormData()
      fd.append('file', importFile.value)
      const res = await api.post('/api/v1/inventory/import', fd, { params: { preset: 'hirehop', dry_run: false, update_existing: updateExistingDevices.value } })
      importDialogError.value = ''
      importing.value = false
      const createdProducts = res.data.created_products || 0
      const createdDevices = res.data.created_devices || 0
      const updatedDevices = res.data.updated_devices || 0
      $q.notify({ type: 'positive', message: `Import completed. Created products: ${createdProducts}, created devices: ${createdDevices}, updated devices: ${updatedDevices}` })
      emit('saved')
      emit('update:modelValue', false)
      return
    } catch (err) {
      importDialogError.value = err?.response?.data?.detail || err?.message || 'Server import failed'
      importing.value = false
      return
    }
  }

  let created = 0
  let skipped = 0
  let unknownEntityTypeCount = 0
  let validationFailureCount = 0
  let apiFailureCount = 0

  try {
    const allowedEntityTypes = importEntityType.value === 'mixed'
      ? ['product', 'device']
      : ['product', 'device', 'location']
    for (const row of importRows.value) {
      const rowEntityType = resolveRowEntityType(row)
      if (!allowedEntityTypes.includes(rowEntityType)) {
        skipped += 1
        unknownEntityTypeCount += 1
        continue
      }

      const payload = normalizeImportPayload(row, rowEntityType)
      const validationError = validateImportPayload(payload, rowEntityType)
      if (validationError) {
        skipped += 1
        validationFailureCount += 1
        continue
      }

      try {
        if (rowEntityType === 'product') {
          await store.createProduct(payload)
        } else if (rowEntityType === 'device') {
          await store.createDevice(payload)
        } else {
          await store.createZone(payload)
        }
        created += 1
      } catch {
        skipped += 1
        apiFailureCount += 1
      }
    }

    importDialogError.value = ''
    importing.value = false
    const skipDetails = []
    if (unknownEntityTypeCount > 0) skipDetails.push(`${unknownEntityTypeCount} unsupported entity type`)
    if (validationFailureCount > 0) skipDetails.push(`${validationFailureCount} validation error`)
    if (apiFailureCount > 0) skipDetails.push(`${apiFailureCount} API error`)
    const skipSuffix = skipDetails.length ? ` (${skipDetails.join(', ')})` : ''
    $q.notify({ type: created > 0 ? 'positive' : 'warning', message: `Import completed. Created: ${created}, skipped: ${skipped}${skipSuffix}` })
    emit('saved')
    emit('update:modelValue', false)
  } finally {
    importing.value = false
  }
}
</script>
