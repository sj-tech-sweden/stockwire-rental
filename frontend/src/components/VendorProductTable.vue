<template>
  <div class="vendor-product-table">
    <!-- Filters (hidden when showing a single product or explicitly hidden) -->
    <div v-if="!hideFilters && !props.productId" class="row q-gutter-sm q-mb-sm items-end wrap">
      <q-input
        v-model="filters.search"
        :label="t('vendorCatalog.search')"
        outlined
        dense
        clearable
        style="min-width: 200px; flex: 1 1 200px"
        @update:model-value="onFilterChange"
      />
      <q-select
        v-if="!props.vendorId"
        v-model="filters.vendor_id"
        :options="vendorOptions"
        :label="t('vendorCatalog.vendor')"
        outlined
        dense
        emit-value
        map-options
        clearable
        style="min-width: 180px; flex: 1 1 180px"
        @update:model-value="onFilterChange"
      />
      <q-select
        v-model="filters.category"
        :options="categoryOptions"
        :label="t('vendorCatalog.category')"
        outlined
        dense
        emit-value
        map-options
        clearable
        use-input
        input-debounce="200"
        style="min-width: 170px; flex: 1 1 170px"
        @filter="filterCategory"
        @update:model-value="onFilterChange"
      />
      <q-select
        v-model="filters.brand"
        :options="brandOptions"
        :label="t('vendorCatalog.brand')"
        outlined
        dense
        emit-value
        map-options
        clearable
        use-input
        input-debounce="200"
        style="min-width: 170px; flex: 1 1 170px"
        @filter="filterBrand"
        @update:model-value="onFilterChange"
      />
      <q-toggle v-model="filters.active_only" :label="t('vendorCatalog.active')" @update:model-value="onFilterChange" />
    </div>

    <q-table
      :rows="rows"
      :columns="columns"
      row-key="id"
      :loading="loading"
      v-model:pagination="pagination"
      v-model:visible-columns="visibleColumns"
      @request="onRequest"
      @row-click="onRowClick"
      flat
      bordered
      dense
      class="vendor-product-table__table"
    >
      <template #top-right>
        <q-btn-dropdown
          outline
          dense
          icon="view_column"
          :label="t('vendorCatalog.columns')"
          menu-anchor="bottom-end"
          menu-self="top-end"
        >
          <q-list dense>
            <q-item
              v-for="col in columns.filter((c) => c.name !== 'info')"
              :key="col.name"
              tag="label"
            >
              <q-item-section avatar>
                <q-checkbox v-model="visibleColumns" :val="col.name" />
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ col.label }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-btn-dropdown>
      </template>

      <template #body-cell-vendorItemNumber="props">
        <q-td :props="props">{{ props.value || '' }}</q-td>
      </template>
      <template #body-cell-supplierItemNumber="props">
        <q-td :props="props">{{ props.value || '' }}</q-td>
      </template>
      <template #body-cell-vendor="props">
        <q-td :props="props">{{ vendorName(props.value) }}</q-td>
      </template>
      <template #body-cell-is_active="props">
        <q-td :props="props">
          <q-icon :name="props.value ? 'check_circle' : 'cancel'" :color="props.value ? 'positive' : 'grey'" />
        </q-td>
      </template>
      <template #body-cell-image="props">
        <q-td :props="props" class="text-center">
          <q-img
            v-if="props.value"
            :src="props.value"
            spinner-color="primary"
            style="width: 48px; height: 48px; object-fit: contain"
            fit="contain"
          />
        </q-td>
      </template>
      <template #body-cell-weight="props">
        <q-td :props="props" class="text-right">{{ formatWeight(props.value) }}</q-td>
      </template>
      <template #body-cell-country_of_origin="props">
        <q-td :props="props">{{ formatCountry(props.value) }}</q-td>
      </template>
      <template #body-cell-expected_delivery_date="props">
        <q-td :props="props">{{ formatDate(props.value) }}</q-td>
      </template>
      <template #body-cell-productUrl="props">
        <q-td :props="props" class="text-center">
          <a
            v-if="props.value"
            :href="props.value"
            target="_blank"
            rel="noopener"
            class="text-primary"
            :title="t('vendorCatalog.viewOnWebshop')"
          >
            <q-icon name="open_in_new" size="sm" />
          </a>
        </q-td>
      </template>
      <template #body-cell-incoming_deliveries="props">
        <q-td :props="props">
          <div v-if="props.value && props.value.length" class="q-gutter-y-xs">
            <div v-for="(d, i) in props.value" :key="i" class="row no-wrap items-center q-gutter-x-xs">
              <span class="text-caption">{{ formatDate(d.expected_delivery_date) }}</span>
              <span class="text-caption text-grey-7">·</span>
              <span class="text-caption">{{ d.incoming_quantity }} {{ t('vendorCatalog.incoming').toLowerCase() }}</span>
            </div>
          </div>
        </q-td>
      </template>
      <template #body-cell-info="cell">
        <q-td :props="cell" class="text-center">
          <q-btn
            v-if="!props.productId"
            flat
            round
            dense
            icon="info"
            color="primary"
            @click.stop="openInfo(cell.row)"
          />
        </q-td>
      </template>
      <template #body-cell-select="cell">
        <q-td :props="cell" class="text-right">
          <q-btn
            v-if="isSelectable"
            size="sm"
            color="primary"
            unelevated
            :label="t('app.actions.add')"
            @click.stop="emit('select', cell.row)"
          />
        </q-td>
      </template>

      <template #no-data>
        <div class="q-pa-md text-grey">{{ t('vendorCatalog.noProducts') }}</div>
      </template>
    </q-table>

    <!-- Per-row detail popup (catalog mode). Shows the full product detail,
         including every advertised upcoming delivery and a webshop link. -->
    <q-dialog v-model="infoDialog" full-width>
      <q-card style="max-width: 640px">
        <q-card-section class="row items-center">
          <div class="text-h6">{{ infoRow?.name || infoRow?.sku }}</div>
          <q-space />
          <q-btn flat round dense icon="close" @click="infoDialog = false" />
        </q-card-section>
        <q-card-section v-if="infoRow" class="q-gutter-md">
          <div class="row q-gutter-md">
            <q-img
              v-if="infoRow.image_url"
              :src="infoRow.image_url"
              spinner-color="primary"
              style="width: 120px; height: 120px; object-fit: contain"
              fit="contain"
            />
            <div class="col">
              <div><strong>{{ t('vendorCatalog.sku') }}:</strong> {{ infoRow.sku }}</div>
              <div><strong>{{ t('vendorCatalog.vendorItemNumber') }}:</strong> {{ infoRow.vendor_item_number || '—' }}</div>
              <div><strong>{{ t('vendorCatalog.supplierItemNumber') }}:</strong> {{ infoRow.supplier_item_number || '—' }}</div>
              <div><strong>{{ t('vendorCatalog.brand') }}:</strong> {{ infoRow.brand || '—' }}</div>
              <div><strong>{{ t('vendorCatalog.category') }}:</strong> {{ infoRow.category || '—' }}</div>
              <div><strong>{{ t('vendorCatalog.vendor') }}:</strong> {{ vendorName(infoRow.vendor_id) }}</div>
            </div>
          </div>

          <q-separator />

          <div class="row q-gutter-x-lg q-gutter-y-xs">
            <div><strong>{{ t('vendorCatalog.weight') }}:</strong> {{ formatWeight(infoRow.weight) }}</div>
            <div><strong>{{ t('vendorCatalog.piecesPerCarton') }}:</strong> {{ infoRow.pieces_per_carton || '—' }}</div>
            <div><strong>{{ t('vendorCatalog.intrastat') }}:</strong> {{ infoRow.intrastat_code || '—' }}</div>
            <div><strong>{{ t('vendorCatalog.countryOfOrigin') }}:</strong> {{ formatCountry(infoRow.country_of_origin) }}</div>
          </div>
          <div class="row q-gutter-x-lg q-gutter-y-xs">
            <div><strong>{{ t('vendorCatalog.incoming') }}:</strong> {{ infoRow.incoming_quantity ?? '—' }}</div>
            <div><strong>{{ t('vendorCatalog.expectedDelivery') }}:</strong> {{ formatDate(infoRow.expected_delivery_date) }}</div>
          </div>

          <q-separator />

          <div>
            <div class="text-subtitle2 q-mb-xs">{{ t('vendorCatalog.upcomingDeliveries') }}</div>
            <template v-if="infoRow.incoming_deliveries && infoRow.incoming_deliveries.length">
              <div
                v-for="(d, i) in infoRow.incoming_deliveries"
                :key="i"
                class="row items-center q-gutter-x-sm"
              >
                <span>{{ formatDate(d.expected_delivery_date) }}</span>
                <span class="text-grey-7">·</span>
                <span>{{ d.incoming_quantity }} {{ t('vendorCatalog.incoming').toLowerCase() }}</span>
              </div>
            </template>
            <div v-else class="text-grey-7">{{ t('vendorCatalog.noProducts') }}</div>
          </div>

          <q-btn
            v-if="infoRow.product_url"
            type="a"
            :href="infoRow.product_url"
            target="_blank"
            rel="noopener"
            color="primary"
            outline
            icon="open_in_new"
            :label="t('vendorCatalog.viewOnWebshop')"
            class="q-mt-sm"
          />
        </q-card-section>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../boot/axios'
