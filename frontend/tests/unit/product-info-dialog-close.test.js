import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('product info dialog mobile close affordance', () => {
  it('keeps a top close button in product dialogs for phones', () => {
    for (const file of [
      'src/components/ProductInfoDialog.vue',
      'src/components/RentalProductInfoDialog.vue',
    ]) {
      const source = readFileSync(resolve(process.cwd(), file), 'utf8')
      const buttonBlocks = source.match(/<q-btn[\s\S]*?\/>/g) || []
      const mobileCloseButton = buttonBlocks.find(block =>
        block.includes('v-if="isPhone"')
        && block.includes('icon="close"')
        && block.includes(`:aria-label="t('app.actions.close')"`)
        && block.includes(`@click="emit('update:modelValue', false)"`)
      )

      expect(mobileCloseButton).toBeTruthy()
    }
  })
})
