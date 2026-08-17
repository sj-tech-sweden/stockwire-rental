<template>
  <div class="report-designer">
    <!-- Header Bar -->
    <div class="row items-center justify-between q-mb-sm">
      <div class="row items-center q-gutter-sm">
        <q-btn-toggle
          v-model="editorMode"
          :options="[{ label: t('reports.visualMode'), value: 'visual' }, { label: t('reports.codeMode'), value: 'code' }]"
          flat dense color="primary"
        />
        <q-separator vertical />
        <q-select
          v-model="editorLanguage"
          :options="languageOptions"
          :label="t('app.language.label')"
          emit-value
          map-options
          outlined
          dense
          style="min-width: 140px"
        />
        <q-separator vertical />
        <q-select v-model="form.category" :options="categoryOptions" emit-value map-options outlined dense class="category-select" />
      </div>
      <div class="row q-gutter-sm">
        <q-btn flat :label="t('app.actions.cancel')" @click="emit('close')" />
        <q-btn color="primary" unelevated :label="t('app.actions.save')" :loading="saving" @click="saveTemplate" />
      </div>
    </div>

    <!-- Template Meta -->
    <div class="row q-col-gutter-sm q-mb-md">
      <div class="col-6">
        <q-input v-model="form.name" :label="t('reports.templateName')" outlined dense />
      </div>
      <div class="col-3">
        <q-select v-model="form.data_source_type" :options="dataSourceOptions" emit-value map-options outlined dense />
      </div>
      <div class="col-3">
        <q-select v-model="form.letterhead_id" :options="letterheadOptions" emit-value map-options clearable outlined dense />
      </div>
    </div>

    <!-- Editor Area -->
    <div class="editor-area">
      <!-- Visual Mode -->
      <div v-if="editorMode === 'visual'" class="visual-editor">
        <div class="row no-wrap" style="height: 500px">
          <!-- Block Palette -->
          <div class="block-palette q-pa-sm">
            <div class="text-caption text-grey-7 q-mb-sm">{{ t('reports.blocks') }}</div>
            <q-btn
              v-for="block in blockTypes"
              :key="block.type"
              flat dense no-caps
              :icon="block.icon"
              :label="block.label"
              class="full-width q-mb-xs text-left"
              @click="addBlock(block.type)"
            />
          </div>
          <q-separator vertical />
          <!-- Canvas -->
          <div class="block-canvas q-pa-sm">
            <div v-if="!flowables.length" class="empty-canvas">
              <q-icon name="add_circle_outline" size="48px" color="grey-5" />
              <div class="text-body2 text-grey-6 q-mt-sm">{{ t('reports.dropBlocksHere') }}</div>
              <div class="text-caption text-grey-5 q-mt-xs">{{ t('reports.canvasHint') }}</div>
            </div>
            <div
              v-for="(block, idx) in flowables"
              :key="idx"
              class="block-item q-pa-sm"
              :class="{ selected: selectedBlockIdx === idx, dragging: dragIdx === idx }"
              draggable="true"
              @click="selectBlock(idx)"
              @dragstart="onDragStart(idx, $event)"
              @dragover="onDragOver(idx, $event)"
              @dragleave="onDragLeave"
              @drop="onDrop(idx, $event)"
              @dragend="onDragEnd"
            >
              <div v-if="dropIndicator?.idx === idx && !dropIndicator.after" class="drop-indicator" />
              <div class="row items-center justify-between">
                <div class="row items-center q-gutter-xs">
                  <q-icon name="drag_indicator" size="xs" color="grey-6" class="drag-handle cursor-grab" />
                  <q-icon :name="blockIcon(block.type)" size="xs" color="primary" />
                  <div class="text-caption text-weight-medium">{{ blockTypeLabel(block.type) }}</div>
                </div>
                <div class="q-gutter-xs">
                  <q-btn flat dense icon="arrow_upward" size="xs" :disable="idx === 0" @click.stop="moveBlock(idx, -1)" />
                  <q-btn flat dense icon="arrow_downward" size="xs" :disable="idx === flowables.length - 1" @click.stop="moveBlock(idx, 1)" />
                  <q-btn flat dense icon="close" size="xs" color="negative" @click.stop="removeBlock(idx)" />
                </div>
              </div>
              <div class="block-preview text-caption q-mt-xs">
                {{ blockPreviewText(block) }}
              </div>
              <div v-if="dropIndicator?.idx === idx && dropIndicator.after" class="drop-indicator" />
            </div>
          </div>
          <q-separator vertical />
          <!-- Properties -->
          <div class="block-properties q-pa-sm">
            <div class="text-caption text-grey-7 q-mb-sm">{{ t('reports.properties') }}</div>
            <template v-if="editedBlock">
              <div v-if="selectedNestedBlock" class="row items-center q-mb-sm">
                <q-btn flat dense icon="arrow_back" size="sm" color="primary" :label="t('reports.backToColumn')" @click="deselectNestedBlock" />
              </div>

              <q-input v-if="editedBlock.text !== undefined" v-model="editedBlock.text" :label="t('reports.textContent')" outlined dense class="q-mb-sm" @update:model-value="onBlockChange" />
              <q-select v-if="editedBlock.type === 'heading'" v-model.number="editedBlock.level" :label="t('reports.headingLevel')" :options="[{label:t('reports.h1'),value:1},{label:t('reports.h2'),value:2},{label:t('reports.h3'),value:3}]" emit-value map-options outlined dense class="q-mb-sm" />
              <q-select v-if="editedBlock.type === 'paragraph'" v-model="editedBlock.style" :label="t('reports.paragraphStyle')" :options="[{label:t('reports.styleBody'),value:'body'},{label:t('reports.styleBold'),value:'bold'},{label:t('reports.styleSmall'),value:'small'},{label:t('reports.styleCenter'),value:'center'}]" emit-value map-options outlined dense class="q-mb-sm" />
              <q-select v-if="hasAlign(editedBlock.type)" v-model="editedBlock.align" :options="alignOptions" :label="t('reports.alignment')" emit-value map-options outlined dense class="q-mb-sm" />
              <q-input v-if="editedBlock.type === 'table'" v-model="editedBlock.source" :label="t('reports.dataSourcePath')" outlined dense class="q-mb-sm" hint="e.g. device.case_contents" />

              <!-- Table columns editor -->
              <template v-if="editedBlock.type === 'table'">
                <div class="text-caption text-grey-7 q-mb-xs">{{ t('reports.columns') }}</div>
                <div v-for="(col, idx) in editedBlock.columns" :key="idx" class="row q-col-gutter-sm q-mb-sm items-center">
                  <div class="col-5">
                    <q-input v-model="col.label" :label="t('reports.label')" outlined dense />
                  </div>
                  <div class="col-5">
                    <q-input v-model="col.key" :label="t('reports.key')" outlined dense />
                  </div>
                  <div class="col-2">
                    <q-btn flat dense icon="close" color="negative" size="sm" @click="removeTableColumn(idx)" />
                  </div>
                </div>
                <q-select :model-value="null" :options="schemaFieldOptions" :label="t('reports.addColumn')" outlined dense emit-value map-options class="q-mb-sm" @update:model-value="(key) => { if (key) { editedBlock.columns.push({ key, label: key.split('.').pop() }); } }" />
              </template>

              <q-input v-if="editedBlock.type === 'key_value'" v-model="editedBlock.source" :label="t('reports.dataSourcePath')" outlined dense class="q-mb-sm" hint="e.g. device" />

              <!-- Key/Value fields editor -->
              <template v-if="editedBlock.type === 'key_value'">
                <div class="text-caption text-grey-7 q-mb-xs">{{ t('reports.fields') }}</div>
                <div v-for="(field, idx) in editedBlock.fields" :key="idx" class="row q-col-gutter-sm q-mb-sm items-center">
                  <div class="col-5">
                    <q-input v-model="field.label" :label="t('reports.label')" outlined dense />
                  </div>
                  <div class="col-5">
                    <q-input v-model="field.key" :label="t('reports.key')" outlined dense />
                  </div>
                  <div class="col-2">
                    <q-btn flat dense icon="close" color="negative" size="sm" @click="removeKeyValueField(idx)" />
                  </div>
                </div>
                <q-select :model-value="null" :options="schemaFieldOptions" :label="t('reports.addField')" outlined dense emit-value map-options class="q-mb-sm" @update:model-value="(key) => { if (key) { editedBlock.fields.push({ key, label: key.split('.').pop() }); } }" />
              </template>
              <q-input v-if="editedBlock.type === 'spacer'" v-model.number="editedBlock.height_mm" type="number" :label="t('reports.heightMm')" outlined dense class="q-mb-sm" />
              <q-input v-if="editedBlock.type === 'barcode'" v-model="editedBlock.value" :label="t('reports.barcodeValue')" outlined dense class="q-mb-sm" hint="e.g. {{ device.barcode }}" />
              <q-select v-if="editedBlock.type === 'barcode'" v-model="editedBlock.barcode_type" :options="barcodeTypeOptions" :label="t('reports.barcodeType')" emit-value map-options outlined dense class="q-mb-sm" />

              <!-- Columns editor -->
              <template v-if="selectedBlock?.type === 'columns' && !selectedNestedBlock">
                <div class="text-caption text-grey-7 q-mb-xs">{{ t('reports.columnWidths') }}</div>
                <div class="row q-col-gutter-sm q-mb-sm">
                  <div v-for="(width, idx) in selectedBlock.widths" :key="idx" class="col-6">
                    <q-input v-model="selectedBlock.widths[idx]" :label="t('reports.column', { index: idx + 1 })" outlined dense />
                  </div>
                </div>
                <q-tabs v-model="activeColumnTab" dense align="left" class="q-mb-sm">
                  <q-tab v-for="(_, idx) in selectedBlock.columns" :key="idx" :name="idx" :label="t('reports.column', { index: idx + 1 })" />
                </q-tabs>
                <q-tab-panels v-model="activeColumnTab" animated>
                  <q-tab-panel v-for="(col, idx) in selectedBlock.columns" :key="idx" :name="idx" class="q-pa-none">
                    <div class="column-blocks">
                      <div v-for="(child, cidx) in col" :key="cidx" class="nested-block row items-center q-pa-xs q-mb-xs cursor-pointer" @click="selectNestedBlock(idx, cidx)">
                        <q-icon :name="blockIcon(child.type)" size="xs" color="primary" class="q-mr-sm" />
                        <div class="text-caption col">{{ blockPreviewText(child) }}</div>
                        <q-btn flat dense icon="close" size="xs" color="negative" @click.stop="removeColumnBlock(idx, cidx)" />
                      </div>
                      <div v-if="!col.length" class="text-caption text-grey-5 q-py-sm">{{ t('reports.emptyColumn') }}</div>
                    </div>
                    <q-select :model-value="null" :options="columnChildOptions" :label="t('reports.addBlockToColumn')" outlined dense emit-value map-options @update:model-value="addColumnBlock(idx, $event)" />
                  </q-tab-panel>
                </q-tab-panels>
              </template>
            </template>
            <div v-else class="text-caption text-grey-6 text-center q-py-md">
              <q-icon name="touch_app" size="24px" class="q-mb-sm block" />
              {{ t('reports.selectBlock') }}
            </div>
          </div>
        </div>
      </div>

      <!-- Code Mode -->
      <div v-else class="code-editor">
        <div ref="editorContainer" style="height: 500px; border: 1px solid #ddd"></div>
      </div>
    </div>

    <!-- Variable Picker -->
    <q-expansion-item :label="t('reports.availableVariables')" class="q-mt-sm">
      <div class="q-pa-sm">
        <div class="text-caption text-grey-6 q-mb-xs">{{ t('reports.clickToCopy') }}</div>
        <div class="variable-grid">
          <div
            v-for="field in dataSourceFields"
            :key="field.key"
            class="variable-item row items-center q-py-xs q-px-sm cursor-pointer"
            @click="copyVariable(field.key)"
          >
            <q-icon name="content_copy" size="xs" color="grey-6" class="q-mr-sm" />
            <span class="text-body2 col">{{ field.label }}</span>
            <code class="text-caption text-primary col-auto">{{ '{' + '{ ' + field.key + ' }' + '}' }}</code>
          </div>
        </div>
      </div>
    </q-expansion-item>

    <!-- Live Preview -->
    <q-expansion-item :label="t('reports.livePreview')" class="q-mt-sm" v-model="previewExpanded">
      <div class="q-pa-sm">
        <div class="row q-col-gutter-sm q-mb-sm items-center">
          <div class="col-4">
            <q-select
              v-model="previewEntityType"
              :options="previewEntityTypeOptions"
              :label="t('reports.entityType')"
              outlined dense emit-value map-options
            />
          </div>
          <div class="col-5">
            <q-select
              v-model="previewEntityId"
              :options="previewEntityOptions"
              :label="t('reports.entity')"
              outlined dense emit-value map-options
              :loading="previewLoading"
            />
          </div>
          <div class="col-3">
            <q-select
              v-model="previewFormat"
              :options="[{ label: t('reports.pdf'), value: 'pdf' }, { label: t('reports.html'), value: 'html' }]"
              :label="t('reports.format')"
              outlined dense emit-value map-options
            />
          </div>
        </div>
        <div class="row justify-end q-mb-sm">
          <q-btn color="primary" unelevated icon="preview" :label="t('reports.generatePreview')" :loading="previewLoading" :disable="!previewEntityId" @click="generatePreview" />
        </div>
        <div class="preview-frame">
          <div v-if="!previewUrl && !previewHtml" class="preview-placeholder">
            <q-icon name="preview" size="48px" color="grey-5" />
            <div class="text-caption text-grey-6 q-mt-sm">{{ t('reports.previewPlaceholder') }}</div>
          </div>
          <object
            v-else-if="previewUrl"
            :data="previewUrl + '#toolbar=0&navpanes=0&page=1&zoom=page-fit'"
            type="application/pdf"
            class="preview-object"
          />
          <div v-else-if="previewHtml" class="preview-html" v-html="previewHtml" />
        </div>
      </div>
    </q-expansion-item>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { SUPPORTED_LOCALES } from '../i18n'
