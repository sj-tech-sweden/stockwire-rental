<template>
  <q-dialog :model-value="modelValue" persistent>
    <q-card style="width: 520px; max-width: 95vw" class="ec-card">
      <q-card-section>
        <div class="text-h6">{{ t('inventory.completeMaintenanceTask') }}</div>
        <div class="text-caption text-grey-7" v-if="task">
          {{ task.asset_tag || t('inventory.noAssetTag') }} · {{ task.maintenance_type || t('inventory.maintenance') }}
        </div>
      </q-card-section>
      <q-card-section class="q-pt-none">
        <div class="row q-col-gutter-sm">
          <div class="col-12 col-md-6"><q-input v-model="form.completed_date" type="date" :label="t('inventory.completedDate')" outlined dense /></div>
          <div class="col-12"><q-input v-model="form.notes" type="textarea" autogrow :label="t('inventory.completionNotes')" outlined dense /></div>
        </div>
        <q-banner v-if="error" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ error }}</q-banner>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="emit('update:modelValue', false)" />
        <q-btn color="positive" unelevated :label="t('inventory.complete')" :loading="saving" @click="save" />
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
  task: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const $q = useQuasar()
const { t } = useI18n()
const store = useInventoryStore()

const saving = ref(false)
const error = ref('')

const emptyForm = () => ({
  completed_date: new Date().toISOString().slice(0, 10),
  notes: '',
})

const form = ref(emptyForm())

watch(() => props.modelValue, (open) => {
  if (!open) return
  error.value = ''
  form.value = {
    completed_date: props.task?.completed_date || new Date().toISOString().slice(0, 10),
    notes: props.task?.notes || '',
  }
})

async function save() {
  const item = props.task
  if (!item?.id) return

  saving.value = true
  error.value = ''
  try {
    const completedDate = (form.value.completed_date) || new Date().toISOString().slice(0, 10)
    const notes = String(form.value.notes || '').trim() || null
    await store.completeMaintenance(item.id, {
      completed_date: completedDate,
      notes,
    })
    emit('saved')
    emit('update:modelValue', false)
    form.value = emptyForm()
    $q.notify({ type: 'positive', message: 'Maintenance completed' })
  } catch (err) {
    error.value = err?.response?.data?.detail || 'Failed to complete maintenance'
  } finally {
    saving.value = false
  }
}
</script>
