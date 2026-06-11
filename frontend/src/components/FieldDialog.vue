<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="emit('update:modelValue', $event)">
    <q-card style="width: 560px; max-width: 95vw" class="ec-card">
      <q-card-section>
        <div class="text-h6">{{ fieldEditing ? t('settings.customFields.editField') : t('settings.customFields.newField') }}</div>
      </q-card-section>
      <q-card-section class="q-pt-none">
        <q-select
          v-model="form.entity_type"
          :options="entityTypeOptions"
          :label="t('settings.customFields.entityType')"
          outlined
          dense
          emit-value
          map-options
          class="q-mb-sm"
        />
        <q-input v-model="form.label" :label="t('settings.customFields.label')" outlined dense class="q-mb-sm" />
        <q-input v-model="form.key" :label="t('settings.customFields.key')" outlined dense class="q-mb-sm" :hint="t('settings.customFields.keyHint')" />
        <q-select
          v-model="form.value_type"
          :options="valueTypeOptions"
          :label="t('settings.customFields.valueType')"
          outlined
          dense
          emit-value
          map-options
          class="q-mb-sm"
        />
        <q-input
          v-model="form.options_text"
          :label="t('settings.customFields.optionsCommaSeparated')"
          outlined
          dense
          class="q-mb-sm"
        />
        <q-toggle v-model="form.is_required" :label="t('settings.customFields.required')" class="q-mb-sm" />
        <q-toggle v-model="form.is_active" :label="t('settings.auth.active')" />
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="emit('update:modelValue', false)" />
        <q-btn color="primary" unelevated :loading="saving" :label="t('app.actions.save')" @click="save" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useCustomFieldsStore, CUSTOM_FIELD_ENTITY_TYPES, CUSTOM_FIELD_VALUE_TYPES } from 'src/stores/customFields'

const props = defineProps({
  modelValue: Boolean,
  field: { type: Object, default: null },
  entityType: { type: String, default: null },
})

const emit = defineEmits([
  'update:modelValue',
  'saved',
])

const $q = useQuasar()
const { t } = useI18n()
const customFieldsStore = useCustomFieldsStore()

const saving = ref(false)
const fieldEditing = ref(null)

const entityTypeOptions = computed(() => CUSTOM_FIELD_ENTITY_TYPES.map(option => ({
  ...option,
  label: t(`settings.customFields.entityType_${option.value}`),
})))

const valueTypeOptions = computed(() => CUSTOM_FIELD_VALUE_TYPES.map(option => ({
  ...option,
  label: t(`settings.customFields.valueType_${option.value}`),
})))

const emptyForm = () => ({
  entity_type: 'product',
  key: '',
  label: '',
  value_type: 'text',
  options_text: '',
  is_required: false,
  is_active: true,
})

const form = ref(emptyForm())

async function save() {
  saving.value = true
  try {
    const payload = {
      entity_type: form.value.entity_type,
      key: form.value.key,
      label: form.value.label,
      value_type: form.value.value_type,
      options: form.value.options_text.split(',').map(option => option.trim()).filter(Boolean),
      is_required: !!form.value.is_required,
      is_active: !!form.value.is_active,
    }

    if (fieldEditing.value) {
      await customFieldsStore.updateDefinition(fieldEditing.value.id, payload)
      $q.notify({ type: 'positive', message: t('settings.customFields.fieldUpdated') })
    } else {
      await customFieldsStore.createDefinition(payload)
      $q.notify({ type: 'positive', message: t('settings.customFields.fieldCreated') })
    }
    emit('update:modelValue', false)
    await customFieldsStore.fetchDefinitions()
    emit('saved')
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('settings.customFields.failedSaveField') })
  } finally {
    saving.value = false
  }
}

watch(() => props.modelValue, (open) => {
  if (open) {
    fieldEditing.value = props.field
    if (props.field) {
      form.value = {
        entity_type: props.field.entity_type,
        key: props.field.key,
        label: props.field.label,
        value_type: props.field.value_type,
        options_text: (props.field.options || []).join(', '),
        is_required: !!props.field.is_required,
        is_active: !!props.field.is_active,
      }
    } else {
      form.value = { ...emptyForm(), entity_type: props.entityType || 'product' }
    }
  }
})
</script>
