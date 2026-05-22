import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('../../src/boot/axios', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn()
  }
}))

import { api } from '../../src/boot/axios'
import { useUsersStore } from '../../src/stores/users'

describe('users store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('fetches users and exposes them', async () => {
    api.get.mockResolvedValue({ data: [{ id: 1, email: 'a@b.com' }] })
    const store = useUsersStore()
    await store.fetchUsers()
    expect(store.users.length).toBe(1)
    expect(store.users[0].email).toBe('a@b.com')
  })

  it('creates a user', async () => {
    api.post.mockResolvedValue({ data: { id: 2, email: 'c@d.com' } })
    const store = useUsersStore()
    const res = await store.createUser({ email: 'c@d.com' })
    expect(res.data || res).toBeTruthy()
  })

  it('lists roles and updates roles ref', async () => {
    const rolesPayload = [{ id: 1, name: 'viewer' }, { id: 2, name: 'admin' }]
    api.get.mockResolvedValueOnce({ data: rolesPayload })
    const store = useUsersStore()
    const res = await store.listRoles()
    expect(store.roles.length).toBe(2)
    expect(res[0].name).toBe('viewer')
  })

  it('assigns and removes role for a user', async () => {
    const userId = 5
    const roleId = 2
    api.post.mockResolvedValueOnce({ data: { id: roleId, name: 'admin' } })
    api.delete.mockResolvedValueOnce({})
    const store = useUsersStore()
    const assigned = await store.assignRoleToUser(userId, roleId)
    expect(assigned.id || assigned).toBeTruthy()
    await store.removeRoleFromUser(userId, roleId)
    expect(api.delete).toHaveBeenCalledWith(`/api/v1/auth/users/${userId}/roles/${roleId}`)
  })
})
