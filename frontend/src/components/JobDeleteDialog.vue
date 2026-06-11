<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="emit('update:modelValue', $event)">
    <q-card class="ec-card">
      <q-card-section class="row items-center">
        <q-icon name="warning" color="negative" size="md" class="q-mr-md" />
        <span>{{ t('jobs.deletePrompt', { code: job?.job_code || '' }) }}</span>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="emit('update:modelValue', false)" />
        <q-btn v-if="authStore.canEdit" color="negative" unelevated :label="t('jobs.delete')" :loading="saving" @click="doDelete" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useJobsStore } from '../stores/jobs'
import { useAuthStore } from '../stores/auth'

const props = defineProps({
  modelValue: Boolean,
  job: { type: Object, default: null },
})

const emit = defineEmits([
  'update:modelValue',
  'deleted',
])

const $q = useQuasar()
const { t } = useI18n()
const jobsStore = useJobsStore()
const authStore = useAuthStore()

const saving = ref(false)

async function doDelete() {
  saving.value = true
  try {
    await jobsStore.deleteJob(props.job.id)
    emit('update:modelValue', false)
    $q.notify({ type: 'positive', message: t('jobs.jobDeleted') })
    emit('deleted')
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('common.deleteFailed') })
  } finally {
    saving.value = false
  }
}
</script>
