import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '../boot/axios'
import { cacheSnapshot, isOnline, queueMutation, readSnapshot } from '../services/offline/orbitSync'

export const DEFAULT_LOCATION_TYPES = ['rack', 'shelf', 'bin', 'pallet', 'stage', 'truck', 'warehouse', 'workshop']
export const DEFAULT_CATEGORY_PREFILL_PATHS = [
  ['Audio', 'Speakers'],
  ['Audio', 'Microphones'],
  ['Audio', 'Mixers'],
  ['Audio', 'Playback'],
  ['Audio', 'Wireless'],
  ['Audio', 'Cables', 'XLR'],
  ['Audio', 'Cables', 'PowerCon'],
  ['Audio', 'Cables', 'Speakon'],
  ['Lighting', 'Fixtures'],
  ['Lighting', 'Control'],
  ['Lighting', 'Dimmers'],
  ['Lighting', 'Cables', 'DMX'],
  ['Lighting', 'Power'],
  ['Rigging', 'Truss'],
  ['Rigging', 'Motors'],
  ['Rigging', 'Hardware'],
  ['Video', 'Displays'],
  ['Video', 'Projectors'],
  ['Video', 'Switchers'],
  ['Video', 'Cables'],
  ['Power', 'Distribution'],
  ['Power', 'Cables'],
  ['Staging', 'Decks'],
  ['Staging', 'Legs'],
  ['Accessories', 'Cases'],
  ['Accessories', 'Adapters'],
  ['Accessories', 'Clamps'],
  ['Accessories', 'Safety'],
  ['Consumables', 'Tape'],
  ['Consumables', 'Batteries'],
  ['Networking', 'Switches'],
  ['Networking', 'Cables'],
]

