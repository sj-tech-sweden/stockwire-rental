<template>
  <q-page class="q-pa-md ec-page">
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">{{ t('app.nav.crew') }}</div>
      <q-btn v-if="authStore.canEdit" color="primary" :icon="activeTab === 'members' ? 'person_add' : 'add'" :label="createBtnLabel" unelevated @click="openCreate" />
    </div>

    <q-tabs v-model="activeTab" inline-label align="left" class="q-mb-md" @update:model-value="onTabChange">
      <q-tab name="roles" :label="t('crew.roles')" />
      <q-tab name="skills" :label="t('crew.skills')" />
      <q-tab name="certifications" :label="t('crew.certifications')" />
      <q-tab name="members" :label="t('crew.members')" />
    </q-tabs>

    <!-- Roles tab -->
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

    <!-- Skills tab -->
    <div v-if="activeTab === 'skills'">
      <q-table
        :rows="crewStore.skills"
        :columns="skillColumns"
        row-key="id"
        flat bordered
        :loading="loadingSkills"
        :filter="skillSearch"
        :pagination="{ rowsPerPage: 50 }"
        class="ec-card"
      >
        <template #top-right>
          <q-input v-model="skillSearch" dense outlined clearable :placeholder="t('crew.searchSkills')">
            <template #prepend><q-icon name="search" /></template>
          </q-input>
        </template>

        <template #body-cell-actions="props">
          <q-td v-if="authStore.canEdit" :props="props" auto-width>
            <q-btn flat round dense icon="delete" color="negative" @click="confirmDeleteSkill(props.row)" />
          </q-td>
        </template>
      </q-table>
    </div>

    <!-- Certifications tab -->
    <div v-if="activeTab === 'certifications'">
      <q-table
        :rows="crewStore.certifications"
        :columns="certColumns"
        row-key="id"
        flat bordered
        :loading="loadingCerts"
        :filter="certSearch"
        :pagination="{ rowsPerPage: 50 }"
        class="ec-card"
      >
        <template #top-right>
          <q-input v-model="certSearch" dense outlined clearable :placeholder="t('crew.searchCertifications')">
            <template #prepend><q-icon name="search" /></template>
          </q-input>
        </template>

        <template #body-cell-actions="props">
          <q-td v-if="authStore.canEdit" :props="props" auto-width>
            <q-btn flat round dense icon="delete" color="negative" @click="confirmDeleteCert(props.row)" />
          </q-td>
        </template>
      </q-table>
    </div>

    <!-- Members tab -->
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
        @row-click="onMemberClick"
        @row-dblclick="onMemberDblClick"
      >
        <template #top-right>
          <q-input v-model="memberSearch" dense outlined clearable :placeholder="t('crew.searchMembers')">
            <template #prepend><q-icon name="search" /></template>
          </q-input>
        </template>

        <template #body-cell-actions="props">
          <q-td :props="props" auto-width>
            <q-btn flat round dense icon="open_in_new" color="primary" @click.stop="router.push(`/crew/${props.row.id}`)" />
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
            <q-badge v-for="skill in (props.row.skills || []).slice(0, 3)" :key="skill.id || skill" color="teal" class="q-mr-xs" :label="skill.name || skill" />
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

    <!-- Role dialog -->
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

    <!-- Skill dialog -->
    <q-dialog v-model="skillDialog" persistent>
      <q-card style="min-width: 400px" class="ec-card">
        <q-card-section><div class="text-h6">{{ t('crew.createSkill') }}</div></q-card-section>
        <q-card-section class="q-pt-none">
          <q-input v-model="skillForm.name" :label="t('crew.skillName')" outlined dense class="q-mb-sm" autofocus :rules="[v => !!v || t('login.required')]" @keyup.enter="saveSkill" />
          <q-input v-model="skillForm.category" :label="t('crew.skillCategory')" outlined dense :placeholder="t('crew.skillCategoryPlaceholder')" @keyup.enter="saveSkill" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="skillDialog = false" />
          <q-btn color="primary" unelevated :label="t('app.actions.save')" :loading="savingSkill" @click="saveSkill" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Certification dialog -->
    <q-dialog v-model="certDialog" persistent>
      <q-card style="min-width: 400px" class="ec-card">
        <q-card-section><div class="text-h6">{{ t('crew.createCertification') }}</div></q-card-section>
        <q-card-section class="q-pt-none">
          <q-input v-model="certForm.name" :label="t('crew.certificationName')" outlined dense class="q-mb-sm" autofocus :rules="[v => !!v || t('login.required')]" @keyup.enter="saveCert" />
          <q-input v-model="certForm.category" :label="t('crew.certificationCategory')" outlined dense @keyup.enter="saveCert" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="certDialog = false" />
          <q-btn color="primary" unelevated :label="t('app.actions.save')" :loading="savingCert" @click="saveCert" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useCrewStore } from '../stores/crew'
import { useAuthStore } from '../stores/auth'

const $q = useQuasar()
const { t } = useI18n()
const router = useRouter()
const crewStore = useCrewStore()
const authStore = useAuthStore()

