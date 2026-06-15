<template>
  <q-page class="q-pa-md ec-page">
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">{{ t('defects.title') }}</div>
      <q-btn color="primary" icon="refresh" :label="t('defects.refresh')" unelevated @click="refresh" :loading="loading" />
    </div>

    <div class="row q-col-gutter-sm q-mb-sm">
      <div class="col-12 col-md-3">
        <q-select v-model="statusFilter" :options="statusOptions" :label="t('defects.filterStatus')" outlined dense emit-value map-options clearable @update:model-value="refresh" />
      </div>
      <div class="col-12 col-md-3">
        <q-select v-model="severityFilter" :options="severityOptions" :label="t('defects.filterSeverity')" outlined dense emit-value map-options clearable @update:model-value="refresh" />
      </div>
      <div class="col-12 col-md-3">
        <q-input v-model="assetTagFilter" dense outlined clearable :label="t('defects.filterAssetTag')" @update:model-value="refresh" />
      </div>
      <div class="col-12 col-md-3">
        <q-input v-model="search" dense outlined clearable :placeholder="t('defects.searchTitle')" @update:model-value="refresh" />
      </div>
    </div>

    <q-table
      :rows="filteredDefects"
      :columns="columns"
      row-key="id"
      :grid="compactGrid"
      :hide-header="compactGrid"
      flat
      bordered
      class="ec-card"
      :loading="loading"
      :pagination="{ rowsPerPage: 25 }"
      :rows-per-page-options="[25, 50, 100]"
    >
      <template #body-cell-asset_tag="props">
        <q-td :props="props">
          <a class="link" @click="openDeviceInfo(props.row.device_id)">{{ props.value }}</a>
        </q-td>
      </template>
      <template #body-cell-product_name="props">
        <q-td :props="props">
          <a v-if="props.row.product_id" class="link" @click="openProductInfo(props.row)">{{ props.value }}</a>
          <span v-else>{{ props.value }}</span>
        </q-td>
      </template>
      <template #body-cell-status="props">
        <q-td :props="props">
          <q-select
            :model-value="props.row.status"
            :options="defectStatusOptions"
            dense
            outlined
            emit-value
            map-options
            size="sm"
            style="min-width: 120px"
            @update:model-value="(v) => updateDefectField(props.row, 'status', v)"
          />
        </q-td>
      </template>

      <template #body-cell-severity="props">
        <q-td :props="props">
          <q-select
            :model-value="props.row.severity"
            :options="defectSeverityOptions"
            dense
            outlined
            emit-value
            map-options
            size="sm"
            style="min-width: 100px"
            @update:model-value="(v) => updateDefectField(props.row, 'severity', v)"
          />
        </q-td>
      </template>

      <template #body-cell-title="props">
        <q-td :props="props">
          <q-input
            :model-value="props.row.title"
            dense
            outlined
            @update:model-value="(v) => updateDefectField(props.row, 'title', v)"
          />
        </q-td>
      </template>

      <template #body-cell-description="props">
        <q-td :props="props">
          <q-input
            :model-value="props.row.description"
            dense
            outlined
            type="textarea"
            autogrow
            @update:model-value="(v) => updateDefectField(props.row, 'description', v || null)"
          />
        </q-td>
      </template>

      <template #body-cell-actions="props">
        <q-td :props="props" class="q-gutter-xs">
          <q-btn dense flat icon="chat" color="primary" @click="toggleComments(props.row)">
            <q-badge v-if="props.row.commentCount" color="primary" floating>{{ props.row.commentCount }}</q-badge>
          </q-btn>
          <q-btn dense flat icon="delete" color="negative" @click="deleteDefect(props.row)" />
        </q-td>
      </template>

      <template #top-row>
        <tr v-if="expandedDefectId">
          <td :colspan="columns.length" class="q-pa-md bg-grey-1">
            <div class="text-subtitle2 q-mb-sm">{{ t('defects.comments') }}</div>
            <div v-if="!expandedComments.length" class="text-caption text-grey-6 q-mb-sm">{{ t('defects.noComments') }}</div>
            <div v-for="comment in expandedComments" :key="comment.id" class="q-mb-xs">
              <div class="comment-bubble">{{ comment.comment }}</div>
            </div>
            <div class="row items-center q-mt-sm">
              <q-input
                v-model="newCommentText"
                dense
                outlined
                type="textarea"
                autogrow
                :placeholder="t('defects.addComment')"
                class="col-grow"
              />
              <q-btn dense flat icon="send" color="primary" :loading="savingComment" :disable="!newCommentText?.trim()" @click="addComment(expandedDefectId)" class="q-ml-xs" />
            </div>
          </td>
        </tr>
      </template>

      <template #item="props">
        <div class="q-pa-xs col-12">
          <q-card flat bordered>
            <q-card-section class="q-pb-sm">
              <div class="text-subtitle2">
                <a class="link" @click="openDeviceInfo(props.row.device_id)">{{ props.row.asset_tag }}</a>
              </div>
              <div class="text-caption text-grey-7">
                <a v-if="props.row.product_id" class="link" @click="openProductInfo(props.row)">{{ props.row.product_name }}</a>
                <span v-else>{{ props.row.product_name }}</span>
              </div>
            </q-card-section>
            <q-card-section class="q-pt-none q-pb-sm">
              <div class="row q-col-gutter-xs">
                <div class="col-6">
                  <q-select
                    :model-value="props.row.status"
                    :options="defectStatusOptions"
                    dense
                    outlined
                    emit-value
                    map-options
                    size="sm"
                    @update:model-value="(v) => updateDefectField(props.row, 'status', v)"
                  />
                </div>
                <div class="col-6">
                  <q-select
                    :model-value="props.row.severity"
                    :options="defectSeverityOptions"
                    dense
                    outlined
                    emit-value
                    map-options
                    size="sm"
                    @update:model-value="(v) => updateDefectField(props.row, 'severity', v)"
                  />
                </div>
                <div class="col-12 q-mt-xs">
                  <q-input
                    :model-value="props.row.title"
                    dense
                    outlined
                    :placeholder="t('defects.titlePlaceholder')"
                    @update:model-value="(v) => updateDefectField(props.row, 'title', v)"
                  />
                </div>
                <div class="col-12" v-if="props.row.description">
                  <div class="text-caption q-mt-xs">{{ props.row.description }}</div>
                </div>
                <div class="col-12 text-caption text-grey-6 q-mt-xs">
                  {{ t('defects.created') }}: {{ props.row.created_at }}
                </div>
                <div class="col-12" v-if="expandedDefectId === props.row.id">
                  <div class="text-subtitle2 q-mt-sm q-mb-sm">{{ t('defects.comments') }}</div>
                  <div v-if="!expandedComments.length" class="text-caption text-grey-6 q-mb-sm">{{ t('defects.noComments') }}</div>
                  <div v-for="comment in expandedComments" :key="comment.id" class="q-mb-xs">
                    <div class="comment-bubble">{{ comment.comment }}</div>
                  </div>
                  <div class="row items-center q-mt-sm">
                    <q-input
                      v-model="newCommentText"
                      dense
                      outlined
                      type="textarea"
                      autogrow
                      :placeholder="t('defects.addComment')"
                      class="col-grow"
                    />
                    <q-btn dense flat icon="send" color="primary" :loading="savingComment" :disable="!newCommentText?.trim()" @click="addComment(expandedDefectId)" class="q-ml-xs" />
                  </div>
                </div>
              </div>
            </q-card-section>
            <q-card-actions align="right">
              <q-btn dense flat icon="chat" color="primary" @click="toggleComments(props.row)">
                <q-badge v-if="props.row.commentCount" color="primary" floating>{{ props.row.commentCount }}</q-badge>
              </q-btn>
              <q-btn dense flat icon="delete" color="negative" @click="deleteDefect(props.row)" />
            </q-card-actions>
          </q-card>
        </div>
      </template>
    </q-table>
    <ProductInfoDialog
      v-model="productInfoDialogOpen"
      :product="productInfoTarget"
      @edit-product="openProductEdit(productInfoTarget)"
      @view-device="(id) => openDeviceInfo(id)"
    />
    <ProductDialog
      v-model="productDialogOpen"
      :product="productEditing"
      @saved="onProductDialogSaved"
    />
    <DeviceInfoDialog
      v-model="deviceInfoDialogOpen"
      :device="deviceInfoTarget"
      @edit-device="(id) => openDeviceInfo(id)"
      @view-device="(id) => openDeviceInfo(id)"
    />
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'
import { useInventoryStore } from '../stores/inventory'
import { useCompactGrid } from '../composables/useCompactGrid'
import ProductDialog from '../components/ProductDialog.vue'
import ProductInfoDialog from '../components/ProductInfoDialog.vue'
import DeviceInfoDialog from '../components/DeviceInfoDialog.vue'

