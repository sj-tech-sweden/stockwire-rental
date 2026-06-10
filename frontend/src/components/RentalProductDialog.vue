<template>
  <q-dialog :model-value="modelValue" persistent :maximized="isPhone" @update:model-value="emit('update:modelValue', $event)">
    <q-card :style="isPhone ? 'width: 100vw; max-width: 100vw; height: 100vh' : 'min-width: 760px; max-width: 95vw'" class="ec-card">
      <q-card-section><div class="text-h6">{{ draft.id ? t('inventory.editRentalProduct') : t('inventory.newRentalProduct') }}</div></q-card-section>
      <q-card-section class="q-pt-none" :style="isPhone ? 'max-height: calc(100vh - 140px); overflow: auto;' : ''">
        <q-form ref="formRef" @submit.prevent="save">
          <q-expansion-item v-model="generalExpanded" icon="sell" :label="t('inventory.general')" dense header-class="rounded-borders">
            <div class="q-pt-sm row q-col-gutter-sm">
              <div class="col-12 col-md-4"><q-input v-model="draft.sku" :label="t('inventory.columnSku')" outlined dense :rules="[v => !!v || t('login.required')]" /></div>
              <div class="col-12 col-md-8"><q-input v-model="draft.name" :label="t('inventory.columnName')" outlined dense :rules="[v => !!v || t('login.required')]" /></div>
              <div class="col-12 col-md-4"><q-input v-model="draft.category" :label="t('inventory.columnCategory')" outlined dense /></div>
              <div class="col-12 col-md-4"><q-input v-model="draft.supplier_name" :label="t('inventory.columnSupplier')" outlined dense /></div>
            </div>
          </q-expansion-item>

          <q-expansion-item v-model="pricingExpanded" icon="payments" :label="t('inventory.pricingAndSync')" dense header-class="rounded-borders" class="q-mt-sm">
            <div class="q-pt-sm row q-col-gutter-sm">
              <div class="col-12 col-md-4">
                <q-input
                  v-model.number="draft.rental_price"
                  type="number"
                  min="0"
                  step="0.01"
                  :label="t('inventory.columnSupplierPrice')"
                  :suffix="activeCurrencyCode"
                  :hint="currencyHelperText"
                  outlined
                  dense
                  @update:model-value="onSupplierPriceChanged"
                />
              </div>
              <div class="col-12 col-md-4">
                <q-input
                  v-model.number="draft.daily_rate"
                  type="number"
                  min="0"
                  step="0.01"
                  :label="t('inventory.columnClientPrice')"
                  :suffix="activeCurrencyCode"
                  :hint="currencyHelperText"
                  outlined
                  dense
                />
              </div>
              <div class="col-12">
                <q-banner v-if="isCurrentDraftSynced" dense class="bg-info text-white rounded-borders">
                  {{ t('inventory.linkedEventoryInstance', { instance: eventoryInstanceLabelById(draft.external_reference) }) }}
                </q-banner>
                <div v-else class="text-caption text-grey-7">{{ t('inventory.manualRentalProductHint') }}</div>
              </div>
            </div>
          </q-expansion-item>

          <q-expansion-item v-model="customFieldsExpanded" icon="tune" :label="t('inventory.customFields')" dense header-class="rounded-borders" class="q-mt-sm">
            <div class="q-pt-sm">
              <div v-if="fieldRows.length">
                <div v-for="field in fieldRows" :key="field.field_definition_id" class="q-mb-sm">
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
              <div v-else class="text-caption text-grey-7">{{ t('inventory.noProductCustomFields') }}</div>
            </div>
          </q-expansion-item>

          <q-banner v-if="dialogError" class="bg-negative text-white q-mt-sm rounded-borders" dense>
            {{ dialogError }}
          </q-banner>
        </q-form>
      </q-card-section>
      <q-card-actions :align="isPhone ? 'stretch' : 'right'" :class="isPhone ? 'q-pa-md bg-grey-2' : ''">
        <q-btn flat :class="isPhone ? 'full-width q-mb-sm' : ''" :label="t('app.actions.cancel')" @click="emit('update:modelValue', false)" />
        <q-btn
          color="primary"
          unelevated
          :class="isPhone ? 'full-width' : ''"
          :label="draft.id ? t('app.actions.save') : t('users.create')"
          :loading="saving"
          @click="save"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useInventoryStore } from '../stores/inventory'
import { useCustomFieldsStore } from '../stores/customFields'
import { useSettingsStore } from '../stores/settings'
import { normalizeCurrencyCode } from '../constants/currencies'
import { translateMaybePrefillCustomFieldLabel, translateMaybePrefillCustomFieldOption } from '../i18n/prefillContent'

const props = defineProps({
  modelValue: Boolean,
  product: { type: Object, default: null },
})

const emit = defineEmits([
  'update:modelValue',
  'saved',
])

const $q = useQuasar()
const { t } = useI18n()
const store = useInventoryStore()
const customFieldsStore = useCustomFieldsStore()
const settingsStore = useSettingsStore()

const isPhone = computed(() => $q.screen.lt.md)
const activeCurrencyCode = computed(() => normalizeCurrencyCode(settingsStore.companyProfile?.currency, 'SEK'))
const currencyHelperText = computed(() => `${t('settings.company.currencyIso')}: ${activeCurrencyCode.value}`)

const formRef = ref(null)
const saving = ref(false)
const dialogError = ref('')
const generalExpanded = ref(true)
const pricingExpanded = ref(true)
const customFieldsExpanded = ref(false)
const fieldRows = ref([])

const booleanValueOptions = [
  { label: t('common.true'), value: 'true' },
  { label: t('common.false'), value: 'false' },
]

