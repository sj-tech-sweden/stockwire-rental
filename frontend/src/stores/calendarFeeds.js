import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '../boot/axios'
import {
  cacheSnapshot,
  isOnline,
  queueMutation,
  readSnapshot,
} from '../services/offline/orbitSync'

// Calendar feeds are admin-managed entities. This store is the single source of
// truth for the feed list and mirrors the offline-first + realtime pattern used
// by inventory/reports (cacheSnapshot/readSnapshot from orbitSync).
export const useCalendarFeedsStore = defineStore('calendarFeeds', () => {
  const feeds = ref([])
  const loading = ref(false)

  async function persistFetchAllSnapshot() {
    await cacheSnapshot('calendarFeeds.fetchAll', { feeds: feeds.value })
  }

  async function restoreFetchAllSnapshot() {
    const cached = await readSnapshot('calendarFeeds.fetchAll')
    if (!cached || typeof cached !== 'object') return false
    feeds.value = Array.isArray(cached.feeds) ? cached.feeds : feeds.value
    return true
  }

  async function fetchFeeds() {
    if (!isOnline()) {
      const restored = await restoreFetchAllSnapshot()
      if (restored) return feeds.value
      // Fall back to an empty list if nothing was cached.
      return feeds.value
    }
    loading.value = true
    try {
      const { data } = await api.get('/api/v1/calendar/feeds')
      feeds.value = Array.isArray(data) ? data : []
      await persistFetchAllSnapshot()
      return feeds.value
    } catch (error) {
      if (!isOnline()) {
        const restored = await restoreFetchAllSnapshot()
        if (restored) return feeds.value
      }
      throw error
    } finally {
      loading.value = false
    }
  }

  async function createFeed(payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'post', url: '/api/v1/calendar/feeds', data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.post('/api/v1/calendar/feeds', payload)
    feeds.value = [data, ...feeds.value.filter((f) => f.id !== data.id)]
    await persistFetchAllSnapshot()
    return data
  }

  async function updateFeed(id, payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'put', url: `/api/v1/calendar/feeds/${id}`, data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.put(`/api/v1/calendar/feeds/${id}`, payload)
    const idx = feeds.value.findIndex((f) => f.id === id)
    if (idx >= 0) feeds.value[idx] = data
    await persistFetchAllSnapshot()
    return data
  }

  async function deleteFeed(id) {
    if (!isOnline()) {
      await queueMutation({ method: 'delete', url: `/api/v1/calendar/feeds/${id}` })
      await persistFetchAllSnapshot()
      return
    }
    await api.delete(`/api/v1/calendar/feeds/${id}`)
    feeds.value = feeds.value.filter((f) => f.id !== id)
    await persistFetchAllSnapshot()
  }

  async function regenerateToken(id) {
    if (!isOnline()) {
      await queueMutation({ method: 'post', url: `/api/v1/calendar/feeds/${id}/regenerate-token` })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.post(`/api/v1/calendar/feeds/${id}/regenerate-token`)
    const idx = feeds.value.findIndex((f) => f.id === id)
    if (idx >= 0) feeds.value[idx] = data
    await persistFetchAllSnapshot()
    return data
  }

  return {
    feeds,
    loading,
    fetchFeeds,
    createFeed,
    updateFeed,
    deleteFeed,
    regenerateToken,
    persistFetchAllSnapshot,
    restoreFetchAllSnapshot,
  }
})
