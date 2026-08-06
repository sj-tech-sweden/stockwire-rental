# Database Schema

> Last reviewed: 2026-08-06

## Overview

Stockwire Rental uses PostgreSQL with SQLAlchemy 2.x ORM and Alembic for migrations.

**Version:** 0.6.0  
**Total Models:** 52  
**Total Migrations:** 60+

---

## Entity Relationship Diagram (Text)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              AUTH DOMAIN                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  users ──┬── user_roles ─── roles                                              │
│          │                                                                      │
│          ├── user_sessions                                                      │
│          │                                                                      │
│          ├── api_keys                                                           │
│          │                                                                      │
│          └── push_subscriptions                                                 │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           INVENTORY DOMAIN                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  inventory_categories ──┬── category_translations                              │
│                         │                                                       │
│                         └── products ──┬── product_accessories                  │
│                                        │                                        │
│                                        ├── product_components                   │
│                                        │                                        │
│                                        ├── product_suppliers                    │
│                                        │                                        │
│                                        └── devices ──┬── device_maintenance    │
│                                                      │                         │
│                                                      ├── device_maintenance_   │
│                                                      │   schedules             │
│                                                      │                         │
│                                                      ├── maintenance_comments  │
│                                                      │                         │
│                                                      └── defect_reports ──     │
│                                                          defect_comments       │
│                                                                                │
│  zones ─────────────────────────────────────────────────────────────────────── │
│                                                                                │
│  inventory_audit_logs                                                          │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────┐
│                           JOBS DOMAIN                                          │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  jobs ──────────────────────────────────────────────────────────────────────── │
│    │                                                                           │
│    ├── job_requirements                                                        │
│    │                                                                           │
│    ├── job_crew_requirements ─── job_required_skills                           │
│    │                                                                           │
│    ├── job_crew_assignments                                                    │
│    │                                                                           │
│    └── financial_transactions                                                  │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────┐
│                           PEOPLE DOMAIN                                        │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  customers ─────────────────────────────────────────────────────────────────── │
│                                                                                │
│  venues ────────────────────────────────────────────────────────────────────── │
│                                                                                │
│  projects                                                                      │
│                                                                                │
│  crew_members ──┬── crew_member_skills ─── crew_skills                        │
│                 │                                                               │
│                 └── crew_member_certifications ─── crew_certifications         │
│                                                                                │
│  crew_roles                                                                    │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────┐
│                          OPERATIONS DOMAIN                                     │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  notification_templates                                                        │
│                                                                                │
│  notification_logs                                                             │
│                                                                                │
│  calendar_feeds                                                                │
│                                                                                │
│  custom_field_definitions                                                      │
│                                                                                │
│  custom_field_values                                                           │
│                                                                                │
│  asset_files (storage)                                                         │
│                                                                                │
│  app_settings                                                                  │
│                                                                                │
│  activity_logs                                                                 │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────┐
│                        ROUTE PLANNER DOMAIN                                    │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  vehicles                                                                      │
│                                                                                │
│  delivery_routes                                                               │
│    │                                                                           │
│    ├── route_vehicles                                                          │
│    │                                                                           │
│    └── route_stops                                                             │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────┐
│                       WAREHOUSE LEDS DOMAIN                                    │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  led_controllers ── led_controller_zones                                       │
│                                                                                │
│  led_bin_mappings                                                              │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────┐
│                       INTEGRATIONS DOMAIN                                      │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  twenty_configs                                                                │
│                                                                                │
│  twenty_sync_logs                                                              │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Models

### Users & Authentication

#### `users`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `email` | VARCHAR | Unique email |
| `hashed_password` | VARCHAR | Bcrypt hashed password |
| `full_name` | VARCHAR | Display name |
| `role` | VARCHAR | `admin`, `manager`, or `viewer` |
| `is_active` | BOOLEAN | Account enabled |
| `external_provider` | VARCHAR | SSO provider name |
| `external_subject` | VARCHAR | SSO subject ID |
| `created_at` | TIMESTAMP | Creation time |
| `updated_at` | TIMESTAMP | Last update time |

