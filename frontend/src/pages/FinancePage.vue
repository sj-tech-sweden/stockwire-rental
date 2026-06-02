<template>
  <q-page class="q-pa-md ec-page">
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">{{ t('finance.title') }}</div>
      <div class="row q-gutter-sm">
        <q-btn color="primary" icon="refresh" :label="t('finance.reload')" unelevated @click="reload" :loading="isLoading" />
        <q-btn
          v-if="authStore.canEdit"
          color="secondary"
          icon="add"
          :label="t('finance.newTransaction')"
          unelevated
          @click="openCreate"
        />
      </div>
    </div>

    <div class="row q-col-gutter-sm q-mb-md">
      <div class="col-12 col-sm-6 col-lg-3">
        <q-card flat bordered class="ec-card">
          <q-card-section>
            <div class="text-caption text-grey-7">{{ t('finance.pendingAmount') }}</div>
            <div class="text-h6">{{ formatMoney(summary.pending_amount) }}</div>
            <div class="text-caption text-grey-6">{{ t('finance.transactionsCount', { count: summary.pending_count }) }}</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-sm-6 col-lg-3">
        <q-card flat bordered class="ec-card">
          <q-card-section>
            <div class="text-caption text-grey-7">{{ t('finance.overdueAmount') }}</div>
            <div class="text-h6 text-negative">{{ formatMoney(summary.overdue_amount) }}</div>
            <div class="text-caption text-grey-6">{{ t('finance.overdueCount', { count: summary.overdue_count }) }}</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-sm-6 col-lg-3">
        <q-card flat bordered class="ec-card">
          <q-card-section>
            <div class="text-caption text-grey-7">{{ t('finance.completedAmount') }}</div>
            <div class="text-h6 text-positive">{{ formatMoney(summary.completed_amount) }}</div>
            <div class="text-caption text-grey-6">{{ t('finance.completedCount', { count: summary.completed_count }) }}</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-sm-6 col-lg-3">
        <q-card flat bordered class="ec-card">
          <q-card-section>
            <div class="text-caption text-grey-7">{{ t('finance.allTransactions') }}</div>
            <div class="text-h6">{{ summary.total_transactions }}</div>
            <div class="text-caption text-grey-6">{{ t('finance.currentDataset') }}</div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <div class="row q-col-gutter-sm q-mb-md">
      <div class="col-12 col-sm-6 col-lg-3">
        <q-card flat bordered class="ec-card">
          <q-card-section>
            <div class="text-caption text-grey-7">{{ t('finance.projectedJobValue') }}</div>
            <div class="text-h6">{{ formatMoney(jobInsights.projected_total_value) }}</div>
            <div class="text-caption text-grey-6">{{ t('finance.jobsTotal', { count: jobInsights.jobs_total }) }}</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-sm-6 col-lg-3">
        <q-card flat bordered class="ec-card">
          <q-card-section>
            <div class="text-caption text-grey-7">{{ t('finance.activePipeline') }}</div>
            <div class="text-h6">{{ formatMoney(jobInsights.projected_active_value) }}</div>
            <div class="text-caption text-grey-6">{{ t('finance.activeJobsCount', { count: jobInsights.jobs_active }) }}</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-sm-6 col-lg-3">
        <q-card flat bordered class="ec-card">
          <q-card-section>
            <div class="text-caption text-grey-7">{{ t('finance.collectedTransactions') }}</div>
            <div class="text-h6 text-positive">{{ formatMoney(jobInsights.collected_total) }}</div>
            <div class="text-caption text-grey-6">{{ t('finance.fromCompletedTransactions') }}</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-sm-6 col-lg-3">
        <q-card flat bordered class="ec-card">
          <q-card-section>
            <div class="text-caption text-grey-7">{{ t('finance.completedJobsValue') }}</div>
            <div class="text-h6">{{ formatMoney(jobInsights.projected_completed_value) }}</div>
            <div class="text-caption text-grey-6">{{ t('finance.completedJobsCount', { count: jobInsights.jobs_completed }) }}</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-sm-6 col-lg-3">
        <q-card flat bordered class="ec-card">
          <q-card-section>
            <div class="text-caption text-grey-7">{{ t('finance.salesPaid') }}</div>
            <div class="text-h6 text-positive">{{ formatMoney(jobInsights.sales_paid_value) }}</div>
            <div class="text-caption text-grey-6">{{ t('finance.paidJobsCount', { count: jobInsights.invoice_paid_jobs }) }}</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-sm-6 col-lg-3">
        <q-card flat bordered class="ec-card">
          <q-card-section>
            <div class="text-caption text-grey-7">{{ t('finance.salesUnpaid') }}</div>
            <div class="text-h6 text-negative">{{ formatMoney(jobInsights.sales_unpaid_value) }}</div>
            <div class="text-caption text-grey-6">{{ t('finance.unpaidJobsCount', { count: jobInsights.invoice_unpaid_jobs }) }}</div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <div class="row q-col-gutter-sm q-mb-md">
      <div class="col-12 col-sm-6 col-lg-4">
        <q-card flat bordered class="ec-card">
          <q-card-section>
            <div class="text-caption text-grey-7">{{ t('finance.warehouseProductsValue') }}</div>
            <div class="text-h6">{{ formatMoney(summary.warehouse_products_value) }}</div>
            <div class="text-caption text-grey-6">{{ t('finance.fromProductReplaceCost') }}</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-sm-6 col-lg-4">
        <q-card flat bordered class="ec-card">
          <q-card-section>
            <div class="text-caption text-grey-7">{{ t('finance.warehouseDevicesValue') }}</div>
            <div class="text-h6">{{ formatMoney(summary.warehouse_devices_value) }}</div>
            <div class="text-caption text-grey-6">{{ t('finance.fromDeviceReplaceCost') }}</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-sm-6 col-lg-4">
        <q-card flat bordered class="ec-card">
          <q-card-section>
            <div class="text-caption text-grey-7">{{ t('finance.warehouseTotalValue') }}</div>
            <div class="text-h6">{{ formatMoney(summary.warehouse_total_value) }}</div>
            <div class="text-caption text-grey-6">{{ t('finance.productsPlusDevices') }}</div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <q-card flat bordered class="ec-card q-mb-md">
      <q-card-section>
        <div class="text-subtitle2 q-mb-sm">{{ t('finance.topJobsByProjectedValue') }}</div>
        <q-table
          :rows="jobInsights.top_jobs || []"
          :columns="jobColumns"
          row-key="job_id"
          dense
          flat
          bordered
          :pagination="{ rowsPerPage: 8 }"
          hide-bottom
        >
          <template #body-cell-estimated_value="props">
            <q-td :props="props">{{ formatMoney(props.value) }}</q-td>
          </template>
          <template #body-cell-completed_transaction_total="props">
            <q-td :props="props">{{ formatMoney(props.value) }}</q-td>
          </template>
          <template #body-cell-status="props">
            <q-td :props="props">
              <q-badge :color="props.value === 'completed' ? 'positive' : (props.value === 'cancelled' ? 'grey' : 'info')" :label="props.value" />
            </q-td>
          </template>
          <template #body-cell-completion_percent="props">
            <q-td :props="props">{{ props.value }}%</q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <q-card flat bordered class="ec-card q-mb-md">
      <q-card-section class="q-gutter-sm row items-end">
        <q-select
          v-model="filters.status"
          :options="statusOptions"
          emit-value
          map-options
          outlined
          dense
          clearable
          :label="t('finance.status')"
          class="col-12 col-sm-6 col-md-3"
        />
        <q-select
          v-model="filters.transaction_type"
          :options="typeOptions"
          emit-value
          map-options
          outlined
          dense
          clearable
          :label="t('finance.type')"
          class="col-12 col-sm-6 col-md-3"
        />
        <q-select
          v-model="filters.job_id"
          :options="jobOptions"
          emit-value
          map-options
          outlined
          dense
          clearable
          :label="t('finance.job')"
          class="col-12 col-sm-6 col-md-3"
        />
        <q-input
          v-model="filters.customer_name"
          outlined
          dense
          clearable
          :label="t('finance.customerContains')"
          class="col-12 col-sm-6 col-md-3"
        />
        <q-input v-model="filters.from_date" type="date" outlined dense :label="t('finance.from')" class="col-12 col-sm-6 col-md-3" />
        <q-input v-model="filters.to_date" type="date" outlined dense :label="t('finance.to')" class="col-12 col-sm-6 col-md-3" />
        <q-checkbox v-model="filters.overdue_only" :label="t('finance.overdueOnly')" class="col-12 col-sm-6 col-md-2" />
        <div class="col-12 col-sm-6 col-md-4 row justify-end q-gutter-sm">
          <q-btn flat color="secondary" :label="t('finance.reset')" @click="resetFilters" />
          <q-btn color="primary" :label="t('finance.applyFilters')" unelevated @click="applyFilters" :loading="isLoading" />
        </div>
      </q-card-section>
    </q-card>

    <q-table
      :rows="store.transactions"
      :columns="columns"
      row-key="id"
      flat
      bordered
      :loading="isLoading"
      :pagination="{ rowsPerPage: 50 }"
      :rows-per-page-options="[25, 50, 100, 0]"
      class="ec-card"
    >
      <template #body-cell-transaction_type="props">
        <q-td :props="props">
          <q-badge color="primary" text-color="white" :label="typeLabel(props.value)" />
        </q-td>
      </template>

      <template #body-cell-status="props">
        <q-td :props="props">
          <q-badge :color="statusColor(props.row)" :label="statusLabel(props.value, props.row.is_overdue)" />
        </q-td>
      </template>

      <template #body-cell-amount="props">
        <q-td :props="props">{{ formatMoney(props.value, props.row.currency) }}</q-td>
      </template>

      <template #body-cell-transaction_date="props">
        <q-td :props="props">{{ formatDateTime(props.value) }}</q-td>
      </template>

      <template #body-cell-due_date="props">
        <q-td :props="props">
          <span>{{ formatDateTime(props.value) }}</span>
          <span v-if="props.row.is_overdue" class="text-negative q-ml-xs">({{ t('finance.daysOverdue', { days: props.row.days_overdue }) }})</span>
        </q-td>
      </template>

      <template #body-cell-actions="props">
        <q-td :props="props" auto-width>
          <q-btn
            v-if="authStore.canEdit && props.row.status !== 'completed'"
            flat
            round
            dense
            icon="done"
            color="positive"
            @click="settle(props.row)"
          />
          <q-btn
            v-if="authStore.canEdit"
            flat
            round
            dense
            icon="edit"
            color="primary"
            @click="openEdit(props.row)"
          />
          <q-btn
            v-if="authStore.canEdit"
            flat
            round
            dense
            icon="delete"
            color="negative"
            @click="remove(props.row)"
          />
        </q-td>
      </template>
    </q-table>

    <q-dialog v-model="dialogOpen" persistent>
      <q-card style="min-width: 680px; max-width: 95vw" class="ec-card">
        <q-card-section>
          <div class="text-h6">{{ editing ? t('finance.editTransaction') : t('finance.newTransaction') }}</div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-form ref="formRef" @submit.prevent="saveTransaction">
            <div class="row q-col-gutter-sm">
              <div class="col-12 col-md-6">
                <q-select
                  v-model="form.transaction_type"
                  :options="typeOptions"
                  emit-value
                  map-options
                  outlined
                  dense
                  :label="t('finance.type')"
                  :rules="[v => !!v || t('login.required')]"
                />
              </div>
              <div class="col-12 col-md-6">
                <q-select
                  v-model="form.status"
                  :options="statusOptions"
                  emit-value
                  map-options
                  outlined
                  dense
                  :label="t('finance.status')"
                  :rules="[v => !!v || t('login.required')]"
                />
              </div>
            </div>

            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-12 col-md-6">
                <q-input
                  v-model.number="form.amount"
                  type="number"
                  step="0.01"
                  min="0"
                  outlined
                  dense
                  :label="t('finance.amount')"
                  :rules="[v => Number(v) >= 0 || t('finance.mustBeNonNegative')]"
                />
              </div>
              <div class="col-12 col-md-6">
                <q-select
                  v-model="form.currency"
                  :options="currencyOptions"
                  emit-value
                  map-options
                  use-input
                  fill-input
                  input-debounce="0"
                  outlined
                  dense
                  :label="t('finance.currency')"
                  :rules="[v => (v || '').length === 3 || t('finance.currencyThreeLetters')]"
                  @filter="filterCurrencySelectOptions"
                />
              </div>
            </div>

            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-12 col-md-6">
                <q-select
                  v-model="form.job_id"
                  :options="jobOptions"
                  emit-value
                  map-options
                  clearable
                  outlined
                  dense
                  :label="t('finance.job')"
                />
              </div>
              <div class="col-12 col-md-6">
                <q-input v-model="form.transaction_date" type="datetime-local" outlined dense :label="t('finance.transactionDate')" />
              </div>
            </div>

            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-12 col-md-6">
                <q-input v-model="form.due_date" type="datetime-local" outlined dense :label="t('finance.dueDate')" />
              </div>
            </div>
          </q-form>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" v-close-popup />
          <q-btn color="primary" unelevated :label="t('app.actions.save')" :loading="saving" @click="saveTransaction" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'

