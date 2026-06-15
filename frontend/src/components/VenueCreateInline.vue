<template>
  <q-expansion-item icon="place" :label="t('jobs.createNewVenue')" dense>
    <div class="q-pt-sm">
      <q-input v-model="draft.name" :label="t('jobs.venueName')" outlined dense class="q-mb-sm" />
      <div class="row q-col-gutter-sm">
        <div class="col-12 col-md-6">
          <q-input v-model="draft.address" :label="t('venues.address')" outlined dense class="q-mb-sm" />
        </div>
        <div class="col-12 col-md-6">
          <q-input v-model="draft.city" :label="t('venues.city')" outlined dense class="q-mb-sm" />
        </div>
      </div>
      <q-input v-model="draft.notes" :label="t('jobs.venueNotes')" type="textarea" autogrow outlined dense />

      <q-separator class="q-my-sm" />
      <div class="text-subtitle2 q-mb-xs">{{ t('jobs.venueCustomFields') }}</div>
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
      <div v-else class="text-caption text-grey-7">{{ t('jobs.noVenueCustomFields') }}</div>

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
import { useVenuesStore } from '../stores/venues'
import { useCustomFieldsStore } from '../stores/customFields'
import { translateMaybePrefillCustomFieldLabel, translateMaybePrefillCustomFieldOption } from '../i18n/prefillContent'

const emit = defineEmits(['created'])

const $q = useQuasar()
const { t } = useI18n()
const venuesStore = useVenuesStore()
const customFieldsStore = useCustomFieldsStore()

const saving = ref(false)
const draft = ref(emptyDraft())

function emptyDraft() {
  return { name: '', address: '', city: '', notes: '' }
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
  const defs = (customFieldsStore.definitions || []).filter(def => def.entity_type === 'venue' && def.is_active !== false)
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
    await customFieldsStore.fetchDefinitions('venue')
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
    const { data } = await api.post('/api/v1/venues', {
      name,
      address: draft.value.address?.trim() || null,
      city: draft.value.city?.trim() || null,
      notes: draft.value.notes?.trim() || null,
    })
    if (fieldRows.value.length) {
      await customFieldsStore.saveEntityValues('venue', data.id, fieldRows.value.map(row => ({
        field_definition_id: row.field_definition_id,
        value: row.value,
      })))
    }
    await venuesStore.fetchAll()
    $q.notify({ type: 'positive', message: t('venues.createdNotice') })
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
