export const CATEGORY_SEGMENT_KEY_BY_CANONICAL = {
  audio: 'settings.prefill.categories.audio',
  speakers: 'settings.prefill.categories.speakers',
  microphones: 'settings.prefill.categories.microphones',
  mixers: 'settings.prefill.categories.mixers',
  playback: 'settings.prefill.categories.playback',
  wireless: 'settings.prefill.categories.wireless',
  soundcards: 'settings.prefill.categories.soundcards',
  interfaces: 'settings.prefill.categories.interfaces',
  headphones: 'settings.prefill.categories.headphones',
  amplifiers: 'settings.prefill.categories.amplifiers',
  cables: 'settings.prefill.categories.cables',
  xlr: 'settings.prefill.categories.xlr',
  powercon: 'settings.prefill.categories.powercon',
  speakon: 'settings.prefill.categories.speakon',
  jack: 'settings.prefill.categories.jack',
  cat5: 'settings.prefill.categories.cat5',
  lighting: 'settings.prefill.categories.lighting',
  fixtures: 'settings.prefill.categories.fixtures',
  'led panels': 'settings.prefill.categories.ledPanels',
  'follow spots': 'settings.prefill.categories.followSpots',
  strobes: 'settings.prefill.categories.strobes',
  'uv lights': 'settings.prefill.categories.uvLights',
  control: 'settings.prefill.categories.control',
  dimmers: 'settings.prefill.categories.dimmers',
  gels: 'settings.prefill.categories.gels',
  power: 'settings.prefill.categories.power',
  rigging: 'settings.prefill.categories.rigging',
  truss: 'settings.prefill.categories.truss',
  motors: 'settings.prefill.categories.motors',
  hardware: 'settings.prefill.categories.hardware',
  'chain hoists': 'settings.prefill.categories.chainHoists',
  'safety lines': 'settings.prefill.categories.safetyLines',
  shackles: 'settings.prefill.categories.shackles',
  slings: 'settings.prefill.categories.slings',
  video: 'settings.prefill.categories.video',
  displays: 'settings.prefill.categories.displays',
  projectors: 'settings.prefill.categories.projectors',
  cameras: 'settings.prefill.categories.cameras',
  switchers: 'settings.prefill.categories.switchers',
  recorders: 'settings.prefill.categories.recorders',
  converters: 'settings.prefill.categories.converters',
  hdmi: 'settings.prefill.categories.hdmi',
  sdi: 'settings.prefill.categories.sdi',
  displayport: 'settings.prefill.categories.displayport',
  distribution: 'settings.prefill.categories.distribution',
  staging: 'settings.prefill.categories.staging',
  decks: 'settings.prefill.categories.decks',
  legs: 'settings.prefill.categories.legs',
  drapes: 'settings.prefill.categories.drapes',
  backdrops: 'settings.prefill.categories.backdrops',
  flooring: 'settings.prefill.categories.flooring',
  tables: 'settings.prefill.categories.tables',
  accessories: 'settings.prefill.categories.accessories',
  cases: 'settings.prefill.categories.cases',
  adapters: 'settings.prefill.categories.adapters',
  clamps: 'settings.prefill.categories.clamps',
  safety: 'settings.prefill.categories.safety',
  labels: 'settings.prefill.categories.labels',
  consumables: 'settings.prefill.categories.consumables',
  tape: 'settings.prefill.categories.tape',
  batteries: 'settings.prefill.categories.batteries',
  cleaning: 'settings.prefill.categories.cleaning',
  'gaffer tape': 'settings.prefill.categories.gafferTape',
  'cable ties': 'settings.prefill.categories.cableTies',
  effects: 'settings.prefill.categories.effects',
  'smoke machines': 'settings.prefill.categories.smokeMachines',
  'haze machines': 'settings.prefill.categories.hazeMachines',
  confetti: 'settings.prefill.categories.confetti',
  pyro: 'settings.prefill.categories.pyro',
  'bubble machines': 'settings.prefill.categories.bubbleMachines',
  fans: 'settings.prefill.categories.fans',
  tools: 'settings.prefill.categories.tools',
  wrenches: 'settings.prefill.categories.wrenches',
  screwdrivers: 'settings.prefill.categories.screwdrivers',
  pliers: 'settings.prefill.categories.pliers',
  cutters: 'settings.prefill.categories.cutters',
  soldering: 'settings.prefill.categories.soldering',
  multimeters: 'settings.prefill.categories.multimeters',
  crimpers: 'settings.prefill.categories.crimpers',
  networking: 'settings.prefill.categories.networking',
  switches: 'settings.prefill.categories.switches',
  routers: 'settings.prefill.categories.routers',
  'access points': 'settings.prefill.categories.accessPoints',
  'patch panels': 'settings.prefill.categories.patchPanels',
  connectors: 'settings.prefill.categories.connectors',
  lamps: 'settings.prefill.categories.lamps',
  'lamp bulbs': 'settings.prefill.categories.lampBulbs',
  'smoke fluid': 'settings.prefill.categories.smokeFluid',
  'haze fluid': 'settings.prefill.categories.hazeFluid',
  fluids: 'settings.prefill.categories.fluids',
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
