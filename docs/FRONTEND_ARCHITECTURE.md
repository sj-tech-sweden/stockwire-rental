# Frontend Architecture

> Last reviewed: 2026-08-06

## Overview

Stockwire Rental frontend is a Quasar Framework (Vue 3) application configured as a Progressive Web App (PWA) with offline-first capabilities.

**Stack:**
- Vue 3 + Composition API
- Quasar Framework v2.18 (UI components)
- Pinia v4 (state management)
- Vue Router v5 (routing)
- Vue I18n v11 (internationalization)
- Orbit.js v0.17 (offline-first data sync)
- Axios v1.9 (HTTP client)
- Vitest v4 (unit testing)
- Playwright v1.60 (E2E testing)

---

## Directory Structure

```
frontend/src/
├── boot/                    # Quasar boot files (app initialization)
├── components/              # 66 Vue components
├── composables/             # Vue composables (reusable logic)
├── constants/               # Static data constants
├── css/                     # Global styles
├── i18n/                    # Internationalization files
├── layouts/                 # Layout wrappers
├── pages/                   # 26 page components
├── router/                  # Vue Router config
├── services/                # Service layer (API, offline, realtime)
├── stores/                  # 16 Pinia stores
└── utils/                   # Utility functions
```

---

## Boot Sequence

Boot files execute in order at app startup:

1. `axios.js` - Axios instance with token refresh interceptor
2. `i18n.js` - Vue I18n initialization
3. `theme.js` - Theme management (dark mode)
4. `force-header-theme.js` - Forces dark/light header theme
5. `realtime-sync.js` - WebSocket connection for live updates
6. `orbit-sync.js` - Offline-first IndexedDB initialization
7. `metrics.js` - Frontend telemetry setup

---

## Pages (26)

| Page | Route | Description |
|------|-------|-------------|
| `HomePage.vue` | `/` | Dashboard with overview stats |
| `LoginPage.vue` | `/login` | Email/password login |
| `SetupPage.vue` | `/setup` | Initial admin setup |
| `ForgotPasswordPage.vue` | `/forgot-password` | Password reset request |
| `ResetPasswordPage.vue` | `/reset-password/:token` | Password reset form |
| `InventoryPage.vue` | `/inventory` | Products, devices, zones, categories |
| `JobsPage.vue` | `/jobs` | Job listing |
| `JobDetailPage.vue` | `/jobs/:jobId` | Job details and requirements |
| `ProjectsPage.vue` | `/projects` | Project listing |
| `CompaniesPage.vue` | `/companies` | Customers and suppliers |
| `CustomerDetailPage.vue` | `/companies/:customerId` | Customer details |
| `CrewPage.vue` | `/crew` | Crew member listing |
| `CrewDetailPage.vue` | `/crew/:crewMemberId` | Crew member details |
| `VenuesPage.vue` | `/venues` | Venue listing |
| `LabelsPage.vue` | `/labels` | Label template management |
| `ScanPage.vue` | `/scan` | Barcode/QR scanning |
| `MaintenancePage.vue` | `/maintenance` | Maintenance and defects |
| `ActivityPage.vue` | `/activity` | Audit/activity log |
| `FinancePage.vue` | `/finance` | Financial transactions |
| `SettingsPage.vue` | `/settings` | App settings (admin only) |
| `UsersPage.vue` | `/users` | User management (admin only) |
| `ProfilePage.vue` | `/profile` | Current user profile |
| `RoutePlannerPage.vue` | `/route-planner` | Route planning |
| `WarehouseLedsPage.vue` | *(not routed)* | LED controller management |

**Redirects:**
- `/defects` → `/maintenance`
- `/auth` → `/settings?tab=auth`
- `/customers` → `/companies`
- `/suppliers` → `/companies?tab=product_supplier`

---

## Components (66)

### Dialog Components (55)

Dialogs are the primary UI pattern for CRUD operations. Most data entry happens through modal dialogs.

**Auth/User Management:**
- `AuthUserDialog` - Create/edit users (admin)
- `AuthDeleteUserDialog` - Confirm user deletion
- `SettingsUserDialog` - User settings variant
- `SettingsDeleteUserDialog` - Delete confirmation variant
- `ApiKeyDialog` - Create/manage API keys

**Inventory - Products:**
- `ProductDialog` - Create/edit products
- `ProductInfoDialog` - View product details
- `ProductAvailabilityDialog` - Check product availability
- `ProductLocationMapDialog` - Product location visualization
- `RentalProductDialog` - Create/edit rental products
- `RentalProductInfoDialog` - View rental product details
- `CategoryDialog` - Create/edit categories
- `DeleteCategoryDialog` - Confirm category deletion

**Inventory - Devices:**
- `DeviceDialog` - Create/edit devices
- `DeviceInfoDialog` - View device details
- `LocateDeviceMapDialog` - Device location on warehouse map
- `BulkDeviceDialog` - Bulk device operations

