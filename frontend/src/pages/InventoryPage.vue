<template>
  <q-page class="q-pa-md ec-page">
    <div class="row items-center q-mb-md">
      <div class="text-h5 col">{{ t('app.nav.inventory') }}</div>
      <q-btn class="q-mr-sm" color="secondary" :label="t('inventory.importData')" icon="upload_file" @click="openImportDialog" />
      <q-btn color="primary" :label="t('finance.reload')" icon="refresh" unelevated @click="loadAll" :loading="store.loading" />
    </div>

    <q-banner
      v-if="showCachedOfflineBanner"
      class="bg-warning text-dark rounded-borders q-mb-md"
      dense
    >
      {{ t('inventory.cachedOfflineBanner') }}
    </q-banner>

    <q-tabs v-model="tab" inline-label align="left" class="q-mb-md">
      <q-tab name="overview" icon="dashboard" :label="t('inventory.tabs.overview')" />
      <q-tab name="products" icon="inventory_2" :label="t('inventory.tabs.products')" />
      <q-tab name="rentals" icon="sell" :label="t('inventory.tabs.rentals')" />
      <q-tab name="devices" icon="memory" :label="t('inventory.tabs.devices')" />
      <q-tab name="maintenance" icon="build_circle" :label="t('inventory.tabs.maintenance')" />
      <q-tab name="schedules" icon="event_repeat" :label="t('inventory.tabs.schedules')" />
      <q-tab name="categories" icon="account_tree" :label="t('inventory.tabs.categories')" />
      <q-tab name="locations" icon="warehouse" :label="t('inventory.tabs.locations')" />
    </q-tabs>

    <q-tab-panels v-model="tab" animated>
      <q-tab-panel name="overview" class="q-pa-none">
        <q-card class="ec-card q-pa-md">
          <div class="text-subtitle1">{{ t('inventory.overview.products', { count: inventoryProductCount }) }}</div>
          <div class="text-subtitle1">{{ t('inventory.overview.rentals', { count: rentalProducts.length }) }}</div>
          <div class="text-subtitle1">{{ t('inventory.overview.devices', { count: store.devices.length }) }}</div>
          <div class="text-subtitle1">{{ t('inventory.overview.categories', { count: categoryOverviewCount }) }}</div>
          <div class="text-subtitle1">{{ t('inventory.overview.storageLocations', { count: store.zones.length }) }}</div>
          <div class="text-subtitle1">{{ t('inventory.overview.maintenancePending', { count: overviewMaintenancePendingCount }) }}</div>
          <div class="text-subtitle1">{{ t('inventory.overview.mostUsedDevice', { device: overviewMostUsedDeviceLabel }) }}</div>
          <div class="text-subtitle1">{{ t('inventory.overview.mostUsedProductByDays', { product: overviewMostUsedProductByUsageDaysLabel }) }}</div>
        </q-card>
      </q-tab-panel>

      <q-tab-panel name="products" class="q-pa-none">
        <div class="row items-center q-mb-sm">
          <q-input v-model="productSearch" dense outlined clearable :placeholder="t('inventory.searchProducts')" class="col">
            <template #prepend><q-icon name="search" /></template>
          </q-input>
          <q-btn class="q-ml-sm" color="primary" icon="add" :label="t('inventory.newProduct')" unelevated @click="openCreateProduct" />
        </div>

        <div v-if="selectedProducts.length" class="row items-center q-gutter-sm q-mb-sm">
          <q-badge color="primary" :label="t('inventory.selectedCount', { count: selectedProducts.length })" />
          <q-btn :color="bulkPrintActionColor" :text-color="bulkPrintActionTextColor" icon="print" :label="t('inventory.bulkPrintLabels')" unelevated @click="openBulkPrintLabels('product', selectedProducts)" />
          <q-btn color="secondary" icon="edit" :label="t('inventory.bulkEdit')" unelevated @click="openBulkEditProducts" />
          <q-btn color="negative" icon="delete" :label="t('inventory.bulkDelete')" unelevated @click="runBulkDeleteProducts" />
          <q-btn flat :label="t('scan.clear')" @click="selectedProducts = []" />
        </div>

        <div class="row q-col-gutter-sm q-mb-sm">
          <div class="col-12 col-md-3">
            <q-select v-model="productCategoryFilter" :options="productCategoryOptions" :label="t('inventory.category')" outlined dense clearable emit-value map-options />
          </div>
          <div class="col-12 col-md-2">
            <q-select v-model="productTypeFilter" :options="productTypeOptions" :label="t('inventory.type')" outlined dense clearable emit-value map-options />
          </div>
          <div class="col-12 col-md-2">
            <q-select v-model="productBrandFilter" :options="productBrandOptions" :label="t('inventory.brand')" outlined dense clearable emit-value map-options />
          </div>
          <div class="col-12 col-md-2">
            <q-select v-model="productManufacturerFilter" :options="productManufacturerOptions" :label="t('inventory.manufacturer')" outlined dense clearable emit-value map-options />
          </div>
          <div class="col-12 col-md-3">
            <q-select v-model="productSort" :options="productSortOptions" :label="t('inventory.sort')" outlined dense emit-value map-options />
          </div>
        </div>

        <q-table
          :rows="filteredProducts"
          :columns="productColumns"
          row-key="id"
          selection="multiple"
          v-model:selected="selectedProducts"
          :grid="compactGrid"
          :hide-header="compactGrid"
          flat
          bordered
          :loading="store.loading"
          :pagination="{ 
            rowsPerPage: 200
            }"
          :rows-per-page-options="[10, 25, 50, 100, 200, 0]"
          class="ec-card inventory-products-table"
        >
          <template #body-cell-sku="props">
            <q-td :props="props">
              <div class="inventory-cell-ellipsis" :title="props.row.sku || ''">{{ props.row.sku || '—' }}</div>
            </q-td>
          </template>
          <template #body-cell-category="props">
            <q-td :props="props">
              <div class="inventory-cell-ellipsis" :title="props.row.category || ''">{{ props.row.category || '—' }}</div>
            </q-td>
          </template>
          <template #body-cell-brand="props">
            <q-td :props="props">
              <a
                v-if="getBrandLink(props.row.brand)"
                :href="getBrandLink(props.row.brand)"
                target="_blank"
                rel="noopener noreferrer"
                class="text-primary"
              >
                {{ props.row.brand || '—' }}
              </a>
              <span v-else>{{ props.row.brand || '—' }}</span>
            </q-td>
          </template>
          <template #body-cell-manufacturer="props">
            <q-td :props="props">
              <a
                v-if="getManufacturerLink(props.row.manufacturer)"
                :href="getManufacturerLink(props.row.manufacturer)"
                target="_blank"
                rel="noopener noreferrer"
                class="text-primary"
              >
                {{ props.row.manufacturer || '—' }}
              </a>
              <span v-else>{{ props.row.manufacturer || '—' }}</span>
            </q-td>
          </template>
          <template #body-cell-availability_now="props">
            <q-td :props="props">
              <q-badge
                :color="productAvailableNow(props.row.id) > 0 ? 'positive' : 'negative'"
                text-color="white"
                :label="t('inventory.availableCount', { count: productAvailableNow(props.row.id) })"
              />
            </q-td>
          </template>
          <template #body-cell-daily_rate="props">
            <q-td :props="props" class="text-right">{{ formatMoney(props.value) }}</q-td>
          </template>
          <template #body-cell-actions="props">
            <q-td :props="props" auto-width>
              <q-btn flat dense round icon="add_box" color="positive" class="q-mr-xs" @click="openQuickCreateDevices(props.row)" />
              <q-btn flat dense round icon="info" :color="infoActionColor" class="q-mr-xs inventory-action-contrast" @click="openProductInfo(props.row)" />
              <q-btn flat dense round icon="calendar_month" :color="calendarActionColor" class="q-mr-xs inventory-action-contrast" @click="openProductAvailabilityCalendar(props.row)" />
              <q-btn flat dense round icon="edit" color="primary" @click="openEditProduct(props.row)" />
            </q-td>
          </template>
          <template #item="props">
            <div class="q-pa-xs col-12">
              <q-card flat bordered>
                <q-card-section class="q-pb-sm">
                  <div class="text-subtitle2">{{ props.row.sku }} · {{ props.row.name }}</div>
                  <div class="text-caption text-grey-7">{{ props.row.brand || t('inventory.noBrand') }} · {{ props.row.manufacturer || t('inventory.noManufacturer') }}</div>
                </q-card-section>
                <q-card-section class="q-pt-none q-pb-sm">
                  <div class="row q-col-gutter-xs">
                    <div class="col-6"><q-badge :color="productAvailableNow(props.row.id) > 0 ? 'positive' : 'negative'" text-color="white" :label="t('inventory.availableLabelCount', { count: productAvailableNow(props.row.id) })" /></div>
                    <div class="col-6"><q-badge color="grey-8" text-color="white" :label="t('inventory.inStoreLabelCount', { count: props.row.in_store_devices || 0 })" /></div>
                    <div class="col-6"><q-badge color="info" text-color="white" :label="t('inventory.onSiteLabelCount', { count: props.row.on_site_devices || 0 })" /></div>
                    <div class="col-6"><q-badge color="negative" text-color="white" :label="t('inventory.damagedLabelCount', { count: props.row.damaged_devices || 0 })" /></div>
                    <div class="col-6"><q-badge color="primary" text-color="white" :label="t('inventory.totalLabelCount', { count: props.row.total_devices || 0 })" /></div>
                  </div>
                </q-card-section>
                <q-card-actions align="right">
                  <q-btn flat dense icon="add_box" color="positive" @click="openQuickCreateDevices(props.row)" />
                  <q-btn flat dense icon="info" :color="infoActionColor" class="inventory-action-contrast" @click="openProductInfo(props.row)" />
                  <q-btn flat dense icon="calendar_month" :color="calendarActionColor" class="inventory-action-contrast" @click="openProductAvailabilityCalendar(props.row)" />
                  <q-btn flat dense icon="edit" color="primary" @click="openEditProduct(props.row)" />
                </q-card-actions>
              </q-card>
            </div>
          </template>
        </q-table>
      </q-tab-panel>

      <q-tab-panel name="rentals" class="q-pa-none">
        <q-card class="ec-card q-pa-md">
          <div class="row items-center q-mb-sm">
            <div class="text-subtitle2 col">{{ t('inventory.rentalProducts') }}</div>
            <q-btn color="primary" icon="add" :label="t('inventory.newRentalProduct')" unelevated @click="openCreateRentalProduct" />
          </div>
          <div class="text-caption text-grey-7 q-mb-sm">{{ t('inventory.rentalProductsHint') }}</div>

          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-12 col-md-4">
              <q-input v-model="rentalProductSearch" dense outlined clearable :placeholder="t('inventory.searchRentalProducts')">
                <template #prepend><q-icon name="search" /></template>
              </q-input>
            </div>
            <div class="col-12 col-md-3">
              <q-select
                v-model="rentalProductSupplierFilter"
                :options="rentalSupplierOptions"
                :label="t('jobs.noSupplier')"
                outlined
                dense
                clearable
                emit-value
                map-options
              />
            </div>
            <div class="col-12 col-md-2">
              <q-select
                v-model="rentalProductSyncFilter"
                :options="rentalSyncFilterOptions"
                :label="t('inventory.sync')"
                outlined
                dense
                emit-value
                map-options
              />
            </div>
            <div class="col-12 col-md-3">
              <q-select
                v-model="rentalProductSort"
                :options="rentalProductSortOptions"
                :label="t('inventory.sort')"
                outlined
                dense
                emit-value
                map-options
              />
            </div>
          </div>

          <q-table
            :rows="filteredRentalProducts"
            :columns="rentalProductColumns"
            row-key="id"
            flat
            bordered
            dense
            :grid="compactGrid"
            :hide-header="compactGrid"
            :pagination="{ rowsPerPage: 50 }"
            :rows-per-page-options="[10, 25, 50, 100, 200]"
          >
            <template #body-cell-eventory_available_qty="props">
              <q-td :props="props" class="text-right">
                {{ Math.max(0, Number(props.row.eventory_available_qty || 0)) }}
              </q-td>
            </template>
            <template #body-cell-external_reference="props">
              <q-td :props="props">
                <q-badge
                  v-if="isSyncedEventoryProduct(props.row)"
                  color="info"
                  text-color="white"
                  :label="`Synced: ${eventoryInstanceLabelById(props.row.external_reference)}`"
                />
                <span v-else class="text-grey-6">{{ t('home.manual') }}</span>
              </q-td>
            </template>
            <template #body-cell-rental_price="props">
              <q-td :props="props" class="text-right">{{ formatMoney(props.value) }}</q-td>
            </template>
            <template #body-cell-daily_rate="props">
              <q-td :props="props" class="text-right">{{ formatMoney(props.value) }}</q-td>
            </template>
            <template #body-cell-actions="props">
              <q-td :props="props" auto-width>
                <q-btn flat dense round icon="info" :color="infoActionColor" class="q-mr-xs inventory-action-contrast" @click="openRentalProductInfo(props.row)" />
                <q-btn flat dense round icon="edit" color="primary" @click="openEditRentalProduct(props.row)" />
              </q-td>
            </template>
            <template #item="props">
              <div class="q-pa-xs col-12">
                <q-card flat bordered>
                  <q-card-section class="q-pb-sm">
                    <div class="text-subtitle2">{{ props.row.sku }} · {{ props.row.name }}</div>
                    <div class="text-caption text-grey-7">
                      {{ props.row.category || '—' }}
                      <span v-if="props.row.supplier_name"> · {{ props.row.supplier_name }}</span>
                    </div>
                  </q-card-section>
                  <q-card-section class="q-pt-none q-pb-sm">
                    <div class="row q-col-gutter-xs">
                      <div class="col-auto">
                        <q-badge color="teal-7" text-color="white" :label="`${t('inventory.columnQty')}: ${Math.max(0, Number(props.row.eventory_available_qty || 0))}`" />
                      </div>
                      <div v-if="props.row.rental_price != null" class="col-auto">
                        <q-badge color="grey-8" text-color="white" :label="`${t('inventory.columnSupplierPrice')}: ${formatMoney(props.row.rental_price)}`" />
                      </div>
                      <div v-if="props.row.daily_rate != null" class="col-auto">
                        <q-badge color="primary" text-color="white" :label="`${t('inventory.columnClientPrice')}: ${formatMoney(props.row.daily_rate)}`" />
                      </div>
                      <div class="col-auto">
                        <q-badge
                          v-if="isSyncedEventoryProduct(props.row)"
                          color="info"
                          text-color="white"
                          :label="t('inventory.linkedEventoryInstance', { instance: eventoryInstanceLabelById(props.row.external_reference) })"
                        />
                        <q-badge v-else color="grey-6" text-color="white" :label="t('home.manual')" />
                      </div>
                    </div>
                  </q-card-section>
                  <q-card-actions align="right">
                    <q-btn flat dense icon="info" :color="infoActionColor" class="inventory-action-contrast" :aria-label="t('inventory.openRentalProductInfo')" @click="openRentalProductInfo(props.row)" />
                    <q-btn flat dense icon="edit" color="primary" :aria-label="t('inventory.editRentalProduct')" @click="openEditRentalProduct(props.row)" />
                  </q-card-actions>
                </q-card>
              </div>
            </template>
          </q-table>
        </q-card>
      </q-tab-panel>

      

      <q-tab-panel name="devices" class="q-pa-none">
        <div class="row items-center q-mb-sm">
          <q-input v-model="deviceSearch" dense outlined clearable :placeholder="t('inventory.searchDevices')" class="col">
            <template #prepend><q-icon name="search" /></template>
          </q-input>
          <q-btn class="q-ml-sm" color="primary" icon="add" :label="t('inventory.newDevice')" unelevated @click="openCreateDevice" />
        </div>

        <div v-if="selectedDevices.length" class="row items-center q-gutter-sm q-mb-sm">
          <q-badge color="primary" :label="t('inventory.selectedCount', { count: selectedDevices.length })" />
          <q-btn :color="bulkPrintActionColor" :text-color="bulkPrintActionTextColor" icon="print" :label="t('inventory.bulkPrintLabels')" unelevated @click="openBulkPrintLabels('device', selectedDevices)" />
          <q-btn color="secondary" icon="edit" :label="t('inventory.bulkEdit')" unelevated @click="openBulkEditDevices" />
          <q-btn color="negative" icon="delete" :label="t('inventory.bulkDelete')" unelevated @click="runBulkDeleteDevices" />
          <q-btn flat :label="t('scan.clear')" @click="selectedDevices = []" />
        </div>

        <q-table
          :rows="filteredDevices"
          :columns="deviceColumns"
          row-key="id"
          selection="multiple"
          v-model:selected="selectedDevices"
          :grid="compactGrid"
          :hide-header="compactGrid"
          flat
          bordered
          :loading="store.loading"
          :pagination="{ rowsPerPage: 50 }"
          :rows-per-page-options="[10, 25, 50, 100, 200]"
          class="ec-card"
        >
          <template #body-cell-status="props">
            <q-td :props="props"><q-badge :label="props.value" :color="deviceStatusColor(props.value)" /></q-td>
          </template>
          <template #body-cell-condition="props">
            <q-td :props="props"><q-badge :label="props.value || 'n/a'" :color="conditionColor(props.value)" /></q-td>
          </template>
          <template #body-cell-current_job_code="props">
            <q-td :props="props">
              <q-badge v-if="props.row.current_job_code" color="info" text-color="white" :label="props.row.current_job_code" />
              <span v-else class="text-grey-6">-</span>
            </q-td>
          </template>
          <template #body-cell-location_zone_id="props">
            <q-td :props="props">{{ props.row.case_asset_tag ? `Case: ${props.row.case_asset_tag}` : (zoneNameById(props.value) || 'Unassigned') }}</q-td>
          </template>
          <template #body-cell-actions="props">
            <q-td :props="props" auto-width>
              <q-btn flat dense round icon="info" :color="infoActionColor" class="q-mr-xs inventory-action-contrast" @click="deviceInfoTarget = props.row; deviceInfoDialogOpen = true" />
              <q-btn flat dense round icon="edit" color="primary" @click="openEditDevice(props.row)" />
            </q-td>
          </template>
          <template #item="props">
            <div class="q-pa-xs col-12">
              <q-card flat bordered>
                <q-card-section class="q-pb-sm">
                  <div class="text-subtitle2">{{ props.row.asset_tag }}</div>
                  <div class="text-caption text-grey-7">{{ store.products.find(item => item.id === props.row.product_id)?.name || `Product #${props.row.product_id}` }}</div>
                </q-card-section>
                <q-card-section class="q-pt-none q-pb-sm">
                  <div class="row q-col-gutter-xs">
                    <div class="col-6"><q-badge :color="deviceStatusColor(props.row.status)" :label="props.row.status" /></div>
                    <div class="col-6"><q-badge color="grey-7" :label="props.row.condition || 'n/a'" /></div>
                    <div class="col-12" v-if="props.row.serial_number"><div class="text-caption">Serial: {{ props.row.serial_number }}</div></div>
                    <div class="col-12" v-if="props.row.current_job_code"><div class="text-caption">On job: {{ props.row.current_job_code }}</div></div>
                    <div class="col-12"><div class="text-caption">Location: {{ props.row.case_asset_tag ? `Case: ${props.row.case_asset_tag}` : (zoneNameById(props.row.location_zone_id) || 'Unassigned') }}</div></div>
                  </div>
                </q-card-section>
                <q-card-actions align="right">
                  <q-btn flat dense icon="info" :color="infoActionColor" class="inventory-action-contrast" @click="deviceInfoTarget = props.row; deviceInfoDialogOpen = true" />
                  <q-btn flat dense icon="edit" color="primary" @click="openEditDevice(props.row)" />
                </q-card-actions>
              </q-card>
            </div>
          </template>
        </q-table>
      </q-tab-panel>

      <q-tab-panel name="maintenance" class="q-pa-none">
        <div class="row items-center q-mb-sm">
          <q-input v-model="maintenanceSearch" dense outlined clearable :placeholder="t('inventory.searchMaintenance')" class="col">
            <template #prepend><q-icon name="search" /></template>
          </q-input>
          <q-btn class="q-ml-sm" color="secondary" icon="build" :label="t('inventory.createTask')" unelevated @click="openCreateMaintenance('task')" />
          <q-btn class="q-ml-sm" color="positive" icon="event_repeat" :label="t('inventory.createSchedule')" unelevated @click="openCreateMaintenance('schedule')" />
        </div>

        <div v-if="selectedMaintenance.length" class="row items-center q-gutter-sm q-mb-sm">
          <q-badge color="primary" :label="t('inventory.selectedCount', { count: selectedMaintenance.length })" />
          <q-btn color="secondary" icon="edit" :label="t('inventory.bulkEdit')" unelevated @click="openBulkEditMaintenance" />
          <q-btn color="negative" icon="delete" :label="t('inventory.bulkDelete')" unelevated @click="runBulkDeleteMaintenance" />
          <q-btn flat :label="t('scan.clear')" @click="selectedMaintenance = []" />
        </div>

        <q-table
          :rows="filteredMaintenance"
          :columns="maintenanceColumns"
          row-key="id"
          selection="multiple"
          v-model:selected="selectedMaintenance"
          :grid="compactGrid"
          :hide-header="compactGrid"
          flat
          bordered
          :loading="store.loading"
          :pagination="{ rowsPerPage: 50 }"
          :rows-per-page-options="[10, 25, 50, 100, 200]"
          class="ec-card"
        >
          <template #body-cell-source="props">
            <q-td :props="props">
              <q-badge :label="maintenanceSourceLabel(props.row)" :color="maintenanceSourceColor(props.row)" />
            </q-td>
          </template>
          <template #body-cell-status="props">
            <q-td :props="props"><q-badge :label="props.value" :color="maintenanceStatusColor(props.value)" /></q-td>
          </template>
          <template #body-cell-actions="props">
            <q-td :props="props" auto-width>
              <q-btn
                v-if="props.row.status !== 'completed'"
                flat dense round icon="task_alt" color="positive" class="q-mr-xs"
                @click="completeMaintenanceRow(props.row)"
              />
              <q-btn
                v-if="props.row.schedule_id"
                flat dense round icon="event_repeat" color="positive" class="q-mr-xs"
                @click="openEditMaintenanceSchedule(props.row)"
              />
              <q-btn flat dense round icon="edit" color="primary" @click="openEditMaintenance(props.row)" />
            </q-td>
          </template>
          <template #item="props">
            <div class="q-pa-xs col-12">
              <q-card flat bordered>
                <q-card-section class="q-pb-sm">
                  <div class="text-subtitle2">{{ props.row.asset_tag || t('inventory.noAssetTag') }}</div>
                  <div class="text-caption text-grey-7">{{ props.row.product_name || t('finance.unknown') }} · {{ props.row.maintenance_type }}</div>
                  <div class="q-mt-xs">
                    <q-badge :label="maintenanceSourceLabel(props.row)" :color="maintenanceSourceColor(props.row)" />
                  </div>
                </q-card-section>
                <q-card-section class="q-pt-none q-pb-sm">
                  <div class="row q-col-gutter-xs items-center">
                    <div class="col-12"><q-badge :color="maintenanceStatusColor(props.row.status)" :label="props.row.status" /></div>
                    <div class="col-12 text-caption">{{ t('inventory.scheduled') }}: {{ props.row.scheduled_date || '-' }}</div>
                    <div class="col-12 text-caption" v-if="props.row.completed_date">{{ t('inventory.completed') }}: {{ props.row.completed_date }}</div>
                    <div class="col-12 text-caption" v-if="props.row.notes">{{ props.row.notes }}</div>
                  </div>
                </q-card-section>
                <q-card-actions align="right">
                  <q-btn
                    v-if="props.row.status !== 'completed'"
                    flat dense icon="task_alt" color="positive"
                    @click="completeMaintenanceRow(props.row)"
                  />
                  <q-btn
                    v-if="props.row.schedule_id"
                    flat dense icon="event_repeat" color="positive"
                    @click="openEditMaintenanceSchedule(props.row)"
                  />
                  <q-btn flat dense icon="edit" color="primary" @click="openEditMaintenance(props.row)" />
                </q-card-actions>
              </q-card>
            </div>
          </template>
        </q-table>
      </q-tab-panel>

      <q-tab-panel name="schedules" class="q-pa-none">
        <div class="row items-center q-mb-sm">
          <q-input v-model="scheduleSearch" dense outlined clearable :placeholder="t('inventory.searchSchedules')" class="col">
            <template #prepend><q-icon name="search" /></template>
          </q-input>
          <q-btn class="q-ml-sm" color="positive" icon="event_repeat" :label="t('inventory.createSchedule')" unelevated @click="openCreateMaintenance('schedule')" />
        </div>

        <div v-if="selectedSchedules.length" class="row items-center q-gutter-sm q-mb-sm">
          <q-badge color="primary" :label="t('inventory.selectedCount', { count: selectedSchedules.length })" />
          <q-btn color="secondary" icon="edit" :label="t('inventory.bulkEdit')" unelevated @click="openBulkEditSchedules" />
          <q-btn color="negative" icon="delete" :label="t('inventory.bulkDelete')" unelevated @click="runBulkDeleteSchedules" />
          <q-btn flat :label="t('scan.clear')" @click="selectedSchedules = []" />
        </div>

        <q-table
          :rows="filteredSchedules"
          :columns="scheduleColumns"
          row-key="id"
          selection="multiple"
          v-model:selected="selectedSchedules"
          :grid="compactGrid"
          :hide-header="compactGrid"
          flat
          bordered
          :loading="store.loading"
          :pagination="{ rowsPerPage: 50 }"
          :rows-per-page-options="[10, 25, 50, 100, 200]"
          class="ec-card"
        >
          <template #body-cell-id="props">
            <q-td :props="props">#{{ props.row.id }}</q-td>
          </template>
          <template #body-cell-interval="props">
            <q-td :props="props">{{ scheduleIntervalLabel(props.row) }}</q-td>
          </template>
          <template #body-cell-task_count="props">
            <q-td :props="props">{{ scheduleTaskCount(props.row.id) }}</q-td>
          </template>
          <template #body-cell-updated_at="props">
            <q-td :props="props">{{ formatDateTime(props.row.updated_at) }}</q-td>
          </template>
          <template #body-cell-actions="props">
            <q-td :props="props" auto-width>
              <q-btn flat dense round icon="edit" color="primary" @click="openEditMaintenanceSchedule(props.row)" />
            </q-td>
          </template>
          <template #item="props">
            <div class="q-pa-xs col-12">
              <q-card flat bordered>
                <q-card-section class="q-pb-sm">
                  <div class="text-subtitle2">{{ t('inventory.scheduleLabel', { id: props.row.id }) }}</div>
                  <div class="text-caption text-grey-7">{{ props.row.maintenance_type || '-' }} · {{ scheduleIntervalLabel(props.row) }}</div>
                </q-card-section>
                <q-card-section class="q-pt-none q-pb-sm">
                  <div class="row q-col-gutter-xs items-center">
                    <div class="col-12 text-caption">{{ t('inventory.tasks') }}: {{ scheduleTaskCount(props.row.id) }}</div>
                    <div class="col-12 text-caption">{{ t('inventory.scheduled') }}: {{ props.row.scheduled_date || '-' }}</div>
                    <div class="col-12 text-caption" v-if="props.row.notes">{{ props.row.notes }}</div>
                  </div>
                </q-card-section>
                <q-card-actions align="right">
                  <q-btn flat dense icon="edit" color="primary" @click="openEditMaintenanceSchedule(props.row)" />
                </q-card-actions>
              </q-card>
            </div>
          </template>
        </q-table>
      </q-tab-panel>

      <q-tab-panel name="categories" class="q-pa-none">
        <div class="row items-center q-mb-sm">
          <q-btn color="primary" icon="add" :label="t('inventory.newCategory')" unelevated @click="openCreateCategory" />
          <q-btn class="q-ml-sm" color="secondary" icon="playlist_add" :label="t('settings.inventory.resetCategoryDefaults')" @click="prefillCategories" />
        </div>

        <q-card class="ec-card q-pa-md">
          <div class="text-subtitle1 q-mb-sm">{{ t('inventory.categoryTree') }}</div>
          <div class="q-pa-sm q-mb-sm bg-grey-2 text-dark rounded-borders text-caption" @dragover.prevent @drop="onCategoryDropToRoot">
            {{ t('inventory.dropCategoryToRoot') }}
          </div>
          <q-tree :nodes="categoryTreeNodes" node-key="id" label-key="label" children-key="children" default-expand-all :no-nodes-label="t('inventory.noCategoriesYet')">
            <template #default-header="prop">
              <div
                class="row items-center no-wrap full-width"
                draggable="true"
                @dragstart="onCategoryDragStart(prop.node)"
                @dragend="onCategoryDragEnd"
                @dragover.prevent
                @drop="onCategoryDropOnRow(prop.node)"
              >
                <q-icon name="drag_indicator" size="16px" class="q-mr-xs text-grey-6" />
                <div class="col ellipsis">{{ prop.node.name }}</div>
                <q-badge
                  size="sm"
                  class="q-mr-xs"
                  :color="prop.node.is_active ? 'positive' : 'grey'"
                  :label="prop.node.is_active ? t('settings.auth.active') : t('settings.auth.inactive')"
                />
                <q-btn flat dense round icon="edit" color="primary" class="q-mr-xs" @click.stop="openEditCategory(prop.node)" />
                <q-btn flat dense round icon="delete" color="negative" @click.stop="confirmDeleteCategory(prop.node)" />
              </div>
            </template>
          </q-tree>
        </q-card>
      </q-tab-panel>

      <q-tab-panel name="locations" class="q-pa-none">
        <div class="row items-center q-mb-sm">
          <q-btn color="primary" icon="add" :label="t('inventory.newLocation')" unelevated @click="openCreateLocation" />
        </div>
        <div v-if="selectedLocationIds.length" class="row items-center q-gutter-sm q-mb-sm">
          <q-badge color="primary" :label="t('inventory.selectedCount', { count: selectedLocationIds.length })" />
          <q-btn :color="bulkPrintActionColor" :text-color="bulkPrintActionTextColor" icon="print" :label="t('inventory.bulkPrintLabels')" unelevated @click="openBulkPrintLabels('location', selectedLocationIds)" />
          <q-btn color="negative" icon="delete" :label="t('inventory.bulkDelete')" unelevated @click="bulkDeleteDialogOpen = true" />
          <q-btn flat :label="t('scan.clear')" @click="selectedLocationIds = []" />
        </div>
        <q-card class="ec-card q-pa-md">
          <div class="text-subtitle1 q-mb-sm">{{ t('inventory.storageTree') }}</div>
          <div class="q-pa-sm q-mb-sm bg-grey-2 text-dark rounded-borders text-caption" @dragover.prevent @drop="onLocationDropToRoot">
            {{ t('inventory.dropLocationToRoot') }}
          </div>
          <q-tree
            :nodes="locationTreeNodes"
            node-key="id"
            label-key="label"
            children-key="children"
            default-expand-all
            :no-nodes-label="t('inventory.noLocationsYet')"
            tick-strategy="strict"
            v-model:ticked="selectedLocationIds"
          >
            <template #default-header="prop">
              <div
                class="row items-center no-wrap full-width"
                draggable="true"
                @dragstart="onLocationDragStart(prop.node)"
                @dragend="onLocationDragEnd"
                @dragover.prevent
                @drop="onLocationDropOnRow(prop.node)"
              >
                <q-icon name="drag_indicator" size="16px" class="q-mr-xs text-grey-6" />
                <div class="col ellipsis">
                  {{ prop.node.name }}
                  <span class="text-caption text-grey-7">({{ prop.node.code }})</span>
                </div>
                <q-badge size="sm" class="q-mr-xs" color="primary" :label="prop.node.zone_type" />
                <q-badge
                  size="sm"
                  class="q-mr-xs"
                  :color="prop.node.is_active ? 'positive' : 'grey'"
                  :label="prop.node.is_active ? 'Active' : 'Inactive'"
                />
                <q-btn flat dense round icon="playlist_add" class="q-mr-xs inventory-action-contrast" @click.stop="openBulkCreateSubzones(prop.node)">
                  <q-tooltip>{{ tr('inventory.bulkCreateSubzones.addButton', 'Add multiple subzones') }}</q-tooltip>
                </q-btn>
                <q-btn flat dense round icon="select_all" class="q-mr-xs inventory-action-contrast" @click.stop="selectNodeAndChildren(prop.node)">
                  <q-tooltip>{{ tr('inventory.selectNodeAndChildren', 'Select node and children') }}</q-tooltip>
                </q-btn>
                <q-btn flat dense round icon="edit" color="primary" @click.stop="openEditLocation(prop.node)" />
              </div>
            </template>
          </q-tree>
        </q-card>
      </q-tab-panel>
    </q-tab-panels>

    <q-dialog v-model="rentalProductDialogOpen" persistent :maximized="isPhone">
      <q-card :style="isPhone ? 'width: 100vw; max-width: 100vw; height: 100vh' : 'min-width: 760px; max-width: 95vw'" class="ec-card">
        <q-card-section><div class="text-h6">{{ rentalProductDraft.id ? t('inventory.editRentalProduct') : t('inventory.newRentalProduct') }}</div></q-card-section>
        <q-card-section class="q-pt-none" :style="isPhone ? 'max-height: calc(100vh - 140px); overflow: auto;' : ''">
          <q-form ref="rentalProductFormRef" @submit.prevent="saveRentalProduct">
            <q-expansion-item v-model="rentalGeneralExpanded" icon="sell" :label="t('inventory.general')" dense header-class="rounded-borders">
              <div class="q-pt-sm row q-col-gutter-sm">
                <div class="col-12 col-md-4"><q-input v-model="rentalProductDraft.sku" :label="t('inventory.columnSku')" outlined dense :rules="[v => !!v || t('login.required')]" /></div>
                <div class="col-12 col-md-8"><q-input v-model="rentalProductDraft.name" :label="t('inventory.columnName')" outlined dense :rules="[v => !!v || t('login.required')]" /></div>
                <div class="col-12 col-md-4"><q-input v-model="rentalProductDraft.category" :label="t('inventory.columnCategory')" outlined dense /></div>
                <div class="col-12 col-md-4"><q-input v-model="rentalProductDraft.supplier_name" :label="t('inventory.columnSupplier')" outlined dense /></div>
              </div>
            </q-expansion-item>

            <q-expansion-item v-model="rentalPricingExpanded" icon="payments" :label="t('inventory.pricingAndSync')" dense header-class="rounded-borders" class="q-mt-sm">
              <div class="q-pt-sm row q-col-gutter-sm">
                <div class="col-12 col-md-4">
                  <q-input
                    v-model.number="rentalProductDraft.rental_price"
                    type="number"
                    min="0"
                    step="0.01"
                    :label="t('inventory.columnSupplierPrice')"
                    :suffix="activeCurrencyCode"
                    :hint="currencyHelperText"
                    outlined
                    dense
                    @update:model-value="onRentalSupplierPriceChanged"
                  />
                </div>
                <div class="col-12 col-md-4">
                  <q-input
                    v-model.number="rentalProductDraft.daily_rate"
                    type="number"
                    min="0"
                    step="0.01"
                    :label="t('inventory.columnClientPrice')"
                    :suffix="activeCurrencyCode"
                    :hint="currencyHelperText"
                    outlined
                    dense
                  />
                </div>
                <div class="col-12">
                  <q-banner v-if="isCurrentRentalDraftSynced" dense class="bg-info text-white rounded-borders">
                    {{ t('inventory.linkedEventoryInstance', { instance: eventoryInstanceLabelById(rentalProductDraft.external_reference) }) }}
                  </q-banner>
                  <div v-else class="text-caption text-grey-7">{{ t('inventory.manualRentalProductHint') }}</div>
                </div>
              </div>
            </q-expansion-item>

            <q-expansion-item v-model="rentalCustomFieldsExpanded" icon="tune" :label="t('inventory.customFields')" dense header-class="rounded-borders" class="q-mt-sm">
              <div class="q-pt-sm">
                <div v-if="rentalProductFieldRows.length">
                  <div v-for="field in rentalProductFieldRows" :key="field.field_definition_id" class="q-mb-sm">
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
                <div v-else class="text-caption text-grey-7">{{ t('inventory.noProductCustomFields') }}</div>
              </div>
            </q-expansion-item>

            <q-banner v-if="rentalProductDialogError" class="bg-negative text-white q-mt-sm rounded-borders" dense>
              {{ rentalProductDialogError }}
            </q-banner>
          </q-form>
        </q-card-section>
        <q-card-actions :align="isPhone ? 'stretch' : 'right'" :class="isPhone ? 'q-pa-md bg-grey-2' : ''">
          <q-btn flat :class="isPhone ? 'full-width q-mb-sm' : ''" :label="t('app.actions.cancel')" @click="rentalProductDialogOpen = false" />
          <q-btn
            color="primary"
            unelevated
            :class="isPhone ? 'full-width' : ''"
            :label="rentalProductDraft.id ? t('app.actions.save') : t('users.create')"
            :loading="rentalProductSaving"
            @click="saveRentalProduct"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="bulkDeleteDialogOpen" persistent>
      <q-card class="ec-card">
        <q-card-section>
          <div class="text-h6">{{ t('inventory.bulkDelete') }}</div>
          <div class="text-caption text-grey-7">{{ t('inventory.bulkDeleteConfirm', { count: selectedLocationIds.length }) }}</div>
          <q-banner v-if="bulkDeleteError" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ bulkDeleteError }}</q-banner>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="bulkDeleteDialogOpen = false" />
          <q-btn color="negative" unelevated :label="t('inventory.bulkDelete')" :loading="bulkDeleteSaving" @click="doBulkDeleteLocations" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <ProductDialog
      v-model="productDialogOpen"
      :product="productEditing"
      @saved="onProductDialogSaved"
      @edit-device="openDeviceEditorFromLink"
      @view-device="openDeviceInfoFromLink"
      @edit-product="openProductEditorFromLink"
    />

    <DeviceDialog
      v-model="deviceDialogOpen"
      :device="deviceEditing"
      :is-phone="isPhone"
      @saved="onDeviceDialogSaved"
    />

    <q-dialog v-model="categoryDialogOpen" persistent>
      <q-card style="width: 520px; max-width: 95vw" class="ec-card">
        <q-card-section><div class="text-h6">{{ categoryEditing ? t('inventory.editCategory') : t('inventory.newCategory') }}</div></q-card-section>
        <q-card-section class="q-pt-none">
          <q-form ref="categoryFormRef" @submit.prevent="saveCategory">
            <q-input v-model="categoryForm.name" :label="t('users.name')" outlined dense class="q-mb-sm" :rules="[v => !!v || t('login.required')]" />
            <q-select v-model="categoryForm.parent_id" :options="parentCategoryOptions" :label="t('inventory.parentCategory')" outlined dense clearable emit-value map-options class="q-mb-sm" />
            <q-input v-model.number="categoryForm.sort_order" type="number" :label="t('inventory.sortOrder')" outlined dense class="q-mb-sm" />
            <q-toggle v-model="categoryForm.is_active" :label="t('settings.auth.active')" color="primary" />
            <q-banner v-if="categoryDialogError" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ categoryDialogError }}</q-banner>
          </q-form>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="categoryDialogOpen = false" />
          <q-btn color="primary" unelevated :label="categoryEditing ? 'Save' : 'Create'" :loading="saving" @click="saveCategory" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="locationDialogOpen" persistent>
      <q-card style="width: 560px; max-width: 95vw" class="ec-card">
        <q-card-section><div class="text-h6">{{ locationEditing ? t('inventory.editLocation') : t('inventory.newLocation') }}</div></q-card-section>
        <q-card-section class="q-pt-none">
          <q-form ref="locationFormRef" @submit.prevent="saveLocation">
            <q-input v-model="locationForm.name" :label="t('users.name')" outlined dense class="q-mb-sm" :rules="[v => !!v || t('login.required')]" />
            <q-input v-model="locationForm.code" :label="t('inventory.code')" outlined dense class="q-mb-sm" :rules="[v => !!v || t('login.required')]" @update:model-value="() => { locationCodeEdited = true }" />
            <div class="row items-center q-mb-sm">
              <div class="col">
                <div v-if="locationForm.name" class="text-caption text-grey-7">
                  {{ t('inventory.generatedCodePreview', { slug: slugify(locationForm.name) }) }}
                </div>
              </div>
              <div class="col-auto">
                <q-btn dense flat size="sm" :label="t('app.actions.reset')" color="primary" v-if="locationForm.name" @click="() => { locationForm.code = slugify(locationForm.name); locationCodeEdited = false }" />
              </div>
            </div>
            <div class="row q-col-gutter-sm q-mb-sm">
              <div class="col-12 col-md-6">
                <q-toggle v-model="locationAutoGenerateCode" :label="t('inventory.autoGenerateCode')" color="primary" />
              </div>
            </div>
            <div class="row q-col-gutter-sm q-mb-sm">
              <div class="col-12 col-md-4">
                <q-input v-model="locationForm.barcode" label="Barcode" outlined dense />
              </div>
              <div class="col-12 col-md-4">
                <q-input v-model="locationForm.qr_code" label="QR code" outlined dense />
              </div>
              <div class="col-12 col-md-4">
                <q-input v-model="locationForm.rfid" label="RFID" outlined dense />
              </div>
            </div>
            <q-select
              v-model="locationForm.zone_type"
              :options="locationTypeOptions"
              :label="t('inventory.type')"
              outlined
              dense
              emit-value
              map-options
              class="q-mb-sm"
            />
            <q-select v-model="locationForm.parent_id" :options="parentLocationOptions" :label="t('inventory.parentLocation')" outlined dense clearable emit-value map-options class="q-mb-sm" />
            <q-input v-model.number="locationForm.sort_order" type="number" :label="t('inventory.sortOrder')" outlined dense class="q-mb-sm" />
            <q-toggle v-model="locationForm.is_active" :label="t('settings.auth.active')" color="primary" />
            <q-banner v-if="locationDialogError" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ locationDialogError }}</q-banner>
          </q-form>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="locationDialogOpen = false" />
          <q-btn color="primary" unelevated :label="locationEditing ? 'Save' : 'Create'" :loading="saving" @click="saveLocation" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="bulkCreateDialogOpen" persistent>
      <q-card style="width: 520px; max-width: 95vw" class="ec-card">
        <q-card-section>
          <div class="text-h6">{{ tr('inventory.bulkCreateSubzones.title', 'Create multiple subzones') }}</div>
          <div class="text-caption text-grey-7">{{ tr('inventory.bulkCreateSubzones.hint', 'Enter one subzone name per line. These will be created as children of the chosen location.') }}</div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <div class="q-mb-sm">
            <q-input type="textarea" autogrow v-model="bulkCreateText" :label="tr('inventory.bulkCreateSubzones.names', 'Subzone names (one per line)')" outlined dense />
          </div>
          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-12 col-md-6">
              <q-select v-model="bulkCreateZoneType" :options="locationTypeOptions" :label="t('inventory.type')" outlined dense emit-value map-options />
            </div>
            <div class="col-12 col-md-6">
              <q-toggle v-model="bulkCreateIsActive" :label="t('settings.auth.active')" color="primary" />
            </div>
          </div>
          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-12 col-md-6">
              <q-toggle v-model="bulkCreateInterpretRanges" :label="tr('inventory.bulkCreateSubzones.interpretRanges', 'Interpret ranges (A-D, 01-05)')" color="primary" />
            </div>
            <div class="col-12 col-md-6">
              <q-toggle v-model="bulkCreateAutoGenerateCode" :label="tr('inventory.bulkCreateSubzones.autoGenerateCode', 'Auto-generate codes from names')" color="primary" />
            </div>
          </div>
          <q-banner v-if="bulkCreateError" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ bulkCreateError }}</q-banner>
        </q-card-section>
          <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="bulkCreateDialogOpen = false" />
          <q-btn color="primary" unelevated :label="tr('inventory.create', 'Create')" :loading="saving" @click="saveBulkCreateSubzones" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="deleteCategoryDialogOpen" persistent>
      <q-card class="ec-card">
        <q-card-section class="row items-center">
          <q-icon name="warning" color="negative" size="md" class="q-mr-md" />
          <span>{{ t('inventory.deleteCategoryPrompt', { name: deleteCategoryTarget?.name }) }}</span>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="deleteCategoryDialogOpen = false" />
          <q-btn color="negative" unelevated :label="t('users.delete')" :loading="saving" @click="doDeleteCategory" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="quickCreateDialogOpen" persistent>
      <q-card style="width: 560px; max-width: 95vw" class="ec-card">
        <q-card-section>
          <div class="text-h6">{{ t('inventory.createDevices') }}</div>
          <div class="text-caption text-grey-7">{{ quickCreateTargetProduct?.sku }} - {{ quickCreateTargetProduct?.name }}</div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <div class="row q-col-gutter-sm">
            <div class="col-12 col-md-4">
              <q-input v-model.number="quickCreateForm.quantity" type="number" min="1" :label="t('inventory.quantity')" outlined dense />
            </div>
            <div class="col-12 col-md-8">
              <q-toggle v-model="quickCreateForm.auto_generate" :label="t('inventory.autoGenerateAssetTags')" color="primary" />
            </div>
            <div class="col-12 col-md-6" v-if="quickCreateForm.auto_generate">
              <q-input v-model="quickCreateForm.asset_tag_prefix" :label="t('inventory.assetTagPrefixOptional')" outlined dense />
            </div>
            <div class="col-12 col-md-6" v-else>
              <q-input v-model="quickCreateForm.asset_tag" :label="t('scan.assetTag')" outlined dense :rules="[v => !!v || t('inventory.requiredWhenAutoGenerateOff')]" />
            </div>
            <div class="col-12 col-md-4">
              <q-select v-model="quickCreateForm.status" :options="statusOptions" label="Status" outlined dense emit-value map-options />
            </div>
            <div class="col-12 col-md-4">
              <q-select v-model="quickCreateForm.condition" :options="conditionOptions" label="Condition" outlined dense emit-value map-options />
            </div>
            <div class="col-12 col-md-4">
              <q-select v-model="quickCreateForm.location_zone_id" :options="locationSelectOptions" label="Location" outlined dense emit-value map-options clearable />
            </div>
          </div>
          <q-banner v-if="quickCreateError" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ quickCreateError }}</q-banner>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="quickCreateDialogOpen = false" />
          <q-btn color="primary" unelevated :label="t('users.create')" :loading="saving" @click="runQuickCreateDevices" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="maintenanceDialogOpen" persistent>
      <q-card style="width: 720px; max-width: 95vw" class="ec-card">
        <q-card-section><div class="text-h6">{{ maintenanceDialogTitle }}</div></q-card-section>
        <q-card-section class="q-pt-none">
          <q-form ref="maintenanceFormRef" @submit.prevent="saveMaintenance">
            <div class="row q-col-gutter-sm">
              <div class="col-12" v-if="!maintenanceEditing && maintenanceDialogMode === 'schedule'">
                <q-expansion-item v-model="maintenanceTargetsExpanded" icon="tune" :label="t('inventory.targetsProductsDevices')" dense>
                  <div class="q-pt-sm">
                    <q-banner dense class="bg-info text-white rounded-borders q-mb-sm">
                      {{ t('inventory.productSchedulesBanner') }}
                    </q-banner>
                    <div class="row q-col-gutter-sm">
                      <div class="col-12 col-md-6">
                        <q-select
                          v-model="maintenanceForm.product_ids"
                          :options="productOptions"
                          :label="t('inventory.products')"
                          outlined
                          dense
                          multiple
                          use-chips
                          emit-value
                          map-options
                        />
                      </div>
                      <div class="col-12 col-md-6">
                        <q-select
                          v-model="maintenanceForm.device_ids"
                          :options="deviceSelectOptions"
                          :label="t('inventory.additionalSpecificDevicesOptional')"
                          outlined
                          dense
                          multiple
                          use-chips
                          emit-value
                          map-options
                        />
                      </div>
                    </div>
                  </div>
                </q-expansion-item>
              </div>
              <div class="col-12" v-if="!maintenanceEditing && maintenanceDialogMode === 'task'">
                <q-banner dense class="bg-info text-white rounded-borders q-mb-sm">
                  {{ t('inventory.directMaintenanceTaskBanner') }}
                </q-banner>
                <q-select
                  v-model="maintenanceForm.device_ids"
                  :options="deviceSelectOptions"
                  :label="t('inventory.device')"
                  outlined
                  dense
                  multiple
                  use-chips
                  emit-value
                  map-options
                />
              </div>
              <div class="col-12 col-md-6" v-if="maintenanceEditing">
                <q-select
                  v-model="maintenanceForm.device_ids"
                  :options="deviceSelectOptions"
                  :label="t('inventory.device')"
                  outlined
                  dense
                  multiple
                  use-chips
                  emit-value
                  map-options
                />
              </div>
              <div class="col-12 col-md-6"><q-select v-model="maintenanceForm.maintenance_type" :options="maintenanceTypeOptions" :label="t('inventory.type')" outlined dense emit-value map-options /></div>
              <div class="col-12 col-md-4" v-if="maintenanceEditing || maintenanceDialogMode === 'task'"><q-select v-model="maintenanceForm.status" :options="maintenanceStatusOptions" :label="t('inventory.status')" outlined dense emit-value map-options /></div>
              <div class="col-12 col-md-4" v-if="maintenanceEditing || maintenanceDialogMode === 'schedule'"><q-select v-model="maintenanceForm.interval_mode" :options="maintenanceIntervalModeOptions" :label="t('inventory.intervalMode')" outlined dense emit-value map-options /></div>
              <div class="col-12 col-md-4" v-if="maintenanceEditing || maintenanceDialogMode === 'schedule'"><q-input v-model.number="maintenanceForm.interval_value" type="number" min="1" :label="maintenanceForm.interval_mode === 'runtime' ? t('inventory.hoursInterval') : t('inventory.daysInterval')" outlined dense /></div>
              <div class="col-12 col-md-4"><q-input v-model="maintenanceForm.scheduled_date" type="date" :label="t('inventory.scheduledDate')" outlined dense /></div>
              <div class="col-12 col-md-4" v-if="maintenanceEditing || maintenanceDialogMode === 'task'"><q-input v-model="maintenanceForm.completed_date" type="date" :label="t('inventory.completedDate')" outlined dense /></div>
              <div class="col-12"><q-input v-model="maintenanceForm.notes" type="textarea" autogrow :label="t('inventory.notes')" outlined dense /></div>
            </div>
            <q-banner v-if="maintenanceDialogError" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ maintenanceDialogError }}</q-banner>
          </q-form>
        </q-card-section>
        <EntityAttachmentsPanel
          entity-type="maintenance"
          :entity-id="maintenanceEditing?.id || null"
          :title="t('inventory.maintenanceDocuments')"
          default-category="maintenance-document"
        />
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="maintenanceDialogOpen = false" />
          <q-btn color="primary" unelevated :label="maintenanceEditing ? t('app.actions.save') : t('users.create')" :loading="saving" @click="saveMaintenance" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="maintenanceScheduleDialogOpen" persistent>
      <q-card style="width: 560px; max-width: 95vw" class="ec-card">
        <q-card-section><div class="text-h6">{{ t('inventory.editMaintenanceSchedule') }}</div></q-card-section>
        <q-card-section class="q-pt-none">
          <q-form ref="maintenanceScheduleFormRef" @submit.prevent="saveMaintenanceSchedule">
            <div class="row q-col-gutter-sm">
              <div class="col-12 col-md-6"><q-select v-model="maintenanceScheduleForm.maintenance_type" :options="maintenanceTypeOptions" :label="t('inventory.type')" outlined dense emit-value map-options /></div>
              <div class="col-12 col-md-6"><q-select v-model="maintenanceScheduleForm.interval_mode" :options="maintenanceIntervalModeOptions" :label="t('inventory.intervalMode')" outlined dense emit-value map-options /></div>
              <div class="col-12 col-md-6"><q-input v-model.number="maintenanceScheduleForm.interval_value" type="number" min="1" :label="maintenanceScheduleForm.interval_mode === 'runtime' ? t('inventory.hoursInterval') : t('inventory.daysInterval')" outlined dense /></div>
              <div class="col-12 col-md-6"><q-input v-model="maintenanceScheduleForm.scheduled_date" type="date" :label="t('inventory.scheduledDate')" outlined dense /></div>
              <div class="col-12"><q-input v-model="maintenanceScheduleForm.notes" type="textarea" autogrow :label="t('inventory.notes')" outlined dense /></div>
            </div>
            <q-banner v-if="maintenanceScheduleDialogError" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ maintenanceScheduleDialogError }}</q-banner>
          </q-form>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="maintenanceScheduleDialogOpen = false" />
          <q-btn color="primary" unelevated :label="t('inventory.saveSchedule')" :loading="saving" @click="saveMaintenanceSchedule" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="maintenanceCompleteDialogOpen" persistent>
      <q-card style="width: 520px; max-width: 95vw" class="ec-card">
        <q-card-section>
          <div class="text-h6">{{ t('inventory.completeMaintenanceTask') }}</div>
          <div class="text-caption text-grey-7" v-if="maintenanceCompleteTarget">
            {{ maintenanceCompleteTarget.asset_tag || t('inventory.noAssetTag') }} · {{ maintenanceCompleteTarget.maintenance_type || t('inventory.maintenance') }}
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <div class="row q-col-gutter-sm">
            <div class="col-12 col-md-6"><q-input v-model="maintenanceCompleteForm.completed_date" type="date" :label="t('inventory.completedDate')" outlined dense /></div>
            <div class="col-12"><q-input v-model="maintenanceCompleteForm.notes" type="textarea" autogrow :label="t('inventory.completionNotes')" outlined dense /></div>
          </div>
          <q-banner v-if="maintenanceCompleteDialogError" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ maintenanceCompleteDialogError }}</q-banner>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="maintenanceCompleteDialogOpen = false" />
          <q-btn color="positive" unelevated :label="t('inventory.complete')" :loading="saving" @click="confirmCompleteMaintenance" />
        </q-card-actions>
      </q-card>
    </q-dialog>



    <q-dialog v-model="bulkProductDialogOpen" persistent>
      <q-card style="width: 560px; max-width: 95vw" class="ec-card">
        <q-card-section><div class="text-h6">{{ t('inventory.bulkEditProducts') }}</div></q-card-section>
        <q-card-section class="q-pt-none">
          <div class="text-caption text-grey-7 q-mb-sm">{{ t('inventory.updatingProductsCount', { count: selectedProducts.length }) }}</div>
          <div class="row q-col-gutter-sm">
            <div class="col-12 col-md-6"><q-select v-model="bulkProductForm.category_id" :options="allCategorySelectOptions" label="Category" outlined dense clearable emit-value map-options /></div>
            <div class="col-12 col-md-6"><q-select v-model="bulkProductForm.product_type" :options="productTypeOptions" label="Type" outlined dense clearable emit-value map-options /></div>
            <div class="col-12 col-md-6">
              <q-select
                v-model="bulkProductForm.brand"
                :options="brandOptions"
                label="Brand"
                outlined
                dense
                clearable
                use-input
                fill-input
                input-debounce="0"
                emit-value
                map-options
                @new-value="onNewBulkBrandValue"
                @update:model-value="onBulkBrandChanged"
              >
                <template #prepend>
                  <q-icon name="storefront" color="grey-6" />
                </template>
              </q-select>
            </div>
            <div class="col-12 col-md-6">
              <q-select
                v-model="bulkProductForm.manufacturer"
                :options="manufacturerOptions"
                label="Manufacturer"
                outlined
                dense
                clearable
                use-input
                fill-input
                input-debounce="0"
                emit-value
                map-options
                @new-value="onNewBulkManufacturerValue"
                @update:model-value="onBulkManufacturerChanged"
              >
                <template #prepend>
                  <q-icon name="factory" color="grey-6" />
                </template>
              </q-select>
            </div>
            <div class="col-12 col-md-6"><q-input v-model.number="bulkProductForm.maintenance_interval_days" type="number" min="1" label="Maintenance interval (days)" outlined dense clearable /></div>
            <div class="col-12 col-md-6">
              <q-input
                v-model.number="bulkProductForm.daily_rate"
                type="number"
                min="0"
                step="0.01"
                label="Daily rate"
                :suffix="activeCurrencyCode"
                :hint="currencyHelperText"
                outlined
                dense
                clearable
              />
            </div>
          </div>
          <q-banner v-if="bulkProductDialogError" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ bulkProductDialogError }}</q-banner>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" @click="bulkProductDialogOpen = false" />
          <q-btn color="primary" unelevated :label="t('inventory.apply')" :loading="saving" @click="saveBulkProducts" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="bulkDeviceDialogOpen" persistent>
      <q-card style="width: 520px; max-width: 95vw" class="ec-card">
        <q-card-section><div class="text-h6">{{ t('inventory.bulkEditDevices') }}</div></q-card-section>
        <q-card-section class="q-pt-none">
          <div class="text-caption text-grey-7 q-mb-sm">{{ t('inventory.updatingDevicesCount', { count: selectedDevices.length }) }}</div>
          <div class="row q-col-gutter-sm">
            <div class="col-12 col-md-4"><q-select v-model="bulkDeviceForm.status" :options="statusOptions" :label="t('inventory.status')" outlined dense clearable emit-value map-options /></div>
            <div class="col-12 col-md-4"><q-select v-model="bulkDeviceForm.condition" :options="conditionOptions" :label="t('inventory.condition')" outlined dense clearable emit-value map-options /></div>
            <div class="col-12 col-md-4"><q-select v-model="bulkDeviceForm.location_zone_id" :options="locationSelectOptions" :label="t('inventory.location')" outlined dense clearable emit-value map-options /></div>
          </div>
          <q-banner v-if="bulkDeviceDialogError" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ bulkDeviceDialogError }}</q-banner>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="bulkDeviceDialogOpen = false" />
          <q-btn color="primary" unelevated :label="t('inventory.apply')" :loading="saving" @click="saveBulkDevices" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="bulkMaintenanceDialogOpen" persistent>
      <q-card style="width: 520px; max-width: 95vw" class="ec-card">
        <q-card-section><div class="text-h6">{{ t('inventory.bulkEditMaintenanceTasks') }}</div></q-card-section>
        <q-card-section class="q-pt-none">
          <div class="text-caption text-grey-7 q-mb-sm">{{ t('inventory.updatingTasksCount', { count: selectedMaintenance.length }) }}</div>
          <div class="row q-col-gutter-sm">
            <div class="col-12 col-md-6"><q-select v-model="bulkMaintenanceForm.status" :options="maintenanceStatusOptions" :label="t('inventory.status')" outlined dense clearable emit-value map-options /></div>
            <div class="col-12 col-md-6"><q-select v-model="bulkMaintenanceForm.maintenance_type" :options="maintenanceTypeOptions" :label="t('inventory.type')" outlined dense clearable emit-value map-options /></div>
            <div class="col-12 col-md-6"><q-input v-model="bulkMaintenanceForm.scheduled_date" type="date" :label="t('inventory.scheduledDate')" outlined dense clearable /></div>
            <div class="col-12 col-md-6"><q-input v-model="bulkMaintenanceForm.completed_date" type="date" :label="t('inventory.completedDate')" outlined dense clearable /></div>
          </div>
          <q-banner v-if="bulkMaintenanceDialogError" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ bulkMaintenanceDialogError }}</q-banner>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="bulkMaintenanceDialogOpen = false" />
          <q-btn color="primary" unelevated :label="t('inventory.apply')" :loading="saving" @click="saveBulkMaintenance" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="bulkScheduleDialogOpen" persistent>
      <q-card style="width: 520px; max-width: 95vw" class="ec-card">
        <q-card-section><div class="text-h6">{{ t('inventory.bulkEditSchedules') }}</div></q-card-section>
        <q-card-section class="q-pt-none">
          <div class="text-caption text-grey-7 q-mb-sm">{{ t('inventory.updatingSchedulesCount', { count: selectedSchedules.length }) }}</div>
          <div class="row q-col-gutter-sm">
            <div class="col-12 col-md-6"><q-select v-model="bulkScheduleForm.maintenance_type" :options="maintenanceTypeOptions" :label="t('inventory.type')" outlined dense clearable emit-value map-options /></div>
            <div class="col-12 col-md-6"><q-select v-model="bulkScheduleForm.interval_mode" :options="maintenanceIntervalModeOptions" :label="t('inventory.intervalMode')" outlined dense clearable emit-value map-options /></div>
            <div class="col-12 col-md-6"><q-input v-model.number="bulkScheduleForm.interval_value" type="number" min="1" :label="bulkScheduleForm.interval_mode === 'runtime' ? t('inventory.hoursInterval') : t('inventory.daysInterval')" outlined dense clearable /></div>
            <div class="col-12 col-md-6"><q-input v-model="bulkScheduleForm.scheduled_date" type="date" :label="t('inventory.scheduledDate')" outlined dense clearable /></div>
            <div class="col-12"><q-input v-model="bulkScheduleForm.notes" type="textarea" autogrow :label="t('inventory.notes')" outlined dense clearable /></div>
          </div>
          <q-banner v-if="bulkScheduleDialogError" class="bg-negative text-white q-mt-sm rounded-borders" dense>{{ bulkScheduleDialogError }}</q-banner>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('app.actions.cancel')" @click="bulkScheduleDialogOpen = false" />
          <q-btn color="primary" unelevated :label="t('inventory.apply')" :loading="saving" @click="saveBulkSchedules" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <DeviceInfoDialog
      v-model="deviceInfoDialogOpen"
      :device="deviceInfoTarget"
      :is-phone="isPhone"
      @edit-device="openDeviceEditorFromLink"
      @edit-product="openProductEditorFromLink"
      @view-device="openDeviceInfoFromLink"
      @open-job="openJobFromLink"
      @report-defect="(id) => openDefectDialog(id)"
      @create-maintenance="(id) => openCreateMaintenance('task', id)"
      @edit-maintenance="openEditMaintenance"
      @complete-maintenance="completeMaintenanceRow"
    />

    <ProductInfoDialog
      v-model="productInfoDialogOpen"
      :product="productInfoTarget"
      @edit-product="openEditProductFromInfo"
      @view-device="openDeviceInfoFromLink"
      @edit-device="openDeviceEditorFromLink"
      @open-job="openJobFromLink"
    />

    <q-dialog v-model="rentalProductInfoDialogOpen" :maximized="isPhone">
      <q-card :style="isPhone ? 'width: 100vw; max-width: 100vw; height: 100vh' : 'min-width: 860px; max-width: 96vw'" class="ec-card">
        <q-card-section>
          <div class="text-h6">Rental Info · {{ rentalProductInfoTarget?.sku || '-' }}</div>
          <div class="text-caption text-grey-7">{{ rentalProductInfoTarget?.name || '-' }}</div>
        </q-card-section>

        <q-card-section class="q-pt-none" :style="isPhone ? 'max-height: calc(100vh - 140px); overflow: auto;' : ''">
          <q-list bordered separator class="rounded-borders q-mb-md">
            <q-item>
              <q-item-section>
                <q-item-label>ID: {{ rentalProductInfoTarget?.id || '-' }} · Supplier: {{ rentalProductInfoTarget?.supplier_name || '-' }}</q-item-label>
                <q-item-label caption>
                  Category: {{ rentalProductInfoTarget?.category || '-' }} · Supplier price: {{ formatMoney(rentalProductInfoTarget?.rental_price) }} · Client price: {{ formatMoney(rentalProductInfoTarget?.daily_rate) }}
                </q-item-label>
                <q-item-label caption>
                  Eventory source: {{ rentalProductInfoTarget?.external_source || '-' }} · Link: {{ eventoryInstanceLabelById(rentalProductInfoTarget?.external_reference) }}
                </q-item-label>
                <q-item-label caption>
                  Eventory available qty: {{ Number(rentalProductInfoTarget?.eventory_available_qty || 0) }}
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-btn
                  flat
                  dense
                  :round="isPhone"
                  color="primary"
                  icon="edit"
                  :label="isPhone ? void 0 : 'Edit'"
                  :aria-label="isPhone ? 'Edit rental product' : void 0"
                  @click="openEditRentalProductFromInfo()"
                />
              </q-item-section>
            </q-item>
          </q-list>

          <div class="text-subtitle2 q-mb-sm">Linked Jobs</div>
          <q-list bordered separator class="rounded-borders q-mb-md">
            <q-item v-for="row in rentalProductInfoJobs" :key="`rental-job-${row.job_id}`">
              <q-item-section>
                <q-item-label>{{ row.job_code || `Job #${row.job_id}` }}</q-item-label>
                <q-item-label caption>
                  Required: {{ row.quantity_required_total }} · Picked: {{ row.quantity_picked_total }}
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-btn
                  flat
                  dense
                  :round="isPhone"
                  color="primary"
                  icon="edit"
                  :label="isPhone ? void 0 : 'Edit'"
                  :aria-label="isPhone ? 'Edit linked job' : void 0"
                  @click="openJobFromLink(row.job_id)"
                />
              </q-item-section>
            </q-item>
            <q-item v-if="!rentalProductInfoJobs.length">
              <q-item-section><q-item-label caption>No linked jobs found for this rental product.</q-item-label></q-item-section>
            </q-item>
          </q-list>

          <EntityAttachmentsPanel
            entity-type="product"
            :entity-id="rentalProductInfoTarget?.id || null"
            title="Rental Documents"
            default-category="rental-document"
            :read-only="true"
          />
        </q-card-section>

        <q-card-actions :align="isPhone ? 'stretch' : 'right'" :class="isPhone ? 'q-pa-md bg-grey-2' : ''">
          <q-space />
          <q-btn flat :class="isPhone ? 'full-width' : ''" label="Close" @click="rentalProductInfoDialogOpen = false" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="productAvailabilityDialogOpen" :maximized="isPhone">
      <q-card :style="isPhone ? 'width: 100vw; max-width: 100vw; height: 100vh' : 'min-width: 860px; max-width: 96vw'" class="ec-card">
        <q-card-section>
          <div class="text-h6">Availability Calendar · {{ productAvailabilityTarget?.sku || '-' }}</div>
          <div class="text-caption text-grey-7">{{ productAvailabilityTarget?.name || '-' }}</div>
        </q-card-section>

        <q-card-section class="q-pt-none" :style="isPhone ? 'max-height: calc(100vh - 140px); overflow: auto;' : ''">
          <div class="row items-center q-col-gutter-sm q-mb-sm">
            <div class="col-auto">
              <q-toggle v-model="productAvailabilityIncludeDrafts" color="primary" label="Include drafts" />
            </div>
            <div class="col-auto">
              <q-select
                v-model="productAvailabilityDays"
                :options="productAvailabilityDaysOptions"
                label="Range"
                outlined
                dense
                emit-value
                map-options
              />
            </div>
          </div>

          <div class="row items-center q-col-gutter-xs q-mb-sm text-caption text-grey-7">
            <div class="col-auto">Heatmap:</div>
            <div class="col-auto"><q-badge color="negative" text-color="white" label="Low / shortage" /></div>
            <div class="col-auto"><q-badge color="warning" text-color="black" label="Tight" /></div>
            <div class="col-auto"><q-badge color="positive" text-color="white" label="Healthy" /></div>
          </div>

          <q-table
            :rows="productAvailabilityCalendarRows"
            :columns="productAvailabilityCalendarColumns"
            row-key="date"
            flat
            bordered
            dense
            :pagination="{ rowsPerPage: 0 }"
            :rows-per-page-options="[0]"
          >
            <template #body-cell-reserved="props">
              <q-td :props="props">
                <div class="text-weight-medium">{{ props.row.reserved }}</div>
              </q-td>
            </template>
            <template #body-cell-available="props">
              <q-td :props="props">
                <div
                  class="availability-heat-cell"
                  :style="productAvailabilityHeatStyle(props.row)"
                  :title="productAvailabilityHeatLabel(props.row)"
                >
                  <span class="availability-heat-value">{{ props.row.available }}</span>
                  <span class="availability-heat-ratio">{{ productAvailabilityPercent(props.row) }}%</span>
                </div>
              </q-td>
            </template>
          </q-table>
        </q-card-section>

        <q-card-actions :align="isPhone ? 'stretch' : 'right'" :class="isPhone ? 'q-pa-md bg-grey-2' : ''">
          <q-space />
          <q-btn flat :class="isPhone ? 'full-width' : ''" label="Close" @click="productAvailabilityDialogOpen = false" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="importDialogOpen" persistent>
      <q-card style="width: 840px; max-width: 98vw" class="ec-card">
        <q-card-section>
          <div class="text-h6">Import Data</div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-12 col-md-4">
              <q-select
                v-model="importEntityType"
                :options="importEntityOptions"
                label="Import to"
                outlined
                dense
                emit-value
                map-options
                @update:model-value="onImportEntityChanged"
              />
            </div>
            <div class="col-12 col-md-8">
              <q-file
                v-model="importFile"
                label="JSON or CSV file"
                outlined
                dense
                accept=".json,.csv,application/json,text/csv"
                @update:model-value="parseImportFile"
              />
            </div>
          </div>

          <q-banner v-if="importDialogError" class="bg-negative text-white q-mb-sm rounded-borders" dense>
            {{ importDialogError }}
          </q-banner>

          <div v-if="importRows.length" class="q-mb-sm text-caption text-grey-7">
            Parsed {{ importRows.length }} records. Map Stockwire fields to source fields below.
          </div>

          <q-table
            :rows="mappingRows"
            :columns="mappingColumns"
            row-key="targetField"
            flat
            bordered
            dense
            class="q-mb-sm"
          >
            <template #body-cell-sourceKey="props">
              <q-td :props="props">
                <q-select
                  v-model="importMapping[props.row.targetField]"
                  :options="importSourceKeyOptions"
                  outlined
                  dense
                  clearable
                  emit-value
                  map-options
                />
              </q-td>
            </template>
            <template #body-cell-required="props">
              <q-td :props="props">
                <q-badge :label="props.row.required ? 'Required' : 'Optional'" :color="props.row.required ? 'negative' : 'grey'" />
              </q-td>
            </template>
          </q-table>

          <div class="q-mb-sm row items-center q-gutter-sm">
            <div class="col-auto">
              <q-btn size="sm" flat label="Load HireHop preset" @click="loadHirehopPreset" />
            </div>
            <div class="col-auto">
              <q-toggle dense v-model="importUseServer" label="Use server import" />
            </div>
            <div class="col-auto">
              <q-toggle dense v-model="updateExistingDevices" label="Update existing devices" />
            </div>
          </div>

          <div class="text-caption text-grey-7 q-mb-md">
            HireHop imports require server import for serial numbers, barcodes, quantity expansion, and device metadata. This is enabled automatically when a HireHop file or preset is detected.
          </div>

          <div v-if="importPreviewRows.length" class="q-mt-md">
            <div class="text-subtitle2 q-mb-xs">Preview (first 10 transformed rows)</div>
            <q-table
              :rows="importPreviewRows"
              :columns="importPreviewColumns"
              row-key="_preview_id"
              flat
              bordered
              dense
            >
              <template #body-cell-_status="props">
                <q-td :props="props">
                  <q-badge
                    :label="props.row._error ? 'Invalid' : 'Valid'"
                    :color="props.row._error ? 'negative' : 'positive'"
                  />
                  <div v-if="props.row._error" class="text-caption text-negative q-mt-xs">{{ props.row._error }}</div>
                </q-td>
              </template>
            </q-table>
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" @click="importDialogOpen = false" />
          <q-btn color="primary" unelevated label="Run Import" :loading="importing" @click="runJsonImport" />
        </q-card-actions>
      </q-card>
    </q-dialog>
    <DefectReportDialog
      v-model="defectDialogOpen"
      :device-id="selectedDeviceId"
    />
  </q-page>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import { DEVICE_STATUSES, useInventoryStore } from '../stores/inventory'