const activeTab = ref('roles')
const roleSearch = ref('')
const memberSearch = ref('')
const skillSearch = ref('')
const certSearch = ref('')
const roleDialog = ref(false)
const skillDialog = ref(false)
const certDialog = ref(false)
const editingRole = ref(null)
const savingRole = ref(false)
const savingSkill = ref(false)
const savingCert = ref(false)
const loadingSkills = ref(false)
const loadingCerts = ref(false)

const roleForm = ref({ name: '', description: '', is_default: false })
const skillForm = ref({ name: '', category: '' })
const certForm = ref({ name: '', category: '' })

const createBtnLabel = computed(() => {
  if (activeTab.value === 'roles') return t('crew.newRole')
  if (activeTab.value === 'skills') return t('crew.createSkill')
  if (activeTab.value === 'certifications') return t('crew.createCertification')
  return t('crew.newMember')
})

const roleColumns = computed(() => [
  { name: 'name', label: t('crew.roleName'), field: 'name', align: 'left', sortable: true },
  { name: 'description', label: t('crew.description'), field: 'description', align: 'left' },
  { name: 'is_default', label: t('crew.default'), field: 'is_default', align: 'center' },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
])

const skillColumns = computed(() => [
  { name: 'name', label: t('crew.skillName'), field: 'name', align: 'left', sortable: true },
  { name: 'category', label: t('crew.skillCategory'), field: 'category', align: 'left', sortable: true },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
])

const certColumns = computed(() => [
  { name: 'name', label: t('crew.certificationName'), field: 'name', align: 'left', sortable: true },
  { name: 'category', label: t('crew.certificationCategory'), field: 'category', align: 'left', sortable: true },
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
  if (activeTab.value === 'skills' && !crewStore.skills.length) {
    loadSkills()
  }
  if (activeTab.value === 'certifications' && !crewStore.certifications.length) {
    loadCerts()
  }
}

async function loadSkills() {
  loadingSkills.value = true
  try {
    await crewStore.fetchSkills()
  } finally {
    loadingSkills.value = false
  }
}

async function loadCerts() {
  loadingCerts.value = true
  try {
    await crewStore.fetchCertifications()
  } finally {
    loadingCerts.value = false
  }
}

function onMemberClick(evt, row) {
  router.push(`/crew/${row.id}`)
}

function onMemberDblClick(evt, row) {
  router.push(`/crew/${row.id}`)
}

function openCreate() {
  if (activeTab.value === 'roles') {
    editingRole.value = null
    roleForm.value = { name: '', description: '', is_default: false }
    roleDialog.value = true
  } else if (activeTab.value === 'skills') {
    skillForm.value = { name: '', category: '' }
    skillDialog.value = true
  } else if (activeTab.value === 'certifications') {
    certForm.value = { name: '', category: '' }
    certDialog.value = true
  } else {
    router.push('/crew/new')
  }
}

function openEditRole(role) {
  editingRole.value = role
  roleForm.value = { name: role.name, description: role.description || '', is_default: role.is_default }
  roleDialog.value = true
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

async function saveSkill() {
  if (!skillForm.value.name.trim()) return
  savingSkill.value = true
  try {
    await crewStore.createSkill({
      name: skillForm.value.name.trim(),
      category: skillForm.value.category.trim() || null,
    })
    $q.notify({ type: 'positive', message: t('crew.skillCreated') })
    skillDialog.value = false
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('crew.failedSaveSkill') })
  } finally {
    savingSkill.value = false
  }
}

async function saveCert() {
  if (!certForm.value.name.trim()) return
  savingCert.value = true
  try {
    await crewStore.createCertification({
      name: certForm.value.name.trim(),
      category: certForm.value.category.trim() || null,
    })
    $q.notify({ type: 'positive', message: t('crew.certificationCreated') })
    certDialog.value = false
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('crew.failedSaveCertification') })
  } finally {
    savingCert.value = false
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

function confirmDeleteSkill(skill) {
  $q.dialog({
    title: t('crew.deleteSkill'),
    message: t('crew.deleteSkillConfirm', { name: skill.name }),
    cancel: t('app.actions.cancel'),
    ok: t('app.actions.delete'),
    persistent: true,
  }).onOk(async () => {
    try {
      await crewStore.deleteSkill(skill.id)
      $q.notify({ type: 'positive', message: t('crew.skillDeleted') })
    } catch (err) {
      $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('crew.failedDeleteSkill') })
    }
  })
}

function confirmDeleteCert(cert) {
  $q.dialog({
    title: t('crew.deleteCertification'),
    message: t('crew.deleteCertificationConfirm', { name: cert.name }),
    cancel: t('app.actions.cancel'),
    ok: t('app.actions.delete'),
    persistent: true,
  }).onOk(async () => {
    try {
      await crewStore.deleteCertification(cert.id)
      $q.notify({ type: 'positive', message: t('crew.certificationDeleted') })
    } catch (err) {
      $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('crew.failedDeleteCertification') })
    }
  })
}

watch(() => crewStore.roles, (val) => {
  if (!val.length) crewStore.fetchRoles()
}, { immediate: true })
</script>