const draft = ref(emptyDraft())

function emptyDraft() {
  return {
    id: null,
    sku: '',
    name: '',
    category: '',
    supplier_name: '',
    rental_price: 0,
    daily_rate: 0,
    replace_cost: 0,
    external_reference: null,
  }
}

function resetDraft() {
  draft.value = emptyDraft()
}

function customFieldLabel(label) {
  return translateMaybePrefillCustomFieldLabel(label, t)
}

function customFieldOption(option) {
  return translateMaybePrefillCustomFieldOption(option, t)
}

function findEventoryInstanceById(instanceId) {
  const key = String(instanceId || '').trim()
  if (!key) return null
  return (settingsStore.integrations?.eventory_instances || []).find(instance => String(instance.id || '').trim() === key) || null
}

function eventoryInstanceLabelById(instanceId) {
  const linked = findEventoryInstanceById(instanceId)
  if (!linked) return instanceId || 'Unknown'
  return linked.name || linked.id
}

function isSyncedEventoryProduct(product) {
  const source = String(product?.external_source || '').trim().toLowerCase()
  const hasExternalReference = !!String(product?.external_reference || '').trim()
  return hasExternalReference && (!source || source === 'eventory')
}

const isCurrentDraftSynced = computed(() => isSyncedEventoryProduct(draft.value))

function roundMoney(value) {
  return Math.round(Number(value || 0) * 100) / 100
}

function applyClientPriceFromMargin() {
  const linkedInstance = findEventoryInstanceById(draft.value.external_reference)
  if (!linkedInstance) return

  const supplierPrice = Math.max(0, Number(draft.value.rental_price || 0))
  const marginPercent = Math.max(0, Number(linkedInstance.price_margin_percent || 0))
  const clientPrice = supplierPrice * (1 + (marginPercent / 100))
  draft.value.daily_rate = roundMoney(clientPrice)

  if (!String(draft.value.supplier_name || '').trim() && String(linkedInstance.supplier_name || '').trim()) {
    draft.value.supplier_name = String(linkedInstance.supplier_name).trim()
  }
}

function onSupplierPriceChanged() {
  applyClientPriceFromMargin()
}

function createEmptyFieldRows() {
  const defs = (customFieldsStore.definitions || []).filter(def => def.entity_type === 'product' && def.is_active !== false)
  return defs.map(def => ({
    field_definition_id: def.id,
    label: def.label,
    value_type: def.value_type,
    options: def.options || [],
    value: null,
  }))
}

async function loadFieldRows(entityId) {
  if (!entityId) {
    fieldRows.value = createEmptyFieldRows()
    return
  }
  try {
    const data = await customFieldsStore.fetchEntityValues('product', entityId)
    fieldRows.value = Array.isArray(data?.values) ? data.values.map(value => ({ ...value })) : createEmptyFieldRows()
  } catch {
    fieldRows.value = createEmptyFieldRows()
  }
}

function openCreate() {
  resetDraft()
  loadFieldRows(null)
  dialogError.value = ''
  generalExpanded.value = true
  pricingExpanded.value = true
  customFieldsExpanded.value = !isPhone.value
}

async function openEdit(product) {
  draft.value = {
    id: product.id,
    sku: product.sku || '',
    name: product.name || '',
    category: product.category || '',
    supplier_name: product.supplier_name || '',
    rental_price: Number(product.rental_price || 0),
    daily_rate: Number(product.daily_rate || 0),
    replace_cost: Number(product.replace_cost || 0),
    external_reference: product.external_reference || null,
  }
  await loadFieldRows(product.id)
  dialogError.value = ''
  generalExpanded.value = true
  pricingExpanded.value = true
  customFieldsExpanded.value = !isPhone.value
}

async function save() {
  const valid = await formRef.value?.validate()
  if (!valid) return

  if (!draft.value.sku.trim() || !draft.value.name.trim()) {
    dialogError.value = 'SKU and name are required'
    return
  }

  saving.value = true
  dialogError.value = ''
  try {
    const keepSyncedLink = isSyncedEventoryProduct(draft.value)
    const payload = {
      sku: draft.value.sku.trim(),
      name: draft.value.name.trim(),
      category: draft.value.category || null,
      supplier_name: draft.value.supplier_name || null,
      rental_price: Number(draft.value.rental_price || 0),
      daily_rate: Number(draft.value.daily_rate || 0),
      product_type: 'rental',
      is_rental_product: true,
      external_source: keepSyncedLink ? 'eventory' : null,
      external_reference: keepSyncedLink ? draft.value.external_reference : null,
      replace_cost: Number(draft.value.replace_cost || 0),
    }

    let savedProduct
    if (draft.value.id) {
      savedProduct = await store.updateProduct(draft.value.id, payload)
      $q.notify({ type: 'positive', message: t('inventory.rentalProductUpdated') })
    } else {
      savedProduct = await store.createProduct(payload)
      $q.notify({ type: 'positive', message: t('inventory.rentalProductCreated') })
    }

    await customFieldsStore.saveEntityValues('product', savedProduct.id, fieldRows.value.map(row => ({
      field_definition_id: row.field_definition_id,
      value: row.value,
    })))

    resetDraft()
    emit('update:modelValue', false)
    emit('saved')
  } catch (error) {
    dialogError.value = error?.response?.data?.detail || t('inventory.failedSaveRentalProduct')
  } finally {
    saving.value = false
  }
}

watch(() => props.modelValue, async (open) => {
  if (open) {
    if (!customFieldsStore.definitions.length) {
      await customFieldsStore.fetchDefinitions('product')
    }
    if (props.product) {
      await openEdit(props.product)
    } else {
      openCreate()
    }
  }
})
</script>
