<template>
  <q-dialog :model-value="modelValue" persistent :maximized="isPhone" @update:model-value="emit('update:modelValue', $event)">
    <q-card :style="isPhone ? 'width: 100vw; max-width: 100vw; height: 100vh' : 'min-width: 760px; max-width: 95vw'" class="ec-card">
      <q-card-section><div class="text-h6">{{ productEditing ? 'Edit product' : 'New product' }}</div></q-card-section>
      <q-card-section class="q-pt-none" :style="isPhone ? 'max-height: calc(100vh - 140px); overflow: auto;' : ''">
        <q-form ref="productFormRef" @submit.prevent="saveProduct">
          <div class="text-subtitle2 q-mb-sm">Identity</div>
          <div class="row q-col-gutter-sm">
            <div class="col-12 col-md-4">
              <q-input v-model="productForm.sku" label="SKU" outlined dense :rules="[v => !!v || 'Required']">
                <template #append>
                  <q-btn flat dense no-caps color="primary" icon="autorenew" label="Generate" :loading="generatingProductSku" @click="generateProductSku(true)" />
                </template>
              </q-input>
            </div>
            <div class="col-12 col-md-2">
              <q-input v-model="productSkuPrefix" label="SKU prefix" outlined dense hint="e.g. SPK-" />
            </div>
            <div class="col-12 col-md-8"><q-input v-model="productForm.name" label="Name" outlined dense :rules="[v => !!v || 'Required']" /></div>
            <div class="col-12 col-md-4">
              <q-select v-model="productForm.product_type" :options="productTypeOptions" label="Product type" outlined dense emit-value map-options />
            </div>
            <div class="col-12 col-md-8">
              <q-select
                v-model="productForm.category_id"
                :options="categorySelectOptions"
                label="Category"
                outlined
                dense
                clearable
                use-input
                fill-input
                input-debounce="0"
                emit-value
                map-options
                @filter="filterCategoryOptions"
              />
            </div>
            <div class="col-12 col-md-4">
              <q-input v-model="productForm.supplier_name" label="Supplier" outlined dense />
            </div>
          </div>

          <q-separator class="q-my-md" />
          <div class="text-subtitle2 q-mb-sm">Brand and Manufacturer</div>
          <div class="row q-col-gutter-sm">
            <div class="col-12 col-md-4">
              <q-select
                v-model="productForm.brand"
                :options="brandSelectOptions"
                label="Brand"
                outlined
                dense
                use-input
                fill-input
                input-debounce="0"
                emit-value
                map-options
                @filter="filterBrandOptions"
                @new-value="onNewBrandValue"
                @update:model-value="onBrandChanged"
              />
            </div>
            <div class="col-12 col-md-4">
              <q-select
                v-model="productForm.manufacturer"
                :options="manufacturerSelectOptions"
                label="Manufacturer"
                outlined
                dense
                use-input
                fill-input
                input-debounce="0"
                emit-value
                map-options
                @filter="filterManufacturerOptions"
                @new-value="onNewManufacturerValue"
                @update:model-value="onManufacturerChanged"
              />
            </div>
            <div class="col-12 col-md-4"><q-input v-model="productForm.brand_url" type="url" label="Brand link (optional)" outlined dense /></div>
            <div class="col-12 col-md-4"><q-input v-model="productForm.manufacturer_url" type="url" label="Manufacturer link (optional)" outlined dense /></div>
          </div>

          <q-separator class="q-my-md" />
          <div class="text-subtitle2 q-mb-sm">Commercial and Maintenance</div>
          <div class="row q-col-gutter-sm">
            <div class="col-12 col-md-4">
              <q-input
                v-model.number="productForm.daily_rate"
                type="number"
                step="0.01"
                label="Daily rate"
                :suffix="activeCurrencyCode"
                :hint="currencyHelperText"
                outlined
                dense
              />
            </div>
            <div class="col-12 col-md-4">
              <q-input
                v-model.number="productForm.replace_cost"
                type="number"
                step="0.01"
                label="Replacement cost"
                :suffix="activeCurrencyCode"
                :hint="currencyHelperText"
                outlined
                dense
              />
            </div>
            <div class="col-12 col-md-4"><q-input v-model.number="productForm.maintenance_interval_days" type="number" label="Maintenance interval (days)" outlined dense /></div>
            <div class="col-12 col-md-4"><q-input v-model.number="productForm.power_consumption_watts" type="number" step="0.01" label="Power (W)" outlined dense /></div>
          </div>

          <q-separator class="q-my-md" />
          <div class="text-subtitle2 q-mb-sm">Physical Specs</div>
          <div class="row q-col-gutter-sm">
            <div class="col-12 col-md-4"><q-input v-model.number="productForm.weight_kg" type="number" step="0.001" label="Weight (kg)" outlined dense /></div>
            <div class="col-12 col-md-3"><q-input v-model.number="productForm.height_cm" type="number" step="0.01" label="Height (cm)" outlined dense /></div>
            <div class="col-12 col-md-3"><q-input v-model.number="productForm.width_cm" type="number" step="0.01" label="Width (cm)" outlined dense /></div>
            <div class="col-12 col-md-3"><q-input v-model.number="productForm.depth_cm" type="number" step="0.01" label="Depth (cm)" outlined dense /></div>
            <div class="col-12 col-md-3" />

            <div class="col-12 q-mt-sm">
              <q-separator class="q-my-md" />
              <q-expansion-item
                v-model="accessoriesExpanded"
                icon="extension"
                label="Accessories"
                dense
                header-class="rounded-borders"
              >
                <div class="text-caption text-grey-7 q-mb-sm">Define accessory products for this product. Mark each as required or optional.</div>
                <div class="row q-col-gutter-sm items-end q-mb-sm">
                  <div class="col-12 col-md-7">
                    <q-select
                      v-model="newAccessoryProductId"
                      :options="filteredAccessoryProductOptions"
                      label="Accessory product"
                      outlined
                      dense
                      emit-value
                      map-options
                      use-input
                      fill-input
                      input-debounce="0"
                      @filter="filterAccessoryProductOptions"
                    />
                  </div>
                  <div class="col-6 col-md-2">
                    <q-input v-model.number="newAccessoryQty" type="number" min="1" label="Qty" outlined dense />
                  </div>
                  <div class="col-6 col-md-2">
                    <q-toggle v-model="newAccessoryRequired" label="Required" color="primary" />
                  </div>
                  <div class="col-12 col-md-1">
                    <q-btn color="primary" unelevated icon="add" @click="addAccessoryRow" />
                  </div>
                </div>

                <q-list bordered separator class="rounded-borders">
                  <q-item v-for="row in productForm.accessories" :key="`acc-${row.accessory_product_id}`">
                    <q-item-section>
                      <q-item-label>{{ productNameById(row.accessory_product_id) }}</q-item-label>
                      <q-item-label caption>{{ row.required ? 'Required' : 'Optional' }} · Qty {{ row.quantity }}</q-item-label>
                    </q-item-section>
                    <q-item-section side>
                      <q-btn flat dense icon="delete" color="negative" @click="removeAccessoryRow(row.accessory_product_id)" />
                    </q-item-section>
                  </q-item>
                  <q-item v-if="!productForm.accessories.length">
                    <q-item-section>
                      <q-item-label caption>No accessories configured.</q-item-label>
                    </q-item-section>
                  </q-item>
                </q-list>
              </q-expansion-item>
            </div>

            <div class="col-12 q-mt-sm">
              <q-separator class="q-my-md" />
              <q-expansion-item
                v-model="componentsExpanded"
                icon="widgets"
                label="Components"
                dense
                header-class="rounded-borders"
              >
                <div class="text-caption text-grey-7 q-mb-sm">Define component products that make up this bundle.</div>
                <div class="row q-col-gutter-sm items-end q-mb-sm">
                  <div class="col-12 col-md-9">
                    <q-select
                      v-model="newComponentProductId"
                      :options="filteredComponentProductOptions"
                      label="Component product"
                      outlined
                      dense
                      emit-value
                      map-options
                      use-input
                      fill-input
                      input-debounce="0"
                      @filter="filterComponentProductOptions"
                    />
                  </div>
                  <div class="col-6 col-md-2">
                    <q-input v-model.number="newComponentQty" type="number" min="1" label="Qty" outlined dense />
                  </div>
                  <div class="col-12 col-md-1">
                    <q-btn color="primary" unelevated icon="add" @click="addComponentRow" />
                  </div>
                </div>

                <q-list bordered separator class="rounded-borders">
                  <q-item v-for="row in productForm.components" :key="`cmp-${row.component_product_id}`">
                    <q-item-section>
                      <q-item-label>{{ productNameById(row.component_product_id) }}</q-item-label>
                      <q-item-label caption>Qty {{ row.quantity }}</q-item-label>
                    </q-item-section>
                    <q-item-section side>
                      <q-btn flat dense icon="delete" color="negative" @click="removeComponentRow(row.component_product_id)" />
                    </q-item-section>
                  </q-item>
                  <q-item v-if="!productForm.components.length">
                    <q-item-section>
                      <q-item-label caption>No components configured.</q-item-label>
                    </q-item-section>
                  </q-item>
                </q-list>
              </q-expansion-item>
            </div>

            <div class="col-12 q-mt-sm">
              <q-separator class="q-my-md" />
              <div class="text-subtitle2 q-mb-sm">Linked Devices</div>
              <div class="text-caption text-grey-7 q-mb-sm">
                {{ productEditing ? `All devices linked to ${productEditing.sku}` : 'Save product to link devices.' }}
              </div>
              <div class="row q-col-gutter-sm q-mb-sm" v-if="productEditing">
                <div class="col-auto">
                  <q-badge color="primary" text-color="white" :label="`Total: ${productLinkedDevices.length}`" />
                </div>
                <div class="col-auto">
                  <q-badge color="positive" text-color="white" :label="`Available: ${productLinkedAvailability.available}`" />
                </div>
                <div class="col-auto">
                  <q-badge color="warning" text-color="black" :label="`Reserved: ${productLinkedAvailability.reserved}`" />
                </div>
                <div class="col-auto">
                  <q-badge color="info" text-color="white" :label="`In Use: ${productLinkedAvailability.in_use}`" />
                </div>
                <div class="col-auto">
                  <q-badge color="negative" text-color="white" :label="`Maintenance: ${productLinkedAvailability.maintenance}`" />
                </div>
              </div>

              <q-list v-if="productEditing" bordered separator class="rounded-borders q-mb-md">
                <q-item v-for="row in productLinkedDevices" :key="row.id">
                  <q-item-section>
                    <q-item-label>{{ row.asset_tag }}</q-item-label>
                    <q-item-label caption>
                      Status: {{ row.status }} · Condition: {{ row.condition || 'n/a' }} · Location: {{ row.case_asset_tag ? `Case: ${row.case_asset_tag}` : (zoneNameById(row.location_zone_id) || 'Unassigned') }}
                    </q-item-label>
                    <q-item-label caption v-if="row.current_job_code">Current job: {{ row.current_job_code }}</q-item-label>
                  </q-item-section>
                  <q-item-section side top>
                    <div class="row no-wrap items-center q-gutter-xs">
                      <q-btn
                        flat
                        dense
                        :round="isPhone"
                        :color="productActionColor"
                        class="inventory-action-contrast"
                        icon="inventory_2"
                        :label="isPhone ? void 0 : 'Product'"
                        :aria-label="isPhone ? 'Open product' : void 0"
                        @click="emit('edit-product', row.product_id)"
                      />
                      <q-btn
                        flat
                        dense
                        :round="isPhone"
                        :color="infoActionColor"
                        icon="info"
                        :label="isPhone ? void 0 : 'Info'"
                        :aria-label="isPhone ? 'Open device info' : void 0"
                        @click="emit('view-device', row.id)"
                      />
                      <q-btn
                        flat
                        dense
                        :round="isPhone"
                        color="primary"
                        icon="edit"
                        :label="isPhone ? void 0 : 'Edit'"
                        :aria-label="isPhone ? 'Edit device' : void 0"
                        @click="emit('edit-device', row.id)"
                      />
                    </div>
                  </q-item-section>
                </q-item>
                <q-item v-if="!productLinkedDevices.length">
                  <q-item-section>
                    <q-item-label caption>No devices linked to this product yet.</q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
            </div>
          </div>
          <q-separator class="q-my-md" />
          <q-expansion-item v-model="customFieldsExpanded" icon="tune" label="Custom Fields" dense header-class="rounded-borders">
            <div class="q-pt-sm">
              <div v-if="productFieldRows.length">
                <div v-for="field in productFieldRows" :key="field.field_definition_id" class="q-mb-sm">
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
                    :options="(field.options || []).map(o => ({ label: customFieldOption(o), value: o }))"
                    :label="customFieldLabel(field.label)"
                    outlined
                    dense
                    clearable
                    emit-value
                    map-options
                  />
                </div>
              </div>
              <div v-else class="text-caption text-grey-7">No product custom fields defined.</div>
            </div>
          </q-expansion-item>
          <q-banner v-if="productDialogError" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ productDialogError }}</q-banner>
        </q-form>
      </q-card-section>
      <EntityAttachmentsPanel
        entity-type="product"
        :entity-id="productEditing?.id || null"
        title="Product Documents"
        default-category="product-document"
      />
      <q-card-actions :align="isPhone ? 'stretch' : 'right'" :class="isPhone ? 'q-pa-md bg-grey-2' : ''">
        <q-btn flat :class="isPhone ? 'full-width q-mb-sm' : ''" label="Cancel" @click="closeProductDialog" />
        <q-btn color="primary" unelevated :class="isPhone ? 'full-width' : ''" :label="productEditing ? 'Save' : 'Create'" :loading="saving" @click="saveProduct" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useInventoryStore } from '../stores/inventory'