import { useReportsStore } from '../stores/reports'
import { useJobsStore } from '../stores/jobs'
import { useInventoryStore } from '../stores/inventory'

const props = defineProps({
  template: { type: Object, default: null },
})

const emit = defineEmits(['close', 'saved'])

const $q = useQuasar()
const { t, locale } = useI18n()
const reportsStore = useReportsStore()
const jobsStore = useJobsStore()
const inventoryStore = useInventoryStore()

const saving = ref(false)
const editorMode = ref('visual')
const editorLanguage = ref(String(locale.value || 'en').split(/[-_]/)[0] || 'en')
const baseName = ref('')
const baseFlowables = ref([])
const flowables = ref([])
const translations = ref({})
const selectedBlockIdx = ref(null)
const dataSourceFields = ref([])
const letterheads = ref([])

const form = ref({
  name: '',
  category: 'custom',
  description: '',
  data_source_type: 'job',
  letterhead_id: null,
  is_enabled: true,
})

const previewEntityType = ref('job')
const previewEntityId = ref(null)
const previewFormat = ref('pdf')
const previewLoading = ref(false)
const previewUrl = ref(null)
const previewHtml = ref('')
const previewExpanded = ref(false)
const dragIdx = ref(null)
const dropIndicator = ref(null)

const languageOptions = computed(() => {
  return SUPPORTED_LOCALES.map(locale => ({
    label: t(`app.language.${locale}`) || locale.toUpperCase(),
    value: locale,
  }))
})

