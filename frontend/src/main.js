import { createApp } from 'vue'
import { Quasar } from 'quasar'

import App from './App.vue'
import router from './router'
import { pinia } from './stores'

import 'quasar/src/css/index.sass'
import './css/app.css'
import './boot/theme'

createApp(App)
  .use(Quasar, {
    config: {}
  })
  .use(pinia)
  .use(router)
  .mount('#q-app')
