<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="$emit('update:modelValue', $event)">
    <q-card class="ec-card">
      <q-card-section>
        <div class="text-h6">{{ t('inventory.bulkDelete') }}</div>
        <div class="text-caption text-grey-7">{{ t('inventory.bulkDeleteConfirm', { count: deleteTarget?.count || 0 }) }}</div>
        <q-banner v-if="error" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ error }}</q-banner>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="$emit('update:modelValue', false)" />
        <q-btn color="negative" unelevated :label="t('inventory.bulkDelete')" :loading="saving" @click="confirm" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useInventoryStore } from '../stores/inventory'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  deleteTarget: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:modelValue', 'deleted'])

const $q = useQuasar()
const { t } = useI18n()
const store = useInventoryStore()
const saving = ref(false)
const error = ref('')

async function confirm() {
  const ids = props.deleteTarget?.ids || []
  if (!ids.length) return
  saving.value = true
  error.value = ''
  try {
    const res = await store.deleteZonesBulk(ids)
    $q.notify({ type: 'positive', message: `${res.deleted} location(s) deleted` })
    emit('deleted', res)
    emit('update:modelValue', false)
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.message || 'Failed to delete locations'
  } finally {
    saving.value = false
  }
}
</script>
