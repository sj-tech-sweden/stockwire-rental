<template>
  <q-page class="q-pa-md ec-page">
    <div class="row items-center justify-between q-col-gutter-sm q-mb-md">
      <div class="col-auto">
        <q-btn flat icon="arrow_back" :label="t('crew.backToMembers')" @click="goBack" />
      </div>
      <div class="col">
        <div class="text-h5">{{ isNew ? t('crew.newMember') : (member?.name || t('crew.members')) }}</div>
      </div>
      <div class="col-auto row q-gutter-sm">
        <q-btn v-if="!isNew && authStore.canEdit" color="negative" outline icon="delete" :label="t('app.actions.delete')" @click="confirmDelete" />
        <q-btn v-if="authStore.canEdit" color="primary" unelevated :label="isNew ? t('crew.create') : t('app.actions.save')" :loading="saving" @click="isNew ? createMember() : saveChanges()" />
      </div>
    </div>

    <div v-if="pageLoading" class="row justify-center q-py-xl">
      <q-spinner color="primary" size="48px" />
    </div>

    <div v-else-if="!isNew && !member" class="q-gutter-md">
      <q-banner class="bg-warning text-dark rounded-borders">
        {{ t('crew.memberNotFound') }}
      </q-banner>
      <q-btn color="primary" unelevated :label="t('crew.backToMembers')" @click="goBack" />
    </div>

    <div v-else class="column q-gutter-md">
      <q-card class="ec-card">
        <q-card-section>
          <div class="row items-center q-mb-sm">
            <div class="text-body1">{{ form.name || t('crew.memberName') }}</div>
            <q-badge v-if="form.is_active" color="positive" :label="t('crew.active')" class="q-ml-sm" />
            <q-badge v-else color="grey" :label="t('crew.inactive')" class="q-ml-sm" />
          </div>
          <div class="text-caption text-grey-7" v-if="form.email">{{ form.email }}</div>
          <div class="text-caption text-grey-7" v-if="form.phone">{{ form.phone }}</div>
          <div class="text-caption text-grey-7" v-if="!isNew">Created: {{ formatDate(member?.created_at) }}</div>
        </q-card-section>
      </q-card>

      <q-card class="ec-card">
        <q-card-section class="row items-center justify-between q-col-gutter-sm">
          <div class="col">
            <div class="text-h6">{{ isNew ? t('crew.newMember') : t('crew.editMember') }}</div>
          </div>
          <div class="col-auto" v-if="authStore.canEdit && !isNew">
            <q-btn color="primary" unelevated :label="t('app.actions.save')" :loading="saving" @click="saveChanges" />
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-form ref="formRef" @submit.prevent="isNew ? createMember() : saveChanges()">
            <div class="row q-col-gutter-sm">
              <div class="col-12 col-md-6">
                <q-input v-model="form.name" :label="t('crew.memberName')" outlined dense :disable="!authStore.canEdit" :rules="[v => !!v || t('common.required')]" />
              </div>
              <div class="col-12 col-md-6">
                <q-input v-model="form.email" :label="t('profile.email')" type="email" outlined dense :disable="!authStore.canEdit" />
              </div>
            </div>
            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-12 col-md-6">
                <q-input v-model="form.phone" :label="t('customers.phone')" outlined dense :disable="!authStore.canEdit" />
              </div>
            </div>
            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-12 col-md-4">
                <q-select v-model="form.supplier_id" :options="filteredSupplierOptions" :label="t('crew.linkSupplier')" outlined dense clearable emit-value map-options use-input :disable="!authStore.canEdit" @filter="filterSuppliers" />
              </div>
              <div class="col-12 col-md-4">
                <q-select v-model="form.person_id" :options="filteredPersonOptions" :label="t('crew.linkPerson')" outlined dense clearable emit-value map-options use-input :disable="!authStore.canEdit" @filter="filterPersons" />
              </div>
              <div class="col-12 col-md-4">
                <q-select v-model="form.user_id" :options="filteredUserOptions" :label="t('crew.linkUser')" outlined dense clearable emit-value map-options use-input :disable="!authStore.canEdit" @filter="filterUsers" />
              </div>
            </div>
            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-6 col-md-3">
                <q-input v-model.number="form.hourly_rate" type="number" min="0" step="0.01" :label="t('crew.hourlyRate')" outlined dense :disable="!authStore.canEdit" />
              </div>
              <div class="col-6 col-md-3">
                <q-input v-model.number="form.daily_rate" type="number" min="0" step="0.01" :label="t('crew.dailyRate')" outlined dense :disable="!authStore.canEdit" />
              </div>
            </div>
            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-12">
                <q-toggle v-model="form.is_active" :label="t('crew.active')" color="primary" :disable="!authStore.canEdit" />
              </div>
            </div>
            <q-input v-model="form.notes" :label="t('crew.notes')" type="textarea" autogrow outlined dense class="q-mt-sm" :disable="!authStore.canEdit" />
          </q-form>
        </q-card-section>
      </q-card>

      <q-card class="ec-card">
        <q-card-section>
          <div class="text-subtitle1 q-mb-sm">{{ t('crew.skills') }}</div>
          <SkillAutocomplete v-if="authStore.canEdit" v-model="form.skills" :label="t('crew.selectSkills')" />
          <div v-else-if="member?.skills?.length" class="row q-gutter-xs">
            <q-badge v-for="skill in member.skills" :key="skill.id" color="teal" class="q-pa-xs">
              {{ skill.name }}
              <span v-if="skill.category" class="text-caption q-ml-xs">({{ skill.category }})</span>
            </q-badge>
          </div>
          <div v-else class="text-caption text-grey-7">{{ t('crew.noSkills') }}</div>
        </q-card-section>
      </q-card>

      <q-card class="ec-card">
        <q-card-section>
          <div class="row items-center justify-between q-col-gutter-sm q-mb-sm">
            <div class="col">
              <div class="text-subtitle1">{{ t('crew.certifications') }}</div>
            </div>
            <div class="col-auto" v-if="authStore.canEdit">
              <q-btn flat dense no-caps color="primary" icon="add" :label="t('crew.addCertification')" @click="showCertDialog = true" />
            </div>
          </div>
          <div v-if="member?.certifications?.length" class="q-gutter-xs">
            <div v-for="cert in member.certifications" :key="cert.id" class="row items-center q-gutter-xs q-py-xs">
              <q-badge color="blue" class="q-pa-xs">
                {{ cert.certification?.name || cert.certification }}
                <span v-if="cert.expiry_date" class="text-caption q-ml-xs">({{ t('crew.expires') }}: {{ formatDate(cert.expiry_date) }})</span>
              </q-badge>
              <a
                v-if="cert.document_url"
                :href="cert.document_url"
                target="_blank"
                class="text-caption text-primary"
              >
                <q-icon name="description" size="xs" class="q-mr-xs" />{{ t('crew.viewDocument') }}
              </a>
              <q-btn
                v-if="authStore.canEdit"
                flat dense icon="upload" size="xs" color="secondary"
                @click="uploadCertDocument(cert)"
              />
              <q-btn v-if="authStore.canEdit" flat dense icon="close" size="xs" @click="removeCertification(cert)" />
            </div>
          </div>
          <div v-else class="text-caption text-grey-7">{{ t('crew.noCertifications') }}</div>
        </q-card-section>
      </q-card>

      <q-card class="ec-card">
        <q-card-section>
          <div class="text-subtitle1 q-mb-sm">{{ t('crew.preferredRoles') }}</div>
          <q-select v-model="form.preferred_role_ids" :options="roleOptions" multiple emit-value map-options outlined dense clearable use-chips :disable="!authStore.canEdit" />
        </q-card-section>
      </q-card>

      <q-card v-if="!isNew && member?.assignments?.length" class="ec-card">
        <q-card-section>
          <div class="text-subtitle1 q-mb-sm">{{ t('crew.jobAssignments') }}</div>
          <q-list bordered separator class="rounded-borders">
            <q-item v-for="assignment in member.assignments" :key="assignment.id">
              <q-item-section>
                <q-item-label>{{ assignment.job_code || `Job #${assignment.job_id}` }}</q-item-label>
                <q-item-label caption>{{ assignment.crew_role_name || t('crew.unknownRole') }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-badge :color="assignment.status === 'completed' ? 'positive' : 'primary'" :label="assignment.status" />
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
      </q-card>

      <q-card v-if="!isNew && feedUrl" class="ec-card">
        <q-card-section>
          <div class="text-subtitle1 q-mb-sm">{{ t('crew.calendarFeed') }}</div>
          <div class="row items-center q-gutter-sm">
            <q-input :model-value="feedUrl" outlined dense readonly class="col" />
            <q-btn flat dense icon="content_copy" color="primary" @click="copyFeedUrl" />
            <q-btn flat dense icon="open_in_new" color="secondary" @click="openFeedUrl" />
          </div>
        </q-card-section>
      </q-card>
    </div>

    <q-dialog v-model="showCertDialog" persistent @show="loadCertTypes">
      <q-card style="min-width: 320px" class="ec-card">
        <q-card-section>
          <div class="text-h6">{{ t('crew.addCertification') }}</div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-select
            v-model="newCertTypeId"
            :options="certTypeOptions"
            :label="t('crew.certificationType')"
            outlined dense emit-value map-options use-input input-debounce="300"
            :rules="[v => !!v || t('common.required')]"
            @filter="filterCertTypes"
          >
            <template #no-option>
              <q-item>
                <q-item-section class="text-grey">{{ t('crew.noMatchingCertTypes') }}</q-item-section>
              </q-item>
            </template>
          </q-select>
          <q-input v-model="newCertExpiry" :label="t('crew.expiryDate')" outlined dense type="date" class="q-mt-sm" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="cancelCert" />
          <q-btn color="primary" unelevated :label="t('app.actions.save')" :loading="addingCert" @click="addCertification" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Hidden file input for certification document upload -->
    <input ref="certFileInput" type="file" class="hidden" accept="image/*,.pdf" @change="onCertFileSelected" />
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useCrewStore } from '../stores/crew'
import { useCustomersStore } from '../stores/customers'
import { usePersonsStore } from '../stores/persons'
import { useUsersStore } from '../stores/users'
import { useAuthStore } from '../stores/auth'
import { api } from '../boot/axios'
import { getApiBaseUrl } from '../utils/runtime-config'
import SkillAutocomplete from '../components/SkillAutocomplete.vue'

