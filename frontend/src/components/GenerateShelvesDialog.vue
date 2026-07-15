<template>
  <q-dialog v-model="dialog" persistent>
    <q-card style="width: 480px; max-width: 95vw" class="ec-card">
      <q-card-section><div class="text-h6">{{ t('inventory.generateShelves') }}</div></q-card-section>
      <q-card-section class="q-pt-none">
        <div class="text-caption text-grey-7 q-mb-sm">
          {{ t('inventory.generatingShelvesFor', { count: selectedRacks.length, name: selectedRacks.length === 1 ? selectedRacks[0]?.name : 'racks' }) }}
        </div>

        <div class="row q-col-gutter-sm q-mb-sm">
          <div class="col-6">
            <q-input v-model.number="form.count" type="number" :label="t('inventory.shelfCount')" outlined dense :min="1" :max="50" />
          </div>
          <div class="col-6">
            <q-input v-model="form.prefix" :label="t('inventory.shelfPrefix')" outlined dense />
          </div>
        </div>

        <div class="text-subtitle2 q-mb-xs">{{ t('inventory.shelfDimensions') }} (cm)</div>
        <div class="row q-col-gutter-sm q-mb-sm">
          <div class="col-4"><q-input v-model.number="form.shelf_width" type="number" label="Width" outlined dense :min="1" /></div>
          <div class="col-4"><q-input v-model.number="form.shelf_depth" type="number" label="Depth" outlined dense :min="1" /></div>
          <div class="col-4"><q-input v-model.number="form.shelf_height" type="number" label="Height" outlined dense :min="1" /></div>
        </div>

        <div class="row q-col-gutter-xs q-mb-sm">
          <q-btn
            v-for="p in shelfPresets" :key="p.label"
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

const emptyForm = () => ({
  count: 5,
  shelf_width: 115,
  shelf_depth: 75,
  shelf_height: 3,
  prefix: 'Shelf',
})

const form = ref(emptyForm())
const error = ref('')
const saving = ref(false)

watch(() => props.modelValue, (val) => {
  if (val) {
    form.value = emptyForm()
    error.value = ''
  }
})

function applyPreset(w, d, h) {
  form.value.shelf_width = w
  form.value.shelf_depth = d
  form.value.shelf_height = h
}

const shelfPresets = computed(() =>
  ZONE_PRESETS.filter(p => p.height <= 40).map(p => ({
    label: `${p.label} (${p.width}×${p.depth}×${p.height})`,
    width: p.width,
    depth: p.depth,
    height: p.height,
  }))
)

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
    const result = await store.generateShelves({
      rack_ids: rackIds,
      count: form.value.count,
      shelf_width: form.value.shelf_width,
      shelf_depth: form.value.shelf_depth,
      shelf_height: form.value.shelf_height,
      prefix: form.value.prefix,
    })
    dialog.value = false
    $q.notify({ type: 'positive', message: `Generated ${result?.length || 0} shelves` })
    emit('saved')
  } catch (err) {
    error.value = err?.response?.data?.detail || 'Shelf generation failed'
  } finally {
    saving.value = false
  }
}
</script>
