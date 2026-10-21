<template>
  <q-page class="q-pa-md labels-page">
    <div class="ec-page-title q-mb-md">{{ t('app.nav.labels') }}</div>
    <div class="row items-center q-col-gutter-sm q-mb-md">
      <div class="col-12 col-md-3">
        <q-select v-model="selectedTemplateId" :options="templateOptions" :label="t('labels.template')" outlined dense emit-value map-options clearable @update:model-value="loadTemplate" />
      </div>
      <div class="col-12 col-md-2">
        <q-input v-model="templateName" :label="t('labels.templateName')" outlined dense />
      </div>
      <div class="col-12 col-md-2">
        <q-select
          :model-value="printPreset"
          :options="printPresetOptions"
          :label="t('labels.printPreset')"
          outlined
          dense
          emit-value
          map-options
          @update:model-value="(v) => { printPreset = v; applyCanvasFromPreset() }"
        />
      </div>
      <div class="col-12 col-md-2">
        <q-select v-model="printerProfile" :options="printerProfileOptions" :label="t('labels.printer')" outlined dense emit-value map-options />
      </div>
      <div class="col-12 col-md-2">
        <q-select v-model="templateVisibility" :options="visibilityOptions" :label="t('labels.visibility')" outlined dense emit-value map-options />
      </div>
      <div class="col-auto">
        <q-btn color="primary" icon="save" :label="t('labels.save')" unelevated @click="saveTemplate" />
      </div>
      <div class="col-auto">
        <q-btn :color="newTemplateButtonColor" :text-color="newTemplateButtonTextColor" icon="add" :label="t('labels.new')" unelevated @click="resetTemplate" />
      </div>
      <div class="col-auto">
        <q-btn color="secondary" icon="auto_awesome" :label="t('labels.loadPreset')" unelevated @click="presetDialogOpen = true" />
      </div>
      <div class="col-auto" v-if="selectedTemplateId && canEditSelectedTemplate">
        <q-btn color="negative" icon="delete" :label="t('labels.delete')" flat @click="deleteTemplate" />
      </div>
      <div class="col-auto">
        <q-btn color="positive" icon="print" :label="t('labels.print')" unelevated :disable="!selectedRows.length" @click="printLabels" />
      </div>
      <div class="col-auto">
        <q-btn
          v-if="webUSBSupported"
          :color="printerConnected ? 'positive' : 'secondary'"
          :icon="printerConnected ? 'usb' : 'link'"
          :label="printerConnected ? t('labels.brotherConnected') : t('labels.brotherConnect')"
          unelevated
          :loading="connectingPrinter"
          @click="togglePrinterConnection"
        />
      </div>
      <div class="col-auto" v-if="printerConnected">
        <q-btn
          color="positive"
          icon="printer"
          :label="t('labels.directPrint')"
          unelevated
          :disable="!selectedRows.length"
          :loading="directPrinting"
          @click="directPrintLabels"
        />
      </div>
      <div class="col-auto" v-if="printerConnected">
        <q-btn
          outline
          color="primary"
          icon="straighten"
          :label="t('labels.calibrationPrint')"
          :loading="directPrinting"
          @click="directPrintLabels({ calibration: true })"
        />
      </div>
      <div class="col-auto" v-if="printerConnected">
        <q-toggle
          v-model="cutLabels"
          :label="t('labels.cutLabels')"
          dense
        >
          <q-tooltip>{{ t('labels.cutInfo') }}</q-tooltip>
        </q-toggle>
      </div>
      <div class="col-auto" v-if="printerConnected">
        <q-btn
          flat
          icon="straighten"
          :label="t('labels.loadPrinterMedia')"
          @click="loadPrinterMedia"
        />
      </div>
      <div class="col-auto" v-if="printerConnected">
        <q-btn
          flat
          icon="build"
          :label="t('labels.diagnosePrinter')"
          @click="diagnosePrinter"
        />
      </div>
      <div class="col-auto self-center" v-if="printerConnected && detectedMedia && detectedMedia.widthMm">
        <span class="text-caption text-grey-7">
          {{ t('labels.detectedMedia', { width: detectedMedia.widthMm, length: detectedMedia.heightMm, name: detectedMedia.name }) }}
        </span>
      </div>
    </div>

    <div class="row q-col-gutter-md">
      <div class="col-12 col-lg-3">
        <q-card class="ec-card q-mb-md">
          <q-card-section>
            <div class="text-subtitle1">{{ t('labels.dataSource') }}</div>
          </q-card-section>
          <q-card-section class="q-pt-none">
            <q-select v-model="entityType" :options="entityTypeOptions" :label="t('labels.entity')" outlined dense emit-value map-options class="q-mb-sm" />
            <q-select
              v-model="selectedEntityIds"
              :options="entityOptions"
              :label="t('labels.selectOneOrMany')"
              outlined
              dense
              use-input
              input-debounce="0"
              clearable
              multiple
              emit-value
              map-options
              @filter="filterEntityOptions"
            />
            <div class="text-caption text-grey-7 q-mt-sm">{{ t('labels.selectedCount', { count: selectedRows.length }) }}</div>
          </q-card-section>
        </q-card>

        <q-card class="ec-card">
          <q-card-section>
            <div class="text-subtitle1">{{ t('labels.templatePermissions') }}</div>
          </q-card-section>
          <q-card-section class="q-pt-none">
            <q-option-group v-model="templateEditRoles" :options="editRoleOptions" type="checkbox" color="primary" />
            <div class="text-caption text-grey-7 q-mt-sm">{{ t('labels.templatePermissionsHelp') }}</div>
          </q-card-section>
        </q-card>

        <q-card class="ec-card q-mt-md">
          <q-card-section>
            <div class="text-subtitle1">{{ t('labels.availableFields') }}</div>
            <div class="text-caption text-grey-7">{{ t('labels.availableFieldsHelp') }}</div>
          </q-card-section>
          <q-card-section class="q-pt-none">
            <div class="text-caption text-grey-6 q-mb-xs">{{ t('labels.entityFields') }}</div>
            <div class="row q-gutter-xs q-mb-sm">
              <q-chip v-for="field in entityFieldKeys" :key="field" draggable="true" color="blue-1" text-color="blue-10" @dragstart="onFieldDragStart($event, field)">{{ field }}</q-chip>
            </div>
            <div class="text-caption text-grey-6 q-mb-xs">{{ t('labels.businessSettingsFields') }}</div>
            <div class="row q-gutter-xs q-mb-sm">
              <q-chip v-for="field in businessFieldKeys" :key="field" draggable="true" color="teal-1" text-color="teal-10" @dragstart="onFieldDragStart($event, field)">{{ field }}</q-chip>
            </div>
            <div class="text-caption text-grey-6 q-mb-xs">{{ t('labels.businessLogos') }}</div>
            <div class="row q-gutter-xs">
              <q-chip
                v-for="logoField in logoImageFields"
                :key="logoField.source"
                draggable="true"
                color="amber-1"
                text-color="amber-10"
                @dragstart="onFieldDragStart($event, logoField.source)"
              >
                <q-avatar square>
                  <img v-if="logoField.previewUrl" :src="logoField.previewUrl" alt="Logo" />
                  <span v-else class="text-caption">{{ t('labels.logoShort') }}</span>
                </q-avatar>
                {{ logoField.label }}
              </q-chip>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <div class="col-12 col-lg-6">
        <q-card class="ec-card">
          <q-card-section class="row items-center q-col-gutter-sm">
            <div class="col-auto text-subtitle1">{{ t('labels.editorTitle') }}</div>
            <div class="col-auto"><q-input v-model.number="canvas.width" type="number" min="120" :label="t('labels.canvasW')" dense outlined style="width: 110px" /></div>
            <div class="col-auto"><q-input v-model.number="canvas.height" type="number" min="80" :label="t('labels.canvasH')" dense outlined style="width: 110px" /></div>
            <div class="col-auto"><q-toggle v-model="previewMode" dense :label="t('labels.previewValues')" /></div>
            <div class="col-auto"><q-toggle v-model="snapToGrid" dense :label="t('labels.snap')" /></div>
            <div class="col-auto"><q-input v-model.number="gridSize" type="number" min="2" max="64" :label="t('labels.grid')" dense outlined style="width: 90px" /></div>
            <div class="col-auto"><q-btn flat dense icon="straighten" :label="t('labels.presetToCanvas')" @click="applyCanvasFromPreset" /></div>
            <div class="col-auto"><q-input v-model.number="customCanvasMm.width" type="number" min="10" step="0.1" label="W mm" dense outlined style="width: 86px" /></div>
            <div class="col-auto"><q-input v-model.number="customCanvasMm.height" type="number" min="10" step="0.1" label="H mm" dense outlined style="width: 86px" /></div>
            <div class="col-auto"><q-btn flat dense icon="crop_free" :label="t('labels.applyMm')" @click="applyCanvasFromCustomMm" /></div>
            <div class="col-auto"><q-toggle :model-value="wideLabel" :label="t('labels.wideLabel')" dense @update:model-value="(v) => { wideLabel = v; applyCanvasFromPreset() }" /></div>
            <div class="col-auto text-caption text-grey-7">{{ t('labels.editorHintArrows') }}</div>
            <div class="col-auto text-caption text-grey-7">{{ t('labels.editorPixels') }}</div>
          </q-card-section>
          <q-separator />
          <q-card-section>
            <div
              ref="canvasRef"
              class="label-canvas"
              :style="canvasStyle"
              tabindex="0"
              @dragover.prevent
              @drop.prevent="onCanvasDrop"
              @keydown="onCanvasKeydown"
              @click="focusCanvas"
            >
              <div v-for="x in guideState.vertical" :key="`guide-v-${x}`" class="label-guide-vertical" :style="{ left: `${x}px` }"></div>
              <div v-for="y in guideState.horizontal" :key="`guide-h-${y}`" class="label-guide-horizontal" :style="{ top: `${y}px` }"></div>
              <div
                v-for="item in templateElements"
                :key="item.id"
                class="label-item"
                :class="{ selected: selectedElementId === item.id }"
                :style="itemStyle(item)"
                @click.stop="selectedElementId = item.id"
                @mousedown="startDragElement($event, item.id)"
              >
                <template v-if="previewMode">
                  <div v-if="item.kind === 'logo'" class="preview-logo-wrap">
                    <img v-if="resolveLogoUrlForElement(item)" :src="resolveLogoUrlForElement(item)" alt="Logo" class="preview-logo" />
                    <div v-else class="text-caption text-grey-7">{{ t('labels.logo') }}</div>
                  </div>
                  <div v-else-if="item.kind === 'barcode'" class="preview-barcode" v-html="barcodePreviewById[item.id] || ''"></div>
                  <div v-else-if="item.kind === 'qrcode'" class="preview-qrcode-wrap">
                    <img v-if="qrcodePreviewById[item.id]" :src="qrcodePreviewById[item.id]" alt="QR" class="preview-qrcode" />
                    <div v-else class="text-caption text-grey-7 truncate">{{ t('labels.qrShort') }} {{ previewValue(item) }}</div>
                  </div>
                  <div v-else class="truncate">{{ previewValue(item) }}</div>
                </template>
                <template v-else>
                  <div v-if="item.kind === 'text'" class="truncate">{{ item.text || t('labels.text') }}</div>
                  <div v-else-if="item.kind === 'barcode'" class="text-caption text-grey-7">{{ t('labels.barcode') }} {{ item.source }}</div>
                  <div v-else-if="item.kind === 'qrcode'" class="text-caption text-grey-7">{{ t('labels.qrShort') }} {{ item.source }}</div>
                  <div v-else-if="item.kind === 'logo'" class="text-caption text-grey-7">{{ t('labels.logo') }}</div>
                  <div v-else class="truncate">{{ item.source }}</div>
                </template>

                <template v-if="selectedElementId === item.id">
                  <div class="resize-handle resize-handle-nw" @mousedown.stop.prevent="startResizeElement($event, item.id, 'nw')"></div>
                  <div class="resize-handle resize-handle-n" @mousedown.stop.prevent="startResizeElement($event, item.id, 'n')"></div>
                  <div class="resize-handle resize-handle-ne" @mousedown.stop.prevent="startResizeElement($event, item.id, 'ne')"></div>
                  <div class="resize-handle resize-handle-e" @mousedown.stop.prevent="startResizeElement($event, item.id, 'e')"></div>
                  <div class="resize-handle resize-handle-se" @mousedown.stop.prevent="startResizeElement($event, item.id, 'se')"></div>
                  <div class="resize-handle resize-handle-s" @mousedown.stop.prevent="startResizeElement($event, item.id, 's')"></div>
                  <div class="resize-handle resize-handle-sw" @mousedown.stop.prevent="startResizeElement($event, item.id, 'sw')"></div>
                  <div class="resize-handle resize-handle-w" @mousedown.stop.prevent="startResizeElement($event, item.id, 'w')"></div>
                </template>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <div class="col-12 col-lg-3">
        <q-card class="ec-card">
          <q-card-section>
            <div class="text-subtitle1">{{ t('labels.elementSettings') }}</div>
          </q-card-section>
          <q-card-section v-if="selectedElement" class="q-pt-none">
            <q-select v-model="selectedElement.kind" :options="elementKindOptions" :label="t('labels.type')" dense outlined emit-value map-options class="q-mb-sm" />
            <q-input v-if="selectedElement.kind === 'text'" v-model="selectedElement.text" :label="t('labels.text')" dense outlined class="q-mb-sm" />
            <q-select
              v-if="selectedElement.kind !== 'text' && selectedElement.kind !== 'logo'"
              v-model="selectedElement.source"
              :options="sourceOptions"
              :label="t('labels.dataField')"
              dense
              outlined
              use-input
              input-debounce="0"
              emit-value
              map-options
              @filter="filterSourceOptions"
              class="q-mb-sm"
            />
            <div class="row q-col-gutter-sm">
              <div class="col-6"><q-input v-model.number="selectedElement.x" type="number" :label="t('labels.x')" dense outlined /></div>
              <div class="col-6"><q-input v-model.number="selectedElement.y" type="number" :label="t('labels.y')" dense outlined /></div>
              <div class="col-6"><q-input v-model.number="selectedElement.w" type="number" :label="t('labels.w')" dense outlined /></div>
              <div class="col-6"><q-input v-model.number="selectedElement.h" type="number" :label="t('labels.h')" dense outlined /></div>
              <div class="col-6"><q-input v-model.number="selectedElement.fontSize" type="number" :label="t('labels.font')" dense outlined /></div>
            </div>
            <div class="row q-gutter-sm q-mt-sm">
              <q-btn :color="duplicateButtonColor" :text-color="duplicateButtonTextColor" icon="content_copy" :label="t('labels.duplicate')" unelevated @click="duplicateElement" />
              <q-btn flat color="negative" icon="delete" :label="t('labels.remove')" @click="removeSelectedElement" />
            </div>
          </q-card-section>
          <q-card-section v-else class="q-pt-none text-grey-7 text-caption">
            {{ t('labels.selectElementToEdit') }}
          </q-card-section>
        </q-card>
      </div>
    </div>

    <q-dialog v-model="presetDialogOpen" persistent>
      <q-card style="min-width: 400px" class="ec-card">
        <q-card-section>
          <div class="text-h6">{{ t('labels.loadPreset') }}</div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-select
            v-model="selectedPresetKey"
            :options="presetOptions"
            :label="t('labels.selectPreset')"
            outlined
            dense
            emit-value
            map-options
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="presetDialogOpen = false" />
          <q-btn color="primary" unelevated :label="t('app.actions.load')" :disable="!selectedPresetKey" @click="loadPresetTemplate(selectedPresetKey)" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useInventoryStore } from '../stores/inventory'
