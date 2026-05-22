import { i18n, resolveAppLocale, setLocale } from '../i18n'

export default ({ app }) => {
  app.use(i18n)
  setLocale(resolveAppLocale(null))
}
