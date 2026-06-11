<template>
  <q-dialog :model-value="modelValue" persistent @update:model-value="$emit('update:modelValue', $event)">
    <q-card style="width: 520px; max-width: 95vw" class="ec-card">
      <q-card-section><div class="text-h6">{{ category ? t('inventory.editCategory') : t('inventory.newCategory') }}</div></q-card-section>
      <q-card-section class="q-pt-none">
        <q-form ref="formRef" @submit.prevent="save">
          <q-input v-model="form.name" :label="t('users.name')" outlined dense class="q-mb-sm" :rules="[v => !!v || t('login.required')]" />
          <q-select v-model="form.parent_id" :options="parentCategoryOptions" :label="t('inventory.parentCategory')" outlined dense clearable emit-value map-options class="q-mb-sm" />
          <q-input v-model.number="form.sort_order" type="number" :label="t('inventory.sortOrder')" outlined dense class="q-mb-sm" />
          <q-toggle v-model="form.is_active" :label="t('settings.auth.active')" color="primary" />
          <q-banner v-if="error" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ error }}</q-banner>
        </q-form>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="$emit('update:modelValue', false)" />
        <q-btn color="primary" unelevated :label="category ? 'Save' : 'Create'" :loading="saving" @click="save" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQuasar } from 'quasar'
import { useInventoryStore } from '../stores/inventory'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  category: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const { t } = useI18n()
const $q = useQuasar()
const store = useInventoryStore()

const formRef = ref(null)
const saving = ref(false)
const error = ref('')

const emptyForm = () => ({ name: '', parent_id: null, sort_order: 0, is_active: true })
const form = ref(emptyForm())

watch(() => props.modelValue, (open) => {
  if (open) {
    error.value = ''
    if (props.category) {
      form.value = {
        name: props.category.name ?? '',
        parent_id: props.category.parent_id ?? null,
        sort_order: Number(props.category.sort_order ?? 0),
        is_active: !!props.category.is_active,
      }
    } else {
      form.value = emptyForm()
    }
  }
})

const parentCategoryOptions = computed(() => {
  const flat = []
  const walk = (nodes, prefix = '') => {
    for (const node of nodes || []) {
      const label = prefix ? `${prefix} / ${node.name}` : node.name
      flat.push({ label, value: node.id })
      walk(node.children || [], label)
    }
  }
  walk(store.categoryTree)
  return [{ label: 'Root', value: null }, ...flat]
})

async function save() {
  const valid = await formRef.value?.validate()
  if (!valid) return

  saving.value = true
  error.value = ''
  try {
    const payload = {
      name: form.value.name.trim(),
      parent_id: form.value.parent_id,
      sort_order: Number(form.value.sort_order || 0),
      is_active: !!form.value.is_active,
    }

    if (props.category) {
      await store.updateCategory(props.category.id, payload)
      $q.notify({ type: 'positive', message: 'Category updated' })
    } else {
      await store.createCategory(payload)
      $q.notify({ type: 'positive', message: 'Category created' })
    }

    emit('saved')
    emit('update:modelValue', false)
  } catch (err) {
    error.value = err?.response?.data?.detail || 'Failed to save category'
  } finally {
    saving.value = false
  }
}
</script>
