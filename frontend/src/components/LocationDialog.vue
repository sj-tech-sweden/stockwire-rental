<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="$emit('update:modelValue', $event)">
    <q-card style="width: 600px; max-width: 95vw" class="ec-card">
      <q-card-section><div class="text-h6">{{ zone ? t('inventory.editLocation') : t('inventory.newLocation') }}</div></q-card-section>
      <q-card-section class="q-pt-none">
        <q-form ref="formRef" @submit.prevent="save">
          <q-input v-model="form.name" :label="t('users.name')" outlined dense class="q-mb-sm" :rules="[v => !!v || t('login.required')]" />
          <q-input v-model="form.code" :label="t('inventory.code')" outlined dense class="q-mb-sm" :rules="[v => !!v || t('login.required')]" @update:model-value="() => { codeEdited = true }" />
          <div class="row items-center q-mb-sm">
            <div class="col">
              <div v-if="form.name" class="text-caption text-grey-7">
                {{ t('inventory.generatedCodePreview', { slug: slugify(form.name) }) }}
              </div>
            </div>
            <div class="col-auto">
              <q-btn dense flat size="sm" :label="t('app.actions.reset')" color="primary" v-if="form.name" @click="() => { form.code = slugify(form.name); codeEdited = false }" />
            </div>
          </div>
          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-12">
              <q-toggle v-model="autoGenerateCode" :label="t('inventory.autoGenerateCode')" color="primary" />
            </div>
          </div>

          <div class="text-subtitle2 q-mb-xs">Dimensions (cm)</div>
          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-4">
              <q-input v-model.number="form.map_width" type="number" label="Width" outlined dense :min="1" />
            </div>
            <div class="col-4">
              <q-input v-model.number="form.map_depth" type="number" label="Depth" outlined dense :min="1" />
            </div>
            <div class="col-4">
              <q-input v-model.number="form.map_height" type="number" label="Height" outlined dense :min="1" />
            </div>
          </div>

          <div class="text-subtitle2 q-mb-xs">Position (cm)</div>
          <div class="row q-col-gutter-sm q-mb-sm">
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

          <div class="text-subtitle2 q-mb-xs">Identifiers</div>
          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-12 col-md-4">
              <q-input ref="barcodeInputRef" v-model="form.barcode" label="Barcode" outlined dense>
                <template #append>
                  <q-btn flat dense round color="positive" icon="qr_code_scanner" @click="openScanDialog('barcode', 'Barcode')">
                    <q-tooltip>Scan barcode</q-tooltip>
                  </q-btn>
                </template>
              </q-input>
            </div>
            <div class="col-12 col-md-4">
              <q-input ref="qrCodeInputRef" v-model="form.qr_code" label="QR code" outlined dense>
                <template #append>
                  <q-btn flat dense round color="positive" icon="qr_code_scanner" @click="openScanDialog('qr_code', 'QR code')">
                    <q-tooltip>Scan QR code</q-tooltip>
                  </q-btn>
                </template>
              </q-input>
            </div>
            <div class="col-12 col-md-4">
              <q-input ref="rfidInputRef" v-model="form.rfid" label="RFID" outlined dense>
                <template #append>
                  <q-btn flat dense round color="positive" icon="nfc" @click="openScanDialog('rfid', 'RFID')">
                    <q-tooltip>Scan RFID tag</q-tooltip>
                  </q-btn>
                </template>
              </q-input>
            </div>
          </div>

          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-12 col-md-6">
              <q-select
                v-model="form.zone_type"
                :options="locationTypeOptions"
                :label="t('inventory.type')"
                outlined
                dense
                emit-value
                map-options
              />
            </div>
            <div class="col-12 col-md-6">
              <q-select v-model="form.parent_id" :options="parentLocationOptions" :label="t('inventory.parentLocation')" outlined dense clearable emit-value map-options />
            </div>
          </div>
          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-6">
              <q-input v-model.number="form.sort_order" type="number" :label="t('inventory.sortOrder')" outlined dense />
            </div>
            <div class="col-6">
              <q-toggle v-model="form.is_active" :label="t('settings.auth.active')" color="primary" />
            </div>
          </div>
          <q-expansion-item label="Quick presets" class="q-mb-sm" dense v-if="zone">
            <div class="row q-col-gutter-xs q-pa-sm">
              <q-btn
                v-for="p in ZONE_PRESETS" :key="p.label"
                flat dense no-caps size="sm" :label="p.label"
                @click="applyPreset(p.width, p.depth, p.height)"
              />
            </div>
          </q-expansion-item>
          <q-banner v-if="error" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ error }}</q-banner>
        </q-form>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="$emit('update:modelValue', false)" />
        <q-btn color="primary" unelevated :label="zone ? 'Save' : 'Create'" :loading="saving" @click="save" />
      </q-card-actions>
    </q-card>
  </q-dialog>

  <FieldScanDialog
    v-model="scanDialogOpen"
    :field-label="scanFieldLabel"
    :initial-value="scanInitialValue"
    @captured="onScanCaptured"
  />
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQuasar } from 'quasar'
import { useInventoryStore } from '../stores/inventory'
import { slugify } from '../utils/slugify'
import { ZONE_PRESETS } from '../utils/zone-presets'
import FieldScanDialog from './FieldScanDialog.vue'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  zone: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const { t } = useI18n()
const $q = useQuasar()
const store = useInventoryStore()

