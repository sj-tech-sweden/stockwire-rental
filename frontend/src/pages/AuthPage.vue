<template>
  <q-page class="q-pa-md ec-page">
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">{{ t('users.title') }}</div>
      <q-btn
        v-if="store.isAdmin"
        color="primary"
        icon="person_add"
        :label="t('users.createUser')"
        unelevated
        @click="openCreate"
      />
    </div>

    <q-table
      :rows="store.users"
      :columns="columns"
      row-key="id"
      :grid="compactGrid"
      :hide-header="compactGrid"
      flat
      bordered
      :loading="loading"
      :filter="filter"
      class="ec-card"
    >
      <template #top-right>
        <q-input v-model="filter" dense outlined :placeholder="t('customers.search')" clearable>
          <template #prepend><q-icon name="search" /></template>
        </q-input>
      </template>

      <template #body-cell-role="props">
        <q-td :props="props">
          <q-badge :color="roleColor(props.value)" :label="props.value" />
        </q-td>
      </template>

      <template #body-cell-is_active="props">
        <q-td :props="props">
          <q-icon
            :name="props.value ? 'check_circle' : 'cancel'"
            :color="props.value ? 'positive' : 'negative'"
            size="sm"
          />
        </q-td>
      </template>

      <template #body-cell-actions="props">
        <q-td :props="props" auto-width>
          <q-btn
            v-if="store.isAdmin"
            flat round dense icon="edit" color="primary"
            class="q-mr-xs"
            @click="openEdit(props.row)"
          />
          <q-btn
            v-if="store.isAdmin && props.row.id !== store.me?.id"
            flat round dense icon="delete" color="negative"
            @click="confirmDelete(props.row)"
          />
        </q-td>
      </template>

      <template #item="props">
        <div class="q-pa-xs col-12">
          <q-card flat bordered>
            <q-card-section class="q-pb-sm">
              <div class="row items-center justify-between">
                <div class="text-subtitle2">{{ props.row.full_name || props.row.email }}</div>
                <q-badge :color="roleColor(props.row.role)" :label="props.row.role" />
              </div>
              <div class="text-caption text-grey-7">{{ props.row.email }}</div>
            </q-card-section>
            <q-card-section class="q-pt-none q-pb-sm">
              <div class="text-caption">{{ t('settings.auth.status') }}: {{ props.row.is_active ? t('settings.auth.active') : t('settings.auth.inactive') }}</div>
            </q-card-section>
            <q-card-actions align="right">
              <q-btn v-if="store.isAdmin" flat dense icon="edit" color="primary" @click="openEdit(props.row)" />
              <q-btn
                v-if="store.isAdmin && props.row.id !== store.me?.id"
                flat dense icon="delete" color="negative"
                @click="confirmDelete(props.row)"
              />
            </q-card-actions>
          </q-card>
        </div>
      </template>
    </q-table>

    <!-- Create / Edit Dialog -->
    <q-dialog v-model="dialogOpen" persistent>
      <q-card style="min-width: 400px" class="ec-card">
        <q-card-section>
          <div class="text-h6">{{ editing ? t('users.editUser') : t('users.createUser') }}</div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-form @submit.prevent="saveUser" ref="formRef">
            <q-input
              v-model="form.full_name"
              :label="t('profile.fullName')"
              outlined
              dense
              class="q-mb-sm"
              :rules="[v => !!v || t('login.required')]"
            />
            <q-input
              v-model="form.email"
              :label="t('profile.email')"
              type="email"
              outlined
              dense
              class="q-mb-sm"
              :rules="[v => !!v || t('login.required')]"
            />
            <q-input
              v-model="form.password"
              :label="editing ? t('users.newPasswordOptional') : t('login.password')"
              type="password"
              outlined
              dense
              class="q-mb-sm"
              :rules="editing ? [] : [v => !!v || t('login.required')]"
            />
            <q-select
              v-model="form.role"
              :options="roleOptions"
              :label="t('users.roles')"
              outlined
              dense
              emit-value
              map-options
              class="q-mb-sm"
              :rules="[v => !!v || t('login.required')]"
            />
            <q-toggle v-model="form.is_active" :label="t('users.active')" color="primary" />

            <q-banner v-if="dialogError" class="bg-negative text-white q-mt-sm rounded-borders" dense>
              {{ dialogError }}
            </q-banner>
          </q-form>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="dialogOpen = false" />
          <q-btn
            color="primary"
            unelevated
            :label="editing ? t('app.actions.save') : t('users.create')"
            :loading="saving"
            @click="saveUser"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Delete confirmation -->
    <q-dialog v-model="deleteDialogOpen" persistent>
      <q-card class="ec-card">
        <q-card-section class="row items-center">
          <q-icon name="warning" color="negative" size="md" class="q-mr-md" />
          <span>{{ t('users.deleteUserConfirm') }}</span>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="deleteDialogOpen = false" />
          <q-btn color="negative" unelevated :label="t('users.delete')" :loading="saving" @click="doDelete" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useCompactGrid } from '../composables/useCompactGrid'

