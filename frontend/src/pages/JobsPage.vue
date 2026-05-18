<template>
  <q-page class="q-pa-md ec-page">
    <div class="text-h5 q-mb-md">Jobs module</div>
    <q-btn color="primary" label="Reload jobs" @click="store.fetchAll" class="q-mb-md" />
    <q-list bordered separator>
      <q-item v-for="job in store.jobs" :key="job.id">
        <q-item-section>
          <q-item-label>{{ job.job_code }} - {{ job.customer_name }}</q-item-label>
          <q-item-label caption>Status: {{ job.status }}</q-item-label>
        </q-item-section>
      </q-item>
    </q-list>
  </q-page>
</template>

<script setup>
import { onMounted } from 'vue'

import { useJobsStore } from '../stores/jobs'

const store = useJobsStore()

onMounted(() => {
  store.fetchAll()
})
</script>
