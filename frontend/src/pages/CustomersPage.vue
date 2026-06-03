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

    <q-dialog v-model="dialogOpen" persistent>
      <q-card style="width: 520px; max-width: 95vw" class="ec-card">
        <q-card-section>
          <div class="text-h6">{{ editing ? t('customers.editCustomer') : t('customers.newCustomer') }}</div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-form ref="formRef" @submit.prevent="saveCustomer">
            <q-input
              v-model="form.name"
              :label="t('customers.name')"
              outlined
              dense
              class="q-mb-sm"
              :rules="[v => !!v || t('login.required')]"
            />
            <q-input v-model="form.email" :label="t('profile.email')" type="email" outlined dense class="q-mb-sm" />
            <q-input v-model="form.phone" :label="t('customers.phone')" outlined dense class="q-mb-sm" />
            <q-input v-model="form.notes" :label="t('customers.notes')" type="textarea" autogrow outlined dense />

            <q-separator class="q-my-md" />
            <div class="text-subtitle2 q-mb-sm">{{ t('customers.customFieldValues') }}</div>
            <div v-if="customerFieldRows.length">
              <div v-for="field in customerFieldRows" :key="field.field_definition_id" class="q-mb-sm">
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
            <div v-else class="text-caption text-grey-7">{{ t('customers.noCustomFields') }}</div>

            <q-banner v-if="dialogError" class="bg-negative text-white q-mt-sm rounded-borders" dense>
              {{ dialogError }}
            </q-banner>
          </q-form>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="dialogOpen = false" />
          <q-btn v-if="authStore.canEdit" color="primary" unelevated :label="editing ? t('app.actions.save') : t('customers.create')" :loading="saving" @click="saveCustomer" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="deleteDialogOpen" persistent>
      <q-card class="ec-card">
        <q-card-section class="row items-center">
          <q-icon name="warning" color="negative" size="md" class="q-mr-md" />
          <span>{{ t('customers.deletePrompt', { name: deleteTarget?.name || '' }) }}</span>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="deleteDialogOpen = false" />
          <q-btn v-if="authStore.canEdit" color="negative" unelevated :label="t('customers.delete')" :loading="saving" @click="doDelete" />
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

import { useCustomersStore } from '../stores/customers'
import { useCustomFieldsStore } from '../stores/customFields'
import { useAuthStore } from '../stores/auth'
import { useCompactGrid } from '../composables/useCompactGrid'
import { translateMaybePrefillCustomFieldLabel, translateMaybePrefillCustomFieldOption } from '../i18n/prefillContent'

const $q = useQuasar()
const compactGrid = useCompactGrid(1024)
const route = useRoute()
const router = useRouter()
const store = useCustomersStore()
const customFieldsStore = useCustomFieldsStore()
const authStore = useAuthStore()
const { t } = useI18n()

const search = ref('')
const customerFieldRows = ref([])

const booleanValueOptions = [
  { label: t('common.true'), value: 'true' },
  { label: t('common.false'), value: 'false' },
]

const columns = [
  { name: 'name', label: t('customers.name'), field: 'name', sortable: true, align: 'left' },
  { name: 'email', label: t('profile.email'), field: 'email', sortable: true, align: 'left' },
  { name: 'phone', label: t('customers.phone'), field: 'phone', sortable: true, align: 'left' },
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
    [customer.name, customer.email, customer.phone, customer.notes]
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
const saving = ref(false)
const dialogError = ref('')
const formRef = ref(null)

const emptyForm = () => ({
  name: '',
  email: '',
  phone: '',
  notes: '',
})

const form = ref(emptyForm())

function createEmptyCustomerFieldRows() {
  const defs = (customFieldsStore.definitions || []).filter(def => def.entity_type === 'customer' && def.is_active !== false)
  return defs.map(def => ({
    field_definition_id: def.id,
    label: def.label,
    value_type: def.value_type,
    options: def.options || [],
    value: null,
  }))
}

async function loadCustomerFieldRows(entityId) {
  if (!entityId) {
    customerFieldRows.value = createEmptyCustomerFieldRows()
    return
  }
  try {
    const data = await customFieldsStore.fetchEntityValues('customer', entityId)
    customerFieldRows.value = Array.isArray(data?.values) ? data.values.map(value => ({ ...value })) : createEmptyCustomerFieldRows()
  } catch {
    customerFieldRows.value = createEmptyCustomerFieldRows()
  }
}

async function openCreate() {
  editing.value = null
  form.value = emptyForm()
  await loadCustomerFieldRows(null)
  dialogError.value = ''
  dialogOpen.value = true
}

async function openEdit(customer) {
  editing.value = customer
  form.value = {
    name: customer.name ?? '',
    email: customer.email ?? '',
    phone: customer.phone ?? '',
    notes: customer.notes ?? '',
  }
  await loadCustomerFieldRows(customer.id)
  dialogError.value = ''
  dialogOpen.value = true
}

async function saveCustomer() {
  const valid = await formRef.value?.validate()
  if (!valid) return

  saving.value = true
  dialogError.value = ''
  try {
    const payload = {
      ...form.value,
      name: form.value.name.trim(),
      email: form.value.email?.trim() || null,
      phone: form.value.phone?.trim() || null,
      notes: form.value.notes?.trim() || null,
    }

    let savedCustomer
    if (editing.value) {
      savedCustomer = await store.updateCustomer(editing.value.id, payload)
    } else {
      savedCustomer = await store.createCustomer(payload)
    }

    await customFieldsStore.saveEntityValues('customer', savedCustomer.id, customerFieldRows.value.map(row => ({
      field_definition_id: row.field_definition_id,
      value: row.value,
    })))

    dialogOpen.value = false
    $q.notify({ type: 'positive', message: editing.value ? t('customers.updated') : t('customers.createdNotice') })
  } catch (error) {
    dialogError.value = error?.response?.data?.detail || t('common.errorOccurred')
  } finally {
    saving.value = false
  }
}

const deleteDialogOpen = ref(false)
const deleteTarget = ref(null)

function confirmDelete(customer) {
  deleteTarget.value = customer
  deleteDialogOpen.value = true
}

async function doDelete() {
  if (!deleteTarget.value) return
  saving.value = true
  try {
    await store.deleteCustomer(deleteTarget.value.id)
    deleteDialogOpen.value = false
    $q.notify({ type: 'positive', message: t('customers.deleted') })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('common.deleteFailed') })
  } finally {
    saving.value = false
  }
}
</script>
