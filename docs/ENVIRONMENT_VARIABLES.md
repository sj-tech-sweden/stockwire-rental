# Environment Variables

> Last reviewed: 2026-08-06

Complete reference for all environment variables used by Stockwire Rental.

## Quick Start

```bash
cp infra/env/.env.example infra/env/.env
# Edit .env with your configuration
```

---

## Application

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `Stockwire Rental API` | Application name |
| `APP_ENV` | `development` | Environment (`development`, `staging`, `production`) |
| `APP_HOST` | `0.0.0.0` | Backend listen host |
| `APP_PORT` | `8000` | Backend listen port |
| `CORS_ORIGINS` | `http://localhost:9000,http://localhost:3000` | Allowed CORS origins (comma-separated) |

---

## PostgreSQL

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `postgres` | Database host |
| `POSTGRES_PORT` | `5432` | Database port |
| `POSTGRES_DB` | `stockwire_rental` | Database name |
| `POSTGRES_USER` | `stockwire_rental` | Database user |
| `POSTGRES_PASSWORD` | `stockwire_rental` | Database password |

---

## Redis

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |

---

## JWT Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET_KEY` | `change-me-in-production-use-a-long-random-string` | **REQUIRED in production** - JWT signing secret |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_EXPIRE_HOURS` | `8` | Session expiry hours |
| `JWT_ACCESS_EXPIRE_MINUTES` | `15` | Access token expiry minutes |
| `JWT_REFRESH_EXPIRE_DAYS` | `7` | Refresh token expiry days |

---

## Password Security

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY_PEPPER` | *(none)* | **REQUIRED in production** - Pepper for API key hashing |
| `PASSWORD_PEPPER` | *(none)* | **REQUIRED in production** - Pepper for password hashing |
| `PASSWORD_RESET_EXPIRE_MINUTES` | `15` | Password reset token expiry |
| `PASSWORD_RESET_BASE_URL` | `http://localhost:9000` | Base URL for password reset links |

---

## SSO / External Identity

| Variable | Default | Description |
|----------|---------|-------------|
| `SSO_ENABLED` | `false` | Enable SSO login |
| `SSO_AUTO_CREATE_USERS` | `true` | Auto-create users on first SSO login |
| `SSO_SYNC_ROLES_ON_LOGIN` | `true` | Sync roles from SSO groups on each login |
| `SSO_DEFAULT_ROLE` | `viewer` | Default role for auto-created SSO users |
| `SSO_GROUP_ROLE_MAP` | `{}` | JSON mapping of SSO groups to app roles |
| `OIDC_PROVIDERS` | `{}` | JSON object of OIDC provider configurations |
| `SAML_PROVIDERS` | `{}` | JSON object of SAML provider configurations |

### SSO_GROUP_ROLE_MAP Example

```json
{
  "Stockwire-Admins": "admin",
  "Stockwire-Managers": "manager",
  "Stockwire-Viewers": "viewer"
}
```

### OIDC_PROVIDERS Example

```json
{
  "entra": {
    "enabled": true,
    "display_name": "Microsoft Entra ID",
    "issuer": "https://login.microsoftonline.com/<tenant-id>/v2.0",
    "client_id": "<entra-client-id>",
    "client_secret": "<entra-client-secret>",
    "authorization_endpoint": "https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/authorize",
    "token_endpoint": "https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token",
    "jwks_uri": "https://login.microsoftonline.com/<tenant-id>/discovery/v2.0/keys",
    "scopes": "openid profile email",
    "group_claim": "groups",
    "email_claim": "preferred_username",
    "name_claim": "name",
    "subject_claim": "sub",
    "allow_auto_create": false
  }
}
```

### SAML_PROVIDERS Example

```json
{
  "entra_saml": {
    "enabled": false,
    "display_name": "Microsoft Entra SAML",
    "idp_entity_id": "https://sts.windows.net/<tenant-id>/",
    "idp_sso_url": "https://login.microsoftonline.com/<tenant-id>/saml2",
    "idp_x509_cert": "<entra-signing-cert>",
    "sp_entity_id": "https://stockwire.example.com/saml/metadata",
    "acs_url": "https://stockwire.example.com/api/v1/auth/sso/saml/login",
    "group_attribute": "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups",
    "email_attribute": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
    "name_attribute": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
    "subject_attribute": "nameid",
    "allow_auto_create": false
  }
}
```

---

## Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `STORAGE_BACKEND` | `local` | Storage backend (`local` or `s3`) |
| `STORAGE_MAX_UPLOAD_MB` | `25` | Maximum upload size in MB |
| `STORAGE_LOCAL_PATH` | `./data/uploads` | Local storage directory |

### S3 Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `STORAGE_S3_BUCKET` | *(none)* | S3 bucket name |
| `STORAGE_S3_REGION` | *(none)* | S3 region |
| `STORAGE_S3_ENDPOINT_URL` | *(none)* | S3 endpoint URL (for MinIO/compatible) |
| `STORAGE_S3_ACCESS_KEY_ID` | *(none)* | S3 access key |
| `STORAGE_S3_SECRET_ACCESS_KEY` | *(none)* | S3 secret key |
| `STORAGE_S3_PREFIX` | `uploads` | S3 key prefix |
| `STORAGE_S3_PRESIGN_EXPIRY_SECONDS` | `900` | Presigned URL expiry (seconds) |

