<template>
  <div class="warehouse-map-container">
    <div class="row items-center q-mb-sm q-gutter-sm" style="flex-shrink: 0">
      <div class="text-subtitle2 col">{{ t('inventory.warehouseMap') }}</div>
      <q-btn-toggle
        v-model="viewMode"
        :options="viewOptions"
        toggle-color="primary"
        dense
        no-caps
        size="sm"
        class="view-mode-toggle"
      />
      <q-toggle
        v-model="editMode"
        :label="t('inventory.editMode')"
        color="warning"
        dense
        class="q-ml-sm"
      />
      <template v-if="editMode">
        <q-separator vertical class="q-mx-xs" />
        <q-btn flat dense icon="straighten" :color="measureMode ? 'positive' : undefined" @click="toggleMeasureMode" size="sm">
          <q-tooltip>Measure distance</q-tooltip>
        </q-btn>
        <q-separator vertical class="q-mx-xs" />
        <q-btn flat dense :icon="snapToGrid ? 'grid_on' : 'grid_off'" :color="snapToGrid ? 'warning' : undefined" @click="snapToGrid = !snapToGrid" size="sm">
          <q-tooltip>{{ snapToGrid ? 'Snap to grid' : 'Grid snapping off' }}</q-tooltip>
        </q-btn>
        <q-input v-if="snapToGrid" v-model.number="gridSizeCm" type="number" min="1" max="100" dense outlined
          :style="{ width: '70px' }" input-class="text-center text-caption" @update:model-value="v => gridSizeCm = Math.max(1, Number(v) || 10)">
          <template #append><span class="text-caption text-grey-6">cm</span></template>
        </q-input>
        <q-btn-dropdown flat dense icon="format_align_left" size="sm" label="Align" no-caps>
          <q-list dense>
            <q-item clickable v-ripple @click="$emit('align-zones', 'left')">
              <q-item-section avatar><q-icon name="format_align_left" /></q-item-section>
              <q-item-section>Align left</q-item-section>
            </q-item>
            <q-item clickable v-ripple @click="$emit('align-zones', 'center-h')">
              <q-item-section avatar><q-icon name="format_align_center" /></q-item-section>
              <q-item-section>Align center</q-item-section>
            </q-item>
            <q-item clickable v-ripple @click="$emit('align-zones', 'right')">
              <q-item-section avatar><q-icon name="format_align_right" /></q-item-section>
              <q-item-section>Align right</q-item-section>
            </q-item>
            <q-separator />
            <q-item clickable v-ripple @click="$emit('align-zones', 'top')">
              <q-item-section avatar><q-icon name="align_vertical_top" /></q-item-section>
              <q-item-section>Align top</q-item-section>
            </q-item>
            <q-item clickable v-ripple @click="$emit('align-zones', 'center-v')">
              <q-item-section avatar><q-icon name="align_vertical_center" /></q-item-section>
              <q-item-section>Align middle</q-item-section>
            </q-item>
            <q-item clickable v-ripple @click="$emit('align-zones', 'bottom')">
              <q-item-section avatar><q-icon name="align_vertical_bottom" /></q-item-section>
              <q-item-section>Align bottom</q-item-section>
            </q-item>
          </q-list>
        </q-btn-dropdown>
        <q-btn-dropdown flat dense icon="grid_view" size="sm" label="Distribute" no-caps>
          <q-list dense>
            <q-item clickable v-ripple @click="$emit('distribute-zones', 'horizontal')">
              <q-item-section avatar><q-icon name="swap_horiz" /></q-item-section>
              <q-item-section>Distribute horizontally</q-item-section>
            </q-item>
            <q-item clickable v-ripple @click="$emit('distribute-zones', 'vertical')">
              <q-item-section avatar><q-icon name="swap_vert" /></q-item-section>
              <q-item-section>Distribute vertically</q-item-section>
            </q-item>
          </q-list>
        </q-btn-dropdown>
      </template>
      <q-btn flat dense icon="zoom_in" @click="zoomIn" :disable="scale >= 3"><q-tooltip>{{ t('inventory.zoomIn') }}</q-tooltip></q-btn>
      <q-btn flat dense icon="zoom_out" @click="zoomOut" :disable="scale <= 0.3"><q-tooltip>{{ t('inventory.zoomOut') }}</q-tooltip></q-btn>
      <q-btn flat dense icon="restart_alt" @click="resetView"><q-tooltip>{{ t('inventory.resetView') }}</q-tooltip></q-btn>
    </div>
    <div v-if="breadcrumb.length > 0" class="breadcrumb-bar row items-center q-mb-xs q-gutter-xs" style="flex-shrink: 0">
      <q-btn flat dense no-caps icon="home" size="sm" color="primary" @click="$emit('drill-up', null)" />
      <template v-for="(crumb, idx) in breadcrumb" :key="crumb.id">
        <q-icon name="chevron_right" size="xs" class="text-grey-5" />
        <q-btn
          flat dense no-caps size="sm"
          :color="idx === breadcrumb.length - 1 ? 'white' : 'primary'"
          :label="crumb.name"
          @click="$emit('drill-up', crumb.id)"
        />
      </template>
    </div>
    <div
      class="warehouse-map-viewport"
      :class="{ 'edit-mode': editMode }"
      ref="viewportRef"
      @mousedown="onViewportMouseDown"
      @touchstart.passive="onTouchStart"
    >
      <svg
        ref="svgRef"
        :width="viewportWidth"
        :height="viewportHeight"
        :viewBox="viewBox"
        class="warehouse-map-svg"
        :class="{ 'measure-mode': measureMode }"
        @click="onMeasureClick"
      >
        <defs>
          <pattern :id="`${mapId}-grid`" :width="snapToGrid ? gridSizeCm / CM_PER_PX : 20" :height="snapToGrid ? gridSizeCm / CM_PER_PX : 20" patternUnits="userSpaceOnUse">
            <path :d="`M ${snapToGrid ? gridSizeCm / CM_PER_PX : 20} 0 L 0 0 0 ${snapToGrid ? gridSizeCm / CM_PER_PX : 20}`" fill="none" :stroke="snapToGrid ? 'rgba(255,200,0,0.08)' : 'rgba(255,255,255,0.04)'" stroke-width="0.5"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" :fill="`url(#${mapId}-grid)`" v-if="editMode" />
        <g :transform="`translate(${panX}, ${panY}) scale(${scale})`">
          <g v-if="parentOutline" :transform="parentOutline.rotation && viewMode === 'top' ? `rotate(${parentOutline.rotation}, ${parentOutline.x + parentOutline.w / 2}, ${parentOutline.y + parentOutline.h / 2})` : undefined">
            <rect
              :x="parentOutline.x"
              :y="parentOutline.y"
              :width="parentOutline.w"
              :height="parentOutline.h"
              fill="none"
              stroke="rgba(255,165,0,0.5)"
              stroke-width="2"
              stroke-dasharray="8,4"
              style="pointer-events:none"
            />
            <text
              :x="parentOutline.x + parentOutline.w / 2"
              :y="parentOutline.y + 14"
              text-anchor="middle"
              class="warehouse-parent-outline-label"
              style="pointer-events:none"
            >{{ parentOutline.name }}</text>
          </g>
          <g v-for="zone in renderMappedZones" :key="'m-' + zone.id">
            <g :transform="zone.rotation && viewMode === 'top' ? `rotate(${zone.rotation}, ${zone.x + zone.w / 2}, ${zone.y + zone.h / 2})` : undefined">
              <rect
                :x="zone.x"
                :y="zone.y"
                :width="zone.w"
                :height="zone.h"
                :fill="zone.fill"
                :stroke="zone.stroke"
                :stroke-width="zone.depth > 0 ? 1 : 1.5"
                :stroke-dasharray="zone.strokeDasharray"
                :style="{ pointerEvents: zone.depth === 0 ? 'auto' : 'none' }"
                :class="[
                  'warehouse-zone-rect',
                  { 'highlighted': isHighlighted(zone.id) },
                  { 'selected': selectedZoneIds.includes(zone.id) },
                  { 'draggable': editMode },
                ]"
                @mousedown.stop="editMode && zone.depth === 0 ? onZoneDragStart($event, zone) : (zone.depth === 0 ? onZoneViewClick($event, zone) : null)"
                @click.stop="!editMode && zone.depth === 0 && onZoneViewClick($event, zone)"
                @dblclick.stop="zone.depth === 0 && onZoneDblClick(zone)"
                @contextmenu.prevent.stop="onZoneContextMenu($event, zone)"
              />
              <text
                v-if="zone.depth > 0 && zone.depth < 2"
                :x="zone.x + zone.w / 2"
                :y="zone.y + 10"
                text-anchor="middle"
                dominant-baseline="middle"
                class="warehouse-zone-label-sm"
                style="pointer-events:none"
              >{{ zone.name }}</text>
              <text
                v-if="zone.depth === 0"
                :x="zone.x + zone.w / 2"
                :y="zone.y + zone.h / 2 + (zone.childCount > 0 ? 8 : 10)"
                text-anchor="middle"
                dominant-baseline="middle"
                class="warehouse-zone-count"
                style="pointer-events:none"
              >{{ zone.deviceCount }} device{{ zone.deviceCount !== 1 ? 's' : '' }}</text>
              <text
                v-if="zone.depth === 0 && zone.childCount > 0"
                :x="zone.x + zone.w / 2"
                :y="zone.y + zone.h / 2 + 22"
                text-anchor="middle"
                dominant-baseline="middle"
                class="warehouse-zone-subcount"
                style="pointer-events:none"
              >{{ zone.childCount }} sub-zone{{ zone.childCount !== 1 ? 's' : '' }}</text>
              <text
                v-if="showDimensions"
                :x="zone.x + zone.w / 2"
                :y="zone.y + zone.h - 4"
                text-anchor="middle"
                dominant-baseline="middle"
                class="warehouse-zone-dim"
                style="pointer-events:none"
              >{{ formatDim(zone.dimW) }}×{{ formatDim(zone.dimH) }}</text>
              <template v-if="editMode && selectedZoneIds.includes(zone.id)">
                <rect v-for="rh in resizeHandles(zone)" :key="rh.key"
                  :x="rh.x" :y="rh.y" :width="rh.size" :height="rh.size"
                  fill="#FFD700" stroke="#333" stroke-width="0.5"
                  class="resize-handle"
                  :style="{ cursor: rh.cursor }"
                  @mousedown.stop="onZoneResizeStart($event, zone, rh.handle)"
                />
              </template>
            </g>
          </g>
          <g v-for="zone in renderMappedZones.filter(z => z.depth === 0)" :key="'lbl-' + zone.id">
            <text
              :x="zone.x + zone.w / 2"
              :y="zone.y + zone.h / 2 - (zone.childCount > 0 ? 8 : 4)"
              text-anchor="middle"
              dominant-baseline="middle"
              class="warehouse-zone-label"
              style="pointer-events:none"
            >{{ zone.name }}</text>
          </g>
          <g v-if="renderUnmappedZones.length > 0">
            <text
              :x="unmappedAreaX"
              :y="unmappedAreaY - 12"
              class="warehouse-unmapped-title"
              style="pointer-events:none"
            >{{ t('inventory.unmappedZones') }}</text>
            <g v-for="zone in renderUnmappedZones" :key="'u-' + zone.id">
              <rect
                :x="zone.x"
                :y="zone.y"
                :width="zone.w"
                :height="zone.h"
                :fill="zone.fill"
                :stroke="isHighlighted(zone.id) ? '#FFD700' : '#555'"
                stroke-width="1"
                :class="[
                  'warehouse-zone-rect',
                  'unmapped',
                  { 'highlighted': isHighlighted(zone.id) },
                { 'selected': selectedZoneIds.includes(zone.id) },
                  { 'draggable': editMode },
                ]"
                @mousedown.stop="editMode ? onUnmappedDragStart($event, zone) : onZoneViewClick($event, zone)"
                @click.stop="!editMode && onZoneViewClick($event, zone)"
                @dblclick.stop="onZoneDblClick(zone)"
              />
              <text
                :x="zone.x + zone.w / 2"
                :y="zone.y + zone.h / 2 - 4"
                text-anchor="middle"
                dominant-baseline="middle"
                class="warehouse-zone-label unmapped-label"
                style="pointer-events:none"
              >{{ zone.name }}</text>
              <text
                :x="zone.x + zone.w / 2"
                :y="zone.y + zone.h / 2 + 10"
                text-anchor="middle"
                dominant-baseline="middle"
                class="warehouse-zone-count"
                style="pointer-events:none"
              >{{ zone.deviceCount }}</text>
            </g>
          </g>
          <g v-if="measureStart && measureMode">
            <line
              :x1="measureStart.x" :y1="measureStart.y"
              :x2="measureEnd?.x ?? measureStart.x" :y2="measureEnd?.y ?? measureStart.y"
              stroke="#FFD700" stroke-width="2" stroke-dasharray="6,3"
            />
            <circle :cx="measureStart.x" :cy="measureStart.y" r="4" fill="#FFD700" />
            <circle v-if="measureEnd" :cx="measureEnd.x" :cy="measureEnd.y" r="4" fill="#FFD700" />
            <text
              v-if="measureDistance"
              :x="(measureStart.x + (measureEnd?.x ?? measureStart.x)) / 2"
              :y="(measureStart.y + (measureEnd?.y ?? measureStart.y)) / 2 - 8"
              text-anchor="middle" dominant-baseline="middle"
              fill="#FFD700" font-size="12" font-weight="bold" font-family="inherit"
              style="pointer-events:none"
            >{{ measureDistance }}</text>
          </g>
        </g>
      </svg>
    </div>
    <div
      v-if="contextMenu.show"
      class="zone-context-menu"
      :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
      @click.stop
    >
      <div class="zone-context-menu-item" @click="onContextMenuSearchDevices">
        <q-icon name="search" size="16px" class="q-mr-sm" />{{ t('inventory.searchDevicesInZone') }}
      </div>
      <div class="zone-context-menu-item" @click="onContextMenuEditProperties">
        <q-icon name="edit" size="16px" class="q-mr-sm" />{{ t('inventory.editZone') }}
      </div>
      <div v-if="getChildren(contextMenu.zone?.id).length" class="zone-context-menu-item" @click="onContextMenuDrillDown">
        <q-icon name="open_in_new" size="16px" class="q-mr-sm" />{{ t('inventory.openZone') }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  zones: { type: Array, default: () => [] },
  zoneTree: { type: Array, default: () => [] },
  devices: { type: Array, default: () => [] },
  highlightZoneIds: { type: Array, default: () => [] },
  selectedZoneIds: { type: Array, default: () => [] },
  focusZoneId: { type: Number, default: null },
  breadcrumb: { type: Array, default: () => [] },
})

