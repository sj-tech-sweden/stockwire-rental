import { describe, expect, it } from 'vitest'

import {
  isWorkflowRequirementComplete,
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
})
