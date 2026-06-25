import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('product info dialog mobile close affordance', () => {
  it('keeps a top close button in product dialogs for phones', () => {
    for (const file of [
      'src/components/ProductInfoDialog.vue',
      'src/components/RentalProductInfoDialog.vue',
    ]) {
      const source = readFileSync(resolve(process.cwd(), file), 'utf8')
      const mobileCloseButtonPattern = /<q-btn[\s\S]*?v-if="isPhone"[\s\S]*?icon="close"[\s\S]*?@click="emit\('update:modelValue', false\)"[\s\S]*?\/>/

      expect(source).toMatch(mobileCloseButtonPattern)
      expect(source).toContain(`:aria-label="t('app.actions.close')"`)
    }
  })
})
