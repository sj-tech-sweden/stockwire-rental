<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="$emit('update:modelValue', $event)">
    <q-card style="width: 560px; max-width: 95vw" class="ec-card">
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
            <div class="col-12 col-md-6">
              <q-toggle v-model="autoGenerateCode" :label="t('inventory.autoGenerateCode')" color="primary" />
            </div>
          </div>
          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-12 col-md-4">
              <q-input v-model="form.barcode" label="Barcode" outlined dense />
            </div>
            <div class="col-12 col-md-4">
              <q-input v-model="form.qr_code" label="QR code" outlined dense />
            </div>
            <div class="col-12 col-md-4">
              <q-input v-model="form.rfid" label="RFID" outlined dense />
            </div>
          </div>
          <q-select
            v-model="form.zone_type"
            :options="locationTypeOptions"
            :label="t('inventory.type')"
            outlined
            dense
            emit-value
            map-options
            class="q-mb-sm"
          />
          <q-select v-model="form.parent_id" :options="parentLocationOptions" :label="t('inventory.parentLocation')" outlined dense clearable emit-value map-options class="q-mb-sm" />
          <q-input v-model.number="form.sort_order" type="number" :label="t('inventory.sortOrder')" outlined dense class="q-mb-sm" />
          <q-toggle v-model="form.is_active" :label="t('settings.auth.active')" color="primary" />
          <q-banner v-if="error" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ error }}</q-banner>
        </q-form>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="$emit('update:modelValue', false)" />
        <q-btn color="primary" unelevated :label="zone ? 'Save' : 'Create'" :loading="saving" @click="save" />
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
