<template>
  <div>
    <q-select
      v-model="selected"
      :options="filteredOptions"
      :label="label || t('crew.skills')"
      outlined
      dense
      multiple
      use-chips
      use-input
      map-options
      clearable
      input-debounce="300"
      :loading="loading"
      @filter="onFilter"
      @update:model-value="onUpdate"
    >
      <template #option="scope">
        <q-item v-bind="scope.itemProps">
          <q-item-section>
            <q-item-label>{{ scope.opt.label }}</q-item-label>
            <q-item-label v-if="scope.opt.category" caption>{{ scope.opt.category }}</q-item-label>
          </q-item-section>
        </q-item>
      </template>
      <template #no-option>
        <q-item>
          <q-item-section class="text-grey">
            <q-item-label v-if="filterText">{{ t('crew.noSkillsFound') }}</q-item-label>
            <q-item-label v-else>{{ t('crew.typeToSearch') }}</q-item-label>
          </q-item-section>
        </q-item>
      </template>
      <template #after>
        <q-btn flat dense icon="add" color="primary" @click="showCreateDialog = true" :title="t('crew.createSkill')" />
      </template>
    </q-select>

    <q-dialog v-model="showCreateDialog" persistent>
      <q-card style="min-width: 320px" class="ec-card">
        <q-card-section>
          <div class="text-h6">{{ t('crew.createSkill') }}</div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-input v-model="newSkillName" :label="t('crew.skillName')" outlined dense class="q-mb-sm" autofocus @keyup.enter="createSkill" :rules="[v => !!v || t('common.required')]" />
          <q-input v-model="newSkillCategory" :label="t('crew.skillCategory')" outlined dense :placeholder="t('crew.skillCategoryPlaceholder')" @keyup.enter="createSkill" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="cancelCreate" />
          <q-btn color="primary" unelevated :label="t('app.actions.create')" :loading="creating" @click="createSkill" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../boot/axios'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  label: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue'])

const { t } = useI18n()

const selected = ref([...props.modelValue])
const allOptions = ref([])
const filteredOptions = ref([])
const loading = ref(false)
const filterText = ref('')
const showCreateDialog = ref(false)
const newSkillName = ref('')
const newSkillCategory = ref('')
const creating = ref(false)

const selectedIds = computed(() => selected.value.map(s => typeof s === 'object' ? s.id : s))

watch(() => props.modelValue, (val) => {
  selected.value = [...val]
})

async function fetchSkills(query = '') {
  loading.value = true
  try {
    const params = query ? { q: query } : {}
    const { data } = await api.get('/api/v1/crew/skills', { params })
    allOptions.value = data.map(s => ({ label: s.name, value: s.id, id: s.id, name: s.name, category: s.category }))
    filteredOptions.value = allOptions.value.filter(o => !selectedIds.value.includes(o.id))
  } catch {
    allOptions.value = []
    filteredOptions.value = []
  } finally {
    loading.value = false
  }
}

function onFilter(val, update) {
  filterText.value = val
  update(() => {
    const term = String(val || '').toLowerCase()
    filteredOptions.value = allOptions.value
      .filter(o => !selectedIds.value.includes(o.id))
      .filter(o => !term || o.name.toLowerCase().includes(term) || (o.category || '').toLowerCase().includes(term))
  })
  if (val && val.length >= 2) {
    fetchSkills(val)
  }
}

function onUpdate(val) {
  emit('update:modelValue', val || [])
}

async function createSkill() {
  if (!newSkillName.value.trim()) return
  creating.value = true
  try {
    const { data } = await api.post('/api/v1/crew/skills', {
      name: newSkillName.value.trim(),
      category: newSkillCategory.value.trim() || null,
    })
    const newOpt = { label: data.name, value: data.id, id: data.id, name: data.name, category: data.category }
    allOptions.value = [newOpt, ...allOptions.value.filter(o => o.id !== data.id)]
    selected.value = [...selected.value, newOpt]
    emit('update:modelValue', [...selected.value])
    cancelCreate()
  } catch (err) {
    // Error handled by parent
    throw err
  } finally {
    creating.value = false
  }
}

function cancelCreate() {
  showCreateDialog.value = false
  newSkillName.value = ''
  newSkillCategory.value = ''
}

fetchSkills()
</script>
