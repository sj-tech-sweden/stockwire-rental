<template>
  <q-page class="q-pa-md ec-page">
    <div class="text-h5 q-mb-md">Auth module</div>
    <q-btn color="primary" label="Reload users" @click="store.fetchUsers" class="q-mb-md" />
    <q-list bordered separator>
      <q-item v-for="user in store.users" :key="user.id">
        <q-item-section>
          <q-item-label>{{ user.full_name }} ({{ user.email }})</q-item-label>
          <q-item-label caption>Admin: {{ user.is_admin }}</q-item-label>
        </q-item-section>
      </q-item>
    </q-list>
  </q-page>
</template>

<script setup>
import { onMounted } from 'vue'

import { useAuthStore } from '../stores/auth'

const store = useAuthStore()

onMounted(() => {
  store.fetchUsers()
})
</script>
