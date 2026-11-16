import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../boot/axios'
import { isOnline, queueMutation, cacheSnapshot, readSnapshot } from '../services/offline/orbitSync'

export const useCrewStore = defineStore('crew', () => {
  const roles = ref([])
  const members = ref([])
  const loadingRoles = ref(false)
  const loadingMembers = ref(false)
  const skills = ref([])
  const certifications = ref([])
  // Bumped whenever job crew requirements change so views showing them
  // (e.g. the quote builder and the job's "crew requirements" panel) can
  // refresh without a full page reload.
  const crewRevision = ref(0)

  // Mirror inventory's offline snapshot pattern: each store persists its own
  // collections to IndexedDB via the shared cacheSnapshot helper so they can be
  // restored when a live fetch fails (e.g. offline on reload).
  async function persistFetchAllSnapshot() {
    await cacheSnapshot('crew.fetchAll', {
      roles: roles.value,
      members: members.value,
      skills: skills.value,
      certifications: certifications.value,
    })
  }

  async function restoreFetchAllSnapshot() {
    const cached = await readSnapshot('crew.fetchAll')
    if (!cached || typeof cached !== 'object') {
      return false
    }
    roles.value = Array.isArray(cached.roles) ? cached.roles : roles.value
    members.value = Array.isArray(cached.members) ? cached.members : members.value
    skills.value = Array.isArray(cached.skills) ? cached.skills : skills.value
    certifications.value = Array.isArray(cached.certifications) ? cached.certifications : certifications.value
    return true
  }

  async function fetchRoles() {
    loadingRoles.value = true
    try {
      const { data } = await api.get('/api/v1/crew/roles')
      roles.value = data
    } catch (error) {
      const restored = await restoreFetchAllSnapshot()
      if (!restored) {
        console.error('Failed to fetch crew roles:', error)
        throw error
      }
    } finally {
      loadingRoles.value = false
    }
  }

  async function createRole(payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'post', url: '/api/v1/crew/roles', data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.post('/api/v1/crew/roles', payload)
    roles.value = [data, ...roles.value.filter(r => r.id !== data.id)]
    return data
  }

  async function updateRole(id, payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'put', url: `/api/v1/crew/roles/${id}`, data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.put(`/api/v1/crew/roles/${id}`, payload)
    const idx = roles.value.findIndex(r => r.id === id)
    if (idx >= 0) roles.value[idx] = data
    return data
  }

  async function deleteRole(id) {
    if (!isOnline()) {
      await queueMutation({ method: 'delete', url: `/api/v1/crew/roles/${id}` })
      await persistFetchAllSnapshot()
      return
    }
    await api.delete(`/api/v1/crew/roles/${id}`)
    roles.value = roles.value.filter(r => r.id !== id)
  }

  async function fetchMembers(params = {}) {
    loadingMembers.value = true
    try {
      const { data } = await api.get('/api/v1/crew/members', { params })
      members.value = data
    } catch (error) {
      console.error('Failed to fetch crew members:', error)
      throw error
    } finally {
      loadingMembers.value = false
    }
  }

  async function getMember(id) {
    const { data } = await api.get(`/api/v1/crew/members/${id}`)
    return data
  }

  async function createMember(payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'post', url: '/api/v1/crew/members', data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.post('/api/v1/crew/members', payload)
    members.value = [data, ...members.value.filter(m => m.id !== data.id)]
    return data
  }

  async function updateMember(id, payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'put', url: `/api/v1/crew/members/${id}`, data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.put(`/api/v1/crew/members/${id}`, payload)
    const idx = members.value.findIndex(m => m.id === id)
    if (idx >= 0) members.value[idx] = data
    return data
  }

  async function deleteMember(id) {
    if (!isOnline()) {
      await queueMutation({ method: 'delete', url: `/api/v1/crew/members/${id}` })
      await persistFetchAllSnapshot()
      return
    }
    await api.delete(`/api/v1/crew/members/${id}`)
    members.value = members.value.filter(m => m.id !== id)
  }

  async function fetchSkills(params = {}) {
    const { data } = await api.get('/api/v1/crew/skills', { params })
    skills.value = data
    return data
  }

  async function createSkill(payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'post', url: '/api/v1/crew/skills', data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.post('/api/v1/crew/skills', payload)
    skills.value = [data, ...skills.value.filter(s => s.id !== data.id)]
    return data
  }

  async function deleteSkill(id) {
    if (!isOnline()) {
      await queueMutation({ method: 'delete', url: `/api/v1/crew/skills/${id}` })
      await persistFetchAllSnapshot()
      return
    }
    await api.delete(`/api/v1/crew/skills/${id}`)
    skills.value = skills.value.filter(s => s.id !== id)
  }

  async function fetchCertifications(params = {}) {
    const { data } = await api.get('/api/v1/crew/certifications', { params })
    certifications.value = data
    return data
  }

  async function createCertification(payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'post', url: '/api/v1/crew/certifications', data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.post('/api/v1/crew/certifications', payload)
    certifications.value = [data, ...certifications.value.filter(c => c.id !== data.id)]
    return data
  }

  async function deleteCertification(id) {
    if (!isOnline()) {
      await queueMutation({ method: 'delete', url: `/api/v1/crew/certifications/${id}` })
      await persistFetchAllSnapshot()
      return
    }
    await api.delete(`/api/v1/crew/certifications/${id}`)
    certifications.value = certifications.value.filter(c => c.id !== id)
  }

  async function fetchJobCrewRequirements(jobId) {
    const { data } = await api.get(`/api/v1/crew/jobs/${jobId}/crew-requirements`)
    return data
  }

  async function createJobCrewRequirement(jobId, payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'post', url: `/api/v1/crew/jobs/${jobId}/crew-requirements`, data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.post(`/api/v1/crew/jobs/${jobId}/crew-requirements`, payload)
    crewRevision.value++
    return data
  }

  async function updateJobCrewRequirement(jobId, reqId, payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'put', url: `/api/v1/crew/jobs/${jobId}/crew-requirements/${reqId}`, data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.put(`/api/v1/crew/jobs/${jobId}/crew-requirements/${reqId}`, payload)
    crewRevision.value++
    return data
  }

  async function deleteJobCrewRequirement(jobId, reqId) {
    if (!isOnline()) {
      await queueMutation({ method: 'delete', url: `/api/v1/crew/jobs/${jobId}/crew-requirements/${reqId}` })
      await persistFetchAllSnapshot()
      return
    }
    await api.delete(`/api/v1/crew/jobs/${jobId}/crew-requirements/${reqId}`)
    crewRevision.value++
  }

  async function bulkUpsertJobCrewRequirements(jobId, items) {
    if (!isOnline()) {
      await queueMutation({ method: 'put', url: `/api/v1/crew/jobs/${jobId}/crew-requirements/bulk`, data: { items } })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.put(`/api/v1/crew/jobs/${jobId}/crew-requirements/bulk`, { items })
    crewRevision.value++
    return data
  }

  async function fetchJobCrewAssignments(jobId) {
    const { data } = await api.get(`/api/v1/crew/jobs/${jobId}/crew-assignments`)
    return data
  }

  async function createCrewAssignment(payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'post', url: '/api/v1/crew/assignments', data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.post('/api/v1/crew/assignments', payload)
    return data
  }

  async function updateCrewAssignment(id, payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'put', url: `/api/v1/crew/assignments/${id}`, data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.put(`/api/v1/crew/assignments/${id}`, payload)
    return data
  }

  async function deleteCrewAssignment(id) {
    if (!isOnline()) {
      await queueMutation({ method: 'delete', url: `/api/v1/crew/assignments/${id}` })
      await persistFetchAllSnapshot()
      return
    }
    await api.delete(`/api/v1/crew/assignments/${id}`)
  }

  async function fetchCrewSuggestions(jobId, requirementId = null) {
    const params = {}
    if (requirementId) params.requirement_id = requirementId
    const { data } = await api.get(`/api/v1/crew/jobs/${jobId}/crew-suggestions`, { params })
    return data
  }

  // ── Self-Service ────────────────────────────────────────────────────────

  async function fetchMySkills() {
    const { data } = await api.get('/api/v1/crew/users/me/skills')
    return data
  }

  async function addMySkill(skillId) {
    if (!isOnline()) {
      await queueMutation({ method: 'post', url: '/api/v1/crew/users/me/skills', data: { skill_id: skillId } })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.post('/api/v1/crew/users/me/skills', { skill_id: skillId })
    return data
  }

  async function removeMySkill(skillId) {
    if (!isOnline()) {
      await queueMutation({ method: 'delete', url: `/api/v1/crew/users/me/skills/${skillId}` })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.delete(`/api/v1/crew/users/me/skills/${skillId}`)
    return data
  }

  async function fetchMyCertifications() {
    const { data } = await api.get('/api/v1/crew/users/me/certifications')
    return data
  }

  async function addMyCertification(payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'post', url: '/api/v1/crew/users/me/certifications', data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.post('/api/v1/crew/users/me/certifications', payload)
    return data
  }

  async function updateMyCertification(certId, payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'patch', url: `/api/v1/crew/users/me/certifications/${certId}`, data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.patch(`/api/v1/crew/users/me/certifications/${certId}`, payload)
    return data
  }

  async function removeMyCertification(certId) {
    if (!isOnline()) {
      await queueMutation({ method: 'delete', url: `/api/v1/crew/users/me/certifications/${certId}` })
      await persistFetchAllSnapshot()
      return
    }
    await api.delete(`/api/v1/crew/users/me/certifications/${certId}`)
  }

  // ── Compliance ──────────────────────────────────────────────────────────

  async function fetchJobCompliance(jobId) {
    const { data } = await api.get(`/api/v1/crew/jobs/${jobId}/compliance`)
    return data
  }

  // ── Required Certifications ─────────────────────────────────────────────

  async function fetchEquipmentRequiredCerts(productId) {
    const { data } = await api.get(`/api/v1/crew/equipment/${productId}/required-certifications`)
    return data
  }

  async function setEquipmentRequiredCerts(productId, certIds) {
    if (!isOnline()) {
      await queueMutation({ method: 'put', url: `/api/v1/crew/equipment/${productId}/required-certifications`, data: { cert_ids: certIds } })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.put(`/api/v1/crew/equipment/${productId}/required-certifications`, { cert_ids: certIds })
    return data
  }

  async function fetchRoleRequiredCerts(roleId) {
    const { data } = await api.get(`/api/v1/crew/roles/${roleId}/required-certifications`)
    return data
  }

  async function setRoleRequiredCerts(roleId, certIds) {
    if (!isOnline()) {
      await queueMutation({ method: 'put', url: `/api/v1/crew/roles/${roleId}/required-certifications`, data: { cert_ids: certIds } })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.put(`/api/v1/crew/roles/${roleId}/required-certifications`, { cert_ids: certIds })
    return data
  }

  return {
    roles,
    members,
    skills,
    certifications,
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
    fetchSkills,
    createSkill,
    deleteSkill,
    fetchCertifications,
    createCertification,
    deleteCertification,
    fetchJobCrewRequirements,
    createJobCrewRequirement,
    updateJobCrewRequirement,
    deleteJobCrewRequirement,
    bulkUpsertJobCrewRequirements,
    crewRevision,
    persistFetchAllSnapshot,
    restoreFetchAllSnapshot,
    fetchJobCrewAssignments,
    createCrewAssignment,
    updateCrewAssignment,
    deleteCrewAssignment,
    fetchCrewSuggestions,
    fetchMySkills,
    addMySkill,
    removeMySkill,
    fetchMyCertifications,
    addMyCertification,
    updateMyCertification,
    removeMyCertification,
    fetchJobCompliance,
    fetchEquipmentRequiredCerts,
    setEquipmentRequiredCerts,
    fetchRoleRequiredCerts,
    setRoleRequiredCerts,
  }
})
