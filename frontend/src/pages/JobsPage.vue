<template>
  <q-page class="q-pa-md ec-page">
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">{{ t('jobs.title') }}</div>
      <q-btn v-if="authStore.canEdit" color="primary" icon="add" :label="t('jobs.newJob')" unelevated @click="openCreate" />
    </div>

    <q-banner
      v-if="showCachedOfflineBanner"
      class="bg-warning text-dark rounded-borders q-mb-md"
      dense
    >
      {{ t('jobs.cachedOfflineBanner') }}
    </q-banner>

    <div class="row items-center justify-between q-mb-md q-gutter-sm">
      <div class="row q-gutter-xs">
        <q-chip
          v-for="status in statusFilters"
          :key="status.value"
          clickable
          dense
          :color="status.color"
          :text-color="activeFilter === status.value ? 'white' : status.color"
          :outline="activeFilter !== status.value"
          @click="activeFilter = activeFilter === status.value ? null : status.value"
        >
          {{ status.label }}
        </q-chip>
      </div>

      <q-input v-model="search" dense outlined clearable :placeholder="t('jobs.searchJobs')">
        <template #prepend>
          <q-icon name="search" />
        </template>
      </q-input>
    </div>

    <q-table
      :rows="visibleJobs"
      :columns="columns"
      row-key="id"
      :grid="compactGrid"
      :hide-header="compactGrid"
      flat
      bordered
      :loading="pageLoading || jobsStore.loading"
      :pagination="{ rowsPerPage: 50 }"
      :rows-per-page-options="[25, 50, 100, 0]"
      class="ec-card"
    >
      <template #body-cell-status="props">
        <q-td :props="props">
          <q-badge :color="statusColor(props.value)" :label="statusLabel(props.value)" />
        </q-td>
      </template>

      <template #body-cell-sales_price="props">
        <q-td :props="props">
          {{ formatMoney(props.value) }}
        </q-td>
      </template>

      <template #body-cell-invoice_paid="props">
        <q-td :props="props">
          <q-badge :color="props.value ? 'positive' : 'warning'" :label="props.value ? t('jobs.paid') : t('jobs.unpaid')" />
        </q-td>
      </template>

      <template #body-cell-actions="props">
        <q-td v-if="authStore.canEdit" :props="props" auto-width>
          <q-btn flat round dense icon="edit" color="primary" class="q-mr-xs" @click="openEdit(props.row)" />
          <q-btn flat round dense icon="delete" color="negative" @click="confirmDelete(props.row)" />
        </q-td>
      </template>

      <template #item="props">
        <div class="q-pa-xs col-12">
          <q-card flat bordered>
            <q-card-section class="q-pb-sm">
              <div class="row items-center justify-between">
                <div class="text-subtitle2">{{ props.row.job_code }}</div>
                <q-badge :color="statusColor(props.row.status)" :label="statusLabel(props.row.status)" />
              </div>
              <div class="text-caption text-grey-7">{{ props.row.description || t('jobs.noDescription') }}</div>
            </q-card-section>
            <q-card-section class="q-pt-none q-pb-sm">
              <div class="text-caption">{{ t('jobs.customerLabel') }}: {{ customerNameForId(props.row.customer_id) || t('jobs.unassigned') }}</div>
              <div class="text-caption">{{ t('jobs.venueLabel') }}: {{ venueNameForId(props.row.venue_id) || t('jobs.unassigned') }}</div>
              <div class="text-caption">{{ t('jobs.salesLabel') }}: {{ formatMoney(props.row.sales_price) }}</div>
              <div class="text-caption">{{ t('jobs.invoiceLabel') }}: {{ props.row.invoice_paid ? t('jobs.paid') : t('jobs.unpaid') }}</div>
              <div class="text-caption">{{ props.row.start_date || '-' }} {{ t('jobs.to') }} {{ props.row.end_date || '-' }}</div>
            </q-card-section>
            <q-card-actions v-if="authStore.canEdit" align="right">
              <q-btn flat dense icon="edit" color="primary" @click="openEdit(props.row)" />
              <q-btn flat dense icon="delete" color="negative" @click="confirmDelete(props.row)" />
            </q-card-actions>
          </q-card>
        </div>
      </template>
    </q-table>

    <q-dialog v-model="dialogOpen" persistent :maximized="isPhoneDialog">
      <q-card :style="isPhoneDialog ? 'width: 100vw; max-width: 100vw; height: 100vh' : 'min-width: 760px; max-width: 95vw'" class="ec-card">
        <q-card-section>
          <div class="text-h6">{{ editing ? t('jobs.editJob') : t('jobs.newJob') }}</div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-form ref="formRef" @submit.prevent="saveJob">
            <div class="row q-col-gutter-sm">
              <div class="col-12 col-md-6">
                <q-input
                  v-model="form.job_code"
                  :label="t('jobs.jobCode')"
                  outlined
                  dense
                  :rules="[v => !!v || t('login.required')]"
                >
                  <template #append>
                    <q-btn
                      flat
                      dense
                      no-caps
                      color="primary"
                      icon="autorenew"
                      :label="t('jobs.generate')"
                      :loading="generatingJobCode"
                      @click="generateJobCode"
                    />
                  </template>
                </q-input>
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
                  :rules="[v => !!v || t('login.required')]"
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
                  @filter="filterVenueOptions"
                />
              </div>
            </div>

            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-12 col-md-6">
                <q-input v-model="form.start_date" :label="t('jobs.startDate')" type="date" outlined dense />
              </div>
              <div class="col-12 col-md-6">
                <q-input v-model="form.end_date" :label="t('jobs.endDate')" type="date" outlined dense />
              </div>
            </div>

            <div class="row q-col-gutter-sm q-mt-sm">
              <div class="col-12 col-md-4">
                <q-input
                  v-model.number="form.sales_price"
                  :label="t('jobs.salesPrice')"
                  :suffix="activeCurrencyCode"
                  :hint="currencyHelperText"
                  type="number"
                  step="0.01"
                  min="0"
                  outlined
                  dense
                />
              </div>
              <div class="col-12 col-md-4 flex items-center">
                <q-toggle v-model="form.invoice_paid" :label="t('jobs.invoicePaid')" />
              </div>
              <div class="col-12 col-md-4">
                <q-input
                  v-model="form.invoice_paid_at"
                  :label="t('jobs.invoicePaidAt')"
                  type="date"
                  outlined
                  dense
                  :disable="!form.invoice_paid"
                />
              </div>
            </div>

            <q-banner class="bg-blue-1 text-primary rounded-borders q-mt-sm" dense>
              {{ t('jobs.projectedPriceFromRequirements') }}: <strong>{{ formatMoney(projectedJobPrice) }}</strong>
              <span v-if="Number(form.sales_price || 0) > 0" class="q-ml-sm">
                {{ t('jobs.salesTarget') }}: <strong>{{ formatMoney(form.sales_price) }}</strong>
              </span>
            </q-banner>

            <q-input
              v-model="form.notes"
              :label="t('jobs.notes')"
              type="textarea"
              autogrow
              outlined
              dense
              class="q-mt-sm"
            />

            <q-expansion-item class="q-mt-md" icon="fact_check" :label="t('jobs.customFieldValues')" dense>
              <div class="q-pt-sm">
                <div v-if="jobFieldRows.length">
                  <div v-for="field in jobFieldRows" :key="field.field_definition_id" class="q-mb-sm">
                    <q-input
                      v-if="field.value_type === 'text'"
                      v-model="field.value"
                      :label="customFieldLabel(field.label)"
                      outlined
                      dense
                    />
                    <q-input
                      v-else-if="field.value_type === 'number'"
                      v-model="field.value"
                      :label="customFieldLabel(field.label)"
                      type="number"
                      outlined
                      dense
                    />
                    <q-select
                      v-else-if="field.value_type === 'boolean'"
                      v-model="field.value"
                      :options="booleanValueOptions"
                      :label="customFieldLabel(field.label)"
                      outlined
                      dense
                      emit-value
                      map-options
                    />
                    <q-input
                      v-else-if="field.value_type === 'date'"
                      v-model="field.value"
                      :label="customFieldLabel(field.label)"
                      type="date"
                      outlined
                      dense
                    />
                    <q-select
                      v-else-if="field.value_type === 'select'"
                      v-model="field.value"
                      :options="(field.options || []).map(option => ({ label: customFieldOption(option), value: option }))"
                      :label="customFieldLabel(field.label)"
                      outlined
                      dense
                      clearable
                      emit-value
                      map-options
                    />
                  </div>
                </div>
                <div v-else class="text-caption text-grey-7">
                  {{ t('jobs.noJobCustomFields') }}
                </div>
              </div>
            </q-expansion-item>

            <q-expansion-item class="q-mt-md" icon="person_add" :label="t('jobs.createNewCustomer')" dense>
              <div class="q-pt-sm">
                <q-input v-model="customerDraft.name" :label="t('jobs.customerName')" outlined dense class="q-mb-sm" />
                <div class="row q-col-gutter-sm">
                  <div class="col-12 col-md-6">
                    <q-input v-model="customerDraft.email" :label="t('profile.email')" outlined dense class="q-mb-sm" />
                  </div>
                  <div class="col-12 col-md-6">
                    <q-input v-model="customerDraft.phone" :label="t('customers.phone')" outlined dense class="q-mb-sm" />
                  </div>
                </div>
                <q-input v-model="customerDraft.notes" :label="t('jobs.customerNotes')" type="textarea" autogrow outlined dense />

                <q-separator class="q-my-sm" />
                <div class="text-subtitle2 q-mb-xs">{{ t('jobs.customerCustomFields') }}</div>
                <div v-if="customerDraftFieldRows.length">
                  <div v-for="field in customerDraftFieldRows" :key="field.field_definition_id" class="q-mb-sm">
                    <q-input
                      v-if="field.value_type === 'text'"
                      v-model="field.value"
                      :label="customFieldLabel(field.label)"
                      outlined
                      dense
                    />
                    <q-input
                      v-else-if="field.value_type === 'number'"
                      v-model="field.value"
                      :label="customFieldLabel(field.label)"
                      type="number"
                      outlined
                      dense
                    />
                    <q-select
                      v-else-if="field.value_type === 'boolean'"
                      v-model="field.value"
                      :options="booleanValueOptions"
                      :label="customFieldLabel(field.label)"
                      outlined
                      dense
                      emit-value
                      map-options
                    />
                    <q-input
                      v-else-if="field.value_type === 'date'"
                      v-model="field.value"
                      :label="customFieldLabel(field.label)"
                      type="date"
                      outlined
                      dense
                    />
                    <q-select
                      v-else-if="field.value_type === 'select'"
                      v-model="field.value"
                      :options="(field.options || []).map(option => ({ label: customFieldOption(option), value: option }))"
                      :label="customFieldLabel(field.label)"
                      outlined
                      dense
                      clearable
                      emit-value
                      map-options
                    />
                  </div>
                </div>
                <div v-else class="text-caption text-grey-7">{{ t('jobs.noCustomerCustomFields') }}</div>
              </div>
            </q-expansion-item>

            <q-expansion-item class="q-mt-md" icon="place" :label="t('jobs.createNewVenue')" dense>
              <div class="q-pt-sm">
                <q-input v-model="venueDraft.name" :label="t('jobs.venueName')" outlined dense class="q-mb-sm" />
                <div class="row q-col-gutter-sm">
                  <div class="col-12 col-md-6">
                    <q-input v-model="venueDraft.address" :label="t('venues.address')" outlined dense class="q-mb-sm" />
                  </div>
                  <div class="col-12 col-md-6">
                    <q-input v-model="venueDraft.city" :label="t('venues.city')" outlined dense class="q-mb-sm" />
                  </div>
                </div>
                <q-input v-model="venueDraft.notes" :label="t('jobs.venueNotes')" type="textarea" autogrow outlined dense />

                <q-separator class="q-my-sm" />
                <div class="text-subtitle2 q-mb-xs">{{ t('jobs.venueCustomFields') }}</div>
                <div v-if="venueDraftFieldRows.length">
                  <div v-for="field in venueDraftFieldRows" :key="field.field_definition_id" class="q-mb-sm">
                    <q-input
                      v-if="field.value_type === 'text'"
                      v-model="field.value"
                      :label="customFieldLabel(field.label)"
                      outlined
                      dense
                    />
                    <q-input
                      v-else-if="field.value_type === 'number'"
                      v-model="field.value"
                      :label="customFieldLabel(field.label)"
                      type="number"
                      outlined
                      dense
                    />
                    <q-select
                      v-else-if="field.value_type === 'boolean'"
                      v-model="field.value"
                      :options="booleanValueOptions"
                      :label="customFieldLabel(field.label)"
                      outlined
                      dense
                      emit-value
                      map-options
                    />
                    <q-input
                      v-else-if="field.value_type === 'date'"
                      v-model="field.value"
                      :label="customFieldLabel(field.label)"
                      type="date"
                      outlined
                      dense
                    />
                    <q-select
                      v-else-if="field.value_type === 'select'"
                      v-model="field.value"
                      :options="(field.options || []).map(option => ({ label: customFieldOption(option), value: option }))"
                      :label="customFieldLabel(field.label)"
                      outlined
                      dense
                      clearable
                      emit-value
                      map-options
                    />
                  </div>
                </div>
                <div v-else class="text-caption text-grey-7">{{ t('jobs.noVenueCustomFields') }}</div>
              </div>
            </q-expansion-item>

            <q-expansion-item class="q-mt-md" icon="inventory_2" :label="t('jobs.requiredProductsAndQuantities')" dense>
              <div class="q-pt-sm">
                <div class="row q-col-gutter-sm q-mb-sm">
                  <div class="col-12 col-md-3">
                    <q-input
                      v-model="requirementProductSearch"
                      :label="t('jobs.searchProducts')"
                      outlined
                      dense
                      clearable
                    >
                      <template #prepend>
                        <q-icon name="search" />
                      </template>
                    </q-input>
                  </div>
                  <div class="col-12 col-md-2">
                    <q-select
                      v-model="requirementCategoryFilter"
                      :options="requirementCategoryFilterOptions"
                      :label="t('jobs.categoryFilter')"
                      outlined
                      dense
                      clearable
                      emit-value
                      map-options
                    />
                  </div>
                  <div class="col-12 col-md-2">
                    <q-select
                      v-model="requirementBrandFilter"
                      :options="requirementBrandFilterOptions"
                      :label="t('jobs.brandFilter')"
                      outlined
                      dense
                      clearable
                      emit-value
                      map-options
                    />
                  </div>
                  <div class="col-12 col-md-2">
                    <q-select
                      v-model="requirementManufacturerFilter"
                      :options="requirementManufacturerFilterOptions"
                      :label="t('jobs.manufacturerFilter')"
                      outlined
                      dense
                      clearable
                      emit-value
                      map-options
                    />
                  </div>
                  <div class="col-12 col-md-1">
                    <q-select
                      v-model="requirementTypeFilter"
                      :options="requirementTypeFilterOptions"
                      :label="t('jobs.typeFilter')"
                      outlined
                      dense
                      clearable
                      emit-value
                      map-options
                    />
                  </div>
                  <div class="col-12 col-md-2">
                    <q-select
                      v-model="requirementSort"
                      :options="requirementSortOptions"
                      :label="t('jobs.sort')"
                      outlined
                      dense
                      emit-value
                      map-options
                    />
                  </div>
                </div>

                <div class="text-caption text-grey-7 q-mb-sm">
                  {{ t('jobs.requirementsHelp') }}
                </div>

                <q-list bordered separator class="rounded-borders jobs-category-list">
                  <q-expansion-item
                    v-for="group in requirementCategoryGroups"
                    :key="group.key"
                    :label="`${group.label} (${group.subtreeCount})`"
                    :default-opened="group.depth === 0"
                    expand-separator
                    dense
                    :header-style="{ paddingLeft: `${Math.min(group.depth * 14, 56)}px` }"
                  >
                    <div class="q-pa-sm">
                      <div v-if="!group.products.length" class="text-caption text-grey-6 q-mb-sm">
                        {{ t('jobs.noProductsInCategory') }}
                      </div>
                      <q-card
                        v-for="product in group.products"
                        :key="product.id"
                        flat
                        bordered
                        class="q-mb-sm"
                      >
                        <q-card-section class="q-pb-xs">
                          <div class="text-subtitle2">{{ product.sku }} · {{ product.name }}</div>
                          <div class="text-caption text-grey-7">
                            {{ product.brand || t('jobs.noBrand') }} · {{ product.manufacturer || t('jobs.noManufacturer') }} · {{ product.product_type || t('jobs.typeEquipment') }}
                          </div>
                        </q-card-section>

                        <q-card-section class="q-pt-none">
                          <div class="row q-col-gutter-sm items-end">
                            <div class="col-6 col-md-3">
                              <q-badge color="grey-8" text-color="white" :label="`${t('jobs.total')}: ${productTotalCount(product)}`" />
                            </div>
                            <div class="col-6 col-md-3">
                              <q-badge color="info" text-color="white" :label="`${t('jobs.availableConfirmed')}: ${productAvailableConfirmedOnly(product)}`" />
                            </div>
                            <div class="col-6 col-md-3">
                              <q-badge color="primary" text-color="white" :label="`${t('jobs.availableWithDrafts')}: ${productAvailableIncludingDrafts(product)}`" />
                            </div>
                            <div class="col-12 col-md-2">
                              <q-input
                                :model-value="productRequirementQty(product.id)"
                                type="number"
                                min="0"
                                :label="t('jobs.requiredQty')"
                                outlined
                                dense
                                @update:model-value="value => setProductRequirementQty(product.id, value)"
                              />
                            </div>
                            <div class="col-12 col-md-1">
                              <q-btn
                                flat
                                dense
                                no-caps
                                color="negative"
                                icon="delete"
                                :label="t('scan.clear')"
                                @click="removeRequirementRow(product.id)"
                              />
                            </div>
                          </div>
                        </q-card-section>
                      </q-card>
                    </div>
                  </q-expansion-item>
                </q-list>
              </div>
            </q-expansion-item>

            <q-expansion-item class="q-mt-md" icon="sell" :label="t('jobs.rentalRequirements')" dense>
              <div class="q-pt-sm">
                <div class="row q-col-gutter-sm q-mb-sm">
                  <div class="col-12 col-md-6">
                    <q-input
                      v-model="rentalRequirementSearch"
                      :label="t('jobs.searchRentals')"
                      outlined
                      dense
                      clearable
                    >
                      <template #prepend>
                        <q-icon name="search" />
                      </template>
                    </q-input>
                  </div>
                </div>

                <div class="text-caption text-grey-7 q-mb-sm">{{ t('jobs.rentalRequirementsHelp') }}</div>

                <q-banner
                  v-if="rentalRequirementOverbookedCount > 0"
                  class="bg-negative text-white rounded-borders q-mb-sm"
                  dense
                >
                  {{ t('jobs.rentalOverbookedBanner', { count: rentalRequirementOverbookedCount, suffix: rentalRequirementOverbookedCount === 1 ? '' : 's' }) }}
                </q-banner>

                <q-list bordered separator class="rounded-borders jobs-category-list">
                  <q-item v-for="product in filteredRentalRequirementProducts" :key="`rental-${product.id}`">
                    <q-item-section>
                      <q-item-label class="text-subtitle2">{{ product.sku }} · {{ product.name }}</q-item-label>
                      <q-item-label caption>
                        {{ product.supplier_name || t('jobs.noSupplier') }} · {{ product.category || t('jobs.uncategorized') }}
                      </q-item-label>
                      <div class="row q-gutter-xs q-mt-xs">
                        <q-badge color="grey-8" text-color="white" :label="`${t('jobs.total')}: ${productTotalCount(product)}`" />
                        <q-badge color="primary" text-color="white" :label="`${t('jobs.availableWithDrafts')}: ${productAvailableIncludingDrafts(product)}`" />
                        <q-badge
                          v-if="isRentalRequirementOverbooked(product)"
                          color="negative"
                          text-color="white"
                          :label="`${t('jobs.overBy')} ${rentalRequirementOverbookedBy(product)}`"
                        />
                      </div>
                    </q-item-section>
                    <q-item-section side top>
                      <q-input
                        :model-value="productRequirementQty(product.id)"
                        type="number"
                        min="0"
                        :label="t('jobs.requiredQty')"
                        outlined
                        dense
                        style="width: 120px"
                        @update:model-value="value => setProductRequirementQty(product.id, value)"
                      />
                    </q-item-section>
                  </q-item>
                  <q-item v-if="!filteredRentalRequirementProducts.length">
                    <q-item-section class="text-caption text-grey-6">{{ t('jobs.noRentalProductsFound') }}</q-item-section>
                  </q-item>
                </q-list>
              </div>
            </q-expansion-item>

            <EntityAttachmentsPanel
              entity-type="job"
              :entity-id="editing?.id || null"
              :title="t('jobs.jobDocuments')"
              default-category="job-document"
            />

            <q-banner v-if="dialogError" class="bg-negative text-white q-mt-sm rounded-borders" dense>
              {{ dialogError }}
            </q-banner>
          </q-form>
        </q-card-section>

        <q-card-actions :align="isPhoneDialog ? 'stretch' : 'right'" :class="isPhoneDialog ? 'q-pa-md bg-grey-2' : ''">
          <q-btn flat :class="isPhoneDialog ? 'full-width q-mb-sm' : ''" :label="t('app.actions.cancel')" @click="closeJobDialog" />
          <q-btn v-if="authStore.canEdit" color="primary" unelevated :class="isPhoneDialog ? 'full-width' : ''" :label="editing ? t('app.actions.save') : t('jobs.create')" :loading="saving" @click="saveJob" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="deleteDialogOpen" persistent>
      <q-card class="ec-card">
        <q-card-section class="row items-center">
          <q-icon name="warning" color="negative" size="md" class="q-mr-md" />
          <span>{{ t('jobs.deletePrompt', { code: deleteTarget?.job_code || '' }) }}</span>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="deleteDialogOpen = false" />
          <q-btn v-if="authStore.canEdit" color="negative" unelevated :label="t('jobs.delete')" :loading="saving" @click="doDelete" />
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

