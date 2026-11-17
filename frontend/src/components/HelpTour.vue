<template>
  <div v-if="isActive" class="tour-layer">
    <!-- Spotlight on a target element when one is found -->
    <div
      v-if="highlightRect"
      class="tour-spotlight"
      :style="spotlightStyle"
    />
    <!-- Gentle full-screen dim when there is no specific target -->
    <div v-else class="tour-dim" />

    <!-- Coach card (kept interactive; the layer itself ignores pointer events) -->
    <q-card
      ref="cardEl"
      class="tour-card"
      :style="cardStyle"
      flat
      bordered
    >
      <q-card-section class="q-pb-none">
        <div class="row items-center justify-between no-wrap">
          <div class="text-overline text-primary q-mb-none">
            {{ t('help.tour.stepOf', { current: currentIndex + 1, total: totalSteps }) }}
          </div>
          <q-btn
            flat
            round
            dense
            icon="close"
            :aria-label="t('help.tour.exit')"
            @click="stop"
          />
        </div>
        <div class="text-subtitle1 text-weight-bold q-mt-xs">{{ title }}</div>
      </q-card-section>

      <q-card-section class="q-pt-sm">
        <p class="text-body2 q-mb-none">{{ text }}</p>
      </q-card-section>

      <q-card-actions align="between" class="q-px-md q-pb-md">
        <q-btn
          flat
          :label="t('help.tour.back')"
          icon="arrow_back"
          :disable="isFirst"
          @click="prev"
        />
        <div class="row q-gutter-sm">
          <q-btn
            flat
            :label="t('help.tour.skip')"
            @click="stop"
          />
          <q-btn
            unelevated
            color="primary"
            :label="isLast ? t('help.tour.finish') : t('help.tour.next')"
            :icon-right="isLast ? undefined : 'arrow_forward'"
            @click="next"
          />
        </div>
      </q-card-actions>
    </q-card>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useTour } from '../help/useTour'

const { t } = useI18n()
const router = useRouter()
const {
  isActive,
  isFirst,
  isLast,
  currentIndex,
  totalSteps,
  title,
  text,
  currentStepMeta,
  next,
  prev,
  stop,
} = useTour()

const cardEl = ref(null)
const highlightRect = ref(null)
const positionTick = ref(0) // bumped after the card renders so its real height is used
const scrolledForStep = ref(false)
let retryTimers = []
let moTimer = null
let mo = null

function clearRetries() {
  retryTimers.forEach((id) => clearTimeout(id))
  retryTimers = []
}

// Find the target element and record its on-screen rect. Falls back to null
// (centered card) when the selector is absent — e.g. an anchor that only exists
// inside a dialog the user has not opened yet.
function measureTarget() {
  const target = currentStepMeta.value?.target
  if (!target) {
    highlightRect.value = null
    return
  }
  const el = document.querySelector(target)
  if (!el) {
    highlightRect.value = null
    return
  }
  const r = el.getBoundingClientRect()
  const pad = 6
  highlightRect.value = {
    top: Math.max(0, r.top - pad),
    left: Math.max(0, r.left - pad),
    width: r.width + pad * 2,
    height: r.height + pad * 2,
  }
  // Bring the element into view once per step so off-screen anchors are visible.
  if (!scrolledForStep.value) {
    const vh = window.innerHeight
    if (r.top < 12 || r.bottom > vh - 12) {
      el.scrollIntoView({ block: 'center', behavior: 'smooth' })
      scrolledForStep.value = true
    }
  }
}

// The target page (and its DOM) may still be mounting after a route change, so
// probe for it a few times over the first few seconds.
function scheduleMeasure() {
  clearRetries()
  measureTarget()
  ;[150, 400, 800, 1500, 3000].forEach((ms) => {
    retryTimers.push(setTimeout(measureTarget, ms))
  })
}

const spotlightStyle = computed(() => {
  const r = highlightRect.value
  if (!r) return {}
  return {
    top: `${r.top}px`,
    left: `${r.left}px`,
    width: `${r.width}px`,
    height: `${r.height}px`,
  }
})

// Position the coach card near the spotlight, clamped within the viewport, or
// centered when there is no target.
const cardStyle = computed(() => {
  void positionTick.value
  const r = highlightRect.value
  const vw = window.innerWidth
  const vh = window.innerHeight
  const cw = Math.min(380, vw - 24)
  if (!r) {
    return {
      top: '50%',
      left: '50%',
      transform: 'translate(-50%, -50%)',
      width: `${cw}px`,
    }
  }
  const ch = cardEl.value?.offsetHeight || 260
  const below = r.bottom + 12
  const above = r.top - ch - 12
  let top
  if (below + ch <= vh - 12) top = below
  else if (above >= 12) top = above
  else top = Math.max(12, Math.min(vh - ch - 12, r.top))
  let left = r.left + r.width / 2 - cw / 2
  left = Math.max(12, Math.min(vw - cw - 12, left))
  return { top: `${top}px`, left: `${left}px`, width: `${cw}px` }
})

function onResize() {
  measureTarget()
}

function onScroll() {
  measureTarget()
}

// Re-measure when the DOM changes (covers lazy component mount + dialog open).
function onMutations() {
  clearTimeout(moTimer)
  moTimer = setTimeout(measureTarget, 120)
}

watch(highlightRect, async () => {
  await nextTick()
  positionTick.value++
})

watch(
  () => [isActive.value, currentIndex.value, router.currentRoute.value.fullPath],
  () => {
    if (isActive.value) {
      scrolledForStep.value = false
      scheduleMeasure()
    }
  },
)

onMounted(() => {
  window.addEventListener('resize', onResize)
  window.addEventListener('scroll', onScroll, true)
  mo = new MutationObserver(onMutations)
  mo.observe(document.body, { childList: true, subtree: true })
  if (isActive.value) {
    scrolledForStep.value = false
    scheduleMeasure()
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('scroll', onScroll, true)
  if (mo) mo.disconnect()
  clearRetries()
  clearTimeout(moTimer)
})
</script>

<style scoped>
.tour-layer {
  position: fixed;
  inset: 0;
  z-index: 6000;
  /* Let clicks pass through to the real UI so the user can act on each step. */
  pointer-events: none;
}
.tour-dim {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  pointer-events: none;
}
.tour-spotlight {
  position: absolute;
  border-radius: 10px;
  border: 2px solid var(--q-primary);
  /* The huge spread shadow dims everything except the highlighted element. */
  box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.5);
  pointer-events: none;
  transition: top 0.18s ease, left 0.18s ease, width 0.18s ease, height 0.18s ease;
  animation: tour-pulse 1.6s ease-in-out infinite;
}
@keyframes tour-pulse {
  0%, 100% { border-color: var(--q-primary); }
  50% { border-color: rgba(255, 255, 255, 0.85); }
}
.tour-card {
  position: absolute;
  pointer-events: auto; /* the card itself stays interactive */
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35);
}
</style>