import { useCustomFieldsStore } from '../stores/customFields'
import { useJobsStore } from '../stores/jobs'
import { useSettingsStore } from '../stores/settings'
import { useCompactGrid } from '../composables/useCompactGrid'
import EntityAttachmentsPanel from '../components/EntityAttachmentsPanel.vue'
import ProductDialog from '../components/ProductDialog.vue'
import ProductInfoDialog from '../components/ProductInfoDialog.vue'
import DeviceDialog from '../components/DeviceDialog.vue'
import DeviceInfoDialog from '../components/DeviceInfoDialog.vue'
import { translateMaybePrefillCustomFieldLabel, translateMaybePrefillCustomFieldOption } from '../i18n/prefillContent'
import { normalizeCurrencyCode } from '../constants/currencies'
import { collectImportSourceKeys, convertDimensionValueToCm, getImportValueBySourceKey, parseImportRows, resolveImportEntityType } from '../utils/import-data'
import {
  countCategoryOverview,
  countPendingMaintenance,
  findMostUsedDevice,
  findMostUsedProductByUsageDays,
  isRentalProduct
} from '../utils/inventory-overview'
import { slugify } from 'src/utils/slugify'
import { api } from '../boot/axios'
import DefectReportDialog from 'components/DefectReportDialog.vue'