import { JOB_STATUSES, useJobsStore } from '../stores/jobs'
import { useCustomersStore } from '../stores/customers'
import { useVenuesStore } from '../stores/venues'
import { useInventoryStore } from '../stores/inventory'
import { useCustomFieldsStore } from '../stores/customFields'
import { useAuthStore } from '../stores/auth'
import { useSettingsStore } from '../stores/settings'
import { useCompactGrid } from '../composables/useCompactGrid'
import EntityAttachmentsPanel from '../components/EntityAttachmentsPanel.vue'
import { translateMaybePrefillCustomFieldLabel, translateMaybePrefillCustomFieldOption } from '../i18n/prefillContent'
import { normalizeCurrencyCode } from '../constants/currencies'

const $q = useQuasar()
const compactGrid = useCompactGrid(1024)
const route = useRoute()
const router = useRouter()
const jobsStore = useJobsStore()
const customersStore = useCustomersStore()
const venuesStore = useVenuesStore()
const inventoryStore = useInventoryStore()
const customFieldsStore = useCustomFieldsStore()
const authStore = useAuthStore()
const settingsStore = useSettingsStore()
const { t, locale } = useI18n()
const activeCurrencyCode = computed(() => normalizeCurrencyCode(settingsStore.companyProfile?.currency, 'SEK'))
const currencyHelperText = computed(() => `${t('settings.company.currencyIso')}: ${activeCurrencyCode.value}`)

