import { i18n, resolveAppLocale, setLocale } from '../i18n'

export default ({ app }) => {
  app.use(i18n)
  setLocale(localStorage.getItem('sw_locale') || resolveAppLocale(null))
}