const emit = defineEmits(['zone-click', 'zone-dblclick', 'zone-move', 'zone-resize', 'drill-down', 'drill-up', 'align-zones', 'distribute-zones', 'zone-properties', 'selection-change', 'search-devices-in-zone'])

const { t } = useI18n()

const viewportRef = ref(null)
const mapId = `whmap-${Math.random().toString(36).slice(2, 8)}`
const svgRef = ref(null)
const viewportWidth = ref(900)
const viewportHeight = ref(500)
const scale = ref(1)
const panX = ref(0)
const panY = ref(0)
const editMode = ref(false)
const measureMode = ref(false)
const snapToGrid = ref(false)
const gridSizeCm = ref(10)
const measureStart = ref(null)
const measureEnd = ref(null)
const viewMode = ref(localStorage.getItem('warehouseMapViewMode') || 'top')

const viewOptions = [
  { label: 'Top', value: 'top' },
  { label: 'Front', value: 'front' },
  { label: 'Side', value: 'side' },
]

const showDimensions = computed(() => editMode.value || scale.value > 0.8)

const CM_PER_PX = 2
const DEFAULT_W_CM = 200
const DEFAULT_H_CM = 150
const DEFAULT_DEPTH_CM = 100
const CHILD_PADDING_CM = 6
const CHILD_HEADER_CM = 18
const UNMAPPED_GAP = 8
const UNMAPPED_CELL_W = 100
const UNMAPPED_CELL_H = 50
const MIN_SIZE = 30

