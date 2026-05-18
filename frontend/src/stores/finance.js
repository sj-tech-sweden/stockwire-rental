import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '../boot/axios'

export const useFinanceStore = defineStore('finance', () => {
  const transactions = ref([])
  const loading = ref(false)

  async function fetchTransactions() {
    loading.value = true
    try {
      const { data } = await api.get('/api/v1/finance/transactions')
      transactions.value = data
    } finally {
      loading.value = false
    }
  }

  return { transactions, loading, fetchTransactions }
})
