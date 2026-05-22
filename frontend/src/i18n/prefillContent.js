const CATEGORY_SEGMENT_KEY_BY_CANONICAL = {
  audio: 'settings.prefill.categories.audio',
  speakers: 'settings.prefill.categories.speakers',
  microphones: 'settings.prefill.categories.microphones',
  mixers: 'settings.prefill.categories.mixers',
  playback: 'settings.prefill.categories.playback',
  wireless: 'settings.prefill.categories.wireless',
  cables: 'settings.prefill.categories.cables',
  xlr: 'settings.prefill.categories.xlr',
  powercon: 'settings.prefill.categories.powercon',
  speakon: 'settings.prefill.categories.speakon',
  lighting: 'settings.prefill.categories.lighting',
  fixtures: 'settings.prefill.categories.fixtures',
  control: 'settings.prefill.categories.control',
  dimmers: 'settings.prefill.categories.dimmers',
  power: 'settings.prefill.categories.power',
  rigging: 'settings.prefill.categories.rigging',
  truss: 'settings.prefill.categories.truss',
  motors: 'settings.prefill.categories.motors',
  hardware: 'settings.prefill.categories.hardware',
  video: 'settings.prefill.categories.video',
  displays: 'settings.prefill.categories.displays',
  projectors: 'settings.prefill.categories.projectors',
  switchers: 'settings.prefill.categories.switchers',
  distribution: 'settings.prefill.categories.distribution',
  staging: 'settings.prefill.categories.staging',
  decks: 'settings.prefill.categories.decks',
  legs: 'settings.prefill.categories.legs',
  accessories: 'settings.prefill.categories.accessories',
  cases: 'settings.prefill.categories.cases',
  adapters: 'settings.prefill.categories.adapters',
  clamps: 'settings.prefill.categories.clamps',
  safety: 'settings.prefill.categories.safety',
  consumables: 'settings.prefill.categories.consumables',
  tape: 'settings.prefill.categories.tape',
  batteries: 'settings.prefill.categories.batteries',
  networking: 'settings.prefill.categories.networking',
  switches: 'settings.prefill.categories.switches',
}

const CUSTOM_FIELD_KEY_BY_CANONICAL = {
  'cable length': 'settings.prefill.customFields.cableLength',
  'length (m)': 'settings.prefill.customFields.lengthMeters',
  'length m': 'settings.prefill.customFields.lengthMeters',
  length: 'settings.prefill.customFields.length',
  'connector type': 'settings.prefill.customFields.connectorType',
  connector: 'settings.prefill.customFields.connector',
  source: 'settings.prefill.customFields.source',
  destination: 'settings.prefill.customFields.destination',
  'signal type': 'settings.prefill.customFields.signalType',
  'power type': 'settings.prefill.customFields.powerType',
  gauge: 'settings.prefill.customFields.gauge',
  color: 'settings.prefill.customFields.color',
  xlr: 'settings.prefill.customFields.xlr',
  dmx: 'settings.prefill.customFields.dmx',
  speakon: 'settings.prefill.customFields.speakon',
  powercon: 'settings.prefill.customFields.powercon',
  ethercon: 'settings.prefill.customFields.ethercon',
}

function canonicalize(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
}

export function translatePrefillCategorySegment(segment, t) {
  const key = CATEGORY_SEGMENT_KEY_BY_CANONICAL[canonicalize(segment)]
  return key ? t(key) : segment
}

export function translatePrefillCategoryPath(path, t) {
  if (!Array.isArray(path)) return []
  return path.map(part => translatePrefillCategorySegment(part, t))
}

export function translatePrefillCategoryLine(line, t) {
  const parts = String(line || '')
    .split('>')
    .map(part => part.trim())
    .filter(Boolean)
  if (!parts.length) return String(line || '')
  return translatePrefillCategoryPath(parts, t).join(' > ')
}

export function translateMaybePrefillCustomFieldLabel(label, t) {
  const key = CUSTOM_FIELD_KEY_BY_CANONICAL[canonicalize(label)]
  return key ? t(key) : label
}

export function translateMaybePrefillCustomFieldOption(option, t) {
  const key = CUSTOM_FIELD_KEY_BY_CANONICAL[canonicalize(option)]
  return key ? t(key) : option
}
