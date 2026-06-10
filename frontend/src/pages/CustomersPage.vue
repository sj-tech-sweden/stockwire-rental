<template>
  <q-page class="q-pa-md ec-page">
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">{{ t('customers.title') }}</div>
      <q-btn v-if="authStore.canEdit" color="primary" icon="person_add" :label="t('customers.newCustomer')" unelevated @click="openCreate" />
    </div>

    <q-table
      :rows="filteredCustomers"
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
        <q-input v-model="search" dense outlined clearable :placeholder="t('customers.search')">
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
              <div class="text-caption text-grey-7">{{ props.row.email || t('customers.noEmail') }}</div>
            </q-card-section>
            <q-card-section class="q-pt-none q-pb-sm">
              <div class="text-caption">{{ t('customers.phone') }}: {{ props.row.phone || '-' }}</div>
              <div class="text-caption" v-if="props.row.address || props.row.city">{{ [props.row.address, props.row.city, props.row.postal_code].filter(Boolean).join(', ') }}</div>
              <div class="text-caption" v-if="props.row.country">{{ props.row.country }}</div>
              <div class="text-caption">{{ t('customers.created') }}: {{ props.row.created_at ? new Date(props.row.created_at).toLocaleDateString() : '—' }}</div>
              <div class="text-caption">{{ props.row.notes || t('customers.noNotes') }}</div>
            </q-card-section>
            <q-card-actions v-if="authStore.canEdit" align="right">
              <q-btn flat dense icon="edit" color="primary" @click="openEdit(props.row)" />
              <q-btn flat dense icon="delete" color="negative" @click="confirmDelete(props.row)" />
            </q-card-actions>
          </q-card>
        </div>
      </template>
    </q-table>

    <CustomerDialog
      v-model="dialogOpen"
      :customer="editing"
      @saved="onCustomerSaved"
    />
    <CustomerDeleteDialog
      v-model="deleteDialogOpen"
      :customer="deleteTarget"
      @deleted="onCustomerDeleted"
    />
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import { useCustomersStore } from '../stores/customers'
import { useCustomFieldsStore } from '../stores/customFields'
import { useAuthStore } from '../stores/auth'
import { useCompactGrid } from '../composables/useCompactGrid'
import CustomerDialog from '../components/CustomerDialog.vue'
import CustomerDeleteDialog from '../components/CustomerDeleteDialog.vue'

const $q = useQuasar()
const compactGrid = useCompactGrid(1024)
const route = useRoute()
const router = useRouter()
const store = useCustomersStore()
const customFieldsStore = useCustomFieldsStore()
const authStore = useAuthStore()
const { t } = useI18n()

const search = ref('')

const columns = [
  { name: 'name', label: t('customers.name'), field: 'name', sortable: true, align: 'left' },
  { name: 'email', label: t('profile.email'), field: 'email', sortable: true, align: 'left' },
  { name: 'phone', label: t('customers.phone'), field: 'phone', sortable: true, align: 'left' },
  { name: 'city', label: t('customers.city'), field: 'city', sortable: true, align: 'left' },
  { name: 'notes', label: t('customers.notes'), field: 'notes', sortable: false, align: 'left' },
  {
    name: 'created_at',
    label: t('customers.created'),
    field: 'created_at',
    sortable: true,
    align: 'left',
    format: v => (v ? new Date(v).toLocaleDateString() : '—'),
  },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
]

const filteredCustomers = computed(() => {
  const term = search.value.trim().toLowerCase()
  if (!term) return store.customers
  return store.customers.filter((customer) =>
    [customer.name, customer.email, customer.phone, customer.address, customer.city, customer.postal_code, customer.country, customer.notes]
      .filter(Boolean)
      .some(value => String(value).toLowerCase().includes(term))
  )
})

async function focusCustomerFromQuery() {
  const focusId = Number(route.query.focusCustomerId || 0)
  if (!focusId) return
  const customer = store.customers.find(item => item.id === focusId)
  if (customer) {
    openEdit(customer)
  }

  const nextQuery = { ...route.query }
  delete nextQuery.focusCustomerId
  await router.replace({ path: '/customers', query: nextQuery })
}

onMounted(async () => {
  await Promise.all([
    store.fetchAll(),
    customFieldsStore.fetchDefinitions('customer'),
  ])
  await focusCustomerFromQuery()
})

const dialogOpen = ref(false)
const editing = ref(null)
const deleteDialogOpen = ref(false)
const deleteTarget = ref(null)

function openCreate() {
  editing.value = null
  dialogOpen.value = true
}

function openEdit(customer) {
  editing.value = customer
  dialogOpen.value = true
}

function confirmDelete(customer) {
  deleteTarget.value = customer
  deleteDialogOpen.value = true
}

function onCustomerSaved() {
  dialogOpen.value = false
  editing.value = null
}

function onCustomerDeleted() {
  deleteDialogOpen.value = false
  deleteTarget.value = null
}
</script>
