# Stockwire Component Library Spec for Penpot

Use this document to build reusable components in the Penpot `Stockwire Library`.
All values reference `design/tokens/tokens.json`.

## Buttons

### Primary Button

- **Background:** `brand/green` (#3F873F)
- **Text:** White, Raleway 600, 14px
- **Padding:** 12px vertical, 20px horizontal
- **Radius:** 8px
- **Hover:** `brand/green-600` (#2D9148)
- **Focus ring:** 2px outline `brand/green` with 2px offset
- **Icon:** left or right, 18px, white
- **States:** default, hover, active, disabled (opacity 0.5)

### Secondary Button

- **Background:** transparent
- **Border:** 1px `border/subtle` (#243138)
- **Text:** `text/primary` (#E9F1EE), Raleway 600, 14px
- **Padding:** 12px vertical, 20px horizontal
- **Radius:** 8px
- **Hover:** background `surface/800` (#11181D)

### Danger Button

- **Background:** `semantic/danger` (#E65656)
- **Text:** White, Raleway 600, 14px
- **Padding:** 12px vertical, 20px horizontal
- **Radius:** 8px

## Cards

### Default Card

- **Background:** `surface/700` (#182228)
- **Border:** 1px rgba(63, 135, 63, 0.08)
- **Radius:** 8px
- **Shadow:** `shadow/card` (0 1px 0 rgba(0,0,0,0.25))
- **Padding:** 16px

### Active Card

- Same as Default Card
- **Left rail:** 3px `brand/green` (#3F873F)

## Forms

### Outlined Input

- **Background:** `surface/800` (#11181D)
- **Border:** 1px `border/subtle` (#243138)
- **Radius:** 8px
- **Label:** `text/secondary`, Myriad Pro 400, 14px
- **Value:** `text/primary`, Myriad Pro 400, 16px
- **Placeholder:** `text/secondary` at 60% opacity
- **Focus border:** `brand/green` (#3F873F)
- **Padding:** 12px 16px

### Filled Input

- **Background:** `surface/900` (#0C1114)
- **Border:** none
- **Radius:** 8px
- Otherwise same as Outlined Input.

## Tables

### Table Header

- **Background:** `surface/800` (#11181D)
- **Text:** `text/secondary`, Raleway 600, 12px, uppercase, letter-spacing 0.08em
- **Border bottom:** 1px `border/subtle`
- **Padding:** 12px 16px

### Table Row

- **Background:** `surface/700` (#182228)
- **Text:** `text/primary`, Myriad Pro 400, 14px
- **Border bottom:** 1px rgba(110, 150, 145, 0.22)
- **Padding:** 12px 16px
- **Hover:** background `surface/800`
- **Zebra (optional):** alternate rows at 96% opacity of base

## Navigation

### Drawer Item

- **Background:** transparent
- **Text:** `drawer/text` (#b8ccc4), Myriad Pro 400, 15px
- **Icon:** `brand/green`, 20px
- **Padding:** 10px 14px
- **Margin:** 6px 10px
- **Radius:** 8px
- **Hover / Active:** background rgba(63, 135, 63, 0.08), text `text/primary`

### Drawer Header

- **Text:** `brand/green`, Raleway 700, 10px, uppercase, letter-spacing 0.12em
- **Margin:** 16px 20px 8px

## Scanner

### Scanner Target

- **Background:** `surface/800` (#11181D)
- **Border:** 2px dashed `brand/green` (#3F873F)
- **Radius:** 16px
- **Min height:** 160px
- **Icon:** `brand/green`, 48px
- **Label:** `text/primary`, Raleway 600, 18px, centered

### Scan Feedback / Success

- **Background:** rgba(63, 135, 63, 0.12)
- **Border:** 1px `brand/green`
- **Icon:** `semantic/success`
- **Text:** `text/primary`

## Status Chips

### Status / Success

- **Background:** rgba(63, 135, 63, 0.16)
- **Text:** `#43C36B`, Myriad Pro 600, 12px
- **Radius:** 999px
- **Padding:** 4px 10px

### Status / Warning

- **Background:** rgba(247, 184, 75, 0.16)
- **Text:** `#F7B84B`, Myriad Pro 600, 12px

### Status / Danger

- **Background:** rgba(230, 86, 86, 0.16)
- **Text:** `#E65656`, Myriad Pro 600, 12px

## Banners

### Banner / Success

- **Background:** `semantic/success` (#3F873F)
- **Text:** white, Myriad Pro 400, 14px
- **Radius:** 8px
- **Padding:** 12px 16px

### Banner / Warning

- **Background:** `semantic/warning` (#F7B84B)
- **Text:** `#0C1114`

### Banner / Danger

- **Background:** `semantic/danger` (#E65656)
- **Text:** white

## Header

### App Header

- **Height:** 60px
- **Background (dark):** `surface/700`
- **Background (light):** `#f3f9f3`
- **Border bottom:** 1px rgba(255,255,255,0.04) dark / rgba(15,23,32,0.06) light
- **Title:** `text/primary` (dark) / `#0f1720` (light), Raleway 600, 18px
- **Actions:** transparent flat buttons, header text color

## Layout primitives

Use these spacers to keep layouts consistent:

- `space/xs` — 4px
- `space/sm` — 8px
- `space/md` — 16px
- `space/lg` — 24px
- `space/xl` — 32px
- `space/2xl` — 48px

## Do's and don'ts

- **Do** use `brand/green` only for primary actions, active states, scan success, and key CTAs.
- **Do not** use pure black; deepest background is `surface/900` (#0C1114).
- **Do** maintain 4.5:1 minimum contrast for body text.
- **Do not** introduce new accent colors without updating the tokens.
- **Do** use Raleway only for headings and button labels; use Myriad Pro for body/data.
