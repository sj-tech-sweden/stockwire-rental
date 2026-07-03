<template>
  <q-dialog :model-value="modelValue" persistent :maximized="isPhone" @update:model-value="emit('update:modelValue', $event)">
    <q-card :style="isPhone ? 'width: 100vw; max-width: 100vw; height: 100vh' : 'min-width: 760px; max-width: 95vw'" class="ec-card">
      <q-card-section>
        <div class="text-h6">{{ editing ? t('jobs.editJob') : t('jobs.newJob') }}</div>
      </q-card-section>

      <q-card-section class="q-pt-none">
        <q-banner v-if="editing?.id" class="bg-blue-1 text-primary rounded-borders q-mb-md">
          <div class="row q-col-gutter-sm items-center">
            <div class="col-12 col-md">
              <div class="text-subtitle2">{{ editing?.job_code }}</div>
              <div class="text-caption">
                {{ editing?.customer_name || t('jobs.unassigned') }} · {{ editing?.venue_name || t('jobs.unassigned') }} · {{ editing?.start_date || '-' }} → {{ editing?.end_date || '-' }}
              </div>
            </div>
            <div class="col-12 col-md-auto">
              <div class="row q-gutter-xs">
                <q-btn
                  flat
                  dense
                  no-caps
                  color="primary"
                  icon="shopping_cart_checkout"
                  :label="t('scan.scanOutJob')"
                  :to="scanJobLink('job_out')"
                />
                <q-btn
                  flat
                  dense
                  no-caps
                  color="primary"
                  icon="assignment_return"
                  :label="t('scan.scanInJob')"
                  :to="scanJobLink('job_in')"
                />
              </div>
            </div>
          </div>
        </q-banner>
        <q-form ref="formRef" @submit.prevent="saveJob">
          <div class="row q-col-gutter-sm">
            <div class="col-12 col-md-6">
              <q-input
                v-model="form.job_code"
                :label="t('jobs.jobCode')"
                outlined
                dense
                :rules="[v => !!v || t('login.required')]"
              >
                <template #append>
                  <q-btn
                    flat
                    dense
                    no-caps
                    color="primary"
                    icon="autorenew"
                    :label="t('jobs.generate')"
                    :loading="generatingJobCode"
                    @click="generateJobCode"
                  />
                </template>
              </q-input>
            </div>
            <div class="col-12 col-md-6">
              <q-select
                v-model="form.status"
                :options="statusOptions"
                :label="t('jobs.status')"
                outlined
                dense
                emit-value
                map-options
                :rules="[v => !!v || t('login.required')]"
              />
            </div>
          </div>

          <q-input
            v-model="form.description"
            :label="t('jobs.description')"
            type="textarea"
            autogrow
            outlined
            dense
            class="q-mt-sm"
          />

          <div class="row q-col-gutter-sm q-mt-sm">
            <div class="col-12 col-md-6">
              <q-select
                v-model="form.customer_id"
                :options="filteredCustomerOptions"
                :label="t('jobs.customer')"
                outlined
                dense
                clearable
                use-input
                fill-input
                input-debounce="0"
                emit-value
                map-options
                @filter="filterCustomerOptions"
              />
            </div>
            <div class="col-12 col-md-6">
              <q-select
                v-model="form.venue_id"
                :options="filteredVenueOptions"
                :label="t('jobs.venue')"
                outlined
                dense
                clearable
                use-input
                fill-input
                input-debounce="0"
                emit-value
                map-options
                @filter="filterVenueOptions"
              />
            </div>
          </div>

          <div v-if="selectedVenueMapEmbedUrl" class="q-mt-sm">
            <q-responsive :ratio="16 / 9" class="rounded-borders" style="overflow: hidden; border: 1px solid #d6dbe2;">
              <iframe
                :src="selectedVenueMapEmbedUrl"
                :title="t('jobs.venueMapPreview')"
                loading="lazy"
                referrerpolicy="no-referrer-when-downgrade"
                style="border: 0; width: 100%; height: 100%;"
              />
            </q-responsive>
            <q-btn
              flat
              dense
              no-caps
              color="primary"
              icon="open_in_new"
              class="q-mt-xs"
              :label="t('jobs.openVenueMap')"
              :href="selectedVenueMapLink"
              target="_blank"
              rel="noopener noreferrer"
            />
          </div>

          <div class="row q-col-gutter-sm q-mt-sm">
            <div class="col-12 col-md-6">
              <q-select
                v-model="form.project_id"
                :options="projectOptions"
                :label="t('jobs.project')"
                outlined
                dense
                clearable
                emit-value
                map-options
              />
            </div>
            <div class="col-12 col-md-6">
              <q-input
                v-model="form.location_in_venue"
                :label="t('jobs.locationInVenue')"
                outlined
                dense
                clearable
              />
            </div>
          </div>

          <div class="row q-col-gutter-sm q-mt-sm">
            <div class="col-12 col-md-6">
              <q-input v-model="form.start_date" :label="t('jobs.startDate')" type="date" outlined dense />
            </div>
            <div class="col-12 col-md-6">
              <q-input v-model="form.end_date" :label="t('jobs.endDate')" type="date" outlined dense />
            </div>
          </div>

          <div class="row q-col-gutter-sm q-mt-sm">
            <div class="col-12 col-md-4">
              <q-input
                v-model.number="form.sales_price"
                :label="t('jobs.salesPrice')"
                :suffix="activeCurrencyCode"
                :hint="currencyHelperText"
                type="number"
                step="0.01"
                min="0"
                outlined
                dense
              />
            </div>
            <div class="col-12 col-md-4 flex items-center">
              <q-toggle v-model="form.invoice_paid" :label="t('jobs.invoicePaid')" />
            </div>
            <div class="col-12 col-md-4">
              <q-input
                v-model="form.invoice_paid_at"
                :label="t('jobs.invoicePaidAt')"
                type="date"
                outlined
                dense
                :disable="!form.invoice_paid"
              />
            </div>
          </div>

          <q-banner class="bg-blue-1 text-primary rounded-borders q-mt-sm" dense>
            {{ t('jobs.projectedPriceFromRequirements') }}: <strong>{{ formatMoney(projectedJobPrice) }}</strong>
            <span v-if="Number(form.sales_price || 0) > 0" class="q-ml-sm">
              {{ t('jobs.salesTarget') }}: <strong>{{ formatMoney(form.sales_price) }}</strong>
            </span>
          </q-banner>

          <q-input
            v-model="form.notes"
            :label="t('jobs.notes')"
            type="textarea"
            autogrow
            outlined
            dense
            class="q-mt-sm"
          />

          <q-expansion-item class="q-mt-md" icon="fact_check" :label="t('jobs.customFieldValues')" dense>
            <div class="q-pt-sm">
              <div v-if="jobFieldRows.length">
                <div v-for="field in jobFieldRows" :key="field.field_definition_id" class="q-mb-sm">
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
              <div v-else class="text-caption text-grey-7">
                {{ t('jobs.noJobCustomFields') }}
              </div>
            </div>
          </q-expansion-item>

          <CustomerCreateInline class="q-mt-md" @created="onCustomerCreated" />
          <VenueCreateInline class="q-mt-md" @created="onVenueCreated" />

          <q-expansion-item class="q-mt-md" icon="inventory_2" :label="t('jobs.requiredProductsAndQuantities')" dense>
            <div class="q-pt-sm">
              <div class="row items-center justify-between q-mb-sm">
                <div class="text-caption text-grey-7">
                  {{ requirementRows.length ? t('jobs.addedRequirements') : t('jobs.noRequirements') }}
                </div>
                <q-btn unelevated color="primary" icon="add" :label="t('jobs.manageRequirements')" no-caps size="sm" @click="requirementDialogOpen = true" />
              </div>
              <q-list v-if="requirementRows.length" bordered separator dense class="rounded-borders q-mb-sm">
                <q-item v-for="row in requirementRows" :key="row.product_id" dense>
                  <q-item-section>
                    <q-item-label>{{ requirementProductName(row.product_id) }}</q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <div class="row items-center q-gutter-xs">
                      <q-input
                        :model-value="row.quantity_required"
                        type="number"
                        min="0"
                        dense
                        outlined
                        style="width: 80px"
                        @update:model-value="value => setProductRequirementQty(row.product_id, value)"
                      />
                      <q-btn flat round dense icon="delete" color="negative" size="sm" @click="removeRequirementRow(row.product_id)" />
                    </div>
                  </q-item-section>
                </q-item>
              </q-list>
            </div>
          </q-expansion-item>

          <q-expansion-item class="q-mt-md" icon="sell" :label="t('jobs.rentalRequirements')" dense>
            <div class="q-pt-sm">
              <div class="row q-col-gutter-sm q-mb-sm">
                <div class="col-12 col-md-6">
                  <q-input
                    v-model="rentalRequirementSearch"
                    :label="t('jobs.searchRentals')"
                    outlined
                    dense
                    clearable
                  >
                    <template #prepend>
                      <q-icon name="search" />
                    </template>
                  </q-input>
                </div>
              </div>

              <div class="text-caption text-grey-7 q-mb-sm">{{ t('jobs.rentalRequirementsHelp') }}</div>

              <q-banner
                v-if="rentalRequirementOverbookedCount > 0"
                class="bg-negative text-white rounded-borders q-mb-sm"
                dense
              >
                {{ t('jobs.rentalOverbookedBanner', { count: rentalRequirementOverbookedCount, suffix: rentalRequirementOverbookedCount === 1 ? '' : 's' }) }}
              </q-banner>

              <q-list bordered separator class="rounded-borders jobs-category-list">
                <q-item v-for="product in filteredRentalRequirementProducts" :key="`rental-${product.id}`">
                  <q-item-section>
                    <q-item-label class="text-subtitle2">{{ product.sku }} · {{ product.name }}</q-item-label>
                    <q-item-label caption>
                      {{ product.supplier_name || t('jobs.noSupplier') }} · {{ product.category || t('jobs.uncategorized') }}
                    </q-item-label>
                    <div class="row q-gutter-xs q-mt-xs">
                      <q-badge color="grey-8" text-color="white" :label="`${t('jobs.total')}: ${productTotalCount(product)}`" />
                      <q-badge color="primary" text-color="white" :label="`${t('jobs.availableWithDrafts')}: ${productAvailableIncludingDrafts(product)}`" />
                      <q-badge
                        v-if="isRentalRequirementOverbooked(product)"
                        color="negative"
                        text-color="white"
                        :label="`${t('jobs.overBy')} ${rentalRequirementOverbookedBy(product)}`"
                      />
                    </div>
                  </q-item-section>
                  <q-item-section side top>
                    <q-input
                      :model-value="productRequirementQty(product.id)"
                      type="number"
                      min="0"
                      :label="t('jobs.requiredQty')"
                      outlined
                      dense
                      style="width: 120px"
                      @update:model-value="value => setProductRequirementQty(product.id, value)"
                    />
                  </q-item-section>
                </q-item>
                <q-item v-if="!filteredRentalRequirementProducts.length">
                  <q-item-section class="text-caption text-grey-6">{{ t('jobs.noRentalProductsFound') }}</q-item-section>
                </q-item>
              </q-list>
            </div>
          </q-expansion-item>

          <EntityAttachmentsPanel
            entity-type="job"
            :entity-id="editing?.id || null"
            :title="t('jobs.jobDocuments')"
            default-category="job-document"
          />

          <q-banner v-if="dialogError" class="bg-negative text-white q-mt-sm rounded-borders" dense>
            {{ dialogError }}
          </q-banner>
        </q-form>
      </q-card-section>

      <q-card-actions :align="isPhone ? 'stretch' : 'right'" :class="isPhone ? 'q-pa-md bg-grey-2' : ''">
        <q-btn flat :class="isPhone ? 'full-width q-mb-sm' : ''" :label="t('app.actions.cancel')" @click="closeJobDialog" />
        <q-btn color="primary" unelevated :class="isPhone ? 'full-width' : ''" :label="editing ? t('app.actions.save') : t('jobs.create')" :loading="saving" @click="saveJob" />
      </q-card-actions>
    </q-card>

    <JobProductRequirementDialog
      v-model="requirementDialogOpen"
      v-model:requirementRows="requirementRows"
      :products="inventoryStore.products"
      :start-date="form.start_date"
      :end-date="form.end_date"
      :job-id="editing?.id || null"
    />
  </q-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'