const formRef = ref(null)
const saving = ref(false)
const error = ref('')
const codeEdited = ref(false)
const autoGenerateCode = ref(true)

const emptyForm = () => ({
  code: '',
  name: '',
  zone_type: 'rack',
  barcode: '',
  qr_code: '',
  rfid: '',
  parent_id: null,
  sort_order: 0,
  is_active: true,
  pos_x: 0,
  pos_y: 0,
  pos_z: 0,
  map_width: 120,
  map_depth: 80,
  map_height: 230,
})

const form = ref(emptyForm())

watch(() => props.modelValue, (open) => {
  if (open) {
    error.value = ''
    if (props.zone) {
      form.value = {
        code: props.zone.code ?? '',
        name: props.zone.name ?? '',
        zone_type: props.zone.zone_type ?? 'rack',
        barcode: props.zone.barcode ?? '',
        qr_code: props.zone.qr_code ?? '',
        rfid: props.zone.rfid ?? '',
        parent_id: props.zone.parent_id ?? null,
        sort_order: Number(props.zone.sort_order ?? 0),
        is_active: !!props.zone.is_active,
        pos_x: props.zone.pos_x ?? 0,
        pos_y: props.zone.pos_y ?? 0,
        pos_z: props.zone.pos_z ?? 0,
        map_width: props.zone.map_width ?? 120,
        map_depth: props.zone.map_depth ?? 80,
        map_height: props.zone.map_height ?? 230,
      }
      codeEdited.value = true
      autoGenerateCode.value = false
    } else {
      form.value = { ...emptyForm(), zone_type: locationTypeOptions.value[0]?.value || 'rack' }
      codeEdited.value = false
      autoGenerateCode.value = true
    }
  }
})

watch(() => form.value.name, (newName) => {
  if (!autoGenerateCode.value) return
  if (codeEdited.value) return
  form.value.code = slugify(newName || '')
})

const locationTypeOptions = computed(() => {
  const values = Array.isArray(store.locationTypes) && store.locationTypes.length
    ? store.locationTypes
    : ['rack', 'shelf', 'bin', 'pallet', 'stage', 'truck', 'warehouse', 'workshop']
  return values.map(value => ({ label: value, value }))
})

const parentLocationOptions = computed(() => {
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

function applyPreset(w, d, h) {
  form.value.map_width = w
  form.value.map_depth = d
  form.value.map_height = h
}

const scanDialogOpen = ref(false)
const scanFieldKey = ref('')
const scanFieldLabel = ref('')
const scanInitialValue = ref('')

function openScanDialog(fieldKey, label) {
  scanFieldKey.value = fieldKey
  scanFieldLabel.value = label
  scanInitialValue.value = form.value[fieldKey] || ''
  scanDialogOpen.value = true
}

function onScanCaptured(value) {
  if (scanFieldKey.value) {
    form.value[scanFieldKey.value] = value
  }
}

async function save() {
  const valid = await formRef.value?.validate()
  if (!valid) return

  saving.value = true
  error.value = ''
  try {
    const payload = {
      code: form.value.code.trim(),
      name: form.value.name.trim(),
      zone_type: form.value.zone_type.trim() || 'rack',
      barcode: form.value.barcode || null,
      qr_code: form.value.qr_code || null,
      rfid: form.value.rfid || null,
      parent_id: form.value.parent_id,
      sort_order: Number(form.value.sort_order || 0),
      is_active: !!form.value.is_active,
      pos_x: Number(form.value.pos_x) || 0,
      pos_y: Number(form.value.pos_y) || 0,
      pos_z: Number(form.value.pos_z) || 0,
      map_width: Number(form.value.map_width) || 120,
      map_depth: Number(form.value.map_depth) || 80,
      map_height: Number(form.value.map_height) || 230,
    }

    if (props.zone) {
      await store.updateZone(props.zone.id, payload)
      $q.notify({ type: 'positive', message: 'Location updated' })
    } else {
      await store.createZone(payload)
      $q.notify({ type: 'positive', message: 'Location created' })
    }

    emit('saved')
    emit('update:modelValue', false)
  } catch (err) {
    error.value = err?.response?.data?.detail || 'Failed to save location'
  } finally {
    saving.value = false
  }
}
</script>
