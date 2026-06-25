<template>
  <q-dialog :model-value="modelValue" :maximized="isPhone" @update:model-value="emit('update:modelValue', $event)">
    <q-card :style="isPhone ? 'width: 100vw; max-width: 100vw; height: 100vh' : 'min-width: 860px; max-width: 96vw'" class="ec-card">
      <q-card-section class="row items-start no-wrap">
        <div>
          <div class="text-h6">Rental Info · {{ product?.sku || '-' }}</div>
          <div class="text-caption text-grey-7">{{ product?.name || '-' }}</div>
        </div>
        <q-space />
        <q-btn
          v-if="isPhone"
          flat
          round
          dense
          icon="close"
          :aria-label="t('app.actions.close')"
          @click="emit('update:modelValue', false)"
        />
      </q-card-section>

      <q-card-section class="q-pt-none" :style="isPhone ? 'max-height: calc(100vh - 140px); overflow: auto;' : ''">
        <q-list bordered separator class="rounded-borders q-mb-md">
          <q-item>
            <q-item-section>
              <q-item-label>ID: {{ product?.id || '-' }} · Supplier: {{ product?.supplier_name || '-' }}</q-item-label>
              <q-item-label caption>
                Category: {{ product?.category || '-' }} · Supplier price: {{ formatMoney(product?.rental_price) }} · Client price: {{ formatMoney(product?.daily_rate) }}
              </q-item-label>
              <q-item-label caption>
                Eventory source: {{ product?.external_source || '-' }} · Link: {{ eventoryInstanceLabelById(product?.external_reference) }}
              </q-item-label>
              <q-item-label caption>
                Eventory available qty: {{ Number(product?.eventory_available_qty || 0) }}
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-btn
                flat
                dense
                :round="isPhone"
                color="primary"
                icon="edit"
                :label="isPhone ? void 0 : 'Edit'"
                :aria-label="isPhone ? 'Edit rental product' : void 0"
                @click="emit('edit-product')"
              />
            </q-item-section>
          </q-item>
        </q-list>

        <div class="text-subtitle2 q-mb-sm">Linked Jobs</div>
        <q-list bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="row in linkedJobs" :key="`rental-job-${row.job_id}`">
            <q-item-section>
              <q-item-label>{{ row.job_code || `Job #${row.job_id}` }}</q-item-label>
              <q-item-label caption>
                Required: {{ row.quantity_required_total }} · Picked: {{ row.quantity_picked_total }}
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-btn
                flat
                dense
                :round="isPhone"
                color="primary"
                icon="edit"
                :label="isPhone ? void 0 : 'Edit'"
                :aria-label="isPhone ? 'Edit linked job' : void 0"
                @click="emit('open-job', row.job_id)"
              />
            </q-item-section>
          </q-item>
          <q-item v-if="!linkedJobs.length">
            <q-item-section><q-item-label caption>No linked jobs found for this rental product.</q-item-label></q-item-section>
          </q-item>
        </q-list>

        <EntityAttachmentsPanel
          entity-type="product"
          :entity-id="product?.id || null"
          title="Rental Documents"
          default-category="rental-document"
          :read-only="true"
        />
      </q-card-section>

      <q-card-actions :align="isPhone ? 'stretch' : 'right'" :class="isPhone ? 'q-pa-md bg-grey-2' : ''">
        <q-space />
        <q-btn flat :class="isPhone ? 'full-width' : ''" label="Close" @click="emit('update:modelValue', false)" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useSettingsStore } from '../stores/settings'
import { useJobsStore } from '../stores/jobs'
import { normalizeCurrencyCode } from '../constants/currencies'
import EntityAttachmentsPanel from './EntityAttachmentsPanel.vue'

const props = defineProps({
  modelValue: Boolean,
  product: { type: Object, default: null },
})

const emit = defineEmits([
  'update:modelValue',
  'edit-product',
  'open-job',
])

const $q = useQuasar()
const { t } = useI18n()
const settingsStore = useSettingsStore()
const jobsStore = useJobsStore()

const isPhone = computed(() => $q.screen.lt.md)

function findEventoryInstanceById(instanceId) {
  const key = String(instanceId || '').trim()
  if (!key) return null
  return (settingsStore.integrations?.eventory_instances || []).find(instance => String(instance.id || '').trim() === key) || null
}

function eventoryInstanceLabelById(instanceId) {
  const linked = findEventoryInstanceById(instanceId)
  if (!linked) return instanceId || 'Unknown'
  return linked.name || linked.id
}

function formatMoney(value) {
  const amount = Number(value || 0)
  if (!Number.isFinite(amount)) return '0.00'
  const currentCurrency = normalizeCurrencyCode(settingsStore.companyProfile?.currency, 'SEK')
  try {
    return new Intl.NumberFormat('sv-SE', {
      style: 'currency',
      currency: currentCurrency,
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

const linkedJobs = computed(() => {
  const targetId = Number(props.product?.id || 0)
  if (!targetId) return []

  const jobsById = new Map((jobsStore.jobs || []).map(job => [job.id, job]))
  const bucket = new Map()

  for (const requirement of jobsStore.requirements || []) {
    if (Number(requirement?.product_id || 0) !== targetId) continue
    const jobId = Number(requirement?.job_id || 0)
    if (!jobId) continue

    const existing = bucket.get(jobId) || {
      job_id: jobId,
      job_code: jobsById.get(jobId)?.job_code || null,
      quantity_required_total: 0,
      quantity_picked_total: 0,
      start_date: jobsById.get(jobId)?.start_date || null,
      end_date: jobsById.get(jobId)?.end_date || null,
      status: jobsById.get(jobId)?.status || null,
    }

    existing.quantity_required_total += Math.max(Number(requirement?.quantity_required || 0), 0)
    existing.quantity_picked_total += Math.max(Number(requirement?.quantity_picked || 0), 0)
    bucket.set(jobId, existing)
  }

  return [...bucket.values()].sort((a, b) => {
    const startA = String(a.start_date || '')
    const startB = String(b.start_date || '')
    return startB.localeCompare(startA)
  })
})
</script>
