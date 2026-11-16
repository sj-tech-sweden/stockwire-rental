import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../boot/axios'
import {
  isOnline,
  queueMutation,
  cacheSnapshot,
  readSnapshot,
} from '../services/offline/orbitSync'

export const useUsersStore = defineStore('users', () => {
  const users = ref([])
  const roles = ref([])

  // Mirror stores/inventory.js: persist/restore this store's collections so
  // they survive an offline reload (cacheSnapshot/readSnapshot from orbitSync).
  async function persistFetchAllSnapshot() {
    await cacheSnapshot('users.fetchAll', {
      users: users.value,
      roles: roles.value,
    })
  }

  async function restoreFetchAllSnapshot() {
    const cached = await readSnapshot('users.fetchAll')
    if (!cached || typeof cached !== 'object') return false
    users.value = Array.isArray(cached.users) ? cached.users : users.value
    roles.value = Array.isArray(cached.roles) ? cached.roles : roles.value
    return true
  }

  async function fetchUsers() {
    try {
      const { data } = await api.get('/api/v1/auth/users')
      users.value = data.users || data
      await persistFetchAllSnapshot()
      return users.value
    } catch (error) {
      if (!isOnline()) {
        const restored = await restoreFetchAllSnapshot()
        if (restored) return users.value
      }
      throw error
    }
  }

  async function createUser(payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'post', url: '/api/v1/auth/users', data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.post('/api/v1/auth/users', payload)
    await persistFetchAllSnapshot()
    return data
  }

  async function getUser(id) {
    const { data } = await api.get(`/api/v1/auth/users/${id}`)
    return data
  }

  async function listRoles() {
    try {
      const { data } = await api.get('/api/v1/auth/roles')
      roles.value = data
      await persistFetchAllSnapshot()
      return roles.value
    } catch (error) {
      if (!isOnline()) {
        const restored = await restoreFetchAllSnapshot()
        if (restored) return roles.value
      }
      throw error
    }
  }

  async function listUserRoles(userId) {
    const { data } = await api.get(`/api/v1/auth/users/${userId}/roles`)
    return data
  }

  async function assignRoleToUser(userId, roleId) {
    if (!isOnline()) {
      await queueMutation({
        method: 'post',
        url: `/api/v1/auth/users/${userId}/roles`,
        data: { role_id: roleId },
      })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.post(`/api/v1/auth/users/${userId}/roles`, { role_id: roleId })
    await persistFetchAllSnapshot()
    return data
  }

  async function removeRoleFromUser(userId, roleId) {
    if (!isOnline()) {
      await queueMutation({
        method: 'delete',
        url: `/api/v1/auth/users/${userId}/roles/${roleId}`,
      })
      await persistFetchAllSnapshot()
      return
    }
    await api.delete(`/api/v1/auth/users/${userId}/roles/${roleId}`)
    await persistFetchAllSnapshot()
  }

  async function deleteUser(id) {
    if (!isOnline()) {
      await queueMutation({ method: 'delete', url: `/api/v1/auth/users/${id}` })
      await persistFetchAllSnapshot()
      return
    }
    await api.delete(`/api/v1/auth/users/${id}`)
    // refresh list
    await fetchUsers()
  }

  async function updateUser(id, payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'put', url: `/api/v1/auth/users/${id}`, data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.put(`/api/v1/auth/users/${id}`, payload)
    await persistFetchAllSnapshot()
    return data
  }

  // API key helpers (admin)
  async function listApiKeys() {
    const { data } = await api.get('/api/v1/auth/api-keys')
    return data
  }

  async function createApiKey(name, rawKey, isAdmin = false) {
    if (!isOnline()) {
      await queueMutation({
        method: 'post',
        url: '/api/v1/auth/api-keys',
        data: { name, raw_key: rawKey, is_admin: isAdmin },
      })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.post('/api/v1/auth/api-keys', { name, raw_key: rawKey, is_admin: isAdmin })
    await persistFetchAllSnapshot()
    return data
  }

  async function revokeApiKey(id) {
    if (!isOnline()) {
      await queueMutation({ method: 'delete', url: `/api/v1/auth/api-keys/${id}` })
      await persistFetchAllSnapshot()
      return
    }
    await api.delete(`/api/v1/auth/api-keys/${id}`)
    await persistFetchAllSnapshot()
  }

  return { users, roles, fetchUsers, listRoles, createUser, getUser, updateUser, deleteUser, listUserRoles, assignRoleToUser, removeRoleFromUser, listApiKeys, createApiKey, revokeApiKey, persistFetchAllSnapshot, restoreFetchAllSnapshot }
})
