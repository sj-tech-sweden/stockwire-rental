/**
 * Grouped product specification fields.
 *
 * Keeps structured data (mixer I/O counts, cable attributes, speaker details, …) in a single
 * `specs` JSON column on the product instead of ad-hoc custom fields, while
 * only exposing the fields that are valid for a given product (matched by
 * product_type and/or category). Stagewire reads `specs.inputs` / `specs.outputs`
 * to suggest a mixer; cable attributes drive cabling/planning views.
 */

// Re-used connector menu (mirrors the backend cable prefill options).
export const COMMON_CONNECTOR_OPTIONS = [
  'PowerCON True1', 'PowerCON 20A', 'Schuko', 'CEE 16A', 'CEE 32A', 'CEE 64A', 'CEE 128A',
  'IEC C13', 'IEC C19', 'XLR 3-pin', 'XLR 5-pin', 'EtherCON RJ45', 'RJ45', 'USB-A', 'USB-C',
  'BNC', 'SDI BNC', 'HDMI Type A', 'DisplayPort', 'HDMI', 'XLR', 'TRS 6.35mm', 'TS 6.35mm',
  'RCA', 'Speakon NL2', 'Speakon NL4',
]

export const STAGEWIRE_CONNECTOR_OPTIONS = [
  'xlr3', 'xlr5', 'trs', 'speakon', 'dante', 'aes50', 'madi', 'avb', 'ethernet',
  'ethercon', 'fiber', 'sdi', 'hdmi', 'displayport', 'bnc', 'usb', 'dmx',
  'powercon', 'schuko', 'cee16',
]

const CONNECTOR_DIRECTIONS = ['in', 'out', 'both']
const CONNECTOR_SIGNALS = ['audio', 'video', 'dmx', 'power', 'data']

