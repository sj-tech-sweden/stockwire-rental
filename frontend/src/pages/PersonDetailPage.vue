<template>
  <q-page class="q-pa-md ec-page">
    <div class="row items-center justify-between q-col-gutter-sm q-mb-md">
      <div class="col-auto">
        <q-btn flat icon="arrow_back" :label="t('persons.backToPersons')" @click="goBack" />
      </div>
      <div class="col">
        <div class="text-h5">{{ isNewPerson ? t('persons.newPerson') : personFullName }}</div>
      </div>
      <div class="col-auto row q-gutter-sm">
        <q-btn v-if="!isNewPerson && authStore.canEdit" color="negative" outline icon="delete" :label="t('persons.delete')" @click="confirmDelete" />
        <q-btn v-if="authStore.canEdit" color="primary" unelevated :label="isNewPerson ? t('persons.create') : t('app.actions.save')" :loading="saving" @click="isNewPerson ? createPerson() : saveChanges()" />
      </div>
    </div>

    <div v-if="pageLoading" class="row justify-center q-py-xl">
      <q-spinner color="primary" size="48px" />
    </div>

    <div v-else-if="!isNewPerson && !currentPerson" class="q-gutter-md">
      <q-banner class="bg-warning text-dark rounded-borders">
        {{ t('persons.notFound') }}
      </q-banner>
      <q-btn color="primary" unelevated :label="t('persons.backToPersons')" @click="goBack" />
    </div>

    <div v-else class="column q-gutter-md">
      <q-card class="ec-card">
        <q-card-section>
          <div class="text-body1 q-mb-xs">{{ personFullName || t('persons.noName') }}</div>
          <div class="text-caption text-grey-7" v-if="form.email">{{ form.email }}</div>
          <div class="text-caption text-grey-7" v-if="form.phone">{{ form.phone }}</div>
          <div class="text-caption text-grey-7" v-if="selectedCompanyName">
            {{ t('persons.company') }}:
            <q-btn flat dense no-caps color="primary" :label="selectedCompanyName" size="sm" @click="router.push(`/companies/${form.company_id}`)" />
          </div>
          <div class="text-caption text-grey-7" v-if="!isNewPerson">{{ t('persons.createdAt') }}: {{ formatDate(currentPerson?.created_at) }}</div>
        </q-card-section>
      </q-card>

      <q-card class="ec-card">
        <q-card-section class="row items-center justify-between q-col-gutter-sm">
          <div class="col">
            <div class="text-h6">{{ isNewPerson ? t('persons.newPerson') : t('persons.editPerson') }}</div>
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-form ref="formRef" @submit.prevent="isNewPerson ? createPerson() : saveChanges()">
            <div class="row q-col-gutter-sm">
              <div class="col-12 col-md-6">
                <q-input
                  v-model="form.first_name"
                  :label="t('persons.firstName')"
                  outlined
                  dense
                  :disable="!authStore.canEdit"
                  :rules="[v => !!v || t('common.required')]"
                />
              </div>
              <div class="col-12 col-md-6">
                <q-input
                  v-model="form.last_name"
                  :label="t('persons.lastName')"
                  outlined
                  dense
                  :disable="!authStore.canEdit"
                  :rules="[v => !!v || t('common.required')]"
                />
              </div>
            </div>

            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-12 col-md-6">
                <q-input v-model="form.email" :label="t('profile.email')" type="email" outlined dense :disable="!authStore.canEdit" />
              </div>
              <div class="col-12 col-md-6">
                <q-input v-model="form.phone" :label="t('persons.phone')" outlined dense :disable="!authStore.canEdit" />
              </div>
            </div>

            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-12 col-md-6">
                <q-input v-model="form.address" :label="t('persons.address')" outlined dense :disable="!authStore.canEdit" />
              </div>
              <div class="col-12 col-md-6">
                <q-input v-model="form.city" :label="t('persons.city')" outlined dense :disable="!authStore.canEdit" />
              </div>
            </div>

            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-12 col-md-4">
                <q-input v-model="form.postal_code" :label="t('persons.postalCode')" outlined dense :disable="!authStore.canEdit" />
              </div>
              <div class="col-12 col-md-4">
                <q-select
                  v-model="form.country"
                  :options="COUNTRIES"
                  :label="t('persons.country')"
                  outlined
                  dense
                  clearable
                  emit-value
                  map-options
                  :disable="!authStore.canEdit"
                />
              </div>
              <div class="col-12 col-md-4">
                <q-select
                  v-model="form.company_id"
                  :options="companyOptions"
                  :label="t('persons.company')"
                  outlined
                  dense
                  clearable
                  emit-value
                  map-options
                  use-input
                  input-debounce="300"
                  @filter="filterCompanies"
                  :disable="!authStore.canEdit"
                />
              </div>
            </div>

            <q-input
              v-model="form.notes"
              :label="t('persons.notes')"
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
                :label="t('persons.emailNotificationsEnabled')"
                :disable="!authStore.canEdit"
              />
            </div>

            <q-select
              v-model="form.preferred_language"
              :options="languageOptions"
              :label="t('persons.preferredLanguage')"
              emit-value
              map-options
              outlined
              dense
              class="q-mt-sm"
              :disable="!authStore.canEdit"
            />
          </q-form>
        </q-card-section>
      </q-card>

      <template v-if="!isNewPerson && personInfo">
        <q-card v-if="personInfo.crew_member_id" class="ec-card">
          <q-card-section class="row items-center justify-between q-col-gutter-sm">
            <div class="col">
              <div class="text-subtitle2">{{ t('persons.crewMember') }}</div>
              <div class="text-caption text-grey-7">
                <q-badge v-if="personInfo.crew_member_is_active" color="positive" :label="t('crew.active')" class="q-mr-xs" />
                <q-badge v-else color="grey" :label="t('crew.inactive')" class="q-mr-xs" />
                <span v-if="personInfo.crew_member_hourly_rate">{{ formatMoney(personInfo.crew_member_hourly_rate) }}/h</span>
                <span v-if="personInfo.crew_member_daily_rate"> · {{ formatMoney(personInfo.crew_member_daily_rate) }}/day</span>
              </div>
              <div class="text-caption text-grey-7" v-if="personInfo.crew_member_skills?.length">
                {{ t('crew.skills') }}: {{ personInfo.crew_member_skills.join(', ') }}
              </div>
              <div class="text-caption text-grey-7" v-if="personInfo.crew_member_certifications?.length">
                {{ t('crew.certifications') }}: {{ personInfo.crew_member_certifications.join(', ') }}
              </div>
              <div class="text-caption text-grey-7" v-if="personInfo.crew_member_preferred_roles?.length">
                {{ t('crew.preferredRoles') }}: {{ personInfo.crew_member_preferred_roles.join(', ') }}
              </div>
            </div>
            <div class="col-auto">
              <q-btn flat dense no-caps color="primary" icon="open_in_new" :label="t('persons.viewCrewMember')" @click="router.push(`/crew/${personInfo.crew_member_id}`)" />
            </div>
          </q-card-section>
        </q-card>

        <q-card v-if="!personInfo.crew_member_id && authStore.canEdit" class="ec-card">
          <q-card-section>
            <div class="text-subtitle2 q-mb-sm">{{ t('persons.crewMemberLink') }}</div>
            <div class="row q-col-gutter-sm items-end">
              <div class="col">
                <q-select
                  v-model="selectedCrewMemberId"
                  :options="filteredCrewMemberOptions"
                  :label="t('persons.linkExistingCrewMember')"
                  outlined
                  dense
                  clearable
                  emit-value
                  map-options
                  use-input
                  input-debounce="300"
                  @filter="filterCrewMembers"
                />
              </div>
              <div class="col-auto">
                <q-btn color="primary" unelevated icon="link" :label="t('persons.linkCrewMember')" :loading="linkingCrewMember" :disable="!selectedCrewMemberId" @click="linkToExistingCrewMember" />
              </div>
            </div>
            <q-separator class="q-my-md" />
            <div class="row q-col-gutter-sm items-end">
              <div class="col">
                <div class="text-caption text-grey-7">{{ t('persons.orCreateNew') }}</div>
              </div>
              <div class="col-auto">
                <q-btn color="secondary" outline icon="group_add" :label="t('persons.createCrewMember')" @click="createCrewMemberFromPerson" :loading="creatingCrewMember" />
              </div>
            </div>
          </q-card-section>
        </q-card>
      </template>
    </div>

    <PersonDeleteDialog
      v-model="deleteDialogOpen"
      :person="currentPerson"
      @deleted="onPersonDeleted"
    />
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import { usePersonsStore } from '../stores/persons'
import { useCompaniesStore } from '../stores/companies'
import { useCrewStore } from '../stores/crew'
import { useAuthStore } from '../stores/auth'
import { useSettingsStore } from '../stores/settings'
import { COUNTRIES } from '../constants/countries'
import { normalizeCurrencyCode } from '../constants/currencies'
import PersonDeleteDialog from '../components/PersonDeleteDialog.vue'

