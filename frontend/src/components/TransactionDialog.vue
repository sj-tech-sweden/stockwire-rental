<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="emit('update:modelValue', $event)">
    <q-card style="width: 680px; max-width: 95vw" class="ec-card">
      <q-card-section>
        <div class="text-h6">{{ editing ? t('finance.editTransaction') : t('finance.newTransaction') }}</div>
      </q-card-section>

      <q-card-section class="q-pt-none">
        <q-form ref="formRef" @submit.prevent="save">
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
        <q-btn color="primary" unelevated :label="t('app.actions.save')" :loading="saving" @click="save" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useFinanceStore } from '../stores/finance'
import { useJobsStore } from '../stores/jobs'
import { useAuthStore } from '../stores/auth'
import { useSettingsStore } from '../stores/settings'
import {
  CURRENCY_OPTIONS,
  currencyOptionFor,
  filterCurrencyOptions,
  normalizeCurrencyCode,
} from '../constants/currencies'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  transaction: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const $q = useQuasar()
const { t } = useI18n()
const financeStore = useFinanceStore()
const jobsStore = useJobsStore()
const authStore = useAuthStore()
const settingsStore = useSettingsStore()

const formRef = ref(null)
const editing = ref(null)
const saving = ref(false)
const currencyOptions = ref([...CURRENCY_OPTIONS])

const selectedCompanyCurrency = computed(() => normalizeCurrencyCode(settingsStore.companyProfile?.currency, 'SEK'))

const form = reactive({
  job_id: null,
  transaction_type: 'payment',
  status: 'pending',
  amount: 0,
  currency: normalizeCurrencyCode(settingsStore.companyProfile?.currency, 'SEK'),
  transaction_date: '',
  due_date: '',
})

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

const jobOptions = computed(() => {
  return (jobsStore.jobs || []).map(job => ({
    label: `${job.job_code}${job.customer_name ? ` - ${job.customer_name}` : ''}`,
    value: job.id,
  }))
})

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

function toDateTimeLocal(value) {
  if (!value) return ''
  const dt = new Date(value)
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

function openEdit(transaction) {
  editing.value = transaction
  form.job_id = transaction.job_id || null
  form.transaction_type = transaction.transaction_type || 'payment'
  form.status = transaction.status || 'pending'
  form.amount = Number(transaction.amount || 0)
  form.currency = normalizeCurrencyCode(transaction.currency || selectedCompanyCurrency.value, 'SEK')
  ensureCurrencyOption(form.currency)
  form.transaction_date = toDateTimeLocal(transaction.transaction_date)
  form.due_date = toDateTimeLocal(transaction.due_date)
}

async function save() {
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
      await financeStore.updateTransaction(editing.value.id, payload)
      $q.notify({ type: 'positive', message: t('finance.transactionUpdated') })
    } else {
      await financeStore.createTransaction(payload)
      $q.notify({ type: 'positive', message: t('finance.transactionCreated') })
    }

    emit('update:modelValue', false)
    emit('saved')
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || error?.message || t('finance.failedSaveTransaction') })
  } finally {
    saving.value = false
  }
}

watch(() => props.modelValue, (open) => {
  if (open) {
    if (props.transaction) {
      openEdit(props.transaction)
    } else {
      resetForm()
    }
  }
})
</script>
