<template>
  <q-expansion-item
    v-model="openState"
    icon="attach_file"
    :label="title || t('attachments.title')"
    dense
    class="q-mt-md"
  >
    <div class="q-pt-sm">
      <div v-if="!entityId" class="text-caption text-grey-7 q-mb-sm">
        {{ readOnly ? t('attachments.noLinkedRecordReadOnly') : t('attachments.noLinkedRecord') }}
      </div>

      <template v-else>
        <div v-if="!readOnly">
          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-12 col-md-4">
              <q-input v-model="category" :label="t('attachments.category')" outlined dense />
            </div>
            <div class="col-12 col-md-8">
              <q-file
                v-model="uploadFile"
                :label="t('attachments.chooseFile')"
                outlined
                dense
                clearable
              />
            </div>
          </div>

          <div class="row items-center q-gutter-sm q-mb-sm">
            <q-btn
              color="primary"
              icon="upload_file"
              :label="t('attachments.upload')"
              unelevated
              :disable="!uploadFile"
              :loading="uploading"
              @click="submitUpload"
            />
            <q-btn
              flat
              color="primary"
              icon="refresh"
              :label="t('app.actions.refresh')"
              :loading="loading"
              @click="loadFiles"
            />
          </div>
        </div>

        <div v-else class="row items-center q-gutter-sm q-mb-sm">
          <q-btn
            flat
            color="primary"
            icon="refresh"
            :label="t('app.actions.refresh')"
            :loading="loading"
            @click="loadFiles"
          />
        </div>

        <q-list bordered separator class="rounded-borders">
          <q-item v-for="item in files" :key="item.id">
            <q-item-section avatar>
              <q-img
                v-if="isImageFile(item)"
                :src="blobUrlsById[item.id] || ''"
                style="width: 56px; height: 56px; border-radius: 6px"
                fit="cover"
                spinner-color="primary"
              >
                <template #error>
                  <div class="column items-center justify-center full-width full-height bg-grey-3 text-grey-8">
                    <q-icon name="image" size="20px" />
                  </div>
                </template>
              </q-img>
              <iframe
                v-else-if="isPdfFile(item)"
                :src="pdfPreviewUrl(item)"
                title="PDF preview"
                style="width: 56px; height: 56px; border: 1px solid #d6dbe2; border-radius: 6px; background: white"
              />
              <div v-else class="row items-center justify-center" style="width: 56px; height: 56px; border: 1px solid #d6dbe2; border-radius: 6px;">
                <q-icon name="description" color="grey-7" size="24px" />
              </div>
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ item.original_filename }}</q-item-label>
              <q-item-label caption>
                {{ item.category || t('attachments.general') }} · {{ formatSize(item.size_bytes) }}
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <div class="row no-wrap q-gutter-xs">
                <q-btn
                  flat
                  dense
                  icon="open_in_new"
                  color="primary"
                  @click="openFile(item)"
                />
                <q-btn
                  flat
                  dense
                  icon="download"
                  color="primary"
                  @click="downloadFile(item)"
                />
                <q-btn
                  v-if="!readOnly"
                  flat
                  dense
                  icon="delete"
                  color="negative"
                  :loading="deletingId === item.id"
                  @click="removeFile(item)"
                />
              </div>
            </q-item-section>
          </q-item>
          <q-item v-if="!files.length">
            <q-item-section>
              <q-item-label caption>{{ t('attachments.noneYet') }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </template>
    </div>
  </q-expansion-item>
</template>

<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'

import { api } from '../boot/axios'

const props = defineProps({
  entityType: {
    type: String,
    required: true,
  },
  entityId: {
    type: Number,
    default: null,
  },
  title: {
    type: String,
    default: '',
  },
  defaultCategory: {
    type: String,
    default: 'document',
  },
  readOnly: {
    type: Boolean,
    default: false,
  },
  defaultOpen: {
    type: Boolean,
    default: false,
  },
})

const $q = useQuasar()
const { t } = useI18n()

const openState = ref(Boolean(props.defaultOpen))
const loading = ref(false)
const uploading = ref(false)
const deletingId = ref(null)
const uploadFile = ref(null)
const category = ref(props.defaultCategory)
const files = ref([])
const blobUrlsById = ref({})

function formatSize(bytes) {
  const value = Number(bytes || 0)
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / (1024 * 1024)).toFixed(1)} MB`
}

function extensionFromName(name) {
  const value = String(name || '').trim().toLowerCase()
  const idx = value.lastIndexOf('.')
  if (idx < 0) return ''
  return value.slice(idx)
}

function isImageFile(item) {
  const contentType = String(item?.content_type || '').toLowerCase()
  if (contentType.startsWith('image/')) return true
  const ext = extensionFromName(item?.original_filename)
  return ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg'].includes(ext)
}

function isPdfFile(item) {
  const contentType = String(item?.content_type || '').toLowerCase()
  if (contentType === 'application/pdf') return true
  return extensionFromName(item?.original_filename) === '.pdf'
}

function pdfPreviewUrl(item) {
  const blobUrl = blobUrlsById.value[item.id]
  if (!blobUrl) return ''
  return `${blobUrl}#toolbar=0&navpanes=0&scrollbar=0&page=1&view=FitH`
}