import { useSettingsStore } from '../stores/settings'
import { useCustomFieldsStore } from '../stores/customFields'
import { translateMaybePrefillCustomFieldLabel, translateMaybePrefillCustomFieldOption } from '../i18n/prefillContent'
import { normalizeCurrencyCode } from '../constants/currencies'
import { isRentalProduct } from '../utils/inventory-overview'
import EntityAttachmentsPanel from './EntityAttachmentsPanel.vue'

const props = defineProps({
  modelValue: Boolean,
  product: { type: Object, default: null },
})

const emit = defineEmits([
  'update:modelValue',
  'saved',
  'edit-device',
  'view-device',
  'edit-product',
])

const $q = useQuasar()
const { t } = useI18n()
const store = useInventoryStore()
const settingsStore = useSettingsStore()
const customFieldsStore = useCustomFieldsStore()

function customFieldLabel(label) {
  return translateMaybePrefillCustomFieldLabel(label, t)
}

function customFieldOption(option) {
  return translateMaybePrefillCustomFieldOption(option, t)
}

const isPhone = computed(() => $q.screen.lt.md)
const productActionColor = computed(() => ($q.dark.isActive ? 'green-4' : 'secondary'))
const infoActionColor = computed(() => ($q.dark.isActive ? 'teal-4' : 'secondary'))
const activeCurrencyCode = computed(() => normalizeCurrencyCode(settingsStore.companyProfile?.currency, 'SEK'))
const currencyHelperText = computed(() => `${t('settings.company.currencyIso')}: ${activeCurrencyCode.value}`)

