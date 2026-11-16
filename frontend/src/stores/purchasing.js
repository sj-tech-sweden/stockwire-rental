import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../boot/axios'
import {
  isOnline,
  queueMutation,
  cacheSnapshot,
  readSnapshot,
} from '../services/offline/orbitSync'

export const usePurchasingStore = defineStore('purchasing', () => {
  const purchaseOrders = ref([])
  const loading = ref(false)
  const loadingPo = ref(false)

  // Mirror stores/inventory.js: each store persists its own collections to
  // IndexedDB via the shared cacheSnapshot helper, and restores them when a
  // live fetch fails (e.g. offline on reload).
  async function persistFetchAllSnapshot() {
    await cacheSnapshot('purchasing.fetchAll', {
      purchaseOrders: purchaseOrders.value,
    })
  }

  async function restoreFetchAllSnapshot() {
    const cached = await readSnapshot('purchasing.fetchAll')
    if (!cached || typeof cached !== 'object') {
      return false
    }
    purchaseOrders.value = Array.isArray(cached.purchaseOrders) ? cached.purchaseOrders : purchaseOrders.value
    return true
  }

  async function fetchPurchaseOrders() {
    loading.value = true
    try {
      const { data } = await api.get('/api/v1/purchasing/purchase-orders')
      purchaseOrders.value = Array.isArray(data) ? data : []
      await persistFetchAllSnapshot()
    } catch (error) {
      const restored = await restoreFetchAllSnapshot()
      if (!restored) {
        console.error('Failed to fetch purchase orders:', error)
        throw error
      }
    } finally {
      loading.value = false
    }
  }

  async function fetchPurchaseOrder(id) {
    loadingPo.value = true
    try {
      const { data } = await api.get(`/api/v1/purchasing/purchase-orders/${id}`)
      return data
    } finally {
      loadingPo.value = false
    }
  }

  async function fetchReceivingLookup(code) {
    const { data } = await api.get('/api/v1/purchasing/receiving/lookup', { params: { code } })
    return data
  }

  async function previewPurchaseOrders(payload) {
    const { data } = await api.post('/api/v1/purchasing/purchase-orders/preview', payload)
    return data
  }

  async function fetchPurchaseOrderPdf(id, language = 'en') {
    return api.get(`/api/v1/purchasing/purchase-orders/${id}/pdf`, {
      params: { language },
      responseType: 'blob',
    })
  }

  // --- Mutations (offline-capable) --------------------------------------- #

  async function buildPurchaseOrders(payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'post', url: '/api/v1/purchasing/purchase-orders/build', data: payload })
      await persistFetchAllSnapshot()
      return []
    }
    const { data } = await api.post('/api/v1/purchasing/purchase-orders/build', payload)
    await persistFetchAllSnapshot()
    return data
  }

  async function createPosFromJob(jobId, selections = null) {
    if (!isOnline()) {
      await queueMutation({
        method: 'post',
        url: `/api/v1/purchasing/purchase-orders/from-job/${jobId}`,
        data: selections,
      })
      await persistFetchAllSnapshot()
      return []
    }
    const { data } = await api.post(`/api/v1/purchasing/purchase-orders/from-job/${jobId}`, selections)
    await persistFetchAllSnapshot()
    return data
  }

  async function createPosFromDraft(draftId) {
    if (!isOnline()) {
      await queueMutation({
        method: 'post',
        url: `/api/v1/purchasing/purchase-orders/from-draft/${draftId}`,
      })
      await persistFetchAllSnapshot()
      return []
    }
    const { data } = await api.post(`/api/v1/purchasing/purchase-orders/from-draft/${draftId}`)
    await persistFetchAllSnapshot()
    return data
  }

  async function createCombinedPos(payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'post', url: '/api/v1/purchasing/purchase-orders/combined', data: payload })
      await persistFetchAllSnapshot()
      return []
    }
    const { data } = await api.post('/api/v1/purchasing/purchase-orders/combined', payload)
    await persistFetchAllSnapshot()
    return data
  }

  async function addLinesToPo(poId, payload) {
    if (!isOnline()) {
      await queueMutation({
        method: 'post',
        url: `/api/v1/purchasing/purchase-orders/${poId}/add-lines`,
        data: payload,
      })
      await persistFetchAllSnapshot()
      return null
    }
    const { data } = await api.post(`/api/v1/purchasing/purchase-orders/${poId}/add-lines`, payload)
    await persistFetchAllSnapshot()
    return data
  }

  async function updatePurchaseOrder(poId, payload) {
    if (!isOnline()) {
      await queueMutation({
        method: 'patch',
        url: `/api/v1/purchasing/purchase-orders/${poId}`,
        data: payload,
      })
      await persistFetchAllSnapshot()
      return null
    }
    const { data } = await api.patch(`/api/v1/purchasing/purchase-orders/${poId}`, payload)
    await persistFetchAllSnapshot()
    return data
  }

  async function deletePurchaseOrder(poId) {
    if (!isOnline()) {
      await queueMutation({
        method: 'delete',
        url: `/api/v1/purchasing/purchase-orders/${poId}`,
      })
      purchaseOrders.value = purchaseOrders.value.filter((po) => po.id !== poId)
      await persistFetchAllSnapshot()
      return
    }
    await api.delete(`/api/v1/purchasing/purchase-orders/${poId}`)
    purchaseOrders.value = purchaseOrders.value.filter((po) => po.id !== poId)
    await persistFetchAllSnapshot()
  }

  async function updatePurchaseOrderLine(poId, lineId, payload) {
    if (!isOnline()) {
      await queueMutation({
        method: 'put',
        url: `/api/v1/purchasing/purchase-orders/${poId}/lines/${lineId}`,
        data: payload,
      })
      await persistFetchAllSnapshot()
      return null
    }
    const { data } = await api.put(`/api/v1/purchasing/purchase-orders/${poId}/lines/${lineId}`, payload)
    await persistFetchAllSnapshot()
    return data
  }

  async function deletePurchaseOrderLine(poId, lineId) {
    if (!isOnline()) {
      await queueMutation({
        method: 'delete',
        url: `/api/v1/purchasing/purchase-orders/${poId}/lines/${lineId}`,
      })
      await persistFetchAllSnapshot()
      return
    }
    await api.delete(`/api/v1/purchasing/purchase-orders/${poId}/lines/${lineId}`)
    await persistFetchAllSnapshot()
  }

  return {
    purchaseOrders,
    loading,
    loadingPo,
    fetchPurchaseOrders,
    fetchPurchaseOrder,
    fetchReceivingLookup,
    previewPurchaseOrders,
    fetchPurchaseOrderPdf,
    buildPurchaseOrders,
    createPosFromJob,
    createPosFromDraft,
    createCombinedPos,
    addLinesToPo,
    updatePurchaseOrder,
    deletePurchaseOrder,
    updatePurchaseOrderLine,
    deletePurchaseOrderLine,
    persistFetchAllSnapshot,
    restoreFetchAllSnapshot,
  }
})
