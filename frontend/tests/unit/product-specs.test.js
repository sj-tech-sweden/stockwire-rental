import { describe, expect, it } from 'vitest'
import {
  calculateSpeakerThrow,
  getSpeakerThrowValue,
  PRODUCT_SPEC_GROUPS,
  PRODUCT_SPEC_FIELDS,
  productSpecDisplayGroups,
  removeSpecGroup,
  setSpeakerThrowManualMode,
} from '../../src/utils/productSpecs.js'

describe('speaker product specifications', () => {
  it('exposes dispersion and calculated throw in the speaker group', () => {
    const speakerFields = PRODUCT_SPEC_GROUPS.find((group) => group.key === 'speaker').fields

    expect(speakerFields).toContain('dispersion_h_deg')
    expect(speakerFields).toContain('throw_m')
    expect(speakerFields).toContain('target_spl_db')
    expect(PRODUCT_SPEC_FIELDS.dispersion_h_deg.unit).toBe('°')
    expect(PRODUCT_SPEC_FIELDS.throw_m.unit).toBe('m')
  })

  it('calculates free-field throw from max SPL and target SPL', () => {
    expect(calculateSpeakerThrow(100, 94)).toBe(2)
    expect(calculateSpeakerThrow(100, 100)).toBe(1)
    expect(calculateSpeakerThrow(94, 100)).toBe(0.5)
  })

  it('does not calculate throw when either SPL value is missing or invalid', () => {
    expect(calculateSpeakerThrow(null, 94)).toBeNull()
    expect(calculateSpeakerThrow(100, null)).toBeNull()
    expect(calculateSpeakerThrow('not-a-number', 94)).toBeNull()
    expect(calculateSpeakerThrow(100, 'not-a-number')).toBeNull()
  })

  it('removes manual throw mode with the speaker specification group', () => {
    expect(removeSpecGroup({ throw_m: 12, throw_m_manual: true, spk_power_w: 500 }, 'speaker')).toEqual({})
  })

  it('uses a manually entered throw only when manual mode is enabled', () => {
    expect(getSpeakerThrowValue({ throw_m: 12, throw_m_manual: true }, 10)).toBe(12)
    expect(getSpeakerThrowValue({ throw_m: 12 }, 10)).toBe(10)
    expect(setSpeakerThrowManualMode({ throw_m: 12 }, true, 10)).toEqual({
      throw_m: 10,
      throw_m_manual: true,
    })
    expect(setSpeakerThrowManualMode({ throw_m: 12, throw_m_manual: true }, false, 10)).toEqual({
      throw_m: 10,
    })
  })

  describe('video product specifications', () => {
    it('exposes separate video mixer input and output counts', () => {
      const videoMixerFields = PRODUCT_SPEC_GROUPS.find((group) => group.key === 'video_mixer').fields

      expect(videoMixerFields).toEqual(['vm_inputs', 'vm_outputs'])
      expect(PRODUCT_SPEC_FIELDS.vm_inputs.type).toBe('number')
      expect(PRODUCT_SPEC_FIELDS.vm_outputs.type).toBe('number')
    })

    it('exposes camera and lens geometry for camera coverage', () => {
      const cameraFields = PRODUCT_SPEC_GROUPS.find((group) => group.key === 'camera').fields
      const lensFields = PRODUCT_SPEC_GROUPS.find((group) => group.key === 'lens').fields

      expect(cameraFields).toEqual(['cam_sensor_width_mm', 'cam_max_distance_m'])
      expect(lensFields).toEqual(['lens_focal_length_min_mm', 'lens_focal_length_max_mm'])
      expect(PRODUCT_SPEC_FIELDS.cam_sensor_width_mm.unit).toBe('mm')
      expect(PRODUCT_SPEC_FIELDS.cam_max_distance_m.unit).toBe('m')
      expect(PRODUCT_SPEC_FIELDS.lens_focal_length_min_mm.unit).toBe('mm')
      expect(PRODUCT_SPEC_FIELDS.lens_focal_length_max_mm.unit).toBe('mm')
    })

    it('formats all populated camera and lens specs for product info', () => {
      const translate = (key) => ({
        'inventory.specGroupCamera': 'Camera',
        'inventory.specCamSensorWidth': 'Sensor Width (mm)',
        'inventory.specGroupLens': 'Lens',
        'inventory.specLensFocalLengthMin': 'Minimum Focal Length (mm)',
        'common.true': 'True',
      }[key] || key)

      expect(productSpecDisplayGroups({
        cam_sensor_width_mm: 23.5,
        cam_max_distance_m: 0,
        lens_focal_length_min_mm: 24,
        lens_focal_length_max_mm: 70,
        spk_flyable: true,
      }, translate)).toEqual([
        {
          key: 'speaker',
          label: 'inventory.specGroupSpeaker',
          fields: [{ key: 'spk_flyable', label: 'inventory.specSpkFlyable', value: 'True' }],
        },
        {
          key: 'camera',
          label: 'Camera',
          fields: [
            { key: 'cam_sensor_width_mm', label: 'Sensor Width (mm)', value: 23.5 },
            { key: 'cam_max_distance_m', label: 'inventory.specCamMaxDistance', value: 0 },
          ],
        },
        {
          key: 'lens',
          label: 'Lens',
          fields: [
            { key: 'lens_focal_length_min_mm', label: 'Minimum Focal Length (mm)', value: 24 },
            { key: 'lens_focal_length_max_mm', label: 'inventory.specLensFocalLengthMax', value: 70 },
          ],
        },
      ])
    })
  })
})
