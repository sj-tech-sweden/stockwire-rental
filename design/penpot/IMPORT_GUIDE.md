# Importing the Stockwire Design System into Penpot

This guide assumes you are using **Penpot Cloud** (`design.penpot.app`) or a
self-hosted Penpot instance with the same features.

> **Note:** Penpot's built-in design token support does **not** require the Tokens Studio plugin. The plugin referenced in older guides is mainly for Figma. Use Penpot's native **Tokens** panel instead.

## What you will create

1. A **Design System Library** file in Penpot.
2. A set of **Shared Color / Typography / Component assets**.
3. Published library that can be enabled in any new Stockwire project.

## Step 1 — Create the library file

1. Log in to Penpot.
2. Create a new project named `Stockwire Design System`.
3. Inside the project, create a file named `Stockwire Library`.
4. Open the file.

## Step 2 — Import design tokens (native Penpot Tokens)

Penpot has a built-in **Tokens** panel that supports the W3C Design Tokens Format.

1. Open the **Tokens** panel (usually in the right sidebar or under the design tab).
2. Choose **Import tokens** or **Load from file**.
3. Upload `design/tokens/tokens.penpot.json`.
4. Penpot will create token groups for:
   - `stockwire.color.brand.*`
   - `stockwire.color.semantic.*`
   - `stockwire.surface.*`
   - `stockwire.text.*`
   - `stockwire.border.*`
   - `stockwire.font.*`
   - `stockwire.spacing.*`
   - `stockwire.radius.*`
5. Apply the tokens to your local fills, strokes, and text styles.

> **If import fails:** Penpot versions vary. If the W3C format is not accepted, use `design/tokens/tokens.json` (full W3C) or add the colors manually from the list in Step 4.

## Step 3 — Import brand assets

> **Note:** Dragging an SVG into Penpot imports it as a group of shapes, **not** as a component. You must convert the imported group into a component afterwards.

1. Create a board/page named `Brand Assets`.
2. Drag and drop the SVGs from `design/assets/` onto the canvas:
   - `logo.svg`
   - `logo-mark.svg`
   - `cable-motif.svg`
3. Select each imported SVG group on the canvas.
4. Right-click and choose **Create component** (or press **Ctrl+K** / **Cmd+K**).
5. In the **Components** panel (or right sidebar), rename each component:
   - `Logo / Full`
   - `Logo / Mark`
   - `Motif / Cable Wave`

> **Why the "Add component" button opens a file browser:** That button is for importing `.penpot` component files, not for turning canvas objects into components. Always use **Create component** from the canvas context menu instead.

## Step 4 — Build the color library

If the token import worked, Penpot should already have these as tokens. If not, add them manually:

1. Open **Assets > Colors**.
2. Add the following solid colors:
   - `brand/green` #3F873F
   - `brand/green-600` #2D9148
   - `brand/green-dark` #35A853
   - `profile/blue` #4F80FF
   - `semantic/success` #3F873F
   - `semantic/warning` #F7B84B
   - `semantic/danger` #E65656
   - `surface/900` #0C1114
   - `surface/800` #11181D
   - `surface/700` #182228
   - `text/primary` #E9F1EE
   - `text/secondary` #A8BAB1
   - `border/subtle` #243138

## Step 5 — Build typography styles

1. Open **Assets > Typography**.
2. Add these text styles:
   - `Heading / H1` — Raleway 600, 32px, #E9F1EE
   - `Heading / H2` — Raleway 600, 24px, #E9F1EE
   - `Heading / H3` — Raleway 600, 20px, #E9F1EE
   - `Body / Regular` — Myriad Pro 400, 16px, #E9F1EE
   - `Body / Muted` — Myriad Pro 400, 14px, #A8BAB1
   - `Numeric / ID` — Myriad Pro 400, 14px, #E9F1EE (monospaced fallback optional)
   - `Button / Primary` — Raleway 600, 14px, #FFFFFF

## Step 6 — Build component library

Create a page named `Components`. You have two options:

### Option A — Use the SVG templates (faster)

Ready-made SVGs live in `design/assets/components/`. Drag them onto the canvas, convert each to a component, and edit the text as needed.

Available templates:

- `button-primary.svg` → `Button / Primary`
- `button-secondary.svg` → `Button / Secondary`
- `button-danger.svg` → `Button / Danger`
- `card-default.svg` → `Card / Default`
- `card-active.svg` → `Card / Active`
- `input-outlined.svg` → `Input / Outlined`
- `input-filled.svg` → `Input / Filled`
- `chip-success.svg` → `Chip / Status / Success`
- `chip-warning.svg` → `Chip / Status / Warning`
- `chip-danger.svg` → `Chip / Status / Danger`
- `banner-success.svg` → `Banner / Success`
- `banner-warning.svg` → `Banner / Warning`
- `banner-danger.svg` → `Banner / Danger`
- `drawer-item.svg` → `Drawer / Item`
- `drawer-item-active.svg` → `Drawer / Active`
- `table-header.svg` → `Table / Header`
- `table-row.svg` → `Table / Row`

For each:

1. Drag the SVG onto the canvas.
2. Select the imported group.
3. Right-click → **Create component**.
4. Rename in the Components panel (e.g., `Button / Primary`).

### Option B — Draw from the spec

Use `components.md` to draw each element manually. This is more work but gives you full control over states and auto-layout.

Components to build:

- `Button / Primary`
- `Button / Secondary`
- `Button / Danger`
- `Card / Default`
- `Card / Active`
- `Input / Outlined`
- `Input / Filled`
- `Table / Row`
- `Table / Header`
- `Drawer / Item`
- `Drawer / Active`
- `Scanner / Target`
- `Chip / Status`
- `Banner / Success`
- `Banner / Warning`
- `Banner / Danger`

### How to create a component in Penpot

1. Draw or import the element on the canvas.
2. Select all the layers that belong to the element.
3. Right-click the selection and choose **Create component** (shortcut: **Ctrl+K** / **Cmd+K**).
4. Penpot adds the component to the **Components** panel.
5. Rename it there to match the naming above.
6. To reuse it, drag the component from the Components panel onto another page, or copy an instance and paste it.

### Tips

- Group related layers first (**Ctrl+G** / **Cmd+G**) if it makes the component easier to select.
- Apply the tokens/colors before creating the component, so every instance stays linked to the library.
- Use **slash naming** (`Button / Primary`) so the Components panel organizes them into folders.

## Step 7 — Publish as shared library

1. Go to **File > Publish as library**.
2. Enable the library.
3. In any new Stockwire design file, go to **Assets > Libraries** and enable `Stockwire Library`.

## Step 8 — Create project files

For each area of the Stockwire interface you want to improve, create a new file:

- `Stockwire / Dashboard`
- `Stockwire / Inventory`
- `Stockwire / Jobs`
- `Stockwire / Scan`
- `Stockwire / Settings`

Enable the shared library in each file and use the components/colors/typography from it.

## Keeping Penpot in sync

When the design system evolves:

1. Update `design/tokens/tokens.json` (source of truth).
2. Update `design/tokens/tokens.penpot.json` if the Penpot format changes.
3. Update the Penpot library tokens/colors.
4. Update affected components.
5. Republish the library.
6. Notify the team to accept library updates in their design files.

## Exporting from Penpot back to code

Penpot can export:

- **CSS** for individual boards/components — useful for checking token alignment.
- **SVG** for icons and motifs.
- **Images (PNG/SVG/PDF)** for presentation decks.

For a full round-trip, consider the **Penpot exporter** CLI or a future CI integration that compares exported CSS against `frontend/src/css/app.css`.
