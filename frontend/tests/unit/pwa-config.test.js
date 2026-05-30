import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import quasarConfig from '../../quasar.config.js'

describe('PWA configuration', () => {
  const frontendRoot = resolve(import.meta.dirname, '../..')

  it('builds the frontend in PWA mode with installable metadata', () => {
    const packageJson = JSON.parse(readFileSync(resolve(frontendRoot, 'package.json'), 'utf8'))
    const config = quasarConfig({})
    const manifestJson = JSON.parse(readFileSync(resolve(frontendRoot, 'src-pwa/manifest.json'), 'utf8'))

    expect(packageJson.scripts.dev).toContain('-m pwa')
    expect(packageJson.scripts.build).toContain('-m pwa')
    expect(config.pwa.workboxMode).toBe('GenerateSW')
    expect(config.pwa.manifest.display).toBe('standalone')
    expect(config.pwa.manifest.icons).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ src: 'icons/icon-192x192.png', sizes: '192x192' }),
        expect.objectContaining({ src: 'icons/icon-512x512.png', sizes: '512x512' }),
      ]),
    )
    expect(manifestJson).toMatchObject({
      display: 'standalone',
      background_color: '#11181D',
      theme_color: '#3F873F',
    })
  })

  it('serves the generated PWA output and ships required icon assets', () => {
    const dockerfile = readFileSync(resolve(frontendRoot, 'Dockerfile'), 'utf8')

    expect(dockerfile).toContain('/app/dist/pwa')
    expect(existsSync(resolve(frontendRoot, 'public/icons/icon-180x180.png'))).toBe(true)
    expect(existsSync(resolve(frontendRoot, 'public/icons/icon-192x192.png'))).toBe(true)
    expect(existsSync(resolve(frontendRoot, 'public/icons/icon-512x512.png'))).toBe(true)
  })

  it('caches runtime config for offline bootstrapping without precaching a stale env file', () => {
    const config = quasarConfig({})
    const runtimeConfigCache = config.pwa.workboxOptions.runtimeCaching.find(({ options }) => options?.cacheName === 'runtime-config')

    expect(config.pwa.manifestFilename).toBe('manifest.webmanifest')
    expect(config.pwa.workboxOptions.globIgnores).toContain('**/env-config.js')
    expect(runtimeConfigCache).toMatchObject({
      handler: 'NetworkFirst',
      options: {
        cacheName: 'runtime-config',
        networkTimeoutSeconds: 3,
      },
    })
    expect(String(runtimeConfigCache.urlPattern)).toContain('env-config')
  })
})
