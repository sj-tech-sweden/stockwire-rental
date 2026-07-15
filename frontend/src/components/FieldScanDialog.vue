<template>
  <q-dialog :model-value="modelValue" persistent @hide="stopCapture" @update:model-value="$emit('update:modelValue', $event)">
    <q-card style="width: 560px; max-width: 95vw" class="ec-card device-capture-card">
      <q-card-section class="text-center">
        <div class="device-capture-icon-wrap q-mb-sm">
          <q-icon name="qr_code_scanner" size="34px" color="white" />
        </div>
        <div class="text-h6 text-white">{{ t('inventory.captureField', { field: fieldLabel }) }}</div>
        <div class="text-caption text-grey-4">{{ t('inventory.scanWithKeyboardCameraNfc') }}</div>
      </q-card-section>
      <q-card-section class="q-pt-none">
        <div class="row q-gutter-sm q-mb-md justify-center">
          <q-btn-toggle
            v-model="mode"
            toggle-color="primary"
            color="grey-9"
            text-color="grey-3"
            unelevated
            no-caps
            :options="modeButtons"
          />
        </div>

        <div class="row q-col-gutter-sm">
          <div class="col-12">
            <q-input ref="captureInputRef" v-model="captureValue" :label="t('inventory.scannerKeyboardInput')" outlined dense @keyup.enter="applyValue">
              <template #append>
                <q-btn flat dense round color="primary" icon="check" @click="applyValue" />
              </template>
            </q-input>
          </div>
          <div class="col-12 text-caption text-grey-5">
            {{ t('inventory.captureModeHelpText') }}
          </div>
          <div class="col-12 row q-gutter-sm" v-if="mode === 'keyboard'">
            <q-btn color="secondary" outline icon="keyboard" :label="t('inventory.focusTargetField')" @click="$emit('focus-target')" />
          </div>
          <div class="col-12" v-if="cameraActive">
            <div class="device-capture-camera-wrap">
              <video ref="videoRef" class="device-capture-video" autoplay muted playsinline />
            </div>
            <canvas ref="ocrCanvasRef" style="display: none" />
            <div class="text-caption text-grey-5 q-mt-xs">
              {{ mode === 'ocr' ? t('inventory.pointCameraToText') : t('inventory.pointCameraToBarcode') }}
            </div>
            <div v-if="mode === 'ocr'" class="row q-mt-sm">
              <q-btn color="primary" unelevated icon="document_scanner" :label="t('inventory.captureText')" :loading="ocrLoading" @click="captureOcrFrame" />
            </div>
            <div v-if="ocrCandidates.length" class="q-mt-sm">
              <div class="text-caption text-grey-4 q-mb-xs">{{ t('inventory.ocrSelectText') }}</div>
              <q-list dense bordered class="rounded-borders">
                <q-item v-for="(candidate, idx) in ocrCandidates" :key="idx" clickable v-ripple @click="applyOcrCandidate(candidate)">
                  <q-item-section>{{ candidate }}</q-item-section>
                  <q-item-section side>
                    <q-icon name="check_circle" color="primary" />
                  </q-item-section>
                </q-item>
              </q-list>
            </div>
          </div>
          <div class="col-12" v-if="mode === 'nfc'">
            <div class="device-capture-nfc-wrap text-center">
              <q-icon name="nfc" size="40px" :color="nfcActive ? 'primary' : 'grey-5'" />
              <div class="text-caption q-mt-sm" :class="nfcActive ? 'text-primary' : 'text-grey-5'">
                {{ nfcActive ? t('inventory.nfcReadyHoldTag') : t('inventory.startingNfcReader') }}
              </div>
            </div>
          </div>
        </div>
        <q-banner v-if="captureError" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ captureError }}</q-banner>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.close')" @click="$emit('update:modelValue', false)" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  fieldLabel: { type: String, default: '' },
  initialValue: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'captured', 'focus-target'])

const { t } = useI18n()

