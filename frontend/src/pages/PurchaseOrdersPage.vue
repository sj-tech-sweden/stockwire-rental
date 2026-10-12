<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <div class="text-h6 q-mr-auto">{{ t('purchasing.title') }}</div>
      <q-btn
        color="primary"
        icon="add"
        :label="t('purchasing.createCombined')"
        class="q-mr-sm"
        @click="openCombined"
      />
      <q-btn
        color="primary"
        icon="post_add"
        :label="t('purchasing.newPo')"
        @click="openNewPo"
      />
    </div>

    <q-table
      :rows="orders"
      :columns="columns"
      row-key="id"
      :loading="loading"
      :no-data-label="t('purchasing.noPos')"
      :rows-per-page-options="[25, 50, 100, 0]"
    >
      <template #body-cell-status="props">
        <q-td :props="props">
          <q-chip :color="statusColor(props.value)" text-color="white" size="sm" dense>
            {{ statusLabel(props.value) }}
          </q-chip>
        </q-td>
      </template>
      <template #body-cell-actions="props">
        <q-td :props="props">
          <q-btn flat dense icon="visibility" :label="t('purchasing.open')" @click="openDetail(props.row)" />
          <q-btn flat dense icon="local_shipping" color="primary" :label="t('purchasing.receive')" @click="goReceive(props.row.id)" />
          <q-btn flat dense icon="picture_as_pdf" :label="t('purchasing.downloadPdf')" @click="downloadPdf(props.row)" />
          <q-btn flat dense icon="delete" color="negative" :label="t('purchasing.delete')" @click="confirmDelete(props.row)" />
        </q-td>
      </template>
    </q-table>

    <!-- Job picker for combined PO -->
    <q-dialog v-model="combinedOpen" style="width: 600px; max-width: 95vw">
      <q-card style="width: 600px; max-width: 95vw">
        <q-card-section class="row items-center">
          <div class="text-h6 q-mr-auto">{{ t('purchasing.createCombined') }}</div>
          <q-btn flat round icon="close" @click="combinedOpen = false" />
        </q-card-section>
        <q-card-section>
          <q-select
            v-model="combinedJobIds"
            :options="jobOptions"
            multiple
            use-chips
            emit-value
            map-options
            outlined
            :label="t('purchasing.jobs')"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="combinedOpen = false" />
          <q-btn
            color="primary"
            :label="t('app.actions.continue')"
            :disable="!combinedJobIds.length"
            @click="startBuilder"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Reusable builder dialog -->
    <PurchaseOrderBuilderDialog
      v-model="builderOpen"
      :job-ids="builderJobIds"
      :po-id="builderPoId"
      :allowed-supplier-id="builderSupplier"
      @done="onBuilderDone"
    />

    <!-- PO detail dialog -->
    <q-dialog v-model="detailOpen" persistent style="width: 900px; max-width: 95vw">
      <q-card v-if="selectedPo" style="width: 900px; max-width: 95vw">
        <q-card-section class="row items-center">
          <div class="text-h6 q-mr-auto">
            {{ selectedPo.po_number }}
            <q-chip color="grey-7" text-color="white" size="sm" dense>{{ selectedPo.status }}</q-chip>
          </div>
          <q-btn flat round icon="close" @click="detailOpen = false" />
        </q-card-section>

        <q-card-section>
          <div class="row q-col-gutter-sm q-mb-md">
            <div class="col-4">
              <div class="text-caption">{{ t('purchasing.supplier') }}</div>
              <div>{{ selectedPo.supplier_name || '—' }}</div>
            </div>
            <div class="col-4">
              <div class="text-caption">{{ t('purchasing.total') }}</div>
              <div>
                {{ selectedPo.grand_total_base != null ? selectedPo.grand_total_base : '—' }}
                {{ selectedPo.report_currency }}
              </div>
              <div v-if="selectedPo.freight_base" class="text-caption">
                {{ t('purchasing.subtotal') }}: {{ selectedPo.total_base }} ·
                {{ t('purchasing.freight') }}: {{ selectedPo.freight_base }}
              </div>
            </div>
            <div class="col-4">
              <div class="text-caption">{{ t('purchasing.changeStatus') }}</div>
              <div class="row items-center">
                <q-select
                  v-model="statusDraft"
                  :options="statusOptions"
                  emit-value
                  map-options
                  dense
                  outlined
                  class="col"
                />
                <q-btn
                  flat
                  dense
                  icon="save"
                  color="primary"
                  class="q-ml-xs"
                  :loading="statusSaving"
                  @click="saveStatus"
                >
                  <q-tooltip>{{ t('purchasing.saveStatus') }}</q-tooltip>
                </q-btn>
              </div>
            </div>
          </div>

          <q-table
            :rows="selectedPo.lines"
            :columns="lineColumns"
            row-key="id"
            hide-bottom
            dense
          >
            <template #body-cell-name="props">
              <q-td :props="props">
                {{ props.row.name }}
                <q-chip v-if="props.row.is_restock" color="orange" text-color="white" size="xs" dense>
                  {{ t('purchasing.restock') }}
                </q-chip>
                <q-chip v-if="props.row.is_manual" color="teal" text-color="white" size="xs" dense>
                  {{ t('purchasing.manual') }}
                </q-chip>
              </q-td>
            </template>
            <template #body-cell-received_qty="props">
              <q-td :props="props">
                <q-input
                  v-model.number="props.row.received_qty"
                  type="number"
                  dense
                  borderless
                  :max="props.row.qty"
                  min="0"
                />
              </q-td>
            </template>
            <template #body-cell-actions="props">
              <q-td :props="props" class="text-right">
                <q-btn
                  flat
                  dense
                  icon="edit"
                  :label="t('purchasing.editLine')"
                  class="q-mr-xs"
                  @click="openEditLine(props.row)"
                />
              </q-td>
            </template>
          </q-table>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat icon="delete" color="negative" :label="t('purchasing.delete')" @click="confirmDelete(selectedPo)" />
          <q-btn flat icon="picture_as_pdf" :label="t('purchasing.downloadPdf')" @click="downloadPdf(selectedPo)" />
          <q-btn
            flat
            color="secondary"
            icon="playlist_add"
            :label="t('purchasing.addLine')"
            @click="addLineToPo"
          />
          <q-btn color="primary" :label="t('purchasing.receive')" @click="goReceive(selectedPo.id)" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <EditPOLineDialog
      v-model="editLineOpen"
      :po-id="selectedPo ? selectedPo.id : 0"
      :line="editLineTarget"
      @saved="onLineSaved"
      @deleted="onLineSaved"
    />
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQuasar } from 'quasar'
import { useRouter } from 'vue-router'
import { api } from '../boot/axios'
import { date as qdate } from 'quasar'
import PurchaseOrderBuilderDialog from '../components/PurchaseOrderBuilderDialog.vue'
import EditPOLineDialog from '../components/EditPOLineDialog.vue'

