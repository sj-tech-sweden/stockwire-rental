<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="emit('update:modelValue', $event)">
    <q-card style="min-width: 480px" class="ec-card">
      <q-card-section><div class="text-h6">{{ requirement ? t('crew.editRequirement') : t('crew.addRequirement') }}</div></q-card-section>
      <q-card-section class="q-pt-none">
        <div class="row q-col-gutter-sm">
          <div class="col-12 col-md-6">
            <q-select
              v-model="form.crew_role_id"
              :options="roleOptions"
              :label="t('crew.role')"
              outlined dense clearable emit-value map-options
              @update:model-value="onRoleChange"
            />
          </div>
          <div class="col-12 col-md-6">
            <q-input v-model="form.custom_role_name" :label="t('crew.customRoleName')" outlined dense :disable="!!form.crew_role_id" />
          </div>
          <div class="col-6 col-md-3">
            <q-input v-model.number="form.quantity" type="number" min="1" :label="t('crew.quantity')" outlined dense />
          </div>
          <div class="col-6 col-md-3">
            <q-input v-model.number="form.hourly_rate" type="number" min="0" step="0.01" :label="t('crew.hourlyRate')" outlined dense />
          </div>
          <div class="col-12">
            <div class="text-subtitle2 q-mb-sm">{{ t('crew.requiredSkills') }}</div>
            <SkillAutocomplete v-model="form.skill_ids" :label="t('crew.selectSkills')" />
          </div>
          <div class="col-12">
            <q-input v-model="form.notes" :label="t('crew.notes')" outlined dense type="textarea" />
          </div>
        </div>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="emit('update:modelValue', false)" />
        <q-btn color="primary" unelevated :label="t('app.actions.save')" :loading="saving" @click="save" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useCrewStore } from '../stores/crew'
import SkillAutocomplete from './SkillAutocomplete.vue'

const props = defineProps({
  modelValue: Boolean,
  jobId: { type: Number, required: true },
  requirement: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const $q = useQuasar()
const { t } = useI18n()
const crewStore = useCrewStore()
const saving = ref(false)

const form = ref(emptyForm())

function emptyForm() {
  return {
    crew_role_id: null,
    custom_role_name: '',
    quantity: 1,
    skill_ids: [],
    hourly_rate: null,
    notes: '',
  }
}

const roleOptions = ref([])

async function loadRoles() {
  await crewStore.fetchRoles()
  roleOptions.value = crewStore.roles.map(r => ({ label: r.name, value: r.id }))
}

function onRoleChange(roleId) {
  if (roleId) {
    const role = crewStore.roles.find(r => r.id === roleId)
    if (role) form.value.custom_role_name = ''
  }
}

async function save() {
  saving.value = true
  try {
    const payload = {
      job_id: props.jobId,
      crew_role_id: form.value.crew_role_id || null,
      custom_role_name: form.value.custom_role_name || null,
      quantity: form.value.quantity || 1,
      skill_ids: form.value.skill_ids.map(s => s.id || s.value),
      hourly_rate: form.value.hourly_rate || null,
      notes: form.value.notes || null,
    }

    if (props.requirement) {
      await crewStore.updateJobCrewRequirement(props.jobId, props.requirement.id, payload)
    } else {
      await crewStore.createJobCrewRequirement(props.jobId, payload)
    }

    emit('update:modelValue', false)
    emit('saved')
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('crew.failedSaveRequirement') })
  } finally {
    saving.value = false
  }
}

watch(() => props.modelValue, async (open) => {
  if (open) {
    await loadRoles()
    if (props.requirement) {
      form.value = {
        crew_role_id: props.requirement.crew_role_id || null,
        custom_role_name: props.requirement.custom_role_name || '',
        quantity: props.requirement.quantity || 1,
        skill_ids: (props.requirement.skills || []).map(s => ({ id: s.id, name: s.name, label: s.name, value: s.id })),
        hourly_rate: props.requirement.hourly_rate ?? null,
        notes: props.requirement.notes || '',
      }
    } else {
      form.value = emptyForm()
    }
  }
})
</script>
