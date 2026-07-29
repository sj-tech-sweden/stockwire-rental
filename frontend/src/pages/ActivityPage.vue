<template>
  <q-page class="q-pa-md ec-page">
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">{{ t('activity.title') }}</div>
      <q-btn color="primary" icon="refresh" :label="t('home.refresh')" unelevated @click="refresh" :loading="store.loading" />
    </div>

    <div class="row q-col-gutter-sm q-mb-sm">
      <div class="col-12 col-md-3">
        <q-select v-model="entityFilter" :options="entityOptions" :label="t('activity.entity')" outlined dense emit-value map-options clearable @update:model-value="refresh" />
      </div>
      <div class="col-12 col-md-9">
        <q-input v-model="search" dense outlined clearable :placeholder="t('activity.search')" />
      </div>
    </div>

    <q-table
      :rows="filteredLogs"
      :columns="columns"
      row-key="id"
      :grid="compactGrid"
      :hide-header="compactGrid"
      flat
      bordered
      class="ec-card"
      :loading="store.loading"
      :pagination="{ rowsPerPage: 25 }"
      :rows-per-page-options="[25, 50, 100]"
    >
      <template #body-cell-created_at="props">
        <q-td :props="props">{{ formatTs(props.value) }}</q-td>
      </template>
      <template #body-cell-entity_ref="props">
        <q-td :props="props">
          <q-btn
            v-if="entityRoute(props.row)"
            flat
            dense
            no-caps
            color="primary"
            :to="entityRoute(props.row)"
            :label="entityLabel(props.row)"
          />
          <span v-else>{{ entityLabel(props.row) }}</span>
        </q-td>
      </template>
      <template #body-cell-action="props">
        <q-td :props="props"><q-badge :color="actionColor(props.row)" :label="actionLabel(props.row.action)" /></q-td>
      </template>
      <template #body-cell-message="props">
        <q-td :props="props" class="ellipsis" style="max-width: 300px">{{ messageLabel(props.row) }}</q-td>
      </template>
      <template #body-cell-user="props">
        <q-td :props="props">{{ userLabel(props.row) }}</q-td>
      </template>
      <template #item="props">
        <div class="q-pa-xs col-12">
          <q-card flat bordered>
            <q-card-section class="q-pb-sm">
              <div class="row items-center justify-between">
                <div class="text-subtitle2">{{ entityLabel(props.row) }}</div>
                <q-badge :color="actionColor(props.row)" :label="actionLabel(props.row.action)" />
              </div>
              <div class="text-caption text-grey-7">{{ formatTs(props.row.created_at) }}</div>
            </q-card-section>
            <q-card-section class="q-pt-none q-pb-sm">
              <div class="text-caption">{{ messageLabel(props.row) }}</div>
              <div class="text-caption">{{ t('activity.user') }}: {{ userLabel(props.row) }}</div>
            </q-card-section>
            <q-card-actions align="right" v-if="entityRoute(props.row)">
              <q-btn flat dense no-caps color="primary" icon="open_in_new" :label="t('activity.open')" :to="entityRoute(props.row)" />
            </q-card-actions>
          </q-card>
        </div>
      </template>
    </q-table>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'

import { useActivityStore } from '../stores/activity'
import { useCompactGrid } from '../composables/useCompactGrid'

const $q = useQuasar()
const compactGrid = useCompactGrid(1024)
const store = useActivityStore()
const { t } = useI18n()
const search = ref('')
const entityFilter = ref(null)

const entityOptions = [
  { label: t('app.nav.jobs'), value: 'job' },
  { label: t('home.products'), value: 'product' },
  { label: t('app.nav.customers'), value: 'customer' },
  { label: t('app.nav.venues'), value: 'venue' },
  { label: t('app.nav.scan'), value: 'scan' },
]

const columns = [
  { name: 'created_at', label: t('activity.time'), field: 'created_at', sortable: true, align: 'left' },
  { name: 'entity_ref', label: t('activity.entity'), field: 'entity_type', sortable: true, align: 'left' },
  { name: 'action', label: t('activity.action'), field: 'action', sortable: true, align: 'left' },
  { name: 'message', label: t('activity.message'), field: 'message', sortable: true, align: 'left' },
  { name: 'user', label: t('activity.user'), field: 'user_full_name', sortable: true, align: 'left' },
]

const filteredLogs = computed(() => {
  const term = search.value.trim().toLowerCase()
  if (!term) return store.logs
  return store.logs.filter((log) =>
    [
      log.entity_type,
      log.action,
      log.message,
      String(log.entity_id || ''),
      String(log.user_id || ''),
      String(log.user_full_name || ''),
    ]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(term))
  )
})

function formatTs(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString()
}

function actionColor(row) {
  if (row.entity_type === 'scan') {
    return row.details?.success === false ? 'negative' : 'positive'
  }
  if (row.action === 'create') return 'positive'
  if (row.action === 'update') return 'warning'
  if (row.action === 'delete') return 'negative'
  return 'primary'
}

function actionLabel(value) {
  const mapping = {
    lookup: t('activity.actionLookup'),
    scan: t('activity.actionScan'),
    create: t('activity.actionCreate'),
    update: t('activity.actionUpdate'),
    delete: t('activity.actionDelete'),
    job_in: t('activity.actionJobIn'),
    job_out: t('activity.actionJobOut'),
    move: t('activity.actionMove'),
  }
  return mapping[value] || value || t('activity.actionUnknown')
}

function messageLabel(log) {
  if (log.message_format) {
    const format = log.message_format.replace(/\./g, '_')
    const key = 'activity.messageFormat.' + format
    const params = log.message_params || {}
    return t(key, params)
  }
  return log.message || '-' || t('activity.actionUnknown')
}

function entityLabel(log) {
  const entityType = String(log.entity_type || '').trim() || 'entity'
  if (log.entity_id != null) return `${entityType} #${log.entity_id}`
  return entityType
}

function entityRoute(log) {
  if (log.entity_type === 'job' && log.entity_id != null) {
    return { path: '/jobs', query: { focusJobId: String(log.entity_id) } }
  }
  if (log.entity_type === 'product' && log.entity_id != null) {
    return { path: '/inventory', query: { tab: 'products', focusProductId: String(log.entity_id) } }
  }
  if (log.entity_type === 'customer' && log.entity_id != null) {
    return { path: '/companies', query: { focusCustomerId: String(log.entity_id) } }
  }
  if (log.entity_type === 'venue' && log.entity_id != null) {
    return { path: '/venues', query: { focusVenueId: String(log.entity_id) } }
  }
  if (log.entity_type === 'scan') {
    const deviceId = Number(log.details?.device_id || log.details?.device_details?.id || 0)
    if (deviceId > 0) {
      return { path: '/inventory', query: { tab: 'devices', focusDeviceId: String(deviceId) } }
    }

    const productId = Number(log.details?.product_id || log.details?.product_details?.id || 0)
    if (productId > 0) {
      return { path: '/inventory', query: { tab: 'products', focusProductId: String(productId) } }
    }
  }
  return null
}

function userLabel(log) {
  if (log.user_full_name) return log.user_full_name
  if (log.user_id != null) return `${t('activity.user')} #${log.user_id}`
  return '-'
}

async function refresh() {
  await store.fetchLogs(300, entityFilter.value)
}

onMounted(refresh)
</script>