const $q = useQuasar()
const { t } = useI18n()
const isPhone = computed(() => $q.screen.lt.md)
const productActionColor = computed(() => ($q.dark.isActive ? 'green-4' : 'secondary'))
const infoActionColor = computed(() => ($q.dark.isActive ? 'teal-4' : 'secondary'))
const calendarActionColor = computed(() => ($q.dark.isActive ? 'light-green-4' : 'secondary'))
const bulkPrintActionColor = computed(() => ($q.dark.isActive ? 'amber-5' : 'accent'))
const bulkPrintActionTextColor = computed(() => ($q.dark.isActive ? 'black' : 'white'))
const route = useRoute()
const router = useRouter()
const store = useInventoryStore()
const customFieldsStore = useCustomFieldsStore()
const jobsStore = useJobsStore()
const settingsStore = useSettingsStore()
const compactGrid = useCompactGrid(1024)
const activeCurrencyCode = computed(() => normalizeCurrencyCode(settingsStore.companyProfile?.currency, 'SEK'))
const currencyHelperText = computed(() => `${t('settings.company.currencyIso')}: ${activeCurrencyCode.value}`)

const tab = ref('products')
const saving = ref(false)
const showCachedOfflineBanner = computed(() => (
  store.fetchSource === 'snapshot' || jobsStore.fetchSource === 'snapshot'
))