#### `roles`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `name` | VARCHAR | Role name |
| `description` | VARCHAR | Role description |
| `created_at` | TIMESTAMP | Creation time |

#### `user_roles`
| Column | Type | Description |
|--------|------|-------------|
| `user_id` | UUID | FK → users |
| `role_id` | UUID | FK → roles |
| `assigned_at` | TIMESTAMP | Assignment time |

#### `api_keys`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | UUID | FK → users |
| `name` | VARCHAR | Key name |
| `key_hash` | VARCHAR | PBKDF2 hash |
| `key_prefix` | VARCHAR | First 8 chars (for display) |
| `lookup_digest` | VARCHAR | HMAC for lookup |
| `expires_at` | TIMESTAMP | Optional expiry |
| `created_at` | TIMESTAMP | Creation time |

---

### Inventory

#### `products`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `sku` | VARCHAR | Unique SKU |
| `name` | VARCHAR | Product name |
| `description` | TEXT | Product description |
| `category_id` | UUID | FK → inventory_categories |
| `brand` | VARCHAR | Brand name |
| `model` | VARCHAR | Model number |
| `unit_cost` | DECIMAL | Cost per unit |
| `replace_cost` | DECIMAL | Replacement cost |
| `rental_rate_daily` | DECIMAL | Daily rental rate |
| `rental_rate_weekly` | DECIMAL | Weekly rental rate |
| `quantity_total` | INT | Total quantity |
| `quantity_available` | INT | Available quantity |
| `weight_kg` | DECIMAL | Weight |
| `dimensions` | VARCHAR | Dimensions string |
| `image_url` | VARCHAR | Product image |
| `source_id` | VARCHAR | External system ID |
| `created_at` | TIMESTAMP | Creation time |
| `updated_at` | TIMESTAMP | Last update time |

#### `devices`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `asset_tag` | VARCHAR | Unique asset tag |
| `product_id` | UUID | FK → products |
| `serial_number` | VARCHAR | Serial number |
| `source_serial_id` | VARCHAR | External serial ID |
| `status` | VARCHAR | `available`, `checked_out`, `maintenance`, `retired` |
| `location_zone_id` | UUID | FK → zones |
| `location_detail` | VARCHAR | Specific location |
| `purchase_price` | DECIMAL | Purchase price |
| `purchase_date` | DATE | Purchase date |
| `last_maintenance` | TIMESTAMP | Last maintenance |
| `next_maintenance` | TIMESTAMP | Next scheduled |
| `parent_device_id` | UUID | FK → devices (component) |
| `created_at` | TIMESTAMP | Creation time |
| `updated_at` | TIMESTAMP | Last update time |

#### `inventory_categories`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `name` | VARCHAR | Category name |
| `parent_id` | UUID | FK → self (tree) |
| `sort_order` | INT | Display order |
| `icon` | VARCHAR | Icon name |
| `color` | VARCHAR | Color hex |
| `created_at` | TIMESTAMP | Creation time |

#### `zones`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `name` | VARCHAR | Zone name |
| `parent_id` | UUID | FK → self (tree) |
| `type` | VARCHAR | `warehouse`, `room`, `shelf`, `bin` |
| `barcode` | VARCHAR | Barcode value |
| `qr_code` | VARCHAR | QR code value |
| `rfid_tag` | VARCHAR | RFID tag |
| `pos_x` | FLOAT | 3D position X |
| `pos_y` | FLOAT | 3D position Y |
| `pos_z` | FLOAT | 3D position Z |
| `map_width` | FLOAT | Map width |
| `map_depth` | FLOAT | Map depth |
| `map_height` | FLOAT | Map height |
| `rotation` | FLOAT | Rotation degrees |
| `created_at` | TIMESTAMP | Creation time |

---

### Jobs

#### `jobs`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `code` | VARCHAR | Unique job code |
| `title` | VARCHAR | Job title |
| `description` | TEXT | Job description |
| `status` | VARCHAR | `draft`, `active`, `completed`, `cancelled` |
| `customer_id` | UUID | FK → customers |
| `venue_id` | UUID | FK → venues |
| `project_id` | UUID | FK → projects |
| `start_date` | DATE | Start date |
| `end_date` | DATE | End date |
| `sales_price` | DECIMAL | Quoted price |
| `invoice_paid` | BOOLEAN | Payment status |
| `eventory_job_id` | VARCHAR | Eventory integration ID |
| `productionplanner_project_id` | VARCHAR | ProductionPlanner ID |
| `created_at` | TIMESTAMP | Creation time |
| `updated_at` | TIMESTAMP | Last update time |

