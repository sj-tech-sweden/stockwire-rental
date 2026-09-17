# Stockwire Page Templates for Penpot

These templates describe the current Stockwire interface so you can redesign and improve it in Penpot while reusing the shared library.

Create one Penpot page per template area and link them together with prototype flows.

## Global layout

All authenticated pages share:

- **Left drawer** (persistent on desktop, overlay on mobile)
  - Logo mark at top
  - Navigation groups: Operations, Inventory, Planning, Admin
  - Active item highlight
- **Top header** (60px)
  - Page title
  - Global search (optional)
  - Theme toggle, notifications, user menu
- **Page container**
  - Background: `ec-bg` gradient
  - Padding: 16px desktop, 8px mobile

## 1. Dashboard

**Route:** `/`

### Sections

1. **Stats row**
   - 4 metric cards: Open jobs, Available devices, Pending maintenance, Today's scans
   - Card: Default Card
   - Metric value: `Heading / H2`
   - Label: `Body / Muted`
2. **Quick actions**
   - Primary button: New job
   - Secondary buttons: Scan, Create product
3. **Recent activity**
   - Table with 5 rows
   - Columns: Time, User, Action, Entity
4. **Upcoming jobs**
   - Card list with job name, customer, date, status chip

### Improvement ideas

- Add a **warehouse snapshot** mini-map showing highlighted bins.
- Show **offline queue status** when mutations are pending.
- Surface **crew availability** for today's jobs.

## 2. Inventory

**Route:** `/inventory`

### Sections

1. **Toolbar**
   - Search input
   - Filter chips (Category, Status, Location)
   - Primary: Add product
   - Secondary: Bulk actions
2. **Tabs**
   - Products, Devices, Zones, Categories
3. **Data table**
   - Table Header / Table Row
   - Actions column with icon buttons
4. **Empty state**
   - Illustration + muted text + primary CTA

### Improvement ideas

- Add a **compact density toggle**.
- Show **availability timeline** inline for rental products.
- Use the **cable motif** as a subtle background on empty states.

## 3. Jobs

**Route:** `/jobs`

### Sections

1. **Toolbar**
   - Search, date range, status filter
   - Primary: New job
2. **Job list / Kanban toggle**
   - Default: table
   - Optional Kanban by status
3. **Job row**
   - Name, customer, dates, crew count, status chip

### Improvement ideas

- Add a **calendar view** alongside the list.
- Highlight jobs with **conflicts or missing requirements**.
- Drag-and-drop assignment from crew sidebar.

## 4. Job Detail

**Route:** `/jobs/:jobId`

### Sections

1. **Header**
   - Job name, customer, dates
   - Status chip
   - Actions: Edit, Duplicate, Delete
2. **Tabs**
   - Details, Requirements, Crew, Route, Attachments
3. **Requirements panel**
   - Product requirements list
   - Rental requirements list
   - Add requirement button
4. **Crew panel**
   - Assigned crew cards

### Improvement ideas

- Show a **packing progress bar**.
- Add a **route map preview** tab.
- Surface **missing certifications** for assigned crew.

## 5. Scan

**Route:** `/scan`

### Sections

1. **Scanner target**
   - Large tap area for camera trigger
   - Manual barcode input fallback
2. **Recent scans**
   - List of last 5 scan results
3. **Action buttons**
   - Check in, Check out, Move, Inspect

### Improvement ideas

- Add **haptic-compatible feedback states**.
- Use **extra-large input targets** (min 64px touch targets).
- Show **device thumbnail** after successful scan.

## 6. Settings

**Route:** `/settings`

### Sections

1. **Sidebar tabs**
   - General, Integrations, Storage, Auth, Users, Notifications
2. **Form panels**
   - Outlined inputs
   - Toggles
   - Save / Cancel actions

### Improvement ideas

- Add **integration health indicators** (connected/disconnected).
- Group related settings into **cards**.
- Show **validation hints** inline.

## 7. Route Planner

**Route:** `/route-planner`

### Sections

1. **Vehicle selector**
   - Dropdown / cards
2. **Stops list**
   - Draggable rows
3. **Map preview**
   - Static or embedded map
4. **Export actions**
   - Google Maps export button

### Improvement ideas

- Show **estimated drive time** per stop.
- Highlight jobs that don't fit vehicle capacity.
- Optimize route button using external service.

## 8. Maintenance

**Route:** `/maintenance`

### Sections

1. **Tabs:** Maintenance tasks / Defects
2. **Table or card list**
3. **Priority chips:** High, Medium, Low
4. **Action:** Mark complete, Schedule

### Improvement ideas

- Add a **defect photo gallery**.
- Show **maintenance history** per device.
- Calendar view for scheduled maintenance.

## Prototype flows to test

1. **Create job flow:** Dashboard → New job → Add requirements → Assign crew → Save
2. **Scan flow:** Dashboard → Scan → Scan device → Choose action → Confirm
3. **Resolve defect flow:** Maintenance → Defect → Add photo → Mark complete
4. **Settings integration flow:** Settings → Integrations → Connect Eventory → Test connection

Use these flows to validate that the component library and spacing system hold together across real screens.