// Field definitions, keyed by spec key. `type` controls the editor control.
export const PRODUCT_SPEC_FIELDS = {
  // Cables
  cable_type: {
    labelKey: 'inventory.specCableType',
    type: 'select',
    options: ['XLR', 'PowerCon', 'DMX', 'Ethernet', 'TRS', 'BNC', 'HDMI', 'Other'],
  },
  connector_a: { labelKey: 'inventory.specConnectorA', type: 'select', options: COMMON_CONNECTOR_OPTIONS },
  connector_b: { labelKey: 'inventory.specConnectorB', type: 'select', options: COMMON_CONNECTOR_OPTIONS },
  length_m: { labelKey: 'inventory.specLengthM', type: 'number', min: 0, step: 0.1, unit: 'm' },
  cable_area_mm2: { labelKey: 'inventory.specCableArea', type: 'number', min: 0, step: 0.01, unit: 'mm²' },
  is_balanced: { labelKey: 'inventory.specBalanced', type: 'boolean' },
  // Mixers / stageboxes / splitters
  inputs: { labelKey: 'inventory.specInputs', type: 'number', min: 0, step: 1 },
  outputs: { labelKey: 'inventory.specOutputs', type: 'number', min: 0, step: 1 },
  aux: { labelKey: 'inventory.specAux', type: 'number', min: 0, step: 1 },
  matrix: { labelKey: 'inventory.specMatrix', type: 'number', min: 0, step: 1 },
  // Stagebox uses distinct keys so it never collides with the mixer group's
  // shared inputs/outputs/aux fields when both groups are added to a product.
  sb_inputs: { labelKey: 'inventory.specInputs', type: 'number', min: 0, step: 1 },
  sb_outputs: { labelKey: 'inventory.specOutputs', type: 'number', min: 0, step: 1 },
  sb_aux: { labelKey: 'inventory.specAux', type: 'number', min: 0, step: 1 },
  // Stagewire connector groups: { connector, direction, count, signal? }.
  connectors: { labelKey: 'inventory.specConnectors', type: 'connectors' },
  // Digital / modular console bus-pool model (specs.mixer.*). Edited by a
  // dedicated editor rather than the generic field controls because the data is
  // nested (dsp_inputs / bus_pool / surface / expansion_ports).
  mixer: { labelKey: 'inventory.specGroupDigitalMixer', type: 'mixer' },
  power_inlet: {
    labelKey: 'inventory.specPowerInlet',
    type: 'select',
    options: ['iec_c13', 'attached_schuko', 'powercon', 'cee16', 'other'],
  },
  // Speaker / PA
  spk_power_w: { labelKey: 'inventory.specSpkPowerW', type: 'number', min: 0, step: 1, unit: 'W' },
  spk_max_spl_db: { labelKey: 'inventory.specSpkMaxSpl', type: 'number', min: 0, step: 0.1, unit: 'dB' },
  target_spl_db: { labelKey: 'inventory.specSpkTargetSpl', type: 'number', min: 0, step: 0.1, unit: 'dB' },
  dispersion_h_deg: { labelKey: 'inventory.specSpkDispersionH', type: 'number', min: 0, max: 360, step: 1, unit: '°' },
  throw_m: { labelKey: 'inventory.specSpkThrowM', type: 'number', min: 0, step: 0.1, unit: 'm' },
  spk_impedance_ohm: { labelKey: 'inventory.specSpkImpedance', type: 'number', min: 0, step: 0.1, unit: 'Ω' },
  spk_driver_config: {
    labelKey: 'inventory.specSpkDriver',
    type: 'select',
    options: ['Full-range', '2-way', '3-way', 'Subwoofer', 'Line array', 'Monitor', 'Other'],
  },
  spk_flyable: { labelKey: 'inventory.specSpkFlyable', type: 'boolean' },
  // Lighting fixture
  lt_dmx_channels: { labelKey: 'inventory.specLtDmxChannels', type: 'number', min: 0, step: 1 },
  fixture_type: { labelKey: 'inventory.specFixtureProfileType', type: 'text' },
  channel_modes: { labelKey: 'inventory.specFixtureChannelModes', type: 'channel_modes' },
  lt_fixture_type: {
    labelKey: 'inventory.specLtFixtureType',
    type: 'select',
    options: ['Moving head', 'PAR', 'LED bar', 'Spot', 'Wash', 'Strobe', 'Fresnel', 'Blinder', 'Other'],
  },
  lt_power_w: { labelKey: 'inventory.specLtPowerW', type: 'number', min: 0, step: 1, unit: 'W' },
  lt_beam_angle: { labelKey: 'inventory.specLtBeamAngle', type: 'number', min: 0, step: 0.5, unit: '°' },
  lt_rgbwa: { labelKey: 'inventory.specLtRgbwa', type: 'boolean' },
  // Power / distro
  pw_max_current_a: { labelKey: 'inventory.specPwMaxCurrent', type: 'number', min: 0, step: 1, unit: 'A' },
  pw_phases: { labelKey: 'inventory.specPwPhases', type: 'number', min: 1, step: 1 },
  pw_inlet: { labelKey: 'inventory.specPwInlet', type: 'select', options: COMMON_CONNECTOR_OPTIONS },
  pw_outlet: { labelKey: 'inventory.specPwOutlet', type: 'select', options: COMMON_CONNECTOR_OPTIONS },
  pw_breaker_count: { labelKey: 'inventory.specPwBreakerCount', type: 'number', min: 0, step: 1 },
  // Video / projection
  vid_lumens: { labelKey: 'inventory.specVidLumens', type: 'number', min: 0, step: 1 },
  vid_resolution: {
    labelKey: 'inventory.specVidResolution',
    type: 'select',
    options: ['720p', '1080p', 'WUXGA', '1440p', '4K UHD', 'Other'],
  },
  proj_throw_ratio_min: { labelKey: 'inventory.specProjThrowRatioMin', type: 'number', min: 0, step: 0.01 },
  proj_throw_ratio_max: { labelKey: 'inventory.specProjThrowRatioMax', type: 'number', min: 0, step: 0.01 },
  proj_aspect_ratio: { labelKey: 'inventory.specProjAspectRatio', type: 'number', min: 0, step: 0.01 },
  proj_lens_shift_horizontal_pct: { labelKey: 'inventory.specProjLensShiftHorizontal', type: 'number', min: 0, step: 1, unit: '%' },
  proj_lens_shift_vertical_pct: { labelKey: 'inventory.specProjLensShiftVertical', type: 'number', min: 0, step: 1, unit: '%' },
  vid_inputs: { labelKey: 'inventory.specVidInputs', type: 'text' },
  vm_inputs: { labelKey: 'inventory.specVidMixerInputs', type: 'number', min: 0, step: 1 },
  vm_outputs: { labelKey: 'inventory.specVidMixerOutputs', type: 'number', min: 0, step: 1 },
  cam_aspect_ratio: { labelKey: 'inventory.specCamAspectRatio', type: 'text' },
  cam_sensor_diagonal_mm: { labelKey: 'inventory.specCamSensorDiagonal', type: 'number', min: 0, step: 0.1, unit: 'mm' },
  cam_sensor_width_mm: { labelKey: 'inventory.specCamSensorWidth', type: 'number', min: 0, step: 0.1, unit: 'mm' },
  cam_max_distance_m: { labelKey: 'inventory.specCamMaxDistance', type: 'number', min: 0, step: 0.1, unit: 'm' },
  lens_focal_length_min_mm: { labelKey: 'inventory.specLensFocalLengthMin', type: 'number', min: 0, step: 0.1, unit: 'mm' },
  lens_focal_length_max_mm: { labelKey: 'inventory.specLensFocalLengthMax', type: 'number', min: 0, step: 0.1, unit: 'mm' },
}

