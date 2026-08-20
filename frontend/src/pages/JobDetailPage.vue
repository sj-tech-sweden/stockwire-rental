<template>
  <q-page class="q-pa-md ec-page">
    <div class="row items-center justify-between q-col-gutter-sm q-mb-md">
      <div class="col-auto">
        <q-btn flat icon="arrow_back" :label="isPhone ? undefined : t('jobs.backToJobs')" @click="goBack" />
      </div>
      <div class="col">
        <div class="text-h5 text-break">{{ isNewJob ? t('jobs.newJob') : (currentJob?.job_code || t('jobs.viewJob')) }}</div>
      </div>
      <div class="col-auto" v-if="authStore.canEdit && !isNewJob">
        <q-btn
          color="secondary"
          outline
          icon="description"
          :label="isPhone ? undefined : t('reports.export')"
          class="q-mr-sm"
          @click="showExportDialog = true"
        />
        <q-btn
          ref="headerSaveBtn"
          color="primary"
          unelevated
          :label="isPhone ? t('app.actions.save') : t('jobs.saveChanges')"
          :loading="saving"
          @click="saveChanges()"
        />
      </div>
      <div class="col-auto" v-if="authStore.canEdit && isNewJob">
        <q-btn
          ref="headerSaveBtn"
          color="primary"
          unelevated
          :label="isPhone ? t('app.actions.create') : t('jobs.create')"
          :loading="saving"
          @click="createJob()"
        />
      </div>
    </div>

    <div v-if="pageLoading" class="row justify-center q-py-xl">
      <q-spinner color="primary" size="48px" />
    </div>

    <div v-else-if="!isNewJob && !currentJob" class="q-gutter-md">
      <q-banner class="bg-warning text-dark rounded-borders">
        {{ t('jobs.jobNotFound') }}
      </q-banner>
      <q-btn color="primary" unelevated :label="t('jobs.backToJobs')" @click="goBack" />
    </div>

    <div v-else class="column q-gutter-md" :class="{ 'q-pb-xl': isPhone && authStore.canEdit }">
      <q-card class="ec-card">
        <q-card-section>
          <div class="row q-col-gutter-md items-start">
            <div class="col-12 col-md">
              <div class="row items-center q-gutter-sm q-mb-sm">
                <div class="text-h6">{{ currentJob.job_code }}</div>
                <q-badge :color="statusColor(currentJob.status)" :label="statusLabel(currentJob.status)" />
              </div>
              <div class="text-body1 q-mb-sm">{{ currentJob.description || t('jobs.noDescription') }}</div>
              <div class="text-caption text-grey-7">{{ t('jobs.customer') }}: {{ customerDisplayName }}</div>
              <div class="text-caption text-grey-7">{{ t('jobs.venue') }}: {{ venueDisplayName }}</div>
              <div class="text-caption text-grey-7">{{ t('jobs.project') }}: {{ projectDisplayName }}</div>
              <div class="text-caption text-grey-7">{{ formattedDateRange }}</div>
              <div class="row q-gutter-sm q-mt-sm">
                <q-btn
                  v-if="twentyJobUrl"
                  flat
                  dense
                  no-caps
                  color="primary"
                  icon="open_in_new"
                  :label="isPhone ? undefined : t('jobs.openInTwenty')"
                  :href="twentyJobUrl"
                  target="_blank"
                />
                <q-btn
                  v-if="productionPlannerUrl"
                  flat
                  dense
                  no-caps
                  color="accent"
                  icon="open_in_new"
                  :label="isPhone ? undefined : t('jobs.openInPP')"
                  :href="productionPlannerUrl"
                  target="_blank"
                />
                <q-btn
                  v-if="productionplannerEnabled"
                  flat
                  dense
                  no-caps
                  color="accent"
                  icon="sync"
                  :label="isPhone ? undefined : t('jobs.syncToPP')"
                  :loading="productionPlannerSyncLoading"
                  @click="syncToProductionPlanner"
                />
              </div>
            </div>
            <div class="col-12 col-md-auto">
              <div class="row q-gutter-sm">
                <q-btn
                  color="primary"
                  outline
                  icon="shopping_cart_checkout"
                  :label="t('scan.scanOutJob')"
                  :to="buildScanJobLink('job_out', currentJob)"
                />
                <q-btn
                  color="primary"
                  outline
                  icon="assignment_return"
                  :label="t('scan.scanInJob')"
                  :to="buildScanJobLink('job_in', currentJob)"
                />
              </div>
            </div>
          </div>
        </q-card-section>
      </q-card>

      <q-card class="ec-card">
        <q-card-section class="row items-center q-col-gutter-sm">
          <div class="col">
            <div class="text-h6">{{ t('jobs.viewJob') }}</div>
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-form ref="formRef" @submit.prevent="saveChanges">
            <div class="row q-col-gutter-sm">
              <div class="col-12 col-md-6">
                <q-input
                  v-model="form.job_code"
                  :label="t('jobs.jobCode')"
                  outlined
                  dense
                  :disable="!authStore.canEdit"
                  :rules="[v => !!v || t('common.required')]"
                />
              </div>
              <div class="col-12 col-md-6">
                <q-select
                  v-model="form.status"
                  :options="statusOptions"
                  :label="t('jobs.status')"
                  outlined
                  dense
                  emit-value
                  map-options
                  :disable="!authStore.canEdit"
                  :rules="[v => !!v || t('common.required')]"
                />
              </div>
            </div>

            <q-input
              v-model="form.description"
              :label="t('jobs.description')"
              type="textarea"
              autogrow
              outlined
              dense
              class="q-mt-sm"
              :disable="!authStore.canEdit"
            />

            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-12 col-md-6">
                <q-select
                  v-model="form.customer_id"
                  :options="filteredCustomerOptions"
                  :label="t('jobs.customer')"
                  outlined
                  dense
                  clearable
                  use-input
                  fill-input
                  input-debounce="0"
                  emit-value
                  map-options
                  :disable="!authStore.canEdit"
                  @filter="filterCustomerOptions"
                />
              </div>
              <div class="col-12 col-md-6">
                <q-select
                  v-model="form.venue_id"
                  :options="filteredVenueOptions"
                  :label="t('jobs.venue')"
                  outlined
                  dense
                  clearable
                  use-input
                  fill-input
                  input-debounce="0"
                  emit-value
                  map-options
                  :disable="!authStore.canEdit"
                  @filter="filterVenueOptions"
                />
              </div>
            </div>

            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-12 col-md-6">
                <q-select
                  v-model="form.project_id"
                  :options="projectOptions"
                  :label="t('jobs.project')"
                  outlined
                  dense
                  clearable
                  emit-value
                  map-options
                  :disable="!authStore.canEdit"
                />
              </div>
              <div class="col-12 col-md-6">
                <q-input
                  v-model="form.location_in_venue"
                  :label="t('jobs.locationInVenue')"
                  outlined
                  dense
                  clearable
                  :disable="!authStore.canEdit"
                />
              </div>
            </div>

            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-12 col-md-6">
                <q-input ref="startDateRef" v-model="form.start_date" :label="t('jobs.startDate')" type="date" outlined dense :disable="!authStore.canEdit" />
              </div>
              <div class="col-12 col-md-6">
                <q-input ref="endDateRef" v-model="form.end_date" :label="t('jobs.endDate')" type="date" outlined dense :disable="!authStore.canEdit" />
              </div>
            </div>

            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-12 col-md-4">
                <q-input
                  v-model.number="form.sales_price"
                  :label="t('jobs.salesPrice')"
                  :suffix="activeCurrencyCode"
                  type="number"
                  min="0"
                  step="0.01"
                  outlined
                  dense
                  :disable="!authStore.canEdit"
                />
              </div>
              <div class="col-12 col-md-4 flex items-center">
                <q-toggle v-model="form.invoice_paid" :label="t('jobs.invoicePaid')" :disable="!authStore.canEdit" />
              </div>
              <div class="col-12 col-md-4">
                <q-input
                  v-model="form.invoice_paid_at"
                  :label="t('jobs.invoicePaidAt')"
                  type="date"
                  outlined
                  dense
                  :disable="!authStore.canEdit || !form.invoice_paid"
                />
              </div>
            </div>

            <q-input
              v-model="form.notes"
              :label="t('jobs.notes')"
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
                :label="t('jobs.emailNotificationsEnabled')"
                :disable="!authStore.canEdit"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>

      <q-card v-if="selectedVenueMapEmbedUrl" class="ec-card">
        <q-card-section>
          <div class="text-subtitle2 q-mb-sm">{{ t('jobs.venue') }}</div>
          <div class="rounded-borders overflow-hidden" style="height: 300px">
            <iframe :src="selectedVenueMapEmbedUrl" width="100%" height="100%" style="border:0" allowfullscreen loading="lazy" />
          </div>
          <q-btn flat dense no-caps color="primary" icon="open_in_new" :label="t('jobs.openVenueMap')" :href="selectedVenueMapLink" target="_blank" class="q-mt-sm" />
        </q-card-section>
      </q-card>

      <q-card class="ec-card">
        <q-card-section class="row items-center justify-between q-col-gutter-sm">
          <div class="col">
            <div class="text-subtitle2">{{ t('jobs.customFieldValues') }}</div>
          </div>
          <div class="col-auto" v-if="authStore.canEdit">
            <q-btn flat dense no-caps color="primary" icon="edit" :label="t('jobs.editCustomFields')" @click="customFieldsDialogOpen = true" />
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none" v-if="jobFieldRows.length">
          <q-list bordered separator class="rounded-borders">
            <q-item v-for="field in jobFieldRows" :key="field.field_definition_id">
              <q-item-section>
                <q-item-label>{{ customFieldLabel(field.label) }}</q-item-label>
                <q-item-label caption>{{ formatFieldValue(field) }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
        <q-card-section class="q-pt-none" v-else>
          <div class="text-caption text-grey-7">{{ t('jobs.noJobCustomFields') }}</div>
        </q-card-section>
      </q-card>

      <EntityAttachmentsPanel
        entity-type="job"
        :entity-id="currentJob?.id || null"
        :title="t('jobs.jobDocuments')"
        default-category="job-document"
      />

      <q-card class="ec-card">
        <q-card-section class="row items-center justify-between q-col-gutter-sm">
          <div class="col">
            <div class="text-h6">{{ t('jobs.productRequirements') }}</div>
            <div class="text-caption text-grey-7">{{ t('jobs.pickList') }}</div>
          </div>
          <div class="col-auto" v-if="authStore.canEdit">
            <q-btn color="primary" unelevated icon="add" :label="isPhone ? undefined : t('jobs.addProductRequirements')" @click="requirementDialogOpen = true" />
          </div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <div class="text-subtitle2 q-mb-sm">{{ t('jobs.requirementsSummary') }}</div>
          <div class="row q-col-gutter-sm q-mb-md">
            <div class="col-12 col-sm-6 col-lg-3">
              <q-card flat bordered>
                <q-card-section>
                  <div class="text-caption text-grey-7">{{ t('jobs.totalWeight') }}</div>
                  <div class="text-subtitle1">{{ t('jobs.weightKg', { value: formatDecimal(summaryTotals.weightKg) }) }}</div>
                </q-card-section>
              </q-card>
            </div>
            <div class="col-12 col-sm-6 col-lg-3">
              <q-card flat bordered>
                <q-card-section>
                  <div class="text-caption text-grey-7">{{ t('jobs.totalVolume') }}</div>
                  <div class="text-subtitle1">{{ t('jobs.volumeM3', { value: formatDecimal(summaryTotals.volumeM3) }) }}</div>
                </q-card-section>
              </q-card>
            </div>
            <div class="col-12 col-sm-6 col-lg-3">
              <q-card flat bordered>
                <q-card-section>
                  <div class="text-caption text-grey-7">{{ t('jobs.totalReplacementCost') }}</div>
                  <div class="text-subtitle1">{{ formatMoney(summaryTotals.replacementCost) }}</div>
                </q-card-section>
              </q-card>
            </div>
            <div class="col-12 col-sm-6 col-lg-3">
              <q-card flat bordered>
                <q-card-section>
                  <div class="text-caption text-grey-7">{{ t('jobs.projectedPriceFromRequirements') }}</div>
                  <div class="text-subtitle1">{{ formatMoney(summaryTotals.projectedPrice) }}</div>
                </q-card-section>
              </q-card>
            </div>
          </div>

          <div v-if="jobRequirementRows.length" class="column q-gutter-sm">
            <q-card v-for="row in jobRequirementRows" :key="row.product_id" flat bordered>
              <q-card-section>
                <div class="row q-col-gutter-sm items-center">
                  <div class="col-12 col-md">
                    <div class="text-subtitle2">{{ row.product?.name || `${t('jobs.productName')} #${row.product_id}` }}</div>
                    <div class="text-caption text-grey-7">{{ row.product?.sku || '—' }}</div>
                    <div class="row q-gutter-xs q-mt-sm items-center">
                      <q-badge color="primary" text-color="white" :label="`${t('jobs.requiredQty')}: ${Number(row.quantity_required || 0)}`" />
                      <q-badge color="info" text-color="white" :label="`${t('scan.picked')}: ${Number(row.quantity_picked || 0)}`" />
                    </div>
                  </div>
                  <div class="col-12 col-md-2">
                    <q-input
                      :model-value="Number(row.quantity_required || 0)"
                      type="number"
                      min="0"
                      :label="t('jobs.requiredQty')"
                      outlined
                      dense
                      :disable="!authStore.canEdit"
                      @update:model-value="value => setRequirementQty(row.product_id, value)"
                    />
                  </div>
                  <div class="col-12 col-md-auto" v-if="authStore.canEdit">
                    <q-btn flat dense no-caps color="negative" icon="delete" :label="t('scan.clear')" @click="removeRequirementRow(row.product_id)" />
                  </div>
                </div>
              </q-card-section>
            </q-card>
          </div>
          <q-banner v-else class="bg-grey-2 text-grey-8 rounded-borders">
            {{ t('jobs.noRequirements') }}
          </q-banner>
        </q-card-section>
      </q-card>

      <q-card class="ec-card">
        <q-card-section class="row items-center justify-between q-col-gutter-sm">
          <div class="col">
            <div class="text-subtitle2">{{ t('jobs.rentalRequirements') }}</div>
          </div>
          <div class="col-auto" v-if="authStore.canEdit">
            <q-btn flat dense no-caps color="primary" icon="edit" :label="isPhone ? undefined : t('jobs.editRequirements')" @click="rentalRequirementDialogOpen = true" />
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none" v-if="rentalRequirementRows.length">
          <q-list bordered separator class="rounded-borders">
            <q-item v-for="row in rentalRequirementRows" :key="`rental-${row.product_id}`">
              <q-item-section>
                <q-item-label>{{ productNameForId(row.product_id) }}</q-item-label>
                <q-item-label caption>{{ t('jobs.requiredQty') }}: {{ row.quantity_required }} · {{ t('jobs.picked') }}: {{ row.quantity_picked }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
          <div v-if="eventorySyncInstances.length" class="q-mt-sm">
            <div class="text-caption text-grey-7 q-mb-xs">{{ t('jobs.eventorySync') }}</div>
            <div v-if="eventoryVerifying" class="text-caption text-grey-7">
              <q-spinner size="14px" class="q-mr-xs" />{{ t('jobs.eventoryVerifying') }}
            </div>
            <div v-else class="row q-gutter-sm">
              <div v-for="inst in eventorySyncInstances" :key="inst.id" class="row items-center q-gutter-xs">
                <q-badge color="teal" :label="inst.name" />
                <template v-if="getEventoryJobId(inst.id) && eventoryVerified[inst.id] === true">
                  <q-badge color="positive" :label="t('jobs.eventoryBooked')">
                    <q-tooltip>{{ t('jobs.eventoryJobId') }}: {{ getEventoryJobId(inst.id) }}</q-tooltip>
                  </q-badge>
                  <q-btn
                    v-if="authStore.canEdit"
                    color="secondary"
                    icon="sync"
                    :label="isPhone ? undefined : t('jobs.eventoryUpdateBooking')"
                    :loading="eventorySyncLoading[inst.id]"
                    unelevated
                    dense
                    no-caps
                    size="sm"
                    @click="updateEventoryRentals(inst.id)"
                  />
                </template>
                <template v-else-if="getEventoryJobId(inst.id) && eventoryVerified[inst.id] === false">
                  <q-badge color="warning" text-color="black" :label="t('jobs.eventoryDeleted')">
                    <q-tooltip>{{ t('jobs.eventoryDeletedHint') }}</q-tooltip>
                  </q-badge>
                  <q-btn
                    v-if="authStore.canEdit && inst.create_jobs && inst.rental_customer_id"
                    color="primary"
                    icon="cloud_upload"
                    :label="isPhone ? undefined : t('jobs.createEventoryBooking')"
                    :loading="eventorySyncLoading[inst.id]"
                    unelevated
                    dense
                    no-caps
                    size="sm"
                    @click="syncEventoryRentals(inst.id)"
                  />
                </template>
                <q-badge v-else-if="!getEventoryJobId(inst.id)" color="grey" :label="t('jobs.eventoryNotBooked')" />
                <q-btn
                  v-if="!getEventoryJobId(inst.id) && authStore.canEdit && inst.create_jobs && inst.rental_customer_id"
                  color="primary"
                  icon="cloud_upload"
                  :label="isPhone ? undefined : t('jobs.createEventoryBooking')"
                  :loading="eventorySyncLoading[inst.id]"
                  unelevated
                  dense
                  no-caps
                  size="sm"
                  @click="syncEventoryRentals(inst.id)"
                />
              </div>
            </div>
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none" v-else>
          <div class="text-caption text-grey-7">{{ t('jobs.noRequirements') }}</div>
        </q-card-section>
      </q-card>

      <q-card class="ec-card" v-if="currentJob?.id">
        <q-card-section class="row items-center justify-between q-col-gutter-sm">
          <div class="col">
            <div class="text-subtitle2">{{ t('crew.crewRequirements') }}</div>
          </div>
          <div class="col-auto" v-if="authStore.canEdit">
            <q-btn flat dense no-caps color="primary" icon="add" :label="isPhone ? undefined : t('crew.addRequirement')" @click="crewRequirementDialogOpen = true" />
            <q-btn flat dense no-caps color="primary" icon="person_add" :label="isPhone ? undefined : t('crew.assignMember')" class="q-ml-xs" @click="crewAssignmentDialogOpen = true" />
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none" v-if="crewRequirementRows.length">
          <q-list bordered separator class="rounded-borders">
            <q-item v-for="row in crewRequirementRows" :key="`crew-req-${row.id}`">
              <q-item-section>
                <q-item-label :class="{ 'text-bold': row.quantity_assigned >= row.quantity }">
                  {{ row.crew_role_name || row.custom_role_name || t('crew.unknownRole') }}
                </q-item-label>
                <q-item-label caption>
                  {{ t('crew.quantity') }}: {{ row.quantity_assigned }}/{{ row.quantity }}
                  <template v-if="row.skills?.length">
                    <q-badge v-for="skill in row.skills" :key="skill.id" color="teal" class="q-mr-xs q-mb-xs" :label="skill.name" />
                  </template>
                </q-item-label>
              </q-item-section>
              <q-item-section side v-if="authStore.canEdit">
                <div class="row items-center no-wrap">
                  <q-btn v-if="row.quantity_assigned < row.quantity" flat dense icon="person_add" color="primary" class="q-mr-xs" @click="openCrewAssignment(row.id)" />
                  <q-btn flat dense icon="delete" color="negative" @click="deleteCrewRequirement(row)" />
                </div>
              </q-item-section>
            </q-item>
          </q-list>
          <div class="q-mt-sm" v-if="crewAssignmentRows.length">
            <div class="text-caption text-grey-7 q-mb-xs">{{ t('crew.crewAssignments') }}</div>
            <q-list bordered separator class="rounded-borders">
              <q-item v-for="a in crewAssignmentRows" :key="`crew-a-${a.id}`">
                <q-item-section>
                  <q-item-label>{{ a.crew_member_name }}</q-item-label>
                  <q-item-label caption>
                    {{ a.crew_role_name }}
                    <q-badge v-if="a.status !== 'assigned'" :color="a.status === 'completed' ? 'positive' : a.status === 'cancelled' ? 'negative' : 'warning'" class="q-ml-xs" :label="t(`crew.${a.status}`)" />
                  </q-item-label>
                </q-item-section>
                <q-item-section side v-if="authStore.canEdit">
                  <q-btn flat dense icon="person_remove" color="negative" @click="unassignCrew(a)" />
                </q-item-section>
              </q-item>
            </q-list>
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none" v-else>
          <div class="text-caption text-grey-7">{{ t('crew.noRequirements') }}</div>
        </q-card-section>
      </q-card>
    </div>

    <!-- Floating save button on mobile -->
    <q-page-sticky v-if="isPhone && authStore.canEdit" position="bottom-right" :offset="[18, 18]">
      <q-btn fab icon="save" color="primary" :loading="saving" @click="isNewJob ? createJob() : saveChanges()" />
    </q-page-sticky>

    <JobProductRequirementDialog
      v-model="requirementDialogOpen"
      v-model:requirementRows="requirementRows"
      :products="inventoryStore.products"
      :start-date="form.start_date"
      :end-date="form.end_date"
      :job-id="currentJob?.id || null"
    />
    <JobRentalRequirementDialog
      v-model="rentalRequirementDialogOpen"
      v-model:requirement-rows="rentalRequirementRows"
      :products="inventoryStore.products"
      :start-date="form.start_date"
      :end-date="form.end_date"
      :job-id="currentJob?.id || null"
    />
    <CustomerPickerDialog v-model="customerPickerOpen" :customers="customersStore.customers" :selected-id="form.customer_id" @select="onCustomerSelected" />
    <VenuePickerDialog v-model="venuePickerOpen" :venues="venuesStore.venues" :selected-id="form.venue_id" @select="onVenueSelected" />
    <JobCustomFieldsDialog v-model="customFieldsDialogOpen" :job-id="currentJob?.id || null" @saved="reloadFieldRows" />
    <CrewRequirementDialog v-model="crewRequirementDialogOpen" :job-id="currentJob?.id || null" @saved="loadCrewData" />
    <CrewAssignmentDialog v-model="crewAssignmentDialogOpen" :job-id="currentJob?.id || null" :requirement-id="selectedCrewRequirementId" @saved="onCrewAssignmentSaved" />
    <ReportExportDialog v-if="currentJob" v-model="showExportDialog" entity-type="job" :entity-id="currentJob.id" />
  </q-page>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'

import { JOB_STATUSES, useJobsStore } from '../stores/jobs'
import { useInventoryStore } from '../stores/inventory'
import { useCustomersStore } from '../stores/customers'
import { useVenuesStore } from '../stores/venues'
import { useProjectsStore } from '../stores/projects'
import { useAuthStore } from '../stores/auth'
import { useSettingsStore } from '../stores/settings'
import { useCrewStore } from '../stores/crew'
import { normalizeCurrencyCode } from '../constants/currencies'
import { isRentalProduct } from '../utils/job-requirements'
import { buildScanJobLink } from '../utils/scan-workflow'
import { googleMapsEmbedUrl, googleMapsSearchUrl, locationQueryFromParts } from '../utils/maps'
import { getTwentyJobUrl } from '../utils/twenty-links'
import { translateMaybePrefillCustomFieldLabel } from '../i18n/prefillContent'
import { useCustomFieldsStore } from '../stores/customFields'
import { api } from '../boot/axios'
import EntityAttachmentsPanel from '../components/EntityAttachmentsPanel.vue'
import JobProductRequirementDialog from '../components/JobProductRequirementDialog.vue'
import JobRentalRequirementDialog from '../components/JobRentalRequirementDialog.vue'
import CrewRequirementDialog from '../components/CrewRequirementDialog.vue'
import CrewAssignmentDialog from '../components/CrewAssignmentDialog.vue'
import CustomerPickerDialog from '../components/CustomerPickerDialog.vue'
import VenuePickerDialog from '../components/VenuePickerDialog.vue'
import JobCustomFieldsDialog from '../components/JobCustomFieldsDialog.vue'
import ReportExportDialog from '../components/ReportExportDialog.vue'

const $q = useQuasar()
const route = useRoute()
const router = useRouter()
const { t, locale } = useI18n()
const isPhone = computed(() => $q.screen.lt.md)

const jobsStore = useJobsStore()
const inventoryStore = useInventoryStore()
const customersStore = useCustomersStore()
const venuesStore = useVenuesStore()
const projectsStore = useProjectsStore()
const authStore = useAuthStore()
const settingsStore = useSettingsStore()
const customFieldsStore = useCustomFieldsStore()
const crewStore = useCrewStore()

const pageLoading = ref(false)
const saving = ref(false)
const isDirty = ref(false)
const formRef = ref(null)
const requirementDialogOpen = ref(false)
const rentalRequirementDialogOpen = ref(false)
const customerPickerOpen = ref(false)
const venuePickerOpen = ref(false)
const customFieldsDialogOpen = ref(false)
const crewRequirementDialogOpen = ref(false)
const crewAssignmentDialogOpen = ref(false)
const showExportDialog = ref(false)
const selectedCrewRequirementId = ref(null)
const eventorySyncLoading = ref({})
const eventoryVerified = ref({})
const eventoryVerifying = ref(false)
const startDateRef = ref(null)
const endDateRef = ref(null)
const crewRequirementRows = ref([])
const crewAssignmentRows = ref([])
const filteredCustomerOptions = ref([])
const filteredVenueOptions = ref([])
const twentyConfig = ref(null)
const form = ref(emptyForm())
const requirementRows = ref([])
const rentalRequirementRows = ref([])
const jobFieldRows = ref([])

const activeCurrencyCode = computed(() => normalizeCurrencyCode(settingsStore.companyProfile?.currency, 'SEK'))
const currentJobId = computed(() => Number(route.params.jobId || 0))
const isNewJob = computed(() => route.path.endsWith('/new'))
const currentJob = computed(() => jobsStore.jobs.find(job => job.id === currentJobId.value) || null)
const twentyJobUrl = computed(() => getTwentyJobUrl(currentJob.value, twentyConfig.value))
const productionplannerEnabled = computed(() => settingsStore.integrations?.productionplanner?.enabled === true)
const productionPlannerUrl = computed(() => {
  const projectId = currentJob.value?.productionplanner_project_id
  return projectId ? jobsStore.getProductionPlannerUrl(projectId) : null
})

const eventoryInstances = computed(() => settingsStore.integrations?.eventory_instances || [])
const eventorySyncInstances = computed(() => {
  if (!rentalRequirementRows.value.length) return []
  const instanceIds = new Set()
  for (const row of rentalRequirementRows.value) {
    const product = inventoryStore.products.find(p => p.id === row.product_id)
    if (product?.external_reference && product.external_reference.includes(':')) {
      instanceIds.add(product.external_reference.split(':')[0])
    }
  }
  return eventoryInstances.value.filter(
    inst => instanceIds.has(inst.id) && inst.enabled && inst.create_jobs
  )
})

function getEventoryJobId(instanceId) {
  if (!currentJob.value?.eventory_job_ids) return null
  try {
    const ids = JSON.parse(currentJob.value.eventory_job_ids)
    return ids[instanceId] || null
  } catch {
    return null
  }
}

async function verifyEventoryJobs() {
  if (!currentJob.value?.eventory_job_ids) return
  let ids
  try {
    ids = JSON.parse(currentJob.value.eventory_job_ids)
  } catch {
    return
  }
  if (!ids || Object.keys(ids).length === 0) return

  eventoryVerifying.value = true
  const results = {}

  for (const [instanceId, eventoryJobId] of Object.entries(ids)) {
    if (!eventoryJobId) continue
    try {
      const { data } = await api.post('/api/v1/jobs/verify-eventory-job', {
        instance_id: instanceId,
        eventory_job_id: eventoryJobId,
      })
      results[instanceId] = Boolean(data?.exists)
    } catch {
      results[instanceId] = false
    }
  }

  eventoryVerified.value = results
  eventoryVerifying.value = false
}

async function syncEventoryRentals(instanceId) {
  if (!currentJob.value?.id) return

  if (!form.value.start_date || !form.value.end_date) {
    $q.dialog({
      title: t('jobs.eventoryDatesRequired'),
      message: t('jobs.eventoryDatesRequiredMessage'),
      ok: { label: t('app.actions.ok'), color: 'primary' },
      persistent: true,
    }).onOk(() => {
      nextTick(() => {
        const el = startDateRef.value?.$el || endDateRef.value?.$el
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' })
          el.classList.add('eventory-highlight-field')
          setTimeout(() => el.classList.remove('eventory-highlight-field'), 2000)
        }
      })
    })
    return
  }

  eventorySyncLoading.value = { ...eventorySyncLoading.value, [instanceId]: true }
  try {
    await jobsStore.createEventoryRentals(currentJob.value.id, instanceId)
    eventoryVerified.value = {}
    $q.notify({ type: 'positive', message: t('jobs.eventorySyncSuccess') })
    await jobsStore.fetchAll()
    await nextTick()
    await verifyEventoryJobs()
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('jobs.eventorySyncFailed') })
  } finally {
    eventorySyncLoading.value = { ...eventorySyncLoading.value, [instanceId]: false }
  }
}

