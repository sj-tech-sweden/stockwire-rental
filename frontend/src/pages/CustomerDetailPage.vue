<template>
  <q-page class="q-pa-md ec-page">
    <div class="row items-center justify-between q-col-gutter-sm q-mb-md">
      <div class="col-auto">
        <q-btn flat icon="arrow_back" :label="t('customers.backToCustomers')" @click="goBack" />
      </div>
      <div class="col">
        <div class="text-h5">{{ isNewCustomer ? t('customers.newCustomer') : (currentCustomer?.name || t('customers.title')) }}</div>
      </div>
      <div class="col-auto row q-gutter-sm">
        <q-btn v-if="!isNewCustomer && authStore.canEdit" color="negative" outline icon="delete" :label="t('customers.delete')" @click="confirmDelete" />
        <q-btn v-if="authStore.canEdit" color="primary" unelevated :label="isNewCustomer ? t('customers.create') : t('app.actions.save')" :loading="saving" @click="isNewCustomer ? createCustomer() : saveChanges()" />
      </div>
    </div>

    <div v-if="pageLoading" class="row justify-center q-py-xl">
      <q-spinner color="primary" size="48px" />
    </div>

    <div v-else-if="!isNewCustomer && !currentCustomer" class="q-gutter-md">
      <q-banner class="bg-warning text-dark rounded-borders">
        {{ t('customers.notFound') }}
      </q-banner>
      <q-btn color="primary" unelevated :label="t('customers.backToCustomers')" @click="goBack" />
    </div>

    <div v-else class="column q-gutter-md">
      <q-card class="ec-card">
        <q-card-section>
          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-auto" v-if="form.is_customer">
              <q-badge color="primary" :label="t('customers.types.customer')" />
            </div>
            <div class="col-auto" v-if="form.is_product_supplier">
              <q-badge color="teal" :label="t('customers.types.productSupplier')" />
            </div>
            <div class="col-auto" v-if="form.is_rental_supplier">
              <q-badge color="orange" :label="t('customers.types.rentalSupplier')" />
            </div>
            <div class="col-auto" v-if="form.is_crew_supplier">
              <q-badge color="purple" :label="t('customers.types.crewSupplier')" />
            </div>
          </div>
          <div class="text-body1 q-mb-xs">{{ form.name || t('customers.noName') }}</div>
          <div class="text-caption text-grey-7" v-if="form.email">{{ form.email }}</div>
          <div class="text-caption text-grey-7" v-if="form.phone">{{ form.phone }}</div>
          <div class="text-caption text-grey-7" v-if="form.address || form.city">
            {{ [form.address, form.postal_code, form.city, form.country].filter(Boolean).join(', ') }}
          </div>
          <div class="text-caption text-grey-7" v-if="!isNewCustomer">{{ t('customers.createdAt') }}: {{ formatDate(currentCustomer?.created_at) }}</div>
          <q-btn
            v-if="twentyCustomerUrl"
            flat
            dense
            no-caps
            color="primary"
            icon="open_in_new"
            :label="t('customers.openInTwenty')"
            :href="twentyCustomerUrl"
            target="_blank"
            class="q-mt-sm"
          />
        </q-card-section>
      </q-card>

      <q-card class="ec-card">
        <q-card-section class="row items-center justify-between q-col-gutter-sm">
          <div class="col">
            <div class="text-h6">{{ isNewCustomer ? t('customers.newCustomer') : t('customers.editCustomer') }}</div>
          </div>
          <div class="col-auto" v-if="authStore.canEdit && !isNewCustomer">
            <q-btn color="primary" unelevated :label="t('app.actions.save')" :loading="saving" @click="saveChanges" />
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-form ref="formRef" @submit.prevent="isNewCustomer ? createCustomer() : saveChanges()">
            <div class="row q-col-gutter-sm">
              <div class="col-12 col-md-6">
                <q-input
                  v-model="form.name"
                  :label="t('customers.name')"
                  outlined
                  dense
                  :disable="!authStore.canEdit"
                  :rules="[v => !!v || t('common.required')]"
                />
              </div>
              <div class="col-12 col-md-6">
                <q-input v-model="form.email" :label="t('profile.email')" type="email" outlined dense :disable="!authStore.canEdit" />
              </div>
            </div>

            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-12 col-md-6">
                <q-input v-model="form.phone" :label="t('customers.phone')" outlined dense :disable="!authStore.canEdit" />
              </div>
              <div class="col-12 col-md-6">
                <q-input v-model="form.address" :label="t('customers.address')" outlined dense :disable="!authStore.canEdit" />
              </div>
            </div>

            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-12 col-md-5">
                <q-input v-model="form.city" :label="t('customers.city')" outlined dense :disable="!authStore.canEdit" />
              </div>
              <div class="col-12 col-md-3">
                <q-input v-model="form.postal_code" :label="t('customers.postalCode')" outlined dense :disable="!authStore.canEdit" />
              </div>
              <div class="col-12 col-md-4">
                <q-select
                  v-model="form.country"
                  :options="COUNTRIES"
                  :label="t('customers.country')"
                  outlined
                  dense
                  clearable
                  emit-value
                  map-options
                  :disable="!authStore.canEdit"
                />
              </div>
            </div>

            <q-input
              v-model="form.notes"
              :label="t('customers.notes')"
              type="textarea"
              autogrow
              outlined
              dense
              class="q-mt-sm"
              :disable="!authStore.canEdit"
            />

            <div class="q-mt-sm">
              <q-toggle
                v-model="form.email_notifications_enabled"
                :label="t('customers.emailNotificationsEnabled')"
                :disable="!authStore.canEdit"
              />
            </div>

            <q-select
              v-model="form.preferred_language"
              :options="languageOptions"
              :label="t('customers.preferredLanguage')"
              emit-value
              map-options
              outlined
              dense
              class="q-mt-sm"
              :disable="!authStore.canEdit"
            />

            <q-separator class="q-my-md" />
            <div class="text-subtitle2 q-mb-sm">{{ t('customers.supplierTypes') }}</div>
            <div class="row q-col-gutter-sm">
              <div class="col-6 col-md-3">
                <q-checkbox v-model="form.is_customer" :label="t('customers.isCustomer')" :disable="!authStore.canEdit" />
              </div>
              <div class="col-6 col-md-3">
                <q-checkbox v-model="form.is_product_supplier" :label="t('customers.isProductSupplier')" :disable="!authStore.canEdit" />
              </div>
              <div class="col-6 col-md-3">
                <q-checkbox v-model="form.is_rental_supplier" :label="t('customers.isRentalSupplier')" :disable="!authStore.canEdit" />
              </div>
              <div class="col-6 col-md-3">
                <q-checkbox v-model="form.is_crew_supplier" :label="t('customers.isCrewSupplier')" :disable="!authStore.canEdit" />
              </div>
            </div>
          </q-form>
        </q-card-section>
      </q-card>

      <q-card class="ec-card">
        <q-card-section class="row items-center justify-between q-col-gutter-sm">
          <div class="col">
            <div class="text-subtitle2">{{ t('customers.customFieldValues') }}</div>
          </div>
          <div class="col-auto" v-if="authStore.canEdit">
            <q-btn flat dense no-caps color="primary" icon="edit" :label="t('customers.editCustomFields')" @click="customFieldsDialogOpen = true" />
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none" v-if="customerFieldRows.length">
          <q-list bordered separator class="rounded-borders">
            <q-item v-for="field in customerFieldRows" :key="field.field_definition_id">
              <q-item-section>
                <q-item-label>{{ customFieldLabel(field.label) }}</q-item-label>
                <q-item-label caption>{{ formatFieldValue(field) }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
        <q-card-section class="q-pt-none" v-else>
          <div class="text-caption text-grey-7">{{ t('customers.noCustomFields') }}</div>
        </q-card-section>
      </q-card>

      <template v-if="!isNewCustomer && info">
        <q-card v-if="form.is_customer" class="ec-card">
          <q-card-section class="row items-center justify-between q-col-gutter-sm">
            <div class="col">
              <div class="text-subtitle2">{{ t('customers.linkedJobs') }}</div>
              <div class="text-caption text-grey-7">{{ info.jobs?.length || 0 }} {{ t('customers.linkedJobs').toLowerCase() }}</div>
            </div>
          </q-card-section>
          <q-card-section class="q-pt-none">
            <template v-if="info.jobs?.length">
              <q-list bordered separator class="rounded-borders">
                <q-item v-for="job in info.jobs" :key="`job-${job.id}`" clickable @click="router.push(`/jobs/${job.id}`)">
                  <q-item-section>
                    <q-item-label>{{ job.job_code }}</q-item-label>
                    <q-item-label caption>
                      {{ job.venue_name || '-' }} · {{ job.description || t('jobs.noDescription') }}
                    </q-item-label>
                    <q-item-label caption v-if="job.start_date || job.end_date">
                      {{ formatDate(job.start_date) }} → {{ formatDate(job.end_date) }}
                    </q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <div class="row items-center no-wrap q-gutter-xs">
                      <q-badge :color="statusColor(job.status)" :label="statusLabel(job.status)" />
                      <q-btn flat round dense icon="open_in_new" size="sm" color="primary" @click.stop="router.push(`/jobs/${job.id}`)" />
                    </div>
                  </q-item-section>
                </q-item>
              </q-list>
            </template>
            <div v-else class="text-caption text-grey-7">{{ t('customers.noLinkedJobs') }}</div>
          </q-card-section>
        </q-card>

        <q-card v-if="form.is_product_supplier" class="ec-card">
          <q-card-section class="row items-center justify-between q-col-gutter-sm">
            <div class="col">
              <div class="text-subtitle2">{{ t('customers.linkedProducts') }}</div>
              <div class="text-caption text-grey-7">{{ linkedProducts.length }} {{ t('customers.linkedProducts').toLowerCase() }}</div>
            </div>
          </q-card-section>
          <q-card-section class="q-pt-none">
            <template v-if="linkedProducts.length">
              <q-list bordered separator class="rounded-borders">
                <q-item v-for="prod in linkedProducts" :key="`prod-${prod.id}`">
                  <q-item-section>
                    <q-item-label>{{ prod.name }}</q-item-label>
                    <q-item-label caption>{{ prod.sku }} · {{ prod.category || t('inventory.uncategorized') }}</q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <div class="row items-center no-wrap q-gutter-xs">
                      <span class="text-caption text-grey-7">{{ formatMoney(prod.daily_rate) }}/day</span>
                      <q-btn flat round dense icon="info" size="sm" :color="infoActionColor" class="inventory-action-contrast" @click.stop="openProductInfo(prod)" />
                      <q-btn v-if="authStore.canEdit" flat round dense icon="edit" size="sm" color="primary" @click.stop="openProductEdit(prod)" />
                    </div>
                  </q-item-section>
                </q-item>
              </q-list>
            </template>
            <div v-else class="text-caption text-grey-7">{{ t('customers.noLinkedProducts') }}</div>
          </q-card-section>
        </q-card>

        <q-card v-if="form.is_rental_supplier" class="ec-card">
          <q-card-section class="row items-center justify-between q-col-gutter-sm">
            <div class="col">
              <div class="text-subtitle2">{{ t('customers.linkedRentals') }}</div>
              <div class="text-caption text-grey-7">{{ linkedRentals.length }} {{ t('customers.linkedRentals').toLowerCase() }}</div>
            </div>
          </q-card-section>
          <q-card-section class="q-pt-none">
            <template v-if="linkedRentals.length">
              <q-list bordered separator class="rounded-borders">
                <q-item v-for="prod in linkedRentals" :key="`rental-${prod.id}`">
                  <q-item-section>
                    <q-item-label>{{ prod.name }}</q-item-label>
                    <q-item-label caption>{{ prod.sku }} · {{ prod.category || t('inventory.uncategorized') }}</q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <div class="row items-center no-wrap q-gutter-xs">
                      <span class="text-caption text-grey-7">{{ formatMoney(prod.daily_rate) }}/day</span>
                      <q-btn flat round dense icon="info" size="sm" :color="infoActionColor" class="inventory-action-contrast" @click.stop="openProductInfo(prod)" />
                      <q-btn v-if="authStore.canEdit" flat round dense icon="edit" size="sm" color="primary" @click.stop="openProductEdit(prod)" />
                    </div>
                  </q-item-section>
                </q-item>
              </q-list>
            </template>
            <div v-else class="text-caption text-grey-7">{{ t('customers.noLinkedRentals') }}</div>
          </q-card-section>
        </q-card>

        <q-card v-if="form.is_crew_supplier" class="ec-card">
          <q-card-section class="row items-center justify-between q-col-gutter-sm">
            <div class="col">
              <div class="text-subtitle2">{{ t('customers.linkedCrew') }}</div>
              <div class="text-caption text-grey-7">{{ info.crew_members?.length || 0 }} {{ t('customers.linkedCrew').toLowerCase() }}</div>
            </div>
            <div class="col-auto" v-if="authStore.canEdit">
              <q-btn flat dense no-caps color="primary" icon="add" :label="t('crew.addMember')" @click="openNewCrewMember" />
            </div>
          </q-card-section>
          <q-card-section class="q-pt-none">
            <template v-if="info.crew_members?.length">
              <q-list bordered separator class="rounded-borders">
                <q-item v-for="cm in info.crew_members" :key="`cm-${cm.id}`" clickable @click="openCrewMember(cm)">
                  <q-item-section>
                    <q-item-label>{{ cm.name }}</q-item-label>
                    <q-item-label caption>
                      <q-badge v-if="cm.is_active" color="positive" :label="t('crew.active')" class="q-mr-xs" />
                      <q-badge v-else color="grey" :label="t('crew.inactive')" class="q-mr-xs" />
                      <span v-if="cm.hourly_rate">{{ formatMoney(cm.hourly_rate) }}/h</span>
                      <span v-if="cm.daily_rate"> · {{ formatMoney(cm.daily_rate) }}/day</span>
                    </q-item-label>
                    <q-item-label caption v-if="cm.skills?.length">
                      <q-badge v-for="skill in cm.skills.slice(0, 5)" :key="skill.id || skill" color="teal" class="q-mr-xs q-mb-xs" :label="skill.name || skill" />
                      <span v-if="cm.skills.length > 5" class="text-caption text-grey-7">+{{ cm.skills.length - 5 }}</span>
                    </q-item-label>
                    <q-item-label caption v-if="cm.preferred_role_names?.length" class="text-grey-7">
                      {{ t('crew.preferredRoles') }}: {{ cm.preferred_role_names.join(', ') }}
                    </q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <q-btn flat round dense icon="edit" size="sm" color="primary" @click.stop="openCrewMember(cm)" />
                  </q-item-section>
                </q-item>
              </q-list>
            </template>
            <div v-else class="text-caption text-grey-7">{{ t('customers.noCrewMembers') }}</div>
          </q-card-section>
        </q-card>
      </template>
    </div>

    <CustomerDeleteDialog
      v-model="deleteDialogOpen"
      :customer="currentCustomer"
      @deleted="onCustomerDeleted"
    />
    <CustomerCustomFieldsDialog
      v-model="customFieldsDialogOpen"
      :customer-id="currentCustomer?.id || null"
      :rows="customerFieldRows"
      @saved="onCustomFieldsSaved"
    />

    <ProductInfoDialog
      v-model="productInfoDialogOpen"
      :product="selectedProductForInfo"
      @edit-product="openProductEdit(selectedProductForInfo)"
    />
    <ProductDialog
      v-model="productEditDialogOpen"
      :product="selectedProductForEdit"
      @saved="onProductSaved"
    />
    <RentalProductInfoDialog
      v-model="rentalInfoDialogOpen"
      :product="selectedRentalForInfo"
      @edit-product="openRentalEdit(selectedRentalForInfo)"
    />
    <RentalProductDialog
      v-model="rentalEditDialogOpen"
      :product="selectedRentalForEdit"
      @saved="onRentalSaved"
    />

    <q-dialog v-model="crewMemberDialogOpen" :maximized="$q.screen.lt.md" persistent>
      <q-card :style="$q.screen.lt.md ? 'width: 100vw; max-width: 100vw' : 'min-width: 520px; max-width: 95vw'" class="ec-card">
        <q-card-section class="row items-center">
          <div class="text-h6">{{ editingCrewMember ? t('crew.editMember') : t('crew.newMember') }}</div>
          <q-space />
          <q-btn flat round dense icon="close" @click="crewMemberDialogOpen = false" />
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-form ref="crewFormRef" @submit.prevent="saveCrewMember">
            <div class="row q-col-gutter-sm">
              <div class="col-12 col-md-6">
                <q-input
                  v-model="crewMemberForm.name"
                  :label="t('crew.memberName')"
                  outlined
                  dense
                  :rules="[v => !!v || t('common.required')]"
                />
              </div>
              <div class="col-12 col-md-6">
                <q-input v-model="crewMemberForm.email" :label="t('profile.email')" type="email" outlined dense />
              </div>
            </div>
            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-12 col-md-6">
                <q-input v-model="crewMemberForm.phone" :label="t('customers.phone')" outlined dense />
              </div>
              <div class="col-12 col-md-6">
                <q-input v-model.number="crewMemberForm.hourly_rate" :label="t('crew.hourlyRate')" type="number" min="0" step="0.01" outlined dense />
              </div>
            </div>
            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-12 col-md-6">
                <q-input v-model.number="crewMemberForm.daily_rate" :label="t('crew.dailyRate')" type="number" min="0" step="0.01" outlined dense />
              </div>
              <div class="col-12 col-md-6 flex items-center">
                <q-toggle v-model="crewMemberForm.is_active" :label="t('crew.active')" />
              </div>
            </div>

            <q-input
              v-model="crewMemberForm.notes"
              :label="t('crew.notes')"
              type="textarea"
              autogrow
              outlined
              dense
              class="q-mt-sm"
            />

            <q-separator class="q-my-md" />
            <div class="text-subtitle2 q-mb-sm">{{ t('crew.skills') }}</div>
            <div class="row q-col-gutter-sm items-center q-mb-sm">
              <div class="col">
                <q-input v-model="newSkill" :label="t('crew.addSkill')" outlined dense @keyup.enter="addCrewSkill" />
              </div>
              <div class="col-auto">
                <q-btn flat dense icon="add" color="primary" @click="addCrewSkill" />
              </div>
            </div>
            <div v-if="crewMemberForm.skill_ids?.length" class="q-mb-sm">
              <q-badge v-for="skillId in crewMemberForm.skill_ids" :key="`skill-${skillId}`" color="teal" class="q-mr-xs q-mb-xs">
                {{ getSkillName(skillId) }}
                <q-btn flat round dense icon="close" size="xs" @click="crewMemberForm.skill_ids = crewMemberForm.skill_ids.filter(id => id !== skillId)" />
              </q-badge>
            </div>
            <div v-else class="text-caption text-grey-7 q-mb-sm">{{ t('crew.noSkills') }}</div>

            <q-separator class="q-my-md" />
            <div class="text-subtitle2 q-mb-sm">{{ t('crew.certifications') }}</div>
            <div class="row q-col-gutter-sm items-center q-mb-sm">
              <div class="col">
                <q-input v-model="newCert" :label="t('crew.addCertification')" outlined dense @keyup.enter="addCrewCert" />
              </div>
              <div class="col-auto">
                <q-btn flat dense icon="add" color="primary" @click="addCrewCert" />
              </div>
            </div>
            <div v-if="crewMemberForm.certification_items?.length" class="q-mb-sm">
              <q-badge v-for="(cert, idx) in crewMemberForm.certification_items" :key="`cert-${idx}`" color="blue" class="q-mr-xs q-mb-xs">
                {{ getCertName(cert.certification_id) }}
                <q-btn flat round dense icon="close" size="xs" @click="crewMemberForm.certification_items.splice(idx, 1)" />
              </q-badge>
            </div>
            <div v-else class="text-caption text-grey-7 q-mb-sm">{{ t('crew.noCertifications') }}</div>
          </q-form>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="crewMemberDialogOpen = false" />
          <q-btn color="primary" unelevated :label="t('app.actions.save')" :loading="savingCrewMember" @click="saveCrewMember" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import { useCustomersStore } from '../stores/customers'
import { useCustomFieldsStore } from '../stores/customFields'
import { useCrewStore } from '../stores/crew'
import { useInventoryStore } from '../stores/inventory'
import { useAuthStore } from '../stores/auth'
import { useSettingsStore } from '../stores/settings'
import { COUNTRIES } from '../constants/countries'
import { normalizeCurrencyCode } from '../constants/currencies'
import { translateMaybePrefillCustomFieldLabel, translateMaybePrefillCustomFieldOption } from '../i18n/prefillContent'
import { getTwentyCustomerUrl } from '../utils/twenty-links'
import CustomerDeleteDialog from '../components/CustomerDeleteDialog.vue'
import CustomerCustomFieldsDialog from '../components/CustomerCustomFieldsDialog.vue'
import ProductInfoDialog from '../components/ProductInfoDialog.vue'
import ProductDialog from '../components/ProductDialog.vue'
import RentalProductInfoDialog from '../components/RentalProductInfoDialog.vue'
import RentalProductDialog from '../components/RentalProductDialog.vue'

const JOB_STATUSES = [
  { value: 'draft', color: 'grey', key: 'jobs.statusDraft' },
  { value: 'confirmed', color: 'blue', key: 'jobs.statusConfirmed' },
  { value: 'in_progress', color: 'orange', key: 'jobs.statusInProgress' },
  { value: 'completed', color: 'positive', key: 'jobs.statusCompleted' },
  { value: 'cancelled', color: 'negative', key: 'jobs.statusCancelled' },
]

const infoActionColor = computed(() => ($q.dark.isActive ? 'teal-4' : 'secondary'))

const $q = useQuasar()
const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const customersStore = useCustomersStore()
const customFieldsStore = useCustomFieldsStore()
const crewStore = useCrewStore()
const inventoryStore = useInventoryStore()
const authStore = useAuthStore()
const settingsStore = useSettingsStore()

const pageLoading = ref(false)
const saving = ref(false)
const formRef = ref(null)
const info = ref(null)
const customerFieldRows = ref([])
const deleteDialogOpen = ref(false)
const customFieldsDialogOpen = ref(false)
const crewMemberDialogOpen = ref(false)
const editingCrewMember = ref(null)
const savingCrewMember = ref(false)
const crewFormRef = ref(null)
const newSkill = ref('')
const newCert = ref('')
const crewMemberForm = ref(emptyCrewMemberForm())
const productInfoDialogOpen = ref(false)
const selectedProductForInfo = ref(null)
const productEditDialogOpen = ref(false)
const selectedProductForEdit = ref(null)
const rentalInfoDialogOpen = ref(false)
const selectedRentalForInfo = ref(null)
const rentalEditDialogOpen = ref(false)
const selectedRentalForEdit = ref(null)
const twentyConfig = ref(null)

const languageOptions = [
  { label: 'English', value: 'en' },
  { label: 'Swedish', value: 'sv' },
]

const isNewCustomer = computed(() => route.path === '/companies/new')

const currentCustomer = computed(() => {
  const id = Number(route.params.customerId || 0)
  if (!id) return null
  return customersStore.customers.find(c => c.id === id) || null
})
const twentyCustomerUrl = computed(() => getTwentyCustomerUrl(currentCustomer.value, twentyConfig.value))

const emptyForm = () => ({
  name: '',
  email: '',
  phone: '',
  address: '',
  city: '',
  postal_code: '',
  country: settingsStore.companyProfile?.default_country || '',
  notes: '',
  is_customer: true,
  is_product_supplier: false,
  is_rental_supplier: false,
  is_crew_supplier: false,
})

const form = ref(emptyForm())

const linkedProducts = computed(() => (info.value?.supplied_products || []).filter(p => !p.is_rental_product))
const linkedRentals = computed(() => (info.value?.supplied_products || []).filter(p => p.is_rental_product))

function formatDate(value) {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '-'
  const currentLocale = String(locale.value || 'en').toLowerCase().startsWith('sv') ? 'sv-SE' : 'en-US'
  return d.toLocaleDateString(currentLocale)
}

function getSkillName(skillId) {
  const skill = crewStore.skills.find(s => s.id === skillId)
  return skill?.name || `Skill #${skillId}`
}

function getCertName(certId) {
  const cert = crewStore.certifications.find(c => c.id === certId)
  return cert?.name || `Cert #${certId}`
}

function formatMoney(value) {
  const amount = Number(value || 0)
  const currentCurrency = normalizeCurrencyCode(settingsStore.companyProfile?.currency, 'SEK')
  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency: currentCurrency,
      maximumFractionDigits: 2,
    }).format(amount)
  } catch {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency: 'SEK',
      maximumFractionDigits: 2,
    }).format(amount)
  }
}

