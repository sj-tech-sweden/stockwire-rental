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
            <div class="ec-title text-h5 q-mb-xs">Stockwire Rental</div>
            <div class="text-subtitle2 ec-brand-green q-mb-xs">First-time Setup</div>
            <div class="text-caption text-muted">Create your administrator account</div>
          </div>
        </div>
        <div class="q-mb-md">
          <!-- graphical profile/avatar placeholder -->
          <div class="ec-avatar">
            <svg width="72" height="72" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="12" r="12" fill="#0B1220" />
              <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-3.31 0-6 2.69-6 6h12c0-3.31-2.69-6-6-6z" fill="#19A974" />
            </svg>
          </div>
        </div>
      </div>

      <q-form @submit.prevent="submit">
        <q-input
          v-model="fullName"
          label="Full name"
          outlined
          dense
          class="q-mb-sm"
          autocomplete="name"
          :rules="[v => !!v || 'Required']"
        />
        <q-input
          v-model="email"
          label="Email"
          type="email"
          outlined
          dense
          class="q-mb-sm"
          autocomplete="email"
          :rules="[v => !!v || 'Required']"
        />
        <q-input
          v-model="password"
          label="Password"
          :type="showPw ? 'text' : 'password'"
          outlined
          dense
          class="q-mb-sm"
          autocomplete="new-password"
          :rules="[v => v.length >= 8 || 'Min 8 characters']"
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
          label="Confirm password"
          :type="showPw ? 'text' : 'password'"
          outlined
          dense
          class="q-mb-md"
          autocomplete="new-password"
          :rules="[v => v === password || 'Passwords do not match']"
        />

        <q-banner v-if="error" class="bg-negative text-white q-mb-md rounded-borders" dense>
          {{ error }}
        </q-banner>

        <q-btn
          type="submit"
          label="Create admin account"
          color="primary"
          class="full-width"
          :loading="loading"
          unelevated
        />
      </q-form>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const router = useRouter()

const fullName = ref('')
const email = ref('')
const password = ref('')
const confirm = ref('')
const showPw = ref(false)
const loading = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await authStore.setup(email.value, password.value, fullName.value)
    router.push('/')
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Setup failed'
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
  color: #e6eef3; /* ensure readable text on dark theme */
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
