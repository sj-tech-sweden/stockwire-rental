<template>
  <q-page class="q-pa-md ec-page">
    <div class="text-h5 q-mb-md">{{ t('settings.title') }}</div>

    <q-tabs v-model="tab" inline-label align="left" class="q-mb-md">
      <q-tab name="auth" icon="manage_accounts" :label="t('settings.tabs.auth')" />
      <q-tab name="company" icon="business" :label="t('settings.tabs.company')" />
      <q-tab name="custom-fields" icon="list_alt" :label="t('settings.tabs.customFields')" />
      <q-tab name="inventory" icon="account_tree" :label="t('settings.tabs.inventory')" />
      <q-tab name="integrations" icon="hub" :label="t('settings.tabs.integrations')" />
      <q-tab name="offline-queue" icon="sync" :label="t('settings.tabs.offlineQueue')" />
      <q-tab name="about" icon="info" :label="t('settings.tabs.about')" />
    </q-tabs>

    <q-tab-panels v-model="tab" animated>
      <q-tab-panel name="auth" class="q-pa-none">
        <q-card class="ec-card q-pa-md">
          <div class="row items-center q-mb-sm">
            <div class="text-subtitle1 col">{{ t('settings.auth.title') }}</div>
            <q-btn color="primary" icon="person_add" :label="t('settings.auth.newUser')" unelevated @click="openCreateUser" />
          </div>

          <q-table
            :rows="authStore.users"
            :columns="authColumns"
            :filter="authFilter"
            row-key="id"
            :grid="compactGrid"
            :hide-header="compactGrid"
            flat
            bordered
            :loading="authLoading"
            :pagination="{ rowsPerPage: 50 }"
            :rows-per-page-options="[25, 50, 100, 0]"
            class="q-mb-md"
          >
            <template #top-right>
              <q-input v-model="authFilter" dense outlined :placeholder="t('settings.auth.searchUsers')" clearable>
                <template #prepend><q-icon name="search" /></template>
              </q-input>
            </template>
            <template #body-cell-role="props">
              <q-td :props="props">
                <q-badge :label="props.value" :color="roleColor(props.value)" />
              </q-td>
            </template>
            <template #body-cell-is_active="props">
              <q-td :props="props">
                <q-icon :name="props.value ? 'check_circle' : 'cancel'" :color="props.value ? 'positive' : 'negative'" />
              </q-td>
            </template>
            <template #body-cell-actions="props">
              <q-td :props="props" auto-width>
                <q-btn flat dense round icon="edit" color="primary" class="q-mr-xs" @click="openEditUser(props.row)" />
                <q-btn
                  flat
                  dense
                  round
                  icon="delete"
                  color="negative"
                  :disable="props.row.id === authStore.me?.id"
                  @click="confirmDeleteUser(props.row)"
                />
              </q-td>
            </template>
            <template #item="props">
              <div class="q-pa-xs col-12">
                <q-card flat bordered>
                  <q-card-section class="q-pb-sm">
                    <div class="row items-center justify-between">
                      <div class="text-subtitle2">{{ props.row.full_name || props.row.email }}</div>
                      <q-badge :label="props.row.role" :color="roleColor(props.row.role)" />
                    </div>
                    <div class="text-caption text-grey-7">{{ props.row.email }}</div>
                  </q-card-section>
                  <q-card-section class="q-pt-none q-pb-sm">
                    <div class="text-caption">{{ t('settings.auth.status') }}: {{ props.row.is_active ? t('settings.auth.active') : t('settings.auth.inactive') }}</div>
                  </q-card-section>
                  <q-card-actions align="right">
                    <q-btn flat dense icon="edit" color="primary" @click="openEditUser(props.row)" />
                    <q-btn
                      flat
                      dense
                      icon="delete"
                      color="negative"
                      :disable="props.row.id === authStore.me?.id"
                      @click="confirmDeleteUser(props.row)"
                    />
                  </q-card-actions>
                </q-card>
              </div>
            </template>
          </q-table>

          <q-separator class="q-my-md" />

          <div class="row items-center q-mb-sm">
            <div class="text-subtitle2 col">{{ t('settings.auth.apiKeys') }}</div>
            <q-btn color="primary" icon="vpn_key" :label="t('settings.auth.newApiKey')" unelevated @click="openCreateApiKey" />
          </div>

          <q-table
            :rows="authStore.apiKeys"
            :columns="apiKeyColumns"
            row-key="id"
            :grid="compactGrid"
            :hide-header="compactGrid"
            flat
            bordered
            :loading="authLoading"
            :pagination="{ rowsPerPage: 50 }"
            :rows-per-page-options="[25, 50, 100, 0]"
          >
            <template #body-cell-is_admin="props">
              <q-td :props="props">
                <q-badge :label="props.value ? t('settings.auth.apiKeyAdmin') : t('settings.auth.apiKeyScoped')" :color="props.value ? 'negative' : 'primary'" />
              </q-td>
            </template>
            <template #body-cell-created_at="props">
              <q-td :props="props">{{ new Date(props.value).toLocaleDateString() }}</q-td>
            </template>
            <template #body-cell-actions="props">
              <q-td :props="props" auto-width>
                <q-btn flat dense round icon="delete" color="negative" @click="deleteApiKey(props.row)" />
              </q-td>
            </template>
            <template #item="props">
              <div class="col-12 col-sm-6 col-md-4 q-pa-xs">
                <q-card flat bordered>
                  <q-card-section class="q-pb-sm">
                    <div class="row items-center justify-between">
                      <div class="text-subtitle2">{{ props.row.name }}</div>
                      <q-badge :label="props.row.is_admin ? t('settings.auth.apiKeyAdmin') : t('settings.auth.apiKeyScoped')" :color="props.row.is_admin ? 'negative' : 'primary'" />
                    </div>
                    <div class="text-caption text-grey-7">Created: {{ new Date(props.row.created_at).toLocaleDateString() }}</div>
                  </q-card-section>
                  <q-card-actions align="right">
                    <q-btn flat dense icon="delete" color="negative" @click="deleteApiKey(props.row)" />
                  </q-card-actions>
                </q-card>
              </div>
            </template>
          </q-table>

          <q-separator class="q-my-md" />

          <div class="text-subtitle2 q-mb-sm">{{ t('settings.sso.title') }}</div>
          <div class="text-caption text-grey-7 q-mb-sm">{{ t('settings.sso.description') }}</div>

          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-12 col-md-3">
              <q-toggle v-model="authSsoDraft.enabled" :label="t('settings.sso.enableSso')" color="primary" />
            </div>
            <div class="col-12 col-md-3">
              <q-toggle v-model="authSsoDraft.auto_create_users" :label="t('settings.sso.autoCreateUsers')" color="primary" />
            </div>
            <div class="col-12 col-md-3">
              <q-toggle v-model="authSsoDraft.sync_roles_on_login" :label="t('settings.sso.syncRolesOnLogin')" color="primary" />
            </div>
            <div class="col-12 col-md-3">
              <q-select
                v-model="authSsoDraft.default_role"
                :options="roleOptions"
                :label="t('settings.sso.defaultRole')"
                outlined
                dense
                emit-value
                map-options
              />
            </div>
          </div>

          <div class="text-subtitle2 q-mt-md q-mb-sm">{{ t('settings.sso.groupRoleMapping') }}</div>
          <div class="text-caption text-grey-7 q-mb-sm">{{ t('settings.sso.groupRoleMappingHint') }}</div>
          <div
            v-for="(row, index) in authSsoDraft.group_role_rows"
            :key="`group-role-${index}`"
            class="row q-col-gutter-sm q-mb-xs"
          >
            <div class="col-12 col-md-6">
              <q-input v-model="row.group" :label="t('settings.sso.externalGroup')" outlined dense />
            </div>
            <div class="col-10 col-md-4">
              <q-select
                v-model="row.role"
                :options="roleOptions"
                :label="t('users.roles')"
                outlined
                dense
                emit-value
                map-options
              />
            </div>
            <div class="col-2 col-md-2 row items-center justify-end">
              <q-btn flat dense round icon="delete" color="negative" @click="removeGroupRoleRow(index)" />
            </div>
          </div>
          <q-btn flat dense icon="add" color="primary" :label="t('settings.sso.addGroupMapping')" class="q-mb-md" @click="addGroupRoleRow" />

          <div class="text-subtitle2 q-mb-sm">{{ t('settings.sso.oidcProviders') }}</div>
          <div class="text-caption text-grey-7 q-mb-sm">{{ t('settings.sso.oidcProvidersHint') }}</div>
          <div
            v-for="(provider, index) in authSsoDraft.oidc_providers"
            :key="`oidc-${provider._draftKey || index}`"
            class="q-pa-sm q-mb-sm"
            style="border: 1px solid #d7dee6; border-radius: 10px"
          >
            <div class="row q-col-gutter-sm q-mb-sm">
              <div class="col-12 col-md-3"><q-input v-model="provider.key" :label="t('settings.sso.providerKey')" outlined dense /></div>
              <div class="col-12 col-md-3"><q-input v-model="provider.display_name" :label="t('settings.sso.displayName')" outlined dense /></div>
              <div class="col-12 col-md-2"><q-toggle v-model="provider.enabled" :label="t('settings.sso.enabled')" color="primary" /></div>
              <div class="col-12 col-md-2"><q-toggle v-model="provider.allow_auto_create" :label="t('settings.sso.autoCreate')" color="primary" /></div>
              <div class="col-12 col-md-2 row items-center justify-end"><q-btn flat dense round icon="delete" color="negative" @click="removeOidcProvider(index)" /></div>
            </div>
            <div class="row q-col-gutter-sm">
              <div class="col-12 col-md-6"><q-input v-model="provider.issuer" :label="t('settings.sso.issuer')" outlined dense /></div>
              <div class="col-12 col-md-6"><q-input v-model="provider.scopes" :label="t('settings.sso.scopes')" outlined dense /></div>
              <div class="col-12 col-md-6"><q-input v-model="provider.client_id" :label="t('settings.sso.clientId')" outlined dense /></div>
              <div class="col-12 col-md-6"><q-input v-model="provider.client_secret" :label="t('settings.sso.clientSecret')" outlined dense type="password" /></div>
              <div class="col-12 col-md-4"><q-input v-model="provider.authorization_endpoint" :label="t('settings.sso.authorizationEndpoint')" outlined dense /></div>
              <div class="col-12 col-md-4"><q-input v-model="provider.token_endpoint" :label="t('settings.sso.tokenEndpoint')" outlined dense /></div>
              <div class="col-12 col-md-4"><q-input v-model="provider.jwks_uri" :label="t('settings.sso.jwksUri')" outlined dense /></div>
              <div class="col-12 col-md-3"><q-input v-model="provider.group_claim" :label="t('settings.sso.groupClaim')" outlined dense /></div>
              <div class="col-12 col-md-3"><q-input v-model="provider.email_claim" :label="t('settings.sso.emailClaim')" outlined dense /></div>
              <div class="col-12 col-md-3"><q-input v-model="provider.name_claim" :label="t('settings.sso.nameClaim')" outlined dense /></div>
              <div class="col-12 col-md-3"><q-input v-model="provider.subject_claim" :label="t('settings.sso.subjectClaim')" outlined dense /></div>
            </div>
          </div>
          <q-btn flat dense icon="add" color="primary" :label="t('settings.sso.addOidcProvider')" class="q-mb-md" @click="addOidcProvider" />

          <div class="text-subtitle2 q-mb-sm">{{ t('settings.sso.samlProviders') }}</div>
          <div class="text-caption text-grey-7 q-mb-sm">{{ t('settings.sso.samlProvidersHint') }}</div>
          <div
            v-for="(provider, index) in authSsoDraft.saml_providers"
            :key="`saml-${provider._draftKey || index}`"
            class="q-pa-sm q-mb-sm"
            style="border: 1px solid #d7dee6; border-radius: 10px"
          >
            <div class="row q-col-gutter-sm q-mb-sm">
              <div class="col-12 col-md-3"><q-input v-model="provider.key" :label="t('settings.sso.providerKey')" outlined dense /></div>
              <div class="col-12 col-md-3"><q-input v-model="provider.display_name" :label="t('settings.sso.displayName')" outlined dense /></div>
              <div class="col-12 col-md-2"><q-toggle v-model="provider.enabled" :label="t('settings.sso.enabled')" color="primary" /></div>
              <div class="col-12 col-md-2"><q-toggle v-model="provider.allow_auto_create" :label="t('settings.sso.autoCreate')" color="primary" /></div>
              <div class="col-12 col-md-2 row items-center justify-end"><q-btn flat dense round icon="delete" color="negative" @click="removeSamlProvider(index)" /></div>
            </div>
            <div class="row q-col-gutter-sm">
              <div class="col-12 col-md-4"><q-input v-model="provider.idp_entity_id" :label="t('settings.sso.idpEntityId')" outlined dense /></div>
              <div class="col-12 col-md-4"><q-input v-model="provider.idp_sso_url" :label="t('settings.sso.idpSsoUrl')" outlined dense /></div>
              <div class="col-12 col-md-4"><q-input v-model="provider.idp_x509_cert" :label="t('settings.sso.idpX509Cert')" outlined dense type="textarea" autogrow /></div>
              <div class="col-12 col-md-6"><q-input v-model="provider.sp_entity_id" :label="t('settings.sso.spEntityId')" outlined dense /></div>
              <div class="col-12 col-md-6"><q-input v-model="provider.acs_url" :label="t('settings.sso.acsUrl')" outlined dense /></div>
              <div class="col-12 col-md-3"><q-input v-model="provider.group_attribute" :label="t('settings.sso.groupAttribute')" outlined dense /></div>
              <div class="col-12 col-md-3"><q-input v-model="provider.email_attribute" :label="t('settings.sso.emailAttribute')" outlined dense /></div>
              <div class="col-12 col-md-3"><q-input v-model="provider.name_attribute" :label="t('settings.sso.nameAttribute')" outlined dense /></div>
              <div class="col-12 col-md-3"><q-input v-model="provider.subject_attribute" :label="t('settings.sso.subjectAttribute')" outlined dense /></div>
            </div>
          </div>
          <q-btn flat dense icon="add" color="primary" :label="t('settings.sso.addSamlProvider')" class="q-mb-sm" @click="addSamlProvider" />

          <q-banner v-if="authSsoValidationError" class="bg-warning text-dark rounded-borders q-mb-sm" dense>
            {{ authSsoValidationError }}
          </q-banner>

          <q-btn
            color="positive"
            :label="t('settings.sso.save')"
            unelevated
            :loading="authSsoSaving"
            @click="saveAuthSsoSettings"
          />
        </q-card>
      </q-tab-panel>

      <q-tab-panel name="company" class="q-pa-none">
        <q-card class="ec-card q-pa-md">
          <div class="text-subtitle1 q-mb-sm">{{ t('settings.company.title') }}</div>
          <div class="text-caption text-grey-7 q-mb-md">{{ t('settings.company.description') }}</div>

          <div class="text-subtitle2 q-mb-sm">{{ t('settings.company.branding') }}</div>
          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-12 col-md-6">
              <q-input v-model="companyProfileDraft.company_name" :label="t('settings.company.companyName')" outlined dense />
            </div>
            <div class="col-12 col-md-3">
              <q-select
                v-model="companyProfileDraft.currency"
                :options="companyCurrencyOptions"
                :label="t('settings.company.currencyIso')"
                outlined
                dense
                emit-value
                map-options
                use-input
                fill-input
                input-debounce="0"
                @filter="filterCompanyCurrencyOptions"
              />
            </div>
            <div class="col-12 col-md-3">
              <q-input v-model="companyProfileDraft.vat_number" :label="t('settings.company.vatNumber')" outlined dense />
            </div>
            <div class="col-12 col-md-3">
              <q-select
                v-model="companyProfileDraft.default_language"
                :options="languageOptions"
                :label="t('settings.company.defaultLanguage')"
                outlined
                dense
                emit-value
                map-options
              />
            </div>
            <div class="col-12 col-md-6">
              <div class="text-caption text-grey-7">{{ t('settings.company.logoHint') }}</div>
            </div>
            <div class="col-12">
              <div class="text-caption text-grey-7">{{ t('settings.company.defaultLanguageHint') }}</div>
            </div>
          </div>

          <div class="row q-col-gutter-md q-mb-sm">
            <div v-for="slot in companyLogoSlots" :key="slot.key" class="col-12 col-md-6">
              <q-card flat bordered class="q-pa-sm">
                <div class="text-subtitle2">{{ slot.label }}</div>
                <div class="text-caption text-grey-7 q-mb-sm">{{ slot.hint }}</div>
                <div class="row q-gutter-xs q-mb-sm">
                  <q-chip v-for="usage in slot.usage" :key="`${slot.key}-${usage}`" dense color="blue-1" text-color="blue-10">
                    {{ usage }}
                  </q-chip>
                </div>
                <q-file
                  v-model="companyLogoFiles[slot.key]"
                  :label="`${t('settings.company.upload')} ${slot.label}`"
                  outlined
                  dense
                  clearable
                  accept="image/*"
                />
                <div class="row items-center q-gutter-sm q-mt-sm">
                  <q-btn
                    color="primary"
                    icon="upload"
                    :label="t('settings.company.upload')"
                    unelevated
                    :disable="!companyLogoFiles[slot.key]"
                    :loading="companyLogoUploading[slot.key]"
                    @click="uploadCompanyLogo(slot.key)"
                  />
                  <q-btn flat color="negative" :label="t('scan.clear')" @click="clearCompanyLogoSlot(slot.key)" />
                </div>
                <div v-if="currentCompanyLogoPreviewUrl(slot)" class="q-mt-sm">
                  <div class="text-caption text-grey-7 q-mb-xs">{{ t('settings.company.currentLogo') }}</div>
                  <q-img :src="currentCompanyLogoPreviewUrl(slot)" style="width: 180px; height: 92px" fit="contain" :alt="slot.label" />
                </div>
              </q-card>
            </div>
          </div>

          <div class="row items-center q-gutter-sm q-mb-sm">
            <q-btn color="positive" icon="save" :label="t('settings.company.save')" unelevated @click="saveCompanyProfile" />
          </div>

          <q-separator class="q-my-md" />

          <div class="text-subtitle2 q-mb-sm">{{ t('settings.company.addressContact') }}</div>
          <div class="row q-col-gutter-sm">
            <div class="col-12 col-md-6"><q-input v-model="companyProfileDraft.address_line1" :label="t('settings.company.addressLine1')" outlined dense /></div>
            <div class="col-12 col-md-6"><q-input v-model="companyProfileDraft.address_line2" :label="t('settings.company.addressLine2')" outlined dense /></div>
            <div class="col-12 col-md-3"><q-input v-model="companyProfileDraft.postal_code" :label="t('settings.company.postalCode')" outlined dense /></div>
            <div class="col-12 col-md-3"><q-input v-model="companyProfileDraft.city" :label="t('settings.company.city')" outlined dense /></div>
            <div class="col-12 col-md-3"><q-input v-model="companyProfileDraft.country" :label="t('settings.company.country')" outlined dense /></div>
            <div class="col-12 col-md-3"><q-input v-model="companyProfileDraft.contact_phone" :label="t('settings.company.phone')" outlined dense /></div>
            <div class="col-12 col-md-6"><q-input v-model="companyProfileDraft.contact_email" :label="t('settings.company.contactEmail')" type="email" outlined dense /></div>
            <div class="col-12 col-md-6"><q-input v-model="companyProfileDraft.website" :label="t('settings.company.website')" outlined dense /></div>
          </div>

          <div class="row q-mt-md">
            <q-btn color="positive" icon="save" :label="t('settings.company.save')" unelevated @click="saveCompanyProfile" />
          </div>
        </q-card>
      </q-tab-panel>

      <q-tab-panel name="custom-fields" class="q-pa-none">
        <q-card class="ec-card q-pa-md">
          <div class="row items-center q-mb-sm">
            <div class="text-subtitle1 col">{{ t('settings.customFields.title') }}</div>
            <q-btn color="secondary" icon="electrical_services" :label="t('settings.customFields.prefillCableFields')" class="q-mr-sm" @click="prefillCableFields" />
            <q-btn color="primary" icon="add" :label="t('settings.customFields.newField')" unelevated @click="openCreateField" />
          </div>

          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-12 col-md-4">
              <q-select
                v-model="activeEntityType"
                :options="entityTypeOptions"
                :label="t('settings.customFields.entityType')"
                outlined
                dense
                emit-value
                map-options
              />
            </div>
          </div>

          <q-table
            :rows="filteredDefinitions"
            :columns="definitionColumns"
            row-key="id"
            :grid="compactGrid"
            :hide-header="compactGrid"
            flat
            bordered
            dense
            :loading="customFieldsStore.loading"
            :pagination="{ rowsPerPage: 50 }"
            :rows-per-page-options="[25, 50, 100, 0]"
            class="q-mb-sm"
          >
            <template #body-cell-value_type="props">
              <q-td :props="props">
                <q-badge color="primary" :label="props.value" />
              </q-td>
            </template>
            <template #body-cell-is_required="props">
              <q-td :props="props">
                <q-badge :color="props.value ? 'negative' : 'grey-7'" :label="props.value ? t('settings.customFields.required') : t('settings.customFields.optional')" />
              </q-td>
            </template>
            <template #body-cell-options="props">
              <q-td :props="props">{{ formatCustomFieldOptions(props.row.options) || '—' }}</q-td>
            </template>
            <template #body-cell-actions="props">
              <q-td :props="props" auto-width>
                <q-btn flat dense round icon="edit" color="primary" class="q-mr-xs" @click="openEditField(props.row)" />
                <q-btn flat dense round icon="delete" color="negative" @click="deleteField(props.row)" />
              </q-td>
            </template>
            <template #item="props">
              <div class="q-pa-xs col-12">
                <q-card flat bordered>
                  <q-card-section class="q-pb-sm">
                    <div class="row items-center justify-between">
                      <div class="text-subtitle2">{{ customFieldLabel(props.row.label) }}</div>
                      <q-badge color="primary" :label="props.row.value_type" />
                    </div>
                    <div class="text-caption text-grey-7">{{ props.row.key }}</div>
                  </q-card-section>
                  <q-card-section class="q-pt-none q-pb-sm">
                    <div class="text-caption">{{ props.row.is_required ? t('settings.customFields.required') : t('settings.customFields.optional') }}</div>
                    <div class="text-caption" v-if="(props.row.options || []).length">{{ t('settings.customFields.options') }}: {{ formatCustomFieldOptions(props.row.options) }}</div>
                  </q-card-section>
                  <q-card-actions align="right">
                    <q-btn flat dense icon="edit" color="primary" @click="openEditField(props.row)" />
                    <q-btn flat dense icon="delete" color="negative" @click="deleteField(props.row)" />
                  </q-card-actions>
                </q-card>
              </div>
            </template>
          </q-table>
        </q-card>
      </q-tab-panel>

      <q-tab-panel name="inventory" class="q-pa-none">
        <q-card class="ec-card q-pa-md">
          <div class="text-subtitle1 q-mb-sm">{{ t('settings.inventory.title') }}</div>
          <div class="text-body2 q-mb-md">{{ t('settings.inventory.description') }}</div>

          <div class="text-subtitle2 q-mb-sm">{{ t('settings.inventory.locationTypeOptions') }}</div>
          <div class="text-caption text-grey-7 q-mb-sm">{{ t('settings.inventory.locationTypeOptionsHint') }}</div>

          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-12 col-md-6">
              <q-input
                v-model="locationTypeInput"
                  :label="t('settings.inventory.addLocationType')"
                outlined
                dense
                @keyup.enter="addLocationType"
              />
            </div>
            <div class="col-12 col-md-6 row items-center q-gutter-sm">
              <q-btn color="primary" icon="add" :label="t('users.create')" unelevated @click="addLocationType" />
              <q-btn color="secondary" :label="t('settings.inventory.resetDefaults')" @click="resetLocationTypesToDefaults" />
              <q-btn color="positive" :label="t('app.actions.save')" unelevated @click="saveLocationTypes" />
            </div>
          </div>

          <div class="q-gutter-xs q-mb-md">
            <q-chip
              v-for="option in locationTypeDraft"
              :key="option"
              removable
              color="grey-3"
              text-color="dark"
              @remove="removeLocationType(option)"
            >
              {{ option }}
            </q-chip>
          </div>

          <q-separator class="q-my-md" />

          <div class="text-subtitle2 q-mb-sm">{{ t('settings.inventory.productBrandManufacturerDefaults') }}</div>
          <div class="text-caption text-grey-7 q-mb-sm">{{ t('settings.inventory.productBrandManufacturerDefaultsHint') }}</div>

          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-12 col-md-6">
              <q-input
                v-model="brandOptionInput"
                  :label="t('settings.inventory.addBrandOption')"
                outlined
                dense
                @keyup.enter="addBrandOption"
              />
            </div>
            <div class="col-12 col-md-6 row items-center q-gutter-sm">
              <q-btn color="primary" icon="add" :label="t('settings.inventory.addBrand')" unelevated @click="addBrandOption" />
              <q-select
                v-model="defaultBrandDraft"
                :options="brandOptionsDraft.map(value => ({ label: value, value }))"
                :label="t('settings.inventory.defaultBrand')"
                outlined
                dense
                emit-value
                map-options
                style="min-width: 200px"
              />
            </div>
          </div>

          <div class="q-gutter-xs q-mb-sm">
            <q-chip
              v-for="option in brandOptionsDraft"
              :key="`brand-${option}`"
              removable
              color="grey-3"
              text-color="dark"
              @remove="removeBrandOption(option)"
            >
              {{ option }}
            </q-chip>
          </div>

          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-12 col-md-6">
              <q-input
                v-model="manufacturerOptionInput"
                  :label="t('settings.inventory.addManufacturerOption')"
                outlined
                dense
                @keyup.enter="addManufacturerOption"
              />
            </div>
            <div class="col-12 col-md-6 row items-center q-gutter-sm">
              <q-btn color="primary" icon="add" :label="t('settings.inventory.addManufacturer')" unelevated @click="addManufacturerOption" />
              <q-select
                v-model="defaultManufacturerDraft"
                :options="manufacturerOptionsDraft.map(value => ({ label: value, value }))"
                :label="t('settings.inventory.defaultManufacturer')"
                outlined
                dense
                emit-value
                map-options
                style="min-width: 220px"
              />
            </div>
          </div>

          <div class="q-gutter-xs q-mb-sm">
            <q-chip
              v-for="option in manufacturerOptionsDraft"
              :key="`manufacturer-${option}`"
              removable
              color="grey-3"
              text-color="dark"
              @remove="removeManufacturerOption(option)"
            >
              {{ option }}
            </q-chip>
          </div>

          <div class="text-subtitle2 q-mb-sm">{{ t('settings.inventory.brandLinksPreferredManufacturer') }}</div>
          <div class="text-caption text-grey-7 q-mb-sm">{{ t('settings.inventory.brandLinksPreferredManufacturerHint') }}</div>
          <q-table
            :rows="brandRows"
            :columns="brandLinkColumns"
            row-key="brand"
            :grid="compactGrid"
            :hide-header="compactGrid"
            flat
            bordered
            dense
            class="q-mb-md"
            :pagination="{ rowsPerPage: 0 }"
            hide-pagination
          >
            <template #body-cell-brand="props">
              <q-td :props="props">{{ props.row.brand }}</q-td>
            </template>
            <template #body-cell-manufacturer="props">
              <q-td :props="props">
                <q-select
                  :model-value="brandManufacturerMapDraft[props.row.brand] || null"
                  :options="manufacturerOptionsDraft.map(value => ({ label: value, value }))"
                  outlined
                  dense
                  clearable
                  emit-value
                  map-options
                  @update:model-value="value => updateBrandManufacturerMap(props.row.brand, value)"
                />
              </q-td>
            </template>
            <template #body-cell-link="props">
              <q-td :props="props">
                <q-input
                  :model-value="brandLinksDraft[props.row.brand] || ''"
                  type="url"
                  outlined
                  dense
                  placeholder="https://..."
                  @update:model-value="value => updateBrandLink(props.row.brand, value)"
                />
              </q-td>
            </template>
            <template #item="props">
              <div class="q-pa-xs col-12">
                <q-card flat bordered>
                  <q-card-section class="q-pb-sm">
                    <div class="text-subtitle2">{{ props.row.brand }}</div>
                  </q-card-section>
                  <q-card-section class="q-pt-none q-pb-sm">
                    <q-select
                      :model-value="brandManufacturerMapDraft[props.row.brand] || null"
                      :options="manufacturerOptionsDraft.map(value => ({ label: value, value }))"
                      :label="t('settings.inventory.preferredManufacturer')"
                      outlined
                      dense
                      clearable
                      emit-value
                      map-options
                      class="q-mb-sm"
                      @update:model-value="value => updateBrandManufacturerMap(props.row.brand, value)"
                    />
                    <q-input
                      :model-value="brandLinksDraft[props.row.brand] || ''"
                      type="url"
                      :label="t('settings.inventory.brandLink')"
                      outlined
                      dense
                      :placeholder="t('settings.inventory.urlPlaceholder')"
                      @update:model-value="value => updateBrandLink(props.row.brand, value)"
                    />
                  </q-card-section>
                </q-card>
              </div>
            </template>
          </q-table>

          <div class="text-subtitle2 q-mb-sm">{{ t('settings.inventory.manufacturerLinks') }}</div>
          <q-table
            :rows="manufacturerRows"
            :columns="manufacturerLinkColumns"
            row-key="manufacturer"
            :grid="compactGrid"
            :hide-header="compactGrid"
            flat
            bordered
            dense
            class="q-mb-sm"
            :pagination="{ rowsPerPage: 0 }"
            hide-pagination
          >
            <template #body-cell-manufacturer="props">
              <q-td :props="props">{{ props.row.manufacturer }}</q-td>
            </template>
            <template #body-cell-link="props">
              <q-td :props="props">
                <q-input
                  :model-value="manufacturerLinksDraft[props.row.manufacturer] || ''"
                  type="url"
                  outlined
                  dense
                  :placeholder="t('settings.inventory.urlPlaceholder')"
                  @update:model-value="value => updateManufacturerLink(props.row.manufacturer, value)"
                />
              </q-td>
            </template>
            <template #item="props">
              <div class="q-pa-xs col-12">
                <q-card flat bordered>
                  <q-card-section class="q-pb-sm">
                    <div class="text-subtitle2">{{ props.row.manufacturer }}</div>
                  </q-card-section>
                  <q-card-section class="q-pt-none q-pb-sm">
                    <q-input
                      :model-value="manufacturerLinksDraft[props.row.manufacturer] || ''"
                      type="url"
                      :label="t('settings.inventory.manufacturerLink')"
                      outlined
                      dense
                      :placeholder="t('settings.inventory.urlPlaceholder')"
                      @update:model-value="value => updateManufacturerLink(props.row.manufacturer, value)"
                    />
                  </q-card-section>
                </q-card>
              </div>
            </template>
          </q-table>

          <q-banner
            v-if="productDefaultsValidationErrors.length"
            class="bg-warning text-dark rounded-borders q-mb-sm"
            dense
          >
            <div class="text-weight-medium q-mb-xs">{{ t('settings.inventory.fixProductDefaultsBeforeSaving') }}</div>
            <div v-for="error in productDefaultsValidationErrors" :key="error" class="text-caption">• {{ error }}</div>
          </q-banner>

          <q-btn
            color="positive"
            :label="t('settings.inventory.saveProductDefaults')"
            unelevated
            :disable="!canSaveProductDefaults"
            @click="saveProductDefaults"
          />
          <q-btn
            class="q-ml-sm"
            color="secondary"
            :label="t('settings.inventory.resetProductDefaults')"
            @click="resetProductDefaultsToDefaults"
          />

          <q-separator class="q-my-md" />

          <div class="text-subtitle2 q-mb-sm">{{ t('settings.inventory.categoryPrefillTitle') }}</div>
          <div class="text-caption text-grey-7 q-mb-sm">{{ t('settings.inventory.categoryPrefillHint') }}</div>
          <q-input
            v-model="categoryPrefillDraftText"
            type="textarea"
            autogrow
            outlined
            dense
            :rows="8"
            class="q-mb-sm"
            :label="t('settings.inventory.categoryPrefillPaths')"
            :error="categoryPrefillValidationErrors.length > 0"
            :error-message="categoryPrefillValidationErrors[0] || ''"
          />
          <q-banner
            v-if="categoryPrefillValidationErrors.length"
            class="bg-warning text-dark rounded-borders q-mb-sm"
            dense
          >
            <div class="text-weight-medium q-mb-xs">{{ t('settings.inventory.categoryPrefillIssues') }}</div>
            <div v-for="error in categoryPrefillValidationErrors" :key="error" class="text-caption">• {{ error }}</div>
          </q-banner>
          <q-banner class="bg-grey-2 text-dark rounded-borders q-mb-sm" dense>
            <div class="text-weight-medium q-mb-xs">{{ t('settings.inventory.categoryPrefillLocalizedPreview') }}</div>
            <div v-for="line in localizedCategoryPrefillPreviewLines" :key="line" class="text-caption">• {{ line }}</div>
          </q-banner>
          <div class="row q-gutter-sm q-mb-md">
            <q-btn color="secondary" :label="t('settings.inventory.resetCategoryDefaults')" @click="resetCategoryPrefillToDefaults" />
            <q-btn
              color="positive"
              :label="t('settings.inventory.saveCategoryPrefill')"
              unelevated
              :disable="!canSaveCategoryPrefill"
              @click="saveCategoryPrefill"
            />
          </div>
        </q-card>
      </q-tab-panel>

      <q-tab-panel name="integrations" class="q-pa-none">
        <q-card class="ec-card q-pa-md">
          <div class="text-subtitle1 q-mb-sm">{{ t('settings.integrations.title') }}</div>
          <div class="text-body2 q-mb-md">{{ t('settings.integrations.description') }}</div>

          <div class="row items-center justify-between q-mb-sm">
            <div class="text-subtitle2">{{ t('settings.integrations.eventoryInstances') }}</div>
            <q-btn color="secondary" icon="add" :label="t('settings.integrations.addInstance')" dense unelevated @click="addEventoryInstance" />
          </div>
          <div class="text-caption text-grey-7 q-mb-sm">{{ t('settings.integrations.eventoryInstancesHint') }}</div>

          <div
            v-for="(instance, index) in integrationsDraft.eventory_instances"
            :key="instance._draftKey || index"
            class="q-pa-sm q-mb-sm"
            style="border: 1px solid #d7dee6; border-radius: 10px"
          >
            <div class="row q-col-gutter-sm q-mb-sm">
              <div class="col-12 col-md-4">
                <q-input
                  v-model="instance.name"
                  :label="t('settings.integrations.instanceName')"
                  outlined
                  dense
                  @update:model-value="value => onEventoryInstanceNameInput(index, value)"
                />
              </div>
              <div class="col-12 col-md-4">
                <q-input
                  v-model="instance.id"
                  :label="t('settings.integrations.instanceKey')"
                  outlined
                  dense
                  :hint="t('settings.integrations.instanceKeyHint')"
                  @update:model-value="value => onEventoryInstanceIdInput(index, value)"
                  @blur="() => onEventoryInstanceIdBlur(index)"
                />
              </div>
              <div class="col-12 col-md-4 row items-center justify-end">
                <q-toggle v-model="instance.enabled" :label="t('settings.sso.enabled')" color="primary" class="q-mr-sm" />
                <q-btn flat dense icon="delete" color="negative" :disable="integrationsDraft.eventory_instances.length <= 1" @click="removeEventoryInstance(index)" />
              </div>
            </div>
            <div class="row q-col-gutter-sm q-mb-sm">
              <div class="col-12 col-md-3">
                <q-select
                  v-model="instance.sync_interval_minutes"
                  :options="integrationSyncIntervalOptions"
                  :label="t('settings.integrations.syncInterval')"
                  outlined
                  dense
                  emit-value
                  map-options
                />
              </div>
              <div class="col-12 col-md-3">
                <q-input v-model="instance.supplier_name" :label="t('settings.integrations.supplierName')" :hint="t('settings.integrations.supplierNameHint')" outlined dense />
              </div>
              <div class="col-12 col-md-3">
                <q-input v-model="instance.api_url" :label="t('settings.integrations.apiUrl')" outlined dense :placeholder="t('settings.integrations.apiUrlPlaceholder')" />
              </div>
              <div class="col-12 col-md-3">
                <q-input v-model="instance.api_key" :label="t('settings.integrations.apiKey')" outlined dense type="password" />
              </div>
              <div class="col-12 col-md-3">
                <q-input v-model="instance.username" :label="t('settings.integrations.username')" outlined dense />
              </div>
              <div class="col-12 col-md-3">
                <q-input v-model="instance.password" :label="t('settings.integrations.password')" outlined dense type="password" />
              </div>
              <div class="col-12 col-md-3">
                <q-input v-model="instance.token_endpoint" :label="t('settings.integrations.tokenEndpoint')" outlined dense :placeholder="t('settings.integrations.tokenEndpointPlaceholder')" />
              </div>
              <div class="col-12 col-md-3">
                <q-input v-model.number="instance.price_margin_percent" type="number" min="0" step="0.01" :label="t('settings.integrations.priceMarginPercent')" outlined dense />
              </div>
            </div>
            <div class="row items-center q-gutter-sm">
              <q-btn
                color="secondary"
                icon="wifi_tethering"
                :label="t('settings.integrations.testConnection')"
                unelevated
                :loading="isIntegrationTesting('eventory', instance.id)"
                @click="testIntegration('eventory', instance, instance.id)"
              />
              <q-btn
                color="primary"
                icon="preview"
                :label="t('settings.integrations.previewProducts')"
                unelevated
                :loading="isEventoryPreviewLoading(instance.id)"
                @click="previewEventoryProducts(instance.id)"
              />
              <q-btn
                color="accent"
                icon="sync"
                :label="t('settings.integrations.syncNow')"
                unelevated
                :loading="isEventorySyncLoading(instance.id)"
                @click="syncEventoryProducts(instance.id)"
              />
              <q-badge
                v-if="integrationResult('eventory', instance.id)"
                :color="integrationResult('eventory', instance.id).ok ? 'positive' : 'negative'"
                :label="integrationResult('eventory', instance.id).ok ? t('settings.integrations.connected') : t('settings.integrations.failed')"
              />
              <span v-if="integrationResult('eventory', instance.id)" class="text-caption text-grey-7">
                {{ integrationResult('eventory', instance.id).message }}
              </span>
            </div>
            <div v-if="eventoryPreviewResult(instance.id)" class="text-caption text-grey-8 q-mt-xs">
              {{ t('settings.integrations.previewCount', { count: eventoryPreviewResult(instance.id).count }) }}
            </div>
            <q-table
              v-if="eventoryPreviewResult(instance.id)?.products?.length"
              :rows="eventoryPreviewResult(instance.id).products.slice(0, 8)"
              :columns="eventoryPreviewColumns"
              row-key="id"
              dense
              flat
              bordered
              hide-pagination
              class="q-mt-sm"
            />
            <div v-if="eventorySyncResult(instance.id)" class="text-caption text-grey-8 q-mt-xs">
              {{ eventorySyncResult(instance.id).message }}
            </div>
            <q-banner
              v-if="isEventorySyncLoading(instance.id)"
              class="bg-info text-white rounded-borders q-mt-sm"
              dense
            >
              <div class="text-caption q-mb-xs">{{ eventorySyncProgressLabel(instance.id) }}</div>
              <q-linear-progress
                :value="eventorySyncProgress(instance.id) / 100"
                color="white"
                track-color="rgba(255,255,255,0.35)"
              />
            </q-banner>
            <div class="text-caption text-grey-7 q-mt-xs">
              {{ t('settings.integrations.lastSync') }}: {{ eventorySyncStamp(instance) }}
            </div>
          </div>

          <q-btn color="positive" :label="t('settings.integrations.save')" unelevated :loading="integrationsSaving" @click="saveIntegrations" />
        </q-card>
      </q-tab-panel>

      <q-tab-panel name="offline-queue" class="q-pa-none">
        <q-card class="ec-card q-pa-md">
          <div class="row items-center q-mb-sm">
            <div class="text-subtitle1 col">{{ t('settings.offlineQueue.title') }}</div>
            <q-badge :color="offlineOnline ? 'positive' : 'warning'" :label="offlineOnline ? t('settings.offlineQueue.online') : t('settings.offlineQueue.offline')" class="q-mr-sm" />
            <q-btn flat dense icon="refresh" :label="t('app.actions.refresh')" @click="loadOfflineQueue" class="q-mr-sm" />
            <q-btn color="primary" dense unelevated icon="cloud_upload" :label="t('settings.offlineQueue.flushNow')" :loading="offlineQueueFlushing" @click="flushOfflineQueueNow" class="q-mr-sm" />
            <q-btn
              color="warning"
              dense
              unelevated
              icon="replay"
              :label="t('settings.offlineQueue.retryFailed')"
              :loading="offlineQueueRetryingFailed"
              :disable="!offlineQueueFailedIds.length"
              @click="retryFailedOfflineQueue"
              class="q-mr-sm"
            />
            <q-btn
              color="deep-orange"
              dense
              unelevated
              icon="rule_folder"
              :label="t('settings.offlineQueue.clearBlocked')"
              :disable="!offlineQueueDeferredIds.length"
              @click="clearBlockedOfflineQueue"
              class="q-mr-sm"
            />
            <q-btn color="negative" dense unelevated icon="delete_sweep" :label="t('settings.offlineQueue.clearAll')" :disable="!offlineQueueRows.length" @click="clearOfflineQueueAll" />
          </div>

          <div class="row items-center q-gutter-xs q-mb-sm">
            <div class="text-caption text-grey-7 q-mr-xs">{{ t('settings.offlineQueue.policy') }}:</div>
            <q-badge color="secondary" :label="t('settings.offlineQueue.policyMerge')" />
            <q-badge color="primary" :label="t('settings.offlineQueue.policyLww')" />
            <q-badge color="warning" text-color="dark" :label="t('settings.offlineQueue.policyGuarded')" />
          </div>

          <div class="text-caption text-grey-7 q-mb-sm">
            Pending operations: {{ offlineQueueRows.length }}
            <span v-if="offlineQueueFailedIds.length"> · Failed pending retry: {{ offlineQueueFailedIds.length }}</span>
            <span v-if="offlineQueueDeferredIds.length"> · Blocked unresolved: {{ offlineQueueDeferredIds.length }}</span>
            <span v-if="offlineQueueLastResult"> · Last flush: {{ offlineQueueLastResult.flushed }} flushed, {{ offlineQueueLastResult.failed }} failed</span>
          </div>

          <q-table
            :rows="offlineQueueRows"
            :columns="offlineQueueColumns"
            row-key="id"
            flat
            bordered
            dense
            :pagination="{ rowsPerPage: 50 }"
            :rows-per-page-options="[25, 50, 100, 0]"
            class="q-mb-md"
          >
            <template #body-cell-conflictPolicy="props">
              <q-td :props="props">
                <q-badge
                  :color="props.value === 'merge' ? 'secondary' : props.value === 'guarded' ? 'warning' : 'primary'"
                  :label="props.value || t('settings.offlineQueue.defaultPolicy')"
                />
              </q-td>
            </template>
            <template #body-cell-status="props">
              <q-td :props="props">
                <q-badge :color="props.value === 'failed' ? 'negative' : props.value === 'blocked' ? 'deep-orange' : 'grey-7'" :label="props.value" />
              </q-td>
            </template>
            <template #body-cell-createdAt="props">
              <q-td :props="props">{{ formatOfflineDate(props.value) }}</q-td>
            </template>
            <template #body-cell-actions="props">
              <q-td :props="props" auto-width>
                <q-btn flat dense round icon="delete" color="negative" @click="removeOfflineQueueRow(props.row)" />
              </q-td>
            </template>
          </q-table>
        </q-card>
      </q-tab-panel>

      <q-tab-panel name="about" class="q-pa-none">
        <q-card class="ec-card q-pa-md">
          <div class="text-subtitle1 q-mb-sm">{{ t('settings.about.title') }}</div>
          <div class="text-caption text-grey-7 q-mb-md">{{ t('settings.about.description') }}</div>

          <div class="row q-col-gutter-sm q-mb-md items-center">
            <div class="col-12 col-md-6">
              <div class="text-body2 text-grey-6">{{ t('settings.about.imageTag') }}</div>
              <div class="text-h6">{{ versionInfo.image_tag || '—' }}</div>
            </div>
            <div class="col-12 col-md-6">
              <div class="text-body2 text-grey-6">{{ t('settings.about.valkeyVersion') }}</div>
              <div class="text-h6">{{ versionInfo.valkey_version || '—' }}</div>
            </div>
            <div class="col-12 col-md-6">
              <div class="text-body2 text-grey-6">{{ t('settings.about.postgresVersion') }}</div>
              <div class="text-h6">{{ versionInfo.postgres_version || '—' }}</div>
            </div>
          </div>

          <div class="row q-col-gutter-sm q-mb-md items-center">
            <div class="col-auto">
              <q-btn
                color="primary"
                icon="system_update"
                :label="t('settings.about.checkForUpdates')"
                unelevated
                :loading="versionCheckLoading"
                @click="checkForUpdates"
              />
            </div>
            <div v-if="versionCheckResult" class="col-auto">
              <q-chip
                v-if="versionCheckResult.up_to_date"
                icon="check_circle"
                color="positive"
                text-color="white"
                :label="t('settings.about.upToDate')"
              />
              <q-chip
                v-else-if="versionCheckResult.latest_version"
                icon="new_releases"
                color="warning"
                text-color="white"
                :label="t('settings.about.updateAvailable', { version: versionCheckResult.latest_version })"
              />
            </div>
            <div v-if="versionCheckError" class="col-auto text-negative text-caption">
              {{ t('settings.about.failedToCheck') }}
            </div>
          </div>

          <template v-if="safeLatestReleaseUrl">
            <q-btn
              flat
              dense
              color="primary"
              icon="open_in_new"
              :label="t('settings.about.viewRelease')"
              :href="safeLatestReleaseUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="q-mb-md"
            />
          </template>

          <template v-if="versionCheckResult">
            <div class="text-subtitle2 q-mb-sm">{{ t('settings.about.releaseNotes') }}</div>
            <q-card flat bordered class="q-pa-sm">
              <pre v-if="versionCheckResult.latest_release_notes" class="text-body2" style="white-space: pre-wrap; margin: 0">{{ versionCheckResult.latest_release_notes }}</pre>
              <div v-else class="text-caption text-grey-7">{{ t('settings.about.noReleaseNotes') }}</div>
            </q-card>
          </template>
        </q-card>
      </q-tab-panel>
    </q-tab-panels>

    <q-dialog v-model="userDialogOpen" persistent>
      <q-card style="width: 460px; max-width: 95vw" class="ec-card">
        <q-card-section>
          <div class="text-h6">{{ userEditing ? t('settings.auth.editUser') : t('settings.auth.newUser') }}</div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-form ref="userFormRef" @submit.prevent="saveUser">
            <q-input v-model="userForm.full_name" :label="t('settings.auth.fullName')" outlined dense class="q-mb-sm" :rules="[v => !!v || t('login.required')]" />
            <q-input v-model="userForm.email" :label="t('settings.auth.email')" type="email" outlined dense class="q-mb-sm" :rules="[v => !!v || t('login.required')]" />
            <q-input
              v-model="userForm.password"
              :label="userEditing ? t('settings.auth.newPasswordOptional') : t('settings.auth.password')"
              type="password"
              outlined
              dense
              class="q-mb-sm"
              :rules="userEditing ? [] : [v => !!v || t('login.required')]"
            />
            <q-select
              v-model="userForm.role"
              :options="roleOptions"
              :label="t('settings.auth.role')"
              outlined
              dense
              emit-value
              map-options
              class="q-mb-sm"
            />
            <q-toggle v-model="userForm.is_active" :label="t('settings.auth.active')" color="primary" />
            <q-banner v-if="userDialogError" class="bg-negative text-white q-mt-sm rounded-borders" dense>
              {{ userDialogError }}
            </q-banner>
          </q-form>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="userDialogOpen = false" />
          <q-btn color="primary" unelevated :loading="saving" :label="t('app.actions.save')" @click="saveUser" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="deleteUserDialogOpen" persistent>
      <q-card class="ec-card">
        <q-card-section class="row items-center">
          <q-icon name="warning" color="negative" size="md" class="q-mr-md" />
          <span>{{ t('settings.auth.deleteUserPrompt', { name: deleteUserTarget?.full_name }) }}</span>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="deleteUserDialogOpen = false" />
          <q-btn color="negative" unelevated :loading="saving" :label="t('users.delete')" @click="doDeleteUser" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="apiKeyDialogOpen" persistent>
      <q-card style="width: 460px; max-width: 95vw" class="ec-card">
        <q-card-section>
          <div class="text-h6">{{ t('settings.auth.createApiKeyTitle') }}</div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-input v-model="apiKeyForm.name" :label="t('users.keyName')" outlined dense class="q-mb-sm" />
          <div class="row items-start q-col-gutter-sm q-mb-sm">
            <div class="col">
              <q-input v-model="apiKeyForm.raw_key" :label="t('settings.auth.rawKey')" outlined dense :hint="t('settings.auth.rawKeyHint')" />
            </div>
            <q-btn dense flat icon="autorenew" color="primary" @click="generateApiKey" class="q-mt-md" />
            <q-btn dense flat icon="content_copy" color="primary" @click="copyApiKey" class="q-mt-md" />
          </div>
          <q-toggle v-model="apiKeyForm.is_admin" :label="t('settings.auth.adminKey')" color="primary" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="apiKeyDialogOpen = false" />
          <q-btn color="primary" unelevated :loading="saving" :label="t('users.create')" @click="saveApiKey" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="fieldDialogOpen" persistent>
      <q-card style="width: 560px; max-width: 95vw" class="ec-card">
        <q-card-section>
          <div class="text-h6">{{ fieldEditing ? t('settings.customFields.editField') : t('settings.customFields.newField') }}</div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-select
            v-model="fieldForm.entity_type"
            :options="entityTypeOptions"
            :label="t('settings.customFields.entityType')"
            outlined
            dense
            emit-value
            map-options
            class="q-mb-sm"
          />
          <q-input v-model="fieldForm.label" :label="t('settings.customFields.label')" outlined dense class="q-mb-sm" />
          <q-input v-model="fieldForm.key" :label="t('settings.customFields.key')" outlined dense class="q-mb-sm" :hint="t('settings.customFields.keyHint')" />
          <q-select
            v-model="fieldForm.value_type"
            :options="valueTypeOptions"
            :label="t('settings.customFields.valueType')"
            outlined
            dense
            emit-value
            map-options
            class="q-mb-sm"
          />
          <q-input
            v-model="fieldForm.options_text"
            :label="t('settings.customFields.optionsCommaSeparated')"
            outlined
            dense
            class="q-mb-sm"
          />
          <q-toggle v-model="fieldForm.is_required" :label="t('settings.customFields.required')" class="q-mb-sm" />
          <q-toggle v-model="fieldForm.is_active" :label="t('settings.auth.active')" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="fieldDialogOpen = false" />
          <q-btn color="primary" unelevated :loading="fieldDialogSaving" :label="t('app.actions.save')" @click="saveField" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'

