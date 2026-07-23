<template>
  <div>
    <q-tabs v-model="ledTab" inline-label align="left" class="q-mb-md" active-color="primary">
      <q-tab name="controllers" icon="developer_board" :label="t('warehouseLeds.tabs.controllers')" />
      <q-tab name="mappings" icon="linear_scale" :label="t('warehouseLeds.tabs.mappings')" />
      <q-tab name="actions" icon="flash_on" :label="t('warehouseLeds.tabs.actions')" />
      <q-tab name="esphome" icon="code" :label="t('warehouseLeds.tabs.esphome')" />
    </q-tabs>

    <q-tab-panels v-model="ledTab" animated>
      <!-- Controllers Tab -->
      <q-tab-panel name="controllers" class="q-pa-none">
        <q-card class="ec-card q-pa-md">
          <div class="row items-center q-mb-md">
            <div class="text-subtitle1 col">{{ t('warehouseLeds.controllersList') }}</div>
            <q-btn color="primary" icon="add" :label="t('warehouseLeds.newController')" unelevated @click="openCreateController" />
          </div>

          <q-table
            :rows="controllers" :columns="controllerColumns" row-key="id"
            flat bordered :loading="loading"
            :pagination="{ rowsPerPage: 25 }"
          >
            <template #body-cell-status="props">
              <q-td :props="props">
                <q-badge :color="props.row.status === 'online' ? 'positive' : 'grey'" :label="props.row.status" />
              </q-td>
            </template>

            <template #body-cell-last_seen="props">
              <q-td :props="props">
                {{ props.row.last_seen ? new Date(props.row.last_seen).toLocaleString() : '-' }}
              </q-td>
            </template>

            <template #body-cell-actions="props">
              <q-td :props="props" auto-width>
                <q-btn flat round dense icon="edit" color="primary" @click="openEditController(props.row)" />
                <q-btn flat round dense icon="settings" color="secondary" @click="openControllerZones(props.row)" />
                <q-btn flat round dense icon="download" color="info" @click="downloadYaml(props.row)" />
                <q-btn flat round dense icon="delete" color="negative" @click="confirmDeleteController(props.row)" />
              </q-td>
            </template>
          </q-table>
        </q-card>
      </q-tab-panel>

      <!-- Mappings Tab -->
      <q-tab-panel name="mappings" class="q-pa-none">
        <q-card class="ec-card q-pa-md">
          <div class="row items-center q-mb-md">
            <div class="text-subtitle1 col">{{ t('warehouseLeds.binMappings') }}</div>
            <q-btn color="primary" icon="add" :label="t('warehouseLeds.newMapping')" unelevated @click="openCreateMapping" />
          </div>

          <q-table
            :rows="mappings" :columns="mappingColumns" row-key="id"
            flat bordered :loading="loading"
            :pagination="{ rowsPerPage: 25 }"
          >
            <template #body-cell-default_color="props">
              <q-td :props="props">
                <q-badge :style="{ backgroundColor: props.row.default_color }" :label="props.row.default_color" />
              </q-td>
            </template>

            <template #body-cell-pixel_range="props">
              <q-td :props="props">
                {{ props.row.pixel_start }} - {{ props.row.pixel_end }}
              </q-td>
            </template>

            <template #body-cell-actions="props">
              <q-td :props="props" auto-width>
                <q-btn flat round dense icon="edit" color="primary" @click="openEditMapping(props.row)" />
                <q-btn flat round dense icon="delete" color="negative" @click="confirmDeleteMapping(props.row)" />
              </q-td>
            </template>
          </q-table>
        </q-card>
      </q-tab-panel>

      <!-- Actions Tab -->
      <q-tab-panel name="actions" class="q-pa-none">
        <div class="q-gutter-md">
          <q-card flat bordered class="ec-card q-pa-md">
            <div class="row items-center q-mb-sm">
              <q-btn color="orange" icon="flash_on" :label="t('warehouseLeds.identifyAll')" unelevated @click="onIdentifyAll" class="q-mr-sm" />
              <q-btn color="negative" icon="clear_all" :label="t('warehouseLeds.clearAll')" unelevated @click="onClearAll" />
            </div>
          </q-card>

          <q-card flat bordered class="ec-card q-pa-md">
            <div class="text-subtitle1">{{ t('warehouseLeds.actions.locateDevice') }}</div>
            <div class="text-caption q-mb-sm">{{ t('warehouseLeds.actions.locateDeviceDesc') }}</div>
            <div class="row q-gutter-sm">
              <q-input v-model="locateDeviceId" :label="t('warehouseLeds.actions.deviceId')" outlined type="number" class="col" />
              <q-btn color="red" icon="gps_fixed" :label="t('warehouseLeds.actions.locate')" unelevated @click="onLocateDevice" />
            </div>
          </q-card>

          <q-card flat bordered class="ec-card q-pa-md">
            <div class="text-subtitle1">{{ t('warehouseLeds.actions.showReturn') }}</div>
            <div class="text-caption q-mb-sm">{{ t('warehouseLeds.actions.showReturnDesc') }}</div>
            <div class="row q-gutter-sm">
              <q-input v-model="returnZoneId" :label="t('warehouseLeds.actions.zoneId')" outlined type="number" class="col" />
              <q-btn color="green" icon="assignment_return" :label="t('warehouseLeds.actions.showReturnBtn')" unelevated @click="onShowReturn" />
            </div>
          </q-card>

          <q-card flat bordered class="ec-card q-pa-md">
            <div class="text-subtitle1">{{ t('warehouseLeds.actions.highlightJob') }}</div>
            <div class="text-caption q-mb-sm">{{ t('warehouseLeds.actions.highlightJobDesc') }}</div>
            <div class="row q-gutter-sm">
              <q-input v-model="highlightJobId" :label="t('warehouseLeds.actions.jobId')" outlined type="number" class="col" />
              <q-btn color="orange" icon="work" :label="t('warehouseLeds.actions.highlight')" unelevated @click="onHighlightJob" />
            </div>
          </q-card>
        </div>
      </q-tab-panel>

      <!-- ESPHome Tab -->
      <q-tab-panel name="esphome" class="q-pa-none">
        <div class="q-gutter-md">
          <q-card flat bordered class="ec-card q-pa-md">
            <div class="text-subtitle1">{{ t('warehouseLeds.esphome.generateConfig') }}</div>
            <div class="text-caption q-mb-sm">{{ t('warehouseLeds.esphome.generateConfigDesc') }}</div>
            <div class="row q-gutter-sm items-end">
              <q-select v-model="esphomeController" :options="controllers" option-label="controller_id" option-value="controller_id" :label="t('warehouseLeds.esphome.selectController')" outlined emit-value map-options class="col" />
              <q-btn color="primary" icon="download" :label="t('warehouseLeds.esphome.downloadYaml')" unelevated :disable="!esphomeController" @click="onDownloadYaml" />
            </div>
          </q-card>

          <q-card flat bordered class="ec-card q-pa-md">
            <div class="text-subtitle1">{{ t('warehouseLeds.esphome.secretsTemplate') }}</div>
            <div class="text-caption q-mb-sm">{{ t('warehouseLeds.esphome.secretsTemplateDesc') }}</div>
            <q-btn color="secondary" icon="download" :label="t('warehouseLeds.esphome.downloadTemplate')" unelevated @click="onDownloadSecretsTemplate" />
          </q-card>

          <q-card v-if="yamlPreview" flat bordered class="ec-card q-pa-md">
            <div class="text-subtitle1 q-mb-sm">{{ t('warehouseLeds.esphome.preview') }}</div>
            <q-input v-model="yamlPreview" type="textarea" readonly outlined input-class="text-mono" :style="{ minHeight: '400px' }" />
          </q-card>
        </div>
      </q-tab-panel>
    </q-tab-panels>

    <!-- Create/Edit Controller Dialog -->
    <q-dialog v-model="controllerDialogOpen" persistent>
      <q-card style="min-width: 450px" class="ec-card">
        <q-card-section class="row items-center">
          <div class="text-h6">{{ editingController ? t('warehouseLeds.editController') : t('warehouseLeds.newController') }}</div>
          <q-space />
          <q-btn icon="close" flat round dense @click="controllerDialogOpen = false" />
        </q-card-section>
        <q-card-section>
          <q-input v-model="controllerForm.controller_id" :label="t('warehouseLeds.form.controllerId')" outlined :disable="!!editingController" class="q-mb-sm" />
          <q-input v-model="controllerForm.display_name" :label="t('warehouseLeds.form.displayName')" outlined class="q-mb-sm" />
          <q-input v-model="controllerForm.mac_address" :label="t('warehouseLeds.form.macAddress')" outlined class="q-mb-sm" />
          <q-input v-model.number="controllerForm.led_count" :label="t('warehouseLeds.form.ledCount')" outlined type="number" class="q-mb-sm" />
          <q-input v-model="controllerForm.topic_suffix" :label="t('warehouseLeds.form.topicSuffix')" outlined class="q-mb-sm" />
          <q-input v-model="controllerForm.notes" :label="t('warehouseLeds.form.notes')" outlined type="textarea" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('common.cancel')" @click="controllerDialogOpen = false" />
          <q-btn color="primary" :label="t('common.save')" @click="onSaveController" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Create/Edit Mapping Dialog -->
    <q-dialog v-model="mappingDialogOpen" persistent>
      <q-card style="min-width: 450px" class="ec-card">
        <q-card-section class="row items-center">
          <div class="text-h6">{{ editingMapping ? t('warehouseLeds.editMapping') : t('warehouseLeds.newMapping') }}</div>
          <q-space />
          <q-btn icon="close" flat round dense @click="mappingDialogOpen = false" />
        </q-card-section>
        <q-card-section>
          <q-select v-model="mappingForm.controller_id" :options="controllers" option-label="controller_id" option-value="id" :label="t('warehouseLeds.form.controller')" outlined emit-value map-options class="q-mb-sm" />
          <q-input v-model="mappingForm.bin_label" :label="t('warehouseLeds.form.binLabel')" outlined class="q-mb-sm" />
          <q-input v-model="mappingForm.shelf_label" :label="t('warehouseLeds.form.shelfLabel')" outlined class="q-mb-sm" />
          <q-input v-model.number="mappingForm.pixel_start" :label="t('warehouseLeds.form.pixelStart')" outlined type="number" class="q-mb-sm" />
          <q-input v-model.number="mappingForm.pixel_end" :label="t('warehouseLeds.form.pixelEnd')" outlined type="number" class="q-mb-sm" />
          <q-input v-model="mappingForm.default_color" :label="t('warehouseLeds.form.defaultColor')" outlined class="q-mb-sm">
            <template #prepend>
              <q-icon name="palette" :style="{ color: mappingForm.default_color }" />
            </template>
          </q-input>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('common.cancel')" @click="mappingDialogOpen = false" />
          <q-btn color="primary" :label="t('common.save')" @click="onSaveMapping" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Zone Assignment Dialog -->
    <q-dialog v-model="zoneDialogOpen" persistent>
      <q-card style="min-width: 450px" class="ec-card">
        <q-card-section class="row items-center">
          <div class="text-h6">{{ t('warehouseLeds.assignZones') }}</div>
          <q-space />
          <q-btn icon="close" flat round dense @click="zoneDialogOpen = false" />
        </q-card-section>
        <q-card-section>
          <div class="text-caption q-mb-sm">{{ t('warehouseLeds.zoneAssignDesc') }}</div>
          <q-select v-model="selectedZones" :options="availableZones" option-label="name" option-value="id" :label="t('warehouseLeds.form.zones')" outlined multiple emit-value use-chips class="q-mb-sm" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('common.cancel')" @click="zoneDialogOpen = false" />
          <q-btn color="primary" :label="t('common.save')" @click="onSaveZones" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, reactive } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useWarehouseLedsStore } from '../stores/warehouseLeds'
