<template>
  <q-page class="q-pa-md ec-page">
    <div class="row items-center justify-between q-col-gutter-sm q-mb-md">
      <div class="col-auto">
        <q-btn flat icon="arrow_back" :label="t('companies.backToCompanies')" @click="goBack" />
      </div>
      <div class="col">
        <div class="text-h5">{{ isNewCompany ? t('companies.newCompany') : (currentCompany?.name || t('companies.title')) }}</div>
      </div>
      <div class="col-auto row q-gutter-sm">
        <q-btn v-if="!isNewCompany && authStore.canEdit" color="negative" outline icon="delete" :label="t('companies.delete')" @click="confirmDelete" />
        <q-btn v-if="authStore.canEdit" color="primary" unelevated :label="isNewCompany ? t('companies.create') : t('app.actions.save')" :loading="saving" @click="isNewCompany ? createCompany() : saveChanges()" />
      </div>
    </div>

    <div v-if="pageLoading" class="row justify-center q-py-xl">
      <q-spinner color="primary" size="48px" />
    </div>

    <div v-else-if="!isNewCompany && !currentCompany" class="q-gutter-md">
      <q-banner class="bg-warning text-dark rounded-borders">
        {{ t('companies.notFound') }}
      </q-banner>
      <q-btn color="primary" unelevated :label="t('companies.backToCompanies')" @click="goBack" />
    </div>

    <div v-else class="column q-gutter-md">
      <q-card class="ec-card">
        <q-card-section>
          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-auto" v-if="form.is_customer">
              <q-badge color="primary" :label="t('companies.types.customer')" />
            </div>
            <div class="col-auto" v-if="form.is_product_supplier">
              <q-badge color="teal" :label="t('companies.types.productSupplier')" />
            </div>
            <div class="col-auto" v-if="form.is_rental_supplier">
              <q-badge color="orange" :label="t('companies.types.rentalSupplier')" />
            </div>
            <div class="col-auto" v-if="form.is_crew_supplier">
              <q-badge color="purple" :label="t('companies.types.crewSupplier')" />
            </div>
          </div>
          <div class="text-body1 q-mb-xs">{{ form.name || t('companies.noName') }}</div>
          <div class="text-caption text-grey-7" v-if="form.address || form.city">
            {{ [form.address, form.postal_code, form.city, form.country].filter(Boolean).join(', ') }}
          </div>
          <div class="text-caption text-grey-7" v-if="!isNewCompany">{{ t('companies.createdAt') }}: {{ formatDate(currentCompany?.created_at) }}</div>
          <q-btn
            v-if="twentyCompanyUrl"
            flat
            dense
            no-caps
            color="primary"
            icon="open_in_new"
            :label="t('companies.openInTwenty')"
            :href="twentyCompanyUrl"
            target="_blank"
            class="q-mt-sm"
          />
        </q-card-section>
      </q-card>

      <q-card class="ec-card">
        <q-card-section class="row items-center justify-between q-col-gutter-sm">
          <div class="col">
            <div class="text-h6">{{ isNewCompany ? t('companies.newCompany') : t('companies.editCompany') }}</div>
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-form ref="formRef" @submit.prevent="isNewCompany ? createCompany() : saveChanges()">
            <div class="row q-col-gutter-sm">
              <div class="col-12 col-md-6">
                <q-input
                  v-model="form.name"
                  :label="t('companies.name')"
                  outlined
                  dense
                  :disable="!authStore.canEdit"
                  :rules="[v => !!v || t('common.required')]"
                />
              </div>
            </div>

            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-12 col-md-6">
                <q-input v-model="form.address" :label="t('companies.address')" outlined dense :disable="!authStore.canEdit" />
              </div>
              <div class="col-12 col-md-6">
                <q-input v-model="form.city" :label="t('companies.city')" outlined dense :disable="!authStore.canEdit" />
              </div>
            </div>

            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-12 col-md-4">
                <q-input v-model="form.postal_code" :label="t('companies.postalCode')" outlined dense :disable="!authStore.canEdit" />
              </div>
              <div class="col-12 col-md-4">
                <q-select
                  v-model="form.country"
                  :options="COUNTRIES"
                  :label="t('companies.country')"
                  outlined
                  dense
                  clearable
                  emit-value
                  map-options
                  :disable="!authStore.canEdit"
                />
              </div>
            </div>

            <q-input
              v-model="form.notes"
              :label="t('companies.notes')"
              type="textarea"
              autogrow
              outlined
              dense
              class="q-mt-sm"
              :disable="!authStore.canEdit"
            />

            <div class="q-mt-sm">
              <q-toggle
                v-model="form.email_notifications_enabled"
                :label="t('companies.emailNotificationsEnabled')"
                :disable="!authStore.canEdit"
              />
            </div>

            <q-select
              v-model="form.preferred_language"
              :options="languageOptions"
              :label="t('companies.preferredLanguage')"
              emit-value
              map-options
              outlined
              dense
              class="q-mt-sm"
              :disable="!authStore.canEdit"
            />

            <q-separator class="q-my-md" />
            <div class="text-subtitle2 q-mb-sm">{{ t('companies.supplierTypes') }}</div>
            <div class="row q-col-gutter-sm">
              <div class="col-6 col-md-3">
                <q-checkbox v-model="form.is_customer" :label="t('companies.isCustomer')" :disable="!authStore.canEdit" />
              </div>
              <div class="col-6 col-md-3">
                <q-checkbox v-model="form.is_product_supplier" :label="t('companies.isProductSupplier')" :disable="!authStore.canEdit" />
              </div>
              <div class="col-6 col-md-3">
                <q-checkbox v-model="form.is_rental_supplier" :label="t('companies.isRentalSupplier')" :disable="!authStore.canEdit" />
              </div>
              <div class="col-6 col-md-3">
                <q-checkbox v-model="form.is_crew_supplier" :label="t('companies.isCrewSupplier')" :disable="!authStore.canEdit" />
              </div>
            </div>
          </q-form>
        </q-card-section>
      </q-card>

      <template v-if="!isNewCompany && info">
        <q-card class="ec-card">
          <q-card-section class="row items-center justify-between q-col-gutter-sm">
            <div class="col">
              <div class="text-subtitle2">{{ t('companies.linkedPersons') }}</div>
              <div class="text-caption text-grey-7">{{ info.persons?.length || 0 }} {{ t('companies.linkedPersons').toLowerCase() }}</div>
            </div>
            <div class="col-auto" v-if="authStore.canEdit">
              <q-btn flat dense no-caps color="primary" icon="add" :label="t('persons.addPerson')" @click="openNewPerson" />
            </div>
          </q-card-section>
          <q-card-section class="q-pt-none">
            <template v-if="info.persons?.length">
              <q-list bordered separator class="rounded-borders">
                <q-item v-for="person in info.persons" :key="`person-${person.id}`" clickable @click="router.push(`/persons/${person.id}`)">
                  <q-item-section>
                    <q-item-label>{{ person.first_name }} {{ person.last_name }}</q-item-label>
                    <q-item-label caption v-if="person.email">{{ person.email }}</q-item-label>
                    <q-item-label caption v-if="person.phone">{{ person.phone }}</q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <q-btn flat round dense icon="open_in_new" size="sm" color="primary" @click.stop="router.push(`/persons/${person.id}`)" />
                  </q-item-section>
                </q-item>
              </q-list>
            </template>
            <div v-else class="text-caption text-grey-7">{{ t('companies.noPersons') }}</div>
          </q-card-section>
        </q-card>

        <q-card v-if="form.is_customer" class="ec-card">
          <q-card-section class="row items-center justify-between q-col-gutter-sm">
            <div class="col">
              <div class="text-subtitle2">{{ t('companies.linkedJobs') }}</div>
              <div class="text-caption text-grey-7">{{ info.jobs?.length || 0 }} {{ t('companies.linkedJobs').toLowerCase() }}</div>
            </div>
          </q-card-section>
          <q-card-section class="q-pt-none">
            <template v-if="info.jobs?.length">
              <q-list bordered separator class="rounded-borders">
                <q-item v-for="job in info.jobs" :key="`job-${job.id}`" clickable @click="router.push(`/jobs/${job.id}`)">
                  <q-item-section>
                    <q-item-label>{{ job.job_code }}</q-item-label>
                    <q-item-label caption>
                      {{ job.venue_name || '-' }} · {{ job.description || t('jobs.noDescription') }}
                    </q-item-label>
                    <q-item-label caption v-if="job.start_date || job.end_date">
                      {{ formatDate(job.start_date) }} → {{ formatDate(job.end_date) }}
                    </q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <div class="row items-center no-wrap q-gutter-xs">
                      <q-badge :color="statusColor(job.status)" :label="statusLabel(job.status)" />
                      <q-btn flat round dense icon="open_in_new" size="sm" color="primary" @click.stop="router.push(`/jobs/${job.id}`)" />
                    </div>
                  </q-item-section>
                </q-item>
              </q-list>
            </template>
            <div v-else class="text-caption text-grey-7">{{ t('companies.noLinkedJobs') }}</div>
          </q-card-section>
        </q-card>

        <q-card v-if="form.is_crew_supplier" class="ec-card">
          <q-card-section class="row items-center justify-between q-col-gutter-sm">
            <div class="col">
              <div class="text-subtitle2">{{ t('companies.linkedCrew') }}</div>
              <div class="text-caption text-grey-7">{{ info.crew_members?.length || 0 }} {{ t('companies.linkedCrew').toLowerCase() }}</div>
            </div>
          </q-card-section>
          <q-card-section class="q-pt-none">
            <template v-if="info.crew_members?.length">
              <q-list bordered separator class="rounded-borders">
                <q-item v-for="cm in info.crew_members" :key="`cm-${cm.id}`" clickable @click="router.push(`/crew/${cm.id}`)">
                  <q-item-section>
                    <q-item-label>{{ cm.name }}</q-item-label>
                    <q-item-label caption>
                      <q-badge v-if="cm.is_active" color="positive" :label="t('crew.active')" class="q-mr-xs" />
                      <q-badge v-else color="grey" :label="t('crew.inactive')" class="q-mr-xs" />
                      <span v-if="cm.hourly_rate">{{ formatMoney(cm.hourly_rate) }}/h</span>
                      <span v-if="cm.daily_rate"> · {{ formatMoney(cm.daily_rate) }}/day</span>
                    </q-item-label>
                    <q-item-label caption v-if="cm.skills?.length">
                      <q-badge v-for="skill in cm.skills.slice(0, 5)" :key="skill.id || skill" color="teal" class="q-mr-xs q-mb-xs" :label="skill.name || skill" />
                      <span v-if="cm.skills.length > 5" class="text-caption text-grey-7">+{{ cm.skills.length - 5 }}</span>
                    </q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <q-btn flat round dense icon="edit" size="sm" color="primary" @click.stop="router.push(`/crew/${cm.id}`)" />
                  </q-item-section>
                </q-item>
              </q-list>
            </template>
            <div v-else class="text-caption text-grey-7">{{ t('companies.noCrewMembers') }}</div>
          </q-card-section>
        </q-card>
      </template>
    </div>

    <CompanyDeleteDialog
      v-model="deleteDialogOpen"
      :company="currentCompany"
      @deleted="onCompanyDeleted"
    />
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import { useCompaniesStore } from '../stores/companies'
import { useAuthStore } from '../stores/auth'
import { useSettingsStore } from '../stores/settings'
import { COUNTRIES } from '../constants/countries'
import { getTwentyCompanyUrl } from '../utils/twenty-links'
import CompanyDeleteDialog from '../components/CompanyDeleteDialog.vue'