async function updateEventoryRentals(instanceId) {
  if (!currentJob.value?.id) return
  eventorySyncLoading.value = { ...eventorySyncLoading.value, [instanceId]: true }
  try {
    await jobsStore.updateEventoryRentals(currentJob.value.id, instanceId)
    eventoryVerified.value = {}
    $q.notify({ type: 'positive', message: t('jobs.eventoryUpdateSuccess') })
    await jobsStore.fetchAll()
    await nextTick()
    await verifyEventoryJobs()
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('jobs.eventoryUpdateFailed') })
  } finally {
    eventorySyncLoading.value = { ...eventorySyncLoading.value, [instanceId]: false }
  }
}

const productionPlannerSyncLoading = ref(false)

async function syncToProductionPlanner() {
  if (!currentJob.value?.id || !productionplannerEnabled.value) return
  productionPlannerSyncLoading.value = true
  try {
    await jobsStore.syncJobToProductionPlanner(currentJob.value.id)
    $q.notify({ type: 'positive', message: t('jobs.syncPPSuccess') })
    await jobsStore.fetchAll()
  } catch (err) {
    $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('jobs.syncPPFailed') })
  } finally {
    productionPlannerSyncLoading.value = false
  }
}

const statusOptions = computed(() => JOB_STATUSES.map(status => ({ label: statusLabel(status.value), value: status.value })))
const customerOptions = computed(() => customersStore.customers.map(customer => ({
  label: customer.email ? `${customer.name} · ${customer.email}` : customer.name,
  value: customer.id,
})))
const venueOptions = computed(() => venuesStore.venues.map(venue => ({
  label: [venue.name, venue.city].filter(Boolean).join(' · '),
  value: venue.id,
})))
const projectOptions = computed(() => projectsStore.projects.map(project => ({
  label: project.name,
  value: project.id,
})))

