import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import MainLayout from '../layouts/MainLayout.vue'
import AuthPage from '../pages/AuthPage.vue'
import FinancePage from '../pages/FinancePage.vue'
import HomePage from '../pages/HomePage.vue'
import InventoryPage from '../pages/InventoryPage.vue'
import JobsPage from '../pages/JobsPage.vue'
import AuthLayout from '../layouts/AuthLayout.vue'
import LoginPage from '../pages/LoginPage.vue'
import SetupPage from '../pages/SetupPage.vue'

const routes = [
  {
    path: '/login',
    component: AuthLayout,
    meta: { public: true },
    children: [{ path: '', component: LoginPage }]
  },
  {
    path: '/setup',
    component: AuthLayout,
    meta: { public: true },
    children: [{ path: '', component: SetupPage }]
  },
  {
    path: '/',
    component: MainLayout,
    children: [
      { path: '', component: HomePage },
      { path: 'auth', component: AuthPage },
      { path: 'inventory', component: InventoryPage },
      { path: 'jobs', component: JobsPage },
      { path: 'finance', component: FinancePage }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to) => {
  if (to.meta.public) return true

  const authStore = useAuthStore()
  if (!authStore.isAuthenticated) {
    try {
      const setupNeeded = await authStore.checkBootstrap()
      if (setupNeeded) return '/setup'
    } catch {
      // If backend unreachable, go to login anyway
    }
    return '/login'
  }

  return true
})

export default router
