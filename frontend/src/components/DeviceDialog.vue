<template>
  <q-dialog :model-value="modelValue" persistent :maximized="isPhone" @update:model-value="emit('update:modelValue', $event)">
    <q-card :style="isPhone ? 'width: 100vw; max-width: 100vw; height: 100vh' : 'min-width: 820px; max-width: 95vw'" class="ec-card">
      <q-card-section><div class="text-h6">{{ t(deviceEditing ? 'inventory.deviceDialog.edit' : 'inventory.deviceDialog.new') }}</div></q-card-section>
      <q-card-section class="q-pt-none" :style="isPhone ? 'max-height: calc(100vh - 140px); overflow: auto;' : ''">
        <q-form ref="deviceFormRef" @submit.prevent="saveDevice">
          <div class="row q-col-gutter-sm">
            <div class="col-12 col-md-6">
              <q-select v-model="deviceForm.product_id" :options="productOptions" :label="t('inventory.deviceDialog.product')" outlined dense emit-value map-options :rules="[v => !!v || t('inventory.deviceDialog.required')]" />
            </div>
            <div class="col-12 col-md-3">
              <q-input ref="deviceAssetTagInputRef" v-model="deviceForm.asset_tag" :label="t('inventory.deviceDialog.assetTag')" outlined dense :rules="[v => !!v || t('inventory.deviceDialog.required')]">
                <template #append>
                  <q-btn flat dense no-caps color="primary" icon="autorenew" :label="t('inventory.deviceDialog.generate')" :loading="generatingDeviceAssetTag" @click="generateDeviceAssetTag" />
                  <q-btn flat dense round color="positive" icon="qr_code_scanner" @click="openDeviceFieldCapture('asset_tag', t('inventory.deviceDialog.assetTag'))">
                    <q-tooltip>{{ t('inventory.deviceDialog.openScanOptions') }}</q-tooltip>
                  </q-btn>
                </template>
              </q-input>
            </div>
            <div class="col-12 col-md-2">
              <q-input v-model="deviceAssetTagPrefix" :label="t('inventory.deviceDialog.tagPrefix')" outlined dense hint="t.ex. LGT" />
            </div>
            <div class="col-12 col-md-3">
              <q-input ref="deviceSerialInputRef" v-model="deviceForm.serial_number" :label="t('inventory.deviceDialog.serialNumber')" outlined dense>
                <template #append>
                  <q-btn flat dense round color="positive" icon="qr_code_scanner" @click="openDeviceFieldCapture('serial_number', t('inventory.deviceDialog.serialNumber'))">
                    <q-tooltip>{{ t('inventory.deviceDialog.openScanOptions') }}</q-tooltip>
                  </q-btn>
                </template>
              </q-input>
            </div>
            <div class="col-12 col-md-3">
              <q-input ref="deviceBarcodeInputRef" v-model="deviceForm.barcode" :label="t('inventory.deviceDialog.barcode')" outlined dense>
                <template #append>
                  <q-btn flat dense round color="positive" icon="qr_code_scanner" @click="openDeviceFieldCapture('barcode', t('inventory.deviceDialog.barcode'))">
                    <q-tooltip>{{ t('inventory.deviceDialog.openScanOptions') }}</q-tooltip>
                  </q-btn>
                </template>
              </q-input>
            </div>
            <div class="col-12 col-md-3">
              <q-input ref="deviceQrCodeInputRef" v-model="deviceForm.qr_code" :label="t('inventory.deviceDialog.qrCode')" outlined dense>
                <template #append>
                  <q-btn flat dense round color="positive" icon="qr_code_scanner" @click="openDeviceFieldCapture('qr_code', t('inventory.deviceDialog.qrCode'))">
                    <q-tooltip>{{ t('inventory.deviceDialog.openScanOptions') }}</q-tooltip>
                  </q-btn>
                </template>
              </q-input>
            </div>
            <div class="col-12 col-md-3">
              <q-input ref="deviceRfidInputRef" v-model="deviceForm.rfid" :label="t('inventory.deviceDialog.rfid')" outlined dense>
                <template #append>
                  <q-btn flat dense round color="positive" icon="qr_code_scanner" @click="openDeviceFieldCapture('rfid', t('inventory.deviceDialog.rfid'))">
                    <q-tooltip>{{ t('inventory.deviceDialog.openScanOptions') }}</q-tooltip>
                  </q-btn>
                </template>
              </q-input>
            </div>
            <div class="col-12 col-md-3"><q-input v-model.number="deviceForm.usage_hours" type="number" step="0.01" :label="t('inventory.deviceDialog.usageHours')" outlined dense /></div>
            <div class="col-12 col-md-4"><q-select v-model="deviceForm.status" :options="statusOptions" :label="t('inventory.deviceDialog.status')" outlined dense emit-value map-options /></div>
            <div class="col-12 col-md-4"><q-select v-model="deviceForm.condition" :options="conditionOptions" :label="t('inventory.deviceDialog.condition')" outlined dense emit-value map-options /></div>
            <div class="col-12 col-md-4"><q-select v-model="deviceForm.location_zone_id" :options="locationSelectOptions" :label="t('inventory.deviceDialog.location')" outlined dense emit-value map-options clearable /></div>
            <div class="col-12 col-md-4"><q-select v-model="deviceForm.case_device_id" :options="caseDeviceOptions" :label="t('inventory.deviceDialog.insideCase')" outlined dense emit-value map-options clearable /></div>
            <div class="col-12 col-md-4">
              <q-select
                v-model="componentDeviceIds"
                :options="componentDeviceOptions"
                :label="t('inventory.deviceDialog.componentDevices')"
                outlined dense
                multiple
                use-chips
                emit-value
                map-options
                :loading="loadingComponentDevices"
                :disable="!deviceEditing"
                :hint="!deviceEditing ? t('inventory.deviceDialog.saveFirstToAssignComponents') : ''"
              >
                <template #no-option>
                  <q-item><q-item-section class="text-grey">{{ t('inventory.deviceDialog.noAvailableComponentDevices') }}</q-item-section></q-item>
                </template>
              </q-select>
            </div>
            <div class="col-12 col-md-4"><q-input v-model="deviceForm.purchase_date" type="date" :label="t('inventory.deviceDialog.purchaseDate')" outlined dense @update:model-value="onPurchaseDateChanged" /></div>
            <div class="col-12 col-md-4"><q-input v-model.number="deviceForm.purchase_price" type="number" step="0.01" :label="t('inventory.deviceDialog.purchasePrice')" outlined dense /></div>
            <div class="col-12 col-md-4"><q-input v-model="deviceForm.purchased_from" :label="t('inventory.deviceDialog.purchasedFrom')" outlined dense /></div>
            <div class="col-12 col-md-4"><q-input v-model.number="deviceForm.sold_price" type="number" step="0.01" :label="t('inventory.deviceDialog.soldPrice')" outlined dense /></div>
            <div class="col-12 col-md-4"><q-input v-model="deviceForm.finance_upto" :label="t('inventory.deviceDialog.financeUpTo')" outlined dense /></div>
            <div class="col-12 col-md-4"><q-input v-model="deviceForm.finance_company" :label="t('inventory.deviceDialog.financeCompany')" outlined dense /></div>
            <div class="col-12 col-md-4"><q-input v-model="deviceForm.finance_ref" :label="t('inventory.deviceDialog.financeRef')" outlined dense /></div>
            <div class="col-12 col-md-4"><q-input v-model="deviceForm.pre_prep" :label="t('inventory.deviceDialog.prePrep')" outlined dense /></div>
            <div class="col-12 col-md-4"><q-input v-model="deviceForm.warranty_end_date" type="date" :label="t('inventory.deviceDialog.warrantyEnd')" outlined dense @update:model-value="onWarrantyEndDateChanged" /></div>
            <div class="col-12 col-md-4"><q-input v-model="deviceForm.retire_date" type="date" :label="t('inventory.deviceDialog.retireDate')" outlined dense /></div>
            <div class="col-12"><q-input v-model="deviceForm.notes" type="textarea" autogrow :label="t('inventory.deviceDialog.notes')" outlined dense /></div>
          </div>
          <q-banner v-if="deviceDialogError" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ deviceDialogError }}</q-banner>
        </q-form>
      </q-card-section>
      <EntityAttachmentsPanel
        entity-type="device"
        :entity-id="deviceEditing?.id || null"
        :title="t('inventory.deviceDialog.deviceDocuments')"
        default-category="device-document"
      />
      <q-card-actions :align="isPhone ? 'stretch' : 'right'" :class="isPhone ? 'q-pa-md bg-grey-2' : ''">
        <q-btn flat :class="isPhone ? 'full-width q-mb-sm' : ''" :label="t('app.actions.cancel')" @click="closeDialog" />
        <q-btn color="primary" unelevated :class="isPhone ? 'full-width' : ''" :label="deviceEditing ? t('app.actions.save') : t('inventory.create')" :loading="saving" @click="saveDevice" />
      </q-card-actions>
    </q-card>
  </q-dialog>

  <FieldScanDialog
    v-model="deviceFieldCaptureDialogOpen"
    :field-label="deviceFieldCaptureLabel"
    :initial-value="deviceFieldCaptureInitialValue"
    @captured="onFieldCaptured"
  />
