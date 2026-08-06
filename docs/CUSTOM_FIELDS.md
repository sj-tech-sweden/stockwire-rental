# Custom Fields

> Last reviewed: 2026-08-06

## Overview

Custom Fields allow users to add custom data fields to products, jobs, customers, and venues without code changes.

**Frontend:** Settings → Custom Fields  
**Backend:** `/api/v1/custom-fields/*`

---

## Features

- **Dynamic Fields** - Add fields to entities at runtime
- **Multiple Field Types** - Text, number, select, date, boolean
- **Entity Support** - Products, jobs, customers, venues
- **Required Fields** - Mark fields as mandatory
- **Bulk Operations** - Set values for multiple entities
- **Prefill Templates** - Predefined field sets for common use cases

---

## Concepts

### Field Definitions

Define the structure of custom fields:

- **Entity Type** - Which entity this field applies to
- **Name** - Display name
- **Field Type** - Data type
- **Options** - For select fields, list of choices
- **Required** - Whether field must be filled
- **Sort Order** - Display order

### Field Values

Actual data stored for each entity:

- Linked to a field definition
- Linked to an entity (type + ID)
- Stored as text (type conversion handled by frontend)

---

## Field Types

| Type | Description | Example |
|------|-------------|---------|
| `text` | Free-form text | "Special instructions" |
| `number` | Numeric value | "Weight capacity" |
| `select` | Dropdown selection | "Color: Red, Blue, Green" |
| `date` | Date picker | "Expiry date" |
| `boolean` | True/false toggle | "Requires certification" |

---

## UI Overview

### Creating Field Definitions

1. Navigate to Settings → Custom Fields
2. Select entity tab (Products, Jobs, etc.)
3. Click "Add Field"
4. Configure:
   - Name
   - Type
   - Options (for select)
   - Required toggle
5. Save

### Setting Field Values

1. Open entity (product, job, etc.)
2. Click "Custom Fields" tab
3. Fill in values
4. Save entity

### Bulk Operations

1. Select multiple entities
2. Click "Set Custom Fields"
3. Choose field and value
4. Apply to all selected

### Prefill Templates

1. Go to Settings → Custom Fields
2. Click "Prefill Product Cable"
3. Select template
4. Fields are created automatically

---

## API Endpoints

### Field Definitions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/custom-fields/definitions` | List definitions |
| `POST` | `/custom-fields/definitions` | Create definition |
| `PUT` | `/custom-fields/definitions/{id}` | Update definition |
| `DELETE` | `/custom-fields/definitions/{id}` | Delete definition |
| `POST` | `/custom-fields/definitions/prefill-product-cable` | Prefill cable fields |

### Field Values

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/custom-fields/values/bulk` | Get multiple values |
| `GET` | `/custom-fields/values/{type}/{id}` | Get entity values |
| `PUT` | `/custom-fields/values/{type}/{id}` | Update entity values |

---

## Data Model

### Field Definition

```json
{
  "id": "uuid",
  "entity_type": "product",
  "name": "Cable Length",
  "field_type": "select",
  "options": ["1m", "3m", "5m", "10m"],
  "required": false,
  "sort_order": 1,
  "created_at": "2026-08-06T10:00:00Z"
}
```

### Field Value

```json
{
  "id": "uuid",
  "definition_id": "uuid",
  "entity_type": "product",
  "entity_id": "uuid",
  "value": "5m",
  "created_at": "2026-08-06T10:00:00Z"
}
```

---

## Workflow Example

### Adding Cable Length Field

1. **Create Definition**
   - Entity: Product
   - Name: Cable Length
   - Type: Select
   - Options: 1m, 3m, 5m, 10m

2. **Set Values**
   - Open Product A → Set "Cable Length" = "5m"
   - Open Product B → Set "Cable Length" = "3m"

3. **Filter by Custom Field**
   - In product list, filter by "Cable Length = 5m"
   - Results show only 5m cables

4. **Bulk Update**
   - Select multiple products
   - Set "Cable Length" = "10m" for all

---

## Prefill Templates

### Product Cable Template

Creates standard cable fields:

- Cable Length (select)
- Cable Type (select: Power, Data, Fiber)
- Connector A (select)
- Connector B (select)
- Max Power (number)
- Shielded (boolean)

### Usage

1. Go to Settings → Custom Fields
2. Click "Prefill Product Cable"
3. All cable-related fields are created
4. Customize as needed

---

## Integration with Other Features

### Jobs

- Custom fields appear in job details
- Can be used in job requirements
- Included in job reports

### Products

- Custom fields in product details
- Shown in inventory lists
- Filterable in search

### Customers

- Custom fields in customer details
- Shown in company lists
- Used in customer reports

### Venues

- Custom fields in venue details
- Shown in venue lists
- Used in venue reports

---

## Limitations

- No file upload field type
- No rich text field type
- No field dependencies (conditional fields)
- No field groups/tabs
- No field versioning
- No audit trail for field changes
