<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="emit('update:modelValue', $event)">
    <q-card style="width: 460px; max-width: 95vw" class="ec-card">
      <q-card-section>
        <div class="text-h6">{{ t('settings.auth.createApiKeyTitle') }}</div>
      </q-card-section>
      <q-card-section class="q-pt-none">
        <q-input v-model="form.name" :label="t('users.keyName')" outlined dense class="q-mb-sm" />
        <div class="row items-start q-col-gutter-sm q-mb-sm">
          <div class="col">
            <q-input v-model="form.raw_key" :label="t('settings.auth.rawKey')" outlined dense :hint="t('settings.auth.rawKeyHint')" />
          </div>
          <q-btn dense flat icon="autorenew" color="primary" @click="generateKey" class="q-mt-md" />
          <q-btn dense flat icon="content_copy" color="primary" @click="copyKey" class="q-mt-md" />
        </div>
        <q-toggle v-model="form.is_admin" :label="t('settings.auth.adminKey')" color="primary" />
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="emit('update:modelValue', false)" />
        <q-btn color="primary" unelevated :loading="saving" :label="t('users.create')" @click="save" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from 'src/stores/auth'

defineProps({
  modelValue: Boolean,
})

const emit = defineEmits([
  'update:modelValue',
  'saved',
])

const $q = useQuasar()
const { t } = useI18n()
const authStore = useAuthStore()

const saving = ref(false)
const form = ref({ name: '', raw_key: '', is_admin: false })

function generateKey() {
  const array = new Uint8Array(32)
  crypto.getRandomValues(array)
  form.value.raw_key = 'sw_' + btoa(String.fromCharCode(...array))
    .replace(/[+/=]/g, '')
    .slice(0, 40)
}

async function copyKey() {
  const key = form.value.raw_key
  if (!key) return
  try {
    await navigator.clipboard.writeText(key)
    $q.notify({ type: 'positive', message: t('settings.auth.apiKeyCopied') })
  } catch {
    $q.notify({ type: 'negative', message: t('settings.auth.apiKeyCopyFailed') })
  }
}

async function save() {
  if (!form.value.name || !form.value.raw_key) {
    $q.notify({ type: 'warning', message: t('settings.auth.apiKeyNameRawRequired') })
    return
  }

  saving.value = true
  try {
    await authStore.createApiKey(form.value)
    emit('update:modelValue', false)
    $q.notify({ type: 'positive', message: t('settings.auth.apiKeyCreated') })
    emit('saved')
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('settings.auth.failedCreateApiKey') })
  } finally {
    saving.value = false
  }
}

watch(() => form.value.raw_key, (val) => {
  if (!val) generateKey()
})

watch(() => props.modelValue, (open) => {
  if (open) {
    form.value = { name: '', raw_key: '', is_admin: false }
    generateKey()
  }
})
</script>