</template>

<script setup>
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { DEVICE_STATUSES, useInventoryStore } from '../stores/inventory'
import { useSettingsStore } from '../stores/settings'
import { isRentalProduct } from '../utils/inventory-overview'
import { api } from '../boot/axios'
import EntityAttachmentsPanel from './EntityAttachmentsPanel.vue'
import FieldScanDialog from './FieldScanDialog.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  device: { type: Object, default: null },
  isPhone: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'saved'])

const $q = useQuasar()
const { t } = useI18n()
const store = useInventoryStore()
const settingsStore = useSettingsStore()

const saving = ref(false)
const generatingDeviceAssetTag = ref(false)
const deviceAssetTagPrefix = ref('')
const assetTagPrefixByProductType = ref({})
const PREFIX_MEMORY_STORAGE_KEY = 'inventory.prefix-memory.v1'

const deviceEditing = ref(null)
const deviceDialogError = ref('')
const deviceFormRef = ref(null)
const componentDeviceIds = ref([])
const loadingComponentDevices = ref(false)
const deviceAssetTagInputRef = ref(null)
const deviceSerialInputRef = ref(null)
const deviceBarcodeInputRef = ref(null)
const deviceQrCodeInputRef = ref(null)
const deviceRfidInputRef = ref(null)
const warrantyManuallyEdited = ref(false)
const deviceFieldCaptureDialogOpen = ref(false)
const deviceFieldCaptureTarget = ref('')
const deviceFieldCaptureLabel = ref('')
const deviceFieldCaptureInitialValue = ref('')

