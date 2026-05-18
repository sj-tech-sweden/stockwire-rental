<template>
  <q-layout view="hHh lpR fFf" class="ec-layout">
    <q-header elevated class="ec-header">
      <q-toolbar>
        <q-toolbar-title>Stockwire Rental</q-toolbar-title>
        <q-btn flat dense label="Home" to="/" />
        <q-btn flat dense label="Auth" to="/auth" />
        <q-btn flat dense label="Inventory" to="/inventory" />
        <q-btn flat dense label="Jobs" to="/jobs" />
        <q-btn flat dense label="Finance" to="/finance" />
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>
