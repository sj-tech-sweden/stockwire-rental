import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '../boot/axios'
import { cacheSnapshot, isOnline, queueMutation, readSnapshot } from '../services/offline/orbitSync'

export const CUSTOM_FIELD_ENTITY_TYPES = [
  { label: 'Products', value: 'product' },
  { label: 'Jobs', value: 'job' },
  { label: 'Customers', value: 'customer' },
  { label: 'Venues', value: 'venue' },
]

export const CUSTOM_FIELD_VALUE_TYPES = [
  { label: 'Text', value: 'text' },
  { label: 'Number', value: 'number' },
  { label: 'Boolean', value: 'boolean' },
  { label: 'Date', value: 'date' },
  { label: 'Select', value: 'select' },
]

export const useCustomFieldsStore = defineStore('custom-fields', () => {
  const definitions = ref([])
  const loading = ref(false)

  async function fetchDefinitions(entityType = null) {
    loading.value = true
    try {
      const params = entityType ? { entity_type: entityType } : undefined
      const { data } = await api.get('/api/v1/custom-fields/definitions', { params })
      definitions.value = data
      await cacheSnapshot(`custom-fields.definitions.${entityType || 'all'}`, data)
      return data
    } catch (error) {
      if (!isOnline()) {
        const cached = await readSnapshot(`custom-fields.definitions.${entityType || 'all'}`)
        if (Array.isArray(cached)) {
          definitions.value = cached
          return cached
        }
      }
      throw error
    } finally {
      loading.value = false
    }
  }

  async function createDefinition(payload) {
    if (!isOnline()) {
      const optimistic = { id: -Date.now(), ...payload, _offline_queued: true }
      definitions.value = [...definitions.value, optimistic]
      await queueMutation({ method: 'post', url: '/api/v1/custom-fields/definitions', data: payload })
      return optimistic
    }
    const { data } = await api.post('/api/v1/custom-fields/definitions', payload)
    definitions.value = [...definitions.value, data]
    return data
  }

  async function updateDefinition(id, payload) {
    if (!isOnline()) {
      definitions.value = definitions.value.map(definition => (definition.id === id ? { ...definition, ...payload, _offline_queued: true } : definition))
      await queueMutation({ method: 'put', url: `/api/v1/custom-fields/definitions/${id}`, data: payload })
      return definitions.value.find(definition => definition.id === id) || { id, ...payload, _offline_queued: true }
    }
    const { data } = await api.put(`/api/v1/custom-fields/definitions/${id}`, payload)
    definitions.value = definitions.value.map(definition => (definition.id === id ? data : definition))
    return data
  }

  async function deleteDefinition(id) {
    if (!isOnline()) {
      definitions.value = definitions.value.filter(definition => definition.id !== id)
      await queueMutation({ method: 'delete', url: `/api/v1/custom-fields/definitions/${id}` })
      return
    }
    await api.delete(`/api/v1/custom-fields/definitions/${id}`)
    definitions.value = definitions.value.filter(definition => definition.id !== id)
  }

  async function fetchEntityValues(entityType, entityId) {
    const { data } = await api.get(`/api/v1/custom-fields/values/${entityType}/${entityId}`)
    return data
  }

  async function saveEntityValues(entityType, entityId, values) {
    if (!isOnline()) {
      await queueMutation({
        method: 'put',
        url: `/api/v1/custom-fields/values/${entityType}/${entityId}`,
        data: { values },
        conflictPolicy: 'merge',
      })
      return { queued: true, values }
    }
    const { data } = await api.put(`/api/v1/custom-fields/values/${entityType}/${entityId}`, { values })
    return data
  }

  async function prefillProductCableFields() {
    const { data } = await api.post('/api/v1/custom-fields/definitions/prefill-product-cable')
    definitions.value = data
    return data
  }

  return {
    definitions,
    loading,
    fetchDefinitions,
    createDefinition,
    updateDefinition,
    deleteDefinition,
    fetchEntityValues,
    saveEntityValues,
    prefillProductCableFields,
  }
})
