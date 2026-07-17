<template>
  <q-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)">
    <q-card style="min-width: 650px; max-height: 80vh">
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6">{{ t('routePlanner.suggestVehicle') }}</div>
        <q-space />
        <q-btn icon="close" flat round dense @click="$emit('update:modelValue', false)" />
      </q-card-section>

      <q-card-section class="scroll" style="max-height: 65vh">
        <div class="q-mb-md text-body2">
          {{ t('routePlanner.totalWeight') }}: {{ totalWeight }} kg ·
          {{ t('routePlanner.totalVolume') }}: {{ totalVolume }} m³
        </div>

        <q-list bordered separator class="rounded-borders">
          <q-item v-for="s in suggestions" :key="s.suggestion_id">
            <q-item-section avatar>
              <q-avatar :color="s.fits ? 'positive' : 'grey-5'" text-color="white" size="36px">
                <q-icon :name="s.is_combo ? 'link' : 'local_shipping'" />
              </q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label class="text-weight-medium">{{ s.label }}</q-item-label>
              <q-item-label v-if="s.is_combo && s.combo_description" caption>
                {{ s.combo_description }}
              </q-item-label>
              <q-item-label caption>
                {{ t('routePlanner.weight') }}: {{ s.total_weight_kg }} / {{ s.total_max_weight_kg }} kg
                <template v-if="s.total_max_volume_m3"> · {{ t('routePlanner.volume') }}: {{ s.total_volume_m3 }} / {{ s.total_max_volume_m3 }} m³</template>
              </q-item-label>
              <!-- Individual vehicle details for combos -->
              <div v-if="s.is_combo && s.vehicles?.length > 1" class="q-mt-xs">
                <div v-for="v in s.vehicles" :key="v.id" class="text-caption text-grey">
                  <q-icon :name="vehicleIcon(v.vehicle_type)" size="xs" />
                  {{ v.name }}:
                  <template v-if="v.vehicle_type === 'trailer' && v.max_payload_kg">{{ t('routePlanner.payload') }} {{ v.max_payload_kg }}kg</template>
                  <template v-else-if="v.max_weight_kg">{{ v.max_weight_kg }}kg</template>
                  <template v-if="v.vehicle_type === 'trailer' && v.curb_weight_kg"> ({{ t('routePlanner.curbWeight') }}: {{ v.curb_weight_kg }}kg)</template>
                  <template v-if="v.max_tow_weight_kg"> · {{ t('routePlanner.maxTowWeight') }}: {{ v.max_tow_weight_kg }}kg</template>
                </div>
              </div>
              <!-- Utilization bars -->
              <div class="row q-gutter-sm q-mt-xs" style="max-width: 300px">
                <div class="col" v-if="s.weight_utilization_pct != null">
                  <q-linear-progress
                    :value="Math.min(s.weight_utilization_pct / 100, 1)"
                    :color="s.weight_utilization_pct > 100 ? 'negative' : 'primary'"
                    size="xs"
                  />
                  <div class="text-caption text-grey">{{ Math.round(s.weight_utilization_pct) }}% {{ t('routePlanner.weight') }}</div>
                </div>
                <div class="col" v-if="s.volume_utilization_pct != null">
                  <q-linear-progress
                    :value="Math.min(s.volume_utilization_pct / 100, 1)"
                    :color="s.volume_utilization_pct > 100 ? 'negative' : 'primary'"
                    size="xs"
                  />
                  <div class="text-caption text-grey">{{ Math.round(s.volume_utilization_pct) }}% {{ t('routePlanner.volume') }}</div>
                </div>
              </div>
            </q-item-section>
            <q-item-section side>
              <q-btn
                v-if="s.fits"
                unelevated
                size="sm"
                color="primary"
                :label="t('common.select')"
                @click="onSelect(s)"
              />
              <span v-else class="text-negative text-caption">{{ t('routePlanner.exceedsCapacity') }}</span>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoutePlannerStore } from '../stores/routePlanner'

const { t } = useI18n()
const store = useRoutePlannerStore()

const props = defineProps({
  modelValue: Boolean,
  jobIds: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue', 'selected'])

const suggestions = ref([])

const totalWeight = computed(() => suggestions.value[0]?.total_weight_kg || '0')
const totalVolume = computed(() => suggestions.value[0]?.total_volume_m3 || '0')

watch(
  () => props.modelValue,
  async (val) => {
    if (val && props.jobIds.length > 0) {
      try {
        suggestions.value = await store.suggestVehicles(props.jobIds)
      } catch (err) {
        console.error(err)
      }
    }
  },
)

function onSelect(suggestion) {
  emit('selected', suggestion)
  emit('update:modelValue', false)
}

function vehicleIcon(type) {
  const map = { truck: 'local_shipping', van: 'airport_shuttle', trailer: 'inventory_2', car: 'directions_car' }
  return map[type] || 'local_shipping'
}
</script>
