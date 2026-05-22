import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useQuasar } from 'quasar'

export function useCompactGrid(maxWidth = 1024) {
  const $q = useQuasar()
  const viewportWidth = ref(typeof window !== 'undefined' ? window.innerWidth : maxWidth + 1)

  function updateViewportWidth() {
    if (typeof window === 'undefined') return
    viewportWidth.value = window.innerWidth || document.documentElement.clientWidth || maxWidth + 1
  }

  onMounted(() => {
    updateViewportWidth()
    window.addEventListener('resize', updateViewportWidth, { passive: true })
  })

  onBeforeUnmount(() => {
    if (typeof window === 'undefined') return
    window.removeEventListener('resize', updateViewportWidth)
  })

  return computed(() => $q.screen.lt.md || viewportWidth.value <= maxWidth)
}
