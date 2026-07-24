<template>
  <q-page class="q-pa-md ec-page">
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">{{ t('app.nav.crew') }}</div>
      <q-btn v-if="authStore.canEdit" color="primary" :icon="activeTab === 'roles' ? 'add' : 'person_add'" :label="activeTab === 'roles' ? t('crew.newRole') : t('crew.newMember')" unelevated @click="openCreate" />
    </div>

    <q-tabs v-model="activeTab" inline-label align="left" class="q-mb-md" @update:model-value="onTabChange">
      <q-tab name="roles" :label="t('crew.roles')" />
      <q-tab name="members" :label="t('crew.members')" />
    </q-tabs>

    <div v-if="activeTab === 'roles'">
      <q-table
        :rows="crewStore.roles"
        :columns="roleColumns"
        row-key="id"
        flat bordered
        :loading="crewStore.loadingRoles"
        :filter="roleSearch"
        :pagination="{ rowsPerPage: 50 }"
        class="ec-card"
      >
        <template #top-right>
          <q-input v-model="roleSearch" dense outlined clearable :placeholder="t('crew.searchRoles')">
            <template #prepend><q-icon name="search" /></template>
          </q-input>
        </template>

        <template #body-cell-actions="props">
          <q-td v-if="authStore.canEdit" :props="props" auto-width>
            <q-btn flat round dense icon="edit" color="primary" class="q-mr-xs" @click="openEditRole(props.row)" />
            <q-btn flat round dense icon="delete" color="negative" @click="confirmDeleteRole(props.row)" />
          </q-td>
        </template>

        <template #body-cell-is_default="props">
          <q-td :props="props" auto-width>
            <q-badge v-if="props.row.is_default" color="grey" :label="t('crew.default')" />
          </q-td>
        </template>
      </q-table>
    </div>

    <div v-if="activeTab === 'members'">
      <q-table
        :rows="crewStore.members"
        :columns="memberColumns"
        row-key="id"
        flat bordered
        :loading="crewStore.loadingMembers"
        :filter="memberSearch"
        :pagination="{ rowsPerPage: 50 }"
        class="ec-card"
      >
        <template #top-right>
          <q-input v-model="memberSearch" dense outlined clearable :placeholder="t('crew.searchMembers')">
            <template #prepend><q-icon name="search" /></template>
          </q-input>
        </template>

        <template #body-cell-actions="props">
          <q-td v-if="authStore.canEdit" :props="props" auto-width>
            <q-btn flat round dense icon="edit" color="primary" class="q-mr-xs" @click="openEditMember(props.row)" />
            <q-btn flat round dense icon="delete" color="negative" @click="confirmDeleteMember(props.row)" />
          </q-td>
        </template>

        <template #body-cell-source="props">
          <q-td :props="props" auto-width>
            <q-badge v-if="props.row.user_id" color="blue" :label="t('crew.internal')" />
            <q-badge v-else-if="props.row.supplier_id" color="orange" :label="t('crew.external')" />
            <q-badge v-else color="grey" :label="t('crew.standalone')" />
          </q-td>
        </template>

        <template #body-cell-skills="props">
          <q-td :props="props">
            <q-badge v-for="skill in (props.row.skills || []).slice(0, 3)" :key="skill" color="teal" class="q-mr-xs" :label="skill" />
            <span v-if="(props.row.skills || []).length > 3" class="text-caption text-grey-7">+{{ props.row.skills.length - 3 }}</span>
          </q-td>
        </template>

        <template #body-cell-is_active="props">
          <q-td :props="props" auto-width>
            <q-icon :name="props.row.is_active ? 'check_circle' : 'cancel'" :color="props.row.is_active ? 'positive' : 'negative'" />
          </q-td>
        </template>
      </q-table>
    </div>

    <q-dialog v-model="roleDialog" persistent>
      <q-card style="min-width: 400px" class="ec-card">
        <q-card-section><div class="text-h6">{{ editingRole ? t('crew.editRole') : t('crew.newRole') }}</div></q-card-section>
        <q-card-section class="q-pt-none">
          <q-input v-model="roleForm.name" :label="t('crew.roleName')" outlined dense class="q-mb-sm" :rules="[v => !!v || t('login.required')]" />
          <q-input v-model="roleForm.description" :label="t('crew.description')" outlined dense class="q-mb-sm" type="textarea" />
          <q-toggle v-model="roleForm.is_default" :label="t('crew.default')" color="primary" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="roleDialog = false" />
          <q-btn color="primary" unelevated :label="t('app.actions.save')" :loading="savingRole" @click="saveRole" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="memberDialog" persistent :maximized="isPhone">
      <q-card :style="isPhone ? 'width: 100vw; max-width: 100vw; height: 100vh' : 'min-width: 560px; max-width: 95vw'" class="ec-card">
        <q-card-section><div class="text-h6">{{ editingMember ? t('crew.editMember') : t('crew.newMember') }}</div></q-card-section>
        <q-card-section class="q-pt-none" :style="isPhone ? 'max-height: calc(100vh - 140px); overflow: auto;' : ''">
          <div class="row q-col-gutter-sm">
            <div class="col-12 col-md-8"><q-input v-model="memberForm.name" :label="t('crew.memberName')" outlined dense :rules="[v => !!v || t('login.required')]" /></div>
            <div class="col-12 col-md-4"><q-input v-model="memberForm.phone" :label="t('customers.phone')" outlined dense /></div>
            <div class="col-12 col-md-6"><q-input v-model="memberForm.email" :label="t('profile.email')" outlined dense /></div>
            <div class="col-12 col-md-6">
              <q-select v-model="memberForm.user_id" :options="filteredUserOptions" :label="t('crew.linkUser')" outlined dense clearable emit-value map-options use-input @filter="filterUsers" />
            </div>
            <div class="col-12 col-md-6">
              <q-select v-model="memberForm.supplier_id" :options="filteredSupplierOptions" :label="t('crew.linkSupplier')" outlined dense clearable emit-value map-options use-input @filter="filterSuppliers" />
            </div>
            <div class="col-6 col-md-3"><q-input v-model.number="memberForm.hourly_rate" type="number" min="0" step="0.01" :label="t('crew.hourlyRate')" outlined dense /></div>
            <div class="col-6 col-md-3"><q-input v-model.number="memberForm.daily_rate" type="number" min="0" step="0.01" :label="t('crew.dailyRate')" outlined dense /></div>
            <div class="col-12"><q-input v-model="memberForm.notes" :label="t('crew.notes')" outlined dense type="textarea" /></div>
            <div class="col-12">
              <div class="text-subtitle2 q-mb-sm">{{ t('crew.preferredRoles') }}</div>
              <q-select
                v-model="memberForm.preferred_role_ids"
                :options="roleOptions"
                multiple
                emit-value
                map-options
                outlined
                dense
                clearable
                use-chips
                class="q-mb-sm"
              />
            </div>
            <div class="col-12">
              <div class="text-subtitle2 q-mb-sm">{{ t('crew.skills') }}</div>
              <div class="row q-col-gutter-xs items-center q-mb-sm">
                <div class="col"><q-input v-model="newSkill" dense outlined :placeholder="t('crew.addSkill')" @keyup.enter="addSkill" /></div>
                <div class="col-auto"><q-btn flat dense icon="add" color="primary" @click="addSkill" /></div>
              </div>
              <div v-if="memberForm.skills.length" class="row q-gutter-xs">
                <q-badge v-for="(skill, idx) in memberForm.skills" :key="idx" color="teal" class="q-pa-xs">
                  {{ skill }}
                  <q-btn flat dense icon="close" size="xs" class="q-ml-xs" @click="memberForm.skills.splice(idx, 1)" />
                </q-badge>
              </div>
            </div>
            <div class="col-12">
              <div class="text-subtitle2 q-mb-sm">{{ t('crew.certifications') }}</div>
              <div class="row q-col-gutter-xs items-center q-mb-sm">
                <div class="col"><q-input v-model="newCert" dense outlined :placeholder="t('crew.addCertification')" @keyup.enter="addCertification" /></div>
                <div class="col-auto"><q-btn flat dense icon="add" color="primary" @click="addCertification" /></div>
              </div>
              <div v-if="memberForm.certifications.length" class="q-gutter-xs">
                <q-badge v-for="(cert, idx) in memberForm.certifications" :key="idx" color="blue" class="q-pa-xs">
                  {{ cert.certification }}
                  <q-btn flat dense icon="close" size="xs" class="q-ml-xs" @click="memberForm.certifications.splice(idx, 1)" />
                </q-badge>
              </div>
            </div>
            <div class="col-12"><q-toggle v-model="memberForm.is_active" :label="t('crew.active')" color="primary" /></div>
          </div>
        </q-card-section>
        <q-card-actions :align="isPhone ? 'stretch' : 'right'" :class="isPhone ? 'q-pa-md bg-grey-2' : ''">
          <q-btn flat :class="isPhone ? 'full-width q-mb-sm' : ''" :label="t('app.actions.cancel')" @click="memberDialog = false" />
          <q-btn color="primary" unelevated :class="isPhone ? 'full-width' : ''" :label="t('app.actions.save')" :loading="savingMember" @click="saveMember" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useCrewStore } from '../stores/crew'