const categoryOptions = computed(() => [
  { label: t('reports.categories.warehouse'), value: 'warehouse' },
  { label: t('reports.categories.asset'), value: 'asset' },
  { label: t('reports.categories.logistics'), value: 'logistics' },
  { label: t('reports.categories.custom'), value: 'custom' },
])

const dataSourceOptions = computed(() => [
  { label: t('reports.dataSources.job'), value: 'job' },
  { label: t('reports.dataSources.device'), value: 'device' },
  { label: t('reports.dataSources.product'), value: 'product' },
  { label: t('reports.dataSources.inventory'), value: 'inventory' },
])

const letterheadOptions = computed(() => [
  { label: t('reports.noLetterhead'), value: null },
  ...letterheads.value.map(l => ({ label: l.name, value: l.id })),
])

const previewEntityTypeOptions = computed(() => [
  { label: t('reports.dataSources.job'), value: 'job' },
  { label: t('reports.dataSources.product'), value: 'product' },
  { label: t('reports.dataSources.device'), value: 'device' },
])

const previewEntityOptions = computed(() => {
  if (previewEntityType.value === 'job') {
    return (jobsStore.jobs || []).map(j => ({ label: `${j.job_code || ''} - ${j.description || j.id}`, value: j.id }))
  }
  if (previewEntityType.value === 'product') {
    return (inventoryStore.products || []).map(p => ({ label: `${p.name || ''} (${p.sku || ''})`, value: p.id }))
  }
  if (previewEntityType.value === 'device') {
    return (inventoryStore.devices || []).map(d => ({ label: `${d.asset_tag || ''} - ${d.serial_number || d.id}`, value: d.id }))
  }
  return []
})