function snap(v) {
  if (!snapToGrid.value || !gridSizeCm.value) return v
  return Math.round(v / gridSizeCm.value) * gridSizeCm.value
}

const overrides = reactive({})
const contextMenu = reactive({ show: false, x: 0, y: 0, zone: null })
const viewBox = computed(() => `0 0 ${viewportWidth.value} ${viewportHeight.value}`)

const maxZExtent = computed(() => {
  if (viewMode.value === 'top') return 0
  let max = 0
  for (const z of props.zones) {
    const end = (z.pos_z || 0) + (z.map_height || 0)
    if (end > max) max = end
  }
  return max
})

function flipY(pb, h) {
  if (viewMode.value === 'top') return cmToPx(pb) || 0
  return (cmToPx(maxZExtent.value) || 0) - (cmToPx(pb) || 0) - h
}

watch(viewMode, (v) => {
  localStorage.setItem('warehouseMapViewMode', v)
  nextTick(() => fitToView())
})

watch(() => props.focusZoneId, () => {
  nextTick(() => fitToView())
})

watch(() => props.zones, () => {
  for (const key of Object.keys(overrides)) {
    delete overrides[key]
  }
}, { deep: true })

const deviceCounts = computed(() => {
  const c = {}
  for (const d of props.devices || []) {
    if (d.location_zone_id) c[d.location_zone_id] = (c[d.location_zone_id] || 0) + 1
  }
  return c
})

