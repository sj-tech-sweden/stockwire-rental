import { configure } from 'quasar/wrappers'

export default configure(function () {
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
      vueRouterMode: 'history'
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
