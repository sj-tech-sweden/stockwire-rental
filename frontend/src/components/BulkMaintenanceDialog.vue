<template>
  <q-dialog v-model="dialog" persistent>
    <q-card style="width: 520px; max-width: 95vw" class="ec-card">
      <q-card-section><div class="text-h6">{{ t('inventory.bulkEditMaintenanceTasks') }}</div></q-card-section>
      <q-card-section class="q-pt-none">
        <div class="text-caption text-grey-7 q-mb-sm">{{ t('inventory.updatingTasksCount', { count: props.selectedTasks.length }) }}</div>
        <div class="row q-col-gutter-sm">
          <div class="col-12 col-md-6"><q-select v-model="form.status" :options="maintenanceStatusOptions" :label="t('inventory.status')" outlined dense clearable emit-value map-options /></div>
          <div class="col-12 col-md-6"><q-select v-model="form.maintenance_type" :options="maintenanceTypeOptions" :label="t('inventory.type')" outlined dense clearable emit-value map-options /></div>
          <div class="col-12 col-md-6"><q-input v-model="form.scheduled_date" type="date" :label="t('inventory.scheduledDate')" outlined dense clearable /></div>
          <div class="col-12 col-md-6"><q-input v-model="form.completed_date" type="date" :label="t('inventory.completedDate')" outlined dense clearable /></div>
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
  selectedTasks: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const dialog = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const emptyForm = () => ({
  status: null,
  maintenance_type: null,
  scheduled_date: '',
  completed_date: '',
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

const maintenanceStatusOptions = [
  { label: t('inventory.maintenanceStatusScheduled'), value: 'scheduled' },
  { label: t('inventory.maintenanceStatusInProgress'), value: 'in_progress' },
  { label: t('inventory.maintenanceStatusCompleted'), value: 'completed' },
  { label: t('inventory.maintenanceStatusCanceled'), value: 'canceled' },
]

const maintenanceTypeOptions = [
  { label: t('inventory.maintenanceTypeInspection'), value: 'inspection' },
  { label: t('inventory.maintenanceTypeCleaning'), value: 'cleaning' },
  { label: t('inventory.maintenanceTypeRepair'), value: 'repair' },
  { label: t('inventory.maintenanceTypeCalibration'), value: 'calibration' },
  { label: t('inventory.maintenanceTypePatTest'), value: 'pat_test' },
  { label: t('inventory.maintenanceTypeScheduled'), value: 'scheduled' },
  { label: t('inventory.maintenanceTypeModification'), value: 'modification' },
]

function normalizeOptionalDate(value) {
  return value || null
}

function selectedRowIds(rows) {
  return [...new Set((rows || []).map(row => Number(row?.id || 0)).filter(Boolean))]
}

async function save() {
  const ids = selectedRowIds(props.selectedTasks)
  if (!ids.length) return

  const patch = {}
  if (form.value.status) patch.status = form.value.status
  if (form.value.maintenance_type) patch.maintenance_type = form.value.maintenance_type
  if (form.value.scheduled_date) patch.scheduled_date = normalizeOptionalDate(form.value.scheduled_date)
  if (form.value.completed_date) patch.completed_date = normalizeOptionalDate(form.value.completed_date)

  if (!Object.keys(patch).length) {
    error.value = 'Choose at least one field to update'
    return
  }

  saving.value = true
  error.value = ''
  try {
    const result = await store.bulkUpdateMaintenance(ids, patch)
    dialog.value = false
    $q.notify({ type: 'positive', message: `Maintenance tasks updated: ${result?.updated || 0}` })
    emit('saved')
  } catch (err) {
    error.value = err?.response?.data?.detail || 'Bulk maintenance update failed'
  } finally {
    saving.value = false
  }
}
</script>