const emptyDeviceForm = () => ({
  product_id: null, asset_tag: '', serial_number: '', barcode: '', qr_code: '', rfid: '',
  location_zone_id: null, case_device_id: null, status: 'available', condition: 'good',
  purchase_date: '', purchase_price: null, purchased_from: '', sold_price: null, finance_upto: '', finance_company: '', finance_ref: '', pre_prep: '', warranty_end_date: '', retire_date: '', usage_hours: null, notes: '',
})
const deviceForm = ref(emptyDeviceForm())

const statusKeyMap = { available: 'Available', reserved: 'Reserved', in_use: 'InUse', maintenance: 'Maintenance' }
const statusOptions = DEVICE_STATUSES.map(item => ({ label: t('inventory.deviceStatus' + (statusKeyMap[item.value] || item.value)), value: item.value }))
const conditionOptions = [
  { label: t('inventory.conditionExcellent'), value: 'excellent' },
  { label: t('inventory.conditionGood'), value: 'good' },
  { label: t('inventory.conditionFair'), value: 'fair' },
  { label: t('inventory.conditionDamaged'), value: 'damaged' },
]

const productOptions = computed(() => store.products.map(p => ({ label: `${p.sku} - ${p.name}`, value: p.id })))
const locationSelectOptions = computed(() => {
  const flat = [{ label: t('inventory.deviceDialog.unassigned'), value: null }]
  const walk = (nodes, prefix = '') => {
    for (const node of nodes || []) {
      const label = prefix ? `${prefix} / ${node.name}` : node.name
      flat.push({ label, value: node.id })
      walk(node.children || [], label)
    }
  }
  walk(store.zoneTree)
  return flat
})
const caseDeviceOptions = computed(() => {
  return store.devices
    .filter(device => {
      const product = store.products.find(item => item.id === device.product_id)
      return product?.product_type === 'case'
    })
    .map(device => ({
      label: `${device.asset_tag} (${store.products.find(item => item.id === device.product_id)?.name || t('inventory.deviceDialog.case')})`,
      value: device.id,
    }))
})

