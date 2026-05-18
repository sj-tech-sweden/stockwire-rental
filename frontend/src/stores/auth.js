import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api } from '../boot/axios'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('sw_token') || null)
  const me = ref(JSON.parse(localStorage.getItem('sw_user') || 'null'))

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => me.value?.role === 'admin')

  // Restore Authorization header on page reload
  if (token.value) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
  }

  function _setSession(data) {
    token.value = data.access_token
    me.value = data.user
    localStorage.setItem('sw_token', data.access_token)
    localStorage.setItem('sw_user', JSON.stringify(data.user))
    api.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`
  }

  function logout() {
    token.value = null
    me.value = null
    localStorage.removeItem('sw_token')
    localStorage.removeItem('sw_user')
    delete api.defaults.headers.common['Authorization']
  }

  async function login(email, password) {
    const { data } = await api.post('/api/v1/auth/login', { email, password })
    _setSession(data)
  }

  async function setup(email, password, fullName) {
    const { data } = await api.post('/api/v1/auth/setup', {
      email,
      password,
      full_name: fullName,
      role: 'admin',
    })
    _setSession(data)
  }

  async function checkBootstrap() {
    const { data } = await api.get('/api/v1/auth/bootstrap-status')
    return data.setup_needed
  }

  return { me, token, isAuthenticated, isAdmin, login, setup, logout, checkBootstrap }
})