import { JOB_STATUSES, useJobsStore } from '../stores/jobs'
import { useCustomersStore } from '../stores/customers'
import { useVenuesStore } from '../stores/venues'
import { useInventoryStore } from '../stores/inventory'
import { useCustomFieldsStore } from '../stores/customFields'
import { useAuthStore } from '../stores/auth'
import { useSettingsStore } from '../stores/settings'
import { useProjectsStore } from '../stores/projects'
import EntityAttachmentsPanel from './EntityAttachmentsPanel.vue'
import CustomerCreateInline from './CustomerCreateInline.vue'
import VenueCreateInline from './VenueCreateInline.vue'
import JobProductRequirementDialog from './JobProductRequirementDialog.vue'
import { translateMaybePrefillCustomFieldLabel, translateMaybePrefillCustomFieldOption } from '../i18n/prefillContent'
import { normalizeCurrencyCode } from '../constants/currencies'
import { googleMapsEmbedUrl, googleMapsSearchUrl, locationQueryFromParts } from '../utils/maps'
import { buildScanJobLink } from '../utils/scan-workflow'

const props = defineProps({
  modelValue: Boolean,
  job: { type: Object, default: null },
  customers: { type: Array, default: () => [] },
  venues: { type: Array, default: () => [] },
  products: { type: Array, default: () => [] },
  initialValues: { type: Object, default: null },
})