import { api } from '../boot/axios'

const $q = useQuasar()
const { t } = useI18n()
const store = useWarehouseLedsStore()

const ledTab = ref('controllers')
const loading = computed(() => store.loading)
const controllers = computed(() => store.controllers)
const mappings = computed(() => store.mappings)

const controllerColumns = [
  { name: 'controller_id', label: t('warehouseLeds.form.controllerId'), field: 'controller_id', sortable: true, align: 'left' },
  { name: 'display_name', label: t('warehouseLeds.form.displayName'), field: 'display_name', sortable: true, align: 'left' },
  { name: 'led_count', label: t('warehouseLeds.form.ledCount'), field: 'led_count', sortable: true, align: 'left' },
  { name: 'status', label: t('warehouseLeds.status'), field: 'status', sortable: true, align: 'left' },
  { name: 'ip_address', label: 'IP', field: 'ip_address', align: 'left' },
  { name: 'last_seen', label: t('warehouseLeds.lastSeen'), field: 'last_seen', sortable: true, align: 'left' },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
]

const mappingColumns = [
  { name: 'bin_label', label: t('warehouseLeds.form.binLabel'), field: 'bin_label', sortable: true, align: 'left' },
  { name: 'shelf_label', label: t('warehouseLeds.form.shelfLabel'), field: 'shelf_label', sortable: true, align: 'left' },
  { name: 'zone_code', label: t('warehouseLeds.zone'), field: 'zone_code', sortable: true, align: 'left' },
  { name: 'controller_id', label: t('warehouseLeds.controller'), field: 'controller_id', sortable: true, align: 'left' },
  { name: 'pixel_range', label: t('warehouseLeds.form.pixelRange'), field: 'pixel_start', align: 'left' },
  { name: 'default_color', label: t('warehouseLeds.form.defaultColor'), field: 'default_color', align: 'left' },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
]