function emptyForm() {
  return {
    job_code: '',
    status: 'draft',
    description: '',
    customer_id: null,
    customer_name: '',
    venue_id: null,
    venue_name: '',
    project_id: null,
    location_in_venue: '',
    start_date: null,
    end_date: null,
    sales_price: null,
    invoice_paid: false,
    invoice_paid_at: null,
    email_notifications_enabled: true,
    notes: '',
  }
}

function normalizeDate(value) {
  if (!value) return null
  if (typeof value === 'string') {
    const match = value.match(/^(\d{4}-\d{2}-\d{2})/)
    return match ? match[1] : null
  }
  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    const year = value.getFullYear()
    const month = String(value.getMonth() + 1).padStart(2, '0')
    const day = String(value.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }
  return null
}

function dateSortKey(value) {
  const normalized = normalizeDate(value)
  return normalized ? Number(normalized.replaceAll('-', '')) : null
}

function formatDate(value) {
  const normalized = normalizeDate(value)
  if (!normalized) return '—'
  const [year, month, day] = normalized.split('-').map(Number)
  const currentLocale = String(locale.value || 'en').toLowerCase().startsWith('sv') ? 'sv-SE' : 'en-US'
  return new Date(year, month - 1, day).toLocaleDateString(currentLocale)
}

