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
const positionTick = ref(0) // bumped so placement recomputes with the real card height
const scrolledForStep = ref(false)
let retryTimers = []
let moTimer = null
let mo = null
let cardRO = null

// The card ref points at a Quasar QCard component instance, whose `.offsetHeight`
// is undefined — read the underlying DOM node instead so placement uses the real
// rendered height (wrapped text on narrow viewports can make it much taller than
// the 260px fallback, which previously let the card overlap its target).
function cardHeight() {
  const el = cardEl.value?.$el || cardEl.value
  return el?.offsetHeight || 260
}

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

// Position the coach card near the spotlight without ever covering the
// highlighted element. Try below, above, right, then left; if none fit fully in
// the viewport, fall back to the top or bottom edge that does not overlap the
// target. Centered only when there is no target at all.
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
  const ch = cardHeight()
  const gap = 12
  const fits = (c) => c.top >= 12 && c.top + ch <= vh - 12 && c.left >= 12 && c.left + cw <= vw - 12
  const overlaps = (c) =>
    !(c.left + cw <= r.left || c.left >= r.right || c.top + ch <= r.top || c.top >= r.bottom)
  const candidates = [
    { top: r.bottom + gap, left: r.left + r.width / 2 - cw / 2 }, // below
    { top: r.top - ch - gap, left: r.left + r.width / 2 - cw / 2 }, // above
    { top: r.top + r.height / 2 - ch / 2, left: r.right + gap }, // right
    { top: r.top + r.height / 2 - ch / 2, left: r.left - cw - gap }, // left
  ]
  let pos = candidates.find((c) => fits(c) && !overlaps(c))
  if (!pos) {
    // No candidate fully fits: clamp to an edge that does not overlap the target.
    const atBottom = { top: vh - ch - 12, left: Math.min(Math.max(r.left + r.width / 2 - cw / 2, 12), vw - cw - 12) }
    const atTop = { top: 12, left: atBottom.left }
    pos = overlaps(atBottom) ? atTop : atBottom
  }
  // Hard guarantee: if the chosen spot still intersects the target, flip to the
  // opposite vertical side; if that fails too, pin to the non-overlapping edge.
  if (overlaps(pos)) {
    const opposite = pos.top < r.top
      ? { top: r.bottom + gap, left: pos.left } // was above -> go below
      : { top: r.top - ch - gap, left: pos.left } // was below -> go above
    if (!overlaps(opposite) && opposite.top >= 12 && opposite.top + ch <= vh - 12) {
      pos = opposite
    } else {
      const atTop = { top: 12, left: pos.left }
      const atBottom = { top: vh - ch - 12, left: pos.left }
      pos = overlaps(atTop) ? atBottom : atTop
    }
  }
  pos.top = Math.min(Math.max(pos.top, 12), Math.max(12, vh - ch - 12))
  pos.left = Math.min(Math.max(pos.left, 12), Math.max(12, vw - cw - 12))
  return { top: `${pos.top}px`, left: `${pos.left}px`, width: `${cw}px` }
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
  // Re-measure placement whenever the card's rendered size changes (e.g. text
  // wraps differently after a locale/i18n swap or viewport change).
  const cardNode = cardEl.value?.$el || cardEl.value
  if (cardNode && typeof ResizeObserver !== 'undefined') {
    cardRO = new ResizeObserver(() => {
      positionTick.value++
    })
    cardRO.observe(cardNode)
  }
  if (isActive.value) {
    scrolledForStep.value = false
    scheduleMeasure()
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('scroll', onScroll, true)
  if (mo) mo.disconnect()
  if (cardRO) cardRO.disconnect()
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