const controllerDialogOpen = ref(false)
const editingController = ref(null)
const controllerForm = reactive({ controller_id: '', display_name: '', mac_address: '', led_count: 300, topic_suffix: '', notes: '' })

const mappingDialogOpen = ref(false)
const editingMapping = ref(null)
const mappingForm = reactive({ controller_id: null, bin_label: '', shelf_label: '', pixel_start: 0, pixel_end: 0, default_color: '#FF6600', zone_id: null })

const zoneDialogOpen = ref(false)
const zoneController = ref(null)
const selectedZones = ref([])
const availableZones = ref([])

const locateDeviceId = ref(null)
const returnZoneId = ref(null)
const highlightJobId = ref(null)
const esphomeController = ref(null)
const yamlPreview = ref('')

function openCreateController() {
  editingController.value = null
  Object.assign(controllerForm, { controller_id: '', display_name: '', mac_address: '', led_count: 300, topic_suffix: '', notes: '' })
  controllerDialogOpen.value = true
}

function openEditController(ctrl) {
  editingController.value = ctrl
  Object.assign(controllerForm, {
    controller_id: ctrl.controller_id,
    display_name: ctrl.display_name || '',
    mac_address: ctrl.mac_address || '',
    led_count: ctrl.led_count,
    topic_suffix: ctrl.topic_suffix || '',
    notes: ctrl.notes || '',
  })
  controllerDialogOpen.value = true
}