const isPhoneDialog = computed(() => $q.screen.lt.md)

const pageLoading = ref(false)
const search = ref('')
const activeFilter = ref(null)
const RETURN_INFO_STORAGE_KEY = 'inventory.return-info.v1'
const showCachedOfflineBanner = computed(() => (
  jobsStore.fetchSource === 'snapshot' || inventoryStore.fetchSource === 'snapshot'
))

function customFieldLabel(label) {
  return translateMaybePrefillCustomFieldLabel(label, t)
}

function customFieldOption(option) {
  return translateMaybePrefillCustomFieldOption(option, t)
}

const statusFilters = computed(() => JOB_STATUSES.map(status => ({
  ...status,
  label: statusLabel(status.value),
})))
const statusOptions = computed(() => JOB_STATUSES.map(status => ({ label: statusLabel(status.value), value: status.value })))

const customerOptions = computed(() => customersStore.customers.map(customer => ({
  label: customer.email ? `${customer.name} · ${customer.email}` : customer.name,
  value: customer.id,
})))

const venueOptions = computed(() => venuesStore.venues.map(venue => ({
  label: [venue.name, venue.city].filter(Boolean).join(' · '),
  value: venue.id,
})))

const filteredCustomerOptions = ref([])
const filteredVenueOptions = ref([])
const filteredProductOptions = ref([])
const requirementProductSearch = ref('')
const rentalRequirementSearch = ref('')
const requirementCategoryFilter = ref(null)
const requirementBrandFilter = ref(null)
const requirementManufacturerFilter = ref(null)
const requirementTypeFilter = ref(null)
const requirementSort = ref('category_name')
const jobFieldRows = ref([])
const customerDraftFieldRows = ref([])
const venueDraftFieldRows = ref([])

