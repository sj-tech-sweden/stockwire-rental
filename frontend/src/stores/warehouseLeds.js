import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../boot/axios'

export const useWarehouseLedsStore = defineStore('warehouseLeds', () => {
  const controllers = ref([])
  const mappings = ref([])
  const statuses = ref([])
  const loading = ref(false)

  async function fetchControllers() {
    loading.value = true
    try {
      const { data } = await api.get('/api/v1/warehouse-leds/controllers')
      controllers.value = data
    } finally {
      loading.value = false
    }
  }

  async function createController(payload) {
    const { data } = await api.post('/api/v1/warehouse-leds/controllers', payload)
    controllers.value = [...controllers.value, data]
    return data
  }

  async function updateController(id, payload) {
    const { data } = await api.patch(`/api/v1/warehouse-leds/controllers/${id}`, payload)
    controllers.value = controllers.value.map(c => c.id === id ? data : c)
    return data
  }

  async function deleteController(id) {
    await api.delete(`/api/v1/warehouse-leds/controllers/${id}`)
    controllers.value = controllers.value.filter(c => c.id !== id)
  }

  async function fetchControllerZones(controllerId) {
    const { data } = await api.get(`/api/v1/warehouse-leds/controllers/${controllerId}/zones`)
    return data
  }

  async function setControllerZones(controllerId, zoneIds) {
    const { data } = await api.put(`/api/v1/warehouse-leds/controllers/${controllerId}/zones`, { zone_ids: zoneIds })
    return data
  }

  async function fetchMappings(params = {}) {
    loading.value = true
    try {
      const { data } = await api.get('/api/v1/warehouse-leds/mappings', { params })
      mappings.value = data
    } finally {
      loading.value = false
    }
  }

  async function createMapping(payload) {
    const { data } = await api.post('/api/v1/warehouse-leds/mappings', payload)
    mappings.value = [...mappings.value, data]
    return data
  }

  async function updateMapping(id, payload) {
    const { data } = await api.put(`/api/v1/warehouse-leds/mappings/${id}`, payload)
    mappings.value = mappings.value.map(m => m.id === id ? data : m)
    return data
  }

  async function deleteMapping(id) {
    await api.delete(`/api/v1/warehouse-leds/mappings/${id}`)
    mappings.value = mappings.value.filter(m => m.id !== id)
  }

  async function bulkCreateMappings(items) {
    const { data } = await api.post('/api/v1/warehouse-leds/mappings/bulk', { items })
    return data
  }

  async function highlightJob(jobId) {
    const { data } = await api.post(`/api/v1/warehouse-leds/highlight-job/${jobId}`)
    return data
  }

  async function locateDevice(deviceId) {
    const { data } = await api.post(`/api/v1/warehouse-leds/locate/${deviceId}`)
    return data
  }

  async function showReturnLocation(zoneId) {
    const { data } = await api.post(`/api/v1/warehouse-leds/return/${zoneId}`)
    return data
  }

  async function clearAll() {
    const { data } = await api.post('/api/v1/warehouse-leds/clear')
    return data
  }

  async function identifyAll() {
    const { data } = await api.post('/api/v1/warehouse-leds/identify')
    return data
  }

  async function fetchStatuses() {
    const { data } = await api.get('/api/v1/warehouse-leds/status')
    statuses.value = data
    return data
  }

  async function getEspHomeYaml(controllerId) {
    const { data } = await api.get(`/api/v1/warehouse-leds/esphome/${controllerId}.yaml`)
    return data
  }

  async function getEspHomeSecretsTemplate() {
    const { data } = await api.get('/api/v1/warehouse-leds/esphome/secrets-template')
    return data
  }

  return {
    controllers,
    mappings,
    statuses,
    loading,
    fetchControllers,
    createController,
    updateController,
    deleteController,
    fetchControllerZones,
    setControllerZones,
    fetchMappings,
    createMapping,
    updateMapping,
    deleteMapping,
    bulkCreateMappings,
    highlightJob,
    locateDevice,
    showReturnLocation,
    clearAll,
    identifyAll,
    fetchStatuses,
    getEspHomeYaml,
    getEspHomeSecretsTemplate,
  }
})