const componentDeviceOptions = computed(() => {
  const currentProductId = deviceForm.value.product_id
  if (!currentProductId) return []
  const currentProduct = store.products.find(p => p.id === currentProductId)
  if (!currentProduct) return []
  const componentProductIds = new Set(
    (currentProduct.components || []).map(c => c.component_product_id)
  )
  if (!componentProductIds.size) return []
  return store.devices
    .filter(d => {
      if (d.id === deviceEditing.value?.id) return false
      if (isRentalProduct(store.products.find(p => p.id === d.product_id))) return false
      return componentProductIds.has(d.product_id)
    })
    .map(d => ({
      label: `${d.asset_tag} (${store.products.find(p => p.id === d.product_id)?.name || ''})`,
      value: d.id,
    }))
})

function loadPrefixMemory() {
  if (typeof window === 'undefined') return
  try {
    const raw = window.localStorage.getItem(PREFIX_MEMORY_STORAGE_KEY)
    if (!raw) return
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed === 'object') {
      assetTagPrefixByProductType.value = parsed.assetByType && typeof parsed.assetByType === 'object' ? { ...parsed.assetByType } : {}
    }
  } catch {
    // Ignore invalid local storage data.
  }
}

function persistPrefixMemory() {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(PREFIX_MEMORY_STORAGE_KEY, JSON.stringify({
      assetByType: assetTagPrefixByProductType.value,
    }))
  } catch {
    // Ignore storage quota/privacy mode failures.
  }
}

function normalizePrefix(value, fallback = '') {
  const cleaned = String(value || '').trim()
  return cleaned || fallback
}

function rememberAssetPrefixForType(type, prefix) {
  const key = String(type || '').trim()
  if (!key) return
  const normalized = normalizePrefix(prefix)
  if (!normalized) return
  assetTagPrefixByProductType.value = {
    ...assetTagPrefixByProductType.value,
    [key]: normalized,
  }
  persistPrefixMemory()
}

function getProductTypeForDeviceProductId(productId) {
  const selected = (store.products || []).find(product => product.id === productId)
  return String(selected?.product_type || '').trim()
}

function applyAssetPrefixForType(type) {
  const key = String(type || '').trim()
  const remembered = key ? assetTagPrefixByProductType.value[key] : null
  deviceAssetTagPrefix.value = normalizePrefix(remembered, '')
}

function openCreateDevice() {
  deviceEditing.value = null
  deviceForm.value = emptyDeviceForm()
  applyAssetPrefixForType('')
  warrantyManuallyEdited.value = false
  deviceDialogError.value = ''
}

function openEditDevice(device) {
  deviceEditing.value = device
  deviceForm.value = {
    product_id: device.product_id ?? null,
    asset_tag: device.asset_tag ?? '',
    serial_number: device.serial_number ?? '',
    barcode: device.barcode ?? '',
    qr_code: device.qr_code ?? '',
    rfid: device.rfid ?? '',
    location_zone_id: device.location_zone_id ?? null,
    case_device_id: device.case_device_id ?? null,
    status: device.status ?? 'available',
    condition: device.condition ?? 'good',
    purchase_date: device.purchase_date || '',
    purchase_price: device.purchase_price ?? null,
    purchased_from: device.purchased_from ?? '',
    sold_price: device.sold_price ?? null,
    finance_upto: device.finance_upto ?? '',
    finance_company: device.finance_company ?? '',
    finance_ref: device.finance_ref ?? '',
    pre_prep: device.pre_prep ?? '',
    warranty_end_date: device.warranty_end_date || '',
    retire_date: device.retire_date || '',
    usage_hours: device.usage_hours ?? null,
    notes: device.notes ?? '',
  }
  applyAssetPrefixForType(getProductTypeForDeviceProductId(device.product_id))
  warrantyManuallyEdited.value = true
  deviceDialogError.value = ''
  loadComponentDevices(device.id)
}

