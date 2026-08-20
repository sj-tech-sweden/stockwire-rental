<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="emit('update:modelValue', $event)">
    <q-card class="ec-card">
      <q-card-section class="row items-center">
        <q-icon name="warning" color="negative" size="md" class="q-mr-md" />
        <span>{{ t('companies.deletePrompt', { name: company?.name || '' }) }}</span>
      </q-card-section>
      <q-card-section v-if="deleteError" class="q-pt-none">
        <q-banner class="bg-warning text-dark rounded-borders">
          {{ deleteError }}
        </q-banner>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="onCancel" />
        <q-btn v-if="authStore.canEdit" color="negative" unelevated :label="t('companies.delete')" :loading="saving" @click="doDelete" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useCompaniesStore } from '../stores/companies'
import { useAuthStore } from '../stores/auth'

const props = defineProps({
  modelValue: Boolean,
  company: { type: Object, default: null },
})

const emit = defineEmits([
  'update:modelValue',
  'deleted',
])

const $q = useQuasar()
const { t } = useI18n()
const store = useCompaniesStore()
const authStore = useAuthStore()

const saving = ref(false)
const deleteError = ref('')

function onCancel() {
  deleteError.value = ''
  emit('update:modelValue', false)
}

async function doDelete() {
  if (!props.company) return
  saving.value = true
  deleteError.value = ''
  try {
    await store.deleteCompany(props.company.id)
    emit('update:modelValue', false)
    $q.notify({ type: 'positive', message: t('companies.deleted') })
    emit('deleted')
  } catch (error) {
    const detail = error?.response?.data?.detail
    if (typeof detail === 'object' && detail.error === 'supplier_has_products') {
      deleteError.value = t('companies.deleteBlockedProducts', { count: detail.product_ids?.length || 0 })
    } else if (typeof detail === 'object' && detail.error === 'supplier_has_devices') {
      deleteError.value = t('companies.deleteBlockedDevices', { count: detail.device_ids?.length || 0 })
    } else {
      $q.notify({ type: 'negative', message: detail || t('common.deleteFailed') })
    }
  } finally {
    saving.value = false
  }
}
</script>
