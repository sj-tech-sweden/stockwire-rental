<template>
  <div>
    <div class="row items-center justify-between q-mb-sm">
      <div class="text-subtitle1">{{ t('reports.templates') }}</div>
      <q-btn color="primary" icon="add" :label="t('reports.newTemplate')" unelevated @click="openDesigner()" />
    </div>

    <div class="row items-center no-wrap q-mb-sm q-pa-sm rounded-borders" :class="$q.dark.isActive ? 'bg-grey-9' : 'bg-grey-2'">
      <div class="text-body2 q-mr-sm">{{ t('reports.setLetterheadForAll') }}</div>
      <q-select
        v-model="bulkLetterheadId"
        :options="letterheadOptions"
        emit-value
        map-options
        clearable
        dense
        outlined
        :label="t('reports.letterhead')"
        style="min-width: 180px"
      />
      <q-btn
        color="primary"
        class="q-ml-sm"
        :label="t('reports.applyToAll')"
        :loading="applyingBulk"
        @click="applyLetterheadToAll"
      />
    </div>

    <q-table
      :rows="templates"
      :columns="columns"
      row-key="id"
      flat bordered dense
      :loading="loading"
      :filter="filter"
      :pagination="{ rowsPerPage: 20 }"
    >
      <template #top-right>
        <q-input v-model="filter" dense outlined :placeholder="t('app.actions.search')" clearable>
          <template #prepend><q-icon name="search" /></template>
        </q-input>
      </template>
      <template #body-cell-name="props">
        <q-td :props="props">
          <div>{{ translatedTemplateName(props.row) }}</div>
          <div v-if="props.row.name !== translatedTemplateName(props.row)" class="text-caption text-grey-6">
            {{ props.row.name }}
          </div>
        </q-td>
      </template>
      <template #body-cell-languages="props">
        <q-td :props="props">
          <q-chip
            v-for="lang in templateLanguages(props.row)"
            :key="lang"
            dense
            size="sm"
            color="accent"
            text-color="white"
          >
            {{ languageLabel(lang) }}
          </q-chip>
        </q-td>
      </template>
      <template #body-cell-category="props">
        <q-td :props="props">
          <q-badge :color="categoryColor(props.row.category)" :label="translateCategory(props.row.category)" />
        </q-td>
      </template>
      <template #body-cell-data_source_type="props">
        <q-td :props="props">
          {{ translateDataSource(props.row.data_source_type) }}
        </q-td>
      </template>
      <template #body-cell-letterhead="props">
        <q-td :props="props">
          <q-select
            :model-value="props.row.letterhead_id"
            :options="letterheadOptions"
            emit-value
            map-options
            clearable
            dense
            outlined
            style="min-width: 160px; max-width: 200px"
            @update:model-value="(val) => updateTemplateLetterhead(props.row, val ?? null)"
          >
            <template #option="{ opt, itemProps }">
              <q-item v-bind="itemProps">
                <q-item-section>
                  <q-item-label>{{ opt.label }}</q-item-label>
                  <q-item-label v-if="opt.default" caption>{{ t('reports.default') }}</q-item-label>
                </q-item-section>
              </q-item>
            </template>
          </q-select>
        </q-td>
      </template>
      <template #body-cell-is_builtin="props">
        <q-td :props="props">
          <q-icon v-if="props.row.is_builtin" name="lock" color="grey" size="xs" />
          <q-icon v-else name="edit" color="primary" size="xs" />
        </q-td>
      </template>
      <template #body-cell-actions="props">
        <q-td :props="props" auto-width>
          <q-btn flat dense round icon="content_copy" color="secondary" :title="t('reports.duplicate')" @click="duplicateTemplate(props.row)" />
          <q-btn flat dense round icon="edit" color="primary" :disable="props.row.is_builtin" @click="openDesigner(props.row)" />
          <q-btn flat dense round icon="delete" color="negative" :disable="props.row.is_builtin" @click="confirmDelete(props.row)" />
        </q-td>
      </template>
      <template #no-data>
        <div class="full-width row flex-center text-grey-7 q-pa-md">
          <q-icon name="summarize" size="2em" class="q-mr-sm" />
          {{ filter ? t('reports.noResults') : t('reports.noTemplates') }}
        </div>
      </template>
    </q-table>

    <!-- Designer Dialog -->
    <q-dialog v-model="showDesigner" persistent :maximized="$q.screen.lt.md">
      <q-card style="min-width: 800px; max-width: 95vw" class="ec-card">
        <ReportDesigner :template="editingTemplate" @close="showDesigner = false" @saved="onDesignerSaved" />
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useReportsStore } from '../stores/reports'
import { SUPPORTED_LOCALES } from '../i18n'
import ReportDesigner from './ReportDesigner.vue'

const $q = useQuasar()
const { t, locale } = useI18n()
const reportsStore = useReportsStore()

const loading = ref(false)
const templates = ref([])
const filter = ref('')
const showDesigner = ref(false)
const editingTemplate = ref(null)
const bulkLetterheadId = ref(null)
const applyingBulk = ref(false)

const letterheadOptions = computed(() => {
  const opts = [{ label: t('reports.noLetterhead'), value: null, default: false }]
  for (const lh of (reportsStore.letterheads || [])) {
    opts.push({ label: lh.name, value: lh.id, default: !!lh.is_default })
  }
  return opts
})