const booleanValueOptions = computed(() => [
  { label: t('common.true'), value: 'true' },
  { label: t('common.false'), value: 'false' },
])

const requirementSortOptions = computed(() => [
  { label: t('jobs.sortCategoryThenName'), value: 'category_name' },
  { label: t('jobs.sortName'), value: 'name' },
  { label: t('jobs.sortSku'), value: 'sku' },
  { label: t('jobs.sortInStoreFirst'), value: 'in_store' },
])

const requirementTypeFilterOptions = computed(() => [
  { label: t('jobs.typeEquipment'), value: 'equipment' },
  { label: t('jobs.typeAccessory'), value: 'accessory' },
  { label: t('jobs.typeConsumable'), value: 'consumable' },
  { label: t('jobs.typeCase'), value: 'case' },
])

function isRentalProduct(product) {
  return Boolean(product?.is_rental_product) || String(product?.product_type || '') === 'rental'
}

const requirementSourceProducts = computed(() =>
  (inventoryStore.products || []).filter(product => !isRentalProduct(product))
)

const rentalRequirementProducts = computed(() =>
  (inventoryStore.products || []).filter(product => isRentalProduct(product))
)

const requirementBrandFilterOptions = computed(() => {
  const unique = Array.from(new Set(requirementSourceProducts.value.map(product => String(product.brand || '').trim()).filter(Boolean)))
  return unique.sort((a, b) => a.localeCompare(b)).map(value => ({ label: value, value }))
})

const requirementManufacturerFilterOptions = computed(() => {
  const unique = Array.from(new Set(requirementSourceProducts.value.map(product => String(product.manufacturer || '').trim()).filter(Boolean)))
  return unique.sort((a, b) => a.localeCompare(b)).map(value => ({ label: value, value }))
})

const categoryById = computed(() => {
  const map = new Map()
  for (const category of inventoryStore.categories) map.set(category.id, category)
  return map
})

function productCategoryPath(product) {
  if (!product) return t('jobs.uncategorized')
  const categoryId = Number(product.category_id || 0)
  if (categoryId > 0 && categoryById.value.size) {
    const names = []
    let current = categoryById.value.get(categoryId)
    let guard = 0
    while (current && guard < 20) {
      names.unshift(current.name)
      current = current.parent_id ? categoryById.value.get(current.parent_id) : null
      guard += 1
    }
    if (names.length) return names.join(' / ')
  }
  return product.category || t('jobs.uncategorized')
}

