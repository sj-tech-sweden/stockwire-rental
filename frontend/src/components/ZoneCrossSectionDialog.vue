<template>
  <q-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)" maximized>
    <q-card class="ec-card zone-cross-section-card">
      <q-card-section class="row items-center q-pb-none">
        <div class="text-h6">
          {{ zone?.name || t('inventory.zone') }}
          <span v-if="zone?.code" class="text-caption text-grey-7 q-ml-sm">({{ zone.code }})</span>
        </div>
        <q-space />
        <q-btn flat dense round icon="close" @click="$emit('update:modelValue', false)" />
      </q-card-section>

      <q-card-section>
        <div v-if="!zone" class="text-grey text-center q-py-lg">
          {{ t('inventory.noZoneSelected') }}
        </div>
        <div v-else>
          <div class="row items-center q-mb-md">
            <q-badge :label="zone.zone_type" color="primary" class="q-mr-sm" />
            <span class="text-caption text-grey-7">
              {{ zoneChildren.length }} sub-zone{{ zoneChildren.length !== 1 ? 's' : '' }}
              · {{ totalDeviceCount }} device{{ totalDeviceCount !== 1 ? 's' : '' }}
            </span>
          </div>

          <div v-if="zoneChildren.length === 0" class="text-grey text-center q-py-lg">
            {{ t('inventory.noSubZones') }}
            <div class="q-mt-sm">
              <q-btn color="primary" unelevated icon="add" :label="t('inventory.addSubZones')" @click="$emit('add-subzones', zone)" />
            </div>
          </div>

          <div v-else class="cross-section-grid">
            <div
              v-for="child in zoneChildren"
              :key="child.id"
              class="cross-section-cell"
              :class="{ 'highlighted': highlightIds.includes(child.id) }"
              @click="$emit('zone-click', child)"
            >
              <div class="cross-section-cell-header">
                <div class="text-subtitle2 ellipsis">{{ child.name }}</div>
                <q-badge :label="child.zone_type" color="secondary" size="sm" />
              </div>
              <div class="cross-section-cell-body">
                <div class="text-caption text-grey-7">
                  {{ getDeviceCount(child.id) }} device{{ getDeviceCount(child.id) !== 1 ? 's' : '' }}
                </div>
                <div v-if="getDeviceCount(child.id) > 0" class="cross-section-device-dots">
                  <span
                    v-for="i in Math.min(getDeviceCount(child.id), 12)"
                    :key="i"
                    class="device-dot"
                    :class="getDeviceStatusClass(child.id, i)"
                  />
                  <span v-if="getDeviceCount(child.id) > 12" class="text-caption text-grey-6">+{{ getDeviceCount(child.id) - 12 }}</span>
                </div>
                <div v-if="childGrandChildren(child).length > 0" class="text-caption text-grey-5 q-mt-xs">
                  {{ childGrandChildren(child).length }} sub-zone{{ childGrandChildren(child).length !== 1 ? 's' : '' }}
                </div>
              </div>
              <div class="cross-section-cell-actions">
                <q-btn flat dense round icon="visibility" size="sm" color="primary" @click.stop="$emit('zone-click', child)">
                  <q-tooltip>{{ t('inventory.viewZone') }}</q-tooltip>
                </q-btn>
                <q-btn flat dense round icon="edit" size="sm" color="secondary" @click.stop="$emit('edit-zone', child)">
                  <q-tooltip>{{ t('inventory.editZone') }}</q-tooltip>
                </q-btn>
              </div>
            </div>
          </div>
        </div>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  zone: { type: Object, default: null },
  zones: { type: Array, default: () => [] },
  devices: { type: Array, default: () => [] },
  highlightIds: { type: Array, default: () => [] },
})

defineEmits(['update:modelValue', 'zone-click', 'edit-zone', 'add-subzones'])

const { t } = useI18n()

const zoneChildren = computed(() => {
  if (!props.zone) return []
  return props.zones
    .filter(z => z.parent_id === props.zone.id)
    .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0) || a.name.localeCompare(b.name))
})

const totalDeviceCount = computed(() => {
  if (!props.zone) return 0
  let count = 0
  function countDevices(zoneId) {
    for (const device of props.devices) {
      if (device.location_zone_id === zoneId) count++
    }
    for (const child of props.zones) {
      if (child.parent_id === zoneId) countDevices(child.id)
    }
  }
  countDevices(props.zone.id)
  return count
})

function getDeviceCount(zoneId) {
  return props.devices.filter(d => d.location_zone_id === zoneId).length
}

function getDeviceStatusClass(zoneId, index) {
  const devices = props.devices.filter(d => d.location_zone_id === zoneId)
  const device = devices[index - 1]
  if (!device) return 'dot-available'
  const statusClasses = {
    available: 'dot-available',
    reserved: 'dot-reserved',
    in_use: 'dot-in-use',
    maintenance: 'dot-maintenance',
  }
  return statusClasses[device.status] || 'dot-available'
}

function childGrandChildren(child) {
  return props.zones.filter(z => z.parent_id === child.id)
}
</script>

<style scoped>
.zone-cross-section-card {
  max-width: 95vw;
  max-height: 95vh;
}

.cross-section-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.cross-section-cell {
  border: 1px solid var(--q-separator-color, #ddd);
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
  background: var(--q-card-background, #fff);
}

.cross-section-cell:hover {
  border-color: var(--q-primary, #3F873F);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.cross-section-cell.highlighted {
  border-color: #FFD700;
  box-shadow: 0 0 0 2px rgba(255, 215, 0, 0.3);
}

.cross-section-cell-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.cross-section-cell-body {
  min-height: 40px;
}

.cross-section-device-dots {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
  margin-top: 4px;
}

.device-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
}

.dot-available {
  background-color: #4caf50;
}

.dot-reserved {
  background-color: #ff9800;
}

.dot-in-use {
  background-color: #2196f3;
}

.dot-maintenance {
  background-color: #f44336;
}

.cross-section-cell-actions {
  display: flex;
  justify-content: flex-end;
  gap: 4px;
  margin-top: 8px;
  border-top: 1px solid var(--q-separator-color, #eee);
  padding-top: 8px;
}
</style>