import { api } from '../boot/axios'

import { useAuthStore } from '../stores/auth'
import { useCustomFieldsStore, CUSTOM_FIELD_ENTITY_TYPES, CUSTOM_FIELD_VALUE_TYPES } from '../stores/customFields'
import { useInventoryStore } from '../stores/inventory'
import { useJobsStore } from '../stores/jobs'
import {
  DEFAULT_AUTH_SSO_SETTINGS,
  DEFAULT_BRAND_LINKS,
  DEFAULT_BRAND_MANUFACTURER_MAP,
  DEFAULT_BRAND_OPTIONS,
  DEFAULT_CATEGORY_PREFILL_PATHS,
  DEFAULT_INTEGRATIONS,
  DEFAULT_LOCATION_TYPES,
  DEFAULT_MANUFACTURER_LINKS,
  DEFAULT_MANUFACTURER_OPTIONS,
  useSettingsStore,
} from '../stores/settings'
import { useCustomersStore } from '../stores/customers'
import { useCompactGrid } from '../composables/useCompactGrid'
import {
  clearQueuedMutations,
  flushQueuedMutations,
  isOnline,
  listQueuedMutations,
  pruneStaleBlockedQueuedMutations,
  removeQueuedMutation,
} from '../services/offline/orbitSync'
import {
  translateMaybePrefillCustomFieldLabel,
  translateMaybePrefillCustomFieldOption,
  translatePrefillCategoryLine,
} from '../i18n/prefillContent'
import {
  CURRENCY_OPTIONS,
  currencyOptionFor,
  filterCurrencyOptions,
  normalizeCurrencyCode,
} from '../constants/currencies'
import { getApiBaseUrl } from '../utils/runtime-config'