const { t } = useI18n()
const $q = useQuasar()
const inventoryStore = useInventoryStore()

const compactGrid = useCompactGrid(1024)

const productInfoDialogOpen = ref(false)
const productInfoTarget = ref(null)

const productDialogOpen = ref(false)
const productEditing = ref(null)

const deviceInfoDialogOpen = ref(false)
const deviceInfoTarget = ref(null)

const loading = ref(false)
const defects = ref([])
const statusFilter = ref(null)
const severityFilter = ref(null)
const assetTagFilter = ref('')
const search = ref('')
const expandedDefectId = ref(null)
const expandedComments = ref([])
const newCommentText = ref('')
const savingComment = ref(false)

const defectStatusOptions = [
  { label: t('inventory.defectStatusOpen'), value: 'open' },
  { label: t('inventory.defectStatusInProgress'), value: 'in_progress' },
  { label: t('inventory.defectStatusResolved'), value: 'resolved' },
  { label: t('inventory.defectStatusClosed'), value: 'closed' },
]

const defectSeverityOptions = [
  { label: t('inventory.defectSeverityLow'), value: 'low' },
  { label: t('inventory.defectSeverityMedium'), value: 'medium' },
  { label: t('inventory.defectSeverityHigh'), value: 'high' },
  { label: t('inventory.defectSeverityCritical'), value: 'critical' },
]