import { useSettingsStore } from '../stores/settings'
import { useAuthStore } from '../stores/auth'
import {
  isWebUSBSupported,
  connectPrinter,
  disconnectPrinter,
  getPrinter,
  getDetectedMedia,
  readDetectedMedia,
  getPrinterStatus,
} from '../utils/brother-print'
import {
  PRINT_PRESETS,
  buildRowsByEntityType,
  getPreset,
  normalizeElement,
  orientedDims,
  printRowsBrowser,
  printRowsDirect,
  resolveLogoUrl,
  resolveLogoUrlBySource,
  resolveLogoUrlForElement,
  resolveValue,
  barcodeSvg,
  qrDataUrl,
} from '../utils/labelPrint'

const inventoryStore = useInventoryStore()
const settingsStore = useSettingsStore()
const authStore = useAuthStore()
const $q = useQuasar()
const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const BROTHER_QL560_HINT = computed(() => t('labels.brotherHint'))

  const PRINTER_PROFILES = {
    auto: { key: 'auto' },
    brother_ql560: { key: 'brother_ql560' },
  }


const canvasRef = ref(null)
const entityType = ref('device')
const selectedEntityIds = ref([])
const entityOptions = ref([])
const sourceOptions = ref([])
const templateName = ref('')
const selectedTemplateId = ref(null)
const templateElements = ref([])
const selectedElementId = ref(null)
const dragPayload = ref(null)
const dragState = ref(null)
const resizeState = ref(null)
const printPreset = ref('62x29')
const printerProfile = ref('auto')
const templateVisibility = ref('all')
const templateEditRoles = ref(['admin', 'manager'])
const canvas = ref({ width: 420, height: 280 })
const previewMode = ref(true)
const snapToGrid = ref(true)
const gridSize = ref(8)
const guideState = ref({ vertical: [], horizontal: [] })
const customCanvasMm = ref({ width: 62, height: 29 })
const qrcodePreviewById = ref({})
const barcodePreviewById = ref({})

