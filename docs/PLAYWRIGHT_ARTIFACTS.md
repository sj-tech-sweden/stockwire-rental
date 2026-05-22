# Playwright Artifacts and Traces

CI runs Playwright E2E across Chromium, Firefox and WebKit and uploads artifacts for each browser.

Artifacts uploaded per job:
- `frontend/playwright-report` — HTML report (reporter=html)
- `frontend/test-results` — raw test results, traces and other files Playwright stores
- `frontend/tests/e2e/artifacts` — any test-specific artifacts saved by tests

Downloading artifacts from GitHub Actions

1. Open the workflow run in the GitHub Actions UI.
2. Under the job for a given browser, expand `Artifacts` and download the ZIP file.

Inspecting traces locally

1. Unzip the artifact. Locate the trace file(s) (usually `.trace` within `test-results` or `playwright-report`).
2. Install Playwright locally if you don't have it:

```
cd frontend
npm ci
npx playwright install
```

3. Open a trace file:

```
npx playwright show-trace /path/to/trace.zip
```

or for a single trace file:

```
npx playwright show-trace /path/to/test-results/1234-trace.zip
```

Viewing the HTML report

1. From the artifact ZIP, extract `playwright-report` folder.
2. Serve the folder locally (or open `index.html`):

```
# from the extracted directory
npx http-server -p 8001 .
# then open http://localhost:8001 in browser
```

or open `playwright-report/index.html` directly in your browser.

Notes

- Playwright traces require `playwright` CLI to render. Use the same Playwright version as CI for best compatibility.
- CI uploads artifacts even on failure; the `if: always()` ensures traces and screenshots are preserved for debugging.
