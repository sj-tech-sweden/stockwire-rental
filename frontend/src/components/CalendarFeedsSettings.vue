<template>
  <q-card class="ec-card q-pa-md">
    <div class="row items-center q-mb-sm">
      <div class="text-subtitle1 col">{{ t('settings.calendarFeeds.title') }}</div>
      <q-btn color="primary" icon="add" :label="t('settings.calendarFeeds.newFeed')" unelevated @click="openCreate" />
    </div>
    <div class="text-caption text-grey-7 q-mb-md">{{ t('settings.calendarFeeds.description') }}</div>

    <q-table
      :rows="feeds"
      :columns="columns"
      row-key="id"
      flat
      bordered
      :loading="loading"
      :pagination="{ rowsPerPage: 50 }"
      :rows-per-page-options="[25, 50, 100, 0]"
    >
      <template #body-cell-feed_type="props">
        <q-td :props="props">
          <q-badge :color="props.value === 'jobs' ? 'primary' : 'secondary'" :label="props.value" />
        </q-td>
      </template>
      <template #body-cell-is_active="props">
        <q-td :props="props">
          <q-icon :name="props.value ? 'check_circle' : 'cancel'" :color="props.value ? 'positive' : 'negative'" />
        </q-td>
      </template>
      <template #body-cell-actions="props">
        <q-td :props="props" auto-width>
          <q-btn flat dense round icon="content_copy" color="primary" class="q-mr-xs" @click="copyUrl(props.row)" />
          <q-btn flat dense round icon="open_in_new" color="secondary" class="q-mr-xs" @click="openFeed(props.row)" />
          <q-btn flat dense round icon="vpn_key" color="warning" class="q-mr-xs" @click="confirmRegenerateToken(props.row)" />
          <q-btn flat dense round icon="edit" color="primary" class="q-mr-xs" @click="openEdit(props.row)" />
          <q-btn flat dense round icon="delete" color="negative" @click="confirmDelete(props.row)" />
        </q-td>
      </template>
      <template #item="props">
        <div class="q-pa-xs col-12">
          <q-card flat bordered>
            <q-card-section class="q-pb-sm">
              <div class="row items-center justify-between">
                <div class="text-subtitle2">{{ props.row.name }}</div>
                <q-badge :color="props.row.feed_type === 'jobs' ? 'primary' : 'secondary'" :label="props.row.feed_type" />
              </div>
              <div class="text-caption text-grey-7">{{ props.row.token }}</div>
            </q-card-section>
            <q-card-actions align="right">
              <q-btn flat dense icon="content_copy" color="primary" @click="copyUrl(props.row)" />
              <q-btn flat dense icon="open_in_new" color="secondary" @click="openFeed(props.row)" />
              <q-btn flat dense icon="vpn_key" color="warning" @click="confirmRegenerateToken(props.row)" />
              <q-btn flat dense icon="edit" color="primary" @click="openEdit(props.row)" />
              <q-btn flat dense icon="delete" color="negative" @click="confirmDelete(props.row)" />
            </q-card-actions>
          </q-card>
        </div>
      </template>
    </q-table>

    <q-dialog v-model="dialogOpen" persistent>
      <q-card style="min-width: 400px" class="ec-card">
        <q-card-section>
          <div class="text-h6">{{ editingFeed ? t('settings.calendarFeeds.editFeed') : t('settings.calendarFeeds.newFeed') }}</div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-input v-model="form.name" :label="t('settings.calendarFeeds.feedName')" outlined dense class="q-mb-sm" :rules="[v => !!String(v || '').trim() || t('login.required')]" />
          <q-select
            v-model="form.feed_type"
            :options="feedTypeOptions"
            emit-value
            map-options
            outlined
            dense
            :label="t('settings.calendarFeeds.feedType')"
            :rules="[v => !!v || t('login.required')]"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="dialogOpen = false" />
          <q-btn color="primary" unelevated :label="t('app.actions.save')" :loading="saving" @click="saveFeed" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { api } from '../boot/axios'
import { getApiBaseUrl } from '../utils/runtime-config'

