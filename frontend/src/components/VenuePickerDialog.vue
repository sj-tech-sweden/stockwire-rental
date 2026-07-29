<template>
  <q-dialog :model-value="modelValue" :maximized="isPhone" @update:model-value="emit('update:modelValue', $event)">
    <q-card :style="isPhone ? '' : 'min-width: 400px; max-width: 95vw'" class="ec-card">
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6">{{ t('jobs.selectVenue') }}</div>
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
            v-for="venue in filteredVenues"
            :key="venue.id"
            clickable
            :active="venue.id === selectedId"
            active-class="bg-primary text-white"
            @click="selectVenue(venue)"
          >
            <q-item-section>
              <q-item-label>{{ venue.name }}</q-item-label>
              <q-item-label v-if="venue.city" caption>{{ venue.city }}</q-item-label>
            </q-item-section>
          </q-item>
          <q-item v-if="!filteredVenues.length">
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
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  modelValue: Boolean,
  venues: { type: Array, default: () => [] },
  selectedId: { type: Number, default: null },
})

const emit = defineEmits(['update:modelValue', 'select'])

const $q = useQuasar()
const { t } = useI18n()
const search = ref('')
const isPhone = computed(() => $q.screen.lt.md)

const filteredVenues = computed(() => {
  const term = search.value.trim().toLowerCase()
  if (!term) return props.venues
  return props.venues.filter(v =>
    String(v.name || '').toLowerCase().includes(term) ||
    String(v.city || '').toLowerCase().includes(term)
  )
})

function selectVenue(venue) {
  emit('select', venue)
  emit('update:modelValue', false)
}
</script>