function formatMoney(value) {
  const amount = Number(value || 0)
  const currentCurrency = normalizeCurrencyCode(settingsStore.companyProfile?.currency, 'SEK')
  try {
    return new Intl.NumberFormat('sv-SE', {
      style: 'currency',
      currency: currentCurrency,
      maximumFractionDigits: 2,
    }).format(amount)
  } catch {
    return new Intl.NumberFormat('sv-SE', {
      style: 'currency',
      currency: 'SEK',
      maximumFractionDigits: 2,
    }).format(amount)
  }
}

function formatDecimal(value) {
  return new Intl.NumberFormat('sv-SE', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(Number(value || 0))
}

function statusColor(value) {
  return JOB_STATUSES.find(status => status.value === value)?.color ?? 'grey'
}

function statusLabel(value) {
  const normalized = String(value || '').toLowerCase()
  const mapping = {
    draft: t('jobs.statusDraft'),
    confirmed: t('jobs.statusConfirmed'),
    in_progress: t('jobs.statusInProgress'),
    completed: t('jobs.statusCompleted'),
    cancelled: t('jobs.statusCancelled'),
  }
  return mapping[normalized] || value
}

function cloneRequirementRows(rows = []) {
  return rows.map(row => ({
    ...row,
    product_id: Number(row.product_id),
    quantity_required: Number(row.quantity_required || 0),
    quantity_picked: Number(row.quantity_picked || 0),
    notes: row.notes || null,
  }))
}

function filterCustomerOptions(val, update) {
  update(() => {
    const needle = val.trim().toLowerCase()
    if (!needle) {
      filteredCustomerOptions.value = customerOptions.value
      return
    }
    filteredCustomerOptions.value = customerOptions.value.filter(option => option.label.toLowerCase().includes(needle))
  })
}

function filterVenueOptions(val, update) {
  update(() => {
    const needle = val.trim().toLowerCase()
    if (!needle) {
      filteredVenueOptions.value = venueOptions.value
      return
    }
    filteredVenueOptions.value = venueOptions.value.filter(option => option.label.toLowerCase().includes(needle))
  })
}

watch(customerOptions, (options) => {
  filteredCustomerOptions.value = options
}, { immediate: true })

watch(venueOptions, (options) => {
  filteredVenueOptions.value = options
}, { immediate: true })

watch(() => form.value, () => { isDirty.value = true }, { deep: true })

watch(() => form.value.invoice_paid, (paid) => {
  if (paid && !form.value.invoice_paid_at) {
    form.value.invoice_paid_at = normalizeDate(new Date())
  }
  if (!paid) {
    form.value.invoice_paid_at = null
  }
})

watch(() => form.value.start_date, (startDate) => {
  const normalizedStart = normalizeDate(startDate)
  if (!normalizedStart) return

  if (form.value.start_date !== normalizedStart) {
    form.value.start_date = normalizedStart
  }

  const normalizedEnd = normalizeDate(form.value.end_date)
  if (!normalizedEnd || dateSortKey(normalizedEnd) < dateSortKey(normalizedStart)) {
    form.value.end_date = normalizedStart
    return
  }

  if (form.value.end_date !== normalizedEnd) {
    form.value.end_date = normalizedEnd
  }
})

const productById = computed(() => {
  const map = new Map()
  for (const product of inventoryStore.products || []) map.set(product.id, product)
  return map
})

const jobRequirementRows = computed(() => (
  cloneRequirementRows(requirementRows.value)
    .map(row => ({ ...row, product: productById.value.get(row.product_id) || null }))
    .sort((a, b) => String(a.product?.name || '').localeCompare(String(b.product?.name || '')))
))

const summaryTotals = computed(() => {
  const startDate = normalizeDate(form.value.start_date || currentJob.value?.start_date)
  const endDate = normalizeDate(form.value.end_date || currentJob.value?.end_date)
  const startKey = dateSortKey(startDate)
  const endKey = dateSortKey(endDate)
  const rentalDays = startKey && endKey && endKey >= startKey
    ? Math.max(1, Math.floor((new Date(endDate).getTime() - new Date(startDate).getTime()) / 86400000) + 1)
    : 1

  return jobRequirementRows.value.reduce((totals, row) => {
    const qty = Math.max(0, Number(row.quantity_required || 0))
    const product = row.product
    if (!product || qty <= 0) return totals

    const weight = Number(product.weight_kg || 0)
    const height = Number(product.height_cm || 0)
    const width = Number(product.width_cm || 0)
    const depth = Number(product.depth_cm || 0)
    const replaceCost = Number(product.replace_cost || 0)
    const unitRate = Number(product.rental_price || product.daily_rate || 0)

    totals.weightKg += weight * qty
    totals.volumeM3 += ((height * width * depth) / 1000000) * qty
    totals.replacementCost += replaceCost * qty
    totals.projectedPrice += unitRate * qty * rentalDays
    return totals
  }, {
    weightKg: 0,
    volumeM3: 0,
    replacementCost: 0,
    projectedPrice: 0,
  })
})

const customerDisplayName = computed(() => {
  const selected = customersStore.customers.find(customer => customer.id === (form.value.customer_id || currentJob.value?.customer_id))
  return selected?.name || form.value.customer_name || currentJob.value?.customer_name || t('jobs.unassigned')
})

const venueDisplayName = computed(() => {
  const selected = venuesStore.venues.find(venue => venue.id === (form.value.venue_id || currentJob.value?.venue_id))
  return selected?.name || form.value.venue_name || currentJob.value?.venue_name || t('jobs.unassigned')
})

const projectDisplayName = computed(() => (
  projectsStore.projects.find(project => project.id === (form.value.project_id || currentJob.value?.project_id))?.name || t('jobs.unassigned')
))

const formattedDateRange = computed(() => `${formatDate(form.value.start_date || currentJob.value?.start_date)} ${t('jobs.to')} ${formatDate(form.value.end_date || currentJob.value?.end_date)}`)

const selectedVenueLocationQuery = computed(() => {
  if (form.value.venue_id) {
    const venue = venuesStore.venues.find(v => v.id === form.value.venue_id)
    return locationQueryFromParts(venue || {})
  }
  return ''
})

const selectedVenueMapLink = computed(() => googleMapsSearchUrl(selectedVenueLocationQuery.value))
const selectedVenueMapEmbedUrl = computed(() => googleMapsEmbedUrl(selectedVenueLocationQuery.value))

function customFieldLabel(label) {
  return translateMaybePrefillCustomFieldLabel(label, t)
}

function formatFieldValue(field) {
  if (field.value == null) return '—'
  if (field.value_type === 'boolean') return field.value === 'true' || field.value === true ? t('common.true') : t('common.false')
  return String(field.value)
}

function productNameForId(id) {
  const p = inventoryStore.products.find(p => p.id === id)
  return p ? `${p.sku} · ${p.name}` : `#${id}`
}

async function loadFieldRows() {
  if (!currentJob.value?.id) {
    jobFieldRows.value = []
    return
  }
  try {
    const data = await customFieldsStore.fetchEntityValues('job', currentJob.value.id)
    jobFieldRows.value = Array.isArray(data?.values) ? data.values.map(v => ({ ...v })) : []
  } catch {
    jobFieldRows.value = []
  }
}

function reloadFieldRows() {
  void loadFieldRows()
}

async function loadCrewData() {
  if (!currentJob.value?.id) return
  try {
    crewRequirementRows.value = await crewStore.fetchJobCrewRequirements(currentJob.value.id)
  } catch {
    crewRequirementRows.value = []
  }
  try {
    crewAssignmentRows.value = await crewStore.fetchJobCrewAssignments(currentJob.value.id)
  } catch {
    crewAssignmentRows.value = []
  }
}

async function deleteCrewRequirement(req) {
  $q.dialog({
    title: t('crew.deleteRequirement'),
    message: t('crew.deleteRequirementConfirm', { name: req.crew_role_name || req.custom_role_name || t('crew.unknownRole') }),
    cancel: t('app.actions.cancel'),
    ok: t('app.actions.delete'),
    persistent: true,
  }).onOk(async () => {
    try {
      await crewStore.deleteJobCrewRequirement(currentJob.value.id, req.id)
      await loadCrewData()
      $q.notify({ type: 'positive', message: t('crew.requirementDeleted') })
    } catch (err) {
      $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('crew.failedToDelete') })
    }
  })
}

