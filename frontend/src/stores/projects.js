import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '../boot/axios'
import { cacheSnapshot, isOnline, queueMutation, readSnapshot } from '../services/offline/orbitSync'

export const useProjectsStore = defineStore('projects', () => {
  const projects = ref([])
  const loading = ref(false)

  async function fetchAll() {
    loading.value = true
    try {
      const { data } = await api.get('/api/v1/projects')
      projects.value = data
      await cacheSnapshot('projects.fetchAll', data)
    } catch (error) {
      if (!isOnline()) {
        const cached = await readSnapshot('projects.fetchAll')
        if (Array.isArray(cached)) {
          projects.value = cached
          return
        }
      }
      throw error
    } finally {
      loading.value = false
    }
  }

  async function createProject(payload) {
    if (!isOnline()) {
      const optimistic = { id: -Date.now(), ...payload, _offline_queued: true }
      projects.value = [...projects.value, optimistic]
      await queueMutation({ method: 'post', url: '/api/v1/projects', data: payload })
      await cacheSnapshot('projects.fetchAll', projects.value)
      return optimistic
    }
    const { data } = await api.post('/api/v1/projects', payload)
    projects.value = [...projects.value, data]
    await cacheSnapshot('projects.fetchAll', projects.value)
    return data
  }

  async function updateProject(id, payload) {
    if (!isOnline()) {
      projects.value = projects.value.map(p => p.id === id ? { ...p, ...payload, _offline_queued: true } : p)
      await queueMutation({ method: 'put', url: `/api/v1/projects/${id}`, data: payload })
      await cacheSnapshot('projects.fetchAll', projects.value)
      return projects.value.find(p => p.id === id) || { id, ...payload, _offline_queued: true }
    }
    const { data } = await api.put(`/api/v1/projects/${id}`, payload)
    projects.value = projects.value.map(p => p.id === id ? data : p)
    await cacheSnapshot('projects.fetchAll', projects.value)
    return data
  }

  async function deleteProject(id) {
    if (!isOnline()) {
      projects.value = projects.value.filter(p => p.id !== id)
      await queueMutation({ method: 'delete', url: `/api/v1/projects/${id}` })
      await cacheSnapshot('projects.fetchAll', projects.value)
      return
    }
    await api.delete(`/api/v1/projects/${id}`)
    projects.value = projects.value.filter(p => p.id !== id)
    await cacheSnapshot('projects.fetchAll', projects.value)
  }

  return { projects, loading, fetchAll, createProject, updateProject, deleteProject }
})
