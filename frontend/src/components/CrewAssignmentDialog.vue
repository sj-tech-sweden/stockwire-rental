<template>
  <q-dialog :model-value="modelValue" persistent :maximized="isPhone" @update:model-value="emit('update:modelValue', $event)">
    <q-card :style="isPhone ? '' : 'min-width: 480px; max-width: 95vw'" class="ec-card">
      <q-card-section>
        <div class="text-h6">{{ t('crew.assignMember') }}</div>
        <div v-if="requirement" class="text-caption text-grey-7">
          {{ roleName }} · {{ t('crew.slotsRemaining', { count: requirement.quantity - requirement.quantity_assigned }) }}
        </div>
      </q-card-section>
      <q-card-section class="q-pt-none">
        <div v-if="!requirements.length" class="text-caption text-grey-7">{{ t('crew.noRequirements') }}</div>
        <div v-else>
          <div class="q-mb-sm">
            <q-select
              v-model="selectedRequirementId"
              :options="requirementOptions"
              :label="t('crew.role')"
              outlined dense emit-value map-options
            />
          </div>
          <div v-if="selectedRequirementId" class="q-mb-sm">
            <div class="text-subtitle2 q-mb-sm">{{ t('crew.suggestedMembers') }}</div>
            <div v-if="loadingSuggestions" class="text-caption text-grey-7">{{ t('common.loading') }}...</div>
            <div v-else-if="!suggestions.length" class="text-caption text-grey-7">{{ t('crew.noSuggestions') }}</div>
            <q-list v-else bordered separator class="rounded-borders">
              <q-item v-for="s in suggestions" :key="s.crew_member_id" clickable @click="selectMember(s)">
                <q-item-section>
                  <q-item-label :class="{ 'text-bold': s.match_score >= 0.8 }">{{ s.name }}</q-item-label>
                  <q-item-label caption>
                    <q-badge v-if="s.source === 'internal'" color="blue" :label="t('crew.internal')" class="q-mr-xs" />
                    <q-badge v-else-if="s.source === 'supplier'" color="orange" :label="t('crew.external')" class="q-mr-xs" />
                    <q-badge v-if="s.hourly_rate" color="grey" :label="`${s.hourly_rate}/h`" class="q-mr-xs" />
                    <span class="text-positive" v-if="s.matching_skills.length">{{ s.matching_skills.join(', ') }}</span>
                    <span class="text-negative q-ml-xs" v-if="s.missing_skills.length">- {{ s.missing_skills.join(', ') }}</span>
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-badge :color="s.match_score >= 0.8 ? 'positive' : s.match_score >= 0.5 ? 'warning' : 'grey'" :label="`${Math.round(s.match_score * 100)}%`" />
                </q-item-section>
              </q-item>
            </q-list>
          </div>
          <div class="text-subtitle2 q-mb-sm q-mt-md">{{ t('crew.orSelectMember') }}</div>
          <q-select
            v-model="selectedMemberId"
            :options="memberOptions"
            :label="t('crew.member')"
            outlined dense emit-value map-options use-input fill-input input-debounce="0"
            @filter="filterMembers"
          />
        </div>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="emit('update:modelValue', false)" />
        <q-btn color="primary" unelevated :label="t('crew.assign')" :loading="saving" :disable="!selectedMemberId || !selectedRequirementId" @click="assign" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useCrewStore } from '../stores/crew'

const props = defineProps({
  modelValue: Boolean,
  jobId: { type: Number, required: true },
  requirementId: { type: Number, default: null },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const $q = useQuasar()
const { t } = useI18n()
const crewStore = useCrewStore()
const saving = ref(false)
const isPhone = computed(() => $q.screen.lt.md)

const requirements = ref([])
const suggestions = ref([])
const allMembers = ref([])
const loadingSuggestions = ref(false)
const selectedRequirementId = ref(null)
const selectedMemberId = ref(null)
const memberSearch = ref('')

const requirementOptions = computed(() => {
  return requirements.value
    .filter(r => r.quantity_assigned < r.quantity)
    .map(r => ({
      label: `${r.crew_role_name || r.custom_role_name || t('crew.unknownRole')} (${r.quantity - r.quantity_assigned} slots)`,
      value: r.id,
    }))
})

const requirement = computed(() => requirements.value.find(r => r.id === selectedRequirementId.value))

const roleName = computed(() => {
  if (!requirement.value) return ''
  return requirement.value.crew_role_name || requirement.value.custom_role_name || t('crew.unknownRole')
})

const memberOptions = computed(() => {
  const term = memberSearch.value.toLowerCase()
  return allMembers.value
    .filter(m => m.is_active && (!term || m.name.toLowerCase().includes(term)))
    .map(m => ({ label: m.name, value: m.id }))
})

function filterMembers(val, update) {
  memberSearch.value = val
  update(() => {})
}

async function selectMember(suggestion) {
  selectedMemberId.value = suggestion.crew_member_id
}

async function loadSuggestions() {
  if (!selectedRequirementId.value) {
    suggestions.value = []
    return
  }
  loadingSuggestions.value = true
  try {
    suggestions.value = await crewStore.fetchCrewSuggestions(props.jobId, selectedRequirementId.value)
  } catch {
    suggestions.value = []
  } finally {
    loadingSuggestions.value = false
  }
}

async function assign() {
  if (!selectedMemberId.value || !selectedRequirementId.value) return
  saving.value = true
  try {
    await crewStore.createCrewAssignment({
      job_crew_requirement_id: selectedRequirementId.value,
      crew_member_id: selectedMemberId.value,
    })
    emit('update:modelValue', false)
    emit('saved')
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('crew.failedAssign') })
  } finally {
    saving.value = false
  }
}

watch(() => props.modelValue, async (open) => {
  if (open) {
    selectedRequirementId.value = null
    selectedMemberId.value = null
    suggestions.value = []
    memberSearch.value = ''

    try {
      requirements.value = await crewStore.fetchJobCrewRequirements(props.jobId)
    } catch {
      requirements.value = []
    }

    if (props.requirementId) {
      selectedRequirementId.value = props.requirementId
    }

    if (!crewStore.members.length) {
      await crewStore.fetchMembers({ active_only: true })
    }
    allMembers.value = crewStore.members
  }
})

watch(selectedRequirementId, () => {
  loadSuggestions()
})
</script>