const isHighlighted = (id) => props.highlightZoneIds.includes(id)

const TYPE_COLORS = {
  warehouse: '#2d4a3e', rack: '#3a5a4a', shelf: '#4a6a5a', bin: '#5a7a6a',
  pallet: '#4a5a6a', stage: '#5a4a6a', truck: '#6a5a4a', workshop: '#6a4a5a',
}
function zoneColor(z) {
  if (overrides[z.id]?.color) return overrides[z.id].color
  if (z.color) return z.color
  return TYPE_COLORS[z.zone_type] || '#3a5a4a'
}

function getChildren(zoneId) {
  return props.zones.filter(z => z.parent_id === zoneId)
}

function cmToPx(cm) {
  return Math.round(Number(cm || 0) / CM_PER_PX)
}

function formatDim(cm) {
  if (!cm) return '?'
  return cm >= 100 ? `${(cm / 100).toFixed(1)}m` : `${cm}cm`
}

function getViewAxes() {
  switch (viewMode.value) {
    case 'front': return { posA: 'pos_x', posB: 'pos_z', sizeA: 'map_width', sizeB: 'map_height', labelA: 'Width', labelB: 'Height' }
    case 'side':  return { posA: 'pos_y', posB: 'pos_z', sizeA: 'map_depth', sizeB: 'map_height', labelA: 'Depth', labelB: 'Height' }
    default:      return { posA: 'pos_x', posB: 'pos_y', sizeA: 'map_width', sizeB: 'map_depth', labelA: 'Width', labelB: 'Depth' }
  }
}

function getZonePosA(z) {
  const ov = overrides[z.id] || {}
  const axes = getViewAxes()
  const val = ov[axes.posA] ?? z[axes.posA]
  if (val == null) {
    if (z.pos_x != null || z.pos_y != null || z.pos_z != null) return 0
    return null
  }
  if (viewMode.value === 'top') return val
  const rot = z.rotation || 0
  if (rot === 90 || rot === 270) {
    if (axes.sizeA === 'map_width') {
      return val + ((z.map_width || 0) - (z.map_depth || 0)) / 2
    }
    if (axes.sizeA === 'map_depth') {
      return val + ((z.map_depth || 0) - (z.map_width || 0)) / 2
    }
  }
  return val
}
function getZonePosB(z) {
  const ov = overrides[z.id] || {}
  const axes = getViewAxes()
  const val = ov[axes.posB] ?? z[axes.posB]
  if (val != null) return val
  if (z.pos_x != null || z.pos_y != null || z.pos_z != null) return 0
  return null
}
function getZoneSizeA(z) {
  const ov = overrides[z.id] || {}
  const axes = getViewAxes()
  const raw = ov[axes.sizeA] ?? z[axes.sizeA]
  if (viewMode.value === 'top') return raw
  const rot = z.rotation || 0
  const swapped = rot === 90 || rot === 270
  if (!swapped) return raw
  if (axes.sizeA === 'map_width') return ov.map_depth ?? z.map_depth
  if (axes.sizeA === 'map_depth') return ov.map_width ?? z.map_width
  return raw
}
function getZoneSizeB(z) { const ov = overrides[z.id] || {}; return ov[getViewAxes().sizeB] ?? z[getViewAxes().sizeB] }

function autoLayoutChildren(parent, children, parentXA, parentXB, parentWA, parentHB) {
  const positioned = []
  const unpadded = []
  const axes = getViewAxes()
  for (const ch of children) {
    const cx = getZonePosA(ch)
    const cy = getZonePosB(ch)
    if (cx != null && cy != null) {
      const chH = cmToPx(getZoneSizeB(ch)) || DEFAULT_H_CM / CM_PER_PX
      const chA = cmToPx(getZoneSizeA(ch)) || DEFAULT_W_CM / CM_PER_PX
      positioned.push({ node: ch, a: cmToPx(Number(cx)), b: flipY(Number(cy), chH), w: chA, h: chH })
    } else {
      unpadded.push(ch)
    }
  }
  if (!unpadded.length) return positioned

  const padPx = cmToPx(CHILD_PADDING_CM)
  const headerPx = cmToPx(CHILD_HEADER_CM)
  const innerX = parentXA + padPx
  const innerXB = parentXB + headerPx
  const innerWA = parentWA - padPx * 2
  const innerHB = parentHB - headerPx - padPx
  if (innerWA < 20 || innerHB < 20) return positioned

  const cols = Math.max(1, Math.ceil(Math.sqrt(unpadded.length * (innerWA / innerHB))))
  const rows = Math.ceil(unpadded.length / cols)
  const cellW = Math.floor(innerWA / cols)
  const cellH = Math.floor(innerHB / rows)

  const auto = unpadded.map((ch, i) => ({
    node: ch,
    a: innerX + (i % cols) * cellW,
    b: innerXB + Math.floor(i / cols) * cellH,
    w: cellW - 2,
    h: cellH - 2,
  }))
  return [...positioned, ...auto]
}

