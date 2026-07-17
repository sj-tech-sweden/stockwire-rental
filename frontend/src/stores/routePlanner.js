import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '../boot/axios'

export const useRoutePlannerStore = defineStore('routePlanner', () => {
  const vehicles = ref([])
  const routes = ref([])
  const currentRoute = ref(null)
  const loading = ref(false)

  // ---- Vehicles ----

  async function fetchVehicles() {
    loading.value = true
    try {
      const { data } = await api.get('/api/v1/route-planner/vehicles')
      vehicles.value = data
    } finally {
      loading.value = false
    }
  }

  async function createVehicle(payload) {
    const { data } = await api.post('/api/v1/route-planner/vehicles', payload)
    vehicles.value.push(data)
    return data
  }

  async function updateVehicle(id, payload) {
    const { data } = await api.put(`/api/v1/route-planner/vehicles/${id}`, payload)
    const idx = vehicles.value.findIndex(v => v.id === id)
    if (idx >= 0) vehicles.value[idx] = data
    return data
  }

  async function deleteVehicle(id) {
    await api.delete(`/api/v1/route-planner/vehicles/${id}`)
    vehicles.value = vehicles.value.filter(v => v.id !== id)
  }

  // ---- Routes ----

  async function fetchRoutes(params = {}) {
    loading.value = true
    try {
      const { data } = await api.get('/api/v1/route-planner/routes', { params })
      routes.value = data
    } finally {
      loading.value = false
    }
  }

  async function createRoute(payload) {
    const { data } = await api.post('/api/v1/route-planner/routes', payload)
    routes.value.unshift(data)
    return data
  }

  async function fetchRoute(id) {
    loading.value = true
    try {
      const { data } = await api.get(`/api/v1/route-planner/routes/${id}`)
      currentRoute.value = data
      return data
    } finally {
      loading.value = false
    }
  }

  async function updateRoute(id, payload) {
    const { data } = await api.put(`/api/v1/route-planner/routes/${id}`, payload)
    currentRoute.value = data
    const idx = routes.value.findIndex(r => r.id === id)
    if (idx >= 0) routes.value[idx] = data
    return data
  }

  async function deleteRoute(id) {
    await api.delete(`/api/v1/route-planner/routes/${id}`)
    routes.value = routes.value.filter(r => r.id !== id)
    if (currentRoute.value?.id === id) currentRoute.value = null
  }

  // ---- Route Vehicles (multi) ----

  async function assignVehicle(routeId, vehicleId, loadOrder = 0) {
    const { data } = await api.post(`/api/v1/route-planner/routes/${routeId}/vehicles`, {
      vehicle_id: vehicleId,
      load_order: loadOrder,
    })
    currentRoute.value = data
    const idx = routes.value.findIndex(r => r.id === routeId)
    if (idx >= 0) routes.value[idx] = data
    return data
  }

  async function removeVehicle(routeId, vehicleId) {
    await api.delete(`/api/v1/route-planner/routes/${routeId}/vehicles/${vehicleId}`)
    await fetchRoute(routeId)
    const idx = routes.value.findIndex(r => r.id === routeId)
    if (idx >= 0 && currentRoute.value) routes.value[idx] = currentRoute.value
  }

  async function reorderVehicles(routeId, vehicleIds) {
    const { data } = await api.put(`/api/v1/route-planner/routes/${routeId}/vehicles/reorder`, {
      vehicle_ids: vehicleIds,
    })
    currentRoute.value = data
    const idx = routes.value.findIndex(r => r.id === routeId)
    if (idx >= 0) routes.value[idx] = data
    return data
  }

  // ---- Stops ----

  async function addStop(routeId, jobId) {
    const { data } = await api.post(`/api/v1/route-planner/routes/${routeId}/stops`, { job_id: jobId })
    currentRoute.value = data
    const idx = routes.value.findIndex(r => r.id === routeId)
    if (idx >= 0) routes.value[idx] = data
    return data
  }

  async function reorderStops(routeId, stopIds) {
    const { data } = await api.put(`/api/v1/route-planner/routes/${routeId}/stops/reorder`, { stop_ids: stopIds })
    currentRoute.value = data
    const idx = routes.value.findIndex(r => r.id === routeId)
    if (idx >= 0) routes.value[idx] = data
    return data
  }

  async function removeStop(routeId, stopId) {
    await api.delete(`/api/v1/route-planner/routes/${routeId}/stops/${stopId}`)
    await fetchRoute(routeId)
    const idx = routes.value.findIndex(r => r.id === routeId)
    if (idx >= 0 && currentRoute.value) routes.value[idx] = currentRoute.value
  }

  async function assignStopVehicle(routeId, stopId, vehicleId) {
    const params = vehicleId ? { vehicle_id: vehicleId } : {}
    const { data } = await api.put(`/api/v1/route-planner/routes/${routeId}/stops/${stopId}/vehicle`, null, { params })
    currentRoute.value = data
    const idx = routes.value.findIndex(r => r.id === routeId)
    if (idx >= 0) routes.value[idx] = data
    return data
  }

  // ---- Planning ----

  async function suggestVehicles(jobIds) {
    const { data } = await api.post('/api/v1/route-planner/suggest-vehicles', { job_ids: jobIds })
    return data
  }

  async function exportGoogleMaps(routeId, originAddress = null) {
    const { data } = await api.post('/api/v1/route-planner/export-google-maps', {
      route_id: routeId,
      origin_address: originAddress,
    })
    return data
  }

  async function getPackingList(routeId) {
    const { data } = await api.get(`/api/v1/route-planner/routes/${routeId}/packing-list`)
    return data
  }

  return {
    vehicles,
    routes,
    currentRoute,
    loading,
    fetchVehicles,
    createVehicle,
    updateVehicle,
    deleteVehicle,
    fetchRoutes,
    createRoute,
    fetchRoute,
    updateRoute,
    deleteRoute,
    assignVehicle,
    removeVehicle,
    reorderVehicles,
    assignStopVehicle,
    addStop,
    reorderStops,
    removeStop,
    suggestVehicles,
    exportGoogleMaps,
    getPackingList,
  }
})
