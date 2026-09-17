# Importing the Stockwire Design System into Penpot

This guide assumes you are using **Penpot Cloud** (`design.penpot.app`) or a
self-hosted Penpot instance with the same features.

## What you will create

1. A **Design System Library** file in Penpot.
2. A set of **Shared Color / Typography / Component assets**.
3. Published library that can be enabled in any new Stockwire project.

## Step 1 — Create the library file

1. Log in to Penpot.
2. Create a new project named `Stockwire Design System`.
3. Inside the project, create a file named `Stockwire Library`.
4. Open the file.

## Step 2 — Import design tokens

Penpot supports the W3C Design Tokens Format through the **Tokens Studio for Penpot** plugin (or Penpot's native Tokens feature, depending on your version).

### Using the Tokens Studio plugin

1. In Penpot, open the plugin panel and launch **Tokens Studio**.
2. Choose **Import tokens**.
3. Upload `design/tokens/tokens.json`.
4. The plugin will create tokens for:
   - Brand colors (`stockwire.color.brand.*`)
   - Semantic colors (`stockwire.color.semantic.*`)
   - Surfaces (`stockwire.surface.*`)
   - Text colors (`stockwire.text.*`)
   - Border colors (`stockwire.border.*`)
   - Font families, weights, sizes
   - Spacing, radius, shadow, motion
5. Apply the tokens to your local styles so they can be used across components.

> **Tip:** If the plugin does not yet support all token types, import the color tokens first, then add typography and spacing manually.

## Step 3 — Import brand assets

1. Create a board/page named `Brand Assets`.
2. Drag and drop the SVGs from `design/assets/` into Penpot:
   - `logo.svg`
   - `logo-mark.svg`
   - `cable-motif.svg`
3. Convert each imported SVG to a **Component** (`Create component`).
4. Name them:
   - `Logo / Full`
   - `Logo / Mark`
   - `Motif / Cable Wave`

## Step 4 — Build the color library

1. Open **Assets > Colors**.
2. Add the following solid colors, naming them to match the tokens:
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

Create a page named `Components`. Use the component spec in `components.md` to build:

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

For each component, use the tokens/colors above and mark it as a **Component**.

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

1. Update `design/tokens/tokens.json`.
2. Update the Penpot library tokens/colors.
3. Update affected components.
4. Republish the library.
5. Notify the team to accept library updates in their design files.

## Exporting from Penpot back to code

Penpot can export:

- **CSS** for individual boards/components — useful for checking token alignment.
- **SVG** for icons and motifs.
- **Images (PNG/SVG/PDF)** for presentation decks.

For a full round-trip, consider the **Penpot exporter** CLI or a future CI integration that compares exported CSS against `frontend/src/css/app.css`.
