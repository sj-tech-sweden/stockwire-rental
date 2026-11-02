# Stockwire Assistant MCP Server

An [MCP](https://modelcontextprotocol.io) (Model Context Protocol) server that
exposes the Stockwire Assistant's tools to **outside agents** — Claude Desktop,
OpenCode, a remote agent, or any MCP-compatible client.

## Design: one source of truth

The MCP server does **not** redefine the assistant's tools. It reuses the exact
same definitions and execution handlers as the in-app SSE chat endpoint:

| Shared code | Role |
| --- | --- |
| `app/assistant/tools.py` → `TOOLS` | OpenAI-style tool schemas (the catalogue) |
| `app/assistant/tools.py` → `execute_tool(name, args, db)` | The actual DB logic |

The MCP server (`app/assistant/mcp_server.py`) reads `TOOLS`, maps each entry to
an MCP tool (name + description + JSON-Schema arguments), and wires each call to
`execute_tool`. **Adding or changing a tool in `tools.py` automatically benefits
both the SSE chat and every MCP client** — there is nothing to keep in sync.

## Deployment: mounted inside FastAPI

The MCP server is **not** a separate process. It is mounted inside the existing
FastAPI app at **`/mcp`** (see `app/main.py`), so it shares the API's database
sessions, CORS configuration, and deployment. This is also what makes the
OAuth-protected design below possible — the same request path is gated by the
same user store the rest of the app uses.

The dependency is `mcp>=2.0.0` (the v2 high-level `MCPServer` API). There is no
upper bound, so `mcp` v3+ is allowed; any API drift will be fixed when we bump.

## Authentication: OAuth 2.0 (Authorization Code + PKCE)

The server uses **full MCP OAuth** so agents can "add the server" in a
browser-based flow, exactly like any other OAuth-protected resource. Access
tokens are the application's existing JWTs (issued by the login/user store), so
no separate token database is needed.

Authorization model:

| Capability | Who |
| --- | --- |
| Read tools (inventory, rates, search, listings, …) | Any **active** user |
| Write tools (`update_product_manufacturer`, `update_product_category`, `batch_update_manufacturers`) | **Admin** only |

Deactivated users lose MCP access immediately, even with a still-valid token
(the verifier re-checks `is_active` on every request).

### Endpoints

All OAuth endpoints are hosted by the FastAPI app itself (not the `mcp`
sub-app), so they reuse the app's login/session machinery:

| Endpoint | Purpose |
| --- | --- |
| `/.well-known/oauth-authorization-server` | OAuth server metadata (discovery) |
| `/.well-known/oauth-protected-resource` | Protected-resource metadata (the `/mcp` resource) |
| `/oauth/register` | Dynamic client registration (RFC 7591) |
| `/oauth/authorize` | Authorization endpoint (Authorization Code + PKCE, S256) |
| `/oauth/login` | Minimal backend login page that issues the `mcp_session` cookie |
| `/oauth/token` | Token exchange (authorization code → access + refresh) and refresh |
| `/oauth/revoke` | Token revocation |
| `/oauth/sso/oidc/start/{provider}` | Begins an OIDC login with the named provider |
| `/oauth/sso/oidc/callback` | OIDC IdP redirect target; sets the `mcp_session` cookie |
| `/oauth/sso/saml/start/{provider}` | Begins a SAML login with the named provider |
| `/oauth/sso/saml/callback` | SAML ACS target; sets the `mcp_session` cookie |
| `/mcp` | The MCP streamable-HTTP protocol endpoint (bearer-token protected) |

The `/mcp` endpoint is protected by `StockwireTokenVerifier`
(`app/assistant/mcp_oauth.py`), which validates the JWT and stores the decoded
claims in a contextvar that the tool handlers consult to enforce the admin gate
on write tools.

### How the flow works

1. A client reads `/.well-known/oauth-authorization-server`, registers itself at
   `/oauth/register`, and opens the browser at `/oauth/authorize` with a PKCE
   `code_challenge` (S256 only).
2. If the user has no `mcp_session` cookie, they are shown the `/oauth/login`
   page and authenticate with their Stockwire credentials. On success a short-
   lived, httpOnly `mcp_session` cookie is set.
3. `/oauth/authorize` issues a single-use authorization code bound to the PKCE
   challenge.
4. The client exchanges the code (plus `code_verifier`) at `/oauth/token` for an
   access token (the app JWT) and a refresh token.
5. The client calls `/mcp` with `Authorization: Bearer <access_token>`.

### Configuration

| Setting | Meaning |
| --- | --- |
| `mcp_issuer_url` | Public base URL the MCP/OAuth endpoints are served from. Used to build the issuer and metadata. Defaults to `effective_api_base_url` when empty. |

### Connecting an agent (OAuth-capable clients)

OAuth-capable MCP clients (e.g. recent Claude Desktop / OpenCode builds) can
typically **discover** the server from its issuer URL and walk the login flow
themselves. Point the client at the issuer (`mcp_issuer_url`) and let it read
the metadata; it will register, open the browser, and obtain a token
automatically.

For clients that only support a static config, register the client once via
`/oauth/register` and supply the resulting `client_id` plus the token the flow
produces.

## Read-only mode

Set `STOCKWIRE_MCP_READONLY=true` to expose **only** the read tools
(`check_inventory_stock`, `get_rental_rates`, `list_customers`, `search_products`,
`list_jobs`, `list_categories`) and disable the manufacturer/category write
tools. Useful when the agent should be able to query but not mutate data.

## Available tools

The tool catalogue is identical to the in-app assistant (see `tools.TOOLS`):
inventory stock checks, rental rates, customer/product search, job listing,
category browsing, and (unless read-only) manufacturer/category updates. The
write tools additionally require an admin-authenticated token.

## Database

The OAuth flow persists clients, authorization codes, and refresh tokens via
three tables (`mcp_oauth_clients`, `mcp_oauth_codes`, `mcp_oauth_refresh_tokens`
in `app/assistant/mcp_oauth_models.py`). Access tokens themselves are stateless
JWTs and are not stored. Apply the Alembic migration
`7c9e1f2a3b4c_add_mcp_oauth_tables.py` when deploying.

## SSO (OIDC / SAML) login

The login page at `/oauth/login` authenticates against the **local** password
store and, when SSO is enabled, also renders a **Continue with &lt;provider&gt;**
button per enabled OIDC / SAML provider. Those buttons start the same SSO flow
the SPA uses (`app.domain.auth.sso`), but instead of returning a token to the
SPA they bounce the user through the IdP and then set the `mcp_session` cookie
before redirecting back to `/oauth/authorize`. From there the rest of the
Authorization Code + PKCE flow is identical to a local-password login.

Endpoints (all under the MCP OAuth router):

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/oauth/sso/oidc/start/{provider}` | GET | Builds the OIDC authorize URL for `{provider}` and redirects to the IdP. Binds a short-lived `oidc_state` cookie (HttpOnly) for CSRF protection. |
| `/oauth/sso/oidc/callback` | GET | IdP redirect target. Verifies `state`, exchanges the code, upserts the external user, sets the `mcp_session` cookie, then redirects to `next`. |
| `/oauth/sso/saml/start/{provider}` | GET | Redirects to the IdP SSO URL, carrying `provider` + `next` in a base64 `RelayState`. |
| `/oauth/sso/saml/callback` | POST | IdP ACS target. Parses the SAML response, upserts the external user, sets the `mcp_session` cookie, then redirects to `next`. |

### IdP registration requirement

Because these endpoints reuse the SSO plumbing, the **same IdP-side registration
that the SPA SSO endpoints need also applies here**:

- **OIDC**: register the callback
  `https://<mcp_issuer_url>/oauth/sso/oidc/callback` as a valid
  `redirect_uri` for the provider. The exact URL the app sends includes
  `?provider=<key>&next=<url>` query parameters, but the IdP must whitelist the
  base `redirect_uri` (most IdPs match on the path prefix / exact host+path).
- **SAML**: register the ACS (assertion consumer service) URL
  `https://<mcp_issuer_url>/oauth/sso/saml/callback` for the SP.

`<mcp_issuer_url>` is the public base URL from the `mcp_issuer_url` setting
(defaults to `effective_api_base_url`). Register the HTTPS form; the cookie is
issued with `Secure` unless running in a dev/local `APP_ENV`.

SSO is controlled by the same settings the SPA uses (`sso_enabled`,
`oidc_providers`, `saml_providers`, `sso_auto_create_users`,
`sso_default_role`, `sso_group_role_map`). When SSO is disabled the SSO buttons
are hidden and the start/callback endpoints return `404`.
