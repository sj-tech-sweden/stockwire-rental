<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <div class="text-h6">{{ t('vendorCatalog.title') }}</div>
    </div>

    <q-tabs v-model="tab" class="text-primary" dense align="left">
      <q-tab name="sources" :label="t('vendorCatalog.sources')" />
      <q-tab name="products" :label="t('vendorCatalog.products')" />
    </q-tabs>
    <q-separator />

    <!-- Sources tab -->
    <div v-show="tab === 'sources'" class="q-mt-md">
      <div class="row items-center q-mb-sm">
        <q-btn
          color="primary"
          icon="add"
          :label="t('vendorCatalog.addSource')"
          @click="openCreate"
        />
      </div>

      <q-table
        :rows="sources"
        :columns="sourceColumns"
        row-key="id"
        :loading="loadingSources"
        flat
        bordered
        dense
      >
        <template #body-cell-enabled="props">
          <q-td :props="props">
            <q-icon :name="props.value ? 'check_circle' : 'cancel'" :color="props.value ? 'positive' : 'grey'" />
          </q-td>
        </template>
        <template #body-cell-status="props">
          <q-td :props="props">
            <q-badge
              v-if="props.row.last_import_status"
              :color="statusColor(props.row.last_import_status)"
              class="text-uppercase"
            >
              {{ statusLabel(props.row) }}
            </q-badge>
          </q-td>
        </template>
        <template #body-cell-vendor="props">
          <q-td :props="props">{{ vendorName(props.value) }}</q-td>
        </template>
        <template #body-cell-actions="props">
          <q-td :props="props" class="text-no-wrap">
            <q-btn dense flat icon="visibility" @click="previewSource(props.row)" :aria-label="t('vendorCatalog.preview')" />
            <q-btn dense flat icon="cloud_download" color="primary" @click="runSource(props.row)" :aria-label="t('vendorCatalog.run')" />
            <q-btn dense flat icon="edit" @click="openEdit(props.row)" />
            <q-btn dense flat icon="delete" color="negative" @click="deleteSource(props.row)" />
          </q-td>
        </template>
        <template #no-data>
          <div class="q-pa-md text-grey">{{ t('vendorCatalog.noSources') }}</div>
        </template>
      </q-table>
    </div>

    <!-- Products tab -->
    <div v-show="tab === 'products'" class="q-mt-md">
      <VendorProductTable :key="productRefresh" />
    </div>

    <!-- Source editor dialog -->
    <q-dialog v-model="dialogOpen" persistent>
      <q-card style="width: 600px; max-width: 90vw">
        <q-card-section class="row items-center">
          <div class="text-h6">
            {{ form.id ? t('vendorCatalog.editSource') : t('vendorCatalog.addSource') }}
          </div>
          <q-space />
          <q-btn flat round dense icon="close" @click="dialogOpen = false" />
        </q-card-section>

        <q-card-section class="q-gutter-md">
          <q-input v-model="form.name" :label="t('vendorCatalog.name')" outlined dense />
          <q-select
            v-model="form.plugin_id"
            :options="pluginOptions"
            :label="t('vendorCatalog.plugin')"
            outlined
            dense
            emit-value
            map-options
            @update:model-value="onPluginChange"
          />
          <q-select
            v-model="form.vendor_id"
            :options="vendorOptions"
            :label="t('vendorCatalog.vendor')"
            outlined
            dense
            emit-value
            map-options
            clearable
          />
          <div class="row items-center q-gutter-sm">
            <q-toggle v-model="form.enabled" :label="t('vendorCatalog.enabled')" />
            <q-input
              v-model.number="form.auto_sync_interval"
              type="number"
              :label="t('vendorCatalog.autoSyncInterval')"
              outlined
              dense
              style="width: 220px"
            />
          </div>
          <!-- Dynamic plugin-specific config fields (declared by the plugin) -->
          <template v-for="field in configFields" :key="field.key">
            <q-select
              v-if="field.type === 'select'"
              v-model="configValues[field.key]"
              :options="field.options"
              :label="field.label"
              :hint="field.help"
              outlined
              dense
              emit-value
              map-options
            />
            <q-input
              v-else
              v-model="configValues[field.key]"
              :label="field.label"
              :type="field.type === 'secret' ? 'password' : (field.type === 'number' ? 'number' : 'text')"
              :hint="field.help"
              outlined
              dense
            />
          </template>
          <q-input
            v-model="form.headersText"
            :label="t('vendorCatalog.headersJson')"
            outlined
            dense
            type="textarea"
            autogrow
          />
          <q-input
            v-model="form.fieldMapText"
            :label="t('vendorCatalog.fieldMapJson')"
            outlined
            dense
            type="textarea"
            autogrow
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat :label="t('vendorCatalog.close')" @click="dialogOpen = false" />
          <q-btn color="primary" :label="t('app.actions.save')" @click="saveSource" :loading="saving" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Preview dialog -->
    <q-dialog v-model="previewOpen" persistent>
      <q-card style="width: 800px; max-width: 95vw">
        <q-card-section class="row items-center">
          <div class="text-h6">{{ t('vendorCatalog.preview') }}</div>
          <q-space />
          <q-btn flat round dense icon="close" @click="previewOpen = false" />
        </q-card-section>
        <q-card-section>
          <div class="text-caption q-mb-sm">{{ t('vendorCatalog.records') }}: {{ previewRecords.length }}</div>
          <q-table
            :rows="previewRecords"
            :columns="previewColumns"
            row-key="sku"
            flat
            bordered
            dense
            :rows-per-page-options="[10, 25, 50]"
          >
            <template #no-data>
              <div class="q-pa-md text-grey">{{ t('vendorCatalog.previewEmpty') }}</div>
            </template>
          </q-table>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('vendorCatalog.close')" @click="previewOpen = false" />
          <q-btn color="primary" :label="t('vendorCatalog.run')" @click="runPreviewSource" :loading="saving" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQuasar, Dialog } from 'quasar'
