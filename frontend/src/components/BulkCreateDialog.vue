<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="$emit('update:modelValue', $event)">
    <q-card style="width: 520px; max-width: 95vw" class="ec-card">
      <q-card-section>
        <div class="text-h6">{{ tr('inventory.bulkCreateSubzones.title', 'Create multiple subzones') }}</div>
        <div class="text-caption text-grey-7">{{ tr('inventory.bulkCreateSubzones.hint', 'Enter one subzone name per line. These will be created as children of the chosen location.') }}</div>
      </q-card-section>
      <q-card-section class="q-pt-none">
        <div class="q-mb-sm">
          <q-input type="textarea" autogrow v-model="text" :label="tr('inventory.bulkCreateSubzones.names', 'Subzone names (one per line)')" outlined dense />
        </div>
        <div class="row q-col-gutter-sm q-mb-sm">
          <div class="col-12 col-md-6">
            <q-select v-model="zoneType" :options="locationTypeOptions" :label="t('inventory.type')" outlined dense emit-value map-options />
          </div>
          <div class="col-12 col-md-6">
            <q-toggle v-model="isActive" :label="t('settings.auth.active')" color="primary" />
          </div>
        </div>
        <div class="row q-col-gutter-sm q-mb-sm">
          <div class="col-12 col-md-6">
            <q-toggle v-model="interpretRanges" :label="tr('inventory.bulkCreateSubzones.interpretRanges', 'Interpret ranges (A-D, 01-05)')" color="primary" />
          </div>
          <div class="col-12 col-md-6">
            <q-toggle v-model="autoGenerateCode" :label="tr('inventory.bulkCreateSubzones.autoGenerateCode', 'Auto-generate codes from names')" color="primary" />
          </div>
        </div>
        <q-banner v-if="error" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ error }}</q-banner>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="$emit('update:modelValue', false)" />
        <q-btn color="primary" unelevated :label="tr('inventory.create', 'Create')" :loading="saving" @click="save" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQuasar } from 'quasar'
import { useInventoryStore } from '../stores/inventory'
import { slugify } from '../utils/slugify'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  parentZone: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const { t } = useI18n()
const $q = useQuasar()
const store = useInventoryStore()

const ZONE_CODE_MAX_LENGTH = 50

const saving = ref(false)
const error = ref('')
const text = ref('')
const zoneType = ref('rack')
const isActive = ref(true)
const interpretRanges = ref(true)
const autoGenerateCode = ref(true)

watch(() => props.modelValue, (open) => {
  if (open) {
    text.value = ''
    zoneType.value = locationTypeOptions.value[0]?.value || 'rack'
    isActive.value = true
    interpretRanges.value = true
    autoGenerateCode.value = true
    error.value = ''
  }
})

function tr(key, fallback) {
  try {
    const val = t(key)
    if (!val || val === key) return fallback || key
    return val
  } catch (e) {
    return fallback || key
  }
}

const locationTypeOptions = computed(() => {
  const values = Array.isArray(store.locationTypes) && store.locationTypes.length
    ? store.locationTypes
    : ['rack', 'shelf', 'bin', 'pallet', 'stage', 'truck', 'warehouse', 'workshop']
  return values.map(value => ({ label: value, value }))
})

async function save() {
  if (!props.parentZone) return

  const rawLines = String(text.value || '').split(/\r?\n/).map(s => s.trim()).filter(Boolean)
  const lines = []

  for (const line of rawLines) {
    if (interpretRanges.value) {
      const mAlpha = line.match(/^([A-Za-z])\s*-\s*([A-Za-z])$/)
      const mNum = line.match(/^(\d+)\s*-\s*(\d+)$/)
      if (mAlpha) {
        let a = mAlpha[1]
        let b = mAlpha[2]
        const start = a.toLowerCase().charCodeAt(0)
        const end = b.toLowerCase().charCodeAt(0)
        const step = start <= end ? 1 : -1
        const preserveUpper = (a[0] >= 'A' && a[0] <= 'Z')
        for (let c = start; step === 1 ? c <= end : c >= end; c += step) {
          const ch = String.fromCharCode(c)
          lines.push(preserveUpper ? ch.toUpperCase() : ch)
        }
        continue
      } else if (mNum) {
        const start = Number(mNum[1])
        const end = Number(mNum[2])
        const step = start <= end ? 1 : -1
        const width = Math.max(String(start).length, String(end).length)
        for (let n = start; step === 1 ? n <= end : n >= end; n += step) {
          lines.push(String(n).padStart(width, '0'))
        }
        continue
      }
    }
    lines.push(line)
  }

  if (!lines.length) {
    error.value = t('inventory.bulkCreateSubzones.emptyNames')
    return
  }

  const existingCodes = new Set((store.zones || []).map(z => String(z.code || '').toLowerCase()).filter(Boolean))
  const items = []
  for (const name of lines) {
    let baseCode = autoGenerateCode.value ? slugify(name) : String(name).trim()
    if (!baseCode) baseCode = `zone-${items.length + 1}`
    baseCode = String(baseCode).slice(0, ZONE_CODE_MAX_LENGTH)
    if (!baseCode) {
      error.value = t('inventory.bulkCreateSubzones.invalidCode')
      return
    }

    let code = baseCode
    let suffix = 1
    while (existingCodes.has(String(code || '').toLowerCase())) {
      const suffixLabel = `-${suffix++}`
      const maxBaseLength = Math.max(ZONE_CODE_MAX_LENGTH - suffixLabel.length, 1)
      code = `${baseCode.slice(0, maxBaseLength)}${suffixLabel}`
    }
    existingCodes.add(String(code || '').toLowerCase())
    items.push({
      code: String(code || '').trim(),
      name,
      zone_type: zoneType.value || 'rack',
      barcode: null,
      qr_code: null,
      rfid: null,
      sort_order: 0,
      is_active: !!isActive.value,
    })
  }

  saving.value = true
  error.value = ''
  try {
    await store.createZonesBulk(props.parentZone.id, items)
    $q.notify({ type: 'positive', message: t('inventory.bulkCreateSubzones.created') })
    emit('saved')
    emit('update:modelValue', false)
  } catch (err) {
    const serverDetail = err?.response?.data?.detail
    if (err?.response?.status === 409 && serverDetail && typeof serverDetail === 'object') {
      const conflicts = serverDetail.conflicts || []
      const msg = t('inventory.bulkCreateSubzones.conflictMessage')
      error.value = conflicts.length ? `${msg}: ${conflicts.join(', ')}` : msg
    } else if (typeof serverDetail === 'string' && serverDetail.trim()) {
      error.value = serverDetail.trim()
    } else {
      error.value = t('inventory.bulkCreateSubzones.failed')
    }
  } finally {
    saving.value = false
  }
}
</script>
