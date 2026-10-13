# Release Process & Required Secrets

This document describes the release workflow and the secrets required to publish images and operate API-key hashing.

## Secrets

- `API_KEY_PEPPER` — required by the backend to HMAC API keys before storing. Set a long random secret (32+ bytes). Keep this secret consistent across replicas; rotate carefully by supporting multiple peppers if needed.

- `JWT_SECRET` — the signing secret for JWT access tokens. Use a secure random value and keep it secret.

- `GITHUB_TOKEN` — provided by GitHub Actions automatically for workflows. For pushing to GHCR from workflows, you may need a Personal Access Token stored as `CR_PAT` or configure `GITHUB_TOKEN` with proper permissions in the workflow.

- `RELEASE_PLEASE_TOKEN` — a Personal Access Token used by the release workflow (`.github/workflows/release.yml`) to open and update the release-please Release PR. This is required because the repository/organization policy disables `GITHUB_TOKEN` from creating or approving pull requests. Create a fine-grained PAT (or classic PAT with `repo`/`contents:write` and `pull-requests:write`) for a user who can push to the repo, store it as `RELEASE_PLEASE_TOKEN`, and keep it rotated.

- `GHCR_USERNAME` / `GHCR_TOKEN` or `CR_PAT` — if not using `GITHUB_TOKEN` for package publishing, store a PAT with `packages:write` permission.

Set these secrets in the repository settings under "Settings → Secrets and variables → Actions".

## Release workflow

Releases are fully automated with [`googleapis/release-please-action`](https://github.com/googleapis/release-please-action), driven by [Conventional Commits](https://www.conventionalcommits.org/) on `main`.

How it works:

- Every merged commit to `main` is inspected by `.github/workflows/release.yml`.
- When conventional commits since the last release imply a version bump, release-please opens (and keeps up to date) a **Release PR** titled `chore: release X.Y.Z`. The PR contains the updated `CHANGELOG.md`, `.release-please-manifest.json`, and `VERSION` file.
- Merging that Release PR causes release-please to:
  - create the GitHub Release with generated release notes (categorised from the commit messages),
  - push the matching `X.Y.Z` git tag.
- On release, `release.yml` calls `.github/workflows/docker-build-and-push.yml` via `workflow_call` to build and publish the `backend` and `frontend` images to GHCR, tagged with the new version and `latest`.

The release type is derived from the commits automatically:

- `fix:` → patch
- `feat:` → minor
- `feat!:` / `fix!:` / a `BREAKING CHANGE` footer → major

Version configuration lives in `release-please-config.json` (release type and changelog sections) and `.release-please-manifest.json` (last released version, currently `0.9.2`). The `simple` release type tracks a root `VERSION` file, so no root `package.json`/`pyproject.toml` is required.

Notes:

- Ensure repository secrets for GHCR are configured before enabling automated pushes.
- The docker build is skipped for the Release PR's own merge commit via the push guard in `docker-build-and-push.yml`, so images are only built once (from the `workflow_call` invoked by the release job).
- To force a specific version, use `release-please`'s `release-as` support or bump the manifest manually; do not rely on PR labels.

## How to use the Release workflow (step-by-step)

- **Normal flow**: Write commits using the Conventional Commits convention (`feat:`, `fix:`, etc.). When `main` accumulates releasable changes, review and merge the `chore: release X.Y.Z` PR that release-please maintains. Merging it publishes the release and the images.

- **Breaking change**: Use a `!` after the type (`feat(api)!: ...`) or add a `BREAKING CHANGE:` footer. This triggers a major bump.

- **First-time setup / verify**: Confirm that `release-please-config.json`, `.release-please-manifest.json`, and `.github/workflows/release.yml` are present and that the workflow has `contents: write`, `pull-requests: write`, and `issues: write` permissions (already configured).

- **Secrets & permissions**:
	- The release job uses `RELEASE_PLEASE_TOKEN` (a PAT) to create the release PR, because `GITHUB_TOKEN` is not permitted to create or approve pull requests in this repository. Ensure that secret exists and is valid (rotate it if expired).
	- Ensure `GITHUB_TOKEN` has `packages: write` when used for GHCR login, or provide `CR_PAT` (Personal Access Token) in repository secrets with `packages:write` permission.
	- `API_KEY_PEPPER` and `JWT_SECRET` must be set for production deployments.

- **How to verify a release**:
	- Check the Actions run for `.github/workflows/release.yml` to see the release-please output and the triggered image build.
	- Confirm a Release is created in the repository `Releases` UI with the computed tag.
	- Verify the `docker-build-and-push` workflow run was triggered and completed (it will push images to `ghcr.io/${{ github.repository_owner }}/...`).

- **Troubleshooting**:
	- If no Release PR appears, check that commits on `main` follow the Conventional Commits convention and that the workflow has the required permissions.
	- If the build job fails to push to GHCR, verify `GITHUB_TOKEN` or `CR_PAT` has `packages:write` and that `docker/login-action` is using the correct credentials in `.github/workflows/docker-build-and-push.yml`.
	- Use the artifact logs and Playwright traces (if available) for test failures; CI uploads Playwright artifacts per-browser.

## Files

- Release workflow: [.github/workflows/release.yml](.github/workflows/release.yml)
- Release-please config: [release-please-config.json](release-please-config.json)
- Release-please manifest: [.release-please-manifest.json](.release-please-manifest.json)
- Build & push workflow: [.github/workflows/docker-build-and-push.yml](.github/workflows/docker-build-and-push.yml)


## Local testing

To run E2E tests locally using Playwright:

1. Install dependencies in `frontend/`:

```
cd frontend
npm install
npx playwright install
```

2. Start the backend and frontend dev servers (see README).

3. Run Playwright tests:

```
npm run test:e2e
```

The E2E tests assume the frontend dev server is available and proxied to the backend. Set `E2E_BASE_URL` to override the base URL.
