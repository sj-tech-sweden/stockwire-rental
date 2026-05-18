import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const getMock = vi.fn()
const postMock = vi.fn()

vi.mock('../src/boot/axios', () => ({
  api: {
    get: (...args) => getMock(...args),
    post: (...args) => postMock(...args)
  }
}))

import { useAuthStore } from '../src/stores/auth'
import { useFinanceStore } from '../src/stores/finance'
import { useInventoryStore } from '../src/stores/inventory'
import { useJobsStore } from '../src/stores/jobs'

describe('stores smoke', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    getMock.mockReset()
    postMock.mockReset()
  })

  it('auth store fetches users', async () => {
    getMock.mockResolvedValueOnce({ data: [{ id: 1, email: 'a@test.local', full_name: 'A', is_admin: true }] })
    const store = useAuthStore()

    await store.fetchUsers()

    expect(getMock).toHaveBeenCalledWith('/api/v1/auth/users')
    expect(store.users).toHaveLength(1)
  })

  it('inventory store fetches products/devices/zones', async () => {
    getMock
      .mockResolvedValueOnce({ data: [{ id: 1 }] })
      .mockResolvedValueOnce({ data: [{ id: 2 }] })
      .mockResolvedValueOnce({ data: [{ id: 3 }] })

    const store = useInventoryStore()
    await store.fetchAll()

    expect(store.products).toHaveLength(1)
    expect(store.devices).toHaveLength(1)
    expect(store.zones).toHaveLength(1)
  })

  it('jobs store fetches jobs and requirements', async () => {
    getMock
      .mockResolvedValueOnce({ data: [{ id: 10 }] })
      .mockResolvedValueOnce({ data: [{ id: 20 }] })

    const store = useJobsStore()
    await store.fetchAll()

    expect(store.jobs).toHaveLength(1)
    expect(store.requirements).toHaveLength(1)
  })

  it('finance store fetches transactions', async () => {
    getMock.mockResolvedValueOnce({ data: [{ id: 100, status: 'pending' }] })
    const store = useFinanceStore()

    await store.fetchTransactions()

    expect(store.transactions).toHaveLength(1)
  })
})