export const DEFAULT_BRAND_OPTIONS = [
  'Bosch',
  'Makita',
  'Hilti',
  'Milwaukee',
  'DeWalt',
  'Festool',
  'Ryobi',
  'Husqvarna',
  'Shure',
  'Sennheiser',
  'Yamaha',
  'Allen & Heath',
  'JBL Professional',
  'd&b audiotechnik',
  'L-Acoustics',
  'Meyer Sound',
  'DiGiCo',
  'Prolyte',
  'Global Truss',
  'ROE Visual',
  'Absen',
  'Robe Lighting',
  'Claypaky',
  'Martin (HARMAN)',
  'ETC',
  'GLP (German Light)',
  'Ayrton',
  'Elation Pro',
  'Chauvet Pro',
  'American DJ',
  'Barco',
  'Panasonic',
  'Blackmagic Design',
  'Unilumin',
  'Brompton Tech',
  'Analog Way',
]
export const DEFAULT_MANUFACTURER_OPTIONS = [
  'Bosch',
  'Makita',
  'Hilti',
  'Techtronic Industries',
  'Stanley Black & Decker',
  'Festool',
  'Husqvarna Group',
  'Shure Incorporated',
  'Sennheiser electronic SE & Co. KG',
  'Yamaha Corporation',
  'Allen & Heath Limited',
  'Harman International',
  'd&b audiotechnik',
  'L-Acoustics',
  'Meyer Sound Laboratories',
  'DiGiCo',
  'Prolyte Group',
  'Global Truss',
  'ROE Visual',
  'Absen',
  'Robe Lighting',
  'Claypaky',
  'Martin Professional',
  'ETC',
  'GLP German Light Products',
  'Ayrton',
  'Elation Professional',
  'CHAUVET Professional',
  'ADJ Products',
  'Barco',
  'Panasonic Connect',
  'Blackmagic Design',
  'Unilumin',
  'Brompton Technology',
  'Analog Way',
]
export const DEFAULT_BRAND_MANUFACTURER_MAP = {
  Bosch: 'Bosch',
  Makita: 'Makita',
  Hilti: 'Hilti',
  Milwaukee: 'Techtronic Industries',
  DeWalt: 'Stanley Black & Decker',
  Festool: 'Festool',
  Ryobi: 'Techtronic Industries',
  Husqvarna: 'Husqvarna Group',
  Shure: 'Shure Incorporated',
  Sennheiser: 'Sennheiser electronic SE & Co. KG',
  Yamaha: 'Yamaha Corporation',
  'Allen & Heath': 'Allen & Heath Limited',
  'JBL Professional': 'Harman International',
  'd&b audiotechnik': 'd&b audiotechnik',
  'L-Acoustics': 'L-Acoustics',
  'Meyer Sound': 'Meyer Sound Laboratories',
  DiGiCo: 'DiGiCo',
  Prolyte: 'Prolyte Group',
  'Global Truss': 'Global Truss',
  'ROE Visual': 'ROE Visual',
  Absen: 'Absen',
  'Robe Lighting': 'Robe Lighting',
  Claypaky: 'Claypaky',
  'Martin (HARMAN)': 'Martin Professional',
  ETC: 'ETC',
  'GLP (German Light)': 'GLP German Light Products',
  Ayrton: 'Ayrton',
  'Elation Pro': 'Elation Professional',
  'Chauvet Pro': 'CHAUVET Professional',
  'American DJ': 'ADJ Products',
  Barco: 'Barco',
  Panasonic: 'Panasonic Connect',
  'Blackmagic Design': 'Blackmagic Design',
  Unilumin: 'Unilumin',
  'Brompton Tech': 'Brompton Technology',
  'Analog Way': 'Analog Way',
}
export const DEFAULT_BRAND_LINKS = {
  Bosch: 'https://www.bosch-professional.com/',
  Makita: 'https://www.makita.com/',
  Hilti: 'https://www.hilti.com/',
  Milwaukee: 'https://www.milwaukeetool.com/',
  DeWalt: 'https://www.dewalt.com/',
  Festool: 'https://www.festool.com/',
  Ryobi: 'https://www.ryobitools.com/',
  Husqvarna: 'https://www.husqvarna.com/',
  Shure: 'https://www.shure.com/',
  Sennheiser: 'https://www.sennheiser.com/',
  Yamaha: 'https://www.yamaha.com/',
  'Allen & Heath': 'https://www.allen-heath.com/',
  'JBL Professional': 'https://jblpro.com/',
  'd&b audiotechnik': 'https://www.dbaudio.com/',
  'L-Acoustics': 'https://www.l-acoustics.com/',
  'Meyer Sound': 'https://meyersound.com/',
  DiGiCo: 'https://digico.biz/',
  Prolyte: 'https://www.prolyte.com/',
  'Global Truss': 'https://www.globaltruss.com/',
  'ROE Visual': 'https://www.roevisual.com/',
  Absen: 'https://www.absen.com/',
  'Robe Lighting': 'https://www.robe.cz/',
  Claypaky: 'https://www.claypaky.it/',
  'Martin (HARMAN)': 'https://www.martin.com/',
  ETC: 'https://www.etcconnect.com/',
  'GLP (German Light)': 'https://www.glp.de/',
  Ayrton: 'https://www.ayrton.eu/',
  'Elation Pro': 'https://www.elationlighting.com/',
  'Chauvet Pro': 'https://www.chauvetprofessional.com/',
  'American DJ': 'https://www.adj.com/',
  Barco: 'https://www.barco.com/',
  Panasonic: 'https://pro-av.panasonic.net/',
  'Blackmagic Design': 'https://www.blackmagicdesign.com/',
  Unilumin: 'https://www.unilumin.com/',
  'Brompton Tech': 'https://www.bromptontech.com/',
  'Analog Way': 'https://www.analogway.com/',
}
export const DEFAULT_MANUFACTURER_LINKS = {
  Bosch: 'https://www.bosch.com/',
  Makita: 'https://www.makita.com/',
  Hilti: 'https://www.hilti.group/',
  'Techtronic Industries': 'https://www.ttigroup.com/',
  'Stanley Black & Decker': 'https://www.stanleyblackanddecker.com/',
  Festool: 'https://www.festool.com/',
  'Husqvarna Group': 'https://www.husqvarnagroup.com/',
  'Shure Incorporated': 'https://www.shure.com/',
  'Sennheiser electronic SE & Co. KG': 'https://www.sennheiser.com/',
  'Yamaha Corporation': 'https://www.yamaha.com/',
  'Allen & Heath Limited': 'https://www.allen-heath.com/',
  'Harman International': 'https://www.harman.com/',
  'd&b audiotechnik': 'https://www.dbaudio.com/',
  'L-Acoustics': 'https://www.l-acoustics.com/',
  'Meyer Sound Laboratories': 'https://meyersound.com/',
  DiGiCo: 'https://digico.biz/',
  'Prolyte Group': 'https://www.prolyte.com/',
  'Global Truss': 'https://www.globaltruss.com/',
  'ROE Visual': 'https://www.roevisual.com/',
  Absen: 'https://www.absen.com/',
  'Robe Lighting': 'https://www.robe.cz/',
  Claypaky: 'https://www.claypaky.it/',
  'Martin Professional': 'https://www.martin.com/',
  ETC: 'https://www.etcconnect.com/',
  'GLP German Light Products': 'https://www.glp.de/',
  Ayrton: 'https://www.ayrton.eu/',
  'Elation Professional': 'https://www.elationlighting.com/',
  'CHAUVET Professional': 'https://www.chauvetprofessional.com/',
  'ADJ Products': 'https://www.adj.com/',
  Barco: 'https://www.barco.com/',
  'Panasonic Connect': 'https://pro-av.panasonic.net/',
  'Blackmagic Design': 'https://www.blackmagicdesign.com/',
  Unilumin: 'https://www.unilumin.com/',
  'Brompton Technology': 'https://www.bromptontech.com/',
  'Analog Way': 'https://www.analogway.com/',
}
export const DEFAULT_INTEGRATIONS = {
  eventory_instances: [
    {
      id: 'eventory-main',
      name: 'Eventory Main',
      enabled: false,
      api_url: 'https://api.eventory.se',
      api_key: '',
      username: '',
      password: '',
      token_endpoint: '',
      supplier_name: 'Eventory',
      sync_interval_minutes: 0,
      price_margin_percent: 0,
      last_sync_at: null,
      last_sync_imported: 0,
      last_sync_updated: 0,
      last_sync_skipped: 0,
      last_sync_total: 0,
      sync_running: false,
      sync_started_at: null,
      sync_finished_at: null,
      sync_progress_current: 0,
      sync_progress_total: 0,
      sync_progress_percent: 0,
      sync_message: null,
    },
  ],
}

export const DEFAULT_AUTH_SSO_SETTINGS = {
  enabled: false,
  auto_create_users: false,
  sync_roles_on_login: true,
  default_role: 'viewer',
  group_role_map: {},
  oidc_providers: [],
  saml_providers: [],
}

