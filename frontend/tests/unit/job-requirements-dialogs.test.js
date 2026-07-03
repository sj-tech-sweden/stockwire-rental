import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('job requirement dialog regressions', () => {
  it('hides zero-quantity ghost rows in JobDialog summary list', () => {
    const source = readFileSync(resolve(process.cwd(), 'src/components/JobDialog.vue'), 'utf8')

    expect(source).toContain('const visibleRequirementRows = computed(() => (')
    expect(source).toContain("requirementRows.value.filter(row => Number(row.quantity_required || 0) > 0 || Number(row.quantity_picked || 0) > 0)")
    expect(source).toContain("{{ visibleRequirementRows.length ? t('jobs.addedRequirements') : t('jobs.noRequirements') }}")
    expect(source).toContain('<q-list v-if="visibleRequirementRows.length"')
    expect(source).toContain('<q-item v-for="row in visibleRequirementRows"')
  })

  it('allows JobDetailPage to include rental products in the requirements dialog', () => {
    const dialogSource = readFileSync(resolve(process.cwd(), 'src/components/JobProductRequirementDialog.vue'), 'utf8')
    const pageSource = readFileSync(resolve(process.cwd(), 'src/pages/JobDetailPage.vue'), 'utf8')

    expect(dialogSource).toContain('includeRentalProducts: Boolean')
    expect(dialogSource).toContain('return source.filter(product => props.includeRentalProducts || !isRentalProduct(product))')
    expect(pageSource).toContain(':include-rental-products="true"')
  })
})
