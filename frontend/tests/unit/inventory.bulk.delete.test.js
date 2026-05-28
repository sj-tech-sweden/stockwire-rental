import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, it, expect, vi } from 'vitest'

const getMock = vi.fn()
const postMock = vi.fn()
vi.mock('../../src/boot/axios', () => ({ api: { get: (...args) => getMock(...args), post: (...args) => postMock(...args) } }))

import { useInventoryStore } from '../../src/stores/inventory'

// simple unit test to ensure deleteZonesBulk is called and returns value
describe('inventory bulk delete', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    postMock.mockReset()
  })

  it('calls deleteZonesBulk and returns result', async () => {
    const resp = { data: { deleted: 2, skipped: 0 } }
    postMock.mockResolvedValueOnce(resp)
    getMock.mockResolvedValue({ data: [] })

    const store = useInventoryStore()
    const result = await store.deleteZonesBulk([1, 2])
    expect(result).toEqual(resp.data)
    expect(postMock).toHaveBeenCalledWith('/api/v1/inventory/locations/bulk-delete', { ids: [1, 2] })
  })
})