import { useAuthStore } from '../stores/auth'
import { useFinanceStore } from '../stores/finance'
import { useJobsStore } from '../stores/jobs'
import { useSettingsStore } from '../stores/settings'
import {
  CURRENCY_OPTIONS,
  currencyOptionFor,
  filterCurrencyOptions,
  normalizeCurrencyCode,
} from '../constants/currencies'

const $q = useQuasar()
const authStore = useAuthStore()
const store = useFinanceStore()
const jobsStore = useJobsStore()
const settingsStore = useSettingsStore()
const { t, locale } = useI18n()

const formRef = ref(null)
const dialogOpen = ref(false)
const editing = ref(null)
const saving = ref(false)

const filters = reactive({
  status: null,
  transaction_type: null,
  job_id: null,
  customer_name: '',
  from_date: '',
  to_date: '',
  overdue_only: false,
})

const form = reactive({
  job_id: null,
  transaction_type: 'payment',
  status: 'pending',
  amount: 0,
  currency: normalizeCurrencyCode(settingsStore.companyProfile?.currency, 'SEK'),
  transaction_date: '',
  due_date: '',
})
const currencyOptions = ref([...CURRENCY_OPTIONS])
const selectedCompanyCurrency = computed(() => normalizeCurrencyCode(settingsStore.companyProfile?.currency, 'SEK'))

