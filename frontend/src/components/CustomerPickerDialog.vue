<template>
  <q-dialog :model-value="modelValue" @update:model-value="emit('update:modelValue', $event)">
    <q-card style="min-width: 400px; max-width: 95vw" class="ec-card">
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6">{{ t('jobs.selectCustomer') }}</div>
        <q-space />
        <q-btn flat round dense icon="close" @click="emit('update:modelValue', false)" />
      </q-card-section>

      <q-card-section>
        <q-input v-model="search" dense outlined clearable :placeholder="t('jobs.searchJobs')">
          <template #prepend><q-icon name="search" /></template>
        </q-input>
      </q-card-section>

      <q-card-section class="q-pt-none" style="max-height: 50vh; overflow: auto">
        <q-list bordered separator class="rounded-borders">
          <q-item
            v-for="customer in filteredCustomers"
            :key="customer.id"
            clickable
            :active="customer.id === selectedId"
            active-class="bg-primary text-white"
            @click="selectCustomer(customer)"
          >
            <q-item-section>
              <q-item-label>{{ customer.name }}</q-item-label>
              <q-item-label v-if="customer.email" caption>{{ customer.email }}</q-item-label>
            </q-item-section>
          </q-item>
          <q-item v-if="!filteredCustomers.length">
            <q-item-section>
              <q-item-label caption>{{ t('jobs.noDescription') }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  modelValue: Boolean,
  customers: { type: Array, default: () => [] },
  selectedId: { type: Number, default: null },
})

const emit = defineEmits(['update:modelValue', 'select'])

const { t } = useI18n()
const search = ref('')

const filteredCustomers = computed(() => {
  const term = search.value.trim().toLowerCase()
  if (!term) return props.customers
  return props.customers.filter(c =>
    String(c.name || '').toLowerCase().includes(term) ||
    String(c.email || '').toLowerCase().includes(term)
  )
})

function selectCustomer(customer) {
  emit('select', customer)
  emit('update:modelValue', false)
}
</script>
