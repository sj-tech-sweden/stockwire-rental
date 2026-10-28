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
  return PRODUCT_SPEC_GROUPS.filter((group) => group.fields.some((f) => s[f] !== undefined && s[f] !== null && s[f] !== ''))
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
