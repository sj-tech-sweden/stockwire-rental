<template>
  <q-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)" persistent>
    <q-card style="min-width: 650px; max-height: 80vh">
      <q-card-section class="row items-center q-pb-sm">
        <q-icon name="local_shipping" size="sm" class="q-mr-sm" />
        <div class="text-h6">{{ t('routePlanner.vehicles') }}</div>
        <q-space />
        <q-btn icon="close" flat round dense @click="$emit('update:modelValue', false)" />
      </q-card-section>

      <!-- Vehicle list -->
      <q-card-section v-if="!editingVehicle && !addingNew" class="q-pt-none">
        <div class="row items-center q-mb-md">
          <div class="text-subtitle2">{{ t('routePlanner.vehicleList', { count: store.vehicles.length }) }}</div>
          <q-space />
          <q-btn unelevated color="primary" icon="add" :label="t('routePlanner.newVehicle')" size="sm" @click="startAdd" />
        </div>

        <q-list v-if="store.vehicles.length > 0" bordered separator class="rounded-borders">
          <q-item v-for="v in store.vehicles" :key="v.id">
            <q-item-section avatar>
              <q-avatar :color="vehicleColor(v.vehicle_type)" text-color="white" size="36px">
                <q-icon :name="vehicleIcon(v.vehicle_type)" />
              </q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label class="text-weight-medium">{{ v.name }}</q-item-label>
              <q-item-label caption>
                {{ v.vehicle_type }}
                <template v-if="v.license_plate"> · {{ v.license_plate }}</template>
                <template v-if="v.max_weight_kg"> · {{ v.max_weight_kg }} kg</template>
                <template v-if="effectiveVolume(v)"> · {{ effectiveVolume(v) }} m³</template>
                <template v-if="v.vehicle_type === 'trailer' && v.max_payload_kg"> · {{ t('routePlanner.payload') }}: {{ v.max_payload_kg }} kg</template>
                <template v-if="v.vehicle_type === 'trailer' && v.curb_weight_kg"> · {{ t('routePlanner.curbWeight') }}: {{ v.curb_weight_kg }} kg</template>
                <template v-if="v.can_pull_trailer">
                  · <q-icon name="link" size="xs" /> towing
                  <template v-if="v.max_tow_weight_kg"> ({{ v.max_tow_weight_kg }} kg)</template>
                </template>
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <div class="row q-gutter-xs">
                <q-btn flat dense round icon="edit" size="sm" color="grey-7" @click="startEdit(v)" />
                <q-btn flat dense round icon="delete" size="sm" color="negative" @click="onDeleteVehicle(v)" />
              </div>
            </q-item-section>
          </q-item>
        </q-list>
        <div v-else class="text-center text-grey q-pa-lg">
          <q-icon name="local_shipping" size="48px" color="grey-4" class="q-mb-sm" /><br />
          {{ t('routePlanner.noVehicles') }}
        </div>
      </q-card-section>

      <!-- Add/Edit form -->
      <q-card-section v-else class="q-pt-none scroll" style="max-height: 65vh">
        <q-form @submit="onSubmit" class="q-gutter-sm">
          <q-input v-model="form.name" :label="t('routePlanner.vehicleName')" outlined dense :rules="[val => !!val || t('common.required')]" />

          <q-select v-model="form.vehicle_type" :label="t('routePlanner.vehicleType')" :options="vehicleTypeOptions" emit-value map-options outlined dense />

          <q-input v-model="form.license_plate" :label="t('routePlanner.licensePlate')" outlined dense />

          <div class="row q-gutter-md">
            <q-input v-model.number="form.max_weight_kg" :label="t('routePlanner.maxWeight')" type="number" outlined dense class="col" />
            <q-input v-model.number="form.max_volume_m3" :label="t('routePlanner.maxVolume')" type="number" step="0.1" outlined dense class="col"
              :hint="volumeHint" />
          </div>

          <div class="text-caption text-grey q-mt-xs">{{ t('routePlanner.cargoInterior') }}</div>
          <div class="row q-gutter-md">
            <q-input v-model.number="form.interior_length_cm" :label="t('routePlanner.cargoLength')" type="number" outlined dense class="col" @update:model-value="autoCalcVolume" />
            <q-input v-model.number="form.interior_width_cm" :label="t('routePlanner.cargoWidth')" type="number" outlined dense class="col" @update:model-value="autoCalcVolume" />
            <q-input v-model.number="form.interior_height_cm" :label="t('routePlanner.cargoHeight')" type="number" outlined dense class="col" @update:model-value="autoCalcVolume" />
          </div>
          <div v-if="calculatedVolume" class="text-caption text-primary">
            {{ t('routePlanner.calculatedVolume') }}: {{ calculatedVolume }} m³
          </div>

          <!-- Trailer-specific: weight fields -->
          <template v-if="form.vehicle_type === 'trailer'">
            <q-separator class="q-my-sm" />
            <div class="text-caption text-grey">{{ t('routePlanner.trailerWeight') }}</div>
            <div class="row q-gutter-md">
              <q-input
                v-model.number="form.curb_weight_kg"
                :label="t('routePlanner.curbWeight')"
                type="number"
                outlined
                dense
                class="col"
                :hint="t('routePlanner.curbWeightHint')"
              />
              <q-input
                v-model.number="form.max_payload_kg"
                :label="t('routePlanner.payload')"
                type="number"
                outlined
                dense
                class="col"
                :hint="t('routePlanner.payloadHint')"
              />
            </div>
          </template>

          <!-- Towing section (only for truck/van/car) -->
          <template v-if="form.vehicle_type !== 'trailer'">
            <q-separator class="q-my-sm" />
            <div class="row items-center q-gutter-sm">
              <q-checkbox v-model="form.can_pull_trailer" :label="t('routePlanner.canPullTrailer')" />
            </div>
            <q-input
              v-if="form.can_pull_trailer"
              v-model.number="form.max_tow_weight_kg"
              :label="t('routePlanner.maxTowWeight')"
              type="number"
              outlined
              dense
              class="q-mt-sm"
            />
          </template>

          <q-input v-model="form.notes" :label="t('common.notes')" type="textarea" outlined dense />

          <div class="row justify-end q-gutter-sm">
            <q-btn flat :label="t('common.cancel')" @click="cancelEdit" />
            <q-btn type="submit" color="primary" :label="t('common.save')" :loading="saving" />
          </div>
        </q-form>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQuasar } from 'quasar'