// A group is shown for a product when it already has data in `specs` (so saved
// groups survive reloads) or when the user explicitly adds it. Selection is
// manual rather than derived from a hardcoded category/product_type list, so it
// works regardless of locale or category naming (e.g. Swedish "Ljud/Mixrar").
export const PRODUCT_SPEC_GROUPS = [
  {
    key: 'cable',
    labelKey: 'inventory.specGroupCable',
    fields: ['cable_type', 'connector_a', 'connector_b', 'length_m', 'cable_area_mm2', 'is_balanced'],
  },
  {
    key: 'mixer',
    labelKey: 'inventory.specGroupMixer',
    fields: ['inputs', 'outputs', 'aux', 'matrix'],
  },
  {
    key: 'stagebox',
    labelKey: 'inventory.specGroupStagebox',
    fields: ['sb_inputs', 'sb_outputs', 'sb_aux'],
  },
  {
    key: 'speaker',
    labelKey: 'inventory.specGroupSpeaker',
    fields: [
      'spk_power_w',
      'spk_max_spl_db',
      'target_spl_db',
      'dispersion_h_deg',
      'throw_m',
      'spk_impedance_ohm',
      'spk_driver_config',
      'spk_flyable',
    ],
  },
  {
    key: 'lighting',
    labelKey: 'inventory.specGroupLighting',
    fields: [
      'fixture_type',
      'channel_modes',
      'lt_dmx_channels',
      'lt_fixture_type',
      'lt_power_w',
      'lt_beam_angle',
      'lt_rgbwa',
    ],
  },
  {
    key: 'power',
    labelKey: 'inventory.specGroupPower',
    fields: ['pw_max_current_a', 'pw_phases', 'pw_inlet', 'pw_outlet', 'pw_breaker_count'],
  },
  {
    key: 'video',
    labelKey: 'inventory.specGroupVideo',
    fields: [
      'vid_lumens',
      'vid_resolution',
      'proj_throw_ratio_min',
      'proj_throw_ratio_max',
      'proj_aspect_ratio',
      'proj_lens_shift_horizontal_pct',
      'proj_lens_shift_vertical_pct',
      'vid_inputs',
    ],
  },
  {
    key: 'video_mixer',
    labelKey: 'inventory.specGroupVideoMixer',
    fields: ['vm_inputs', 'vm_outputs'],
  },
  {
    key: 'camera',
    labelKey: 'inventory.specGroupCamera',
    fields: ['cam_aspect_ratio', 'cam_sensor_diagonal_mm', 'cam_sensor_width_mm', 'cam_max_distance_m'],
  },
  {
    key: 'lens',
    labelKey: 'inventory.specGroupLens',
    fields: ['lens_focal_length_min_mm', 'lens_focal_length_max_mm'],
  },
  {
    key: 'connectors',
    labelKey: 'inventory.specGroupConnectors',
    fields: ['connectors', 'power_inlet'],
  },
  {
    key: 'digitalMixer',
    labelKey: 'inventory.specGroupDigitalMixer',
    fields: ['mixer'],
  },
]

