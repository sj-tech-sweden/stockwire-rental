<template>
  <q-dialog v-model="dialogOpen" persistent :maximized="isPhone">
    <q-card :style="isPhone ? 'width: 100vw; max-width: 100vw; height: 100vh' : 'min-width: 680px; max-width: 95vw'" class="ec-card">
      <q-card-section>
        <div class="text-h6">{{ venue ? t('venues.editVenue') : t('venues.newVenue') }}</div>
      </q-card-section>

      <q-card-section class="q-pt-none" :style="isPhone ? 'max-height: calc(100vh - 140px); overflow: auto;' : ''">
        <q-form ref="formRef" @submit.prevent="saveVenue">
          <q-expansion-item v-model="venueGeneralExpanded" icon="apartment" :label="t('venues.general')" dense header-class="rounded-borders">
            <div class="q-pt-sm">
              <q-input
                v-model="form.name"
                :label="t('venues.name')"
                outlined
                dense
                class="q-mb-sm"
                :rules="[v => !!v || t('login.required')]"
              />
              <q-input v-model="form.address" :label="t('venues.address')" outlined dense class="q-mb-sm" />
              <q-input v-model="form.city" :label="t('venues.city')" outlined dense class="q-mb-sm" />
              <q-input v-model="form.phone" :label="t('venues.phone')" outlined dense class="q-mb-sm" />
              <q-input v-model="form.email" :label="t('venues.email')" type="email" outlined dense class="q-mb-sm" />
              <q-input v-model="form.contact_person" :label="t('venues.contactPerson')" outlined dense class="q-mb-sm" />
              <q-select v-model="form.country" :options="COUNTRIES" :label="t('venues.country')" outlined dense clearable emit-value map-options class="q-mb-sm" />
              <div v-if="venueFormMapEmbedUrl" class="q-mb-sm">
                <q-responsive :ratio="16 / 9" class="rounded-borders" style="overflow: hidden; border: 1px solid #d6dbe2;">
                  <iframe
                    :src="venueFormMapEmbedUrl"
                    :title="t('venues.mapPreview')"
                    loading="lazy"
                    referrerpolicy="no-referrer-when-downgrade"
                    style="border: 0; width: 100%; height: 100%;"
                  />
                </q-responsive>
                <q-btn
                  flat
                  dense
                  no-caps
                  color="primary"
                  icon="open_in_new"
                  class="q-mt-xs"
                  :label="t('venues.openMap')"
                  :href="venueFormMapLink"
                  target="_blank"
                  rel="noopener noreferrer"
                />
              </div>
              <q-input v-model="form.notes" :label="t('venues.notes')" type="textarea" autogrow outlined dense />
            </div>
          </q-expansion-item>

          <q-expansion-item v-model="venueCustomFieldsExpanded" icon="tune" :label="t('venues.customFields')" dense header-class="rounded-borders" class="q-mt-sm">
            <div class="q-pt-sm">
              <div v-if="venueFieldRows.length">
                <div v-for="field in venueFieldRows" :key="field.field_definition_id" class="q-mb-sm">
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
              <div v-else class="text-caption text-grey-7">{{ t('venues.noCustomFields') }}</div>
            </div>
          </q-expansion-item>

          <q-banner v-if="dialogError" class="bg-negative text-white q-mt-sm rounded-borders" dense>
            {{ dialogError }}
          </q-banner>
        </q-form>
      </q-card-section>

      <q-card-actions :align="isPhone ? 'stretch' : 'right'" :class="isPhone ? 'q-pa-md bg-grey-2' : ''">
        <q-btn flat :class="isPhone ? 'full-width q-mb-sm' : ''" :label="t('app.actions.cancel')" @click="dialogOpen = false" />
        <q-btn v-if="authStore.canEdit" color="primary" unelevated :class="isPhone ? 'full-width' : ''" :label="venue ? t('app.actions.save') : t('venues.create')" :loading="saving" @click="saveVenue" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'

import { useVenuesStore } from '../stores/venues'
import { useCustomFieldsStore } from '../stores/customFields'
import { useAuthStore } from '../stores/auth'
import { useSettingsStore } from '../stores/settings'
import { COUNTRIES } from '../constants/countries'
import { translateMaybePrefillCustomFieldLabel, translateMaybePrefillCustomFieldOption } from '../i18n/prefillContent'
import { googleMapsEmbedUrl, googleMapsSearchUrl, locationQueryFromParts } from '../utils/maps'

