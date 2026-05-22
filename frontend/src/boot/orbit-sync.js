import { api } from './axios'
import {
  flushQueuedMutations,
  initOrbitSync,
  isOnline,
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
  await flushQueue()

  if (typeof window !== 'undefined') {
    window.addEventListener('online', () => {
      void flushQueue()
    })
  }
}