const saving = ref(false)
const generatingProductSku = ref(false)
const productSkuPrefix = ref('PRD-')
const skuPrefixByProductType = ref({})
const PREFIX_MEMORY_STORAGE_KEY = 'inventory.prefix-memory.v1'

const productEditing = ref(null)
const productDialogError = ref('')
const productFormRef = ref(null)
const accessoriesExpanded = ref(true)
const newAccessoryProductId = ref(null)
const newAccessoryQty = ref(1)
const newAccessoryRequired = ref(false)
const componentsExpanded = ref(true)
const newComponentProductId = ref(null)
const newComponentQty = ref(1)

const customFieldsExpanded = ref(true)
const productFieldRows = ref([])

const booleanValueOptions = [
  { label: t('common.true'), value: 'true' },
  { label: t('common.false'), value: 'false' },
]

function createEmptyProductFieldRows() {
  const defs = (customFieldsStore.definitions || []).filter(def => def.entity_type === 'product' && def.is_active !== false)
  productFieldRows.value = defs.map(def => ({
    field_definition_id: def.id,
    label: def.label,
    value_type: def.value_type,
    options: def.options || [],
    value: null,
  }))
}

async function loadProductFieldRows(entityId) {
  if (!entityId) {
    createEmptyProductFieldRows()
    return
  }
  try {
    const data = await customFieldsStore.fetchEntityValues('product', entityId)
    productFieldRows.value = Array.isArray(data?.values) ? data.values.map(v => ({ ...v })) : createEmptyProductFieldRows()
  } catch {
    createEmptyProductFieldRows()
  }
}

