import { createI18n } from 'vue-i18n'

import en from './locales/en'
import sv from './locales/sv'

export const SUPPORTED_LOCALES = ['en', 'sv']

const messages = {
  en,
  sv,
}

function normalizeLocale(raw) {
  const value = String(raw || '').trim().toLowerCase()
  if (!value) return 'en'
  if (value === 'sv' || value.startsWith('sv-')) return 'sv'
  if (value === 'en' || value.startsWith('en-')) return 'en'
  return 'en'
}

export function getBrowserLocale() {
  const lang = navigator?.language || navigator?.languages?.[0] || ''
  const value = String(lang || '').trim().toLowerCase()
  if (!value) return null
  if (value === 'sv' || value.startsWith('sv-')) return 'sv'
  if (value === 'en' || value.startsWith('en-')) return 'en'
  return null
}

export function getCompanyDefaultLocale() {
  const stored = localStorage.getItem('sw_company_default_language') || ''
  const normalized = normalizeLocale(stored)
  return SUPPORTED_LOCALES.includes(normalized) ? normalized : 'en'
}

export function getUserLocalePreference(userId) {
  const key = userId ? `sw_user_locale_${userId}` : 'sw_user_locale'
  const stored = localStorage.getItem(key) || ''
  const normalized = normalizeLocale(stored)
  return SUPPORTED_LOCALES.includes(normalized) ? normalized : null
}

export function setUserLocalePreference(userId, locale) {
  const normalized = normalizeLocale(locale)
  const key = userId ? `sw_user_locale_${userId}` : 'sw_user_locale'
  localStorage.setItem(key, normalized)
  localStorage.setItem('sw_locale', normalized)
  return normalized
}

export function resolveAppLocale(userId) {
  return getUserLocalePreference(userId) || getCompanyDefaultLocale() || getBrowserLocale() || 'en'
}

export function resolveLoginLocale(companyDefault) {
  const browser = getBrowserLocale()
  if (browser) return browser
  const company = normalizeLocale(companyDefault)
  if (SUPPORTED_LOCALES.includes(company)) return company
  return 'en'
}

export const i18n = createI18n({
  legacy: false,
  locale: normalizeLocale(localStorage.getItem('sw_locale') || 'en'),
  fallbackLocale: 'en',
  messages,
})

export function setLocale(locale) {
  const normalized = normalizeLocale(locale)
  i18n.global.locale.value = normalized
  localStorage.setItem('sw_locale', normalized)
  if (typeof document !== 'undefined') {
    document.documentElement.lang = normalized
  }
  return normalized
}
