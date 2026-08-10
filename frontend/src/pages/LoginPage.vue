<template>
  <q-page class="ec-auth-page flex flex-center">
    <q-card class="ec-auth-card q-pa-lg" style="width: 380px">
      <div class="text-center q-mb-lg">
        <q-img
          v-if="companyLogoUrl"
          :src="companyLogoUrl"
          style="width: 120px; height: 72px; margin: 0 auto 8px auto"
          fit="contain"
          spinner-color="primary"
          :alt="companyName || 'Company logo'"
        />
        <div v-if="!companyLogoUrl" class="ec-title text-h5 q-mb-xs">{{ companyName || 'Stockwire Rental' }}</div>
        <div class="text-caption text-grey">{{ t('login.subtitle') }}</div>
      </div>

      <q-select
        v-model="selectedLocale"
        :options="localeOptions"
        emit-value
        map-options
        dense
        outlined
        :label="t('app.language.label')"
        class="q-mb-md"
        @update:model-value="onLocaleChange"
      />

      <q-form @submit.prevent="submit">
        <q-input
          v-model="email"
          :label="t('login.email')"
          type="text"
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
          class="q-mb-md"
          autocomplete="current-password"
          :rules="[v => !!v || t('login.required')]"
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
          :label="t('login.signIn')"
          color="primary"
          class="full-width"
          :loading="loading"
          unelevated
        />

        <div class="text-center q-mt-sm">
          <q-btn
            :label="t('login.forgotPassword')"
            color="grey-7"
            flat
            dense
            size="sm"
            :to="{ name: 'forgot-password' }"
          />
        </div>
      </q-form>

      <q-separator class="q-my-md" dark />

      <div v-if="ssoProviders.length" class="q-gutter-sm">
        <div class="text-caption text-grey-4 q-mb-xs">{{ t('login.sso') }}</div>
        <q-btn
          v-for="provider in ssoProviders"
          :key="`${provider.kind}-${provider.provider}`"
          :label="t('login.continueWith', { provider: provider.display_name })"
          color="grey-8"
          text-color="white"
          class="full-width"
          unelevated
          :loading="ssoLoading"
          @click="startSso(provider)"
        />
      </div>
    </q-card>
  </q-page>
</template>

<script setup>
import axios from 'axios'
import { computed, ref } from 'vue'
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'

import { useAuthStore } from '../stores/auth'
import { resolveLoginLocale, setLocale, setUserLocalePreference } from '../i18n'
import { getApiBaseUrl } from '../utils/runtime-config'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()
const { t } = useI18n()

const email = ref('')
const password = ref('')
const showPw = ref(false)
const loading = ref(false)
const ssoLoading = ref(false)
const error = ref('')
const ssoProviders = ref([])
const companyName = ref('Stockwire Rental')
const companyLogoUrl = ref('')
const selectedLocale = ref('en')

const localeOptions = computed(() => [
  { label: t('app.language.english'), value: 'en' },
  { label: t('app.language.swedish'), value: 'sv' },
])

const apiBaseUrl = getApiBaseUrl()

async function loadPublicBranding() {
  try {
    const { data } = await axios.get(`${apiBaseUrl}/api/v1/storage/public/company-profile`, { timeout: 8000 })
    companyName.value = String(data?.company_name || '').trim() || 'Stockwire Rental'
    selectedLocale.value = setLocale(resolveLoginLocale(data?.default_language))

    const rawLogo = [
      data?.logo_light_wide_url,
      data?.logo_light_small_url,
      data?.logo_url,
    ].map(value => String(value || '').trim()).find(Boolean) || ''

    if (!rawLogo) {
      companyLogoUrl.value = ''
    } else if (/^(https?:|data:|blob:)/i.test(rawLogo)) {
      companyLogoUrl.value = rawLogo
    } else if (rawLogo.startsWith('/')) {
      companyLogoUrl.value = `${apiBaseUrl}${rawLogo}`
    } else {
      companyLogoUrl.value = `${apiBaseUrl}/${rawLogo}`
    }
  } catch {
    companyName.value = 'Stockwire Rental'
    companyLogoUrl.value = ''
    selectedLocale.value = setLocale(resolveLoginLocale('en'))
  }
}

function onLocaleChange(value) {
  selectedLocale.value = setLocale(value)
}