const emptyProductForm = () => ({
  sku: '',
  name: '',
  category_id: null,
  supplier_name: '',
  brand: settingsStore.defaultBrand || '',
  manufacturer: settingsStore.defaultManufacturer || '',
  brand_url: '',
  manufacturer_url: '',
  product_type: 'equipment',
  accessories: [],
  components: [],
  weight_kg: null, height_cm: null, width_cm: null, depth_cm: null,
  maintenance_interval_days: null, power_consumption_watts: null, daily_rate: 0, replace_cost: 0,
})
const productForm = ref(emptyProductForm())

const productTypeOptions = [
  { label: t('inventory.productTypeEquipment'), value: 'equipment' },
  { label: t('inventory.productTypeAccessory'), value: 'accessory' },
  { label: t('inventory.productTypeConsumable'), value: 'consumable' },
  { label: t('inventory.productTypeCase'), value: 'case' },
  { label: t('inventory.productTypeBundle'), value: 'bundle' },
]

const productOptions = computed(() => store.products.map(p => ({ label: `${p.sku} - ${p.name}`, value: p.id })))
const accessoryProductOptions = computed(() => {
  return productOptions.value.filter(o => {
    if (o.value === productEditing.value?.id) return false
    const product = store.products.find(p => p.id === o.value)
    if (product && isRentalProduct(product)) return false
    return true
  })
})
const componentProductOptions = computed(() => {
  return productOptions.value.filter(o => {
    if (o.value === productEditing.value?.id) return false
    const product = store.products.find(p => p.id === o.value)
    if (product && isRentalProduct(product)) return false
    return true
  })
})

