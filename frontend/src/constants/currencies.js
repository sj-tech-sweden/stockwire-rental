export const CURRENCY_OPTIONS = [
  { value: 'SEK', label: 'SEK - Swedish Krona' },
  { value: 'EUR', label: 'EUR - Euro' },
  { value: 'USD', label: 'USD - US Dollar' },
  { value: 'GBP', label: 'GBP - British Pound' },
  { value: 'NOK', label: 'NOK - Norwegian Krone' },
  { value: 'DKK', label: 'DKK - Danish Krone' },
  { value: 'CHF', label: 'CHF - Swiss Franc' },
  { value: 'PLN', label: 'PLN - Polish Zloty' },
  { value: 'CZK', label: 'CZK - Czech Koruna' },
  { value: 'HUF', label: 'HUF - Hungarian Forint' },
  { value: 'RON', label: 'RON - Romanian Leu' },
  { value: 'BGN', label: 'BGN - Bulgarian Lev' },
  { value: 'ISK', label: 'ISK - Icelandic Krona' },
  { value: 'CAD', label: 'CAD - Canadian Dollar' },
  { value: 'AUD', label: 'AUD - Australian Dollar' },
  { value: 'NZD', label: 'NZD - New Zealand Dollar' },
  { value: 'JPY', label: 'JPY - Japanese Yen' },
  { value: 'CNY', label: 'CNY - Chinese Yuan' },
  { value: 'INR', label: 'INR - Indian Rupee' },
  { value: 'KRW', label: 'KRW - South Korean Won' },
  { value: 'SGD', label: 'SGD - Singapore Dollar' },
  { value: 'HKD', label: 'HKD - Hong Kong Dollar' },
  { value: 'THB', label: 'THB - Thai Baht' },
  { value: 'MYR', label: 'MYR - Malaysian Ringgit' },
  { value: 'IDR', label: 'IDR - Indonesian Rupiah' },
  { value: 'PHP', label: 'PHP - Philippine Peso' },
  { value: 'VND', label: 'VND - Vietnamese Dong' },
  { value: 'AED', label: 'AED - UAE Dirham' },
  { value: 'SAR', label: 'SAR - Saudi Riyal' },
  { value: 'QAR', label: 'QAR - Qatari Riyal' },
  { value: 'TRY', label: 'TRY - Turkish Lira' },
  { value: 'ILS', label: 'ILS - Israeli New Shekel' },
  { value: 'MXN', label: 'MXN - Mexican Peso' },
  { value: 'BRL', label: 'BRL - Brazilian Real' },
  { value: 'ARS', label: 'ARS - Argentine Peso' },
  { value: 'CLP', label: 'CLP - Chilean Peso' },
  { value: 'COP', label: 'COP - Colombian Peso' },
  { value: 'PEN', label: 'PEN - Peruvian Sol' },
  { value: 'ZAR', label: 'ZAR - South African Rand' },
  { value: 'NGN', label: 'NGN - Nigerian Naira' },
  { value: 'EGP', label: 'EGP - Egyptian Pound' },
]

export function normalizeCurrencyCode(value, fallback = 'SEK') {
  const code = String(value || '').trim().toUpperCase()
  if (/^[A-Z]{3}$/.test(code)) return code
  return fallback
}

export function currencyOptionFor(code) {
  const normalized = normalizeCurrencyCode(code)
  const known = CURRENCY_OPTIONS.find(option => option.value === normalized)
  if (known) return known
  return { value: normalized, label: normalized }
}

export function filterCurrencyOptions(options, needle) {
  const term = String(needle || '').trim().toLowerCase()
  if (!term) return [...options]
  return options.filter(option => {
    const label = String(option?.label || '').toLowerCase()
    const value = String(option?.value || '').toLowerCase()
    return label.includes(term) || value.includes(term)
  })
}