const JOB_STATUSES = [
  { value: 'draft', color: 'grey', key: 'jobs.statusDraft' },
  { value: 'confirmed', color: 'blue', key: 'jobs.statusConfirmed' },
  { value: 'in_progress', color: 'orange', key: 'jobs.statusInProgress' },
  { value: 'completed', color: 'positive', key: 'jobs.statusCompleted' },
  { value: 'cancelled', color: 'negative', key: 'jobs.statusCancelled' },
]

const $q = useQuasar()
const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const companiesStore = useCompaniesStore()
const authStore = useAuthStore()
const settingsStore = useSettingsStore()

const pageLoading = ref(false)
const saving = ref(false)
const formRef = ref(null)
const info = ref(null)
const deleteDialogOpen = ref(false)
const twentyConfig = ref(null)

const languageOptions = [
  { label: 'English', value: 'en' },
  { label: 'Swedish', value: 'sv' },
]

const isNewCompany = computed(() => route.path === '/companies/new')

const currentCompany = computed(() => {
  const id = Number(route.params.companyId || 0)
  if (!id) return null
  return companiesStore.companies.find(c => c.id === id) || null
})
const twentyCompanyUrl = computed(() => getTwentyCompanyUrl(currentCompany.value, twentyConfig.value))

const emptyForm = () => ({
  name: '',
  address: '',
  city: '',
  postal_code: '',
  country: settingsStore.companyProfile?.default_country || '',
  notes: '',
  is_customer: true,
  is_product_supplier: false,
  is_rental_supplier: false,
  is_crew_supplier: false,
  email_notifications_enabled: true,
  preferred_language: 'en',
})

