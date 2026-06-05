<template>
  <q-dialog v-model="defectDialogOpen" persistent>
        <q-card style="width: 95vw; max-width: 500px">
          <q-card-section class="row items-center q-pb-none">
            <div class="text-h6">{{ t('scan.defectReportDialogTitle') }}</div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup :disable="defectSaving" />
          </q-card-section>
          <q-card-section class="q-pt-sm">
            <q-input
              v-model="defectTitle"
              :label="t('scan.defectTitleLabel')"
              :placeholder="t('scan.defectTitlePlaceholder')"
              outlined
              dense
              class="q-mb-sm"
              :rules="[v => !!v?.trim() || t('scan.required')]"
              ref="defectTitleRef"
            />
            <q-input
              v-model="defectDescription"
              :label="t('scan.defectDescriptionLabel')"
              :placeholder="t('scan.defectDescriptionPlaceholder')"
              outlined
              dense
              type="textarea"
              autogrow
              class="q-mb-sm"
            />
            <q-select
              v-model="defectSeverity"
              :label="t('scan.defectSeverityLabel')"
              :options="defectSeverityOptions"
              outlined
              dense
              emit-value
              map-options
              class="q-mb-sm"
            />
            <q-file
              v-model="defectFiles"
              :label="t('scan.defectPhotosLabel')"
              outlined
              dense
              multiple
              accept="image/*"
              clearable
            >
              <template #prepend>
                <q-icon name="photo_camera" />
              </template>
            </q-file>
          </q-card-section>
          <q-card-actions align="right" class="q-pb-md q-pr-md">
            <q-btn flat :label="t('app.actions.cancel')" v-close-popup :disable="defectSaving" />
            <q-btn
              color="warning"
              unelevated
              icon="warning"
              :label="t('scan.markAsDefective')"
              :loading="defectSaving"
              @click="submitDefectReport"
            />
          </q-card-actions>
        </q-card>
      </q-dialog>
</template>

<script setup>
import { computed, ref } from 'vue'
import { api } from 'boot/axios'
import { useI18n } from 'vue-i18n'
import { Notify } from 'quasar'

const { t } = useI18n()


const props = defineProps({
  modelValue: Boolean,
  deviceId: {
    type: [String, Number],
    required: true,
  },
})

const emit = defineEmits([
  'update:modelValue',
  'success',
  'error',
])

const defectDialogOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const defectSeverityOptions = computed(() => [
  { label: t('scan.defectSeverityLow'), value: 'low' },
  { label: t('scan.defectSeverityMedium'), value: 'medium' },
  { label: t('scan.defectSeverityHigh'), value: 'high' },
  { label: t('scan.defectSeverityCritical'), value: 'critical' },
])

const defectTitleRef = ref(null)
const defectTitle = ref('')
const defectDescription = ref('')
const defectSeverity = ref('medium')
const defectFiles = ref(null)
const defectSaving = ref(false)

async function submitDefectReport() {
  const deviceId = props.deviceId
  if (!deviceId) return
  const title = String(defectTitle.value || '').trim()
  if (!title) {
    if (defectTitleRef.value) defectTitleRef.value.validate()
    return
  }

  defectSaving.value = true
  try {
    const { data: report } = await api.post('/api/v1/inventory/defect-reports', {
      device_id: deviceId,
      title,
      description: String(defectDescription.value || '').trim() || null,
      severity: defectSeverity.value || 'medium',
    })

    const files = defectFiles.value
      ? (Array.isArray(defectFiles.value) ? defectFiles.value : [defectFiles.value])
      : []

    let uploadFailed = false
    for (const file of files) {
      try {
        const formData = new FormData()
        formData.append('file', file)
        formData.append('entity_type', 'defect_report')
        formData.append('entity_id', String(report.id))
        formData.append('category', 'photo')
        await api.post('/api/v1/storage/files', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      } catch (uploadError) {
        console.error('Photo upload failed:', uploadError)
        uploadFailed = true
      }
    }

    
    Notify.create({
    type: uploadFailed ? 'warning' : 'positive',
    message: uploadFailed
        ? t('scan.defectPhotoUploadFailed')
        : t('scan.defectReportCreated')
    })
    emit('success', { report, uploadFailed })
    defectDialogOpen.value = false

  } catch (error) {
    Notify.create({
    type: 'negative',
    message:
        error?.response?.data?.detail ||
        t('scan.defectReportFailed')
    })
    emit('error', error)
  } finally {
    defectSaving.value = false
  }
}
</script>