function customFieldLabel(label) {
  return translateMaybePrefillCustomFieldLabel(label, t)
}

function customFieldOption(option) {
  return translateMaybePrefillCustomFieldOption(option, t)
}

function formatFieldValue(field) {
  if (field.value == null) return '-'
  if (field.value_type === 'boolean') return field.value === 'true' || field.value === true ? t('common.true') : t('common.false')
  if (field.value_type === 'select' && field.options?.length) {
    const opt = field.options.find(o => o === field.value)
    return opt ? customFieldOption(opt) : String(field.value)
  }
  return String(field.value)
}

function openProductInfo(prod) {
  if (prod.is_rental_product) {
    const full = inventoryStore.products.find(p => p.id === prod.id) || prod
    selectedRentalForInfo.value = full
    rentalInfoDialogOpen.value = true
  } else {
    const full = inventoryStore.products.find(p => p.id === prod.id) || prod
    selectedProductForInfo.value = full
    productInfoDialogOpen.value = true
  }
}

function openProductEdit(prod) {
  if (prod.is_rental_product) {
    const rental = inventoryStore.products.find(p => p.id === prod.id) || prod
    selectedRentalForEdit.value = rental
    rentalEditDialogOpen.value = true
  } else {
    const product = inventoryStore.products.find(p => p.id === prod.id) || prod
    selectedProductForEdit.value = product
    productEditDialogOpen.value = true
  }
}

