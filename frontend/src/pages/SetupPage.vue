<template>
  <q-page class="ec-auth-page flex flex-center">
    <q-card class="ec-auth-card q-pa-lg" style="width: 420px">
      <div class="text-center q-mb-lg">
        <div class="row items-center justify-center q-mb-sm" style="gap:12px">
          <div class="ec-logo" aria-hidden>
            <!-- simple inline SVG logo (blue) -->
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect width="24" height="24" rx="4" fill="#1E88E5" />
              <path d="M6 12h12v2H6z" fill="white" opacity="0.9" />
            </svg>
          </div>
          <div>
            <div class="ec-title text-h5 q-mb-xs">{{ t('app.name') }}</div>
            <div class="text-subtitle2 ec-brand-green q-mb-xs">{{ t('setup.title') }}</div>
            <div class="text-caption text-muted">{{ t('setup.subtitle') }}</div>
          </div>
        </div>
        <div class="q-mb-md">
          <!-- graphical profile/avatar placeholder -->
          <div class="ec-avatar">
            <svg width="72" height="72" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="12" r="12" fill="#0B1220" />
              <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-3.31 0-6 2.69-6 6h12c0-3.31-2.69-6-6-6z" fill="#3F873F" />
            </svg>
          </div>
        </div>
      </div>

      <q-form @submit.prevent="submit">
        <q-input
          v-model="fullName"
          :label="t('profile.fullName')"
          outlined
          dense
          class="q-mb-sm"
          autocomplete="name"
          :rules="[v => !!v || t('login.required')]"
        />
        <q-input
          v-model="email"
          :label="t('profile.email')"
          type="email"
          outlined
          dense
          class="q-mb-sm"
          autocomplete="email"
          :rules="[v => !!v || t('login.required')]"
        />
        <q-input
          v-model="password"
          :label="t('login.password')"
          :type="showPw ? 'text' : 'password'"
          outlined
          dense
          class="q-mb-sm"
          autocomplete="new-password"
          maxlength="72"
          :rules="[v => v.length >= 8 || t('setup.minLength'), v => (v || '').length <= 72 || t('setup.maxLength')]"
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
          v-model="confirm"
          :label="t('setup.confirmPassword')"
          :type="showPw ? 'text' : 'password'"
          outlined
          dense
          class="q-mb-md"
          autocomplete="new-password"
          maxlength="72"
          :rules="[v => v === password || t('setup.passwordMismatch')]"
        />

        <q-banner v-if="error" class="bg-negative text-white q-mb-md rounded-borders" dense>
          {{ error }}
        </q-banner>

        <div v-if="alreadySetup">
          <q-banner class="bg-info text-white q-mb-md rounded-borders" dense>
            {{ t('setup.alreadySetup') }}
          </q-banner>
          <q-btn :label="t('setup.goToLogin')" color="primary" class="full-width" @click="() => router.push('/login')" />
        </div>
        <div v-else>
          <q-btn
            type="submit"
            :label="t('setup.createAdmin')"
            color="primary"
            class="full-width"
            :loading="loading"
            unelevated
          />
        </div>
      </q-form>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const { t } = useI18n()

const fullName = ref('')
const email = ref('')
const password = ref('')
const confirm = ref('')
const showPw = ref(false)
const loading = ref(false)
const error = ref('')
const alreadySetup = ref(false)

onMounted(async () => {
  try {
    const setupNeeded = await authStore.checkBootstrap()
    if (!setupNeeded) {
      alreadySetup.value = true
    }
  } catch (e) {
    // ignore bootstrap check errors; allow submit to show errors
  }
})

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await authStore.setup(email.value, password.value, fullName.value)
    router.push('/')
  } catch (e) {
    error.value = e?.response?.data?.detail || t('setup.failed')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.ec-auth-page {
  background: var(--ec-bg);
  min-height: 100vh;
}
.ec-auth-card {
  background: var(--ec-surface);
  border: 1px solid rgba(63,135,63,0.12);
  border-radius: 8px;
  color: var(--ec-text);
}
.ec-brand-green { color: #19A974 !important }
.text-muted { color: #9aa6b2 }
.ec-logo svg { border-radius: 6px }
.ec-avatar { display: inline-flex; justify-content: center; }

/* Ensure Quasar input labels and hints are visible on dark backgrounds */
.ec-auth-card .q-field__label,
.ec-auth-card .q-field__label--float,
.ec-auth-card .q-field__hint {
  color: #cfdfe6 !important;
}
.ec-auth-card .q-field__native {
  color: #e6eef3 !important;
}
</style>