async function updateTemplateLetterhead(row, value) {
  try {
    const updated = await reportsStore.updateTemplate(row.id, { letterhead_id: value })
    // Reflect the new value locally so the select stays in sync.
    row.letterhead_id = updated.letterhead_id ?? null
    $q.notify({ type: 'positive', message: t('reports.letterheadUpdated') })
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('reports.letterheadUpdateFailed') })
    await loadTemplates()
  }
}

const columns = [
  { name: 'name', label: t('reports.templateName'), field: 'name', align: 'left', sortable: true },
  { name: 'languages', label: t('reports.languages'), field: 'languages', align: 'left' },
  { name: 'category', label: t('reports.category'), field: 'category', align: 'left', sortable: true },
  { name: 'data_source_type', label: t('reports.dataSource'), field: 'data_source_type', align: 'left' },
  { name: 'letterhead', label: t('reports.letterhead'), field: 'letterhead_id', align: 'left' },
  { name: 'is_builtin', label: '', field: 'is_builtin', align: 'center' },
  { name: 'actions', label: '', field: 'actions', align: 'center' },
]

function categoryColor(cat) {
  const map = { warehouse: 'blue', asset: 'orange', logistics: 'green', custom: 'grey' }
  return map[cat] || 'grey'
}

function translateCategory(cat) {
  return t('reports.categories.' + cat) || cat
}

function translateDataSource(ds) {
  return t('reports.dataSources.' + ds) || ds
}

function parseTranslations(row) {
  if (!row.translations_json) return {}
  try {
    const parsed = JSON.parse(row.translations_json)
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}

function translatedTemplateName(row) {
  const currentLang = String(locale.value || 'en').split(/[-_]/)[0]
  if (currentLang === 'en') return row.name
  const translations = parseTranslations(row)
  const translated = translations[currentLang]?.name
  return translated || row.name
}

function templateLanguages(row) {
  const translations = parseTranslations(row)
  const langs = new Set(['en'])
  Object.keys(translations).forEach(lang => langs.add(lang))
  return Array.from(langs)
    .filter(lang => SUPPORTED_LOCALES.includes(lang))
    .sort()
}

function languageLabel(lang) {
  return t('app.language.' + lang) || lang.toUpperCase()
}

async function loadTemplates() {
  loading.value = true
  try {
    templates.value = await reportsStore.fetchTemplates()
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('reports.failedLoad') })
  } finally {
    loading.value = false
  }
}

function openDesigner(template = null) {
  if (template) {
    // Fetch full template data (list endpoint doesn't include body_json)
    reportsStore.getTemplate(template.id).then(full => {
      editingTemplate.value = full
      showDesigner.value = true
    }).catch(() => {
      editingTemplate.value = template
      showDesigner.value = true
    })
  } else {
    editingTemplate.value = null
    showDesigner.value = true
  }
}

function onDesignerSaved() {
  showDesigner.value = false
  loadTemplates()
}

async function duplicateTemplate(template) {
  try {
    const newTemplate = await reportsStore.duplicateTemplate(template.id)
    $q.notify({ type: 'positive', message: t('reports.templateDuplicated') })
    openDesigner(newTemplate)
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('reports.failedDuplicate') })
  }
}

function confirmDelete(template) {
  $q.dialog({
    title: t('reports.deleteTemplate'),
    message: t('reports.deleteTemplateConfirm', { name: template.name }),
    cancel: t('app.actions.cancel'),
    ok: t('app.actions.delete'),
    persistent: true,
  }).onOk(async () => {
    try {
      await reportsStore.deleteTemplate(template.id)
      $q.notify({ type: 'positive', message: t('reports.templateDeleted') })
      await loadTemplates()
    } catch (err) {
      $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('reports.failedDelete') })
    }
  })
}

async function applyLetterheadToAll() {
  const value = bulkLetterheadId.value
  const label = letterheadOptions.value.find(o => o.value === value)?.label || t('reports.noLetterhead')
  $q.dialog({
    title: t('reports.applyToAll'),
    message: t('reports.letterheadApplyConfirm', { name: label, count: templates.value.length }),
    cancel: t('app.actions.cancel'),
    ok: t('app.actions.apply'),
    persistent: true,
  }).onOk(async () => {
    applyingBulk.value = true
    let okCount = 0
    let failCount = 0
    try {
      await Promise.all(templates.value.map(t =>
        reportsStore.updateTemplate(t.id, { letterhead_id: value })
          .then(() => { okCount += 1 })
          .catch(() => { failCount += 1 }),
      ))
      if (failCount === 0) {
        $q.notify({ type: 'positive', message: t('reports.letterheadAppliedToAll', { count: okCount }) })
      } else {
        $q.notify({ type: 'warning', message: t('reports.letterheadAppliedPartial', { ok: okCount, fail: failCount }) })
      }
      await loadTemplates()
    } catch {
      $q.notify({ type: 'negative', message: t('reports.letterheadUpdateFailed') })
    } finally {
      applyingBulk.value = false
    }
  })
}

onMounted(() => {
  loadTemplates()
  reportsStore.fetchLetterheads().catch(() => {})
})
</script>