async function unassignCrew(assignment) {
  $q.dialog({
    title: t('crew.unassign'),
    message: t('crew.unassignConfirm', { member: assignment.crew_member_name, role: assignment.crew_role_name }),
    cancel: t('app.actions.cancel'),
    ok: t('app.actions.delete'),
    persistent: true,
  }).onOk(async () => {
    try {
      await crewStore.deleteCrewAssignment(assignment.id)
      await loadCrewData()
      $q.notify({ type: 'positive', message: t('crew.memberUnassigned') })
    } catch (err) {
      $q.notify({ type: 'negative', message: err?.response?.data?.detail || t('crew.failedToUnassign') })
    }
  })
}

function openCrewAssignment(requirementId) {
  selectedCrewRequirementId.value = requirementId
  crewAssignmentDialogOpen.value = true
}

function onCrewAssignmentSaved() {
  selectedCrewRequirementId.value = null
  loadCrewData()
}

function onCustomerSelected(customer) {
  form.value.customer_id = customer.id
  form.value.customer_name = customer.name
}

function onVenueSelected(venue) {
  form.value.venue_id = venue.id
  form.value.venue_name = venue.name
}

function syncFromJob(job) {
  if (!job) {
    form.value = emptyForm()
    requirementRows.value = []
    rentalRequirementRows.value = []
    jobFieldRows.value = []
    isDirty.value = false
    return
  }

  form.value = {
    job_code: job.job_code ?? '',
    status: job.status ?? 'draft',
    description: job.description ?? '',
    customer_id: job.customer_id ?? null,
    customer_name: job.customer_name ?? '',
    venue_id: job.venue_id ?? null,
    venue_name: job.venue_name ?? '',
    project_id: job.project_id ?? null,
    location_in_venue: job.location_in_venue ?? '',
    start_date: normalizeDate(job.start_date),
    end_date: normalizeDate(job.end_date),
    sales_price: job.sales_price == null ? null : Number(job.sales_price),
    invoice_paid: Boolean(job.invoice_paid),
    invoice_paid_at: normalizeDate(job.invoice_paid_at),
    email_notifications_enabled: job.email_notifications_enabled !== false,
    notes: job.notes ?? '',
  }

  const allRows = jobsStore.requirements
    .filter(req => (
      req.job_id === job.id
      && (Number(req.quantity_required || 0) > 0 || Number(req.quantity_picked || 0) > 0)
    ))
    .map(req => ({
      product_id: req.product_id,
      quantity_required: req.quantity_required,
      quantity_picked: req.quantity_picked,
      notes: req.notes || null,
    }))

  const productMap = productById.value
  requirementRows.value = allRows.filter(r => !isRentalProduct(productMap.get(r.product_id)))
  rentalRequirementRows.value = allRows.filter(r => isRentalProduct(productMap.get(r.product_id)))

  isDirty.value = false
  void loadFieldRows()
  void loadCrewData()
}