const RETURN_INFO_STORAGE_KEY = 'inventory.return-info.v1'
const ZONE_CODE_MAX_LENGTH = 50

const defectDialogOpen = ref(false)
const selectedDeviceId = ref(null)

function openDefectDialog(deviceId) {
  selectedDeviceId.value = deviceId
  defectDialogOpen.value = true
}

function customFieldLabel(label) {
  return translateMaybePrefillCustomFieldLabel(label, t)
}

function customFieldOption(option) {
  return translateMaybePrefillCustomFieldOption(option, t)
}

const productSearch = ref('')
const productCategoryFilter = ref(null)
const productTypeFilter = ref(null)
const productBrandFilter = ref(null)
const productManufacturerFilter = ref(null)
const productSort = ref('name_asc')
const deviceSearch = ref('')
const maintenanceSearch = ref('')
const scheduleSearch = ref('')
const selectedProducts = ref([])
const selectedDevices = ref([])
const selectedLocationIds = ref([])
const selectedMaintenance = ref([])
const selectedSchedules = ref([])
const rentalProductSearch = ref('')
const rentalProductSupplierFilter = ref(null)
const rentalProductSyncFilter = ref('all')
const rentalProductSort = ref('name_asc')
const rentalProductSaving = ref(false)
const rentalProductDraft = ref(emptyRentalProductDraft())
const rentalProductDialogOpen = ref(false)
const rentalProductDialogError = ref('')
const rentalProductFormRef = ref(null)
const rentalGeneralExpanded = ref(true)
const rentalPricingExpanded = ref(true)
const rentalCustomFieldsExpanded = ref(false)
const rentalProductFieldRows = ref([])

const bulkProductDialogOpen = ref(false)
const bulkProductDialogError = ref('')
const bulkProductForm = ref({
  category_id: null,
  product_type: null,
  brand: '',
  manufacturer: '',
  maintenance_interval_days: null,
  daily_rate: null,
})

const bulkDeviceDialogOpen = ref(false)
const bulkDeviceDialogError = ref('')
const bulkDeviceForm = ref({
  status: null,
  condition: null,
  location_zone_id: null,
})

const bulkMaintenanceDialogOpen = ref(false)
const bulkMaintenanceDialogError = ref('')
const bulkMaintenanceForm = ref({
  status: null,
  maintenance_type: null,
  scheduled_date: '',
  completed_date: '',
})

const bulkScheduleDialogOpen = ref(false)
const bulkScheduleDialogError = ref('')
const bulkScheduleForm = ref({
  maintenance_type: null,
  interval_mode: null,
  interval_value: null,
  scheduled_date: '',
  notes: '',
})

const booleanValueOptions = [
  { label: t('common.true'), value: 'true' },
  { label: t('common.false'), value: 'false' },
]

const productTypeOptions = [
  { label: t('inventory.productTypeEquipment'), value: 'equipment' },
  { label: t('inventory.productTypeAccessory'), value: 'accessory' },
  { label: t('inventory.productTypeConsumable'), value: 'consumable' },
  { label: t('inventory.productTypeCase'), value: 'case' },
]

const statusOptions = DEVICE_STATUSES.map(item => ({ label: item.label, value: item.value }))
const conditionOptions = [
  { label: t('inventory.conditionExcellent'), value: 'excellent' },
  { label: t('inventory.conditionGood'), value: 'good' },
  { label: t('inventory.conditionFair'), value: 'fair' },
  { label: t('inventory.conditionDamaged'), value: 'damaged' },
]

const maintenanceStatusOptions = [
  { label: t('inventory.maintenanceStatusScheduled'), value: 'scheduled' },
  { label: t('inventory.maintenanceStatusInProgress'), value: 'in_progress' },
  { label: t('inventory.maintenanceStatusCompleted'), value: 'completed' },
  { label: t('inventory.maintenanceStatusCanceled'), value: 'canceled' },
]

const maintenanceTypeOptions = [
  { label: t('inventory.maintenanceTypeInspection'), value: 'inspection' },
  { label: t('inventory.maintenanceTypeCleaning'), value: 'cleaning' },
  { label: t('inventory.maintenanceTypeRepair'), value: 'repair' },
  { label: t('inventory.maintenanceTypeCalibration'), value: 'calibration' },
  { label: t('inventory.maintenanceTypePatTest'), value: 'pat_test' },
  { label: t('inventory.maintenanceTypeScheduled'), value: 'scheduled' },
]

const maintenanceIntervalModeOptions = [
  { label: t('inventory.calendarTime'), value: 'calendar' },
  { label: t('inventory.runtimeHours'), value: 'runtime' },
]

const productColumns = [
  { name: 'sku', label: t('inventory.columnSku'), field: 'sku', sortable: true, align: 'left' },
  { name: 'name', label: t('inventory.columnName'), field: 'name', sortable: true, align: 'left' },
  { name: 'brand', label: t('inventory.columnBrand'), field: 'brand', sortable: true, align: 'left' },
  { name: 'manufacturer', label: t('inventory.columnManufacturer'), field: 'manufacturer', sortable: true, align: 'left' },
  { name: 'availability_now', label: t('inventory.columnAvailability'), field: 'availability_now', sortable: false, align: 'left' },
  { name: 'product_type', label: t('inventory.columnType'), field: 'product_type', sortable: true, align: 'left' },
  { name: 'category', label: t('inventory.columnCategory'), field: 'category', sortable: true, align: 'left' },
  { name: 'in_store_devices', label: t('inventory.columnInStore'), field: 'in_store_devices', sortable: true, align: 'left' },
  { name: 'on_site_devices', label: t('inventory.columnOnSite'), field: 'on_site_devices', sortable: true, align: 'left' },
  { name: 'damaged_devices', label: t('inventory.columnDamaged'), field: 'damaged_devices', sortable: true, align: 'left' },
  { name: 'total_devices', label: t('inventory.columnTotal'), field: 'total_devices', sortable: true, align: 'left' },
  { name: 'daily_rate', label: t('inventory.columnDailyRate'), field: 'daily_rate', sortable: true, align: 'left' },
  { name: 'replace_cost', label: t('inventory.columnReplaceCost'), field: 'replace_cost', sortable: true, align: 'left' },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
]

const rentalProductColumns = [
  { name: 'sku', label: t('inventory.columnSku'), field: 'sku', sortable: true, align: 'left' },
  { name: 'name', label: t('inventory.columnName'), field: 'name', sortable: true, align: 'left' },
  { name: 'category', label: t('inventory.columnCategory'), field: 'category', sortable: true, align: 'left' },
  { name: 'supplier_name', label: t('inventory.columnSupplier'), field: 'supplier_name', sortable: true, align: 'left' },
  { name: 'eventory_available_qty', label: t('inventory.columnQty'), field: 'eventory_available_qty', sortable: true, align: 'right' },
  { name: 'rental_price', label: t('inventory.columnSupplierPrice'), field: 'rental_price', sortable: true, align: 'right' },
  { name: 'daily_rate', label: t('inventory.columnClientPrice'), field: 'daily_rate', sortable: true, align: 'right' },
  { name: 'external_reference', label: t('inventory.columnEventoryLink'), field: 'external_reference', sortable: false, align: 'left' },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
]

const rentalSyncFilterOptions = [
  { label: t('inventory.filterAll'), value: 'all' },
  { label: t('inventory.filterSyncedOnly'), value: 'synced' },
  { label: t('inventory.filterManualOnly'), value: 'manual' },
]

const rentalProductSortOptions = [
  { label: t('inventory.sortNameAsc'), value: 'name_asc' },
  { label: t('inventory.sortNameDesc'), value: 'name_desc' },
  { label: t('inventory.sortSkuAsc'), value: 'sku_asc' },
  { label: t('inventory.sortSkuDesc'), value: 'sku_desc' },
  { label: t('inventory.sortSupplierPriceDesc'), value: 'supplier_price_desc' },
  { label: t('inventory.sortSupplierPriceAsc'), value: 'supplier_price_asc' },
  { label: t('inventory.sortClientPriceDesc'), value: 'client_price_desc' },
  { label: t('inventory.sortClientPriceAsc'), value: 'client_price_asc' },
]

const productSortOptions = [
  { label: t('inventory.sortNameAsc'), value: 'name_asc' },
  { label: t('inventory.sortNameDesc'), value: 'name_desc' },
  { label: t('inventory.sortSkuAsc'), value: 'sku_asc' },
  { label: t('inventory.sortSkuDesc'), value: 'sku_desc' },
  { label: t('inventory.sortAvailabilityDesc'), value: 'available_desc' },
  { label: t('inventory.sortAvailabilityAsc'), value: 'available_asc' },
  { label: t('inventory.sortTotalDesc'), value: 'total_desc' },
]

const productAvailabilityDaysOptions = [
  { label: t('inventory.daysCount', { count: 30 }), value: 30 },
  { label: t('inventory.daysCount', { count: 60 }), value: 60 },
  { label: t('inventory.daysCount', { count: 90 }), value: 90 },
]

const productAvailabilityCalendarColumns = [
  { name: 'date', label: t('inventory.columnDate'), field: 'date', align: 'left' },
  { name: 'weekday', label: t('inventory.columnDay'), field: 'weekday', align: 'left' },
  { name: 'reserved', label: t('inventory.columnReserved'), field: 'reserved', align: 'left' },
  { name: 'available', label: t('inventory.columnAvailable'), field: 'available', align: 'left' },
]

const deviceColumns = [
  { name: 'asset_tag', label: t('inventory.columnAssetTag'), field: 'asset_tag', sortable: true, align: 'left' },
  { name: 'serial_number', label: t('inventory.columnSerial'), field: 'serial_number', sortable: true, align: 'left' },
  { name: 'status', label: t('inventory.columnStatus'), field: 'status', sortable: true, align: 'left' },
  { name: 'condition', label: t('inventory.columnCondition'), field: 'condition', sortable: true, align: 'left' },
  { name: 'current_job_code', label: t('inventory.columnCurrentJob'), field: 'current_job_code', sortable: true, align: 'left' },
  { name: 'location_zone_id', label: t('inventory.columnLocation'), field: 'location_zone_id', sortable: true, align: 'left' },
  { name: 'usage_hours', label: t('inventory.columnHours'), field: 'usage_hours', sortable: true, align: 'left' },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
]

const maintenanceColumns = [
  { name: 'asset_tag', label: t('inventory.columnAssetTag'), field: 'asset_tag', sortable: true, align: 'left' },
  { name: 'product_name', label: t('inventory.columnProduct'), field: 'product_name', sortable: true, align: 'left' },
  { name: 'maintenance_type', label: t('inventory.columnType'), field: 'maintenance_type', sortable: true, align: 'left' },
  { name: 'source', label: t('inventory.columnSource'), field: row => maintenanceSourceLabel(row), sortable: false, align: 'left' },
  { name: 'status', label: t('inventory.columnStatus'), field: 'status', sortable: true, align: 'left' },
  { name: 'scheduled_date', label: t('inventory.columnScheduled'), field: 'scheduled_date', sortable: true, align: 'left' },
  { name: 'completed_date', label: t('inventory.columnCompleted'), field: 'completed_date', sortable: true, align: 'left' },
  { name: 'notes', label: t('inventory.columnNotes'), field: 'notes', sortable: false, align: 'left' },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
]

const scheduleColumns = [
  { name: 'id', label: t('inventory.columnId'), field: 'id', sortable: true, align: 'left' },
  { name: 'maintenance_type', label: t('inventory.columnType'), field: 'maintenance_type', sortable: true, align: 'left' },
  { name: 'interval', label: t('inventory.columnInterval'), field: row => scheduleIntervalLabel(row), sortable: false, align: 'left' },
  { name: 'scheduled_date', label: t('inventory.columnScheduled'), field: 'scheduled_date', sortable: true, align: 'left' },
  { name: 'task_count', label: t('inventory.columnLinkedTasks'), field: row => scheduleTaskCount(row.id), sortable: false, align: 'left' },
  { name: 'notes', label: t('inventory.columnNotes'), field: 'notes', sortable: false, align: 'left' },
  { name: 'updated_at', label: t('inventory.columnUpdated'), field: 'updated_at', sortable: true, align: 'left' },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
]

const filteredProducts = computed(() => {
  const needle = productSearch.value.trim().toLowerCase()
  const rows = store.products.filter(product => {
    if (isRentalProduct(product)) return false
    if (productCategoryFilter.value && String(product.category || '') !== String(productCategoryFilter.value)) return false
    if (productTypeFilter.value && String(product.product_type || '') !== String(productTypeFilter.value)) return false
    if (productBrandFilter.value && String(product.brand || '') !== String(productBrandFilter.value)) return false
    if (productManufacturerFilter.value && String(product.manufacturer || '') !== String(productManufacturerFilter.value)) return false
    if (!needle) return true
    return [product.sku, product.name, product.brand, product.manufacturer, product.category]
      .filter(Boolean)
      .some(value => String(value).toLowerCase().includes(needle))
  })

  return [...rows].sort((a, b) => {
    const sortMode = productSort.value
    const skuA = String(a.sku || '').toLowerCase()
    const skuB = String(b.sku || '').toLowerCase()
    const nameA = String(a.name || '').toLowerCase()
    const nameB = String(b.name || '').toLowerCase()
    const availA = productAvailableNow(a.id)
    const availB = productAvailableNow(b.id)
    const totalA = Number(a.total_devices || 0)
    const totalB = Number(b.total_devices || 0)

    if (sortMode === 'sku_desc') return skuB.localeCompare(skuA)
    if (sortMode === 'name_asc') return nameA.localeCompare(nameB)
    if (sortMode === 'name_desc') return nameB.localeCompare(nameA)
    if (sortMode === 'available_desc') return availB - availA || nameA.localeCompare(nameB)
    if (sortMode === 'available_asc') return availA - availB || nameA.localeCompare(nameB)
    if (sortMode === 'total_desc') return totalB - totalA || nameA.localeCompare(nameB)
    return skuA.localeCompare(skuB)
  })
})

