<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="emit('update:modelValue', $event)">
    <q-card style="min-width: 420px; max-width: 95vw; max-height: 90vh; display: flex; flex-direction: column;" class="ec-card">
      <q-card-section>
        <div class="text-h6">{{ t('reports.exportReport') }}</div>
        <div class="text-caption text-grey-7">{{ t('reports.exportDescription', { type: entityType, id: entityId }) }}</div>
      </q-card-section>

      <q-card-section class="q-pt-none" style="overflow-y: auto; flex: 1 1 auto;">
        <q-select
          v-model="selectedTemplateId"
          :options="templateOptions"
          :label="t('reports.selectTemplate')"
          outlined dense emit-value map-options
          class="q-mb-sm"
        >
          <template #no-option>
            <q-item>
              <q-item-section class="text-grey">{{ t('reports.noTemplates') }}</q-item-section>
            </q-item>
          </template>
        </q-select>
        <q-select
          v-model="outputFormat"
          :options="formatOptions"
          :label="t('reports.outputFormat')"
          outlined dense emit-value map-options
          class="q-mb-sm"
        />
        <q-select
          v-model="selectedLanguage"
          :options="templateLanguageOptions"
          :label="t('app.language.label')"
          outlined dense emit-value map-options
          class="q-mb-sm"
        />

        <!-- Preview Section -->
        <div v-if="previewData" class="preview-section q-pa-sm q-mb-sm">
          <div class="text-caption text-grey-7 q-mb-xs">{{ t('reports.preview') }}</div>
          <div class="preview-box">
            <div v-for="(block, idx) in (previewData.body_json?.flowables || [])" :key="idx" class="q-py-xs">
              <div v-if="block.type === 'heading'" :class="'text-h' + (block.level || 1)">{{ resolveText(block.text) }}</div>
              <div v-else-if="block.type === 'paragraph'" class="text-body2">{{ resolveText(block.text) }}</div>
              <q-separator v-else-if="block.type === 'line'" class="q-my-xs" />
              <div v-else-if="block.type === 'spacer'" :style="{ height: (block.height_mm || 5) + 'mm' }"></div>
            </div>
          </div>
        </div>

        <!-- Generation Result -->
        <div v-if="generated" class="bg-positive text-white q-pa-sm rounded-borders q-mb-sm">
          <div class="row items-center justify-between">
            <div>
              <q-icon name="check_circle" class="q-mr-sm" />
              {{ t('reports.generatedSuccessfully') }}
            </div>
            <q-btn flat dense color="white" icon="download" :label="t('reports.download')" @click="downloadReport" />
          </div>
        </div>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="emit('update:modelValue', false)" />
        <q-btn
          v-if="!generated"
          color="primary" unelevated
          :label="t('reports.generate')"
          :loading="generating"
          :disable="!selectedTemplateId"
          @click="doGenerate"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useReportsStore } from '../stores/reports'
import { SUPPORTED_LOCALES } from '../i18n'
import { api } from '../boot/axios'

const props = defineProps({
  modelValue: Boolean,
  entityType: { type: String, required: true },
  entityId: { type: [Number, String], required: true },
})

const emit = defineEmits(['update:modelValue', 'generated'])

const $q = useQuasar()
const { t, locale } = useI18n()
const reportsStore = useReportsStore()

const templates = ref([])
const selectedTemplateId = ref(null)
const selectedLanguage = ref('en')
const outputFormat = ref('pdf')
const generating = ref(false)
const generated = ref(null)
const previewData = ref(null)

const templateOptions = computed(() => {
  if (!templates.value.length) return []
  // Only show templates that are compatible with this entity type:
  // exact match or generic inventory templates.
  const compatible = templates.value.filter(tmpl =>
    tmpl.data_source_type === props.entityType || tmpl.data_source_type === 'inventory'
  )
  return compatible.map(tmpl => {
    const catLabel = t('reports.categories.' + tmpl.category) || tmpl.category
    const nameLabel = translateTemplateName(tmpl.name)
    const sourceLabel = t('reports.dataSources.' + tmpl.data_source_type) || tmpl.data_source_type
    return {
      label: nameLabel + ' (' + catLabel + ' · ' + sourceLabel + ')',
      value: tmpl.id,
    }
  })
})

const formatOptions = computed(() => [
  { label: t('reports.pdf'), value: 'pdf' },
  { label: t('reports.html'), value: 'html' },
])

const selectedTemplate = computed(() => {
  return templates.value.find(tmpl => tmpl.id === selectedTemplateId.value) || null
})