function setRequirementQty(productId, value) {
  const qty = Math.max(0, Number(value || 0))
  const row = requirementRows.value.find(item => item.product_id === productId)
  if (row) {
    row.quantity_required = qty
    if (qty === 0) removeRequirementRow(productId)
    return
  }
  if (qty > 0) {
    requirementRows.value.push({ product_id: productId, quantity_required: qty, quantity_picked: 0, notes: null })
  }
}

function removeRequirementRow(productId) {
  const row = requirementRows.value.find(item => item.product_id === productId)
  if (!row) return
  
  // Preserve rows with any picked quantity by setting quantity_required to 0
  if ((row.quantity_picked ?? 0) > 0) {
    row.quantity_required = 0
  } else {
    requirementRows.value = requirementRows.value.filter(item => item.product_id !== productId)
  }
}

async function loadData() {
  pageLoading.value = true
  try {
    await Promise.all([
      jobsStore.fetchAll(),
      inventoryStore.fetchAll(),
      customersStore.fetchAll(),
      venuesStore.fetchAll(),
      projectsStore.fetchAll(),
      settingsStore.fetchCompanyProfile(),
      settingsStore.fetchIntegrations(),
      settingsStore.fetchTwentyConfig().then(data => { twentyConfig.value = data }).catch(() => { twentyConfig.value = null }),
    ])

    if (isNewJob.value) {
      const customerId = Number(route.query.customerId || 0)
      const venueId = Number(route.query.venueId || 0)
      const projectId = Number(route.query.projectId || 0)
      const customer = customerId > 0 ? customersStore.customers.find(c => c.id === customerId) : null
      const venue = venueId > 0 ? venuesStore.venues.find(v => v.id === venueId) : null
      form.value = emptyForm()
      if (customer) {
        form.value.customer_id = customer.id
        form.value.customer_name = customer.name
      }
      if (venue) {
        form.value.venue_id = venue.id
        form.value.venue_name = venue.name
      }
      if (projectId > 0) {
        form.value.project_id = projectId
      }
    } else {
      syncFromJob(currentJob.value)
    }
  } finally {
    pageLoading.value = false
  }

  if (!isNewJob.value && currentJob.value?.eventory_job_ids) {
    verifyEventoryJobs()
  }
}