const renderMappedZones = computed(() => {
  const result = []
  const nodes = currentLevelNodes.value
  const axes = getViewAxes()

  function collect(nodeList, depth) {
    for (const n of nodeList || []) {
      const pa = getZonePosA(n)
      const pb = getZonePosB(n)
      const sa = getZoneSizeA(n)
      const sb = getZoneSizeB(n)
      const children = getChildren(n.id)
      if (pa != null && pb != null) {
        const w = cmToPx(sa) || DEFAULT_W_CM / CM_PER_PX
        const h = cmToPx(sb) || DEFAULT_H_CM / CM_PER_PX
        result.push({
          id: n.id, name: n.name, zone_type: n.zone_type,
          x: cmToPx(pa) || 0, y: flipY(pb, h), w, h,
          dimW: sa || DEFAULT_W_CM, dimH: sb || DEFAULT_H_CM,
          fill: zoneColor(n),
          stroke: isHighlighted(n.id) ? '#FFD700' : (depth === 0 ? '#888' : 'rgba(255,255,255,0.2)'),
          strokeDasharray: depth > 0 ? '3,2' : undefined,
          deviceCount: deviceCounts.value[n.id] || 0,
          childCount: children.length,
          depth,
          rotation: n.rotation || 0,
          _tree: n,
        })
        if (children.length) {
          const laid = autoLayoutChildren(n, children, cmToPx(pa) || 0, flipY(pb, h), w, h)
          for (const item of laid) {
            const chSA = getZoneSizeA(item.node)
            const chSB = getZoneSizeB(item.node)
            const chChildren = getChildren(item.node.id)
            result.push({
              id: item.node.id, name: item.node.name, zone_type: item.node.zone_type,
              x: item.a, y: item.b, w: item.w, h: item.h,
              dimW: chSA, dimH: chSB,
              fill: zoneColor(item.node),
              stroke: isHighlighted(item.node.id) ? '#FFD700' : 'rgba(255,255,255,0.25)',
              strokeDasharray: '3,2',
              deviceCount: deviceCounts.value[item.node.id] || 0,
              childCount: chChildren.length,
              depth: depth + 1,
              rotation: item.node.rotation || 0,
              _tree: item.node,
            })
            if (chChildren.length) {
              collectInside(item.node, item.a, item.b, item.w, item.h, depth + 2)
            }
          }
        }
      } else {
        collect(children, depth)
      }
    }
  }

  function collectInside(node, pxA, pxB, pwA, phB, depth) {
    const children = getChildren(node.id)
    const laid = autoLayoutChildren(node, children, pxA, pxB, pwA, phB)
    for (const item of laid) {
      const chSA = getZoneSizeA(item.node)
      const chSB = getZoneSizeB(item.node)
      const chChildren = getChildren(item.node.id)
      result.push({
        id: item.node.id, name: item.node.name, zone_type: item.node.zone_type,
        x: item.a, y: item.b, w: item.w, h: item.h,
        dimW: chSA, dimH: chSB,
        fill: zoneColor(item.node),
        stroke: isHighlighted(item.node.id) ? '#FFD700' : 'rgba(255,255,255,0.2)',
        strokeDasharray: '3,2',
        deviceCount: deviceCounts.value[item.node.id] || 0,
        childCount: chChildren.length,
        depth,
        rotation: item.node.rotation || 0,
        _tree: item.node,
      })
      if (chChildren.length && depth < 4) {
        collectInside(item.node, item.a, item.b, item.w, item.h, depth + 1)
      }
    }
  }

  collect(nodes, 0)
  return result
})

const unmappedAreaX = 20
const unmappedAreaY = computed(() => {
  const maxY = renderMappedZones.value.reduce((m, z) => Math.max(m, z.y + z.h + 40), 0)
  return Math.max(maxY, 20)
})
const unmappedCols = computed(() => Math.max(1, Math.floor(viewportWidth.value / (UNMAPPED_CELL_W + UNMAPPED_GAP))))

const renderUnmappedZones = computed(() => {
  const mappedIds = new Set(renderMappedZones.value.map(z => z.id))
  const result = []
  let idx = 0
  const nodes = currentLevelNodes.value
  function walk(nodeList) {
    for (const n of nodeList || []) {
      if (mappedIds.has(n.id)) {
        const children = getChildren(n.id)
        if (children.length) walk(children)
        continue
      }
      const pa = getZonePosA(n)
      const pb = getZonePosB(n)
      if (pa == null || pb == null) {
        const col = idx % unmappedCols.value
        const row = Math.floor(idx / unmappedCols.value)
        result.push({
          id: n.id, name: n.name, zone_type: n.zone_type,
          x: unmappedAreaX + col * (UNMAPPED_CELL_W + UNMAPPED_GAP),
          y: unmappedAreaY.value + row * (UNMAPPED_CELL_H + UNMAPPED_GAP),
          w: UNMAPPED_CELL_W, h: UNMAPPED_CELL_H,
          fill: zoneColor(n),
          deviceCount: deviceCounts.value[n.id] || 0,
          _tree: n,
        })
        idx++
      }
      const children = getChildren(n.id)
      if (children.length) walk(children)
    }
  }
  walk(nodes)
  return result
})

const focusZoneNode = computed(() => {
  if (!props.focusZoneId) return null
  function find(nodes) {
    for (const n of nodes || []) {
      if (n.id === props.focusZoneId) return n
      if (n.children?.length) {
        const found = find(n.children)
        if (found) return found
      }
    }
    return null
  }
  return find(props.zoneTree)
})

const currentLevelNodes = computed(() => {
  if (props.focusZoneId) {
    return props.zones.filter(z => z.parent_id === props.focusZoneId)
  }
  return props.zones.filter(z => z.parent_id == null)
})

const parentOutline = computed(() => {
  if (!props.focusZoneId) return null
  const parent = props.zones.find(z => z.id === props.focusZoneId)
  if (!parent) return null
  const pa = getZonePosA(parent)
  const pb = getZonePosB(parent)
  if (pa == null || pb == null) return null
  const sa = getZoneSizeA(parent)
  const sb = getZoneSizeB(parent)
  const w = cmToPx(sa) || DEFAULT_W_CM / CM_PER_PX
  const h = cmToPx(sb) || DEFAULT_H_CM / CM_PER_PX
  return {
    x: cmToPx(pa) || 0,
    y: flipY(pb, h),
    w,
    h,
    rotation: parent.rotation || 0,
    name: parent.name || '',
  }
})

function toggleMeasureMode() {
  measureMode.value = !measureMode.value
  measureStart.value = null
  measureEnd.value = null
}

function onMeasureClick(e) {
  if (!measureMode.value) return
  const pt = clientToSvg(e.clientX, e.clientY)
  if (!measureStart.value) {
    measureStart.value = pt
    measureEnd.value = null
  } else {
    measureEnd.value = pt
  }
}

