<template>
  <q-page class="scan-page q-pa-md">
    <div class="scan-shell">
      <q-card class="scanner-card q-pa-lg q-mb-md">
        <div class="text-center q-mb-md">
          <div class="scanner-icon-wrap q-mb-sm">
            <q-icon name="qr_code_scanner" size="42px" color="white" />
          </div>
          <div class="text-h5 text-white">{{ t('scan.title') }}</div>
          <div class="text-caption text-grey-4">{{ t('scan.subtitle') }}</div>
        </div>

        <div class="row q-mb-md">
          <q-btn-toggle
            :model-value="scanActionGroup"
            toggle-color="primary"
            color="grey-8"
            text-color="grey-2"
            unelevated
            no-caps
            spread
            class="full-width"
            :options="scanActionGroupButtonsDisplay"
            @update:model-value="onScanGroupChanged"
          />
        </div>

        <div v-if="scanActionVariantButtons.length" class="row q-gutter-sm q-mb-md justify-center">
          <q-btn-toggle
            :model-value="scanAction"
            toggle-color="primary"
            color="grey-9"
            text-color="grey-3"
            unelevated
            no-caps
            :options="scanActionVariantButtons"
            @update:model-value="onScanVariantChanged"
          />
        </div>

        <div class="row items-center justify-center q-gutter-xs q-mb-sm">
          <div class="text-caption text-grey-5">{{ t('scan.hotkeysHint') }}</div>
          <q-btn
            flat
            dense
            round
            size="sm"
            icon="help_outline"
            color="grey-5"
            @click="showShortcutHelp = true"
          >
            <q-tooltip>{{ t('scan.showKeyboardShortcuts') }}</q-tooltip>
          </q-btn>
        </div>

        <div v-if="scanAction === 'job_out' || scanAction === 'rental_job_out'" class="q-mb-md">
          <div class="step-row">
            <div class="step-item" :class="activeJobCode ? 'step-done' : 'step-active'">
              <span class="step-dot">1</span>
              <span>{{ t('scan.selectJob') }}</span>
            </div>
            <div class="step-line" />
            <div class="step-item" :class="activeJobCode ? 'step-active' : 'step-pending'">
              <span class="step-dot">2</span>
              <span>{{ scanAction === 'rental_job_out' ? t('scan.scanRental') : t('scan.scanDevice') }}</span>
            </div>
          </div>
        </div>

        <div v-if="scanAction === 'move'" class="q-mb-md">
          <div class="step-row">
            <div class="step-item" :class="moveDestinationReady ? 'step-done' : 'step-active'">
              <span class="step-dot">1</span>
              <span>{{ t('scan.selectOrScanDestination') }}</span>
            </div>
            <div class="step-line" />
            <div class="step-item" :class="moveDestinationReady ? 'step-active' : 'step-pending'">
              <span class="step-dot">2</span>
              <span>{{ t('scan.scanDevices') }}</span>
            </div>
          </div>
        </div>

        <q-banner v-if="scanAction === 'move' && moveDestinationReady" class="bg-teal-8 text-white q-mb-md rounded-borders">
          {{ t('scan.destination') }}: {{ moveDestinationLabel }}
          <q-btn flat dense no-caps class="q-ml-sm" :label="t('scan.changeDestination')" @click="clearMoveDestination" />
          <div class="text-caption q-mt-xs">{{ t('scan.step2DestinationHelp') }}</div>
        </q-banner>

        <q-banner v-if="scanAction === 'move' && !moveDestinationReady" class="bg-amber-8 text-black q-mb-md rounded-borders" dense>
          {{ t('scan.step1RequiredMove') }}
        </q-banner>

        <q-banner v-if="(scanAction === 'job_out' || scanAction === 'rental_job_out') && activeJobCode" class="bg-primary text-white q-mb-md rounded-borders">
          {{ t('scan.jobSelected') }}: {{ activeJobCode }}
          <span v-if="activeJobId"> (#{{ activeJobId }})</span>
          <q-btn flat dense no-caps class="q-ml-sm" :label="t('scan.change')" @click="clearActiveJob" />
        </q-banner>

        <q-banner v-if="(scanAction === 'job_out' || scanAction === 'rental_job_out') && activeJobCode" class="bg-teal-8 text-white q-mb-md rounded-borders" dense>
          {{ t('scan.step2ScanAndSubmit', { item: scanAction === 'rental_job_out' ? t('scan.rental').toLowerCase() : t('scan.device').toLowerCase(), submit: scanSubmitLabel }) }}
        </q-banner>

        <div class="row q-col-gutter-sm q-mb-sm items-end">
          <div class="col-12 col-md-4" v-if="scanAction === 'move'">
            <q-select
              v-model="scanZoneId"
              :options="locationSelectOptions"
              :label="t('scan.moveToLocation')"
              outlined
              dense
              emit-value
              map-options
              :disable="!!scanCaseDeviceId"
            />
          </div>
          <div class="col-12 col-md-4" v-if="scanAction === 'move'">
            <q-select
              v-model="scanCaseDeviceId"
              :options="caseMoveSelectOptions"
              :label="t('scan.orMoveIntoCase')"
              outlined
              dense
              clearable
              emit-value
              map-options
              :disable="!!scanZoneId"
            />
          </div>
          <div class="col-12 col-md-4" v-if="scanAction === 'move'">
            <q-input v-model="scanZoneCode" :label="t('scan.orScanLocationCaseIdentifier')" :placeholder="t('scan.locationCasePlaceholder')" outlined dense />
          </div>
          <div class="col-12 col-md-4" v-if="scanAction === 'move' && moveDestinationReady">
            <q-btn color="grey-8" text-color="white" icon="restart_alt" :label="t('scan.changeDestination')" no-caps unelevated @click="clearMoveDestination" />
          </div>
          <div class="col-12 col-md-4" v-if="(scanAction === 'job_out' || scanAction === 'rental_job_out') && !activeJobCode">
            <q-select
              v-model="scanJobId"
              :options="jobSelectOptions"
              :label="t('scan.selectJob')"
              outlined
              dense
              clearable
              emit-value
              map-options
            />
          </div>
          <div class="col-12 col-md-4" v-if="scanAction === 'job_in'">
            <q-toggle
              v-model="globalCheckin"
              :label="t('scan.globalCheckInNoJob')"
              color="primary"
              class="q-mb-sm"
              @update:model-value="onGlobalCheckinChanged"
            />
            <q-select
              v-model="scanJobId"
              :options="intakeJobSelectOptions"
              :label="t('scan.selectJobWithCheckedOutDevices')"
              outlined
              dense
              clearable
              emit-value
              map-options
              class="q-mb-sm"
              :disable="globalCheckin"
            />
            <q-input v-model="scanJobCode" :label="t('scan.jobCode')" :placeholder="t('scan.jobCodePlaceholder')" outlined dense :disable="globalCheckin" />
          </div>
          <div class="col-12 col-md-4" v-if="scanAction === 'rental_job_in'">
            <q-select
              v-model="scanJobId"
              :options="jobSelectOptions"
              :label="t('scan.selectJob')"
              outlined
              dense
              clearable
              emit-value
              map-options
              class="q-mb-sm"
            />
            <q-input v-model="scanJobCode" :label="t('scan.jobCode')" :placeholder="t('scan.jobCodePlaceholder')" outlined dense />
          </div>
          <div class="col-12 col-md-4" v-if="scanAction === 'maintenance'">
            <q-select v-model="scanMaintenanceType" :options="maintenanceTypeOptions" :label="t('scan.maintenanceType')" outlined dense emit-value map-options />
          </div>
          <div class="col-12 col-md-4" v-if="scanAction === 'maintenance'">
            <q-select v-model="scanIntervalMode" :options="maintenanceIntervalModeOptions" :label="t('scan.intervalMode')" outlined dense emit-value map-options />
          </div>
          <div class="col-12 col-md-4" v-if="scanAction === 'maintenance'">
            <q-input v-model.number="scanIntervalValue" type="number" min="1" :label="scanIntervalMode === 'runtime' ? t('scan.hoursInterval') : t('scan.daysInterval')" outlined dense />
          </div>
        </div>

        <div class="row q-gutter-sm q-mb-md justify-center">
          <q-btn-toggle
            v-model="inputMode"
            toggle-color="primary"
            color="grey-9"
            text-color="grey-3"
            unelevated
            no-caps
            :options="inputModeButtons"
            @update:model-value="onInputModeChanged"
          />
        </div>

        <div v-if="inputMode === 'camera'" class="camera-wrap q-mb-md">
          <video ref="videoRef" class="camera-video" playsinline muted />
          <div v-if="cameraError" class="camera-overlay text-negative">{{ cameraError }}</div>
          <div v-else-if="!cameraRunning" class="camera-overlay text-grey-4">{{ t('scan.startingCamera') }}</div>
        </div>

        <div v-if="inputMode === 'nfc'" class="nfc-wrap q-mb-md text-center">
          <q-icon name="nfc" size="44px" :color="nfcRunning ? 'primary' : 'grey-5'" />
          <div class="text-caption q-mt-sm" :class="nfcRunning ? 'text-primary' : 'text-grey-5'">
            {{ nfcRunning ? t('scan.nfcReady') : nfcError || t('scan.startingNfc') }}
          </div>
        </div>

        <q-form @submit.prevent="runScanAction">
          <div class="row q-col-gutter-sm items-end">
            <div class="col-12 col-md-10">
              <q-input
                ref="scanCodeInputRef"
                v-model="scanCode"
                :label="t('scan.scanCode')"
                outlined
                dense
                :placeholder="scanCodePlaceholder"
                @keyup.enter="runScanAction"
              />
            </div>
            <div class="col-12 col-md-2">
              <q-btn color="primary" unelevated icon="qr_code_scanner" :label="scanSubmitLabel" type="submit" :loading="saving" class="full-width" />
            </div>
          </div>
        </q-form>

        <div v-if="canShowMaintenanceActions" class="row q-gutter-sm q-mt-md">
          <q-btn
            color="primary"
            unelevated
            icon="build_circle"
            :label="t('scan.markNeedsMaintenance')"
            :loading="saving"
            @click="scheduleMaintenanceFromLookup"
          />
          <q-btn
            color="warning"
            unelevated
            icon="warning"
            :label="t('scan.markAsDefective')"
            :loading="saving"
            @click="openDefectDialog"
          />
        </div>

        <q-card v-if="scanAction === 'lookup' && lastLookupResult" flat bordered class="q-mt-md lookup-details-card">
          <q-card-section>
            <div class="text-subtitle1 q-mb-sm">{{ t('scan.lookupDetails') }}</div>

            <div v-if="lookupDeviceEntries.length" class="q-mb-sm">
              <div class="text-caption text-grey-4 q-mb-xs">{{ t('scan.device') }}</div>
              <div v-for="entry in lookupDeviceEntries" :key="`device-${entry.key}`" class="lookup-row">
                <span class="lookup-label">{{ entry.label }}</span>
                <span class="lookup-value">{{ formatLookupValue(entry.value) }}</span>
              </div>
            </div>

            <div v-if="lookupProductEntries.length" class="q-mb-sm">
              <div class="text-caption text-grey-4 q-mb-xs">{{ t('scan.product') }}</div>
              <div v-for="entry in lookupProductEntries" :key="`product-${entry.key}`" class="lookup-row">
                <span class="lookup-label">{{ entry.label }}</span>
                <span class="lookup-value">{{ formatLookupValue(entry.value) }}</span>
              </div>
            </div>

            <div v-if="lookupLocationEntries.length" class="q-mb-sm">
              <div class="text-caption text-grey-4 q-mb-xs">{{ t('scan.location') }}</div>
              <div v-for="entry in lookupLocationEntries" :key="`location-${entry.key}`" class="lookup-row">
                <span class="lookup-label">{{ entry.label }}</span>
                <span class="lookup-value">{{ formatLookupValue(entry.value) }}</span>
              </div>
            </div>

            <div>
              <div class="text-caption text-grey-4 q-mb-xs">{{ t('scan.maintenanceHistory') }}</div>
              <div v-if="lookupMaintenanceEntries.length">
                <div
                  v-for="item in lookupMaintenanceEntries"
                  :key="`maintenance-${item.id}`"
                  class="lookup-maintenance-item"
                >
                  <span>#{{ item.id }} {{ item.maintenance_type }} - {{ item.status }}</span>
                  <span>{{ formatLookupValue(item.scheduled_date || item.completed_date || item.created_at) }}</span>
                </div>
              </div>
              <div v-else class="text-grey-5">{{ t('scan.noMaintenanceRecords') }}</div>
            </div>
          </q-card-section>
        </q-card>

        <q-banner v-if="scanResultMessage" class="q-mt-md rounded-borders" :class="scanResultSuccess ? 'bg-positive text-white' : 'bg-negative text-white'" dense>
          {{ scanResultMessage }}
        </q-banner>

        <q-card v-if="scanAction === 'move'" flat bordered class="q-mt-md recent-moves-card">
          <q-card-section class="q-pb-sm">
            <div class="row items-center">
              <div class="text-subtitle2 col">{{ t('scan.recentlyMovedLastFive') }}</div>
              <q-btn
                v-if="recentMovedDevices.length"
                flat
                dense
                no-caps
                icon="clear_all"
                :label="t('scan.clear')"
                @click="recentMovedDevices = []"
              />
            </div>
            <div class="text-caption recent-moves-help">{{ t('scan.recentMovesHelp') }}</div>
          </q-card-section>
          <q-list dense separator>
            <q-item v-for="item in recentMovedDevices" :key="item.id">
              <q-item-section>
                <q-item-label>
                  <span class="text-weight-medium">{{ item.asset_tag }}</span>
                  <span v-if="item.product_name"> · {{ item.product_name }}</span>
                </q-item-label>
                <q-item-label caption>
                  {{ item.destination }} · {{ formatScanTime(item.moved_at) }}
                </q-item-label>
                <q-item-label caption>{{ item.message }}</q-item-label>
              </q-item-section>
            </q-item>
            <q-item v-if="!recentMovedDevices.length">
              <q-item-section>
                <q-item-label caption>{{ t('scan.noMovesYet') }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>
      </q-card>

      <q-card class="ec-card q-pa-md" v-if="activeWorkflowJob">
        <div class="text-subtitle1 q-mb-sm">
          {{ (scanAction === 'job_in' || scanAction === 'rental_job_in') ? t('scan.checkInReturnList') : t('scan.checkOutPickList') }} {{ t('scan.forJob', { jobCode: activeWorkflowJob.job_code }) }}
        </div>
        <q-table
          :rows="workflowRequirements"
          :columns="workflowColumns"
          row-key="product_id"
          flat
          bordered
          dense
          :grid="compactGrid"
          :hide-header="compactGrid"
          :pagination="{ rowsPerPage: 15 }"
          :rows-per-page-options="[15, 30, 50]"
        >
          <template #item="props">
            <div class="q-pa-xs col-12 col-sm-6 col-md-4">
              <q-card flat bordered class="scan-workflow-card">
                <q-card-section class="q-pb-sm">
                  <div class="text-subtitle2">{{ props.row.product_name }}</div>
                </q-card-section>
                <q-card-section class="q-pt-none">
                  <div class="row q-col-gutter-xs">
                    <div class="col-6">
                      <q-badge color="grey-8" text-color="white" :label="t('scan.requiredCount', { count: props.row.quantity_required })" />
                    </div>
                    <div class="col-6">
                      <q-badge color="blue-8" text-color="white" :label="t('scan.pickedCount', { count: props.row.quantity_picked })" />
                    </div>
                    <div class="col-6">
                      <q-badge color="info" text-color="white" :label="t('scan.checkedOutCount', { count: props.row.checked_out })" />
                    </div>
                    <div class="col-6">
                      <q-badge :color="props.row.remaining > 0 ? 'amber-7' : 'green-8'" text-color="black" :label="t('scan.remainingCount', { count: props.row.remaining })" />
                    </div>
                    <div class="col-12">
                      <q-badge :color="props.row.available > 0 ? 'primary' : 'grey-7'" text-color="white" :label="t('scan.availableInStoreCount', { count: props.row.available })" />
                    </div>
                  </div>
                </q-card-section>
              </q-card>
            </div>
          </template>
          <template #body-cell-checked_out="props">
            <q-td :props="props">
              <q-badge :color="props.value > 0 ? 'info' : 'grey-7'" :label="String(props.value)" />
            </q-td>
          </template>
          <template #body-cell-remaining="props">
            <q-td :props="props">
              <q-badge
                :color="props.value > 0 ? 'amber-7' : 'green-8'"
                text-color="black"
                :label="String(props.value)"
              />
            </q-td>
          </template>
          <template #body-cell-available="props">
            <q-td :props="props">
              <q-badge :color="props.value > 0 ? 'primary' : 'grey-7'" :label="String(props.value)" />
            </q-td>
          </template>
        </q-table>
      </q-card>

      <q-card class="ec-card q-pa-md" v-if="scanAction === 'job_in'">
        <div class="text-subtitle1 q-mb-sm">{{ t('scan.currentlyCheckedOutDevices', { count: checkedOutDeviceRows.length }) }}</div>
        <div v-if="isTightScreen" class="checked-out-grid">
          <q-card v-for="row in checkedOutDeviceRows" :key="row.id" flat bordered class="checked-out-card">
            <q-card-section class="q-pb-sm">
              <div class="text-subtitle2">{{ row.asset_tag || t('scan.unknownAsset') }}</div>
              <div class="text-caption text-grey-6">{{ row.product_name }}</div>
            </q-card-section>
            <q-card-section class="q-pt-none">
              <div class="row q-col-gutter-xs">
                <div class="col-12">
                  <q-badge color="blue-8" text-color="white" :label="t('scan.locationValue', { value: row.location_name })" />
                </div>
                <div class="col-12">
                  <q-badge color="grey-8" text-color="white" :label="t('scan.conditionValue', { value: row.condition })" />
                </div>
              </div>
            </q-card-section>
          </q-card>
          <div v-if="!checkedOutDeviceRows.length" class="text-grey-5 text-caption">
            {{ t('scan.noDevicesCurrentlyCheckedOut') }}
          </div>
        </div>
        <q-table
          v-else
          :rows="checkedOutDeviceRows"
          :columns="checkedOutColumns"
          row-key="id"
          flat
          bordered
          dense
          :pagination="{ rowsPerPage: 15 }"
          :rows-per-page-options="[15, 30, 50]"
          :no-data-label="t('scan.noDevicesCurrentlyCheckedOut')"
        />
      </q-card>

      <q-card class="ec-card q-pa-md" v-if="isRentalScanMode">
        <div class="text-subtitle1 q-mb-sm">{{ t('scan.rentalScanTimeline') }}</div>
        <div class="text-caption text-grey-6 q-mb-sm">{{ t('scan.rentalScanTimelineHelp') }}</div>
        <q-list dense separator>
          <q-item v-for="item in recentRentalAuditRows" :key="item.id">
            <q-item-section>
              <q-item-label>
                <q-badge class="q-mr-xs" :color="rentalActionColor(item.action)" text-color="white" :label="rentalActionLabel(item.action)" />
                {{ item.product_name || item.scan_code || t('scan.rental') }}
                <span v-if="item.job_code"> · {{ item.job_code }}</span>
              </q-item-label>
              <q-item-label caption>{{ item.message }}</q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-item-label caption>{{ formatScanTime(item.created_at) }}</q-item-label>
            </q-item-section>
          </q-item>
          <q-item v-if="!recentRentalAuditRows.length">
            <q-item-section>
              <q-item-label caption>{{ t('scan.noRentalScansYet') }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <q-dialog v-model="showShortcutHelp">
        <q-card style="width: 320px; max-width: min(460px, 95vw)">
          <q-card-section class="row items-center q-pb-none">
            <div class="text-h6">{{ t('scan.scannerShortcuts') }}</div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup />
          </q-card-section>
          <q-card-section>
            <q-list dense>
              <q-item>
                <q-item-section>
                  <q-item-label><strong>Alt+1..6</strong> {{ t('scan.shortcutSwitchPrimaryMode') }}</q-item-label>
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section>
                  <q-item-label><strong>Alt+Shift+Left/Right</strong> {{ t('scan.shortcutCycleSubmode') }}</q-item-label>
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section>
                  <q-item-label><strong>?</strong> {{ t('scan.shortcutOpenHelp') }}</q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
        </q-card>
      </q-dialog>

      <q-dialog v-model="defectDialogOpen" persistent>
        <q-card style="width: 95vw; max-width: 500px">
          <q-card-section class="row items-center q-pb-none">
            <div class="text-h6">{{ t('scan.defectReportDialogTitle') }}</div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup :disable="defectSaving" />
          </q-card-section>
          <q-card-section class="q-pt-sm">
            <q-input
              v-model="defectTitle"
              :label="t('scan.defectTitleLabel')"
              :placeholder="t('scan.defectTitlePlaceholder')"
              outlined
              dense
              class="q-mb-sm"
              :rules="[v => !!v?.trim() || t('scan.required')]"
              ref="defectTitleRef"
            />
            <q-input
              v-model="defectDescription"
              :label="t('scan.defectDescriptionLabel')"
              :placeholder="t('scan.defectDescriptionPlaceholder')"
              outlined
              dense
              type="textarea"
              autogrow
              class="q-mb-sm"
            />
            <q-select
              v-model="defectSeverity"
              :label="t('scan.defectSeverityLabel')"
              :options="defectSeverityOptions"
              outlined
              dense
              emit-value
              map-options
              class="q-mb-sm"
            />
            <q-file
              v-model="defectFiles"
              :label="t('scan.defectPhotosLabel')"
              outlined
              dense
              multiple
              accept="image/*"
              clearable
            >
              <template #prepend>
                <q-icon name="photo_camera" />
              </template>
            </q-file>
          </q-card-section>
          <q-card-actions align="right" class="q-pb-md q-pr-md">
            <q-btn flat :label="t('app.actions.cancel')" v-close-popup :disable="defectSaving" />
            <q-btn
              color="warning"
              unelevated
              icon="warning"
              :label="t('scan.markAsDefective')"
              :loading="defectSaving"
              @click="submitDefectReport"
            />
          </q-card-actions>
        </q-card>
      </q-dialog>
    </div>
  </q-page>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'

import { api } from '../boot/axios'
import { useInventoryStore } from '../stores/inventory'
import { useJobsStore } from '../stores/jobs'
import { useCompactGrid } from '../composables/useCompactGrid'

const store = useInventoryStore()
const jobsStore = useJobsStore()
const $q = useQuasar()
const { t } = useI18n()
const compactGrid = useCompactGrid(1024)
const saving = ref(false)

const scanAction = ref('lookup')
const scanCode = ref('')
const scanZoneId = ref(null)
const scanCaseDeviceId = ref(null)
const scanZoneCode = ref('')
const scanJobCode = ref('')
const scanJobId = ref(null)
const globalCheckin = ref(false)
const activeJobCode = ref('')
const activeJobId = ref(null)
const scanMaintenanceType = ref('inspection')
const scanIntervalMode = ref('calendar')
const scanIntervalValue = ref(null)
const scanResultMessage = ref('')
const scanResultSuccess = ref(false)
const lastLookupCode = ref('')
const lastLookupResult = ref(null)
const lastIntakeResult = ref(null)
const recentMovedDevices = ref([])

const inputMode = ref('keyboard')
const scanCodeInputRef = ref(null)
const videoRef = ref(null)
const cameraRunning = ref(false)
const cameraError = ref('')
let cameraStream = null
let cameraTimer = null
const nfcRunning = ref(false)
const nfcError = ref('')
let nfcReader = null
const showShortcutHelp = ref(false)

const defectDialogOpen = ref(false)
const defectTitle = ref('')
const defectDescription = ref('')
const defectSeverity = ref('medium')
const defectFiles = ref(null)
const defectSaving = ref(false)
const defectTitleRef = ref(null)

const supportsCamera = computed(() => {
  return typeof navigator !== 'undefined'
    && !!navigator.mediaDevices
    && typeof navigator.mediaDevices.getUserMedia === 'function'
    && typeof window !== 'undefined'
    && typeof window.BarcodeDetector !== 'undefined'
})

const supportsNfc = computed(() => {
  return typeof window !== 'undefined' && typeof window.NDEFReader !== 'undefined'
})

const isTightScreen = computed(() => compactGrid.value)
const RENTAL_SCAN_ACTIONS = ['rental_receive', 'rental_job_out', 'rental_job_in', 'rental_return_supplier']

const scanActionGroupButtons = computed(() => [
  { label: t('scan.lookup'), value: 'lookup', icon: 'search' },
  { label: t('scan.move'), value: 'move', icon: 'swap_horiz' },
  { label: t('scan.maintenance'), value: 'maintenance', icon: 'build_circle' },
  { label: t('scan.outtake'), value: 'outtake', icon: 'shopping_cart_checkout' },
  { label: t('scan.intake'), value: 'intake', icon: 'assignment_return' },
  { label: t('scan.rentalOps'), value: 'rental_ops', icon: 'inventory_2' },
])

const scanActionGroupButtonsDisplay = computed(() =>
  $q.screen.lt.sm
    ? scanActionGroupButtons.value.map(({ icon, value, label }) => ({ icon, value, 'aria-label': label, title: label }))
    : scanActionGroupButtons.value
)

const scanActionGroupState = ref({
  outtake: 'job_out',
  intake: 'job_in',
  rental_ops: 'rental_receive',
})

function actionToGroup(action) {
  if (action === 'job_out' || action === 'rental_job_out') return 'outtake'
  if (action === 'job_in' || action === 'rental_job_in') return 'intake'
  if (action === 'rental_receive' || action === 'rental_return_supplier') return 'rental_ops'
  return action
}

function defaultActionForGroup(group) {
  if (group === 'outtake' || group === 'intake' || group === 'rental_ops') {
    return scanActionGroupState.value[group]
  }
  return group
}

const scanActionGroup = computed(() => actionToGroup(scanAction.value))

const scanActionVariantButtons = computed(() => {
  if (scanActionGroup.value === 'outtake') {
    return [
      { label: t('scan.deviceOut'), value: 'job_out', icon: 'shopping_cart_checkout' },
      { label: t('scan.rentalOut'), value: 'rental_job_out', icon: 'local_shipping' },
    ]
  }
  if (scanActionGroup.value === 'intake') {
    return [
      { label: t('scan.deviceIn'), value: 'job_in', icon: 'assignment_return' },
      { label: t('scan.rentalIn'), value: 'rental_job_in', icon: 'assignment_returned' },
    ]
  }
  if (scanActionGroup.value === 'rental_ops') {
    return [
      { label: t('scan.receive'), value: 'rental_receive', icon: 'inventory' },
      { label: t('scan.returnSupplier'), value: 'rental_return_supplier', icon: 'undo' },
    ]
  }
  return []
})

function onScanGroupChanged(group) {
  const nextAction = defaultActionForGroup(group)
  if (scanAction.value === nextAction) return
  scanAction.value = nextAction
  onActionChanged()
}

function onScanVariantChanged(nextAction) {
  if (scanAction.value === nextAction) return
  const group = actionToGroup(nextAction)
  if (group === 'outtake' || group === 'intake' || group === 'rental_ops') {
    scanActionGroupState.value[group] = nextAction
  }
  scanAction.value = nextAction
  onActionChanged()
}

function cycleScanVariant(direction) {
  const variants = scanActionVariantButtons.value
  if (!variants.length) return
  const currentIndex = variants.findIndex((option) => option.value === scanAction.value)
  const fallbackIndex = 0
  const startIndex = currentIndex >= 0 ? currentIndex : fallbackIndex
  const nextIndex = (startIndex + direction + variants.length) % variants.length
  const next = variants[nextIndex]
  if (!next) return
  onScanVariantChanged(next.value)
}

function isEditableElement(target) {
  if (!target || typeof target.closest !== 'function') return false
  const tag = String(target.tagName || '').toLowerCase()
  if (tag === 'input' || tag === 'textarea' || tag === 'select') return true
  if (target.isContentEditable) return true
  return !!target.closest('[contenteditable="true"]')
}

function onGlobalScanHotkey(event) {
  if ((event.key === '?' || (event.key === '/' && event.shiftKey)) && !isEditableElement(event.target)) {
    event.preventDefault()
    showShortcutHelp.value = true
    return
  }

  if (!event.altKey || event.metaKey || event.ctrlKey) return

  if (event.shiftKey && event.key === 'ArrowLeft') {
    event.preventDefault()
    cycleScanVariant(-1)
    return
  }
  if (event.shiftKey && event.key === 'ArrowRight') {
    event.preventDefault()
    cycleScanVariant(1)
    return
  }

  if (event.shiftKey) return
  if (isEditableElement(event.target)) return

  const groupByDigit = {
    '1': 'lookup',
    '2': 'move',
    '3': 'maintenance',
    '4': 'outtake',
    '5': 'intake',
    '6': 'rental_ops',
  }
  const group = groupByDigit[event.key]
  if (!group) return
  event.preventDefault()
  onScanGroupChanged(group)
}

const inputModeButtons = computed(() => {
  const buttons = [{ label: t('scan.keyboard'), value: 'keyboard' }]
  if (supportsCamera.value) buttons.push({ label: t('scan.camera'), value: 'camera' })
  if (supportsNfc.value) buttons.push({ label: 'NFC', value: 'nfc' })
  return buttons
})

const maintenanceTypeOptions = computed(() => [
  { label: t('scan.maintenanceInspection'), value: 'inspection' },
  { label: t('scan.maintenanceCleaning'), value: 'cleaning' },
  { label: t('scan.maintenanceRepair'), value: 'repair' },
  { label: t('scan.maintenanceCalibration'), value: 'calibration' },
  { label: t('scan.maintenancePatTest'), value: 'pat_test' },
  { label: t('scan.maintenanceScheduled'), value: 'scheduled' },
])

const maintenanceIntervalModeOptions = computed(() => [
  { label: t('scan.calendarTime'), value: 'calendar' },
  { label: t('scan.runtimeHours'), value: 'runtime' },
])

const workflowColumns = computed(() => [
  { name: 'product', label: t('scan.product'), field: 'product_name', align: 'left', sortable: true },
  { name: 'required', label: t('scan.required'), field: 'quantity_required', align: 'left', sortable: true },
  { name: 'picked', label: t('scan.picked'), field: 'quantity_picked', align: 'left', sortable: true },
  { name: 'checked_out', label: t('scan.checkedOut'), field: 'checked_out', align: 'left', sortable: true },
  { name: 'remaining', label: t('scan.remaining'), field: 'remaining', align: 'left', sortable: true },
  { name: 'available', label: t('scan.availableInStore'), field: 'available', align: 'left', sortable: true },
])

const scanSubmitLabel = computed(() => {
  if (scanAction.value === 'move') {
    return moveDestinationReady.value ? t('scan.moveDevice') : t('scan.setDestination')
  }
  if (scanAction.value === 'job_out' || scanAction.value === 'rental_job_out') {
    return activeJobCode.value ? (scanAction.value === 'rental_job_out' ? t('scan.scanRental') : t('scan.scanDevice')) : t('scan.selectJob')
  }
  if (scanAction.value === 'rental_receive') return t('scan.receiveRental')
  if (scanAction.value === 'rental_return_supplier') return t('scan.returnRental')
  if (scanAction.value === 'rental_job_in' && !selectedOrTypedJob()) return t('scan.selectJob')
  if (scanAction.value === 'job_in' && !globalCheckin.value && !selectedOrTypedJob()) {
    return t('scan.selectJob')
  }
  return t('scan.scan')
})

const scanCodePlaceholder = computed(() => {
  if (scanAction.value === 'move') {
    return moveDestinationReady.value
      ? t('scan.scanDeviceCodePlaceholder')
      : t('scan.scanDestinationFirstPlaceholder')
  }
  if ((scanAction.value === 'job_out' || scanAction.value === 'rental_job_out') && !activeJobCode.value) {
    return t('scan.selectScanTypeJobCodeFirst')
  }
  if (RENTAL_SCAN_ACTIONS.includes(scanAction.value)) {
    return t('scan.scanRentalSkuOrExternalRef')
  }
  return t('scan.scanDeviceCodePlaceholder')
})

const isRentalScanMode = computed(() => RENTAL_SCAN_ACTIONS.includes(scanAction.value))

const recentRentalAuditRows = computed(() => {
  return (store.auditLogs || [])
    .filter(item => RENTAL_SCAN_ACTIONS.includes(String(item.action || '').toLowerCase()))
    .slice(0, 20)
})

function rentalActionLabel(action) {
  const key = String(action || '').toLowerCase()
  if (key === 'rental_receive') return t('scan.received')
  if (key === 'rental_job_out') return t('scan.toJob')
  if (key === 'rental_job_in') return t('scan.fromJob')
  if (key === 'rental_return_supplier') return t('scan.supplierReturn')
  return key || t('scan.rental')
}

function rentalActionColor(action) {
  const key = String(action || '').toLowerCase()
  if (key === 'rental_receive') return 'positive'
  if (key === 'rental_job_out') return 'primary'
  if (key === 'rental_job_in') return 'teal'
  if (key === 'rental_return_supplier') return 'orange-8'
  return 'grey-7'
}

const moveDestinationReady = computed(() => scanAction.value === 'move' && (!!scanZoneId.value || !!scanCaseDeviceId.value))

const moveDestinationLabel = computed(() => {
  if (!moveDestinationReady.value) return t('scan.none')
  if (scanCaseDeviceId.value) {
    const caseDevice = (store.devices || []).find(item => item.id === scanCaseDeviceId.value)
    return caseDevice?.asset_tag ? `${t('scan.case')} ${caseDevice.asset_tag}` : `${t('scan.case')} #${scanCaseDeviceId.value}`
  }
  const zone = zoneById.value.get(scanZoneId.value)
  if (!zone) return `${t('scan.location')} #${scanZoneId.value}`
  return zone.code ? `${zone.name} (${zone.code})` : zone.name
})

const maintenanceTargetDeviceId = computed(() => {
  if (scanAction.value === 'lookup') {
    return Number(lastLookupResult.value?.device_id || 0)
  }
  if (scanAction.value === 'job_in') {
    return Number(lastIntakeResult.value?.device_id || 0)
  }
  return 0
})

const maintenanceTargetCode = computed(() => {
  if (scanAction.value === 'lookup') {
    return String(lastLookupCode.value || '').trim()
  }
  if (scanAction.value === 'job_in') {
    return String(lastIntakeResult.value?.asset_tag || '').trim()
  }
  return ''
})

const canShowMaintenanceActions = computed(() => {
  if (scanAction.value === 'lookup') {
    return !!lastLookupResult.value?.success && Number(lastLookupResult.value?.device_id || 0) > 0
  }
  if (scanAction.value === 'job_in') {
    return !!lastIntakeResult.value?.success && Number(lastIntakeResult.value?.device_id || 0) > 0
  }
  return false
})

const checkedOutColumns = computed(() => [
  { name: 'asset_tag', label: t('scan.assetTag'), field: 'asset_tag', align: 'left', sortable: true },
  { name: 'product_name', label: t('scan.product'), field: 'product_name', align: 'left', sortable: true },
  { name: 'location_name', label: t('scan.location'), field: 'location_name', align: 'left', sortable: true },
  { name: 'condition', label: t('scan.condition'), field: 'condition', align: 'left', sortable: true },
])

const caseMoveSelectOptions = computed(() => {
  return (store.devices || [])
    .filter((device) => {
      const product = productById.value.get(device.product_id)
      return product?.product_type === 'case'
    })
    .sort((a, b) => String(a.asset_tag || '').localeCompare(String(b.asset_tag || '')))
    .map((device) => {
      const product = productById.value.get(device.product_id)
      return {
        label: `${device.asset_tag || `${t('scan.case')} #${device.id}`} · ${product?.name || t('scan.case')}`,
        value: device.id,
      }
    })
})

const locationSelectOptions = computed(() => {
  const flat = [{ label: t('scan.unassigned'), value: null }]
  const walk = (nodes, prefix = '') => {
    for (const node of nodes || []) {
      const label = prefix ? `${prefix} / ${node.name}` : node.name
      flat.push({ label, value: node.id })
      walk(node.children || [], label)
    }
  }
  walk(store.zoneTree)
  return flat
})

const jobSelectOptions = computed(() => {
  return [...jobsStore.jobs]
    .sort((a, b) => String(a.job_code || '').localeCompare(String(b.job_code || '')))
    .map(job => ({
      label: `${job.job_code}${job.description ? ` · ${job.description}` : ''}`,
      value: job.id,
    }))
})

const pickedByJobId = computed(() => {
  const map = new Map()
  for (const req of jobsStore.requirements) {
    const picked = Number(req.quantity_picked || 0)
    if (picked <= 0) continue
    map.set(req.job_id, Number(map.get(req.job_id) || 0) + picked)
  }
  return map
})

const intakeJobSelectOptions = computed(() => {
  return [...jobsStore.jobs]
    .filter(job => Number(pickedByJobId.value.get(job.id) || 0) > 0)
    .sort((a, b) => String(a.job_code || '').localeCompare(String(b.job_code || '')))
    .map(job => ({
      label: `${job.job_code} · ${pickedByJobId.value.get(job.id)} ${t('scan.checkedOut').toLowerCase()}`,
      value: job.id,
    }))
})

const zoneByCode = computed(() => {
  const map = new Map()
  for (const zone of store.zones) {
    for (const raw of [zone.code, zone.barcode, zone.qr_code, zone.rfid]) {
      const code = String(raw || '').trim().toUpperCase()
      if (!code) continue
      map.set(code, zone)
    }
  }
  return map
})

const caseDeviceByCode = computed(() => {
  const map = new Map()
  for (const device of store.devices || []) {
    const product = productById.value.get(device.product_id)
    if (!product || product.product_type !== 'case') continue
    for (const raw of [device.asset_tag, device.barcode, device.qr_code, device.rfid, device.serial_number]) {
      const code = String(raw || '').trim().toUpperCase()
      if (!code) continue
      map.set(code, device)
    }
  }
  return map
})

const productById = computed(() => {
  const out = new Map()
  for (const product of store.products) out.set(product.id, product)
  return out
})

const zoneById = computed(() => {
  const map = new Map()
  for (const zone of store.zones) map.set(zone.id, zone)
  return map
})

const checkedOutDeviceRows = computed(() => {
  return (store.checkedOutDevices || []).map((device) => ({
    id: device.device_id,
    asset_tag: device.asset_tag,
    product_id: device.product_id,
    product_name: device.product_name || productById.value.get(device.product_id)?.name || `Product #${device.product_id}`,
    location_name: device.location_name || zoneById.value.get(device.location_zone_id)?.name || t('scan.unassigned'),
    condition: device.condition || '-',
  }))
})

const checkedOutCountByProduct = computed(() => {
  const map = new Map()
  for (const row of checkedOutDeviceRows.value) {
    map.set(row.product_id, Number(map.get(row.product_id) || 0) + 1)
  }
  return map
})

const rentalFlowCountsByProduct = computed(() => {
  const map = new Map()
  for (const row of store.auditLogs || []) {
    if (!row?.success) continue
    const productId = Number(row.product_id || 0)
    if (!productId) continue
    const action = String(row.action || '').toLowerCase()
    if (!RENTAL_SCAN_ACTIONS.includes(action)) continue

    const bucket = map.get(productId) || { received: 0, job_out: 0, job_in: 0, returned: 0 }
    if (action === 'rental_receive') bucket.received += 1
    else if (action === 'rental_job_out') bucket.job_out += 1
    else if (action === 'rental_job_in') bucket.job_in += 1
    else if (action === 'rental_return_supplier') bucket.returned += 1
    map.set(productId, bucket)
  }
  return map
})

const activeWorkflowJob = computed(() => {
  if ((scanAction.value === 'job_out' || scanAction.value === 'rental_job_out') && activeJobId.value) {
    return jobsStore.jobs.find(item => item.id === activeJobId.value) || null
  }
  if (scanAction.value === 'job_in' || scanAction.value === 'rental_job_in') {
    if (scanJobId.value) {
      return jobsStore.jobs.find(item => item.id === scanJobId.value) || null
    }
    const normalizedCode = String(scanJobCode.value || '').trim().toUpperCase()
    if (!normalizedCode) return null
    return jobsStore.jobs.find(item => String(item.job_code || '').toUpperCase() === normalizedCode) || null
  }
  return null
})

const workflowRequirements = computed(() => {
  const job = activeWorkflowJob.value
  if (!job) return []

  const reqs = jobsStore.requirements.filter(item => item.job_id === job.id)
  return reqs.map((item) => {
    const product = productById.value.get(item.product_id)
    const isRental = Boolean(product?.is_rental_product) || String(product?.product_type || '') === 'rental'
    const rentalFlow = rentalFlowCountsByProduct.value.get(item.product_id) || { received: 0, job_out: 0, job_in: 0, returned: 0 }
    const available = isRental
      ? Math.max(rentalFlow.received + rentalFlow.job_in - rentalFlow.job_out - rentalFlow.returned, 0)
      : store.devices.filter(device => device.product_id === item.product_id && device.status === 'available').length
    const required = Number(item.quantity_required || 0)
    const picked = Number(item.quantity_picked || 0)
    const remaining = Math.max(required - picked, 0)
    const checkedOut = isRental
      ? Math.max(rentalFlow.job_out - rentalFlow.job_in, 0)
      : Number(checkedOutCountByProduct.value.get(item.product_id) || 0)
    return {
      product_id: item.product_id,
      product_name: product?.name || `Product #${item.product_id}`,
      quantity_required: required,
      quantity_picked: picked,
      checked_out: checkedOut,
      remaining,
      available,
    }
  })
})

const lookupDeviceEntries = computed(() => detailEntries(lastLookupResult.value?.device_details, [
  ['asset_tag', 'Asset tag'],
  ['serial_number', 'Serial number'],
  ['barcode', 'Barcode'],
  ['qr_code', 'QR code'],
  ['rfid', 'RFID'],
  ['status', 'Status'],
  ['condition', 'Condition'],
  ['location_zone_name', 'Location'],
  ['usage_hours', 'Usage hours'],
  ['purchase_date', 'Purchase date'],
  ['warranty_end_date', 'Warranty end'],
  ['retire_date', 'Retire date'],
  ['notes', 'Notes'],
]))
const lookupProductEntries = computed(() => detailEntries(lastLookupResult.value?.product_details, [
  ['sku', 'SKU'],
  ['name', 'Name'],
  ['category', 'Category'],
  ['brand', 'Brand'],
  ['manufacturer', 'Manufacturer'],
  ['product_type', 'Type'],
  ['weight_kg', 'Weight (kg)'],
  ['height_cm', 'Height (cm)'],
  ['width_cm', 'Width (cm)'],
  ['depth_cm', 'Depth (cm)'],
  ['maintenance_interval_days', 'Maintenance interval (days)'],
  ['power_consumption_watts', 'Power (W)'],
  ['daily_rate', 'Daily rate'],
]))
const lookupLocationEntries = computed(() => detailEntries(lastLookupResult.value?.location_details, [
  ['code', 'Code'],
  ['name', 'Name'],
  ['zone_type', 'Type'],
  ['is_active', 'Active'],
]))
const lookupMaintenanceEntries = computed(() => {
  const raw = lastLookupResult.value?.maintenance_details
  return Array.isArray(raw) ? raw : []
})

function detailEntries(source, fields) {
  if (!source || typeof source !== 'object') return []
  const rows = []
  for (const [key, label] of fields || []) {
    const value = source[key]
    if (value === null || value === undefined || value === '') continue
    rows.push({ key, label, value })
  }
  return rows
}

function formatLookupValue(value) {
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'boolean') return value ? t('common.true') : t('common.false')
  if (typeof value === 'number') return String(value)
  if (typeof value === 'string') return value
  if (Array.isArray(value)) return value.join(', ')
  return JSON.stringify(value)
}

async function loadData() {
  try {
    await Promise.all([
      store.fetchAll(),
      jobsStore.fetchAll(),
      store.fetchCheckedOutDevices(),
      store.fetchAuditLogs(200),
    ])
  } catch (error) {
    if (error?.response?.status === 401) {
      scanResultMessage.value = t('scan.sessionExpiredRedirecting')
      scanResultSuccess.value = false
      return
    }
    scanResultMessage.value = t('scan.unableLoadScanData')
    scanResultSuccess.value = false
  }
}

function clearActiveJob() {
  activeJobCode.value = ''
  activeJobId.value = null
  scanJobId.value = null
}

function clearMoveDestination() {
  scanZoneId.value = null
  scanCaseDeviceId.value = null
  scanZoneCode.value = ''
  scanCode.value = ''
  scanResultMessage.value = t('scan.destinationClearedStep1')
  scanResultSuccess.value = true
  focusScanCodeInput()
}

function focusScanCodeInput() {
  nextTick(() => {
    const input = scanCodeInputRef.value
    if (input && typeof input.focus === 'function') {
      input.focus()
    }
  })
}

function formatScanTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function trackRecentMove(response, scannedCode) {
  const assetTag = String(response?.asset_tag || scannedCode || '').trim() || t('scan.unknownDevice')
  const productName = String(response?.product_name || '').trim()
  const message = String(response?.message || t('scan.moved')).trim()
  const destination = moveDestinationLabel.value
  const entry = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    moved_at: new Date().toISOString(),
    asset_tag: assetTag,
    product_name: productName,
    destination,
    message,
  }
  recentMovedDevices.value = [entry, ...recentMovedDevices.value].slice(0, 5)
}

function onActionChanged() {
  scanCode.value = ''
  scanResultMessage.value = ''
  scanResultSuccess.value = false
  scanJobCode.value = ''
  scanJobId.value = null
  globalCheckin.value = false
  scanZoneId.value = null
  scanCaseDeviceId.value = null
  scanZoneCode.value = ''
  if (scanAction.value !== 'lookup') {
    lastLookupResult.value = null
  }
  if (scanAction.value !== 'job_in') {
    lastIntakeResult.value = null
  }
  if (scanAction.value !== 'job_out' && scanAction.value !== 'rental_job_out') {
    clearActiveJob()
  }
  if (scanAction.value !== 'move') {
    recentMovedDevices.value = []
  }
  focusScanCodeInput()
}

function onGlobalCheckinChanged(value) {
  if (!value) return
  scanJobCode.value = ''
  scanJobId.value = null
}

function resolveZoneIdFromCode(value) {
  const normalized = String(value || '').trim().toUpperCase()
  if (!normalized) return null
  return zoneByCode.value.get(normalized)?.id ?? null
}

function resolveCaseDeviceIdFromCode(value) {
  const normalized = String(value || '').trim().toUpperCase()
  if (!normalized) return null
  return caseDeviceByCode.value.get(normalized)?.id ?? null
}

function selectedOrTypedJob() {
  if (scanJobId.value) {
    return jobsStore.jobs.find(job => job.id === scanJobId.value) || null
  }
  const normalizedCode = String(scanJobCode.value || '').trim().toUpperCase()
  if (!normalizedCode) return null
  return jobsStore.jobs.find(job => String(job.job_code || '').toUpperCase() === normalizedCode) || null
}

function selectedOrTypedJobCode() {
  const job = selectedOrTypedJob()
  return job?.job_code || null
}

async function refreshCheckedOutForIntake() {
  if (scanAction.value !== 'job_in') {
    await store.fetchCheckedOutDevices()
    return
  }

  if (globalCheckin.value) {
    await store.fetchCheckedOutDevices()
    return
  }

  const jobCode = selectedOrTypedJobCode()
  if (jobCode) {
    await store.fetchCheckedOutDevices(jobCode)
    return
  }

  await store.fetchCheckedOutDevices()
}

async function scheduleMaintenanceFromLookup() {
  const lookupCode = maintenanceTargetCode.value
  if (!lookupCode) return

  saving.value = true
  scanResultMessage.value = ''
  scanResultSuccess.value = false
  try {
    const response = await store.processScan({
      scan_code: lookupCode,
      action: 'maintenance',
      maintenance_type: scanMaintenanceType.value,
      interval_mode: scanIntervalMode.value,
      interval_value: scanIntervalValue.value,
    })
    await jobsStore.fetchAll()
    scanResultMessage.value = response.message || t('scan.maintenanceScheduled')
    scanResultSuccess.value = !!response.success
  } catch (error) {
    scanResultMessage.value = error?.response?.data?.detail || t('scan.maintenanceScheduleFailed')
    scanResultSuccess.value = false
  } finally {
    saving.value = false
  }
}

const defectSeverityOptions = computed(() => [
  { label: t('scan.defectSeverityLow'), value: 'low' },
  { label: t('scan.defectSeverityMedium'), value: 'medium' },
  { label: t('scan.defectSeverityHigh'), value: 'high' },
  { label: t('scan.defectSeverityCritical'), value: 'critical' },
])

function openDefectDialog() {
  const deviceId = maintenanceTargetDeviceId.value
  if (!deviceId) {
    scanResultMessage.value = t('scan.scanDeviceFirst')
    scanResultSuccess.value = false
    return
  }
  defectTitle.value = ''
  defectDescription.value = ''
  defectSeverity.value = 'medium'
  defectFiles.value = null
  defectDialogOpen.value = true
}

async function submitDefectReport() {
  const deviceId = maintenanceTargetDeviceId.value
  if (!deviceId) return
  const title = String(defectTitle.value || '').trim()
  if (!title) {
    if (defectTitleRef.value) defectTitleRef.value.validate()
    return
  }

  defectSaving.value = true
  try {
    const { data: report } = await api.post('/api/v1/inventory/defect-reports', {
      device_id: deviceId,
      title,
      description: String(defectDescription.value || '').trim() || null,
      severity: defectSeverity.value || 'medium',
    })

    const files = defectFiles.value
      ? (Array.isArray(defectFiles.value) ? defectFiles.value : [defectFiles.value])
      : []

    let uploadFailed = false
    for (const file of files) {
      try {
        const formData = new FormData()
        formData.append('file', file)
        formData.append('entity_type', 'defect_report')
        formData.append('entity_id', String(report.id))
        formData.append('category', 'photo')
        await api.post('/api/v1/storage/files', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      } catch (uploadError) {
        console.error('Photo upload failed:', uploadError)
        uploadFailed = true
      }
    }

    defectDialogOpen.value = false
    scanResultMessage.value = uploadFailed
      ? t('scan.defectPhotoUploadFailed')
      : t('scan.defectReportCreated')
    scanResultSuccess.value = !uploadFailed
  } catch (error) {
    scanResultMessage.value = error?.response?.data?.detail || t('scan.defectReportFailed')
    scanResultSuccess.value = false
  } finally {
    defectSaving.value = false
  }
}

async function runScanAction() {
  const code = String(scanCode.value || '').trim()

  if (scanAction.value === 'move' && !moveDestinationReady.value) {
    const destinationCode = String(scanZoneCode.value || code || '').trim()
    const resolvedZoneId = resolveZoneIdFromCode(destinationCode)
    const resolvedCaseDeviceId = resolveCaseDeviceIdFromCode(destinationCode)
    if (resolvedCaseDeviceId) {
      scanCaseDeviceId.value = resolvedCaseDeviceId
      scanZoneId.value = null
      scanZoneCode.value = ''
      scanCode.value = ''
      const caseDevice = (store.devices || []).find(item => item.id === resolvedCaseDeviceId)
      scanResultMessage.value = t('scan.destinationSetToCaseStep2', { case: caseDevice?.asset_tag || `#${resolvedCaseDeviceId}` })
      scanResultSuccess.value = true
      focusScanCodeInput()
      return
    }
    if (resolvedZoneId) {
      scanZoneId.value = resolvedZoneId
      scanCaseDeviceId.value = null
      scanZoneCode.value = ''
      scanCode.value = ''
      const zone = zoneById.value.get(resolvedZoneId)
      scanResultMessage.value = t('scan.destinationSetToLocationStep2', { location: zone?.name || `${t('scan.location').toLowerCase()} #${resolvedZoneId}` })
      scanResultSuccess.value = true
      focusScanCodeInput()
      return
    }
    scanResultMessage.value = t('scan.step1RequiredSelectDestinationOrScan')
    scanResultSuccess.value = false
    focusScanCodeInput()
    return
  }

  if ((scanAction.value === 'job_out' || scanAction.value === 'rental_job_out') && !activeJobCode.value) {
    let job = selectedOrTypedJob()
    if (!job && code) {
      const normalizedCode = code.toUpperCase()
      job = jobsStore.jobs.find(item => String(item.job_code || '').toUpperCase() === normalizedCode) || null
    }
    if (!job) {
      scanResultMessage.value = t('scan.selectEnterScanValidJobCodeFirst')
      scanResultSuccess.value = false
      return
    }
    activeJobCode.value = job.job_code
    activeJobId.value = job.id
    scanJobId.value = job.id
    scanJobCode.value = job.job_code

    if (!code || code.toUpperCase() === String(job.job_code || '').toUpperCase()) {
      scanCode.value = ''
      scanResultMessage.value = t('scan.jobSelectedScanCodesNow', { jobCode: job.job_code, item: scanAction.value === 'rental_job_out' ? t('scan.rental').toLowerCase() : t('scan.device').toLowerCase() })
      scanResultSuccess.value = true
      focusScanCodeInput()
      return
    }
  }

  if (scanAction.value === 'job_in') {
    if (!globalCheckin.value) {
      const job = selectedOrTypedJob()
      if (!job) {
        scanResultMessage.value = t('scan.selectValidJobForIntakeOrGlobal')
        scanResultSuccess.value = false
        return
      }
      scanJobCode.value = job.job_code
      scanJobId.value = job.id
    }
  }

  if (scanAction.value === 'rental_job_in') {
    const job = selectedOrTypedJob()
    if (!job) {
      scanResultMessage.value = t('scan.selectValidJobForRentalIntake')
      scanResultSuccess.value = false
      return
    }
    scanJobCode.value = job.job_code
    scanJobId.value = job.id
  }

  if (!code) {
    scanResultMessage.value = RENTAL_SCAN_ACTIONS.includes(scanAction.value)
      ? t('scan.scanOrTypeRentalCodeFirst')
      : t('scan.scanOrTypeDeviceCodeFirst')
    scanResultSuccess.value = false
    focusScanCodeInput()
    return
  }

  scanResultMessage.value = ''
  scanResultSuccess.value = false
  saving.value = true
  try {
    const response = await store.processScan({
      scan_code: code,
      action: scanAction.value,
      zone_id: scanAction.value === 'move' ? scanZoneId.value : null,
      case_device_id: scanAction.value === 'move' ? scanCaseDeviceId.value : null,
      job_code: (scanAction.value === 'job_out' || scanAction.value === 'rental_job_out')
        ? activeJobCode.value
        : (scanAction.value === 'job_in'
          ? (globalCheckin.value ? null : scanJobCode.value)
          : (scanAction.value === 'rental_job_in' ? scanJobCode.value : null)),
      maintenance_type: scanAction.value === 'maintenance' ? scanMaintenanceType.value : null,
      interval_mode: scanAction.value === 'maintenance' ? scanIntervalMode.value : null,
      interval_value: scanAction.value === 'maintenance' ? scanIntervalValue.value : null,
    })
    if (scanAction.value === 'lookup' && response.success) {
      lastLookupCode.value = response.asset_tag || code
      lastLookupResult.value = response
    }
    if (scanAction.value === 'job_in') {
      lastIntakeResult.value = response.success && Number(response.device_id || 0) > 0 ? response : null
    }
    await jobsStore.fetchAll()
    await refreshCheckedOutForIntake()
    scanResultMessage.value = response.message || t('scan.scanProcessed')
    scanResultSuccess.value = !!response.success
    if (scanAction.value === 'move' && response.success) {
      trackRecentMove(response, code)
    }
    scanCode.value = ''
    if (scanAction.value === 'move') scanZoneCode.value = ''
  } catch (error) {
    scanResultMessage.value = error?.response?.data?.detail || t('scan.scanFailed')
    scanResultSuccess.value = false
  } finally {
    saving.value = false
    focusScanCodeInput()
  }
}

async function startCameraScan() {
  cameraError.value = ''
  cameraRunning.value = false
  if (!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)) {
    cameraError.value = t('scan.cameraApiNotSupported')
    return
  }
  if (typeof window.BarcodeDetector === 'undefined') {
    cameraError.value = t('scan.barcodeDetectionNotSupported')
    return
  }

  try {
    const detector = new window.BarcodeDetector({ formats: ['qr_code', 'code_128', 'ean_13', 'ean_8'] })
    cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
    const video = videoRef.value
    if (!video) return
    video.srcObject = cameraStream
    await video.play()
    cameraRunning.value = true

    cameraTimer = setInterval(async () => {
      if (!video || inputMode.value !== 'camera') return
      try {
        const barcodes = await detector.detect(video)
        if (barcodes?.length) {
          const raw = String(barcodes[0].rawValue || '').trim()
          if (raw) {
            scanCode.value = raw
            await runScanAction()
          }
        }
      } catch {
        // ignore transient detect errors
      }
    }, 450)
  } catch {
    cameraError.value = t('scan.unableStartCameraScanner')
  }
}

function stopCameraScan() {
  if (cameraTimer) {
    clearInterval(cameraTimer)
    cameraTimer = null
  }
  if (cameraStream) {
    const tracks = cameraStream.getTracks ? cameraStream.getTracks() : []
    for (const track of tracks) track.stop()
    cameraStream = null
  }
  cameraRunning.value = false
}

async function startNfcScan() {
  nfcError.value = ''
  nfcRunning.value = false
  if (typeof window.NDEFReader === 'undefined') {
    nfcError.value = t('scan.webNfcNotSupported')
    return
  }
  try {
    nfcReader = new window.NDEFReader()
    await nfcReader.scan()
    nfcRunning.value = true
    nfcReader.onreading = async (event) => {
      const serial = String(event.serialNumber || '').trim()
      if (serial) {
        scanCode.value = serial
        await runScanAction()
      }
    }
  } catch {
    nfcError.value = t('scan.unableStartNfcScanner')
  }
}

function stopNfcScan() {
  nfcReader = null
  nfcRunning.value = false
}

function onInputModeChanged() {
  if (inputMode.value === 'camera' && !supportsCamera.value) {
    inputMode.value = 'keyboard'
  }
  if (inputMode.value === 'nfc' && !supportsNfc.value) {
    inputMode.value = 'keyboard'
  }

  if (inputMode.value === 'keyboard') {
    stopCameraScan()
    stopNfcScan()
    return
  }
  if (inputMode.value === 'camera') {
    stopNfcScan()
    startCameraScan()
    return
  }
  stopCameraScan()
  startNfcScan()
}

onMounted(async () => {
  if (inputMode.value === 'camera' && !supportsCamera.value) {
    inputMode.value = 'keyboard'
  }
  if (inputMode.value === 'nfc' && !supportsNfc.value) {
    inputMode.value = 'keyboard'
  }
  await loadData()
  if (typeof window !== 'undefined') {
    window.addEventListener('keydown', onGlobalScanHotkey)
  }
  focusScanCodeInput()
})

watch([scanAction, globalCheckin, scanJobId, scanJobCode], async () => {
  await refreshCheckedOutForIntake()
})

watch(scanZoneId, (value) => {
  if (scanAction.value !== 'move') return
  if (!value) return
  scanCaseDeviceId.value = null
})

watch(scanCaseDeviceId, (value) => {
  if (scanAction.value !== 'move') return
  if (!value) return
  scanZoneId.value = null
})

watch([scanAction, scanJobId], () => {
  if (scanAction.value !== 'job_out' && scanAction.value !== 'rental_job_out') return
  if (activeJobCode.value) return
  if (!scanJobId.value) return

  const job = jobsStore.jobs.find(item => item.id === scanJobId.value)
  if (!job) return

  activeJobCode.value = job.job_code
  activeJobId.value = job.id
  scanJobCode.value = job.job_code
  scanResultMessage.value = t('scan.jobSelectedScanCodesNow', { jobCode: job.job_code, item: scanAction.value === 'rental_job_out' ? t('scan.rental').toLowerCase() : t('scan.device').toLowerCase() })
  scanResultSuccess.value = true
  scanCode.value = ''
  focusScanCodeInput()
})

onBeforeUnmount(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('keydown', onGlobalScanHotkey)
  }
  stopCameraScan()
  stopNfcScan()
})
</script>