const filteredAccessoryProductOptions = ref([])
const filteredComponentProductOptions = ref([])

const allBrandOptions = computed(() =>
  [...settingsStore.brandOptions].sort((a, b) => a.localeCompare(b)).map(value => ({ label: value, value }))
)
const allManufacturerOptions = computed(() =>
  [...settingsStore.manufacturerOptions].sort((a, b) => a.localeCompare(b)).map(value => ({ label: value, value }))
)
const brandSelectOptions = ref([])
const manufacturerSelectOptions = ref([])
const brandManufacturerMap = computed(() => settingsStore.brandManufacturerMap || {})
const brandLinks = computed(() => settingsStore.brandLinks || {})
const manufacturerLinks = computed(() => settingsStore.manufacturerLinks || {})

const allCategorySelectOptions = computed(() => {
  const flat = []
  const walk = (nodes, prefix = '') => {
    for (const node of nodes || []) {
      const label = prefix ? `${prefix} / ${node.name}` : node.name
      flat.push({ label, value: node.id })
      walk(node.children || [], label)
    }
  }
  walk(store.categoryTree)
  return flat
})

const categorySelectOptions = ref([])

watch(allCategorySelectOptions, (options) => {
  categorySelectOptions.value = options
}, { immediate: true })

watch(allBrandOptions, (options) => {
  brandSelectOptions.value = options
}, { immediate: true })

watch(allManufacturerOptions, (options) => {
  manufacturerSelectOptions.value = options
}, { immediate: true })

function filterCategoryOptions(val, update) {
  update(() => {
    const needle = val.trim().toLowerCase()
    if (!needle) {
      categorySelectOptions.value = allCategorySelectOptions.value
      return
    }
    categorySelectOptions.value = allCategorySelectOptions.value.filter(option => option.label.toLowerCase().includes(needle))
  })
}

watch(accessoryProductOptions, (options) => {
  filteredAccessoryProductOptions.value = options
}, { immediate: true })

watch(componentProductOptions, (options) => {
  filteredComponentProductOptions.value = options
}, { immediate: true })

function filterAccessoryProductOptions(val, update) {
  update(() => {
    const needle = val.trim().toLowerCase()
    if (!needle) {
      filteredAccessoryProductOptions.value = accessoryProductOptions.value
      return
    }
    filteredAccessoryProductOptions.value = accessoryProductOptions.value.filter(
      option => option.label.toLowerCase().includes(needle)
    )
  })
}

function filterComponentProductOptions(val, update) {
  update(() => {
    const needle = val.trim().toLowerCase()
    if (!needle) {
      filteredComponentProductOptions.value = componentProductOptions.value
      return
    }
    filteredComponentProductOptions.value = componentProductOptions.value.filter(
      option => option.label.toLowerCase().includes(needle)
    )
  })
}
function filterBrandOptions(val, update) {
  update(() => {
    const needle = val.trim().toLowerCase()
    if (!needle) {
      brandSelectOptions.value = allBrandOptions.value
      return
    }
    brandSelectOptions.value = allBrandOptions.value.filter(option => option.label.toLowerCase().includes(needle))
  })
}

function filterManufacturerOptions(val, update) {
  update(() => {
    const needle = val.trim().toLowerCase()
    if (!needle) {
      manufacturerSelectOptions.value = allManufacturerOptions.value
      return
    }
    manufacturerSelectOptions.value = allManufacturerOptions.value.filter(option => option.label.toLowerCase().includes(needle))
  })
}

