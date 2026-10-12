<template>
  <q-dialog
    :model-value="modelValue"
    @update:model-value="(v) => emit('update:modelValue', v)"
    persistent
  >
    <q-card style="width: 1400px; max-width: 98vw; min-height: 600px" class="ec-card">
      <q-card-section class="row items-center">
        <div class="text-h6">{{ title || t('purchasing.pickCatalog') }}</div>
        <q-space />
        <q-btn flat round dense icon="close" @click="emit('update:modelValue', false)" />
      </q-card-section>

      <q-card-section class="q-pt-none">
        <q-tabs v-model="tab" dense class="text-primary" align="left">
          <q-tab name="products" :label="t('purchasing.products')" />
          <q-tab name="vendor" :label="t('vendorCatalog.title')" />
        </q-tabs>
        <q-separator />

        <!-- Products tab: same search/filter UX as adding products to a job -->
        <div v-show="tab === 'products'" class="q-mt-sm">
          <div class="row q-gutter-sm q-mb-sm items-end wrap">
            <q-input
              v-model="search"
              :label="t('jobs.searchProducts')"
              outlined
              dense
              clearable
              style="min-width: 220px; flex: 1 1 220px"
            >
              <template #prepend><q-icon name="search" /></template>
            </q-input>
            <q-select
              v-model="brandFilter"
              :options="brandOptions"
              :label="t('vendorCatalog.brand')"
              outlined
              dense
              clearable
              use-input
              input-debounce="200"
              style="min-width: 160px; flex: 1 1 160px"
              @filter="filterBrand"
            />
            <q-select
              v-model="manufacturerFilter"
              :options="manufacturerOptions"
              :label="t('purchasing.manufacturer')"
              outlined
              dense
              clearable
              use-input
              input-debounce="200"
              style="min-width: 160px; flex: 1 1 160px"
              @filter="filterManufacturer"
            />
            <q-select
              v-model="categoryFilter"
              :options="categoryOptions"
              :label="t('vendorCatalog.category')"
              outlined
              dense
              clearable
              use-input
              input-debounce="200"
              style="min-width: 160px; flex: 1 1 160px"
              @filter="filterCategory"
            />
            <q-toggle v-model="excludeRental" :label="t('purchasing.excludeRental')" />
          </div>

          <q-table
            :rows="filteredProducts"
            :columns="productColumns"
            row-key="id"
            :loading="loadingProducts"
            flat
            bordered
            dense
            :rows-per-page-options="[25, 50, 100]"
            @row-click="(_e, row) => pickProduct(row)"
            class="catalog-picker__table cursor-pointer"
          >
            <template #no-data>
              <div class="q-pa-md text-grey">{{ t('inventory.noProducts') }}</div>
            </template>
          </q-table>
        </div>

        <!-- Vendor catalog tab: reuse the existing searchable/filterable table -->
        <div v-show="tab === 'vendor'" class="q-mt-sm">
          <VendorProductTable
            :vendor-id="vendorId"
            selectable
            @select="(vp) => emit('select', { type: 'vendor', data: vp })"
          />
        </div>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInventoryStore } from '../stores/inventory'
import VendorProductTable from './VendorProductTable.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  vendorId: { type: Number, default: null },
  title: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'select'])

const { t } = useI18n()
const inventoryStore = useInventoryStore()

const tab = ref('products')
const search = ref('')
const brandFilter = ref(null)
const manufacturerFilter = ref(null)
const categoryFilter = ref(null)
const excludeRental = ref(true)
const loadingProducts = ref(false)

const productColumns = computed(() => [
  { name: 'name', label: t('purchasing.name'), field: 'name', align: 'left', sortable: true },
  { name: 'sku', label: t('purchasing.sku'), field: 'sku', align: 'left', sortable: true },
  { name: 'brand', label: t('vendorCatalog.brand'), field: 'brand', align: 'left', sortable: true },
  { name: 'manufacturer', label: t('purchasing.manufacturer'), field: 'manufacturer', align: 'left', sortable: true },
  { name: 'category', label: t('vendorCatalog.category'), field: 'category', align: 'left', sortable: true },
])

const filteredProducts = computed(() => {
  const term = String(search.value || '').trim().toLowerCase()
  const brand = brandFilter.value || null
  const manuf = manufacturerFilter.value || null
  const cat = categoryFilter.value || null
  return (inventoryStore.products || []).filter((p) => {
    if (excludeRental.value && p.is_rental_product) return false
    if (brand && (p.brand || '') !== brand) return false
    if (manuf && (p.manufacturer || '') !== manuf) return false
    if (cat && (p.category || '') !== cat) return false
    if (term) {
      const hay = `${p.name || ''} ${p.sku || ''} ${p.brand || ''} ${p.manufacturer || ''}`.toLowerCase()
      if (!hay.includes(term)) return false
    }
    return true
  })
})

function distinct(field) {
  const set = new Set()
  for (const p of inventoryStore.products || []) {
    const v = p[field]
    if (v) set.add(v)
  }
  return Array.from(set).sort().map((v) => ({ label: v, value: v }))
}

const brandOptions = ref([])
const manufacturerOptions = ref([])
const categoryOptions = ref([])

function loadFacets() {
  brandOptions.value = distinct('brand')
  manufacturerOptions.value = distinct('manufacturer')
  categoryOptions.value = distinct('category')
}

function filterBrand(val, update) {
  const needle = String(val || '').toLowerCase()
  update(() => {
    brandOptions.value = distinct('brand').filter((o) => o.label.toLowerCase().includes(needle))
  })
}
function filterManufacturer(val, update) {
  const needle = String(val || '').toLowerCase()
  update(() => {
    manufacturerOptions.value = distinct('manufacturer').filter((o) => o.label.toLowerCase().includes(needle))
  })
}
function filterCategory(val, update) {
  const needle = String(val || '').toLowerCase()
  update(() => {
    categoryOptions.value = distinct('category').filter((o) => o.label.toLowerCase().includes(needle))
  })
}

function pickProduct(row) {
  emit('select', { type: 'product', data: row })
}

function ensureLoaded() {
  if (inventoryStore.products.length) {
    loadFacets()
    return
  }
  loadingProducts.value = true
  inventoryStore
    .fetchAll()
    .catch(() => {})
    .finally(() => {
      loadingProducts.value = false
      loadFacets()
    })
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) ensureLoaded()
  }
)

onMounted(() => {
  if (props.modelValue) ensureLoaded()
})
</script>

<style scoped>
.catalog-picker__table {
  max-width: 100%;
}
</style>
