<template>
  <div>
    <!-- Quick Actions -->
    <q-card class="ec-card q-mb-md">
      <q-card-section class="row items-center">
        <div>
          <div class="text-subtitle1 text-weight-medium">
            {{ t('settings.notifications.quickActions') }}
          </div>
          <div class="text-caption text-grey-7">
            {{ t('settings.notifications.quickActionsHint') }}
          </div>
        </div>
        <q-space />
        <q-btn
          color="primary"
          icon="send"
          :label="t('settings.notifications.sendTest')"
          :loading="sendingTest"
          @click="sendTestNotification"
        />
      </q-card-section>
    </q-card>

    <!-- Preferences Section -->
    <q-card class="ec-card q-mb-md">
      <q-card-section>
        <div class="text-subtitle1 text-weight-medium q-mb-md">
          {{ t('settings.notifications.preferences') }}
        </div>
        <div class="text-caption text-grey-7 q-mb-md">
          {{ t('settings.notifications.preferencesHint') }}
        </div>
        <q-table
          :rows="preferences"
          :columns="prefColumns"
          row-key="id"
          flat
          dense
          :loading="loadingPrefs"
          hide-bottom
        >
          <template #body-cell-email="props">
            <q-td :props="props">
              <q-toggle
                :model-value="props.row.email_enabled"
                @update:model-value="togglePref(props.row, 'email_enabled', $event)"
                color="primary"
                dense
              />
            </q-td>
          </template>
          <template #body-cell-web_push="props">
            <q-td :props="props">
              <q-toggle
                :model-value="props.row.web_push_enabled"
                @update:model-value="togglePref(props.row, 'web_push_enabled', $event)"
                color="primary"
                dense
              />
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <!-- Templates Section -->
    <q-card class="ec-card">
      <q-card-section>
        <div class="row items-center q-mb-md">
          <div class="text-subtitle1 text-weight-medium">
            {{ t('settings.notifications.templates') }}
          </div>
          <q-space />
          <q-btn
            flat
            dense
            color="secondary"
            icon="download"
            :label="t('settings.notifications.loadDefaults')"
            :loading="seedingDefaults"
            @click="seedDefaults"
            class="q-mr-sm"
          />
          <q-btn
            flat
            dense
            color="primary"
            icon="add"
            :label="t('settings.notifications.addTemplate')"
            @click="openCreateTemplate"
          />
        </div>
        <div class="text-caption text-grey-7 q-mb-md">
          {{ t('settings.notifications.templatesHint') }}
        </div>

        <!-- Filter by key -->
        <div class="row q-gutter-sm q-mb-md">
          <q-select
            v-model="filterKey"
            :options="templateKeyOptions"
            :label="t('settings.notifications.filterByKey')"
            emit-value
            map-options
            clearable
            dense
            outlined
            style="min-width: 200px"
          />
          <q-select
            v-model="filterRecipient"
            :options="recipientOptions"
            :label="t('settings.notifications.filterByRecipient')"
            emit-value
            map-options
            clearable
            dense
            outlined
            style="min-width: 150px"
          />
        </div>

        <q-table
          :rows="filteredTemplates"
          :columns="tplColumns"
          row-key="id"
          flat
          dense
          :loading="loadingTemplates"
          hide-bottom
        >
          <template #body-cell-template_key="props">
            <q-td :props="props">
              {{ translateKey(props.row.template_key) }}
            </q-td>
          </template>
          <template #body-cell-recipient="props">
            <q-td :props="props">
              <q-badge :color="recipientColor(props.row.recipient_type)" :label="recipientLabel(props.row.recipient_type)" />
            </q-td>
          </template>
          <template #body-cell-locale="props">
            <q-td :props="props">
              <q-badge :color="props.row.locale === 'en' ? 'blue' : 'orange'">
                {{ localeLabel(props.row.locale) }}
              </q-badge>
            </q-td>
          </template>
          <template #body-cell-is_enabled="props">
            <q-td :props="props">
              <q-toggle
                :model-value="props.row.is_enabled"
                @update:model-value="toggleTemplateEnabled(props.row, $event)"
                color="positive"
                dense
              />
            </q-td>
          </template>
          <template #body-cell-actions="props">
            <q-td :props="props">
              <q-btn flat dense icon="send" size="sm" color="primary" :aria-label="t('settings.notifications.sendTest')" @click="sendTestForTemplate(props.row.id)" :loading="testingTemplateId === props.row.id" />
              <q-btn flat dense icon="edit" size="sm" :aria-label="t('app.actions.edit')" @click="editTemplate(props.row)" />
              <q-btn flat dense icon="delete" size="sm" color="negative" :aria-label="t('app.actions.delete')" @click="confirmDeleteTemplate(props.row)" />
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <!-- Create/Edit Template Dialog -->
    <q-dialog v-model="templateDialogOpen" persistent>
      <q-card style="min-width: 700px; max-width: 90vw">
        <q-card-section>
          <div class="text-h6">
            {{ editingTemplate ? t('settings.notifications.editTemplate') : t('settings.notifications.createTemplate') }}
          </div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <div class="row q-gutter-md">
            <q-select
              v-model="templateForm.template_key"
              :options="templateKeyOptions"
              :label="t('settings.notifications.templateKey')"
              emit-value
              map-options
              outlined
              dense
              class="col-6"
              :disable="!!editingTemplate"
            />
            <q-select
              v-model="templateForm.locale"
              :options="localeOptions"
              :label="t('settings.notifications.locale')"
              emit-value
              map-options
              outlined
              dense
              class="col-3"
              :disable="!!editingTemplate"
            />
            <q-select
              v-model="templateForm.recipient_type"
              :options="recipientOptions"
              :label="t('settings.notifications.recipient')"
              emit-value
              map-options
              outlined
              dense
              class="col-3"
            />
          </div>

          <div class="q-mt-sm q-mb-md">
            <q-badge :color="recipientColor(templateForm.recipient_type)" :label="recipientLabel(templateForm.recipient_type)" />
            <span class="text-caption text-grey-7 q-ml-sm">
              {{ recipientHint(templateForm.recipient_type) }}
            </span>
          </div>

          <q-input
            v-model="templateForm.subject_template"
            :label="t('settings.notifications.subjectTemplate')"
            outlined
            dense
            class="q-mt-md"
          />

          <q-input
            v-model="templateForm.text_template"
            :label="t('settings.notifications.textTemplate')"
            outlined
            dense
            type="textarea"
            rows="4"
            class="q-mt-md"
          />

          <q-input
            v-model="templateForm.html_template"
            :label="t('settings.notifications.htmlTemplate')"
            outlined
            dense
            type="textarea"
            rows="8"
            class="q-mt-md"
          />

          <div class="text-caption text-grey-7 q-mt-sm">
            {{ t('settings.notifications.templateHelp') }}
          </div>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" v-close-popup />
          <q-btn
            color="primary"
            :label="t('app.actions.save')"
            :loading="savingTemplate"
            @click="saveTemplate"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQuasar } from 'quasar'
