<template>
  <q-page class="q-pa-md">
    <div class="row q-col-gutter-md">
      <!-- Article index -->
      <template v-if="!selectedArticle">
        <div class="col-12">
          <div class="text-h5 q-mb-xs">{{ t('help.title') }}</div>
          <div class="text-body2 text-grey-7 q-mb-md">{{ t('help.intro') }}</div>
        </div>
        <div
          v-for="grp in groups"
          :key="grp.key"
          class="col-12 col-sm-6 col-md-4"
        >
          <q-card flat bordered>
            <q-card-section class="bg-primary text-white">
              <div class="text-subtitle1">{{ grp.label }}</div>
            </q-card-section>
            <q-list separator>
              <q-item
                v-for="art in articlesByGroup(grp.key)"
                :key="art.id"
                clickable
                v-ripple
                :to="`/help/${art.id}`"
              >
                <q-item-section>
                  <q-item-label>{{ art.title }}</q-item-label>
                  <q-item-label caption>{{ art.summary }}</q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>
        </div>
      </template>

      <!-- Single article -->
      <template v-else>
        <div class="col-12">
          <q-btn
            flat
            :label="t('help.back')"
            icon="arrow_back"
            to="/help"
            class="q-mb-sm"
            no-caps
          />
          <div class="text-h5 q-mb-xs">{{ selectedArticle.title }}</div>
          <div class="text-body2 text-grey-7 q-mb-md">{{ selectedArticle.summary }}</div>

          <q-card
            v-for="(sec, i) in selectedArticle.sections"
            :key="i"
            flat
            bordered
            class="q-mb-md"
          >
            <q-card-section>
              <div class="text-subtitle1 text-primary q-mb-sm">{{ sec.heading }}</div>
              <p
                v-for="(para, j) in sec.body"
                :key="j"
                class="text-body2 q-mb-xs"
              >
                {{ para }}
              </p>
            </q-card-section>
          </q-card>

          <q-banner v-if="!selectedArticle.sections.length" class="text-body2">
            {{ t('help.comingSoon') }}
          </q-banner>
        </div>
      </template>
    </div>
  </q-page>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'

const { t, tm, locale } = useI18n()
const route = useRoute()

// `tm` returns the structured help messages (objects/arrays) for the active
// locale; referencing `locale` keeps the lists reactive on language switch.
const articles = computed(() => {
  void locale.value
  const raw = (tm('help.articles') || {})
  return Object.entries(raw).map(([id, a]) => ({ id, ...a }))
})

const groups = computed(() => {
  void locale.value
  const raw = (tm('help.groups') || {})
  return Object.entries(raw).map(([key, label]) => ({ key, label }))
})

function articlesByGroup(key) {
  return articles.value.filter((a) => a.group === key)
}

const selectedArticle = computed(() => {
  const id = route.params.articleId
  if (!id) return null
  return articles.value.find((a) => a.id === id) || null
})
</script>