function openRentalEdit(prod) {
  rentalInfoDialogOpen.value = false
  openProductEdit(prod)
}

function onProductSaved() {
  productEditDialogOpen.value = false
  selectedProductForEdit.value = null
  loadInfo()
}

function onRentalSaved() {
  rentalEditDialogOpen.value = false
  selectedRentalForEdit.value = null
  loadInfo()
}

function openCrewMember(cm) {
  editingCrewMember.value = cm
  crewMemberForm.value = {
    name: cm.name || '',
    email: cm.email || '',
    phone: cm.phone || '',
    user_id: cm.user_id || null,
    supplier_id: cm.supplier_id || null,
    hourly_rate: cm.hourly_rate ?? null,
    daily_rate: cm.daily_rate ?? null,
    notes: cm.notes || '',
    is_active: cm.is_active ?? true,
    skill_ids: (cm.skills || []).map(s => s.id || s),
    certification_items: (cm.certifications || []).map(c => ({
      certification_id: c.certification?.id || c.certification_id,
      expiry_date: c.expiry_date || c.expires_at || null,
    })),
    preferred_role_ids: (cm.preferred_roles || []).map(r => r.id),
  }
  newSkill.value = ''
  newCert.value = ''
  crewMemberDialogOpen.value = true
}

function openNewCrewMember() {
  editingCrewMember.value = null
  crewMemberForm.value = {
    name: '',
    email: '',
    phone: '',
    user_id: null,
    supplier_id: currentCustomer.value?.id || null,
    hourly_rate: null,
    daily_rate: null,
    notes: '',
    is_active: true,
    skill_ids: [],
    certification_items: [],
    preferred_role_ids: [],
  }
  newSkill.value = ''
  newCert.value = ''
  crewMemberDialogOpen.value = true
}

