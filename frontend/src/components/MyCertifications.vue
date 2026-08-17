<template>
  <div>
    <div class="row items-center justify-between q-mb-sm">
      <div class="text-subtitle1">{{ t('crew.myCertifications') }}</div>
      <q-btn flat dense no-caps color="primary" icon="add" :label="t('crew.addCertification')" :disable="loading || noProfile" @click="showAddDialog = true" />
    </div>

    <div v-if="loading" class="text-caption text-grey-7">
      <q-spinner size="16px" class="q-mr-sm" />{{ t('app.actions.loading') }}
    </div>

    <div v-else-if="noProfile" class="text-caption text-grey-7 q-mb-sm">
      {{ t('crew.memberNotFound') }}
    </div>

    <div v-else-if="!certifications.length" class="text-caption text-grey-7 q-mb-sm">
      {{ t('crew.noCertifications') }}
    </div>

    <div v-else class="q-gutter-xs">
      <q-card v-for="cert in certifications" :key="cert.id" flat bordered class="q-pa-sm">
        <div class="row items-center justify-between">
          <div class="col">
            <div class="row items-center q-gutter-xs">
              <q-badge :color="statusColor(cert.status)" class="q-pa-xs">
                {{ statusLabel(cert.status) }}
              </q-badge>
              <span class="text-body2">{{ cert.certification_type_name }}</span>
              <span v-if="cert.certification_type_category" class="text-caption text-grey-7">
                ({{ cert.certification_type_category }})
              </span>
            </div>
            <div v-if="cert.certificate_number" class="text-caption text-grey-7">
              #{{ cert.certificate_number }}
            </div>
            <div class="text-caption text-grey-7">
              <span v-if="cert.issued_at">{{ t('crew.issued') }}: {{ formatDate(cert.issued_at) }}</span>
              <span v-if="cert.expiry_date" class="q-ml-sm">{{ t('crew.expires') }}: {{ formatDate(cert.expiry_date) }}</span>
            </div>
          </div>
          <div class="col-auto row q-gutter-xs items-center">
            <q-btn
              v-if="cert.document_url"
              flat dense icon="download" size="sm" color="primary"
              @click="downloadDocument(cert)"
            />
            <q-btn flat dense icon="upload" size="sm" color="secondary" @click="uploadDocument(cert)" />
            <q-btn flat dense icon="delete" size="sm" color="negative" @click="removeCert(cert)" />
          </div>
        </div>
      </q-card>
    </div>

    <!-- Add Certification Dialog -->
    <q-dialog v-model="showAddDialog" persistent>
      <q-card style="min-width: 360px" class="ec-card">
        <q-card-section>
          <div class="text-h6">{{ t('crew.addCertification') }}</div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-select
            v-model="newCert.certification_type_id"
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
          <q-input v-model="newCert.certificate_number" :label="t('crew.certificateNumber')" outlined dense class="q-mt-sm" />
          <div class="row q-col-gutter-sm q-mt-sm">
            <div class="col-6">
              <q-input v-model="newCert.issued_at" :label="t('crew.issuedDate')" outlined dense type="date" />
            </div>
            <div class="col-6">
              <q-input v-model="newCert.expires_at" :label="t('crew.expiryDate')" outlined dense type="date" />
            </div>
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="cancelAdd" />
          <q-btn color="primary" unelevated :label="t('app.actions.save')" :loading="adding" @click="addCert" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Hidden file input for document upload -->
    <input ref="fileInput" type="file" class="hidden" accept="image/*,.pdf" @change="onFileSelected" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useCrewStore } from '../stores/crew'
import { api } from '../boot/axios'

const $q = useQuasar()
const { t } = useI18n()
const crewStore = useCrewStore()

const loading = ref(false)
const certifications = ref([])
const certTypes = ref([])
const showAddDialog = ref(false)
const adding = ref(false)
const fileInput = ref(null)
const uploadingCertId = ref(null)
const certTypeFilter = ref('')
const noProfile = ref(false)

