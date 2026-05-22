# Storage and File Upload Guide (Local + S3)

This guide explains how to use file storage for:

- Company logo uploads
- Documents linked to jobs
- Documents linked to products
- Documents linked to devices
- Documents linked to maintenance tasks

## Storage Backends

The backend supports two interchangeable storage backends:

- `local`: files stored on the application filesystem
- `s3`: files stored in an S3-compatible object storage bucket

## Choosing Local Disk vs S3

Use `local` when:

- You are running a single-node local/dev setup.
- You want zero external dependencies.
- You can safely persist a host volume and accept node-local coupling.

Use `s3` when:

- You run multiple backend replicas or multiple hosts.
- You need durable, centrally managed object storage.
- You want easier backups/lifecycle policies and cloud-native operations.

Quick comparison:

| Dimension | local | s3 |
| --- | --- | --- |
| Setup complexity | low | medium |
| Works across multiple app nodes | no (unless shared FS) | yes |
| Durability by default | depends on host/volume | depends on provider config (typically high) |
| Best for | local development, small single-node installs | staging/production, multi-node deployments |
| Download behavior | streamed by app | short-lived presigned URL |

## Recommended Backend by Environment

- Local development: `STORAGE_BACKEND=local`
- Staging: prefer `s3` to mirror production behavior
- Production: `s3` strongly recommended

If you keep `local` in production, ensure:

- persistent volumes are mounted and backed up,
- only one writer node is used (or shared filesystem semantics are explicitly handled),
- restore procedures are tested.

## Environment Variables

Set these variables in backend runtime environment.

### Common

- `STORAGE_BACKEND=local|s3`
- `STORAGE_MAX_UPLOAD_MB=25`

### Local backend

- `STORAGE_LOCAL_PATH=./data/uploads`

Notes:

- In containers, mount this path to a persistent volume.
- Avoid ephemeral container filesystems for persistent uploads.

### S3 backend

- `STORAGE_S3_BUCKET=your-bucket`
- `STORAGE_S3_REGION=eu-central-1`
- `STORAGE_S3_ENDPOINT_URL=https://s3.amazonaws.com` (optional for AWS, required for MinIO/other S3-compatible)
- `STORAGE_S3_ACCESS_KEY_ID=...`
- `STORAGE_S3_SECRET_ACCESS_KEY=...`
- `STORAGE_S3_PREFIX=uploads`
- `STORAGE_S3_PRESIGN_EXPIRY_SECONDS=900`

## Data Model

Uploaded files are stored in database table `asset_files`.

Fields include:

- `entity_type` (`company`, `job`, `product`, `device`, `maintenance`)
- `entity_id` (required for all except `company`)
- `category` (for example: `logo`, `manual`, `invoice`, `photo`, `service-report`)
- `storage_backend` and `storage_key`
- `original_filename`, `content_type`, `size_bytes`

## API Endpoints

All routes are under `/api/v1/storage`.

- `POST /files` (multipart form upload)
- `GET /files` (list with optional filters)
- `GET /files/{file_id}` (metadata)
- `GET /files/{file_id}/download` (download or S3 presigned redirect)
- `DELETE /files/{file_id}` (soft delete + storage object removal)

### Upload request fields (multipart form)

- `file`: binary file payload (required)
- `entity_type`: `company|job|product|device|maintenance` (optional)
- `entity_id`: integer ID (required unless entity_type is `company`)
- `category`: custom category label (optional)

## Company Branding API

Company profile is stored in app settings.

- `GET /api/v1/settings/company-profile`
- `PUT /api/v1/settings/company-profile`

Payload for update:

```json
{
  "company_name": "Tsunami Events",
  "logo_file_id": 123
}
```

The frontend settings page can upload a logo file first, then persist `logo_file_id` via company profile endpoint.

## Example cURL Uploads

Upload a logo:

```bash
curl -X POST "http://localhost:8000/api/v1/storage/files" \
  -H "Authorization: Bearer <token>" \
  -F "file=@./logo.png" \
  -F "entity_type=company" \
  -F "category=logo"
```

Upload a job document:

```bash
curl -X POST "http://localhost:8000/api/v1/storage/files" \
  -H "Authorization: Bearer <token>" \
  -F "file=@./offer.pdf" \
  -F "entity_type=job" \
  -F "entity_id=42" \
  -F "category=quote"
```

List all product manuals:

```bash
curl "http://localhost:8000/api/v1/storage/files?entity_type=product&category=manual" \
  -H "Authorization: Bearer <token>"
```

## Notes

- Upload endpoints require editor-or-higher permissions.
- Maximum upload size is enforced by `STORAGE_MAX_UPLOAD_MB`.
- For S3 backend, downloads are provided through short-lived presigned URLs.
- Deleting a file marks DB row as deleted and removes the object from storage backend.

## Backend Migration Notes (local <-> s3)

Switching `STORAGE_BACKEND` only changes where new files are written. Existing files remain in their original backend and are still resolvable via `asset_files.storage_backend` and `asset_files.storage_key`.

Recommended migration approach:

1. Freeze writes or run migration during low-traffic window.
2. Copy objects from source backend to target backend.
3. Update `asset_files.storage_backend` and `asset_files.storage_key` per migrated row.
4. Validate downloads for a representative sample.
5. Switch `STORAGE_BACKEND` for new writes.
