import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import MainLayout from '../layouts/MainLayout.vue'
import CustomersPage from '../pages/CustomersPage.vue'
import FinancePage from '../pages/FinancePage.vue'
import ActivityPage from '../pages/ActivityPage.vue'
import HomePage from '../pages/HomePage.vue'
import InventoryPage from '../pages/InventoryPage.vue'
import JobsPage from '../pages/JobsPage.vue'
import LabelsPage from '../pages/LabelsPage.vue'
import ScanPage from '../pages/ScanPage.vue'
import SettingsPage from '../pages/SettingsPage.vue'
import VenuesPage from '../pages/VenuesPage.vue'
import AuthLayout from '../layouts/AuthLayout.vue'
import LoginPage from '../pages/LoginPage.vue'
import SetupPage from '../pages/SetupPage.vue'
import ForgotPasswordPage from '../pages/ForgotPasswordPage.vue'
import ResetPasswordPage from '../pages/ResetPasswordPage.vue'
import ProfilePage from '../pages/ProfilePage.vue'

const routes = [
  {
    path: '/auth',
    redirect: '/settings?tab=auth',
  },
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
    path: '/forgot-password',
    name: 'forgot-password',
    component: AuthLayout,
    meta: { public: true },
    children: [{ path: '', component: ForgotPasswordPage }]
  },
  {
    path: '/reset-password/:token',
    name: 'reset-password',
    component: AuthLayout,
    meta: { public: true },
    children: [{ path: '', component: ResetPasswordPage }]
  },
  {
    path: '/',
    component: MainLayout,
    children: [
      { path: '', component: HomePage },
      { path: 'auth', redirect: '/settings?tab=auth' },
      { path: 'users', component: () => import('../pages/UsersPage.vue') },
      { path: 'inventory', component: InventoryPage },
      { path: 'labels', component: LabelsPage },
      { path: 'scan', component: ScanPage },
      { path: 'activity', component: ActivityPage },
      { path: 'jobs', component: JobsPage },
      { path: 'jobs/:jobId', component: () => import('../pages/JobDetailPage.vue') },
      { path: 'projects', component: () => import('../pages/ProjectsPage.vue') },
      { path: 'defects', component: () => import('../pages/DefectsPage.vue') },
      { path: 'customers', component: CustomersPage },
      { path: 'venues', component: VenuesPage },
      { path: 'profile', component: ProfilePage },
      { path: 'settings', component: SettingsPage },
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
    sessionStorage.setItem('sw_login_redirect', to.fullPath)
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (to.path.startsWith('/settings') && !authStore.canManageSettings) {
    return '/jobs'
  }

  return true
})

export default router
