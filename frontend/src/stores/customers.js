import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api } from '../boot/axios'
import { cacheSnapshot, isOnline, queueMutation, readSnapshot } from '../services/offline/orbitSync'

export const useCustomersStore = defineStore('customers', () => {
  const customers = ref([])
  const loading = ref(false)

  const productSuppliers = computed(() =>
    customers.value.filter(c => c.is_product_supplier)
  )

  const rentalSuppliers = computed(() =>
    customers.value.filter(c => c.is_rental_supplier)
  )

  const crewSuppliers = computed(() =>
    customers.value.filter(c => c.is_crew_supplier)
  )

  const allSuppliers = computed(() =>
    customers.value.filter(c => c.is_product_supplier || c.is_rental_supplier || c.is_crew_supplier)
  )

  async function fetchAll() {
    loading.value = true
    try {
      const { data } = await api.get('/api/v1/customers')
      customers.value = data?.items ?? data
      await cacheSnapshot('customers.fetchAll', customers.value)
    } catch (error) {
      if (!isOnline()) {
        const cached = await readSnapshot('customers.fetchAll')
        if (Array.isArray(cached)) {
          customers.value = cached
          return
        }
      }
      throw error
    } finally {
      loading.value = false
    }
  }

  async function createCustomer(payload) {
    if (!isOnline()) {
      const optimistic = { id: -Date.now(), ...payload, _offline_queued: true }
      customers.value = [...customers.value, optimistic]
      await queueMutation({ method: 'post', url: '/api/v1/customers', data: payload })
      await cacheSnapshot('customers.fetchAll', customers.value)
      return optimistic
    }
    try {
      const { data } = await api.post('/api/v1/customers', payload)
      customers.value = [...customers.value, data]
      await cacheSnapshot('customers.fetchAll', customers.value)
      return data
    } catch (error) {
      console.error('Failed to create customer:', error)
      throw error
    }
  }

  async function updateCustomer(id, payload) {
    if (!isOnline()) {
      customers.value = customers.value.map(customer => customer.id === id ? { ...customer, ...payload, _offline_queued: true } : customer)
      await queueMutation({ method: 'put', url: `/api/v1/customers/${id}`, data: payload })
      await cacheSnapshot('customers.fetchAll', customers.value)
      return customers.value.find(customer => customer.id === id) || { id, ...payload, _offline_queued: true }
    }
    try {
      const { data } = await api.put(`/api/v1/customers/${id}`, payload)
      customers.value = customers.value.map(customer => customer.id === id ? data : customer)
      await cacheSnapshot('customers.fetchAll', customers.value)
      return data
    } catch (error) {
      console.error('Failed to update customer:', error)
      throw error
    }
  }

  async function deleteCustomer(id) {
    if (!isOnline()) {
      customers.value = customers.value.filter(customer => customer.id !== id)
      await queueMutation({ method: 'delete', url: `/api/v1/customers/${id}` })
      await cacheSnapshot('customers.fetchAll', customers.value)
      return
    }
    try {
      await api.delete(`/api/v1/customers/${id}`)
      customers.value = customers.value.filter(customer => customer.id !== id)
      await cacheSnapshot('customers.fetchAll', customers.value)
    } catch (error) {
      console.error('Failed to delete customer:', error)
      throw error
    }
  }

  async function fetchCustomerInfo(id) {
    try {
      const { data } = await api.get(`/api/v1/customers/${id}/info`)
      return data
    } catch (error) {
      console.error('Failed to fetch customer info:', error)
      throw error
    }
  }

  return {
    customers,
    loading,
    productSuppliers,
    rentalSuppliers,
    crewSuppliers,
    allSuppliers,
    fetchAll,
    fetchCustomerInfo,
    createCustomer,
    updateCustomer,
    deleteCustomer,
  }
})
