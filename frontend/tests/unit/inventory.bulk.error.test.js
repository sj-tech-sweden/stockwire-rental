import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, it, expect, vi } from 'vitest'

const getMock = vi.fn()
const postMock = vi.fn()
vi.mock('../../src/boot/axios', () => ({ api: { get: (...args) => getMock(...args), post: (...args) => postMock(...args) } }))

import { useInventoryStore } from '../../src/stores/inventory'

describe('inventory bulk create error propagation', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    postMock.mockReset()
  })

  it('propagates 409 conflict detail from server', async () => {
    const conflictDetail = { message: 'Code conflict', conflicts: ['A', 'B'] }
    const err = { response: { status: 409, data: { detail: conflictDetail } }, message: 'Conflict' }
    postMock.mockRejectedValueOnce(err)

    const store = useInventoryStore()
    try {
      await store.createZonesBulk(1, [{ name: 'A', code: 'A' }])
      throw new Error('Expected createZonesBulk to reject')
    } catch (e) {
      expect(e).toEqual(err)
      expect(e.response.data.detail).toEqual(conflictDetail)
    }
  })
})
