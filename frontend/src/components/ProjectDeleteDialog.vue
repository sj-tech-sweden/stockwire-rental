<template>
  <q-dialog v-model="dialogOpen" persistent>
    <q-card class="ec-card">
      <q-card-section class="row items-center q-gutter-sm">
        <q-icon name="warning" color="negative" size="md" />
        <span>{{ t('projects.deletePrompt', { name: project?.name || '' }) }}</span>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" v-close-popup />
        <q-btn color="negative" :label="t('projects.delete')" :loading="deleting" unelevated @click="confirmDelete" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'

import { useProjectsStore } from '../stores/projects'

const props = defineProps({
  modelValue: Boolean,
  project: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue', 'deleted'])

const $q = useQuasar()
const { t } = useI18n()
const projectsStore = useProjectsStore()

const dialogOpen = computed({ get: () => props.modelValue, set: v => emit('update:modelValue', v) })
const deleting = ref(false)

async function confirmDelete() {
  deleting.value = true
  try {
    await projectsStore.deleteProject(props.project.id)
    emit('deleted')
    dialogOpen.value = false
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('common.errorOccurred') })
  } finally {
    deleting.value = false
  }
}
</script>