const templateLanguageOptions = computed(() => {
  const tmpl = selectedTemplate.value
  const langs = new Set(['en'])
  if (tmpl?.translations_json) {
    try {
      const parsed = JSON.parse(tmpl.translations_json)
      if (parsed && typeof parsed === 'object') {
        Object.keys(parsed).forEach(lang => langs.add(lang))
      }
    } catch { /* ignore */ }
  }
  return Array.from(langs)
    .filter(lang => SUPPORTED_LOCALES.includes(lang))
    .sort()
    .map(lang => ({
      label: t('app.language.' + lang) || lang.toUpperCase(),
      value: lang,
    }))
})

const TEMPLATE_NAME_MAP = {
  'Case Lid / Insert Manifest': 'caseLid',
  'Case Contents Summary (No Serials)': 'caseContents',
  'Kit Component Breakdown': 'kitBreakdown',
  'Zone-Based Pick List': 'pickList',
  'Return Check-In & Missing Items Audit': 'returnAudit',
  'Vehicle Load & Weight Summary': 'vehicleLoad',
  'Asset Utilization & Idle Stock': 'assetUtilization',
  'Overdue & Unreturned Items': 'overdueItems',
  'Damage & Maintenance Log': 'damageLog',
  'On-Site Handover & Delivery Sign-Off': 'deliveryHandover',
  'Venue Compliance & Safety Packet': 'venueCompliance',
  'Job Summary Card': 'jobSummaryCard',
}

function translateTemplateName(name) {
  const key = TEMPLATE_NAME_MAP[name]
  if (key) return t(`reports.templateNames.${key}`)
  return name
}

function resolveText(text) {
  if (!text) return ''
  return text.replace(/\{\{\s*now\s*\}\}/g, new Date().toLocaleDateString())
    .replace(/\{\{\s*\w+\.\w+\s*\}\}/g, '[data]')
}

async function loadTemplates() {
  try {
    const all = await reportsStore.fetchTemplates()
    templates.value = all || []
    if (!templates.value.length) {
      $q.notify({ type: 'warning', message: t('reports.noTemplatesFound') })
    }
  } catch (err) {
    $q.notify({ type: 'negative', message: t('reports.failedLoadTemplates') })
  }
}

async function loadPreview() {
  if (!selectedTemplateId.value) {
    previewData.value = null
    return
  }
  try {
    previewData.value = await reportsStore.previewTemplate(
      selectedTemplateId.value,
      props.entityType,
      Number(props.entityId),
      selectedLanguage.value,
    )
  } catch { /* ignore */ }
}

async function doGenerate() {
  generating.value = true
  generated.value = null
  try {
    const result = await reportsStore.generateReport({
      template_id: selectedTemplateId.value,
      entity_type: props.entityType,
      entity_id: Number(props.entityId),
      format: outputFormat.value,
      language: selectedLanguage.value,
    })
    generated.value = result
    emit('generated', result)
  } catch (err) {
    const detail = err?.response?.data?.detail || err?.message || t('reports.generationFailed')
    $q.notify({ type: 'negative', message: detail })
    // Try to get debug info
    try {
      const debug = await api.get(`/api/v1/reports/debug/template/${selectedTemplateId.value}`)
      console.log('Template debug:', debug.data)
    } catch { /* ignore */ }
  } finally {
    generating.value = false
  }
}

async function downloadReport() {
  if (!generated.value?.download_url) return
  // download_url is a backend path (e.g. /api/v1/storage/files/...).
  // Use the api instance so it resolves against the API base URL, not the frontend origin.
  const downloadPath = generated.value.download_url
  try {
    const resp = await api.get(downloadPath, { responseType: 'blob' })
    const blobUrl = URL.createObjectURL(resp.data)
    const a = document.createElement('a')
    a.href = blobUrl
    const ext = generated.value?.format || 'pdf'
    a.download = `report_${props.entityType}_${props.entityId}.${ext}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(blobUrl)
  } catch {
    $q.notify({ type: 'negative', message: t('reports.generationFailed') })
  }
}

function defaultLanguage() {
  const current = String(locale.value || 'en').split(/[-_]/)[0]
  return SUPPORTED_LOCALES.includes(current) ? current : 'en'
}

function pickLanguageForTemplate() {
  const current = defaultLanguage()
  const options = templateLanguageOptions.value
  if (options.some(opt => opt.value === current)) return current
  return options[0]?.value || 'en'
}

watch(() => props.modelValue, (open) => {
  if (open) {
    generated.value = null
    previewData.value = null
    selectedTemplateId.value = null
    selectedLanguage.value = defaultLanguage()
    loadTemplates()
  }
}, { immediate: true })

watch(selectedTemplateId, () => {
  generated.value = null
  selectedLanguage.value = pickLanguageForTemplate()
  loadPreview()
})

watch(selectedLanguage, () => {
  generated.value = null
  loadPreview()
})

watch(outputFormat, () => {
  generated.value = null
})
</script>

<style scoped>
.preview-section { border: 1px solid #e0e0e0; border-radius: 4px; background: #fafafa; }
.preview-box { padding: 8px; background: white; border: 1px solid #eee; }
</style>
