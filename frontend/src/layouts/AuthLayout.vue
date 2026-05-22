<template>
  <q-layout view="hHh lpR fFf">
    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup>
// minimal layout for auth pages
</script>

<style scoped>
/* keep consistent background with auth pages */
.q-page-container { background: #0d1117; }
/* Improve contrast for all auth pages/forms */
.q-page-container ::v-deep .q-field__label {
  color: rgba(255,255,255,0.86) !important;
}
.q-page-container ::v-deep .q-field__control,
.q-page-container ::v-deep .q-field__native,
.q-page-container ::v-deep .q-input__control .q-field__control {
  color: rgba(255,255,255,0.95) !important;
}
.q-page-container ::v-deep .q-icon {
  color: rgba(255,255,255,0.85) !important;
}
.q-page-container ::v-deep .text-caption {
  color: rgba(255,255,255,0.7) !important;
}
</style>