const $q = useQuasar()
const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const crewStore = useCrewStore()
const customersStore = useCustomersStore()
const personsStore = usePersonsStore()
const usersStore = useUsersStore()
const authStore = useAuthStore()

const pageLoading = ref(false)
const saving = ref(false)
const formRef = ref(null)
const member = ref(null)

const isNew = computed(() => !route.params.crewMemberId)

const form = ref(emptyForm())

const filteredUserOptions = ref([])
const filteredSupplierOptions = ref([])
const filteredPersonOptions = ref([])
const userSearch = ref('')
const supplierSearch = ref('')
const personSearch = ref('')

const showCertDialog = ref(false)
const newCertTypeId = ref(null)
const newCertExpiry = ref('')
const addingCert = ref(false)
const certFileInput = ref(null)
const uploadingCertId = ref(null)
const certTypeFilter = ref('')
const certTypes = ref([])
const certTypeOptions = ref([])

const roleOptions = computed(() => crewStore.roles.map(r => ({ label: r.name, value: r.id })))

const crewFeed = ref(null)
const feedUrl = computed(() => {
  if (!member.value || !crewFeed.value) return ''
  return `${getApiBaseUrl()}/api/v1/calendar/${crewFeed.value.token}/feed.ics`
})

function emptyForm() {
  return {
    name: '',
    email: '',
    phone: '',
    user_id: null,
    supplier_id: null,
    person_id: null,
    hourly_rate: null,
    daily_rate: null,
    notes: '',
    is_active: true,
    skills: [],
    certification_items: [],
    preferred_role_ids: [],
  }
}