const { t, locale } = useI18n()
const $q = useQuasar()
const router = useRouter()

function goReceive(poId) {
  router.push({ path: '/receive', query: { po: String(poId) } })
}

const orders = ref([])
const jobs = ref([])
const loading = ref(false)

const combinedOpen = ref(false)
const combinedJobIds = ref([])

const builderOpen = ref(false)
const builderJobIds = ref([])
const builderPoId = ref(null)
const builderSupplier = ref(null)

const detailOpen = ref(false)
const selectedPo = ref(null)
const statusDraft = ref(null)
const statusSaving = ref(false)

const editLineOpen = ref(false)
const editLineTarget = ref(null)

function openEditLine(row) {
  editLineTarget.value = row
  editLineOpen.value = true
}

async function onLineSaved() {
  if (selectedPo.value) {
    await reloadPo(selectedPo.value.id)
  }
}

function asList(resp) {
  if (Array.isArray(resp)) return resp
  if (resp && Array.isArray(resp.items)) return resp.items
  if (resp && resp.data && Array.isArray(resp.data)) return resp.data
  return []
}

const jobOptions = computed(() =>
  jobs.value.map((j) => ({ label: `${j.job_code || j.code || j.id}`, value: j.id }))
)

const columns = computed(() => [
  { name: 'po_number', label: t('purchasing.poNumber'), field: 'po_number', align: 'left' },
  { name: 'supplier_name', label: t('purchasing.supplier'), field: 'supplier_name', align: 'left' },
  { name: 'status', label: t('purchasing.status'), field: 'status', align: 'left' },
  {
    name: 'grand_total_base',
    label: t('purchasing.total'),
    field: (row) =>
      row.grand_total_base != null ? `${row.grand_total_base} ${row.report_currency}` : '—',
    align: 'right',
  },
  {
    name: 'created_at',
    label: t('purchasing.created'),
    field: 'created_at',
    align: 'left',
    format: (v) => (v ? qdate.formatDate(v, 'YYYY-MM-DD HH:mm') : '—'),
  },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
])