const blockTypes = computed(() => [
  { type: 'heading', label: t('reports.blockHeading'), icon: 'title' },
  { type: 'paragraph', label: t('reports.blockParagraph'), icon: 'notes' },
  { type: 'table', label: t('reports.blockTable'), icon: 'table_chart' },
  { type: 'key_value', label: t('reports.blockKeyValue'), icon: 'grid_on' },
  { type: 'columns', label: t('reports.columns'), icon: 'view_column' },
  { type: 'spacer', label: t('reports.blockSpacer'), icon: 'space_bar' },
  { type: 'line', label: t('reports.blockLine'), icon: 'horizontal_rule' },
  { type: 'barcode', label: t('reports.blockBarcode'), icon: 'qr_code' },
  { type: 'page_break', label: t('reports.blockPageBreak'), icon: 'insert_page_break' },
])

const alignOptions = computed(() => [
  { label: t('reports.alignLeft'), value: 'left' },
  { label: t('reports.alignCenter'), value: 'center' },
  { label: t('reports.alignRight'), value: 'right' },
])

const barcodeTypeOptions = computed(() => [
  { label: 'Code 128', value: 'code128' },
  { label: 'QR Code', value: 'qr' },
])

const schemaFieldOptions = computed(() => {
  return dataSourceFields.value.map(f => ({ label: f.label || f.key, value: f.key }))
})

