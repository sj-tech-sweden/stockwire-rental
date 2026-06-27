import { describe, expect, it } from 'vitest'

import {
  buildScanJobLink,
  isWorkflowRequirementComplete,
  resolveDeviceScanCode,
  splitWorkflowRequirements,
  summarizeWorkflowRequirements,
  workflowRequirementProgress,
} from '../../src/utils/scan-workflow'

describe('scan workflow utilities', () => {
  it('caps progress at the required quantity', () => {
    expect(workflowRequirementProgress({ quantity_required: 4, quantity_picked: 6 })).toEqual({
      required: 4,
      picked: 6,
      packed: 4,
      percent: 100,
    })
  })

  it('treats zero remaining items as complete', () => {
    expect(isWorkflowRequirementComplete({ remaining: 0 })).toBe(true)
    expect(isWorkflowRequirementComplete({ remaining: -2 })).toBe(true)
    expect(isWorkflowRequirementComplete({ remaining: 1 })).toBe(false)
  })

  it('splits pending and completed requirements for separate lists', () => {
    const rows = [
      { product_id: 1, remaining: 2 },
      { product_id: 2, remaining: 0 },
      { product_id: 3, remaining: -1 },
    ]

    expect(splitWorkflowRequirements(rows)).toEqual({
      pending: [{ product_id: 1, remaining: 2 }],
      completed: [
        { product_id: 2, remaining: 0 },
        { product_id: 3, remaining: -1 },
      ],
    })
  })

  it('summarizes overall packed progress from all requirements', () => {
    const summary = summarizeWorkflowRequirements([
      { quantity_required: 4, quantity_picked: 2, remaining: 2 },
      { quantity_required: 1, quantity_picked: 1, remaining: 0 },
      { quantity_required: 2, quantity_picked: 5, remaining: 0 },
    ])

    expect(summary).toEqual({
      totalRequired: 7,
      totalPacked: 5,
      completedCount: 2,
      totalCount: 3,
      percent: 71,
    })
  })

  it('uses the first available device identifier for selector-based scanning', () => {
    expect(resolveDeviceScanCode({ barcode: 'BAR-1', serial_number: 'SER-1' })).toBe('BAR-1')
    expect(resolveDeviceScanCode({ asset_tag: 'DEV-1', barcode: 'BAR-1' })).toBe('DEV-1')
    expect(resolveDeviceScanCode({})).toBe('')
  })

  it('builds deep links to open scan workflows for a job', () => {
    expect(buildScanJobLink('job_out', { id: 12, job_code: 'JOB-12' })).toEqual({
      path: '/scan',
      query: {
        action: 'job_out',
        jobId: '12',
        jobCode: 'JOB-12',
      },
    })
  })
})
