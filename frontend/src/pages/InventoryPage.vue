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
          <q-btn-dropdown class="q-ml-sm" color="secondary" icon="download" :label="t('inventory.exportData')" unelevated>
            <q-list dense>
              <q-item clickable v-close-popup @click="exportProducts('csv', 'all')">
                <q-item-section>{{ t('inventory.exportAllCsv') }}</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="exportProducts('json', 'all')">
                <q-item-section>{{ t('inventory.exportAllJson') }}</q-item-section>
              </q-item>
              <q-separator />
              <q-item clickable v-close-popup :disable="!selectedProducts.length" @click="exportProducts('csv', 'selected')">
                <q-item-section>{{ t('inventory.exportSelectedCsv') }}</q-item-section>
              </q-item>
              <q-item clickable v-close-popup :disable="!selectedProducts.length" @click="exportProducts('json', 'selected')">
                <q-item-section>{{ t('inventory.exportSelectedJson') }}</q-item-section>
              </q-item>
            </q-list>
          </q-btn-dropdown>
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
          <q-btn-dropdown class="q-ml-sm" color="secondary" icon="download" :label="t('inventory.exportData')" unelevated>
            <q-list dense>
              <q-item clickable v-close-popup @click="exportDevices('csv', 'all')">
                <q-item-section>{{ t('inventory.exportAllCsv') }}</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="exportDevices('json', 'all')">
                <q-item-section>{{ t('inventory.exportAllJson') }}</q-item-section>
              </q-item>
              <q-separator />
              <q-item clickable v-close-popup :disable="!selectedDevices.length" @click="exportDevices('csv', 'selected')">
                <q-item-section>{{ t('inventory.exportSelectedCsv') }}</q-item-section>
              </q-item>
              <q-item clickable v-close-popup :disable="!selectedDevices.length" @click="exportDevices('json', 'selected')">
                <q-item-section>{{ t('inventory.exportSelectedJson') }}</q-item-section>
              </q-item>
            </q-list>
          </q-btn-dropdown>
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
            <q-td :props="props"><q-badge :label="statusLabel(props.value)" :color="deviceStatusColor(props.value)" /></q-td>
          </template>
          <template #body-cell-condition="props">
            <q-td :props="props"><q-badge :label="conditionLabel(props.value)" :color="conditionColor(props.value)" /></q-td>
          </template>
          <template #body-cell-current_job_code="props">
            <q-td :props="props">
              <q-badge v-if="props.row.current_job_code" color="info" text-color="white" :label="props.row.current_job_code" />
              <span v-else class="text-grey-6">-</span>
            </q-td>
          </template>
          <template #body-cell-location_zone_id="props">
            <q-td :props="props">{{ props.row.case_asset_tag ? t('inventory.infoDialogs.caseLocation', { assetTag: props.row.case_asset_tag }) : (zoneNameById(props.value) || t('inventory.infoDialogs.unassigned')) }}</q-td>
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
                    <div class="col-6"><q-badge :color="deviceStatusColor(props.row.status)" :label="statusLabel(props.row.status)" /></div>
                    <div class="col-6"><q-badge color="grey-7" :label="conditionLabel(props.row.condition)" /></div>
                    <div class="col-12" v-if="props.row.serial_number"><div class="text-caption">{{ t('inventory.infoDialogs.serialNumber') }}: {{ props.row.serial_number }}</div></div>
                    <div class="col-12" v-if="props.row.current_job_code"><div class="text-caption">{{ t('inventory.infoDialogs.currentJob') }}: {{ props.row.current_job_code }}</div></div>
                    <div class="col-12"><div class="text-caption">{{ t('inventory.infoDialogs.location') }}: {{ props.row.case_asset_tag ? t('inventory.infoDialogs.caseLocation', { assetTag: props.row.case_asset_tag }) : (zoneNameById(props.row.location_zone_id) || t('inventory.infoDialogs.unassigned')) }}</div></div>
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
                <q-badge size="sm" class="q-mr-xs" color="primary" :label="zoneTypeLabel(prop.node.zone_type)" />
                <q-badge
                  size="sm"
                  class="q-mr-xs"
                  :color="prop.node.is_active ? 'positive' : 'grey'"
                  :label="prop.node.is_active ? t('app.general.active') : t('app.general.inactive')"
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

    <RentalProductDialog
      v-model="rentalProductDialogOpen"
      :product="rentalProductEditing"
      @saved="onRentalProductDialogSaved"
    />

    <BulkDeleteDialog
      v-model="bulkDeleteDialogOpen"
      :delete-target="{ ids: selectedLocationIds, count: selectedLocationIds.length }"
      @deleted="onBulkDeleteLocationsDone"
    />

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

    <CategoryDialog v-model="categoryDialogOpen" :category="categoryEditing" @saved="categoryDialogOpen = false" />

    <LocationDialog v-model="locationDialogOpen" :zone="locationEditing" @saved="locationDialogOpen = false" />

    <BulkCreateDialog v-model="bulkCreateDialogOpen" :parent-zone="bulkCreateParent" @saved="bulkCreateDialogOpen = false" />

    <DeleteCategoryDialog v-model="deleteCategoryDialogOpen" :category="deleteCategoryTarget" @deleted="deleteCategoryDialogOpen = false" />

    <QuickCreateDialog
      v-model="quickCreateDialogOpen"
      :product="quickCreateTargetProduct"
      @saved="onQuickCreateDone"
    />

    <MaintenanceDialog v-model="maintenanceDialogOpen" :task="maintenanceEditing" :mode="maintenanceDialogMode" :initial-device-id="maintenanceInitialDeviceId" @saved="onMaintenanceSaved" />
    <MaintenanceScheduleDialog v-model="maintenanceScheduleDialogOpen" :schedule="maintenanceScheduleEditing" @saved="onMaintenanceScheduleSaved" />
    <MaintenanceCompleteDialog v-model="maintenanceCompleteDialogOpen" :task="maintenanceCompleteTarget" @saved="onMaintenanceCompleteSaved" />

    <BulkProductDialog v-model="bulkProductDialogOpen" :selected-products="selectedProducts" @saved="onBulkProductsSaved" />

    <BulkDeviceDialog v-model="bulkDeviceDialogOpen" :selected-devices="selectedDevices" @saved="onBulkDevicesSaved" />

    <BulkMaintenanceDialog v-model="bulkMaintenanceDialogOpen" :selected-tasks="selectedMaintenance" @saved="onBulkMaintenanceSaved" />

    <BulkScheduleDialog v-model="bulkScheduleDialogOpen" :selected-schedules="selectedSchedules" @saved="onBulkSchedulesSaved" />

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

    <RentalProductInfoDialog
      v-model="rentalProductInfoDialogOpen"
      :product="rentalProductInfoTarget"
      @edit-product="openEditRentalProductFromInfo"
      @open-job="openJobFromLink"
    />

    <ProductAvailabilityDialog
      v-model="productAvailabilityDialogOpen"
      :product="productAvailabilityTarget"
    />

    <ImportDialog
      v-model="importDialogOpen"
      @saved="onImportDone"
    />
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
import { normalizeCurrencyCode } from '../constants/currencies'
import { enrichInventoryExportRows, serializeRowsToCsv, serializeRowsToJson } from '../utils/export-data'