<style scoped>
.scan-page {
  background: radial-gradient(1100px 420px at 8% -20%, rgba(63, 135, 63, 0.26), transparent),
    radial-gradient(900px 440px at 100% 0%, rgba(24, 34, 40, 0.28), transparent);
}

.scan-shell {
  max-width: 1100px;
  margin: 0 auto;
}

.scanner-card {
  background: linear-gradient(155deg, rgba(24, 34, 40, 0.97), rgba(17, 24, 29, 0.96));
  border: 1px solid rgba(63, 135, 63, 0.26);
  border-radius: 18px;
}

.scanner-icon-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 78px;
  height: 78px;
  border-radius: 18px;
  background: linear-gradient(135deg, #3f873f, #2f6b30);
}

.step-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.step-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.step-dot {
  width: 24px;
  height: 24px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.step-active {
  color: #7dd77d;
}

.step-active .step-dot {
  background: #3f873f;
  color: #fff;
}

.step-done {
  color: #22c55e;
}

.step-done .step-dot {
  background: #22c55e;
  color: #fff;
}

.step-pending {
  color: #9ca3af;
}

.step-pending .step-dot {
  background: #4b5563;
  color: #fff;
}

.step-line {
  width: 56px;
  height: 2px;
  background: rgba(63, 135, 63, 0.4);
}

.camera-wrap {
  position: relative;
  border: 1px solid rgba(63, 135, 63, 0.36);
  border-radius: 12px;
  overflow: hidden;
  background: #000;
}

.camera-video {
  width: 100%;
  height: 260px;
  object-fit: cover;
}

.camera-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.45);
}