const webUSBSupported = isWebUSBSupported()
const printerConnected = ref(false)
const connectingPrinter = ref(false)
const directPrinting = ref(false)
const cutLabels = ref(true)
const detectedMedia = ref(null)
const printerPreset = ref(null)
const wideLabel = ref(false)

  const printPresetOptions = computed(() => {
  const options = [
    { label: t('labels.preset62x29'), value: '62x29' },
    { label: t('labels.preset62x100'), value: '62x100' },
    { label: t('labels.preset50x25'), value: '50x25' },
    { label: t('labels.presetA43x8'), value: 'a4-3x8' },
  ]
  // Include any size preset registered at runtime (e.g. a size detected from
  // the printer), so it can be selected and saved like a built-in preset.
  for (const preset of Object.values(PRINT_PRESETS)) {
    if (!options.some(o => o.value === preset.key)) {
      options.push({
        label: `${Math.round(preset.labelW)}×${Math.round(preset.labelH)} mm`,
        value: preset.key,
      })
    }
  }
  return options
})
const printerProfileOptions = computed(() => [
  { label: t('labels.printerAuto'), value: 'auto' },
  { label: t('labels.printerBrotherQl560'), value: 'brother_ql560' },
])
const entityTypeOptions = computed(() => [
  { label: t('labels.entitiesDevices'), value: 'device' },
  { label: t('labels.entitiesProducts'), value: 'product' },
  { label: t('labels.entitiesLocations'), value: 'location' },
  { label: t('labels.entitiesCases'), value: 'case' },
])
const visibilityOptions = computed(() => [
  { label: t('labels.visibilityAllUsers'), value: 'all' },
  { label: t('labels.visibilityAdminsOnly'), value: 'admin' },
  { label: t('labels.visibilityOwnerOnly'), value: 'owner' },
])
const editRoleOptions = computed(() => [
  { label: t('labels.roleAdmin'), value: 'admin' },
  { label: t('labels.roleManager'), value: 'manager' },
  { label: t('labels.roleViewer'), value: 'viewer' },
])
const elementKindOptions = computed(() => [
  { label: t('labels.kindFieldText'), value: 'field' },
  { label: t('labels.kindStaticText'), value: 'text' },
  { label: t('labels.kindBarcode'), value: 'barcode' },
  { label: t('labels.kindQrCode'), value: 'qrcode' },
  { label: t('labels.kindBusinessLogo'), value: 'logo' },
])
const newTemplateButtonColor = computed(() => ($q.dark.isActive ? 'amber-5' : 'secondary'))
const newTemplateButtonTextColor = computed(() => ($q.dark.isActive ? 'black' : 'white'))
const duplicateButtonColor = computed(() => ($q.dark.isActive ? 'amber-4' : 'secondary'))
const duplicateButtonTextColor = computed(() => ($q.dark.isActive ? 'black' : 'white'))

const templateOptions = computed(() => (settingsStore.labelTemplates || []).map(item => ({ label: item.name, value: item.id })))

const canEditSelectedTemplate = computed(() => {
  const selected = (settingsStore.labelTemplates || []).find(item => item.id === selectedTemplateId.value)
  if (!selected) return false
  const meRole = String(authStore.me?.role || '').toLowerCase()
  const meId = Number(authStore.me?.id || 0)
  if (meRole === 'admin') return true
  if (Number(selected.created_by_user_id || 0) > 0 && Number(selected.created_by_user_id || 0) === meId) return true
  const roles = Array.isArray(selected.edit_roles) ? selected.edit_roles.map(v => String(v || '').toLowerCase()) : []
  return roles.includes(meRole)
})

const selectedElement = computed(() => templateElements.value.find(item => item.id === selectedElementId.value) || null)

const canvasStyle = computed(() => ({
  width: `${Math.max(120, Number(canvas.value.width || 0))}px`,
  height: `${Math.max(80, Number(canvas.value.height || 0))}px`,
}))

