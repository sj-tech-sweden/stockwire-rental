# Release Process & Required Secrets

This document describes the release workflow and the secrets required to publish images and operate API-key hashing.

## Secrets

- `API_KEY_PEPPER` — required by the backend to HMAC API keys before storing. Set a long random secret (32+ bytes). Keep this secret consistent across replicas; rotate carefully by supporting multiple peppers if needed.

- `JWT_SECRET` — the signing secret for JWT access tokens. Use a secure random value and keep it secret.

- `GITHUB_TOKEN` — provided by GitHub Actions automatically for workflows. For pushing to GHCR from workflows, you may need a Personal Access Token stored as `CR_PAT` or configure `GITHUB_TOKEN` with proper permissions in the workflow.

- `GHCR_USERNAME` / `GHCR_TOKEN` or `CR_PAT` — if not using `GITHUB_TOKEN` for package publishing, store a PAT with `packages:write` permission.

Set these secrets in the repository settings under "Settings → Secrets and variables → Actions".

## Release workflow

Releases are triggered by labeling a pull request with one of the semantic labels: `major`, `minor`, or `patch` (or by manually dispatching the Release workflow).

When a PR receives a label, the workflow will:

- Determine the release type from the label (major/minor/patch)
- Compute the next semantic version based on the latest git tag
- Create an annotated GitHub Release with the new tag
- (Placeholder) Build and push container images to GHCR — implement by calling the `docker-build-and-push` workflow or adding a composite action to build and push images.

Notes:

- Ensure repository secrets for GHCR are configured before enabling automated pushes.
- The release workflow currently creates the release and leaves a placeholder for image build/push. We recommend wiring it to the existing `docker-build-and-push.yml` via `workflow_run` or a composite action.

## How to use the Release workflow (step-by-step)

- **Label a PR**: Add one of `major`, `minor`, or `patch` to the pull request. The release workflow (`.github/workflows/release.yml`) listens for PR label events and will pick the highest-priority semantic label present.

- **What the workflow does**:

	- Determines release type from PR labels or from manual `workflow_dispatch` input.
	- Computes the next semantic version based on latest git tag (from the default branch).
	- Creates an annotated GitHub Release with the new tag using `softprops/action-gh-release`.
	- Dispatches the `docker-build-and-push.yml` workflow to build and publish images to GHCR.

- **Manual dispatch**: You can run the same workflow manually from the Actions tab and provide `release_type` (major/minor/patch). Manual dispatch will compute the next version accordingly.

- **Secrets & permissions**:
	- Ensure `GITHUB_TOKEN` has `packages: write` when used for GHCR login, or provide `CR_PAT` (Personal Access Token) in repository secrets with `packages:write` permission.
	- `API_KEY_PEPPER` and `JWT_SECRET` must be set for production deployments.

- **How to verify a release**:
	- Check the Actions run for `.github/workflows/release.yml` to see computed tag and release creation.
	- Confirm a Release is created in the repository `Releases` UI with the computed tag.
	- Verify the `docker-build-and-push` workflow run was triggered and completed (it will push images to `ghcr.io/${{ github.repository_owner }}/...`).

- **Troubleshooting**:
	- If no tag is computed, ensure there is at least one previous git tag (the script treats no-tags as `0.0.0`).
	- If the build job fails to push to GHCR, verify `GITHUB_TOKEN` or `CR_PAT` has `packages:write` and that `docker/login-action` is using the correct credentials in `.github/workflows/docker-build-and-push.yml`.
	- Use the artifact logs and Playwright traces (if available) for test failures; CI uploads Playwright artifacts per-browser.

## Files

- Release workflow: [.github/workflows/release.yml](.github/workflows/release.yml)
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
