<template>
  <JobProductRequirementDialog
    :model-value="modelValue"
    :requirement-rows="requirementRows"
    :products="rentalProducts"
    :start-date="startDate"
    :end-date="endDate"
    :job-id="jobId"
    :include-rental-products="true"
    @update:model-value="emit('update:modelValue', $event)"
    @update:requirement-rows="emit('update:requirementRows', $event)"
  />
</template>

<script setup>
import { computed } from 'vue'
import JobProductRequirementDialog from './JobProductRequirementDialog.vue'

const props = defineProps({
  modelValue: Boolean,
  requirementRows: { type: Array, default: () => [] },
  products: { type: Array, default: () => [] },
  startDate: { type: String, default: null },
  endDate: { type: String, default: null },
  jobId: { type: Number, default: null },
})

const emit = defineEmits(['update:modelValue', 'update:requirementRows'])

const rentalProducts = computed(() =>
  props.products.filter(p => Boolean(p?.is_rental_product) || String(p?.product_type || '').toLowerCase() === 'rental')
)
</script>