const route = useRoute()
const apiBaseUrl = getApiBaseUrl()
const knownTabs = new Set(['auth', 'company', 'custom-fields', 'inventory', 'integrations', 'offline-queue', 'about'])
const requestedTab = String(route.query.tab || '')
const tab = ref(knownTabs.has(requestedTab) ? requestedTab : 'auth')
const $q = useQuasar()
const { t } = useI18n()
const compactGrid = useCompactGrid(1024)

const authStore = useAuthStore()
const authLoading = ref(false)
const authFilter = ref('')
const roleOptions = [
  { label: t('settings.auth.roleAdmin'), value: 'admin' },
  { label: t('settings.auth.roleManager'), value: 'manager' },
  { label: t('settings.auth.roleViewer'), value: 'viewer' },
]

const authColumns = [
  { name: 'full_name', label: t('users.name'), field: 'full_name', sortable: true, align: 'left' },
  { name: 'email', label: t('settings.auth.email'), field: 'email', sortable: true, align: 'left' },
  { name: 'role', label: t('settings.auth.role'), field: 'role', sortable: true, align: 'left' },
  { name: 'is_active', label: t('settings.auth.active'), field: 'is_active', sortable: true, align: 'center' },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
]

const apiKeyColumns = [
  { name: 'name', label: t('users.name'), field: 'name', sortable: true, align: 'left' },
  { name: 'is_admin', label: t('settings.auth.scope'), field: 'is_admin', sortable: true, align: 'left' },
  { name: 'created_at', label: t('settings.auth.created'), field: 'created_at', sortable: true, align: 'left', format: v => new Date(v).toLocaleDateString() },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
]

