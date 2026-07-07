<template>
  <q-dialog v-model="dialog" persistent>
    <q-card style="width: 560px; max-width: 95vw" class="ec-card">
      <q-card-section><div class="text-h6">{{ t('inventory.bulkEditProducts') }}</div></q-card-section>
      <q-card-section class="q-pt-none">
        <div class="text-caption text-grey-7 q-mb-sm">{{ t('inventory.updatingProductsCount', { count: props.selectedProducts.length }) }}</div>
        <div class="row q-col-gutter-sm">
          <div class="col-12 col-md-6"><q-select v-model="form.category_id" :options="allCategorySelectOptions" label="Category" outlined dense clearable emit-value map-options /></div>
          <div class="col-12 col-md-6"><q-select v-model="form.product_type" :options="productTypeOptions" label="Type" outlined dense clearable emit-value map-options /></div>
          <div class="col-12 col-md-6">
            <q-select
              v-model="form.brand"
              :options="brandOptions"
              label="Brand"
              outlined
              dense
              clearable
              use-input
              fill-input
              input-debounce="0"
              emit-value
              map-options
              @new-value="onNewBrandValue"
            >
              <template #prepend>
                <q-icon name="storefront" color="grey-6" />
              </template>
            </q-select>
          </div>
          <div class="col-12 col-md-6">
            <q-select
              v-model="form.manufacturer"
              :options="manufacturerOptions"
              label="Manufacturer"
              outlined
              dense
              clearable
              use-input
              fill-input
              input-debounce="0"
              emit-value
              map-options
              @new-value="onNewManufacturerValue"
            >
              <template #prepend>
                <q-icon name="factory" color="grey-6" />
              </template>
            </q-select>
          </div>
          <div class="col-12 col-md-6"><q-input v-model.number="form.maintenance_interval_days" type="number" min="1" label="Maintenance interval (days)" outlined dense clearable /></div>
          <div class="col-12 col-md-6">
            <q-input
              v-model.number="form.daily_rate"
              type="number"
              min="0"
              step="0.01"
              label="Daily rate"
              :suffix="activeCurrencyCode"
              :hint="currencyHelperText"
              outlined
              dense
              clearable
            />
          </div>
        </div>
        <q-banner v-if="error" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ error }}</q-banner>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat label="Cancel" @click="dialog = false" />
        <q-btn color="primary" unelevated :label="t('inventory.apply')" :loading="saving" @click="save" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQuasar } from 'quasar'
import { useInventoryStore } from '../stores/inventory'
import { useSettingsStore } from '../stores/settings'
import { normalizeCurrencyCode } from '../constants/currencies'

const { t } = useI18n()
const $q = useQuasar()
const store = useInventoryStore()
const settingsStore = useSettingsStore()

const props = defineProps({
  modelValue: Boolean,
  selectedProducts: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const dialog = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const emptyForm = () => ({
  category_id: null,
  product_type: null,
  brand: '',
  manufacturer: '',
  maintenance_interval_days: null,
  daily_rate: null,
})

const form = ref(emptyForm())

watch(() => props.modelValue, (val) => {
  if (val) {
    form.value = emptyForm()
    error.value = ''
  }
})

const error = ref('')
const saving = ref(false)

const activeCurrencyCode = computed(() => normalizeCurrencyCode(settingsStore.companyProfile?.currency, 'SEK'))
const currencyHelperText = computed(() => `${t('settings.company.currencyIso')}: ${activeCurrencyCode.value}`)

const productTypeOptions = [
  { label: t('inventory.productTypeEquipment'), value: 'equipment' },
  { label: t('inventory.productTypeAccessory'), value: 'accessory' },
  { label: t('inventory.productTypeConsumable'), value: 'consumable' },
  { label: t('inventory.productTypeCase'), value: 'case' },
]

const brandOptions = computed(() => settingsStore.brandOptions.map(value => ({ label: value, value })))
const manufacturerOptions = computed(() => settingsStore.manufacturerOptions.map(value => ({ label: value, value })))

const allCategorySelectOptions = computed(() => {
  const flat = []
  const walk = (nodes, prefix) => {
    for (const node of nodes || []) {
      const label = prefix ? `${prefix} / ${node.name}` : node.name
      flat.push({ label, value: node.id })
      walk(node.children || [], label)
    }
  }
  walk(store.categoryTree)
  return flat
})

function selectedRowIds(rows) {
  return [...new Set((rows || []).map(row => Number(row?.id || 0)).filter(Boolean))]
}

function onNewBrandValue(val, done) {
  done(val, 'add-unique')
}

function onNewManufacturerValue(val, done) {
  done(val, 'add-unique')
}

async function save() {
  const ids = selectedRowIds(props.selectedProducts)
  if (!ids.length) return

  const patch = {}
  if (form.value.category_id != null) patch.category_id = form.value.category_id
  if (form.value.product_type) patch.product_type = form.value.product_type
  if (String(form.value.brand || '').trim()) patch.brand = String(form.value.brand).trim()
  if (String(form.value.manufacturer || '').trim()) patch.manufacturer = String(form.value.manufacturer).trim()
  if (form.value.maintenance_interval_days != null) patch.maintenance_interval_days = form.value.maintenance_interval_days
  if (form.value.daily_rate != null) patch.daily_rate = form.value.daily_rate
  if (!Object.keys(patch).length) {
    error.value = 'Choose at least one field to update'
    return
  }

  saving.value = true
  error.value = ''
  try {
    const result = await store.bulkUpdateProducts(ids, patch)
    dialog.value = false
    $q.notify({ type: 'positive', message: `Products updated: ${result?.updated || 0}` })
    emit('saved')
  } catch (err) {
    error.value = err?.response?.data?.detail || 'Bulk product update failed'
  } finally {
    saving.value = false
  }
}
</script>
