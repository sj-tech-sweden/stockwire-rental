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
          <div class="col-12 col-md-6">
            <q-select
              v-model="form.notification_channel"
              :options="notificationChannelOptions"
              emit-value
              map-options
              dense
              outlined
              :label="t('profile.notificationChannel')"
              :disable="saving"
            />
          </div>
        </div>

        <div class="q-mt-md">
          <div class="text-subtitle2 q-mb-sm">{{ t('profile.webNotifications') }}</div>
          <div class="text-caption text-grey-7 q-mb-sm">{{ t('profile.webNotificationsDescription') }}</div>
          <div class="row items-center q-gutter-sm">
            <q-btn
              color="secondary"
              icon="notifications"
              :label="t('profile.enableWebNotifications')"
              :disable="saving || !canUseWebPush"
              @click="enableWebNotifications"
            />
            <span class="text-caption text-grey-7">{{ webPushStatus }}</span>
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

      <template v-if="crewCalendarUrl">
        <q-separator class="q-my-md" />
        <div class="text-subtitle1 q-mb-sm">{{ t('profile.crewCalendar') }}</div>
        <div class="text-caption text-grey-7 q-mb-sm">{{ t('profile.crewCalendarDescription') }}</div>
        <div class="row items-center q-gutter-sm">
          <q-input
            :model-value="crewCalendarUrl"
            outlined
            dense
            readonly
            class="col"
          />
          <q-btn flat dense icon="content_copy" color="primary" @click="copyCrewCalendarUrl" />
          <q-btn flat dense icon="open_in_new" color="secondary" @click="openCrewCalendarUrl" />
        </div>
      </template>
    </q-card>

    <!-- My Skills & Certifications (crew self-service) -->
    <q-card v-if="hasCrewProfile" class="ec-card q-pa-md q-mt-md" style="max-width: 720px; margin: 0 auto;">
      <MySkills class="q-mb-md" />
      <q-separator class="q-my-md" />
      <MyCertifications />
    </q-card>

    <!-- Per-user notification preferences (start from company defaults) -->
    <q-card class="ec-card q-pa-md q-mt-md" style="max-width: 720px; margin: 0 auto;">
      <div class="text-subtitle1 q-mb-sm">{{ t('profile.myNotificationPreferences') }}</div>
      <div class="text-caption text-grey-7 q-mb-md">{{ t('profile.myNotificationPreferencesHint') }}</div>
      <q-table
        :rows="myPrefs"
        :columns="myPrefColumns"
        row-key="event_type"
        flat
        dense
        :loading="loadingMyPrefs"
        hide-bottom
      >
        <template #body-cell-event_type="props">
          <q-td :props="props">{{ translateEventType(props.row.event_type) }}</q-td>
        </template>
        <template #body-cell-email_enabled="props">
          <q-td :props="props">
            <q-toggle
              :model-value="props.row.email_enabled"
              @update:model-value="toggleMyPref(props.row, 'email_enabled', $event)"
              color="primary"
              dense
            />
          </q-td>
        </template>
        <template #body-cell-web_push_enabled="props">
          <q-td :props="props">
            <q-toggle
              :model-value="props.row.web_push_enabled"
              @update:model-value="toggleMyPref(props.row, 'web_push_enabled', $event)"
              color="primary"
              dense
            />
          </q-td>
        </template>
        <template #body-cell-source="props">
          <q-td :props="props">
            <q-badge
              :color="props.row.is_override ? 'warning' : 'grey'"
              :label="props.row.is_override ? t('profile.myPrefOverridden') : t('profile.myPrefGlobalDefault')"
            />
            <q-btn
              v-if="props.row.is_override"
              flat
              dense
              size="sm"
              icon="restart_alt"
              :label="t('profile.myPrefReset')"
              class="q-ml-sm"
              @click="resetMyPref(props.row)"
            />
          </q-td>
        </template>
      </q-table>
    </q-card>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'

import { useAuthStore } from '../stores/auth'
import { api } from '../boot/axios'
import { getApiBaseUrl } from '../utils/runtime-config'
import { resolveAppLocale, setLocale, setUserLocalePreference } from '../i18n'
import MySkills from '../components/MySkills.vue'
import MyCertifications from '../components/MyCertifications.vue'

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
  notification_channel: 'both',
})
const localeOptions = computed(() => [
  { label: t('app.language.english'), value: 'en' },
  { label: t('app.language.swedish'), value: 'sv' },
])
const notificationChannelOptions = computed(() => [
  { label: t('profile.notificationChannels.both'), value: 'both' },
  { label: t('profile.notificationChannels.email'), value: 'email' },
  { label: t('profile.notificationChannels.webPush'), value: 'web_push' },
  { label: t('profile.notificationChannels.none'), value: 'none' },
])

const crewCalendarUrl = ref('')
const webPushStatus = ref('')
const canUseWebPush = typeof window !== 'undefined' && 'Notification' in window && 'serviceWorker' in navigator