import {
  countCategoryOverview,
  countPendingMaintenance,
  findMostUsedDevice,
  findMostUsedProductByUsageDays,
  isRentalProduct
} from '../utils/inventory-overview'
import { api } from '../boot/axios'
import DefectReportDialog from 'components/DefectReportDialog.vue'
import RentalProductDialog from '../components/RentalProductDialog.vue'
import RentalProductInfoDialog from '../components/RentalProductInfoDialog.vue'
import ProductAvailabilityDialog from '../components/ProductAvailabilityDialog.vue'
import MaintenanceDialog from '../components/MaintenanceDialog.vue'
import MaintenanceScheduleDialog from '../components/MaintenanceScheduleDialog.vue'
import MaintenanceCompleteDialog from '../components/MaintenanceCompleteDialog.vue'
import BulkProductDialog from '../components/BulkProductDialog.vue'
import BulkDeviceDialog from '../components/BulkDeviceDialog.vue'
import BulkMaintenanceDialog from '../components/BulkMaintenanceDialog.vue'
import BulkScheduleDialog from '../components/BulkScheduleDialog.vue'
import CategoryDialog from '../components/CategoryDialog.vue'
import DeleteCategoryDialog from '../components/DeleteCategoryDialog.vue'
import LocationDialog from '../components/LocationDialog.vue'
import BulkCreateDialog from '../components/BulkCreateDialog.vue'
import QuickCreateDialog from '../components/QuickCreateDialog.vue'
import ImportDialog from '../components/ImportDialog.vue'
import BulkDeleteDialog from '../components/BulkDeleteDialog.vue'

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
const defectDialogOpen = ref(false)
const selectedDeviceId = ref(null)