const rentalProducts = computed(() =>
  (store.products || []).filter(product => isRentalProduct(product))
)

const inventoryProductCount = computed(() => (store.products || []).filter(product => !isRentalProduct(product)).length)
const categoryOverviewCount = computed(() => countCategoryOverview(store.categories, store.categoryTree))
const overviewMaintenancePendingCount = computed(() => countPendingMaintenance(store.maintenances))
const overviewMostUsedDeviceLabel = computed(() => {
  const device = findMostUsedDevice(store.devices)
  if (!device) return t('inventory.overview.noUsageData')
  const assetTag = device.asset_tag || t('inventory.overview.unknownDevice')
  return `${assetTag} (${device.usage_hours}h)`
})
const overviewMostUsedProductByUsageDaysLabel = computed(() => {
  const usage = findMostUsedProductByUsageDays(store.products, jobsStore.requirements, jobsStore.jobs)
  if (!usage) return t('inventory.overview.noProductUsageData')
  const productName = usage.product?.name || t('inventory.overview.unknownProduct')
  return `${productName} (${usage.usage_days} ${t('inventory.overview.days')})`
})

const rentalSupplierOptions = computed(() => {
  const values = [...new Set(rentalProducts.value.map(item => String(item.supplier_name || '').trim()).filter(Boolean))]
  return values.sort((a, b) => a.localeCompare(b)).map(value => ({ label: value, value }))
})

const filteredRentalProducts = computed(() => {
  const needle = rentalProductSearch.value.trim().toLowerCase()
  const rows = rentalProducts.value.filter(product => {
    if (rentalProductSupplierFilter.value && String(product.supplier_name || '') !== String(rentalProductSupplierFilter.value)) return false
    if (rentalProductSyncFilter.value === 'synced' && !isSyncedEventoryProduct(product)) return false
    if (rentalProductSyncFilter.value === 'manual' && isSyncedEventoryProduct(product)) return false
    if (!needle) return true
    return [product.sku, product.name, product.category, product.supplier_name, product.external_reference]
      .filter(Boolean)
      .some(value => String(value).toLowerCase().includes(needle))
  })

  return [...rows].sort((a, b) => {
    const mode = rentalProductSort.value
    const nameA = String(a.name || '').toLowerCase()
    const nameB = String(b.name || '').toLowerCase()
    const skuA = String(a.sku || '').toLowerCase()
    const skuB = String(b.sku || '').toLowerCase()
    const supplierA = Number(a.rental_price || 0)
    const supplierB = Number(b.rental_price || 0)
    const clientA = Number(a.daily_rate || 0)
    const clientB = Number(b.daily_rate || 0)

    if (mode === 'name_desc') return nameB.localeCompare(nameA)
    if (mode === 'sku_asc') return skuA.localeCompare(skuB)
    if (mode === 'sku_desc') return skuB.localeCompare(skuA)
    if (mode === 'supplier_price_desc') return supplierB - supplierA || nameA.localeCompare(nameB)
    if (mode === 'supplier_price_asc') return supplierA - supplierB || nameA.localeCompare(nameB)
    if (mode === 'client_price_desc') return clientB - clientA || nameA.localeCompare(nameB)
    if (mode === 'client_price_asc') return clientA - clientB || nameA.localeCompare(nameB)
    return nameA.localeCompare(nameB)
  })
})

const isCurrentRentalDraftSynced = computed(() => isSyncedEventoryProduct(rentalProductDraft.value))

function roundMoney(value) {
  return Math.round(Number(value || 0) * 100) / 100
}

function findEventoryInstanceById(instanceId) {
  const key = String(instanceId || '').trim()
  if (!key) return null
  return (settingsStore.integrations?.eventory_instances || []).find(instance => String(instance.id || '').trim() === key) || null
}

function eventoryInstanceLabelById(instanceId) {
  const linked = findEventoryInstanceById(instanceId)
  if (!linked) return instanceId || 'Unknown'
  return linked.name || linked.id
}

function isSyncedEventoryProduct(product) {
  const source = String(product?.external_source || '').trim().toLowerCase()
  const hasExternalReference = !!String(product?.external_reference || '').trim()
  return hasExternalReference && (!source || source === 'eventory')
}

function applyRentalClientPriceFromMargin() {
  const linkedInstance = findEventoryInstanceById(rentalProductDraft.value.external_reference)
  if (!linkedInstance) return

  const supplierPrice = Math.max(0, Number(rentalProductDraft.value.rental_price || 0))
  const marginPercent = Math.max(0, Number(linkedInstance.price_margin_percent || 0))
  const clientPrice = supplierPrice * (1 + (marginPercent / 100))
  rentalProductDraft.value.daily_rate = roundMoney(clientPrice)

  if (!String(rentalProductDraft.value.supplier_name || '').trim() && String(linkedInstance.supplier_name || '').trim()) {
    rentalProductDraft.value.supplier_name = String(linkedInstance.supplier_name).trim()
  }
}

function onRentalSupplierPriceChanged() {
  applyRentalClientPriceFromMargin()
}

function createEmptyRentalProductFieldRows() {
  const defs = (customFieldsStore.definitions || []).filter(def => def.entity_type === 'product' && def.is_active !== false)
  return defs.map(def => ({
    field_definition_id: def.id,
    label: def.label,
    value_type: def.value_type,
    options: def.options || [],
    value: null,
  }))
}

async function loadRentalProductFieldRows(entityId) {
  if (!entityId) {
    rentalProductFieldRows.value = createEmptyRentalProductFieldRows()
    return
  }
  try {
    const data = await customFieldsStore.fetchEntityValues('product', entityId)
    rentalProductFieldRows.value = Array.isArray(data?.values) ? data.values.map(value => ({ ...value })) : createEmptyRentalProductFieldRows()
  } catch {
    rentalProductFieldRows.value = createEmptyRentalProductFieldRows()
  }
}

function emptyRentalProductDraft() {
  return {
    id: null,
    sku: '',
    name: '',
    category: '',
    supplier_name: '',
    rental_price: 0,
    daily_rate: 0,
    replace_cost: 0,
    external_reference: null,
  }
}

function resetRentalProductDraft() {
  rentalProductDraft.value = emptyRentalProductDraft()
}

async function openCreateRentalProduct() {
  resetRentalProductDraft()
  await loadRentalProductFieldRows(null)
  rentalProductDialogError.value = ''
  rentalGeneralExpanded.value = true
  rentalPricingExpanded.value = true
  rentalCustomFieldsExpanded.value = !isPhone.value
  rentalProductDialogOpen.value = true
}

async function openEditRentalProduct(product) {
  rentalProductDraft.value = {
    id: product.id,
    sku: product.sku || '',
    name: product.name || '',
    category: product.category || '',
    supplier_name: product.supplier_name || '',
    rental_price: Number(product.rental_price || 0),
    daily_rate: Number(product.daily_rate || 0),
    replace_cost: Number(product.replace_cost || 0),
    external_reference: product.external_reference || null,
  }
  await loadRentalProductFieldRows(product.id)
  rentalProductDialogError.value = ''
  rentalGeneralExpanded.value = true
  rentalPricingExpanded.value = true
  rentalCustomFieldsExpanded.value = !isPhone.value
  rentalProductDialogOpen.value = true
}

async function saveRentalProduct() {
  const valid = await rentalProductFormRef.value?.validate()
  if (!valid) return

  if (!rentalProductDraft.value.sku.trim() || !rentalProductDraft.value.name.trim()) {
    rentalProductDialogError.value = 'SKU and name are required'
    return
  }

  rentalProductSaving.value = true
  rentalProductDialogError.value = ''
  try {
    const keepSyncedLink = isSyncedEventoryProduct(rentalProductDraft.value)
    const payload = {
      sku: rentalProductDraft.value.sku.trim(),
      name: rentalProductDraft.value.name.trim(),
      category: rentalProductDraft.value.category || null,
      supplier_name: rentalProductDraft.value.supplier_name || null,
      rental_price: Number(rentalProductDraft.value.rental_price || 0),
      daily_rate: Number(rentalProductDraft.value.daily_rate || 0),
      product_type: 'rental',
      is_rental_product: true,
      external_source: keepSyncedLink ? 'eventory' : null,
      external_reference: keepSyncedLink ? rentalProductDraft.value.external_reference : null,
      replace_cost: Number(rentalProductDraft.value.replace_cost || 0),
    }

    let savedProduct
    if (rentalProductDraft.value.id) {
      savedProduct = await store.updateProduct(rentalProductDraft.value.id, payload)
      $q.notify({ type: 'positive', message: t('inventory.rentalProductUpdated') })
    } else {
      savedProduct = await store.createProduct(payload)
      $q.notify({ type: 'positive', message: t('inventory.rentalProductCreated') })
    }

    await customFieldsStore.saveEntityValues('product', savedProduct.id, rentalProductFieldRows.value.map(row => ({
      field_definition_id: row.field_definition_id,
      value: row.value,
    })))

    resetRentalProductDraft()
    rentalProductDialogOpen.value = false
  } catch (error) {
    rentalProductDialogError.value = error?.response?.data?.detail || t('inventory.failedSaveRentalProduct')
  } finally {
    rentalProductSaving.value = false
  }
}

const productCategoryOptions = computed(() => {
  const values = [...new Set(store.products.map(item => String(item.category || '').trim()).filter(Boolean))]
  return values.sort((a, b) => a.localeCompare(b)).map(value => ({ label: value, value }))
})

const productBrandOptions = computed(() => {
  const values = [...new Set(store.products.map(item => String(item.brand || '').trim()).filter(Boolean))]
  return values.sort((a, b) => a.localeCompare(b)).map(value => ({ label: value, value }))
})

const productManufacturerOptions = computed(() => {
  const values = [...new Set(store.products.map(item => String(item.manufacturer || '').trim()).filter(Boolean))]
  return values.sort((a, b) => a.localeCompare(b)).map(value => ({ label: value, value }))
})

const productAvailabilityById = computed(() => {
  const byId = new Map()
  for (const device of store.devices || []) {
    const productId = device.product_id
    if (!byId.has(productId)) {
      byId.set(productId, {
        available: 0,
        reserved: 0,
        in_use: 0,
        maintenance: 0,
        damaged: 0,
        total: 0,
      })
    }
    const counters = byId.get(productId)
    counters.total += 1

    const condition = String(device.condition || '').toLowerCase()
    const status = String(device.status || '').toLowerCase()

    if (condition === 'damaged') counters.damaged += 1
    if (status === 'available' && condition !== 'damaged') counters.available += 1
    if (status === 'reserved') counters.reserved += 1
    if (status === 'in_use') counters.in_use += 1
    if (status === 'maintenance') counters.maintenance += 1
  }
  return byId
})

function productAvailableNow(productId) {
  return Number(productAvailabilityById.value.get(productId)?.available || 0)
}

const productAvailabilityDialogOpen = ref(false)
const productAvailabilityTarget = ref(null)
const productAvailabilityIncludeDrafts = ref(false)
const productAvailabilityDays = ref(60)

const productAvailabilityCalendarRows = computed(() => {
  if (!productAvailabilityTarget.value) return []

  const today = new Date()
  const isRental = String(productAvailabilityTarget.value?.product_type || '').toLowerCase() === 'rental'
    || productAvailabilityTarget.value?.is_rental_product
  const baseOperational = isRental
    ? Math.max(0, Number(productAvailabilityTarget.value?.eventory_available_qty || 0))
    : (store.devices || []).filter(device => {
      if (device.product_id !== productAvailabilityTarget.value.id) return false
      const condition = String(device.condition || '').toLowerCase()
      const status = String(device.status || '').toLowerCase()
      const retired = device.retire_date ? new Date(device.retire_date) <= today : false
      if (retired) return false
      if (condition === 'damaged') return false
      if (status === 'maintenance') return false
      return true
    }).length

  const reservingStatuses = productAvailabilityIncludeDrafts.value
    ? new Set(['draft', 'confirmed', 'in_progress'])
    : new Set(['confirmed', 'in_progress'])

  const jobsById = new Map((jobsStore.jobs || []).map(job => [job.id, job]))
  const requirements = (jobsStore.requirements || []).filter(req => req.product_id === productAvailabilityTarget.value.id)
  const rows = []

  for (let i = 0; i < Number(productAvailabilityDays.value || 60); i += 1) {
    const date = new Date(today)
    date.setDate(today.getDate() + i)
    const dateYmd = toYmd(date)

    let reserved = 0
    let externalReserved = 0
    for (const req of requirements) {
      const job = jobsById.get(req.job_id)
      if (!job) continue
      if (!reservingStatuses.has(String(job.status || '').toLowerCase())) continue
      const start = normalizeYmd(job.start_date)
      const end = normalizeYmd(job.end_date)
      if (!start || !end) continue
      if (dateYmd < start || dateYmd > end) continue
      reserved += Math.max(Number(req.quantity_required || 0), Number(req.quantity_picked || 0))
    }

    if (isRental) {
      for (const packlist of eventoryPacklistsForDate(productAvailabilityTarget.value, dateYmd)) {
        externalReserved += Math.max(Number(packlist?.quantity || 0), Number(packlist?.out || 0), 0)
      }
    }

    const totalReserved = reserved + externalReserved

    rows.push({
      date: dateYmd,
      weekday: date.toLocaleDateString(undefined, { weekday: 'short' }),
      reserved: totalReserved,
      available: Math.max(baseOperational - totalReserved, 0),
      total_operational: baseOperational,
    })
  }

  return rows
})

function eventoryPacklistsForDate(product, dateYmd) {
  if (!Array.isArray(product?.eventory_packlists)) return []
  return product.eventory_packlists.filter(packlist => {
    if (!packlist || typeof packlist !== 'object') return false
    const status = String(packlist?.job_status || '').toLowerCase()
    if (status && ['cancelled', 'canceled', 'completed', 'returned'].includes(status)) return false
    const start = normalizeYmd(packlist?.start_date)
    const end = normalizeYmd(packlist?.end_date)
    if (!start || !end) return false
    return !(dateYmd < start || dateYmd > end)
  })
}

function normalizeYmd(value) {
  if (!value) return ''
  return String(value).slice(0, 10)
}

