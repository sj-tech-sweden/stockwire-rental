<template>
  <q-dialog :model-value="modelValue" @update:model-value="emit('update:modelValue', $event)">
    <q-card style="min-width: 500px; max-width: 95vw" class="ec-card">
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6">{{ t('customers.customFieldValues') }}</div>
        <q-space />
        <q-btn flat round dense icon="close" @click="emit('update:modelValue', false)" />
      </q-card-section>

      <q-card-section>
        <div v-if="!localRows.length" class="text-caption text-grey-7">
          {{ t('customers.noCustomFields') }}
        </div>
        <div v-for="field in localRows" :key="field.field_definition_id" class="q-mb-sm">
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
            :options="(field.options || []).map(opt => ({ label: customFieldOption(opt), value: opt }))"
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
  customerId: { type: Number, default: null },
  rows: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const { t } = useI18n()
const customFieldsStore = useCustomFieldsStore()

const localRows = ref([])
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
  const defs = (customFieldsStore.definitions || []).filter(def => def.entity_type === 'customer' && def.is_active !== false)
  return defs.map(def => ({
    field_definition_id: def.id,
    label: def.label,
    value_type: def.value_type,
    options: def.options || [],
    value: null,
  }))
}

async function loadFieldRows() {
  if (!props.customerId) {
    localRows.value = props.rows.length ? props.rows.map(r => ({ ...r })) : createEmptyFieldRows()
    return
  }
  try {
    const data = await customFieldsStore.fetchEntityValues('customer', props.customerId)
    localRows.value = Array.isArray(data?.values) ? data.values.map(v => ({ ...v })) : createEmptyFieldRows()
  } catch {
    localRows.value = createEmptyFieldRows()
  }
}

async function saveValues() {
  if (!props.customerId) {
    emit('update:modelValue', false)
    return
  }
  saving.value = true
  try {
    await customFieldsStore.saveEntityValues('customer', props.customerId, localRows.value.map(row => ({
      field_definition_id: row.field_definition_id,
      value: row.value,
    })))
    emit('saved', localRows.value.map(r => ({ ...r })))
    emit('update:modelValue', false)
  } finally {
    saving.value = false
  }
}

watch(() => props.modelValue, async (open) => {
  if (open) {
    if (!customFieldsStore.definitions.length) {
      await customFieldsStore.fetchDefinitions('customer')
    }
    await loadFieldRows()
  }
})
</script>
