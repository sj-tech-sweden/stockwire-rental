# Importing Current Stockwire Pages into Penpot

You don't need to rebuild every page from scratch to test small UI changes. Use the existing screenshots as reference images and design improvements directly on top of them.

## What you need

The repository already contains PNG screenshots of most pages in both dark and light themes:

```
docs/screenshots/
├── dashboard-dark.png
├── dashboard.png
├── inventory-dark.png
├── inventory.png
├── jobs-dark.png
├── jobs.png
├── scan-dark.png
├── scan.png
├── settings-dark.png
├── settings.png
├── companies-dark.png
├── companies.png
├── crew-dark.png
├── crew.png
├── venues-dark.png
├── venues.png
├── labels-dark.png
├── labels.png
├── activity-dark.png
├── activity.png
├── finance-dark.png
├── finance.png
└── ...
```

Each `-dark.png` file is the default dark theme. The file without the suffix is the light theme.

## Import workflow

### Step 1 — Create reference files in Penpot

Create one Penpot file per page you want to improve, for example:

- `Stockwire / Dashboard`
- `Stockwire / Inventory`
- `Stockwire / Jobs`
- `Stockwire / Scan`

Enable the `Stockwire Library` shared library in each file.

### Step 2 — Add the screenshot as a reference board

1. Create a board (artboard) with the same dimensions as the screenshot.
   - Most screenshots are around **1440×900** or **1280×800**. Penpot will show the imported image dimensions when you drag it in.
2. Drag the PNG screenshot from `docs/screenshots/` onto the board.
3. Penpot imports it as an image layer.
4. **Lock the image layer** so you don't accidentally move it while designing.

### Step 3 — Design improvements on top

1. Create a new layer above the screenshot.
2. Use components, colors, and typography from the shared library.
3. Draw the improved version directly over the existing UI.
4. Use low-opacity rectangles or outlines to highlight changed areas.

### Step 4 — Compare versions

1. Duplicate the board.
2. On the duplicate, hide the screenshot layer.
3. Now you have:
   - **Board A:** Screenshot + improvement overlay
   - **Board B:** Just the improved design

Use these two boards to present before/after comparisons.

## Quick start — which screenshots to use

| Page | Dark screenshot | Light screenshot |
|---|---|---|
| Dashboard | `dashboard-dark.png` | `dashboard.png` |
| Inventory | `inventory-dark.png` | `inventory.png` |
| Jobs | `jobs-dark.png` | `jobs.png` |
| Scan | `scan-dark.png` | `scan.png` |
| Settings | `settings-dark.png` | `settings.png` |
| Companies | `companies-dark.png` | `companies.png` |
| Crew | `crew-dark.png` | `crew.png` |
| Venues | `venues-dark.png` | `venues.png` |
| Labels | `labels-dark.png` | `labels.png` |
| Activity | `activity-dark.png` | `activity.png` |
| Finance | `finance-dark.png` | `finance.png` |

## Updating screenshots

When the frontend changes:

1. Run the app and capture new screenshots.
2. Replace the files in `docs/screenshots/`.
3. Re-import the updated image into Penpot (or replace the image layer).

### Automated screenshot capture

If you add Playwright E2E tests, you can generate screenshots automatically:

```bash
docker compose -f infra/compose/docker-compose.dev.yml --env-file infra/env/.env run --rm frontend npm run test:e2e
```

Then save the relevant artifacts to `docs/screenshots/`.

## Prototyping tips

- **Start with one page.** Pick the page you use most (e.g., Inventory or Jobs) and redesign only the elements that cause friction.
- **Use boards for variants.** Create multiple boards for A/B tests, such as "compact table" vs. "card list on mobile."
- **Keep the library enabled.** All colors and components should come from the shared `Stockwire Library` so changes propagate.
- **Annotate changes.** Add sticky notes or text labels explaining why a change improves usability.

## Example: improving the Scan page

1. Create file `Stockwire / Scan Improvements`.
2. Enable `Stockwire Library`.
3. Add board `Current Scan` and drag in `docs/screenshots/scan-dark.png`.
4. Lock the image.
5. Draw a new scanner target using the `Scanner / Target` component.
6. Add a device thumbnail area using the `Card / Default` component.
7. Add a status banner using `Banner / Success`.
8. Duplicate the board, hide the screenshot, and name it `Proposed Scan`.

Now you can toggle between current and proposed versions.
