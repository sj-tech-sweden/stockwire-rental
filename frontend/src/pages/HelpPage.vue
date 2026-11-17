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
          v-for="grp in groupTree"
          :key="grp.key"
          class="col-12 col-sm-6 col-md-4"
        >
          <q-card flat bordered>
            <q-card-section class="bg-primary text-white">
              <div class="text-subtitle1">{{ grp.label }}</div>
            </q-card-section>
            <q-list separator>
              <template v-for="item in grp.items" :key="item.article.id">
                <q-item
                  clickable
                  v-ripple
                  :to="`/help/${item.article.id}`"
                >
                  <q-item-section>
                    <q-item-label>{{ item.article.title }}</q-item-label>
                    <q-item-label caption>{{ item.article.summary }}</q-item-label>
                  </q-item-section>
                </q-item>
                <q-list
                  v-if="item.children.length"
                  dense
                  bordered
                  separator
                  :class="$q.dark.isActive ? 'q-ml-md q-mb-xs bg-grey-9' : 'q-ml-md q-mb-xs bg-grey-2'"
                >
                  <q-item
                    v-for="child in item.children"
                    :key="child.id"
                    clickable
                    v-ripple
                    :to="`/help/${child.id}`"
                  >
                    <q-item-section avatar class="q-pr-none">
                      <q-icon name="subdirectory_arrow_right" size="xs" class="text-grey-6" />
                    </q-item-section>
                    <q-item-section>
                      <q-item-label>{{ child.title }}</q-item-label>
                      <q-item-label caption>{{ child.summary }}</q-item-label>
                    </q-item-section>
                  </q-item>
                </q-list>
              </template>
            </q-list>
          </q-card>
        </div>
      </template>

      <!-- Single article -->
      <template v-else>
        <div class="col-12">
          <q-btn
            flat
            :label="parentArticle ? t('help.backTo', { name: parentArticle.title }) : t('help.back')"
            :icon="parentArticle ? 'subdirectory_arrow_left' : 'arrow_back'"
            :to="parentArticle ? `/help/${parentArticle.id}` : '/help'"
            class="q-mb-sm"
            no-caps
          />
          <div class="text-h5 q-mb-xs">{{ selectedArticle.title }}</div>
          <div class="text-body2 text-grey-7 q-mb-md">{{ selectedArticle.summary }}</div>

          <q-btn
            v-if="tourAvailable"
            class="q-mb-md"
            color="primary"
            icon="play_circle"
            :label="t('help.tour.startClickThrough')"
            no-caps
            @click="startTour(selectedArticle.id)"
          />

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

          <q-card v-if="childArticles.length" flat bordered class="q-mt-md">
            <q-card-section>
              <div class="text-subtitle2 q-mb-sm">{{ t('help.inThisSection') }}</div>
              <q-list separator>
                <q-item
                  v-for="child in childArticles"
                  :key="child.id"
                  clickable
                  v-ripple
                  :to="`/help/${child.id}`"
                >
                  <q-item-section avatar class="q-pr-none">
                    <q-icon name="subdirectory_arrow_right" size="xs" class="text-grey-6" />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label>{{ child.title }}</q-item-label>
                    <q-item-label caption>{{ child.summary }}</q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
            </q-card-section>
          </q-card>
        </div>
      </template>
    </div>
  </q-page>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useTour } from '../help/useTour'
import { TOUR_IDS } from '../help/tours'

const { t, tm, locale } = useI18n()
const route = useRoute()
const { startTour } = useTour()

// `tm` returns the structured help messages (objects/arrays) for the active
// locale; referencing `locale` keeps the lists reactive on language switch.
const articles = computed(() => {
  void locale.value
  const raw = (tm('help.articles') || {})
  return Object.entries(raw).map(([id, a]) => ({ id, ...a }))
})

const articlesById = computed(() => {
  const map = {}
  for (const a of articles.value) map[a.id] = a
  return map
})

// Map of parent article id -> child articles (the nesting relationship).
const childrenByParent = computed(() => {
  const map = {}
  for (const a of articles.value) {
    if (a.parent) (map[a.parent] = map[a.parent] || []).push(a)
  }
  return map
})

const groups = computed(() => {
  void locale.value
  const raw = (tm('help.groups') || {})
  return Object.entries(raw).map(([key, label]) => ({ key, label }))
})

// A grouped, nested view of the index: each group lists its top-level articles
// (those without a parent in the same group) with their children indented.
const groupTree = computed(() => {
  void locale.value
  return groups.value
    .map((g) => {
      const topLevel = articles.value.filter(
        (a) =>
          a.group === g.key &&
          (!a.parent ||
            !articlesById.value[a.parent] ||
            articlesById.value[a.parent].group !== g.key),
      )
      return {
        key: g.key,
        label: g.label,
        items: topLevel.map((article) => ({
          article,
          children: (childrenByParent.value[article.id] || []).filter(
            (c) => c.group === g.key,
          ),
        })),
      }
    })
    .filter((g) => g.items.length)
})

const selectedArticle = computed(() => {
  const id = route.params.articleId
  if (!id) return null
  return articles.value.find((a) => a.id === id) || null
})

const parentArticle = computed(() =>
  selectedArticle.value?.parent ? articlesById.value[selectedArticle.value.parent] || null : null,
)

// Walkthrough guides (articles under the "walkthroughs" group that are not the
// overview) have an interactive click-through tour keyed by their article id.
const tourAvailable = computed(
  () =>
    selectedArticle.value &&
    selectedArticle.value.group === 'walkthroughs' &&
    selectedArticle.value.id !== 'walkthroughs' &&
    TOUR_IDS.includes(selectedArticle.value.id),
)

const childArticles = computed(() =>
  selectedArticle.value ? childrenByParent.value[selectedArticle.value.id] || [] : [],
)
</script>
