<template>
  <q-dialog v-model="dialog" persistent>
    <q-card style="width: 560px; max-width: 95vw" class="ec-card">
      <q-card-section><div class="text-h6">{{ t('inventory.bulkEditZones') }}</div></q-card-section>
      <q-card-section class="q-pt-none">
        <div class="text-caption text-grey-7 q-mb-sm">{{ t('inventory.updatingZonesCount', { count: selectedIds.length }) }}</div>

        <div class="text-subtitle2 q-mb-xs">{{ t('inventory.zoneType') }}</div>
        <q-select v-model="form.zone_type" :options="zoneTypeOptions" :label="t('inventory.zoneType')" outlined dense clearable emit-value map-options class="q-mb-sm" />

        <div class="text-subtitle2 q-mb-xs">Dimensions (cm)</div>
        <div class="row q-col-gutter-sm q-mb-sm">
          <div class="col-4"><q-input v-model.number="form.map_width" type="number" label="Width" outlined dense clearable /></div>
          <div class="col-4"><q-input v-model.number="form.map_depth" type="number" label="Depth" outlined dense clearable /></div>
          <div class="col-4"><q-input v-model.number="form.map_height" type="number" label="Height" outlined dense clearable /></div>
        </div>

        <q-expansion-item label="Quick presets" class="q-mb-sm" dense>
          <div class="row q-col-gutter-xs q-pa-sm">
            <q-btn
              v-for="p in filteredPresets" :key="p.label"
              flat dense no-caps size="sm" :label="t(p.label)"
              @click="applyPreset(p.width, p.depth, p.height)"
            />
          </div>
        </q-expansion-item>

        <div class="text-subtitle2 q-mb-xs">Color</div>
        <q-input v-model="form.color" label="Hex color" outlined dense clearable class="q-mb-sm" />

        <div class="text-subtitle2 q-mb-xs">Rotation (°)</div>
        <div class="row q-col-gutter-sm q-mb-sm items-center">
          <div class="col-4">
            <q-input v-model.number="form.rotation" type="number" label="Rotation" outlined dense clearable :min="0" :max="360" />
          </div>
          <div class="col-auto">
            <div class="row q-col-gutter-xs">
              <q-btn flat dense no-caps size="sm" label="0°" @click="form.rotation = 0" :color="form.rotation === 0 ? 'primary' : undefined" />
              <q-btn flat dense no-caps size="sm" label="90°" @click="form.rotation = 90" :color="form.rotation === 90 ? 'primary' : undefined" />
              <q-btn flat dense no-caps size="sm" label="180°" @click="form.rotation = 180" :color="form.rotation === 180 ? 'primary' : undefined" />
              <q-btn flat dense no-caps size="sm" label="270°" @click="form.rotation = 270" :color="form.rotation === 270 ? 'primary' : undefined" />
            </div>
          </div>
        </div>

        <div class="text-subtitle2 q-mb-xs">{{ t('inventory.parentZone') }}</div>
        <q-select v-model="form.parent_id" :options="parentOptions" :label="t('inventory.parentZone')" outlined dense clearable emit-value map-options class="q-mb-sm" />

        <q-toggle v-model="form.is_active" :label="t('inventory.active')" color="primary" class="q-mb-sm" />

        <q-banner v-if="error" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ error }}</q-banner>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="dialog = false" />
        <q-btn color="primary" unelevated :label="t('inventory.apply')" :loading="saving" @click="save" />
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
  selectedZones: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const dialog = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const KEEP_VALUE = '__keep__'

const emptyForm = () => ({
  zone_type: null,
  map_width: null,
  map_depth: null,
  map_height: null,
  color: null,
  parent_id: KEEP_VALUE,
  is_active: true,
  rotation: null,
})

const form = ref(emptyForm())
const error = ref('')
const saving = ref(false)

const selectedIds = computed(() => props.selectedZones.map(z => z.id).filter(Boolean))

watch(() => props.modelValue, (val) => {
  if (val) {
    form.value = emptyForm()
    error.value = ''
  }
})

const zoneTypeOptions = computed(() => [
  { label: t('inventory.zoneTypeRack'), value: 'rack' },
  { label: t('inventory.zoneTypeShelf'), value: 'shelf' },
  { label: t('inventory.zoneTypeBin'), value: 'bin' },
  { label: t('inventory.zoneTypePallet'), value: 'pallet' },
  { label: t('inventory.zoneTypeStage'), value: 'stage' },
  { label: t('inventory.zoneTypeTruck'), value: 'truck' },
  { label: t('inventory.zoneTypeWarehouse'), value: 'warehouse' },
  { label: t('inventory.zoneTypeWorkshop'), value: 'workshop' },
])

const parentOptions = computed(() => {
  const flat = [
    { label: '— No change', value: KEEP_VALUE },
    { label: '— None (top level)', value: null },
  ]
  const walk = (nodes, prefix) => {
    for (const node of nodes || []) {
      const label = prefix ? `${prefix} / ${node.name}` : node.name
      flat.push({ label, value: node.id })
      walk(node.children || [], label)
    }
  }
  walk(store.zoneTree)
  return flat
})

function applyPreset(w, d, h) {
  form.value.map_width = w
  form.value.map_depth = d
  form.value.map_height = h
}

const filteredPresets = computed(() => {
  const type = form.value.zone_type
  if (!type) return ZONE_PRESETS
  return ZONE_PRESETS.filter(p => p.types.includes(type))
})

async function save() {
  if (!selectedIds.value.length) return

  const patch = {}
  if (form.value.zone_type) patch.zone_type = form.value.zone_type
  if (form.value.map_width != null) patch.map_width = form.value.map_width
  if (form.value.map_depth != null) patch.map_depth = form.value.map_depth
  if (form.value.map_height != null) patch.map_height = form.value.map_height
  if (form.value.color) patch.color = form.value.color
  if (form.value.rotation != null) patch.rotation = form.value.rotation
  if (form.value.parent_id !== KEEP_VALUE) patch.parent_id = form.value.parent_id
  patch.is_active = form.value.is_active

  if (!Object.keys(patch).length) {
    error.value = 'Choose at least one field to update'
    return
  }

  saving.value = true
  error.value = ''
  try {
    await store.bulkUpdateZones(selectedIds.value, patch)
    dialog.value = false
    $q.notify({ type: 'positive', message: `Zones updated: ${selectedIds.value.length}` })
    emit('saved')
  } catch (err) {
    error.value = err?.response?.data?.detail || 'Bulk zone update failed'
  } finally {
    saving.value = false
  }
}
</script>
