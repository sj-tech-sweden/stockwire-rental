import { Quasar } from 'quasar'
import quasarEn from 'quasar/lang/en-GB'
import quasarSv from 'quasar/lang/sv'
import { i18n, onLocaleChange, resolveAppLocale, setLocale } from '../i18n'

// Pre-load Quasar language packs for the supported locales so component strings
// (e.g. q-table footer) are available synchronously and update immediately when
// the locale changes. Additional locales can be added here as the app grows.
const QUASAR_LANGS = {
  en: quasarEn,
  sv: quasarSv,
}

function applyQuasarLang(locale) {
  const base = String(locale || 'en').toLowerCase().split(/[-_]/)[0]
  const lang = QUASAR_LANGS[base] || QUASAR_LANGS.en
  Quasar.lang.set(lang)
}

export default async ({ app }) => {
  app.use(i18n)
  const initial = localStorage.getItem('sw_locale') || resolveAppLocale(null)
  setLocale(initial)
  applyQuasarLang(initial)
  onLocaleChange(applyQuasarLang)
}
