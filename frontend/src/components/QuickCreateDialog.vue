<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="$emit('update:modelValue', $event)">
    <q-card style="width: 560px; max-width: 95vw" class="ec-card">
      <q-card-section>
        <div class="text-h6">{{ t('inventory.createDevices') }}</div>
        <div class="text-caption text-grey-7">{{ product?.sku }} - {{ product?.name }}</div>
      </q-card-section>
      <q-card-section class="q-pt-none">
        <div class="row q-col-gutter-sm">
          <div class="col-12 col-md-4">
            <q-input v-model.number="form.quantity" type="number" min="1" :label="t('inventory.quantity')" outlined dense />
          </div>
          <div class="col-12 col-md-8">
            <q-toggle v-model="form.auto_generate" :label="t('inventory.autoGenerateAssetTags')" color="primary" />
          </div>
          <div class="col-12 col-md-6" v-if="form.auto_generate">
            <q-input v-model="form.asset_tag_prefix" :label="t('inventory.assetTagPrefixOptional')" outlined dense />
          </div>
          <div class="col-12 col-md-6" v-else>
            <q-input v-model="form.asset_tag" :label="t('scan.assetTag')" outlined dense :rules="[v => !!v || t('inventory.requiredWhenAutoGenerateOff')]" />
          </div>
          <div class="col-12 col-md-4">
            <q-select v-model="form.status" :options="statusOptions" label="Status" outlined dense emit-value map-options />
          </div>
          <div class="col-12 col-md-4">
            <q-select v-model="form.condition" :options="conditionOptions" label="Condition" outlined dense emit-value map-options />
          </div>
          <div class="col-12 col-md-4">
            <q-select v-model="form.location_zone_id" :options="locationSelectOptions" label="Location" outlined dense emit-value map-options clearable />
          </div>
        </div>
        <q-banner v-if="error" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ error }}</q-banner>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="$emit('update:modelValue', false)" />
        <q-btn color="primary" unelevated :label="t('users.create')" :loading="saving" @click="run" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { DEVICE_STATUSES, useInventoryStore } from '../stores/inventory'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  product: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const $q = useQuasar()
const { t } = useI18n()
const store = useInventoryStore()
const saving = ref(false)
const error = ref('')
const form = ref({
  quantity: 1,
  auto_generate: true,
  asset_tag_prefix: '',
  asset_tag: '',
  status: 'available',
  condition: 'good',
  location_zone_id: null,
})

const DEVICE_STATUS_KEY_MAP = { available: 'Available', reserved: 'Reserved', in_use: 'InUse', maintenance: 'Maintenance' }
const statusOptions = DEVICE_STATUSES.map(item => ({ label: t('inventory.deviceStatus' + DEVICE_STATUS_KEY_MAP[item.value]), value: item.value }))
const conditionOptions = [
  { label: t('inventory.conditionExcellent'), value: 'excellent' },
  { label: t('inventory.conditionGood'), value: 'good' },
  { label: t('inventory.conditionFair'), value: 'fair' },
  { label: t('inventory.conditionDamaged'), value: 'damaged' },
]

function resetForm() {
  form.value = {
    quantity: 1,
    auto_generate: true,
    asset_tag_prefix: props.product?.sku || '',
    asset_tag: '',
    status: 'available',
    condition: 'good',
    location_zone_id: null,
  }
  error.value = ''
}

watch(() => props.modelValue, (open) => {
  if (open) resetForm()
})

const locationSelectOptions = computed(() => {
  const flat = [{ label: 'Unassigned', value: null }]
  const walk = (nodes, prefix = '') => {
    for (const node of nodes || []) {
      const label = prefix ? `${prefix} / ${node.name}` : node.name
      flat.push({ label, value: node.id })
      walk(node.children || [], label)
    }
  }
  walk(store.zoneTree)
  return flat
})

async function run() {
  if (!props.product) return
  if (!form.value.auto_generate && !form.value.asset_tag) {
    error.value = 'Asset tag is required when auto-generate is disabled'
    return
  }

  saving.value = true
  error.value = ''
  try {
    const payload = {
      quantity: Number(form.value.quantity || 1),
      auto_generate: !!form.value.auto_generate,
      asset_tag_prefix: form.value.asset_tag_prefix || null,
      asset_tag: form.value.asset_tag || null,
      status: form.value.status || 'available',
      condition: form.value.condition || 'good',
      location_zone_id: form.value.location_zone_id,
    }
    const devices = await store.createDevicesForProduct(props.product.id, payload)
    emit('update:modelValue', false)
    emit('saved', devices)
    $q.notify({ type: 'positive', message: `${devices.length} device(s) created` })
  } catch (err) {
    error.value = err?.response?.data?.detail || 'Failed to create devices'
  } finally {
    saving.value = false
  }
}
</script>