**Inventory - Zones/Locations:**
- `LocationDialog` - Create/edit locations
- `ZoneCrossSectionDialog` - 3D zone cross-section view
- `ZonePropertiesDialog` - Edit zone properties
- `GenerateShelvesDialog` - Auto-generate shelf locations
- `BulkZoneDialog` - Bulk zone operations

**Inventory - Bulk Operations:**
- `BulkCreateDialog` - Bulk create items
- `BulkDeleteDialog` - Bulk delete confirmation
- `BulkMaintenanceDialog` - Bulk maintenance operations
- `BulkProductDialog` - Bulk product operations
- `BulkScheduleDialog` - Bulk schedule operations

**Jobs:**
- `JobInfoDialog` - View job details
- `JobDeleteDialog` - Confirm job deletion
- `JobPickerDialog` - Select existing job
- `JobCustomFieldsDialog` - Manage job custom fields
- `JobProductRequirementDialog` - Add product requirements
- `JobRentalRequirementDialog` - Add rental requirements

**Customers:**
- `CustomerDialog` - Create/edit customers
- `CustomerDeleteDialog` - Confirm customer deletion
- `CustomerPickerDialog` - Select customer
- `CustomerCustomFieldsDialog` - Manage customer custom fields

**Crew:**
- `CrewAssignmentDialog` - Assign crew to job
- `CrewRequirementDialog` - Add crew requirements

**Venues:**
- `VenueDialog` - Create/edit venues
- `VenueDeleteDialog` - Confirm venue deletion
- `VenuePickerDialog` - Select venue

**Projects:**
- `ProjectDialog` - Create/edit projects
- `ProjectDeleteDialog` - Confirm project deletion

**Maintenance:**
- `MaintenanceDialog` - Create/edit maintenance
- `MaintenanceCompleteDialog` - Mark maintenance complete
- `MaintenanceScheduleDialog` - Schedule maintenance
- `DefectReportDialog` - Create/edit defect reports

**Finance:**
- `TransactionDialog` - Create/edit transactions

**Settings:**
- `CalendarFeedsSettings` - Calendar feed configuration
- `WarehouseLedsSettings` - LED controller settings
- `ShortcutHelpDialog` - Keyboard shortcuts help

**Scan/Import:**
- `FieldScanDialog` - Barcode/QR scanning
- `ImportDialog` - Data import

**Other:**
- `QuickCreateDialog` - Quick entity creation
- `PackingListDialog` - View packing list
- `VehicleDialog` - Create/edit vehicles
- `VehicleSuggestionDialog` - Vehicle suggestions

### Inline Components (4)

- `CustomerCreateInline` - Inline customer creation form
- `SupplierPickerInline` - Inline supplier selection
- `VenueCreateInline` - Inline venue creation form
- `SkillAutocomplete` - Autocomplete for crew skills

### UI/Panel Components (5)

- `AssistantDrawer` - AI assistant side drawer
- `EntityAttachmentsPanel` - Attachment management panel
- `FieldDialog` - Custom field editor
- `WarehouseMap` - Warehouse visual map
- `CalendarFeedsSettings` - Calendar iCal feed configuration

---

## Pinia Stores (16)

| Store | ID | Purpose |
|-------|----|---------|
| `auth.js` | `auth` | Authentication, users, API keys, SSO |
| `inventory.js` | `inventory` | Products, devices, zones, maintenance, defects, categories |
| `jobs.js` | `jobs` | Jobs and requirements |
| `customers.js` | `customers` | Companies/customers and suppliers |
| `crew.js` | `crew` | Crew roles, members, skills, certifications |
| `venues.js` | `venues` | Venues/locations |
| `projects.js` | `projects` | Projects |
| `finance.js` | `finance` | Financial transactions, summaries, job insights |
| `activity.js` | `activity` | Audit/activity log |
| `settings.js` | `settings` | App settings, location types, category prefill |
| `customFields.js` | `custom-fields` | Custom field definitions and values |
| `users.js` | `users` | User management (admin) |
| `routePlanner.js` | `routePlanner` | Vehicles and route planning |
| `assistantStore.js` | `assistant` | AI assistant chat |
| `warehouseLeds.js` | `warehouseLeds` | Warehouse LED controller management |
| `index.js` | N/A | Pinia instance creation |

---

## Offline-First Architecture

The app uses Orbit.js + IndexedDB for offline data persistence.

### Pattern

Each store follows this pattern:

```javascript
// When online, fetch from API
if (isOnline.value) {
  const data = await api.get('/inventory/products')
  await cacheSnapshot('products', data)  // Cache in IndexedDB
  return data
}

// When offline, read from IndexedDB
const cached = await readSnapshot('products')
if (cached) return cached

// Queue mutation for sync when back online
await queueMutation({
  endpoint: '/inventory/products',
  method: 'POST',
  body: newProduct
})
```