const newCert = ref({
  certification_type_id: null,
  certificate_number: '',
  issued_at: '',
  expires_at: '',
})

const certTypeOptions = ref([])

function filterCertTypes(val, update) {
  certTypeFilter.value = val
  update(() => {
    const term = (val || '').toLowerCase()
    certTypeOptions.value = certTypes.value
      .filter(c => !term || c.name.toLowerCase().includes(term) || (c.category || '').toLowerCase().includes(term))
      .map(c => ({ label: c.name + (c.category ? ` (${c.category})` : ''), value: c.id }))
  })
}

function statusColor(status) {
  if (status === 'valid') return 'positive'
  if (status === 'expiring_soon') return 'warning'
  return 'negative'
}

function statusLabel(status) {
  if (status === 'valid') return t('crew.statusValid')
  if (status === 'expiring_soon') return t('crew.statusExpiringSoon')
  return t('crew.statusExpired')
}

function formatDate(value) {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '-'
  return d.toLocaleDateString()
}

async function loadData() {
  loading.value = true
  try {
    const results = await Promise.allSettled([
      crewStore.fetchMyCertifications(),
      crewStore.fetchCertifications(),
    ])
    const [certsResult, typesResult] = results

    if (certsResult.status === 'fulfilled') {
      certifications.value = certsResult.value
    } else if (certsResult.reason?.response?.status === 404) {
      noProfile.value = true
    } else {
      throw certsResult.reason
    }

    if (typesResult.status === 'fulfilled') {
      certTypes.value = typesResult.value
    }
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('crew.failedLoadCertifications') })
  } finally {
    loading.value = false
  }
}

async function addCert() {
  if (!newCert.value.certification_type_id) return
  adding.value = true
  try {
    const cert = await crewStore.addMyCertification({
      certification_type_id: newCert.value.certification_type_id,
      certificate_number: newCert.value.certificate_number || null,
      issued_at: newCert.value.issued_at || null,
      expires_at: newCert.value.expires_at || null,
    })
    certifications.value.push(cert)
    cancelAdd()
    $q.notify({ type: 'positive', message: t('crew.certificationAdded') })
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('crew.failedAddCertification') })
  } finally {
    adding.value = false
  }
}

function cancelAdd() {
  showAddDialog.value = false
  newCert.value = { certification_type_id: null, certificate_number: '', issued_at: '', expires_at: '' }
}

async function removeCert(cert) {
  $q.dialog({
    title: t('crew.removeCertification'),
    message: t('crew.removeCertificationConfirm', { name: cert.certification_type_name }),
    cancel: t('app.actions.cancel'),
    ok: t('app.actions.delete'),
    persistent: true,
  }).onOk(async () => {
    try {
      await crewStore.removeMyCertification(cert.id)
      certifications.value = certifications.value.filter(c => c.id !== cert.id)
      $q.notify({ type: 'positive', message: t('crew.certificationRemoved') })
    } catch (err) {
      $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('crew.failedRemoveCertification') })
    }
  })
}

function downloadDocument(cert) {
  if (cert.document_url) {
    window.open(cert.document_url, '_blank')
  }
}

function uploadDocument(cert) {
  uploadingCertId.value = cert.id
  fileInput.value?.click()
}

async function onFileSelected(event) {
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
    await crewStore.updateMyCertification(uploadingCertId.value, {
      document_url: `/api/v1/storage/files/${uploaded.id}/download`,
    })
    const cert = certifications.value.find(c => c.id === uploadingCertId.value)
    if (cert) cert.document_url = `/api/v1/storage/files/${uploaded.id}/download`
    $q.notify({ type: 'positive', message: t('crew.documentUploaded') })
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('crew.failedUploadDocument') })
  } finally {
    uploadingCertId.value = null
    if (fileInput.value) fileInput.value.value = ''
  }
}

onMounted(loadData)
</script>