const lineColumns = computed(() => [
  { name: 'name', label: t('purchasing.item'), field: 'name', align: 'left' },
  { name: 'sku', label: t('purchasing.sku'), field: 'sku', align: 'left' },
  { name: 'qty', label: t('purchasing.qty'), field: 'qty', align: 'left' },
  { name: 'received_qty', label: t('purchasing.receivedQty'), field: 'received_qty', align: 'left' },
  { name: 'unit_cost', label: t('purchasing.unitCost'), field: 'unit_cost', align: 'right' },
  { name: 'line_total', label: t('purchasing.lineTotal'), field: 'line_total', align: 'right' },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
])

function statusColor(status) {
  switch (status) {
    case 'received':
      return 'positive'
    case 'partial':
      return 'warning'
    case 'sent':
    case 'ordered':
      return 'info'
    case 'cancelled':
      return 'red-10'
    default:
      return 'grey-7'
  }
}

const statusKey = {
  draft: 'purchasing.statusDraft',
  sent: 'purchasing.statusSent',
  approved: 'purchasing.statusApproved',
  ordered: 'purchasing.statusOrdered',
  partial: 'purchasing.statusPartial',
  received: 'purchasing.statusReceived',
  cancelled: 'purchasing.statusCancelled',
}

const statusOptions = computed(() =>
  Object.entries(statusKey).map(([value, key]) => ({ label: t(key), value }))
)

function statusLabel(status) {
  return t(statusKey[status] || 'purchasing.statusDraft')
}

async function loadOrders() {
  loading.value = true
  try {
    const { data } = await api.get('/api/v1/purchasing/purchase-orders')
    orders.value = asList(data)
  } finally {
    loading.value = false
  }
}

async function loadJobs() {
  try {
    const { data } = await api.get('/api/v1/jobs')
    jobs.value = asList(data)
  } catch {
    jobs.value = []
  }
}

function openCombined() {
  combinedJobIds.value = []
  combinedOpen.value = true
}

function startBuilder() {
  combinedOpen.value = false
  builderPoId.value = null
  builderSupplier.value = null
  builderJobIds.value = [...combinedJobIds.value]
  builderOpen.value = true
}

function openNewPo() {
  builderPoId.value = null
  builderSupplier.value = null
  builderJobIds.value = []
  builderOpen.value = true
}

function onBuilderDone() {
  loadOrders()
  if (selectedPo.value) reloadPo(selectedPo.value.id)
}

function addLineToPo() {
  if (!selectedPo.value) return
  builderPoId.value = selectedPo.value.id
  builderSupplier.value = selectedPo.value.supplier_company_id
  builderJobIds.value = []
  builderOpen.value = true
}

function openDetail(po) {
  selectedPo.value = JSON.parse(JSON.stringify(po))
  statusDraft.value = po.status
  detailOpen.value = true
}

async function reloadPo(id) {
  try {
    const { data } = await api.get(`/api/v1/purchasing/purchase-orders/${id}`)
    selectedPo.value = data
    statusDraft.value = data.status
  } catch {
    /* ignore */
  }
}

async function saveStatus() {
  if (!selectedPo.value || statusDraft.value === selectedPo.value.status) return
  statusSaving.value = true
  try {
    const { data } = await api.patch(
      `/api/v1/purchasing/purchase-orders/${selectedPo.value.id}`,
      { status: statusDraft.value }
    )
    selectedPo.value = data
    const idx = orders.value.findIndex((o) => o.id === data.id)
    if (idx !== -1) orders.value[idx] = data
    $q.notify({ type: 'positive', message: t('purchasing.saveStatus') })
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Error' })
  } finally {
    statusSaving.value = false
  }
}

function confirmDelete(po) {
  $q.dialog({
    title: t('purchasing.delete'),
    message: t('purchasing.deleteConfirm'),
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await api.delete(`/api/v1/purchasing/purchase-orders/${po.id}`)
      orders.value = orders.value.filter((o) => o.id !== po.id)
      if (selectedPo.value && selectedPo.value.id === po.id) detailOpen.value = false
      $q.notify({ type: 'positive', message: t('purchasing.delete') })
    } catch (e) {
      $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Error' })
    }
  })
}

async function downloadPdf(po) {
  try {
    const resp = await api.get(`/api/v1/purchasing/purchase-orders/${po.id}/pdf`, {
      params: { language: String(locale.value || 'en').split(/[-_]/)[0] },
      responseType: 'blob',
    })
    const url = URL.createObjectURL(resp.data)
    window.open(url, '_blank')
    setTimeout(() => URL.revokeObjectURL(url), 60000)
  } catch {
    $q.notify({ type: 'negative', message: 'PDF error' })
  }
}

onMounted(() => {
  loadOrders()
  loadJobs()
})
</script>
