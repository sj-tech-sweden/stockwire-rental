import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '../boot/axios'

export const useAuthStore = defineStore('auth', () => {
  const users = ref([])
  const loading = ref(false)

  async function fetchUsers() {
    loading.value = true
    try {
      const { data } = await api.get('/api/v1/auth/users')
      users.value = data
    } finally {
      loading.value = false
    }
  }

  async function createUser(payload) {
    await api.post('/api/v1/auth/users', payload)
    await fetchUsers()
  }

  return { users, loading, fetchUsers, createUser }
})
