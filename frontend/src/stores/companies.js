import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api } from '../boot/axios'
import { cacheSnapshot, isOnline, queueMutation, readSnapshot } from '../services/offline/orbitSync'

export const useCompaniesStore = defineStore('companies', () => {
  const companies = ref([])
  const loading = ref(false)

  const customers = computed(() =>
    companies.value.filter(c => c.is_customer)
  )

  const productSuppliers = computed(() =>
    companies.value.filter(c => c.is_product_supplier)
  )

  const rentalSuppliers = computed(() =>
    companies.value.filter(c => c.is_rental_supplier)
  )

  const crewSuppliers = computed(() =>
    companies.value.filter(c => c.is_crew_supplier)
  )

  const allSuppliers = computed(() =>
    companies.value.filter(c => c.is_product_supplier || c.is_rental_supplier || c.is_crew_supplier)
  )

  async function fetchAll(params = {}) {
    loading.value = true
    try {
      const { data } = await api.get('/api/v1/companies', { params })
      companies.value = data?.items ?? data
      await cacheSnapshot('companies.fetchAll', companies.value)
    } catch (error) {
      if (!isOnline()) {
        const cached = await readSnapshot('companies.fetchAll')
        if (Array.isArray(cached)) {
          companies.value = cached
          return
        }
      }
      throw error
    } finally {
      loading.value = false
    }
  }

  async function fetchCompany(id) {
    try {
      const { data } = await api.get(`/api/v1/companies/${id}`)
      return data
    } catch (error) {
      console.error('Failed to fetch company:', error)
      throw error
    }
  }

  async function fetchCompanyInfo(id) {
    try {
      const { data } = await api.get(`/api/v1/companies/${id}/info`)
      return data
    } catch (error) {
      console.error('Failed to fetch company info:', error)
      throw error
    }
  }

  async function createCompany(payload) {
    if (!isOnline()) {
      const optimistic = { id: -Date.now(), ...payload, _offline_queued: true }
      companies.value = [...companies.value, optimistic]
      await queueMutation({ method: 'post', url: '/api/v1/companies', data: payload })
      await cacheSnapshot('companies.fetchAll', companies.value)
      return optimistic
    }
    try {
      const { data } = await api.post('/api/v1/companies', payload)
      companies.value = [...companies.value, data]
      await cacheSnapshot('companies.fetchAll', companies.value)
      return data
    } catch (error) {
      console.error('Failed to create company:', error)
      throw error
    }
  }

  async function updateCompany(id, payload) {
    if (!isOnline()) {
      companies.value = companies.value.map(company => company.id === id ? { ...company, ...payload, _offline_queued: true } : company)
      await queueMutation({ method: 'put', url: `/api/v1/companies/${id}`, data: payload })
      await cacheSnapshot('companies.fetchAll', companies.value)
      return companies.value.find(company => company.id === id) || { id, ...payload, _offline_queued: true }
    }
    try {
      const { data } = await api.put(`/api/v1/companies/${id}`, payload)
      companies.value = companies.value.map(company => company.id === id ? data : company)
      await cacheSnapshot('companies.fetchAll', companies.value)
      return data
    } catch (error) {
      console.error('Failed to update company:', error)
      throw error
    }
  }

  async function deleteCompany(id) {
    if (!isOnline()) {
      companies.value = companies.value.filter(company => company.id !== id)
      await queueMutation({ method: 'delete', url: `/api/v1/companies/${id}` })
      await cacheSnapshot('companies.fetchAll', companies.value)
      return
    }
    try {
      await api.delete(`/api/v1/companies/${id}`)
      companies.value = companies.value.filter(company => company.id !== id)
      await cacheSnapshot('companies.fetchAll', companies.value)
    } catch (error) {
      console.error('Failed to delete company:', error)
      throw error
    }
  }

  return {
    companies,
    loading,
    customers,
    productSuppliers,
    rentalSuppliers,
    crewSuppliers,
    allSuppliers,
    fetchAll,
    fetchCompany,
    fetchCompanyInfo,
    createCompany,
    updateCompany,
    deleteCompany,
  }
})