const emit = defineEmits([
  'update:modelValue',
  'saved',
])

const $q = useQuasar()
const { t, locale } = useI18n()
const jobsStore = useJobsStore()
const customersStore = useCustomersStore()
const venuesStore = useVenuesStore()
const inventoryStore = useInventoryStore()
const customFieldsStore = useCustomFieldsStore()
const authStore = useAuthStore()
const settingsStore = useSettingsStore()
const projectsStore = useProjectsStore()

const isPhone = computed(() => $q.screen.lt.md)
const activeCurrencyCode = computed(() => normalizeCurrencyCode(settingsStore.companyProfile?.currency, 'SEK'))
const currencyHelperText = computed(() => `${t('settings.company.currencyIso')}: ${activeCurrencyCode.value}`)

const editing = ref(null)
const saving = ref(false)
const generatingJobCode = ref(false)
const dialogError = ref('')
const formRef = ref(null)
const requirementDialogOpen = ref(false)

function scanJobLink(action) {
  return buildScanJobLink(action, editing.value)
}

function customFieldLabel(label) {
  return translateMaybePrefillCustomFieldLabel(label, t)
}

function customFieldOption(option) {
  return translateMaybePrefillCustomFieldOption(option, t)
}

const statusOptions = computed(() => JOB_STATUSES.map(status => ({ label: statusLabel(status.value), value: status.value })))

const customerOptions = computed(() => customersStore.customers.map(customer => ({
  label: customer.email ? `${customer.name} · ${customer.email}` : customer.name,
  value: customer.id,
})))

const venueOptions = computed(() => venuesStore.venues.map(venue => ({
  label: [venue.name, venue.city].filter(Boolean).join(' · '),
  value: venue.id,
})))

const projectOptions = computed(() => projectsStore.projects.map(p => ({
  label: p.name,
  value: p.id,
})))

const filteredCustomerOptions = ref([])
const filteredVenueOptions = ref([])
const filteredProductOptions = ref([])
const requirementProductSearch = ref('')
const rentalRequirementSearch = ref('')
const requirementCategoryFilter = ref(null)
const requirementBrandFilter = ref(null)
const requirementManufacturerFilter = ref(null)
const requirementTypeFilter = ref(null)
const requirementSort = ref('category_name')
const jobFieldRows = ref([])

const booleanValueOptions = computed(() => [
  { label: t('common.true'), value: 'true' },
  { label: t('common.false'), value: 'false' },
])