const form = ref(emptyForm())

function formatDate(value) {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '-'
  const currentLocale = String(locale.value || 'en').toLowerCase().startsWith('sv') ? 'sv-SE' : 'en-US'
  return d.toLocaleDateString(currentLocale)
}

function statusColor(status) {
  return JOB_STATUSES.find(s => s.value === status)?.color || 'grey'
}

function statusLabel(status) {
  const found = JOB_STATUSES.find(s => s.value === status)
  return found ? t(found.key) : status
}

function formatMoney(value) {
  const amount = Number(value || 0)
  const currentCurrency = settingsStore.companyProfile?.currency || 'SEK'
  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency: currentCurrency,
      maximumFractionDigits: 2,
    }).format(amount)
  } catch {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency: 'SEK',
      maximumFractionDigits: 2,
    }).format(amount)
  }
}

function goBack() {
  router.push('/companies')
}

async function loadInfo() {
  if (!currentCompany.value) return
  try {
    info.value = await companiesStore.fetchCompanyInfo(currentCompany.value.id)
  } catch (error) {
    console.error('Failed to load company info:', error)
  }
}

async function loadTwentyConfig() {
  try {
    const { data } = await import('../boot/axios').then(m => m.api.get('/api/v1/integrations/twenty/config'))
    twentyConfig.value = data
  } catch {
    // Twenty not configured
  }
}

