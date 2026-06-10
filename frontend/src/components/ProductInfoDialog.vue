<template>
  <q-dialog :model-value="modelValue" :maximized="isPhone" @update:model-value="emit('update:modelValue', $event)">
    <q-card :style="isPhone ? 'width: 100vw; max-width: 100vw; height: 100vh' : 'min-width: 860px; max-width: 96vw'" class="ec-card">
      <q-card-section>
        <div class="text-h6">{{ t('inventory.infoDialogs.productTitle', { sku: product?.sku || '-' }) }}</div>
        <div class="text-caption text-grey-7">{{ product?.name || '-' }}</div>
      </q-card-section>

      <q-card-section class="q-pt-none" :style="isPhone ? 'max-height: calc(100vh - 140px); overflow: auto;' : ''">
        <div class="row q-col-gutter-sm q-mb-md">
          <div class="col-12 col-md-4"><q-badge color="positive" text-color="white" :label="t('inventory.infoDialogs.available', { count: availability.available })" /></div>
          <div class="col-12 col-md-4"><q-badge color="warning" text-color="black" :label="t('inventory.infoDialogs.reserved', { count: availability.reserved })" /></div>
          <div class="col-12 col-md-4"><q-badge color="info" text-color="white" :label="t('inventory.infoDialogs.inUse', { count: availability.in_use })" /></div>
        </div>

        <q-list bordered separator class="rounded-borders q-mb-md">
          <q-item>
            <q-item-section>
              <q-item-label>Type: {{ product?.product_type || '-' }}</q-item-label>
              <q-item-label caption>
                {{ t('inventory.infoDialogs.categoryBrandManufacturer', { category: product?.category || t('inventory.uncategorized'), brand: product?.brand || '-', manufacturer: product?.manufacturer || '-' }) }}
              </q-item-label>
              <q-item-label caption>
                {{
                  t('inventory.infoDialogs.dailyRateMaintenanceInterval', {
                    dailyRate: formatMoney(product?.daily_rate),
                    days: product?.maintenance_interval_days ?? '-'
                  })
                }}
              </q-item-label>
              <q-item-label caption>
                {{ t('inventory.infoDialogs.replaceCost', {
                  replaceCost: formatMoney(product?.replace_cost)
                }) }}
              </q-item-label>
              <q-item-label caption>
                {{ t('inventory.infoDialogs.weightSize', { weight: product?.weight_kg ?? '-', height: product?.height_cm ?? '-', width: product?.width_cm ?? '-', depth: product?.depth_cm ?? '-' }) }}
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
                :aria-label="isPhone ? 'Edit product' : void 0"
                @click="emit('edit-product')"
              />
            </q-item-section>
          </q-item>
        </q-list>

        <div class="text-subtitle2 q-mb-sm">{{ t('inventory.infoDialogs.linkedDevices') }}</div>
        <q-list bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="row in linkedDevices" :key="row.id">
            <q-item-section>
              <q-item-label>{{ row.asset_tag }}</q-item-label>
              <q-item-label caption>
                {{ t('inventory.infoDialogs.deviceStatusConditionLocation', {
                  status: row.status,
                  condition: row.condition || t('inventory.infoDialogs.notAvailable'),
                  location: row.case_asset_tag
                    ? t('inventory.infoDialogs.caseLocation', { assetTag: row.case_asset_tag })
                    : (zoneNameById(row.location_zone_id) || t('inventory.infoDialogs.unassigned')),
                }) }}
              </q-item-label>
            </q-item-section>
            <q-item-section side top>
              <div class="row no-wrap items-center q-gutter-xs">
                <q-btn
                  flat
                  dense
                  :round="isPhone"
                  :color="infoActionColor"
                  icon="info"
                  :label="isPhone ? void 0 : 'Info'"
                  :aria-label="isPhone ? 'Open device info' : void 0"
                  @click="emit('view-device', row.id)"
                />
                <q-btn
                  flat
                  dense
                  :round="isPhone"
                  color="primary"
                  icon="edit"
                  :label="isPhone ? void 0 : 'Edit'"
                  :aria-label="isPhone ? 'Edit device' : void 0"
                  @click="emit('edit-device', row.id)"
                />
              </div>
            </q-item-section>
          </q-item>
          <q-item v-if="!linkedDevices.length">
            <q-item-section><q-item-label caption>{{ t('inventory.infoDialogs.noDevicesLinkedToProduct') }}</q-item-label></q-item-section>
          </q-item>
        </q-list>

        <div class="text-subtitle2 q-mb-sm">{{ t('inventory.infoDialogs.linkedJobs') }}</div>
        <q-list bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="row in linkedJobs" :key="`product-job-${row.job_id}`">
            <q-item-section>
              <q-item-label>{{ row.job_code || `Job #${row.job_id}` }}</q-item-label>
              <q-item-label caption>
                {{ t('inventory.infoDialogs.requiredPicked', { required: row.quantity_required_total, picked: row.quantity_picked_total }) }}
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
            <q-item-section><q-item-label caption>{{ t('inventory.infoDialogs.noLinkedJobsForProduct') }}</q-item-label></q-item-section>
          </q-item>
        </q-list>

        <div v-if="infoCustomFieldValues.length" class="text-subtitle2 q-mb-sm">Custom Fields</div>
        <q-list v-if="infoCustomFieldValues.length" bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="field in infoCustomFieldValues" :key="field.field_definition_id">
            <q-item-section>
              <q-item-label>{{ field.label }}</q-item-label>
              <q-item-label caption>{{ field.value ?? '-' }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <EntityAttachmentsPanel
          entity-type="product"
          :entity-id="product?.id || null"
          :title="t('inventory.infoDialogs.productDocuments')"
          default-category="product-document"
          :read-only="true"
        />
      </q-card-section>

      <q-card-actions :align="isPhone ? 'stretch' : 'right'" :class="isPhone ? 'q-pa-md bg-grey-2' : ''">
        <q-space />
        <q-btn flat :class="isPhone ? 'full-width' : ''" :label="t('app.actions.close')" @click="emit('update:modelValue', false)" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useInventoryStore } from '../stores/inventory'
