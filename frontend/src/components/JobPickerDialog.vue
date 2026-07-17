<template>
  <q-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)" persistent>
    <q-card style="min-width: 700px; max-height: 80vh">
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6">{{ t('routePlanner.addJobs') }}</div>
        <q-space />
        <q-btn icon="close" flat round dense @click="$emit('update:modelValue', false)" />
      </q-card-section>

      <q-card-section>
        <q-input
          v-model="search"
          :label="t('common.search')"
          outlined
          dense
          class="q-mb-md"
          clearable
        >
          <template #prepend><q-icon name="search" /></template>
        </q-input>

        <q-table
          :rows="filteredJobs"
          :columns="columns"
          row-key="id"
          flat
          dense
          :rows-per-page-options="[0]"
          :loading="loading"
          hide-bottom
          style="max-height: 50vh"
          virtual-scroll
        >
          <template #body-cell-select="bodyProps">
            <q-td :props="bodyProps">
              <q-checkbox
                :model-value="selectedIds.has(bodyProps.row.id)"
                @update:model-value="toggleSelect(bodyProps.row.id)"
              />
            </q-td>
          </template>
          <template #body-cell-customer="bodyProps">
            <q-td :props="bodyProps">
              {{ bodyProps.row.customer_name || '—' }}
            </q-td>
          </template>
          <template #body-cell-venue="bodyProps">
            <q-td :props="bodyProps">
              {{ bodyProps.row.venue_name || '—' }}
            </q-td>
          </template>
        </q-table>
      </q-card-section>

      <q-card-section class="row justify-end q-gutter-sm">
        <q-btn :label="t('common.cancel')" flat @click="$emit('update:modelValue', false)" />
        <q-btn
          :label="t('routePlanner.addJobsCount', { count: selectedIds.size })"
          color="primary"
          :disable="selectedIds.size === 0"
          :loading="adding"
          @click="onAdd"
        />
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../boot/axios'

const { t } = useI18n()

const props = defineProps({
  modelValue: Boolean,
  existingJobIds: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue', 'added'])

const search = ref('')
const loading = ref(false)
const adding = ref(false)
const jobs = ref([])
const selectedIds = ref(new Set())

const columns = [
  { name: 'select', label: '', field: 'select', align: 'center', style: 'width: 40px' },
  { name: 'job_code', label: t('jobs.jobCode'), field: 'job_code', align: 'left' },
  { name: 'customer', label: t('customers.title'), field: 'customer_name', align: 'left' },
  { name: 'venue', label: t('venues.title'), field: 'venue_name', align: 'left' },
  { name: 'status', label: t('common.status'), field: 'status', align: 'left' },
  { name: 'start_date', label: t('jobs.startDate'), field: 'start_date', align: 'left' },
]

const filteredJobs = computed(() => {
  const q = (search.value || '').toLowerCase()
  return jobs.value.filter(j => {
    if (props.existingJobIds.includes(j.id)) return false
    if (!q) return true
    return (
      (j.job_code || '').toLowerCase().includes(q) ||
      (j.customer_name || '').toLowerCase().includes(q) ||
      (j.venue_name || '').toLowerCase().includes(q)
    )
  })
})

function toggleSelect(id) {
  const s = new Set(selectedIds.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  selectedIds.value = s
}

watch(
  () => props.modelValue,
  async (val) => {
    if (val) {
      selectedIds.value = new Set()
      search.value = ''
      loading.value = true
      try {
        const { data } = await api.get('/api/v1/jobs', { params: { skip: 0, limit: 500 } })
        jobs.value = Array.isArray(data) ? data : (data.items || [])
      } catch {
        jobs.value = []
      } finally {
        loading.value = false
      }
    }
  },
)

async function onAdd() {
  adding.value = true
  try {
    emit('added', Array.from(selectedIds.value))
    emit('update:modelValue', false)
  } finally {
    adding.value = false
  }
}
</script>