const zoneById = computed(() => {
  const map = new Map()
  for (const zone of store.zones) map.set(zone.id, zone)
  return map
})

function zoneNameById(id) {
  if (!id) return null
  return zoneById.value.get(id)?.name ?? null
}

const productLinkedDevices = computed(() => {
  if (!productEditing.value?.id) return []
  return (store.devices || [])
    .filter(row => row.product_id === productEditing.value.id)
    .slice()
    .sort((a, b) => String(a.asset_tag || '').localeCompare(String(b.asset_tag || '')))
})

const productLinkedAvailability = computed(() => {
  const bucket = { available: 0, reserved: 0, in_use: 0, maintenance: 0 }
  for (const row of productLinkedDevices.value) {
    const status = String(row.status || '').toLowerCase()
    if (status === 'available') bucket.available += 1
    else if (status === 'reserved') bucket.reserved += 1
    else if (status === 'in_use') bucket.in_use += 1
    else if (status === 'maintenance') bucket.maintenance += 1
  }
  return bucket
})

function productNameById(productId) {
  const item = store.products.find(row => row.id === productId)
  if (!item) return `Product #${productId}`
  return `${item.sku} - ${item.name}`
}

function addAccessoryRow() {
  const accessoryId = Number(newAccessoryProductId.value || 0)
  if (!accessoryId) return

  const quantity = Math.max(Number(newAccessoryQty.value || 1), 1)
  const existing = (productForm.value.accessories || []).find(item => item.accessory_product_id === accessoryId)
  if (existing) {
    existing.quantity = quantity
    existing.required = !!newAccessoryRequired.value
  } else {
    productForm.value.accessories = [
      ...(productForm.value.accessories || []),
      {
        accessory_product_id: accessoryId,
        quantity,
        required: !!newAccessoryRequired.value,
      },
    ]
  }

  newAccessoryProductId.value = null
  newAccessoryQty.value = 1
  newAccessoryRequired.value = false
}

function removeAccessoryRow(accessoryProductId) {
  productForm.value.accessories = (productForm.value.accessories || []).filter(
    item => item.accessory_product_id !== accessoryProductId
  )
}

function addComponentRow() {
  const componentId = Number(newComponentProductId.value || 0)
  if (!componentId) return

  const quantity = Math.max(Number(newComponentQty.value || 1), 1)
  const existing = (productForm.value.components || []).find(item => item.component_product_id === componentId)
  if (existing) {
    existing.quantity = quantity
  } else {
    productForm.value.components = [
      ...(productForm.value.components || []),
      {
        component_product_id: componentId,
        quantity,
      },
    ]
  }

  newComponentProductId.value = null
  newComponentQty.value = 1
}

function removeComponentRow(componentProductId) {
  productForm.value.components = (productForm.value.components || []).filter(
    item => item.component_product_id !== componentProductId
  )
}

function loadPrefixMemory() {
  if (typeof window === 'undefined') return
  try {
    const raw = window.localStorage.getItem(PREFIX_MEMORY_STORAGE_KEY)
    if (!raw) return
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed === 'object') {
      skuPrefixByProductType.value = parsed.skuByType && typeof parsed.skuByType === 'object' ? { ...parsed.skuByType } : {}
    }
  } catch {
    // Ignore invalid local storage data.
  }
}

function persistPrefixMemory() {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(PREFIX_MEMORY_STORAGE_KEY, JSON.stringify({
      skuByType: skuPrefixByProductType.value,
    }))
  } catch {
    // Ignore storage quota/privacy mode failures.
  }
}

function normalizePrefix(value, fallback = '') {
  const cleaned = String(value || '').trim()
  return cleaned || fallback
}

function rememberSkuPrefixForType(type, prefix) {
  const key = String(type || '').trim()
  if (!key) return
  const normalized = normalizePrefix(prefix)
  if (!normalized) return
  skuPrefixByProductType.value = {
    ...skuPrefixByProductType.value,
    [key]: normalized,
  }
  persistPrefixMemory()
}

function applySkuPrefixForType(type) {
  const key = String(type || '').trim()
  const remembered = key ? skuPrefixByProductType.value[key] : null
  productSkuPrefix.value = normalizePrefix(remembered, 'PRD-')
}

loadPrefixMemory()