import { useJobsStore } from '../stores/jobs'
import { useSettingsStore } from '../stores/settings'
import { useCustomFieldsStore } from '../stores/customFields'
import { normalizeCurrencyCode } from '../constants/currencies'
import EntityAttachmentsPanel from './EntityAttachmentsPanel.vue'

const props = defineProps({
  modelValue: Boolean,
  product: { type: Object, default: null },
})

const emit = defineEmits([
  'update:modelValue',
  'edit-product',
  'view-device',
  'edit-device',
  'open-job',
])

const $q = useQuasar()
const { t } = useI18n()
const store = useInventoryStore()
const jobsStore = useJobsStore()
const settingsStore = useSettingsStore()
const customFieldsStore = useCustomFieldsStore()

const infoCustomFieldValues = ref([])

watch(() => props.modelValue, async (open) => {
  if (open && props.product?.id) {
    if (!customFieldsStore.definitions.length) {
      await customFieldsStore.fetchDefinitions('product')
    }
    try {
      const data = await customFieldsStore.fetchEntityValues('product', props.product.id)
      infoCustomFieldValues.value = Array.isArray(data?.values) ? data.values : []
    } catch {
      infoCustomFieldValues.value = []
    }
  }
})

const isPhone = computed(() => $q.screen.lt.md)
const infoActionColor = computed(() => ($q.dark.isActive ? 'teal-4' : 'secondary'))

const zoneById = computed(() => {
  const map = new Map()
  for (const zone of store.zones) map.set(zone.id, zone)
  return map
})

function zoneNameById(id) {
  if (!id) return null
  return zoneById.value.get(id)?.name ?? null
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

const linkedDevices = computed(() => {
  if (!props.product?.id) return []
  return (store.devices || [])
    .filter(item => item.product_id === props.product.id)
    .slice()
    .sort((a, b) => String(a.asset_tag || '').localeCompare(String(b.asset_tag || '')))
})

const availability = computed(() => {
  const bucket = { available: 0, reserved: 0, in_use: 0, maintenance: 0 }
  for (const row of linkedDevices.value) {
    const status = String(row.status || '').toLowerCase()
    if (status === 'available') bucket.available += 1
    else if (status === 'reserved') bucket.reserved += 1
    else if (status === 'in_use') bucket.in_use += 1
    else if (status === 'maintenance') bucket.maintenance += 1
  }
  return bucket
})

function linkedJobsForProductId(productId) {
  const targetId = Number(productId || 0)
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
}

const linkedJobs = computed(() => linkedJobsForProductId(props.product?.id))
</script>
