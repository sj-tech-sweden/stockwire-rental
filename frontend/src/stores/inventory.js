import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '../boot/axios'

export const useInventoryStore = defineStore('inventory', () => {
  const products = ref([])
  const devices = ref([])
  const zones = ref([])
  const loading = ref(false)

  async function fetchAll() {
    loading.value = true
    try {
      const [productsRes, devicesRes, zonesRes] = await Promise.all([
        api.get('/api/v1/inventory/products'),
        api.get('/api/v1/inventory/devices'),
        api.get('/api/v1/inventory/zones')
      ])
      products.value = productsRes.data
      devices.value = devicesRes.data
      zones.value = zonesRes.data
    } finally {
      loading.value = false
    }
  }

  return { products, devices, zones, loading, fetchAll }
})
