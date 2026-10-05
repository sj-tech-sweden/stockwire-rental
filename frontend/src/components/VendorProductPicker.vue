<template>
  <q-dialog
    :model-value="modelValue"
    @update:model-value="(v) => emit('update:modelValue', v)"
    persistent
  >
    <q-card style="width: 1400px; max-width: 98vw; min-height: 600px" class="ec-card">
      <q-card-section class="row items-center">
        <div class="text-h6">{{ title || t('vendorCatalog.selectVendorItem') }}</div>
        <q-space />
        <q-btn flat round dense icon="close" @click="emit('update:modelValue', false)" />
      </q-card-section>

      <q-card-section class="q-pt-none">
        <VendorProductTable :vendor-id="vendorId" :selectable="true" @select="select" />
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import VendorProductTable from './VendorProductTable.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  vendorId: { type: [Number, null], default: null },
  title: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'select'])

const { t } = useI18n()

function select(row) {
  emit('select', row)
  emit('update:modelValue', false)
}
</script>
