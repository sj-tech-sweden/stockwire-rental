<template>
  <q-page class="q-pa-md">
    <div class="text-h6 q-mb-md">{{ t('receiving.title') }}</div>

    <q-tabs v-model="mode" dense class="q-mb-md" active-color="primary">
      <q-tab name="po" :label="t('receiving.fromPo')" />
      <q-tab name="scan" :label="t('receiving.scanBarcode')" />
    </q-tabs>

    <!-- PO-centric receiving -->
    <template v-if="mode === 'po'">
      <q-card flat bordered class="q-pa-md q-mb-md">
        <div class="row q-gutter-sm items-end">
          <q-select
            v-model="selectedPoId"
            :options="poOptions"
            :label="t('receiving.selectPo')"
            emit-value
            map-options
            clearable
            class="col"
            @update:model-value="loadPo"
          />
        </div>
      </q-card>

      <q-card flat bordered v-if="po" class="q-pa-md q-mb-md">
        <div class="row items-center q-gutter-md">
          <div class="text-subtitle1">{{ po.po_number }}</div>
          <q-chip color="grey-7" text-color="white" dense>{{ po.status }}</q-chip>
          <div class="text-caption">{{ po.supplier_name }}</div>
        </div>
        <q-list separator class="q-mt-sm">
          <q-item v-for="line in poLines" :key="line.id">
            <q-item-section>
              <q-item-label>{{ line.name || line.sku }}</q-item-label>
              <q-item-label caption>
                {{ t('receiving.qty') }}: {{ line.qty }} ·
                {{ t('receiving.received') }}: {{ line.received_qty }} ·
                {{ t('receiving.remaining') }}: {{ line.remaining }}
                <span v-if="line.currency"> · {{ line.unit_cost }} {{ line.currency }}</span>
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-btn
                color="primary"
                :label="t('receiving.receive')"
                :disable="line.remaining <= 0"
                @click="openReceiveForPoLine(line)"
              />
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>
    </template>

    <!-- Barcode scan receiving -->
    <template v-else>
      <q-card flat bordered class="q-pa-md q-mb-md">
        <div class="row q-gutter-sm items-end">
          <q-input
            v-model="scanCode"
            :label="t('receiving.scanPrompt')"
            class="col"
            clearable
            autofocus
            @keyup.enter="doLookup"
          >
            <template #prepend>
              <q-icon name="qr_code_scanner" />
            </template>
          </q-input>
          <q-btn color="primary" :label="t('receiving.lookup')" :loading="loading" @click="doLookup" />
        </div>
      </q-card>

      <q-banner v-if="error" class="bg-negative text-white q-mb-md" dense>{{ error }}</q-banner>

      <template v-if="lookup">
        <q-card flat bordered class="q-pa-md q-mb-md" v-if="lookup.product">
          <div class="row q-gutter-md items-center">
            <q-avatar icon="inventory_2" color="primary" text-color="white" />
            <div>
              <div class="text-subtitle1">{{ lookup.product.name }}</div>
              <div class="text-caption">
                {{ t('receiving.sku') }}: {{ lookup.product.sku }}
                <span v-if="lookup.product.barcode"> · {{ t('receiving.barcode') }}: {{ lookup.product.barcode }}</span>
              </div>
            </div>
          </div>
        </q-card>

        <q-card flat bordered v-if="lookup.lines.length" class="q-mb-md">
          <q-card-section class="text-subtitle2">{{ t('receiving.openLines') }}</q-card-section>
          <q-list separator>
            <q-item v-for="line in lookup.lines" :key="line.line_id">
              <q-item-section>
                <q-item-label>{{ line.name || lookup.product?.name }}</q-item-label>
                <q-item-label caption>
                  {{ t('receiving.poNumber') }}: {{ line.po_number }} ·
                  {{ t('receiving.qty') }}: {{ line.qty }} ·
                  {{ t('receiving.received') }}: {{ line.received_qty }} ·
                  {{ t('receiving.remaining') }}: {{ line.remaining }}
                  <span v-if="line.currency"> · {{ line.unit_cost }} {{ line.currency }}</span>
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-btn
                  color="primary"
                  :label="t('receiving.receive')"
                  :disable="line.remaining <= 0"
                  @click="openReceive(line)"
                />
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>

        <q-banner v-else class="bg-grey-3 q-mb-md" dense>{{ t('receiving.noMatch') }}</q-banner>
      </template>
    </template>

    <!-- Shared receive dialog -->
    <q-dialog v-model="receiveDialog" persistent>
      <q-card style="width: 700px; max-width: 95vw" class="q-pa-md">
        <q-card-section class="row items-center">
          <div class="text-h6">{{ t('receiving.receive') }}</div>
          <q-space />
          <q-btn flat round dense icon="close" @click="receiveDialog = false" />
        </q-card-section>

        <q-card-section v-if="activeLine">
          <div class="text-subtitle2">
            {{ activeLine.name }}
            <span class="text-caption">· {{ t('receiving.remaining') }}: {{ activeLine.remaining - receivedQty }}</span>
          </div>

          <div class="row items-end q-gutter-sm q-mt-xs">
            <q-input
              v-model.number="receiveQtyInput"
              type="number"
              :label="t('receiving.qtyToReceive')"
              dense
              outlined
              style="width: 150px"
              :min="0"
              :max="activeLine.remaining"
              :disable="activeLine.creates_device && createdDevices.length > 0"
            />
            <div class="text-caption q-pb-xs">
              {{ t('receiving.receiveWithoutSerialsHint') }}
            </div>
          </div>

          <!-- Sale article: no device created, optional serials -->
          <template v-if="!activeLine.creates_device">
            <q-banner class="bg-info text-white q-mt-sm" dense>
              {{ t('receiving.saleArticleNote') }}
            </q-banner>
            <div class="row q-gutter-sm items-end q-mt-md">
              <q-input
                v-model="serialInput"
                :label="t('receiving.serialNumber')"
                class="col"
                @keyup.enter="addSaleSerial"
              >
                <template #prepend><q-icon name="qr_code_scanner" /></template>
              </q-input>
              <q-btn
                icon="qr_code_scanner"
                color="primary"
                :label="t('receiving.scanSerialBtn')"
                @click="scanOpen = true"
              />
            </div>
            <q-list bordered separator class="q-mt-md" v-if="saleSerials.length">
              <q-item-label header>{{ t('receiving.capturedSerials') }} ({{ saleSerials.length }})</q-item-label>
              <q-item v-for="(s, i) in saleSerials" :key="i">
                <q-item-section>{{ s }}</q-item-section>
                <q-item-section side>
                  <q-btn flat round dense icon="delete" color="negative" @click="saleSerials.splice(i, 1)" />
                </q-item-section>
              </q-item>
            </q-list>
          </template>

          <!-- Device line: full device create dialog per unit -->
          <template v-else>
            <div class="row q-mt-sm">
              <q-btn
                color="primary"
                icon="add"
                :label="t('receiving.addDevice')"
                @click="openDeviceDialog"
              />
            </div>
            <q-list bordered separator class="q-mt-md" v-if="createdDevices.length">
              <q-item-label header>{{ t('receiving.pendingDevices') }} ({{ createdDevices.length }})</q-item-label>
              <q-item v-for="(d, i) in createdDevices" :key="i">
                <q-item-section>
                  <q-item-label>{{ d.asset_tag || d.serial_number || t('receiving.serialNumber') + ' —' }}</q-item-label>
                  <q-item-label caption v-if="d.condition">
                    {{ conditionLabel(d.condition) }}
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-btn flat round dense icon="delete" color="negative" @click="createdDevices.splice(i, 1)" />
                </q-item-section>
              </q-item>
            </q-list>
          </template>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="receiveDialog = false" />
          <q-btn
            color="primary"
            :label="t('receiving.finish')"
            :disable="!canFinish"
            :loading="submitting"
            @click="submitReceive"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <FieldScanDialog v-model="scanOpen" :field-label="t('receiving.serialNumber')" @captured="onSerialCaptured" />
    <DeviceDialog v-model="deviceDialogOpen" :device="devicePrefill" @saved="onDeviceSaved" />
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useQuasar } from 'quasar'
import { useInventoryStore } from '../stores/inventory'
import FieldScanDialog from '../components/FieldScanDialog.vue'
import DeviceDialog from '../components/DeviceDialog.vue'