const requirementSortOptions = computed(() => [
  { label: t('jobs.sortCategoryThenName'), value: 'category_name' },
  { label: t('jobs.sortName'), value: 'name' },
  { label: t('jobs.sortSku'), value: 'sku' },
  { label: t('jobs.sortInStoreFirst'), value: 'in_store' },
])

const requirementTypeFilterOptions = computed(() => [
  { label: t('jobs.typeEquipment'), value: 'equipment' },
  { label: t('jobs.typeAccessory'), value: 'accessory' },
  { label: t('jobs.typeConsumable'), value: 'consumable' },
  { label: t('jobs.typeCase'), value: 'case' },
])

function isRentalProduct(product) {
  return Boolean(product?.is_rental_product) || String(product?.product_type || '') === 'rental'
}

const requirementSourceProducts = computed(() =>
  (inventoryStore.products || []).filter(product => !isRentalProduct(product))
)

const rentalRequirementProducts = computed(() =>
  (inventoryStore.products || []).filter(product => isRentalProduct(product))
)

const requirementBrandFilterOptions = computed(() => {
  const unique = Array.from(new Set(requirementSourceProducts.value.map(product => String(product.brand || '').trim()).filter(Boolean)))
  return unique.sort((a, b) => a.localeCompare(b)).map(value => ({ label: value, value }))
})

const requirementManufacturerFilterOptions = computed(() => {
  const unique = Array.from(new Set(requirementSourceProducts.value.map(product => String(product.manufacturer || '').trim()).filter(Boolean)))
  return unique.sort((a, b) => a.localeCompare(b)).map(value => ({ label: value, value }))
})

const categoryById = computed(() => {
  const map = new Map()
  for (const category of inventoryStore.categories) map.set(category.id, category)
  return map
})

function productCategoryPath(product) {
  if (!product) return t('jobs.uncategorized')
  const categoryId = Number(product.category_id || 0)
  if (categoryId > 0 && categoryById.value.size) {
    const names = []
    let current = categoryById.value.get(categoryId)
    let guard = 0
    while (current && guard < 20) {
      names.unshift(current.name)
      current = current.parent_id ? categoryById.value.get(current.parent_id) : null
      guard += 1
    }
    if (names.length) return names.join(' / ')
  }
  return product.category || t('jobs.uncategorized')
}

function compareProducts(a, b, sortMode) {
  const categoryA = productCategoryPath(a)
  const categoryB = productCategoryPath(b)
  const nameA = String(a.name || '').toLowerCase()
  const nameB = String(b.name || '').toLowerCase()
  const skuA = String(a.sku || '').toLowerCase()
  const skuB = String(b.sku || '').toLowerCase()

  if (sortMode === 'name') return nameA.localeCompare(nameB)
  if (sortMode === 'sku') return skuA.localeCompare(skuB)
  if (sortMode === 'in_store') {
    const inStoreDiff = Number(b.in_store_devices || 0) - Number(a.in_store_devices || 0)
    if (inStoreDiff !== 0) return inStoreDiff
    return nameA.localeCompare(nameB)
  }

  const categoryCompare = categoryA.localeCompare(categoryB)
  if (categoryCompare !== 0) return categoryCompare
  return nameA.localeCompare(nameB)
}

const productOptions = computed(() => {
  const term = requirementProductSearch.value.trim().toLowerCase()
  const categoryFilter = requirementCategoryFilter.value
  const brandFilter = requirementBrandFilter.value
  const manufacturerFilter = requirementManufacturerFilter.value
  const typeFilter = requirementTypeFilter.value

  const filtered = requirementSourceProducts.value.filter(product => {
    if (categoryFilter && productCategoryPath(product) !== categoryFilter) return false
    if (brandFilter && String(product.brand || '').trim() !== brandFilter) return false
    if (manufacturerFilter && String(product.manufacturer || '').trim() !== manufacturerFilter) return false
    if (typeFilter && product.product_type !== typeFilter) return false
    if (!term) return true
    return [
      product.sku,
      product.name,
      product.brand,
      product.manufacturer,
      productCategoryPath(product),
      product.product_type,
    ]
      .filter(Boolean)
      .some(value => String(value).toLowerCase().includes(term))
  })

  const sorted = [...filtered].sort((a, b) => compareProducts(a, b, requirementSort.value))
  return sorted.map(product => ({
    label: `${productCategoryPath(product)} · ${product.sku} · ${product.name}`,
    value: product.id,
  }))
})

const requirementCategoryFilterOptions = computed(() => {
  const unique = Array.from(new Set(requirementSourceProducts.value.map(product => productCategoryPath(product))))
  return unique.sort((a, b) => a.localeCompare(b)).map(value => ({ label: value, value }))
})

watch(customerOptions, (options) => {
  filteredCustomerOptions.value = options
}, { immediate: true })

watch(venueOptions, (options) => {
  filteredVenueOptions.value = options
}, { immediate: true })

watch(productOptions, (options) => {
  filteredProductOptions.value = options
}, { immediate: true })

function filterCustomerOptions(val, update) {
  update(() => {
    const needle = val.trim().toLowerCase()
    if (!needle) {
      filteredCustomerOptions.value = customerOptions.value
      return
    }
    filteredCustomerOptions.value = customerOptions.value.filter(option =>
      option.label.toLowerCase().includes(needle)
    )
  })
}

