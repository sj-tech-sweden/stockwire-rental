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

          <div class="text-subtitle2 q-mb-xs">{{ t('inventory.coordinatesAddress') }}</div>
          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-6">
              <q-input v-model.number="form.latitude" type="number" :label="t('inventory.latitude')" outlined dense :min="-90" :max="90" step="0.000001" />
            </div>
            <div class="col-6">
              <q-input v-model.number="form.longitude" type="number" :label="t('inventory.longitude')" outlined dense :min="-180" :max="180" step="0.000001" />
            </div>
          </div>
          <q-input v-model="form.address_line1" :label="t('inventory.addressLine1')" outlined dense class="q-mb-sm" />
          <q-input v-model="form.address_line2" :label="t('inventory.addressLine2')" outlined dense class="q-mb-sm" />
          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-6">
              <q-input v-model="form.postal_code" :label="t('inventory.zonePostalCode')" outlined dense />
            </div>
            <div class="col-6">
              <q-input v-model="form.city" :label="t('venues.city')" outlined dense />
            </div>
          </div>
          <q-select
            v-model="form.country"
            :options="COUNTRIES"
            :label="t('venues.country')"
            outlined
            dense
            clearable
            emit-value
            map-options
            class="q-mb-sm"
          >
            <template #append>
              <q-btn
                flat dense round color="primary" icon="my_location"
                :title="t('inventory.useInheritedCoords')"
                v-if="mapInherited"
                @click="copyInheritedLocation"
              />
            </template>
          </q-select>
          <q-chip v-if="mapInherited" dense class="q-mb-sm" color="grey-3" text-color="dark">
            {{ t('inventory.mapInherited') }}
          </q-chip>
          <div v-if="zoneMapEmbedUrl" class="q-mb-sm">
            <q-responsive :ratio="16 / 9" class="rounded-borders" style="overflow: hidden; border: 1px solid #d6dbe2;">
              <iframe
                :src="zoneMapEmbedUrl"
                :title="t('inventory.mapPreview')"
                loading="lazy"
                referrerpolicy="no-referrer-when-downgrade"
                style="border: 0; width: 100%; height: 100%;"
              />
            </q-responsive>
            <q-btn
              flat dense no-caps color="primary" icon="open_in_new"
              class="q-mt-xs"
              :label="t('inventory.openMap')"
              :href="zoneMapLink"
              target="_blank"
              rel="noopener"
            />
          </div>

          <div class="text-subtitle2 q-mb-xs">{{ t('inventory.zoneDimensions') }}</div>
          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-4">
              <q-input v-model.number="form.map_width" type="number" :label="t('inventory.zoneWidth')" outlined dense :min="1" />
            </div>
            <div class="col-4">
              <q-input v-model.number="form.map_depth" type="number" :label="t('inventory.zoneDepth')" outlined dense :min="1" />
            </div>
            <div class="col-4">
              <q-input v-model.number="form.map_height" type="number" :label="t('inventory.zoneHeight')" outlined dense :min="1" />
            </div>
          </div>

          <div class="text-subtitle2 q-mb-xs">{{ t('inventory.position') }}</div>
          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-4">
              <q-input v-model.number="form.pos_x" type="number" :label="t('inventory.posX')" outlined dense>
                <q-tooltip>{{ t('inventory.tooltipPosX') }}</q-tooltip>
              </q-input>
            </div>
            <div class="col-4">
              <q-input v-model.number="form.pos_y" type="number" :label="t('inventory.posY')" outlined dense>
                <q-tooltip>{{ t('inventory.tooltipPosY') }}</q-tooltip>
              </q-input>
            </div>
            <div class="col-4">
              <q-input v-model.number="form.pos_z" type="number" :label="t('inventory.posZ')" outlined dense>
                <q-tooltip>{{ t('inventory.tooltipPosZ') }}</q-tooltip>
              </q-input>
            </div>
          </div>

          <div class="text-subtitle2 q-mb-xs">{{ t('inventory.rotation') }}</div>
          <div class="row q-col-gutter-sm q-mb-sm items-center">
            <div class="col-4">
              <q-input v-model.number="form.rotation" type="number" :label="t('inventory.rotation')" outlined dense :min="0" :max="360" />
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

          <div class="text-subtitle2 q-mb-xs">{{ t('inventory.zoneColor') }}</div>
          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-6">
              <q-input v-model="form.color" :label="t('inventory.zoneColor')" outlined dense>
                <template #append>
                  <q-btn flat dense round color="primary" icon="colorize" @click="showColorPicker = !showColorPicker" />
                </template>
              </q-input>
              <q-color v-if="showColorPicker" v-model="form.color" class="my-app-cp q-mt-sm" />
            </div>
          </div>

          <div class="text-subtitle2 q-mb-xs">{{ t('inventory.identifiers') }}</div>
          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-12 col-md-4">
              <q-input ref="barcodeInputRef" v-model="form.barcode" :label="t('inventory.barcode')" outlined dense>
                <template #append>
                  <q-btn flat dense round color="positive" icon="qr_code_scanner" @click="openScanDialog('barcode', t('inventory.barcode'))">
                    <q-tooltip>{{ t('inventory.scanBarcode') }}</q-tooltip>
                  </q-btn>
                </template>
              </q-input>
            </div>
            <div class="col-12 col-md-4">
              <q-input ref="qrCodeInputRef" v-model="form.qr_code" :label="t('inventory.qrCode')" outlined dense>
                <template #append>
                  <q-btn flat dense round color="positive" icon="qr_code_scanner" @click="openScanDialog('qr_code', t('inventory.qrCode'))">
                    <q-tooltip>{{ t('inventory.scanQr') }}</q-tooltip>
                  </q-btn>
                </template>
              </q-input>
            </div>
            <div class="col-12 col-md-4">
              <q-input ref="rfidInputRef" v-model="form.rfid" :label="t('inventory.zoneRfid')" outlined dense>
                <template #append>
                  <q-btn flat dense round color="positive" icon="nfc" @click="openScanDialog('rfid', t('inventory.zoneRfid'))">
                    <q-tooltip>{{ t('inventory.scanRfid') }}</q-tooltip>
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
          <q-expansion-item :label="t('inventory.zoneQuickPresets')" class="q-mb-sm" dense v-if="zone">
            <div class="row q-col-gutter-xs q-pa-sm">
              <q-btn
                v-for="p in filteredPresets" :key="p.label"
                flat dense no-caps size="sm" :label="t(p.label)"
                @click="applyPreset(p.width, p.depth, p.height)"
              />
            </div>
          </q-expansion-item>
          <q-banner v-if="error" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ error }}</q-banner>
        </q-form>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="$emit('update:modelValue', false)" />
        <q-btn color="primary" unelevated :label="zone ? t('inventory.zoneSave') : t('inventory.zoneCreate')" :loading="saving" @click="save" />
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
import { googleMapsEmbedUrl, googleMapsSearchUrl, locationQueryFromParts } from '../utils/maps'
import { COUNTRIES } from '../constants/countries'
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
const showColorPicker = ref(false)

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
  rotation: 0,
  color: '',
  latitude: null,
  longitude: null,
  address_line1: '',
  address_line2: '',
  postal_code: '',
  city: '',
  country: '',
})

