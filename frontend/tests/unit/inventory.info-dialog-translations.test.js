import { describe, expect, it } from 'vitest'

import en from '../../src/i18n/locales/en'
import sv from '../../src/i18n/locales/sv'

const requiredKeys = [
  'deviceTitle',
  'productTitle',
  'available',
  'reserved',
  'inUse',
  'idType',
  'categoryBrandManufacturer',
  'dailyRateMaintenanceInterval',
  'weightSize',
  'linkedDevices',
  'deviceStatusCondition',
  'deviceStatusConditionLocation',
  'noDevicesLinkedToProduct',
  'linkedJobs',
  'requiredPicked',
  'noLinkedJobsForProduct',
  'productDocuments',
  'deviceDocuments',
  'notAvailable',
  'unassigned',
]

describe('inventory info dialog translations', () => {
  it('defines all required keys in both English and Swedish locales', () => {
    for (const key of requiredKeys) {
      expect(en.inventory.infoDialogs[key]).toBeTruthy()
      expect(sv.inventory.infoDialogs[key]).toBeTruthy()
    }
  })
})