import { api } from '../boot/axios'
import { useCompaniesStore } from '../stores/companies'
import VendorProductTable from '../components/VendorProductTable.vue'

const { t } = useI18n()
const $q = useQuasar()
const companiesStore = useCompaniesStore()

const tab = ref('sources')
const loadingSources = ref(false)
const saving = ref(false)
const sources = ref([])
const plugins = ref([])

// Bumped after an import completes so the embedded product table remounts and
// re-fetches the freshly upserted rows.
const productRefresh = ref(0)

const dialogOpen = ref(false)
const previewOpen = ref(false)
const previewRecords = ref([])
const previewSourceRow = ref(null)

const form = reactive({
  id: null,
  name: '',
  plugin_id: '',
  vendor_id: null,
  enabled: true,
  auto_sync_interval: 0,
  headersText: '{}',
  fieldMapText: '{}',
})

// Per-plugin config values, keyed by the plugin's declared config_schema.
const configValues = reactive({})

const vendorOptions = computed(() =>
  companiesStore.companies.map((c) => ({ label: c.name, value: c.id }))
)

const vendorName = (id) => {
  if (!id) return t('vendorCatalog.noVendor')
  const c = companiesStore.companies.find((x) => x.id === id)
  return c ? c.name : `#${id}`
}

const pluginOptions = computed(() =>
  plugins.value.map((p) => ({ label: p.label, value: p.id }))
)

const pluginLabel = (id) => {
  const p = plugins.value.find((x) => x.id === id)
  return p ? p.label : id
}

function statusColor(status) {
  if (status === 'completed') return 'positive'
  if (status === 'failed') return 'negative'
  if (status === 'running') return 'warning'
  return 'grey'
}

function statusLabel(row) {
  const status = row.last_import_status
  const stage = row.last_import_stage
  if (status === 'running' && stage) {
    return t(`vendorCatalog.importStage.${stage}`) || stage
  }
  return t(`vendorCatalog.importStatus.${status}`) || status
}

const pluginMeta = computed(() => plugins.value.find((p) => p.id === form.plugin_id) || null)
const configFields = computed(() => pluginMeta.value?.config_schema || [])

