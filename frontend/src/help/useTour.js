// Interactive click-through tour engine.
//
// A tour walks the user through the real interface: for each step it navigates
// to the relevant route and shows a coach card (see HelpTour.vue). The engine
// keeps a single shared reactive state so any component (the "Start
// click-through" button, the overlay) reads the same tour.
//
// Text for each step is read from i18n (help.tours.<id>.steps[<i>].{title,text})
// so it follows the active language. Step count is driven by the metadata in
// tours.js; the i18n arrays must have at least that many entries.

import { reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { TOURS } from './tours'

const state = reactive({
  activeTourId: null,
  stepIndex: 0,
})

export function useTour() {
  const router = useRouter()
  const { t, locale } = useI18n()

  const isActive = computed(() => !!state.activeTourId)

  const steps = computed(() =>
    state.activeTourId ? TOURS[state.activeTourId] || [] : [],
  )
  const totalSteps = computed(() => steps.value.length)
  const currentIndex = computed(() => state.stepIndex)
  const isFirst = computed(() => state.stepIndex === 0)
  const isLast = computed(() => totalSteps.value > 0 && state.stepIndex === totalSteps.value - 1)

  const base = computed(() => (state.activeTourId ? `help.tours.${state.activeTourId}.steps` : ''))

  // `locale` is read so the computed values re-evaluate when language changes.
  const title = computed(() => {
    void locale.value
    if (!state.activeTourId) return ''
    return t(`${base.value}.${state.stepIndex}.title`)
  })
  const text = computed(() => {
    void locale.value
    if (!state.activeTourId) return ''
    return t(`${base.value}.${state.stepIndex}.text`)
  })

  const currentStepMeta = computed(() => steps.value[state.stepIndex] || null)

  async function navigateTo(route) {
    if (!route) return
    if (router.currentRoute.value.path !== route) {
      try {
        await router.push(route)
      } catch {
        // navigation guards / redirects may reject; ignore for tour purposes
      }
    }
  }

  function syncStep() {
    const step = currentStepMeta.value
    if (step) navigateTo(step.route)
  }

  async function startTour(id) {
    if (!TOURS[id]) return
    state.activeTourId = id
    state.stepIndex = 0
    syncStep()
  }

  function goTo(index) {
    if (index < 0 || index >= totalSteps.value) return
    state.stepIndex = index
    syncStep()
  }

  function next() {
    if (isLast.value) {
      stop()
      return
    }
    goTo(state.stepIndex + 1)
  }

  function prev() {
    goTo(state.stepIndex - 1)
  }

  function stop() {
    state.activeTourId = null
    state.stepIndex = 0
  }

  return {
    isActive,
    totalSteps,
    currentIndex,
    isFirst,
    isLast,
    title,
    text,
    currentStepMeta,
    startTour,
    next,
    prev,
    stop,
  }
}