const userDialogOpen = ref(false)
const userEditing = ref(null)
const userDialogError = ref('')
const userFormRef = ref(null)
const emptyUserForm = () => ({ full_name: '', email: '', password: '', role: 'viewer', is_active: true })
const userForm = ref(emptyUserForm())

const deleteUserDialogOpen = ref(false)
const deleteUserTarget = ref(null)

const apiKeyDialogOpen = ref(false)
const apiKeyForm = ref({ name: '', raw_key: '', is_admin: false })
const saving = ref(false)

function roleColor(role) {
  return { admin: 'negative', manager: 'warning', viewer: 'primary' }[role] ?? 'grey'
}

function openCreateUser() {
  userEditing.value = null
  userForm.value = emptyUserForm()
  userDialogError.value = ''
  userDialogOpen.value = true
}

function openEditUser(user) {
  userEditing.value = user
  userForm.value = { full_name: user.full_name, email: user.email, password: '', role: user.role, is_active: user.is_active }
  userDialogError.value = ''
  userDialogOpen.value = true
}

async function saveUser() {
  const valid = await userFormRef.value?.validate()
  if (!valid) return

  saving.value = true
  userDialogError.value = ''
  try {
    const payload = { ...userForm.value }
    if (userEditing.value && !payload.password) delete payload.password

    if (userEditing.value) {
      await authStore.updateUser(userEditing.value.id, payload)
      $q.notify({ type: 'positive', message: t('settings.auth.userUpdated') })
    } else {
      await authStore.createUser(payload)
      $q.notify({ type: 'positive', message: t('settings.auth.userCreated') })
    }
    userDialogOpen.value = false
  } catch (error) {
    userDialogError.value = error?.response?.data?.detail || t('settings.auth.failedSaveUser')
  } finally {
    saving.value = false
  }
}

function confirmDeleteUser(user) {
  deleteUserTarget.value = user
  deleteUserDialogOpen.value = true
}

async function doDeleteUser() {
  if (!deleteUserTarget.value) return
  saving.value = true
  try {
    await authStore.deleteUser(deleteUserTarget.value.id)
    deleteUserDialogOpen.value = false
    $q.notify({ type: 'positive', message: t('settings.auth.userDeleted') })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('common.deleteFailed') })
  } finally {
    saving.value = false
  }
}

function generateApiKey() {
  const array = new Uint8Array(32)
  crypto.getRandomValues(array)
  apiKeyForm.value.raw_key = 'sw_' + btoa(String.fromCharCode(...array))
    .replace(/[+/=]/g, '')
    .slice(0, 40)
}

async function copyApiKey() {
  const key = apiKeyForm.value.raw_key
  if (!key) return
  try {
    await navigator.clipboard.writeText(key)
    $q.notify({ type: 'positive', message: t('settings.auth.apiKeyCopied') })
  } catch {
    $q.notify({ type: 'negative', message: t('settings.auth.apiKeyCopyFailed') })
  }
}

function openCreateApiKey() {
  apiKeyForm.value = { name: '', raw_key: '', is_admin: false }
  generateApiKey()
  apiKeyDialogOpen.value = true
}

async function saveApiKey() {
  if (!apiKeyForm.value.name || !apiKeyForm.value.raw_key) {
    $q.notify({ type: 'warning', message: t('settings.auth.apiKeyNameRawRequired') })
    return
  }

  saving.value = true
  try {
    await authStore.createApiKey(apiKeyForm.value)
    apiKeyDialogOpen.value = false
    $q.notify({ type: 'positive', message: t('settings.auth.apiKeyCreated') })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('settings.auth.failedCreateApiKey') })
  } finally {
    saving.value = false
  }
}

