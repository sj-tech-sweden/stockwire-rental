<template>
  <q-page class="ec-auth-page flex flex-center">
    <q-card class="ec-auth-card q-pa-lg" style="width: 380px">
      <div class="text-center q-mb-lg">
        <div class="ec-title text-h5 q-mb-xs">{{ companyName || 'Stockwire Rental' }}</div>
        <div class="text-caption text-grey">{{ t('resetPassword.subtitle') }}</div>
      </div>

      <q-form @submit.prevent="submit">
        <q-input
          v-model="newPassword"
          :label="t('resetPassword.newPassword')"
          :type="showPw ? 'text' : 'password'"
          outlined
          dense
          class="q-mb-sm"
          autocomplete="new-password"
          :rules="[
            v => !!v || t('login.required'),
            v => v.length >= 8 || t('resetPassword.minLength'),
            v => v.length <= 72 || t('resetPassword.maxLength'),
          ]"
        >
          <template #append>
            <q-icon
              :name="showPw ? 'visibility_off' : 'visibility'"
              class="cursor-pointer"
              @click="showPw = !showPw"
            />
          </template>
        </q-input>

        <q-input
          v-model="confirmPassword"
          :label="t('resetPassword.confirmPassword')"
          :type="'password'"
          outlined
          dense
          class="q-mb-md"
          autocomplete="new-password"
          :rules="[v => v === newPassword || t('resetPassword.passwordMismatch')]"
        />

        <q-banner v-if="error" class="bg-negative text-white q-mb-md rounded-borders" dense>
          {{ error }}
        </q-banner>

        <q-banner v-if="success" class="bg-positive text-white q-mb-md rounded-borders" dense>
          {{ t('resetPassword.success') }}
        </q-banner>

        <q-btn
          v-if="!success"
          type="submit"
          :label="t('resetPassword.reset')"
          color="primary"
          class="full-width"
          :loading="loading"
          unelevated
        />

        <q-btn
          v-if="success"
          :label="t('resetPassword.goToLogin')"
          color="primary"
          class="full-width"
          unelevated
          :to="{ name: 'login' }"
        />
      </q-form>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const newPassword = ref('')
const confirmPassword = ref('')
const showPw = ref(false)
const loading = ref(false)
const error = ref('')
const success = ref(false)
const companyName = ref('Stockwire Rental')

const token = route.params.token

async function submit() {
  if (newPassword.value !== confirmPassword.value) {
    error.value = t('resetPassword.passwordMismatch')
    return
  }
  error.value = ''
  loading.value = true
  try {
    await authStore.resetPassword(token, newPassword.value)
    success.value = true
  } catch (e) {
    error.value = e?.response?.data?.detail || t('resetPassword.failed')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.ec-auth-page {
  background: #0d1117;
  min-height: 100vh;
}
.ec-auth-card {
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 8px;
}
.ec-auth-card :deep(.q-field__label) {
  color: rgba(255,255,255,0.86) !important;
}
.ec-auth-card :deep(.q-field__control),
.ec-auth-card :deep(.q-field__native),
.ec-auth-card :deep(.q-input__control .q-field__control) {
  color: rgba(255,255,255,0.95) !important;
}
</style>
