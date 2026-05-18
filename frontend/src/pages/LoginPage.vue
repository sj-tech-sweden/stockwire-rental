<template>
  <q-page class="ec-auth-page flex flex-center">
    <q-card class="ec-auth-card q-pa-lg" style="width: 380px">
      <div class="text-center q-mb-lg">
        <div class="ec-title text-h5 q-mb-xs">Stockwire Rental</div>
        <div class="text-caption text-grey">Sign in to continue</div>
      </div>

      <q-form @submit.prevent="submit">
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
          class="q-mb-md"
          autocomplete="current-password"
          :rules="[v => !!v || 'Required']"
        >
          <template #append>
            <q-icon
              :name="showPw ? 'visibility_off' : 'visibility'"
              class="cursor-pointer"
              @click="showPw = !showPw"
            />
          </template>
        </q-input>

        <q-banner v-if="error" class="bg-negative text-white q-mb-md rounded-borders" dense>
          {{ error }}
        </q-banner>

        <q-btn
          type="submit"
          label="Sign in"
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

const email = ref('')
const password = ref('')
const showPw = ref(false)
const loading = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await authStore.login(email.value, password.value)
    router.push('/')
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Login failed'
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
</style>