---

## Email / SMTP

| Variable | Default | Description |
|----------|---------|-------------|
| `SMTP_HOST` | *(empty)* | SMTP server host |
| `SMTP_PORT` | `587` | SMTP server port |
| `SMTP_USER` | *(empty)* | SMTP username |
| `SMTP_PASSWORD` | *(empty)* | SMTP password |
| `SMTP_FROM_EMAIL` | `noreply@stockwire.app` | Sender email address |
| `SMTP_FROM_NAME` | `Stockwire Rental` | Sender display name |
| `SMTP_USE_TLS` | `true` | Enable TLS |

### Resend (Alternative)

| Variable | Default | Description |
|----------|---------|-------------|
| `RESEND_API_KEY` | *(empty)* | Resend API key (overrides SMTP) |

---

## Web Push Notifications

| Variable | Default | Description |
|----------|---------|-------------|
| `WEB_PUSH_VAPID_PUBLIC_KEY` | *(empty)* | VAPID public key for web push |
| `WEB_PUSH_VAPID_PRIVATE_KEY` | *(empty)* | VAPID private key for web push |
| `WEB_PUSH_VAPID_SUBJECT` | `mailto:noreply@stockwire.app` | VAPID subject (mailto or URL) |

---

## Prometheus / Observability

| Variable | Default | Description |
|----------|---------|-------------|
| `PROMETHEUS_ENABLED` | `true` | Enable Prometheus metrics endpoint |
| `PROMETHEUS_PUSHGATEWAY` | *(empty)* | Pushgateway URL (optional) |
| `PROMETHEUS_METRICS_USER` | *(empty)* | Basic auth username for `/metrics` |
| `PROMETHEUS_METRICS_PASSWORD` | *(empty)* | Basic auth password for `/metrics` |

---

## ProductionPlanner Integration

| Variable | Default | Description |
|----------|---------|-------------|
| `PRODUCTIONPLANNER_API_KEY` | *(empty)* | ProductionPlanner API key |
| `PRODUCTIONPLANNER_BASE_URL` | `https://api.productionplanner.io/v1` | ProductionPlanner API URL |

---

## Twenty CRM Integration

| Variable | Default | Description |
|----------|---------|-------------|
| `TWENTY_API_KEY` | *(empty)* | Twenty CRM API key |
| `TWENTY_BASE_URL` | `https://api.twenty.com` | Twenty CRM API URL |

---

## MQTT / Warehouse LEDs

| Variable | Default | Description |
|----------|---------|-------------|
| `MQTT_ENABLED` | `false` | Enable MQTT for LED control |
| `MQTT_BROKER_HOST` | `localhost` | MQTT broker host |
| `MQTT_BROKER_PORT` | `1883` | MQTT broker port |
| `MQTT_USERNAME` | *(empty)* | MQTT username |
| `MQTT_PASSWORD` | *(empty)* | MQTT password |
| `MQTT_TOPIC_PREFIX` | `stockwire` | MQTT topic prefix |
| `MQTT_WAREHOUSE_ID` | `default` | Warehouse ID for MQTT topics |
| `MQTT_TLS` | `false` | Enable MQTT TLS |

---

## LLM / AI Assistant

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_BASE_URL` | `http://localhost:11434/v1` | LLM API base URL (Ollama default) |
| `LLM_API_KEY` | `ollama` | LLM API key |
| `LLM_MODEL` | `qwen2.5-coder` | LLM model name |

---

## Frontend (Vite)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API URL for frontend |

---

## Production Recommendations

### Minimum Required for Production

```bash
# Security
JWT_SECRET_KEY=<long-random-string>
API_KEY_PEPPER=<random-string>
PASSWORD_PEPPER=<random-string>

# Database
POSTGRES_PASSWORD=<strong-password>

# CORS
CORS_ORIGINS=https://your-domain.com
```

### Recommended for Production

```bash
# Storage
STORAGE_BACKEND=s3
STORAGE_S3_BUCKET=stockwire-uploads
STORAGE_S3_REGION=us-east-1
STORAGE_S3_ACCESS_KEY_ID=<access-key>
STORAGE_S3_SECRET_ACCESS_KEY=<secret-key>

# Email
SMTP_HOST=smtp.your-provider.com
SMTP_USER=your-email
SMTP_PASSWORD=your-password

# SSO (if using)
SSO_ENABLED=true
SSO_AUTO_CREATE_USERS=false
```

---

## Environment-Specific Notes

### Development

- Default values work for local Docker development
- `JWT_SECRET_KEY` can use the default (not secure, but OK for dev)
- `STORAGE_BACKEND=local` is fine for single-node dev

### Staging

- Use real secrets for all `*_KEY`, `*_SECRET`, `*_PASSWORD` variables
- Consider `STORAGE_BACKEND=s3` for multi-node staging
- Enable `SSO_ENABLED=true` if testing SSO flows

### Production

- **All secrets MUST be set to strong, unique values**
- Use `STORAGE_BACKEND=s3` for durability
- Enable `PROMETHEUS_ENABLED=true` for monitoring
- Set `SSO_AUTO_CREATE_USERS=false` for security
- Configure `SMTP_*` for email notifications
