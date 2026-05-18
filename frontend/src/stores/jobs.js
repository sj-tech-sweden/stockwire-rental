import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '../boot/axios'

export const useJobsStore = defineStore('jobs', () => {
  const jobs = ref([])
  const requirements = ref([])
  const loading = ref(false)

  async function fetchAll() {
    loading.value = true
    try {
      const [jobsRes, reqRes] = await Promise.all([
        api.get('/api/v1/jobs'),
        api.get('/api/v1/jobs/requirements')
      ])
      jobs.value = jobsRes.data
      requirements.value = reqRes.data
    } finally {
      loading.value = false
    }
  }

  return { jobs, requirements, loading, fetchAll }
})
