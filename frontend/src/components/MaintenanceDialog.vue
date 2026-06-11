<template>
  <q-dialog :model-value="modelValue" persistent>
    <q-card style="width: 720px; max-width: 95vw" class="ec-card">
      <q-card-section><div class="text-h6">{{ dialogTitle }}</div></q-card-section>
      <q-card-section class="q-pt-none">
        <q-form ref="formRef" @submit.prevent="save">
          <div class="row q-col-gutter-sm">
            <div class="col-12" v-if="!task && mode === 'schedule'">
              <q-expansion-item v-model="targetsExpanded" icon="tune" :label="t('inventory.targetsProductsDevices')" dense>
                <div class="q-pt-sm">
                  <q-banner dense class="bg-info text-white rounded-borders q-mb-sm">
                    {{ t('inventory.productSchedulesBanner') }}
                  </q-banner>
                  <div class="row q-col-gutter-sm">
                    <div class="col-12 col-md-6">
                      <q-select
                        v-model="form.product_ids"
                        :options="productOptions"
                        :label="t('inventory.products')"
                        outlined
                        dense
                        multiple
                        use-chips
                        emit-value
                        map-options
                      />
                    </div>
                    <div class="col-12 col-md-6">
                      <q-select
                        v-model="form.device_ids"
                        :options="deviceSelectOptions"
                        :label="t('inventory.additionalSpecificDevicesOptional')"
                        outlined
                        dense
                        multiple
                        use-chips
                        emit-value
                        map-options
                      />
                    </div>
                  </div>
                </div>
              </q-expansion-item>
            </div>
            <div class="col-12" v-if="!task && mode === 'task'">
              <q-banner dense class="bg-info text-white rounded-borders q-mb-sm">
                {{ t('inventory.directMaintenanceTaskBanner') }}
              </q-banner>
              <q-select
                v-model="form.device_ids"
                :options="deviceSelectOptions"
                :label="t('inventory.device')"
                outlined
                dense
                multiple
                use-chips
                emit-value
                map-options
              />
            </div>
            <div class="col-12 col-md-6" v-if="task">
              <q-select
                v-model="form.device_ids"
                :options="deviceSelectOptions"
                :label="t('inventory.device')"
                outlined
                dense
                multiple
                use-chips
                emit-value
                map-options
              />
            </div>
            <div class="col-12 col-md-6"><q-select v-model="form.maintenance_type" :options="maintenanceTypeOptions" :label="t('inventory.type')" outlined dense emit-value map-options /></div>
            <div class="col-12 col-md-4" v-if="task || mode === 'task'"><q-select v-model="form.status" :options="maintenanceStatusOptions" :label="t('inventory.status')" outlined dense emit-value map-options /></div>
            <div class="col-12 col-md-4" v-if="task || mode === 'schedule'"><q-select v-model="form.interval_mode" :options="maintenanceIntervalModeOptions" :label="t('inventory.intervalMode')" outlined dense emit-value map-options /></div>
            <div class="col-12 col-md-4" v-if="task || mode === 'schedule'"><q-input v-model.number="form.interval_value" type="number" min="1" :label="form.interval_mode === 'runtime' ? t('inventory.hoursInterval') : t('inventory.daysInterval')" outlined dense /></div>
            <div class="col-12 col-md-4"><q-input v-model="form.scheduled_date" type="date" :label="t('inventory.scheduledDate')" outlined dense /></div>
            <div class="col-12 col-md-4" v-if="task || mode === 'task'"><q-input v-model="form.completed_date" type="date" :label="t('inventory.completedDate')" outlined dense /></div>
            <div class="col-12"><q-input v-model="form.notes" type="textarea" autogrow :label="t('inventory.notes')" outlined dense /></div>
          </div>
          <q-banner v-if="error" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ error }}</q-banner>
        </q-form>
      </q-card-section>
      <EntityAttachmentsPanel
        entity-type="maintenance"
        :entity-id="task?.id || null"
        :title="t('inventory.maintenanceDocuments')"
        default-category="maintenance-document"
      />
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="emit('update:modelValue', false)" />
        <q-btn color="primary" unelevated :label="task ? t('app.actions.save') : t('users.create')" :loading="saving" @click="save" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQuasar } from 'quasar'
import { useInventoryStore } from 'src/stores/inventory'
import EntityAttachmentsPanel from 'src/components/EntityAttachmentsPanel.vue'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  task: { type: Object, default: null },
  mode: { type: String, default: 'task' },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const $q = useQuasar()
const { t } = useI18n()
const store = useInventoryStore()

const formRef = ref(null)
const targetsExpanded = ref(true)
const saving = ref(false)
const error = ref('')

const emptyForm = () => ({
  product_ids: [],
  device_ids: [],
  maintenance_type: 'inspection',
  status: 'scheduled',
  interval_mode: 'calendar',
  interval_value: null,
  scheduled_date: new Date().toISOString().slice(0, 10),
  completed_date: '',
  notes: '',
})