const sourceColumns = [
  { name: 'name', label: t('vendorCatalog.name'), field: 'name', align: 'left' },
  { name: 'plugin', label: t('vendorCatalog.plugin'), field: 'plugin_id', align: 'left', format: (v) => pluginLabel(v) },
  { name: 'vendor', label: t('vendorCatalog.vendor'), field: 'vendor_id', align: 'left' },
  { name: 'enabled', label: t('vendorCatalog.enabled'), field: 'enabled', align: 'center' },
  { name: 'last_synced_at', label: t('vendorCatalog.lastSynced'), field: 'last_synced_at', align: 'left' },
  { name: 'status', label: t('vendorCatalog.status'), field: 'last_import_status', align: 'left' },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
]

const previewColumns = [
  { name: 'sku', label: t('vendorCatalog.sku'), field: 'sku', align: 'left' },
  { name: 'name', label: t('vendorCatalog.name'), field: 'name', align: 'left' },
  { name: 'brand', label: t('vendorCatalog.brand'), field: 'brand', align: 'left' },
  { name: 'category', label: t('vendorCatalog.category'), field: 'category', align: 'left' },
  { name: 'unit_cost', label: t('vendorCatalog.unitCost'), field: 'unit_cost', align: 'right' },
  { name: 'currency', label: t('vendorCatalog.currency'), field: 'currency', align: 'left' },
  { name: 'stock_quantity', label: t('vendorCatalog.stock'), field: 'stock_quantity', align: 'right' },
  { name: 'availability', label: t('vendorCatalog.availability'), field: 'availability', align: 'left' },
]

function defaultFieldMapFor(pluginId) {
  const p = plugins.value.find((x) => x.id === pluginId)
  return p?.default_field_map || {}
}

// Surface the backend's actual error detail (e.g. an Aurdel/auth/DB failure)
// instead of only the generic "failed to load" message, so problems are
// debuggable from the UI.
function notifyError(e, fallbackKey) {
  const detail = e?.response?.data?.detail
  $q.notify({ type: 'negative', message: detail ? `${t(fallbackKey)}: ${detail}` : t(fallbackKey) })
}

// Seed configValues from the plugin's declared defaults (used when creating
// a new source so selects/text fields are pre-filled).
function seedConfigDefaults() {
  for (const key of Object.keys(configValues)) delete configValues[key]
  for (const field of configFields.value) {
    if (field.default !== undefined) configValues[field.key] = field.default
  }
}

function onPluginChange(pluginId) {
  if (!form.id) {
    seedConfigDefaults()
    form.fieldMapText = JSON.stringify(defaultFieldMapFor(pluginId), null, 2)
  }
}

async function loadSources() {
  loadingSources.value = true
  try {
    const { data } = await api.get('/api/v1/vendor-catalog/sources')
    sources.value = data || []
  } catch (e) {
    notifyError(e, 'vendorCatalog.failedToLoad')
  } finally {
    loadingSources.value = false
  }
}

async function loadPlugins() {
  try {
    const { data } = await api.get('/api/v1/vendor-catalog/plugins')
    plugins.value = data || []
  } catch (e) {
    plugins.value = []
  }
}

function openCreate() {
  form.id = null
  form.name = ''
  form.plugin_id = ''
  form.vendor_id = null
  form.enabled = true
  form.auto_sync_interval = 0
  form.headersText = '{}'
  form.fieldMapText = '{}'
  seedConfigDefaults()
  dialogOpen.value = true
}

function openEdit(source) {
  form.id = source.id
  form.name = source.name
  form.plugin_id = source.plugin_id
  form.vendor_id = source.vendor_id
  form.enabled = source.enabled
  form.auto_sync_interval = source.auto_sync_interval || 0
  // Populate the dynamic config fields from the stored config.
  for (const key of Object.keys(configValues)) delete configValues[key]
  const cfg = source.config || {}
  for (const field of configFields.value) {
    if (cfg[field.key] !== undefined) configValues[field.key] = cfg[field.key]
    else if (field.default !== undefined) configValues[field.key] = field.default
  }
  form.headersText = cfg.headers ? JSON.stringify(cfg.headers, null, 2) : '{}'
  form.fieldMapText = JSON.stringify(source.field_map || {}, null, 2)
  dialogOpen.value = true
}