export function specFieldDef(key) {
  return PRODUCT_SPEC_FIELDS[key]
}

// Assumes max SPL is specified at 1 m in free field (20 dB loss per distance decade).
export function calculateSpeakerThrow(maxSplDb, targetSplDb) {
  const maxSpl = Number(maxSplDb)
  const targetSpl = Number(targetSplDb)
  if (
    maxSplDb === null || maxSplDb === undefined || maxSplDb === ''
    || targetSplDb === null || targetSplDb === undefined || targetSplDb === ''
    || !Number.isFinite(maxSpl) || !Number.isFinite(targetSpl)
  ) {
    return null
  }

  const distance = 10 ** ((maxSpl - targetSpl) / 20)
  return Number.isFinite(distance) && distance > 0 ? Number(distance.toFixed(2)) : null
}

export function calculateCameraSensorWidth(aspectRatio, diagonalMm) {
  const match = String(aspectRatio ?? '').trim().match(
    /^(\d+(?:\.\d+)?)\s*[:/xX]\s*(\d+(?:\.\d+)?)$/,
  )
  const diagonal = Number(diagonalMm)
  if (!match || !Number.isFinite(diagonal) || diagonal <= 0) return null

  const aspectWidth = Number(match[1])
  const aspectHeight = Number(match[2])
  if (
    !Number.isFinite(aspectWidth) || aspectWidth <= 0
    || !Number.isFinite(aspectHeight) || aspectHeight <= 0
  ) {
    return null
  }

  const width = diagonal * aspectWidth / Math.hypot(aspectWidth, aspectHeight)
  return Number.isFinite(width) && width > 0 ? Number(width.toFixed(2)) : null
}

export function getCameraSensorWidth(specs) {
  return calculateCameraSensorWidth(specs?.cam_aspect_ratio, specs?.cam_sensor_diagonal_mm)
    ?? getSpecValue(specs, 'cam_sensor_width_mm')
}

export function withCalculatedCameraSensorWidth(specs) {
  const next = { ...(specs || {}) }
  const width = calculateCameraSensorWidth(next.cam_aspect_ratio, next.cam_sensor_diagonal_mm)
  if (width !== null) next.cam_sensor_width_mm = width
  return next
}

export function getSpeakerThrowValue(specs, calculatedThrow) {
  return specs?.throw_m_manual === true ? getSpecValue(specs, 'throw_m') : calculatedThrow
}

export function setSpeakerThrowManualMode(specs, manual, calculatedThrow) {
  const next = { ...(specs || {}) }
  if (manual) {
    next.throw_m_manual = true
    next.throw_m = calculatedThrow
  } else {
    delete next.throw_m_manual
    next.throw_m = calculatedThrow
  }
  return next
}

// Groups that currently have at least one populated field in `specs`.
export function populatedSpecGroups(specs) {
  const s = specs || {}
  return PRODUCT_SPEC_GROUPS.filter((group) => group.fields.some((field) => {
    if (field === 'connectors') return getConnectorGroups(s).length > 0
    return s[field] !== undefined && s[field] !== null && s[field] !== ''
  }))
}

