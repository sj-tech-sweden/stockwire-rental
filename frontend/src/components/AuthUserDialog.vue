<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="emit('update:modelValue', $event)">
    <q-card style="min-width: 400px" class="ec-card">
      <q-card-section>
        <div class="text-h6">{{ editing ? t('users.editUser') : t('users.createUser') }}</div>
      </q-card-section>

      <q-card-section class="q-pt-none">
        <q-form @submit.prevent="save" ref="formRef">
          <q-input
            v-model="form.full_name"
            :label="t('profile.fullName')"
            outlined
            dense
            class="q-mb-sm"
            :rules="[v => !!v || t('login.required')]"
          />
          <q-input
            v-model="form.email"
            :label="t('profile.email')"
            type="email"
            outlined
            dense
            class="q-mb-sm"
            :rules="[v => !!v || t('login.required')]"
          />
          <q-input
            v-model="form.password"
            :label="editing ? t('users.newPasswordOptional') : t('login.password')"
            type="password"
            outlined
            dense
            class="q-mb-sm"
            :rules="editing ? [] : [v => !!v || t('login.required')]"
          />
          <q-select
            v-model="form.role"
            :options="roleOptions"
            :label="t('users.roles')"
            outlined
            dense
            emit-value
            map-options
            class="q-mb-sm"
            :rules="[v => !!v || t('login.required')]"
          />
          <q-toggle v-model="form.is_active" :label="t('users.active')" color="primary" />

          <q-banner v-if="dialogError" class="bg-negative text-white q-mt-sm rounded-borders" dense>
            {{ dialogError }}
          </q-banner>
        </q-form>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="emit('update:modelValue', false)" />
        <q-btn
          color="primary"
          unelevated
          :label="editing ? t('app.actions.save') : t('users.create')"
          :loading="saving"
          @click="save"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  user: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const $q = useQuasar()
const { t } = useI18n()
const store = useAuthStore()

const editing = ref(null)
const saving = ref(false)
const dialogError = ref('')
const formRef = ref(null)

const emptyForm = () => ({ full_name: '', email: '', password: '', role: 'viewer', is_active: true })
const form = ref(emptyForm())

const roleOptions = [
  { label: t('users.admin'), value: 'admin' },
  { label: t('users.manager'), value: 'manager' },
  { label: t('users.viewer'), value: 'viewer' },
]

function initCreate() {
  editing.value = null
  form.value = emptyForm()
  dialogError.value = ''
}

function initEdit(user) {
  editing.value = user
  form.value = { full_name: user.full_name, email: user.email, password: '', role: user.role, is_active: user.is_active }
  dialogError.value = ''
}

async function save() {
  const valid = await formRef.value?.validate()
  if (!valid) return
  saving.value = true
  dialogError.value = ''
  try {
    const payload = { ...form.value }
    if (editing.value && !payload.password) delete payload.password
    if (editing.value) {
      await store.updateUser(editing.value.id, payload)
    } else {
      await store.createUser(payload)
    }
    emit('update:modelValue', false)
    $q.notify({ type: 'positive', message: editing.value ? t('customers.updated') : t('customers.createdNotice') })
  } catch (e) {
    dialogError.value = e?.response?.data?.detail || t('common.errorOccurred')
  } finally {
    saving.value = false
  }
}

watch(() => props.modelValue, (open) => {
  if (open) {
    if (props.user) {
      initEdit(props.user)
    } else {
      initCreate()
    }
  }
})
</script>
