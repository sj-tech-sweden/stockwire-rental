<template>
  <q-page class="q-pa-md">
    <q-card class="ec-card q-pa-md" style="max-width: 720px; margin: 0 auto;">
      <div class="text-h6 q-mb-sm">{{ t('profile.title') }}</div>
      <div class="text-caption text-grey-7 q-mb-md">
        {{ t('profile.description') }}
      </div>

      <q-banner v-if="isSsoManaged" class="bg-warning text-dark rounded-borders q-mb-md" dense>
        {{ t('profile.managedBanner', { provider: managedProviderLabel }) }}
      </q-banner>

      <q-form @submit.prevent="saveProfile">
        <div class="row q-col-gutter-sm">
          <div class="col-12 col-md-6">
            <q-input
              v-model="form.full_name"
              :label="t('profile.fullName')"
              outlined
              dense
              :disable="isSsoManaged || saving"
              :rules="[v => !!String(v || '').trim() || t('login.required')]"
            />
          </div>
          <div class="col-12 col-md-6">
            <q-input
              v-model="form.email"
              :label="t('profile.email')"
              outlined
              dense
              :disable="isSsoManaged || saving"
              :rules="[v => !!String(v || '').trim() || t('login.required')]"
            />
          </div>
          <div class="col-12 col-md-6">
            <q-input
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              :label="t('profile.newPassword')"
              outlined
              dense
              :disable="isSsoManaged || saving"
            >
              <template #append>
                <q-icon
                  :name="showPassword ? 'visibility_off' : 'visibility'"
                  class="cursor-pointer"
                  @click="showPassword = !showPassword"
                />
              </template>
            </q-input>
          </div>
          <div class="col-12 col-md-6">
            <q-select
              v-model="userLocale"
              :options="localeOptions"
              emit-value
              map-options
              dense
              outlined
              :label="t('app.language.userLanguage')"
              :disable="saving || !authStore.me?.id"
              @update:model-value="onUserLocaleChange"
            />
          </div>
        </div>

        <div class="row items-center q-gutter-sm q-mt-md">
          <q-btn
            type="submit"
            color="primary"
            icon="save"
            :label="t('profile.save')"
            unelevated
            :loading="saving"
            :disable="isSsoManaged"
          />
        </div>
      </q-form>
    </q-card>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'

import { useAuthStore } from '../stores/auth'
import { resolveAppLocale, setLocale, setUserLocalePreference } from '../i18n'

const $q = useQuasar()
const authStore = useAuthStore()
const { t } = useI18n()

const saving = ref(false)
const showPassword = ref(false)
const userLocale = ref('en')
const form = ref({
  full_name: '',
  email: '',
  password: '',
})
const localeOptions = computed(() => [
  { label: t('app.language.english'), value: 'en' },
  { label: t('app.language.swedish'), value: 'sv' },
])

const authSource = computed(() => String(authStore.me?.auth_source || 'local').toLowerCase())
const isSsoManaged = computed(() => ['oidc', 'saml'].includes(authSource.value))
const managedProviderLabel = computed(() => {
  const provider = String(authStore.me?.external_provider || '').trim()
  if (provider) return provider
  if (authSource.value === 'oidc') return 'OIDC'
  if (authSource.value === 'saml') return 'SAML'
  return 'SSO'
})

function applyFormFromMe() {
  form.value = {
    full_name: String(authStore.me?.full_name || '').trim(),
    email: String(authStore.me?.email || '').trim(),
    password: '',
  }
}

function onUserLocaleChange(value) {
  const locale = setLocale(value)
  userLocale.value = locale
  if (authStore.me?.id) {
    setUserLocalePreference(authStore.me.id, locale)
  }
}

async function saveProfile() {
  if (isSsoManaged.value) return
  saving.value = true
  try {
    await authStore.updateMyProfile({
      full_name: form.value.full_name,
      email: form.value.email,
      password: form.value.password,
    })
    form.value.password = ''
    $q.notify({ type: 'positive', message: t('profile.updated') })
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error?.response?.data?.detail || t('profile.updateFailed'),
    })
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    await authStore.fetchMe()
  } catch {
    // Ignore fetch errors, form will use local cached user if available.
  }
  applyFormFromMe()
  userLocale.value = setLocale(resolveAppLocale(authStore.me?.id || null))
})
</script>