function emptyCrewMemberForm() {
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
    skill_ids: [],
    certification_items: [],
    preferred_role_ids: [],
  }
}

function addCrewSkill() {
  const val = newSkill.value.trim()
  if (!val) return
  const existing = crewMemberForm.value.skill_ids.find(id => {
    const skill = crewStore.skills.find(s => s.id === id)
    return skill && skill.name.toLowerCase() === val.toLowerCase()
  })
  if (existing) {
    newSkill.value = ''
    return
  }
  const match = crewStore.skills.find(s => s.name.toLowerCase() === val.toLowerCase())
  if (match) {
    crewMemberForm.value.skill_ids.push(match.id)
  } else {
    $q.notify({ type: 'warning', message: t('crew.noSkillsFound') })
  }
  newSkill.value = ''
}

function addCrewCert() {
  const val = newCert.value.trim()
  if (!val) return
  const match = crewStore.certifications.find(c => c.name.toLowerCase() === val.toLowerCase())
  if (match) {
    crewMemberForm.value.certification_items.push({ certification_id: match.id, expiry_date: null })
  }
  newCert.value = ''
}

async function saveCrewMember() {
  const valid = await crewFormRef.value?.validate()
  if (!valid) return

  savingCrewMember.value = true
  try {
    const payload = { ...crewMemberForm.value }
    if (editingCrewMember.value) {
      await crewStore.updateMember(editingCrewMember.value.id, payload)
    } else {
      await crewStore.createMember(payload)
    }
    $q.notify({ type: 'positive', message: editingCrewMember.value ? t('crew.memberUpdated') : t('crew.memberCreated') })
    crewMemberDialogOpen.value = false
    await loadInfo()
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('crew.failedSaveMember') })
  } finally {
    savingCrewMember.value = false
  }
}