import { useCustomersStore } from '../stores/customers'
import { useUsersStore } from '../stores/users'
import { useAuthStore } from '../stores/auth'

const $q = useQuasar()
const { t } = useI18n()
const crewStore = useCrewStore()
const customersStore = useCustomersStore()
const usersStore = useUsersStore()
const authStore = useAuthStore()

const isPhone = computed(() => $q.screen.lt.md)
const activeTab = ref('roles')
const roleSearch = ref('')
const memberSearch = ref('')
const roleDialog = ref(false)
const memberDialog = ref(false)
const editingRole = ref(null)
const editingMember = ref(null)
const savingRole = ref(false)
const savingMember = ref(false)
const newSkill = ref('')
const newCert = ref('')

const roleForm = ref({ name: '', description: '', is_default: false })
const memberForm = ref(emptyMemberForm())

const userSearch = ref('')
const supplierSearch = ref('')
const filteredUserOptions = ref([])
const filteredSupplierOptions = ref([])

const roleOptions = computed(() => crewStore.roles.map(r => ({ label: r.name, value: r.id })))

function filterUsers(val, update) {
  userSearch.value = val
  update(() => {
    const term = String(val || '').toLowerCase()
    if (!usersStore.users.length) {
      usersStore.fetchUsers().catch(() => {})
    }
    filteredUserOptions.value = usersStore.users
      .filter(u => !term || (u.full_name || '').toLowerCase().includes(term) || (u.email || '').toLowerCase().includes(term))
      .map(u => ({ label: `${u.full_name || u.email}`, value: u.id }))
  })
}

