<template>
  <q-dialog v-model="dialog" persistent>
    <q-card style="width: 620px; max-width: 95vw" class="ec-card">
      <q-card-section><div class="text-h6">{{ t('inventory.bulkEditDevices') }}</div></q-card-section>
      <q-card-section class="q-pt-none">
        <div class="text-caption text-grey-7 q-mb-sm">{{ t('inventory.updatingDevicesCount', { count: props.selectedDevices.length }) }}</div>
        <div class="row q-col-gutter-sm">
          <div class="col-12 col-md-4"><q-select v-model="form.status" :options="statusOptions" :label="t('inventory.status')" outlined dense clearable emit-value map-options /></div>
          <div class="col-12 col-md-4"><q-select v-model="form.condition" :options="conditionOptions" :label="t('inventory.condition')" outlined dense clearable emit-value map-options /></div>
          <div class="col-12 col-md-4"><q-select v-model="form.location_zone_id" :options="locationSelectOptions" :label="t('inventory.location')" outlined dense clearable emit-value map-options /></div>
          <div class="col-12 col-md-6">
            <q-select
              v-model="form.case_device_id"
              :options="caseDeviceOptions"
              :label="t('inventory.case')"
              outlined dense clearable emit-value map-options
              use-input input-debounce="0" fill-input
            />
          </div>
          <div class="col-12 col-md-6">
            <q-input v-model="form.pre_prep" :label="t('inventory.prepInstructions')" outlined dense clearable />
          </div>
          <div class="col-12">
            <q-input v-model="form.notes" :label="t('inventory.notes')" outlined dense clearable type="textarea" rows="2" />
          </div>
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
import { DEVICE_STATUSES, useInventoryStore } from '../stores/inventory'

const { t } = useI18n()
const $q = useQuasar()
const store = useInventoryStore()

const props = defineProps({
  modelValue: Boolean,
  selectedDevices: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const dialog = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const emptyForm = () => ({
  status: null,
  condition: null,
  location_zone_id: null,
  case_device_id: null,
  pre_prep: null,
  notes: null,
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

const DEVICE_STATUS_KEY_MAP = { available: 'Available', reserved: 'Reserved', in_use: 'InUse', maintenance: 'Maintenance' }
const statusOptions = DEVICE_STATUSES.map(item => ({ label: t('inventory.deviceStatus' + DEVICE_STATUS_KEY_MAP[item.value]), value: item.value }))

const conditionOptions = [
  { label: t('inventory.conditionExcellent'), value: 'excellent' },
  { label: t('inventory.conditionGood'), value: 'good' },
  { label: t('inventory.conditionFair'), value: 'fair' },
  { label: t('inventory.conditionDamaged'), value: 'damaged' },
]

const locationSelectOptions = computed(() => {
  const flat = [{ label: 'Unassigned', value: null }]
  const walk = (nodes, prefix) => {
    for (const node of nodes || []) {
      const label = prefix ? `${prefix} / ${node.name}` : node.name
      flat.push({ label, value: node.id })
      walk(node.children || [], label)
    }
  }
  walk(store.zoneTree)
  return flat
})

const caseDeviceOptions = computed(() => {
  const caseProductIds = new Set(
    (store.products || []).filter(p => p.product_type === 'case').map(p => p.id)
  )
  return (store.devices || [])
    .filter(d => caseProductIds.has(d.product_id))
    .map(d => ({ label: `${d.asset_tag}${d.serial_number ? ' (' + d.serial_number + ')' : ''}`, value: d.id }))
})

function selectedRowIds(rows) {
  return [...new Set((rows || []).map(row => Number(row?.id || 0)).filter(Boolean))]
}

async function save() {
  const ids = selectedRowIds(props.selectedDevices)
  if (!ids.length) return

  const patch = {}
  if (form.value.status) patch.status = form.value.status
  if (form.value.condition) patch.condition = form.value.condition
  if (form.value.location_zone_id != null) patch.location_zone_id = form.value.location_zone_id
  if (form.value.case_device_id != null) patch.case_device_id = form.value.case_device_id
  if (String(form.value.pre_prep || '').trim()) patch.pre_prep = String(form.value.pre_prep).trim()
  if (String(form.value.notes || '').trim()) patch.notes = String(form.value.notes).trim()

  if (!Object.keys(patch).length) {
    error.value = 'Choose at least one field to update'
    return
  }

  saving.value = true
  error.value = ''
  try {
    const result = await store.bulkUpdateDevices(ids, patch)
    dialog.value = false
    $q.notify({ type: 'positive', message: `Devices updated: ${result?.updated || 0}` })
    emit('saved')
  } catch (err) {
    error.value = err?.response?.data?.detail || 'Bulk device update failed'
  } finally {
    saving.value = false
  }
}
</script>
