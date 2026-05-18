import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('router smoke', () => {
  it('contains phase 1 route definitions', () => {
    const routerSource = readFileSync(resolve(process.cwd(), 'src/router/index.js'), 'utf8')

    expect(routerSource).toContain("path: '/'")
    expect(routerSource).toContain("path: 'auth'")
    expect(routerSource).toContain("path: 'inventory'")
    expect(routerSource).toContain("path: 'jobs'")
    expect(routerSource).toContain("path: 'finance'")
  })
})
