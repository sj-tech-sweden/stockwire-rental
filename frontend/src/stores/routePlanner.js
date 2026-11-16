import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '../boot/axios'
import { isOnline, queueMutation, cacheSnapshot, readSnapshot } from '../services/offline/orbitSync'

export const useRoutePlannerStore = defineStore('routePlanner', () => {
  const vehicles = ref([])
  const routes = ref([])
  const currentRoute = ref(null)
  const loading = ref(false)

  // Mirror stores/inventory.js: persist/restore this store's collections so
  // they survive an offline reload (cacheSnapshot/readSnapshot from orbitSync).
  async function persistFetchAllSnapshot() {
    await cacheSnapshot('routePlanner.fetchAll', {
      vehicles: vehicles.value,
      routes: routes.value,
      currentRoute: currentRoute.value,
    })
  }

  async function restoreFetchAllSnapshot() {
    const cached = await readSnapshot('routePlanner.fetchAll')
    if (!cached || typeof cached !== 'object') return false
    vehicles.value = Array.isArray(cached.vehicles) ? cached.vehicles : vehicles.value
    routes.value = Array.isArray(cached.routes) ? cached.routes : routes.value
    currentRoute.value = cached.currentRoute ?? currentRoute.value
    return true
  }

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
    if (!isOnline()) {
      await queueMutation({ method: 'post', url: '/api/v1/route-planner/vehicles', data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.post('/api/v1/route-planner/vehicles', payload)
    vehicles.value.push(data)
    return data
  }

  async function updateVehicle(id, payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'put', url: `/api/v1/route-planner/vehicles/${id}`, data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.put(`/api/v1/route-planner/vehicles/${id}`, payload)
    const idx = vehicles.value.findIndex(v => v.id === id)
    if (idx >= 0) vehicles.value[idx] = data
    return data
  }

  async function deleteVehicle(id) {
    if (!isOnline()) {
      await queueMutation({ method: 'delete', url: `/api/v1/route-planner/vehicles/${id}` })
      await persistFetchAllSnapshot()
      return
    }
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
    if (!isOnline()) {
      await queueMutation({ method: 'post', url: '/api/v1/route-planner/routes', data: payload })
      await persistFetchAllSnapshot()
      return
    }
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
    if (!isOnline()) {
      await queueMutation({ method: 'put', url: `/api/v1/route-planner/routes/${id}`, data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.put(`/api/v1/route-planner/routes/${id}`, payload)
    currentRoute.value = data
    const idx = routes.value.findIndex(r => r.id === id)
    if (idx >= 0) routes.value[idx] = data
    return data
  }

  async function deleteRoute(id) {
    if (!isOnline()) {
      await queueMutation({ method: 'delete', url: `/api/v1/route-planner/routes/${id}` })
      await persistFetchAllSnapshot()
      return
    }
    await api.delete(`/api/v1/route-planner/routes/${id}`)
    routes.value = routes.value.filter(r => r.id !== id)
    if (currentRoute.value?.id === id) currentRoute.value = null
  }

  // ---- Route Vehicles (multi) ----

  async function assignVehicle(routeId, vehicleId, loadOrder = 0) {
    if (!isOnline()) {
      await queueMutation({ method: 'post', url: `/api/v1/route-planner/routes/${routeId}/vehicles`, data: { vehicle_id: vehicleId, load_order: loadOrder } })
      await persistFetchAllSnapshot()
      return
    }
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
    if (!isOnline()) {
      await queueMutation({ method: 'delete', url: `/api/v1/route-planner/routes/${routeId}/vehicles/${vehicleId}` })
      await persistFetchAllSnapshot()
      return
    }
    await api.delete(`/api/v1/route-planner/routes/${routeId}/vehicles/${vehicleId}`)
    await fetchRoute(routeId)
    const idx = routes.value.findIndex(r => r.id === routeId)
    if (idx >= 0 && currentRoute.value) routes.value[idx] = currentRoute.value
  }

  async function reorderVehicles(routeId, vehicleIds) {
    if (!isOnline()) {
      await queueMutation({ method: 'put', url: `/api/v1/route-planner/routes/${routeId}/vehicles/reorder`, data: { vehicle_ids: vehicleIds } })
      await persistFetchAllSnapshot()
      return
    }
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
    if (!isOnline()) {
      await queueMutation({ method: 'post', url: `/api/v1/route-planner/routes/${routeId}/stops`, data: { job_id: jobId } })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.post(`/api/v1/route-planner/routes/${routeId}/stops`, { job_id: jobId })
    currentRoute.value = data
    const idx = routes.value.findIndex(r => r.id === routeId)
    if (idx >= 0) routes.value[idx] = data
    return data
  }

  async function reorderStops(routeId, stopIds) {
    if (!isOnline()) {
      await queueMutation({ method: 'put', url: `/api/v1/route-planner/routes/${routeId}/stops/reorder`, data: { stop_ids: stopIds } })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.put(`/api/v1/route-planner/routes/${routeId}/stops/reorder`, { stop_ids: stopIds })
    currentRoute.value = data
    const idx = routes.value.findIndex(r => r.id === routeId)
    if (idx >= 0) routes.value[idx] = data
    return data
  }

  async function removeStop(routeId, stopId) {
    if (!isOnline()) {
      await queueMutation({ method: 'delete', url: `/api/v1/route-planner/routes/${routeId}/stops/${stopId}` })
      await persistFetchAllSnapshot()
      return
    }
    await api.delete(`/api/v1/route-planner/routes/${routeId}/stops/${stopId}`)
    await fetchRoute(routeId)
    const idx = routes.value.findIndex(r => r.id === routeId)
    if (idx >= 0 && currentRoute.value) routes.value[idx] = currentRoute.value
  }

  async function assignStopVehicle(routeId, stopId, vehicleId) {
    const params = vehicleId ? { vehicle_id: vehicleId } : {}
    if (!isOnline()) {
      await queueMutation({ method: 'put', url: `/api/v1/route-planner/routes/${routeId}/stops/${stopId}/vehicle`, data: null, params })
      await persistFetchAllSnapshot()
      return
    }
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

  async function getRouteDriveTimes(routeId, originAddress = null) {
    const params = {}
    if (originAddress) params.origin_address = originAddress
    const { data } = await api.get(`/api/v1/route-planner/routes/${routeId}/drive-times`, { params })
    return data
  }

  async function getRouteLocations(routeId, originAddress = null) {
    const params = {}
    if (originAddress) params.origin_address = originAddress
    const { data } = await api.get(`/api/v1/route-planner/routes/${routeId}/locations`, { params })
    return data
  }

  async function optimizeRoute(routeId, originAddress = null) {
    const params = {}
    if (originAddress) params.origin_address = originAddress
    if (!isOnline()) {
      await queueMutation({ method: 'post', url: `/api/v1/route-planner/routes/${routeId}/optimize`, data: null, params })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.post(`/api/v1/route-planner/routes/${routeId}/optimize`, null, { params })
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
    getRouteDriveTimes,
    getRouteLocations,
    optimizeRoute,
    persistFetchAllSnapshot,
    restoreFetchAllSnapshot,
  }
})
