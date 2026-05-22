import { useActivityStore } from '../stores/activity'
import { useCustomersStore } from '../stores/customers'
import { useInventoryStore } from '../stores/inventory'
import { useJobsStore } from '../stores/jobs'
import { useVenuesStore } from '../stores/venues'
import { startRealtime, subscribeRealtime } from '../services/realtime/client'

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
  const apiBase = import.meta.env.VITE_API_BASE_URL || window.location.origin

  startRealtime({
    apiBase,
    tokenProvider: () => localStorage.getItem('sw_token') || '',
  })

  const inventoryStore = useInventoryStore(store)
  const jobsStore = useJobsStore(store)
  const customersStore = useCustomersStore(store)
  const venuesStore = useVenuesStore(store)
  const activityStore = useActivityStore(store)

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

  const refreshCustomers = debounce(async () => {
    await Promise.allSettled([customersStore.fetchAll()])
  })

  const refreshVenues = debounce(async () => {
    await Promise.allSettled([venuesStore.fetchAll()])
  })

  subscribeRealtime((event) => {
    const topic = String(event?.topic || '')
    if (!topic) return

    if (topic.startsWith('inventory.')) refreshInventory()
    if (topic.startsWith('jobs.')) refreshJobs()
    if (topic.startsWith('customers.')) refreshCustomers()
    if (topic.startsWith('venues.')) refreshVenues()
    if (
      topic.startsWith('activity.')
      || topic.startsWith('inventory.')
      || topic.startsWith('jobs.')
      || topic.startsWith('customers.')
      || topic.startsWith('venues.')
    ) {
      refreshActivity()
    }
  })
}
