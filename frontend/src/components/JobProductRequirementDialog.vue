<template>
  <q-dialog :model-value="modelValue" persistent :maximized="isPhone" @update:model-value="emit('update:modelValue', $event)">
    <q-card :style="isPhone ? 'width: 100vw; max-width: 100vw; height: 100vh' : 'min-width: 900px; max-width: 98vw; height: 90vh'" class="ec-card column">
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6">{{ t('jobs.addProductRequirements') }}</div>
        <q-space />
        <q-btn
          flat
          round
          dense
          icon="close"
          :aria-label="t('app.actions.close')"
          @click="emit('update:modelValue', false)"
        />
      </q-card-section>

      <q-card-section class="col overflow-auto q-pt-sm">
        <q-banner class="bg-blue-1 text-primary rounded-borders q-mb-md">
          <div class="text-subtitle2 q-mb-sm">{{ t('jobs.addedRequirements') }}</div>
          <div v-if="addedRequirementProducts.length" class="column q-gutter-sm">
            <q-card
              v-for="item in addedRequirementProducts"
              :key="`added-${item.product.id}`"
              flat
              bordered
              class="bg-white"
            >
              <q-card-section class="q-pb-xs">
                <div class="text-subtitle2">
                  {{ item.product.sku }} · {{ item.product.name }}
                  <q-badge v-if="item.row.is_scannable" color="positive" text-color="white" label="Scan" class="q-ml-xs" />
                  <q-badge v-else color="warning" text-color="white" label="Check" class="q-ml-xs" />
                </div>
                <div v-if="item.parentProduct" class="text-caption text-primary q-mb-xs">
                  <q-icon name="link" size="12px" />
                  {{ t('jobs.packWith') }} {{ item.parentProduct.sku }} · {{ item.parentProduct.name }}
                </div>
                <div class="text-caption text-grey-7">
                  {{ productCategoryPath(item.product) }} · {{ item.product.brand || t('jobs.noBrand') }}
                </div>
              </q-card-section>
              <q-card-section class="q-pt-none">
                <div class="row q-col-gutter-sm items-end">
                  <div class="col-12 col-md-auto">
                    <q-badge color="grey-8" text-color="white" :label="`${t('jobs.total')}: ${productTotalCount(item.product)}`" />
                  </div>
                  <div class="col-12 col-md-auto">
                    <q-badge color="info" text-color="white" :label="`${t('jobs.availableConfirmed')}: ${productAvailableConfirmedOnly(item.product)}`" />
                  </div>
                  <div class="col-12 col-md-auto">
                    <q-badge color="primary" text-color="white" :label="`${t('jobs.availableWithDrafts')}: ${productAvailableIncludingDrafts(item.product)}`" />
                  </div>
                  <div class="col-12 col-md-2">
                    <q-input
                      :model-value="item.row.quantity_required"
                      type="number"
                      min="0"
                      :label="t('jobs.requiredQty')"
                      outlined
                      dense
                      @update:model-value="value => setProductRequirementQty(item.product.id, value)"
                    />
                  </div>
                  <div class="col-12 col-md-auto">
                    <q-btn
                      flat
                      dense
                      no-caps
                      color="negative"
                      icon="delete"
                      :label="t('scan.clear')"
                      @click="removeRequirementRow(item.product.id)"
                    />
                  </div>
                </div>
              </q-card-section>
            </q-card>
          </div>
          <div v-else class="text-caption text-grey-7">{{ t('jobs.noRequirements') }}</div>
        </q-banner>

        <div class="row q-col-gutter-sm q-mb-sm">
          <div class="col-12 col-md-3">
            <q-input
              v-model="requirementProductSearch"
              :label="t('jobs.searchProducts')"
              outlined
              dense
              clearable
            >
              <template #prepend>
                <q-icon name="search" />
              </template>
            </q-input>
          </div>
          <div class="col-12 col-md-2">
            <q-select
              v-model="requirementCategoryFilter"
              :options="requirementCategoryFilterOptions"
              :label="t('jobs.categoryFilter')"
              outlined
              dense
              clearable
              emit-value
              map-options
            />
          </div>
          <div class="col-12 col-md-2">
            <q-select
              v-model="requirementBrandFilter"
              :options="requirementBrandFilterOptions"
              :label="t('jobs.brandFilter')"
              outlined
              dense
              clearable
              emit-value
              map-options
            />
          </div>
          <div class="col-12 col-md-2">
            <q-select
              v-model="requirementManufacturerFilter"
              :options="requirementManufacturerFilterOptions"
              :label="t('jobs.manufacturerFilter')"
              outlined
              dense
              clearable
              emit-value
              map-options
            />
          </div>
          <div class="col-12 col-md-1">
            <q-select
              v-model="requirementTypeFilter"
              :options="requirementTypeFilterOptions"
              :label="t('jobs.typeFilter')"
              outlined
              dense
              clearable
              emit-value
              map-options
            />
          </div>
          <div class="col-12 col-md-2">
            <q-select
              v-model="requirementSort"
              :options="requirementSortOptions"
              :label="t('jobs.sort')"
              outlined
              dense
              emit-value
              map-options
            />
          </div>
        </div>

        <div class="text-caption text-grey-7 q-mb-sm">
          {{ t('jobs.requirementsHelp') }}
        </div>

        <q-list v-if="requirementCategoryGroups.length" bordered separator class="rounded-borders jobs-category-list">
          <q-expansion-item
            v-for="group in requirementCategoryGroups"
            :key="group.key"
            :label="`${group.label} (${group.subtreeCount})`"
            :default-opened="group.depth === 0"
            expand-separator
            dense
            :header-style="{ paddingLeft: `${Math.min(group.depth * 14, 56)}px` }"
          >
            <div class="q-pa-sm">
              <div v-if="!group.products.length" class="text-caption text-grey-6 q-mb-sm">
                {{ t('jobs.noProductsInCategory') }}
              </div>
              <q-card
                v-for="product in group.products"
                :key="product.id"
                flat
                bordered
                class="q-mb-sm"
              >
                <q-card-section class="q-pb-xs">
                  <div class="text-subtitle2">{{ product.sku }} · {{ product.name }}</div>
                  <div class="text-caption text-grey-7">
                    {{ product.brand || t('jobs.noBrand') }} · {{ product.manufacturer || t('jobs.noManufacturer') }} · {{ product.product_type || t('jobs.typeEquipment') }}
                    <q-badge v-if="productAccessoryScanCount(product)" color="positive" text-color="white" :label="`${productAccessoryScanCount(product)} scan`" class="q-ml-xs" />
                    <q-badge v-if="productInspectionCount(product)" color="warning" text-color="white" :label="`${productInspectionCount(product)} check`" class="q-ml-xs" />
                  </div>
                </q-card-section>

                <q-card-section class="q-pt-none">
                  <div class="row q-col-gutter-sm items-end">
                    <div class="col-6 col-md-3">
                      <q-badge color="grey-8" text-color="white" :label="`${t('jobs.total')}: ${productTotalCount(product)}`" />
                    </div>
                    <div class="col-6 col-md-3">
                      <q-badge color="info" text-color="white" :label="`${t('jobs.availableConfirmed')}: ${productAvailableConfirmedOnly(product)}`" />
                    </div>
                    <div class="col-6 col-md-3">
                      <q-badge color="primary" text-color="white" :label="`${t('jobs.availableWithDrafts')}: ${productAvailableIncludingDrafts(product)}`" />
                    </div>
                    <div class="col-6 col-md-auto">
                      <q-btn flat dense no-caps color="primary" icon="place" size="sm" :label="t('inventory.deviceDialog.locateOnMap')" @click.stop="openProductLocationMap(product)" />
                    </div>
                    <div class="col-12 col-md-2">
                      <q-input
                        :model-value="productRequirementQty(product.id)"
                        type="number"
                        min="0"
                        :label="t('jobs.requiredQty')"
                        outlined
                        dense
                        @update:model-value="value => setProductRequirementQty(product.id, value)"
                      />
                    </div>
                    <div class="col-12 col-md-1">
                      <q-btn
                        flat
                        dense
                        no-caps
                        color="negative"
                        icon="delete"
                        :label="t('scan.clear')"
                        @click="removeRequirementRow(product.id)"
                      />
                    </div>
                  </div>
                </q-card-section>
              </q-card>
            </div>
          </q-expansion-item>
        </q-list>
        <q-banner v-else class="bg-grey-2 text-grey-8 rounded-borders">
          {{ t('jobs.noRequirements') }}
        </q-banner>
      </q-card-section>

      <q-card-actions align="right" class="q-pa-md">
        <q-btn color="primary" unelevated :label="t('app.actions.done')" @click="emit('update:modelValue', false)" />
      </q-card-actions>
    </q-card>
  </q-dialog>

  <ProductLocationMapDialog
    v-model="productLocationMapOpen"
    :product="productLocationMapProduct"
  />

  <q-dialog v-model="optionalAccessoryDialogOpen" persistent>
    <q-card style="min-width: 400px; max-width: 95vw" class="ec-card">
      <q-card-section>
        <div class="text-h6">{{ t('jobs.optionalAccessories') }}</div>
        <div class="text-caption text-grey-7">
          {{ t('jobs.optionalAccessoriesHint', { product: optionalAccessoryProduct?.name || '' }) }}
        </div>
      </q-card-section>
      <q-card-section class="q-pt-none">
        <q-list bordered separator class="rounded-borders">
          <q-item v-for="item in optionalAccessorySelections" :key="`opt-${item.accessory_product_id}`" tag="label" clickable v-ripple>
            <q-item-section avatar>
              <q-checkbox v-model="item.selected" color="primary" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ item.name }}</q-item-label>
              <q-item-label caption>Qty {{ item.quantity }} · {{ item.is_scannable ? t('jobs.scannable') : t('jobs.inspection') }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="optionalAccessoryDialogOpen = false" />
        <q-btn color="primary" unelevated :label="t('app.actions.confirm')" @click="confirmOptionalAccessories" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'

import { useJobsStore } from '../stores/jobs'
import { useInventoryStore } from '../stores/inventory'
import { filterRequirementSourceProducts, isRentalProduct } from '../utils/job-requirements'
import ProductLocationMapDialog from './ProductLocationMapDialog.vue'

const props = defineProps({
  modelValue: Boolean,
  requirementRows: { type: Array, default: () => [] },
  products: { type: Array, default: () => [] },
  startDate: { type: String, default: null },
  endDate: { type: String, default: null },
  jobId: { type: Number, default: null },
  includeRentalProducts: Boolean,
})

const emit = defineEmits([
  'update:modelValue',
  'update:requirementRows',
])

const $q = useQuasar()
const { t } = useI18n()
const jobsStore = useJobsStore()
const inventoryStore = useInventoryStore()

const isPhone = computed(() => $q.screen.lt.md)
const localRows = ref([])
const requirementProductSearch = ref('')
const requirementCategoryFilter = ref(null)
const requirementBrandFilter = ref(null)
const requirementManufacturerFilter = ref(null)
const requirementTypeFilter = ref(null)
const requirementSort = ref('category_name')
const productLocationMapOpen = ref(false)
const productLocationMapProduct = ref(null)

function openProductLocationMap(product) {
  productLocationMapProduct.value = product
  productLocationMapOpen.value = true
}

const requirementSortOptions = computed(() => [
  { label: t('jobs.sortCategoryThenName'), value: 'category_name' },
  { label: t('jobs.sortName'), value: 'name' },
  { label: t('jobs.sortSku'), value: 'sku' },
  { label: t('jobs.sortInStoreFirst'), value: 'in_store' },
  { label: t('jobs.sortByLocation'), value: 'location' },
])

const requirementTypeFilterOptions = computed(() => [
  { label: t('jobs.typeEquipment'), value: 'equipment' },
  { label: t('jobs.typeAccessory'), value: 'accessory' },
  { label: t('jobs.typeConsumable'), value: 'consumable' },
  { label: t('jobs.typeCase'), value: 'case' },
])

function cloneRequirementRows(rows = []) {
  return rows.map(item => ({
    ...item,
    product_id: Number(item.product_id),
    quantity_required: Number(item.quantity_required || 0),
    quantity_picked: Number(item.quantity_picked || 0),
    is_scannable: item.is_scannable !== false,
    notes: item.notes || null,
  }))
}

function resetLocalRows() {
  localRows.value = cloneRequirementRows(props.requirementRows)
}

function syncRows() {
  emit('update:requirementRows', cloneRequirementRows(localRows.value))
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

const requirementSourceProducts = computed(() => {
  const source = props.products?.length ? props.products : (inventoryStore.products || [])
  return filterRequirementSourceProducts(source, { includeRentalProducts: props.includeRentalProducts })
})

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
  for (const category of inventoryStore.categories || []) map.set(category.id, category)
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

function productLocationPath(product) {
  const devices = (inventoryStore.devices || []).filter(d => d.product_id === product.id && d.location_zone_id)
  if (devices.length === 0) return ''
  const zoneIds = [...new Set(devices.map(d => d.location_zone_id))]
  const zones = (inventoryStore.zones || []).filter(z => zoneIds.includes(z.id))
  if (zones.length === 0) return ''
  const zonePaths = zones.map(zone => {
    const parts = []
    let current = zone
    while (current) {
      parts.unshift(current.code || current.name || '')
      current = (inventoryStore.zones || []).find(z => z.id === current.parent_id)
    }
    return parts.join('/')
  })
  return [...new Set(zonePaths)].sort()[0] || ''
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
  if (sortMode === 'location') {
    const locA = productLocationPath(a)
    const locB = productLocationPath(b)
    const locCompare = locA.localeCompare(locB)
    if (locCompare !== 0) return locCompare
    return nameA.localeCompare(nameB)
  }

  const categoryCompare = categoryA.localeCompare(categoryB)
  if (categoryCompare !== 0) return categoryCompare
  return nameA.localeCompare(nameB)
}

const requirementCategoryFilterOptions = computed(() => {
  const unique = Array.from(new Set(requirementSourceProducts.value.map(product => productCategoryPath(product))))
  return unique.sort((a, b) => a.localeCompare(b)).map(value => ({ label: value, value }))
})

const filteredRequirementProducts = computed(() => {
  const term = String(requirementProductSearch.value || '').trim().toLowerCase()
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

const requirementCategoryGroups = computed(() => {
  const byCategoryId = new Map()
  const uncategorized = []

  const types = {}
  for (const p of filteredRequirementProducts.value) {
    const t = p.product_type || 'unknown'
    types[t] = (types[t] || 0) + 1
  }
  console.log('[requirementCategoryGroups]', {
    filteredCount: filteredRequirementProducts.value.length,
    types,
    hasTree: Array.isArray(inventoryStore.categoryTree) && inventoryStore.categoryTree.length > 0,
  })

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
    const countDescendants = (node) => {
      const directProducts = (byCategoryId.get(node.id) || []).length
      const childCount = (node.children || []).reduce((sum, child) => sum + countDescendants(child), 0)
      return directProducts + childCount
    }

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

  console.log('[requirementCategoryGroups] groups:', groups.map(g => `${g.label} (${g.products.length} products)`))
  return groups
})

function reservedByProductForStatuses(statuses) {
  const startDate = normalizeDate(props.startDate)
  const endDate = normalizeDate(props.endDate)
  if (!startDate || !endDate) return new Map()

  const reservingStatuses = new Set(statuses)
  const jobsById = new Map((jobsStore.jobs || []).map(job => [job.id, job]))
  const reserved = new Map()

  for (const req of jobsStore.requirements || []) {
    const job = jobsById.get(req.job_id)
    if (!job) continue
    if (props.jobId && req.job_id === props.jobId) continue
    if (!reservingStatuses.has(String(job.status || '').toLowerCase())) continue

    const otherStart = normalizeDate(job.start_date)
    const otherEnd = normalizeDate(job.end_date)
    if (!otherStart || !otherEnd) continue
    if (endDate < otherStart || otherEnd < startDate) continue

    const qty = Math.max(Number(req.quantity_required || 0), Number(req.quantity_picked || 0))
    if (qty <= 0) continue
    reserved.set(req.product_id, Number(reserved.get(req.product_id) || 0) + qty)
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
  return Number(localRows.value.find(item => item.product_id === productId)?.quantity_required || 0)
}

function expandProductChildren(parentProductId, parentQty) {
  const product = productById.value.get(parentProductId)
  if (!product) return

  const accessories = product.accessories || []
  for (const acc of accessories) {
    if (!acc.required) continue
    const childProductId = acc.accessory_product_id
    const existing = localRows.value.find(r => r.product_id === childProductId)
    if (existing) {
      existing.quantity_required = Math.max(existing.quantity_required, acc.quantity * parentQty)
      existing.is_scannable = acc.is_scannable !== false
    } else {
      localRows.value.push({
        product_id: childProductId,
        quantity_required: acc.quantity * parentQty,
        quantity_picked: 0,
        is_scannable: acc.is_scannable !== false,
        notes: null,
      })
    }
  }

  const components = product.components || []
  for (const comp of components) {
    const childProductId = comp.component_product_id
    const existing = localRows.value.find(r => r.product_id === childProductId)
    if (existing) {
      existing.quantity_required = Math.max(existing.quantity_required, comp.quantity * parentQty)
      existing.is_scannable = !!comp.is_scannable
    } else {
      localRows.value.push({
        product_id: childProductId,
        quantity_required: comp.quantity * parentQty,
        quantity_picked: 0,
        is_scannable: !!comp.is_scannable,
        notes: null,
      })
    }
  }
}

const optionalAccessoryDialogOpen = ref(false)
const optionalAccessoryProduct = ref(null)
const optionalAccessoryQty = ref(1)
const optionalAccessorySelections = ref([])

function addOptionalAccessories(parentProductId, parentQty) {
  const product = productById.value.get(parentProductId)
  if (!product) return
  const optionals = (product.accessories || []).filter(a => !a.required)
  if (!optionals.length) return

  optionalAccessoryProduct.value = product
  optionalAccessoryQty.value = parentQty
  optionalAccessorySelections.value = optionals.map(acc => ({
    accessory_product_id: acc.accessory_product_id,
    name: productNameById(acc.accessory_product_id),
    quantity: acc.quantity,
    is_scannable: acc.is_scannable !== false,
    selected: false,
  }))
  optionalAccessoryDialogOpen.value = true
}

function confirmOptionalAccessories() {
  const parentQty = optionalAccessoryQty.value
  for (const item of optionalAccessorySelections.value) {
    if (!item.selected) continue
    const existing = localRows.value.find(r => r.product_id === item.accessory_product_id)
    if (existing) {
      existing.quantity_required = Math.max(existing.quantity_required, item.quantity * parentQty)
      existing.is_scannable = item.is_scannable
    } else {
      localRows.value.push({
        product_id: item.accessory_product_id,
        quantity_required: item.quantity * parentQty,
        quantity_picked: 0,
        is_scannable: item.is_scannable,
        notes: null,
      })
    }
  }
  optionalAccessoryDialogOpen.value = false
  syncRows()
}

function productNameById(productId) {
  const item = productById.value.get(productId)
  if (!item) return `Product #${productId}`
  return `${item.sku} - ${item.name}`
}

function productAccessoryScanCount(product) {
  const accessories = product?.accessories || []
  return accessories.filter(a => a.required && a.is_scannable !== false).length
}

function productInspectionCount(product) {
  const accessories = product?.accessories || []
  const components = product?.components || []
  const accInspection = accessories.filter(a => a.required && a.is_scannable === false).length
  const compInspection = components.filter(c => !c.is_scannable).length
  return accInspection + compInspection
}

function setProductRequirementQty(productId, value) {
  const qty = Math.max(0, Number(value || 0))
  const row = localRows.value.find(item => item.product_id === productId)
  if (row) {
    row.quantity_required = qty
    if (qty === 0) {
      removeRequirementRow(productId)
      return
    }
    syncRows()
    return
  }
  if (qty > 0) {
    localRows.value.push({ product_id: productId, quantity_required: qty, quantity_picked: 0, is_scannable: true, notes: null })
    expandProductChildren(productId, qty)
    syncRows()
    addOptionalAccessories(productId, qty)
  }
}

function removeRequirementRow(productId) {
  const row = localRows.value.find(item => item.product_id === productId)
  if (!row) return
  
  // Preserve rows with any picked quantity by setting quantity_required to 0
  if ((row.quantity_picked ?? 0) > 0) {
    row.quantity_required = 0
  } else {
    localRows.value = localRows.value.filter(item => item.product_id !== productId)
  }
  syncRows()
}

function productTotalCount(product) {
  return Number(product?.total_devices || 0)
}

function productAvailableByMap(product, reservedMap) {
  if (!product) return 0
  if (isRentalProduct(product) && product.external_source === 'eventory') {
    return Number(product.eventory_available_qty || 0)
  }
  const startDate = normalizeDate(props.startDate)
  const endDate = normalizeDate(props.endDate)
  if (!startDate || !endDate) {
    return Number(availableNowCountsByProduct.value.get(product.id) || 0)
  }
  const total = Number(operationalDeviceCountsByProduct.value.get(product.id) || 0)
  const reserved = Number(reservedMap.get(product.id) || 0)
  return Math.max(total - reserved, 0)
}

function productAvailableConfirmedOnly(product) {
  return productAvailableByMap(product, overlappingReservedConfirmedOnlyByProduct.value)
}

function productAvailableIncludingDrafts(product) {
  return productAvailableByMap(product, overlappingReservedIncludingDraftsByProduct.value)
}

const productById = computed(() => {
  const map = new Map()
  for (const product of requirementSourceProducts.value) map.set(product.id, product)
  return map
})

const parentByChildId = computed(() => {
  const map = new Map()
  for (const product of requirementSourceProducts.value) {
    for (const acc of product.accessories || []) {
      if (!acc.required) continue
      map.set(acc.accessory_product_id, product.id)
    }
    for (const comp of product.components || []) {
      map.set(comp.component_product_id, product.id)
    }
  }
  return map
})

const addedRequirementProducts = computed(() => {
  const addedIds = new Set(
    localRows.value
      .filter(row => Number(row.quantity_required || 0) > 0)
      .map(row => row.product_id)
  )
  return localRows.value
    .filter(row => Number(row.quantity_required || 0) > 0)
    .map(row => {
      const product = productById.value.get(row.product_id)
      const parentId = parentByChildId.value.get(row.product_id)
      const parentProduct = parentId && addedIds.has(parentId) ? productById.value.get(parentId) : null
      return { row, product, parentProduct }
    })
    .filter(item => item.product)
    .sort((a, b) => {
      const aParentId = parentByChildId.value.get(a.row.product_id) || 0
      const bParentId = parentByChildId.value.get(b.row.product_id) || 0
      if (aParentId !== bParentId) return aParentId - bParentId
      return compareProducts(a.product, b.product, requirementSort.value)
    })
})

function resetFilters() {
  requirementProductSearch.value = ''
  requirementCategoryFilter.value = null
  requirementBrandFilter.value = null
  requirementManufacturerFilter.value = null
  requirementTypeFilter.value = null
  requirementSort.value = 'category_name'
}

watch(() => props.modelValue, (open) => {
  if (open) {
    resetFilters()
    resetLocalRows()
    if (!inventoryStore.products?.length) {
      inventoryStore.fetchAll()
    }
  }
})

watch(() => props.jobId, (jobId, previousJobId) => {
  if (props.modelValue && jobId !== previousJobId) {
    resetLocalRows()
  }
})
</script>

<style scoped>
.jobs-category-list {
  background: var(--jobs-category-bg, #ffffff);
}
</style>