function filterVenueOptions(val, update) {
  update(() => {
    const needle = val.trim().toLowerCase()
    if (!needle) {
      filteredVenueOptions.value = venueOptions.value
      return
    }
    filteredVenueOptions.value = venueOptions.value.filter(option =>
      option.label.toLowerCase().includes(needle)
    )
  })
}

function statusLabel(value) {
  const normalized = String(value || '').toLowerCase()
  const mapping = {
    draft: t('jobs.statusDraft'),
    confirmed: t('jobs.statusConfirmed'),
    in_progress: t('jobs.statusInProgress'),
    completed: t('jobs.statusCompleted'),
    cancelled: t('jobs.statusCancelled'),
  }
  return mapping[normalized] || value
}

function normalizeDate(value) {
  if (!value) return null
  if (typeof value === 'string') {
    const match = value.match(/^(\d{4}-\d{2}-\d{2})/)
    return match ? match[1] : null
  }
  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    const year = value.getFullYear()
    const month = String(value.getMonth() + 1).padStart(2, '0')
    const day = String(value.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }
  return null
}

function dateSortKey(value) {
  const normalized = normalizeDate(value)
  return normalized ? Number(normalized.replaceAll('-', '')) : null
}

function formatMoney(value) {
  const amount = Number(value || 0)
  const currentCurrency = normalizeCurrencyCode(settingsStore.companyProfile?.currency, 'SEK')
  try {
    return new Intl.NumberFormat('sv-SE', {
      style: 'currency',
      currency: currentCurrency,
      maximumFractionDigits: 2,
    }).format(amount)
  } catch {
    return new Intl.NumberFormat('sv-SE', {
      style: 'currency',
      currency: 'SEK',
      maximumFractionDigits: 2,
    }).format(amount)
  }
}

const emptyForm = () => ({
  job_code: '',
  description: '',
  project_id: null,
  location_in_venue: '',
  customer_id: null,
  customer_name: '',
  venue_id: null,
  venue_name: '',
  status: 'draft',
  start_date: null,
  end_date: null,
  sales_price: null,
  invoice_paid: false,
  invoice_paid_at: null,
  notes: '',
})

const form = ref(emptyForm())
const requirementRows = ref([])
const requirementDraft = ref({ product_id: null, quantity_required: 1 })

const filteredRequirementProducts = computed(() => {
  const term = requirementProductSearch.value.trim().toLowerCase()
  const categoryFilter = requirementCategoryFilter.value
  const brandFilter = requirementBrandFilter.value
  const manufacturerFilter = requirementManufacturerFilter.value
  const typeFilter = requirementTypeFilter.value

  const filtered = requirementSourceProducts.value.filter((product) => {
    if (categoryFilter && productCategoryPath(product) !== categoryFilter) return false
    if (brandFilter && String(product.brand || '').trim() !== brandFilter) return false
    if (manufacturerFilter && String(product.manufacturer || '').trim() !== manufacturerFilter) return false
    if (typeFilter && product.product_type !== typeFilter) return false
    if (!term) return true
    return [
      product.sku,
      product.name,
      product.brand,
      product.manufacturer,
      productCategoryPath(product),
      product.product_type,
    ]
      .filter(Boolean)
      .some(value => String(value).toLowerCase().includes(term))
  })

  return [...filtered].sort((a, b) => compareProducts(a, b, requirementSort.value))
})

const filteredRentalRequirementProducts = computed(() => {
  const term = rentalRequirementSearch.value.trim().toLowerCase()
  const filtered = rentalRequirementProducts.value.filter((product) => {
    if (!term) return true
    return [
      product.sku,
      product.name,
      product.category,
      product.supplier_name,
      product.external_reference,
    ]
      .filter(Boolean)
      .some(value => String(value).toLowerCase().includes(term))
  })
  return [...filtered].sort((a, b) => compareProducts(a, b, 'name'))
})

const rentalRequirementOverbookedCount = computed(() => (
  rentalRequirementProducts.value.filter(product => isRentalRequirementOverbooked(product)).length
))

const requirementCategoryGroups = computed(() => {
  const byCategoryId = new Map()
  const uncategorized = []

  for (const product of filteredRequirementProducts.value) {
    const categoryId = Number(product.category_id || 0)
    if (!categoryId) {
      uncategorized.push(product)
      continue
    }
    if (!byCategoryId.has(categoryId)) byCategoryId.set(categoryId, [])
    byCategoryId.get(categoryId).push(product)
  }

  for (const products of byCategoryId.values()) {
    products.sort((a, b) => compareProducts(a, b, requirementSort.value))
  }
  uncategorized.sort((a, b) => compareProducts(a, b, requirementSort.value))

  const groups = []

  const hasCategoryTree = Array.isArray(inventoryStore.categoryTree) && inventoryStore.categoryTree.length > 0
  if (hasCategoryTree) {
    const traverse = (nodes, depth = 0, pathPrefix = '') => {
      for (const node of nodes || []) {
        const nodeName = String(node?.name || '').trim() || t('jobs.uncategorized')
        const labelPath = pathPrefix ? `${pathPrefix} / ${nodeName}` : nodeName
        const directProducts = byCategoryId.get(node.id) || []

        let descendantCount = directProducts.length
        for (const child of node.children || []) {
          descendantCount += countDescendants(child)
        }

        if (descendantCount > 0) {
          groups.push({
            key: `cat-${node.id}`,
            label: labelPath,
            depth,
            products: directProducts,
            subtreeCount: descendantCount,
          })
        }

        traverse(node.children || [], depth + 1, labelPath)
      }
    }

    const countDescendants = (node) => {
      const directProducts = (byCategoryId.get(node.id) || []).length
      const childCount = (node.children || []).reduce((sum, child) => sum + countDescendants(child), 0)
      return directProducts + childCount
    }

    traverse(inventoryStore.categoryTree)
  } else {
    const fallbackGrouped = new Map()
    for (const product of filteredRequirementProducts.value) {
      const key = productCategoryPath(product)
      if (!fallbackGrouped.has(key)) fallbackGrouped.set(key, [])
      fallbackGrouped.get(key).push(product)
    }
    for (const [label, products] of [...fallbackGrouped.entries()].sort((a, b) => a[0].localeCompare(b[0]))) {
      groups.push({ key: label, label, depth: 0, products, subtreeCount: products.length })
    }
  }

  if (uncategorized.length) {
    groups.push({
      key: 'cat-uncategorized',
      label: t('jobs.uncategorized'),
      depth: 0,
      products: uncategorized,
      subtreeCount: uncategorized.length,
    })
  }

  return groups
})

