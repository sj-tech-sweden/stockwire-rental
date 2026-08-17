<template>
  <div>
    <div class="row items-center justify-between q-mb-sm">
      <div class="text-subtitle1">{{ t('reports.letterheads') }}</div>
      <q-btn color="primary" icon="add" :label="t('reports.uploadLetterhead')" unelevated @click="showUpload = true" />
    </div>

    <div v-if="loading" class="text-caption text-grey-7">
      <q-spinner size="16px" class="q-mr-sm" />{{ t('app.actions.loading') }}
    </div>

    <div v-else-if="!letterheads.length" class="text-caption text-grey-7">
      {{ t('reports.noLetterheads') }}
    </div>

    <q-list v-else bordered separator class="rounded-borders">
      <q-item v-for="lh in letterheads" :key="lh.id">
        <q-item-section avatar>
          <q-icon name="description" color="primary" />
        </q-item-section>
        <q-item-section>
          <q-item-label>{{ lh.name }}</q-item-label>
          <q-item-label caption>
            {{ t('reports.pageCount', lh.page_count) }}
            · {{ t('reports.margins') }}: {{ lh.margin_top_mm }}/{{ lh.margin_bottom_mm }}/{{ lh.margin_left_mm }}/{{ lh.margin_right_mm }}mm
          </q-item-label>
        </q-item-section>
        <q-item-section side>
          <div class="row q-gutter-xs items-center">
            <q-badge v-if="lh.is_default" color="positive" :label="t('reports.default')" />
            <q-btn flat dense icon="tune" color="secondary" @click="openCalibrator(lh)" />
            <q-btn flat dense icon="delete" color="negative" @click="confirmDelete(lh)" />
          </div>
        </q-item-section>
      </q-item>
    </q-list>

    <!-- Upload Dialog -->
    <q-dialog v-model="showUpload" persistent>
      <q-card style="min-width: 400px" class="ec-card">
        <q-card-section>
          <div class="text-h6">{{ t('reports.uploadLetterhead') }}</div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-input v-model="uploadForm.name" :label="t('reports.letterheadName')" outlined dense class="q-mb-sm" :rules="[v => !!v || t('common.required')]" />
          <q-file v-model="uploadFile" :label="t('reports.selectPdfFile')" outlined dense accept=".pdf" class="q-mb-sm" />
          <q-toggle v-model="uploadForm.is_default" :label="t('reports.setAsDefault')" color="primary" />
          <div class="text-caption text-grey-7 q-mt-sm">{{ t('reports.marginHint') }}</div>
          <div class="row q-col-gutter-sm q-mt-xs">
            <div class="col-3">
              <q-input v-model.number="uploadForm.margin_top_mm" type="number" :label="t('reports.topMm')" outlined dense />
            </div>
            <div class="col-3">
              <q-input v-model.number="uploadForm.margin_bottom_mm" type="number" :label="t('reports.bottomMm')" outlined dense />
            </div>
            <div class="col-3">
              <q-input v-model.number="uploadForm.margin_left_mm" type="number" :label="t('reports.leftMm')" outlined dense />
            </div>
            <div class="col-3">
              <q-input v-model.number="uploadForm.margin_right_mm" type="number" :label="t('reports.rightMm')" outlined dense />
            </div>
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="cancelUpload" />
          <q-btn color="primary" unelevated :label="t('app.actions.upload')" :loading="uploading" :disable="!uploadFile" @click="doUpload" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Calibrator Dialog -->
    <q-dialog v-model="showCalibrator" persistent :maximized="$q.screen.lt.md">
      <q-card class="ec-card" style="width: 95vw; max-width: 95vw; height: 90vh; max-height: 90vh; display: flex; flex-direction: column">
        <q-card-section class="q-py-sm q-px-md" style="flex-shrink: 0">
          <div class="row items-center justify-between">
            <div class="text-subtitle1">{{ t('reports.marginCalibrator') }} — {{ calibratorLetterhead?.name }}</div>
            <q-btn flat dense round icon="close" @click="showCalibrator = false" />
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none col" style="flex: 1; min-height: 0; overflow: hidden">
          <LetterheadCalibrator
            v-if="calibratorLetterhead"
            :letterhead="calibratorLetterhead"
            @save="saveMargins"
          />
        </q-card-section>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useReportsStore } from '../stores/reports'
import LetterheadCalibrator from './LetterheadCalibrator.vue'

const $q = useQuasar()
const { t } = useI18n()
const reportsStore = useReportsStore()

const loading = ref(false)
const letterheads = ref([])
const showUpload = ref(false)
const uploading = ref(false)
const uploadFile = ref(null)
const uploadForm = ref({
  name: '',
  is_default: false,
  margin_top_mm: 20,
  margin_bottom_mm: 20,
  margin_left_mm: 20,
  margin_right_mm: 20,
})

const showCalibrator = ref(false)
const calibratorLetterhead = ref(null)

async function loadLetterheads() {
  loading.value = true
  try {
    letterheads.value = await reportsStore.fetchLetterheads()
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('reports.failedLoad') })
  } finally {
    loading.value = false
  }
}

async function doUpload() {
  if (!uploadFile.value) return
  uploading.value = true
  try {
    await reportsStore.uploadLetterhead(uploadFile.value, uploadForm.value)
    cancelUpload()
    $q.notify({ type: 'positive', message: t('reports.letterheadUploaded') })
    await loadLetterheads()
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('reports.failedUpload') })
  } finally {
    uploading.value = false
  }
}

function cancelUpload() {
  showUpload.value = false
  uploadFile.value = null
  uploadForm.value = { name: '', is_default: false, margin_top_mm: 20, margin_bottom_mm: 20, margin_left_mm: 20, margin_right_mm: 20 }
}

function openCalibrator(lh) {
  calibratorLetterhead.value = { ...lh }
  showCalibrator.value = true
}

async function saveMargins(margins) {
  try {
    await reportsStore.updateLetterhead(calibratorLetterhead.value.id, margins)
    showCalibrator.value = false
    $q.notify({ type: 'positive', message: t('reports.marginsSaved') })
    await loadLetterheads()
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('reports.failedSave') })
  }
}

function confirmDelete(lh) {
  $q.dialog({
    title: t('reports.deleteLetterhead'),
    message: t('reports.deleteLetterheadConfirm', { name: lh.name }),
    cancel: t('app.actions.cancel'),
    ok: t('app.actions.delete'),
    persistent: true,
  }).onOk(async () => {
    try {
      await reportsStore.deleteLetterhead(lh.id)
      $q.notify({ type: 'positive', message: t('reports.letterheadDeleted') })
      await loadLetterheads()
    } catch (err) {
      $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('reports.failedDelete') })
    }
  })
}

onMounted(loadLetterheads)
</script>