function ensureCurrencyOption(value) {
  const option = currencyOptionFor(value)
  if (!currencyOptions.value.some(item => item.value === option.value)) {
    currencyOptions.value = [...currencyOptions.value, option]
  }
}

function filterCurrencySelectOptions(val, update) {
  update(() => {
    currencyOptions.value = filterCurrencyOptions(CURRENCY_OPTIONS, val)
    ensureCurrencyOption(form.currency)
  })
}

const statusOptions = computed(() => [
  { label: t('finance.statusPending'), value: 'pending' },
  { label: t('finance.statusCompleted'), value: 'completed' },
  { label: t('finance.statusFailed'), value: 'failed' },
  { label: t('finance.statusCancelled'), value: 'cancelled' },
  { label: t('finance.statusRefunded'), value: 'refunded' },
])

const typeOptions = computed(() => [
  { label: t('finance.typeRental'), value: 'rental' },
  { label: t('finance.typeDeposit'), value: 'deposit' },
  { label: t('finance.typePayment'), value: 'payment' },
  { label: t('finance.typeRefund'), value: 'refund' },
  { label: t('finance.typeFee'), value: 'fee' },
  { label: t('finance.typeDiscount'), value: 'discount' },
])

const columns = computed(() => [
  { name: 'id', label: 'ID', field: 'id', align: 'left', sortable: true },
  { name: 'transaction_type', label: t('finance.type'), field: 'transaction_type', align: 'left', sortable: true },
  { name: 'status', label: t('finance.status'), field: 'status', align: 'left', sortable: true },
  { name: 'amount', label: t('finance.amount'), field: 'amount', align: 'right', sortable: true },
  { name: 'currency', label: t('finance.currencyShort'), field: 'currency', align: 'left', sortable: true },
  { name: 'job_code', label: t('finance.job'), field: 'job_code', align: 'left', sortable: true },
  { name: 'customer_name', label: t('finance.customer'), field: 'customer_name', align: 'left', sortable: true },
  { name: 'transaction_date', label: t('finance.transactionDate'), field: 'transaction_date', align: 'left', sortable: true },
  { name: 'due_date', label: t('finance.dueDate'), field: 'due_date', align: 'left', sortable: true },
  { name: 'actions', label: '', field: 'id', align: 'right' },
])

