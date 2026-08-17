<template>
  <div class="calibrator-root">
    <!-- Toolbar -->
    <div class="calibrator-toolbar row items-center justify-between q-mb-sm q-gutter-sm">
      <div class="row items-center q-col-gutter-xs">
        <div class="col">
          <q-input v-model.number="margins.top" type="number" :label="t('reports.top')" outlined dense style="width: 80px" />
        </div>
        <div class="col">
          <q-input v-model.number="margins.bottom" type="number" :label="t('reports.bottom')" outlined dense style="width: 80px" />
        </div>
        <div class="col">
          <q-input v-model.number="margins.left" type="number" :label="t('reports.left')" outlined dense style="width: 80px" />
        </div>
        <div class="col">
          <q-input v-model.number="margins.right" type="number" :label="t('reports.right')" outlined dense style="width: 80px" />
        </div>
        <div class="col-auto text-caption text-grey-6">mm</div>
      </div>
      <div class="row items-center q-gutter-xs">
        <q-btn flat dense icon="remove" @click="zoomOut" :title="t('app.actions.zoomOut')" />
        <span class="text-caption" style="min-width: 48px; text-align: center">{{ Math.round(scale * 100) }}%</span>
        <q-btn flat dense icon="add" @click="zoomIn" :title="t('app.actions.zoomIn')" />
        <q-btn flat dense icon="fit_screen" @click="fitToScreen" :title="t('app.actions.fitToScreen')" />
      </div>
    </div>

    <!-- PDF Preview -->
    <div class="calibrator-canvas-wrapper" ref="wrapperRef">
      <div class="calibrator-canvas" :style="canvasStyle">
        <div class="page-container" :style="pageStyle">
          <div v-if="loadingPdf" class="pdf-placeholder">
            <q-spinner color="primary" size="32px" />
          </div>
          <object
            v-else-if="pdfBlobUrl"
            :data="pdfBlobUrl + '#toolbar=0&navpanes=0&scrollbar=0&page=1&zoom=page-fit'"
            type="application/pdf"
            class="pdf-object"
            tabindex="-1"
          />
          <div v-else class="pdf-placeholder">
            <q-icon name="description" size="48px" color="grey-5" />
            <div class="text-caption text-grey-6 q-mt-sm">{{ t('reports.noPdfPreview') }}</div>
          </div>

          <!-- Margin overlay -->
          <div v-if="pdfBlobUrl || loadingPdf" class="margin-overlay">
            <div class="margin-guide margin-top" :style="{ height: marginTopPx + 'px' }">
              <span class="margin-label">{{ t('reports.marginTop', { value: margins.top }) }}</span>
            </div>
            <div class="margin-guide margin-bottom" :style="{ height: marginBottomPx + 'px' }">
              <span class="margin-label">{{ t('reports.marginBottom', { value: margins.bottom }) }}</span>
            </div>
            <div class="margin-guide margin-left" :style="{ width: marginLeftPx + 'px' }">
              <span class="margin-label vertical">{{ t('reports.marginLeft', { value: margins.left }) }}</span>
            </div>
            <div class="margin-guide margin-right" :style="{ width: marginRightPx + 'px' }">
              <span class="margin-label vertical">{{ t('reports.marginRight', { value: margins.right }) }}</span>
            </div>
            <div class="printable-area" :style="printableAreaStyle">
              <div class="printable-label">{{ t('reports.printableArea') }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Save button -->
    <div class="calibrator-actions q-mt-sm row justify-end">
      <q-btn color="primary" unelevated :label="t('app.actions.save')" @click="save" />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../boot/axios'

const { t } = useI18n()

const props = defineProps({
  letterhead: { type: Object, required: true },
})

const emit = defineEmits(['save'])

// Match the backend PDF conversion (1 mm = 2.83465 pt) so the calibrator's
// margin overlay lines up with the actual rendered report margins.
const MM_TO_PX = 2.83465
const PAGE_W = 595
const PAGE_H = 842
const MIN_SCALE = 0.25
const MAX_SCALE = 3

const margins = reactive({
  top: Number(props.letterhead.margin_top_mm) || 20,
  bottom: Number(props.letterhead.margin_bottom_mm) || 20,
  left: Number(props.letterhead.margin_left_mm) || 20,
  right: Number(props.letterhead.margin_right_mm) || 20,
})

const pdfBlobUrl = ref(null)
const loadingPdf = ref(false)
const wrapperRef = ref(null)
const scale = ref(1)
const userZoom = ref(false)

const marginTopPx = computed(() => margins.top * MM_TO_PX)
const marginBottomPx = computed(() => margins.bottom * MM_TO_PX)
const marginLeftPx = computed(() => margins.left * MM_TO_PX)
const marginRightPx = computed(() => margins.right * MM_TO_PX)

const pageStyle = computed(() => ({
  width: PAGE_W + 'px',
  height: PAGE_H + 'px',
  transform: `scale(${scale.value})`,
  transformOrigin: 'top center',
}))

const canvasStyle = computed(() => ({
  width: PAGE_W * scale.value + 'px',
  height: PAGE_H * scale.value + 'px',
}))

const printableAreaStyle = computed(() => ({
  top: marginTopPx.value + 'px',
  bottom: marginBottomPx.value + 'px',
  left: marginLeftPx.value + 'px',
  right: marginRightPx.value + 'px',
}))

async function loadPdf() {
  if (!props.letterhead.asset_file_id) {
    pdfBlobUrl.value = null
    return
  }
  loadingPdf.value = true
  try {
    const response = await api.get(`/api/v1/storage/files/${props.letterhead.asset_file_id}/download`, {
      responseType: 'blob',
    })
    if (pdfBlobUrl.value) URL.revokeObjectURL(pdfBlobUrl.value)
    pdfBlobUrl.value = URL.createObjectURL(response.data)
  } catch {
    pdfBlobUrl.value = null
  } finally {
    loadingPdf.value = false
  }
}

function recalcScale() {
  if (!wrapperRef.value) return
  const padding = 32
  const availW = wrapperRef.value.clientWidth - padding
  const availH = wrapperRef.value.clientHeight - padding
  if (availW <= 0 || availH <= 0) return
  const fit = Math.min(availW / PAGE_W, availH / PAGE_H)
  scale.value = Math.max(MIN_SCALE, Math.min(MAX_SCALE, fit))
  userZoom.value = false
}

function zoomIn() {
  scale.value = Math.min(MAX_SCALE, scale.value * 1.2)
  userZoom.value = true
}

function zoomOut() {
  scale.value = Math.max(MIN_SCALE, scale.value / 1.2)
  userZoom.value = true
}

function fitToScreen() {
  recalcScale()
  userZoom.value = false
}

function save() {
  emit('save', {
    margin_top_mm: margins.top,
    margin_bottom_mm: margins.bottom,
    margin_left_mm: margins.left,
    margin_right_mm: margins.right,
  })
}

watch(() => props.letterhead.asset_file_id, loadPdf)

onMounted(async () => {
  await loadPdf()
  await nextTick()
  recalcScale()
  window.addEventListener('resize', () => {
    if (!userZoom.value) recalcScale()
  })
})

onUnmounted(() => {
  if (pdfBlobUrl.value) URL.revokeObjectURL(pdfBlobUrl.value)
})
</script>

<style scoped>
.calibrator-root {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.calibrator-toolbar {
  flex-shrink: 0;
}
.calibrator-canvas-wrapper {
  flex: 1;
  min-height: 0;
  overflow: auto;
  background: var(--q-color-step-1, #e0e0e0);
  border-radius: 4px;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 16px;
}
.calibrator-canvas {
  flex-shrink: 0;
  position: relative;
}
.page-container {
  position: relative;
  background: white;
  box-shadow: 0 2px 12px rgba(0,0,0,0.15);
  overflow: hidden;
}
.pdf-object {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border: none;
  pointer-events: none;
}
.pdf-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--q-color-bg, #f8f8f8);
}
.margin-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 10;
  pointer-events: none;
}
.margin-guide {
  position: absolute;
  background: rgba(255, 152, 0, 0.18);
  border: 1px solid rgba(255, 152, 0, 0.5);
}
.margin-top { top: 0; left: 0; right: 0; border-top: none; }
.margin-bottom { bottom: 0; left: 0; right: 0; border-bottom: none; }
.margin-left { top: 0; bottom: 0; left: 0; border-left: none; }
.margin-right { top: 0; bottom: 0; right: 0; border-right: none; }
.margin-label {
  position: absolute;
  bottom: 2px;
  left: 4px;
  font-size: 9px;
  color: #e65100;
  font-weight: 600;
  background: rgba(255,255,255,0.85);
  padding: 0 3px;
  border-radius: 2px;
}
.margin-label.vertical {
  bottom: auto;
  right: 2px;
  left: auto;
  writing-mode: vertical-rl;
  text-orientation: mixed;
}
.printable-area {
  position: absolute;
  border: 2px dashed #1976D2;
  background: rgba(25, 118, 210, 0.04);
}
.printable-label {
  position: absolute;
  top: 4px;
  left: 4px;
  font-size: 9px;
  color: #1976D2;
  font-weight: 600;
  background: rgba(255,255,255,0.85);
  padding: 1px 4px;
  border-radius: 2px;
}
.calibrator-actions {
  flex-shrink: 0;
}
</style>