function statusColor(value) {
  return JOB_STATUSES.find(s => s.value === value)?.color ?? 'grey'
}

function statusLabel(value) {
  const mapping = {
    draft: t('jobs.statusDraft'),
    confirmed: t('jobs.statusConfirmed'),
    in_progress: t('jobs.statusInProgress'),
    completed: t('jobs.statusCompleted'),
    cancelled: t('jobs.statusCancelled'),
  }
  return mapping[value] || value || '-'
}

function createEmptyCustomerFieldRows() {
  const defs = (customFieldsStore.definitions || []).filter(def => def.entity_type === 'customer' && def.is_active !== false)
  return defs.map(def => ({
    field_definition_id: def.id,
    label: def.label,
    value_type: def.value_type,
    options: def.options || [],
    value: null,
  }))
}

async function loadFieldRows() {
  if (!currentCustomer.value?.id) {
    customerFieldRows.value = createEmptyCustomerFieldRows()
    return
  }
  try {
    const data = await customFieldsStore.fetchEntityValues('customer', currentCustomer.value.id)
    customerFieldRows.value = Array.isArray(data?.values) ? data.values.map(v => ({ ...v })) : createEmptyCustomerFieldRows()
  } catch {
    customerFieldRows.value = createEmptyCustomerFieldRows()
  }
}