export function productSpecDisplayGroups(specs, translate) {
  const values = specs || {}
  const cameraSensorWidth = getCameraSensorWidth(values)
  return populatedSpecGroups(values).map((group) => ({
    key: group.key,
    label: translate(group.labelKey),
    fields: group.fields
      .filter((key) => key === 'cam_sensor_width_mm'
        ? cameraSensorWidth !== undefined && cameraSensorWidth !== null && cameraSensorWidth !== ''
        : values[key] !== undefined && values[key] !== null && values[key] !== '')
      .map((key) => ({
        key,
        label: translate(PRODUCT_SPEC_FIELDS[key].labelKey),
        value: key === 'cam_sensor_width_mm'
          ? cameraSensorWidth
          : PRODUCT_SPEC_FIELDS[key].type === 'boolean'
            ? translate(values[key] ? 'common.true' : 'common.false')
            : PRODUCT_SPEC_FIELDS[key].type === 'channel_modes'
              ? getFixtureChannelModes(values)
                .map((mode) => `${mode.name}: ${mode.footprint} ${translate('inventory.specLtDmxChannels')}`)
                .join(', ')
            : PRODUCT_SPEC_FIELDS[key].type === 'connectors'
              ? getConnectorGroups(values)
                .map((group) => `${group.count > 1 ? `${group.count} × ` : ''}${group.connector}${group.direction !== 'both' ? ` (${group.direction})` : ''}${group.signal ? ` · ${group.signal}` : ''}`)
                .join(', ')
              : PRODUCT_SPEC_FIELDS[key].type === 'mixer'
                ? describeMixerSpec(values, translate)
                : values[key],
      })),
  }))
}

// All groups that should be visible: populated ones plus any explicitly added.
export function activeSpecGroups(specs, explicitlyAddedKeys = []) {
  const populated = new Set(populatedSpecGroups(specs).map((g) => g.key))
  const keys = new Set([...populated, ...explicitlyAddedKeys])
  return PRODUCT_SPEC_GROUPS.filter((g) => keys.has(g.key))
}

export function removeSpecGroup(specs, groupKey) {
  const group = PRODUCT_SPEC_GROUPS.find((g) => g.key === groupKey)
  if (!group) return specs
  const next = { ...(specs || {}) }
  for (const f of group.fields) delete next[f]
  if (groupKey === 'speaker') delete next.throw_m_manual
  return next
}

export function getSpecValue(specs, key) {
  const v = specs?.[key]
  return v === undefined || v === null ? null : v
}

export function setSpecValue(specs, key, value) {
  const next = { ...(specs || {}) }
  if (value === null || value === undefined || value === '') {
    delete next[key]
  } else {
    next[key] = value
  }
  return next
}

export function getConnectorGroups(specs) {
  if (!Array.isArray(specs?.connectors)) return []
  return specs.connectors.map((entry) => {
    const raw = typeof entry === 'string' ? { connector: entry } : entry
    if (!raw || typeof raw !== 'object') return null
    const connector = String(raw.connector || '').trim().toLowerCase()
    if (!connector) return null
    const direction = CONNECTOR_DIRECTIONS.includes(String(raw.direction || '').toLowerCase())
      ? String(raw.direction).toLowerCase()
      : 'both'
    const countValue = Number(raw.count)
    const count = Number.isInteger(countValue) && countValue > 0 ? countValue : 1
    const signal = CONNECTOR_SIGNALS.includes(String(raw.signal || '').toLowerCase())
      ? String(raw.signal).toLowerCase()
      : null
    return { connector, direction, count, ...(signal ? { signal } : {}) }
  }).filter(Boolean)
}

export function addConnectorGroup(specs) {
  return {
    ...(specs || {}),
    connectors: [...getConnectorGroups(specs), { connector: 'xlr3', direction: 'both', count: 1 }],
  }
}

