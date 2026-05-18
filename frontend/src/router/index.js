import { createRouter, createWebHistory } from 'vue-router'

import MainLayout from '../layouts/MainLayout.vue'
import HomePage from '../pages/HomePage.vue'

const routes = [
  {
    path: '/',
    component: MainLayout,
    children: [{ path: '', component: HomePage }]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