const measureDistance = computed(() => {
  if (!measureStart.value || !measureEnd.value) return null
  const dx = measureEnd.value.x - measureStart.value.x
  const dy = measureEnd.value.y - measureStart.value.y
  const distPx = Math.sqrt(dx * dx + dy * dy)
  const distCm = Math.round(distPx * CM_PER_PX)
  return distCm >= 100 ? `${(distCm / 100).toFixed(2)}m` : `${distCm}cm`
})

function onZoneViewClick(e, zone) {
  if (editMode.value) return
  if (e.shiftKey) {
    const current = [...props.selectedZoneIds]
    const idx = current.indexOf(zone.id)
    if (idx >= 0) {
      current.splice(idx, 1)
    } else {
      current.push(zone.id)
    }
    emit('selection-change', current)
  } else {
    emit('zone-click', zone)
  }
}

function onZoneDblClick(zone) {
  const children = getChildren(zone.id)
  if (children.length) {
    emit('drill-down', zone._tree || zone)
  }
  emit('zone-dblclick', zone)
}

function onZoneContextMenu(e, zone) {
  let target = zone
  if (zone.depth !== 0 && zone._tree) {
    let node = zone._tree
    while (node.parent_id != null) {
      const parent = props.zones.find(z => z.id === node.parent_id)
      if (!parent) break
      node = parent
    }
    const rendered = renderMappedZones.value.find(z => z.id === node.id)
    if (rendered) target = rendered
  }
  contextMenu.x = e.clientX
  contextMenu.y = e.clientY
  contextMenu.zone = target
  contextMenu.show = true
}

function closeContextMenu() {
  contextMenu.show = false
  contextMenu.zone = null
}

function onContextMenuSearchDevices() {
  if (contextMenu.zone) {
    emit('search-devices-in-zone', contextMenu.zone._tree || contextMenu.zone)
  }
  closeContextMenu()
}

function onContextMenuEditProperties() {
  if (contextMenu.zone) {
    emit('zone-properties', contextMenu.zone)
  }
  closeContextMenu()
}

function onContextMenuDrillDown() {
  if (contextMenu.zone) {
    const children = getChildren(contextMenu.zone.id)
    if (children.length) {
      emit('drill-down', contextMenu.zone._tree || contextMenu.zone)
    }
  }
  closeContextMenu()
}

function resizeHandles(zone) {
  const s = 8
  const hs = s / 2
  return [
    { key: 'nw', x: zone.x - hs, y: zone.y - hs, handle: 'nw', cursor: 'nwse-resize', size: s },
    { key: 'ne', x: zone.x + zone.w - hs, y: zone.y - hs, handle: 'ne', cursor: 'nesw-resize', size: s },
    { key: 'sw', x: zone.x - hs, y: zone.y + zone.h - hs, handle: 'sw', cursor: 'nesw-resize', size: s },
    { key: 'se', x: zone.x + zone.w - hs, y: zone.y + zone.h - hs, handle: 'se', cursor: 'nwse-resize', size: s },
    { key: 'n', x: zone.x + zone.w / 2 - hs, y: zone.y - 1, handle: 'n', cursor: 'ns-resize', size: s },
    { key: 's', x: zone.x + zone.w / 2 - hs, y: zone.y + zone.h - hs + 1, handle: 's', cursor: 'ns-resize', size: s },
    { key: 'w', x: zone.x - 1, y: zone.y + zone.h / 2 - hs, handle: 'w', cursor: 'ew-resize', size: s },
    { key: 'e', x: zone.x + zone.w - hs + 1, y: zone.y + zone.h / 2 - hs, handle: 'e', cursor: 'ew-resize', size: s },
  ]
}

function clientToSvg(cx, cy) {
  const rect = viewportRef.value?.getBoundingClientRect()
  if (!rect) return { x: 0, y: 0 }
  return {
    x: (cx - rect.left - panX.value) / scale.value,
    y: (cy - rect.top - panY.value) / scale.value,
  }
}

function zoomIn() { scale.value = Math.min(3, scale.value * 1.2) }
function zoomOut() { scale.value = Math.max(0.3, scale.value / 1.2) }
function resetView() { fitToView() }

function fitToView() {
  updateViewportSize()
  const vh = viewportHeight.value
  if (vh < 50) return
  const zones = renderMappedZones.value.filter(z => z.depth === 0)
  if (!zones.length) return resetView()
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
  for (const z of zones) {
    minX = Math.min(minX, z.x)
    minY = Math.min(minY, z.y)
    maxX = Math.max(maxX, z.x + z.w)
    maxY = Math.max(maxY, z.y + z.h)
  }
  const contentW = maxX - minX
  const contentH = maxY - minY
  if (contentW <= 0 || contentH <= 0) return resetView()
  const pad = 40
  const scaleX = (viewportWidth.value - pad * 2) / contentW
  const scaleY = (viewportHeight.value - pad * 2) / contentH
  const s = Math.min(scaleX, scaleY, 2)
  scale.value = Math.max(0.1, s)
  panX.value = (viewportWidth.value - contentW * s) / 2 - minX * s
  panY.value = (viewportHeight.value - contentH * s) / 2 - minY * s
}

let _panCleanup = null
function onViewportMouseDown(e) {
  if (e.button !== 0 || editMode.value) return
  const startX = e.clientX, startY = e.clientY
  const startPanX = panX.value, startPanY = panY.value
  function onMove(ev) {
    panX.value = startPanX + (ev.clientX - startX)
    panY.value = startPanY + (ev.clientY - startY)
  }
  function onUp() {
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
  _panCleanup = () => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp) }
}

