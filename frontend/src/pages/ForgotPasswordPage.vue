<template>
  <q-page class="ec-auth-page flex flex-center">
    <q-card class="ec-auth-card q-pa-lg" style="width: 380px">
      <div class="text-center q-mb-lg">
        <div class="ec-title text-h5 q-mb-xs">{{ companyName || 'Stockwire Rental' }}</div>
        <div class="text-caption text-grey">{{ t('forgotPassword.subtitle') }}</div>
      </div>

      <q-banner v-if="sent" class="bg-positive text-white q-mb-md rounded-borders" dense>
        {{ t('forgotPassword.emailSent') }}
      </q-banner>

      <q-form v-if="!sent" @submit.prevent="submit">
        <q-input
          v-model="email"
          :label="t('forgotPassword.email')"
          type="email"
          outlined
          dense
          class="q-mb-md"
          autocomplete="email"
          :rules="[v => !!v || t('login.required')]"
        />

        <q-banner v-if="error" class="bg-negative text-white q-mb-md rounded-borders" dense>
          {{ error }}
        </q-banner>

        <q-btn
          type="submit"
          :label="t('forgotPassword.send')"
          color="primary"
          class="full-width"
          :loading="loading"
          unelevated
        />
      </q-form>

      <div class="text-center q-mt-md">
        <q-btn
          :label="t('forgotPassword.backToLogin')"
          color="grey-7"
          flat
          dense
          size="sm"
          :to="{ name: 'login' }"
        />
      </div>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const { t } = useI18n()

const email = ref('')
const loading = ref(false)
const error = ref('')
const sent = ref(false)
const companyName = ref('Stockwire Rental')

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await authStore.forgotPassword(email.value)
    sent.value = true
  } catch (e) {
    error.value = e?.response?.data?.detail || t('forgotPassword.failed')
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