function onCustomFieldsSaved(rows) {
  customerFieldRows.value = rows
}

async function loadInfo() {
  if (!currentCustomer.value?.id) {
    info.value = null
    return
  }
  try {
    info.value = await customersStore.fetchCustomerInfo(currentCustomer.value.id)
  } catch {
    info.value = null
  }
}

function syncFromCustomer(customer) {
  if (!customer) {
    form.value = emptyForm()
    customerFieldRows.value = []
    info.value = null
    return
  }
  form.value = {
    name: customer.name ?? '',
    email: customer.email ?? '',
    phone: customer.phone ?? '',
    address: customer.address ?? '',
    city: customer.city ?? '',
    postal_code: customer.postal_code ?? '',
    country: customer.country ?? '',
    notes: customer.notes ?? '',
    is_customer: customer.is_customer ?? true,
    is_product_supplier: customer.is_product_supplier ?? false,
    is_rental_supplier: customer.is_rental_supplier ?? false,
    is_crew_supplier: customer.is_crew_supplier ?? false,
    email_notifications_enabled: customer.email_notifications_enabled !== false,
    preferred_language: customer.preferred_language ?? 'en',
  }
  void loadFieldRows()
  void loadInfo()
}

async function loadData() {
  pageLoading.value = true
  try {
    await Promise.all([
      customersStore.fetchAll(),
      customFieldsStore.fetchDefinitions('customer'),
      settingsStore.fetchCompanyProfile(),
      settingsStore.fetchTwentyConfig().then(data => { twentyConfig.value = data }).catch(() => { twentyConfig.value = null }),
      inventoryStore.fetchAll(),
      crewStore.fetchSkills(),
      crewStore.fetchCertifications(),
    ])

    if (isNewCustomer.value) {
      form.value = emptyForm()
      await loadFieldRows()
    } else {
      syncFromCustomer(currentCustomer.value)
    }
  } finally {
    pageLoading.value = false
  }
}

