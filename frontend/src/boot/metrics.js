import { api } from '../boot/axios'
import { startMetricsFlush, trackPageView, trackApiTiming, trackError } from '../services/metrics'

export default ({ router }) => {
  router.afterEach((to) => {
    trackPageView(to.fullPath)
  })

  api.interceptors.response.use(
    (response) => {
      const cfg = response.config
      if (cfg && cfg.method && cfg.url && !cfg.url.includes('/api/v1/metrics')) {
        const duration = Date.now() - (cfg._metricsStart || Date.now())
        trackApiTiming(cfg.method.toUpperCase(), cfg.url, duration / 1000)
      }
      return response
    },
    (error) => {
      const cfg = error.config
      if (cfg && cfg.method && cfg.url && !cfg.url.includes('/api/v1/metrics')) {
        const duration = Date.now() - (cfg._metricsStart || Date.now())
        trackApiTiming(cfg.method.toUpperCase(), cfg.url, duration / 1000)
      }
      trackError('api_error')
      return Promise.reject(error)
    }
  )

  api.interceptors.request.use(
    (config) => {
      config._metricsStart = Date.now()
      return config
    },
    (error) => Promise.reject(error)
  )

  startMetricsFlush()
}