const $q = useQuasar()
const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const personsStore = usePersonsStore()
const companiesStore = useCompaniesStore()
const crewStore = useCrewStore()
const authStore = useAuthStore()
const settingsStore = useSettingsStore()

const pageLoading = ref(false)
const saving = ref(false)
const creatingCrewMember = ref(false)
const linkingCrewMember = ref(false)
const selectedCrewMemberId = ref(null)
const crewMemberSearch = ref('')
const filteredCrewMemberOptions = ref([])
const formRef = ref(null)
const personInfo = ref(null)
const deleteDialogOpen = ref(false)
const companyFilter = ref('')

const languageOptions = [
  { label: 'English', value: 'en' },
  { label: 'Swedish', value: 'sv' },
]

const isNewPerson = computed(() => route.path === '/persons/new')

const currentPerson = computed(() => {
  const id = Number(route.params.personId || 0)
  if (!id) return null
  return personsStore.persons.find(p => p.id === id) || null
})

const personFullName = computed(() => {
  if (!currentPerson.value) return ''
  return `${currentPerson.value.first_name || ''} ${currentPerson.value.last_name || ''}`.trim()
})

const companyOptions = computed(() => {
  const companies = companiesStore.companies || []
  if (companyFilter.value) {
    return companies
      .filter(c => c.name.toLowerCase().includes(companyFilter.value.toLowerCase()))
      .map(c => ({ label: c.name, value: c.id }))
  }
  return companies.map(c => ({ label: c.name, value: c.id }))
})

