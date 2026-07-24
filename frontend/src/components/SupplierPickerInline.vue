<template>
  <div>
    <div class="row q-col-gutter-sm items-end">
      <div class="col">
        <q-select
          :model-value="modelValue"
          :options="filteredOptions"
          :label="label"
          outlined
          dense
          clearable
          emit-value
          map-options
          use-input
          fill-input
          input-debounce="0"
          @filter="onFilter"
          @update:model-value="emit('update:modelValue', $event)"
        />
      </div>
      <div class="col-auto">
        <q-btn flat dense icon="add" color="primary" @click="showCreate = true">
          <q-tooltip>{{ t('customers.newSupplier') }}</q-tooltip>
        </q-btn>
      </div>
    </div>

    <q-dialog v-model="showCreate" persistent>
      <q-card style="min-width: 400px" class="ec-card">
        <q-card-section>
          <div class="text-h6">{{ t('customers.newSupplier') }}</div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-input v-model="newName" :label="t('customers.name')" outlined dense class="q-mb-sm" :rules="[v => !!v || t('login.required')]" />
          <q-input v-model="newEmail" :label="t('profile.email')" type="email" outlined dense class="q-mb-sm" />
          <q-input v-model="newPhone" :label="t('customers.phone')" outlined dense class="q-mb-sm" />
          <q-checkbox v-model="newIsProductSupplier" :label="t('customers.isProductSupplier')" />
          <q-checkbox v-model="newIsRentalSupplier" :label="t('customers.isRentalSupplier')" />
          <q-checkbox v-model="newIsCrewSupplier" :label="t('customers.isCrewSupplier')" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="showCreate = false" />
          <q-btn color="primary" unelevated :label="t('customers.create')" :loading="creating" @click="createSupplier" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQuasar } from 'quasar'
import { useCustomersStore } from '../stores/customers'

const props = defineProps({
  modelValue: { type: Number, default: null },
  label: { type: String, default: 'Supplier' },
  supplierType: { type: String, default: 'product' },
  productSupplierIds: { type: Array, default: null },
})

const emit = defineEmits(['update:modelValue', 'created'])

const { t } = useI18n()
const $q = useQuasar()
const customersStore = useCustomersStore()

const showCreate = ref(false)
const creating = ref(false)
const newName = ref('')
const newEmail = ref('')
const newPhone = ref('')
const newIsProductSupplier = ref(props.supplierType === 'product')
const newIsRentalSupplier = ref(props.supplierType === 'rental')
const newIsCrewSupplier = ref(props.supplierType === 'crew')
const searchFilter = ref('')

watch(() => props.supplierType, (val) => {
  newIsProductSupplier.value = val === 'product'
  newIsRentalSupplier.value = val === 'rental'
  newIsCrewSupplier.value = val === 'crew'
})

const allOptions = computed(() => {
  let list = customersStore.customers
  if (props.supplierType === 'product') {
    list = list.filter(c => c.is_product_supplier)
  } else if (props.supplierType === 'rental') {
    list = list.filter(c => c.is_rental_supplier)
  } else if (props.supplierType === 'crew') {
    list = list.filter(c => c.is_crew_supplier)
  }
  if (props.productSupplierIds && props.productSupplierIds.length) {
    const allowedIds = new Set(props.productSupplierIds)
    list = list.filter(c => allowedIds.has(c.id))
  }
  return list.map(c => ({ label: c.name, value: c.id }))
})

const filteredOptions = ref([])

function onFilter(val, update) {
  searchFilter.value = val
  update(() => {
    const term = String(val || '').toLowerCase()
    if (term && props.productSupplierIds && props.productSupplierIds.length) {
      let list = customersStore.customers
      if (props.supplierType === 'product') {
        list = list.filter(c => c.is_product_supplier)
      } else if (props.supplierType === 'rental') {
        list = list.filter(c => c.is_rental_supplier)
      } else if (props.supplierType === 'crew') {
        list = list.filter(c => c.is_crew_supplier)
      }
      filteredOptions.value = list
        .map(c => ({ label: c.name, value: c.id }))
        .filter(o => o.label.toLowerCase().includes(term))
    } else {
      filteredOptions.value = allOptions.value.filter(
        o => !term || o.label.toLowerCase().includes(term)
      )
    }
  })
}

async function createSupplier() {
  if (!newName.value.trim()) return
  creating.value = true
  try {
    const payload = {
      name: newName.value.trim(),
      email: newEmail.value.trim() || null,
      phone: newPhone.value.trim() || null,
      is_customer: false,
      is_product_supplier: newIsProductSupplier.value,
      is_rental_supplier: newIsRentalSupplier.value,
      is_crew_supplier: newIsCrewSupplier.value,
    }
    const created = await customersStore.createCustomer(payload)
    emit('update:modelValue', created.id)
    emit('created', created)
    showCreate.value = false
    newName.value = ''
    newEmail.value = ''
    newPhone.value = ''
    newIsProductSupplier.value = props.supplierType === 'product'
    newIsRentalSupplier.value = props.supplierType === 'rental'
    newIsCrewSupplier.value = props.supplierType === 'crew'
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || 'Failed to create supplier' })
  } finally {
    creating.value = false
  }
}
</script>
