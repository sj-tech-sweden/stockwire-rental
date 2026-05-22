import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '../boot/axios'

export const useActivityStore = defineStore('activity', () => {
  const logs = ref([])
  const loading = ref(false)

  async function fetchLogs(limit = 200, entityType = null) {
    loading.value = true
    try {
      const params = { limit }
      if (entityType) params.entity_type = entityType
      const { data } = await api.get('/api/v1/audit/activity', { params })
      logs.value = Array.isArray(data) ? data : []
      return logs.value
    } finally {
      loading.value = false
    }
  }

  return {
    logs,
    loading,
    fetchLogs,
  }
})