let _dragCleanup = null
function onZoneDragStart(e, zone) {
  if (!editMode.value) return
  if (e.shiftKey) {
    const current = [...props.selectedZoneIds]
    const idx = current.indexOf(zone.id)
    if (idx >= 0) {
      current.splice(idx, 1)
    } else {
      current.push(zone.id)
    }
    emit('selection-change', current)
    return
  }
  e.preventDefault()
  const axes = getViewAxes()
  const startX = e.clientX, startY = e.clientY
  const svg = clientToSvg(e.clientX, e.clientY)
  const origX = Number(zone.x) || 0
  const origY = Number(zone.y) || 0
  const parentOrigA = zone._tree ? (zone._tree[axes.posA] ?? 0) : 0
  const parentOrigB = zone._tree ? (zone._tree[axes.posB] ?? 0) : 0
  function getAllDescendants(zoneId) {
    const result = []
    const kids = getChildren(zoneId)
    for (const k of kids) {
      const ca = getZonePosA(k)
      const cb = getZonePosB(k)
      if (ca != null && cb != null) {
        result.push({ node: k, origA: Number(ca), origB: Number(cb) })
      }
      result.push(...getAllDescendants(k.id))
    }
    return result
  }
  const childDragData = getAllDescendants(zone.id)
  let dragging = false
  const DRAG_THRESHOLD = 4
  function onMove(ev) {
    if (!dragging) {
      if (Math.abs(ev.clientX - startX) < DRAG_THRESHOLD && Math.abs(ev.clientY - startY) < DRAG_THRESHOLD) return
      dragging = true
    }
    const cur = clientToSvg(ev.clientX, ev.clientY)
    const nxA = Math.max(0, snap(Math.round((origX + (cur.x - svg.x)) * CM_PER_PX)))
    const nxB = Math.max(0, snap(Math.round((origY + (cur.y - svg.y)) * CM_PER_PX)))
    overrides[zone.id] = { ...(overrides[zone.id] || {}), [axes.posA]: nxA, [axes.posB]: nxB }
    const deltaA = nxA - parentOrigA
    const deltaB = nxB - parentOrigB
    for (const cd of childDragData) {
      const newA = Math.max(0, snap(cd.origA + deltaA))
      const newB = Math.max(0, snap(cd.origB + deltaB))
      overrides[cd.node.id] = { ...(overrides[cd.node.id] || {}), [axes.posA]: newA, [axes.posB]: newB }
    }
  }
  function onUp() {
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    if (!dragging) {
      emit('zone-click', zone)
      return
    }
    const ov = overrides[zone.id]
    if (ov) {
      emit('zone-move', { id: zone.id, ...ov })
      delete overrides[zone.id]
    }
    for (const cd of childDragData) {
      delete overrides[cd.node.id]
    }
  }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
  _dragCleanup = () => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp) }
}

let _resizeCleanup = null
function onZoneResizeStart(e, zone, handle) {
  e.preventDefault()
  const axes = getViewAxes()
  const svg = clientToSvg(e.clientX, e.clientY)
  const origX = Number(zone.x) || 0
  const origY = Number(zone.y) || 0
  const origW = Number(zone.w) || DEFAULT_W_CM / CM_PER_PX
  const origH = Number(zone.h) || DEFAULT_H_CM / CM_PER_PX
  function onMove(ev) {
    const cur = clientToSvg(ev.clientX, ev.clientY)
    const dx = cur.x - svg.x
    const dy = cur.y - svg.y
    let nx = origX, ny = origY, nw = origW, nh = origH
    if (handle.includes('e')) nw = Math.max(MIN_SIZE, Math.round(origW + dx))
    if (handle.includes('w')) { nw = Math.max(MIN_SIZE, Math.round(origW - dx)); nx = Math.max(0, Math.round(origX + origW - nw)) }
    if (handle.includes('s')) nh = Math.max(MIN_SIZE, Math.round(origH + dy))
    if (handle.includes('n')) { nh = Math.max(MIN_SIZE, Math.round(origH - dy)); ny = Math.max(0, Math.round(origY + origH - nh)) }
    const snx = snap(nx * CM_PER_PX), sny = snap(ny * CM_PER_PX)
    const snw = Math.max(MIN_SIZE * CM_PER_PX, snap(nw * CM_PER_PX))
    const snh = Math.max(MIN_SIZE * CM_PER_PX, snap(nh * CM_PER_PX))
    overrides[zone.id] = {
      ...(overrides[zone.id] || {}),
      [axes.posA]: snx, [axes.posB]: sny,
      [axes.sizeA]: snw, [axes.sizeB]: snh,
    }
  }
  function onUp() {
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    const ov = overrides[zone.id]
    if (ov) {
      emit('zone-resize', { id: zone.id, ...ov })
      delete overrides[zone.id]
    }
  }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
  _resizeCleanup = () => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp) }
}

let _unmappedCleanup = null
function onUnmappedDragStart(e, zone) {
  if (!editMode.value) return
  if (e.shiftKey) {
    const current = [...props.selectedZoneIds]
    const idx = current.indexOf(zone.id)
    if (idx >= 0) {
      current.splice(idx, 1)
    } else {
      current.push(zone.id)
    }
    emit('selection-change', current)
    return
  }
  e.preventDefault()
  const axes = getViewAxes()
  const startX = e.clientX, startY = e.clientY
  let dragging = false
  const DRAG_THRESHOLD = 4
  function onMove(ev) {
    if (!dragging) {
      if (Math.abs(ev.clientX - startX) < DRAG_THRESHOLD && Math.abs(ev.clientY - startY) < DRAG_THRESHOLD) return
      dragging = true
    }
    const cur = clientToSvg(ev.clientX, ev.clientY)
    overrides[zone.id] = {
      ...(overrides[zone.id] || {}),
      [axes.posA]: Math.max(0, snap(Math.round((cur.x - UNMAPPED_CELL_W / 2) * CM_PER_PX))),
      [axes.posB]: Math.max(0, snap(Math.round((cur.y - UNMAPPED_CELL_H / 2) * CM_PER_PX))),
    }
  }
  function onUp() {
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    if (!dragging) {
      emit('zone-click', zone)
      return
    }
    const ov = overrides[zone.id]
    if (ov) {
      emit('zone-move', { id: zone.id, ...ov })
      delete overrides[zone.id]
    }
  }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
  _unmappedCleanup = () => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp) }
}

