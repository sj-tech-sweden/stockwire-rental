import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '../boot/axios'
import {
  cacheSnapshot,
  isOnline,
  queueMutation,
  readSnapshot,
} from '../services/offline/orbitSync'

// Storage holds AssetFile metadata (attachments, logos, letterheads, report
// outputs). This store mirrors the offline-first + realtime pattern used by
// inventory/reports.
//
// Real-time strategy: rather than fetching every file globally on each event, we
// expose a `revision` counter. Realtime refresh bumps it (invalidate()), and any
// mounted EntityAttachmentsPanel watches it and reloads only its own entity —
// avoiding a global fetch and avoiding a self-trigger loop (loadFiles does not
// touch revision).
export const useStorageStore = defineStore('storage', () => {
  const files = ref([])
  const revision = ref(0)

  async function persistFetchAllSnapshot() {
    await cacheSnapshot('storage.fetchAll', { files: files.value })
  }

  async function restoreFetchAllSnapshot() {
    const cached = await readSnapshot('storage.fetchAll')
    if (!cached || typeof cached !== 'object') return false
    files.value = Array.isArray(cached.files) ? cached.files : files.value
    return true
  }

  async function fetchFiles(params = {}) {
    if (!isOnline()) {
      const restored = await restoreFetchAllSnapshot()
      if (restored) return files.value
      return files.value
    }
    const { data } = await api.get('/api/v1/storage/files', { params })
    files.value = Array.isArray(data) ? data : []
    await persistFetchAllSnapshot()
    return files.value
  }

  async function deleteFile(id) {
    if (!isOnline()) {
      await queueMutation({ method: 'delete', url: `/api/v1/storage/files/${encodeURIComponent(id)}` })
      await persistFetchAllSnapshot()
      return
    }
    await api.delete(`/api/v1/storage/files/${encodeURIComponent(id)}`)
    await persistFetchAllSnapshot()
  }

  // File uploads are binary multipart payloads that cannot be queued through
  // queueMutation (JSON), so uploads stay online-only (like letterhead upload).
  async function uploadFile({ file, entityType, entityId, category }) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('entity_type', entityType)
    formData.append('entity_id', String(entityId))
    formData.append('category', String(category || 'document'))
    const { data } = await api.post('/api/v1/storage/files', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    await persistFetchAllSnapshot()
    return data
  }

  function invalidate() {
    revision.value += 1
  }

  return {
    files,
    revision,
    fetchFiles,
    deleteFile,
    uploadFile,
    invalidate,
    persistFetchAllSnapshot,
    restoreFetchAllSnapshot,
  }
})