export function updateConnectorGroup(specs, index, field, value) {
  const groups = getConnectorGroups(specs)
  if (!groups[index] || !['connector', 'direction', 'count', 'signal'].includes(field)) return specs || {}
  const updated = { ...groups[index] }
  if (field === 'connector') {
    updated.connector = String(value || '').trim().toLowerCase()
  } else if (field === 'count') {
    const count = Number(value)
    updated.count = Number.isInteger(count) && count > 0 ? count : 1
  } else if (field === 'signal') {
    if (CONNECTOR_SIGNALS.includes(String(value || '').toLowerCase())) {
      updated.signal = String(value).toLowerCase()
    } else {
      delete updated.signal
    }
  } else {
    updated.direction = CONNECTOR_DIRECTIONS.includes(String(value || '').toLowerCase())
      ? String(value).toLowerCase()
      : 'both'
  }
  groups[index] = updated
  return { ...(specs || {}), connectors: groups }
}

export function removeConnectorGroup(specs, index) {
  const connectors = getConnectorGroups(specs).filter((_, connectorIndex) => connectorIndex !== index)
  const next = { ...(specs || {}) }
  if (connectors.length) next.connectors = connectors
  else delete next.connectors
  return next
}

export function getFixtureChannelModes(specs) {
  if (!Array.isArray(specs?.channel_modes)) return []
  return specs.channel_modes.map((mode) => ({
    name: mode && typeof mode.name === 'string' ? mode.name : '',
    footprint: mode && Number.isInteger(Number(mode.footprint)) && Number(mode.footprint) > 0
      && mode.footprint !== null && mode.footprint !== undefined && mode.footprint !== ''
      ? Number(mode.footprint)
      : null,
  }))
}

export function addFixtureChannelMode(specs) {
  return {
    ...(specs || {}),
    channel_modes: [...getFixtureChannelModes(specs), { name: '', footprint: null }],
  }
}

export function updateFixtureChannelMode(specs, index, field, value) {
  const modes = getFixtureChannelModes(specs)
  if (!modes[index] || !['name', 'footprint'].includes(field)) return specs || {}
  modes[index] = {
    ...modes[index],
    [field]: field === 'footprint'
      ? (value === null || value === '' ? null : Number(value))
      : value,
  }
  return { ...(specs || {}), channel_modes: modes }
}

export function removeFixtureChannelMode(specs, index) {
  const modes = getFixtureChannelModes(specs).filter((_, modeIndex) => modeIndex !== index)
  const next = { ...(specs || {}) }
  if (modes.length) next.channel_modes = modes
  else delete next.channel_modes
  return next
}

// --- Digital / modular console mixer model (specs.mixer) ----------------------
//
// Models the dynamic bus pool, decoupled DSP I/O, control-surface banks and
// expansion ports of modern digital consoles (see backend
// app/domain/inventory/mixer_spec.py for the matching typed model and the
// bus-pool slot math). The block is optional; every accessor falls back to a
// sensible empty structure rather than throwing on partial data.

export const MIXER_ARCHITECTURES = [
  { value: 'digital_bus_pool', labelKey: 'inventory.specMixerArchDigitalBusPool' },
  { value: 'digital_fixed', labelKey: 'inventory.specMixerArchDigitalFixed' },
  { value: 'fixed_analog', labelKey: 'inventory.specMixerArchFixedAnalog' },
]

// Bus roles that a console's bus pool may be allowed to host. Mirrors the
// backend BusPool.allowed_roles vocabulary.
export const MIXER_BUS_ROLES = ['aux', 'group', 'matrix', 'main', 'fx_send', 'sub']

const MIXER_DEFAULT_STEREO_COST = 2
const MIXER_DEFAULT_LCR_COST = 3

function emptyMixerSpec() {
  return {
    architecture: 'digital_bus_pool',
    dsp_inputs: { mono: null, stereo: null, fx_returns: null },
    bus_pool: {
      total_slots: null,
      max_mixes: null,
      stereo_slot_cost: MIXER_DEFAULT_STEREO_COST,
      lcr_slot_cost: MIXER_DEFAULT_LCR_COST,
      allowed_roles: [],
      odd_even_stereo_pairing: false,
    },
    dcas: null,
    surface: { banks: [], layers: null },
    expansion_ports: [],
  }
}

