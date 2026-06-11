<template>
  <q-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)">
    <q-card style="width: min(460px, 95vw)">
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6">{{ t('scan.scannerShortcuts') }}</div>
        <q-space />
        <q-btn icon="close" flat round dense v-close-popup />
      </q-card-section>
      <q-card-section>
        <q-list dense>
          <q-item>
            <q-item-section>
              <q-item-label><strong>Alt+1..6</strong> {{ t('scan.shortcutSwitchPrimaryMode') }}</q-item-label>
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section>
              <q-item-label><strong>Alt+Shift+Left/Right</strong> {{ t('scan.shortcutCycleSubmode') }}</q-item-label>
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section>
              <q-item-label><strong>?</strong> {{ t('scan.shortcutOpenHelp') }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

defineProps({
  modelValue: Boolean,
})

defineEmits([
  'update:modelValue',
])

const { t } = useI18n()
</script>