function openCreateProduct() {
  productEditing.value = null
  productForm.value = emptyProductForm()
  applySkuPrefixForType(productForm.value.product_type)
  productDialogError.value = ''
  accessoriesExpanded.value = !isPhone.value
  customFieldsExpanded.value = !isPhone.value
  newAccessoryProductId.value = null
  newAccessoryQty.value = 1
  newAccessoryRequired.value = false
  componentsExpanded.value = !isPhone.value
  newComponentProductId.value = null
  newComponentQty.value = 1
  createEmptyProductFieldRows()
  generateProductSku()
}

async function generateProductSku(force = false) {
  if (!force && productForm.value.sku) {
    return
  }
  generatingProductSku.value = true
  try {
    rememberSkuPrefixForType(
      productForm.value.product_type,
      productSkuPrefix.value
    )
    const sku = await store.generateProductSku(productSkuPrefix.value)
    if (sku) {
      productForm.value.sku = sku
    }
  } finally {
    generatingProductSku.value = false
  }
}

function openEditProduct(product) {
  const brand = product.brand ?? ''
  const manufacturer = product.manufacturer ?? ''
  productEditing.value = product
  productForm.value = {
    sku: product.sku ?? '',
    name: product.name ?? '',
    category_id: product.category_id ?? null,
    supplier_name: product.supplier_name ?? '',
    brand,
    manufacturer,
    brand_url: brand ? (brandLinks.value[brand] || '') : '',
    manufacturer_url: manufacturer ? (manufacturerLinks.value[manufacturer] || '') : '',
    product_type: product.product_type ?? 'equipment',
    accessories: Array.isArray(product.accessories)
      ? product.accessories.map(item => ({
          accessory_product_id: item.accessory_product_id,
          quantity: Number(item.quantity || 1),
          required: !!item.required,
        }))
      : [],
    components: Array.isArray(product.components)
      ? product.components.map(item => ({
          component_product_id: item.component_product_id,
          quantity: Number(item.quantity || 1),
        }))
      : [],
    weight_kg: product.weight_kg ?? null,
    height_cm: product.height_cm ?? null,
    width_cm: product.width_cm ?? null,
    depth_cm: product.depth_cm ?? null,
    maintenance_interval_days: product.maintenance_interval_days ?? null,
    power_consumption_watts: product.power_consumption_watts ?? null,
    daily_rate: product.daily_rate ?? 0,
    replace_cost: product.replace_cost ?? 0,
  }
  applySkuPrefixForType(productForm.value.product_type)
  productDialogError.value = ''
  accessoriesExpanded.value = !isPhone.value
  customFieldsExpanded.value = !isPhone.value
  newAccessoryProductId.value = null
  newAccessoryQty.value = 1
  newAccessoryRequired.value = false
  componentsExpanded.value = !isPhone.value
  newComponentProductId.value = null
  newComponentQty.value = 1
  loadProductFieldRows(product.id)
}

function normalizeOptionalUrl(value) {
  const url = String(value || '').trim()
  return url || null
}

async function persistInlineProductDefaults() {
  const nextBrandOptions = [...settingsStore.brandOptions]
  const nextManufacturerOptions = [...settingsStore.manufacturerOptions]
  const nextBrandMap = { ...(settingsStore.brandManufacturerMap || {}) }
  const nextBrandLinks = { ...(settingsStore.brandLinks || {}) }
  const nextManufacturerLinks = { ...(settingsStore.manufacturerLinks || {}) }

  const brand = String(productForm.value.brand || '').trim()
  const manufacturer = String(productForm.value.manufacturer || '').trim()
  const brandUrl = normalizeOptionalUrl(productForm.value.brand_url)
  const manufacturerUrl = normalizeOptionalUrl(productForm.value.manufacturer_url)

  if (brand && !nextBrandOptions.includes(brand)) nextBrandOptions.push(brand)
  if (manufacturer && !nextManufacturerOptions.includes(manufacturer)) nextManufacturerOptions.push(manufacturer)

  if (brand && manufacturer) {
    nextBrandMap[brand] = manufacturer
  }

  if (brand && brandUrl) nextBrandLinks[brand] = brandUrl
  if (brand && !brandUrl && nextBrandLinks[brand]) delete nextBrandLinks[brand]

  if (manufacturer && manufacturerUrl) nextManufacturerLinks[manufacturer] = manufacturerUrl
  if (manufacturer && !manufacturerUrl && nextManufacturerLinks[manufacturer]) delete nextManufacturerLinks[manufacturer]

  await settingsStore.updateProductDefaults({
    brand_options: nextBrandOptions,
    manufacturer_options: nextManufacturerOptions,
    default_brand: settingsStore.defaultBrand,
    default_manufacturer: settingsStore.defaultManufacturer,
    brand_manufacturer_map: nextBrandMap,
    brand_links: nextBrandLinks,
    manufacturer_links: nextManufacturerLinks,
  })
}