const form = ref(emptyForm())

watch(() => props.modelValue, (open) => {
  if (open) {
    error.value = ''
    showColorPicker.value = false
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
        rotation: props.zone.rotation ?? 0,
        color: props.zone.color ?? '',
        latitude: props.zone.latitude ?? null,
        longitude: props.zone.longitude ?? null,
        address_line1: props.zone.address_line1 ?? '',
        address_line2: props.zone.address_line2 ?? '',
        postal_code: props.zone.postal_code ?? '',
        city: props.zone.city ?? '',
        country: props.zone.country ?? '',
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
  return values.map(value => ({
    label: t(`inventory.zoneTypes.${value}`) || value,
    value,
  }))
})

const parentLocationOptions = computed(() => {
  const flat = [{ label: t('inventory.unassigned'), value: null }]
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

const filteredPresets = computed(() => {
  const type = form.value.zone_type
  if (!type) return ZONE_PRESETS
  return ZONE_PRESETS.filter(p => p.types.includes(type))
})

const hasOwnCoords = computed(
  () => form.value.latitude != null && form.value.longitude != null,
)
const inheritsCoords = computed(
  () => !hasOwnCoords.value
    && (props.zone?.effective_latitude != null || props.zone?.effective_longitude != null),
)
const mapInherited = computed(() => !hasOwnCoords.value && inheritsCoords.value)
const zoneLocationQuery = computed(() => locationQueryFromParts({
  name: form.value.name,
  address: form.value.address_line1 || form.value.address_line2,
  city: form.value.city,
  postal_code: form.value.postal_code,
  country: form.value.country,
  latitude: hasOwnCoords.value ? form.value.latitude : props.zone?.effective_latitude,
  longitude: hasOwnCoords.value ? form.value.longitude : props.zone?.effective_longitude,
}))
const zoneMapEmbedUrl = computed(() => (zoneLocationQuery.value ? googleMapsEmbedUrl(zoneLocationQuery.value) : ''))
const zoneMapLink = computed(() => googleMapsSearchUrl(zoneLocationQuery.value))

function copyInheritedLocation() {
  form.value.latitude = props.zone?.effective_latitude
  form.value.longitude = props.zone?.effective_longitude
  form.value.address_line1 = props.zone?.effective_address_line1 || ''
  form.value.address_line2 = props.zone?.effective_address_line2 || ''
  form.value.postal_code = props.zone?.effective_postal_code || ''
  form.value.city = props.zone?.effective_city || ''
  form.value.country = props.zone?.effective_country || ''
}

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
      rotation: Number(form.value.rotation) || 0,
      color: form.value.color || null,
      latitude: form.value.latitude != null && form.value.latitude !== '' ? Number(form.value.latitude) : null,
      longitude: form.value.longitude != null && form.value.longitude !== '' ? Number(form.value.longitude) : null,
      address_line1: form.value.address_line1?.trim() || null,
      address_line2: form.value.address_line2?.trim() || null,
      postal_code: form.value.postal_code?.trim() || null,
      city: form.value.city?.trim() || null,
      country: form.value.country?.trim() || null,
    }

    if (props.zone) {
      await store.updateZone(props.zone.id, payload)
      $q.notify({ type: 'positive', message: t('inventory.locationUpdated') })
    } else {
      await store.createZone(payload)
      $q.notify({ type: 'positive', message: t('inventory.locationCreated') })
    }

    emit('saved')
    emit('update:modelValue', false)
  } catch (err) {
    error.value = err?.response?.data?.detail || t('inventory.failedToSaveLocation')
  } finally {
    saving.value = false
  }
}
</script>