const selectedBlock = computed(() => {
  if (selectedBlockIdx.value === null || selectedBlockIdx.value >= flowables.value.length) return null
  return flowables.value[selectedBlockIdx.value]
})

const selectedNestedBlock = ref(null)

const editedBlock = computed(() => {
  if (!selectedNestedBlock.value || selectedBlock.value?.type !== 'columns') return selectedBlock.value
  const { colIdx, childIdx } = selectedNestedBlock.value
  const col = selectedBlock.value.columns?.[colIdx]
  return col?.[childIdx] || selectedBlock.value
})

const activeColumnTab = ref(0)

const columnChildOptions = computed(() => [
  { label: t('reports.blockHeading'), value: 'heading' },
  { label: t('reports.blockParagraph'), value: 'paragraph' },
  { label: t('reports.blockBarcode'), value: 'barcode' },
  { label: t('reports.blockSpacer'), value: 'spacer' },
  { label: t('reports.blockLine'), value: 'line' },
])

function hasAlign(type) {
  return ['heading', 'paragraph', 'table', 'key_value', 'barcode', 'line'].includes(type)
}

function blockPreviewText(block) {
  if (block.type === 'heading') return `[H${block.level || 1}] ${block.text || t('reports.emptyBlock')}`
  if (block.type === 'paragraph') return block.text || t('reports.emptyBlock')
  if (block.type === 'table') return `${t('reports.tableFrom')}: ${block.source || '...'}`
  if (block.type === 'key_value') return `${t('reports.keyValueFrom')}: ${block.source || '...'}`
  if (block.type === 'columns') return `${t('reports.columns')}: ${(block.widths || []).join(' / ')}`
  if (block.type === 'spacer') return `${t('reports.spacer')}: ${block.height_mm || 5}mm`
  if (block.type === 'line') return `--- ${t('reports.divider')} ---`
  if (block.type === 'barcode') return `${t('reports.barcode')}: ${block.value || '...'}`
  if (block.type === 'page_break') return `--- ${t('reports.pageBreak')} ---`
  return block.type
}

function blockTypeLabel(type) {
  const map = {
    heading: t('reports.blockHeading'),
    paragraph: t('reports.blockParagraph'),
    table: t('reports.blockTable'),
    key_value: t('reports.blockKeyValue'),
    columns: t('reports.columns') || 'Columns',
    spacer: t('reports.blockSpacer'),
    line: t('reports.blockLine'),
    barcode: t('reports.blockBarcode'),
    page_break: t('reports.blockPageBreak'),
  }
  return map[type] || type
}

function blockIcon(type) {
  const map = {
    heading: 'title',
    paragraph: 'notes',
    table: 'table_chart',
    key_value: 'grid_on',
    columns: 'view_column',
    spacer: 'space_bar',
    line: 'horizontal_rule',
    barcode: 'qr_code',
    page_break: 'insert_page_break',
  }
  return map[type] || 'block'
}

function addBlock(type) {
  const defaults = {
    heading: { type: 'heading', text: '', level: 1, align: 'left' },
    paragraph: { type: 'paragraph', text: '', style: 'body', align: 'left' },
    table: { type: 'table', source: '', columns: [{ key: 'name', label: t('reports.name') }], align: 'left' },
    key_value: { type: 'key_value', source: '', fields: [{ key: 'name', label: t('reports.name') }], align: 'left' },
    columns: { type: 'columns', columns: [[], []], widths: ['50%', '50%'] },
    spacer: { type: 'spacer', height_mm: 5 },
    line: { type: 'line', width_percent: 100, align: 'left' },
    barcode: { type: 'barcode', value: '', barcode_type: 'code128', align: 'left' },
    page_break: { type: 'page_break' },
  }
  flowables.value.push({ ...defaults[type] })
  selectedBlockIdx.value = flowables.value.length - 1
}

