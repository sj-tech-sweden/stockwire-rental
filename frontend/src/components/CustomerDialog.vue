<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="emit('update:modelValue', $event)">
    <q-card style="width: 520px; max-width: 95vw" class="ec-card">
      <q-card-section>
        <div class="text-h6">{{ customerEditing ? t('customers.editCustomer') : t('customers.newCustomer') }}</div>
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
          <q-input v-model="form.address" :label="t('customers.address')" outlined dense class="q-mb-sm" />
          <div class="row q-col-gutter-sm">
            <div class="col-12 col-md-6">
              <q-input v-model="form.city" :label="t('customers.city')" outlined dense class="q-mb-sm" />
            </div>
            <div class="col-12 col-md-3">
              <q-input v-model="form.postal_code" :label="t('customers.postalCode')" outlined dense class="q-mb-sm" />
            </div>
            <div class="col-12 col-md-3">
              <q-select v-model="form.country" :options="COUNTRIES" :label="t('customers.country')" outlined dense clearable emit-value map-options class="q-mb-sm" />
            </div>
          </div>
          <q-input v-model="form.notes" :label="t('customers.notes')" type="textarea" autogrow outlined dense />

          <q-separator class="q-my-md" />
          <div class="text-subtitle2 q-mb-sm">{{ t('customers.supplierTypes') }}</div>
          <div class="row q-col-gutter-sm q-mb-md">
            <div class="col-6 col-md-3">
              <q-checkbox v-model="form.is_customer" :label="t('customers.isCustomer')" />
            </div>
            <div class="col-6 col-md-3">
              <q-checkbox v-model="form.is_product_supplier" :label="t('customers.isProductSupplier')" />
            </div>
            <div class="col-6 col-md-3">
              <q-checkbox v-model="form.is_rental_supplier" :label="t('customers.isRentalSupplier')" />
            </div>
            <div class="col-6 col-md-3">
              <q-checkbox v-model="form.is_crew_supplier" :label="t('customers.isCrewSupplier')" />
            </div>
          </div>

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
        <q-btn flat :label="t('app.actions.cancel')" @click="emit('update:modelValue', false)" />
        <q-btn v-if="authStore.canEdit" color="primary" unelevated :label="customerEditing ? t('app.actions.save') : t('customers.create')" :loading="saving" @click="saveCustomer" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useCustomersStore } from '../stores/customers'
import { useCustomFieldsStore } from '../stores/customFields'
import { useAuthStore } from '../stores/auth'
import { useSettingsStore } from '../stores/settings'
import { COUNTRIES } from '../constants/countries'
import { translateMaybePrefillCustomFieldLabel, translateMaybePrefillCustomFieldOption } from '../i18n/prefillContent'

const props = defineProps({
  modelValue: Boolean,
  customer: { type: Object, default: null },
})

const emit = defineEmits([
  'update:modelValue',
  'saved',
])

const $q = useQuasar()
const { t } = useI18n()
const store = useCustomersStore()
const customFieldsStore = useCustomFieldsStore()
const authStore = useAuthStore()

const saving = ref(false)
const dialogError = ref('')
const formRef = ref(null)
const customerEditing = ref(null)
const customerFieldRows = ref([])

const booleanValueOptions = [
  { label: t('common.true'), value: 'true' },
  { label: t('common.false'), value: 'false' },
]

const emptyForm = () => ({
  name: '',
  email: '',
  phone: '',
  address: '',
  city: '',
  postal_code: '',
  country: '',
  notes: '',
  is_customer: true,
  is_product_supplier: false,
  is_rental_supplier: false,
  is_crew_supplier: false,
})

const form = ref(emptyForm())

function customFieldLabel(label) {
  return translateMaybePrefillCustomFieldLabel(label, t)
}

function customFieldOption(option) {
  return translateMaybePrefillCustomFieldOption(option, t)
}

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
  customerEditing.value = null
  form.value = emptyForm()
  const settingsStore = useSettingsStore()
  if (settingsStore.companyProfile?.default_country) {
    form.value.country = settingsStore.companyProfile.default_country
  }
  await loadCustomerFieldRows(null)
  dialogError.value = ''
}

async function openEdit(customer) {
  customerEditing.value = customer
  form.value = {
    name: customer.name ?? '',
    email: customer.email ?? '',
    phone: customer.phone ?? '',
    address: customer.address ?? '',
    city: customer.city ?? '',
    postal_code: customer.postal_code ?? '',
    country: customer.country ?? '',
    notes: customer.notes ?? '',
    is_customer: customer.is_customer ?? true,
    is_product_supplier: customer.is_product_supplier ?? false,
    is_rental_supplier: customer.is_rental_supplier ?? false,
    is_crew_supplier: customer.is_crew_supplier ?? false,
  }
  await loadCustomerFieldRows(customer.id)
  dialogError.value = ''
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
      address: form.value.address?.trim() || null,
      city: form.value.city?.trim() || null,
      postal_code: form.value.postal_code?.trim() || null,
      country: form.value.country?.trim() || null,
      notes: form.value.notes?.trim() || null,
    }

    let savedCustomer
    if (customerEditing.value) {
      savedCustomer = await store.updateCustomer(customerEditing.value.id, payload)
    } else {
      savedCustomer = await store.createCustomer(payload)
    }

    await customFieldsStore.saveEntityValues('customer', savedCustomer.id, customerFieldRows.value.map(row => ({
      field_definition_id: row.field_definition_id,
      value: row.value,
    })))

    emit('update:modelValue', false)
    $q.notify({ type: 'positive', message: customerEditing.value ? t('customers.updated') : t('customers.createdNotice') })
    emit('saved')
  } catch (error) {
    dialogError.value = error?.response?.data?.detail || t('common.errorOccurred')
  } finally {
    saving.value = false
  }
}

watch(() => props.modelValue, async (open) => {
  if (open) {
    if (!customFieldsStore.definitions.length) {
      await customFieldsStore.fetchDefinitions('customer')
    }
    if (props.customer) {
      await openEdit(props.customer)
    } else {
      await openCreate()
    }
  }
})
</script>
