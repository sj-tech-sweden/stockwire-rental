<template>
  <div>
    <h2>{{ t('users.title') }}</h2>
    <button @click="reload">{{ t('home.refresh') }}</button>
    <section style="margin-top:16px">
      <h3>{{ t('users.createUser') }}</h3>
      <form @submit.prevent="create">
        <input v-model="form.email" :placeholder="t('profile.email')" required />
        <input v-model="form.full_name" :placeholder="t('profile.fullName')" required />
        <input v-model="form.password" type="password" :placeholder="t('login.password')" required />
        <select v-model="form.role">
          <option value="viewer">{{ t('users.viewer') }}</option>
          <option value="manager">{{ t('users.manager') }}</option>
          <option value="admin">{{ t('users.admin') }}</option>
        </select>
        <button type="submit">{{ t('users.create') }}</button>
      </form>
    </section>

    <section style="margin-top:16px">
      <h3>{{ t('users.apiKeys') }}</h3>
      <form @submit.prevent="createKey">
        <input v-model="keyForm.name" :placeholder="t('users.keyName')" required />
        <input v-model="keyForm.raw" :placeholder="t('users.rawKey')" required />
        <label><input type="checkbox" v-model="keyForm.is_admin" /> {{ t('users.admin') }}</label>
        <button type="submit">{{ t('users.createApiKey') }}</button>
      </form>
      <div style="margin-top:8px">
        <button @click="loadKeys">{{ t('users.refreshKeys') }}</button>
        <ul>
          <li v-for="k in keys" :key="k.id">{{ k.name }} - {{ k.is_admin ? t('users.admin') : t('users.limited') }} <button @click="revoke(k.id)">{{ t('users.revoke') }}</button></li>
        </ul>
      </div>
    </section>
    <table>
      <thead>
        <tr><th>ID</th><th>{{ t('profile.email') }}</th><th>{{ t('users.name') }}</th><th>{{ t('users.roles') }}</th><th>{{ t('users.active') }}</th><th>{{ t('users.actions') }}</th></tr>
      </thead>
      <tbody>
        <tr v-for="u in users" :key="u.id">
          <td>{{ u.id }}</td>
          <td>{{ u.email }}</td>
          <td>{{ u.full_name }}</td>
          <td>
            <div>{{ t('users.primary') }}: {{ u.role }}</div>
            <div style="margin-top:6px">
              <span v-if="userRoles[u.id] && userRoles[u.id].length">
                <span v-for="r in userRoles[u.id]" :key="r.id" class="role-chip">
                  {{ r.display_name || r.name }} <button style="margin-left:6px" @click="removeRole(u.id, r.id)">x</button>
                </span>
              </span>
              <span v-else>{{ t('users.noRolesAssigned') }}</span>
            </div>
            <div style="margin-top:6px">
              <select v-model="assignSelection[u.id]">
                <option value="">{{ t('users.assignRole') }}</option>
                <option v-for="r in roles" :key="r.id" :value="r.id">{{ r.display_name || r.name }}</option>
              </select>
              <button @click="assignRole(u.id)">{{ t('users.assign') }}</button>
            </div>
          </td>
          <td>{{ u.is_active }}</td>
          <td>
            <button @click="del(u.id)">{{ t('users.delete') }}</button>
            <button @click="edit(u)">{{ t('users.edit') }}</button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-if="editing" style="margin-top:16px">
      <h3>{{ t('users.editUser') }}</h3>
      <form @submit.prevent="saveEdit">
        <input v-model="editForm.email" :placeholder="t('profile.email')" required />
        <input v-model="editForm.full_name" :placeholder="t('profile.fullName')" required />
        <input v-model="editForm.password" type="password" :placeholder="t('users.newPasswordOptional')" />
        <select v-model="editForm.role">
          <option value="viewer">{{ t('users.viewer') }}</option>
          <option value="manager">{{ t('users.manager') }}</option>
          <option value="admin">{{ t('users.admin') }}</option>
        </select>
        <label><input type="checkbox" v-model="editForm.is_active" /> {{ t('users.active') }}</label>
        <button type="submit">{{ t('app.actions.save') }}</button>
        <button type="button" @click="cancelEdit">{{ t('app.actions.cancel') }}</button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUsersStore } from '../stores/users'

const store = useUsersStore()
const { t } = useI18n()
const users = store.users
const keys = ref([])
const roles = store.roles

const form = reactive({ email: '', full_name: '', password: '', role: 'viewer' })
const keyForm = reactive({ name: '', raw: '', is_admin: false })

const editing = ref(false)
const editForm = reactive({ id: null, email: '', full_name: '', password: '', role: 'viewer', is_active: true })

const userRoles = ref({})
const assignSelection = ref({})

async function reload() {
  await store.fetchUsers()
  // populate userRoles for each user
  for (const u of users) {
    const rolesForUser = await store.listUserRoles(u.id)
    userRoles.value[u.id] = rolesForUser
  }
}

async function del(id) {
  if (!confirm(t('users.deleteUserConfirm'))) return
  await store.deleteUser(id)
}

function edit(u) {
  editing.value = true
  editForm.id = u.id
  editForm.email = u.email
  editForm.full_name = u.full_name
  editForm.role = u.role
  editForm.is_active = u.is_active
  editForm.password = ''
}

function cancelEdit() {
  editing.value = false
}

async function saveEdit() {
  const payload = { email: editForm.email, password: editForm.password || undefined, full_name: editForm.full_name, role: editForm.role, is_active: editForm.is_active }
  await store.updateUser(editForm.id, payload)
  editing.value = false
  await reload()
}

async function create() {
  await store.createUser({ email: form.email, password: form.password, full_name: form.full_name, role: form.role, is_active: true })
  form.email = form.full_name = form.password = ''
  form.role = 'viewer'
  await reload()
}

async function loadKeys() {
  keys.value = await store.listApiKeys()
}

async function createKey() {
  await store.createApiKey(keyForm.name, keyForm.raw, keyForm.is_admin)
  keyForm.name = keyForm.raw = ''
  keyForm.is_admin = false
  await loadKeys()
}

async function revoke(id) {
  if (!confirm(t('users.revokeKeyConfirm'))) return
  await store.revokeApiKey(id)
  await loadKeys()
}

async function removeRole(userId, roleId) {
  if (!confirm(t('users.removeRoleConfirm'))) return
  await store.removeRoleFromUser(userId, roleId)
  await reload()
}

async function assignRole(userId) {
  const rid = assignSelection[userId]
  if (!rid) return alert(t('users.selectRole'))
  await store.assignRoleToUser(userId, rid)
  assignSelection[userId] = null
  await reload()
}

onMounted(() => {
  ;(async () => {
    await store.listRoles()
    await reload()
  })()
})
</script>

<style scoped>
.role-chip { display:inline-block; padding:4px 8px; margin:2px; background:#eef; border-radius:4px }
</style>