function selectBlock(idx) {
  selectedBlockIdx.value = idx
  selectedNestedBlock.value = null
}

function selectNestedBlock(colIdx, childIdx) {
  selectedNestedBlock.value = { colIdx, childIdx }
  activeColumnTab.value = colIdx
}

function deselectNestedBlock() {
  selectedNestedBlock.value = null
}

function moveBlock(idx, direction) {
  const newIdx = idx + direction
  if (newIdx < 0 || newIdx >= flowables.value.length) return
  const temp = flowables.value[idx]
  flowables.value[idx] = flowables.value[newIdx]
  flowables.value[newIdx] = temp
  selectedBlockIdx.value = newIdx
}

function removeBlock(idx) {
  flowables.value.splice(idx, 1)
  if (selectedBlockIdx.value >= flowables.value.length) {
    selectedBlockIdx.value = flowables.value.length > 0 ? flowables.value.length - 1 : null
  }
}

function onDragStart(idx, event) {
  dragIdx.value = idx
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', String(idx))
}

function onDragOver(idx, event) {
  event.preventDefault()
  event.dataTransfer.dropEffect = 'move'
  if (dragIdx.value === null || dragIdx.value === idx) {
    dropIndicator.value = null
    return
  }
  const rect = event.currentTarget.getBoundingClientRect()
  const midpoint = rect.top + rect.height / 2
  dropIndicator.value = { idx, after: event.clientY > midpoint }
}

function onDragLeave() {
  dropIndicator.value = null
}

function onDrop(targetIdx, event) {
  event.preventDefault()
  const sourceIdx = dragIdx.value
  if (sourceIdx === null || sourceIdx === targetIdx) {
    dropIndicator.value = null
    return
  }
  const rect = event.currentTarget.getBoundingClientRect()
  const midpoint = rect.top + rect.height / 2
  const after = event.clientY > midpoint
  const item = flowables.value.splice(sourceIdx, 1)[0]
  let insertIdx = targetIdx
  if (sourceIdx < targetIdx && after) insertIdx = targetIdx
  if (sourceIdx < targetIdx && !after) insertIdx = targetIdx - 1
  if (sourceIdx > targetIdx && after) insertIdx = targetIdx + 1
  flowables.value.splice(insertIdx, 0, item)
  selectedBlockIdx.value = insertIdx
  dropIndicator.value = null
}

function onDragEnd() {
  dragIdx.value = null
  dropIndicator.value = null
}

function addColumnBlock(colIdx, type) {
  if (!selectedBlock.value || selectedBlock.value.type !== 'columns') return
  const defaults = {
    heading: { type: 'heading', text: '', level: 1, align: 'left' },
    paragraph: { type: 'paragraph', text: '', style: 'body', align: 'left' },
    barcode: { type: 'barcode', value: '', barcode_type: 'code128', align: 'left' },
    spacer: { type: 'spacer', height_mm: 5 },
    line: { type: 'line', width_percent: 100, align: 'left' },
  }
  selectedBlock.value.columns[colIdx].push({ ...defaults[type] })
}

function removeColumnBlock(colIdx, childIdx) {
  if (!selectedBlock.value || selectedBlock.value.type !== 'columns') return
  selectedBlock.value.columns[colIdx].splice(childIdx, 1)
}

function addKeyValueField() {
  if (!editedBlock.value || editedBlock.value.type !== 'key_value') return
  if (!editedBlock.value.fields) editedBlock.value.fields = []
  editedBlock.value.fields.push({ key: '', label: '' })
}

function removeKeyValueField(index) {
  if (!editedBlock.value || editedBlock.value.type !== 'key_value') return
  editedBlock.value.fields.splice(index, 1)
}

function addTableColumn() {
  if (!editedBlock.value || editedBlock.value.type !== 'table') return
  if (!editedBlock.value.columns) editedBlock.value.columns = []
  editedBlock.value.columns.push({ key: '', label: '' })
}

function removeTableColumn(index) {
  if (!editedBlock.value || editedBlock.value.type !== 'table') return
  editedBlock.value.columns.splice(index, 1)
}

function onBlockChange() {
  // Triggers reactivity for block preview
}

function insertVariable(key) {
  const varText = `{{ ${key} }}`
  if (editedBlock.value && editedBlock.value.text !== undefined) {
    editedBlock.value.text += varText
  }
}

