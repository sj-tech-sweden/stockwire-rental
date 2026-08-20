<template>
  <q-page class="q-pa-md ec-page">
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">{{ t('persons.title') }}</div>
      <q-btn v-if="authStore.canEdit" color="primary" icon="person_add" :label="t('persons.newPerson')" unelevated @click="openCreate" />
    </div>

    <q-table
      :rows="filteredPersons"
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
      @row-dblclick="(evt, row) => openDetail(row)"
    >
      <template #top-right>
        <q-input v-model="search" dense outlined clearable :placeholder="t('persons.search')">
          <template #prepend>
            <q-icon name="search" />
          </template>
        </q-input>
      </template>

      <template #body-cell-actions="props">
        <q-td :props="props" auto-width>
          <q-btn flat round dense :icon="authStore.canEdit ? 'edit' : 'info'" color="primary" @click="openDetail(props.row)" />
          <q-btn v-if="authStore.canEdit" flat round dense icon="delete" color="negative" class="q-ml-xs" @click="confirmDelete(props.row)" />
        </q-td>
      </template>

      <template #body-cell-name="props">
        <q-td :props="props">
          {{ props.row.first_name }} {{ props.row.last_name }}
        </q-td>
      </template>

      <template #body-cell-company="props">
        <q-td :props="props" auto-width>
          <q-badge v-if="props.row.company_name" color="blue" :label="props.row.company_name" />
          <span v-else class="text-caption text-grey-7">{{ t('persons.standalone') }}</span>
        </q-td>
      </template>

      <template #item="props">
        <div class="q-pa-xs col-12">
          <q-card flat bordered @dblclick="openDetail(props.row)">
            <q-card-section class="q-pb-sm">
              <div class="text-subtitle2">{{ props.row.first_name }} {{ props.row.last_name }}</div>
              <div class="text-caption text-grey-7">{{ props.row.email || t('persons.noEmail') }}</div>
              <div class="q-mt-xs">
                <q-badge v-if="props.row.company_name" color="blue" :label="props.row.company_name" />
                <span v-else class="text-caption text-grey-7">{{ t('persons.standalone') }}</span>
              </div>
            </q-card-section>
            <q-card-section class="q-pt-none q-pb-sm">
              <div class="text-caption">{{ t('persons.phone') }}: {{ props.row.phone || '-' }}</div>
              <div class="text-caption">{{ t('persons.created') }}: {{ props.row.created_at ? new Date(props.row.created_at).toLocaleDateString() : '—' }}</div>
            </q-card-section>
            <q-card-actions align="right">
              <q-btn flat dense :icon="authStore.canEdit ? 'edit' : 'info'" color="primary" @click="openDetail(props.row)" />
              <q-btn v-if="authStore.canEdit" flat dense icon="delete" color="negative" class="q-ml-xs" @click="confirmDelete(props.row)" />
            </q-card-actions>
          </q-card>
        </div>
      </template>
    </q-table>

    <PersonDeleteDialog
      v-model="deleteDialogOpen"
      :person="deleteTarget"
      @deleted="onPersonDeleted"
    />
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import { usePersonsStore } from '../stores/persons'
import { useAuthStore } from '../stores/auth'
import { useCompactGrid } from '../composables/useCompactGrid'
import PersonDeleteDialog from '../components/PersonDeleteDialog.vue'

const compactGrid = useCompactGrid(1024)
const router = useRouter()
const store = usePersonsStore()
const authStore = useAuthStore()
const { t } = useI18n()

const search = ref('')

const columns = [
  { name: 'name', label: t('persons.name'), field: row => `${row.first_name} ${row.last_name}`, sortable: true, align: 'left' },
  { name: 'email', label: t('profile.email'), field: 'email', sortable: true, align: 'left' },
  { name: 'phone', label: t('persons.phone'), field: 'phone', sortable: true, align: 'left' },
  { name: 'company', label: t('persons.company'), field: 'company_name', sortable: true, align: 'left' },
  {
    name: 'created_at',
    label: t('persons.created'),
    field: 'created_at',
    sortable: true,
    align: 'left',
    format: v => (v ? new Date(v).toLocaleDateString() : '—'),
  },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
]

const filteredPersons = computed(() => {
  let list = store.persons

  const term = search.value.trim().toLowerCase()
  if (!term) return list
  return list.filter((person) =>
    [person.first_name, person.last_name, person.email, person.phone, person.company_name]
      .filter(Boolean)
      .some(value => String(value).toLowerCase().includes(term))
  )
})

onMounted(async () => {
  await store.fetchAll()
})

function openCreate() {
  router.push('/persons/new')
}

function openDetail(person) {
  router.push(`/persons/${person.id}`)
}

const deleteDialogOpen = ref(false)
const deleteTarget = ref(null)

function confirmDelete(person) {
  deleteTarget.value = person
  deleteDialogOpen.value = true
}

function onPersonDeleted() {
  deleteDialogOpen.value = false
  deleteTarget.value = null
}
</script>
