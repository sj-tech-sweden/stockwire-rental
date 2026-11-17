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
    <q-card class="tour-card" :class="cardPositionClass" :style="cardStyle" flat bordered>
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
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useTour } from '../help/useTour'

const { t } = useI18n()
const router = useRouter()
const { isActive, isFirst, isLast, currentIndex, totalSteps, title, text, currentStepMeta, next, prev, stop } =
  useTour()

const highlightRect = ref(null)
let retryTimers = []

function clearRetries() {
  retryTimers.forEach((id) => clearTimeout(id))
  retryTimers = []
}

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
  // Add a margin so the highlighted element is not flush against the dim.
  const pad = 6
  highlightRect.value = {
    top: Math.max(0, r.top - pad),
    left: Math.max(0, r.left - pad),
    width: r.width + pad * 2,
    height: r.height + pad * 2,
  }
}

// Re-measure with a few retries because the target page may still be mounting
// (lazy-loaded route components) when the step becomes active.
function scheduleMeasure() {
  clearRetries()
  measureTarget()
  ;[120, 300, 600].forEach((ms) => {
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

const cardStyle = computed(() => {
  const r = highlightRect.value
  if (!r) return { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }
  // Place the card below the target if there is room, otherwise above.
  const cardW = 380
  const cardH = 240
  const below = r.top + r.height + 16
  const above = r.top - cardH - 16
  const top = below + cardH < window.innerHeight ? below : Math.max(12, above)
  let left = r.left + r.width / 2 - cardW / 2
  left = Math.min(Math.max(12, left), window.innerWidth - cardW - 12)
  return { top: `${top}px`, left: `${left}px` }
})

const cardPositionClass = computed(() => (highlightRect.value ? '' : 'tour-card--centered'))

function onResize() {
  measureTarget()
}

watch(
  () => [isActive.value, currentIndex.value, router.currentRoute.value.fullPath],
  () => {
    if (isActive.value) scheduleMeasure()
  },
)

onMounted(() => {
  window.addEventListener('resize', onResize)
  window.addEventListener('scroll', measureTarget, true)
  if (isActive.value) scheduleMeasure()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('scroll', measureTarget, true)
  clearRetries()
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
  /* The huge spread shadow dims everything except the highlighted element. */
  box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.5);
  pointer-events: none;
  transition: top 0.18s ease, left 0.18s ease, width 0.18s ease, height 0.18s ease;
}
.tour-card {
  position: absolute;
  width: 380px;
  max-width: calc(100vw - 24px);
  pointer-events: auto; /* the card itself stays interactive */
}
.tour-card--centered {
  /* centered positioning is applied via inline style; this is a no-op hook */
}
</style>
