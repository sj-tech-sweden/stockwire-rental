import { api } from './axios'
import {
  checkBackendReachability,
  flushQueuedMutations,
  initOrbitSync,
  isOnline,
  setBackendReachable,
} from '../services/offline/orbitSync'

async function flushQueue() {
  if (!isOnline()) return
  const token = typeof window !== 'undefined' ? window.localStorage.getItem('sw_token') : null
  if (token && !api.defaults.headers.common['Authorization']) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
  }
  await flushQueuedMutations(async (mutation) => {
    return api.request({
      method: mutation.method,
      url: mutation.url,
      data: mutation.data,
      params: mutation.params,
    })
  })
}

export default async () => {
  await initOrbitSync()

  // Check backend reachability on startup
  await checkBackendReachability()

  await flushQueue()

  if (typeof window !== 'undefined') {
    window.addEventListener('online', async () => {
      // Re-check backend reachability when browser reports online
      await checkBackendReachability()
      void flushQueue()
    })

    window.addEventListener('offline', () => {
      setBackendReachable(false)
    })
  }
}