function loadComponentDevices(deviceId) {
  if (!deviceId) {
    componentDeviceIds.value = []
    return
  }
  loadingComponentDevices.value = true
  api.get(`/api/v1/inventory/devices/${deviceId}/component-devices`)
    .then(({ data }) => {
      componentDeviceIds.value = (Array.isArray(data) ? data : []).map(d => d.id)
    })
    .catch(() => {
      componentDeviceIds.value = []
    })
    .finally(() => {
      loadingComponentDevices.value = false
    })
}

function closeDialog() {
  emit('update:modelValue', false)
}

async function generateDeviceAssetTag() {
  generatingDeviceAssetTag.value = true
  try {
    const productType = getProductTypeForDeviceProductId(deviceForm.value.product_id)
    if (deviceAssetTagPrefix.value) {
      rememberAssetPrefixForType(productType, deviceAssetTagPrefix.value)
    }
    const assetTag = await store.generateDeviceAssetTag({
      productId: deviceForm.value.product_id || null,
      prefix: deviceAssetTagPrefix.value || null,
    })
    if (assetTag) {
      deviceForm.value.asset_tag = assetTag
      const inferredPrefix = String(assetTag).replace(/-\d+$/, '')
      rememberAssetPrefixForType(productType, inferredPrefix)
      if (!deviceAssetTagPrefix.value) {
        deviceAssetTagPrefix.value = inferredPrefix
      }
    }
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('inventory.deviceDialog.failedGenerateAssetTag') })
  } finally {
    generatingDeviceAssetTag.value = false
  }
}

async function saveDevice() {
  const valid = await deviceFormRef.value?.validate()
  if (!valid) return

  saving.value = true
  deviceDialogError.value = ''
  try {
    const payload = {
      product_id: deviceForm.value.product_id,
      asset_tag: deviceForm.value.asset_tag.trim(),
      serial_number: deviceForm.value.serial_number || null,
      barcode: deviceForm.value.barcode || null,
      qr_code: deviceForm.value.qr_code || null,
      rfid: deviceForm.value.rfid || null,
      location_zone_id: deviceForm.value.location_zone_id,
      case_device_id: deviceForm.value.case_device_id,
      status: deviceForm.value.status,
      condition: deviceForm.value.condition,
      purchase_date: normalizeOptionalDate(deviceForm.value.purchase_date),
      purchase_price: deviceForm.value.purchase_price === '' || deviceForm.value.purchase_price === null || deviceForm.value.purchase_price === undefined ? null : Number(deviceForm.value.purchase_price),
      purchased_from: deviceForm.value.purchased_from || null,
      sold_price: deviceForm.value.sold_price === '' || deviceForm.value.sold_price === null || deviceForm.value.sold_price === undefined ? null : Number(deviceForm.value.sold_price),
      finance_upto: deviceForm.value.finance_upto || null,
      finance_company: deviceForm.value.finance_company || null,
      finance_ref: deviceForm.value.finance_ref || null,
      pre_prep: deviceForm.value.pre_prep || null,
      warranty_end_date: normalizeOptionalDate(deviceForm.value.warranty_end_date),
      retire_date: normalizeOptionalDate(deviceForm.value.retire_date),
      usage_hours: deviceForm.value.usage_hours,
      notes: deviceForm.value.notes || null,
    }

    let savedDevice
    if (deviceEditing.value) {
      savedDevice = await store.updateDevice(deviceEditing.value.id, payload)
      $q.notify({ type: 'positive', message: t('inventory.deviceDialog.deviceUpdated') })
    } else {
      savedDevice = await store.createDevice(payload)
      $q.notify({ type: 'positive', message: t('inventory.deviceDialog.deviceCreated') })
    }
    if (savedDevice?.id || deviceEditing.value?.id) {
      const id = savedDevice?.id || deviceEditing.value?.id
      await api.put(`/api/v1/inventory/devices/${id}/component-devices`, componentDeviceIds.value)
    }
    emit('update:modelValue', false)
    emit('saved')
  } catch (error) {
    deviceDialogError.value = error?.response?.data?.detail || t('inventory.deviceDialog.failedSaveDevice')
  } finally {
    saving.value = false
  }
}