const captureInputRef = ref(null)
const videoRef = ref(null)
const ocrCanvasRef = ref(null)
const captureValue = ref('')
const captureError = ref('')
const mode = ref('keyboard')
const cameraActive = ref(false)
const nfcActive = ref(false)
const stream = ref(null)
const raf = ref(null)
const nfcController = ref(null)
const ocrLoading = ref(false)
const ocrCandidates = ref([])
let ocrWorkerInstance = null
const OCR_MIN_CONFIDENCE = 30
const OCR_MAX_CANDIDATES = 6

const supportsCamera = computed(() => {
  if (typeof window === 'undefined') return false
  return typeof window.BarcodeDetector === 'function' && !!navigator.mediaDevices?.getUserMedia
})
const supportsNfc = computed(() => {
  if (typeof window === 'undefined') return false
  return !!window.isSecureContext && typeof window.NDEFReader === 'function'
})
const supportsOcr = computed(() => {
  if (typeof window === 'undefined') return false
  return !!navigator.mediaDevices?.getUserMedia
})
const modeButtons = computed(() => {
  const buttons = [{ label: t('inventory.deviceDialog.keyboard'), value: 'keyboard', icon: 'keyboard' }]
  if (supportsCamera.value) buttons.push({ label: t('inventory.deviceDialog.camera'), value: 'camera', icon: 'photo_camera' })
  if (supportsNfc.value) buttons.push({ label: t('inventory.deviceDialog.nfc'), value: 'nfc', icon: 'nfc' })
  if (supportsOcr.value) buttons.push({ label: t('inventory.deviceDialog.ocr'), value: 'ocr', icon: 'document_scanner' })
  return buttons
})

watch(() => props.modelValue, (open) => {
  if (open) {
    captureValue.value = props.initialValue || ''
    captureError.value = ''
    mode.value = 'keyboard'
    focusCaptureInput()
  } else {
    stopCapture()
  }
})

watch(mode, (m) => {
  if (!props.modelValue) return
  if (m === 'keyboard') {
    stopCapture()
    focusCaptureInput()
    return
  }
  if (m === 'camera') { void startCameraCapture(); return }
  if (m === 'nfc') { void startNfcCapture(); return }
  if (m === 'ocr') { void startOcrCapture() }
})

function focusCaptureInput() {
  if (!props.modelValue) return
  if (mode.value !== 'keyboard') return
  nextTick(() => { captureInputRef.value?.focus?.() })
}

function applyValue() {
  if (captureValue.value) {
    emit('captured', captureValue.value)
    emit('update:modelValue', false)
  }
}

function stopCapture() {
  if (raf.value) { cancelAnimationFrame(raf.value); raf.value = null }
  if (nfcController.value) { nfcController.value.abort(); nfcController.value = null }
  if (stream.value) {
    for (const track of stream.value.getTracks()) track.stop()
    stream.value = null
  }
  if (videoRef.value) videoRef.value.srcObject = null
  cameraActive.value = false
  nfcActive.value = false
  ocrCandidates.value = []
  ocrLoading.value = false
}

async function startCameraCapture() {
  captureError.value = ''
  if (!supportsCamera.value) { captureError.value = 'Camera not supported'; return }
  if (!navigator.mediaDevices?.getUserMedia) { captureError.value = 'Camera not available'; return }
  stopCapture()
  try {
    const s = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } } })
    stream.value = s
    cameraActive.value = true
    await nextTick()
    const videoEl = videoRef.value
    if (!videoEl) { captureError.value = 'Camera preview unavailable'; return }
    videoEl.srcObject = s
    await videoEl.play()
    const detector = new window.BarcodeDetector({
      formats: ['qr_code', 'code_128', 'code_39', 'ean_13', 'ean_8', 'upc_a', 'upc_e'],
    })
    const detectLoop = async () => {
      if (!props.modelValue || !cameraActive.value) return
      try {
        const codes = await detector.detect(videoEl)
        const first = Array.isArray(codes) && codes.length ? codes[0] : null
        const value = String(first?.rawValue || '').trim()
        if (value) {
          captureValue.value = value
          emit('captured', value)
          emit('update:modelValue', false)
          stopCapture()
          return
        }
      } catch { /* continue scanning */ }
      raf.value = requestAnimationFrame(detectLoop)
    }
    raf.value = requestAnimationFrame(detectLoop)
  } catch (error) {
    captureError.value = error?.message || 'Unable to start camera'
    stopCapture()
  }
}

