import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../boot/axios'

export const useCrewStore = defineStore('crew', () => {
  const roles = ref([])
  const members = ref([])
  const loadingRoles = ref(false)
  const loadingMembers = ref(false)

  async function fetchRoles() {
    loadingRoles.value = true
    try {
      const { data } = await api.get('/api/v1/crew/roles')
      roles.value = data
    } finally {
      loadingRoles.value = false
    }
  }

  async function createRole(payload) {
    const { data } = await api.post('/api/v1/crew/roles', payload)
    roles.value = [data, ...roles.value.filter(r => r.id !== data.id)]
    return data
  }

  async function updateRole(id, payload) {
    const { data } = await api.put(`/api/v1/crew/roles/${id}`, payload)
    const idx = roles.value.findIndex(r => r.id === id)
    if (idx >= 0) roles.value[idx] = data
    return data
  }

  async function deleteRole(id) {
    await api.delete(`/api/v1/crew/roles/${id}`)
    roles.value = roles.value.filter(r => r.id !== id)
  }

  async function fetchMembers(params = {}) {
    loadingMembers.value = true
    try {
      const { data } = await api.get('/api/v1/crew/members', { params })
      members.value = data
    } finally {
      loadingMembers.value = false
    }
  }

  async function getMember(id) {
    const { data } = await api.get(`/api/v1/crew/members/${id}`)
    return data
  }

  async function createMember(payload) {
    const { data } = await api.post('/api/v1/crew/members', payload)
    members.value = [data, ...members.value.filter(m => m.id !== data.id)]
    return data
  }

  async function updateMember(id, payload) {
    const { data } = await api.put(`/api/v1/crew/members/${id}`, payload)
    const idx = members.value.findIndex(m => m.id === id)
    if (idx >= 0) members.value[idx] = data
    return data
  }

  async function deleteMember(id) {
    await api.delete(`/api/v1/crew/members/${id}`)
    members.value = members.value.filter(m => m.id !== id)
  }

  async function fetchJobCrewRequirements(jobId) {
    const { data } = await api.get(`/api/v1/crew/jobs/${jobId}/crew-requirements`)
    return data
  }

  async function createJobCrewRequirement(jobId, payload) {
    const { data } = await api.post(`/api/v1/crew/jobs/${jobId}/crew-requirements`, payload)
    return data
  }

  async function updateJobCrewRequirement(jobId, reqId, payload) {
    const { data } = await api.put(`/api/v1/crew/jobs/${jobId}/crew-requirements/${reqId}`, payload)
    return data
  }

  async function deleteJobCrewRequirement(jobId, reqId) {
    await api.delete(`/api/v1/crew/jobs/${jobId}/crew-requirements/${reqId}`)
  }

  async function bulkUpsertJobCrewRequirements(jobId, items) {
    const { data } = await api.put(`/api/v1/crew/jobs/${jobId}/crew-requirements/bulk`, { items })
    return data
  }

  async function fetchJobCrewAssignments(jobId) {
    const { data } = await api.get(`/api/v1/crew/jobs/${jobId}/crew-assignments`)
    return data
  }

  async function createCrewAssignment(payload) {
    const { data } = await api.post('/api/v1/crew/assignments', payload)
    return data
  }

  async function updateCrewAssignment(id, payload) {
    const { data } = await api.put(`/api/v1/crew/assignments/${id}`, payload)
    return data
  }

  async function deleteCrewAssignment(id) {
    await api.delete(`/api/v1/crew/assignments/${id}`)
  }

  async function fetchCrewSuggestions(jobId, requirementId = null) {
    const params = {}
    if (requirementId) params.requirement_id = requirementId
    const { data } = await api.get(`/api/v1/crew/jobs/${jobId}/crew-suggestions`, { params })
    return data
  }

  return {
    roles,
    members,
    loadingRoles,
    loadingMembers,
    fetchRoles,
    createRole,
    updateRole,
    deleteRole,
    fetchMembers,
    getMember,
    createMember,
    updateMember,
    deleteMember,
    fetchJobCrewRequirements,
    createJobCrewRequirement,
    updateJobCrewRequirement,
    deleteJobCrewRequirement,
    bulkUpsertJobCrewRequirements,
    fetchJobCrewAssignments,
    createCrewAssignment,
    updateCrewAssignment,
    deleteCrewAssignment,
    fetchCrewSuggestions,
  }
})
