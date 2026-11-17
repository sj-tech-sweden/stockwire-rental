// Tour navigation metadata for the interactive click-through walkthroughs.
//
// Each tour is keyed by the matching help article id (e.g. `walkthroughReceivePo`)
// so the "Start click-through" button on a walkthrough article can launch it
// directly. A tour is an ordered list of steps:
//
//   route  – the real app route to navigate to for this step. The tour engine
//            pushes this route when the step becomes active so the user lands on
//            the actual screen the instruction is about.
//   target – an optional CSS selector to spotlight (a stable hook on the page).
//            When null (the default for now) the coach card is centered and the
//            whole UI is dimmed gently instead of highlighting one element. This
//            keeps the tour robust without depending on pixel-exact selectors.
//
// The displayed title/text for each step live in i18n at
// `help.tours.<tourId>.steps[<i>].{title,text}` so they stay in EN/SV parity.
//
// IMPORTANT: the number of steps here MUST match the number of `steps` entries
// in the i18n locale files (see /tmp/validate_help.cjs which checks this).

export const TOURS = {
  walkthroughReceivePo: [
    { route: '/purchase-orders' },
    { route: '/purchase-orders' },
    { route: '/purchase-orders' },
    { route: '/receive' },
    { route: '/inventory' },
  ],
  walkthroughRunJob: [
    { route: '/jobs' },
    { route: '/jobs' },
    { route: '/jobs' },
    { route: '/jobs' },
    { route: '/jobs' },
  ],
  walkthroughProductVendor: [
    { route: '/inventory' },
    { route: '/inventory' },
    { route: '/vendor-catalog' },
    { route: '/inventory' },
    { route: '/inventory' },
  ],
  walkthroughDeliveryRoute: [
    { route: '/route-planner' },
    { route: '/route-planner' },
    { route: '/route-planner' },
    { route: '/route-planner' },
    { route: '/route-planner' },
  ],
  walkthroughPrintLabels: [
    { route: '/labels' },
    { route: '/labels' },
    { route: '/labels' },
    { route: '/labels' },
  ],
  walkthroughEntraSso: [
    { route: '/settings' },
    { route: '/settings' },
    { route: '/settings' },
    { route: '/settings' },
    { route: '/settings' },
  ],
  walkthroughOnboardCrew: [
    { route: '/persons' },
    { route: '/persons' },
    { route: '/persons' },
    { route: '/jobs' },
    { route: '/persons' },
  ],
}

// Article ids that have an interactive click-through tour.
export const TOUR_IDS = Object.keys(TOURS)