// Returns a deep, normalized mixer object, filling in nested defaults and
// tolerating partial / legacy data. Returns a fresh empty spec when none exists.
function cloneMixer(mixer) {
  if (!mixer || typeof mixer !== 'object') return emptyMixerSpec()
  const m = JSON.parse(JSON.stringify(mixer))
  if (!m.dsp_inputs || typeof m.dsp_inputs !== 'object') m.dsp_inputs = { mono: null, stereo: null, fx_returns: null }
  if (!m.bus_pool || typeof m.bus_pool !== 'object') m.bus_pool = {}
  if (!Array.isArray(m.bus_pool.allowed_roles)) m.bus_pool.allowed_roles = []
  if (m.bus_pool.stereo_slot_cost === undefined || m.bus_pool.stereo_slot_cost === null) {
    m.bus_pool.stereo_slot_cost = MIXER_DEFAULT_STEREO_COST
  }
  if (m.bus_pool.lcr_slot_cost === undefined || m.bus_pool.lcr_slot_cost === null) {
    m.bus_pool.lcr_slot_cost = MIXER_DEFAULT_LCR_COST
  }
  if (!m.surface || typeof m.surface !== 'object') m.surface = {}
  if (!Array.isArray(m.surface.banks)) m.surface.banks = []
  if (!Array.isArray(m.expansion_ports)) m.expansion_ports = []
  return m
}

export function getMixerSpec(specs) {
  const raw = specs && typeof specs === 'object' ? specs.mixer : undefined
  if (!raw || typeof raw !== 'object') return null
  return raw
}

export function addMixerSpec(specs) {
  if (getMixerSpec(specs)) return specs || {}
  return { ...(specs || {}), mixer: emptyMixerSpec() }
}

export function removeMixerSpec(specs) {
  const next = { ...(specs || {}) }
  delete next.mixer
  return next
}

// Applies a mutation to a normalized copy of the mixer block and writes it back
// to `specs`, returning a new specs object (never mutates the input).
function updateMixerSpec(specs, mutate) {
  const mixer = cloneMixer(getMixerSpec(specs))
  mutate(mixer)
  return { ...(specs || {}), mixer }
}

