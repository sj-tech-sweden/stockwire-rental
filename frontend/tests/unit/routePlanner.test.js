import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('../../src/boot/axios', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn()
  }
}))

import { api } from '../../src/boot/axios'
import { useRoutePlannerStore } from '../../src/stores/routePlanner'

describe('routePlanner store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  // ---- Vehicles ----

  describe('vehicles', () => {
    it('fetchVehicles sets vehicles list', async () => {
      const vehicles = [
        { id: 1, name: 'Truck 1', vehicle_type: 'truck' },
        { id: 2, name: 'Trailer 1', vehicle_type: 'trailer' }
      ]
      api.get.mockResolvedValue({ data: vehicles })
      const store = useRoutePlannerStore()
      await store.fetchVehicles()
      expect(store.vehicles).toHaveLength(2)
      expect(store.vehicles[0].name).toBe('Truck 1')
    })

    it('createVehicle adds to list and returns data', async () => {
      const newVehicle = { id: 3, name: 'Van 1', vehicle_type: 'van' }
      api.post.mockResolvedValue({ data: newVehicle })
      const store = useRoutePlannerStore()
      const result = await store.createVehicle({ name: 'Van 1', vehicle_type: 'van' })
      expect(result.name).toBe('Van 1')
      expect(store.vehicles).toHaveLength(1)
      expect(store.vehicles[0].id).toBe(3)
    })

    it('updateVehicle updates in-place', async () => {
      const store = useRoutePlannerStore()
      store.vehicles = [{ id: 1, name: 'Old', vehicle_type: 'truck' }]
      const updated = { id: 1, name: 'New', vehicle_type: 'truck' }
      api.put.mockResolvedValue({ data: updated })
      await store.updateVehicle(1, { name: 'New' })
      expect(store.vehicles[0].name).toBe('New')
    })

    it('deleteVehicle removes from list', async () => {
      const store = useRoutePlannerStore()
      store.vehicles = [
        { id: 1, name: 'V1' },
        { id: 2, name: 'V2' }
      ]
      api.delete.mockResolvedValue({})
      await store.deleteVehicle(1)
      expect(store.vehicles).toHaveLength(1)
      expect(store.vehicles[0].id).toBe(2)
    })

    it('sets loading during fetch', async () => {
      api.get.mockResolvedValue({ data: [] })
      const store = useRoutePlannerStore()
      expect(store.loading).toBe(false)
      const promise = store.fetchVehicles()
      expect(store.loading).toBe(true)
      await promise
      expect(store.loading).toBe(false)
    })
  })

  // ---- Routes ----

  describe('routes', () => {
    it('fetchRoutes sets routes list', async () => {
      const routes = [{ id: 1, name: 'Route 1', status: 'planned' }]
      api.get.mockResolvedValue({ data: routes })
      const store = useRoutePlannerStore()
      await store.fetchRoutes()
      expect(store.routes).toHaveLength(1)
      expect(store.routes[0].name).toBe('Route 1')
    })

    it('fetchRoutes with status filter passes params', async () => {
      api.get.mockResolvedValue({ data: [] })
      const store = useRoutePlannerStore()
      await store.fetchRoutes({ status: 'completed' })
      expect(api.get).toHaveBeenCalledWith('/api/v1/route-planner/routes', { params: { status: 'completed' } })
    })

    it('createRoute adds to front of list', async () => {
      const store = useRoutePlannerStore()
      store.routes = [{ id: 1, name: 'Existing' }]
      const newRoute = { id: 2, name: 'New Route' }
      api.post.mockResolvedValue({ data: newRoute })
      const result = await store.createRoute({ name: 'New Route' })
      expect(result.name).toBe('New Route')
      expect(store.routes).toHaveLength(2)
      expect(store.routes[0].name).toBe('New Route')
    })

    it('fetchRoute sets currentRoute', async () => {
      const route = { id: 1, name: 'Route 1', stops: [], vehicles: [] }
      api.get.mockResolvedValue({ data: route })
      const store = useRoutePlannerStore()
      await store.fetchRoute(1)
      expect(store.currentRoute).toEqual(route)
    })

    it('updateRoute updates currentRoute and routes list', async () => {
      const store = useRoutePlannerStore()
      store.routes = [{ id: 1, name: 'Old' }]
      store.currentRoute = { id: 1, name: 'Old' }
      const updated = { id: 1, name: 'Updated' }
      api.put.mockResolvedValue({ data: updated })
      await store.updateRoute(1, { name: 'Updated' })
      expect(store.currentRoute.name).toBe('Updated')
      expect(store.routes[0].name).toBe('Updated')
    })

    it('deleteRoute removes from list and clears currentRoute', async () => {
      const store = useRoutePlannerStore()
      store.routes = [{ id: 1 }, { id: 2 }]
      store.currentRoute = { id: 1 }
      api.delete.mockResolvedValue({})
      await store.deleteRoute(1)
      expect(store.routes).toHaveLength(1)
      expect(store.routes[0].id).toBe(2)
      expect(store.currentRoute).toBeNull()
    })

    it('deleteRoute does not clear currentRoute if different id', async () => {
      const store = useRoutePlannerStore()
      store.routes = [{ id: 1 }, { id: 2 }]
      store.currentRoute = { id: 2 }
      api.delete.mockResolvedValue({})
      await store.deleteRoute(1)
      expect(store.currentRoute?.id).toBe(2)
    })
  })

  // ---- Route Vehicles (multi) ----

  describe('route vehicles', () => {
    it('assignVehicle adds vehicle to route', async () => {
      const store = useRoutePlannerStore()
      store.currentRoute = { id: 1, vehicles: [] }
      const updated = { id: 1, vehicles: [{ vehicle_id: 5, vehicle_name: 'Truck' }] }
      api.post.mockResolvedValue({ data: updated })
      await store.assignVehicle(1, 5, 0)
      expect(store.currentRoute.vehicles).toHaveLength(1)
    })

    it('removeVehicle fetches updated route', async () => {
      const store = useRoutePlannerStore()
      store.currentRoute = { id: 1, vehicles: [{ vehicle_id: 5 }] }
      api.delete.mockResolvedValue({})
      api.get.mockResolvedValue({ data: { id: 1, vehicles: [] } })
      await store.removeVehicle(1, 5)
      expect(store.currentRoute.vehicles).toHaveLength(0)
    })

    it('reorderVehicles updates currentRoute', async () => {
      const store = useRoutePlannerStore()
      store.currentRoute = { id: 1, vehicles: [{ vehicle_id: 1 }, { vehicle_id: 2 }] }
      const reordered = { id: 1, vehicles: [{ vehicle_id: 2 }, { vehicle_id: 1 }] }
      api.put.mockResolvedValue({ data: reordered })
      await store.reorderVehicles(1, [2, 1])
      expect(store.currentRoute.vehicles[0].vehicle_id).toBe(2)
    })
  })

  // ---- Stops ----

  describe('stops', () => {
    it('addStop adds job to route', async () => {
      const store = useRoutePlannerStore()
      store.currentRoute = { id: 1, stops: [] }
      const updated = { id: 1, stops: [{ id: 10, job_id: 5 }] }
      api.post.mockResolvedValue({ data: updated })
      await store.addStop(1, 5)
      expect(store.currentRoute.stops).toHaveLength(1)
      expect(store.currentRoute.stops[0].job_id).toBe(5)
    })

    it('reorderStops updates currentRoute', async () => {
      const store = useRoutePlannerStore()
      store.currentRoute = { id: 1, stops: [{ id: 10 }, { id: 20 }] }
      const reordered = { id: 1, stops: [{ id: 20 }, { id: 10 }] }
      api.put.mockResolvedValue({ data: reordered })
      await store.reorderStops(1, [20, 10])
      expect(store.currentRoute.stops[0].id).toBe(20)
    })

    it('removeStop fetches updated route', async () => {
      const store = useRoutePlannerStore()
      store.currentRoute = { id: 1, stops: [{ id: 10 }, { id: 20 }] }
      api.delete.mockResolvedValue({})
      api.get.mockResolvedValue({ data: { id: 1, stops: [{ id: 20 }] } })
      await store.removeStop(1, 10)
      expect(store.currentRoute.stops).toHaveLength(1)
    })

    it('assignStopVehicle updates currentRoute', async () => {
      const store = useRoutePlannerStore()
      store.currentRoute = {
        id: 1,
        stops: [{ id: 10, vehicle_id: null, vehicle: null }]
      }
      const updated = {
        id: 1,
        stops: [{ id: 10, vehicle_id: 3, vehicle: { id: 3, name: 'V1' } }]
      }
      api.put.mockResolvedValue({ data: updated })
      await store.assignStopVehicle(1, 10, 3)
      expect(store.currentRoute.stops[0].vehicle_id).toBe(3)
    })

    it('assignStopVehicle with null clears vehicle', async () => {
      const store = useRoutePlannerStore()
      store.currentRoute = {
        id: 1,
        stops: [{ id: 10, vehicle_id: 3 }]
      }
      const updated = {
        id: 1,
        stops: [{ id: 10, vehicle_id: null }]
      }
      api.put.mockResolvedValue({ data: updated })
      await store.assignStopVehicle(1, 10, null)
      expect(store.currentRoute.stops[0].vehicle_id).toBeNull()
    })
  })

  // ---- Planning ----

  describe('planning', () => {
    it('suggestVehicles returns suggestion list', async () => {
      const suggestions = [
        { suggestion_id: 's1', label: 'Truck 1', is_combo: false, fits: true }
      ]
      api.post.mockResolvedValue({ data: suggestions })
      const store = useRoutePlannerStore()
      const result = await store.suggestVehicles([1, 2])
      expect(result).toHaveLength(1)
      expect(result[0].label).toBe('Truck 1')
    })

    it('suggestVehicles includes combo suggestions', async () => {
      const suggestions = [
        { suggestion_id: 'single-1', label: 'Truck', is_combo: false },
        { suggestion_id: 'combo-1-2', label: 'Truck + Trailer', is_combo: true }
      ]
      api.post.mockResolvedValue({ data: suggestions })
      const store = useRoutePlannerStore()
      const result = await store.suggestVehicles([1])
      const combos = result.filter(s => s.is_combo)
      expect(combos).toHaveLength(1)
    })

    it('exportGoogleMaps returns URL', async () => {
      api.post.mockResolvedValue({ data: { url: 'https://google.com/maps?...' } })
      const store = useRoutePlannerStore()
      const result = await store.exportGoogleMaps(1)
      expect(result.url).toContain('google.com/maps')
    })

    it('getPackingList returns packing data', async () => {
      const packing = {
        route_name: 'Route 1',
        stops: [{ stop_order: 1, job_code: 'JOB-1' }],
        total_weight_kg: 10,
        total_volume_m3: 0.5
      }
      api.get.mockResolvedValue({ data: packing })
      const store = useRoutePlannerStore()
      const result = await store.getPackingList(1)
      expect(result.route_name).toBe('Route 1')
      expect(result.stops).toHaveLength(1)
    })
  })

  // ---- Edge cases ----

  describe('edge cases', () => {
    it('fetchRoutes resets loading even on error', async () => {
      api.get.mockRejectedValue(new Error('Network error'))
      const store = useRoutePlannerStore()
      await expect(store.fetchRoutes()).rejects.toThrow()
      expect(store.loading).toBe(false)
    })

    it('fetchVehicles resets loading even on error', async () => {
      api.get.mockRejectedValue(new Error('Network error'))
      const store = useRoutePlannerStore()
      await expect(store.fetchVehicles()).rejects.toThrow()
      expect(store.loading).toBe(false)
    })

    it('fetchRoute resets loading even on error', async () => {
      api.get.mockRejectedValue(new Error('Network error'))
      const store = useRoutePlannerStore()
      await expect(store.fetchRoute(1)).rejects.toThrow()
      expect(store.loading).toBe(false)
    })

    it('updateVehicle with non-existent id does not crash', async () => {
      const store = useRoutePlannerStore()
      store.vehicles = []
      api.put.mockResolvedValue({ data: { id: 999, name: 'X' } })
      const result = await store.updateVehicle(999, { name: 'X' })
      expect(result).toBeTruthy()
      expect(store.vehicles).toHaveLength(0)
    })

    it('deleteRoute with non-matching currentRoute does not clear it', async () => {
      const store = useRoutePlannerStore()
      store.routes = [{ id: 1 }, { id: 2 }]
      store.currentRoute = { id: 3 }
      api.delete.mockResolvedValue({})
      await store.deleteRoute(1)
      expect(store.currentRoute.id).toBe(3)
    })
  })
})
