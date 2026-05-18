<template>
  <q-layout view="hHh lpR fFf" class="ec-layout">
    <q-header elevated class="ec-header">
      <q-toolbar>
        <q-btn
          flat
          dense
          round
          icon="menu"
          aria-label="Menu"
          @click="drawerOpen = !drawerOpen"
        />
        <q-toolbar-title class="ec-title">Stockwire Rental</q-toolbar-title>
        <div v-if="authStore.me" class="row items-center q-gutter-sm">
          <span class="text-caption">{{ authStore.me.full_name }}</span>
          <q-btn flat dense round icon="logout" aria-label="Logout" @click="logout" />
        </div>
      </q-toolbar>
    </q-header>

    <q-drawer
      v-model="drawerOpen"
      side="left"
      bordered
      overlay
      :width="220"
      class="ec-drawer"
    >
      <q-list padding>
        <q-item-label header class="ec-drawer-header">Navigation</q-item-label>

        <q-item clickable v-ripple to="/" exact @click="drawerOpen = false">
          <q-item-section avatar><q-icon name="home" /></q-item-section>
          <q-item-section>Home</q-item-section>
        </q-item>

        <q-item clickable v-ripple to="/auth" @click="drawerOpen = false">
          <q-item-section avatar><q-icon name="manage_accounts" /></q-item-section>
          <q-item-section>Auth</q-item-section>
        </q-item>

        <q-item clickable v-ripple to="/inventory" @click="drawerOpen = false">
          <q-item-section avatar><q-icon name="inventory_2" /></q-item-section>
          <q-item-section>Inventory</q-item-section>
        </q-item>

        <q-item clickable v-ripple to="/jobs" @click="drawerOpen = false">
          <q-item-section avatar><q-icon name="work" /></q-item-section>
          <q-item-section>Jobs</q-item-section>
        </q-item>

        <q-item clickable v-ripple to="/finance" @click="drawerOpen = false">
          <q-item-section avatar><q-icon name="payments" /></q-item-section>
          <q-item-section>Finance</q-item-section>
        </q-item>
      </q-list>
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const drawerOpen = ref(false)
const authStore = useAuthStore()
const router = useRouter()

async function logout() {
  authStore.logout()
  router.push('/login')
}
</script>
