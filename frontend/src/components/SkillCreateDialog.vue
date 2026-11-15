<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="emit('update:modelValue', $event)">
    <q-card style="width: 420px; max-width: 95vw" class="ec-card">
      <q-card-section>
        <div class="text-h6">{{ t('crew.createSkill') }}</div>
      </q-card-section>

      <q-card-section class="q-pt-none">
        <q-form ref="formRef" @submit.prevent="saveSkill">
          <q-input
            v-model="form.name"
            :label="t('crew.skillName')"
            outlined
            dense
            class="q-mb-sm"
            :rules="[v => !!v || t('common.required')]"
          />
          <q-input
            v-model="form.category"
            :label="t('crew.skillCategory')"
            outlined
            dense
            :placeholder="t('crew.skillCategoryPlaceholder')"
          />

          <q-banner v-if="dialogError" class="bg-negative text-white q-mt-sm rounded-borders" dense>
            {{ dialogError }}
          </q-banner>
        </q-form>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="emit('update:modelValue', false)" />
        <q-btn color="primary" unelevated :label="t('app.actions.create')" :loading="saving" @click="saveSkill" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useCrewStore } from '../stores/crew'

const props = defineProps({
  modelValue: Boolean,
})

const emit = defineEmits(['update:modelValue', 'saved'])

const $q = useQuasar()
const { t } = useI18n()
const store = useCrewStore()

const saving = ref(false)
const dialogError = ref('')
const formRef = ref(null)

const emptyForm = () => ({ name: '', category: '' })
const form = ref(emptyForm())

async function saveSkill() {
  const valid = await formRef.value?.validate()
  if (!valid) return

  saving.value = true
  dialogError.value = ''
  try {
    const saved = await store.createSkill({
      name: form.value.name.trim(),
      category: form.value.category?.trim() || null,
    })
    emit('update:modelValue', false)
    $q.notify({ type: 'positive', message: t('crew.skillCreated') })
    emit('saved', saved)
  } catch (error) {
    dialogError.value = error?.response?.data?.detail || t('crew.failedSaveSkill') || t('common.errorOccurred')
  } finally {
    saving.value = false
  }
}

watch(() => props.modelValue, (open) => {
  if (open) {
    form.value = emptyForm()
    dialogError.value = ''
  }
})
</script>