function reservedByProductForStatuses(statuses) {
  const startDate = normalizeDate(form.value.start_date)
  const endDate = normalizeDate(form.value.end_date)
  if (!startDate || !endDate) return new Map()

  const reservingStatuses = new Set(statuses)
  const jobsById = new Map(jobsStore.jobs.map(job => [job.id, job]))
  const reserved = new Map()

  for (const req of jobsStore.requirements) {
    const job = jobsById.get(req.job_id)
    if (!job) continue
    if (editing.value && req.job_id === editing.value.id) continue
    if (!reservingStatuses.has(String(job.status || '').toLowerCase())) continue

    const otherStart = normalizeDate(job.start_date)
    const otherEnd = normalizeDate(job.end_date)
    if (!otherStart || !otherEnd) continue
    if (endDate < otherStart || otherEnd < startDate) continue

    const productId = req.product_id
    const qty = Math.max(Number(req.quantity_required || 0), Number(req.quantity_picked || 0))
    if (qty <= 0) continue
    reserved.set(productId, Number(reserved.get(productId) || 0) + qty)
  }

  return reserved
}

const overlappingReservedConfirmedOnlyByProduct = computed(() => (
  reservedByProductForStatuses(['confirmed', 'in_progress'])
))

const overlappingReservedIncludingDraftsByProduct = computed(() => (
  reservedByProductForStatuses(['draft', 'confirmed', 'in_progress'])
))

const operationalDeviceCountsByProduct = computed(() => {
  const now = new Date()
  const counts = new Map()

  for (const device of inventoryStore.devices || []) {
    const status = String(device.status || '').toLowerCase()
    const condition = String(device.condition || '').toLowerCase()
    const retired = device.retire_date ? new Date(device.retire_date) <= now : false
    if (retired) continue
    if (status === 'maintenance') continue
    if (condition === 'damaged') continue
    counts.set(device.product_id, Number(counts.get(device.product_id) || 0) + 1)
  }

  return counts
})

const availableNowCountsByProduct = computed(() => {
  const now = new Date()
  const counts = new Map()

  for (const device of inventoryStore.devices || []) {
    const status = String(device.status || '').toLowerCase()
    const condition = String(device.condition || '').toLowerCase()
    const retired = device.retire_date ? new Date(device.retire_date) <= now : false
    if (retired) continue
    if (condition === 'damaged') continue
    if (status !== 'available') continue
    counts.set(device.product_id, Number(counts.get(device.product_id) || 0) + 1)
  }

  return counts
})

function productRequirementQty(productId) {
  return Number(requirementRows.value.find(item => item.product_id === productId)?.quantity_required || 0)
}

function requirementProductName(productId) {
  const product = inventoryStore.products.find(p => p.id === productId)
  return product ? (product.sku ? `${product.sku} · ${product.name}` : product.name) : `#${productId}`
}

function setProductRequirementQty(productId, value) {
  const qty = Math.max(0, Number(value || 0))
  const row = requirementRows.value.find(item => item.product_id === productId)
  if (row) {
    row.quantity_required = qty
    if (qty === 0) removeRequirementRow(productId)
    return
  }
  if (qty > 0) {
    requirementRows.value.push({ product_id: productId, quantity_required: qty, quantity_picked: 0, notes: null })
  }
}

function productTotalCount(product) {
  return Number(product?.total_devices || 0)
}

function productEventoryAvailableQty(product) {
  return Math.max(0, Number(product?.eventory_available_qty || 0))
}

function eventoryPacklistsForProduct(product) {
  if (!Array.isArray(product?.eventory_packlists)) return []
  return product.eventory_packlists.filter(item => item && typeof item === 'object')
}

function eventoryPacklistReservesDate(packlist, startDate, endDate) {
  const status = String(packlist?.job_status || '').toLowerCase()
  if (status && ['cancelled', 'canceled', 'completed', 'returned'].includes(status)) return false

  const packStart = normalizeDate(packlist?.start_date)
  const packEnd = normalizeDate(packlist?.end_date)

  if (!startDate || !endDate) {
    const source = String(packlist?.source || '').toLowerCase()
    const outQty = Math.max(0, Number(packlist?.out || 0))
    return source === 'active' && outQty > 0
  }

  if (!packStart || !packEnd) return false
  return !(endDate < packStart || packEnd < startDate)
}

