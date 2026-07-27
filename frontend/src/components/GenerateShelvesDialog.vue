<template>
  <q-dialog v-model="dialog" persistent>
    <q-card style="width: 520px; max-width: 95vw" class="ec-card">
      <q-card-section>
        <div class="text-h6">{{ isBinMode ? t('inventory.generateBins') : t('inventory.generateShelves') }}</div>
      </q-card-section>
      <q-card-section class="q-pt-none">
        <div class="text-caption text-grey-7 q-mb-sm">
          {{ t('inventory.generatingChildrenFor', { count: selectedRacks.length, name: selectedRacks.length === 1 ? selectedRacks[0]?.name : 'zones' }) }}
        </div>

        <q-select
          v-model="form.child_type"
          :options="childTypeOptions"
          :label="t('inventory.childType')"
          outlined dense emit-value map-options
          class="q-mb-sm"
        />

        <div class="row q-col-gutter-sm q-mb-sm">
          <div class="col-6">
            <q-input v-model.number="form.count" type="number" :label="t('inventory.childCount')" outlined dense :min="1" :max="50" />
          </div>
          <div class="col-6">
            <q-input v-model="form.prefix" :label="t('inventory.childPrefix')" outlined dense />
          </div>
        </div>

        <div class="row q-col-gutter-sm q-mb-sm">
          <div class="col-12">
            <q-select
              v-model="form.naming_format"
              :options="namingFormatOptions"
              :label="t('inventory.namingFormat')"
              outlined dense emit-value map-options
            />
          </div>
        </div>

        <div class="text-subtitle2 q-mb-xs">{{ t('inventory.childDimensions') }} (cm)</div>
        <div class="row q-col-gutter-sm q-mb-sm">
          <div class="col-4"><q-input v-model.number="form.child_width" type="number" label="Width" outlined dense :min="1" /></div>
          <div class="col-4"><q-input v-model.number="form.child_depth" type="number" label="Depth" outlined dense :min="1" /></div>
          <div class="col-4"><q-input v-model.number="form.child_height" type="number" label="Height" outlined dense :min="1" /></div>
        </div>

        <div class="row q-col-gutter-xs q-mb-sm">
          <q-btn
            v-for="p in filteredPresets" :key="p.label"
            flat dense no-caps size="sm" :label="p.label"
            @click="applyPreset(p.width, p.depth, p.height)"
          />
        </div>

        <q-banner v-if="error" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ error }}</q-banner>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="dialog = false" />
        <q-btn color="primary" unelevated :label="t('inventory.generate')" :loading="saving" @click="save" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQuasar } from 'quasar'
import { useInventoryStore } from '../stores/inventory'
import { ZONE_PRESETS } from '../utils/zone-presets'

const { t } = useI18n()
const $q = useQuasar()
const store = useInventoryStore()

const props = defineProps({
  modelValue: Boolean,
  selectedRacks: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const dialog = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const SHELF_DEFAULTS = { child_width: 115, child_depth: 75, child_height: 3, prefix: 'Shelf', count: 5, naming_format: 'numeric' }
const BIN_DEFAULTS = { child_width: 55, child_depth: 35, child_height: 12, prefix: 'Bin', count: 5, naming_format: 'numeric' }

const form = ref({ child_type: 'shelf', ...SHELF_DEFAULTS })
const error = ref('')
const saving = ref(false)

const isBinMode = computed(() => form.value.child_type === 'bin')

const namingFormatOptions = computed(() => [
  { label: t('inventory.namingFormatNumeric'), value: 'numeric' },
  { label: t('inventory.namingFormatAlphabetic'), value: 'alphabetic' },
])

const childTypeOptions = computed(() => [
  { label: t('inventory.zoneTypeShelf'), value: 'shelf' },
  { label: t('inventory.zoneTypeBin'), value: 'bin' },
])

watch(() => props.modelValue, (val) => {
  if (val) {
    form.value = { child_type: 'shelf', ...SHELF_DEFAULTS }
    error.value = ''
  }
})

watch(() => form.value.child_type, (type) => {
  const defaults = type === 'bin' ? BIN_DEFAULTS : SHELF_DEFAULTS
  form.value.child_width = defaults.child_width
  form.value.child_depth = defaults.child_depth
  form.value.child_height = defaults.child_height
  form.value.prefix = defaults.prefix
  form.value.naming_format = defaults.naming_format
})

function applyPreset(w, d, h) {
  form.value.child_width = w
  form.value.child_depth = d
  form.value.child_height = h
}

const filteredPresets = computed(() => {
  const type = form.value.child_type
  return ZONE_PRESETS.filter(p => p.types.includes(type)).map(p => ({
    label: `${t(p.label)} (${p.width}×${p.depth}×${p.height})`,
    width: p.width, depth: p.depth, height: p.height,
  }))
})

async function save() {
  if (!props.selectedRacks.length) return
  if (form.value.count < 1) {
    error.value = 'Count must be at least 1'
    return
  }

  saving.value = true
  error.value = ''
  try {
    const rackIds = props.selectedRacks.map(r => r.id || r._tree?.id).filter(Boolean)
    const childType = form.value.child_type
    const result = await store.generateShelves({
      rack_ids: rackIds,
      count: form.value.count,
      shelf_width: form.value.child_width,
      shelf_depth: form.value.child_depth,
      shelf_height: form.value.child_height,
      prefix: form.value.prefix,
      child_type: childType,
      naming_format: form.value.naming_format || 'numeric',
    })
    dialog.value = false
    const label = childType === 'bin' ? 'bins' : 'shelves'
    $q.notify({ type: 'positive', message: `Generated ${result?.length || 0} ${label}` })
    emit('saved')
  } catch (err) {
    error.value = err?.response?.data?.detail || 'Generation failed'
  } finally {
    saving.value = false
  }
}
</script>