async function deleteApiKey(row) {
  try {
    await authStore.deleteApiKey(row.id)
    $q.notify({ type: 'positive', message: t('settings.auth.apiKeyDisabled') })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('common.deleteFailed') })
  }
}

const customFieldsStore = useCustomFieldsStore()
const inventoryStore = useInventoryStore()
const jobsStore = useJobsStore()
const settingsStore = useSettingsStore()
const customersStore = useCustomersStore()

const locationTypeInput = ref('')
const locationTypeDraft = ref([...DEFAULT_LOCATION_TYPES])
const brandOptionInput = ref('')
const manufacturerOptionInput = ref('')
const brandOptionsDraft = ref([...DEFAULT_BRAND_OPTIONS])
const manufacturerOptionsDraft = ref([...DEFAULT_MANUFACTURER_OPTIONS])
const defaultBrandDraft = ref(DEFAULT_BRAND_OPTIONS[0])
const defaultManufacturerDraft = ref(DEFAULT_MANUFACTURER_OPTIONS[0])
const brandManufacturerMapDraft = ref({ ...DEFAULT_BRAND_MANUFACTURER_MAP })
const brandLinksDraft = ref({ ...DEFAULT_BRAND_LINKS })
const manufacturerLinksDraft = ref({ ...DEFAULT_MANUFACTURER_LINKS })
const categoryPrefillDraftText = ref('')
const integrationsDraft = ref({
  eventory_instances: DEFAULT_INTEGRATIONS.eventory_instances.map(instance => ({ ...instance })),
})
const authSsoDraft = ref({ ...DEFAULT_AUTH_SSO_SETTINGS })
const authSsoValidationError = ref('')
const authSsoSaving = ref(false)
const companyProfileDraft = ref({
  company_name: '',
  default_language: 'en',
  logo_file_id: null,
  logo_url: null,
  logo_light_wide_file_id: null,
  logo_light_wide_url: null,
  logo_light_small_file_id: null,
  logo_light_small_url: null,
  logo_dark_wide_file_id: null,
  logo_dark_wide_url: null,
  logo_dark_small_file_id: null,
  logo_dark_small_url: null,
  currency: 'SEK',
  vat_number: '',
  address_line1: '',
  address_line2: '',
  postal_code: '',
  city: '',
  country: '',
  contact_email: '',
  contact_phone: '',
  website: '',
})
const companyLogoSlots = [
  {
    key: 'default',
    label: 'Default logo',
    hint: 'Fallback if no specific theme/size logo is available.',
    usage: ['Fallback', 'Legacy pages'],
    publicVariant: 'default',
    fileIdField: 'logo_file_id',
    urlField: 'logo_url',
    category: 'logo',
  },
  {
    key: 'lightWide',
    label: 'Light wide logo',
    hint: 'Preferred on dark auth page backgrounds.',
    usage: ['Auth page'],
    publicVariant: 'light-wide',
    fileIdField: 'logo_light_wide_file_id',
    urlField: 'logo_light_wide_url',
    category: 'logo-light-wide',
  },
  {
    key: 'lightSmall',
    label: 'Light small logo',
    hint: 'Compact light variant for tight dark UI areas.',
    usage: ['Header in dark mode'],
    publicVariant: 'light-small',
    fileIdField: 'logo_light_small_file_id',
    urlField: 'logo_light_small_url',
    category: 'logo-light-small',
  },
  {
    key: 'darkWide',
    label: 'Dark wide logo',
    hint: 'Preferred on light surfaces such as labels and documents.',
    usage: ['Labels', 'Documents'],
    publicVariant: 'dark-wide',
    fileIdField: 'logo_dark_wide_file_id',
    urlField: 'logo_dark_wide_url',
    category: 'logo-dark-wide',
  },
  {
    key: 'darkSmall',
    label: 'Dark small logo',
    hint: 'Compact dark variant for light UI surfaces.',
    usage: ['Header in light mode'],
    publicVariant: 'dark-small',
    fileIdField: 'logo_dark_small_file_id',
    urlField: 'logo_dark_small_url',
    category: 'logo-dark-small',
  },
]
const companyLogoSlotByKey = Object.fromEntries(companyLogoSlots.map(slot => [slot.key, slot]))
const companyLogoFiles = ref({
  default: null,
  lightWide: null,
  lightSmall: null,
  darkWide: null,
  darkSmall: null,
})
const companyLogoUploading = ref({
  default: false,
  lightWide: false,
  lightSmall: false,
  darkWide: false,
  darkSmall: false,
})
const languageOptions = computed(() => [
  { label: t('app.language.english'), value: 'en' },
  { label: t('app.language.swedish'), value: 'sv' },
])
const companyCurrencyOptions = ref([...CURRENCY_OPTIONS])

function ensureCompanyCurrencyOption(value) {
  const option = currencyOptionFor(value)
  if (!companyCurrencyOptions.value.some(item => item.value === option.value)) {
    companyCurrencyOptions.value = [...companyCurrencyOptions.value, option]
  }
}

function filterCompanyCurrencyOptions(val, update) {
  update(() => {
    companyCurrencyOptions.value = filterCurrencyOptions(CURRENCY_OPTIONS, val)
    ensureCompanyCurrencyOption(companyProfileDraft.value.currency)
  })
}
const integrationsSaving = ref(false)
const integrationTesting = ref({
  eventoryInstances: {},
})
const integrationTestResults = ref({
  eventoryInstances: {},
})
const eventoryPreviewLoading = ref({})
const eventoryPreviewResults = ref({})
const eventorySyncLoading = ref({})
const eventorySyncResults = ref({})
const eventorySyncPollTimers = ref({})
const eventoryDraftCounter = ref(0)
const offlineQueueRows = ref([])
const offlineQueueFlushing = ref(false)
const offlineQueueRetryingFailed = ref(false)
const offlineQueueLastResult = ref(null)
const offlineQueueFailedIds = ref([])
const offlineQueueDeferredIds = ref([])

const offlineQueueFailedIdSet = computed(() => new Set(offlineQueueFailedIds.value))
const offlineQueueDeferredIdSet = computed(() => new Set(offlineQueueDeferredIds.value))

const versionCheckLoading = ref(false)
const versionCheckResult = ref(null)
const versionCheckError = ref(false)
const safeLatestReleaseUrl = computed(() => {
  const rawUrl = versionCheckResult.value?.latest_release_url
  if (typeof rawUrl !== 'string' || !rawUrl.trim()) return null
  try {
    const parsed = new URL(rawUrl)
    if (parsed.protocol !== 'https:') return null
    if (parsed.hostname !== 'github.com' && parsed.hostname !== 'www.github.com') return null
    if (parsed.username || parsed.password) return null
    return parsed.href
  } catch {
    return null
  }
})
const versionInfo = reactive({
  backend_version: null,
  image_tag: null,
  valkey_version: null,
  postgres_version: null,
})

function applyVersionInfo(data) {
  versionInfo.backend_version = data?.backend_version ?? data?.version ?? null
  versionInfo.image_tag = data?.image_tag ?? null
  versionInfo.valkey_version = data?.valkey_version ?? null
  versionInfo.postgres_version = data?.postgres_version ?? null
}

async function fetchVersionInfo() {
  try {
    const { data } = await api.get('/api/v1/settings/version')
    applyVersionInfo(data)
  } catch {
    versionInfo.backend_version = null
    versionInfo.image_tag = null
    versionInfo.valkey_version = null
    versionInfo.postgres_version = null
  }
}

async function checkForUpdates() {
  versionCheckLoading.value = true
  versionCheckError.value = false
  versionCheckResult.value = null
  try {
    const { data } = await api.get('/api/v1/settings/version', { params: { check_updates: true } })
    versionCheckResult.value = data
    applyVersionInfo(data)
  } catch {
    versionCheckError.value = true
  } finally {
    versionCheckLoading.value = false
  }
}

const offlineQueueColumns = [
  { name: 'method', label: 'Method', field: 'method', align: 'left' },
  { name: 'url', label: 'URL', field: 'url', align: 'left' },
  { name: 'conflictPolicy', label: 'Policy', field: 'conflictPolicy', align: 'left' },
  { name: 'status', label: 'Status', field: 'status', align: 'left' },
  { name: 'createdAt', label: 'Queued At', field: 'createdAt', align: 'left' },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
]

const integrationSyncIntervalOptions = [
  { label: 'Disabled', value: 0 },
  { label: '15 minutes', value: 15 },
  { label: '30 minutes', value: 30 },
  { label: '1 hour', value: 60 },
  { label: '2 hours', value: 120 },
  { label: '4 hours', value: 240 },
  { label: '8 hours', value: 480 },
  { label: '24 hours', value: 1440 },
]

const eventoryPreviewColumns = [
  { name: 'name', label: 'Name', field: 'name', align: 'left' },
  { name: 'category', label: 'Category', field: 'category', align: 'left' },
  { name: 'price', label: 'Daily Rate', field: row => Number(row.price || 0).toFixed(2), align: 'right' },
]

const offlineOnline = computed(() => isOnline())

const productDefaultsValidationErrors = computed(() => {
  const errors = []
  if (!brandOptionsDraft.value.length) {
    errors.push(t('settings.inventory.brandOptionsCannotBeEmpty'))
  }
  if (!manufacturerOptionsDraft.value.length) {
    errors.push(t('settings.inventory.manufacturerOptionsCannotBeEmpty'))
  }

  const defaultBrand = String(defaultBrandDraft.value || '').trim().toLowerCase()
  const defaultManufacturer = String(defaultManufacturerDraft.value || '').trim().toLowerCase()
  const brands = brandOptionsDraft.value.map(option => String(option || '').trim().toLowerCase())
  const manufacturers = manufacturerOptionsDraft.value.map(option => String(option || '').trim().toLowerCase())

  if (!defaultBrand) {
    errors.push(t('settings.inventory.defaultBrandRequired'))
  } else if (!brands.includes(defaultBrand)) {
    errors.push(t('settings.inventory.defaultBrandMustExist'))
  }

  if (!defaultManufacturer) {
    errors.push(t('settings.inventory.defaultManufacturerRequired'))
  } else if (!manufacturers.includes(defaultManufacturer)) {
    errors.push(t('settings.inventory.defaultManufacturerMustExist'))
  }

  return errors
})

const canSaveProductDefaults = computed(() => productDefaultsValidationErrors.value.length === 0)

const brandRows = computed(() => brandOptionsDraft.value.map(brand => ({ brand })))
const manufacturerRows = computed(() => manufacturerOptionsDraft.value.map(manufacturer => ({ manufacturer })))

const brandLinkColumns = [
  { name: 'brand', label: t('inventory.brand'), field: 'brand', align: 'left' },
  { name: 'manufacturer', label: t('settings.inventory.preferredManufacturer'), field: 'manufacturer', align: 'left' },
  { name: 'link', label: t('settings.inventory.brandLink'), field: 'link', align: 'left' },
]

const manufacturerLinkColumns = [
  { name: 'manufacturer', label: t('inventory.manufacturer'), field: 'manufacturer', align: 'left' },
  { name: 'link', label: t('settings.inventory.manufacturerLink'), field: 'link', align: 'left' },
]

const categoryPrefillValidationErrors = computed(() => {
  const errors = []
  const lines = String(categoryPrefillDraftText.value || '')
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean)

  if (!lines.length) {
    errors.push(t('settings.inventory.categoryPathRequired'))
    return errors
  }

  const malformed = []
  const duplicateLines = []
  const seen = new Set()

  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i]
    const parts = line.split('>').map(part => part.trim())
    const hasEmptySegment = parts.some(part => !part)
    if (hasEmptySegment) {
      malformed.push(i + 1)
      continue
    }

    const key = parts.map(part => part.toLowerCase()).join(' > ')
    if (seen.has(key)) {
      duplicateLines.push(i + 1)
      continue
    }
    seen.add(key)
  }

  if (malformed.length) {
    errors.push(t('settings.inventory.categoryMalformedLines', { lines: malformed.join(', ') }))
  }
  if (duplicateLines.length) {
    errors.push(t('settings.inventory.categoryDuplicateLines', { lines: duplicateLines.join(', ') }))
  }

  return errors
})

const canSaveCategoryPrefill = computed(() => categoryPrefillValidationErrors.value.length === 0)

const entityTypeOptions = computed(() => CUSTOM_FIELD_ENTITY_TYPES.map(option => ({
  ...option,
  label: t(`settings.customFields.entityType_${option.value}`),
})))
const valueTypeOptions = computed(() => CUSTOM_FIELD_VALUE_TYPES.map(option => ({
  ...option,
  label: t(`settings.customFields.valueType_${option.value}`),
})))

const activeEntityType = ref('product')

const definitionColumns = computed(() => [
  { name: 'label', label: t('settings.customFields.label'), field: 'label', sortable: true, align: 'left' },
  { name: 'key', label: t('settings.customFields.key'), field: 'key', sortable: true, align: 'left' },
  { name: 'value_type', label: t('settings.customFields.type'), field: 'value_type', sortable: true, align: 'left' },
  { name: 'is_required', label: t('settings.customFields.required'), field: 'is_required', sortable: true, align: 'left' },
  { name: 'options', label: t('settings.customFields.options'), field: 'options', sortable: false, align: 'left' },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
])

const filteredDefinitions = computed(() =>
  customFieldsStore.definitions.filter(definition => definition.entity_type === activeEntityType.value)
)

const localizedCategoryPrefillPreviewLines = computed(() => {
  const lines = String(categoryPrefillDraftText.value || '')
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean)
  return lines.map(line => translatePrefillCategoryLine(line, t))
})

function customFieldLabel(label) {
  return translateMaybePrefillCustomFieldLabel(label, t)
}

function customFieldOption(option) {
  return translateMaybePrefillCustomFieldOption(option, t)
}

function formatCustomFieldOptions(options) {
  return (options || []).map(option => customFieldOption(option)).join(', ')
}

const fieldDialogOpen = ref(false)
const fieldDialogSaving = ref(false)
const fieldEditing = ref(null)
const fieldForm = ref(emptyFieldForm())

function emptyFieldForm() {
  return {
    entity_type: 'product',
    key: '',
    label: '',
    value_type: 'text',
    options_text: '',
    is_required: false,
    is_active: true,
  }
}

function openCreateField() {
  fieldEditing.value = null
  fieldForm.value = { ...emptyFieldForm(), entity_type: activeEntityType.value }
  fieldDialogOpen.value = true
}