const selectedCompanyName = computed(() => {
  if (!form.value.company_id) return null
  const company = companiesStore.companies.find(c => c.id === form.value.company_id)
  return company?.name || null
})

function filterCompanies(val, update) {
  companyFilter.value = val
  update()
}

function formatMoney(value) {
  const amount = Number(value || 0)
  const currentCurrency = normalizeCurrencyCode(settingsStore.companyProfile?.currency, 'SEK')
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

const emptyForm = () => ({
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  address: '',
  city: '',
  postal_code: '',
  country: '',
  notes: '',
  company_id: null,
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

function goBack() {
  router.push('/persons')
}

async function loadInfo() {
  if (!currentPerson.value) return
  try {
    personInfo.value = await personsStore.fetchPersonInfo(currentPerson.value.id)
  } catch (error) {
    console.error('Failed to load person info:', error)
  }
}

function populateForm(person) {
  if (!person) return
  form.value = {
    first_name: person.first_name || '',
    last_name: person.last_name || '',
    email: person.email || '',
    phone: person.phone || '',
    address: person.address || '',
    city: person.city || '',
    postal_code: person.postal_code || '',
    country: person.country || '',
    notes: person.notes || '',
    company_id: person.company_id || null,
    email_notifications_enabled: person.email_notifications_enabled ?? true,
    preferred_language: person.preferred_language || 'en',
  }
}

async function createPerson() {
  saving.value = true
  try {
    const created = await personsStore.createPerson(form.value)
    $q.notify({ type: 'positive', message: t('persons.createdNotice') })
    router.push(`/persons/${created.id}`)
  } catch (error) {
    console.error('Failed to create person:', error)
    $q.notify({ type: 'negative', message: t('persons.createFailed') })
  } finally {
    saving.value = false
  }
}

async function saveChanges() {
  if (!currentPerson.value) return
  saving.value = true
  try {
    await personsStore.updatePerson(currentPerson.value.id, form.value)
    $q.notify({ type: 'positive', message: t('persons.saved') })
  } catch (error) {
    console.error('Failed to save person:', error)
    $q.notify({ type: 'negative', message: t('persons.saveFailed') })
  } finally {
    saving.value = false
  }
}

function confirmDelete() {
  deleteDialogOpen.value = true
}

function onPersonDeleted() {
  deleteDialogOpen.value = false
  router.push('/persons')
}

function filterCrewMembers(val, update) {
  crewMemberSearch.value = val
  update(() => {
    const term = String(val || '').toLowerCase()
    crewStore.fetchMembers().catch(() => {})
    filteredCrewMemberOptions.value = crewStore.members
      .filter(m => !m.person_id)
      .filter(m => !term || m.name.toLowerCase().includes(term) || (m.email || '').toLowerCase().includes(term))
      .map(m => ({ label: m.name, value: m.id }))
  })
}

async function linkToExistingCrewMember() {
  if (!currentPerson.value || !selectedCrewMemberId.value) return
  linkingCrewMember.value = true
  try {
    await crewStore.updateMember(selectedCrewMemberId.value, {
      person_id: currentPerson.value.id,
    })
    $q.notify({ type: 'positive', message: t('persons.crewMemberLinked') })
    selectedCrewMemberId.value = null
    await loadInfo()
  } catch (error) {
    console.error('Failed to link crew member:', error)
    $q.notify({ type: 'negative', message: t('persons.crewMemberLinkFailed') })
  } finally {
    linkingCrewMember.value = false
  }
}

async function createCrewMemberFromPerson() {
  if (!currentPerson.value) return
  creatingCrewMember.value = true
  try {
    const payload = {
      name: `${currentPerson.value.first_name || ''} ${currentPerson.value.last_name || ''}`.trim(),
      email: currentPerson.value.email || '',
      phone: currentPerson.value.phone || '',
      person_id: currentPerson.value.id,
      is_active: true,
    }
    const created = await crewStore.createMember(payload)
    $q.notify({ type: 'positive', message: t('persons.crewMemberCreated') })
    await loadInfo()
    router.push(`/crew/${created.id}`)
  } catch (error) {
    console.error('Failed to create crew member:', error)
    $q.notify({ type: 'negative', message: t('persons.crewMemberCreateFailed') })
  } finally {
    creatingCrewMember.value = false
  }
}

onMounted(async () => {
  pageLoading.value = true
  try {
    await Promise.all([
      personsStore.fetchAll(),
      companiesStore.fetchAll(),
    ])
    if (!isNewPerson.value && currentPerson.value) {
      populateForm(currentPerson.value)
      await loadInfo()
    } else if (isNewPerson.value) {
      // Pre-fill company_id from query param if present
      const companyId = route.query.company_id
      if (companyId) {
        form.value.company_id = Number(companyId)
      }
    }
  } finally {
    pageLoading.value = false
  }
})
</script>
