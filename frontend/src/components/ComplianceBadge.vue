<template>
  <q-badge
    :color="badgeColor"
    :label="badgeLabel"
    class="q-pa-xs cursor-pointer"
  >
    <q-tooltip v-if="warnings.length">
      <div class="text-caption" style="max-width: 300px">
        <div v-for="(w, i) in warnings" :key="i" class="q-py-xs">
          <q-icon :name="w.severity === 'error' ? 'error' : 'warning'" :color="w.severity === 'error' ? 'negative' : 'warning'" class="q-mr-xs" />
          {{ w.message }}
        </div>
      </div>
    </q-tooltip>
  </q-badge>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  warnings: { type: Array, default: () => [] },
  isCompliant: { type: Boolean, default: true },
})

const hasErrors = computed(() => props.warnings.some(w => w.severity === 'error'))
const hasWarnings = computed(() => props.warnings.some(w => w.severity === 'warning'))

const badgeColor = computed(() => {
  if (hasErrors.value) return 'negative'
  if (hasWarnings.value) return 'warning'
  return 'positive'
})

const badgeLabel = computed(() => {
  if (hasErrors.value) return t('crew.complianceMissing')
  if (hasWarnings.value) return t('crew.complianceExpiringSoon')
  return t('crew.complianceValid')
})
</script>
