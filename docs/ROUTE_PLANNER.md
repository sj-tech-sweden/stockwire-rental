# Route Planner

> Last reviewed: 2026-08-06

## Overview

The Route Planner module enables delivery route planning with multi-vehicle support, stop management, and Google Maps integration.

**Frontend:** `/route-planner` (RoutePlannerPage.vue)  
**Backend:** `/api/v1/route-planner/*`

---

## Features

- **Vehicle Management** - Define and manage delivery vehicles
- **Route Planning** - Create routes with multiple stops
- **Multi-Vehicle Support** - Assign multiple vehicles to a single route
- **Stop Management** - Add, reorder, and assign stops to vehicles
- **Vehicle Suggestions** - Get AI-powered vehicle suggestions based on load
- **Google Maps Export** - Export routes to Google Maps for navigation
- **Packing Lists** - Generate packing lists per route or vehicle

---

## Concepts

### Vehicles

Vehicles represent physical delivery assets:

- **Trucks** - Large delivery vehicles
- **Vans** - Medium delivery vehicles
- **Trailers** - Towable cargo units

Each vehicle has capacity constraints:
- Weight capacity (kg)
- Volume capacity (m³)

### Routes

Routes are collections of stops organized for a specific date:

- A route can have multiple vehicles
- Each stop can be assigned to a specific vehicle
- Stops have a type: `pickup` or `delivery`
- Routes have statuses: `planned`, `in_progress`, `completed`

### Stops

Stops represent locations to visit:

- Linked to a venue (address)
- Linked to a job (for context)
- Assigned to a vehicle
- Ordered by `sort_order`

---

## UI Overview

### Vehicle Management

1. Click "Add Vehicle" to create a new vehicle
2. Fill in vehicle details (name, type, capacity)
3. Vehicles appear in the sidebar list
4. Click vehicle to edit, click trash to delete

### Route Planning

1. Click "New Route" to create a route
2. Set route name and date
3. Add stops by clicking "Add Stop"
4. Select venue for each stop
5. Assign vehicle to each stop
6. Drag to reorder stops
7. Click "Save Route"

### Vehicle Suggestions

1. After adding stops, click "Suggest Vehicles"
2. System analyzes load requirements
3. Recommends optimal vehicle combination
4. Click "Apply" to assign vehicles

### Google Maps Export

1. Open a route
2. Click "Export to Google Maps"
3. Opens Google Maps with all stops
4. Get turn-by-turn directions

### Packing Lists

1. Open a route
2. Click "Packing List"
3. View all items needed for route
4. Print or export list

---

## API Endpoints

### Vehicles

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/route-planner/vehicles` | List all vehicles |
| `POST` | `/route-planner/vehicles` | Create vehicle |
| `PUT` | `/route-planner/vehicles/{id}` | Update vehicle |
| `DELETE` | `/route-planner/vehicles/{id}` | Delete vehicle |

### Routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/route-planner/routes` | List all routes |
| `GET` | `/route-planner/routes/{id}` | Get route with stops |
| `POST` | `/route-planner/routes` | Create route |
| `PUT` | `/route-planner/routes/{id}` | Update route |
| `DELETE` | `/route-planner/routes/{id}` | Delete route |

### Route Vehicles

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/route-planner/routes/{id}/vehicles` | Add vehicle to route |
| `PUT` | `/route-planner/routes/{id}/vehicles/reorder` | Reorder vehicles |
| `DELETE` | `/route-planner/routes/{id}/vehicles/{vid}` | Remove vehicle |

### Route Stops

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/route-planner/routes/{id}/stops` | Add stop to route |
| `PUT` | `/route-planner/routes/{id}/stops/reorder` | Reorder stops |
| `DELETE` | `/route-planner/routes/{id}/stops/{sid}` | Remove stop |
| `PUT` | `/route-planner/routes/{id}/stops/{sid}/vehicle` | Assign vehicle to stop |

### Suggestions & Export

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/route-planner/suggest-vehicles` | Get vehicle suggestions |
| `POST` | `/route-planner/export-google-maps` | Export to Google Maps |
| `GET` | `/route-planner/routes/{id}/packing-list` | Get packing list |

---

## Data Model

### Vehicle

```json
{
  "id": "uuid",
  "name": "Truck 1",
  "type": "truck",
  "capacity_kg": 5000,
  "capacity_m3": 20,
  "license_plate": "ABC-1234",
  "notes": "Main delivery truck",
  "created_at": "2026-08-06T10:00:00Z"
}
```

### Route

```json
{
  "id": "uuid",
  "name": "Downtown Deliveries",
  "date": "2026-08-07",
  "status": "planned",
  "vehicles": [...],
  "stops": [...],
  "notes": "Monday route",
  "created_at": "2026-08-06T10:00:00Z"
}
```

### Stop

```json
{
  "id": "uuid",
  "route_id": "uuid",
  "venue_id": "uuid",
  "job_id": "uuid",
  "vehicle_id": "uuid",
  "sort_order": 1,
  "type": "delivery",
  "status": "pending",
  "notes": "Ring bell twice",
  "created_at": "2026-08-06T10:00:00Z"
}
```

---

## Workflow Example

1. **Create Vehicles**
   - Add "Truck A" (capacity: 3000kg, 15m³)
   - Add "Van B" (capacity: 1000kg, 6m³)

2. **Create Route**
   - Name: "Friday Deliveries"
   - Date: 2026-08-08

3. **Add Stops**
   - Stop 1: Customer A (delivery)
   - Stop 2: Customer B (delivery)
   - Stop 3: Supplier C (pickup)
   - Stop 4: Customer D (delivery)

4. **Assign Vehicles**
   - Use "Suggest Vehicles" or manually assign
   - Truck A: Stops 1, 2, 4
   - Van B: Stop 3

5. **Export & Execute**
   - Export to Google Maps
   - Driver follows route
   - Mark stops as completed

6. **Review**
   - View packing list
   - Check completion status
   - Generate delivery reports

---

## Integration with Jobs

- Stops can be linked to jobs
- Packing lists pull job requirements
- Route completion updates job status
- Activity log tracks route changes

---

## Limitations

- No real-time traffic integration
- No automatic route optimization (manual or suggestion-based)
- No driver assignment (vehicle-focused)
- No multi-day route planning
