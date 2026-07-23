<template>
  <q-dialog :model-value="modelValue" @update:model-value="emit('update:modelValue', $event)">
    <q-card style="min-width: 500px; max-width: 95vw" class="ec-card">
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6">{{ t('jobs.customFieldValues') }}</div>
        <q-space />
        <q-btn flat round dense icon="close" @click="emit('update:modelValue', false)" />
      </q-card-section>

      <q-card-section>
        <div v-if="!fieldRows.length" class="text-caption text-grey-7">
          {{ t('jobs.noJobCustomFields') }}
        </div>
        <div v-for="field in fieldRows" :key="field.field_definition_id" class="q-mb-sm">
          <q-input
            v-if="field.value_type === 'text'"
            v-model="field.value"
            :label="customFieldLabel(field.label)"
            outlined
            dense
          />
          <q-input
            v-else-if="field.value_type === 'number'"
            v-model.number="field.value"
            :label="customFieldLabel(field.label)"
            type="number"
            outlined
            dense
          />
          <q-select
            v-else-if="field.value_type === 'boolean'"
            v-model="field.value"
            :label="customFieldLabel(field.label)"
            :options="booleanOptions"
            outlined
            dense
            emit-value
            map-options
          />
          <q-input
            v-else-if="field.value_type === 'date'"
            v-model="field.value"
            :label="customFieldLabel(field.label)"
            type="date"
            outlined
            dense
          />
          <q-select
            v-else-if="field.value_type === 'select'"
            v-model="field.value"
            :label="customFieldLabel(field.label)"
            :options="(field.options || []).map(opt => customFieldOption(opt))"
            outlined
            dense
            emit-value
            map-options
            clearable
          />
        </div>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="emit('update:modelValue', false)" />
        <q-btn color="primary" unelevated :label="t('app.actions.save')" :loading="saving" @click="saveValues" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCustomFieldsStore } from '../stores/customFields'
import { translateMaybePrefillCustomFieldLabel, translateMaybePrefillCustomFieldOption } from '../i18n/prefillContent'

const props = defineProps({
  modelValue: Boolean,
  jobId: { type: Number, default: null },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const { t } = useI18n()
const customFieldsStore = useCustomFieldsStore()

const fieldRows = ref([])
const saving = ref(false)

const booleanOptions = [
  { label: t('common.true'), value: 'true' },
  { label: t('common.false'), value: 'false' },
]

function customFieldLabel(label) {
  return translateMaybePrefillCustomFieldLabel(label, t)
}

function customFieldOption(option) {
  return translateMaybePrefillCustomFieldOption(option, t)
}

function createEmptyFieldRows() {
  const defs = (customFieldsStore.definitions || []).filter(def => def.entity_type === 'job' && def.is_active !== false)
  return defs.map(def => ({
    field_definition_id: def.id,
    label: def.label,
    value_type: def.value_type,
    options: def.options || [],
    value: null,
  }))
}

async function loadFieldRows() {
  if (!props.jobId) {
    fieldRows.value = createEmptyFieldRows()
    return
  }
  try {
    const data = await customFieldsStore.fetchEntityValues('job', props.jobId)
    fieldRows.value = Array.isArray(data?.values) ? data.values.map(v => ({ ...v })) : createEmptyFieldRows()
  } catch {
    fieldRows.value = createEmptyFieldRows()
  }
}

async function saveValues() {
  if (!props.jobId) {
    emit('update:modelValue', false)
    return
  }
  saving.value = true
  try {
    await customFieldsStore.saveEntityValues('job', props.jobId, fieldRows.value.map(row => ({
      field_definition_id: row.field_definition_id,
      value: row.value,
    })))
    emit('saved')
    emit('update:modelValue', false)
  } finally {
    saving.value = false
  }
}

watch(() => props.modelValue, async (open) => {
  if (open) {
    if (!customFieldsStore.definitions.length) {
      await customFieldsStore.fetchFieldDefinitions()
    }
    await loadFieldRows()
  }
})
</script>
