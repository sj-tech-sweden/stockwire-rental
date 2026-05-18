# Roadmap Mapped From WarehouseCore Open Issues

Source: issues in [cores/issues.json](../cores/issues.json)

## Priority bands
- P0: operational blockers and core UX debt
- P1: high-value workflow improvements
- P2: platform capabilities and strategic extensions

## P0 (Sprint 1-2)
- #114 Fix scroll
  - Define viewport-safe layout shell and page-level overflow policy
  - Add mobile and desktop visual regression checks
- #112 Better mobile experience
  - Mobile-first job pick/scan flow
  - Card layouts for devices and less horizontal scrolling
- #105 Scan in and out cases
  - Scan case to include member devices
  - Optional strict mode: require per-device verification on check-in
- #118 Job on device info
  - Expand device-job popover: customer, date range, status, remaining picks

## P1 (Sprint 3-4)
- #117 Edit zones
  - Zone edit UX + bulk create/edit subzones
  - Server-side validation for hierarchy constraints
- #111 Inline change requirement
  - Search + category tree picker for requirement edits
- #115 Edit defective reports
  - Defect edit modal, timeline comments, audit entries
- #104 Refactor admin view
  - Replace tab sprawl with nav sections + feature-based route groups

## P1/P2 (Sprint 4-5)
- #108 Light mode
  - Theme switching: dark, light, auto(system)
  - Ensure brand contrast in both modes
- #102 Update documentation
  - Continuous docs updates tied to each feature PR

## P2 (Sprint 5-7)
- #110 SSO
  - OIDC first (Entra ID, Keycloak)
  - Optional SAML bridge after OIDC baseline
  - Group-to-role mapping support
- #109 Expand eventory
  - Default URL set to https://api.eventory.se
  - Multi-instance/vendor configuration model
- #106 Scan rental equipment
  - Vendor rental equipment scan lifecycle and location tracking
- #101 Remove nextcloud dependency
  - Storage abstraction with S3-compatible providers
- #103 Offline abilities
  - Offline queue + sync conflict policy
  - Live updates when online via websockets

## Cross-cutting acceptance criteria
- Every feature includes:
  - API contract tests
  - Quasar component tests
  - audit trail where domain-relevant
  - docs update checklist

## Domain backlog structure
- Epic A: Mobile scanning and pick workflow
- Epic B: Zone and inventory management UX
- Epic C: Defects and operational collaboration
- Epic D: Identity and enterprise integrations
- Epic E: Storage/integration abstraction
- Epic F: Offline-first architecture