async function createJob() {
  if (!authStore.canEdit) return

  const valid = await formRef.value?.validate()
  if (!valid) return

  saving.value = true
  try {
    const selectedCustomer = customersStore.customers.find(customer => customer.id === form.value.customer_id)
    const selectedVenue = venuesStore.venues.find(venue => venue.id === form.value.venue_id)

    const payload = {
      ...form.value,
      customer_name: selectedCustomer?.name || form.value.customer_name || '',
      venue_name: selectedVenue?.name || form.value.venue_name || '',
      start_date: normalizeDate(form.value.start_date),
      end_date: normalizeDate(form.value.end_date),
      sales_price: form.value.sales_price == null || form.value.sales_price === '' ? null : Number(form.value.sales_price),
      invoice_paid: Boolean(form.value.invoice_paid),
      invoice_paid_at: form.value.invoice_paid ? normalizeDate(form.value.invoice_paid_at) : null,
      email_notifications_enabled: !!form.value.email_notifications_enabled,
    }

    const savedJob = await jobsStore.createJob(payload)
    $q.notify({ type: 'positive', message: t('jobs.created') || 'Job created' })
    await router.replace(`/jobs/${savedJob.id}`)
  } catch (err) {
    console.error('Failed to create job:', err)
    $q.notify({ type: 'negative', message: t('jobs.createFailed') || 'Failed to create job' })
  } finally {
    saving.value = false
  }
}

