<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="emit('update:modelValue', $event)">
    <q-card class="ec-card">
      <q-card-section class="row items-center">
        <q-icon name="warning" color="negative" size="md" class="q-mr-md" />
        <span>{{ t('persons.deletePrompt', { name: personFullName }) }}</span>
      </q-card-section>
      <q-card-section v-if="deleteError" class="q-pt-none">
        <q-banner class="bg-warning text-dark rounded-borders">
          {{ deleteError }}
        </q-banner>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="onCancel" />
        <q-btn v-if="authStore.canEdit" color="negative" unelevated :label="t('persons.delete')" :loading="saving" @click="doDelete" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { usePersonsStore } from '../stores/persons'
import { useAuthStore } from '../stores/auth'

const props = defineProps({
  modelValue: Boolean,
  person: { type: Object, default: null },
})

const emit = defineEmits([
  'update:modelValue',
  'deleted',
])

const $q = useQuasar()
const { t } = useI18n()
const store = usePersonsStore()
const authStore = useAuthStore()

const saving = ref(false)
const deleteError = ref('')

const personFullName = computed(() => {
  if (!props.person) return ''
  return `${props.person.first_name || ''} ${props.person.last_name || ''}`.trim()
})

function onCancel() {
  deleteError.value = ''
  emit('update:modelValue', false)
}

async function doDelete() {
  if (!props.person) return
  saving.value = true
  deleteError.value = ''
  try {
    await store.deletePerson(props.person.id)
    emit('update:modelValue', false)
    $q.notify({ type: 'positive', message: t('persons.deleted') })
    emit('deleted')
  } catch (error) {
    const detail = error?.response?.data?.detail
    if (typeof detail === 'object' && detail.error === 'person_has_crew_member') {
      deleteError.value = t('persons.deleteBlockedCrewMember')
    } else {
      $q.notify({ type: 'negative', message: detail || t('common.deleteFailed') })
    }
  } finally {
    saving.value = false
  }
}
</script>
