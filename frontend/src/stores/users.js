import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../boot/axios'

export const useUsersStore = defineStore('users', () => {
  const users = ref([])
  const roles = ref([])

  async function fetchUsers() {
    const { data } = await api.get('/api/v1/auth/users')
    users.value = data.users || data
    return users.value
  }

  async function createUser(payload) {
    const { data } = await api.post('/api/v1/auth/users', payload)
    return data
  }

  async function getUser(id) {
    const { data } = await api.get(`/api/v1/auth/users/${id}`)
    return data
  }

  async function listRoles() {
    const { data } = await api.get('/api/v1/auth/roles')
    roles.value = data
    return roles.value
  }

  async function listUserRoles(userId) {
    const { data } = await api.get(`/api/v1/auth/users/${userId}/roles`)
    return data
  }

  async function assignRoleToUser(userId, roleId) {
    const { data } = await api.post(`/api/v1/auth/users/${userId}/roles`, { role_id: roleId })
    return data
  }

  async function removeRoleFromUser(userId, roleId) {
    await api.delete(`/api/v1/auth/users/${userId}/roles/${roleId}`)
  }

  async function deleteUser(id) {
    await api.delete(`/api/v1/auth/users/${id}`)
    // refresh list
    await fetchUsers()
  }

  async function updateUser(id, payload) {
    const { data } = await api.put(`/api/v1/auth/users/${id}`, payload)
    return data
  }

  // API key helpers (admin)
  async function listApiKeys() {
    const { data } = await api.get('/api/v1/auth/api-keys')
    return data
  }

  async function createApiKey(name, rawKey, isAdmin = false) {
    const { data } = await api.post('/api/v1/auth/api-keys', { name, raw_key: rawKey, is_admin: isAdmin })
    return data
  }

  async function revokeApiKey(id) {
    await api.delete(`/api/v1/auth/api-keys/${id}`)
  }

  return { users, roles, fetchUsers, listRoles, createUser, getUser, updateUser, deleteUser, listUserRoles, assignRoleToUser, removeRoleFromUser, listApiKeys, createApiKey, revokeApiKey }
})
