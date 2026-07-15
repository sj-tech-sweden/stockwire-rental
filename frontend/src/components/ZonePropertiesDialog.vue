<template>
  <q-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)" persistent>
    <q-card style="width: 480px; max-width: 95vw" class="ec-card">
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6">{{ zone?.name || t('inventory.zone') }}</div>
        <q-space />
        <q-btn flat dense round icon="close" @click="$emit('update:modelValue', false)" />
      </q-card-section>

      <q-card-section v-if="zone" class="q-pt-sm">
        <div class="text-caption text-grey-6 q-mb-md">All measurements in centimeters</div>

        <div class="text-subtitle2 q-mb-xs">Position</div>
        <div class="row q-col-gutter-sm q-mb-md">
          <div class="col-4">
            <q-input v-model.number="form.pos_x" type="number" label="X (left/right)" outlined dense />
          </div>
          <div class="col-4">
            <q-input v-model.number="form.pos_y" type="number" label="Y (front/back)" outlined dense />
          </div>
          <div class="col-4">
            <q-input v-model.number="form.pos_z" type="number" label="Z (height)" outlined dense />
          </div>
        </div>

        <div class="text-subtitle2 q-mb-xs">Dimensions</div>
        <div class="row q-col-gutter-sm q-mb-md">
          <div class="col-4">
            <q-input v-model.number="form.map_width" type="number" label="Width (cm)" outlined dense :min="1" />
          </div>
          <div class="col-4">
            <q-input v-model.number="form.map_depth" type="number" label="Depth (cm)" outlined dense :min="1" />
          </div>
          <div class="col-4">
            <q-input v-model.number="form.map_height" type="number" label="Height (cm)" outlined dense :min="1" />
          </div>
        </div>

        <div class="row q-col-gutter-sm q-mb-md">
          <div class="col-6">
            <q-input v-model="form.name" label="Name" outlined dense />
          </div>
          <div class="col-6">
            <q-select v-model="form.zone_type" :options="typeOptions" label="Type" outlined dense emit-value map-options />
          </div>
        </div>

        <div class="row q-col-gutter-sm q-mb-md">
          <div class="col-6">
            <q-input v-model="form.color" label="Color" outlined dense>
              <template #prepend>
                <div :style="{ width: '16px', height: '16px', borderRadius: '3px', background: form.color || '#3a5a4a' }" />
              </template>
            </q-input>
          </div>
          <div class="col-6">
            <q-toggle v-model="form.is_active" label="Active" color="primary" />
          </div>
        </div>

        <q-expansion-item label="Quick presets" class="q-mb-sm" dense>
          <div class="row q-col-gutter-xs q-pa-sm">
            <q-btn
              v-for="p in ZONE_PRESETS" :key="p.label"
              flat dense no-caps size="sm" :label="p.label"
              @click="applyPreset(p.width, p.depth, p.height)"
            />
          </div>
        </q-expansion-item>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="$emit('update:modelValue', false)" />
        <q-btn color="primary" unelevated :label="t('app.actions.save')" :loading="saving" @click="save" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQuasar } from 'quasar'
import { useInventoryStore } from '../stores/inventory'
import { ZONE_PRESETS } from '../utils/zone-presets'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  zone: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const { t } = useI18n()
const $q = useQuasar()
const store = useInventoryStore()

const saving = ref(false)
const form = ref({
  pos_x: 0, pos_y: 0, pos_z: 0,
  map_width: 200, map_depth: 100, map_height: 150,
  name: '', zone_type: 'rack', color: '', is_active: true,
})

const typeOptions = [
  { label: 'Warehouse', value: 'warehouse' },
  { label: 'Rack', value: 'rack' },
  { label: 'Shelf', value: 'shelf' },
  { label: 'Bin', value: 'bin' },
  { label: 'Pallet', value: 'pallet' },
  { label: 'Stage', value: 'stage' },
  { label: 'Truck', value: 'truck' },
  { label: 'Workshop', value: 'workshop' },
]

watch(() => props.modelValue, (open) => {
  if (open && props.zone) {
    form.value = {
      pos_x: props.zone.pos_x ?? 0,
      pos_y: props.zone.pos_y ?? 0,
      pos_z: props.zone.pos_z ?? 0,
      map_width: props.zone.map_width ?? 200,
      map_depth: props.zone.map_depth ?? 100,
      map_height: props.zone.map_height ?? 150,
      name: props.zone.name ?? '',
      zone_type: props.zone.zone_type ?? 'rack',
      color: props.zone.color ?? '',
      is_active: props.zone.is_active ?? true,
    }
  }
})

function applyPreset(w, d, h) {
  form.value.map_width = w
  form.value.map_depth = d
  form.value.map_height = h
}

async function save() {
  if (!props.zone) return
  saving.value = true
  try {
    await store.updateZone(props.zone.id, {
      pos_x: Number(form.value.pos_x) || 0,
      pos_y: Number(form.value.pos_y) || 0,
      pos_z: Number(form.value.pos_z) || 0,
      map_width: Number(form.value.map_width) || 200,
      map_depth: Number(form.value.map_depth) || 100,
      map_height: Number(form.value.map_height) || 150,
      name: form.value.name,
      zone_type: form.value.zone_type,
      color: form.value.color || null,
      is_active: form.value.is_active,
    })
    $q.notify({ type: 'positive', message: 'Zone updated' })
    emit('saved')
    emit('update:modelValue', false)
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || 'Failed to save zone' })
  } finally {
    saving.value = false
  }
}
</script>
