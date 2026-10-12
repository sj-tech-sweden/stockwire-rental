<template>
  <div class="q-gutter-md">
    <div class="row items-center q-gutter-sm wrap">
      <q-select
        v-model="base"
        :options="currencyOptions"
        :label="t('purchasing.fxBase')"
        dense
        outlined
        emit-value
        map-options
        style="width: 160px"
      />
      <q-btn
        color="primary"
        :label="t('app.actions.save')"
        :loading="saving"
        @click="save"
      />
      <q-btn
        color="secondary"
        :label="t('purchasing.refreshFx')"
        :loading="refreshing"
        @click="refresh"
      />
    </div>

    <q-table
      :rows="rows"
      :columns="columns"
      row-key="currency"
      dense
      bordered
      flat
      hide-bottom
      :rows-per-page-options="[0]"
    >
      <template #body-cell-rate="props">
        <q-td :props="props">
          <q-input
            v-model.number="props.row.rate"
            type="number"
            dense
            borderless
            :step="0.0001"
          />
        </q-td>
      </template>
      <template #body-cell-actions="props">
        <q-td :props="props" class="text-right">
          <q-btn
            flat
            dense
            icon="delete"
            color="negative"
            @click="removeRow(props.row)"
          />
        </q-td>
      </template>
    </q-table>

    <div class="row items-center q-gutter-sm">
      <q-select
        v-model="newCurrency"
        :options="currencyOptions"
        :label="t('purchasing.fxAddCurrency')"
        dense
        outlined
        use-input
        new-value-mode="add-unique"
        style="width: 180px"
      />
      <q-btn outline :label="t('app.actions.add')" @click="addRow" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQuasar } from 'quasar'
import { api } from '../boot/axios'

const { t } = useI18n()
const $q = useQuasar()
const emit = defineEmits(['saved'])

const base = ref(null)
const companyCurrency = ref('SEK')
const rows = ref([])
const saving = ref(false)
const refreshing = ref(false)
const newCurrency = ref(null)
const currencyOptions = [
  'SEK', 'EUR', 'USD', 'GBP', 'NOK', 'DKK', 'CHF', 'PLN', 'CZK', 'HUF',
].map((c) => ({ label: c, value: c }))

const columns = [
  { name: 'currency', label: t('purchasing.currency'), field: 'currency', align: 'left' },
  { name: 'rate', label: t('purchasing.fxRate'), field: 'rate', align: 'right' },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
]

function toRows(rates) {
  return Object.entries(rates || {}).map(([currency, rate]) => ({
    currency,
    rate: rate,
  }))
}

async function load() {
  try {
    const { data: cp } = await api.get('/api/v1/settings/company-profile')
    if (cp && cp.currency) {
      companyCurrency.value = cp.currency.toUpperCase()
    }
  } catch {
    /* not fatal */
  }
  try {
    const { data } = await api.get('/api/v1/settings/fx-rates')
    // Default the base to the company's currency unless rates were already saved.
    base.value = (data.base || companyCurrency.value || 'SEK').toUpperCase()
    rows.value = toRows(data.rates)
  } catch {
    base.value = (companyCurrency.value || 'SEK').toUpperCase()
  }
}

async function save() {
  saving.value = true
  try {
    const rates = {}
    for (const r of rows.value) {
      if (r.currency) rates[r.currency.toUpperCase()] = Number(r.rate)
    }
    await api.put('/api/v1/settings/fx-rates', {
      base: (base.value || companyCurrency.value || 'SEK').toUpperCase(),
      rates,
    })
    $q.notify({ type: 'positive', message: t('purchasing.fxRatesUpdated') })
    emit('saved')
  } catch {
    $q.notify({ type: 'negative', message: t('app.actions.saveFailed') })
  } finally {
    saving.value = false
  }
}

async function refresh() {
  refreshing.value = true
  try {
    const { data } = await api.post('/api/v1/settings/fx-rates/refresh')
    base.value = data.base
    rows.value = toRows(data.rates)
    $q.notify({ type: 'positive', message: t('purchasing.fxRefreshed') })
    emit('saved')
  } catch {
    $q.notify({ type: 'negative', message: t('app.actions.saveFailed') })
  } finally {
    refreshing.value = false
  }
}

function addRow() {
  if (!newCurrency.value) return
  const code = String(newCurrency.value).toUpperCase()
  if (!rows.value.some((r) => r.currency === code)) {
    rows.value.push({ currency: code, rate: null })
  }
  newCurrency.value = null
}

function removeRow(row) {
  rows.value = rows.value.filter((r) => r !== row)
}

onMounted(load)
</script>