function parseNfcRecordValue(record) {
  try {
    if (!record?.data) return ''
    const decoder = new TextDecoder(record.encoding || 'utf-8')
    return decoder.decode(record.data).trim()
  } catch { return '' }
}

async function startNfcCapture() {
  captureError.value = ''
  if (!supportsNfc.value) { captureError.value = 'NFC not supported'; return }
  stopCapture()
  try {
    const ndef = new window.NDEFReader()
    const controller = new AbortController()
    nfcController.value = controller
    await ndef.scan({ signal: controller.signal })
    nfcActive.value = true
    ndef.onreadingerror = () => { captureError.value = 'NFC read error' }
    ndef.onreading = (event) => {
      const records = event?.message?.records || []
      for (const record of records) {
        const value = parseNfcRecordValue(record)
        if (value) {
          captureValue.value = value
          emit('captured', value)
          emit('update:modelValue', false)
          stopCapture()
          return
        }
      }
      captureError.value = 'NFC tag has no text payload'
    }
  } catch (error) {
    captureError.value = error?.message || 'Unable to start NFC'
    stopCapture()
  }
}

async function startOcrCapture() {
  captureError.value = ''
  ocrCandidates.value = []
  if (!supportsOcr.value) { captureError.value = 'OCR not supported'; return }
  if (!navigator.mediaDevices?.getUserMedia) { captureError.value = 'Camera not available'; return }
  stopCapture()
  try {
    const s = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } } })
    stream.value = s
    cameraActive.value = true
    await nextTick()
    const videoEl = videoRef.value
    if (!videoEl) { captureError.value = 'Camera preview unavailable'; stopCapture(); return }
    videoEl.srcObject = s
    await videoEl.play()
  } catch (error) {
    captureError.value = error?.message || 'Unable to start camera'
    stopCapture()
  }
}

async function captureOcrFrame() {
  const videoEl = videoRef.value
  if (!videoEl || !cameraActive.value) return
  ocrLoading.value = true
  ocrCandidates.value = []
  captureError.value = ''
  try {
    const canvas = ocrCanvasRef.value
    canvas.width = videoEl.videoWidth || 640
    canvas.height = videoEl.videoHeight || 480
    const ctx = canvas.getContext('2d')
    ctx.drawImage(videoEl, 0, 0)
    const imageDataUrl = canvas.toDataURL('image/png')
    if (!ocrWorkerInstance) {
      const { createWorker } = await import('tesseract.js')
      ocrWorkerInstance = await createWorker()
      await ocrWorkerInstance.loadLanguage('eng')
      await ocrWorkerInstance.initialize('eng')
    }
    const { data } = await ocrWorkerInstance.recognize(imageDataUrl)
    const candidates = (data.lines || [])
      .filter(line => line.confidence > OCR_MIN_CONFIDENCE)
      .map(line => line.text.replace(/\s+/g, ' ').trim())
      .filter(text => text.length > 1)
      .slice(0, OCR_MAX_CANDIDATES)
    ocrCandidates.value = candidates
    if (!candidates.length) captureError.value = 'No text found in image'
  } catch {
    captureError.value = 'OCR failed'
  } finally {
    ocrLoading.value = false
  }
}

function applyOcrCandidate(text) {
  captureValue.value = text
  emit('captured', text)
  emit('update:modelValue', false)
}

onUnmounted(() => stopCapture())
</script>

<style scoped>
.device-capture-card { background: #1a1a2e; }
.device-capture-icon-wrap {
  width: 60px; height: 60px; border-radius: 50%;
  background: rgba(255,255,255,0.1); display: inline-flex;
  align-items: center; justify-content: center;
}
.device-capture-camera-wrap {
  width: 100%; max-height: 200px; overflow: hidden;
  border-radius: 8px; background: #000;
}
.device-capture-video { width: 100%; height: auto; object-fit: cover; }
</style>
