import { setActivePinia, createPinia } from 'pinia'
import { useUsersStore } from '../../src/stores/users'

describe('users store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  test('initial state', () => {
    const store = useUsersStore()
    expect(store.users).toBeDefined()
    expect(Array.isArray(store.users)).toBe(true)
  })
})
