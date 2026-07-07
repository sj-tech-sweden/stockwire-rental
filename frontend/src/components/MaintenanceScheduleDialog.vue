<template>
  <q-dialog :model-value="modelValue" persistent>
    <q-card style="width: 560px; max-width: 95vw" class="ec-card">
      <q-card-section><div class="text-h6">{{ t('inventory.editMaintenanceSchedule') }}</div></q-card-section>
      <q-card-section class="q-pt-none">
        <q-form ref="formRef" @submit.prevent="save">
          <div class="row q-col-gutter-sm">
            <div class="col-12 col-md-6"><q-select v-model="form.maintenance_type" :options="maintenanceTypeOptions" :label="t('inventory.type')" outlined dense emit-value map-options /></div>
            <div class="col-12 col-md-6"><q-select v-model="form.interval_mode" :options="maintenanceIntervalModeOptions" :label="t('inventory.intervalMode')" outlined dense emit-value map-options /></div>
            <div class="col-12 col-md-6"><q-input v-model.number="form.interval_value" type="number" min="1" :label="form.interval_mode === 'runtime' ? t('inventory.hoursInterval') : t('inventory.daysInterval')" outlined dense /></div>
            <div class="col-12 col-md-6"><q-input v-model="form.scheduled_date" type="date" :label="t('inventory.scheduledDate')" outlined dense /></div>
            <div class="col-12"><q-input v-model="form.notes" type="textarea" autogrow :label="t('inventory.notes')" outlined dense /></div>
          </div>
          <q-banner v-if="error" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ error }}</q-banner>
        </q-form>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="emit('update:modelValue', false)" />
        <q-btn color="primary" unelevated :label="t('inventory.saveSchedule')" :loading="saving" @click="save" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQuasar } from 'quasar'
import { useInventoryStore } from '../stores/inventory'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  schedule: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const $q = useQuasar()
const { t } = useI18n()
const store = useInventoryStore()

const formRef = ref(null)
const saving = ref(false)
const error = ref('')
const editingId = ref(null)

const emptyForm = () => ({
  maintenance_type: 'inspection',
  interval_mode: 'calendar',
  interval_value: null,
  scheduled_date: new Date().toISOString().slice(0, 10),
  notes: '',
})

const form = ref(emptyForm())

const maintenanceTypeOptions = [
  { label: t('inventory.maintenanceTypeInspection'), value: 'inspection' },
  { label: t('inventory.maintenanceTypeCleaning'), value: 'cleaning' },
  { label: t('inventory.maintenanceTypeRepair'), value: 'repair' },
  { label: t('inventory.maintenanceTypeCalibration'), value: 'calibration' },
  { label: t('inventory.maintenanceTypePatTest'), value: 'pat_test' },
  { label: t('inventory.maintenanceTypeScheduled'), value: 'scheduled' },
  { label: t('inventory.maintenanceTypeModification'), value: 'modification' },
]

const maintenanceIntervalModeOptions = [
  { label: t('inventory.calendarTime'), value: 'calendar' },
  { label: t('inventory.runtimeHours'), value: 'runtime' },
]

function normalizeOptionalDate(value) {
  return value || null
}

watch(() => props.modelValue, (open) => {
  if (!open) return
  error.value = ''
  const scheduleId = Number(props.schedule?.schedule_id || props.schedule?.id || 0)
  editingId.value = scheduleId
  if (props.schedule) {
    form.value = {
      maintenance_type: props.schedule.maintenance_type || 'inspection',
      interval_mode: props.schedule.interval_mode || 'calendar',
      interval_value: props.schedule.interval_value ?? null,
      scheduled_date: props.schedule.scheduled_date || '',
      notes: props.schedule.notes || '',
    }
  } else {
    form.value = emptyForm()
  }
})

async function save() {
  const valid = await formRef.value?.validate()
  if (!valid) return
  if (!editingId.value) return

  saving.value = true
  error.value = ''
  try {
    const payload = {
      maintenance_type: form.value.maintenance_type || 'inspection',
      interval_mode: form.value.interval_mode || 'calendar',
      interval_value: form.value.interval_value,
      scheduled_date: normalizeOptionalDate(form.value.scheduled_date),
      notes: form.value.notes || null,
    }
    await store.updateMaintenanceSchedule(editingId.value, payload)
    emit('saved')
    emit('update:modelValue', false)
    $q.notify({ type: 'positive', message: 'Schedule and pending tasks updated' })
  } catch (err) {
    error.value = err?.response?.data?.detail || 'Failed to update maintenance schedule'
  } finally {
    saving.value = false
  }
}
</script>
