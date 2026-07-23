# Job Info Dialog — Fully Editable with Popup Sub-Dialogs

## Context

No `JobInfoDialog` exists. The user wants a single comprehensive dialog that shows all job information and allows editing everything inline, with small popup sub-dialogs for complex editing (requirements, custom fields, customer/venue selection).

## Design

The `JobInfoDialog` is a **fully editable** dialog — not read-only. It shows the job's information in a well-organized card layout. Simple fields are edited inline. Complex operations open in small popup sub-dialogs.

### Layout (scrollable card)

1. **Header** — job code (editable input), status badge (clickable to open status dropdown)
2. **Quick info row** — customer (click → popup customer picker), venue (click → popup venue picker), project (inline select), dates (inline date inputs)
3. **Description** — inline textarea
4. **Venue map** — Google Maps embed when venue has address data, with "Open in Maps" button
5. **Financials** — sales price (inline), invoice paid (toggle), invoice paid date (inline)
6. **Location in venue** — inline text
7. **Notes** — inline textarea
8. **Product requirements** — summary list + "Edit" button → opens `JobProductRequirementDialog` (existing component)
9. **Rental requirements** — summary list + "Edit" button → opens new `JobRentalRequirementDialog`
10. **Custom fields** — "Edit" button → opens `JobCustomFieldsDialog` (small popup)
11. **Documents** — `EntityAttachmentsPanel` with upload
12. **Footer** — Save + Close buttons

### Sub-Dialogs (small popups)

1. **CustomerPickerDialog** — searchable list of customers, emit selected. ~400px wide.
2. **VenuePickerDialog** — searchable list of venues, emit selected. ~400px wide.
3. **JobRentalRequirementDialog** — rental product search + qty + availability. Same pattern as `JobProductRequirementDialog` but filtered to rental products only. ~900px wide.
4. **JobCustomFieldsDialog** — renders custom field inputs (text/number/boolean/date/select). Save button commits to parent form. ~500px wide.

## New Files

### 1. `frontend/src/components/JobInfoDialog.vue`

**Props:** `modelValue: Boolean`, `job: Object`
**Emits:** `update:modelValue`, `saved`

**Key implementation:**
- Form state in a `ref` initialized from `props.job` on open (same pattern as JobDialog `openEdit`)
- All inline fields bound to the form ref
- Sub-dialogs open via boolean refs (`customerPickerOpen`, `venuePickerOpen`, etc.)
- Save function: `jobsStore.updateJob(job.id, payload)` + `jobsStore.bulkUpsertRequirements()` + `customFieldsStore.saveEntityValues()`
- Loads custom fields and requirements on open via `watch`

**Imports:**
- `useJobsStore`, `useCustomersStore`, `useVenuesStore`, `useInventoryStore`, `useCustomFieldsStore`, `useProjectsStore`, `useSettingsStore`
- `EntityAttachmentsPanel`, `JobProductRequirementDialog`
- `googleMapsEmbedUrl`, `googleMapsSearchUrl`, `locationQueryFromParts` from `../utils/maps`
- `normalizeCurrencyCode` from `../constants/currencies`
- `translateMaybePrefillCustomFieldLabel`, `translateMaybePrefillCustomFieldOption` from `../i18n/prefillContent`

### 2. `frontend/src/components/CustomerPickerDialog.vue`

**Props:** `modelValue: Boolean`, `customers: Array`, `selectedId: Number`
**Emits:** `update:modelValue`, `select(customer)`

Small popup: `q-input` search + `q-list` of filtered customers. Click to select + close.

### 3. `frontend/src/components/VenuePickerDialog.vue`

**Props:** `modelValue: Boolean`, `venues: Array`, `selectedId: Number`
**Emits:** `update:modelValue`, `select(venue)`

Same pattern as CustomerPickerDialog.

### 4. `frontend/src/components/JobRentalRequirementDialog.vue`

**Props:** `modelValue: Boolean`, `requirementRows: Array`, `products: Array`, `startDate: String`, `endDate: String`, `jobId: Number`
**Emits:** `update:modelValue`, `update:requirementRows`

Same pattern as `JobProductRequirementDialog` but filtered to rental products only (`isRentalProduct`). Shows availability badges, qty input, remove button.

### 5. `frontend/src/components/JobCustomFieldsDialog.vue`

**Props:** `modelValue: Boolean`, `jobId: Number`
**Emits:** `update:modelValue`, `save(values)`

Loads field definitions and values from `customFieldsStore`. Renders editable inputs. On save, emits the values array to parent.

## Changes to Existing Files

### `frontend/src/pages/JobsPage.vue`
- Import `JobInfoDialog`
- Add `infoDialogOpen`, `infoTarget` refs
- Add `openInfo(row)` function
- Replace double-click on table row: open info dialog instead of navigating to detail page
- Add `JobInfoDialog` to template
- Handle `@saved` to refresh data

### `frontend/src/i18n/locales/en.js` + `sv.js`
- `jobs.jobInfo` — "Job Info"
- `jobs.editRequirements` — "Edit requirements"
- `jobs.editCustomFields` — "Edit custom fields"
- `jobs.selectCustomer` — "Select customer"
- `jobs.selectVenue` — "Select venue"

## Save Flow

1. User edits inline fields → changes stored in local form ref
2. User opens sub-dialogs → edits stored in sub-dialog, emitted back to parent on save
3. User clicks main Save → `jobsStore.updateJob()` + `bulkUpsertRequirements()` + `customFieldsStore.saveEntityValues()`
4. Emit `saved` + close

## Verification

1. Open info dialog from JobsPage (eye icon or double-click)
2. Edit inline fields (status, description, dates, etc.) and save
3. Click customer name → picker opens → select customer → name updates
4. Click venue name → picker opens → select venue → name + map update
5. Edit product requirements → existing dialog opens → save → list updates
6. Edit rental requirements → new dialog opens → save → list updates
7. Edit custom fields → dialog opens → save → values persist
8. Upload document → appears in list
9. Test on phone (maximized, responsive)
