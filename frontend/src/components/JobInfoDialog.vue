<template>
  <q-dialog :model-value="modelValue" :maximized="isPhone" @update:model-value="emit('update:modelValue', $event)">
    <q-card :style="isPhone ? 'width: 100vw; max-width: 100vw; height: 100vh' : 'min-width: 820px; max-width: 96vw'" class="ec-card column">
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6">{{ t('jobs.jobInfo') }}</div>
        <q-space />
        <q-btn flat round dense icon="close" @click="emit('update:modelValue', false)" />
      </q-card-section>

      <q-card-section class="col overflow-auto q-pt-sm">
        <q-form ref="formRef" @submit.prevent="saveJob">
          <div class="row q-col-gutter-sm q-mb-md">
            <div class="col-12 col-md-6">
              <q-input v-model="form.job_code" :label="t('jobs.jobCode')" outlined dense :rules="[v => !!v || t('common.required')]" />
            </div>
            <div class="col-12 col-md-6">
              <q-select v-model="form.status" :options="statusOptions" :label="t('jobs.status')" outlined dense emit-value map-options />
            </div>
          </div>

          <q-input v-model="form.description" :label="t('jobs.description')" type="textarea" autogrow outlined dense class="q-mb-md" />

          <div class="row q-col-gutter-sm q-mb-md">
            <div class="col-12 col-md-6">
              <q-input :model-value="customerDisplayName" :label="t('jobs.customer')" outlined dense readonly @click="customerPickerOpen = true">
                <template #append>
                  <q-btn flat dense round icon="edit" size="sm" @click.stop="customerPickerOpen = true" />
                </template>
              </q-input>
            </div>
            <div class="col-12 col-md-6">
              <q-input :model-value="venueDisplayName" :label="t('jobs.venue')" outlined dense readonly @click="venuePickerOpen = true">
                <template #append>
                  <q-btn flat dense round icon="edit" size="sm" @click.stop="venuePickerOpen = true" />
                </template>
              </q-input>
            </div>
          </div>

          <div class="row q-col-gutter-sm q-mb-md">
            <div class="col-12 col-md-6">
              <q-select v-model="form.project_id" :options="projectOptions" :label="t('jobs.project')" outlined dense clearable emit-value map-options />
            </div>
            <div class="col-12 col-md-6">
              <q-input v-model="form.location_in_venue" :label="t('jobs.locationInVenue')" outlined dense clearable />
            </div>
          </div>

          <div class="row q-col-gutter-sm q-mb-md">
            <div class="col-12 col-md-6">
              <q-input v-model="form.start_date" :label="t('jobs.startDate')" type="date" outlined dense />
            </div>
            <div class="col-12 col-md-6">
              <q-input v-model="form.end_date" :label="t('jobs.endDate')" type="date" outlined dense />
            </div>
          </div>

          <div v-if="selectedVenueMapEmbedUrl" class="q-mb-md">
            <div class="text-subtitle2 q-mb-sm">{{ t('jobs.venue') }}</div>
            <q-responsive :ratio="16/9" style="max-height: 300px">
              <iframe :src="selectedVenueMapEmbedUrl" width="100%" height="100%" style="border:0" allowfullscreen loading="lazy" />
            </q-responsive>
            <q-btn flat dense no-caps color="primary" icon="open_in_new" :label="t('jobs.openVenueMap')" :href="selectedVenueMapLink" target="_blank" class="q-mt-sm" />
          </div>

          <div class="row q-col-gutter-sm q-mb-md">
            <div class="col-12 col-md-4">
              <q-input v-model.number="form.sales_price" :label="t('jobs.salesPrice')" :suffix="activeCurrencyCode" type="number" min="0" step="0.01" outlined dense />
            </div>
            <div class="col-12 col-md-4 flex items-center">
              <q-toggle v-model="form.invoice_paid" :label="t('jobs.invoicePaid')" />
            </div>
            <div class="col-12 col-md-4">
              <q-input v-model="form.invoice_paid_at" :label="t('jobs.invoicePaidAt')" type="date" outlined dense :disable="!form.invoice_paid" />
            </div>
          </div>

          <q-input v-model="form.notes" :label="t('jobs.notes')" type="textarea" autogrow outlined dense class="q-mb-md" />
        </q-form>

        <q-separator class="q-my-md" />

        <div class="row items-center justify-between q-mb-sm">
          <div class="text-subtitle2">{{ t('jobs.productRequirements') }}</div>
          <q-btn flat dense no-caps color="primary" icon="edit" :label="t('jobs.editRequirements')" @click="productRequirementDialogOpen = true" />
        </div>
        <div v-if="!productRequirementRows.length" class="text-caption text-grey-7 q-mb-md">{{ t('jobs.noRequirements') }}</div>
        <q-list v-else bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="row in productRequirementRows" :key="`prod-${row.product_id}`">
            <q-item-section>
              <q-item-label>{{ productNameForId(row.product_id) }}</q-item-label>
              <q-item-label caption>{{ t('jobs.requiredQty') }}: {{ row.quantity_required }} · {{ t('jobs.picked') }}: {{ row.quantity_picked }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <div class="row items-center justify-between q-mb-sm">
          <div class="text-subtitle2">{{ t('jobs.rentalRequirements') }}</div>
          <q-btn flat dense no-caps color="primary" icon="edit" :label="t('jobs.editRequirements')" @click="rentalRequirementDialogOpen = true" />
        </div>
        <div v-if="!rentalRequirementRows.length" class="text-caption text-grey-7 q-mb-md">{{ t('jobs.noRequirements') }}</div>
        <q-list v-else bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="row in rentalRequirementRows" :key="`rental-${row.product_id}`">
            <q-item-section>
              <q-item-label>{{ productNameForId(row.product_id) }}</q-item-label>
              <q-item-label caption>{{ t('jobs.requiredQty') }}: {{ row.quantity_required }} · {{ t('jobs.picked') }}: {{ row.quantity_picked }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <q-separator class="q-my-md" />

        <div class="row items-center justify-between q-mb-sm">
          <div class="text-subtitle2">{{ t('jobs.customFieldValues') }}</div>
          <q-btn flat dense no-caps color="primary" icon="edit" :label="t('jobs.editCustomFields')" @click="customFieldsDialogOpen = true" />
        </div>
        <div v-if="!jobFieldRows.length" class="text-caption text-grey-7 q-mb-md">{{ t('jobs.noJobCustomFields') }}</div>
        <q-list v-else bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="field in jobFieldRows" :key="field.field_definition_id">
            <q-item-section>
              <q-item-label>{{ customFieldLabel(field.label) }}</q-item-label>
              <q-item-label caption>{{ formatFieldValue(field) }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <q-separator class="q-my-md" />

        <EntityAttachmentsPanel
          entity-type="job"
          :entity-id="job?.id || null"
          :title="t('jobs.jobDocuments')"
          default-category="job-document"
        />
      </q-card-section>

      <q-card-actions :align="isPhone ? 'stretch' : 'right'" :class="isPhone ? 'q-pa-md bg-grey-2' : ''">
        <q-btn flat :class="isPhone ? 'full-width q-mb-sm' : ''" :label="t('app.actions.cancel')" @click="emit('update:modelValue', false)" />
        <q-btn color="primary" unelevated :class="isPhone ? 'full-width' : ''" :label="t('app.actions.save')" :loading="saving" @click="saveJob" />
      </q-card-actions>
    </q-card>

    <CustomerPickerDialog v-model="customerPickerOpen" :customers="customersStore.customers" :selected-id="form.customer_id" @select="onCustomerSelected" />
    <VenuePickerDialog v-model="venuePickerOpen" :venues="venuesStore.venues" :selected-id="form.venue_id" @select="onVenueSelected" />
    <JobProductRequirementDialog
      v-model="productRequirementDialogOpen"
      v-model:requirement-rows="productRequirementRows"
      :products="inventoryStore.products"
      :start-date="form.start_date"
      :end-date="form.end_date"
      :job-id="job?.id || null"
    />
    <JobRentalRequirementDialog
      v-model="rentalRequirementDialogOpen"
      v-model:requirement-rows="rentalRequirementRows"
      :products="inventoryStore.products"
      :start-date="form.start_date"
      :end-date="form.end_date"
      :job-id="job?.id || null"
    />
    <JobCustomFieldsDialog v-model="customFieldsDialogOpen" :job-id="job?.id || null" @saved="reloadFieldRows" />
  </q-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'

import { JOB_STATUSES, useJobsStore } from '../stores/jobs'
import { useCustomersStore } from '../stores/customers'
import { useVenuesStore } from '../stores/venues'
import { useInventoryStore } from '../stores/inventory'
import { useCustomFieldsStore } from '../stores/customFields'
import { useSettingsStore } from '../stores/settings'
import { useProjectsStore } from '../stores/projects'
import EntityAttachmentsPanel from './EntityAttachmentsPanel.vue'
import CustomerPickerDialog from './CustomerPickerDialog.vue'
import VenuePickerDialog from './VenuePickerDialog.vue'
import JobProductRequirementDialog from './JobProductRequirementDialog.vue'
import JobRentalRequirementDialog from './JobRentalRequirementDialog.vue'
import JobCustomFieldsDialog from './JobCustomFieldsDialog.vue'
import { translateMaybePrefillCustomFieldLabel } from '../i18n/prefillContent'
import { normalizeCurrencyCode } from '../constants/currencies'
import { googleMapsEmbedUrl, googleMapsSearchUrl, locationQueryFromParts } from '../utils/maps'

const props = defineProps({
  modelValue: Boolean,
  job: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const $q = useQuasar()
const { t } = useI18n()
const jobsStore = useJobsStore()
const customersStore = useCustomersStore()
const venuesStore = useVenuesStore()
const inventoryStore = useInventoryStore()
const customFieldsStore = useCustomFieldsStore()
const settingsStore = useSettingsStore()
const projectsStore = useProjectsStore()

const isPhone = computed(() => $q.screen.lt.md)
const activeCurrencyCode = computed(() => normalizeCurrencyCode(settingsStore.companyProfile?.currency, 'SEK'))

const formRef = ref(null)
const saving = ref(false)

const customerPickerOpen = ref(false)
const venuePickerOpen = ref(false)
const productRequirementDialogOpen = ref(false)
const rentalRequirementDialogOpen = ref(false)
const customFieldsDialogOpen = ref(false)

const form = ref(emptyForm())
const productRequirementRows = ref([])
const rentalRequirementRows = ref([])
const jobFieldRows = ref([])

function emptyForm() {
  return {
    job_code: '',
    description: '',
    project_id: null,
    location_in_venue: '',
    customer_id: null,
    customer_name: '',
    venue_id: null,
    venue_name: '',
    status: 'draft',
    start_date: null,
    end_date: null,
    sales_price: null,
    invoice_paid: false,
    invoice_paid_at: null,
    notes: '',
  }
}

const statusOptions = computed(() => JOB_STATUSES.map(s => ({
  label: statusLabel(s.value),
  value: s.value,
})))

function statusLabel(value) {
  const map = {
    draft: t('jobs.statusDraft'),
    confirmed: t('jobs.statusConfirmed'),
    in_progress: t('jobs.statusInProgress'),
    completed: t('jobs.statusCompleted'),
    cancelled: t('jobs.statusCancelled'),
  }
  return map[String(value || '').toLowerCase()] || value
}

const projectOptions = computed(() => projectsStore.projects.map(p => ({ label: p.name, value: p.id })))

const customerDisplayName = computed(() => {
  if (form.value.customer_id) {
    const c = customersStore.customers.find(c => c.id === form.value.customer_id)
    if (c) return c.email ? `${c.name} · ${c.email}` : c.name
  }
  return form.value.customer_name || t('jobs.unassigned')
})

const venueDisplayName = computed(() => {
  if (form.value.venue_id) {
    const v = venuesStore.venues.find(v => v.id === form.value.venue_id)
    if (v) return [v.name, v.city].filter(Boolean).join(' · ')
  }
  return form.value.venue_name || t('jobs.unassigned')
})

const selectedVenueLocationQuery = computed(() => {
  if (form.value.venue_id) {
    const venue = venuesStore.venues.find(v => v.id === form.value.venue_id)
    return locationQueryFromParts(venue || {})
  }
  return ''
})

const selectedVenueMapLink = computed(() => googleMapsSearchUrl(selectedVenueLocationQuery.value))
const selectedVenueMapEmbedUrl = computed(() => googleMapsEmbedUrl(selectedVenueLocationQuery.value))

function productNameForId(id) {
  const p = inventoryStore.products.find(p => p.id === id)
  return p ? `${p.sku} · ${p.name}` : `#${id}`
}

function customFieldLabel(label) {
  return translateMaybePrefillCustomFieldLabel(label, t)
}

function formatFieldValue(field) {
  if (field.value == null) return '—'
  if (field.value_type === 'boolean') return field.value === 'true' || field.value === true ? t('common.true') : t('common.false')
  return String(field.value)
}

function onCustomerSelected(customer) {
  form.value.customer_id = customer.id
  form.value.customer_name = customer.name
}

function onVenueSelected(venue) {
  form.value.venue_id = venue.id
  form.value.venue_name = venue.name
}

function normalizeDate(value) {
  if (!value) return null
  const str = String(value).slice(0, 10)
  return /^\d{4}-\d{2}-\d{2}$/.test(str) ? str : null
}

async function loadFieldRows() {
  if (!props.job?.id) {
    jobFieldRows.value = []
    return
  }
  try {
    const data = await customFieldsStore.fetchEntityValues('job', props.job.id)
    jobFieldRows.value = Array.isArray(data?.values) ? data.values.map(v => ({ ...v })) : []
  } catch {
    jobFieldRows.value = []
  }
}

function reloadFieldRows() {
  void loadFieldRows()
}

async function saveJob() {
  const valid = await formRef.value?.validate()
  if (!valid) return

  saving.value = true
  try {
    const payload = {
      ...form.value,
      customer_name: form.value.customer_name || customerDisplayName.value,
      venue_name: form.value.venue_name || venueDisplayName.value,
      start_date: normalizeDate(form.value.start_date),
      end_date: normalizeDate(form.value.end_date),
      sales_price: form.value.sales_price == null || form.value.sales_price === '' ? null : Number(form.value.sales_price),
      invoice_paid: Boolean(form.value.invoice_paid),
      invoice_paid_at: form.value.invoice_paid ? normalizeDate(form.value.invoice_paid_at) : null,
    }

    const savedJob = await jobsStore.updateJob(props.job.id, payload)

    await jobsStore.bulkUpsertRequirements(savedJob.id, [
      ...productRequirementRows.value.map(item => ({
        product_id: item.product_id,
        quantity_required: Number(item.quantity_required || 0),
        quantity_picked: Number(item.quantity_picked || 0),
        notes: item.notes || null,
      })),
      ...rentalRequirementRows.value.map(item => ({
        product_id: item.product_id,
        quantity_required: Number(item.quantity_required || 0),
        quantity_picked: Number(item.quantity_picked || 0),
        notes: item.notes || null,
      })),
    ])

    $q.notify({ type: 'positive', message: t('jobs.jobUpdated') })
    emit('saved')
    emit('update:modelValue', false)
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('common.errorOccurred') })
  } finally {
    saving.value = false
  }
}

watch(() => props.modelValue, async (open) => {
  if (open && props.job) {
    form.value = {
      job_code: props.job.job_code ?? '',
      description: props.job.description ?? '',
      project_id: props.job.project_id ?? null,
      location_in_venue: props.job.location_in_venue ?? '',
      customer_id: props.job.customer_id ?? null,
      customer_name: props.job.customer_name ?? '',
      venue_id: props.job.venue_id ?? null,
      venue_name: props.job.venue_name ?? '',
      status: props.job.status ?? 'draft',
      start_date: normalizeDate(props.job.start_date),
      end_date: normalizeDate(props.job.end_date),
      sales_price: props.job.sales_price == null ? null : Number(props.job.sales_price),
      invoice_paid: Boolean(props.job.invoice_paid),
      invoice_paid_at: normalizeDate(props.job.invoice_paid_at),
      notes: props.job.notes ?? '',
    }
    productRequirementRows.value = jobsStore.requirements
      .filter(req => req.job_id === props.job.id)
      .map(req => ({
        product_id: req.product_id,
        quantity_required: req.quantity_required,
        quantity_picked: req.quantity_picked,
        notes: req.notes || null,
      }))
    rentalRequirementRows.value = jobsStore.requirements
      .filter(req => req.job_id === props.job.id)
      .map(req => ({
        product_id: req.product_id,
        quantity_required: req.quantity_required,
        quantity_picked: req.quantity_picked,
        notes: req.notes || null,
      }))
    await loadFieldRows()
    if (!projectsStore.projects.length) projectsStore.fetchAll()
  }
})
</script>
