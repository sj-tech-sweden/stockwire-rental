<template>
  <q-page class="q-pa-md ec-page">
    <div class="text-h5 q-mb-md">{{ t('reports.title') }}</div>

    <q-tabs v-model="tab" inline-label align="left" class="q-mb-md">
      <q-tab name="letterheads" icon="description" :label="t('reports.letterheads')" />
      <q-tab name="templates" icon="summarize" :label="t('reports.templates')" />
    </q-tabs>

    <q-tab-panels v-model="tab" animated>
      <q-tab-panel name="letterheads" class="q-pa-none">
        <q-card class="ec-card q-pa-md">
          <LetterheadManager />
        </q-card>
      </q-tab-panel>
      <q-tab-panel name="templates" class="q-pa-none">
        <q-card class="ec-card q-pa-md">
          <ReportTemplateManager />
        </q-card>
      </q-tab-panel>
    </q-tab-panels>
  </q-page>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import LetterheadManager from '../components/LetterheadManager.vue'
import ReportTemplateManager from '../components/ReportTemplateManager.vue'

const { t } = useI18n()
const tab = ref('letterheads')
</script>
