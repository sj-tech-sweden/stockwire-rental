# Keycloak SSO Guide (OIDC and SAML)

This guide explains how to integrate Keycloak with Stockwire Rental using OIDC or SAML, including group to role mapping and disabling automatic user creation.

## Scope

- Backend: FastAPI auth SSO endpoints
- Frontend: Admin Settings -> Auth -> Single Sign-On (OIDC / SAML)
- Identity provider: Keycloak

## Prerequisites

- Stockwire Rental backend and frontend running
- Admin account in Stockwire Rental
- Keycloak admin access
- Realm created for your organization

## How Stockwire maps users and roles

On successful SSO login, Stockwire applies:

1. User lookup:
- external_provider + external_subject
- fallback by email

2. Role resolution:
- groups from token/assertion are matched against Group to Role Mapping
- highest role wins: admin > manager > viewer
- if no mapping, Default role is used

3. Auto-provisioning:
- Auto-create disabled: unknown users are rejected
- Auto-create enabled: unknown users are created from SSO identity

## Part A: OIDC with Keycloak

### 1) Create client in realm

- Realm -> Clients -> Create client
- Client type: OpenID Connect
- Client ID: stockwire-web
- Client authentication: On (confidential client)
- Standard flow: On

### 2) Configure redirect URIs and origins

- Valid redirect URIs:
  - https://your-domain/login?oidc_provider=keycloak
  - http://localhost:9000/login?oidc_provider=keycloak
- Web origins:
  - https://your-domain
  - http://localhost:9000

### 3) Configure group claims

- Add protocol mapper that includes groups in ID token
- Ensure mapper name/claim is groups

### 4) Collect OIDC endpoints

For realm stockwire on host sso.example.com:

- Issuer:
  - https://sso.example.com/realms/stockwire
- Authorization endpoint:
  - https://sso.example.com/realms/stockwire/protocol/openid-connect/auth
- Token endpoint:
  - https://sso.example.com/realms/stockwire/protocol/openid-connect/token
- JWKS URI:
  - https://sso.example.com/realms/stockwire/protocol/openid-connect/certs

Also collect:

- Client ID
- Client Secret

### 5) Configure Stockwire Settings UI (OIDC)

Go to Admin Settings -> Auth -> Single Sign-On.

Global controls:

- Enable SSO: on
- Auto-create users: optional (off for strict provisioning)
- Sync roles on login: on (recommended)
- Default role: viewer

Add OIDC provider row:

- Provider key: keycloak
- Display name: Keycloak
- Enabled: on
- Auto-create: off (if strict provisioning)
- Issuer: value above
- Scopes: openid profile email groups
- Client ID: stockwire-web (or your chosen client id)
- Client secret: from Keycloak client credentials
- Authorization endpoint: value above
- Token endpoint: value above
- JWKS URI: value above
- Group claim: groups
- Email claim: email
- Name claim: name
- Subject claim: sub

### 6) Group to role mapping

Define rows in Stockwire settings, for example:

- /stockwire/admins -> admin
- /stockwire/managers -> manager
- /stockwire/viewers -> viewer

Use exact group values that Keycloak emits.

### 7) Test OIDC login

- Open Login page
- Click Continue with Keycloak
- Authenticate via Keycloak
- Verify role and access in Stockwire

## Part B: SAML with Keycloak

### 1) Create SAML client in Keycloak

- Realm -> Clients -> Create
- Client type/protocol: SAML
- Client ID: your SP entity ID (for Stockwire)

### 2) Configure ACS and NameID

- Valid redirect/ACS URL should point to backend SAML login endpoint:
  - https://your-domain/api/v1/auth/sso/saml/login
- Configure NameID to stable value (commonly username or email)

### 3) Configure SAML mappers

Create mappers for:

- email
- name
- groups

### 4) Collect IdP metadata values

- IdP entity ID
- IdP SSO URL
- Signing certificate x509

### 5) Configure Stockwire Settings UI (SAML)

Add SAML provider row:

- Provider key: keycloak_saml
- Display name: Keycloak SAML
- Enabled: on
- Auto-create: off (if strict provisioning)
- IdP entity ID: from Keycloak metadata
- IdP SSO URL: from Keycloak metadata
- IdP x509 cert: Keycloak signing cert
- SP entity ID: your Stockwire SP identifier
- ACS URL: backend SAML endpoint
- Group attribute: groups
- Email attribute: email
- Name attribute: name
- Subject attribute: nameid

### 6) Test SAML login

- Start from your Keycloak SAML app entry
- Confirm user creation/matching behavior based on auto-create policy
- Confirm role mapping by group

## Production hardening checklist

- Use HTTPS on all endpoints
- Keep confidential clients and rotate secrets
- Disable auto-create users if governance requires pre-provisioning
- Keep Sync roles on login on if Keycloak groups are source of truth
- Restrict SSO configuration to Stockwire admins only

## Troubleshooting

### OIDC authorization page does not open correctly

- Verify authorization endpoint and redirect URI
- Verify frontend URL is listed in Web origins

### Invalid OIDC token / audience issues

- Verify issuer URL exactly matches realm
- Verify client id and secret
- Verify token endpoint and JWKS URI

### Group mapping not applied

- Confirm groups are included in token/assertion
- Confirm mapping rows match emitted group strings exactly

### User denied when Auto-create is off

- Expected for unknown users
- Pre-create user in Stockwire with matching email, or enable auto-create
