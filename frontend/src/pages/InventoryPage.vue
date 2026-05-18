<template>
  <q-page class="q-pa-md ec-page">
    <div class="text-h5 q-mb-md">Inventory module</div>
    <q-btn color="primary" label="Reload inventory" @click="store.fetchAll" class="q-mb-md" />
    <q-card class="ec-card q-pa-md q-mb-md">
      <div class="text-subtitle1">Products: {{ store.products.length }}</div>
      <div class="text-subtitle1">Devices: {{ store.devices.length }}</div>
      <div class="text-subtitle1">Zones: {{ store.zones.length }}</div>
    </q-card>
  </q-page>
</template>

<script setup>
import { onMounted } from 'vue'

import { useInventoryStore } from '../stores/inventory'

const store = useInventoryStore()

onMounted(() => {
  store.fetchAll()
})
</script>