function compareProducts(a, b, sortMode) {
  const categoryA = productCategoryPath(a)
  const categoryB = productCategoryPath(b)
  const nameA = String(a.name || '').toLowerCase()
  const nameB = String(b.name || '').toLowerCase()
  const skuA = String(a.sku || '').toLowerCase()
  const skuB = String(b.sku || '').toLowerCase()

  if (sortMode === 'name') return nameA.localeCompare(nameB)
  if (sortMode === 'sku') return skuA.localeCompare(skuB)
  if (sortMode === 'in_store') {
    const inStoreDiff = Number(b.in_store_devices || 0) - Number(a.in_store_devices || 0)
    if (inStoreDiff !== 0) return inStoreDiff
    return nameA.localeCompare(nameB)
  }

  const categoryCompare = categoryA.localeCompare(categoryB)
  if (categoryCompare !== 0) return categoryCompare
  return nameA.localeCompare(nameB)
}

const productOptions = computed(() => {
  const term = requirementProductSearch.value.trim().toLowerCase()
  const categoryFilter = requirementCategoryFilter.value
  const brandFilter = requirementBrandFilter.value
  const manufacturerFilter = requirementManufacturerFilter.value
  const typeFilter = requirementTypeFilter.value

  const filtered = requirementSourceProducts.value.filter(product => {
    if (categoryFilter && productCategoryPath(product) !== categoryFilter) return false
    if (brandFilter && String(product.brand || '').trim() !== brandFilter) return false
    if (manufacturerFilter && String(product.manufacturer || '').trim() !== manufacturerFilter) return false
    if (typeFilter && product.product_type !== typeFilter) return false
    if (!term) return true
    return [
      product.sku,
      product.name,
      product.brand,
      product.manufacturer,
      productCategoryPath(product),
      product.product_type,
    ]
      .filter(Boolean)
      .some(value => String(value).toLowerCase().includes(term))
  })

  const sorted = [...filtered].sort((a, b) => compareProducts(a, b, requirementSort.value))
  return sorted.map(product => ({
    label: `${productCategoryPath(product)} · ${product.sku} · ${product.name}`,
    value: product.id,
  }))
})

const requirementCategoryFilterOptions = computed(() => {
  const unique = Array.from(new Set(requirementSourceProducts.value.map(product => productCategoryPath(product))))
  return unique.sort((a, b) => a.localeCompare(b)).map(value => ({ label: value, value }))
})

watch(customerOptions, (options) => {
  filteredCustomerOptions.value = options
}, { immediate: true })

watch(venueOptions, (options) => {
  filteredVenueOptions.value = options
}, { immediate: true })

watch(productOptions, (options) => {
  filteredProductOptions.value = options
}, { immediate: true })

function filterCustomerOptions(val, update) {
  update(() => {
    const needle = val.trim().toLowerCase()
    if (!needle) {
      filteredCustomerOptions.value = customerOptions.value
      return
    }
    filteredCustomerOptions.value = customerOptions.value.filter(option =>
      option.label.toLowerCase().includes(needle)
    )
  })
}

function filterVenueOptions(val, update) {
  update(() => {
    const needle = val.trim().toLowerCase()
    if (!needle) {
      filteredVenueOptions.value = venueOptions.value
      return
    }
    filteredVenueOptions.value = venueOptions.value.filter(option =>
      option.label.toLowerCase().includes(needle)
    )
  })
}