function openEditField(definition) {
  fieldEditing.value = definition
  fieldForm.value = {
    entity_type: definition.entity_type,
    key: definition.key,
    label: definition.label,
    value_type: definition.value_type,
    options_text: (definition.options || []).join(', '),
    is_required: !!definition.is_required,
    is_active: !!definition.is_active,
  }
  fieldDialogOpen.value = true
}

async function saveField() {
  fieldDialogSaving.value = true
  try {
    const payload = {
      entity_type: fieldForm.value.entity_type,
      key: fieldForm.value.key,
      label: fieldForm.value.label,
      value_type: fieldForm.value.value_type,
      options: fieldForm.value.options_text.split(',').map(option => option.trim()).filter(Boolean),
      is_required: !!fieldForm.value.is_required,
      is_active: !!fieldForm.value.is_active,
    }

    if (fieldEditing.value) {
      await customFieldsStore.updateDefinition(fieldEditing.value.id, payload)
      $q.notify({ type: 'positive', message: t('settings.customFields.fieldUpdated') })
    } else {
      await customFieldsStore.createDefinition(payload)
      $q.notify({ type: 'positive', message: t('settings.customFields.fieldCreated') })
    }
    fieldDialogOpen.value = false
    await loadDefinitions()
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('settings.customFields.failedSaveField') })
  } finally {
    fieldDialogSaving.value = false
  }
}

async function deleteField(definition) {
  try {
    await customFieldsStore.deleteDefinition(definition.id)
    $q.notify({ type: 'positive', message: t('settings.customFields.fieldDeleted') })
    await loadDefinitions()
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('common.deleteFailed') })
  }
}

async function prefillCableFields() {
  try {
    await customFieldsStore.prefillProductCableFields()
    await loadDefinitions()
    $q.notify({ type: 'positive', message: t('settings.customFields.cableFieldsPrefilled') })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('settings.customFields.prefillFailed') })
  }
}

async function loadDefinitions() {
  await customFieldsStore.fetchDefinitions()
}

function addLocationType() {
  const value = String(locationTypeInput.value || '').trim().toLowerCase()
  if (!value) return
  if (!locationTypeDraft.value.includes(value)) {
    locationTypeDraft.value = [...locationTypeDraft.value, value]
  }
  locationTypeInput.value = ''
}

function removeLocationType(value) {
  locationTypeDraft.value = locationTypeDraft.value.filter(item => item !== value)
}

function resetLocationTypesToDefaults() {
  locationTypeDraft.value = [...DEFAULT_LOCATION_TYPES]
}

async function saveLocationTypes() {
  try {
    const saved = await settingsStore.updateLocationTypes(locationTypeDraft.value)
    locationTypeDraft.value = [...saved]
    inventoryStore.locationTypes = [...saved]
    $q.notify({ type: 'positive', message: t('settings.inventory.locationTypesUpdated') })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('settings.inventory.failedUpdateLocationTypes') })
  }
}

function addBrandOption() {
  const value = String(brandOptionInput.value || '').trim()
  if (!value) return
  const exists = brandOptionsDraft.value.some(option => option.toLowerCase() === value.toLowerCase())
  if (!exists) {
    brandOptionsDraft.value = [...brandOptionsDraft.value, value]
  }
  if (!defaultBrandDraft.value) {
    defaultBrandDraft.value = value
  }
  brandOptionInput.value = ''
}

function removeBrandOption(value) {
  brandOptionsDraft.value = brandOptionsDraft.value.filter(item => item !== value)
  if (brandManufacturerMapDraft.value[value]) {
    const nextMap = { ...brandManufacturerMapDraft.value }
    delete nextMap[value]
    brandManufacturerMapDraft.value = nextMap
  }
  if (brandLinksDraft.value[value]) {
    const nextLinks = { ...brandLinksDraft.value }
    delete nextLinks[value]
    brandLinksDraft.value = nextLinks
  }
  if (!brandOptionsDraft.value.some(item => item === defaultBrandDraft.value)) {
    defaultBrandDraft.value = brandOptionsDraft.value[0] || null
  }
}

function addManufacturerOption() {
  const value = String(manufacturerOptionInput.value || '').trim()
  if (!value) return
  const exists = manufacturerOptionsDraft.value.some(option => option.toLowerCase() === value.toLowerCase())
  if (!exists) {
    manufacturerOptionsDraft.value = [...manufacturerOptionsDraft.value, value]
  }
  if (!defaultManufacturerDraft.value) {
    defaultManufacturerDraft.value = value
  }
  manufacturerOptionInput.value = ''
}

function removeManufacturerOption(value) {
  manufacturerOptionsDraft.value = manufacturerOptionsDraft.value.filter(item => item !== value)
  if (manufacturerLinksDraft.value[value]) {
    const nextLinks = { ...manufacturerLinksDraft.value }
    delete nextLinks[value]
    manufacturerLinksDraft.value = nextLinks
  }
  const nextMap = { ...brandManufacturerMapDraft.value }
  let changed = false
  for (const [brand, manufacturer] of Object.entries(nextMap)) {
    if (manufacturer === value) {
      delete nextMap[brand]
      changed = true
    }
  }
  if (changed) {
    brandManufacturerMapDraft.value = nextMap
  }
  if (!manufacturerOptionsDraft.value.some(item => item === defaultManufacturerDraft.value)) {
    defaultManufacturerDraft.value = manufacturerOptionsDraft.value[0] || null
  }
}

function updateBrandManufacturerMap(brand, manufacturer) {
  const next = { ...brandManufacturerMapDraft.value }
  if (!manufacturer) {
    delete next[brand]
  } else {
    next[brand] = manufacturer
  }
  brandManufacturerMapDraft.value = next
}

function updateBrandLink(brand, value) {
  const next = { ...brandLinksDraft.value }
  const normalized = String(value || '').trim()
  if (!normalized) {
    delete next[brand]
  } else {
    next[brand] = normalized
  }
  brandLinksDraft.value = next
}

function updateManufacturerLink(manufacturer, value) {
  const next = { ...manufacturerLinksDraft.value }
  const normalized = String(value || '').trim()
  if (!normalized) {
    delete next[manufacturer]
  } else {
    next[manufacturer] = normalized
  }
  manufacturerLinksDraft.value = next
}

function categoryPathsToText(paths) {
  return (paths || []).map(path => path.join(' > ')).join('\n')
}

function textToCategoryPaths(text) {
  return String(text || '')
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean)
    .map(line => line.split('>').map(part => part.trim()).filter(Boolean))
    .filter(parts => parts.length)
}

function resetCategoryPrefillToDefaults() {
  categoryPrefillDraftText.value = categoryPathsToText(DEFAULT_CATEGORY_PREFILL_PATHS)
}

async function saveCategoryPrefill() {
  if (!canSaveCategoryPrefill.value) {
    $q.notify({ type: 'warning', message: t('settings.inventory.fixCategoryPrefillValidation') })
    return
  }
  try {
    const paths = textToCategoryPaths(categoryPrefillDraftText.value)
    const saved = await settingsStore.updateCategoryPrefillPaths(paths)
    categoryPrefillDraftText.value = categoryPathsToText(saved)
    $q.notify({ type: 'positive', message: t('settings.inventory.categoryPrefillUpdated') })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('settings.inventory.failedCategoryPrefillUpdate') })
  }
}

async function saveProductDefaults() {
  if (!canSaveProductDefaults.value) {
    $q.notify({ type: 'warning', message: t('settings.inventory.fixProductDefaultsValidation') })
    return
  }
  try {
    const saved = await settingsStore.updateProductDefaults({
      brand_options: brandOptionsDraft.value,
      manufacturer_options: manufacturerOptionsDraft.value,
      default_brand: defaultBrandDraft.value,
      default_manufacturer: defaultManufacturerDraft.value,
      brand_manufacturer_map: brandManufacturerMapDraft.value,
      brand_links: brandLinksDraft.value,
      manufacturer_links: manufacturerLinksDraft.value,
    })
    brandOptionsDraft.value = [...saved.brand_options]
    manufacturerOptionsDraft.value = [...saved.manufacturer_options]
    defaultBrandDraft.value = saved.default_brand
    defaultManufacturerDraft.value = saved.default_manufacturer
    brandManufacturerMapDraft.value = { ...(saved.brand_manufacturer_map || {}) }
    brandLinksDraft.value = { ...(saved.brand_links || {}) }
    manufacturerLinksDraft.value = { ...(saved.manufacturer_links || {}) }
    $q.notify({ type: 'positive', message: t('settings.inventory.productDefaultsUpdated') })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('settings.inventory.failedUpdateProductDefaults') })
  }
}

function resetProductDefaultsToDefaults() {
  brandOptionsDraft.value = [...DEFAULT_BRAND_OPTIONS]
  manufacturerOptionsDraft.value = [...DEFAULT_MANUFACTURER_OPTIONS]
  defaultBrandDraft.value = DEFAULT_BRAND_OPTIONS[0] || null
  defaultManufacturerDraft.value = DEFAULT_MANUFACTURER_OPTIONS[0] || null
  brandManufacturerMapDraft.value = { ...DEFAULT_BRAND_MANUFACTURER_MAP }
  brandLinksDraft.value = { ...DEFAULT_BRAND_LINKS }
  manufacturerLinksDraft.value = { ...DEFAULT_MANUFACTURER_LINKS }
}

function normalizeEventoryInstanceKey(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
}

function nextEventoryDraftKey() {
  eventoryDraftCounter.value += 1
  return `eventory-draft-${eventoryDraftCounter.value}`
}

function prefillEventoryInstanceKey(nameValue, index) {
  return normalizeEventoryInstanceKey(nameValue) || `eventory-${index + 1}`
}

function withEventoryDraftMeta(instances) {
  return (instances || []).map((instance, index) => {
    const normalizedId = normalizeEventoryInstanceKey(instance.id)
    const normalizedName = String(instance.name || '').trim() || `Eventory ${index + 1}`
    const defaultId = `eventory-${index + 1}`
    const generatedFromName = prefillEventoryInstanceKey(normalizedName, index)
    const hasManualKey = !!normalizedId && normalizedId !== defaultId && normalizedId !== generatedFromName
    return {
      ...instance,
      id: normalizedId || prefillEventoryInstanceKey(normalizedName, index),
      name: normalizedName,
      _draftKey: instance._draftKey || nextEventoryDraftKey(),
      _keyManuallyEdited: Boolean(instance._keyManuallyEdited || hasManualKey),
    }
  })
}

function onEventoryInstanceNameInput(index, value) {
  const current = integrationsDraft.value.eventory_instances || []
  const instance = current[index]
  if (!instance) return

  const nextName = String(value || '')
  const nextInstances = [...current]
  const nextInstance = {
    ...instance,
    name: nextName,
  }

  if (!nextInstance._keyManuallyEdited || !String(nextInstance.id || '').trim()) {
    nextInstance.id = prefillEventoryInstanceKey(nextName, index)
  }

  nextInstances[index] = nextInstance
  integrationsDraft.value = {
    ...integrationsDraft.value,
    eventory_instances: nextInstances,
  }
}

function onEventoryInstanceIdInput(index, value) {
  const current = integrationsDraft.value.eventory_instances || []
  const instance = current[index]
  if (!instance) return

  const nextRaw = String(value || '')
  const nextInstances = [...current]
  nextInstances[index] = {
    ...instance,
    id: nextRaw,
    _keyManuallyEdited: nextRaw.trim().length > 0,
  }
  integrationsDraft.value = {
    ...integrationsDraft.value,
    eventory_instances: nextInstances,
  }
}

function onEventoryInstanceIdBlur(index) {
  const current = integrationsDraft.value.eventory_instances || []
  const instance = current[index]
  if (!instance) return

  const sanitized = normalizeEventoryInstanceKey(instance.id)
  const fallback = prefillEventoryInstanceKey(instance.name, index)
  const nextId = sanitized || fallback
  const nextInstances = [...current]
  nextInstances[index] = {
    ...instance,
    id: nextId,
    _keyManuallyEdited: Boolean(sanitized),
  }
  integrationsDraft.value = {
    ...integrationsDraft.value,
    eventory_instances: nextInstances,
  }
}

function addEventoryInstance() {
  const nextIndex = (integrationsDraft.value.eventory_instances || []).length + 1
  const name = `Eventory ${nextIndex}`
  integrationsDraft.value.eventory_instances = [
    ...(integrationsDraft.value.eventory_instances || []),
    {
      id: prefillEventoryInstanceKey(name, nextIndex - 1),
      name,
      enabled: false,
      api_url: 'https://api.eventory.se',
      api_key: '',
      username: '',
      password: '',
      token_endpoint: '',
      supplier_name: 'Eventory',
      sync_interval_minutes: 0,
      price_margin_percent: 0,
      last_sync_at: null,
      last_sync_imported: 0,
      last_sync_updated: 0,
      last_sync_skipped: 0,
      last_sync_total: 0,
      sync_running: false,
      sync_started_at: null,
      sync_finished_at: null,
      sync_progress_current: 0,
      sync_progress_total: 0,
      sync_progress_percent: 0,
      sync_message: null,
      _draftKey: nextEventoryDraftKey(),
      _keyManuallyEdited: false,
    },
  ]
}

function removeEventoryInstance(index) {
  const current = [...(integrationsDraft.value.eventory_instances || [])]
  if (current.length <= 1) return
  current.splice(index, 1)
  integrationsDraft.value.eventory_instances = current
}

function integrationResult(plugin, target = 'default') {
  if (plugin === 'eventory') {
    return integrationTestResults.value.eventoryInstances?.[target] || null
  }
  return integrationTestResults.value[plugin] || null
}

function isIntegrationTesting(plugin, target = 'default') {
  if (plugin === 'eventory') {
    return !!integrationTesting.value.eventoryInstances?.[target]
  }
  return !!integrationTesting.value[plugin]
}

function isEventoryPreviewLoading(instanceId) {
  return !!eventoryPreviewLoading.value[String(instanceId || '').trim()]
}

function isEventorySyncLoading(instanceId) {
  const key = String(instanceId || '').trim()
  if (!key) return false
  if (eventorySyncLoading.value[key]) return true
  const instance = (integrationsDraft.value.eventory_instances || []).find(item => String(item?.id || '').trim() === key)
  return Boolean(instance?.sync_running)
}

function eventoryPreviewResult(instanceId) {
  return eventoryPreviewResults.value[String(instanceId || '').trim()] || null
}

function eventorySyncResult(instanceId) {
  return eventorySyncResults.value[String(instanceId || '').trim()] || null
}

