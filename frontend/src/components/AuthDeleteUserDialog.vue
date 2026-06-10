<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="emit('update:modelValue', $event)">
    <q-card class="ec-card">
      <q-card-section class="row items-center">
        <q-icon name="warning" color="negative" size="md" class="q-mr-md" />
        <span>{{ t('users.deleteUserConfirm') }}</span>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="emit('update:modelValue', false)" />
        <q-btn color="negative" unelevated :label="t('users.delete')" :loading="saving" @click="doDelete" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  user: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue', 'deleted'])

const $q = useQuasar()
const { t } = useI18n()
const store = useAuthStore()

const saving = ref(false)

async function doDelete() {
  if (!props.user?.id) return
  saving.value = true
  try {
    await store.deleteUser(props.user.id)
    emit('update:modelValue', false)
    emit('deleted')
    $q.notify({ type: 'positive', message: t('customers.deleted') })
  } catch (e) {
    $q.notify({ type: 'negative', message: e?.response?.data?.detail || t('common.deleteFailed') })
  } finally {
    saving.value = false
  }
}
</script>