async function saveChanges() {
  if (!currentJob.value || !authStore.canEdit) return

  const valid = await formRef.value?.validate()
  if (!valid) return

  saving.value = true
  try {
    const selectedCustomer = customersStore.customers.find(customer => customer.id === form.value.customer_id)
    const selectedVenue = venuesStore.venues.find(venue => venue.id === form.value.venue_id)

    const payload = {
      ...currentJob.value,
      ...form.value,
      customer_name: selectedCustomer?.name || form.value.customer_name || currentJob.value.customer_name || '',
      venue_name: selectedVenue?.name || form.value.venue_name || currentJob.value.venue_name || '',
      start_date: normalizeDate(form.value.start_date),
      end_date: normalizeDate(form.value.end_date),
      sales_price: form.value.sales_price == null || form.value.sales_price === '' ? null : Number(form.value.sales_price),
      invoice_paid: Boolean(form.value.invoice_paid),
      invoice_paid_at: form.value.invoice_paid ? normalizeDate(form.value.invoice_paid_at) : null,
      email_notifications_enabled: !!form.value.email_notifications_enabled,
    }

    const savedJob = await jobsStore.updateJob(currentJob.value.id, payload)
    const allRequirements = new Map()
    for (const item of requirementRows.value) {
      allRequirements.set(item.product_id, {
        product_id: item.product_id,
        quantity_required: Number(item.quantity_required || 0),
        quantity_picked: Number(item.quantity_picked || 0),
        notes: item.notes || null,
      })
    }
    for (const item of rentalRequirementRows.value) {
      if (!allRequirements.has(item.product_id)) {
        allRequirements.set(item.product_id, {
          product_id: item.product_id,
          quantity_required: Number(item.quantity_required || 0),
          quantity_picked: Number(item.quantity_picked || 0),
          notes: item.notes || null,
        })
      }
    }
    await jobsStore.bulkUpsertRequirements(savedJob.id, [...allRequirements.values()])

    syncFromJob(savedJob)
    $q.notify({ type: 'positive', message: t('jobs.jobUpdated') })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('common.errorOccurred') })
  } finally {
    saving.value = false
  }
}

function goBack() {
  router.push('/jobs')
}

onMounted(async () => {
  await loadData()
})

watch(currentJob, (job) => {
  if (isNewJob.value) return
  if (!isDirty.value) syncFromJob(job)
})

watch(() => route.params.jobId, async (next, prev) => {
  if (next === prev) return
  await loadData()
})
</script>

<style scoped>
.eventory-highlight-field {
  animation: eventory-pulse 0.6s ease-in-out 3;
  border-radius: 4px;
}

@keyframes eventory-pulse {
  0%, 100% { box-shadow: none; }
  50% { box-shadow: 0 0 0 3px rgba(255, 193, 7, 0.6); }
}
</style>