import { api } from '../boot/axios'

const { t } = useI18n()
const $q = useQuasar()

const loadingPrefs = ref(false)
const loadingTemplates = ref(false)
const savingTemplate = ref(false)
const seedingDefaults = ref(false)
const sendingTest = ref(false)
const testingTemplateId = ref(null)
const preferences = ref([])
const templates = ref([])
const filterKey = ref(null)
const filterRecipient = ref(null)
const templateDialogOpen = ref(false)
const editingTemplate = ref(null)

const templateForm = ref({
  template_key: '',
  locale: 'en',
  recipient_type: 'both',
  subject_template: '',
  text_template: '',
  html_template: '',
  is_enabled: true,
})

const templateKeyOptions = [
  { label: t('settings.notifications.eventJobCreated'), value: 'job.created' },
  { label: t('settings.notifications.eventJobUpdated'), value: 'job.updated' },
  { label: t('settings.notifications.eventJobCompleted'), value: 'job.completed' },
  { label: t('settings.notifications.eventMaintenanceScheduled'), value: 'maintenance.scheduled' },
  { label: t('settings.notifications.eventDefectReported'), value: 'defect.reported' },
  { label: t('settings.notifications.eventCrewAssigned'), value: 'crew.assigned' },
  { label: t('settings.notifications.eventInvoiceSent'), value: 'invoice.sent' },
]