function openDefectDialog(deviceId) {
  selectedDeviceId.value = deviceId
  defectDialogOpen.value = true
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
const rentalProductDialogOpen = ref(false)
const rentalProductEditing = ref(null)

const bulkProductDialogOpen = ref(false)
const bulkDeviceDialogOpen = ref(false)
const bulkMaintenanceDialogOpen = ref(false)
const bulkScheduleDialogOpen = ref(false)

const productTypeOptions = [
  { label: t('inventory.productTypeEquipment'), value: 'equipment' },
  { label: t('inventory.productTypeAccessory'), value: 'accessory' },
  { label: t('inventory.productTypeConsumable'), value: 'consumable' },
  { label: t('inventory.productTypeCase'), value: 'case' },
]

const DEVICE_STATUS_KEY_MAP = { available: 'Available', reserved: 'Reserved', in_use: 'InUse', maintenance: 'Maintenance' }
const statusOptions = DEVICE_STATUSES.map(item => ({ label: t('inventory.deviceStatus' + DEVICE_STATUS_KEY_MAP[item.value]), value: item.value }))
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
  { label: t('inventory.maintenanceTypeModification'), value: 'modification' },
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

function openCreateRentalProduct() {
  rentalProductEditing.value = null
  rentalProductDialogOpen.value = true
}

function openEditRentalProduct(product) {
  rentalProductEditing.value = product
  rentalProductDialogOpen.value = true
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

const productById = computed(() => {
  const map = new Map()
  for (const product of store.products) map.set(product.id, product)
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
  const deviceStatus = String(route.query.deviceStatus || '').trim().toLowerCase()
  const hasDeviceStatusFilter = ['available', 'reserved', 'in_use', 'maintenance'].includes(deviceStatus)

  if (hasDeviceStatusFilter) {
    tab.value = 'devices'
    deviceSearch.value = deviceStatus
  }

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

  if (focusProductId || focusDeviceId || focusLocationId || hasDeviceStatusFilter) {
    const nextQuery = { ...route.query }
    delete nextQuery.focusProductId
    delete nextQuery.focusDeviceId
    delete nextQuery.focusLocationId
    delete nextQuery.deviceStatus
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
  () => [route.query.focusProductId, route.query.focusDeviceId, route.query.focusLocationId, route.query.deviceStatus, route.query.tab],
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

function onRentalProductDialogSaved() {
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

function statusLabel(value) {
  const mapping = {
    available: t('inventory.deviceStatusAvailable'),
    reserved: t('inventory.deviceStatusReserved'),
    in_use: t('inventory.deviceStatusInUse'),
    maintenance: t('inventory.deviceStatusMaintenance'),
  }
  return mapping[value] || value
}

function conditionColor(condition) {
  if (condition === 'damaged') return 'negative'
  if (condition === 'fair') return 'warning'
  if (condition === 'good') return 'positive'
  return 'grey-7'
}

function conditionLabel(value) {
  const mapping = {
    good: t('inventory.conditionGood'),
    fair: t('inventory.conditionFair'),
    damaged: t('inventory.conditionDamaged'),
  }
  return mapping[value] || value || t('inventory.infoDialogs.notAvailable')
}

function zoneTypeLabel(value) {
  const mapping = {
    rack: t('inventory.zoneTypeRack'),
    shelf: t('inventory.zoneTypeShelf'),
    bin: t('inventory.zoneTypeBin'),
    pallet: t('inventory.zoneTypePallet'),
    stage: t('inventory.zoneTypeStage'),
    truck: t('inventory.zoneTypeTruck'),
    warehouse: t('inventory.zoneTypeWarehouse'),
    workshop: t('inventory.zoneTypeWorkshop'),
  }
  return mapping[value] || value
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
const maintenanceInitialDeviceId = ref(null)
const maintenanceScheduleDialogOpen = ref(false)
const maintenanceScheduleEditing = ref(null)
const maintenanceCompleteDialogOpen = ref(false)
const maintenanceCompleteTarget = ref(null)

function openCreateMaintenance(mode = 'schedule', preferredDeviceId = null) {
  maintenanceDialogMode.value = mode === 'task' ? 'task' : 'schedule'
  maintenanceEditing.value = null
  maintenanceInitialDeviceId.value = preferredDeviceId || null
  maintenanceDialogOpen.value = true
}

function openEditMaintenance(item) {
  maintenanceEditing.value = item
  maintenanceDialogOpen.value = true
}

async function openEditMaintenanceSchedule(item) {
  const scheduleId = Number(item?.schedule_id || item?.id || 0)
  if (!scheduleId) return
  try {
    const schedule = await store.fetchMaintenanceSchedule(scheduleId)
    maintenanceScheduleEditing.value = schedule
    maintenanceScheduleDialogOpen.value = true
  } catch (error) {
    $q.notify({ type: 'negative', message: error?.response?.data?.detail || 'Failed to load maintenance schedule' })
  }
}

async function completeMaintenanceRow(item) {
  maintenanceCompleteTarget.value = item || null
  maintenanceCompleteDialogOpen.value = true
}

function onMaintenanceSaved() {
  maintenanceDialogOpen.value = false
  maintenanceEditing.value = null
}

function onMaintenanceScheduleSaved() {
  maintenanceScheduleDialogOpen.value = false
  maintenanceScheduleEditing.value = null
}

function onMaintenanceCompleteSaved() {
  maintenanceCompleteDialogOpen.value = false
  maintenanceCompleteTarget.value = null
}

function selectedRowIds(rows) {
  return [...new Set((rows || []).map(row => Number(row?.id || 0)).filter(Boolean))]
}

function downloadExportFile(content, filename, mimeType) {
  if (typeof window === 'undefined' || typeof document === 'undefined') return
  const blob = new Blob([content], { type: mimeType })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  try {
    link.click()
  } finally {
    link.remove()
    window.setTimeout(() => {
      window.URL.revokeObjectURL(url)
    }, 0)
  }
}

function createExportTimestamp(date = new Date()) {
  return [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, '0'),
    String(date.getDate()).padStart(2, '0'),
    '-',
    String(date.getHours()).padStart(2, '0'),
    String(date.getMinutes()).padStart(2, '0'),
    String(date.getSeconds()).padStart(2, '0'),
  ].join('')
}

async function runDataExport(entity, rows, format) {
  const baseRows = enrichInventoryExportRows(entity, rows, {
    productById: productById.value,
    zoneById: zoneById.value,
    customFieldValuesByEntityId: new Map(),
  })
  if (!baseRows.length) {
    $q.notify({ type: 'warning', message: t('inventory.noDataToExport') })
    return
  }

  let customFieldValuesByEntityId = new Map()
  if (entity === 'products' || entity === 'devices') {
    try {
      const result = await customFieldsStore.fetchAllValues('product')
      const raw = result?.values_by_entity_id ?? {}
      for (const [idStr, vals] of Object.entries(raw)) {
        customFieldValuesByEntityId.set(Number(idStr), vals)
      }
    } catch {
      // proceed without custom fields if the request fails
    }
  }

  const enrichedRows = enrichInventoryExportRows(entity, rows, {
    productById: productById.value,
    zoneById: zoneById.value,
    customFieldValuesByEntityId,
  })

  const normalizedFormat = String(format || '').toLowerCase()
  const timestamp = createExportTimestamp()
  const extension = normalizedFormat === 'json' ? 'json' : 'csv'
  const filename = `${entity}-${timestamp}.${extension}`
  const content = normalizedFormat === 'json' ? serializeRowsToJson(enrichedRows) : serializeRowsToCsv(enrichedRows)
  const mimeType = normalizedFormat === 'json' ? 'application/json;charset=utf-8' : 'text/csv;charset=utf-8'
  downloadExportFile(content, filename, mimeType)
}

function exportProducts(format, scope = 'all') {
  const rows = scope === 'selected' ? selectedProducts.value : filteredProducts.value
  runDataExport('products', rows, format)
}

function exportDevices(format, scope = 'all') {
  const rows = scope === 'selected' ? selectedDevices.value : filteredDevices.value
  runDataExport('devices', rows, format)
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
  bulkProductDialogOpen.value = true
}

function onBulkProductsSaved() {
  selectedProducts.value = []
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
  bulkDeviceDialogOpen.value = true
}

function onBulkDevicesSaved() {
  selectedDevices.value = []
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
  bulkMaintenanceDialogOpen.value = true
}

function onBulkMaintenanceSaved() {
  selectedMaintenance.value = []
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
  bulkScheduleDialogOpen.value = true
}

function onBulkSchedulesSaved() {
  selectedSchedules.value = []
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

function openCreateCategory() {
  categoryEditing.value = null
  categoryDialogOpen.value = true
}

function openEditCategory(category) {
  categoryEditing.value = category
  categoryDialogOpen.value = true
}

const locationDialogOpen = ref(false)
const locationEditing = ref(null)

function openCreateLocation() {
  locationEditing.value = null
  locationDialogOpen.value = true
}

function openEditLocation(zone) {
  locationEditing.value = zone
  locationDialogOpen.value = true
}

const bulkCreateDialogOpen = ref(false)
const bulkCreateParent = ref(null)

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
  bulkCreateDialogOpen.value = true
}

const deleteCategoryDialogOpen = ref(false)
const deleteCategoryTarget = ref(null)
const draggingCategoryId = ref(null)
const draggingLocationId = ref(null)

const quickCreateDialogOpen = ref(false)
const quickCreateTargetProduct = ref(null)

function openQuickCreateDevices(product) {
  quickCreateTargetProduct.value = product
  quickCreateDialogOpen.value = true
}

function onQuickCreateDone() {
  quickCreateTargetProduct.value = null
}

const importDialogOpen = ref(false)

const bulkDeleteDialogOpen = ref(false)

function selectNodeAndChildren(node) {
  const ids = []
  function walk(n) {
    ids.push(n.id)
    for (const c of n.children || []) walk(c)
  }
  walk(node)
  selectedLocationIds.value = ids
}

function openImportDialog() {
  importDialogOpen.value = true
}

function onImportDone() {
  loadAll()
}

function onBulkDeleteLocationsDone() {
  selectedLocationIds.value = []
}

function confirmDeleteCategory(category) {
  deleteCategoryTarget.value = category
  deleteCategoryDialogOpen.value = true
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
