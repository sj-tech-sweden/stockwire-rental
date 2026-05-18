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
        <div class="row items-center q-gutter-sm"> 
          <q-btn
            flat
            round
            :icon="$q.dark.isActive ? 'light_mode' : 'dark_mode'"
            @click="$q.dark.toggle()"
            aria-label="Toggle dark mode"
          />
        </div>
      </q-toolbar>
    </q-header>

    <q-drawer
      v-model="drawerOpen"
      side="left"
      bordered
      :width="220"
      class="ec-drawer"
    >
      <q-scroll-area class="fit">
        <q-list padding>
          <q-item-label header class="ec-drawer-header">Navigation</q-item-label>

          <template v-for="(item, idx) in menuList" :key="idx">
            <q-item
              clickable
              v-ripple
              :to="item.to"
              @click="onNavigate(item)">
              <q-item-section avatar>
                <q-icon :name="item.icon" class="text-primary" />
              </q-item-section>
              <q-item-section :class="$q.dark.isActive ? 'text-grey-3' : 'text-grey-8'">
                {{ item.label }}
              </q-item-section>
            </q-item>
            <q-separator v-if="item.separator" :key="'sep-'+idx" />
          </template>
        </q-list>
      </q-scroll-area>
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { ref } from 'vue'
import { useQuasar } from 'quasar'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const drawerOpen = ref(false)
const authStore = useAuthStore()
const router = useRouter()
const $q = useQuasar()

async function logout() {
  authStore.logout()
  router.push('/login')
}

const menuList = [
  { icon: 'home', label: 'Home', to: '/', separator: true },
  { icon: 'manage_accounts', label: 'Auth', to: '/auth', separator: false },
  { icon: 'inventory_2', label: 'Inventory', to: '/inventory', separator: false },
  { icon: 'work', label: 'Jobs', to: '/jobs', separator: false },
  { icon: 'payments', label: 'Finance', to: '/finance', separator: false }
]

function onNavigate(item) {
  drawerOpen.value = false
  if (item.to) router.push(item.to)
}
</script>
