<template>
  <div class="ec-scanner-target" :class="{ 'ec-scanner-target--feedback': !!feedback }">
    <transition name="ec-scan-pulse" mode="out-in">
      <div v-if="feedback" key="feedback" class="ec-scanner-target__feedback">
        <ScanFeedback
          :type="feedback.type"
          :icon="feedback.icon"
          :label="feedback.label"
          :sublabel="feedback.sublabel"
          :thumbnail="feedback.thumbnail"
        />
      </div>
      <div v-else key="idle" class="ec-scanner-target__inner">
        <q-icon class="ec-scanner-target__icon" :name="icon" />
        <div class="ec-scanner-target__label">{{ title }}</div>
        <div class="text-caption ec-scanner-target__subtitle">{{ subtitle }}</div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import ScanFeedback from './ScanFeedback.vue'

defineProps({
  icon: { type: String, default: 'qr_code_scanner' },
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  // feedback: null | { type: 'success'|'error'|'info', icon, label, sublabel, thumbnail }
  feedback: { type: Object, default: null },
})
</script>

<style scoped>
.ec-scanner-target {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 160px;
  padding: var(--ec-space-lg, 24px);
  background: var(--ec-surface-800, #11181D);
  border: 2px dashed var(--ec-primary, #3F873F);
  border-radius: 16px;
  color: var(--ec-text, #e9f1ee);
  text-align: center;
}

.ec-scanner-target__icon {
  color: var(--ec-primary, #3F873F);
  font-size: 48px;
  margin-bottom: var(--ec-space-sm, 8px);
}

.ec-scanner-target__label {
  font-family: var(--ec-font-heading, "Myriad Pro", sans-serif);
  font-size: 1.1rem;
  font-weight: 600;
}

.ec-scanner-target__subtitle {
  margin-top: 2px;
}

.ec-scanner-target--feedback {
  border-style: solid;
}

.ec-scan-pulse-enter-active {
  animation: ec-scan-pulse 0.4s ease-out;
}

@keyframes ec-scan-pulse {
  0% { transform: scale(0.92); opacity: 0; }
  60% { transform: scale(1.02); opacity: 1; }
  100% { transform: scale(1); }
}
</style>
