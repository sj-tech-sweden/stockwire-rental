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

      <template #body-cell-address="props">
        <q-td :props="props">
          <a
            v-if="venueMapLink(props.row)"
            :href="venueMapLink(props.row)"
            target="_blank"
            rel="noopener noreferrer"
            class="text-primary"
          >
            {{ props.value || '—' }}
          </a>
          <span v-else>{{ props.value || '—' }}</span>
        </q-td>
      </template>

      <template #body-cell-actions="props">
        <q-td v-if="authStore.canEdit" :props="props" auto-width>
          <q-btn
            v-if="venueMapLink(props.row)"
            flat
            round
            dense
            icon="open_in_new"
            color="secondary"
            class="q-mr-xs"
            :href="venueMapLink(props.row)"
            target="_blank"
            rel="noopener noreferrer"
            :aria-label="t('venues.openMap')"
          />
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
              <div class="text-caption">
                {{ t('venues.address') }}:
                <a
                  v-if="venueMapLink(props.row)"
                  :href="venueMapLink(props.row)"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-primary"
                >
                  {{ props.row.address || '-' }}
                </a>
                <span v-else>{{ props.row.address || '-' }}</span>
              </div>
              <div class="text-caption" v-if="props.row.phone">{{ t('venues.phone') }}: {{ props.row.phone }}</div>
              <div class="text-caption" v-if="props.row.email">{{ t('venues.email') }}: {{ props.row.email }}</div>
              <div class="text-caption" v-if="props.row.contact_person">{{ t('venues.contactPerson') }}: {{ props.row.contact_person }}</div>
              <div class="text-caption" v-if="props.row.country">{{ t('venues.country') }}: {{ props.row.country }}</div>
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

    <VenueDialog
      v-model="dialogOpen"
      :venue="editing"
      @saved="onVenueSaved"
    />
    <VenueDeleteDialog
      v-model="deleteDialogOpen"
      :venue="deleteTarget"
      @deleted="onVenueDeleted"
    />
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import { useVenuesStore } from '../stores/venues'
import { useAuthStore } from '../stores/auth'
import { useCompactGrid } from '../composables/useCompactGrid'
import { googleMapsSearchUrl, locationQueryFromParts } from '../utils/maps'
import VenueDialog from '../components/VenueDialog.vue'
import VenueDeleteDialog from '../components/VenueDeleteDialog.vue'

const $q = useQuasar()
const isPhone = computed(() => $q.screen.lt.md)
const compactGrid = useCompactGrid(1024)
const route = useRoute()
const router = useRouter()
const store = useVenuesStore()
const authStore = useAuthStore()
const { t } = useI18n()

const search = ref('')

const columns = [
  { name: 'name', label: t('venues.name'), field: 'name', sortable: true, align: 'left' },
  { name: 'address', label: t('venues.address'), field: 'address', sortable: true, align: 'left' },
  { name: 'city', label: t('venues.city'), field: 'city', sortable: true, align: 'left' },
  { name: 'phone', label: t('venues.phone'), field: 'phone', sortable: true, align: 'left' },
  { name: 'email', label: t('venues.email'), field: 'email', sortable: true, align: 'left' },
  { name: 'contact_person', label: t('venues.contactPerson'), field: 'contact_person', sortable: true, align: 'left' },
  { name: 'country', label: t('venues.country'), field: 'country', sortable: true, align: 'left' },
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
    [venue.name, venue.address, venue.city, venue.phone, venue.email, venue.contact_person, venue.country, venue.notes]
      .filter(Boolean)
      .some(value => String(value).toLowerCase().includes(term))
  )
})

function venueMapLink(venue) {
  return googleMapsSearchUrl(locationQueryFromParts(venue))
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
  await store.fetchAll()
  await focusVenueFromQuery()
})

const dialogOpen = ref(false)
const editing = ref(null)

const deleteDialogOpen = ref(false)
const deleteTarget = ref(null)

function confirmDelete(venue) {
  deleteTarget.value = venue
  deleteDialogOpen.value = true
}

function onVenueSaved() {
  dialogOpen.value = false
  editing.value = null
}

function onVenueDeleted() {
  deleteDialogOpen.value = false
  deleteTarget.value = null
}

async function openCreate() {
  editing.value = null
  dialogOpen.value = true
}

async function openEdit(venue) {
  editing.value = venue
  dialogOpen.value = true
}
</script>
