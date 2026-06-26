<template>
  <q-dialog v-model="dialog" persistent>
    <q-card style="width: 520px; max-width: 95vw" class="ec-card">
      <q-card-section><div class="text-h6">{{ t('inventory.bulkEditSchedules') }}</div></q-card-section>
      <q-card-section class="q-pt-none">
        <div class="text-caption text-grey-7 q-mb-sm">{{ t('inventory.updatingSchedulesCount', { count: props.selectedSchedules.length }) }}</div>
        <div class="row q-col-gutter-sm">
          <div class="col-12 col-md-6"><q-select v-model="form.maintenance_type" :options="maintenanceTypeOptions" :label="t('inventory.type')" outlined dense clearable emit-value map-options /></div>
          <div class="col-12 col-md-6"><q-select v-model="form.interval_mode" :options="maintenanceIntervalModeOptions" :label="t('inventory.intervalMode')" outlined dense clearable emit-value map-options /></div>
          <div class="col-12 col-md-6"><q-input v-model.number="form.interval_value" type="number" min="1" :label="form.interval_mode === 'runtime' ? t('inventory.hoursInterval') : t('inventory.daysInterval')" outlined dense clearable /></div>
          <div class="col-12 col-md-6"><q-input v-model="form.scheduled_date" type="date" :label="t('inventory.scheduledDate')" outlined dense clearable /></div>
          <div class="col-12"><q-input v-model="form.notes" type="textarea" autogrow :label="t('inventory.notes')" outlined dense clearable /></div>
        </div>
        <q-banner v-if="error" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ error }}</q-banner>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="dialog = false" />
        <q-btn color="primary" unelevated :label="t('inventory.apply')" :loading="saving" @click="save" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQuasar } from 'quasar'
import { useInventoryStore } from 'src/stores/inventory'

const { t } = useI18n()
const $q = useQuasar()
const store = useInventoryStore()

const props = defineProps({
  modelValue: Boolean,
  selectedSchedules: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const dialog = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const emptyForm = () => ({
  maintenance_type: null,
  interval_mode: null,
  interval_value: null,
  scheduled_date: '',
  notes: '',
})

const form = ref(emptyForm())

watch(() => props.modelValue, (val) => {
  if (val) {
    form.value = emptyForm()
    error.value = ''
  }
})

const error = ref('')
const saving = ref(false)

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

function selectedRowIds(rows) {
  return [...new Set((rows || []).map(row => Number(row?.id || 0)).filter(Boolean))]
}

async function save() {
  const ids = selectedRowIds(props.selectedSchedules)
  if (!ids.length) return

  const patch = {}
  if (form.value.maintenance_type) patch.maintenance_type = form.value.maintenance_type
  if (form.value.interval_mode) patch.interval_mode = form.value.interval_mode
  if (form.value.interval_value != null) patch.interval_value = Number(form.value.interval_value)
  if (form.value.scheduled_date) patch.scheduled_date = normalizeOptionalDate(form.value.scheduled_date)
  if (String(form.value.notes || '').trim()) patch.notes = String(form.value.notes).trim()

  if (!Object.keys(patch).length) {
    error.value = 'Choose at least one field to update'
    return
  }

  saving.value = true
  error.value = ''
  try {
    const result = await store.bulkUpdateMaintenanceSchedules(ids, patch)
    dialog.value = false
    $q.notify({ type: 'positive', message: `Schedules updated: ${result?.updated || 0}` })
    emit('saved')
  } catch (err) {
    error.value = err?.response?.data?.detail || 'Bulk schedule update failed'
  } finally {
    saving.value = false
  }
}
</script>