function filterProductOptions(val, update) {
  update(() => {
    requirementProductSearch.value = val
    filteredProductOptions.value = productOptions.value
  })
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

const columns = computed(() => [
  { name: 'job_code', label: t('jobs.jobCode'), field: 'job_code', sortable: true, align: 'left' },
  { name: 'description', label: t('jobs.description'), field: 'description', sortable: true, align: 'left' },
  { name: 'customer_name', label: t('jobs.customer'), field: 'customer_name', sortable: true, align: 'left' },
  { name: 'venue_name', label: t('jobs.venue'), field: 'venue_name', sortable: true, align: 'left' },
  { name: 'status', label: t('jobs.status'), field: 'status', sortable: true, align: 'left' },
  { name: 'sales_price', label: t('jobs.salesLabel'), field: 'sales_price', sortable: true, align: 'right' },
  { name: 'invoice_paid', label: t('jobs.invoiceLabel'), field: 'invoice_paid', sortable: true, align: 'left' },
  { name: 'start_date', label: t('jobs.start'), field: 'start_date', sortable: true, align: 'left', format: formatDate },
  { name: 'end_date', label: t('jobs.end'), field: 'end_date', sortable: true, align: 'left', format: formatDate },
  { name: 'created_at', label: t('jobs.created'), field: 'created_at', sortable: true, align: 'left', format: formatDate },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
])

const visibleJobs = computed(() => {
  const term = search.value.trim().toLowerCase()
  return jobsStore.jobs.filter(job => {
    if (activeFilter.value && job.status !== activeFilter.value) return false
    if (!term) return true
    return [job.job_code, job.description, job.customer_name, job.venue_name, job.status]
      .filter(Boolean)
      .some(value => String(value).toLowerCase().includes(term))
  })
})

const dialogOpen = ref(false)
const editing = ref(null)
const saving = ref(false)
const generatingJobCode = ref(false)
const dialogError = ref('')
const formRef = ref(null)
const focusedFromInventoryPopup = ref(false)

function hasPendingInventoryReturnContext() {
  if (typeof window === 'undefined') return false
  const raw = window.sessionStorage.getItem(RETURN_INFO_STORAGE_KEY)
  if (!raw) return false
  try {
    const parsed = JSON.parse(raw)
    return Boolean(parsed?.type && Number(parsed?.id || 0) > 0)
  } catch {
    return false
  }
}

async function closeJobDialog() {
  dialogOpen.value = false
  if (focusedFromInventoryPopup.value && hasPendingInventoryReturnContext()) {
    await router.push({ path: '/inventory' })
    return
  }
  focusedFromInventoryPopup.value = false
}

const emptyForm = () => ({
  job_code: '',
  description: '',
  customer_id: null,
  customer_name: '',
  venue_id: null,
  venue_name: '',
  status: 'draft',
  start_date: null,
  end_date: null,
  sales_price: null,
  invoice_paid: false,
  invoice_paid_at: null,
  notes: '',
})

const form = ref(emptyForm())
const emptyCustomerDraft = () => ({ name: '', email: '', phone: '', notes: '' })
const emptyVenueDraft = () => ({ name: '', address: '', city: '', notes: '' })
const customerDraft = ref(emptyCustomerDraft())
const venueDraft = ref(emptyVenueDraft())
const requirementRows = ref([])
const requirementDraft = ref({ product_id: null, quantity_required: 1 })

const filteredRequirementProducts = computed(() => {
  const term = requirementProductSearch.value.trim().toLowerCase()
  const categoryFilter = requirementCategoryFilter.value
  const brandFilter = requirementBrandFilter.value
  const manufacturerFilter = requirementManufacturerFilter.value
  const typeFilter = requirementTypeFilter.value

  const filtered = requirementSourceProducts.value.filter((product) => {
    if (categoryFilter && productCategoryPath(product) !== categoryFilter) return false
    if (brandFilter && String(product.brand || '').trim() !== brandFilter) return false
    if (manufacturerFilter && String(product.manufacturer || '').trim() !== manufacturerFilter) return false
    if (typeFilter && product.product_type !== typeFilter) return false
    if (!term) return true
    return [
      product.sku,
      product.name,
      product.brand,
      product.manufacturer,
      productCategoryPath(product),
      product.product_type,
    ]
      .filter(Boolean)
      .some(value => String(value).toLowerCase().includes(term))
  })

  return [...filtered].sort((a, b) => compareProducts(a, b, requirementSort.value))
})

const filteredRentalRequirementProducts = computed(() => {
  const term = rentalRequirementSearch.value.trim().toLowerCase()
  const filtered = rentalRequirementProducts.value.filter((product) => {
    if (!term) return true
    return [
      product.sku,
      product.name,
      product.category,
      product.supplier_name,
      product.external_reference,
    ]
      .filter(Boolean)
      .some(value => String(value).toLowerCase().includes(term))
  })
  return [...filtered].sort((a, b) => compareProducts(a, b, 'name'))
})

const rentalRequirementOverbookedCount = computed(() => (
  rentalRequirementProducts.value.filter(product => isRentalRequirementOverbooked(product)).length
))

const requirementCategoryGroups = computed(() => {
  const byCategoryId = new Map()
  const uncategorized = []

  for (const product of filteredRequirementProducts.value) {
    const categoryId = Number(product.category_id || 0)
    if (!categoryId) {
      uncategorized.push(product)
      continue
    }
    if (!byCategoryId.has(categoryId)) byCategoryId.set(categoryId, [])
    byCategoryId.get(categoryId).push(product)
  }

  for (const products of byCategoryId.values()) {
    products.sort((a, b) => compareProducts(a, b, requirementSort.value))
  }
  uncategorized.sort((a, b) => compareProducts(a, b, requirementSort.value))

  const groups = []

  const hasCategoryTree = Array.isArray(inventoryStore.categoryTree) && inventoryStore.categoryTree.length > 0
  if (hasCategoryTree) {
    // Use category hierarchy ordering for a real tree-like product browser.
    const traverse = (nodes, depth = 0, pathPrefix = '') => {
      for (const node of nodes || []) {
        const nodeName = String(node?.name || '').trim() || t('jobs.uncategorized')
        const labelPath = pathPrefix ? `${pathPrefix} / ${nodeName}` : nodeName
        const directProducts = byCategoryId.get(node.id) || []

        let descendantCount = directProducts.length
        for (const child of node.children || []) {
          descendantCount += countDescendants(child)
        }

        if (descendantCount > 0) {
          groups.push({
            key: `cat-${node.id}`,
            label: labelPath,
            depth,
            products: directProducts,
            subtreeCount: descendantCount,
          })
        }

        traverse(node.children || [], depth + 1, labelPath)
      }
    }

    const countDescendants = (node) => {
      const directProducts = (byCategoryId.get(node.id) || []).length
      const childCount = (node.children || []).reduce((sum, child) => sum + countDescendants(child), 0)
      return directProducts + childCount
    }

    traverse(inventoryStore.categoryTree)
  } else {
    const fallbackGrouped = new Map()
    for (const product of filteredRequirementProducts.value) {
      const key = productCategoryPath(product)
      if (!fallbackGrouped.has(key)) fallbackGrouped.set(key, [])
      fallbackGrouped.get(key).push(product)
    }
    for (const [label, products] of [...fallbackGrouped.entries()].sort((a, b) => a[0].localeCompare(b[0]))) {
      groups.push({ key: label, label, depth: 0, products, subtreeCount: products.length })
    }
  }

  if (uncategorized.length) {
    groups.push({
      key: 'cat-uncategorized',
      label: t('jobs.uncategorized'),
      depth: 0,
      products: uncategorized,
      subtreeCount: uncategorized.length,
    })
  }

  return groups
})

function reservedByProductForStatuses(statuses) {
  const startDate = normalizeDate(form.value.start_date)
  const endDate = normalizeDate(form.value.end_date)
  if (!startDate || !endDate) return new Map()

  const reservingStatuses = new Set(statuses)
  const jobsById = new Map(jobsStore.jobs.map(job => [job.id, job]))
  const reserved = new Map()

  for (const req of jobsStore.requirements) {
    const job = jobsById.get(req.job_id)
    if (!job) continue
    if (editing.value && req.job_id === editing.value.id) continue
    if (!reservingStatuses.has(String(job.status || '').toLowerCase())) continue

    const otherStart = normalizeDate(job.start_date)
    const otherEnd = normalizeDate(job.end_date)
    if (!otherStart || !otherEnd) continue
    if (endDate < otherStart || otherEnd < startDate) continue

    const productId = req.product_id
    const qty = Math.max(Number(req.quantity_required || 0), Number(req.quantity_picked || 0))
    if (qty <= 0) continue
    reserved.set(productId, Number(reserved.get(productId) || 0) + qty)
  }

  return reserved
}

const overlappingReservedConfirmedOnlyByProduct = computed(() => (
  reservedByProductForStatuses(['confirmed', 'in_progress'])
))

const overlappingReservedIncludingDraftsByProduct = computed(() => (
  reservedByProductForStatuses(['draft', 'confirmed', 'in_progress'])
))

const operationalDeviceCountsByProduct = computed(() => {
  const now = new Date()
  const counts = new Map()

  for (const device of inventoryStore.devices || []) {
    const status = String(device.status || '').toLowerCase()
    const condition = String(device.condition || '').toLowerCase()
    const retired = device.retire_date ? new Date(device.retire_date) <= now : false
    if (retired) continue
    if (status === 'maintenance') continue
    if (condition === 'damaged') continue
    counts.set(device.product_id, Number(counts.get(device.product_id) || 0) + 1)
  }

  return counts
})

const availableNowCountsByProduct = computed(() => {
  const now = new Date()
  const counts = new Map()

  for (const device of inventoryStore.devices || []) {
    const status = String(device.status || '').toLowerCase()
    const condition = String(device.condition || '').toLowerCase()
    const retired = device.retire_date ? new Date(device.retire_date) <= now : false
    if (retired) continue
    if (condition === 'damaged') continue
    if (status !== 'available') continue
    counts.set(device.product_id, Number(counts.get(device.product_id) || 0) + 1)
  }

  return counts
})

function productRequirementQty(productId) {
  return Number(requirementRows.value.find(item => item.product_id === productId)?.quantity_required || 0)
}

function setProductRequirementQty(productId, value) {
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

function productTotalCount(product) {
  return Number(product?.total_devices || 0)
}

function productEventoryAvailableQty(product) {
  return Math.max(0, Number(product?.eventory_available_qty || 0))
}

function eventoryPacklistsForProduct(product) {
  if (!Array.isArray(product?.eventory_packlists)) return []
  return product.eventory_packlists.filter(item => item && typeof item === 'object')
}

function eventoryPacklistReservesDate(packlist, startDate, endDate) {
  const status = String(packlist?.job_status || '').toLowerCase()
  if (status && ['cancelled', 'canceled', 'completed', 'returned'].includes(status)) return false

  const packStart = normalizeDate(packlist?.start_date)
  const packEnd = normalizeDate(packlist?.end_date)

  if (!startDate || !endDate) {
    const source = String(packlist?.source || '').toLowerCase()
    const outQty = Math.max(0, Number(packlist?.out || 0))
    return source === 'active' && outQty > 0
  }

  if (!packStart || !packEnd) return false
  return !(endDate < packStart || packEnd < startDate)
}

function eventoryReservedQtyForProduct(product, startDate, endDate) {
  let reserved = 0
  for (const packlist of eventoryPacklistsForProduct(product)) {
    if (!eventoryPacklistReservesDate(packlist, startDate, endDate)) continue
    const quantity = Math.max(Number(packlist?.quantity || 0), Number(packlist?.out || 0), 0)
    reserved += quantity
  }
  return reserved
}

function rentalAvailableByMap(product, reservedMap) {
  const startDate = normalizeDate(form.value.start_date)
  const endDate = normalizeDate(form.value.end_date)
  const base = productEventoryAvailableQty(product)
  const externalReserved = eventoryReservedQtyForProduct(product, startDate, endDate)
  const internalReserved = Number(reservedMap.get(product?.id) || 0)
  return Math.max(base - externalReserved - internalReserved, 0)
}

function rentalRequirementOverbookedBy(product) {
  const required = Math.max(0, Number(productRequirementQty(product?.id) || 0))
  const available = rentalAvailableByMap(product, overlappingReservedIncludingDraftsByProduct.value)
  return Math.max(required - available, 0)
}

function isRentalRequirementOverbooked(product) {
  return rentalRequirementOverbookedBy(product) > 0
}

function productAvailableByMap(product, reservedMap) {
  if (!product) return 0
  const startDate = normalizeDate(form.value.start_date)
  const endDate = normalizeDate(form.value.end_date)
  if (!startDate || !endDate) {
    return Number(availableNowCountsByProduct.value.get(product.id) || 0)
  }
  const total = Number(operationalDeviceCountsByProduct.value.get(product.id) || 0)
  const reserved = Number(reservedMap.get(product.id) || 0)
  return Math.max(total - reserved, 0)
}

function productAvailableConfirmedOnly(product) {
  if (String(product?.product_type || '').toLowerCase() === 'rental' || product?.is_rental_product) {
    return rentalAvailableByMap(product, overlappingReservedConfirmedOnlyByProduct.value)
  }
  return productAvailableByMap(product, overlappingReservedConfirmedOnlyByProduct.value)
}

function productAvailableIncludingDrafts(product) {
  if (String(product?.product_type || '').toLowerCase() === 'rental' || product?.is_rental_product) {
    return rentalAvailableByMap(product, overlappingReservedIncludingDraftsByProduct.value)
  }
  return productAvailableByMap(product, overlappingReservedIncludingDraftsByProduct.value)
}

function addRequirementRow() {
  const productId = requirementDraft.value.product_id
  const qty = Number(requirementDraft.value.quantity_required || 0)
  if (!productId || qty <= 0) return

  const existing = requirementRows.value.find(item => item.product_id === productId)
  if (existing) {
    existing.quantity_required = Number(existing.quantity_required || 0) + qty
  } else {
    requirementRows.value.push({ product_id: productId, quantity_required: qty, quantity_picked: 0, notes: null })
  }
  requirementDraft.value = { product_id: null, quantity_required: 1 }
}

function removeRequirementRow(productId) {
  requirementRows.value = requirementRows.value.filter(item => item.product_id !== productId)
}

const projectedJobPrice = computed(() => {
  const productsById = new Map((inventoryStore.products || []).map(product => [product.id, product]))
  const startKey = dateSortKey(form.value.start_date)
  const endKey = dateSortKey(form.value.end_date)
  const rentalDays = startKey && endKey && endKey >= startKey
    ? Math.max(1, Math.floor((new Date(form.value.end_date).getTime() - new Date(form.value.start_date).getTime()) / 86400000) + 1)
    : 1

  let total = 0
  for (const row of requirementRows.value) {
    const product = productsById.get(row.product_id)
    if (!product) continue
    const qty = Math.max(0, Number(row.quantity_required || 0))
    const unit = Number(product.rental_price || product.daily_rate || 0)
    total += qty * unit * rentalDays
  }
  return Number(total.toFixed(2))
})

watch(
  () => form.value.invoice_paid,
  (paid) => {
    if (paid && !form.value.invoice_paid_at) {
      form.value.invoice_paid_at = normalizeDate(new Date())
    }
    if (!paid) {
      form.value.invoice_paid_at = null
    }
  }
)

watch(
  () => form.value.start_date,
  (startDate) => {
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
  }
)

async function loadData() {
  pageLoading.value = true
  try {
    await Promise.all([
      jobsStore.fetchAll(),
      customersStore.fetchAll(),
      venuesStore.fetchAll(),
      inventoryStore.fetchAll(),
      customFieldsStore.fetchDefinitions(),
      settingsStore.fetchCompanyProfile(),
    ])
  } finally {
    pageLoading.value = false
  }
}

function createEmptyJobFieldRows() {
  const defs = (customFieldsStore.definitions || []).filter(def => def.entity_type === 'job' && def.is_active !== false)
  return defs.map(def => ({
    field_definition_id: def.id,
    label: def.label,
    value_type: def.value_type,
    options: def.options || [],
    value: null,
  }))
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

function createEmptyVenueFieldRows() {
  const defs = (customFieldsStore.definitions || []).filter(def => def.entity_type === 'venue' && def.is_active !== false)
  return defs.map(def => ({
    field_definition_id: def.id,
    label: def.label,
    value_type: def.value_type,
    options: def.options || [],
    value: null,
  }))
}

async function loadJobFieldRows(entityId) {
  if (!entityId) {
    jobFieldRows.value = createEmptyJobFieldRows()
    return
  }
  try {
    const data = await customFieldsStore.fetchEntityValues('job', entityId)
    jobFieldRows.value = Array.isArray(data?.values) ? data.values.map(value => ({ ...value })) : createEmptyJobFieldRows()
  } catch {
    jobFieldRows.value = createEmptyJobFieldRows()
  }
}

async function focusJobFromQuery() {
  const focusId = Number(route.query.focusJobId || 0)
  if (!focusId) return
  focusedFromInventoryPopup.value = hasPendingInventoryReturnContext()
  const job = jobsStore.jobs.find(item => item.id === focusId)
  if (job) {
    openEdit(job)
  }

  const nextQuery = { ...route.query }
  delete nextQuery.focusJobId
  await router.replace({ path: '/jobs', query: nextQuery })
}

onMounted(async () => {
  await loadData()
  await focusJobFromQuery()
})

watch(() => route.query.focusJobId, async () => {
  await focusJobFromQuery()
})

async function generateJobCode() {
  generatingJobCode.value = true
  try {
    const code = await jobsStore.generateJobCode('JOB-')
    if (code) form.value.job_code = code
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('jobs.failedGenerateJobCode') })
  } finally {
    generatingJobCode.value = false
  }
}

async function openCreate() {
  editing.value = null
  form.value = emptyForm()
  customerDraft.value = emptyCustomerDraft()
  venueDraft.value = emptyVenueDraft()
  requirementRows.value = []
  requirementDraft.value = { product_id: null, quantity_required: 1 }
  requirementProductSearch.value = ''
  rentalRequirementSearch.value = ''
  requirementCategoryFilter.value = null
  requirementBrandFilter.value = null
  requirementManufacturerFilter.value = null
  requirementTypeFilter.value = null
  requirementSort.value = 'category_name'
  await loadJobFieldRows(null)
  customerDraftFieldRows.value = createEmptyCustomerFieldRows()
  venueDraftFieldRows.value = createEmptyVenueFieldRows()
  dialogError.value = ''
  await generateJobCode()
  dialogOpen.value = true
}

async function openEdit(job) {
  editing.value = job
  form.value = {
    job_code: job.job_code ?? '',
    description: job.description ?? '',
    customer_id: job.customer_id ?? null,
    customer_name: job.customer_name ?? '',
    venue_id: job.venue_id ?? null,
    venue_name: job.venue_name ?? '',
    status: job.status ?? 'draft',
    start_date: normalizeDate(job.start_date),
    end_date: normalizeDate(job.end_date),
    sales_price: job.sales_price == null ? null : Number(job.sales_price),
    invoice_paid: Boolean(job.invoice_paid),
    invoice_paid_at: normalizeDate(job.invoice_paid_at),
    notes: job.notes ?? '',
  }
  customerDraft.value = emptyCustomerDraft()
  venueDraft.value = emptyVenueDraft()
  requirementRows.value = jobsStore.requirements
    .filter(req => req.job_id === job.id)
    .map(req => ({
      product_id: req.product_id,
      quantity_required: req.quantity_required,
      quantity_picked: req.quantity_picked,
      notes: req.notes || null,
    }))
  requirementDraft.value = { product_id: null, quantity_required: 1 }
  requirementProductSearch.value = ''
  rentalRequirementSearch.value = ''
  requirementCategoryFilter.value = null
  requirementBrandFilter.value = null
  requirementManufacturerFilter.value = null
  requirementTypeFilter.value = null
  requirementSort.value = 'category_name'
  await loadJobFieldRows(job.id)
  customerDraftFieldRows.value = createEmptyCustomerFieldRows()
  venueDraftFieldRows.value = createEmptyVenueFieldRows()
  dialogError.value = ''
  dialogOpen.value = true
}

function customerNameForId(id) {
  return customersStore.customers.find(customer => customer.id === id)?.name ?? ''
}

function venueNameForId(id) {
  return venuesStore.venues.find(venue => venue.id === id)?.name ?? ''
}

async function ensureCustomer() {
  if (form.value.customer_id) return form.value.customer_id
  const name = customerDraft.value.name.trim()
  if (!name) return null
  const created = await customersStore.createCustomer({ ...customerDraft.value, name })
  if (customerDraftFieldRows.value.length) {
    await customFieldsStore.saveEntityValues('customer', created.id, customerDraftFieldRows.value.map(row => ({
      field_definition_id: row.field_definition_id,
      value: row.value,
    })))
  }
  form.value.customer_id = created.id
  form.value.customer_name = created.name
  return created.id
}

async function ensureVenue() {
  if (form.value.venue_id) return form.value.venue_id
  const name = venueDraft.value.name.trim()
  if (!name) return null
  const created = await venuesStore.createVenue({ ...venueDraft.value, name })
  if (venueDraftFieldRows.value.length) {
    await customFieldsStore.saveEntityValues('venue', created.id, venueDraftFieldRows.value.map(row => ({
      field_definition_id: row.field_definition_id,
      value: row.value,
    })))
  }
  form.value.venue_id = created.id
  form.value.venue_name = created.name
  return created.id
}

async function saveJob() {
  const valid = await formRef.value?.validate()
  if (!valid) return

  dialogError.value = ''
  saving.value = true
  try {
    await ensureCustomer()
    await ensureVenue()

    if (!form.value.customer_id && !form.value.customer_name?.trim()) {
      dialogError.value = t('jobs.selectOrCreateCustomer')
      return
    }
    if (!form.value.venue_id && !form.value.venue_name?.trim()) {
      dialogError.value = t('jobs.selectOrCreateVenue')
      return
    }

    const payload = {
      ...form.value,
      customer_name: form.value.customer_name || customerNameForId(form.value.customer_id),
      venue_name: form.value.venue_name || venueNameForId(form.value.venue_id),
      start_date: normalizeDate(form.value.start_date),
      end_date: normalizeDate(form.value.end_date),
      sales_price: form.value.sales_price == null || form.value.sales_price === '' ? null : Number(form.value.sales_price),
      invoice_paid: Boolean(form.value.invoice_paid),
      invoice_paid_at: form.value.invoice_paid ? normalizeDate(form.value.invoice_paid_at) : null,
    }

    let savedJob
    if (editing.value) {
      savedJob = await jobsStore.updateJob(editing.value.id, payload)
    } else {
      savedJob = await jobsStore.createJob(payload)
    }

    await jobsStore.bulkUpsertRequirements(savedJob.id, requirementRows.value.map(item => ({
      product_id: item.product_id,
      quantity_required: Number(item.quantity_required || 0),
      quantity_picked: Number(item.quantity_picked || 0),
      notes: item.notes || null,
    })))

    await customFieldsStore.saveEntityValues('job', savedJob.id, jobFieldRows.value.map(row => ({
      field_definition_id: row.field_definition_id,
      value: row.value,
    })))

    dialogOpen.value = false
    $q.notify({ type: 'positive', message: editing.value ? t('jobs.jobUpdated') : t('jobs.jobCreated') })
    if (focusedFromInventoryPopup.value && hasPendingInventoryReturnContext()) {
      await router.push({ path: '/inventory' })
      return
    }
    focusedFromInventoryPopup.value = false
  } catch (error) {
    dialogError.value = error?.response?.data?.detail || t('common.errorOccurred')
  } finally {
    saving.value = false
  }
}

const deleteDialogOpen = ref(false)
const deleteTarget = ref(null)

function confirmDelete(job) {
  deleteTarget.value = job
  deleteDialogOpen.value = true
}

async function doDelete() {
  saving.value = true
  try {
    await jobsStore.deleteJob(deleteTarget.value.id)
    deleteDialogOpen.value = false
    $q.notify({ type: 'positive', message: t('jobs.jobDeleted') })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('common.deleteFailed') })
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.jobs-category-list {
  background: var(--jobs-category-bg, #ffffff);
}

:global(body.body--dark) {
  --jobs-category-bg: #161b22;
}

:global(body.body--light) {
  --jobs-category-bg: #ffffff;
}
</style>