const props = defineProps({
  modelValue: Boolean,
  venue: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const $q = useQuasar()
const { t } = useI18n()
const store = useVenuesStore()
const customFieldsStore = useCustomFieldsStore()
const authStore = useAuthStore()

const isPhone = computed(() => $q.screen.lt.md)

const dialogOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const formRef = ref(null)
const form = ref(emptyForm())
const saving = ref(false)
const dialogError = ref('')
const venueFieldRows = ref([])
const venueGeneralExpanded = ref(true)
const venueCustomFieldsExpanded = ref(false)

const booleanValueOptions = computed(() => [
  { label: t('common.true'), value: 'true' },
  { label: t('common.false'), value: 'false' },
])

const venueFormLocationQuery = computed(() => locationQueryFromParts(form.value))
const venueFormMapLink = computed(() => googleMapsSearchUrl(venueFormLocationQuery.value))
const venueFormMapEmbedUrl = computed(() => googleMapsEmbedUrl(venueFormLocationQuery.value))

function emptyForm() {
  return {
    name: '',
    address: '',
    city: '',
    phone: '',
    email: '',
    contact_person: '',
    country: '',
    notes: '',
  }
}

function customFieldLabel(label) {
  return translateMaybePrefillCustomFieldLabel(label, t)
}

function customFieldOption(option) {
  return translateMaybePrefillCustomFieldOption(option, t)
}

function createEmptyVenueFieldRows() {
  const defs = (customFieldsStore.definitions || []).filter(def => def.entity_type === 'venue' && def.is_active !== false)
  return defs.map(def => ({
    field_definition_id: def.id,
    label: def.label,
    value_type: def.value_type,
    options: def.options || [],
    value: null,
  }))
}

async function loadVenueFieldRows(entityId) {
  if (!entityId) {
    venueFieldRows.value = createEmptyVenueFieldRows()
    return
  }
  try {
    const data = await customFieldsStore.fetchEntityValues('venue', entityId)
    venueFieldRows.value = Array.isArray(data?.values) ? data.values.map(value => ({ ...value })) : createEmptyVenueFieldRows()
  } catch {
    venueFieldRows.value = createEmptyVenueFieldRows()
  }
}

watch(() => props.modelValue, async (open) => {
  if (!open) return
  if (props.venue) {
    form.value = {
      name: props.venue.name ?? '',
      address: props.venue.address ?? '',
      city: props.venue.city ?? '',
      phone: props.venue.phone ?? '',
      email: props.venue.email ?? '',
      contact_person: props.venue.contact_person ?? '',
      country: props.venue.country ?? '',
      notes: props.venue.notes ?? '',
    }
    await loadVenueFieldRows(props.venue.id)
  } else {
    form.value = emptyForm()
    const settingsStore = useSettingsStore()
    if (settingsStore.companyProfile?.default_country) {
      form.value.country = settingsStore.companyProfile.default_country
    }
    await loadVenueFieldRows(null)
  }
  venueGeneralExpanded.value = true
  venueCustomFieldsExpanded.value = !isPhone.value
  dialogError.value = ''
})

async function saveVenue() {
  const valid = await formRef.value?.validate()
  if (!valid) return

  saving.value = true
  dialogError.value = ''
  try {
    const payload = {
      ...form.value,
      name: form.value.name.trim(),
      address: form.value.address?.trim() || null,
      city: form.value.city?.trim() || null,
      phone: form.value.phone?.trim() || null,
      email: form.value.email?.trim() || null,
      contact_person: form.value.contact_person?.trim() || null,
      country: form.value.country?.trim() || null,
      notes: form.value.notes?.trim() || null,
    }

    let savedVenue
    if (props.venue) {
      savedVenue = await store.updateVenue(props.venue.id, payload)
    } else {
      savedVenue = await store.createVenue(payload)
    }

    await customFieldsStore.saveEntityValues('venue', savedVenue.id, venueFieldRows.value.map(row => ({
      field_definition_id: row.field_definition_id,
      value: row.value,
    })))

    dialogOpen.value = false
    $q.notify({ type: 'positive', message: props.venue ? t('venues.updated') : t('venues.createdNotice') })
    emit('saved', savedVenue)
  } catch (error) {
    dialogError.value = error?.response?.data?.detail || t('common.errorOccurred')
  } finally {
    saving.value = false
  }
}
</script>