import { useRoutePlannerStore } from '../stores/routePlanner'

const { t } = useI18n()
const $q = useQuasar()
const store = useRoutePlannerStore()

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue'])

const saving = ref(false)
const editingVehicle = ref(null)
const addingNew = ref(false)

const vehicleTypeOptions = [
  { label: t('routePlanner.truck'), value: 'truck' },
  { label: t('routePlanner.van'), value: 'van' },
  { label: t('routePlanner.trailer'), value: 'trailer' },
  { label: t('routePlanner.car'), value: 'car' },
]

const defaultForm = () => ({
  name: '',
  vehicle_type: 'truck',
  license_plate: '',
  max_weight_kg: null,
  max_volume_m3: null,
  interior_length_cm: null,
  interior_width_cm: null,
  interior_height_cm: null,
  can_pull_trailer: false,
  max_tow_weight_kg: null,
  curb_weight_kg: null,
  max_payload_kg: null,
  notes: '',
})

const form = ref(defaultForm())

const calculatedVolume = computed(() => {
  const l = form.value.interior_length_cm
  const w = form.value.interior_width_cm
  const h = form.value.interior_height_cm
  if (l && w && h) {
    return ((l * w * h) / 1000000).toFixed(2)
  }
  return null
})

const volumeHint = computed(() => {
  if (form.value.max_volume_m3) return null
  if (calculatedVolume.value) return `= ${calculatedVolume.value} m³`
  return t('routePlanner.volumeOrDimensions')
})

function effectiveVolume(v) {
  if (v.max_volume_m3) return v.max_volume_m3
  if (v.interior_length_cm && v.interior_width_cm && v.interior_height_cm) {
    return ((v.interior_length_cm * v.interior_width_cm * v.interior_height_cm) / 1000000).toFixed(2)
  }
  return null
}

function autoCalcVolume() {
  if (calculatedVolume.value && !form.value.max_volume_m3) {
    form.value.max_volume_m3 = parseFloat(calculatedVolume.value)
  }
}

function vehicleIcon(type) {
  const map = { truck: 'local_shipping', van: 'airport_shuttle', trailer: 'inventory_2', car: 'directions_car' }
  return map[type] || 'local_shipping'
}

function vehicleColor(type) {
  const map = { truck: 'blue', van: 'teal', trailer: 'orange', car: 'purple' }
  return map[type] || 'grey'
}

function startAdd() {
  editingVehicle.value = null
  addingNew.value = true
  form.value = defaultForm()
}

function startEdit(vehicle) {
  editingVehicle.value = vehicle
  addingNew.value = false
  form.value = { ...defaultForm(), ...vehicle }
}

function cancelEdit() {
  editingVehicle.value = null
  addingNew.value = false
  form.value = defaultForm()
}

async function onSubmit() {
  saving.value = true
  try {
    if (editingVehicle.value) {
      await store.updateVehicle(editingVehicle.value.id, form.value)
    } else {
      await store.createVehicle(form.value)
    }
    cancelEdit()
    $q.notify({ type: 'positive', message: t('common.saved') })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
  } finally {
    saving.value = false
  }
}

async function onDeleteVehicle(vehicle) {
  $q.dialog({
    title: t('common.confirm'),
    message: t('routePlanner.deleteVehicleConfirm'),
    cancel: t('common.cancel'),
    ok: t('common.delete'),
    color: 'negative',
  }).onOk(async () => {
    try {
      await store.deleteVehicle(vehicle.id)
      $q.notify({ type: 'positive', message: t('common.deleted') })
    } catch (err) {
      $q.notify({ type: 'negative', message: err.response?.data?.detail || err.message })
    }
  })
}

watch(() => props.modelValue, (val) => { if (val) { cancelEdit(); store.fetchVehicles() } })
</script>