const jobColumns = computed(() => [
  { name: 'job_code', label: t('finance.job'), field: 'job_code', align: 'left' },
  { name: 'customer_name', label: t('finance.customer'), field: 'customer_name', align: 'left' },
  { name: 'status', label: t('finance.status'), field: 'status', align: 'left' },
  { name: 'requirement_lines', label: t('finance.reqLines'), field: 'requirement_lines', align: 'right' },
  { name: 'completion_percent', label: t('finance.pickPercent'), field: 'completion_percent', align: 'right' },
  { name: 'estimated_value', label: t('finance.projectedValue'), field: 'estimated_value', align: 'right' },
  { name: 'completed_transaction_total', label: t('finance.collected'), field: 'completed_transaction_total', align: 'right' },
])

const summary = computed(() => store.summary || {})
const jobInsights = computed(() => store.jobInsights || {
  jobs_total: 0,
  jobs_active: 0,
  jobs_completed: 0,
  jobs_cancelled: 0,
  projected_total_value: '0.00',
  projected_active_value: '0.00',
  projected_completed_value: '0.00',
  sales_total_value: '0.00',
  sales_paid_value: '0.00',
  sales_unpaid_value: '0.00',
  invoice_paid_jobs: 0,
  invoice_unpaid_jobs: 0,
  transaction_total: '0.00',
  collected_total: '0.00',
  top_jobs: [],
})
const isLoading = computed(() => store.loading || store.summaryLoading || store.jobInsightsLoading)
const jobOptions = computed(() => {
  return (jobsStore.jobs || []).map(job => ({
    label: `${job.job_code}${job.customer_name ? ` - ${job.customer_name}` : ''}`,
    value: job.id,
  }))
})

