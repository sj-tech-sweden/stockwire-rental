<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="$emit('update:modelValue', $event)">
    <q-card class="ec-card">
      <q-card-section class="row items-center">
        <q-icon name="warning" color="negative" size="md" class="q-mr-md" />
        <span>{{ t('inventory.deleteCategoryPrompt', { name: category?.name }) }}</span>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="$emit('update:modelValue', false)" />
        <q-btn color="negative" unelevated :label="t('users.delete')" :loading="saving" @click="doDelete" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQuasar } from 'quasar'
import { useInventoryStore } from '../stores/inventory'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  category: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue', 'deleted'])

const { t } = useI18n()
const $q = useQuasar()
const store = useInventoryStore()

const saving = ref(false)

async function doDelete() {
  if (!props.category) return
  saving.value = true
  try {
    await store.deleteCategory(props.category.id)
    emit('deleted')
    emit('update:modelValue', false)
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || 'Delete failed' })
  } finally {
    saving.value = false
  }
}
</script>