function toIntOrNull(value) {
  if (value === '' || value === null || value === undefined) return null
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

export function setMixerArchitecture(specs, value) {
  return updateMixerSpec(specs, (m) => { m.architecture = value || 'digital_bus_pool' })
}

export function setMixerDcas(specs, value) {
  return updateMixerSpec(specs, (m) => { m.dcas = toIntOrNull(value) })
}

export function setMixerDspInput(specs, field, value) {
  if (!['mono', 'stereo', 'fx_returns'].includes(field)) return specs || {}
  return updateMixerSpec(specs, (m) => { m.dsp_inputs[field] = toIntOrNull(value) })
}

export function setMixerBusPoolField(specs, field, value) {
  if (field === 'odd_even_stereo_pairing') {
    const bool = value === true || value === 'true'
    return updateMixerSpec(specs, (m) => { m.bus_pool.odd_even_stereo_pairing = bool })
  }
  if (!['total_slots', 'max_mixes', 'stereo_slot_cost', 'lcr_slot_cost'].includes(field)) return specs || {}
  return updateMixerSpec(specs, (m) => { m.bus_pool[field] = toIntOrNull(value) })
}

export function toggleMixerAllowedRole(specs, role) {
  return updateMixerSpec(specs, (m) => {
    const roles = Array.isArray(m.bus_pool.allowed_roles) ? [...m.bus_pool.allowed_roles] : []
    const idx = roles.indexOf(role)
    if (idx >= 0) roles.splice(idx, 1)
    else roles.push(role)
    m.bus_pool.allowed_roles = roles
  })
}

export function setMixerSurfaceLayers(specs, value) {
  return updateMixerSpec(specs, (m) => { m.surface.layers = toIntOrNull(value) })
}

export function getMixerBanks(specs) {
  const m = getMixerSpec(specs)
  return Array.isArray(m?.surface?.banks) ? m.surface.banks : []
}

export function addMixerBank(specs) {
  return updateMixerSpec(specs, (m) => {
    const banks = Array.isArray(m.surface.banks) ? m.surface.banks : []
    const id = String.fromCharCode(65 + banks.length) // A, B, C, ...
    banks.push({ id, label: '', faders: null })
    m.surface.banks = banks
  })
}

export function updateMixerBank(specs, index, field, value) {
  if (!['id', 'label', 'faders'].includes(field)) return specs || {}
  return updateMixerSpec(specs, (m) => {
    const banks = Array.isArray(m.surface.banks) ? m.surface.banks : []
    if (!banks[index]) return
    if (field === 'faders') banks[index].faders = toIntOrNull(value)
    else banks[index][field] = value
  })
}

export function removeMixerBank(specs, index) {
  return updateMixerSpec(specs, (m) => {
    const banks = Array.isArray(m.surface.banks) ? m.surface.banks : []
    m.surface.banks = banks.filter((_, i) => i !== index)
  })
}

export function getMixerExpansionPorts(specs) {
  const m = getMixerSpec(specs)
  return Array.isArray(m?.expansion_ports) ? m.expansion_ports : []
}

function emptyExpansionPort() {
  return { protocol: 'dsnake', max_channels_in: null, max_channels_out: null, slots: null, max_channels: null }
}

export function addMixerExpansionPort(specs) {
  return updateMixerSpec(specs, (m) => {
    const ports = Array.isArray(m.expansion_ports) ? m.expansion_ports : []
    ports.push(emptyExpansionPort())
    m.expansion_ports = ports
  })
}

export function updateMixerExpansionPort(specs, index, field, value) {
  const numericFields = ['max_channels_in', 'max_channels_out', 'slots', 'max_channels']
  if (!['protocol', ...numericFields].includes(field)) return specs || {}
  return updateMixerSpec(specs, (m) => {
    const ports = Array.isArray(m.expansion_ports) ? m.expansion_ports : []
    if (!ports[index]) return
    if (numericFields.includes(field)) ports[index][field] = toIntOrNull(value)
    else ports[index][field] = value
  })
}

export function removeMixerExpansionPort(specs, index) {
  return updateMixerSpec(specs, (m) => {
    const ports = Array.isArray(m.expansion_ports) ? m.expansion_ports : []
    m.expansion_ports = ports.filter((_, i) => i !== index)
  })
}

// Human-readable one-line summary for the read-only display (ProductInfoDialog).
export function describeMixerSpec(specs, translate) {
  const m = getMixerSpec(specs)
  if (!m) return ''
  const parts = []
  const arch = MIXER_ARCHITECTURES.find((a) => a.value === m.architecture)
  if (arch) parts.push(translate(arch.labelKey))
  const dsp = m.dsp_inputs || {}
  const dspTotal = (Number(dsp.mono) || 0) + 2 * (Number(dsp.stereo) || 0) + (Number(dsp.fx_returns) || 0)
  if (dspTotal > 0) parts.push(`${dspTotal} ${translate('inventory.specMixerDspChannels')}`)
  const pool = m.bus_pool || {}
  if (pool.total_slots != null) parts.push(`${pool.total_slots} ${translate('inventory.specMixerBusSlots')}`)
  if (pool.max_mixes != null) parts.push(`${pool.max_mixes} ${translate('inventory.specMixerMaxMixes')}`)
  const banks = Array.isArray(m.surface?.banks) ? m.surface.banks : []
  if (banks.length) parts.push(`${banks.length} ${translate('inventory.specMixerSurfaceBanks')}`)
  const ports = Array.isArray(m.expansion_ports) ? m.expansion_ports : []
  if (ports.length) parts.push(`${ports.length} ${translate('inventory.specMixerExpansionPortsShort')}`)
  return parts.join(' · ')
}
