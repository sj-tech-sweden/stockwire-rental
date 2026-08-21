import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import MainLayout from '../layouts/MainLayout.vue'
import AuthLayout from '../layouts/AuthLayout.vue'
import LoginPage from '../pages/LoginPage.vue'
import SetupPage from '../pages/SetupPage.vue'

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
    children: [{ path: '', component: () => import('../pages/ForgotPasswordPage.vue') }]
  },
  {
    path: '/reset-password/:token',
    name: 'reset-password',
    component: AuthLayout,
    meta: { public: true },
    children: [{ path: '', component: () => import('../pages/ResetPasswordPage.vue') }]
  },
  {
    path: '/',
    component: MainLayout,
    children: [
      { path: '', component: () => import('../pages/HomePage.vue') },
      { path: 'auth', redirect: '/settings?tab=auth' },
      { path: 'users', component: () => import('../pages/UsersPage.vue') },
      { path: 'inventory', component: () => import('../pages/InventoryPage.vue') },
      { path: 'labels', component: () => import('../pages/LabelsPage.vue') },
      { path: 'scan', component: () => import('../pages/ScanPage.vue') },
      { path: 'maintenance', component: () => import('../pages/MaintenancePage.vue') },
      { path: 'defects', redirect: '/maintenance' },
      { path: 'activity', component: () => import('../pages/ActivityPage.vue') },
      { path: 'jobs', component: () => import('../pages/JobsPage.vue') },
      { path: 'jobs/new', component: () => import('../pages/JobDetailPage.vue') },
      { path: 'jobs/:jobId', component: () => import('../pages/JobDetailPage.vue') },
      { path: 'projects', component: () => import('../pages/ProjectsPage.vue') },
      { path: 'companies', component: () => import('../pages/CompaniesPage.vue') },
      { path: 'companies/new', component: () => import('../pages/CompanyDetailPage.vue') },
      { path: 'companies/:companyId', component: () => import('../pages/CompanyDetailPage.vue') },
      { path: 'persons', component: () => import('../pages/PersonsPage.vue') },
      { path: 'persons/new', component: () => import('../pages/PersonDetailPage.vue') },
      { path: 'persons/:personId', component: () => import('../pages/PersonDetailPage.vue') },
      { path: 'customers', redirect: '/companies' },
      { path: 'customers/new', redirect: '/companies/new' },
      { path: 'customers/:customerId', redirect: to => `/companies/${to.params.customerId}` },
      { path: 'suppliers', redirect: '/companies?tab=product_supplier' },
      { path: 'crew', component: () => import('../pages/CrewPage.vue') },
      { path: 'crew/new', component: () => import('../pages/CrewDetailPage.vue') },
      { path: 'crew/:crewMemberId', component: () => import('../pages/CrewDetailPage.vue') },
      { path: 'venues', component: () => import('../pages/VenuesPage.vue') },
      { path: 'reports', component: () => import('../pages/ReportsPage.vue') },
      { path: 'profile', component: () => import('../pages/ProfilePage.vue') },
      { path: 'settings', component: () => import('../pages/SettingsPage.vue') },
      { path: 'finance', component: () => import('../pages/FinancePage.vue') },
      { path: 'route-planner', component: () => import('../pages/RoutePlannerPage.vue') }
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
