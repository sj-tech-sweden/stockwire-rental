import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '../boot/axios'
import { cacheSnapshot, isOnline, queueMutation, readSnapshot } from '../services/offline/orbitSync'

export const usePersonsStore = defineStore('persons', () => {
  const persons = ref([])
  const loading = ref(false)

  async function fetchAll(params = {}) {
    loading.value = true
    try {
      const { data } = await api.get('/api/v1/persons', { params })
      persons.value = data?.items ?? data
      await cacheSnapshot('persons.fetchAll', persons.value)
    } catch (error) {
      if (!isOnline()) {
        const cached = await readSnapshot('persons.fetchAll')
        if (Array.isArray(cached)) {
          persons.value = cached
          return
        }
      }
      throw error
    } finally {
      loading.value = false
    }
  }

  async function fetchPerson(id) {
    try {
      const { data } = await api.get(`/api/v1/persons/${id}`)
      return data
    } catch (error) {
      console.error('Failed to fetch person:', error)
      throw error
    }
  }

  async function fetchPersonInfo(id) {
    try {
      const { data } = await api.get(`/api/v1/persons/${id}/info`)
      return data
    } catch (error) {
      console.error('Failed to fetch person info:', error)
      throw error
    }
  }

  async function createPerson(payload) {
    if (!isOnline()) {
      const optimistic = { id: -Date.now(), ...payload, _offline_queued: true }
      persons.value = [...persons.value, optimistic]
      await queueMutation({ method: 'post', url: '/api/v1/persons', data: payload })
      await cacheSnapshot('persons.fetchAll', persons.value)
      return optimistic
    }
    try {
      const { data } = await api.post('/api/v1/persons', payload)
      persons.value = [...persons.value, data]
      await cacheSnapshot('persons.fetchAll', persons.value)
      return data
    } catch (error) {
      console.error('Failed to create person:', error)
      throw error
    }
  }

  async function updatePerson(id, payload) {
    if (!isOnline()) {
      persons.value = persons.value.map(person => person.id === id ? { ...person, ...payload, _offline_queued: true } : person)
      await queueMutation({ method: 'put', url: `/api/v1/persons/${id}`, data: payload })
      await cacheSnapshot('persons.fetchAll', persons.value)
      return persons.value.find(person => person.id === id) || { id, ...payload, _offline_queued: true }
    }
    try {
      const { data } = await api.put(`/api/v1/persons/${id}`, payload)
      persons.value = persons.value.map(person => person.id === id ? data : person)
      await cacheSnapshot('persons.fetchAll', persons.value)
      return data
    } catch (error) {
      console.error('Failed to update person:', error)
      throw error
    }
  }

  async function deletePerson(id) {
    if (!isOnline()) {
      persons.value = persons.value.filter(person => person.id !== id)
      await queueMutation({ method: 'delete', url: `/api/v1/persons/${id}` })
      await cacheSnapshot('persons.fetchAll', persons.value)
      return
    }
    try {
      await api.delete(`/api/v1/persons/${id}`)
      persons.value = persons.value.filter(person => person.id !== id)
      await cacheSnapshot('persons.fetchAll', persons.value)
    } catch (error) {
      console.error('Failed to delete person:', error)
      throw error
    }
  }

  return {
    persons,
    loading,
    fetchAll,
    fetchPerson,
    fetchPersonInfo,
    createPerson,
    updatePerson,
    deletePerson,
  }
})