async function createCustomer() {
  if (!authStore.canEdit) return

  const valid = await formRef.value?.validate()
  if (!valid) return

  saving.value = true
  try {
    const payload = {
      ...form.value,
      name: form.value.name.trim(),
      email: form.value.email?.trim() || null,
      phone: form.value.phone?.trim() || null,
      address: form.value.address?.trim() || null,
      city: form.value.city?.trim() || null,
      postal_code: form.value.postal_code?.trim() || null,
      country: form.value.country?.trim() || null,
      notes: form.value.notes?.trim() || null,
      email_notifications_enabled: !!form.value.email_notifications_enabled,
    }

    const saved = await customersStore.createCustomer(payload)
    await customFieldsStore.saveEntityValues('customer', saved.id, customerFieldRows.value.map(row => ({
      field_definition_id: row.field_definition_id,
      value: row.value,
    })))

    $q.notify({ type: 'positive', message: t('customers.createdNotice') })
    await router.replace(`/companies/${saved.id}`)
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('common.errorOccurred') })
  } finally {
    saving.value = false
  }
}

async function saveChanges() {
  if (!currentCustomer.value || !authStore.canEdit) return

  const valid = await formRef.value?.validate()
  if (!valid) return

  saving.value = true
  try {
    const payload = {
      ...form.value,
      name: form.value.name.trim(),
      email: form.value.email?.trim() || null,
      phone: form.value.phone?.trim() || null,
      address: form.value.address?.trim() || null,
      city: form.value.city?.trim() || null,
      postal_code: form.value.postal_code?.trim() || null,
      country: form.value.country?.trim() || null,
      notes: form.value.notes?.trim() || null,
      email_notifications_enabled: !!form.value.email_notifications_enabled,
    }

    const saved = await customersStore.updateCustomer(currentCustomer.value.id, payload)
    await customFieldsStore.saveEntityValues('customer', saved.id, customerFieldRows.value.map(row => ({
      field_definition_id: row.field_definition_id,
      value: row.value,
    })))

    syncFromCustomer(saved)
    $q.notify({ type: 'positive', message: t('customers.updated') })
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('common.errorOccurred') })
  } finally {
    saving.value = false
  }
}