function filterSuppliers(val, update) {
  supplierSearch.value = val
  update(() => {
    const term = String(val || '').toLowerCase()
    if (!customersStore.customers.length) {
      customersStore.fetchAll().catch(() => {})
    }
    filteredSupplierOptions.value = customersStore.customers
      .filter(c => c.is_crew_supplier)
      .filter(c => !term || c.name.toLowerCase().includes(term))
      .map(c => ({ label: c.name, value: c.id }))
  })
}

function emptyMemberForm() {
  return {
    name: '',
    email: '',
    phone: '',
    user_id: null,
    supplier_id: null,
    hourly_rate: null,
    daily_rate: null,
    notes: '',
    is_active: true,
    skills: [],
    certifications: [],
    preferred_role_ids: [],
  }
}

const roleColumns = computed(() => [
  { name: 'name', label: t('crew.roleName'), field: 'name', align: 'left', sortable: true },
  { name: 'description', label: t('crew.description'), field: 'description', align: 'left' },
  { name: 'is_default', label: t('crew.default'), field: 'is_default', align: 'center' },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
])

const memberColumns = computed(() => [
  { name: 'name', label: t('crew.memberName'), field: 'name', align: 'left', sortable: true },
  { name: 'source', label: t('crew.source'), field: 'source', align: 'left' },
  { name: 'skills', label: t('crew.skills'), field: 'skills', align: 'left' },
  { name: 'is_active', label: t('crew.active'), field: 'is_active', align: 'center' },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
])

function onTabChange() {
  if (activeTab.value === 'members' && !crewStore.members.length) {
    crewStore.fetchMembers()
  }
}

