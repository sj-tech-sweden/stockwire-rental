import { Dark } from 'quasar'

export default () => {
  try {
    const saved = localStorage.getItem('ec_dark_mode')
    if (saved !== null) {
      Dark.set(saved === 'true')
      return
    }

    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
    Dark.set(!!prefersDark)

    // If user hasn't chosen, follow system changes
    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        const stored = localStorage.getItem('ec_dark_mode')
        if (stored === null) {
          Dark.set(e.matches)
        }
      })
    }
  } catch (e) {
    // no-op in environments without window/localStorage
  }
}
