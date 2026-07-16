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
                <div class="text-subtitle2">{{ item.product.sku }} · {{ item.product.name }}</div>
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
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'

import { useJobsStore } from '../stores/jobs'
import { useInventoryStore } from '../stores/inventory'
import { filterRequirementSourceProducts } from '../utils/job-requirements'
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
    localRows.value.push({ product_id: productId, quantity_required: qty, quantity_picked: 0, notes: null })
    syncRows()
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

const addedRequirementProducts = computed(() => (
  localRows.value
    .filter(row => Number(row.quantity_required || 0) > 0)
    .map(row => ({ row, product: productById.value.get(row.product_id) }))
    .filter(item => item.product)
    .sort((a, b) => compareProducts(a.product, b.product, requirementSort.value))
))

watch(() => props.modelValue, (open) => {
  if (open) {
    resetLocalRows()
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