const statusOptions = computed(() => [{ label: t('defects.all'), value: null }, ...defectStatusOptions])
const severityOptions = computed(() => [{ label: t('defects.all'), value: null }, ...defectSeverityOptions])

const columns = [
  { name: 'id', label: t('defects.columnId'), field: 'id', sortable: true, style: 'width: 60px' },
  { name: 'asset_tag', label: t('defects.columnDevice'), field: 'asset_tag', sortable: true },
  { name: 'product_name', label: t('defects.columnProduct'), field: 'product_name', sortable: true },
  { name: 'title', label: t('defects.columnTitle'), field: 'title', sortable: true, style: 'min-width: 180px' },
  { name: 'description', label: t('defects.columnDescription'), field: 'description', style: 'min-width: 200px' },
  { name: 'status', label: t('defects.columnStatus'), field: 'status', sortable: true },
  { name: 'severity', label: t('defects.columnSeverity'), field: 'severity', sortable: true },
  { name: 'created_at', label: t('defects.columnCreated'), field: 'created_at', sortable: true },
  { name: 'actions', label: '', field: 'actions', style: 'width: 90px' },
]

const filteredDefects = computed(() => {
  let result = defects.value
  if (statusFilter.value) {
    result = result.filter(d => d.status === statusFilter.value)
  }
  if (severityFilter.value) {
    result = result.filter(d => d.severity === severityFilter.value)
  }
  const assetTag = assetTagFilter.value?.trim().toLowerCase()
  if (assetTag) {
    result = result.filter(d => String(d.asset_tag || '').toLowerCase().includes(assetTag))
  }
  const needle = search.value?.trim().toLowerCase()
  if (needle) {
    result = result.filter(d => String(d.title || '').toLowerCase().includes(needle))
  }
  return result
})