function toYmd(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

function productAvailabilityPercent(row) {
  const total = Math.max(Number(row?.total_operational || 0), 0)
  const available = Math.max(Number(row?.available || 0), 0)
  if (!total) return available > 0 ? 100 : 0
  return Math.round((available / total) * 100)
}

function productAvailabilityHeat(row) {
  const total = Math.max(Number(row?.total_operational || 0), 0)
  const available = Math.max(Number(row?.available || 0), 0)
  const reserved = Math.max(Number(row?.reserved || 0), 0)

  if (total <= 0) {
    if (reserved > 0) return { rgb: '220, 53, 69', alpha: 0.34, level: 'Low / shortage' }
    return { rgb: '245, 124, 0', alpha: 0.2, level: 'Tight' }
  }

  const availabilityRatio = available / total
  const utilization = clamp(reserved / total, 0, 1.6)

  if (availabilityRatio <= 0.25) {
    return { rgb: '220, 53, 69', alpha: 0.18 + (utilization * 0.18), level: 'Low / shortage' }
  }
  if (availabilityRatio <= 0.55) {
    return { rgb: '245, 124, 0', alpha: 0.14 + (utilization * 0.14), level: 'Tight' }
  }
  return { rgb: '46, 125, 50', alpha: 0.12 + ((1 - availabilityRatio) * 0.16), level: 'Healthy' }
}

function productAvailabilityHeatStyle(row) {
  const heat = productAvailabilityHeat(row)
  return {
    backgroundColor: `rgba(${heat.rgb}, ${clamp(heat.alpha, 0.1, 0.42).toFixed(3)})`,
    border: `1px solid rgba(${heat.rgb}, 0.35)`,
  }
}

function productAvailabilityHeatLabel(row) {
  const heat = productAvailabilityHeat(row)
  const pct = productAvailabilityPercent(row)
  return `${heat.level} • ${pct}% available (${row.available}/${row.total_operational})`
}

function openProductAvailabilityCalendar(product) {
  productAvailabilityTarget.value = product
  productAvailabilityDialogOpen.value = true
}

const filteredDevices = computed(() => {
  const needle = deviceSearch.value.trim().toLowerCase()
  if (!needle) return store.devices
  return store.devices.filter(device =>
    [device.asset_tag, device.serial_number, device.status, device.condition, device.barcode, device.rfid, device.current_job_code]
      .filter(Boolean)
      .some(value => String(value).toLowerCase().includes(needle))
  )
})

const deviceInfoDialogOpen = ref(false)
const deviceInfoTarget = ref(null)
const pendingInfoReturn = ref(null)

const productInfoDialogOpen = ref(false)
const productInfoTarget = ref(null)

const rentalProductInfoDialogOpen = ref(false)
const rentalProductInfoTarget = ref(null)

const rentalProductInfoJobs = computed(() => linkedJobsForProductId(rentalProductInfoTarget.value?.id))

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

function linkedJobsForProductId(productId) {
  const targetId = Number(productId || 0)
  if (!targetId) return []

  const jobsById = new Map((jobsStore.jobs || []).map(job => [job.id, job]))
  const bucket = new Map()

  for (const requirement of jobsStore.requirements || []) {
    if (Number(requirement?.product_id || 0) !== targetId) continue
    const jobId = Number(requirement?.job_id || 0)
    if (!jobId) continue

    const existing = bucket.get(jobId) || {
      job_id: jobId,
      job_code: jobsById.get(jobId)?.job_code || null,
      quantity_required_total: 0,
      quantity_picked_total: 0,
      start_date: jobsById.get(jobId)?.start_date || null,
      end_date: jobsById.get(jobId)?.end_date || null,
      status: jobsById.get(jobId)?.status || null,
    }

    existing.quantity_required_total += Math.max(Number(requirement?.quantity_required || 0), 0)
    existing.quantity_picked_total += Math.max(Number(requirement?.quantity_picked || 0), 0)
    bucket.set(jobId, existing)
  }

  return [...bucket.values()].sort((a, b) => {
    const startA = String(a.start_date || '')
    const startB = String(b.start_date || '')
    return startB.localeCompare(startA)
  })
}

function openProductInfo(product) {
  if (!product) return
  productInfoTarget.value = product
  productInfoDialogOpen.value = true
}

function openRentalProductInfo(product) {
  if (!product) return
  rentalProductInfoTarget.value = product
  rentalProductInfoDialogOpen.value = true
}

function openEditProductFromInfo() {
  if (!productInfoTarget.value) return
  productInfoDialogOpen.value = false
  openEditProduct(productInfoTarget.value)
}

async function openEditRentalProductFromInfo() {
  if (!rentalProductInfoTarget.value) return
  rentalProductInfoDialogOpen.value = false
  await openEditRentalProduct(rentalProductInfoTarget.value)
}

function getActiveInfoContext() {
  if (deviceInfoDialogOpen.value && deviceInfoTarget.value?.id) {
    return { type: 'device', id: Number(deviceInfoTarget.value.id) }
  }
  if (productInfoDialogOpen.value && productInfoTarget.value?.id) {
    return { type: 'product', id: Number(productInfoTarget.value.id) }
  }
  if (rentalProductInfoDialogOpen.value && rentalProductInfoTarget.value?.id) {
    return { type: 'rental', id: Number(rentalProductInfoTarget.value.id) }
  }
  return null
}

function rememberReturnInfoContext(context) {
  if (typeof window === 'undefined') return
  if (!context?.type || !context?.id) return
  window.sessionStorage.setItem(RETURN_INFO_STORAGE_KEY, JSON.stringify({
    type: context.type,
    id: Number(context.id),
  }))
}

function consumeReturnInfoContext() {
  if (typeof window === 'undefined') return null
  const raw = window.sessionStorage.getItem(RETURN_INFO_STORAGE_KEY)
  if (!raw) return null
  window.sessionStorage.removeItem(RETURN_INFO_STORAGE_KEY)
  try {
    const parsed = JSON.parse(raw)
    if (!parsed?.type || !parsed?.id) return null
    return { type: String(parsed.type), id: Number(parsed.id) }
  } catch {
    return null
  }
}

async function openDeviceInfoFromLink(deviceId) {
  const targetId = Number(deviceId || 0)
  if (!targetId) return
  const device = store.devices.find(item => item.id === targetId)
  if (!device) {
    try {
      const { data } = await api.get(`/api/v1/inventory/devices/${targetId}`)
      if (data) {
        deviceInfoTarget.value = data
        deviceInfoDialogOpen.value = true
      }
    } catch {
      // ignore
    }
    return
  }
  deviceInfoTarget.value = device
  deviceInfoDialogOpen.value = true
}

async function openJobFromLink(jobId) {
  const targetId = Number(jobId || 0)
  if (!targetId) return

  const context = getActiveInfoContext()
  if (context?.type && context?.id) rememberReturnInfoContext(context)

  await router.push({ path: '/jobs', query: { focusJobId: String(targetId) } })
}

async function restorePendingInfoDialog() {
  const pending = pendingInfoReturn.value
  pendingInfoReturn.value = null
  if (!pending || !pending.type || !pending.id) return

  if (pending.type === 'device') {
    const device = store.devices.find(item => item.id === pending.id)
    if (device) {
      deviceInfoTarget.value = device
      deviceInfoDialogOpen.value = true
    }
    return
  }
  if (pending.type === 'product') {
    const product = store.products.find(item => item.id === pending.id)
    if (product) openProductInfo(product)
    return
  }
  if (pending.type === 'rental') {
    const rental = store.products.find(item => item.id === pending.id)
    if (rental) openRentalProductInfo(rental)
  }
}

function openProductEditorFromLink(productId) {
  const targetId = Number(productId || 0)
  if (!targetId) return
  const product = store.products.find(item => item.id === targetId)
  if (!product) return

  const context = getActiveInfoContext()
  if (context?.type && context?.id) {
    pendingInfoReturn.value = { type: context.type, id: Number(context.id) }
  }

  deviceInfoDialogOpen.value = false
  productInfoDialogOpen.value = false
  rentalProductInfoDialogOpen.value = false
  openEditProduct(product)
}

function openDeviceEditorFromLink(deviceId) {
  const targetId = Number(deviceId || 0)
  if (!targetId) return
  const device = store.devices.find(item => item.id === targetId)
  if (!device) return

  if (deviceInfoDialogOpen.value && deviceInfoTarget.value?.id) {
    pendingInfoReturn.value = { type: 'device', id: Number(deviceInfoTarget.value.id) }
  } else if (productInfoDialogOpen.value && productInfoTarget.value?.id) {
    pendingInfoReturn.value = { type: 'product', id: Number(productInfoTarget.value.id) }
  } else if (rentalProductInfoDialogOpen.value && rentalProductInfoTarget.value?.id) {
    pendingInfoReturn.value = { type: 'rental', id: Number(rentalProductInfoTarget.value.id) }
  }

  deviceInfoDialogOpen.value = false
  productInfoDialogOpen.value = false
  rentalProductInfoDialogOpen.value = false
  openEditDevice(device)
}

const filteredMaintenance = computed(() => {
  const needle = maintenanceSearch.value.trim().toLowerCase()
  if (!needle) return store.maintenances
  return store.maintenances.filter(item =>
    [item.asset_tag, item.product_name, item.maintenance_type, item.status, item.notes]
      .filter(Boolean)
      .some(value => String(value).toLowerCase().includes(needle))
  )
})

function scheduleTaskCount(scheduleId) {
  const targetId = Number(scheduleId || 0)
  if (!targetId) return 0
  return (store.maintenances || []).filter(item => Number(item?.schedule_id || 0) === targetId).length
}

function scheduleIntervalLabel(schedule) {
  const mode = String(schedule?.interval_mode || '').toLowerCase()
  const value = Number(schedule?.interval_value)
  if (!Number.isFinite(value) || value <= 0) return mode === 'runtime' ? 'Runtime' : 'Calendar'
  return mode === 'runtime' ? `Every ${value}h` : `Every ${value}d`
}

const filteredSchedules = computed(() => {
  const needle = scheduleSearch.value.trim().toLowerCase()
  if (!needle) return store.schedules
  return store.schedules.filter(item =>
    [item.id, item.maintenance_type, item.interval_mode, item.interval_value, item.scheduled_date, item.notes]
      .filter(value => value !== null && value !== undefined)
      .some(value => String(value).toLowerCase().includes(needle))
  )
})

const categoryById = computed(() => {
  const map = new Map()
  for (const category of store.categories) map.set(category.id, category)
  return map
})

const zoneById = computed(() => {
  const map = new Map()
  for (const zone of store.zones) map.set(zone.id, zone)
  return map
})

function categoryNameById(id) {
  if (!id) return null
  return categoryById.value.get(id)?.name ?? null
}

function zoneNameById(id) {
  if (!id) return null
  return zoneById.value.get(id)?.name ?? null
}

function treeToNodes(nodes, prefix = '') {
  const output = []
  for (const node of nodes || []) {
    const label = prefix ? `${prefix} / ${node.name}` : node.name
    output.push({ ...node, label, children: treeToNodes(node.children || [], label) })
  }
  return output
}

const categoryTreeNodes = computed(() => treeToNodes(store.categoryTree))
const locationTreeNodes = computed(() => treeToNodes(store.zoneTree))

const allCategorySelectOptions = computed(() => {
  const flat = []
  const walk = (nodes, prefix = '') => {
    for (const node of nodes || []) {
      const label = prefix ? `${prefix} / ${node.name}` : node.name
      flat.push({ label, value: node.id })
      walk(node.children || [], label)
    }
  }
  walk(store.categoryTree)
  return flat
})

const locationSelectOptions = computed(() => {
  const flat = [{ label: 'Unassigned', value: null }]
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

const parentCategoryOptions = computed(() => [{ label: 'Root', value: null }, ...allCategorySelectOptions.value])
const parentLocationOptions = computed(() => locationSelectOptions.value)
const productOptions = computed(() => store.products.map(p => ({ label: `${p.sku} - ${p.name}`, value: p.id })))
const deviceSelectOptions = computed(() => store.devices.map(d => ({ label: `${d.asset_tag} (${zoneNameById(d.location_zone_id) || 'Unassigned'})`, value: d.id })))
const brandOptions = computed(() => settingsStore.brandOptions.map(value => ({ label: value, value })))
const manufacturerOptions = computed(() => settingsStore.manufacturerOptions.map(value => ({ label: value, value })))
const brandManufacturerMap = computed(() => settingsStore.brandManufacturerMap || {})
const brandLinks = computed(() => settingsStore.brandLinks || {})
const manufacturerLinks = computed(() => settingsStore.manufacturerLinks || {})
const locationTypeOptions = computed(() => {
  const values = Array.isArray(store.locationTypes) && store.locationTypes.length
    ? store.locationTypes
    : ['rack', 'shelf', 'bin', 'pallet', 'stage', 'truck', 'warehouse', 'workshop']
  return values.map(value => ({ label: value, value }))
})

async function applyFocusFromQuery() {
  const queryTab = String(route.query.tab || '').trim()
  if (queryTab) {
    tab.value = queryTab
  }

  const focusProductId = Number(route.query.focusProductId || 0)
  const focusDeviceId = Number(route.query.focusDeviceId || 0)
  const focusLocationId = Number(route.query.focusLocationId || 0)

  if (focusProductId > 0) {
    tab.value = 'products'
    let product = store.products.find(item => item.id === focusProductId)
    if (!product) {
      try {
        const { data } = await api.get(`/api/v1/inventory/products/${focusProductId}`)
        product = data
      } catch {
        product = null
      }
    }
    if (product) openProductInfo(product)
  } else if (focusDeviceId > 0) {
    tab.value = 'devices'
    const device = store.devices.find(item => item.id === focusDeviceId)
    if (device) {
      deviceInfoTarget.value = device
      deviceInfoDialogOpen.value = true
    } else {
      try {
        const { data } = await api.get(`/api/v1/inventory/devices/${focusDeviceId}`)
        if (data) {
          deviceInfoTarget.value = data
          deviceInfoDialogOpen.value = true
        }
      } catch {
        // ignore
      }
    }
  } else if (focusLocationId > 0) {
    tab.value = 'locations'
    const zone = store.zones.find(item => item.id === focusLocationId)
    if (zone) openEditLocation(zone)
  }

  if (focusProductId || focusDeviceId || focusLocationId) {
    const nextQuery = { ...route.query }
    delete nextQuery.focusProductId
    delete nextQuery.focusDeviceId
    delete nextQuery.focusLocationId
    await router.replace({ path: '/inventory', query: nextQuery })
  }
}

async function applyReturnInfoFromQuery() {
  const returnType = String(route.query.returnInfoType || '').trim().toLowerCase()
  const returnId = Number(route.query.returnInfoId || 0)

  if (!returnType || !returnId) return

  if (returnType === 'device') {
    const device = store.devices.find(item => item.id === returnId)
    if (device) {
      tab.value = 'devices'
      deviceInfoTarget.value = device
      deviceInfoDialogOpen.value = true
    }
  } else if (returnType === 'product') {
    const product = store.products.find(item => item.id === returnId)
    if (product) {
      tab.value = 'products'
      openProductInfo(product)
    }
  } else if (returnType === 'rental') {
    const rental = store.products.find(item => item.id === returnId)
    if (rental) {
      tab.value = 'rentals'
      openRentalProductInfo(rental)
    }
  }

  const nextQuery = { ...route.query }
  delete nextQuery.returnInfoType
  delete nextQuery.returnInfoId
  await router.replace({ path: '/inventory', query: nextQuery })
}

async function applyReturnInfoFromStorage() {
  const pending = consumeReturnInfoContext()
  if (!pending || !pending.type || !pending.id) return

  if (pending.type === 'device') {
    const device = store.devices.find(item => item.id === pending.id)
    if (device) {
      tab.value = 'devices'
      deviceInfoTarget.value = device
      deviceInfoDialogOpen.value = true
    }
    return
  }

  if (pending.type === 'product') {
    const product = store.products.find(item => item.id === pending.id)
    if (product) {
      tab.value = 'products'
      openProductInfo(product)
    }
    return
  }

  if (pending.type === 'rental') {
    const rental = store.products.find(item => item.id === pending.id)
    if (rental) {
      tab.value = 'rentals'
      openRentalProductInfo(rental)
    }
  }
}

onMounted(async () => {
  await loadAll()
  await applyFocusFromQuery()
  await applyReturnInfoFromQuery()
  await applyReturnInfoFromStorage()
})

watch(
  () => [route.query.focusProductId, route.query.focusDeviceId, route.query.focusLocationId, route.query.tab],
  async () => {
    await applyFocusFromQuery()
  }
)

watch(
  () => route.path,
  async (nextPath) => {
    if (nextPath !== '/inventory') return
    await applyReturnInfoFromStorage()
  }
)

async function loadAll() {
  try {
    await Promise.all([
      store.fetchAll(),
      jobsStore.fetchAll(),
      settingsStore.fetchProductDefaults(),
      settingsStore.fetchIntegrations(),
      settingsStore.fetchCompanyProfile(),
      customFieldsStore.fetchDefinitions('product'),
    ])
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || 'Failed to load inventory' })
  }
}

async function prefillCategories() {
  try {
    await store.prefillCategories()
    $q.notify({ type: 'positive', message: t('settings.inventory.categoryPrefillUpdated') })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || t('settings.customFields.prefillFailed') })
  }
}

function getBrandLink(brand) {
  if (!brand) return ''
  return brandLinks.value[brand] || ''
}

function getManufacturerLink(manufacturer) {
  if (!manufacturer) return ''
  return manufacturerLinks.value[manufacturer] || ''
}

const productDialogOpen = ref(false)
const productEditing = ref(null)

function openCreateProduct() {
  productEditing.value = null
  productDialogOpen.value = true
}

function openEditProduct(product) {
  productEditing.value = product
  productDialogOpen.value = true
}

function onProductDialogSaved() {
  restorePendingInfoDialog()
}

watch(productDialogOpen, (open) => {
  if (!open) {
    restorePendingInfoDialog()
  }
})

const deviceDialogOpen = ref(false)
const deviceEditing = ref(null)

function onDeviceDialogSaved() {
  restorePendingInfoDialog()
}

function openCreateDevice() {
  deviceEditing.value = null
  deviceDialogOpen.value = true
}

function openEditDevice(device) {
  deviceEditing.value = device
  deviceDialogOpen.value = true
}

function normalizeOptionalDate(value) {
  return value ? value : null
}

function deviceStatusColor(status) {
  return DEVICE_STATUSES.find(item => item.value === status)?.color || 'grey'
}

function conditionColor(condition) {
  if (condition === 'damaged') return 'negative'
  if (condition === 'fair') return 'warning'
  if (condition === 'good') return 'positive'
  return 'grey-7'
}

function maintenanceStatusColor(status) {
  if (status === 'completed') return 'positive'
  if (status === 'in_progress') return 'warning'
  if (status === 'canceled') return 'grey'
  return 'info'
}

function maintenanceSourceLabel(row) {
  const scheduleId = Number(row?.schedule_id || 0)
  return scheduleId ? `Schedule #${scheduleId}` : 'Manual'
}

function maintenanceSourceColor(row) {
  return Number(row?.schedule_id || 0) ? 'secondary' : 'grey-7'
}

const maintenanceDialogOpen = ref(false)
const maintenanceEditing = ref(null)
const maintenanceDialogMode = ref('schedule')
const maintenanceDialogError = ref('')
const maintenanceFormRef = ref(null)
const maintenanceTargetsExpanded = ref(true)
const maintenanceDialogTitle = computed(() => {
  if (maintenanceEditing.value) return 'Edit maintenance'
  return maintenanceDialogMode.value === 'task' ? 'Create maintenance task' : 'Create maintenance schedule'
})
const maintenanceScheduleDialogOpen = ref(false)
const maintenanceScheduleDialogError = ref('')
const maintenanceScheduleFormRef = ref(null)
const maintenanceScheduleEditingId = ref(null)
const maintenanceCompleteDialogOpen = ref(false)
const maintenanceCompleteDialogError = ref('')
const maintenanceCompleteTarget = ref(null)
const emptyMaintenanceCompleteForm = () => ({
  completed_date: new Date().toISOString().slice(0, 10),
  notes: '',
})
const maintenanceCompleteForm = ref(emptyMaintenanceCompleteForm())
const emptyMaintenanceScheduleForm = () => ({
  maintenance_type: 'inspection',
  interval_mode: 'calendar',
  interval_value: null,
  scheduled_date: new Date().toISOString().slice(0, 10),
  notes: '',
})
const maintenanceScheduleForm = ref(emptyMaintenanceScheduleForm())
const emptyMaintenanceForm = () => ({
  product_ids: [],
  device_ids: [],
  maintenance_type: 'inspection',
  status: 'scheduled',
  interval_mode: 'calendar',
  interval_value: null,
  scheduled_date: new Date().toISOString().slice(0, 10),
  completed_date: '',
  notes: '',
})
const maintenanceForm = ref(emptyMaintenanceForm())

function openCreateMaintenance(mode = 'schedule', preferredDeviceId = null) {
  maintenanceDialogMode.value = mode === 'task' ? 'task' : 'schedule'
  maintenanceEditing.value = null
  maintenanceDialogError.value = ''
  maintenanceTargetsExpanded.value = maintenanceDialogMode.value === 'schedule' && !isPhone.value
  maintenanceForm.value = emptyMaintenanceForm()
  if (preferredDeviceId) {
    maintenanceForm.value.device_ids = [Number(preferredDeviceId)]
  }
  maintenanceDialogOpen.value = true
}

function openEditMaintenance(item) {
  maintenanceEditing.value = item
  maintenanceDialogError.value = ''
  maintenanceTargetsExpanded.value = true
  maintenanceForm.value = {
    product_ids: item.product_id ? [item.product_id] : [],
    device_ids: item.device_id ? [item.device_id] : [],
    maintenance_type: item.maintenance_type || 'inspection',
    status: item.status || 'scheduled',
    interval_mode: item.interval_mode || 'calendar',
    interval_value: item.interval_value ?? null,
    scheduled_date: item.scheduled_date || '',
    completed_date: item.completed_date || '',
    notes: item.notes || '',
  }
  maintenanceDialogOpen.value = true
}

async function saveMaintenance() {
  const valid = await maintenanceFormRef.value?.validate()
  if (!valid) return

  if (!maintenanceEditing.value && maintenanceDialogMode.value === 'schedule' && maintenanceForm.value.product_ids.length === 0 && maintenanceForm.value.device_ids.length === 0) {
    maintenanceDialogError.value = 'Select at least one product or device'
    return
  }

  if (!maintenanceEditing.value && maintenanceDialogMode.value === 'task' && maintenanceForm.value.device_ids.length === 0) {
    maintenanceDialogError.value = 'Select one device for the task'
    return
  }

  if (maintenanceEditing.value && maintenanceForm.value.device_ids.length === 0) {
    maintenanceDialogError.value = 'Device is required when editing'
    return
  }

  saving.value = true
  maintenanceDialogError.value = ''
  try {
    const payload = {
      device_id: maintenanceForm.value.device_ids[0],
      maintenance_type: maintenanceForm.value.maintenance_type || 'inspection',
      status: (maintenanceEditing.value || maintenanceDialogMode.value === 'task')
        ? (maintenanceForm.value.status || 'scheduled')
        : 'scheduled',
      scheduled_date: normalizeOptionalDate(maintenanceForm.value.scheduled_date),
      completed_date: normalizeOptionalDate(maintenanceForm.value.completed_date),
      notes: maintenanceForm.value.notes || null,
    }

    if (maintenanceEditing.value || maintenanceDialogMode.value === 'schedule') {
      payload.interval_mode = maintenanceForm.value.interval_mode || 'calendar'
      payload.interval_value = maintenanceForm.value.interval_value
    }

    if (maintenanceEditing.value) {
      await store.updateMaintenance(maintenanceEditing.value.id, payload)
      $q.notify({ type: 'positive', message: 'Maintenance updated' })
    } else if (maintenanceDialogMode.value === 'task') {
      await store.createMaintenance(payload)
      $q.notify({ type: 'positive', message: 'Maintenance task created' })
    } else {
      const records = await store.bulkScheduleMaintenance({
        device_ids: maintenanceForm.value.device_ids,
        product_ids: maintenanceForm.value.product_ids,
        maintenance_type: payload.maintenance_type,
        interval_mode: payload.interval_mode,
        interval_value: payload.interval_value,
        scheduled_date: payload.scheduled_date,
        notes: payload.notes,
      })
      $q.notify({ type: 'positive', message: `${records.length} maintenance items scheduled` })
    }
    maintenanceDialogOpen.value = false
  } catch (error) {
    maintenanceDialogError.value = error?.response?.data?.detail || 'Failed to save maintenance'
  } finally {
    saving.value = false
  }
}

async function openEditMaintenanceSchedule(item) {
  const scheduleId = Number(item?.schedule_id || item?.id || 0)
  if (!scheduleId) return

  maintenanceScheduleDialogError.value = ''
  try {
    const schedule = await store.fetchMaintenanceSchedule(scheduleId)
    maintenanceScheduleEditingId.value = scheduleId
    maintenanceScheduleForm.value = {
      maintenance_type: schedule?.maintenance_type || 'inspection',
      interval_mode: schedule?.interval_mode || 'calendar',
      interval_value: schedule?.interval_value ?? null,
      scheduled_date: schedule?.scheduled_date || '',
      notes: schedule?.notes || '',
    }
    maintenanceScheduleDialogOpen.value = true
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || 'Failed to load maintenance schedule' })
  }
}

async function saveMaintenanceSchedule() {
  const valid = await maintenanceScheduleFormRef.value?.validate()
  if (!valid) return
  if (!maintenanceScheduleEditingId.value) return

  saving.value = true
  maintenanceScheduleDialogError.value = ''
  try {
    const payload = {
      maintenance_type: maintenanceScheduleForm.value.maintenance_type || 'inspection',
      interval_mode: maintenanceScheduleForm.value.interval_mode || 'calendar',
      interval_value: maintenanceScheduleForm.value.interval_value,
      scheduled_date: normalizeOptionalDate(maintenanceScheduleForm.value.scheduled_date),
      notes: maintenanceScheduleForm.value.notes || null,
    }
    await store.updateMaintenanceSchedule(maintenanceScheduleEditingId.value, payload)
    maintenanceScheduleDialogOpen.value = false
    $q.notify({ type: 'positive', message: 'Schedule and pending tasks updated' })
  } catch (error) {
    maintenanceScheduleDialogError.value = error?.response?.data?.detail || 'Failed to update maintenance schedule'
  } finally {
    saving.value = false
  }
}

async function completeMaintenanceRow(item) {
  maintenanceCompleteTarget.value = item || null
  maintenanceCompleteDialogError.value = ''
  maintenanceCompleteForm.value = {
    completed_date: item?.completed_date || new Date().toISOString().slice(0, 10),
    notes: item?.notes || '',
  }
  maintenanceCompleteDialogOpen.value = true
}

async function confirmCompleteMaintenance() {
  const item = maintenanceCompleteTarget.value
  if (!item?.id) return

  saving.value = true
  maintenanceCompleteDialogError.value = ''
  try {
    const completedDate = normalizeOptionalDate(maintenanceCompleteForm.value.completed_date) || new Date().toISOString().slice(0, 10)
    const notes = String(maintenanceCompleteForm.value.notes || '').trim() || null
    await store.completeMaintenance(item.id, {
      completed_date: completedDate,
      notes,
    })
    maintenanceCompleteDialogOpen.value = false
    maintenanceCompleteTarget.value = null
    maintenanceCompleteForm.value = emptyMaintenanceCompleteForm()
    $q.notify({ type: 'positive', message: 'Maintenance completed' })
  } catch (error) {
    maintenanceCompleteDialogError.value = error?.response?.data?.detail || 'Failed to complete maintenance'
  } finally {
    saving.value = false
  }
}

function selectedRowIds(rows) {
  return [...new Set((rows || []).map(row => Number(row?.id || 0)).filter(Boolean))]
}

async function openBulkPrintLabels(entity, rowsOrIds) {
  const normalizedEntity = String(entity || '').trim().toLowerCase()
  if (!['product', 'device', 'location'].includes(normalizedEntity)) return

  const ids = Array.isArray(rowsOrIds)
    ? rowsOrIds.map(item => Number(typeof item === 'object' ? item?.id : item)).filter(Boolean)
    : []

  if (!ids.length) {
    $q.notify({ type: 'warning', message: 'Select at least one item to print labels' })
    return
  }

  await router.push({
    path: '/labels',
    query: {
      entity: normalizedEntity,
      ids: [...new Set(ids)].join(','),
      autoPrint: '1',
    },
  })
}

function openBulkEditProducts() {
  bulkProductDialogError.value = ''
  bulkProductForm.value = {
    category_id: null,
    product_type: null,
    brand: '',
    manufacturer: '',
    maintenance_interval_days: null,
    daily_rate: null,
    replace_cost: null,
  }
  bulkProductDialogOpen.value = true
}

async function saveBulkProducts() {
  const ids = selectedRowIds(selectedProducts.value)
  if (!ids.length) return

  const patch = {}
  if (bulkProductForm.value.category_id != null) patch.category_id = bulkProductForm.value.category_id
  if (bulkProductForm.value.product_type) patch.product_type = bulkProductForm.value.product_type
  if (String(bulkProductForm.value.brand || '').trim()) patch.brand = String(bulkProductForm.value.brand).trim()
  if (String(bulkProductForm.value.manufacturer || '').trim()) patch.manufacturer = String(bulkProductForm.value.manufacturer).trim()
  if (bulkProductForm.value.maintenance_interval_days != null) patch.maintenance_interval_days = bulkProductForm.value.maintenance_interval_days
  if (bulkProductForm.value.daily_rate != null) patch.daily_rate = bulkProductForm.value.daily_rate
  if (bulkProductForm.value.replace_cost != null) patch.replace_cost = bulkProductForm.value.replace_cost
  if (!Object.keys(patch).length) {
    bulkProductDialogError.value = 'Choose at least one field to update'
    return
  }

  saving.value = true
  bulkProductDialogError.value = ''
  try {
    const result = await store.bulkUpdateProducts(ids, patch)
    selectedProducts.value = []
    bulkProductDialogOpen.value = false
    $q.notify({ type: 'positive', message: `Products updated: ${result?.updated || 0}` })
  } catch (error) {
    bulkProductDialogError.value = error?.response?.data?.detail || 'Bulk product update failed'
  } finally {
    saving.value = false
  }
}