function formatDate(value) {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '-'
  const currentLocale = String(locale.value || 'en').toLowerCase().startsWith('sv') ? 'sv-SE' : 'en-US'
  return d.toLocaleDateString(currentLocale)
}

function filterUsers(val, update) {
  userSearch.value = val
  update(() => {
    const term = String(val || '').toLowerCase()
    if (!usersStore.users.length) {
      usersStore.fetchUsers().catch(() => {})
    }
    filteredUserOptions.value = usersStore.users
      .filter(u => !term || (u.full_name || '').toLowerCase().includes(term) || (u.email || '').toLowerCase().includes(term))
      .map(u => ({ label: `${u.full_name || u.email}`, value: u.id }))
  })
}

function filterSuppliers(val, update) {
  supplierSearch.value = val
  update(() => {
    const term = String(val || '').toLowerCase()
    if (!companiesStore.companies.length) {
      companiesStore.fetchAll().catch(() => {})
    }
    filteredSupplierOptions.value = companiesStore.companies
      .filter(c => c.is_crew_supplier)
      .filter(c => !term || c.name.toLowerCase().includes(term))
      .map(c => ({ label: c.name, value: c.id }))
  })
}

function filterPersons(val, update) {
  personSearch.value = val
  update(() => {
    const term = String(val || '').toLowerCase()
    if (!personsStore.persons.length) {
      personsStore.fetchAll().catch(() => {})
    }
    filteredPersonOptions.value = personsStore.persons
      .filter(p => !term || `${p.first_name} ${p.last_name}`.toLowerCase().includes(term) || (p.email || '').toLowerCase().includes(term))
      .map(p => ({ label: `${p.first_name} ${p.last_name}`, value: p.id }))
  })
}

