import { useActivityStore } from '../stores/activity'
import { useCompaniesStore } from '../stores/companies'
import { useCrewStore } from '../stores/crew'
import { useInventoryStore } from '../stores/inventory'
import { useJobsStore } from '../stores/jobs'
import { usePurchasingStore } from '../stores/purchasing'
import { useRoutePlannerStore } from '../stores/routePlanner'
import { useVenuesStore } from '../stores/venues'
import { useWarehouseLedsStore } from '../stores/warehouseLeds'
import { useNotificationsStore } from '../stores/notifications'
import { useFinanceStore } from '../stores/finance'
import { startRealtime, subscribeRealtime } from '../services/realtime/client'
import { getApiBaseUrl } from '../utils/runtime-config'

function debounce(fn, waitMs = 350) {
  let timer = null
  return (...args) => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      timer = null
      fn(...args)
    }, waitMs)
  }
}

export default ({ store }) => {
  const apiBase = getApiBaseUrl()

  startRealtime({
    apiBase,
    tokenProvider: () => localStorage.getItem('sw_token') || '',
  })

  const inventoryStore = useInventoryStore(store)
  const jobsStore = useJobsStore(store)
  const companiesStore = useCompaniesStore(store)
  const venuesStore = useVenuesStore(store)
  const crewStore = useCrewStore(store)
  const purchasingStore = usePurchasingStore(store)
  const routePlannerStore = useRoutePlannerStore(store)
  const warehouseLedsStore = useWarehouseLedsStore(store)
  const notificationsStore = useNotificationsStore(store)
  const financeStore = useFinanceStore(store)
  const activityStore = useActivityStore(store)

  const refreshCrew = debounce(async () => {
    // Crew has no single fetchAll(); re-fetch every collection that the
    // `crew.updated` event may have changed, then bump the revision so
    // dependent views (quote builder, job crew panels) refresh too.
    await Promise.allSettled([
      crewStore.fetchRoles(),
      crewStore.fetchMembers(),
      crewStore.fetchSkills(),
      crewStore.fetchCertifications(),
    ])
    crewStore.crewRevision++
  })

  const refreshPurchasing = debounce(async () => {
    await Promise.allSettled([purchasingStore.fetchPurchaseOrders()])
  })

  const refreshRoutePlanner = debounce(async () => {
    await Promise.allSettled([
      routePlannerStore.fetchVehicles(),
      routePlannerStore.fetchRoutes(),
    ])
  })

  const refreshWarehouseLeds = debounce(async () => {
    await Promise.allSettled([
      warehouseLedsStore.fetchControllers(),
      warehouseLedsStore.fetchMappings(),
    ])
  })

  const refreshNotifications = debounce(async () => {
    await Promise.allSettled([
      notificationsStore.fetchPreferences(),
      notificationsStore.fetchTemplates(),
      notificationsStore.fetchMyPreferences(),
    ])
  })

  const refreshFinance = debounce(async () => {
    await Promise.allSettled([
      financeStore.fetchTransactions(),
      financeStore.fetchSummary(),
      financeStore.fetchJobInsights(),
    ])
  })

  const refreshInventory = debounce(async () => {
    await Promise.allSettled([
      inventoryStore.fetchAll(),
      inventoryStore.fetchAuditLogs(80),
    ])
  })

  const refreshJobs = debounce(async () => {
    await Promise.allSettled([jobsStore.fetchAll()])
  })

  const refreshActivity = debounce(async () => {
    await Promise.allSettled([activityStore.fetchLogs(120)])
  })

  const refreshCompanies = debounce(async () => {
    await Promise.allSettled([companiesStore.fetchAll()])
  })

  const refreshVenues = debounce(async () => {
    await Promise.allSettled([venuesStore.fetchAll()])
  })

  subscribeRealtime((event) => {
    const topic = String(event?.topic || '')
    if (!topic) return

    if (topic.startsWith('inventory.')) refreshInventory()
    if (topic.startsWith('jobs.')) refreshJobs()
    if (topic.startsWith('companies.')) refreshCompanies()
    if (topic.startsWith('venues.')) refreshVenues()
    if (topic.startsWith('crew.')) refreshCrew()
    if (topic.startsWith('purchasing.')) refreshPurchasing()
    if (topic.startsWith('route_planner.')) refreshRoutePlanner()
    if (topic.startsWith('warehouse_leds.')) refreshWarehouseLeds()
    if (topic.startsWith('notifications.')) refreshNotifications()
    if (topic.startsWith('finance.')) refreshFinance()
    if (
      topic.startsWith('activity.')
      || topic.startsWith('inventory.')
      || topic.startsWith('jobs.')
      || topic.startsWith('companies.')
      || topic.startsWith('venues.')
    ) {
      refreshActivity()
    }
  })
}