async function onSaveController() {
  try {
    if (editingController.value) {
      await store.updateController(editingController.value.id, { ...controllerForm })
    } else {
      await store.createController({ ...controllerForm })
    }
    controllerDialogOpen.value = false
    $q.notify({ type: 'positive', message: t('common.saved') })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
  }
}

function confirmDeleteController(ctrl) {
  $q.dialog({
    title: t('common.confirm'),
    message: t('warehouseLeds.confirmDeleteController', { id: ctrl.controller_id }),
    cancel: t('common.cancel'),
    ok: t('common.delete'),
    persistent: true,
  }).onOk(async () => {
    await store.deleteController(ctrl.id)
    $q.notify({ type: 'positive', message: t('common.deleted') })
  })
}

async function openControllerZones(ctrl) {
  zoneController.value = ctrl
  try {
    const zones = await api.get('/api/v1/inventory/zones')
    availableZones.value = zones.data
  } catch { availableZones.value = [] }
  try {
    const assignments = await store.fetchControllerZones(ctrl.id)
    selectedZones.value = assignments.map(a => a.zone_id)
  } catch { selectedZones.value = [] }
  zoneDialogOpen.value = true
}

async function onSaveZones() {
  try {
    await store.setControllerZones(zoneController.value.id, selectedZones.value)
    zoneDialogOpen.value = false
    $q.notify({ type: 'positive', message: t('common.saved') })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
  }
}