function goBack() {
  router.push('/crew')
}

async function loadMember() {
  const id = Number(route.params.crewMemberId || 0)
  if (!id) {
    member.value = null
    return
  }
  try {
    member.value = await crewStore.getMember(id)
    syncFromMember()
  } catch {
    member.value = null
  }
}

function syncFromMember() {
  if (!member.value) {
    form.value = emptyForm()
    return
  }
  const m = member.value
  form.value = {
    name: m.name || '',
    email: m.email || '',
    phone: m.phone || '',
    user_id: m.user_id || null,
    supplier_id: m.supplier_id || null,
    person_id: m.person_id || null,
    hourly_rate: m.hourly_rate ?? null,
    daily_rate: m.daily_rate ?? null,
    notes: m.notes || '',
    is_active: m.is_active ?? true,
    skills: (m.skills || []).map(s => ({ id: s.id, name: s.name, label: s.name, value: s.id, category: s.category })),
    certification_items: (m.certifications || []).map(c => ({
      certification_id: c.certification?.id || c.certification_id,
      expiry_date: c.expiry_date || null,
    })),
    preferred_role_ids: (m.preferred_roles || []).map(r => r.id),
  }
}

async function fetchCrewFeed() {
  if (isNew.value || !member.value) {
    crewFeed.value = null
    return
  }
  try {
    const { data } = await api.get(`/api/v1/calendar/crew-member/${member.value.id}/feed`)
    crewFeed.value = data
  } catch {
    crewFeed.value = null
  }
}

function copyFeedUrl() {
  if (!feedUrl.value) return
  navigator.clipboard.writeText(feedUrl.value).then(() => {
    $q.notify({ type: 'positive', message: t('crew.calendarFeedCopied') })
  }).catch(() => {
    $q.notify({ type: 'negative', message: t('crew.calendarFeedCopyFailed') })
  })
}

function openFeedUrl() {
  if (feedUrl.value) window.open(feedUrl.value, '_blank')
}

async function loadData() {
  pageLoading.value = true
  try {
    await Promise.all([
      crewStore.fetchRoles(),
      companiesStore.fetchAll(),
      personsStore.fetchAll(),
      usersStore.fetchUsers(),
    ])
    if (!isNew.value) {
      await loadMember()
      await fetchCrewFeed()
    } else {
      form.value = emptyForm()
    }
  } finally {
    pageLoading.value = false
  }
}

async function createMember() {
  if (!authStore.canEdit) return
  const valid = await formRef.value?.validate()
  if (!valid) return

  saving.value = true
  try {
    const payload = {
      ...form.value,
      name: form.value.name.trim(),
      skill_ids: form.value.skills.map(s => s.id || s.value),
    }
    const saved = await crewStore.createMember(payload)
    $q.notify({ type: 'positive', message: t('crew.memberCreated') })
    await router.replace(`/crew/${saved.id}`)
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('crew.failedSaveMember') })
  } finally {
    saving.value = false
  }
}