const businessFieldKeys = computed(() => {
  const profile = settingsStore.companyProfile || {}
  return Object.keys(profile).map(key => `business.${key}`).sort((a, b) => a.localeCompare(b))
})

const rowsByEntityType = computed(() => buildRowsByEntityType())

const currentRows = computed(() => rowsByEntityType.value[entityType.value] || [])
const selectedRows = computed(() => {
  const ids = new Set((selectedEntityIds.value || []).map(Number))
  return currentRows.value.filter(item => ids.has(Number(item.id)))
})

const activePreviewRow = computed(() => selectedRows.value[0] || currentRows.value[0] || null)

const entityFieldKeys = computed(() => {
  const keys = new Set()
  for (const row of currentRows.value.slice(0, 120)) {
    for (const [key, value] of Object.entries(row || {})) {
      if (value == null || ['string', 'number', 'boolean'].includes(typeof value)) keys.add(key)
      if (key === 'custom_fields' && value && typeof value === 'object') {
        for (const cKey of Object.keys(value)) {
          keys.add(`custom_fields.${cKey}`)
        }
      }
    }
  }
  // Expose the parent product and current zone properties on device (and case)
  // labels so users can place any of them via dot-path sources like
  // `product.sku` or `zone.name`.
  if (entityType.value === 'device' || entityType.value === 'case') {
    const sampleProduct = (inventoryStore.products || [])[0]
    if (sampleProduct) {
      for (const [key, value] of Object.entries(sampleProduct)) {
        if (value == null || ['string', 'number', 'boolean'].includes(typeof value)) {
          keys.add(`product.${key}`)
        }
      }
    }
    const sampleZone = (inventoryStore.zones || [])[0]
    if (sampleZone) {
      for (const [key, value] of Object.entries(sampleZone)) {
        if (value == null || ['string', 'number', 'boolean'].includes(typeof value)) {
          keys.add(`zone.${key}`)
        }
      }
    }
  }
  return [...keys].sort((a, b) => a.localeCompare(b))
})

function defaultSourceField() {
  return entityFieldKeys.value[0] || 'id'
}

function resetTemplate() {
  selectedTemplateId.value = null
  templateName.value = ''
  templateElements.value = [normalizeElement({ source: defaultSourceField() })]
  selectedElementId.value = templateElements.value[0]?.id || null
  printPreset.value = '62x29'
  wideLabel.value = false
  templateVisibility.value = 'all'
  templateEditRoles.value = ['admin', 'manager']
  applyCanvasFromPreset()
}

const PRESET_TEMPLATES = {
  device_simple: {
    name: 'Device — Simple',
    entity_type: 'device',
    print_preset: '62x29',
    canvas: { width: 732, height: 343 },
    elements: [
      { kind: 'field', source: 'asset_tag', x: 5, y: 5, w: 90, h: 12, fontSize: 14 },
      { kind: 'barcode', source: 'asset_tag', x: 5, y: 22, w: 90, h: 20 },
      { kind: 'field', source: 'product.name', x: 5, y: 48, w: 90, h: 8, fontSize: 8 },
      { kind: 'field', source: 'product.sku', x: 5, y: 58, w: 90, h: 8, fontSize: 8 },
    ],
  },
  device_detailed: {
    name: 'Device — Detailed',
    entity_type: 'device',
    print_preset: '62x100',
    canvas: { width: 732, height: 1181 },
    elements: [
      { kind: 'field', source: 'asset_tag', x: 5, y: 5, w: 90, h: 12, fontSize: 16 },
      { kind: 'barcode', source: 'asset_tag', x: 5, y: 22, w: 90, h: 25 },
      { kind: 'field', source: 'product.name', x: 5, y: 52, w: 90, h: 10, fontSize: 10 },
      { kind: 'field', source: 'product.sku', x: 5, y: 65, w: 90, h: 8, fontSize: 8 },
      { kind: 'field', source: 'serial_number', x: 5, y: 78, w: 90, h: 8, fontSize: 8 },
      { kind: 'field', source: 'location_name', x: 5, y: 91, w: 90, h: 8, fontSize: 8 },
      { kind: 'logo', source: 'logo_default', x: 5, y: 105, w: 25, h: 8 },
    ],
  },
  product_simple: {
    name: 'Product — Simple',
    entity_type: 'product',
    print_preset: '62x29',
    canvas: { width: 732, height: 343 },
    elements: [
      { kind: 'field', source: 'name', x: 5, y: 5, w: 90, h: 12, fontSize: 12 },
      { kind: 'barcode', source: 'sku', x: 5, y: 22, w: 90, h: 20 },
      { kind: 'field', source: 'sku', x: 5, y: 48, w: 90, h: 8, fontSize: 8 },
    ],
  },
  product_pricing: {
    name: 'Product — With Pricing',
    entity_type: 'product',
    print_preset: '62x100',
    canvas: { width: 732, height: 1181 },
    elements: [
      { kind: 'field', source: 'name', x: 5, y: 5, w: 90, h: 14, fontSize: 14 },
      { kind: 'barcode', source: 'sku', x: 5, y: 24, w: 90, h: 25 },
      { kind: 'field', source: 'sku', x: 5, y: 54, w: 90, h: 8, fontSize: 8 },
      { kind: 'field', source: 'category', x: 5, y: 68, w: 90, h: 8, fontSize: 8 },
      { kind: 'field', source: 'daily_rate', x: 5, y: 82, w: 45, h: 10, fontSize: 12 },
      { kind: 'field', source: 'replace_cost', x: 50, y: 82, w: 45, h: 10, fontSize: 10 },
    ],
  },
  location_simple: {
    name: 'Location — Simple',
    entity_type: 'location',
    print_preset: '62x29',
    canvas: { width: 732, height: 343 },
    elements: [
      { kind: 'field', source: 'name', x: 5, y: 5, w: 90, h: 14, fontSize: 16 },
      { kind: 'barcode', source: 'code', x: 5, y: 24, w: 90, h: 20 },
    ],
  },
  location_detailed: {
    name: 'Location — With Zone',
    entity_type: 'location',
    print_preset: '62x100',
    canvas: { width: 732, height: 1181 },
    elements: [
      { kind: 'field', source: 'name', x: 5, y: 5, w: 90, h: 14, fontSize: 16 },
      { kind: 'barcode', source: 'code', x: 5, y: 24, w: 90, h: 25 },
      { kind: 'field', source: 'code', x: 5, y: 54, w: 90, h: 10, fontSize: 10 },
      { kind: 'field', source: 'zone_name', x: 5, y: 70, w: 90, h: 10, fontSize: 10 },
    ],
  },
}

const presetDialogOpen = ref(false)
const selectedPresetKey = ref(null)
const presetOptions = computed(() =>
  Object.entries(PRESET_TEMPLATES).map(([key, tpl]) => ({
    label: tpl.name,
    value: key,
  }))
)

function loadPresetTemplate(presetKey) {
  const preset = PRESET_TEMPLATES[presetKey]
  if (!preset) return
  selectedTemplateId.value = null
  templateName.value = preset.name
  entityType.value = preset.entity_type
  printPreset.value = preset.print_preset
  canvas.value = { ...preset.canvas }
  wideLabel.value = Number(preset.canvas?.height || 0) > Number(preset.canvas?.width || 0)
  templateElements.value = preset.elements.map(el => normalizeElement({ ...el }))
  selectedElementId.value = templateElements.value[0]?.id || null
  presetDialogOpen.value = false
}

