<template>
  <q-dialog v-model="deleteDialogOpen" persistent>
    <q-card class="ec-card">
      <q-card-section class="row items-center">
        <q-icon name="warning" color="negative" size="md" class="q-mr-md" />
        <span>{{ t('venues.deletePrompt', { name: venue?.name || '' }) }}</span>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="deleteDialogOpen = false" />
        <q-btn v-if="authStore.canEdit" color="negative" unelevated :label="t('venues.delete')" :loading="saving" @click="doDelete" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Notify } from 'quasar'
import { useI18n } from 'vue-i18n'

import { useVenuesStore } from '../stores/venues'
import { useAuthStore } from '../stores/auth'

const props = defineProps({
  modelValue: Boolean,
  venue: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['update:modelValue', 'deleted'])

const { t } = useI18n()
const store = useVenuesStore()
const authStore = useAuthStore()

const deleteDialogOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const saving = ref(false)

async function doDelete() {
  if (!props.venue) return
  saving.value = true
  try {
    await store.deleteVenue(props.venue.id)
    deleteDialogOpen.value = false
    emit('deleted', props.venue)
  } catch (error) {
    Notify.create({ type: 'negative', message: error?.response?.data?.detail || t('common.deleteFailed') })
  } finally {
    saving.value = false
  }
}
</script>