export const DEFAULT_COMPANY_PROFILE = {
  company_name: null,
  default_language: 'en',
  logo_file_id: null,
  logo_url: null,
  logo_light_wide_file_id: null,
  logo_light_wide_url: null,
  logo_light_small_file_id: null,
  logo_light_small_url: null,
  logo_dark_wide_file_id: null,
  logo_dark_wide_url: null,
  logo_dark_small_file_id: null,
  logo_dark_small_url: null,
  currency: 'SEK',
  vat_number: null,
  address_line1: null,
  address_line2: null,
  postal_code: null,
  city: null,
  country: null,
  contact_email: null,
  contact_phone: null,
  website: null,
}

export const useSettingsStore = defineStore('settings', () => {
  const locationTypes = ref([...DEFAULT_LOCATION_TYPES])
  const categoryPrefillPaths = ref(DEFAULT_CATEGORY_PREFILL_PATHS.map(path => [...path]))
  const brandOptions = ref([...DEFAULT_BRAND_OPTIONS])
  const manufacturerOptions = ref([...DEFAULT_MANUFACTURER_OPTIONS])
  const defaultBrand = ref(DEFAULT_BRAND_OPTIONS[0])
  const defaultManufacturer = ref(DEFAULT_MANUFACTURER_OPTIONS[0])
  const brandManufacturerMap = ref({ ...DEFAULT_BRAND_MANUFACTURER_MAP })
  const brandLinks = ref({ ...DEFAULT_BRAND_LINKS })
  const manufacturerLinks = ref({ ...DEFAULT_MANUFACTURER_LINKS })
  const integrations = ref(cloneIntegrations(DEFAULT_INTEGRATIONS))
  const authSsoSettings = ref(cloneAuthSsoSettings(DEFAULT_AUTH_SSO_SETTINGS))
  const companyProfile = ref({ ...DEFAULT_COMPANY_PROFILE })
  const labelTemplates = ref([])
  const loading = ref(false)

  async function fetchLocationTypes() {
    loading.value = true
    try {
      const { data } = await api.get('/api/v1/settings/location-types')
      locationTypes.value = Array.isArray(data?.options) && data.options.length
        ? data.options
        : [...DEFAULT_LOCATION_TYPES]
      await cacheSnapshot('settings.locationTypes', locationTypes.value)
      return locationTypes.value
    } catch (error) {
      if (!isOnline()) {
        const cached = await readSnapshot('settings.locationTypes')
        if (Array.isArray(cached) && cached.length) {
          locationTypes.value = cached
          return locationTypes.value
        }
      }
      throw error
    } finally {
      loading.value = false
    }
  }

  async function updateLocationTypes(options) {
    const normalized = normalizeOptions(options)
    if (!isOnline()) {
      locationTypes.value = normalized
      await queueMutation({
        method: 'put',
        url: '/api/v1/settings/location-types',
        data: { options: normalized },
        conflictPolicy: 'guarded',
      })
      return locationTypes.value
    }
    const { data } = await api.put('/api/v1/settings/location-types', { options: normalized })
    locationTypes.value = Array.isArray(data?.options) && data.options.length
      ? data.options
      : [...DEFAULT_LOCATION_TYPES]
    return locationTypes.value
  }

  async function fetchCategoryPrefillPaths() {
    try {
      const { data } = await api.get('/api/v1/settings/category-prefill')
      categoryPrefillPaths.value = Array.isArray(data?.paths) && data.paths.length
        ? data.paths.map(path => [...path])
        : DEFAULT_CATEGORY_PREFILL_PATHS.map(path => [...path])
      await cacheSnapshot('settings.categoryPrefill', categoryPrefillPaths.value)
      return categoryPrefillPaths.value
    } catch (error) {
      if (!isOnline()) {
        const cached = await readSnapshot('settings.categoryPrefill')
        if (Array.isArray(cached) && cached.length) {
          categoryPrefillPaths.value = cached.map(path => [...path])
          return categoryPrefillPaths.value
        }
      }
      throw error
    }
  }

  async function updateCategoryPrefillPaths(paths) {
    const normalized = normalizeCategoryPaths(paths)
    if (!isOnline()) {
      categoryPrefillPaths.value = normalized.map(path => [...path])
      await queueMutation({
        method: 'put',
        url: '/api/v1/settings/category-prefill',
        data: { paths: normalized },
        conflictPolicy: 'guarded',
      })
      return categoryPrefillPaths.value
    }
    const { data } = await api.put('/api/v1/settings/category-prefill', { paths: normalized })
    categoryPrefillPaths.value = Array.isArray(data?.paths) && data.paths.length
      ? data.paths.map(path => [...path])
      : DEFAULT_CATEGORY_PREFILL_PATHS.map(path => [...path])
    return categoryPrefillPaths.value
  }

  async function fetchProductDefaults() {
    try {
      const { data } = await api.get('/api/v1/settings/product-defaults')
      brandOptions.value = normalizeCaseOptions(data?.brand_options, DEFAULT_BRAND_OPTIONS)
      manufacturerOptions.value = normalizeCaseOptions(data?.manufacturer_options, DEFAULT_MANUFACTURER_OPTIONS)
      defaultBrand.value = normalizeSelected(data?.default_brand, brandOptions.value)
      defaultManufacturer.value = normalizeSelected(data?.default_manufacturer, manufacturerOptions.value)
      brandManufacturerMap.value = normalizeMap(data?.brand_manufacturer_map, brandOptions.value, manufacturerOptions.value)
      brandLinks.value = normalizeLinks(data?.brand_links, brandOptions.value)
      manufacturerLinks.value = normalizeLinks(data?.manufacturer_links, manufacturerOptions.value)
      await cacheSnapshot('settings.productDefaults', {
        brand_options: brandOptions.value,
        manufacturer_options: manufacturerOptions.value,
        default_brand: defaultBrand.value,
        default_manufacturer: defaultManufacturer.value,
        brand_manufacturer_map: brandManufacturerMap.value,
        brand_links: brandLinks.value,
        manufacturer_links: manufacturerLinks.value,
      })
      return {
        brand_options: brandOptions.value,
        manufacturer_options: manufacturerOptions.value,
        default_brand: defaultBrand.value,
        default_manufacturer: defaultManufacturer.value,
        brand_manufacturer_map: brandManufacturerMap.value,
        brand_links: brandLinks.value,
        manufacturer_links: manufacturerLinks.value,
      }
    } catch (error) {
      if (!isOnline()) {
        const cached = await readSnapshot('settings.productDefaults')
        if (cached && typeof cached === 'object') {
          brandOptions.value = normalizeCaseOptions(cached.brand_options, DEFAULT_BRAND_OPTIONS)
          manufacturerOptions.value = normalizeCaseOptions(cached.manufacturer_options, DEFAULT_MANUFACTURER_OPTIONS)
          defaultBrand.value = normalizeSelected(cached.default_brand, brandOptions.value)
          defaultManufacturer.value = normalizeSelected(cached.default_manufacturer, manufacturerOptions.value)
          brandManufacturerMap.value = normalizeMap(cached.brand_manufacturer_map, brandOptions.value, manufacturerOptions.value)
          brandLinks.value = normalizeLinks(cached.brand_links, brandOptions.value)
          manufacturerLinks.value = normalizeLinks(cached.manufacturer_links, manufacturerOptions.value)
          return cached
        }
      }
      throw error
    }
  }

  async function updateProductDefaults(payload) {
    const body = {
      brand_options: normalizeCaseOptions(payload?.brand_options, DEFAULT_BRAND_OPTIONS),
      manufacturer_options: normalizeCaseOptions(payload?.manufacturer_options, DEFAULT_MANUFACTURER_OPTIONS),
      default_brand: payload?.default_brand ?? null,
      default_manufacturer: payload?.default_manufacturer ?? null,
      brand_manufacturer_map: payload?.brand_manufacturer_map || {},
      brand_links: payload?.brand_links || {},
      manufacturer_links: payload?.manufacturer_links || {},
    }
    if (!isOnline()) {
      brandOptions.value = normalizeCaseOptions(body.brand_options, DEFAULT_BRAND_OPTIONS)
      manufacturerOptions.value = normalizeCaseOptions(body.manufacturer_options, DEFAULT_MANUFACTURER_OPTIONS)
      defaultBrand.value = normalizeSelected(body.default_brand, brandOptions.value)
      defaultManufacturer.value = normalizeSelected(body.default_manufacturer, manufacturerOptions.value)
      brandManufacturerMap.value = normalizeMap(body.brand_manufacturer_map, brandOptions.value, manufacturerOptions.value)
      brandLinks.value = normalizeLinks(body.brand_links, brandOptions.value)
      manufacturerLinks.value = normalizeLinks(body.manufacturer_links, manufacturerOptions.value)
      await queueMutation({
        method: 'put',
        url: '/api/v1/settings/product-defaults',
        data: body,
        conflictPolicy: 'guarded',
      })
      return {
        brand_options: brandOptions.value,
        manufacturer_options: manufacturerOptions.value,
        default_brand: defaultBrand.value,
        default_manufacturer: defaultManufacturer.value,
        brand_manufacturer_map: brandManufacturerMap.value,
        brand_links: brandLinks.value,
        manufacturer_links: manufacturerLinks.value,
      }
    }
    const { data } = await api.put('/api/v1/settings/product-defaults', body)
    brandOptions.value = normalizeCaseOptions(data?.brand_options, DEFAULT_BRAND_OPTIONS)
    manufacturerOptions.value = normalizeCaseOptions(data?.manufacturer_options, DEFAULT_MANUFACTURER_OPTIONS)
    defaultBrand.value = normalizeSelected(data?.default_brand, brandOptions.value)
    defaultManufacturer.value = normalizeSelected(data?.default_manufacturer, manufacturerOptions.value)
    brandManufacturerMap.value = normalizeMap(data?.brand_manufacturer_map, brandOptions.value, manufacturerOptions.value)
    brandLinks.value = normalizeLinks(data?.brand_links, brandOptions.value)
    manufacturerLinks.value = normalizeLinks(data?.manufacturer_links, manufacturerOptions.value)
    return {
      brand_options: brandOptions.value,
      manufacturer_options: manufacturerOptions.value,
      default_brand: defaultBrand.value,
      default_manufacturer: defaultManufacturer.value,
      brand_manufacturer_map: brandManufacturerMap.value,
      brand_links: brandLinks.value,
      manufacturer_links: manufacturerLinks.value,
    }
  }

  async function fetchIntegrations() {
    try {
      const { data } = await api.get('/api/v1/settings/integrations')
      integrations.value = normalizeIntegrations(data)
      await cacheSnapshot('settings.integrations', integrations.value)
      return integrations.value
    } catch (error) {
      if (!isOnline()) {
        const cached = await readSnapshot('settings.integrations')
        if (cached && typeof cached === 'object') {
          integrations.value = normalizeIntegrations(cached)
          return integrations.value
        }
      }
      throw error
    }
  }

  async function updateIntegrations(payload) {
    const normalized = normalizeIntegrations(payload)
    if (!isOnline()) {
      integrations.value = normalized
      await queueMutation({
        method: 'put',
        url: '/api/v1/settings/integrations',
        data: normalized,
        conflictPolicy: 'guarded',
      })
      return integrations.value
    }

    const { data } = await api.put('/api/v1/settings/integrations', normalized)
    integrations.value = normalizeIntegrations(data)
    return integrations.value
  }

  async function testIntegrationConnection(plugin, config) {
    const pluginKey = String(plugin || '').trim().toLowerCase()
    if (!pluginKey) {
      throw new Error('Plugin is required')
    }
    const payload = {
      config: normalizeIntegrationPlugin(config || {}, DEFAULT_INTEGRATIONS[pluginKey] || DEFAULT_INTEGRATIONS.eventory_instances[0]),
    }
    const { data } = await api.post(`/api/v1/settings/integrations/${pluginKey}/test`, payload)
    return data
  }

  async function previewEventoryProducts(instanceId) {
    const key = String(instanceId || '').trim()
    if (!key) {
      throw new Error('Eventory instance is required')
    }
    const { data } = await api.get(`/api/v1/settings/integrations/eventory/${encodeURIComponent(key)}/products`)
    return {
      count: Number(data?.count || 0),
      products: Array.isArray(data?.products) ? data.products : [],
    }
  }

  async function syncEventoryProducts(instanceId) {
    const key = String(instanceId || '').trim()
    if (!key) {
      throw new Error('Eventory instance is required')
    }
    const { data } = await api.post(`/api/v1/settings/integrations/eventory/${encodeURIComponent(key)}/sync`, {}, { timeout: 12000 })
    return {
      started: Boolean(data?.started),
      message: String(data?.message || '').trim(),
    }
  }

  async function getEventorySyncStatus(instanceId) {
    const key = String(instanceId || '').trim()
    if (!key) {
      throw new Error('Eventory instance is required')
    }
    const { data } = await api.get(`/api/v1/settings/integrations/eventory/${encodeURIComponent(key)}/sync`, { timeout: 12000 })
    return {
      running: Boolean(data?.running),
      progress_current: Number(data?.progress_current || 0),
      progress_total: Number(data?.progress_total || 0),
      progress_percent: Number(data?.progress_percent || 0),
      started_at: String(data?.started_at || '').trim() || null,
      finished_at: String(data?.finished_at || '').trim() || null,
      imported: Number(data?.imported || 0),
      updated: Number(data?.updated || 0),
      skipped: Number(data?.skipped || 0),
      total: Number(data?.total || 0),
      message: String(data?.message || '').trim() || null,
    }
  }

  async function fetchAuthSsoSettings() {
    try {
      const { data } = await api.get('/api/v1/settings/auth-sso')
      authSsoSettings.value = normalizeAuthSsoSettings(data)
      await cacheSnapshot('settings.authSso', authSsoSettings.value)
      return authSsoSettings.value
    } catch (error) {
      if (!isOnline()) {
        const cached = await readSnapshot('settings.authSso')
        if (cached && typeof cached === 'object') {
          authSsoSettings.value = normalizeAuthSsoSettings(cached)
          return authSsoSettings.value
        }
      }
      throw error
    }
  }

  async function updateAuthSsoSettings(payload) {
    const normalized = normalizeAuthSsoSettings(payload)
    if (!isOnline()) {
      authSsoSettings.value = normalized
      await queueMutation({
        method: 'put',
        url: '/api/v1/settings/auth-sso',
        data: normalized,
        conflictPolicy: 'guarded',
      })
      return authSsoSettings.value
    }
    const { data } = await api.put('/api/v1/settings/auth-sso', normalized)
    authSsoSettings.value = normalizeAuthSsoSettings(data)
    return authSsoSettings.value
  }

  async function fetchCompanyProfile() {
    const { data } = await api.get('/api/v1/settings/company-profile')
    companyProfile.value = normalizeCompanyProfile(data)
    localStorage.setItem('sw_company_default_language', companyProfile.value.default_language || 'en')
    return companyProfile.value
  }

  async function updateCompanyProfile(payload) {
    const body = normalizeCompanyProfile(payload)
    const { data } = await api.put('/api/v1/settings/company-profile', {
      company_name: body.company_name,
      default_language: body.default_language,
      logo_file_id: body.logo_file_id,
      logo_light_wide_file_id: body.logo_light_wide_file_id,
      logo_light_small_file_id: body.logo_light_small_file_id,
      logo_dark_wide_file_id: body.logo_dark_wide_file_id,
      logo_dark_small_file_id: body.logo_dark_small_file_id,
      currency: body.currency,
      vat_number: body.vat_number,
      address_line1: body.address_line1,
      address_line2: body.address_line2,
      postal_code: body.postal_code,
      city: body.city,
      country: body.country,
      contact_email: body.contact_email,
      contact_phone: body.contact_phone,
      website: body.website,
    })
    companyProfile.value = normalizeCompanyProfile(data)
    localStorage.setItem('sw_company_default_language', companyProfile.value.default_language || 'en')
    return companyProfile.value
  }

  async function fetchLabelTemplates() {
    const { data } = await api.get('/api/v1/settings/label-templates')
    labelTemplates.value = Array.isArray(data) ? data : []
    return labelTemplates.value
  }

  async function createLabelTemplate(payload) {
    const { data } = await api.post('/api/v1/settings/label-templates', payload)
    const idx = labelTemplates.value.findIndex(item => item.id === data?.id)
    if (idx >= 0) {
      labelTemplates.value.splice(idx, 1, data)
    } else {
      labelTemplates.value.unshift(data)
    }
    return data
  }

  async function updateLabelTemplate(templateId, payload) {
    const { data } = await api.put(`/api/v1/settings/label-templates/${encodeURIComponent(templateId)}`, payload)
    const idx = labelTemplates.value.findIndex(item => item.id === data?.id)
    if (idx >= 0) {
      labelTemplates.value.splice(idx, 1, data)
    } else {
      labelTemplates.value.unshift(data)
    }
    return data
  }

  async function deleteLabelTemplate(templateId) {
    await api.delete(`/api/v1/settings/label-templates/${encodeURIComponent(templateId)}`)
    labelTemplates.value = labelTemplates.value.filter(item => item.id !== templateId)
  }

  async function uploadStorageFile({ file, entityType = null, entityId = null, category = null }) {
    if (!file) {
      throw new Error('File is required')
    }
    const formData = new FormData()
    formData.append('file', file)
    if (entityType) formData.append('entity_type', String(entityType))
    if (entityId !== null && entityId !== undefined && entityId !== '') formData.append('entity_id', String(entityId))
    if (category) formData.append('category', String(category))

    const { data } = await api.post('/api/v1/storage/files', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  }

  async function listStorageFiles({ entityType = null, entityId = null, category = null } = {}) {
    const params = {}
    if (entityType) params.entity_type = entityType
    if (entityId !== null && entityId !== undefined && entityId !== '') params.entity_id = entityId
    if (category) params.category = category
    const { data } = await api.get('/api/v1/storage/files', { params })
    return Array.isArray(data) ? data : []
  }

  async function deleteStorageFile(fileId) {
    await api.delete(`/api/v1/storage/files/${encodeURIComponent(fileId)}`)
  }

  function normalizeCompanyProfile(value) {
    const source = value && typeof value === 'object' ? value : DEFAULT_COMPANY_PROFILE
    const logoIdNum = Number(source.logo_file_id)
    const logoLightWideIdNum = Number(source.logo_light_wide_file_id)
    const logoLightSmallIdNum = Number(source.logo_light_small_file_id)
    const logoDarkWideIdNum = Number(source.logo_dark_wide_file_id)
    const logoDarkSmallIdNum = Number(source.logo_dark_small_file_id)
    return {
      company_name: String(source.company_name || '').trim() || null,
      default_language: ['en', 'sv'].includes(String(source.default_language || '').trim().toLowerCase())
        ? String(source.default_language || '').trim().toLowerCase()
        : 'en',
      logo_file_id: Number.isFinite(logoIdNum) && logoIdNum > 0 ? logoIdNum : null,
      logo_url: String(source.logo_url || '').trim() || null,
      logo_light_wide_file_id: Number.isFinite(logoLightWideIdNum) && logoLightWideIdNum > 0 ? logoLightWideIdNum : null,
      logo_light_wide_url: String(source.logo_light_wide_url || '').trim() || null,
      logo_light_small_file_id: Number.isFinite(logoLightSmallIdNum) && logoLightSmallIdNum > 0 ? logoLightSmallIdNum : null,
      logo_light_small_url: String(source.logo_light_small_url || '').trim() || null,
      logo_dark_wide_file_id: Number.isFinite(logoDarkWideIdNum) && logoDarkWideIdNum > 0 ? logoDarkWideIdNum : null,
      logo_dark_wide_url: String(source.logo_dark_wide_url || '').trim() || null,
      logo_dark_small_file_id: Number.isFinite(logoDarkSmallIdNum) && logoDarkSmallIdNum > 0 ? logoDarkSmallIdNum : null,
      logo_dark_small_url: String(source.logo_dark_small_url || '').trim() || null,
      currency: String(source.currency || 'SEK').trim().toUpperCase() || 'SEK',
      vat_number: String(source.vat_number || '').trim() || null,
      address_line1: String(source.address_line1 || '').trim() || null,
      address_line2: String(source.address_line2 || '').trim() || null,
      postal_code: String(source.postal_code || '').trim() || null,
      city: String(source.city || '').trim() || null,
      country: String(source.country || '').trim() || null,
      contact_email: String(source.contact_email || '').trim() || null,
      contact_phone: String(source.contact_phone || '').trim() || null,
      website: String(source.website || '').trim() || null,
    }
  }

  function normalizeOptions(options) {
    const seen = new Set()
    const normalized = []
    for (const raw of options || []) {
      const value = String(raw || '').trim().toLowerCase()
      if (!value || seen.has(value)) continue
      seen.add(value)
      normalized.push(value)
    }
    return normalized.length ? normalized : [...DEFAULT_LOCATION_TYPES]
  }

  function normalizeCategoryPaths(paths) {
    const result = []
    const seen = new Set()
    for (const path of paths || []) {
      if (!Array.isArray(path)) continue
      const parts = path.map(part => String(part || '').trim()).filter(Boolean)
      if (!parts.length) continue
      const key = parts.map(part => part.toLowerCase()).join(' > ')
      if (seen.has(key)) continue
      seen.add(key)
      result.push(parts)
    }
    return result.length ? result : DEFAULT_CATEGORY_PREFILL_PATHS.map(path => [...path])
  }

  function normalizeCaseOptions(options, fallback) {
    const result = []
    const seen = new Set()
    for (const raw of options || []) {
      const value = String(raw || '').trim()
      if (!value) continue
      const key = value.toLowerCase()
      if (seen.has(key)) continue
      seen.add(key)
      result.push(value)
    }
    return result.length ? result : [...fallback]
  }

  function normalizeSelected(value, options) {
    const candidate = String(value || '').trim().toLowerCase()
    if (!options.length) return null
    if (!candidate) return options[0]
    const matched = options.find(option => option.toLowerCase() === candidate)
    return matched || options[0]
  }

  function findMatchingOption(value, options) {
    const candidate = String(value || '').trim().toLowerCase()
    if (!candidate) return null
    return options.find(option => option.toLowerCase() === candidate) || null
  }

  function normalizeMap(inputMap, keysOptions, valuesOptions) {
    if (!inputMap || typeof inputMap !== 'object') return {}
    const output = {}
    for (const [rawKey, rawValue] of Object.entries(inputMap)) {
      const key = findMatchingOption(rawKey, keysOptions)
      const value = findMatchingOption(rawValue, valuesOptions)
      if (!key || !value) continue
      output[key] = value
    }
    return output
  }

  function normalizeLinks(inputLinks, options) {
    if (!inputLinks || typeof inputLinks !== 'object') return {}
    const output = {}
    for (const [rawKey, rawUrl] of Object.entries(inputLinks)) {
      const key = findMatchingOption(rawKey, options)
      const url = String(rawUrl || '').trim()
      if (!key || !url) continue
      output[key] = url
    }
    return output
  }

  function normalizeIntegrationPlugin(plugin, fallback) {
    const syncInterval = Number(plugin?.sync_interval_minutes ?? fallback.sync_interval_minutes)
    const priceMargin = Number(plugin?.price_margin_percent ?? fallback.price_margin_percent)
    const lastSyncImported = Number(plugin?.last_sync_imported ?? fallback.last_sync_imported)
    const lastSyncUpdated = Number(plugin?.last_sync_updated ?? fallback.last_sync_updated)
    const lastSyncSkipped = Number(plugin?.last_sync_skipped ?? fallback.last_sync_skipped)
    const lastSyncTotal = Number(plugin?.last_sync_total ?? fallback.last_sync_total)
    const syncProgressCurrent = Number(plugin?.sync_progress_current ?? 0)
    const syncProgressTotal = Number(plugin?.sync_progress_total ?? 0)
    const syncProgressPercent = Number(plugin?.sync_progress_percent ?? 0)
    return {
      enabled: Boolean(plugin?.enabled),
      api_url: String(plugin?.api_url ?? fallback.api_url ?? '').trim() || String(fallback.api_url || '').trim(),
      api_key: String(plugin?.api_key || '').trim(),
      username: String(plugin?.username || '').trim(),
      password: String(plugin?.password || '').trim(),
      token_endpoint: String(plugin?.token_endpoint || '').trim(),
      supplier_name: String(plugin?.supplier_name || fallback.supplier_name || '').trim() || fallback.supplier_name,
      sync_interval_minutes: Number.isFinite(syncInterval) && syncInterval > 0 ? Math.floor(syncInterval) : 0,
      price_margin_percent: Number.isFinite(priceMargin) && priceMargin > 0 ? priceMargin : 0,
      last_sync_at: String(plugin?.last_sync_at || '').trim() || null,
      last_sync_imported: Number.isFinite(lastSyncImported) && lastSyncImported > 0 ? Math.floor(lastSyncImported) : 0,
      last_sync_updated: Number.isFinite(lastSyncUpdated) && lastSyncUpdated > 0 ? Math.floor(lastSyncUpdated) : 0,
      last_sync_skipped: Number.isFinite(lastSyncSkipped) && lastSyncSkipped > 0 ? Math.floor(lastSyncSkipped) : 0,
      last_sync_total: Number.isFinite(lastSyncTotal) && lastSyncTotal > 0 ? Math.floor(lastSyncTotal) : 0,
      sync_running: Boolean(plugin?.sync_running),
      sync_started_at: String(plugin?.sync_started_at || '').trim() || null,
      sync_finished_at: String(plugin?.sync_finished_at || '').trim() || null,
      sync_progress_current: Number.isFinite(syncProgressCurrent) && syncProgressCurrent > 0 ? Math.floor(syncProgressCurrent) : 0,
      sync_progress_total: Number.isFinite(syncProgressTotal) && syncProgressTotal > 0 ? Math.floor(syncProgressTotal) : 0,
      sync_progress_percent: Number.isFinite(syncProgressPercent) && syncProgressPercent > 0 ? Math.max(0, Math.min(100, Math.floor(syncProgressPercent))) : 0,
      sync_message: String(plugin?.sync_message || '').trim() || null,
    }
  }

  function normalizeEventoryInstance(instance, index = 0) {
    const fallback = DEFAULT_INTEGRATIONS.eventory_instances[0]
    const normalized = normalizeIntegrationPlugin(instance, fallback)
    const normalizedName = String(instance?.name || '').trim() || `Eventory ${index + 1}`
    const idFromName = String(normalizedName)
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '')
    const id = String(instance?.id || '')
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '') || idFromName || `eventory-${index + 1}`
    const name = normalizedName
    return {
      id,
      name,
      ...normalized,
    }
  }

  function normalizeIntegrations(value) {
    const rawInstances = Array.isArray(value?.eventory_instances)
      ? value.eventory_instances
      : (value?.eventory ? [{ id: 'eventory-main', name: 'Eventory Main', ...value.eventory }] : [])
    const eventoryInstances = rawInstances
      .map((instance, index) => normalizeEventoryInstance(instance, index))
      .filter(instance => instance.id)

    return {
      eventory_instances: eventoryInstances.length ? eventoryInstances : [normalizeEventoryInstance(DEFAULT_INTEGRATIONS.eventory_instances[0], 0)],
    }
  }

  function cloneIntegrations(value) {
    return {
      eventory_instances: (value.eventory_instances || []).map(instance => ({ ...instance })),
    }
  }

  function normalizeAuthSsoProvider(item = {}) {
    return {
      key: String(item?.key || '').trim(),
      display_name: String(item?.display_name || '').trim() || null,
      enabled: Boolean(item?.enabled),
      allow_auto_create: item?.allow_auto_create === null || item?.allow_auto_create === undefined ? null : Boolean(item?.allow_auto_create),
      issuer: String(item?.issuer || '').trim() || null,
      client_id: String(item?.client_id || '').trim() || null,
      client_secret: String(item?.client_secret || '').trim() || null,
      authorization_endpoint: String(item?.authorization_endpoint || '').trim() || null,
      token_endpoint: String(item?.token_endpoint || '').trim() || null,
      jwks_uri: String(item?.jwks_uri || '').trim() || null,
      scopes: String(item?.scopes || '').trim() || null,
      group_claim: String(item?.group_claim || '').trim() || null,
      email_claim: String(item?.email_claim || '').trim() || null,
      name_claim: String(item?.name_claim || '').trim() || null,
      subject_claim: String(item?.subject_claim || '').trim() || null,
      idp_entity_id: String(item?.idp_entity_id || '').trim() || null,
      idp_sso_url: String(item?.idp_sso_url || '').trim() || null,
      idp_x509_cert: String(item?.idp_x509_cert || '').trim() || null,
      sp_entity_id: String(item?.sp_entity_id || '').trim() || null,
      acs_url: String(item?.acs_url || '').trim() || null,
      group_attribute: String(item?.group_attribute || '').trim() || null,
      email_attribute: String(item?.email_attribute || '').trim() || null,
      name_attribute: String(item?.name_attribute || '').trim() || null,
      subject_attribute: String(item?.subject_attribute || '').trim() || null,
    }
  }

  function normalizeAuthSsoSettings(value) {
    const source = value && typeof value === 'object' ? value : DEFAULT_AUTH_SSO_SETTINGS
    const roleMapRaw = source.group_role_map && typeof source.group_role_map === 'object' ? source.group_role_map : {}
    const roleMap = {}
    for (const [k, v] of Object.entries(roleMapRaw)) {
      const key = String(k || '').trim()
      const role = String(v || '').trim().toLowerCase()
      if (!key || !['admin', 'manager', 'viewer'].includes(role)) continue
      roleMap[key] = role
    }

    return {
      enabled: Boolean(source.enabled),
      auto_create_users: Boolean(source.auto_create_users),
      sync_roles_on_login: Boolean(source.sync_roles_on_login),
      default_role: ['admin', 'manager', 'viewer'].includes(String(source.default_role || '').toLowerCase())
        ? String(source.default_role || '').toLowerCase()
        : 'viewer',
      group_role_map: roleMap,
      oidc_providers: Array.isArray(source.oidc_providers)
        ? source.oidc_providers.map(normalizeAuthSsoProvider).filter(item => item.key)
        : [],
      saml_providers: Array.isArray(source.saml_providers)
        ? source.saml_providers.map(normalizeAuthSsoProvider).filter(item => item.key)
        : [],
    }
  }

  function cloneAuthSsoSettings(value) {
    const normalized = normalizeAuthSsoSettings(value)
    return {
      ...normalized,
      group_role_map: { ...(normalized.group_role_map || {}) },
      oidc_providers: (normalized.oidc_providers || []).map(item => ({ ...item })),
      saml_providers: (normalized.saml_providers || []).map(item => ({ ...item })),
    }
  }

  return {
    locationTypes,
    categoryPrefillPaths,
    brandOptions,
    manufacturerOptions,
    defaultBrand,
    defaultManufacturer,
    brandManufacturerMap,
    brandLinks,
    manufacturerLinks,
    integrations,
    authSsoSettings,
    companyProfile,
    labelTemplates,
    loading,
    fetchLocationTypes,
    updateLocationTypes,
    fetchCategoryPrefillPaths,
    updateCategoryPrefillPaths,
    fetchProductDefaults,
    updateProductDefaults,
    fetchIntegrations,
    updateIntegrations,
    testIntegrationConnection,
    previewEventoryProducts,
    syncEventoryProducts,
    getEventorySyncStatus,
    fetchAuthSsoSettings,
    updateAuthSsoSettings,
    fetchCompanyProfile,
    updateCompanyProfile,
    fetchLabelTemplates,
    createLabelTemplate,
    updateLabelTemplate,
    deleteLabelTemplate,
    uploadStorageFile,
    listStorageFiles,
    deleteStorageFile,
    normalizeOptions,
    normalizeCategoryPaths,
    normalizeCaseOptions,
    normalizeSelected,
    normalizeMap,
    normalizeLinks,
    normalizeIntegrations,
    cloneIntegrations,
    normalizeAuthSsoSettings,
    cloneAuthSsoSettings,
    normalizeCompanyProfile,
  }
})