function loadTemplate(templateId) {
  const selected = (settingsStore.labelTemplates || []).find(item => item.id === templateId)
  if (!selected) return
  selectedTemplateId.value = selected.id
  templateName.value = selected.name || ''
  entityType.value = selected.entity_type || 'device'
  printPreset.value = selected.print_preset || '62x29'
  templateVisibility.value = selected.visibility || 'all'
  templateEditRoles.value = Array.isArray(selected.edit_roles) && selected.edit_roles.length ? [...selected.edit_roles] : ['admin', 'manager']
  canvas.value = {
    width: Number(selected.canvas?.width || 420),
    height: Number(selected.canvas?.height || 280),
  }
  // Restore the saved orientation so the design opens exactly as it was saved
  // instead of defaulting back to landscape and forcing a manual toggle.
  wideLabel.value = Boolean(selected.wide_label) || (Number(selected.canvas?.height || 0) > Number(selected.canvas?.width || 0))
  templateElements.value = Array.isArray(selected.elements) ? selected.elements.map(normalizeElement) : []
  if (!templateElements.value.length) {
    templateElements.value = [normalizeElement({ source: defaultSourceField() })]
  }
  selectedElementId.value = templateElements.value[0]?.id || null
}

async function saveTemplate() {
  const name = String(templateName.value || '').trim()
  if (!name) return
  const payload = {
    name,
    entity_type: entityType.value,
    print_preset: printPreset.value,
    wide_label: Boolean(wideLabel.value),
    visibility: templateVisibility.value,
    edit_roles: templateEditRoles.value,
    canvas: { ...canvas.value },
    elements: templateElements.value.map(item => ({ ...item })),
  }

  try {
    if (selectedTemplateId.value) {
      const saved = await settingsStore.updateLabelTemplate(selectedTemplateId.value, payload)
      selectedTemplateId.value = saved?.id || selectedTemplateId.value
    } else {
      const created = await settingsStore.createLabelTemplate(payload)
      selectedTemplateId.value = created?.id || null
    }
    await settingsStore.fetchLabelTemplates()
    $q.notify({ type: 'positive', message: t('labels.saveSuccess'), timeout: 2500 })
  } catch (err) {
    const detail = err?.response?.data?.detail
    const msg = Array.isArray(detail)
      ? detail.map(d => `${d.loc?.slice(1)?.join('.') || 'field'}: ${d.msg}`).join('; ')
      : (detail || err?.message || err)
    $q.notify({ type: 'negative', message: `${t('labels.saveFailed')}: ${msg}`, timeout: 8000 })
  }
}

async function deleteTemplate() {
  if (!selectedTemplateId.value) return
  await settingsStore.deleteLabelTemplate(selectedTemplateId.value)
  selectedTemplateId.value = null
  resetTemplate()
}

function itemStyle(item) {
  return {
    left: `${Math.max(0, Number(item.x || 0))}px`,
    top: `${Math.max(0, Number(item.y || 0))}px`,
    width: `${Math.max(20, Number(item.w || 0))}px`,
    height: `${Math.max(16, Number(item.h || 0))}px`,
    fontSize: `${Math.max(8, Number(item.fontSize || 12))}px`,
  }
}

function focusCanvas() {
  canvasRef.value?.focus?.()
}

function normalizedGridSize() {
  return Math.max(2, Math.min(64, Number(gridSize.value || 8)))
}

function mmToPx(valueMm) {
  const mm = Math.max(1, Number(valueMm || 0))
  return Math.max(1, Math.round(mm * 3.7795275591))
}

function applyCanvasSizeMm(widthMm, heightMm) {
  const w = Math.max(10, Number(widthMm || 0))
  const h = Math.max(10, Number(heightMm || 0))
  customCanvasMm.value = {
    width: Number(w.toFixed(2)),
    height: Number(h.toFixed(2)),
  }
  canvas.value = {
    width: mmToPx(w),
    height: mmToPx(h),
  }
}

 /**
  * Return the label dimensions for the current orientation. When `wideLabel`
  * is on, the width/height are swapped so the design area (and the printed
  * label) is landscape instead of portrait.
  */
  function applyCanvasFromPreset() {
    const preset = getPreset(printPreset.value)
    const { w, h } = orientedDims(preset.labelW, preset.labelH, wideLabel.value)
    applyCanvasSizeMm(w, h)
  }

function applyCanvasFromCustomMm() {
  applyCanvasSizeMm(customCanvasMm.value.width, customCanvasMm.value.height)
}

function snapValue(value) {
  if (!snapToGrid.value) return value
  const grid = normalizedGridSize()
  return Math.round(Number(value || 0) / grid) * grid
}

function applyElementBounds(item) {
  const minW = 20
  const minH = 16
  const maxW = Math.max(minW, Number(canvas.value.width || 420))
  const maxH = Math.max(minH, Number(canvas.value.height || 280))
  item.w = Math.max(minW, Math.min(maxW, Math.round(item.w || minW)))
  item.h = Math.max(minH, Math.min(maxH, Math.round(item.h || minH)))
  item.x = Math.max(0, Math.min(maxW - item.w, Math.round(item.x || 0)))
  item.y = Math.max(0, Math.min(maxH - item.h, Math.round(item.y || 0)))
}

function setGuidesForItem(item) {
  if (!item || !snapToGrid.value) {
    guideState.value = { vertical: [], horizontal: [] }
    return
  }
  const left = Math.max(0, Math.round(item.x || 0))
  const top = Math.max(0, Math.round(item.y || 0))
  const right = Math.max(0, Math.round((item.x || 0) + (item.w || 0)))
  const bottom = Math.max(0, Math.round((item.y || 0) + (item.h || 0)))
  guideState.value = {
    vertical: [left, right],
    horizontal: [top, bottom],
  }
}

function clearGuides() {
  guideState.value = { vertical: [], horizontal: [] }
}

function onCanvasKeydown(event) {
  if (!selectedElement.value) return
  const key = String(event.key || '')
  if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(key)) return
  event.preventDefault()

  const item = selectedElement.value
  const step = event.shiftKey ? 10 : 1
  const resizeMode = event.altKey
  const initialW = Number(item.w || 20)
  const initialH = Number(item.h || 16)
  const aspectRatio = initialW / Math.max(1, initialH)
  let deltaX = 0
  let deltaY = 0

  if (key === 'ArrowLeft') deltaX = -step
  if (key === 'ArrowRight') deltaX = step
  if (key === 'ArrowUp') deltaY = -step
  if (key === 'ArrowDown') deltaY = step

  if (resizeMode) {
    item.w = initialW + deltaX
    item.h = initialH + deltaY
    if (['qrcode', 'logo'].includes(item.kind)) {
      if (Math.abs(deltaX) >= Math.abs(deltaY)) {
        item.h = Number(item.w || 20) / Math.max(0.01, aspectRatio)
      } else {
        item.w = Number(item.h || 16) * Math.max(0.01, aspectRatio)
      }
    }
  } else {
    item.x = Number(item.x || 0) + deltaX
    item.y = Number(item.y || 0) + deltaY
  }

  item.x = snapValue(item.x)
  item.y = snapValue(item.y)
  item.w = snapValue(item.w)
  item.h = snapValue(item.h)
  applyElementBounds(item)
  setGuidesForItem(item)
}