function copyVariable(key) {
  const varText = `{{ ${key} }}`
  navigator.clipboard.writeText(varText).then(() => {
    $q.notify({ type: 'positive', message: `${t('reports.copied')}: ${varText}`, timeout: 1500 })
  }).catch(() => {
    insertVariable(key)
  })
}

async function loadEntities() {
  try {
    if (previewEntityType.value === 'job') {
      await jobsStore.fetchJobs()
    } else if (previewEntityType.value === 'product' || previewEntityType.value === 'device') {
      await inventoryStore.fetchInventory()
    }
  } catch { /* ignore */ }
}

async function generatePreview() {
  if (!props.template?.id) {
    $q.notify({ type: 'warning', message: t('reports.saveBeforePreview') })
    return
  }
  if (!previewEntityId.value) {
    $q.notify({ type: 'warning', message: t('reports.selectEntityToPreview') })
    return
  }
  previewLoading.value = true
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = null
  previewHtml.value = ''
  try {
    const payload = {
      template_id: props.template.id,
      entity_type: previewEntityType.value,
      entity_id: previewEntityId.value,
      format: previewFormat.value,
      language: locale.value,
    }
    if (previewFormat.value === 'html') {
      const html = await reportsStore.previewReport(payload, 'text')
      previewHtml.value = html
    } else {
      const blob = await reportsStore.previewReport(payload, 'blob')
      previewUrl.value = URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }))
    }
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('reports.previewFailed') })
  } finally {
    previewLoading.value = false
  }
}

async function loadLetterheads() {
  try {
    letterheads.value = await reportsStore.fetchLetterheads()
  } catch { /* ignore */ }
}

async function loadSchema() {
  try {
    const schema = await reportsStore.fetchDataSourceSchema(form.value.data_source_type)
    dataSourceFields.value = schema.fields || []
  } catch { /* ignore */ }
}

async function saveTemplate() {
  if (!form.value.name) {
    $q.notify({ type: 'warning', message: t('reports.nameRequired') })
    return
  }
  saving.value = true
  try {
    // Persist whichever language is currently being edited.
    let currentTranslations = translations.value
    let saveFlowables = baseFlowables.value
    const currentLang = editorLanguage.value || 'en'
    if (currentLang === 'en') {
      saveFlowables = flowables.value
    } else {
      currentTranslations = {
        ...translations.value,
        [currentLang]: {
          name: form.value.name,
          flowables: JSON.parse(JSON.stringify(flowables.value)),
        },
      }
      saveFlowables = baseFlowables.value
    }

    const bodyJson = JSON.stringify({ flowables: saveFlowables, page_size: 'A4' })
    const payload = {
      name: baseName.value || form.value.name,
      category: form.value.category,
      description: form.value.description,
      data_source_type: form.value.data_source_type,
      letterhead_id: form.value.letterhead_id,
      is_enabled: form.value.is_enabled,
      body_json: bodyJson,
      translations_json: Object.keys(currentTranslations).length ? JSON.stringify(currentTranslations) : null,
    }
    if (props.template?.id) {
      await reportsStore.updateTemplate(props.template.id, payload)
    } else {
      await reportsStore.createTemplate(payload)
    }
    emit('saved')
    emit('close')
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('reports.failedSave') })
  } finally {
    saving.value = false
  }
}

watch(() => form.value.data_source_type, loadSchema)
watch(previewEntityType, async () => {
  previewEntityId.value = null
  await loadEntities()
})

watch(editorLanguage, (newLang, oldLang) => {
  // Persist the flowables and name we were just editing into the language we are leaving.
  if (oldLang) {
    if (oldLang === 'en') {
      baseName.value = form.value.name
      baseFlowables.value = JSON.parse(JSON.stringify(flowables.value))
    } else {
      translations.value = {
        ...translations.value,
        [oldLang]: {
          name: form.value.name,
          flowables: JSON.parse(JSON.stringify(flowables.value)),
        },
      }
    }
  }
  // Load the name and flowables for the new language.
  if (newLang === 'en') {
    form.value.name = baseName.value || form.value.name
    flowables.value = JSON.parse(JSON.stringify(baseFlowables.value))
  } else {
    const translated = translations.value?.[newLang]
    form.value.name = translated?.name || baseName.value || form.value.name
    flowables.value = translated?.flowables
      ? JSON.parse(JSON.stringify(translated.flowables))
      : JSON.parse(JSON.stringify(baseFlowables.value))
  }
  selectedBlockIdx.value = null
  selectedNestedBlock.value = null
})