.nfc-wrap {
  border: 1px dashed rgba(63, 135, 63, 0.42);
  border-radius: 12px;
  padding: 20px;
  background: rgba(63, 135, 63, 0.07);
}

.lookup-details-card {
  background: var(--scan-lookup-bg, rgba(15, 21, 26, 0.65));
}

.recent-moves-card {
  background: var(--scan-panel-bg, rgba(255, 255, 255, 0.96));
  color: var(--scan-panel-text, #111827);
}

.recent-moves-help {
  color: var(--scan-panel-caption, #4b5563);
}

.recent-moves-card :deep(.q-item__label) {
  color: var(--scan-panel-text, #111827);
}

.recent-moves-card :deep(.q-item__label--caption) {
  color: var(--scan-panel-caption, #4b5563);
}

.lookup-row {
  display: grid;
  grid-template-columns: minmax(160px, 240px) 1fr;
  gap: 8px;
  padding: 2px 0;
}

.lookup-label {
  color: var(--scan-lookup-label, #9ca3af);
  text-transform: capitalize;
}

.lookup-value {
  color: var(--scan-lookup-value, #e5e7eb);
  word-break: break-word;
}

:global(body.body--light) {
  --scan-lookup-bg: rgba(255, 255, 255, 0.95);
  --scan-lookup-label: #4b5563;
  --scan-lookup-value: #111827;
  --scan-panel-bg: rgba(255, 255, 255, 0.96);
  --scan-panel-text: #111827;
  --scan-panel-caption: #4b5563;
}

:global(body.body--dark) {
  --scan-lookup-bg: rgba(15, 21, 26, 0.65);
  --scan-lookup-label: #9ca3af;
  --scan-lookup-value: #e5e7eb;
  --scan-panel-bg: rgba(15, 21, 26, 0.78);
  --scan-panel-text: #e5e7eb;
  --scan-panel-caption: #c7d2df;
}

.lookup-maintenance-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 4px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.checked-out-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}

.checked-out-card {
  background: rgba(255, 255, 255, 0.96);
}
</style>