function revokeAllBlobUrls() {
  for (const url of Object.values(blobUrlsById.value || {})) {
    if (typeof url === 'string' && url) {
      URL.revokeObjectURL(url)
    }
  }
  blobUrlsById.value = {}
}

async function ensureBlobUrl(item) {
  const fileId = Number(item?.id || 0)
  if (!fileId) return ''
  if (blobUrlsById.value[fileId]) return blobUrlsById.value[fileId]

  const { data } = await api.get(item.download_url, { responseType: 'blob', timeout: 60000 })
  const blobUrl = URL.createObjectURL(data)
  blobUrlsById.value = {
    ...blobUrlsById.value,
    [fileId]: blobUrl,
  }
  return blobUrl
}

async function preloadPreviewBlobs(fileRows) {
  const previewRows = (fileRows || []).filter(item => isImageFile(item) || isPdfFile(item))
  for (const item of previewRows) {
    try {
      await ensureBlobUrl(item)
    } catch {
      // Ignore preview fetch failures; open/download can still be attempted explicitly.
    }
  }
}

async function openFile(item) {
  try {
    const blobUrl = await ensureBlobUrl(item)
    if (!blobUrl) return
    window.open(blobUrl, '_blank', 'noopener,noreferrer')
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('attachments.failedOpen') })
  }
}

async function downloadFile(item) {
  try {
    const blobUrl = await ensureBlobUrl(item)
    if (!blobUrl) return
    const anchor = document.createElement('a')
    anchor.href = blobUrl
    anchor.download = String(item?.original_filename || 'download')
    document.body.appendChild(anchor)
    anchor.click()
    document.body.removeChild(anchor)
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('attachments.failedDownload') })
  }
}

async function loadFiles() {
  if (!props.entityId) {
    files.value = []
    return
  }

  loading.value = true
  try {
    const { data } = await api.get('/api/v1/storage/files', {
      params: {
        entity_type: props.entityType,
        entity_id: props.entityId,
      },
    })
    const rows = Array.isArray(data) ? data : []
    files.value = rows
    revokeAllBlobUrls()
    await preloadPreviewBlobs(rows)
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('attachments.failedLoad') })
  } finally {
    loading.value = false
  }
}

async function submitUpload() {
  if (!uploadFile.value || !props.entityId) return

  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', uploadFile.value)
    formData.append('entity_type', props.entityType)
    formData.append('entity_id', String(props.entityId))
    formData.append('category', String(category.value || props.defaultCategory || 'document'))

    await api.post('/api/v1/storage/files', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    uploadFile.value = null
    await loadFiles()
    $q.notify({ type: 'positive', message: t('attachments.uploaded') })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('attachments.uploadFailed') })
  } finally {
    uploading.value = false
  }
}

async function removeFile(item) {
  deletingId.value = item.id
  try {
    await api.delete(`/api/v1/storage/files/${encodeURIComponent(item.id)}`)
    await loadFiles()
    $q.notify({ type: 'positive', message: t('attachments.deleted') })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('common.deleteFailed') })
  } finally {
    deletingId.value = null
  }
}

watch(() => props.entityId, () => {
  uploadFile.value = null
  if (props.entityId) {
    loadFiles()
  } else {
    revokeAllBlobUrls()
    files.value = []
  }
}, { immediate: true })

watch(() => props.defaultCategory, (nextValue) => {
  category.value = nextValue || 'document'
})

onBeforeUnmount(() => {
  revokeAllBlobUrls()
})
</script>
