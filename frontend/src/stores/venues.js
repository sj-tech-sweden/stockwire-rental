import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '../boot/axios'
import { cacheSnapshot, isOnline, queueMutation, readSnapshot } from '../services/offline/orbitSync'

export const useVenuesStore = defineStore('venues', () => {
  const venues = ref([])
  const loading = ref(false)

  async function fetchAll() {
    loading.value = true
    try {
      const { data } = await api.get('/api/v1/venues')
      venues.value = data
      await cacheSnapshot('venues.fetchAll', data)
    } catch (error) {
      if (!isOnline()) {
        const cached = await readSnapshot('venues.fetchAll')
        if (Array.isArray(cached)) {
          venues.value = cached
          return
        }
      }
      throw error
    } finally {
      loading.value = false
    }
  }

  async function createVenue(payload) {
    if (!isOnline()) {
      const optimistic = { id: -Date.now(), ...payload, _offline_queued: true }
      venues.value = [...venues.value, optimistic]
      await queueMutation({ method: 'post', url: '/api/v1/venues', data: payload })
      await cacheSnapshot('venues.fetchAll', venues.value)
      return optimistic
    }
    const { data } = await api.post('/api/v1/venues', payload)
    venues.value = [...venues.value, data]
    await cacheSnapshot('venues.fetchAll', venues.value)
    return data
  }

  async function updateVenue(id, payload) {
    if (!isOnline()) {
      venues.value = venues.value.map(venue => venue.id === id ? { ...venue, ...payload, _offline_queued: true } : venue)
      await queueMutation({ method: 'put', url: `/api/v1/venues/${id}`, data: payload })
      await cacheSnapshot('venues.fetchAll', venues.value)
      return venues.value.find(venue => venue.id === id) || { id, ...payload, _offline_queued: true }
    }
    const { data } = await api.put(`/api/v1/venues/${id}`, payload)
    venues.value = venues.value.map(venue => venue.id === id ? data : venue)
    await cacheSnapshot('venues.fetchAll', venues.value)
    return data
  }

  async function deleteVenue(id) {
    if (!isOnline()) {
      venues.value = venues.value.filter(venue => venue.id !== id)
      await queueMutation({ method: 'delete', url: `/api/v1/venues/${id}` })
      await cacheSnapshot('venues.fetchAll', venues.value)
      return
    }
    await api.delete(`/api/v1/venues/${id}`)
    venues.value = venues.value.filter(venue => venue.id !== id)
    await cacheSnapshot('venues.fetchAll', venues.value)
  }

  return { venues, loading, fetchAll, createVenue, updateVenue, deleteVenue }
})