function onBrandChanged(value) {
  const brand = String(value || '').trim()
  productForm.value.brand = brand
  productForm.value.brand_url = brand ? (brandLinks.value[brand] || '') : ''
  if (brand && brandManufacturerMap.value[brand]) {
    productForm.value.manufacturer = brandManufacturerMap.value[brand]
    onManufacturerChanged(brandManufacturerMap.value[brand])
  }
}

function onManufacturerChanged(value) {
  const manufacturer = String(value || '').trim()
  productForm.value.manufacturer = manufacturer
  productForm.value.manufacturer_url = manufacturer ? (manufacturerLinks.value[manufacturer] || '') : ''
}

function addBrandToStore(value) {
  if (!value || settingsStore.brandOptions.includes(value)) return
  settingsStore.brandOptions.push(value)
  settingsStore.brandOptions.sort((a, b) => a.localeCompare(b))
}

function addManufacturerToStore(value) {
  if (!value || settingsStore.manufacturerOptions.includes(value)) return
  settingsStore.manufacturerOptions.push(value)
  settingsStore.manufacturerOptions.sort((a, b) => a.localeCompare(b))
}

function onNewBrandValue(value, done) {
  const normalized = String(value || '').trim()
  addBrandToStore(normalized)
  done(normalized, 'add-unique')
  onBrandChanged(normalized)
}

function onNewManufacturerValue(value, done) {
  const normalized = String(value || '').trim()
  addManufacturerToStore(normalized)
  done(normalized, 'add-unique')
  onManufacturerChanged(normalized)
}

function getBrandLink(brand) {
  if (!brand) return ''
  return brandLinks.value[brand] || ''
}

function getManufacturerLink(manufacturer) {
  if (!manufacturer) return ''
  return manufacturerLinks.value[manufacturer] || ''
}

async function saveProduct() {
  const valid = await productFormRef.value?.validate()
  if (!valid) return

  saving.value = true
  productDialogError.value = ''
  try {
    await persistInlineProductDefaults()

    const payload = {
      sku: productForm.value.sku.trim(),
      name: productForm.value.name.trim(),
      category_id: productForm.value.category_id,
      supplier_name: productForm.value.supplier_name || null,
      brand: productForm.value.brand || null,
      manufacturer: productForm.value.manufacturer || null,
      product_type: productForm.value.product_type,
      weight_kg: productForm.value.weight_kg,
      height_cm: productForm.value.height_cm,
      width_cm: productForm.value.width_cm,
      depth_cm: productForm.value.depth_cm,
      maintenance_interval_days: productForm.value.maintenance_interval_days,
      power_consumption_watts: productForm.value.power_consumption_watts,
      daily_rate: Number(productForm.value.daily_rate || 0),
      replace_cost: Number(productForm.value.replace_cost || 0),
    }

    let savedProduct
    if (productEditing.value) {
      savedProduct = await store.updateProduct(productEditing.value.id, payload)
      await store.updateProductAccessories(productEditing.value.id, productForm.value.accessories || [])
      await store.updateProductComponents(productEditing.value.id, productForm.value.components || [])
      $q.notify({ type: 'positive', message: 'Product updated' })
    } else {
      savedProduct = await store.createProduct(payload)
      await store.updateProductAccessories(savedProduct.id, productForm.value.accessories || [])
      await store.updateProductComponents(savedProduct.id, productForm.value.components || [])
      $q.notify({ type: 'positive', message: 'Product created' })
    }

    if (savedProduct?.id) {
      await customFieldsStore.saveEntityValues('product', savedProduct.id, productFieldRows.value.map(row => ({
        field_definition_id: row.field_definition_id,
        value: row.value,
      })))
    }

    emit('update:modelValue', false)
    emit('saved')
  } catch (error) {
    productDialogError.value = error?.response?.data?.detail || 'Failed to save product'
  } finally {
    saving.value = false
  }
}

function closeProductDialog() {
  emit('update:modelValue', false)
}

watch(() => props.modelValue, async (open) => {
  if (open) {
    if (!customFieldsStore.definitions.length) {
      await customFieldsStore.fetchDefinitions('product')
    }
    if (props.product) {
      await openEditProduct(props.product)
    } else {
      openCreateProduct()
    }
  }
})
</script>