async function runBulkDeleteProducts() {
  const ids = selectedRowIds(selectedProducts.value)
  if (!ids.length) return
  if (!window.confirm(`Delete ${ids.length} selected products? All linked devices and job requirements for these products will also be deleted.`)) return

  saving.value = true
  try {
    const result = await store.bulkDeleteProducts(ids, { deleteLinkedDevices: true })
    selectedProducts.value = []
    $q.notify({ type: 'positive', message: `Products deleted: ${result?.deleted || 0}, skipped: ${result?.skipped || 0}` })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || 'Bulk product delete failed' })
  } finally {
    saving.value = false
  }
}

function openBulkEditDevices() {
  bulkDeviceDialogError.value = ''
  bulkDeviceForm.value = { status: null, condition: null, location_zone_id: null }
  bulkDeviceDialogOpen.value = true
}

async function saveBulkDevices() {
  const ids = selectedRowIds(selectedDevices.value)
  if (!ids.length) return

  const patch = {}
  if (bulkDeviceForm.value.status) patch.status = bulkDeviceForm.value.status
  if (bulkDeviceForm.value.condition) patch.condition = bulkDeviceForm.value.condition
  if (bulkDeviceForm.value.location_zone_id != null) patch.location_zone_id = bulkDeviceForm.value.location_zone_id

  if (!Object.keys(patch).length) {
    bulkDeviceDialogError.value = 'Choose at least one field to update'
    return
  }

  saving.value = true
  bulkDeviceDialogError.value = ''
  try {
    const result = await store.bulkUpdateDevices(ids, patch)
    selectedDevices.value = []
    bulkDeviceDialogOpen.value = false
    $q.notify({ type: 'positive', message: `Devices updated: ${result?.updated || 0}` })
  } catch (error) {
    bulkDeviceDialogError.value = error?.response?.data?.detail || 'Bulk device update failed'
  } finally {
    saving.value = false
  }
}

async function runBulkDeleteDevices() {
  const ids = selectedRowIds(selectedDevices.value)
  if (!ids.length) return
  if (!window.confirm(`Delete ${ids.length} selected devices?`)) return

  saving.value = true
  try {
    const result = await store.bulkDeleteDevices(ids)
    selectedDevices.value = []
    $q.notify({ type: 'positive', message: `Devices deleted: ${result?.deleted || 0}` })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || 'Bulk device delete failed' })
  } finally {
    saving.value = false
  }
}

function openBulkEditMaintenance() {
  bulkMaintenanceDialogError.value = ''
  bulkMaintenanceForm.value = {
    status: null,
    maintenance_type: null,
    scheduled_date: '',
    completed_date: '',
  }
  bulkMaintenanceDialogOpen.value = true
}

async function saveBulkMaintenance() {
  const ids = selectedRowIds(selectedMaintenance.value)
  if (!ids.length) return

  const patch = {}
  if (bulkMaintenanceForm.value.status) patch.status = bulkMaintenanceForm.value.status
  if (bulkMaintenanceForm.value.maintenance_type) patch.maintenance_type = bulkMaintenanceForm.value.maintenance_type
  if (bulkMaintenanceForm.value.scheduled_date) patch.scheduled_date = normalizeOptionalDate(bulkMaintenanceForm.value.scheduled_date)
  if (bulkMaintenanceForm.value.completed_date) patch.completed_date = normalizeOptionalDate(bulkMaintenanceForm.value.completed_date)

  if (!Object.keys(patch).length) {
    bulkMaintenanceDialogError.value = 'Choose at least one field to update'
    return
  }

  saving.value = true
  bulkMaintenanceDialogError.value = ''
  try {
    const result = await store.bulkUpdateMaintenance(ids, patch)
    selectedMaintenance.value = []
    bulkMaintenanceDialogOpen.value = false
    $q.notify({ type: 'positive', message: `Maintenance tasks updated: ${result?.updated || 0}` })
  } catch (error) {
    bulkMaintenanceDialogError.value = error?.response?.data?.detail || 'Bulk maintenance update failed'
  } finally {
    saving.value = false
  }
}

async function runBulkDeleteMaintenance() {
  const ids = selectedRowIds(selectedMaintenance.value)
  if (!ids.length) return
  if (!window.confirm(`Delete ${ids.length} selected maintenance tasks?`)) return

  saving.value = true
  try {
    const result = await store.bulkDeleteMaintenance(ids)
    selectedMaintenance.value = []
    $q.notify({ type: 'positive', message: `Maintenance tasks deleted: ${result?.deleted || 0}` })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || 'Bulk maintenance delete failed' })
  } finally {
    saving.value = false
  }
}

function openBulkEditSchedules() {
  bulkScheduleDialogError.value = ''
  bulkScheduleForm.value = {
    maintenance_type: null,
    interval_mode: null,
    interval_value: null,
    scheduled_date: '',
    notes: '',
  }
  bulkScheduleDialogOpen.value = true
}

async function saveBulkSchedules() {
  const ids = selectedRowIds(selectedSchedules.value)
  if (!ids.length) return

  const patch = {}
  if (bulkScheduleForm.value.maintenance_type) patch.maintenance_type = bulkScheduleForm.value.maintenance_type
  if (bulkScheduleForm.value.interval_mode) patch.interval_mode = bulkScheduleForm.value.interval_mode
  if (bulkScheduleForm.value.interval_value != null) patch.interval_value = Number(bulkScheduleForm.value.interval_value)
  if (bulkScheduleForm.value.scheduled_date) patch.scheduled_date = normalizeOptionalDate(bulkScheduleForm.value.scheduled_date)
  if (String(bulkScheduleForm.value.notes || '').trim()) patch.notes = String(bulkScheduleForm.value.notes).trim()

  if (!Object.keys(patch).length) {
    bulkScheduleDialogError.value = 'Choose at least one field to update'
    return
  }

  saving.value = true
  bulkScheduleDialogError.value = ''
  try {
    const result = await store.bulkUpdateMaintenanceSchedules(ids, patch)
    selectedSchedules.value = []
    bulkScheduleDialogOpen.value = false
    $q.notify({ type: 'positive', message: `Schedules updated: ${result?.updated || 0}` })
  } catch (error) {
    bulkScheduleDialogError.value = error?.response?.data?.detail || 'Bulk schedule update failed'
  } finally {
    saving.value = false
  }
}

async function runBulkDeleteSchedules() {
  const ids = selectedRowIds(selectedSchedules.value)
  if (!ids.length) return
  if (!window.confirm(`Delete ${ids.length} selected schedules? Linked maintenance tasks stay unchanged.`)) return

  saving.value = true
  try {
    const result = await store.bulkDeleteMaintenanceSchedules(ids)
    selectedSchedules.value = []
    $q.notify({ type: 'positive', message: `Schedules deleted: ${result?.deleted || 0}, skipped: ${result?.skipped || 0}` })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || 'Bulk schedule delete failed' })
  } finally {
    saving.value = false
  }
}

const categoryDialogOpen = ref(false)
const categoryEditing = ref(null)
const categoryDialogError = ref('')
const categoryFormRef = ref(null)
const emptyCategoryForm = () => ({ name: '', parent_id: null, sort_order: 0, is_active: true })
const categoryForm = ref(emptyCategoryForm())

function openCreateCategory() {
  categoryEditing.value = null
  categoryForm.value = emptyCategoryForm()
  categoryDialogError.value = ''
  categoryDialogOpen.value = true
}

function openEditCategory(category) {
  categoryEditing.value = category
  categoryForm.value = {
    name: category.name ?? '',
    parent_id: category.parent_id ?? null,
    sort_order: Number(category.sort_order ?? 0),
    is_active: !!category.is_active,
  }
  categoryDialogError.value = ''
  categoryDialogOpen.value = true
}

async function saveCategory() {
  const valid = await categoryFormRef.value?.validate()
  if (!valid) return

  saving.value = true
  categoryDialogError.value = ''
  try {
    const payload = {
      name: categoryForm.value.name.trim(),
      parent_id: categoryForm.value.parent_id,
      sort_order: Number(categoryForm.value.sort_order || 0),
      is_active: !!categoryForm.value.is_active,
    }

    if (categoryEditing.value) {
      await store.updateCategory(categoryEditing.value.id, payload)
      $q.notify({ type: 'positive', message: 'Category updated' })
    } else {
      await store.createCategory(payload)
      $q.notify({ type: 'positive', message: 'Category created' })
    }

    categoryDialogOpen.value = false
  } catch (error) {
    categoryDialogError.value = error?.response?.data?.detail || 'Failed to save category'
  } finally {
    saving.value = false
  }
}

const locationDialogOpen = ref(false)
const locationEditing = ref(null)
const locationDialogError = ref('')
const locationFormRef = ref(null)
const emptyLocationForm = () => ({
  code: '',
  name: '',
  zone_type: 'rack',
  barcode: '',
  qr_code: '',
  rfid: '',
  parent_id: null,
  sort_order: 0,
  is_active: true,
})
const locationForm = ref(emptyLocationForm())
// Single-location auto-generate toggle and edit-tracking
const locationAutoGenerateCode = ref(true)
const locationCodeEdited = ref(false)

// Auto-generate `code` from `name` for location dialog when enabled
watch(() => locationForm.value.name, (newName) => {
  if (!locationAutoGenerateCode.value) return
  if (locationCodeEdited.value) return
  locationForm.value.code = slugify(newName || '')
})

function openCreateLocation() {
  locationEditing.value = null
  const firstType = locationTypeOptions.value[0]?.value || 'rack'
  locationForm.value = { ...emptyLocationForm(), zone_type: firstType }
  locationDialogError.value = ''
  locationCodeEdited.value = false
  locationAutoGenerateCode.value = true
  locationDialogOpen.value = true
}

function openEditLocation(zone) {
  locationEditing.value = zone
  locationForm.value = {
    code: zone.code ?? '',
    name: zone.name ?? '',
    zone_type: zone.zone_type ?? 'rack',
    barcode: zone.barcode ?? '',
    qr_code: zone.qr_code ?? '',
    rfid: zone.rfid ?? '',
    parent_id: zone.parent_id ?? null,
    sort_order: Number(zone.sort_order ?? 0),
    is_active: !!zone.is_active,
  }
  locationDialogError.value = ''
  // When editing an existing zone, treat the code as manually set by default
  locationCodeEdited.value = true
  locationAutoGenerateCode.value = false
  locationDialogOpen.value = true
}

async function saveLocation() {
  const valid = await locationFormRef.value?.validate()
  if (!valid) return

  saving.value = true
  locationDialogError.value = ''
  try {
    const payload = {
      code: locationForm.value.code.trim(),
      name: locationForm.value.name.trim(),
      zone_type: locationForm.value.zone_type.trim() || 'rack',
      barcode: locationForm.value.barcode || null,
      qr_code: locationForm.value.qr_code || null,
      rfid: locationForm.value.rfid || null,
      parent_id: locationForm.value.parent_id,
      sort_order: Number(locationForm.value.sort_order || 0),
      is_active: !!locationForm.value.is_active,
    }

    if (locationEditing.value) {
      await store.updateZone(locationEditing.value.id, payload)
      $q.notify({ type: 'positive', message: 'Location updated' })
    } else {
      await store.createZone(payload)
      $q.notify({ type: 'positive', message: 'Location created' })
    }

    locationDialogOpen.value = false
  } catch (error) {
    locationDialogError.value = error?.response?.data?.detail || 'Failed to save location'
  } finally {
    saving.value = false
  }
}

const bulkCreateDialogOpen = ref(false)
const bulkCreateParent = ref(null)
const bulkCreateText = ref('')
const bulkCreateZoneType = ref(locationTypeOptions.value[0]?.value || 'rack')
const bulkCreateIsActive = ref(true)
const bulkCreateInterpretRanges = ref(true)
const bulkCreateAutoGenerateCode = ref(true)
const bulkCreateError = ref('')

function tr(key, fallback) {
  try {
    const val = t(key)
    if (!val || val === key) return fallback || key
    return val
  } catch (e) {
    return fallback || key
  }
}

function openBulkCreateSubzones(node) {
  bulkCreateParent.value = node
  bulkCreateText.value = ''
  bulkCreateZoneType.value = locationTypeOptions.value[0]?.value || 'rack'
  bulkCreateIsActive.value = true
  bulkCreateError.value = ''
  bulkCreateDialogOpen.value = true
}

async function saveBulkCreateSubzones() {
  const rawLines = String(bulkCreateText.value || '').split(/\r?\n/).map(s => s.trim()).filter(Boolean)
  const lines = []
  // expand ranges like a-f or 1-5
  for (const line of rawLines) {
    if (bulkCreateInterpretRanges.value) {
      const mAlpha = line.match(/^([A-Za-z])\s*-\s*([A-Za-z])$/)
      const mNum = line.match(/^(\d+)\s*-\s*(\d+)$/)
      if (mAlpha) {
        let a = mAlpha[1]
        let b = mAlpha[2]
        const start = a.toLowerCase().charCodeAt(0)
        const end = b.toLowerCase().charCodeAt(0)
        const step = start <= end ? 1 : -1
        const preserveUpper = (a[0] >= 'A' && a[0] <= 'Z')
        for (let c = start; step === 1 ? c <= end : c >= end; c += step) {
          const ch = String.fromCharCode(c)
          lines.push(preserveUpper ? ch.toUpperCase() : ch)
        }
        continue
      } else if (mNum) {
        const start = Number(mNum[1])
        const end = Number(mNum[2])
        const step = start <= end ? 1 : -1
        const width = Math.max(String(start).length, String(end).length)
        for (let n = start; step === 1 ? n <= end : n >= end; n += step) {
          lines.push(String(n).padStart(width, '0'))
        }
        continue
      }
    }
    lines.push(line)
  }
  if (!lines.length) {
    bulkCreateError.value = t('inventory.bulkCreateSubzones.emptyNames')
    return
  }

  // prepare codes: sanitize and avoid collisions when auto-generate enabled
  const existingCodes = new Set((store.zones || []).map(z => String(z.code || '').toLowerCase()).filter(Boolean))
  const items = []
  for (const name of lines) {
    let baseCode = bulkCreateAutoGenerateCode.value ? slugify(name) : String(name).trim()
    if (!baseCode) baseCode = `zone-${items.length + 1}`
    baseCode = String(baseCode).slice(0, ZONE_CODE_MAX_LENGTH)
    if (!baseCode) {
      bulkCreateError.value = t('inventory.bulkCreateSubzones.invalidCode')
      return
    }

    let code = baseCode
    let suffix = 1
    while (existingCodes.has(String(code || '').toLowerCase())) {
      const suffixLabel = `-${suffix++}`
      const maxBaseLength = Math.max(ZONE_CODE_MAX_LENGTH - suffixLabel.length, 1)
      code = `${baseCode.slice(0, maxBaseLength)}${suffixLabel}`
    }
    existingCodes.add(String(code || '').toLowerCase())
    items.push({
      code: String(code || '').trim(),
      name,
      zone_type: bulkCreateZoneType.value || 'rack',
      barcode: null,
      qr_code: null,
      rfid: null,
      sort_order: 0,
      is_active: !!bulkCreateIsActive.value,
    })
  }

  saving.value = true
  bulkCreateError.value = ''
  try {
    await store.createZonesBulk(bulkCreateParent.value.id, items)
    $q.notify({ type: 'positive', message: t('inventory.bulkCreateSubzones.created') })
    bulkCreateDialogOpen.value = false
  } catch (error) {
    const serverDetail = error?.response?.data?.detail
    if (error?.response?.status === 409 && serverDetail && typeof serverDetail === 'object') {
      const conflicts = serverDetail.conflicts || []
      const msg = t('inventory.bulkCreateSubzones.conflictMessage')
      bulkCreateError.value = conflicts.length ? `${msg}: ${conflicts.join(', ')}` : msg
    } else if (typeof serverDetail === 'string' && serverDetail.trim()) {
      bulkCreateError.value = serverDetail.trim()
    } else {
      bulkCreateError.value = t('inventory.bulkCreateSubzones.failed')
    }
  } finally {
    saving.value = false
  }
}

const deleteCategoryDialogOpen = ref(false)
const deleteCategoryTarget = ref(null)
const draggingCategoryId = ref(null)
const draggingLocationId = ref(null)

const quickCreateDialogOpen = ref(false)
const quickCreateTargetProduct = ref(null)
const quickCreateError = ref('')
const quickCreateForm = ref({
  quantity: 1,
  auto_generate: true,
  asset_tag_prefix: '',
  asset_tag: '',
  status: 'available',
  condition: 'good',
  location_zone_id: null,
})

function openQuickCreateDevices(product) {
  quickCreateTargetProduct.value = product
  quickCreateError.value = ''
  quickCreateForm.value = {
    quantity: 1,
    auto_generate: true,
    asset_tag_prefix: product?.sku || '',
    asset_tag: '',
    status: 'available',
    condition: 'good',
    location_zone_id: null,
  }
  quickCreateDialogOpen.value = true
}

async function runQuickCreateDevices() {
  if (!quickCreateTargetProduct.value) return
  if (!quickCreateForm.value.auto_generate && !quickCreateForm.value.asset_tag) {
    quickCreateError.value = 'Asset tag is required when auto-generate is disabled'
    return
  }

  saving.value = true
  quickCreateError.value = ''
  try {
    const payload = {
      quantity: Number(quickCreateForm.value.quantity || 1),
      auto_generate: !!quickCreateForm.value.auto_generate,
      asset_tag_prefix: quickCreateForm.value.asset_tag_prefix || null,
      asset_tag: quickCreateForm.value.asset_tag || null,
      status: quickCreateForm.value.status || 'available',
      condition: quickCreateForm.value.condition || 'good',
      location_zone_id: quickCreateForm.value.location_zone_id,
    }
    const devices = await store.createDevicesForProduct(quickCreateTargetProduct.value.id, payload)
    quickCreateDialogOpen.value = false
    $q.notify({ type: 'positive', message: `${devices.length} device(s) created` })
  } catch (error) {
    quickCreateError.value = error?.response?.data?.detail || 'Failed to create devices'
  } finally {
    saving.value = false
  }
}

const importDialogOpen = ref(false)
const importing = ref(false)
const importDialogError = ref('')
const importEntityType = ref('product')
const importFile = ref(null)
const importRows = ref([])
const importSourceKeys = ref([])
const importMapping = ref({})
const importUseServer = ref(false)
const updateExistingDevices = ref(false)

// bulk-delete dialog
const bulkDeleteDialogOpen = ref(false)
const bulkDeleteSaving = ref(false)
const bulkDeleteError = ref('')

function selectNodeAndChildren(node) {
  const ids = []
  function walk(n) {
    ids.push(n.id)
    for (const c of n.children || []) walk(c)
  }
  walk(node)
  // replace selection with subtree
  selectedLocationIds.value = ids
}

async function doBulkDeleteLocations() {
  if (!selectedLocationIds.value.length) return
  bulkDeleteSaving.value = true
  bulkDeleteError.value = ''
  try {
    const res = await store.deleteZonesBulk(selectedLocationIds.value)
    $q.notify({ type: 'positive', message: `${res.deleted} location(s) deleted` })
    selectedLocationIds.value = []
    bulkDeleteDialogOpen.value = false
  } catch (error) {
    bulkDeleteError.value = error?.response?.data?.detail || error?.message || 'Failed to delete locations'
  } finally {
    bulkDeleteSaving.value = false
  }
}

const importEntityOptions = [
  { label: 'Products', value: 'product' },
  { label: 'Devices', value: 'device' },
  { label: 'Products + Devices', value: 'mixed' },
  { label: 'Locations', value: 'location' },
]

