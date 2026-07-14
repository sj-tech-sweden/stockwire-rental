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
import { useProjectsStore } from '../src/stores/projects'

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

  it('finance store fetches summary including warehouse values', async () => {
    getMock.mockResolvedValueOnce({
      data: {
        currency: 'SEK',
        total_transactions: 1,
        pending_count: 0,
        overdue_count: 0,
        completed_count: 1,
        pending_amount: '0.00',
        overdue_amount: '0.00',
        completed_amount: '1200.00',
        warehouse_products_value: '2500.00',
        warehouse_devices_value: '5000.00',
        warehouse_total_value: '7500.00',
      }
    })
    const store = useFinanceStore()

    await store.fetchSummary()

    expect(store.summary.warehouse_products_value).toBe('2500.00')
    expect(store.summary.warehouse_devices_value).toBe('5000.00')
    expect(store.summary.warehouse_total_value).toBe('7500.00')
  })

  it('jobs store marks loading during ProductionPlanner sync', async () => {
    let resolveRequest
    postMock.mockImplementationOnce(() => new Promise(resolve => {
      resolveRequest = resolve
    }))

    const store = useJobsStore()
    store.jobs = [{ id: 10 }]

    const syncPromise = store.syncJobToProductionPlanner(10)

    expect(store.loading).toBe(true)

    resolveRequest({ data: { success: true, productionplanner_project_id: 'pp-job-10' } })
    await syncPromise

    expect(store.loading).toBe(false)
    expect(store.jobs[0].productionplanner_project_id).toBe('pp-job-10')
  })

  it('projects store marks loading during ProductionPlanner sync', async () => {
    let resolveRequest
    postMock.mockImplementationOnce(() => new Promise(resolve => {
      resolveRequest = resolve
    }))

    const store = useProjectsStore()
    store.projects = [{ id: 20 }]

    const syncPromise = store.syncProjectToProductionPlanner(20)

    expect(store.loading).toBe(true)

    resolveRequest({ data: { success: true, productionplanner_project_id: 'pp-project-20' } })
    await syncPromise

    expect(store.loading).toBe(false)
    expect(store.projects[0].productionplanner_project_id).toBe('pp-project-20')
  })
})
