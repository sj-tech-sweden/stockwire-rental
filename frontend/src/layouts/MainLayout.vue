<template>
  <q-layout view="hHh lpR fFf" class="ec-layout">
    <q-header elevated class="ec-header" :style="headerStyle" ref="headerRef">
      <q-toolbar>
        <q-btn
          flat
          dense
          round
          icon="menu"
          :aria-label="t('app.menu')"
          @click="handleMenuClick"
          :style="{ color: headerStyle.color }"
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
              :style="{ color: headerStyle.color }"
              :aria-label="t('app.toggleDarkMode')"
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
            :style="{ color: headerStyle.color }"
          />
          <q-btn flat dense round icon="logout" :aria-label="t('app.actions.logout')" @click="logout" :style="{ color: headerStyle.color }" />
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
          <q-item-label header class="ec-drawer-header">{{ t('app.navigation') }}</q-item-label>

          <template v-for="(item, idx) in menuList" :key="idx">
            <q-item
              clickable
              v-ripple
              :to="item.to"
              @click="onNavigate(item)">
              <q-item-section avatar>
                <q-icon :name="item.icon" class="text-primary" />
              </q-item-section>
              <q-item-section :class="$q.dark.isActive ? 'text-grey-3' : 'text-grey-8'">
                {{ item.label }}
              </q-item-section>
            </q-item>
            <q-separator v-if="item.separator" :key="'sep-'+idx" />
          </template>
        </q-list>
      </q-scroll-area>
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick, onUnmounted } from 'vue'
import { useQuasar } from 'quasar'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import { useSettingsStore } from '../stores/settings'
import { resolveAppLocale, setLocale } from '../i18n'

const drawerOpen = ref(false)
// In "mini" screens we keep drawer collapsed by default but allow
// a temporary expansion via the menu button (drawerExpanded).
const drawerExpanded = ref(false)
// allow forcing mini mode even on wide screens
const forceMini = ref(false)
const authStore = useAuthStore()
const settingsStore = useSettingsStore()
const router = useRouter()
const $q = useQuasar()
const { t } = useI18n()

const headerRef = ref(null)
const headerStyle = computed(() => {
  const dark = $q.dark.isActive
  // Use explicit colors to avoid depending on other CSS variables that may be
  // overridden by Quasar. Also expose CSS vars so injected/apply-order rules
  // can read them with high specificity.
  const bg = dark ? '#182228' : '#f3f9f3'
  const text = dark ? '#E9F1EE' : '#0f1720'
  return {
    backgroundColor: bg,
    color: text,
    '--ec-header-bg': bg,
    '--ec-header-text': text
  }
})

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

function applyInlineHeaderStyles() {
  const comp = headerRef.value
  const el = comp && comp.$el ? comp.$el : comp
  if (!el || !el.style) return
  const dark = $q.dark.isActive
  const bg = dark ? '#182228' : '#f3f9f3'
  const text = dark ? '#E9F1EE' : '#0f1720'
  // set as important so runtime rules can't easily override
  el.style.setProperty('--ec-header-bg', bg, 'important')
  el.style.setProperty('--ec-header-text', text, 'important')
  el.style.setProperty('background-color', bg, 'important')
  el.style.setProperty('color', text, 'important')
}

onMounted(() => {
  applyInlineHeaderStyles()
  watch(() => $q.dark.isActive, async () => {
    await nextTick()
    applyInlineHeaderStyles()
  })

  // Observe DOM changes so we can re-apply inline styles if Quasar replaces
  // the header element during theme toggles or route changes.
  const domObserver = new MutationObserver((mutations) => {
    for (const m of mutations) {
      if (m.type === 'attributes' && m.attributeName === 'class') {
        applyInlineHeaderStyles()
        return
      }
      if (m.type === 'childList' && m.addedNodes.length) {
        applyInlineHeaderStyles()
        return
      }
    }
  })
  domObserver.observe(document.body, { attributes: true, attributeFilter: ['class'], childList: true, subtree: true })
  // cleanup on unmount
  onUnmounted(() => domObserver.disconnect())

  if (authStore.me) {
    settingsStore.fetchCompanyProfile().catch(() => {
      // Header logo/name is optional, ignore fetch failures.
    })
  }

  const preferred = resolveAppLocale(authStore.me?.id || null)
  setLocale(preferred)
})

async function logout() {
  authStore.logout()
  router.push('/login')
}

function goToProfile() {
  router.push('/profile')
}

function toggleDark() {
  // toggle and persist user's explicit choice
  $q.dark.toggle()
  try {
    localStorage.setItem('ec_dark_mode', $q.dark.isActive ? 'true' : 'false')
  } catch (e) {
    // ignore storage errors
  }
}

const baseMenuList = [
  { icon: 'home', key: 'app.nav.home', to: '/', separator: true },
  { icon: 'inventory_2', key: 'app.nav.inventory', to: '/inventory', separator: false },
  { icon: 'print', key: 'app.nav.labels', to: '/labels', separator: false },
  { icon: 'qr_code_scanner', key: 'app.nav.scan', to: '/scan', separator: false },
  { icon: 'history', key: 'app.nav.activity', to: '/activity', separator: false },
  { icon: 'work', key: 'app.nav.jobs', to: '/jobs', separator: false },
  { icon: 'business', key: 'app.nav.customers', to: '/customers', separator: false },
  { icon: 'place', key: 'app.nav.venues', to: '/venues', separator: false },
  { icon: 'payments', key: 'app.nav.finance', to: '/finance', separator: false }
]

const menuList = computed(() => {
  const items = baseMenuList.map(item => ({ ...item, label: t(item.key) }))
  if (authStore.canManageSettings) {
    return [...items, { icon: 'tune', label: t('app.nav.settings'), to: '/settings', separator: false }]
  }
  return items
})

// Responsive mode helpers
const isPhone = computed(() => $q.screen.width < 600)
const isMiniMode = computed(() => $q.screen.width >= 600 && $q.screen.width < 1024)
const isDesktop = computed(() => $q.screen.width >= 1024)

const miniActive = computed(() => isMiniMode.value || forceMini.value)

const drawerWidth = computed(() => 220)

// no separate header mini toggle; hamburger controls mini/full on medium+ screens

// Initialize drawer state based on screen size and keep it updated when
// breakpoints change.
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
    // keep open so mini bar is visible; collapsed by default
    drawerOpen.value = true
    drawerExpanded.value = false
  } else {
    // phone / very small: closed by default
    drawerOpen.value = false
    drawerExpanded.value = false
  }
}

// call once and watch for changes
setDrawerForScreen()
watch(() => $q.screen.width, () => setDrawerForScreen())

function handleMenuClick() {
  if (isPhone.value) {
    drawerOpen.value = !drawerOpen.value
    return
  }
  // medium and up: toggle between mini and full
  forceMini.value = !forceMini.value
  drawerOpen.value = true
  drawerExpanded.value = false
}

function onNavigate(item) {
  // only auto-close drawer on phones
  if (isPhone.value) {
    drawerOpen.value = false
  }
  if (item.to) router.push(item.to)
}
</script>
