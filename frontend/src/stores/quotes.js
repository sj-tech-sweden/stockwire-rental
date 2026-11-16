import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '../boot/axios'
import {
  cacheSnapshot,
  isOnline,
  queueMutation,
  readSnapshot,
} from '../services/offline/orbitSync'

export const useQuotesStore = defineStore('quotes', () => {
  const settings = ref({})
  const loading = ref(false)

  // Mirror stores/inventory.js: persist/restore this store's collections so
  // they survive an offline reload (cacheSnapshot/readSnapshot from orbitSync).
  async function persistFetchAllSnapshot() {
    await cacheSnapshot('quotes.fetchAll', { settings: settings.value })
  }

  async function restoreFetchAllSnapshot() {
    const cached = await readSnapshot('quotes.fetchAll')
    if (!cached || typeof cached !== 'object') return false
    settings.value = cached.settings && typeof cached.settings === 'object' ? cached.settings : settings.value
    return true
  }

  async function fetchSettings() {
    try {
      const { data } = await api.get('/api/v1/quotes/settings')
      settings.value = data || {}
      await persistFetchAllSnapshot()
      return settings.value
    } catch (error) {
      if (!isOnline()) {
        const restored = await restoreFetchAllSnapshot()
        if (restored) return settings.value
      }
      throw error
    }
  }

  async function updateSettings(payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'put', url: '/api/v1/quotes/settings', data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.put('/api/v1/quotes/settings', payload)
    settings.value = data || {}
    await persistFetchAllSnapshot()
    return settings.value
  }

  // PDF generation is a server-side render + download and cannot be queued
  // while offline. It is an online-only action (like route optimization); the
  // resulting job-status flip is broadcast via the "jobs.updated" topic.
  async function generateQuote(jobId) {
    const resp = await api.post(`/api/v1/quotes/jobs/${jobId}/generate`, {}, { responseType: 'blob' })
    return resp
  }

  return {
    settings,
    loading,
    fetchSettings,
    updateSettings,
    generateQuote,
    persistFetchAllSnapshot,
    restoreFetchAllSnapshot,
  }
})