function formatMoney(value, currency) {
  const amount = Number(value || 0)
  const curr = normalizeCurrencyCode(currency || selectedCompanyCurrency.value || summary.value.currency, 'SEK')
  try {
    return new Intl.NumberFormat('sv-SE', {
      style: 'currency',
      currency: curr,
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

function formatDateTime(value) {
  if (!value) return '-'
  const dt = new Date(value)
  if (Number.isNaN(dt.getTime())) return '-'
  return dt.toLocaleString('sv-SE')
}

function statusColor(row) {
  if (row.is_overdue) return 'negative'
  if (row.status === 'completed') return 'positive'
  if (row.status === 'pending') return 'warning'
  if (row.status === 'failed') return 'negative'
  if (row.status === 'cancelled') return 'grey'
  if (row.status === 'refunded') return 'info'
  return 'primary'
}

function statusLabel(value, isOverdue) {
  if (isOverdue && value !== 'completed') return t('finance.overdue')
  const hit = statusOptions.value.find(item => item.value === value)
  return hit?.label || value || t('finance.unknown')
}

function typeLabel(value) {
  const hit = typeOptions.value.find(item => item.value === value)
  return hit?.label || value || t('finance.unknown')
}

function toDateTimeLocal(value) {
  if (!value) return ''
  const localeCode = locale.value === 'sv' ? 'sv-SE' : 'en-US'
  return new Date(value).toLocaleString(localeCode)
  if (Number.isNaN(dt.getTime())) return ''
  const yyyy = dt.getFullYear()
  const mm = `${dt.getMonth() + 1}`.padStart(2, '0')
  const dd = `${dt.getDate()}`.padStart(2, '0')
  const hh = `${dt.getHours()}`.padStart(2, '0')
  const min = `${dt.getMinutes()}`.padStart(2, '0')
  return `${yyyy}-${mm}-${dd}T${hh}:${min}`
}

function parseDateTimeLocal(value) {
  if (!value) return null
  const dt = new Date(value)
  if (Number.isNaN(dt.getTime())) return null
  return dt.toISOString()
}

async function reload() {
  await Promise.all([
    jobsStore.fetchAll(),
    store.fetchSummary(),
    store.fetchJobInsights(),
    store.fetchTransactions({ ...filters }),
  ])
}

async function applyFilters() {
  try {
    await store.fetchTransactions({ ...filters })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || error?.message || t('finance.failedFilterTransactions') })
  }
}

async function resetFilters() {
  filters.status = null
  filters.transaction_type = null
  filters.job_id = null
  filters.customer_name = ''
  filters.from_date = ''
  filters.to_date = ''
  filters.overdue_only = false
  await applyFilters()
}

function resetForm() {
  editing.value = null
  form.job_id = null
  form.transaction_type = 'payment'
  form.status = 'pending'
  form.amount = 0
  form.currency = selectedCompanyCurrency.value
  form.transaction_date = ''
  form.due_date = ''
  ensureCurrencyOption(form.currency)
}

function openCreate() {
  resetForm()
  dialogOpen.value = true
}

function openEdit(row) {
  editing.value = row
  form.job_id = row.job_id || null
  form.transaction_type = row.transaction_type || 'payment'
  form.status = row.status || 'pending'
  form.amount = Number(row.amount || 0)
  form.currency = normalizeCurrencyCode(row.currency || selectedCompanyCurrency.value, 'SEK')
  ensureCurrencyOption(form.currency)
  form.transaction_date = toDateTimeLocal(row.transaction_date)
  form.due_date = toDateTimeLocal(row.due_date)
  dialogOpen.value = true
}

async function saveTransaction() {
  const ok = await formRef.value?.validate?.()
  if (ok === false) return

  saving.value = true
  try {
    const payload = {
      job_id: form.job_id || null,
      transaction_type: String(form.transaction_type || '').trim().toLowerCase(),
      status: String(form.status || '').trim().toLowerCase(),
      amount: Number(form.amount || 0),
      currency: normalizeCurrencyCode(form.currency || selectedCompanyCurrency.value, 'SEK'),
      transaction_date: parseDateTimeLocal(form.transaction_date),
      due_date: parseDateTimeLocal(form.due_date),
    }

    if (editing.value?.id) {
      await store.updateTransaction(editing.value.id, payload)
      $q.notify({ type: 'positive', message: t('finance.transactionUpdated') })
    } else {
      await store.createTransaction(payload)
      $q.notify({ type: 'positive', message: t('finance.transactionCreated') })
    }

    dialogOpen.value = false
    await Promise.all([store.fetchSummary(), store.fetchJobInsights(), store.fetchTransactions({ ...filters })])
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || error?.message || t('finance.failedSaveTransaction') })
  } finally {
    saving.value = false
  }
}

async function settle(row) {
  try {
    await store.settleTransaction(row.id)
    await Promise.all([store.fetchSummary(), store.fetchJobInsights(), store.fetchTransactions({ ...filters })])
    $q.notify({ type: 'positive', message: t('finance.transactionSettled') })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || error?.message || t('finance.failedSettleTransaction') })
  }
}

function remove(row) {
  $q.dialog({
    title: t('finance.deleteTransaction'),
    message: t('finance.deleteTransactionPrompt', { id: row.id }),
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await store.deleteTransaction(row.id)
      await Promise.all([store.fetchSummary(), store.fetchJobInsights(), store.fetchTransactions({ ...filters })])
      $q.notify({ type: 'positive', message: t('finance.transactionDeleted') })
    } catch (error) {
      $q.notify({ type: 'negative', message: error?.response?.data?.detail || error?.message || t('finance.failedDeleteTransaction') })
    }
  })
}

onMounted(async () => {
  try {
    await settingsStore.fetchCompanyProfile()
    ensureCurrencyOption(selectedCompanyCurrency.value)
    form.currency = selectedCompanyCurrency.value
    await reload()
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || error?.message || t('finance.failedLoadFinanceData') })
  }
})
</script>