const importFieldConfigs = {
  product: [
    { targetField: 'sku', label: 'SKU', required: true },
    { targetField: 'name', label: 'Name', required: true },
    { targetField: 'brand', label: 'Brand', required: false },
    { targetField: 'manufacturer', label: 'Manufacturer', required: false },
    { targetField: 'product_type', label: 'Product Type', required: false },
    { targetField: 'category_id', label: 'Category (id/name)', required: false },
    { targetField: 'daily_rate', label: 'Daily Rate', required: false },
    { targetField: 'replace_cost', label: 'Replacement Cost', required: false },
    { targetField: 'weight_kg', label: 'Weight (kg)', required: false },
    { targetField: 'height_cm', label: 'Height (cm)', required: false },
    { targetField: 'width_cm', label: 'Width (cm)', required: false },
    { targetField: 'depth_cm', label: 'Depth (cm)', required: false },
    { targetField: 'maintenance_interval_days', label: 'Maintenance Interval Days', required: false },
    { targetField: 'power_consumption_watts', label: 'Power Consumption Watts', required: false },
  ],
  device: [
    { targetField: 'product_id', label: 'Product (id/sku/name)', required: true },
    { targetField: 'asset_tag', label: 'Asset Tag', required: true },
    { targetField: 'serial_number', label: 'Serial Number', required: false },
    { targetField: 'barcode', label: 'Barcode', required: false },
    { targetField: 'qr_code', label: 'QR Code', required: false },
    { targetField: 'rfid', label: 'RFID', required: false },
    { targetField: 'location_zone_id', label: 'Location (id/code/name)', required: false },
    { targetField: 'status', label: 'Status', required: false },
    { targetField: 'condition', label: 'Condition', required: false },
    { targetField: 'purchase_date', label: 'Purchase Date', required: false },
    { targetField: 'purchase_price', label: 'Purchase Price', required: false },
    { targetField: 'purchased_from', label: 'Purchased From', required: false },
    { targetField: 'sold_price', label: 'Sold Price', required: false },
    { targetField: 'finance_upto', label: 'Finance Up To', required: false },
    { targetField: 'finance_company', label: 'Finance Company', required: false },
    { targetField: 'finance_ref', label: 'Finance Reference', required: false },
    { targetField: 'pre_prep', label: 'Pre-prep', required: false },
    { targetField: 'warranty_end_date', label: 'Warranty End Date', required: false },
    { targetField: 'retire_date', label: 'Retire Date', required: false },
    { targetField: 'usage_hours', label: 'Usage Hours', required: false },
    { targetField: 'notes', label: 'Notes', required: false },
  ],
  mixed: [
    { targetField: 'entity_type', label: 'Entity Type (product/device)', required: false },
    { targetField: 'sku', label: 'SKU', required: false },
    { targetField: 'name', label: 'Name', required: false },
    { targetField: 'brand', label: 'Brand', required: false },
    { targetField: 'manufacturer', label: 'Manufacturer', required: false },
    { targetField: 'supplier_name', label: 'Supplier', required: false },
    { targetField: 'daily_rate', label: 'Daily Rate', required: false },
    { targetField: 'product_type', label: 'Product Type', required: false },
    { targetField: 'category_id', label: 'Category (id/name)', required: false },
    { targetField: 'weight_kg', label: 'Weight (kg)', required: false },
    { targetField: 'height_cm', label: 'Height (cm)', required: false },
    { targetField: 'width_cm', label: 'Width (cm)', required: false },
    { targetField: 'depth_cm', label: 'Depth (cm)', required: false },
    { targetField: 'maintenance_interval_days', label: 'Maintenance Interval Days', required: false },
    { targetField: 'power_consumption_watts', label: 'Power Consumption Watts', required: false },
    { targetField: 'replace_cost', label: 'Replacement Cost', required: false },
    { targetField: 'product_id', label: 'Product (id/sku/name)', required: false },
    { targetField: 'asset_tag', label: 'Asset Tag', required: false },
    { targetField: 'serial_number', label: 'Serial Number', required: false },
    { targetField: 'barcode', label: 'Barcode', required: false },
    { targetField: 'qr_code', label: 'QR Code', required: false },
    { targetField: 'rfid', label: 'RFID', required: false },
    { targetField: 'location_zone_id', label: 'Location (id/code/name)', required: false },
    { targetField: 'status', label: 'Status', required: false },
    { targetField: 'condition', label: 'Condition', required: false },
    { targetField: 'purchase_date', label: 'Purchase Date', required: false },
    { targetField: 'purchase_price', label: 'Purchase Price', required: false },
    { targetField: 'purchased_from', label: 'Purchased From', required: false },
    { targetField: 'sold_price', label: 'Sold Price', required: false },
    { targetField: 'finance_upto', label: 'Finance Up To', required: false },
    { targetField: 'finance_company', label: 'Finance Company', required: false },
    { targetField: 'finance_ref', label: 'Finance Reference', required: false },
    { targetField: 'pre_prep', label: 'Pre-prep', required: false },
    { targetField: 'warranty_end_date', label: 'Warranty End Date', required: false },
    { targetField: 'retire_date', label: 'Retire Date', required: false },
    { targetField: 'usage_hours', label: 'Usage Hours', required: false },
    { targetField: 'notes', label: 'Notes', required: false },
  ],
  location: [
    { targetField: 'code', label: 'Code', required: true },
    { targetField: 'name', label: 'Name', required: true },
    { targetField: 'zone_type', label: 'Location Type', required: false },
    { targetField: 'parent_id', label: 'Parent (id/code/name)', required: false },
    { targetField: 'sort_order', label: 'Sort Order', required: false },
    { targetField: 'is_active', label: 'Is Active', required: false },
  ],
}

const mappingColumns = [
  { name: 'label', label: 'Stockwire Field', field: 'label', align: 'left' },
  { name: 'sourceKey', label: 'Source Field', field: 'sourceKey', align: 'left' },
  { name: 'required', label: 'Required', field: 'required', align: 'left' },
]

const mappingRows = computed(() => importFieldConfigs[importEntityType.value] || [])
const importSourceKeyOptions = computed(() => importSourceKeys.value.map(key => ({ label: key, value: key })))

const importPreviewRows = computed(() => {
  return (importRows.value || []).slice(0, 10).map((rawRow, idx) => {
    const rowEntityType = resolveRowEntityType(rawRow)
    const payload = normalizeImportPayload(rawRow, rowEntityType)
    const error = validateImportPayload(payload, rowEntityType)
    return {
      _preview_id: idx + 1,
      _index: idx + 1,
      _entity_type: rowEntityType,
      _status: error ? 'invalid' : 'valid',
      _error: error,
      ...payload,
    }
  })
})

const importPreviewColumns = computed(() => {
  const cols = [
    { name: '_index', label: '#', field: '_index', align: 'left' },
    { name: '_status', label: 'Status', field: '_status', align: 'left' },
  ]
  if (importEntityType.value === 'mixed') {
    cols.push({
      name: '_entity_type',
      label: 'Entity Type',
      field: row => formatPreviewValue(row._entity_type),
      align: 'left',
    })
  }
  for (const field of mappingRows.value) {
    if (field.targetField === 'entity_type') continue
    cols.push({
      name: field.targetField,
      label: field.label,
      field: row => formatPreviewValue(row[field.targetField]),
      align: 'left',
    })
  }
  return cols
})

function openImportDialog() {
  importDialogOpen.value = true
  importDialogError.value = ''
  importRows.value = []
  importSourceKeys.value = []
  importFile.value = null
  importEntityType.value = 'product'
  resetImportMapping()
}

function onImportEntityChanged() {
  resetImportMapping()
}

function resetImportMapping() {
  const map = {}
  for (const field of importFieldConfigs[importEntityType.value] || []) {
    map[field.targetField] = field.targetField
  }
  importMapping.value = map
}

function isLikelyHirehopRows(rows) {
  if (!Array.isArray(rows)) return false
  return rows.some(row =>
    Array.isArray(row?.serialnumbers) ||
    (row?.ID !== undefined && (row?.TITLE !== undefined || row?.REPLACE_COST !== undefined || row?.serialnumbers !== undefined))
  )
}

async function loadHirehopPreset() {
  const fallbackProductPreset = {
    sku: 'ID',
    name: 'TITLE',
    title: 'TITLE',
    description: 'DESCRIPTION',
    brand: 'fields.tillverkare.value',
    manufacturer: 'fields.tillverkare.value',
    replace_cost: 'REPLACE_COST',
    weight: 'WEIGHT',
    category_id: 'CATEGORY_ID',
    barcode: 'BARCODE',
    height_cm: 'HEIGHT',
    width_cm: 'WIDTH',
    depth_cm: 'LENGTH',
  }

  let preset = {}
  try {
    const res = await api.get('/api/v1/inventory/import/presets/hirehop')
    preset = res.data || {}
  } catch (err) {
    // Keep import usable even when preset endpoint is unavailable.
    preset = {}
  }

  // Use product-only mode for frontend preview; server handles device/serialnumber expansion
  importEntityType.value = 'product'
  importUseServer.value = true
  resetImportMapping()

  // Merge server preset over fallback so required keys are always present.
  const p = { ...fallbackProductPreset, ...(preset.product || {}) }
  const map = { ...importMapping.value }

  // Directly assign: map[stockwireField] = hirehopSourceKey
  map['sku'] = p.sku || p.external_id || 'ID'
  map['name'] = p.name || p.title || 'TITLE'
  map['brand'] = p.brand || 'fields.tillverkare.value'
  map['manufacturer'] = p.manufacturer || 'fields.tillverkare.value'
  map['description'] = p.description || 'DESCRIPTION'
  map['weight_kg'] = p.weight || 'WEIGHT'
  map['category_id'] = p.category_id || 'CATEGORY_ID'
  map['replace_cost'] = p.replace_cost || 'REPLACE_COST'
  map['daily_rate'] = p.daily_rate || 'PRICE1'
  map['rental_price'] = p.rental_price || 'PRICE2'
  map['barcode'] = p.barcode || 'BARCODE'
  map['height_cm'] = p.height_cm || 'HEIGHT'
  map['width_cm'] = p.width_cm || 'WIDTH'
  map['depth_cm'] = p.depth_cm || 'LENGTH'

  importMapping.value = map
  // importSourceKeys will be refreshed when user picks a file; seed with known HireHop keys
  importSourceKeys.value = [
    'ID', 'TITLE', 'DESCRIPTION', 'BARCODE', 'REPLACE_COST', 'WEIGHT', 'CATEGORY_ID',
    'fields.tillverkare.value',
    'HEIGHT', 'WIDTH', 'LENGTH',
    'PRICE1', 'PRICE2', 'STATUS', 'LOCATION', 'MEMO', 'PART_NUMBER',
  ]

  if (preset.product) {
    $q.notify({ type: 'positive', message: 'HireHop preset loaded' })
  } else {
    $q.notify({ type: 'warning', message: 'HireHop preset endpoint unavailable; loaded built-in preset' })
  }
}

async function parseImportFile(file) {
  importDialogError.value = ''
  importRows.value = []
  importSourceKeys.value = []
  if (!file) return

  try {
    const text = await file.text()
    const rows = parseImportRows(text, file?.name || '')
    if (isLikelyHirehopRows(rows)) {
      importUseServer.value = true
    }
    const detectedTypes = Array.from(new Set(rows.slice(0, 100).map(row => resolveImportEntityType(row)).filter(Boolean)))
    if (detectedTypes.length > 1 && detectedTypes.includes('product') && detectedTypes.includes('device')) {
      importEntityType.value = 'mixed'
      // Only reset mapping if the current mapping is still the default (key==value),
      // so a loaded preset isn't overwritten when the user selects a file.
      const isDefaultMap = Object.keys(importMapping.value || {}).length > 0 && Object.entries(importMapping.value).every(([k, v]) => v === k)
      if (isDefaultMap) resetImportMapping()
    }
    importRows.value = rows
    importSourceKeys.value = collectImportSourceKeys(rows)
    const map = { ...importMapping.value }
    for (const field of importFieldConfigs[importEntityType.value] || []) {
      // Only auto-fill fields that are still pointing at themselves (not set by a preset)
      const currentVal = map[field.targetField]
      if (!currentVal || currentVal === field.targetField) {
        map[field.targetField] = importSourceKeys.value.includes(field.targetField) ? field.targetField : null
      }
    }
    importMapping.value = map
  } catch (error) {
    importDialogError.value = error?.message || 'Invalid import file'
  }
}

function toBoolean(value) {
  if (typeof value === 'boolean') return value
  const normalized = String(value || '').trim().toLowerCase()
  return ['1', 'true', 'yes', 'y'].includes(normalized)
}

function resolveCategoryId(value) {
  if (value === null || value === undefined || value === '') return null
  if (typeof value === 'number') return value
  const asNumber = Number(value)
  if (!Number.isNaN(asNumber)) return asNumber
  const needle = String(value).trim().toLowerCase()
  const byName = store.categories.find(item => String(item.name || '').toLowerCase() === needle)
  return byName?.id ?? null
}

function resolveProductId(value) {
  if (value === null || value === undefined || value === '') return null
  if (typeof value === 'number') return value
  const asNumber = Number(value)
  if (!Number.isNaN(asNumber)) return asNumber
  const needle = String(value).trim().toLowerCase()
  const bySku = store.products.find(item => String(item.sku || '').toLowerCase() === needle)
  if (bySku) return bySku.id
  const byName = store.products.find(item => String(item.name || '').toLowerCase() === needle)
  return byName?.id ?? null
}

function resolveZoneId(value) {
  if (value === null || value === undefined || value === '') return null
  if (typeof value === 'number') return value
  const asNumber = Number(value)
  if (!Number.isNaN(asNumber)) return asNumber
  const needle = String(value).trim().toLowerCase()
  const byCode = store.zones.find(item => String(item.code || '').toLowerCase() === needle)
  if (byCode) return byCode.id
  const byName = store.zones.find(item => String(item.name || '').toLowerCase() === needle)
  return byName?.id ?? null
}

function resolveRowEntityType(rawRow) {
  if (importEntityType.value !== 'mixed') return importEntityType.value
  // If the JSON row looks like a HireHop product (has serialnumbers array), prefer product
  if (rawRow && (Array.isArray(rawRow.serialnumbers) || Array.isArray(getImportValueBySourceKey(rawRow, 'serialnumbers')))) return 'product'

  const entityTypeSourceKey = importMapping.value.entity_type
  const mappedEntityValue = entityTypeSourceKey ? getImportValueBySourceKey(rawRow, entityTypeSourceKey) : undefined
  const resolved = resolveImportEntityType({ ...rawRow, entity_type: mappedEntityValue }, null)
  if (['product', 'device'].includes(resolved)) return resolved
  return null
}

function normalizeImportPayload(rawRow, rowEntityType = resolveRowEntityType(rawRow)) {
  const payload = {}
  const fields = importFieldConfigs[rowEntityType] || []
  for (const field of fields) {
    const sourceKey = importMapping.value[field.targetField]
    if (!sourceKey) continue
    const rawValue = getImportValueBySourceKey(rawRow, sourceKey)
    if (['height_cm', 'width_cm', 'depth_cm'].includes(field.targetField)) {
      payload[field.targetField] = convertDimensionValueToCm(rawValue, sourceKey)
    } else {
      payload[field.targetField] = rawValue
    }
  }

  if (rowEntityType === 'product') {
    payload.category_id = resolveCategoryId(payload.category_id)
    if (!payload.product_type) payload.product_type = 'equipment'
  }
  if (rowEntityType === 'device') {
    payload.product_id = resolveProductId(payload.product_id)
    payload.location_zone_id = resolveZoneId(payload.location_zone_id)
    if (!payload.status) payload.status = 'available'
    if (!payload.condition) payload.condition = 'good'
  }
  if (rowEntityType === 'location') {
    payload.parent_id = resolveZoneId(payload.parent_id)
    if (!payload.zone_type) payload.zone_type = locationTypeOptions.value[0]?.value || 'rack'
    if (payload.sort_order === '' || payload.sort_order === undefined || payload.sort_order === null) payload.sort_order = 0
    payload.is_active = payload.is_active === undefined ? true : toBoolean(payload.is_active)
  }

  return payload
}

function validateImportPayload(payload, rowEntityType) {
  if (!rowEntityType) {
    if (importEntityType.value === 'mixed') return 'Entity Type must be product or device'
    return 'Entity type is invalid'
  }
  const required = (importFieldConfigs[rowEntityType] || []).filter(field => field.required)
  for (const field of required) {
    const value = payload[field.targetField]
    if (value === undefined || value === null || value === '') {
      return `${field.label} is required`
    }
  }
  return null
}

function formatPreviewValue(value) {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

async function runJsonImport() {
  if (!importRows.value.length) {
    importDialogError.value = 'Load a JSON or CSV file first'
    return
  }

  importing.value = true
  importDialogError.value = ''
  // Server-side import: upload file and let backend process (supports update_existing)
  if (importUseServer.value) {
    if (!importFile.value) {
      importDialogError.value = 'No file selected for server import'
      importing.value = false
      return
    }
    if (!isLikelyHirehopRows(importRows.value)) {
      importDialogError.value = 'Server import is only supported for HireHop JSON files. Disable "Use server import" to import other file types.'
      importing.value = false
      return
    }
    try {
      const fd = new FormData()
      fd.append('file', importFile.value)
      const res = await api.post('/api/v1/inventory/import', fd, { params: { preset: 'hirehop', dry_run: false, update_existing: updateExistingDevices.value } })
      await loadAll()
      importDialogOpen.value = false
      importing.value = false
      const createdProducts = res.data.created_products || 0
      const createdDevices = res.data.created_devices || 0
      const updatedDevices = res.data.updated_devices || 0
      $q.notify({ type: 'positive', message: `Import completed. Created products: ${createdProducts}, created devices: ${createdDevices}, updated devices: ${updatedDevices}` })
      return
    } catch (err) {
      importDialogError.value = err?.response?.data?.detail || err?.message || 'Server import failed'
      importing.value = false
      return
    }
  }
  let created = 0
  let skipped = 0
  let unknownEntityTypeCount = 0
  let validationFailureCount = 0
  let apiFailureCount = 0

  try {
    const allowedEntityTypes = importEntityType.value === 'mixed'
      ? ['product', 'device']
      : ['product', 'device', 'location']
    for (const row of importRows.value) {
      const rowEntityType = resolveRowEntityType(row)
      if (!allowedEntityTypes.includes(rowEntityType)) {
        skipped += 1
        unknownEntityTypeCount += 1
        continue
      }

      const payload = normalizeImportPayload(row, rowEntityType)
      const validationError = validateImportPayload(payload, rowEntityType)
      if (validationError) {
        skipped += 1
        validationFailureCount += 1
        continue
      }

      try {
        if (rowEntityType === 'product') {
          await store.createProduct(payload)
        } else if (rowEntityType === 'device') {
          await store.createDevice(payload)
        } else {
          await store.createZone(payload)
        }
        created += 1
      } catch {
        skipped += 1
        apiFailureCount += 1
      }
    }

    await loadAll()
    importDialogOpen.value = false
    const skipDetails = []
    if (unknownEntityTypeCount > 0) skipDetails.push(`${unknownEntityTypeCount} unsupported entity type`)
    if (validationFailureCount > 0) skipDetails.push(`${validationFailureCount} validation error`)
    if (apiFailureCount > 0) skipDetails.push(`${apiFailureCount} API error`)
    const skipSuffix = skipDetails.length ? ` (${skipDetails.join(', ')})` : ''
    $q.notify({ type: created > 0 ? 'positive' : 'warning', message: `Import completed. Created: ${created}, skipped: ${skipped}${skipSuffix}` })
  } finally {
    importing.value = false
  }
}

function confirmDeleteCategory(category) {
  deleteCategoryTarget.value = category
  deleteCategoryDialogOpen.value = true
}

async function doDeleteCategory() {
  if (!deleteCategoryTarget.value) return
  saving.value = true
  try {
    await store.deleteCategory(deleteCategoryTarget.value.id)
    deleteCategoryDialogOpen.value = false
    $q.notify({ type: 'positive', message: 'Category deleted' })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || 'Delete failed' })
  } finally {
    saving.value = false
  }
}

function onCategoryDragStart(category) {
  draggingCategoryId.value = category.id
}

function onCategoryDragEnd() {
  draggingCategoryId.value = null
}

async function onCategoryDropOnRow(targetCategory) {
  if (!draggingCategoryId.value || draggingCategoryId.value === targetCategory.id) return
  const draggedCategory = store.categories.find(category => category.id === draggingCategoryId.value)
  if (!draggedCategory) return

  const sameParent = draggedCategory.parent_id === targetCategory.parent_id
  const payload = sameParent ? { parent_id: targetCategory.parent_id, before_id: targetCategory.id } : { parent_id: targetCategory.id, before_id: null }

  try {
    await store.moveCategory(draggedCategory.id, payload)
    $q.notify({ type: 'positive', message: sameParent ? 'Category reordered' : 'Category moved under new parent' })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || 'Move failed' })
  } finally {
    draggingCategoryId.value = null
  }
}

async function onCategoryDropToRoot() {
  if (!draggingCategoryId.value) return
  try {
    await store.moveCategory(draggingCategoryId.value, { parent_id: null, before_id: null })
    $q.notify({ type: 'positive', message: 'Category moved to root' })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || 'Move failed' })
  } finally {
    draggingCategoryId.value = null
  }
}

function onLocationDragStart(zone) {
  draggingLocationId.value = zone.id
}

function onLocationDragEnd() {
  draggingLocationId.value = null
}

async function onLocationDropOnRow(targetZone) {
  if (!draggingLocationId.value || draggingLocationId.value === targetZone.id) return
  const draggedZone = store.zones.find(zone => zone.id === draggingLocationId.value)
  if (!draggedZone) return

  const sameParent = draggedZone.parent_id === targetZone.parent_id
  const payload = sameParent ? { parent_id: targetZone.parent_id, before_id: targetZone.id } : { parent_id: targetZone.id, before_id: null }

  try {
    await store.moveZone(draggedZone.id, payload)
    $q.notify({ type: 'positive', message: sameParent ? 'Location reordered' : 'Location moved under new parent' })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || 'Move failed' })
  } finally {
    draggingLocationId.value = null
  }
}

async function onLocationDropToRoot() {
  if (!draggingLocationId.value) return
  try {
    await store.moveZone(draggingLocationId.value, { parent_id: null, before_id: null })
    $q.notify({ type: 'positive', message: 'Location moved to root' })
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || 'Move failed' })
  } finally {
    draggingLocationId.value = null
  }
}
</script>

<style scoped>
.availability-heat-cell {
  min-width: 98px;
  border-radius: 8px;
  padding: 3px 8px;
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.availability-heat-value {
  font-weight: 700;
  line-height: 1;
}

.availability-heat-ratio {
  font-size: 11px;
  line-height: 1;
  opacity: 0.9;
}

.inventory-cell-ellipsis {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.inventory-products-table :deep(th:last-child),
.inventory-products-table :deep(td:last-child) {
  position: sticky;
  right: 0;
  z-index: 2;
  background: inherit;
}

.inventory-products-table :deep(th:last-child) {
  z-index: 3;
}

:global(body.body--dark) .inventory-products-table :deep(th:last-child),
:global(body.body--dark) .inventory-products-table :deep(td:last-child) {
  background: #1f1f1f;
}

.inventory-action-contrast {
  border: 1px solid rgba(18, 142, 197, 0.42);
  background: rgba(18, 142, 197, 0.08);
}

.device-capture-card {
  background: linear-gradient(155deg, rgba(24, 34, 40, 0.97), rgba(17, 24, 29, 0.96));
  border: 1px solid rgba(63, 135, 63, 0.26);
  border-radius: 18px;
}

.device-capture-icon-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 66px;
  height: 66px;
  border-radius: 16px;
  background: linear-gradient(135deg, #3f873f, #2f6b30);
}

.device-capture-camera-wrap {
  position: relative;
  border: 1px solid rgba(63, 135, 63, 0.36);
  border-radius: 12px;
  overflow: hidden;
  background: #000;
}

.device-capture-video {
  width: 100%;
  height: 260px;
  object-fit: cover;
}

.device-capture-nfc-wrap {
  border: 1px dashed rgba(63, 135, 63, 0.42);
  border-radius: 12px;
  padding: 20px;
  background: rgba(63, 135, 63, 0.07);
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

.comment-bubble {
  background: #f5f5f5;
  border-radius: 6px;
  padding: 6px 10px;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.85rem;
  line-height: 1.4;
}

</style>

<style lang="scss">
body.body--dark .comment-bubble {
  background: #333;
}
</style>