function openCreateMapping() {
  editingMapping.value = null
  Object.assign(mappingForm, { controller_id: null, bin_label: '', shelf_label: '', pixel_start: 0, pixel_end: 0, default_color: '#FF6600', zone_id: null })
  mappingDialogOpen.value = true
}

function openEditMapping(m) {
  editingMapping.value = m
  Object.assign(mappingForm, {
    controller_id: m.controller_id,
    bin_label: m.bin_label,
    shelf_label: m.shelf_label || '',
    pixel_start: m.pixel_start,
    pixel_end: m.pixel_end,
    default_color: m.default_color,
    zone_id: m.zone_id,
  })
  mappingDialogOpen.value = true
}

async function onSaveMapping() {
  try {
    if (editingMapping.value) {
      await store.updateMapping(editingMapping.value.id, { ...mappingForm })
    } else {
      await store.createMapping({ ...mappingForm })
    }
    mappingDialogOpen.value = false
    $q.notify({ type: 'positive', message: t('common.saved') })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
  }
}

function confirmDeleteMapping(m) {
  $q.dialog({
    title: t('common.confirm'),
    message: t('warehouseLeds.confirmDeleteMapping', { bin: m.bin_label }),
    cancel: t('common.cancel'),
    ok: t('common.delete'),
    persistent: true,
  }).onOk(async () => {
    await store.deleteMapping(m.id)
    $q.notify({ type: 'positive', message: t('common.deleted') })
  })
}

async function onLocateDevice() {
  if (!locateDeviceId.value) return
  try {
    const result = await store.locateDevice(locateDeviceId.value)
    $q.notify({ type: 'positive', message: t('warehouseLeds.locateSuccess', { tag: result.asset_tag }) })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
  }
}

async function onShowReturn() {
  if (!returnZoneId.value) return
  try {
    await store.showReturnLocation(returnZoneId.value)
    $q.notify({ type: 'positive', message: t('warehouseLeds.returnShown') })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
  }
}

async function onHighlightJob() {
  if (!highlightJobId.value) return
  try {
    const result = await store.highlightJob(highlightJobId.value)
    $q.notify({ type: 'positive', message: t('warehouseLeds.jobHighlighted', { count: result.bins_highlighted }) })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
  }
}

async function onClearAll() {
  try {
    await store.clearAll()
    $q.notify({ type: 'positive', message: t('warehouseLeds.allCleared') })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
  }
}

async function onIdentifyAll() {
  try {
    await store.identifyAll()
    $q.notify({ type: 'positive', message: t('warehouseLeds.allIdentified') })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
  }
}

async function downloadYaml(ctrl) {
  try {
    const result = await store.getEspHomeYaml(ctrl.controller_id)
    yamlPreview.value = result.yaml
    const blob = new Blob([result.yaml], { type: 'text/yaml' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = result.filename
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    $q.notify({ type: 'negative', message: err.message })
  }
}

async function onDownloadYaml() {
  if (!esphomeController.value) return
  const ctrl = controllers.value.find(c => c.controller_id === esphomeController.value)
  if (ctrl) await downloadYaml(ctrl)
}

async function onDownloadSecretsTemplate() {
  try {
    const result = await store.getEspHomeSecretsTemplate()
    const blob = new Blob([result.yaml], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = result.filename
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    $q.notify({ type: 'negative', message: err.message })
  }
}

onMounted(async () => {
  await Promise.all([store.fetchControllers(), store.fetchMappings()])
})
</script>