function selectedIdsFromRows(rows) {
  return [...new Set((rows || []).map(row => Number(row?.id || 0)).filter(Boolean))]
}

function parseIdsFromQuery(value) {
  return String(value || '')
    .split(',')
    .map(token => Number(token.trim()))
    .filter(Number.isFinite)
    .filter(id => id > 0)
}

function queryFlagEnabled(value) {
  const normalized = String(value || '').trim().toLowerCase()
  return ['1', 'true', 'yes', 'y', 'on'].includes(normalized)
}

async function applyIncomingSelectionFromQuery() {
  const entity = String(route.query.entity || '').trim().toLowerCase()
  const ids = parseIdsFromQuery(route.query.ids)
  if (!entity || !ids.length) return
  if (!['product', 'device', 'location', 'case'].includes(entity)) return

  entityType.value = entity
  const validIds = new Set((rowsByEntityType.value[entity] || []).map(item => Number(item.id || 0)))
  selectedEntityIds.value = ids.filter(id => validIds.has(id))
  if (!selectedEntityIds.value.length) return

  // Pre-select a saved template when the caller specified one (e.g. the
  // inventory "Print labels" dialog), so the print uses a real design instead
  // of the blank default.
  const requestedTemplateId = String(route.query.templateId || '').trim()
  if (requestedTemplateId) {
    const match = (settingsStore.labelTemplates || []).find(item => item.id === requestedTemplateId)
    if (match && match.entity_type === entity) {
      selectedTemplateId.value = match.id
      loadTemplate(match.id)
    }
  }

  const nextQuery = { ...route.query }
  delete nextQuery.entity
  delete nextQuery.ids
  delete nextQuery.templateId
  await router.replace({ path: '/labels', query: nextQuery })
}

function previewValue(item) {
  if (item.kind === 'text') {
    return item.text || ''
  }
  if (item.kind === 'logo') {
    return settingsStore.companyProfile?.company_name || 'Logo'
  }
  if (!item.source) {
    return ''
  }
  return String(resolveValue(activePreviewRow.value, item.source) ?? '')
}

function inferFieldKind(field) {
  const key = String(field || '').trim().toLowerCase()
  if (key.includes('qrcode') || key.includes('qr_code') || key.endsWith('.qr') || key.endsWith('_qr')) return 'qrcode'
  if (key.includes('barcode') || key === 'ean' || key === 'upc') return 'barcode'
  if (key.includes('logo')) return 'logo'
  return 'field'
}

function onFieldDragStart(event, field) {
  dragPayload.value = { source: field, kind: inferFieldKind(field) }
  event.dataTransfer?.setData('application/json', JSON.stringify(dragPayload.value))
}

function onCanvasDrop(event) {
  if (!canvasRef.value) return
  let payload = dragPayload.value
  try {
    const raw = event.dataTransfer?.getData('application/json')
    if (raw) payload = JSON.parse(raw)
  } catch {
    // ignore malformed payload
  }
  if (!payload) return
  const rect = canvasRef.value.getBoundingClientRect()
  const el = normalizeElement({
    kind: payload.kind || 'field',
    source: payload.source || defaultSourceField(),
    x: event.clientX - rect.left - 60,
    y: event.clientY - rect.top - 12,
    w: payload.kind === 'qrcode' ? 92 : payload.kind === 'barcode' ? 140 : payload.kind === 'logo' ? 120 : 140,
    h: payload.kind === 'qrcode' ? 92 : payload.kind === 'barcode' ? 54 : payload.kind === 'logo' ? 44 : 30,
  })
  el.x = snapValue(el.x)
  el.y = snapValue(el.y)
  applyElementBounds(el)
  templateElements.value.push(el)
  selectedElementId.value = el.id
  setGuidesForItem(el)
}

function startDragElement(event, id) {
  if (resizeState.value) return
  const item = templateElements.value.find(el => el.id === id)
  if (!item || !canvasRef.value) return
  selectedElementId.value = id
  focusCanvas()
  const rect = canvasRef.value.getBoundingClientRect()
  dragState.value = {
    id,
    offsetX: event.clientX - rect.left - item.x,
    offsetY: event.clientY - rect.top - item.y,
  }
  window.addEventListener('mousemove', onElementMouseMove)
  window.addEventListener('mouseup', stopDragElement)
}

function startResizeElement(event, id, direction) {
  const item = templateElements.value.find(el => el.id === id)
  if (!item || !canvasRef.value) return
  selectedElementId.value = id
  focusCanvas()
  resizeState.value = {
    id,
    direction,
    startX: event.clientX,
    startY: event.clientY,
    startItem: {
      x: Number(item.x || 0),
      y: Number(item.y || 0),
      w: Number(item.w || 20),
      h: Number(item.h || 16),
    },
    aspectRatio: Number(item.w || 20) / Math.max(1, Number(item.h || 16)),
    keepAspect: ['qrcode', 'logo'].includes(item.kind),
  }
  window.addEventListener('mousemove', onElementResizeMove)
  window.addEventListener('mouseup', stopResizeElement)
}

function onElementResizeMove(event) {
  if (!resizeState.value) return
  const item = templateElements.value.find(el => el.id === resizeState.value.id)
  if (!item) return

  const { direction, startX, startY, startItem, aspectRatio, keepAspect } = resizeState.value
  const dx = event.clientX - startX
  const dy = event.clientY - startY
  const minW = 20
  const minH = 16
  const maxW = Math.max(minW, Number(canvas.value.width || 420))
  const maxH = Math.max(minH, Number(canvas.value.height || 280))

  let x = startItem.x
  let y = startItem.y
  let w = startItem.w
  let h = startItem.h

  if (direction.includes('e')) {
    w = startItem.w + dx
  }
  if (direction.includes('s')) {
    h = startItem.h + dy
  }
  if (direction.includes('w')) {
    x = startItem.x + dx
    w = startItem.w - dx
  }
  if (direction.includes('n')) {
    y = startItem.y + dy
    h = startItem.h - dy
  }

  if (keepAspect) {
    const ratio = Math.max(0.01, Number(aspectRatio || 1))
    const horizontalDriven = Math.abs(dx) >= Math.abs(dy)
    if (direction === 'e' || direction === 'w' || horizontalDriven) {
      h = w / ratio
      if (direction.includes('n')) {
        y = startItem.y + (startItem.h - h)
      }
    } else {
      w = h * ratio
      if (direction.includes('w')) {
        x = startItem.x + (startItem.w - w)
      }
    }
  }

  if (w < minW) {
    if (direction.includes('w')) {
      x -= (minW - w)
    }
    w = minW
  }
  if (h < minH) {
    if (direction.includes('n')) {
      y -= (minH - h)
    }
    h = minH
  }

  if (x < 0) {
    if (direction.includes('w')) {
      w += x
    }
    x = 0
  }
  if (y < 0) {
    if (direction.includes('n')) {
      h += y
    }
    y = 0
  }

  if (x + w > maxW) {
    if (direction.includes('w')) {
      x = maxW - w
    } else {
      w = maxW - x
    }
  }
  if (y + h > maxH) {
    if (direction.includes('n')) {
      y = maxH - h
    } else {
      h = maxH - y
    }
  }

  item.x = snapValue(Math.max(0, x))
  item.y = snapValue(Math.max(0, y))
  item.w = snapValue(Math.max(minW, w))
  item.h = snapValue(Math.max(minH, h))
  applyElementBounds(item)
  setGuidesForItem(item)
}

