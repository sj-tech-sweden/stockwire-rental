<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="emit('update:modelValue', $event)">
    <q-card style="width: 460px; max-width: 95vw" class="ec-card">
      <q-card-section>
        <div class="text-h6">{{ userEditing ? t('settings.auth.editUser') : t('settings.auth.newUser') }}</div>
      </q-card-section>
      <q-card-section class="q-pt-none">
        <q-form ref="formRef" @submit.prevent="save">
          <q-input v-model="form.full_name" :label="t('settings.auth.fullName')" outlined dense class="q-mb-sm" :rules="[v => !!v || t('login.required')]" />
          <q-input v-model="form.email" :label="t('settings.auth.email')" type="email" outlined dense class="q-mb-sm" :rules="[v => !!v || t('login.required')]" />
          <q-input
            v-model="form.password"
            :label="userEditing ? t('settings.auth.newPasswordOptional') : t('settings.auth.password')"
            type="password"
            outlined
            dense
            class="q-mb-sm"
            :rules="userEditing ? [] : [v => !!v || t('login.required')]"
          />
          <q-select
            v-model="form.role"
            :options="roleOptions"
            :label="t('settings.auth.role')"
            outlined
            dense
            emit-value
            map-options
            class="q-mb-sm"
          />
          <q-toggle v-model="form.is_active" :label="t('settings.auth.active')" color="primary" />
          <q-banner v-if="dialogError" class="bg-negative text-white q-mt-sm rounded-borders" dense>
            {{ dialogError }}
          </q-banner>
        </q-form>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="emit('update:modelValue', false)" />
        <q-btn color="primary" unelevated :loading="saving" :label="t('app.actions.save')" @click="save" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'

const props = defineProps({
  modelValue: Boolean,
  user: { type: Object, default: null },
})

const emit = defineEmits([
  'update:modelValue',
  'saved',
])

const $q = useQuasar()
const { t } = useI18n()
const authStore = useAuthStore()

const saving = ref(false)
const dialogError = ref('')
const formRef = ref(null)
const userEditing = ref(null)

const roleOptions = computed(() => [
  { label: t('settings.auth.roleAdmin'), value: 'admin' },
  { label: t('settings.auth.roleManager'), value: 'manager' },
  { label: t('settings.auth.roleViewer'), value: 'viewer' },
])

const emptyForm = () => ({
  full_name: '',
  email: '',
  password: '',
  role: 'viewer',
  is_active: true,
})

const form = ref(emptyForm())

async function save() {
  const valid = await formRef.value?.validate()
  if (!valid) return

  saving.value = true
  dialogError.value = ''
  try {
    const payload = { ...form.value }
    if (userEditing.value && !payload.password) delete payload.password

    if (userEditing.value) {
      await authStore.updateUser(userEditing.value.id, payload)
      $q.notify({ type: 'positive', message: t('settings.auth.userUpdated') })
    } else {
      await authStore.createUser(payload)
      $q.notify({ type: 'positive', message: t('settings.auth.userCreated') })
    }
    emit('update:modelValue', false)
    emit('saved')
  } catch (error) {
    dialogError.value = error?.response?.data?.detail || t('settings.auth.failedSaveUser')
  } finally {
    saving.value = false
  }
}

watch(() => props.modelValue, (open) => {
  if (open) {
    userEditing.value = props.user
    if (props.user) {
      form.value = {
        full_name: props.user.full_name,
        email: props.user.email,
        password: '',
        role: props.user.role,
        is_active: props.user.is_active,
      }
    } else {
      form.value = emptyForm()
    }
    dialogError.value = ''
  }
})
</script>