import { useCompaniesStore } from '../stores/companies'

const props = defineProps({
  vendorId: { type: Number, default: null },
  productId: { type: Number, default: null },
  hideFilters: { type: Boolean, default: false },
  // When true, clicking a row (or its "select" button) emits `select` with the
  // row — used inside the "add item" picker dialog.
  selectable: { type: Boolean, default: false },
})

const emit = defineEmits(['select'])

const { t, locale } = useI18n()
const companiesStore = useCompaniesStore()

function onRowClick(evt, row) {
  if (props.selectable) emit('select', row)
}

const isSelectable = computed(() => props.selectable)

const rows = ref([])
const loading = ref(false)

const filters = reactive({
  search: '',
  vendor_id: null,
  category: null,
  brand: null,
  active_only: false,
})
const allCategories = ref([])
const allBrands = ref([])
const categoryOptions = ref([])
const brandOptions = ref([])

const pagination = ref({
  page: 1,
  rowsPerPage: 25,
  rowsNumber: 0,
  sortBy: 'name',
  descending: false,
})

const infoDialog = ref(false)
const infoRow = ref(null)

const vendorOptions = computed(() =>
  companiesStore.companies.map((c) => ({ label: c.name, value: c.id }))
)

const vendorName = (id) => {
  if (!id) return t('vendorCatalog.noVendor')
  const c = companiesStore.companies.find((x) => x.id === id)
  return c ? c.name : `#${id}`
}

