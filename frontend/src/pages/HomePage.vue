<template>
  <q-page class="q-pa-md ec-page">
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">{{ t('home.title') }}</div>
      <q-btn color="primary" icon="refresh" :label="t('home.refresh')" unelevated :loading="loading" @click="loadDashboard" />
    </div>

    <div class="row q-col-gutter-sm q-mb-md">
      <div class="col-12 col-sm-6 col-md-3">
        <q-card class="ec-card q-pa-md cursor-pointer" clickable @click="openSettingsPage">
          <div class="text-caption text-grey-6">{{ t('home.backendHealth') }}</div>
          <div class="text-h6">{{ status }}</div>
        </q-card>
      </div>
      <div class="col-12 col-sm-6 col-md-3">
        <q-card class="ec-card q-pa-md cursor-pointer" clickable @click="openInventoryTab('products')">
          <div class="text-caption text-grey-6">{{ t('home.products') }}</div>
          <div class="text-h6">{{ store.products.length }}</div>
        </q-card>
      </div>
      <div class="col-12 col-sm-6 col-md-3">
        <q-card class="ec-card q-pa-md cursor-pointer" clickable @click="openInventoryDevices()">
          <div class="text-caption text-grey-6">{{ t('home.devices') }}</div>
          <div class="text-h6">{{ store.devices.length }}</div>
        </q-card>
      </div>
      <div class="col-12 col-sm-6 col-md-3">
        <q-card class="ec-card q-pa-md cursor-pointer" clickable @click="openInventoryDevices('in_use')">
          <div class="text-caption text-grey-6">{{ t('home.checkedOutDevices') }}</div>
          <div class="text-h6">{{ store.checkedOutDevices.length }}</div>
        </q-card>
      </div>
    </div>

    <div class="row q-col-gutter-sm q-mb-md">
      <div class="col-12 col-sm-6 col-md-3">
        <q-card class="ec-card q-pa-md cursor-pointer" clickable @click="openInventoryDevices('available')">
          <div class="text-caption text-grey-6">{{ t('home.availableDevices') }}</div>
          <div class="text-h6 text-positive">{{ availableDevices }}</div>
        </q-card>
      </div>
      <div class="col-12 col-sm-6 col-md-3">
        <q-card class="ec-card q-pa-md cursor-pointer" clickable @click="openInventoryDevices('in_use')">
          <div class="text-caption text-grey-6">{{ t('home.inUseDevices') }}</div>
          <div class="text-h6 text-info">{{ inUseDevices }}</div>
        </q-card>
      </div>
      <div class="col-12 col-sm-6 col-md-3">
        <q-card class="ec-card q-pa-md cursor-pointer" clickable @click="openInventoryDevices('maintenance')">
          <div class="text-caption text-grey-6">{{ t('home.maintenanceDevices') }}</div>
          <div class="text-h6 text-negative">{{ maintenanceDevices }}</div>
        </q-card>
      </div>
      <div class="col-12 col-sm-6 col-md-3">
        <q-card class="ec-card q-pa-md cursor-pointer" clickable @click="openJobsPage">
          <div class="text-caption text-grey-6">{{ t('home.activeJobs') }}</div>
          <div class="text-h6 text-warning">{{ activeJobs }}</div>
        </q-card>
      </div>
    </div>

    <div class="row q-col-gutter-sm q-mb-md">
      <div class="col-12 col-md-6">
        <q-card class="ec-card q-pa-md full-height">
          <div class="row items-center q-mb-sm">
            <div class="text-subtitle1 col">{{ t('home.lowAvailabilityProducts') }}</div>
            <q-badge color="negative" text-color="white" :label="String(lowAvailabilityProducts.length)" />
          </div>
          <q-list dense separator>
            <q-item v-for="item in lowAvailabilityProducts" :key="item.id" clickable @click="openProduct(item.id)">
              <q-item-section>
                <q-item-label>{{ item.sku || `Product #${item.id}` }} · {{ item.name || '-' }}</q-item-label>
                <q-item-label caption>
                  {{ t('home.availableOfTotal', { available: item.available, total: item.operationalTotal, threshold: item.threshold }) }}
                </q-item-label>
              </q-item-section>
            </q-item>
            <q-item v-if="!lowAvailabilityProducts.length">
              <q-item-section>
                <q-item-label caption>{{ t('home.noLowAvailability') }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>
      </div>

      <div class="col-12 col-md-6">
        <q-card class="ec-card q-pa-md full-height">
          <div class="row items-center q-mb-sm">
            <div class="text-subtitle1 col">{{ t('home.jobsStartingThisWeek') }}</div>
            <q-badge color="warning" text-color="black" :label="String(jobsStartingThisWeek.length)" />
          </div>
          <q-list dense separator>
            <q-item v-for="job in jobsStartingThisWeek" :key="job.id" clickable @click="openJob(job.id)">
              <q-item-section>
                <q-item-label>{{ job.job_code || `Job #${job.id}` }}</q-item-label>
                <q-item-label caption>{{ job.start_date || '-' }} · {{ job.status || '-' }}</q-item-label>
              </q-item-section>
            </q-item>
            <q-item v-if="!jobsStartingThisWeek.length">
              <q-item-section>
                <q-item-label caption>{{ t('home.noJobsThisWeek') }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>
      </div>
    </div>

    <div class="row q-col-gutter-sm">
      <div class="col-12 col-md-6">
        <q-card class="ec-card q-pa-md full-height cursor-pointer" clickable @click="openJobsPage">
          <div class="text-subtitle1 q-mb-sm">{{ t('home.jobsOverview') }}</div>
          <div class="row q-col-gutter-sm">
            <div class="col-6"><q-badge class="cursor-pointer" color="grey-7" text-color="white" :label="t('home.jobStateDraft', { count: draftJobs })" @click.stop="openJobsPage('draft')" /></div>
            <div class="col-6"><q-badge class="cursor-pointer" color="info" text-color="white" :label="t('home.jobStateConfirmed', { count: confirmedJobs })" @click.stop="openJobsPage('confirmed')" /></div>
            <div class="col-6"><q-badge class="cursor-pointer" color="warning" text-color="black" :label="t('home.jobStateInProgress', { count: inProgressJobs })" @click.stop="openJobsPage('in_progress')" /></div>
            <div class="col-6"><q-badge class="cursor-pointer" color="positive" text-color="white" :label="t('home.jobStateCompleted', { count: completedJobs })" @click.stop="openJobsPage('completed')" /></div>
          </div>

          <div class="text-subtitle2 q-mt-md q-mb-xs">{{ t('home.upcomingJobs') }}</div>
          <q-list dense separator>
            <q-item v-for="job in upcomingJobs" :key="job.id" clickable @click.stop="openJob(job.id)">
              <q-item-section>
                <q-item-label>{{ job.job_code || `Job #${job.id}` }}</q-item-label>
                <q-item-label caption>
                  {{ job.start_date || '-' }} to {{ job.end_date || '-' }} · {{ job.status || '-' }}
                </q-item-label>
              </q-item-section>
            </q-item>
            <q-item v-if="!upcomingJobs.length">
              <q-item-section>
                <q-item-label caption>{{ t('home.noUpcomingJobs') }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>
      </div>

      <div class="col-12 col-md-6">
        <q-card class="ec-card q-pa-md full-height">
          <div class="text-subtitle1 q-mb-sm">{{ t('home.recentScanActivity') }}</div>
          <q-list dense separator>
            <q-item v-for="item in recentScanActivity" :key="item.id" clickable @click="openScanActivityTarget(item)">
              <q-item-section>
                <q-item-label>{{ item.message || item.action }}</q-item-label>
                <q-item-label caption>
                  {{ item.action }} · {{ item.scan_code || t('home.manual') }} · {{ formatDateTime(item.created_at) }}
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-badge :color="item.success ? 'positive' : 'negative'" :label="item.success ? t('home.ok') : t('home.failed')" />
              </q-item-section>
            </q-item>
            <q-item v-if="!recentScanActivity.length">
              <q-item-section>
                <q-item-label caption>{{ t('home.noRecentScanActivity') }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import { api } from '../boot/axios'
import { useInventoryStore } from '../stores/inventory'
import { useJobsStore } from '../stores/jobs'
import { dashboardJobRoute, dashboardProductRoute, dashboardScanRoute } from '../utils/dashboard-links'

const { t } = useI18n()
const router = useRouter()
const status = ref('unknown')
const loading = ref(false)
const store = useInventoryStore()
const jobsStore = useJobsStore()

const availableDevices = computed(() => store.devices.filter(item => String(item.status || '').toLowerCase() === 'available').length)
const inUseDevices = computed(() => store.devices.filter(item => String(item.status || '').toLowerCase() === 'in_use').length)
const maintenanceDevices = computed(() => store.devices.filter(item => String(item.status || '').toLowerCase() === 'maintenance').length)

const activeJobs = computed(() => jobsStore.jobs.filter(item => {
  const statusValue = String(item.status || '').toLowerCase()
  return statusValue === 'confirmed' || statusValue === 'in_progress'
}).length)

const draftJobs = computed(() => jobsStore.jobs.filter(item => String(item.status || '').toLowerCase() === 'draft').length)
const confirmedJobs = computed(() => jobsStore.jobs.filter(item => String(item.status || '').toLowerCase() === 'confirmed').length)
const inProgressJobs = computed(() => jobsStore.jobs.filter(item => String(item.status || '').toLowerCase() === 'in_progress').length)
const completedJobs = computed(() => jobsStore.jobs.filter(item => String(item.status || '').toLowerCase() === 'completed').length)

const lowAvailabilityProducts = computed(() => {
  const byProduct = new Map()

  for (const device of store.devices || []) {
    const productId = device.product_id
    if (!productId) continue
    if (!byProduct.has(productId)) {
      byProduct.set(productId, { operationalTotal: 0, available: 0 })
    }
    const counters = byProduct.get(productId)
    const condition = String(device.condition || '').toLowerCase()
    const statusValue = String(device.status || '').toLowerCase()
    const retired = Boolean(device.retire_date) && normalizeYmd(device.retire_date) <= toYmd(new Date())

    if (retired || condition === 'damaged' || statusValue === 'maintenance') continue
    counters.operationalTotal += 1
    if (statusValue === 'available') counters.available += 1
  }

  return store.products
    .map(product => {
      const counters = byProduct.get(product.id) || { operationalTotal: 0, available: 0 }
      const threshold = Math.max(1, Math.floor(Number(counters.operationalTotal || 0) * 0.2))
      return {
        id: product.id,
        sku: product.sku,
        name: product.name,
        available: Number(counters.available || 0),
        operationalTotal: Number(counters.operationalTotal || 0),
        threshold,
      }
    })
    .filter(item => item.operationalTotal > 0 && item.available <= item.threshold)
    .sort((a, b) => (a.available - b.available) || (a.operationalTotal - b.operationalTotal) || String(a.sku || '').localeCompare(String(b.sku || '')))
    .slice(0, 8)
})

const jobsStartingThisWeek = computed(() => {
  const now = new Date()
  const start = startOfWeek(now)
  const end = new Date(start)
  end.setDate(start.getDate() + 6)
  const startYmd = toYmd(start)
  const endYmd = toYmd(end)

  return [...jobsStore.jobs]
    .filter(job => {
      const startDate = normalizeYmd(job.start_date)
      if (!startDate) return false
      return startDate >= startYmd && startDate <= endYmd
    })
    .sort((a, b) => String(a.start_date || '').localeCompare(String(b.start_date || '')))
    .slice(0, 8)
})

const upcomingJobs = computed(() => {
  const today = new Date()
  const todayYmd = toYmd(today)
  return [...jobsStore.jobs]
    .filter(item => {
      const start = normalizeYmd(item.start_date)
      return start && start >= todayYmd
    })
    .sort((a, b) => String(a.start_date || '').localeCompare(String(b.start_date || '')))
    .slice(0, 6)
})

const recentScanActivity = computed(() => {
  return (store.auditLogs || [])
    .filter(item => Boolean(item.scan_code) || ['lookup', 'move', 'job_in', 'job_out', 'maintenance'].includes(String(item.action || '').toLowerCase()))
    .slice(0, 8)
})

async function loadHealth() {
  try {
    const response = await api.get('/api/v1/health/live')
    status.value = response.data.status || 'ok'
  } catch {
    status.value = t('home.unreachable')
  }
}

function normalizeYmd(value) {
  if (!value) return ''
  return String(value).slice(0, 10)
}

function toYmd(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function startOfWeek(date) {
  const result = new Date(date)
  const day = result.getDay()
  const diff = day === 0 ? -6 : 1 - day
  result.setHours(0, 0, 0, 0)
  result.setDate(result.getDate() + diff)
  return result
}

function formatDateTime(value) {
  if (!value) return '-'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return String(value)
  return parsed.toLocaleString()
}

async function openSettingsPage() {
  await router.push({ path: '/settings' })
}

async function openInventoryTab(tab) {
  await router.push({ path: '/inventory', query: { tab } })
}

async function openInventoryDevices(deviceStatus = '') {
  const query = { tab: 'devices' }
  if (deviceStatus) query.deviceStatus = deviceStatus
  await router.push({ path: '/inventory', query })
}

async function openJobsPage(status = '') {
  const query = {}
  if (status) query.status = status
  await router.push({ path: '/jobs', query })
}

async function openJob(jobId) {
  const route = dashboardJobRoute(jobId)
  if (!route) return
  await router.push(route)
}

async function openProduct(productId) {
  const route = dashboardProductRoute(productId)
  if (!route) return
  await router.push(route)
}

async function openScanActivityTarget(item) {
  await router.push(dashboardScanRoute(item))
}

async function loadDashboard() {
  loading.value = true
  try {
    await Promise.all([
      loadHealth(),
      store.fetchAll(),
      jobsStore.fetchAll(),
      store.fetchCheckedOutDevices(),
      store.fetchAuditLogs(80),
    ])
  } finally {
    loading.value = false
  }
}

onMounted(loadDashboard)
</script>