function eventoryReservedQtyForProduct(product, startDate, endDate) {
  let reserved = 0
  for (const packlist of eventoryPacklistsForProduct(product)) {
    if (!eventoryPacklistReservesDate(packlist, startDate, endDate)) continue
    const quantity = Math.max(Number(packlist?.quantity || 0), Number(packlist?.out || 0), 0)
    reserved += quantity
  }
  return reserved
}

function rentalAvailableByMap(product, reservedMap) {
  const startDate = normalizeDate(form.value.start_date)
  const endDate = normalizeDate(form.value.end_date)
  const base = productEventoryAvailableQty(product)
  const externalReserved = eventoryReservedQtyForProduct(product, startDate, endDate)
  const internalReserved = Number(reservedMap.get(product?.id) || 0)
  return Math.max(base - externalReserved - internalReserved, 0)
}

function rentalRequirementOverbookedBy(product) {
  const required = Math.max(0, Number(productRequirementQty(product?.id) || 0))
  const available = rentalAvailableByMap(product, overlappingReservedIncludingDraftsByProduct.value)
  return Math.max(required - available, 0)
}

function isRentalRequirementOverbooked(product) {
  return rentalRequirementOverbookedBy(product) > 0
}

function productAvailableByMap(product, reservedMap) {
  if (!product) return 0
  const startDate = normalizeDate(form.value.start_date)
  const endDate = normalizeDate(form.value.end_date)
  if (!startDate || !endDate) {
    return Number(availableNowCountsByProduct.value.get(product.id) || 0)
  }
  const total = Number(operationalDeviceCountsByProduct.value.get(product.id) || 0)
  const reserved = Number(reservedMap.get(product.id) || 0)
  return Math.max(total - reserved, 0)
}

function productAvailableConfirmedOnly(product) {
  if (String(product?.product_type || '').toLowerCase() === 'rental' || product?.is_rental_product) {
    return rentalAvailableByMap(product, overlappingReservedConfirmedOnlyByProduct.value)
  }
  return productAvailableByMap(product, overlappingReservedConfirmedOnlyByProduct.value)
}

function productAvailableIncludingDrafts(product) {
  if (String(product?.product_type || '').toLowerCase() === 'rental' || product?.is_rental_product) {
    return rentalAvailableByMap(product, overlappingReservedIncludingDraftsByProduct.value)
  }
  return productAvailableByMap(product, overlappingReservedIncludingDraftsByProduct.value)
}

function removeRequirementRow(productId) {
  requirementRows.value = requirementRows.value.filter(item => item.product_id !== productId)
}

const projectedJobPrice = computed(() => {
  const productsById = new Map((inventoryStore.products || []).map(product => [product.id, product]))
  const startKey = dateSortKey(form.value.start_date)
  const endKey = dateSortKey(form.value.end_date)
  const rentalDays = startKey && endKey && endKey >= startKey
    ? Math.max(1, Math.floor((new Date(form.value.end_date).getTime() - new Date(form.value.start_date).getTime()) / 86400000) + 1)
    : 1

  let total = 0
  for (const row of requirementRows.value) {
    const product = productsById.get(row.product_id)
    if (!product) continue
    const qty = Math.max(0, Number(row.quantity_required || 0))
    const unit = Number(product.rental_price || product.daily_rate || 0)
    total += qty * unit * rentalDays
  }
  return Number(total.toFixed(2))
})

const selectedVenueLocationQuery = computed(() => {
  if (form.value.venue_id) {
    const venue = venuesStore.venues.find(item => item.id === form.value.venue_id)
    return locationQueryFromParts(venue || {})
  }
  return ''
})

const selectedVenueMapLink = computed(() => googleMapsSearchUrl(selectedVenueLocationQuery.value))
const selectedVenueMapEmbedUrl = computed(() => googleMapsEmbedUrl(selectedVenueLocationQuery.value))

watch(
  () => form.value.invoice_paid,
  (paid) => {
    if (paid && !form.value.invoice_paid_at) {
      form.value.invoice_paid_at = normalizeDate(new Date())
    }
    if (!paid) {
      form.value.invoice_paid_at = null
    }
  }
)

watch(
  () => form.value.start_date,
  (startDate) => {
    const normalizedStart = normalizeDate(startDate)
    if (!normalizedStart) return

    if (form.value.start_date !== normalizedStart) {
      form.value.start_date = normalizedStart
    }

    const normalizedEnd = normalizeDate(form.value.end_date)
    if (!normalizedEnd || dateSortKey(normalizedEnd) < dateSortKey(normalizedStart)) {
      form.value.end_date = normalizedStart
      return
    }

    if (form.value.end_date !== normalizedEnd) {
      form.value.end_date = normalizedEnd
    }
  }
)

function createEmptyJobFieldRows() {
  const defs = (customFieldsStore.definitions || []).filter(def => def.entity_type === 'job' && def.is_active !== false)
  return defs.map(def => ({
    field_definition_id: def.id,
    label: def.label,
    value_type: def.value_type,
    options: def.options || [],
    value: null,
  }))
}

async function loadJobFieldRows(entityId) {
  if (!entityId) {
    jobFieldRows.value = createEmptyJobFieldRows()
    return
  }
  try {
    const data = await customFieldsStore.fetchEntityValues('job', entityId)
    jobFieldRows.value = Array.isArray(data?.values) ? data.values.map(value => ({ ...value })) : createEmptyJobFieldRows()
  } catch {
    jobFieldRows.value = createEmptyJobFieldRows()
  }
}

