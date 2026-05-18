# Brand and UI System (Quasar)

## Brand direction from attached logo
Observed identity cues from your logo:
- Deep dark background
- Bright cable-green accent
- Technical, clean, industrial tone
- Curved cable motif as a signature element

Brand values integrated from `/Users/samsjo02/Downloads/grafiskProfil.pdf` extraction:
- Typography families: `Myriad Pro` and `Raleway SemiBold`
- Profile primary blue token from PDF color metadata: `#4F80FF` (derived from `[20224,32768,65535]`)

## Design principles
- Functional first: operational UI with strong readability
- Brand-led accents: green used for active state, scan success, and key CTA
- Calm surfaces: dark neutrals for dense data views
- Motion with meaning: route transitions and scan feedback only

## Quasar token proposal
Use these as CSS vars and map to Quasar brand config.

- Brand primary: #4F80FF
- Brand primary-600: #2D9148
- Brand success: #43C36B
- Brand warning: #F7B84B
- Brand danger: #E65656
- Surface-900: #0C1114
- Surface-800: #11181D
- Surface-700: #182228
- Text-primary: #E9F1EE
- Text-secondary: #A8BAB1
- Border-subtle: #243138

## Typography
Integrated profile pair:
- Headings/UI emphasis: Raleway SemiBold (600)
- Body/data dense text: Myriad Pro (400)
- Numeric/scan IDs: Myriad Pro (400)

If your grafisk profil specifies different fonts, replace in one place:
- Quasar boot typography config
- global CSS font variables

## Component style guidance
- Buttons: rounded-md, high-contrast labels, strong hover/focus ring
- Cards: elevated dark surfaces with subtle border and green active rail
- Tables: zebra with compact density option and sticky mobile column strategy
- Scanner panels: extra-large input targets, persistent camera trigger, haptic-compatible feedback states

## Theming modes
- dark (default)
- light
- auto (prefers-color-scheme)

## Accessibility baseline
- Minimum contrast 4.5:1 for body text
- keyboard-first nav for all admin workflows
- focus-visible styling mandatory
- reduced-motion variant for animations