const form = ref(emptyForm())

const dialogTitle = computed(() => {
  if (props.task) return 'Edit maintenance'
  return props.mode === 'task' ? 'Create maintenance task' : 'Create maintenance schedule'
})

const maintenanceTypeOptions = [
  { label: t('inventory.maintenanceTypeInspection'), value: 'inspection' },
  { label: t('inventory.maintenanceTypeCleaning'), value: 'cleaning' },
  { label: t('inventory.maintenanceTypeRepair'), value: 'repair' },
  { label: t('inventory.maintenanceTypeCalibration'), value: 'calibration' },
  { label: t('inventory.maintenanceTypePatTest'), value: 'pat_test' },
  { label: t('inventory.maintenanceTypeScheduled'), value: 'scheduled' },
]

const maintenanceStatusOptions = [
  { label: t('inventory.maintenanceStatusScheduled'), value: 'scheduled' },
  { label: t('inventory.maintenanceStatusInProgress'), value: 'in_progress' },
  { label: t('inventory.maintenanceStatusCompleted'), value: 'completed' },
  { label: t('inventory.maintenanceStatusCanceled'), value: 'canceled' },
]

const maintenanceIntervalModeOptions = [
  { label: t('inventory.calendarTime'), value: 'calendar' },
  { label: t('inventory.runtimeHours'), value: 'runtime' },
]

const productOptions = computed(() =>
  store.products.map(p => ({ label: `${p.sku} - ${p.name}`, value: p.id }))
)

const deviceSelectOptions = computed(() =>
  store.devices.map(d => {
    const zone = store.zones.find(z => z.id === d.location_zone_id)
    const zoneName = zone?.name || 'Unassigned'
    return { label: `${d.asset_tag} (${zoneName})`, value: d.id }
  })
)

function normalizeOptionalDate(value) {
  return value || null
}

watch(() => props.modelValue, (open) => {
  if (!open) return
  error.value = ''
  targetsExpanded.value = true
  if (props.task) {
    form.value = {
      product_ids: props.task.product_id ? [props.task.product_id] : [],
      device_ids: props.task.device_id ? [props.task.device_id] : [],
      maintenance_type: props.task.maintenance_type || 'inspection',
      status: props.task.status || 'scheduled',
      interval_mode: props.task.interval_mode || 'calendar',
      interval_value: props.task.interval_value ?? null,
      scheduled_date: props.task.scheduled_date || '',
      completed_date: props.task.completed_date || '',
      notes: props.task.notes || '',
    }
  } else {
    form.value = emptyForm()
  }
})

async function save() {
  const valid = await formRef.value?.validate()
  if (!valid) return

  if (!props.task && props.mode === 'schedule' && form.value.product_ids.length === 0 && form.value.device_ids.length === 0) {
    error.value = 'Select at least one product or device'
    return
  }

  if (!props.task && props.mode === 'task' && form.value.device_ids.length === 0) {
    error.value = 'Select one device for the task'
    return
  }

  if (props.task && form.value.device_ids.length === 0) {
    error.value = 'Device is required when editing'
    return
  }

  saving.value = true
  error.value = ''
  try {
    const payload = {
      device_id: form.value.device_ids[0],
      maintenance_type: form.value.maintenance_type || 'inspection',
      status: (props.task || props.mode === 'task')
        ? (form.value.status || 'scheduled')
        : 'scheduled',
      scheduled_date: normalizeOptionalDate(form.value.scheduled_date),
      completed_date: normalizeOptionalDate(form.value.completed_date),
      notes: form.value.notes || null,
    }

    if (props.task || props.mode === 'schedule') {
      payload.interval_mode = form.value.interval_mode || 'calendar'
      payload.interval_value = form.value.interval_value
    }

    if (props.task) {
      await store.updateMaintenance(props.task.id, payload)
      $q.notify({ type: 'positive', message: 'Maintenance updated' })
    } else if (props.mode === 'task') {
      await store.createMaintenance(payload)
      $q.notify({ type: 'positive', message: 'Maintenance task created' })
    } else {
      const records = await store.bulkScheduleMaintenance({
        device_ids: form.value.device_ids,
        product_ids: form.value.product_ids,
        maintenance_type: payload.maintenance_type,
        interval_mode: payload.interval_mode,
        interval_value: payload.interval_value,
        scheduled_date: payload.scheduled_date,
        notes: payload.notes,
      })
      $q.notify({ type: 'positive', message: `${records.length} maintenance items scheduled` })
    }
    emit('saved')
    emit('update:modelValue', false)
  } catch (err) {
    error.value = err?.response?.data?.detail || 'Failed to save maintenance'
  } finally {
    saving.value = false
  }
}
</script>
