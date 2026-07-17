<template>
  <q-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)">
    <q-card style="min-width: 700px; max-height: 80vh">
      <q-card-section class="row items-center q-pb-sm">
        <q-icon name="inventory_2" size="sm" class="q-mr-sm" />
        <div class="text-h6">{{ t('routePlanner.packingList') }}</div>
        <q-space />
        <q-btn icon="close" flat round dense @click="$emit('update:modelValue', false)" />
      </q-card-section>

      <q-card-section v-if="packingList" class="scroll" style="max-height: 65vh">
        <div class="q-mb-sm text-body2 text-grey">
          {{ t('routePlanner.reverseOrder') }}
        </div>
        <div v-if="packingList.vehicles?.length > 0" class="row q-gutter-sm q-mb-md">
          <q-chip v-for="v in packingList.vehicles" :key="v.id" :color="vehicleChipColor(v.vehicle_type)" text-color="white" icon="local_shipping" size="sm">
            {{ v.name }}
          </q-chip>
        </div>

        <div class="row q-gutter-md q-mb-md">
          <q-chip icon="scale" color="blue-1" size="sm">
            {{ packingList.total_weight_kg }} kg
          </q-chip>
          <q-chip icon="straighten" color="green-1" size="sm">
            {{ packingList.total_volume_m3 }} m³
          </q-chip>
        </div>

        <!-- Group stops by vehicle -->
        <div v-for="(group, vehicleName) in groupedStops" :key="vehicleName" class="q-mb-md">
          <div class="text-subtitle2 text-weight-medium q-mb-sm">
            <q-icon name="local_shipping" size="xs" class="q-mr-xs" />
            {{ vehicleName }}
          </div>
          <q-list bordered separator class="rounded-borders">
            <q-item v-for="stop in group" :key="stop.stop_order">
              <q-item-section avatar>
                <q-avatar size="28px" color="primary" text-color="white" class="text-caption">
                  {{ stop.stop_order }}
                </q-avatar>
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-caption">
                  <span class="text-weight-medium">{{ stop.job_code }}</span> — {{ stop.customer_name || '—' }}
                </q-item-label>
                <q-item-label v-if="stop.venue_address" caption class="text-caption">{{ stop.venue_address }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <div class="row q-gutter-xs">
                  <q-badge v-if="Number(stop.stop_weight_kg) > 0" color="grey-7" class="text-caption">{{ stop.stop_weight_kg }} kg</q-badge>
                  <q-badge v-if="Number(stop.stop_volume_m3) > 0" color="grey-6" class="text-caption">{{ stop.stop_volume_m3 }} m³</q-badge>
                </div>
              </q-item-section>
              <q-item-section side style="min-width: 120px">
                <div v-for="p in stop.products" :key="p.product_id" class="text-caption text-grey">
                  {{ p.product_name }} ×{{ p.quantity }}
                </div>
              </q-item-section>
              <q-item-section side>
                <q-btn flat dense round icon="qr_code_scanner" size="sm" color="positive" @click="scanJob(stop.job_id)" :title="t('routePlanner.scanThisJob')" />
              </q-item-section>
            </q-item>
          </q-list>
        </div>
      </q-card-section>

      <q-card-section v-else-if="loading" class="text-center q-pa-lg">
        <q-spinner /> {{ t('common.loading') }}
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useRoutePlannerStore } from '../stores/routePlanner'

const { t } = useI18n()
const router = useRouter()
const store = useRoutePlannerStore()

const props = defineProps({
  modelValue: Boolean,
  routeId: { type: Number, default: null },
})

defineEmits(['update:modelValue'])

const loading = ref(false)
const packingList = ref(null)

const groupedStops = computed(() => {
  if (!packingList.value?.stops) return {}
  const groups = {}
  for (const stop of packingList.value.stops) {
    // Find vehicle for this stop from the original route data
    const vehicleName = stop.vehicle_name || t('routePlanner.noVehicleForJob')
    if (!groups[vehicleName]) groups[vehicleName] = []
    groups[vehicleName].push(stop)
  }
  return groups
})

function vehicleChipColor(type) {
  const map = { truck: 'blue', van: 'teal', trailer: 'orange', car: 'purple' }
  return map[type] || 'grey'
}

function scanJob(jobId) {
  if (!jobId) return
  router.push({ path: '/scan', query: { action: 'job_out', jobId } })
}

watch(
  () => props.modelValue,
  async (val) => {
    if (val && props.routeId) {
      loading.value = true
      packingList.value = null
      try {
        packingList.value = await store.getPackingList(props.routeId)
      } catch (err) {
        console.error(err)
      } finally {
        loading.value = false
      }
    }
  },
)
</script>
