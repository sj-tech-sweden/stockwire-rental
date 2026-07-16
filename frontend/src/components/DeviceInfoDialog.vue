<template>
  <q-dialog :model-value="modelValue" :maximized="effectiveIsPhone" @update:model-value="emit('update:modelValue', $event)">
    <q-card :style="effectiveIsPhone ? 'width: 100vw; max-width: 100vw; height: 100vh' : 'min-width: 820px; max-width: 96vw'" class="ec-card">
      <q-card-section>
        <div class="text-h6">{{ t('inventory.infoDialogs.deviceTitle', { assetTag: device?.asset_tag || '-' }) }}</div>
        <div class="text-caption text-grey-7">
          {{ device ? (store.products.find(item => item.id === device.product_id)?.name || t('inventory.productWithId', { id: device.product_id })) : '-' }}
        </div>
      </q-card-section>

      <q-card-section class="q-pt-none" :style="effectiveIsPhone ? 'max-height: calc(100vh - 140px); overflow: auto;' : ''">
        <div class="row q-col-gutter-sm q-mb-md">
          <div class="col-12 col-md-4"><q-badge color="grey-8" text-color="white" :label="t('inventory.status') + ': ' + (device?.status || '-')" /></div>
          <div class="col-12 col-md-4"><q-badge color="grey-7" text-color="white" :label="t('inventory.condition') + ': ' + (device?.condition || '-')" /></div>
          <div class="col-12 col-md-4">
            <q-badge
              :color="device?.current_job_code ? 'info' : 'grey'"
              text-color="white"
              :label="device?.current_job_code ? t('inventory.infoDialogs.currentJob') + ': ' + device.current_job_code : t('inventory.infoDialogs.currentJob') + ': ' + t('inventory.infoDialogs.none')"
            />
            <q-btn
              v-if="device?.current_job_id"
              flat
              dense
              :round="effectiveIsPhone"
              color="primary"
              icon="edit"
              class="q-ml-xs"
              :label="effectiveIsPhone ? void 0 : t('app.actions.edit')"
              :aria-label="effectiveIsPhone ? t('app.actions.editJob') : void 0"
              @click="openJobFromLink(device.current_job_id)"
            />
          </div>
          <div class="col-12">
            <q-btn flat dense color="positive" icon="build" :label="t('inventory.infoDialogs.createMaintenanceTask')" @click="emit('create-maintenance', device?.id)" />
            <q-btn flat dense color="positive" icon="event_repeat" :label="t('inventory.infoDialogs.createMaintenanceSchedule')" class="q-ml-xs" @click="emit('create-maintenance', device?.id)" />
            <q-btn
              color="warning"
              icon="warning"
              :label="t('inventory.infoDialogs.reportDefect')"
              @click="emit('report-defect', device?.id)"
            />
          </div>
          <div class="col-12 col-md-6 text-caption">
            {{ t('inventory.infoDialogs.serialNumber') }}: {{ device?.serial_number || '-' }}
          </div>
          <div class="col-12 col-md-6 text-caption">
            {{ t('inventory.infoDialogs.barcode') }}: {{ device?.barcode || '-' }}
          </div>
          <div class="col-12 col-md-6 text-caption">
            {{ t('inventory.infoDialogs.qrCode') }}: {{ device?.qr_code || '-' }}
          </div>
          <div class="col-12 col-md-6 text-caption">
            {{ t('inventory.infoDialogs.rfid') }}: {{ device?.rfid || '-' }}
          </div>
          <div class="col-12 col-md-6 text-caption">
            {{ t('inventory.infoDialogs.usageHours') }}: {{ device?.usage_hours || '-' }}
          </div>
          <div class="col-12 col-md-6 text-caption">
            {{ t('inventory.infoDialogs.location') }}: {{ deviceLocationPath || device?.location || '-' }}
            <q-btn v-if="device?.location_zone_id" flat dense round color="primary" icon="place" size="sm" class="q-ml-xs" @click="locateDeviceMapOpen = true">
              <q-tooltip>{{ t('inventory.deviceDialog.locateOnMap') }}</q-tooltip>
            </q-btn>
          </div>
          <div class="col-12 col-md-6 text-caption">
            {{ t('inventory.infoDialogs.purchase') }}:
            {{ device?.purchase_price == null ? '-' : formatMoney(device.purchase_price) }}
            <template v-if="device?.purchased_from">
              {{ t('inventory.infoDialogs.from') }} {{ device.purchased_from }}
            </template>
            <template v-if="device?.purchase_date">
              {{ t('inventory.infoDialogs.at') }} {{ device.purchase_date }}
            </template>
          </div>
          <div class="col-12 col-md-6 text-caption">
            {{ t('inventory.infoDialogs.warrantyUntil') }}: {{ device?.warranty_until || '-' }}
          </div>
          <div class="col-12 col-md-6 text-caption">
            {{ t('inventory.infoDialogs.retirement') }}: {{ device?.retirement_date || '-' }} · {{ t('inventory.infoDialogs.reason') }}: {{ device?.retirement_reason || '-' }}
          </div>
          <div class="col-12 col-md-6 text-caption">
            {{ t('inventory.infoDialogs.sold') }}: {{ device?.sold_price == null ? '-' : formatMoney(device?.sold_price) }}
            <template v-if="device?.sold_date">
              {{ t('inventory.infoDialogs.at') }} {{ device.sold_date }}
            </template>
          </div>
          <div class="col-12 col-md-6 text-caption">
            {{ t('inventory.infoDialogs.financeUpTo') }}: {{ device?.finance_upto || '-' }}
          </div>
          <div class="col-12 col-md-6 text-caption">
            {{ t('inventory.infoDialogs.financeCompany') }}: {{ device?.finance_company || '-' }} · {{ t('inventory.infoDialogs.ref') }}: {{ device?.finance_ref || '-' }}
          </div>
          <div class="col-12 col-md-6 text-caption">
            {{ t('inventory.infoDialogs.prePrep') }}: {{ device?.pre_prep || '-' }}
          </div>
          <div class="col-12 col-md-6 text-caption">
            {{ t('inventory.infoDialogs.notes') }}: {{ device?.notes || '-' }}
          </div>
        </div>

        <div class="text-subtitle2 q-mb-sm">{{ t('inventory.infoDialogs.parentProduct') }}</div>
        <q-list bordered separator class="rounded-borders q-mb-md">
          <q-item>
            <q-item-section>
              <q-item-label>{{ deviceInfoProduct?.sku || '-' }} · {{ deviceInfoProduct?.name || '-' }}</q-item-label>
              <q-item-label caption>
                {{ t('inventory.type') }}: {{ deviceInfoProduct?.product_type || '-' }} · {{ t('inventory.category') }}: {{ deviceInfoProduct?.category || t('inventory.uncategorized') }}
              </q-item-label>
              <q-item-label caption>
                {{ t('inventory.infoDialogs.brand') }}: {{ deviceInfoProduct?.brand || '-' }} · {{ t('inventory.infoDialogs.manufacturer') }}: {{ deviceInfoProduct?.manufacturer || '-' }}
              </q-item-label>
              <q-item-label caption>
                {{ t('inventory.infoDialogs.dailyRate') }}: {{ formatMoney(deviceInfoProduct?.daily_rate) }} · {{ t('inventory.infoDialogs.supplier') }}: {{ deviceInfoProduct?.supplier_name || '-' }}
              </q-item-label>
              <q-item-label caption>
                {{ t('inventory.infoDialogs.replacementCost') }}: {{ formatMoney(deviceInfoProduct?.replace_cost) }} · {{ t('inventory.infoDialogs.supplier') }}: {{ deviceInfoProduct?.supplier_name || '-' }}
              </q-item-label>
              <q-item-label caption v-if="deviceInfoProduct?.is_rental_product">
                {{ t('inventory.infoDialogs.rentalSource') }}: {{ deviceInfoProduct?.external_source || '-' }} · {{ t('inventory.infoDialogs.externalRef') }}: {{ deviceInfoProduct?.external_reference || '-' }}
              </q-item-label>
              <q-item-label caption v-if="deviceInfoProduct?.is_rental_product">
                {{ t('inventory.infoDialogs.eventoryAvailable') }}: {{ Number(deviceInfoProduct?.eventory_available_qty || 0) }} · {{ t('inventory.infoDialogs.isRental') }}: {{ deviceInfoProduct?.is_rental_product ? t('inventory.infoDialogs.yes') : t('inventory.infoDialogs.no') }}
              </q-item-label>
              <q-item-label caption>
                {{ t('inventory.infoDialogs.weight') }}: {{ deviceInfoProduct?.weight_kg ?? '-' }} kg · {{ t('inventory.infoDialogs.size') }}: {{ deviceInfoProduct?.height_cm ?? '-' }}x{{ deviceInfoProduct?.width_cm ?? '-' }}x{{ deviceInfoProduct?.depth_cm ?? '-' }} cm
              </q-item-label>
              <q-item-label caption>
                {{ t('inventory.infoDialogs.power') }}: {{ deviceInfoProduct?.power_consumption_watts ?? '-' }} W · {{ t('inventory.infoDialogs.maintenanceInterval') }}: {{ deviceInfoProduct?.maintenance_interval_days ?? '-' }} days
              </q-item-label>
              <q-item-label caption>
                {{ t('inventory.infoDialogs.devicesTotal') }}: {{ Number(deviceInfoProduct?.total_devices || 0) }} · {{ t('inventory.infoDialogs.inStore') }}: {{ Number(deviceInfoProduct?.in_store_devices || 0) }} · {{ t('inventory.infoDialogs.onSite') }}: {{ Number(deviceInfoProduct?.on_site_devices || 0) }} · {{ t('inventory.infoDialogs.damaged') }}: {{ Number(deviceInfoProduct?.damaged_devices || 0) }}
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-btn
                flat
                dense
                color="primary"
                icon="edit"
                :label="t('inventory.infoDialogs.editProduct')"
                @click="emit('edit-product', deviceInfoProduct?.id)"
              />
            </q-item-section>
          </q-item>
        </q-list>

        <div v-if="deviceInfoProduct?.accessories?.length" class="text-subtitle2 q-mb-sm">{{ t('inventory.infoDialogs.productAccessories') }}</div>
        <q-list v-if="deviceInfoProduct?.accessories?.length" bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="row in deviceInfoProduct.accessories" :key="`acc-${row.accessory_product_id}`">
            <q-item-section>
              <q-item-label>{{ productNameById(row.accessory_product_id) }}</q-item-label>
              <q-item-label caption>{{ row.required ? t('inventory.infoDialogs.required') : t('inventory.infoDialogs.optional') }} · {{ t('inventory.infoDialogs.qty') }} {{ row.quantity }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <div v-if="deviceInfoProduct?.components?.length" class="text-subtitle2 q-mb-sm">{{ t('inventory.infoDialogs.productComponents') }}</div>
        <q-list v-if="deviceInfoProduct?.components?.length" bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="row in deviceInfoProduct.components" :key="`cmp-${row.component_product_id}`">
            <q-item-section>
              <q-item-label>{{ productNameById(row.component_product_id) }}</q-item-label>
              <q-item-label caption>{{ t('inventory.infoDialogs.qty') }} {{ row.quantity }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <div class="text-subtitle2 q-mb-sm">{{ t('inventory.infoDialogs.devicesAtSameLocation') }}</div>
        <q-list bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="row in deviceInfoLocationDevices" :key="row.id">
            <q-item-section>
              <q-item-label>{{ row.asset_tag }} · {{ productNameById(row.product_id) }}</q-item-label>
              <q-item-label caption>
                {{ t('inventory.infoDialogs.deviceStatusCondition', { status: row.status, condition: row.condition || t('inventory.infoDialogs.notAvailable') }) }}
                <span v-if="row.current_job_code"> · Job {{ row.current_job_code }}</span>
              </q-item-label>
            </q-item-section>
            <q-item-section side top>
              <div class="row no-wrap items-center q-gutter-xs">
                <q-btn
                  flat
                  dense
                  :round="effectiveIsPhone"
                  :color="productActionColor"
                  class="inventory-action-contrast"
                  icon="inventory_2"
              :label="effectiveIsPhone ? void 0 : t('inventory.products')"
              :aria-label="effectiveIsPhone ? t('inventory.openProduct') : void 0"
                  @click="emit('edit-product', row.product_id)"
                />
                <q-btn
                  flat
                  dense
                  :round="effectiveIsPhone"
                  :color="infoActionColor"
                  icon="info"
              :label="effectiveIsPhone ? void 0 : t('inventory.infoDialogs.deviceInfo')"
              :aria-label="effectiveIsPhone ? t('inventory.infoDialogs.openDeviceInfo') : void 0"
                  @click="emit('view-device', row.id)"
                />
                <q-btn
                  flat
                  dense
                  :round="effectiveIsPhone"
                  color="primary"
                  icon="edit"
              :label="effectiveIsPhone ? void 0 : t('app.actions.edit')"
              :aria-label="effectiveIsPhone ? t('inventory.deviceDialog.edit') : void 0"
                  @click="emit('edit-device', row.id)"
                />
              </div>
            </q-item-section>
          </q-item>
          <q-item v-if="!deviceInfoLocationDevices.length">
            <q-item-section>
              <q-item-label caption>{{ t('inventory.infoDialogs.noDevicesAtLocation') }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <div v-if="deviceInfoIsCase" class="text-subtitle2 q-mb-sm">{{ t('inventory.infoDialogs.devicesInsideThisCase') }}</div>
        <q-list v-if="deviceInfoIsCase" bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="row in deviceInfoContainedDevices" :key="row.id">
            <q-item-section>
              <q-item-label>{{ row.asset_tag }} · {{ productNameById(row.product_id) }}</q-item-label>
              <q-item-label caption>
                {{ t('inventory.infoDialogs.deviceStatusCondition', { status: row.status, condition: row.condition || t('inventory.infoDialogs.notAvailable') }) }}
                <span v-if="row.current_job_code"> · {{ t('inventory.infoDialogs.job') }} {{ row.current_job_code }}</span>
              </q-item-label>
            </q-item-section>
            <q-item-section side top>
              <div class="row no-wrap items-center q-gutter-xs">
                <q-btn
                  flat
                  dense
                  :round="effectiveIsPhone"
                  :color="productActionColor"
                  class="inventory-action-contrast"
                  icon="inventory_2"
              :label="effectiveIsPhone ? void 0 : t('inventory.products')"
              :aria-label="effectiveIsPhone ? t('inventory.openProduct') : void 0"
                  @click="emit('edit-product', row.product_id)"
                />
                <q-btn
                  flat
                  dense
                  :round="effectiveIsPhone"
                  :color="infoActionColor"
                  icon="info"
              :label="effectiveIsPhone ? void 0 : t('inventory.infoDialogs.deviceInfo')"
              :aria-label="effectiveIsPhone ? t('inventory.infoDialogs.openDeviceInfo') : void 0"
                  @click="emit('view-device', row.id)"
                />
                <q-btn
                  flat
                  dense
                  :round="effectiveIsPhone"
                  color="primary"
                  icon="edit"
              :label="effectiveIsPhone ? void 0 : t('app.actions.edit')"
              :aria-label="effectiveIsPhone ? t('inventory.deviceDialog.edit') : void 0"
                  @click="emit('edit-device', row.id)"
                />
              </div>
            </q-item-section>
          </q-item>
          <q-item v-if="!deviceInfoContainedDevices.length">
            <q-item-section>
              <q-item-label caption>{{ t('inventory.infoDialogs.noDevicesInsideCase') }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <div v-if="deviceInfoComponentDevices.length" class="text-subtitle2 q-mb-sm">{{ t('inventory.infoDialogs.componentDevices') }}</div>
        <q-list v-if="deviceInfoComponentDevices.length" bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="row in deviceInfoComponentDevices" :key="row.id">
            <q-item-section>
              <q-item-label>{{ row.asset_tag }} · {{ productNameById(row.product_id) }}</q-item-label>
              <q-item-label caption>
                {{ t('inventory.infoDialogs.deviceStatusCondition', { status: row.status, condition: row.condition || t('inventory.infoDialogs.notAvailable') }) }}
                <span v-if="row.current_job_code"> · {{ t('inventory.infoDialogs.job') }} {{ row.current_job_code }}</span>
              </q-item-label>
            </q-item-section>
            <q-item-section side top>
              <div class="row no-wrap items-center q-gutter-xs">
                <q-btn flat dense :round="effectiveIsPhone" :color="productActionColor" class="inventory-action-contrast" icon="inventory_2" :label="effectiveIsPhone ? void 0 : t('inventory.infoDialogs.product')" :aria-label="effectiveIsPhone ? t('inventory.infoDialogs.openProductForEdit') : void 0" @click="emit('edit-product', row.product_id)" />
                <q-btn flat dense :round="effectiveIsPhone" :color="infoActionColor" icon="info" :label="effectiveIsPhone ? void 0 : t('inventory.infoDialogs.deviceInfo')" :aria-label="effectiveIsPhone ? t('inventory.infoDialogs.openDeviceInfo') : void 0" @click="emit('view-device', row.id)" />
                <q-btn flat dense :round="effectiveIsPhone" color="primary" icon="edit" :label="effectiveIsPhone ? void 0 : t('app.actions.edit')" :aria-label="effectiveIsPhone ? t('inventory.deviceDialog.edit') : void 0" @click="emit('edit-device', row.id)" />
              </div>
            </q-item-section>
          </q-item>
        </q-list>

        <div class="text-subtitle2 q-mb-sm">{{ t('inventory.infoDialogs.maintenanceOverview') }}</div>
        <q-list bordered separator class="rounded-borders q-mb-md">
          <q-item v-if="deviceInfoNextMaintenance">
            <q-item-section>
              <q-item-label>{{ t('inventory.infoDialogs.nextScheduledTask') }} · {{ deviceInfoNextMaintenance.maintenance_type || '-' }}</q-item-label>
              <q-item-label caption>
                {{ t('inventory.infoDialogs.status') }}: {{ deviceInfoNextMaintenance.status || '-' }} · {{ maintenanceTimingLabel(deviceInfoNextMaintenance) }}
              </q-item-label>
              <q-item-label caption v-if="deviceInfoNextMaintenance.notes">{{ deviceInfoNextMaintenance.notes }}</q-item-label>
            </q-item-section>
            <q-item-section side top>
              <div class="row no-wrap items-center q-gutter-xs">
                <q-btn
                  v-if="deviceInfoNextMaintenance.status !== 'completed'"
                  flat
                  dense
                  color="positive"
                  icon="task_alt"
                  @click="emit('complete-maintenance', deviceInfoNextMaintenance)"
                />
                <q-btn flat dense color="primary" icon="edit" @click="emit('edit-maintenance', deviceInfoNextMaintenance)" />
              </div>
            </q-item-section>
          </q-item>
          <q-item v-else>
            <q-item-section>
              <q-item-label caption>{{ t('inventory.infoDialogs.noUpcomingMaintenance') }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <div class="text-subtitle2 q-mb-sm">{{ t('inventory.infoDialogs.previousMaintenanceTasks') }}</div>
        <q-list bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="row in deviceInfoPreviousMaintenance" :key="`maint-prev-${row.id}`">
            <q-item-section>
              <q-item-label>{{ row.maintenance_type || '-' }}</q-item-label>
              <q-item-label caption>
                {{ t('inventory.infoDialogs.status') }}: {{ row.status || '-' }} · {{ maintenanceTimingLabel(row) }}
              </q-item-label>
              <q-item-label caption v-if="row.notes">{{ row.notes }}</q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-badge :color="maintenanceStatusColor(row.status)" :label="row.status || '-'" />
            </q-item-section>
          </q-item>
          <q-item v-if="!deviceInfoPreviousMaintenance.length">
            <q-item-section>
              <q-item-label caption>{{ t('inventory.infoDialogs.noPreviousMaintenance') }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <div class="text-subtitle2 q-mb-sm">{{ t('inventory.infoDialogs.jobsHistory') }}</div>
        <q-list bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="row in deviceJobHistory" :key="`${row.job_id}-${row.last_event_at}`">
            <q-item-section>
              <q-item-label>{{ row.job_code || t('inventory.infoDialogs.jobWithId', { jobId: row.job_id }) }}</q-item-label>
              <q-item-label caption>
                {{ t('inventory.infoDialogs.firstOut') }}: {{ formatDateTime(row.first_out_at) || '-' }} · {{ t('inventory.infoDialogs.lastIn') }}: {{ formatDateTime(row.last_in_at) || '-' }} · {{ t('inventory.infoDialogs.lastEvent') }}: {{ formatDateTime(row.last_event_at) || '-' }}
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-btn
                flat
                dense
                :round="effectiveIsPhone"
                color="primary"
                icon="edit"
                :label="effectiveIsPhone ? void 0 : t('app.actions.edit')"
                :aria-label="effectiveIsPhone ? t('app.actions.editJob') : void 0"
                @click="openJobFromLink(row.job_id)"
              />
            </q-item-section>
          </q-item>
          <q-item v-if="!deviceJobHistory.length">
            <q-item-section>
              <q-item-label caption>{{ t('inventory.infoDialogs.noJobHistory') }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <div class="text-subtitle2 q-mb-sm">{{ t('inventory.infoDialogs.auditTimeline') }}</div>
        <q-list bordered separator class="rounded-borders">
          <q-item v-for="row in deviceInfoAudits" :key="row.id">
            <q-item-section>
              <q-item-label>{{ row.action }} · {{ row.message }}</q-item-label>
              <q-item-label caption>
                {{ formatDateTime(row.created_at) || '-' }}
                <span v-if="row.job_code"> · {{ t('inventory.infoDialogs.job') }} {{ row.job_code }}</span>
                <span v-if="row.scan_code"> · {{ t('inventory.infoDialogs.scan') }} {{ row.scan_code }}</span>
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-badge :color="row.success ? 'positive' : 'negative'" :label="row.success ? t('inventory.infoDialogs.ok') : t('inventory.infoDialogs.failed')" />
            </q-item-section>
          </q-item>
          <q-item v-if="!deviceInfoAudits.length">
            <q-item-section>
              <q-item-label caption>{{ t('inventory.infoDialogs.noAuditEntries') }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <div class="text-subtitle2 q-mb-sm q-mt-lg">{{ t('defects.title') }}</div>
        <div v-if="!deviceInfoDefects.length" class="text-caption text-grey-6 q-mb-sm">{{ t('defects.noDefectsForDevice') }}</div>
        <q-list v-else bordered separator class="rounded-borders q-mb-md">
          <q-item v-for="defect in deviceInfoDefects" :key="defect.id">
            <q-item-section>
              <q-input
                :model-value="defect.title"
                dense
                outlined
                class="text-weight-medium"
                @update:model-value="(v) => updateDefectField(defect, 'title', v)"
              />
              <q-input
                :model-value="defect.description"
                dense
                outlined
                type="textarea"
                autogrow
                :placeholder="t('defects.noDescription')"
                class="q-mt-xs"
                @update:model-value="(v) => updateDefectField(defect, 'description', v || null)"
              />
              <div class="row q-gutter-sm q-mt-xs items-center">
                <q-select
                  :model-value="defect.status"
                  :options="defectStatusOptions"
                  dense
                  outlined
                  emit-value
                  map-options
                  size="sm"
                  style="min-width: 130px"
                  @update:model-value="(v) => updateDefectStatus(defect, v)"
                />
                <q-select
                  :model-value="defect.severity"
                  :options="defectSeverityOptions"
                  dense
                  outlined
                  emit-value
                  map-options
                  size="sm"
                  style="min-width: 110px"
                  @update:model-value="(v) => updateDefectSeverity(defect, v)"
                />
                <q-btn dense flat icon="delete" color="negative" size="sm" @click="deleteDefect(defect)" />
              </div>
              <div v-if="defect.comments?.length" class="q-mt-sm">
                <div v-for="comment in defect.comments" :key="comment.id" class="text-caption q-py-xs">
                  <div class="comment-bubble">
                    {{ comment.comment }}
                    <div v-if="comment.created_at" class="text-grey-5 text-right" style="font-size: 0.7rem;">{{ comment.created_at }}</div>
                  </div>
                </div>
              </div>
              <div class="q-mt-xs">
                <q-input
                  v-model="defect.newComment"
                  dense
                  outlined
                  type="textarea"
                  autogrow
                  :placeholder="t('defects.addComment')"
                  class="col-grow"
                />
                <q-btn
                  dense
                  flat
                  icon="send"
                  color="primary"
                  :loading="defect.savingComment"
                  :disable="!defect.newComment?.trim()"
                  @click="addDefectComment(defect)"
                  class="q-mt-xs"
                />
              </div>
            </q-item-section>
          </q-item>
        </q-list>

        <EntityAttachmentsPanel
          entity-type="device"
          :entity-id="device?.id || null"
          :title="t('inventory.infoDialogs.deviceDocuments')"
          default-category="device-document"
          :read-only="true"
        />
      </q-card-section>

      <q-card-actions :align="effectiveIsPhone ? 'stretch' : 'right'" :class="effectiveIsPhone ? 'q-pa-md bg-grey-2' : ''">
        <q-space />
        <q-btn flat :class="effectiveIsPhone ? 'full-width' : ''" :label="t('app.actions.close')" @click="emit('update:modelValue', false)" />
      </q-card-actions>
    </q-card>
  </q-dialog>

  <LocateDeviceMapDialog
    v-model="locateDeviceMapOpen"
    :device="device"
  />
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useInventoryStore } from '../stores/inventory'
import { useJobsStore } from '../stores/jobs'
import { useSettingsStore } from '../stores/settings'
import { normalizeCurrencyCode } from '../constants/currencies'
import { api } from '../boot/axios'
import EntityAttachmentsPanel from './EntityAttachmentsPanel.vue'
import LocateDeviceMapDialog from './LocateDeviceMapDialog.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  device: { type: Object, default: null },
  isPhone: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'edit-device', 'edit-product', 'view-device', 'open-job', 'report-defect', 'create-maintenance', 'edit-maintenance', 'complete-maintenance'])

const $q = useQuasar()
const { t } = useI18n()
const store = useInventoryStore()
const jobsStore = useJobsStore()
const settingsStore = useSettingsStore()

const effectiveIsPhone = computed(() => props.isPhone || $q.screen.lt.md)

const deviceInfoAudits = ref([])
const deviceInfoDefects = ref([])
const defectFieldTimers = {}

const productActionColor = computed(() => ($q.dark.isActive ? 'green-4' : 'secondary'))
const infoActionColor = computed(() => ($q.dark.isActive ? 'teal-4' : 'secondary'))

const locateDeviceMapOpen = ref(false)

const deviceLocationPath = computed(() => {
  if (!props.device?.location_zone_id) return ''
  const zone = store.zones.find(z => z.id === props.device.location_zone_id)
  if (!zone) return ''
  const parts = []
  let current = zone
  while (current) {
    parts.unshift(current.name || '')
    current = store.zones.find(z => z.id === current.parent_id)
  }
  return parts.join(' / ')
})

const defectStatusOptions = [
  { label: t('inventory.defectStatusOpen'), value: 'open' },
  { label: t('inventory.defectStatusInProgress'), value: 'in_progress' },
  { label: t('inventory.defectStatusResolved'), value: 'resolved' },
  { label: t('inventory.defectStatusClosed'), value: 'closed' },
]

const defectSeverityOptions = [
  { label: t('inventory.defectSeverityLow'), value: 'low' },
  { label: t('inventory.defectSeverityMedium'), value: 'medium' },
  { label: t('inventory.defectSeverityHigh'), value: 'high' },
  { label: t('inventory.defectSeverityCritical'), value: 'critical' },
]

const deviceInfoProduct = computed(() => {
  if (!props.device) return null
  return store.products.find(item => item.id === props.device.product_id) || null
})
const deviceInfoIsCase = computed(() => deviceInfoProduct.value?.product_type === 'case')

const deviceInfoLocationDevices = computed(() => {
  if (!props.device?.location_zone_id) return []
  const sourceId = props.device.id
  return store.devices.filter(item => item.location_zone_id === props.device.location_zone_id && item.id !== sourceId)
})

const deviceInfoContainedDevices = computed(() => {
  if (!props.device?.id) return []
  const caseId = props.device.id
  return store.devices.filter(item => item.case_device_id === caseId)
})

const deviceInfoComponentDevices = computed(() => {
  if (!props.device?.id) return []
  const parentId = props.device.id
  return store.devices.filter(item => item.parent_component_device_id === parentId)
})

const deviceInfoMaintenance = computed(() => {
  if (!props.device?.id) return []
  const targetId = Number(props.device.id)
  return (store.maintenances || [])
    .filter(item => Number(item.device_id) === targetId)
    .slice()
    .sort((a, b) => maintenanceSortTimestamp(a) - maintenanceSortTimestamp(b))
})

const deviceInfoNextMaintenance = computed(() => {
  const currentUsageHours = Number(props.device?.usage_hours)
  const hasUsageHours = Number.isFinite(currentUsageHours)
  const rows = deviceInfoMaintenance.value
    .filter(item => ['scheduled', 'in_progress'].includes(String(item.status || '').toLowerCase()))
    .slice()
    .sort((a, b) => compareUpcomingMaintenance(a, b, hasUsageHours ? currentUsageHours : null))
  return rows.length ? rows[0] : null
})

const deviceInfoPreviousMaintenance = computed(() => {
  const nextId = deviceInfoNextMaintenance.value?.id
  return deviceInfoMaintenance.value
    .filter(item => item.id !== nextId)
    .slice()
    .sort((a, b) => maintenanceSortTimestamp(b) - maintenanceSortTimestamp(a))
    .slice(0, 12)
})

const deviceJobHistory = computed(() => {
  const byJob = new Map()
  for (const row of deviceInfoAudits.value || []) {
    if (!row?.job_id) continue
    const existing = byJob.get(row.job_id) || {
      job_id: row.job_id,
      job_code: row.job_code || null,
      first_out_at: null,
      last_in_at: null,
      last_event_at: row.created_at,
    }

    if (!existing.job_code && row.job_code) existing.job_code = row.job_code
    if (!existing.last_event_at || String(row.created_at) > String(existing.last_event_at)) {
      existing.last_event_at = row.created_at
    }
    if (row.action === 'job_out') {
      if (!existing.first_out_at || String(row.created_at) < String(existing.first_out_at)) {
        existing.first_out_at = row.created_at
      }
    }
    if (row.action === 'job_in') {
      if (!existing.last_in_at || String(row.created_at) > String(existing.last_in_at)) {
        existing.last_in_at = row.created_at
      }
    }
    byJob.set(row.job_id, existing)
  }
  return [...byJob.values()].sort((a, b) => String(b.last_event_at || '').localeCompare(String(a.last_event_at || '')))
})

function formatDateTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString()
}

function formatMoney(value) {
  const amount = Number(value || 0)
  if (!Number.isFinite(amount)) return '0.00'
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

function productNameById(productId) {
  const item = store.products.find(row => row.id === productId)
  if (!item) return t('inventory.infoDialogs.productWithIdName', { productId })
  return `${item.sku} - ${item.name}`
}

function maintenanceSortTimestamp(row) {
  if (!row) return 0
  const scheduledTs = row.scheduled_date ? new Date(`${row.scheduled_date}T00:00:00`).getTime() : Number.NaN
  const completedTs = row.completed_date ? new Date(`${row.completed_date}T00:00:00`).getTime() : Number.NaN
  const createdTs = row.created_at ? new Date(row.created_at).getTime() : 0
  if (Number.isFinite(scheduledTs)) return scheduledTs
  if (Number.isFinite(completedTs)) return completedTs
  return Number.isFinite(createdTs) ? createdTs : 0
}

function maintenanceUpcomingPriority(row, currentUsageHours = null) {
  const status = String(row?.status || '').toLowerCase()
  const statusRank = status === 'in_progress' ? 0 : 1

  const dueUsageHours = Number(row?.due_usage_hours)
  if (row?.interval_mode === 'runtime' && Number.isFinite(dueUsageHours) && Number.isFinite(currentUsageHours)) {
    const remainingHours = dueUsageHours - currentUsageHours
    const dueRank = remainingHours <= 0 ? 0 : 1
    return [statusRank, 0, dueRank, remainingHours]
  }

  const scheduledTs = row?.scheduled_date ? new Date(`${row.scheduled_date}T00:00:00`).getTime() : Number.NaN
  if (Number.isFinite(scheduledTs)) {
    const todayTs = new Date(new Date().toDateString()).getTime()
    const dayDelta = Math.floor((scheduledTs - todayTs) / 86400000)
    const dueRank = dayDelta <= 0 ? 0 : 1
    return [statusRank, 1, dueRank, dayDelta]
  }

  return [statusRank, 2, 1, maintenanceSortTimestamp(row)]
}

function compareUpcomingMaintenance(a, b, currentUsageHours = null) {
  const pa = maintenanceUpcomingPriority(a, currentUsageHours)
  const pb = maintenanceUpcomingPriority(b, currentUsageHours)
  for (let i = 0; i < pa.length; i += 1) {
    if (pa[i] === pb[i]) continue
    return pa[i] < pb[i] ? -1 : 1
  }
  return maintenanceSortTimestamp(a) - maintenanceSortTimestamp(b)
}

function maintenanceTimingLabel(row) {
  if (!row) return t('inventory.noDateSet')
  if (row.interval_mode === 'runtime' && row.due_usage_hours != null) {
    const dueUsageHours = Number(row.due_usage_hours)
    const currentUsageHours = Number(props.device?.usage_hours)
    if (Number.isFinite(dueUsageHours) && Number.isFinite(currentUsageHours)) {
      const remaining = Number((dueUsageHours - currentUsageHours).toFixed(1))
      if (remaining <= 0) return t('inventory.infoDialogs.runtimeDueNow', { remaining: Math.abs(remaining) })
      return t('inventory.infoDialogs.runtimeDueIn', { remaining, dueUsageHours })
    }
    return t('inventory.infoDialogs.dueAt', { hours: row.due_usage_hours })
  }
  if (row.scheduled_date) return t('inventory.infoDialogs.scheduled', { date: row.scheduled_date })
  if (row.completed_date) return t('inventory.infoDialogs.completed', { date: row.completed_date })
  return t('inventory.noDateSet')
}

function maintenanceStatusColor(status) {
  if (status === 'completed') return 'positive'
  if (status === 'in_progress') return 'warning'
  if (status === 'canceled') return 'grey'
  return 'info'
}

function openJobFromLink(jobId) {
  emit('open-job', jobId)
}

async function loadDeviceData(device) {
  if (!device?.id) return
  deviceInfoAudits.value = []
  deviceInfoDefects.value = []
  try {
    deviceInfoAudits.value = await store.fetchDeviceAuditLogs(device.id, 300)
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('inventory.failedLoadDeviceHistory') })
  }
  try {
    const { data: defects } = await api.get('/api/v1/inventory/defect-reports', {
      params: { device_id: device.id }
    })
    deviceInfoDefects.value = defects || []
    for (const defect of deviceInfoDefects.value) {
      try {
        const { data: comments } = await api.get(`/api/v1/inventory/defect-reports/${defect.id}/comments`)
        defect.comments = comments || []
      } catch {
        defect.comments = []
      }
      defect.newComment = ''
      defect.savingComment = false
    }
  } catch {
    deviceInfoDefects.value = []
  }
}

async function refreshDeviceInfoTarget() {
  if (!props.device?.id) return
  try {
    const { data } = await api.get(`/api/v1/inventory/devices/${props.device.id}`)
    Object.assign(props.device, data)
  } catch {
    // ignore
  }
  await loadDeviceData(props.device)
}

async function updateDefectStatus(defect, newStatus) {
  try {
    const { data } = await api.put(`/api/v1/inventory/defect-reports/${defect.id}`, { status: newStatus })
    Object.assign(defect, data)
    await refreshDeviceInfoTarget()
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('inventory.failedUpdateStatus') })
  }
}

async function updateDefectSeverity(defect, newSeverity) {
  try {
    const { data } = await api.put(`/api/v1/inventory/defect-reports/${defect.id}`, { severity: newSeverity })
    Object.assign(defect, data)
    await refreshDeviceInfoTarget()
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('inventory.failedUpdateSeverity') })
  }
}

