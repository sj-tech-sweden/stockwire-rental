import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '../boot/axios'
import {
  cacheSnapshot,
  isOnline,
  queueMutation,
  readSnapshot,
} from '../services/offline/orbitSync'

export const DEVICE_STATUSES = [
  { label: 'Available', value: 'available', color: 'positive' },
  { label: 'Reserved', value: 'reserved', color: 'warning' },
  { label: 'In Use', value: 'in_use', color: 'info' },
  { label: 'Maintenance', value: 'maintenance', color: 'negative' },
]

export const useInventoryStore = defineStore('inventory', () => {
  const products = ref([])
  const devices = ref([])
  const zones = ref([])
  const zoneTree = ref([])
  const maintenances = ref([])
  const schedules = ref([])
  const auditLogs = ref([])
  const checkedOutDevices = ref([])
  const locationTypes = ref(['rack', 'shelf', 'bin', 'pallet', 'stage', 'truck', 'warehouse', 'workshop'])
  const categories = ref([])
  const categoryTree = ref([])
  const loading = ref(false)
  const fetchSource = ref('none')

  async function persistFetchAllSnapshot() {
    await cacheSnapshot('inventory.fetchAll', {
      products: products.value,
      devices: devices.value,
      zones: zones.value,
      zoneTree: zoneTree.value,
      categories: categories.value,
      categoryTree: categoryTree.value,
      maintenances: maintenances.value,
      schedules: schedules.value,
      locationTypes: locationTypes.value,
    })
  }

  async function restoreFetchAllSnapshot() {
    const cached = await readSnapshot('inventory.fetchAll')
    if (!cached || typeof cached !== 'object') {
      return false
    }
    products.value = Array.isArray(cached.products) ? cached.products : []
    devices.value = Array.isArray(cached.devices) ? cached.devices : []
    zones.value = Array.isArray(cached.zones) ? cached.zones : []
    zoneTree.value = Array.isArray(cached.zoneTree) ? cached.zoneTree : []
    categories.value = Array.isArray(cached.categories) ? cached.categories : []
    categoryTree.value = Array.isArray(cached.categoryTree) ? cached.categoryTree : []
    maintenances.value = Array.isArray(cached.maintenances) ? cached.maintenances : []
    schedules.value = Array.isArray(cached.schedules) ? cached.schedules : []
    locationTypes.value = Array.isArray(cached.locationTypes) && cached.locationTypes.length
      ? cached.locationTypes
      : locationTypes.value
    return true
  }

  async function fetchAll() {
    loading.value = true
    try {
      const [productsRes, devicesRes, zonesRes, zoneTreeRes, categoriesRes, categoryTreeRes, locationTypesRes, maintenanceRes, schedulesRes] = await Promise.all([
        api.get('/api/v1/inventory/products'),
        api.get('/api/v1/inventory/devices'),
        api.get('/api/v1/inventory/zones'),
        api.get('/api/v1/inventory/zones/tree'),
        api.get('/api/v1/inventory/categories'),
        api.get('/api/v1/inventory/categories/tree'),
        api.get('/api/v1/settings/location-types'),
        api.get('/api/v1/inventory/maintenance'),
        api.get('/api/v1/inventory/maintenance-schedules'),
      ])
      const productsData = Array.isArray(productsRes?.data) ? productsRes.data : []
      const devicesData = Array.isArray(devicesRes?.data) ? devicesRes.data : []
      const zonesData = Array.isArray(zonesRes?.data) ? zonesRes.data : []
      const zoneTreeData = Array.isArray(zoneTreeRes?.data) ? zoneTreeRes.data : []
      const categoriesData = Array.isArray(categoriesRes?.data) ? categoriesRes.data : []
      const categoryTreeData = Array.isArray(categoryTreeRes?.data) ? categoryTreeRes.data : []
      const locationTypesData = locationTypesRes?.data
      const maintenanceData = Array.isArray(maintenanceRes?.data) ? maintenanceRes.data : []
      const schedulesData = Array.isArray(schedulesRes?.data) ? schedulesRes.data : []
      products.value = productsData
      devices.value = devicesData
      zones.value = zonesData
      zoneTree.value = zoneTreeData.length ? zoneTreeData : zonesData
      categories.value = categoriesData
      categoryTree.value = categoryTreeData.length ? categoryTreeData : categoriesData
      maintenances.value = maintenanceData
      schedules.value = schedulesData
      if (Array.isArray(locationTypesData?.options) && locationTypesData.options.length) {
        locationTypes.value = locationTypesData.options
      }
      await persistFetchAllSnapshot()
      fetchSource.value = 'live'
    } catch (error) {
      const restored = await restoreFetchAllSnapshot()
      if (restored) {
        fetchSource.value = 'snapshot'
        return
      }
      throw error
    } finally {
      loading.value = false
    }
  }

  async function fetchCategories() {
    const [categoriesRes, categoryTreeRes] = await Promise.all([
      api.get('/api/v1/inventory/categories'),
      api.get('/api/v1/inventory/categories/tree'),
    ])
    const categoriesData = Array.isArray(categoriesRes?.data) ? categoriesRes.data : []
    const categoryTreeData = Array.isArray(categoryTreeRes?.data) ? categoryTreeRes.data : []
    categories.value = categoriesData
    categoryTree.value = categoryTreeData.length ? categoryTreeData : categoriesData
    await persistFetchAllSnapshot()
    return categories.value
  }

  async function prefillCategories() {
    await api.post('/api/v1/inventory/categories/prefill')
    await fetchCategories()
  }

  async function createCategory(payload) {
    if (!isOnline()) {
      const optimistic = { id: -Date.now(), ...payload, _offline_queued: true }
      categories.value = [...categories.value, optimistic]
      categoryTree.value = [...categories.value]
      await queueMutation({ method: 'post', url: '/api/v1/inventory/categories', data: payload })
      await persistFetchAllSnapshot()
      return optimistic
    }
    const { data } = await api.post('/api/v1/inventory/categories', payload)
    await fetchCategories()
    return data
  }

  async function updateCategory(id, payload) {
    if (!isOnline()) {
      categories.value = categories.value.map(item => (item.id === id ? { ...item, ...payload, _offline_queued: true } : item))
      categoryTree.value = [...categories.value]
      await queueMutation({ method: 'put', url: `/api/v1/inventory/categories/${id}`, data: payload })
      await persistFetchAllSnapshot()
      return categories.value.find(item => item.id === id) || { id, ...payload, _offline_queued: true }
    }
    const { data } = await api.put(`/api/v1/inventory/categories/${id}`, payload)
    await fetchCategories()
    return data
  }

  async function deleteCategory(id) {
    await api.delete(`/api/v1/inventory/categories/${id}`)
    await fetchCategories()
  }

  async function moveCategory(id, payload) {
    const { data } = await api.post(`/api/v1/inventory/categories/${id}/move`, payload)
    await fetchCategories()
    return data
  }

  async function createProduct(payload) {
    if (!isOnline()) {
      const tempId = -Date.now()
      const optimistic = { id: tempId, ...payload, _offline_queued: true }
      products.value = [...products.value, optimistic]
      await queueMutation({ method: 'post', url: '/api/v1/inventory/products', data: payload, clientTempId: tempId })
      await persistFetchAllSnapshot()
      return optimistic
    }
    const { data } = await api.post('/api/v1/inventory/products', payload)
    products.value = [...products.value, data]
    await persistFetchAllSnapshot()
    return data
  }

  async function updateProduct(id, payload) {
    if (!isOnline()) {
      products.value = products.value.map(product => (product.id === id ? { ...product, ...payload, _offline_queued: true } : product))
      await queueMutation({ method: 'put', url: `/api/v1/inventory/products/${id}`, data: payload })
      await persistFetchAllSnapshot()
      return products.value.find(product => product.id === id) || { id, ...payload, _offline_queued: true }
    }
    const { data } = await api.put(`/api/v1/inventory/products/${id}`, payload)
    products.value = products.value.map(product => (product.id === id ? data : product))
    await persistFetchAllSnapshot()
    return data
  }

  async function bulkUpdateProducts(ids, patch) {
    const { data } = await api.post('/api/v1/inventory/products/bulk-update', { ids, patch })
    await fetchAll()
    return data
  }

  async function bulkDeleteProducts(ids, options = {}) {
    const { data } = await api.post('/api/v1/inventory/products/bulk-delete', { ids }, {
      params: {
        delete_linked_devices: !!options.deleteLinkedDevices,
      },
    })
    await fetchAll()
    return data
  }

  async function fetchProductAccessories(productId) {
    const { data } = await api.get(`/api/v1/inventory/products/${productId}/accessories`)
    return Array.isArray(data) ? data : []
  }

  async function fetchProductComponents(productId) {
    const { data } = await api.get(`/api/v1/inventory/products/${productId}/components`)
    return Array.isArray(data) ? data : []
  }

  async function updateProductComponents(productId, items) {
    if (!isOnline()) {
      products.value = products.value.map(product => (
        product.id === productId
          ? { ...product, components: Array.isArray(items) ? items : [], _offline_queued: true }
          : product
      ))
      if (Number(productId) > 0) {
        await queueMutation({ method: 'put', url: `/api/v1/inventory/products/${productId}/components`, data: { items } })
      }
      await persistFetchAllSnapshot()
      return Array.isArray(items) ? items : []
    }
    const { data } = await api.put(`/api/v1/inventory/products/${productId}/components`, { items })
    await fetchAll()
    return Array.isArray(data) ? data : []
  }

  async function updateProductAccessories(productId, items) {
    if (!isOnline()) {
      products.value = products.value.map(product => (
        product.id === productId
          ? { ...product, accessories: Array.isArray(items) ? items : [], _offline_queued: true }
          : product
      ))
      if (Number(productId) > 0) {
        await queueMutation({ method: 'put', url: `/api/v1/inventory/products/${productId}/accessories`, data: { items } })
      }
      await persistFetchAllSnapshot()
      return Array.isArray(items) ? items : []
    }
    const { data } = await api.put(`/api/v1/inventory/products/${productId}/accessories`, { items })
    await fetchAll()
    return Array.isArray(data) ? data : []
  }

  async function createDevicesForProduct(productId, payload) {
    const hasTempProductId = Number(productId) < 0
    if (!isOnline() || hasTempProductId) {
      const count = Math.max(Number(payload?.quantity || 1), 1)
      const selectedProduct = (products.value || []).find(item => item.id === productId) || null
      const normalizedPrefix = String(payload?.asset_tag_prefix || selectedProduct?.sku || 'ASSET').trim().toUpperCase().replace(/-+$/, '') || 'ASSET'
      const nextAssetTagNumber = payload?.auto_generate === false
        ? 0
        : getNextAssetTagNumberForPrefix(normalizedPrefix)
      const optimisticRows = Array.from({ length: count }).map((_, index) => ({
        id: -(Date.now() + index),
        product_id: productId,
        asset_tag: payload?.auto_generate === false
          ? (payload?.asset_tag || `OFFLINE-${Math.abs(productId)}-${index + 1}`)
          : `${normalizedPrefix}-${String(nextAssetTagNumber + index).padStart(3, '0')}`,
        status: payload?.status || 'available',
        condition: payload?.condition || 'good',
        location_zone_id: payload?.location_zone_id ?? null,
        _offline_queued: true,
      }))
      devices.value = [...devices.value, ...optimisticRows]
      await queueMutation({
        method: 'post',
        url: `/api/v1/inventory/products/${productId}/devices`,
        data: payload,
        meta: {
          tempProductId: hasTempProductId ? Number(productId) : null,
        },
      })
      await persistFetchAllSnapshot()
      return optimisticRows
    }
    const { data } = await api.post(`/api/v1/inventory/products/${productId}/devices`, payload)
    await fetchAll()
    return data
  }

  function getNextAssetTagNumberForPrefix(prefix) {
    const normalizedPrefix = String(prefix || '').trim().toUpperCase().replace(/-+$/, '') || 'ASSET'
    const matcher = new RegExp(`^${normalizedPrefix.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}-(\\d+)$`, 'i')
    let maxNumber = 0

    for (const device of devices.value || []) {
      const tag = String(device?.asset_tag || '').trim()
      if (!tag) continue
      const matched = tag.match(matcher)
      if (!matched) continue
      maxNumber = Math.max(maxNumber, Number(matched[1] || 0))
    }

    return maxNumber + 1
  }

  async function createDevice(payload) {
    const hasTempProductId = Number(payload?.product_id) < 0
    if (!isOnline() || hasTempProductId) {
      const optimistic = {
        id: -Date.now(),
        ...payload,
        _offline_queued: true,
      }
      devices.value = [...devices.value, optimistic]
      await queueMutation({
        method: 'post',
        url: '/api/v1/inventory/devices',
        data: payload,
        meta: {
          tempProductId: hasTempProductId ? Number(payload?.product_id) : null,
        },
      })
      await persistFetchAllSnapshot()
      return optimistic
    }
    const { data } = await api.post('/api/v1/inventory/devices', payload)
    devices.value = [...devices.value, data]
    await persistFetchAllSnapshot()
    return data
  }

  async function updateDevice(id, payload) {
    if (!isOnline()) {
      devices.value = devices.value.map(device => (device.id === id ? { ...device, ...payload, _offline_queued: true } : device))
      await queueMutation({ method: 'put', url: `/api/v1/inventory/devices/${id}`, data: payload })
      await persistFetchAllSnapshot()
      return devices.value.find(device => device.id === id) || { id, ...payload, _offline_queued: true }
    }
    const { data } = await api.put(`/api/v1/inventory/devices/${id}`, payload)
    devices.value = devices.value.map(device => (device.id === id ? data : device))
    await persistFetchAllSnapshot()
    return data
  }

  async function bulkUpdateDevices(ids, patch) {
    const { data } = await api.post('/api/v1/inventory/devices/bulk-update', { ids, patch })
    await fetchAll()
    return data
  }

  async function bulkDeleteDevices(ids) {
    const { data } = await api.post('/api/v1/inventory/devices/bulk-delete', { ids })
    await fetchAll()
    return data
  }

  async function fetchZones() {
    const [zonesRes, zoneTreeRes] = await Promise.all([
      api.get('/api/v1/inventory/zones'),
      api.get('/api/v1/inventory/zones/tree'),
    ])
    const zonesData = Array.isArray(zonesRes?.data) ? zonesRes.data : []
    const zoneTreeData = Array.isArray(zoneTreeRes?.data) ? zoneTreeRes.data : []
    zones.value = zonesData
    zoneTree.value = zoneTreeData.length ? zoneTreeData : zonesData
    await persistFetchAllSnapshot()
    return zones.value
  }

  async function fetchMaintenance(status = null) {
    const query = status ? { params: { status } } : undefined
    const response = await api.get('/api/v1/inventory/maintenance', query)
    maintenances.value = response?.data || []
    await persistFetchAllSnapshot()
    return maintenances.value
  }

  async function fetchMaintenanceSchedules() {
    const response = await api.get('/api/v1/inventory/maintenance-schedules')
    schedules.value = Array.isArray(response?.data) ? response.data : []
    await persistFetchAllSnapshot()
    return schedules.value
  }

  async function createMaintenance(payload) {
    if (!isOnline()) {
      const optimistic = { id: -Date.now(), ...payload, _offline_queued: true }
      maintenances.value = [...maintenances.value, optimistic]
      await queueMutation({ method: 'post', url: '/api/v1/inventory/maintenance', data: payload })
      await persistFetchAllSnapshot()
      return optimistic
    }
    const { data } = await api.post('/api/v1/inventory/maintenance', payload)
    maintenances.value = [...maintenances.value, data]
    await persistFetchAllSnapshot()
    return data
  }

  async function bulkScheduleMaintenance(payload) {
    if (!isOnline()) {
      const count = Math.max(
        Number(payload?.device_ids?.length || 0),
        Number(payload?.product_ids?.length || 0),
        1
      )
      const optimisticRows = Array.from({ length: count }).map((_, index) => ({
        id: -(Date.now() + index),
        ...payload,
        _offline_queued: true,
      }))
      maintenances.value = [...maintenances.value, ...optimisticRows]
      await queueMutation({ method: 'post', url: '/api/v1/inventory/maintenance/bulk-schedule', data: payload })
      await persistFetchAllSnapshot()
      return optimisticRows
    }
    const { data } = await api.post('/api/v1/inventory/maintenance/bulk-schedule', payload)
    await fetchMaintenance()
    await fetchMaintenanceSchedules()
    return data
  }

  async function updateMaintenance(id, payload) {
    if (!isOnline()) {
      maintenances.value = maintenances.value.map(item => (item.id === id ? { ...item, ...payload, _offline_queued: true } : item))
      await queueMutation({ method: 'put', url: `/api/v1/inventory/maintenance/${id}`, data: payload })
      await persistFetchAllSnapshot()
      return maintenances.value.find(item => item.id === id) || { id, ...payload, _offline_queued: true }
    }
    const { data } = await api.put(`/api/v1/inventory/maintenance/${id}`, payload)
    maintenances.value = maintenances.value.map(item => (item.id === id ? data : item))
    await persistFetchAllSnapshot()
    return data
  }

  async function completeMaintenance(id, payload = {}) {
    if (!isOnline()) {
      maintenances.value = maintenances.value.map(item => (
        item.id === id
          ? { ...item, ...payload, status: 'completed', _offline_queued: true }
          : item
      ))
      await queueMutation({ method: 'post', url: `/api/v1/inventory/maintenance/${id}/complete`, data: payload })
      await persistFetchAllSnapshot()
      return maintenances.value.find(item => item.id === id) || { id, ...payload, status: 'completed', _offline_queued: true }
    }
    const { data } = await api.post(`/api/v1/inventory/maintenance/${id}/complete`, payload)
    maintenances.value = maintenances.value.map(item => (item.id === id ? data : item))
    await persistFetchAllSnapshot()
    return data
  }

  async function bulkUpdateMaintenance(ids, patch) {
    const { data } = await api.post('/api/v1/inventory/maintenance/bulk-update', { ids, patch })
    await fetchMaintenance()
    return data
  }

  async function bulkDeleteMaintenance(ids) {
    const { data } = await api.post('/api/v1/inventory/maintenance/bulk-delete', { ids })
    await fetchMaintenance()
    return data
  }

  async function bulkUpdateMaintenanceSchedules(ids, patch) {
    const { data } = await api.post('/api/v1/inventory/maintenance-schedules/bulk-update', { ids, patch })
    await fetchMaintenance()
    await fetchMaintenanceSchedules()
    return data
  }

  async function bulkDeleteMaintenanceSchedules(ids) {
    const { data } = await api.post('/api/v1/inventory/maintenance-schedules/bulk-delete', { ids })
    await fetchMaintenance()
    await fetchMaintenanceSchedules()
    return data
  }

  async function fetchMaintenanceSchedule(scheduleId) {
    const { data } = await api.get(`/api/v1/inventory/maintenance-schedules/${scheduleId}`)
    return data
  }

  async function updateMaintenanceSchedule(scheduleId, payload) {
    const { data } = await api.put(`/api/v1/inventory/maintenance-schedules/${scheduleId}`, payload)
    await fetchMaintenance()
    await fetchMaintenanceSchedules()
    await persistFetchAllSnapshot()
    return data
  }

  async function processScan(payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'post', url: '/api/v1/inventory/scan/process', data: payload })
      return {
        success: true,
        queued: true,
        action: payload.action || 'lookup',
        message: 'Offline: scan queued and will sync when connection returns.',
        asset_tag: payload.scan_code,
      }
    }
    const { data } = await api.post('/api/v1/inventory/scan/process', payload)
    await fetchAll()
    await fetchCheckedOutDevices()
    await fetchAuditLogs(100)
    return data
  }

  async function fetchCheckedOutDevices(jobCode = null) {
    const query = jobCode ? { params: { job_code: jobCode } } : undefined
    const { data } = await api.get('/api/v1/inventory/checked-out-devices', query)
    checkedOutDevices.value = Array.isArray(data) ? data : []
    return checkedOutDevices.value
  }

  async function fetchAuditLogs(limit = 100) {
    const { data } = await api.get('/api/v1/inventory/audit', { params: { limit } })
    auditLogs.value = Array.isArray(data) ? data : []
    return auditLogs.value
  }

  async function fetchDeviceAuditLogs(deviceId, limit = 200) {
    const { data } = await api.get('/api/v1/inventory/audit', { params: { limit, device_id: deviceId } })
    return Array.isArray(data) ? data : []
  }

  async function createZone(payload) {
    if (!isOnline()) {
      const optimistic = { id: -Date.now(), ...payload, _offline_queued: true }
      zones.value = [...zones.value, optimistic]
      zoneTree.value = [...zones.value]
      await queueMutation({ method: 'post', url: '/api/v1/inventory/zones', data: payload })
      await persistFetchAllSnapshot()
      return optimistic
    }
    const { data } = await api.post('/api/v1/inventory/zones', payload)
    await fetchZones()
    return data
  }

  async function createZonesBulk(parentId, items) {
    // items: array of ZoneCreate-like objects (name, code, zone_type, etc.)
    if (!isOnline()) {
      // optimistic: add temporary entries
      const optimisticRows = (items || []).map((item, idx) => ({ id: -(Date.now() + idx), parent_id: parentId, ...item, _offline_queued: true }))
      zones.value = [...zones.value, ...optimisticRows]
      zoneTree.value = [...zones.value]
      await queueMutation({ method: 'post', url: `/api/v1/inventory/locations/${parentId}/subzones/bulk`, data: items })
      await persistFetchAllSnapshot()
      return optimisticRows
    }
    const { data } = await api.post(`/api/v1/inventory/locations/${parentId}/subzones/bulk`, items)
    await fetchZones()
    return data
  }

  async function updateZone(id, payload) {
    if (!isOnline()) {
      zones.value = zones.value.map(item => (item.id === id ? { ...item, ...payload, _offline_queued: true } : item))
      zoneTree.value = [...zones.value]
      await queueMutation({ method: 'put', url: `/api/v1/inventory/zones/${id}`, data: payload })
      await persistFetchAllSnapshot()
      return zones.value.find(item => item.id === id) || { id, ...payload, _offline_queued: true }
    }
    const { data } = await api.put(`/api/v1/inventory/zones/${id}`, payload)
    await fetchZones()
    return data
  }

  async function moveZone(id, payload) {
    const { data } = await api.post(`/api/v1/inventory/zones/${id}/move`, payload)
    await fetchZones()
    return data
  }

  async function deleteZonesBulk(ids) {
    if (!Array.isArray(ids) || !ids.length) return { deleted: 0, skipped: 0 }
    const { data } = await api.post('/api/v1/inventory/locations/bulk-delete', { ids })
    await fetchZones()
    return data
  }

  async function generateProductSku(prefix = 'PRD-') {
    const cleanedPrefix = String(prefix || '').trim() || 'PRD-'
    if (!isOnline()) {
      const existing = (products.value || []).map(item => String(item?.sku || ''))
      let maxNumber = 0
      let width = 4
      for (const sku of existing) {
        if (!sku.startsWith(cleanedPrefix)) continue
        const suffix = sku.slice(cleanedPrefix.length)
        if (!/^\d+$/.test(suffix)) continue
        maxNumber = Math.max(maxNumber, Number(suffix))
        width = Math.max(width, suffix.length)
      }
      return `${cleanedPrefix}${String(maxNumber + 1).padStart(width, '0')}`
    }

    const { data } = await api.get('/api/v1/inventory/products/generate-sku', { params: { prefix: cleanedPrefix } })
    return data?.sku || ''
  }

  async function generateDeviceAssetTag({ productId = null, prefix = null } = {}) {
    const chosenProduct = (products.value || []).find(item => item.id === productId) || null
    const cleanedPrefix = String(prefix || '').trim() || String(chosenProduct?.sku || '').trim() || 'ASSET'

    if (!isOnline()) {
      const normalizedPrefix = cleanedPrefix.toUpperCase().replace(/-+$/, '') || 'ASSET'
      const existing = (devices.value || []).map(item => String(item?.asset_tag || ''))
      let maxNumber = 0
      for (const tag of existing) {
        if (!tag.startsWith(`${normalizedPrefix}-`)) continue
        const suffix = tag.slice(normalizedPrefix.length + 1)
        if (!/^\d+$/.test(suffix)) continue
        maxNumber = Math.max(maxNumber, Number(suffix))
      }
      return `${normalizedPrefix}-${String(maxNumber + 1).padStart(3, '0')}`
    }

    const params = {}
    if (productId != null) params.product_id = productId
    if (prefix) params.prefix = prefix
    const { data } = await api.get('/api/v1/inventory/devices/generate-asset-tag', { params })
    return data?.asset_tag || ''
  }

  return {
    products,
    devices,
    zones,
    zoneTree,
    maintenances,
    schedules,
    auditLogs,
    checkedOutDevices,
    locationTypes,
    categories,
    categoryTree,
    fetchSource,
    loading,
    fetchAll,
    fetchCategories,
    prefillCategories,
    createCategory,
    updateCategory,
    deleteCategory,
    moveCategory,
    createProduct,
    updateProduct,
    bulkUpdateProducts,
    bulkDeleteProducts,
    fetchProductAccessories,
    updateProductAccessories,
    fetchProductComponents,
    updateProductComponents,
    createDevicesForProduct,
    createDevice,
    updateDevice,
    bulkUpdateDevices,
    bulkDeleteDevices,
    fetchZones,
    fetchMaintenance,
    fetchMaintenanceSchedules,
    createMaintenance,
    bulkScheduleMaintenance,
    updateMaintenance,
    completeMaintenance,
    bulkUpdateMaintenance,
    bulkDeleteMaintenance,
    bulkUpdateMaintenanceSchedules,
    bulkDeleteMaintenanceSchedules,
    fetchMaintenanceSchedule,
    updateMaintenanceSchedule,
    processScan,
    fetchCheckedOutDevices,
    fetchAuditLogs,
    fetchDeviceAuditLogs,
    createZone,
    createZonesBulk,
    deleteZonesBulk,
    updateZone,
    moveZone,
    generateProductSku,
    generateDeviceAssetTag,
  }
})