const { t } = useI18n()
const $q = useQuasar()
const store = useInventoryStore()
const route = useRoute()

const mode = ref('po')
const scanCode = ref('')
const lookup = ref(null)
const loading = ref(false)
const error = ref('')

const selectedPoId = ref(route.query.po ? Number(route.query.po) : null)
const poOptions = ref([])
const po = ref(null)
const poLoading = ref(false)

const receiveDialog = ref(false)
const activeLine = ref(null)
const serialInput = ref('')
const scanOpen = ref(false)
const saleSerials = ref([])
const createdDevices = ref([])
const deviceDialogOpen = ref(false)
const devicePrefill = ref(null)
const submitting = ref(false)
const receiveQtyInput = ref(0)

const conditionOptions = [
  { label: t('inventory.conditionExcellent'), value: 'excellent' },
  { label: t('inventory.conditionGood'), value: 'good' },
  { label: t('inventory.conditionFair'), value: 'fair' },
  { label: t('inventory.conditionDamaged'), value: 'damaged' },
]

function conditionLabel(value) {
  const found = conditionOptions.find(o => o.value === value)
  return found ? found.label : value
}

const poLines = computed(() =>
  (po.value?.lines || []).map(line => ({
    ...line,
    remaining: Math.max(0, (line.qty || 0) - (line.received_qty || 0)),
  }))
)

