<template>
  <q-page class="q-pa-md ec-page">
    <div class="text-h5 q-mb-md">Unified Operations Dashboard</div>
    <q-card class="ec-card q-pa-md">
      <div class="text-subtitle1 q-mb-sm">Platform status</div>
      <div class="q-mb-sm">Backend health: <strong>{{ status }}</strong></div>
      <q-btn color="primary" label="Refresh health" @click="loadHealth" />
    </q-card>
  </q-page>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import axios from 'axios'

const status = ref('unknown')

async function loadHealth() {
  try {
    const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    const response = await axios.get(`${base}/api/v1/health/live`)
    status.value = response.data.status || 'ok'
  } catch (error) {
    status.value = 'unreachable'
  }
}

onMounted(loadHealth)
</script>