function eventorySyncStamp(instance) {
  const ts = String(instance?.last_sync_at || '').trim()
  if (!ts) return 'never'

  const parsed = new Date(ts)
  const dateText = Number.isNaN(parsed.getTime()) ? ts : parsed.toLocaleString()
  const imported = Number(instance?.last_sync_imported || 0)
  const updated = Number(instance?.last_sync_updated || 0)
  const skipped = Number(instance?.last_sync_skipped || 0)
  const total = Number(instance?.last_sync_total || 0)
  return `${dateText} (${imported} imported, ${updated} updated, ${skipped} skipped, ${total} total)`
}

function eventorySyncProgress(instanceId) {
  const key = String(instanceId || '').trim()
  if (!key) return 0
  const instance = (integrationsDraft.value.eventory_instances || []).find(item => String(item?.id || '').trim() === key)
  if (!instance) return 0

  const current = Math.max(0, Number(instance.sync_progress_current || 0))
  const total = Math.max(0, Number(instance.sync_progress_total || 0))
  const percent = Math.max(0, Math.min(100, Number(instance.sync_progress_percent || 0)))
  if (total > 0) {
    return Math.max(percent, Math.min(100, Math.round((current / total) * 100)))
  }
  return percent
}

function eventorySyncProgressLabel(instanceId) {
  const key = String(instanceId || '').trim()
  const instance = (integrationsDraft.value.eventory_instances || []).find(item => String(item?.id || '').trim() === key)
  if (!instance) return 'Sync in progress...'

  const current = Math.max(0, Number(instance.sync_progress_current || 0))
  const total = Math.max(0, Number(instance.sync_progress_total || 0))
  const percent = eventorySyncProgress(key)
  const message = String(instance.sync_message || '').trim()
  const suffix = total > 0 ? `${current}/${total}` : `${current}`
  if (message) {
    return `${message} (${percent}% • ${suffix})`
  }
  return `Sync in progress (${percent}% • ${suffix})`
}

function stopEventorySyncPolling(instanceId) {
  const key = String(instanceId || '').trim()
  if (!key) return
  const timer = eventorySyncPollTimers.value[key]
  if (timer) {
    clearInterval(timer)
    eventorySyncPollTimers.value = {
      ...eventorySyncPollTimers.value,
      [key]: null,
    }
  }
}

function applyEventorySyncStatus(instanceId, status) {
  const key = String(instanceId || '').trim()
  const currentInstances = integrationsDraft.value.eventory_instances || []
  integrationsDraft.value = {
    ...integrationsDraft.value,
    eventory_instances: currentInstances.map(instance => {
      if (String(instance?.id || '').trim() !== key) return instance
      return {
        ...instance,
        sync_running: Boolean(status?.running),
        sync_started_at: status?.started_at || instance.sync_started_at || null,
        sync_finished_at: status?.finished_at || null,
        sync_progress_current: Math.max(0, Number(status?.progress_current || 0)),
        sync_progress_total: Math.max(0, Number(status?.progress_total || 0)),
        sync_progress_percent: Math.max(0, Math.min(100, Number(status?.progress_percent || 0))),
        sync_message: status?.message || null,
        last_sync_imported: Math.max(0, Number(status?.imported || instance.last_sync_imported || 0)),
        last_sync_updated: Math.max(0, Number(status?.updated || instance.last_sync_updated || 0)),
        last_sync_skipped: Math.max(0, Number(status?.skipped || instance.last_sync_skipped || 0)),
        last_sync_total: Math.max(0, Number(status?.total || instance.last_sync_total || 0)),
        last_sync_at: status?.finished_at || instance.last_sync_at || null,
      }
    }),
  }

  if (!status?.running && status?.message) {
    eventorySyncResults.value = {
      ...eventorySyncResults.value,
      [key]: {
        imported: Math.max(0, Number(status?.imported || 0)),
        updated: Math.max(0, Number(status?.updated || 0)),
        skipped: Math.max(0, Number(status?.skipped || 0)),
        total: Math.max(0, Number(status?.total || 0)),
        message: String(status?.message || '').trim(),
      },
    }
  }
}

async function refreshEventorySyncStatus(instanceId, options = {}) {
  const key = String(instanceId || '').trim()
  if (!key) return

  try {
    const status = await settingsStore.getEventorySyncStatus(key)
    applyEventorySyncStatus(key, status)

    if (!status.running) {
      stopEventorySyncPolling(key)
      eventorySyncLoading.value = {
        ...eventorySyncLoading.value,
        [key]: false,
      }
      if (options.notifyWhenDone) {
        $q.notify({ type: 'positive', message: status.message || t('settings.integrations.syncCompleted') })
      }
    }
  } catch (error) {
    stopEventorySyncPolling(key)
    eventorySyncLoading.value = {
      ...eventorySyncLoading.value,
      [key]: false,
    }
    if (options.notifyErrors !== false) {
      const message = error?.response?.data?.detail || error?.message || t('settings.integrations.failedFetchSyncStatus')
      $q.notify({ type: 'negative', message })
    }
  }
}

function startEventorySyncPolling(instanceId, options = {}) {
  const key = String(instanceId || '').trim()
  if (!key) return
  stopEventorySyncPolling(key)

  refreshEventorySyncStatus(key, { notifyWhenDone: false, notifyErrors: options.notifyErrors !== false })

  const timer = setInterval(() => {
    refreshEventorySyncStatus(key, {
      notifyWhenDone: Boolean(options.notifyWhenDone),
      notifyErrors: options.notifyErrors !== false,
    })
  }, 2000)

  eventorySyncPollTimers.value = {
    ...eventorySyncPollTimers.value,
    [key]: timer,
  }
}

async function saveIntegrations(options = {}) {
  const silent = Boolean(options?.silent)
  const normalizedInstances = (integrationsDraft.value.eventory_instances || []).map((instance, index) => {
    const { _draftKey, _keyManuallyEdited, ...persistedFields } = instance
    return {
      ...persistedFields,
      id: normalizeEventoryInstanceKey(instance.id) || prefillEventoryInstanceKey(instance.name, index),
      name: String(instance.name || '').trim() || `Eventory ${index + 1}`,
    }
  })

  integrationsSaving.value = true
  try {
    const saved = await settingsStore.updateIntegrations({
      ...integrationsDraft.value,
      eventory_instances: normalizedInstances.length ? normalizedInstances : [{ ...DEFAULT_INTEGRATIONS.eventory_instances[0] }],
    })
    integrationsDraft.value = {
      eventory_instances: withEventoryDraftMeta((saved.eventory_instances || DEFAULT_INTEGRATIONS.eventory_instances).map(instance => ({ ...instance }))),
    }
    if (!silent) {
      $q.notify({ type: 'positive', message: t('settings.integrations.updated') })
    }
    return true
  } catch (error) {
    if (!silent) {
      $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('settings.integrations.failedSave') })
    }
    return false
  } finally {
    integrationsSaving.value = false
  }
}

function formatJson(value) {
  try {
    return JSON.stringify(value ?? {}, null, 2)
  } catch {
    return '{}'
  }
}

function nextSsoDraftKey(prefix) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function emptyGroupRoleRow() {
  return { group: '', role: 'viewer' }
}

function emptyOidcProvider() {
  return {
    _draftKey: nextSsoDraftKey('oidc'),
    key: '',
    display_name: '',
    enabled: true,
    allow_auto_create: false,
    issuer: '',
    client_id: '',
    client_secret: '',
    authorization_endpoint: '',
    token_endpoint: '',
    jwks_uri: '',
    scopes: 'openid profile email',
    group_claim: 'groups',
    email_claim: 'email',
    name_claim: 'name',
    subject_claim: 'sub',
  }
}

function emptySamlProvider() {
  return {
    _draftKey: nextSsoDraftKey('saml'),
    key: '',
    display_name: '',
    enabled: true,
    allow_auto_create: false,
    idp_entity_id: '',
    idp_sso_url: '',
    idp_x509_cert: '',
    sp_entity_id: '',
    acs_url: '',
    group_attribute: 'groups',
    email_attribute: 'email',
    name_attribute: 'displayName',
    subject_attribute: 'nameid',
  }
}

function applyAuthSsoDraft(settings) {
  const normalized = settingsStore.normalizeAuthSsoSettings(settings || DEFAULT_AUTH_SSO_SETTINGS)

  const groupRows = Object.entries(normalized.group_role_map || {}).map(([group, role]) => ({
    group,
    role,
  }))

  authSsoDraft.value = {
    ...normalized,
    group_role_rows: groupRows,
    oidc_providers: (normalized.oidc_providers || []).map(item => ({ ...emptyOidcProvider(), ...item, _draftKey: nextSsoDraftKey('oidc') })),
    saml_providers: (normalized.saml_providers || []).map(item => ({ ...emptySamlProvider(), ...item, _draftKey: nextSsoDraftKey('saml') })),
  }
}

function addGroupRoleRow() {
  authSsoDraft.value.group_role_rows = [...(authSsoDraft.value.group_role_rows || []), emptyGroupRoleRow()]
}

function removeGroupRoleRow(index) {
  const rows = [...(authSsoDraft.value.group_role_rows || [])]
  rows.splice(index, 1)
  authSsoDraft.value.group_role_rows = rows
}

function addOidcProvider() {
  authSsoDraft.value.oidc_providers = [...(authSsoDraft.value.oidc_providers || []), emptyOidcProvider()]
}

function removeOidcProvider(index) {
  const rows = [...(authSsoDraft.value.oidc_providers || [])]
  rows.splice(index, 1)
  authSsoDraft.value.oidc_providers = rows
}

function addSamlProvider() {
  authSsoDraft.value.saml_providers = [...(authSsoDraft.value.saml_providers || []), emptySamlProvider()]
}

function removeSamlProvider(index) {
  const rows = [...(authSsoDraft.value.saml_providers || [])]
  rows.splice(index, 1)
  authSsoDraft.value.saml_providers = rows
}

function sanitizeProviderKey(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
}

function normalizeProviders(rows, kind) {
  const out = []
  const seen = new Set()
  for (const row of rows || []) {
    const key = sanitizeProviderKey(row?.key)
    if (!key) continue
    if (seen.has(key)) throw new Error(`${kind} provider keys must be unique`)
    seen.add(key)
    const normalized = {
      ...row,
      key,
      display_name: String(row?.display_name || '').trim() || key,
    }
    delete normalized._draftKey
    out.push(normalized)
  }
  return out
}

async function saveAuthSsoSettings() {
  authSsoValidationError.value = ''
  authSsoSaving.value = true
  try {
    const groupRoleMap = {}
    for (const row of authSsoDraft.value.group_role_rows || []) {
      const group = String(row?.group || '').trim()
      const role = String(row?.role || '').trim().toLowerCase()
      if (!group) continue
      if (!['admin', 'manager', 'viewer'].includes(role)) {
        throw new Error(`Invalid role mapping for group ${group}`)
      }
      groupRoleMap[group] = role
    }

    const oidcProviders = normalizeProviders(authSsoDraft.value.oidc_providers || [], 'OIDC')
    const samlProviders = normalizeProviders(authSsoDraft.value.saml_providers || [], 'SAML')

    const saved = await settingsStore.updateAuthSsoSettings({
      enabled: !!authSsoDraft.value.enabled,
      auto_create_users: !!authSsoDraft.value.auto_create_users,
      sync_roles_on_login: !!authSsoDraft.value.sync_roles_on_login,
      default_role: authSsoDraft.value.default_role,
      group_role_map: groupRoleMap,
      oidc_providers: oidcProviders,
      saml_providers: samlProviders,
    })
    applyAuthSsoDraft(saved)
    $q.notify({ type: 'positive', message: t('settings.sso.updated') })
  } catch (error) {
    authSsoValidationError.value = error?.response?.data?.detail || error?.message || t('settings.sso.failedSave')
    $q.notify({ type: 'negative', message: authSsoValidationError.value })
  } finally {
    authSsoSaving.value = false
  }
}

function applyCompanyProfileDraft(profile) {
  companyProfileDraft.value = {
    company_name: String(profile?.company_name || '').trim(),
    default_language: ['en', 'sv'].includes(String(profile?.default_language || '').trim().toLowerCase())
      ? String(profile?.default_language || '').trim().toLowerCase()
      : 'en',
    logo_file_id: Number(profile?.logo_file_id || 0) || null,
    logo_url: String(profile?.logo_url || '').trim() || null,
    logo_light_wide_file_id: Number(profile?.logo_light_wide_file_id || 0) || null,
    logo_light_wide_url: String(profile?.logo_light_wide_url || '').trim() || null,
    logo_light_small_file_id: Number(profile?.logo_light_small_file_id || 0) || null,
    logo_light_small_url: String(profile?.logo_light_small_url || '').trim() || null,
    logo_dark_wide_file_id: Number(profile?.logo_dark_wide_file_id || 0) || null,
    logo_dark_wide_url: String(profile?.logo_dark_wide_url || '').trim() || null,
    logo_dark_small_file_id: Number(profile?.logo_dark_small_file_id || 0) || null,
    logo_dark_small_url: String(profile?.logo_dark_small_url || '').trim() || null,
    currency: normalizeCurrencyCode(profile?.currency, 'SEK'),
    vat_number: String(profile?.vat_number || '').trim(),
    address_line1: String(profile?.address_line1 || '').trim(),
    address_line2: String(profile?.address_line2 || '').trim(),
    postal_code: String(profile?.postal_code || '').trim(),
    city: String(profile?.city || '').trim(),
    country: String(profile?.country || '').trim(),
    contact_email: String(profile?.contact_email || '').trim(),
    contact_phone: String(profile?.contact_phone || '').trim(),
    website: String(profile?.website || '').trim(),
  }
  ensureCompanyCurrencyOption(companyProfileDraft.value.currency)
}

async function uploadCompanyLogo(slotKey) {
  const slot = companyLogoSlotByKey[slotKey]
  if (!slot) return
  const file = companyLogoFiles.value[slotKey]
  if (!file) {
    $q.notify({ type: 'warning', message: t('settings.company.selectLogoFirst') })
    return
  }

  companyLogoUploading.value[slotKey] = true
  try {
    const uploaded = await settingsStore.uploadStorageFile({
      file,
      entityType: 'company',
      category: slot.category,
    })
    companyProfileDraft.value[slot.fileIdField] = Number(uploaded?.id || 0) || null
    companyProfileDraft.value[slot.urlField] = String(uploaded?.download_url || '').trim() || null
    companyLogoFiles.value[slotKey] = null
    $q.notify({ type: 'positive', message: t('settings.company.logoUploaded', { slot: slot.label }) })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('settings.company.logoUploadFailed') })
  } finally {
    companyLogoUploading.value[slotKey] = false
  }
}