### Key Functions (from `services/offline/orbitSync.js`)

- `cacheSnapshot(entity, data)` - Store data in IndexedDB
- `readSnapshot(entity)` - Retrieve cached data
- `queueMutation(mutation)` - Queue write for later sync
- `isOnline` - Reactive online status

### IndexedDB Database

- Name: `stockwire-offline`
- Stores: One per entity type (products, devices, jobs, etc.)

---

## Realtime Updates

WebSocket client connects to `/api/v1/realtime/ws` for live updates.

### Features

- Auto-reconnect with 1.5s delay
- Subscribe/unsubscribe pattern
- Events pushed from server trigger store updates

### Usage

```javascript
// In store or component
import { useRealtimeClient } from 'services/realtime/client'

const client = useRealtimeClient()
client.subscribe('inventory', (event) => {
  // Handle real-time inventory update
})
```

---

## Routing

### Navigation Guard

The router has a `beforeEach` guard that:

1. Allows public routes (`meta.public`) through
2. Redirects unauthenticated users to `/login`
3. Redirects to `/setup` if no users exist (bootstrap)
4. Restricts `/settings` to admin role

### Route Groups

**Public (AuthLayout):**
- `/login`, `/setup`, `/forgot-password`, `/reset-password/:token`

**Authenticated (MainLayout):**
- All other routes require valid JWT

**Lazy-loaded:**
- `JobDetailPage`, `ProjectsPage`, `CustomerDetailPage`, `CrewDetailPage`
- `UsersPage`, `RoutePlannerPage`, `MaintenancePage`

---

## Internationalization (i18n)

### Locales

- English (`en.js`) - Default
- Swedish (`sv.js`) - Secondary

### Structure

```javascript
// i18n/locales/en.js
export default {
  app: {
    name: 'Stockwire Rental',
    nav: {
      inventory: 'Inventory',
      jobs: 'Jobs',
      // ...
    }
  },
  inventory: {
    products: { /* ... */ },
    devices: { /* ... */ }
  }
}
```

### Usage in Components

```vue
<template>
  <div>{{ $t('app.nav.inventory') }}</div>
</template>
```

### Adding Translations

1. Add key to `i18n/locales/en.js`
2. Add corresponding key to `i18n/locales/sv.js`
3. Use `$t('key.path')` in templates

---

## Composables

| Composable | Purpose |
|------------|---------|
| `useCompactGrid` | Compact grid layout logic |
| `useProductImage` | Product image handling |

---

## Utilities

| Utility | Purpose |
|---------|---------|
| `dashboard-links.js` | Dashboard link generation |
| `export-data.js` | Data export utilities |
| `import-data.js` | Data import utilities |
| `inventory-helpers.js` | Inventory helper functions |
| `inventory-overview.js` | Inventory overview computations |
| `job-requirements.js` | Job requirements helpers |
| `maps.js` | Map/geolocation utilities |
| `runtime-config.js` | Runtime config (API base URL) |
| `scan-camera.js` | Camera scanning utilities |
| `scan-workflow.js` | Scan workflow logic |
| `slugify.js` | URL slug generation |
| `translate-helpers.js` | Translation helper utilities |
| `twenty-links.js` | Twenty CRM quick-link generation |
| `zone-presets.js` | Warehouse zone presets |

---

## Services

| Service | Purpose |
|---------|---------|
| `metrics.js` | Frontend telemetry (page views, API timings, errors) |
| `offline/orbitSync.js` | Offline-first IndexedDB sync |
| `realtime/client.js` | WebSocket client for live updates |

---

## Testing

### Unit Tests (Vitest)

- Location: `tests/unit/`
- Environment: jsdom
- Setup: `tests/setup/indexeddb.setup.js` (fake-indexeddb)

### E2E Tests (Playwright)

- Location: `tests/e2e/`
- Projects: chromium, firefox, webkit
- Serial execution (workers: 1)

### Running Tests

```bash
# Unit tests
npm run test:smoke

# E2E tests
npm run test:e2e
```

---

## Build & Deployment

### Development

```bash
npm run dev  # Quasar dev server with PWA
```

### Production Build

```bash
npm run build  # Generates dist/ with PWA assets
```

### Docker

The frontend is served via nginx in production:

```bash
docker compose -f infra/compose/docker-compose.yml up frontend
```

---

## Key Patterns

### Dialog-Driven UI

Most CRUD operations use modal dialogs rather than separate pages. This keeps the user in context and reduces navigation overhead.

### Store-Centric Data Flow

All API calls go through Pinia stores. Components never call API directly - they dispatch actions to stores.

### Offline-First by Default

Every store action checks online status and falls back to IndexedDB when offline. Mutations are queued and synced when connectivity returns.

### Lazy Loading

Heavy pages (JobDetail, Projects, Users, RoutePlanner) are lazy-loaded to reduce initial bundle size.