#### `job_requirements`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `job_id` | UUID | FK → jobs |
| `product_id` | UUID | FK → products |
| `quantity` | INT | Required quantity |
| `type` | VARCHAR | `product` or `rental` |
| `notes` | VARCHAR | Special requirements |
| `created_at` | TIMESTAMP | Creation time |

---

### Financial

#### `financial_transactions`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `job_id` | UUID | FK → jobs |
| `type` | VARCHAR | `income`, `expense`, `refund` |
| `category` | VARCHAR | Transaction category |
| `amount` | DECIMAL | Transaction amount |
| `currency` | VARCHAR | Currency code |
| `description` | TEXT | Description |
| `reference` | VARCHAR | Reference number |
| `settled` | BOOLEAN | Settlement status |
| `settled_at` | TIMESTAMP | Settlement time |
| `created_at` | TIMESTAMP | Creation time |

---

### Crew Management

#### `crew_members`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `name` | VARCHAR | Full name |
| `email` | VARCHAR | Email |
| `phone` | VARCHAR | Phone |
| `role_id` | UUID | FK → crew_roles |
| `status` | VARCHAR | `active`, `inactive` |
| `hourly_rate` | DECIMAL | Rate |
| `notes` | VARCHAR | Notes |
| `created_at` | TIMESTAMP | Creation time |

#### `crew_roles`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `name` | VARCHAR | Role name |
| `description` | VARCHAR | Description |
| `created_at` | TIMESTAMP | Creation time |

#### `crew_skills`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `name` | VARCHAR | Skill name |
| `description` | VARCHAR | Description |
| `created_at` | TIMESTAMP | Creation time |

#### `crew_certifications`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `name` | VARCHAR | Certification name |
| `description` | VARCHAR | Description |
| `created_at` | TIMESTAMP | Creation time |

---

### Route Planner

#### `vehicles`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `name` | VARCHAR | Vehicle name |
| `type` | VARCHAR | `truck`, `van`, `trailer` |
| `capacity_kg` | DECIMAL | Weight capacity |
| `capacity_m3` | DECIMAL | Volume capacity |
| `license_plate` | VARCHAR | License plate |
| `notes` | VARCHAR | Notes |
| `created_at` | TIMESTAMP | Creation time |

#### `delivery_routes`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `name` | VARCHAR | Route name |
| `date` | DATE | Route date |
| `status` | VARCHAR | `planned`, `in_progress`, `completed` |
| `notes` | VARCHAR | Notes |
| `created_at` | TIMESTAMP | Creation time |

#### `route_stops`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `route_id` | UUID | FK → delivery_routes |
| `venue_id` | UUID | FK → venues |
| `job_id` | UUID | FK → jobs |
| `vehicle_id` | UUID | FK → vehicles |
| `sort_order` | INT | Stop order |
| `type` | VARCHAR | `pickup`, `delivery` |
| `status` | VARCHAR | `pending`, `completed` |
| `notes` | VARCHAR | Notes |
| `created_at` | TIMESTAMP | Creation time |

---

### Warehouse LEDs

#### `led_controllers`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `name` | VARCHAR | Controller name |
| `ip_address` | VARCHAR | IP address |
| `type` | VARCHAR | Controller type |
| `status` | VARCHAR | `online`, `offline`, `error` |
| `created_at` | TIMESTAMP | Creation time |

#### `led_bin_mappings`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `controller_id` | UUID | FK → led_controllers |
| `zone_id` | UUID | FK → zones |
| `led_index` | INT | LED index on controller |
| `color` | VARCHAR | Default color |
| `created_at` | TIMESTAMP | Creation time |

---

### Other Models