function stopResizeElement() {
  resizeState.value = null
  window.removeEventListener('mousemove', onElementResizeMove)
  window.removeEventListener('mouseup', stopResizeElement)
  clearGuides()
}

function onElementMouseMove(event) {
  if (!dragState.value || !canvasRef.value) return
  const item = templateElements.value.find(el => el.id === dragState.value.id)
  if (!item) return
  const rect = canvasRef.value.getBoundingClientRect()
  const maxX = Math.max(0, Number(canvas.value.width || 420) - Number(item.w || 20))
  const maxY = Math.max(0, Number(canvas.value.height || 280) - Number(item.h || 16))
  item.x = Math.max(0, Math.min(maxX, snapValue(event.clientX - rect.left - dragState.value.offsetX)))
  item.y = Math.max(0, Math.min(maxY, snapValue(event.clientY - rect.top - dragState.value.offsetY)))
  setGuidesForItem(item)
}

function stopDragElement() {
  dragState.value = null
  window.removeEventListener('mousemove', onElementMouseMove)
  window.removeEventListener('mouseup', stopDragElement)
  clearGuides()
}

function duplicateElement() {
  if (!selectedElement.value) return
  const clone = normalizeElement({ ...selectedElement.value, id: undefined, x: Number(selectedElement.value.x || 0) + 14, y: Number(selectedElement.value.y || 0) + 14 })
  templateElements.value.push(clone)
  selectedElementId.value = clone.id
}

function removeSelectedElement() {
  if (!selectedElement.value) return
  templateElements.value = templateElements.value.filter(item => item.id !== selectedElement.value.id)
  selectedElementId.value = templateElements.value[0]?.id || null
}

function filterEntityOptions(val, update) {
  const needle = String(val || '').trim().toLowerCase()
  update(() => {
    entityOptions.value = currentRows.value
      .filter((row) => {
        const search = [row.id, row.asset_tag, row.name, row.code, row.sku, row.barcode, row.qr_code, row.rfid]
          .map(v => String(v || '').toLowerCase())
          .join(' | ')
        return !needle || search.includes(needle)
      })
      .slice(0, 400)
      .map((row) => ({ label: row.asset_tag || row.name || row.code || row.sku || `#${row.id}`, value: row.id }))
  })
}

function filterSourceOptions(val, update) {
  const needle = String(val || '').trim().toLowerCase()
  const list = [...entityFieldKeys.value, ...businessFieldKeys.value]
  update(() => {
    sourceOptions.value = list
      .filter(item => !needle || item.toLowerCase().includes(needle))
      .map(item => ({ label: item, value: item }))
  })
}

async function printLabels() {
  if (!selectedRows.value.length || !templateElements.value.length) return
  const preset = getPreset(printPreset.value)
  if (printerProfile.value === 'brother_ql560') {
    $q.notify({ type: 'info', timeout: 7000, message: BROTHER_QL560_HINT.value })
  }
  await printRowsBrowser({
    rows: selectedRows.value,
    elements: templateElements.value,
    printPreset: printPreset.value,
    profileKey: printerProfile.value,
    canvasWpx: canvas.value.width,
    canvasHpx: canvas.value.height,
    brotherHint: BROTHER_QL560_HINT.value,
    notify: (m) => $q.notify(m),
  })
}

async function togglePrinterConnection() {
  if (printerConnected.value) {
    await disconnectPrinter()
    printerConnected.value = false
    $q.notify({ type: 'info', message: t('labels.brotherDisconnected') })
    return
  }
  connectingPrinter.value = true
  try {
    await connectPrinter()
    printerConnected.value = true
    detectedMedia.value = getDetectedMedia()
    $q.notify({ type: 'positive', message: t('labels.brotherConnected') })
  } catch (err) {
    if (err?.name !== 'NotFoundError') {
      $q.notify({ type: 'negative', message: t('labels.brotherConnectFailed') })
    }
  } finally {
    connectingPrinter.value = false
  }
}

async function loadPrinterMedia() {
  try {
    const media = await readDetectedMedia()
    if (media && media.widthMm) {
      detectedMedia.value = media
      // Prefer an existing preset that already matches the detected size;
      // otherwise register the detected size as a dynamic preset option so
      // the label can be resized to match the printer media.
      const match = Object.values(PRINT_PRESETS).find(
        (p) => p.labelW === media.widthMm && (media.heightMm === 0 || p.labelH === media.heightMm),
      )
      if (match) {
        printerPreset.value = null
        printPreset.value = match.key
        applyCanvasFromPreset()
      } else {
        const labelH = media.heightMm || customCanvasMm.value.height || 29
        // Register the detected size as a `WxH` preset (e.g. `38x90`) so it can
        // be selected and saved like a built-in preset.
        const sizeKey = `${Math.round(media.widthMm)}x${Math.round(labelH)}`
        if (!PRINT_PRESETS[sizeKey]) {
          PRINT_PRESETS[sizeKey] = {
            key: sizeKey,
            mode: 'single',
            labelW: media.widthMm,
            labelH,
          }
        }
        printerPreset.value = null
        printPreset.value = sizeKey
        // Resize the design canvas so the label matches the printer media,
        // honouring the current portrait/wide orientation.
        const { w, h } = orientedDims(PRINT_PRESETS[sizeKey].labelW, PRINT_PRESETS[sizeKey].labelH, wideLabel.value)
        applyCanvasSizeMm(w, h)
      }
      $q.notify({
        type: 'positive',
        message: t('labels.mediaLoadedFromPrinter', { width: media.widthMm, length: media.heightMm }),
      })
    } else {
      $q.notify({ type: 'warning', message: t('labels.noMediaDetected') })
    }
  } catch (err) {
    $q.notify({ type: 'negative', message: t('labels.directPrintFailed') + ': ' + (err?.message || err) })
  }
}

async function diagnosePrinter() {
  const printer = getPrinter()
  if (!printer?.connected) {
    $q.notify({ type: 'warning', message: t('labels.brotherNotConnected') })
    return
  }
  try {
    const status = await getPrinterStatus()
    const printer = getPrinter()
    const lines = []
    if (printer?.model) lines.push(`Model: ${printer.model}`)
    lines.push(status?.ready ? t('labels.printerReady') : t('labels.printerNotReady'))
    lines.push(status?.mediaLoaded ? t('labels.printerMediaLoaded') : t('labels.printerMediaNotLoaded'))
    const errs = status?.errors || []
    if (errs.length) {
      lines.push(
        `${t('labels.printerStatusErrors')}: ${errs.map((e) => `${e.message} [${e.code}]`).join(', ')}`,
      )
    } else {
      lines.push(t('labels.printerNoErrors'))
    }
    $q.notify({
      type: status?.ready && !errs.length ? 'positive' : 'warning',
      message: lines.join(' — '),
      timeout: 8000,
    })
  } catch (err) {
    $q.notify({ type: 'negative', message: t('labels.directPrintFailed') + ': ' + (err?.message || err) })
  }
}

