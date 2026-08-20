<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="emit('update:modelValue', $event)">
    <q-card style="width: 480px; max-width: 95vw" class="ec-card">
      <q-card-section>
        <div class="text-h6">{{ t('companies.newCompany') }}</div>
      </q-card-section>

      <q-card-section class="q-pt-none">
        <q-form ref="formRef" @submit.prevent="saveCompany">
          <q-input
            v-model="form.name"
            :label="t('companies.name')"
            outlined
            dense
            class="q-mb-sm"
            :rules="[v => !!v || t('common.required')]"
          />
          <q-input v-model="form.address" :label="t('companies.address')" outlined dense class="q-mb-sm" />
          <div class="row q-col-gutter-sm">
            <div class="col-12 col-md-6">
              <q-input v-model="form.city" :label="t('companies.city')" outlined dense class="q-mb-sm" />
            </div>
            <div class="col-12 col-md-6">
              <q-input v-model="form.postal_code" :label="t('companies.postalCode')" outlined dense class="q-mb-sm" />
            </div>
          </div>
          <q-select v-model="form.country" :options="COUNTRIES" :label="t('companies.country')" outlined dense clearable emit-value map-options class="q-mb-sm" />
          <q-input v-model="form.notes" :label="t('companies.notes')" type="textarea" autogrow outlined dense />

          <q-banner v-if="dialogError" class="bg-negative text-white q-mt-sm rounded-borders" dense>
            {{ dialogError }}
          </q-banner>
        </q-form>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="emit('update:modelValue', false)" />
        <q-btn color="primary" unelevated :label="t('companies.create')" :loading="saving" @click="saveCompany" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useCompaniesStore } from '../stores/companies'
import { useSettingsStore } from '../stores/settings'
import { COUNTRIES } from '../constants/countries'

const props = defineProps({
  modelValue: Boolean,
})

const emit = defineEmits([
  'update:modelValue',
  'saved',
])

const $q = useQuasar()
const { t } = useI18n()
const store = useCompaniesStore()

const saving = ref(false)
const dialogError = ref('')
const formRef = ref(null)

const emptyForm = () => ({
  name: '',
  address: '',
  city: '',
  postal_code: '',
  country: '',
  notes: '',
  is_customer: true,
  is_product_supplier: false,
  is_rental_supplier: false,
  is_crew_supplier: false,
})

const form = ref(emptyForm())

async function saveCompany() {
  const valid = await formRef.value?.validate()
  if (!valid) return

  saving.value = true
  dialogError.value = ''
  try {
    const payload = {
      ...form.value,
      name: form.value.name.trim(),
      address: form.value.address?.trim() || null,
      city: form.value.city?.trim() || null,
      postal_code: form.value.postal_code?.trim() || null,
      country: form.value.country?.trim() || null,
      notes: form.value.notes?.trim() || null,
    }

    const saved = await store.createCompany(payload)
    emit('update:modelValue', false)
    $q.notify({ type: 'positive', message: t('companies.createdNotice') })
    emit('saved', saved)
  } catch (error) {
    dialogError.value = error?.response?.data?.detail || t('common.errorOccurred')
  } finally {
    saving.value = false
  }
}

watch(() => props.modelValue, (open) => {
  if (open) {
    form.value = emptyForm()
    const settingsStore = useSettingsStore()
    if (settingsStore.companyProfile?.default_country) {
      form.value.country = settingsStore.companyProfile.default_country
    }
    dialogError.value = ''
  }
})
</script>
