<template>
  <q-page class="q-pa-md ec-page">
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">{{ t('customers.title') }}</div>
      <q-btn v-if="authStore.canEdit" color="primary" icon="person_add" :label="t('customers.newCustomer')" unelevated @click="openCreate" />
    </div>

    <q-tabs v-model="filterType" inline-label align="left" class="q-mb-md">
      <q-tab name="all" :label="t('common.all')" />
      <q-tab name="customer" :label="t('customers.isCustomer')" />
      <q-tab name="product_supplier" :label="t('customers.isProductSupplier')" />
      <q-tab name="rental_supplier" :label="t('customers.isRentalSupplier')" />
      <q-tab name="crew_supplier" :label="t('customers.isCrewSupplier')" />
    </q-tabs>

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
      @row-dblclick="(evt, row) => openDetail(row)"
    >
      <template #top-right>
        <q-input v-model="search" dense outlined clearable :placeholder="t('customers.search')">
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

      <template #body-cell-supplier_types="props">
        <q-td :props="props" auto-width>
          <q-badge v-if="props.row.is_product_supplier" color="blue" :label="t('customers.isProductSupplier')" class="q-mr-xs" />
          <q-badge v-if="props.row.is_rental_supplier" color="orange" :label="t('customers.isRentalSupplier')" class="q-mr-xs" />
          <q-badge v-if="props.row.is_crew_supplier" color="green" :label="t('customers.isCrewSupplier')" />
        </q-td>
      </template>

      <template #item="props">
        <div class="q-pa-xs col-12">
          <q-card flat bordered @dblclick="openDetail(props.row)">
            <q-card-section class="q-pb-sm">
              <div class="text-subtitle2">{{ props.row.name }}</div>
              <div class="text-caption text-grey-7">{{ props.row.email || t('customers.noEmail') }}</div>
              <div class="q-mt-xs">
                <q-badge v-if="props.row.is_product_supplier" color="blue" :label="t('customers.isProductSupplier')" class="q-mr-xs" />
                <q-badge v-if="props.row.is_rental_supplier" color="orange" :label="t('customers.isRentalSupplier')" class="q-mr-xs" />
                <q-badge v-if="props.row.is_crew_supplier" color="green" :label="t('customers.isCrewSupplier')" />
              </div>
            </q-card-section>
            <q-card-section class="q-pt-none q-pb-sm">
              <div class="text-caption">{{ t('customers.phone') }}: {{ props.row.phone || '-' }}</div>
              <div class="text-caption" v-if="props.row.address || props.row.city">{{ [props.row.address, props.row.city, props.row.postal_code].filter(Boolean).join(', ') }}</div>
              <div class="text-caption" v-if="props.row.country">{{ props.row.country }}</div>
              <div class="text-caption">{{ t('customers.created') }}: {{ props.row.created_at ? new Date(props.row.created_at).toLocaleDateString() : '—' }}</div>
              <div class="text-caption">{{ props.row.notes || t('customers.noNotes') }}</div>
            </q-card-section>
            <q-card-actions align="right">
              <q-btn flat dense :icon="authStore.canEdit ? 'edit' : 'info'" color="primary" @click="openDetail(props.row)" />
              <q-btn v-if="authStore.canEdit" flat dense icon="delete" color="negative" class="q-ml-xs" @click="confirmDelete(props.row)" />
            </q-card-actions>
          </q-card>
        </div>
      </template>
    </q-table>

    <CustomerDeleteDialog
      v-model="deleteDialogOpen"
      :customer="deleteTarget"
      @deleted="onCustomerDeleted"
    />
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import { useCustomersStore } from '../stores/customers'
import { useCustomFieldsStore } from '../stores/customFields'
import { useAuthStore } from '../stores/auth'
import { useCompactGrid } from '../composables/useCompactGrid'
import CustomerDeleteDialog from '../components/CustomerDeleteDialog.vue'

const compactGrid = useCompactGrid(1024)
const route = useRoute()
const router = useRouter()
const store = useCustomersStore()
const customFieldsStore = useCustomFieldsStore()
const authStore = useAuthStore()
const { t } = useI18n()

const search = ref('')
const filterType = ref(route.query.tab || 'all')

const columns = [
  { name: 'name', label: t('customers.name'), field: 'name', sortable: true, align: 'left' },
  { name: 'email', label: t('profile.email'), field: 'email', sortable: true, align: 'left' },
  { name: 'phone', label: t('customers.phone'), field: 'phone', sortable: true, align: 'left' },
  { name: 'city', label: t('customers.city'), field: 'city', sortable: true, align: 'left' },
  { name: 'supplier_types', label: t('customers.supplierTypes'), field: 'supplier_types', align: 'left' },
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
  let list = store.customers

  if (filterType.value === 'customer') {
    list = list.filter(c => c.is_customer)
  } else if (filterType.value === 'product_supplier') {
    list = list.filter(c => c.is_product_supplier)
  } else if (filterType.value === 'rental_supplier') {
    list = list.filter(c => c.is_rental_supplier)
  } else if (filterType.value === 'crew_supplier') {
    list = list.filter(c => c.is_crew_supplier)
  }

  const term = search.value.trim().toLowerCase()
  if (!term) return list
  return list.filter((customer) =>
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
    openDetail(customer)
  }

  const nextQuery = { ...route.query }
  delete nextQuery.focusCustomerId
  await router.replace({ path: '/companies', query: nextQuery })
}

onMounted(async () => {
  await Promise.all([
    store.fetchAll(),
    customFieldsStore.fetchDefinitions('customer'),
  ])
  await focusCustomerFromQuery()
})

const deleteDialogOpen = ref(false)
const deleteTarget = ref(null)

function openCreate() {
  router.push('/companies/new')
}

function openDetail(customer) {
  router.push(`/companies/${customer.id}`)
}

function confirmDelete(customer) {
  deleteTarget.value = customer
  deleteDialogOpen.value = true
}

function onCustomerDeleted() {
  deleteDialogOpen.value = false
  deleteTarget.value = null
}
</script>