const formatWeight = (value) => {
  const n = Number(value)
  if (!Number.isFinite(n) || !n) return ''
  return `${n.toString().replace('.', ',')} kg`
}

const formatDate = (value) => {
  if (!value) return ''
  const d = new Date(value)
  if (isNaN(d.getTime())) return value
  return d.toLocaleDateString()
}

const formatCountry = (code) => {
  if (!code) return ''
  try {
    const name = new Intl.DisplayNames([locale.value || 'en'], { type: 'region' }).of(code)
    return name || code
  } catch {
    return code
  }
}

// Columns shown by default. Heavy/detail fields are hidden — they live in the
// info popup and the two optional columns below, all toggleable via "Columns".
const defaultVisibleColumns = [
  'sku', 'name', 'brand', 'category', 'unit_cost', 'currency',
  'stock_quantity', 'availability', 'vendor', 'source_plugin',
  'is_active', 'info',
]

// When used to show a single product (popup), surface the webshop link and the
// full upcoming-delivery list, drop the now-redundant info button, and reveal
// the heavier detail columns so the focused view is informative by default
// (still customizable via the Columns menu).
const detailDefaults = props.productId
  ? defaultVisibleColumns
      .filter((c) => c !== 'info')
      .concat([
        'image',
        'weight',
        'country_of_origin',
        'intrastat_code',
        'pieces_per_carton',
        'expected_delivery_date',
        'productUrl',
        'incoming_deliveries',
      ])
  : defaultVisibleColumns
const visibleColumns = ref(
  [...detailDefaults, ...(props.selectable ? ['select'] : [])],
)