async function saveChanges() {
  if (!member.value || !authStore.canEdit) return
  const valid = await formRef.value?.validate()
  if (!valid) return

  saving.value = true
  try {
    const payload = {
      name: form.value.name.trim(),
      email: form.value.email || null,
      phone: form.value.phone || null,
      user_id: form.value.user_id || null,
      supplier_id: form.value.supplier_id || null,
      person_id: form.value.person_id || null,
      hourly_rate: form.value.hourly_rate,
      daily_rate: form.value.daily_rate,
      notes: form.value.notes || null,
      is_active: form.value.is_active,
      skill_ids: form.value.skills.map(s => s.id || s.value),
      certification_items: form.value.certification_items,
      preferred_role_ids: form.value.preferred_role_ids,
    }
    const updated = await crewStore.updateMember(member.value.id, payload)
    member.value = updated
    syncFromMember()
    $q.notify({ type: 'positive', message: t('crew.memberUpdated') })
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('crew.failedSaveMember') })
  } finally {
    saving.value = false
  }
}

function confirmDelete() {
  $q.dialog({
    title: t('crew.deleteMember'),
    message: t('crew.deleteMemberConfirm', { name: member.value?.name }),
    cancel: t('app.actions.cancel'),
    ok: t('app.actions.delete'),
    persistent: true,
  }).onOk(async () => {
    try {
      await crewStore.deleteMember(member.value.id)
      $q.notify({ type: 'positive', message: t('crew.memberDeleted') })
      router.push('/crew')
    } catch (err) {
      $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('crew.failedDeleteMember') })
    }
  })
}

function filterCertTypes(val, update) {
  certTypeFilter.value = val
  update(() => {
    const term = (val || '').toLowerCase()
    certTypeOptions.value = certTypes.value
      .filter(c => !term || c.name.toLowerCase().includes(term) || (c.category || '').toLowerCase().includes(term))
      .map(c => ({ label: c.name + (c.category ? ` (${c.category})` : ''), value: c.id }))
  })
}

async function addCertification() {
  if (!newCertTypeId.value) return
  addingCert.value = true
  try {
    form.value.certification_items.push({
      certification_id: newCertTypeId.value,
      expiry_date: newCertExpiry.value || null,
    })
    cancelCert()
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('crew.failedSaveMember') })
  } finally {
    addingCert.value = false
  }
}

function cancelCert() {
  showCertDialog.value = false
  newCertTypeId.value = null
  newCertExpiry.value = ''
}

function removeCertification(cert) {
  form.value.certification_items = form.value.certification_items.filter(c => c.certification_id !== (cert.certification?.id || cert.certification_id))
}

function uploadCertDocument(cert) {
  uploadingCertId.value = cert.id
  certFileInput.value?.click()
}

async function onCertFileSelected(event) {
  const file = event.target.files?.[0]
  if (!file || !uploadingCertId.value) return

  const formData = new FormData()
  formData.append('file', file)
  formData.append('entity_type', 'crew_certification')
  formData.append('entity_id', String(uploadingCertId.value))
  formData.append('category', 'proof')

  try {
    const { data: uploaded } = await api.post('/api/v1/storage/files', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    await api.patch(`/api/v1/crew/users/me/certifications/${uploadingCertId.value}`, {
      document_url: `/api/v1/storage/files/${uploaded.id}/download`,
    })
    await loadMember()
    $q.notify({ type: 'positive', message: t('crew.documentUploaded') })
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('crew.failedUploadDocument') })
  } finally {
    uploadingCertId.value = null
    if (certFileInput.value) certFileInput.value.value = ''
  }
}

async function loadCertTypes() {
  if (certTypes.value.length) return
  try {
    certTypes.value = await crewStore.fetchCertifications()
  } catch {
    // silent - dropdown will just be empty
  }
}

watch(() => route.params.crewMemberId, async (next, prev) => {
  if (next === prev) return
  await loadData()
})

watch(() => route.path, async (next, prev) => {
  if (next === prev) return
  if (next === '/crew/new') {
    form.value = emptyForm()
    member.value = null
  }
})

onMounted(() => {
  loadData()
})
</script>
