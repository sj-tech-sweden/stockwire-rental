# Job Filters Improvement Plan

## Context

The Jobs page currently has two filters: a single-select status chip toggle and a text search input. Users cannot select multiple statuses at once (e.g. view "Draft + Confirmed" together), and there are no filters for customer, venue, project, or date range despite these being available as table columns. All filtering is client-side against the full jobs dataset.

## Goal

Replace the current filter bar with an improved multi-select status filter plus additional dropdown/date filters, consistent with established patterns in the codebase (FinancePage apply/reset style, InventoryPage dropdown style).

## Design Decisions

- **Multi-select status**: `q-select multiple use-chips` (consistent with WarehouseLedsSettings zone picker)
- **Dropdown filters**: `q-select clearable emit-value map-options outlined dense` (consistent with InventoryPage, MaintenancePage)
- **Date range**: `q-input type="date` (consistent with FinancePage)
- **Layout**: Compact filter row above the table, search stays alongside
- **No backend changes**: All filtering stays client-side (data is already fetched in bulk)
- **No Apply/Reset buttons**: Filters apply instantly (consistent with existing JobsPage behavior; FinancePage's apply/reset is for server-side queries)

## Filter Controls

| Filter | Component | State | Options Source |
|--------|-----------|-------|----------------|
| Status | `q-select multiple use-chips` | `selectedStatuses` ref `[]` | `statusFilters` computed from `JOB_STATUSES` |
| Customer | `q-select clearable` | `filterCustomerId` ref `null` | `customersStore.customers` → `{ label, value }` |
| Venue | `q-select clearable` | `filterVenueId` ref `null` | `venuesStore.venues` → `{ label, value }` |
| Project | `q-select clearable` | `filterProjectIdLocal` ref `null` | `projectsStore.projects` → `{ label, value }` |
| Start date from | `q-input type="date` clearable | `filterStartDateFrom` ref `''` | N/A |
| Start date to | `q-input type="date` clearable | `filterStartDateTo` ref `''` | N/A |
| Search | `q-input` clearable | `search` ref `''` | N/A |

## Files to Modify

1. **`frontend/src/pages/JobsPage.vue`** — Main changes
   - Replace chip filter bar with new filter controls
   - Add new filter refs
   - Update `visibleJobs` computed to apply all filters
   - Update `applyRouteContext` for new status handling (array vs single)
   - Add `clearAllFilters` function
   - Add `hasActiveFilters` computed for showing a clear button

2. **`frontend/src/i18n/locales/en.js`** — Add filter labels
   - `jobs.filterByStatus` → "Filter by status"
   - `jobs.filterByCustomer` → "Customer"
   - `jobs.filterByVenue` → "Venue"
   - `jobs.filterByProject` → "Project"
   - `jobs.startDateFrom` → "Start from"
   - `jobs.startDateTo` → "Start to"
   - `jobs.clearFilters` → "Clear filters"
   - `jobs.noFiltersActive` → "No filters active"

3. **`frontend/src/i18n/locales/sv.js`** — Swedish translations for same keys

## Implementation Details

### New filter refs (replacing `activeFilter`)

```js
const selectedStatuses = ref([])          // multi-select status
const filterCustomerId = ref(null)        // customer dropdown
const filterVenueId = ref(null)           // venue dropdown
const filterProjectIdLocal = ref(null)    // project dropdown
const filterStartDateFrom = ref('')       // date range start
const filterStartDateTo = ref('')         // date range end
const search = ref('')                    // text search (existing)
```

### Updated `visibleJobs` computed

```js
const visibleJobs = computed(() => {
  const term = search.value.trim().toLowerCase()
  return jobsWithProject.value.filter(job => {
    // URL-based project filter (from ProjectsPage link)
    if (filterProjectId.value && job.project_id !== filterProjectId.value) return false
    // Multi-status filter
    if (selectedStatuses.value.length && !selectedStatuses.value.includes(job.status)) return false
    // Customer filter
    if (filterCustomerId.value && job.customer_id !== filterCustomerId.value) return false
    // Venue filter
    if (filterVenueId.value && job.venue_id !== filterVenueId.value) return false
    // Project filter (page-level)
    if (filterProjectIdLocal.value && job.project_id !== filterProjectIdLocal.value) return false
    // Date range filters
    if (filterStartDateFrom.value && job.start_date < filterStartDateFrom.value) return false
    if (filterStartDateTo.value && job.start_date > filterStartDateTo.value) return false
    // Text search
    if (!term) return true
    return [job.job_code, job.description, job.customer_name, job.venue_name, job.project_name, job.status]
      .filter(Boolean)
      .some(value => String(value).toLowerCase().includes(term))
  })
})
```

### Updated `applyRouteContext`

Change from setting a single `activeFilter` to pushing to `selectedStatuses` array:

```js
if (status && JOB_STATUSES.some(item => item.value === status)) {
  selectedStatuses.value = [status]
}
```

### Filter option computeds

```js
const customerOptions = computed(() =>
  customersStore.customers.map(c => ({ label: c.name, value: c.id })).sort((a, b) => a.label.localeCompare(b.label))
)
const venueOptions = computed(() =>
  venuesStore.venues.map(v => ({ label: v.name, value: v.id })).sort((a, b) => a.label.localeCompare(b.label))
)
const projectOptions = computed(() =>
  projectsStore.projects.map(p => ({ label: p.name, value: p.id })).sort((a, b) => a.label.localeCompare(b.label))
)
const statusOptions = computed(() =>
  statusFilters.value.map(s => ({ label: s.label, value: s.value }))
)
```

### Template layout

```html
<div class="row q-col-gutter-sm q-mb-md items-end">
  <!-- Status multi-select -->
  <div class="col-12 col-sm-6 col-md-3">
    <q-select v-model="selectedStatuses" :options="statusOptions" emit-value map-options
      outlined dense use-chips multiple :label="t('jobs.filterByStatus')" clearable />
  </div>
  <!-- Customer -->
  <div class="col-12 col-sm-6 col-md-3">
    <q-select v-model="filterCustomerId" :options="customerOptions" emit-value map-options
      outlined dense clearable :label="t('jobs.filterByCustomer')" />
  </div>
  <!-- Venue -->
  <div class="col-12 col-sm-6 col-md-3">
    <q-select v-model="filterVenueId" :options="venueOptions" emit-value map-options
      outlined dense clearable :label="t('jobs.filterByVenue')" />
  </div>
  <!-- Project -->
  <div class="col-12 col-sm-6 col-md-3">
    <q-select v-model="filterProjectIdLocal" :options="projectOptions" emit-value map-options
      outlined dense clearable :label="t('jobs.filterByProject')" />
  </div>
  <!-- Date from -->
  <div class="col-6 col-sm-3 col-md-2">
    <q-input v-model="filterStartDateFrom" type="date" outlined dense clearable :label="t('jobs.startDateFrom')" />
  </div>
  <!-- Date to -->
  <div class="col-6 col-sm-3 col-md-2">
    <q-input v-model="filterStartDateTo" type="date" outlined dense clearable :label="t('jobs.startDateTo')" />
  </div>
  <!-- Search -->
  <div class="col-12 col-sm-6 col-md-3">
    <q-input v-model="search" dense outlined clearable :placeholder="t('jobs.searchJobs')">
      <template #prepend><q-icon name="search" /></template>
    </q-input>
  </div>
  <!-- Clear all -->
  <div v-if="hasActiveFilters" class="col-auto">
    <q-btn flat dense color="negative" icon="filter_alt_off" :label="t('jobs.clearFilters')" @click="clearAllFilters" />
  </div>
</div>
```

### `clearAllFilters` function

```js
function clearAllFilters() {
  selectedStatuses.value = []
  filterCustomerId.value = null
  filterVenueId.value = null
  filterProjectIdLocal.value = null
  filterStartDateFrom.value = ''
  filterStartDateTo.value = ''
  search.value = ''
}
```

### `hasActiveFilters` computed

```js
const hasActiveFilters = computed(() =>
  selectedStatuses.value.length > 0 ||
  filterCustomerId.value !== null ||
  filterVenueId.value !== null ||
  filterProjectIdLocal.value !== null ||
  filterStartDateFrom.value !== '' ||
  filterStartDateTo.value !== '' ||
  search.value.trim() !== ''
)
```

## Verification

1. Run `npm run lint` in `frontend/` to check for lint errors
2. Manual testing:
   - Multi-status: Select multiple statuses, verify jobs with any selected status appear
   - Customer/Venue/Project dropdowns: Select, verify filtering works; clear, verify all return
   - Date range: Set from/to, verify only jobs within range appear
   - Clear button: Appears when any filter active, clears all on click
   - URL query `?status=in_progress`: Should still pre-select that status in the multi-select
   - Search: Combined with other filters, works correctly
