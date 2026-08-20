<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="emit('update:modelValue', $event)">
    <q-card style="width: 480px; max-width: 95vw" class="ec-card">
      <q-card-section>
        <div class="text-h6">{{ t('persons.newPerson') }}</div>
      </q-card-section>

      <q-card-section class="q-pt-none">
        <q-form ref="formRef" @submit.prevent="savePerson">
          <div class="row q-col-gutter-sm">
            <div class="col-6">
              <q-input
                v-model="form.first_name"
                :label="t('persons.firstName')"
                outlined
                dense
                class="q-mb-sm"
                :rules="[v => !!v || t('common.required')]"
              />
            </div>
            <div class="col-6">
              <q-input
                v-model="form.last_name"
                :label="t('persons.lastName')"
                outlined
                dense
                class="q-mb-sm"
                :rules="[v => !!v || t('common.required')]"
              />
            </div>
          </div>
          <q-input v-model="form.email" :label="t('profile.email')" type="email" outlined dense class="q-mb-sm" />
          <q-input v-model="form.phone" :label="t('persons.phone')" outlined dense class="q-mb-sm" />
          <q-select
            v-model="form.company_id"
            :options="companyOptions"
            :label="t('persons.company')"
            outlined
            dense
            clearable
            emit-value
            map-options
            use-input
            input-debounce="300"
            @filter="filterCompanies"
            class="q-mb-sm"
          />

          <q-banner v-if="dialogError" class="bg-negative text-white q-mt-sm rounded-borders" dense>
            {{ dialogError }}
          </q-banner>
        </q-form>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="emit('update:modelValue', false)" />
        <q-btn color="primary" unelevated :label="t('persons.create')" :loading="saving" @click="savePerson" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { usePersonsStore } from '../stores/persons'
import { useCompaniesStore } from '../stores/companies'

const props = defineProps({
  modelValue: Boolean,
  companyId: { type: Number, default: null },
})

const emit = defineEmits([
  'update:modelValue',
  'saved',
])

const $q = useQuasar()
const { t } = useI18n()
const personsStore = usePersonsStore()
const companiesStore = useCompaniesStore()

const saving = ref(false)
const dialogError = ref('')
const formRef = ref(null)
const companyFilter = ref('')

const emptyForm = () => ({
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  company_id: null,
})

const form = ref(emptyForm())

const companyOptions = computed(() => {
  const companies = companiesStore.companies || []
  if (companyFilter.value) {
    return companies
      .filter(c => c.name.toLowerCase().includes(companyFilter.value.toLowerCase()))
      .map(c => ({ label: c.name, value: c.id }))
  }
  return companies.map(c => ({ label: c.name, value: c.id }))
})

function filterCompanies(val, update) {
  companyFilter.value = val
  update()
}

async function savePerson() {
  const valid = await formRef.value?.validate()
  if (!valid) return

  saving.value = true
  dialogError.value = ''
  try {
    const payload = {
      ...form.value,
      first_name: form.value.first_name.trim(),
      last_name: form.value.last_name.trim(),
      email: form.value.email?.trim() || null,
      phone: form.value.phone?.trim() || null,
    }

    const saved = await personsStore.createPerson(payload)
    emit('update:modelValue', false)
    $q.notify({ type: 'positive', message: t('persons.createdNotice') })
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
    if (props.companyId) {
      form.value.company_id = props.companyId
    }
    dialogError.value = ''
    companiesStore.fetchAll().catch(() => {})
  }
})
</script>
