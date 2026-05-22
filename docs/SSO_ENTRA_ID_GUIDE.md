# Entra ID SSO Guide (OIDC and SAML)

This guide explains how to integrate Microsoft Entra ID with Stockwire Rental using either OIDC or SAML, including group to role mapping and disabling automatic user creation.

## Scope

- Backend: FastAPI auth SSO endpoints
- Frontend: Admin Settings -> Auth -> Single Sign-On (OIDC / SAML)
- Identity provider: Microsoft Entra ID

## Prerequisites

- Stockwire Rental backend and frontend running
- Admin account in Stockwire Rental
- Entra tenant admin access (or delegated app registration rights)
- DNS/URL for your deployment (for production)

## How Stockwire maps users and roles

On successful SSO login, Stockwire reads identity claims/attributes and applies:

1. User lookup order:
- external_provider + external_subject
- fallback by email

2. Role resolution:
- external groups are matched against Group to Role Mapping
- highest role wins: admin > manager > viewer
- if no match, Default role is used

3. Auto-provisioning:
- if Auto-create users is disabled, unknown SSO users are rejected
- if enabled, unknown users are created from SSO identity data

## Part A: OIDC with Entra ID

### 1) Create app registration in Entra

- Go to Entra admin center -> App registrations -> New registration
- Name: Stockwire Rental OIDC
- Supported account types: usually Single tenant
- Redirect URI (Web):
  - https://your-domain/login?oidc_provider=entra
  - For local dev: http://localhost:9000/login?oidc_provider=entra

### 2) Create client secret

- App registration -> Certificates & secrets -> New client secret
- Copy secret value immediately (you will not see it again)

### 3) Configure API permissions / claims

- Ensure ID token includes profile and email style claims
- If you need group based roles:
  - Token configuration -> Add groups claim
  - Recommended: Security groups

### 4) Capture endpoints and identifiers

You need:

- Tenant ID
- Client ID
- Client Secret
- Issuer:
  - https://login.microsoftonline.com/<tenant-id>/v2.0
- Authorization endpoint:
  - https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/authorize
- Token endpoint:
  - https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token
- JWKS URI:
  - https://login.microsoftonline.com/<tenant-id>/discovery/v2.0/keys

### 5) Configure Stockwire Settings UI (OIDC)

Go to Admin Settings -> Auth -> Single Sign-On.

Global controls:

- Enable SSO: on
- Auto-create users: optional (off for strict pre-provisioning)
- Sync roles on login: on (recommended)
- Default role: viewer (recommended)

Add OIDC provider row with values:

- Provider key: entra
- Display name: Microsoft Entra ID
- Enabled: on
- Auto-create: off (if you do not want auto user creation)
- Issuer: value from step 4
- Scopes: openid profile email
- Client ID: app registration client id
- Client secret: app registration secret
- Authorization endpoint: value from step 4
- Token endpoint: value from step 4
- JWKS URI: value from step 4
- Group claim: groups
- Email claim: preferred_username (common for Entra)
- Name claim: name
- Subject claim: sub

### 6) Configure Group to Role Mapping

Add rows, for example:

- Stockwire-Admins -> admin
- Stockwire-Managers -> manager
- Stockwire-Viewers -> viewer

These group names must match what Entra sends in token groups claim.

### 7) Test login

- Open Login page
- Click Continue with Microsoft Entra ID
- Authenticate in Entra
- Verify role and access in Stockwire

## Part B: SAML with Entra ID

Use this if your organization requires SAML.

### 1) Create enterprise app in Entra

- Entra admin center -> Enterprise applications -> New application
- Add your SAML app

### 2) Configure SAML basic settings

- Identifier (Entity ID): your SP entity id used by Stockwire
- Reply URL (ACS):
  - https://your-domain/api/v1/auth/sso/saml/login
  - For local testing, use your reachable backend URL

### 3) Configure claims and groups

- Add or confirm claims for email, name, groups
- Note exact claim URIs/attribute names used in assertions

### 4) Collect IdP values

- IdP Entity ID
- IdP SSO URL
- Signing certificate (x509)

### 5) Configure Stockwire Settings UI (SAML)

Add SAML provider row with values:

- Provider key: entra_saml
- Display name: Microsoft Entra SAML
- Enabled: on
- Auto-create: off (if strict provisioning)
- IdP entity ID: from Entra
- IdP SSO URL: from Entra
- IdP x509 cert: from Entra signing cert
- SP entity ID: your app SP identifier
- ACS URL: your backend ACS endpoint
- Group attribute: claim name/URI used for groups
- Email attribute: claim name/URI for email
- Name attribute: claim name/URI for display name
- Subject attribute: usually nameid

### 6) Test SAML login

- Initiate from Entra app launcher or your SAML flow
- Confirm Stockwire creates or matches user according to your auto-create policy

## Production hardening checklist

- Use HTTPS only for frontend and backend
- Rotate client secrets regularly
- Keep Auto-create users off unless onboarding flow requires it
- Keep Sync roles on login on if your source of truth is Entra groups
- Restrict who can edit SSO settings in Stockwire (admin only)

## Troubleshooting

### Browser shows CORS errors for all API requests

Often this is backend 500 during auth lookup. Check backend logs first.

### OIDC login fails with invalid token

- Verify issuer exactly matches tenant and v2.0 form
- Verify client id/secret and redirect URI
- Verify JWKS URI is correct

### User gets viewer role unexpectedly

- Check Group to Role Mapping values
- Verify Entra sends groups claim in ID token
- Confirm group names in token match mapping exactly

### Unknown SSO user denied

- This is expected when Auto-create users is off
- Pre-create user in Stockwire with matching email, or enable auto-create