// Per-user notification preferences (start from company defaults)
const loadingMyPrefs = ref(false)
const myPrefs = ref([])
const myPrefColumns = [
  { name: 'event_type', label: t('profile.myPrefEvent'), field: 'event_type', align: 'left' },
  { name: 'email_enabled', label: t('profile.myPrefEmail'), field: 'email_enabled', align: 'center' },
  { name: 'web_push_enabled', label: t('profile.myPrefWebPush'), field: 'web_push_enabled', align: 'center' },
  { name: 'source', label: t('profile.myPrefStatus'), field: 'is_override', align: 'left' },
]

function translateEventType(key) {
  const map = {
    'job.created': t('settings.notifications.eventJobCreated'),
    'job.updated': t('settings.notifications.eventJobUpdated'),
    'job.completed': t('settings.notifications.eventJobCompleted'),
    'maintenance.scheduled': t('settings.notifications.eventMaintenanceScheduled'),
    'defect.reported': t('settings.notifications.eventDefectReported'),
    'crew.assigned': t('settings.notifications.eventCrewAssigned'),
    'invoice.sent': t('settings.notifications.eventInvoiceSent'),
  }
  return map[key] || key
}

async function loadMyPrefs() {
  loadingMyPrefs.value = true
  try {
    const { data } = await api.get('/api/v1/notifications/my-preferences')
    myPrefs.value = data
  } catch (error) {
    console.error('Failed to load notification preferences:', error)
  } finally {
    loadingMyPrefs.value = false
  }
}

async function toggleMyPref(row, field, value) {
  row[field] = value
  row.is_override = true
  try {
    await api.put(`/api/v1/notifications/my-preferences/${row.event_type}`, {
      email_enabled: row.email_enabled,
      web_push_enabled: row.web_push_enabled,
    })
    $q.notify({ type: 'positive', message: t('profile.myPrefUpdated') })
  } catch (error) {
    await loadMyPrefs()
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('profile.myPrefUpdateFailed') })
  }
}

async function resetMyPref(row) {
  try {
    await api.delete(`/api/v1/notifications/my-preferences/${row.event_type}`)
    await loadMyPrefs()
    $q.notify({ type: 'positive', message: t('profile.myPrefUpdated') })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('profile.myPrefUpdateFailed') })
  }
}

function copyCrewCalendarUrl() {
  if (!crewCalendarUrl.value) return
  navigator.clipboard.writeText(crewCalendarUrl.value).then(() => {
    $q.notify({ type: 'positive', message: t('crew.calendarFeedCopied') })
  }).catch(() => {
    $q.notify({ type: 'negative', message: t('crew.calendarFeedCopyFailed') })
  })
}

function openCrewCalendarUrl() {
  if (crewCalendarUrl.value) window.open(crewCalendarUrl.value, '_blank')
}

async function fetchCrewCalendarUrl() {
  try {
    const { data: feed } = await api.get('/api/v1/calendar/my-feed')
    if (feed && feed.token) {
      crewCalendarUrl.value = `${getApiBaseUrl()}/api/v1/calendar/${feed.token}/feed.ics`
    }
  } catch (err) {
    if (err?.response?.status !== 404) {
      $q.notify({ type: 'warning', message: t('crew.calendarFeedCopyFailed') })
    }
  }
}

const authSource = computed(() => String(authStore.me?.auth_source || 'local').toLowerCase())
const isSsoManaged = computed(() => ['oidc', 'saml'].includes(authSource.value))
const hasCrewProfile = computed(() => !!authStore.me?.id)
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
    notification_channel: String(authStore.me?.notification_channel || 'both'),
  }
}

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = window.atob(base64)
  return Uint8Array.from([...rawData].map(char => char.charCodeAt(0)))
}

async function enableWebNotifications() {
  if (!canUseWebPush) {
    webPushStatus.value = t('profile.webNotificationsUnavailable')
    return
  }
  const permission = await Notification.requestPermission()
  if (permission !== 'granted') {
    webPushStatus.value = t('profile.webNotificationsDenied')
    return
  }
  const [{ data: vapid }, registration] = await Promise.all([
    api.get('/api/v1/notifications/vapid-public-key'),
    navigator.serviceWorker.ready,
  ])
  if (!vapid?.public_key) {
    webPushStatus.value = t('profile.webNotificationsUnavailable')
    return
  }
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(vapid.public_key),
  })
  await api.post('/api/v1/notifications/subscriptions', {
    endpoint: subscription.endpoint,
    keys: subscription.toJSON().keys,
    user_agent: navigator.userAgent,
  })
  webPushStatus.value = t('profile.webNotificationsEnabled')
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
      notification_channel: form.value.notification_channel,
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
  const userId = authStore.me?.id || null
  const preferred = userId
    ? resolveAppLocale(userId)
    : localStorage.getItem('sw_locale') || resolveAppLocale(null)
  userLocale.value = setLocale(preferred)
  fetchCrewCalendarUrl()
  loadMyPrefs()
  webPushStatus.value = canUseWebPush
    ? (Notification.permission === 'granted'
        ? t('profile.webNotificationsEnabled')
        : t('profile.webNotificationsPrompt'))
    : t('profile.webNotificationsUnavailable')
})
</script>
