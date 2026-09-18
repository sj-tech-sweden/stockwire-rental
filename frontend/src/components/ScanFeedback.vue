<template>
  <div class="ec-scan-feedback" :class="`ec-scan-feedback--${type}`">
    <q-icon v-if="icon" :name="icon" class="ec-scan-feedback__icon" />
    <div class="ec-scan-feedback__content">
      <div v-if="label" class="ec-scan-feedback__label">{{ label }}</div>
      <div v-if="sublabel" class="ec-scan-feedback__sublabel">{{ sublabel }}</div>
    </div>
    <q-img
      v-if="thumbnail"
      :src="thumbnail"
      class="ec-scan-feedback__thumb"
      fit="cover"
    >
      <template #error>
        <div class="absolute-full flex flex-center bg-grey-3">
          <q-icon name="broken_image" color="grey-6" size="18px" />
        </div>
      </template>
    </q-img>
  </div>
</template>

<script setup>
defineProps({
  type: { type: String, default: 'success' }, // success | error | info
  icon: { type: String, default: '' },
  label: { type: String, default: '' },
  sublabel: { type: String, default: '' },
  thumbnail: { type: String, default: '' },
})
</script>

<style scoped>
.ec-scan-feedback {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 16px;
  border-radius: var(--ec-radius-md, 8px);
  background: rgba(63, 135, 63, 0.12);
  border: 1px solid var(--ec-success, #3F873F);
  color: var(--ec-text, #e9f1ee);
}

.ec-scan-feedback--success {
  background: rgba(63, 135, 63, 0.12);
  border-color: var(--ec-success, #3F873F);
}

.ec-scan-feedback--error {
  background: rgba(230, 86, 86, 0.12);
  border-color: var(--ec-danger, #E65656);
}

.ec-scan-feedback--info {
  background: rgba(79, 128, 255, 0.12);
  border-color: var(--ec-profile-blue, #4F80FF);
}

.ec-scan-feedback__icon {
  font-size: 28px;
  flex: 0 0 auto;
}

.ec-scan-feedback--success .ec-scan-feedback__icon { color: var(--ec-success, #3F873F); }
.ec-scan-feedback--error .ec-scan-feedback__icon { color: var(--ec-danger, #E65656); }
.ec-scan-feedback--info .ec-scan-feedback__icon { color: var(--ec-profile-blue, #4F80FF); }

.ec-scan-feedback__content {
  min-width: 0;
  flex: 1 1 auto;
  text-align: left;
}

.ec-scan-feedback__label {
  font-weight: 600;
  font-size: 0.98rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ec-scan-feedback__sublabel {
  font-size: 0.82rem;
  opacity: 0.82;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ec-scan-feedback__thumb {
  width: 48px;
  height: 48px;
  flex: 0 0 48px;
  border-radius: 8px;
}
</style>
