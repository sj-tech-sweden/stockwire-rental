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
          <q-separator class="q-my-sm" />
          <div class="text-subtitle2 q-mb-sm">{{ t('inventory.translations') }}</div>
          <div class="row q-col-gutter-sm">
            <div v-for="locale in SUPPORTED_LOCALES" :key="locale" class="col-6">
              <q-input v-model="translations[locale]" :label="localeNames[locale]" outlined dense class="q-mb-sm" />
            </div>
          </div>
          <q-banner v-if="error" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ error }}</q-banner>
        </q-form>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('app.actions.cancel')" @click="$emit('update:modelValue', false)" />
        <q-btn color="primary" unelevated :label="category ? t('app.actions.save') : t('app.actions.create')" :loading="saving" @click="save" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQuasar } from 'quasar'
import { useInventoryStore } from '../stores/inventory'
import { translateCategory } from '../utils/translate-helpers'
import { SUPPORTED_LOCALES } from '../i18n'

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
const translations = ref({})

const localeNames = {
  en: 'English',
  sv: 'Svenska',
}

const emptyForm = () => ({ name: '', parent_id: null, sort_order: 0, is_active: true })
const form = ref(emptyForm())

watch(() => props.modelValue, async (open) => {
  if (open) {
    error.value = ''
    translations.value = Object.fromEntries(SUPPORTED_LOCALES.map(l => [l, '']))
    if (props.category) {
      form.value = {
        name: props.category.name ?? '',
        parent_id: props.category.parent_id ?? null,
        sort_order: Number(props.category.sort_order ?? 0),
        is_active: !!props.category.is_active,
      }
      try {
        const categoryTranslations = await store.fetchCategoryTranslations(props.category.id)
        for (const tr of categoryTranslations) {
          if (SUPPORTED_LOCALES.includes(tr.locale)) {
            translations.value[tr.locale] = tr.name
          }
        }
      } catch {
        // ignore
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
      const translatedName = translateCategory(node.name, t)
      const label = prefix ? `${prefix} / ${translatedName}` : translatedName
      flat.push({ label, value: node.id })
      walk(node.children || [], label)
    }
  }
  walk(store.categoryTree)
  return [{ label: t('inventory.root'), value: null }, ...flat]
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

    let categoryId
    if (props.category) {
      await store.updateCategory(props.category.id, payload)
      categoryId = props.category.id
      $q.notify({ type: 'positive', message: t('inventory.categoryUpdated') })
    } else {
      const saved = await store.createCategory(payload)
      categoryId = saved.id
      $q.notify({ type: 'positive', message: t('inventory.categoryCreated') })
    }

    if (categoryId) {
      await saveTranslations(categoryId)
    }

    emit('saved')
    emit('update:modelValue', false)
  } catch (err) {
    error.value = err?.response?.data?.detail || t('inventory.failedSaveCategory')
  } finally {
    saving.value = false
  }
}

async function saveTranslations(categoryId) {
  for (const locale of SUPPORTED_LOCALES) {
    const name = translations.value[locale]?.trim()
    if (name) {
      try {
        await store.saveCategoryTranslation(categoryId, { locale, name })
      } catch {
        // ignore individual translation errors
      }
    }
  }
}
</script>
