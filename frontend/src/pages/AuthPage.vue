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

    <AuthUserDialog
      v-model="dialogOpen"
      :user="editing"
      @saved="onUserSaved"
    />
    <AuthDeleteUserDialog
      v-model="deleteDialogOpen"
      :user="deleteTarget"
      @deleted="onUserDeleted"
    />
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useI18n } from 'vue-i18n'
import AuthUserDialog from '../components/AuthUserDialog.vue'
import AuthDeleteUserDialog from '../components/AuthDeleteUserDialog.vue'
import { useCompactGrid } from '../composables/useCompactGrid'

const store = useAuthStore()
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

const dialogOpen = ref(false)
const editing = ref(null)

const deleteDialogOpen = ref(false)
const deleteTarget = ref(null)

function openCreate() {
  editing.value = null
  dialogOpen.value = true
}

function openEdit(user) {
  editing.value = user
  dialogOpen.value = true
}

function confirmDelete(user) {
  deleteTarget.value = user
  deleteDialogOpen.value = true
}

function onUserSaved() {
  dialogOpen.value = false
  editing.value = null
}

function onUserDeleted() {
  deleteDialogOpen.value = false
  deleteTarget.value = null
}
</script>