const receivedQty = computed(() => {
  if (!activeLine.value) return 0
  if (activeLine.value.creates_device && createdDevices.value.length > 0) {
    return createdDevices.value.length
  }
  return receiveQtyInput.value
})

const canFinish = computed(() => {
  const q = receivedQty.value
  return q > 0 && q <= (activeLine.value?.remaining || 0)
})

watch(createdDevices, (list) => {
  if (activeLine.value?.creates_device && list.length > 0) receiveQtyInput.value = list.length
})

onMounted(async () => {
  try {
    const data = await store.listPurchaseOrders()
    const rows = Array.isArray(data) ? data : (data.items || [])
    poOptions.value = rows.map(p => ({
      label: `${p.po_number} — ${p.supplier_name || ''} (${p.status})`,
      value: p.id,
    }))
  } catch {
    poOptions.value = []
  }
  if (selectedPoId.value) await loadPo(selectedPoId.value)
})

async function loadPo(id) {
  po.value = null
  if (!id) return
  poLoading.value = true
  try {
    po.value = await store.getPurchaseOrder(id)
  } catch (e) {
    $q.notify({ type: 'negative', message: e?.response?.data?.detail || t('receiving.receiveFailed') })
  } finally {
    poLoading.value = false
  }
}

async function doLookup() {
  const code = scanCode.value.trim()
  if (!code) return
  loading.value = true
  error.value = ''
  try {
    lookup.value = await store.receivingLookup(code)
  } catch (e) {
    error.value = e?.response?.data?.detail || t('receiving.receiveFailed')
    lookup.value = null
  } finally {
    loading.value = false
  }
}

function openReceive(line) {
  activeLine.value = {
    po_id: line.po_id,
    line_id: line.line_id,
    name: line.name,
    remaining: line.remaining,
    received_qty: line.received_qty || 0,
    creates_device: line.creates_device,
    product_id: lookup.value?.product?.id ?? line.product_id,
    unit_cost: line.unit_cost,
  }
  resetDialogState()
  receiveQtyInput.value = line.remaining
  receiveDialog.value = true
}

function openReceiveForPoLine(line) {
  activeLine.value = {
    po_id: po.value.id,
    line_id: line.id,
    name: line.name,
    remaining: line.remaining,
    creates_device: line.creates_device,
    product_id: line.product_id,
    unit_cost: line.unit_cost,
  }
  resetDialogState()
  receiveQtyInput.value = line.remaining
  receiveDialog.value = true
}

function resetDialogState() {
  serialInput.value = ''
  saleSerials.value = []
  createdDevices.value = []
  devicePrefill.value = null
}

function addSaleSerial() {
  const s = serialInput.value.trim()
  if (!s) return
  if (!saleSerials.value.includes(s)) saleSerials.value.push(s)
  serialInput.value = ''
}

function onSerialCaptured(value) {
  serialInput.value = value
  addSaleSerial()
}

function openDeviceDialog() {
  devicePrefill.value = {
    product_id: activeLine.value?.product_id ?? null,
    purchase_price: activeLine.value?.unit_cost ?? null,
  }
  deviceDialogOpen.value = true
}

function onDeviceSaved(device) {
  createdDevices.value.push({
    asset_tag: device?.asset_tag || null,
    serial_number: device?.serial_number || null,
    condition: device?.condition || 'good',
  })
}

async function submitReceive() {
  if (!activeLine.value || !canFinish.value) return
  submitting.value = true
  try {
    const line = activeLine.value
    // Backend expects the ABSOLUTE cumulative received count, so add the amount
    // being received now to what was already received on this line.
    const toAdd = receivedQty.value
    const absolute = (line.received_qty || 0) + toAdd
    const payload = { line_id: line.line_id, devices: [], received_qty: absolute }
    if (line.creates_device) {
      if (createdDevices.value.length > 0) {
        // Send the captured device specs so the backend mints one Device per spec
        // (with the scanned asset tags / serials / condition).
        payload.devices = createdDevices.value.map((d) => ({
          asset_tag: d.asset_tag || null,
          serial_number: d.serial_number || null,
          condition: d.condition || 'new',
        }))
      } else {
        // Receive without scanning: auto-create units with generated asset tags
        // so a partial receipt (e.g. 1 or 2 of 3) is possible.
        payload.devices = null
      }
    } else {
      payload.serials = saleSerials.value
    }
    await store.receivePurchaseOrder(line.po_id, [payload])
    $q.notify({
      type: 'positive',
      message: t('receiving.receivedOk', { count: receivedQty.value }),
    })
    receiveDialog.value = false
    if (mode.value === 'scan' && scanCode.value.trim()) await doLookup()
    if (mode.value === 'po' && selectedPoId.value) await loadPo(selectedPoId.value)
  } catch (e) {
    $q.notify({ type: 'negative', message: e?.response?.data?.detail || t('receiving.receiveFailed') })
  } finally {
    submitting.value = false
  }
}
</script>