function buildPayload() {
  let headers = {}
  try {
    headers = form.headersText ? JSON.parse(form.headersText) : {}
  } catch {
    headers = {}
  }
  let field_map = {}
  try {
    field_map = form.fieldMapText ? JSON.parse(form.fieldMapText) : {}
  } catch {
    field_map = {}
  }
  // Build the config object from the plugin's declared fields; only include
  // values that are non-empty so we don't send blank credentials/links.
  const config = {}
  for (const field of configFields.value) {
    const value = configValues[field.key]
    if (value !== undefined && value !== null && value !== '') {
      config[field.key] = value
    }
  }
  if (Object.keys(headers).length) config.headers = headers
  return {
    name: form.name,
    plugin_id: form.plugin_id,
    enabled: form.enabled,
    vendor_id: form.vendor_id || null,
    auto_sync_interval: Number(form.auto_sync_interval) || 0,
    config,
    field_map,
  }
}

async function saveSource() {
  saving.value = true
  try {
    const payload = buildPayload()
    if (form.id) {
      await api.put(`/api/v1/vendor-catalog/sources/${form.id}`, payload)
    } else {
      await api.post('/api/v1/vendor-catalog/sources', payload)
    }
    dialogOpen.value = false
    await loadSources()
    $q.notify({ type: 'positive', message: t('common.saved') })
  } catch (e) {
    $q.notify({ type: 'negative', message: t('app.actions.saveFailed') })
  } finally {
    saving.value = false
  }
}

function previewSource(source) {
  previewSourceRow.value = source
  api
    .post(`/api/v1/vendor-catalog/sources/${source.id}/preview`)
    .then(({ data }) => {
      previewRecords.value = data.records || []
      previewOpen.value = true
    })
    .catch((e) => notifyError(e, 'vendorCatalog.failedToLoad'))
}

async function runSource(source) {
  saving.value = true
  source.last_import_status = 'pending'
  source.last_import_stage = 'queued'
  try {
    const { data } = await api.post(`/api/v1/vendor-catalog/sources/${source.id}/run`)
    const result = await pollImportJob(data.job_id)
    if (result.status === 'completed') {
      $q.notify({
        type: 'positive',
        message: `${t('vendorCatalog.created')}: ${result.created ?? 0}, ${t('vendorCatalog.updated')}: ${result.updated ?? 0}`,
      })
      await loadSources()
      productRefresh.value++
    } else {
      $q.notify({ type: 'negative', message: result.error || t('vendorCatalog.failedToLoad') })
    }
  } catch (e) {
    notifyError(e, 'vendorCatalog.failedToLoad')
  } finally {
    saving.value = false
  }
}

function pollImportJob(jobId) {
  return new Promise((resolve) => {
    const interval = setInterval(async () => {
      try {
        const { data } = await api.get(`/api/v1/vendor-catalog/vendor-import-jobs/${jobId}`)
        const sourceRow = sources.value.find((s) => s.id === data.source_id)
        if (sourceRow) {
          sourceRow.last_import_status = data.status
          sourceRow.last_import_stage = data.stage
          sourceRow.last_import_processed = data.processed
          sourceRow.last_import_total = data.total
          sourceRow.last_import_error = data.error
        }
        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(interval)
          resolve(data)
        }
      } catch (e) {
        clearInterval(interval)
        resolve({ status: 'failed', error: e?.response?.data?.detail || t('vendorCatalog.failedToLoad') })
      }
    }, 500)
  })
}

function runPreviewSource() {
  if (previewSourceRow.value) runSource(previewSourceRow.value).then(() => (previewOpen.value = false))
}

function deleteSource(source) {
  Dialog.create({
    title: t('vendorCatalog.editSource'),
    message: t('vendorCatalog.confirmDelete'),
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await api.delete(`/api/v1/vendor-catalog/sources/${source.id}`)
      await loadSources()
    } catch (e) {
      $q.notify({ type: 'negative', message: t('app.actions.deleteFailed') })
    }
  })
}

onMounted(async () => {
  await companiesStore.fetchAll().catch(() => {})
  await loadPlugins()
  await loadSources()
})
</script>