async function refresh() {
  loading.value = true
  try {
    const { data } = await api.get('/api/v1/inventory/defect-reports')
    defects.value = (data || []).map(d => ({
      ...d,
      commentCount: 0,
    }))
    for (const defect of defects.value) {
      try {
        const { data: comments } = await api.get(`/api/v1/inventory/defect-reports/${defect.id}/comments`)
        defect.commentCount = (comments || []).length
      } catch {
        defect.commentCount = 0
      }
    }
  } catch {
    defects.value = []
  } finally {
    loading.value = false
  }
}

const fieldTimers = {}

function updateDefectField(defect, field, value) {
  defect[field] = value
  const key = `${defect.id}-${field}`
  if (fieldTimers[key]) clearTimeout(fieldTimers[key])
  fieldTimers[key] = setTimeout(async () => {
    try {
      await api.put(`/api/v1/inventory/defect-reports/${defect.id}`, { [field]: value })
    } catch (error) {
      // Will be overwritten on next refresh
    }
  }, 600)
}

async function toggleComments(defect) {
  if (expandedDefectId.value === defect.id) {
    expandedDefectId.value = null
    expandedComments.value = []
    return
  }
  expandedDefectId.value = defect.id
  expandedComments.value = []
  try {
    const { data } = await api.get(`/api/v1/inventory/defect-reports/${defect.id}/comments`)
    expandedComments.value = data || []
  } catch {
    expandedComments.value = []
  }
}

async function addComment(defectId) {
  const text = (newCommentText.value || '').trim()
  if (!text || !defectId) return
  savingComment.value = true
  try {
    const { data } = await api.post(`/api/v1/inventory/defect-reports/${defectId}/comments`, { comment: text })
    expandedComments.value.push(data)
    newCommentText.value = ''
    const defect = defects.value.find(d => d.id === defectId)
    if (defect) defect.commentCount = (defect.commentCount || 0) + 1
  } catch {
    // ignore
  } finally {
    savingComment.value = false
  }
}

async function openDeviceInfo(deviceId) {
  const targetId = Number(deviceId || 0)
  if (!targetId) return
  let device = inventoryStore.devices.find(d => d.id === targetId)
  if (!device) {
    try {
      const { data } = await api.get(`/api/v1/inventory/devices/${targetId}`)
      device = data
    } catch {
      return
    }
  }
  deviceInfoTarget.value = device
  deviceInfoDialogOpen.value = true
}

async function openProductInfo(defect) {
  if (!defect?.product_id) return
  let product = inventoryStore.products.find(p => p.id === defect.product_id)
  if (!product) {
    try {
      const { data } = await api.get(`/api/v1/inventory/products/${defect.product_id}`)
      product = data
    } catch {
      return
    }
  }
  productInfoTarget.value = product
  productInfoDialogOpen.value = true
}

function openProductEdit(product) {
  productEditing.value = product
  productDialogOpen.value = true
}

function onProductDialogSaved() {
  // Re-fetch defects after product edit
  refresh()
}

async function deleteDefect(defect) {
  $q.dialog({
    title: t('inventory.deleteDefect'),
    message: t('inventory.deleteDefectConfirm', { title: defect.title || defect.id }),
    cancel: true,
    persistent: true,
    ok: { label: t('inventory.delete'), color: 'negative' },
  }).onOk(async () => {
    try {
      await api.delete(`/api/v1/inventory/defect-reports/${defect.id}`)
      defects.value = defects.value.filter(d => d.id !== defect.id)
      if (expandedDefectId.value === defect.id) {
        expandedDefectId.value = null
        expandedComments.value = []
      }
    } catch (error) {
      $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('inventory.failedDeleteDefect') })
    }
  })
}

onMounted(refresh)
</script>

<style lang="scss" scoped>
.comment-bubble {
  background: #f5f5f5;
  border-radius: 6px;
  padding: 6px 10px;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.85rem;
  line-height: 1.4;
}

.link {
  color: var(--q-primary);
  cursor: pointer;
  text-decoration: none;
}
.link:hover {
  text-decoration: underline;
}
</style>

<style lang="scss">
body.body--dark .comment-bubble {
  background: #333;
}
</style>