const $q = useQuasar()
const { t } = useI18n()
const apiBaseUrl = getApiBaseUrl()

const feeds = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogOpen = ref(false)
const editingFeed = ref(null)
const form = ref({ name: '', feed_type: 'jobs' })

const feedTypeOptions = [
  { label: 'Jobs', value: 'jobs' },
  { label: 'Crew', value: 'crew' },
]

const columns = [
  { name: 'name', label: t('settings.calendarFeeds.feedName'), field: 'name', sortable: true, align: 'left' },
  { name: 'feed_type', label: t('settings.calendarFeeds.feedType'), field: 'feed_type', sortable: true, align: 'left' },
  { name: 'is_active', label: t('settings.calendarFeeds.active'), field: 'is_active', sortable: true, align: 'center' },
  { name: 'token', label: t('settings.calendarFeeds.token'), field: 'token', sortable: false, align: 'left' },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
]

function feedUrl(feed) {
  return `${apiBaseUrl}/api/v1/calendar/${feed.token}/feed.ics`
}

function copyUrl(feed) {
  const url = feedUrl(feed)
  navigator.clipboard.writeText(url).then(() => {
    $q.notify({ type: 'positive', message: t('settings.calendarFeeds.urlCopied') })
  }).catch(() => {
    $q.notify({ type: 'negative', message: t('settings.calendarFeeds.copyFailed') })
  })
}

function openFeed(feed) {
  window.open(feedUrl(feed), '_blank')
}

function openCreate() {
  editingFeed.value = null
  form.value = { name: '', feed_type: 'jobs' }
  dialogOpen.value = true
}

function openEdit(feed) {
  editingFeed.value = feed
  form.value = { name: feed.name, feed_type: feed.feed_type }
  dialogOpen.value = true
}

async function saveFeed() {
  if (!form.value.name || !form.value.feed_type) return
  saving.value = true
  try {
    if (editingFeed.value) {
      await api.put(`/api/v1/calendar/feeds/${editingFeed.value.id}`, form.value)
    } else {
      await api.post('/api/v1/calendar/feeds', form.value)
    }
    dialogOpen.value = false
    await fetchFeeds()
    $q.notify({ type: 'positive', message: t('settings.calendarFeeds.saved') })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('settings.calendarFeeds.saveFailed') })
  } finally {
    saving.value = false
  }
}

function confirmDelete(feed) {
  $q.dialog({
    title: t('settings.calendarFeeds.deleteFeed'),
    message: t('settings.calendarFeeds.deleteConfirm', { name: feed.name }),
    cancel: { label: t('app.actions.cancel'), flat: true },
    ok: { label: t('app.actions.delete'), color: 'negative' },
    persistent: true,
  }).onOk(async () => {
    try {
      await api.delete(`/api/v1/calendar/feeds/${feed.id}`)
      await fetchFeeds()
      $q.notify({ type: 'positive', message: t('settings.calendarFeeds.deleted') })
    } catch (error) {
      $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('settings.calendarFeeds.deleteFailed') })
    }
  })
}

function confirmRegenerateToken(feed) {
  $q.dialog({
    title: t('settings.calendarFeeds.regenerateToken'),
    message: t('settings.calendarFeeds.regenerateConfirm'),
    cancel: { label: t('app.actions.cancel'), flat: true },
    ok: { label: t('settings.calendarFeeds.regenerate'), color: 'warning' },
    persistent: true,
  }).onOk(async () => {
    try {
      await api.post(`/api/v1/calendar/feeds/${feed.id}/regenerate-token`)
      await fetchFeeds()
      $q.notify({ type: 'positive', message: t('settings.calendarFeeds.tokenRegenerated') })
    } catch (error) {
      $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('settings.calendarFeeds.regenerateFailed') })
    }
  })
}

async function fetchFeeds() {
  loading.value = true
  try {
    const { data } = await api.get('/api/v1/calendar/feeds')
    feeds.value = data
  } catch {
    feeds.value = []
  } finally {
    loading.value = false
  }
}

onMounted(fetchFeeds)
</script>