function clearCompanyLogoSlot(slotKey) {
  const slot = companyLogoSlotByKey[slotKey]
  if (!slot) return
  companyProfileDraft.value[slot.fileIdField] = null
  companyProfileDraft.value[slot.urlField] = null
  companyLogoFiles.value[slotKey] = null
}

function resolveAssetUrl(value) {
  const raw = String(value || '').trim()
  if (!raw) return ''
  if (/^(https?:|data:|blob:)/i.test(raw)) return raw
  if (raw.startsWith('/')) return `${apiBaseUrl}${raw}`
  return `${apiBaseUrl}/${raw}`
}

function currentCompanyLogoPreviewUrl(slot) {
  if (!slot || !slot.fileIdField) return ''
  const fileId = Number(companyProfileDraft.value?.[slot.fileIdField] || 0)
  if (!fileId) return ''
  if (slot.publicVariant === 'default') {
    return `${apiBaseUrl}/api/v1/storage/public/company-logo?v=${fileId}`
  }
  return `${apiBaseUrl}/api/v1/storage/public/company-logo/${encodeURIComponent(slot.publicVariant)}?v=${fileId}`
}

async function saveCompanyProfile() {
  try {
    companyProfileDraft.value.currency = normalizeCurrencyCode(companyProfileDraft.value.currency, 'SEK')
    const saved = await settingsStore.updateCompanyProfile({
      company_name: companyProfileDraft.value.company_name,
      default_language: companyProfileDraft.value.default_language,
      logo_file_id: companyProfileDraft.value.logo_file_id,
      logo_light_wide_file_id: companyProfileDraft.value.logo_light_wide_file_id,
      logo_light_small_file_id: companyProfileDraft.value.logo_light_small_file_id,
      logo_dark_wide_file_id: companyProfileDraft.value.logo_dark_wide_file_id,
      logo_dark_small_file_id: companyProfileDraft.value.logo_dark_small_file_id,
      currency: companyProfileDraft.value.currency,
      vat_number: companyProfileDraft.value.vat_number,
      address_line1: companyProfileDraft.value.address_line1,
      address_line2: companyProfileDraft.value.address_line2,
      postal_code: companyProfileDraft.value.postal_code,
      city: companyProfileDraft.value.city,
      country: companyProfileDraft.value.country,
      contact_email: companyProfileDraft.value.contact_email,
      contact_phone: companyProfileDraft.value.contact_phone,
      website: companyProfileDraft.value.website,
    })
    applyCompanyProfileDraft(saved)
    $q.notify({ type: 'positive', message: t('settings.company.saved') })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('settings.company.failedSave') })
  }
}

function findEventoryInstanceByKey(instanceId) {
  const raw = String(instanceId || '').trim()
  const normalized = normalizeEventoryInstanceKey(raw)
  return (integrationsDraft.value.eventory_instances || []).find((instance) => {
    const candidate = String(instance.id || '').trim()
    return candidate === raw || normalizeEventoryInstanceKey(candidate) === normalized
  }) || null
}

async function ensureEventoryInstancePersisted(instanceId) {
  const instance = findEventoryInstanceByKey(instanceId)
  if (!instance) return normalizeEventoryInstanceKey(instanceId)

  const normalizedKey = normalizeEventoryInstanceKey(instance.id)
  if (!normalizedKey) return ''

  if (String(instance.id || '').trim() !== normalizedKey) {
    instance.id = normalizedKey
  }

  const ok = await saveIntegrations({ silent: true })
  if (!ok) {
    throw new Error('Please save integration settings before previewing or syncing products')
  }

  return normalizedKey
}

async function testIntegration(plugin, config = null, target = 'default') {
  const pluginKey = String(plugin || '').trim().toLowerCase()
  if (!pluginKey) return

  const sourceConfig = config || integrationsDraft.value[pluginKey]
  if (!sourceConfig) return

  if (pluginKey === 'eventory') {
    integrationTesting.value = {
      ...integrationTesting.value,
      eventoryInstances: {
        ...(integrationTesting.value.eventoryInstances || {}),
        [target]: true,
      },
    }
  } else {
    integrationTesting.value = {
      ...integrationTesting.value,
      [pluginKey]: true,
    }
  }

  try {
    const result = await settingsStore.testIntegrationConnection(pluginKey, sourceConfig)
    if (pluginKey === 'eventory') {
      integrationTestResults.value = {
        ...integrationTestResults.value,
        eventoryInstances: {
          ...(integrationTestResults.value.eventoryInstances || {}),
          [target]: result,
        },
      }
    } else {
      integrationTestResults.value = {
        ...integrationTestResults.value,
        [pluginKey]: result,
      }
    }
    $q.notify({
      type: result.ok ? 'positive' : 'warning',
      message: `${pluginKey}${pluginKey === 'eventory' ? ` (${target})` : ''} test: ${result.message}`,
    })
  } catch (error) {
    const message = error?.response?.data?.detail || error?.message || t('settings.integrations.connectionTestFailed')
    if (pluginKey === 'eventory') {
      integrationTestResults.value = {
        ...integrationTestResults.value,
        eventoryInstances: {
          ...(integrationTestResults.value.eventoryInstances || {}),
          [target]: { ok: false, message },
        },
      }
    } else {
      integrationTestResults.value = {
        ...integrationTestResults.value,
        [pluginKey]: { ok: false, message },
      }
    }
    $q.notify({ type: 'negative', message })
  } finally {
    if (pluginKey === 'eventory') {
      integrationTesting.value = {
        ...integrationTesting.value,
        eventoryInstances: {
          ...(integrationTesting.value.eventoryInstances || {}),
          [target]: false,
        },
      }
    } else {
      integrationTesting.value = {
        ...integrationTesting.value,
        [pluginKey]: false,
      }
    }
  }
}

async function previewEventoryProducts(instanceId) {
  const key = await ensureEventoryInstancePersisted(instanceId)
  if (!key) return

  eventoryPreviewLoading.value = {
    ...eventoryPreviewLoading.value,
    [key]: true,
  }

  try {
    const result = await settingsStore.previewEventoryProducts(key)
    eventoryPreviewResults.value = {
      ...eventoryPreviewResults.value,
      [key]: result,
    }
    $q.notify({ type: 'positive', message: t('settings.integrations.previewLoaded', { count: result.count }) })
  } catch (error) {
    const message = error?.response?.data?.detail || error?.message || t('settings.integrations.failedPreviewProducts')
    $q.notify({ type: 'negative', message })
  } finally {
    eventoryPreviewLoading.value = {
      ...eventoryPreviewLoading.value,
      [key]: false,
    }
  }
}

async function syncEventoryProducts(instanceId) {
  const key = await ensureEventoryInstancePersisted(instanceId)
  if (!key) return

  eventorySyncLoading.value = {
    ...eventorySyncLoading.value,
    [key]: true,
  }

  try {
    const result = await settingsStore.syncEventoryProducts(key)

    if (!result.started) {
      eventorySyncLoading.value = {
        ...eventorySyncLoading.value,
        [key]: false,
      }
      await refreshEventorySyncStatus(key, { notifyWhenDone: false })
      $q.notify({ type: 'info', message: result.message || t('settings.integrations.syncAlreadyRunning') })
      return
    }

    startEventorySyncPolling(key, { notifyWhenDone: true, notifyErrors: true })
    $q.notify({ type: 'info', message: result.message || t('settings.integrations.syncStarted') })
  } catch (error) {
    const message = error?.response?.data?.detail || error?.message || t('settings.integrations.failedSyncProducts')
    $q.notify({ type: 'negative', message })
    eventorySyncLoading.value = {
      ...eventorySyncLoading.value,
      [key]: false,
    }
  } finally {
    // loading is cleared by polling when sync completes
  }
}

function formatOfflineDate(value) {
  if (!value) return '-'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return String(value)
  return parsed.toLocaleString()
}

async function loadOfflineQueue() {
  await pruneStaleBlockedQueuedMutations()
  const rows = await listQueuedMutations()
  const existingIds = new Set(rows.map(row => row.id))
  offlineQueueFailedIds.value = offlineQueueFailedIds.value.filter(id => existingIds.has(id))
  offlineQueueDeferredIds.value = offlineQueueDeferredIds.value.filter(id => existingIds.has(id))
  offlineQueueRows.value = rows.map(row => ({
    ...row,
    status: offlineQueueFailedIdSet.value.has(row.id)
      ? 'failed'
      : offlineQueueDeferredIdSet.value.has(row.id)
        ? 'blocked'
        : 'pending',
  }))
}

async function removeOfflineQueueRow(row) {
  if (!row?.id) return
  await removeQueuedMutation(row.id)
  offlineQueueFailedIds.value = offlineQueueFailedIds.value.filter(id => id !== row.id)
  offlineQueueDeferredIds.value = offlineQueueDeferredIds.value.filter(id => id !== row.id)
  await loadOfflineQueue()
  $q.notify({ type: 'positive', message: t('settings.offlineQueue.queuedOperationRemoved') })
}

async function clearOfflineQueueAll() {
  await clearQueuedMutations()
  offlineQueueFailedIds.value = []
  offlineQueueDeferredIds.value = []
  await loadOfflineQueue()
  $q.notify({ type: 'positive', message: t('settings.offlineQueue.cleared') })
}

async function clearBlockedOfflineQueue() {
  if (!offlineQueueDeferredIds.value.length) {
    $q.notify({ type: 'info', message: t('settings.offlineQueue.noBlockedToClear') })
    return
  }

  const blockedSet = new Set(offlineQueueDeferredIds.value)
  const rows = await listQueuedMutations()
  const blockedRows = rows.filter(row => blockedSet.has(row.id))
  for (const row of blockedRows) {
    if (!row?.id) continue
    await removeQueuedMutation(row.id)
  }
  offlineQueueDeferredIds.value = []
  offlineQueueFailedIds.value = offlineQueueFailedIds.value.filter(id => !blockedSet.has(id))
  await loadOfflineQueue()
  $q.notify({ type: 'positive', message: t('settings.offlineQueue.clearedBlocked', { count: blockedRows.length }) })
}

async function flushOfflineQueueNow() {
  offlineQueueFlushing.value = true
  try {
    const result = await flushQueuedMutations(async (mutation) => {
      await api.request({
        method: mutation.method,
        url: mutation.url,
        data: mutation.data,
        params: mutation.params,
      })
    })
    offlineQueueFailedIds.value = result.failedIds || []
    offlineQueueDeferredIds.value = result.deferredIds || []
    offlineQueueLastResult.value = result
    await loadOfflineQueue()
    $q.notify({
      type: (result.failed || result.deferred) ? 'warning' : 'positive',
      message: t('settings.offlineQueue.flushComplete', { flushed: result.flushed, failed: result.failed, blocked: result.deferred || 0, pruned: result.pruned || 0 }),
    })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.message || t('settings.offlineQueue.flushFailed') })
  } finally {
    offlineQueueFlushing.value = false
  }
}

async function retryFailedOfflineQueue() {
  if (!offlineQueueFailedIds.value.length) {
    $q.notify({ type: 'info', message: t('settings.offlineQueue.noFailedToRetry') })
    return
  }

  offlineQueueRetryingFailed.value = true
  try {
    const failedSet = new Set(offlineQueueFailedIds.value)
    const queueRows = await listQueuedMutations()
    const retryRows = queueRows.filter(row => failedSet.has(row.id))
    let flushed = 0
    let failed = 0
    const failedIds = []

    for (const mutation of retryRows) {
      try {
        await api.request({
          method: mutation.method,
          url: mutation.url,
          data: mutation.data,
          params: mutation.params,
        })
        await removeQueuedMutation(mutation.id)
        flushed += 1
      } catch {
        failed += 1
        failedIds.push(mutation.id)
      }
    }

    offlineQueueFailedIds.value = failedIds
    offlineQueueDeferredIds.value = offlineQueueDeferredIds.value.filter(id => failedIds.includes(id))
    offlineQueueLastResult.value = { flushed, failed }
    await loadOfflineQueue()
    $q.notify({ type: failed ? 'warning' : 'positive', message: t('settings.offlineQueue.retryComplete', { flushed, failed }) })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.message || t('settings.offlineQueue.retryFailedMessage') })
  } finally {
    offlineQueueRetryingFailed.value = false
  }
}

onMounted(async () => {
  authLoading.value = true
  try {
    await Promise.all([
      authStore.fetchUsers(),
      authStore.fetchApiKeys(),
      loadDefinitions(),
      inventoryStore.fetchAll(),
      settingsStore.fetchLocationTypes(),
      settingsStore.fetchCategoryPrefillPaths(),
      settingsStore.fetchProductDefaults(),
      settingsStore.fetchIntegrations(),
      settingsStore.fetchAuthSsoSettings(),
      settingsStore.fetchCompanyProfile(),
      jobsStore.fetchAll(),
      customersStore.fetchAll(),
      fetchVersionInfo(),
    ])
    locationTypeDraft.value = [...settingsStore.locationTypes]
    brandOptionsDraft.value = [...settingsStore.brandOptions]
    manufacturerOptionsDraft.value = [...settingsStore.manufacturerOptions]
    defaultBrandDraft.value = settingsStore.defaultBrand
    defaultManufacturerDraft.value = settingsStore.defaultManufacturer
    brandManufacturerMapDraft.value = { ...(settingsStore.brandManufacturerMap || {}) }
    brandLinksDraft.value = { ...(settingsStore.brandLinks || {}) }
    manufacturerLinksDraft.value = { ...(settingsStore.manufacturerLinks || {}) }
    categoryPrefillDraftText.value = categoryPathsToText(settingsStore.categoryPrefillPaths)
    integrationsDraft.value = {
      eventory_instances: withEventoryDraftMeta((settingsStore.integrations?.eventory_instances || DEFAULT_INTEGRATIONS.eventory_instances).map(instance => ({ ...instance }))),
    }
    applyAuthSsoDraft(settingsStore.authSsoSettings)
    for (const instance of integrationsDraft.value.eventory_instances || []) {
      if (instance?.sync_running) {
        const key = String(instance?.id || '').trim()
        if (!key) continue
        eventorySyncLoading.value = {
          ...eventorySyncLoading.value,
          [key]: true,
        }
        startEventorySyncPolling(key, { notifyWhenDone: false, notifyErrors: false })
      }
    }
    applyCompanyProfileDraft(settingsStore.companyProfile)
    await loadOfflineQueue()
  } finally {
    authLoading.value = false
  }
})

onBeforeUnmount(() => {
  for (const timer of Object.values(eventorySyncPollTimers.value || {})) {
    if (timer) clearInterval(timer)
  }
})
</script>