#### `customers`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `name` | VARCHAR | Company name |
| `email` | VARCHAR | Contact email |
| `phone` | VARCHAR | Contact phone |
| `address` | TEXT | Physical address |
| `notes` | VARCHAR | Notes |
| `created_at` | TIMESTAMP | Creation time |

#### `venues`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `name` | VARCHAR | Venue name |
| `address` | TEXT | Address |
| `contact_name` | VARCHAR | Contact person |
| `contact_phone` | VARCHAR | Contact phone |
| `contact_email` | VARCHAR | Contact email |
| `notes` | VARCHAR | Notes |
| `created_at` | TIMESTAMP | Creation time |

#### `projects`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `name` | VARCHAR | Project name |
| `description` | TEXT | Description |
| `venue_id` | UUID | FK → venues |
| `status` | VARCHAR | `active`, `completed`, `archived` |
| `productionplanner_project_id` | VARCHAR | ProductionPlanner ID |
| `created_at` | TIMESTAMP | Creation time |

#### `custom_field_definitions`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `entity_type` | VARCHAR | `product`, `job`, `customer`, `venue` |
| `name` | VARCHAR | Field name |
| `field_type` | VARCHAR | `text`, `number`, `select`, `date`, `boolean` |
| `options` | JSON | Select options |
| `required` | BOOLEAN | Required flag |
| `sort_order` | INT | Display order |
| `created_at` | TIMESTAMP | Creation time |

#### `custom_field_values`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `definition_id` | UUID | FK → custom_field_definitions |
| `entity_type` | VARCHAR | Entity type |
| `entity_id` | UUID | Entity ID |
| `value` | TEXT | Field value |
| `created_at` | TIMESTAMP | Creation time |

#### `calendar_feeds`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `name` | VARCHAR | Feed name |
| `token` | VARCHAR | Unique token (public access) |
| `user_id` | UUID | FK → users |
| `crew_member_id` | UUID | FK → crew_members |
| `includes_jobs` | BOOLEAN | Include jobs |
| `includes_maintenance` | BOOLEAN | Include maintenance |
| `created_at` | TIMESTAMP | Creation time |

#### `asset_files`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `entity_type` | VARCHAR | Entity type |
| `entity_id` | UUID | Entity ID |
| `filename` | VARCHAR | Original filename |
| `category` | VARCHAR | File category |
| `storage_backend` | VARCHAR | `local` or `s3` |
| `storage_path` | VARCHAR | Storage path |
| `mime_type` | VARCHAR | MIME type |
| `size_bytes` | INT | File size |
| `created_at` | TIMESTAMP | Creation time |

#### `activity_logs`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | UUID | FK → users |
| `entity_type` | VARCHAR | Entity type |
| `entity_id` | UUID | Entity ID |
| `action` | VARCHAR | `create`, `update`, `delete` |
| `message` | TEXT | Human-readable message |
| `metadata` | JSON | Additional data |
| `created_at` | TIMESTAMP | Creation time |

---

## Migrations

### Migration Files

Located in `backend/alembic/versions/`

**60+ migrations** spanning from initial schema to latest features.

### Key Migrations

| Migration | Description |
|-----------|-------------|
| `20250518_0001_phase1_core.py` | Initial schema |
| `20260518_0003_add_rbac_api_keys.py` | RBAC and API keys |
| `20260520_0002_add_customers_venues_and_job_details.py` | Customers, venues |
| `20260520_0005_custom_fields.py` | Custom fields |
| `20260521_0018_asset_files_storage.py` | File storage |
| `20260717_0047_add_route_planner.py` | Route planner |
| `20260717_0050_add_warehouse_leds.py` | Warehouse LEDs |
| `20260724_0052_crew_management.py` | Crew management |
| `20260727_0054_calendar_feeds.py` | Calendar feeds |
| `20260804_0060_notification_system.py` | Notifications |

### Creating Migrations

```bash
cd backend

# Auto-generate from model changes
alembic revision --autogenerate -m "description"

# Create empty migration
alembic revision -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Migration Best Practices

1. Always review auto-generated migrations
2. Add indexes for frequently queried columns
3. Use `batch_alter_table` for SQLite compatibility
4. Test both upgrade and downgrade paths
5. Never modify committed migrations
