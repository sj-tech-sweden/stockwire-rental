import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '../boot/axios'
import {
  cacheSnapshot,
  isOnline,
  queueMutation,
  readSnapshot,
} from '../services/offline/orbitSync'

export const JOB_STATUSES = [
  { label: 'Draft',       value: 'draft',       color: 'grey' },
  { label: 'Confirmed',   value: 'confirmed',   color: 'info' },
  { label: 'In Progress', value: 'in_progress',  color: 'warning' },
  { label: 'Completed',   value: 'completed',   color: 'positive' },
  { label: 'Cancelled',   value: 'cancelled',   color: 'negative' },
]

export const useJobsStore = defineStore('jobs', () => {
  const jobs = ref([])
  const requirements = ref([])
  const loading = ref(false)
  const fetchSource = ref('none')

  async function persistSnapshot() {
    await cacheSnapshot('jobs.fetchAll', {
      jobs: jobs.value,
      requirements: requirements.value,
    })
  }

  async function restoreSnapshot() {
    const cached = await readSnapshot('jobs.fetchAll')
    if (!cached || typeof cached !== 'object') {
      return false
    }
    jobs.value = Array.isArray(cached.jobs) ? cached.jobs : []
    requirements.value = Array.isArray(cached.requirements) ? cached.requirements : []
    return true
  }

  async function fetchAll() {
    loading.value = true
    try {
      const [jobsRes, reqRes] = await Promise.all([
        api.get('/api/v1/jobs'),
        api.get('/api/v1/jobs/requirements')
      ])
      jobs.value = jobsRes.data
      requirements.value = reqRes.data
      await persistSnapshot()
      fetchSource.value = 'live'
    } catch (error) {
      const restored = await restoreSnapshot()
      if (restored) {
        fetchSource.value = 'snapshot'
        return
      }
      throw error
    } finally {
      loading.value = false
    }
  }

  async function createJob(payload) {
    if (!isOnline()) {
      const tempId = -Date.now()
      const optimistic = { id: tempId, ...payload, _offline_queued: true }
      jobs.value = [...jobs.value, optimistic]
      await queueMutation({ method: 'post', url: '/api/v1/jobs', data: payload })
      await persistSnapshot()
      return optimistic
    }
    const { data } = await api.post('/api/v1/jobs', payload)
    jobs.value = [...jobs.value, data]
    await persistSnapshot()
    return data
  }

  async function generateJobCode(prefix = 'JOB-') {
    const { data } = await api.get('/api/v1/jobs/generate-code', { params: { prefix } })
    return data?.job_code || ''
  }

  async function updateJob(id, payload) {
    if (!isOnline()) {
      jobs.value = jobs.value.map(j => j.id === id ? { ...j, ...payload, _offline_queued: true } : j)
      await queueMutation({ method: 'put', url: `/api/v1/jobs/${id}`, data: payload })
      await persistSnapshot()
      return jobs.value.find(j => j.id === id) || { id, ...payload, _offline_queued: true }
    }
    const { data } = await api.put(`/api/v1/jobs/${id}`, payload)
    jobs.value = jobs.value.map(j => j.id === id ? data : j)
    await persistSnapshot()
    return data
  }

  async function deleteJob(id) {
    if (!isOnline()) {
      jobs.value = jobs.value.filter(j => j.id !== id)
      await queueMutation({ method: 'delete', url: `/api/v1/jobs/${id}` })
      await persistSnapshot()
      return
    }
    await api.delete(`/api/v1/jobs/${id}`)
    jobs.value = jobs.value.filter(j => j.id !== id)
    await persistSnapshot()
  }

  async function createRequirement(payload) {
    if (!isOnline()) {
      const tempId = -Date.now()
      const optimistic = { id: tempId, ...payload, _offline_queued: true }
      requirements.value = [...requirements.value, optimistic]
      await queueMutation({ method: 'post', url: '/api/v1/jobs/requirements', data: payload })
      await persistSnapshot()
      return optimistic
    }
    const { data } = await api.post('/api/v1/jobs/requirements', payload)
    requirements.value = [...requirements.value, data]
    await persistSnapshot()
    return data
  }

  async function updateRequirement(id, payload) {
    if (!isOnline()) {
      requirements.value = requirements.value.map(r => (r.id === id ? { ...r, ...payload, _offline_queued: true } : r))
      await queueMutation({ method: 'put', url: `/api/v1/jobs/requirements/${id}`, data: payload })
      await persistSnapshot()
      return requirements.value.find(r => r.id === id) || { id, ...payload, _offline_queued: true }
    }
    const { data } = await api.put(`/api/v1/jobs/requirements/${id}`, payload)
    requirements.value = requirements.value.map(r => (r.id === id ? data : r))
    await persistSnapshot()
    return data
  }

  async function bulkUpsertRequirements(jobId, items) {
    if (!isOnline()) {
      const offlineRows = items.map((item, idx) => ({
        id: -(Date.now() + idx),
        job_id: jobId,
        ...item,
        _offline_queued: true,
      }))
      requirements.value = [
        ...requirements.value.filter(r => r.job_id !== jobId),
        ...offlineRows,
      ]
      await queueMutation({ method: 'put', url: `/api/v1/jobs/${jobId}/requirements/bulk`, data: { items } })
      await persistSnapshot()
      return offlineRows
    }
    const { data } = await api.put(`/api/v1/jobs/${jobId}/requirements/bulk`, { items })
    requirements.value = [
      ...requirements.value.filter(r => r.job_id !== jobId),
      ...data,
    ]
    await persistSnapshot()
    return data
  }

  async function syncJobToProductionPlanner(jobId) {
    const { data } = await api.post(`/api/v1/jobs/${jobId}/sync-productionplanner`)
    const job = jobs.value.find(j => j.id === jobId)
    if (job && data.success && data.productionplanner_project_id) {
      job.productionplanner_project_id = data.productionplanner_project_id
      await persistSnapshot()
    }
    return data
  }

  async function getJobProductionPlannerInfo(jobId) {
    const { data } = await api.get(`/api/v1/jobs/${jobId}/productionplanner`)
    return data
  }

  function getProductionPlannerUrl(productionPlannerProjectId) {
    return `https://app.productionplanner.io/projects/${productionPlannerProjectId}`
  }

  return {
    jobs,
    requirements,
    fetchSource,
    loading,
    fetchAll,
    createJob,
    generateJobCode,
    updateJob,
    deleteJob,
    createRequirement,
    updateRequirement,
    bulkUpsertRequirements,
    syncJobToProductionPlanner,
    getJobProductionPlannerInfo,
    getProductionPlannerUrl,
  }
})