const store = useAuthStore()
const $q = useQuasar()
const { t } = useI18n()
const compactGrid = useCompactGrid(1024)

const loading = ref(false)
const filter = ref('')

const columns = [
  { name: 'full_name', label: t('users.name'), field: 'full_name', sortable: true, align: 'left' },
  { name: 'email', label: t('profile.email'), field: 'email', sortable: true, align: 'left' },
  { name: 'role', label: t('users.roles'), field: 'role', sortable: true, align: 'left' },
  { name: 'is_active', label: t('users.active'), field: 'is_active', sortable: true, align: 'center' },
  { name: 'created_at', label: t('customers.created'), field: 'created_at', sortable: true, align: 'left',
    format: v => new Date(v).toLocaleDateString() },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
]

const roleOptions = [
  { label: t('users.admin'), value: 'admin' },
  { label: t('users.manager'), value: 'manager' },
  { label: t('users.viewer'), value: 'viewer' },
]

function roleColor(role) {
  return { admin: 'negative', manager: 'warning', viewer: 'primary' }[role] ?? 'grey'
}

onMounted(async () => {
  loading.value = true
  try { await store.fetchUsers() } finally { loading.value = false }
})

// Dialog state
const dialogOpen = ref(false)
const editing = ref(null) // user object or null
const saving = ref(false)
const dialogError = ref('')
const formRef = ref(null)

const emptyForm = () => ({ full_name: '', email: '', password: '', role: 'viewer', is_active: true })
const form = ref(emptyForm())

function openCreate() {
  editing.value = null
  form.value = emptyForm()
  dialogError.value = ''
  dialogOpen.value = true
}

function openEdit(user) {
  editing.value = user
  form.value = { full_name: user.full_name, email: user.email, password: '', role: user.role, is_active: user.is_active }
  dialogError.value = ''
  dialogOpen.value = true
}

async function saveUser() {
  const valid = await formRef.value?.validate()
  if (!valid) return
  saving.value = true
  dialogError.value = ''
  try {
    const payload = { ...form.value }
    if (editing.value && !payload.password) delete payload.password
    if (editing.value) {
      await store.updateUser(editing.value.id, payload)
    } else {
      await store.createUser(payload)
    }
    dialogOpen.value = false
    $q.notify({ type: 'positive', message: editing.value ? t('customers.updated') : t('customers.createdNotice') })
  } catch (e) {
    dialogError.value = e?.response?.data?.detail || t('common.errorOccurred')
  } finally {
    saving.value = false
  }
}

// Delete
const deleteDialogOpen = ref(false)
const deleteTarget = ref(null)

function confirmDelete(user) {
  deleteTarget.value = user
  deleteDialogOpen.value = true
}

async function doDelete() {
  saving.value = true
  try {
    await store.deleteUser(deleteTarget.value.id)
    deleteDialogOpen.value = false
    $q.notify({ type: 'positive', message: t('customers.deleted') })
  } catch (e) {
    $q.notify({ type: 'negative', message: e?.response?.data?.detail || t('common.deleteFailed') })
  } finally {
    saving.value = false
  }
}
</script>