function addYearsToDateString(dateString, yearsToAdd) {
  if (!dateString) return ''
  const dateObj = new Date(`${dateString}T00:00:00`)
  if (Number.isNaN(dateObj.getTime())) return ''
  dateObj.setFullYear(dateObj.getFullYear() + yearsToAdd)
  return dateObj.toISOString().slice(0, 10)
}

function onPurchaseDateChanged(value) {
  const purchaseDate = String(value || '').trim()
  if (!purchaseDate) return
  if (warrantyManuallyEdited.value && deviceForm.value.warranty_end_date) return
  const prefetchedWarrantyDate = addYearsToDateString(purchaseDate, 3)
  if (prefetchedWarrantyDate) {
    deviceForm.value.warranty_end_date = prefetchedWarrantyDate
  }
}

function onWarrantyEndDateChanged() {
  warrantyManuallyEdited.value = true
}

function normalizeOptionalDate(value) {
  return value ? value : null
}

// Field capture functions
function focusDeviceField(field) {
  const fieldRefMap = {
    asset_tag: deviceAssetTagInputRef,
    serial_number: deviceSerialInputRef,
    barcode: deviceBarcodeInputRef,
    qr_code: deviceQrCodeInputRef,
    rfid: deviceRfidInputRef,
  }
  fieldRefMap[field]?.value?.focus?.()
}

function setCapturedDeviceFieldValue(field, value) {
  if (!field) return
  if (!Object.prototype.hasOwnProperty.call(deviceForm.value, field)) return
  const normalized = String(value || '').trim()
  if (!normalized) return
  deviceForm.value[field] = normalized
  $q.notify({ type: 'positive', message: t('inventory.deviceDialog.fieldCaptured', { field: deviceFieldCaptureLabel.value || '' }) })
}

function openDeviceFieldCapture(field, label) {
  deviceFieldCaptureTarget.value = field
  deviceFieldCaptureLabel.value = label
  deviceFieldCaptureInitialValue.value = deviceForm.value[field] || ''
  deviceFieldCaptureDialogOpen.value = true
}

function onFieldCaptured(value) {
  setCapturedDeviceFieldValue(deviceFieldCaptureTarget.value, value)
}

function focusDeviceCaptureTargetField() {
  focusDeviceField(deviceFieldCaptureTarget.value)
  $q.notify({ type: 'info', message: `Target ${deviceFieldCaptureLabel.value} focused for keyboard scanner input` })
}

watch(() => deviceForm.value.product_id, (nextProductId) => {
  if (!props.modelValue) return
  applyAssetPrefixForType(getProductTypeForDeviceProductId(nextProductId))
})

watch(() => props.modelValue, (open) => {
  if (open) {
    loadPrefixMemory()
    if (props.device) {
      openEditDevice(props.device)
    } else {
      openCreateDevice()
    }
  }
})

onUnmounted(async () => {
  if (ocrWorkerInstance) {
    try {
      await ocrWorkerInstance.terminate()
    } catch {
      // Ignore termination errors on unmount.
    }
    ocrWorkerInstance = null
  }
})
</script>

<style lang="scss" scoped>
.device-capture-card {
  background: var(--q-dark-page, #1d1d1d) !important;
}
.device-capture-icon-wrap {
  width: 60px;
  height: 60px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--q-primary, #1976d2);
}
.device-capture-camera-wrap {
  border-radius: 8px;
  overflow: hidden;
  background: #000;
  max-width: 100%;
}
.device-capture-video {
  width: 100%;
  display: block;
}
</style>