function populateForm(company) {
  if (!company) return
  form.value = {
    name: company.name || '',
    address: company.address || '',
    city: company.city || '',
    postal_code: company.postal_code || '',
    country: company.country || '',
    notes: company.notes || '',
    is_customer: company.is_customer ?? true,
    is_product_supplier: company.is_product_supplier ?? false,
    is_rental_supplier: company.is_rental_supplier ?? false,
    is_crew_supplier: company.is_crew_supplier ?? false,
    email_notifications_enabled: company.email_notifications_enabled ?? true,
    preferred_language: company.preferred_language || 'en',
  }
}

async function createCompany() {
  saving.value = true
  try {
    const created = await companiesStore.createCompany(form.value)
    $q.notify({ type: 'positive', message: t('companies.createdNotice') })
    router.push(`/companies/${created.id}`)
  } catch (error) {
    console.error('Failed to create company:', error)
    $q.notify({ type: 'negative', message: t('companies.createFailed') })
  } finally {
    saving.value = false
  }
}

async function saveChanges() {
  if (!currentCompany.value) return
  saving.value = true
  try {
    await companiesStore.updateCompany(currentCompany.value.id, form.value)
    $q.notify({ type: 'positive', message: t('companies.saved') })
  } catch (error) {
    console.error('Failed to save company:', error)
    $q.notify({ type: 'negative', message: t('companies.saveFailed') })
  } finally {
    saving.value = false
  }
}

function confirmDelete() {
  deleteDialogOpen.value = true
}

function onCompanyDeleted() {
  deleteDialogOpen.value = false
  router.push('/companies')
}

function openNewPerson() {
  router.push(`/persons/new?company_id=${currentCompany.value?.id || ''}`)
}

onMounted(async () => {
  pageLoading.value = true
  try {
    await Promise.all([
      companiesStore.fetchAll(),
      loadTwentyConfig(),
    ])
    if (!isNewCompany.value && currentCompany.value) {
      populateForm(currentCompany.value)
      await loadInfo()
    }
  } finally {
    pageLoading.value = false
  }
})
</script>