function onTouchStart(e) {
  if (editMode.value || e.touches.length !== 1) return
  const startX = e.touches[0].clientX, startY = e.touches[0].clientY
  const startPanX = panX.value, startPanY = panY.value
  function onMove(ev) {
    ev.preventDefault()
    panX.value = startPanX + (ev.touches[0].clientX - startX)
    panY.value = startPanY + (ev.touches[0].clientY - startY)
  }
  function onEnd() {
    document.removeEventListener('touchmove', onMove)
    document.removeEventListener('touchend', onEnd)
  }
  document.addEventListener('touchmove', onMove, { passive: false })
  document.addEventListener('touchend', onEnd)
}

function onWheel(e) {
  e.preventDefault()
  scale.value = e.deltaY < 0 ? Math.min(3, scale.value * 1.05) : Math.max(0.3, scale.value / 1.05)
}

function updateViewportSize() {
  if (viewportRef.value) {
    const w = viewportRef.value.clientWidth
    const h = viewportRef.value.clientHeight
    if (w > 0) viewportWidth.value = w
    if (h > 0) viewportHeight.value = h
  }
}

let _resizeHeightCleanup = null
function onResizeHandleStart(e) {
  e.preventDefault()
  const startY = e.clientY
  const startH = viewportHeight.value
  function onMove(ev) {
    const dh = ev.clientY - startY
    viewportHeight.value = Math.max(200, Math.round(startH + dh))
  }
  function onUp() {
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
  _resizeHeightCleanup = () => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp) }
}

onMounted(() => {
  updateViewportSize()
  viewportRef.value?.addEventListener('wheel', onWheel, { passive: false })
  window.addEventListener('resize', updateViewportSize)
  document.addEventListener('click', closeContextMenu)
  document.addEventListener('contextmenu', closeContextMenu)
  if (viewportHeight.value > 50) {
    nextTick(() => fitToView())
  }
})

onUnmounted(() => {
  _panCleanup?.(); _dragCleanup?.(); _resizeCleanup?.(); _unmappedCleanup?.(); _resizeHeightCleanup?.()
  window.removeEventListener('resize', updateViewportSize)
  document.removeEventListener('click', closeContextMenu)
  document.removeEventListener('contextmenu', closeContextMenu)
})

defineExpose({ fitToView })
</script>

<style scoped>
.warehouse-map-container { width: 100%; height: 100%; display: flex; flex-direction: column; }

.view-mode-toggle { border-radius: 6px; overflow: hidden; }

.breadcrumb-bar {
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  min-height: 32px;
}

.warehouse-map-viewport {
  width: 100%; flex: 1; min-height: 0; overflow: hidden;
  border: 1px solid var(--q-separator-color, #ccc);
  border-radius: 8px; background: var(--q-dark-page, #1a1a2e);
  cursor: grab; position: relative;
}
.warehouse-map-viewport:active { cursor: grabbing; }
.warehouse-map-viewport.edit-mode { cursor: default; border-color: var(--q-warning, #f59e0b); border-width: 2px; }

.map-resize-handle {
  width: 100%; height: 6px; cursor: ns-resize;
  background: transparent; position: relative;
}
.map-resize-handle::after {
  content: '';
  position: absolute; left: 50%; top: 50%;
  transform: translate(-50%, -50%);
  width: 40px; height: 3px; border-radius: 2px;
  background: var(--q-separator-color, #ccc);
}
.map-resize-handle:hover::after {
  background: var(--q-warning, #f59e0b);
}

.warehouse-map-svg { display: block; }
.warehouse-map-svg.measure-mode { cursor: crosshair; }

.warehouse-zone-rect {
  cursor: pointer; transition: opacity 0.15s ease; rx: 4; ry: 4;
}
.warehouse-zone-rect:hover { opacity: 0.85; filter: brightness(1.15); }
.warehouse-zone-rect.draggable { cursor: move; }
.warehouse-zone-rect.highlighted { stroke-width: 3; filter: drop-shadow(0 0 6px rgba(255, 215, 0, 0.6)); }
.warehouse-zone-rect.selected { stroke: #2196F3; stroke-width: 3; }

.warehouse-zone-label { fill: #fff; font-size: 11px; font-weight: 600; font-family: inherit; }
.warehouse-zone-label-sm { fill: rgba(255,255,255,0.85); font-size: 9px; font-weight: 500; font-family: inherit; }
.warehouse-parent-outline-label { fill: rgba(255,165,0,0.85); font-size: 10px; font-weight: 600; font-family: inherit; stroke: rgba(0,0,0,0.7); stroke-width: 2px; paint-order: stroke fill; }
.warehouse-zone-count { fill: rgba(255,255,255,0.75); font-size: 9px; font-family: inherit; }
.warehouse-zone-subcount { fill: rgba(255,255,255,0.5); font-size: 8px; font-family: inherit; }
.warehouse-zone-dim { fill: rgba(255,255,255,0.4); font-size: 7px; font-family: inherit; }
.warehouse-unmapped-title { fill: #888; font-size: 10px; font-weight: 600; font-family: inherit; }
.unmapped-label { font-size: 9px; }
.resize-handle { cursor: nwse-resize; }
.zone-context-menu {
  position: fixed; z-index: 9999;
  background: var(--q-dark, #1a1a2e);
  border: 1px solid var(--q-separator-color, #555);
  border-radius: 6px; padding: 4px 0;
  box-shadow: 0 4px 12px rgba(0,0,0,0.5);
  min-width: 180px;
}
.zone-context-menu-item {
  padding: 6px 12px; cursor: pointer;
  font-size: 13px; color: #fff;
  display: flex; align-items: center;
}
.zone-context-menu-item:hover { background: rgba(255,255,255,0.1); }
</style>
