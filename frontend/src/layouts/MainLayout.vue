<template>
  <q-layout view="hHh lpR fFf" class="ec-layout">
    <q-header elevated class="ec-header" :style="headerStyle">
      <q-toolbar>
        <q-btn
          flat
          dense
          round
          icon="menu"
          :aria-label="t('app.menu')"
          @click="handleMenuClick"
        />
        <q-toolbar-title class="title row items-center no-wrap q-gutter-sm">
          <q-img
            v-if="headerLogoUrl"
            :src="headerLogoUrl"
            style="width: 36px; height: 36px"
            fit="contain"
            spinner-color="primary"
            alt="Company logo"
          />
          <span>{{ settingsStore.companyProfile?.company_name || t('app.name') }}</span>
        </q-toolbar-title>
        <div class="row items-center q-gutter-sm"> 
          <q-btn
              flat
              round
              :icon="$q.dark.isActive ? 'light_mode' : 'dark_mode'"
              @click="toggleDark"
              :aria-label="t('app.toggleDarkMode')"
            />
          <q-btn
              flat
              round
              icon="smart_toy"
              :color="assistantStore.isOpen ? 'primary' : undefined"
              @click="assistantStore.toggle()"
              :aria-label="t('assistant.title')"
            />
        </div>
        <div v-if="authStore.me" class="row items-center q-gutter-sm">
          <q-btn
            flat
            dense
            no-caps
            class="text-caption ec-username"
            :label="authStore.me.full_name"
            @click="goToProfile"
          />
          <q-btn flat dense round icon="logout" :aria-label="t('app.actions.logout')" @click="logout" />
        </div>
      </q-toolbar>
    </q-header>

    <q-drawer
      v-model="drawerOpen"
      side="left"
      bordered
      :width="drawerWidth"
      :mini="miniActive && !drawerExpanded"
      :mini-width="56"
      :overlay="isPhone"
      :behavior="isPhone ? 'mobile' : 'desktop'"
      class="ec-drawer"
    >
       <q-scroll-area class="fit">
        <q-list padding>
          <q-item-label v-if="!isFolded" header class="ec-drawer-header">{{ t('app.navigation') }}</q-item-label>

          <!-- Folded (mini) view: flat icons for every page so nested routes stay reachable -->
          <template v-if="isFolded">
            <q-item
              v-for="item in allNavItems"
              :key="item.to"
              clickable
              v-ripple
              :to="item.to"
              @click="onChildNavigate"
              dense
            >
              <q-item-section avatar>
                <q-icon :name="item.icon" class="text-primary" />
              </q-item-section>
              <q-tooltip anchor="center right" self="center left" :offset="[8, 0]">
                {{ t(item.labelKey) }}
              </q-tooltip>
            </q-item>
          </template>

          <!-- Expanded view: grouped navigation -->
          <template v-else>
            <!-- Home -->
            <q-item
              clickable
              v-ripple
              to="/"
              @click="onChildNavigate"
            >
              <q-item-section avatar>
                <q-icon name="home" class="text-primary" />
              </q-item-section>
              <q-item-section :class="$q.dark.isActive ? 'text-grey-3' : 'text-grey-8'">
                {{ t('app.nav.home') }}
              </q-item-section>
            </q-item>
            <q-separator />

            <!-- Grouped nav items -->
            <q-expansion-item
              v-for="group in navGroups"
              :key="group.key"
              :label="t(group.labelKey)"
              :icon="group.icon"
              v-model="expandedGroups[group.key]"
              :header-inset-level="0"
              content-inset-level="0.2"
              dense
            >
              <q-item
                v-for="child in group.children"
                :key="child.to"
                clickable
                v-ripple
                :to="child.to"
                @click="onChildNavigate"
              >
                <q-item-section avatar>
                  <q-icon :name="child.icon" class="text-primary" />
                </q-item-section>
                <q-item-section :class="$q.dark.isActive ? 'text-grey-3' : 'text-grey-8'">
                  {{ t(child.labelKey) }}
                </q-item-section>
              </q-item>
            </q-expansion-item>

            <!-- Standalone items -->
            <q-separator />
            <q-item
              clickable
              v-ripple
              to="/activity"
              @click="onChildNavigate"
            >
              <q-item-section avatar>
                <q-icon name="history" class="text-primary" />
              </q-item-section>
              <q-item-section :class="$q.dark.isActive ? 'text-grey-3' : 'text-grey-8'">
                {{ t('app.nav.activity') }}
              </q-item-section>
            </q-item>
            <q-item
              clickable
              v-ripple
              to="/reports"
              @click="onChildNavigate"
            >
              <q-item-section avatar>
                <q-icon name="summarize" class="text-primary" />
              </q-item-section>
              <q-item-section :class="$q.dark.isActive ? 'text-grey-3' : 'text-grey-8'">
                {{ t('app.nav.reports') }}
              </q-item-section>
            </q-item>
            <q-item
              v-if="authStore.canManageSettings"
              clickable
              v-ripple
              to="/settings"
              @click="onChildNavigate"
            >
              <q-item-section avatar>
                <q-icon name="tune" class="text-primary" />
              </q-item-section>
              <q-item-section :class="$q.dark.isActive ? 'text-grey-3' : 'text-grey-8'">
                {{ t('app.nav.settings') }}
              </q-item-section>
            </q-item>
          </template>
        </q-list>
      </q-scroll-area>
    </q-drawer>

    <q-drawer
      v-model="assistantStore.isOpen"
      side="right"
      bordered
      :width="380"
      :mini-width="0"
      :overlay="isPhone"
      :behavior="isPhone ? 'mobile' : 'desktop'"
      class="ec-assistant-drawer"
    >
      <AssistantDrawer />
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { ref, computed, reactive, onMounted, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import { useSettingsStore } from '../stores/settings'
import { useAssistantStore } from '../stores/assistantStore'
import { getUserLocalePreference, resolveAppLocale, setLocale } from '../i18n'
import AssistantDrawer from '../components/AssistantDrawer.vue'

const drawerOpen = ref(false)
const drawerExpanded = ref(false)
const forceMini = ref(false)
const authStore = useAuthStore()
const settingsStore = useSettingsStore()
const assistantStore = useAssistantStore()
const router = useRouter()
const $q = useQuasar()
const { t } = useI18n()

const headerStyle = computed(() => ({
  background: $q.dark.isActive ? 'var(--ec-header-bg-dark)' : 'var(--ec-header-bg-light)',
  color: $q.dark.isActive ? 'var(--ec-header-text-dark)' : 'var(--ec-header-text-light)',
}))

const headerLogoUrl = computed(() => {
  const profile = settingsStore.companyProfile || {}
  const preferred = $q.dark.isActive
    ? [profile.logo_light_small_url, profile.logo_light_wide_url]
    : [profile.logo_dark_small_url, profile.logo_dark_wide_url]

  return [
    ...preferred,
    profile.logo_url,
    profile.logo_dark_small_url,
    profile.logo_dark_wide_url,
    profile.logo_light_small_url,
    profile.logo_light_wide_url,
  ].map(value => String(value || '').trim()).find(Boolean) || ''
})

onMounted(() => {
  if (authStore.me) {
    settingsStore.fetchCompanyProfile().catch(() => {})
  }

  const userId = authStore.me?.id || null
  const preferred = userId
    ? resolveAppLocale(userId)
    : localStorage.getItem('sw_locale') || resolveAppLocale(null)
  setLocale(preferred)
})

watch(
  () => authStore.me?.id,
  (userId) => {
    if (!userId) return
    const perUserLocale = getUserLocalePreference(userId)
    if (!perUserLocale) return
    setLocale(perUserLocale)
  },
  { immediate: true },
)

async function logout() {
  authStore.logout()
  router.push('/login')
}

function goToProfile() {
  router.push('/profile')
}

function toggleDark() {
  $q.dark.toggle()
  try {
    localStorage.setItem('ec_dark_mode', $q.dark.isActive ? 'true' : 'false')
  } catch (e) {
    // ignore storage errors
  }
}

// ── Grouped navigation ──────────────────────────────────────────────────────

const NAV_STORAGE_KEY = 'ec_nav_expanded'

function loadExpandedState() {
  try {
    const raw = localStorage.getItem(NAV_STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function saveExpandedState(state) {
  try {
    localStorage.setItem(NAV_STORAGE_KEY, JSON.stringify(state))
  } catch {
    // ignore storage errors
  }
}

const navGroups = [
  {
    key: 'inventory',
    icon: 'inventory_2',
    labelKey: 'app.nav.group.inventory',
    children: [
      { icon: 'inventory_2', labelKey: 'app.nav.inventory', to: '/inventory' },
      { icon: 'print', labelKey: 'app.nav.labels', to: '/labels' },
      { icon: 'qr_code_scanner', labelKey: 'app.nav.scan', to: '/scan' },
    ],
  },
  {
    key: 'maintenance',
    icon: 'build_circle',
    labelKey: 'app.nav.group.maintenance',
    children: [
      { icon: 'build_circle', labelKey: 'app.nav.maintenance', to: '/maintenance' },
    ],
  },
  {
    key: 'operations',
    icon: 'work',
    labelKey: 'app.nav.group.operations',
    children: [
      { icon: 'work', labelKey: 'app.nav.jobs', to: '/jobs' },
      { icon: 'folder', labelKey: 'app.nav.projects', to: '/projects' },
      { icon: 'payments', labelKey: 'app.nav.finance', to: '/finance' },
      { icon: 'alt_route', labelKey: 'app.nav.routePlanner', to: '/route-planner' },
    ],
  },
  {
    key: 'people',
    icon: 'groups',
    labelKey: 'app.nav.group.people',
    children: [
      { icon: 'business', labelKey: 'app.nav.companies', to: '/companies' },
      { icon: 'person', labelKey: 'app.nav.persons', to: '/persons' },
      { icon: 'groups', labelKey: 'app.nav.crew', to: '/crew' },
      { icon: 'place', labelKey: 'app.nav.venues', to: '/venues' },
    ],
  },
]

const expandedGroups = reactive(loadExpandedState())

watch(expandedGroups, (val) => {
  saveExpandedState({ ...val })
}, { deep: true })

function onChildNavigate() {
  if (isPhone.value) {
    drawerOpen.value = false
  }
}

// ── Responsive mode helpers ─────────────────────────────────────────────────

const isPhone = computed(() => $q.screen.width < 600)
const isMiniMode = computed(() => $q.screen.width >= 600 && $q.screen.width < 1024)
const isDesktop = computed(() => $q.screen.width >= 1024)

const miniActive = computed(() => isMiniMode.value || forceMini.value)

const isFolded = computed(() => miniActive.value && !drawerExpanded.value)

const drawerWidth = computed(() => 280)

const allNavItems = computed(() => {
  const items = [
    { icon: 'home', labelKey: 'app.nav.home', to: '/' },
  ]
  navGroups.forEach((group) => {
    group.children.forEach((child) => {
      items.push({ icon: child.icon, labelKey: child.labelKey, to: child.to })
    })
  })
  items.push({ icon: 'history', labelKey: 'app.nav.activity', to: '/activity' })
  items.push({ icon: 'summarize', labelKey: 'app.nav.reports', to: '/reports' })
  if (authStore.canManageSettings) {
    items.push({ icon: 'tune', labelKey: 'app.nav.settings', to: '/settings' })
  }
  return items
})

function setDrawerForScreen() {
  if (forceMini.value) {
    drawerOpen.value = true
    drawerExpanded.value = false
    return
  }
  if (isDesktop.value) {
    drawerOpen.value = true
    drawerExpanded.value = false
  } else if (isMiniMode.value) {
    drawerOpen.value = true
    drawerExpanded.value = false
  } else {
    drawerOpen.value = false
    drawerExpanded.value = false
  }
}

setDrawerForScreen()
watch(() => $q.screen.width, () => setDrawerForScreen())

function handleMenuClick() {
  if (isPhone.value) {
    drawerOpen.value = !drawerOpen.value
    return
  }
  forceMini.value = !forceMini.value
  drawerOpen.value = true
  drawerExpanded.value = false
}
</script>