const columns = [
  { name: 'sku', label: t('vendorCatalog.sku'), field: 'sku', align: 'left', sortable: true },
  { name: 'vendorItemNumber', label: t('vendorCatalog.vendorItemNumber'), field: 'vendor_item_number', align: 'left', sortable: true },
  { name: 'supplierItemNumber', label: t('vendorCatalog.supplierItemNumber'), field: 'supplier_item_number', align: 'left', sortable: true },
  { name: 'name', label: t('vendorCatalog.name'), field: 'name', align: 'left', sortable: true },
  { name: 'brand', label: t('vendorCatalog.brand'), field: 'brand', align: 'left', sortable: true },
  { name: 'category', label: t('vendorCatalog.category'), field: 'category', align: 'left', sortable: true },
  { name: 'image', label: t('vendorCatalog.image'), field: 'image_url', align: 'center' },
  { name: 'unit_cost', label: t('vendorCatalog.unitCost'), field: 'unit_cost', align: 'right', sortable: true },
  { name: 'currency', label: t('vendorCatalog.currency'), field: 'currency', align: 'left' },
  { name: 'stock_quantity', label: t('vendorCatalog.stock'), field: 'stock_quantity', align: 'right', sortable: true },
  { name: 'availability', label: t('vendorCatalog.availability'), field: 'availability', align: 'left' },
  { name: 'weight', label: t('vendorCatalog.weight'), field: 'weight', align: 'right', sortable: true },
  { name: 'country_of_origin', label: t('vendorCatalog.countryOfOrigin'), field: 'country_of_origin', align: 'left', sortable: true, format: (v) => formatCountry(v) },
  { name: 'intrastat_code', label: t('vendorCatalog.intrastat'), field: 'intrastat_code', align: 'left', sortable: true },
  { name: 'pieces_per_carton', label: t('vendorCatalog.piecesPerCarton'), field: 'pieces_per_carton', align: 'right', sortable: true },
  { name: 'incoming_quantity', label: t('vendorCatalog.incoming'), field: 'incoming_quantity', align: 'right', sortable: true },
  { name: 'expected_delivery_date', label: t('vendorCatalog.expectedDelivery'), field: 'expected_delivery_date', align: 'left', sortable: true, format: (v) => formatDate(v) },
  { name: 'productUrl', label: t('vendorCatalog.viewOnWebshop'), field: 'product_url', align: 'center' },
  { name: 'incoming_deliveries', label: t('vendorCatalog.upcomingStock'), field: 'incoming_deliveries', align: 'left' },
  { name: 'vendor', label: t('vendorCatalog.vendor'), field: 'vendor_id', align: 'left' },
  { name: 'source_plugin', label: t('vendorCatalog.source'), field: 'source_plugin', align: 'left' },
  { name: 'is_active', label: t('vendorCatalog.active'), field: 'is_active', align: 'center' },
  { name: 'info', label: '', field: 'id', align: 'center' },
  { name: 'select', label: '', field: 'select', align: 'right' },
]

async function loadFacets(q) {
  try {
    const { data } = await api.get('/api/v1/vendor-products/facets', { params: q ? { q } : {} })
    if (!q) {
      allCategories.value = data.categories || []
      allBrands.value = data.brands || []
    }
    categoryOptions.value = data.categories || []
    brandOptions.value = data.brands || []
  } catch {
    /* facets are optional */
  }
}

async function loadData() {
  loading.value = true
  try {
    const params = {
      limit: pagination.value.rowsPerPage,
      offset: (pagination.value.page - 1) * pagination.value.rowsPerPage,
      sort_by: pagination.value.sortBy || 'name',
      sort_dir: pagination.value.descending ? 'desc' : 'asc',
      active_only: filters.active_only,
    }
    if (filters.search) params.search = filters.search
    if (props.vendorId) params.vendor_id = props.vendorId
    else if (filters.vendor_id) params.vendor_id = filters.vendor_id
    if (filters.category) params.category = filters.category
    if (filters.brand) params.brand = filters.brand
    if (props.productId) params.ids = String(props.productId)
    const { data, headers } = await api.get('/api/v1/vendor-products', { params })
    rows.value = data || []
    const total = headers['x-total-count']
    pagination.value.rowsNumber = total != null ? parseInt(total, 10) : (data || []).length
  } catch {
    rows.value = []
  } finally {
    loading.value = false
  }
}

function onFilterChange() {
  pagination.value.page = 1
  loadData()
}

function onRequest(req) {
  const { page, rowsPerPage, sortBy, descending } = req.pagination
  pagination.value = {
    ...pagination.value,
    page: page || 1,
    rowsPerPage: rowsPerPage || 25,
    sortBy,
    descending,
  }
  loadData()
}

function filterCategory(val, update) {
  if (val === '') {
    update(() => {
      categoryOptions.value = allCategories.value
    })
    return
  }
  update(async () => {
    const { data } = await api.get('/api/v1/vendor-products/facets', { params: { q: val } })
    categoryOptions.value = data.categories || []
  })
}

function filterBrand(val, update) {
  if (val === '') {
    update(() => {
      brandOptions.value = allBrands.value
    })
    return
  }
  update(async () => {
    const { data } = await api.get('/api/v1/vendor-products/facets', { params: { q: val } })
    brandOptions.value = data.brands || []
  })
}

function openInfo(row) {
  infoRow.value = row
  infoDialog.value = true
}

onMounted(() => {
  if (!props.productId) loadFacets()
  loadData()
})

// Re-fetch when a single product id is supplied later.
watch(
  () => props.productId,
  (id) => {
    if (id) loadData()
  }
)
</script>

<style scoped>
.vendor-product-table__table {
  max-width: 100%;
}
</style>
