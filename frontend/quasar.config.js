import { configure } from 'quasar/wrappers'

export default configure(function () {
  const runningInContainer = Boolean(process.env.KUBERNETES_SERVICE_HOST || process.env.DOCKER)
  const usePolling = process.env.CHOKIDAR_USEPOLLING
    ? process.env.CHOKIDAR_USEPOLLING === 'true'
    : runningInContainer
  const watchInterval = Number(process.env.CHOKIDAR_INTERVAL || 350)
  const watchBinaryInterval = Number(process.env.CHOKIDAR_BINARY_INTERVAL || 700)

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
