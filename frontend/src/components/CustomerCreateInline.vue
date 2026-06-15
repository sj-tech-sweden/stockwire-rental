<template>
  <q-expansion-item icon="person_add" :label="t('jobs.createNewCustomer')" dense>
    <div class="q-pt-sm">
      <q-input v-model="draft.name" :label="t('jobs.customerName')" outlined dense class="q-mb-sm" />
      <div class="row q-col-gutter-sm">
        <div class="col-12 col-md-6">
          <q-input v-model="draft.email" :label="t('profile.email')" outlined dense class="q-mb-sm" />
        </div>
        <div class="col-12 col-md-6">
          <q-input v-model="draft.phone" :label="t('customers.phone')" outlined dense class="q-mb-sm" />
        </div>
      </div>
      <q-input v-model="draft.notes" :label="t('jobs.customerNotes')" type="textarea" autogrow outlined dense />

      <q-separator class="q-my-sm" />
      <div class="text-subtitle2 q-mb-xs">{{ t('jobs.customerCustomFields') }}</div>
      <div v-if="fieldRows.length">
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
            v-model="field.value"
            :label="customFieldLabel(field.label)"
            type="number"
            outlined
            dense
          />
          <q-select
            v-else-if="field.value_type === 'boolean'"
            v-model="field.value"
            :options="booleanValueOptions"
            :label="customFieldLabel(field.label)"
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
            :options="(field.options || []).map(option => ({ label: customFieldOption(option), value: option }))"
            :label="customFieldLabel(field.label)"
            outlined
            dense
            clearable
            emit-value
            map-options
          />
        </div>
      </div>
      <div v-else class="text-caption text-grey-7">{{ t('jobs.noCustomerCustomFields') }}</div>

      <q-btn
        color="primary"
        :label="t('app.actions.save')"
        unelevated
        :loading="saving"
        @click="save"
        class="q-mt-sm"
      />
    </div>
  </q-expansion-item>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'

import { api } from '../boot/axios'
import { useCustomersStore } from '../stores/customers'
import { useCustomFieldsStore } from '../stores/customFields'
import { translateMaybePrefillCustomFieldLabel, translateMaybePrefillCustomFieldOption } from '../i18n/prefillContent'

const emit = defineEmits(['created'])

const $q = useQuasar()
const { t } = useI18n()
const customersStore = useCustomersStore()
const customFieldsStore = useCustomFieldsStore()

const saving = ref(false)
const draft = ref(emptyDraft())

function emptyDraft() {
  return { name: '', email: '', phone: '', notes: '' }
}

const booleanValueOptions = computed(() => [
  { label: t('common.true'), value: 'true' },
  { label: t('common.false'), value: 'false' },
])

const fieldRows = ref([])

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
  if (!customFieldsStore.definitions.length) {
    await customFieldsStore.fetchDefinitions('customer')
  }
  fieldRows.value = createEmptyFieldRows()
}

async function save() {
  const name = draft.value.name?.trim()
  if (!name) {
    $q.notify({ type: 'warning', message: t('login.required') })
    return
  }
  saving.value = true
  try {
    const { data } = await api.post('/api/v1/customers', {
      name,
      email: draft.value.email?.trim() || null,
      phone: draft.value.phone?.trim() || null,
      notes: draft.value.notes?.trim() || null,
    })
    if (fieldRows.value.length) {
      await customFieldsStore.saveEntityValues('customer', data.id, fieldRows.value.map(row => ({
        field_definition_id: row.field_definition_id,
        value: row.value,
      })))
    }
    await customersStore.fetchAll()
    $q.notify({ type: 'positive', message: t('customers.createdNotice') })
    draft.value = emptyDraft()
    fieldRows.value = createEmptyFieldRows()
    emit('created', data)
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('common.errorOccurred') })
  } finally {
    saving.value = false
  }
}

loadFieldRows()
</script>
