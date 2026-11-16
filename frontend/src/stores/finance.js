import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '../boot/axios'
import {
  cacheSnapshot,
  isOnline,
  queueMutation,
  readSnapshot,
} from '../services/offline/orbitSync'

export const useFinanceStore = defineStore('finance', () => {
  const transactions = ref([])
  const summary = ref({
    currency: 'SEK',
    total_transactions: 0,
    pending_count: 0,
    overdue_count: 0,
    completed_count: 0,
    pending_amount: '0.00',
    overdue_amount: '0.00',
    completed_amount: '0.00',
    warehouse_products_value: '0.00',
    warehouse_devices_value: '0.00',
    warehouse_total_value: '0.00',
  })
  const jobInsights = ref({
    jobs_total: 0,
    jobs_active: 0,
    jobs_completed: 0,
    jobs_cancelled: 0,
    projected_total_value: '0.00',
    projected_active_value: '0.00',
    projected_completed_value: '0.00',
    sales_total_value: '0.00',
    sales_paid_value: '0.00',
    sales_unpaid_value: '0.00',
    invoice_paid_jobs: 0,
    invoice_unpaid_jobs: 0,
    transaction_total: '0.00',
    collected_total: '0.00',
    top_jobs: [],
  })
  const loading = ref(false)
  const summaryLoading = ref(false)
  const jobInsightsLoading = ref(false)

  // Mirror stores/inventory.js: persist/restore this store's collections so
  // they survive an offline reload (cacheSnapshot/readSnapshot from orbitSync).
  async function persistFetchAllSnapshot() {
    await cacheSnapshot('finance.fetchAll', {
      transactions: transactions.value,
      summary: summary.value,
      jobInsights: jobInsights.value,
    })
  }

  async function restoreFetchAllSnapshot() {
    const cached = await readSnapshot('finance.fetchAll')
    if (!cached || typeof cached !== 'object') return false
    transactions.value = Array.isArray(cached.transactions) ? cached.transactions : transactions.value
    summary.value = cached.summary && typeof cached.summary === 'object' ? cached.summary : summary.value
    jobInsights.value = cached.jobInsights && typeof cached.jobInsights === 'object' ? cached.jobInsights : jobInsights.value
    return true
  }

  async function fetchTransactions(filters = {}) {
    loading.value = true
    try {
      const params = {}
      if (filters.status) params.status = filters.status
      if (filters.transaction_type) params.transaction_type = filters.transaction_type
      if (filters.job_id) params.job_id = filters.job_id
      if (filters.customer_name) params.customer_name = filters.customer_name
      if (filters.from_date) params.from_date = filters.from_date
      if (filters.to_date) params.to_date = filters.to_date
      if (filters.overdue_only) params.overdue_only = true

      const { data } = await api.get('/api/v1/finance/transactions', { params })
      transactions.value = data
      await cacheSnapshot('finance.transactions', data)
    } catch (error) {
      if (!isOnline()) {
        const cached = await readSnapshot('finance.transactions')
        if (Array.isArray(cached)) {
          transactions.value = cached
          return
        }
      }
      throw error
    } finally {
      loading.value = false
    }
  }

  async function fetchSummary() {
    summaryLoading.value = true
    try {
      const { data } = await api.get('/api/v1/finance/summary')
      summary.value = data
      await cacheSnapshot('finance.summary', data)
    } catch (error) {
      if (!isOnline()) {
        const cached = await readSnapshot('finance.summary')
        if (cached && typeof cached === 'object') {
          summary.value = cached
          return
        }
      }
      throw error
    } finally {
      summaryLoading.value = false
    }
  }

  async function fetchJobInsights() {
    jobInsightsLoading.value = true
    try {
      const { data } = await api.get('/api/v1/finance/job-insights')
      jobInsights.value = data
      await cacheSnapshot('finance.jobInsights', data)
    } catch (error) {
      if (!isOnline()) {
        const cached = await readSnapshot('finance.jobInsights')
        if (cached && typeof cached === 'object') {
          jobInsights.value = cached
          return
        }
      }
      throw error
    } finally {
      jobInsightsLoading.value = false
    }
  }

  async function createTransaction(payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'post', url: '/api/v1/finance/transactions', data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.post('/api/v1/finance/transactions', payload)
    await persistFetchAllSnapshot()
    return data
  }

  async function updateTransaction(id, payload) {
    if (!isOnline()) {
      await queueMutation({ method: 'put', url: `/api/v1/finance/transactions/${id}`, data: payload })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.put(`/api/v1/finance/transactions/${id}`, payload)
    await persistFetchAllSnapshot()
    return data
  }

  async function settleTransaction(id) {
    if (!isOnline()) {
      await queueMutation({ method: 'post', url: `/api/v1/finance/transactions/${id}/settle` })
      await persistFetchAllSnapshot()
      return
    }
    const { data } = await api.post(`/api/v1/finance/transactions/${id}/settle`)
    await persistFetchAllSnapshot()
    return data
  }

  async function deleteTransaction(id) {
    if (!isOnline()) {
      await queueMutation({ method: 'delete', url: `/api/v1/finance/transactions/${id}` })
      await persistFetchAllSnapshot()
      return
    }
    await api.delete(`/api/v1/finance/transactions/${id}`)
    await persistFetchAllSnapshot()
  }

  return {
    transactions,
    summary,
    jobInsights,
    loading,
    summaryLoading,
    jobInsightsLoading,
    fetchTransactions,
    fetchSummary,
    fetchJobInsights,
    createTransaction,
    updateTransaction,
    settleTransaction,
    deleteTransaction,
    persistFetchAllSnapshot,
    restoreFetchAllSnapshot,
  }
})
