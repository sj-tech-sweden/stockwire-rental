import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../boot/axios'
import {
  isOnline,
  queueMutation,
  cacheSnapshot,
  readSnapshot,
} from '../services/offline/orbitSync'

export const useNotificationsStore = defineStore('notifications', () => {
  const subscriptions = ref([])
  const templates = ref([])
  const preferences = ref([])
  const myPreferences = ref([])
  const loading = ref(false)

  // Mirror stores/inventory.js: persist/restore this store's collections so
  // they survive an offline reload (cacheSnapshot/readSnapshot from orbitSync).
  async function persistFetchAllSnapshot() {
    await cacheSnapshot('notifications.fetchAll', {
      subscriptions: subscriptions.value,
      templates: templates.value,
      preferences: preferences.value,
      myPreferences: myPreferences.value,
    })
  }

  async function restoreFetchAllSnapshot() {
    const cached = await readSnapshot('notifications.fetchAll')
    if (!cached || typeof cached !== 'object') return false
    subscriptions.value = Array.isArray(cached.subscriptions) ? cached.subscriptions : subscriptions.value
    templates.value = Array.isArray(cached.templates) ? cached.templates : templates.value
    preferences.value = Array.isArray(cached.preferences) ? cached.preferences : preferences.value
    myPreferences.value = Array.isArray(cached.myPreferences) ? cached.myPreferences : myPreferences.value
    return true
  }

  // --- Reads --------------------------------------------------------------- #

  async function fetchVapidPublicKey() {
    const { data } = await api.get('/api/v1/notifications/vapid-public-key')
    return data
  }

  async function fetchSubscriptions() {
    const { data } = await api.get('/api/v1/notifications/subscriptions')
    subscriptions.value = Array.isArray(data) ? data : []
    return subscriptions.value
  }

  async function fetchPreferences() {
    loading.value = true
    try {
      const { data } = await api.get('/api/v1/notifications/preferences')
      preferences.value = Array.isArray(data) ? data : []
      await persistFetchAllSnapshot()
    } catch (error) {
      const restored = await restoreFetchAllSnapshot()
      if (!restored) {
        console.error('Failed to load notification preferences:', error)
        throw error
      }
    } finally {
      loading.value = false
    }
  }

  async function fetchTemplates() {
    loading.value = true
    try {
      const { data } = await api.get('/api/v1/notifications/templates')
      templates.value = Array.isArray(data) ? data : []
      await persistFetchAllSnapshot()
    } catch (error) {
      const restored = await restoreFetchAllSnapshot()
      if (!restored) {
        console.error('Failed to load notification templates:', error)
        throw error
      }
    } finally {
      loading.value = false
    }
  }

  async function fetchMyPreferences() {
    loading.value = true
    try {
      const { data } = await api.get('/api/v1/notifications/my-preferences')
      myPreferences.value = Array.isArray(data) ? data : []
      await persistFetchAllSnapshot()
    } catch (error) {
      const restored = await restoreFetchAllSnapshot()
      if (!restored) {
        console.error('Failed to load notification preferences:', error)
        throw error
      }
    } finally {
      loading.value = false
    }
  }

  // --- Mutations (offline-capable) --------------------------------------- #

  async function createSubscription(payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'post', url: '/api/v1/notifications/subscriptions', data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.post('/api/v1/notifications/subscriptions', payload)
    await persistFetchAllSnapshot()
    return data
  }

  async function deleteSubscription(id) {
    if (!isOnline()) {
      await queueMutation({ method: 'delete', url: `/api/v1/notifications/subscriptions/${id}` })
      subscriptions.value = subscriptions.value.filter((s) => s.id !== id)
      await persistFetchAllSnapshot()
      return
    }
    await api.delete(`/api/v1/notifications/subscriptions/${id}`)
    subscriptions.value = subscriptions.value.filter((s) => s.id !== id)
    await persistFetchAllSnapshot()
  }

  async function createTemplate(payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'post', url: '/api/v1/notifications/templates', data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.post('/api/v1/notifications/templates', payload)
    await persistFetchAllSnapshot()
    return data
  }

  async function updateTemplate(id, payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'put', url: `/api/v1/notifications/templates/${id}`, data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.put(`/api/v1/notifications/templates/${id}`, payload)
    await persistFetchAllSnapshot()
    return data
  }

  async function deleteTemplate(id) {
    if (!isOnline()) {
      await queueMutation({ method: 'delete', url: `/api/v1/notifications/templates/${id}` })
      templates.value = templates.value.filter((t) => t.id !== id)
      await persistFetchAllSnapshot()
      return
    }
    await api.delete(`/api/v1/notifications/templates/${id}`)
    templates.value = templates.value.filter((t) => t.id !== id)
    await persistFetchAllSnapshot()
  }

  async function updatePreference(id, payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'put', url: `/api/v1/notifications/preferences/${id}`, data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.put(`/api/v1/notifications/preferences/${id}`, payload)
    await persistFetchAllSnapshot()
    return data
  }

  async function updateMyPreference(eventType, payload) {
    if (!isOnline()) {
      await queueMutation({
        method: 'put',
        url: `/api/v1/notifications/my-preferences/${eventType}`,
        data: payload,
      })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.put(`/api/v1/notifications/my-preferences/${eventType}`, payload)
    await persistFetchAllSnapshot()
    return data
  }

  async function resetMyPreference(eventType) {
    if (!isOnline()) {
      await queueMutation({
        method: 'delete',
        url: `/api/v1/notifications/my-preferences/${eventType}`,
      })
      await persistFetchAllSnapshot()
      return
    }
    await api.delete(`/api/v1/notifications/my-preferences/${eventType}`)
    await persistFetchAllSnapshot()
  }

  // --- Admin / transient (online-only) ----------------------------------- #

  async function seedDefaults() {
    const { data } = await api.post('/api/v1/notifications/seed-defaults')
    return data
  }

  async function testNotification(templateId = null) {
    const { data } = await api.post(
      templateId != null
        ? `/api/v1/notifications/test?template_id=${templateId}`
        : '/api/v1/notifications/test',
    )
    return data
  }

  return {
    subscriptions,
    templates,
    preferences,
    myPreferences,
    loading,
    fetchVapidPublicKey,
    fetchSubscriptions,
    fetchPreferences,
    fetchTemplates,
    fetchMyPreferences,
    createSubscription,
    deleteSubscription,
    createTemplate,
    updateTemplate,
    deleteTemplate,
    updatePreference,
    updateMyPreference,
    resetMyPreference,
    seedDefaults,
    testNotification,
    persistFetchAllSnapshot,
    restoreFetchAllSnapshot,
  }
})
