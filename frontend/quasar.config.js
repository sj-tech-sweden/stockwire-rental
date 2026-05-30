import { configure } from 'quasar/wrappers'

export default configure(function () {
  const runningInContainer = Boolean(process.env.KUBERNETES_SERVICE_HOST || process.env.DOCKER)
  const usePolling = process.env.CHOKIDAR_USEPOLLING
    ? process.env.CHOKIDAR_USEPOLLING === 'true'
    : runningInContainer
  const parsePositiveInteger = (value, fallback) => {
    const normalized = String(value ?? '').trim()
    if (!/^\d+$/.test(normalized)) {
      return fallback
    }

    const parsed = Number(normalized)
    return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback
  }
  const watchInterval = parsePositiveInteger(process.env.CHOKIDAR_INTERVAL, 350)
  const watchBinaryInterval = parsePositiveInteger(process.env.CHOKIDAR_BINARY_INTERVAL, 700)

  return {
    supportTS: false,
    boot: ['axios', 'i18n', 'theme', 'force-header-theme', 'realtime-sync', 'orbit-sync'],
    css: ['app.css'],
    extras: ['material-icons'],
    build: {
      target: {
        browser: ['es2022', 'firefox115', 'chrome115', 'safari14'],
        node: 'node20'
      },
      vueRouterMode: 'history',
      extendViteConf(viteConf) {
        const currentWatch = viteConf.server?.watch || {}
        const currentIgnored = Array.isArray(currentWatch.ignored)
          ? currentWatch.ignored
          : currentWatch.ignored
            ? [currentWatch.ignored]
            : []

        const ignored = [
          ...currentIgnored,
          '**/.git/**',
          '**/.quasar/**',
          '**/dist/**',
          '**/coverage/**',
          '**/test-results/**',
          '**/playwright-report/**',
          '**/node_modules/**'
        ]

        viteConf.server = {
          ...(viteConf.server || {}),
          watch: {
            ...currentWatch,
            ignored,
            usePolling,
            interval: watchInterval,
            binaryInterval: watchBinaryInterval,
            awaitWriteFinish: {
              stabilityThreshold: 200,
              pollInterval: 100
            }
          }
        }
      }
    },
    pwa: {
      workboxMode: 'GenerateSW',
      injectRegister: 'auto',
      swFilename: 'service-worker.js',
      manifestFilename: 'manifest.webmanifest',
      workboxOptions: {
        cleanupOutdatedCaches: true,
        clientsClaim: true,
        skipWaiting: true,
        globIgnores: ['**/env-config.js'],
        runtimeCaching: [
          {
            urlPattern: /\/env-config\.js$/,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'runtime-config',
              networkTimeoutSeconds: 3,
              cacheableResponse: {
                statuses: [200]
              }
            }
          }
        ]
      },
      manifest: {
        name: 'Stockwire Rental',
        short_name: 'Stockwire',
        description: 'Offline-capable rental inventory management for Stockwire.',
        display: 'standalone',
        orientation: 'portrait',
        background_color: '#11181D',
        theme_color: '#3F873F',
        icons: [
          {
            src: 'icons/icon-192x192.png',
            sizes: '192x192',
            type: 'image/png',
            purpose: 'any maskable'
          },
          {
            src: 'icons/icon-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable'
          }
        ]
      }
    },
    devServer: {
      host: '0.0.0.0',
      port: 9000,
      open: false
    },
    framework: {
      config: {
        brand: {
          primary: '#3F873F',
          secondary: '#11181D',
          accent: '#35A853',
          dark: '#0C1114',
          positive: '#43C36B',
          negative: '#E65656',
          info: '#3F873F',
          warning: '#F7B84B'
        }
      },
      plugins: ['Dark', 'Notify', 'Dialog']
    }
  }
})