function deleteDefect(defect) {
  $q.dialog({
    title: t('inventory.deleteDefect'),
    message: t('inventory.deleteDefectConfirm'),
    cancel: true,
    ok: { label: t('inventory.delete'), color: 'negative' },
  }).onOk(async () => {
    try {
      await api.delete(`/api/v1/inventory/defect-reports/${defect.id}`)
      deviceInfoDefects.value = deviceInfoDefects.value.filter(d => d.id !== defect.id)
      await refreshDeviceInfoTarget()
    } catch (error) {
      $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('inventory.failedDeleteDefect') })
    }
  })
}

function updateDefectField(defect, field, value) {
  defect[field] = value
  if (defectFieldTimers[`${defect.id}-${field}`]) {
    clearTimeout(defectFieldTimers[`${defect.id}-${field}`])
  }
  defectFieldTimers[`${defect.id}-${field}`] = setTimeout(async () => {
    try {
      const { data } = await api.put(`/api/v1/inventory/defect-reports/${defect.id}`, { [field]: value })
      Object.assign(defect, data)
    } catch (error) {
      $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('inventory.failedUpdate') })
    }
  }, 600)
}

async function addDefectComment(defect) {
  const text = (defect.newComment || '').trim()
  if (!text) return
  defect.savingComment = true
  try {
    const { data } = await api.post(`/api/v1/inventory/defect-reports/${defect.id}/comments`, { comment: text })
    defect.comments.push(data)
    defect.newComment = ''
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('inventory.failedAddComment') })
  } finally {
    defect.savingComment = false
  }
}

watch(() => props.device, (device) => {
  if (props.modelValue && device) {
    void loadDeviceData(device)
  }
})

watch(() => props.modelValue, (open) => {
  if (open && props.device) {
    void loadDeviceData(props.device)
  }
})
</script>

<style lang="scss" scoped>
.comment-bubble {
  background: #f5f5f5;
  border-radius: 6px;
  padding: 6px 10px;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.85rem;
  line-height: 1.4;
}
:deep(.inventory-action-contrast) {
  color: var(--q-secondary, #26a69a) !important;
}
</style>
