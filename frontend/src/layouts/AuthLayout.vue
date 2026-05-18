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
</style>