const localeOptions = [
  { label: 'English', value: 'en' },
  { label: 'Svenska', value: 'sv' },
]

const recipientOptions = [
  { label: t('settings.notifications.recipientCustomer'), value: 'customer' },
  { label: t('settings.notifications.recipientStaff'), value: 'staff' },
  { label: t('settings.notifications.recipientBoth'), value: 'both' },
]

const prefColumns = [
  { name: 'label', label: t('settings.notifications.eventType'), field: 'label', align: 'left' },
  { name: 'description', label: t('settings.notifications.description'), field: 'description', align: 'left' },
  { name: 'email', label: t('settings.notifications.email'), field: 'email_enabled', align: 'center' },
  { name: 'web_push', label: t('settings.notifications.webPush'), field: 'web_push_enabled', align: 'center' },
]

const tplColumns = [
  { name: 'template_key', label: t('settings.notifications.eventType'), field: 'template_key', align: 'left' },
  { name: 'recipient', label: t('settings.notifications.recipient'), field: 'recipient_type', align: 'center' },
  { name: 'locale', label: t('settings.notifications.locale'), field: 'locale', align: 'center' },
  { name: 'subject_template', label: t('settings.notifications.subject'), field: 'subject_template', align: 'left' },
  { name: 'is_enabled', label: t('settings.notifications.enabled'), field: 'is_enabled', align: 'center' },
  { name: 'actions', label: '', field: 'actions', align: 'center' },
]

const filteredTemplates = computed(() => {
  let result = templates.value
  if (filterKey.value) {
    result = result.filter(tpl => tpl.template_key === filterKey.value)
  }
  if (filterRecipient.value) {
    result = result.filter(tpl => tpl.recipient_type === filterRecipient.value)
  }
  return result
})

function recipientLabel(recipientType) {
  if (recipientType === 'customer') return t('settings.notifications.recipientCustomer')
  if (recipientType === 'staff') return t('settings.notifications.recipientStaff')
  return t('settings.notifications.recipientBoth')
}

function recipientColor(recipientType) {
  if (recipientType === 'customer') return 'blue'
  if (recipientType === 'staff') return 'green'
  return 'purple'
}

function recipientHint(recipientType) {
  if (recipientType === 'customer') return t('settings.notifications.recipientHintCustomer')
  if (recipientType === 'staff') return t('settings.notifications.recipientHintStaff')
  return t('settings.notifications.recipientHintBoth')
}

function translateKey(key) {
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

function localeLabel(locale) {
  const map = { en: 'EN', sv: 'SV' }
  return map[locale] || locale.toUpperCase()
}

async function loadPreferences() {
  loadingPrefs.value = true
  try {
    const { data } = await api.get('/api/v1/notifications/preferences')
    preferences.value = data
  } catch (error) {
    console.error('Failed to load preferences:', error)
  } finally {
    loadingPrefs.value = false
  }
}

async function loadTemplates() {
  loadingTemplates.value = true
  try {
    const { data } = await api.get('/api/v1/notifications/templates')
    templates.value = data
  } catch (error) {
    console.error('Failed to load templates:', error)
  } finally {
    loadingTemplates.value = false
  }
}

async function seedDefaults() {
  $q.dialog({
    title: t('settings.notifications.loadDefaultsTitle'),
    message: t('settings.notifications.loadDefaultsMessage'),
    cancel: { label: t('app.actions.cancel'), flat: true },
    ok: { label: t('settings.notifications.loadDefaults'), color: 'primary' },
    persistent: true,
  }).onOk(async () => {
    seedingDefaults.value = true
    try {
      const { data } = await api.post('/api/v1/notifications/seed-defaults')
      $q.notify({
        type: 'positive',
        message: `Loaded ${data.templates_added} templates and ${data.preferences_added} preferences`,
      })
      await Promise.all([loadPreferences(), loadTemplates()])
    } catch (error) {
      $q.notify({ type: 'negative', message: error?.response?.data?.detail || 'Failed to load defaults' })
    } finally {
      seedingDefaults.value = false
    }
  })
}

async function sendTestNotification() {
  sendingTest.value = true
  try {
    await api.post('/api/v1/notifications/test')
    $q.notify({
      type: 'positive',
      message: 'Test notification sent! Check your email and browser notifications.',
    })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || 'Failed to send test notification' })
  } finally {
    sendingTest.value = false
  }
}

