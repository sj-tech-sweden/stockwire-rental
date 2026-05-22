<template>
  <q-page class="q-pa-md ec-page">
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">{{ t('venues.title') }}</div>
      <q-btn v-if="authStore.canEdit" color="primary" icon="add_location" :label="t('venues.newVenue')" unelevated @click="openCreate" />
    </div>

    <q-table
      :rows="filteredVenues"
      :columns="columns"
      row-key="id"
      :grid="compactGrid"
      :hide-header="compactGrid"
      flat
      bordered
      :loading="store.loading"
      :filter="search"
      :pagination="{ rowsPerPage: 50 }"
      :rows-per-page-options="[25, 50, 100, 0]"
      class="ec-card"
    >
      <template #top-right>
        <q-input v-model="search" dense outlined clearable :placeholder="t('venues.search')">
          <template #prepend>
            <q-icon name="search" />
          </template>
        </q-input>
      </template>

      <template #body-cell-actions="props">
        <q-td v-if="authStore.canEdit" :props="props" auto-width>
          <q-btn flat round dense icon="edit" color="primary" class="q-mr-xs" @click="openEdit(props.row)" />
          <q-btn flat round dense icon="delete" color="negative" @click="confirmDelete(props.row)" />
        </q-td>
      </template>

      <template #item="props">
        <div class="q-pa-xs col-12">
          <q-card flat bordered>
            <q-card-section class="q-pb-sm">
              <div class="text-subtitle2">{{ props.row.name }}</div>
              <div class="text-caption text-grey-7">{{ props.row.city || t('venues.noCity') }}</div>
            </q-card-section>
            <q-card-section class="q-pt-none q-pb-sm">
              <div class="text-caption">{{ t('venues.address') }}: {{ props.row.address || '-' }}</div>
              <div class="text-caption">{{ t('venues.created') }}: {{ props.row.created_at ? new Date(props.row.created_at).toLocaleDateString() : '—' }}</div>
              <div class="text-caption">{{ props.row.notes || t('venues.noNotes') }}</div>
            </q-card-section>
            <q-card-actions v-if="authStore.canEdit" align="right">
              <q-btn flat dense icon="edit" color="primary" @click="openEdit(props.row)" />
              <q-btn flat dense icon="delete" color="negative" @click="confirmDelete(props.row)" />
            </q-card-actions>
          </q-card>
        </div>
      </template>
    </q-table>

    <q-dialog v-model="dialogOpen" persistent :maximized="isPhone">
      <q-card :style="isPhone ? 'width: 100vw; max-width: 100vw; height: 100vh' : 'min-width: 680px; max-width: 95vw'" class="ec-card">
        <q-card-section>
          <div class="text-h6">{{ editing ? t('venues.editVenue') : t('venues.newVenue') }}</div>
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
          <q-btn v-if="authStore.canEdit" color="primary" unelevated :class="isPhone ? 'full-width' : ''" :label="editing ? t('app.actions.save') : t('venues.create')" :loading="saving" @click="saveVenue" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="deleteDialogOpen" persistent>
      <q-card class="ec-card">
        <q-card-section class="row items-center">
          <q-icon name="warning" color="negative" size="md" class="q-mr-md" />
          <span>{{ t('venues.deletePrompt', { name: deleteTarget?.name || '' }) }}</span>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="deleteDialogOpen = false" />
          <q-btn v-if="authStore.canEdit" color="negative" unelevated :label="t('venues.delete')" :loading="saving" @click="doDelete" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import { useVenuesStore } from '../stores/venues'
import { useCustomFieldsStore } from '../stores/customFields'
import { useAuthStore } from '../stores/auth'
import { useCompactGrid } from '../composables/useCompactGrid'
import { translateMaybePrefillCustomFieldLabel, translateMaybePrefillCustomFieldOption } from '../i18n/prefillContent'

const $q = useQuasar()
const isPhone = computed(() => $q.screen.lt.md)
const compactGrid = useCompactGrid(1024)
const route = useRoute()
const router = useRouter()
const store = useVenuesStore()
const customFieldsStore = useCustomFieldsStore()
const authStore = useAuthStore()
const { t } = useI18n()

