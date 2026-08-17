<template>
  <div>
    <div class="text-subtitle1 q-mb-sm">{{ t('crew.mySkills') }}</div>
    <div v-if="loading" class="text-caption text-grey-7">
      <q-spinner size="16px" class="q-mr-sm" />{{ t('app.actions.loading') }}
    </div>
    <div v-else-if="noProfile" class="text-caption text-grey-7">
      {{ t('crew.memberNotFound') }}
    </div>
    <div v-else>
      <div v-if="mySkills.length" class="row q-gutter-xs q-mb-sm">
        <q-badge
          v-for="skill in mySkills"
          :key="skill.id"
          color="teal"
          class="q-pa-xs"
        >
          {{ skill.name }}
          <span v-if="skill.category" class="text-caption q-ml-xs">({{ skill.category }})</span>
          <q-btn flat dense icon="close" size="xs" class="q-ml-xs" @click="removeSkill(skill)" />
        </q-badge>
      </div>
      <div v-else class="text-caption text-grey-7 q-mb-sm">{{ t('crew.noSkills') }}</div>
      <q-select
        v-model="selectedSkill"
        :options="availableSkills"
        :label="t('crew.addSkill')"
        outlined
        dense
        emit-value
        map-options
        use-input
        input-debounce="300"
        clearable
        @filter="filterSkills"
        @update:model-value="addSkill"
      >
        <template #no-option>
          <q-item>
            <q-item-section class="text-grey">{{ t('crew.noMatchingSkills') }}</q-item-section>
          </q-item>
        </template>
      </q-select>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useCrewStore } from '../stores/crew'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue'])

const $q = useQuasar()
const { t } = useI18n()
const crewStore = useCrewStore()

const loading = ref(false)
const mySkills = ref([])
const allSkills = ref([])
const selectedSkill = ref(null)
const filterText = ref('')
const noProfile = ref(false)

const availableSkills = computed(() => {
  const myIds = new Set(mySkills.value.map(s => s.id))
  const term = filterText.value.toLowerCase()
  return allSkills.value
    .filter(s => !myIds.has(s.id))
    .filter(s => !term || s.name.toLowerCase().includes(term) || (s.category || '').toLowerCase().includes(term))
    .map(s => ({ label: s.name + (s.category ? ` (${s.category})` : ''), value: s.id }))
})

function filterSkills(val, update) {
  filterText.value = val
  update()
}

async function loadSkills() {
  loading.value = true
  try {
    mySkills.value = await crewStore.fetchMySkills()
    allSkills.value = await crewStore.fetchSkills()
  } catch (err) {
    if (err?.response?.status === 404) {
      noProfile.value = true
    } else {
      $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('crew.failedLoadSkills') })
    }
  } finally {
    loading.value = false
  }
}

async function addSkill(skillId) {
  if (!skillId) return
  try {
    mySkills.value = await crewStore.addMySkill(skillId)
    selectedSkill.value = null
    emit('update:modelValue', mySkills.value)
    $q.notify({ type: 'positive', message: t('crew.skillAdded') })
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('crew.failedAddSkill') })
  }
}

async function removeSkill(skill) {
  try {
    mySkills.value = await crewStore.removeMySkill(skill.id)
    emit('update:modelValue', mySkills.value)
    $q.notify({ type: 'positive', message: t('crew.skillRemoved') })
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('crew.failedRemoveSkill') })
  }
}

onMounted(loadSkills)
</script>