async function generateJobCode() {
  generatingJobCode.value = true
  try {
    const code = await jobsStore.generateJobCode('JOB-')
    if (code) form.value.job_code = code
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('jobs.failedGenerateJobCode') })
  } finally {
    generatingJobCode.value = false
  }
}

function openCreate() {
  editing.value = null
  form.value = emptyForm()
  requirementRows.value = []
  requirementDraft.value = { product_id: null, quantity_required: 1 }
  requirementProductSearch.value = ''
  rentalRequirementSearch.value = ''
  requirementCategoryFilter.value = null
  requirementBrandFilter.value = null
  requirementManufacturerFilter.value = null
  requirementTypeFilter.value = null
  requirementSort.value = 'category_name'
  loadJobFieldRows(null)
  dialogError.value = ''
  generateJobCode()
}

function openEdit(job) {
  editing.value = job
  form.value = {
    job_code: job.job_code ?? '',
    description: job.description ?? '',
    project_id: job.project_id ?? null,
    location_in_venue: job.location_in_venue ?? '',
    customer_id: job.customer_id ?? null,
    customer_name: job.customer_name ?? '',
    venue_id: job.venue_id ?? null,
    venue_name: job.venue_name ?? '',
    status: job.status ?? 'draft',
    start_date: normalizeDate(job.start_date),
    end_date: normalizeDate(job.end_date),
    sales_price: job.sales_price == null ? null : Number(job.sales_price),
    invoice_paid: Boolean(job.invoice_paid),
    invoice_paid_at: normalizeDate(job.invoice_paid_at),
    notes: job.notes ?? '',
  }
  requirementRows.value = jobsStore.requirements
    .filter(req => req.job_id === job.id)
    .map(req => ({
      product_id: req.product_id,
      quantity_required: req.quantity_required,
      quantity_picked: req.quantity_picked,
      notes: req.notes || null,
    }))
  requirementDraft.value = { product_id: null, quantity_required: 1 }
  requirementProductSearch.value = ''
  rentalRequirementSearch.value = ''
  requirementCategoryFilter.value = null
  requirementBrandFilter.value = null
  requirementManufacturerFilter.value = null
  requirementTypeFilter.value = null
  requirementSort.value = 'category_name'
  loadJobFieldRows(job.id)
  dialogError.value = ''
}

function customerNameForId(id) {
  return customersStore.customers.find(customer => customer.id === id)?.name ?? ''
}

function venueNameForId(id) {
  return venuesStore.venues.find(venue => venue.id === id)?.name ?? ''
}

function onCustomerCreated(customer) {
  form.value.customer_id = customer.id
  form.value.customer_name = customer.name
}

function onVenueCreated(venue) {
  form.value.venue_id = venue.id
  form.value.venue_name = venue.name
}

async function saveJob() {
  const valid = await formRef.value?.validate()
  if (!valid) return

  dialogError.value = ''
  saving.value = true
  try {
    if (!form.value.customer_id && !form.value.customer_name?.trim()) {
      dialogError.value = t('jobs.selectOrCreateCustomer')
      return
    }
    if (!form.value.venue_id && !form.value.venue_name?.trim()) {
      dialogError.value = t('jobs.selectOrCreateVenue')
      return
    }

    const payload = {
      ...form.value,
      customer_name: form.value.customer_name || customerNameForId(form.value.customer_id),
      venue_name: form.value.venue_name || venueNameForId(form.value.venue_id),
      start_date: normalizeDate(form.value.start_date),
      end_date: normalizeDate(form.value.end_date),
      sales_price: form.value.sales_price == null || form.value.sales_price === '' ? null : Number(form.value.sales_price),
      invoice_paid: Boolean(form.value.invoice_paid),
      invoice_paid_at: form.value.invoice_paid ? normalizeDate(form.value.invoice_paid_at) : null,
    }

    let savedJob
    if (editing.value) {
      savedJob = await jobsStore.updateJob(editing.value.id, payload)
    } else {
      savedJob = await jobsStore.createJob(payload)
    }

    await jobsStore.bulkUpsertRequirements(savedJob.id, requirementRows.value.map(item => ({
      product_id: item.product_id,
      quantity_required: Number(item.quantity_required || 0),
      quantity_picked: Number(item.quantity_picked || 0),
      notes: item.notes || null,
    })))

    await customFieldsStore.saveEntityValues('job', savedJob.id, jobFieldRows.value.map(row => ({
      field_definition_id: row.field_definition_id,
      value: row.value,
    })))

    emit('update:modelValue', false)
    $q.notify({ type: 'positive', message: editing.value ? t('jobs.jobUpdated') : t('jobs.jobCreated') })
    emit('saved')
  } catch (error) {
    dialogError.value = error?.response?.data?.detail || t('common.errorOccurred')
  } finally {
    saving.value = false
  }
}

function closeJobDialog() {
  emit('update:modelValue', false)
}

watch(() => props.modelValue, async (open) => {
  if (open) {
    if (!projectsStore.projects.length) {
      projectsStore.fetchAll()
    }
    if (props.job) {
      openEdit(props.job)
    } else {
      openCreate()
      if (props.initialValues) {
        Object.assign(form.value, props.initialValues)
      }
    }
  }
})
</script>

<style scoped>
.jobs-category-list {
  background: var(--jobs-category-bg, #ffffff);
}

:global(body.body--dark) {
  --jobs-category-bg: #161b22;
}

:global(body.body--light) {
  --jobs-category-bg: #ffffff;
}
</style>