const search = ref('')
const venueFieldRows = ref([])
const venueGeneralExpanded = ref(true)
const venueCustomFieldsExpanded = ref(false)

const booleanValueOptions = [
  { label: t('common.true'), value: 'true' },
  { label: t('common.false'), value: 'false' },
]

const columns = [
  { name: 'name', label: t('venues.name'), field: 'name', sortable: true, align: 'left' },
  { name: 'address', label: t('venues.address'), field: 'address', sortable: true, align: 'left' },
  { name: 'city', label: t('venues.city'), field: 'city', sortable: true, align: 'left' },
  { name: 'notes', label: t('venues.notes'), field: 'notes', sortable: false, align: 'left' },
  {
    name: 'created_at',
    label: t('venues.created'),
    field: 'created_at',
    sortable: true,
    align: 'left',
    format: v => (v ? new Date(v).toLocaleDateString() : '—'),
  },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
]

const filteredVenues = computed(() => {
  const term = search.value.trim().toLowerCase()
  if (!term) return store.venues
  return store.venues.filter((venue) =>
    [venue.name, venue.address, venue.city, venue.notes]
      .filter(Boolean)
      .some(value => String(value).toLowerCase().includes(term))
  )
})

function customFieldLabel(label) {
  return translateMaybePrefillCustomFieldLabel(label, t)
}

function customFieldOption(option) {
  return translateMaybePrefillCustomFieldOption(option, t)
}

async function focusVenueFromQuery() {
  const focusId = Number(route.query.focusVenueId || 0)
  if (!focusId) return
  const venue = store.venues.find(item => item.id === focusId)
  if (venue) {
    openEdit(venue)
  }

  const nextQuery = { ...route.query }
  delete nextQuery.focusVenueId
  await router.replace({ path: '/venues', query: nextQuery })
}

onMounted(async () => {
  await Promise.all([
    store.fetchAll(),
    customFieldsStore.fetchDefinitions('venue'),
  ])
  await focusVenueFromQuery()
})

const dialogOpen = ref(false)
const editing = ref(null)
const saving = ref(false)
const dialogError = ref('')
const formRef = ref(null)

const emptyForm = () => ({
  name: '',
  address: '',
  city: '',
  notes: '',
})

const form = ref(emptyForm())

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

async function openCreate() {
  editing.value = null
  form.value = emptyForm()
  await loadVenueFieldRows(null)
  venueGeneralExpanded.value = true
  venueCustomFieldsExpanded.value = !isPhone.value
  dialogError.value = ''
  dialogOpen.value = true
}

async function openEdit(venue) {
  editing.value = venue
  form.value = {
    name: venue.name ?? '',
    address: venue.address ?? '',
    city: venue.city ?? '',
    notes: venue.notes ?? '',
  }
  await loadVenueFieldRows(venue.id)
  venueGeneralExpanded.value = true
  venueCustomFieldsExpanded.value = !isPhone.value
  dialogError.value = ''
  dialogOpen.value = true
}

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
      notes: form.value.notes?.trim() || null,
    }

    let savedVenue
    if (editing.value) {
      savedVenue = await store.updateVenue(editing.value.id, payload)
    } else {
      savedVenue = await store.createVenue(payload)
    }

    await customFieldsStore.saveEntityValues('venue', savedVenue.id, venueFieldRows.value.map(row => ({
      field_definition_id: row.field_definition_id,
      value: row.value,
    })))

    dialogOpen.value = false
    $q.notify({ type: 'positive', message: editing.value ? t('venues.updated') : t('venues.createdNotice') })
  } catch (error) {
    dialogError.value = error?.response?.data?.detail || t('common.errorOccurred')
  } finally {
    saving.value = false
  }
}

const deleteDialogOpen = ref(false)
const deleteTarget = ref(null)

function confirmDelete(venue) {
  deleteTarget.value = venue
  deleteDialogOpen.value = true
}

async function doDelete() {
  if (!deleteTarget.value) return
  saving.value = true
  try {
    await store.deleteVenue(deleteTarget.value.id)
    deleteDialogOpen.value = false
    $q.notify({ type: 'positive', message: t('venues.deleted') })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('common.deleteFailed') })
  } finally {
    saving.value = false
  }
}
</script>
