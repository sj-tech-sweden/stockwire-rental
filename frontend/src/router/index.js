import { createRouter, createWebHistory } from 'vue-router'

import MainLayout from '../layouts/MainLayout.vue'
import AuthPage from '../pages/AuthPage.vue'
import FinancePage from '../pages/FinancePage.vue'
import HomePage from '../pages/HomePage.vue'
import InventoryPage from '../pages/InventoryPage.vue'
import JobsPage from '../pages/JobsPage.vue'

const routes = [
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

export default router
