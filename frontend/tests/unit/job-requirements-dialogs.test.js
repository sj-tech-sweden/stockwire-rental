import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import JobProductRequirementDialog from '../../src/components/JobProductRequirementDialog.vue'
import {
  filterRequirementSourceProducts,
  isVisibleRequirementRow,
} from '../../src/utils/job-requirements'

describe('job requirement dialog regressions', () => {
  it('treats only non-zero requirement rows as visible', () => {
    expect(isVisibleRequirementRow({ quantity_required: 0, quantity_picked: 0 })).toBe(false)
    expect(isVisibleRequirementRow({ quantity_required: 2, quantity_picked: 0 })).toBe(true)
    expect(isVisibleRequirementRow({ quantity_required: 0, quantity_picked: 1 })).toBe(true)
  })

  it('allows the requirements dialog source list to include rentals only when requested', () => {
    const products = [
      { id: 1, product_type: 'equipment', is_rental_product: false },
      { id: 2, product_type: 'rental', is_rental_product: false },
      { id: 3, product_type: 'equipment', is_rental_product: true },
    ]

    expect(filterRequirementSourceProducts(products)).toEqual([
      { id: 1, product_type: 'equipment', is_rental_product: false },
    ])
    expect(filterRequirementSourceProducts(products, { includeRentalProducts: true })).toEqual(products)
    expect(JobProductRequirementDialog.props.includeRentalProducts).toBeDefined()
  })

  it('enables rental inclusion from JobDetailPage', () => {
    const pageSource = readFileSync(resolve(process.cwd(), 'src/pages/JobDetailPage.vue'), 'utf8')

    expect(pageSource).toContain(':include-rental-products="true"')
  })
})
