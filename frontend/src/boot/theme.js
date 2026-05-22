import { Dark } from 'quasar'

export default () => {
  try {
    const saved = localStorage.getItem('ec_dark_mode')
    if (saved !== null) {
      Dark.set(saved === 'true')
      return
    }

    // No saved preference — use system preference and follow changes
    const mq = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)')
    Dark.set(mq ? mq.matches : false)

    if (mq) {
      mq.addEventListener('change', (e) => {
        if (localStorage.getItem('ec_dark_mode') === null) {
          Dark.set(e.matches)
        }
      })
    }
  } catch (e) {
    // no-op in environments without window/localStorage
  }
}