onMounted(async () => {
  await loadPublicBranding()

  if (route.query.reason === 'expired') {
    error.value = t('login.sessionExpired')
  }

  try {
    ssoProviders.value = await authStore.fetchSsoProviders()
  } catch {
    ssoProviders.value = []
  }

  const oidcProvider = String(route.query.oidc_provider || '').trim()
  const code = String(route.query.code || '').trim()
  const oidcState = String(route.query.state || '').trim()
  if (oidcProvider && code) {
    await completeOidcLogin(oidcProvider, code, oidcState)
  }

  const samlProvider = String(route.query.saml_provider || '').trim()
  const samlResponse = String(route.query.saml_response || '').trim()
  if (samlProvider && samlResponse) {
    await completeSamlLogin(samlProvider, samlResponse)
  }
})

function resolveRedirect() {
  return route.query.redirect ||
    sessionStorage.getItem('sw_login_redirect') ||
    '/'
}

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await authStore.login(email.value, password.value)
    setUserLocalePreference(authStore.me?.id || null, selectedLocale.value)
    const redirect = resolveRedirect()
    sessionStorage.removeItem('sw_login_redirect')
    router.push(redirect)
  } catch (e) {
    error.value = e?.response?.data?.detail || t('login.loginFailed')
  } finally {
    loading.value = false
  }
}

function callbackRedirectUri(provider) {
  const origin = window.location.origin
  return `${origin}/login?oidc_provider=${encodeURIComponent(provider)}`
}

async function completeOidcLogin(provider, code, state) {
  error.value = ''
  ssoLoading.value = true
  try {
    await authStore.oidcExchange(provider, code, callbackRedirectUri(provider), state)
    const redirect = resolveRedirect()
    sessionStorage.removeItem('sw_login_redirect')
    router.replace(redirect)
  } catch (e) {
    error.value = e?.response?.data?.detail || t('login.oidcFailed')
  } finally {
    ssoLoading.value = false
  }
}

async function completeSamlLogin(provider, samlResponse) {
  error.value = ''
  ssoLoading.value = true
  try {
    await authStore.samlLogin(provider, samlResponse)
    const redirect = resolveRedirect()
    sessionStorage.removeItem('sw_login_redirect')
    router.replace(redirect)
  } catch (e) {
    error.value = e?.response?.data?.detail || t('login.samlFailed')
  } finally {
    ssoLoading.value = false
  }
}

async function startSso(provider) {
  if (!provider) return
  error.value = ''
  ssoLoading.value = true
  try {
    if (provider.kind === 'oidc') {
      const redirectUri = callbackRedirectUri(provider.provider)
      const url = await authStore.getOidcAuthorizeUrl(provider.provider, redirectUri)
      if (!url) throw new Error('Missing authorize URL')
      window.location.assign(url)
      return
    }
    if (provider.kind === 'saml') {
      const samlConfig = await authStore.fetchSamlProviderConfig(provider.provider)
      if (!samlConfig?.idp_sso_url) throw new Error('Missing SAML IdP SSO URL')
      const relayState = btoa(JSON.stringify({ provider: provider.provider }))
      const samlRequest = {
        Issuer: samlConfig.sp_entity_id,
        Destination: samlConfig.idp_sso_url,
        'urn:oasis:names:tc:SAML:2.0:protocol': {
          AssertionConsumerServiceURL: samlConfig.acs_url,
          ProtocolBinding: 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect',
          IssueInstant: new Date().toISOString(),
        },
      }
      const samlRequestStr = btoa(JSON.stringify(samlRequest))
      const samlUrl = `${samlConfig.idp_sso_url}?SAMLRequest=${encodeURIComponent(samlRequestStr)}&RelayState=${encodeURIComponent(relayState)}`
      window.location.assign(samlUrl)
      return
    }
    error.value = 'SAML provider is configured. Start from your IdP app and pass saml_response to /login query.'
  } catch (e) {
    error.value = e?.response?.data?.detail || t('login.ssoStartFailed')
  } finally {
    ssoLoading.value = false
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

/* Improve contrast for labels and input text on dark auth pages */
.ec-auth-card :deep(.q-field__label) {
  color: rgba(255,255,255,0.86) !important;
}
.ec-auth-card :deep(.q-field__control),
.ec-auth-card :deep(.q-field__native),
.ec-auth-card :deep(.q-input__control .q-field__control) {
  color: rgba(255,255,255,0.95) !important;
}
.ec-auth-card :deep(.q-icon) {
  color: rgba(255,255,255,0.85) !important;
}
.ec-auth-card .text-caption {
  color: rgba(255,255,255,0.7) !important;
}
</style>