async function sendTestForTemplate(templateId) {
  testingTemplateId.value = templateId
  try {
    await api.post(`/api/v1/notifications/test?template_id=${templateId}`)
    $q.notify({
      type: 'positive',
      message: 'Test notification sent! Check your email and browser notifications.',
    })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || 'Failed to send test notification' })
  } finally {
    testingTemplateId.value = null
  }
}

async function togglePref(pref, field, value) {
  try {
    await api.put(`/api/v1/notifications/preferences/${pref.id}`, { [field]: value })
    pref[field] = value
  } catch (error) {
    console.error('Failed to update preference:', error)
  }
}

async function toggleTemplateEnabled(tpl, value) {
  try {
    await api.put(`/api/v1/notifications/templates/${tpl.id}`, { is_enabled: value })
    tpl.is_enabled = value
  } catch (error) {
    console.error('Failed to update template:', error)
  }
}

function openCreateTemplate() {
  editingTemplate.value = null
  templateForm.value = {
    template_key: '',
    locale: 'en',
    recipient_type: 'both',
    subject_template: '',
    text_template: '',
    html_template: '',
    is_enabled: true,
  }
  templateDialogOpen.value = true
}

function editTemplate(tpl) {
  editingTemplate.value = tpl
  templateForm.value = {
    template_key: tpl.template_key,
    locale: tpl.locale,
    recipient_type: tpl.recipient_type || 'both',
    subject_template: tpl.subject_template || '',
    text_template: tpl.text_template || '',
    html_template: tpl.html_template || '',
    is_enabled: tpl.is_enabled,
  }
  templateDialogOpen.value = true
}

async function saveTemplate() {
  savingTemplate.value = true
  try {
    if (editingTemplate.value) {
      await api.put(`/api/v1/notifications/templates/${editingTemplate.value.id}`, {
        recipient_type: templateForm.value.recipient_type,
        subject_template: templateForm.value.subject_template || null,
        text_template: templateForm.value.text_template || null,
        html_template: templateForm.value.html_template || null,
        is_enabled: templateForm.value.is_enabled,
      })
    } else {
      await api.post('/api/v1/notifications/templates', templateForm.value)
    }
    await loadTemplates()
    templateDialogOpen.value = false
    $q.notify({ type: 'positive', message: t('settings.notifications.templateSaved') })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || 'Failed to save template' })
  } finally {
    savingTemplate.value = false
  }
}

function confirmDeleteTemplate(tpl) {
  $q.dialog({
    title: t('settings.notifications.deleteTemplate'),
    message: t('settings.notifications.deleteTemplateConfirm'),
    cancel: { label: t('app.actions.cancel'), flat: true },
    ok: { label: t('app.actions.delete'), color: 'negative' },
    persistent: true,
  }).onOk(async () => {
    try {
      await api.delete(`/api/v1/notifications/templates/${tpl.id}`)
      await loadTemplates()
      $q.notify({ type: 'positive', message: t('settings.notifications.templateDeleted') })
    } catch (error) {
      $q.notify({ type: 'negative', message: 'Failed to delete template' })
    }
  })
}

onMounted(() => {
  loadPreferences()
  loadTemplates()
})
</script>