function confirmDelete() {
  deleteDialogOpen.value = true
}

function onCustomerDeleted() {
  deleteDialogOpen.value = false
  router.push('/companies')
}

function goBack() {
  router.push('/companies')
}

onMounted(async () => {
  await loadData()
})

watch(currentCustomer, (customer) => {
  if (isNewCustomer.value) return
  syncFromCustomer(customer)
})

watch(() => route.params.customerId, async (next, prev) => {
  if (next === prev) return
  await loadData()
})

watch(() => route.path, async (next, prev) => {
  if (next === prev) return
  if (next === '/companies/new') {
    form.value = emptyForm()
    await loadFieldRows()
    info.value = null
  }
})
</script>

<style scoped>
.inventory-action-contrast {
  border: 1px solid rgba(18, 142, 197, 0.42);
  background: rgba(18, 142, 197, 0.08);
}

:global(body.body--dark) .inventory-action-contrast {
  border-color: rgba(129, 186, 165, 0.7);
  background: rgba(74, 122, 104, 0.24);
  color: #cfe7dd !important;
  box-shadow: 0 0 0 1px rgba(129, 186, 165, 0.22) inset;
}

:global(body.q-dark) .inventory-action-contrast {
  border-color: rgba(129, 186, 165, 0.7);
  background: rgba(74, 122, 104, 0.24);
  color: #cfe7dd !important;
  box-shadow: 0 0 0 1px rgba(129, 186, 165, 0.22) inset;
}
</style>