async function directPrintLabels({ calibration = false } = {}) {
  if (!calibration && (!selectedRows.value.length || !templateElements.value.length)) return
  if (!calibration && !getPrinter()?.connected) {
    $q.notify({ type: 'warning', message: t('labels.brotherNotConnected') })
    return
  }
  await printRowsDirect({
    rows: selectedRows.value,
    elements: templateElements.value,
    canvasWpx: canvas.value.width,
    canvasHpx: canvas.value.height,
    cutLabels: cutLabels.value,
    calibration,
    notify: (m) => $q.notify(m),
  })
}

let autoPrintConsumed = false
async function maybeAutoPrintFromQuery() {
  if (autoPrintConsumed) return
  if (!queryFlagEnabled(route.query.autoPrint)) return
  autoPrintConsumed = true

  if (!selectedRows.value.length || !templateElements.value.length) return

  await nextTick()

  // Direct-print via the connected Brother printer (no browser print window).
  // If no printer is connected, leave the user on the editor (template + rows
  // already loaded) so they can connect and print manually.
  if (!getPrinter()?.connected) {
    $q.notify({
      type: 'warning',
      message: t('labels.connectPrinterToPrint'),
      timeout: 6000,
    })
    clearAutoPrintFlag()
    return
  }

  await directPrintLabels()
  clearAutoPrintFlag()
}

function clearAutoPrintFlag() {
  const nextQuery = { ...route.query }
  delete nextQuery.autoPrint
  router.replace({ path: '/labels', query: nextQuery })
}

watch(entityType, () => {
  selectedEntityIds.value = []
  filterEntityOptions('', () => {})
  filterSourceOptions('', () => {})
})

// Canvas sizing is applied explicitly (on preset change, wide toggle, "preset to
// canvas", custom mm, and when loading a template/preset) rather than via a
// reactive watch, so loading a saved template does not override its stored
// canvas with the preset's default dimensions.

onMounted(async () => {
  await Promise.all([
    inventoryStore.fetchAll(),
    settingsStore.fetchCompanyProfile(),
    settingsStore.fetchLabelTemplates(),
  ])
  resetTemplate()
  await applyIncomingSelectionFromQuery()
  await maybeAutoPrintFromQuery()
  filterEntityOptions('', () => {})
  filterSourceOptions('', () => {})
})

onBeforeUnmount(() => {
  stopDragElement()
  stopResizeElement()
  clearGuides()
})

watch(() => `${route.query.entity || ''}|${route.query.ids || ''}`, async () => {
  await applyIncomingSelectionFromQuery()
  await maybeAutoPrintFromQuery()
})

watch(templateElements, () => {
  if (selectedElementId.value && !templateElements.value.find(item => item.id === selectedElementId.value)) {
    selectedElementId.value = templateElements.value[0]?.id || null
  }
}, { deep: true })

watch(
  [templateElements, activePreviewRow, previewMode],
  async () => {
    if (!previewMode.value) {
      qrcodePreviewById.value = {}
      barcodePreviewById.value = {}
      return
    }

    const nextBarcode = {}
    const nextQrcode = {}
    for (const item of templateElements.value) {
      const value = previewValue(item)
      if (item.kind === 'barcode') {
        nextBarcode[item.id] = value ? barcodeSvg(value, item.w, item.h) : ''
      }
      if (item.kind === 'qrcode') {
        nextQrcode[item.id] = value ? await qrDataUrl(value, Math.min(item.w, item.h)) : ''
      }
    }
    barcodePreviewById.value = nextBarcode
    qrcodePreviewById.value = nextQrcode
  },
  { deep: true, immediate: true }
)

const logoImageFields = computed(() => {
  const list = [
    { source: 'business.logo_url', label: t('labels.logoDefault') },
    { source: 'business.logo_light_wide_url', label: t('labels.logoLightWide') },
    { source: 'business.logo_light_small_url', label: t('labels.logoLightSmall') },
    { source: 'business.logo_dark_wide_url', label: t('labels.logoDarkWide') },
    { source: 'business.logo_dark_small_url', label: t('labels.logoDarkSmall') },
  ]
  return list.map(item => ({
    ...item,
    previewUrl: resolveLogoUrlBySource(item.source),
  }))
})

</script>

<style scoped>
.labels-page {
  background: radial-gradient(900px 380px at 0% -10%, rgba(35, 101, 160, 0.14), transparent),
    radial-gradient(760px 360px at 100% 0%, rgba(22, 163, 74, 0.14), transparent);
}

.label-canvas {
  position: relative;
  margin: 0 auto;
  border: 1px dashed rgba(0, 0, 0, 0.34);
  border-radius: 8px;
  background: repeating-linear-gradient(
      0deg,
      rgba(0, 0, 0, 0.02),
      rgba(0, 0, 0, 0.02) 10px,
      rgba(0, 0, 0, 0.04) 10px,
      rgba(0, 0, 0, 0.04) 20px
    ),
    #fff;
  overflow: hidden;
}

.label-canvas:focus {
  outline: 2px solid rgba(37, 99, 235, 0.55);
  outline-offset: 2px;
}

.label-guide-vertical,
.label-guide-horizontal {
  position: absolute;
  pointer-events: none;
  z-index: 2;
  background: rgba(37, 99, 235, 0.45);
}

.label-guide-vertical {
  top: 0;
  bottom: 0;
  width: 1px;
}

.label-guide-horizontal {
  left: 0;
  right: 0;
  height: 1px;
}

.label-item {
  position: absolute;
  border: 1px solid rgba(107, 114, 128, 0.55);
  border-radius: 4px;
  padding: 2px 4px;
  background: rgba(255, 255, 255, 0.9);
  color: #111;
  cursor: move;
  user-select: none;
  overflow: hidden;
}

.preview-logo-wrap,
.preview-qrcode-wrap,
.preview-barcode {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.preview-logo,
.preview-qrcode {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.preview-barcode :deep(svg) {
  width: 100%;
  height: 100%;
}

.resize-handle {
  position: absolute;
  width: 8px;
  height: 8px;
  background: #2563eb;
  border: 1px solid #ffffff;
  border-radius: 999px;
  z-index: 4;
}

.resize-handle-nw {
  left: -4px;
  top: -4px;
  cursor: nwse-resize;
}

.resize-handle-n {
  left: calc(50% - 4px);
  top: -4px;
  cursor: ns-resize;
}

.resize-handle-ne {
  right: -4px;
  top: -4px;
  cursor: nesw-resize;
}

.resize-handle-e {
  right: -4px;
  top: calc(50% - 4px);
  cursor: ew-resize;
}

.resize-handle-se {
  right: -4px;
  bottom: -4px;
  cursor: nwse-resize;
}

.resize-handle-s {
  left: calc(50% - 4px);
  bottom: -4px;
  cursor: ns-resize;
}

.resize-handle-sw {
  left: -4px;
  bottom: -4px;
  cursor: nesw-resize;
}

.resize-handle-w {
  left: -4px;
  top: calc(50% - 4px);
  cursor: ew-resize;
}

.label-item.selected {
  border-color: #2563eb;
  box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.2);
}
</style>