onMounted(async () => {
  await loadLetterheads()
  await loadSchema()

    if (props.template) {
      baseName.value = props.template.name || ''
      form.value = {
        name: props.template.name || '',
        category: props.template.category || 'custom',
        description: props.template.description || '',
        data_source_type: props.template.data_source_type || 'job',
        letterhead_id: props.template.letterhead_id || null,
        is_enabled: props.template.is_enabled ?? true,
      }
      const rawJson = props.template.body_json
      if (rawJson && typeof rawJson === 'string' && rawJson.trim().startsWith('{')) {
        try {
          const parsed = JSON.parse(rawJson)
          baseFlowables.value = Array.isArray(parsed.flowables) ? parsed.flowables : []
          flowables.value = JSON.parse(JSON.stringify(baseFlowables.value))
        } catch (e) {
          console.warn('Failed to parse template body_json:', e)
          baseFlowables.value = []
          flowables.value = []
        }
      } else {
        baseFlowables.value = []
        flowables.value = []
      }
      const transJson = props.template.translations_json
      if (transJson && typeof transJson === 'string' && transJson.trim().startsWith('{')) {
        try {
          translations.value = JSON.parse(transJson)
        } catch (e) {
          console.warn('Failed to parse template translations_json:', e)
          translations.value = {}
        }
      }
      previewEntityType.value = form.value.data_source_type === 'inventory' ? 'job' : form.value.data_source_type
      await loadEntities()
      // Pre-select first entity if available
      const first = previewEntityOptions.value[0]
      if (first) previewEntityId.value = first.value
    }
})

onUnmounted(() => {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
})
</script>

<style scoped>
.report-designer { border: 1px solid var(--q-separator-color, #e0e0e0); border-radius: 4px; padding: 12px; }
.editor-area { border: 1px solid var(--q-separator-color, #e0e0e0); border-radius: 4px; overflow: hidden; }
.visual-editor { min-height: 500px; }
.block-palette { width: 140px; border-right: 1px solid var(--q-separator-color, #e0e0e0); overflow-y: auto; }
.block-canvas { flex: 1; overflow-y: auto; }
.block-properties { width: 220px; border-left: 1px solid var(--q-separator-color, #e0e0e0); overflow-y: auto; }
.block-item {
  border: 1px solid var(--q-separator-color, #ccc);
  border-radius: 6px;
  cursor: pointer;
  transition: border-color 0.15s, background-color 0.15s;
  margin-bottom: 6px;
  padding: 8px 10px;
}
.block-item:hover { border-color: var(--q-primary, #1976D2); }
.block-item.selected { border-color: var(--q-primary, #1976D2); background: var(--q-primary-subtle, rgba(25, 118, 210, 0.12)); }
.block-preview { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; opacity: 0.7; }
.empty-canvas { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; opacity: 0.5; }
.category-select { width: 180px; }
.code-editor { min-height: 500px; }
.variable-grid { border: 1px solid var(--q-separator-color, #e0e0e0); border-radius: 4px; max-height: 200px; overflow-y: auto; }
.variable-item { border-bottom: 1px solid var(--q-separator-color, #f0f0f0); padding: 4px 8px; }
.variable-item:last-child { border-bottom: none; }
.variable-item:hover { background: var(--q-primary-subtle, rgba(25, 118, 210, 0.08)); }
.variable-item code { font-size: 11px; padding: 1px 4px; border-radius: 3px; }
.preview-frame {
  border: 1px solid var(--q-separator-color, #e0e0e0);
  border-radius: 4px;
  background: #f5f5f5;
  height: 500px;
  overflow: auto;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 16px;
}
.preview-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  width: 100%;
}
.preview-object {
  width: 100%;
  height: 100%;
  border: none;
  background: white;
}
.preview-html {
  background: white;
  padding: 20px;
  min-width: 210mm;
  min-height: 297mm;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.column-blocks {
  border: 1px dashed var(--q-separator-color, #ccc);
  border-radius: 4px;
  padding: 6px;
  min-height: 48px;
  margin-bottom: 8px;
}
.nested-block {
  background: var(--q-primary-subtle, rgba(25, 118, 210, 0.06));
  border-radius: 4px;
  border: 1px solid var(--q-separator-color, #e0e0e0);
}
.block-item {
  transition: opacity 0.15s, border-color 0.15s, background-color 0.15s;
}
.block-item.dragging {
  opacity: 0.5;
}
.block-item .drag-handle {
  cursor: grab;
}
.block-item .drag-handle:active {
  cursor: grabbing;
}
.drop-indicator {
  height: 3px;
  background: var(--q-primary, #1976D2);
  border-radius: 2px;
  margin: 4px 0;
}
</style>