function openCreate() {
  if (activeTab.value === 'roles') {
    editingRole.value = null
    roleForm.value = { name: '', description: '', is_default: false }
    roleDialog.value = true
  } else {
    editingMember.value = null
    memberForm.value = emptyMemberForm()
    memberDialog.value = true
    if (!customersStore.customers.length) customersStore.fetchAll().catch(() => {})
    if (!usersStore.users.length) usersStore.fetchUsers().catch(() => {})
  }
}

function openEditRole(role) {
  editingRole.value = role
  roleForm.value = { name: role.name, description: role.description || '', is_default: role.is_default }
  roleDialog.value = true
}

function openEditMember(member) {
  editingMember.value = member
  memberForm.value = {
    name: member.name || '',
    email: member.email || '',
    phone: member.phone || '',
    user_id: member.user_id || null,
    supplier_id: member.supplier_id || null,
    hourly_rate: member.hourly_rate ?? null,
    daily_rate: member.daily_rate ?? null,
    notes: member.notes || '',
    is_active: member.is_active,
    skills: [...(member.skills || [])],
    certifications: (member.certifications || []).map(c => ({ certification: c.certification, expires_at: c.expires_at })),
    preferred_role_ids: (member.preferred_roles || []).map(r => r.id),
  }
  memberDialog.value = true
  if (!customersStore.customers.length) customersStore.fetchAll().catch(() => {})
  if (!usersStore.users.length) usersStore.fetchUsers().catch(() => {})
}

function addSkill() {
  const val = newSkill.value.trim()
  if (val && !memberForm.value.skills.includes(val)) {
    memberForm.value.skills.push(val)
  }
  newSkill.value = ''
}

function addCertification() {
  const val = newCert.value.trim()
  if (val) {
    memberForm.value.certifications.push({ certification: val, expires_at: null })
  }
  newCert.value = ''
}

async function saveRole() {
  if (!roleForm.value.name.trim()) return
  savingRole.value = true
  try {
    if (editingRole.value) {
      await crewStore.updateRole(editingRole.value.id, roleForm.value)
      $q.notify({ type: 'positive', message: t('crew.roleUpdated') })
    } else {
      await crewStore.createRole(roleForm.value)
      $q.notify({ type: 'positive', message: t('crew.roleCreated') })
    }
    roleDialog.value = false
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('crew.failedSaveRole') })
  } finally {
    savingRole.value = false
  }
}

async function saveMember() {
  if (!memberForm.value.name.trim()) return
  savingMember.value = true
  try {
    const payload = { ...memberForm.value }
    if (editingMember.value) {
      await crewStore.updateMember(editingMember.value.id, payload)
      $q.notify({ type: 'positive', message: t('crew.memberUpdated') })
    } else {
      await crewStore.createMember(payload)
      $q.notify({ type: 'positive', message: t('crew.memberCreated') })
    }
    memberDialog.value = false
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('crew.failedSaveMember') })
  } finally {
    savingMember.value = false
  }
}

function confirmDeleteRole(role) {
  $q.dialog({
    title: t('crew.deleteRole'),
    message: t('crew.deleteRoleConfirm', { name: role.name }),
    cancel: t('app.actions.cancel'),
    ok: t('app.actions.delete'),
    persistent: true,
  }).onOk(async () => {
    try {
      await crewStore.deleteRole(role.id)
      $q.notify({ type: 'positive', message: t('crew.roleDeleted') })
    } catch (err) {
      $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('crew.failedDeleteRole') })
    }
  })
}

function confirmDeleteMember(member) {
  $q.dialog({
    title: t('crew.deleteMember'),
    message: t('crew.deleteMemberConfirm', { name: member.name }),
    cancel: t('app.actions.cancel'),
    ok: t('app.actions.delete'),
    persistent: true,
  }).onOk(async () => {
    try {
      await crewStore.deleteMember(member.id)
      $q.notify({ type: 'positive', message: t('crew.memberDeleted') })
    } catch (err) {
      $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('crew.failedDeleteMember') })
    }
  })
}

watch(() => crewStore.roles, (val) => {
  if (!val.length) crewStore.fetchRoles()
}, { immediate: true })

watch(() => memberForm.value.user_id, (userId) => {
  if (!userId) return
  const user = usersStore.users.find(u => u.id === userId)
  if (user) {
    if (!memberForm.value.name) memberForm.value.name = user.full_name || ''
    if (!memberForm.value.email) memberForm.value.email = user.email || ''
  }
})
</script>
