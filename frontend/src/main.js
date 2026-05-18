import { createApp } from 'vue'
import { Quasar } from 'quasar'

import App from './App.vue'
import router from './router'

import 'quasar/src/css/index.sass'
import './css/app.css'

createApp(App)
  .use(Quasar, {
    config: {}
  })
  .use(router)
  .mount('#q-app')
