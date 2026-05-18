<template>
  <q-page class="q-pa-md ec-page">
    <div class="text-h5 q-mb-md">Finance module</div>
    <q-btn color="primary" label="Reload transactions" @click="store.fetchTransactions" class="q-mb-md" />
    <q-list bordered separator>
      <q-item v-for="tx in store.transactions" :key="tx.id">
        <q-item-section>
          <q-item-label>{{ tx.transaction_type }} - {{ tx.amount }} {{ tx.currency }}</q-item-label>
          <q-item-label caption>Status: {{ tx.status }}</q-item-label>
        </q-item-section>
      </q-item>
    </q-list>
  </q-page>
</template>

<script setup>
import { onMounted } from 'vue'

import { useFinanceStore } from '../stores/finance'

const store = useFinanceStore()

onMounted(() => {
  store.fetchTransactions()
})
</script>
